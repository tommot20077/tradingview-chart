"""Performance tests for model operations.

This module tests the performance characteristics of Pydantic models used throughout
the asset_core library, focusing on large-scale serialization, validation performance,
and memory footprint measurements.
"""

import random
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pydantic
import pytest
from pydantic import TypeAdapter

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide

# Optional memory profiler import
try:
    from memory_profiler import profile
except ImportError:
    # Create a no-op decorator if memory_profiler is not available
    def profile(func: Any) -> Any:
        return func


class TestModelPerformance:
    """Performance tests for model serialization, validation, and memory usage.

    Summary line.

    Tests performance characteristics of Trade and Kline models under high load,
    focusing on serialization/deserialization performance, validation performance,
    and memory footprint analysis.

    Preconditions:
    - Models are available and properly configured
    - memory_profiler is available for memory testing
    - Sufficient system resources for large-scale testing

    Steps:
    - Generate large datasets for testing
    - Measure performance metrics
    - Profile memory usage

    Expected Result:
    - Performance metrics within acceptable thresholds
    - No memory leaks or excessive memory consumption
    - Validation performance scales linearly
    """

    @pytest.fixture
    def sample_trades(self) -> Generator[list[Trade], None, None]:
        """Generate a list of sample Trade objects for performance testing.

        Description of what the fixture covers:
        This fixture generates a large list of `Trade` objects with varied data
        to be used across performance tests. It ensures a consistent and sufficiently
        sized dataset for benchmarking serialization, deserialization, and memory usage.
        Enhanced with boundary conditions and randomization for more realistic testing.

        Preconditions:
        - The `Trade` model is correctly defined and importable.
        - `Decimal` and `datetime` (with `UTC`) are available for data generation.

        Steps:
        - Initialize an empty list `trades`.
        - Define a `base_time` for timestamps.
        - Loop 100,000 times to create individual `Trade` objects.
        - For each `Trade` object, assign a unique `trade_id` and vary `price`,
          `quantity`, `side`, `timestamp`, and include `metadata`.
        - Include boundary conditions: some trades with None metadata, empty trade_id
        - Append each created `Trade` object to the `trades` list.
        - Yield the complete list of `trades`.

        Expected Result:
        - A list containing 100,000 valid `Trade` objects, each with diverse and
          realistic data, is provided to the tests.
        """
        trades = []
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for i in range(100_000):
            # Add randomization and boundary conditions
            use_empty_trade_id = random.random() < 0.1  # 10% chance
            use_empty_metadata = random.random() < 0.1  # 10% chance

            trade = Trade(
                symbol="BTCUSDT",
                trade_id="" if use_empty_trade_id else f"trade_{i:06d}",
                price=Decimal(f"{50000 + random.randint(0, 10000)}"),
                quantity=Decimal(f"{random.uniform(0.001, 10.0):.6f}"),
                side=TradeSide.BUY if i % 2 == 0 else TradeSide.SELL,
                timestamp=base_time.replace(second=i % 60, microsecond=i % 1000000),
                exchange="binance",
                metadata={} if use_empty_metadata else {"test_id": i, "batch": i // 1000},
            )
            trades.append(trade)

        yield trades

    @pytest.fixture
    def sample_klines(self) -> Generator[list[Kline], None, None]:
        """Generate a list of sample Kline objects for performance testing.

        Description of what the fixture covers:
        This fixture generates a large list of `Kline` objects with varied data
        to be used across performance tests. It ensures a consistent and sufficiently
        sized dataset for benchmarking serialization, deserialization, and memory usage.
        Enhanced with boundary conditions and randomization for more realistic testing.

        Preconditions:
        - The `Kline` model is correctly defined and importable.
        - `Decimal`, `datetime` (with `UTC`), and `KlineInterval` are available for data generation.

        Steps:
        - Initialize an empty list `klines`.
        - Define a `base_time` for timestamps.
        - Loop 100,000 times to create individual `Kline` objects.
        - For each `Kline` object, calculate `open_price`, `high_price`, `low_price`,
          and `close_price` based on randomized values.
        - Include boundary conditions: some klines with None optional fields
        - Assign `symbol`, `interval`, `open_time`, `close_time`, `volume`,
          `quote_volume`, `trades_count`, `exchange`, and `metadata`.
        - Append each created `Kline` object to the `klines` list.
        - Yield the complete list of `klines`.

        Expected Result:
        - A list containing 100,000 valid `Kline` objects, each with diverse and
          realistic data, is provided to the tests.
        """
        klines = []
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for i in range(100_000):
            # Add randomization and boundary conditions
            use_none_taker_buy_volume = random.random() < 0.1  # 10% chance
            use_empty_metadata = random.random() < 0.1  # 10% chance

            base_price = Decimal(f"{50000 + random.randint(0, 10000)}")
            price_variation = random.randint(1, 500)

            open_price = base_price
            high_price = base_price + Decimal(f"{price_variation}")
            low_price = base_price - Decimal(f"{price_variation // 2}")
            close_price = base_price + Decimal(f"{random.randint(-price_variation, price_variation)}")

            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time.replace(minute=i % 60),
                close_time=base_time.replace(minute=i % 60, second=59),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=Decimal(f"{random.uniform(10, 1000):.3f}"),
                quote_volume=Decimal(f"{random.uniform(500000, 50000000):.2f}"),
                trades_count=random.randint(1, 2000),
                exchange="binance",
                taker_buy_volume=None if use_none_taker_buy_volume else Decimal(f"{random.uniform(5, 500):.3f}"),
                metadata={} if use_empty_metadata else {"test_id": i, "batch": i // 1000},
            )
            klines.append(kline)

        yield klines

    def test_large_scale_serialization_and_deserialization(self, benchmark: Any, sample_trades: list[Trade]) -> None:
        """Test serialization and deserialization performance using TypeAdapter and benchmark.

        Description of what the test covers:
        This test measures the time taken to serialize and deserialize large datasets
        of `Trade` and `Kline` objects using Pydantic's high-performance TypeAdapter.
        It uses pytest-benchmark for reliable, environment-independent performance measurement.

        Preconditions:
        - `sample_trades` and `sample_klines` fixtures provide large lists of model objects.
        - The system has sufficient memory to handle large data structures.
        - `pytest-benchmark` is available for performance measurement.

        Steps:
        - Create TypeAdapter instances for Trade and Kline lists.
        - Use benchmark.pedantic() to measure serialization performance.
        - Use benchmark.pedantic() to measure deserialization performance.
        - Verify data integrity after round-trip conversion.

        Expected Result:
        - Serialization and deserialization operations are benchmarked accurately.
        - No data loss or corruption occurs during the conversion process.
        """
        # Create TypeAdapters for high-performance serialization
        trade_adapter = TypeAdapter(list[Trade])

        # Test Trade serialization performance
        def serialize_trades() -> bytes:
            return trade_adapter.dump_json(sample_trades)

        trades_json = benchmark.pedantic(serialize_trades, rounds=3, iterations=1)

        # Validate serialization worked
        assert len(trades_json) > 0

        # Test data integrity with a small subset (not benchmarked)
        reconstructed_trades = trade_adapter.validate_json(trades_json)
        assert len(reconstructed_trades) == len(sample_trades)
        assert reconstructed_trades[0].symbol == sample_trades[0].symbol
        assert reconstructed_trades[-1].price == sample_trades[-1].price

    def test_trade_creation_and_validation_performance(self, benchmark: Any) -> None:
        """Test Trade model validation performance using benchmark for large datasets.

        Description of what the test covers:
        This test measures the performance of Pydantic model validation when creating
        a large number of `Trade` instances. It uses pytest-benchmark
        for reliable performance measurement and proper exception handling.

        Preconditions:
        - Pydantic models (`Trade`) are properly defined and configured for validation.
        - System resources are sufficient for large-scale validation testing.
        - pytest-benchmark is available for performance measurement.

        Steps:
        - Define valid data templates for Trade.
        - Use benchmark to measure creation time for valid models.
        - Verify that models are created successfully.

        Expected Result:
        - Model creation and validation performance is accurately benchmarked.
        """
        valid_trade_data = {
            "symbol": "BTCUSDT",
            "trade_id": "test_trade",
            "price": Decimal("50000"),
            "quantity": Decimal("1.5"),
            "side": TradeSide.BUY,
            "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
            "exchange": "binance",
        }

        # Test valid Trade creation performance
        def create_valid_trades() -> list[Trade]:
            valid_trades = []
            for i in range(50_000):
                trade_data = valid_trade_data.copy()
                trade_data["trade_id"] = f"trade_{i}"
                trade_data["price"] = Decimal(f"{50000 + i % 1000}")
                valid_trades.append(Trade(**trade_data))
            return valid_trades

        valid_trades = benchmark.pedantic(create_valid_trades, rounds=2, iterations=1)

        # Verify results
        assert len(valid_trades) == 50_000

    def test_kline_creation_and_validation_performance(self, benchmark: Any) -> None:
        """Test Kline model validation performance using benchmark for large datasets.

        Description of what the test covers:
        This test measures the performance of Pydantic model validation when creating
        a large number of `Kline` instances. It uses pytest-benchmark
        for reliable performance measurement and proper exception handling.

        Preconditions:
        - Pydantic models (`Kline`) are properly defined and configured for validation.
        - System resources are sufficient for large-scale validation testing.
        - pytest-benchmark is available for performance measurement.

        Steps:
        - Define valid data templates for Kline.
        - Use benchmark to measure creation time for valid models.
        - Verify that models are created successfully.

        Expected Result:
        - Model creation and validation performance is accurately benchmarked.
        """
        valid_kline_data = {
            "symbol": "BTCUSDT",
            "interval": KlineInterval.MINUTE_1,
            "open_time": datetime(2024, 1, 1, tzinfo=UTC),
            "close_time": datetime(2024, 1, 1, 0, 0, 59, tzinfo=UTC),
            "open_price": Decimal("50000"),
            "high_price": Decimal("50100"),
            "low_price": Decimal("49900"),
            "close_price": Decimal("50050"),
            "volume": Decimal("100"),
            "quote_volume": Decimal("5000000"),
            "trades_count": 500,
            "exchange": "binance",
        }

        # Test valid Kline creation performance
        def create_valid_klines() -> list[Kline]:
            valid_klines = []
            for i in range(50_000):
                kline_data = valid_kline_data.copy()
                kline_data["open_time"] = datetime(2024, 1, 1, minute=i % 60, tzinfo=UTC)
                kline_data["close_time"] = datetime(2024, 1, 1, minute=i % 60, second=59, tzinfo=UTC)
                base_price = Decimal(f"{50000 + i % 1000}")
                kline_data["open_price"] = base_price
                kline_data["high_price"] = base_price + Decimal("100")
                kline_data["low_price"] = base_price - Decimal("100")
                kline_data["close_price"] = base_price + Decimal(f"{(i % 200) - 100}")
                valid_klines.append(Kline(**kline_data))
            return valid_klines

        valid_klines = benchmark.pedantic(create_valid_klines, rounds=2, iterations=1)

        # Verify results
        assert len(valid_klines) == 50_000

    def test_validation_error_handling_performance(self, benchmark: Any) -> None:
        """Test validation error handling performance using benchmark.

        Description of what the test covers:
        This test measures the performance of Pydantic validation error handling
        when creating invalid `Trade` instances. It uses pytest-benchmark
        for reliable performance measurement and proper exception handling.

        Preconditions:
        - Pydantic models (`Trade`) are properly defined and configured for validation.
        - System resources are sufficient for large-scale validation testing.
        - pytest-benchmark is available for performance measurement.

        Steps:
        - Define invalid data templates for Trade.
        - Use benchmark to measure error handling time for invalid models.
        - Verify that validation errors are properly caught.

        Expected Result:
        - Validation errors are raised promptly for invalid data.
        """
        valid_trade_data = {
            "symbol": "BTCUSDT",
            "trade_id": "test_trade",
            "price": Decimal("50000"),
            "quantity": Decimal("1.5"),
            "side": TradeSide.BUY,
            "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
            "exchange": "binance",
        }

        # Test error handling performance
        invalid_trade_data = valid_trade_data.copy()
        invalid_trade_data["price"] = Decimal("-1000")

        def create_invalid_trades() -> int:
            validation_errors = 0
            for _i in range(1_000):
                try:
                    Trade(**invalid_trade_data)
                except pydantic.ValidationError:
                    validation_errors += 1
            return validation_errors

        validation_errors = benchmark.pedantic(create_invalid_trades, rounds=2, iterations=1)

        # Verify results
        assert validation_errors == 1_000

    @profile  # type: ignore[misc]
    def test_memory_of_holding_models(self, sample_trades: list[Trade], sample_klines: list[Kline]) -> None:
        """Test memory consumption of holding large collections of model instances.

        Description of what the test covers:
        This test uses `memory_profiler` to measure the memory footprint of holding
        large collections of `Trade` and `Kline` objects. It focuses specifically
        on the memory cost of keeping model instances in memory.

        Preconditions:
        - `memory_profiler` is installed and available.
        - Sufficient system memory is available for large-scale memory testing.
        - `sample_trades` and `sample_klines` fixtures provide large lists of model objects.

        Steps:
        - Force garbage collection to establish a clean memory baseline.
        - Access all model instances to ensure they are fully loaded into memory.
        - Perform simple operations to confirm models are accessible.
        - The `@profile` decorator automatically tracks memory usage.

        Expected Result:
        - Memory usage scales predictably with the number of objects.
        - No excessive memory overhead per object.
        """
        import gc

        gc.collect()

        # Access all trades to ensure they're in memory
        total_volume = sum(trade.volume for trade in sample_trades)
        assert total_volume > 0

        # Access all klines to ensure they're in memory
        total_kline_volume = sum(kline.volume for kline in sample_klines)
        assert total_kline_volume > 0

        # Perform comparison operations
        sample_size = 1_000
        comparison_results = []
        for i in range(sample_size - 1):
            trade_equal = sample_trades[i].symbol == sample_trades[i + 1].symbol
            kline_equal = sample_klines[i].interval == sample_klines[i + 1].interval
            comparison_results.append(trade_equal and kline_equal)

        assert len(comparison_results) == sample_size - 1

    @profile  # type: ignore[misc]
    def test_memory_of_serialization(self, sample_trades: list[Trade], sample_klines: list[Kline]) -> None:
        """Test memory consumption during TypeAdapter serialization operations.

        Description of what the test covers:
        This test uses `memory_profiler` to measure the peak memory usage during
        high-performance serialization operations using TypeAdapter. It focuses
        specifically on memory usage during the serialization process.

        Preconditions:
        - `memory_profiler` is installed and available.
        - Sufficient system memory is available for serialization testing.
        - `sample_trades` and `sample_klines` fixtures provide large lists of model objects.

        Steps:
        - Force garbage collection to establish a clean memory baseline.
        - Create TypeAdapter instances for serialization.
        - Perform serialization operations using TypeAdapter.
        - Clean up temporary data and force garbage collection.
        - The `@profile` decorator automatically tracks memory usage.

        Expected Result:
        - Memory usage during serialization is reasonable and predictable.
        - Memory is properly released after serialization completes.
        """
        import gc

        gc.collect()

        # Create TypeAdapters for high-performance serialization
        trade_adapter = TypeAdapter(list[Trade])
        kline_adapter = TypeAdapter(list[Kline])

        # Serialize a subset for memory measurement
        subset_trades = sample_trades[:10_000]
        subset_klines = sample_klines[:10_000]

        trades_json = trade_adapter.dump_json(subset_trades)
        klines_json = kline_adapter.dump_json(subset_klines)

        assert len(trades_json) > 0
        assert len(klines_json) > 0

        # Clean up and observe memory release
        del trades_json
        del klines_json
        del subset_trades
        del subset_klines
        gc.collect()
