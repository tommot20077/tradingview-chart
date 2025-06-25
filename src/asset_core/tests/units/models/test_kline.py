"""Unit tests for Kline model."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.models import Kline, KlineInterval


def aligned_datetime(
    year: int = 2023, month: int = 1, day: int = 1, hour: int = 12, minute: int = 0, second: int = 0
) -> datetime:
    """Create a datetime aligned to interval boundaries."""
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


@pytest.mark.unit
class TestKlineInterval:
    """Test cases for KlineInterval enum."""

    def test_kline_interval_values(self) -> None:
        """Test KlineInterval enum string values.

        Description of what the test covers:
        Verifies that KlineInterval enum has correct string values
        for all supported time intervals.

        Preconditions:
            - KlineInterval enum is properly defined

        Steps:
            - Check each KlineInterval enum member value
            - Verify string values match expected format

        Expected Result:
            - MINUTE_1 should be "1m"
            - MINUTE_5 should be "5m"
            - HOUR_1 should be "1h"
            - DAY_1 should be "1d"
            - WEEK_1 should be "1w"
            - MONTH_1 should be "1M"
        """
        assert KlineInterval.MINUTE_1 == "1m"
        assert KlineInterval.MINUTE_5 == "5m"
        assert KlineInterval.HOUR_1 == "1h"
        assert KlineInterval.DAY_1 == "1d"
        assert KlineInterval.WEEK_1 == "1w"
        assert KlineInterval.MONTH_1 == "1M"

    def test_to_seconds_conversion(self) -> None:
        """Test KlineInterval conversion to seconds.

        Description of what the test covers:
        Verifies that the to_seconds() method correctly converts
        all interval types to their equivalent seconds.

        Preconditions:
            - KlineInterval enum with to_seconds() method

        Steps:
            - Call to_seconds() for each interval type
            - Verify returned seconds match expected values

        Expected Result:
            - MINUTE_1 should be 60 seconds
            - MINUTE_5 should be 300 seconds
            - HOUR_1 should be 3600 seconds
            - DAY_1 should be 86400 seconds
            - WEEK_1 should be 604800 seconds
            - MONTH_1 should be 2592000 seconds
        """
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_1) == 60
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_5) == 300
        assert KlineInterval.to_seconds(KlineInterval.HOUR_1) == 3600
        assert KlineInterval.to_seconds(KlineInterval.DAY_1) == 86400
        assert KlineInterval.to_seconds(KlineInterval.WEEK_1) == 604800
        assert KlineInterval.to_seconds(KlineInterval.MONTH_1) == 2592000

    def test_to_timedelta_conversion(self) -> None:
        """Test KlineInterval conversion to timedelta objects.

        Description of what the test covers:
        Verifies that the to_timedelta() method correctly converts
        interval types to equivalent timedelta objects.

        Preconditions:
            - KlineInterval enum with to_timedelta() method

        Steps:
            - Call to_timedelta() for various interval types
            - Verify returned timedelta objects match expected durations

        Expected Result:
            - MINUTE_1 should be timedelta(minutes=1)
            - HOUR_1 should be timedelta(hours=1)
            - DAY_1 should be timedelta(days=1)
        """
        assert KlineInterval.to_timedelta(KlineInterval.MINUTE_1) == timedelta(minutes=1)
        assert KlineInterval.to_timedelta(KlineInterval.HOUR_1) == timedelta(hours=1)
        assert KlineInterval.to_timedelta(KlineInterval.DAY_1) == timedelta(days=1)


@pytest.mark.unit
class TestKlineConstruction:
    """Test cases for Kline model construction."""

    def test_valid_kline_creation(self, sample_kline) -> None:
        """Test valid Kline instance creation using fixture.

        Description of what the test covers:
        Verifies that a Kline instance can be created successfully
        with all required fields and validates stored values.

        Preconditions:
            - sample_kline fixture provides valid Kline instance

        Steps:
            - Use sample_kline fixture
            - Verify all field values match expected data
            - Check data types and ranges

        Expected Result:
            - Symbol should be "BTCUSDT"
            - Interval should be MINUTE_1
            - OHLC prices should be valid Decimal values
            - Volume and trade count should be positive
            - is_closed should be True
        """
        assert sample_kline.symbol == "BTCUSDT"
        assert sample_kline.interval == KlineInterval.MINUTE_1
        assert sample_kline.open_price == Decimal("50000.00")
        assert sample_kline.high_price == Decimal("50100.00")
        assert sample_kline.low_price == Decimal("49900.00")
        assert sample_kline.close_price == Decimal("50050.00")
        assert sample_kline.volume == Decimal("1.5")
        assert sample_kline.quote_volume == Decimal("75000.00")
        assert sample_kline.trades_count == 10
        assert sample_kline.is_closed is True

    def test_kline_creation_with_all_fields(self) -> None:
        """Test Kline creation with all optional fields provided.

        Description of what the test covers:
        Verifies that Kline correctly accepts and stores all
        optional fields including exchange, taker volumes, and metadata.

        Preconditions:
            - All field values including optional ones

        Steps:
            - Create Kline with all possible fields
            - Verify all provided values are stored correctly
            - Check optional fields are not overridden

        Expected Result:
            - All provided field values should be stored exactly
            - Exchange, taker volumes, received_at should be preserved
            - Metadata should match input dictionary
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=5)
        received_time = close_time + timedelta(seconds=1)

        kline = Kline(
            symbol="ETHUSDT",
            interval=KlineInterval.MINUTE_5,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("3000.00"),
            high_price=Decimal("3010.00"),
            low_price=Decimal("2995.00"),
            close_price=Decimal("3005.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("301000.00"),
            trades_count=50,
            exchange="binance",
            taker_buy_volume=Decimal("60.3"),
            taker_buy_quote_volume=Decimal("180900.00"),
            is_closed=True,
            received_at=received_time,
            metadata={"source": "websocket", "version": "v1"},
        )

        assert kline.exchange == "binance"
        assert kline.taker_buy_volume == Decimal("60.3")
        assert kline.taker_buy_quote_volume == Decimal("180900.00")
        assert kline.received_at == received_time
        assert kline.metadata == {"source": "websocket", "version": "v1"}

    def test_kline_creation_minimal_fields(self) -> None:
        """Test Kline creation with only required fields.

        Description of what the test covers:
        Verifies that Kline can be created with just the required
        fields and optional fields receive appropriate defaults.

        Preconditions:
            - Only required field values provided

        Steps:
            - Create Kline with required fields only
            - Verify required fields are set correctly
            - Verify optional fields have None or empty defaults

        Expected Result:
            - Required fields should match input values
            - Optional fields should be None or empty dict
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(hours=1)

        kline = Kline(
            symbol="ADAUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("1.25"),
            high_price=Decimal("1.30"),
            low_price=Decimal("1.20"),
            close_price=Decimal("1.28"),
            volume=Decimal("1000"),
            quote_volume=Decimal("1250"),
            trades_count=25,
        )

        assert kline.symbol == "ADAUSDT"
        assert kline.exchange is None
        assert kline.taker_buy_volume is None
        assert kline.taker_buy_quote_volume is None
        assert kline.received_at is None
        assert kline.metadata == {}


@pytest.mark.unit
class TestKlineValidation:
    """Test cases for Kline model validation."""

    def test_symbol_validation(self) -> None:
        """Test symbol field validation and uppercase normalization.

        Description of what the test covers:
        Verifies that Kline automatically normalizes symbol values
        to uppercase and trims whitespace during validation.

        Preconditions:
            - Symbol value with mixed case and whitespace
            - Valid kline data for other required fields

        Steps:
            - Create Kline with symbol="  btcusdt  "
            - Verify symbol is normalized to uppercase
            - Verify whitespace is trimmed

        Expected Result:
            - Symbol should be "BTCUSDT" (uppercase, no whitespace)
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # Valid symbol normalization
        kline = Kline(
            symbol="  btcusdt  ",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )
        assert kline.symbol == "BTCUSDT"

    def test_empty_symbol_validation(self) -> None:
        """Test validation error for empty symbol string.

        Description of what the test covers:
        Verifies that Kline raises ValidationError when symbol
        is provided as an empty string.

        Preconditions:
            - Empty string value for symbol
            - Valid values for all other required fields

        Steps:
            - Attempt to create Kline with symbol=""
            - Verify ValidationError is raised
            - Check error message mentions symbol validation

        Expected Result:
            - ValidationError should be raised
            - Error message should contain "Symbol cannot be empty"
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "Symbol cannot be empty" in str(exc_info.value)

    def test_price_positive_validation(self) -> None:
        """Test validation that all prices must be positive.

        Description of what the test covers:
        Verifies that Kline raises ValidationError when any OHLC
        price is zero or negative.

        Preconditions:
            - Valid kline data except for one zero price

        Steps:
            - Attempt to create Kline with open_price=0
            - Verify ValidationError is raised
            - Check error message mentions positive requirement

        Expected Result:
            - ValidationError should be raised for zero price
            - Error message should mention "greater than 0"
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("0"),  # Invalid
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_volume_non_negative_validation(self) -> None:
        """Test validation that volume must be non-negative.

        Description of what the test covers:
        Verifies that Kline raises ValidationError when volume
        is negative (zero is allowed).

        Preconditions:
            - Valid kline data except for negative volume

        Steps:
            - Attempt to create Kline with volume=-1.0
            - Verify ValidationError is raised
            - Check error message mentions non-negative requirement

        Expected Result:
            - ValidationError should be raised for negative volume
            - Error message should mention "greater than or equal to 0"
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("-1.0"),  # Invalid
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_trades_count_non_negative_validation(self) -> None:
        """Test trades_count must be non-negative."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=-5,  # Invalid
            )
        assert "greater than or equal to 0" in str(exc_info.value)


