"""ABOUTME: Unit tests specifically for Event model functionality
ABOUTME: Testing event-specific validation and data consistency across all event types
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from asset_core.models.events import (
    BaseEvent,
    ConnectionEvent,
    ConnectionStatus,
    ErrorEvent,
    EventPriority,
    EventType,
    KlineEvent,
    TradeEvent,
)
from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide


@pytest.mark.unit
class TestEventBusinessLogic:
    """Unit tests for Event model business logic."""

    def test_base_event_auto_generation(self) -> None:
        """Test that BaseEvent auto-generates event_id and timestamp."""
        event: BaseEvent = BaseEvent(event_type=EventType.SYSTEM, source="test_service", data={"message": "test"})

        # Event ID should be auto-generated UUID
        assert isinstance(event.event_id, str)
        assert len(event.event_id) > 0
        # Verify it's a valid UUID
        UUID(event.event_id)  # Will raise ValueError if invalid

        # Timestamp should be auto-generated and recent
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == UTC
        time_diff = datetime.now(UTC) - event.timestamp
        assert time_diff < timedelta(seconds=1)  # Should be very recent

    def test_event_id_uniqueness(self) -> None:
        """Test that event IDs are unique across multiple events."""
        events = []
        for i in range(100):
            event: BaseEvent = BaseEvent(event_type=EventType.SYSTEM, source="test_service", data={"index": i})
            events.append(event)

        event_ids = [event.event_id for event in events]
        assert len(set(event_ids)) == 100  # All should be unique

    def test_symbol_validation_and_normalization(self) -> None:
        """Test symbol validation and normalization across event types."""
        # Valid symbols should be normalized
        valid_symbols = ["BTCUSDT", "btcusdt", "  ETHBTC  "]

        for symbol in valid_symbols:
            event: BaseEvent = BaseEvent(
                event_type=EventType.TRADE, source="test_source", symbol=symbol, data={"test": "data"}
            )
            assert event.symbol == symbol.strip().upper()

        # None symbol should work (optional field)
        event = BaseEvent(event_type=EventType.TRADE, source="test_source", symbol=None, data={"test": "data"})
        assert event.symbol is None

        # Empty symbol should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseEvent(event_type=EventType.TRADE, source="test_source", symbol="", data={"test": "data"})
        assert any("Symbol cannot be empty" in str(error) for error in exc_info.value.errors())

    def test_timezone_handling_consistency(self) -> None:
        """Test consistent timezone handling across all event types."""
        # Naive datetime should be converted to UTC
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)

        event: BaseEvent = BaseEvent(
            event_type=EventType.SYSTEM, source="test_source", data={"test": "data"}, timestamp=naive_dt
        )
        assert event.timestamp.tzinfo == UTC

        # UTC datetime should remain UTC
        utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = BaseEvent(event_type=EventType.SYSTEM, source="test_source", data={"test": "data"}, timestamp=utc_dt)
        assert event.timestamp.tzinfo == UTC
        assert event.timestamp == utc_dt

    def test_trade_event_type_consistency(self) -> None:
        """Test that TradeEvent enforces TRADE event type."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Should automatically set event_type to TRADE
        event = TradeEvent(source="binance", data=trade)
        assert event.event_type == EventType.TRADE

        # Should not be able to override event_type
        event = TradeEvent(
            source="binance",
            data=trade,
            event_type=EventType.ERROR,  # This should be ignored
        )
        assert event.event_type == EventType.TRADE  # Still TRADE

    def test_kline_event_type_consistency(self) -> None:
        """Test that KlineEvent enforces KLINE event type."""
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            close_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        # Should automatically set event_type to KLINE
        event = KlineEvent(source="binance", data=kline)
        assert event.event_type == EventType.KLINE

        # Should not be able to override event_type
        event = KlineEvent(
            source="binance",
            data=kline,
            event_type=EventType.TRADE,  # This should be ignored
        )
        assert event.event_type == EventType.KLINE  # Still KLINE

    def test_connection_event_status_handling(self) -> None:
        """Test ConnectionEvent status handling and data consistency."""
        # Test all connection statuses
        statuses = [
            ConnectionStatus.CONNECTING,
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DISCONNECTED,
            ConnectionStatus.RECONNECTING,
            ConnectionStatus.ERROR,
        ]

        for status in statuses:
            event = ConnectionEvent(status=status, source="websocket_client")
            assert event.event_type == EventType.CONNECTION
            assert event.data["status"] == status.value

        # Test with additional data
        event = ConnectionEvent(
            status=ConnectionStatus.DISCONNECTED,
            source="websocket_client",
            data={"reason": "network_error", "retry_count": 3},
        )

        assert event.event_type == EventType.CONNECTION
        assert event.data["status"] == "disconnected"
        assert event.data["reason"] == "network_error"
        assert event.data["retry_count"] == 3

    def test_error_event_priority_and_data(self) -> None:
        """Test ErrorEvent priority defaults and data handling."""
        # Test default high priority
        event = ErrorEvent(error="Connection failed", source="websocket_client")
        assert event.event_type == EventType.ERROR
        assert event.priority == EventPriority.HIGH  # Default for errors
        assert event.data["error"] == "Connection failed"

        # Test with error code
        event = ErrorEvent(error="Invalid symbol", error_code="INVALID_SYMBOL", source="api_client")
        assert event.data["error"] == "Invalid symbol"
        assert event.data["error_code"] == "INVALID_SYMBOL"

        # Test with additional data
        event = ErrorEvent(
            error="Rate limit exceeded",
            error_code="RATE_LIMIT",
            source="api_client",
            data={"retry_after": 60, "limit": 1200},
        )
        assert event.data["error"] == "Rate limit exceeded"
        assert event.data["error_code"] == "RATE_LIMIT"
        assert event.data["retry_after"] == 60
        assert event.data["limit"] == 1200

        # Test custom priority
        event = ErrorEvent(error="Minor warning", source="logger", priority=EventPriority.LOW)
        assert event.priority == EventPriority.LOW

    def test_event_data_type_consistency(self) -> None:
        """Test that event data types are consistent with their event types."""
        # TradeEvent should contain Trade data
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        trade_event = TradeEvent(source="binance", data=trade)
        assert isinstance(trade_event.data, Trade)
        assert trade_event.data.symbol == "BTCUSDT"

        # KlineEvent should contain Kline data
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            close_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        kline_event = KlineEvent(source="binance", data=kline)
        assert isinstance(kline_event.data, Kline)
        assert kline_event.data.symbol == "BTCUSDT"

    def test_event_serialization_consistency(self) -> None:
        """Test that all event types serialize consistently."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # BaseEvent serialization
        base_event: BaseEvent = BaseEvent(
            event_type=EventType.TRADE, source="binance", symbol="BTCUSDT", data={"price": "50000"}, timestamp=timestamp
        )

        data = base_event.to_dict()

        # Check that timestamp is converted to ISO format
        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == "2023-01-01T12:00:00+00:00"

        # Check other fields are preserved
        assert data["event_type"] == "trade"
        assert data["source"] == "binance"
        assert data["symbol"] == "BTCUSDT"
        assert data["data"] == {"price": "50000"}

    def test_event_priority_ordering(self) -> None:
        """Test that event priorities are correctly ordered."""
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL

        # Test integer values
        assert EventPriority.LOW.value == 0
        assert EventPriority.NORMAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.CRITICAL.value == 3

    def test_metadata_independence(self) -> None:
        """Test that metadata dictionaries are independent between events."""
        event1: BaseEvent = BaseEvent(event_type=EventType.SYSTEM, source="service1", data={"key": "value1"})

        event2: BaseEvent = BaseEvent(event_type=EventType.SYSTEM, source="service2", data={"key": "value2"})

        # Both should start with empty metadata
        assert event1.metadata == {}
        assert event2.metadata == {}
        assert event1.metadata is not event2.metadata  # Different objects

        # Modify event1's metadata
        event1.metadata["test_key"] = "test_value"
        event1.metadata["source_detail"] = "api"

        # event2's metadata should remain unchanged
        assert event2.metadata == {}
        assert "test_key" not in event2.metadata

        # Verify event1's changes
        assert event1.metadata["test_key"] == "test_value"
        assert event1.metadata["source_detail"] == "api"

    def test_correlation_id_functionality(self) -> None:
        """Test correlation ID functionality for event tracing."""
        correlation_id = "trace-12345"

        # Create related events with same correlation ID
        events: list[BaseEvent] = [
            BaseEvent(event_type=EventType.SYSTEM, source="service1", data={"step": 1}, correlation_id=correlation_id),
            BaseEvent(event_type=EventType.SYSTEM, source="service2", data={"step": 2}, correlation_id=correlation_id),
            BaseEvent(event_type=EventType.SYSTEM, source="service3", data={"step": 3}, correlation_id=correlation_id),
        ]

        # All should have the same correlation ID
        for event in events:
            assert event.correlation_id == correlation_id

        # But different event IDs
        event_ids = [event.event_id for event in events]
        assert len(set(event_ids)) == 3  # All unique

    def test_string_representation_consistency(self) -> None:
        """Test string representation across different event types."""
        # BaseEvent
        base_event: BaseEvent = BaseEvent(
            event_id="test-id-123", event_type=EventType.TRADE, source="binance", data={"test": "data"}
        )

        str_repr = str(base_event)
        assert "BaseEvent" in str_repr
        assert "test-id-123" in str_repr
        assert "trade" in str_repr
        assert "binance" in str_repr

        # TradeEvent
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        trade_event = TradeEvent(source="binance", data=trade)
        trade_str = str(trade_event)
        assert "TradeEvent" in trade_str or "BaseEvent" in trade_str
        assert "trade" in trade_str
        assert "binance" in trade_str

    def test_invalid_data_type_validation(self) -> None:
        """Test validation of invalid data types for events."""
        # TradeEvent should validate Trade data type
        with pytest.raises(ValidationError):
            TradeEvent(
                source="binance",
                data="not a trade object",
            )

        # KlineEvent should validate Kline data type
        with pytest.raises(ValidationError):
            KlineEvent(
                source="binance",
                data={"not": "a kline object"},
            )

    def test_event_type_enumeration_values(self) -> None:
        """Test that all EventType enumeration values are correct."""
        assert EventType.TRADE.value == "trade"
        assert EventType.KLINE.value == "kline"
        assert EventType.ORDER.value == "order"
        assert EventType.BALANCE.value == "balance"
        assert EventType.CONNECTION.value == "connection"
        assert EventType.ERROR.value == "error"
        assert EventType.SYSTEM.value == "system"

        # Test string conversion
        assert str(EventType.TRADE) == "trade"
        assert str(EventType.ERROR) == "error"

    def test_connection_status_enumeration_values(self) -> None:
        """Test that all ConnectionStatus enumeration values are correct."""
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.RECONNECTING.value == "reconnecting"
        assert ConnectionStatus.ERROR.value == "error"

    def test_extreme_data_handling(self) -> None:
        """Test event handling with extreme but valid data."""
        # Large data payload
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        event: BaseEvent = BaseEvent(event_type=EventType.SYSTEM, source="test_service", data=large_data)

        assert len(event.data) == 1000
        assert event.data["key_999"] == "value_999"

        # Deeply nested data
        nested_data = {"level1": {"level2": {"level3": {"value": "deep_value", "list": [1, 2, 3, {"nested": True}]}}}}

        event = BaseEvent(event_type=EventType.SYSTEM, source="test_service", data=nested_data)

        assert event.data["level1"]["level2"]["level3"]["value"] == "deep_value"
        assert event.data["level1"]["level2"]["level3"]["list"][3]["nested"] is True

    def test_edge_case_timestamps(self) -> None:
        """Test events with edge case timestamps."""
        # Very old timestamp
        old_time = datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)
        old_event: BaseEvent = BaseEvent(
            event_type=EventType.SYSTEM, source="test_service", data={"test": "old"}, timestamp=old_time
        )
        assert old_event.timestamp == old_time

        # Future timestamp
        future_time = datetime(2030, 12, 31, 23, 59, 59, tzinfo=UTC)
        future_event: BaseEvent = BaseEvent(
            event_type=EventType.SYSTEM, source="test_service", data={"test": "future"}, timestamp=future_time
        )
        assert future_event.timestamp == future_time
