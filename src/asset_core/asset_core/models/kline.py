"""Kline (candlestick) model definition."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KlineInterval(str, Enum):
    """Kline interval enumeration."""

    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_8 = "8h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

    @classmethod
    def to_seconds(cls, interval: "KlineInterval") -> int:
        """Convert interval to seconds."""
        mapping = {
            cls.MINUTE_1: 60,
            cls.MINUTE_3: 180,
            cls.MINUTE_5: 300,
            cls.MINUTE_15: 900,
            cls.MINUTE_30: 1800,
            cls.HOUR_1: 3600,
            cls.HOUR_2: 7200,
            cls.HOUR_4: 14400,
            cls.HOUR_6: 21600,
            cls.HOUR_8: 28800,
            cls.HOUR_12: 43200,
            cls.DAY_1: 86400,
            cls.DAY_3: 259200,
            cls.WEEK_1: 604800,
            cls.MONTH_1: 2592000,  # 30 days approximation
        }
        return mapping[interval]

    @classmethod
    def to_timedelta(cls, interval: "KlineInterval") -> timedelta:
        """Convert interval to timedelta."""
        return timedelta(seconds=cls.to_seconds(interval))


class Kline(BaseModel):
    """Represents a candlestick/kline data point."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    # Core fields
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    interval: KlineInterval = Field(..., description="Kline interval")
    open_time: datetime = Field(..., description="Kline open time (UTC)")
    close_time: datetime = Field(..., description="Kline close time (UTC)")

    # Price data
    open_price: Decimal = Field(..., description="Open price")
    high_price: Decimal = Field(..., description="High price")
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Close price")

    # Volume data
    volume: Decimal = Field(..., description="Volume in base asset")
    quote_volume: Decimal = Field(..., description="Volume in quote asset")

    # Trade statistics
    trades_count: int = Field(..., description="Number of trades", ge=0)

    # Optional fields
    exchange: str | None = Field(None, description="Exchange name")
    taker_buy_volume: Decimal | None = Field(None, description="Taker buy volume")
    taker_buy_quote_volume: Decimal | None = Field(None, description="Taker buy quote volume")

    # Status
    is_closed: bool = Field(True, description="Whether the kline is closed")

    # Metadata
    received_at: datetime | None = Field(None, description="When the kline was received")
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

    @field_validator("open_price", "high_price", "low_price", "close_price")
    @classmethod
    def validate_prices(cls, v: Decimal) -> Decimal:
        """Validate price values are positive."""
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @field_validator("volume", "quote_volume")
    @classmethod
    def validate_volumes(cls, v: Decimal) -> Decimal:
        """Validate volume values are non-negative."""
        if v < 0:
            raise ValueError("Volume must be greater than or equal to 0")
        return v

    @field_validator("taker_buy_volume", "taker_buy_quote_volume")
    @classmethod
    def validate_optional_volumes(cls, v: Decimal | None) -> Decimal | None:
        """Validate optional volume values are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Volume must be greater than or equal to 0")
        return v

    @field_validator("open_time", "close_time", "received_at")
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

    @field_validator("high_price")
    @classmethod
    def validate_high(cls, v: Decimal, info: Any) -> Decimal:
        """Validate high price."""
        data = info.data
        if "low_price" in data and v < data["low_price"]:
            raise ValueError("High price cannot be less than low price")
        if "open_price" in data and v < data["open_price"]:
            raise ValueError("High price cannot be less than open price")
        if "close_price" in data and v < data["close_price"]:
            raise ValueError("High price cannot be less than close price")
        return v

    @field_validator("low_price")
    @classmethod
    def validate_low(cls, v: Decimal, info: Any) -> Decimal:
        """Validate low price."""
        data = info.data
        if "open_price" in data and v > data["open_price"]:
            raise ValueError("Low price cannot be greater than open price")
        if "close_price" in data and v > data["close_price"]:
            raise ValueError("Low price cannot be greater than close price")
        return v

    @field_validator("close_time")
    @classmethod
    def validate_close_time(cls, v: datetime, info: Any) -> datetime:
        """Validate close time is after open time."""
        data = info.data
        if "open_time" in data and v <= data["open_time"]:
            raise ValueError("Close time must be after open time")
        return v

    @model_validator(mode="after")
    def validate_time_continuity(self) -> "Kline":
        """Validate time continuity and interval consistency."""
        # Calculate expected duration based on interval
        expected_duration = KlineInterval.to_timedelta(self.interval)
        actual_duration = self.duration

        # Allow for small tolerance (1 second) for timing variations
        tolerance = timedelta(seconds=1)
        duration_diff = abs(actual_duration - expected_duration)

        if duration_diff > tolerance:
            raise ValueError(
                f"Kline duration {actual_duration} does not match expected duration "
                f"{expected_duration} for interval {self.interval}. "
                f"Difference: {duration_diff}"
            )

        # Validate that open_time aligns with interval boundaries
        # For example, 1h klines should start at the top of the hour
        if not self._is_time_aligned_to_interval():
            raise ValueError(f"Kline open_time {self.open_time} is not aligned to interval {self.interval} boundaries")

        return self

    def _is_time_aligned_to_interval(self) -> bool:
        """Check if open_time is aligned to interval boundaries."""
        interval_seconds = KlineInterval.to_seconds(self.interval)

        # Convert to timestamp for easier calculation
        timestamp = int(self.open_time.timestamp())

        # Check if timestamp is divisible by interval seconds
        return timestamp % interval_seconds == 0

    @classmethod
    def validate_sequence_continuity(cls, klines: list["Kline"]) -> bool:
        """Validate that a sequence of klines is continuous without gaps."""
        if len(klines) < 2:
            return True

        # Sort klines by open_time
        sorted_klines = sorted(klines, key=lambda k: k.open_time)

        for i in range(1, len(sorted_klines)):
            current = sorted_klines[i]
            previous = sorted_klines[i - 1]

            # Check if klines are for the same symbol and interval
            if current.symbol != previous.symbol:
                raise ValueError(f"Klines must have the same symbol. Found {current.symbol} and {previous.symbol}")

            if current.interval != previous.interval:
                raise ValueError(
                    f"Klines must have the same interval. Found {current.interval} and {previous.interval}"
                )

            # Check for continuity: current.open_time should equal previous.close_time
            # Allow small tolerance for timing variations
            tolerance = timedelta(seconds=1)
            time_gap = abs(current.open_time - previous.close_time)

            if time_gap > tolerance:
                raise ValueError(
                    f"Gap detected between klines: {previous.close_time} to {current.open_time}, gap: {time_gap}"
                )

        return True

    @property
    def duration(self) -> timedelta:
        """Calculate kline duration."""
        return self.close_time - self.open_time

    @property
    def price_change(self) -> Decimal:
        """Calculate price change (close - open)."""
        return self.close_price - self.open_price

    @property
    def price_change_percent(self) -> Decimal:
        """Calculate price change percentage."""
        if self.open_price == 0:
            return Decimal("0")
        return (self.price_change / self.open_price) * 100

    @property
    def is_bullish(self) -> bool:
        """Check if kline is bullish (close > open)."""
        return self.close_price > self.open_price

    @property
    def is_bearish(self) -> bool:
        """Check if kline is bearish (close < open)."""
        return self.close_price < self.open_price

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with string representations."""
        data = self.model_dump()
        # Convert Decimal to string for JSON serialization
        for field in ["open_price", "high_price", "low_price", "close_price", "volume", "quote_volume"]:
            data[field] = str(data[field])
        if self.taker_buy_volume is not None:
            data["taker_buy_volume"] = str(self.taker_buy_volume)
        if self.taker_buy_quote_volume is not None:
            data["taker_buy_quote_volume"] = str(self.taker_buy_quote_volume)
        # Convert datetime to ISO format
        data["open_time"] = self.open_time.isoformat()
        data["close_time"] = self.close_time.isoformat()
        if self.received_at:
            data["received_at"] = self.received_at.isoformat()
        # Add calculated fields
        data["price_change"] = str(self.price_change)
        data["price_change_percent"] = str(self.price_change_percent)
        return data

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Kline({self.symbol} {self.interval} "
            f"O:{self.open_price} H:{self.high_price} L:{self.low_price} C:{self.close_price} "
            f"V:{self.volume} at {self.open_time.isoformat()})"
        )
