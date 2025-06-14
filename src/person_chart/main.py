import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, WebSocket, HTTPException

from .config import config
from .providers.crypto_provider import CryptoPriceProviderRealtime, InfluxDBManager

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class ConnectionManager:
    """
    (基本版) 管理 WebSocket 連接和加密貨幣價格提供者。
    """

    def __init__(self):
        """初始化 ConnectionManager 實例。"""
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        log.info("ConnectionManager (基本版) 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 連接。"""
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket 客戶端已連接。總連接數: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """斷開 WebSocket 連接。"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info(f"WebSocket 客戶端已斷開連接。總連接數: {len(self.active_connections)}")

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

    def start_crypto_provider(self):
        """初始化並啟動基本版加密貨幣價格提供者。"""
        log.info("啟動基本版加密貨幣價格提供者...")
        if not config.validate():
            raise ValueError("配置無效，請檢查 .env 文件。")

        influxdb_manager = InfluxDBManager(
            host=config.influxdb_host, token=config.influxdb_token, database=config.influxdb_database
        )
        self.crypto_provider = CryptoPriceProviderRealtime(
            influxdb_manager=influxdb_manager, message_callback=self.sync_broadcast
        )
        self.crypto_provider.start()
        self.crypto_provider.subscribe(symbol=config.binance_symbol, interval=config.binance_interval)
        log.info(f"已為 {config.binance_symbol} 啟動基本版加密貨幣價格提供者。")

    def stop_crypto_provider(self):
        """停止加密貨幣價格提供者。"""
        log.info("停止基本版加密貨幣價格提供者...")
        if self.crypto_provider:
            self.crypto_provider.stop()


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理。"""
    log.info("基本版應用程式啟動...")
    manager.loop = asyncio.get_running_loop()
    manager.start_crypto_provider()
    yield
    log.info("基本版應用程式關閉...")
    manager.stop_crypto_provider()


app = FastAPI(
    title="基本版加密貨幣價格串流 API",
    description="提供即時加密貨幣價格串流和 InfluxDB 儲存",
    version="1.0.0",
    lifespan=lifespan
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """用於即時價格串流的 WebSocket 端點。"""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        log.info("WebSocket 連接關閉。")
    finally:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """根端點，提供 API 資訊。"""
    return {
        "message": "基本版加密貨幣價格串流服務器",
        "version": "1.0.0",
        "status": "運行中",
        "websocket_endpoint": "/ws/price"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點。"""
    provider_status = "running" if manager.crypto_provider and manager.crypto_provider.binance_client else "stopped"
    return {
        "status": "healthy",
        "crypto_provider": provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "subscribed_symbols": manager.crypto_provider.subscribed_symbols if manager.crypto_provider else []
    }


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """訂閱新的交易對價格串流 (非持久化)。"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")
    manager.crypto_provider.subscribe(symbol, interval=interval)
    return {"status": "success", "message": f"已訂閱 {symbol.upper()}@{interval}"}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """取消訂閱交易對價格串流。"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")
    manager.crypto_provider.unsubscribe(symbol, interval=interval)
    return {"status": "success", "message": f"已取消訂閱 {symbol.upper()}@{interval}"}


if __name__ == "__main__":
    import uvicorn

    log.info(f"在 {config.api_host}:{config.api_port} 啟動基本版服務器。")
    uvicorn.run("main:app", host=config.api_host, port=config.api_port, reload=True)
