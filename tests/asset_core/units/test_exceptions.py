"""Unit tests for exception system."""

from datetime import UTC, datetime, timedelta

import pytest

from asset_core.exceptions import (
    AuthenticationError,
    CircuitBreakerError,
    ConfigurationError,
    ConnectionError,
    CoreError,
    DataProviderError,
    DataValidationError,
    EventBusError,
    NetworkError,
    RateLimitError,
    ResourceExhaustedError,
    StorageConnectionError,
    StorageError,
    StorageReadError,
    StorageWriteError,
    TimeoutError,
    ValidationError,
    WebSocketError,
)


@pytest.mark.unit
class TestCoreError:
    """Test cases for CoreError base exception."""

    def test_core_error_basic_creation(self) -> None:
        """Test creating CoreError with basic message."""
        error = CoreError("Something went wrong")

        assert error.message == "Something went wrong"
        assert error.error_code == "CoreError"
        assert error.details == {"trace_id": "no-trace"}
        assert str(error) == "Something went wrong"

    def test_core_error_with_error_code(self) -> None:
        """Test creating CoreError with custom error code."""
        error = CoreError("Something went wrong", error_code="CUSTOM_ERROR")

        assert error.message == "Something went wrong"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == {"trace_id": "no-trace"}
        assert str(error) == "[CUSTOM_ERROR] Something went wrong"

    def test_core_error_with_details(self) -> None:
        """Test creating CoreError with details."""
        details = {"field": "price", "value": "invalid"}
        error = CoreError("Validation failed", details=details)

        assert error.message == "Validation failed"
        assert error.error_code == "CoreError"
        assert error.details == details
        assert str(error) == "Validation failed Details: {'field': 'price', 'value': 'invalid'}"

    def test_core_error_with_all_parameters(self) -> None:
        """Test creating CoreError with all parameters."""
        details = {"context": "test"}
        error = CoreError("Operation failed", error_code="TEST_ERROR", details=details)

        assert error.message == "Operation failed"
        assert error.error_code == "TEST_ERROR"
        assert error.details == details
        assert str(error) == "[TEST_ERROR] Operation failed Details: {'context': 'test'}"

    def test_core_error_inheritance_from_exception(self) -> None:
        """Test CoreError properly inherits from Exception."""
        error = CoreError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, CoreError)

    def test_core_error_can_be_raised(self) -> None:
        """Test CoreError can be raised and caught."""
        with pytest.raises(CoreError) as exc_info:
            raise CoreError("Test error", error_code="TEST")

        assert exc_info.value.message == "Test error"
        assert exc_info.value.error_code == "TEST"

    def test_core_error_default_details(self) -> None:
        """Test CoreError with None details defaults to empty dict."""
        error = CoreError("Test", details=None)
        assert error.details == {"trace_id": "no-trace"}

    def test_core_error_default_error_code(self) -> None:
        """Test CoreError with None error_code defaults to class name."""
        error = CoreError("Test", error_code=None)
        assert error.error_code == "CoreError"


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test cases for exception inheritance hierarchy."""

    def test_configuration_error_inheritance(self) -> None:
        """Test ConfigurationError inheritance."""
        error = ConfigurationError("Config error")

        assert isinstance(error, CoreError)
        assert isinstance(error, ConfigurationError)
        assert error.error_code == "ConfigurationError"

    def test_data_provider_error_inheritance(self) -> None:
        """Test DataProviderError inheritance."""
        error = DataProviderError("Provider error")

        assert isinstance(error, CoreError)
        assert isinstance(error, DataProviderError)
        assert error.error_code == "DataProviderError"

    def test_connection_error_inheritance(self) -> None:
        """Test ConnectionError inheritance."""
        error = ConnectionError("Connection failed")

        assert isinstance(error, CoreError)
        assert isinstance(error, DataProviderError)
        assert isinstance(error, ConnectionError)
        assert error.error_code == "ConnectionError"

    def test_authentication_error_inheritance(self) -> None:
        """Test AuthenticationError inheritance."""
        error = AuthenticationError("Auth failed")

        assert isinstance(error, CoreError)
        assert isinstance(error, DataProviderError)
        assert isinstance(error, AuthenticationError)
        assert error.error_code == "AuthenticationError"

    def test_storage_error_inheritance(self) -> None:
        """Test StorageError inheritance."""
        error = StorageError("Storage error")

        assert isinstance(error, CoreError)
        assert isinstance(error, StorageError)
        assert error.error_code == "StorageError"

    def test_storage_connection_error_inheritance(self) -> None:
        """Test StorageConnectionError inheritance."""
        error = StorageConnectionError("DB connection failed")

        assert isinstance(error, CoreError)
        assert isinstance(error, StorageError)
        assert isinstance(error, StorageConnectionError)
        assert error.error_code == "StorageConnectionError"

    def test_network_error_inheritance(self) -> None:
        """Test NetworkError inheritance."""
        error = NetworkError("Network error")

        assert isinstance(error, CoreError)
        assert isinstance(error, NetworkError)
        assert error.error_code == "NetworkError"

    def test_websocket_error_inheritance(self) -> None:
        """Test WebSocketError inheritance."""
        error = WebSocketError("WebSocket error")

        assert isinstance(error, CoreError)
        assert isinstance(error, NetworkError)
        assert isinstance(error, WebSocketError)
        assert error.error_code == "WebSocketError"

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inheritance."""
        error = ValidationError("Validation error")

        assert isinstance(error, CoreError)
        assert isinstance(error, ValidationError)
        assert error.error_code == "ValidationError"


