"""Event model definitions.

This module defines Pydantic models for various types of events within the
`asset_core` library, including base event, trade events, kline events,
connection events, and error events. These models ensure structured and
type-safe event data for inter-component communication.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .kline import Kline
from .trade import Trade

T = TypeVar("T")


class EventType(str, Enum):
    """Enumeration of predefined event types.

    Each member represents a distinct category of event that can occur within
    the system, facilitating event routing and handling.

    Attributes:
        TRADE (str): Represents a trade event.
        KLINE (str): Represents a kline (candlestick) event.
        ORDER (str): Represents an order-related event.
        BALANCE (str): Represents a balance change event.
        CONNECTION (str): Represents a connection status change event.
        ERROR (str): Represents an error event.
        SYSTEM (str): Represents a general system event.
    """

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
    """Enumeration of event priority levels.

    Higher priority events are typically processed before lower priority ones.

    Attributes:
        LOW (int): Lowest priority.
        NORMAL (int): Default priority.
        HIGH (int): High priority.
        CRITICAL (int): Highest priority, for urgent events.
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class BaseEvent[T](BaseModel):
    """Base class for all events in the system.

    This Pydantic model provides a common structure for all events, including
    metadata such as event ID, type, timestamp, source, and an optional symbol.
    It also includes a generic `data` field to hold the event-specific payload.

    Type Parameters:
        T: The type of the `data` payload for the event.

    Attributes:
        event_id (str): A unique identifier for the event, automatically generated.
        event_type (EventType): The type of the event, indicating its category.
        timestamp (datetime): The UTC timestamp when the event occurred, automatically set.
        source (str): The origin of the event (e.g., exchange name, service name).
        symbol (str | None): The trading symbol associated with the event, if applicable.
        data (T): The actual payload of the event, typed generically.
        priority (EventPriority): The priority level of the event. Defaults to `NORMAL`.
        correlation_id (str | None): An optional ID for correlating related events across different systems.
        metadata (dict[str, Any]): A dictionary for any additional, unstructured metadata.
    """

    @field_validator("timestamp")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        """Validates and ensures the timestamp is timezone-aware UTC.

        Args:
            v: The datetime object to validate.

        Returns:
            The validated datetime object, converted to UTC if necessary.

        Raises:
            ValueError: If the value is not a datetime object.
        """
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
        """Validates and normalizes the trading symbol.

        The symbol is stripped of whitespace and converted to uppercase.

        Args:
            v: The symbol string to validate.

        Returns:
            The normalized symbol string, or `None` if the input was `None`.

        Raises:
            ValueError: If the symbol is not a string or becomes empty after stripping.
        """
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

    # Model fields
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for the event")
    event_type: EventType = Field(description="The type of the event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp when the event occurred"
    )
    source: str = Field(description="The origin of the event")
    symbol: str | None = Field(default=None, description="Trading symbol associated with the event")
    data: T = Field(description="The actual payload of the event")
    priority: EventPriority = Field(default=EventPriority.NORMAL, description="Priority level of the event")
    correlation_id: str | None = Field(default=None, description="ID for correlating related events")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional unstructured metadata")

    def to_dict(self) -> dict[str, Any]:
        """Converts the `BaseEvent` instance to a dictionary representation.

        The timestamp is converted to ISO 8601 format.

        Returns:
            A dictionary representing the event.
        """
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def __str__(self) -> str:
        """Returns a string representation of the `BaseEvent` instance.

        Returns:
            A string in the format `ClassName(id=..., type=..., source=...)`.
        """
        return f"{self.__class__.__name__}(id={self.event_id}, type={self.event_type}, source={self.source})"


class TradeEvent(BaseEvent[Trade]):
    """Represents an event containing trade data.

    This event type is specifically designed to carry `Trade` objects as its payload.
    The `event_type` is automatically set to `EventType.TRADE`.
    """

    event_type: EventType = Field(default=EventType.TRADE, frozen=True)

    def __init__(self, **data: Any) -> None:
        """Initializes a `TradeEvent` instance.

        Args:
            **data: Arbitrary keyword arguments to initialize the `BaseEvent`.
                    The `event_type` is automatically set to `EventType.TRADE`.
        """
        if "event_type" not in data:
            data["event_type"] = EventType.TRADE
        super().__init__(**data)


class KlineEvent(BaseEvent[Kline]):
    """Represents an event containing Kline (candlestick) data.

    This event type is specifically designed to carry `Kline` objects as its payload.
    The `event_type` is automatically set to `EventType.KLINE`.
    """

    event_type: EventType = Field(default=EventType.KLINE, frozen=True)

    def __init__(self, **data: Any) -> None:
        """Initializes a `KlineEvent` instance.

        Args:
            **data: Arbitrary keyword arguments to initialize the `BaseEvent`.
                    The `event_type` is automatically set to `EventType.KLINE`.
        """
        if "event_type" not in data:
            data["event_type"] = EventType.KLINE
        super().__init__(**data)


class ConnectionStatus(str, Enum):
    """Enumeration of connection status states.

    These states represent the lifecycle of a network connection.

    Attributes:
        CONNECTING (str): The connection is currently being established.
        CONNECTED (str): The connection is active and ready for use.
        DISCONNECTED (str): The connection has been lost or closed.
        RECONNECTING (str): The system is attempting to re-establish a lost connection.
        ERROR (str): The connection is in an error state.
    """

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ConnectionEvent(BaseEvent[dict[str, Any]]):
    """Represents an event indicating a change in connection status.

    This event carries information about the current `ConnectionStatus`.
    The `event_type` is automatically set to `EventType.CONNECTION`.
    """

    event_type: EventType = Field(default=EventType.CONNECTION, frozen=True)

    def __init__(self, status: ConnectionStatus, **data: Any) -> None:
        """Initializes a `ConnectionEvent` instance.

        Args:
            status: The current `ConnectionStatus`.
            **data: Arbitrary keyword arguments to initialize the `BaseEvent`.
                    The `event_type` is automatically set to `EventType.CONNECTION`.
        """
        event_data = data.pop("data", {})
        event_data["status"] = status.value
        if "event_type" not in data:
            data["event_type"] = EventType.CONNECTION
        data["data"] = event_data
        super().__init__(**data)


class ErrorEvent(BaseEvent[dict[str, Any]]):
    """Represents an event indicating an error has occurred.

    This event carries details about the error, including a human-readable
    message and an optional error code. The `event_type` is automatically
    set to `EventType.ERROR`, and its `priority` defaults to `EventPriority.HIGH`.
    """

    event_type: EventType = Field(default=EventType.ERROR, frozen=True)
    priority: EventPriority = Field(default=EventPriority.HIGH)

    def __init__(self, error: str, error_code: str | None = None, **data: Any) -> None:
        """Initializes an `ErrorEvent` instance.

        Args:
            error: A human-readable error message.
            error_code: Optional. A standardized error code string.
            **data: Arbitrary keyword arguments to initialize the `BaseEvent`.
                    The `event_type` is automatically set to `EventType.ERROR`
                    and `priority` to `EventPriority.HIGH`.
        """
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
