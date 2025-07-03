"""Tests for enhanced logging functionality with trace ID."""

import json
import sys
from collections.abc import Generator
from io import StringIO
from typing import Any

import pytest
from loguru import logger

from asset_core.exceptions import CoreError
from asset_core.observability.logging import (
    Record,
    TraceableLogger,
    create_traced_logger,
    log_exception_with_context,
    log_with_trace_id,
    setup_logging,
    trace_id_patcher,
)
from asset_core.observability.trace_id import clear_trace_id, set_trace_id


@pytest.mark.integration
class TestTraceIdPatcher:
    """Test cases for trace ID patcher functionality.

    Verifies that the `trace_id_patcher` correctly injects trace IDs
    into log records, handling cases where a trace ID is present, absent,
    or embedded within an exception.
    """

    def test_trace_id_patcher_with_trace_id(self) -> None:
        """Test patcher adds trace ID when available.

        Description of what the test covers:
        Verifies that the `trace_id_patcher` correctly adds the current trace ID
        to log record extra fields when a trace ID is set.

        Preconditions:
        - Trace ID is set in the context.
        - Empty record with extra field.

        Steps:
        - Set a specific trace ID.
        - Create log record with empty extra dict.
        - Apply `trace_id_patcher` to record.

        Expected Result:
        - Record extra should contain the set trace ID.
        """
        set_trace_id("patcher_test")

        from typing import cast

        record: dict[str, dict[str, str]] = {"extra": {}}
        trace_id_patcher(cast(Record, record))

        assert record["extra"]["trace_id"] == "patcher_test"

    def test_trace_id_patcher_no_trace_id(self) -> None:
        """Test patcher adds 'no-trace' when no trace ID is set.

        Description of what the test covers:
        Verifies that the `trace_id_patcher` adds default 'no-trace' value
        when no trace ID is available in the context.

        Preconditions:
        - No trace ID set in context.
        - Empty record with extra field.

        Steps:
        - Clear any existing trace ID.
        - Create log record with empty extra dict.
        - Apply `trace_id_patcher` to record.

        Expected Result:
        - Record extra should contain 'no-trace' as trace ID.
        """
        clear_trace_id()

        from typing import cast

        record: dict[str, dict[str, str]] = {"extra": {}}
        trace_id_patcher(cast(Record, record))

        assert record["extra"]["trace_id"] == "no-trace"

    def test_trace_id_patcher_with_exception(self) -> None:
        """Test patcher extracts trace ID from exception.

        Description of what the test covers:
        Verifies that the `trace_id_patcher` can extract trace ID from
        `CoreError` exceptions and add both current and exception trace IDs.

        Preconditions:
        - Current trace ID is set.
        - `CoreError` with different trace ID exists.
        - Log record with exception present.

        Steps:
        - Set current trace ID.
        - Create `CoreError` with different trace ID.
        - Create log record with exception.
        - Apply `trace_id_patcher` to record.

        Expected Result:
        - Record should contain both current and exception trace IDs.
        """
        set_trace_id("current_trace")
        error = CoreError("Test error", trace_id="exception_trace")

        # Mock exception object
        class MockException:
            def __init__(self, value: Exception) -> None:
                self.value = value
                self.type = type(value)

        record: dict[str, Any] = {"extra": {}, "exception": MockException(error)}

        from typing import cast

        trace_id_patcher(cast(Record, record))

        assert isinstance(record["extra"], dict)
        assert record["extra"]["trace_id"] == "current_trace"
        assert record["extra"]["exception_trace_id"] == "exception_trace"

    def test_trace_id_patcher_exception_no_trace_id(self) -> None:
        """Test patcher with exception that has no trace ID.

        Description of what the test covers:
        Verifies that the `trace_id_patcher` handles standard exceptions
        that don't have trace ID attributes correctly.

        Preconditions:
        - Current trace ID is set.
        - Standard exception (not `CoreError`) exists.
        - Log record with exception present.

        Steps:
        - Set current trace ID.
        - Create standard `ValueError`.
        - Create log record with exception.
        - Apply `trace_id_patcher` to record.

        Expected Result:
        - Record should contain current trace ID only.
        - No `exception_trace_id` should be added.
        """
        set_trace_id("current_trace")
        error = ValueError("Standard error")

        class MockException:
            def __init__(self, value: Exception) -> None:
                self.value = value
                self.type = type(value)

        record: dict[str, Any] = {"extra": {}, "exception": MockException(error)}

        from typing import cast

        trace_id_patcher(cast(Record, record))

        assert isinstance(record["extra"], dict)
        assert record["extra"]["trace_id"] == "current_trace"
        assert "exception_trace_id" not in record["extra"]


