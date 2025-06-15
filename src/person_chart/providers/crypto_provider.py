import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List, Any, Union

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from .abstract_data_provider import AbstractRealtimeDataProvider, AbstractHistoricalDataProvider
from .. import config
from ..analysis.data_analyzer import CryptoDataAnalyzer
from ..colored_logging import setup_colored_logging
from ..data_models import InfluxDBStats, PriceData
from ..tools.time_unity import interval_to_seconds, find_optimal_source_interval

log = setup_colored_logging(level=logging.INFO)

_KAFKA_AVAILABLE = True
try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None
    _KAFKA_AVAILABLE = False
    log.warning("kafka-python 未安裝。Kafka 功能將不可用。請運行 'pip install -e .[kafka]' 來安裝。")


class KlineAggregator:
    """
    處理 K 線數據聚合的輔助類。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 23:58:00
    版本號: 0.6.1
    用途說明:
        此類負責將基礎時間間隔的 K 線數據聚合成更大的時間間隔 K 線。
        它維護每個目標時間間隔的聚合器狀態，並在接收到新的基礎 K 線數據時，
        更新相應的聚合 K 線，並在時間窗口結束時將聚合結果寫入數據庫。
    """

    def __init__(self, symbol: str, base_interval: str, target_intervals: List[str], writer_func: Callable):
        """
        初始化 KlineAggregator 實例。

        參數:
            symbol (str): 交易對符號。
            base_interval (str): 基礎 K 線時間間隔 (例如 '1m')。
            target_intervals (List[str]): 目標聚合時間間隔列表 (例如 ['5m', '1h'])。
            writer_func (Callable): 用於寫入聚合 K 線數據的回調函數。
        """
        self.symbol = symbol.upper()
        self.base_interval_seconds = interval_to_seconds(base_interval)
        self.target_intervals = target_intervals
        self.writer_func = writer_func
        self.aggregators: Dict[str, Optional[PriceData]] = {
            interval: None for interval in target_intervals
        }

    def process(self, base_kline: PriceData):
        """
        處理新的基礎 K 線數據並更新所有目標聚合器。

        此方法接收一個新的基礎 K 線數據點，並遍歷所有目標聚合時間間隔。
        對於每個目標間隔，它會檢查當前基礎 K 線是否屬於新的聚合時間窗口。
        如果是，則完成前一個聚合 K 線（如果存在）並寫入數據庫，然後開始新的聚合 K 線。
        否則，它會更新當前聚合 K 線的最高價、最低價、收盤價、交易量和交易數量。

        參數:
            base_kline (PriceData): 新的基礎 K 線數據。
        """
        for interval in self.target_intervals:
            interval_seconds = interval_to_seconds(interval)
            if interval_seconds <= self.base_interval_seconds:
                continue

            kline_timestamp = int(base_kline.timestamp.timestamp())
            time_bucket = kline_timestamp - (kline_timestamp % interval_seconds)

            agg_kline = self.aggregators.get(interval)

            if agg_kline is None or int(agg_kline.timestamp.timestamp()) != time_bucket:
                if agg_kline is not None:
                    log.debug(f"正在完成 {self.symbol} {interval} K 線於 {agg_kline.timestamp}。")
                    self.writer_func(agg_kline, interval)

                self.aggregators[interval] = PriceData(
                    symbol=self.symbol,
                    price=base_kline.price,
                    timestamp=datetime.fromtimestamp(time_bucket, tz=timezone.utc),
                    open_price=base_kline.open_price,
                    high_price=base_kline.high_price,
                    low_price=base_kline.low_price,
                    close_price=base_kline.close_price,
                    volume=base_kline.volume,
                    trade_count=base_kline.trade_count or 0
                )
            else:
                agg_kline.high_price = max(agg_kline.high_price, base_kline.high_price)
                agg_kline.low_price = min(agg_kline.low_price, base_kline.low_price)
                agg_kline.close_price = base_kline.close_price
                agg_kline.volume += base_kline.volume
                current_trade_count = base_kline.trade_count or 0
                agg_kline.trade_count = (agg_kline.trade_count or 0) + current_trade_count
                agg_kline.price = base_kline.price