@pytest.mark.unit
class TestKlineOHLCValidation:
    """Test cases for OHLC price validation."""

    def test_high_price_validation(self) -> None:
        """Test high price cannot be less than other prices."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # High less than low
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("50000"),
                high_price=Decimal("49900"),  # Less than low
                low_price=Decimal("50000"),
                close_price=Decimal("50050"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "High price cannot be less than" in str(exc_info.value)

    def test_low_price_validation(self) -> None:
        """Test low price cannot be greater than other prices."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # Low greater than open
        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=close_time,
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("50050"),  # Greater than open
                close_price=Decimal("50025"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "Low price cannot be greater than open price" in str(exc_info.value)

    def test_valid_ohlc_relationships(self) -> None:
        """Test valid OHLC relationships."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # Valid: high >= all others, low <= all others
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),  # Highest
            low_price=Decimal("49900"),  # Lowest
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.high_price >= kline.open_price
        assert kline.high_price >= kline.close_price
        assert kline.high_price >= kline.low_price
        assert kline.low_price <= kline.open_price
        assert kline.low_price <= kline.close_price


@pytest.mark.unit
class TestKlineTimezoneHandling:
    """Test cases for Kline model timezone handling."""

    def test_timezone_aware_timestamps(self) -> None:
        """Test timezone-aware timestamp handling."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.open_time.tzinfo == UTC
        assert kline.close_time.tzinfo == UTC

    def test_timezone_naive_conversion(self) -> None:
        """Test timezone-naive timestamp conversion to UTC."""
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        close_time = naive_time + timedelta(minutes=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=naive_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.open_time.tzinfo == UTC
        assert kline.close_time.tzinfo == UTC


@pytest.mark.unit
class TestKlineTimeValidation:
    """Test cases for time validation."""

    def test_close_time_after_open_time(self) -> None:
        """Test close_time must be after open_time."""
        base_time = aligned_datetime()

        with pytest.raises(ValidationError) as exc_info:
            Kline(
                symbol="BTCUSDT",
                interval=KlineInterval.MINUTE_1,
                open_time=base_time,
                close_time=base_time,  # Same as open_time
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
        assert "Close time must be after open time" in str(exc_info.value)

    def test_interval_duration_validation(self) -> None:
        """Test interval duration validation."""
        # Aligned to hour boundary: 2023-01-01 12:00:00
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        # Correct duration for 1-hour interval
        close_time = base_time + timedelta(hours=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.HOUR_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.duration == timedelta(hours=1)

    def test_time_alignment_validation(self) -> None:
        """Test time alignment to interval boundaries."""
        # Aligned to minute boundary: 2023-01-01 12:05:00
        base_time = datetime(2023, 1, 1, 12, 5, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=5)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_5,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline._is_time_aligned_to_interval() is True


@pytest.mark.unit
class TestKlineCalculatedProperties:
    """Test cases for Kline model calculated properties."""

    def test_duration_calculation(self, sample_kline) -> None:
        """Test duration calculation property."""
        expected_duration = sample_kline.close_time - sample_kline.open_time
        assert sample_kline.duration == expected_duration
        assert sample_kline.duration == timedelta(minutes=1)

    def test_price_change_calculation(self) -> None:
        """Test price change calculation."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.price_change == Decimal("50.00")  # 50050 - 50000

    def test_price_change_percent_calculation(self) -> None:
        """Test price change percentage calculation."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("51000.00"),  # 2% increase
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert kline.price_change_percent == Decimal("2.00")

    def test_price_change_percent_zero_open(self) -> None:
        """Test price change percentage with zero open price."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # This should raise an error due to validation, but let's test the property logic
        # by creating a mock scenario
        kline = Kline(
            symbol="TESTUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("0.00000001"),  # Minimum allowed
            high_price=Decimal("0.00000002"),
            low_price=Decimal("0.00000001"),
            close_price=Decimal("0.00000002"),
            volume=Decimal("0"),
            quote_volume=Decimal("0"),
            trades_count=0,
        )

        # Should calculate percentage normally
        expected_percent = (Decimal("0.00000001") / Decimal("0.00000001")) * 100
        assert kline.price_change_percent == expected_percent

    def test_bullish_bearish_detection(self) -> None:
        """Test bullish and bearish detection."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        # Bullish kline (close > open)
        bullish_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),  # Higher than open
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert bullish_kline.is_bullish is True
        assert bullish_kline.is_bearish is False

        # Bearish kline (close < open)
        bearish_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("49950.00"),  # Lower than open
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert bearish_kline.is_bullish is False
        assert bearish_kline.is_bearish is True

        # Doji kline (close == open)
        doji_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50000.00"),  # Same as open
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert doji_kline.is_bullish is False
        assert doji_kline.is_bearish is False


@pytest.mark.unit
class TestKlineSerialization:
    """Test cases for Kline model serialization."""

    def test_to_dict_conversion(self, sample_kline) -> None:
        """Test to_dict method."""
        kline_dict = sample_kline.to_dict()

        assert isinstance(kline_dict, dict)
        assert kline_dict["symbol"] == "BTCUSDT"
        assert kline_dict["interval"] == "1m"
        assert kline_dict["open_price"] == "50000.00"
        assert kline_dict["high_price"] == "50100.00"
        assert kline_dict["low_price"] == "49900.00"
        assert kline_dict["close_price"] == "50050.00"
        assert kline_dict["volume"] == "1.5"
        assert kline_dict["quote_volume"] == "75000.00"
        assert kline_dict["trades_count"] == 10
        assert isinstance(kline_dict["open_time"], str)
        assert isinstance(kline_dict["close_time"], str)
        assert "price_change" in kline_dict
        assert "price_change_percent" in kline_dict

    def test_to_dict_with_optional_fields(self) -> None:
        """Test to_dict with optional fields."""
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)
        received_time = close_time + timedelta(seconds=1)

        kline = Kline(
            symbol="ETHUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("3000.00"),
            high_price=Decimal("3010.00"),
            low_price=Decimal("2995.00"),
            close_price=Decimal("3005.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("301000.00"),
            trades_count=50,
            exchange="binance",
            taker_buy_volume=Decimal("60.3"),
            taker_buy_quote_volume=Decimal("180900.00"),
            received_at=received_time,
            metadata={"test": "data"},
        )

        kline_dict = kline.to_dict()
        assert kline_dict["exchange"] == "binance"
        assert kline_dict["taker_buy_volume"] == "60.3"
        assert kline_dict["taker_buy_quote_volume"] == "180900.00"
        assert isinstance(kline_dict["received_at"], str)
        assert kline_dict["metadata"] == {"test": "data"}

    def test_model_dump_json_serializable(self, sample_kline) -> None:
        """Test model can be dumped to JSON-serializable format."""
        data = sample_kline.model_dump()

        # Should be able to convert to JSON
        import json

        json_str = json.dumps(data, default=str)
        assert isinstance(json_str, str)


@pytest.mark.unit
class TestKlineStringRepresentation:
    """Test cases for Kline model string representation."""

    def test_string_representation(self, sample_kline) -> None:
        """Test string representation."""
        str_repr = str(sample_kline)

        # Pydantic models have custom __str__ method
        assert "BTCUSDT" in str_repr
        assert "1m" in str_repr
        assert "O:50000.00" in str_repr
        assert "H:50100.00" in str_repr
        assert "L:49900.00" in str_repr
        assert "C:50050.00" in str_repr
        assert "V:1.5" in str_repr


@pytest.mark.unit
class TestKlineSequenceValidation:
    """Test cases for Kline sequence validation."""

    def test_validate_sequence_continuity_valid(self) -> None:
        """Test validation of continuous kline sequence."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        klines = []
        for i in range(3):
            open_time = base_time + timedelta(minutes=i)
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
                volume=Decimal("1.0"),
                quote_volume=Decimal("50000"),
                trades_count=10,
            )
            klines.append(kline)

        assert Kline.validate_sequence_continuity(klines) is True

    def test_validate_sequence_continuity_gap(self) -> None:
        """Test validation fails with gap in sequence."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        kline1 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=base_time + timedelta(minutes=1),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        # Gap: next kline starts 2 minutes later instead of 1
        kline2 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time + timedelta(minutes=2),
            close_time=base_time + timedelta(minutes=3),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        with pytest.raises(ValueError) as exc_info:
            Kline.validate_sequence_continuity([kline1, kline2])
        assert "Gap detected between klines" in str(exc_info.value)

    def test_validate_sequence_different_symbols(self) -> None:
        """Test validation fails with different symbols."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        kline1 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=base_time + timedelta(minutes=1),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        kline2 = Kline(
            symbol="ETHUSDT",  # Different symbol
            interval=KlineInterval.MINUTE_1,
            open_time=base_time + timedelta(minutes=1),
            close_time=base_time + timedelta(minutes=2),
            open_price=Decimal("3000"),
            high_price=Decimal("3010"),
            low_price=Decimal("2990"),
            close_price=Decimal("3005"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("3000"),
            trades_count=10,
        )

        with pytest.raises(ValueError) as exc_info:
            Kline.validate_sequence_continuity([kline1, kline2])
        assert "Klines must have the same symbol" in str(exc_info.value)

    def test_validate_sequence_single_kline(self) -> None:
        """Test validation with single kline."""
        base_time = aligned_datetime()

        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=base_time + timedelta(minutes=1),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        assert Kline.validate_sequence_continuity([kline]) is True

    def test_validate_sequence_empty_list(self) -> None:
        """Test sequence validation with empty kline list.

        Description of what the test covers:
        Verifies that Kline.validate_sequence_continuity returns True
        when called with an empty list (no klines to validate).

        Preconditions:
        - Empty list of klines

        Steps:
        - Call validate_sequence_continuity with empty list
        - Verify return value is True

        Expected Result:
        - Empty sequence should be considered valid (True)
        """
        assert Kline.validate_sequence_continuity([]) is True


@pytest.mark.unit
class TestKlineBoundaryValues:
    """Test cases for Kline model boundary values."""

    def test_minimum_valid_values(self) -> None:
        """Test kline creation with minimum valid boundary values.

        Description of what the test covers:
        Verifies that Kline accepts the minimum valid values
        for all price, volume, and count fields.

        Preconditions:
        - Aligned timestamps for 1-minute interval
        - Minimum valid price (0.00000001)
        - Zero volume and trades count

        Steps:
        - Create Kline with minimum price for all price fields
        - Set volume and quote_volume to zero
        - Set trades_count to zero
        - Verify all minimum values are correctly stored

        Expected Result:
        - All price fields should accept minimum valid price
        - Volume fields should accept zero
        - Trades count should accept zero
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        min_price = Decimal("0.00000001")

        kline = Kline(
            symbol="TESTUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=min_price,
            high_price=min_price,
            low_price=min_price,
            close_price=min_price,
            volume=Decimal("0"),
            quote_volume=Decimal("0"),
            trades_count=0,
        )

        assert kline.open_price == min_price
        assert kline.volume == Decimal("0")
        assert kline.trades_count == 0

    def test_large_values(self) -> None:
        """Test kline creation with large boundary values.

        Description of what the test covers:
        Verifies that Kline accepts large values for all
        price, volume, and count fields without limitations.

        Preconditions:
        - Aligned timestamps for 1-minute interval
        - Large price values (1,000,000)
        - Large volume and trades count

        Steps:
        - Create Kline with large price for all price fields
        - Set volume to large value
        - Calculate quote_volume as volume * price
        - Set trades_count to large value
        - Verify all large values are correctly stored

        Expected Result:
        - All price fields should accept large values
        - Volume fields should accept large values
        - Trades count should accept large values
        - No upper bound limitations imposed
        """
        base_time = aligned_datetime()
        close_time = base_time + timedelta(minutes=1)

        large_price = Decimal("1000000")
        large_volume = Decimal("1000000")

        kline = Kline(
            symbol="TESTUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=large_price,
            high_price=large_price,
            low_price=large_price,
            close_price=large_price,
            volume=large_volume,
            quote_volume=large_volume * large_price,
            trades_count=1000000,
        )

        assert kline.open_price == large_price
        assert kline.volume == large_volume
        assert kline.trades_count == 1000000


@pytest.mark.unit
class TestKlineInvalidData:
    """Test cases for Kline model with invalid data."""

    def test_missing_required_fields(self) -> None:
        """Test missing required fields."""
        required_fields = [
            "symbol",
            "interval",
            "open_time",
            "close_time",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "quote_volume",
            "trades_count",
        ]

        base_data = {
            "symbol": "BTCUSDT",
            "interval": KlineInterval.MINUTE_1,
            "open_time": datetime.now(UTC),
            "close_time": datetime.now(UTC) + timedelta(minutes=1),
            "open_price": Decimal("50000"),
            "high_price": Decimal("50100"),
            "low_price": Decimal("49900"),
            "close_price": Decimal("50050"),
            "volume": Decimal("1.0"),
            "quote_volume": Decimal("50000"),
            "trades_count": 10,
        }

        for field_to_remove in required_fields:
            data = base_data.copy()
            del data[field_to_remove]

            with pytest.raises(ValidationError):
                Kline(**data)


@pytest.mark.unit
@pytest.mark.models
class TestKlineIntegration:
    """Integration test cases for Kline model."""

    def test_kline_lifecycle(self) -> None:
        """Test complete kline lifecycle."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=5)

        # Create kline
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_5,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("45000.00"),
            high_price=Decimal("45500.00"),
            low_price=Decimal("44500.00"),
            close_price=Decimal("45250.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("4525000.00"),
            trades_count=150,
            metadata={"test": "lifecycle"},
        )

        # Verify calculated properties
        assert kline.price_change == Decimal("250.00")
        assert kline.is_bullish is True
        assert kline.duration == timedelta(minutes=5)

        # Serialize to dict
        kline_dict = kline.to_dict()
        assert kline_dict["price_change"] == "250.00"

        # Verify string representation
        str_repr = str(kline)
        assert "O:45000.00" in str_repr
        assert "H:45500.00" in str_repr
        assert "L:44500.00" in str_repr
        assert "C:45250.00" in str_repr

    def test_kline_equality_and_hashing(self) -> None:
        """Test kline equality and hashing behavior."""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=1)

        kline1 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        kline2 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        # Pydantic models are equal if all fields are equal
        assert kline1 == kline2

        # Different symbol should make them different
        kline3 = Kline(
            symbol="ETHUSDT",  # Different
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("3000"),
            high_price=Decimal("3010"),
            low_price=Decimal("2990"),
            close_price=Decimal("3005"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("3000"),
            trades_count=10,
        )

        assert kline1 != kline3
