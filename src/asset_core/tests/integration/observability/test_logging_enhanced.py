"""Tests for enhanced logging functionality with trace ID."""

import json
import sys
from io import StringIO

import pytest
from asset_core.exceptions import CoreError
from asset_core.observability.logging import (
    TraceableLogger,
    create_traced_logger,
    log_exception_with_context,
    log_with_trace_id,
    setup_logging,
    trace_id_patcher,
)
from asset_core.observability.trace_id import clear_trace_id, set_trace_id
from loguru import logger


@pytest.mark.integration
class TestTraceIdPatcher:
    """Test trace ID patcher functionality."""

    def test_trace_id_patcher_with_trace_id(self):
        """Test patcher adds trace ID when available.

        Description of what the test covers:
        Verifies that the trace_id_patcher correctly adds the current trace ID
        to log record extra fields when a trace ID is set.

        Preconditions:
        - Trace ID is set in the context
        - Empty record with extra field

        Steps:
        - Set a specific trace ID
        - Create log record with empty extra dict
        - Apply trace_id_patcher to record

        Expected Result:
        - Record extra should contain the set trace ID
        """
        set_trace_id("patcher_test")

        record = {"extra": {}}
        trace_id_patcher(record)

        assert record["extra"]["trace_id"] == "patcher_test"

    def test_trace_id_patcher_no_trace_id(self):
        """Test patcher adds 'no-trace' when no trace ID is set.

        Description of what the test covers:
        Verifies that the trace_id_patcher adds default 'no-trace' value
        when no trace ID is available in the context.

        Preconditions:
        - No trace ID set in context
        - Empty record with extra field

        Steps:
        - Clear any existing trace ID
        - Create log record with empty extra dict
        - Apply trace_id_patcher to record

        Expected Result:
        - Record extra should contain 'no-trace' as trace ID
        """
        clear_trace_id()

        record = {"extra": {}}
        trace_id_patcher(record)

        assert record["extra"]["trace_id"] == "no-trace"

    def test_trace_id_patcher_with_exception(self):
        """Test patcher extracts trace ID from exception.

        Description of what the test covers:
        Verifies that the trace_id_patcher can extract trace ID from
        CoreError exceptions and add both current and exception trace IDs.

        Preconditions:
        - Current trace ID is set
        - CoreError with different trace ID exists
        - Log record with exception present

        Steps:
        - Set current trace ID
        - Create CoreError with different trace ID
        - Create log record with exception
        - Apply trace_id_patcher to record

        Expected Result:
        - Record should contain both current and exception trace IDs
        """
        set_trace_id("current_trace")
        error = CoreError("Test error", trace_id="exception_trace")

        # Mock exception object (simulates sys.exc_info() format)
        class MockException:
            def __init__(self, value):
                self.value = value
                self.type = type(value)  # Add the missing type attribute

        record = {"extra": {}, "exception": MockException(error)}

        trace_id_patcher(record)

        assert record["extra"]["trace_id"] == "current_trace"
        assert record["extra"]["exception_trace_id"] == "exception_trace"

    def test_trace_id_patcher_exception_no_trace_id(self):
        """Test patcher with exception that has no trace ID.

        Description of what the test covers:
        Verifies that the trace_id_patcher handles standard exceptions
        that don't have trace ID attributes correctly.

        Preconditions:
        - Current trace ID is set
        - Standard exception (not CoreError) exists
        - Log record with exception present

        Steps:
        - Set current trace ID
        - Create standard ValueError
        - Create log record with exception
        - Apply trace_id_patcher to record

        Expected Result:
        - Record should contain current trace ID only
        - No exception_trace_id should be added
        """
        set_trace_id("current_trace")
        error = ValueError("Standard error")

        class MockException:
            def __init__(self, value):
                self.value = value
                self.type = type(value)  # Add the missing type attribute

        record = {"extra": {}, "exception": MockException(error)}

        trace_id_patcher(record)

        assert record["extra"]["trace_id"] == "current_trace"
        assert "exception_trace_id" not in record["extra"]


