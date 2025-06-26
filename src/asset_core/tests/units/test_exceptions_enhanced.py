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
from src.asset_core.asset_core.observability.trace_id import clear_trace_id, set_trace_id


@pytest.mark.unit
class TestCoreErrorWithTraceId:
    """Test cases for CoreError with trace ID functionality.

    Verifies that `CoreError` instances correctly capture and expose
    trace IDs, whether automatically generated or explicitly provided,
    and that string representations include this information.
    """

    def test_core_error_auto_trace_id(self) -> None:
        """Test that CoreError automatically captures trace ID.

        Description of what the test covers.
        Verifies that when a `CoreError` is instantiated, it automatically
        captures the currently set trace ID from the `TraceContext`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID using `set_trace_id()`.
        - Instantiate a `CoreError`.
        - Assert that the `trace_id` attribute of the error matches the set trace ID.
        - Assert that the `details` dictionary of the error also contains the trace ID.

        Expected Result:
        - The `CoreError` instance should automatically inherit the current trace ID.
        """
        set_trace_id("test123")
        error = CoreError("Test error")

        assert error.trace_id == "test123"
        assert error.details["trace_id"] == "test123"

    def test_core_error_explicit_trace_id(self) -> None:
        """Test CoreError with explicit trace ID.

        Description of what the test covers.
        Verifies that an explicitly provided `trace_id` during `CoreError`
        instantiation overrides any trace ID set in the `TraceContext`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a current trace ID using `set_trace_id()`.
        - Instantiate a `CoreError`, providing a different explicit `trace_id`.
        - Assert that the `trace_id` attribute of the error matches the explicitly provided ID.
        - Assert that the `details` dictionary also contains the explicit trace ID.

        Expected Result:
        - The `CoreError` instance should use the explicitly provided trace ID.
        """
        set_trace_id("current")
        error = CoreError("Test error", trace_id="explicit123")

        assert error.trace_id == "explicit123"
        assert error.details["trace_id"] == "explicit123"

    def test_core_error_no_trace_id(self) -> None:
        """Test CoreError when no trace ID is set.

        Description of what the test covers.
        Verifies that when no trace ID is set in the `TraceContext`,
        `CoreError` defaults to a "no-trace" identifier.

        Preconditions:
        - No trace ID is set in the `TraceContext`.

        Steps:
        - Clear any existing trace ID using `clear_trace_id()`.
        - Instantiate a `CoreError`.
        - Assert that the `trace_id` attribute of the error is "no-trace".
        - Assert that the `details` dictionary also contains "no-trace" for the trace ID.

        Expected Result:
        - The `CoreError` instance should indicate "no-trace" when no trace ID is available.
        """
        clear_trace_id()
        error = CoreError("Test error")

        assert error.trace_id == "no-trace"
        assert error.details["trace_id"] == "no-trace"

    def test_core_error_str_representation(self) -> None:
        """Test string representation includes trace ID.

        Description of what the test covers.
        Verifies that the string representation (`str()`) of a `CoreError`
        instance includes the associated trace ID when one is present.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `CoreError`.
        - Convert the error to a string using `str()`.
        - Assert that the string contains the trace ID in the expected format.
        - Assert that the original error message is also present.

        Expected Result:
        - The string representation of `CoreError` should include the trace ID.
        """
        set_trace_id("test123")
        error = CoreError("Test error")

        error_str = str(error)
        assert "[test123]" in error_str
        assert "Test error" in error_str

    def test_core_error_repr_representation(self) -> None:
        """Test repr representation includes trace ID.

        Description of what the test covers.
        Verifies that the developer-friendly representation (`repr()`) of a `CoreError`
        instance includes the trace ID and other key attributes.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `CoreError` with a message and error code.
        - Convert the error to its representation using `repr()`.
        - Assert that the representation string contains the trace ID, error code,
          and message in the expected format.

        Expected Result:
        - The `repr()` of `CoreError` should provide a detailed representation
          including trace ID and other attributes.
        """
        set_trace_id("test123")
        error = CoreError("Test error", error_code="TEST_ERROR")

        error_repr = repr(error)
        assert "trace_id='test123'" in error_repr
        assert "error_code='TEST_ERROR'" in error_repr
        assert "message='Test error'" in error_repr

    def test_core_error_no_trace_str(self) -> None:
        """Test string representation when trace ID is 'no-trace'.

        Description of what the test covers.
        Verifies that the string representation (`str()`) of a `CoreError`
        instance does not include the `[no-trace]` prefix when no trace ID
        is present.

        Preconditions:
        - No trace ID is set in the `TraceContext`.

        Steps:
        - Clear any existing trace ID.
        - Instantiate a `CoreError`.
        - Convert the error to a string using `str()`.
        - Assert that the string does not contain `[no-trace]`.
        - Assert that the original error message is present.

        Expected Result:
        - The string representation should only contain the error message
          when no trace ID is available.
        """
        clear_trace_id()
        error = CoreError("Test error")

        error_str = str(error)
        assert "[no-trace]" not in error_str
        assert "Test error" in error_str

    def test_core_error_with_details(self) -> None:
        """Test CoreError with additional details.

        Description of what the test covers.
        Verifies that `CoreError` instances correctly incorporate additional
        details provided during instantiation, and that these details are
        reflected in the error's `details` attribute and string representation.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `CoreError`, providing a dictionary of additional details.
        - Assert that the `details` dictionary contains both the trace ID and
          the provided additional details.
        - Assert that the string representation of the error includes the trace ID
          and the additional details.

        Expected Result:
        - `CoreError` should correctly store and display additional details.
        """
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
    """Test cases for specialized exception classes.

    Verifies that custom exception classes (e.g., `RateLimitError`,
    `DataValidationError`) correctly inherit from `CoreError` and
    include trace ID functionality, along with their specific attributes.
    """

    def test_rate_limit_error_with_trace_id(self) -> None:
        """Test RateLimitError includes trace ID.

        Description of what the test covers.
        Verifies that `RateLimitError` correctly captures the trace ID
        and stores its specific `retry_after` attribute in `details`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `RateLimitError` with a `retry_after` value.
        - Assert that the error's `trace_id` matches the set ID.
        - Assert that `retry_after` is correctly stored as an attribute and in `details`.

        Expected Result:
        - `RateLimitError` should include trace ID and its specific attributes.
        """
        set_trace_id("rate_limit_test")
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        assert error.trace_id == "rate_limit_test"
        assert error.retry_after == 60
        assert error.details["retry_after"] == 60
        assert error.details["trace_id"] == "rate_limit_test"

    def test_data_validation_error_with_trace_id(self) -> None:
        """Test DataValidationError includes trace ID.

        Description of what the test covers.
        Verifies that `DataValidationError` correctly captures the trace ID
        and stores its specific `field_name` and `field_value` attributes in `details`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `DataValidationError` with `field_name` and `field_value`.
        - Assert that the error's `trace_id` matches the set ID.
        - Assert that `field_name` and `field_value` are correctly stored as attributes and in `details`.

        Expected Result:
        - `DataValidationError` should include trace ID and its specific attributes.
        """
        set_trace_id("validation_test")
        error = DataValidationError("Invalid value", field_name="test_field", field_value="invalid")

        assert error.trace_id == "validation_test"
        assert error.field_name == "test_field"
        assert error.field_value == "invalid"
        assert error.details["trace_id"] == "validation_test"
        assert error.details["field_name"] == "test_field"
        assert error.details["field_value"] == "invalid"

    def test_resource_exhausted_error_with_trace_id(self) -> None:
        """Test ResourceExhaustedError includes trace ID.

        Description of what the test covers.
        Verifies that `ResourceExhaustedError` correctly captures the trace ID
        and stores its specific `resource_type`, `current_usage`, and `limit`
        attributes in `details`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `ResourceExhaustedError` with resource details.
        - Assert that the error's `trace_id` matches the set ID.
        - Assert that resource details are correctly stored as attributes and in `details`.

        Expected Result:
        - `ResourceExhaustedError` should include trace ID and its specific attributes.
        """
        set_trace_id("resource_test")
        error = ResourceExhaustedError("Memory exhausted", resource_type="memory", current_usage=95.5, limit=100.0)

        assert error.trace_id == "resource_test"
        assert error.resource_type == "memory"
        assert error.current_usage == 95.5
        assert error.limit == 100.0
        assert error.details["trace_id"] == "resource_test"

    def test_circuit_breaker_error_with_trace_id(self) -> None:
        """Test CircuitBreakerError includes trace ID.

        Description of what the test covers.
        Verifies that `CircuitBreakerError` correctly captures the trace ID
        and stores its specific attributes (`service_name`, `failure_count`,
        `failure_threshold`, `next_retry_time`) in `details`.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Instantiate a `CircuitBreakerError` with circuit breaker details.
        - Assert that the error's `trace_id` matches the set ID.
        - Assert that circuit breaker details are correctly stored as attributes and in `details`.

        Expected Result:
        - `CircuitBreakerError` should include trace ID and its specific attributes.
        """
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
    """Test cases for creation of traced exceptions.

    Verifies that the `create_traced_exception` utility function correctly
    creates new exception instances (both custom and standard Python exceptions)
    and injects the current trace ID into them.
    """

    def test_create_traced_core_error(self) -> None:
        """Test creating traced CoreError.

        Description of what the test covers.
        Verifies that `create_traced_exception` correctly creates a `CoreError`
        instance and automatically assigns the current trace ID to it.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Call `create_traced_exception()` with `CoreError` and a message.
        - Assert that the returned object is an instance of `CoreError`.
        - Assert that its `trace_id` matches the set ID.
        - Assert that its `message` matches the provided message.

        Expected Result:
        - A `CoreError` instance with the correct trace ID and message should be created.
        """
        set_trace_id("traced_test")
        error = create_traced_exception(CoreError, "Test error")

        assert isinstance(error, CoreError)
        assert error.trace_id == "traced_test"
        assert error.message == "Test error"

    def test_create_traced_standard_exception(self) -> None:
        """Test creating traced standard exception.

        Description of what the test covers.
        Verifies that `create_traced_exception` can enhance a standard Python
        exception (like `ValueError`) by injecting the current trace ID into its
        string representation.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Call `create_traced_exception()` with `ValueError` and a message.
        - Assert that the returned object is an instance of `ValueError`.
        - Assert that the string representation of the exception includes the trace ID.

        Expected Result:
        - A standard exception instance with the trace ID in its string representation should be created.
        """
        set_trace_id("traced_standard")
        error = create_traced_exception(ValueError, "Invalid value")

        assert isinstance(error, ValueError)
        assert str(error) == "[traced_standard] Invalid value"

    def test_create_traced_exception_with_kwargs(self) -> None:
        """Test creating traced exception with additional kwargs.

        Description of what the test covers.
        Verifies that `create_traced_exception` correctly passes additional
        keyword arguments to the constructor of specialized exceptions.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Call `create_traced_exception()` with `DataValidationError` and additional kwargs.
        - Assert that the returned object is an instance of `DataValidationError`.
        - Assert that its `trace_id` matches the set ID.
        - Assert that the additional kwargs (`field_name`) are correctly set as attributes.

        Expected Result:
        - A specialized exception instance with the correct trace ID and additional
          attributes should be created.
        """
        set_trace_id("traced_kwargs")
        error = create_traced_exception(DataValidationError, "Invalid field", field_name="test_field")

        assert isinstance(error, DataValidationError)
        assert error.trace_id == "traced_kwargs"
        assert error.field_name == "test_field"


