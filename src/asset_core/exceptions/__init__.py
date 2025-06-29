"""Asset core exceptions package.

This package contains all core exception classes for the asset_core library.
All exceptions inherit from CoreError which provides structured error handling
with error codes, messages, and additional details.
"""

from .core import (
    AuthenticationError,
    CircuitBreakerError,
    ConfigurationError,
    ConnectionError,
    CoreError,
    DataProviderError,
    DataValidationError,
    EventBusError,
    NetworkError,
    RateLimitError,
    ResourceExhaustedError,
    StorageConnectionError,
    StorageError,
    StorageReadError,
    StorageWriteError,
    TimeoutError,
    TraceIdExceptionHandler,
    ValidationError,
    WebSocketError,
    create_traced_exception,
    enhance_exception_with_trace_id,
    install_global_exception_handler,
    uninstall_global_exception_handler,
)

__all__ = [
    # Core exception classes
    "CoreError",
    "ConfigurationError",
    "DataProviderError",
    "ConnectionError",
    "AuthenticationError",
    "RateLimitError",
    "StorageError",
    "StorageConnectionError",
    "StorageWriteError",
    "StorageReadError",
    "EventBusError",
    "ValidationError",
    "NetworkError",
    "WebSocketError",
    "TimeoutError",
    "DataValidationError",
    "ResourceExhaustedError",
    "CircuitBreakerError",
    # Trace ID enhanced exception utilities
    "create_traced_exception",
    "enhance_exception_with_trace_id",
    "TraceIdExceptionHandler",
    "install_global_exception_handler",
    "uninstall_global_exception_handler",
]
