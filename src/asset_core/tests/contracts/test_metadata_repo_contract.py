"""
Contract tests for AbstractMetadataRepository interface.

Comprehensive tests to verify that any implementation of AbstractMetadataRepository
follows the expected behavioral contracts and interface specifications.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from asset_core.storage.metadata_repo import AbstractMetadataRepository
from asset_core.types.common import Symbol

from .base_contract_test import AsyncContractTestMixin, BaseContractTest, \
    MockImplementationBase


class MockMetadataRepository(AbstractMetadataRepository, MockImplementationBase):
    """
    Mock implementation of AbstractMetadataRepository for contract testing.

    Provides a complete implementation that follows the interface contract
    while using in-memory storage for testing purposes.
    """

    def __init__(self):
        super().__init__()
        self._metadata: dict[str, dict[str, Any]] = {}
        self._ttl_data: dict[str, datetime] = {}
        self._name = "mock_metadata_repo"
        self._metadata.clear()
        self._ttl_data.clear()

    @property
    def name(self) -> str:
        return self._name

    def _is_expired(self, key: str) -> bool:
        """Check if a key with TTL has expired."""
        if key not in self._ttl_data:
            return False
        return datetime.now(UTC) > self._ttl_data[key]

    def _cleanup_expired(self, key: str) -> None:
        """Remove expired data."""
        if self._is_expired(key):
            self._metadata.pop(key, None)
            self._ttl_data.pop(key, None)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Store metadata as JSON-serializable dict."""
        self._check_not_closed()

        if not isinstance(value, dict):
            raise ValueError("Value must be a dictionary")

        # Simulate JSON serialization check
        try:
            import json

            json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value must be JSON-serializable: {e}")

        self._metadata[key] = value.copy()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve metadata by key."""
        self._check_not_closed()
        self._cleanup_expired(key)

        return self._metadata.get(key)

    async def exists(self, key: str) -> bool:
        """Check key existence."""
        self._check_not_closed()
        self._cleanup_expired(key)

        return key in self._metadata

    async def delete(self, key: str) -> bool:
        """Remove metadata, return True if key existed."""
        self._check_not_closed()

        existed = key in self._metadata
        self._metadata.pop(key, None)
        self._ttl_data.pop(key, None)

        return existed

    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """List keys with optional prefix filter."""
        self._check_not_closed()

        # Cleanup expired keys first
        expired_keys = [k for k in self._metadata if self._is_expired(k)]
        for key in expired_keys:
            self._cleanup_expired(key)

        keys = list(self._metadata.keys())

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        return sorted(keys)

    async def set_with_ttl(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        """Store with expiration time."""
        self._check_not_closed()

        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")

        await self.set(key, value)

        # Set expiration time
        from datetime import timedelta

        expiry_time = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._ttl_data[key] = expiry_time

    async def get_last_sync_time(self, symbol: Symbol) -> datetime | None:
        """Get synchronization timestamp."""
        self._check_not_closed()

        sync_data = await self.get(f"sync_time:{symbol}")

        if sync_data and "timestamp" in sync_data:
            # Convert ISO string back to datetime
            timestamp_str = sync_data["timestamp"]
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return None

    async def set_last_sync_time(self, symbol: Symbol, timestamp: datetime) -> None:
        """Update synchronization timestamp."""
        self._check_not_closed()

        sync_data = {"timestamp": timestamp.isoformat(), "symbol": symbol}

        await self.set(f"sync_time:{symbol}", sync_data)

    async def get_backfill_status(self, symbol: Symbol) -> dict[str, Any] | None:
        """Get backfill progress information."""
        self._check_not_closed()

        return await self.get(f"backfill:{symbol}")

    async def set_backfill_status(self, symbol: Symbol, status: dict[str, Any]) -> None:
        """Update backfill progress."""
        self._check_not_closed()

        if not isinstance(status, dict):
            raise ValueError("Status must be a dictionary")

        # Validate required fields
        required_fields = {"status", "progress", "last_updated"}
        if not all(field in status for field in required_fields):
            raise ValueError(f"Status must contain fields: {required_fields}")

        await self.set(f"backfill:{symbol}", status)

    async def close(self) -> None:
        """Close repository and clean up resources."""
        self._is_closed = True
        self._metadata.clear()
        self._ttl_data.clear()

    async def __aenter__(self) -> "MockMetadataRepository":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Async context manager exit."""
        await self.close()
        return False


@pytest.fixture(scope="function")
async def repo() -> MockMetadataRepository:
    """Create a mock repository instance for testing."""
    return MockMetadataRepository()


