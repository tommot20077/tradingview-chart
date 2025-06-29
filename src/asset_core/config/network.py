"""Network configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseNetworkConfig(BaseSettings):
    """Base configuration settings for network-related functionalities.

    This class defines parameters for WebSocket connections, including
    reconnection strategies and heartbeat settings.
    """

    model_config = SettingsConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )
    """Pydantic model configuration.

    Attributes:
        str_strip_whitespace (bool): Whether to strip whitespace from strings.
        extra (str): Policy for handling extra fields ('ignore' to ignore them).
    """

    # WebSocket settings
    ws_reconnect_interval: int = Field(default=5, description="WebSocket reconnection interval in seconds", ge=0)
    """Interval in seconds between WebSocket reconnection attempts. Must be non-negative."""
    ws_max_reconnect_attempts: int = Field(
        default=10,
        description="Maximum number of WebSocket reconnection attempts. Set to -1 for unlimited.",
        ge=-1,
    )
    """Maximum number of WebSocket reconnection attempts. Set to -1 for unlimited attempts. Must be non-negative or -1."""
    ws_ping_interval: int = Field(
        default=30,
        description="Interval in seconds for sending WebSocket ping messages to keep the connection alive. Set to 0 to disable.",
        ge=0,
    )
    """Interval in seconds for sending WebSocket ping messages. Must be non-negative."""
    ws_ping_timeout: int = Field(
        default=10,
        description="Timeout in seconds for WebSocket ping responses. If no pong is received within this time, the connection is considered broken.",
        ge=0,
    )
    """Timeout in seconds for WebSocket ping responses. Must be non-negative."""
