import json
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, List

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from .abstract_data_provider import AbstractRealtimeDataProvider
from ..colored_logging import setup_colored_logging
from ..data_models import PriceData

import json
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, List

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from .abstract_data_provider import AbstractRealtimeDataProvider
from ..colored_logging import setup_colored_logging
from ..data_models import PriceData

log = setup_colored_logging(level=logging.INFO)


class InfluxDBManager:
    """
    管理與 InfluxDB 資料庫的連接和資料寫入。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類為基本版本的 InfluxDB 管理器，負責建立與 InfluxDB 數據庫的連接，
        並提供將加密貨幣價格數據同步寫入數據庫的功能。
        它還配置了寫入選項，包括批次大小、刷新間隔和錯誤處理回調，
        以優化數據寫入的性能和可靠性。
    """

    def __init__(self, host: str, token: str, database: str):
        """
        初始化 InfluxDBManager 實例。

        參數:
            host (str): InfluxDB 服務器的主機位址。
            token (str): 用於 InfluxDB 認證的令牌。
            database (str): 要連接的 InfluxDB 資料庫名稱。
        """
        self.host = host
        self.token = token
        self.database = database
        self.client: Optional[InfluxDBClient3] = None
        self._setup_write_options()
        log.info(f"InfluxDBManager 初始化完成，主機: {self.host}, 資料庫: {self.database}")

    def _setup_write_options(self):
        """
        配置 InfluxDB 寫入選項以優化性能。
        此方法設定批次寫入、刷新間隔、重試策略等，
        並定義了成功、錯誤和重試時的回調函數，用於日誌記錄和監控寫入操作。
        """
        log.info("正在設定 InfluxDB 寫入選項...")

        def success_callback(conf, data: str):
            log.info(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組。")

        def error_callback(conf, data: str, exception: InfluxDBError):
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}。")

        def retry_callback(conf, data: str, exception: InfluxDBError):
            log.warning(f"正在重試寫入到 InfluxDB: {exception}。")

        write_options = WriteOptions(
            batch_size=100, flush_interval=5_000, jitter_interval=1_000,
            retry_interval=5_000, max_retries=3, max_retry_delay=30_000,
            exponential_base=2
        )

        self.write_client_options = write_client_options(
            success_callback=success_callback,
            error_callback=error_callback,
            retry_callback=retry_callback,
            write_options=write_options
        )
        log.info("InfluxDB 寫入選項設定完成。")

    def connect(self):
        """
        連接到 InfluxDB 資料庫。

        此方法嘗試使用配置的主機、令牌和數據庫名稱建立與 InfluxDB 的連接。
        如果連接成功，將記錄信息；如果失敗，則記錄錯誤並拋出異常。

        Raises:
            Exception: 如果連接失敗則拋出異常。
        """
        log.info("正在嘗試連接到 InfluxDB...")
        try:
            self.client = InfluxDBClient3(
                host=self.host, token=self.token, database=self.database,
                write_client_options=self.write_client_options
            )
            log.info(f"成功連接到 InfluxDB，主機: {self.host}。")
        except Exception as e:
            log.error(f"連接到 InfluxDB 失敗: {e}。")
            raise

    def disconnect(self):
        """
        從 InfluxDB 資料庫斷開連接。
        此方法會安全地關閉與 InfluxDB 的客戶端連接，釋放相關資源。
        """
        log.info("正在嘗試從 InfluxDB 斷開連接...")
        if self.client:
            self.client.close()
            self.client = None
            log.info("已從 InfluxDB 斷開連接。")

    def write_price_data(self, price_data: PriceData):
        """
        將價格資料同步寫入 InfluxDB。

        此方法將 PriceData 對象轉換為 InfluxDB 的 Point 數據點，
        並將其寫入到配置的數據庫中。
        如果客戶端未連接或寫入過程中發生錯誤，將記錄相應的錯誤信息。

        參數:
            price_data (PriceData): 包含要寫入的價格資料的 PriceData 物件。
        """
        if not self.client:
            log.error("InfluxDB 客戶端未連接，無法寫入資料。")
            return

        try:
            point = (Point("crypto_price")
                     .tag("symbol", price_data.symbol)
                     .field("price", price_data.price)
                     .field("open", price_data.open_price)
                     .field("high", price_data.high_price)
                     .field("low", price_data.low_price)
                     .field("close", price_data.close_price)
                     .field("volume", price_data.volume)
                     .time(price_data.timestamp, write_precision='ms'))

            self.client.write(point)
            log.debug(f"已將 {price_data.symbol} 的價格資料寫入 InfluxDB。")
        except Exception as e:
            log.error(f"寫入價格資料到 InfluxDB 失敗: {e}。")


