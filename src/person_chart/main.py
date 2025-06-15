import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, WebSocket, HTTPException

from person_chart.colored_logging import setup_colored_logging
from .config import config
from .providers.crypto_provider import CryptoPriceProviderRealtime, InfluxDBManager

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, WebSocket, HTTPException

from person_chart.colored_logging import setup_colored_logging
from .config import config
from .providers.crypto_provider import CryptoPriceProviderRealtime, InfluxDBManager

log = setup_colored_logging(level=logging.INFO)


class ConnectionManager:
    """
    管理 WebSocket 連接和加密貨幣價格提供者 (基本版)。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類負責管理所有連接到服務器的 WebSocket 客戶端，
        並協調加密貨幣價格數據的實時廣播。
        它還負責初始化和啟動/停止基本版加密貨幣價格提供者，
        確保數據流的順暢運行。
    """

    def __init__(self):
        """
        初始化 ConnectionManager 實例。
        設置活躍的 WebSocket 連接列表、加密貨幣提供者實例和事件循環。
        """
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        log.info("ConnectionManager (基本版) 初始化完成。")

    async def connect(self, websocket: WebSocket):
        """
        接受新的 WebSocket 連接。
        將新的 WebSocket 連接添加到活躍連接列表中，並記錄連接狀態。
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket 客戶端已連接。總連接數: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        斷開 WebSocket 連接。
        從活躍連接列表中移除指定的 WebSocket 連接，並記錄斷開狀態。
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info(f"WebSocket 客戶端已斷開連接。總連接數: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """
        將訊息廣播到所有連接的 WebSocket 客戶端。
        遍歷所有活躍連接，嘗試發送文本訊息。
        如果發送失敗，則將該客戶端標記為斷開連接並從列表中移除。
        """
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
        """
        在同步上下文中使用執行緒安全的方式廣播訊息。
        此方法允許從同步代碼中調用異步的廣播功能，
        通過將廣播任務提交到事件循環中執行來確保執行緒安全。
        """
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)

    def start_crypto_provider(self):
        """
        初始化並啟動基本版加密貨幣價格提供者。
        在啟動提供者之前，會先驗證應用程式配置。
        然後創建 InfluxDBManager 和 CryptoPriceProviderRealtime 實例，
        並啟動數據提供者，訂閱預設的交易對和時間間隔。
        """
        log.info("正在啟動基本版加密貨幣價格提供者...")
        if not config.validate():
            raise ValueError("配置無效，請檢查 .env 文件。")

        influxdb_manager = InfluxDBManager(
            host=config.influxdb_host, token=config.influxdb_token, database=config.influxdb_database
        )
        self.crypto_provider = CryptoPriceProviderRealtime(
            influxdb_manager=influxdb_manager, message_callback=self.sync_broadcast
        )
        self.crypto_provider.start()
        # 根據任務要求，移除 binance_symbol 和 binance_interval 的硬編碼訂閱
        # 這些將由客戶端請求時提供
        # self.crypto_provider.subscribe(symbol=config.binance_symbol, interval=config.binance_interval)
        log.info("基本版加密貨幣價格提供者已啟動。")

    def stop_crypto_provider(self):
        """
        停止加密貨幣價格提供者。
        如果加密貨幣提供者實例存在，則調用其 stop 方法來停止數據流。
        """
        log.info("正在停止基本版加密貨幣價格提供者...")
        if self.crypto_provider:
            self.crypto_provider.stop()


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理。
    此異步上下文管理器負責在應用程式啟動時初始化並啟動加密貨幣價格提供者，
    並在應用程式關閉時停止該提供者，確保資源的正確釋放。
    """
    log.info("基本版應用程式正在啟動...")
    manager.loop = asyncio.get_running_loop()
    manager.start_crypto_provider()
    yield
    log.info("基本版應用程式正在關閉...")
    manager.stop_crypto_provider()


app = FastAPI(
    title="基本版加密貨幣價格串流 API",
    description="提供即時加密貨幣價格串流和 InfluxDB 儲存",
    version="1.0.0",
    lifespan=lifespan
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """
    用於即時價格串流的 WebSocket 端點。
    接受新的 WebSocket 連接，並在連接期間持續接收訊息。
    當連接關閉或發生異常時，會調用 manager.disconnect 方法。
    """
    await manager.connect(websocket)
    try:
        while True:
            # 保持連接活躍，等待客戶端發送訊息
            await websocket.receive_text()
    except Exception:
        log.info("WebSocket 連接已關閉。")
    finally:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """
    根端點，提供 API 資訊。
    返回關於基本版加密貨幣價格串流服務器的基本信息，包括版本和 WebSocket 端點。
    """
    return {
        "message": "基本版加密貨幣價格串流服務器",
        "version": "1.0.0",
        "status": "運行中",
        "websocket_endpoint": "/ws/price"
    }


@app.get("/health")
async def health_check():
    """
    健康檢查端點。
    返回服務器的健康狀態，包括加密貨幣提供者的運行狀態、
    活躍的 WebSocket 連接數以及已訂閱的交易對列表。
    """
    provider_status = "運行中" if manager.crypto_provider and manager.crypto_provider.binance_client else "已停止"
    return {
        "status": "健康",
        "crypto_provider": provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "subscribed_symbols": manager.crypto_provider.subscribed_symbols if manager.crypto_provider else []
    }


@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """
    訂閱新的交易對價格串流 (非持久化)。
    允許客戶端訂閱指定交易對和時間間隔的實時價格數據。
    如果加密貨幣提供者未初始化，則返回 503 錯誤。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")
    manager.crypto_provider.subscribe(symbol, interval=interval)
    return {"status": "成功", "message": f"已訂閱 {symbol.upper()}@{interval}"}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """
    取消訂閱交易對價格串流。
    允許客戶端取消訂閱指定交易對和時間間隔的實時價格數據。
    如果加密貨幣提供者未初始化，則返回 503 錯誤。
    """
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="加密貨幣提供者未初始化")
    manager.crypto_provider.unsubscribe(symbol, interval=interval)
    return {"status": "成功", "message": f"已取消訂閱 {symbol.upper()}@{interval}"}


if __name__ == "__main__":
    import uvicorn

    log.info(f"正在 {config.api_host}:{config.api_port} 啟動基本版服務器。")
    uvicorn.run("main:app", host=config.api_host, port=config.api_port, reload=True)
