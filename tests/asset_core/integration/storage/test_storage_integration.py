# ABOUTME: This file contains integration tests for the storage module repositories.
# ABOUTME: It tests interactions between kline and metadata repositories and end-to-end workflows.

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asset_core.exceptions.core import StorageError
from asset_core.models.kline import Kline, KlineInterval
from asset_core.storage.kline_repo import AbstractKlineRepository, QueryOptions
from asset_core.storage.metadata_repo import AbstractMetadataRepository


class IntegratedMockKlineRepository(AbstractKlineRepository):
    """Mock kline repository for integration testing with metadata coordination."""

    def __init__(self, metadata_repo: AbstractMetadataRepository) -> None:
        """Initialize with a metadata repository for coordination."""
        self.klines: list[Kline] = []
        self.metadata_repo = metadata_repo
        self.closed = False

    async def save(self, kline: Kline) -> None:
        """Save a single kline and update metadata."""
        if self.closed:
            raise StorageError("Repository is closed")

        # Simulate idempotent behavior
        self.klines = [
            k
            for k in self.klines
            if not (k.symbol == kline.symbol and k.interval == kline.interval and k.open_time == kline.open_time)
        ]
        self.klines.append(kline)

        # Update metadata about last saved kline
        await self.metadata_repo.set_last_sync_time(kline.symbol, f"klines_{kline.interval}", kline.open_time)

    async def save_batch(self, klines: list[Kline]) -> int:
        """Save batch and update metadata."""
        if self.closed:
            raise StorageError("Repository is closed")

        saved_count = 0
        latest_times: dict[tuple[str, str], datetime] = {}

        for kline in klines:
            await self.save(kline)
            saved_count += 1

            # Track latest time per symbol/interval
            key = (kline.symbol, kline.interval)
            if key not in latest_times or kline.open_time > latest_times[key]:
                latest_times[key] = kline.open_time

        # Update batch metadata
        for (symbol, interval_str), latest_time in latest_times.items():
            await self.metadata_repo.set_backfill_status(
                symbol,
                f"klines_{interval_str}",
                {
                    "last_batch_time": latest_time.isoformat(),
                    "last_batch_size": len([k for k in klines if k.symbol == symbol and k.interval == interval_str]),
                    "total_processed": saved_count,
                },
            )

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
        """Query with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        # Track query statistics
        query_key = f"query_stats:{symbol}:{interval.value}"
        existing_stats = await self.metadata_repo.get(query_key) or {}
        query_count = existing_stats.get("count", 0) + 1

        await self.metadata_repo.set(
            query_key,
            {
                "count": query_count,
                "last_query_time": datetime.now(UTC).isoformat(),
                "last_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            },
        )

        # Basic filtering
        filtered_klines = [
            k
            for k in self.klines
            if k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time
        ]

        # Apply options if provided
        if options:
            if options.order_by == "open_time":
                filtered_klines.sort(key=lambda k: k.open_time, reverse=options.order_desc)

            if options.offset:
                filtered_klines = filtered_klines[options.offset :]
            if options.limit:
                filtered_klines = filtered_klines[: options.limit]

        return filtered_klines

    def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,
    ) -> AsyncIterator[Kline]:
        """Stream with metadata tracking."""

        async def _stream() -> AsyncIterator[Kline]:
            if self.closed:
                raise StorageError("Repository is closed")

            # Track streaming session
            stream_key = f"stream_stats:{symbol}:{interval.value}"
            await self.metadata_repo.set(
                stream_key,
                {
                    "session_start": datetime.now(UTC).isoformat(),
                    "batch_size": batch_size,
                    "range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                },
            )

            matching_klines = [
                k
                for k in self.klines
                if k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time
            ]

            streamed_count = 0
            for i in range(0, len(matching_klines), batch_size):
                batch = matching_klines[i : i + batch_size]
                for kline in batch:
                    streamed_count += 1
                    yield kline

            # Update completion stats
            await self.metadata_repo.set(
                stream_key,
                {
                    "session_start": (await self.metadata_repo.get(stream_key) or {}).get("session_start"),
                    "session_end": datetime.now(UTC).isoformat(),
                    "batch_size": batch_size,
                    "total_streamed": streamed_count,
                    "range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                },
            )

        return _stream()

    async def get_latest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Get latest with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        matching_klines = [k for k in self.klines if k.symbol == symbol and k.interval == interval]

        if not matching_klines:
            return None

        latest = max(matching_klines, key=lambda k: k.open_time)

        # Update latest access metadata
        await self.metadata_repo.set(
            f"latest_access:{symbol}:{interval.value}",
            {"access_time": datetime.now(UTC).isoformat(), "latest_kline_time": latest.open_time.isoformat()},
        )

        return latest

    async def get_oldest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Get oldest with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        matching_klines = [k for k in self.klines if k.symbol == symbol and k.interval == interval]

        if not matching_klines:
            return None

        oldest = min(matching_klines, key=lambda k: k.open_time)

        # Update oldest access metadata
        await self.metadata_repo.set(
            f"oldest_access:{symbol}:{interval.value}",
            {"access_time": datetime.now(UTC).isoformat(), "oldest_kline_time": oldest.open_time.isoformat()},
        )

        return oldest

    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        matching_klines = [k for k in self.klines if k.symbol == symbol and k.interval == interval]

        if start_time is not None:
            matching_klines = [k for k in matching_klines if k.open_time >= start_time]
        if end_time is not None:
            matching_klines = [k for k in matching_klines if k.open_time < end_time]

        count = len(matching_klines)

        # Update count statistics
        count_key = f"count_stats:{symbol}:{interval.value}"
        existing_stats = await self.metadata_repo.get(count_key) or {}

        await self.metadata_repo.set(
            count_key,
            {
                "last_count": count,
                "last_count_time": datetime.now(UTC).isoformat(),
                "total_count_queries": existing_stats.get("total_count_queries", 0) + 1,
            },
        )

        return count

    async def delete(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        original_count = len(self.klines)
        self.klines = [
            k
            for k in self.klines
            if not (k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time)
        ]
        deleted_count = original_count - len(self.klines)

        # Track deletion
        if deleted_count > 0:
            await self.metadata_repo.set(
                f"deletion_log:{symbol}:{interval.value}",
                {
                    "deleted_count": deleted_count,
                    "deletion_time": datetime.now(UTC).isoformat(),
                    "range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                },
            )

        return deleted_count

    async def get_gaps(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Get gaps with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        matching_klines = [
            k
            for k in self.klines
            if k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time
        ]
        matching_klines.sort(key=lambda k: k.open_time)

        gaps = []
        interval_seconds = KlineInterval.to_seconds(interval)
        current_expected = start_time

        for kline in matching_klines:
            if kline.open_time > current_expected:
                gaps.append((current_expected, kline.open_time))
            current_expected = kline.open_time + timedelta(seconds=interval_seconds)

        if current_expected < end_time:
            gaps.append((current_expected, end_time))

        # Track gap analysis
        await self.metadata_repo.set(
            f"gap_analysis:{symbol}:{interval.value}",
            {
                "analysis_time": datetime.now(UTC).isoformat(),
                "gaps_found": len(gaps),
                "range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            },
        )

        return gaps

    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get statistics with metadata tracking."""
        if self.closed:
            raise StorageError("Repository is closed")

        matching_klines = [k for k in self.klines if k.symbol == symbol and k.interval == interval]

        if start_time is not None:
            matching_klines = [k for k in matching_klines if k.open_time >= start_time]
        if end_time is not None:
            matching_klines = [k for k in matching_klines if k.open_time < end_time]

        if not matching_klines:
            stats: dict[str, Any] = {
                "count": 0,
                "earliest": None,
                "latest": None,
                "avg_volume": None,
            }
        else:
            total_volume = sum(k.volume for k in matching_klines)
            stats = {
                "count": len(matching_klines),
                "earliest": min(k.open_time for k in matching_klines).isoformat(),
                "latest": max(k.open_time for k in matching_klines).isoformat(),
                "avg_volume": float(total_volume / len(matching_klines)),
            }

        # Track statistics requests
        await self.metadata_repo.set(
            f"stats_requests:{symbol}:{interval.value}",
            {
                "request_time": datetime.now(UTC).isoformat(),
                "stats_generated": stats.copy() if (stats["count"] or 0) > 0 else {"empty": True},
            },
        )

        return stats

    async def close(self) -> None:
        """Close the repository."""
        self.closed = True