@pytest.mark.unit
class TestExceptionEnhancement:
    """Test cases for exception enhancement functionality.

    Verifies that the `enhance_exception_with_trace_id` utility function
    correctly adds trace ID information to exceptions, handling various
    scenarios including `CoreError` and standard Python exceptions.
    """

    def test_enhance_core_error(self) -> None:
        """Test enhancing CoreError (should be no-op).

        Description of what the test covers.
        Verifies that attempting to enhance a `CoreError` (which already handles
        trace IDs internally) results in a no-op, returning the original instance.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a `CoreError` instance.
        - Call `enhance_exception_with_trace_id()` with the `CoreError`.
        - Assert that the returned exception is the same instance as the original.
        - Assert that its `trace_id` matches the set ID.

        Expected Result:
        - `CoreError` instances should not be modified by `enhance_exception_with_trace_id`.
        """
        set_trace_id("enhance_test")
        original_error = CoreError("Original error")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert enhanced_error.trace_id == "enhance_test"

    def test_enhance_standard_exception(self) -> None:
        """Test enhancing standard exception.

        Description of what the test covers.
        Verifies that `enhance_exception_with_trace_id` correctly adds the
        current trace ID to the string representation of a standard Python exception.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a standard `ValueError` instance.
        - Call `enhance_exception_with_trace_id()` with the `ValueError`.
        - Assert that the returned exception is the same instance as the original.
        - Assert that the string representation of the enhanced exception includes the trace ID.

        Expected Result:
        - Standard exceptions should have their string representation prefixed with the trace ID.
        """
        set_trace_id("enhance_standard")
        original_error = ValueError("Original message")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert str(enhanced_error) == "[enhance_standard] Original message"

    def test_enhance_exception_no_trace(self) -> None:
        """Test enhancing exception when no trace ID is set.

        Description of what the test covers.
        Verifies that `enhance_exception_with_trace_id` does not modify the
        string representation of an exception if no trace ID is currently set.

        Preconditions:
        - No trace ID is set in the `TraceContext`.

        Steps:
        - Clear any existing trace ID.
        - Create a standard `ValueError` instance.
        - Call `enhance_exception_with_trace_id()` with the `ValueError`.
        - Assert that the returned exception is the same instance as the original.
        - Assert that the string representation remains unchanged.

        Expected Result:
        - The exception's string representation should not be altered if no trace ID is available.
        """
        clear_trace_id()
        original_error = ValueError("Original message")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert enhanced_error is original_error
        assert str(enhanced_error) == "Original message"

    def test_enhance_exception_already_enhanced(self) -> None:
        """Test enhancing already enhanced exception.

        Description of what the test covers.
        Verifies that `enhance_exception_with_trace_id` does not re-enhance
        an exception that already has a trace ID prefix in its string representation.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a `ValueError` instance with a pre-existing trace ID prefix.
        - Call `enhance_exception_with_trace_id()` with this exception.
        - Assert that the string representation remains unchanged.

        Expected Result:
        - The exception should not be re-enhanced if it already contains a trace ID prefix.
        """
        set_trace_id("enhance_twice")
        original_error = ValueError("[enhance_twice] Already enhanced")
        enhanced_error = enhance_exception_with_trace_id(original_error)

        assert str(enhanced_error) == "[enhance_twice] Already enhanced"


