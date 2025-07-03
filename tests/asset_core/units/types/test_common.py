# ABOUTME: 測試asset_core.types.common模組的類型定義和功能
# ABOUTME: 驗證自定義類型、枚舉、數據類別的實例化和類型轉換邏輯

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.types.common import (
    URL,
    CPUUsage,
    ExchangeName,
    Failure,
    HostPort,
    # Protocol types
    Identifiable,
    JsonValue,
    OptionalPrice,
    OptionalQuantity,
    OptionalSymbol,
    OptionalTimestamp,
    OrderBook,
    OrderId,
    PageSize,
    Price,
    PriceLevel,
    PriceList,
    Quantity,
    QueryLimit,
    QueryOffset,
    Result,
    Success,
    SuccessOrFailure,
    # NewType types
    Symbol,
    Symbolized,
    SymbolList,
    Timeout,
    Timestamped,
    TimestampList,
    TimestampMs,
    TimestampUs,
    TradeId,
    Volume,
)


@pytest.mark.unit
class TestNewTypeInstantiation:
    """Test cases for NewType instances.

    Verifies that NewType-based types can be correctly instantiated
    and maintain their underlying string representation while providing
    type safety at the static analysis level.
    """

    def test_symbol_instantiation(self) -> None:
        """Test Symbol NewType instantiation.

        Description of what the test covers:
        Verifies that Symbol can be created from a string and maintains
        its string value while providing semantic distinction.

        Preconditions:
        - None.

        Steps:
        - Create a Symbol instance from a string
        - Assert that the Symbol value equals the original string
        - Assert that isinstance check works for the underlying type

        Expected Result:
        - Symbol should be instantiated correctly and maintain string properties
        """
        symbol_str = "BTCUSDT"
        symbol = Symbol(symbol_str)

        assert symbol == symbol_str
        assert isinstance(symbol, str)
        assert str(symbol) == symbol_str

    def test_exchange_name_instantiation(self) -> None:
        """Test ExchangeName NewType instantiation.

        Description of what the test covers:
        Verifies that ExchangeName can be created from a string and maintains
        its string value while providing semantic distinction.

        Preconditions:
        - None.

        Steps:
        - Create an ExchangeName instance from a string
        - Assert that the ExchangeName value equals the original string
        - Assert that isinstance check works for the underlying type

        Expected Result:
        - ExchangeName should be instantiated correctly and maintain string properties
        """
        exchange_str = "Binance"
        exchange = ExchangeName(exchange_str)

        assert exchange == exchange_str
        assert isinstance(exchange, str)
        assert str(exchange) == exchange_str

    def test_trade_id_instantiation(self) -> None:
        """Test TradeId NewType instantiation.

        Description of what the test covers:
        Verifies that TradeId can be created from a string and maintains
        its string value while providing semantic distinction.

        Preconditions:
        - None.

        Steps:
        - Create a TradeId instance from a string
        - Assert that the TradeId value equals the original string
        - Assert that isinstance check works for the underlying type

        Expected Result:
        - TradeId should be instantiated correctly and maintain string properties
        """
        trade_id_str = "12345"
        trade_id = TradeId(trade_id_str)

        assert trade_id == trade_id_str
        assert isinstance(trade_id, str)
        assert str(trade_id) == trade_id_str

    def test_order_id_instantiation(self) -> None:
        """Test OrderId NewType instantiation.

        Description of what the test covers:
        Verifies that OrderId can be created from a string and maintains
        its string value while providing semantic distinction.

        Preconditions:
        - None.

        Steps:
        - Create an OrderId instance from a string
        - Assert that the OrderId value equals the original string
        - Assert that isinstance check works for the underlying type

        Expected Result:
        - OrderId should be instantiated correctly and maintain string properties
        """
        order_id_str = "order_67890"
        order_id = OrderId(order_id_str)

        assert order_id == order_id_str
        assert isinstance(order_id, str)
        assert str(order_id) == order_id_str

    def test_url_instantiation(self) -> None:
        """Test URL NewType instantiation.

        Description of what the test covers:
        Verifies that URL can be created from a string and maintains
        its string value while providing semantic distinction.

        Preconditions:
        - None.

        Steps:
        - Create a URL instance from a string
        - Assert that the URL value equals the original string
        - Assert that isinstance check works for the underlying type

        Expected Result:
        - URL should be instantiated correctly and maintain string properties
        """
        url_str = "https://api.binance.com/v3/ticker/price"
        url = URL(url_str)

        assert url == url_str
        assert isinstance(url, str)
        assert str(url) == url_str

    def test_multiple_newtype_instances(self) -> None:
        """Test multiple NewType instances with different types.

        Description of what the test covers:
        Verifies that different NewType instances can coexist and maintain
        their respective values without interference.

        Preconditions:
        - None.

        Steps:
        - Create instances of various NewType types
        - Assert each maintains its original value
        - Assert they can be used in collections

        Expected Result:
        - All NewType instances should maintain their values independently
        """
        symbol = Symbol("ETHUSDT")
        exchange = ExchangeName("Coinbase")
        trade_id = TradeId("trade123")

        assert symbol == "ETHUSDT"
        assert exchange == "Coinbase"
        assert trade_id == "trade123"

        # Test they can be used in collections
        identifiers = [symbol, exchange, trade_id]
        assert len(identifiers) == 3
        assert "ETHUSDT" in identifiers
        assert "Coinbase" in identifiers
        assert "trade123" in identifiers


