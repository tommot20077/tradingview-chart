"""Tests for event bus interfaces."""

import asyncio
from abc import ABC
from collections.abc import Callable
from typing import Any

import pytest

from asset_core.events.bus import AbstractEventBus, AsyncEventHandler, EventHandler
from asset_core.models.events import BaseEvent, EventType


class MockEventBus(AbstractEventBus):
    """Mock implementation of AbstractEventBus for testing.

    This mock provides an in-memory event bus for testing purposes,
    simulating publish, subscribe, unsubscribe, and event waiting.

    Attributes:
        _subscribers (dict[EventType, list[tuple]]): Stores registered event handlers.
        _subscription_counter (int): Counter for generating unique subscription IDs.
        _closed (bool): Flag indicating if the event bus is closed.
        _events (list[BaseEvent[Any]]): A list to store published events for inspection.
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[tuple[Any, ...]]] = {}
        self._subscription_counter = 0
        self._closed = False
        self._events: list[BaseEvent[Any]] = []

    async def publish(self, event: BaseEvent[Any]) -> None:
        """Publishes an event to the bus, notifying all relevant subscribers.

        Args:
            event (BaseEvent[Any]): The event to publish.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        if self._closed:
            raise RuntimeError("Event bus is closed")

        self._events.append(event)

        # Notify subscribers
        if event.event_type in self._subscribers:
            for _sub_id, handler, filter_symbol in self._subscribers[event.event_type]:
                # Apply symbol filter if specified
                if filter_symbol and event.symbol != filter_symbol:
                    continue

                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribes a handler to a specific event type, with optional symbol filtering.

        Args:
            event_type (EventType): The type of event to subscribe to.
            handler (EventHandler | AsyncEventHandler): The callable (sync or async)
                                                        that will handle the event.
            filter_symbol (str | None): An optional symbol to filter events by.
                                        If provided, only events matching this symbol
                                        will be dispatched to the handler.

        Returns:
            str: A unique subscription ID that can be used to unsubscribe.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        if self._closed:
            raise RuntimeError("Event bus is closed")

        sub_id = f"sub_{self._subscription_counter}"
        self._subscription_counter += 1

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append((sub_id, handler, filter_symbol))
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribes a handler using its subscription ID.

        Args:
            subscription_id (str): The unique ID of the subscription to remove.

        Returns:
            bool: True if the subscription was found and removed, False otherwise.
        """
        for _event_type, subs in self._subscribers.items():
            for i, (sub_id, _handler, _filter_symbol) in enumerate(subs):
                if sub_id == subscription_id:
                    del subs[i]
                    return True
        return False

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Unsubscribes all handlers, optionally for a specific event type.

        Args:
            event_type (EventType | None): The type of event for which to unsubscribe
                                           all handlers. If None, all handlers for
                                           all event types will be unsubscribed.

        Returns:
            int: The number of handlers that were unsubscribed.
        """
        if event_type:
            count = len(self._subscribers.get(event_type, []))
            self._subscribers[event_type] = []
            return count
        else:
            total_count = sum(len(subs) for subs in self._subscribers.values())
            self._subscribers.clear()
            return total_count

    async def close(self) -> None:
        """Closes the event bus, preventing further operations and clearing subscribers.

        Sets the internal `_closed` flag to True and clears all registered subscribers.
        """
        self._closed = True
        self._subscribers.clear()

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Returns the number of active subscriptions, optionally for a specific event type.

        Args:
            event_type (EventType | None): The event type for which to count subscriptions.
                                           If None, returns the total count across all types.

        Returns:
            int: The number of subscriptions.
        """
        if event_type:
            return len(self._subscribers.get(event_type, []))
        else:
            return sum(len(subs) for subs in self._subscribers.values())

    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,
        filter_func: Callable[[BaseEvent[Any]], bool] | None = None,
    ) -> BaseEvent[Any] | None:
        """Waits for a specific event to be published, with optional timeout and filtering.

        Args:
            event_type (EventType): The type of event to wait for.
            timeout (float | None): The maximum time in seconds to wait for the event.
                                    If None, waits indefinitely.
            filter_func (Callable[[BaseEvent[Any]], bool] | None): An optional callable
                                                                to filter events. Only
                                                                events for which this
                                                                function returns True
                                                                will be considered.

        Returns:
            BaseEvent[Any] | None: The first matching event, or None if the timeout is reached.
        """
        # Simple implementation for testing
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check existing events
            for event in self._events:
                if event.event_type == event_type and (filter_func is None or filter_func(event)):
                    return event

            # Check timeout
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                return None

            # Wait a bit before checking again
            await asyncio.sleep(0.01)

    @property
    def is_closed(self) -> bool:
        """Checks if the event bus is closed.

        Returns:
            bool: True if the event bus is closed, False otherwise.
        """
        return self._closed


@pytest.mark.unit
class TestAbstractEventBus:
    """Test cases for AbstractEventBus interface.

    Verifies that the `AbstractEventBus` is correctly defined as an abstract
    base class and that its mock implementation (`MockEventBus`) adheres
    to the expected behaviors for event publishing, subscription, and management.
    """

    def test_is_abstract(self) -> None:
        """Test that AbstractEventBus is abstract.

        Description of what the test covers.
        Verifies that `AbstractEventBus` is correctly defined as an abstract
        base class and cannot be instantiated directly.

        Expected Result:
        - `AbstractEventBus` should be a subclass of `abc.ABC`.
        - Attempting to instantiate `AbstractEventBus` directly should raise `TypeError`.
        """
        assert issubclass(AbstractEventBus, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractEventBus()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_mock_event_bus_basic_operations(self) -> None:
        """Test basic operations of mock event bus.

        Description of what the test covers.
        Verifies the initial state of the `MockEventBus` and its ability to be
        closed, ensuring the `is_closed` property reflects the state correctly.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Assert that `is_closed` is initially False and subscription count is 0.
        - Call the `close()` method.
        - Assert that `is_closed` becomes True.

        Expected Result:
        - The event bus should initialize in an open state.
        - The event bus should transition to a closed state after `close()` is called.
        """
        bus = MockEventBus()

        assert not bus.is_closed
        assert bus.get_subscription_count() == 0

        await bus.close()
        assert bus.is_closed

    @pytest.mark.asyncio
    async def test_mock_event_bus_subscription(self) -> None:
        """Test event subscription.

        Description of what the test covers.
        Verifies that a handler can successfully subscribe to an event type,
        receive published events, and that the subscription count is accurate.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Define a synchronous handler function.
        - Subscribe the handler to `EventType.TRADE`.
        - Assert that the subscription ID is a string and the subscription count is 1.
        - Publish a `BaseEvent` of `EventType.TRADE`.
        - Assert that the handler was called and received the correct event.

        Expected Result:
        - The handler should be successfully subscribed.
        - The handler should receive the published event.
        - The subscription count should reflect the active subscription.
        """
        bus = MockEventBus()
        received_events = []

        def handler(event: BaseEvent[Any]) -> None:
            received_events.append(event)

        # Subscribe to trade events
        sub_id = bus.subscribe(EventType.TRADE, handler)
        assert isinstance(sub_id, str)
        assert bus.get_subscription_count(EventType.TRADE) == 1

        # Publish a trade event
        event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={"test": "data"},
        )
        await bus.publish(event)

        # Check that handler was called
        assert len(received_events) == 1
        assert received_events[0] == event

    @pytest.mark.asyncio
    async def test_mock_event_bus_async_handler(self) -> None:
        """Test async event handler.

        Description of what the test covers.
        Verifies that an asynchronous handler can successfully subscribe to an
        event type and receive published events.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Define an asynchronous handler function.
        - Subscribe the asynchronous handler to `EventType.TRADE`.
        - Publish a `BaseEvent` of `EventType.TRADE`.
        - Assert that the asynchronous handler was called and received the correct event.

        Expected Result:
        - The asynchronous handler should be successfully subscribed.
        - The asynchronous handler should receive the published event.
        """
        bus = MockEventBus()
        received_events = []

        async def async_handler(event: BaseEvent[Any]) -> None:
            received_events.append(event)

        # Subscribe with async handler
        _sub_id = bus.subscribe(EventType.TRADE, async_handler)

        # Publish event
        event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={"test": "data"},
        )
        await bus.publish(event)

        # Check that async handler was called
        assert len(received_events) == 1
        assert received_events[0] == event

    @pytest.mark.asyncio
    async def test_mock_event_bus_symbol_filter(self) -> None:
        """Test event filtering by symbol.

        Description of what the test covers:
        Verifies that event handlers subscribed with a `filter_symbol` only
        receive events that match the specified symbol.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Subscribe two handlers to `EventType.TRADE`, each with a different `filter_symbol`.
        - Publish a `BaseEvent` for each symbol.
        - Assert that each handler only received events matching its subscribed symbol.

        Expected Result:
        - Events should be correctly filtered by symbol.
        - Handlers should only receive events for their specified symbol.
        """
        bus = MockEventBus()
        btc_events = []
        eth_events = []

        def btc_handler(event: BaseEvent[Any]) -> None:
            btc_events.append(event)

        def eth_handler(event: BaseEvent[Any]) -> None:
            eth_events.append(event)

        # Subscribe with symbol filters
        bus.subscribe(EventType.TRADE, btc_handler, filter_symbol="BTCUSDT")
        bus.subscribe(EventType.TRADE, eth_handler, filter_symbol="ETHUSDT")

        # Publish BTC event
        btc_event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            symbol="BTCUSDT",
            data={"symbol": "BTCUSDT"},
        )
        await bus.publish(btc_event)

        # Publish ETH event
        eth_event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            symbol="ETHUSDT",
            data={"symbol": "ETHUSDT"},
        )
        await bus.publish(eth_event)

        # Check filtering worked
        assert len(btc_events) == 1
        assert len(eth_events) == 1
        assert btc_events[0].symbol == "BTCUSDT"
        assert eth_events[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_mock_event_bus_unsubscribe(self) -> None:
        """Test unsubscribing from events.

        Description of what the test covers.
        Verifies that a handler can be successfully unsubscribed using its
        subscription ID, and that it no longer receives published events.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Define a handler function.
        - Subscribe the handler to `EventType.TRADE` and store the `sub_id`.
        - Assert that the subscription count is 1.
        - Unsubscribe using the `sub_id`.
        - Assert that the unsubscription was successful and the subscription count is 0.
        - Publish a `BaseEvent` of `EventType.TRADE`.
        - Assert that the handler was not called.

        Expected Result:
        - The handler should be successfully unsubscribed.
        - The handler should not receive events after unsubscription.
        - The subscription count should reflect the removal of the subscription.
        """
        bus = MockEventBus()
        received_events = []

        def handler(event: BaseEvent[Any]) -> None:
            received_events.append(event)

        # Subscribe and then unsubscribe
        sub_id = bus.subscribe(EventType.TRADE, handler)
        assert bus.get_subscription_count(EventType.TRADE) == 1

        result = bus.unsubscribe(sub_id)
        assert result is True
        assert bus.get_subscription_count(EventType.TRADE) == 0

        # Publish event - should not be received
        event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={"test": "data"},
        )
        await bus.publish(event)

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_mock_event_bus_unsubscribe_all(self) -> None:
        """Test unsubscribing all handlers.

        Description of what the test covers.
        Verifies that all handlers for a specific event type, or all handlers
        across all event types, can be successfully unsubscribed.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Subscribe multiple handlers to different event types.
        - Assert the total subscription count and count for a specific event type.
        - Call `unsubscribe_all()` for a specific event type.
        - Assert that only handlers for that event type are removed.
        - Call `unsubscribe_all()` without an event type.
        - Assert that all remaining handlers are removed.

        Expected Result:
        - `unsubscribe_all()` should correctly remove handlers based on the specified scope.
        - Subscription counts should accurately reflect the changes.
        """
        bus = MockEventBus()

        def handler1(event: BaseEvent[Any]) -> None:
            pass

        def handler2(event: BaseEvent[Any]) -> None:
            pass

        # Subscribe multiple handlers
        bus.subscribe(EventType.TRADE, handler1)
        bus.subscribe(EventType.TRADE, handler2)
        bus.subscribe(EventType.KLINE, handler1)

        assert bus.get_subscription_count() == 3
        assert bus.get_subscription_count(EventType.TRADE) == 2

        # Unsubscribe all trade handlers
        count = bus.unsubscribe_all(EventType.TRADE)
        assert count == 2
        assert bus.get_subscription_count(EventType.TRADE) == 0
        assert bus.get_subscription_count(EventType.KLINE) == 1

        # Unsubscribe all remaining
        count = bus.unsubscribe_all()
        assert count == 1
        assert bus.get_subscription_count() == 0

    @pytest.mark.asyncio
    async def test_mock_event_bus_wait_for(self) -> None:
        """Test waiting for specific events.

        Description of what the test covers.
        Verifies that the `wait_for` method correctly waits for a specific event
        to be published and returns it.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Start a background task that publishes a `BaseEvent` after a short delay.
        - Call `bus.wait_for()` for the expected event type with a timeout.
        - Assert that the returned event is not None and matches the expected event type.

        Expected Result:
        - The `wait_for` method should successfully retrieve the published event.
        """
        bus = MockEventBus()

        # Start waiting for event in background
        async def wait_and_publish() -> None:
            await asyncio.sleep(0.05)  # Small delay
            event: BaseEvent[dict[str, Any]] = BaseEvent(
                event_type=EventType.TRADE,
                source="test",
                data={"test": "data"},
            )
            await bus.publish(event)

        # Start background task
        asyncio.create_task(wait_and_publish())

        # Wait for the event
        result = await bus.wait_for(EventType.TRADE, timeout=1.0)

        assert result is not None
        assert result.event_type == EventType.TRADE

    @pytest.mark.asyncio
    async def test_mock_event_bus_wait_for_timeout(self) -> None:
        """Test waiting for events with timeout.

        Description of what the test covers.
        Verifies that the `wait_for` method correctly returns None when the
        specified timeout is reached and no matching event is published.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance.
        - Call `bus.wait_for()` for an event type that will not be published,
          with a short timeout.
        - Assert that the returned result is None.

        Expected Result:
        - The `wait_for` method should return None after the timeout.
        """
        bus = MockEventBus()

        # Wait for event that won't come
        result = await bus.wait_for(EventType.TRADE, timeout=0.1)

        assert result is None

    @pytest.mark.asyncio
    async def test_mock_event_bus_closed_operations(self) -> None:
        """Test operations on closed event bus.

        Description of what the test covers.
        Verifies that attempting to perform operations (publish, subscribe)
        on a closed event bus raises a `RuntimeError`.

        Preconditions:
        - None.

        Steps:
        - Create a `MockEventBus` instance and immediately close it.
        - Attempt to `publish` an event.
        - Assert that a `RuntimeError` is raised with a specific message.
        - Attempt to `subscribe` a handler.
        - Assert that a `RuntimeError` is raised with a specific message.

        Expected Result:
        - Operations on a closed event bus should raise a `RuntimeError`.
        """
        bus = MockEventBus()

        await bus.close()

        # Should fail when trying to use closed bus
        with pytest.raises(RuntimeError, match="Event bus is closed"):
            await bus.publish(
                BaseEvent(
                    event_type=EventType.TRADE,
                    source="test",
                    data={},
                )
            )

        with pytest.raises(RuntimeError, match="Event bus is closed"):
            bus.subscribe(EventType.TRADE, lambda _: None)