@pytest.mark.integration
class TestLogWithTraceId:
    """Test cases for `log_with_trace_id` function.

    Verifies that the `log_with_trace_id` utility function correctly logs
    messages, incorporating explicit or current trace IDs and additional fields.
    """

    def test_log_with_explicit_trace_id(self) -> None:
        """Test logging with explicit trace ID.

        Description of what the test covers:
        Verifies that `log_with_trace_id` function correctly logs messages
        when an explicit trace ID is provided.

        Preconditions:
        - Logger configured with `trace_id_patcher`.
        - Output capture set up.

        Steps:
        - Configure logger with trace ID formatting.
        - Call `log_with_trace_id` with explicit trace ID.
        - Verify output contains trace ID and message.

        Expected Result:
        - Log output should contain the explicit trace ID and message.
        """
        # Set up logging to capture output
        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} {message}")

        log_with_trace_id("INFO", "Test message", trace_id="explicit_test")

        output_str = output.getvalue()
        assert "explicit_test" in output_str
        assert "Test message" in output_str

    def test_log_with_current_trace_id(self) -> None:
        """Test logging with current trace ID.

        Description of what the test covers:
        Verifies that `log_with_trace_id` function uses the current
        trace ID when no explicit trace ID is provided.

        Preconditions:
        - Current trace ID is set.
        - Logger configured with `trace_id_patcher`.

        Steps:
        - Set current trace ID.
        - Configure logger with trace ID formatting.
        - Call `log_with_trace_id` without explicit trace ID.
        - Verify output contains current trace ID.

        Expected Result:
        - Log output should contain the current trace ID and message.
        """
        set_trace_id("current_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} {message}")

        log_with_trace_id("INFO", "Test message")

        output_str = output.getvalue()
        assert "current_test" in output_str
        assert "Test message" in output_str

    def test_log_with_extra_fields(self) -> None:
        """Test logging with additional fields.

        Description of what the test covers:
        Verifies that `log_with_trace_id` function correctly handles
        additional extra fields along with trace ID.

        Preconditions:
        - Current trace ID is set.
        - Logger configured for JSON serialization.

        Steps:
        - Set current trace ID.
        - Configure logger for JSON output.
        - Call `log_with_trace_id` with extra fields.
        - Parse and verify JSON output.

        Expected Result:
        - Log output should contain trace ID and extra fields in JSON.
        """
        set_trace_id("extra_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} {extra[user_id]} {message}")

        log_with_trace_id("INFO", "Test message", user_id="user123")

        output_str = output.getvalue()
        assert "extra_test" in output_str
        assert "user123" in output_str
        assert "Test message" in output_str


@pytest.mark.integration
class TestLogExceptionWithContext:
    """Test cases for `log_exception_with_context` function.

    Verifies that the `log_exception_with_context` utility function correctly
    logs exceptions with rich context, including trace IDs, error codes,
    and custom details.
    """

    def test_log_core_error_with_context(self) -> None:
        """Test logging CoreError with full context.

        Description of what the test covers:
        Verifies that `log_exception_with_context` function properly logs
        `CoreError` exceptions with all context information.

        Preconditions:
        - Trace ID is set.
        - `CoreError` with error code and details exists.
        - Logger configured for JSON serialization.

        Steps:
        - Set trace ID.
        - Create `CoreError` with error code and details.
        - Configure logger for JSON output.
        - Call `log_exception_with_context`.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain message, exception type, error code, and details.
        """
        set_trace_id("exception_test")
        error = CoreError("Test error", error_code="TEST_ERROR", details={"key": "value"})

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, serialize=True)

        log_exception_with_context(error, "ERROR", "Custom message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Custom message"
        assert log_data["record"]["extra"]["exception_type"] == "CoreError"
        assert log_data["record"]["extra"]["error_code"] == "TEST_ERROR"
        assert log_data["record"]["extra"]["exception_trace_id"] == "exception_test"
        assert log_data["record"]["extra"]["key"] == "value"

    def test_log_standard_exception_with_context(self) -> None:
        """Test logging standard exception with context.

        Description of what the test covers:
        Verifies that `log_exception_with_context` function handles
        standard Python exceptions correctly.

        Preconditions:
        - Trace ID is set.
        - Standard exception (`ValueError`) exists.
        - Logger configured for JSON serialization.

        Steps:
        - Set trace ID.
        - Create standard `ValueError`.
        - Configure logger for JSON output.
        - Call `log_exception_with_context` without custom message.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain exception message and type information.
        """
        set_trace_id("std_exception_test")
        error = ValueError("Standard error")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, serialize=True)

        log_exception_with_context(error, "ERROR")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert "Standard error" in log_data["text"]
        assert log_data["record"]["extra"]["exception_type"] == "ValueError"
        assert "error_code" not in log_data["record"]["extra"]
        assert "exception_trace_id" not in log_data["record"]["extra"]

    def test_log_exception_default_message(self) -> None:
        """Test logging exception with default message.

        Description of what the test covers:
        Verifies that `log_exception_with_context` function uses a default
        message format when no custom message is provided.

        Preconditions:
        - Standard exception exists.
        - Logger configured for simple output.

        Steps:
        - Create standard `ValueError`.
        - Configure logger with simple formatting.
        - Call `log_exception_with_context` without custom message or level.
        - Verify output contains default message format.

        Expected Result:
        - Log output should contain 'Exception occurred:' prefix with error message.
        """
        error = ValueError("Test error")

        output = StringIO()
        logger.remove()
        logger.add(output, format="{message}")

        log_exception_with_context(error)

        output_str = output.getvalue()
        assert "Exception occurred: Test error" in output_str


