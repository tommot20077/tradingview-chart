"""Common type aliases and definitions for asset_core.

This module defines a comprehensive set of type aliases and new types
used throughout the `asset_core` library. These types enhance readability,
maintainability, and provide stronger type checking for various data
structures, financial values, and system components.
"""

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, NewType, Protocol, TypeVar

from pydantic import Field

from .. import exceptions
from ..models.events import BaseEvent
from ..models.kline import Kline
from ..models.trade import Trade

# Generic type variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Basic type aliases
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]
"""Type alias for any valid JSON value (string, number, boolean, null, object, or array)."""
JsonDict = dict[str, JsonValue]
"""Type alias for a JSON object (dictionary with string keys and JSON values)."""
JsonList = list[JsonValue]
"""Type alias for a JSON array (list of JSON values)."""

# Timestamp types
Timestamp = datetime
TimestampMs = int  # Milliseconds since epoch
"""Type alias for an integer representing milliseconds since the Unix epoch."""
TimestampUs = int  # Microseconds since epoch
"""Type alias for an integer representing microseconds since the Unix epoch."""

# Price and quantity types - using Pydantic for validation
Price = Annotated[Decimal, Field(gt=0, decimal_places=12, description="Positive price value")]
"""Annotated type for a positive Decimal price value with 12 decimal places of precision."""
Quantity = Annotated[Decimal, Field(ge=0, decimal_places=12, description="Non-negative quantity")]
"""Annotated type for a non-negative Decimal quantity value with 12 decimal places of precision."""
Volume = Annotated[Decimal, Field(ge=0, decimal_places=12, description="Non-negative volume")]
"""Annotated type for a non-negative Decimal volume value with 12 decimal places of precision."""

# Symbol and identifier types - using NewType for semantic distinction
Symbol = NewType("Symbol", str)
"""NewType for a trading symbol (e.g., "BTCUSDT")."""
ExchangeName = NewType("ExchangeName", str)
"""NewType for the name of a cryptocurrency exchange (e.g., "Binance")."""
TradeId = NewType("TradeId", str)
"""NewType for a unique trade identifier."""
OrderId = NewType("OrderId", str)
"""NewType for a unique order identifier."""

# Event handling types
EventHandler = Callable[[BaseEvent], None]
"""Type alias for a synchronous callable that handles a `BaseEvent`."""
AsyncEventHandler = Callable[[BaseEvent], Any]  # Returns awaitable
"""Type alias for an asynchronous callable that handles a `BaseEvent`."""

# Data streaming types
TradeStream = AsyncIterator[Trade]
"""Type alias for an asynchronous iterator that yields `Trade` objects."""
KlineStream = AsyncIterator[Kline]
"""Type alias for an asynchronous iterator that yields `Kline` objects."""
DataStream = AsyncIterator[T]
"""Type alias for a generic asynchronous iterator that yields objects of type `T`."""

# Configuration types
ConfigDict = dict[str, Any]
"""Type alias for a dictionary representing configuration settings."""
EnvironmentName = NewType("EnvironmentName", str)
"""NewType for the name of a deployment environment (e.g., "development", "production")."""
AppName = NewType("AppName", str)
"""NewType for the name of an application."""

# Network types
URL = NewType("URL", str)
"""NewType for a Uniform Resource Locator string."""
HostPort = tuple[str, int]
"""Type alias for a tuple representing a host and port combination (e.g., ("localhost", 8080))."""
Timeout = Annotated[float, Field(gt=0, description="Positive timeout value in seconds")]
"""Annotated type for a positive float value representing a timeout duration in seconds."""

# Error handling types
ErrorCode = NewType("ErrorCode", str)
"""NewType for a standardized error code string."""
ErrorMessage = NewType("ErrorMessage", str)
"""NewType for a human-readable error message string."""
ErrorDetails = dict[str, Any]
"""Type alias for a dictionary containing additional error details."""

# Storage types
StorageKey = NewType("StorageKey", str)
"""NewType for a key used in storage operations."""
StorageValue = Any
"""Type alias for any value stored in the storage layer."""
QueryFilter = dict[str, Any]
"""Type alias for a dictionary representing query filtering criteria."""
QueryLimit = Annotated[int, Field(ge=1, description="Positive query limit")]
"""Annotated type for a positive integer representing a query result limit."""
QueryOffset = Annotated[int, Field(ge=0, description="Non-negative query offset")]
"""Annotated type for a non-negative integer representing a query result offset."""

# Pagination types
PageSize = Annotated[int, Field(ge=1, le=1000, description="Page size between 1 and 1000")]
"""Annotated type for an integer representing the number of items per page, between 1 and 1000."""
PageNumber = Annotated[int, Field(ge=1, description="Page number starting from 1")]
"""Annotated type for an integer representing the page number, starting from 1."""
TotalCount = Annotated[int, Field(ge=0, description="Non-negative total count")]
"""Annotated type for a non-negative integer representing a total count."""

