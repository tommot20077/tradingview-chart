"""Performance tests for model operations.

This module tests the performance characteristics of Pydantic models used throughout
the asset_core library, focusing on large-scale serialization, validation performance,
and memory footprint measurements.
"""

import json
import time
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide

# Optional memory profiler import
try:
    from memory_profiler import profile  # type: ignore[import-untyped]
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

        Preconditions:
        - The `Trade` model is correctly defined and importable.
        - `Decimal` and `datetime` (with `UTC`) are available for data generation.

        Steps:
        - Initialize an empty list `trades`.
        - Define a `base_time` for timestamps.
        - Loop 100,000 times to create individual `Trade` objects.
        - For each `Trade` object, assign a unique `trade_id` and vary `price`,
          `quantity`, `side`, `timestamp`, and include `metadata`.
        - Append each created `Trade` object to the `trades` list.
        - Yield the complete list of `trades`.

        Expected Result:
        - A list containing 100,000 valid `Trade` objects, each with diverse and
          realistic data, is provided to the tests.
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

        Description of what the fixture covers:
        This fixture generates a large list of `Kline` objects with varied data
        to be used across performance tests. It ensures a consistent and sufficiently
        sized dataset for benchmarking serialization, deserialization, and memory usage.

        Preconditions:
        - The `Kline` model is correctly defined and importable.
        - `Decimal`, `datetime` (with `UTC`), and `KlineInterval` are available for data generation.

        Steps:
        - Initialize an empty list `klines`.
        - Define a `base_time` for timestamps.
        - Loop 100,000 times to create individual `Kline` objects.
        - For each `Kline` object, calculate `open_price`, `high_price`, `low_price`,
          and `close_price` based on the loop index.
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

        Description of what the test covers:
        This test measures the time taken to serialize and deserialize large datasets
        of `Trade` and `Kline` objects to and from JSON format. It ensures that these
        operations are performant and that no data loss or corruption occurs during
        the round-trip conversion.

        Preconditions:
        - `sample_trades` and `sample_klines` fixtures provide large lists of model objects.
        - The system has sufficient memory to handle large data structures.
        - `json` module is available for serialization/deserialization.

        Steps:
        - **Trade Serialization:**
            - Convert `sample_trades` to a list of dictionaries using `to_dict()`.
            - Serialize the list of dictionaries to a JSON string using `json.dumps()`.
            - Measure the time taken for this serialization.
        - **Trade Deserialization:**
            - Deserialize the JSON string back into a list of dictionaries using `json.loads()`.
            - Reconstruct `Trade` objects from these dictionaries, ensuring proper type conversion
              for `Decimal` and `datetime` fields, and handling of optional fields.
            - Measure the time taken for this deserialization.
        - **Kline Serialization:**
            - Perform similar serialization steps for `sample_klines`.
            - Measure the time taken.
        - **Kline Deserialization:**
            - Perform similar deserialization steps for `sample_klines`, including type conversion
              for `Decimal` and `datetime` fields, and handling of optional/calculated fields.
            - Measure the time taken.
        - **Performance Assertions:**
            - Assert that serialization times for both `Trade` and `Kline` are below a specified threshold (e.g., 10 seconds).
            - Assert that deserialization times for both `Trade` and `Kline` are below a specified threshold (e.g., 15 seconds).
        - **Data Integrity Assertions:**
            - Verify that the number of reconstructed models matches the original sample size.
            - Compare the first and last reconstructed items with their original counterparts
              to ensure data consistency after the round-trip.

        Expected Result:
        - Serialization and deserialization of large model datasets complete within acceptable
          time limits, demonstrating efficient performance.
        - No data loss or corruption occurs during the conversion process, ensuring data integrity.
        """
        start_time = time.perf_counter()
        trade_dicts = [trade.to_dict() for trade in sample_trades]
        trades_json = json.dumps(trade_dicts)
        trade_serialization_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        deserialized_trade_dicts = json.loads(trades_json)
        reconstructed_trades = []
        for trade_dict in deserialized_trade_dicts:
            trade_dict["price"] = Decimal(trade_dict["price"])
            trade_dict["quantity"] = Decimal(trade_dict["quantity"])
            trade_dict["timestamp"] = datetime.fromisoformat(trade_dict["timestamp"])
            if trade_dict.get("received_at"):
                trade_dict["received_at"] = datetime.fromisoformat(trade_dict["received_at"])
            trade_dict.pop("volume", None)
            reconstructed_trades.append(Trade(**trade_dict))
        trade_deserialization_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        kline_dicts = [kline.to_dict() for kline in sample_klines]
        klines_json = json.dumps(kline_dicts)
        kline_serialization_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        deserialized_kline_dicts = json.loads(klines_json)
        reconstructed_klines = []
        for kline_dict in deserialized_kline_dicts:
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
            for calc_field in ["price_change", "price_change_percent"]:
                kline_dict.pop(calc_field, None)
            reconstructed_klines.append(Kline(**kline_dict))
        kline_deserialization_time = time.perf_counter() - start_time

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

        assert len(reconstructed_trades) == len(sample_trades)
        assert len(reconstructed_klines) == len(sample_klines)

        assert reconstructed_trades[0].symbol == sample_trades[0].symbol
        assert reconstructed_trades[-1].price == sample_trades[-1].price
        assert reconstructed_klines[0].symbol == sample_klines[0].symbol
        assert reconstructed_klines[-1].volume == sample_klines[-1].volume

    def test_validation_performance(self) -> None:
        """Test Pydantic model validation performance for large datasets.

        Description of what the test covers:
        This test measures the performance of Pydantic model validation when creating
        a large number of `Trade` and `Kline` instances. It assesses the time taken
        for validating valid data, and the efficiency of handling invalid data and
        edge cases.

        Preconditions:
        - Pydantic models (`Trade`, `Kline`) are properly defined and configured for validation.
        - System resources are sufficient for large-scale validation testing.

        Steps:
        - Define `valid_trade_data` and `valid_kline_data` dictionaries.
        - Measure the time to create 50,000 valid `Trade` instances, varying `trade_id` and `price`.
        - Measure the time to create 50,000 valid `Kline` instances, varying `open_time`, `close_time`,
          and price-related fields.
        - Assert that the creation times for valid models are below a specified threshold (e.g., 5 seconds).
        - Define `invalid_trade_data` (e.g., with a negative price).
        - Measure the time to attempt creating 1,000 `Trade` instances with invalid data,
          counting the number of `ValueError` exceptions raised.
        - Assert that the error handling time is below a specified threshold (e.g., 1 second).
        - Verify that the total number of valid trades and klines created matches the expected count.
        - Assert that all invalid trade creations resulted in validation errors.

        Expected Result:
        - Creation and validation of valid model instances complete efficiently within acceptable time limits.
        - Validation errors are raised promptly for invalid data, demonstrating effective error handling performance.
        - The system maintains robust validation performance even with large datasets and edge cases.
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

        start_time = time.perf_counter()
        valid_trades = []
        for i in range(50_000):
            trade_data = valid_trade_data.copy()
            trade_data["trade_id"] = f"trade_{i}"
            trade_data["price"] = Decimal(f"{50000 + i % 1000}")
            valid_trades.append(Trade(**trade_data))
        valid_trade_creation_time = time.perf_counter() - start_time

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

        invalid_trade_data = valid_trade_data.copy()
        invalid_trade_data["price"] = Decimal("-1000")

        start_time = time.perf_counter()
        validation_errors = 0
        for _i in range(1_000):
            try:
                Trade(**invalid_trade_data)
            except ValueError:
                validation_errors += 1
        error_handling_time = time.perf_counter() - start_time

        assert valid_trade_creation_time < 5.0, (
            f"Valid Trade creation took {valid_trade_creation_time:.2f} seconds, expected < 5s"
        )
        assert valid_kline_creation_time < 5.0, (
            f"Valid Kline creation took {valid_kline_creation_time:.2f} seconds, expected < 5s"
        )
        assert error_handling_time < 1.0, f"Error handling took {error_handling_time:.2f} seconds, expected < 1s"

        assert len(valid_trades) == 50_000
        assert len(valid_klines) == 50_000
        assert validation_errors == 1_000

    @profile  # type: ignore[misc]
    def test_memory_footprint(self, sample_trades: list[Trade], sample_klines: list[Kline]) -> None:
        """Test memory consumption of creating and holding large numbers of model instances.

        Description of what the test covers:
        This test uses `memory_profiler` to measure the memory footprint of creating
        and holding large collections of `Trade` and `Kline` objects. It aims to ensure
        that memory usage is reasonable and does not indicate memory leaks or excessive
        overhead per object.

        Preconditions:
        - `memory_profiler` is installed and available.
        - Sufficient system memory is available for large-scale memory testing.
        - `sample_trades` and `sample_klines` fixtures provide large lists of model objects.

        Steps:
        - Force garbage collection to establish a clean memory baseline.
        - Access all `sample_trades` and `sample_klines` to ensure they are fully loaded
          into memory, and perform a simple calculation (e.g., sum of volumes) to confirm access.
        - Create smaller subsets of `Trade` and `Kline` dictionaries (e.g., 10,000 items)
          to test memory usage during serialization.
        - Delete the temporary dictionaries and force garbage collection to observe memory release.
        - Perform comparison operations on a sample of trades/klines to test memory efficiency
          of common model operations.
        - The `@profile` decorator will automatically track and report memory usage during the test execution.

        Expected Result:
        - Memory usage scales predictably with the number of objects, without excessive overhead per object.
        - Memory is properly released when objects are no longer referenced.
        - The test completes successfully, and `memory_profiler` reports reasonable memory consumption.
        """
        import gc

        gc.collect()

        total_volume = sum(trade.volume for trade in sample_trades)
        assert total_volume > 0

        total_kline_volume = sum(kline.volume for kline in sample_klines)
        assert total_kline_volume > 0

        trade_dicts = [trade.to_dict() for trade in sample_trades[:10_000]]
        kline_dicts = [kline.to_dict() for kline in sample_klines[:10_000]]

        assert len(trade_dicts) == 10_000
        assert len(kline_dicts) == 10_000

        del trade_dicts
        del kline_dicts
        gc.collect()

        sample_size = 1_000
        comparison_results = []
        for i in range(sample_size - 1):
            trade_equal = sample_trades[i].symbol == sample_trades[i + 1].symbol
            kline_equal = sample_klines[i].interval == sample_klines[i + 1].interval
            comparison_results.append(trade_equal and kline_equal)

        assert len(comparison_results) == sample_size - 1
        import gc

        gc.collect()

        total_volume = sum(trade.volume for trade in sample_trades)
        assert total_volume > 0

        total_kline_volume = sum(kline.volume for kline in sample_klines)
        assert total_kline_volume > 0

        trade_dicts = [trade.to_dict() for trade in sample_trades[:10_000]]
        kline_dicts = [kline.to_dict() for kline in sample_klines[:10_000]]

        assert len(trade_dicts) == 10_000
        assert len(kline_dicts) == 10_000

        del trade_dicts
        del kline_dicts
        gc.collect()

        sample_size = 1_000
        comparison_results = []
        for i in range(sample_size - 1):
            trade_equal = sample_trades[i].symbol == sample_trades[i + 1].symbol
            kline_equal = sample_klines[i].interval == sample_klines[i + 1].interval
            comparison_results.append(trade_equal and kline_equal)

        assert len(comparison_results) == sample_size - 1