@pytest.mark.integration
class TestCreateTracedLogger:
    """Test cases for `create_traced_logger` function.

    Verifies that the `create_traced_logger` utility function correctly
    creates Loguru logger instances that automatically include trace IDs
    and additional default fields in log messages.
    """

    def test_create_traced_logger_basic(self) -> None:
        """Test creating traced logger with basic functionality.

        Description of what the test covers:
        Verifies that `create_traced_logger` function creates a logger
        that automatically includes component information.

        Preconditions:
        - Trace ID is set.
        - Logger system is configured.

        Steps:
        - Set trace ID.
        - Create traced logger with component name.
        - Configure output capture.
        - Log a message.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain message and component information.
        """
        set_trace_id("traced_logger_test")

        traced_logger = create_traced_logger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        traced_logger.info("Test message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Test message"
        assert log_data["record"]["extra"]["component"] == "test_component"

    def test_create_traced_logger_with_fields(self) -> None:
        """Test creating traced logger with default fields.

        Description of what the test covers:
        Verifies that `create_traced_logger` function correctly handles
        additional default fields that are included in all log messages.

        Preconditions:
        - Trace ID is set.
        - Logger system is configured.

        Steps:
        - Set trace ID.
        - Create traced logger with component name and additional fields.
        - Configure output capture.
        - Log a message.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain message, component, and additional fields.
        """
        set_trace_id("traced_logger_fields_test")

        traced_logger = create_traced_logger("test_component", service="test_service", version="1.0.0")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        traced_logger.info("Test message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Test message"
        assert log_data["record"]["extra"]["component"] == "test_component"
        assert log_data["record"]["extra"]["service"] == "test_service"
        assert log_data["record"]["extra"]["version"] == "1.0.0"


@pytest.mark.integration
class TestTraceableLogger:
    """Test cases for `TraceableLogger` class.

    Verifies that `TraceableLogger` instances correctly ensure trace ID presence
    and provide convenient logging methods across different log levels and scenarios.
    """

    def test_traceable_logger_debug(self) -> None:
        """Test TraceableLogger debug method.

        Description of what the test covers:
        Verifies that the `debug` method of `TraceableLogger` correctly logs
        messages at the DEBUG level.

        Preconditions:
        - Trace ID is set.
        - Logger configured to capture DEBUG level output.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Call `debug` method with a message.
        - Verify output contains DEBUG level and the message.

        Expected Result:
        - Log output should contain the DEBUG level and the message.
        """
        set_trace_id("traceable_debug")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="DEBUG", format="{level} {message}")

        traceable_logger.debug("Debug message")

        output_str = output.getvalue()
        assert "DEBUG" in output_str
        assert "Debug message" in output_str

    def test_traceable_logger_info(self) -> None:
        """Test TraceableLogger info method.

        Description of what the test covers:
        Verifies that the `info` method of `TraceableLogger` correctly logs
        messages at the INFO level.

        Preconditions:
        - Trace ID is set.
        - Logger configured to capture INFO level output.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Call `info` method with a message.
        - Verify output contains INFO level and the message.

        Expected Result:
        - Log output should contain the INFO level and the message.
        """
        set_trace_id("traceable_info")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="INFO", format="{level} {message}")

        traceable_logger.info("Info message")

        output_str = output.getvalue()
        assert "INFO" in output_str
        assert "Info message" in output_str

    def test_traceable_logger_warning(self) -> None:
        """Test TraceableLogger warning method.

        Description of what the test covers:
        Verifies that the `warning` method of `TraceableLogger` correctly logs
        messages at the WARNING level.

        Preconditions:
        - Trace ID is set.
        - Logger configured to capture WARNING level output.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Call `warning` method with a message.
        - Verify output contains WARNING level and the message.

        Expected Result:
        - Log output should contain the WARNING level and the message.
        """
        set_trace_id("traceable_warning")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="WARNING", format="{level} {message}")

        traceable_logger.warning("Warning message")

        output_str = output.getvalue()
        assert "WARNING" in output_str
        assert "Warning message" in output_str

    def test_traceable_logger_error_with_exception(self) -> None:
        """Test TraceableLogger error method with exception.

        Description of what the test covers:
        Verifies that the `error` method of `TraceableLogger` correctly logs
        exceptions, including their type and error code, when a `CoreError`
        is provided.

        Preconditions:
        - Trace ID is set.
        - `CoreError` instance with error code exists.
        - Logger configured for JSON serialization.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Create `CoreError` instance.
        - Configure output capture.
        - Call `error` method with a message and the exception.
        - Parse and verify JSON output contains exception type and error code.

        Expected Result:
        - Log output should contain the error message, exception type, and error code.
        """
        set_trace_id("traceable_error")

        traceable_logger = TraceableLogger("test_component")
        error = CoreError("Test error", error_code="TEST_ERROR")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        traceable_logger.error("Error occurred", exc=error)

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Error occurred"
        assert log_data["record"]["extra"]["exception_type"] == "CoreError"
        assert log_data["record"]["extra"]["error_code"] == "TEST_ERROR"

    def test_traceable_logger_error_without_exception(self) -> None:
        """Test TraceableLogger error method without exception.

        Description of what the test covers:
        Verifies that the `error` method of `TraceableLogger` correctly logs
        messages at the ERROR level even when no exception is provided.

        Preconditions:
        - Trace ID is set.
        - Logger configured to capture ERROR level output.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Call `error` method with a message but no exception.
        - Verify output contains ERROR level and the message.

        Expected Result:
        - Log output should contain the ERROR level and the message.
        """
        set_trace_id("traceable_error_no_exc")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="ERROR", format="{level} {message}")

        traceable_logger.error("Simple error message")

        output_str = output.getvalue()
        assert "ERROR" in output_str
        assert "Simple error message" in output_str

    def test_traceable_logger_critical(self) -> None:
        """Test TraceableLogger critical method.

        Description of what the test covers:
        Verifies that the `critical` method of `TraceableLogger` correctly logs
        messages at the CRITICAL level.

        Preconditions:
        - Trace ID is set.
        - Logger configured to capture CRITICAL level output.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Call `critical` method with a message.
        - Verify output contains CRITICAL level and the message.

        Expected Result:
        - Log output should contain the CRITICAL level and the message.
        """
        set_trace_id("traceable_critical")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="CRITICAL", format="{level} {message}")

        traceable_logger.critical("Critical message")

        output_str = output.getvalue()
        assert "CRITICAL" in output_str
        assert "Critical message" in output_str

    def test_traceable_logger_exception(self) -> None:
        """Test TraceableLogger exception method.

        Description of what the test covers:
        Verifies that the `exception` method of `TraceableLogger` correctly logs
        exception information, including type, when called within an exception handler.

        Preconditions:
        - Trace ID is set.
        - Logger configured for JSON serialization.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` instance.
        - Configure output capture.
        - Raise and catch a `ValueError`.
        - Call `exception` method within the `except` block.
        - Parse and verify JSON output contains exception type.

        Expected Result:
        - Log output should contain the message and exception type.
        """
        set_trace_id("traceable_exception")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        try:
            raise ValueError("Test exception")
        except ValueError:
            traceable_logger.exception("Exception occurred")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Exception occurred"
        assert log_data["record"]["extra"]["exception_type"] == "ValueError"

    def test_traceable_logger_with_default_fields(self) -> None:
        """Test TraceableLogger with default fields.

        Description of what the test covers:
        Verifies that `TraceableLogger` properly includes default fields
        in all log messages along with trace ID information.

        Preconditions:
        - Trace ID is set.
        - Logger system is configured.

        Steps:
        - Set trace ID.
        - Create `TraceableLogger` with component and additional fields.
        - Configure output capture.
        - Log a message.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain message and all default fields.
        """
        set_trace_id("traceable_defaults")

        traceable_logger = TraceableLogger("test_component", service="test_service", version="1.0.0")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        traceable_logger.info("Test message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["message"] == "Test message"
        assert log_data["record"]["extra"]["service"] == "test_service"
        assert log_data["record"]["extra"]["version"] == "1.0.0"

    def test_traceable_logger_ensures_trace_id(self) -> None:
        """Test that TraceableLogger ensures trace ID exists.

        Description of what the test covers:
        Verifies that `TraceableLogger` automatically generates a trace ID
        when no trace ID is currently set in the context.

        Preconditions:
        - No trace ID set in context.
        - Logger system is configured.

        Steps:
        - Clear any existing trace ID.
        - Create `TraceableLogger`.
        - Configure output capture.
        - Log a message.
        - Parse and verify JSON output.

        Expected Result:
        - JSON log should contain an automatically generated trace ID.
        """
        clear_trace_id()  # Start with no trace ID

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, serialize=True, format="{message}")

        traceable_logger.info("Test message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        # Should have automatically created a trace ID
        assert "trace_id" in log_data["record"]["extra"]
        assert log_data["record"]["extra"]["trace_id"] != "no-trace"
        assert len(log_data["record"]["extra"]["trace_id"]) == 32  # UUID without dashes


@pytest.mark.integration
class TestSetupLoggingIntegration:
    """Test cases for integration with `setup_logging` function.

    Verifies that the `setup_logging` function correctly configures the
    logging system to integrate trace ID information into log messages.
    """

    def test_setup_logging_with_trace_id(self) -> None:
        """Test that setup_logging properly integrates trace ID.

        Description of what the test covers:
        Verifies that the `setup_logging` function properly configures
        the logging system to include trace ID information.

        Preconditions:
        - Trace ID is set.
        - Fresh logging environment.

        Steps:
        - Set trace ID.
        - Call `setup_logging` function.
        - Log a message using standard logger.
        - Verify trace ID is included in output.

        Expected Result:
        - Log output should include the set trace ID.
        """
        set_trace_id("setup_test")

        # Capture output
        output = StringIO()

        # Remove existing handlers and set up new one
        logger.remove()
        setup_logging(
            level="INFO",
            enable_console=True,
            enable_file=False,
        )
        logger.add(output, format="{extra[trace_id]} {message}")

        logger.info("Test message")

        output_str = output.getvalue()
        assert "setup_test" in output_str
        assert "Test message" in output_str


@pytest.mark.integration
class TestLogFormatters:
    """Test cases for log formatters with trace ID.

    Verifies that different log formatters (e.g., JSON) correctly include
    trace ID information in the final log output.
    """

    def test_json_formatter_with_trace_id(self) -> None:
        """Test JSON formatter includes trace ID.

        Description of what the test covers:
        Verifies that the JSON formatter correctly includes the trace ID
        in the `extra` field of the JSON log record.

        Preconditions:
        - Trace ID is set.
        - Logger configured for JSON serialization with `trace_id_patcher`.

        Steps:
        - Set trace ID.
        - Configure logger for JSON output.
        - Log a message.
        - Parse the JSON output and verify `trace_id` in `extra`.

        Expected Result:
        - JSON log output should contain the trace ID in the `extra` field.
        """

    def test_json_formatter_with_exception(self) -> None:
        """Test JSON formatter with exception includes trace ID info.

        Description of what the test covers:
        Verifies that the JSON formatter correctly includes trace ID and
        exception information when logging an exception.

        Preconditions:
        - Trace ID is set.
        - `CoreError` instance exists.
        - Logger configured for JSON serialization with `trace_id_patcher`.

        Steps:
        - Set trace ID.
        - Create `CoreError` instance.
        - Configure logger for JSON output.
        - Log an error with the exception using `logger.opt(exception=error).error()`.
        - Parse the JSON output and verify `trace_id` and exception details.

        Expected Result:
        - JSON log output should contain the trace ID and exception details.
        """


@pytest.mark.integration
class TestLogContextPropagation:
    """Test cases for contextual information propagation across boundaries.

    Verifies that trace IDs and other contextual data are correctly propagated
    across function calls, asynchronous boundaries, and nested contexts.
    """

    def test_log_context_propagation_across_functions(self) -> None:
        """Test context propagation across function calls.

        Description:
            Verifies that contextual information (trace_id, user ID) is correctly
            propagated and included in log records across nested function calls.

        Preconditions:
            - Trace ID is set in the context.
            - Logger configured with `trace_id_patcher`.

        Steps:
            - Set trace ID and configure logger.
            - Create nested function calls with logging.
            - Verify context appears in all log messages.

        Expected Result:
            - All log messages should contain the same trace ID.
            - Context information should be preserved across function boundaries.
        """
        set_trace_id("context_propagation_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} | {function} | {message}")

        def inner_function() -> str:
            logger.info("Inner function log")
            return "inner_result"

        def middle_function() -> str:
            logger.info("Middle function start")
            result = inner_function()
            logger.info(f"Middle function end with result: {result}")
            return result

        def outer_function() -> str:
            logger.info("Outer function start")
            result = middle_function()
            logger.info(f"Outer function end with result: {result}")
            return result

        outer_function()
        output_str = output.getvalue()

        # Verify all log messages contain the same trace ID
        lines = output_str.strip().split("\n")
        assert len(lines) == 5  # Should have 5 log messages

        for line in lines:
            assert "context_propagation_test" in line

        # Verify function names appear correctly
        assert "outer_function" in output_str
        assert "middle_function" in output_str
        assert "inner_function" in output_str

    async def test_log_context_propagation_across_async_boundaries(self) -> None:
        """Test context propagation across async/await boundaries.

        Description:
            Verifies that trace ID and context information is preserved
            when control flow crosses async/await calls and task switches.

        Preconditions:
            - Trace ID is set in the context.
            - Async functions with logging calls.

        Steps:
            - Set trace ID in main context.
            - Create async functions with await calls.
            - Verify trace ID persists across async boundaries.

        Expected Result:
            - Trace ID should be preserved across all async calls.
            - Context should not be lost during task switching.
        """
        import asyncio

        set_trace_id("async_propagation_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} | async | {message}")

        async def async_inner() -> str:
            await asyncio.sleep(0.01)  # Simulate async work
            logger.info("Async inner function")
            return "async_inner_result"

        async def async_middle() -> str:
            logger.info("Async middle start")
            await asyncio.sleep(0.01)
            result = await async_inner()
            logger.info(f"Async middle end: {result}")
            return result

        async def async_outer() -> str:
            logger.info("Async outer start")
            result = await async_middle()
            await asyncio.sleep(0.01)
            logger.info(f"Async outer end: {result}")
            return result

        await async_outer()
        output_str = output.getvalue()

        # Verify all async log messages contain the same trace ID
        lines = output_str.strip().split("\n")
        assert len(lines) == 5

        for line in lines:
            assert "async_propagation_test" in line
            assert "async" in line

    def test_log_context_nesting_and_restoration(self) -> None:
        """Test context nesting and proper restoration.

        Description:
            Verifies that nested trace contexts are handled correctly
            and that the original context is restored after exiting.

        Preconditions:
            - Multiple trace contexts can be nested.
            - Logger configured to capture context changes.

        Steps:
            - Set initial trace ID.
            - Enter nested trace context.
            - Log messages in different contexts.
            - Verify context restoration.

        Expected Result:
            - Different trace IDs should appear in nested contexts.
            - Original context should be restored after nesting.
        """
        from asset_core.observability.trace_id import TraceContext

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} | {message}")

        set_trace_id("outer_context")
        logger.info("Outer context message")

        with TraceContext("nested_context_1"):
            logger.info("Nested context 1 message")

            with TraceContext("nested_context_2"):
                logger.info("Deeply nested context message")

            logger.info("Back to nested context 1")

        logger.info("Back to outer context")

        output_str = output.getvalue()
        lines = output_str.strip().split("\n")

        # Verify correct context appears in each message
        assert "outer_context | Outer context message" in lines[0]
        assert "nested_context_1 | Nested context 1 message" in lines[1]
        assert "nested_context_2 | Deeply nested context message" in lines[2]
        assert "nested_context_1 | Back to nested context 1" in lines[3]
        assert "outer_context | Back to outer context" in lines[4]


