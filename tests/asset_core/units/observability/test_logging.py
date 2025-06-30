import asyncio
import json
import logging
import sys
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger
from pytest_mock import MockerFixture

from asset_core.exceptions import CoreError
from asset_core.observability.logging import (
    LogContext,
    LogFilter,
    LogFormat,
    Record,
    TraceableLogger,
    create_debug_filter,
    create_error_filter,
    create_performance_filter,
    create_traced_logger,
    get_formatter,
    get_logger,
    get_structured_logger,
    log_exception_with_context,
    log_function_calls,
    log_performance,
    log_with_trace_id,
    setup_logging,
    trace_id_patcher,
)


@pytest.fixture
def mock_loguru_logger(mocker: MockerFixture) -> MagicMock:
    """Mocks the global Loguru logger instance."""
    mock_logger_instance = MagicMock(spec=logger)
    mocker.patch("asset_core.observability.logging.logger", new=mock_logger_instance)
    return mock_logger_instance


@pytest.fixture
def mock_trace_id_module(mocker: MockerFixture) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Mocks the trace_id module functions."""
    mock_get_trace_id = mocker.patch("asset_core.observability.trace_id.get_trace_id", return_value="test-trace-id")
    mock_ensure_trace_id = mocker.patch("asset_core.observability.trace_id.ensure_trace_id")
    mock_trace_context = mocker.patch("asset_core.observability.trace_id.TraceContext")
    return mock_get_trace_id, mock_ensure_trace_id, mock_trace_context


@pytest.fixture(autouse=True)
def reset_loguru_handlers() -> Generator[None, None, None]:
    """Ensures Loguru handlers are reset before and after each test."""
    logger.remove()
    yield
    logger.remove()


def create_mock_record(
    level_name: str = "INFO",
    message: str = "test message",
    name: str = "test_module",
    function: str = "test_function",
    line: int = 1,
    extra: dict[str, Any] | None = None,
    exception: Any = None,
) -> Record:
    """Create a properly typed mock Record object."""
    now = datetime.now()

    # Create a mock level object with the needed attributes
    level_mock = MagicMock()
    level_mock.name = level_name
    level_mock.no = logger.level(level_name).no
    level_mock.icon = "🔵"

    return cast(
        Record,
        {
            "elapsed": timedelta(seconds=1),
            "exception": exception,
            "extra": extra or {},
            "file": {"name": "test.py", "path": "/test/test.py"},
            "function": function,
            "level": level_mock,
            "line": line,
            "message": message,
            "module": name.split(".")[-1],
            "name": name,
            "process": {"id": 1234, "name": "test_process"},
            "thread": {"id": 5678, "name": "test_thread"},
            "time": now,
        },
    )


@pytest.mark.parametrize(
    "min_level, max_level, record_level, expected",
    [
        ("INFO", None, "DEBUG", False),
        ("INFO", None, "INFO", True),
        ("INFO", None, "WARNING", True),
        (None, "INFO", "DEBUG", True),
        (None, "INFO", "INFO", True),
        (None, "INFO", "WARNING", False),
        ("INFO", "WARNING", "DEBUG", False),
        ("INFO", "WARNING", "INFO", True),
        ("INFO", "WARNING", "WARNING", True),
        ("INFO", "WARNING", "ERROR", False),
    ],
)
def test_log_filter_level_filtering(
    min_level: str | None, max_level: str | None, record_level: str, expected: bool
) -> None:
    """Test LogFilter's level filtering."""
    log_filter = LogFilter(min_level=min_level, max_level=max_level)
    record = create_mock_record(level_name=record_level)
    assert log_filter(record) == expected


@pytest.mark.parametrize(
    "include_modules, exclude_modules, module_name, expected",
    [
        (["app"], [], "app.module", True),
        (["app"], [], "other.module", False),
        ([], ["app"], "app.module", False),
        ([], ["app"], "other.module", True),
        (["app"], ["app.sub"], "app.module", True),
        (["app"], ["app.sub"], "app.sub.module", False),
    ],
)
def test_log_filter_module_filtering(
    include_modules: list[str], exclude_modules: list[str], module_name: str, expected: bool
) -> None:
    """Test LogFilter's module filtering."""
    log_filter = LogFilter(include_modules=include_modules, exclude_modules=exclude_modules)
    record = create_mock_record(name=module_name)
    assert log_filter(record) == expected


