"""Tests for event bus interfaces."""

import asyncio
from abc import ABC
from collections.abc import Callable

import pytest

from src.asset_core.asset_core.events.bus import AbstractEventBus, AsyncEventHandler, \
    EventHandler
from src.asset_core.asset_core.models.events import BaseEvent, EventType


class MockEventBus(AbstractEventBus):
    """Mock implementation of AbstractEventBus for testing."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[tuple]] = {}
        self._subscription_counter = 0
        self._closed = False
        self._events: list[BaseEvent] = []

    async def publish(self, event: BaseEvent) -> None:
        """Mock event publishing."""
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
        """Mock subscription."""
        if self._closed:
            raise RuntimeError("Event bus is closed")

        sub_id = f"sub_{self._subscription_counter}"
        self._subscription_counter += 1

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append((sub_id, handler, filter_symbol))
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Mock unsubscription."""
        for _event_type, subs in self._subscribers.items():
            for i, (sub_id, _handler, _filter_symbol) in enumerate(subs):
                if sub_id == subscription_id:
                    del subs[i]
                    return True
        return False

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Mock unsubscribe all."""
        if event_type:
            count = len(self._subscribers.get(event_type, []))
            self._subscribers[event_type] = []
            return count
        else:
            total_count = sum(len(subs) for subs in self._subscribers.values())
            self._subscribers.clear()
            return total_count

    async def close(self) -> None:
        """Mock close."""
        self._closed = True
        self._subscribers.clear()

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Mock subscription count."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        else:
            return sum(len(subs) for subs in self._subscribers.values())

    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,
        filter_func: Callable[[BaseEvent], bool] | None = None,
    ) -> BaseEvent | None:
        """Mock wait for event."""
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
        return self._closed


@pytest.mark.unit
class TestAbstractEventBus:
    """Test AbstractEventBus interface."""

    def test_is_abstract(self) -> None:
        """Test that AbstractEventBus is abstract."""
        assert issubclass(AbstractEventBus, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            AbstractEventBus()

    @pytest.mark.asyncio
    async def test_mock_event_bus_basic_operations(self) -> None:
        """Test basic operations of mock event bus."""
        bus = MockEventBus()

        assert not bus.is_closed
        assert bus.get_subscription_count() == 0

        await bus.close()
        assert bus.is_closed

    @pytest.mark.asyncio
    async def test_mock_event_bus_subscription(self) -> None:
        """Test event subscription."""
        bus = MockEventBus()
        received_events = []

        def handler(event: BaseEvent) -> None:
            received_events.append(event)

        # Subscribe to trade events
        sub_id = bus.subscribe(EventType.TRADE, handler)
        assert isinstance(sub_id, str)
        assert bus.get_subscription_count(EventType.TRADE) == 1

        # Publish a trade event
        event = BaseEvent(
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
        """Test async event handler."""
        bus = MockEventBus()
        received_events = []

        async def async_handler(event: BaseEvent) -> None:
            received_events.append(event)

        # Subscribe with async handler
        _sub_id = bus.subscribe(EventType.TRADE, async_handler)

        # Publish event
        event = BaseEvent(
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
        """Test event filtering by symbol."""
        bus = MockEventBus()
        btc_events = []
        eth_events = []

        def btc_handler(event: BaseEvent) -> None:
            btc_events.append(event)

        def eth_handler(event: BaseEvent) -> None:
            eth_events.append(event)

        # Subscribe with symbol filters
        bus.subscribe(EventType.TRADE, btc_handler, filter_symbol="BTCUSDT")
        bus.subscribe(EventType.TRADE, eth_handler, filter_symbol="ETHUSDT")

        # Publish BTC event
        btc_event = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            symbol="BTCUSDT",
            data={"symbol": "BTCUSDT"},
        )
        await bus.publish(btc_event)

        # Publish ETH event
        eth_event = BaseEvent(
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
        """Test unsubscribing from events."""
        bus = MockEventBus()
        received_events = []

        def handler(event: BaseEvent) -> None:
            received_events.append(event)

        # Subscribe and then unsubscribe
        sub_id = bus.subscribe(EventType.TRADE, handler)
        assert bus.get_subscription_count(EventType.TRADE) == 1

        result = bus.unsubscribe(sub_id)
        assert result is True
        assert bus.get_subscription_count(EventType.TRADE) == 0

        # Publish event - should not be received
        event = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={"test": "data"},
        )
        await bus.publish(event)

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_mock_event_bus_unsubscribe_all(self) -> None:
        """Test unsubscribing all handlers."""
        bus = MockEventBus()

        def handler1(event: BaseEvent) -> None:
            pass

        def handler2(event: BaseEvent) -> None:
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
        """Test waiting for specific events."""
        bus = MockEventBus()

        # Start waiting for event in background
        async def wait_and_publish() -> None:
            await asyncio.sleep(0.05)  # Small delay
            event = BaseEvent(
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
        """Test waiting for events with timeout."""
        bus = MockEventBus()

        # Wait for event that won't come
        result = await bus.wait_for(EventType.TRADE, timeout=0.1)

        assert result is None

    @pytest.mark.asyncio
    async def test_mock_event_bus_closed_operations(self) -> None:
        """Test operations on closed event bus."""
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
