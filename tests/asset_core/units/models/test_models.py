"""ABOUTME: Comprehensive unit tests for core data models
ABOUTME: Testing Trade, Kline, and related enum classes with proper Pydantic validation
"""

import typing
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide


@pytest.mark.unit
class TestTradeSide:
    """Unit tests for TradeSide enumeration."""

    def test_enum_values(self) -> None:
        """Test that TradeSide enum has correct values."""
        assert TradeSide.BUY.value == "buy"
        assert TradeSide.SELL.value == "sell"

    def test_enum_from_string(self) -> None:
        """Test creating TradeSide from string values."""
        assert TradeSide("buy") == TradeSide.BUY
        assert TradeSide("sell") == TradeSide.SELL

    def test_enum_invalid_value(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            TradeSide("invalid")


@pytest.mark.unit
class TestKlineInterval:
    """Unit tests for KlineInterval enumeration."""

    def test_enum_values(self) -> None:
        """Test that KlineInterval enum has correct string values."""
        assert KlineInterval.MINUTE_1.value == "1m"
        assert KlineInterval.HOUR_1.value == "1h"
        assert KlineInterval.DAY_1.value == "1d"
        assert KlineInterval.WEEK_1.value == "1w"
        assert KlineInterval.MONTH_1.value == "1M"

    def test_to_seconds_conversion(self) -> None:
        """Test conversion of intervals to seconds."""
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_1) == 60
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_5) == 300
        assert KlineInterval.to_seconds(KlineInterval.HOUR_1) == 3600
        assert KlineInterval.to_seconds(KlineInterval.DAY_1) == 86400
        assert KlineInterval.to_seconds(KlineInterval.WEEK_1) == 604800
        assert KlineInterval.to_seconds(KlineInterval.MONTH_1) == 2592000  # 30 days approximation

    def test_to_timedelta_conversion(self) -> None:
        """Test conversion of intervals to timedelta objects."""
        assert KlineInterval.to_timedelta(KlineInterval.MINUTE_1) == timedelta(minutes=1)
        assert KlineInterval.to_timedelta(KlineInterval.HOUR_1) == timedelta(hours=1)
        assert KlineInterval.to_timedelta(KlineInterval.DAY_1) == timedelta(days=1)

    def test_month_interval_approximation(self) -> None:
        """Test that MONTH_1 uses 30-day approximation as documented."""
        expected_seconds = 30 * 24 * 60 * 60  # 30 days in seconds
        assert KlineInterval.to_seconds(KlineInterval.MONTH_1) == expected_seconds


