"""Tests for enhanced exception functionality with trace ID."""

import sys
from collections.abc import Generator
from unittest.mock import patch

import pytest

from src.asset_core.asset_core.exceptions import (
    CircuitBreakerError,
    CoreError,
    DataValidationError,
    RateLimitError,
    ResourceExhaustedError,
    TraceIdExceptionHandler,
    create_traced_exception,
    enhance_exception_with_trace_id,
    install_global_exception_handler,
    uninstall_global_exception_handler,
)
from src.asset_core.asset_core.observability.trace_id import clear_trace_id, \
    set_trace_id


@pytest.mark.unit
class TestCoreErrorWithTraceId:
    """Test CoreError with trace ID functionality."""

    def test_core_error_auto_trace_id(self) -> None:
        """Test that CoreError automatically captures trace ID."""
        set_trace_id("test123")
        error = CoreError("Test error")

        assert error.trace_id == "test123"
        assert error.details["trace_id"] == "test123"

    def test_core_error_explicit_trace_id(self) -> None:
        """Test CoreError with explicit trace ID."""
        set_trace_id("current")
        error = CoreError("Test error", trace_id="explicit123")

        assert error.trace_id == "explicit123"
        assert error.details["trace_id"] == "explicit123"

    def test_core_error_no_trace_id(self) -> None:
        """Test CoreError when no trace ID is set."""
        clear_trace_id()
        error = CoreError("Test error")

        assert error.trace_id == "no-trace"
        assert error.details["trace_id"] == "no-trace"

    def test_core_error_str_representation(self) -> None:
        """Test string representation includes trace ID."""
        set_trace_id("test123")
        error = CoreError("Test error")

        error_str = str(error)
        assert "[test123]" in error_str
        assert "Test error" in error_str

    def test_core_error_repr_representation(self) -> None:
        """Test repr representation includes trace ID."""
        set_trace_id("test123")
        error = CoreError("Test error", error_code="TEST_ERROR")

        error_repr = repr(error)
        assert "trace_id='test123'" in error_repr
        assert "error_code='TEST_ERROR'" in error_repr
        assert "message='Test error'" in error_repr

    def test_core_error_no_trace_str(self) -> None:
        """Test string representation when trace ID is 'no-trace'."""
        clear_trace_id()
        error = CoreError("Test error")

        error_str = str(error)
        assert "[no-trace]" not in error_str
        assert "Test error" in error_str

    def test_core_error_with_details(self) -> None:
        """Test CoreError with additional details."""
        set_trace_id("test123")
        error = CoreError("Test error", details={"key": "value"})

        assert error.details["trace_id"] == "test123"
        assert error.details["key"] == "value"

        error_str = str(error)
        assert "[test123]" in error_str
        assert "key" in error_str
        assert "value" in error_str


@pytest.mark.unit
class TestSpecializedExceptions:
    """Test specialized exception classes."""

    def test_rate_limit_error_with_trace_id(self) -> None:
        """Test RateLimitError includes trace ID."""
        set_trace_id("rate_limit_test")
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        assert error.trace_id == "rate_limit_test"
        assert error.retry_after == 60
        assert error.details["retry_after"] == 60
        assert error.details["trace_id"] == "rate_limit_test"

    def test_data_validation_error_with_trace_id(self) -> None:
        """Test DataValidationError includes trace ID."""
        set_trace_id("validation_test")
        error = DataValidationError("Invalid value", field_name="test_field", field_value="invalid")

        assert error.trace_id == "validation_test"
        assert error.field_name == "test_field"
        assert error.field_value == "invalid"
        assert error.details["trace_id"] == "validation_test"
        assert error.details["field_name"] == "test_field"
        assert error.details["field_value"] == "invalid"

    def test_resource_exhausted_error_with_trace_id(self) -> None:
        """Test ResourceExhaustedError includes trace ID."""
        set_trace_id("resource_test")
        error = ResourceExhaustedError("Memory exhausted", resource_type="memory", current_usage=95.5, limit=100.0)

        assert error.trace_id == "resource_test"
        assert error.resource_type == "memory"
        assert error.current_usage == 95.5
        assert error.limit == 100.0
        assert error.details["trace_id"] == "resource_test"

    def test_circuit_breaker_error_with_trace_id(self) -> None:
        """Test CircuitBreakerError includes trace ID."""
        from datetime import datetime

        set_trace_id("circuit_test")
        retry_time = datetime.now()
        error = CircuitBreakerError(
            "Circuit breaker triggered",
            service_name="test_service",
            failure_count=5,
            failure_threshold=3,
            next_retry_time=retry_time,
        )

        assert error.trace_id == "circuit_test"
        assert error.service_name == "test_service"
        assert error.failure_count == 5
        assert error.failure_threshold == 3
        assert error.next_retry_time == retry_time
        assert error.details["trace_id"] == "circuit_test"


