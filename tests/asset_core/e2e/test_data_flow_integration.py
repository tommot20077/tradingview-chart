"""End-to-end integration tests for data flow.

This module tests the complete data flow pipeline from raw data ingestion
through processing, event publishing, storage, and downstream consumption,
ensuring all components work together correctly.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asset_core.events.bus import AbstractEventBus
from asset_core.models.events import BaseEvent, EventType, KlineEvent, TradeEvent
from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide
from asset_core.providers.base import AbstractDataProvider
from asset_core.storage.kline_repo import AbstractKlineRepository, QueryOptions


class MockDataProvider(AbstractDataProvider):
    """Mock data provider for testing.

    Description of what the class covers:
    This mock implementation of `AbstractDataProvider` is used for testing purposes.
    It simulates a data provider by allowing trades and klines to be added manually
    and then streamed or fetched, without requiring actual network connections.

    Preconditions:
    - Inherits from `AbstractDataProvider`.

    Steps:
    - Initializes with an optional name.
    - Provides properties for `name` and `is_connected` status.
    - Implements `connect` and `disconnect` methods to toggle connection status.
    - Implements `stream_trades` and `stream_klines` to yield pre-added mock data.
    - Implements `fetch_historical_trades` and `fetch_historical_klines` for historical data retrieval.
    - Implements `get_exchange_info`, `get_symbol_info`, `ping`, and `close` for completeness.
    - Provides `add_mock_trade` and `add_mock_kline` methods to populate internal data lists.

    Expected Result:
    - Behaves like a data provider for testing, allowing controlled injection and retrieval of data.
    - Simulates asynchronous operations with small delays.
    """

    def __init__(self, name: str = "mock_provider") -> None:
        self._name = name
        self._connected = False
        self._trades: list[Trade] = []
        self._klines: list[Kline] = []

    @property
    def name(self) -> str:
        """Get the name of the mock data provider.

        Description of what the property covers:
        This property returns the name assigned to the mock data provider instance.

        Preconditions:
        - The `MockDataProvider` instance has been initialized.

        Steps:
        - Access the `name` property of the `MockDataProvider` instance.

        Expected Result:
        - The string representing the provider's name is returned.
        """
        return self._name

    @property
    def is_connected(self) -> bool:
        """Get the connection status of the mock data provider.

        Description of what the property covers:
        This property indicates whether the mock data provider is currently connected.

        Preconditions:
        - The `MockDataProvider` instance has been initialized.

        Steps:
        - Access the `is_connected` property of the `MockDataProvider` instance.

        Expected Result:
        - A boolean value indicating the connection status (`True` if connected, `False` otherwise) is returned.
        """
        return self._connected

    async def connect(self) -> None:
        """Simulate connecting the mock data provider.

        Description of what the method covers:
        This asynchronous method simulates the process of connecting to a data provider.
        It sets the internal `_connected` flag to `True`.

        Preconditions:
        - The `MockDataProvider` instance is initialized.

        Steps:
        - Call the `connect` method.
        - Set the internal `_connected` flag to `True`.

        Expected Result:
        - The provider's `is_connected` status becomes `True`.
        """
        self._connected = True

    async def disconnect(self) -> None:
        """Simulate disconnecting the mock data provider.

        Description of what the method covers:
        This asynchronous method simulates the process of disconnecting from a data provider.
        It sets the internal `_connected` flag to `False`.

        Preconditions:
        - The `MockDataProvider` instance is initialized.

        Steps:
        - Call the `disconnect` method.
        - Set the internal `_connected` flag to `False`.

        Expected Result:
        - The provider's `is_connected` status becomes `False`.
        """
        self._connected = False

    async def stream_trades(self, symbol: str, *, start_from: datetime | None = None) -> AsyncIterator[Trade]:  # noqa: ARG002
        """Simulate streaming trades for a given symbol.

        Description of what the method covers:
        This asynchronous generator method simulates a real-time trade stream.
        It yields pre-added mock `Trade` objects that match the specified symbol.

        Preconditions:
        - The mock provider must be connected (`is_connected` is True).
        - Mock `Trade` objects have been added using `add_mock_trade`.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT") for which to stream trades.
            start_from: Optional. A `datetime` object to start streaming trades from.
                        (Currently not fully implemented in mock, yields all matching trades).

        Yields:
            An `AsyncIterator` of `Trade` objects.

        Raises:
            ConnectionError: If the provider is not connected.

        Expected Result:
        - Yields `Trade` objects matching the symbol.
        - Introduces a small delay to simulate real-time streaming.
        - Raises `ConnectionError` if not connected.
        """
        if not self._connected:
            raise ConnectionError("Provider not connected")

        for trade in self._trades:
            if trade.symbol == symbol:
                yield trade
                await asyncio.sleep(0.001)

    async def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,  # noqa: ARG002
    ) -> AsyncIterator[Kline]:
        """Simulate streaming klines for a given symbol and interval.

        Description of what the method covers:
        This asynchronous generator method simulates a real-time kline stream.
        It yields pre-added mock `Kline` objects that match the specified symbol and interval.

        Preconditions:
        - The mock provider must be connected (`is_connected` is True).
        - Mock `Kline` objects have been added using `add_mock_kline`.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT") for which to stream klines.
            interval: The `KlineInterval` (e.g., `MINUTE_1`) for the klines.
            start_from: Optional. A `datetime` object to start streaming klines from.
                        (Currently not fully implemented in mock, yields all matching klines).

        Yields:
            An `AsyncIterator` of `Kline` objects.

        Raises:
            ConnectionError: If the provider is not connected.

        Expected Result:
        - Yields `Kline` objects matching the symbol and interval.
        - Introduces a small delay to simulate real-time streaming.
        - Raises `ConnectionError` if not connected.
        """

        async def generator() -> AsyncIterator[Kline]:
            if not self._connected:
                raise ConnectionError("Provider not connected")

            for kline in self._klines:
                if kline.symbol == symbol and kline.interval == interval:
                    yield kline
                    await asyncio.sleep(0.001)

        async for kline in generator():
            yield kline

    async def fetch_historical_trades(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,  # noqa: ARG002
    ) -> list[Trade]:
        """Simulate fetching historical trades for a given symbol within a time range.

        Description of what the method covers:
        This asynchronous method simulates fetching historical `Trade` objects.
        It returns a list of pre-added mock trades that fall within the specified
        time range and match the given symbol.

        Preconditions:
        - Mock `Trade` objects have been added using `add_mock_trade`.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT") for which to fetch historical trades.
            start_time: The `datetime` object representing the start of the historical period.
            end_time: The `datetime` object representing the end of the historical period.
            limit: Optional. The maximum number of trades to return.
                   (Currently not fully implemented in mock, returns all matching trades).

        Returns:
            A list of `Trade` objects matching the criteria.

        Expected Result:
        - Returns `Trade` objects that are within the specified symbol and time range.
        """
        return [t for t in self._trades if t.symbol == symbol and start_time <= t.timestamp < end_time]

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,  # noqa: ARG002
    ) -> list[Kline]:
        """Simulate fetching historical klines for a given symbol and interval within a time range.

        Description of what the method covers:
        This asynchronous method simulates fetching historical `Kline` objects.
        It returns a list of pre-added mock klines that fall within the specified
        time range and match the given symbol and interval.

        Preconditions:
        - Mock `Kline` objects have been added using `add_mock_kline`.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT") for which to fetch historical klines.
            interval: The `KlineInterval` (e.g., `MINUTE_1`) for the klines.
            start_time: The `datetime` object representing the start of the historical period.
            end_time: The `datetime` object representing the end of the historical period.
            limit: Optional. The maximum number of klines to return.
                   (Currently not fully implemented in mock, returns all matching klines).

        Returns:
            A list of `Kline` objects matching the criteria.

        Expected Result:
        - Returns `Kline` objects that are within the specified symbol, interval, and time range.
        """
        return [
            k
            for k in self._klines
            if k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time
        ]

    async def get_exchange_info(self) -> dict[str, Any]:
        """Simulate fetching exchange information.

        Description of what the method covers:
        This asynchronous method simulates retrieving general information about the exchange,
        including its name and supported symbols.

        Preconditions:
        - The mock provider is initialized.

        Returns:
            A dictionary containing mock exchange information.

        Expected Result:
        - Returns a dictionary with the exchange's name and a list of supported symbols.
        """
        return {"name": self._name, "symbols": ["BTCUSDT", "ETHUSDT"]}

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Simulate fetching information for a specific trading symbol.

        Description of what the method covers:
        This asynchronous method simulates retrieving detailed information about a given trading symbol.

        Preconditions:
        - The mock provider is initialized.

        Args:
            symbol: The trading symbol (e.g., "BTCUSDT") for which to fetch information.

        Returns:
            A dictionary containing mock symbol information.

        Expected Result:
        - Returns a dictionary with the symbol's name and its trading status.
        """
        return {"symbol": symbol, "status": "TRADING"}

    async def ping(self) -> float:
        """Simulate a ping operation to measure latency.

        Description of what the method covers:
        This asynchronous method simulates sending a ping request to the data provider
        and returning a mock latency value.

        Preconditions:
        - The mock provider is initialized.

        Returns:
            A float representing the simulated latency in milliseconds.

        Expected Result:
        - Returns a fixed float value (e.g., 10.0) representing mock latency.
        """
        return 10.0

    async def close(self) -> None:
        """Simulate closing the mock data provider connection.

        Description of what the method covers:
        This asynchronous method simulates closing the connection to the data provider.
        It sets the internal `_connected` flag to `False`.

        Preconditions:
        - The `MockDataProvider` instance is initialized.

        Steps:
        - Call the `close` method.
        - Set the internal `_connected` flag to `False`.

        Expected Result:
        - The provider's `is_connected` status becomes `False`.
        """
        self._connected = False

    def add_mock_trade(self, trade: Trade) -> None:
        """Add a mock trade for testing.

        Description of what the method covers:
        This method adds a `Trade` object to the internal list of mock trades.
        These trades can then be streamed or fetched by other methods.

        Preconditions:
        - The `MockDataProvider` instance is initialized.
        - `Trade` object is a valid instance.

        Args:
            trade: The `Trade` object to add to the mock data.

        Expected Result:
        - The `Trade` object is successfully added to the provider's internal trade list.
        """
        self._trades.append(trade)

    def add_mock_kline(self, kline: Kline) -> None:
        """Add a mock kline for testing.

        Description of what the method covers:
        This method adds a `Kline` object to the internal list of mock klines.
        These klines can then be streamed or fetched by other methods.

        Preconditions:
        - The `MockDataProvider` instance is initialized.
        - `Kline` object is a valid instance.

        Args:
            kline: The `Kline` object to add to the mock data.

        Expected Result:
        - The `Kline` object is successfully added to the provider's internal kline list.
        """
        self._klines.append(kline)


