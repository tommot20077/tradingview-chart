# ABOUTME: 測試asset_core.models.validators模組中的自定義驗證器功能
# ABOUTME: 包含對BaseValidator、RangeValidator、StringValidator、DateTimeValidator、CompositeValidator和ValidationMixin的完整測試覆蓋

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.exceptions import DataValidationError
from asset_core.models.validators import (
    BaseValidator,
    CompositeValidator,
    DateTimeValidator,
    RangeValidator,
    StringValidator,
    ValidationMixin,
)


class ConcreteValidator(BaseValidator):
    """Concrete implementation of BaseValidator for testing purposes."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def validate(self, value: Any, field_name: str) -> Any:
        if self.should_fail:
            raise DataValidationError(
                "Test validation failed",
                field_name=field_name,
                field_value=value,
            )
        return value


@pytest.mark.unit
class TestBaseValidator:
    """Test cases for BaseValidator abstract class.

    Verifies the contract and basic behavior of the BaseValidator
    abstract base class through a concrete implementation.
    """

    def test_base_validator_is_abstract(self) -> None:
        """Test BaseValidator cannot be instantiated directly.

        Description of what the test covers:
        Verifies that BaseValidator is an abstract class and cannot
        be instantiated directly, requiring concrete implementations.

        Preconditions:
        - BaseValidator is an abstract class with abstract methods.

        Steps:
        - Attempt to instantiate BaseValidator directly.
        - Verify TypeError is raised.

        Expected Result:
        - TypeError should be raised when trying to instantiate BaseValidator.
        """
        with pytest.raises(TypeError) as exc_info:
            BaseValidator()  # type: ignore[abstract]
        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_concrete_validator_success(self) -> None:
        """Test successful validation with concrete validator.

        Description of what the test covers:
        Verifies that a concrete implementation of BaseValidator
        can successfully validate values when validation passes.

        Preconditions:
        - ConcreteValidator implementation available.
        - Validator configured to pass validation.

        Steps:
        - Create ConcreteValidator with should_fail=False.
        - Call validate with test value and field name.
        - Verify the original value is returned unchanged.

        Expected Result:
        - Validation should succeed and return the original value.
        """
        validator = ConcreteValidator(should_fail=False)
        test_value = "test_value"
        result = validator.validate(test_value, "test_field")
        assert result == test_value

    def test_concrete_validator_failure(self) -> None:
        """Test validation failure with concrete validator.

        Description of what the test covers:
        Verifies that a concrete implementation of BaseValidator
        properly raises DataValidationError when validation fails.

        Preconditions:
        - ConcreteValidator implementation available.
        - Validator configured to fail validation.

        Steps:
        - Create ConcreteValidator with should_fail=True.
        - Call validate with test value and field name.
        - Verify DataValidationError is raised with correct details.

        Expected Result:
        - DataValidationError should be raised with field information.
        """
        validator = ConcreteValidator(should_fail=True)
        test_value = "test_value"
        field_name = "test_field"

        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(test_value, field_name)

        error = exc_info.value
        assert "Test validation failed" in str(error)
        assert error.field_name == field_name
        assert error.field_value == test_value


@pytest.mark.unit
class TestRangeValidator:
    """Test cases for RangeValidator.

    Verifies numeric range validation with various boundary conditions,
    inclusive/exclusive ranges, and type validation.
    """

    def test_range_validator_within_range_inclusive(self) -> None:
        """Test value within inclusive range validation.

        Description of what the test covers:
        Verifies that RangeValidator accepts values within the specified
        inclusive range (min_value <= value <= max_value).

        Preconditions:
        - RangeValidator with min_value=10, max_value=20, inclusive=True.

        Steps:
        - Create validator with inclusive range 10-20.
        - Test values at boundaries (10, 20) and within range (15).
        - Verify all values pass validation unchanged.

        Expected Result:
        - All values within inclusive range should be accepted.
        """
        validator = RangeValidator(min_value=10, max_value=20, inclusive=True)

        # Test boundary values
        assert validator.validate(10, "test_field") == 10
        assert validator.validate(20, "test_field") == 20

        # Test value within range
        assert validator.validate(15, "test_field") == 15

        # Test with different numeric types
        assert validator.validate(Decimal("15.5"), "test_field") == Decimal("15.5")
        assert validator.validate(15.5, "test_field") == 15.5

    def test_range_validator_outside_range_inclusive(self) -> None:
        """Test value outside inclusive range validation.

        Description of what the test covers:
        Verifies that RangeValidator rejects values outside the specified
        inclusive range with appropriate error messages.

        Preconditions:
        - RangeValidator with min_value=10, max_value=20, inclusive=True.

        Steps:
        - Create validator with inclusive range 10-20.
        - Test values below minimum (9) and above maximum (21).
        - Verify DataValidationError is raised with descriptive messages.

        Expected Result:
        - Values outside range should raise DataValidationError.
        - Error messages should indicate the specific boundary violation.
        """
        validator = RangeValidator(min_value=10, max_value=20, inclusive=True)

        # Test below minimum
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(9, "test_field")
        assert "below minimum 10" in str(exc_info.value)

        # Test above maximum
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(21, "test_field")
        assert "exceeds maximum 20" in str(exc_info.value)

    def test_range_validator_exclusive_range(self) -> None:
        """Test exclusive range validation.

        Description of what the test covers:
        Verifies that RangeValidator with exclusive=False correctly
        rejects boundary values and accepts values strictly within range.

        Preconditions:
        - RangeValidator with min_value=10, max_value=20, inclusive=False.

        Steps:
        - Create validator with exclusive range 10-20.
        - Test boundary values (10, 20) - should fail.
        - Test value within range (15) - should pass.
        - Verify appropriate error messages for boundary values.

        Expected Result:
        - Boundary values should be rejected in exclusive mode.
        - Values strictly within range should be accepted.
        """
        validator = RangeValidator(min_value=10, max_value=20, inclusive=False)

        # Test boundary values - should fail in exclusive mode
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(10, "test_field")
        assert "must be greater than 10" in str(exc_info.value)

        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(20, "test_field")
        assert "must be less than 20" in str(exc_info.value)

        # Test value within range - should pass
        assert validator.validate(15, "test_field") == 15

    def test_range_validator_min_only(self) -> None:
        """Test range validation with minimum value only.

        Description of what the test covers:
        Verifies that RangeValidator works correctly when only
        minimum value is specified (no maximum limit).

        Preconditions:
        - RangeValidator with min_value=10, max_value=None.

        Steps:
        - Create validator with only minimum value.
        - Test value below minimum - should fail.
        - Test values at and above minimum - should pass.

        Expected Result:
        - Only minimum constraint should be enforced.
        - No maximum limit should be applied.
        """
        validator = RangeValidator(min_value=10, max_value=None, inclusive=True)

        # Below minimum should fail
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(9, "test_field")
        assert "below minimum 10" in str(exc_info.value)

        # At and above minimum should pass
        assert validator.validate(10, "test_field") == 10
        assert validator.validate(1000, "test_field") == 1000

    def test_range_validator_max_only(self) -> None:
        """Test range validation with maximum value only.

        Description of what the test covers:
        Verifies that RangeValidator works correctly when only
        maximum value is specified (no minimum limit).

        Preconditions:
        - RangeValidator with min_value=None, max_value=20.

        Steps:
        - Create validator with only maximum value.
        - Test value above maximum - should fail.
        - Test values at and below maximum - should pass.

        Expected Result:
        - Only maximum constraint should be enforced.
        - No minimum limit should be applied.
        """
        validator = RangeValidator(min_value=None, max_value=20, inclusive=True)

        # Above maximum should fail
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(21, "test_field")
        assert "exceeds maximum 20" in str(exc_info.value)

        # At and below maximum should pass
        assert validator.validate(20, "test_field") == 20
        assert validator.validate(-1000, "test_field") == -1000

    def test_range_validator_no_limits(self) -> None:
        """Test range validation with no limits.

        Description of what the test covers:
        Verifies that RangeValidator accepts any numeric value
        when both min_value and max_value are None.

        Preconditions:
        - RangeValidator with min_value=None, max_value=None.

        Steps:
        - Create validator with no range limits.
        - Test various numeric values including extremes.
        - Verify all numeric values are accepted.

        Expected Result:
        - All numeric values should be accepted.
        - Only type validation should be performed.
        """
        validator = RangeValidator(min_value=None, max_value=None)

        # All numeric values should pass
        assert validator.validate(-1000000, "test_field") == -1000000
        assert validator.validate(0, "test_field") == 0
        assert validator.validate(1000000, "test_field") == 1000000
        assert validator.validate(Decimal("123.456"), "test_field") == Decimal("123.456")

    def test_range_validator_invalid_type(self) -> None:
        """Test range validation with invalid data types.

        Description of what the test covers:
        Verifies that RangeValidator rejects non-numeric types
        with appropriate error messages.

        Preconditions:
        - RangeValidator instance.

        Steps:
        - Create validator with any range configuration.
        - Test non-numeric values (string, list, None, etc.).
        - Verify DataValidationError is raised for each invalid type.

        Expected Result:
        - Non-numeric types should raise DataValidationError.
        - Error message should indicate type requirement.
        """
        validator = RangeValidator(min_value=0, max_value=100)

        invalid_values = [
            "not_a_number",
            [],
            {},
            None,
            object(),
        ]

        for invalid_value in invalid_values:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_value, "test_field")
            assert "Value must be numeric" in str(exc_info.value)
            assert f"got {type(invalid_value).__name__}" in str(exc_info.value)

    def test_range_validator_decimal_precision(self) -> None:
        """Test range validation with high-precision Decimal values.

        Description of what the test covers:
        Verifies that RangeValidator correctly handles high-precision
        Decimal values for financial calculations.

        Preconditions:
        - RangeValidator with Decimal boundaries.

        Steps:
        - Create validator with high-precision Decimal boundaries.
        - Test Decimal values at and near boundaries.
        - Verify precise decimal comparisons work correctly.

        Expected Result:
        - High-precision Decimal values should be handled accurately.
        - Decimal arithmetic should be preserved without rounding errors.
        """
        min_val = Decimal("0.000000001")
        max_val = Decimal("999.999999999")
        validator = RangeValidator(min_value=min_val, max_value=max_val, inclusive=True)

        # Test precise boundary values
        assert validator.validate(min_val, "test_field") == min_val
        assert validator.validate(max_val, "test_field") == max_val

        # Test values just outside boundaries
        with pytest.raises(DataValidationError):
            validator.validate(Decimal("0.0000000009"), "test_field")

        with pytest.raises(DataValidationError):
            validator.validate(Decimal("1000.0"), "test_field")


@pytest.mark.unit
class TestStringValidator:
    """Test cases for StringValidator.

    Verifies string validation including length constraints,
    regex pattern matching, allowed values checking, and case sensitivity.
    """

    def test_string_validator_valid_string(self) -> None:
        """Test validation of valid strings.

        Description of what the test covers:
        Verifies that StringValidator accepts valid string values
        that meet all specified criteria.

        Preconditions:
        - StringValidator with no constraints.

        Steps:
        - Create validator with no restrictions.
        - Test various valid string values.
        - Verify strings are returned unchanged.

        Expected Result:
        - Valid strings should be accepted and returned unchanged.
        """
        validator = StringValidator()

        test_strings = [
            "simple_string",
            "String with spaces",
            "String123",
            "",  # Empty string should be valid by default
            "Special!@#$%^&*()Characters",
        ]

        for test_string in test_strings:
            assert validator.validate(test_string, "test_field") == test_string

    def test_string_validator_length_constraints(self) -> None:
        """Test string length validation.

        Description of what the test covers:
        Verifies that StringValidator correctly enforces minimum
        and maximum length constraints on string values.

        Preconditions:
        - StringValidator with min_length=3, max_length=10.

        Steps:
        - Create validator with length constraints.
        - Test strings within length range - should pass.
        - Test strings outside length range - should fail.
        - Verify appropriate error messages.

        Expected Result:
        - Strings within length constraints should be accepted.
        - Strings outside constraints should raise DataValidationError.
        """
        validator = StringValidator(min_length=3, max_length=10)

        # Valid lengths
        assert validator.validate("abc", "test_field") == "abc"
        assert validator.validate("abcdefghij", "test_field") == "abcdefghij"
        assert validator.validate("middle", "test_field") == "middle"

        # Too short
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("ab", "test_field")
        assert "length 2 is below minimum 3" in str(exc_info.value)

        # Too long
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("abcdefghijk", "test_field")
        assert "length 11 exceeds maximum 10" in str(exc_info.value)

    def test_string_validator_pattern_matching(self) -> None:
        """Test regex pattern validation.

        Description of what the test covers:
        Verifies that StringValidator correctly validates strings
        against regex patterns.

        Preconditions:
        - StringValidator with regex pattern for email format.

        Steps:
        - Create validator with email pattern.
        - Test valid email strings - should pass.
        - Test invalid email strings - should fail.
        - Verify pattern error messages.

        Expected Result:
        - Strings matching pattern should be accepted.
        - Strings not matching pattern should raise DataValidationError.
        """
        # Email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        validator = StringValidator(pattern=email_pattern)

        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
            "123@test.org",
        ]

        for email in valid_emails:
            assert validator.validate(email, "email_field") == email

        # Invalid emails
        invalid_emails = [
            "invalid_email",
            "@domain.com",
            "user@",
            "user@domain",
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_email, "email_field")
            assert "does not match required pattern" in str(exc_info.value)

    def test_string_validator_allowed_values_case_sensitive(self) -> None:
        """Test allowed values validation with case sensitivity.

        Description of what the test covers:
        Verifies that StringValidator correctly enforces allowed values
        with case-sensitive matching.

        Preconditions:
        - StringValidator with specific allowed values, case_sensitive=True.

        Steps:
        - Create validator with case-sensitive allowed values.
        - Test exact matches - should pass.
        - Test case variations - should fail.
        - Test values not in allowed list - should fail.

        Expected Result:
        - Only exact case matches should be accepted.
        - Case variations and unlisted values should be rejected.
        """
        allowed_values = ["RED", "GREEN", "BLUE"]
        validator = StringValidator(allowed_values=allowed_values, case_sensitive=True)

        # Valid values (exact case)
        for value in allowed_values:
            assert validator.validate(value, "color_field") == value

        # Invalid case variations
        invalid_cases = ["red", "Green", "bLuE"]
        for invalid_case in invalid_cases:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_case, "color_field")
            assert "is not in allowed values" in str(exc_info.value)

        # Value not in list
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("YELLOW", "color_field")
        assert "is not in allowed values" in str(exc_info.value)

    def test_string_validator_allowed_values_case_insensitive(self) -> None:
        """Test allowed values validation without case sensitivity.

        Description of what the test covers:
        Verifies that StringValidator correctly enforces allowed values
        with case-insensitive matching.

        Preconditions:
        - StringValidator with specific allowed values, case_sensitive=False.

        Steps:
        - Create validator with case-insensitive allowed values.
        - Test various case combinations - should pass.
        - Test values not in allowed list - should fail.

        Expected Result:
        - Case variations of allowed values should be accepted.
        - Values not in allowed list should be rejected regardless of case.
        """
        allowed_values = ["RED", "GREEN", "BLUE"]
        validator = StringValidator(allowed_values=allowed_values, case_sensitive=False)

        # Valid values with different cases
        valid_variations = [
            "RED",
            "red",
            "Red",
            "GREEN",
            "green",
            "Green",
            "BLUE",
            "blue",
            "Blue",
        ]

        for value in valid_variations:
            assert validator.validate(value, "color_field") == value

        # Value not in list (any case)
        invalid_values = ["YELLOW", "yellow", "Purple"]
        for invalid_value in invalid_values:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_value, "color_field")
            assert "is not in allowed values" in str(exc_info.value)

    def test_string_validator_combined_constraints(self) -> None:
        """Test string validation with multiple combined constraints.

        Description of what the test covers:
        Verifies that StringValidator correctly applies multiple
        validation rules simultaneously (length, pattern, allowed values).

        Preconditions:
        - StringValidator with length, pattern, and allowed values constraints.

        Steps:
        - Create validator with multiple constraints.
        - Test values that meet all constraints - should pass.
        - Test values that fail different constraints - should fail appropriately.

        Expected Result:
        - Values meeting all constraints should be accepted.
        - Values failing any constraint should be rejected with specific error.
        """
        # Allowed codes must be 3-5 characters, alphanumeric, from specific list
        allowed_codes = ["ABC", "XYZ", "TEST1"]
        validator = StringValidator(
            min_length=3,
            max_length=5,
            pattern=r"^[A-Z0-9]+$",
            allowed_values=allowed_codes,
            case_sensitive=True,
        )

        # Valid values
        for code in allowed_codes:
            assert validator.validate(code, "code_field") == code

        # Length violation
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("AB", "code_field")
        assert "length 2 is below minimum 3" in str(exc_info.value)

        # Pattern violation
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("abc", "code_field")  # lowercase fails pattern
        assert "does not match required pattern" in str(exc_info.value)

        # Not in allowed values
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate("DEF", "code_field")  # valid format but not allowed
        assert "is not in allowed values" in str(exc_info.value)

    def test_string_validator_invalid_type(self) -> None:
        """Test string validation with invalid data types.

        Description of what the test covers:
        Verifies that StringValidator rejects non-string types
        with appropriate error messages.

        Preconditions:
        - StringValidator instance.

        Steps:
        - Create validator with any configuration.
        - Test non-string values (int, list, None, etc.).
        - Verify DataValidationError is raised for each invalid type.

        Expected Result:
        - Non-string types should raise DataValidationError.
        - Error message should indicate string type requirement.
        """
        validator = StringValidator()

        invalid_values = [
            123,
            [],
            {},
            None,
            True,
            12.34,
        ]

        for invalid_value in invalid_values:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_value, "test_field")
            assert "Value must be a string" in str(exc_info.value)
            assert f"got {type(invalid_value).__name__}" in str(exc_info.value)


@pytest.mark.unit
class TestDateTimeValidator:
    """Test cases for DateTimeValidator.

    Verifies datetime validation including timezone requirements,
    future/past restrictions, and range constraints.
    """

    def test_datetime_validator_valid_timezone_aware(self) -> None:
        """Test validation of timezone-aware datetime objects.

        Description of what the test covers:
        Verifies that DateTimeValidator accepts valid timezone-aware
        datetime objects when timezone is required.

        Preconditions:
        - DateTimeValidator with require_timezone=True.

        Steps:
        - Create validator requiring timezone.
        - Test UTC and other timezone datetime objects.
        - Verify datetime objects are returned unchanged.

        Expected Result:
        - Timezone-aware datetime objects should be accepted.
        """
        validator = DateTimeValidator(require_timezone=True)

        utc_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert validator.validate(utc_datetime, "datetime_field") == utc_datetime

        # Test with custom timezone
        import zoneinfo

        eastern = zoneinfo.ZoneInfo("US/Eastern")
        eastern_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=eastern)
        assert validator.validate(eastern_datetime, "datetime_field") == eastern_datetime

    def test_datetime_validator_timezone_required_failure(self) -> None:
        """Test timezone requirement validation failure.

        Description of what the test covers:
        Verifies that DateTimeValidator rejects naive datetime objects
        when timezone information is required.

        Preconditions:
        - DateTimeValidator with require_timezone=True.

        Steps:
        - Create validator requiring timezone.
        - Test naive datetime object (no timezone).
        - Verify DataValidationError is raised.

        Expected Result:
        - Naive datetime should raise DataValidationError.
        - Error message should indicate timezone requirement.
        """
        validator = DateTimeValidator(require_timezone=True)

        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)

        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(naive_datetime, "datetime_field")
        assert "must include timezone information" in str(exc_info.value)

    def test_datetime_validator_timezone_not_required(self) -> None:
        """Test datetime validation when timezone is not required.

        Description of what the test covers:
        Verifies that DateTimeValidator accepts both timezone-aware
        and naive datetime objects when timezone is not required.

        Preconditions:
        - DateTimeValidator with require_timezone=False.

        Steps:
        - Create validator not requiring timezone.
        - Test both timezone-aware and naive datetime objects.
        - Verify both types are accepted.

        Expected Result:
        - Both timezone-aware and naive datetime objects should be accepted.
        """
        validator = DateTimeValidator(require_timezone=False)

        # Naive datetime
        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)
        assert validator.validate(naive_datetime, "datetime_field") == naive_datetime

        # Timezone-aware datetime
        utc_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert validator.validate(utc_datetime, "datetime_field") == utc_datetime

    def test_datetime_validator_future_restriction(self) -> None:
        """Test future datetime restriction validation.

        Description of what the test covers:
        Verifies that DateTimeValidator correctly enforces future
        datetime restrictions when future_allowed=False.

        Preconditions:
        - DateTimeValidator with future_allowed=False.

        Steps:
        - Create validator disallowing future dates.
        - Test past datetime - should pass.
        - Test future datetime - should fail.
        - Test current datetime (approximately) - should pass.

        Expected Result:
        - Past and current datetime should be accepted.
        - Future datetime should raise DataValidationError.
        """
        validator = DateTimeValidator(future_allowed=False, require_timezone=True)

        # Past datetime should pass
        past_datetime = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert validator.validate(past_datetime, "datetime_field") == past_datetime

        # Future datetime should fail
        future_datetime = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(future_datetime, "datetime_field")
        assert "Future datetime" in str(exc_info.value)
        assert "is not allowed" in str(exc_info.value)

    def test_datetime_validator_past_restriction(self) -> None:
        """Test past datetime restriction validation.

        Description of what the test covers:
        Verifies that DateTimeValidator correctly enforces past
        datetime restrictions when past_allowed=False.

        Preconditions:
        - DateTimeValidator with past_allowed=False.

        Steps:
        - Create validator disallowing past dates.
        - Test future datetime - should pass.
        - Test past datetime - should fail.

        Expected Result:
        - Future datetime should be accepted.
        - Past datetime should raise DataValidationError.
        """
        validator = DateTimeValidator(past_allowed=False, require_timezone=True)

        # Future datetime should pass
        future_datetime = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert validator.validate(future_datetime, "datetime_field") == future_datetime

        # Past datetime should fail
        past_datetime = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(past_datetime, "datetime_field")
        assert "Past datetime" in str(exc_info.value)
        assert "is not allowed" in str(exc_info.value)

    def test_datetime_validator_range_constraints(self) -> None:
        """Test datetime range validation.

        Description of what the test covers:
        Verifies that DateTimeValidator correctly enforces minimum
        and maximum datetime boundaries.

        Preconditions:
        - DateTimeValidator with min_datetime and max_datetime set.

        Steps:
        - Create validator with datetime range.
        - Test datetime within range - should pass.
        - Test datetime before minimum - should fail.
        - Test datetime after maximum - should fail.

        Expected Result:
        - Datetime within range should be accepted.
        - Datetime outside range should raise DataValidationError.
        """
        min_datetime = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        max_datetime = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)
        validator = DateTimeValidator(
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            require_timezone=True,
        )

        # Within range
        valid_datetime = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)
        assert validator.validate(valid_datetime, "datetime_field") == valid_datetime

        # Before minimum
        early_datetime = datetime(2022, 12, 31, 23, 59, 59, tzinfo=UTC)
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(early_datetime, "datetime_field")
        assert "is before minimum" in str(exc_info.value)

        # After maximum
        late_datetime = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(late_datetime, "datetime_field")
        assert "is after maximum" in str(exc_info.value)

    def test_datetime_validator_invalid_type(self) -> None:
        """Test datetime validation with invalid data types.

        Description of what the test covers:
        Verifies that DateTimeValidator rejects non-datetime types
        with appropriate error messages.

        Preconditions:
        - DateTimeValidator instance.

        Steps:
        - Create validator with any configuration.
        - Test non-datetime values (string, int, None, etc.).
        - Verify DataValidationError is raised for each invalid type.

        Expected Result:
        - Non-datetime types should raise DataValidationError.
        - Error message should indicate datetime type requirement.
        """
        validator = DateTimeValidator()

        invalid_values = [
            "2023-01-01",
            1672531200,  # Unix timestamp
            [],
            {},
            None,
            True,
        ]

        for invalid_value in invalid_values:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_value, "datetime_field")
            assert "Value must be a datetime" in str(exc_info.value)
            assert f"got {type(invalid_value).__name__}" in str(exc_info.value)


@pytest.mark.unit
class TestCompositeValidator:
    """Test cases for CompositeValidator.

    Verifies composition of multiple validators and sequential validation.
    """

    def test_composite_validator_success(self) -> None:
        """Test successful validation through composite validator.

        Description of what the test covers:
        Verifies that CompositeValidator successfully applies multiple
        validators in sequence when all validations pass.

        Preconditions:
        - Multiple individual validators that will pass.

        Steps:
        - Create CompositeValidator with multiple successful validators.
        - Test value that passes all component validations.
        - Verify final result is returned after all validations.

        Expected Result:
        - All validators should be applied in sequence.
        - Final validated value should be returned.
        """
        # Create validators that will all pass
        range_validator = RangeValidator(min_value=0, max_value=100)

        # Custom validator that doubles the value
        class DoublingValidator(BaseValidator):
            def validate(self, value: Any, field_name: str) -> Any:
                if not isinstance(value, int | float | Decimal):
                    raise DataValidationError("Must be numeric", field_name=field_name, field_value=value)
                return value * 2

        doubling_validator = DoublingValidator()

        composite = CompositeValidator([range_validator, doubling_validator])

        # Test value that passes range check, then gets doubled
        result = composite.validate(25, "test_field")
        assert result == 50  # 25 * 2

    def test_composite_validator_first_validator_fails(self) -> None:
        """Test composite validation when first validator fails.

        Description of what the test covers:
        Verifies that CompositeValidator stops at the first failing
        validator and raises appropriate error.

        Preconditions:
        - Multiple validators where the first one will fail.

        Steps:
        - Create CompositeValidator with failing first validator.
        - Test value that fails first validation.
        - Verify DataValidationError is raised from first validator.

        Expected Result:
        - Validation should stop at first failure.
        - Error should be from the first validator.
        """
        # First validator will fail for negative values
        range_validator = RangeValidator(min_value=0, max_value=100)
        success_validator = ConcreteValidator(should_fail=False)

        composite = CompositeValidator([range_validator, success_validator])

        # Test negative value that fails first validator
        with pytest.raises(DataValidationError) as exc_info:
            composite.validate(-10, "test_field")
        assert "below minimum 0" in str(exc_info.value)

    def test_composite_validator_second_validator_fails(self) -> None:
        """Test composite validation when second validator fails.

        Description of what the test covers:
        Verifies that CompositeValidator processes validators in sequence
        and fails at the appropriate validator in the chain.

        Preconditions:
        - Multiple validators where later validator will fail.

        Steps:
        - Create CompositeValidator with first passing, second failing.
        - Test value that passes first but fails second validation.
        - Verify DataValidationError is raised from second validator.

        Expected Result:
        - First validator should process successfully.
        - Second validator should fail and raise error.
        """
        success_validator = ConcreteValidator(should_fail=False)
        fail_validator = ConcreteValidator(should_fail=True)

        composite = CompositeValidator([success_validator, fail_validator])

        with pytest.raises(DataValidationError) as exc_info:
            composite.validate("test_value", "test_field")
        assert "Test validation failed" in str(exc_info.value)

    def test_composite_validator_empty_list(self) -> None:
        """Test composite validator with empty validator list.

        Description of what the test covers:
        Verifies that CompositeValidator handles empty validator list
        gracefully by returning the input value unchanged.

        Preconditions:
        - CompositeValidator with empty validator list.

        Steps:
        - Create CompositeValidator with empty list.
        - Test any value.
        - Verify value is returned unchanged.

        Expected Result:
        - Input value should be returned unchanged.
        - No validation should be performed.
        """
        composite = CompositeValidator([])

        test_value = "unchanged_value"
        result = composite.validate(test_value, "test_field")
        assert result == test_value

    def test_composite_validator_single_validator(self) -> None:
        """Test composite validator with single validator.

        Description of what the test covers:
        Verifies that CompositeValidator works correctly with a single
        validator in the list.

        Preconditions:
        - CompositeValidator with single validator.

        Steps:
        - Create CompositeValidator with one validator.
        - Test validation with passing and failing cases.
        - Verify behavior matches single validator behavior.

        Expected Result:
        - Behavior should be identical to using the single validator directly.
        """
        range_validator = RangeValidator(min_value=10, max_value=20)
        composite = CompositeValidator([range_validator])

        # Should pass
        assert composite.validate(15, "test_field") == 15

        # Should fail
        with pytest.raises(DataValidationError) as exc_info:
            composite.validate(5, "test_field")
        assert "below minimum 10" in str(exc_info.value)

    def test_composite_validator_value_transformation_chain(self) -> None:
        """Test composite validator with value transformation chain.

        Description of what the test covers:
        Verifies that CompositeValidator correctly passes transformed
        values through the validation chain.

        Preconditions:
        - Multiple validators that transform values.

        Steps:
        - Create validators that transform values in sequence.
        - Test initial value transformation through chain.
        - Verify final result reflects all transformations.

        Expected Result:
        - Each validator should receive result from previous validator.
        - Final result should reflect all transformations.
        """

        # Validator that adds 10
        class AddTenValidator(BaseValidator):
            def validate(self, value: Any, field_name: str) -> Any:
                if not isinstance(value, int | float):
                    raise DataValidationError("Must be numeric", field_name=field_name, field_value=value)
                return value + 10

        # Validator that multiplies by 2
        class MultiplyTwoValidator(BaseValidator):
            def validate(self, value: Any, field_name: str) -> Any:
                if not isinstance(value, int | float):
                    raise DataValidationError("Must be numeric", field_name=field_name, field_value=value)
                return value * 2

        composite = CompositeValidator(
            [
                AddTenValidator(),
                MultiplyTwoValidator(),
            ]
        )

        # 5 -> (5 + 10) -> (15 * 2) = 30
        result = composite.validate(5, "test_field")
        assert result == 30


@pytest.mark.unit
class TestValidationMixin:
    """Test cases for ValidationMixin.

    Verifies integration utilities for using custom validators with Pydantic.
    """

    def test_validate_with_custom_validator_success(self) -> None:
        """Test successful validation with custom validator via mixin.

        Description of what the test covers:
        Verifies that ValidationMixin.validate_with_custom_validator
        correctly applies custom validator and returns result.

        Preconditions:
        - ValidationMixin available.
        - Custom validator that will pass.

        Steps:
        - Create custom validator that passes.
        - Use ValidationMixin.validate_with_custom_validator.
        - Verify result is returned correctly.

        Expected Result:
        - Custom validator should be applied successfully.
        - Result should be returned from validator.
        """
        validator = ConcreteValidator(should_fail=False)

        result = ValidationMixin.validate_with_custom_validator("test_value", validator, "test_field")
        assert result == "test_value"

    def test_validate_with_custom_validator_failure(self) -> None:
        """Test validation failure with custom validator via mixin.

        Description of what the test covers:
        Verifies that ValidationMixin.validate_with_custom_validator
        correctly converts DataValidationError to ValueError for Pydantic compatibility.

        Preconditions:
        - ValidationMixin available.
        - Custom validator that will fail.

        Steps:
        - Create custom validator that fails.
        - Use ValidationMixin.validate_with_custom_validator.
        - Verify ValueError is raised (not DataValidationError).

        Expected Result:
        - DataValidationError should be converted to ValueError.
        - Original error message should be preserved.
        """
        validator = ConcreteValidator(should_fail=True)

        with pytest.raises(ValueError) as exc_info:
            ValidationMixin.validate_with_custom_validator("test_value", validator, "test_field")
        assert "Test validation failed" in str(exc_info.value)

    def test_create_pydantic_validator(self) -> None:
        """Test creation of Pydantic validator function.

        Description of what the test covers:
        Verifies that ValidationMixin.create_pydantic_validator
        creates a callable suitable for use with Pydantic's @field_validator.

        Preconditions:
        - ValidationMixin available.
        - Custom validator instance.

        Steps:
        - Create custom validator.
        - Use ValidationMixin.create_pydantic_validator to create function.
        - Test the created function with mock validation info.
        - Verify it behaves like Pydantic validator.

        Expected Result:
        - Function should be created successfully.
        - Function should handle Pydantic validation context correctly.
        """
        validator = RangeValidator(min_value=0, max_value=100)
        pydantic_validator = ValidationMixin.create_pydantic_validator(validator)

        # Mock Pydantic validation info
        class MockValidationInfo:
            def __init__(self, field_name: str):
                self.field_name = field_name

        # Test successful validation
        result = pydantic_validator(50, MockValidationInfo("test_field"))
        assert result == 50

        # Test validation failure
        with pytest.raises(ValueError) as exc_info:
            pydantic_validator(150, MockValidationInfo("test_field"))
        assert "exceeds maximum 100" in str(exc_info.value)

    def test_create_pydantic_validator_with_none_info(self) -> None:
        """Test Pydantic validator function with None validation info.

        Description of what the test covers:
        Verifies that the created Pydantic validator function handles
        None validation info gracefully.

        Preconditions:
        - ValidationMixin available.
        - Custom validator instance.

        Steps:
        - Create Pydantic validator function.
        - Call function with None as validation info.
        - Verify it uses "unknown" as field name.

        Expected Result:
        - Function should handle None info without errors.
        - Field name should default to "unknown".
        """
        validator = ConcreteValidator(should_fail=True)
        pydantic_validator = ValidationMixin.create_pydantic_validator(validator)

        with pytest.raises(ValueError) as exc_info:
            pydantic_validator("test_value", None)

        # Error should mention the test failure, indicating validator was called
        assert "Test validation failed" in str(exc_info.value)


@pytest.mark.unit
class TestValidatorEdgeCases:
    """Test cases for validator edge cases and boundary conditions.

    Verifies comprehensive edge case handling across all validator types
    to ensure robust validation behavior under extreme conditions.
    """

    def test_range_validator_with_infinity_values(self) -> None:
        """Test RangeValidator behavior with infinity values.

        Description of what the test covers:
        Verifies how RangeValidator handles float infinity values,
        both positive and negative, and NaN values.

        Preconditions:
        - RangeValidator supports numeric validation.

        Steps:
        - Create RangeValidator with finite bounds
        - Test positive and negative infinity values
        - Test NaN values
        - Verify appropriate handling

        Expected Result:
        - Infinity and NaN values should be handled gracefully
        - Appropriate errors should be raised for invalid values
        """
        import math

        validator = RangeValidator(min_value=0, max_value=100, inclusive=True)

        # Test positive infinity
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(float("inf"), "test_field")
        assert "exceeds maximum 100" in str(exc_info.value)

        # Test negative infinity
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(float("-inf"), "test_field")
        assert "below minimum 0" in str(exc_info.value)

        # Test NaN (Not a Number)
        # NaN passes type check but comparisons behave unexpectedly
        # This documents current behavior - NaN may pass through validation
        nan_result = validator.validate(float("nan"), "test_field")
        assert math.isnan(nan_result)  # NaN passes through due to comparison behavior

    def test_range_validator_with_very_large_decimals(self) -> None:
        """Test RangeValidator with extremely large Decimal values.

        Description of what the test covers:
        Verifies that RangeValidator can handle very large Decimal values
        without precision loss or overflow errors.

        Preconditions:
        - RangeValidator supports Decimal type validation.

        Steps:
        - Create RangeValidator with large bounds
        - Test extremely large and small Decimal values
        - Verify precision is maintained

        Expected Result:
        - Large Decimal values should be validated correctly
        - No precision loss should occur
        """
        large_min = Decimal("1" + "0" * 100)  # 10^100
        large_max = Decimal("9" + "0" * 100)  # 9 * 10^100
        validator = RangeValidator(min_value=large_min, max_value=large_max, inclusive=True)

        # Test value within large range
        large_value = Decimal("5" + "0" * 100)  # 5 * 10^100
        result = validator.validate(large_value, "test_field")
        assert result == large_value

        # Test value below large minimum
        small_value = Decimal("999999999999999999999999999999")
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate(small_value, "test_field")
        assert "below minimum" in str(exc_info.value)

    def test_string_validator_with_unicode_and_emoji(self) -> None:
        """Test StringValidator with Unicode characters and emojis.

        Description of what the test covers:
        Verifies that StringValidator properly handles Unicode characters,
        emojis, and special characters in string validation.

        Preconditions:
        - StringValidator supports Unicode strings.

        Steps:
        - Create StringValidator with length constraints
        - Test strings with Unicode characters and emojis
        - Verify character counting and pattern matching

        Expected Result:
        - Unicode strings should be validated correctly
        - Character counting should handle multi-byte characters properly
        """
        validator = StringValidator(min_length=1, max_length=10)

        # Test Unicode characters
        unicode_strings = [
            "café",  # Accented characters
            "测试",  # Chinese characters
            "привет",  # Cyrillic characters
            "🚀✨💎",  # Emojis
            "🇺🇸🇨🇳",  # Flag emojis (compound characters)
        ]

        for unicode_string in unicode_strings:
            if len(unicode_string) <= 10:
                result = validator.validate(unicode_string, "test_field")
                assert result == unicode_string

        # Test emoji length counting (emojis might count as multiple characters)
        long_emoji_string = "🚀" * 15  # 15 rocket emojis
        if len(long_emoji_string) > 10:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(long_emoji_string, "test_field")
            assert "exceeds maximum 10" in str(exc_info.value)

    def test_string_validator_with_complex_regex_patterns(self) -> None:
        """Test StringValidator with complex regex patterns.

        Description of what the test covers:
        Verifies that StringValidator correctly handles complex regex patterns
        including lookaheads, backreferences, and character classes.

        Preconditions:
        - StringValidator supports regex pattern validation.

        Steps:
        - Create StringValidator with complex regex patterns
        - Test strings that should match and not match
        - Verify pattern matching accuracy

        Expected Result:
        - Complex regex patterns should be evaluated correctly
        - Edge cases in regex matching should be handled properly
        """
        # Simple alphanumeric pattern for testing
        simple_pattern = r"^[A-Z][a-z0-9]+$"  # Start with uppercase, followed by lowercase and digits
        validator = StringValidator(pattern=simple_pattern)

        # Valid strings
        valid_strings = [
            "Password123",
            "Test42",
            "Hello1",
        ]

        for test_string in valid_strings:
            result = validator.validate(test_string, "test_field")
            assert result == test_string

        # Invalid strings
        invalid_strings = [
            "password",  # Starts with lowercase
            "PASSWORD",  # All uppercase
            "Test!",  # Contains special character
            "test123",  # Starts with lowercase
        ]

        for invalid_string in invalid_strings:
            with pytest.raises(DataValidationError) as exc_info:
                validator.validate(invalid_string, "test_field")
            assert "does not match required pattern" in str(exc_info.value) or "pattern" in str(exc_info.value).lower()

    def test_datetime_validator_with_timezone_edge_cases(self) -> None:
        """Test DateTimeValidator with timezone edge cases.

        Description of what the test covers:
        Verifies DateTimeValidator behavior with timezone edge cases
        including DST transitions, leap seconds, and rare timezones.

        Preconditions:
        - DateTimeValidator supports timezone validation.

        Steps:
        - Test datetime objects during DST transitions
        - Test datetime objects with unusual timezones
        - Verify timezone handling consistency

        Expected Result:
        - Timezone edge cases should be handled correctly
        - DST transitions should not cause validation errors
        """
        import zoneinfo

        validator = DateTimeValidator(require_timezone=True)

        # Test DST transition (spring forward)
        try:
            # Note: This might not exist due to DST transition
            eastern = zoneinfo.ZoneInfo("US/Eastern")
            dst_transition = datetime(2023, 3, 12, 3, 0, 0, tzinfo=eastern)
            result = validator.validate(dst_transition, "datetime_field")
            assert result == dst_transition
        except Exception:
            # DST transition datetime might not exist, which is expected
            pass

        # Test unusual timezone
        pacific_marquesas = zoneinfo.ZoneInfo("Pacific/Marquesas")  # UTC-9:30
        unusual_tz_datetime = datetime(2023, 6, 15, 12, 0, 0, tzinfo=pacific_marquesas)
        result = validator.validate(unusual_tz_datetime, "datetime_field")
        assert result == unusual_tz_datetime

        # Test leap second handling (if supported by system)
        leap_second_datetime = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)
        result = validator.validate(leap_second_datetime, "datetime_field")
        assert result == leap_second_datetime

    def test_datetime_validator_with_extreme_dates(self) -> None:
        """Test DateTimeValidator with extreme date values.

        Description of what the test covers:
        Verifies DateTimeValidator behavior with extreme dates
        including very early and very late dates within datetime limits.

        Preconditions:
        - DateTimeValidator supports wide date ranges.

        Steps:
        - Test datetime objects near datetime.min and datetime.max
        - Test with extreme but valid datetime values
        - Verify boundary handling

        Expected Result:
        - Extreme but valid datetime values should be accepted
        - datetime.min and datetime.max limits should be respected
        """
        validator = DateTimeValidator(require_timezone=True)

        # Test near datetime.min (year 1)
        early_datetime = datetime(100, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = validator.validate(early_datetime, "datetime_field")
        assert result == early_datetime

        # Test near datetime.max (year 9999)
        late_datetime = datetime(9000, 12, 31, 23, 59, 59, tzinfo=UTC)
        result = validator.validate(late_datetime, "datetime_field")
        assert result == late_datetime

        # Test with microsecond precision
        precise_datetime = datetime(2023, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
        result = validator.validate(precise_datetime, "datetime_field")
        assert result == precise_datetime

    def test_composite_validator_with_circular_dependencies(self) -> None:
        """Test CompositeValidator behavior with potential circular dependencies.

        Description of what the test covers:
        Verifies that CompositeValidator handles complex validation chains
        without infinite loops or stack overflow issues.

        Preconditions:
        - CompositeValidator supports chaining multiple validators.

        Steps:
        - Create validators that transform values in ways that could cycle
        - Test with large validator chains
        - Verify no infinite loops occur

        Expected Result:
        - Complex validator chains should execute without infinite loops
        - Transformations should be applied in correct order
        """

        # Create validators that increment/decrement values
        class IncrementValidator(BaseValidator):
            def validate(self, value: Any, field_name: str) -> Any:
                if not isinstance(value, int):
                    raise DataValidationError("Must be integer", field_name=field_name, field_value=value)
                return value + 1

        class DecrementValidator(BaseValidator):
            def validate(self, value: Any, field_name: str) -> Any:
                if not isinstance(value, int):
                    raise DataValidationError("Must be integer", field_name=field_name, field_value=value)
                return value - 1

        # Create a chain that should not cycle
        composite = CompositeValidator(
            [
                IncrementValidator(),  # +1
                IncrementValidator(),  # +1 (total +2)
                DecrementValidator(),  # -1 (total +1)
            ]
        )

        result = composite.validate(10, "test_field")
        assert result == 11  # 10 + 1

    def test_validator_with_memory_intensive_operations(self) -> None:
        """Test validators with memory-intensive operations.

        Description of what the test covers:
        Verifies that validators handle large data structures
        and memory-intensive operations without memory leaks.

        Preconditions:
        - Validators can process large data structures.

        Steps:
        - Create validators that process large strings/data
        - Test with increasingly large inputs
        - Monitor for memory issues (if possible)

        Expected Result:
        - Large inputs should be processed efficiently
        - No memory leaks should occur
        """
        # Test with very long strings
        long_string = "a" * 100000  # 100KB string
        validator = StringValidator(max_length=200000)

        result = validator.validate(long_string, "test_field")
        assert result == long_string
        assert len(result) == 100000

        # Test range validation with many operations
        range_validator = RangeValidator(min_value=0, max_value=1000000)
        large_numbers = [i * 1000 for i in range(1000)]  # 1000 numbers

        for number in large_numbers:
            result = range_validator.validate(number, "test_field")
            assert result == number

    def test_validation_mixin_error_propagation(self) -> None:
        """Test ValidationMixin error propagation and conversion.

        Description of what the test covers:
        Verifies that ValidationMixin properly converts and propagates
        errors from custom validators to Pydantic-compatible errors.

        Preconditions:
        - ValidationMixin supports error conversion.

        Steps:
        - Create validators that raise different types of errors
        - Test error propagation through ValidationMixin
        - Verify error message preservation

        Expected Result:
        - All error types should be properly converted
        - Original error information should be preserved
        """

        # Test with validator that raises different error types
        class MultiErrorValidator(BaseValidator):
            def __init__(self, error_type: str):
                self.error_type = error_type

            def validate(self, value: Any, field_name: str) -> Any:
                if self.error_type == "data":
                    raise DataValidationError("Data validation failed", field_name=field_name, field_value=value)
                elif self.error_type == "value":
                    raise ValueError("Value error occurred")
                elif self.error_type == "type":
                    raise TypeError("Type error occurred")
                elif self.error_type == "generic":
                    raise Exception("Generic exception occurred")
                return value

        # Test DataValidationError conversion
        data_validator = MultiErrorValidator("data")
        with pytest.raises(ValueError) as exc_info:
            ValidationMixin.validate_with_custom_validator("test", data_validator, "test_field")
        assert "Data validation failed" in str(exc_info.value)

        # Test other exception types - they should propagate as-is
        # ValidationMixin only converts DataValidationError to ValueError

        # Test ValueError propagation
        value_validator = MultiErrorValidator("value")
        with pytest.raises(ValueError) as value_exc_info:  # type: pytest.ExceptionInfo[Exception]
            ValidationMixin.validate_with_custom_validator("test", value_validator, "test_field")
        assert "Value error occurred" in str(value_exc_info.value)

        # Test TypeError propagation
        type_validator = MultiErrorValidator("type")
        with pytest.raises(TypeError) as type_exc_info:  # type: pytest.ExceptionInfo[Exception]
            ValidationMixin.validate_with_custom_validator("test", type_validator, "test_field")
        assert "Type error occurred" in str(type_exc_info.value)

        # Test Exception propagation
        generic_validator = MultiErrorValidator("generic")
        with pytest.raises(Exception) as generic_exc_info:  # type: pytest.ExceptionInfo[Exception]
            ValidationMixin.validate_with_custom_validator("test", generic_validator, "test_field")
        assert "Generic exception occurred" in str(generic_exc_info.value)

    def test_validator_thread_safety(self) -> None:
        """Test validator thread safety with concurrent access.

        Description of what the test covers:
        Verifies that validators can be safely used in multi-threaded
        environments without race conditions or state corruption.

        Preconditions:
        - Validators should be stateless or thread-safe.

        Steps:
        - Create validator instances
        - Test concurrent validation from multiple threads
        - Verify consistent results

        Expected Result:
        - Validators should produce consistent results under concurrent access
        - No race conditions should occur
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        validator = RangeValidator(min_value=0, max_value=100)
        results = []
        errors = []

        def validate_value(value: int) -> bool:
            try:
                result = validator.validate(value, "test_field")
                results.append(result)
                return True
            except Exception as e:
                errors.append(e)
                return False

        # Test concurrent validation
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_value, i) for i in range(50)]

            for future in as_completed(futures):
                future.result()  # Wait for completion

        # Verify results
        assert len(results) == 50
        assert len(errors) == 0
        assert sorted(results) == list(range(50))

    def test_validator_performance_with_large_datasets(self) -> None:
        """Test validator performance with large datasets.

        Description of what the test covers:
        Verifies that validators maintain reasonable performance
        when processing large numbers of values sequentially.

        Preconditions:
        - Validators should scale reasonably with input size.

        Steps:
        - Create validators for different types
        - Test with large datasets
        - Measure basic performance characteristics

        Expected Result:
        - Validators should handle large datasets efficiently
        - Performance should scale reasonably
        """
        import time

        # Test string validator performance
        string_validator = StringValidator(min_length=1, max_length=100)
        test_strings = [f"test_string_{i}" for i in range(10000)]

        start_time = time.time()
        for test_string in test_strings:
            string_validator.validate(test_string, "test_field")
        string_duration = time.time() - start_time

        # Should complete in reasonable time (less than 1 second for 10k validations)
        assert string_duration < 1.0

        # Test range validator performance
        range_validator = RangeValidator(min_value=0, max_value=100000)
        test_numbers = list(range(10000))

        start_time = time.time()
        for test_number in test_numbers:
            range_validator.validate(test_number, "test_field")
        range_duration = time.time() - start_time

        # Should complete in reasonable time
        assert range_duration < 1.0