class InfluxDBManager:
    """
    InfluxDB 管理器，支援高效的非同步批次寫入和後台工作執行緒。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類負責建立與 InfluxDB 數據庫的連接，並提供將加密貨幣價格數據
        （包括基礎數據和聚合數據）非同步批次寫入數據庫的功能。
        它配置了優化的寫入選項，包括批次大小、刷新間隔和錯誤處理回調，
        以確保數據的高效和可靠攝取，並提供實時的寫入統計信息。
    """

    def __init__(self, host: str, token: str, database: str, batch_size: int = 200, flush_interval: int = 5_000):
        """
        初始化 InfluxDBManager 實例。

        參數:
            host (str): InfluxDB 服務器的主機位址。
            token (str): 用於 InfluxDB 認證的令牌。
            database (str): 要連接的 InfluxDB 資料庫名稱。
            batch_size (int): 批次寫入的點數大小。
            flush_interval (int): 強制刷新批次到資料庫的間隔（毫秒）。
        """
        self.host = host
        self.token = token
        self.database = database
        self.client: Optional[InfluxDBClient3] = None
        self.stats = InfluxDBStats()
        self._setup_write_options(batch_size, flush_interval)
        log.info(f"InfluxDBManager 初始化完成，主機: {self.host}, 資料庫: {self.database}")

    def _setup_write_options(self, batch_size: int, flush_interval: int):
        """
        配置 InfluxDB 寫入選項以優化性能。
        此方法設定批次寫入、刷新間隔、重試策略等，
        並定義了成功、錯誤和重試時的回調函數，用於更新內部統計和日誌記錄。
        """
        log.info("正在設定 InfluxDB 寫入選項...")

        def success_callback(conf, data: str):
            self.stats.successful_writes += 1
            self.stats.last_write_time = datetime.now(timezone.utc)
            log.debug(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組。")

        def error_callback(conf, data: str, exception: InfluxDBError):
            self.stats.failed_writes += 1
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}。")

        def retry_callback(conf, data: str, exception: InfluxDBError):
            self.stats.retry_count += 1
            log.warning(f"正在重試寫入到 InfluxDB: {exception}。")

        write_options = WriteOptions(
            batch_size=batch_size, flush_interval=flush_interval, jitter_interval=2_000,
            retry_interval=5_000, max_retries=3, max_retry_delay=30_000, exponential_base=2
        )
        self.write_client_options = write_client_options(
            success_callback=success_callback, error_callback=error_callback,
            retry_callback=retry_callback, write_options=write_options
        )
        log.info("InfluxDB 寫入選項設定完成。")

    def connect(self):
        """
        連接到 InfluxDB 資料庫。
        此方法嘗試使用配置的主機、令牌和數據庫名稱建立與 InfluxDB 的連接。
        如果連接成功，將記錄信息；如果失敗，則記錄錯誤並拋出異常。
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
        將價格資料點非同步寫入 InfluxDB。

        此方法將 PriceData 對象轉換為 InfluxDB 的 Point 數據點，
        並將其寫入到配置的數據庫中。
        它會更新內部統計數據，並記錄調試信息。
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

            if price_data.trade_count is not None:
                point = point.field("trade_count", price_data.trade_count)

            self.client.write(point)
            self.stats.total_writes += 1
            log.debug(f"已將 {price_data.symbol} 的價格資料提交至 InfluxDB 寫入緩存。")
        except Exception as e:
            log.error(f"提交價格資料到 InfluxDB 寫入緩存失敗: {e}。")

    def get_stats(self) -> dict:
        """
        獲取 InfluxDB 操作統計數據。
        此方法返回一個字典，包含 InfluxDB 寫入操作的詳細統計信息，
        例如總寫入點數、成功批次數、失敗批次數、重試次數和最後寫入時間。
        """
        return {
            "total_points_written": self.stats.total_writes,
            "successful_batches": self.stats.successful_writes,
            "failed_batches": self.stats.failed_writes,
            "retry_count": self.stats.retry_count,
            "last_write_time": self.stats.last_write_time.isoformat() if self.stats.last_write_time else None,
        }

    def write_aggregated_price_data(self, price_data: PriceData, interval: str):
        """
        將聚合後的價格數據寫入對應的 InfluxDB measurement。

        此方法將聚合後的 PriceData 對象轉換為 InfluxDB 的 Point 數據點，
        並將其寫入到以時間間隔命名的特定 measurement 中（例如 `crypto_price_5m`）。
        這有助於將不同時間粒度的 K 線數據分開存儲，便於查詢和管理。

        參數:
            price_data (PriceData): 包含要寫入的聚合價格資料的 PriceData 物件。
            interval (str): 聚合的時間間隔 (例如 '5m', '1h')。
        """
        if not self.client:
            log.error("InfluxDB 客戶端未連接。")
            return

        measurement_name = f"crypto_price_{interval}"
        point = (Point(measurement_name)
                 .tag("symbol", price_data.symbol)
                 .field("open", price_data.open_price)
                 .field("high", price_data.high_price)
                 .field("low", price_data.low_price)
                 .field("close", price_data.close_price)
                 .field("volume", price_data.volume)
                 .time(price_data.timestamp, write_precision='s'))

        if price_data.trade_count is not None:
            point = point.field("trade_count", price_data.trade_count)

        self.client.write(point)
        log.debug(f"已將 {price_data.symbol}@{interval} 的聚合數據提交至 InfluxDB。")


class CryptoPriceProviderRealtime(AbstractRealtimeDataProvider, AbstractHistoricalDataProvider):
    """
    增強型加密貨幣價格提供者。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.1
    用途說明:
        此類從幣安 WebSocket 獲取實時加密貨幣價格數據，
        並提供多種高級功能，包括：
        - 數據快取：儲存最新價格數據。
        - Kafka 集成：可選地將數據發佈到 Kafka 消息隊列。
        - 實時 K 線聚合：將基礎數據聚合成多種時間粒度的 K 線數據並寫入 InfluxDB。
        - 歷史數據查詢：從 InfluxDB 獲取歷史 K 線數據，支持分頁和動態聚合。
        它實現了 AbstractRealtimeDataProvider 和 AbstractHistoricalDataProvider 介面。
    """

    def __init__(self,
                 influxdb_manager: InfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None,
                 kafka_producer: Optional[KafkaProducer] = None,
                 kafka_topic: Optional[str] = None):
        """
        初始化 CryptoPriceProviderRealtime 實例。

        參數:
            influxdb_manager (InfluxDBManager): 用於管理 InfluxDB 的實例。
            message_callback (Optional[Callable[[str], None]]): 當 Kafka 禁用時，用於處理訊息的回調。
            kafka_producer (Optional[KafkaProducer]): Kafka 生產者實例。
            kafka_topic (Optional[str]): Kafka 主題名稱。
        """
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.kafka_producer = kafka_producer if _KAFKA_AVAILABLE and kafka_producer else None
        self.kafka_topic = kafka_topic
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self._subscribed_symbols = set()
        self._price_cache: Dict[str, PriceData] = {}
        self._aggregators: Dict[str, KlineAggregator] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="CryptoProviderWorker")
        self.analyzer = CryptoDataAnalyzer(
            host=influxdb_manager.host, token=influxdb_manager.token, database=influxdb_manager.database
        )
        self.stats: Dict[str, Optional[Union[int, datetime, None]]] = {
            "messages_received": 0, "messages_processed": 0, "messages_failed": 0,
            "kafka_messages_sent": 0, "start_time": None
        }
        log.info("CryptoPriceProviderRealtime 初始化完成。")
        if self.kafka_producer:
            log.info(f"Kafka 模式已啟用，將發佈到主題: {self.kafka_topic}。")

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """
        解析幣安 K 線訊息，計算價格變化並更新快取。

        此方法接收來自幣安 WebSocket 的原始 JSON 訊息，
        解析其中的 K 線數據，並計算相對於前一個數據點的價格變化和百分比變化。
        它還會更新內部價格快取，並記錄消息處理統計。

        參數:
            message (str): 來自幣安 WebSocket 的原始 JSON 訊息字串。

        返回:
            Optional[PriceData]: 如果解析成功則返回 PriceData 物件，否則返回 None。
        """
        try:
            data = json.loads(message)
            self.stats["messages_received"] += 1
            if 'k' not in data:
                return None

            kline = data['k']
            symbol = kline['s']
            current_price = float(kline['c'])
            price_change, price_change_percent = None, None

            if symbol in self._price_cache:
                previous_price = self._price_cache[symbol].price
                price_change = current_price - previous_price
                if previous_price > 0:
                    price_change_percent = (price_change / previous_price) * 100

            price_data = PriceData(
                symbol=symbol, price=current_price,
                timestamp=datetime.fromtimestamp(kline['t'] / 1000, tz=timezone.utc),
                open_price=float(kline['o']), high_price=float(kline['h']),
                low_price=float(kline['l']), close_price=float(kline['c']),
                volume=float(kline['v']), price_change=price_change,
                price_change_percent=price_change_percent,
                trade_count=int(kline.get('n', 0))
            )
            self._price_cache[symbol] = price_data
            self.stats["messages_processed"] += 1
            return price_data
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.stats["messages_failed"] += 1
            log.error(f"解析 K 線資料失敗: {e}。")
            return None

    def _handle_binance_message(self, ws, message: str):
        """
        處理來自幣安的訊息，解析、儲存並分發。

        此方法是幣安 WebSocket 客戶端的回調函數。
        它會解析接收到的原始訊息，將其轉換為 PriceData 對象。
        然後，它會將基礎數據寫入 InfluxDB，並觸發 K 線聚合處理。
        最後，根據 Kafka 是否啟用，將處理後的數據發佈到 Kafka 或通過直接回調分發。

        參數:
            ws: WebSocket 連接實例。
            message (str): 來自幣安 WebSocket 的原始訊息字串。
        """
        price_data = self._parse_kline_data(message)
        if not price_data:
            return

        self.influxdb_manager.write_price_data(price_data)

        if price_data.symbol not in self._aggregators:
            self._aggregators[price_data.symbol] = KlineAggregator(
                symbol=price_data.symbol,
                base_interval=config.binance_base_interval,
                target_intervals=config.binance_aggregation_intervals,
                writer_func=self.influxdb_manager.write_aggregated_price_data
            )

        self._executor.submit(self._aggregators[price_data.symbol].process, price_data)

        enhanced_message_dict = {
            "type": "price_update",
            "interval": config.binance_base_interval,
            "data": price_data.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        enhanced_message_json = json.dumps(enhanced_message_dict)

        if self.kafka_producer and self.kafka_topic:
            try:
                self.kafka_producer.send(self.kafka_topic, value=enhanced_message_json.encode('utf-8'))
                self.stats["kafka_messages_sent"] += 1
                log.debug(f"已將 {price_data.symbol} 價格更新發佈到 Kafka 主題 {self.kafka_topic}。")
            except Exception as e:
                log.error(f"發佈消息到 Kafka 失敗: {e}。")
        elif self.message_callback:
            self.message_callback(enhanced_message_json)

    def start(self):
        """
        啟動價格提供者。
        此方法會記錄啟動時間，連接到 InfluxDB，並初始化幣安 WebSocket 客戶端，
        準備好接收實時價格數據。
        """
        log.info("正在啟動 CryptoPriceProviderRealtime ...")
        self.stats["start_time"] = datetime.now(timezone.utc)
        self.influxdb_manager.connect()
        self.binance_client = UMFuturesWebsocketClient(on_message=self._handle_binance_message)
        log.info("CryptoPriceProviderRealtime 已成功啟動。")

    def stop(self):
        """
        停止價格提供者。
        此方法會停止幣安 WebSocket 客戶端，刷新並關閉 Kafka 生產者（如果啟用），
        關閉線程池，並斷開與 InfluxDB 的連接，確保所有數據流和資源被正確釋放。
        """
        log.info("正在停止 CryptoPriceProviderRealtime...")
        if self.binance_client:
            self.binance_client.stop()
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
        self._executor.shutdown(wait=True)
        self.influxdb_manager.disconnect()
        log.info("CryptoPriceProviderRealtime 已成功停止。")

    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱指定交易對。
        此方法會向幣安 WebSocket 客戶端發送訂閱請求，
        以獲取指定交易對基礎時間間隔的 K 線數據。
        如果幣安客戶端未初始化，則會記錄錯誤。

        參數:
            symbol (str): 要訂閱的交易對符號。
            **kwargs: 其他訂閱參數 (目前未使用，間隔由 config.binance_base_interval 決定)。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法訂閱。")
            return
        stream_name = f"{symbol.lower()}@kline_{config.binance_base_interval}"
        if stream_name not in self._subscribed_symbols:
            self.binance_client.subscribe(stream_name)
            self._subscribed_symbols.add(stream_name)
            log.info(f"已訂閱 {stream_name}。")

    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱指定交易對。
        此方法會向幣安 WebSocket 客戶端發送取消訂閱請求，
        停止接收指定交易對基礎時間間隔的 K 線數據。
        如果幣安客戶端未初始化，則會記錄錯誤。

        參數:
            symbol (str): 要取消訂閱的交易對符號。
            **kwargs: 其他取消訂閱參數 (目前未使用)。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法取消訂閱。")
            return
        stream_name = f"{symbol.lower()}@kline_{config.binance_base_interval}"
        if stream_name in self._subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self._subscribed_symbols.remove(stream_name)
            log.info(f"已取消訂閱 {stream_name}。")

    def get_stats(self) -> dict:
        """
        獲取提供者的詳細運行統計數據。
        此方法返回一個字典，包含提供者的運行時間、接收/處理/失敗的消息數量、
        發送到 Kafka 的消息數量、已訂閱的數據流列表、緩存的交易對數量，
        以及 InfluxDB 操作的統計信息。
        """
        uptime = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "subscribed_streams": list(self._subscribed_symbols),
            "cached_symbols_count": len(self._price_cache),
            "influxdb_stats": self.influxdb_manager.get_stats()
        }

    def get_latest_prices(self) -> Dict[str, dict]:
        """
        獲取所有已快取符號的最新價格。
        此方法返回一個字典，其中鍵為交易對符號，值為其最新的價格數據（已轉換為字典格式）。
        """
        return {symbol: data.to_dict() for symbol, data in self._price_cache.items()}

    @property
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號流名稱列表。
        此屬性返回一個列表，包含所有當前正在幣安 WebSocket 上訂閱的數據流名稱。
        """
        return list(self._subscribed_symbols)

    def get_historical_data(self, symbol: str, interval: str, start: datetime, end: datetime, limit: int, offset: int) -> List[
        Dict[str, Any]]:
        """
        從 InfluxDB 獲取歷史 K 線數據，支持分頁和優化的動態聚合。

        此方法從 InfluxDB 查詢指定交易對在給定時間範圍內的歷史 K 線數據。
        它支持兩種模式：
        1. 如果請求的 `interval` 是預聚合的（即在 `config.aggregation_intervals` 中或為基礎間隔），
           則直接查詢對應的 measurement，並應用分頁。
        2. 如果請求的 `interval` 是自定義的，則使用 `find_optimal_source_interval` 找到最高效的
        預聚合數據源進行二次聚合，然後在內存中應用分頁，並被格式化為適合圖表庫使用的字典列表。

        參數:
            symbol (str): 交易對符號。
            interval (str): K 線間隔 (例如 '1m', '5m', '1h', '1d')。
            start (datetime): 查詢的起始時間 (UTC)。
            end (datetime): 查詢的結束時間 (UTC)。
            limit (int): 返回的最大數據點數量。
            offset (int): 偏移量，用於分頁查詢。

        返回:
            List[Dict[str, Any]]: 包含歷史 K 線數據的字典列表。
        """
        log.debug(f"正在為 {symbol} 獲取從 {start} 到 {end} 的歷史數據 {symbol}@{interval}。")

        is_pre_aggregated = interval in config.binance_aggregation_intervals or interval == config.binance_base_interval

        try:
            if is_pre_aggregated:
                measurement = f"crypto_price_{interval}" if interval != config.binance_base_interval else "crypto_price"
                log.debug(f"從預聚合的 measurement '{measurement}' 直接查詢數據。")
                df = self.analyzer.query_direct(symbol, measurement, start, end, limit, offset)
            else:
                base_seconds = interval_to_seconds(config.binance_base_interval)
                target_seconds = interval_to_seconds(interval)

                if not target_seconds or target_seconds < base_seconds or target_seconds % base_seconds != 0:
                    raise ValueError(f"自定義間隔 {interval} 無效或必須是基礎間隔 {config.binance_base_interval} 的整數倍。")

                source_interval, _ = find_optimal_source_interval(interval)
                log.debug(f"為目標間隔 '{interval}' 找到最佳聚合來源: '{source_interval}'。")

                source_measurement = f"crypto_price_{source_interval}" if source_interval != config.binance_base_interval else "crypto_price"

                df = self.analyzer.query_and_aggregate(symbol, source_measurement, start, end, interval)

                if not df.empty and (limit or offset):
                    total_records = len(df)
                    df = df.iloc[offset: offset + limit]
                    log.info(f"對聚合後的 {total_records} 條記錄應用分頁: 偏移 {offset}, 限制 {limit}。")

            if df.empty:
                return []

            df.reset_index(inplace=True)
            df['time'] = df['time'].apply(lambda x: int(x.timestamp()))
            required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            return df[required_columns].to_dict('records')

        except Exception as e:
            log.error(f"獲取 {symbol} 的歷史數據失敗: {e}。")
            return []

    def get_available_symbols(self) -> List[str]:
        """
        從 InfluxDB 獲取所有可用的交易對符號。
        此方法調用內部數據分析器來查詢 InfluxDB，
        並返回數據庫中所有有數據記錄的交易對符號列表。
        """
        log.info("正在獲取所有可用的符號...")
        try:
            return self.analyzer.get_available_symbols()
        except Exception as e:
            log.error(f"獲取可用符號時出錯: {e}。")
            return []
