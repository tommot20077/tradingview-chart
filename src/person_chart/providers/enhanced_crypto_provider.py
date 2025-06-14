import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List, Any

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from ..analysis.data_analyzer import CryptoDataAnalyzer
from .abstract_data_provider import AbstractRealtimeDataProvider, AbstractHistoricalDataProvider
from ..data_models import InfluxDBStats, PriceData

# 檢查 Kafka 是否可用
_KAFKA_AVAILABLE = True
try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None
    _KAFKA_AVAILABLE = False
    logging.warning("kafka-python 未安裝。Kafka 功能將不可用。請運行 'pip install -e .[kafka]' 來安裝。")

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class EnhancedInfluxDBManager:
    """
    增強型 InfluxDB 管理器，支援高效的非同步批次寫入和後台工作執行緒。
    """

    def __init__(self, host: str, token: str, database: str, batch_size: int = 200, flush_interval: int = 5_000):
        """
        初始化 EnhancedInfluxDBManager 實例。

        Parameters:
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
        log.info(f"EnhancedInfluxDBManager 初始化完成，主機: {self.host}, 資料庫: {self.database}")

    def _setup_write_options(self, batch_size: int, flush_interval: int):
        """配置 InfluxDB 寫入選項以優化性能。"""
        log.info("設定增強型 InfluxDB 寫入選項...")

        def success_callback(conf, data: str):
            self.stats.successful_writes += 1
            self.stats.last_write_time = datetime.now(timezone.utc)
            log.debug(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組")

        def error_callback(conf, data: str, exception: InfluxDBError):
            self.stats.failed_writes += 1
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}")

        def retry_callback(conf, data: str, exception: InfluxDBError):
            self.stats.retry_count += 1
            log.warning(f"重試寫入到 InfluxDB: {exception}")

        write_options = WriteOptions(
            batch_size=batch_size, flush_interval=flush_interval, jitter_interval=2_000,
            retry_interval=5_000, max_retries=3, max_retry_delay=30_000, exponential_base=2
        )
        self.write_client_options = write_client_options(
            success_callback=success_callback, error_callback=error_callback,
            retry_callback=retry_callback, write_options=write_options
        )

    def connect(self):
        """連接到 InfluxDB 資料庫。"""
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
        """從 InfluxDB 資料庫斷開連接。"""
        log.info("嘗試從 InfluxDB 斷開連接...")
        if self.client:
            self.client.close()
            self.client = None
            log.info("已從 InfluxDB 斷開連接。")

    def write_price_data(self, price_data: PriceData):
        """
        將價格資料點非同步寫入 InfluxDB。

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

            if price_data.trade_count is not None:
                point = point.field("trade_count", price_data.trade_count)

            self.client.write(point)
            self.stats.total_writes += 1
            log.debug(f"已將 {price_data.symbol} 的價格資料提交至 InfluxDB 寫入緩存。")
        except Exception as e:
            log.error(f"提交價格資料到 InfluxDB 寫入緩存失敗: {e}")

    def get_stats(self) -> dict:
        """獲取 InfluxDB 操作統計數據。"""
        return {
            "total_points_written": self.stats.total_writes,
            "successful_batches": self.stats.successful_writes,
            "failed_batches": self.stats.failed_writes,
            "retry_count": self.stats.retry_count,
            "last_write_time": self.stats.last_write_time.isoformat() if self.stats.last_write_time else None,
        }


