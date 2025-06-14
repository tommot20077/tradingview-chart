import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable, Dict, List

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from abstract_data_provider import AbstractRealtimeDataProvider
from data_models import PriceData

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class InfluxDBManager:
    """
    管理與 InfluxDB 資料庫的連接和資料寫入。
    """

    def __init__(self, host: str, token: str, database: str):
        """
        初始化 InfluxDBManager 實例。

        輸入:
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

        輸入:
            self (InfluxDBManager): InfluxDBManager 實例本身。

        輸出:
            無。
        """
        log.info("設定 InfluxDB 寫入選項...")

        def success_callback(data: str):
            """
            批次寫入成功時的回調函數。

            輸入:
                data (str): 成功寫入的資料字串。

            輸出:
                無。
            """
            log.info(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組")

        def error_callback(data: str, exception: InfluxDBError):
            """
            批次寫入失敗時的回調函數。

            輸入:
                data (str): 寫入失敗的資料字串。
                exception (InfluxDBError): 寫入失敗時的異常。

            輸出:
                無。
            """
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}")

        def retry_callback(data: str, exception: InfluxDBError):
            """
            批次寫入重試時的回調函數。

            輸入:
                data (str): 正在重試寫入的資料字串。
                exception (InfluxDBError): 重試時的異常。

            輸出:
                無。
            """
            log.warning(f"重試寫入到 InfluxDB: {exception}")

        write_options = WriteOptions(
            batch_size=100,
            flush_interval=5_000,
            jitter_interval=1_000,
            retry_interval=5_000,
            max_retries=3,
            max_retry_delay=30_000,
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

        輸入:
            self (InfluxDBManager): InfluxDBManager 實例本身。

        輸出:
            無。

        異常:
            Exception: 如果連接失敗則拋出異常。
        """
        log.info("嘗試連接到 InfluxDB...")
        try:
            self.client = InfluxDBClient3(
                host=self.host,
                token=self.token,
                database=self.database,
                write_client_options=self.write_client_options
            )
            log.info(f"成功連接到 InfluxDB，主機: {self.host}")
        except Exception as e:
            log.error(f"連接到 InfluxDB 失敗: {e}")
            raise

    def disconnect(self):
        """
        從 InfluxDB 資料庫斷開連接。

        輸入:
            self (InfluxDBManager): InfluxDBManager 實例本身。

        輸出:
            無。
        """
        log.info("嘗試從 InfluxDB 斷開連接...")
        if self.client:
            self.client.close()
            self.client = None
            log.info("已從 InfluxDB 斷開連接。")
        else:
            log.info("InfluxDB 客戶端未連接，無需斷開。")

    def write_price_data(self, price_data: PriceData):
        """
        將價格資料寫入 InfluxDB。

        輸入:
            self (InfluxDBManager): InfluxDBManager 實例本身。
            price_data (PriceData): 包含要寫入的價格資料的 PriceData 物件。

        輸出:
            無。
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
                     .time(price_data.timestamp))

            self.client.write([point])
            log.debug(f"已將 {price_data.symbol} 的價格資料寫入 InfluxDB。")
        except Exception as e:
            log.error(f"寫入價格資料到 InfluxDB 失敗: {e}")


