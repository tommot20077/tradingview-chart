"""Exception definitions for asset_core.

This module defines the base exception class `CoreError` and various
specific exception types used throughout the `asset_core` library.
It also provides utilities for enhancing exceptions with trace IDs
for improved observability and debugging.
"""

from datetime import datetime
from types import TracebackType
from typing import Any

from asset_core.observability.trace_id import get_formatted_trace_id


class CoreError(Exception):
    """Base exception for all asset_core errors.

    All custom exceptions within the `asset_core` library should inherit from this class.
    It provides standardized fields for error messages, error codes, and detailed information,
    including an automatically generated or provided trace ID for easier debugging and logging.

    Attributes:
        message (str): A human-readable error message.
        error_code (str): A standardized code for the error, defaulting to the class name.
        details (dict[str, Any]): A dictionary for additional, context-specific error details.
        trace_id (str): A unique identifier for tracing the error through system logs.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Initializes a new instance of the `CoreError` exception.

        Args:
            message (str): A human-readable description of the error.
            error_code (str | None): An optional, standardized code for the error.
                                     If `None`, the class name of the exception will be used.
            details (dict[str, Any] | None): An optional dictionary containing additional, context-specific
                                            details about the error. This can include any relevant data
                                            that helps in debugging or understanding the error.
            trace_id (str | None): An optional trace ID to associate with this error.
                                   If `None`, a new trace ID will be automatically generated and assigned.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

        # Automatically capture trace ID
        self.trace_id = trace_id if trace_id is not None else get_formatted_trace_id()

        # Add trace_id to details for easy access in tests
        self.details["trace_id"] = self.trace_id

    def __str__(self) -> str:
        """Returns a user-friendly string representation of the error.

        This method formats the error message to include the trace ID, error code (if different
        from the class name), the main message, and any additional details, making it suitable
        for logging and display to end-users.

        Returns:
            str: A formatted string representing the error.
        """
        parts = []

        # Add trace ID at the beginning for easy identification
        if self.trace_id and self.trace_id != "no-trace":
            parts.append(f"[{self.trace_id}]")

        # Add error code if different from class name
        if self.error_code != self.__class__.__name__:
            parts.append(f"[{self.error_code}]")

        # Add main message
        parts.append(self.message)

        # Add details (excluding trace_id since it's already shown)
        details_to_show = {k: v for k, v in self.details.items() if k != "trace_id"}
        if details_to_show:
            parts.append(f"Details: {details_to_show}")

        return " ".join(parts)

    def __repr__(self) -> str:
        """Returns a developer-friendly string representation of the error.

        This method provides a detailed representation of the `CoreError` instance,
        including its class name, message, error code, trace ID, and all details,
        which is useful for debugging and internal logging.

        Returns:
            str: A string that can be used to recreate the `CoreError` instance.
        """
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"trace_id='{self.trace_id}', "
            f"details={self.details}"
            f")"
        )


class ConfigurationError(CoreError):
    """Raised when an issue related to application configuration occurs.

    This exception indicates problems such as missing required settings,
    invalid configuration values, or malformed configuration files.
    """

    pass


class DataProviderError(CoreError):
    """Base exception for errors originating from data providers.

    This exception serves as a superclass for all errors related to interacting
    with external data sources, such as exchanges or market data APIs.
    Specific subclasses provide more granular error types.
    """

    pass


class ConnectionError(DataProviderError):
    """Raised when a connection to a data provider fails or is lost.

    This exception specifically indicates issues with network connectivity
    to the data source, preventing data exchange.
    """

    pass


class AuthenticationError(DataProviderError):
    """Raised when authentication with a data provider fails.

    This exception signifies that the provided credentials (e.g., API keys,
    secrets) are invalid or insufficient to access the data provider's services.
    """

    pass


class RateLimitError(DataProviderError):
    """Raised when an operation is rejected due to exceeding a rate limit.

    This exception indicates that the system has sent too many requests to an
    external service (e.g., an exchange API) within a given time frame.
    It may include a `retry_after` field suggesting when to retry.

    Attributes:
        retry_after (int | None): The number of seconds to wait before retrying the operation.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a new instance of the `RateLimitError` exception.

        Args:
            message (str): A human-readable description of the error.
            retry_after (int | None): Optional. The number of seconds to wait before retrying the operation.
                                      This value is typically provided by the rate-limited service.
            **kwargs (Any): Additional keyword arguments to pass to the base `CoreError` constructor.
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after is not None:
            self.details["retry_after"] = retry_after


