import pytest

from asset_core.exceptions import (
    AuthenticationError,
    ConnectionError,
    CoreError,
    DataProviderError,
    DataValidationError,
    NetworkError,
    RateLimitError,
    StorageConnectionError,
    StorageWriteError,
    ValidationError,
)


@pytest.mark.integration
@pytest.mark.exceptions
class TestExceptionIntegration:
    """Integration test cases for exception system."""

    def test_complete_error_lifecycle(self) -> None:
        """Test complete error lifecycle with all features."""
        try:
            # Simulate a complex error scenario
            raise DataValidationError(
                "Price validation failed for trading pair",
                field_name="price",
                field_value=-100.50,
                error_code="NEGATIVE_PRICE_ERROR",
                details={
                    "symbol": "BTCUSDT",
                    "timestamp": "2023-01-01T12:00:00Z",
                    "user_id": 12345,
                    "validation_rules": ["positive_price", "min_price_0.01"],
                },
            )
        except DataValidationError as e:
            # Verify all error information is accessible
            assert e.message == "Price validation failed for trading pair"
            assert e.field_name == "price"
            assert e.field_value == -100.50
            assert e.error_code == "NEGATIVE_PRICE_ERROR"
            assert e.details["symbol"] == "BTCUSDT"
            assert e.details["field_name"] == "price"
            assert e.details["field_value"] == "-100.5"

            # Verify inheritance chain
            assert isinstance(e, DataValidationError)
            assert isinstance(e, ValidationError)
            assert isinstance(e, CoreError)
            assert isinstance(e, Exception)

            # Verify string representation
            error_str = str(e)
            assert "NEGATIVE_PRICE_ERROR" in error_str
            assert "Price validation failed" in error_str
            assert "Details:" in error_str

    def test_error_chaining_scenarios(self) -> None:
        """Test error chaining and context scenarios."""

        def level_3_function() -> None:
            raise StorageConnectionError("Database connection lost")

        def level_2_function() -> None:
            try:
                level_3_function()
            except StorageConnectionError as e:
                raise StorageWriteError(
                    "Failed to save trade data", error_code="TRADE_SAVE_FAILED", details={"original_error": str(e)}
                ) from e

        def level_1_function() -> None:
            try:
                level_2_function()
            except StorageWriteError as e:
                raise CoreError(
                    "Trading operation failed",
                    error_code="TRADING_OPERATION_FAILED",
                    details={"operation": "buy_order", "inner_error": str(e)},
                ) from e

        with pytest.raises(CoreError) as exc_info:
            level_1_function()

        # Verify error chaining
        error = exc_info.value
        assert error.message == "Trading operation failed"
        assert error.error_code == "TRADING_OPERATION_FAILED"
        assert "buy_order" in error.details["operation"]

        # Verify cause chain
        assert error.__cause__ is not None
        assert isinstance(error.__cause__, StorageWriteError)
        assert error.__cause__.__cause__ is not None
        assert isinstance(error.__cause__.__cause__, StorageConnectionError)

    def test_exception_polymorphism(self) -> None:
        """Test exception polymorphism in error handling."""

        def handle_data_provider_error(error: DataProviderError) -> str:
            """Generic handler for data provider errors."""
            base_info = f"Provider Error: {error.message}"

            if isinstance(error, RateLimitError):
                if error.retry_after:
                    return f"{base_info} (retry after {error.retry_after}s)"
            elif isinstance(error, AuthenticationError):
                return f"{base_info} (authentication required)"
            elif isinstance(error, ConnectionError):
                return f"{base_info} (connection issue)"

            return base_info

        # Test polymorphic handling
        rate_limit = RateLimitError("Too many requests", retry_after=60)
        auth_error = AuthenticationError("Invalid API key")
        conn_error = ConnectionError("Network timeout")

        assert "retry after 60s" in handle_data_provider_error(rate_limit)
        assert "authentication required" in handle_data_provider_error(auth_error)
        assert "connection issue" in handle_data_provider_error(conn_error)

    def test_error_aggregation_scenario(self) -> None:
        """Test error aggregation scenarios."""
        errors = []

        # Collect multiple errors
        try:
            raise DataValidationError("Invalid price", field_name="price")
        except Exception as e:
            errors.append(e)

        try:
            raise DataValidationError("Invalid quantity", field_name="quantity")
        except Exception as e:
            errors.append(e)

        try:
            raise NetworkError("Connection timeout")
        except Exception as e:
            errors.append(e)

        # Create aggregated error
        aggregated_details = {
            "error_count": len(errors),
            "errors": [
                {
                    "type": type(e).__name__,
                    "message": e.message if isinstance(e, CoreError) else str(e),
                    "code": e.error_code if isinstance(e, CoreError) else type(e).__name__,
                }
                for e in errors
            ],
        }

        aggregated_error = CoreError(
            "Multiple validation errors occurred", error_code="MULTIPLE_ERRORS", details=aggregated_details
        )

        assert aggregated_error.details["error_count"] == 3
        assert len(aggregated_error.details["errors"]) == 3
        assert aggregated_error.details["errors"][0]["type"] == "DataValidationError"
        assert aggregated_error.details["errors"][2]["type"] == "NetworkError"
