"""Loguru-based structured logging configuration with trace ID support.

This module provides a comprehensive logging solution for the `asset_core` library,
leveraging Loguru for structured logging, automatic trace ID injection, and flexible
output formatting. It includes utilities for setting up various log sinks (console,
file), filtering logs, and integrating with standard Python logging.
"""

import json
import sys
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any

from loguru import logger

from .trace_id import get_trace_id

if TYPE_CHECKING:
    from loguru import Logger, Record
else:
    Logger = type(logger)
    from datetime import datetime, timedelta
    from typing import TypedDict

    class RecordException(TypedDict, total=False):
        type: type[BaseException] | None
        value: BaseException | None
        traceback: Any

    class RecordFile(TypedDict):
        name: str
        path: str

    class RecordLevel(TypedDict):
        name: str
        no: int
        icon: str

    class RecordThread(TypedDict):
        id: int
        name: str

    class RecordProcess(TypedDict):
        id: int
        name: str

    class Record(TypedDict):
        elapsed: timedelta
        exception: RecordException | None
        extra: dict[Any, Any]
        file: RecordFile
        function: str
        level: RecordLevel
        line: int
        message: str
        module: str
        name: str | None
        process: RecordProcess
        thread: RecordThread
        time: datetime


class LogFormat(str, Enum):
    """Defines available log output formats.

    Attributes:
        JSON (str): Logs are formatted as JSON objects, suitable for machine parsing.
        PRETTY (str): Logs are formatted for human readability with colors and detailed information.
        COMPACT (str): A more concise human-readable format.
        DETAILED (str): A highly detailed human-readable format including process and thread info.
    """

    JSON = "json"
    PRETTY = "pretty"
    COMPACT = "compact"
    DETAILED = "detailed"


class LogFilter:
    """A flexible log filter allowing filtering by level, module, function, and custom criteria.

    This class enables fine-grained control over which log records are processed
    by a Loguru sink, based on various attributes of the log record.
    """

    def __init__(
        self,
        min_level: str | None = None,
        max_level: str | None = None,
        include_modules: list[str] | None = None,
        exclude_modules: list[str] | None = None,
        include_functions: list[str] | None = None,
        exclude_functions: list[str] | None = None,
        custom_filter: Callable[[Record], bool] | None = None,
    ) -> None:
        """Initializes the LogFilter with specified filtering criteria.

        Args:
            min_level: The minimum log level (e.g., "INFO", "DEBUG") for records to be included.
            max_level: The maximum log level for records to be included.
            include_modules: A list of module name prefixes; only logs from these modules will be included.
            exclude_modules: A list of module name prefixes; logs from these modules will be excluded.
            include_functions: A list of function names; only logs from these functions will be included.
            exclude_functions: A list of function names; logs from these functions will be excluded.
            custom_filter: An optional callable that takes a Loguru `Record` and returns a boolean.
                           If `False`, the record is filtered out.
        """
        self.min_level = min_level
        self.max_level = max_level
        self.include_modules = include_modules if include_modules is not None else []
        self.exclude_modules = exclude_modules if exclude_modules is not None else []
        self.include_functions = include_functions if include_functions is not None else []
        self.exclude_functions = exclude_functions if exclude_functions is not None else []
        self.custom_filter = custom_filter

    def __call__(self, record: Record) -> bool:
        """Applies the defined filters to a log record.

        Args:
            record: The Loguru `Record` dictionary to filter.

        Returns:
            `True` if the record should be logged, `False` otherwise.
        """
        # Level filtering
        if self.min_level and record["level"].no < logger.level(self.min_level).no:
            return False

        if self.max_level and record["level"].no > logger.level(self.max_level).no:
            return False

        # Module filtering
        module_name = str(record["name"])
        if self.include_modules and not any(module_name.startswith(module) for module in self.include_modules):
            return False

        if self.exclude_modules and any(module_name.startswith(module) for module in self.exclude_modules):
            return False

        # Function filtering
        function_name = str(record["function"])
        if self.include_functions and function_name not in self.include_functions:
            return False

        if self.exclude_functions and function_name in self.exclude_functions:
            return False

        # Custom filter
        return not (self.custom_filter and not self.custom_filter(record))


