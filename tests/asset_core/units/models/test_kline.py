"""ABOUTME: Unit tests specifically for Kline model functionality
ABOUTME: Testing Kline-specific validation and calculated properties including DivisionByZeroError handling
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from asset_core.models.kline import Kline, KlineInterval


@pytest.mark.unit
class TestKlineBusinessLogic:
    """Unit tests for Kline model business logic."""

    def test_price_change_calculation(self) -> None:
        """Test that price_change is calculated correctly."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

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

        assert kline.price_change == Decimal("500.0")

    def test_price_change_percent_calculation(self) -> None:
        """Test that price_change_percent is calculated correctly."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("51000.0"),  # 2% increase
            volume=Decimal("10.0"),
            quote_volume=Decimal("510000.0"),
            trades_count=100,
        )

        assert kline.price_change_percent == Decimal("2.0")

    def test_price_change_percent_division_by_zero(self) -> None:
        """Test that zero prices are properly rejected by validation.

        Business logic: Zero prices are invalid in real financial markets.
        The model should reject such data during validation rather than handling division by zero.
        """
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        # Zero prices should be rejected during validation
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="TESTCOIN",
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

        # Verify the validation error mentions price requirement
        assert any("Price must be greater than 0" in str(error) for error in exc_info.value.errors())

    def test_bullish_bearish_detection(self) -> None:
        """Test bullish and bearish kline detection."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        # Bullish kline (close > open)
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

        # Bearish kline (close < open)
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

    def test_doji_kline_detection(self) -> None:
        """Test doji kline detection (open == close)."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        # Doji kline (close == open)
        doji_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("51000.0"),
            low_price=Decimal("49000.0"),
            close_price=Decimal("50000.0"),  # Same as open
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        assert doji_kline.is_bullish is False
        assert doji_kline.is_bearish is False
        assert doji_kline.price_change == Decimal("0")
        assert doji_kline.price_change_percent == Decimal("0")

    def test_duration_calculation(self) -> None:
        """Test that duration is calculated correctly."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

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

    def test_high_precision_calculations(self) -> None:
        """Test calculations maintain precision with high decimal places."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        kline = Kline(
            symbol="MICROTOKEN",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("0.000123456789"),
            high_price=Decimal("0.000123456890"),
            low_price=Decimal("0.000123456788"),
            close_price=Decimal("0.000123456800"),
            volume=Decimal("1000000.123456789"),
            quote_volume=Decimal("123456.789123456"),
            trades_count=1000,
        )

        # Price change should maintain precision
        expected_change = Decimal("0.000123456800") - Decimal("0.000123456789")
        assert kline.price_change == expected_change

        # Percentage calculation should be precise
        expected_percent = (expected_change / Decimal("0.000123456789")) * 100
        assert kline.price_change_percent == expected_percent

    def test_interval_alignment_validation(self) -> None:
        """Test that klines validate alignment to interval boundaries."""
        # 1-hour kline should start at the top of the hour
        aligned_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = aligned_time + timedelta(hours=1)

        # This should work - aligned to hour boundary
        valid_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=aligned_time,
            close_time=close_time,
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        assert valid_kline.duration == timedelta(hours=1)

        # Misaligned time should raise ValidationError
        misaligned_time = datetime(2023, 1, 1, 12, 30, 0, tzinfo=UTC)  # Not top of hour
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.HOUR_1,
                open_time=misaligned_time,
                close_time=misaligned_time + timedelta(hours=1),
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

    def test_ohlc_price_relationships(self) -> None:
        """Test that OHLC price relationships are enforced."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        # Valid relationships should work
        valid_kline = Kline(
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

        assert valid_kline.high_price >= valid_kline.low_price
        assert valid_kline.high_price >= valid_kline.open_price
        assert valid_kline.high_price >= valid_kline.close_price

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

    def test_sequence_continuity_validation(self) -> None:
        """Test Kline sequence continuity validation."""
        # Create continuous sequence
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        klines = []
        for i in range(3):
            open_time = base_time + timedelta(hours=i)
            close_time = open_time + timedelta(hours=1)

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
            klines.append(kline)

        # Continuous sequence should validate
        assert Kline.validate_sequence_continuity(klines) is True

        # Gap in sequence should raise ValidationError
        gap_time = base_time + timedelta(hours=5)  # Gap here
        kline_with_gap = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=gap_time,
            close_time=gap_time + timedelta(hours=1),
            open_price=Decimal("50000.0"),
            high_price=Decimal("50000.0"),
            low_price=Decimal("50000.0"),
            close_price=Decimal("50000.0"),
            volume=Decimal("10.0"),
            quote_volume=Decimal("500000.0"),
            trades_count=100,
        )

        with pytest.raises(ValueError) as exc_info:
            Kline.validate_sequence_continuity([klines[0], kline_with_gap])

        assert "Gap detected between klines" in str(exc_info.value)

    def test_to_dict_serialization(self) -> None:
        """Test Kline to_dict method for JSON serialization."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

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

    def test_optional_fields_behavior(self) -> None:
        """Test behavior of optional fields."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

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

        # Optional fields should have default values
        assert kline.exchange is None
        assert kline.taker_buy_volume is None
        assert kline.taker_buy_quote_volume is None
        assert kline.received_at is None
        assert kline.metadata == {}

    def test_kline_with_all_optional_fields(self) -> None:
        """Test kline creation with all optional fields provided."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)
        received_at = close_time + timedelta(seconds=1)
        metadata = {"source": "websocket", "version": "1.0"}

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
            exchange="binance",
            taker_buy_volume=Decimal("6.0"),
            taker_buy_quote_volume=Decimal("300000.0"),
            received_at=received_at,
            metadata=metadata,
        )

        assert kline.exchange == "binance"
        assert kline.taker_buy_volume == Decimal("6.0")
        assert kline.taker_buy_quote_volume == Decimal("300000.0")
        assert kline.received_at == received_at
        assert kline.metadata == metadata

    def test_extreme_value_handling(self) -> None:
        """Test kline handling of extreme but valid values."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

        # Test very small values
        small_kline = Kline(
            symbol="MICROTOKEN",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("0.000000000001"),  # Very small
            high_price=Decimal("0.000000000001"),
            low_price=Decimal("0.000000000001"),
            close_price=Decimal("0.000000000001"),
            volume=Decimal("0"),
            quote_volume=Decimal("0"),
            trades_count=0,
        )

        assert small_kline.price_change == Decimal("0")
        assert small_kline.price_change_percent == Decimal("0")

        # Test large values
        large_kline = Kline(
            symbol="WHALE",
            interval=KlineInterval.HOUR_1,
            open_time=open_time,
            close_time=close_time,
            open_price=Decimal("1000000000"),  # Very large
            high_price=Decimal("1000000000"),
            low_price=Decimal("1000000000"),
            close_price=Decimal("1000000000"),
            volume=Decimal("1000000"),
            quote_volume=Decimal("1000000000000000"),
            trades_count=1000000,
        )

        assert large_kline.price_change == Decimal("0")
        assert large_kline.price_change_percent == Decimal("0")

    def test_string_representation(self) -> None:
        """Test Kline string representation includes key information."""
        open_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = open_time + timedelta(hours=1)

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

        str_repr = str(kline)
        assert "BTCUSDT" in str_repr
        assert "1h" in str_repr
        assert "O:50000.0" in str_repr
        assert "H:51000.0" in str_repr
        assert "L:49000.0" in str_repr
        assert "C:50500.0" in str_repr
        assert "V:10.0" in str_repr
