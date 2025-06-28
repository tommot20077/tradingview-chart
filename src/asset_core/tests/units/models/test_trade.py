"""Unit tests for Trade model."""

from typing import Any

import pytest

from asset_core.models.trade import Trade


@pytest.mark.unit
class TestTradeSide:
    """Test cases for TradeSide enum.

    Verifies the correct values and string conversions for the `TradeSide` enum.
    """

    def test_trade_side_values(self) -> None:
        """Test TradeSide enum string values.

        Description of what the test covers.
        Verifies that the `value` attribute of `TradeSide.BUY` and `TradeSide.SELL`
        enums correctly correspond to their string representations.

        Preconditions:
        - None.

        Steps:
        - Assert `TradeSide.BUY.value` is "buy".
        - Assert `TradeSide.SELL.value` is "sell".

        Expected Result:
        - The enum values should match the expected string literals.
        """

    def test_trade_side_string_conversion(self) -> None:
        """Test TradeSide enum value property access.

        Description of what the test covers.
        Verifies that accessing the `.value` property of `TradeSide` enum members
        returns their correct string representation.

        Preconditions:
        - None.

        Steps:
        - Assert `TradeSide.BUY.value` is "buy".
        - Assert `TradeSide.SELL.value` is "sell".

        Expected Result:
        - The `.value` property should return the correct string for each enum member.
        """