def create_performance_filter() -> LogFilter:
    """Creates a `LogFilter` instance specifically for performance-related log messages.

    This filter identifies log messages that contain keywords commonly associated
    with performance metrics (e.g., "performance", "latency", "duration").

    Returns:
        A `LogFilter` configured to capture performance-related logs.
    """

    def performance_filter(record: Record) -> bool:
        message = record["message"].lower()
        return any(
            keyword in message
            for keyword in [
                "performance",
                "latency",
                "duration",
                "timing",
                "benchmark",
                "speed",
                "throughput",
                "response_time",
                "elapsed",
            ]
        )

    return LogFilter(custom_filter=performance_filter)


def create_error_filter() -> LogFilter:
    """Creates a `LogFilter` instance for error and warning level logs.

    This filter includes log messages with a level of `WARNING` or higher.

    Returns:
        A `LogFilter` configured to capture error and warning logs.
    """
    return LogFilter(min_level="WARNING")


def create_debug_filter() -> LogFilter:
    """Creates a `LogFilter` instance for debug level logs only.

    This filter specifically targets log messages with a `DEBUG` level.

    Returns:
        A `LogFilter` configured to capture only debug logs.
    """
    return LogFilter(min_level="DEBUG", max_level="DEBUG")


def trace_id_patcher(record: Record) -> None:
    """Loguru patcher to inject trace ID into log records and enhance exception info.

    This function is called by Loguru for each log record. It retrieves the
    current trace ID (if available) and adds it to the `extra` field of the
    log record. It also extracts trace ID from exceptions if present.

    Args:
        record: The Loguru `Record` dictionary to be patched.
    """
    record["extra"]["trace_id"] = get_trace_id() or "no-trace"

    # If there's an exception, try to extract trace ID from it
    exc_info = record.get("exception")
    if exc_info and exc_info.value and exc_info.type:
        exception_trace_id = getattr(exc_info.value, "trace_id", None)
        if exception_trace_id and exception_trace_id != "no-trace":
            record["extra"]["exception_trace_id"] = exception_trace_id


def get_formatter(format_type: LogFormat) -> str | Callable[[Record], str]:
    """Returns a Loguru formatter string or a callable based on the specified format type.

    Args:
        format_type: The desired `LogFormat` (e.g., `LogFormat.JSON`, `LogFormat.PRETTY`).

    Returns:
        A string formatter suitable for Loguru's `add` method, or a callable
        that formats a log record into a string (e.g., for JSON output).
    """
    if format_type == LogFormat.PRETTY:
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<yellow>{extra[trace_id]}</yellow> | "
            "<level>{message}</level>"
        )

    elif format_type == LogFormat.COMPACT:
        return (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level[0]}</level> | "
            "<cyan>{name.split('.')[-1]}</cyan> | "
            "<level>{message}</level>"
        )

    elif format_type == LogFormat.DETAILED:
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<blue>{process}</blue>:<blue>{thread}</blue> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<yellow>{extra[trace_id]}</yellow> | "
            "<magenta>{extra.get('user_id', 'N/A')}</magenta> | "
            "<level>{message}</level> {exception}"
        )

    elif format_type == LogFormat.JSON:

        def json_formatter(record: Record) -> str:
            """Formats a Loguru record into a JSON string.

            Args:
                record: The Loguru `Record` dictionary.

            Returns:
                A JSON string representation of the log record.
            """
            log_entry = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "trace_id": record["extra"].get("trace_id", "no-trace"),
                "process": record["process"].id,
                "thread": record["thread"].id,
            }

            # Add extra fields
            for key, value in record["extra"].items():
                if key not in ("trace_id",):
                    log_entry[key] = value

            # Add exception info if present
            exc_info = record.get("exception")
            if exc_info and exc_info.value and exc_info.type:
                exception_info = {
                    "type": exc_info.type.__name__,
                    "value": str(exc_info.value),
                    "traceback": str(exc_info.traceback),
                }

                # Add exception-specific trace ID if available
                if hasattr(exc_info.value, "trace_id"):
                    trace_id = getattr(exc_info.value, "trace_id", None)
                    if trace_id is not None:
                        exception_info["exception_trace_id"] = trace_id

                # Add exception details if it's a CoreError
                if hasattr(exc_info.value, "details"):
                    details = getattr(exc_info.value, "details", None)
                    if details is not None:
                        exception_info["details"] = details

                # Add error code if available
                if hasattr(exc_info.value, "error_code"):
                    error_code = getattr(exc_info.value, "error_code", None)
                    if error_code is not None:
                        exception_info["error_code"] = error_code

                log_entry["exception"] = exception_info

            return json.dumps(log_entry, ensure_ascii=False, default=str)

        return json_formatter