@pytest.mark.parametrize(
    "include_functions, exclude_functions, function_name, expected",
    [
        (["func_a"], [], "func_a", True),
        (["func_a"], [], "func_b", False),
        ([], ["func_a"], "func_a", False),
        ([], ["func_a"], "func_b", True),
        (["func_a", "func_b"], ["func_b"], "func_a", True),
        (["func_a", "func_b"], ["func_b"], "func_b", False),
    ],
)
def test_log_filter_function_filtering(
    include_functions: list[str], exclude_functions: list[str], function_name: str, expected: bool
) -> None:
    """Test LogFilter's function filtering."""
    log_filter = LogFilter(include_functions=include_functions, exclude_functions=exclude_functions)
    record = create_mock_record(function=function_name)
    assert log_filter(record) == expected


def test_log_filter_custom_filter() -> None:
    """Test LogFilter with a custom filter."""

    def custom_filter_func(record: Record) -> bool:
        return "special" in record["message"]

    log_filter = LogFilter(custom_filter=custom_filter_func)
    assert log_filter(create_mock_record(message="This is a special message")) is True
    assert log_filter(create_mock_record(message="This is a normal message")) is False


def test_log_filter_combined_filters() -> None:
    """Test LogFilter with a combination of filters."""
    log_filter = LogFilter(
        min_level="INFO",
        include_modules=["app"],
        exclude_functions=["sensitive_func"],
    )

    # Should pass
    record_pass = create_mock_record(level_name="INFO", name="app.module", function="normal_func", message="test")
    assert log_filter(record_pass) is True

    # Should fail (level)
    record_fail_level = create_mock_record(
        level_name="DEBUG", name="app.module", function="normal_func", message="test"
    )
    assert log_filter(record_fail_level) is False

    # Should fail (module)
    record_fail_module = create_mock_record(
        level_name="INFO", name="other.module", function="normal_func", message="test"
    )
    assert log_filter(record_fail_module) is False

    # Should fail (function)
    record_fail_function = create_mock_record(
        level_name="INFO", name="app.module", function="sensitive_func", message="test"
    )
    assert log_filter(record_fail_function) is False


def test_create_performance_filter() -> None:
    """Test create_performance_filter function."""
    perf_filter = create_performance_filter()
    assert perf_filter(create_mock_record(message="Function performance: 10ms")) is True
    assert perf_filter(create_mock_record(message="Request latency: 50ms")) is True
    assert perf_filter(create_mock_record(message="Normal log message")) is False


def test_create_error_filter() -> None:
    """Test create_error_filter function."""
    error_filter = create_error_filter()
    assert error_filter(create_mock_record(level_name="WARNING")) is True
    assert error_filter(create_mock_record(level_name="ERROR")) is True
    assert error_filter(create_mock_record(level_name="INFO")) is False


def test_create_debug_filter() -> None:
    """Test create_debug_filter function."""
    debug_filter = create_debug_filter()
    assert debug_filter(create_mock_record(level_name="DEBUG")) is True
    assert debug_filter(create_mock_record(level_name="INFO")) is False


def test_trace_id_patcher(mocker: MockerFixture) -> None:
    """Test trace_id_patcher injects trace ID and handles exception trace ID."""
    mock_get_trace_id = mocker.patch("asset_core.observability.logging.get_trace_id", return_value="test-trace-id")
    mock_get_trace_id.return_value = "test-trace-id"

    record: Record = create_mock_record()
    trace_id_patcher(record)
    assert record["extra"]["trace_id"] == "test-trace-id"

    # Test with exception that has trace_id
    class CustomException(Exception):
        def __init__(self, message: str, trace_id: str) -> None:
            super().__init__(message)
            self.trace_id = trace_id

    exc = CustomException("Error", "exception-trace-id")
    record_with_exc = create_mock_record(exception=MagicMock(value=exc, type=CustomException))
    trace_id_patcher(record_with_exc)
    assert record_with_exc["extra"]["trace_id"] == "test-trace-id"
    assert record_with_exc["extra"]["exception_trace_id"] == "exception-trace-id"

    # Test with exception that does not have trace_id
    exc_no_trace = ValueError("Generic error")
    record_with_exc_no_trace = create_mock_record(exception=MagicMock(value=exc_no_trace, type=ValueError))
    trace_id_patcher(record_with_exc_no_trace)
    assert "exception_trace_id" not in record_with_exc_no_trace["extra"]