class StorageError(CoreError):
    """Base exception for errors related to data storage operations.

    This exception serves as a superclass for all errors that occur during
    interactions with storage backends, such as databases, file systems,
    or object storage. Specific subclasses provide more granular error types.
    """

    pass


class StorageConnectionError(StorageError):
    """Raised when a connection to the storage backend fails or is lost.

    This error specifically indicates issues with establishing or maintaining
    connectivity to the data persistence layer.
    """

    pass


class StorageWriteError(StorageError):
    """Raised when an attempt to write data to storage fails.

    This can occur due to various reasons such as insufficient permissions,
    disk full conditions, data integrity violations, or issues with the
    storage medium itself.
    """

    pass


class StorageReadError(StorageError):
    """Raised when an attempt to read data from storage fails.

    This can occur due to reasons such as data not found, corrupted data,
    access permissions issues, or problems with the storage medium.
    """

    pass


class EventBusError(CoreError):
    """Base exception for errors related to the event bus.

    This exception serves as a superclass for all errors that occur during
    event publishing, subscription, or processing within the event bus system.
    """

    pass


class ValidationError(CoreError):
    """Raised when data validation fails.

    This exception indicates that input data or an object's state does not
    conform to expected rules or constraints.
    """

    pass


class NetworkError(CoreError):
    """Base exception for network-related errors.

    This exception serves as a superclass for all errors that occur during
    network communication, such as issues with sockets, protocols, or connectivity.
    """

    pass


class WebSocketError(NetworkError):
    """Raised when an operation involving WebSockets fails.

    This exception indicates issues specific to WebSocket communication,
    such as protocol errors, unexpected disconnections, or message handling problems.
    """

    pass


class TimeoutError(NetworkError):
    """Raised when an operation exceeds its allotted time limit.

    This exception indicates that a network request or other time-sensitive
    operation did not complete within the expected duration.
    """

    pass


class NotSupportedError(CoreError):
    """Raised when a requested operation is not supported by the current backend.

    This exception indicates that the requested functionality is not available
    or implemented in the current storage backend or configuration.
    """

    pass


class DataValidationError(ValidationError):
    """Raised when specific data fields fail validation.

    This exception extends `ValidationError` by providing more context about
    which field failed validation and what its invalid value was.

    Attributes:
        field_name (str | None): The name of the field that failed validation.
        field_value (Any | None): The value of the field that failed validation.
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        field_value: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a new instance of the `DataValidationError`.

        Args:
            message: A human-readable description of the validation error.
            field_name: Optional. The name of the field that caused the validation failure.
            field_value: Optional. The value of the field that failed validation.
            **kwargs: Additional keyword arguments to pass to the base `CoreError` constructor.
        """
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value
        if field_name:
            self.details["field_name"] = field_name
        if field_value is not None:
            self.details["field_value"] = str(field_value)