@pytest.mark.unit
class TestRateLimitError:
    """Test cases for RateLimitError."""

    def test_rate_limit_error_basic(self) -> None:
        """Test basic RateLimitError creation."""
        error = RateLimitError("Rate limit exceeded")

        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RateLimitError"
        assert error.retry_after is None
        assert "retry_after" not in error.details

    def test_rate_limit_error_with_retry_after(self) -> None:
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        assert error.message == "Rate limit exceeded"
        assert error.retry_after == 60
        assert error.details["retry_after"] == 60

    def test_rate_limit_error_with_all_parameters(self) -> None:
        """Test RateLimitError with all parameters."""
        error = RateLimitError(
            "Rate limit exceeded", retry_after=120, error_code="API_RATE_LIMIT", details={"endpoint": "/api/trades"}
        )

        assert error.message == "Rate limit exceeded"
        assert error.retry_after == 120
        assert error.error_code == "API_RATE_LIMIT"
        assert error.details["retry_after"] == 120
        assert error.details["endpoint"] == "/api/trades"

    def test_rate_limit_error_inheritance(self) -> None:
        """Test RateLimitError inheritance."""
        error = RateLimitError("Rate limit exceeded")

        assert isinstance(error, CoreError)
        assert isinstance(error, DataProviderError)
        assert isinstance(error, RateLimitError)


@pytest.mark.unit
class TestDataValidationError:
    """Test cases for DataValidationError."""

    def test_data_validation_error_basic(self) -> None:
        """Test basic DataValidationError creation."""
        error = DataValidationError("Invalid price")

        assert error.message == "Invalid price"
        assert error.error_code == "DataValidationError"
        assert error.field_name is None
        assert error.field_value is None
        assert "field_name" not in error.details
        assert "field_value" not in error.details

    def test_data_validation_error_with_field_name(self) -> None:
        """Test DataValidationError with field name."""
        error = DataValidationError("Invalid value", field_name="price")

        assert error.field_name == "price"
        assert error.details["field_name"] == "price"

    def test_data_validation_error_with_field_value(self) -> None:
        """Test DataValidationError with field value."""
        error = DataValidationError("Invalid value", field_value=-100)

        assert error.field_value == -100
        assert error.details["field_value"] == "-100"

    def test_data_validation_error_with_all_parameters(self) -> None:
        """Test DataValidationError with all parameters."""
        error = DataValidationError(
            "Price cannot be negative",
            field_name="price",
            field_value=-50.5,
            error_code="NEGATIVE_PRICE",
            details={"symbol": "BTCUSDT"},
        )

        assert error.message == "Price cannot be negative"
        assert error.field_name == "price"
        assert error.field_value == -50.5
        assert error.error_code == "NEGATIVE_PRICE"
        assert error.details["field_name"] == "price"
        assert error.details["field_value"] == "-50.5"
        assert error.details["symbol"] == "BTCUSDT"

    def test_data_validation_error_field_value_none(self) -> None:
        """Test DataValidationError with None field_value."""
        error = DataValidationError("Required field", field_value=None)

        assert error.field_value is None
        assert "field_value" not in error.details

    def test_data_validation_error_inheritance(self) -> None:
        """Test DataValidationError inheritance."""
        error = DataValidationError("Validation failed")

        assert isinstance(error, CoreError)
        assert isinstance(error, ValidationError)
        assert isinstance(error, DataValidationError)


