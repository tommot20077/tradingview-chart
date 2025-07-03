"""Custom validator base classes and utilities.

This module provides a framework for creating reusable and composable data
validators. It defines abstract base classes for validators and concrete
implementations for common validation scenarios like range checks, string
constraints, and datetime validation. It also includes a mixin for integrating
these custom validators with Pydantic models.
"""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel

from asset_core.exceptions import DataValidationError

T = TypeVar("T", bound=BaseModel)


class BaseValidator(ABC):
    """Abstract base class for all custom validators.

    All concrete validator implementations should inherit from this class
    and implement the `validate` method.
    """

    @abstractmethod
    def validate(self, value: Any, field_name: str) -> Any:
        """Validates a given value and returns the validated result.

        This method should be implemented by concrete validator classes to
        perform specific validation logic. If validation fails, it should
        raise a `DataValidationError`.

        Args:
            value: The value to be validated.
            field_name: The name of the field being validated, used for error reporting.

        Returns:
            The validated value, potentially transformed (e.g., stripped string).

        Raises:
            DataValidationError: If the value does not pass validation.
        """
        pass


class RangeValidator(BaseValidator):
    """A validator for checking if a numeric value falls within a specified range.

    The range can be inclusive or exclusive of its bounds.
    """

    def __init__(
        self,
        min_value: int | float | Decimal | None = None,
        max_value: int | float | Decimal | None = None,
        inclusive: bool = True,
    ) -> None:
        """Initializes the RangeValidator.

        Args:
            min_value: The minimum allowed value. If `None`, no minimum check is performed.
            max_value: The maximum allowed value. If `None`, no maximum check is performed.
            inclusive: If `True`, the range includes `min_value` and `max_value`. If `False`,
                       the range excludes them. Defaults to `True`.
        """
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive

    def validate(self, value: Any, field_name: str) -> Any:
        """Validates that the given value is numeric and falls within the specified range.

        Args:
            value: The numeric value to validate.
            field_name: The name of the field being validated.

        Returns:
            The validated numeric value.

        Raises:
            DataValidationError: If the value is not numeric or is outside the defined range.
        """
        if not isinstance(value, int | float | Decimal):
            raise DataValidationError(
                f"Value must be numeric, got {type(value).__name__}",
                field_name=field_name,
                field_value=value,
            )

        # Check for NaN values
        import math

        if isinstance(value, float) and math.isnan(value):
            raise DataValidationError(
                "NaN values are not allowed",
                field_name=field_name,
                field_value=value,
            )

        if self.min_value is not None:
            if self.inclusive and value < self.min_value:
                raise DataValidationError(
                    f"Value {value} is below minimum {self.min_value}",
                    field_name=field_name,
                    field_value=value,
                )
            elif not self.inclusive and value <= self.min_value:
                raise DataValidationError(
                    f"Value {value} must be greater than {self.min_value}",
                    field_name=field_name,
                    field_value=value,
                )

        if self.max_value is not None:
            if self.inclusive and value > self.max_value:
                raise DataValidationError(
                    f"Value {value} exceeds maximum {self.max_value}",
                    field_name=field_name,
                    field_value=value,
                )
            elif not self.inclusive and value >= self.max_value:
                raise DataValidationError(
                    f"Value {value} must be less than {self.max_value}",
                    field_name=field_name,
                    field_value=value,
                )

        return value


class StringValidator(BaseValidator):
    """A validator for string values, supporting length, regex pattern, and allowed values checks.

    It can enforce minimum and maximum lengths, validate against a regular
    expression, and restrict values to a predefined list, with optional case sensitivity.
    """

    regex: re.Pattern[str] | None

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        allowed_values: list[str] | None = None,
        case_sensitive: bool = True,
    ) -> None:
        """Initializes the StringValidator.

        Args:
            min_length: The minimum allowed length for the string. If `None`, no minimum length check.
            max_length: The maximum allowed length for the string. If `None`, no maximum length check.
            pattern: A regular expression string that the value must match. If `None`, no pattern check.
            allowed_values: A list of strings; the value must be one of these. If `None`, no allowed values check.
            case_sensitive: If `True`, string comparisons (for `allowed_values`) are case-sensitive.
                            Defaults to `True`.
        """
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.allowed_values = allowed_values
        self.case_sensitive = case_sensitive

        if pattern:
            import re

            self.regex = re.compile(pattern)
        else:
            self.regex = None

    def validate(self, value: Any, field_name: str) -> Any:
        """Validates the given value as a string based on configured rules.

        Args:
            value: The string value to validate.
            field_name: The name of the field being validated.

        Returns:
            The validated string value.

        Raises:
            DataValidationError: If the value is not a string or fails any of the configured checks.
        """
        if not isinstance(value, str):
            raise DataValidationError(
                f"Value must be a string, got {type(value).__name__}",
                field_name=field_name,
                field_value=value,
            )

        # Length validation
        if self.min_length is not None and len(value) < self.min_length:
            raise DataValidationError(
                f"String length {len(value)} is below minimum {self.min_length}",
                field_name=field_name,
                field_value=value,
            )

        if self.max_length is not None and len(value) > self.max_length:
            raise DataValidationError(
                f"String length {len(value)} exceeds maximum {self.max_length}",
                field_name=field_name,
                field_value=value,
            )

        # Pattern validation
        if self.regex and not self.regex.match(value):
            raise DataValidationError(
                f"String '{value}' does not match required pattern '{self.pattern}'",
                field_name=field_name,
                field_value=value,
            )

        # Allowed values validation
        if self.allowed_values is not None:
            comparison_value = value if self.case_sensitive else value.lower()
            allowed_comparison = (
                self.allowed_values if self.case_sensitive else [v.lower() for v in self.allowed_values]
            )

            if comparison_value not in allowed_comparison:
                raise DataValidationError(
                    f"Value '{value}' is not in allowed values: {self.allowed_values}",
                    field_name=field_name,
                    field_value=value,
                )

        return value


