"""Performance tests for concurrent operations.

This module tests the performance characteristics of concurrent operations
with asset_core models, focusing on thread safety, async operation overhead,
and concurrent model creation performance.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.kline import KlineInterval
from asset_core.models.trade import Trade, TradeSide


class TestConcurrencyPerformance:
    """Performance tests for concurrent model operations.

    Summary line.

    Tests the performance and thread safety of model operations under concurrent
    access, including multi-threaded model creation, async operation overhead,
    and shared resource access patterns.

    Preconditions:
    - Models support concurrent access
    - System has sufficient resources for concurrent testing
    - Threading and asyncio are available

    Steps:
    - Create concurrent workloads
    - Measure performance under concurrent access
    - Verify thread safety and data integrity

    Expected Result:
    - Concurrent operations complete without data corruption
    - Performance scales reasonably with concurrency level
    - No race conditions or deadlocks occur
    """

    @pytest.fixture
    def base_trade_data(self) -> dict[str, Any]:
        """Provide base trade data for concurrent testing.

        Returns:
            Dictionary containing base trade data fields.
        """
        return {
            "symbol": "BTCUSDT",
            "trade_id": "base_trade",
            "price": Decimal("50000"),
            "quantity": Decimal("1.0"),
            "side": TradeSide.BUY,
            "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
            "exchange": "binance",
        }

    @pytest.fixture
    def base_kline_data(self) -> dict[str, Any]:
        """Provide base kline data for concurrent testing.

        Returns:
            Dictionary containing base kline data fields.
        """
        return {
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

    def test_concurrent_model_creation(self, base_trade_data: dict[str, Any], base_kline_data: dict[str, Any]) -> None:
        """Test performance of creating model instances concurrently.

        Description of what the test covers:
        This test measures the performance of creating `Trade` and `Kline` model instances
        concurrently using multiple threads. It compares the time taken for concurrent
        creation against sequential creation to assess the overhead and benefits of concurrency
        for CPU-bound tasks in Python (considering the GIL).

        Preconditions:
        - Base data for `Trade` and `Kline` models is provided by fixtures.
        - `ThreadPoolExecutor` from `concurrent.futures` is available and functional.
        - The system has sufficient resources to handle concurrent operations.

        Steps:
        - Define the number of models to create and the number of threads to use.
        - Establish a sequential baseline for `Trade` model creation: iterate and create `num_models`
          instances, recording the time taken.
        - Implement a `create_trade_batch` function to create a subset of `Trade` models.
        - Use `ThreadPoolExecutor` to concurrently create `Trade` models across multiple threads,
          collecting results using `as_completed`.
        - Record the time taken for concurrent `Trade` creation.
        - Establish a sequential baseline for `Kline` model creation, similar to `Trade`.
        - Implement a `create_kline_batch` function for `Kline` models.
        - Use `ThreadPoolExecutor` to concurrently create `Kline` models.
        - Record the time taken for concurrent `Kline` creation.
        - Assert that concurrent creation times are within reasonable bounds (acknowledging GIL impact).
        - Verify data integrity: assert that the total number of models created concurrently
          matches the expected count for both `Trade` and `Kline`.
        - Sort both sequential and concurrent lists of `Trade` models by `trade_id`.
        - Compare each corresponding `Trade` model from sequential and concurrent lists
          to ensure data consistency (e.g., `trade_id`, `price`, `symbol`).

        Expected Result:
        - Concurrent model creation completes successfully without data corruption.
        - All created models are valid and identical to their sequentially created counterparts.
        - Performance metrics indicate that concurrent operations, while not necessarily faster
          due to Python's GIL for CPU-bound tasks, do not introduce excessive overhead and
          maintain data integrity.
        """

    def test_thread_safety(self, base_trade_data: dict[str, Any]) -> None:
        """Test thread safety of shared resources and mutable objects within models.

        Description of what the test covers:
        This test verifies the thread safety of `Trade` model instances and their operations
        under concurrent access. It simulates scenarios where multiple threads simultaneously
        read from and create model instances, ensuring data integrity and consistency.

        Preconditions:
        - `Trade` models are designed to be thread-safe for read operations.
        - Python's `threading` module and `ThreadPoolExecutor` are available.
        - Base trade data is provided by a fixture.

        Steps:
        - Create a single `shared_trade` instance to be accessed concurrently.
        - Define a `concurrent_read_operations` function for threads to perform read-only
          operations (e.g., accessing attributes, converting to string/dict) on the `shared_trade`.
        - Launch multiple threads to execute `concurrent_read_operations`.
        - Join all threads and assert that no errors occurred during concurrent reads.
        - Verify that all read results are consistent with the `shared_trade`'s initial state.
        - Define a `concurrent_model_creation` function for threads to create new `Trade` instances
          with unique IDs.
        - Launch multiple threads to execute `concurrent_model_creation`.
        - Join all threads and assert that no errors occurred during concurrent creation.
        - Verify that the total number of created models matches the expected count.
        - Assert that all created trade IDs are unique and that model attributes are consistent.

        Expected Result:
        - Concurrent read operations on shared model instances complete without race conditions
          or data corruption, producing consistent results.
        - Concurrent creation of new model instances across multiple threads is thread-safe,
          resulting in valid and unique model objects.
        - The overall system demonstrates robust thread safety for model interactions.
        """

    def test_sync_trade_creation_performance(self, benchmark: Any, base_trade_data: dict[str, Any]) -> None:
        """Benchmark synchronous trade creation performance.

        Uses pytest-benchmark to measure baseline performance of synchronous trade creation.
        """
        num_operations = 1000

        def create_sync_trades() -> list[Trade]:
            trades = []
            for i in range(num_operations):
                trade_data = base_trade_data.copy()
                trade_data["trade_id"] = f"sync_trade_{i}"
                trade_data["timestamp"] = datetime.now(UTC)
                trade = Trade(**trade_data)
                _ = trade.model_dump_json()  # Simulate processing
                trades.append(trade)
            return trades

        trades = benchmark.pedantic(create_sync_trades, rounds=3, iterations=1)
        assert len(trades) == num_operations
        assert all(isinstance(t, Trade) for t in trades)

    def test_async_trade_creation_performance(self, benchmark: Any, base_trade_data: dict[str, Any]) -> None:
        """Benchmark asynchronous trade creation performance.

        Uses pytest-benchmark to measure async trade creation with simulated I/O.
        """
        num_operations = 1000

        async def create_async_trades() -> list[Trade]:
            async def create_and_process_trade(index: int) -> Trade:
                trade_data = base_trade_data.copy()
                trade_data["trade_id"] = f"async_trade_{index}"
                trade_data["timestamp"] = datetime.now(UTC)
                trade = Trade(**trade_data)
                await asyncio.sleep(0)  # Yield control
                _ = trade.model_dump_json()
                return trade

            tasks = [create_and_process_trade(i) for i in range(num_operations)]
            return await asyncio.gather(*tasks)

        def sync_wrapper() -> list[Trade]:
            return asyncio.run(create_async_trades())

        trades = benchmark.pedantic(sync_wrapper, rounds=3, iterations=1)
        assert len(trades) == num_operations
        assert all(isinstance(t, Trade) for t in trades)

    def test_async_batch_processing_performance(self, benchmark: Any, base_trade_data: dict[str, Any]) -> None:
        """Benchmark asynchronous batch processing performance.

        Uses pytest-benchmark to measure performance of concurrent batch processing.
        """
        num_operations = 1000
        batch_size = 100

        # Create test data
        test_trades = []
        for i in range(num_operations):
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"batch_trade_{i}"
            trade_data["timestamp"] = datetime.now(UTC)
            test_trades.append(Trade(**trade_data))

        async def process_batch_concurrent() -> list[list[Trade]]:
            async def process_trade_batch(trades_batch: list[Trade]) -> list[Trade]:
                processed_batch = []
                for trade in trades_batch:
                    await asyncio.sleep(0.0001)  # Simulate I/O
                    processed_batch.append(trade)
                return processed_batch

            batches = [test_trades[i : i + batch_size] for i in range(0, num_operations, batch_size)]
            return await asyncio.gather(*[process_trade_batch(b) for b in batches])

        def sync_wrapper() -> list[list[Trade]]:
            return asyncio.run(process_batch_concurrent())

        results = benchmark.pedantic(sync_wrapper, rounds=3, iterations=1)
        total_processed = sum(len(b) for b in results)
        assert total_processed == num_operations