class MockMetadataRepository(AbstractMetadataRepository):
    """Simple mock metadata repository for integration testing."""

    def __init__(self) -> None:
        """Initialize the mock repository."""
        self.data: dict[str, dict[str, Any]] = {}
        self.closed = False

    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Set a key-value pair."""
        if self.closed:
            raise StorageError("Repository is closed")
        self.data[key] = value.copy()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a value by key."""
        if self.closed:
            raise StorageError("Repository is closed")
        return self.data.get(key, {}).copy()

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if self.closed:
            raise StorageError("Repository is closed")
        return key in self.data

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if self.closed:
            raise StorageError("Repository is closed")
        if key in self.data:
            del self.data[key]
            return True
        return False

    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        if self.closed:
            raise StorageError("Repository is closed")
        keys = list(self.data.keys())
        if prefix is not None:
            keys = [key for key in keys if key.startswith(prefix)]
        return sorted(keys)

    async def set_with_ttl(self, key: str, value: dict[str, Any], _ttl_seconds: int) -> None:
        """Set with TTL (simplified for integration tests)."""
        if self.closed:
            raise StorageError("Repository is closed")
        await self.set(key, value)

    async def get_last_sync_time(self, symbol: str, data_type: str) -> datetime | None:
        """Get last sync time."""
        if self.closed:
            raise StorageError("Repository is closed")
        key = f"sync_time:{symbol}:{data_type}"
        data = await self.get(key)
        if data is None or "timestamp" not in data:
            return None
        return datetime.fromisoformat(data["timestamp"])

    async def set_last_sync_time(self, symbol: str, data_type: str, timestamp: datetime) -> None:
        """Set last sync time."""
        if self.closed:
            raise StorageError("Repository is closed")
        key = f"sync_time:{symbol}:{data_type}"
        await self.set(key, {"timestamp": timestamp.isoformat()})

    async def get_backfill_status(self, symbol: str, data_type: str) -> dict[str, Any] | None:
        """Get backfill status."""
        if self.closed:
            raise StorageError("Repository is closed")
        key = f"backfill_status:{symbol}:{data_type}"
        return await self.get(key)

    async def set_backfill_status(self, symbol: str, data_type: str, status: dict[str, Any]) -> None:
        """Set backfill status."""
        if self.closed:
            raise StorageError("Repository is closed")
        key = f"backfill_status:{symbol}:{data_type}"
        await self.set(key, status)

    async def close(self) -> None:
        """Close the repository."""
        self.closed = True


