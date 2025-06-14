import json
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, List

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from .abstract_data_provider import AbstractRealtimeDataProvider
from ..data_models import PriceData

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class InfluxDBManager:
    """
    管理與 InfluxDB 資料庫的連接和資料寫入。
    此為基本版本，提供同步寫入和基本的回調功能。
    """

    def __init__(self, host: str, token: str, database: str):
        """
        初始化 InfluxDBManager 實例。

        Parameters:
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
        此方法設定批次寫入、刷新間隔、重試策略等。
        """
        log.info("設定 InfluxDB 寫入選項...")

        def success_callback(conf, data: str):
            log.info(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組")

        def error_callback(conf, data: str, exception: InfluxDBError):
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}")

        def retry_callback(conf, data: str, exception: InfluxDBError):
            log.warning(f"重試寫入到 InfluxDB: {exception}")

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

        Raises:
            Exception: 如果連接失敗則拋出異常。
        """
        log.info("嘗試連接到 InfluxDB...")
        try:
            self.client = InfluxDBClient3(
                host=self.host, token=self.token, database=self.database,
                write_client_options=self.write_client_options
            )
            log.info(f"成功連接到 InfluxDB，主機: {self.host}")
        except Exception as e:
            log.error(f"連接到 InfluxDB 失敗: {e}")
            raise

    def disconnect(self):
        """
        從 InfluxDB 資料庫斷開連接。
        """
        log.info("嘗試從 InfluxDB 斷開連接...")
        if self.client:
            self.client.close()
            self.client = None
            log.info("已從 InfluxDB 斷開連接。")

    def write_price_data(self, price_data: PriceData):
        """
        將價格資料同步寫入 InfluxDB。

        Parameters:
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
            log.error(f"寫入價格資料到 InfluxDB 失敗: {e}")


class CryptoPriceProviderRealtime(AbstractRealtimeDataProvider):
    """
    基本版加密貨幣價格提供者。
    從幣安 WebSocket 獲取加密貨幣價格資料，並將其同步儲存到 InfluxDB。
    """

    def __init__(self, influxdb_manager: InfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None):
        """
        初始化 CryptoPriceProviderRealtime 實例。

        Parameters:
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

        Parameters:
            message (str): 來自幣安 WebSocket 的原始 JSON 訊息字串。

        Returns:
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
            log.error(f"解析 K 線資料失敗: {e}，原始訊息: {message}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """
        處理來自幣安 WebSocket 的傳入訊息。
        此方法解析訊息，將價格資料寫入 InfluxDB，並調用回調函數。

        Parameters:
            ws: WebSocket 連接實例。
            message (str): 來自幣安 WebSocket 的原始訊息字串。
        """
        price_data = self._parse_kline_data(message)
        if price_data:
            self.influxdb_manager.write_price_data(price_data)
            log.info(f"已處理 {price_data.symbol}: ${price_data.price}")

            if self.message_callback:
                self.message_callback(message)

    def start(self):
        """
        啟動價格提供者。連接到 InfluxDB 並初始化幣安 WebSocket 客戶端。
        """
        log.info("啟動 CryptoPriceProviderRealtime (基本版)...")
        self.influxdb_manager.connect()
        self.binance_client = UMFuturesWebsocketClient(on_message=self._handle_binance_message)
        log.info("CryptoPriceProviderRealtime (基本版) 已成功啟動。")

    def stop(self):
        """
        停止價格提供者。停止幣安 WebSocket 並斷開 InfluxDB 連接。
        """
        log.info("停止 CryptoPriceProviderRealtime (基本版)...")
        if self.binance_client:
            self.binance_client.stop()
            self.binance_client = None
        self.influxdb_manager.disconnect()
        log.info("CryptoPriceProviderRealtime (基本版) 已成功停止。")

    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱指定交易對的價格串流。符合 AbstractRealtimeDataProvider 介面。

        Parameters:
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
            log.info(f"已訂閱 {stream_name}")

    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱指定交易對的價格串流。符合 AbstractRealtimeDataProvider 介面。

        Parameters:
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
            log.info(f"已取消訂閱 {stream_name}")

    def get_stats(self) -> Dict:
        """
        獲取提供者的運行統計數據。

        Returns:
            Dict: 包含已訂閱符號數量和列表的字典。
        """
        return {
            "subscribed_symbols_count": len(self._subscribed_symbols),
            "subscribed_symbols_list": list(self._subscribed_symbols)
        }

    def get_latest_prices(self) -> Dict:
        """
        獲取最新價格。基本版不實現快取，因此返回空字典。

        Returns:
            Dict: 空字典。
        """
        return {}

    @property
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號流名稱列表。

        Returns:
            List[str]: 當前已訂閱的符號列表。
        """
        return list(self._subscribed_symbols)
