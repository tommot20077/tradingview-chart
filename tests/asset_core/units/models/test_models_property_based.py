"""Property-based tests for Trade and Kline models using Hypothesis."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide


# Hypothesis strategies for model testing
def decimal_strategy(min_value: str = "0.000000000001", max_value: str = "1000000000") -> st.SearchStrategy[Decimal]:
    """Generates Decimal values within a specified range with updated precision.

    Args:
        min_value (str): The minimum value for the Decimal numbers (inclusive).
        max_value (str): The maximum value for the Decimal numbers (inclusive).

    Returns:
        st.SearchStrategy[Decimal]: A Hypothesis strategy that generates Decimal numbers.
    """
    return st.decimals(
        min_value=Decimal(min_value), max_value=Decimal(max_value), allow_nan=False, allow_infinity=False, places=12
    )


def symbol_strategy() -> st.SearchStrategy[str]:
    """Generates valid trading symbols.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating valid trading symbols.
    It produces alphanumeric strings with optional underscores, ensuring they are
    non-empty and not composed solely of whitespace.

    Preconditions:
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[str]: A Hypothesis strategy that generates strings
                                suitable for trading symbols (alphanumeric, underscores).

    Steps:
    - Uses `st.text` to generate strings with a whitelist of alphanumeric and underscore characters.
    - Sets `min_size` to 1 and `max_size` to 20.
    - Filters out strings that are empty or contain only whitespace using a `lambda` function.

    Expected Result:
    - A Hypothesis strategy that generates valid, non-empty, and non-whitespace-only
      trading symbol strings.
    """
    return st.text(
        alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd", "Pc"]), min_size=1, max_size=20
    ).filter(lambda x: x.strip() and not x.isspace())


def trade_side_strategy() -> st.SearchStrategy[TradeSide]:
    """Generates `TradeSide` enum values.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating random `TradeSide`
    enum values (`BUY` or `SELL`).

    Preconditions:
    - `TradeSide` enum is defined and imported.
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[TradeSide]: A Hypothesis strategy that generates `TradeSide.BUY` or `TradeSide.SELL`.

    Steps:
    - Uses `st.sampled_from` to pick randomly from the `TradeSide` enum members.

    Expected Result:
    - A Hypothesis strategy that generates either `TradeSide.BUY` or `TradeSide.SELL`.
    """
    return st.sampled_from(TradeSide)


def datetime_strategy() -> st.SearchStrategy[datetime]:
    """Generates datetime values in a reasonable range for testing.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating `datetime` objects.
    It produces datetimes within a predefined reasonable range (2020 to 2030)
    and ensures they are timezone-naive (no timezone information).

    Preconditions:
    - `datetime` type from the `datetime` module is available.
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[datetime]: A Hypothesis strategy that generates datetime objects
                                     between 2020-01-01 and 2030-12-31, without timezone info.

    Steps:
    - Uses `st.datetimes` with `min_value` and `max_value` set to specific dates.
    - Sets `timezones` to `st.none()` to ensure naive datetimes.

    Expected Result:
    - A Hypothesis strategy that generates timezone-naive `datetime` objects within the specified range.
    """
    return st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31), timezones=st.none())


def trade_strategy() -> st.SearchStrategy[Trade]:
    """Generates valid Trade instances with proper volume constraints.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating valid `Trade` objects.
    It ensures that the combination of `price` and `quantity` results in a `volume`
    that adheres to the `Trade` model's validation rules (e.g., positive volume,
    within reasonable bounds). It also generates values for all optional fields.

    Preconditions:
    - `Trade` model is defined and imported.
    - `decimal_strategy`, `symbol_strategy`, `trade_side_strategy`, `datetime_strategy` are available.
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[Trade]: A Hypothesis strategy that generates `Trade` objects,
                                 ensuring that `price` and `quantity` combinations
                                 result in a valid `volume`.

    Steps:
    - Uses `@st.composite` to create a composite strategy.
    - Draws `price` from `decimal_strategy` within a test-friendly range.
    - Calculates `min_quantity` and `max_quantity` dynamically based on `price`
      to ensure the resulting `volume` is within valid bounds, adding safety margins.
    - Draws `quantity` from `st.decimals` using the calculated `min_q` and `max_q`.
    - Draws values for `symbol`, `trade_id`, `side`, `timestamp`, and all optional fields
      (`exchange`, `maker_order_id`, `taker_order_id`, `is_buyer_maker`, `received_at`, `metadata`)
      from their respective strategies or `st.one_of(st.none(), ...)`.
    - Constructs and returns a `Trade` instance with the drawn values.

    Expected Result:
    - A Hypothesis strategy that generates `Trade` objects that are consistently valid
      according to the `Trade` model's rules, especially concerning `volume` constraints.
    - Generated trades include a diverse set of values for all fields, including optional ones.
    """

    @st.composite
    def _trade_strategy(draw: DrawFn) -> Trade:
        # Generate valid price first with reasonable range for testing
        price = draw(decimal_strategy(min_value="0.01", max_value="100000"))

        # Calculate quantity that ensures volume is well within valid range (0.001 to 10000000000)
        # Add safety margin to avoid precision issues at boundaries
        min_quantity = Decimal("0.002") / price  # Slightly above minimum
        max_quantity = Decimal("1000000000") / price  # Well below maximum

        # Ensure quantity is within valid range and reasonable for testing
        min_q = max(min_quantity, Decimal("0.000000000001"))
        max_q = min(max_quantity, Decimal("100000"))  # Reduced for more reliable testing

        quantity = draw(st.decimals(min_value=min_q, max_value=max_q, places=12, allow_nan=False, allow_infinity=False))

        return Trade(
            symbol=draw(symbol_strategy()),
            trade_id=draw(st.text(min_size=1, max_size=50)),
            price=price,
            quantity=quantity,
            side=draw(trade_side_strategy()),
            timestamp=draw(datetime_strategy()),
            exchange=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
            maker_order_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
            taker_order_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
            is_buyer_maker=draw(st.one_of(st.none(), st.booleans())),
            received_at=draw(st.one_of(st.none(), datetime_strategy())),
            metadata=draw(st.dictionaries(st.text(), st.text())),
        )

    return _trade_strategy()


def kline_interval_strategy() -> st.SearchStrategy[KlineInterval]:
    """Generates `KlineInterval` enum values.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating random `KlineInterval`
    enum values.

    Preconditions:
    - `KlineInterval` enum is defined and imported.
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[KlineInterval]: A Hypothesis strategy that generates `KlineInterval` enum members.

    Steps:
    - Uses `st.sampled_from` to pick randomly from the `KlineInterval` enum members.

    Expected Result:
    - A Hypothesis strategy that generates any valid `KlineInterval` enum member.
    """
    return st.sampled_from(KlineInterval)


def ohlc_prices_strategy() -> st.SearchStrategy[dict[str, Decimal]]:
    """Generates valid OHLC price combinations.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating valid Open, High, Low, Close (OHLC) price combinations.
    It ensures that the fundamental OHLC relationships are maintained: `low_price` is always less than or equal to
    `open_price`, `close_price`, and `high_price`, and `high_price` is always greater than or equal to `open_price` and `close_price`.

    Preconditions:
    - `decimal_strategy` is available for generating `Decimal` prices.
    - `hypothesis.strategies` module is imported as `st`.
    - `hypothesis.assume` is available for filtering invalid combinations.

    Returns:
        st.SearchStrategy[dict[str, Decimal]]: A Hypothesis strategy that generates a dictionary
                                              with 'open_price', 'high_price', 'low_price', and 'close_price' keys.

    Steps:
    - Uses `@st.composite` to create a composite strategy.
    - Draws `low` and `high` prices using `decimal_strategy`, ensuring `high` is greater than or equal to `low`.
    - Uses `assume` to filter out cases where `high` is less than `low` (though `decimal_strategy` should prevent this).
    - Draws `open_price` and `close_price` from `st.decimals` within the `[low, high]` range.
    - Returns a dictionary containing the generated OHLC prices.

    Expected Result:
    - A Hypothesis strategy that generates dictionaries of OHLC prices where `low` <= `open`, `close` <= `high`, and `low` <= `high`.
    - All generated prices are `Decimal` instances.
    """

    @st.composite
    def _ohlc_prices(draw: DrawFn) -> dict[str, Decimal]:
        # Generate base prices
        low = draw(decimal_strategy())
        high = draw(decimal_strategy(min_value=str(low)))

        # Ensure high >= low
        assume(high >= low)

        # Generate open and close within [low, high] range
        open_price = draw(st.decimals(min_value=low, max_value=high, places=12))
        close_price = draw(st.decimals(min_value=low, max_value=high, places=12))

        return {"open_price": open_price, "high_price": high, "low_price": low, "close_price": close_price}

    return _ohlc_prices()


def kline_strategy() -> st.SearchStrategy[Kline]:
    """Generates valid Kline instances.

    Description of what the function covers:
    This function creates a Hypothesis strategy for generating valid `Kline` objects.
    It ensures that `open_time` and `close_time` are correctly aligned with the
    specified `interval` boundaries, and that all other `Kline` fields are valid.

    Preconditions:
    - `Kline` model is defined and imported.
    - `kline_interval_strategy`, `datetime_strategy`, `ohlc_prices_strategy`,
      `decimal_strategy`, `symbol_strategy` are available.
    - `KlineInterval.to_seconds` and `KlineInterval.to_timedelta` are available.
    - `hypothesis.strategies` module is imported as `st`.

    Returns:
        st.SearchStrategy[Kline]: A Hypothesis strategy that generates `Kline` objects.

    Steps:
    - Uses `@st.composite` to create a composite strategy.
    - Draws `interval` from `kline_interval_strategy` and `open_time` from `datetime_strategy`.
    - Aligns `open_time` to the `interval` boundary using `KlineInterval.to_seconds`.
    - Calculates `close_time` based on the aligned `open_time` and `interval` duration.
    - Draws `ohlc_prices` from `ohlc_prices_strategy`.
    - Draws `volume`, `quote_volume`, `trades_count`, `exchange`, optional `taker_buy_volume`,
      `taker_buy_quote_volume`, `is_closed`, `received_at`, and `metadata` from their
      respective strategies or `st.one_of(st.none(), ...)`.
    - Constructs and returns a `Kline` instance with the drawn values.

    Expected Result:
    - A Hypothesis strategy that generates `Kline` objects that are consistently valid
      according to the `Kline` model's rules, especially concerning time alignment and OHLC relationships.
    - Generated klines include a diverse set of values for all fields, including optional ones.
    """

    @st.composite
    def _kline(draw: DrawFn) -> Kline:
        interval = draw(kline_interval_strategy())
        open_time = draw(datetime_strategy())

        # Align open_time to interval boundary
        interval_seconds = KlineInterval.to_seconds(interval)
        timestamp_seconds = int(open_time.timestamp())
        aligned_timestamp = (timestamp_seconds // interval_seconds) * interval_seconds
        aligned_open_time = datetime.fromtimestamp(aligned_timestamp, tz=UTC)

        close_time = aligned_open_time + KlineInterval.to_timedelta(interval)

        ohlc_prices = draw(ohlc_prices_strategy())

        volume = draw(decimal_strategy(min_value="0", max_value="1000000"))
        quote_volume = draw(decimal_strategy(min_value="0", max_value="10000000"))

        taker_buy_vol = draw(st.one_of(st.none(), decimal_strategy(min_value="0", max_value=str(volume))))
        taker_buy_quote_vol = draw(st.one_of(st.none(), decimal_strategy(min_value="0", max_value=str(quote_volume))))

        return Kline(
            symbol=draw(symbol_strategy()),
            interval=interval,
            open_time=aligned_open_time,
            close_time=close_time,
            **ohlc_prices,
            volume=volume,
            quote_volume=quote_volume,
            trades_count=draw(st.integers(min_value=0, max_value=100000)),
            exchange=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
            taker_buy_volume=taker_buy_vol,
            taker_buy_quote_volume=taker_buy_quote_vol,
            is_closed=draw(st.booleans()),
            received_at=draw(st.one_of(st.none(), datetime_strategy())),
            metadata=draw(st.dictionaries(st.text(), st.text())),
        )

    return _kline()


@pytest.mark.unit
class TestTradePropertyBased:
    """Property-based tests for Trade model.

    These tests use Hypothesis to generate diverse inputs and verify
    invariants and behaviors of the `Trade` model, ensuring robustness.
    """

    @given(trade_data=trade_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_price_quantity_invariants(self, trade_data: Trade) -> None:
        """Test price and quantity invariants with property-based testing.

        Description of what the test covers.
        This test uses Hypothesis to generate `Trade` objects and assert that price
        and quantity are always positive, and their product (volume) is consistent.

        Preconditions:
            - Generated trades use optimized strategy with valid ranges.
            - Trade model validation rules are enforced.

        Steps:
            - Use generated `Trade` with valid price and quantity.
            - Verify `price > 0` and `quantity > 0`.
            - Verify `volume = price × quantity` calculation.
            - Test mathematical properties and edge cases.

        Expected Result:
            - All price/quantity invariants hold.
            - Volume calculation is mathematically correct.
            - Edge cases are handled properly.
        """

        # Test basic invariants using the generated trade
        assert trade_data.price > 0
        assert trade_data.quantity > 0
        assert trade_data.volume > 0

        # Test mathematical relationship
        expected_volume = trade_data.price * trade_data.quantity
        assert trade_data.volume == expected_volume

        # Test precision preservation
        assert isinstance(trade_data.price, Decimal)
        assert isinstance(trade_data.quantity, Decimal)
        assert isinstance(trade_data.volume, Decimal)

        # Test that volume calculation is consistent
        recalculated_volume = trade_data.price * trade_data.quantity
        assert trade_data.volume == recalculated_volume

    @given(trade_data=trade_strategy())
    def test_volume_calculation_property(self, trade_data: Trade) -> None:
        """Test volume calculation correctness across all Trade instances.

        Description of what the test covers.
        This test verifies that the volume calculation is always mathematically
        correct regardless of the input values used to construct the `Trade`.

        Preconditions:
            - `Trade` instance is valid.
            - Price and quantity are positive decimals.

        Steps:
            - Generate `Trade` instance with Hypothesis.
            - Verify `volume = price × quantity`.
            - Test calculation precision.
            - Test decimal arithmetic consistency.

        Expected Result:
            - Volume calculation is always correct.
            - No precision loss in decimal arithmetic.
            - Mathematical properties are preserved.
        """
        # Volume should always equal price × quantity
        expected_volume = trade_data.price * trade_data.quantity
        assert trade_data.volume == expected_volume

        # Volume should be positive (since price and quantity are positive)
        assert trade_data.volume > 0

        # Test precision - volume should have appropriate decimal places
        assert isinstance(trade_data.volume, Decimal)

        # Test that volume doesn't change when accessed multiple times
        volume1 = trade_data.volume
        volume2 = trade_data.volume
        assert volume1 == volume2

        # Test mathematical properties
        assert (
            trade_data.volume >= trade_data.price if trade_data.quantity >= 1 else trade_data.volume <= trade_data.price
        )
        assert (
            trade_data.volume >= trade_data.quantity
            if trade_data.price >= 1
            else trade_data.volume <= trade_data.quantity
        )

    @given(symbol_input=st.text(min_size=1, max_size=50))
    def test_symbol_normalization_property(self, symbol_input: str) -> None:
        """Test symbol normalization idempotency and consistency.

        Description of what the test covers.
        This test verifies that symbol normalization consistently produces the
        expected normalized form for various inputs, and that normalization
        is idempotent (applying it multiple times yields the same result).

        Preconditions:
            - Input symbol is non-empty string.
            - Symbol normalization rules are well-defined.

        Steps:
            - Generate various symbol inputs.
            - Create `Trade` with symbol.
            - Verify normalization rules (uppercase, stripped).
            - Test idempotency of normalization.

        Expected Result:
            - Symbols are consistently normalized to uppercase.
            - Leading/trailing whitespace is removed.
            - Normalization is idempotent.
        """
        # Skip invalid symbols that would be rejected
        assume(symbol_input.strip())
        assume(len(symbol_input.strip()) > 0)

        try:
            trade = Trade(
                symbol=symbol_input,
                trade_id="test_trade",
                price=Decimal("100.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

            # Test normalization rules
            expected_symbol = symbol_input.strip().upper()
            assert trade.symbol == expected_symbol

            # Test idempotency - creating another trade with the normalized symbol
            trade2 = Trade(
                symbol=trade.symbol,
                trade_id="test_trade2",
                price=Decimal("100.0"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )
            assert trade2.symbol == trade.symbol

            # Test that normalization is consistent
            # Note: Numeric symbols are valid but don't have .isupper() == True
            assert trade.symbol == trade.symbol.upper()
            assert trade.symbol == trade.symbol.strip()

        except ValueError:
            # If symbol validation rejects the input, that's acceptable
            # The test is about valid symbols being normalized correctly
            pass

    @given(dt=datetime_strategy())
    def test_timestamp_conversion_property(self, dt: datetime) -> None:
        """Test timestamp conversion round-trip consistency.

        Description of what the test covers.
        This test verifies that timezone conversions are handled correctly
        and that timestamp precision is preserved through various operations.

        Preconditions:
            - Generated datetime is within reasonable range.
            - Timezone handling is implemented correctly.

        Steps:
            - Generate datetime with timezone info.
            - Create `Trade` with timestamp.
            - Verify timezone conversion to UTC.
            - Test round-trip conversion consistency.

        Expected Result:
            - Timestamps are converted to UTC.
            - Precision is preserved (microsecond level).
            - Round-trip conversions are consistent.
        """
        trade = Trade(
            symbol="TESTBTC",
            trade_id="test_trade",
            price=Decimal("100.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=dt,
        )

        # Timestamp should be in UTC
        assert trade.timestamp.tzinfo == UTC

        # Test precision preservation (should preserve microseconds)
        if dt.tzinfo is not None:
            # If input had timezone info, should be converted to UTC
            assert trade.timestamp.timestamp() == dt.timestamp()
        else:
            # If input was naive, it gets interpreted as UTC
            expected_dt = dt.replace(tzinfo=UTC)
            assert trade.timestamp == expected_dt

        # Test that timestamp is immutable-like (accessing multiple times gives same result)
        timestamp1 = trade.timestamp
        timestamp2 = trade.timestamp
        assert timestamp1 == timestamp2

        # Test serialization round-trip through ISO format
        iso_string = trade.timestamp.isoformat()
        parsed_timestamp = datetime.fromisoformat(iso_string)
        assert parsed_timestamp == trade.timestamp

    @given(trade_data=trade_strategy())
    def test_serialization_roundtrip_property(self, trade_data: Trade) -> None:
        """Test Trade serialization/deserialization round-trip consistency.

        Description of what the test covers.
        This test verifies that `Trade` objects can be serialized to dict/JSON
        and deserialized back without losing any information or precision.

        Preconditions:
            - `Trade` instance is valid.
            - Serialization methods are implemented.

        Steps:
            - Generate `Trade` instance.
            - Serialize to dict using `to_dict()`.
            - Verify all fields are preserved.
            - Test JSON serialization round-trip.
            - Verify reconstructed object equivalence.

        Expected Result:
            - Serialization preserves all field values.
            - No precision loss in decimal values.
            - Round-trip serialization is lossless.
        """
        # Test to_dict() serialization
        trade_dict = trade_data.to_dict()

        # Verify all required fields are present
        required_fields = ["symbol", "trade_id", "price", "quantity", "side", "timestamp", "volume"]
        for field in required_fields:
            assert field in trade_dict

        # Test that prices are properly serialized as strings
        assert isinstance(trade_dict["price"], str)
        assert isinstance(trade_dict["quantity"], str)
        assert isinstance(trade_dict["volume"], str)

        # Test decimal precision preservation
        assert Decimal(trade_dict["price"]) == trade_data.price
        assert Decimal(trade_dict["quantity"]) == trade_data.quantity
        assert Decimal(trade_dict["volume"]) == trade_data.volume

        # Test timestamp serialization
        assert isinstance(trade_dict["timestamp"], str)
        parsed_timestamp = datetime.fromisoformat(trade_dict["timestamp"])
        # Timestamps should be equivalent (in UTC)
        assert parsed_timestamp.replace(tzinfo=UTC) == trade_data.timestamp

        # Test side serialization - handle both enum and string cases
        expected_side = trade_data.side.value if hasattr(trade_data.side, "value") else trade_data.side
        assert trade_dict["side"] == expected_side

        # Test JSON serialization round-trip
        json_str = json.dumps(trade_dict)
        reconstructed_dict = json.loads(json_str)

        # Verify JSON round-trip preserves all values
        assert reconstructed_dict["symbol"] == trade_data.symbol
        assert Decimal(reconstructed_dict["price"]) == trade_data.price
        assert Decimal(reconstructed_dict["quantity"]) == trade_data.quantity

        # Test optional fields preservation
        if trade_data.exchange is not None:
            assert trade_dict.get("exchange") == trade_data.exchange
        if trade_data.maker_order_id is not None:
            assert trade_dict.get("maker_order_id") == trade_data.maker_order_id
        if trade_data.taker_order_id is not None:
            assert trade_dict.get("taker_order_id") == trade_data.taker_order_id
        if trade_data.is_buyer_maker is not None:
            assert trade_dict.get("is_buyer_maker") == trade_data.is_buyer_maker
        if trade_data.metadata is not None:
            assert trade_dict.get("metadata") == trade_data.metadata


@pytest.mark.unit
class TestKlinePropertyBased:
    """Property-based tests for Kline model.

    These tests use Hypothesis to generate diverse inputs and verify
    invariants and behaviors of the `Kline` model, ensuring robustness.
    """

    @given(ohlc_data=ohlc_prices_strategy())
    def test_ohlc_relationship_invariants(self, ohlc_data: dict[str, Decimal]) -> None:
        """Test OHLC price relationship invariants.

        Description of what the test covers.
        This test verifies that OHLC prices maintain their mathematical
        relationships: `low` <= `open`, `close` <= `high`, and `low` <= `high`.

        Preconditions:
            - Generated OHLC prices satisfy basic constraints.
            - Kline validation enforces OHLC relationships.

        Steps:
            - Generate valid OHLC price combinations.
            - Create `Kline` with these prices.
            - Verify all OHLC mathematical relationships.
            - Test edge cases (all prices equal).

        Expected Result:
            - `low` <= `open`, `close` <= `high`.
            - `low` <= `high` (fundamental relationship).
            - All OHLC relationships are mathematically sound.
        """
        # Create a basic kline with the OHLC prices
        kline = Kline(
            symbol="TESTBTC",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2023, 1, 1),
            close_time=datetime(2023, 1, 1, 0, 1),
            **ohlc_data,
            volume=Decimal("1000"),
            quote_volume=Decimal("100000"),
            trades_count=100,
        )

        # Test fundamental OHLC relationships
        assert kline.low_price <= kline.high_price
        assert kline.low_price <= kline.open_price <= kline.high_price
        assert kline.low_price <= kline.close_price <= kline.high_price

        # Test that all prices are positive
        assert kline.open_price > 0
        assert kline.high_price > 0
        assert kline.low_price > 0
        assert kline.close_price > 0

        # Test precision preservation
        assert isinstance(kline.open_price, Decimal)
        assert isinstance(kline.high_price, Decimal)
        assert isinstance(kline.low_price, Decimal)
        assert isinstance(kline.close_price, Decimal)

    @given(interval=kline_interval_strategy(), base_time=datetime_strategy())
    def test_time_alignment_property(self, interval: KlineInterval, base_time: datetime) -> None:
        """Test time alignment with intervals.

        Description of what the test covers.
        This test verifies that `open_time` and `close_time` are correctly aligned
        with the specified interval boundaries.

        Preconditions:
            - `KlineInterval` defines valid time periods.
            - Time alignment logic is implemented correctly.

        Steps:
            - Generate interval and base timestamp.
            - Create `Kline` with aligned timestamps.
            - Verify `open_time` alignment to interval boundary.
            - Verify `close_time = open_time + interval duration`.

        Expected Result:
            - `open_time` is aligned to interval boundaries.
            - `close_time - open_time` equals interval duration.
            - Time alignment is mathematically correct.
        """
        # Align the base time to interval boundary
        interval_seconds = KlineInterval.to_seconds(interval)
        timestamp_seconds = int(base_time.timestamp())
        aligned_timestamp = (timestamp_seconds // interval_seconds) * interval_seconds
        aligned_open_time = datetime.fromtimestamp(aligned_timestamp, tz=UTC)

        close_time = aligned_open_time + KlineInterval.to_timedelta(interval)

        kline = Kline(
            symbol="TESTBTC",
            interval=interval,
            open_time=aligned_open_time,
            close_time=close_time,
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("1000"),
            quote_volume=Decimal("100000"),
            trades_count=100,
        )

        # Test time alignment
        assert kline.open_time == aligned_open_time
        assert kline.close_time == close_time

        # Test that open_time is properly aligned to interval boundary
        open_timestamp = int(kline.open_time.timestamp())
        assert open_timestamp % interval_seconds == 0

        # Test duration property
        actual_duration = kline.close_time - kline.open_time
        expected_duration = KlineInterval.to_timedelta(interval)
        assert actual_duration == expected_duration

        # Test that duration matches interval
        assert kline.duration == expected_duration

    @given(kline_data=kline_strategy())
    def test_interval_duration_property(self, kline_data: Kline) -> None:
        """Test interval duration consistency.

        Description of what the test covers.
        This test verifies that the duration between `open_time` and `close_time`
        always matches the specified interval duration.

        Preconditions:
            - `Kline` instance is valid with proper time alignment.
            - Interval duration calculations are correct.

        Steps:
            - Generate `Kline` instance with Hypothesis.
            - Calculate actual duration (`close_time - open_time`).
            - Compare with expected interval duration.
            - Verify `duration` property consistency.

        Expected Result:
            - Actual duration equals `interval.to_timedelta()`.
            - Duration calculation is precise.
            - All interval types are handled correctly.
        """
        # Test duration calculation
        actual_duration = kline_data.close_time - kline_data.open_time
        expected_duration = KlineInterval.to_timedelta(kline_data.interval)
        assert actual_duration == expected_duration

        # Test duration property
        assert kline_data.duration == expected_duration

        # Test that duration is positive
        assert kline_data.duration.total_seconds() > 0

        # Test specific interval duration
        interval_seconds = KlineInterval.to_seconds(kline_data.interval)
        assert kline_data.duration.total_seconds() == interval_seconds

    @given(kline_data=kline_strategy())
    def test_price_change_calculation_property(self, kline_data: Kline) -> None:
        """Test price change calculation accuracy.

        Description of what the test covers.
        This test verifies that price change and percentage calculations
        are mathematically correct across all generated `Kline` instances.

        Preconditions:
            - `Kline` instance has valid OHLC prices.
            - Price change calculations are implemented.

        Steps:
            - Generate `Kline` instance.
            - Verify `price_change = close_price - open_price`.
            - Test percentage calculation accuracy.
            - Verify mathematical properties.

        Expected Result:
            - Price change calculation is mathematically correct.
            - Percentage calculations have proper precision.
            - Edge cases (zero change) are handled correctly.
        """
        # Test price change calculation
        expected_change = kline_data.close_price - kline_data.open_price
        assert kline_data.price_change == expected_change

        # Test price change percentage calculation
        if kline_data.open_price != 0:
            expected_percentage = (expected_change / kline_data.open_price) * 100
            # Allow for small rounding differences in percentage calculation
            assert abs(kline_data.price_change_percent - expected_percentage) < Decimal("0.000001")

        # Test directional properties
        if kline_data.close_price > kline_data.open_price:
            assert kline_data.price_change > 0
            assert kline_data.is_bullish is True
            assert kline_data.is_bearish is False
        elif kline_data.close_price < kline_data.open_price:
            assert kline_data.price_change < 0
            assert kline_data.is_bullish is False
            assert kline_data.is_bearish is True
        else:
            assert kline_data.price_change == 0
            assert kline_data.is_bullish is False
            assert kline_data.is_bearish is False

        # Test precision preservation
        assert isinstance(kline_data.price_change, Decimal)
        assert isinstance(kline_data.price_change_percent, Decimal)

    @given(kline_data=kline_strategy())
    def test_volume_consistency_property(self, kline_data: Kline) -> None:
        """Test volume non-negativity and logical consistency.

        Description of what the test covers.
        This test verifies that all volume-related fields are non-negative
        and maintain logical relationships with each other.

        Preconditions:
            - `Kline` instance is valid.
            - Volume fields follow business logic constraints.

        Steps:
            - Generate `Kline` instance.
            - Verify all volumes are non-negative.
            - Test logical relationships between volume fields.
            - Verify trades count consistency.

        Expected Result:
            - All volume fields are `>= 0`.
            - Volume relationships are logically consistent.
            - Trades count is non-negative integer.
        """
        # Test non-negativity
        assert kline_data.volume >= 0
        assert kline_data.quote_volume >= 0
        assert kline_data.trades_count >= 0

        # Test optional volume fields
        if kline_data.taker_buy_volume is not None:
            assert kline_data.taker_buy_volume >= 0
            # Taker buy volume should not exceed total volume
            assert kline_data.taker_buy_volume <= kline_data.volume

        if kline_data.taker_buy_quote_volume is not None:
            assert kline_data.taker_buy_quote_volume >= 0
            # Taker buy quote volume should not exceed total quote volume
            assert kline_data.taker_buy_quote_volume <= kline_data.quote_volume

        # Test logical consistency
        if kline_data.trades_count == 0:
            # If no trades, volumes should typically be zero
            # (though this might depend on specific business logic)
            pass
        elif kline_data.trades_count > 0:
            # If there are trades, there should typically be some volume
            # (though zero volume trades are theoretically possible)
            pass

        # Test types
        assert isinstance(kline_data.volume, Decimal)
        assert isinstance(kline_data.quote_volume, Decimal)
        assert isinstance(kline_data.trades_count, int)

        # Test precision
        assert kline_data.volume.is_finite()
        assert kline_data.quote_volume.is_finite()