# Performance and monitoring types
Latency = Annotated[float, Field(ge=0, description="Latency in milliseconds")]
"""Annotated type for a non-negative float representing latency in milliseconds."""
MemoryUsage = Annotated[int, Field(ge=0, description="Memory usage in bytes")]
"""Annotated type for a non-negative integer representing memory usage in bytes."""
CPUUsage = Annotated[float, Field(ge=0, le=100, description="CPU usage percentage (0-100)")]
"""Annotated type for a float representing CPU usage percentage (0-100)."""
ConnectionCount = Annotated[int, Field(ge=0, description="Non-negative connection count")]
"""Annotated type for a non-negative integer representing a connection count."""

# Data validation types
ValidationRule = Callable[[Any], bool]
"""Type alias for a callable that takes any value and returns a boolean indicating validity."""
ValidatorFunc = Callable[[Any], Any]
"""Type alias for a callable that performs validation and potentially transforms a value."""
ValidationError = exceptions.ValidationError
"""Type alias for the specific `ValidationError` defined in the exceptions module."""

# Trading-specific types
PriceLevel = tuple[Price, Quantity]  # Price and quantity at that level
"""Type alias for a tuple representing a price level in an order book (price, quantity)."""
OrderBook = dict[str, list[PriceLevel]]  # bid/ask levels
"""Type alias for a dictionary representing an order book (e.g., {"bids": [...], "asks": [...]})."""
TickerData = dict[str, Any]
"""Type alias for a dictionary containing ticker information for a trading pair."""
ExchangeInfo = dict[str, Any]
"""Type alias for a dictionary containing general exchange information."""
SymbolInfo = dict[str, Any]
"""Type alias for a dictionary containing detailed information about a trading symbol."""
# Aggregation types
AggregationPeriod = str  # e.g., "1m", "5m", "1h", "1d"
"""Type alias for a string representing an aggregation period (e.g., "1m", "5m", "1h", "1d")."""
AggregationFunction = Callable[[list[T]], T]
"""Type alias for a callable that aggregates a list of items of type `T` into a single item of type `T`."""

# Filter and selector types
SymbolFilter = Callable[[Symbol], bool]
"""Type alias for a callable that filters `Symbol` objects."""
EventFilter = Callable[[BaseEvent], bool]
"""Type alias for a callable that filters `BaseEvent` objects."""
DataFilter = Callable[[T], bool]
"""Type alias for a generic callable that filters objects of type `T`."""

# Subscription types
SubscriptionId = NewType("SubscriptionId", str)
"""NewType for a unique subscription identifier string."""
SubscriptionCallback = Callable[[T], None]
"""Type alias for a callable that serves as a callback for a subscription."""
SubscriptionFilter = Callable[[T], bool]
"""Type alias for a callable that filters items for a subscription."""

# Provider types
ProviderName = NewType("ProviderName", str)
"""NewType for the name of a data provider (e.g., "BinanceProvider")."""
ProviderConfig = dict[str, Any]
"""Type alias for a dictionary containing configuration settings for a data provider."""
ConnectionString = NewType("ConnectionString", str)
"""NewType for a database or service connection string."""

# Observer pattern types
Observer = Callable[[T], None]
"""Type alias for a callable that observes changes in a subject."""
Subject = Any  # Object that can be observed
"""Type alias for an object that can be observed in the observer pattern."""

# Cache types
CacheKey = NewType("CacheKey", str)
"""NewType for a key used in caching mechanisms."""
CacheValue = Any
"""Type alias for any value stored in a cache."""
CacheTTL = Annotated[int, Field(gt=0, description="Cache TTL in seconds")]
"""Annotated type for a positive integer representing the Time-To-Live (TTL) of a cache entry in seconds."""

# Serialization types
SerializedData = NewType("SerializedData", str)
"""NewType for data that has been serialized into a string format (e.g., JSON, XML)."""
DeserializedData = Any
"""Type alias for data that has been deserialized from a string into a Python object."""
SerializationFormat = NewType("SerializationFormat", str)  # e.g., "json", "pickle", "msgpack"
"""NewType for a string that specifies the serialization format (e.g., 'json', 'pickle')."""

# Logging types
LogLevel = NewType("LogLevel", str)
"""NewType for a string representing a logging level (e.g., 'INFO', 'DEBUG')."""
LogMessage = NewType("LogMessage", str)
"""NewType for a log message string."""
LogContext = dict[str, Any]
"""Type alias for a dictionary providing context for a log entry."""

