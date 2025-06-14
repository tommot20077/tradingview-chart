import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI
from fastapi.websockets import WebSocket

from config import config
from crypto_provider import CryptoPriceProviderRealtime, InfluxDBManager

# 設定日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    管理 WebSocket 連接和加密貨幣價格提供者。
    負責處理客戶端連接、斷開連接、訊息廣播以及啟動/停止價格提供者。
    """

    def __init__(self):
        """
        初始化 ConnectionManager 實例。

        輸入:
            無。

        輸出:
            無。
        """
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: Optional[CryptoPriceProviderRealtime] = None
        self.loop = None
        logger.info("ConnectionManager 初始化完成。")

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
        logger.info(f"WebSocket 客戶端已連接。總連接數: {len(self.active_connections)}")

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
            logger.info(f"WebSocket 客戶端已斷開連接。總連接數: {len(self.active_connections)}")
        else:
            logger.warning("嘗試斷開未知的 WebSocket 連接。")

    async def broadcast(self, message: str):
        """
        將訊息廣播到所有連接的 WebSocket 客戶端。

        輸入:
            message (str): 要廣播的訊息字串。

        輸出:
            無。
        """
        if not self.active_connections:
            logger.debug("沒有活動的 WebSocket 連接，無需廣播。")
            return

        # 建立一個列表來追蹤失敗的連接
        failed_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"發送訊息到 WebSocket 客戶端失敗: {e}")
                failed_connections.append(connection)

        # 移除失敗的連接
        for failed_connection in failed_connections:
            self.disconnect(failed_connection)
        logger.info(
            f"已廣播訊息。成功發送: {len(self.active_connections) - len(failed_connections)}, 失敗: {len(failed_connections)}")

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
            logger.warning("事件循環未運行，無法安排廣播。")
            return

        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
            logger.debug("已安排同步廣播任務。")
        except Exception as e:
            logger.error(f"安排廣播失敗: {e}")

    def start_crypto_provider(self):
        """
        初始化並啟動加密貨幣價格提供者。
        它會驗證配置，建立 InfluxDB 管理器和價格提供者，然後啟動它並訂閱預設符號。

        輸入:
            self (ConnectionManager): ConnectionManager 實例本身。

        輸出:
            無。

        異常:
            ValueError: 如果配置無效則拋出。
            Exception: 如果啟動價格提供者失敗則拋出。
        """
        logger.info("啟動加密貨幣價格提供者...")
        try:
            # 驗證配置
            if not config.validate():
                logger.error("配置無效。請檢查您的 .env 檔案。")
                raise ValueError("配置無效")

            # 建立 InfluxDB 管理器
            influxdb_manager = InfluxDBManager(
                host=config.influxdb_host,
                token=config.influxdb_token,
                database=config.influxdb_database
            )

            # 建立加密貨幣價格提供者，帶有 WebSocket 廣播的訊息回調
            self.crypto_provider = CryptoPriceProviderRealtime(
                influxdb_manager=influxdb_manager,
                message_callback=self.sync_broadcast
            )

            # 啟動提供者
            self.crypto_provider.start()

            # 訂閱配置的符號
            self.crypto_provider.subscribe_symbol(
                symbol=config.binance_symbol,
                interval=config.binance_interval
            )

            logger.info(f"已為 {config.binance_symbol} 啟動加密貨幣價格提供者。")

        except Exception as e:
            logger.error(f"啟動加密貨幣價格提供者失敗: {e}")
            raise

    def stop_crypto_provider(self):
        """
        停止加密貨幣價格提供者。

        輸入:
            self (ConnectionManager): ConnectionManager 實例本身。

        輸出:
            無。
        """
        logger.info("停止加密貨幣價格提供者...")
        if self.crypto_provider:
            try:
                self.crypto_provider.stop()
                logger.info("已停止加密貨幣價格提供者。")
            except Exception as e:
                logger.error(f"停止加密貨幣價格提供者時發生錯誤: {e}")
        else:
            logger.info("加密貨幣提供者未運行，無需停止。")


manager = ConnectionManager()


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
    # 啟動
    try:
        logger.info("啟動應用程式...")

        # 儲存事件循環以進行同步廣播
        manager.loop = asyncio.get_running_loop()

        # 啟動加密貨幣價格提供者
        manager.start_crypto_provider()

        logger.info("應用程式已成功啟動。")

        yield

    except Exception as e:
        logger.error(f"啟動應用程式失敗: {e}")
        raise

    finally:
        # 關閉
        logger.info("正在關閉應用程式...")
        manager.stop_crypto_provider()
        logger.info("應用程式關閉完成。")


app = FastAPI(
    title="加密貨幣價格串流 API",
    description="具有 InfluxDB 儲存的即時加密貨幣價格串流",
    version="1.0.0",
    lifespan=lifespan
)


@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """
    用於即時價格串流的 WebSocket 端點。
    處理客戶端連接並保持連接活躍。

    輸入:
        websocket (WebSocket): 傳入的 WebSocket 連接。

    輸出:
        無。
    """
    await manager.connect(websocket)
    try:
        while True:
            # 透過等待任何訊息來保持連接活躍
            # 在實際應用程式中，您可以在此處處理客戶端命令
            message = await websocket.receive_text()
            logger.debug(f"從 WebSocket 接收到訊息: {message}")
    except Exception as e:
        logger.info(f"WebSocket 連接關閉: {e}")
    finally:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """
    根端點，提供 API 資訊。

    輸入:
        無。

    輸出:
        Dict: 包含 API 訊息、版本、端點和狀態的字典。
    """
    logger.info("訪問根端點。")
    return {
        "message": "加密貨幣價格串流服務器",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/price",
            "health": "/health",
            "config": "/config"
        },
        "status": "運行中"
    }


@app.get("/health")
async def health_check():
    """
    健康檢查端點。
    返回應用程式的健康狀態，包括加密貨幣提供者狀態和活動 WebSocket 連接數。

    輸入:
        無。

    輸出:
        Dict: 包含健康狀態資訊的字典。
    """
    logger.info("執行健康檢查。")
    crypto_provider_status = "運行中" if manager.crypto_provider else "已停止"

    return {
        "status": "健康",
        "crypto_provider": crypto_provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols) if manager.crypto_provider else []
    }


@app.get("/config")
async def get_config():
    """
    獲取當前配置（不包括敏感數據）。

    輸入:
        無。

    輸出:
        Dict: 包含應用程式配置的字典。
    """
    logger.info("獲取當前配置。")
    return {
        "binance_symbol": config.binance_symbol,
        "binance_interval": config.binance_interval,
        "api_host": config.api_host,
        "api_port": config.api_port,
        "influxdb_host": config.influxdb_host,
        "influxdb_database": config.influxdb_database
        # 注意: influxdb_token 出於安全原因被排除
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
    """
    logger.info(f"嘗試訂閱符號: {symbol}，間隔: {interval}")
    if not manager.crypto_provider:
        logger.error("加密貨幣提供者未初始化，無法訂閱符號。")
        return {"error": "加密貨幣提供者未初始化"}

    try:
        manager.crypto_provider.subscribe_symbol(symbol, interval)
        logger.info(f"已成功訂閱 {symbol}，間隔 {interval}。")
        return {
            "status": "成功",
            "message": f"已訂閱 {symbol}，間隔 {interval}"
        }
    except Exception as e:
        logger.error(f"訂閱 {symbol} 失敗: {e}")
        return {"error": str(e)}


@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """
    取消訂閱交易對價格串流。

    輸入:
        symbol (str): 要取消訂閱的交易對符號。
        interval (str): K 線資料的時間間隔，預設為 "1m"。

    輸出:
        Dict: 包含取消訂閱狀態和訊息的字典。
    """
    logger.info(f"嘗試取消訂閱符號: {symbol}，間隔: {interval}")
    if not manager.crypto_provider:
        logger.error("加密貨幣提供者未初始化，無法取消訂閱符號。")
        return {"error": "加密貨幣提供者未初始化"}

    try:
        manager.crypto_provider.unsubscribe_symbol(symbol, interval)
        logger.info(f"已成功取消訂閱 {symbol}，間隔 {interval}。")
        return {
            "status": "成功",
            "message": f"已取消訂閱 {symbol}，間隔 {interval}"
        }
    except Exception as e:
        logger.error(f"取消訂閱 {symbol} 失敗: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"在 {config.api_host}:{config.api_port} 啟動服務器。")
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level="info"
    )
