"""Tests for asset_core models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from asset_core.models import (
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


@pytest.mark.unit
class TestTradeModel:
    """Test Trade model."""

    def test_trade_creation(self) -> None:
        """Test basic Trade model instance creation.

        Description of what the test covers:
        Verifies that Trade model can be created with required fields
        and that all field values are correctly stored and accessible.

        Preconditions:
        - Valid trade data for all required fields
        - Current UTC timestamp available

        Steps:
        - Create Trade instance with symbol, trade_id, price, quantity, side, timestamp
        - Verify all field values are stored correctly
        - Verify calculated volume property

        Expected Result:
        - All input values should be stored exactly as provided
        - Volume should be calculated as price * quantity
        - TradeSide enum should be converted to string value
        """
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
        """Test automatic symbol normalization to uppercase.

        Description of what the test covers:
        Verifies that Trade model automatically normalizes
        symbol values to uppercase regardless of input case.

        Preconditions:
        - Lowercase symbol value for testing normalization
        - Valid trade data for other required fields

        Steps:
        - Create Trade with lowercase symbol "btcusdt"
        - Verify symbol is automatically normalized to uppercase

        Expected Result:
        - Symbol should be stored as "BTCUSDT" (uppercase)
        - Other field values should remain unchanged
        """
        trade = Trade(
            symbol="btcusdt",
            trade_id="123",
            price=Decimal("1"),
            quantity=Decimal("1"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        assert trade.symbol == "BTCUSDT"

    def test_trade_timezone_handling(self) -> None:
        """Test automatic timezone conversion to UTC.

        Description of what the test covers:
        Verifies that Trade model automatically converts
        naive datetime values to UTC timezone.

        Preconditions:
        - Naive datetime (no timezone information)
        - Valid trade data for other required fields

        Steps:
        - Create Trade with naive datetime timestamp
        - Verify timestamp is automatically converted to UTC

        Expected Result:
        - Timestamp should have UTC timezone information
        - Original datetime value should be preserved
        """
        # Naive datetime should be treated as UTC
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="123",
            price=Decimal("1"),
            quantity=Decimal("1"),
            side=TradeSide.BUY,
            timestamp=naive_dt,
        )

        assert trade.timestamp.tzinfo == UTC

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


@pytest.mark.unit
class TestKlineModel:
    """Test Kline model."""

    def test_kline_creation(self) -> None:
        """Test creating a kline."""
        # Use aligned timestamp for 1-minute interval (aligned to minute boundary)
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
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

    def test_kline_validation(self) -> None:
        """Test kline validation."""
        open_time = datetime.now(UTC)

        # High must be >= all other prices
        with pytest.raises(ValueError, match="High price cannot be less than"):
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

        # Close time must be after open time
        with pytest.raises(ValueError, match="Close time must be after open time"):
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

    def test_kline_price_calculations(self) -> None:
        """Test price change calculations."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(minutes=1)
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time,
            close_time=close_time,
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
        open_time_bearish = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)
        close_time_bearish = open_time_bearish + timedelta(minutes=1)
        kline_bearish = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=open_time_bearish,
            close_time=close_time_bearish,
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


@pytest.mark.unit
class TestEventModels:
    """Test event models."""

    def test_base_event_creation(self) -> None:
        """Test creating a base event."""
        data = {"test": "data"}
        event: BaseEvent = BaseEvent(
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
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
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

        event = KlineEvent(
            source="binance",
            symbol="BTCUSDT",
            data=kline,
        )

        assert event.event_type == "kline"
        assert event.symbol == "BTCUSDT"
        assert isinstance(event.data, Kline)

    def test_event_priority(self) -> None:
        """Test event priority levels."""
        # Normal priority by default
        event1: BaseEvent = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data={},
        )
        assert event1.priority == EventPriority.NORMAL

        # High priority
        event2: BaseEvent = BaseEvent(
            event_type=EventType.ERROR,
            source="test",
            data={},
            priority=EventPriority.HIGH,
        )
        assert event2.priority == EventPriority.HIGH
