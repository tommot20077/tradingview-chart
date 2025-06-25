"""Network configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseNetworkConfig(BaseSettings):
    """Network-related configuration settings."""

    model_config = SettingsConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    # WebSocket settings
    ws_reconnect_interval: int = Field(default=5, description="WebSocket reconnection interval in seconds", ge=0)
    ws_max_reconnect_attempts: int = Field(default=10, description="Maximum WebSocket reconnection attempts", ge=0)
    ws_ping_interval: int = Field(default=30, description="WebSocket ping interval in seconds", ge=0)
    ws_ping_timeout: int = Field(default=10, description="WebSocket ping timeout in seconds", ge=0)