class CryptoPriceProviderRealtime(AbstractRealtimeDataProvider):
    """
    加密貨幣價格提供者，此類為 AbstractDataProvider 的實現，
    從幣安 WebSocket 獲取加密貨幣價格資料並將其儲存到 InfluxDB。
    """

    def __init__(self, influxdb_manager: InfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None):
        """
        初始化 CryptoPriceProvider 實例。

        輸入:
            influxdb_manager (InfluxDBManager): 用於管理 InfluxDB 連接和寫入的實例。
            message_callback (Optional[Callable[[str], None]]): 可選的回調函數，用於處理接收到的原始 WebSocket 訊息。
        """
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self._subscribed_symbols = set()

        log.info("CryptoPriceProvider 初始化完成。")

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """
        解析幣安 K 線 WebSocket 訊息並提取價格資料。

        輸入:
            message (str): 來自幣安 WebSocket 的原始 JSON 訊息字串。

        輸出:
            Optional[PriceData]: 如果解析成功則返回 PriceData 物件，否則返回 None。
        """
        try:
            data = json.loads(message)

            if 'k' not in data:
                log.debug("接收到的訊息不包含 K 線資料。")
                return None

            kline = data['k']

            price_data = PriceData(
                symbol=kline['s'],
                price=float(kline['c']),  # 收盤價作為當前價格
                timestamp=datetime.fromtimestamp(kline['T'] / 1000),  # 收盤時間
                open_price=float(kline['o']),
                high_price=float(kline['h']),
                low_price=float(kline['l']),
                close_price=float(kline['c']),
                volume=float(kline['v'])
            )
            log.debug(f"成功解析 K 線資料: {price_data.symbol} @ {price_data.price}")
            return price_data
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.error(f"解析 K 線資料失敗: {e}，原始訊息: {message}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """
        處理來自幣安 WebSocket 的傳入訊息。
        此方法解析訊息，將價格資料寫入 InfluxDB，並將原始訊息轉發給回調函數（如果已提供）。

        輸入:
            ws: WebSocket 連接實例 (由 binance-connector 庫提供)。
            message (str): 來自幣安 WebSocket 的原始訊息字串。

        輸出:
            無。
        """
        try:
            # 解析價格資料
            price_data = self._parse_kline_data(message)

            if price_data:
                # 儲存到 InfluxDB
                self.influxdb_manager.write_price_data(price_data)
                log.info(f"已處理 {price_data.symbol}: ${price_data.price}")

            # 將訊息轉發給回調函數 (用於 WebSocket 廣播)
            if self.message_callback:
                self.message_callback(message)
                log.debug("訊息已轉發給回調函數。")

        except Exception as e:
            log.error(f"處理幣安訊息時發生錯誤: {e}，原始訊息: {message}")

    def start(self):
        """
        啟動價格提供者。
        此方法連接到 InfluxDB 並初始化幣安 WebSocket 客戶端。

        輸入:
            self (CryptoPriceProvider): CryptoPriceProvider 實例本身。

        輸出:
            無。

        異常:
            Exception: 如果啟動失敗則拋出異常。
        """
        log.info("啟動 CryptoPriceProvider...")
        try:
            # 連接到 InfluxDB
            self.influxdb_manager.connect()

            # 建立幣安 WebSocket 客戶端
            self.binance_client = UMFuturesWebsocketClient(
                on_message=self._handle_binance_message
            )
            log.info("CryptoPriceProvider 已成功啟動。")

        except Exception as e:
            log.error(f"啟動 CryptoPriceProvider 失敗: {e}")
            raise

    def stop(self):
        """
        停止價格提供者。
        此方法停止幣安 WebSocket 客戶端並斷開與 InfluxDB 的連接。

        輸入:
            self (CryptoPriceProvider): CryptoPriceProvider 實例本身。

        輸出:
            無。
        """
        log.info("停止 CryptoPriceProvider...")
        try:
            if self.binance_client:
                self.binance_client.stop()
                self.binance_client = None
                log.info("幣安 WebSocket 客戶端已停止。")

            self.influxdb_manager.disconnect()
            log.info("CryptoPriceProvider 已成功停止。")

        except Exception as e:
            log.error(f"停止 CryptoPriceProvider 時發生錯誤: {e}")

    def subscribe_symbol(self, symbol: str, interval: str = "1m"):
        """
        訂閱指定交易對的價格串流。

        輸入:
            self (CryptoPriceProvider): CryptoPriceProvider 實例本身。
            symbol (str): 要訂閱的交易對符號 (例如 'btcusdt')。
            interval (str): K 線資料的時間間隔 (例如 '1m', '5m')。預設為 '1m'。

        輸出:
            無。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法訂閱。")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name not in self._subscribed_symbols:
            self.binance_client.subscribe(stream_name)
            self._subscribed_symbols.add(stream_name)
            log.info(f"已訂閱 {stream_name}")
        else:
            log.info(f"已訂閱 {stream_name}，無需重複訂閱。")

    def unsubscribe_symbol(self, symbol: str, interval: str = "1m"):
        """
        取消訂閱指定交易對的價格串流。

        輸入:
            self (CryptoPriceProvider): CryptoPriceProvider 實例本身。
            symbol (str): 要取消訂閱的交易對符號 (例如 'btcusdt')。
            interval (str): K 線資料的時間間隔 (例如 '1m', '5m')。預設為 '1m'。

        輸出:
            無。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法取消訂閱。")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name in self._subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self._subscribed_symbols.remove(stream_name)
            log.info(f"已取消訂閱 {stream_name}")
        else:
            log.info(f"未訂閱 {stream_name}，無需取消。")

    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱指定交易對的價格串流。
        此方法是為了符合 AbstractDataProvider 介面而提供的通用訂閱方法。
        """
        interval = kwargs.get("interval", "1m")
        self.subscribe_symbol(symbol, interval)

    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱指定交易對的價格串流。
        此方法是為了符合 AbstractDataProvider 介面而提供的通用取消訂閱方法。
        """
        interval = kwargs.get("interval", "1m")
        self.unsubscribe_symbol(symbol, interval)

    def get_stats(self) -> Dict:
        """
        獲取提供者的運行統計數據。
        此處為基本實現，可根據需要擴展。
        """
        log.debug("獲取價格提供者統計數據。")
        return {
            "subscribed_symbols_count": len(self._subscribed_symbols),
            "subscribed_symbols_list": list(self._subscribed_symbols)
        }

    def get_latest_prices(self) -> Dict:
        """
        獲取所有已快取符號的最新價格數據。
        CryptoPriceProvider 沒有內建快取，因此此方法返回空字典。
        """
        log.debug("獲取所有已快取符號的最新價格。")
        return {}

    @property
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號列表。
        """
        return list(self._subscribed_symbols)
