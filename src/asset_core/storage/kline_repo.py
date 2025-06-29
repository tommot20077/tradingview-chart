"""Abstract kline repository interface.

This module defines the abstract base class for Kline (candlestick) data
repositories. It provides a standardized interface for storing, querying,
streaming, and managing historical and real-time Kline data, enabling
various storage backends to be used interchangeably.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from asset_core.models.kline import Kline, KlineInterval


class QueryOptions:
    """Options for querying klines.

    This class encapsulates various parameters that can be used to refine
    Kline data queries, such as limiting results, offsetting, ordering,
    and including additional metadata.

    Attributes:
        limit (int | None): The maximum number of results to return.
        offset (int | None): The number of results to skip from the beginning.
        order_by (str): The field by which to order the results (e.g., "open_time").
        order_desc (bool): If True, results are ordered in descending order; otherwise, ascending.
        include_metadata (bool): If True, additional metadata associated with Klines will be included.
    """

    def __init__(
        self,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str = "open_time",
        order_desc: bool = False,
        include_metadata: bool = False,
    ) -> None:
        """Initializes a new instance of `QueryOptions`.

        Args:
            limit (int | None): Optional. The maximum number of Kline results to retrieve.
                                If `None`, no limit is applied.
            offset (int | None): Optional. The number of Kline results to skip from the beginning.
                                 Useful for pagination. If `None`, no offset is applied.
            order_by (str): Optional. The field name to use for ordering the results.
                            Defaults to "open_time".
            order_desc (bool): Optional. If `True`, results are ordered in descending order.
                               If `False`, results are ordered in ascending order. Defaults to `False`.
            include_metadata (bool): Optional. If `True`, additional metadata associated with each
                                     Kline will be included in the results. Defaults to `False`.
        """
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self.order_desc = order_desc
        self.include_metadata = include_metadata


class AbstractKlineRepository(ABC):
    """Abstract interface for a repository managing Kline data.

    This abstract base class defines a standard contract for Kline (candlestick)
    data storage and retrieval. It supports operations like saving, querying,
    streaming, and deleting Kline data, as well as more advanced features like
    gap detection and statistical analysis.
    """

    @abstractmethod
    async def save(self, kline: Kline) -> None:
        """Saves a single Kline object to the repository.

        This method is idempotent. If a Kline with the same symbol, interval,
        and open time already exists, it will be overwritten.

        Args:
            kline: The `Kline` object to save.

        Raises:
            StorageError: If the operation fails due to a backend issue.
        """
        pass

    @abstractmethod
    async def save_batch(self, klines: list[Kline]) -> int:
        """Saves a batch of Kline objects in a single transaction.

        This method is designed for efficient bulk insertion of Kline data.
        Like `save`, this operation should be idempotent.

        Args:
            klines: A list of `Kline` objects to save.

        Returns:
            The number of klines successfully saved.

        Raises:
            StorageError: If the batch operation fails.
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
        """Queries for Kline data within a specified time range.

        Args:
            symbol: The trading symbol to query (e.g., "BTCUSDT").
            interval: The Kline interval (e.g., KlineInterval.ONE_MINUTE).
            start_time: The inclusive start of the time range.
            end_time: The exclusive end of the time range.
            options: Optional `QueryOptions` to customize the query (e.g., limit, order).

        Returns:
            A list of `Kline` objects matching the query criteria.

        Raises:
            InvalidQueryError: If the query parameters are invalid.
            StorageError: If the operation fails.
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
        """Streams Kline data for a given time range, yielding results iteratively.

        This method is useful for processing large datasets that may not fit into memory.

        Args:
            symbol: The trading symbol to stream (e.g., "BTCUSDT").
            interval: The Kline interval.
            start_time: The inclusive start of the time range.
            end_time: The exclusive end of the time range.
            batch_size: The number of klines to fetch from the database in each batch.

        Yields:
            An asynchronous iterator of `Kline` objects.

        Raises:
            StorageError: If the streaming operation fails.
        """
        pass

    @abstractmethod
    async def get_latest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Retrieves the most recent Kline for a given symbol and interval.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.

        Returns:
            The latest `Kline` object, or `None` if no data exists.

        Raises:
            StorageError: If the operation fails.
        """
        pass

    @abstractmethod
    async def get_oldest(
        self,
        symbol: str,
        interval: KlineInterval,
    ) -> Kline | None:
        """Retrieves the earliest Kline for a given symbol and interval.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.

        Returns:
            The oldest `Kline` object, or `None` if no data exists.

        Raises:
            StorageError: If the operation fails.
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
        """Counts the number of Klines for a given symbol and interval.

        If a time range is provided, the count is restricted to that range.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.
            start_time: Optional inclusive start of the time range.
            end_time: Optional exclusive end of the time range.

        Returns:
            The total number of `Kline` objects matching the criteria.

        Raises:
            StorageError: If the operation fails.
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
        """Deletes Kline data within a specified time range.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.
            start_time: The inclusive start of the time range for deletion.
            end_time: The exclusive end of the time range for deletion.

        Returns:
            The number of klines that were deleted.

        Raises:
            StorageError: If the deletion fails.
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
        """Identifies and returns any time gaps in the Kline data.

        A gap is a period where klines are expected but are missing from storage.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.
            start_time: The inclusive start of the time range to check for gaps.
            end_time: The exclusive end of the time range to check for gaps.

        Returns:
            A list of tuples, where each tuple contains the start and end
            datetime of a detected gap.

        Raises:
            StorageError: If the operation fails.
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
        """Retrieves statistical information about the stored Kline data.

        Statistics can include total count, date ranges, and other
        backend-specific metrics.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.
            start_time: Optional inclusive start of the time range.
            end_time: Optional exclusive end of the time range.

        Returns:
            A dictionary containing statistical data.

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

    async def __aenter__(self) -> "AbstractKlineRepository":
        """Enters the asynchronous context, returning the repository instance."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the asynchronous context, ensuring the repository is closed."""
        await self.close()