class CryptoPriceProviderRealtime(AbstractRealtimeDataProvider):
    """
    基本版加密貨幣價格提供者。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類從幣安 WebSocket 獲取加密貨幣價格資料，
        並將接收到的數據同步儲存到 InfluxDB。
        它實現了 AbstractRealtimeDataProvider 介面，
        提供了啟動、停止、訂閱和取消訂閱數據流的功能，
        以及獲取運行統計和最新價格的方法。
    """

    def __init__(self, influxdb_manager: InfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None):
        """
        初始化 CryptoPriceProviderRealtime 實例。

        參數:
            influxdb_manager (InfluxDBManager): 用於管理 InfluxDB 連接和寫入的實例。
            message_callback (Optional[Callable[[str], None]]): 可選的回調函數，用於處理接收到的原始 WebSocket 訊息。
        """
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self._subscribed_symbols = set()
        log.info("CryptoPriceProviderRealtime (基本版) 初始化完成。")

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """
        解析幣安 K 線 WebSocket 訊息並提取價格資料。

        此方法接收來自幣安 WebSocket 的原始 JSON 訊息字串，
        解析其中的 K 線數據，並將其轉換為 PriceData 對象。
        如果解析失敗（例如 JSON 格式錯誤或缺少關鍵字段），則返回 None。

        參數:
            message (str): 來自幣安 WebSocket 的原始 JSON 訊息字串。

        返回:
            Optional[PriceData]: 如果解析成功則返回 PriceData 物件，否則返回 None。
        """
        try:
            data = json.loads(message)
            if 'k' not in data:
                return None

            kline = data['k']
            return PriceData(
                symbol=kline['s'],
                price=float(kline['c']),
                timestamp=datetime.fromtimestamp(kline['T'] / 1000),
                open_price=float(kline['o']),
                high_price=float(kline['h']),
                low_price=float(kline['l']),
                close_price=float(kline['c']),
                volume=float(kline['v'])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.error(f"解析 K 線資料失敗: {e}，原始訊息: {message}。")
            return None

    def _handle_binance_message(self, ws, message: str):
        """
        處理來自幣安 WebSocket 的傳入訊息。
        此方法解析接收到的 WebSocket 訊息，將提取的價格資料寫入 InfluxDB，
        並在成功處理後調用註冊的回調函數，將原始訊息傳遞出去。

        參數:
            ws: WebSocket 連接實例。
            message (str): 來自幣安 WebSocket 的原始訊息字串。
        """
        price_data = self._parse_kline_data(message)
        if price_data:
            self.influxdb_manager.write_price_data(price_data)
            log.info(f"已處理 {price_data.symbol}: ${price_data.price}。")

            if self.message_callback:
                self.message_callback(message)

    def start(self):
        """
        啟動價格提供者。
        此方法會首先連接到 InfluxDB，然後初始化幣安 WebSocket 客戶端，
        並準備好接收實時價格數據。
        """
        log.info("正在啟動 CryptoPriceProviderRealtime (基本版)...")
        self.influxdb_manager.connect()
        self.binance_client = UMFuturesWebsocketClient(on_message=self._handle_binance_message)
        log.info("CryptoPriceProviderRealtime (基本版) 已成功啟動。")

    def stop(self):
        """
        停止價格提供者。
        此方法會停止幣安 WebSocket 客戶端，並斷開與 InfluxDB 的連接，
        確保所有數據流和資源被正確釋放。
        """
        log.info("正在停止 CryptoPriceProviderRealtime (基本版)...")
        if self.binance_client:
            self.binance_client.stop()
            self.binance_client = None
        self.influxdb_manager.disconnect()
        log.info("CryptoPriceProviderRealtime (基本版) 已成功停止。")

    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱指定交易對的價格串流。符合 AbstractRealtimeDataProvider 介面。

        此方法會向幣安 WebSocket 客戶端發送訂閱請求，
        以獲取指定交易對和時間間隔的 K 線數據。
        如果幣安客戶端未初始化，則會記錄錯誤。

        參數:
            symbol (str): 要訂閱的交易對符號 (例如 'btcusdt')。
            **kwargs: 包含 'interval' 的可選參數。
        """
        interval = kwargs.get("interval", "1m")
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法訂閱。")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"
        if stream_name not in self._subscribed_symbols:
            self.binance_client.subscribe(stream_name)
            self._subscribed_symbols.add(stream_name)
            log.info(f"已訂閱 {stream_name}。")

    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱指定交易對的價格串流。符合 AbstractRealtimeDataProvider 介面。

        此方法會向幣安 WebSocket 客戶端發送取消訂閱請求，
        停止接收指定交易對和時間間隔的 K 線數據。
        如果幣安客戶端未初始化，則會記錄錯誤。

        參數:
            symbol (str): 要取消訂閱的交易對符號。
            **kwargs: 包含 'interval' 的可選參數。
        """
        interval = kwargs.get("interval", "1m")
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法取消訂閱。")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"
        if stream_name in self._subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self._subscribed_symbols.remove(stream_name)
            log.info(f"已取消訂閱 {stream_name}。")

    def get_stats(self) -> Dict:
        """
        獲取提供者的運行統計數據。

        此方法返回一個字典，包含當前已訂閱的交易對數量和列表，
        用於監控數據提供者的運行狀態。

        返回:
            Dict: 包含已訂閱符號數量和列表的字典。
        """
        return {
            "subscribed_symbols_count": len(self._subscribed_symbols),
            "subscribed_symbols_list": list(self._subscribed_symbols)
        }

    def get_latest_prices(self) -> Dict:
        """
        獲取最新價格。基本版不實現快取，因此返回空字典。

        此方法在基本版中不提供實時價格快取功能，因此總是返回一個空字典。

        返回:
            Dict: 空字典。
        """
        return {}

    @property
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號流名稱列表。

        此屬性返回一個列表，包含所有當前正在訂閱的幣安 WebSocket 數據流名稱。

        返回:
            List[str]: 當前已訂閱的符號列表。
        """
        return list(self._subscribed_symbols)