@pytest.mark.parametrize(
    "log_format, expected_type",
    [
        (LogFormat.PRETTY, str),
        (LogFormat.COMPACT, str),
        (LogFormat.DETAILED, str),
        (LogFormat.JSON, type(lambda x: x)),  # Callable
    ],
)
def test_get_formatter(log_format: LogFormat, expected_type: type) -> None:
    """Test get_formatter returns correct type of formatter."""
    formatter = get_formatter(log_format)
    assert isinstance(formatter, expected_type)


def test_get_formatter_json_output() -> None:
    """Test JSON formatter output structure and content."""
    json_formatter = get_formatter(LogFormat.JSON)
    assert callable(json_formatter), "JSON formatter should be callable"

    # Mock a record for testing
    mock_time = MagicMock()
    mock_time.isoformat.return_value = "2023-01-01T12:00:00.000000"

    mock_record = create_mock_record(
        level_name="INFO",
        name="test_module",
        function="test_func",
        line=123,
        message="Test message",
        extra={"trace_id": "abc-123", "custom_field": "value"},
    )
    mock_record["time"] = mock_time
    # Create mock objects with proper attributes for process and thread
    process_mock = MagicMock()
    process_mock.id = 100
    process_mock.name = "test_process"
    thread_mock = MagicMock()
    thread_mock.id = 200
    thread_mock.name = "test_thread"
    mock_record["process"] = process_mock
    mock_record["thread"] = thread_mock

    json_output = json_formatter(mock_record)
    parsed_output = json.loads(json_output)

    assert parsed_output["timestamp"] == "2023-01-01T12:00:00.000000"
    assert parsed_output["level"] == "INFO"
    assert parsed_output["logger"] == "test_module"
    assert parsed_output["function"] == "test_func"
    assert parsed_output["line"] == 123
    assert parsed_output["message"] == "Test message"
    assert parsed_output["trace_id"] == "abc-123"
    assert parsed_output["process"] == 100
    assert parsed_output["thread"] == 200
    assert parsed_output["custom_field"] == "value"
    assert "exception" not in parsed_output


def test_get_formatter_json_output_with_exception() -> None:
    """Test JSON formatter output with exception details."""
    json_formatter = get_formatter(LogFormat.JSON)
    assert callable(json_formatter), "JSON formatter should be callable"

    class TestCoreError(CoreError):
        def __init__(self, message: str, error_code: str, details: dict[str, Any], trace_id: str) -> None:
            super().__init__(message, error_code=error_code, details=details, trace_id=trace_id)

    exc = TestCoreError("Something went wrong", "ERR_001", {"data": "abc"}, "exc-trace-456")

    mock_time = MagicMock()
    mock_time.isoformat.return_value = "2023-01-01T12:00:00.000000"

    mock_record = create_mock_record(
        level_name="ERROR",
        name="test_module",
        function="test_func",
        line=123,
        message="Error message",
        extra={"trace_id": "abc-123"},
        exception=MagicMock(value=exc, type=type(exc), traceback="mock_traceback"),
    )
    mock_record["time"] = mock_time
    # Create mock objects with proper attributes for process and thread
    process_mock = MagicMock()
    process_mock.id = 100
    process_mock.name = "test_process"
    thread_mock = MagicMock()
    thread_mock.id = 200
    thread_mock.name = "test_thread"
    mock_record["process"] = process_mock
    mock_record["thread"] = thread_mock

    json_output = json_formatter(mock_record)
    parsed_output = json.loads(json_output)

    assert "exception" in parsed_output
    exc_info = parsed_output["exception"]
    assert exc_info["type"] == "TestCoreError"
    assert "Something went wrong" in exc_info["value"]
    assert exc_info["traceback"] == "mock_traceback"
    assert exc_info["exception_trace_id"] == "exc-trace-456"
    assert exc_info["error_code"] == "ERR_001"
    assert exc_info["details"]["data"] == "abc"
    assert exc_info["details"]["trace_id"] == "exc-trace-456"


@patch("asset_core.observability.logging.logger.remove")
@patch("asset_core.observability.logging.logger.add")
@patch("asset_core.observability.logging.configure_third_party_logging")
@patch("logging.basicConfig")
def test_setup_logging_basic_config(
    mock_basicConfig: MagicMock,
    mock_configure_third_party_logging: MagicMock,
    mock_logger_add: MagicMock,
    mock_logger_remove: MagicMock,
    mocker: MockerFixture,
) -> None:
    """Test basic setup_logging configuration."""
    setup_logging(level="DEBUG", enable_console=True, enable_file=False)

    mock_logger_remove.assert_called_once()
    mock_logger_add.assert_called_once()  # Only console handler
    mock_logger_add.assert_called_with(
        sys.stdout,
        format=get_formatter(LogFormat.PRETTY),
        level="DEBUG",
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=mocker.ANY,  # Filter is a callable, check its logic separately
        serialize=False,
    )
    mock_basicConfig.assert_called_once()
    # Verify that basicConfig was called with an InterceptHandler instance
    assert isinstance(mock_basicConfig.call_args.kwargs["handlers"][0], logging.Handler)
    assert mock_basicConfig.call_args.kwargs["level"] == 0
    assert mock_basicConfig.call_args.kwargs["force"] is True
    mock_configure_third_party_logging.assert_called_once()


