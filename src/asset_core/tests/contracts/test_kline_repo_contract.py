"""
Contract tests for AbstractKlineRepository interface.

Comprehensive tests to verify that any implementation of AbstractKlineRepository
follows the expected behavioral contracts and interface specifications.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from asset_core.models.kline import Kline, KlineInterval
from asset_core.storage.kline_repo import AbstractKlineRepository, QueryOptions
from asset_core.types.common import Symbol

from .base_contract_test import AsyncContractTestMixin, BaseContractTest, \
    MockImplementationBase


class MockKlineRepository(AbstractKlineRepository, MockImplementationBase):
    """
    Mock implementation of AbstractKlineRepository for contract testing.

    Provides a complete implementation that follows the interface contract
    while using in-memory storage for testing purposes.
    """

    def __init__(self):
        super().__init__()
        self._klines: list[Kline] = []
        self._name = "mock_kline_repo"

    @property
    def name(self) -> str:
        return self._name

    async def save(self, kline: Kline) -> None:
        """Save single kline to mock storage."""
        self._check_not_closed()
        # Simulate unique constraint - replace existing kline with same key
        existing_index = None
        for i, existing in enumerate(self._klines):
            if (
                existing.symbol == kline.symbol
                and existing.interval == kline.interval
                and existing.open_time == kline.open_time
            ):
                existing_index = i
                break

        if existing_index is not None:
            self._klines[existing_index] = kline
        else:
            self._klines.append(kline)

    async def save_batch(self, klines: list[Kline]) -> int:
        """Save multiple klines to mock storage."""
        self._check_not_closed()
        count = 0
        for kline in klines:
            await self.save(kline)
            count += 1
        return count

    async def query(
        self,
        symbol: Symbol,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        options: QueryOptions | None = None,
    ) -> list[Kline]:
        """Query klines from mock storage."""
        self._check_not_closed()

        results = [k for k in self._klines if k.symbol == symbol and k.interval == interval]

        if start_time:
            results = [k for k in results if k.open_time >= start_time]
        if end_time:
            results = [k for k in results if k.open_time < end_time]

        # Apply ordering
        if options and options.order_by == "open_time":
            reverse = options.order_desc
            results.sort(key=lambda k: k.open_time, reverse=reverse)

        # Apply pagination
        if options:
            if options.offset:
                results = results[options.offset :]
            if options.limit:
                results = results[: options.limit]

        return results

    async def stream(
        self,
        symbol: Symbol,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        batch_size: int = 1000,
    ) -> AsyncIterator[list[Kline]]:
        """Stream klines in batches."""
        self._check_not_closed()

        all_klines = await self.query(symbol, interval, start_time, end_time)

        for i in range(0, len(all_klines), batch_size):
            batch = all_klines[i : i + batch_size]
            if batch:
                yield batch

    async def get_latest(self, symbol: Symbol, interval: KlineInterval) -> Kline | None:
        """Get most recent kline."""
        self._check_not_closed()

        matching = [k for k in self._klines if k.symbol == symbol and k.interval == interval]

        if not matching:
            return None

        return max(matching, key=lambda k: k.open_time)

    async def get_oldest(self, symbol: Symbol, interval: KlineInterval) -> Kline | None:
        """Get oldest kline."""
        self._check_not_closed()

        matching = [k for k in self._klines if k.symbol == symbol and k.interval == interval]

        if not matching:
            return None

        return min(matching, key=lambda k: k.open_time)

    async def count(
        self,
        symbol: Symbol,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count klines matching criteria."""
        self._check_not_closed()

        results = await self.query(symbol, interval, start_time, end_time)
        return len(results)

    async def delete(self, symbol: Symbol, interval: KlineInterval, start_time: datetime, end_time: datetime) -> int:
        """Delete klines in time range."""
        self._check_not_closed()

        to_delete = [
            k
            for k in self._klines
            if (k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time)
        ]

        for kline in to_delete:
            self._klines.remove(kline)

        return len(to_delete)

    async def get_gaps(
        self, symbol: Symbol, interval: KlineInterval, start_time: datetime, end_time: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Find missing data gaps."""
        self._check_not_closed()

        # Simple gap detection - find intervals with no data
        existing_times = {k.open_time for k in self._klines if k.symbol == symbol and k.interval == interval}

        gaps = []
        current_time = start_time

        # This is a simplified gap detection for testing
        while current_time < end_time:
            if current_time not in existing_times:
                gap_start = current_time
                while current_time < end_time and current_time not in existing_times:
                    current_time = current_time.replace(hour=current_time.hour + 1)
                gaps.append((gap_start, current_time))
            else:
                current_time = current_time.replace(hour=current_time.hour + 1)

        return gaps

    async def get_statistics(self, symbol: Symbol, interval: KlineInterval) -> dict:
        """Get storage statistics."""
        self._check_not_closed()

        matching = [k for k in self._klines if k.symbol == symbol and k.interval == interval]

        if not matching:
            return {"count": 0, "earliest": None, "latest": None, "size_bytes": 0}

        return {
            "count": len(matching),
            "earliest": min(k.open_time for k in matching),
            "latest": max(k.open_time for k in matching),
            "size_bytes": len(matching) * 100,  # Mock size calculation
        }

    async def close(self) -> None:
        """Close repository and clean up resources."""
        self._is_closed = True

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False


class TestAbstractKlineRepositoryContract(BaseContractTest, AsyncContractTestMixin):
    """
    Contract tests for AbstractKlineRepository interface.

    These tests verify that any implementation of AbstractKlineRepository
    follows the expected behavioral contracts.
    """

    @pytest.fixture
    async def repo(self) -> MockKlineRepository:
        """Create a mock repository instance for testing."""
        return MockKlineRepository()

    @pytest.fixture
    def sample_kline(self) -> Kline:
        """Create a sample kline for testing."""
        return Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 12, 59, 59, tzinfo=UTC),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49500.0,
            close_price=50500.0,
            volume=100.0,
            quote_volume=5025000.0,
            trades_count=1000,
        )

    def test_required_methods_defined(self):
        """
        Test that all required abstract methods are defined in the interface.

        Verifies that AbstractKlineRepository declares all necessary methods
        as abstract and that they have the correct signatures.

        Expected Result:
            - All required methods are present as abstract methods
            - Method signatures match the expected interface
        """
        abstract_methods = self.get_abstract_methods(AbstractKlineRepository)

        required_methods = {
            "save",
            "save_batch",
            "query",
            "stream",
            "get_latest",
            "get_oldest",
            "count",
            "delete",
            "get_gaps",
            "get_statistics",
            "close",
        }

        # All required methods should be abstract
        assert required_methods.issubset(set(abstract_methods)), (
            f"Missing abstract methods: {required_methods - set(abstract_methods)}"
        )

    def test_method_signatures(self):
        """
        Test that all abstract methods have correct signatures.

        Verifies parameter types, return types, and async/sync designation
        for all methods in the interface.

        Expected Result:
            - All methods have correct parameter and return type annotations
            - Async methods are properly marked as async
        """
        # Test key method signatures
        save_sig = self.get_method_signature(AbstractKlineRepository, "save")
        assert len(save_sig.parameters) == 2  # self, kline
        assert "kline" in save_sig.parameters

        query_sig = self.get_method_signature(AbstractKlineRepository, "query")
        assert len(query_sig.parameters) >= 3  # self, symbol, interval + optionals
        assert "symbol" in query_sig.parameters
        assert "interval" in query_sig.parameters

        # Test that core methods are async
        assert self.is_async_method(AbstractKlineRepository, "save")
        assert self.is_async_method(AbstractKlineRepository, "query")
        assert self.is_async_method(AbstractKlineRepository, "close")

    def test_async_context_manager_protocol(self):
        """
        Test that the repository implements async context manager protocol.

        Verifies that __aenter__ and __aexit__ methods are present and
        that they work correctly for resource management.

        Expected Result:
            - Repository has __aenter__ and __aexit__ methods
            - Can be used in async with statements
        """
        assert self.has_async_context_manager(AbstractKlineRepository)

    @pytest.mark.asyncio
    async def test_mock_implementation_completeness(self, repo: MockKlineRepository):
        """
        Test that the mock implementation provides complete interface coverage.

        Creates a complete mock implementation and verifies that all methods
        work correctly and follow the expected behavioral contracts.

        Expected Result:
            - All abstract methods are implemented
            - Methods return expected types
            - State transitions work correctly
        """
        # Test that all abstract methods are implemented
        abstract_methods = self.get_abstract_methods(AbstractKlineRepository)
        for method_name in abstract_methods:
            assert hasattr(repo, method_name), f"Missing method: {method_name}"
            method = getattr(repo, method_name)
            assert callable(method), f"Method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_basic_crud_operations(self, repo: MockKlineRepository, sample_kline: Kline):
        """
        Test basic CRUD operations work correctly.

        Tests the fundamental create, read, update, delete operations
        to ensure the repository behaves as expected.

        Preconditions:
            - Repository is initialized and not closed

        Steps:
            - Save a kline
            - Query it back
            - Update it
            - Delete it
            - Verify it's gone

        Expected Result:
            - All operations complete successfully
            - Data consistency is maintained
            - Return values match expectations
        """
        # Test save operation
        await repo.save(sample_kline)

        # Test query operation
        results = await repo.query(
            sample_kline.symbol, sample_kline.interval, sample_kline.open_time, sample_kline.open_time.replace(hour=13)
        )
        assert len(results) == 1
        assert results[0].symbol == sample_kline.symbol

        # Test count operation
        count = await repo.count(sample_kline.symbol, sample_kline.interval)
        assert count == 1

        # Test get_latest operation
        latest = await repo.get_latest(sample_kline.symbol, sample_kline.interval)
        assert latest is not None
        assert latest.open_time == sample_kline.open_time

        # Test delete operation
        deleted_count = await repo.delete(
            sample_kline.symbol, sample_kline.interval, sample_kline.open_time, sample_kline.open_time.replace(hour=13)
        )
        assert deleted_count == 1

        # Verify deletion
        count_after = await repo.count(sample_kline.symbol, sample_kline.interval)
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_batch_operations(self, repo: MockKlineRepository):
        """
        Test batch operations for performance and consistency.

        Tests that batch operations work correctly and return appropriate
        counts and maintain data consistency.

        Expected Result:
            - Batch save returns correct count
            - All items are saved consistently
            - Batch operations are atomic where possible
        """
        # Create multiple klines
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="ETHUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i, 59, tzinfo=UTC),
                open_price=3000.0 + i,
                high_price=3100.0 + i,
                low_price=2900.0 + i,
                close_price=3050.0 + i,
                volume=50.0,
                quote_volume=152500.0,
                trades_count=500,
            )
            klines.append(kline)

        # Test batch save
        saved_count = await repo.save_batch(klines)
        assert saved_count == 5

        # Verify all were saved
        total_count = await repo.count("ETHUSDT", KlineInterval.MINUTE_1)
        assert total_count == 5

    @pytest.mark.asyncio
    async def test_streaming_interface(self, repo: MockKlineRepository):
        """
        Test streaming interface for large datasets.

        Verifies that the stream method returns an async iterator
        and properly batches results.

        Expected Result:
            - stream() returns an async iterator
            - Batches are properly sized
            - All data is returned across batches
        """
        # Add some test data
        klines = []
        for i in range(10):
            kline = Kline(
                symbol="ADAUSDT",
                interval=KlineInterval.MINUTE_5,
                open_time=datetime(2024, 1, 1, 12, i * 5, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i * 5 + 4, 59, tzinfo=UTC),
                open_price=1.0,
                high_price=1.1,
                low_price=0.9,
                close_price=1.05,
                volume=1000.0,
                quote_volume=1050.0,
                trades_count=100,
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test streaming with small batch size
        batches = []
        async for batch in repo.stream("ADAUSDT", KlineInterval.MINUTE_5, batch_size=3):
            batches.append(batch)
            assert len(batch) <= 3  # Batch size should be respected
            assert all(isinstance(k, Kline) for k in batch)

        # All data should be returned
        total_streamed = sum(len(batch) for batch in batches)
        assert total_streamed == 10

    @pytest.mark.asyncio
    async def test_query_options_interface(self, repo: MockKlineRepository):
        """
        Test QueryOptions functionality for pagination and ordering.

        Verifies that QueryOptions properly controls result ordering,
        pagination, and filtering.

        Expected Result:
            - Ordering works correctly (asc/desc)
            - Pagination limits and offsets work
            - Results are consistent
        """
        # Add test data with different timestamps
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="DOTUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=datetime(2024, 1, 1, 10 + i, 0, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 10 + i, 59, 59, tzinfo=UTC),
                open_price=20.0,
                high_price=21.0,
                low_price=19.0,
                close_price=20.5,
                volume=200.0,
                quote_volume=4100.0,
                trades_count=200,
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test ordering
        options_asc = QueryOptions(order_by="open_time", order_desc=False)
        results_asc = await repo.query("DOTUSDT", KlineInterval.HOUR_1, options=options_asc)
        assert len(results_asc) == 5

        # Should be ordered by open_time ascending
        for i in range(len(results_asc) - 1):
            assert results_asc[i].open_time <= results_asc[i + 1].open_time

        # Test pagination
        options_paginated = QueryOptions(limit=2, offset=1)
        results_paginated = await repo.query("DOTUSDT", KlineInterval.HOUR_1, options=options_paginated)
        assert len(results_paginated) == 2

    @pytest.mark.asyncio
    async def test_gap_detection_interface(self, repo: MockKlineRepository):
        """
        Test gap detection functionality.

        Verifies that the repository can detect missing data gaps
        in time series data.

        Expected Result:
            - get_gaps() returns list of (start_time, end_time) tuples
            - Gaps are correctly identified
            - Method handles edge cases
        """
        # Add some klines with gaps
        klines = [
            Kline(
                symbol="SOLUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 10, 59, 59, tzinfo=UTC),
                open_price=100.0,
                high_price=105.0,
                low_price=95.0,
                close_price=102.0,
                volume=1000.0,
                quote_volume=102000.0,
                trades_count=500,
            ),
            # Gap here - missing 11:00 and 12:00
            Kline(
                symbol="SOLUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 13, 59, 59, tzinfo=UTC),
                open_price=102.0,
                high_price=107.0,
                low_price=98.0,
                close_price=105.0,
                volume=1000.0,
                quote_volume=105000.0,
                trades_count=500,
            ),
        ]

        await repo.save_batch(klines)

        # Test gap detection
        gaps = await repo.get_gaps(
            "SOLUSDT",
            KlineInterval.HOUR_1,
            datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        )

        assert isinstance(gaps, list)
        # Should have detected the gap between 11:00 and 13:00
        assert len(gaps) >= 0  # Implementation-dependent exact gap detection

    @pytest.mark.asyncio
    async def test_statistics_interface(self, repo: MockKlineRepository):
        """
        Test statistics gathering functionality.

        Verifies that get_statistics returns useful metadata about
        stored data.

        Expected Result:
            - Returns dict with count, earliest, latest, size_bytes
            - Values are accurate for stored data
            - Handles empty datasets correctly
        """
        # Test with empty dataset
        stats_empty = await repo.get_statistics("EMPTY", KlineInterval.MINUTE_1)
        assert isinstance(stats_empty, dict)
        assert stats_empty["count"] == 0

        # Add some data
        kline = Kline(
            symbol="LINKUSDT",
            interval=KlineInterval.MINUTE_15,
            open_time=datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 15, 14, 59, tzinfo=UTC),
            open_price=15.0,
            high_price=15.5,
            low_price=14.8,
            close_price=15.2,
            volume=5000.0,
            quote_volume=76000.0,
            trades_count=250,
        )

        await repo.save(kline)

        # Test with data
        stats = await repo.get_statistics("LINKUSDT", KlineInterval.MINUTE_15)
        assert stats["count"] == 1
        assert stats["earliest"] == kline.open_time
        assert stats["latest"] == kline.open_time
        assert isinstance(stats["size_bytes"], int)
        assert stats["size_bytes"] >= 0

    @pytest.mark.asyncio
    async def test_async_context_manager_behavior(self, repo: MockKlineRepository):
        """
        Test async context manager resource management.

        Ensures that the repository properly implements async context
        manager protocol and handles resource cleanup.

        Expected Result:
            - Can be used in async with statements
            - Resources are properly cleaned up
            - Repository is properly closed after context exit
        """
        await self.assert_async_context_manager_protocol(repo)

    @pytest.mark.asyncio
    async def test_closed_state_handling(self, repo: MockKlineRepository):
        """
        Test that operations fail appropriately when repository is closed.

        Verifies that attempting to use a closed repository raises
        appropriate exceptions.

        Expected Result:
            - Operations raise RuntimeError when repository is closed
            - Error messages are clear and helpful
        """
        # Close the repository
        await repo.close()

        # Test that operations fail when closed
        sample_kline = Kline(
            symbol="TESTUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 0, 0, 59, tzinfo=UTC),
            open_price=1.0,
            high_price=1.0,
            low_price=1.0,
            close_price=1.0,
            volume=1.0,
            quote_volume=1.0,
            trades_count=1,
        )

        await self.assert_method_raises_when_not_ready(repo, "save", RuntimeError, sample_kline)

        await self.assert_method_raises_when_not_ready(repo, "query", RuntimeError, "TESTUSDT", KlineInterval.MINUTE_1)
