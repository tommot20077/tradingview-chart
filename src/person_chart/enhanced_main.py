import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from person_chart.config import config
from person_chart.data_models import PriceData
from person_chart.providers.binance_provider import CryptoPriceProviderRealtime, InfluxDBManager
from person_chart.services.kafka_manager import kafka_manager, _KAFKA_AVAILABLE
from person_chart.storage.subscription_repo import SubscriptionRepository
from person_chart.utils.colored_logging import setup_colored_logging
from person_chart.utils.time_unity import interval_to_seconds

log = setup_colored_logging(level=logging.INFO)


class EnhancedConnectionManager:
    """
    管理 WebSocket 連接、加密貨幣價格提供者和後端服務。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-17 19:30:00
    版本號: 0.6.2
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
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self._kafka_thread: Optional[threading.Thread] = None
        self.subscription_repo: Optional[SubscriptionRepository] = None
        self._stop_event = threading.Event()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.base_interval_seconds = interval_to_seconds(config.binance_base_interval)
        log.info("EnhancedConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """
        接受新的 WebSocket 連接。
        此方法會接受一個新的 WebSocket 連接，但不會立即設定訂閱。
        客戶端需要發送訂閱消息來指定要訂閱的交易對和時間間隔。
        """
        await websocket.accept()
        self.active_connections[websocket] = {
            "subscriptions": {},  # 存儲多個訂閱: {"stream_key": {subscription_info}}
        }
        log.info(f"WebSocket 客戶端已連接。總連接數: {len(self.active_connections)}")

    async def _initialize_current_kline(self, symbol: str, interval_seconds: int) -> Optional[PriceData]:
        """
        初始化當前時間窗口的聚合K線狀態。
        
        此方法會查詢數據庫中當前時間窗口內的基礎數據，
        並在內存中聚合成對應間隔的K線，確保WebSocket連接時
        能夠正確銜接之前累積的數據，避免數據跳空。
        
        參數:
            symbol (str): 交易對符號
            interval_seconds (int): 目標間隔的秒數
            
        返回:
            Optional[PriceData]: 當前時間窗口的聚合K線，如果沒有數據則返回None
        """
        if not self.crypto_provider:
            return None

        try:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            current_timestamp = int(now.timestamp())

            time_bucket_start = current_timestamp - (current_timestamp % interval_seconds)
            window_start = datetime.fromtimestamp(time_bucket_start, tz=timezone.utc)

            base_data = self.crypto_provider.analyzer.get_price_data(
                symbol=symbol,
                start_time=window_start,
                end_time=now
            )

            if base_data.empty:
                log.debug(f"當前時間窗口內沒有找到 {symbol} 的基礎數據")
                return None

            agg_kline = PriceData(
                symbol=symbol,
                price=float(base_data['close'].iloc[-1]),
                timestamp=window_start,
                open_price=float(base_data['open'].iloc[0]),
                high_price=float(base_data['high'].max()),
                low_price=float(base_data['low'].min()),
                close_price=float(base_data['close'].iloc[-1]),
                volume=float(base_data['volume'].sum()),
                trade_count=int(base_data['trade_count'].sum()) if 'trade_count' in base_data.columns else 0
            )

            log.info(f"成功初始化 {symbol} 當前時間窗口的聚合K線: {window_start}")
            return agg_kline

        except Exception as e:
            log.error(f"初始化 {symbol} 當前K線狀態失敗: {e}")
            return None

    async def handle_subscription_message(self, websocket: WebSocket, message: dict):
        """
        處理客戶端訂閱消息。
        支援 subscribe 和 unsubscribe 動作，以及不同的 symbol 和 interval。
        """
        try:
            action = message.get("action")
            stream = message.get("stream")

            if not action or not stream:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "缺少必要的 action 或 stream 參數"
                }))
                return

            # 解析 stream 格式: symbol@kline_interval
            if "@kline_" not in stream:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "stream 格式無效，應為 symbol@kline_interval"
                }))
                return

            symbol, interval_part = stream.split("@kline_")
            symbol = symbol.upper()
            interval = interval_part

            # 驗證間隔
            target_interval_seconds = interval_to_seconds(interval)
            if target_interval_seconds < self.base_interval_seconds or target_interval_seconds % self.base_interval_seconds != 0:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"間隔 '{interval}' 無效，必須是基礎間隔 '{config.binance_base_interval}' 的倍數"
                }))
                return

            conn_info = self.active_connections.get(websocket)
            if not conn_info:
                return

            subscriptions = conn_info["subscriptions"]

            if action == "subscribe":
                # 新增或更新訂閱
                current_agg_kline = await self._initialize_current_kline(symbol, target_interval_seconds)

                subscriptions[stream] = {
                    "symbol": symbol,
                    "interval": interval,
                    "interval_seconds": target_interval_seconds,
                    "current_agg_kline": current_agg_kline
                }

                # 確保後端已訂閱該 symbol
                if self.crypto_provider and symbol not in self.crypto_provider.subscribed_symbols:
                    self.crypto_provider.subscribe(symbol)
                    if self.subscription_repo:
                        self.subscription_repo.add_subscription(symbol)

                await websocket.send_text(json.dumps({
                    "type": "subscription_success",
                    "stream": stream,
                    "message": f"已訂閱 {stream}"
                }))

                log.info(f"WebSocket 客戶端訂閱: {stream}")

            elif action == "unsubscribe":
                # 取消訂閱
                if stream in subscriptions:
                    del subscriptions[stream]

                    await websocket.send_text(json.dumps({
                        "type": "unsubscription_success",
                        "stream": stream,
                        "message": f"已取消訂閱 {stream}"
                    }))

                    log.info(f"WebSocket 客戶端取消訂閱: {stream}")
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"未找到訂閱 {stream}"
                    }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"不支援的動作: {action}"
                }))

        except Exception as e:
            log.error(f"處理訂閱消息失敗: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"處理訂閱消息失敗， 請檢查訂閱的格式和參數"
            }))

    def disconnect(self, websocket: WebSocket):
        """
        斷開 WebSocket 連接。
        從活躍連接字典中移除指定的 WebSocket 連接，並記錄斷開狀態。
        """
        if websocket in self.active_connections:
            conn_info = self.active_connections.pop(websocket)
            subscriptions = conn_info.get("subscriptions", {})
            if subscriptions:
                log.info(f"WebSocket 客戶端已斷開連接，取消 {len(subscriptions)} 個訂閱。總連接數: {len(self.active_connections)}")
            else:
                log.info(f"WebSocket 客戶端已斷開連接。總連接數: {len(self.active_connections)}")

    def _update_and_get_aggregate(self, sub_details: Dict, base_kline: PriceData) -> Optional[PriceData]:
        """
        使用狀態管理方法更新或創建聚合 K 線。

        此方法取代了原有的緩衝區聚合邏輯，改為更高效的狀態管理。
        它檢查傳入的基礎 K 線是否屬於新的時間窗口。
        如果是，則創建一個新的聚合 K 線。
        如果不是，則更新現有的聚合 K 線。
        只有當一個時間窗口的第一筆數據到達時，才會返回聚合 K 線，之後只更新不返回，直到下一個窗口。
        （註：此處邏輯簡化為每次都返回更新後的K線，以提供更即時的更新）
        """
        interval_seconds = sub_details["interval_seconds"]
        current_agg_kline: Optional[PriceData] = sub_details.get("current_agg_kline")

        base_timestamp = int(base_kline.timestamp.timestamp())
        time_bucket_ts = base_timestamp - (base_timestamp % interval_seconds)
        time_bucket_dt = datetime.fromtimestamp(time_bucket_ts, tz=timezone.utc)

        if current_agg_kline is None or current_agg_kline.timestamp != time_bucket_dt:
            new_agg_kline = PriceData(
                symbol=base_kline.symbol,
                price=base_kline.close_price,
                timestamp=time_bucket_dt,
                open_price=base_kline.open_price,
                high_price=base_kline.high_price,
                low_price=base_kline.low_price,
                close_price=base_kline.close_price,
                volume=base_kline.volume,
                trade_count=base_kline.trade_count or 0
            )
            sub_details["current_agg_kline"] = new_agg_kline
            return new_agg_kline
        else:
            current_agg_kline.high_price = max(current_agg_kline.high_price, base_kline.high_price)
            current_agg_kline.low_price = min(current_agg_kline.low_price, base_kline.low_price)
            current_agg_kline.close_price = base_kline.close_price
            current_agg_kline.price = base_kline.close_price
            current_agg_kline.volume += base_kline.volume
            current_agg_kline.trade_count = (current_agg_kline.trade_count or 0) + (base_kline.trade_count or 0)
            return current_agg_kline

    async def broadcast(self, base_price_data: PriceData):
        """
        將基礎價格數據廣播或聚合後廣播到所有客戶端。
        此方法會遍歷所有活躍的 WebSocket 連接，根據客戶端請求的間隔，
        決定是直接廣播基礎價格數據，還是將數據緩衝並聚合成更大的 K 線數據後再廣播。
        如果發送失敗，則將該客戶端標記為斷開連接並從列表中移除。
        """
        if not self.active_connections:
            return

        tasks = []
        disconnected_clients = []

        for connection, conn_info in list(self.active_connections.items()):
            subscriptions = conn_info.get("subscriptions", {})

            for stream_key, sub_details in subscriptions.items():
                if sub_details["symbol"] != base_price_data.symbol:
                    continue

                if sub_details["interval_seconds"] == self.base_interval_seconds:
                    message_to_send = base_price_data
                else:
                    message_to_send = self._update_and_get_aggregate(sub_details, base_price_data)

                if message_to_send:
                    try:
                        payload = json.dumps({
                            "type": "price_update",
                            "data": message_to_send.to_dict(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "stream": stream_key
                        })
                        tasks.append(asyncio.create_task(connection.send_text(payload)))
                    except Exception:
                        if connection not in disconnected_clients:
                            disconnected_clients.append(connection)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 找到對應的連接並標記為斷開
                    task_index = 0
                    for connection in self.active_connections.keys():
                        conn_subscriptions = self.active_connections[connection].get("subscriptions", {})
                        for stream_key, sub_details in conn_subscriptions.items():
                            if sub_details["symbol"] == base_price_data.symbol:
                                if task_index == i and connection not in disconnected_clients:
                                    disconnected_clients.append(connection)
                                    break
                                task_index += 1
                        if connection in disconnected_clients:
                            break

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
                log.debug(f"從 Kafka 收到消息: {message.value}")
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

        influxdb_manager = InfluxDBManager(
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
            message_cb = None
            self._kafka_thread = threading.Thread(target=self._kafka_consumer_worker, daemon=True)
            self._kafka_thread.start()
        else:
            if config.kafka_enabled:
                log.warning("Kafka 已在配置中啟用，但 kafka-python 庫不可用或管理器初始化失敗。將使用直接回調模式。")
            log.info("Kafka 模式已禁用。將使用直接回調模式。")

        self.crypto_provider = CryptoPriceProviderRealtime(
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
        log.info(f"自動訂閱的交易對: {[sub['symbol'] for sub in subscriptions]}")
        for sub in subscriptions:
            log.debug(f"正在訂閱 {sub['symbol']}...")
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
            self.kafka_consumer.close(autocommit=False)
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
    version="1.0.2",
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
async def websocket_endpoint(websocket: WebSocket):
    """
    用於即時價格串流的 WebSocket 端點。
    客戶端可以通過此端點連接並發送訂閱消息來指定要訂閱的交易對和時間間隔。
    支援動態訂閱切換，包括不同的 symbol 和 interval。
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await manager.handle_subscription_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "JSON 格式無效"
                }))
    except Exception as e:
        log.info(f"WebSocket 連接已關閉: {e}")
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
        start: int,
        end: int,
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
    return {"status": "success", "message": f"已訂閱 {symbol.upper()} 並已持久化。"}


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
    return {"status": "success", "message": f"已取消訂閱 {symbol.upper()} 並已移除持久化。"}


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
