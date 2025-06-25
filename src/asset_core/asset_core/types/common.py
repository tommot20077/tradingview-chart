"""Common type aliases and definitions for asset_core."""

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
JsonDict = dict[str, JsonValue]
JsonList = list[JsonValue]

# Timestamp types
Timestamp = datetime
TimestampMs = int  # Milliseconds since epoch
TimestampUs = int  # Microseconds since epoch

# Price and quantity types - using Pydantic for validation
Price = Annotated[Decimal, Field(gt=0, decimal_places=8, description="Positive price value")]
Quantity = Annotated[Decimal, Field(ge=0, decimal_places=8, description="Non-negative quantity")]
Volume = Annotated[Decimal, Field(ge=0, decimal_places=8, description="Non-negative volume")]

# Symbol and identifier types - using NewType for semantic distinction
Symbol = NewType("Symbol", str)
ExchangeName = NewType("ExchangeName", str)
TradeId = NewType("TradeId", str)
OrderId = NewType("OrderId", str)

# Event handling types
EventHandler = Callable[[BaseEvent], None]
AsyncEventHandler = Callable[[BaseEvent], Any]  # Returns awaitable

# Data streaming types
TradeStream = AsyncIterator[Trade]
KlineStream = AsyncIterator[Kline]
DataStream = AsyncIterator[T]

# Configuration types
ConfigDict = dict[str, Any]
EnvironmentName = NewType("EnvironmentName", str)
AppName = NewType("AppName", str)

# Network types
URL = NewType("URL", str)
HostPort = tuple[str, int]
Timeout = Annotated[float, Field(gt=0, description="Positive timeout value in seconds")]

# Error handling types
ErrorCode = NewType("ErrorCode", str)
ErrorMessage = NewType("ErrorMessage", str)
ErrorDetails = dict[str, Any]

# Storage types
StorageKey = NewType("StorageKey", str)
StorageValue = Any
QueryFilter = dict[str, Any]
QueryLimit = Annotated[int, Field(ge=1, description="Positive query limit")]
QueryOffset = Annotated[int, Field(ge=0, description="Non-negative query offset")]

# Pagination types
PageSize = Annotated[int, Field(ge=1, le=1000, description="Page size between 1 and 1000")]
PageNumber = Annotated[int, Field(ge=1, description="Page number starting from 1")]
TotalCount = Annotated[int, Field(ge=0, description="Non-negative total count")]

# Performance and monitoring types
Latency = Annotated[float, Field(ge=0, description="Latency in milliseconds")]
MemoryUsage = Annotated[int, Field(ge=0, description="Memory usage in bytes")]
CPUUsage = Annotated[float, Field(ge=0, le=100, description="CPU usage percentage (0-100)")]
ConnectionCount = Annotated[int, Field(ge=0, description="Non-negative connection count")]

# Data validation types
ValidationRule = Callable[[Any], bool]
ValidatorFunc = Callable[[Any], Any]
ValidationError = exceptions.ValidationError  # Use the specific ValidationError from exceptions.py

# Trading-specific types
PriceLevel = tuple[Price, Quantity]  # Price and quantity at that level
OrderBook = dict[str, list[PriceLevel]]  # bid/ask levels
TickerData = dict[str, Any]
ExchangeInfo = dict[str, Any]
SymbolInfo = dict[str, Any]

# Aggregation types
AggregationPeriod = str  # e.g., "1m", "5m", "1h", "1d"
AggregationFunction = Callable[[list[T]], T]

# Filter and selector types
SymbolFilter = Callable[[Symbol], bool]
EventFilter = Callable[[BaseEvent], bool]
DataFilter = Callable[[T], bool]

# Subscription types
SubscriptionId = NewType("SubscriptionId", str)
SubscriptionCallback = Callable[[T], None]
SubscriptionFilter = Callable[[T], bool]

# Provider types
ProviderName = NewType("ProviderName", str)
ProviderConfig = dict[str, Any]
ConnectionString = NewType("ConnectionString", str)

# Observer pattern types
Observer = Callable[[T], None]
Subject = Any  # Object that can be observed

# Cache types
CacheKey = NewType("CacheKey", str)
CacheValue = Any
CacheTTL = Annotated[int, Field(gt=0, description="Cache TTL in seconds")]

# Serialization types
SerializedData = NewType("SerializedData", str)
DeserializedData = Any
SerializationFormat = NewType("SerializationFormat", str)  # e.g., "json", "pickle", "msgpack"

# Logging types
LogLevel = NewType("LogLevel", str)
LogMessage = NewType("LogMessage", str)
LogContext = dict[str, Any]

# Metrics types
MetricName = NewType("MetricName", str)
MetricValue = int | float
MetricTags = dict[str, str]
MetricTimestamp = datetime

# Rate limiting types
RateLimit = Annotated[int, Field(gt=0, description="Requests per time period")]
RatePeriod = Annotated[int, Field(gt=0, description="Time period in seconds")]
RateWindow = tuple[datetime, datetime]

# Circuit breaker types
FailureThreshold = Annotated[int, Field(gt=0, description="Positive failure threshold")]
RecoveryTimeout = Annotated[int, Field(gt=0, description="Recovery timeout in seconds")]
CircuitState = NewType("CircuitState", str)  # "closed", "open", "half-open"

# Retry policy types
RetryAttempts = Annotated[int, Field(ge=0, description="Non-negative retry attempts")]
RetryDelay = Annotated[float, Field(gt=0, description="Positive retry delay in seconds")]
RetryBackoff = Annotated[float, Field(gt=1, description="Backoff multiplier greater than 1")]

# Health check types
HealthStatus = NewType("HealthStatus", str)  # "healthy", "unhealthy", "degraded"
HealthCheckResult = dict[str, Any]

# Common collections
SymbolList = list[Symbol]
PriceList = list[Price]
TimestampList = list[Timestamp]

# Optional versions of common types
OptionalPrice = Price | None
OptionalQuantity = Quantity | None
OptionalTimestamp = Timestamp | None
OptionalSymbol = Symbol | None


# Result types for error handling
class Result:
    """Generic result type for operations that can fail."""

    pass


class Success[T](Result):
    """Successful result with value."""

    def __init__(self, value: T):
        self.value = value


class Failure(Result):
    """Failed result with error."""

    def __init__(self, error: Exception):
        self.error = error


# Union types for common patterns
SuccessOrFailure = Success[T] | Failure
PriceOrVolume = Price | Volume
TimeOrOffset = Timestamp | int

# Functional types
Predicate = Callable[[T], bool]
Transformer = Callable[[T], K]
Reducer = Callable[[T, K], T]
Mapper = Callable[[T], K]

# Protocol types (for structural typing)


class Identifiable(Protocol):
    """Protocol for objects that have a unique identifier.
    Classes implementing this protocol must have an 'id' attribute of type string.
    """

    id: str


class Timestamped(Protocol):
    """Protocol for objects that have an associated timestamp.
    Classes implementing this protocol must have a 'timestamp' attribute of type datetime.
    """

    timestamp: datetime


class Symbolized(Protocol):
    """Protocol for objects that are associated with a trading symbol.
    Classes implementing this protocol must have a 'symbol' attribute of type string.
    """

    symbol: str


class Serializable(Protocol):
    """Protocol for objects that can be converted to and from a dictionary representation.
    Classes implementing this protocol must provide 'to_dict' and 'from_dict' methods.
    """

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any: ...


class Validatable(Protocol):
    """Protocol for objects that can perform self-validation.
    Classes implementing this protocol must provide a 'validate' method that returns a boolean.
    """

    def validate(self) -> bool: ...


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
