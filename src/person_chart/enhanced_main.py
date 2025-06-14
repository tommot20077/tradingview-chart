import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from .config import config
from .providers.enhanced_crypto_provider import EnhancedCryptoPriceProviderRealtime, EnhancedInfluxDBManager
from .services.kafka_manager import kafka_manager, _KAFKA_AVAILABLE
from .services.database_manager import SubscriptionRepository

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class EnhancedConnectionManager:
    """
    管理 WebSocket 連接、加密貨幣價格提供者和後端服務。
    負責處理客戶端連接、訊息廣播以及啟動/停止所有服務。
    """

    def __init__(self):
        """初始化 EnhancedConnectionManager 實例。"""
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: Optional[EnhancedCryptoPriceProviderRealtime] = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self._kafka_thread: Optional[threading.Thread] = None
        self.subscription_repo: Optional[SubscriptionRepository] = None
        self._stop_event = threading.Event()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        log.info("EnhancedConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 連接。"""
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket 客戶端已連接。活動連接數: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """斷開 WebSocket 連接。"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info(f"WebSocket 客戶端已斷開連接。活動連接數: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """將訊息廣播到所有連接的 WebSocket 客戶端。"""
        if not self.active_connections:
            return

        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected_clients.append(connection)

        for client in disconnected_clients:
            self.disconnect(client)

    def sync_broadcast(self, message: str):
        """在同步上下文中使用執行緒安全的方式廣播訊息。"""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)

    def _kafka_consumer_worker(self):
        """在背景執行緒中運行的 Kafka 消費者。"""
        log.info("Kafka 消費者工作執行緒啟動。")
        try:
            if not self.kafka_consumer:
                log.warning("Kafka 消費者未初始化，工作執行緒退出。")
                return

            for message in self.kafka_consumer:
                if self._stop_event.is_set():
                    break
                log.debug(f"從 Kafka 收到消息: {message.value}")
                self.sync_broadcast(message.value)
        except Exception as e:
            if "KafkaConsumer is closed" == str(e):
                log.info(f"Kafka 消費者已關閉")
            else:
                log.error(f"Kafka 消費者工作執行緒中發生錯誤: {e}")
        finally:
            log.info("Kafka 消費者工作執行緒停止。")

    def start_services(self):
        """初始化並啟動所有後端服務。"""
        log.info("啟動所有後端服務...")
        if not config.validate():
            raise ValueError("配置無效，請檢查 .env 文件。")

        influxdb_manager = EnhancedInfluxDBManager(
            host=config.influxdb_host, token=config.influxdb_token,
            database=config.influxdb_database, batch_size=200
        )

        self.subscription_repo = SubscriptionRepository(
            db_type=config.db_type, db_path=config.db_path, db_url=config.db_url
        )

        message_cb = self.sync_broadcast
        if config.kafka_enabled and _KAFKA_AVAILABLE and kafka_manager:
            log.info("Kafka 模式已啟用。正在建立生產者和消費者...")
            self.kafka_producer = kafka_manager.create_producer()
            self.kafka_consumer = kafka_manager.create_consumer(
                topic=config.kafka_topic, group_id="crypto-streamer-group"
            )
            message_cb = None  # Kafka 將處理廣播
            self._kafka_thread = threading.Thread(target=self._kafka_consumer_worker, daemon=True)
            self._kafka_thread.start()
        else:
            if config.kafka_enabled:
                log.warning("Kafka 已在配置中啟用，但 kafka-python 庫不可用或管理器初始化失敗。將使用直接回調模式。")
            log.info("Kafka 模式已禁用。使用直接回調模式。")

        self.crypto_provider = EnhancedCryptoPriceProviderRealtime(
            influxdb_manager=influxdb_manager,
            message_callback=message_cb,
            kafka_producer=self.kafka_producer,
            kafka_topic=config.kafka_topic
        )
        self.crypto_provider.start()
        self.load_and_subscribe()

    def load_and_subscribe(self):
        """從數據庫加載並訂閱持久化的符號。"""
        if not self.crypto_provider or not self.subscription_repo:
            log.warning("提供者或倉庫未初始化，無法加載訂閱。")
            return

        subscriptions = self.subscription_repo.get_all_subscriptions()
        log.info(f"從資料庫找到 {len(subscriptions)} 個持久化訂閱。")
        for sub in subscriptions:
            log.info(f"自動訂閱: {sub['symbol']}@{sub['interval']}")
            self.crypto_provider.subscribe(symbol=sub['symbol'], interval=sub['interval'])

    def stop_services(self):
        """停止所有後端服務。"""
        log.info("停止所有後端服務...")
        self._stop_event.set()
        if self.crypto_provider:
            self.crypto_provider.stop()
        if self.kafka_consumer:
            self.kafka_consumer.close()
        if self._kafka_thread and self._kafka_thread.is_alive():
            self._kafka_thread.join(timeout=5)


manager = EnhancedConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理。"""
    log.info("應用程式啟動...")
    manager.loop = asyncio.get_running_loop()
    manager.start_services()
    yield
    log.info("應用程式關閉...")
    manager.stop_services()


app = FastAPI(
    title="增強型加密貨幣價格串流 API",
    description="具有增強型 InfluxDB 儲存、監控和持久化訂閱的即時加密貨幣價格串流",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """用於即時價格串流的 WebSocket 端點。"""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # 保持連接活躍
    except Exception:
        log.info("WebSocket 連接異常關閉。")
    finally:
        manager.disconnect(websocket)


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    """提供 Web 監控儀表板。"""
    return FileResponse('./static/index.html')


@app.get("/health")
async def health_check():
    """健康檢查端點，返回系統狀態。"""
    provider_status = "running" if manager.crypto_provider and manager.crypto_provider.binance_client else "stopped"
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crypto_provider_status": provider_status,
        "active_websocket_connections": len(manager.active_connections),
    }


@app.get("/stats")
async def get_detailed_stats():
    """獲取詳細的系統和提供者統計數據。"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return manager.crypto_provider.get_stats()


@app.get("/prices")
async def get_latest_prices():
    """獲取所有已快取符號的最新價格。"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return manager.crypto_provider.get_latest_prices()


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """訂閱新的交易對，並持久化該訂閱。"""
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")

    manager.crypto_provider.subscribe(symbol, interval=interval)
    manager.subscription_repo.add_subscription(symbol, interval)
    return {"status": "success", "message": f"已訂閱 {symbol.upper()}@{interval} 並已持久化。"}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """取消訂閱交易對，並移除持久化訂閱。"""
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")

    manager.crypto_provider.unsubscribe(symbol, interval=interval)
    manager.subscription_repo.remove_subscription(symbol, interval)
    return {"status": "success", "message": f"已取消訂閱 {symbol.upper()}@{interval} 並已移除持久化記錄。"}


@app.get("/symbols")
async def get_subscribed_symbols():
    """獲取當前已訂閱的符號列表。"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return {
        "subscribed_streams": manager.crypto_provider.subscribed_symbols,
        "cached_symbols": list(manager.crypto_provider.get_latest_prices().keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    log.info(f"在 {config.api_host}:{config.api_port} 啟動增強型服務器。")
    uvicorn.run("enhanced_main:app", host=config.api_host, port=config.api_port, reload=True)
