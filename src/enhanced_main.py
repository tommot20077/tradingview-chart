import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.websockets import WebSocket
from kafka import KafkaConsumer, KafkaProducer
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from config import config
from enhanced_crypto_provider import EnhancedCryptoPriceProvider, EnhancedInfluxDBManager
from kafka_manager import kafka_manager

# 設定日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


class EnhancedConnectionManager:
    """
    管理 WebSocket 連接和加密貨幣價格提供者。
    負責處理客戶端連接、斷開連接、訊息廣播以及啟動/停止價格提供者。
    """

    def __init__(self):
        """
        初始化 EnhancedConnectionManager 實例。

        輸入:
            無。

        輸出:
            無。
        """
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: Optional[EnhancedCryptoPriceProvider] = None
        self.kafka_consumer: Optional[KafkaConsumer] = None
        self.kafka_producer: Optional[KafkaProducer] = None
        self._kafka_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.loop = None
        self.connection_stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "failed_sends": 0
        }
        log.info("EnhancedConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """
        接受新的 WebSocket 連接並將其添加到活動連接列表中。

        輸入:
            websocket (WebSocket): 新建立的 WebSocket 連接。

        輸出:
            無。
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_stats["total_connections"] += 1
        log.info(
            f"WebSocket 客戶端已連接。活動連接數: {len(self.active_connections)}, 總連接數: {self.connection_stats['total_connections']}")

    def disconnect(self, websocket: WebSocket):
        """
        從活動連接列表中移除斷開連接的 WebSocket 客戶端。

        輸入:
            websocket (WebSocket): 要斷開的 WebSocket 連接。

        輸出:
            無。
        """
        if websocket in self.active_connections:
            websocket.close()
            self.active_connections.remove(websocket)
            log.info(f"WebSocket 客戶端已斷開連接。活動連接數: {len(self.active_connections)}")
        elif websocket:
            websocket.close()
            log.warning("嘗試斷開未知的 WebSocket 連接。")

    async def broadcast(self, message: str):
        """
        將訊息廣播到所有連接的 WebSocket 客戶端。

        輸入:
            message (str): 要廣播的訊息字串。

        輸出:
            無。
        """
        if not self.active_connections:
            log.debug("沒有活動的 WebSocket 連接，無需廣播。")
            return

        failed_connections = []
        successful_sends = 0

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                successful_sends += 1
            except Exception as e:
                log.warning(f"發送訊息到 WebSocket 客戶端失敗: {e}")
                failed_connections.append(connection)
                self.connection_stats["failed_sends"] += 1

        self.connection_stats["messages_sent"] += successful_sends
        log.debug(f"已廣播訊息。成功發送: {successful_sends}, 失敗: {len(failed_connections)}")

        # 移除失敗的連接
        for failed_connection in failed_connections:
            self.disconnect(failed_connection)

    def sync_broadcast(self, message: str):
        """
        在同步上下文中使用執行緒安全的方式廣播訊息。
        將異步廣播任務提交到運行中的事件循環。

        輸入:
            message (str): 要廣播的訊息字串。

        輸出:
            無。
        """
        if self.loop is None or not self.loop.is_running():
            log.warning("事件循環未運行，無法安排廣播。")
            return

        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
            log.debug("已安排同步廣播任務。")
        except Exception as e:
            log.error(f"安排廣播失敗: {e}")

    def _kafka_consumer_worker(self):
        """在背景執行緒中運行的 Kafka 消費者，使用 poll 以響應停止事件。"""
        log.info("Kafka 消費者工作執行緒啟動。")
        try:
            while not self._stop_event.is_set():
                msg_pack = self.kafka_consumer.poll(timeout_ms=1000)
                if not msg_pack:
                    continue
                for tp, messages in msg_pack.items():
                    for message in messages:
                        log.debug(f"從 Kafka 收到消息: {message.value}")
                        self.sync_broadcast(message.value)
        except Exception as e:
            log.error(f"Kafka 消費者工作執行緒中發生錯誤: {e}")
        finally:
            log.info("Kafka 消費者工作執行緒停止。")

    def start_services(self):
        """
        初始化並啟動增強型加密貨幣價格提供者。
        它會驗證配置，建立 InfluxDB 管理器和價格提供者，然後啟動它並訂閱預設符號。

        輸入:
            self (EnhancedConnectionManager): EnhancedConnectionManager 實例本身。

        輸出:
            無。

        異常:
            ValueError: 如果配置無效則拋出。
            Exception: 如果啟動價格提供者失敗則拋出。
        """
        log.info("啟動增強型加密貨幣價格提供者...")
        try:
            if not config.validate():
                log.error("配置無效。請檢查您的 .env 檔案。")
                raise ValueError("配置無效")

            # 建立增強型 InfluxDB 管理器，使用更大的批次大小以獲得更好的性能
            influxdb_manager = EnhancedInfluxDBManager(
                host=config.influxdb_host,
                token=config.influxdb_token,
                database=config.influxdb_database,
                batch_size=200  # 增加批次大小以獲得更好的性能
            )

            if config.kafka_enabled:
                log.info("Kafka 模式已啟用。正在建立生產者和消費者...")
                self.kafka_producer = kafka_manager.create_producer()
                self.kafka_consumer = kafka_manager.create_consumer(
                    topic=config.kafka_topic, group_id="crypto-streamer-group"
                )
                self.crypto_provider = EnhancedCryptoPriceProvider(
                    influxdb_manager=influxdb_manager,
                    kafka_producer=self.kafka_producer,
                    kafka_topic=config.kafka_topic
                )
                # 啟動 Kafka 消費者執行緒
                self._kafka_thread = threading.Thread(target=self._kafka_consumer_worker, daemon=True)
                self._kafka_thread.start()
            else:
                log.info("Kafka 模式已禁用。使用直接回調模式。")
                self.crypto_provider = EnhancedCryptoPriceProvider(
                    influxdb_manager=influxdb_manager,
                    message_callback=self.sync_broadcast
                )

            self.crypto_provider.start()

            # 訂閱配置的符號
            self.crypto_provider.subscribe(
                symbol=config.binance_symbol,
                interval=config.binance_interval
            )

            log.info(f"已為 {config.binance_symbol} 啟動增強型加密貨幣價格提供者。")

        except Exception as e:
            log.error(f"啟動增強型加密貨幣價格提供者失敗: {e}")
            raise

    def stop_services(self):
        """
        停止增強型加密貨幣價格提供者。

        輸入:
            self (EnhancedConnectionManager): EnhancedConnectionManager 實例本身。

        輸出:
            無。
        """

        log.info("停止增強型加密貨幣價格提供者...")
        self._stop_event.set()

        if self.crypto_provider:
            try:
                self.crypto_provider.stop()
                log.info("已停止增強型加密貨幣價格提供者。")
            except Exception as e:
                log.error(f"停止增強型加密貨幣價格提供者時發生錯誤: {e}")
        else:
            log.info("加密貨幣提供者未運行，無需停止。")

        if self._kafka_thread and self._kafka_thread.is_alive():
            log.info("正在等待 Kafka 消費者工作執行緒結束...")
            self._kafka_thread.join(timeout=5)
            if self._kafka_thread.is_alive():
                log.warning("Kafka 消費者工作執行緒未能在預期時間內結束。")
            else:
                log.info("Kafka 消費者工作執行緒已成功結束。")

        if self.kafka_consumer:
            try:
                self.kafka_consumer.close()
                log.info("已關閉 Kafka 消費者。")
            except Exception as e:
                log.error(f"關閉 Kafka 消費者時發生錯誤: {e}")


manager = EnhancedConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理。
    在應用程式啟動時啟動加密貨幣價格提供者，並在應用程式關閉時停止它。

    輸入:
        app (FastAPI): FastAPI 應用程式實例。

    輸出:
        AsyncGenerator: 異步生成器，用於管理應用程式的生命週期。
    """
    try:
        log.info("啟動增強型加密貨幣應用程式...")

        manager.loop = asyncio.get_running_loop()
        manager.start_services()

        log.info("增強型加密貨幣應用程式已成功啟動。")
        yield

    except Exception as e:
        log.error(f"啟動增強型加密貨幣應用程式失敗: {e}")
        raise

    finally:
        log.info("正在關閉增強型加密貨幣應用程式...")
        manager.stop_services()
        log.info("增強型加密貨幣應用程式關閉完成。")


app = FastAPI(
    title="增強型加密貨幣價格串流 API",
    description="具有增強型 InfluxDB 儲存和監控的即時加密貨幣價格串流",
    version="2.0.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源，生產環境請設置具體域名
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有方法
    allow_headers=["*"],  # 允許所有頭
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """
    用於即時價格串流的 WebSocket 端點。
    處理客戶端連接、接收訂閱/取消訂閱命令，並保持連接活躍。

    輸入:
        websocket (WebSocket): 傳入的 WebSocket 連接。

    輸出:
        無。
    """
    await manager.connect(websocket)
    try:
        while True:
            # 保持連接活躍並處理潛在的客戶端命令
            message = await websocket.receive_text()
            log.debug(f"從 WebSocket 接收到訊息: {message}")

            # 處理客戶端命令 (可選功能)
            if message.startswith("subscribe:"):
                symbol = message.split(":")[1].upper()
                if manager.crypto_provider:
                    manager.crypto_provider.subscribe(symbol)
                    await websocket.send_text(f"已訂閱 {symbol}")
                    log.info(f"客戶端已訂閱 {symbol}")
                else:
                    await websocket.send_text("錯誤: 加密貨幣提供者未運行。")
                    log.warning("客戶端嘗試訂閱，但加密貨幣提供者未運行。")

            elif message.startswith("unsubscribe:"):
                symbol = message.split(":")[1].upper()
                if manager.crypto_provider:
                    manager.crypto_provider.unsubscribe(symbol)
                    await websocket.send_text(f"已取消訂閱 {symbol}")
                    log.info(f"客戶端已取消訂閱 {symbol}")
                else:
                    await websocket.send_text("錯誤: 加密貨幣提供者未運行。")
                    log.warning("客戶端嘗試取消訂閱，但加密貨幣提供者未運行。")
            else:
                log.info(f"接收到未知 WebSocket 訊息: {message}")

    except Exception as e:
        log.info(f"WebSocket 連接關閉: {e}")
    finally:
        manager.disconnect(websocket)


@app.get("/", response_class=FileResponse)
async def root():
    """
    帶有儀表板的根端點。
    提供一個 HTML 頁面，顯示即時價格和系統統計數據。

    輸入:
        無。

    輸出:
        HTMLResponse: 包含儀表板 HTML 內容的 HTTP 回應。
    """

    return FileResponse('./static/index.html', media_type='text/html')


@app.get("/health")
async def health_check():
    """
    增強型健康檢查端點。
    返回應用程式的健康狀態，包括加密貨幣提供者狀態、活動 WebSocket 連接數和連接統計數據。

    輸入:
        無。

    輸出:
        Dict: 包含健康狀態資訊的字典。
    """
    log.info("執行健康檢查。")
    crypto_provider_status = "stopped"
    provider_stats = {}

    if manager.crypto_provider:
        crypto_provider_status = "running"
        provider_stats = manager.crypto_provider.get_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crypto_provider": crypto_provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "connection_stats": manager.connection_stats,
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols) if manager.crypto_provider else [],
        "provider_stats": provider_stats
    }


@app.get("/stats")
async def get_detailed_stats():
    """
    獲取詳細的系統統計數據。
    包括 WebSocket 連接統計、加密貨幣提供者統計和已訂閱符號列表。

    輸入:
        無。

    輸出:
        Dict: 包含詳細統計數據的字典。

    異常:
        HTTPException: 如果加密貨幣提供者未運行則返回 503 錯誤。
    """
    log.debug("獲取詳細系統統計數據。")
    if not manager.crypto_provider:
        log.error("加密貨幣提供者未運行，無法獲取統計數據。")
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")

    crypto_stats = manager.crypto_provider.get_stats()

    return {
        "system": {
            "active_websocket_connections": len(manager.active_connections),
            "connection_stats": manager.connection_stats,
            "uptime": datetime.now(timezone.utc).isoformat()
        },
        "crypto_provider": crypto_stats,
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols)
    }


@app.get("/prices")
async def get_latest_prices():
    """
    獲取所有已快取符號的最新價格。

    輸入:
        無。

    輸出:
        Dict[str, dict]: 鍵為符號，值為 PriceData 物件的字典表示形式。

    異常:
        HTTPException: 如果加密貨幣提供者未運行則返回 503 錯誤。
    """
    log.info("獲取所有已快取符號的最新價格。")
    if not manager.crypto_provider:
        log.error("加密貨幣提供者未運行，無法獲取最新價格。")
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")

    return manager.crypto_provider.get_latest_prices()


@app.get("/config")
async def get_config():
    """
    獲取當前配置（不包括敏感數據）。

    輸入:
        無。

    輸出:
        Dict: 包含應用程式配置的字典。
    """
    log.info("獲取當前配置。")
    return {
        "binance_symbol": config.binance_symbol,
        "binance_interval": config.binance_interval,
        "api_host": config.api_host,
        "api_port": config.api_port,
        "influxdb_host": config.influxdb_host,
        "influxdb_database": config.influxdb_database
    }


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """
    訂閱新的交易對價格串流。

    輸入:
        symbol (str): 要訂閱的交易對符號。
        interval (str): K 線資料的時間間隔，預設為 "1m"。

    輸出:
        Dict: 包含訂閱狀態和訊息的字典。

    異常:
        HTTPException: 如果加密貨幣提供者未初始化或訂閱失敗則返回錯誤。
    """
    log.info(f"嘗試訂閱符號: {symbol.upper()}，間隔: {interval}")
    if not manager.crypto_provider:
        log.error("加密貨幣提供者未初始化，無法訂閱符號。")
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")

    try:
        manager.crypto_provider.subscribe(symbol.upper(), interval)
        log.info(f"已成功訂閱 {symbol.upper()}，間隔 {interval}。")
        return {
            "status": "success",
            "message": f"已訂閱 {symbol.upper()}，間隔 {interval}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        log.error(f"訂閱 {symbol} 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """
    取消訂閱交易對價格串流。

    輸入:
        symbol (str): 要取消訂閱的交易對符號。
        interval (str): K 線資料的時間間隔，預設為 "1m"。

    輸出:
        Dict: 包含取消訂閱狀態和訊息的字典。

    異常:
        HTTPException: 如果加密貨幣提供者未初始化或取消訂閱失敗則返回錯誤。
    """
    log.info(f"嘗試取消訂閱符號: {symbol.upper()}，間隔: {interval}")
    if not manager.crypto_provider:
        log.error("加密貨幣提供者未初始化，無法取消訂閱符號。")
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")

    try:
        manager.crypto_provider.unsubscribe(symbol.upper(), interval)
        log.info(f"已成功取消訂閱 {symbol.upper()}，間隔 {interval}。")
        return {
            "status": "success",
            "message": f"已取消訂閱 {symbol.upper()}，間隔 {interval}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        log.error(f"取消訂閱 {symbol} 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/symbols")
async def get_subscribed_symbols():
    """
    獲取當前已訂閱的符號列表。

    輸入:
        無。

    輸出:
        Dict: 包含已訂閱符號、已快取符號和時間戳記的字典。

    異常:
        HTTPException: 如果加密貨幣提供者未運行則返回 503 錯誤。
    """
    log.info("獲取已訂閱符號列表。")
    if not manager.crypto_provider:
        log.error("加密貨幣提供者未運行，無法獲取已訂閱符號。")
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")

    return {
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols),
        "cached_symbols": list(manager.crypto_provider.get_latest_prices().keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    log.info(f"在 {config.api_host}:{config.api_port} 啟動增強型服務器。")
    uvicorn.run(
        "enhanced_main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level="info"
    )
