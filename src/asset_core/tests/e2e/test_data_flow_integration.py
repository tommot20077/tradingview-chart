"""End-to-end integration tests for data flow.

This module tests the complete data flow pipeline from raw data ingestion
through processing, event publishing, storage, and downstream consumption,
ensuring all components work together correctly.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asset_core.events.bus import AbstractEventBus
from asset_core.models.events import BaseEvent, EventType, KlineEvent, TradeEvent
from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide
from asset_core.providers.base import AbstractDataProvider
from asset_core.storage.kline_repo import AbstractKlineRepository


class MockDataProvider(AbstractDataProvider):
    """Mock data provider for testing."""

    def __init__(self, name: str = "mock_provider") -> None:
        self._name = name
        self._connected = False
        self._trades: list[Trade] = []
        self._klines: list[Kline] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def stream_trades(self, symbol: str, *, start_from: datetime | None = None) -> AsyncIterator[Trade]:
        if not self._connected:
            raise ConnectionError("Provider not connected")

        for trade in self._trades:
            if trade.symbol == symbol:
                yield trade
                await asyncio.sleep(0.001)  # Simulate streaming delay

    async def stream_klines(
        self, symbol: str, interval: KlineInterval, *, start_from: datetime | None = None
    ) -> AsyncIterator[Kline]:
        if not self._connected:
            raise ConnectionError("Provider not connected")

        for kline in self._klines:
            if kline.symbol == symbol and kline.interval == interval:
                yield kline
                await asyncio.sleep(0.001)  # Simulate streaming delay

    async def fetch_historical_trades(
        self, symbol: str, start_time: datetime, end_time: datetime, *, limit: int | None = None
    ) -> list[Trade]:
        return [t for t in self._trades if t.symbol == symbol and start_time <= t.timestamp < end_time]

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Kline]:
        return [
            k
            for k in self._klines
            if k.symbol == symbol and k.interval == interval and start_time <= k.open_time < end_time
        ]

    async def get_exchange_info(self) -> dict[str, Any]:
        return {"name": self._name, "symbols": ["BTCUSDT", "ETHUSDT"]}

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "status": "TRADING"}

    async def ping(self) -> float:
        return 10.0

    async def close(self) -> None:
        self._connected = False

    def add_mock_trade(self, trade: Trade) -> None:
        """Add a mock trade for testing."""
        self._trades.append(trade)

    def add_mock_kline(self, kline: Kline) -> None:
        """Add a mock kline for testing."""
        self._klines.append(kline)


class MockKlineRepository(AbstractKlineRepository):
    """Mock kline repository for testing."""

    def __init__(self) -> None:
        self._klines: dict[tuple[str, KlineInterval, datetime], Kline] = {}
        self._closed = False

    async def save(self, kline: Kline) -> None:
        if self._closed:
            raise RuntimeError("Repository is closed")
        key = (kline.symbol, kline.interval, kline.open_time)
        self._klines[key] = kline

    async def save_batch(self, klines: list[Kline]) -> int:
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
        options: Any = None,
    ) -> list[Kline]:
        if self._closed:
            raise RuntimeError("Repository is closed")

        results = []
        for (s, i, t), kline in self._klines.items():
            if s == symbol and i == interval and start_time <= t < end_time:
                results.append(kline)

        return sorted(results, key=lambda k: k.open_time)

    async def stream(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        batch_size: int = 1000,
    ) -> AsyncIterator[Kline]:
        results = await self.query(symbol, interval, start_time, end_time)
        for kline in results:
            yield kline

    async def get_latest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        matching = [k for (s, i, _), k in self._klines.items() if s == symbol and i == interval]
        return max(matching, key=lambda k: k.open_time) if matching else None

    async def get_oldest(self, symbol: str, interval: KlineInterval) -> Kline | None:
        matching = [k for (s, i, _), k in self._klines.items() if s == symbol and i == interval]
        return min(matching, key=lambda k: k.open_time) if matching else None

    async def count(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
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
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[tuple[datetime, datetime]]:
        return []  # Simplified for testing

    async def get_statistics(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        count = await self.count(symbol, interval, start_time, end_time)
        return {"count": count, "symbol": symbol, "interval": interval.value}

    async def close(self) -> None:
        self._closed = True


class MockEventBus(AbstractEventBus):
    """Mock event bus for testing."""

    def __init__(self) -> None:
        self._events: list[BaseEvent] = []
        self._subscribers: dict[str, tuple[EventType, Any, str | None]] = {}
        self._closed = False

    async def publish(self, event: BaseEvent) -> None:
        if self._closed:
            raise RuntimeError("Event bus is closed")
        self._events.append(event)

        # Simulate event dispatch to subscribers
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
        sub_id = f"sub_{len(self._subscribers)}"
        self._subscribers[sub_id] = (event_type, handler, filter_symbol)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        return self._subscribers.pop(subscription_id, None) is not None

    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        if event_type is None:
            count = len(self._subscribers)
            self._subscribers.clear()
            return count

        to_remove = [sub_id for sub_id, (et, _, _) in self._subscribers.items() if et == event_type]

        for sub_id in to_remove:
            del self._subscribers[sub_id]

        return len(to_remove)

    async def close(self) -> None:
        self._closed = True

    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        if event_type is None:
            return len(self._subscribers)
        return len([1 for et, _, _ in self._subscribers.values() if et == event_type])

    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,
        filter_func: Any = None,
    ) -> BaseEvent | None:
        # Simplified implementation for testing
        for event in self._events:
            if event.event_type == event_type and (filter_func is None or filter_func(event)):
                return event
        return None

    @property
    def is_closed(self) -> bool:
        return self._closed

    def get_published_events(self) -> list[BaseEvent]:
        """Get all published events for testing."""
        return self._events.copy()


class TestDataFlowIntegration:
    """Integration tests for complete data flow pipeline.

    Summary line.

    Tests the end-to-end data flow from data providers through event processing
    to storage repositories, ensuring all components integrate correctly and
    data flows properly through the entire system.

    Preconditions:
    - Mock implementations of all components are available
    - Event system is properly configured
    - Storage systems are accessible

    Steps:
    - Set up complete data pipeline
    - Inject test data at entry points
    - Verify data flows through all stages
    - Validate final storage and processing results

    Expected Result:
    - Data flows correctly through all pipeline stages
    - Events are properly published and consumed
    - Storage operations complete successfully
    - No data loss or corruption occurs
    """

    @pytest.fixture
    def mock_provider(self) -> MockDataProvider:
        """Provide a mock data provider for testing."""
        return MockDataProvider("test_exchange")

    @pytest.fixture
    def mock_repository(self) -> MockKlineRepository:
        """Provide a mock kline repository for testing."""
        return MockKlineRepository()

    @pytest.fixture
    def mock_event_bus(self) -> MockEventBus:
        """Provide a mock event bus for testing."""
        return MockEventBus()

    @pytest.fixture
    def sample_trades(self) -> list[Trade]:
        """Provide sample trades for testing."""
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
        """Provide sample klines for testing."""
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

        Summary line.

        Tests the full pipeline of receiving trade data from a provider,
        processing it through the event system, and ensuring all events
        are properly published and can be consumed by subscribers.

        Preconditions:
        - Mock provider is configured with sample trades
        - Event bus is ready for publishing and subscribing
        - Sample trade data is available

        Steps:
        - Set up trade event subscribers
        - Connect provider and stream trades
        - Process trades through event system
        - Verify all events are published correctly

        Expected Result:
        - All trades are successfully streamed from provider
        - Trade events are published to event bus
        - Event subscribers receive all trade events
        - Data integrity is maintained throughout pipeline
        """
        # Set up sample trades in provider
        for trade in sample_trades:
            mock_provider.add_mock_trade(trade)

        # Set up event collection
        received_events: list[TradeEvent] = []

        def trade_handler(event: BaseEvent) -> None:
            if isinstance(event, TradeEvent):
                received_events.append(event)

        # Subscribe to trade events
        subscription_id = mock_event_bus.subscribe(EventType.TRADE, trade_handler, filter_symbol="BTCUSDT")

        # Connect provider and process trades
        await mock_provider.connect()

        try:
            # Stream trades and publish events
            async for trade in mock_provider.stream_trades("BTCUSDT"):
                trade_event = TradeEvent(source=mock_provider.name, symbol=trade.symbol, data=trade)
                await mock_event_bus.publish(trade_event)

            # Verify all trades were processed
            assert len(received_events) == len(sample_trades)

            # Verify event data integrity
            for i, event in enumerate(received_events):
                assert event.event_type == EventType.TRADE
                assert event.source == mock_provider.name
                assert event.symbol == "BTCUSDT"
                assert event.data.trade_id == sample_trades[i].trade_id
                assert event.data.price == sample_trades[i].price
                assert event.data.quantity == sample_trades[i].quantity

            # Verify event bus state
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

        Summary line.

        Tests the process of aggregating individual trade data into kline
        candlesticks and storing them in the repository, including event
        publishing for completed klines.

        Preconditions:
        - Sample trade data is available
        - Repository is ready for storage operations
        - Event bus can handle kline events

        Steps:
        - Aggregate trades into klines by time periods
        - Store klines in repository
        - Publish kline events for each completed kline
        - Verify storage and event publishing

        Expected Result:
        - Trades are correctly aggregated into klines
        - Klines are stored in repository without errors
        - Kline events are published for each stored kline
        - OHLC data is calculated correctly from trades
        """
        # Group trades by minute for kline aggregation
        kline_data: dict[datetime, list[Trade]] = {}

        for trade in sample_trades:
            # Round timestamp to minute for 1-minute klines
            minute_time = trade.timestamp.replace(second=0, microsecond=0)
            if minute_time not in kline_data:
                kline_data[minute_time] = []
            kline_data[minute_time].append(trade)

        # Set up event collection
        received_kline_events: list[KlineEvent] = []

        def kline_handler(event: BaseEvent) -> None:
            if isinstance(event, KlineEvent):
                received_kline_events.append(event)

        subscription_id = mock_event_bus.subscribe(EventType.KLINE, kline_handler)

        try:
            created_klines = []

            # Aggregate trades into klines
            for open_time, trades in kline_data.items():
                if not trades:
                    continue

                # Calculate OHLC from trades
                prices = [t.price for t in trades]
                open_price = trades[0].price  # First trade price
                close_price = trades[-1].price  # Last trade price
                high_price = max(prices)
                low_price = min(prices)
                volume = sum(t.quantity for t in trades)
                quote_volume = sum(t.price * t.quantity for t in trades)

                # Create kline
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

                # Store kline
                await mock_repository.save(kline)
                created_klines.append(kline)

                # Publish kline event
                kline_event = KlineEvent(source="aggregator", symbol=kline.symbol, data=kline)
                await mock_event_bus.publish(kline_event)

            # Verify klines were stored
            stored_count = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert stored_count == len(created_klines)

            # Verify event publishing
            assert len(received_kline_events) == len(created_klines)

            # Verify kline data integrity
            for _i, event in enumerate(received_kline_events):
                assert event.event_type == EventType.KLINE
                assert event.symbol == "BTCUSDT"
                assert event.data.interval == KlineInterval.MINUTE_1
                assert event.data.trades_count > 0
                assert event.data.volume > 0

                # Verify OHLC relationships
                kline_data = event.data
                assert kline_data.low_price <= kline_data.open_price <= kline_data.high_price
                assert kline_data.low_price <= kline_data.close_price <= kline_data.high_price

            # Test querying stored klines
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

        Summary line.

        Tests how the system handles various error conditions in the data
        pipeline, including provider disconnections, storage failures,
        and event system errors, ensuring graceful recovery.

        Preconditions:
        - System components are configured for error testing
        - Error injection mechanisms are available
        - Recovery procedures are implemented

        Steps:
        - Inject various error conditions at different pipeline stages
        - Verify error detection and handling
        - Test recovery mechanisms
        - Ensure data consistency after recovery

        Expected Result:
        - Errors are properly detected and handled
        - System recovers gracefully from failures
        - Data integrity is maintained during error conditions
        - Error events are published for monitoring
        """
        # Set up error event collection
        error_events: list[BaseEvent] = []

        def error_handler(event: BaseEvent) -> None:
            if event.event_type == EventType.ERROR:
                error_events.append(event)

        error_subscription = mock_event_bus.subscribe(EventType.ERROR, error_handler)

        try:
            # Test 1: Provider connection error
            with pytest.raises(ConnectionError):
                async for _ in mock_provider.stream_trades("BTCUSDT"):
                    pass  # Should fail because provider not connected

            # Publish error event for connection failure
            from asset_core.models.events import ErrorEvent

            connection_error = ErrorEvent(
                error="Provider connection failed", error_code="CONN_001", source="data_processor"
            )
            await mock_event_bus.publish(connection_error)

            # Test 2: Storage error simulation
            await mock_repository.close()  # Close repository to simulate error

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

            # Try to save to closed repository
            with pytest.raises(RuntimeError, match="Repository is closed"):
                await mock_repository.save(sample_kline)

            # Publish storage error event
            storage_error = ErrorEvent(
                error="Storage operation failed", error_code="STORE_001", source="storage_manager"
            )
            await mock_event_bus.publish(storage_error)

            # Test 3: Recovery simulation
            # Recreate repository (simulate recovery)
            recovered_repository = MockKlineRepository()

            # Verify recovery works
            await recovered_repository.save(sample_kline)
            stored_count = await recovered_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert stored_count == 1

            # Connect provider (simulate recovery)
            await mock_provider.connect()
            assert mock_provider.is_connected

            # Test 4: Event system error handling
            await mock_event_bus.close()  # Close event bus

            # Try to publish to closed event bus
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

            # Verify error events were collected
            assert len(error_events) == 2  # Connection error and storage error
            assert all(e.event_type == EventType.ERROR for e in error_events)

            # Test data consistency after partial failures
            # Verify that successfully stored data is still intact
            latest_kline = await recovered_repository.get_latest("BTCUSDT", KlineInterval.MINUTE_1)
            assert latest_kline is not None
            assert latest_kline.symbol == "BTCUSDT"
            assert latest_kline.volume == Decimal("100")

        finally:
            # Cleanup - this might fail if event bus is closed, which is expected
            with contextlib.suppress(RuntimeError):
                mock_event_bus.unsubscribe(error_subscription)

    @pytest.mark.asyncio
    async def test_backfill_integration(
        self, mock_provider: MockDataProvider, mock_repository: MockKlineRepository, sample_klines: list[Kline]
    ) -> None:
        """Test historical data backfill integration with real-time processing.

        Summary line.

        Tests the process of backfilling historical data while maintaining
        integration with real-time data processing, ensuring no gaps or
        duplicates occur during the transition.

        Preconditions:
        - Historical data is available from provider
        - Repository supports batch operations
        - Real-time processing is available

        Steps:
        - Perform historical data backfill
        - Start real-time data processing
        - Verify seamless transition between historical and real-time
        - Check for gaps or duplicates in data

        Expected Result:
        - Historical data is successfully backfilled
        - Real-time processing continues without gaps
        - No duplicate data is stored
        - Timeline continuity is maintained
        """
        # Set up historical data in provider
        for kline in sample_klines:
            mock_provider.add_mock_kline(kline)

        await mock_provider.connect()

        try:
            # Phase 1: Historical backfill
            start_time = datetime(2024, 1, 1, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)  # 1 hour of data

            # Fetch historical klines
            historical_klines = await mock_provider.fetch_historical_klines(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time
            )

            # Store historical data in batch
            stored_count = await mock_repository.save_batch(historical_klines)
            assert stored_count == len(historical_klines)

            # Verify historical data storage
            total_stored = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            assert total_stored == len(historical_klines)

            # Phase 2: Real-time processing simulation
            # Create additional real-time klines that continue from historical data
            latest_historical = await mock_repository.get_latest("BTCUSDT", KlineInterval.MINUTE_1)
            assert latest_historical is not None

            # Generate real-time klines starting after historical data
            realtime_klines = []
            next_time = latest_historical.close_time + timedelta(seconds=1)

            for i in range(10):  # 10 more klines for real-time simulation
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

            # Process real-time klines
            realtime_count = 0
            async for kline in mock_provider.stream_klines("BTCUSDT", KlineInterval.MINUTE_1):
                # Only process klines that are after historical data
                if kline.open_time > latest_historical.close_time:
                    await mock_repository.save(kline)
                    realtime_count += 1

                    # Stop after processing all real-time klines
                    if realtime_count >= len(realtime_klines):
                        break

            # Phase 3: Verify integration and continuity
            total_final_count = await mock_repository.count("BTCUSDT", KlineInterval.MINUTE_1)
            expected_total = len(historical_klines) + len(realtime_klines)
            assert total_final_count == expected_total

            # Verify chronological continuity
            all_stored_klines = await mock_repository.query(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, realtime_klines[-1].close_time + timedelta(seconds=1)
            )

            # Check that klines are in chronological order
            for i in range(1, len(all_stored_klines)):
                prev_kline = all_stored_klines[i - 1]
                curr_kline = all_stored_klines[i]
                assert curr_kline.open_time > prev_kline.open_time

                # Check for time continuity (allowing for small gaps)
                time_diff = curr_kline.open_time - prev_kline.close_time
                assert time_diff <= timedelta(seconds=2)  # Allow 1-2 second gap

            # Phase 4: Test gap detection
            gaps = await mock_repository.get_gaps(
                "BTCUSDT", KlineInterval.MINUTE_1, start_time, realtime_klines[-1].close_time
            )

            # Should have no gaps in our test data
            assert len(gaps) == 0

            # Verify statistics
            stats = await mock_repository.get_statistics("BTCUSDT", KlineInterval.MINUTE_1)
            assert stats["count"] == expected_total
            assert stats["symbol"] == "BTCUSDT"
            assert stats["interval"] == KlineInterval.MINUTE_1.value

        finally:
            await mock_provider.disconnect()