class MockKlineRepository(AbstractKlineRepository):
    """Mock kline repository for testing.

    Description of what the class covers:
    This mock implementation of `AbstractKlineRepository` simulates a data store
    for `Kline` objects. It provides in-memory storage and basic CRUD operations
    (save, query, delete) for testing purposes, without requiring a real database.

    Preconditions:
    - Inherits from `AbstractKlineRepository`.

    Steps:
    - Initializes with an empty dictionary to store klines, keyed by a tuple of (symbol, interval, open_time).
    - Implements `save` to store a single kline.
    - Implements `save_batch` to store multiple klines.
    - Implements `query` to retrieve klines within a specified time range.
    - Implements `stream` to yield klines from a query.
    - Implements `get_latest` and `get_oldest` to retrieve boundary klines.
    - Implements `count` to return the number of stored klines matching criteria.
    - Implements `delete` to remove klines within a time range.
    - Implements `get_gaps` (simplified to return empty list for mock).
    - Implements `get_statistics` to return basic kline statistics.
    - Implements `close` to simulate closing the repository.

    Expected Result:
    - Behaves like a kline repository for testing, allowing controlled storage and retrieval of kline data.
    - Supports basic querying and data management operations.
    """

    def __init__(self) -> None:
        self._klines: dict[tuple[str, KlineInterval, datetime], Kline] = {}
        self._closed = False

    async def save(self, kline: Kline) -> None:
        """Save a single Kline object to the repository.

        Description of what the method covers:
        This asynchronous method simulates saving a single `Kline` object into the
        in-memory repository. It uses a tuple of (symbol, interval, open_time) as the key.

        Preconditions:
        - The `MockKlineRepository` instance is initialized and not closed.
        - `kline` is a valid `Kline` object.

        Args:
            kline: The `Kline` object to be saved.

        Raises:
            RuntimeError: If the repository is closed.

        Expected Result:
        - The `Kline` object is successfully stored in the repository.
        """
        if self._closed:
            raise RuntimeError("Repository is closed")
        key = (kline.symbol, kline.interval, kline.open_time)
        self._klines[key] = kline

    async def save_batch(self, klines: list[Kline]) -> int:
        """Save a batch of Kline objects to the repository.

        Description of what the method covers:
        This asynchronous method simulates saving multiple `Kline` objects into the
        in-memory repository by iterating through the list and calling the `save` method for each.

        Preconditions:
        - The `MockKlineRepository` instance is initialized and not closed.
        - `klines` is a list of valid `Kline` objects.

        Args:
            klines: A list of `Kline` objects to be saved.

        Returns:
            The number of klines successfully saved.

        Raises:
            RuntimeError: If the repository is closed.

        Expected Result:
        - All `Kline` objects in the batch are successfully stored in the repository.
        - The returned count matches the number of klines provided in the batch.
        """
        if self._closed:
            raise RuntimeError("Repository is closed")
        count = 0
        for kline in klines:
            await self.save(kline)
            count += 1
        return count

    async def query(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        options: QueryOptions | None = None,  # noqa: ARG002
    ) -> list[Kline]:
        """Query kline objects from the repository within a specified time range.

        Description of what the method covers:
        This asynchronous method simulates querying `Kline` objects from the in-memory
        repository based on symbol, interval, and a time range. It returns a sorted
        list of matching klines.

        Preconditions:
        - The `MockKlineRepository` instance is initialized and not closed.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to query klines.
            interval: The `KlineInterval` for the klines.
            start_time: The `datetime` object representing the start of the query period.
            end_time: The `datetime` object representing the end of the query period.
            options: Optional. Additional query options (not used in mock).

        Returns:
            A list of `Kline` objects matching the criteria, sorted by `open_time`.

        Raises:
            RuntimeError: If the repository is closed.

        Expected Result:
        - Returns a list of `Kline` objects that fall within the specified symbol, interval, and time range.
        - The results are sorted chronologically by `open_time`.
        """
        if self._closed:
            raise RuntimeError("Repository is closed")

        results = []
        for (s, i, t), kline in self._klines.items():
            if s == symbol and i == interval and start_time <= t < end_time:
                results.append(kline)

        return sorted(results, key=lambda k: k.open_time)

    def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,  # noqa: ARG002
    ) -> AsyncIterator[Kline]:
        """Stream kline objects from the repository within a specified time range.

        Description of what the method covers:
        This asynchronous generator method simulates streaming `Kline` objects from the
        in-memory repository. It first queries all matching klines and then yields them one by one.

        Preconditions:
        - The `MockKlineRepository` instance is initialized and not closed.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to stream klines.
            interval: The `KlineInterval` for the klines.
            start_time: The `datetime` object representing the start of the stream period.
            end_time: The `datetime` object representing the end of the stream period.
            batch_size: Optional. The number of klines to yield in a batch (not fully implemented in mock).

        Yields:
            An `AsyncIterator` of `Kline` objects.

        Expected Result:
        - Yields `Kline` objects that fall within the specified symbol, interval, and time range.
        - Klines are yielded in chronological order.
        """

        async def _stream() -> AsyncIterator[Kline]:
            results = await self.query(symbol, interval, start_time, end_time)
            for kline in results:
                yield kline

        return _stream()

    async def get_latest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Retrieve the latest Kline object for a given symbol and interval.

        Description of what the method covers:
        This asynchronous method simulates retrieving the most recent `Kline` object
        from the in-memory repository based on the provided symbol and interval.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to retrieve the latest kline.
            interval: The `KlineInterval` for the kline.

        Returns:
            The latest `Kline` object if found, otherwise `None`.

        Expected Result:
        - Returns the `Kline` object with the most recent `open_time` for the specified symbol and interval.
        - Returns `None` if no matching klines are found.
        """
        matching = [k for (s, i, _), k in self._klines.items() if s == symbol and i == interval]
        return max(matching, key=lambda k: k.open_time) if matching else None

    async def get_oldest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        """Retrieve the oldest Kline object for a given symbol and interval.

        Description of what the method covers:
        This asynchronous method simulates retrieving the oldest `Kline` object
        from the in-memory repository based on the provided symbol and interval.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to retrieve the oldest kline.
            interval: The `KlineInterval` for the kline.

        Returns:
            The oldest `Kline` object if found, otherwise `None`.

        Expected Result:
        - Returns the `Kline` object with the oldest `open_time` for the specified symbol and interval.
        - Returns `None` if no matching klines are found.
        """
        matching = [k for (s, i, _), k in self._klines.items() if s == symbol and i == interval]
        return min(matching, key=lambda k: k.open_time) if matching else None

    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count the number of Kline objects in the repository matching criteria.

        Description of what the method covers:
        This asynchronous method simulates counting `Kline` objects in the in-memory
        repository based on symbol, interval, and an optional time range.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to count klines.
            interval: The `KlineInterval` for the klines.
            start_time: Optional. The `datetime` object representing the start of the count period.
            end_time: Optional. The `datetime` object representing the end of the count period.

        Returns:
            The number of `Kline` objects matching the criteria.

        Expected Result:
        - Returns the correct count of `Kline` objects within the specified parameters.
        """
        if start_time is None and end_time is None:
            return len([k for (s, i, _), k in self._klines.items() if s == symbol and i == interval])

        start_time = start_time or datetime.min.replace(tzinfo=UTC)
        end_time = end_time or datetime.max.replace(tzinfo=UTC)

        return len(
            [k for (s, i, t), k in self._klines.items() if s == symbol and i == interval and start_time <= t < end_time]
        )

    async def delete(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete Kline objects from the repository within a specified time range.

        Description of what the method covers:
        This asynchronous method simulates deleting `Kline` objects from the in-memory
        repository based on symbol, interval, and a time range.

        Preconditions:
        - The `MockKlineRepository` instance is initialized and not closed.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to delete klines.
            interval: The `KlineInterval` for the klines.
            start_time: The `datetime` object representing the start of the deletion period.
            end_time: The `datetime` object representing the end of the deletion period.

        Returns:
            The number of klines successfully deleted.

        Raises:
            RuntimeError: If the repository is closed.

        Expected Result:
        - `Kline` objects within the specified parameters are removed from the repository.
        - The returned count matches the number of klines deleted.
        """
        if self._closed:
            raise RuntimeError("Repository is closed")

        to_delete = [
            key
            for key, kline in self._klines.items()
            if (key[0] == symbol and key[1] == interval and start_time <= key[2] < end_time)
        ]

        for key in to_delete:
            del self._klines[key]

        return len(to_delete)

    async def get_gaps(
        self,
        _symbol: str,
        _interval: KlineInterval,
        _start_time: datetime,
        _end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Simulate retrieving gaps in kline data for a given symbol and interval.

        Description of what the method covers:
        This asynchronous method is a simplified mock implementation that always returns
        an empty list, simulating no gaps in the test data. In a real repository,
        it would identify missing klines within a specified time range.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.

        Args:
            symbol: The trading symbol for which to find gaps.
            interval: The `KlineInterval` for the klines.
            start_time: The `datetime` object representing the start of the period to check for gaps.
            end_time: The `datetime` object representing the end of the period to check for gaps.

        Returns:
            An empty list of tuples, where each tuple would represent a (start_time, end_time) of a gap.

        Expected Result:
        - Always returns an empty list, indicating no gaps in the mock data.
        """
        return []

    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Retrieve statistics about kline data for a given symbol and interval.

        Description of what the method covers:
        This asynchronous method simulates retrieving basic statistics for `Kline` objects
        in the in-memory repository. It currently returns the count of matching klines,
        along with the symbol and interval.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.
        - Klines have been saved to the repository.

        Args:
            symbol: The trading symbol for which to retrieve statistics.
            interval: The `KlineInterval` for the klines.
            start_time: Optional. The `datetime` object representing the start of the statistics period.
            end_time: Optional. The `datetime` object representing the end of the statistics period.

        Returns:
            A dictionary containing mock statistics (count, symbol, interval value).

        Expected Result:
        - Returns a dictionary with the count of klines, the symbol, and the interval value.
        """
        count = await self.count(symbol, interval, start_time, end_time)
        return {"count": count, "symbol": symbol, "interval": interval.value}

    async def close(self) -> None:
        """Simulate closing the kline repository.

        Description of what the method covers:
        This asynchronous method simulates closing the repository, setting an internal
        flag to indicate that the repository is no longer operational.

        Preconditions:
        - The `MockKlineRepository` instance is initialized.

        Steps:
        - Call the `close` method.
        - Set the internal `_closed` flag to `True`.

        Expected Result:
        - The repository's `_closed` status becomes `True`, preventing further operations.
        """
        self._closed = True


class MockEventBus(AbstractEventBus):
    """Mock event bus for testing.

    Description of what the class covers:
    This mock implementation of `AbstractEventBus` simulates an event publishing
    and subscription system. It stores events in memory and dispatches them to
    registered subscribers, allowing for controlled testing of event-driven flows.

    Preconditions:
    - Inherits from `AbstractEventBus`.

    Steps:
    - Initializes with empty lists/dictionaries for events and subscribers.
    - Implements `publish` to add events to an internal list and dispatch to subscribers.
    - Implements `subscribe` to register handlers for specific event types and optional symbols.
    - Implements `unsubscribe` to remove a specific subscription.
    - Implements `unsubscribe_all` to remove all or specific types of subscriptions.
    - Implements `close` to simulate closing the event bus.
    - Implements `get_subscription_count` to return the number of active subscriptions.
    - Implements `wait_for` (simplified) to retrieve a matching event.
    - Provides `is_closed` property to check the bus status.
    - Provides `get_published_events` to retrieve all events published during a test.

    Expected Result:
    - Behaves like an event bus for testing, allowing events to be published and consumed.
    - Supports subscription management and event filtering.
    - Provides methods to inspect published events and subscription counts.
    """

    def __init__(self) -> None:
        self._events: list[BaseEvent] = []
        self._subscribers: dict[str, tuple[EventType, Any, str | None]] = {}
        self._closed = False

    async def publish(self, event: BaseEvent) -> None:
        """Simulate publishing an event to the event bus.

        Description of what the method covers:
        This asynchronous method simulates publishing a `BaseEvent` to the event bus.
        It appends the event to an internal list and then dispatches it to all
        registered subscribers whose criteria match the event.

        Preconditions:
        - The `MockEventBus` instance is initialized and not closed.
        - `event` is a valid `BaseEvent` object.

        Args:
            event: The `BaseEvent` object to be published.

        Raises:
            RuntimeError: If the event bus is closed.

        Expected Result:
        - The event is added to the internal list of published events.
        - The event is dispatched to all matching subscribed handlers.
        """
        if self._closed:
            raise RuntimeError("Event bus is closed")
        self._events.append(event)

        for _sub_id, (event_type, handler, filter_symbol) in self._subscribers.items():
            if event.event_type == event_type and (filter_symbol is None or event.symbol == filter_symbol):
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

    def subscribe(
        self,
        event_type: EventType,
        handler: Any,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribe to events of a specific type, optionally filtered by symbol.

        Description of what the method covers:
        This method simulates subscribing to events on the event bus. It registers
        a handler function for a given `EventType` and returns a unique subscription ID.
        Optionally, a `filter_symbol` can be provided to receive events only for that symbol.

        Preconditions:
        - The `MockEventBus` instance is initialized.
        - `event_type` is a valid `EventType` enum member.
        - `handler` is a callable function or coroutine function.

        Args:
            event_type: The type of event to subscribe to.
            handler: The callable (function or coroutine function) that will be invoked when a matching event is published.
            filter_symbol: Optional. A string symbol to filter events by (e.g., "BTCUSDT").

        Returns:
            A unique string identifier for the new subscription.

        Expected Result:
        - A new subscription is successfully registered.
        - A unique subscription ID is returned.
        """
        sub_id = f"sub_{len(self._subscribers)}"
        self._subscribers[sub_id] = (event_type, handler, filter_symbol)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe a handler using its subscription ID.

        Description of what the method covers:
        This method removes a previously registered subscription from the event bus
        using its unique `subscription_id`.

        Preconditions:
        - The `MockEventBus` instance is initialized.
        - `subscription_id` is a valid ID returned by a prior `subscribe` call.

        Args:
            subscription_id: The unique identifier of the subscription to remove.

        Returns:
            `True` if the subscription was successfully removed, `False` otherwise.

        Expected Result:
        - The handler associated with the `subscription_id` is no longer invoked for published events.
        - Returns `True` if the subscription existed and was removed, `False` if not found.
        """
        return self._subscribers.pop(subscription_id, None) is not None

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Unsubscribe all handlers, or all handlers for a specific event type.

        Description of what the method covers:
        This method removes multiple subscriptions from the event bus. If `event_type`
        is provided, it removes all subscriptions for that specific type. If `event_type`
        is `None`, it removes all subscriptions from the bus.

        Preconditions:
        - The `MockEventBus` instance is initialized.

        Args:
            event_type: Optional. The `EventType` for which to unsubscribe all handlers.
                        If `None`, all subscriptions are removed.

        Returns:
            The number of subscriptions that were removed.

        Expected Result:
        - All matching subscriptions are removed from the event bus.
        - The returned count accurately reflects the number of removed subscriptions.
        """
        if event_type is None:
            count = len(self._subscribers)
            self._subscribers.clear()
            return count

        to_remove = [sub_id for sub_id, (et, _, _) in self._subscribers.items() if et == event_type]

        for sub_id in to_remove:
            del self._subscribers[sub_id]

        return len(to_remove)

    async def close(self) -> None:
        """Simulate closing the event bus.

        Description of what the method covers:
        This asynchronous method simulates closing the event bus, setting an internal
        flag to indicate that the bus is no longer operational and preventing further
        event publishing.

        Preconditions:
        - The `MockEventBus` instance is initialized.

        Steps:
        - Call the `close` method.
        - Set the internal `_closed` flag to `True`.

        Expected Result:
        - The event bus's `_closed` status becomes `True`, preventing further event publishing.
        """
        self._closed = True

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Get the number of active subscriptions, optionally filtered by event type.

        Description of what the method covers:
        This method returns the current number of active subscriptions on the event bus.
        If an `event_type` is provided, it returns the count of subscriptions for that
        specific event type; otherwise, it returns the total count of all subscriptions.

        Preconditions:
        - The `MockEventBus` instance is initialized.

        Args:
            event_type: Optional. The `EventType` to filter subscriptions by.

        Returns:
            The number of matching active subscriptions.

        Expected Result:
        - Returns an accurate count of subscriptions based on the provided filter.
        """
        if event_type is None:
            return len(self._subscribers)
        return len([1 for et, _, _ in self._subscribers.values() if et == event_type])

    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,  # noqa: ARG002
        filter_func: Callable[[BaseEvent], bool] | None = None,
    ) -> BaseEvent | None:
        """Simulate waiting for a specific event to be published.

        Description of what the method covers:
        This asynchronous method is a simplified mock implementation that checks if a
        matching event has already been published. In a real event bus, this would
        block until a matching event is received or a timeout occurs.

        Preconditions:
        - The `MockEventBus` instance is initialized.
        - `event_type` is a valid `EventType` enum member.

        Args:
            event_type: The type of event to wait for.
            timeout: Optional. The maximum time to wait for the event (not implemented in mock).
            filter_func: Optional. A callable to further filter the event (e.g., `lambda e: e.symbol == "BTC"`).

        Returns:
            The first `BaseEvent` object that matches the criteria, or `None` if not found.

        Expected Result:
        - Returns a matching event if it has been published.
        - Returns `None` if no matching event is found (without blocking).
        """
        for event in self._events:
            if event.event_type == event_type and (filter_func is None or filter_func(event)):
                return event
        return None

    @property
    def is_closed(self) -> bool:
        """Get the closed status of the event bus.

        Description of what the property covers:
        This property indicates whether the mock event bus is currently closed.

        Preconditions:
        - The `MockEventBus` instance has been initialized.

        Steps:
        - Access the `is_closed` property of the `MockEventBus` instance.

        Expected Result:
        - A boolean value indicating the closed status (`True` if closed, `False` otherwise) is returned.
        """
        return self._closed

    def get_published_events(self) -> list[BaseEvent]:
        """Get all published events for testing.

        Description of what the method covers:
        This method returns a copy of all `BaseEvent` objects that have been
        published to the mock event bus since its initialization. This is useful
        for asserting that specific events were published during a test run.

        Preconditions:
        - The `MockEventBus` instance is initialized.

        Returns:
            A list of `BaseEvent` objects that were published.

        Steps:
        - Call the `get_published_events` method.

        Expected Result:
        - Returns a list containing all `BaseEvent` objects that have been published.
        - The returned list is a copy, so modifications to it do not affect the internal state.
        """
        return self._events.copy()


class TestDataFlowIntegration:
    """Integration tests for complete data flow pipeline.

    Description of what the class covers:
    This test suite provides end-to-end integration tests for the entire data flow pipeline,
    from raw data ingestion (simulated by mock providers) through event publishing and
    consumption, to data storage and retrieval. It ensures that all components of the
    system (data providers, event bus, and repositories) work together seamlessly and correctly.

    Preconditions:
    - Mock implementations of `AbstractDataProvider`, `AbstractKlineRepository`, and
      `AbstractEventBus` are available and correctly configured.
    - The event system is set up for publishing and subscribing to various event types.
    - Storage systems (mock repositories) are accessible for data persistence.

    Steps:
    - Set up a complete data pipeline using mock components.
    - Inject test data at the entry points (e.g., mock provider streams).
    - Verify that data flows correctly through all intermediate stages (e.g., events are published).
    - Validate the final state of data in storage and the results of processing.

    Expected Result:
    - Data flows accurately and completely through all stages of the pipeline.
    - Events are properly published by producers and correctly consumed by subscribers.
    - Data storage operations (saving and querying) complete successfully.
    - No data loss, corruption, or inconsistencies occur during the end-to-end data flow.
    """

    @pytest.fixture
    def mock_provider(self) -> MockDataProvider:
        """Provide a mock data provider for testing.

        Description of what the fixture covers:
        This fixture provides an instance of `MockDataProvider` configured for testing.
        It simulates an external data source, allowing tests to control the data
        streamed and fetched without actual network dependencies.

        Preconditions:
        - The `MockDataProvider` class is defined and importable.

        Steps:
        - Instantiates `MockDataProvider` with a test exchange name.

        Expected Result:
        - A `MockDataProvider` instance ready for use in tests is returned.
        """
        return MockDataProvider("test_exchange")

    @pytest.fixture
    def mock_repository(self) -> MockKlineRepository:
        """Provide a mock kline repository for testing.

        Description of what the fixture covers:
        This fixture provides an instance of `MockKlineRepository` for testing.
        It simulates a data storage layer for `Kline` objects, allowing tests to
        save, query, and manage kline data in memory without a real database.

        Preconditions:
        - The `MockKlineRepository` class is defined and importable.

        Steps:
        - Instantiates `MockKlineRepository`.

        Expected Result:
        - A `MockKlineRepository` instance ready for use in tests is returned.
        """
        return MockKlineRepository()

    @pytest.fixture
    def mock_event_bus(self) -> MockEventBus:
        """Provide a mock event bus for testing.

        Description of what the fixture covers:
        This fixture provides an instance of `MockEventBus` for testing.
        It simulates an event-driven communication channel, allowing tests to
        publish and subscribe to events in memory.

        Preconditions:
        - The `MockEventBus` class is defined and importable.

        Steps:
        - Instantiates `MockEventBus`.

        Expected Result:
        - A `MockEventBus` instance ready for use in tests is returned.
        """
        return MockEventBus()

    @pytest.fixture
    def sample_trades(self) -> list[Trade]:
        """Provide sample trades for testing.

        Description of what the fixture covers:
        This fixture generates a list of sample `Trade` objects to be used in integration tests.
        It provides a consistent set of mock trade data for simulating data flow.

        Preconditions:
        - The `Trade` model is correctly defined and importable.
        - `Decimal` and `datetime` (with `UTC`) are available for data generation.

        Steps:
        - Initializes an empty list `trades`.
        - Defines a `base_time` for timestamps.
        - Loops 100 times to create individual `Trade` objects.
        - For each `Trade` object, assigns a unique `trade_id`, varies `price`,
          sets `quantity`, `side`, `timestamp`, and `exchange`.
        - Appends each created `Trade` object to the `trades` list.

        Returns:
            A list of 100 `Trade` objects.

        Expected Result:
        - A list containing 100 valid `Trade` objects with diverse data is returned.
        """
        base_time = datetime(2024, 1, 1, tzinfo=UTC)
        trades = []

        for i in range(100):
            trade = Trade(
                symbol="BTCUSDT",
                trade_id=f"trade_{i:03d}",
                price=Decimal(f"{50000 + i}"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY if i % 2 == 0 else TradeSide.SELL,
                timestamp=base_time + timedelta(seconds=i),
                exchange="test_exchange",
            )
            trades.append(trade)

        return trades

    @pytest.fixture
    def sample_klines(self) -> list[Kline]:
        """Provide sample klines for testing.

        Description of what the fixture covers:
        This fixture generates a list of sample `Kline` objects to be used in integration tests.
        It provides a consistent set of mock kline data for simulating data flow.

        Preconditions:
        - The `Kline` model is correctly defined and importable.
        - `Decimal`, `datetime` (with `UTC`), and `KlineInterval` are available for data generation.

        Steps:
        - Initializes an empty list `klines`.
        - Defines a `base_time` for timestamps.
        - Loops 50 times to create individual `Kline` objects.
        - For each `Kline` object, calculates `open_time`, `close_time`, and price-related fields.
        - Assigns `symbol`, `interval`, `volume`, `quote_volume`, `trades_count`, and `exchange`.
        - Appends each created `Kline` object to the `klines` list.

        Returns:
            A list of 50 `Kline` objects.

        Expected Result:
        - A list containing 50 valid `Kline` objects with diverse data is returned.
        """
        base_time = datetime(2024, 1, 1, tzinfo=UTC)
        klines = []

        for i in range(50):
            open_time = base_time + timedelta(minutes=i)
            close_time = open_time + timedelta(seconds=59)
            base_price = Decimal(f"{50000 + i * 10}")

            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=open_time,
                close_time=close_time,
                open_price=base_price,
                high_price=base_price + Decimal("50"),
                low_price=base_price - Decimal("30"),
                close_price=base_price + Decimal("20"),
                volume=Decimal("100"),
                quote_volume=Decimal("5000000"),
                trades_count=10,
                exchange="test_exchange",
            )
            klines.append(kline)

        return klines

    @pytest.mark.asyncio
    async def test_end_to_end_trade_processing(
        self, mock_provider: MockDataProvider, mock_event_bus: MockEventBus, sample_trades: list[Trade]
    ) -> None:
        """Test complete trade processing pipeline from provider to event system.

        Description of what the test covers:
        This test verifies the end-to-end pipeline for trade data processing.
        It simulates receiving trade data from a mock provider, publishing it
        through a mock event bus, and ensuring that subscribers correctly receive
        and process these events, maintaining data integrity throughout the flow.

        Preconditions:
        - `mock_provider` is configured with `sample_trades`.
        - `mock_event_bus` is ready for publishing and subscribing.
        - `sample_trades` fixture provides the necessary test data.

        Steps:
        - Add `sample_trades` to the `mock_provider`.
        - Initialize an empty list `received_events` to collect events from the subscriber.
        - Define a `trade_handler` function to append received `TradeEvent` objects to `received_events`.
        - Subscribe the `trade_handler` to `EventType.TRADE` events on the `mock_event_bus`,
          filtering by "BTCUSDT" symbol.
        - Connect the `mock_provider`.
        - Asynchronously iterate through trades streamed from the `mock_provider`.
        - For each trade, create a `TradeEvent` and publish it to the `mock_event_bus`.
        - After streaming, assert that the number of `received_events` matches the number of `sample_trades`.
        - Verify the data integrity of each received event, ensuring `event_type`, `source`,
          `symbol`, `trade_id`, `price`, and `quantity` match the original `sample_trades`.
        - Retrieve all published events from the `mock_event_bus` and verify their count and type.
        - In a `finally` block, unsubscribe the handler and disconnect the provider to clean up.

        Expected Result:
        - All trades are successfully streamed from the mock provider.
        - Corresponding `TradeEvent` objects are correctly published to the event bus.
        - The event subscriber receives all published trade events with accurate data.
        - Data integrity is maintained throughout the entire trade processing pipeline.
        """
        for trade in sample_trades:
            mock_provider.add_mock_trade(trade)

        received_events: list[TradeEvent] = []

        def trade_handler(event: BaseEvent) -> None:
            if isinstance(event, TradeEvent):
                received_events.append(event)

        subscription_id = mock_event_bus.subscribe(EventType.TRADE, trade_handler, filter_symbol="BTCUSDT")

        await mock_provider.connect()

        try:
            async for trade in mock_provider.stream_trades("BTCUSDT"):
                trade_event = TradeEvent(source=mock_provider.name, symbol=trade.symbol, data=trade)
                await mock_event_bus.publish(trade_event)

            assert len(received_events) == len(sample_trades)

            for i, event in enumerate(received_events):
                assert event.event_type == EventType.TRADE
                assert event.source == mock_provider.name
                assert event.symbol == "BTCUSDT"
                assert event.data.trade_id == sample_trades[i].trade_id
                assert event.data.price == sample_trades[i].price
                assert event.data.quantity == sample_trades[i].quantity

            published_events = mock_event_bus.get_published_events()
            assert len(published_events) == len(sample_trades)
            assert all(e.event_type == EventType.TRADE for e in published_events)

        finally:
            mock_event_bus.unsubscribe(subscription_id)
            await mock_provider.disconnect()

    @pytest.mark.asyncio
    async def test_kline_aggregation_flow(
        self, sample_trades: list[Trade], mock_repository: MockKlineRepository, mock_event_bus: MockEventBus
    ) -> None:
        """Test trade data aggregation into klines and storage flow.

        Description of what the test covers:
        This test verifies the process of aggregating individual trade data into `Kline`
        candlesticks and subsequently storing them in a mock repository. It also ensures
        that `KlineEvent` objects are correctly published for each completed kline.

        Preconditions:
        - `sample_trades` fixture provides the necessary trade data.
        - `mock_repository` is ready for storing `Kline` objects.
        - `mock_event_bus` is configured to handle `KlineEvent` publishing and subscription.

        Steps:
        - Group `sample_trades` by minute to simulate kline aggregation periods.
        - Initialize an empty list `received_kline_events` to collect events from the subscriber.
        - Define a `kline_handler` function to append received `KlineEvent` objects to `received_kline_events`.
        - Subscribe the `kline_handler` to `EventType.KLINE` events on the `mock_event_bus`.
        - Iterate through the aggregated trade data (by minute).
        - For each minute, calculate OHLC (Open, High, Low, Close) prices, volume, and quote volume from the trades.
        - Create a `Kline` object using the calculated data.
        - Save the created `Kline` object to the `mock_repository`.
        - Publish a `KlineEvent` for the newly created kline to the `mock_event_bus`.
        - After processing all trades, assert that the number of stored klines in the repository
          matches the number of created klines.
        - Assert that the number of `received_kline_events` matches the number of created klines.
        - Verify the data integrity of each received `KlineEvent`, ensuring `event_type`, `symbol`,
          `interval`, `trades_count`, `volume`, and OHLC relationships are correct.
        - Query the stored klines from the `mock_repository` within the relevant time range and
          assert that the count and properties of the queried klines are correct.
        - In a `finally` block, unsubscribe the handler to clean up.

        Expected Result:
        - Individual trade data is correctly aggregated into `Kline` candlesticks.
        - `Kline` objects are successfully stored in the mock repository.
        - `KlineEvent` objects are accurately published for each stored kline.
        - OHLC data is correctly calculated from the aggregated trades.
        - Data integrity is maintained throughout the aggregation and storage flow.
        """
        kline_data: dict[datetime, list[Trade]] = {}

        for trade in sample_trades:
            minute_time = trade.timestamp.replace(second=0, microsecond=0)
            if minute_time not in kline_data:
                kline_data[minute_time] = []
            kline_data[minute_time].append(trade)

        received_kline_events: list[KlineEvent] = []

        def kline_handler(event: BaseEvent) -> None:
            if isinstance(event, KlineEvent):
                received_kline_events.append(event)

        subscription_id = mock_event_bus.subscribe(EventType.KLINE, kline_handler)

        try:
            created_klines = []

            for open_time, trades in kline_data.items():
                if not trades:
                    continue

                prices = [t.price for t in trades]
                open_price = trades[0].price
                close_price = trades[-1].price
                high_price = max(prices)
                low_price = min(prices)
                volume = sum(t.quantity for t in trades)
                quote_volume = sum(t.price * t.quantity for t in trades)

                kline = Kline(
                    symbol="BTCUSDT",
                    interval=KlineInterval.MINUTE_1,
                    open_time=open_time,
                    close_time=open_time + timedelta(seconds=59),
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    quote_volume=quote_volume,
                    trades_count=len(trades),
                    is_closed=True,
                    exchange="test_exchange",
                )

                await mock_repository.save(kline)
                created_klines.append(kline)

                kline_event = KlineEvent(source="aggregator", symbol=kline.symbol, data=kline)
                await mock_event_bus.publish(kline_event)

            stored_count = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert stored_count == len(created_klines)

            assert len(received_kline_events) == len(created_klines)

            for _i, event in enumerate(received_kline_events):
                assert event.event_type == EventType.KLINE
                assert event.symbol == "BTCUSDT"
                assert event.data.interval == KlineInterval.MINUTE_1
                assert event.data.trades_count > 0
                assert event.data.volume > 0

                assert isinstance(event.data, Kline)
                assert event.data.low_price <= event.data.open_price <= event.data.high_price
                assert event.data.low_price <= event.data.close_price <= event.data.high_price

            start_time = min(k.open_time for k in created_klines)
            end_time = max(k.close_time for k in created_klines) + timedelta(seconds=1)

            queried_klines = await mock_repository.query("BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time)

            assert len(queried_klines) == len(created_klines)
            assert all(k.symbol == "BTCUSDT" for k in queried_klines)
            assert all(k.interval == KlineInterval.MINUTE_1 for k in queried_klines)

        finally:
            mock_event_bus.unsubscribe(subscription_id)

    @pytest.mark.asyncio
    async def test_error_recovery_flow(
        self, mock_provider: MockDataProvider, mock_repository: MockKlineRepository, mock_event_bus: MockEventBus
    ) -> None:
        """Test error handling and recovery in the data flow pipeline.

        Description of what the test covers:
        This test verifies the system's ability to handle various error conditions
        within the data pipeline, such as provider disconnections, storage failures,
        and event system errors. It ensures that the system detects and handles these
        errors gracefully, and can recover to a consistent state.

        Preconditions:
        - Mock components (`mock_provider`, `mock_repository`, `mock_event_bus`) are configured for error simulation.
        - Error event types (`EventType.ERROR`) are defined.

        Steps:
        - Initialize an empty list `error_events` to collect error events.
        - Define an `error_handler` function to append received `ErrorEvent` objects to `error_events`.
        - Subscribe the `error_handler` to `EventType.ERROR` events on the `mock_event_bus`.
        - **Test 1: Provider Connection Error:**
            - Attempt to stream trades from `mock_provider` without connecting it, asserting `ConnectionError` is raised.
            - Publish a mock `ErrorEvent` for the connection failure to the `mock_event_bus`.
        - **Test 2: Storage Error Simulation:**
            - Close the `mock_repository` to simulate a storage failure.
            - Attempt to save a sample `Kline` to the closed repository, asserting `RuntimeError` is raised.
            - Publish a mock `ErrorEvent` for the storage failure to the `mock_event_bus`.
        - **Test 3: Recovery Simulation:**
            - Recreate a new `MockKlineRepository` to simulate recovery.
            - Save the sample `Kline` to the recovered repository and verify it's stored.
            - Connect the `mock_provider` to simulate provider recovery.
        - **Test 4: Event System Error Handling:**
            - Close the `mock_event_bus` to simulate an event system failure.
            - Attempt to publish a `TradeEvent` to the closed event bus, asserting `RuntimeError` is raised.
        - Verify that the `error_events` list contains the expected number of error events and that they are of `EventType.ERROR`.
        - Verify data consistency after partial failures by checking if successfully stored data (e.g., the `latest_kline`)
          is still intact in the recovered repository.
        - In a `finally` block, suppress `RuntimeError` during unsubscribe to ensure cleanup even if the event bus is closed.

        Expected Result:
        - The system correctly detects and handles various error conditions at different pipeline stages.
        - It demonstrates graceful recovery from failures, allowing operations to resume.
        - Data integrity is maintained for data processed before and after error conditions.
        - Appropriate `ErrorEvent` objects are published for monitoring and debugging purposes.
        """
        error_events: list[BaseEvent] = []

        def error_handler(event: BaseEvent) -> None:
            if event.event_type == EventType.ERROR:
                error_events.append(event)

        error_subscription = mock_event_bus.subscribe(EventType.ERROR, error_handler)

        try:
            with pytest.raises(ConnectionError):
                async for _ in mock_provider.stream_trades("BTCUSDT"):
                    pass

            from asset_core.models.events import ErrorEvent

            connection_error = ErrorEvent(
                error="Provider connection failed", error_code="CONN_001", source="data_processor"
            )
            await mock_event_bus.publish(connection_error)

            await mock_repository.close()

            sample_kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2024, 1, 1, tzinfo=UTC),
                close_time=datetime(2024, 1, 1, 0, 0, 59, tzinfo=UTC),
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("100"),
                quote_volume=Decimal("5000000"),
                trades_count=10,
                exchange="test_exchange",
            )

            with pytest.raises(RuntimeError, match="Repository is closed"):
                await mock_repository.save(sample_kline)

            storage_error = ErrorEvent(
                error="Storage operation failed", error_code="STORE_001", source="storage_manager"
            )
            await mock_event_bus.publish(storage_error)

            recovered_repository = MockKlineRepository()

            await recovered_repository.save(sample_kline)
            stored_count = await recovered_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert stored_count == 1

            await mock_provider.connect()
            assert mock_provider.is_connected

            await mock_event_bus.close()

            with pytest.raises(RuntimeError, match="Event bus is closed"):
                test_event = TradeEvent(
                    source="test",
                    symbol="BTCUSDT",
                    data=Trade(
                        symbol="BTCUSDT",
                        trade_id="test_trade",
                        price=Decimal("50000"),
                        quantity=Decimal("1.0"),
                        side=TradeSide.BUY,
                        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    ),
                )
                await mock_event_bus.publish(test_event)

            assert len(error_events) == 2
            assert all(e.event_type == EventType.ERROR for e in error_events)

            latest_kline = await recovered_repository.get_latest("BTCUSDT", KlineInterval.MINUTE_1)
            assert latest_kline is not None
            assert latest_kline.symbol == "BTCUSDT"
            assert latest_kline.volume == Decimal("100")

        finally:
            with contextlib.suppress(RuntimeError):
                mock_event_bus.unsubscribe(error_subscription)

    @pytest.mark.asyncio
    async def test_backfill_integration(
        self, mock_provider: MockDataProvider, mock_repository: MockKlineRepository, sample_klines: list[Kline]
    ) -> None:
        """Test historical data backfill integration with real-time processing.

        Description of what the test covers:
        This test verifies the seamless integration of historical data backfill
        with real-time data processing. It ensures that historical data is correctly
        ingested and stored, and that real-time data processing continues without
        gaps or duplicates during the transition.

        Preconditions:
        - `mock_provider` is capable of providing historical and real-time data.
        - `mock_repository` supports batch saving and querying of klines.
        - `sample_klines` fixture provides the necessary historical test data.

        Steps:
        - Add `sample_klines` to the `mock_provider` to simulate historical data.
        - Connect the `mock_provider`.
        - **Phase 1: Historical Backfill:**
            - Define a historical time range.
            - Fetch historical klines from the `mock_provider` using `fetch_historical_klines`.
            - Save the fetched historical klines to the `mock_repository` using `save_batch`.
            - Verify that the number of stored klines matches the number of historical klines.
        - **Phase 2: Real-time Processing Simulation:**
            - Retrieve the `latest_historical` kline from the `mock_repository`.
            - Generate additional `realtime_klines` that chronologically follow the historical data.
            - Add these `realtime_klines` to the `mock_provider`.
            - Stream klines from the `mock_provider` and save only those that are newer than the `latest_historical` kline to the `mock_repository`.
        - **Phase 3: Verify Integration and Continuity:**
            - Assert that the `total_final_count` of klines in the repository equals the sum of historical and real-time klines.
            - Query all stored klines within the full time range.
            - Verify chronological continuity by asserting that each kline's `open_time` is greater than the previous one's, and that time differences between `close_time` and subsequent `open_time` are minimal.
        - **Phase 4: Test Gap Detection and Statistics:**
            - Call `mock_repository.get_gaps` and assert that no gaps are found in the continuous test data.
            - Call `mock_repository.get_statistics` and verify the returned count, symbol, and interval.
        - In a `finally` block, disconnect the `mock_provider` to clean up.

        Expected Result:
        - Historical data is successfully backfilled into the repository.
        - Real-time data processing seamlessly continues from the historical data without gaps or duplicates.
        - The combined dataset in the repository maintains chronological continuity.
        - Gap detection and statistics functions operate correctly on the integrated data.
        """
        for kline in sample_klines:
            mock_provider.add_mock_kline(kline)

        await mock_provider.connect()

        try:
            start_time = datetime(2024, 1, 1, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)

            historical_klines = await mock_provider.fetch_historical_klines(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time
            )

            stored_count = await mock_repository.save_batch(historical_klines)
            assert stored_count == len(historical_klines)

            total_stored = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert total_stored == len(historical_klines)

            latest_historical = await mock_repository.get_latest("BTCUSDT", KlineInterval.MINUTE_1)
            assert latest_historical is not None

            realtime_klines = []
            next_time = latest_historical.close_time + timedelta(seconds=1)

            for i in range(10):
                kline_open_time = next_time + timedelta(minutes=i)
                kline_close_time = kline_open_time + timedelta(seconds=59)
                base_price = Decimal(f"{55000 + i * 10}")

                realtime_kline = Kline(
                    symbol="BTCUSDT",
                    interval=KlineInterval.MINUTE_1,
                    open_time=kline_open_time,
                    close_time=kline_close_time,
                    open_price=base_price,
                    high_price=base_price + Decimal("25"),
                    low_price=base_price - Decimal("15"),
                    close_price=base_price + Decimal("10"),
                    volume=Decimal("50"),
                    quote_volume=Decimal("2750000"),
                    trades_count=5,
                    exchange="test_exchange",
                )
                realtime_klines.append(realtime_kline)
                mock_provider.add_mock_kline(realtime_kline)

            realtime_count = 0
            kline_stream = mock_provider.stream_klines("BTCUSDT", KlineInterval.MINUTE_1)
            async for kline in kline_stream:
                if kline.open_time > latest_historical.close_time:
                    await mock_repository.save(kline)
                    realtime_count += 1

                    if realtime_count >= len(realtime_klines):
                        break

            total_final_count = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            expected_total = len(historical_klines) + len(realtime_klines)
            assert total_final_count == expected_total

            all_stored_klines = await mock_repository.query(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, realtime_klines[-1].close_time + timedelta(seconds=1)
            )

            for i in range(1, len(all_stored_klines)):
                prev_kline = all_stored_klines[i - 1]
                curr_kline = all_stored_klines[i]
                assert curr_kline.open_time > prev_kline.open_time

                time_diff = curr_kline.open_time - prev_kline.close_time
                assert time_diff <= timedelta(seconds=2)

            gaps = await mock_repository.get_gaps(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, realtime_klines[-1].close_time
            )

            assert len(gaps) == 0

            stats = await mock_repository.get_statistics("BTCUSDT", KlineInterval.MINUTE_1)
            assert stats["count"] == expected_total
            assert stats["symbol"] == "BTCUSDT"
            assert stats["interval"] == KlineInterval.MINUTE_1.value

        finally:
            await mock_provider.disconnect()
