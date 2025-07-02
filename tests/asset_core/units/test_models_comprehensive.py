"""Comprehensive tests for asset_core models with improved coverage."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

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
from asset_core.models.events import ConnectionEvent, ConnectionStatus, ErrorEvent


@pytest.mark.unit
class TestTradeModelComprehensive:
    """Comprehensive tests for Trade model.

    Description of what the class covers:
    This test suite covers various aspects of the `Trade` model,
    including valid creation, data normalization, timezone handling,
    validation for invalid inputs, and serialization to dictionary.

    Preconditions:
    - The `Trade` model is correctly defined and importable.

    Steps:
    - Test valid `Trade` object creation with all required fields.
    - Verify symbol normalization to uppercase.
    - Confirm correct handling of timezone for timestamps.
    - Test validation for invalid (non-positive) prices and quantities.
    - Verify trade volume validation against minimum thresholds.
    - Test `to_dict()` serialization for correct data representation.
    - Test creation with all optional fields.

    Expected Result:
    - `Trade` objects are created successfully with valid data.
    - Data normalization and timezone handling work as expected.
    - Invalid inputs are correctly rejected by Pydantic validation.
    - Serialization to dictionary produces accurate representations.
    """

    def test_trade_creation_valid(self) -> None:
        """Test creating a valid trade.

        Description of what the test covers.
        Verifies that a `Trade` object can be successfully instantiated
        with valid and complete data, and that its attributes are correctly set.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with all required valid parameters.
        - Assert that each attribute of the created `Trade` object matches
          the input values, including calculated `volume` and normalized `side`.

        Expected Result:
        - The `Trade` object should be created without `ValidationError`.
        - All attributes (`symbol`, `trade_id`, `price`, `quantity`, `side`,
          `timestamp`, `volume`) should hold their expected values.
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
        """Test symbol normalization.

        Description of what the test covers.
        Verifies that the `symbol` attribute of a `Trade` object is
        automatically normalized to uppercase upon instantiation.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with a lowercase `symbol`.
        - Assert that the `symbol` attribute of the created `Trade` object
          is converted to its uppercase equivalent.

        Expected Result:
        - The `symbol` attribute should be normalized to uppercase.
        """
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
        """Test timezone handling.

        Description of what the test covers.
        Verifies that naive datetime objects provided for `timestamp` are
        correctly interpreted as UTC and converted to timezone-aware datetimes.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with a naive `datetime` object for `timestamp`.
        - Assert that the `tzinfo` attribute of the `timestamp` is set to UTC.

        Expected Result:
        - The `timestamp` attribute should be a timezone-aware datetime object
          with UTC timezone information.
        """
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
        """Test validation for invalid prices.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when attempting to create a `Trade`
        object with a non-positive (`0` or negative) `price`.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `price` set to `Decimal("0")`.
        - Attempt to create a `Trade` instance with `price` set to `Decimal("-100")`.
        - Assert that `ValidationError` is raised in both cases.

        Expected Result:
        - `ValidationError` should be raised for zero or negative prices.
        """
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
        """Test validation for invalid quantities.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when attempting to create a `Trade`
        object with a non-positive (`0` or negative) `quantity`.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `quantity` set to `Decimal("0")`.
        - Assert that `ValidationError` is raised.

        Expected Result:
        - `ValidationError` should be raised for zero or negative quantities.
        """
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
        """Test trade volume validation.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when the calculated `volume`
        (price * quantity) of a `Trade` object falls below a predefined minimum.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance where `price` and `quantity`
          are very small, resulting in a `volume` below the minimum threshold.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the trade volume
          is below the minimum allowed.
        """
        # Volume too small
        with pytest.raises(ValidationError, match="Trade volume.*is below minimum"):
            Trade(
                symbol="BTCUSDT",
                trade_id="123",
                price=Decimal("0.000000000001"),  # Updated to new minimum price
                quantity=Decimal("0.000000000001"),  # Volume = 0.000000000000000000000001
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_trade_to_dict(self) -> None:
        """Test converting trade to dictionary.

        Description of what the test covers.
        Verifies that the `to_dict()` method of a `Trade` object correctly
        converts its attributes into a dictionary representation, including
        string conversion for Decimal and datetime objects.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with various attributes, including optional ones.
        - Call the `to_dict()` method on the `Trade` object.
        - Assert that the resulting dictionary contains all expected keys and
          that their values are correctly formatted (e.g., Decimals as strings).

        Expected Result:
        - The `to_dict()` method should return a dictionary with all trade details.
        - Decimal values should be represented as strings.
        - The `timestamp` should be present in the dictionary.
        """
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
        """Test trade with optional fields.

        Description of what the test covers.
        Verifies that a `Trade` object can be successfully created and its
        optional fields (`exchange`, `maker_order_id`, `taker_order_id`,
        `is_buyer_maker`, `received_at`, `metadata`) are correctly stored.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance, providing values for all optional fields.
        - Assert that each optional attribute of the created `Trade` object
          matches the input values.

        Expected Result:
        - The `Trade` object should be created without `ValidationError`.
        - All optional attributes should hold their specified values.
        """
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
    """Comprehensive tests for Kline model.

    This test suite covers various aspects of the `Kline` model,
    including valid creation, interval conversion, validation for
    prices and time alignment, price calculations, and serialization
    to dictionary.
    """

    def test_kline_creation_valid(self) -> None:
        """Test creating a valid kline.

        Description of what the test covers.
        Verifies that a `Kline` object can be successfully instantiated
        with valid and complete data, and that its attributes are correctly set,
        including derived properties like `price_change` and `is_bullish`.

        Preconditions:
        - None.

        Steps:
        - Create a `Kline` instance with all required valid parameters,
          ensuring time alignment for the specified interval.
        - Assert that each attribute of the created `Kline` object matches
          the input values, and that derived properties are calculated correctly.

        Expected Result:
        - The `Kline` object should be created without `ValidationError`.
        - All attributes (`symbol`, `interval`, `open_time`, `close_time`,
          `open_price`, `high_price`, `low_price`, `close_price`, `volume`,
          `quote_volume`, `trades_count`) should hold their expected values.
        - `price_change` should be `close_price - open_price`.
        - `is_bullish` should be True if `close_price > open_price`.
        - `is_bearish` should be False if `close_price > open_price`.
        """
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
        """Test interval conversion methods.

        Description of what the test covers.
        Verifies that `KlineInterval.to_seconds()` and `KlineInterval.to_timedelta()`
        methods correctly convert `KlineInterval` enum members to their
        corresponding duration in seconds and `timedelta` objects, respectively.

        Preconditions:
        - None.

        Steps:
        - Call `KlineInterval.to_seconds()` with various `KlineInterval` values.
        - Assert that the returned integer matches the expected number of seconds.
        - Call `KlineInterval.to_timedelta()` with various `KlineInterval` values.
        - Assert that the returned `timedelta` object matches the expected duration.

        Expected Result:
        - `to_seconds()` should return the correct number of seconds for each interval.
        - `to_timedelta()` should return the correct `timedelta` object for each interval.
        """
        assert KlineInterval.to_seconds(KlineInterval.MINUTE_1) == 60
        assert KlineInterval.to_seconds(KlineInterval.HOUR_1) == 3600
        assert KlineInterval.to_seconds(KlineInterval.DAY_1) == 86400

        assert KlineInterval.to_timedelta(KlineInterval.MINUTE_5) == timedelta(minutes=5)
        assert KlineInterval.to_timedelta(KlineInterval.HOUR_4) == timedelta(hours=4)

    def test_kline_price_validation(self) -> None:
        """Test kline price validation.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when attempting to create a `Kline`
        object with invalid price relationships (e.g., `high_price` less than `open_price`).

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Kline` instance where `high_price` is less than `open_price`.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised for invalid price relationships.
        """
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
        """Test kline time validation.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when attempting to create a `Kline`
        object with an invalid time relationship (e.g., `close_time` before `open_time`).

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Kline` instance where `close_time` is before `open_time`.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised if `close_time` is not after `open_time`.
        """
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
        """Test kline time alignment validation.

        Description of what the test covers.
        Verifies that `ValidationError` is raised when attempting to create a `Kline`
        object whose `open_time` is not aligned to the specified `interval` boundaries.

        Preconditions:
        - None.

        Steps:
        - Create a `Kline` instance with an `open_time` that is not aligned
          to its `interval` (e.g., 30 seconds offset for a 1-minute interval).
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised if `open_time` is not aligned to
          the `KlineInterval` boundaries.
        """
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
        """Test price change calculations.

        Description of what the test covers.
        Verifies that `price_change` and `price_change_percent` properties
        of a `Kline` object are correctly calculated for both bullish and
        bearish scenarios.

        Preconditions:
        - None.

        Steps:
        - Create a bullish `Kline` instance.
        - Assert that `price_change` and `price_change_percent` are positive
          and correctly calculated.
        - Assert that `is_bullish` is True and `is_bearish` is False.
        - Create a bearish `Kline` instance.
        - Assert that `price_change` and `price_change_percent` are negative
          and correctly calculated.
        - Assert that `is_bearish` is True and `is_bullish` is False.

        Expected Result:
        - `price_change` should be `close_price - open_price`.
        - `price_change_percent` should be `(price_change / open_price) * 100`.
        - `is_bullish` and `is_bearish` flags should reflect the price movement correctly.
        """
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
        """Test converting kline to dictionary.

        Description of what the test covers.
        Verifies that the `to_dict()` method of a `Kline` object correctly
        converts its attributes into a dictionary representation, including
        string conversion for Decimal and calculated properties.

        Preconditions:
        - None.

        Steps:
        - Create a `Kline` instance with various attributes.
        - Call the `to_dict()` method on the `Kline` object.
        - Assert that the resulting dictionary contains all expected keys and
          that their values are correctly formatted (e.g., Decimals as strings).

        Expected Result:
        - The `to_dict()` method should return a dictionary with all kline details.
        - Decimal values should be represented as strings.
        - Calculated properties like `price_change` and `price_change_percent`
          should be included and correctly formatted.
        """
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
    """Comprehensive tests for event models.

    This test suite covers various aspects of the event models,
    including base event creation, specific event types (TradeEvent,
    KlineEvent, ConnectionEvent, ErrorEvent), priority handling,
    symbol validation, correlation ID functionality, and serialization
    to dictionary.
    """

    def test_base_event_creation(self) -> None:
        """Test creating a base event.

        Description of what the test covers.
        Verifies that a `BaseEvent` object can be successfully instantiated
        with valid data, and that its attributes are correctly set,
        including default values for `priority` and auto-generated `event_id`
        and `timestamp`.

        Preconditions:
        - None.

        Steps:
        - Create a `BaseEvent` instance with required parameters.
        - Assert that each attribute of the created `BaseEvent` object matches
          the input values or expected default/generated values.

        Expected Result:
        - The `BaseEvent` object should be created without `ValidationError`.
        - `event_type`, `source`, `data` should match input.
        - `priority` should default to `EventPriority.NORMAL`.
        - `event_id` should be a non-None UUID string.
        - `timestamp` should be a timezone-aware datetime in UTC.
        """
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
        """Test trade event.

        Description of what the test covers.
        Verifies that a `TradeEvent` object can be successfully instantiated
        and correctly encapsulates a `Trade` object, with its `event_type`
        and `symbol` attributes set appropriately.

        Preconditions:
        - A valid `Trade` object is available.

        Steps:
        - Create a `Trade` object.
        - Create a `TradeEvent` instance, passing the `Trade` object as data.
        - Assert that `event_type` is "trade".
        - Assert that `symbol` matches the trade's symbol.
        - Assert that `data` is an instance of `Trade`.

        Expected Result:
        - The `TradeEvent` object should be created without `ValidationError`.
        - Its attributes should correctly reflect the encapsulated trade information.
        """
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
        """Test kline event.

        Description of what the test covers.
        Verifies that a `KlineEvent` object can be successfully instantiated
        and correctly encapsulates a `Kline` object, with its `event_type`
        and `symbol` attributes set appropriately.

        Preconditions:
        - A valid `Kline` object is available.

        Steps:
        - Create a `Kline` object.
        - Create a `KlineEvent` instance, passing the `Kline` object as data.
        - Assert that `event_type` is "kline".
        - Assert that `symbol` matches the kline's symbol.
        - Assert that `data` is an instance of `Kline`.

        Expected Result:
        - The `KlineEvent` object should be created without `ValidationError`.
        - Its attributes should correctly reflect the encapsulated kline information.
        """
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
        """Test connection event.

        Description of what the test covers.
        Verifies that a `ConnectionEvent` object can be successfully instantiated
        and correctly reflects the connection status and source.

        Preconditions:
        - None.

        Steps:
        - Create a `ConnectionEvent` instance with a `ConnectionStatus` and source.
        - Assert that `event_type` is "connection".
        - Assert that `data["status"]` matches the provided status.
        - Assert that `source` matches the provided source.

        Expected Result:
        - The `ConnectionEvent` object should be created without `ValidationError`.
        - Its attributes should correctly reflect the connection information.
        """
        event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED,
            source="binance",
        )

        assert event.event_type == "connection"
        assert event.data["status"] == "connected"
        assert event.source == "binance"

    def test_error_event(self) -> None:
        """Test error event.

        Description of what the test covers.
        Verifies that an `ErrorEvent` object can be successfully instantiated
        and correctly reflects the error details, error code, and source,
        and that its priority is set to HIGH by default.

        Preconditions:
        - None.

        Steps:
        - Create an `ErrorEvent` instance with error message, error code, and source.
        - Assert that `event_type` is "error".
        - Assert that `priority` is `EventPriority.HIGH`.
        - Assert that `data["error"]` and `data["error_code"]` match the provided values.
        - Assert that `source` matches the provided source.

        Expected Result:
        - The `ErrorEvent` object should be created without `ValidationError`.
        - Its attributes should correctly reflect the error information.
        """
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
        """Test event priority levels.

        Description of what the test covers.
        Verifies that `BaseEvent` objects correctly assign and reflect
        event priority, including the default `NORMAL` priority and
        explicitly set `HIGH` priority.

        Preconditions:
        - None.

        Steps:
        - Create a `BaseEvent` instance without specifying priority.
        - Assert that its `priority` is `EventPriority.NORMAL`.
        - Create another `BaseEvent` instance, explicitly setting `priority` to `EventPriority.HIGH`.
        - Assert that its `priority` is `EventPriority.HIGH`.

        Expected Result:
        - Events should correctly reflect their assigned or default priority levels.
        """
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

    def test_event_symbol_validation(self) -> None:
        """Test event symbol validation.

        Description of what the test covers.
        Verifies that the `symbol` attribute of an event is normalized to
        uppercase and that an empty symbol raises a `ValidationError`.

        Preconditions:
        - None.

        Steps:
        - Create a `BaseEvent` instance with a lowercase `symbol`.
        - Assert that the `symbol` attribute is normalized to uppercase.
        - Attempt to create a `BaseEvent` instance with an empty `symbol`.
        - Assert that `ValidationError` is raised.

        Expected Result:
        - `symbol` should be normalized to uppercase.
        - `ValidationError` should be raised for an empty `symbol`.
        """
        # Symbol should be normalized to uppercase
        event: BaseEvent = BaseEvent(
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
        """Test event correlation ID functionality.

        Description of what the test covers.
        Verifies that `correlation_id` can be assigned to events and that
        events sharing the same `correlation_id` are correctly identified.

        Preconditions:
        - None.

        Steps:
        - Define a `correlation_id` string.
        - Create two `BaseEvent` instances, assigning the same `correlation_id` to both.
        - Assert that the `correlation_id` attribute of both events matches the assigned ID.
        - Assert that the `correlation_id` of the two events are equal.

        Expected Result:
        - Events should correctly store and expose their `correlation_id`.
        - Events with the same `correlation_id` should be comparable based on it.
        """
        correlation_id = "test-correlation-123"

        event1: BaseEvent = BaseEvent(
            event_type=EventType.SYSTEM,
            source="test",
            data={},
            correlation_id=correlation_id,
        )

        event2: BaseEvent = BaseEvent(
            event_type=EventType.TRADE,
            source="test",
            data={},
            correlation_id=correlation_id,
        )

        assert event1.correlation_id == correlation_id
        assert event2.correlation_id == correlation_id
        assert event1.correlation_id == event2.correlation_id

    def test_event_to_dict(self) -> None:
        """Test converting event to dictionary.

        Description of what the test covers.
        Verifies that the `to_dict()` method of a `BaseEvent` object correctly
        converts its attributes into a dictionary representation, including
        `event_type`, `source`, `data`, `metadata`, `timestamp`, and `event_id`.

        Preconditions:
        - None.

        Steps:
        - Create a `BaseEvent` instance with `data` and `metadata`.
        - Call the `to_dict()` method on the `BaseEvent` object.
        - Assert that the resulting dictionary contains all expected keys and
          that their values are correctly represented.

        Expected Result:
        - The `to_dict()` method should return a dictionary with all event details.
        - `timestamp` and `event_id` should be present in the dictionary.
        """
        event: BaseEvent = BaseEvent(
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