@pytest.mark.unit
class TestTradeConstruction:
    """Test cases for Trade model construction.

    Verifies that `Trade` instances can be correctly created with various
    combinations of required and optional fields.
    """

    def test_valid_trade_creation(self, sample_trade: Trade) -> None:
        """Test valid Trade instance creation using fixture.

        Description of what the test covers.
        Verifies that a `Trade` object created using the `sample_trade` fixture
        has all its attributes correctly set to the expected values.

        Preconditions:
        - `sample_trade` fixture is available and provides a valid `Trade` instance.

        Steps:
        - Assert that each attribute of the `sample_trade` object matches
          the predefined values, including symbol, trade ID, price, quantity,
          side, and timestamp (with UTC timezone).

        Expected Result:
        - The `Trade` object should be valid and its attributes should match
          the expected values from the fixture.
        """

    def test_trade_creation_with_all_fields(self) -> None:
        """Test Trade creation with all optional fields provided.

        Description of what the test covers.
        Verifies that a `Trade` object can be successfully created when all
        optional fields (`exchange`, `maker_order_id`, `taker_order_id`,
        `is_buyer_maker`, `received_at`, `metadata`) are provided, and that
        their values are correctly stored.

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

    def test_trade_creation_minimal_fields(self) -> None:
        """Test Trade creation with only required fields.

        Description of what the test covers.
        Verifies that a `Trade` object can be successfully created when only
        the required fields are provided, and that optional fields default to `None`
        or empty values.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance, providing only the required fields.
        - Assert that the required fields are correctly set.
        - Assert that all optional fields are `None` or empty dictionaries.

        Expected Result:
        - The `Trade` object should be created without `ValidationError`.
        - Optional attributes should default to `None` or empty values.
        """


@pytest.mark.unit
class TestTradeValidation:
    """Test cases for Trade model validation.

    Verifies that the `Trade` model correctly validates input data
    for fields like symbol, price, quantity, and volume, ensuring
    data integrity and adherence to business rules.
    """

    def test_symbol_validation(self) -> None:
        """Test symbol field validation and uppercase normalization.

        Description of what the test covers.
        Verifies that the `symbol` field is automatically stripped of whitespace
        and converted to uppercase during `Trade` object creation.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with a symbol string containing leading/trailing
          whitespace and lowercase characters.
        - Assert that the `symbol` attribute of the created `Trade` object is
          stripped and converted to uppercase.

        Expected Result:
        - The `symbol` attribute should be normalized to uppercase and trimmed.
        """

    def test_empty_symbol_validation(self) -> None:
        """Test validation error for empty symbol string.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with an empty string as the `symbol`.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `symbol` set to an empty string.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the symbol cannot be empty.
        """

    def test_whitespace_symbol_validation(self) -> None:
        """Test validation error for whitespace-only symbol.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a symbol consisting only of whitespace characters.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `symbol` set to a whitespace-only string.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the symbol cannot be empty.
        """

    def test_price_validation_positive(self) -> None:
        """Test validation that price must be positive.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a non-positive (`0` or negative) `price`.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `price` set to `Decimal("0")`.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the price must be greater than 0.
        """

    def test_quantity_validation_positive(self) -> None:
        """Test validation that quantity must be positive.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a non-positive (`0` or negative) `quantity`.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `quantity` set to `Decimal("-0.001")`.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the quantity must be greater than 0.
        """

    def test_price_range_validation_minimum(self) -> None:
        """Test price minimum range validation.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a `price` below the minimum allowed value.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `price` set to a value
          just below the minimum allowed price.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the price is below the minimum.
        """

    def test_price_range_validation_maximum(self) -> None:
        """Test price maximum range validation.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a `price` exceeding the maximum allowed value.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `price` set to a value
          just above the maximum allowed price.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the price exceeds the maximum.
        """

    def test_quantity_range_validation_minimum(self) -> None:
        """Test quantity minimum range validation.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a `quantity` below the minimum allowed value.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `quantity` set to a value
          just below the minimum allowed quantity.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the quantity is below the minimum.
        """

    def test_quantity_range_validation_maximum(self) -> None:
        """Test quantity maximum range validation.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with a `quantity` that, when multiplied by `price`, results in a `volume`
        exceeding the maximum allowed volume.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `quantity` set to a value
          that will cause the calculated `volume` to exceed the maximum allowed.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the volume exceeds the maximum.
        """

    def test_volume_validation_minimum(self) -> None:
        """Test trade volume minimum validation.

        Description of what the test covers:
        Verifies that a `ValidationError` is raised when the calculated `volume`
        (price * quantity) of a `Trade` object falls below the minimum allowed volume (`MIN_VOLUME`).

        Preconditions:
        - `MIN_VOLUME` is defined in the `Trade` model's validation logic.

        Steps:
        - Attempt to create a `Trade` instance with `price` and `quantity` values
          that result in a `volume` just below `MIN_VOLUME`.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the volume is below the minimum.
        """
        from datetime import UTC, datetime
        from decimal import Decimal
        from pydantic import ValidationError

        # Assuming MIN_VOLUME is 0.000000000001
        with pytest.raises(ValidationError, match="Trade volume.*is below minimum"):
            Trade(
                symbol="BTCUSDT",
                trade_id="1",
                price=Decimal("0.000000000001"),
                quantity=Decimal("0.0000000000001"),  # Volume = 1e-25, below MIN_VOLUME
                side="buy",
                timestamp=datetime.now(UTC),
            )

    def test_volume_validation_maximum(self) -> None:
        """Test trade volume maximum validation.

        Description of what the test covers.
        Verifies that a `ValidationError` is raised when the calculated `volume`
        (price * quantity) of a `Trade` object exceeds the maximum allowed volume.

        Preconditions:
        - None.

        Steps:
        - Attempt to create a `Trade` instance with `price` and `quantity` values
          that result in a `volume` just above the maximum allowed.
        - Assert that `ValidationError` is raised with a specific error message.

        Expected Result:
        - `ValidationError` should be raised, indicating that the volume exceeds the maximum.
        """


@pytest.mark.unit
class TestTradeTimezoneHandling:
    """Test cases for Trade model timezone handling.

    Verifies that `Trade` objects correctly handle and convert timestamps
    to UTC, regardless of whether they are timezone-aware or naive inputs.
    """

    def test_timezone_aware_timestamp(self) -> None:
        """Test timezone-aware timestamp handling.

        Description of what the test covers.
        Verifies that a timezone-aware timestamp provided during `Trade` creation
        is preserved and correctly recognized as UTC.

        Preconditions:
        - None.

        Steps:
        - Create a UTC timezone-aware `datetime` object.
        - Create a `Trade` instance with this timestamp.
        - Assert that the `tzinfo` of the `trade.timestamp` is UTC.

        Expected Result:
        - The `Trade` object's timestamp should retain its UTC timezone information.
        """

    def test_timezone_naive_timestamp_conversion(self) -> None:
        """Test timezone-naive timestamp is converted to UTC.

        Description of what the test covers.
        Verifies that a timezone-naive timestamp provided during `Trade` creation
        is automatically converted to a UTC timezone-aware timestamp.

        Preconditions:
        - None.

        Steps:
        - Create a timezone-naive `datetime` object.
        - Create a `Trade` instance with this timestamp.
        - Assert that the `tzinfo` of the `trade.timestamp` is UTC.
        - Assert that the naive part of the `trade.timestamp` matches the original naive time.

        Expected Result:
        - The `Trade` object's timestamp should be converted to UTC timezone-aware.
        """

    def test_timezone_conversion_to_utc(self) -> None:
        """Test timestamp from different timezone is converted to UTC.

        Description of what the test covers:
        Verifies that a timestamp from a non-UTC timezone is correctly converted
        to UTC when creating a `Trade` object.

        Preconditions:
        - None.

        Steps:
        - Create a timezone-aware `datetime` object in a non-UTC timezone (e.g., EST).
        - Create a `Trade` instance with this timestamp.
        - Assert that the `tzinfo` of the `trade.timestamp` is UTC.
        - Assert that the `trade.timestamp` value is correctly converted to the
          equivalent UTC time.

        Expected Result:
        - The `Trade` object's timestamp should be converted to UTC, preserving the correct point in time.
        """
        from datetime import datetime
        from decimal import Decimal
        from zoneinfo import ZoneInfo

        # Create an EST timezone-aware datetime
        est = ZoneInfo("America/New_York")
        est_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=est)  # 12:00 PM EST

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="1",
            price=Decimal("100"),
            quantity=Decimal("1"),
            side="buy",
            timestamp=est_dt,
        )

        assert trade.timestamp.tzinfo == ZoneInfo("UTC")
        # 12:00 PM EST is 5:00 PM UTC (during standard time, no DST)
        expected_utc_dt = datetime(2024, 1, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert trade.timestamp == expected_utc_dt

    def test_received_at_timezone_handling(self) -> None:
        """Test received_at timezone handling.

        Description of what the test covers.
        Verifies that the `received_at` timestamp, if provided as a naive datetime,
        is also converted to a UTC timezone-aware datetime.

        Preconditions:
        - None.

        Steps:
        - Create a timezone-naive `datetime` object for `received_at`.
        - Create a `Trade` instance with this `received_at` timestamp.
        - Assert that the `tzinfo` of `trade.received_at` is UTC.

        Expected Result:
        - The `received_at` timestamp should be converted to UTC timezone-aware.
        """


@pytest.mark.unit
class TestTradeCalculatedProperties:
    """Test cases for Trade model calculated properties.

    Verifies the correctness of derived properties such as `volume`
    and ensures precision is maintained in calculations.
    """

    def test_volume_calculation(self, sample_trade: Trade) -> None:
        """Test volume calculation property.

        Description of what the test covers.
        Verifies that the `volume` property of a `Trade` object is correctly
        calculated as the product of `price` and `quantity`.

        Preconditions:
        - `sample_trade` fixture is available.

        Steps:
        - Calculate the expected volume manually (`price * quantity`).
        - Assert that `sample_trade.volume` matches the expected volume.
        - Assert that `sample_trade.volume` matches a specific Decimal value.

        Expected Result:
        - The `volume` property should be accurately calculated.
        """

    def test_volume_calculation_precision(self) -> None:
        """Test volume calculation maintains precision.

        Description of what the test covers.
        Verifies that the `volume` calculation preserves the precision of `Decimal`
        numbers, avoiding floating-point inaccuracies.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with `Decimal` values for `price` and `quantity`.
        - Calculate the expected volume using `Decimal` arithmetic.
        - Assert that `trade.volume` exactly matches the expected `Decimal` volume.

        Expected Result:
        - The `volume` property should be calculated with precise `Decimal` arithmetic.
        """


@pytest.mark.unit
class TestTradeSerialization:
    """Test cases for Trade model serialization.

    Verifies that `Trade` objects can be correctly converted to dictionary
    and JSON-serializable formats, preserving data and handling optional fields.
    """

    def test_to_dict_conversion(self, sample_trade: Trade) -> None:
        """Test to_dict method.

        Description of what the test covers.
        Verifies that the `to_dict()` method of a `Trade` object correctly
        converts its attributes into a dictionary representation, including
        string conversion for Decimal and datetime objects.

        Preconditions:
        - `sample_trade` fixture is available.

        Steps:
        - Call `to_dict()` on the `sample_trade` object.
        - Assert that the resulting dictionary contains all expected keys and
          that their values are correctly formatted (e.g., Decimals as strings,
          timestamps as ISO 8601 strings).

        Expected Result:
        - The `to_dict()` method should return a dictionary with all trade details.
        - Decimal values should be represented as strings.
        - The timestamp should be present and in ISO 8601 format.
        """

    def test_to_dict_with_optional_fields(self) -> None:
        """Test to_dict with optional fields.

        Description of what the test covers.
        Verifies that the `to_dict()` method correctly includes optional fields
        (`exchange`, `received_at`, `metadata`) when they are present in the `Trade` object.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with values for optional fields.
        - Call `to_dict()` on the `Trade` object.
        - Assert that the resulting dictionary contains the optional fields
          and their values are correctly represented (e.g., `received_at` as string).

        Expected Result:
        - The `to_dict()` method should include all optional fields with their values.
        """

    def test_to_dict_without_received_at(self, sample_trade: Trade) -> None:
        """Test to_dict when received_at is None.

        Description of what the test covers.
        Verifies that the `to_dict()` method correctly represents `received_at`
        as `None` when it is not set in the `Trade` object.

        Preconditions:
        - `sample_trade` fixture is available and its `received_at` is `None`.

        Steps:
        - Call `to_dict()` on the `sample_trade` object.
        - Assert that `trade_dict["received_at"]` is `None`.

        Expected Result:
        - The `received_at` field in the dictionary should be `None`.
        """

    def test_model_dump_json_serializable(self, sample_trade: Trade) -> None:
        """Test model can be dumped to JSON-serializable format.

        Description of what the test covers.
        Verifies that the `model_dump()` method produces a dictionary that is
        directly JSON-serializable without custom encoders, by converting `Decimal`
        and `datetime` objects to strings.

        Preconditions:
        - `sample_trade` fixture is available.

        Steps:
        - Call `model_dump()` on the `sample_trade` object.
        - Attempt to `json.dumps()` the resulting dictionary, using `default=str`
          as a fallback for types not natively handled by Pydantic's `model_dump()`.
        - Assert that the JSON serialization is successful and the result is a string.

        Expected Result:
        - The `Trade` model's dumped data should be compatible with JSON serialization.
        """


@pytest.mark.unit
class TestTradeStringRepresentation:
    """Test cases for Trade model string representation.

    Verifies that the `Trade` model's string representation (`str()`) provides
    a concise and informative summary of the trade details.
    """

    def test_string_representation(self, sample_trade: Trade) -> None:
        """Test string representation.

        Description of what the test covers.
        Verifies that the `str()` representation of a `Trade` object contains
        key information such as symbol, side, quantity, and price.

        Preconditions:
        - `sample_trade` fixture is available.

        Steps:
        - Convert the `sample_trade` object to its string representation.
        - Assert that the string contains the expected parts of the trade data.

        Expected Result:
        - The string representation should be informative and include core trade details.
        """

    def test_string_representation_sell_side(self) -> None:
        """Test string representation for sell side.

        Description of what the test covers:
        Verifies that the `str()` representation of a `Trade` object with `TradeSide.SELL`
        correctly includes the "sell" indicator and other trade details.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with `side` set to `TradeSide.SELL`.
        - Convert the trade object to its string representation.
        - Assert that the string contains "sell" and the symbol.

        Expected Result:
        - The string representation should correctly reflect the sell side and other trade details.
        """


@pytest.mark.unit
class TestTradeBoundaryValues:
    """Test cases for Trade model boundary values.

    Verifies that the `Trade` model correctly handles and validates values
    at the minimum and maximum boundaries for price, quantity, and volume,
    as well as edge cases for timestamps.
    """

    def test_minimum_valid_values(self) -> None:
        """Test trade with minimum valid values.

        Description of what the test covers:
        Verifies that a `Trade` object can be successfully created with `price`
        and `quantity` values at their minimum valid thresholds, and that the
        calculated `volume` meets its minimum requirement.

        Preconditions:
        - None.

        Steps:
        - Define `min_price` and `min_quantity` to meet the minimum volume requirement.
        - Create a `Trade` instance with these minimum values.
        - Assert that `trade.price` and `trade.quantity` match the defined minimums.
        - Assert that the calculated `trade.volume` is greater than or equal to
          the minimum allowed volume and matches the expected calculated value.

        Expected Result:
        - The `Trade` object should be valid and its attributes should reflect
          the minimum valid inputs, with correct volume calculation.
        """

    def test_maximum_valid_values(self) -> None:
        """Test trade with maximum valid values.

        Description of what the test covers:
        Verifies that a `Trade` object can be successfully created with `price`
        and `quantity` values at their maximum valid thresholds, ensuring the
        calculated `volume` does not exceed its maximum requirement.

        Preconditions:
        - None.

        Steps:
        - Define `max_price` and `max_quantity` to stay within the maximum volume limit.
        - Create a `Trade` instance with these maximum values.
        - Assert that `trade.price` and `trade.quantity` match the defined maximums.
        - Assert that the calculated `trade.volume` is less than or equal to
          the maximum allowed volume.

        Expected Result:
        - The `Trade` object should be valid and its attributes should reflect
          the maximum valid inputs, with correct volume calculation.
        """

    def test_edge_case_timestamps(self) -> None:
        """Test edge case timestamps.

        Description of what the test covers:
        Verifies that `Trade` objects correctly handle timestamps at the extreme
        ends of the valid range (e.g., Unix epoch, far future).

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with a timestamp set to the Unix epoch (1970-01-01).
        - Assert that the `trade.timestamp` matches the input.
        - Create another `Trade` instance with a timestamp set to a far future date.
        - Assert that the `trade.timestamp` matches the input.

        Expected Result:
        - `Trade` objects should correctly store and represent timestamps at edge cases.
        """


@pytest.mark.unit
class TestTradeInvalidData:
    """Test cases for Trade model with invalid data.

    Verifies that `Trade` model validation correctly rejects invalid data
    types and missing required fields, raising `ValidationError`.
    """

    def test_invalid_data_types(self, invalid_data_samples: dict[str, Any]) -> None:
        """Test various invalid data types.

        Description of what the test covers:
        Verifies that `ValidationError` is raised when attempting to create a `Trade`
        object with invalid data types for its fields (e.g., non-numeric price,
        non-string symbol).

        Preconditions:
        - `invalid_data_samples` fixture is available.

        Steps:
        - Iterate through various invalid data samples for `price`, `quantity`,
          and `symbol`.
        - For each invalid sample, attempt to create a `Trade` object.
        - Assert that `ValidationError` is raised in each case.

        Expected Result:
        - `ValidationError` should be raised for all invalid data type inputs.
        """

    def test_missing_required_fields(self) -> None:
        """Test missing required fields.

        Description of what the test covers:
        Verifies that a `ValidationError` is raised when attempting to create a `Trade`
        object with any of its required fields missing.

        Preconditions:
        - None.

        Steps:
        - Iterate through each required field of the `Trade` model.
        - For each field, create a `Trade` data dictionary with that field removed.
        - Attempt to create a `Trade` object from the modified dictionary.
        - Assert that `ValidationError` is raised in each case.

        Expected Result:
        - `ValidationError` should be raised for each missing required field.
        """


@pytest.mark.unit
@pytest.mark.models
class TestTradeIntegration:
    """Integration test cases for Trade model.

    These tests verify the end-to-end behavior of the `Trade` model,
    including its lifecycle from creation through calculation, serialization,
    and string representation.
    """

    def test_trade_lifecycle(self) -> None:
        """Test complete trade lifecycle.

        Description of what the test covers:
        Verifies the full lifecycle of a `Trade` object, from instantiation
        to calculation of derived properties, serialization to dictionary,
        and string representation.

        Preconditions:
        - None.

        Steps:
        - Create a `Trade` instance with all relevant fields.
        - Assert the correctness of calculated `volume`.
        - Convert the `Trade` object to a dictionary using `to_dict()`.
        - Assert the correctness of `volume` in the dictionary.
        - Convert the `Trade` object to its string representation.
        - Assert that key information is present in the string representation.

        Expected Result:
        - The `Trade` object should behave correctly throughout its lifecycle,
          with consistent data across different representations.
        """

    def test_trade_equality_and_hashing(self) -> None:
        """Test trade equality and hashing behavior.

        Description of what the test covers:
        Verifies that `Trade` objects with identical content are considered equal
        and have the same hash, while objects with different content are not equal.

        Preconditions:
        - None.

        Steps:
        - Create two `Trade` objects with identical data.
        - Assert that they are equal (`==`).
        - Create a third `Trade` object with different data.
        - Assert that it is not equal to the first two.

        Expected Result:
        - `Trade` objects should correctly implement equality and hashing based on their content.
        """