@patch("asset_core.observability.logging.logger.add")
@patch("pathlib.Path.mkdir")
def test_setup_logging_file_output(mock_mkdir: MagicMock, mock_logger_add: MagicMock) -> None:
    """Test setup_logging with file output enabled."""
    setup_logging(enable_console=False, enable_file=True, log_file="test_logs/app.log")

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Check that logger.add was called for the file handler
    file_handler_call = mock_logger_add.call_args_list[0]
    assert file_handler_call.args[0] == Path("test_logs/app.log")
    assert file_handler_call.kwargs["level"] == "INFO"
    assert file_handler_call.kwargs["rotation"] == "1 day"
    assert file_handler_call.kwargs["retention"] == "30 days"
    assert file_handler_call.kwargs["compression"] == "gz"
    assert file_handler_call.kwargs["serialize"] is True  # Default file format is JSON


@patch("asset_core.observability.logging.logger.add")
@patch("pathlib.Path.mkdir")
def test_setup_logging_separate_error_file(mock_mkdir: MagicMock, mock_logger_add: MagicMock) -> None:
    """Test setup_logging with separate error file enabled."""
    setup_logging(enable_console=False, enable_file=False, enable_separate_error_file=True)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Check that logger.add was called for the error file handler
    error_file_call = mock_logger_add.call_args_list[0]
    assert error_file_call.args[0] == Path("logs/errors.log")
    assert error_file_call.kwargs["level"] == "WARNING"
    assert error_file_call.kwargs["serialize"] is True


@patch("asset_core.observability.logging.logger.add")
@patch("pathlib.Path.mkdir")
def test_setup_logging_performance_logs(mock_mkdir: MagicMock, mock_logger_add: MagicMock) -> None:
    """Test setup_logging with performance logs enabled."""
    setup_logging(enable_console=False, enable_file=False, enable_performance_logs=True)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Check that logger.add was called for the performance file handler
    perf_file_call = mock_logger_add.call_args_list[0]
    assert perf_file_call.args[0] == Path("logs/performance.log")
    assert perf_file_call.kwargs["level"] == "DEBUG"
    assert perf_file_call.kwargs["serialize"] is True


def test_get_logger(mock_loguru_logger: MagicMock) -> None:
    """Test get_logger returns Loguru logger and binds fields."""
    # Test without extra fields
    logger_instance = get_logger("my_module")
    assert logger_instance == mock_loguru_logger
    mock_loguru_logger.bind.assert_not_called()

    # Test with extra fields
    logger_instance_bound = get_logger("my_module", user_id="123", session_id="abc")
    mock_loguru_logger.bind.assert_called_once_with(user_id="123", session_id="abc")
    assert logger_instance_bound == mock_loguru_logger.bind.return_value


def test_get_structured_logger(mock_loguru_logger: MagicMock) -> None:
    """Test get_structured_logger returns Loguru logger and binds fields."""
    # get_structured_logger is a wrapper around get_logger
    logger_instance = get_structured_logger("my_module", request_id="xyz")
    mock_loguru_logger.bind.assert_called_once_with(request_id="xyz")
    assert logger_instance == mock_loguru_logger.bind.return_value


@pytest.mark.asyncio
async def test_log_performance_async_function(mock_loguru_logger: MagicMock) -> None:
    """Test log_performance decorator with an async function."""

    @log_performance(level="INFO")
    async def async_test_func() -> str:
        await asyncio.sleep(0.01)
        return "done"

    result = await async_test_func()
    assert result == "done"
    mock_loguru_logger.log.assert_called_once()
    args, kwargs = mock_loguru_logger.log.call_args
    assert args[0] == "INFO"
    assert "Performance: async_test_func completed in" in args[1]
    assert kwargs["function_name"] == "async_test_func"
    assert "duration_ms" in kwargs
    assert kwargs["success"] is True
    assert kwargs["error"] is None


