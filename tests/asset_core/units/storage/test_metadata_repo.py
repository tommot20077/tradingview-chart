# ABOUTME: This file contains unit tests for the AbstractMetadataRepository interface.
# ABOUTME: It tests CRUD operations, TTL functionality, and synchronization status management.

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asset_core.exceptions.core import (
    NotSupportedError,
    StorageConnectionError,
    StorageError,
    StorageReadError,
    StorageWriteError,
)
from asset_core.storage.metadata_repo import AbstractMetadataRepository


class MockMetadataRepository(AbstractMetadataRepository):
    """Mock implementation of AbstractMetadataRepository for testing."""

    def __init__(self, support_ttl: bool = True) -> None:
        """Initialize the mock repository."""
        self.data: dict[str, dict[str, Any]] = {}
        self.ttl_data: dict[str, datetime] = {}
        self.closed = False
        self.support_ttl = support_ttl

    def _is_expired(self, key: str) -> bool:
        """Check if a key with TTL has expired."""
        if key not in self.ttl_data:
            return False
        return datetime.now(UTC) > self.ttl_data[key]

    def _cleanup_expired(self) -> None:
        """Remove expired keys."""
        expired_keys = [key for key in self.ttl_data if self._is_expired(key)]
        for key in expired_keys:
            self.data.pop(key, None)
            self.ttl_data.pop(key, None)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Set a key-value pair."""
        if self.closed:
            raise StorageError("Repository is closed")

        # Validate value type
        if not isinstance(value, dict):
            raise TypeError("value must be a dictionary")

        # Check for non-serializable objects
        try:
            import json

            json.dumps(value)  # This will fail for non-serializable objects
        except (TypeError, ValueError):
            raise StorageWriteError("value contains non-serializable objects")

        self._cleanup_expired()
        self.data[key] = value.copy()
        # Remove TTL if it exists (regular set operation)
        self.ttl_data.pop(key, None)

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a value by key."""
        if self.closed:
            raise StorageError("Repository is closed")

        self._cleanup_expired()

        if key not in self.data:
            return None

        return self.data[key].copy()

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if self.closed:
            raise StorageError("Repository is closed")

        self._cleanup_expired()
        return key in self.data

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if self.closed:
            raise StorageError("Repository is closed")

        self._cleanup_expired()

        if key in self.data:
            del self.data[key]
            self.ttl_data.pop(key, None)
            return True
        return False

    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        if self.closed:
            raise StorageError("Repository is closed")

        self._cleanup_expired()

        keys = list(self.data.keys())

        if prefix is not None and prefix != "":
            keys = [key for key in keys if key.startswith(prefix)]

        return sorted(keys)

    async def set_with_ttl(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Set a key-value pair with TTL."""
        if self.closed:
            raise StorageError("Repository is closed")

        if not self.support_ttl:
            raise NotSupportedError("TTL is not supported by this backend")

        # Validate value type
        if not isinstance(value, dict):
            raise TypeError("value must be a dictionary")

        # Check for non-serializable objects
        try:
            import json

            json.dumps(value)  # This will fail for non-serializable objects
        except (TypeError, ValueError):
            raise StorageWriteError("value contains non-serializable objects")

        # Validate TTL
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self._cleanup_expired()

        self.data[key] = value.copy()
        self.ttl_data[key] = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    async def get_last_sync_time(
        self,
        symbol: str,
        data_type: str,
    ) -> datetime | None:
        """Get the last sync time for a symbol and data type."""
        if self.closed:
            raise StorageError("Repository is closed")

        key = f"sync_time:{symbol}:{data_type}"
        data = await self.get(key)

        if data is None or "timestamp" not in data:
            return None

        return datetime.fromisoformat(data["timestamp"])

    async def set_last_sync_time(
        self,
        symbol: str,
        data_type: str,
        timestamp: datetime,
    ) -> None:
        """Set the last sync time for a symbol and data type."""
        if self.closed:
            raise StorageError("Repository is closed")

        key = f"sync_time:{symbol}:{data_type}"
        await self.set(key, {"timestamp": timestamp.isoformat()})

    async def get_backfill_status(
        self,
        symbol: str,
        data_type: str,
    ) -> dict[str, Any] | None:
        """Get the backfill status for a symbol and data type."""
        if self.closed:
            raise StorageError("Repository is closed")

        key = f"backfill_status:{symbol}:{data_type}"
        return await self.get(key)

    async def set_backfill_status(
        self,
        symbol: str,
        data_type: str,
        status: dict[str, Any],
    ) -> None:
        """Set the backfill status for a symbol and data type."""
        if self.closed:
            raise StorageError("Repository is closed")

        key = f"backfill_status:{symbol}:{data_type}"
        await self.set(key, status)

    async def close(self) -> None:
        """Close the repository."""
        self.closed = True


@pytest.mark.unit
class TestAbstractMetadataRepository:
    """Test cases for AbstractMetadataRepository interface."""

    @pytest.fixture
    def repository(self) -> MockMetadataRepository:
        """Provides a mock repository for testing."""
        return MockMetadataRepository()

    @pytest.fixture
    def sample_data(self) -> dict[str, Any]:
        """Provides sample metadata for testing."""
        return {
            "version": "1.0",
            "config": {"enabled": True, "limit": 100},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def test_repository_set_and_get(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test basic set and get operations.

        Description of what the test covers:
        Verifies that key-value pairs can be stored and retrieved correctly.

        Preconditions:
        - Repository is initialized and functional.
        - Sample data is valid.

        Steps:
        - Set a key-value pair.
        - Get the value back.
        - Verify the retrieved value matches the original.

        Expected Result:
        - Retrieved value is identical to the original data.
        """
        key = "test_key"
        await repository.set(key, sample_data)

        retrieved_data = await repository.get(key)

        assert retrieved_data is not None
        assert retrieved_data == sample_data

    async def test_repository_get_nonexistent_key(self, repository: MockMetadataRepository) -> None:
        """Test getting a non-existent key.

        Description of what the test covers:
        Verifies that getting a non-existent key returns None.

        Preconditions:
        - Repository is empty or key doesn't exist.

        Steps:
        - Get a key that doesn't exist.
        - Verify None is returned.

        Expected Result:
        - Returns None for non-existent keys.
        """
        result = await repository.get("nonexistent_key")
        assert result is None

    async def test_repository_exists(self, repository: MockMetadataRepository, sample_data: dict[str, Any]) -> None:
        """Test key existence checking.

        Description of what the test covers:
        Verifies that key existence can be checked correctly.

        Preconditions:
        - Repository supports exists operation.

        Steps:
        - Check existence of non-existent key.
        - Set a key-value pair.
        - Check existence of the key.
        - Verify results are correct.

        Expected Result:
        - Returns False for non-existent keys, True for existing keys.
        """
        key = "test_key"

        # Check non-existent key
        assert not await repository.exists(key)

        # Set key and check again
        await repository.set(key, sample_data)
        assert await repository.exists(key)

    async def test_repository_delete(self, repository: MockMetadataRepository, sample_data: dict[str, Any]) -> None:
        """Test key deletion.

        Description of what the test covers:
        Verifies that keys can be deleted and the operation returns correct status.

        Preconditions:
        - Repository supports delete operation.

        Steps:
        - Try to delete non-existent key.
        - Set a key-value pair.
        - Delete the key.
        - Verify key is removed and existence check fails.

        Expected Result:
        - Delete returns False for non-existent keys, True for existing keys.
        - Key is actually removed from storage.
        """
        key = "test_key"

        # Try to delete non-existent key
        assert not await repository.delete(key)

        # Set key and delete
        await repository.set(key, sample_data)
        assert await repository.delete(key)

        # Verify key is gone
        assert not await repository.exists(key)
        assert await repository.get(key) is None

    async def test_repository_list_keys(self, repository: MockMetadataRepository, sample_data: dict[str, Any]) -> None:
        """Test listing keys.

        Description of what the test covers:
        Verifies that all keys can be listed and prefix filtering works.

        Preconditions:
        - Repository supports listing keys.
        - Prefix filtering is implemented.

        Steps:
        - List keys from empty repository.
        - Add keys with different prefixes.
        - List all keys.
        - List keys with specific prefix.
        - Verify results are correct.

        Expected Result:
        - All keys are returned when no prefix is specified.
        - Only matching keys are returned when prefix is specified.
        """
        # Empty repository
        keys = await repository.list_keys()
        assert keys == []

        # Add keys with different prefixes
        await repository.set("config:app", sample_data)
        await repository.set("config:db", sample_data)
        await repository.set("status:sync", sample_data)

        # List all keys
        all_keys = await repository.list_keys()
        assert len(all_keys) == 3
        assert "config:app" in all_keys
        assert "config:db" in all_keys
        assert "status:sync" in all_keys

        # List with prefix
        config_keys = await repository.list_keys("config:")
        assert len(config_keys) == 2
        assert "config:app" in config_keys
        assert "config:db" in config_keys
        assert "status:sync" not in config_keys

    async def test_repository_list_keys_empty_prefix(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test list_keys with empty prefix.

        This test verifies the scenario described in missing_tests.md line 215:
        - list_keys with empty prefix
        - assert result is the same as calling list_keys() with no prefix
        """
        # Add keys with different prefixes
        await repository.set("config:app", sample_data)
        await repository.set("config:db", sample_data)
        await repository.set("status:sync", sample_data)

        # List all keys with no prefix
        all_keys_no_prefix = await repository.list_keys()

        # List all keys with empty string prefix
        all_keys_empty_prefix = await repository.list_keys("")

        # Should return the same result
        assert all_keys_empty_prefix == all_keys_no_prefix
        assert len(all_keys_empty_prefix) == 3
        assert "config:app" in all_keys_empty_prefix
        assert "config:db" in all_keys_empty_prefix
        assert "status:sync" in all_keys_empty_prefix

    async def test_repository_set_with_ttl(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test setting keys with TTL.

        Description of what the test covers:
        Verifies that keys can be set with TTL and expire automatically.

        Preconditions:
        - Repository supports TTL functionality.
        - Time-based expiration works.

        Steps:
        - Set a key with short TTL.
        - Verify key exists immediately.
        - Wait for TTL to expire.
        - Verify key is automatically removed.

        Expected Result:
        - Key exists immediately after setting.
        - Key is automatically removed after TTL expires.
        """
        key = "ttl_key"
        ttl_seconds = 1

        await repository.set_with_ttl(key, sample_data, ttl_seconds)

        # Key should exist immediately
        assert await repository.exists(key)

        # Wait for expiration
        import asyncio

        await asyncio.sleep(ttl_seconds + 0.1)

        # Key should be expired and removed
        assert not await repository.exists(key)
        assert await repository.get(key) is None

    async def test_repository_set_with_ttl_not_supported(self, sample_data: dict[str, Any]) -> None:
        """Test TTL operation when not supported.

        Description of what the test covers:
        Verifies that NotSupportedError is raised when TTL is not supported.

        Preconditions:
        - Repository is configured to not support TTL.

        Steps:
        - Try to set a key with TTL.
        - Verify NotSupportedError is raised.

        Expected Result:
        - NotSupportedError is raised with appropriate message.
        """
        repository = MockMetadataRepository(support_ttl=False)

        with pytest.raises(NotSupportedError, match="TTL is not supported"):
            await repository.set_with_ttl("key", sample_data, 60)

    async def test_repository_get_set_last_sync_time(self, repository: MockMetadataRepository) -> None:
        """Test last sync time operations.

        Description of what the test covers:
        Verifies that last sync timestamps can be stored and retrieved.

        Preconditions:
        - Repository supports sync time operations.
        - DateTime handling is correct.

        Steps:
        - Try to get sync time for non-existent entry.
        - Set sync time for a symbol and data type.
        - Retrieve the sync time.
        - Verify timestamp is correct.

        Expected Result:
        - Returns None for non-existent sync times.
        - Correctly stores and retrieves sync timestamps.
        """
        symbol = "BTCUSDT"
        data_type = "klines_1m"

        # Get non-existent sync time
        sync_time = await repository.get_last_sync_time(symbol, data_type)
        assert sync_time is None

        # Set sync time
        test_time = datetime.now(UTC)
        await repository.set_last_sync_time(symbol, data_type, test_time)

        # Get sync time
        retrieved_time = await repository.get_last_sync_time(symbol, data_type)

        assert retrieved_time is not None
        # Compare as ISO strings to avoid microsecond precision issues
        assert retrieved_time.isoformat() == test_time.isoformat()

    async def test_repository_get_set_backfill_status(self, repository: MockMetadataRepository) -> None:
        """Test backfill status operations.

        Description of what the test covers:
        Verifies that backfill status can be stored and retrieved.

        Preconditions:
        - Repository supports backfill status operations.
        - Complex status data is handled correctly.

        Steps:
        - Try to get backfill status for non-existent entry.
        - Set backfill status with complex data.
        - Retrieve the backfill status.
        - Verify status data is correct.

        Expected Result:
        - Returns None for non-existent backfill status.
        - Correctly stores and retrieves backfill status data.
        """
        symbol = "BTCUSDT"
        data_type = "klines_1m"

        # Get non-existent backfill status
        status = await repository.get_backfill_status(symbol, data_type)
        assert status is None

        # Set backfill status
        test_status = {
            "progress": 0.75,
            "last_timestamp": datetime.now(UTC).isoformat(),
            "errors": 0,
            "state": "in_progress",
            "metadata": {"batch_size": 1000},
        }
        await repository.set_backfill_status(symbol, data_type, test_status)

        # Get backfill status
        retrieved_status = await repository.get_backfill_status(symbol, data_type)

        assert retrieved_status is not None
        assert retrieved_status == test_status

    async def test_repository_overwrite_existing_key(self, repository: MockMetadataRepository) -> None:
        """Test overwriting existing keys.

        Description of what the test covers:
        Verifies that existing keys can be overwritten with new values.

        Preconditions:
        - Repository supports key overwriting.

        Steps:
        - Set a key with initial value.
        - Overwrite the key with new value.
        - Verify the new value is retrieved.

        Expected Result:
        - Key is overwritten with new value.
        - Old value is no longer accessible.
        """
        key = "overwrite_key"
        initial_data = {"version": "1.0"}
        new_data = {"version": "2.0", "new_field": "value"}

        # Set initial value
        await repository.set(key, initial_data)
        assert await repository.get(key) == initial_data

        # Overwrite with new value
        await repository.set(key, new_data)
        assert await repository.get(key) == new_data

    async def test_repository_data_isolation(self, repository: MockMetadataRepository) -> None:
        """Test data isolation between keys.

        Description of what the test covers:
        Verifies that modifying retrieved data doesn't affect stored data.

        Preconditions:
        - Repository returns copies of data.
        - Data isolation is maintained.

        Steps:
        - Set a key with mutable data.
        - Get the data and modify it.
        - Get the data again and verify it's unchanged.

        Expected Result:
        - Modifications to retrieved data don't affect stored data.
        """
        key = "isolation_key"
        original_data = {"list": [1, 2, 3], "dict": {"a": 1}}

        await repository.set(key, original_data)

        # Get data and modify it
        retrieved_data = await repository.get(key)
        assert retrieved_data is not None
        retrieved_data["list"].append(4)
        retrieved_data["dict"]["b"] = 2

        # Get data again - should be unchanged
        fresh_data = await repository.get(key)
        assert fresh_data == original_data

    async def test_repository_complex_data_types(self, repository: MockMetadataRepository) -> None:
        """Test handling of complex data types.

        Description of what the test covers:
        Verifies that complex nested data structures are handled correctly.

        Preconditions:
        - Repository supports complex JSON-serializable data.

        Steps:
        - Set keys with various complex data types.
        - Retrieve and verify all data types.

        Expected Result:
        - All complex data types are stored and retrieved correctly.
        """
        complex_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, "two", 3.0, True, None],
            "nested_dict": {"inner_list": [{"deep": "value"}], "inner_dict": {"nested": {"very": {"deep": "data"}}}},
            "empty_list": [],
            "empty_dict": {},
        }

        key = "complex_key"
        await repository.set(key, complex_data)

        retrieved_data = await repository.get(key)
        assert retrieved_data == complex_data

    async def test_repository_close(self, repository: MockMetadataRepository, sample_data: dict[str, Any]) -> None:
        """Test repository close functionality.

        Description of what the test covers:
        Verifies that repository can be closed and operations fail after closing.

        Preconditions:
        - Repository supports close operation.
        - Operations should fail after close.

        Steps:
        - Close the repository.
        - Attempt various operations after close.
        - Verify operations raise appropriate errors.

        Expected Result:
        - Operations fail with StorageError after repository is closed.
        """
        await repository.close()

        with pytest.raises(StorageError, match="Repository is closed"):
            await repository.set("key", sample_data)

        with pytest.raises(StorageError, match="Repository is closed"):
            await repository.get("key")

        with pytest.raises(StorageError, match="Repository is closed"):
            await repository.exists("key")

        with pytest.raises(StorageError, match="Repository is closed"):
            await repository.delete("key")

        with pytest.raises(StorageError, match="Repository is closed"):
            await repository.list_keys()

    async def test_repository_context_manager(self, sample_data: dict[str, Any]) -> None:
        """Test repository as async context manager.

        Description of what the test covers:
        Verifies that repository can be used as an async context manager.

        Preconditions:
        - Repository implements async context manager protocol.
        - Close is called automatically on exit.

        Steps:
        - Use repository in async with statement.
        - Perform operations within the context.
        - Verify repository is automatically closed after exit.

        Expected Result:
        - Repository is properly closed after context exit.
        """
        repository = MockMetadataRepository()

        async with repository as repo:
            # Type: MockMetadataRepository (has closed attribute)
            assert not repository.closed  # Use repository instead since repo type is abstract
            await repo.set("test", sample_data)
            assert await repo.exists("test")

        assert repository.closed

    async def test_repository_empty_data(self, repository: MockMetadataRepository) -> None:
        """Test handling of empty data.

        Description of what the test covers:
        Verifies that empty dictionaries are handled correctly.

        Preconditions:
        - Repository supports empty data structures.

        Steps:
        - Set a key with empty dictionary.
        - Retrieve and verify the data.

        Expected Result:
        - Empty dictionary is stored and retrieved correctly.
        """
        key = "empty_key"
        empty_data: dict[str, Any] = {}

        await repository.set(key, empty_data)
        retrieved_data = await repository.get(key)

        assert retrieved_data == empty_data

    async def test_repository_key_name_variations(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test various key name patterns.

        Description of what the test covers:
        Verifies that different key naming patterns are supported.

        Preconditions:
        - Repository supports various key naming patterns.

        Steps:
        - Set keys with different naming patterns.
        - Verify all keys can be stored and retrieved.

        Expected Result:
        - All key naming patterns are supported.
        """
        key_patterns = [
            "simple",
            "with_underscores",
            "with-dashes",
            "with.dots",
            "with:colons",
            "with/slashes",
            "with spaces",
            "with123numbers",
            "UPPERCASE",
            "MixedCase",
            "特殊字符",  # Unicode characters
            "emoji🚀test",
        ]

        # Set all keys
        for key in key_patterns:
            await repository.set(key, sample_data)

        # Verify all keys exist
        for key in key_patterns:
            assert await repository.exists(key)
            retrieved_data = await repository.get(key)
            assert retrieved_data == sample_data

    async def test_repository_ttl_overrides_regular_set(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test that regular set removes TTL.

        Description of what the test covers:
        Verifies that setting a key with regular set operation removes any existing TTL.

        Preconditions:
        - Repository supports both TTL and regular set operations.

        Steps:
        - Set a key with TTL.
        - Overwrite with regular set.
        - Wait beyond original TTL.
        - Verify key still exists.

        Expected Result:
        - Key persists beyond original TTL after regular set.
        """
        key = "ttl_override_key"
        ttl_seconds = 1

        # Set with TTL
        await repository.set_with_ttl(key, sample_data, ttl_seconds)

        # Overwrite with regular set
        new_data = {"overwritten": True}
        await repository.set(key, new_data)

        # Wait beyond original TTL
        import asyncio

        await asyncio.sleep(ttl_seconds + 0.1)

        # Key should still exist
        assert await repository.exists(key)
        retrieved_data = await repository.get(key)
        assert retrieved_data == new_data

    async def test_set_with_invalid_value_types(self, repository: MockMetadataRepository) -> None:
        """Test set method with invalid value types.

        This test verifies the scenario described in missing_tests.md line 207:
        - set and set_with_ttl with invalid value types
        - assert TypeError or StorageWriteError is raised
        """
        key = "invalid_key"

        # Test with None (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set(key, None)  # type: ignore[arg-type]

        # Test with list (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set(key, [1, 2, 3])  # type: ignore[arg-type]

        # Test with integer (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set(key, 42)  # type: ignore[arg-type]

        # Test with string (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set(key, "not a dict")  # type: ignore[arg-type]

    async def test_set_with_non_serializable_objects(self, repository: MockMetadataRepository) -> None:
        """Test set method with non-JSON-serializable objects in dictionary.

        This test verifies the scenario described in missing_tests.md line 207:
        - set with dictionary containing non-serializable objects
        - assert StorageWriteError is raised
        """
        import datetime

        key = "non_serializable_key"

        # Test with raw datetime object (not JSON serializable without conversion)
        non_serializable_data = {
            "timestamp": datetime.datetime.now(),  # Raw datetime not JSON serializable
            "function": lambda x: x,  # Function not JSON serializable
        }

        with pytest.raises(StorageWriteError, match="contains non-serializable objects"):
            await repository.set(key, non_serializable_data)

    async def test_set_with_ttl_invalid_value_types(self, repository: MockMetadataRepository) -> None:
        """Test set_with_ttl method with invalid value types.

        This test verifies the scenario described in missing_tests.md line 207:
        - set_with_ttl with invalid value types
        - assert TypeError or StorageWriteError is raised
        """
        key = "invalid_ttl_key"
        ttl_seconds = 60

        # Test with None (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set_with_ttl(key, None, ttl_seconds)  # type: ignore[arg-type]

        # Test with list (should raise TypeError)
        with pytest.raises(TypeError, match="value must be a dictionary"):
            await repository.set_with_ttl(key, [1, 2, 3], ttl_seconds)  # type: ignore[arg-type]

    async def test_set_with_ttl_invalid_ttl_seconds(
        self, repository: MockMetadataRepository, sample_data: dict[str, Any]
    ) -> None:
        """Test set_with_ttl with invalid ttl_seconds values.

        This test verifies the scenario described in missing_tests.md line 211:
        - set_with_ttl with invalid ttl_seconds
        - assert ValueError is raised
        """
        key = "ttl_key"

        # Test with zero TTL (should raise ValueError)
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            await repository.set_with_ttl(key, sample_data, 0)

        # Test with negative TTL (should raise ValueError)
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            await repository.set_with_ttl(key, sample_data, -1)

        # Test with negative TTL (should raise ValueError)
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            await repository.set_with_ttl(key, sample_data, -60)

    @pytest.mark.asyncio
    async def test_repository_multiple_sync_times(self, repository: MockMetadataRepository) -> None:
        """Test multiple sync time entries.

        Description of what the test covers:
        Verifies that multiple symbol/data_type combinations can have independent sync times.

        Preconditions:
        - Repository supports multiple independent sync time entries.

        Steps:
        - Set sync times for different symbol/data_type combinations.
        - Retrieve each sync time.
        - Verify they are independent and correct.

        Expected Result:
        - Each symbol/data_type combination has independent sync time.
        """
        combinations = [
            ("BTCUSDT", "klines_1m"),
            ("ETHUSDT", "klines_1m"),
            ("BTCUSDT", "trades"),
            ("ETHUSDT", "trades"),
        ]

        # Set different sync times
        for i, (symbol, data_type) in enumerate(combinations):
            timestamp = datetime.now(UTC) + timedelta(minutes=i)
            await repository.set_last_sync_time(symbol, data_type, timestamp)

        # Verify each combination has correct sync time
        for i, (symbol, data_type) in enumerate(combinations):
            expected_time = datetime.now(UTC) + timedelta(minutes=i)
            retrieved_time = await repository.get_last_sync_time(symbol, data_type)

            assert retrieved_time is not None
            # Check that the times are close (within 1 second)
            time_diff = abs((retrieved_time - expected_time).total_seconds())
            assert time_diff < 1.0


class TestMetadataRepositoryErrorHandling:
    """Test error handling and database exception scenarios for metadata repository."""

    @pytest.fixture
    def mock_failing_repo(self) -> Mock:
        """Create a mock metadata repository that simulates database failures."""
        repo = Mock(spec=AbstractMetadataRepository)
        repo.db_driver = AsyncMock()
        repo.closed = False
        return repo

    @pytest.fixture
    def sample_metadata(self) -> dict[str, Any]:
        """Create sample metadata for error testing."""
        return {
            "version": "1.0",
            "config": {"enabled": True, "limit": 100},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @pytest.mark.asyncio
    async def test_database_connection_error_on_set(
        self, mock_failing_repo: Mock, sample_metadata: dict[str, Any]
    ) -> None:
        """Test handling of database connection errors during set operations.

        Description of what the test covers:
        Verifies that the metadata repository properly handles and wraps database
        connection errors during set operations with appropriate StorageError exceptions.

        Preconditions:
        - Repository is configured with database driver
        - Database connection can fail during write operations

        Steps:
        - Mock database driver to raise connection error on set operation
        - Attempt to set a key-value pair
        - Verify StorageConnectionError is raised
        - Check error message includes operation context and trace ID

        Expected Result:
        - StorageConnectionError is raised instead of raw DB error
        - Error includes relevant context about the failed operation
        - Trace ID is present for debugging
        """
        # Configure mock to raise connection error
        mock_failing_repo.db_driver.upsert.side_effect = Exception("Connection timeout")

        async def failing_set(key: str, value: dict[str, Any]) -> None:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")
            try:
                await mock_failing_repo.db_driver.upsert(key, value)
            except Exception as e:
                raise StorageConnectionError(
                    f"Failed to connect to database during set operation: {str(e)}",
                    details={"operation": "set", "key": key, "error_type": type(e).__name__},
                ) from e

        mock_failing_repo.set = failing_set

        # Test connection error handling
        with pytest.raises(StorageConnectionError) as exc_info:
            await mock_failing_repo.set("test_key", sample_metadata)

        error = exc_info.value
        assert "Failed to connect to database during set operation" in str(error)
        assert "Connection timeout" in str(error)
        assert error.details["operation"] == "set"
        assert error.details["key"] == "test_key"
        assert error.details["error_type"] == "Exception"
        assert error.trace_id is not None

    @pytest.mark.asyncio
    async def test_database_read_error_on_get(self, mock_failing_repo: Mock) -> None:
        """Test handling of database read errors during get operations.

        Description of what the test covers:
        Verifies that read operation failures are properly caught and
        wrapped in StorageReadError exceptions with relevant context.

        Preconditions:
        - Repository can perform read operations
        - Database can fail during read operations

        Steps:
        - Mock database to raise read-specific errors
        - Attempt get operation
        - Verify StorageReadError is raised
        - Check error details include operation context

        Expected Result:
        - StorageReadError is raised with proper error message
        - Error includes details about failed read operation
        """
        # Configure mock to raise read error
        mock_failing_repo.db_driver.select.side_effect = Exception("Table corruption detected")

        async def failing_get(key: str) -> dict[str, Any] | None:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")
            try:
                result: dict[str, Any] | None = await mock_failing_repo.db_driver.select(key)
                return result
            except Exception as e:
                raise StorageReadError(
                    f"Failed to read from database: {str(e)}",
                    details={"operation": "get", "key": key, "error_type": type(e).__name__},
                ) from e

        mock_failing_repo.get = failing_get

        # Test read error handling
        with pytest.raises(StorageReadError) as exc_info:
            await mock_failing_repo.get("non_existent_key")

        error = exc_info.value
        assert "Failed to read from database" in str(error)
        assert "Table corruption detected" in str(error)
        assert error.details["operation"] == "get"
        assert error.details["key"] == "non_existent_key"
        assert error.details["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_database_write_error_on_set_with_ttl(
        self, mock_failing_repo: Mock, sample_metadata: dict[str, Any]
    ) -> None:
        """Test handling of database write errors during TTL operations.

        Description of what the test covers:
        Verifies that TTL write operation failures are properly handled and
        wrapped in StorageWriteError exceptions.

        Preconditions:
        - Repository supports TTL operations
        - Database can reject TTL write operations

        Steps:
        - Mock database to raise write-specific errors on TTL operations
        - Attempt set_with_ttl operation
        - Verify StorageWriteError is raised
        - Check error includes TTL operation context

        Expected Result:
        - StorageWriteError is raised with proper error message
        - Error includes details about failed TTL operation
        """
        # Configure mock to raise write error
        mock_failing_repo.db_driver.upsert_with_ttl.side_effect = Exception("Disk full - cannot write TTL")

        async def failing_set_with_ttl(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")
            try:
                await mock_failing_repo.db_driver.upsert_with_ttl(key, value, ttl_seconds)
            except Exception as e:
                raise StorageWriteError(
                    f"Failed to write TTL data to database: {str(e)}",
                    details={
                        "operation": "set_with_ttl",
                        "key": key,
                        "ttl_seconds": ttl_seconds,
                        "error_type": type(e).__name__,
                    },
                ) from e

        mock_failing_repo.set_with_ttl = failing_set_with_ttl

        # Test TTL write error handling
        with pytest.raises(StorageWriteError) as exc_info:
            await mock_failing_repo.set_with_ttl("ttl_key", sample_metadata, 300)

        error = exc_info.value
        assert "Failed to write TTL data to database" in str(error)
        assert "Disk full - cannot write TTL" in str(error)
        assert error.details["operation"] == "set_with_ttl"
        assert error.details["key"] == "ttl_key"
        assert error.details["ttl_seconds"] == 300
        assert error.details["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_database_error_on_delete_operation(self, mock_failing_repo: Mock) -> None:
        """Test handling of database errors during delete operations.

        Description of what the test covers:
        Verifies that delete operation failures are properly handled and
        appropriate errors are raised with context.

        Preconditions:
        - Repository supports delete operations
        - Database can fail during delete operations

        Steps:
        - Mock database to raise errors on delete operations
        - Attempt delete operation
        - Verify appropriate StorageError is raised
        - Check error includes delete operation context

        Expected Result:
        - StorageError is raised with proper error message
        - Error includes details about failed delete operation
        """
        # Configure mock to raise delete error
        mock_failing_repo.db_driver.delete.side_effect = Exception("Foreign key constraint violation")

        async def failing_delete(key: str) -> bool:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")
            try:
                result: bool = await mock_failing_repo.db_driver.delete(key)
                return result
            except Exception as e:
                raise StorageError(
                    f"Failed to delete from database: {str(e)}",
                    details={"operation": "delete", "key": key, "error_type": type(e).__name__},
                ) from e

        mock_failing_repo.delete = failing_delete

        # Test delete error handling
        with pytest.raises(StorageError) as exc_info:
            await mock_failing_repo.delete("protected_key")

        error = exc_info.value
        assert "Failed to delete from database" in str(error)
        assert "Foreign key constraint violation" in str(error)
        assert error.details["operation"] == "delete"
        assert error.details["key"] == "protected_key"
        assert error.details["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_database_error_on_list_keys_operation(self, mock_failing_repo: Mock) -> None:
        """Test handling of database errors during list_keys operations.

        Description of what the test covers:
        Verifies that list_keys operation failures are properly handled and
        appropriate read errors are raised.

        Preconditions:
        - Repository supports list_keys operations
        - Database can fail during key listing operations

        Steps:
        - Mock database to raise errors on list operations
        - Attempt list_keys operation with prefix
        - Verify StorageReadError is raised
        - Check error includes list operation context

        Expected Result:
        - StorageReadError is raised with proper error message
        - Error includes details about failed list operation
        """
        # Configure mock to raise list error
        mock_failing_repo.db_driver.list_keys.side_effect = Exception("Index corruption in keys table")

        async def failing_list_keys(prefix: str | None = None) -> list[str]:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")
            try:
                result: list[str] = await mock_failing_repo.db_driver.list_keys(prefix)
                return result
            except Exception as e:
                raise StorageReadError(
                    f"Failed to list keys from database: {str(e)}",
                    details={"operation": "list_keys", "prefix": prefix, "error_type": type(e).__name__},
                ) from e

        mock_failing_repo.list_keys = failing_list_keys

        # Test list keys error handling
        with pytest.raises(StorageReadError) as exc_info:
            await mock_failing_repo.list_keys("config:")

        error = exc_info.value
        assert "Failed to list keys from database" in str(error)
        assert "Index corruption in keys table" in str(error)
        assert error.details["operation"] == "list_keys"
        assert error.details["prefix"] == "config:"
        assert error.details["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_graceful_handling_of_transaction_rollback(self, mock_failing_repo: Mock) -> None:
        """Test graceful handling of transaction rollback scenarios.

        Description of what the test covers:
        Verifies that the repository can handle transaction rollback scenarios
        gracefully and provide appropriate error information.

        Preconditions:
        - Repository supports transactional operations
        - Database can rollback transactions due to conflicts

        Steps:
        - Mock database to simulate transaction rollback
        - Attempt operation that triggers rollback
        - Verify error handling includes transaction context
        - Check that repository state remains consistent

        Expected Result:
        - Appropriate error is raised with transaction details
        - Repository remains in consistent state after rollback
        """
        # Configure mock to raise transaction rollback error
        mock_failing_repo.db_driver.begin_transaction = AsyncMock()
        mock_failing_repo.db_driver.commit_transaction = AsyncMock(
            side_effect=Exception("Transaction conflict - rolling back")
        )
        mock_failing_repo.db_driver.rollback_transaction = AsyncMock()

        async def failing_transactional_operation(operations: list[dict[str, Any]]) -> None:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")

            try:
                await mock_failing_repo.db_driver.begin_transaction()
                # Simulate multiple operations
                for op in operations:
                    await mock_failing_repo.db_driver.upsert(op["key"], op["value"])
                await mock_failing_repo.db_driver.commit_transaction()
            except Exception as e:
                await mock_failing_repo.db_driver.rollback_transaction()
                raise StorageError(
                    f"Transaction failed and was rolled back: {str(e)}",
                    details={
                        "operation": "transactional_batch",
                        "operations_count": len(operations),
                        "error_type": type(e).__name__,
                        "rollback_performed": True,
                    },
                ) from e

        mock_failing_repo.transactional_batch = failing_transactional_operation

        # Test transaction rollback handling
        operations = [
            {"key": "key1", "value": {"data": "value1"}},
            {"key": "key2", "value": {"data": "value2"}},
        ]

        with pytest.raises(StorageError) as exc_info:
            await mock_failing_repo.transactional_batch(operations)

        error = exc_info.value
        assert "Transaction failed and was rolled back" in str(error)
        assert "Transaction conflict - rolling back" in str(error)
        assert error.details["operation"] == "transactional_batch"
        assert error.details["operations_count"] == 2
        assert error.details["rollback_performed"] is True

        # Verify rollback was called
        mock_failing_repo.db_driver.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_with_retry_logic(
        self, mock_failing_repo: Mock, sample_metadata: dict[str, Any]
    ) -> None:
        """Test error handling with retry logic for transient failures.

        Description of what the test covers:
        Verifies that the repository can implement retry logic for transient
        failures and eventually succeed or fail with appropriate context.

        Preconditions:
        - Repository supports retry logic for transient failures
        - Database can have temporary connectivity issues

        Steps:
        - Mock database to fail initially then succeed
        - Implement retry logic in repository operation
        - Verify operation eventually succeeds after retries
        - Test that permanent failures are handled correctly

        Expected Result:
        - Transient failures are retried successfully
        - Permanent failures raise appropriate errors after max retries
        - Error details include retry information
        """
        # Create a mock that fails twice then succeeds
        call_count = 0

        def side_effect_with_retries(*_args: Any, **_kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary connection issue")
            # Third call succeeds
            return None

        mock_failing_repo.db_driver.upsert.side_effect = side_effect_with_retries

        async def set_with_retry(key: str, value: dict[str, Any], max_retries: int = 3) -> None:
            if mock_failing_repo.closed:
                raise StorageError("Repository is closed")

            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    await mock_failing_repo.db_driver.upsert(key, value)
                    return  # Success
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        # Wait briefly before retry (in real implementation)
                        continue
                    else:
                        # Max retries exceeded
                        raise StorageWriteError(
                            f"Failed to set key after {max_retries} retries: {str(e)}",
                            details={
                                "operation": "set_with_retry",
                                "key": key,
                                "max_retries": max_retries,
                                "attempts_made": attempt + 1,
                                "final_error": str(last_error),
                            },
                        ) from e

        mock_failing_repo.set_with_retry = set_with_retry

        # Test successful retry scenario
        # This should succeed on the third attempt
        await mock_failing_repo.set_with_retry("retry_key", sample_metadata, max_retries=3)

        # Verify the operation was retried
        assert mock_failing_repo.db_driver.upsert.call_count == 3

        # Reset for permanent failure test
        mock_failing_repo.db_driver.upsert.side_effect = Exception("Permanent database error")

        # Test permanent failure scenario
        with pytest.raises(StorageWriteError) as exc_info:
            await mock_failing_repo.set_with_retry("permanent_fail_key", sample_metadata, max_retries=2)

        error = exc_info.value
        assert "Failed to set key after 2 retries" in str(error)
        assert error.details["max_retries"] == 2
        assert error.details["attempts_made"] == 3  # 1 initial + 2 retries
        assert "Permanent database error" in error.details["final_error"]

    @pytest.mark.asyncio
    async def test_context_manager_error_handling(self, sample_metadata: dict[str, Any]) -> None:
        """Test error handling within async context manager usage.

        Description of what the test covers:
        Verifies that errors occurring within async context manager usage
        are properly handled and the repository is correctly closed.

        Preconditions:
        - Repository supports async context manager protocol
        - Errors can occur during context manager operations

        Steps:
        - Use repository in async context manager
        - Simulate error during operation within context
        - Verify error is properly raised
        - Verify repository is properly closed even after error

        Expected Result:
        - Errors are not swallowed by context manager
        - Repository is properly closed after error
        - Original error is preserved with trace information
        """

        # Create a mock repository that fails during operation but supports context manager
        class FailingMockRepository:
            def __init__(self) -> None:
                self.closed = False
                self.db_driver = AsyncMock()
                self.db_driver.upsert.side_effect = Exception("Operation failed in context")

            async def __aenter__(self) -> "FailingMockRepository":
                return self

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                await self.close()

            async def close(self) -> None:
                self.closed = True

            async def set(self, key: str, value: dict[str, Any]) -> None:
                if self.closed:
                    raise StorageError("Repository is closed")
                try:
                    await self.db_driver.upsert(key, value)
                except Exception as e:
                    raise StorageError(
                        f"Failed to set key in context: {str(e)}",
                        details={"operation": "set", "key": key, "in_context_manager": True},
                    ) from e

        failing_repo = FailingMockRepository()

        # Test error handling in context manager
        with pytest.raises(StorageError) as exc_info:
            async with failing_repo as repo:
                assert not repo.closed
                await repo.set("context_key", sample_metadata)

        # Verify error details
        error = exc_info.value
        assert "Failed to set key in context" in str(error)
        assert "Operation failed in context" in str(error)
        assert error.details["operation"] == "set"
        assert error.details["key"] == "context_key"
        assert error.details["in_context_manager"] is True

        # Verify repository was properly closed despite the error
        assert failing_repo.closed
