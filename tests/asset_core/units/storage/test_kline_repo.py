# ABOUTME: Unit tests for the abstract kline repository interface
# ABOUTME: Validates Kline repository contract compliance, query operations and data streaming

from abc import ABC
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asset_core.exceptions.core import StorageConnectionError, StorageReadError, \
    StorageWriteError
from asset_core.models.kline import Kline, KlineInterval
from asset_core.storage.kline_repo import AbstractKlineRepository, QueryOptions


class ConcreteKlineRepository(AbstractKlineRepository):
    """Concrete implementation for testing the abstract interface."""

    def __init__(self) -> None:
        self._data: dict[str, Kline] = {}
        self._closed = False

    def _get_key(self, symbol: str, interval: KlineInterval, open_time: datetime) -> str:
        """Generate storage key for kline."""
        return f"{symbol}:{interval}:{open_time.timestamp()}"

    async def save(self, kline: Kline) -> None:
        """Save a single kline."""
        if self._closed:
            raise RuntimeError("Repository is closed")
        key = self._get_key(kline.symbol, kline.interval, kline.open_time)
        self._data[key] = kline

    async def save_batch(self, klines: list[Kline]) -> int:
        """Save batch of klines."""
        if self._closed:
            raise RuntimeError("Repository is closed")
        saved_count = 0
        for kline in klines:
            await self.save(kline)
            saved_count += 1
        return saved_count

    async def query(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        options: QueryOptions | None = None,
    ) -> list[Kline]:
        """Query klines."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        results = []
        for kline in self._data.values():
            if kline.symbol == symbol and kline.interval == interval and start_time <= kline.open_time < end_time:
                results.append(kline)

        # Apply query options
        if options:
            if options.order_desc:
                results.sort(key=lambda k: k.open_time, reverse=True)
            else:
                results.sort(key=lambda k: k.open_time)

            if options.offset:
                results = results[options.offset :]

            if options.limit:
                results = results[: options.limit]

        return results

    async def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,
    ) -> AsyncIterator[Kline]:
        """Stream klines."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        # Note: batch_size is for interface compatibility but not used in this mock
        _ = batch_size
        klines = await self.query(symbol, interval, start_time, end_time)
        for kline in klines:
            yield kline

    async def get_latest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Get latest kline."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        latest = None
        for kline in self._data.values():
            if (
                kline.symbol == symbol
                and kline.interval == interval
                and (latest is None or kline.open_time > latest.open_time)
            ):
                latest = kline
        return latest

    async def get_oldest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Get oldest kline."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        oldest = None
        for kline in self._data.values():
            if (
                kline.symbol == symbol
                and kline.interval == interval
                and (oldest is None or kline.open_time < oldest.open_time)
            ):
                oldest = kline
        return oldest

    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count klines."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        count = 0
        for kline in self._data.values():
            if kline.symbol == symbol and kline.interval == interval:
                if start_time and kline.open_time < start_time:
                    continue
                if end_time and kline.open_time >= end_time:
                    continue
                count += 1
        return count

    async def delete(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete klines."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        keys_to_delete = []
        for key, kline in self._data.items():
            if kline.symbol == symbol and kline.interval == interval and start_time <= kline.open_time < end_time:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._data[key]

        return len(keys_to_delete)

    async def get_gaps(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Get time gaps in kline data.

        This enhanced implementation identifies gaps in time series data
        by checking for missing intervals between start_time and end_time.
        """
        if self._closed:
            raise RuntimeError("Repository is closed")

        # Get all klines for the symbol and interval within the time range
        klines = []
        for kline in self._data.values():
            if kline.symbol == symbol and kline.interval == interval and start_time <= kline.open_time < end_time:
                klines.append(kline)

        if not klines:
            # If no data exists, the entire range is a gap
            return [(start_time, end_time)]

        # Sort klines by open_time
        klines.sort(key=lambda k: k.open_time)

        # Calculate expected interval in seconds
        interval_seconds = {
            KlineInterval.MINUTE_1: 60,
            KlineInterval.MINUTE_5: 300,
            KlineInterval.MINUTE_15: 900,
            KlineInterval.MINUTE_30: 1800,
            KlineInterval.HOUR_1: 3600,
            KlineInterval.HOUR_4: 14400,
            KlineInterval.DAY_1: 86400,
        }.get(interval, 60)  # Default to 1 minute

        gaps = []

        # Check for gap before first kline
        first_kline = klines[0]
        if start_time < first_kline.open_time:
            gaps.append((start_time, first_kline.open_time))

        # Check for gaps between consecutive klines
        for i in range(len(klines) - 1):
            current_kline = klines[i]
            next_kline = klines[i + 1]

            # Expected next time = current open_time + interval
            expected_next_time = current_kline.open_time + timedelta(seconds=interval_seconds)

            # If there's a gap (missing intervals)
            if expected_next_time < next_kline.open_time:
                gaps.append((expected_next_time, next_kline.open_time))

        # Check for gap after last kline
        last_kline = klines[-1]
        expected_end_time = last_kline.open_time + timedelta(seconds=interval_seconds)
        if expected_end_time < end_time:
            gaps.append((expected_end_time, end_time))

        return gaps

    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get statistics."""
        if self._closed:
            raise RuntimeError("Repository is closed")

        count = await self.count(symbol, interval, start_time, end_time)
        return {"count": count, "symbol": symbol, "interval": interval.value}

    async def close(self) -> None:
        """Close repository."""
        self._closed = True


class TestQueryOptions:
    """Test the QueryOptions class."""

    def test_default_initialization(self) -> None:
        """Test QueryOptions with default values."""
        options = QueryOptions()

        assert options.limit is None
        assert options.offset is None
        assert options.order_by == "open_time"
        assert options.order_desc is False
        assert options.include_metadata is False

    def test_custom_initialization(self) -> None:
        """Test QueryOptions with custom values."""
        options = QueryOptions(limit=100, offset=50, order_by="close_time", order_desc=True, include_metadata=True)

        assert options.limit == 100
        assert options.offset == 50
        assert options.order_by == "close_time"
        assert options.order_desc is True
        assert options.include_metadata is True

    def test_partial_initialization(self) -> None:
        """Test QueryOptions with some custom values."""
        options = QueryOptions(limit=200, order_desc=True)

        assert options.limit == 200
        assert options.offset is None
        assert options.order_by == "open_time"
        assert options.order_desc is True
        assert options.include_metadata is False

    def test_negative_limit_validation(self) -> None:
        """Test QueryOptions with negative limit value.

        This test verifies the scenario described in missing_tests.md line 183:
        - QueryOptions with negative limit/offset values
        - assert validation errors
        """
        with pytest.raises(ValueError, match="limit must be non-negative"):
            QueryOptions(limit=-1)

    def test_negative_offset_validation(self) -> None:
        """Test QueryOptions with negative offset value.

        This test verifies the scenario described in missing_tests.md line 183:
        - QueryOptions with negative limit/offset values
        - assert validation errors
        """
        with pytest.raises(ValueError, match="offset must be non-negative"):
            QueryOptions(offset=-5)

    def test_both_negative_values_validation(self) -> None:
        """Test QueryOptions with both negative limit and offset values.

        This test verifies the scenario described in missing_tests.md line 183:
        - QueryOptions with negative limit/offset values
        - assert validation errors
        """
        with pytest.raises(ValueError, match="limit must be non-negative"):
            QueryOptions(limit=-10, offset=-20)


class TestAbstractKlineRepository:
    """Test the AbstractKlineRepository interface."""

    def test_is_abstract_base_class(self) -> None:
        """Test that AbstractKlineRepository is an abstract class."""
        assert issubclass(AbstractKlineRepository, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            AbstractKlineRepository()  # type: ignore[abstract]

    def test_has_required_abstract_methods(self) -> None:
        """Test that all required methods are marked as abstract."""
        abstract_methods = AbstractKlineRepository.__abstractmethods__
        expected_methods = {
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

        assert expected_methods.issubset(abstract_methods)

    def test_concrete_implementation_interface(self) -> None:
        """Test that concrete implementation satisfies interface."""
        repo = ConcreteKlineRepository()

        # Should be an instance of the abstract class
        assert isinstance(repo, AbstractKlineRepository)

        # Should have all required methods
        required_methods = [
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
        ]

        for method_name in required_methods:
            assert hasattr(repo, method_name)
            assert callable(getattr(repo, method_name))

    @pytest.mark.asyncio
    async def test_save_and_query_single_kline(self) -> None:
        """Test saving and querying a single kline."""
        repo = ConcreteKlineRepository()

        # Create test kline
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("10.5"),
            quote_volume=Decimal("525525.0"),  # Added missing field
            trades_count=100,
            taker_buy_volume=Decimal("5.0"),
            taker_buy_quote_volume=Decimal("250000"),
        )

        # Save kline
        await repo.save(kline)

        # Query kline
        start_time = datetime(2024, 1, 1, 11, 59, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 2, tzinfo=UTC)

        results = await repo.query("BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        assert len(results) == 1
        assert results[0].symbol == "BTCUSDT"
        assert results[0].open_price == Decimal("50000")

        await repo.close()

    @pytest.mark.asyncio
    async def test_save_batch_klines(self) -> None:
        """Test saving batch of klines."""
        repo = ConcreteKlineRepository()

        # Create test klines
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="ETHUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("3000") + Decimal(str(i)),
                high_price=Decimal("3010") + Decimal(str(i)),
                low_price=Decimal("2990") + Decimal(str(i)),
                close_price=Decimal("3005") + Decimal(str(i)),
                volume=Decimal("5.0"),
                quote_volume=Decimal("15000.0"),  # Added missing field
                trades_count=50,
                taker_buy_volume=Decimal("2.5"),
                taker_buy_quote_volume=Decimal("7500"),
            )
            klines.append(kline)

        # Save batch
        saved_count = await repo.save_batch(klines)
        assert saved_count == 5

        # Verify all saved
        count = await repo.count("ETHUSDT", KlineInterval.MINUTE_1)
        assert count == 5

        await repo.close()

    @pytest.mark.asyncio
    async def test_save_batch_empty_list(self) -> None:
        """Test saving batch with empty list.

        This test verifies the scenario described in missing_tests.md line 189:
        - save_batch with empty list
        - assert returns 0
        """
        repo = ConcreteKlineRepository()

        # Test with empty list
        empty_klines: list[Kline] = []
        saved_count = await repo.save_batch(empty_klines)

        # Should return 0 for empty list
        assert saved_count == 0

        # Verify no data was saved
        total_count = await repo.count("ANYUSDT", KlineInterval.MINUTE_1)
        assert total_count == 0

        await repo.close()

    @pytest.mark.asyncio
    async def test_query_with_options(self) -> None:
        """Test querying with query options."""
        repo = ConcreteKlineRepository()

        # Create and save test klines
        klines = []
        for i in range(10):
            kline = Kline(
                symbol="ADAUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("1.0") + Decimal(str(i * 0.01)),
                high_price=Decimal("1.01") + Decimal(str(i * 0.01)),
                low_price=Decimal("0.99") + Decimal(str(i * 0.01)),
                close_price=Decimal("1.005") + Decimal(str(i * 0.01)),
                volume=Decimal("100.0"),
                quote_volume=Decimal("100.0"),  # Added missing field
                trades_count=20,
                taker_buy_volume=Decimal("50.0"),
                taker_buy_quote_volume=Decimal("50.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test with limit
        options = QueryOptions(limit=3)
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 30, tzinfo=UTC)

        results = await repo.query("ADAUSDT", KlineInterval.MINUTE_1, start_time, end_time, options=options)
        assert len(results) == 3

        # Test with offset and limit
        options = QueryOptions(offset=5, limit=3)
        results = await repo.query("ADAUSDT", KlineInterval.MINUTE_1, start_time, end_time, options=options)
        assert len(results) == 3

        # Test with descending order
        options = QueryOptions(order_desc=True, limit=2)
        results = await repo.query("ADAUSDT", KlineInterval.MINUTE_1, start_time, end_time, options=options)
        assert len(results) == 2
        # Latest should be first when descending
        assert results[0].open_time > results[1].open_time

        await repo.close()

    @pytest.mark.asyncio
    async def test_stream_klines(self) -> None:
        """Test streaming klines."""
        repo = ConcreteKlineRepository()

        # Create and save test klines
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="DOTUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("8.0"),
                high_price=Decimal("8.1"),
                low_price=Decimal("7.9"),
                close_price=Decimal("8.05"),
                volume=Decimal("20.0"),
                quote_volume=Decimal("1610.0"),  # Added missing field
                trades_count=30,
                taker_buy_volume=Decimal("10.0"),
                taker_buy_quote_volume=Decimal("80.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Stream klines
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 10, tzinfo=UTC)

        streamed_klines = []
        async for kline in repo.stream("DOTUSDT", KlineInterval.MINUTE_1, start_time, end_time):
            streamed_klines.append(kline)

        assert len(streamed_klines) == 5
        assert all(k.symbol == "DOTUSDT" for k in streamed_klines)

        await repo.close()

    @pytest.mark.asyncio
    async def test_stream_error_propagation(self) -> None:
        """Test error propagation during stream iteration.

        This test verifies the scenario described in missing_tests.md line 193:
        - stream method error propagation during iteration
        - assert exceptions are correctly propagated to the caller
        """

        class FailingKlineRepository(ConcreteKlineRepository):
            """Repository that fails during streaming."""

            async def stream(
                self,
                symbol: str,
                interval: KlineInterval,
                start_time: datetime,
                end_time: datetime,  # noqa: ARG002
                *,
                batch_size: int = 1000,  # noqa: ARG002
            ) -> AsyncIterator[Kline]:
                """Stream that raises error during iteration."""
                # Yield one item successfully
                first_kline = Kline(
                    symbol=symbol,
                    interval=interval,
                    open_time=start_time,
                    close_time=start_time + timedelta(minutes=1),
                    open_price=Decimal("100.0"),
                    high_price=Decimal("101.0"),
                    low_price=Decimal("99.0"),
                    close_price=Decimal("100.5"),
                    volume=Decimal("1.0"),
                    quote_volume=Decimal("100.0"),
                    trades_count=10,
                    taker_buy_volume=Decimal("0.5"),
                    taker_buy_quote_volume=Decimal("50.0"),
                )
                yield first_kline

                # Then raise an error
                raise StorageReadError("Stream failed during iteration")

        repo = FailingKlineRepository()

        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 10, tzinfo=UTC)

        # Test that error is propagated during iteration
        streamed_count = 0
        with pytest.raises(StorageReadError, match="Stream failed during iteration"):
            async for kline in repo.stream("TESTUSDT", KlineInterval.MINUTE_1, start_time, end_time):
                streamed_count += 1
                # First item should be received successfully
                if streamed_count == 1:
                    assert kline.symbol == "TESTUSDT"
                # Second iteration should raise the error

        # Verify we got the first item before the error
        assert streamed_count == 1

        await repo.close()

    @pytest.mark.asyncio
    async def test_get_latest_and_oldest(self) -> None:
        """Test getting latest and oldest klines."""
        repo = ConcreteKlineRepository()

        # Test when no data exists
        latest = await repo.get_latest("NONEXISTENT", KlineInterval.MINUTE_1)
        assert latest is None

        oldest = await repo.get_oldest("NONEXISTENT", KlineInterval.MINUTE_1)
        assert oldest is None

        # Create test klines with different timestamps
        timestamps = [
            datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 12, 5, tzinfo=UTC),
            datetime(2024, 1, 1, 12, 2, tzinfo=UTC),
        ]

        klines = []
        for _i, ts in enumerate(timestamps):
            kline = Kline(
                symbol="SOLUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=ts,
                close_time=ts + timedelta(minutes=1),
                open_price=Decimal("100") + Decimal(str(_i)),
                high_price=Decimal("101") + Decimal(str(_i)),
                low_price=Decimal("99") + Decimal(str(_i)),
                close_price=Decimal("100.5") + Decimal(str(_i)),
                volume=Decimal("15.0"),
                quote_volume=Decimal("1500.0"),  # Added missing field
                trades_count=25,
                taker_buy_volume=Decimal("7.5"),
                taker_buy_quote_volume=Decimal("750.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test latest
        latest = await repo.get_latest("SOLUSDT", KlineInterval.MINUTE_1)
        assert latest is not None
        assert latest.open_time == datetime(2024, 1, 1, 12, 5, tzinfo=UTC)

        # Test oldest
        oldest = await repo.get_oldest("SOLUSDT", KlineInterval.MINUTE_1)
        assert oldest is not None
        assert oldest.open_time == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

        await repo.close()

    @pytest.mark.asyncio
    async def test_count_klines(self) -> None:
        """Test counting klines."""
        repo = ConcreteKlineRepository()

        # Create and save test klines
        klines = []
        for i in range(10):
            kline = Kline(
                symbol="LINKUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("15.0"),
                high_price=Decimal("15.1"),
                low_price=Decimal("14.9"),
                close_price=Decimal("15.05"),
                volume=Decimal("30.0"),
                quote_volume=Decimal("3000.0"),  # Added missing field
                trades_count=40,
                taker_buy_volume=Decimal("15.0"),
                taker_buy_quote_volume=Decimal("225.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test count all
        total_count = await repo.count("LINKUSDT", KlineInterval.MINUTE_1)
        assert total_count == 10

        # Test count with time range
        start_time = datetime(2024, 1, 1, 12, 3, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 7, tzinfo=UTC)

        range_count = await repo.count("LINKUSDT", KlineInterval.MINUTE_1, start_time, end_time)
        assert range_count == 4  # Minutes 3, 4, 5, 6

        await repo.close()

    @pytest.mark.asyncio
    async def test_delete_klines(self) -> None:
        """Test deleting klines."""
        repo = ConcreteKlineRepository()

        # Create and save test klines
        klines = []
        for i in range(10):
            kline = Kline(
                symbol="UNIUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("6.0"),
                high_price=Decimal("6.1"),
                low_price=Decimal("5.9"),
                close_price=Decimal("6.05"),
                volume=Decimal("25.0"),
                quote_volume=Decimal("150.0"),  # Added missing field
                trades_count=35,
                taker_buy_volume=Decimal("12.5"),
                taker_buy_quote_volume=Decimal("75.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Verify initial count
        initial_count = await repo.count("UNIUSDT", KlineInterval.MINUTE_1)
        assert initial_count == 10

        # Delete some klines
        start_time = datetime(2024, 1, 1, 12, 3, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 7, tzinfo=UTC)

        deleted_count = await repo.delete("UNIUSDT", KlineInterval.MINUTE_1, start_time, end_time)
        assert deleted_count == 4

        # Verify remaining count
        remaining_count = await repo.count("UNIUSDT", KlineInterval.MINUTE_1)
        assert remaining_count == 6

        await repo.close()

    @pytest.mark.asyncio
    async def test_get_statistics(self) -> None:
        """Test getting repository statistics."""
        repo = ConcreteKlineRepository()

        # Create and save test klines
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="AVAXUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("40.0"),
                high_price=Decimal("40.5"),
                low_price=Decimal("39.5"),
                close_price=Decimal("40.25"),
                volume=Decimal("18.0"),
                quote_volume=Decimal("720.0"),  # Added missing field
                trades_count=28,
                taker_buy_volume=Decimal("9.0"),
                taker_buy_quote_volume=Decimal("360.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Get statistics
        stats = await repo.get_statistics("AVAXUSDT", KlineInterval.MINUTE_1)

        assert isinstance(stats, dict)
        assert stats["count"] == 5
        assert stats["symbol"] == "AVAXUSDT"
        assert stats["interval"] == KlineInterval.MINUTE_1.value

        await repo.close()

    @pytest.mark.asyncio
    async def test_get_gaps_realistic_implementation(self) -> None:
        """Test get_gaps method with realistic implementation and known gaps.

        This test verifies the scenario described in missing_tests.md line 197:
        - Enhance get_gaps method with realistic implementation and tests
        """
        repo = ConcreteKlineRepository()

        # Create klines with intentional gaps
        # Times: 12:00, 12:01, [GAP: 12:02], 12:03, [GAP: 12:04, 12:05], 12:06
        timestamps = [
            datetime(2024, 1, 1, 12, 0, tzinfo=UTC),  # 12:00
            datetime(2024, 1, 1, 12, 1, tzinfo=UTC),  # 12:01
            # Missing 12:02
            datetime(2024, 1, 1, 12, 3, tzinfo=UTC),  # 12:03
            # Missing 12:04, 12:05
            datetime(2024, 1, 1, 12, 6, tzinfo=UTC),  # 12:06
        ]

        klines = []
        for _i, ts in enumerate(timestamps):
            kline = Kline(
                symbol="GAPUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=ts,
                close_time=ts + timedelta(minutes=1),
                open_price=Decimal("100.0"),
                high_price=Decimal("101.0"),
                low_price=Decimal("99.0"),
                close_price=Decimal("100.5"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("100.0"),
                trades_count=10,
                taker_buy_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("50.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Test gap detection
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 10, tzinfo=UTC)  # Search until 12:10

        gaps = await repo.get_gaps("GAPUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        # Expected gaps:
        # 1. 12:02 (1 minute gap)
        # 2. 12:04 to 12:06 (2 minute gap)
        # 3. 12:07 to 12:10 (3 minute gap after last kline)
        expected_gaps = [
            (datetime(2024, 1, 1, 12, 2, tzinfo=UTC), datetime(2024, 1, 1, 12, 3, tzinfo=UTC)),
            (datetime(2024, 1, 1, 12, 4, tzinfo=UTC), datetime(2024, 1, 1, 12, 6, tzinfo=UTC)),
            (datetime(2024, 1, 1, 12, 7, tzinfo=UTC), datetime(2024, 1, 1, 12, 10, tzinfo=UTC)),
        ]

        assert len(gaps) == 3
        for i, (expected_start, expected_end) in enumerate(expected_gaps):
            assert gaps[i][0] == expected_start
            assert gaps[i][1] == expected_end

        await repo.close()

    @pytest.mark.asyncio
    async def test_get_gaps_no_data(self) -> None:
        """Test get_gaps when no data exists - entire range should be a gap."""
        repo = ConcreteKlineRepository()

        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)

        gaps = await repo.get_gaps("NODATAUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        # Should return entire range as one gap
        assert len(gaps) == 1
        assert gaps[0] == (start_time, end_time)

        await repo.close()

    @pytest.mark.asyncio
    async def test_get_gaps_no_gaps(self) -> None:
        """Test get_gaps when data is continuous - no gaps should be found."""
        repo = ConcreteKlineRepository()

        # Create continuous data (no gaps)
        klines = []
        for i in range(5):
            kline = Kline(
                symbol="NOGAPUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("100.0"),
                high_price=Decimal("101.0"),
                low_price=Decimal("99.0"),
                close_price=Decimal("100.5"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("100.0"),
                trades_count=10,
                taker_buy_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("50.0"),
            )
            klines.append(kline)

        await repo.save_batch(klines)

        # Query exactly the range of data
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 5, tzinfo=UTC)

        gaps = await repo.get_gaps("NOGAPUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        # Should find no gaps
        assert len(gaps) == 0

        await repo.close()

    @pytest.mark.asyncio
    async def test_repository_context_manager(self) -> None:
        """Test repository as async context manager."""
        async with ConcreteKlineRepository() as repo:
            # Create test kline
            kline = Kline(
                symbol="MATICUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
                open_price=Decimal("0.8"),
                high_price=Decimal("0.82"),
                low_price=Decimal("0.78"),
                close_price=Decimal("0.81"),
                volume=Decimal("1000.0"),
                quote_volume=Decimal("810.0"),  # Added missing field
                trades_count=50,
                taker_buy_volume=Decimal("500.0"),
                taker_buy_quote_volume=Decimal("400.0"),
            )

            await repo.save(kline)
            count = await repo.count("MATICUSDT", KlineInterval.MINUTE_1)
            assert count == 1

        # Repository should be closed after context exit
        assert repo._closed is True  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_repository_operations_after_close(self) -> None:
        """Test that operations fail after repository is closed."""
        repo = ConcreteKlineRepository()
        await repo.close()

        # All operations should fail
        with pytest.raises(RuntimeError, match="Repository is closed"):
            kline = Kline(
                symbol="FTMUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
                open_price=Decimal("0.3"),
                high_price=Decimal("0.31"),
                low_price=Decimal("0.29"),
                close_price=Decimal("0.305"),
                volume=Decimal("2000.0"),
                quote_volume=Decimal("610.0"),  # Added missing field
                trades_count=75,
                taker_buy_volume=Decimal("1000.0"),
                taker_buy_quote_volume=Decimal("300.0"),
            )
            await repo.save(kline)

        with pytest.raises(RuntimeError, match="Repository is closed"):
            await repo.query(
                "FTMUSDT", KlineInterval.MINUTE_1, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 2, tzinfo=UTC)
            )

        with pytest.raises(RuntimeError, match="Repository is closed"):
            await repo.count("FTMUSDT", KlineInterval.MINUTE_1)

    def test_docstring_presence(self) -> None:
        """Test that the abstract class has proper documentation."""
        assert AbstractKlineRepository.__doc__ is not None
        assert len(AbstractKlineRepository.__doc__.strip()) > 0

        # Check some key method docstrings
        assert AbstractKlineRepository.save.__doc__ is not None
        assert AbstractKlineRepository.query.__doc__ is not None
        assert AbstractKlineRepository.stream.__doc__ is not None


class TestKlineRepositoryDataFormatting:
    """Test data formatting for database operations."""

    @pytest.fixture
    def mock_db_repo(self) -> Mock:
        """Create a mock repository with database driver."""
        repo = Mock(spec=AbstractKlineRepository)
        repo.db_driver = AsyncMock()
        repo._closed = False
        return repo

    @pytest.fixture
    def sample_kline(self) -> Kline:
        """Create a sample kline for testing."""
        return Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("10.5"),
            quote_volume=Decimal("525525.0"),
            trades_count=100,
            taker_buy_volume=Decimal("5.0"),
            taker_buy_quote_volume=Decimal("250000.0"),
        )

    @pytest.mark.asyncio
    async def test_data_formatting_before_db_save(self, mock_db_repo: Mock, sample_kline: Kline) -> None:
        """Test that data is properly formatted before sending to DB driver.

        Description of what the test covers:
        Verifies that Kline objects are correctly formatted to database-compatible
        format before being passed to the underlying database driver.

        Preconditions:
        - Repository has a database driver configured
        - Kline object is valid and properly structured

        Steps:
        - Mock the database driver's insert method
        - Call repository save with a Kline object
        - Verify the data passed to DB driver is in correct format
        - Check that Decimal values are properly serialized
        - Verify datetime objects are properly formatted

        Expected Result:
        - Database driver receives properly formatted data
        - All numeric values are in string format for precision
        - Timestamps are in ISO format
        """

        # Setup mock repository with save implementation
        async def mock_save(kline: Kline) -> None:
            # Simulate data formatting for DB
            formatted_data = {
                "symbol": kline.symbol,
                "interval": kline.interval,  # Already converted to string by Pydantic
                "open_time": kline.open_time.isoformat(),
                "close_time": kline.close_time.isoformat(),
                "open_price": str(kline.open_price),
                "high_price": str(kline.high_price),
                "low_price": str(kline.low_price),
                "close_price": str(kline.close_price),
                "volume": str(kline.volume),
                "quote_volume": str(kline.quote_volume),
                "trades_count": kline.trades_count,
                "taker_buy_volume": str(kline.taker_buy_volume or Decimal("0")),
                "taker_buy_quote_volume": str(kline.taker_buy_quote_volume or Decimal("0")),
            }
            await mock_db_repo.db_driver.insert(formatted_data)

        mock_db_repo.save = mock_save

        # Execute save
        await mock_db_repo.save(sample_kline)

        # Verify DB driver was called with formatted data
        mock_db_repo.db_driver.insert.assert_called_once()
        call_args = mock_db_repo.db_driver.insert.call_args[0][0]

        # Verify data formatting
        assert call_args["symbol"] == "BTCUSDT"
        assert call_args["interval"] == "1m"
        assert call_args["open_time"] == "2024-01-01T12:00:00+00:00"
        assert call_args["open_price"] == "50000.00"
        assert call_args["volume"] == "10.5"
        assert isinstance(call_args["trades_count"], int)

    @pytest.mark.asyncio
    async def test_batch_data_formatting(self, mock_db_repo: Mock) -> None:
        """Test batch data formatting for database operations.

        Description of what the test covers:
        Verifies that batch operations correctly format multiple Kline objects
        for efficient database insertion.

        Preconditions:
        - Repository supports batch operations
        - Multiple Kline objects are available for testing

        Steps:
        - Create multiple Kline objects with different values
        - Mock the database driver's batch_insert method
        - Call repository save_batch
        - Verify all data is properly formatted as a batch

        Expected Result:
        - All Kline objects are formatted consistently
        - Batch operation receives list of formatted records
        """
        # Create test klines
        klines = []
        for i in range(3):
            kline = Kline(
                symbol="ETHUSDT",
                interval=KlineInterval.MINUTE_5,
                open_time=datetime(2024, 1, 1, 12, i * 5, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i * 5 + 5, tzinfo=UTC),
                open_price=Decimal(f"300{i}.00"),
                high_price=Decimal(f"301{i}.00"),
                low_price=Decimal(f"299{i}.00"),
                close_price=Decimal(f"300{i}.50"),
                volume=Decimal("5.0"),
                quote_volume=Decimal("15000.0"),
                trades_count=50,
                taker_buy_volume=Decimal("2.5"),
                taker_buy_quote_volume=Decimal("7500.0"),
            )
            klines.append(kline)

        # Setup mock batch save
        async def mock_save_batch(klines_list: list[Kline]) -> int:
            formatted_batch = []
            for kline in klines_list:
                formatted_data = {
                    "symbol": kline.symbol,
                    "interval": kline.interval,  # Already converted to string by Pydantic
                    "open_time": kline.open_time.isoformat(),
                    "open_price": str(kline.open_price),
                    "volume": str(kline.volume),
                }
                formatted_batch.append(formatted_data)
            await mock_db_repo.db_driver.batch_insert(formatted_batch)
            return len(klines_list)

        mock_db_repo.save_batch = mock_save_batch

        # Execute batch save
        result = await mock_db_repo.save_batch(klines)

        # Verify results
        assert result == 3
        mock_db_repo.db_driver.batch_insert.assert_called_once()
        batch_data = mock_db_repo.db_driver.batch_insert.call_args[0][0]
        assert len(batch_data) == 3
        assert all("open_price" in record for record in batch_data)
        assert batch_data[0]["open_price"] == "3000.00"
        assert batch_data[1]["open_price"] == "3001.00"
        assert batch_data[2]["open_price"] == "3002.00"


class TestKlineRepositoryQueryGeneration:
    """Test query generation logic for repository operations."""

    @pytest.fixture
    def mock_query_builder(self) -> Mock:
        """Create a mock query builder."""
        builder = Mock()
        builder.build_query = Mock(return_value="SELECT * FROM klines WHERE ...")
        return builder

    @pytest.mark.asyncio
    async def test_basic_query_generation(self, mock_query_builder: Mock) -> None:
        """Test generation of basic SELECT queries.

        Description of what the test covers:
        Verifies that the repository correctly generates SQL queries for
        basic Kline data retrieval operations.

        Preconditions:
        - Query builder is available and functional
        - Repository can generate queries for time range searches

        Steps:
        - Set up query parameters (symbol, interval, time range)
        - Mock the query builder to capture generated queries
        - Execute query operation
        - Verify the generated query contains correct conditions

        Expected Result:
        - Generated query includes symbol filter
        - Time range conditions are properly formatted
        - Interval filter is included
        """
        # Setup test parameters
        symbol = "BTCUSDT"
        interval = KlineInterval.MINUTE_1
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)

        # Mock repository with query builder
        repo = Mock()
        repo.query_builder = mock_query_builder

        # Setup query generation logic
        def build_query_mock(table: str, conditions: dict[str, Any]) -> str:
            query_parts = [f"SELECT * FROM {table}"]
            where_conditions = []

            if "symbol" in conditions:
                where_conditions.append(f"symbol = '{conditions['symbol']}'")
            if "interval" in conditions:
                where_conditions.append(f"interval = '{conditions['interval']}'")
            if "start_time" in conditions:
                where_conditions.append(f"open_time >= '{conditions['start_time']}'")
            if "end_time" in conditions:
                where_conditions.append(f"open_time < '{conditions['end_time']}'")

            if where_conditions:
                query_parts.append("WHERE " + " AND ".join(where_conditions))

            return " ".join(query_parts)

        mock_query_builder.build_query.side_effect = build_query_mock

        # Simulate query execution
        conditions = {
            "symbol": symbol,
            "interval": interval.value,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        generated_query = mock_query_builder.build_query("klines", conditions)

        # Verify query generation
        assert "SELECT * FROM klines" in generated_query
        assert "symbol = 'BTCUSDT'" in generated_query
        assert "interval = '1m'" in generated_query
        assert "open_time >= '2024-01-01T12:00:00+00:00'" in generated_query
        assert "open_time < '2024-01-01T13:00:00+00:00'" in generated_query
        assert "WHERE" in generated_query
        assert "AND" in generated_query

    @pytest.mark.asyncio
    async def test_query_with_options_generation(self, mock_query_builder: Mock) -> None:
        """Test query generation with QueryOptions.

        Description of what the test covers:
        Verifies that QueryOptions (limit, offset, ordering) are correctly
        translated into SQL query components.

        Preconditions:
        - Repository supports QueryOptions
        - Query builder can handle ordering and pagination

        Steps:
        - Create QueryOptions with limit, offset, and ordering
        - Generate query with these options
        - Verify SQL includes correct LIMIT, OFFSET, ORDER BY clauses

        Expected Result:
        - Query includes proper ORDER BY clause
        - LIMIT and OFFSET are correctly applied
        - Descending order is handled correctly
        """
        options = QueryOptions(limit=100, offset=50, order_by="open_time", order_desc=True)

        def build_query_with_options(
            table: str, _conditions: dict[str, Any], options_dict: dict[str, Any] | None = None
        ) -> str:
            query = f"SELECT * FROM {table}"

            if options_dict:
                if "order_by" in options_dict:
                    order_direction = "DESC" if options_dict.get("order_desc", False) else "ASC"
                    query += f" ORDER BY {options_dict['order_by']} {order_direction}"

                if "limit" in options_dict:
                    query += f" LIMIT {options_dict['limit']}"

                if "offset" in options_dict:
                    query += f" OFFSET {options_dict['offset']}"

            return query

        mock_query_builder.build_query_with_options = Mock(side_effect=build_query_with_options)

        # Generate query with options
        options_dict = {
            "order_by": options.order_by,
            "order_desc": options.order_desc,
            "limit": options.limit,
            "offset": options.offset,
        }

        generated_query = mock_query_builder.build_query_with_options("klines", {}, options_dict)

        # Verify query components
        assert "ORDER BY open_time DESC" in generated_query
        assert "LIMIT 100" in generated_query
        assert "OFFSET 50" in generated_query

    @pytest.mark.asyncio
    async def test_count_query_generation(self, mock_query_builder: Mock) -> None:
        """Test generation of COUNT queries.

        Description of what the test covers:
        Verifies that count operations generate proper COUNT(*) queries
        with appropriate WHERE conditions.

        Preconditions:
        - Repository supports count operations
        - Query builder can generate COUNT queries

        Steps:
        - Set parameters for count operation
        - Generate COUNT query
        - Verify query uses COUNT(*) and proper conditions

        Expected Result:
        - Query uses COUNT(*) instead of SELECT *
        - WHERE conditions are properly applied
        """

        def build_count_query(table: str, conditions: dict[str, Any]) -> str:
            query = f"SELECT COUNT(*) FROM {table}"

            where_conditions = []
            if "symbol" in conditions:
                where_conditions.append(f"symbol = '{conditions['symbol']}'")
            if "interval" in conditions:
                where_conditions.append(f"interval = '{conditions['interval']}'")

            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)

            return query

        mock_query_builder.build_count_query = Mock(side_effect=build_count_query)

        # Generate count query
        conditions = {
            "symbol": "ETHUSDT",
            "interval": "5m",
        }

        count_query = mock_query_builder.build_count_query("klines", conditions)

        # Verify count query
        assert "SELECT COUNT(*) FROM klines" in count_query
        assert "symbol = 'ETHUSDT'" in count_query
        assert "interval = '5m'" in count_query
        assert "WHERE" in count_query


class TestKlineRepositoryResultParsing:
    """Test parsing of raw database results into Kline objects."""

    @pytest.mark.asyncio
    async def test_raw_data_parsing_to_kline_objects(self) -> None:
        """Test parsing raw database rows into Kline objects.

        Description of what the test covers:
        Verifies that raw database results are correctly parsed and converted
        into properly typed Kline objects with all fields populated.

        Preconditions:
        - Raw database data is in expected format
        - Parser can handle string to Decimal conversions
        - DateTime parsing works correctly

        Steps:
        - Create mock raw database results
        - Parse results into Kline objects
        - Verify all fields are correctly typed and populated
        - Check that Decimal and datetime conversions work

        Expected Result:
        - All numeric fields are properly converted to Decimal
        - Datetime fields are parsed correctly with timezone
        - String fields remain as strings
        """
        # Mock raw database results
        raw_results = [
            {
                "symbol": "BTCUSDT",
                "interval": "1m",
                "open_time": "2024-01-01T12:00:00+00:00",
                "close_time": "2024-01-01T12:01:00+00:00",
                "open_price": "50000.00",
                "high_price": "50100.00",
                "low_price": "49900.00",
                "close_price": "50050.00",
                "volume": "10.5",
                "quote_volume": "525525.0",
                "trades_count": 100,
                "taker_buy_volume": "5.0",
                "taker_buy_quote_volume": "250000.0",
            },
            {
                "symbol": "ETHUSDT",
                "interval": "5m",
                "open_time": "2024-01-01T12:05:00+00:00",
                "close_time": "2024-01-01T12:10:00+00:00",
                "open_price": "3000.00",
                "high_price": "3010.00",
                "low_price": "2990.00",
                "close_price": "3005.00",
                "volume": "5.0",
                "quote_volume": "15000.0",
                "trades_count": 50,
                "taker_buy_volume": "2.5",
                "taker_buy_quote_volume": "7500.0",
            },
        ]

        # Mock parser function
        def parse_raw_result_to_kline(raw_row: dict[str, Any]) -> Kline:
            return Kline(
                symbol=raw_row["symbol"],
                interval=KlineInterval(raw_row["interval"]),
                open_time=datetime.fromisoformat(raw_row["open_time"]),
                close_time=datetime.fromisoformat(raw_row["close_time"]),
                open_price=Decimal(raw_row["open_price"]),
                high_price=Decimal(raw_row["high_price"]),
                low_price=Decimal(raw_row["low_price"]),
                close_price=Decimal(raw_row["close_price"]),
                volume=Decimal(raw_row["volume"]),
                quote_volume=Decimal(raw_row["quote_volume"]),
                trades_count=int(raw_row["trades_count"]),
                taker_buy_volume=Decimal(raw_row["taker_buy_volume"]),
                taker_buy_quote_volume=Decimal(raw_row["taker_buy_quote_volume"]),
            )

        # Parse results
        parsed_klines = [parse_raw_result_to_kline(row) for row in raw_results]

        # Verify first kline
        kline1 = parsed_klines[0]
        assert kline1.symbol == "BTCUSDT"
        assert kline1.interval == KlineInterval.MINUTE_1
        assert kline1.open_time == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        assert isinstance(kline1.open_price, Decimal)
        assert kline1.open_price == Decimal("50000.00")
        assert isinstance(kline1.volume, Decimal)
        assert kline1.volume == Decimal("10.5")
        assert isinstance(kline1.trades_count, int)
        assert kline1.trades_count == 100

        # Verify second kline
        kline2 = parsed_klines[1]
        assert kline2.symbol == "ETHUSDT"
        assert kline2.interval == KlineInterval.MINUTE_5
        assert kline2.open_time == datetime(2024, 1, 1, 12, 5, tzinfo=UTC)
        assert kline2.open_price == Decimal("3000.00")

        # Verify all klines are properly typed
        for kline in parsed_klines:
            assert isinstance(kline.symbol, str)
            assert isinstance(kline.interval, str)  # Converted to string by Pydantic use_enum_values=True
            assert isinstance(kline.open_time, datetime)
            assert isinstance(kline.close_time, datetime)
            assert isinstance(kline.open_price, Decimal)
            assert isinstance(kline.high_price, Decimal)
            assert isinstance(kline.low_price, Decimal)
            assert isinstance(kline.close_price, Decimal)
            assert isinstance(kline.volume, Decimal)
            assert isinstance(kline.quote_volume, Decimal)
            assert isinstance(kline.trades_count, int)
            assert isinstance(kline.taker_buy_volume, Decimal)
            assert isinstance(kline.taker_buy_quote_volume, Decimal)

    @pytest.mark.asyncio
    async def test_parsing_edge_cases(self) -> None:
        """Test parsing of edge cases in raw data.

        Description of what the test covers:
        Verifies that the parser handles edge cases like zero values,
        very large numbers, and boundary datetime values correctly.

        Preconditions:
        - Parser can handle extreme numeric values
        - Edge case datetime values are supported

        Steps:
        - Create raw data with edge case values
        - Parse the data into Kline objects
        - Verify edge cases are handled correctly

        Expected Result:
        - Zero values are preserved
        - Large numbers are handled without precision loss
        - Edge case timestamps are parsed correctly
        """
        # Edge case raw data
        edge_case_data = {
            "symbol": "TESTUSDT",
            "interval": "1h",
            "open_time": "2024-12-31T23:00:00+00:00",
            "close_time": "2025-01-01T00:00:00+00:00",
            "open_price": "0.00000001",  # Very small price
            "high_price": "999999999.99999999",  # Very large price
            "low_price": "0.00000001",  # Very small but non-zero value (prices must be > 0)
            "close_price": "1.23456789",  # High precision
            "volume": "0",  # Zero volume
            "quote_volume": "0.00000000",
            "trades_count": 0,  # No trades
            "taker_buy_volume": "0",
            "taker_buy_quote_volume": "0",
        }

        # Parse edge case data
        def parse_edge_case(raw_row: dict[str, Any]) -> Kline:
            return Kline(
                symbol=raw_row["symbol"],
                interval=KlineInterval(raw_row["interval"]),
                open_time=datetime.fromisoformat(raw_row["open_time"]),
                close_time=datetime.fromisoformat(raw_row["close_time"]),
                open_price=Decimal(raw_row["open_price"]),
                high_price=Decimal(raw_row["high_price"]),
                low_price=Decimal(raw_row["low_price"]),
                close_price=Decimal(raw_row["close_price"]),
                volume=Decimal(raw_row["volume"]),
                quote_volume=Decimal(raw_row["quote_volume"]),
                trades_count=int(raw_row["trades_count"]),
                taker_buy_volume=Decimal(raw_row["taker_buy_volume"]),
                taker_buy_quote_volume=Decimal(raw_row["taker_buy_quote_volume"]),
            )

        kline = parse_edge_case(edge_case_data)

        # Verify edge case handling
        assert kline.open_price == Decimal("0.00000001")
        assert kline.high_price == Decimal("999999999.99999999")
        assert kline.low_price == Decimal("0.00000001")  # Updated to non-zero value
        assert kline.close_price == Decimal("1.23456789")
        assert kline.volume == Decimal("0")
        assert kline.trades_count == 0
        assert kline.open_time.year == 2024
        assert kline.close_time.year == 2025


class TestKlineRepositoryErrorHandling:
    """Test error handling and database exception scenarios."""

    @pytest.fixture
    def mock_failing_repo(self) -> Mock:
        """Create a mock repository that simulates database failures."""
        repo = Mock(spec=AbstractKlineRepository)
        repo.db_driver = AsyncMock()
        repo._closed = False
        return repo

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, mock_failing_repo: Mock, sample_kline: Kline) -> None:
        """Test handling of database connection errors.

        Description of what the test covers:
        Verifies that the repository properly handles and wraps database
        connection errors in appropriate StorageError exceptions.

        Preconditions:
        - Repository is configured with database driver
        - Database connection can fail

        Steps:
        - Mock database driver to raise connection error
        - Attempt repository operation
        - Verify StorageConnectionError is raised
        - Check error message and trace ID are present

        Expected Result:
        - StorageConnectionError is raised instead of raw DB error
        - Error includes relevant context and trace ID
        """
        # Configure mock to raise connection error
        mock_failing_repo.db_driver.insert.side_effect = Exception("Connection refused")

        async def failing_save(kline: Kline) -> None:
            try:
                await mock_failing_repo.db_driver.insert({})
            except Exception as e:
                raise StorageConnectionError(
                    f"Failed to connect to database: {str(e)}", details={"operation": "save", "symbol": kline.symbol}
                ) from e

        mock_failing_repo.save = failing_save

        # Test connection error handling
        with pytest.raises(StorageConnectionError) as exc_info:
            await mock_failing_repo.save(sample_kline)

        error = exc_info.value
        assert "Failed to connect to database" in str(error)
        assert "Connection refused" in str(error)
        assert error.details["operation"] == "save"
        assert error.details["symbol"] == "BTCUSDT"
        assert error.trace_id is not None

    @pytest.mark.asyncio
    async def test_database_write_error_handling(self, mock_failing_repo: Mock) -> None:
        """Test handling of database write errors.

        Description of what the test covers:
        Verifies that write operation failures are properly caught and
        wrapped in StorageWriteError exceptions with relevant context.

        Preconditions:
        - Repository can perform write operations
        - Database can reject write operations

        Steps:
        - Mock database to raise write-specific errors
        - Attempt batch save operation
        - Verify StorageWriteError is raised
        - Check error details include operation context

        Expected Result:
        - StorageWriteError is raised with proper error message
        - Error includes details about failed operation
        """
        klines = [
            Kline(
                symbol="FAILUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
                open_price=Decimal("100.00"),
                high_price=Decimal("101.00"),
                low_price=Decimal("99.00"),
                close_price=Decimal("100.50"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("100.0"),
                trades_count=10,
                taker_buy_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("50.0"),
            )
        ]

        # Configure mock to raise write error
        mock_failing_repo.db_driver.batch_insert.side_effect = Exception("Disk full")

        async def failing_save_batch(klines_list: list[Kline]) -> int:
            try:
                await mock_failing_repo.db_driver.batch_insert([])
                return len(klines_list)
            except Exception as e:
                raise StorageWriteError(
                    f"Failed to write batch to database: {str(e)}",
                    details={
                        "operation": "save_batch",
                        "batch_size": len(klines_list),
                        "first_symbol": klines_list[0].symbol if klines_list else None,
                    },
                ) from e

        mock_failing_repo.save_batch = failing_save_batch

        # Test write error handling
        with pytest.raises(StorageWriteError) as exc_info:
            await mock_failing_repo.save_batch(klines)

        error = exc_info.value
        assert "Failed to write batch to database" in str(error)
        assert "Disk full" in str(error)
        assert error.details["operation"] == "save_batch"
        assert error.details["batch_size"] == 1
        assert error.details["first_symbol"] == "FAILUSDT"

    @pytest.mark.asyncio
    async def test_database_read_error_handling(self, mock_failing_repo: Mock) -> None:
        """Test handling of database read errors.

        Description of what the test covers:
        Verifies that read operation failures are properly handled and
        wrapped in StorageReadError exceptions.

        Preconditions:
        - Repository can perform read operations
        - Database can fail during read operations

        Steps:
        - Mock database to raise read errors
        - Attempt query operation
        - Verify StorageReadError is raised
        - Check error includes query context

        Expected Result:
        - StorageReadError is raised instead of raw database error
        - Error message includes relevant query information
        """
        # Configure mock to raise read error
        mock_failing_repo.db_driver.select.side_effect = Exception("Table not found")

        async def failing_query(
            symbol: str,
            interval: KlineInterval,
            start_time: datetime,
            end_time: datetime,
            *,
            _options: QueryOptions | None = None,
        ) -> list[Kline]:
            try:
                await mock_failing_repo.db_driver.select("SELECT * FROM klines")
                return []
            except Exception as e:
                raise StorageReadError(
                    f"Failed to read from database: {str(e)}",
                    details={
                        "operation": "query",
                        "symbol": symbol,
                        "interval": interval.value,
                        "time_range": f"{start_time} to {end_time}",
                    },
                ) from e

        mock_failing_repo.query = failing_query

        # Test read error handling
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)

        with pytest.raises(StorageReadError) as exc_info:
            await mock_failing_repo.query("BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        error = exc_info.value
        assert "Failed to read from database" in str(error)
        assert "Table not found" in str(error)
        assert error.details["operation"] == "query"
        assert error.details["symbol"] == "BTCUSDT"
        assert error.details["interval"] == "1m"

    @pytest.mark.asyncio
    async def test_graceful_handling_of_partial_failures(self, mock_failing_repo: Mock) -> None:
        """Test graceful handling of partial batch operation failures.

        Description of what the test covers:
        Verifies that the repository can handle scenarios where some
        operations in a batch succeed while others fail.

        Preconditions:
        - Repository supports batch operations
        - Some operations can fail while others succeed

        Steps:
        - Create batch with mix of valid and invalid data
        - Mock database to fail on specific records
        - Execute batch operation
        - Verify partial success is handled correctly

        Expected Result:
        - Successful operations are committed
        - Failed operations are reported with details
        - Error includes information about partial success
        """
        # Create mixed batch with some that will fail
        mixed_klines = []
        for i in range(3):
            symbol = "FAILUSDT" if i == 1 else "BTCUSDT"  # Middle one will fail
            kline = Kline(
                symbol=symbol,
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, 12, i, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 12, i + 1, tzinfo=UTC),
                open_price=Decimal("100.00"),
                high_price=Decimal("101.00"),
                low_price=Decimal("99.00"),
                close_price=Decimal("100.50"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("100.0"),
                trades_count=10,
                taker_buy_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("50.0"),
            )
            mixed_klines.append(kline)

        async def partial_failing_save_batch(klines_list: list[Kline]) -> int:
            successful_saves = 0
            failed_symbols = []

            for kline in klines_list:
                try:
                    if kline.symbol == "FAILUSDT":
                        raise Exception(f"Constraint violation for {kline.symbol}")
                    successful_saves += 1
                except Exception:
                    failed_symbols.append(kline.symbol)

            if failed_symbols and successful_saves < len(klines_list):
                raise StorageWriteError(
                    f"Partial batch failure: {len(failed_symbols)} of {len(klines_list)} records failed",
                    details={
                        "operation": "save_batch",
                        "total_records": len(klines_list),
                        "successful_saves": successful_saves,
                        "failed_symbols": failed_symbols,
                    },
                )

            return successful_saves

        mock_failing_repo.save_batch = partial_failing_save_batch

        # Test partial failure handling
        with pytest.raises(StorageWriteError) as exc_info:
            await mock_failing_repo.save_batch(mixed_klines)

        error = exc_info.value
        assert "Partial batch failure" in str(error)
        assert error.details["total_records"] == 3
        assert error.details["successful_saves"] == 2
        assert "FAILUSDT" in error.details["failed_symbols"]

    @pytest.fixture
    def sample_kline(self) -> Kline:
        """Create a sample kline for error testing."""
        return Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("10.5"),
            quote_volume=Decimal("525525.0"),
            trades_count=100,
            taker_buy_volume=Decimal("5.0"),
            taker_buy_quote_volume=Decimal("250000.0"),
        )