def test_log_performance_sync_function(mock_loguru_logger: MagicMock) -> None:
    """Test log_performance decorator with a synchronous function."""

    @log_performance(level="DEBUG", func_name="custom_sync_name")
    def sync_test_func(a: int, b: int) -> int:
        return a + b

    result = sync_test_func(1, 2)
    assert result == 3
    mock_loguru_logger.log.assert_called_once()
    args, kwargs = mock_loguru_logger.log.call_args
    assert args[0] == "DEBUG"
    assert "Performance: custom_sync_name completed in" in args[1]
    assert kwargs["function_name"] == "custom_sync_name"
    assert "duration_ms" in kwargs
    assert kwargs["success"] is True
    assert kwargs["error"] is None


def test_log_performance_exception_handling(mock_loguru_logger: MagicMock) -> None:
    """Test log_performance decorator handles exceptions."""

    @log_performance(level="ERROR")
    def failing_func() -> None:
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        failing_func()

    mock_loguru_logger.log.assert_called_once()
    args, kwargs = mock_loguru_logger.log.call_args
    assert args[0] == "ERROR"
    assert "Performance: failing_func completed in" in args[1]
    assert kwargs["function_name"] == "failing_func"
    assert "duration_ms" in kwargs
    assert kwargs["success"] is False
    assert kwargs["error"] == "Test error"


def test_log_context(mock_loguru_logger: MagicMock) -> None:
    """Test LogContext manager binds and unbinds extra fields."""
    with LogContext(user_id="123", request_id="abc") as ctx_logger:
        ctx_logger.info("Message inside context")
        mock_loguru_logger.bind.assert_called_once_with(user_id="123", request_id="abc")
        mock_loguru_logger.bind.return_value.info.assert_called_once_with("Message inside context")
        mock_loguru_logger.bind.reset_mock()  # Reset for next assertion

    # After exiting context, bind should not be called with context fields
    mock_loguru_logger.info("Message outside context")
    mock_loguru_logger.bind.assert_not_called()
    mock_loguru_logger.info.assert_called_with("Message outside context")


@pytest.mark.asyncio
async def test_log_function_calls_async(mock_loguru_logger: MagicMock) -> None:
    """Test log_function_calls decorator with async function."""

    @log_function_calls(include_args=True, include_result=True)
    async def async_func(a: int, b: int) -> int:
        return a + b

    result = await async_func(1, 2)
    assert result == 3

    # Check debug logs for entry and exit
    assert mock_loguru_logger.debug.call_count == 2
    entry_call = mock_loguru_logger.debug.call_args_list[0]
    exit_call = mock_loguru_logger.debug.call_args_list[1]

    assert "Calling function: async_func" in entry_call.args[0]
    assert entry_call.kwargs["function"] == "async_func"
    assert entry_call.kwargs["args"] == "(1, 2)"
    assert entry_call.kwargs["kwargs"] == {} or entry_call.kwargs["kwargs"] is None

    assert "Function completed: async_func" in exit_call.args[0]
    assert exit_call.kwargs["function"] == "async_func"
    assert exit_call.kwargs["result"] == "3"


def test_log_function_calls_sync(mock_loguru_logger: MagicMock) -> None:
    """Test log_function_calls decorator with sync function."""

    @log_function_calls(include_args=False, include_result=False)
    def sync_func() -> str:
        return "hello"

    result = sync_func()
    assert result == "hello"

    # Check debug logs for entry and exit
    assert mock_loguru_logger.debug.call_count == 2
    entry_call = mock_loguru_logger.debug.call_args_list[0]
    exit_call = mock_loguru_logger.debug.call_args_list[1]

    assert "Calling function: sync_func" in entry_call.args[0]
    assert entry_call.kwargs["function"] == "sync_func"
    assert "args" not in entry_call.kwargs
    assert "kwargs" not in entry_call.kwargs

    assert "Function completed: sync_func" in exit_call.args[0]
    assert exit_call.kwargs["function"] == "sync_func"
    assert "result" not in exit_call.kwargs


def test_log_function_calls_exception(mock_loguru_logger: MagicMock) -> None:
    """Test log_function_calls decorator handles exceptions."""

    @log_function_calls()
    def failing_func() -> None:
        raise RuntimeError("Test error in func call")

    with pytest.raises(RuntimeError, match="Test error in func call"):
        failing_func()

    assert mock_loguru_logger.debug.call_count == 1
    assert mock_loguru_logger.error.call_count == 1
    error_call = mock_loguru_logger.error.call_args_list[0]
    assert "Function failed: failing_func" in error_call.args[0]
    assert error_call.kwargs["error"] == "Test error in func call"


