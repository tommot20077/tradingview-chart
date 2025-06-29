"""Storage configuration settings."""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseStorageConfig(BaseSettings):
    """Base configuration settings for storage-related functionalities.

    This class defines parameters for database connections and file storage,
    allowing for centralized management of data persistence settings.
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

    # Database settings
    database_url: str = Field(
        ..., description="Database connection URL. Must be provided by the application.", min_length=1
    )
    """The database connection URL. This field is mandatory and must be provided by the application."""
    database_pool_size: int = Field(default=10, description="Database connection pool size.", gt=0)
    """The maximum number of connections to maintain in the database connection pool. Must be greater than 0."""
    database_timeout: int = Field(default=30, description="Database connection timeout in seconds.", gt=0)
    """The maximum time in seconds to wait for a database connection to be established. Must be greater than 0."""

    # File storage settings
    data_directory: str = Field(default="data", description="Directory for storing data files.")
    """The path to the directory where application data files will be stored. Defaults to "data"."""
    max_file_size: int = Field(
        default=100 * 1024 * 1024, description="Maximum size of individual data files in bytes.", ge=0
    )
    """The maximum allowed size for individual data files in bytes. Must be non-negative."""

    @classmethod
    @field_validator("database_pool_size", "database_timeout", "max_file_size", mode="before")
    def convert_float_to_int(cls, v: Any) -> Any:
        """Converts float values to integers for fields that are expected to be integers.

        This validator is applied before other validations to ensure that float inputs
        (e.g., from environment variables) are correctly cast to integers.

        Args:
            v: The value to convert.

        Returns:
            The value cast to an integer if it was a float, otherwise the original value.
        """
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v