# Metrics types
MetricName = NewType("MetricName", str)
"""NewType for the name of a metric (e.g., 'cpu_usage', 'latency')."""
MetricValue = int | float
"""Type alias for the value of a metric, which can be an integer or a float."""
MetricTags = dict[str, str]
"""Type alias for a dictionary of tags (key-value pairs) to associate with a metric."""
MetricTimestamp = datetime
"""Type alias for a datetime object representing the timestamp of a metric recording."""

# Rate limiting types
RateLimit = Annotated[int, Field(gt=0, description="Requests per time period")]
"""Annotated type for a positive integer representing the maximum number of requests allowed within a specific time period."""
RatePeriod = Annotated[int, Field(gt=0, description="Time period in seconds")]
"""Annotated type for a positive integer representing the time period in seconds for rate limiting."""
RateWindow = tuple[datetime, datetime]
"""Type alias for a tuple representing a time window for rate limiting, defined by a start and end datetime."""

# Circuit breaker types
FailureThreshold = Annotated[int, Field(gt=0, description="Positive failure threshold")]
"""Annotated type for a positive integer representing the number of consecutive failures before a circuit breaks."""
RecoveryTimeout = Annotated[int, Field(gt=0, description="Recovery timeout in seconds")]
"""Annotated type for a positive integer representing the time in seconds before a half-open circuit attempts to close."""
CircuitState = NewType("CircuitState", str)  # "closed", "open", "half-open"
"""NewType for a string representing the state of a circuit breaker (e.g., 'closed', 'open', 'half-open')."""

# Retry policy types
RetryAttempts = Annotated[int, Field(ge=0, description="Non-negative retry attempts")]
"""Annotated type for a non-negative integer representing the number of retry attempts."""
RetryDelay = Annotated[float, Field(gt=0, description="Positive retry delay in seconds")]
"""Annotated type for a positive float representing the delay in seconds between retry attempts."""
RetryBackoff = Annotated[float, Field(gt=1, description="Backoff multiplier greater than 1")]
"""Annotated type for a float representing the backoff multiplier for retry delays (must be greater than 1)."""

# Health check types
HealthStatus = NewType("HealthStatus", str)  # "healthy", "unhealthy", "degraded"
"""NewType for a string representing the health status of a component or system (e.g., 'healthy', 'unhealthy', 'degraded')."""
HealthCheckResult = dict[str, Any]
"""Type alias for a dictionary containing the results of a health check."""

# Common collections
SymbolList = list[Symbol]
"""Type alias for a list of `Symbol` objects."""
PriceList = list[Price]
"""Type alias for a list of `Price` objects."""
TimestampList = list[Timestamp]
"""Type alias for a list of `Timestamp` objects."""

# Optional versions of common types
OptionalPrice = Price | None
"""Type alias for an optional `Price` value, which can be `Price` or `None`."""
OptionalQuantity = Quantity | None
"""Type alias for an optional `Quantity` value, which can be `Quantity` or `None`."""
OptionalTimestamp = Timestamp | None
"""Type alias for an optional `Timestamp` value, which can be `Timestamp` or `None`."""
OptionalSymbol = Symbol | None
"""Type alias for an optional `Symbol` value, which can be `Symbol` or `None`."""


# Result types for error handling
class Result[T]:
    """Generic result type for operations that can fail.

    This class serves as a base for `Success` and `Failure` types,
    providing a common interface for handling operation outcomes.
    It uses generics to allow the `Success` variant to hold a value of any type.

    Type Parameters:
        T: The type of the value held by a `Success` result.
    """

    pass


class Success[T](Result[T]):
    """Represents a successful result containing a value.

    This class indicates that an operation completed without errors and holds
    the resulting value.

    Type Parameters:
        T: The type of the successful result value.

    Attributes:
        value (T): The successful result value.
    """

    def __init__(self, value: T):
        self.value = value


class Failure[T](Result[T]):
    """Represents a failed result containing an error.

    This class indicates that an operation failed and holds the exception
    that caused the failure.

    Type Parameters:
        T: The type parameter is unused but included for consistency with `Success`.

    Attributes:
        error (Exception): The exception representing the failure.
    """

    def __init__(self, error: Exception):
        self.error = error


# Union types for common patterns
SuccessOrFailure = Success[T] | Failure[T]
"""Type alias for a result that can be either a `Success` or a `Failure`."""
PriceOrVolume = Price | Volume
"""Type alias for a value that can represent either a `Price` or a `Volume`."""
TimeOrOffset = Timestamp | int
"""Type alias for a value that can be either a `Timestamp` or an integer offset."""

# Functional types
Predicate = Callable[[T], bool]
"""Type alias for a callable that takes a value of type `T` and returns a boolean."""
Transformer = Callable[[T], K]
"""Type alias for a callable that transforms a value of type `T` to a value of type `K`."""
Reducer = Callable[[T, K], T]
"""Type alias for a callable that reduces a sequence of values of type `K` into a single value of type `T`."""
Mapper = Callable[[T], K]
"""Type alias for a callable that maps a value of type `T` to a value of type `K`."""