def test_log_with_trace_id(
    mock_loguru_logger: MagicMock, mock_trace_id_module: tuple[MagicMock, MagicMock, MagicMock]
) -> None:
    """Test log_with_trace_id logs with explicit or current trace ID."""
    mock_get_trace_id, mock_ensure_trace_id, mock_trace_context = mock_trace_id_module

    # Test with explicit trace_id
    log_with_trace_id("INFO", "Message with explicit trace ID", trace_id="explicit-id")
    mock_trace_context.assert_called_once_with("explicit-id")
    mock_loguru_logger.log.assert_called_once_with("INFO", "Message with explicit trace ID")
    mock_loguru_logger.log.reset_mock()
    mock_trace_context.reset_mock()

    # Test without explicit trace_id (uses current from get_trace_id mock)
    log_with_trace_id("DEBUG", "Message with current trace ID")
    mock_trace_context.assert_not_called()  # TraceContext not used if trace_id is None
    mock_loguru_logger.log.assert_called_once_with("DEBUG", "Message with current trace ID")


def test_log_exception_with_context_basic(mock_loguru_logger: MagicMock) -> None:
    """Test log_exception_with_context with a basic exception."""
    exc = ValueError("Something bad happened")
    log_exception_with_context(exc, level="WARNING", message="Custom error message", custom_data="abc")

    mock_loguru_logger.log.assert_called_once()
    args, kwargs = mock_loguru_logger.log.call_args
    assert args[0] == "WARNING"
    assert args[1] == "Custom error message"
    assert kwargs["exception_type"] == "ValueError"
    assert kwargs["custom_data"] == "abc"
    assert "error_code" not in kwargs
    assert "exception_trace_id" not in kwargs


def test_log_exception_with_context_core_error(mock_loguru_logger: MagicMock) -> None:
    """Test log_exception_with_context with a CoreError."""

    class MyCoreError(CoreError):
        def __init__(self, message: str, error_code: str, details: dict[str, Any], trace_id: str) -> None:
            super().__init__(message, error_code=error_code, details=details, trace_id=trace_id)

    exc = MyCoreError("Core issue", "CORE_001", {"reason": "failed"}, "core-trace-123")
    log_exception_with_context(exc, level="ERROR")

    mock_loguru_logger.log.assert_called_once()
    args, kwargs = mock_loguru_logger.log.call_args
    assert args[0] == "ERROR"
    assert "Core issue" in args[1]
    assert kwargs["exception_type"] == "MyCoreError"
    assert kwargs["error_code"] == "CORE_001"
    assert kwargs["exception_trace_id"] == "core-trace-123"
    assert kwargs["reason"] == "failed"  # Details are unpacked


def test_create_traced_logger(mock_loguru_logger: MagicMock) -> None:
    """Test create_traced_logger binds component name and default fields."""
    traced_logger = create_traced_logger("my_component", default_val=123)
    mock_loguru_logger.bind.assert_called_once_with(component="my_component", default_val=123)
    assert traced_logger == mock_loguru_logger.bind.return_value


def test_traceable_logger_debug(
    mock_loguru_logger: MagicMock, mock_trace_id_module: tuple[MagicMock, MagicMock, MagicMock]
) -> None:
    """Test TraceableLogger.debug logs with trace ID and default fields."""
    mock_get_trace_id, mock_ensure_trace_id, mock_trace_context = mock_trace_id_module

    t_logger = TraceableLogger("my_service", service_version="1.0")
    t_logger.debug("Debug message", request_id="req-456")

    mock_ensure_trace_id.assert_called_once()
    mock_loguru_logger.bind.assert_called_once_with(component="my_service", service_version="1.0", request_id="req-456")
    mock_loguru_logger.bind.return_value.log.assert_called_once_with("DEBUG", "Debug message")


def test_traceable_logger_error_with_exception(mock_loguru_logger: MagicMock, mocker: MockerFixture) -> None:
    """Test TraceableLogger.error calls log_exception_with_context when exception is provided."""
    mock_log_exc_context = mocker.patch("asset_core.observability.logging.log_exception_with_context")

    t_logger = TraceableLogger("error_service")
    exc = ValueError("Test error")
    t_logger.error("Error occurred", exc=exc, custom_tag="important")

    mock_log_exc_context.assert_called_once_with(exc, "ERROR", "Error occurred", custom_tag="important")
    mock_loguru_logger.log.assert_not_called()
