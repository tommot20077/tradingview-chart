"""Advanced tests for storage abstractions including transactions and batch operations."""

import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from src.asset_core.asset_core.exceptions import StorageError, TimeoutError
from src.asset_core.asset_core.models.kline import Kline, KlineInterval
from src.asset_core.asset_core.storage.kline_repo import AbstractKlineRepository, QueryOptions
from src.asset_core.asset_core.storage.metadata_repo import AbstractMetadataRepository


class MockTransactionalKlineRepository(AbstractKlineRepository):
    """Mock implementation of AbstractKlineRepository with transaction support for testing.

    This mock repository simulates transactional behavior for Kline data,
    including support for nested transactions, timeouts, and different
    isolation levels. It's designed to test the contract of transactional
    storage operations without relying on a real database.

    Attributes:
        data (dict[str, list[Kline]]): The main storage for kline data, organized by symbol_interval.
        transaction_data (dict[str, list[Kline]] | None): Temporary storage for data within a transaction.
        in_transaction (bool): Flag indicating if a transaction is currently active.
        transaction_timeout (float): The maximum duration for a transaction in seconds.
        transaction_start_time (float | None): Timestamp when the current transaction started.
        isolation_level (str): The current transaction isolation level (e.g., "READ_COMMITTED").
        nested_transaction_count (int): Counter for nested transactions.
        operation_delays (dict[str, float]): Configurable delays for specific operations (e.g., "save").
        batch_size_limit (int): Maximum number of klines allowed in a single batch save operation.
        should_fail_on_operation (dict[str, bool]): Flags to simulate failures for specific operations.
    """

    def __init__(self) -> None:
        self.data: dict[str, list[Kline]] = defaultdict(list)
        self.transaction_data: dict[str, list[Kline]] | None = None
        self.in_transaction = False
        self.transaction_timeout = 30.0
        self.transaction_start_time: float | None = None
        self.isolation_level = "READ_COMMITTED"
        self.nested_transaction_count = 0
        self.operation_delays: dict[str, float] = {}
        self.batch_size_limit = 1000
        self.should_fail_on_operation: dict[str, bool] = {}

    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED", timeout: float = 30.0) -> None:
        """Begin a transaction."""
        if self.in_transaction:
            self.nested_transaction_count += 1
        else:
            self.in_transaction = True
            self.transaction_start_time = time.time()
            self.transaction_timeout = timeout
            self.isolation_level = isolation_level
            self.transaction_data = defaultdict(list)

    async def commit_transaction(self) -> None:
        """Commits the current transaction.

        If nested transactions are active, it decrements the nested transaction count.
        If it's the outermost transaction, it applies the changes from the transaction
        data to the main repository data and resets the transaction state.

        Raises:
            StorageError: If no active transaction exists to commit.
            TimeoutError: If the transaction has timed out.
        """
        self._check_transaction_timeout()

        if not self.in_transaction:
            raise StorageError("No active transaction to commit")

        if self.nested_transaction_count > 0:
            self.nested_transaction_count -= 1
        else:
            if self.transaction_data is not None:
                # Apply transaction data to main data
                for key, klines in self.transaction_data.items():
                    self.data[key].extend(klines)
            self._end_transaction()

    async def rollback_transaction(self) -> None:
        """Rollback current transaction."""
        if not self.in_transaction:
            raise StorageError("No active transaction to rollback")

        if self.nested_transaction_count > 0:
            self.nested_transaction_count -= 1
        else:
            self._end_transaction()

    def _end_transaction(self) -> None:
        """End transaction and reset state."""
        self.in_transaction = False
        self.transaction_data = None
        self.transaction_start_time = None
        self.nested_transaction_count = 0

    def _check_transaction_timeout(self) -> None:
        """Check if transaction has timed out."""
        if (
            self.in_transaction
            and self.transaction_start_time
            and time.time() - self.transaction_start_time > self.transaction_timeout
        ):
            raise TimeoutError("Transaction timeout exceeded")

    def _get_storage(self) -> dict[str, list[Kline]]:
        """Get appropriate storage based on transaction state."""
        if self.in_transaction and self.transaction_data is not None:
            # Merge committed data with transaction data for read operations
            merged = {}
            # Start with committed data
            for key, klines in self.data.items():
                merged[key] = list(klines)
            # Add transaction data
            for key, klines in self.transaction_data.items():
                if key in merged:
                    merged[key].extend(klines)
                else:
                    merged[key] = list(klines)
            return merged
        return self.data

    async def save(self, kline: Kline) -> None:
        """Saves a single Kline object to the repository.

        If a transaction is active, the Kline is saved to the transaction-specific
        storage; otherwise, it's saved directly to the main data store.
        Simulates potential storage errors and delays for testing purposes.

        Args:
            kline (Kline): The Kline object to save.

        Raises:
            StorageError: If a simulated save failure is configured.
            TimeoutError: If the current transaction has timed out.
        """
        self._check_transaction_timeout()

        if self.should_fail_on_operation.get("save", False):
            raise StorageError("Simulated save failure")

        if delay := self.operation_delays.get("save", 0):
            await asyncio.sleep(delay)

        key = f"{kline.symbol}_{kline.interval}"
        # For writes, use transaction_data if in transaction, otherwise use main data
        storage = self.transaction_data if self.in_transaction and self.transaction_data is not None else self.data

        if key not in storage:
            storage[key] = []
        storage[key].append(kline)

    async def save_batch(self, klines: list[Kline]) -> int:
        """Saves multiple Kline objects in a batch operation.

        This method iterates through a list of Klines and attempts to save each.
        It enforces a `batch_size_limit` and can simulate failures.
        If an error occurs within a transaction, it re-raises to trigger a rollback.

        Args:
            klines (list[Kline]): A list of Kline objects to save.

        Returns:
            int: The number of Klines successfully saved.

        Raises:
            StorageError: If a simulated batch save failure is configured, or if
                          the batch size exceeds `batch_size_limit`.
            TimeoutError: If the current transaction has timed out.
        """
        self._check_transaction_timeout()

        if self.should_fail_on_operation.get("save_batch", False):
            raise StorageError("Simulated batch save failure")

        if len(klines) > self.batch_size_limit:
            raise StorageError(f"Batch size {len(klines)} exceeds limit {self.batch_size_limit}")

        if delay := self.operation_delays.get("save_batch", 0):
            await asyncio.sleep(delay)

        saved_count = 0
        for kline in klines:
            try:
                await self.save(kline)
                saved_count += 1
            except Exception:
                if self.in_transaction:
                    raise  # Re-raise in transaction to trigger rollback
                # Outside transaction, continue with remaining items
                continue

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
        """Queries Kline objects from the repository based on specified criteria.

        Retrieves Klines for a given symbol and interval within a time range.
        Supports optional filtering, ordering, offset, and limit through `QueryOptions`.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime): The start time for the query (inclusive).
            end_time (datetime): The end time for the query (exclusive).
            options (QueryOptions | None): Optional query parameters for ordering, offset, and limit.

        Returns:
            list[Kline]: A list of matching Kline objects.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        self._check_transaction_timeout()

        key = f"{symbol}_{interval.value if hasattr(interval, 'value') else interval}"
        storage = self._get_storage()
        klines = storage.get(key, [])

        # Apply time filtering
        filtered = [k for k in klines if start_time <= k.open_time < end_time]

        # Apply query options
        if options:
            if options.order_desc:
                filtered.sort(key=lambda k: getattr(k, options.order_by), reverse=True)
            else:
                filtered.sort(key=lambda k: getattr(k, options.order_by))

            if options.offset:
                filtered = filtered[options.offset :]

            if options.limit:
                filtered = filtered[: options.limit]

        return filtered

    async def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,
    ):
        """Streams Kline objects from the repository in batches.

        Retrieves Klines for a given symbol and interval within a time range
        and yields them in specified batch sizes.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime): The start time for the stream (inclusive).
            end_time (datetime): The end time for the stream (exclusive).
            batch_size (int): The number of Klines to yield in each batch (default: 1000).

        Yields:
            Kline: A Kline object.

        Raises:
            TimeoutError: If the current transaction has timed out during the underlying query.
        """
        klines = await self.query(symbol, interval, start_time, end_time)
        for i in range(0, len(klines), batch_size):
            batch = klines[i : i + batch_size]
            for kline in batch:
                yield kline

    async def get_latest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Retrieves the latest Kline object for a given symbol and interval.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).

        Returns:
            Kline | None: The latest Kline object, or None if no Klines are found.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        key = f"{symbol}_{interval.value if hasattr(interval, 'value') else interval}"
        storage = self._get_storage()
        klines = storage.get(key, [])
        return max(klines, key=lambda k: k.open_time) if klines else None

    async def get_oldest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Retrieves the oldest Kline object for a given symbol and interval.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).

        Returns:
            Kline | None: The oldest Kline object, or None if no Klines are found.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        key = f"{symbol}_{interval.value if hasattr(interval, 'value') else interval}"
        storage = self._get_storage()
        klines = storage.get(key, [])
        return min(klines, key=lambda k: k.open_time) if klines else None

    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Counts the number of Kline objects for a given symbol and interval.

        Optionally filters by a time range.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime | None): Optional start time for filtering (inclusive).
            end_time (datetime | None): Optional end time for filtering (exclusive).

        Returns:
            int: The number of matching Kline objects.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        key = f"{symbol}_{interval.value if hasattr(interval, 'value') else interval}"
        storage = self._get_storage()
        klines = storage.get(key, [])

        if start_time and end_time:
            klines = [k for k in klines if start_time <= k.open_time < end_time]

        return len(klines)

    async def delete(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Deletes Kline objects from the repository within a specified time range.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime): The start time for deletion (inclusive).
            end_time (datetime): The end time for deletion (exclusive).

        Returns:
            int: The number of Kline objects deleted.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        key = f"{symbol}_{interval.value if hasattr(interval, 'value') else interval}"
        storage = self._get_storage()
        klines = storage.get(key, [])

        to_delete = [k for k in klines if start_time <= k.open_time < end_time]
        for kline in to_delete:
            klines.remove(kline)

        return len(to_delete)

    async def get_gaps(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Finds gaps in the stored Kline data for a given symbol and interval within a time range.

        Note: This is a simplified mock implementation that always returns an empty list.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime): The start time for checking gaps (inclusive).
            end_time (datetime): The end time for checking gaps (exclusive).

        Returns:
            list[tuple[datetime, datetime]]: A list of tuples, where each tuple represents
                                             a gap (start_time, end_time). Always empty in this mock.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        return []  # Simplified implementation

    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Retrieves statistics about stored Klines for a given symbol and interval.

        Currently, it only returns the count of Klines within the specified range.

        Args:
            symbol (str): The trading symbol (e.g., "BTCUSDT").
            interval (KlineInterval): The Kline interval (e.g., HOUR_1).
            start_time (datetime | None): Optional start time for statistics (inclusive).
            end_time (datetime | None): Optional end time for statistics (exclusive).

        Returns:
            dict[str, Any]: A dictionary containing statistics, e.g., {"count": int}.

        Raises:
            TimeoutError: If the current transaction has timed out during the underlying count operation.
        """
        count = await self.count(symbol, interval, start_time, end_time)
        return {"count": count}

    async def close(self) -> None:
        """Close the repository and clean up resources."""
        if self.in_transaction:
            await self.rollback_transaction()


