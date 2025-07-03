"""Abstract metadata repository interface.

This module defines the abstract base class for metadata repositories.
Metadata repositories are used to store and retrieve arbitrary key-value
pairs, often used for configuration, synchronization status, or other
on-demand data that doesn't fit into structured data models like Klines or Trades.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class AbstractMetadataRepository(ABC):
    """Abstract interface for a repository managing key-value metadata.

    This repository stores and retrieves arbitrary key-value pairs, which are
    typically used for storing configuration, synchronization status, backfill
    progress, and other operational metadata.
    """

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Sets or updates a value for a given key.

        If the key already exists, its value will be overwritten.

        Args:
            key: The unique key for the metadata entry.
            value: The JSON-serializable dictionary to store.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieves the value associated with a given key.

        Args:
            key: The key of the metadata to retrieve.

        Returns:
            The deserialized dictionary value, or `None` if the key is not found.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Checks if a key exists in the repository.

        Args:
            key: The key to check.

        Returns:
            `True` if the key exists, `False` otherwise.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletes a key-value pair from the repository.

        Args:
            key: The key to delete.

        Returns:
            `True` if the key was found and deleted, `False` otherwise.

        Raises:
            StorageError: If the deletion fails.
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: str | None = None) -> list[str]:
        """Lists all keys, optionally filtering by a prefix.

        Args:
            prefix: If provided, only keys starting with this prefix will be returned.

        Returns:
            A list of keys matching the prefix.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def set_with_ttl(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Sets a key-value pair with a Time-To-Live (TTL).

        The entry will automatically expire and be removed after the specified duration.

        Args:
            key: The unique key for the metadata entry.
            value: The JSON-serializable dictionary to store.
            ttl_seconds: The time-to-live for the entry, in seconds.

        Raises:
            StorageError: If the operation fails.
            NotSupportedError: If the backend does not support TTL.
        """
        pass

    @abstractmethod
    async def get_last_sync_time(
        self,
        symbol: str,
        data_type: str,
    ) -> datetime | None:
        """Retrieves the last synchronization timestamp for a specific data type and symbol.

        This is a convenience method, likely implemented on top of `get`.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT").
            data_type: The type of data that was synced (e.g., "trades", "klines_1m").

        Returns:
            The `datetime` of the last sync, or `None` if no sync has occurred.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def set_last_sync_time(
        self,
        symbol: str,
        data_type: str,
        timestamp: datetime,
    ) -> None:
        """Sets the last synchronization timestamp for a specific data type and symbol.

        This is a convenience method, likely implemented on top of `set`.

        Args:
            symbol: The trading symbol.
            data_type: The type of data being synced.
            timestamp: The timestamp of the last successful sync.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def get_backfill_status(
        self,
        symbol: str,
        data_type: str,
    ) -> dict[str, Any] | None:
        """Retrieves the backfill status for a given data type and symbol.

        The status can include progress, last attempted timestamp, errors, etc.

        Args:
            symbol: The trading symbol.
            data_type: The type of data being backfilled.

        Returns:
            A dictionary containing the backfill status, or `None` if no status exists.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def set_backfill_status(
        self,
        symbol: str,
        data_type: str,
        status: dict[str, Any],
    ) -> None:
        """Sets or updates the backfill status.

        Args:
            symbol: The trading symbol.
            data_type: The type of data being backfilled.
            status: A dictionary containing the current backfill status.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes the repository and releases any underlying resources.

        This method should be called to gracefully shut down the repository,
        closing database connections or file handles.
        """
        pass

    async def __aenter__(self) -> "AbstractMetadataRepository":
        """Enters the asynchronous context, returning the repository instance."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the asynchronous context, ensuring the repository is closed."""
        await self.close()