@pytest.mark.integration
class TestStorageIntegration:
    """Integration tests for storage repositories."""

    @pytest.fixture
    def metadata_repo(self) -> MockMetadataRepository:
        """Provides a metadata repository for testing."""
        return MockMetadataRepository()

    @pytest.fixture
    def kline_repo(self, metadata_repo: MockMetadataRepository) -> IntegratedMockKlineRepository:
        """Provides an integrated kline repository for testing."""
        return IntegratedMockKlineRepository(metadata_repo)

    @pytest.fixture
    def sample_klines(self) -> list[Kline]:
        """Provides sample klines for testing."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        klines = []

        for i in range(5):
            kline_time = base_time + timedelta(minutes=i)
            klines.append(
                Kline(
                    symbol="BTCUSDT",
                    interval=KlineInterval.MINUTE_1,
                    open_time=kline_time,
                    close_time=kline_time + timedelta(minutes=1),
                    open_price=Decimal(f"{50000 + i}.00"),
                    high_price=Decimal(f"{50100 + i}.00"),
                    low_price=Decimal(f"{49900 + i}.00"),
                    close_price=Decimal(f"{50050 + i}.00"),
                    volume=Decimal(1 + 0.1 * i),
                    quote_volume=Decimal("75000.00"),
                    trades_count=10 + i,
                )
            )

        return klines

    async def test_kline_save_updates_metadata(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that saving klines updates metadata.

        Description of what the test covers:
        Verifies that kline save operations automatically update related metadata.

        Preconditions:
        - Both repositories are initialized and functional.
        - Sample klines are available.

        Steps:
        - Save a single kline.
        - Verify sync time metadata is updated.
        - Save a batch of klines.
        - Verify backfill status metadata is updated.

        Expected Result:
        - Metadata is automatically updated when klines are saved.
        """
        kline = sample_klines[0]

        # Save single kline
        await kline_repo.save(kline)

        # Check sync time was updated
        sync_time = await metadata_repo.get_last_sync_time("BTCUSDT", "klines_1m")
        assert sync_time is not None
        assert sync_time == kline.open_time

        # Save batch
        await kline_repo.save_batch(sample_klines[1:])

        # Check backfill status was updated
        backfill_status = await metadata_repo.get_backfill_status("BTCUSDT", "klines_1m")
        assert backfill_status is not None
        assert "last_batch_time" in backfill_status
        assert "last_batch_size" in backfill_status
        assert backfill_status["last_batch_size"] == 4

    async def test_query_tracks_statistics(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that queries track statistics in metadata.

        Description of what the test covers:
        Verifies that query operations track usage statistics in metadata.

        Preconditions:
        - Repositories are integrated and functional.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Perform multiple queries.
        - Check that query statistics are tracked.

        Expected Result:
        - Query statistics are tracked in metadata repository.
        """
        await kline_repo.save_batch(sample_klines)

        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Perform multiple queries
        for _i in range(3):
            await kline_repo.query("BTCUSDT", KlineInterval.MINUTE_1, base_time, base_time + timedelta(minutes=10))

        # Check query statistics
        query_stats = await metadata_repo.get("query_stats:BTCUSDT:1m")
        assert query_stats is not None
        assert query_stats.get("count") == 3
        assert "last_query_time" in query_stats
        assert "last_range" in query_stats

    async def test_streaming_session_tracking(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that streaming sessions are tracked in metadata.

        Description of what the test covers:
        Verifies that streaming operations track session information.

        Preconditions:
        - Repositories support streaming with metadata tracking.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Stream klines and collect all results.
        - Check that streaming session was tracked.

        Expected Result:
        - Streaming session metadata is recorded.
        """
        await kline_repo.save_batch(sample_klines)

        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Stream klines
        streamed_klines = []
        async for kline in kline_repo.stream(
            "BTCUSDT", KlineInterval.MINUTE_1, base_time, base_time + timedelta(minutes=10), batch_size=2
        ):
            streamed_klines.append(kline)

        # Check streaming statistics
        stream_stats = await metadata_repo.get("stream_stats:BTCUSDT:1m")
        assert stream_stats is not None
        assert "session_start" in stream_stats
        assert "session_end" in stream_stats
        assert stream_stats["batch_size"] == 2
        assert stream_stats["total_streamed"] == 5

    async def test_access_pattern_tracking(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that access patterns are tracked.

        Description of what the test covers:
        Verifies that latest/oldest access operations are tracked in metadata.

        Preconditions:
        - Repositories support access pattern tracking.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Access latest and oldest klines.
        - Check that access metadata is recorded.

        Expected Result:
        - Access patterns are tracked in metadata.
        """
        await kline_repo.save_batch(sample_klines)

        # Access latest and oldest
        latest = await kline_repo.get_latest("BTCUSDT", KlineInterval.MINUTE_1)
        oldest = await kline_repo.get_oldest("BTCUSDT", KlineInterval.MINUTE_1)

        assert latest is not None
        assert oldest is not None

        # Check access metadata
        latest_access = await metadata_repo.get("latest_access:BTCUSDT:1m")
        oldest_access = await metadata_repo.get("oldest_access:BTCUSDT:1m")

        assert latest_access is not None
        assert oldest_access is not None
        assert "access_time" in latest_access
        assert "access_time" in oldest_access
        assert "latest_kline_time" in latest_access
        assert "oldest_kline_time" in oldest_access

    async def test_count_operations_tracking(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that count operations are tracked.

        Description of what the test covers:
        Verifies that count operations track statistics in metadata.

        Preconditions:
        - Repositories support count operation tracking.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Perform multiple count operations.
        - Check that count statistics are tracked.

        Expected Result:
        - Count operation statistics are tracked.
        """
        await kline_repo.save_batch(sample_klines)

        # Perform multiple count operations
        for _ in range(2):
            count = await kline_repo.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert count == 5

        # Check count statistics
        count_stats = await metadata_repo.get("count_stats:BTCUSDT:1m")
        assert count_stats is not None
        assert count_stats["last_count"] == 5
        assert count_stats["total_count_queries"] == 2
        assert "last_count_time" in count_stats

    async def test_deletion_logging(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that deletions are logged in metadata.

        Description of what the test covers:
        Verifies that delete operations are logged with details.

        Preconditions:
        - Repositories support deletion logging.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Delete some klines.
        - Check that deletion is logged.

        Expected Result:
        - Deletion details are logged in metadata.
        """
        await kline_repo.save_batch(sample_klines)

        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Delete some klines
        deleted_count = await kline_repo.delete(
            "BTCUSDT", KlineInterval.MINUTE_1, base_time + timedelta(minutes=1), base_time + timedelta(minutes=4)
        )

        assert deleted_count == 3

        # Check deletion log
        deletion_log = await metadata_repo.get("deletion_log:BTCUSDT:1m")
        assert deletion_log is not None
        assert deletion_log["deleted_count"] == 3
        assert "deletion_time" in deletion_log
        assert "range" in deletion_log

    async def test_gap_analysis_tracking(
        self, kline_repo: IntegratedMockKlineRepository, metadata_repo: MockMetadataRepository
    ) -> None:
        """Test that gap analysis is tracked.

        Description of what the test covers:
        Verifies that gap analysis operations are tracked in metadata.

        Preconditions:
        - Repositories support gap analysis tracking.
        - Data with gaps is available.

        Steps:
        - Save klines with gaps.
        - Perform gap analysis.
        - Check that analysis is tracked.

        Expected Result:
        - Gap analysis details are tracked in metadata.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create klines with gaps
        klines_with_gaps = []
        for i in [0, 2, 4]:  # Missing minutes 1 and 3
            kline_time = base_time + timedelta(minutes=i)
            klines_with_gaps.append(
                Kline(
                    symbol="BTCUSDT",
                    interval=KlineInterval.MINUTE_1,
                    open_time=kline_time,
                    close_time=kline_time + timedelta(minutes=1),
                    open_price=Decimal("50000.00"),
                    high_price=Decimal("50100.00"),
                    low_price=Decimal("49900.00"),
                    close_price=Decimal("50050.00"),
                    volume=Decimal("1.0"),
                    quote_volume=Decimal("75000.00"),
                    trades_count=10,
                )
            )

        await kline_repo.save_batch(klines_with_gaps)

        # Analyze gaps
        gaps = await kline_repo.get_gaps("BTCUSDT", KlineInterval.MINUTE_1, base_time, base_time + timedelta(minutes=6))

        assert len(gaps) == 3  # Gaps at minutes 1-2, 3-4, and 5-6

        # Check gap analysis tracking
        gap_analysis = await metadata_repo.get("gap_analysis:BTCUSDT:1m")
        assert gap_analysis is not None
        assert gap_analysis["gaps_found"] == 3
        assert "analysis_time" in gap_analysis
        assert "range" in gap_analysis

    async def test_statistics_request_tracking(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test that statistics requests are tracked.

        Description of what the test covers:
        Verifies that statistics generation is tracked in metadata.

        Preconditions:
        - Repositories support statistics tracking.
        - Sample data is available.

        Steps:
        - Save sample klines.
        - Generate statistics.
        - Check that request is tracked.

        Expected Result:
        - Statistics request details are tracked.
        """
        await kline_repo.save_batch(sample_klines)

        # Generate statistics
        stats = await kline_repo.get_statistics("BTCUSDT", KlineInterval.MINUTE_1)

        assert stats["count"] == 5
        assert stats["avg_volume"] is not None

        # Check statistics request tracking
        stats_requests = await metadata_repo.get("stats_requests:BTCUSDT:1m")
        assert stats_requests is not None
        assert "request_time" in stats_requests
        assert "stats_generated" in stats_requests

    async def test_concurrent_operations_metadata_consistency(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test metadata consistency under concurrent operations.

        Description of what the test covers:
        Verifies that metadata remains consistent when multiple operations
        are performed concurrently.

        Preconditions:
        - Repositories support concurrent operations.
        - Sample data is available.

        Steps:
        - Perform concurrent save and query operations.
        - Check that metadata is consistent.

        Expected Result:
        - Metadata remains consistent despite concurrent operations.
        """
        # Perform concurrent operations
        tasks = []

        # Concurrent saves
        for kline in sample_klines[:3]:
            tasks.append(kline_repo.save(kline))

        # Concurrent queries
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        async def query_task() -> None:
            await kline_repo.query("BTCUSDT", KlineInterval.MINUTE_1, base_time, base_time + timedelta(minutes=10))

        for _ in range(2):
            tasks.append(query_task())

        # Execute all tasks concurrently
        await asyncio.gather(*tasks)

        # Check that metadata is consistent
        sync_time = await metadata_repo.get_last_sync_time("BTCUSDT", "klines_1m")
        query_stats = await metadata_repo.get("query_stats:BTCUSDT:1m")

        assert sync_time is not None
        assert query_stats is not None
        assert query_stats["count"] == 2

    async def test_repository_lifecycle_coordination(self, metadata_repo: MockMetadataRepository) -> None:
        """Test repository lifecycle coordination.

        Description of what the test covers:
        Verifies that repositories can be managed together through their lifecycle.

        Preconditions:
        - Repositories support lifecycle management.

        Steps:
        - Create integrated repositories.
        - Use them in context managers.
        - Verify both are properly closed.

        Expected Result:
        - Both repositories are properly managed through their lifecycle.
        """
        kline_repo = IntegratedMockKlineRepository(metadata_repo)

        async with metadata_repo, kline_repo:
            # Verify both are open
            assert not metadata_repo.closed
            assert not kline_repo.closed

            # Perform some operations
            await metadata_repo.set("test", {"value": 1})
            assert await metadata_repo.exists("test")

        # Verify both are closed
        assert metadata_repo.closed
        assert kline_repo.closed  # type: ignore[unreachable]

    async def test_metadata_driven_kline_operations(
        self,
        kline_repo: IntegratedMockKlineRepository,
        metadata_repo: MockMetadataRepository,
        sample_klines: list[Kline],
    ) -> None:
        """Test kline operations driven by metadata.

        Description of what the test covers:
        Verifies that kline operations can be influenced by metadata state.

        Preconditions:
        - Repositories support metadata-driven operations.
        - Sample data is available.

        Steps:
        - Set metadata that could influence operations.
        - Perform kline operations.
        - Verify operations respect metadata state.

        Expected Result:
        - Kline operations are properly influenced by metadata.
        """
        # Save some klines
        await kline_repo.save_batch(sample_klines[:3])

        # Check initial sync time
        initial_sync_time = await metadata_repo.get_last_sync_time("BTCUSDT", "klines_1m")
        assert initial_sync_time is not None

        # Save more klines
        await kline_repo.save_batch(sample_klines[3:])

        # Check that sync time was updated
        updated_sync_time = await metadata_repo.get_last_sync_time("BTCUSDT", "klines_1m")
        assert updated_sync_time is not None
        assert updated_sync_time > initial_sync_time

        # Check that backfill status reflects the latest batch
        backfill_status = await metadata_repo.get_backfill_status("BTCUSDT", "klines_1m")
        assert backfill_status is not None
        assert backfill_status["last_batch_size"] == 2