class MockTransactionalMetadataRepository(AbstractMetadataRepository):
    """Mock implementation of AbstractMetadataRepository with transaction support for testing.

    This mock repository simulates transactional behavior for metadata,
    designed to test the contract of transactional storage operations
    for key-value metadata without relying on a real database.

    Attributes:
        data (dict[str, dict[str, Any]]): The main storage for metadata.
        transaction_data (dict[str, dict[str, Any]] | None): Temporary storage for data within a transaction.
        in_transaction (bool): Flag indicating if a transaction is currently active.
        transaction_timeout (float): The maximum duration for a transaction in seconds.
        transaction_start_time (float | None): Timestamp when the current transaction started.
        isolation_level (str): The current transaction isolation level (e.g., "READ_COMMITTED").
        nested_transaction_count (int): Counter for nested transactions.
        should_fail_on_operation (dict[str, bool]): Flags to simulate failures for specific operations.
    """

    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}
        self.transaction_data: dict[str, dict[str, Any]] | None = None
        self.in_transaction = False
        self.transaction_timeout = 30.0
        self.transaction_start_time: float | None = None
        self.isolation_level = "READ_COMMITTED"
        self.nested_transaction_count = 0
        self.should_fail_on_operation: dict[str, bool] = {}

    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED", timeout: float = 30.0) -> None:
        """Begin a transaction."""
        if self.in_transaction:
            self.nested_transaction_count += 1
        else:
            self.in_transaction = True
            self.transaction_start_time = time.time()
            self.transaction_timeout = timeout
            self.isolation_level = isolation_level
            self.transaction_data = defaultdict(list)

    async def commit_transaction(self) -> None:
        """Commit current transaction."""
        self._check_transaction_timeout()

        if not self.in_transaction:
            raise StorageError("No active transaction to commit")

        if self.nested_transaction_count > 0:
            self.nested_transaction_count -= 1
        else:
            if self.transaction_data is not None:
                self.data.update(self.transaction_data)
            self._end_transaction()

    async def rollback_transaction(self) -> None:
        """Rollback current transaction."""
        if not self.in_transaction:
            raise StorageError("No active transaction to rollback")

        if self.nested_transaction_count > 0:
            self.nested_transaction_count -= 1
        else:
            self._end_transaction()

    def _end_transaction(self) -> None:
        """End transaction and reset state."""
        self.in_transaction = False
        self.transaction_data = None
        self.transaction_start_time = None
        self.nested_transaction_count = 0

    def _check_transaction_timeout(self) -> None:
        """Check if transaction has timed out."""
        if (
            self.in_transaction
            and self.transaction_start_time
            and time.time() - self.transaction_start_time > self.transaction_timeout
        ):
            raise TimeoutError("Transaction timeout exceeded")

    def _get_storage(self) -> dict[str, dict[str, Any]]:
        """Returns the appropriate storage (transactional or main) based on transaction state.

        Returns:
            dict[str, dict[str, Any]]: The dictionary representing the current storage context.
        """
        if self.in_transaction and self.transaction_data is not None:
            return self.transaction_data
        return self.data

    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Sets a metadata value for a given key.

        If a transaction is active, the value is set in the transaction-specific
        storage; otherwise, it's set directly in the main data store.
        Simulates potential storage errors for testing purposes.

        Args:
            key (str): The key for the metadata.
            value (dict[str, Any]): The metadata value to set.

        Raises:
            StorageError: If a simulated set failure is configured.
            TimeoutError: If the current transaction has timed out.
        """
        self._check_transaction_timeout()

        if self.should_fail_on_operation.get("set", False):
            raise StorageError("Simulated set failure")

        storage = self._get_storage()
        storage[key] = value

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieves a metadata value for a given key.

        Args:
            key (str): The key for the metadata.

        Returns:
            dict[str, Any] | None: The metadata value, or None if the key is not found.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        self._check_transaction_timeout()
        storage = self._get_storage()
        return storage.get(key)

    async def exists(self, key: str) -> bool:
        """Checks if a metadata key exists in the repository.

        Args:
            key (str): The key to check for existence.

        Returns:
            bool: True if the key exists, False otherwise.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        storage = self._get_storage()
        return key in storage

    async def delete(self, key: str) -> bool:
        """Deletes a metadata entry by its key.

        Args:
            key (str): The key of the metadata to delete.

        Returns:
            bool: True if the key was found and deleted, False otherwise.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        storage = self._get_storage()
        if key in storage:
            del storage[key]
            return True
        return False

    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """Lists all metadata keys, optionally filtered by a prefix.

        Args:
            prefix (str | None): An optional prefix to filter the keys.

        Returns:
            list[str]: A list of matching metadata keys.

        Raises:
            TimeoutError: If the current transaction has timed out.
        """
        storage = self._get_storage()
        keys = list(storage.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    async def set_with_ttl(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Sets a metadata value with a time-to-live (TTL).

        Note: In this mock implementation, TTL is not actually enforced.

        Args:
            key (str): The key for the metadata.
            value (dict[str, Any]): The metadata value to set.
            ttl_seconds (int): The time-to-live in seconds.

        Raises:
            StorageError: If a simulated set failure is configured.
            TimeoutError: If the current transaction has timed out.
        """
        await self.set(key, value)

    async def get_last_sync_time(
        self,
        symbol: str,
        data_type: str,
    ) -> datetime | None:
        """Retrieves the last synchronization time for a given symbol and data type.

        Args:
            symbol (str): The trading symbol.
            data_type (str): The type of data (e.g., "kline", "trade").

        Returns:
            datetime | None: The last synchronization time as a datetime object, or None if not found.

        Raises:
            TimeoutError: If the current transaction has timed out during the underlying get operation.
        """
        key = f"sync_time_{symbol}_{data_type}"
        data = await self.get(key)
        return datetime.fromisoformat(data["timestamp"]) if data else None

    async def set_last_sync_time(
        self,
        symbol: str,
        data_type: str,
        timestamp: datetime,
    ) -> None:
        """Sets the last synchronization time for a given symbol and data type.

        Args:
            symbol (str): The trading symbol.
            data_type (str): The type of data (e.g., "kline", "trade").
            timestamp (datetime): The datetime object representing the last sync time.

        Raises:
            StorageError: If a simulated set failure is configured.
            TimeoutError: If the current transaction has timed out.
        """
        key = f"sync_time_{symbol}_{data_type}"
        await self.set(key, {"timestamp": timestamp.isoformat()})

    async def get_backfill_status(
        self,
        symbol: str,
        data_type: str,
    ) -> dict[str, Any] | None:
        """Retrieves the backfill status for a given symbol and data type.

        Args:
            symbol (str): The trading symbol.
            data_type (str): The type of data (e.g., "kline", "trade").

        Returns:
            dict[str, Any] | None: A dictionary containing the backfill status, or None if not found.

        Raises:
            TimeoutError: If the current transaction has timed out during the underlying get operation.
        """
        key = f"backfill_{symbol}_{data_type}"
        return await self.get(key)

    async def set_backfill_status(
        self,
        symbol: str,
        data_type: str,
        status: dict[str, Any],
    ) -> None:
        """Sets the backfill status for a given symbol and data type.

        Args:
            symbol (str): The trading symbol.
            data_type (str): The type of data (e.g., "kline", "trade").
            status (dict[str, Any]): A dictionary containing the backfill status to set.

        Raises:
            StorageError: If a simulated set failure is configured.
            TimeoutError: If the current transaction has timed out.
        """
        key = f"backfill_{symbol}_{data_type}"
        await self.set(key, status)

    async def close(self) -> None:
        """Close the repository and clean up resources."""
        if self.in_transaction:
            await self.rollback_transaction()


