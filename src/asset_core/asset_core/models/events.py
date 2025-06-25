"""Event model definitions."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .kline import Kline
from .trade import Trade

T = TypeVar("T")


class EventType(str, Enum):
    """Event type enumeration."""

    TRADE = "trade"
    KLINE = "kline"
    ORDER = "order"
    BALANCE = "balance"
    CONNECTION = "connection"
    ERROR = "error"
    SYSTEM = "system"

    def __str__(self) -> str:
        return self.value


class EventPriority(int, Enum):
    """Event priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class BaseEvent[T](BaseModel):
    """Base event class for all events."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    # Event metadata
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")
    event_type: EventType = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")

    # Source information
    source: str = Field(..., description="Event source (e.g., exchange name, service name)")
    symbol: str | None = Field(None, description="Trading symbol if applicable")

    # Event data
    data: T = Field(..., description="Event payload data")

    # Optional fields
    priority: EventPriority = Field(default=EventPriority.NORMAL, description="Event priority")
    correlation_id: str | None = Field(None, description="Correlation ID for tracking related events")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("timestamp")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware UTC."""
        if not isinstance(v, datetime):
            raise ValueError("Value must be a datetime object")

        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=UTC)

        # Convert to UTC if different timezone
        return v.astimezone(UTC)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str | None) -> str | None:
        """Validate and normalize symbol."""
        if v is None:
            return None

        # Handle non-string values
        if not isinstance(v, str):
            raise ValueError("Symbol must be a string")

        # Strip whitespace and convert to uppercase
        v = v.strip().upper()

        # Check for empty symbol after stripping
        if not v:
            raise ValueError("Symbol cannot be empty")

        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(id={self.event_id}, type={self.event_type}, source={self.source})"


class TradeEvent(BaseEvent[Trade]):
    """Event containing trade data."""

    event_type: EventType = Field(default=EventType.TRADE, frozen=True)

    def __init__(self, **data: Any) -> None:
        """Initialize TradeEvent with trade type."""
        if "event_type" not in data:
            data["event_type"] = EventType.TRADE
        super().__init__(**data)


class KlineEvent(BaseEvent[Kline]):
    """Event containing kline data."""

    event_type: EventType = Field(default=EventType.KLINE, frozen=True)

    def __init__(self, **data: Any) -> None:
        """Initialize KlineEvent with kline type."""
        if "event_type" not in data:
            data["event_type"] = EventType.KLINE
        super().__init__(**data)


class ConnectionStatus(str, Enum):
    """Connection status enumeration."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ConnectionEvent(BaseEvent[dict[str, Any]]):
    """Event for connection status changes."""

    event_type: EventType = Field(default=EventType.CONNECTION, frozen=True)

    def __init__(self, status: ConnectionStatus, **data: Any) -> None:
        """Initialize ConnectionEvent."""
        event_data = data.pop("data", {})
        event_data["status"] = status.value
        if "event_type" not in data:
            data["event_type"] = EventType.CONNECTION
        data["data"] = event_data
        super().__init__(**data)


class ErrorEvent(BaseEvent[dict[str, Any]]):
    """Event for errors."""

    event_type: EventType = Field(default=EventType.ERROR, frozen=True)
    priority: EventPriority = Field(default=EventPriority.HIGH)

    def __init__(self, error: str, error_code: str | None = None, **data: Any) -> None:
        """Initialize ErrorEvent."""
        event_data = data.pop("data", {})
        event_data["error"] = error
        if error_code:
            event_data["error_code"] = error_code
        if "event_type" not in data:
            data["event_type"] = EventType.ERROR
        if "priority" not in data:
            data["priority"] = EventPriority.HIGH
        data["data"] = event_data
        super().__init__(**data)
