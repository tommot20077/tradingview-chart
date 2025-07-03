# ABOUTME: Unit tests for the abstract kline repository interface
# ABOUTME: Validates Kline repository contract compliance, query operations and data streaming

from abc import ABC
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asset_core.exceptions.core import StorageReadError
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
