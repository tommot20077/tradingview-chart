import pytest

from asset_core.exceptions import (
    CoreError,
)
from asset_core.observability.trace_id import set_trace_id


@pytest.mark.integration
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