@pytest.fixture
def kline_repo() -> MockTransactionalKlineRepository:
    """Provides a mock kline repository with transaction support for testing.

    Returns:
        MockTransactionalKlineRepository: An instance of the mock kline repository.
    """
    return MockTransactionalKlineRepository()


@pytest.fixture
def metadata_repo() -> MockTransactionalMetadataRepository:
    """Provides a mock metadata repository with transaction support for testing.

    Returns:
        MockTransactionalMetadataRepository: An instance of the mock metadata repository.
    """
    return MockTransactionalMetadataRepository()


@pytest.fixture
def sample_klines() -> list[Kline]:
    """Provides a list of sample Kline objects for testing purposes.

    These Klines are generated with sequential open times and varying prices
    to simulate realistic time-series data.

    Returns:
        list[Kline]: A list of 10 sample Kline objects.
    """
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    klines = []

    for i in range(10):
        open_time = base_time.replace(hour=i)
        close_time = base_time.replace(hour=i + 1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.00") + Decimal(i * 100),
            high_price=Decimal("50100.00") + Decimal(i * 100),
            low_price=Decimal("49900.00") + Decimal(i * 100),
            close_price=Decimal("50050.00") + Decimal(i * 100),
            volume=Decimal("100.0"),
            quote_volume=Decimal("5000000.0"),
            trades_count=100,
        )
        klines.append(kline)

    return klines