class DateTimeValidator(BaseValidator):
    """A validator for `datetime` objects, supporting range, timezone, and future/past checks.

    It can enforce minimum and maximum datetime values, require timezone
    information, and restrict dates to be in the past or future.
    """

    def __init__(
        self,
        min_datetime: datetime | None = None,
        max_datetime: datetime | None = None,
        require_timezone: bool = True,
        future_allowed: bool = True,
        past_allowed: bool = True,
    ) -> None:
        """Initializes the DateTimeValidator.

        Args:
            min_datetime: The minimum allowed datetime. If `None`, no minimum check.
            max_datetime: The maximum allowed datetime. If `None`, no maximum check.
            require_timezone: If `True`, the datetime must be timezone-aware. Defaults to `True`.
            future_allowed: If `True`, future datetimes are allowed. Defaults to `True`.
            past_allowed: If `True`, past datetimes are allowed. Defaults to `True`.
        """
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime
        self.require_timezone = require_timezone
        self.future_allowed = future_allowed
        self.past_allowed = past_allowed

    def validate(self, value: Any, field_name: str) -> Any:
        """Validates the given value as a datetime object based on configured rules.

        Args:
            value: The datetime object to validate.
            field_name: The name of the field being validated.

        Returns:
            The validated datetime object.

        Raises:
            DataValidationError: If the value is not a datetime or fails any of the configured checks.
        """
        if not isinstance(value, datetime):
            raise DataValidationError(
                f"Value must be a datetime, got {type(value).__name__}",
                field_name=field_name,
                field_value=value,
            )

        # Timezone validation
        if self.require_timezone and value.tzinfo is None:
            raise DataValidationError(
                "Datetime must include timezone information",
                field_name=field_name,
                field_value=value,
            )

        # Future/past validation
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()

        if not self.future_allowed and value > now:
            raise DataValidationError(
                f"Future datetime {value} is not allowed",
                field_name=field_name,
                field_value=value,
            )

        if not self.past_allowed and value < now:
            raise DataValidationError(
                f"Past datetime {value} is not allowed",
                field_name=field_name,
                field_value=value,
            )

        # Range validation
        if self.min_datetime and value < self.min_datetime:
            raise DataValidationError(
                f"Datetime {value} is before minimum {self.min_datetime}",
                field_name=field_name,
                field_value=value,
            )

        if self.max_datetime and value > self.max_datetime:
            raise DataValidationError(
                f"Datetime {value} is after maximum {self.max_datetime}",
                field_name=field_name,
                field_value=value,
            )

        return value


class CompositeValidator(BaseValidator):
    """A validator that combines multiple `BaseValidator` instances.

    It applies a sequence of validators to a value, passing the result of one
    validator as the input to the next. This allows for building complex
    validation pipelines.
    """

    def __init__(self, validators: list[BaseValidator]) -> None:
        """Initializes the CompositeValidator.

        Args:
            validators: A list of `BaseValidator` instances to apply in sequence.
        """
        self.validators = validators

    def validate(self, value: Any, field_name: str) -> Any:
        """Applies all contained validators to the given value in sequence.

        Args:
            value: The value to validate.
            field_name: The name of the field being validated.

        Returns:
            The final validated value after all validators have been applied.

        Raises:
            DataValidationError: If any of the validators in the sequence fail.
        """
        result = value
        for validator in self.validators:
            result = validator.validate(result, field_name)
        return result


class ValidationMixin:
    """A mixin class providing utility methods for integrating custom validators with Pydantic models.

    This mixin simplifies the process of using `BaseValidator` instances within
    Pydantic's validation system, allowing custom validation logic to be applied
    to model fields.
    """

    @classmethod
    def validate_with_custom_validator(
        cls,
        value: Any,
        validator: BaseValidator,
        field_name: str,
    ) -> Any:
        """Validates a value using a provided custom `BaseValidator` instance.

        This method wraps the custom validator's logic and converts any
        `DataValidationError` into a `ValueError` to maintain compatibility
        with Pydantic's expected exception types.

        Args:
            value: The value to be validated.
            validator: An instance of a `BaseValidator` to apply.
            field_name: The name of the field being validated.

        Returns:
            The validated value.

        Raises:
            ValueError: If the custom validator raises a `DataValidationError`.
        """
        try:
            return validator.validate(value, field_name)
        except DataValidationError as e:
            # Convert to ValueError for Pydantic compatibility
            raise ValueError(str(e)) from e

    @classmethod
    def create_pydantic_validator(cls, validator: BaseValidator) -> Any:
        """Creates a Pydantic field validator function from a custom `BaseValidator`.

        This factory method generates a callable that can be used with Pydantic's
        `@field_validator` decorator, allowing custom validation logic to be
        seamlessly integrated into Pydantic models.

        Args:
            validator: An instance of a `BaseValidator` to wrap.

        Returns:
            A callable that takes `value` and `info` (Pydantic's validation context)
            and returns the validated value, suitable for Pydantic's validation system.
        """

        def pydantic_validator(value: Any, info: Any) -> Any:
            field_name = info.field_name if info else "unknown"
            return cls.validate_with_custom_validator(value, validator, field_name)

        return pydantic_validator
