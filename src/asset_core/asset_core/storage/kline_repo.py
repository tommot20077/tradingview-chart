"""Abstract kline repository interface."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from ..models.kline import Kline, KlineInterval


class QueryOptions:
    """Options for querying klines."""

    def __init__(
        self,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str = "open_time",
        order_desc: bool = False,
        include_metadata: bool = False,
    ) -> None:
        """Initialize query options.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Whether to order descending
            include_metadata: Whether to include metadata
        """
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self.order_desc = order_desc
        self.include_metadata = include_metadata


class AbstractKlineRepository(ABC):
    """Abstract interface for kline storage implementations."""

    @abstractmethod
    async def save(self, kline: Kline) -> None:
        """Save a single kline.

        Args:
            kline: Kline to save
        """
        pass

    @abstractmethod
    async def save_batch(self, klines: list[Kline]) -> int:
        """Save multiple klines in a batch.

        Args:
            klines: List of klines to save

        Returns:
            Number of klines successfully saved
        """
        pass

    @abstractmethod
    async def query(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        options: QueryOptions | None = None,
    ) -> list[Kline]:
        """Query klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (exclusive)
            options: Optional query options

        Returns:
            List of klines matching the query
        """
        pass

    @abstractmethod
    async def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,
    ) -> AsyncIterator[Kline]:
        """Stream klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (exclusive)
            batch_size: Number of klines to fetch per batch

        Yields:
            Klines matching the query
        """
        pass

    @abstractmethod
    async def get_latest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Get the latest kline.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval

        Returns:
            Latest kline or None if not found
        """
        pass

    @abstractmethod
    async def get_oldest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Get the oldest kline.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval

        Returns:
            Oldest kline or None if not found
        """
        pass

    @abstractmethod
    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Optional start time (inclusive)
            end_time: Optional end time (exclusive)

        Returns:
            Number of klines
        """
        pass

    @abstractmethod
    async def delete(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (exclusive)

        Returns:
            Number of klines deleted
        """
        pass

    @abstractmethod
    async def get_gaps(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Find gaps in kline data.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (exclusive)

        Returns:
            List of (gap_start, gap_end) tuples
        """
        pass

    @abstractmethod
    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get statistics about stored klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Optional start time (inclusive)
            end_time: Optional end time (exclusive)

        Returns:
            Dictionary with statistics (count, date range, etc.)
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the repository and clean up resources."""
        pass

    async def __aenter__(self) -> "AbstractKlineRepository":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
