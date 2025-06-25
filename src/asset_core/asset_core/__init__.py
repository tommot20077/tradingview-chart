"""Asset Core - Core library for asset trading data infrastructure."""

from .exceptions import (
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
    ValidationError,
    WebSocketError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
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
]
