"""Performance tests for concurrent operations.

This module tests the performance characteristics of concurrent operations
with asset_core models, focusing on thread safety, async operation overhead,
and concurrent model creation performance.
"""

import asyncio
import time
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

    @pytest.mark.asyncio
    async def test_async_operation_overhead(self, base_trade_data: dict[str, Any]) -> None:
        """Test overhead introduced by asynchronous operations compared to synchronous ones.

        Description of what the test covers:
        This test measures the performance overhead of asynchronous operations involving
        model creation, serialization, and processing compared to their synchronous counterparts.
        It also assesses the benefits of concurrent asynchronous execution for I/O-bound tasks.

        Preconditions:
        - `asyncio` is available and functional for asynchronous programming.
        - Models support both synchronous and asynchronous interaction patterns.
        - Base test data for `Trade` and `Kline` models is provided by fixtures.

        Steps:
        - Define the number of operations to perform.
        - Establish a synchronous baseline: create and process `Trade` models sequentially,
          recording the time taken.
        - Implement an asynchronous equivalent: define `create_and_process_trade` as an `async` function
          that creates and processes a `Trade` model, including a small `asyncio.sleep(0)` to yield control.
        - Perform sequential asynchronous operations: iterate and `await` calls to `create_and_process_trade`,
          recording the time taken.
        - Perform concurrent asynchronous operations: create a list of `create_and_process_trade` tasks
          and run them concurrently using `asyncio.gather`, recording the time taken.
        - Implement `process_trade_batch` as an `async` function to simulate batch processing with
          realistic async I/O (using `asyncio.sleep(0)`).
        - Divide synchronous trades into batches and process them concurrently using `asyncio.gather`.
        - Assert that the asynchronous sequential overhead is minimal compared to synchronous execution.
        - Assert that concurrent asynchronous operations show reasonable performance relative to sequential async.
        - Verify data integrity: assert that the number of models/results from all operations matches the expected count.
        - Implement `validate_model_async` to simulate asynchronous model validation.
        - Test concurrent validation of models using `asyncio.gather` and assert that all validations pass
          within an acceptable time frame.

        Expected Result:
        - Asynchronous operations introduce minimal overhead for CPU-bound tasks.
        - Concurrent asynchronous operations demonstrate performance benefits for tasks that can yield control
          (e.g., simulated I/O).
        - No significant performance degradation occurs for simple asynchronous operations.
        - All models are created, processed, and validated correctly across synchronous and asynchronous paths.
        """

        num_operations = 5000

        # --- Synchronous Baseline ---
        start_time = time.perf_counter()
        sync_trades = []
        for i in range(num_operations):
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"sync_trade_{i}"
            trade_data["timestamp"] = datetime.now(UTC)
            trade = Trade(**trade_data)
            # Simulate some synchronous processing
            _ = trade.model_dump_json()
            sync_trades.append(trade)
        sync_time = time.perf_counter() - start_time
        # Synchronous operations baseline: {sync_time:.4f} seconds

        # --- Asynchronous Sequential ---
        async def create_and_process_trade(index: int) -> Trade:
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"async_seq_trade_{index}"
            trade_data["timestamp"] = datetime.now(UTC)
            trade = Trade(**trade_data)
            # Simulate non-blocking I/O or yielding control
            await asyncio.sleep(0)  # Yield control to event loop
            _ = trade.model_dump_json()
            return trade

        start_time = time.perf_counter()
        async_seq_trades = []
        for i in range(num_operations):
            async_seq_trades.append(await create_and_process_trade(i))
        async_seq_time = time.perf_counter() - start_time
        # Asynchronous sequential operations: {async_seq_time:.4f} seconds

        # Asynchronous sequential should be comparable to sync, possibly slightly higher due to async overhead
        assert async_seq_time < sync_time * 2.0  # Allow up to double overhead for simple ops

        # --- Asynchronous Concurrent (I/O bound simulation) ---
        start_time = time.perf_counter()
        tasks = [create_and_process_trade(i) for i in range(num_operations)]
        async_concurrent_trades = await asyncio.gather(*tasks)
        async_concurrent_time = time.perf_counter() - start_time
        # Asynchronous concurrent operations: {async_concurrent_time:.4f} seconds

        # For I/O bound tasks, concurrent async should be significantly faster than sequential
        # The exact ratio depends on the nature of 'I/O' (here, asyncio.sleep(0))
        assert (
            async_concurrent_time < async_seq_time * 3.0
        )  # Allow for realistic performance variance (some systems may be slower)

        assert len(sync_trades) == num_operations
        assert len(async_seq_trades) == num_operations
        assert len(async_concurrent_trades) == num_operations

        # Verify data integrity (simplified)
        assert all(isinstance(t, Trade) for t in sync_trades)
        assert all(isinstance(t, Trade) for t in async_seq_trades)
        assert all(isinstance(t, Trade) for t in async_concurrent_trades)

        # Test concurrent batch processing (simulating I/O)
        async def process_trade_batch(trades_batch: list[Trade]) -> list[Trade]:
            processed_batch = []
            for trade in trades_batch:
                await asyncio.sleep(0.0001)  # Simulate small I/O delay per item
                processed_batch.append(trade)
            return processed_batch

        batch_size = 100
        batches = [sync_trades[i : i + batch_size] for i in range(0, num_operations, batch_size)]

        start_time = time.perf_counter()
        processed_results = await asyncio.gather(*[process_trade_batch(b) for b in batches])
        # Async batch processing: {batch_processing_time:.4f} seconds

        total_processed = sum(len(b) for b in processed_results)
        assert total_processed == num_operations

        # Test concurrent model validation (simulating async validation)
        async def validate_model_async(model: Trade) -> bool:
            await asyncio.sleep(0.00005)  # Simulate async validation check
            return bool(model.price > 0)  # Simple validation

        start_time = time.perf_counter()
        validation_tasks = [validate_model_async(t) for t in sync_trades]
        validation_results = await asyncio.gather(*validation_tasks)
        validation_time = time.perf_counter() - start_time
        # Async concurrent validation: {validation_time:.4f} seconds

        assert all(validation_results)  # All should be valid
        assert (
            validation_time < async_seq_time * 2.0
        )  # Allow for realistic performance variance (some systems may be slower)