def setup_logging(
    level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    log_file: str | Path | None = None,
    app_name: str | None = None,
    environment: str | None = None,
    additional_fields: dict[str, Any] | None = None,
    console_format: LogFormat = LogFormat.PRETTY,
    file_format: LogFormat = LogFormat.JSON,
    log_filter: LogFilter | None = None,
    enable_performance_logs: bool = False,
    enable_separate_error_file: bool = False,
) -> None:
    """Configures Loguru-based structured logging for the application.

    This function sets up various log sinks (console, file), applies formatting,
    and integrates with trace ID injection and standard Python logging.

    Args:
        level: The minimum logging level to capture (e.g., "INFO", "DEBUG").
        enable_console: If `True`, logs will be output to the console.
        enable_file: If `True`, logs will be written to a file.
        log_file: The path to the main log file. Defaults to `logs/app.log`.
        app_name: An optional name for the application, added as an extra field.
        environment: An optional environment name (e.g., "production", "development"), added as an extra field.
        additional_fields: A dictionary of additional key-value pairs to include in every log record.
        console_format: The `LogFormat` to use for console output.
        file_format: The `LogFormat` to use for file output.
        log_filter: An optional `LogFilter` instance to apply custom filtering rules.
        enable_performance_logs: If `True`, a separate log file (`logs/performance.log`)
                                 will be created for performance-related messages.
        enable_separate_error_file: If `True`, a separate log file (`logs/errors.log`)
                                    will be created for warning and error messages.
    """
    # Remove default handler
    logger.remove()

    # Base extra fields
    extra_fields = {}
    if app_name:
        extra_fields["app"] = app_name
    if environment:
        extra_fields["environment"] = environment
    if additional_fields:
        extra_fields.update(additional_fields)

    # Create combined filter
    def combined_filter(record: Record) -> bool:
        # Update extra fields
        record["extra"].update(extra_fields)

        # Apply custom filter if provided
        return not (log_filter and not log_filter(record))

    # Console handler
    if enable_console:
        console_formatter = get_formatter(console_format)

        logger.add(
            sys.stdout,
            format=console_formatter if isinstance(console_formatter, str) else "{message}",
            level=level,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            filter=combined_filter,
            serialize=not isinstance(console_formatter, str),
        )

    # Main file handler
    if enable_file:
        log_file = Path("logs/app.log") if log_file is None else Path(log_file)

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_formatter = get_formatter(file_format)

        logger.add(
            log_file,
            format=file_formatter if isinstance(file_formatter, str) else "{message}",
            level=level,
            rotation="1 day",
            retention="30 days",
            compression="gz",
            enqueue=True,
            backtrace=True,
            diagnose=True,
            filter=combined_filter,
            serialize=not isinstance(file_formatter, str),
        )

    # Separate error file
    if enable_separate_error_file:
        error_file = Path("logs/errors.log")
        error_file.parent.mkdir(parents=True, exist_ok=True)

        error_filter = create_error_filter()

        def error_combined_filter(record: Record) -> bool:
            record["extra"].update(extra_fields)
            return error_filter(record) and (log_filter is None or log_filter(record))

        logger.add(
            error_file,
            format=get_formatter(LogFormat.JSON),
            level="WARNING",
            rotation="1 week",
            retention="90 days",
            compression="gz",
            enqueue=True,
            backtrace=True,
            diagnose=True,
            filter=error_combined_filter,
            serialize=True,
        )

    # Performance logs
    if enable_performance_logs:
        perf_file = Path("logs/performance.log")
        perf_file.parent.mkdir(parents=True, exist_ok=True)

        perf_filter = create_performance_filter()

        def perf_combined_filter(record: Record) -> bool:
            record["extra"].update(extra_fields)
            return perf_filter(record) and (log_filter is None or log_filter(record))

        logger.add(
            perf_file,
            format=get_formatter(LogFormat.JSON),
            level="DEBUG",
            rotation="1 day",
            retention="7 days",
            compression="gz",
            enqueue=True,
            filter=perf_combined_filter,
            serialize=True,
        )

    # Add trace ID patcher
    logger.configure(patcher=trace_id_patcher)

    # Intercept standard library logging
    import logging

    class InterceptHandler(logging.Handler):
        """A custom logging handler that intercepts standard Python logging records
        and redirects them to Loguru.

        This ensures that all log messages, regardless of their origin (standard
        library `logging` module or Loguru), are processed by Loguru's configured
        sinks and formatters.
        """

        def emit(self, record: logging.LogRecord) -> None:
            """Emits a log record by redirecting it to Loguru.

            Args:
                record: The standard `logging.LogRecord` to be emitted.
            """
            # Get corresponding Loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = str(record.levelno)

            # Find caller
            frame: FrameType | None = sys._getframe(6)
            depth = 6
            while frame and frame.f_code.co_filename.endswith("logging/__init__.py"):
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Replace standard library logging handlers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Reduce noise from third-party libraries
    configure_third_party_logging()


