"""Unit tests for Event models."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
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
from asset_core.models.kline import Kline
from asset_core.models.trade import Trade


@pytest.mark.unit
class TestEventType:
    """Test cases for EventType enum."""

    def test_event_type_values(self) -> None:
        """Test EventType enum string values."""
        assert EventType.TRADE.value == "trade"
        assert EventType.KLINE.value == "kline"
        assert EventType.ORDER.value == "order"
        assert EventType.BALANCE.value == "balance"
        assert EventType.CONNECTION.value == "connection"
        assert EventType.ERROR.value == "error"
        assert EventType.SYSTEM.value == "system"

    def test_event_type_string_conversion(self) -> None:
        """Test EventType enum value property access."""
        assert str(EventType.TRADE) == "trade"
        assert str(EventType.KLINE) == "kline"
        assert str(EventType.ERROR) == "error"


@pytest.mark.unit
class TestEventPriority:
    """Test cases for EventPriority enum."""

    def test_event_priority_values(self) -> None:
        """Test EventPriority enum integer values."""
        assert EventPriority.LOW.value == 0
        assert EventPriority.NORMAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.CRITICAL.value == 3

    def test_event_priority_ordering(self) -> None:
        """Test EventPriority enum comparison ordering."""
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL

    def test_event_priority_integer_conversion(self) -> None:
        """Test EventPriority conversion to integer."""
        assert int(EventPriority.LOW) == 0
        assert int(EventPriority.CRITICAL) == 3


@pytest.mark.unit
class TestBaseEventConstruction:
    """Test cases for BaseEvent model construction."""

    def test_valid_base_event_creation(self) -> None:
        """Test valid BaseEvent instance creation."""
        test_data = {"message": "test", "value": 123}
        event: BaseEvent[dict[str, Any]] = BaseEvent(event_type=EventType.SYSTEM, source="test_service", data=test_data)

        assert event.event_type == EventType.SYSTEM
        assert event.source == "test_service"
        assert event.data == test_data
        assert event.priority == EventPriority.NORMAL
        assert event.symbol is None
        assert event.correlation_id is None
        assert event.metadata == {}
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == UTC

    def test_event_id_uniqueness(self) -> None:
        """Test that event_id is unique across multiple BaseEvent instances."""
        # Create a large number of BaseEvent instances to test uniqueness
        num_events = 1000
        events = []

        for i in range(num_events):
            event: BaseEvent[dict[str, Any]] = BaseEvent(
                event_type=EventType.SYSTEM, source="test_service", data={"index": i}
            )
            events.append(event)

        # Collect all event IDs
        event_ids = [event.event_id for event in events]

        # Assert all event IDs are unique
        assert len(set(event_ids)) == num_events, "All event IDs should be unique"

        # Additional verification: check that all event IDs are valid UUIDs
        for event_id in event_ids:
            try:
                UUID(event_id)
            except ValueError:
                pytest.fail(f"event_id '{event_id}' is not a valid UUID")

    def test_timestamp_precision_rapid_creation(self) -> None:
        """Test timestamp behavior when events are created rapidly."""
        import time

        # Create events in rapid succession
        events = []
        for i in range(10):
            event: BaseEvent[dict[str, Any]] = BaseEvent(
                event_type=EventType.SYSTEM, source="test_service", data={"index": i}
            )
            events.append(event)
            # Small delay to potentially create different timestamps
            time.sleep(0.001)  # 1ms delay

        # Collect all timestamps
        timestamps = [event.timestamp for event in events]

        # Even if some timestamps are identical, the event_id should ensure uniqueness
        # This test observes the timestamp behavior and verifies event_id uniqueness
        event_ids = [event.event_id for event in events]
        assert len(set(event_ids)) == len(events), "Event IDs should be unique even with rapid creation"

        # All timestamps should be valid UTC datetime objects
        for timestamp in timestamps:
            assert isinstance(timestamp, datetime)
            assert timestamp.tzinfo == UTC

    def test_metadata_default_factory_isolation(self) -> None:
        """Test that metadata default factory creates isolated dictionaries."""
        # Create two BaseEvent instances
        event1: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.SYSTEM, source="test_service", data={"key": "value1"}
        )

        event2: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.SYSTEM, source="test_service", data={"key": "value2"}
        )

        # Initially both metadata should be empty but separate
        assert event1.metadata == {}
        assert event2.metadata == {}
        assert event1.metadata is not event2.metadata, "Metadata dictionaries should be separate instances"

        # Modify metadata of event1
        event1.metadata["test_key"] = "test_value"
        event1.metadata["number"] = 42

        # Assert that event2's metadata remains unchanged
        assert event2.metadata == {}, "Event2 metadata should remain unchanged"
        assert "test_key" not in event2.metadata
        assert "number" not in event2.metadata

        # Verify event1's metadata has the changes
        assert event1.metadata["test_key"] == "test_value"
        assert event1.metadata["number"] == 42

    def test_base_event_with_all_fields(self) -> None:
        """Test BaseEvent creation with all optional fields provided."""
        test_data = {"key": "value"}
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        event: BaseEvent[dict[str, Any]] = BaseEvent(
            event_type=EventType.TRADE,
            source="binance",
            data=test_data,
            symbol="BTCUSDT",
            priority=EventPriority.HIGH,
            correlation_id="corr_123",
            timestamp=test_time,
            metadata={"source_type": "websocket"},
        )

        assert event.symbol == "BTCUSDT"
        assert event.priority == EventPriority.HIGH
        assert event.correlation_id == "corr_123"
        assert event.timestamp == test_time
        assert event.metadata == {"source_type": "websocket"}

    def test_base_event_auto_generated_fields(self) -> None:
        """Test automatic generation of event ID and timestamp."""
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={})

        assert isinstance(event.event_id, str)
        try:
            UUID(event.event_id)
        except ValueError:
            pytest.fail("event_id should be a valid UUID string")

        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == UTC

    def test_base_event_minimal_fields(self) -> None:
        """Test BaseEvent creation with only required fields."""
        event: BaseEvent[Any] = BaseEvent(
            event_type=EventType.ERROR, source="error_service", data={"error": "something went wrong"}
        )

        assert event.event_type == EventType.ERROR
        assert event.source == "error_service"
        assert event.data == {"error": "something went wrong"}


@pytest.mark.unit
class TestBaseEventValidation:
    """Test cases for BaseEvent model validation."""

    def test_symbol_validation_normalization(self) -> None:
        """Test symbol field validation and uppercase normalization."""
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.TRADE, source="test", data={}, symbol="  btcusdt  ")
        assert event.symbol == "BTCUSDT"

    def test_empty_symbol_validation(self) -> None:
        """Test empty symbol validation."""
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            BaseEvent(event_type=EventType.TRADE, source="test", data={}, symbol="")

    def test_whitespace_symbol_validation(self) -> None:
        """Test whitespace-only symbol validation."""
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            BaseEvent(event_type=EventType.TRADE, source="test", data={}, symbol="   ")

    def test_none_symbol_allowed(self) -> None:
        """Test None symbol is allowed."""
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, symbol=None)
        assert event.symbol is None

    def test_missing_required_fields(self) -> None:
        """Test missing required fields."""
        required_fields = ["event_type", "source", "data"]

        for field_to_remove in required_fields:
            data: dict[str, Any] = {"event_type": EventType.SYSTEM, "source": "test", "data": {}}
            del data[field_to_remove]

            with pytest.raises(ValidationError):
                BaseEvent(**data)


@pytest.mark.unit
class TestBaseEventTimezoneHandling:
    """Test cases for BaseEvent timezone handling."""

    def test_timezone_aware_timestamp(self) -> None:
        """Test timezone-aware timestamp handling."""
        utc_time = datetime.now(UTC)
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, timestamp=utc_time)
        assert event.timestamp.tzinfo == UTC

    def test_timezone_naive_timestamp_conversion(self) -> None:
        """Test timezone-naive timestamp is converted to UTC."""
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, timestamp=naive_time)
        assert event.timestamp.tzinfo == UTC
        assert event.timestamp.replace(tzinfo=None) == naive_time

    def test_timezone_conversion_to_utc(self) -> None:
        """Test timestamp from different timezone is converted to UTC."""
        est = timezone(timedelta(hours=-5))
        est_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)

        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, timestamp=est_time)

        assert event.timestamp.tzinfo == UTC
        expected_utc = datetime(2023, 1, 1, 17, 0, 0, tzinfo=UTC)
        assert event.timestamp == expected_utc


@pytest.mark.unit
class TestBaseEventSerialization:
    """Test cases for BaseEvent serialization."""

    def test_to_dict_conversion(self) -> None:
        """Test to_dict method."""
        test_data = {"key": "value", "number": 42}
        event: BaseEvent[Any] = BaseEvent(
            event_type=EventType.TRADE, source="binance", data=test_data, symbol="BTCUSDT"
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "trade"
        assert event_dict["source"] == "binance"
        assert event_dict["data"] == test_data
        assert event_dict["symbol"] == "BTCUSDT"
        assert isinstance(event_dict["timestamp"], str)
        assert event_dict["timestamp"].endswith("Z") or "+" in event_dict["timestamp"]

    def test_model_dump_json_serializable(self) -> None:
        """Test model can be dumped to JSON-serializable format."""
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={"test": "data"})

        data = event.model_dump()

        import json

        json_str = json.dumps(data, default=str)
        assert isinstance(json_str, str)


@pytest.mark.unit
class TestBaseEventStringRepresentation:
    """Test cases for BaseEvent string representation."""

    def test_string_representation(self) -> None:
        """Test string representation."""
        event: BaseEvent[Any] = BaseEvent(event_type=EventType.TRADE, source="binance", data={})

        str_repr = str(event)

        assert f"id={event.event_id}" in str_repr
        assert "type=trade" in str_repr
        assert "source=binance" in str_repr


@pytest.mark.unit
class TestTradeEvent:
    """Test cases for TradeEvent."""

    def test_trade_event_creation(self, sample_trade: Trade) -> None:
        """Test creating a TradeEvent."""
        event = TradeEvent(source="binance", data=sample_trade, symbol="BTCUSDT")

        assert event.event_type == EventType.TRADE
        assert event.source == "binance"
        assert event.data == sample_trade
        assert event.symbol == "BTCUSDT"
        assert isinstance(event.data, Trade)

    def test_trade_event_auto_type_setting(self, sample_trade: Trade) -> None:
        """Test TradeEvent automatically sets event_type."""
        event = TradeEvent(source="binance", data=sample_trade)

        assert event.event_type == EventType.TRADE

    def test_trade_event_is_immutable(self, sample_trade: Trade) -> None:
        """Test TradeEvent type is frozen."""
        event = TradeEvent(source="binance", data=sample_trade)

        with pytest.raises(ValidationError):
            event.event_type = EventType.SYSTEM  # type: ignore

    def test_trade_event_with_trade_data(self, sample_trade: Trade) -> None:
        """Test TradeEvent with actual trade data."""
        event = TradeEvent(source="binance", data=sample_trade, symbol="BTCUSDT")

        assert event.data.symbol == "BTCUSDT"
        assert event.data.price == Decimal("50000.50")
        assert event.data.side == "buy"


@pytest.mark.unit
class TestKlineEvent:
    """Test cases for KlineEvent."""

    def test_kline_event_creation(self, sample_kline: Kline) -> None:
        """Test creating a KlineEvent."""
        event = KlineEvent(source="binance", data=sample_kline, symbol="BTCUSDT")

        assert event.event_type == EventType.KLINE
        assert event.source == "binance"
        assert event.data == sample_kline
        assert event.symbol == "BTCUSDT"
        assert isinstance(event.data, Kline)

    def test_kline_event_auto_type_setting(self, sample_kline: Kline) -> None:
        """Test KlineEvent automatically sets event_type."""
        event = KlineEvent(source="binance", data=sample_kline)

        assert event.event_type == EventType.KLINE

    def test_kline_event_with_kline_data(self, sample_kline: Kline) -> None:
        """Test KlineEvent with actual kline data."""
        event = KlineEvent(source="binance", data=sample_kline, symbol="BTCUSDT")

        assert event.data.symbol == "BTCUSDT"
        assert event.data.interval == "1m"
        assert event.data.is_bullish is True


@pytest.mark.unit
class TestConnectionEvent:
    """Test cases for ConnectionEvent."""

    def test_connection_event_creation(self) -> None:
        """Test creating a ConnectionEvent."""
        event = ConnectionEvent(status=ConnectionStatus.CONNECTED, source="websocket_client")

        assert event.event_type == EventType.CONNECTION
        assert event.source == "websocket_client"
        assert event.data["status"] == "connected"

    def test_connection_event_with_additional_data(self) -> None:
        """Test ConnectionEvent with additional data."""
        event = ConnectionEvent(
            status=ConnectionStatus.CONNECTING,
            source="websocket_client",
            data={"url": "wss://stream.binance.com", "attempt": 1},
        )

        assert event.data["status"] == "connecting"
        assert event.data["url"] == "wss://stream.binance.com"
        assert event.data["attempt"] == 1

    def test_connection_status_values(self) -> None:
        """Test ConnectionStatus enum values."""
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.RECONNECTING.value == "reconnecting"
        assert ConnectionStatus.ERROR.value == "error"

    def test_connection_event_all_statuses(self) -> None:
        """Test ConnectionEvent with all status values."""
        statuses = [
            ConnectionStatus.CONNECTING,
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DISCONNECTED,
            ConnectionStatus.RECONNECTING,
            ConnectionStatus.ERROR,
        ]

        for status in statuses:
            event = ConnectionEvent(status=status, source="test_client")
            assert event.data["status"] == status.value

    def test_connection_event_invalid_status_type(self) -> None:
        """Test ConnectionEvent with non-ConnectionStatus value raises AttributeError."""
        # Test with various invalid status types
        invalid_statuses = [
            "invalid_string",  # String that's not a ConnectionStatus
            123,  # Integer
            None,  # None
            ["connected"],  # List
            {"status": "connected"},  # Dict
        ]

        for invalid_status in invalid_statuses:
            with pytest.raises(AttributeError):
                # This should raise AttributeError because status.value is called
                # but non-ConnectionStatus objects don't have a 'value' attribute
                ConnectionEvent(status=invalid_status, source="test_client")  # type: ignore


@pytest.mark.unit
class TestErrorEvent:
    """Test cases for ErrorEvent."""

    def test_error_event_creation(self) -> None:
        """Test creating an ErrorEvent."""
        event = ErrorEvent(error="Connection failed", source="websocket_client")

        assert event.event_type == EventType.ERROR
        assert event.priority == EventPriority.HIGH
        assert event.source == "websocket_client"
        assert event.data["error"] == "Connection failed"

    def test_error_event_with_error_code(self) -> None:
        """Test ErrorEvent with error code."""
        event = ErrorEvent(error="Invalid symbol", error_code="INVALID_SYMBOL", source="api_client")

        assert event.data["error"] == "Invalid symbol"
        assert event.data["error_code"] == "INVALID_SYMBOL"

    def test_error_event_high_priority_default(self) -> None:
        """Test ErrorEvent defaults to high priority."""
        event = ErrorEvent(error="Test error", source="test")

        assert event.priority == EventPriority.HIGH

    def test_error_event_with_custom_priority(self) -> None:
        """Test ErrorEvent with custom priority."""
        event = ErrorEvent(error="Minor warning", source="test", priority=EventPriority.LOW)

        assert event.priority == EventPriority.LOW

    def test_error_event_with_additional_data(self) -> None:
        """Test ErrorEvent with additional data."""
        event = ErrorEvent(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            source="validator",
            data={"field": "price", "value": "invalid"},
        )

        assert event.data["error"] == "Validation failed"
        assert event.data["error_code"] == "VALIDATION_ERROR"
        assert event.data["field"] == "price"
        assert event.data["value"] == "invalid"


@pytest.mark.unit
class TestEventBoundaryValues:
    """Test cases for Event models with boundary values."""

    def test_event_with_very_large_data(self) -> None:
        """Test event with large data payload."""
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data=large_data)

        assert len(event.data) == 1000
        assert event.data["key_999"] == "value_999"

    def test_event_with_nested_data(self) -> None:
        """Test event with deeply nested data."""
        nested_data = {
            "level1": {"level2": {"level3": {"value": "deep_value", "list": [1, 2, 3, {"nested_list": True}]}}}
        }

        event: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data=nested_data)

        assert event.data["level1"]["level2"]["level3"]["value"] == "deep_value"

    def test_event_with_edge_case_timestamps(self) -> None:
        """Test event with edge case timestamps."""
        old_timestamp = datetime(1970, 1, 1, tzinfo=UTC)
        event_old: BaseEvent[Any] = BaseEvent(
            event_type=EventType.SYSTEM, source="test", data={}, timestamp=old_timestamp
        )
        assert event_old.timestamp == old_timestamp

        future_timestamp = datetime(2050, 12, 31, tzinfo=UTC)
        event_future: BaseEvent[Any] = BaseEvent(
            event_type=EventType.SYSTEM, source="test", data={}, timestamp=future_timestamp
        )
        assert event_future.timestamp == future_timestamp


@pytest.mark.unit
class TestEventInvalidData:
    """Test cases for Event models with invalid data."""

    def test_invalid_event_type(self) -> None:
        """Test invalid event type."""
        with pytest.raises(ValidationError):
            BaseEvent(event_type="invalid_type", source="test", data={})

    def test_invalid_priority(self) -> None:
        """Test invalid priority."""
        with pytest.raises(ValidationError):
            BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, priority="invalid_priority")

    def test_invalid_timestamp_type(self) -> None:
        """Test invalid timestamp type."""
        with pytest.raises(ValidationError):
            BaseEvent(event_type=EventType.SYSTEM, source="test", data={}, timestamp="not_a_datetime")


@pytest.mark.unit
@pytest.mark.models
class TestEventIntegration:
    """Integration test cases for Event models."""

    def test_event_lifecycle_with_trade(self, sample_trade: Trade) -> None:
        """Test complete event lifecycle with trade data."""
        event = TradeEvent(
            source="binance",
            data=sample_trade,
            symbol="BTCUSDT",
            correlation_id="trade_batch_123",
            metadata={"latency_ms": 15},
        )

        assert event.event_type == EventType.TRADE
        assert event.data.volume == Decimal("50.00050")

        event_dict = event.to_dict()
        assert event_dict["correlation_id"] == "trade_batch_123"
        assert event_dict["metadata"]["latency_ms"] == 15

        str_repr = str(event)
        assert event.event_id in str_repr

    def test_event_lifecycle_with_kline(self, sample_kline: Kline) -> None:
        """Test complete event lifecycle with kline data."""
        event = KlineEvent(source="binance", data=sample_kline, symbol="BTCUSDT", priority=EventPriority.NORMAL)

        assert event.event_type == EventType.KLINE
        assert event.data.is_bullish is True

        event_dict = event.to_dict()
        assert event_dict["priority"] == 1

        _str_repr = str(event)

    def test_event_chain_with_correlation_id(self) -> None:
        """Test event chain using correlation ID."""
        correlation_id = "chain_123"

        conn_event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED, source="websocket", correlation_id=correlation_id
        )

        error_event = ErrorEvent(error="Connection lost", source="websocket", correlation_id=correlation_id)

        assert conn_event.correlation_id == correlation_id
        assert error_event.correlation_id == correlation_id
        assert conn_event.correlation_id == error_event.correlation_id

    def test_event_equality_and_uniqueness(self) -> None:
        """Test event equality and uniqueness."""
        event1: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={"key": "value"})

        event2: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={"key": "value"})

        assert event1 != event2
        assert event1.event_id != event2.event_id

        assert event1.data == event2.data
        assert event1.event_type == event2.event_type
        assert event1.source == event2.source
