"""ABOUTME: Comprehensive validation tests for all data models
ABOUTME: Testing complex validation scenarios, edge cases, and model interactions
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

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
class TestEventTypeAndPriority:
    """Unit tests for Event enumeration types."""

    def test_event_type_values(self) -> None:
        """Test EventType enum values."""
        assert EventType.TRADE.value == "trade"
        assert EventType.KLINE.value == "kline"
        assert EventType.ORDER.value == "order"
        assert EventType.BALANCE.value == "balance"
        assert EventType.CONNECTION.value == "connection"
        assert EventType.ERROR.value == "error"
        assert EventType.SYSTEM.value == "system"

    def test_event_type_string_conversion(self) -> None:
        """Test EventType string conversion."""
        assert str(EventType.TRADE) == "trade"
        assert str(EventType.ERROR) == "error"

    def test_event_priority_values(self) -> None:
        """Test EventPriority enum values."""
        assert EventPriority.LOW.value == 0
        assert EventPriority.NORMAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.CRITICAL.value == 3

    def test_event_priority_ordering(self) -> None:
        """Test that event priorities can be ordered."""
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL

    def test_connection_status_values(self) -> None:
        """Test ConnectionStatus enum values."""
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.RECONNECTING.value == "reconnecting"
        assert ConnectionStatus.ERROR.value == "error"


@pytest.mark.unit
class TestBaseEventValidation:
    """Unit tests for BaseEvent validation."""

    def test_valid_base_event_creation(self) -> None:
        """Test creating a valid BaseEvent instance."""
        test_data = {"test": "data"}
        event = BaseEvent[dict](event_type=EventType.SYSTEM, source="test_source", data=test_data)

        assert event.event_type == EventType.SYSTEM
        assert event.source == "test_source"
        assert event.data == test_data
        assert event.priority == EventPriority.NORMAL  # Default
        assert event.symbol is None  # Default
        assert event.correlation_id is None  # Default
        assert isinstance(event.metadata, dict)
        assert event.metadata == {}  # Default empty dict

    def test_auto_generated_fields(self) -> None:
        """Test that auto-generated fields work correctly."""
        event = BaseEvent[str](event_type=EventType.SYSTEM, source="test_source", data="test")

        # event_id should be auto-generated UUID
        assert isinstance(event.event_id, str)
        assert len(event.event_id) > 0

        # timestamp should be auto-generated and recent
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == UTC
        time_diff = datetime.now(UTC) - event.timestamp
        assert time_diff < timedelta(seconds=1)  # Should be very recent

    def test_symbol_validation(self) -> None:
        """Test symbol field validation."""
        # Valid symbols should work
        valid_symbols = ["BTCUSDT", "btcusdt", "  ETHBTC  "]
        for symbol in valid_symbols:
            event = BaseEvent[str](event_type=EventType.TRADE, source="test_source", symbol=symbol, data="test")
            assert event.symbol == symbol.strip().upper()

        # None symbol should work (optional field)
        event = BaseEvent[str](event_type=EventType.TRADE, source="test_source", symbol=None, data="test")
        assert event.symbol is None

        # Empty symbol should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseEvent[str](event_type=EventType.TRADE, source="test_source", symbol="", data="test")
        assert any("Symbol cannot be empty" in str(error) for error in exc_info.value.errors())

        # Non-string symbol should raise ValidationError
        with pytest.raises(ValidationError):
            BaseEvent[str](
                event_type=EventType.TRADE,
                source="test_source",
                symbol=123,
                data="test",
            )

    def test_timestamp_timezone_validation(self) -> None:
        """Test timestamp timezone validation."""
        # Naive datetime should be converted to UTC
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)
        event = BaseEvent[str](event_type=EventType.SYSTEM, source="test_source", data="test", timestamp=naive_dt)
        assert event.timestamp.tzinfo == UTC

        # UTC datetime should remain UTC
        utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = BaseEvent[str](event_type=EventType.SYSTEM, source="test_source", data="test", timestamp=utc_dt)
        assert event.timestamp.tzinfo == UTC
        assert event.timestamp == utc_dt

    def test_optional_fields(self) -> None:
        """Test optional fields work correctly."""
        correlation_id = str(uuid4())
        metadata = {"source_detail": "api", "version": "1.0"}

        event = BaseEvent[dict](
            event_type=EventType.TRADE,
            source="binance",
            symbol="BTCUSDT",
            data={"price": "50000"},
            priority=EventPriority.HIGH,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        assert event.priority == EventPriority.HIGH
        assert event.correlation_id == correlation_id
        assert event.metadata == metadata

    def test_to_dict_serialization(self) -> None:
        """Test BaseEvent to_dict method."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = BaseEvent[dict](
            event_type=EventType.TRADE, source="binance", symbol="BTCUSDT", data={"price": "50000"}, timestamp=timestamp
        )

        data = event.to_dict()

        # Check that timestamp is converted to ISO format
        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == "2023-01-01T12:00:00+00:00"

        # Check other fields are preserved
        assert data["event_type"] == "trade"
        assert data["source"] == "binance"
        assert data["symbol"] == "BTCUSDT"
        assert data["data"] == {"price": "50000"}

    def test_string_representation(self) -> None:
        """Test BaseEvent string representation."""
        event = BaseEvent[str](event_id="test-id-123", event_type=EventType.TRADE, source="binance", data="test")

        str_repr = str(event)
        assert "BaseEvent" in str_repr
        assert "test-id-123" in str_repr
        assert "trade" in str_repr
        assert "binance" in str_repr