@pytest.mark.unit
class TestAnnotatedTypeConstraints:
    """Test cases for Pydantic Annotated type constraint validation.

    Verifies that Annotated types properly enforce their constraints
    by testing edge cases and invalid values that should trigger validation errors.
    """

    def test_price_constraint_violations(self) -> None:
        """Test Price type constraint violations.

        Description of what the test covers:
        Verifies that Price type properly rejects zero, negative, and non-decimal values.
        Tests the Pydantic Field constraints (gt=0, decimal_places=12).

        Preconditions:
        - Price is defined as Annotated[Decimal, Field(gt=0, decimal_places=12)].

        Steps:
        - Create a mock Pydantic model with Price field
        - Test invalid values (zero, negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid Price values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class PriceModel(BaseModel):
            price: Price

        # Test zero price (should fail gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            PriceModel(price=Decimal("0"))
        assert "greater than 0" in str(exc_info.value)

        # Test negative price (should fail gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            PriceModel(price=Decimal("-10.50"))
        assert "greater than 0" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            PriceModel(price="not_a_decimal")
        error_str = str(exc_info.value)
        assert "decimal" in error_str.lower() or "invalid" in error_str.lower()

        # Test None value (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            PriceModel(price=None)
        assert (
            "none is not an allowed value" in str(exc_info.value).lower()
            or "input should be" in str(exc_info.value).lower()
        )

    def test_quantity_constraint_violations(self) -> None:
        """Test Quantity type constraint violations.

        Description of what the test covers:
        Verifies that Quantity type properly rejects negative values and non-decimal types.
        Tests the Pydantic Field constraints (ge=0, decimal_places=12).

        Preconditions:
        - Quantity is defined as Annotated[Decimal, Field(ge=0, decimal_places=12)].

        Steps:
        - Create a mock Pydantic model with Quantity field
        - Test invalid values (negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid Quantity values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class QuantityModel(BaseModel):
            quantity: Quantity

        # Test negative quantity (should fail ge=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            QuantityModel(quantity=Decimal("-1.0"))
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        # Note: Pydantic may coerce int to Decimal, so we test with non-numeric type
        with pytest.raises(ValidationError) as exc_info:
            QuantityModel(quantity=["not", "decimal"])
        error_str = str(exc_info.value)
        assert (
            "decimal" in error_str.lower() or "invalid" in error_str.lower() or "input should be" in error_str.lower()
        )

        # Test string that cannot be converted to decimal
        with pytest.raises(ValidationError) as exc_info:
            QuantityModel(quantity="invalid_decimal")
        error_str = str(exc_info.value)
        assert "decimal" in error_str.lower() or "invalid" in error_str.lower()

    def test_volume_constraint_violations(self) -> None:
        """Test Volume type constraint violations.

        Description of what the test covers:
        Verifies that Volume type properly rejects negative values and non-decimal types.
        Tests the Pydantic Field constraints (ge=0, decimal_places=12).

        Preconditions:
        - Volume is defined as Annotated[Decimal, Field(ge=0, decimal_places=12)].

        Steps:
        - Create a mock Pydantic model with Volume field
        - Test invalid values (negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid Volume values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class VolumeModel(BaseModel):
            volume: Volume

        # Test negative volume (should fail ge=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            VolumeModel(volume=Decimal("-100.0"))
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            VolumeModel(volume=[1, 2, 3])
        error_str = str(exc_info.value)
        assert "decimal" in error_str.lower() or "invalid" in error_str.lower()

    def test_timeout_constraint_violations(self) -> None:
        """Test Timeout type constraint violations.

        Description of what the test covers:
        Verifies that Timeout type properly rejects zero, negative, and non-float values.
        Tests the Pydantic Field constraints (gt=0).

        Preconditions:
        - Timeout is defined as Annotated[float, Field(gt=0)].

        Steps:
        - Create a mock Pydantic model with Timeout field
        - Test invalid values (zero, negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid Timeout values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class TimeoutModel(BaseModel):
            timeout: Timeout

        # Test zero timeout (should fail gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            TimeoutModel(timeout=0.0)
        assert "greater than 0" in str(exc_info.value)

        # Test negative timeout (should fail gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            TimeoutModel(timeout=-5.0)
        assert "greater than 0" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            TimeoutModel(timeout="not_a_float")
        error_str = str(exc_info.value)
        assert "float" in error_str.lower() or "invalid" in error_str.lower()

    def test_query_limit_constraint_violations(self) -> None:
        """Test QueryLimit type constraint violations.

        Description of what the test covers:
        Verifies that QueryLimit type properly rejects zero, negative, and non-integer values.
        Tests the Pydantic Field constraints (ge=1).

        Preconditions:
        - QueryLimit is defined as Annotated[int, Field(ge=1)].

        Steps:
        - Create a mock Pydantic model with QueryLimit field
        - Test invalid values (zero, negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid QueryLimit values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class QueryLimitModel(BaseModel):
            limit: QueryLimit

        # Test zero limit (should fail ge=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            QueryLimitModel(limit=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test negative limit (should fail ge=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            QueryLimitModel(limit=-10)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            QueryLimitModel(limit=3.14)
        error_str = str(exc_info.value)
        assert "int" in error_str.lower() or "integer" in error_str.lower()

    def test_query_offset_constraint_violations(self) -> None:
        """Test QueryOffset type constraint violations.

        Description of what the test covers:
        Verifies that QueryOffset type properly rejects negative values and non-integer types.
        Tests the Pydantic Field constraints (ge=0).

        Preconditions:
        - QueryOffset is defined as Annotated[int, Field(ge=0)].

        Steps:
        - Create a mock Pydantic model with QueryOffset field
        - Test invalid values (negative, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid QueryOffset values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class QueryOffsetModel(BaseModel):
            offset: QueryOffset

        # Test negative offset (should fail ge=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            QueryOffsetModel(offset=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            QueryOffsetModel(offset="not_an_int")
        error_str = str(exc_info.value)
        assert "int" in error_str.lower() or "integer" in error_str.lower()

    def test_page_size_constraint_violations(self) -> None:
        """Test PageSize type constraint violations.

        Description of what the test covers:
        Verifies that PageSize type properly enforces its range constraints (1-1000).
        Tests the Pydantic Field constraints (ge=1, le=1000).

        Preconditions:
        - PageSize is defined as Annotated[int, Field(ge=1, le=1000)].

        Steps:
        - Create a mock Pydantic model with PageSize field
        - Test boundary violations (zero, too large, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid PageSize values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class PageSizeModel(BaseModel):
            page_size: PageSize

        # Test zero page size (should fail ge=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            PageSizeModel(page_size=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test page size too large (should fail le=1000 constraint)
        with pytest.raises(ValidationError) as exc_info:
            PageSizeModel(page_size=1001)
        assert "less than or equal to 1000" in str(exc_info.value)

        # Test negative page size (should fail ge=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            PageSizeModel(page_size=-10)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            PageSizeModel(page_size=2.5)
        error_str = str(exc_info.value)
        assert "int" in error_str.lower() or "integer" in error_str.lower()

    def test_cpu_usage_constraint_violations(self) -> None:
        """Test CPUUsage type constraint violations.

        Description of what the test covers:
        Verifies that CPUUsage type properly enforces its percentage range (0-100).
        Tests the Pydantic Field constraints (ge=0, le=100).

        Preconditions:
        - CPUUsage is defined as Annotated[float, Field(ge=0, le=100)].

        Steps:
        - Create a mock Pydantic model with CPUUsage field
        - Test boundary violations (negative, over 100, wrong type)
        - Verify ValidationError is raised

        Expected Result:
        - Invalid CPUUsage values should raise ValidationError with appropriate messages
        """
        from pydantic import BaseModel, ValidationError

        class CPUUsageModel(BaseModel):
            cpu: CPUUsage

        # Test negative CPU usage (should fail ge=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            CPUUsageModel(cpu=-10.0)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test CPU usage over 100% (should fail le=100 constraint)
        with pytest.raises(ValidationError) as exc_info:
            CPUUsageModel(cpu=150.0)
        assert "less than or equal to 100" in str(exc_info.value)

        # Test invalid type (should fail type validation)
        with pytest.raises(ValidationError) as exc_info:
            CPUUsageModel(cpu="high")
        error_str = str(exc_info.value)
        assert "float" in error_str.lower() or "invalid" in error_str.lower()

    def test_decimal_precision_constraints(self) -> None:
        """Test decimal precision constraints for financial types.

        Description of what the test covers:
        Verifies that Price, Quantity, and Volume types properly handle
        decimal precision constraints (decimal_places=12).

        Preconditions:
        - Financial types are defined with decimal_places=12 constraint.

        Steps:
        - Create models with financial types
        - Test values with excessive decimal places
        - Verify behavior (rounding or validation error)

        Expected Result:
        - Values should be accepted and precision handled appropriately
        """
        from pydantic import BaseModel

        class FinancialModel(BaseModel):
            price: Price
            quantity: Quantity
            volume: Volume

        # This should work - Pydantic should handle precision appropriately
        model = FinancialModel(
            price=Decimal("100.123456789012"), quantity=Decimal("1.123456789012"), volume=Decimal("101.123456789012")
        )

        assert model.price == Decimal("100.123456789012")
        assert model.quantity == Decimal("1.123456789012")
        assert model.volume == Decimal("101.123456789012")

    def test_type_coercion_behavior(self) -> None:
        """Test type coercion behavior for Annotated types.

        Description of what the test covers:
        Verifies how Pydantic handles type coercion for Annotated types,
        particularly for numeric types that can be converted.

        Preconditions:
        - Pydantic models with Annotated types are defined.

        Steps:
        - Test valid coercions (string to Decimal, int to float, etc.)
        - Verify successful conversions
        - Test invalid coercions that should fail

        Expected Result:
        - Valid coercions should succeed with proper type conversion
        - Invalid coercions should raise ValidationError
        """
        from pydantic import BaseModel, ValidationError

        class CoercionTestModel(BaseModel):
            price: Price
            timeout: Timeout
            limit: QueryLimit

        # Test valid coercions
        model = CoercionTestModel(
            price="100.50",  # String to Decimal
            timeout=30,  # Int to float
            limit="10",  # String to int
        )

        assert model.price == Decimal("100.50")
        assert model.timeout == 30.0
        assert model.limit == 10

        # Test invalid coercions that should fail
        with pytest.raises(ValidationError):
            CoercionTestModel(price="not_a_number", timeout=30.0, limit=10)

        with pytest.raises(ValidationError):
            CoercionTestModel(price="100.50", timeout="not_a_number", limit=10)

    def test_edge_case_boundary_values(self) -> None:
        """Test edge case boundary values for constrained types.

        Description of what the test covers:
        Verifies behavior at exact constraint boundaries and with
        extreme values for all constrained types.

        Preconditions:
        - All constrained types are properly defined.

        Steps:
        - Test exact boundary values for each type
        - Test very small and very large valid values
        - Verify consistent behavior

        Expected Result:
        - Boundary values should be handled consistently
        - Extreme valid values should be accepted
        """
        from pydantic import BaseModel

        class BoundaryTestModel(BaseModel):
            page_size_min: PageSize
            page_size_max: PageSize
            cpu_min: CPUUsage
            cpu_max: CPUUsage
            query_limit_min: QueryLimit
            query_offset_min: QueryOffset

        # Test exact boundary values
        model = BoundaryTestModel(
            page_size_min=1,  # Minimum valid PageSize
            page_size_max=1000,  # Maximum valid PageSize
            cpu_min=0.0,  # Minimum valid CPUUsage
            cpu_max=100.0,  # Maximum valid CPUUsage
            query_limit_min=1,  # Minimum valid QueryLimit
            query_offset_min=0,  # Minimum valid QueryOffset
        )

        assert model.page_size_min == 1
        assert model.page_size_max == 1000
        assert model.cpu_min == 0.0
        assert model.cpu_max == 100.0
        assert model.query_limit_min == 1
        assert model.query_offset_min == 0

        # Test very small valid values for financial types
        from pydantic import create_model

        small_financial_model = create_model(
            "SmallFinancialModel",
            tiny_price=(Price, ...),
            tiny_quantity=(Quantity, ...),
            tiny_volume=(Volume, ...),
        )

        tiny_model = small_financial_model(
            tiny_price=Decimal("0.000000000001"),
            tiny_quantity=Decimal("0.000000000001"),
            tiny_volume=Decimal("0.000000000001"),
        )

        assert tiny_model.tiny_price > 0  # type: ignore[attr-defined]
        assert tiny_model.tiny_quantity >= 0  # type: ignore[attr-defined]
        assert tiny_model.tiny_volume >= 0  # type: ignore[attr-defined]


@pytest.mark.unit
class TestResultTypes:
    """Test cases for Result type hierarchy.

    Verifies the behavior of Result, Success, and Failure types
    for error handling patterns.
    """

    def test_success_instantiation(self) -> None:
        """Test Success type instantiation.

        Description of what the test covers:
        Verifies that Success can be instantiated with a value
        and the value is accessible via the value attribute.

        Preconditions:
        - None.

        Steps:
        - Create Success instances with various value types
        - Assert the value attribute contains the expected value
        - Assert Success is a subclass of Result

        Expected Result:
        - Success should store the provided value correctly
        """
        # Test with various value types
        success_str = Success("operation completed")
        success_int = Success(42)
        success_dict = Success({"status": "ok"})

        assert success_str.value == "operation completed"
        assert success_int.value == 42
        assert success_dict.value == {"status": "ok"}

        # Verify inheritance
        assert isinstance(success_str, Result)
        assert isinstance(success_int, Result)
        assert isinstance(success_dict, Result)

    def test_failure_instantiation(self) -> None:
        """Test Failure type instantiation.

        Description of what the test covers:
        Verifies that Failure can be instantiated with an Exception
        and the exception is accessible via the error attribute.

        Preconditions:
        - None.

        Steps:
        - Create Failure instances with various exception types
        - Assert the error attribute contains the expected exception
        - Assert Failure is a subclass of Result

        Expected Result:
        - Failure should store the provided exception correctly
        """
        # Test with various exception types
        value_error = ValueError("Invalid value")
        type_error = TypeError("Wrong type")
        custom_error = Exception("Custom error")

        failure_value: Failure[ValueError] = Failure(value_error)
        failure_type: Failure[TypeError] = Failure(type_error)
        failure_custom: Failure[Exception] = Failure(custom_error)

        assert failure_value.error == value_error
        assert failure_type.error == type_error
        assert failure_custom.error == custom_error

        # Verify inheritance
        assert isinstance(failure_value, Result)
        assert isinstance(failure_type, Result)
        assert isinstance(failure_custom, Result)

    def test_result_type_discrimination(self) -> None:
        """Test Result type discrimination.

        Description of what the test covers:
        Verifies that Success and Failure instances can be
        distinguished and handled appropriately in conditional logic.

        Preconditions:
        - None.

        Steps:
        - Create Success and Failure instances
        - Use isinstance checks to discriminate between types
        - Assert proper type discrimination works

        Expected Result:
        - Success and Failure should be distinguishable via isinstance
        """
        success_result = Success("success")
        failure_result: Failure[Exception] = Failure(Exception("error"))

        # Test type discrimination
        assert isinstance(success_result, Success)
        assert not isinstance(success_result, Failure)

        assert isinstance(failure_result, Failure)
        assert not isinstance(failure_result, Success)

        # Both should be Result instances
        assert isinstance(success_result, Result)
        assert isinstance(failure_result, Result)

    def test_result_pattern_matching(self) -> None:
        """Test Result pattern matching usage.

        Description of what the test covers:
        Verifies that Result types can be used in pattern matching
        or conditional logic to handle success/failure cases.

        Preconditions:
        - None.

        Steps:
        - Create Success and Failure instances
        - Process them through conditional logic
        - Assert proper handling of each case

        Expected Result:
        - Result types should enable proper success/failure handling
        """

        def process_result(result: SuccessOrFailure[str]) -> str:
            """Helper function to process Result types."""
            if isinstance(result, Success):
                return f"Success: {result.value}"
            else:
                return f"Failure: {str(result.error)}"

        success_result = Success("operation completed")
        failure_result: Failure[str] = Failure(ValueError("validation failed"))

        success_message = process_result(success_result)
        failure_message = process_result(failure_result)

        assert success_message == "Success: operation completed"
        assert failure_message == "Failure: validation failed"


@pytest.mark.unit
class TestProtocolTypes:
    """Test cases for Protocol types.

    Verifies that Protocol types can be implemented by classes
    and provide structural typing capabilities.
    """

    def test_identifiable_protocol(self) -> None:
        """Test Identifiable protocol implementation.

        Description of what the test covers:
        Verifies that classes implementing the Identifiable protocol
        are recognized as conforming to the protocol.

        Preconditions:
        - None.

        Steps:
        - Create a class implementing Identifiable protocol
        - Verify protocol conformance
        - Test accessing the id attribute

        Expected Result:
        - Classes with id attribute should conform to Identifiable protocol
        """

        class MockIdentifiable:
            def __init__(self, id_value: str):
                self.id = id_value

        mock_obj = MockIdentifiable("test_id_123")

        # Verify protocol conformance (structural typing)
        assert hasattr(mock_obj, "id")
        assert mock_obj.id == "test_id_123"

        # Test it can be used where Identifiable is expected
        def get_id(obj: Identifiable[str]) -> str:
            return obj.id

        result = get_id(mock_obj)
        assert result == "test_id_123"

    def test_timestamped_protocol(self) -> None:
        """Test Timestamped protocol implementation.

        Description of what the test covers:
        Verifies that classes implementing the Timestamped protocol
        are recognized as conforming to the protocol.

        Preconditions:
        - None.

        Steps:
        - Create a class implementing Timestamped protocol
        - Verify protocol conformance
        - Test accessing the timestamp attribute

        Expected Result:
        - Classes with timestamp attribute should conform to Timestamped protocol
        """

        class MockTimestamped:
            def __init__(self, timestamp: datetime):
                self.timestamp = timestamp

        test_timestamp = datetime.now(UTC)
        mock_obj = MockTimestamped(test_timestamp)

        # Verify protocol conformance (structural typing)
        assert hasattr(mock_obj, "timestamp")
        assert mock_obj.timestamp == test_timestamp

        # Test it can be used where Timestamped is expected
        def get_timestamp(obj: Timestamped) -> datetime:
            return obj.timestamp

        result = get_timestamp(mock_obj)
        assert result == test_timestamp

    def test_symbolized_protocol(self) -> None:
        """Test Symbolized protocol implementation.

        Description of what the test covers:
        Verifies that classes implementing the Symbolized protocol
        are recognized as conforming to the protocol.

        Preconditions:
        - None.

        Steps:
        - Create a class implementing Symbolized protocol
        - Verify protocol conformance
        - Test accessing the symbol attribute

        Expected Result:
        - Classes with symbol attribute should conform to Symbolized protocol
        """

        class MockSymbolized:
            def __init__(self, symbol: Symbol):
                self.symbol = symbol

        test_symbol = Symbol("BTCUSDT")
        mock_obj = MockSymbolized(test_symbol)

        # Verify protocol conformance (structural typing)
        assert hasattr(mock_obj, "symbol")
        assert mock_obj.symbol == test_symbol

        # Test it can be used where Symbolized is expected
        def get_symbol(obj: Symbolized) -> Symbol:
            return obj.symbol

        result = get_symbol(mock_obj)
        assert result == test_symbol

    def test_serializable_protocol(self) -> None:
        """Test Serializable protocol implementation.

        Description of what the test covers:
        Verifies that classes implementing the Serializable protocol
        provide to_dict and from_dict methods.

        Preconditions:
        - None.

        Steps:
        - Create a class implementing Serializable protocol
        - Verify protocol conformance
        - Test to_dict and from_dict methods

        Expected Result:
        - Classes should properly implement serialization methods
        """

        class MockSerializable:
            def __init__(self, data: dict[str, Any]):
                self.data = data

            def to_dict(self) -> dict[str, Any]:
                return self.data.copy()

            @classmethod
            def from_dict(cls, data: dict[str, Any]) -> "MockSerializable":
                return cls(data)

        test_data = {"key": "value", "number": 42}
        mock_obj = MockSerializable(test_data)

        # Verify protocol conformance
        assert hasattr(mock_obj, "to_dict")
        assert hasattr(mock_obj, "from_dict")
        assert callable(mock_obj.to_dict)
        assert callable(mock_obj.from_dict)

        # Test serialization
        serialized = mock_obj.to_dict()
        assert serialized == test_data

        # Test deserialization
        new_obj = MockSerializable.from_dict(serialized)
        assert new_obj.data == test_data

    def test_validatable_protocol(self) -> None:
        """Test Validatable protocol implementation.

        Description of what the test covers:
        Verifies that classes implementing the Validatable protocol
        provide a validate method that returns a boolean.

        Preconditions:
        - None.

        Steps:
        - Create a class implementing Validatable protocol
        - Verify protocol conformance
        - Test validate method

        Expected Result:
        - Classes should properly implement validation method
        """

        class MockValidatable:
            def __init__(self, value: int):
                self.value = value

            def validate(self) -> bool:
                return self.value > 0

        valid_obj = MockValidatable(10)
        invalid_obj = MockValidatable(-5)

        # Verify protocol conformance
        assert hasattr(valid_obj, "validate")
        assert callable(valid_obj.validate)

        # Test validation
        assert valid_obj.validate() is True
        assert invalid_obj.validate() is False


@pytest.mark.unit
class TestTypeAliases:
    """Test cases for type aliases.

    Verifies that type aliases are properly defined and can be used
    with their expected underlying types.
    """

    def test_json_value_types(self) -> None:
        """Test JsonValue type alias accepts valid JSON types.

        Description of what the test covers:
        Verifies that JsonValue type alias encompasses all valid JSON
        value types including strings, numbers, booleans, null, objects, and arrays.

        Preconditions:
        - None.

        Steps:
        - Create instances of all valid JSON value types
        - Verify they are of expected underlying types

        Expected Result:
        - All JSON value types should be valid
        """
        # Test all JsonValue types
        json_string: JsonValue = "test string"
        json_int: JsonValue = 42
        json_float: JsonValue = 3.14
        json_bool: JsonValue = True
        json_none: JsonValue = None
        json_dict: JsonValue = {"key": "value"}
        json_list: JsonValue = [1, 2, 3]

        assert isinstance(json_string, str)
        assert isinstance(json_int, int)
        assert isinstance(json_float, float)
        assert isinstance(json_bool, bool)
        assert json_none is None
        assert isinstance(json_dict, dict)
        assert isinstance(json_list, list)

    def test_timestamp_types(self) -> None:
        """Test timestamp type aliases.

        Description of what the test covers:
        Verifies that timestamp type aliases (TimestampMs, TimestampUs)
        are properly defined as integer types.

        Preconditions:
        - None.

        Steps:
        - Create instances of timestamp types
        - Verify they are integers

        Expected Result:
        - Timestamp types should be integer values
        """
        # Test timestamp types
        timestamp_ms: TimestampMs = 1640995200000  # 2022-01-01 00:00:00 UTC in ms
        timestamp_us: TimestampUs = 1640995200000000  # 2022-01-01 00:00:00 UTC in μs

        assert isinstance(timestamp_ms, int)
        assert isinstance(timestamp_us, int)
        assert timestamp_us == timestamp_ms * 1000

    def test_host_port_tuple(self) -> None:
        """Test HostPort type alias.

        Description of what the test covers:
        Verifies that HostPort type alias is a tuple of string and int
        representing host and port combinations.

        Preconditions:
        - None.

        Steps:
        - Create HostPort tuples
        - Verify tuple structure and types

        Expected Result:
        - HostPort should be tuple of (str, int)
        """
        # Test HostPort type
        host_port: HostPort = ("localhost", 8080)
        host_port_prod: HostPort = ("api.exchange.com", 443)

        assert isinstance(host_port, tuple)
        assert len(host_port) == 2
        assert isinstance(host_port[0], str)
        assert isinstance(host_port[1], int)

        assert isinstance(host_port_prod, tuple)
        assert len(host_port_prod) == 2
        assert isinstance(host_port_prod[0], str)
        assert isinstance(host_port_prod[1], int)

    def test_price_level_tuple(self) -> None:
        """Test PriceLevel type alias.

        Description of what the test covers:
        Verifies that PriceLevel type alias is a tuple of Price and Quantity
        representing order book levels.

        Preconditions:
        - None.

        Steps:
        - Create PriceLevel tuples
        - Verify tuple structure and types

        Expected Result:
        - PriceLevel should be tuple of (Price, Quantity)
        """
        # Test PriceLevel type
        price = Decimal("100.50")
        quantity = Decimal("1.5")
        price_level: PriceLevel = (price, quantity)

        assert isinstance(price_level, tuple)
        assert len(price_level) == 2
        assert isinstance(price_level[0], Decimal)
        assert isinstance(price_level[1], Decimal)
        assert price_level[0] == price
        assert price_level[1] == quantity

    def test_order_book_structure(self) -> None:
        """Test OrderBook type alias structure.

        Description of what the test covers:
        Verifies that OrderBook type alias is a dictionary containing
        bid and ask price levels.

        Preconditions:
        - None.

        Steps:
        - Create OrderBook dictionaries
        - Verify structure and nested types

        Expected Result:
        - OrderBook should be dict with string keys and PriceLevel lists
        """
        # Test OrderBook type
        bids: list[PriceLevel] = [
            (Decimal("100.00"), Decimal("1.0")),
            (Decimal("99.50"), Decimal("2.5")),
        ]
        asks: list[PriceLevel] = [
            (Decimal("100.50"), Decimal("1.5")),
            (Decimal("101.00"), Decimal("3.0")),
        ]

        order_book: OrderBook = {
            "bids": bids,
            "asks": asks,
        }

        assert isinstance(order_book, dict)
        assert "bids" in order_book
        assert "asks" in order_book
        assert isinstance(order_book["bids"], list)
        assert isinstance(order_book["asks"], list)

        # Verify price levels
        for bid in order_book["bids"]:
            assert isinstance(bid, tuple)
            assert len(bid) == 2
            assert isinstance(bid[0], Decimal)
            assert isinstance(bid[1], Decimal)

    def test_optional_types(self) -> None:
        """Test optional type aliases.

        Description of what the test covers:
        Verifies that optional type aliases can hold both their
        expected type and None values.

        Preconditions:
        - None.

        Steps:
        - Create instances of optional types with both valid values and None
        - Verify type handling

        Expected Result:
        - Optional types should accept both valid values and None
        """
        # Test optional types with valid values
        opt_price: OptionalPrice = Decimal("100.50")
        opt_quantity: OptionalQuantity = Decimal("1.5")
        opt_timestamp: OptionalTimestamp = datetime.now(UTC)
        opt_symbol: OptionalSymbol = Symbol("BTCUSDT")

        assert isinstance(opt_price, Decimal)
        assert isinstance(opt_quantity, Decimal)
        assert isinstance(opt_timestamp, datetime)
        assert isinstance(opt_symbol, str)

        # Test optional types with None values
        opt_price_none: OptionalPrice = None
        opt_quantity_none: OptionalQuantity = None
        opt_timestamp_none: OptionalTimestamp = None
        opt_symbol_none: OptionalSymbol = None

        assert opt_price_none is None
        assert opt_quantity_none is None
        assert opt_timestamp_none is None
        assert opt_symbol_none is None

    def test_collection_types(self) -> None:
        """Test collection type aliases.

        Description of what the test covers:
        Verifies that collection type aliases (SymbolList, PriceList, etc.)
        can hold lists of their respective element types.

        Preconditions:
        - None.

        Steps:
        - Create collection instances with appropriate element types
        - Verify collection and element types

        Expected Result:
        - Collection types should hold lists of correct element types
        """
        # Test collection types
        symbol_list: SymbolList = [Symbol("BTCUSDT"), Symbol("ETHUSDT")]
        price_list: PriceList = [Decimal("100.0"), Decimal("200.0")]
        timestamp_list: TimestampList = [datetime.now(UTC), datetime.now(UTC)]

        assert isinstance(symbol_list, list)
        assert isinstance(price_list, list)
        assert isinstance(timestamp_list, list)

        # Verify element types
        for symbol in symbol_list:
            assert isinstance(symbol, str)

        for price in price_list:
            assert isinstance(price, Decimal)

        for timestamp in timestamp_list:
            assert isinstance(timestamp, datetime)


@pytest.mark.unit
class TestTypeConversions:
    """Test cases for type conversions and interoperability.

    Verifies that custom types can be converted and used with
    their underlying types appropriately.
    """

    def test_newtype_string_operations(self) -> None:
        """Test NewType instances work with string operations.

        Description of what the test covers:
        Verifies that NewType instances based on strings support
        standard string operations like concatenation, comparison,
        and string methods.

        Preconditions:
        - None.

        Steps:
        - Create NewType instances
        - Perform string operations
        - Verify results

        Expected Result:
        - NewType instances should support string operations
        """
        symbol = Symbol("BTC")
        exchange = ExchangeName("Binance")

        # String concatenation
        pair_symbol = Symbol(symbol + "USDT")
        assert pair_symbol == "BTCUSDT"

        # String comparison
        assert symbol < Symbol("ETH")
        assert exchange == "Binance"

        # String methods
        assert symbol.lower() == "btc"
        assert exchange.startswith("Bin")
        assert len(symbol) == 3

    def test_decimal_arithmetic_operations(self) -> None:
        """Test Decimal-based types support arithmetic operations.

        Description of what the test covers:
        Verifies that types based on Decimal (Price, Quantity, Volume)
        support standard arithmetic operations with precision.

        Preconditions:
        - None.

        Steps:
        - Create Decimal-based type instances
        - Perform arithmetic operations
        - Verify precision and results

        Expected Result:
        - Decimal-based types should support precise arithmetic
        """
        price = Decimal("100.50")
        quantity = Decimal("2.0")

        # Arithmetic operations
        volume = price * quantity
        assert volume == Decimal("201.00")

        total_price = price + Decimal("50.25")
        assert total_price == Decimal("150.75")

        half_quantity = quantity / Decimal("2")
        assert half_quantity == Decimal("1.0")

        # Precision preservation
        precise_price = Decimal("0.123456789012")
        precise_quantity = Decimal("1.000000000001")
        precise_volume = precise_price * precise_quantity
        assert isinstance(precise_volume, Decimal)
        # Verify precision is maintained in multiplication
        assert precise_volume != Decimal("0.123456789012")

    def test_result_type_chaining(self) -> None:
        """Test Result types can be chained in operations.

        Description of what the test covers:
        Verifies that Success and Failure types can be used in
        functional programming patterns and chained operations.

        Preconditions:
        - None.

        Steps:
        - Create Result type instances
        - Chain operations based on success/failure
        - Verify proper flow control

        Expected Result:
        - Result types should enable proper error handling chains
        """

        def safe_divide(a: float, b: float) -> SuccessOrFailure[float]:
            """Helper function that returns Success or Failure."""
            if b == 0:
                return Failure(ZeroDivisionError("Division by zero"))
            return Success(a / b)

        def safe_multiply(result: SuccessOrFailure[float], multiplier: float) -> SuccessOrFailure[float]:
            """Chain operation that handles previous result."""
            if isinstance(result, Failure):
                return result  # Pass through failure
            return Success(result.value * multiplier)

        # Test successful chain
        result1 = safe_divide(10.0, 2.0)
        result2 = safe_multiply(result1, 3.0)

        assert isinstance(result1, Success)
        assert result1.value == 5.0
        assert isinstance(result2, Success)
        assert result2.value == 15.0

        # Test failure chain
        result3 = safe_divide(10.0, 0.0)
        result4 = safe_multiply(result3, 3.0)

        assert isinstance(result3, Failure)
        assert isinstance(result3.error, ZeroDivisionError)
        assert isinstance(result4, Failure)
        assert result4.error == result3.error  # Same error passed through