def get_logger(_: str, **kwargs: Any) -> Logger:
    """Retrieves a Loguru logger instance, optionally with bound extra fields.

    This function acts as a wrapper around Loguru's global logger, allowing
    for the attachment of context-specific data that will be included in all
    subsequent log messages from this logger instance.

    Args:
        _: Placeholder for a name, as Loguru's global logger doesn't require one.
        **kwargs: Arbitrary keyword arguments representing extra fields to bind to the logger.

    Returns:
        A Loguru `Logger` instance.
    """
    if kwargs:
        # Bind extra fields to logger
        return logger.bind(**kwargs)

    return logger


# Convenience function for backward compatibility
def get_structured_logger(name: str, **extra_fields: Any) -> Logger:
    """Retrieves a structured logger with specified extra fields.

    This is a convenience function for backward compatibility, equivalent to `get_logger`.

    Args:
        name: The name of the logger (though not directly used by Loguru's global logger).
        **extra_fields: Additional key-value pairs to include in log records.

    Returns:
        A Loguru `Logger` instance with bound extra fields.
    """
    return get_logger(name, **extra_fields)


def log_performance(func_name: str | None = None, level: str = "INFO") -> Callable[..., Any]:
    """A decorator to log the execution time and success/failure of a function.

    This decorator can be applied to both synchronous and asynchronous functions.
    It measures the duration of the function call and logs it, along with
    information about whether the function completed successfully or raised an error.

    Args:
        func_name: Optional. A custom name to use in the log message for the function.
                   If `None`, the function's actual name will be used.
        level: The logging level at which to log the performance metrics (e.g., "INFO", "DEBUG").

    Returns:
        A decorator that wraps the function to add performance logging.
    """
    import functools
    import time

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000

                logger.log(
                    level,
                    f"Performance: {func_name or func.__name__} completed in {duration_ms:.2f}ms",
                    function_name=func_name or func.__name__,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                )

            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000

                logger.log(
                    level,
                    f"Performance: {func_name or func.__name__} completed in {duration_ms:.2f}ms",
                    function_name=func_name or func.__name__,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                )

            return result

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class LogContext:
    """A context manager for temporarily adding extra fields to log records.

    When entering the context, any keyword arguments provided to the constructor
    are bound to the Loguru logger, meaning they will be included in all log
    messages emitted within that context. This is useful for adding request-specific
    or operation-specific context to logs.
    """

    def __init__(self, **context: Any) -> None:
        """Initializes the LogContext with the given context fields.

        Args:
            **context: Arbitrary keyword arguments representing the context fields
                       to add to log records within this context.
        """
        self.context = context
        self.original_logger: Logger | None = None

    def __enter__(self) -> Logger:
        """Enters the context, binding the provided context fields to the logger.

        Returns:
            The Loguru `Logger` instance with the new context bound.
        """
        self.original_logger = logger
        return logger.bind(**self.context)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the context.

        Loguru automatically handles the unbinding of context fields when the
        context manager exits.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
            exc_val: The exception instance.
            exc_tb: The traceback object.
        """


def log_function_calls(include_args: bool = False, include_result: bool = False) -> Callable[..., Any]:
    """A decorator to log the entry and exit of a function, including arguments and results.

    This decorator provides visibility into function execution flow, which can be
    useful for debugging and understanding program behavior.

    Args:
        include_args: If `True`, function arguments will be included in the log.
        include_result: If `True`, the function's return value will be included in the log.

    Returns:
        A decorator that wraps the function to add call logging.
    """
    import functools

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            log_data: dict[str, Any] = {"function": func.__name__}

            if include_args:
                log_data["args"] = str(args) if args else None
                log_data["kwargs"] = kwargs if kwargs else None

            logger.debug(f"Calling function: {func.__name__}", **log_data)

            try:
                result = await func(*args, **kwargs)

                if include_result:
                    log_data["result"] = str(result)

                logger.debug(f"Function completed: {func.__name__}", **log_data)
                return result

            except Exception as e:
                log_data["error"] = str(e)
                logger.error(f"Function failed: {func.__name__}", **log_data)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            log_data: dict[str, Any] = {"function": func.__name__}

            if include_args:
                log_data["args"] = str(args) if args else None
                log_data["kwargs"] = kwargs if kwargs else None

            logger.debug(f"Calling function: {func.__name__}", **log_data)

            try:
                result = func(*args, **kwargs)

                if include_result:
                    log_data["result"] = str(result)

                logger.debug(f"Function completed: {func.__name__}", **log_data)
                return result

            except Exception as e:
                log_data["error"] = str(e)
                logger.error(f"Function failed: {func.__name__}", **log_data)
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def configure_third_party_logging() -> None:
    """Configures logging levels for common third-party libraries to reduce log noise.

    This function sets more restrictive logging levels (e.g., WARNING) for
    libraries that tend to produce a large volume of INFO or DEBUG level logs,
    making the application logs cleaner and more focused.
    """
    import logging

    # Set more restrictive levels for noisy libraries
    third_party_loggers = {
        "websockets": logging.WARNING,
        "urllib3": logging.WARNING,
        "asyncio": logging.WARNING,
        "aiohttp": logging.WARNING,
        "requests": logging.WARNING,
        "httpx": logging.WARNING,
        "sqlalchemy": logging.WARNING,
        "alembic": logging.WARNING,
        "boto3": logging.WARNING,
        "botocore": logging.WARNING,
        "paramiko": logging.WARNING,
        "pydantic": logging.WARNING,
    }

    for logger_name, level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(level)


def log_with_trace_id(level: str, message: str, trace_id: str | None = None, **kwargs: Any) -> None:
    """Logs a message with an explicit trace ID.

    If a `trace_id` is provided, it will be used for the log record. Otherwise,
    the currently active trace ID from the `TraceContext` will be used.

    Args:
        level: The logging level (e.g., "INFO", "ERROR").
        message: The log message string.
        trace_id: Optional. An explicit trace ID to associate with this log entry.
        **kwargs: Additional keyword arguments to include as extra fields in the log record.
    """
    from .trace_id import TraceContext

    if trace_id:
        with TraceContext(trace_id):
            logger.log(level, message, **kwargs)
    else:
        logger.log(level, message, **kwargs)


def log_exception_with_context(exc: Exception, level: str = "ERROR", message: str | None = None, **kwargs: Any) -> None:
    """Logs an exception with rich context, including trace ID and custom error details.

    This function enhances standard exception logging by extracting relevant
    information from `CoreError` instances (like error codes and details)
    and associating them with the log record.

    Args:
        exc: The exception object to log.
        level: The logging level for the exception (e.g., "ERROR", "CRITICAL").
        message: Optional. A custom message to prepend to the exception log.
        **kwargs: Additional keyword arguments to include as extra fields in the log record.
    """
    from asset_core.exceptions import CoreError

    log_message = message or f"Exception occurred: {exc}"

    # Add exception-specific context
    extra_context = kwargs.copy()
    extra_context["exception_type"] = exc.__class__.__name__

    if isinstance(exc, CoreError):
        extra_context["error_code"] = exc.error_code
        extra_context["exception_trace_id"] = exc.trace_id
        extra_context.update(exc.details)

    logger.log(level, log_message, **extra_context)


def create_traced_logger(name: str, **default_fields: Any) -> Logger:
    """Creates a Loguru logger instance that automatically includes a trace ID and default fields.

    This logger is useful for components that consistently need to log with
    a specific component name and other predefined context, while also ensuring
    traceability through a trace ID.

    Args:
        name: The name of the component or module associated with this logger.
        **default_fields: Default key-value pairs to include in every log record from this logger.

    Returns:
        A Loguru `Logger` instance with bound fields and trace ID patching enabled.
    """

    # Add trace ID to default fields
    fields = {"component": name, **default_fields}

    return logger.bind(**fields)


class TraceableLogger:
    """A wrapper around Loguru's logger that ensures a trace ID is always present in log records.

    This class provides a convenient interface for logging within components
    that require all their log messages to be associated with a trace ID,
    facilitating distributed tracing and debugging.
    """

    def __init__(self, name: str, **default_fields: Any) -> None:
        """Initializes the TraceableLogger.

        Args:
            name: The name of the logger, typically the module or component name.
            **default_fields: Default key-value pairs to include in every log record.
        """
        self.name = name
        self.default_fields = {"component": name, **default_fields}

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal method to log a message, ensuring trace ID is present.

        Args:
            level: The logging level (e.g., "DEBUG", "INFO").
            message: The log message string.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        from .trace_id import ensure_trace_id

        # Ensure we have a trace ID
        ensure_trace_id()

        # Merge fields
        fields = {**self.default_fields, **kwargs}

        # Log with bound fields
        bound_logger = logger.bind(**fields) if fields else logger
        bound_logger.log(level, message)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Logs a debug-level message.

        Args:
            message: The debug message string.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Logs an info-level message.

        Args:
            message: The info message string.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Logs a warning-level message.

        Args:
            message: The warning message string.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, exc: Exception | None = None, **kwargs: Any) -> None:
        """Logs an error-level message, optionally with an exception.

        Args:
            message: The error message string.
            exc: Optional. The exception object to log.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        if exc:
            log_exception_with_context(exc, "ERROR", message, **kwargs)
        else:
            self._log("ERROR", message, **kwargs)

    def critical(self, message: str, exc: Exception | None = None, **kwargs: Any) -> None:
        """Logs a critical-level message, optionally with an exception.

        Args:
            message: The critical message string.
            exc: Optional. The exception object to log.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        if exc:
            log_exception_with_context(exc, "CRITICAL", message, **kwargs)
        else:
            self._log("CRITICAL", message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Logs an exception message, typically used within an exception handler.

        This method automatically captures exception information from the current
        execution context and logs it at the ERROR level.

        Args:
            message: The message to log alongside the exception.
            **kwargs: Additional keyword arguments to include as extra fields.
        """
        import sys

        exc_info = sys.exc_info()
        if exc_info[1] and isinstance(exc_info[1], Exception):
            log_exception_with_context(exc_info[1], "ERROR", message, **kwargs)
        else:
            self.error(message, **kwargs)
