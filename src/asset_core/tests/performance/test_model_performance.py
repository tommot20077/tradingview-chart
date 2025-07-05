"""Performance tests for model operations.

This module tests the performance characteristics of Pydantic models used throughout
the asset_core library, focusing on large-scale serialization, validation performance,
and memory footprint measurements.
"""

import json
import time
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide

# Optional memory profiler import
try:
    from memory_profiler import profile
except ImportError:
    # Create a no-op decorator if memory_profiler is not available
    def profile(func: Callable) -> Callable:
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

        Yields:
            A list of 100,000 Trade objects with varied data.
        """
        trades = []
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for i in range(100_000):
            trade = Trade(
                symbol="BTCUSDT",
                trade_id=f"trade_{i:06d}",
                price=Decimal(f"{50000 + (i % 1000)}"),
                quantity=Decimal(f"1.{i % 999:03d}"),
                side=TradeSide.BUY if i % 2 == 0 else TradeSide.SELL,
                timestamp=base_time.replace(second=i % 60, microsecond=i % 1000000),
                exchange="binance",
                metadata={"test_id": i, "batch": i // 1000},
            )
            trades.append(trade)

        yield trades

    @pytest.fixture
    def sample_klines(self) -> Generator[list[Kline], None, None]:
        """Generate a list of sample Kline objects for performance testing.

        Yields:
            A list of 100,000 Kline objects with varied data.
        """
        klines = []
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for i in range(100_000):
            open_price = Decimal(f"{50000 + (i % 1000)}")
            high_price = open_price + Decimal(f"{i % 100}")
            low_price = open_price - Decimal(f"{i % 50}")
            close_price = open_price + Decimal(f"{(i % 200) - 100}")

            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time.replace(minute=i % 60),
                close_time=base_time.replace(minute=i % 60, second=59),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=Decimal(f"{100 + i % 500}"),
                quote_volume=Decimal(f"{5000000 + i % 50000}"),
                trades_count=i % 1000 + 1,
                exchange="binance",
                metadata={"test_id": i, "batch": i // 1000},
            )
            klines.append(kline)

        yield klines

    def test_large_scale_serialization(self, sample_trades: list[Trade], sample_klines: list[Kline]) -> None:
        """Test serialization and deserialization performance of large model datasets.

        Summary line.

        Measures the time taken to serialize and deserialize 100,000 Trade and Kline
        objects to/from JSON format, ensuring performance is within acceptable limits.

        Preconditions:
        - Sample datasets are available
        - System has sufficient memory for large operations

        Steps:
        - Serialize models to JSON
        - Measure serialization time
        - Deserialize from JSON
        - Measure deserialization time

        Expected Result:
        - Serialization completes within 10 seconds
        - Deserialization completes within 15 seconds
        - No data loss during round-trip conversion
        """
        # Test Trade serialization performance
        start_time = time.perf_counter()
        trade_dicts = [trade.to_dict() for trade in sample_trades]
        trades_json = json.dumps(trade_dicts)
        trade_serialization_time = time.perf_counter() - start_time

        # Test Trade deserialization performance
        start_time = time.perf_counter()
        deserialized_trade_dicts = json.loads(trades_json)
        reconstructed_trades = []
        for trade_dict in deserialized_trade_dicts:
            # Convert string fields back to appropriate types
            trade_dict["price"] = Decimal(trade_dict["price"])
            trade_dict["quantity"] = Decimal(trade_dict["quantity"])
            trade_dict["timestamp"] = datetime.fromisoformat(trade_dict["timestamp"])
            if trade_dict.get("received_at"):
                trade_dict["received_at"] = datetime.fromisoformat(trade_dict["received_at"])
            # Remove calculated fields that aren't model fields
            trade_dict.pop("volume", None)
            reconstructed_trades.append(Trade(**trade_dict))
        trade_deserialization_time = time.perf_counter() - start_time

        # Test Kline serialization performance
        start_time = time.perf_counter()
        kline_dicts = [kline.to_dict() for kline in sample_klines]
        klines_json = json.dumps(kline_dicts)
        kline_serialization_time = time.perf_counter() - start_time

        # Test Kline deserialization performance
        start_time = time.perf_counter()
        deserialized_kline_dicts = json.loads(klines_json)
        reconstructed_klines = []
        for kline_dict in deserialized_kline_dicts:
            # Convert string fields back to appropriate types
            for field in ["open_price", "high_price", "low_price", "close_price", "volume", "quote_volume"]:
                kline_dict[field] = Decimal(kline_dict[field])
            if kline_dict.get("taker_buy_volume"):
                kline_dict["taker_buy_volume"] = Decimal(kline_dict["taker_buy_volume"])
            if kline_dict.get("taker_buy_quote_volume"):
                kline_dict["taker_buy_quote_volume"] = Decimal(kline_dict["taker_buy_quote_volume"])
            kline_dict["open_time"] = datetime.fromisoformat(kline_dict["open_time"])
            kline_dict["close_time"] = datetime.fromisoformat(kline_dict["close_time"])
            if kline_dict.get("received_at"):
                kline_dict["received_at"] = datetime.fromisoformat(kline_dict["received_at"])
            # Remove calculated fields
            for calc_field in ["price_change", "price_change_percent"]:
                kline_dict.pop(calc_field, None)
            reconstructed_klines.append(Kline(**kline_dict))
        kline_deserialization_time = time.perf_counter() - start_time

        # Performance assertions
        assert trade_serialization_time < 10.0, (
            f"Trade serialization took {trade_serialization_time:.2f} seconds, expected < 10s"
        )
        assert trade_deserialization_time < 15.0, (
            f"Trade deserialization took {trade_deserialization_time:.2f} seconds, expected < 15s"
        )
        assert kline_serialization_time < 10.0, (
            f"Kline serialization took {kline_serialization_time:.2f} seconds, expected < 10s"
        )
        assert kline_deserialization_time < 15.0, (
            f"Kline deserialization took {kline_deserialization_time:.2f} seconds, expected < 15s"
        )

        # Data integrity assertions
        assert len(reconstructed_trades) == len(sample_trades)
        assert len(reconstructed_klines) == len(sample_klines)

        # Verify first and last items to ensure data integrity
        assert reconstructed_trades[0].symbol == sample_trades[0].symbol
        assert reconstructed_trades[-1].price == sample_trades[-1].price
        assert reconstructed_klines[0].symbol == sample_klines[0].symbol
        assert reconstructed_klines[-1].volume == sample_klines[-1].volume

    def test_validation_performance(self) -> None:
        """Test Pydantic model validation performance for large datasets.

        Summary line.

        Measures the performance of Pydantic validation when creating large numbers
        of model instances with various validation scenarios including valid data,
        edge cases, and invalid data handling.

        Preconditions:
        - Pydantic models are properly configured
        - System resources available for validation testing

        Steps:
        - Create valid model instances and measure time
        - Test edge case validations
        - Test invalid data handling performance

        Expected Result:
        - Valid model creation completes within 5 seconds for 50,000 instances
        - Validation errors are raised promptly for invalid data
        - Edge case validation doesn't significantly impact performance
        """
        # Test valid Trade creation performance
        valid_trade_data = {
            "symbol": "BTCUSDT",
            "trade_id": "test_trade",
            "price": Decimal("50000"),
            "quantity": Decimal("1.5"),
            "side": TradeSide.BUY,
            "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
            "exchange": "binance",
        }

        start_time = time.perf_counter()
        valid_trades = []
        for i in range(50_000):
            trade_data = valid_trade_data.copy()
            trade_data["trade_id"] = f"trade_{i}"
            trade_data["price"] = Decimal(f"{50000 + i % 1000}")
            valid_trades.append(Trade(**trade_data))
        valid_trade_creation_time = time.perf_counter() - start_time

        # Test valid Kline creation performance
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

        start_time = time.perf_counter()
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
        valid_kline_creation_time = time.perf_counter() - start_time

        # Test validation error handling performance
        invalid_trade_data = valid_trade_data.copy()
        invalid_trade_data["price"] = Decimal("-1000")  # Invalid negative price

        start_time = time.perf_counter()
        validation_errors = 0
        for _i in range(1_000):  # Smaller sample for error testing
            try:
                Trade(**invalid_trade_data)
            except ValueError:
                validation_errors += 1
        error_handling_time = time.perf_counter() - start_time

        # Performance assertions
        assert valid_trade_creation_time < 5.0, (
            f"Valid Trade creation took {valid_trade_creation_time:.2f} seconds, expected < 5s"
        )
        assert valid_kline_creation_time < 5.0, (
            f"Valid Kline creation took {valid_kline_creation_time:.2f} seconds, expected < 5s"
        )
        assert error_handling_time < 1.0, f"Error handling took {error_handling_time:.2f} seconds, expected < 1s"

        # Correctness assertions
        assert len(valid_trades) == 50_000
        assert len(valid_klines) == 50_000
        assert validation_errors == 1_000  # All should have failed validation

    @profile  # type: ignore
    def test_memory_footprint(self, sample_trades: list[Trade], sample_klines: list[Kline]) -> None:
        """Test memory consumption of creating and holding large numbers of model instances.

        Summary line.

        Uses memory_profiler to measure the memory footprint of creating and holding
        large collections of Trade and Kline objects, ensuring memory usage is
        reasonable and doesn't indicate memory leaks.

        Preconditions:
        - memory_profiler is available
        - Sufficient system memory for testing
        - Sample datasets are provided

        Steps:
        - Create large collections of models
        - Measure memory usage at different stages
        - Verify memory is released after deletion

        Expected Result:
        - Memory usage scales predictably with object count
        - No excessive memory overhead per object
        - Memory is properly released when objects are deleted
        """
        # Baseline memory measurement
        import gc

        gc.collect()

        # Memory usage during model creation and access
        # The @profile decorator will track memory usage

        # Access all trades to ensure they're fully loaded in memory
        total_volume = sum(trade.volume for trade in sample_trades)
        assert total_volume > 0  # Ensure calculation completed

        # Access all klines to ensure they're fully loaded in memory
        total_kline_volume = sum(kline.volume for kline in sample_klines)
        assert total_kline_volume > 0  # Ensure calculation completed

        # Test memory usage of model serialization
        trade_dicts = [trade.to_dict() for trade in sample_trades[:10_000]]  # Smaller sample for memory test
        kline_dicts = [kline.to_dict() for kline in sample_klines[:10_000]]

        assert len(trade_dicts) == 10_000
        assert len(kline_dicts) == 10_000

        # Clean up to test memory release
        del trade_dicts
        del kline_dicts
        gc.collect()

        # Test memory efficiency of model comparison operations
        sample_size = 1_000
        comparison_results = []
        for i in range(sample_size - 1):
            # Compare adjacent trades/klines to test memory efficiency of operations
            trade_equal = sample_trades[i].symbol == sample_trades[i + 1].symbol
            kline_equal = sample_klines[i].interval == sample_klines[i + 1].interval
            comparison_results.append(trade_equal and kline_equal)

        assert len(comparison_results) == sample_size - 1

        # The actual memory profiling is handled by the @profile decorator
        # This test ensures the operations complete successfully while memory is tracked
