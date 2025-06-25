"""Abstract metadata repository interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class AbstractMetadataRepository(ABC):
    """Abstract interface for metadata storage implementations."""

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value (must be JSON-serializable)
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        """Get metadata value.

        Args:
            key: Metadata key

        Returns:
            Metadata value or None if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if metadata key exists.

        Args:
            key: Metadata key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete metadata.

        Args:
            key: Metadata key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """List metadata keys.

        Args:
            prefix: Optional key prefix to filter by

        Returns:
            List of keys
        """
        pass

    @abstractmethod
    async def set_with_ttl(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Set metadata with TTL.

        Args:
            key: Metadata key
            value: Metadata value
            ttl_seconds: Time to live in seconds
        """
        pass

    @abstractmethod
    async def get_last_sync_time(
        self,
        symbol: str,
        data_type: str,
    ) -> datetime | None:
        """Get last synchronization time for a symbol and data type.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data (e.g., "trades", "klines_1m")

        Returns:
            Last sync time or None if never synced
        """
        pass

    @abstractmethod
    async def set_last_sync_time(
        self,
        symbol: str,
        data_type: str,
        timestamp: datetime,
    ) -> None:
        """Set last synchronization time.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data (e.g., "trades", "klines_1m")
            timestamp: Synchronization timestamp
        """
        pass

    @abstractmethod
    async def get_backfill_status(
        self,
        symbol: str,
        data_type: str,
    ) -> dict[str, Any] | None:
        """Get backfill status.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data

        Returns:
            Backfill status including progress, errors, etc.
        """
        pass

    @abstractmethod
    async def set_backfill_status(
        self,
        symbol: str,
        data_type: str,
        status: dict[str, Any],
    ) -> None:
        """Set backfill status.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data
            status: Status information
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the repository and clean up resources."""
        pass

    async def __aenter__(self) -> "AbstractMetadataRepository":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
