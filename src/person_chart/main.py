import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict

from fastapi import FastAPI, WebSocket, HTTPException, Query

from person_chart.colored_logging import setup_colored_logging
from person_chart.data_models import PriceData
from person_chart.tools.time_unity import interval_to_seconds
from .config import config
from .providers.crypto_provider import CryptoPriceProviderRealtime, InfluxDBManager
from .services.database_manager import SubscriptionRepository

log = setup_colored_logging(level=logging.INFO)


class ConnectionManager:
    """
    管理 WebSocket 連接和加密貨幣價格提供者 (基本版)。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-16 01:17:00
    版本號: 0.7.0
    用途說明:
        此類負責管理所有連接到服務器的 WebSocket 客戶端，
        並協調加密貨幣價格數據的實時廣播。
        使用虛擬貨幣提供者核心，能夠在後台抓取、聚合並將所有時間週期的 K 線數據存儲到 InfluxDB。
        同時，它為連接的客戶端提供實時的、內存中的 K 線聚合功能。
        它還管理持久化訂閱，確保服務重啟後自動恢復數據收集。
    """

    def __init__(self):
        """
        初始化 ConnectionManager 實例。
        """
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.subscription_repo: Optional[SubscriptionRepository] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.base_interval_seconds = interval_to_seconds(config.binance_base_interval)
        log.info("ConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket, symbol: str, interval: str):
        """
        接受新的 WebSocket 連接並設定其聚合需求。
        """
        await websocket.accept()
        target_interval_seconds = interval_to_seconds(interval)
        if target_interval_seconds < self.base_interval_seconds or target_interval_seconds % self.base_interval_seconds != 0:
            log.warning(
                f"客戶端請求的間隔 '{interval}' 對於符號 '{symbol}' 無效。它必須是基礎間隔 '{config.binance_base_interval}' 的倍數。正在關閉連接。")
            await websocket.close(code=1008, reason="Invalid interval")
            return

        self.active_connections[websocket] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "interval_seconds": target_interval_seconds,
            "buffer": [],
        }
        log.info(f"WebSocket 客戶端已連接，訂閱 {symbol}@{interval}。總連接數: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        斷開 WebSocket 連接。
        """
        if websocket in self.active_connections:
            sub_details = self.active_connections.pop(websocket)
            log.info(
                f"WebSocket 客戶端已斷開連接，訂閱 {sub_details['symbol']}@{sub_details['interval']}。總連接數: {len(self.active_connections)}")

    def _update_and_get_aggregate(self, sub_details: Dict, base_kline: PriceData) -> PriceData:
        """
        根據基礎 K 線更新並返回為 WebSocket 客戶端聚合的 K 線數據。
        """
        buffer = sub_details["buffer"]
        interval_seconds = sub_details["interval_seconds"]

        base_timestamp = int(base_kline.timestamp.timestamp())
        time_bucket_start_ts = base_timestamp - (base_timestamp % interval_seconds)

        if buffer and int(buffer[0].timestamp.timestamp()) < time_bucket_start_ts:
            buffer.clear()

        buffer.append(base_kline)
        sub_details["buffer"] = [k for k in buffer if int(k.timestamp.timestamp()) >= time_bucket_start_ts]
        buffer = sub_details["buffer"]

        first_kline = buffer[0]
        last_kline = buffer[-1]

        return PriceData(
            symbol=base_kline.symbol,
            price=last_kline.close_price,
            timestamp=datetime.fromtimestamp(time_bucket_start_ts, tz=timezone.utc),
            open_price=first_kline.open_price,
            high_price=max(p.high_price for p in buffer),
            low_price=min(p.low_price for p in buffer),
            close_price=last_kline.close_price,
            volume=sum(p.volume for p in buffer),
            trade_count=sum(p.trade_count or 0 for p in buffer)
        )

    async def broadcast(self, base_price_data: PriceData):
        """
        將基礎價格數據廣播或聚合後廣播到所有客戶端。
        """
        if not self.active_connections:
            return

        tasks = []
        disconnected_clients = []

        for connection, sub in list(self.active_connections.items()):
            if sub["symbol"] != base_price_data.symbol:
                continue

            if sub["interval_seconds"] == self.base_interval_seconds:
                message_to_send = base_price_data
            else:
                message_to_send = self._update_and_get_aggregate(sub, base_price_data)

            if message_to_send:
                try:
                    payload = json.dumps({
                        "type": "price_update",
                        "data": message_to_send.to_dict(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    tasks.append(asyncio.create_task(connection.send_text(payload)))
                except Exception:
                    disconnected_clients.append(connection)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    conn_to_disconnect = list(self.active_connections.keys())[i]
                    if conn_to_disconnect not in disconnected_clients:
                        disconnected_clients.append(conn_to_disconnect)

        for client in disconnected_clients:
            self.disconnect(client)

    def sync_broadcast(self, message: str):
        """
        從 Provider 接收 JSON 訊息，解析後交給異步 broadcast 處理。
        """
        if self.loop and self.loop.is_running():
            try:
                msg_data = json.loads(message)
                if msg_data.get("type") == "price_update":
                    price_data_dict = msg_data["data"]
                    price_data_dict["timestamp"] = datetime.fromisoformat(price_data_dict["timestamp"])
                    base_price_data = PriceData(**price_data_dict)
                    asyncio.run_coroutine_threadsafe(self.broadcast(base_price_data), self.loop)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                log.error(f"處理廣播訊息失敗: {e}")

    def load_and_subscribe(self):
        """
        從數據庫加載並訂閱持久化的符號。
        """
        if not self.crypto_provider or not self.subscription_repo:
            log.warning("提供者或倉庫未初始化，無法加載訂閱。")
            return

        subscriptions = self.subscription_repo.get_all_subscriptions()
        log.info(f"從資料庫找到 {len(subscriptions)} 個持久化訂閱。")
        if subscriptions:
            log.info(f"自動訂閱的交易對: {[sub['symbol'] for sub in subscriptions]}")
            for sub in subscriptions:
                log.debug(f"正在訂閱 {sub['symbol']}...")
                self.crypto_provider.subscribe(symbol=sub['symbol'])

    def start_crypto_provider(self):
        """
        初始化並啟動加密貨幣價格提供者核心。
        """
        log.info("正在啟動基本版服務器...")
        if not config.validate():
            raise ValueError("配置無效，請檢查 .env 文件。")

        # 使用 InfluxDB 管理器
        influxdb_manager = InfluxDBManager(
            host=config.influxdb_host, token=config.influxdb_token,
            database=config.influxdb_database, batch_size=200
        )

        self.subscription_repo = SubscriptionRepository(
            db_type=config.db_type, db_path=config.db_path, db_url=config.db_url
        )

        self.crypto_provider = CryptoPriceProviderRealtime(
            influxdb_manager=influxdb_manager,
            message_callback=self.sync_broadcast
        )
        self.crypto_provider.start()
        self.load_and_subscribe()
        log.info("基本版服務器已啟動。")

    def stop_crypto_provider(self):
        """
        停止加密貨幣價格提供者。
        """
        log.info("正在停止數據提供者核心...")
        if self.crypto_provider:
            self.crypto_provider.stop()


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理。
    """
    log.info("基本版應用程式正在啟動...")
    manager.loop = asyncio.get_running_loop()
    manager.start_crypto_provider()
    yield
    log.info("基本版應用程式正在關閉...")
    manager.stop_crypto_provider()


app = FastAPI(
    title="基本版加密貨幣價格串流 API",
    description="提供即時加密貨幣價格串流、後台聚合數據存儲、持久化訂閱和實時 K 線聚合廣播",
    version="1.0.1",
    lifespan=lifespan
)


@app.websocket("/ws/price")
async def websocket_endpoint(
        websocket: WebSocket,
        symbol: str = Query(...),
        interval: str = Query(config.binance_base_interval)
):
    """
    用於即時價格串流的 WebSocket 端點。
    客戶端可以通過此端點連接並接收指定交易對和時間間隔的實時 K 線數據。
    服務器會根據請求的間隔進行數據聚合。
    """
    await manager.connect(websocket, symbol, interval)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        log.info("WebSocket 連接已關閉。")
    finally:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """
    根端點，提供 API 資訊。
    """
    return {
        "message": "基本版加密貨幣價格串流服務器",
        "version": "1.0.0",
        "status": "running",
        "websocket_endpoint": "/ws/price?symbol=<symbol>&interval=<interval>"
    }


@app.get("/health")
async def health_check():
    """
    healthy檢查端點。
    """
    provider_status = "running" if manager.crypto_provider and manager.crypto_provider.binance_client else "stopped"
    return {
        "status": "healthy",
        "crypto_provider": provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "subscribed_streams": manager.crypto_provider.subscribed_symbols if manager.crypto_provider else []
    }


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str):
    """
    訂閱新的交易對，並持久化該訂閱。
    服務器將訂閱基礎數據流，並在後台自動聚合和存儲。
    """
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")
    manager.crypto_provider.subscribe(symbol)
    manager.subscription_repo.add_subscription(symbol)
    return {"status": "成功", "message": f"已訂閱 {symbol.upper()} 的基礎數據流並已持久化。"}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str):
    """
    取消訂閱交易對，並移除持久化訂閱。
    """
    if not manager.crypto_provider or not manager.subscription_repo:
        raise HTTPException(status_code=503, detail="服務未完全初始化")
    manager.crypto_provider.unsubscribe(symbol)
    manager.subscription_repo.remove_subscription(symbol)
    return {"status": "成功", "message": f"已取消訂閱 {symbol.upper()} 的基礎數據流並已移除持久化。"}


if __name__ == "__main__":
    import uvicorn

    log.info(f"正在 {config.api_host}:{config.api_port} 啟動基本版服務器。")
    uvicorn.run("main:app", host=config.api_host, port=config.api_port, reload=True)