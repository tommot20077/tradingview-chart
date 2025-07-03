"""Abstract data provider interface.

This module defines the abstract base class for data providers, establishing
a standardized interface for interacting with various financial data sources.
It includes methods for connecting, disconnecting, streaming real-time data
(trades, klines), fetching historical data, and retrieving exchange/symbol
information.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade


class AbstractDataProvider(ABC):
    """Abstract interface for a data provider.

    This abstract base class defines the contract for any data provider
    implementation, ensuring a consistent way to interact with various
    financial data sources. It covers real-time streaming, historical data
    fetching, and exchange/symbol information retrieval.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the data provider (e.g., "Binance", "Coinbase")."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establishes a connection to the data provider.

        This method should handle all necessary setup, such as establishing
        websocket connections or initializing API clients.

        Raises:
            ConnectionError: If the connection fails.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes the connection to the data provider.

        This method should release any resources held by the provider.

        Raises:
            ConnectionError: If disconnection fails.
        """

    @abstractmethod
    def stream_trades(
        self,
        symbol: str,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Trade]:
        """Streams real-time trade data for a given symbol.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT").
            start_from: Optional. If provided, attempts to stream trades from this timestamp.
                        Behavior may vary by provider (e.g., some may not support historical streaming).

        Yields:
            `Trade` objects as they are received from the data source.

        Raises:
            StreamError: If there is an issue with the data stream.
            NotSupportedError: If the provider does not support trade streaming.
        """
        pass

    @abstractmethod
    def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Kline]:
        """Streams real-time Kline (candlestick) data for a given symbol and interval.

        Args:
            symbol: The trading symbol.
            interval: The desired Kline interval (e.g., `KlineInterval.ONE_MINUTE`).
            start_from: Optional. If provided, attempts to stream klines from this timestamp.
                        Behavior may vary by provider.

        Yields:
            `Kline` objects as they are received from the data source.

        Raises:
            StreamError: If there is an issue with the data stream.
            NotSupportedError: If the provider does not support kline streaming.
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
        """Fetches historical trade data for a specified period.

        Args:
            symbol: The trading symbol.
            start_time: The inclusive start of the time range.
            end_time: The exclusive end of the time range.
            limit: Optional. The maximum number of trades to fetch.

        Returns:
            A list of `Trade` objects within the specified range.

        Raises:
            DataFetchError: If historical data cannot be retrieved.
            NotSupportedError: If the provider does not support historical trade fetching.
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
        """Fetches historical Kline data for a specified period and interval.

        Args:
            symbol: The trading symbol.
            interval: The Kline interval.
            start_time: The inclusive start of the time range.
            end_time: The exclusive end of the time range.
            limit: Optional. The maximum number of klines to fetch.

        Returns:
            A list of `Kline` objects within the specified range.

        Raises:
            DataFetchError: If historical data cannot be retrieved.
            NotSupportedError: If the provider does not support historical kline fetching.
        """
        pass

    @abstractmethod
    async def get_exchange_info(self) -> dict[str, Any]:
        """Retrieves general information about the exchange.

        This can include supported symbols, trading rules, rate limits, etc.

        Returns:
            A dictionary containing exchange information.

        Raises:
            DataFetchError: If exchange information cannot be retrieved.
        """
        pass

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Retrieves detailed information for a specific trading symbol.

        This can include price precision, quantity precision, minimum/maximum
        order sizes, etc.

        Args:
            symbol: The trading symbol.

        Returns:
            A dictionary containing symbol-specific information.

        Raises:
            DataFetchError: If symbol information cannot be retrieved.
            SymbolNotFoundError: If the symbol is not found.
        """
        pass

    @abstractmethod
    async def ping(self) -> float:
        """Pings the data provider to check connectivity and measure latency.

        Returns:
            The latency in milliseconds.

        Raises:
            ConnectionError: If the ping fails.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes all connections and cleans up resources held by the provider.

        This method should be called to gracefully shut down the provider.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Indicates whether the provider is currently connected to its data source."""
        pass

    async def __aenter__(self) -> "AbstractDataProvider":
        """Enters the asynchronous context, connecting to the data provider."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the asynchronous context, ensuring the provider is closed."""
        await self.close()