@pytest.mark.unit
class TestResourceExhaustedError:
    """Test cases for ResourceExhaustedError."""

    def test_resource_exhausted_error_basic(self) -> None:
        """Test basic ResourceExhaustedError creation."""
        error = ResourceExhaustedError("Resource exhausted")

        assert error.message == "Resource exhausted"
        assert error.error_code == "ResourceExhaustedError"
        assert error.resource_type is None
        assert error.current_usage is None
        assert error.limit is None

    def test_resource_exhausted_error_with_resource_type(self) -> None:
        """Test ResourceExhaustedError with resource type."""
        error = ResourceExhaustedError("Memory exhausted", resource_type="memory")

        assert error.resource_type == "memory"
        assert error.details["resource_type"] == "memory"

    def test_resource_exhausted_error_with_usage_and_limit(self) -> None:
        """Test ResourceExhaustedError with usage and limit."""
        error = ResourceExhaustedError(
            "Connection pool exhausted", resource_type="connections", current_usage=95.5, limit=100.0
        )

        assert error.resource_type == "connections"
        assert error.current_usage == 95.5
        assert error.limit == 100.0
        assert error.details["resource_type"] == "connections"
        assert error.details["current_usage"] == 95.5
        assert error.details["limit"] == 100.0

    def test_resource_exhausted_error_with_all_parameters(self) -> None:
        """Test ResourceExhaustedError with all parameters."""
        error = ResourceExhaustedError(
            "CPU limit exceeded",
            resource_type="cpu",
            current_usage=90.0,
            limit=80.0,
            error_code="CPU_LIMIT_EXCEEDED",
            details={"process_id": 12345},
        )

        assert error.message == "CPU limit exceeded"
        assert error.resource_type == "cpu"
        assert error.current_usage == 90.0
        assert error.limit == 80.0
        assert error.error_code == "CPU_LIMIT_EXCEEDED"
        assert error.details["process_id"] == 12345

    def test_resource_exhausted_error_none_values(self) -> None:
        """Test ResourceExhaustedError with None values."""
        error = ResourceExhaustedError("Resource exhausted", resource_type=None, current_usage=None, limit=None)

        assert error.resource_type is None
        assert error.current_usage is None
        assert error.limit is None
        assert "resource_type" not in error.details
        assert "current_usage" not in error.details
        assert "limit" not in error.details


@pytest.mark.unit
class TestCircuitBreakerError:
    """Test cases for CircuitBreakerError."""

    def test_circuit_breaker_error_basic(self) -> None:
        """Test basic CircuitBreakerError creation."""
        error = CircuitBreakerError("Circuit breaker open")

        assert error.message == "Circuit breaker open"
        assert error.error_code == "CircuitBreakerError"
        assert error.service_name is None
        assert error.failure_count is None
        assert error.failure_threshold is None
        assert error.next_retry_time is None

    def test_circuit_breaker_error_with_service_name(self) -> None:
        """Test CircuitBreakerError with service name."""
        error = CircuitBreakerError("Circuit breaker open", service_name="binance_api")

        assert error.service_name == "binance_api"
        assert error.details["service_name"] == "binance_api"

    def test_circuit_breaker_error_with_failure_info(self) -> None:
        """Test CircuitBreakerError with failure information."""
        error = CircuitBreakerError(
            "Circuit breaker open", service_name="exchange_api", failure_count=5, failure_threshold=3
        )

        assert error.failure_count == 5
        assert error.failure_threshold == 3
        assert error.details["failure_count"] == 5
        assert error.details["failure_threshold"] == 3

    def test_circuit_breaker_error_with_retry_time(self) -> None:
        """Test CircuitBreakerError with next retry time."""
        retry_time = datetime.now(UTC) + timedelta(minutes=5)
        error = CircuitBreakerError("Circuit breaker open", next_retry_time=retry_time)

        assert error.next_retry_time == retry_time
        assert error.details["next_retry_time"] == retry_time.isoformat()

    def test_circuit_breaker_error_with_all_parameters(self) -> None:
        """Test CircuitBreakerError with all parameters."""
        retry_time = datetime(2023, 1, 1, 12, 30, 0, tzinfo=UTC)
        error = CircuitBreakerError(
            "Service temporarily unavailable",
            service_name="trading_api",
            failure_count=10,
            failure_threshold=5,
            next_retry_time=retry_time,
            error_code="CIRCUIT_BREAKER_OPEN",
            details={"endpoint": "/api/orders"},
        )

        assert error.message == "Service temporarily unavailable"
        assert error.service_name == "trading_api"
        assert error.failure_count == 10
        assert error.failure_threshold == 5
        assert error.next_retry_time == retry_time
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
        assert error.details["service_name"] == "trading_api"
        assert error.details["failure_count"] == 10
        assert error.details["failure_threshold"] == 5
        assert error.details["next_retry_time"] == retry_time.isoformat()
        assert error.details["endpoint"] == "/api/orders"

    def test_circuit_breaker_error_none_values(self) -> None:
        """Test CircuitBreakerError with None values."""
        error = CircuitBreakerError(
            "Circuit breaker open", service_name=None, failure_count=None, failure_threshold=None, next_retry_time=None
        )

        assert error.service_name is None
        assert error.failure_count is None
        assert error.failure_threshold is None
        assert error.next_retry_time is None
        assert "service_name" not in error.details
        assert "failure_count" not in error.details
        assert "failure_threshold" not in error.details
        assert "next_retry_time" not in error.details