class ResourceExhaustedError(CoreError):
    """Raised when a system resource limit has been reached or exceeded.

    This exception indicates that an operation cannot proceed because a critical
    resource (e.g., memory, file handles, connections) is fully utilized.

    Attributes:
        resource_type (str | None): The type of resource that was exhausted (e.g., "memory", "connections").
        current_usage (float | None): The current usage level of the resource.
        limit (float | None): The maximum allowed limit for the resource.
    """

    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        current_usage: float | None = None,
        limit: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a new instance of the `ResourceExhaustedError`.

        Args:
            message: A human-readable description of the error.
            resource_type: Optional. The type of resource that was exhausted (e.g., 'memory', 'connections').
            current_usage: Optional. The current usage level of the resource.
            limit: Optional. The maximum allowed limit for the resource.
            **kwargs: Additional keyword arguments to pass to the base `CoreError` constructor.
        """
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit
        if resource_type:
            self.details["resource_type"] = resource_type
        if current_usage is not None:
            self.details["current_usage"] = current_usage
        if limit is not None:
            self.details["limit"] = limit


class CircuitBreakerError(CoreError):
    """Raised when a circuit breaker is open, preventing an operation.

    This exception indicates that a service or component is temporarily unavailable
    because its circuit breaker has tripped, typically due to a high rate of failures.

    Attributes:
        service_name (str | None): The name of the service or component that is circuit-broken.
        failure_count (int | None): The current number of consecutive failures that led to the circuit breaking.
        failure_threshold (int | None): The threshold of failures that triggers the circuit breaker.
        next_retry_time (datetime | None): The UTC time when the circuit breaker will next allow a retry attempt.
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        failure_count: int | None = None,
        failure_threshold: int | None = None,
        next_retry_time: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a new instance of the `CircuitBreakerError`.

        Args:
            message: A human-readable description of the error.
            service_name: Optional. The name of the service or component that is circuit-broken.
            failure_count: Optional. The current number of consecutive failures.
            failure_threshold: Optional. The failure threshold that triggered the circuit breaker.
            next_retry_time: Optional. The UTC time when the circuit breaker will next allow a retry.
            **kwargs: Additional keyword arguments to pass to the base `CoreError` constructor.
        """
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold
        self.next_retry_time = next_retry_time
        if service_name:
            self.details["service_name"] = service_name
        if failure_count is not None:
            self.details["failure_count"] = failure_count
        if failure_threshold is not None:
            self.details["failure_threshold"] = failure_threshold
        if next_retry_time is not None:
            self.details["next_retry_time"] = next_retry_time.isoformat()


def create_traced_exception(exc_class: type[Exception], message: str, **kwargs: Any) -> Exception:
    """Creates an exception instance, ensuring it includes trace ID information.

    If `exc_class` is a subclass of `CoreError`, the trace ID is handled internally.
    Otherwise, the trace ID is prepended to the exception message.

    Args:
        exc_class: The exception class to instantiate.
        message: The primary error message for the exception.
        **kwargs: Additional keyword arguments to pass to the exception's constructor.

    Returns:
        An instance of the specified exception class, enhanced with trace ID.
    """
    if issubclass(exc_class, CoreError):
        return exc_class(message, **kwargs)
    else:
        # For non-CoreError exceptions, create a wrapper
        trace_id = get_formatted_trace_id()
        enhanced_message = f"[{trace_id}] {message}"
        return exc_class(enhanced_message)


def enhance_exception_with_trace_id(exc: BaseException) -> BaseException:
    """Enhances an existing exception object by adding trace ID information to its message.

    If the exception is already a `CoreError` (which inherently supports trace IDs),
    it is returned as is. For other exception types, the current trace ID is prepended
    to the exception's message.

    Args:
        exc: The exception instance to enhance.

    Returns:
        The enhanced exception instance (may be the same instance if already enhanced).
    """
    if isinstance(exc, CoreError):
        # Already has trace ID
        return exc

    # For other exceptions, modify the message if possible
    trace_id = get_formatted_trace_id()
    if trace_id != "no-trace":
        try:
            # Try to enhance the exception message
            current_message = str(exc)
            if not current_message.startswith(f"[{trace_id}]"):
                exc.args = (f"[{trace_id}] {current_message}",) + exc.args[1:]
        except Exception:
            # If we can't modify the exception, that's ok
            pass

    return exc


class TraceIdExceptionHandler:
    """A global exception handler that automatically injects trace IDs into uncaught exceptions.

    This handler intercepts exceptions that are not caught by application code
    and enhances them with the current trace ID, making it easier to correlate
    errors in logs with specific requests or operations.
    """

    def __init__(self) -> None:
        self._original_handler: Any = None

    def install(self) -> None:
        """Installs this handler as the global exception hook.

        This replaces `sys.excepthook` with the handler's `_handle_exception` method,
        ensuring all uncaught exceptions are processed.
        """
        import sys

        self._original_handler = sys.excepthook
        sys.excepthook = self._handle_exception

    def uninstall(self) -> None:
        """Uninstalls the global exception handler, restoring the original hook.

        This should be called to clean up the exception hook when the application
        is shutting down or the handler is no longer needed.
        """
        import sys

        if self._original_handler:
            # Only restore if we are the current handler
            if sys.excepthook == self._handle_exception:
                sys.excepthook = self._original_handler
            self._original_handler = None

    def _handle_exception(
        self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None
    ) -> None:
        """Internal method to handle uncaught exceptions.

        This method is set as `sys.excepthook`. It enhances the exception with
        trace ID information and then calls the original exception handler.

        Args:
            exc_type: The type of the exception.
            exc_value: The exception instance.
            exc_traceback: The traceback object.
        """
        # Enhance the exception with trace ID
        enhanced_exc = enhance_exception_with_trace_id(exc_value)

        # Call the original handler with the enhanced exception
        if self._original_handler:
            self._original_handler(exc_type, enhanced_exc, exc_traceback)
        else:
            # Default behavior
            import traceback

            traceback.print_exception(exc_type, enhanced_exc, exc_traceback)


# Global instance for easy access
_global_exception_handler = TraceIdExceptionHandler()


def install_global_exception_handler() -> None:
    """Installs the global exception handler to automatically add trace IDs to uncaught exceptions.

    This function should be called early in the application's lifecycle to ensure
    all unhandled errors are traceable.
    """
    _global_exception_handler.install()


def uninstall_global_exception_handler() -> None:
    """Uninstall global exception handler."""
    _global_exception_handler.uninstall()
