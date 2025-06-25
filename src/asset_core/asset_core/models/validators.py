"""Custom validator base classes and utilities."""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel

from ..exceptions import DataValidationError

T = TypeVar("T", bound=BaseModel)


class BaseValidator(ABC):
    """Abstract base class for all custom validators."""

    @abstractmethod
    def validate(self, value: Any, field_name: str) -> Any:
        """Validate a value and return the validated value or raise an error.

        Args:
            value: The value to validate
            field_name: The name of the field being validated

        Returns:
            The validated value

        Raises:
            DataValidationError: If validation fails
        """
        pass


class RangeValidator(BaseValidator):
    """Validator for numeric ranges."""

    def __init__(
        self,
        min_value: int | float | Decimal | None = None,
        max_value: int | float | Decimal | None = None,
        inclusive: bool = True,
    ) -> None:
        """Initialize range validator.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            inclusive: Whether the range is inclusive of the bounds
        """
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive

    def validate(self, value: Any, field_name: str) -> Any:
        """Validate that value is within the specified range."""
        if not isinstance(value, int | float | Decimal):
            raise DataValidationError(
                f"Value must be numeric, got {type(value).__name__}",
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
    """Validator for string values."""

    regex: re.Pattern[str] | None

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        allowed_values: list[str] | None = None,
        case_sensitive: bool = True,
    ) -> None:
        """Initialize string validator.

        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern the string must match
            allowed_values: List of allowed string values
            case_sensitive: Whether string comparison is case sensitive
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
        """Validate string value."""
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
    """Validator for datetime values."""

    def __init__(
        self,
        min_datetime: datetime | None = None,
        max_datetime: datetime | None = None,
        require_timezone: bool = True,
        future_allowed: bool = True,
        past_allowed: bool = True,
    ) -> None:
        """Initialize datetime validator.

        Args:
            min_datetime: Minimum allowed datetime
            max_datetime: Maximum allowed datetime
            require_timezone: Whether timezone info is required
            future_allowed: Whether future dates are allowed
            past_allowed: Whether past dates are allowed
        """
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime
        self.require_timezone = require_timezone
        self.future_allowed = future_allowed
        self.past_allowed = past_allowed

    def validate(self, value: Any, field_name: str) -> Any:
        """Validate datetime value."""
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
    """Validator that combines multiple validators."""

    def __init__(self, validators: list[BaseValidator]) -> None:
        """Initialize composite validator.

        Args:
            validators: List of validators to apply in order
        """
        self.validators = validators

    def validate(self, value: Any, field_name: str) -> Any:
        """Apply all validators in sequence."""
        result = value
        for validator in self.validators:
            result = validator.validate(result, field_name)
        return result


class ValidationMixin:
    """Mixin class to add validation utilities to Pydantic models."""

    @classmethod
    def validate_with_custom_validator(
        cls,
        value: Any,
        validator: BaseValidator,
        field_name: str,
    ) -> Any:
        """Validate a value using a custom validator.

        Args:
            value: The value to validate
            validator: The validator to use
            field_name: The name of the field being validated

        Returns:
            The validated value

        Raises:
            ValueError: If validation fails (for Pydantic compatibility)
        """
        try:
            return validator.validate(value, field_name)
        except DataValidationError as e:
            # Convert to ValueError for Pydantic compatibility
            raise ValueError(str(e)) from e

    @classmethod
    def create_pydantic_validator(cls, validator: BaseValidator) -> Any:
        """Create a Pydantic field validator from a custom validator.

        Args:
            validator: The custom validator to wrap

        Returns:
            A function that can be used as a Pydantic field validator
        """

        def pydantic_validator(value: Any, info: Any) -> Any:
            field_name = info.field_name if info else "unknown"
            return cls.validate_with_custom_validator(value, validator, field_name)

        return pydantic_validator
