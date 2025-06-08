import json
import logging
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty

from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options

@dataclass
class PriceData:
    symbol: str
    price: float
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    trade_count: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class InfluxDBStats:
    """InfluxDB operation statistics"""
    total_writes: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    last_write_time: Optional[datetime] = None
    retry_count: int = 0

class EnhancedInfluxDBManager:
    def __init__(self, host: str, token: str, database: str, batch_size: int = 100):
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
        
        # Setup logging
        self.logger = logging.getLogger(__name__)

    def _setup_write_options(self):
        """Configure InfluxDB write options for optimal performance"""

        def success_callback(self, data: str):
            self.stats.successful_writes += 1
            self.stats.last_write_time = datetime.now(timezone.utc)
            self.logger.debug(f"Successfully wrote batch to InfluxDB: {len(data)} bytes")

        def error_callback(self, data: str, exception: InfluxDBError):
            self.stats.failed_writes += 1
            self.logger.error(f"Failed writing batch to InfluxDB: {exception}")

        def retry_callback(self, data: str, exception: InfluxDBError):
            self.stats.retry_count += 1
            self.logger.warning(f"Retrying write to InfluxDB: {exception}")

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

    def connect(self):
        """Connect to InfluxDB and start worker thread"""
        try:
            self.client = InfluxDBClient3(
                host=self.host,
                token=self.token,
                database=self.database,
                write_client_options=self.write_client_options
            )
            
            # Start background worker thread for writing
            self._worker_thread = threading.Thread(target=self._writer_worker, daemon=True)
            self._worker_thread.start()
            
            self.logger.info(f"Connected to InfluxDB at {self.host}")
        except Exception as e:
            self.logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

    def disconnect(self):
        """Disconnect from InfluxDB and stop worker thread"""
        # Stop worker thread
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        
        if self.client:
            self.client.close()
            self.client = None
            self.logger.info("Disconnected from InfluxDB")

    def _writer_worker(self):
        """Background worker thread for writing data to InfluxDB"""
        batch = []
        
        while not self._stop_event.is_set():
            try:
                # Try to get data with timeout
                try:
                    data = self._write_queue.get(timeout=1.0)
                    batch.append(data)
                except Empty:
                    # If queue is empty, write any pending batch
                    if batch:
                        self._write_batch(batch)
                        batch = []
                    continue
                
                # Write batch when it reaches batch size
                if len(batch) >= self.batch_size:
                    self._write_batch(batch)
                    batch = []
                    
            except Exception as e:
                self.logger.error(f"Error in writer worker: {e}")
        
        # Write any remaining data
        if batch:
            self._write_batch(batch)

    def _write_batch(self, batch: List[Point]):
        """Write a batch of points to InfluxDB"""
        if not self.client or not batch:
            return
        
        try:
            self.client.write(batch)
            self.stats.total_writes += len(batch)
            self.logger.debug(f"Wrote batch of {len(batch)} points to InfluxDB")
        except Exception as e:
            self.logger.error(f"Failed to write batch to InfluxDB: {e}")

    def write_price_data(self, price_data: PriceData):
        """Queue price data for writing to InfluxDB"""
        if not self.client:
            self.logger.error("InfluxDB client not connected")
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
            
            # Add optional fields if available
            if price_data.price_change is not None:
                point = point.field("price_change", price_data.price_change)
            if price_data.price_change_percent is not None:
                point = point.field("price_change_percent", price_data.price_change_percent)
            if price_data.trade_count is not None:
                point = point.field("trade_count", price_data.trade_count)
            
            point = point.time(price_data.timestamp)
            
            # Add to write queue
            self._write_queue.put(point)
            
        except Exception as e:
            self.logger.error(f"Failed to queue price data for InfluxDB: {e}")

    def get_stats(self) -> dict:
        """Get InfluxDB operation statistics"""
        return {
            "total_writes": self.stats.total_writes,
            "successful_writes": self.stats.successful_writes,
            "failed_writes": self.stats.failed_writes,
            "retry_count": self.stats.retry_count,
            "last_write_time": self.stats.last_write_time.isoformat() if self.stats.last_write_time else None,
            "queue_size": self._write_queue.qsize()
        }

