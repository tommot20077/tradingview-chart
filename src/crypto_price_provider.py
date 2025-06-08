import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

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


class InfluxDBManager:
    def __init__(self, host: str, token: str, database: str):
        self.host = host
        self.token = token
        self.database = database
        self.client: Optional[InfluxDBClient3] = None
        self._setup_write_options()

    def _setup_write_options(self):
        """Configure InfluxDB write options for optimal performance"""

        def success_callback(self, data: str):
            logging.info(f"Successfully wrote batch to InfluxDB: {len(data)} bytes")

        def error_callback(self, data: str, exception: InfluxDBError):
            logging.error(f"Failed writing batch to InfluxDB: {exception}")

        def retry_callback(self, data: str, exception: InfluxDBError):
            logging.warning(f"Retrying write to InfluxDB: {exception}")

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

    def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient3(
                host=self.host,
                token=self.token,
                database=self.database,
                write_client_options=self.write_client_options
            )
            logging.info(f"Connected to InfluxDB at {self.host}")
        except Exception as e:
            logging.error(f"Failed to connect to InfluxDB: {e}")
            raise

    def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.client:
            self.client.close()
            self.client = None
            logging.info("Disconnected from InfluxDB")

    def write_price_data(self, price_data: PriceData):
        """Write price data to InfluxDB"""
        if not self.client:
            logging.error("InfluxDB client not connected")
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
        except Exception as e:
            logging.error(f"Failed to write price data to InfluxDB: {e}")


class CryptoPriceProvider:
    def __init__(self, influxdb_manager: InfluxDBManager,
                 message_callback: Optional[Callable[[str], None]] = None):
        self.influxdb_manager = influxdb_manager
        self.message_callback = message_callback
        self.binance_client: Optional[UMFuturesWebsocketClient] = None
        self.subscribed_symbols = set()

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _parse_kline_data(self, message: str) -> Optional[PriceData]:
        """Parse Binance kline message and extract price data"""
        try:
            data = json.loads(message)

            if 'k' not in data:
                return None

            kline = data['k']

            return PriceData(
                symbol=kline['s'],
                price=float(kline['c']),  # Close price as current price
                timestamp=datetime.fromtimestamp(kline['T'] / 1000),  # Close time
                open_price=float(kline['o']),
                high_price=float(kline['h']),
                low_price=float(kline['l']),
                close_price=float(kline['c']),
                volume=float(kline['v'])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse kline data: {e}")
            return None

    def _handle_binance_message(self, ws, message: str):
        """Handle incoming Binance WebSocket messages"""
        try:
            # Parse price data
            price_data = self._parse_kline_data(message)

            if price_data:
                # Store to InfluxDB
                self.influxdb_manager.write_price_data(price_data)

                self.logger.info(f"Processed {price_data.symbol}: ${price_data.price}")

            # Forward message to callback (for WebSocket broadcasting)
            if self.message_callback:
                self.message_callback(message)

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

            self.logger.info("CryptoPriceProvider started")

        except Exception as e:
            self.logger.error(f"Failed to start CryptoPriceProvider: {e}")
            raise

    def stop(self):
        """Stop the price provider"""
        try:
            if self.binance_client:
                self.binance_client.stop()
                self.binance_client = None

            self.influxdb_manager.disconnect()

            self.logger.info("CryptoPriceProvider stopped")

        except Exception as e:
            self.logger.error(f"Error stopping CryptoPriceProvider: {e}")

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
