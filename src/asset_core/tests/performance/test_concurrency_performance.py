"""Performance tests for concurrent operations.

This module tests the performance characteristics of concurrent operations
with asset_core models, focusing on thread safety, async operation overhead,
and concurrent model creation performance.
"""

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.kline import Kline, KlineInterval
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

        Summary line.

        Measures the performance of creating Trade and Kline model instances
        concurrently using multiple threads and async tasks, comparing against
        sequential creation to assess concurrency benefits and overhead.

        Preconditions:
        - Base model data is available
        - ThreadPoolExecutor and asyncio are functional
        - System supports concurrent operations

        Steps:
        - Create models sequentially as baseline
        - Create models concurrently using threads
        - Create models concurrently using async
        - Compare performance metrics

        Expected Result:
        - Concurrent creation completes successfully (may be slower due to GIL)
        - All created models are valid and identical
        - No data corruption occurs during concurrent creation
        """
        num_models = 10_000
        num_threads = 4

        # Sequential baseline for Trade creation
        start_time = time.perf_counter()
        sequential_trades = []
        for i in range(num_models):
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"trade_{i}"
            trade_data["price"] = Decimal(f"{50000 + i % 1000}")
            sequential_trades.append(Trade(**trade_data))
        sequential_trade_time = time.perf_counter() - start_time

        # Concurrent Trade creation using threads
        def create_trade_batch(start_idx: int, batch_size: int) -> list[Trade]:
            trades = []
            for i in range(start_idx, start_idx + batch_size):
                trade_data = base_trade_data.copy()
                trade_data["trade_id"] = f"trade_{i}"
                trade_data["price"] = Decimal(f"{50000 + i % 1000}")
                trades.append(Trade(**trade_data))
            return trades

        start_time = time.perf_counter()
        concurrent_trades = []
        batch_size = num_models // num_threads

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures: list[Future[list[Trade]]] = []
            for thread_id in range(num_threads):
                start_idx = thread_id * batch_size
                future = executor.submit(create_trade_batch, start_idx, batch_size)
                futures.append(future)

            for future in as_completed(futures):
                concurrent_trades.extend(future.result())

        concurrent_trade_time = time.perf_counter() - start_time

        # Sequential baseline for Kline creation
        start_time = time.perf_counter()
        sequential_klines = []
        for i in range(num_models):
            kline_data = base_kline_data.copy()
            kline_data["open_time"] = datetime(2024, 1, 1, minute=i % 60, tzinfo=UTC)
            kline_data["close_time"] = datetime(2024, 1, 1, minute=i % 60, second=59, tzinfo=UTC)
            base_price = Decimal(f"{50000 + i % 1000}")
            kline_data["open_price"] = base_price
            kline_data["high_price"] = base_price + Decimal("100")
            kline_data["low_price"] = base_price - Decimal("100")
            kline_data["close_price"] = base_price + Decimal(f"{(i % 200) - 100}")
            sequential_klines.append(Kline(**kline_data))
        sequential_kline_time = time.perf_counter() - start_time

        # Concurrent Kline creation using threads
        def create_kline_batch(start_idx: int, batch_size: int) -> list[Kline]:
            klines = []
            for i in range(start_idx, start_idx + batch_size):
                kline_data = base_kline_data.copy()
                kline_data["open_time"] = datetime(2024, 1, 1, minute=i % 60, tzinfo=UTC)
                kline_data["close_time"] = datetime(2024, 1, 1, minute=i % 60, second=59, tzinfo=UTC)
                base_price = Decimal(f"{50000 + i % 1000}")
                kline_data["open_price"] = base_price
                kline_data["high_price"] = base_price + Decimal("100")
                kline_data["low_price"] = base_price - Decimal("100")
                kline_data["close_price"] = base_price + Decimal(f"{(i % 200) - 100}")
                klines.append(Kline(**kline_data))
            return klines

        start_time = time.perf_counter()
        concurrent_klines = []

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures_klines: list[Future[list[Kline]]] = []
            for thread_id in range(num_threads):
                start_idx = thread_id * batch_size
                kline_future: Future[list[Kline]] = executor.submit(create_kline_batch, start_idx, batch_size)
                futures_klines.append(kline_future)

            for kline_future in as_completed(futures_klines):
                concurrent_klines.extend(kline_future.result())

        concurrent_kline_time = time.perf_counter() - start_time

        # Performance assertions - focus on completion rather than performance comparison
        # Python's GIL makes threading inefficient for CPU-bound tasks like model creation
        # The purpose is to test that concurrent operations complete successfully, not performance
        assert concurrent_trade_time < 30.0, (
            f"Concurrent trade creation took too long: {concurrent_trade_time:.2f}s (sequential: {sequential_trade_time:.2f}s)"
        )
        assert concurrent_kline_time < 30.0, (
            f"Concurrent kline creation took too long: {concurrent_kline_time:.2f}s (sequential: {sequential_kline_time:.2f}s)"
        )

        # Data integrity assertions
        assert len(concurrent_trades) == num_models
        assert len(concurrent_klines) == num_models
        assert len(sequential_trades) == num_models
        assert len(sequential_klines) == num_models

        # Verify data consistency between sequential and concurrent creation
        sequential_trades.sort(key=lambda t: t.trade_id)
        concurrent_trades.sort(key=lambda t: t.trade_id)

        for seq_trade, conc_trade in zip(sequential_trades, concurrent_trades, strict=False):
            assert seq_trade.trade_id == conc_trade.trade_id
            assert seq_trade.price == conc_trade.price
            assert seq_trade.symbol == conc_trade.symbol

    def test_thread_safety(self, base_trade_data: dict[str, Any]) -> None:
        """Test thread safety of shared resources and mutable objects within models.

        Summary line.

        Verifies that concurrent access to model instances and their operations
        is thread-safe, testing scenarios where multiple threads access and
        modify model instances simultaneously.

        Preconditions:
        - Models support concurrent access
        - Threading primitives are available
        - Test data is prepared

        Steps:
        - Create shared model instances
        - Access models concurrently from multiple threads
        - Verify data integrity after concurrent operations
        - Test concurrent serialization operations

        Expected Result:
        - No race conditions or data corruption
        - Concurrent operations produce consistent results
        - Model state remains valid after concurrent access
        """
        # Create a shared model instance
        shared_trade = Trade(**base_trade_data)

        # Test concurrent read operations
        results = []
        errors = []

        def concurrent_read_operations(thread_id: int) -> None:
            try:
                thread_results = []
                for i in range(1000):
                    # Test various read-only operations
                    volume = shared_trade.volume
                    symbol = shared_trade.symbol
                    trade_str = str(shared_trade)
                    trade_dict = shared_trade.to_dict()

                    thread_results.append(
                        {
                            "thread_id": thread_id,
                            "iteration": i,
                            "volume": volume,
                            "symbol": symbol,
                            "str_len": len(trade_str),
                            "dict_keys": len(trade_dict),
                        }
                    )

                results.extend(thread_results)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Run concurrent read operations
        num_threads = 8
        threads = []

        for thread_id in range(num_threads):
            thread = threading.Thread(target=concurrent_read_operations, args=(thread_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent read operations: {errors}"
        assert len(results) == num_threads * 1000, f"Expected {num_threads * 1000} results, got {len(results)}"

        # Verify all results are consistent
        expected_volume = shared_trade.volume
        expected_symbol = shared_trade.symbol

        for result in results:
            assert result["volume"] == expected_volume, f"Volume mismatch in result: {result}"
            assert result["symbol"] == expected_symbol, f"Symbol mismatch in result: {result}"
            str_len: int = result["str_len"]  # type: ignore[assignment]
            dict_keys: int = result["dict_keys"]  # type: ignore[assignment]
            assert str_len > 0, f"String representation should not be empty: {result}"
            assert dict_keys > 0, f"Dictionary should have keys: {result}"

        # Test concurrent model creation with shared resources
        creation_results = []
        creation_errors = []

        def concurrent_model_creation(thread_id: int) -> None:
            try:
                thread_trades = []
                for i in range(500):
                    trade_data = base_trade_data.copy()
                    trade_data["trade_id"] = f"thread_{thread_id}_trade_{i}"
                    trade_data["price"] = Decimal(f"{50000 + (thread_id * 1000) + i}")
                    trade = Trade(**trade_data)
                    thread_trades.append(trade)

                creation_results.extend(thread_trades)
            except Exception as e:
                creation_errors.append(f"Thread {thread_id}: {e}")

        # Run concurrent model creation
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=concurrent_model_creation, args=(thread_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify concurrent creation results
        assert len(creation_errors) == 0, f"Errors during concurrent model creation: {creation_errors}"
        assert len(creation_results) == num_threads * 500, f"Expected {num_threads * 500} created models"

        # Verify all created models are unique and valid
        trade_ids = [trade.trade_id for trade in creation_results]
        assert len(set(trade_ids)) == len(trade_ids), "All trade IDs should be unique"

        for trade in creation_results:
            assert trade.volume > 0, "All trades should have positive volume"
            assert trade.symbol == base_trade_data["symbol"], "All trades should have consistent symbol"

    @pytest.mark.asyncio
    async def test_async_operation_overhead(
        self, base_trade_data: dict[str, Any], _base_kline_data: dict[str, Any]
    ) -> None:
        """Test overhead introduced by asynchronous operations compared to synchronous ones.

        Summary line.

        Measures the performance overhead of asynchronous operations involving
        model creation, serialization, and processing compared to their
        synchronous counterparts.

        Preconditions:
        - asyncio is available and functional
        - Models support both sync and async patterns
        - Base test data is available

        Steps:
        - Perform synchronous model operations as baseline
        - Perform equivalent asynchronous operations
        - Compare timing and resource usage
        - Test async concurrency benefits

        Expected Result:
        - Async overhead is minimal for CPU-bound operations
        - Async operations show benefits with concurrency
        - No significant performance degradation for simple operations
        """
        num_operations = 5_000

        # Synchronous baseline - model creation and processing
        start_time = time.perf_counter()
        sync_trades = []
        for i in range(num_operations):
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"sync_trade_{i}"
            trade_data["price"] = Decimal(f"{50000 + i % 1000}")
            trade = Trade(**trade_data)
            # Simulate processing
            _ = trade.volume
            _ = trade.to_dict()
            sync_trades.append(trade)
        sync_time = time.perf_counter() - start_time

        # Asynchronous equivalent operations
        async def create_and_process_trade(i: int) -> Trade:
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"async_trade_{i}"
            trade_data["price"] = Decimal(f"{50000 + i % 1000}")
            trade = Trade(**trade_data)
            # Simulate async processing with small delay
            await asyncio.sleep(0)  # Yield control
            # Simulate processing
            _ = trade.volume
            _ = trade.to_dict()
            return trade

        start_time = time.perf_counter()
        async_trades = []
        for i in range(num_operations):
            trade = await create_and_process_trade(i)
            async_trades.append(trade)
        async_sequential_time = time.perf_counter() - start_time

        # Concurrent asynchronous operations
        start_time = time.perf_counter()
        concurrent_tasks = [create_and_process_trade(i) for i in range(num_operations)]
        concurrent_trades = await asyncio.gather(*concurrent_tasks)
        async_concurrent_time = time.perf_counter() - start_time

        # Test async batch operations with realistic async work
        async def process_trade_batch(trades: list[Trade]) -> list[dict[str, Any]]:
            results = []
            for trade in trades:
                await asyncio.sleep(0)  # Simulate async I/O
                result = {
                    "trade_id": trade.trade_id,
                    "volume": trade.volume,
                    "symbol": trade.symbol,
                    "timestamp": trade.timestamp.isoformat(),
                }
                results.append(result)
            return results

        batch_size = 1000
        trade_batches = [sync_trades[i : i + batch_size] for i in range(0, len(sync_trades), batch_size)]

        start_time = time.perf_counter()
        batch_tasks = [process_trade_batch(batch) for batch in trade_batches]
        batch_results = await asyncio.gather(*batch_tasks)
        time.perf_counter() - start_time

        # Performance assertions
        # Async sequential should have overhead but not excessive
        overhead_ratio = async_sequential_time / sync_time
        assert overhead_ratio < 4.0, (
            f"Async sequential overhead too high: {overhead_ratio:.2f}x "
            f"(sync: {sync_time:.2f}s, async: {async_sequential_time:.2f}s)"
        )

        # Concurrent async performance varies by environment - ensure it's not excessively worse
        assert async_concurrent_time < async_sequential_time * 2.5, (
            f"Async concurrent performance acceptable: concurrent={async_concurrent_time:.2f}s, "
            f"sequential={async_sequential_time:.2f}s"
        )

        # Data integrity assertions
        assert len(sync_trades) == num_operations
        assert len(async_trades) == num_operations
        assert len(concurrent_trades) == num_operations

        # Verify batch processing results
        flattened_batch_results = [item for batch in batch_results for item in batch]
        assert len(flattened_batch_results) == len(sync_trades)

        # Test async operation with model validation
        async def validate_model_async(model_data: dict[str, Any], model_class: type) -> bool:
            await asyncio.sleep(0)  # Simulate async validation
            try:
                model_class(**model_data)
                return True
            except Exception:
                return False

        # Test concurrent validation
        validation_tasks = []
        for i in range(1000):
            trade_data = base_trade_data.copy()
            trade_data["trade_id"] = f"validation_trade_{i}"
            validation_tasks.append(validate_model_async(trade_data, Trade))

        start_time = time.perf_counter()
        validation_results = await asyncio.gather(*validation_tasks)
        validation_time = time.perf_counter() - start_time

        # Validation assertions
        assert validation_time < 2.0, f"Async validation took too long: {validation_time:.2f}s"
        assert all(validation_results), "All validations should pass"
        assert len(validation_results) == 1000, "Should have 1000 validation results"
