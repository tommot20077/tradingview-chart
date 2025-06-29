"""Asset core types package.

This package contains common type aliases, type definitions, and protocols
used throughout the asset_core library. It provides type safety and
consistency across all modules.
"""

from .common import (
    # Network types
    URL,
    AppName,
    AsyncEventHandler,
    CacheKey,
    CacheTTL,
    CacheValue,
    CircuitState,
    # Configuration types
    ConfigDict,
    DataFilter,
    DataStream,
    DeserializedData,
    EnvironmentName,
    EventFilter,
    # Event types
    EventHandler,
    ExchangeInfo,
    ExchangeName,
    Failure,
    FailureThreshold,
    HealthCheckResult,
    HealthStatus,
    HostPort,
    # Protocol types
    Identifiable,
    IdentifiableT,
    JsonDict,
    JsonList,
    # Basic types
    JsonValue,
    K,
    KlineStream,
    LogLevel,
    LogMessage,
    Mapper,
    MetricName,
    MetricTags,
    MetricTimestamp,
    MetricValue,
    # Optional types
    OptionalPrice,
    OptionalQuantity,
    OptionalSymbol,
    OptionalTimestamp,
    OrderBook,
    OrderId,
    # Functional types
    Predicate,
    Price,
    # Trading types
    PriceLevel,
    PriceList,
    Quantity,
    RateLimit,
    RatePeriod,
    RateWindow,
    RecoveryTimeout,
    Reducer,
    # Result types
    Result,
    RetryAttempts,
    RetryBackoff,
    RetryDelay,
    Serializable,
    SerializableT,
    SerializationFormat,
    SerializedData,
    SubscriptionCallback,
    SubscriptionFilter,
    # Subscription types
    SubscriptionId,
    Success,
    SuccessOrFailure,
    Symbol,
    # Filter types
    SymbolFilter,
    SymbolInfo,
    Symbolized,
    SymbolizedT,
    # Collection types
    SymbolList,
    # Generic type variables
    T,
    TickerData,
    Timeout,
    Timestamp,
    Timestamped,
    TimestampedT,
    TimestampList,
    TimestampMs,
    TimestampUs,
    TradeId,
    # Stream types
    TradeStream,
    Transformer,
    V,
    Validatable,
    ValidatableT,
    ValidationError,
    Volume,
)

__all__ = [
    # Basic types
    "JsonValue",
    "JsonDict",
    "JsonList",
    "Timestamp",
    "TimestampMs",
    "TimestampUs",
    "Price",
    "Quantity",
    "Volume",
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
    # Cache types
    "CacheKey",
    "CacheValue",
    "CacheTTL",
    # Serialization types
    "SerializedData",
    "DeserializedData",
    "SerializationFormat",
    # Logging types
    "LogLevel",
    "LogMessage",
    "LogContext",
    # Metrics types
    "MetricName",
    "MetricValue",
    "MetricTags",
    "MetricTimestamp",
    # Rate limiting types
    "RateLimit",
    "RatePeriod",
    "RateWindow",
    # Circuit breaker types
    "FailureThreshold",
    "RecoveryTimeout",
    "CircuitState",
    # Retry policy types
    "RetryAttempts",
    "RetryDelay",
    "RetryBackoff",
    # Health check types
    "HealthStatus",
    "HealthCheckResult",
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

from asset_core.observability.logging import LogContext