class EnhancedCryptoPriceProvider:
    def __init__(self, influxdb_manager: EnhancedInfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None):
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self.subscribed_symbols = set()
        self._price_cache: Dict[str, PriceData] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "start_time": None
        }

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """Parse Binance kline message and extract price data"""
        try:
            data = json.loads(message)
            self.stats["messages_received"] += 1

            if 'k' not in data:
                return None

            kline = data['k']
            
            # Calculate price change if we have previous data
            symbol = kline['s']
            current_price = float(kline['c'])
            price_change = None
            price_change_percent = None
            
            if symbol in self._price_cache:
                previous_price = self._price_cache[symbol].price
                price_change = current_price - previous_price
                if previous_price > 0:
                    price_change_percent = (price_change / previous_price) * 100

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
            
            # Update cache
            self._price_cache[symbol] = price_data
            
            self.stats["messages_processed"] += 1
            return price_data
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.stats["messages_failed"] += 1
            self.logger.error(f"Failed to parse kline data: {e}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """Handle incoming Binance WebSocket messages"""
        try:
            # Parse price data
            price_data = self._parse_kline_data(message)

            if price_data:
                # Store to InfluxDB (asynchronously)
                self._executor.submit(self.influxdb_manager.write_price_data, price_data)

                self.logger.debug(f"Processed {price_data.symbol}: ${price_data.price:.4f}")

                # Create enhanced message for broadcasting
                enhanced_message = json.dumps({
                    "type": "price_update",
                    "data": price_data.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

                # Forward enhanced message to callback (for WebSocket broadcasting)
                if self.message_callback:
                    self.message_callback(enhanced_message)

        except Exception as e:
            self.logger.error(f"Error handling Binance message: {e}")

    def start(self):
        """Start the price provider"""
        try:
            # Connect to InfluxDB
            self.influxdb_manager.connect()

            # Create Binance WebSocket client
            self.binance_client = UMFuturesWebsocketClient(
                on_message=self._handle_binance_message
            )
            
            self.stats["start_time"] = datetime.now(timezone.utc)
            self.logger.info("Enhanced CryptoPriceProvider started")

        except Exception as e:
            self.logger.error(f"Failed to start Enhanced CryptoPriceProvider: {e}")
            raise

    def stop(self):
        """Stop the price provider"""
        try:
            if self.binance_client:
                self.binance_client.stop()
                self.binance_client = None

            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            self.influxdb_manager.disconnect()

            self.logger.info("Enhanced CryptoPriceProvider stopped")

        except Exception as e:
            self.logger.error(f"Error stopping Enhanced CryptoPriceProvider: {e}")

    def subscribe_symbol(self, symbol: str, interval: str = "1m"):
        """Subscribe to a symbol's price stream"""
        if not self.binance_client:
            self.logger.error("Binance client not initialized")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name not in self.subscribed_symbols:
            self.binance_client.subscribe(stream_name)
            self.subscribed_symbols.add(stream_name)
            self.logger.info(f"Subscribed to {stream_name}")
        else:
            self.logger.info(f"Already subscribed to {stream_name}")

    def unsubscribe_symbol(self, symbol: str, interval: str = "1m"):
        """Unsubscribe from a symbol's price stream"""
        if not self.binance_client:
            self.logger.error("Binance client not initialized")
            return

        stream_name = f"{symbol.lower()}@kline_{interval}"

        if stream_name in self.subscribed_symbols:
            self.binance_client.unsubscribe(stream_name)
            self.subscribed_symbols.remove(stream_name)
            self.logger.info(f"Unsubscribed from {stream_name}")
        else:
            self.logger.info(f"Not subscribed to {stream_name}")

    def get_stats(self) -> dict:
        """Get provider statistics"""
        current_time = datetime.now(timezone.utc)
        uptime = None
        if self.stats["start_time"]:
            uptime = (current_time - self.stats["start_time"]).total_seconds()
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "subscribed_symbols": list(self.subscribed_symbols),
            "cached_symbols": list(self._price_cache.keys()),
            "influxdb_stats": self.influxdb_manager.get_stats()
        }

    def get_latest_prices(self) -> Dict[str, dict]:
        """Get latest cached prices for all symbols"""
        return {symbol: data.to_dict() for symbol, data in self._price_cache.items()}
