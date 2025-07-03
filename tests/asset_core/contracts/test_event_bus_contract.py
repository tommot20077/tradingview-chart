"""
Contract tests for AbstractEventBus interface.

Comprehensive tests to verify that any implementation of AbstractEventBus
follows the expected behavioral contracts and interface specifications.
"""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from asset_core.events.bus import AbstractEventBus, AsyncEventHandler, EventHandler
from asset_core.models.events import BaseEvent, EventType
from .base_contract_test import AsyncContractTestMixin, BaseContractTest, \
    MockImplementationBase


class MockEvent(BaseEvent[dict[str, Any]]):
    """A mock event class for contract testing of the event bus.

    This class extends `BaseEvent` and is used to create test events
    with specific event types, symbols, and data payloads.
    """

    def __init__(self, event_type: EventType, symbol: str | None = None, data: dict[str, Any] | None = None) -> None:
        super().__init__(event_type=event_type, symbol=symbol, source="test_source", data=data or {})


class MockEventBus(AbstractEventBus, MockImplementationBase):
    """Mock implementation of AbstractEventBus for contract testing.

    Provides a complete implementation that follows the interface contract
    while using in-memory event handling for testing purposes.
    """

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions: dict[str, list[dict[str, Any]]] = {}
        self._subscription_counter = 0
        self._published_events: list[BaseEvent[Any]] = []

    async def publish(self, event: BaseEvent[Any]) -> None:
        """Publishes an event to all matching subscribers.

        Args:
            event (BaseEvent[Any]): The event to publish.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        self._check_not_closed()

        self._published_events.append(event)

        # Find matching subscriptions
        matching_subscriptions = []

        for event_type, subscriptions in self._subscriptions.items():
            if event_type == event.event_type:
                for subscription in subscriptions:
                    # Check symbol filter
                    if subscription["symbol_filter"] is None or subscription["symbol_filter"] == event.symbol:
                        matching_subscriptions.append(subscription)

        # Call handlers
        for subscription in matching_subscriptions:
            handler = subscription["handler"]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # In a real implementation, you might want to handle errors differently
                print(f"Handler error: {e}")

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribes a handler to events of a specific type, with optional symbol filtering.

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
            ValueError: If the handler is not callable.
            RuntimeError: If the event bus is closed.
        """
        self._check_not_closed()

        if not callable(handler):
            raise ValueError("Handler must be callable")

        subscription_id = f"sub_{self._subscription_counter}"
        self._subscription_counter += 1

        subscription = {
            "id": subscription_id,
            "handler": handler,
            "symbol_filter": filter_symbol,
            "event_type": event_type,
        }

        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []

        self._subscriptions[event_type].append(subscription)

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Removes a specific subscription from the event bus.

        Args:
            subscription_id (str): The unique ID of the subscription to remove.

        Returns:
            bool: True if the subscription was found and removed, False otherwise.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        self._check_not_closed()

        for _event_type, subscriptions in self._subscriptions.items():
            for i, subscription in enumerate(subscriptions):
                if subscription["id"] == subscription_id:
                    del subscriptions[i]
                    return True

        return False

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Removes all subscriptions, optionally for a specific event type.

        Args:
            event_type (EventType | None): The type of event for which to remove
                                           all subscriptions. If None, all subscriptions
                                           across all event types will be removed.

        Returns:
            int: The number of subscriptions that were removed.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        self._check_not_closed()

        removed_count = 0

        if event_type is None:
            # Remove all subscriptions
            for subscriptions in self._subscriptions.values():
                removed_count += len(subscriptions)
                subscriptions.clear()
        else:
            # Remove subscriptions for specific event type
            if event_type in self._subscriptions:
                subscriptions = self._subscriptions[event_type]
                removed_count = len(subscriptions)
                subscriptions.clear()

        return removed_count

    async def close(self) -> None:
        """Closes the event bus and cleans up resources.

        Sets the internal `_is_closed` flag to True and clears all subscriptions
        and published events.
        """
        self._is_closed = True
        self._subscriptions.clear()
        self._published_events.clear()

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Returns the number of active subscriptions, optionally for a specific event type.

        Args:
            event_type (EventType | None): The event type for which to count subscriptions.
                                           If None, returns the total count across all types.

        Returns:
            int: The number of subscriptions.

        Raises:
            RuntimeError: If the event bus is closed.
        """
        self._check_not_closed()

        if event_type is None:
            return sum(len(subs) for subs in self._subscriptions.values())
        else:
            return len(self._subscriptions.get(event_type, []))

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

        Raises:
            RuntimeError: If the event bus is closed.
            asyncio.TimeoutError: If the timeout is reached before the event is received.
        """
        self._check_not_closed()

        # Create a future to wait for the event
        event_future: asyncio.Future[BaseEvent[Any]] = asyncio.Future()

        def event_waiter(event: BaseEvent[Any]) -> None:
            if not event_future.done() and (filter_func is None or filter_func(event)):
                event_future.set_result(event)

        # Subscribe to the event temporarily
        subscription_id = self.subscribe(event_type, event_waiter)

        try:
            # Wait for the event with timeout
            if timeout is not None:
                event = await asyncio.wait_for(event_future, timeout=timeout)
            else:
                event = await event_future

            return event

        finally:
            # Clean up subscription
            self.unsubscribe(subscription_id)

    @property
    def is_closed(self) -> bool:
        """Checks if the event bus is closed.

        Returns:
            bool: True if the event bus is closed, False otherwise.
        """
        return self._is_closed

    # Additional testing helpers
    def get_published_events(self) -> list[BaseEvent[Any]]:
        """Returns a copy of the list of all events published to this mock bus.

        This method is primarily for testing and inspection purposes.

        Returns:
            list[BaseEvent[Any]]: A list of published events.
        """
        return self._published_events.copy()

    def clear_published_events(self) -> None:
        """Clears the list of published events.

        This method is primarily for testing and resetting the state.
        """
        self._published_events.clear()


