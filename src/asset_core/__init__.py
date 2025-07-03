"""Asset Core - Core library for asset trading data infrastructure."""

# Configuration
# Models and data structures
# Network components
# Storage components
# Event system
# Observability
# Patterns
# Providers
# Type definitions
from . import config, events, models, network, observability, patterns, providers, storage, types

# Exceptions
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

__version__ = "0.2.2"

__all__ = [
    "__version__",
    # Modules
    "config",
    "models",
    "network",
    "storage",
    "events",
    "observability",
    "patterns",
    "providers",
    "types",
    # Exceptions
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