@pytest.mark.unit
class TestTradeEventValidation:
    """Unit tests for TradeEvent validation."""

    def test_valid_trade_event_creation(self) -> None:
        """Test creating a valid TradeEvent instance."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        event = TradeEvent(source="binance", data=trade)

        assert event.event_type == EventType.TRADE
        assert event.source == "binance"
        assert event.data == trade
        assert isinstance(event.data, Trade)

    def test_trade_event_type_frozen(self) -> None:
        """Test that TradeEvent event_type cannot be changed."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Should not be able to override event_type
        event = TradeEvent(
            source="binance",
            data=trade,
            event_type=EventType.ERROR,  # This should be ignored
        )

        # Should still be TRADE
        assert event.event_type == EventType.TRADE

    def test_trade_event_data_validation(self) -> None:
        """Test that TradeEvent validates the Trade data."""
        # Invalid trade data should raise ValidationError
        with pytest.raises(ValidationError):
            TradeEvent(
                source="binance",
                data="not a trade object",
            )

    def test_trade_event_symbol_consistency(self) -> None:
        """Test symbol consistency between event and trade data."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Symbol on event should be independent of trade symbol
        event = TradeEvent(
            source="binance",
            symbol="ETHUSDT",  # Different from trade symbol
            data=trade,
        )

        assert event.symbol == "ETHUSDT"
        assert event.data.symbol == "BTCUSDT"


@pytest.mark.unit
class TestKlineEventValidation:
    """Unit tests for KlineEvent validation."""

    def test_valid_kline_event_creation(self) -> None:
        """Test creating a valid KlineEvent instance."""
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            close_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("50500.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("505000.0"),
            trades_count=100,
        )

        event = KlineEvent(source="binance", data=kline)

        assert event.event_type == EventType.KLINE
        assert event.source == "binance"
        assert event.data == kline
        assert isinstance(event.data, Kline)

    def test_kline_event_type_frozen(self) -> None:
        """Test that KlineEvent event_type cannot be changed."""
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

        # Should not be able to override event_type
        event = KlineEvent(
            source="binance",
            data=kline,
            event_type=EventType.TRADE,  # This should be ignored
        )

        # Should still be KLINE
        assert event.event_type == EventType.KLINE


@pytest.mark.unit
class TestConnectionEventValidation:
    """Unit tests for ConnectionEvent validation."""

    def test_valid_connection_event_creation(self) -> None:
        """Test creating a valid ConnectionEvent instance."""
        event = ConnectionEvent(status=ConnectionStatus.CONNECTED, source="websocket_client")

        assert event.event_type == EventType.CONNECTION
        assert event.source == "websocket_client"
        assert event.data["status"] == "connected"

    def test_connection_event_with_additional_data(self) -> None:
        """Test ConnectionEvent with additional data."""
        event = ConnectionEvent(
            status=ConnectionStatus.DISCONNECTED,
            source="websocket_client",
            data={"reason": "network_error", "retry_count": 3},
        )

        assert event.event_type == EventType.CONNECTION
        assert event.data["status"] == "disconnected"
        assert event.data["reason"] == "network_error"
        assert event.data["retry_count"] == 3

    def test_connection_event_all_statuses(self) -> None:
        """Test ConnectionEvent with all possible statuses."""
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


@pytest.mark.unit
class TestErrorEventValidation:
    """Unit tests for ErrorEvent validation."""

    def test_valid_error_event_creation(self) -> None:
        """Test creating a valid ErrorEvent instance."""
        event = ErrorEvent(error="Connection failed", source="websocket_client")

        assert event.event_type == EventType.ERROR
        assert event.source == "websocket_client"
        assert event.data["error"] == "Connection failed"
        assert event.priority == EventPriority.HIGH  # Default for errors

    def test_error_event_with_error_code(self) -> None:
        """Test ErrorEvent with error code."""
        event = ErrorEvent(error="Invalid symbol", error_code="INVALID_SYMBOL", source="api_client")

        assert event.data["error"] == "Invalid symbol"
        assert event.data["error_code"] == "INVALID_SYMBOL"

    def test_error_event_with_additional_data(self) -> None:
        """Test ErrorEvent with additional data."""
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

    def test_error_event_custom_priority(self) -> None:
        """Test ErrorEvent with custom priority."""
        event = ErrorEvent(error="Minor warning", source="logger", priority=EventPriority.LOW)

        assert event.priority == EventPriority.LOW


@pytest.mark.unit
class TestModelComplexValidationScenarios:
    """Test complex validation scenarios across models."""

    @pytest.mark.skip(reason="待動態最小值分支處理 - 需要基於資產類型的動態最小值")
    def test_trade_with_extreme_values(self) -> None:
        """Test Trade model with extreme but valid values."""
        # Test minimum values
        min_trade = Trade(
            symbol="DOGE",
            trade_id="min_trade",
            price=Decimal("0.000000000001"),  # Minimum price
            quantity=Decimal("0.000000000001"),  # Minimum quantity
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        assert min_trade.volume == Decimal("0.000000000000000001")
        assert min_trade.volume >= Decimal("0.001")  # Should pass volume validation

    def test_kline_with_zero_open_price_edge_case(self) -> None:
        """Test that Kline model properly rejects zero prices during validation."""
        # Business logic: Zero prices are invalid in real financial markets
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="TESTCOIN",
                interval=KlineInterval.MINUTE_1,
                open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
                close_time=datetime(2023, 1, 1, 12, 1, 0, tzinfo=UTC),
                open_price=Decimal("0"),  # Invalid: zero price
                high_price=Decimal("1.0"),
                low_price=Decimal("1.0"),
                close_price=Decimal("1.0"),
                volume=Decimal("100"),
                quote_volume=Decimal("100"),
                trades_count=1,
            )

        # Verify validation error mentions price requirement
        assert any("Price must be greater than 0" in str(error) for error in exc_info.value.errors())

    def test_kline_interval_time_alignment(self) -> None:
        """Test Kline time alignment validation for different intervals."""
        # 1-hour kline should start at the top of the hour
        valid_hour_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),  # Top of hour
            close_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        assert valid_hour_kline.duration == timedelta(hours=1)

        # Misaligned time should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=datetime(2023, 1, 1, 12, 30, 0, tzinfo=UTC),  # Not top of hour
                close_time=datetime(2023, 1, 1, 13, 30, 0, tzinfo=UTC),
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
            )

        error_msg = str(exc_info.value)
        assert "not aligned to interval" in error_msg

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

    def test_cross_model_symbol_validation_consistency(self) -> None:
        """Test that symbol validation is consistent across all models."""
        timestamp = datetime.now(UTC)

        # All models should handle symbols consistently
        test_symbols = ["BTCUSDT", "  ethusdt  ", "DOT"]

        for symbol in test_symbols:
            normalized_symbol = symbol.strip().upper()

            # Trade model
            trade = Trade(
                symbol=symbol,
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=timestamp,
            )
            assert trade.symbol == normalized_symbol

            # Kline model
            kline = Kline(
                symbol=symbol,
                interval=KlineInterval.HOUR_1,
                open_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
                close_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
                open_price=Decimal("1.0"),
                high_price=Decimal("1.0"),
                low_price=Decimal("1.0"),
                close_price=Decimal("1.0"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("1.0"),
                trades_count=1,
            )
            assert kline.symbol == normalized_symbol

            # BaseEvent model
            event = BaseEvent[str](event_type=EventType.SYSTEM, source="test", symbol=symbol, data="test")
            assert event.symbol == normalized_symbol

    def test_timezone_consistency_across_models(self) -> None:
        """Test that timezone handling is consistent across all models."""
        # Test naive datetime conversion
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)

        # Trade model
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=naive_dt,
        )
        assert trade.timestamp.tzinfo == UTC

        # Kline model
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=naive_dt,
            close_time=naive_dt + timedelta(hours=1),
            open_price=Decimal("1.0"),
            high_price=Decimal("1.0"),
            low_price=Decimal("1.0"),
            close_price=Decimal("1.0"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("1.0"),
            trades_count=1,
        )
        assert kline.open_time.tzinfo == UTC
        assert kline.close_time.tzinfo == UTC

        # BaseEvent model
        event = BaseEvent[str](event_type=EventType.SYSTEM, source="test", data="test", timestamp=naive_dt)
        assert event.timestamp.tzinfo == UTC
