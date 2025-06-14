import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from queue import Queue, Empty
from typing import Optional, Callable, Dict, List, Any

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

from src.data_analyzer import CryptoDataAnalyzer

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None
    logging.warning("KafkaProducer 無法導入。請確保已安裝 'kafka-python' 以啟用 Kafka 功能。")

from abstract_data_provider import AbstractRealtimeDataProvider, AbstractHistoricalDataProvider
from data_models import InfluxDBStats, PriceData

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class EnhancedInfluxDBManager:
    """
    增強型 InfluxDB 管理器，支援批次寫入和後台工作執行緒。
    """

    def __init__(self, host: str, token: str, database: str, batch_size: int = 100):
        """
        初始化 EnhancedInfluxDBManager 實例。

        輸入:
            host (str): InfluxDB 服務器的主機位址。
            token (str): 用於 InfluxDB 認證的令牌。
            database (str): 要連接的 InfluxDB 資料庫名稱。
            batch_size (int): 批次寫入的點數大小，預設為 100。

        """
        self.host = host
        self.token = token
        self.database = database
        self.batch_size = batch_size
        self.client: Optional[InfluxDBClient3] = None
        self.stats = InfluxDBStats()
        self._write_queue = Queue()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._setup_write_options()
        log.info(
            f"EnhancedInfluxDBManager 初始化完成，主機: {self.host}, 資料庫: {self.database}, 批次大小: {self.batch_size}")

    def _setup_write_options(self):
        """
        配置 InfluxDB 寫入選項以優化性能。
        此方法設定批次寫入、刷新間隔、重試策略等。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。

        輸出:
            無。
        """
        log.info("設定 InfluxDB 寫入選項...")

        def success_callback(conf, data: str):
            """
            批次寫入成功時的回調函數。

            輸入:
                conf: 寫入配置。
                data (str): 成功寫入的資料字串。

            輸出:
                無。
            """
            self.stats.successful_writes += 1
            self.stats.last_write_time = datetime.now(timezone.utc)
            log.debug(f"成功寫入批次資料到 InfluxDB: {len(data)} 位元組")

        def error_callback(conf, data: str, exception: InfluxDBError):
            """
            批次寫入失敗時的回調函數。

            輸入:
                conf: 寫入配置。
                data (str): 寫入失敗的資料字串。
                exception (InfluxDBError): 寫入失敗時的異常。

            輸出:
                無。
            """
            self.stats.failed_writes += 1
            log.error(f"寫入批次資料到 InfluxDB 失敗: {exception}")

        def retry_callback(conf, data: str, exception: InfluxDBError):
            """
            批次寫入重試時的回調函數。

            輸入:
                conf: 寫入配置。
                data (str): 正在重試寫入的資料字串。
                exception (InfluxDBError): 重試時的異常。

            輸出:
                無。
            """
            self.stats.retry_count += 1
            log.warning(f"重試寫入到 InfluxDB: {exception}")

        write_options = WriteOptions(
            batch_size=self.batch_size,
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
        連接到 InfluxDB 資料庫並啟動後台寫入工作執行緒。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。

        輸出:
            無。

        異常:
            Exception: 如果連接失敗則拋出異常。
        """
        log.info("嘗試連接到 InfluxDB 並啟動寫入工作執行緒...")
        try:
            self.client = InfluxDBClient3(
                host=self.host,
                token=self.token,
                database=self.database,
                write_client_options=self.write_client_options
            )

            # 啟動後台寫入工作執行緒
            self._worker_thread = threading.Thread(target=self._writer_worker, daemon=True)
            self._worker_thread.start()

            log.info(f"成功連接到 InfluxDB，主機: {self.host}")
        except Exception as e:
            log.error(f"連接到 InfluxDB 失敗: {e}")
            raise

    def disconnect(self):
        """
        從 InfluxDB 資料庫斷開連接並停止後台工作執行緒。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。

        輸出:
            無。
        """
        log.info("嘗試從 InfluxDB 斷開連接並停止寫入工作執行緒...")
        # 停止工作執行緒
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
            log.info("寫入工作執行緒已停止。")

        if self.client:
            self.client.close()
            self.client = None
            log.info("已從 InfluxDB 斷開連接。")
        else:
            log.info("InfluxDB 客戶端未連接，無需斷開。")

    def _writer_worker(self):
        """
        後台工作執行緒，用於將數據寫入 InfluxDB。
        它從佇列中獲取數據點並以批次形式寫入。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。

        輸出:
            無。
        """
        log.info("InfluxDB 寫入工作執行緒啟動。")
        batch = []

        while not self._stop_event.is_set():
            try:
                # 嘗試從佇列中獲取數據，設定超時時間
                try:
                    data = self._write_queue.get(timeout=1.0)
                    batch.append(data)
                except Empty:
                    # 如果佇列為空，寫入任何待處理的批次
                    if batch:
                        self._write_batch(batch)
                        batch = []
                    continue

                # 當批次達到指定大小時寫入
                if len(batch) >= self.batch_size:
                    self._write_batch(batch)
                    batch = []

            except Exception as e:
                log.error(f"寫入工作執行緒中發生錯誤: {e}")

        # 寫入任何剩餘的數據
        if batch:
            self._write_batch(batch)
        log.info("InfluxDB 寫入工作執行緒停止。")

    def _write_batch(self, batch: List[Point]):
        """
        將一批數據點寫入 InfluxDB。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。
            batch (List[Point]): 要寫入的數據點列表。

        輸出:
            無。
        """
        if not self.client or not batch:
            log.debug("客戶端未連接或批次為空，無法寫入。")
            return

        try:
            self.client.write(batch)
            self.stats.total_writes += len(batch)
            log.debug(f"已將 {len(batch)} 個點的批次寫入 InfluxDB。")
        except Exception as e:
            log.error(f"寫入批次到 InfluxDB 失敗: {e}")

    def write_price_data(self, price_data: PriceData):
        """
        將價格資料加入佇列，等待寫入 InfluxDB。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。
            price_data (PriceData): 包含要寫入的價格資料的 PriceData 物件。

        輸出:
            無。
        """
        if not self.client:
            log.error("InfluxDB 客戶端未連接，無法將資料加入佇列。")
            return

        try:
            point = (Point("crypto_price")
                     .tag("symbol", price_data.symbol)
                     .field("price", price_data.price)
                     .field("open", price_data.open_price)
                     .field("high", price_data.high_price)
                     .field("low", price_data.low_price)
                     .field("close", price_data.close_price)
                     .field("volume", price_data.volume))

            # 如果可用，添加可選欄位
            if price_data.price_change is not None:
                point = point.field("price_change", price_data.price_change)
            if price_data.price_change_percent is not None:
                point = point.field("price_change_percent", price_data.price_change_percent)
            if price_data.trade_count is not None:
                point = point.field("trade_count", price_data.trade_count)

            point = point.time(price_data.timestamp)

            # 加入寫入佇列
            self._write_queue.put(point)
            log.debug(f"已將 {price_data.symbol} 的價格資料加入寫入佇列。佇列大小: {self._write_queue.qsize()}")

        except Exception as e:
            log.error(f"將價格資料加入 InfluxDB 佇列失敗: {e}")

    def get_stats(self) -> dict:
        """
        獲取 InfluxDB 操作統計數據。

        輸入:
            self (EnhancedInfluxDBManager): EnhancedInfluxDBManager 實例本身。

        輸出:
            dict: 包含總寫入數、成功寫入數、失敗寫入數、重試次數、最後寫入時間和佇列大小的字典。
        """
        log.debug("獲取 InfluxDB 操作統計。")
        return {
            "total_writes": self.stats.total_writes,
            "successful_writes": self.stats.successful_writes,
            "failed_writes": self.stats.failed_writes,
            "retry_count": self.stats.retry_count,
            "last_write_time": self.stats.last_write_time.isoformat() if self.stats.last_write_time else None,
            "queue_size": self._write_queue.qsize()
        }


class EnhancedCryptoPriceProviderRealtime(AbstractRealtimeDataProvider, AbstractHistoricalDataProvider):
    """
    增強型加密貨幣價格提供者，此類為 AbstractDataProvider 的實現，
    從幣安 WebSocket 獲取數據，進行處理，並異步儲存到 InfluxDB。
    可選地發佈到 Kafka 主題或通過回調函數處理。
    """

    def __init__(self,
                 influxdb_manager: EnhancedInfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None,
                 kafka_producer: Optional[KafkaProducer] = None,
                 kafka_topic: Optional[str] = None):
        """
        初始化 EnhancedCryptoPriceProvider 實例。

        輸入:
            influxdb_manager (EnhancedInfluxDBManager): 用於管理 InfluxDB 連接和寫入的實例。
            message_callback (Optional[Callable[[str], None]]): 可選的回調函數，用於處理接收到的原始 WebSocket 訊息。
            kafka_producer (Optional[KafkaProducer]): 可選的 Kafka 生產者實例。
            kafka_topic (Optional[str]): 可選的 Kafka 主題名稱。
        """
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.kafka_producer = kafka_producer if KafkaProducer else None
        self.kafka_topic = kafka_topic
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self._subscribed_symbols = set()
        self._price_cache: Dict[str, PriceData] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.analyzer = CryptoDataAnalyzer(
            host=influxdb_manager.host,
            token=influxdb_manager.token,
            database=influxdb_manager.database
        )
        # 統計數據
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "kafka_messages_sent": 0,
            "start_time": None
        }
        log.info("EnhancedCryptoPriceProvider 初始化完成。")

        if self.kafka_producer:
            log.info(f"Kafka 模式已啟用，將發佈到主題: {self.kafka_topic}")
        else:
            log.info("Kafka 模式已禁用，將使用直接回調。")

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """
        解析幣安 K 線 WebSocket 訊息並提取價格資料。
        同時計算價格變化和變化百分比。

        輸入:
            message (str): 來自幣安 WebSocket 的原始 JSON 訊息字串。

        輸出:
            Optional[PriceData]: 如果解析成功則返回 PriceData 物件，否則返回 None。
        """
        try:
            data = json.loads(message)
            self.stats["messages_received"] += 1
            log.debug(f"接收到訊息，總數: {self.stats['messages_received']}")

            if 'k' not in data:
                log.debug("接收到的訊息不包含 K 線資料。")
                return None

            kline = data['k']

            # 如果有先前的數據，計算價格變化
            symbol = kline['s']
            current_price = float(kline['c'])
            price_change = None
            price_change_percent = None

            if symbol in self._price_cache:
                previous_price = self._price_cache[symbol].price
                price_change = current_price - previous_price
                if previous_price > 0:
                    price_change_percent = (price_change / previous_price) * 100
                log.debug(f"{symbol} 價格變化: {price_change:.4f}, 百分比: {price_change_percent:.2f}%")

            price_data = PriceData(
                symbol=symbol,
                price=current_price,
                timestamp=datetime.fromtimestamp(kline['T'] / 1000, tz=timezone.utc),
                open_price=float(kline['o']),
                high_price=float(kline['h']),
                low_price=float(kline['l']),
                close_price=float(kline['c']),
                volume=float(kline['v']),
                price_change=price_change,
                price_change_percent=price_change_percent,
                trade_count=int(kline['n']) if 'n' in kline else None
            )

            # 更新快取
            self._price_cache[symbol] = price_data

            self.stats["messages_processed"] += 1
            log.debug(
                f"成功解析 K 線資料: {price_data.symbol} @ {price_data.price}。已處理訊息總數: {self.stats['messages_processed']}")
            return price_data

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.stats["messages_failed"] += 1
            log.error(f"解析 K 線資料失敗: {e}，原始訊息: {message}。失敗訊息總數: {self.stats['messages_failed']}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """
        處理來自幣安 WebSocket 的傳入訊息。
        此方法解析訊息，將價格資料異步寫入 InfluxDB，並將增強後的訊息轉發給回調函數（如果已提供）。

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
                # 異步儲存到 InfluxDB
                self._executor.submit(self.influxdb_manager.write_price_data, price_data)
                log.debug(f"已將 {price_data.symbol} 的價格資料提交給 InfluxDB 寫入。")

                # 建立用於廣播的增強訊息
                enhanced_message = json.dumps({
                    "type": "price_update",
                    "data": price_data.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

                if self.kafka_producer and self.kafka_topic:
                    self.kafka_producer.send(self.kafka_topic, value=enhanced_message)
                    self.stats["kafka_messages_sent"] += 1
                    log.debug(f"增強訊息已發送到 Kafka 主題 {self.kafka_topic}。")
                elif self.message_callback:
                    self.message_callback(enhanced_message)
                    log.debug("增強訊息已轉發給回調函數。")

        except Exception as e:
            log.error(f"處理幣安訊息時發生錯誤: {e}，原始訊息: {message}")

    def start(self):
        """
        啟動價格提供者。
        此方法連接到 InfluxDB 並初始化幣安 WebSocket 客戶端。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。

        輸出:
            無。

        異常:
            Exception: 如果啟動失敗則拋出異常。
        """
        log.info("啟動 Enhanced CryptoPriceProvider...")
        try:
            # 連接到 InfluxDB
            self.influxdb_manager.connect()

            # 建立幣安 WebSocket 客戶端
            self.binance_client = UMFuturesWebsocketClient(
                on_message=self._handle_binance_message
            )

            self.stats["start_time"] = datetime.now(timezone.utc)
            log.info("Enhanced CryptoPriceProvider 已成功啟動。")

        except Exception as e:
            log.error(f"啟動 Enhanced CryptoPriceProvider 失敗: {e}")
            raise

    def stop(self):
        """
        停止價格提供者。
        此方法停止幣安 WebSocket 客戶端，關閉執行緒池，並斷開與 InfluxDB 的連接。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。

        輸出:
            無。
        """
        log.info("停止 Enhanced CryptoPriceProvider...")
        try:
            if self.binance_client:
                self.binance_client.stop()
                self.binance_client = None
                log.info("幣安 WebSocket 客戶端已停止。")

            if self.kafka_producer:
                log.info("正在刷新並關閉 Kafka 生產者...")
                self.kafka_producer.flush()
                self.kafka_producer.close()
                log.info("Kafka 生產者已關閉。")

            # 關閉執行緒池
            self._executor.shutdown(wait=True)
            log.info("執行緒池已關閉。")

            self.influxdb_manager.disconnect()
            log.info("Enhanced CryptoPriceProvider 已成功停止。")

        except Exception as e:
            log.error(f"停止 Enhanced CryptoPriceProvider 時發生錯誤: {e}")

    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱指定交易對的價格串流。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。
            symbol (str): 要訂閱的交易對符號 (例如 'btcusdt')。
            interval (str): K 線資料的時間間隔 (例如 '1m', '5m')。預設為 '1m'。

        輸出:
            無。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法訂閱。")
            return

        interval = kwargs.get("interval", "1m")
        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name not in self._subscribed_symbols:
            self.binance_client.subscribe(stream_name)
            self._subscribed_symbols.add(stream_name)
            log.info(f"已訂閱 {stream_name}")
        else:
            log.info(f"已訂閱 {stream_name}，無需重複訂閱。")

    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱指定交易對的價格串流。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。
            symbol (str): 要取消訂閱的交易對符號 (例如 'btcusdt')。
            interval (str): K 線資料的時間間隔 (例如 '1m', '5m')。預設為 '1m'。

        輸出:
            無。
        """
        if not self.binance_client:
            log.error("幣安客戶端未初始化，無法取消訂閱。")
            return

        interval = kwargs.get("interval", "1m")
        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name in self._subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self._subscribed_symbols.remove(stream_name)
            log.info(f"已取消訂閱 {stream_name}")
        else:
            log.info(f"未訂閱 {stream_name}，無需取消。")

    def get_stats(self) -> dict:
        """
        獲取價格提供者的運行統計數據。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。

        輸出:
            dict: 包含接收訊息數、處理訊息數、失敗訊息數、運行時間、已訂閱符號、快取符號和 InfluxDB 統計數據的字典。
        """
        log.debug("獲取價格提供者統計數據。")
        current_time = datetime.now(timezone.utc)
        uptime = None
        if self.stats["start_time"]:
            uptime = (current_time - self.stats["start_time"]).total_seconds()

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "subscribed_symbols": list(self._subscribed_symbols),
            "cached_symbols": list(self._price_cache.keys()),
            "influxdb_stats": self.influxdb_manager.get_stats()
        }

    def get_latest_prices(self) -> Dict[str, dict]:
        """
        獲取所有已快取符號的最新價格。

        輸入:
            self (EnhancedCryptoPriceProvider): EnhancedCryptoPriceProvider 實例本身。

        輸出:
            Dict[str, dict]: 鍵為符號，值為 PriceData 物件的字典表示形式。
        """
        log.debug("獲取所有已快取符號的最新價格。")
        return {symbol: data.to_dict() for symbol, data in self._price_cache.items()}

    @property
    def subscribed_symbols(self) -> List[str]:
        return list(self._subscribed_symbols)

    def get_historical_data(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """
        從 InfluxDB 獲取歷史K線數據。
        注意: 'interval' 參數目前用於日誌記錄，實際數據間隔取決於存儲在數據庫中的數據。
        未來的版本可以實現基於 interval 的數據降採樣。
        """
        log.info(f"正在為 {symbol} 獲取從 {start_time} 到 {end_time} 的歷史數據 (間隔: {interval})")
        try:
            df = self.analyzer.get_price_data(symbol, start_time=start_time, end_time=end_time)
            if df.empty:
                return []

            df.reset_inplace = True
            df['time'] = df['time'].apply(lambda x: int(x.timestamp()))

            # 選擇並重命名列以匹配圖表庫要求
            df_renamed = df.rename(columns={
                'open_price': 'open',
                'high_price': 'high',
                'low_price': 'low',
                'close_price': 'close'
            })

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
