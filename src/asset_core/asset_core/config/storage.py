"""Storage configuration settings."""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseStorageConfig(BaseSettings):
    """Storage-related configuration settings."""

    model_config = SettingsConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Database settings
    database_url: str = Field(
        ..., description="Database connection URL. Must be provided by the application.", min_length=1
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size", gt=0)
    database_timeout: int = Field(default=30, description="Database connection timeout in seconds", gt=0)

    # File storage settings
    data_directory: str = Field(default="data", description="Directory for data files")
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes", ge=0)

    @classmethod
    @field_validator("database_pool_size", "database_timeout", "max_file_size", mode="before")
    def convert_float_to_int(cls, v: Any) -> Any:
        """Convert float values to int for integer fields."""
        if isinstance(v, float):
            return int(v)
        return v