@pytest.mark.unit
class TestExceptionStringRepresentation:
    """Test cases for exception string representation."""

    def test_core_error_string_without_code_and_details(self) -> None:
        """Test CoreError string representation without custom code and details."""
        error = CoreError("Simple error")
        assert str(error) == "Simple error"

    def test_core_error_string_with_custom_code(self) -> None:
        """Test CoreError string representation with custom code."""
        error = CoreError("Error with code", error_code="CUSTOM_CODE")
        assert str(error) == "[CUSTOM_CODE] Error with code"

    def test_core_error_string_with_details(self) -> None:
        """Test CoreError string representation with details."""
        error = CoreError("Error with details", details={"key": "value"})
        assert str(error) == "Error with details Details: {'key': 'value'}"

    def test_core_error_string_with_code_and_details(self) -> None:
        """Test CoreError string representation with code and details."""
        error = CoreError("Complex error", error_code="COMPLEX_ERROR", details={"field": "price", "value": 100})
        expected = "[COMPLEX_ERROR] Complex error Details: {'field': 'price', 'value': 100}"
        assert str(error) == expected

    def test_derived_exception_string_representation(self) -> None:
        """Test derived exception string representation."""
        error = ConfigurationError("Config error", details={"config_file": "app.yaml"})
        expected = "Config error Details: {'config_file': 'app.yaml'}"
        assert str(error) == expected

    def test_rate_limit_error_string_representation(self) -> None:
        """Test RateLimitError string representation."""
        error = RateLimitError("Rate limited", retry_after=60)
        expected = "Rate limited Details: {'retry_after': 60}"
        assert str(error) == expected


@pytest.mark.unit
class TestExceptionCatchingAndHandling:
    """Test cases for exception catching and handling."""

    def test_catch_base_exception(self) -> None:
        """Test catching exceptions using base CoreError."""
        with pytest.raises(CoreError) as exc_info:
            raise ConfigurationError("Config error")

        assert isinstance(exc_info.value, ConfigurationError)
        assert exc_info.value.message == "Config error"

    def test_catch_specific_exception(self) -> None:
        """Test catching specific exception types."""
        with pytest.raises(DataProviderError) as exc_info:
            raise AuthenticationError("Auth failed")

        assert isinstance(exc_info.value, AuthenticationError)
        assert exc_info.value.message == "Auth failed"

    def test_exception_hierarchy_catching(self) -> None:
        """Test catching exceptions at different hierarchy levels."""
        # ConnectionError should be catchable as DataProviderError
        with pytest.raises(DataProviderError):
            raise ConnectionError("Connection failed")

        # WebSocketError should be catchable as NetworkError
        with pytest.raises(NetworkError):
            raise WebSocketError("WebSocket failed")

        # All should be catchable as CoreError
        with pytest.raises(CoreError):
            raise StorageWriteError("Write failed")

    def test_multiple_exception_types(self) -> None:
        """Test handling multiple exception types."""

        def raise_various_errors(error_type: str) -> None:
            if error_type == "config":
                raise ConfigurationError("Config error")
            elif error_type == "network":
                raise NetworkError("Network error")
            elif error_type == "storage":
                raise StorageError("Storage error")
            else:
                raise CoreError("Unknown error")

        # Test catching different exception types
        with pytest.raises(ConfigurationError):
            raise_various_errors("config")

        with pytest.raises(NetworkError):
            raise_various_errors("network")

        with pytest.raises(StorageError):
            raise_various_errors("storage")

        with pytest.raises(CoreError):
            raise_various_errors("other")


