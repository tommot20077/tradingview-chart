#!/usr/bin/env python3
"""
Example: How to implement a custom data provider.

This example shows how to create a custom data provider by extending
the AbstractDataProvider interface. We'll implement a simple CSV-based
data provider that reads historical data from files.
"""

import asyncio
import csv
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide
from asset_core.providers.base import AbstractDataProvider


class CSVDataProvider(AbstractDataProvider):
    """CSV-based data provider for historical data analysis."""

    def __init__(self, data_directory: Path):
        """Initialize CSV data provider.

        Args:
            data_directory: Directory containing CSV files with historical data
        """
        self.data_directory = Path(data_directory)
        self._connected = False
        self._name = "csv_provider"

    @property
    def name(self) -> str:
        """Get provider name."""
        return self._name

    async def connect(self) -> None:
        """Connect to the data provider (validate data directory)."""
        if not self.data_directory.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_directory}")

        if not self.data_directory.is_dir():
            raise ValueError(f"Data path is not a directory: {self.data_directory}")

        self._connected = True
        print(f"✅ Connected to CSV data provider: {self.data_directory}")

    async def disconnect(self) -> None:
        """Disconnect from the data provider."""
        self._connected = False
        print("📤 Disconnected from CSV data provider")

    async def stream_trades(
        self,
        symbol: str,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream trades from CSV file.

        Expected CSV format: timestamp,symbol,trade_id,price,quantity,side
        """
        if not self._connected:
            raise RuntimeError("Provider not connected")

        trades_file = self.data_directory / f"{symbol.lower()}_trades.csv"
        if not trades_file.exists():
            raise FileNotFoundError(f"Trades file not found: {trades_file}")

        with open(trades_file) as file:
            reader = csv.DictReader(file)
            for row in reader:
                timestamp = datetime.fromisoformat(row["timestamp"]).replace(tzinfo=UTC)

                # Skip trades before start_from if specified
                if start_from and timestamp < start_from:
                    continue

                trade = Trade(
                    symbol=row["symbol"],
                    trade_id=row["trade_id"],
                    price=Decimal(row["price"]),
                    quantity=Decimal(row["quantity"]),
                    side=TradeSide(row["side"]),
                    timestamp=timestamp,
                )

                yield trade

                # Add small delay to simulate real-time streaming
                await asyncio.sleep(0.001)

    async def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Kline]:
        """Stream klines from CSV file.

        Expected CSV format: open_time,close_time,symbol,interval,open,high,low,close,volume,quote_volume,trades_count
        """
        if not self._connected:
            raise RuntimeError("Provider not connected")

        klines_file = self.data_directory / f"{symbol.lower()}_klines_{interval.value}.csv"
        if not klines_file.exists():
            raise FileNotFoundError(f"Klines file not found: {klines_file}")

        with open(klines_file) as file:
            reader = csv.DictReader(file)
            for row in reader:
                open_time = datetime.fromisoformat(row["open_time"]).replace(tzinfo=UTC)

                # Skip klines before start_from if specified
                if start_from and open_time < start_from:
                    continue

                kline = Kline(
                    symbol=row["symbol"],
                    interval=KlineInterval(row["interval"]),
                    open_time=open_time,
                    close_time=datetime.fromisoformat(row["close_time"]).replace(tzinfo=UTC),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=Decimal(row["volume"]),
                    quote_volume=Decimal(row["quote_volume"]),
                    trades_count=int(row["trades_count"]),
                )

                yield kline

                # Add small delay to simulate real-time streaming
                await asyncio.sleep(0.01)

    async def fetch_historical_trades(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Trade]:
        """Fetch historical trades from CSV file."""
        trades = []
        count = 0

        async for trade in self.stream_trades(symbol, start_from=start_time):
            if trade.timestamp >= end_time:
                break

            trades.append(trade)
            count += 1

            if limit and count >= limit:
                break

        return trades

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Kline]:
        """Fetch historical klines from CSV file."""
        klines = []
        count = 0

        async for kline in self.stream_klines(symbol, interval, start_from=start_time):
            if kline.open_time >= end_time:
                break

            klines.append(kline)
            count += 1

            if limit and count >= limit:
                break

        return klines

    async def get_exchange_info(self) -> dict[str, Any]:
        """Get exchange information from metadata file."""
        metadata_file = self.data_directory / "exchange_info.json"
        if metadata_file.exists():
            import json

            with open(metadata_file) as file:
                return json.load(file)

        # Default exchange info if no metadata file
        return {
            "exchange": "csv_data",
            "symbols": self._discover_symbols(),
            "status": "TRADING",
        }

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Get symbol information."""
        return {
            "symbol": symbol,
            "status": "TRADING",
            "price_precision": 8,
            "quantity_precision": 8,
            "base_asset": symbol.split("USDT")[0] if "USDT" in symbol else symbol[:3],
            "quote_asset": "USDT" if "USDT" in symbol else symbol[3:],
        }

    async def ping(self) -> float:
        """Ping the provider (simulate file system latency)."""
        import time

        start = time.time()

        # Test file access
        list(self.data_directory.iterdir())

        end = time.time()
        return (end - start) * 1000  # Convert to milliseconds

    async def close(self) -> None:
        """Close all connections and clean up resources."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self._connected

    def _discover_symbols(self) -> list[str]:
        """Discover available symbols from CSV files."""
        symbols = set()

        for csv_file in self.data_directory.glob("*_trades.csv"):
            symbol = csv_file.stem.replace("_trades", "").upper()
            symbols.add(symbol)

        for csv_file in self.data_directory.glob("*_klines_*.csv"):
            symbol = csv_file.stem.split("_klines_")[0].upper()
            symbols.add(symbol)

        return sorted(symbols)


async def main():
    """Example usage of the custom CSV data provider."""

    # Create sample data directory (in real usage, this would contain your CSV files)
    data_dir = Path("./sample_data")
    data_dir.mkdir(exist_ok=True)

    # Create sample CSV file for demonstration
    sample_trades_file = data_dir / "btcusdt_trades.csv"
    if not sample_trades_file.exists():
        with open(sample_trades_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "symbol", "trade_id", "price", "quantity", "side"])

            # Sample trades
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            for i in range(10):
                timestamp = base_time.replace(second=i)
                writer.writerow(
                    [
                        timestamp.isoformat(),
                        "BTCUSDT",
                        f"trade_{i}",
                        f"{50000 + i * 10}",
                        "0.001",
                        "buy" if i % 2 == 0 else "sell",
                    ]
                )

    # Initialize and use the custom provider
    provider = CSVDataProvider(data_dir)

    try:
        # Connect to the provider
        await provider.connect()

        # Test basic functionality
        print(f"Provider name: {provider.name}")
        print(f"Is connected: {provider.is_connected}")

        # Get exchange info
        exchange_info = await provider.get_exchange_info()
        print(f"Exchange info: {exchange_info}")

        # Get symbol info
        symbol_info = await provider.get_symbol_info("BTCUSDT")
        print(f"Symbol info: {symbol_info}")

        # Test ping
        latency = await provider.ping()
        print(f"Latency: {latency:.2f}ms")

        # Stream some trades
        print("\n📈 Streaming trades:")
        count = 0
        async for trade in provider.stream_trades("BTCUSDT"):
            print(f"  {trade}")
            count += 1
            if count >= 3:  # Just show first 3 trades
                break

        # Fetch historical trades
        print("\n📊 Historical trades:")
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 0, 5, tzinfo=UTC)

        historical_trades = await provider.fetch_historical_trades("BTCUSDT", start_time, end_time, limit=5)

        for trade in historical_trades:
            print(f"  {trade}")

    finally:
        # Always clean up
        await provider.close()


if __name__ == "__main__":
    print("🚀 Custom Data Provider Example")
    print("=" * 50)
    asyncio.run(main())
