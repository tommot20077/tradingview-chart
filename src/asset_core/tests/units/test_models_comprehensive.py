"""Comprehensive tests for asset_core models with improved coverage."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.models import (
    BaseEvent,
    EventPriority,
    EventType,
    Kline,
    KlineEvent,
    KlineInterval,
    Trade,
    TradeEvent,
    TradeSide,
)
from src.asset_core.asset_core.models.events import ConnectionEvent, ConnectionStatus, \
    ErrorEvent


@pytest.mark.unit
class TestTradeModelComprehensive:
    """Comprehensive tests for Trade model."""

    def test_trade_creation_valid(self) -> None:
        """Test creating a valid trade."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123456",
            price=Decimal("50000.50"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        assert trade.symbol == "BTCUSDT"
        assert trade.trade_id == "123456"
        assert trade.price == Decimal("50000.50")
        assert trade.quantity == Decimal("0.001")
        assert trade.side == "buy"
        assert trade.volume == Decimal("50.0005")

    def test_trade_symbol_normalization(self) -> None:
        """Test symbol normalization."""
        trade = Trade(
            symbol="btcusdt",  # lowercase input
            trade_id="123",
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        assert trade.symbol == "BTCUSDT"  # should be uppercase

    def test_trade_timezone_handling(self) -> None:
        """Test timezone handling."""
        # Naive datetime should be treated as UTC
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123",
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
            side=TradeSide.BUY,
            timestamp=naive_dt,
        )

        assert trade.timestamp.tzinfo == UTC

    def test_trade_invalid_price(self) -> None:
        """Test validation for invalid prices."""
        with pytest.raises(ValidationError):
            Trade(
                symbol="BTCUSDT",
                trade_id="123",
                price=Decimal("0"),  # Invalid: zero price
                quantity=Decimal("0.01"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

        with pytest.raises(ValidationError):
            Trade(
                symbol="BTCUSDT",
                trade_id="123",
                price=Decimal("-100"),  # Invalid: negative price
                quantity=Decimal("0.01"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_trade_invalid_quantity(self) -> None:
        """Test validation for invalid quantities."""
        with pytest.raises(ValidationError):
            Trade(
                symbol="BTCUSDT",
                trade_id="123",
                price=Decimal("50000"),
                quantity=Decimal("0"),  # Invalid: zero quantity
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_trade_volume_validation(self) -> None:
        """Test trade volume validation."""
        # Volume too small
        with pytest.raises(ValidationError, match="Trade volume.*is below minimum"):
            Trade(
                symbol="BTCUSDT",
                trade_id="123",
                price=Decimal("0.00000001"),
                quantity=Decimal("0.00000001"),  # Volume = 0.0000000000000001
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_trade_to_dict(self) -> None:
        """Test converting trade to dictionary."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123",
            price=Decimal("50000.50"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            exchange="binance",
        )

        data = trade.to_dict()
        assert data["symbol"] == "BTCUSDT"
        assert data["price"] == "50000.5"
        assert data["quantity"] == "0.001"
        assert data["volume"] == "50.0005"
        assert data["side"] == "buy"
        assert data["exchange"] == "binance"
        assert "timestamp" in data

    def test_trade_with_optional_fields(self) -> None:
        """Test trade with optional fields."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123",
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            exchange="binance",
            maker_order_id="maker123",
            taker_order_id="taker456",
            is_buyer_maker=True,
            received_at=datetime.now(UTC),
            metadata={"source": "websocket"},
        )

        assert trade.exchange == "binance"
        assert trade.maker_order_id == "maker123"
        assert trade.taker_order_id == "taker456"
        assert trade.is_buyer_maker is True
        assert trade.received_at is not None
        assert trade.metadata["source"] == "websocket"


@pytest.mark.unit
class TestKlineModelComprehensive:
    """Comprehensive tests for Kline model."""

    def test_kline_creation_valid(self) -> None:
        """Test creating a valid kline."""
        # Use aligned time for 1-minute interval
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(minutes=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("100"),
            quote_volume=Decimal("5000000"),
            trades_count=1000,
        )

        assert kline.symbol == "BTCUSDT"
        assert kline.interval == "1m"
        assert kline.open_price == Decimal("50000")
        assert kline.high_price == Decimal("50100")
        assert kline.low_price == Decimal("49900")
        assert kline.close_price == Decimal("50050")
        assert kline.price_change == Decimal("50")
        assert kline.is_bullish is True
        assert kline.is_bearish is False

    def test_kline_interval_conversion(self) -> None:
        """Test interval conversion methods."""
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_1) == 60
        assert KlineInterval.to_seconds(KlineInterval.HOUR_1) == 3600
        assert KlineInterval.to_seconds(KlineInterval.DAY_1) == 86400

        assert KlineInterval.to_timedelta(KlineInterval.MINUTE_5) == timedelta(minutes=5)
        assert KlineInterval.to_timedelta(KlineInterval.HOUR_4) == timedelta(hours=4)

    def test_kline_price_validation(self) -> None:
        """Test kline price validation."""
        # Use aligned time for 1-minute interval
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # High must be >= all other prices
        with pytest.raises(ValidationError, match="High price cannot be less than"):
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=open_time,
                close_time=open_time + timedelta(minutes=1),
                open_price=Decimal("100"),
                high_price=Decimal("90"),  # Invalid: less than open
                low_price=Decimal("90"),
                close_price=Decimal("100"),
                volume=Decimal("1"),
                quote_volume=Decimal("100"),
                trades_count=1,
            )

    def test_kline_time_validation(self) -> None:
        """Test kline time validation."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Close time must be after open time
        with pytest.raises(ValidationError, match="Close time must be after open time"):
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=open_time,
                close_time=open_time - timedelta(minutes=1),  # Invalid: before open
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("1"),
                quote_volume=Decimal("100"),
                trades_count=1,
            )

    def test_kline_time_alignment_validation(self) -> None:
        """Test kline time alignment validation."""
        # Non-aligned time should fail
        non_aligned_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)  # 30 seconds offset

        with pytest.raises(ValidationError, match="is not aligned to interval.*boundaries"):
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=non_aligned_time,
                close_time=non_aligned_time + timedelta(minutes=1),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("1"),
                quote_volume=Decimal("100"),
                trades_count=1,
            )

    def test_kline_price_calculations(self) -> None:
        """Test price change calculations."""
        # Use aligned time for 1-minute interval
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time,
            close_time=open_time + timedelta(minutes=1),
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("1000"),
            quote_volume=Decimal("100000"),
            trades_count=100,
        )

        assert kline.price_change == Decimal("5")
        assert kline.price_change_percent == Decimal("5")

        # Test bearish kline
        open_time_bearish = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        kline_bearish = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time_bearish,
            close_time=open_time_bearish + timedelta(minutes=1),
            open_price=Decimal("100"),
            high_price=Decimal("100"),
            low_price=Decimal("90"),
            close_price=Decimal("95"),
            volume=Decimal("1000"),
            quote_volume=Decimal("95000"),
            trades_count=100,
        )

        assert kline_bearish.price_change == Decimal("-5")
        assert kline_bearish.price_change_percent == Decimal("-5")
        assert kline_bearish.is_bearish is True
        assert kline_bearish.is_bullish is False

    def test_kline_to_dict(self) -> None:
        """Test converting kline to dictionary."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time,
            close_time=open_time + timedelta(minutes=1),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("100"),
            quote_volume=Decimal("5000000"),
            trades_count=1000,
        )

        data = kline.to_dict()
        assert data["symbol"] == "BTCUSDT"
        assert data["open_price"] == "50000"
        assert data["high_price"] == "50100"
        assert data["low_price"] == "49900"
        assert data["close_price"] == "50050"
        assert data["price_change"] == "50"
        assert data["price_change_percent"] == "0.100"


@pytest.mark.unit
class TestEventModelsComprehensive:
    """Comprehensive tests for event models."""

    def test_base_event_creation(self) -> None:
        """Test creating a base event."""
        data = {"test": "data"}
        event = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data=data,
        )

        assert event.event_type == "system"
        assert event.source == "test"
        assert event.data == data
        assert event.priority == EventPriority.NORMAL
        assert event.event_id is not None
        assert event.timestamp.tzinfo == UTC

    def test_trade_event(self) -> None:
        """Test trade event."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123",
            price=Decimal("50000"),
            quantity=Decimal("0.1"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        event = TradeEvent(
            source="binance",
            symbol="BTCUSDT",
            data=trade,
        )

        assert event.event_type == "trade"
        assert event.symbol == "BTCUSDT"
        assert isinstance(event.data, Trade)

    def test_kline_event(self) -> None:
        """Test kline event."""
        # Use aligned time for 1-minute interval
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time,
            close_time=open_time + timedelta(minutes=1),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("100"),
            quote_volume=Decimal("5000000"),
            trades_count=1000,
        )

        event = KlineEvent(
            source="binance",
            symbol="BTCUSDT",
            data=kline,
        )

        assert event.event_type == "kline"
        assert event.symbol == "BTCUSDT"
        assert isinstance(event.data, Kline)

    def test_connection_event(self) -> None:
        """Test connection event."""
        event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED,
            source="binance",
        )

        assert event.event_type == "connection"
        assert event.data["status"] == "connected"
        assert event.source == "binance"

    def test_error_event(self) -> None:
        """Test error event."""
        event = ErrorEvent(
            error="Connection failed",
            error_code="CONN_FAILED",
            source="binance",
        )

        assert event.event_type == "error"
        assert event.priority == EventPriority.HIGH
        assert event.data["error"] == "Connection failed"
        assert event.data["error_code"] == "CONN_FAILED"
        assert event.source == "binance"

    def test_event_priority(self) -> None:
        """Test event priority levels."""
        # Normal priority by default
        event1 = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data={},
        )
        assert event1.priority == EventPriority.NORMAL

        # High priority
        event2 = BaseEvent(
            event_type=EventType.ERROR,
            source="test",
            data={},
            priority=EventPriority.HIGH,
        )
        assert event2.priority == EventPriority.HIGH

    def test_event_symbol_validation(self) -> None:
        """Test event symbol validation."""
        # Symbol should be normalized to uppercase
        event = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            symbol="btcusdt",  # lowercase
            data={},
        )
        assert event.symbol == "BTCUSDT"

        # Empty symbol should raise error
        with pytest.raises(ValidationError):
            BaseEvent(
                event_type=EventType.TRADE,
                source="test",
                symbol="",  # empty
                data={},
            )

    def test_event_correlation_id(self) -> None:
        """Test event correlation ID functionality."""
        correlation_id = "test-correlation-123"

        event1 = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data={},
            correlation_id=correlation_id,
        )

        event2 = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={},
            correlation_id=correlation_id,
        )

        assert event1.correlation_id == correlation_id
        assert event2.correlation_id == correlation_id
        assert event1.correlation_id == event2.correlation_id

    def test_event_to_dict(self) -> None:
        """Test converting event to dictionary."""
        event = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data={"key": "value"},
            metadata={"extra": "data"},
        )

        data = event.to_dict()
        assert data["event_type"] == "system"
        assert data["source"] == "test"
        assert data["data"] == {"key": "value"}
        assert data["metadata"] == {"extra": "data"}
        assert "timestamp" in data
        assert "event_id" in data