# Protocol types (for structural typing)


class Identifiable(Protocol[T]):
    """Protocol for objects that have a unique identifier.

    Classes implementing this protocol must have an 'id' attribute.

    Type Parameters:
        T: The type of the identifier.
    """

    id: T


class Timestamped(Protocol):
    """Protocol for objects that have an associated timestamp.

    Classes implementing this protocol must have a `timestamp` attribute.
    """

    timestamp: Timestamp


class Symbolized(Protocol):
    """Protocol for objects that are associated with a trading symbol.

    Classes implementing this protocol must have a `symbol` attribute.
    """

    symbol: Symbol


class Serializable(Protocol):
    """Protocol for objects that can be serialized to and from a dictionary.

    This protocol defines a standard interface for serialization, ensuring that
    objects can be easily converted to a dictionary format and reconstructed.
    """

    def to_dict(self) -> dict[str, Any]:
        """Converts the object to a dictionary.

        Returns:
            A dictionary representation of the object.
        """
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        """Creates an object from a dictionary.

        Args:
            data: A dictionary containing the object's data.

        Returns:
            An instance of the class.
        """
        ...


class Validatable(Protocol):
    """Protocol for objects that can perform self-validation.

    This protocol ensures that an object can verify its own state, typically
    by checking its attributes against a set of rules.
    """

    def validate(self) -> bool:
        """Performs self-validation on the object.

        Returns:
            True if the object is valid, False otherwise.
        """
        ...


# Type aliases for protocols
IdentifiableT = TypeVar("IdentifiableT", bound=Identifiable)
TimestampedT = TypeVar("TimestampedT", bound=Timestamped)
SymbolizedT = TypeVar("SymbolizedT", bound=Symbolized)
SerializableT = TypeVar("SerializableT", bound=Serializable)
ValidatableT = TypeVar("ValidatableT", bound=Validatable)

# Export commonly used types for convenience
__all__ = [
    # Basic types
    "JsonValue",
    "JsonDict",
    "JsonList",
    "Timestamp",
    "TimestampMs",
    "TimestampUs",
    # Validated financial types (Pydantic)
    "Price",
    "Quantity",
    "Volume",
    # Identifier types (NewType)
    "Symbol",
    "ExchangeName",
    "TradeId",
    "OrderId",
    # Event types
    "EventHandler",
    "AsyncEventHandler",
    # Stream types
    "TradeStream",
    "KlineStream",
    "DataStream",
    # Configuration types
    "ConfigDict",
    "EnvironmentName",
    "AppName",
    # Network types
    "URL",
    "HostPort",
    "Timeout",
    # Trading types
    "PriceLevel",
    "OrderBook",
    "TickerData",
    "ExchangeInfo",
    "SymbolInfo",
    # Filter types
    "SymbolFilter",
    "EventFilter",
    "DataFilter",
    # Subscription types
    "SubscriptionId",
    "SubscriptionCallback",
    "SubscriptionFilter",
    # Storage and pagination types
    "StorageKey",
    "QueryLimit",
    "QueryOffset",
    "PageSize",
    "PageNumber",
    "TotalCount",
    # Performance types
    "Latency",
    "MemoryUsage",
    "CPUUsage",
    "ConnectionCount",
    # Provider types
    "ProviderName",
    "ConnectionString",
    # Cache types
    "CacheKey",
    "CacheTTL",
    # Rate limiting types
    "RateLimit",
    "RatePeriod",
    "FailureThreshold",
    "RecoveryTimeout",
    "RetryAttempts",
    "RetryDelay",
    "RetryBackoff",
    # Health and status types
    "HealthStatus",
    "CircuitState",
    # Logging and metrics types
    "LogLevel",
    "LogMessage",
    "MetricName",
    # Error handling types
    "ErrorCode",
    "ErrorMessage",
    # Result types
    "Result",
    "Success",
    "Failure",
    "SuccessOrFailure",
    # Protocol types
    "Identifiable",
    "Timestamped",
    "Symbolized",
    "Serializable",
    "Validatable",
    # Functional types
    "Predicate",
    "Transformer",
    "ValidationError",
    "Reducer",
    "Mapper",
    # Optional types
    "OptionalPrice",
    "OptionalQuantity",
    "OptionalTimestamp",
    "OptionalSymbol",
    # Collection types
    "SymbolList",
    "PriceList",
    "TimestampList",
    # Generic type variables
    "T",
    "K",
    "V",
    "IdentifiableT",
    "TimestampedT",
    "SymbolizedT",
    "SerializableT",
    "ValidatableT",
]
