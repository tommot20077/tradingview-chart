"""Abstract data provider interface."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from ..models.kline import Kline, KlineInterval
from ..models.trade import Trade


class AbstractDataProvider(ABC):
    """Abstract interface for data provider implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the data provider."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data provider."""
        pass

    @abstractmethod
    async def stream_trades(
        self,
        symbol: str,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream real-time trades.

        Args:
            symbol: Trading pair symbol
            start_from: Optional timestamp to start streaming from

        Yields:
            Trade objects as they arrive
        """
        pass

    @abstractmethod
    async def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Kline]:
        """Stream real-time klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_from: Optional timestamp to start streaming from

        Yields:
            Kline objects as they arrive
        """
        pass

    @abstractmethod
    async def fetch_historical_trades(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Trade]:
        """Fetch historical trades.

        Args:
            symbol: Trading pair symbol
            start_time: Start time (inclusive)
            end_time: End time (exclusive)
            limit: Optional maximum number of trades to fetch

        Returns:
            List of historical trades
        """
        pass

    @abstractmethod
    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Kline]:
        """Fetch historical klines.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (exclusive)
            limit: Optional maximum number of klines to fetch

        Returns:
            List of historical klines
        """
        pass

    @abstractmethod
    async def get_exchange_info(self) -> dict[str, Any]:
        """Get exchange information.

        Returns:
            Exchange information including supported symbols, limits, etc.
        """
        pass

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Get information for a specific symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Symbol information including price/quantity precision, limits, etc.
        """
        pass

    @abstractmethod
    async def ping(self) -> float:
        """Ping the provider to check connectivity.

        Returns:
            Latency in milliseconds
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close all connections and clean up resources."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if provider is connected."""
        pass

    async def __aenter__(self) -> "AbstractDataProvider":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
