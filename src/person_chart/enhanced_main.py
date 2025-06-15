import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, WebSocket, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from person_chart.data_models import PriceData
from person_chart.tools.time_unity import interval_to_seconds
from .config import config
from .providers.enhanced_crypto_provider import EnhancedCryptoPriceProviderRealtime, EnhancedInfluxDBManager
from .services.kafka_manager import kafka_manager, _KAFKA_AVAILABLE
from .services.database_manager import SubscriptionRepository
from .colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)


class EnhancedConnectionManager:
    """
    管理 WebSocket 連接、加密貨幣價格提供者和後端服務。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類負責處理所有連接到服務器的 WebSocket 客戶端，
        並協調加密貨幣價格數據的實時廣播。
        它還負責初始化和啟動/停止所有後端服務，包括加密貨幣價格提供者、
        Kafka 消費者（如果啟用）以及訂閱數據庫管理，確保數據流的順暢運行和持久化。
        此外，它還支持 K 線數據的聚合處理，以滿足不同時間尺度的數據需求。
    """

    def __init__(self):
        """
        初始化 EnhancedConnectionManager 實例。
        設置活躍的 WebSocket 連接字典、加密貨幣提供者實例、Kafka 相關組件、
        訂閱倉庫實例、停止事件和事件循環。
        同時計算基礎時間間隔的秒數，用於 K 線聚合。
        """
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.crypto_provider: Optional[EnhancedCryptoPriceProviderRealtime] = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self._kafka_thread: Optional[threading.Thread] = None
        self.subscription_repo: Optional[SubscriptionRepository] = None
        self._stop_event = threading.Event()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.base_interval_seconds = interval_to_seconds(config.binance_base_interval)
        log.info("EnhancedConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket, symbol: str, interval: str):
        """
        接受新的 WebSocket 連接並設定其聚合需求。
        此方法會接受一個新的 WebSocket 連接，並根據客戶端請求的交易對和時間間隔，
        計算所需的聚合乘數，並將連接信息存儲在 active_connections 字典中，
        同時初始化用於自定義聚合的緩衝區。
        """
        await websocket.accept()

        target_interval_seconds = interval_to_seconds(interval)
        multiplier = 1
        is_custom = False

        if target_interval_seconds > self.base_interval_seconds and target_interval_seconds % self.base_interval_seconds == 0:
            multiplier = target_interval_seconds // self.base_interval_seconds
            is_custom = True

        self.active_connections[websocket] = {
            "symbol": symbol,
            "interval": interval,
            "is_custom": is_custom,
            "multiplier": multiplier,
            "buffer": []  # 用於自定義聚合的緩衝區
        }
        log.info(f"WebSocket 客戶端已連接，訂閱 {symbol}@{interval}。總連接數: {len(self.active_connections)}")

    def _aggregate_buffer(self, buffer: List[PriceData]) -> PriceData | None:
        """
        將緩衝區中的 PriceData 聚合成單個 PriceData。
        此方法接收一個 PriceData 對象列表，並將其聚合成一個代表 K 線數據的單個 PriceData 對象。
        聚合邏輯包括使用第一筆數據的開盤價、最後一筆數據的收盤價和時間戳，
        以及緩衝區中所有數據的最高價、最低價、總交易量和總交易數量。
        """
        if not buffer:
            return None

        first = buffer[0]
        last = buffer[-1]

        return PriceData(
            symbol=first.symbol,
            price=last.price,
            timestamp=last.timestamp,  # 使用最後一筆數據的時間戳
            open_price=first.open_price,
            high_price=max(p.high_price for p in buffer),
            low_price=min(p.low_price for p in buffer),
            close_price=last.close_price,
            volume=sum(p.volume for p in buffer),
            trade_count=sum(p.trade_count or 0 for p in buffer)
        )

    def disconnect(self, websocket: WebSocket):
        """
        斷開 WebSocket 連接。
        從活躍連接字典中移除指定的 WebSocket 連接，並記錄斷開狀態。
        """
        if websocket in self.active_connections:
            sub_details = self.active_connections.pop(websocket)
            log.info(
                f"WebSocket 客戶端已斷開連接，訂閱 {sub_details['symbol']}@{sub_details['interval']}。總連接數: {len(self.active_connections)}")

    async def broadcast(self, base_price_data: PriceData):
        """
        將基礎價格數據廣播或聚合後廣播到所有客戶端。
        此方法會遍歷所有活躍的 WebSocket 連接，根據客戶端請求的間隔，
        決定是直接廣播基礎價格數據，還是將數據緩衝並聚合成更大的 K 線數據後再廣播。
        如果發送失敗，則將該客戶端標記為斷開連接並從列表中移除。
        """
        if not self.active_connections:
            return

        disconnected_clients = []
        # 迭代項目的副本，因為 disconnect 可能會修改字典
        for connection, sub in list(self.active_connections.items()):
            if sub["symbol"] != base_price_data.symbol:
                continue

            message_to_send = None

            # 情況 1: 客戶端直接需要基礎間隔的數據
            # `is_custom` 為 False 且 `interval` 與基礎間隔匹配
            if not sub["is_custom"] and sub["interval"] == config.binance_base_interval:
                message_to_send = base_price_data

            # 情況 2: 客戶端需要一個聚合後的時間間隔
            # `is_custom` 為 True
            elif sub["is_custom"]:
                sub["buffer"].append(base_price_data)
                if len(sub["buffer"]) >= sub["multiplier"]:
                    aggregated_data = self._aggregate_buffer(sub["buffer"])
                    if aggregated_data:
                        # 修正時間戳：將其對齊到聚合區間的起始時間
                        # 這對於圖表正確放置 K 線至關重要
                        interval_seconds = sub["multiplier"] * self.base_interval_seconds
                        kline_timestamp = int(aggregated_data.timestamp.timestamp())
                        time_bucket = kline_timestamp - (kline_timestamp % interval_seconds)
                        aggregated_data.timestamp = datetime.fromtimestamp(time_bucket, tz=timezone.utc)

                        message_to_send = aggregated_data
                    sub["buffer"] = []  # 清空緩衝區

            # 情況 3 (隱含): 客戶端請求了不支持的時間間隔。
            # `is_custom` 為 False 且 `interval` 與基礎間隔不匹配。不會發送任何消息。

            if message_to_send:
                try:
                    payload = json.dumps({
                        "type": "price_update",
                        "data": message_to_send.to_dict(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    await connection.send_text(payload)
                except Exception:
                    # 可能的各種連接錯誤
                    disconnected_clients.append(connection)

        for client in disconnected_clients:
            self.disconnect(client)

    def sync_broadcast(self, message: str):
        """
        從 Provider 接收 JSON 訊息，解析後交給異步 broadcast 處理。
        此方法用於從同步上下文接收包含基礎間隔數據的 JSON 訊息，
        將其解析為 PriceData 對象，然後將廣播任務提交到異步事件循環中執行，
        以確保數據的實時分發。
        """
        if self.loop and self.loop.is_running():
            try:
                msg_data = json.loads(message)
                if msg_data.get("type") == "price_update":
                    price_data_dict = msg_data["data"]
                    price_data_dict["timestamp"] = datetime.fromisoformat(price_data_dict["timestamp"])
                    base_price_data = PriceData(**price_data_dict)
                    asyncio.run_coroutine_threadsafe(self.broadcast(base_price_data), self.loop)
            except (json.JSONDecodeError, TypeError) as e:
                log.error(f"處理廣播訊息失敗: {e}")

    def _kafka_consumer_worker(self):
        """
        在背景執行緒中運行的 Kafka 消費者。
        此方法作為一個獨立的執行緒運行，負責從 Kafka 主題消費訊息。
        它會持續監聽 Kafka 消息，並將接收到的消息通過 sync_broadcast 方法轉發給 WebSocket 客戶端。
        當停止事件被設置時，此執行緒會安全退出。
        """
        log.info("Kafka 消費者工作執行緒已啟動。")
        try:
            if not self.kafka_consumer:
                log.warning("Kafka 消費者未初始化，工作執行緒將退出。")
                return

            for message in self.kafka_consumer:
                if self._stop_event.is_set():
                    break
                log.debug(f"從 Kafka 收到訊息: {message.value}")
                self.sync_broadcast(message.value)
        except Exception as e:
            if "KafkaConsumer is closed" == str(e):
                log.info("Kafka 消費者已關閉。")
            else:
                log.error(f"Kafka 消費者工作執行緒中發生錯誤: {e}")
        finally:
            log.info("Kafka 消費者工作執行緒已停止。")

    def start_services(self):
        """
        初始化並啟動所有後端服務。
        此方法負責在應用程式啟動時，根據配置初始化並啟動所有必要的後端服務，
        包括 InfluxDB 管理器、訂閱倉庫、Kafka 生產者和消費者（如果啟用），
        以及加密貨幣價格提供者。它還會從數據庫加載並訂閱持久化的交易對。
        """
        log.info("正在啟動所有後端服務...")
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
            log.info("Kafka 模式已禁用。將使用直接回調模式。")

        self.crypto_provider = EnhancedCryptoPriceProviderRealtime(
            influxdb_manager=influxdb_manager,
            message_callback=message_cb,
            kafka_producer=self.kafka_producer,
            kafka_topic=config.kafka_topic
        )
        self.crypto_provider.start()
        self.load_and_subscribe()

    def load_and_subscribe(self):
        """
        從數據庫加載並訂閱持久化的符號。
        此方法會從訂閱倉庫中獲取所有持久化的交易對，
        並調用加密貨幣提供者的 subscribe 方法來重新建立這些交易對的數據流訂閱。
        """
        if not self.crypto_provider or not self.subscription_repo:
            log.warning("提供者或倉庫未初始化，無法加載訂閱。")
            return

        subscriptions = self.subscription_repo.get_all_subscriptions()
        log.info(f"從資料庫找到 {len(subscriptions)} 個持久化訂閱。")
        for sub in subscriptions:
            log.info(f"自動訂閱: {sub['symbol']}")
            self.crypto_provider.subscribe(symbol=sub['symbol'])

    def stop_services(self):
        """
        停止所有後端服務。
        此方法負責在應用程式關閉時，安全地停止所有已啟動的後端服務，
        包括加密貨幣價格提供者、Kafka 消費者（如果啟用）以及相關的執行緒，
        確保資源的正確釋放。
        """
        log.info("正在停止所有後端服務...")
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
    """
    應用程式生命週期管理。
    此異步上下文管理器負責在應用程式啟動時初始化並啟動所有後端服務，
    並在應用程式關閉時安全地停止這些服務，確保資源的正確釋放。
    """
    log.info("應用程式正在啟動...")
    manager.loop = asyncio.get_running_loop()
    manager.start_services()
    yield
    log.info("應用程式正在關閉...")
    manager.stop_services()


app = FastAPI(
    title="增強型加密貨幣價格串流 API",
    description="具有增強型 InfluxDB 儲存、監控和持久化訂閱的即時加密貨幣價格串流",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/price")
async def websocket_endpoint(
        websocket: WebSocket,
        symbol: str = Query(...),
        interval: str = Query("1m")
):
    """
    用於即時價格串流的 WebSocket 端點。
    客戶端可以通過此端點連接並接收指定交易對和時間間隔的實時 K 線數據。
    服務器會根據請求的間隔進行數據聚合。
    """
    await manager.connect(websocket, symbol, interval)
    try:
        while True:
            await websocket.receive_text()  # 保持連接活躍
    except Exception:
        log.info("WebSocket 連接已關閉。")
    finally:
        manager.disconnect(websocket)


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    """
    提供 Web 監控儀表板。
    此根端點返回靜態文件 `static/index.html`，作為 Web 監控儀表板的入口。
    """
    return FileResponse('./static/index.html')


@app.get("/health")
async def health_check():
    """
    健康檢查端點，返回系統狀態。
    提供服務器的健康狀態概覽，包括加密貨幣提供者的運行狀態、
    活躍的 WebSocket 連接數以及當前時間戳。
    """
    provider_status = "運行中" if manager.crypto_provider and manager.crypto_provider.binance_client else "已停止"
    return {
        "status": "健康",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crypto_provider_status": provider_status,
        "active_websocket_connections": len(manager.active_connections),
    }


@app.get("/status")
async def get_detailed_stats():
    """
    獲取詳細的系統和提供者統計數據。
    返回加密貨幣提供者的詳細運行統計信息，包括消息處理、寫入數據庫等性能指標。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return manager.crypto_provider.get_stats()


@app.get("/prices")
async def get_latest_prices():
    """
    獲取所有已快取符號的最新價格。
    返回所有已訂閱並緩存的交易對的最新價格數據。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return manager.crypto_provider.get_latest_prices()


@app.get("/history")
async def get_history(
        symbol: str,
        interval: str,
        start: int,  # UNIX timestamp
        end: int,  # UNIX timestamp
        limit: int = 1000,
        offset: int = 0
):
    """
    獲取歷史 K 線數據（分頁）。
    允許客戶端查詢指定交易對、時間間隔和時間範圍內的歷史 K 線數據，
    並支持通過 limit 和 offset 參數進行分頁查詢。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")

    start_dt = datetime.fromtimestamp(start, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(end, tz=timezone.utc)

    data = manager.crypto_provider.get_historical_data(symbol, interval, start_dt, end_dt, limit, offset)
    return data


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str):
    """
    訂閱新的交易對，並持久化該訂閱。
    此端點允許客戶端訂閱指定交易對的實時數據流，
    並將該訂閱信息持久化到數據庫中，以便服務器重啟後能自動恢復訂閱。
    間隔設定由伺服端管理，用戶無需提供。
    """
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")

    manager.crypto_provider.subscribe(symbol)
    manager.subscription_repo.add_subscription(symbol)
    return {"status": "成功", "message": f"已訂閱 {symbol.upper()} 並已持久化。"}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str):
    """
    取消訂閱交易對，並移除持久化訂閱。
    此端點允許客戶端取消訂閱指定交易對的實時數據流，
    並從數據庫中移除該訂閱信息。
    """
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")

    manager.crypto_provider.unsubscribe(symbol)
    manager.subscription_repo.remove_subscription(symbol)
    return {"status": "成功", "message": f"已取消訂閱 {symbol.upper()} 並已移除持久化。"}


@app.get("/symbols")
async def get_subscribed_symbols():
    """
    獲取當前已訂閱的符號列表。
    返回當前加密貨幣提供者已訂閱的數據流列表，
    以及已緩存的交易對列表和當前時間戳。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未運行")
    return {
        "subscribed_streams": manager.crypto_provider.subscribed_symbols,
        "cached_symbols": list(manager.crypto_provider.get_latest_prices().keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    log.info(f"正在 {config.api_host}:{config.api_port} 啟動增強型服務器。")
    uvicorn.run("enhanced_main:app", host=config.api_host, port=config.api_port, reload=True)
