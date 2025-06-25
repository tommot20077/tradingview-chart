"""Trade model definition."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TradeSide(str, Enum):
    """Trade side enumeration."""

    BUY = "buy"
    SELL = "sell"


class Trade(BaseModel):
    """Represents a single trade/transaction."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    # Core fields
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    trade_id: str = Field(..., description="Unique trade identifier from exchange")
    price: Decimal = Field(..., description="Trade price")
    quantity: Decimal = Field(..., description="Trade quantity")
    side: TradeSide = Field(..., description="Trade side (buy/sell)")
    timestamp: datetime = Field(..., description="Trade timestamp (UTC)")

    # Optional fields
    exchange: str | None = Field(None, description="Exchange name")
    maker_order_id: str | None = Field(None, description="Maker order ID")
    taker_order_id: str | None = Field(None, description="Taker order ID")
    is_buyer_maker: bool | None = Field(None, description="Whether buyer is the maker")

    # Metadata
    received_at: datetime | None = Field(None, description="When the trade was received")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize symbol."""
        # Handle None and non-string values
        if v is None:
            raise ValueError("Symbol cannot be None")
        if not isinstance(v, str):
            raise ValueError("Symbol must be a string")

        # Strip whitespace and convert to uppercase
        v = v.strip().upper()

        # Check for empty symbol after stripping
        if not v:
            raise ValueError("Symbol cannot be empty")

        return v

    @field_validator("timestamp", "received_at")
    @classmethod
    def validate_timezone(cls, v: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware UTC."""
        if v is None:
            return None
        if not isinstance(v, datetime):
            raise ValueError("Value must be a datetime object")

        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=UTC)

        # Convert to UTC if different timezone
        return v.astimezone(UTC)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price value and range."""
        # First check if positive
        if v <= 0:
            raise ValueError("Price must be greater than 0")

        # Then check range - adjusted for extreme low-price cryptocurrencies
        # Minimum price: 1E-12 (supports extreme meme coins)
        min_price = Decimal("0.000000000001")
        # Maximum price: 10,000,000 (reasonable upper bound)
        max_price = Decimal("10000000")

        if v < min_price:
            raise ValueError(f"Price {v} is below minimum allowed price {min_price}")
        if v > max_price:
            raise ValueError(f"Price {v} exceeds maximum allowed price {max_price}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validate quantity value and range."""
        # First check if positive
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")

        # Then check range - removed maximum limit to support large purchases of low-price coins
        # Minimum quantity: 1E-12 (supports micro-transactions)
        min_quantity = Decimal("0.000000000001")
        # No maximum quantity limit - let market and exchange handle this

        if v < min_quantity:
            raise ValueError(f"Quantity {v} is below minimum allowed quantity {min_quantity}")
        # Removed maximum quantity check to support large purchases of meme coins
        return v

    @model_validator(mode="after")
    def validate_trade_volume(self) -> "Trade":
        """Validate trade volume is within reasonable range."""
        volume = self.volume

        # Minimum volume: $0.01 equivalent
        min_volume = Decimal("0.01")
        # Maximum volume: $100,000,000 (100M USD equivalent)
        max_volume = Decimal("100000000")

        if volume < min_volume:
            raise ValueError(f"Trade volume {volume} is below minimum allowed volume {min_volume}")
        if volume > max_volume:
            raise ValueError(f"Trade volume {volume} exceeds maximum allowed volume {max_volume}")

        return self

    @property
    def volume(self) -> Decimal:
        """Calculate trade volume (price * quantity)."""
        return self.price * self.quantity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with string representations."""
        data = self.model_dump()
        # Convert Decimal to string for JSON serialization
        # Use normalize() to preserve precision for all cryptocurrencies
        data["price"] = str(self.price.normalize())
        data["quantity"] = str(self.quantity.normalize())
        data["volume"] = str(self.volume.normalize())
        # Convert datetime to ISO format
        data["timestamp"] = self.timestamp.isoformat()
        if self.received_at:
            data["received_at"] = self.received_at.isoformat()
        return data

    def __str__(self) -> str:
        """String representation."""
        return f"Trade({self.symbol} {self.side} {self.quantity}@{self.price} at {self.timestamp.isoformat()})"