@pytest.mark.unit
class TestTradeValidation:
    """Unit tests for Trade model validation."""

    def test_valid_trade_creation(self) -> None:
        """Test creating a valid Trade instance."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.00"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=timestamp,
        )

        assert trade.symbol == "BTCUSDT"
        assert trade.trade_id == "12345"
        assert trade.price == Decimal("50000.00")
        assert trade.quantity == Decimal("0.001")
        assert trade.side == TradeSide.BUY
        assert trade.timestamp == timestamp

    def test_symbol_validation(self) -> None:
        """Test symbol field validation."""
        timestamp = datetime.now(UTC)

        # Valid symbols should work
        valid_symbols = ["BTCUSDT", "btcusdt", "  ETHBTC  "]
        for symbol in valid_symbols:
            trade = Trade(
                symbol=symbol,
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=timestamp,
            )
            assert trade.symbol == symbol.strip().upper()

        # Invalid symbols should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Trade(
                symbol="",
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=timestamp,
            )
        assert any("Symbol cannot be empty" in str(error) for error in exc_info.value.errors())

        # None symbol should raise ValidationError
        with pytest.raises(ValidationError):
            Trade(
                symbol=None,
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=timestamp,
            )

    @pytest.mark.skip(reason="待動態最小值分支處理 - 需要基於資產類型的動態最小值")
    def test_price_validation(self) -> None:
        """Test price field validation constraints."""
        timestamp = datetime.now(UTC)

        # Valid prices should work
        valid_prices = [
            Decimal("0.000000000001"),  # Minimum allowed
            Decimal("1.0"),
            Decimal("50000.0"),
            Decimal("1000000000"),  # Maximum allowed
        ]

        for price in valid_prices:
            trade = Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=price,
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=timestamp,
            )
            assert trade.price == price

        # Invalid prices should raise ValidationError
        invalid_prices = [
            Decimal("0"),
            Decimal("-1.0"),
            Decimal("0.0000000000001"),  # Below minimum
            Decimal("10000000000"),  # Above maximum
        ]

        for price in invalid_prices:
            with pytest.raises(ValidationError) as exc_info:
                Trade(
                    symbol="BTCUSDT",
                    trade_id="12345",
                    price=price,
                    quantity=Decimal("1.0"),
                    side=TradeSide.BUY,
                    timestamp=timestamp,
                )

            errors = exc_info.value.errors()
            assert any("price" in str(error).lower() for error in errors)

    @pytest.mark.skip(reason="待動態最小值分支處理 - 需要基於資產類型的動態最小值")
    def test_quantity_validation(self) -> None:
        """Test quantity field validation constraints."""
        timestamp = datetime.now(UTC)

        # Valid quantities should work
        valid_quantities = [
            Decimal("0.000000000001"),  # Minimum allowed
            Decimal("1.0"),
            Decimal("1000000.0"),  # Large quantity for meme coins
        ]

        for quantity in valid_quantities:
            trade = Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=quantity,
                side=TradeSide.BUY,
                timestamp=timestamp,
            )
            assert trade.quantity == quantity

        # Invalid quantities should raise ValidationError
        invalid_quantities = [
            Decimal("0"),
            Decimal("-1.0"),
            Decimal("0.0000000000001"),  # Below minimum
        ]

        for quantity in invalid_quantities:
            with pytest.raises(ValidationError) as exc_info:
                Trade(
                    symbol="BTCUSDT",
                    trade_id="12345",
                    price=Decimal("1.0"),
                    quantity=quantity,
                    side=TradeSide.BUY,
                    timestamp=timestamp,
                )

            errors = exc_info.value.errors()
            assert any("quantity" in str(error).lower() for error in errors)

    @pytest.mark.skip(reason="待動態最小值分支處理 - 需要基於資產類型的動態最小值")
    def test_volume_validation(self) -> None:
        """Test trade volume validation (price * quantity)."""
        timestamp = datetime.now(UTC)

        # Valid volume combinations should work
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1000.0"),
            quantity=Decimal("0.001"),  # Volume = 1.0
            side=TradeSide.BUY,
            timestamp=timestamp,
        )
        assert trade.volume == Decimal("1.0")

        # Invalid volume - too small
        with pytest.raises(ValidationError) as exc_info:
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("0.0001"),
                quantity=Decimal("0.001"),  # Volume = 0.0000001 < 0.001
                side=TradeSide.BUY,
                timestamp=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "below minimum allowed volume" in error_msg

        # Invalid volume - too large
        with pytest.raises(ValidationError) as exc_info:
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("1000000000"),
                quantity=Decimal("100"),  # Volume = 100B > 10B limit
                side=TradeSide.BUY,
                timestamp=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "exceeds maximum allowed volume" in error_msg

    def test_timezone_validation(self) -> None:
        """Test timezone validation for datetime fields."""
        # Naive datetime should be converted to UTC
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=naive_dt,
        )
        assert trade.timestamp.tzinfo == UTC

        # UTC datetime should remain UTC
        utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=utc_dt,
        )
        assert trade.timestamp.tzinfo == UTC
        assert trade.timestamp == utc_dt

    def test_optional_fields(self) -> None:
        """Test that optional fields work correctly."""
        timestamp = datetime.now(UTC)
        received_at = datetime.now(UTC)

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=timestamp,
            exchange="binance",
            maker_order_id="maker123",
            taker_order_id="taker456",
            is_buyer_maker=True,
            received_at=received_at,
            metadata={"source": "api"},
        )

        assert trade.exchange == "binance"
        assert trade.maker_order_id == "maker123"
        assert trade.taker_order_id == "taker456"
        assert trade.is_buyer_maker is True
        assert trade.received_at == received_at
        assert trade.metadata == {"source": "api"}

    def test_to_dict_serialization(self) -> None:
        """Test Trade to_dict method for JSON serialization."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.12345"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=timestamp,
        )

        data = trade.to_dict()

        # Check that Decimal fields are converted to strings
        assert isinstance(data["price"], str)
        assert isinstance(data["quantity"], str)
        assert isinstance(data["volume"], str)
        assert data["price"] == "50000.12345"
        assert data["quantity"] == "0.001"
        assert data["volume"] == "50.00012345"

        # Check that datetime is converted to ISO format
        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == "2023-01-01T12:00:00+00:00"

    def test_string_representation(self) -> None:
        """Test Trade string representation."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=timestamp,
        )

        str_repr = str(trade)
        assert "BTCUSDT" in str_repr
        assert "buy" in str_repr
        assert "0.001" in str_repr
        assert "50000" in str_repr
        assert "2023-01-01T12:00:00+00:00" in str_repr


@pytest.mark.unit
class TestKlineValidation:
    """Unit tests for Kline model validation."""

    def test_valid_kline_creation(self) -> None:
        """Test creating a valid Kline instance."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("50500.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("505000.0"),
            trades_count=100,
        )

        assert kline.symbol == "BTCUSDT"
        assert kline.interval == KlineInterval.HOUR_1
        assert kline.open_time == open_time
        assert kline.close_time == close_time

    def test_price_relationship_validation(self) -> None:
        """Test validation of price relationships (high >= low, etc.)."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Valid price relationships should work
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),  # Highest
            low_price=Decimal("49000.0"),  # Lowest
            close_price=Decimal("50500.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("505000.0"),
            trades_count=100,
        )
        assert kline.high_price >= kline.low_price
        assert kline.high_price >= kline.open_price
        assert kline.high_price >= kline.close_price

        # Invalid: high < low should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("49000.0"),  # Lower than low
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
            )

        error_msg = str(exc_info.value)
        assert "High price cannot be less than open price" in error_msg

        # Invalid: low > open should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("49000.0"),
                high_price=Decimal("51000.0"),
                low_price=Decimal("50000.0"),  # Higher than open
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
            )

        error_msg = str(exc_info.value)
        assert "Low price cannot be greater than open price" in error_msg

    def test_time_validation(self) -> None:
        """Test time-related validation."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Valid times should work
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )
        assert kline.duration == timedelta(hours=1)

        # Invalid: close_time <= open_time should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=close_time,  # Same as close time
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
            )

        error_msg = str(exc_info.value)
        assert "Close time must be after open time" in error_msg

    def test_volume_validation(self) -> None:
        """Test volume field validation."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Valid volumes (including zero) should work
        valid_volumes = [Decimal("0"), Decimal("10.0"), Decimal("1000.0")]

        for volume in valid_volumes:
            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=volume,
                quote_volume=volume * Decimal("50000.0"),
                trades_count=100,
            )
            assert kline.volume == volume

        # Invalid: negative volume should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("-1.0"),  # Negative
                quote_volume=Decimal("500000.0"),
                trades_count=100,
            )

        errors = exc_info.value.errors()
        assert any("Volume must be greater than or equal to 0" in str(error) for error in errors)

    def test_trades_count_validation(self) -> None:
        """Test trades_count field validation."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Valid trades count (including zero) should work
        valid_counts = [0, 1, 100, 10000]

        for count in valid_counts:
            kline = Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=count,
            )
            assert kline.trades_count == count

        # Invalid: negative trades count should raise ValidationError
        with pytest.raises(ValidationError):
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
                open_price=Decimal("50000.0"),
                high_price=Decimal("50000.0"),
                low_price=Decimal("50000.0"),
                close_price=Decimal("50000.0"),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=-1,  # Negative
            )

    def test_price_change_percent_division_by_zero(self) -> None:
        """Test that zero prices are properly rejected by validation."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Zero prices should be rejected during validation
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=open_time,
                close_time=close_time,
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

    def test_calculated_properties(self) -> None:
        """Test calculated properties of Kline."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        # Bullish kline
        bullish_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("50500.0"),  # Higher than open
            volume=Decimal("10.0"),
            quote_volume=Decimal("505000.0"),
            trades_count=100,
        )

        assert bullish_kline.is_bullish is True
        assert bullish_kline.is_bearish is False
        assert bullish_kline.price_change == Decimal("500.0")
        assert bullish_kline.price_change_percent == Decimal("1.0")  # 1% increase

        # Bearish kline
        bearish_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("49500.0"),  # Lower than open
            volume=Decimal("10.0"),
            quote_volume=Decimal("495000.0"),
            trades_count=100,
        )

        assert bearish_kline.is_bullish is False
        assert bearish_kline.is_bearish is True
        assert bearish_kline.price_change == Decimal("-500.0")
        assert bearish_kline.price_change_percent == Decimal("-1.0")  # 1% decrease

    def test_sequence_continuity_validation(self) -> None:
        """Test Kline sequence continuity validation."""
        # Create continuous sequence
        kline1 = Kline(
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

        kline2 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
            close_time=datetime(2023, 1, 1, 14, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        # Continuous sequence should validate
        assert Kline.validate_sequence_continuity([kline1, kline2]) is True

        # Gap in sequence should raise ValidationError
        kline3_with_gap = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=datetime(2023, 1, 1, 15, 0, 0, tzinfo=UTC),  # Gap here
            close_time=datetime(2023, 1, 1, 16, 0, 0, tzinfo=UTC),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        with pytest.raises(ValueError) as exc_info:
            Kline.validate_sequence_continuity([kline1, kline3_with_gap])

        assert "Gap detected between klines" in str(exc_info.value)

    def test_to_dict_serialization(self) -> None:
        """Test Kline to_dict method for JSON serialization."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.12345"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("50500.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("505000.0"),
            trades_count=100,
        )

        data = kline.to_dict()

        # Check that Decimal fields are converted to strings
        decimal_fields = ["open_price", "high_price", "low_price", "close_price", "volume", "quote_volume"]
        for field in decimal_fields:
            assert isinstance(data[field], str)

        # Check datetime conversion
        assert isinstance(data["open_time"], str)
        assert isinstance(data["close_time"], str)
        assert data["open_time"] == "2023-01-01T12:00:00+00:00"

        # Check calculated fields are included
        assert "price_change" in data
        assert "price_change_percent" in data
        assert isinstance(data["price_change"], str)
        assert isinstance(data["price_change_percent"], str)


@pytest.mark.unit
class TestModelConcurrency:
    """Unit tests for model thread safety and concurrent operations."""

    def test_trade_model_thread_safety(self) -> None:
        """Test that Trade model instances are thread-safe for read operations."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create a shared trade instance
        shared_trade = Trade(
            symbol="BTCUSDT",
            trade_id="thread_safe_test",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            exchange="binance",
        )

        results = []
        errors = []

        def read_trade_properties() -> dict[str, typing.Any]:
            """Read various properties from the shared trade."""
            try:
                return {
                    "symbol": shared_trade.symbol,
                    "price": shared_trade.price,
                    "volume": shared_trade.volume,
                    "json": shared_trade.model_dump_json(),
                    "dict": shared_trade.model_dump(),
                    "str": str(shared_trade),
                }
            except Exception as e:
                errors.append(e)
                raise

        # Run concurrent read operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_trade_properties) for _ in range(100)]

            for future in as_completed(futures):
                results.append(future.result())

        # Verify no errors occurred
        assert not errors
        assert len(results) == 100

        # Verify all results are consistent
        expected_symbol = shared_trade.symbol
        expected_price = shared_trade.price
        for result in results:
            assert result["symbol"] == expected_symbol
            assert result["price"] == expected_price
            assert isinstance(result["json"], str)
            assert isinstance(result["dict"], dict)

    def test_concurrent_trade_creation(self) -> None:
        """Test concurrent creation of Trade instances."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        created_trades = []
        errors = []
        lock = threading.Lock()

        def create_trade_batch(start_index: int, count: int) -> list[Trade]:
            """Create a batch of trades with unique IDs."""
            try:
                batch_trades = []
                for i in range(count):
                    trade = Trade(
                        symbol="BTCUSDT",
                        trade_id=f"concurrent_trade_{start_index + i}",
                        price=Decimal(f"{50000 + i}"),
                        quantity=Decimal("1.0"),
                        side=TradeSide.BUY if i % 2 == 0 else TradeSide.SELL,
                        timestamp=datetime.now(UTC),
                        exchange="binance",
                    )
                    batch_trades.append(trade)

                with lock:
                    created_trades.extend(batch_trades)

                return batch_trades
            except Exception as e:
                with lock:
                    errors.append(e)
                raise

        # Create trades concurrently across multiple threads
        batch_size = 10
        num_batches = 20
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_trade_batch, i * batch_size, batch_size) for i in range(num_batches)]

            batch_results = [future.result() for future in as_completed(futures)]

        # Verify no errors occurred
        assert not errors
        assert len(created_trades) == num_batches * batch_size

        # Verify batch results consistency
        assert len(batch_results) == num_batches
        total_from_batches = sum(len(batch) for batch in batch_results)
        assert total_from_batches == num_batches * batch_size

        # Verify all trade IDs are unique
        trade_ids = [trade.trade_id for trade in created_trades]
        assert len(set(trade_ids)) == len(trade_ids)

        # Verify all trades are valid
        for trade in created_trades:
            assert isinstance(trade, Trade)
            assert trade.symbol == "BTCUSDT"
            assert trade.price > 0

        # Verify batch results contain the same trades
        all_batch_trades = []
        for batch in batch_results:
            all_batch_trades.extend(batch)
        assert len(all_batch_trades) == len(created_trades)

    def test_kline_model_thread_safety(self) -> None:
        """Test that Kline model instances are thread-safe for read operations."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create a shared kline instance
        shared_kline = Kline(
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
            trades_count=500,
            exchange="binance",
        )

        results = []
        errors = []

        def read_kline_properties() -> dict[str, typing.Any]:
            """Read various properties from the shared kline."""
            try:
                return {
                    "symbol": shared_kline.symbol,
                    "price_change": shared_kline.price_change,
                    "price_change_percent": shared_kline.price_change_percent,
                    "json": shared_kline.model_dump_json(),
                    "dict": shared_kline.model_dump(),
                }
            except Exception as e:
                errors.append(e)
                raise

        # Run concurrent read operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_kline_properties) for _ in range(100)]

            for future in as_completed(futures):
                results.append(future.result())

        # Verify no errors occurred
        assert not errors
        assert len(results) == 100

        # Verify all results are consistent
        expected_symbol = shared_kline.symbol
        expected_price_change = shared_kline.price_change
        for result in results:
            assert result["symbol"] == expected_symbol
            assert result["price_change"] == expected_price_change
            assert isinstance(result["json"], str)
            assert isinstance(result["dict"], dict)