@pytest.mark.unit
class TestExceptionDetails:
    """Test cases for exception details handling."""

    def test_details_modification_after_creation(self) -> None:
        """Test that details can be modified after creation."""
        error = CoreError("Test error", details={"initial": "value"})

        # Modifying details should work (dict is mutable)
        error.details["new_key"] = "new_value"
        assert error.details["new_key"] == "new_value"

    def test_details_with_complex_data(self) -> None:
        """Test details with complex data structures."""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
            "boolean": True,
            "none_value": None,
        }

        error = CoreError("Complex error", details=complex_details)

        assert error.details["nested"]["key"] == "value"
        assert error.details["list"] == [1, 2, 3]
        assert error.details["number"] == 42
        assert error.details["boolean"] is True
        assert error.details["none_value"] is None

    def test_details_serialization(self) -> None:
        """Test that details can be serialized to JSON."""
        import json

        details = {"timestamp": "2023-01-01T12:00:00Z", "count": 5, "enabled": True}

        error = CoreError("Serialization test", details=details)

        # Should be able to serialize details to JSON
        json_str = json.dumps(error.details)
        parsed_details = json.loads(json_str)

        assert parsed_details == details


@pytest.mark.unit
class TestExceptionEdgeCases:
    """Test cases for exception edge cases."""

    def test_empty_message(self) -> None:
        """Test exception with empty message."""
        error = CoreError("")

        assert error.message == ""
        assert str(error) == ""

    def test_very_long_message(self) -> None:
        """Test exception with very long message."""
        long_message = "x" * 10000
        error = CoreError(long_message)

        assert error.message == long_message
        assert len(str(error)) >= 10000

    def test_special_characters_in_message(self) -> None:
        """Test exception with special characters in message."""
        special_message = "Error with 特殊字符 and émojis 🚫 and newlines\nand tabs\t"
        error = CoreError(special_message)

        assert error.message == special_message
        assert special_message in str(error)

    def test_unicode_in_details(self) -> None:
        """Test exception with unicode in details."""
        unicode_details = {"symbol": "交易代碼", "message": "価格が無効です", "emoji": "💰"}

        error = CoreError("Unicode test", details=unicode_details)

        assert error.details["symbol"] == "交易代碼"
        assert error.details["message"] == "価格が無効です"
        assert error.details["emoji"] == "💰"


@pytest.mark.unit
class TestAllExceptionTypes:
    """Test cases to ensure all exception types work correctly."""

    def test_all_simple_exception_types(self) -> None:
        """Test all simple exception types can be created and work correctly."""
        exceptions_to_test = [
            (ConfigurationError, "Configuration error"),
            (DataProviderError, "Data provider error"),
            (StorageError, "Storage error"),
            (StorageWriteError, "Storage write error"),
            (StorageReadError, "Storage read error"),
            (EventBusError, "Event bus error"),
            (ValidationError, "Validation error"),
            (NetworkError, "Network error"),
            (TimeoutError, "Timeout error"),
        ]

        for exception_class, message in exceptions_to_test:
            error = exception_class(message)

            assert error.message == message
            assert error.error_code == exception_class.__name__
            assert error.details == {"trace_id": "no-trace"}
            assert isinstance(error, CoreError)
            assert isinstance(error, exception_class)

            # Test string representation
            assert str(error) == message

            # Test can be raised and caught
            with pytest.raises(exception_class):
                raise error

    def test_specialized_exception_types_basic_usage(self) -> None:
        """Test specialized exception types with basic usage."""
        # Test RateLimitError
        rate_error = RateLimitError("Too many requests")
        assert isinstance(rate_error, DataProviderError)
        assert rate_error.retry_after is None

        # Test DataValidationError
        validation_error = DataValidationError("Invalid data")
        assert isinstance(validation_error, ValidationError)
        assert validation_error.field_name is None

        # Test ResourceExhaustedError
        resource_error = ResourceExhaustedError("Out of memory")
        assert isinstance(resource_error, CoreError)
        assert resource_error.resource_type is None

        # Test CircuitBreakerError
        circuit_error = CircuitBreakerError("Circuit open")
        assert isinstance(circuit_error, CoreError)
        assert circuit_error.service_name is None