@pytest.mark.integration
class TestLogWithTraceId:
    """Test log_with_trace_id function."""

    def test_log_with_explicit_trace_id(self):
        """Test logging with explicit trace ID.

        Description of what the test covers:
        Verifies that log_with_trace_id function correctly logs messages
        when an explicit trace ID is provided.

        Preconditions:
        - Logger configured with trace_id_patcher
        - Output capture set up

        Steps:
        - Configure logger with trace ID formatting
        - Call log_with_trace_id with explicit trace ID
        - Verify output contains trace ID and message

        Expected Result:
        - Log output should contain the explicit trace ID and message
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

    def test_log_with_current_trace_id(self):
        """Test logging with current trace ID.

        Description of what the test covers:
        Verifies that log_with_trace_id function uses the current
        trace ID when no explicit trace ID is provided.

        Preconditions:
        - Current trace ID is set
        - Logger configured with trace_id_patcher

        Steps:
        - Set current trace ID
        - Configure logger with trace ID formatting
        - Call log_with_trace_id without explicit trace ID
        - Verify output contains current trace ID

        Expected Result:
        - Log output should contain the current trace ID and message
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

    def test_log_with_extra_fields(self):
        """Test logging with additional fields.

        Description of what the test covers:
        Verifies that log_with_trace_id function correctly handles
        additional extra fields along with trace ID.

        Preconditions:
        - Current trace ID is set
        - Logger configured for JSON serialization

        Steps:
        - Set current trace ID
        - Configure logger for JSON output
        - Call log_with_trace_id with extra fields
        - Parse and verify JSON output

        Expected Result:
        - Log output should contain trace ID and extra fields in JSON
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
    """Test log_exception_with_context function."""

    def test_log_core_error_with_context(self):
        """Test logging CoreError with full context.

        Description of what the test covers:
        Verifies that log_exception_with_context function properly logs
        CoreError exceptions with all context information.

        Preconditions:
        - Trace ID is set
        - CoreError with error code and details exists
        - Logger configured for JSON serialization

        Steps:
        - Set trace ID
        - Create CoreError with error code and details
        - Configure logger for JSON output
        - Call log_exception_with_context
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain message, exception type, error code, and details
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

    def test_log_standard_exception_with_context(self):
        """Test logging standard exception with context.

        Description of what the test covers:
        Verifies that log_exception_with_context function handles
        standard Python exceptions correctly.

        Preconditions:
        - Trace ID is set
        - Standard exception (ValueError) exists
        - Logger configured for JSON serialization

        Steps:
        - Set trace ID
        - Create standard ValueError
        - Configure logger for JSON output
        - Call log_exception_with_context without custom message
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain exception message and type information
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

    def test_log_exception_default_message(self):
        """Test logging exception with default message.

        Description of what the test covers:
        Verifies that log_exception_with_context function uses a default
        message format when no custom message is provided.

        Preconditions:
        - Standard exception exists
        - Logger configured for simple output

        Steps:
        - Create standard ValueError
        - Configure logger with simple formatting
        - Call log_exception_with_context without custom message or level
        - Verify output contains default message format

        Expected Result:
        - Log output should contain 'Exception occurred:' prefix with error message
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
    """Test create_traced_logger function."""

    def test_create_traced_logger_basic(self):
        """Test creating traced logger with basic functionality.

        Description of what the test covers:
        Verifies that create_traced_logger function creates a logger
        that automatically includes component information.

        Preconditions:
        - Trace ID is set
        - Logger system is configured

        Steps:
        - Set trace ID
        - Create traced logger with component name
        - Configure output capture
        - Log a message
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain message and component information
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

    def test_create_traced_logger_with_fields(self):
        """Test creating traced logger with default fields.

        Description of what the test covers:
        Verifies that create_traced_logger function correctly handles
        additional default fields that are included in all log messages.

        Preconditions:
        - Trace ID is set
        - Logger system is configured

        Steps:
        - Set trace ID
        - Create traced logger with component name and additional fields
        - Configure output capture
        - Log a message
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain message, component, and additional fields
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
    """Test TraceableLogger class."""

    def test_traceable_logger_debug(self):
        """Test TraceableLogger debug method."""
        set_trace_id("traceable_debug")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="DEBUG", format="{level} {message}")

        traceable_logger.debug("Debug message")

        output_str = output.getvalue()
        assert "DEBUG" in output_str
        assert "Debug message" in output_str

    def test_traceable_logger_info(self):
        """Test TraceableLogger info method."""
        set_trace_id("traceable_info")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="INFO", format="{level} {message}")

        traceable_logger.info("Info message")

        output_str = output.getvalue()
        assert "INFO" in output_str
        assert "Info message" in output_str

    def test_traceable_logger_warning(self):
        """Test TraceableLogger warning method."""
        set_trace_id("traceable_warning")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="WARNING", format="{level} {message}")

        traceable_logger.warning("Warning message")

        output_str = output.getvalue()
        assert "WARNING" in output_str
        assert "Warning message" in output_str

    def test_traceable_logger_error_with_exception(self):
        """Test TraceableLogger error method with exception."""
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

    def test_traceable_logger_error_without_exception(self):
        """Test TraceableLogger error method without exception."""
        set_trace_id("traceable_error_no_exc")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="ERROR", format="{level} {message}")

        traceable_logger.error("Simple error message")

        output_str = output.getvalue()
        assert "ERROR" in output_str
        assert "Simple error message" in output_str

    def test_traceable_logger_critical(self):
        """Test TraceableLogger critical method."""
        set_trace_id("traceable_critical")

        traceable_logger = TraceableLogger("test_component")

        output = StringIO()
        logger.remove()
        logger.add(output, level="CRITICAL", format="{level} {message}")

        traceable_logger.critical("Critical message")

        output_str = output.getvalue()
        assert "CRITICAL" in output_str
        assert "Critical message" in output_str

    def test_traceable_logger_exception(self):
        """Test TraceableLogger exception method."""
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

    def test_traceable_logger_with_default_fields(self):
        """Test TraceableLogger with default fields.

        Description of what the test covers:
        Verifies that TraceableLogger properly includes default fields
        in all log messages along with trace ID information.

        Preconditions:
        - Trace ID is set
        - Logger system is configured

        Steps:
        - Set trace ID
        - Create TraceableLogger with component and additional fields
        - Configure output capture
        - Log a message
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain message and all default fields
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

    def test_traceable_logger_ensures_trace_id(self):
        """Test that TraceableLogger ensures trace ID exists.

        Description of what the test covers:
        Verifies that TraceableLogger automatically generates a trace ID
        when no trace ID is currently set in the context.

        Preconditions:
        - No trace ID set in context
        - Logger system is configured

        Steps:
        - Clear any existing trace ID
        - Create TraceableLogger
        - Configure output capture
        - Log a message
        - Parse and verify JSON output

        Expected Result:
        - JSON log should contain an automatically generated trace ID
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
    """Test integration with setup_logging function."""

    def test_setup_logging_with_trace_id(self):
        """Test that setup_logging properly integrates trace ID.

        Description of what the test covers:
        Verifies that the setup_logging function properly configures
        the logging system to include trace ID information.

        Preconditions:
        - Trace ID is set
        - Fresh logging environment

        Steps:
        - Set trace ID
        - Call setup_logging function
        - Log a message using standard logger
        - Verify trace ID is included in output

        Expected Result:
        - Log output should include the set trace ID
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
    """Test log formatters with trace ID."""

    def test_json_formatter_with_trace_id(self):
        """Test JSON formatter includes trace ID."""
        set_trace_id("json_format_test")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, serialize=True, format="{message}")

        logger.info("Test message")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["extra"]["trace_id"] == "json_format_test"
        assert log_data["record"]["message"] == "Test message"

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception includes trace ID info."""
        set_trace_id("json_exception_test")
        error = CoreError("Test error", error_code="TEST_ERROR")

        output = StringIO()
        logger.remove()
        logger.configure(patcher=trace_id_patcher)
        logger.add(output, serialize=True, format="{message}")

        logger.opt(exception=error).error("Exception occurred")

        output_str = output.getvalue()
        log_data = json.loads(output_str.strip())

        assert log_data["record"]["extra"]["trace_id"] == "json_exception_test"
        assert log_data["record"]["message"] == "Exception occurred"
        assert "exception" in log_data["record"]


@pytest.fixture(autouse=True)
def cleanup_logging_and_trace_id():
    """Cleanup logging and trace ID after each test."""
    yield
    clear_trace_id()
    # Reset loguru to default state
    logger.remove()
    logger.add(sys.stderr, format="{time} | {level} | {message}")
