#!/usr/bin/env python3
"""
Example: How to use the event system.

This example demonstrates how to:
1. Create and publish events
2. Subscribe to specific event types
3. Filter events by symbol
4. Handle events asynchronously
5. Implement custom event types
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from asset_core.events.bus import AbstractEventBus, AsyncEventHandler, EventHandler
from asset_core.models.events import (
    BaseEvent,
    ConnectionEvent,
    ConnectionStatus,
    ErrorEvent,
    EventPriority,
    EventType,
    TradeEvent,
)
from asset_core.models.trade import Trade, TradeSide


class InMemoryEventBus(AbstractEventBus):
    """Simple in-memory event bus implementation for demonstration."""

    def __init__(self):
        self._subscribers: dict[EventType, list[tuple]] = {}
        self._subscription_counter = 0
        self._closed = False
        self._events: list[BaseEvent] = []

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all subscribers."""
        if self._closed:
            raise RuntimeError("Event bus is closed")

        print(f"📡 Publishing event: {event.event_type} from {event.source}")
        self._events.append(event)

        # Notify subscribers
        if event.event_type in self._subscribers:
            for sub_id, handler, filter_symbol in self._subscribers[event.event_type]:
                # Apply symbol filter if specified
                if filter_symbol and event.symbol != filter_symbol:
                    continue

                try:
                    # Call handler (sync or async)
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    print(f"❌ Error in event handler {sub_id}: {e}")

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribe to events of a specific type."""
        if self._closed:
            raise RuntimeError("Event bus is closed")

        sub_id = f"sub_{self._subscription_counter}"
        self._subscription_counter += 1

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append((sub_id, handler, filter_symbol))

        filter_info = f" (symbol: {filter_symbol})" if filter_symbol else ""
        print(f"📫 Subscribed {sub_id} to {event_type}{filter_info}")

        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        for _event_type, subs in self._subscribers.items():
            for i, (sub_id, _handler, _filter_symbol) in enumerate(subs):
                if sub_id == subscription_id:
                    del subs[i]
                    print(f"📭 Unsubscribed {subscription_id}")
                    return True
        return False

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Unsubscribe all handlers."""
        if event_type:
            count = len(self._subscribers.get(event_type, []))
            self._subscribers[event_type] = []
            print(f"📭 Unsubscribed all handlers for {event_type} ({count} handlers)")
            return count
        else:
            total_count = sum(len(subs) for subs in self._subscribers.values())
            self._subscribers.clear()
            print(f"📭 Unsubscribed all handlers ({total_count} handlers)")
            return total_count

    async def close(self) -> None:
        """Close the event bus."""
        self._closed = True
        self._subscribers.clear()
        print("🔒 Event bus closed")

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Get number of active subscriptions."""
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
        """Wait for a specific event."""
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
        """Check if the event bus is closed."""
        return self._closed


class TradingAnalyzer:
    """Example class that analyzes trading events."""

    def __init__(self, event_bus: AbstractEventBus):
        self.event_bus = event_bus
        self.trade_count = 0
        self.total_volume = Decimal("0")

        # Subscribe to trade events
        self.event_bus.subscribe(EventType.TRADE, self.handle_trade_event)

    def handle_trade_event(self, event: BaseEvent) -> None:
        """Handle incoming trade events."""
        if isinstance(event, TradeEvent):
            trade = event.data
            self.trade_count += 1
            self.total_volume += trade.volume

            print(
                f"📈 Trade analyzed: {trade.symbol} {trade.side} "
                f"{trade.quantity}@{trade.price} (Volume: {trade.volume})"
            )
            print(f"   Total trades: {self.trade_count}, Total volume: {self.total_volume}")


class AlertSystem:
    """Example class that sends alerts based on events."""

    def __init__(self, event_bus: AbstractEventBus):
        self.event_bus = event_bus

        # Subscribe to error events with high priority
        self.event_bus.subscribe(EventType.ERROR, self.handle_error_event)

        # Subscribe to connection events
        self.event_bus.subscribe(EventType.CONNECTION, self.handle_connection_event)

    async def handle_error_event(self, event: BaseEvent) -> None:
        """Handle error events (async handler example)."""
        if isinstance(event, ErrorEvent):
            error_data = event.data

            print(f"🚨 ALERT: Error in {event.source}: {error_data.get('error', 'Unknown error')}")

            if event.priority == EventPriority.CRITICAL:
                print("🆘 CRITICAL ERROR - Immediate attention required!")

                # Simulate sending notification
                await asyncio.sleep(0.1)
                print("📧 Alert notification sent to administrators")

    def handle_connection_event(self, event: BaseEvent) -> None:
        """Handle connection status events."""
        if isinstance(event, ConnectionEvent):
            status = event.data.get("status")
            source = event.source

            if status == ConnectionStatus.CONNECTED.value:
                print(f"✅ Connection established: {source}")
            elif status == ConnectionStatus.DISCONNECTED.value:
                print(f"❌ Connection lost: {source}")
            elif status == ConnectionStatus.RECONNECTING.value:
                print(f"🔄 Reconnecting: {source}")


async def main():
    """Demonstrate event system usage."""

    print("🎯 Event System Example")
    print("=" * 50)

    # Create event bus
    event_bus = InMemoryEventBus()

    # Create event handlers
    analyzer = TradingAnalyzer(event_bus)
    _alert_system = AlertSystem(event_bus)  # Created for completeness, handles alerts internally

    try:
        # Example 1: Publishing trade events
        print("\n1️⃣ Publishing trade events:")

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="trade_001",
            price=Decimal("50000"),
            quantity=Decimal("0.1"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        trade_event = TradeEvent(
            source="binance",
            symbol="BTCUSDT",
            data=trade,
        )

        await event_bus.publish(trade_event)

        # Another trade
        trade2 = Trade(
            symbol="ETHUSDT",
            trade_id="trade_002",
            price=Decimal("3000"),
            quantity=Decimal("1.0"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        trade_event2 = TradeEvent(
            source="binance",
            symbol="ETHUSDT",
            data=trade2,
        )

        await event_bus.publish(trade_event2)

        # Example 2: Symbol-specific subscriptions
        print("\n2️⃣ Symbol-specific subscriptions:")

        btc_events = []

        def btc_only_handler(event: BaseEvent):
            btc_events.append(event)
            print(f"🟡 BTC-only handler: Received {event.event_type} for {event.symbol}")

        # Subscribe only to BTC events
        _btc_sub_id = event_bus.subscribe(EventType.TRADE, btc_only_handler, filter_symbol="BTCUSDT")

        # Publish more trades
        await event_bus.publish(trade_event)  # Should trigger BTC handler
        await event_bus.publish(trade_event2)  # Should NOT trigger BTC handler

        print(f"BTC handler received {len(btc_events)} events")

        # Example 3: Connection events
        print("\n3️⃣ Connection events:")

        connection_event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED,
            source="binance_ws",
        )
        await event_bus.publish(connection_event)

        disconnect_event = ConnectionEvent(
            status=ConnectionStatus.DISCONNECTED,
            source="binance_ws",
        )
        await event_bus.publish(disconnect_event)

        # Example 4: Error events with different priorities
        print("\n4️⃣ Error events:")

        warning_error = ErrorEvent(
            error="Rate limit warning",
            error_code="RATE_LIMIT_WARNING",
            source="binance_api",
            priority=EventPriority.NORMAL,
        )
        await event_bus.publish(warning_error)

        critical_error = ErrorEvent(
            error="Database connection failed",
            error_code="DB_CONN_FAILED",
            source="storage_service",
            priority=EventPriority.CRITICAL,
        )
        await event_bus.publish(critical_error)

        # Example 5: Waiting for specific events
        print("\n5️⃣ Waiting for specific events:")

        async def publish_delayed_event():
            await asyncio.sleep(0.5)
            system_event = BaseEvent(
                event_type=EventType.SYSTEM,
                source="scheduler",
                data={"message": "System maintenance completed"},
            )
            await event_bus.publish(system_event)

        # Start background task
        asyncio.create_task(publish_delayed_event())

        print("⏳ Waiting for system event...")
        result = await event_bus.wait_for(EventType.SYSTEM, timeout=2.0)

        if result:
            print(f"✅ Received expected system event: {result.data}")
        else:
            print("⏰ Timeout waiting for system event")

        # Example 6: Custom event filtering
        print("\n6️⃣ Custom event filtering:")

        high_volume_trades = []

        def high_volume_filter(event: BaseEvent) -> bool:
            """Filter for high-volume trades only."""
            if isinstance(event, TradeEvent):
                return event.data.volume > Decimal("1000")
            return False

        def high_volume_handler(event: BaseEvent):
            high_volume_trades.append(event)
            trade = event.data
            print(f"💰 High volume trade: {trade.volume} {trade.symbol}")

        # Subscribe with custom logic (would need to implement in real event bus)
        event_bus.subscribe(EventType.TRADE, high_volume_handler)

        # Publish a high-volume trade
        big_trade = Trade(
            symbol="BTCUSDT",
            trade_id="big_trade_001",
            price=Decimal("50000"),
            quantity=Decimal("0.05"),  # Volume = 2500 > 1000
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        big_trade_event = TradeEvent(
            source="whale_trader",
            symbol="BTCUSDT",
            data=big_trade,
        )

        await event_bus.publish(big_trade_event)

        # Show final statistics
        print("\n📊 Final Statistics:")
        print(f"Total subscriptions: {event_bus.get_subscription_count()}")
        print(f"Trade events processed: {analyzer.trade_count}")
        print(f"Total trading volume: {analyzer.total_volume}")

    finally:
        # Clean up
        await event_bus.close()


if __name__ == "__main__":
    asyncio.run(main())
