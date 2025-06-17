import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict

from fastapi import FastAPI, WebSocket, HTTPException

from person_chart.config import config
from person_chart.data_models import PriceData
from person_chart.providers.binance_provider import CryptoPriceProviderRealtime, InfluxDBManager
from person_chart.storage.subscription_repo import SubscriptionRepository
from person_chart.utils.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)


class ConnectionManager:
    """
    管理 WebSocket 連接和加密貨幣價格提供者 (基本版)。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-17 16:00:00
    版本號: 0.7.1
    用途說明:
        此類負責管理所有連接到服務器的 WebSocket 客戶端，
        並協調加密貨幣價格數據的實時廣播。
        使用虛擬貨幣提供者核心，能夠在後台抓取、聚合並將所有時間週期的 K 線數據存儲到 InfluxDB。
        同時，它為連接的客戶端提供實時的、內存中的 K 線聚合功能。
        它還管理持久化訂閱，確保服務重啟後自動恢復數據收集。
    """

    def __init__(self):
        """
        初始化基本版 ConnectionManager 實例。
        設定簡化的連接管理和單一訂閱支援。
        """
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.subscription_repo: Optional[SubscriptionRepository] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        log.info("基本版 ConnectionManager 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """
        接受新的 WebSocket 連接。
        基本版簡化設計：只支援單一訂閱，固定 1m 間隔。
        """
        await websocket.accept()
        self.active_connections[websocket] = {
            "current_symbol": None,  # 當前訂閱的交易對
        }
        log.info(f"WebSocket 客戶端已連接。總連接數: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        斷開 WebSocket 連接。
        """
        if websocket in self.active_connections:
            conn_info = self.active_connections.pop(websocket)
            current_symbol = conn_info.get("current_symbol")
            if current_symbol:
                log.info(f"WebSocket 客戶端已斷開連接，訂閱 {current_symbol}@1m。總連接數: {len(self.active_connections)}")
            else:
                log.info(f"WebSocket 客戶端已斷開連接。總連接數: {len(self.active_connections)}")


    async def broadcast(self, base_price_data: PriceData):
        """
        將基礎價格數據廣播到所有客戶端。
        """
        if not self.active_connections:
            return

        tasks = []
        disconnected_clients = []

        for connection, conn_info in list(self.active_connections.items()):
            current_symbol = conn_info.get("current_symbol")
            if not current_symbol or current_symbol != base_price_data.symbol:
                continue

            try:
                payload = json.dumps({
                    "type": "price_update",
                    "data": base_price_data.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stream": f"{current_symbol.lower()}@kline_1m"
                })
                tasks.append(asyncio.create_task(connection.send_text(payload)))
            except Exception:
                disconnected_clients.append(connection)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_index = 0
                    for connection, conn_info in self.active_connections.items():
                        if conn_info.get("current_symbol") == base_price_data.symbol:
                            if task_index == i and connection not in disconnected_clients:
                                disconnected_clients.append(connection)
                                break
                            task_index += 1

        for client in disconnected_clients:
            self.disconnect(client)

    async def handle_subscription_message(self, websocket: WebSocket, message: dict):
        """
        處理客戶端訂閱消息。
        基本版限制：只支援 1m 間隔的單一訂閱，新訂閱會自動取代舊訂閱。
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

            if "@kline_" not in stream:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "stream 格式無效，應為 symbol@kline_interval"
                }))
                return

            symbol, interval_part = stream.split("@kline_")
            symbol = symbol.upper()
            interval = interval_part

            # 基本版限制：只支援 1m 間隔
            if interval != "1m":
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"基本版只支援 1m 間隔，不支援 '{interval}'"
                }))
                return

            conn_info = self.active_connections.get(websocket)
            if not conn_info:
                return

            if action == "subscribe":
                # 基本版：新訂閱自動取代舊訂閱
                old_symbol = conn_info.get("current_symbol")
                conn_info["current_symbol"] = symbol

                # 確保後端已訂閱該 symbol
                if self.crypto_provider and symbol not in self.crypto_provider.subscribed_symbols:
                    self.crypto_provider.subscribe(symbol)
                    if self.subscription_repo:
                        self.subscription_repo.add_subscription(symbol)

                success_message = f"已訂閱 {stream}"
                if old_symbol and old_symbol != symbol:
                    success_message += f"（已自動取代 {old_symbol}@kline_1m）"

                await websocket.send_text(json.dumps({
                    "type": "subscription_success",
                    "stream": stream,
                    "message": success_message
                }))

                log.info(f"WebSocket 客戶端訂閱: {stream} (基本版單一訂閱)")

            elif action == "unsubscribe":
                # 取消當前訂閱
                current_symbol = conn_info.get("current_symbol")
                if current_symbol:
                    conn_info["current_symbol"] = None

                    await websocket.send_text(json.dumps({
                        "type": "unsubscription_success",
                        "stream": stream,
                        "message": f"已取消訂閱 {stream}"
                    }))

                    log.info(f"WebSocket 客戶端取消訂閱: {stream}")
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "目前沒有活動訂閱"
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
                "message": f"處理訂閱消息失敗: {str(e)}"
            }))

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
    version="1.0.2",
    lifespan=lifespan
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """
    用於即時價格串流的 WebSocket 端點。
    客戶端可以通過此端點連接並發送訂閱消息來指定要訂閱的交易對和時間間隔。
    基本版只支援單一訂閱，新訂閱會自動取代舊訂閱。
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