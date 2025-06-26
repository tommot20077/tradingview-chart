"""Observability configuration settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseObservabilityConfig(BaseSettings):
    """Base configuration settings for observability components.

    This class defines parameters related to logging and metrics, allowing
    for centralized management of how application behavior is monitored and recorded.
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

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    """The logging level (e.g., "INFO", "DEBUG", "WARNING")."""
    log_format: str = Field(default="json", description="Log format (json or text)")
    """The format for log output (e.g., "json" or "text")."""

    # Metrics settings
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics exposure.")
    """Whether to enable the Prometheus metrics endpoint. Defaults to `True`."""
    metrics_port: int = Field(
        default=9090,
        description="Port on which the Prometheus metrics endpoint will be exposed.",
        gt=0,
        le=65535,
    )
    """The port number for the Prometheus metrics endpoint. Must be between 1 and 65535."""

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validates the `log_level` field.

        Args:
            v: The log level string to validate.

        Returns:
            The validated and normalized (uppercase) log level string.

        Raises:
            ValueError: If the log level is not one of the allowed values.
        """
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validates the `log_format` field.

        Args:
            v: The log format string to validate.

        Returns:
            The validated log format string.

        Raises:
            ValueError: If the log format is not one of the allowed values.
        """
        allowed = {"json", "text"}
        if v not in allowed:
            raise ValueError(f"log_format must be one of {allowed}")
        return v