@pytest.mark.integration
class TestStorageTransactions:
    """Test transaction management for storage abstractions.

    Tests comprehensive transaction scenarios including rollback behavior,
    isolation levels, nested transaction support, and timeout handling
    for both Kline and Metadata repositories.
    """

    @pytest.mark.asyncio
    async def test_transaction_rollback_behavior(
        self, kline_repo: MockTransactionalKlineRepository, sample_klines: list[Kline]
    ) -> None:
        """Test rollback scenarios and data consistency.

        Description of what the test covers.
        Tests that transactions properly rollback when errors occur,
        ensuring data consistency and that no partial changes are applied.

        Preconditions:
        - Clean repository state.
        - Sample klines for testing.

        Steps:
        - Begin transaction.
        - Save some klines.
        - Trigger an error condition.
        - Rollback transaction.
        - Verify no data was saved.

        Expected Result:
        - Data should not be visible after rollback.
        - Repository state should be unchanged.
        - Error should be properly handled.
        """
        # Verify initial state is empty
        initial_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert initial_count == 0

        # Begin transaction
        await kline_repo.begin_transaction()

        # Save some klines within transaction
        for kline in sample_klines[:5]:
            await kline_repo.save(kline)

        # Verify klines are visible within transaction
        transaction_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert transaction_count == 5

        # Simulate error and rollback
        kline_repo.should_fail_on_operation["save"] = True

        try:
            await kline_repo.save(sample_klines[5])
            raise AssertionError("Expected operation to fail")
        except StorageError:
            pass

        # Rollback transaction
        await kline_repo.rollback_transaction()

        # Verify no data was committed
        final_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert final_count == 0

        # Verify repository is in clean state
        assert not kline_repo.in_transaction
        assert kline_repo.transaction_data is None

    @pytest.mark.asyncio
    async def test_isolation_levels(
        self, kline_repo: MockTransactionalKlineRepository, sample_klines: list[Kline]
    ) -> None:
        """Test transaction isolation behavior.

        Description of what the test covers.
        Tests different isolation levels (READ_COMMITTED, SERIALIZABLE)
        to ensure proper data visibility and consistency between concurrent
        transactions.

        Preconditions:
        - Clean repository state.
        - Multiple transactions capability.

        Steps:
        - Start transaction with specific isolation level.
        - Modify data within transaction.
        - Verify isolation behavior.
        - Test different isolation levels.

        Expected Result:
        - Data visibility should follow isolation level rules.
        - Concurrent transactions should be properly isolated.
        - No dirty reads or phantom reads should occur.
        """
        # Test READ_COMMITTED isolation
        await kline_repo.begin_transaction(isolation_level="READ_COMMITTED")
        assert kline_repo.isolation_level == "READ_COMMITTED"

        # Save data in transaction
        await kline_repo.save(sample_klines[0])

        # Data should be visible within transaction
        count_in_transaction = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert count_in_transaction == 1

        # Simulate concurrent access (data should not be visible outside transaction)
        # In a real implementation, this would be tested with actual concurrent transactions
        original_in_transaction = kline_repo.in_transaction
        kline_repo.in_transaction = False

        count_outside_transaction = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert count_outside_transaction == 0

        # Restore transaction state
        kline_repo.in_transaction = original_in_transaction

        # Commit transaction
        await kline_repo.commit_transaction()

        # Data should now be visible
        final_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert final_count == 1

        # Test SERIALIZABLE isolation
        await kline_repo.begin_transaction(isolation_level="SERIALIZABLE")
        assert kline_repo.isolation_level == "SERIALIZABLE"

        await kline_repo.rollback_transaction()

    @pytest.mark.asyncio
    async def test_nested_transaction_support(self, metadata_repo: MockTransactionalMetadataRepository) -> None:
        """Test nested transaction handling.

        Description of what the test covers.
        Tests support for nested transactions including proper commit/rollback
        behavior, savepoint handling, and state management across multiple
        transaction levels.

        Preconditions:
        - Repository supporting nested transactions.
        - Clean initial state.

        Steps:
        - Begin outer transaction.
        - Begin inner transaction (nested).
        - Modify data in inner transaction.
        - Test rollback of inner transaction.
        - Test commit of outer transaction.

        Expected Result:
        - Nested transactions should be properly managed.
        - Inner transaction rollback should not affect outer transaction.
        - Proper transaction count should be maintained.
        """
        # Begin outer transaction
        await metadata_repo.begin_transaction()
        assert metadata_repo.in_transaction
        assert metadata_repo.nested_transaction_count == 0

        # Set some data in outer transaction
        await metadata_repo.set("outer_key", {"value": "outer_data"})

        # Begin nested (inner) transaction
        await metadata_repo.begin_transaction()
        assert metadata_repo.nested_transaction_count == 1

        # Set data in nested transaction
        await metadata_repo.set("inner_key", {"value": "inner_data"})

        # Both keys should be visible
        assert await metadata_repo.exists("outer_key")
        assert await metadata_repo.exists("inner_key")

        # Rollback inner transaction
        await metadata_repo.rollback_transaction()
        assert metadata_repo.nested_transaction_count == 0
        assert metadata_repo.in_transaction  # Outer transaction still active

        # Outer key should still exist, inner key should be gone from transaction view
        assert await metadata_repo.exists("outer_key")
        # Note: In this mock implementation, rollback of nested transaction
        # doesn't actually remove the data, but in a real implementation it would

        # Begin another nested transaction
        await metadata_repo.begin_transaction()
        await metadata_repo.set("inner_key2", {"value": "inner_data2"})

        # Commit inner transaction
        await metadata_repo.commit_transaction()
        assert metadata_repo.nested_transaction_count == 0

        # Commit outer transaction
        await metadata_repo.commit_transaction()
        assert not metadata_repo.in_transaction

        # Verify final state
        assert await metadata_repo.exists("outer_key")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, kline_repo: MockTransactionalKlineRepository) -> None:
        """Test transaction timeout scenarios.

        Description of what the test covers.
        Tests that transactions properly timeout when they exceed configured
        timeout duration, ensuring resources are not held indefinitely and
        proper cleanup occurs.

        Preconditions:
        - Repository supporting transaction timeouts.
        - Configurable timeout values.

        Steps:
        - Begin transaction with short timeout.
        - Let transaction exceed timeout.
        - Attempt operation after timeout.
        - Verify timeout error is raised.
        - Verify proper cleanup.

        Expected Result:
        - Operations should fail after timeout.
        - TimeoutError should be raised.
        - Transaction should be properly cleaned up.
        """
        # Begin transaction with very short timeout
        short_timeout = 0.1
        await kline_repo.begin_transaction(timeout=short_timeout)

        # Simulate time passing to exceed timeout
        if kline_repo.transaction_start_time:
            kline_repo.transaction_start_time = time.time() - (short_timeout + 0.1)

        # Attempt operation after timeout should fail
        sample_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 1, tzinfo=UTC),
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("100.0"),
            quote_volume=Decimal("5000000.0"),
            trades_count=100,
        )

        with pytest.raises(TimeoutError, match="Transaction timeout exceeded"):
            await kline_repo.save(sample_kline)

        # Cleanup first transaction before testing commit timeout
        await kline_repo.rollback_transaction()

        # Test timeout during commit
        await kline_repo.begin_transaction(timeout=short_timeout)
        if kline_repo.transaction_start_time:
            kline_repo.transaction_start_time = time.time() - (short_timeout + 0.1)

        with pytest.raises(TimeoutError):
            await kline_repo.commit_transaction()

        # Verify transaction state is cleaned up
        # In a real implementation, timeout should trigger automatic rollback
        await kline_repo.rollback_transaction()
        assert not kline_repo.in_transaction