@pytest.mark.integration
class TestLogFilteringRules:
    """Test cases for logging levels and custom filter functionality.

    Verifies that log levels and custom filter functions correctly control
    which log messages are processed and outputted.
    """

    def test_log_level_filtering(self) -> None:
        """Test logging level filtering works correctly.

        Description:
            Verifies that different log levels are filtered correctly
            and only messages at or above the configured level appear.

        Preconditions:
            - Logger can be configured with different levels.
            - Multiple log levels can be tested.

        Steps:
            - Configure logger with WARNING level.
            - Log messages at various levels.
            - Verify only WARNING and above appear.

        Expected Result:
            - DEBUG and INFO messages should be filtered out.
            - WARNING, ERROR, CRITICAL should appear.
        """
        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, level="WARNING", format="{level} | {message}")

        # Log at various levels
        logger.debug("Debug message - should not appear")
        logger.info("Info message - should not appear")
        logger.warning("Warning message - should appear")
        logger.error("Error message - should appear")
        logger.critical("Critical message - should appear")

        output_str = output.getvalue()
        lines = output_str.strip().split("\n")

        # Should only have 3 messages (WARNING, ERROR, CRITICAL)
        assert len(lines) == 3
        assert "Warning message - should appear" in output_str
        assert "Error message - should appear" in output_str
        assert "Critical message - should appear" in output_str
        assert "Debug message" not in output_str
        assert "Info message" not in output_str

    def test_custom_filter_functionality(self) -> None:
        """Test custom filter functions work correctly.

        Description:
            Verifies that custom filter functions can be used to selectively
            filter log messages based on custom criteria.

        Preconditions:
            - Custom filter function can be defined.
            - Logger accepts custom filters.

        Steps:
            - Define custom filter for specific module/function.
            - Configure logger with custom filter.
            - Log messages from different sources.
            - Verify filtering works correctly.

        Expected Result:
            - Only messages matching filter criteria should appear.
            - Messages not matching should be filtered out.
        """
        output = StringIO()
        logger.remove()

        # Custom filter that only allows messages containing "important"
        def important_filter(record: Any) -> bool:
            return "important" in record["message"].lower()

        logger.configure(patcher=trace_id_patcher)
        logger.add(output, filter=important_filter, format="{message}")

        # Log various messages
        logger.info("This is an important message")
        logger.info("This is a regular message")
        logger.error("Important error occurred")
        logger.warning("Regular warning")
        logger.critical("Very important system alert")

        output_str = output.getvalue()
        lines = [line for line in output_str.strip().split("\n") if line]

        # Should only have messages containing "important"
        assert len(lines) == 3
        assert "important message" in output_str
        assert "Important error occurred" in output_str
        assert "important system alert" in output_str
        assert "regular message" not in output_str
        assert "Regular warning" not in output_str

    def test_combined_level_and_custom_filtering(self) -> None:
        """Test combination of level filtering and custom filters.

        Description:
            Verifies that level filtering and custom filters work together
            correctly, with both conditions needing to be met.

        Preconditions:
            - Logger supports both level and custom filtering.
            - Multiple filter types can be combined.

        Steps:
            - Configure logger with ERROR level and custom filter.
            - Log messages at various levels with different content.
            - Verify both filters are applied.

        Expected Result:
            - Messages must pass both level and custom filter.
            - Messages failing either filter should not appear.
        """
        output = StringIO()
        logger.remove()

        # Custom filter for API-related messages
        def api_filter(record: Any) -> bool:
            return "api" in record["message"].lower()

        logger.configure(patcher=trace_id_patcher)
        logger.add(output, level="ERROR", filter=api_filter, format="{level} | {message}")

        # Various log messages
        logger.debug("API debug message")  # Wrong level
        logger.info("API info message")  # Wrong level
        logger.warning("API warning")  # Wrong level
        logger.error("API error occurred")  # Should appear (both filters pass)
        logger.error("Database error")  # Wrong content
        logger.critical("API critical failure")  # Should appear

        output_str = output.getvalue()
        lines = [line for line in output_str.strip().split("\n") if line]

        # Should only have 2 messages (ERROR and CRITICAL with "api")
        assert len(lines) == 2
        assert "ERROR | API error occurred" in output_str
        assert "CRITICAL | API critical failure" in output_str

        # Verify filtered messages don't appear
        assert "API debug message" not in output_str
        assert "API info message" not in output_str
        assert "Database error" not in output_str