class TestAbstractMetadataRepositoryContract(BaseContractTest, AsyncContractTestMixin):
    """
    Contract tests for AbstractMetadataRepository interface.

    These tests verify that any implementation of AbstractMetadataRepository
    follows the expected behavioral contracts.
    """

    @pytest.fixture
    def sample_metadata(self) -> dict[str, Any]:
        """Create sample metadata for testing."""
        return {
            "version": "1.0",
            "created_at": "2024-01-01T12:00:00Z",
            "config": {"retry_count": 3, "timeout_seconds": 30},
            "tags": ["crypto", "trading"],
        }

    def test_required_methods_defined(self):
        """
        Test that all required abstract methods are defined in the interface.

        Verifies that AbstractMetadataRepository declares all necessary methods
        as abstract and that they have the correct signatures.

        Expected Result:
            - All required methods are present as abstract methods
            - Method signatures match the expected interface
        """
        abstract_methods = self.get_abstract_methods(AbstractMetadataRepository)

        required_methods = {
            "set",
            "get",
            "exists",
            "delete",
            "list_keys",
            "set_with_ttl",
            "get_last_sync_time",
            "set_last_sync_time",
            "get_backfill_status",
            "set_backfill_status",
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
        set_sig = self.get_method_signature(AbstractMetadataRepository, "set")
        assert len(set_sig.parameters) == 3  # self, key, value
        assert "key" in set_sig.parameters
        assert "value" in set_sig.parameters

        get_sig = self.get_method_signature(AbstractMetadataRepository, "get")
        assert len(get_sig.parameters) == 2  # self, key
        assert "key" in get_sig.parameters

        # Test that core methods are async
        assert self.is_async_method(AbstractMetadataRepository, "set")
        assert self.is_async_method(AbstractMetadataRepository, "get")
        assert self.is_async_method(AbstractMetadataRepository, "close")

    def test_async_context_manager_protocol(self):
        """
        Test that the repository implements async context manager protocol.

        Verifies that __aenter__ and __aexit__ methods are present and
        that they work correctly for resource management.

        Expected Result:
            - Repository has __aenter__ and __aexit__ methods
            - Can be used in async with statements
        """
        assert self.has_async_context_manager(AbstractMetadataRepository)

    @pytest.mark.asyncio
    async def test_mock_implementation_completeness(self, repo: MockMetadataRepository):
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
        abstract_methods = self.get_abstract_methods(AbstractMetadataRepository)
        for method_name in abstract_methods:
            assert hasattr(repo, method_name), f"Missing method: {method_name}"
            method = getattr(repo, method_name)
            assert callable(method), f"Method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_basic_crud_operations(self, repo: MockMetadataRepository, sample_metadata: dict[str, Any]):
        """
        Test basic CRUD operations work correctly.

        Tests the fundamental create, read, update, delete operations
        to ensure the repository behaves as expected.

        Preconditions:
            - Repository is initialized and not closed

        Steps:
            - Set metadata
            - Get it back
            - Check existence
            - Update it
            - Delete it
            - Verify it's gone

        Expected Result:
            - All operations complete successfully
            - Data consistency is maintained
            - Return values match expectations
        """
        test_key = "test:config"

        # Test set operation
        await repo.set(test_key, sample_metadata)

        # Test get operation
        retrieved = await repo.get(test_key)
        assert retrieved is not None
        assert retrieved == sample_metadata

        # Test exists operation
        exists = await repo.exists(test_key)
        assert exists is True

        # Test update operation
        updated_metadata = sample_metadata.copy()
        updated_metadata["version"] = "2.0"
        await repo.set(test_key, updated_metadata)

        retrieved_updated = await repo.get(test_key)
        assert retrieved_updated["version"] == "2.0"

        # Test delete operation
        deleted = await repo.delete(test_key)
        assert deleted is True

        # Verify deletion
        exists_after = await repo.exists(test_key)
        assert exists_after is False

        retrieved_after = await repo.get(test_key)
        assert retrieved_after is None

        # Test deleting non-existent key
        deleted_again = await repo.delete(test_key)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_json_serializable_validation(self, repo: MockMetadataRepository):
        """
        Test that only JSON-serializable values are accepted.

        Verifies that the repository validates that all stored values
        can be serialized to JSON.

        Expected Result:
            - Valid JSON-serializable dicts are accepted
            - Non-serializable values raise ValueError
            - Non-dict values raise ValueError
        """
        # Test valid JSON-serializable dict
        valid_data = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"},
        }

        await repo.set("valid", valid_data)
        retrieved = await repo.get("valid")
        assert retrieved == valid_data

        # Test non-dict value
        with pytest.raises(ValueError, match="must be a dictionary"):
            await repo.set("invalid", "not a dict")

        # Test non-JSON-serializable dict
        import datetime

        invalid_data = {
            "datetime": datetime.datetime.now(),  # Not JSON serializable
        }

        with pytest.raises(ValueError, match="must be JSON-serializable"):
            await repo.set("invalid", invalid_data)

    @pytest.mark.asyncio
    async def test_key_listing_and_prefix_filtering(self, repo: MockMetadataRepository):
        """
        Test key listing functionality with prefix filtering.

        Verifies that list_keys returns all keys and properly filters
        by prefix when specified.

        Expected Result:
            - list_keys() returns all keys
            - Prefix filtering works correctly
            - Keys are returned in consistent order
        """
        # Add test data with different prefixes
        test_data = {
            "user:123": {"name": "Alice"},
            "user:456": {"name": "Bob"},
            "config:app": {"version": "1.0"},
            "config:db": {"host": "localhost"},
            "temp:cache": {"data": "cached"},
        }

        for key, value in test_data.items():
            await repo.set(key, value)

        # Test listing all keys
        all_keys = await repo.list_keys()
        assert len(all_keys) == 5
        assert set(all_keys) == set(test_data.keys())

        # Test prefix filtering
        user_keys = await repo.list_keys("user:")
        assert len(user_keys) == 2
        assert all(key.startswith("user:") for key in user_keys)
        assert set(user_keys) == {"user:123", "user:456"}

        config_keys = await repo.list_keys("config:")
        assert len(config_keys) == 2
        assert set(config_keys) == {"config:app", "config:db"}

        # Test non-matching prefix
        no_match_keys = await repo.list_keys("nonexistent:")
        assert len(no_match_keys) == 0

        # Test empty prefix (should return all keys)
        empty_prefix_keys = await repo.list_keys("")
        assert len(empty_prefix_keys) == 5

    @pytest.mark.asyncio
    async def test_ttl_functionality(self, repo: MockMetadataRepository):
        """
        Test TTL (Time To Live) functionality.

        Verifies that set_with_ttl properly sets expiration times
        and that expired data is cleaned up correctly.

        Expected Result:
            - TTL values are accepted and stored
            - Expired data is not returned
            - Invalid TTL values raise exceptions
        """
        ttl_data = {"temporary": "data", "expires": True}

        # Test setting with TTL
        await repo.set_with_ttl("ttl:test", ttl_data, 60)  # 60 seconds

        # Should be accessible immediately
        retrieved = await repo.get("ttl:test")
        assert retrieved == ttl_data

        exists = await repo.exists("ttl:test")
        assert exists is True

        # Test invalid TTL values
        with pytest.raises(ValueError, match="TTL must be positive"):
            await repo.set_with_ttl("invalid", ttl_data, -1)

        with pytest.raises(ValueError, match="TTL must be positive"):
            await repo.set_with_ttl("invalid", ttl_data, 0)

        # Note: Testing actual expiration would require time manipulation
        # which is complex in unit tests. The mock implementation shows
        # the expected behavior pattern.

    @pytest.mark.asyncio
    async def test_sync_time_management_interface(self, repo: MockMetadataRepository):
        """
        Test synchronization time management functionality.

        Verifies that sync time can be stored and retrieved correctly
        for different symbols.

        Expected Result:
            - Sync times can be set and retrieved
            - Different symbols have independent sync times
            - Returns None for non-existent sync times
        """
        symbol1 = "BTCUSDT"
        symbol2 = "ETHUSDT"

        sync_time1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        sync_time2 = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Test setting sync times
        await repo.set_last_sync_time(symbol1, sync_time1)
        await repo.set_last_sync_time(symbol2, sync_time2)

        # Test retrieving sync times
        retrieved1 = await repo.get_last_sync_time(symbol1)
        retrieved2 = await repo.get_last_sync_time(symbol2)

        assert retrieved1 == sync_time1
        assert retrieved2 == sync_time2

        # Test non-existent sync time
        non_existent = await repo.get_last_sync_time("NONEXISTENT")
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_backfill_status_management_interface(self, repo: MockMetadataRepository):
        """
        Test backfill status management functionality.

        Verifies that backfill progress can be tracked and updated
        for different symbols.

        Expected Result:
            - Backfill status can be set and retrieved
            - Status validation works correctly
            - Different symbols have independent status
        """
        symbol = "ADAUSDT"

        backfill_status = {
            "status": "in_progress",
            "progress": 0.65,
            "last_updated": "2024-01-01T12:00:00Z",
            "total_records": 10000,
            "processed_records": 6500,
            "errors": 0,
        }

        # Test setting backfill status
        await repo.set_backfill_status(symbol, backfill_status)

        # Test retrieving backfill status
        retrieved = await repo.get_backfill_status(symbol)
        assert retrieved == backfill_status  # type: ignore[comparison-overlap]

        # Test non-existent backfill status
        non_existent = await repo.get_backfill_status("NONEXISTENT")
        assert non_existent is None

        # Test status validation
        invalid_status = {"incomplete": "status"}  # Missing required fields

        with pytest.raises(ValueError, match="Status must contain fields"):
            await repo.set_backfill_status(symbol, invalid_status)

        # Test non-dict status
        with pytest.raises(ValueError, match="Status must be a dictionary"):
            await repo.set_backfill_status(symbol, "not a dict")

    @pytest.mark.asyncio
    async def test_async_context_manager_behavior(self, repo: MockMetadataRepository):
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
    async def test_closed_state_handling(self, repo: MockMetadataRepository):
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
        test_data = {"test": "data"}

        await self.assert_method_raises_when_not_ready(repo, "set", RuntimeError, "test_key", test_data)

        await self.assert_method_raises_when_not_ready(repo, "get", RuntimeError, "test_key")

        await self.assert_method_raises_when_not_ready(repo, "exists", RuntimeError, "test_key")

        await self.assert_method_raises_when_not_ready(repo, "list_keys", RuntimeError)