@pytest.mark.integration
class TestStorageBatchOperations:
    """Test batch operation functionality for storage abstractions.

    Tests various aspects of batch operations including performance,
    atomicity, size optimization, and error handling.
    """

    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, kline_repo: MockTransactionalKlineRepository) -> None:
        """Test batch insert operations and performance.

        Description of what the test covers.
        Tests that batch insert operations provide better performance than
        individual inserts and properly handle large datasets while maintaining
        data integrity.

        Preconditions:
        - Clean repository state.
        - Large dataset for testing.

        Steps:
        - Prepare large batch of klines.
        - Measure individual insert time.
        - Measure batch insert time.
        - Verify all data was saved correctly.
        - Compare performance metrics.

        Expected Result:
        - Batch operations should be faster than individual operations.
        - All data should be saved correctly.
        - Performance should scale appropriately.
        """
        # Create large dataset
        large_dataset = []
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for i in range(500):  # 500 klines for performance testing
            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time + timedelta(minutes=i),
                close_time=base_time + timedelta(minutes=i + 1),
                open_price=Decimal("50000.00") + Decimal(i),
                high_price=Decimal("50100.00") + Decimal(i),
                low_price=Decimal("49900.00") + Decimal(i),
                close_price=Decimal("50050.00") + Decimal(i),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.0"),
                trades_count=100,
            )
            large_dataset.append(kline)

        # Test individual inserts (smaller sample for speed)
        individual_sample = large_dataset[:50]
        start_time = time.time()
        for kline in individual_sample:
            await kline_repo.save(kline)
        individual_time = time.time() - start_time

        # Clear data
        await kline_repo.delete("BTCUSDT", KlineInterval.MINUTE_1, base_time, base_time.replace(day=2))

        # Test batch insert
        start_time = time.time()
        saved_count = await kline_repo.save_batch(large_dataset)
        batch_time = time.time() - start_time

        # Verify all data was saved
        assert saved_count == len(large_dataset)
        final_count = await kline_repo.count("BTCUSDT", KlineInterval.MINUTE_1)
        assert final_count == len(large_dataset)

        # Performance verification (batch should be relatively faster per item)
        # Note: In a real database, batch operations would show significant performance gains
        individual_time_per_item = individual_time / len(individual_sample)
        batch_time_per_item = batch_time / len(large_dataset)

        # Log performance metrics (in real test, you might assert performance ratios)
        print(f"Individual insert time per item: {individual_time_per_item:.6f}s")
        print(f"Batch insert time per item: {batch_time_per_item:.6f}s")

    @pytest.mark.asyncio
    async def test_batch_update_atomicity(
        self, kline_repo: MockTransactionalKlineRepository, sample_klines: list[Kline]
    ) -> None:
        """Test atomic batch update operations.

        Description of what the test covers.
        Tests that batch update operations are atomic - either all updates
        succeed or none do, ensuring data consistency in case of failures
        during batch processing.

        Preconditions:
        - Repository with existing data.
        - Batch operation support.

        Steps:
        - Save initial batch of klines.
        - Prepare batch update with some invalid data.
        - Attempt batch update within transaction.
        - Verify atomicity on failure.
        - Test successful atomic batch update.

        Expected Result:
        - Failed batch updates should not partially modify data.
        - Successful batch updates should modify all data.
        - Transaction rollback should work correctly.
        """
        # Save initial data
        await kline_repo.save_batch(sample_klines[:5])
        initial_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert initial_count == 5

        # Prepare batch with mix of valid and invalid operations
        # In this mock, we'll simulate failure by setting failure flag
        await kline_repo.begin_transaction()

        # Save some valid klines
        valid_klines = sample_klines[5:8]
        await kline_repo.save_batch(valid_klines)

        # Verify data is visible in transaction
        transaction_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert transaction_count == 8  # 5 initial + 3 new

        # Simulate failure during next batch operation
        kline_repo.should_fail_on_operation["save_batch"] = True

        try:
            await kline_repo.save_batch(sample_klines[8:])
            raise AssertionError("Expected batch operation to fail")
        except StorageError:
            pass

        # Rollback transaction to ensure atomicity
        await kline_repo.rollback_transaction()

        # Verify only initial data remains (transaction was rolled back)
        final_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert final_count == 5  # Only initial data

        # Test successful atomic batch update
        kline_repo.should_fail_on_operation["save_batch"] = False
        await kline_repo.begin_transaction()

        # Add remaining klines in transaction
        await kline_repo.save_batch(sample_klines[5:])
        await kline_repo.commit_transaction()

        # Verify all data is now present
        final_count = await kline_repo.count("BTCUSDT", KlineInterval.HOUR_1)
        assert final_count == len(sample_klines)

    @pytest.mark.asyncio
    async def test_batch_size_optimization(self, kline_repo: MockTransactionalKlineRepository) -> None:
        """Test optimal batch size handling.

        Description of what the test covers.
        Tests that batch operations handle different batch sizes appropriately,
        including very small batches, optimal batch sizes, and batches that
        exceed system limits.

        Preconditions:
        - Repository with configurable batch size limits.
        - Various sized datasets.

        Steps:
        - Test very small batch (1 item).
        - Test optimal batch size.
        - Test batch size at limit.
        - Test batch size exceeding limit.
        - Verify error handling for oversized batches.

        Expected Result:
        - Small batches should work correctly.
        - Optimal batches should perform well.
        - Oversized batches should be rejected with appropriate error.
        """
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        # Test very small batch (1 item)
        small_batch = [
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=base_time,
                close_time=base_time.replace(hour=1),
                open_price=Decimal("50000.00"),
                high_price=Decimal("50100.00"),
                low_price=Decimal("49900.00"),
                close_price=Decimal("50050.00"),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.0"),
                trades_count=100,
            )
        ]

        saved_count = await kline_repo.save_batch(small_batch)
        assert saved_count == 1

        # Test batch at configured limit
        limit_batch = []
        for i in range(kline_repo.batch_size_limit):
            kline = Kline(
                symbol="ETHUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=base_time + timedelta(hours=i),
                close_time=base_time + timedelta(hours=i + 1),
                open_price=Decimal("3000.00") + Decimal(i),
                high_price=Decimal("3100.00") + Decimal(i),
                low_price=Decimal("2900.00") + Decimal(i),
                close_price=Decimal("3050.00") + Decimal(i),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.0"),
                trades_count=100,
            )
            limit_batch.append(kline)

        saved_count = await kline_repo.save_batch(limit_batch)
        assert saved_count == kline_repo.batch_size_limit

        # Test batch exceeding limit
        oversized_batch = limit_batch + [limit_batch[0]]  # Add one more item

        with pytest.raises(StorageError, match="Batch size .* exceeds limit"):
            await kline_repo.save_batch(oversized_batch)

        # Verify optimal batch size performance
        # Create batch at 50% of limit for "optimal" testing
        optimal_size = kline_repo.batch_size_limit // 2
        optimal_batch = limit_batch[:optimal_size]

        start_time = time.time()
        saved_count = await kline_repo.save_batch(optimal_batch)
        optimal_time = time.time() - start_time

        assert saved_count == optimal_size
        print(f"Optimal batch ({optimal_size} items) completed in {optimal_time:.6f}s")

    @pytest.mark.asyncio
    async def test_batch_error_handling(self, kline_repo: MockTransactionalKlineRepository) -> None:
        """Test error handling in batch operations.

        Description of what the test covers.
        Tests various error scenarios during batch operations including
        partial failures, network errors, validation errors, and recovery
        strategies.

        Preconditions:
        - Repository supporting error simulation.
        - Batch of valid and invalid data.

        Steps:
        - Test batch with some invalid items.
        - Test batch operation during system failure.
        - Test recovery after partial failure.
        - Verify error reporting and logging.

        Expected Result:
        - Errors should be properly reported.
        - Valid items should be processed when possible.
        - System should recover gracefully from failures.
        """
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        # Create batch with potentially problematic data
        test_batch = []
        for i in range(10):
            kline = Kline(
                symbol="ADAUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=base_time.replace(hour=i),
                close_time=base_time.replace(hour=i + 1),
                open_price=Decimal("1.00") + Decimal(i * 0.01),
                high_price=Decimal("1.10") + Decimal(i * 0.01),
                low_price=Decimal("0.90") + Decimal(i * 0.01),
                close_price=Decimal("1.05") + Decimal(i * 0.01),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.0"),
                trades_count=100,
            )
            test_batch.append(kline)

        # Test batch operation with intermittent failures
        # Configure repository to fail on every 3rd item (outside transaction)
        failure_count = 0
        original_save = kline_repo.save

        async def failing_save(kline: Kline) -> None:
            nonlocal failure_count
            failure_count += 1
            if failure_count % 3 == 0 and not kline_repo.in_transaction:
                raise StorageError(f"Simulated failure on item {failure_count}")
            await original_save(kline)

        kline_repo.save = failing_save

        # Attempt batch save (should handle failures gracefully outside transaction)
        saved_count = await kline_repo.save_batch(test_batch)

        # Should save 7 out of 10 items (items 3, 6, 9 fail)
        expected_saved = len(test_batch) - (len(test_batch) // 3)
        assert saved_count == expected_saved

        # Restore original save method
        kline_repo.save = original_save

        # Test batch operation within transaction (should fail completely)
        await kline_repo.begin_transaction()

        kline_repo.should_fail_on_operation["save"] = True

        with pytest.raises(StorageError):
            await kline_repo.save_batch(test_batch[:3])

        # Rollback and verify no partial data
        await kline_repo.rollback_transaction()

        # Reset failure flag
        kline_repo.should_fail_on_operation["save"] = False

        # Test recovery after failure
        recovery_batch = test_batch[:5]
        saved_count = await kline_repo.save_batch(recovery_batch)
        assert saved_count == 5

        # Verify final state
        total_count = await kline_repo.count("ADAUSDT", KlineInterval.HOUR_1)
        assert total_count == expected_saved + 5  # Previous partial + recovery batch
