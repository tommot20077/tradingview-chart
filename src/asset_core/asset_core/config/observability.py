"""Observability configuration settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseObservabilityConfig(BaseSettings):
    """Observability-related configuration settings."""

    model_config = SettingsConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

    # Metrics settings
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Port for metrics endpoint", gt=0, le=65535)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        allowed = {"json", "text"}
        if v not in allowed:
            raise ValueError(f"log_format must be one of {allowed}")
        return v