@pytest.mark.unit
class TestTracedExceptionCreation:
    """Test creation of traced exceptions."""

    def test_create_traced_core_error(self) -> None:
        """Test creating traced CoreError."""
        set_trace_id("traced_test")
        error = create_traced_exception(CoreError, "Test error")

        assert isinstance(error, CoreError)
        assert error.trace_id == "traced_test"
        assert error.message == "Test error"

    def test_create_traced_standard_exception(self) -> None:
        """Test creating traced standard exception."""
        set_trace_id("traced_standard")
        error = create_traced_exception(ValueError, "Invalid value")

        assert isinstance(error, ValueError)
        assert str(error) == "[traced_standard] Invalid value"

    def test_create_traced_exception_with_kwargs(self) -> None:
        """Test creating traced exception with additional kwargs."""
        set_trace_id("traced_kwargs")
        error = create_traced_exception(DataValidationError, "Invalid field", field_name="test_field")

        assert isinstance(error, DataValidationError)
        assert error.trace_id == "traced_kwargs"
        assert error.field_name == "test_field"


@pytest.mark.unit
class TestExceptionEnhancement:
    """Test exception enhancement functionality."""

    def test_enhance_core_error(self) -> None:
        """Test enhancing CoreError (should be no-op)."""
        set_trace_id("enhance_test")
        original_error = CoreError("Original error")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert enhanced_error.trace_id == "enhance_test"

    def test_enhance_standard_exception(self) -> None:
        """Test enhancing standard exception."""
        set_trace_id("enhance_standard")
        original_error = ValueError("Original message")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert str(enhanced_error) == "[enhance_standard] Original message"

    def test_enhance_exception_no_trace(self) -> None:
        """Test enhancing exception when no trace ID is set."""
        clear_trace_id()
        original_error = ValueError("Original message")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert str(enhanced_error) == "Original message"

    def test_enhance_exception_already_enhanced(self) -> None:
        """Test enhancing already enhanced exception."""
        set_trace_id("enhance_twice")
        original_error = ValueError("[enhance_twice] Already enhanced")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert str(enhanced_error) == "[enhance_twice] Already enhanced"


@pytest.mark.unit
class TestGlobalExceptionHandler:
    """Test global exception handler."""

    def test_install_uninstall_handler(self) -> None:
        """Test installing and uninstalling global exception handler."""
        original_hook = sys.excepthook

        install_global_exception_handler()
        assert sys.excepthook != original_hook

        uninstall_global_exception_handler()
        assert sys.excepthook == original_hook

    def test_handler_instance(self) -> None:
        """Test TraceIdExceptionHandler instance."""
        handler = TraceIdExceptionHandler()
        original_hook = sys.excepthook

        handler.install()
        assert sys.excepthook != original_hook

        handler.uninstall()
        assert sys.excepthook == original_hook

    def test_multiple_install_uninstall(self) -> None:
        """Test multiple install/uninstall cycles with separate handler instances."""
        original_hook = sys.excepthook

        handler1 = TraceIdExceptionHandler()
        handler2 = TraceIdExceptionHandler()

        handler1.install()
        first_hook = sys.excepthook
        assert first_hook != original_hook

        handler2.install()
        second_hook = sys.excepthook
        assert second_hook != first_hook

        handler2.uninstall()
        assert sys.excepthook == first_hook

        handler1.uninstall()
        assert sys.excepthook == original_hook

        handler1.uninstall()
        handler2.uninstall()

    def test_exception_handler_with_trace_id(self) -> None:
        """Test that exception handler adds trace ID."""
        set_trace_id("handler_test")
        handler = TraceIdExceptionHandler()

        import io

        captured_stderr = io.StringIO()

        with patch("sys.stderr", captured_stderr):
            handler._handle_exception(ValueError, ValueError("Test error"), None)

        output = captured_stderr.getvalue()
        assert "[handler_test]" in output

    def test_exception_handler_no_trace_id(self) -> None:
        """Test exception handler when no trace ID is set."""
        clear_trace_id()
        handler = TraceIdExceptionHandler()

        handler._handle_exception(ValueError, ValueError("Test error"), None)


@pytest.mark.unit
class TestInheritanceAndCompatibility:
    """Test inheritance and compatibility."""

    def test_exception_inheritance(self) -> None:
        """Test that enhanced exceptions maintain inheritance."""
        set_trace_id("inheritance_test")
        error = CoreError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, CoreError)
        assert hasattr(error, "trace_id")

    def test_exception_pickling(self) -> None:
        """Test that exceptions can be pickled/unpickled."""
        import pickle

        set_trace_id("pickle_test")
        original_error = CoreError("Pickle test", error_code="PICKLE")

        pickled = pickle.dumps(original_error)
        unpickled_error = pickle.loads(pickled)

        assert unpickled_error.message == original_error.message
        assert unpickled_error.error_code == original_error.error_code
        assert unpickled_error.trace_id == original_error.trace_id

    def test_exception_with_cause(self) -> None:
        """Test exception chaining with trace ID."""
        set_trace_id("chaining_test")

        try:
            try:
                raise ValueError("Root cause")
            except ValueError as e:
                raise CoreError("Wrapper error") from e
        except CoreError as wrapper:
            assert wrapper.trace_id == "chaining_test"
            assert isinstance(wrapper.__cause__, ValueError)
            assert str(wrapper.__cause__) == "Root cause"


@pytest.fixture(autouse=True)
def cleanup_trace_id() -> Generator[None, None, None]:
    """Cleanup trace ID and global handlers after each test."""
    yield
    clear_trace_id()
    uninstall_global_exception_handler()