class EnhancedCryptoPriceProviderRealtime(AbstractRealtimeDataProvider, AbstractHistoricalDataProvider):
    """
    增強型加密貨幣價格提供者。
    提供即時數據流、歷史數據查詢、快取、Kafka 整合等高級功能。
    """

    def __init__(self,
                 influxdb_manager: EnhancedInfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None,
                 kafka_producer: Optional[KafkaProducer] = None,
                 kafka_topic: Optional[str] = None):
        """
        初始化 EnhancedCryptoPriceProviderRealtime 實例。

        Parameters:
            influxdb_manager (EnhancedInfluxDBManager): 用於管理 InfluxDB 的實例。
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
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="CryptoProviderWorker")
        self.analyzer = CryptoDataAnalyzer(
            host=influxdb_manager.host, token=influxdb_manager.token, database=influxdb_manager.database
        )
        self.stats = {
            "messages_received": 0, "messages_processed": 0, "messages_failed": 0,
            "kafka_messages_sent": 0, "start_time": None
        }
        log.info("EnhancedCryptoPriceProviderRealtime (增強版) 初始化完成。")
        if self.kafka_producer:
            log.info(f"Kafka 模式已啟用，將發佈到主題: {self.kafka_topic}")

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """解析幣安 K 線訊息，計算價格變化並更新快取。"""
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
                timestamp=datetime.fromtimestamp(kline['T'] / 1000, tz=timezone.utc),
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
            log.error(f"解析 K 線資料失敗: {e}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """處理來自幣安的訊息，解析、儲存並分發。"""
        price_data = self._parse_kline_data(message)
        if not price_data:
            return

        # 異步儲存到 InfluxDB
        self._executor.submit(self.influxdb_manager.write_price_data, price_data)

        # 建立用於廣播的增強訊息
        enhanced_message = json.dumps({
            "type": "price_update",
            "data": price_data.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        if self.kafka_producer and self.kafka_topic:
            self.kafka_producer.send(self.kafka_topic, enhanced_message.encode('utf-8'))
            self.stats["kafka_messages_sent"] += 1
        elif self.message_callback:
            self.message_callback(enhanced_message)

    def start(self):
        """啟動價格提供者。"""
        log.info("啟動 EnhancedCryptoPriceProviderRealtime (增強版)...")
        self.stats["start_time"] = datetime.now(timezone.utc)
        self.influxdb_manager.connect()
        self.binance_client = UMFuturesWebsocketClient(on_message=self._handle_binance_message)
        log.info("EnhancedCryptoPriceProviderRealtime (增強版) 已成功啟動。")

    def stop(self):
        """停止價格提供者。"""
        log.info("停止 EnhancedCryptoPriceProviderRealtime (增強版)...")
        if self.binance_client:
            self.binance_client.stop()
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
        self._executor.shutdown(wait=True)
        self.influxdb_manager.disconnect()
        log.info("EnhancedCryptoPriceProviderRealtime (增強版) 已成功停止。")

    def subscribe(self, symbol: str, **kwargs):
        """訂閱指定交易對。"""
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
        """取消訂閱指定交易對。"""
        interval = kwargs.get("interval", "1m")
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法取消訂閱。")
            return
        stream_name = f"{symbol.lower()}@kline_{interval}"
        if stream_name in self._subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self._subscribed_symbols.remove(stream_name)
            log.info(f"已取消訂閱 {stream_name}")

    def get_stats(self) -> dict:
        """獲取提供者的詳細運行統計數據。"""
        uptime = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "subscribed_streams": list(self._subscribed_symbols),
            "cached_symbols_count": len(self._price_cache),
            "influxdb_stats": self.influxdb_manager.get_stats()
        }

    def get_latest_prices(self) -> Dict[str, dict]:
        """獲取所有已快取符號的最新價格。"""
        return {symbol: data.to_dict() for symbol, data in self._price_cache.items()}

    @property
    def subscribed_symbols(self) -> List[str]:
        """獲取當前已訂閱的符號流名稱列表。"""
        return list(self._subscribed_symbols)

    def get_historical_data(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """從 InfluxDB 獲取歷史K線數據。"""
        log.info(f"正在為 {symbol} 獲取從 {start_time} 到 {end_time} 的歷史數據 (間隔: {interval})")
        try:
            df = self.analyzer.get_price_data(symbol, start_time=start_time, end_time=end_time)
            if df.empty:
                return []

            df.reset_index(inplace=True)
            df['time'] = df['time'].apply(lambda x: int(x.timestamp()))
            df_renamed = df.rename(columns={'open_price': 'open', 'high_price': 'high', 'low_price': 'low', 'close_price': 'close'})
            required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            return df_renamed[required_columns].to_dict('records')
        except Exception as e:
            log.error(f"獲取 {symbol} 的歷史數據時出錯: {e}")
            return []

    def get_available_symbols(self) -> List[str]:
        """從 InfluxDB 獲取所有可用的交易對符號。"""
        log.info("正在獲取所有可用的符號...")
        try:
            return self.analyzer.get_available_symbols()
        except Exception as e:
            log.error(f"獲取可用符號時出錯: {e}")
            return []
