"""Exception definitions for asset_core."""

from datetime import datetime
from types import TracebackType
from typing import Any

from ..observability.trace_id import get_formatted_trace_id


class CoreError(Exception):
    """Base exception for all asset_core errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Initialize CoreError.

        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Optional additional error details
            trace_id: Optional trace ID. If None, uses current trace ID
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
        """String representation of the error."""
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
        """Developer-friendly representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"trace_id='{self.trace_id}', "
            f"details={self.details}"
            f")"
        )


class ConfigurationError(CoreError):
    """Raised when there's a configuration error."""

    pass


class DataProviderError(CoreError):
    """Base exception for data provider errors."""

    pass


class ConnectionError(DataProviderError):
    """Raised when connection to data provider fails."""

    pass


class AuthenticationError(DataProviderError):
    """Raised when authentication with data provider fails."""

    pass


class RateLimitError(DataProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize RateLimitError.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            **kwargs: Additional arguments for CoreError
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after is not None:
            self.details["retry_after"] = retry_after


class StorageError(CoreError):
    """Base exception for storage errors."""

    pass


class StorageConnectionError(StorageError):
    """Raised when connection to storage fails."""

    pass


class StorageWriteError(StorageError):
    """Raised when writing to storage fails."""

    pass


class StorageReadError(StorageError):
    """Raised when reading from storage fails."""

    pass


class EventBusError(CoreError):
    """Base exception for event bus errors."""

    pass


class ValidationError(CoreError):
    """Raised when data validation fails."""

    pass


class NetworkError(CoreError):
    """Base exception for network-related errors."""

    pass


class WebSocketError(NetworkError):
    """Raised when WebSocket operations fail."""

    pass


class TimeoutError(NetworkError):
    """Raised when an operation times out."""

    pass


class DataValidationError(ValidationError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        field_value: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize DataValidationError.

        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            **kwargs: Additional arguments for CoreError
        """
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value
        if field_name:
            self.details["field_name"] = field_name
        if field_value is not None:
            self.details["field_value"] = str(field_value)


class ResourceExhaustedError(CoreError):
    """Raised when system resources are exhausted."""

    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        current_usage: float | None = None,
        limit: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ResourceExhaustedError.

        Args:
            message: Error message
            resource_type: Type of resource that is exhausted (e.g., 'memory', 'connections')
            current_usage: Current resource usage
            limit: Resource limit
            **kwargs: Additional arguments for CoreError
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
    """Raised when circuit breaker is triggered."""

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
        """Initialize CircuitBreakerError.

        Args:
            message: Error message
            service_name: Name of the service that is circuit broken
            failure_count: Current failure count
            failure_threshold: Failure threshold that triggered the circuit breaker
            next_retry_time: When the circuit breaker will next allow a retry
            **kwargs: Additional arguments for CoreError
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
    """Create an exception with automatic trace ID injection.

    Args:
        exc_class: Exception class to instantiate
        message: Error message
        **kwargs: Additional arguments for the exception

    Returns:
        Exception instance with trace ID
    """
    if issubclass(exc_class, CoreError):
        return exc_class(message, **kwargs)
    else:
        # For non-CoreError exceptions, create a wrapper
        trace_id = get_formatted_trace_id()
        enhanced_message = f"[{trace_id}] {message}"
        return exc_class(enhanced_message)


def enhance_exception_with_trace_id(exc: BaseException) -> BaseException:
    """Enhance an existing exception with trace ID information.

    Args:
        exc: The exception to enhance

    Returns:
        Enhanced exception (may be the same instance if already enhanced)
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
    """Global exception handler that ensures all exceptions include trace ID."""

    def __init__(self) -> None:
        self._original_handler: Any = None

    def install(self) -> None:
        """Install the global exception handler."""
        import sys

        self._original_handler = sys.excepthook
        sys.excepthook = self._handle_exception

    def uninstall(self) -> None:
        """Uninstall the global exception handler."""
        import sys

        if self._original_handler:
            # Only restore if we are the current handler
            if sys.excepthook == self._handle_exception:
                sys.excepthook = self._original_handler
            self._original_handler = None

    def _handle_exception(
        self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None
    ) -> None:
        """Handle uncaught exceptions by adding trace ID."""
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
    """Install global exception handler to add trace IDs to all uncaught exceptions."""
    _global_exception_handler.install()


def uninstall_global_exception_handler() -> None:
    """Uninstall global exception handler."""
    _global_exception_handler.uninstall()