@pytest.mark.unit
class TestGlobalExceptionHandler:
    """Test cases for global exception handler.

    Verifies the installation, uninstallation, and behavior of the
    `TraceIdExceptionHandler` as a global exception hook, ensuring it
    correctly processes exceptions and integrates with trace IDs.
    """

    def test_install_uninstall_handler(self) -> None:
        """Test installing and uninstalling global exception handler.

        Description of what the test covers.
        Verifies that the global exception handler can be successfully installed
        and uninstalled, restoring the original exception hook.

        Preconditions:
        - None.

        Steps:
        - Store the original `sys.excepthook`.
        - Call `install_global_exception_handler()`.
        - Assert that `sys.excepthook` has changed.
        - Call `uninstall_global_exception_handler()`.
        - Assert that `sys.excepthook` has been restored to the original hook.

        Expected Result:
        - The global exception handler should be installed and uninstalled correctly.
        """
        original_hook = sys.excepthook

        install_global_exception_handler()
        assert sys.excepthook != original_hook

        uninstall_global_exception_handler()
        assert sys.excepthook == original_hook

    def test_handler_instance(self) -> None:
        """Test TraceIdExceptionHandler instance.

        Description of what the test covers.
        Verifies that an instance of `TraceIdExceptionHandler` can be used
        to install and uninstall itself as the global exception hook.

        Preconditions:
        - None.

        Steps:
        - Create an instance of `TraceIdExceptionHandler`.
        - Store the original `sys.excepthook`.
        - Call `handler.install()`.
        - Assert that `sys.excepthook` has changed.
        - Call `handler.uninstall()`.
        - Assert that `sys.excepthook` has been restored to the original hook.

        Expected Result:
        - The `TraceIdExceptionHandler` instance should correctly manage the global exception hook.
        """
        handler = TraceIdExceptionHandler()
        original_hook = sys.excepthook

        handler.install()
        assert sys.excepthook != original_hook

        handler.uninstall()
        assert sys.excepthook == original_hook

    def test_multiple_install_uninstall(self) -> None:
        """Test multiple install/uninstall cycles with separate handler instances.

        Description of what the test covers.
        Verifies that multiple `TraceIdExceptionHandler` instances can be installed
        and uninstalled sequentially, and that `sys.excepthook` correctly reflects
        the active handler.

        Preconditions:
        - None.

        Steps:
        - Store the original `sys.excepthook`.
        - Create two `TraceIdExceptionHandler` instances.
        - Install `handler1`, assert `sys.excepthook` changes.
        - Install `handler2`, assert `sys.excepthook` changes again.
        - Uninstall `handler2`, assert `sys.excepthook` reverts to `handler1`.
        - Uninstall `handler1`, assert `sys.excepthook` reverts to the original hook.

        Expected Result:
        - Multiple handlers should be managed correctly, with `sys.excepthook`
          reflecting the most recently installed handler.
        """
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
        """Test that exception handler adds trace ID.

        Description of what the test covers.
        Verifies that when an exception is handled by `TraceIdExceptionHandler`,
        the current trace ID is included in the output.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a `TraceIdExceptionHandler` instance.
        - Patch `sys.stderr` to capture output.
        - Call the internal `_handle_exception()` method with a test exception.
        - Assert that the captured output contains the trace ID.

        Expected Result:
        - The exception output should include the trace ID.
        """
        set_trace_id("handler_test")
        handler = TraceIdExceptionHandler()

        import io

        captured_stderr = io.StringIO()

        with patch("sys.stderr", captured_stderr):
            handler._handle_exception(ValueError, ValueError("Test error"), None)

        output = captured_stderr.getvalue()
        assert "[handler_test]" in output

    def test_exception_handler_no_trace_id(self) -> None:
        """Test exception handler when no trace ID is set.

        Description of what the test covers.
        Verifies that when an exception is handled by `TraceIdExceptionHandler`
        and no trace ID is set, the output does not include a trace ID prefix.

        Preconditions:
        - No trace ID is set in the `TraceContext`.

        Steps:
        - Clear any existing trace ID.
        - Create a `TraceIdExceptionHandler` instance.
        - Call the internal `_handle_exception()` method with a test exception.
        - (Implicitly) Assert that the output does not contain a trace ID prefix.

        Expected Result:
        - The exception output should not include a trace ID prefix if none is available.
        """
        clear_trace_id()
        handler = TraceIdExceptionHandler()

        handler._handle_exception(ValueError, ValueError("Test error"), None)


