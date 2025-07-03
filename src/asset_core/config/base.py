"""Base configuration settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseCoreSettings(BaseSettings):
    """Base settings class for all applications built on `asset_core`.

    This class provides fundamental configuration parameters that are common
    across different applications and environments. It leverages Pydantic's
    `BaseSettings` for environment variable and `.env` file integration.

    Attributes:
        app_name (str): The name of the application. Defaults to "asset-core".
        environment (str): The deployment environment (e.g., "development", "staging", "production").
        debug (bool): A flag indicating whether debug mode is enabled. Defaults to `False`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    """Pydantic model configuration.

    Attributes:
        env_file (str): Specifies the .env file to load environment variables from.
        env_file_encoding (str): The encoding of the .env file.
        case_sensitive (bool): Whether environment variable names are case-sensitive.
        extra (str): Policy for handling extra fields ('ignore' to ignore them).
    """

    # Application settings
    app_name: str = Field(default="asset-core", description="Application name")
    """The name of the application. Defaults to "asset-core"."""
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    """The deployment environment (e.g., "development", "staging", "production")."""
    debug: bool = Field(default=False, description="Debug mode")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validates the `environment` field to ensure it's one of the allowed values.

        Args:
            v: The environment string to validate.

        Returns:
            The validated and normalized (lowercase) environment string.

        Raises:
            ValueError: If the environment value is not one of "development", "staging", or "production".
        """
        # Convert to lowercase for case-insensitive validation
        v = v.lower()
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    def is_production(self) -> bool:
        """Checks if the application is running in the production environment.

        Returns:
            `True` if the `environment` is "production", `False` otherwise.
        """
        return self.environment == "production"

    def is_development(self) -> bool:
        """Checks if the application is running in the development environment.

        Returns:
            `True` if the `environment` is "development", `False` otherwise.
        """
        return self.environment == "development"
