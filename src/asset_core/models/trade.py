"""Trade model definition.

This module defines the Pydantic models for representing individual trades
(transactions) in financial markets. It includes the `TradeSide` enumeration
and the `Trade` model, which captures essential details of a trade such as
symbol, price, quantity, timestamp, and side (buy/sell).
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TradeSide(str, Enum):
    """Enumeration for the side of a trade.

    Attributes:
        BUY (str): Indicates a buy trade.
        SELL (str): Indicates a sell trade.
    """

    BUY = "buy"
    SELL = "sell"


class Trade(BaseModel):
    """Represents a single trade or transaction in a financial market.

    This Pydantic model captures the essential details of a trade, including
    the trading pair, price, quantity, timestamp, and whether it was a buy or sell.
    It includes validation logic to ensure data integrity and consistency.

    Attributes:
        symbol (str): The trading pair symbol (e.g., "BTCUSDT").
        trade_id (str): A unique identifier for the trade, typically from the exchange.
        price (Decimal): The price at which the trade occurred.
        quantity (Decimal): The quantity of the base asset traded.
        side (TradeSide): The side of the trade (buy or sell).
        timestamp (datetime): The UTC timestamp when the trade occurred.
        exchange (str | None): Optional. The name of the exchange where the trade originated.
        maker_order_id (str | None): Optional. The ID of the maker order involved in the trade.
        taker_order_id (str | None): Optional. The ID of the taker order involved in the trade.
        is_buyer_maker (bool | None): Optional. Indicates if the buyer was the maker of the trade.
        received_at (datetime | None): Optional. The UTC timestamp when the trade data was received.
        metadata (dict[str, Any]): Additional, unstructured metadata for the trade.
    """

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
        """Validates and normalizes the trading symbol.

        The symbol is stripped of whitespace and converted to uppercase.

        Args:
            v: The symbol string to validate.

        Returns:
            The normalized symbol string.

        Raises:
            ValueError: If the symbol is `None`, not a string, or becomes empty after stripping.
        """
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
        """Ensures that datetime fields are timezone-aware UTC.

        Args:
            v: The datetime object to validate.

        Returns:
            The validated datetime object, converted to UTC if necessary, or `None`.

        Raises:
            ValueError: If the value is not a datetime object.
        """
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
        """Validates the trade price, ensuring it's positive and within a reasonable range.

        Args:
            v: The price value to validate.

        Returns:
            The validated price value.

        Raises:
            ValueError: If the price is not greater than 0 or falls outside the defined min/max range.
        """
        # First check if positive
        if v <= 0:
            raise ValueError("Price must be greater than 0")

        # Then check range - adjusted for extreme low-price cryptocurrencies
        # Minimum price: 1E-12 (supports extreme meme coins)
        min_price = Decimal("0.000000000001")
        # Maximum price: 1,000,000,000 (supports high-value assets like stocks, bonds, real estate tokens)
        max_price = Decimal("1000000000")

        if v < min_price:
            raise ValueError(f"Price {v} is below minimum allowed price {min_price}")
        if v > max_price:
            raise ValueError(f"Price {v} exceeds maximum allowed price {max_price}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validates the trade quantity, ensuring it's positive and within a reasonable range.

        Args:
            v: The quantity value to validate.

        Returns:
            The validated quantity value.

        Raises:
            ValueError: If the quantity is not greater than 0 or falls below the defined minimum.
        """
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
        """Validates the calculated trade volume against predefined minimum and maximum thresholds.

        This ensures that the trade's total value (price * quantity) falls within
        acceptable operational limits.

        Returns:
            The validated `Trade` instance.

        Raises:
            ValueError: If the calculated trade volume is outside the allowed range.
        """
        volume = self.volume

        # Minimum volume: $0.001 equivalent (supports micro-transactions)
        min_volume = Decimal("0.001")
        # Maximum volume: $10,000,000,000 (10B USD equivalent, supports institutional trades)
        max_volume = Decimal("10000000000")

        if volume < min_volume:
            raise ValueError(f"Trade volume {volume} is below minimum allowed volume {min_volume}")
        if volume > max_volume:
            raise ValueError(f"Trade volume {volume} exceeds maximum allowed volume {max_volume}")

        return self

    @property
    def volume(self) -> Decimal:
        """Calculates the total volume of the trade (price * quantity).

        Returns:
            A `Decimal` representing the trade volume.
        """
        return self.price * self.quantity

    def to_dict(self) -> dict[str, Any]:
        """Converts the `Trade` object to a dictionary, with Decimal and datetime fields
        converted to string representations suitable for JSON serialization.

        Returns:
            A dictionary representation of the trade.
        """
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
        """Returns a string representation of the `Trade` object.

        Returns:
            A formatted string showing key trade details.
        """
        return f"Trade({self.symbol} {self.side} {self.quantity}@{self.price} at {self.timestamp.isoformat()})"