@pytest.mark.integration
class TestAsyncLoggingPerformance:
    """Test cases for asynchronous logging mechanisms and performance characteristics.

    Verifies that logging operations in async contexts are non-blocking
    and handle exceptions gracefully.
    """

    async def test_async_logging_non_blocking(self) -> None:
        """Test that async logging doesn't block the main thread.

        Description:
            Verifies that logging operations in async contexts don't block
            the event loop and allow other tasks to run concurrently.

        Preconditions:
            - Async environment is set up.
            - Multiple concurrent tasks can be created.

        Steps:
            - Create multiple async tasks that log heavily.
            - Measure execution time and verify concurrency.
            - Ensure no blocking behavior.

        Expected Result:
            - Tasks should run concurrently without blocking.
            - Total execution time should be reasonable.
            - No deadlocks or hanging should occur.
        """
        import asyncio
        import time

        set_trace_id("async_performance_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} | {time:HH:mm:ss.SSS} | {message}")

        async def heavy_logging_task(task_id: int, message_count: int) -> str:
            """Task that performs heavy logging."""
            for i in range(message_count):
                logger.info(f"Task {task_id} - Message {i}")
                await asyncio.sleep(0.001)  # Small delay to simulate work
            return f"Task {task_id} completed"

        # Create multiple concurrent tasks
        start_time = time.time()
        tasks = []
        task_count = 5
        messages_per_task = 20

        for i in range(task_count):
            task = asyncio.create_task(heavy_logging_task(i, messages_per_task))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time
        total_messages = task_count * messages_per_task

        # Verify all tasks completed
        assert len(results) == task_count
        for i, result in enumerate(results):
            assert f"Task {i} completed" == result

        # Verify all messages were logged
        output_str = output.getvalue()
        logged_lines = [line for line in output_str.strip().split("\n") if line]
        assert len(logged_lines) == total_messages

        # Performance check: should complete reasonably quickly
        # With 5 tasks * 20 messages * 0.001s delay = ~0.1s minimum
        # Allow up to 2 seconds for actual execution (generous buffer)
        assert total_time < 2.0, f"Async logging took too long: {total_time:.2f}s"

        # Verify trace ID appears in all messages
        for line in logged_lines:
            assert "async_performance_test" in line

    async def test_async_logging_with_exceptions(self) -> None:
        """Test async logging behavior when exceptions occur.

        Description:
            Verifies that logging works correctly in async contexts
            even when exceptions are raised and handled.

        Preconditions:
            - Async exception handling is set up.
            - Logger configured for exception capture.

        Steps:
            - Create async tasks that raise exceptions.
            - Log exceptions with trace context.
            - Verify proper exception logging.

        Expected Result:
            - Exceptions should be logged with full context.
            - Trace IDs should be preserved during exception handling.
            - No loss of logging functionality.
        """
        import asyncio

        set_trace_id("async_exception_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, format="{extra[trace_id]} | {level} | {message}")

        async def failing_task(task_id: int) -> str:
            """Task that will raise an exception."""
            try:
                logger.info(f"Task {task_id} starting")
                await asyncio.sleep(0.01)

                if task_id % 2 == 0:
                    raise ValueError(f"Task {task_id} failed")

                logger.info(f"Task {task_id} completed successfully")
                return f"Task {task_id} success"

            except Exception as e:
                logger.error(f"Task {task_id} exception: {e}")
                return f"Task {task_id} failed"

        # Create mix of successful and failing tasks
        tasks = []
        for i in range(4):
            task = asyncio.create_task(failing_task(i))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        output_str = output.getvalue()
        lines = [line for line in output_str.strip().split("\n") if line]

        # Verify all messages have trace ID
        for line in lines:
            assert "async_exception_test" in line

        # Verify we have start messages for all tasks
        start_messages = [line for line in lines if "starting" in line]
        assert len(start_messages) == 4

        # Verify we have exception messages for even-numbered tasks (0, 2)
        exception_messages = [line for line in lines if "ERROR" in line and "exception" in line]
        assert len(exception_messages) == 2

        # Verify we have success messages for odd-numbered tasks (1, 3)
        success_messages = [line for line in lines if "completed successfully" in line]
        assert len(success_messages) == 2


@pytest.mark.integration
class TestLogSanitization:
    """Test cases for sensitive information masking and sanitization.

    Verifies that sensitive data (e.g., API keys, PII) is correctly
    redacted or masked in log output to prevent accidental exposure.
    """

    def test_api_key_masking(self) -> None:
        """Test that API keys are masked in log messages.

        Description:
            Verifies that sensitive information like API keys is automatically
            masked or redacted in log output to prevent exposure.

        Preconditions:
            - Logger configured with sanitization.
            - Test data contains sensitive information.

        Steps:
            - Configure logger with sensitive data filter.
            - Log messages containing API keys and secrets.
            - Verify sensitive data is masked.

        Expected Result:
            - API keys should be masked as `****`.
            - Other sensitive patterns should be redacted.
            - Non-sensitive data should remain visible.
        """
        output = StringIO()
        logger.remove()

        # Custom filter for sanitizing sensitive data
        def sanitize_filter(record: Any) -> bool:
            import re

            message = record["message"]

            # Mask API keys (pattern: api_key=xxx or apikey=xxx)
            message = re.sub(r"(api[_-]?key\s*[=:]\s*)[^\s&]+", r"\1****", message, flags=re.IGNORECASE)

            # Mask tokens
            message = re.sub(r"(token\s*[=:]\s*)[^\s&]+", r"\1****", message, flags=re.IGNORECASE)

            # Mask passwords
            message = re.sub(r"(password\s*[=:]\s*)[^\s&]+", r"\1****", message, flags=re.IGNORECASE)

            record["message"] = message
            return True

        logger.configure(patcher=trace_id_patcher)
        logger.add(output, filter=sanitize_filter, format="{message}")

        # Log messages with sensitive data
        logger.info("User login with api_key=abc123def456")
        logger.info("Authentication token=xyz789token123")
        logger.info("Database password=secretpassword123")
        logger.info("Regular message without sensitive data")
        logger.error("API request failed with apikey=sensitive123")

        output_str = output.getvalue()

        # Verify sensitive data is masked
        assert "api_key=****" in output_str
        assert "token=****" in output_str
        assert "password=****" in output_str
        assert "apikey=****" in output_str

        # Verify original sensitive data doesn't appear
        assert "abc123def456" not in output_str
        assert "xyz789token123" not in output_str
        assert "secretpassword123" not in output_str
        assert "sensitive123" not in output_str

        # Verify non-sensitive data remains
        assert "Regular message without sensitive data" in output_str

    def test_pii_data_redaction(self) -> None:
        """Test that PII (Personally Identifiable Information) is redacted.

        Description:
            Verifies that personal information like email addresses,
            phone numbers, and credit card numbers are properly redacted.

        Preconditions:
            - Logger configured with PII redaction.
            - Test data contains various PII patterns.

        Steps:
            - Configure logger with PII detection filter.
            - Log messages containing PII data.
            - Verify PII is properly redacted.

        Expected Result:
            - Email addresses should be partially masked.
            - Phone numbers should be redacted.
            - Credit card numbers should be masked.
        """
        output = StringIO()
        logger.remove()

        def pii_redaction_filter(record: Any) -> bool:
            import re

            message = record["message"]

            # Mask email addresses (keep domain)
            message = re.sub(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})", r"****@\1", message)

            # Mask phone numbers
            message = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", r"***-***-****", message)

            # Mask credit card numbers (basic pattern)
            message = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", r"****-****-****-****", message)

            record["message"] = message
            return True

        logger.configure(patcher=trace_id_patcher)
        logger.add(output, filter=pii_redaction_filter, format="{message}")

        # Log messages with PII
        logger.info("User email: john.doe@example.com")
        logger.info("Contact phone: 555-123-4567")
        logger.info("Payment card: 1234 5678 9012 3456")
        logger.info("Support request from jane@company.org")
        logger.warning("Invalid phone format: 123.456.7890")

        output_str = output.getvalue()

        # Verify PII is redacted
        assert "****@example.com" in output_str
        assert "****@company.org" in output_str
        assert "***-***-****" in output_str
        assert "****-****-****-****" in output_str

        # Verify original PII doesn't appear
        assert "john.doe@example.com" not in output_str
        assert "jane@company.org" not in output_str
        assert "555-123-4567" not in output_str
        assert "123.456.7890" not in output_str
        assert "1234 5678 9012 3456" not in output_str

    def test_custom_sensitive_pattern_masking(self) -> None:
        """Test custom sensitive pattern detection and masking.

        Description:
            Verifies that custom patterns can be defined and used
            to mask domain-specific sensitive information.

        Preconditions:
            - Custom patterns can be configured.
            - Logger accepts custom sanitization rules.

        Steps:
            - Define custom patterns for application-specific data.
            - Configure logger with custom sanitization.
            - Test various sensitive patterns.

        Expected Result:
            - Custom patterns should be detected and masked.
            - Application-specific sensitive data should be protected.
            - Flexibility in defining new patterns.
        """
        output = StringIO()
        logger.remove()

        def custom_pattern_filter(record: Any) -> bool:
            import re

            message = record["message"]

            # Custom patterns for trading application
            # Mask user IDs
            message = re.sub(r"\buser_id[=:]\s*\d+", r"user_id=****", message, flags=re.IGNORECASE)

            # Mask trading account numbers
            message = re.sub(r"\baccount[=:]\s*[A-Z0-9]+", r"account=****", message, flags=re.IGNORECASE)

            # Mask IP addresses
            message = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", r"***.***.***.***", message)

            record["message"] = message
            return True

        logger.configure(patcher=trace_id_patcher)
        logger.add(output, filter=custom_pattern_filter, format="{message}")

        # Log messages with custom sensitive patterns
        logger.info("Trade executed for user_id=12345")
        logger.info("Account: ABC123XYZ balance updated")
        logger.info("Request from IP: 192.168.1.100")
        logger.error("Failed login attempt from 10.0.0.50")
        logger.info("User account=DEF456 suspended")

        output_str = output.getvalue()

        # Verify custom patterns are masked
        assert "user_id=****" in output_str
        assert "account=****" in output_str.lower()
        assert "***.***.***.***" in output_str

        # Verify original sensitive data doesn't appear
        assert "user_id=12345" not in output_str
        assert "ABC123XYZ" not in output_str
        assert "DEF456" not in output_str
        assert "192.168.1.100" not in output_str
        assert "10.0.0.50" not in output_str


@pytest.fixture(autouse=True)
def cleanup_logging_and_trace_id() -> Generator[None, None, None]:
    """Cleans up logging and trace ID after each test.

    Description of what the fixture covers:
    This fixture is automatically used by all tests (`autouse=True`)
    to ensure a clean and isolated environment for each test function.
    It clears any set trace ID and resets the Loguru logger to its default
    state (removing all handlers and re-adding a basic stderr handler),
    preventing interference between tests.

    Preconditions:
    - `clear_trace_id` function is available.
    - Loguru `logger` is available.
    - `sys.stderr` is available.

    Steps:
    - Yields control to the test function.
    - After the test function completes, calls `clear_trace_id()`.
    - Removes all existing Loguru handlers.
    - Adds a default Loguru handler to `sys.stderr` with a basic format.

    Expected Result:
    - The trace ID context is reset to a clean state after every test.
    - The Loguru logger is reset to a default, clean configuration after every test.
    """
    yield
    clear_trace_id()
    # Reset loguru to default state
    logger.remove()
    logger.add(sys.stderr, format="{time} | {level} | {message}")