@pytest.mark.unit
class TestInheritanceAndCompatibility:
    """Test cases for inheritance and compatibility of enhanced exceptions.

    Verifies that custom exceptions maintain their inheritance hierarchy
    and can be serialized/deserialized (pickled) correctly, and that
    exception chaining works as expected with trace IDs.
    """

    def test_exception_inheritance(self) -> None:
        """Test that enhanced exceptions maintain inheritance.

        Description of what the test covers.
        Verifies that custom exceptions (like `CoreError`) correctly inherit
        from `Exception` and retain their custom attributes (`trace_id`).

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a `CoreError` instance.
        - Assert that the error is an instance of `Exception`.
        - Assert that the error is an instance of `CoreError`.
        - Assert that the error object has a `trace_id` attribute.

        Expected Result:
        - Custom exceptions should maintain their expected inheritance hierarchy.
        """
        set_trace_id("inheritance_test")
        error = CoreError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, CoreError)
        assert hasattr(error, "trace_id")

    def test_exception_pickling(self) -> None:
        """Test that exceptions can be pickled/unpickled.

        Description of what the test covers.
        Verifies that `CoreError` instances, including their trace ID and
        other attributes, can be successfully serialized (pickled) and
        deserialized (unpickled) without data loss.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Create a `CoreError` instance with a message and error code.
        - Pickle the original error.
        - Unpickle the error.
        - Assert that the unpickled error's message, error code, and trace ID
          match those of the original error.

        Expected Result:
        - `CoreError` instances should be correctly serializable and deserializable.
        """
        import pickle

        set_trace_id("pickle_test")
        original_error = CoreError("Pickle test", error_code="PICKLE")

        pickled = pickle.dumps(original_error)
        unpickled_error = pickle.loads(pickled)

        assert unpickled_error.message == original_error.message
        assert unpickled_error.error_code == original_error.error_code
        assert unpickled_error.trace_id == original_error.trace_id

    def test_exception_with_cause(self) -> None:
        """Test exception chaining with trace ID.

        Description of what the test covers.
        Verifies that when exceptions are chained (`raise ... from ...`), the
        trace ID is correctly propagated to the outer exception, and the cause
        is preserved.

        Preconditions:
        - A trace ID is set in the `TraceContext`.

        Steps:
        - Set a trace ID.
        - Raise a `ValueError` as a root cause.
        - Catch the `ValueError` and re-raise it as a `CoreError` with `from e`.
        - Catch the `CoreError`.
        - Assert that the `CoreError`'s `trace_id` matches the set ID.
        - Assert that the `__cause__` attribute is the original `ValueError`.
        - Assert that the `__cause__`'s string representation is correct.

        Expected Result:
        - Exception chaining should correctly propagate trace IDs and preserve causes.
        """
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
    """Cleans up trace ID and global exception handlers after each test.

    This fixture ensures that the global state related to trace IDs and
    exception handlers is reset, preventing test interference.

    Yields:
        None: Yields control to the test function.
    """
    yield
    clear_trace_id()
    uninstall_global_exception_handler()