class TestAbstractEventBusContract(BaseContractTest, AsyncContractTestMixin):
    """Contract tests for AbstractEventBus interface.

    These tests verify that any implementation of AbstractEventBus
    follows the expected behavioral contracts and interface specifications.
    """

    @pytest.fixture
    async def event_bus(self) -> MockEventBus:
        """Provides a mock event bus instance for testing.

        Returns:
            MockEventBus: An instance of the mock event bus.
        """
        return MockEventBus()

    @pytest.fixture
    def sample_event(self) -> MockEvent:
        """Provides a sample event for testing.

        Returns:
            MockEvent: A sample `MockEvent` of type `TRADE` with symbol "BTCUSDT".
        """
        return MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000})

    def test_required_methods_defined(self) -> None:
        """Test that all required abstract methods are defined in the interface.

        Description of what the test covers.
        Verifies that `AbstractEventBus` declares all necessary methods
        as abstract and that they have the correct signatures.

        Expected Result:
        - All required methods are present as abstract methods.
        - Method signatures match the expected interface.
        """
        abstract_methods = self.get_abstract_methods(AbstractEventBus)

        required_methods = {
            "publish",
            "subscribe",
            "unsubscribe",
            "unsubscribe_all",
            "close",
            "get_subscription_count",
            "wait_for",
        }

        # All required methods should be abstract
        assert required_methods.issubset(set(abstract_methods)), (
            f"Missing abstract methods: {required_methods - set(abstract_methods)}"
        )

    def test_method_signatures(self) -> None:
        """Test that all abstract methods have correct signatures.

        Description of what the test covers.
        Verifies parameter types, return types, and async/sync designation
        for all methods in the interface.

        Expected Result:
        - All methods have correct parameter and return type annotations.
        - Async methods are properly marked as async.
        """
        # Test key method signatures
        publish_sig = self.get_method_signature(AbstractEventBus, "publish")
        assert len(publish_sig.parameters) == 2  # self, event
        assert "event" in publish_sig.parameters

        subscribe_sig = self.get_method_signature(AbstractEventBus, "subscribe")
        assert len(subscribe_sig.parameters) == 4  # self, event_type, handler, filter_symbol
        assert "event_type" in subscribe_sig.parameters
        assert "handler" in subscribe_sig.parameters
        assert "filter_symbol" in subscribe_sig.parameters

        # Test that core methods are async or sync as expected
        assert self.is_async_method(AbstractEventBus, "publish")
        assert not self.is_async_method(AbstractEventBus, "subscribe")  # Subscribe is synchronous
        assert self.is_async_method(AbstractEventBus, "close")
        assert self.is_async_method(AbstractEventBus, "wait_for")

        # Test that utility methods are not async
        assert not self.is_async_method(AbstractEventBus, "get_subscription_count")
        assert not self.is_async_method(AbstractEventBus, "unsubscribe")
        assert not self.is_async_method(AbstractEventBus, "unsubscribe_all")

    def test_inheritance_chain(self) -> None:
        """Test that AbstractEventBus correctly inherits from abc.ABC.

        Description of what the test covers.
        Verifies that the abstract event bus follows proper inheritance patterns
        for abstract base classes.

        Expected Result:
        - `AbstractEventBus` should inherit from `abc.ABC`.
        - Should be properly marked as abstract class.
        """
        import abc

        # Test inheritance from ABC
        assert issubclass(AbstractEventBus, abc.ABC)

        # Test that the class itself is abstract (cannot be instantiated)
        with pytest.raises(TypeError):
            AbstractEventBus()  # type: ignore[abstract]

    def test_event_handler_type_definitions(self) -> None:
        """Test that event handler types are properly defined.

        Description of what the test covers.
        Verifies that `EventHandler` and `AsyncEventHandler` types
        are available and correctly typed.

        Expected Result:
        - Handler types are available for import.
        - Types represent callable interfaces.
        """
        # Test that handler types are available
        assert EventHandler is not None
        assert AsyncEventHandler is not None

        # These should be type aliases or protocols for callable handlers
        # The exact implementation depends on the typing system used

    async def test_mock_implementation_completeness(self, event_bus: MockEventBus) -> None:
        """Test that the mock implementation provides complete interface coverage.

        Description of what the test covers.
        Creates a complete mock implementation and verifies that all methods
        work correctly and follow the expected behavioral contracts.

        Expected Result:
        - All abstract methods are implemented.
        - Methods return expected types.
        - State transitions work correctly.
        """
        # Test that all abstract methods are implemented
        abstract_methods = self.get_abstract_methods(AbstractEventBus)

        # Properties that should be implemented as properties, not methods
        expected_properties = {"is_closed"}

        for method_name in abstract_methods:
            assert hasattr(event_bus, method_name), f"Missing method: {method_name}"
            method = getattr(event_bus, method_name)

            if method_name in expected_properties:
                # For properties, check they can be accessed (not callable)
                try:
                    _ = method  # Try to access the property
                    assert not callable(method), f"Property {method_name} should not be callable"
                except AttributeError:
                    pytest.fail(f"Property {method_name} is not accessible")
            else:
                assert callable(method), f"Method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_basic_publish_subscribe_flow(self, event_bus: MockEventBus, sample_event: MockEvent) -> None:
        """Test basic publish-subscribe functionality.

        Description of what the test covers.
        Tests the fundamental event publishing and subscription mechanism
        to ensure events are properly delivered to subscribers.

        Preconditions:
        - Event bus is initialized and not closed.

        Steps:
        - Subscribe to an event type.
        - Publish an event of that type.
        - Verify the handler is called.
        - Unsubscribe.
        - Verify no more events are received.

        Expected Result:
        - Events are delivered to subscribers.
        - Handlers are called with correct event data.
        - Subscription management works correctly.
        """
        received_events = []

        # Define event handler
        def event_handler(event: BaseEvent[Any]) -> None:
            received_events.append(event)

        # Test subscription
        subscription_id = event_bus.subscribe(EventType.TRADE, event_handler)
        assert isinstance(subscription_id, str)
        assert len(subscription_id) > 0

        # Test publishing
        await event_bus.publish(sample_event)

        # Give a moment for event delivery
        await asyncio.sleep(0.001)

        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0] == sample_event

        # Test unsubscription
        unsubscribed = event_bus.unsubscribe(subscription_id)
        assert unsubscribed is True

        # Publish another event
        second_event = MockEvent(EventType.TRADE, "ETHUSDT", {"price": 3000})
        await event_bus.publish(second_event)

        await asyncio.sleep(0.001)

        # Should not receive the second event
        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_async_event_handler_support(self, event_bus: MockEventBus) -> None:
        """Test support for async event handlers.

        Description of what the test covers.
        Verifies that both synchronous and asynchronous event handlers can be registered
        and that they are properly called when events are published.

        Expected Result:
        - Async handlers are properly awaited.
        - Both sync and async handlers work correctly.
        - Mixed handler types can coexist.
        """
        sync_events = []
        async_events = []

        # Define sync handler
        def sync_handler(event: BaseEvent[Any]) -> None:
            sync_events.append(event)

        # Define async handler
        async def async_handler(event: BaseEvent[Any]) -> None:
            async_events.append(event)
            await asyncio.sleep(0.001)  # Simulate async work

        # Subscribe both handlers
        sync_sub_id = event_bus.subscribe(EventType.TRADE, sync_handler)
        async_sub_id = event_bus.subscribe(EventType.TRADE, async_handler)

        # Publish event
        test_event = MockEvent(EventType.TRADE, "ADAUSDT", {"price": 1.5})
        await event_bus.publish(test_event)

        # Give time for async handler to complete
        await asyncio.sleep(0.01)

        # Both handlers should have received the event
        assert len(sync_events) == 1
        assert len(async_events) == 1
        assert sync_events[0] == test_event
        assert async_events[0] == test_event

        # Cleanup
        event_bus.unsubscribe(sync_sub_id)
        event_bus.unsubscribe(async_sub_id)

    @pytest.mark.asyncio
    async def test_symbol_filtering_mechanism(self, event_bus: MockEventBus) -> None:
        """Test symbol-based event filtering.

        Description of what the test covers.
        Verifies that events can be filtered by symbol and that only
        matching events are delivered to filtered subscribers.

        Expected Result:
        - Symbol filters work correctly.
        - Only matching events are delivered.
        - Unfiltered subscriptions receive all events.
        """
        btc_events = []
        eth_events = []
        all_events = []

        # Define handlers
        def btc_handler(event: BaseEvent[Any]) -> None:
            btc_events.append(event)

        def eth_handler(event: BaseEvent[Any]) -> None:
            eth_events.append(event)

        def all_handler(event: BaseEvent[Any]) -> None:
            all_events.append(event)

        # Subscribe with symbol filters
        btc_sub_id = event_bus.subscribe(EventType.TRADE, btc_handler, filter_symbol="BTCUSDT")
        eth_sub_id = event_bus.subscribe(EventType.TRADE, eth_handler, filter_symbol="ETHUSDT")
        all_sub_id = event_bus.subscribe(EventType.TRADE, all_handler)  # No filter

        # Publish events for different symbols
        btc_event = MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000})
        eth_event = MockEvent(EventType.TRADE, "ETHUSDT", {"price": 3000})
        ada_event = MockEvent(EventType.TRADE, "ADAUSDT", {"price": 1.5})

        await event_bus.publish(btc_event)
        await event_bus.publish(eth_event)
        await event_bus.publish(ada_event)

        await asyncio.sleep(0.001)

        # Check filtering results
        assert len(btc_events) == 1
        assert btc_events[0] == btc_event

        assert len(eth_events) == 1
        assert eth_events[0] == eth_event

        assert len(all_events) == 3  # Should receive all events

        # Cleanup
        event_bus.unsubscribe(btc_sub_id)
        event_bus.unsubscribe(eth_sub_id)
        event_bus.unsubscribe(all_sub_id)

    @pytest.mark.asyncio
    async def test_subscription_management_interface(self, event_bus: MockEventBus) -> None:
        """Test subscription management functionality.

        Description of what the test covers.
        Verifies that subscriptions can be managed through various methods
        including bulk unsubscribe operations.

        Expected Result:
        - Individual unsubscribe works correctly.
        - Bulk unsubscribe operations work.
        - Subscription counts are accurate.
        """
        # Create multiple subscriptions
        handlers = [lambda _e: None for _ in range(5)]

        sub_ids = []
        for i, handler in enumerate(handlers):
            event_type = EventType.TRADE if i % 2 == 0 else EventType.KLINE
            sub_id = event_bus.subscribe(event_type, handler)
            sub_ids.append(sub_id)

        # Test subscription count
        total_count = event_bus.get_subscription_count()
        assert total_count == 5

        event_0_count = event_bus.get_subscription_count(EventType.TRADE)
        event_1_count = event_bus.get_subscription_count(EventType.KLINE)
        assert event_0_count + event_1_count == 5

        # Test individual unsubscribe
        unsubscribed = event_bus.unsubscribe(sub_ids[0])
        assert unsubscribed is True

        # Test unsubscribing non-existent subscription
        fake_unsubscribed = event_bus.unsubscribe("fake_id")
        assert fake_unsubscribed is False

        # Test bulk unsubscribe for specific event type
        removed_count = event_bus.unsubscribe_all(EventType.TRADE)
        assert removed_count >= 1  # At least one TRADE subscription should remain

        # Test bulk unsubscribe all
        remaining_count = event_bus.unsubscribe_all()
        assert remaining_count >= 0

        final_count = event_bus.get_subscription_count()
        assert final_count == 0

    @pytest.mark.asyncio
    async def test_wait_for_event_interface(self, event_bus: MockEventBus) -> None:
        """Test event waiting functionality with timeout.

        Description of what the test covers.
        Verifies that `wait_for` can be used to wait for specific events
        with optional timeout and symbol filtering.

        Expected Result:
        - Can wait for and receive specific events.
        - Timeout functionality works correctly.
        - Symbol filtering works in `wait_for`.
        """

        # Test successful event waiting
        async def publish_delayed_event() -> None:
            await asyncio.sleep(0.01)
            test_event = MockEvent(EventType.SYSTEM, "BTCUSDT", {"price": 55000})
            await event_bus.publish(test_event)

        # Start publishing task
        publish_task = asyncio.create_task(publish_delayed_event())

        # Wait for the event
        received_event = await event_bus.wait_for(EventType.SYSTEM, timeout=1.0)

        assert received_event is not None
        assert received_event.event_type == EventType.SYSTEM
        assert received_event.symbol == "BTCUSDT"

        await publish_task

        # Test timeout
        with pytest.raises(asyncio.TimeoutError):
            await event_bus.wait_for(EventType.ORDER, timeout=0.01)

        # Test symbol filtering in wait_for
        async def publish_multiple_symbols() -> None:
            await asyncio.sleep(0.01)
            await event_bus.publish(MockEvent(EventType.BALANCE, "ETHUSDT", {"price": 3000}))
            await asyncio.sleep(0.01)
            await event_bus.publish(MockEvent(EventType.BALANCE, "BTCUSDT", {"price": 50000}))

        publish_task = asyncio.create_task(publish_multiple_symbols())

        # Should receive only the BTCUSDT event
        btc_event = await event_bus.wait_for(
            EventType.BALANCE, timeout=1.0, filter_func=lambda e: e.symbol == "BTCUSDT"
        )
        assert btc_event is not None and btc_event.symbol == "BTCUSDT"

        await publish_task

    @pytest.mark.asyncio
    async def test_event_type_filtering(self, event_bus: MockEventBus) -> None:
        """Test that event type filtering works correctly.

        Description of what the test covers.
        Verifies that subscribers only receive events of the types
        they subscribed to.

        Expected Result:
        - Event type filtering is accurate.
        - Different event types are handled independently.
        - No cross-contamination between event types.
        """
        trade_events = []
        kline_events = []

        def trade_handler(event: BaseEvent[Any]) -> None:
            trade_events.append(event)

        def kline_handler(event: BaseEvent[Any]) -> None:
            kline_events.append(event)

        # Subscribe to different event types
        trade_sub_id = event_bus.subscribe(EventType.TRADE, trade_handler)
        kline_sub_id = event_bus.subscribe(EventType.KLINE, kline_handler)

        # Publish different event types
        trade_event = MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000})
        kline_event = MockEvent(EventType.KLINE, "BTCUSDT", {"ohlc": [50000, 51000, 49000, 50500]})
        other_event = MockEvent(EventType.CONNECTION, "BTCUSDT", {"data": "test"})

        await event_bus.publish(trade_event)
        await event_bus.publish(kline_event)
        await event_bus.publish(other_event)

        await asyncio.sleep(0.001)

        # Check that handlers only received their event types
        assert len(trade_events) == 1
        assert trade_events[0] == trade_event

        assert len(kline_events) == 1
        assert kline_events[0] == kline_event

        # Cleanup
        event_bus.unsubscribe(trade_sub_id)
        event_bus.unsubscribe(kline_sub_id)

    @pytest.mark.asyncio
    async def test_closed_state_handling(self, event_bus: MockEventBus) -> None:
        """Test that operations fail appropriately when event bus is closed.

        Description of what the test covers.
        Verifies that attempting to use a closed event bus raises
        appropriate exceptions.

        Expected Result:
        - Operations raise `RuntimeError` when bus is closed.
        - `is_closed` property works correctly.
        - Error messages are clear and helpful.
        """
        # Test initial state
        assert not event_bus.is_closed

        # Close the event bus
        await event_bus.close()
        assert event_bus.is_closed

        # Test that operations fail when closed
        test_event: MockEvent = MockEvent(EventType.SYSTEM, "BTCUSDT")  # type: ignore[unreachable]

        with pytest.raises(RuntimeError):
            await event_bus.publish(test_event)

        with pytest.raises(RuntimeError):
            event_bus.subscribe(EventType.SYSTEM, lambda _e: None)

        # get_subscription_count should also fail when closed
        with pytest.raises(RuntimeError):
            event_bus.get_subscription_count()

        # Test that unsubscribe operations also fail when closed
        with pytest.raises(RuntimeError):
            event_bus.unsubscribe("test_sub_id")

        with pytest.raises(RuntimeError):
            event_bus.unsubscribe_all()

        with pytest.raises(RuntimeError):
            event_bus.unsubscribe_all(EventType.TRADE)

        # Test that wait_for also fails when closed
        with pytest.raises(RuntimeError):
            await event_bus.wait_for(EventType.SYSTEM, timeout=0.1)

    @pytest.mark.asyncio
    async def test_handler_error_resilience(self, event_bus: MockEventBus) -> None:
        """Test that handler errors don't break the event bus.

        Description of what the test covers.
        Verifies that if one handler throws an exception, other handlers
        still get called and the event bus continues to work.

        Expected Result:
        - Handler errors are contained.
        - Other handlers still receive events.
        - Event bus remains operational.
        """
        successful_events = []

        def failing_handler(_event: BaseEvent[Any]) -> None:
            raise ValueError("Handler error")

        def successful_handler(event: BaseEvent[Any]) -> None:
            successful_events.append(event)

        # Subscribe both handlers
        failing_sub_id = event_bus.subscribe(EventType.ERROR, failing_handler)
        successful_sub_id = event_bus.subscribe(EventType.ERROR, successful_handler)

        # Publish event
        test_event = MockEvent(EventType.ERROR, "BTCUSDT", {"price": 50000})
        await event_bus.publish(test_event)

        await asyncio.sleep(0.001)

        # Successful handler should still have received the event
        assert len(successful_events) == 1
        assert successful_events[0] == test_event

        # Event bus should still be operational
        assert not event_bus.is_closed

        # Cleanup
        event_bus.unsubscribe(failing_sub_id)
        event_bus.unsubscribe(successful_sub_id)

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_event(self, event_bus: MockEventBus) -> None:
        """Test that multiple subscribers can listen to the same event type.

        Description of what the test covers.
        Verifies that events are delivered to all subscribers of the
        same event type.

        Expected Result:
        - All subscribers receive the event.
        - Event delivery is reliable.
        - Order of handler execution is not guaranteed but all are called.
        """
        received_counts = {"handler1": 0, "handler2": 0, "handler3": 0}

        def create_handler(name: str) -> Callable[[BaseEvent[Any]], None]:
            def handler(_event: BaseEvent[Any]) -> None:
                received_counts[name] += 1

            return handler

        # Subscribe multiple handlers to same event type
        handlers = {}
        for name in received_counts:
            handler = create_handler(name)
            sub_id = event_bus.subscribe(EventType.CONNECTION, handler)
            handlers[name] = sub_id

        # Publish event
        test_event = MockEvent(EventType.CONNECTION, "BTCUSDT", {"price": 50000})
        await event_bus.publish(test_event)

        await asyncio.sleep(0.001)

        # All handlers should have received the event
        assert all(count == 1 for count in received_counts.values())

        # Cleanup
        for sub_id in handlers.values():
            event_bus.unsubscribe(sub_id)

    def test_subscribe_invalid_handler_type(self, event_bus: MockEventBus) -> None:
        """Test that invalid handler types raise ValueError.

        Description of what the test covers.
        Verifies that passing non-callable objects as handlers raises
        appropriate ValueError exceptions.

        Expected Result:
        - Non-callable objects (None, string, int, etc.) raise ValueError.
        - Error message is clear and helpful.
        - Event bus remains operational after error.
        """
        # Test with None
        with pytest.raises(ValueError, match="Handler must be callable"):
            event_bus.subscribe(EventType.TRADE, None)  # type: ignore[arg-type]

        # Test with string
        with pytest.raises(ValueError, match="Handler must be callable"):
            event_bus.subscribe(EventType.TRADE, "not_callable")  # type: ignore[arg-type]

        # Test with integer
        with pytest.raises(ValueError, match="Handler must be callable"):
            event_bus.subscribe(EventType.TRADE, 42)  # type: ignore[arg-type]

        # Test with dict
        with pytest.raises(ValueError, match="Handler must be callable"):
            event_bus.subscribe(EventType.TRADE, {"not": "callable"})  # type: ignore[arg-type]

        # Verify event bus is still operational
        assert not event_bus.is_closed
        assert event_bus.get_subscription_count() == 0

    @pytest.mark.asyncio
    async def test_wait_for_timeout_zero(self, event_bus: MockEventBus) -> None:
        """Test that wait_for with timeout=0 raises TimeoutError immediately.

        Description of what the test covers.
        Verifies that setting timeout=0 in wait_for causes an immediate
        TimeoutError to be raised without waiting.

        Expected Result:
        - TimeoutError is raised immediately.
        - No actual waiting occurs.
        - Event bus remains operational.
        """
        # Test with timeout=0 should raise TimeoutError immediately
        with pytest.raises(asyncio.TimeoutError):
            await event_bus.wait_for(EventType.TRADE, timeout=0)

        # Verify event bus is still operational
        assert not event_bus.is_closed

    @pytest.mark.asyncio
    async def test_wait_for_always_false_filter(self, event_bus: MockEventBus) -> None:
        """Test wait_for with filter function that always returns False.

        Description of what the test covers.
        Verifies that a filter function that always returns False
        causes wait_for to timeout even when matching events are published.

        Expected Result:
        - TimeoutError is raised when filter never matches.
        - Events are published but filtered out.
        - Event bus remains operational.
        """

        # Define a filter that always returns False
        def always_false_filter(_event: BaseEvent[Any]) -> bool:
            return False

        # Start a task that publishes events
        async def publish_events() -> None:
            await asyncio.sleep(0.01)
            for i in range(3):
                test_event = MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000 + i})
                await event_bus.publish(test_event)
                await asyncio.sleep(0.01)

        publish_task = asyncio.create_task(publish_events())

        # wait_for should timeout because filter never matches
        with pytest.raises(asyncio.TimeoutError):
            await event_bus.wait_for(EventType.TRADE, timeout=0.1, filter_func=always_false_filter)

        await publish_task

        # Verify event bus is still operational
        assert not event_bus.is_closed

    @pytest.mark.asyncio
    async def test_publish_with_no_subscribers(self, event_bus: MockEventBus) -> None:
        """Test publishing events when there are no subscribers.

        Description of what the test covers.
        Verifies that publishing events to an event bus with no subscribers
        does not raise exceptions and completes successfully.

        Expected Result:
        - No exceptions are raised.
        - Publish completes successfully.
        - Event bus remains operational.
        """
        # Ensure no subscribers exist
        assert event_bus.get_subscription_count() == 0

        # Publish various types of events
        events = [
            MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000}),
            MockEvent(EventType.KLINE, "ETHUSDT", {"ohlc": [3000, 3100, 2900, 3050]}),
            MockEvent(EventType.SYSTEM, None, {"message": "test"}),
        ]

        # All publishes should succeed without error
        for event in events:
            await event_bus.publish(event)

        # Verify event bus is still operational
        assert not event_bus.is_closed
        assert event_bus.get_subscription_count() == 0

    @pytest.mark.asyncio
    async def test_handler_error_logging(self, event_bus: MockEventBus) -> None:
        """Test that handler errors are properly logged.

        Description of what the test covers.
        Verifies that when event handlers raise exceptions, the errors
        are properly logged and don't break the event bus operation.

        Expected Result:
        - Handler errors are logged to stdout/stderr.
        - Other handlers continue to receive events.
        - Event bus remains operational.
        """
        from unittest.mock import patch

        successful_events = []

        def failing_handler(_event: BaseEvent[Any]) -> None:
            raise ValueError("Test handler error")

        def successful_handler(event: BaseEvent[Any]) -> None:
            successful_events.append(event)

        # Subscribe both handlers
        failing_sub_id = event_bus.subscribe(EventType.TRADE, failing_handler)
        successful_sub_id = event_bus.subscribe(EventType.TRADE, successful_handler)

        # Patch print to capture error logging
        with patch("builtins.print") as mock_print:
            # Publish event
            test_event = MockEvent(EventType.TRADE, "BTCUSDT", {"price": 50000})
            await event_bus.publish(test_event)

            await asyncio.sleep(0.001)

            # Verify error was logged
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Handler error:" in call_args
            assert "Test handler error" in call_args

        # Verify successful handler still received the event
        assert len(successful_events) == 1
        assert successful_events[0] == test_event

        # Verify event bus is still operational
        assert not event_bus.is_closed

        # Cleanup
        event_bus.unsubscribe(failing_sub_id)
        event_bus.unsubscribe(successful_sub_id)
