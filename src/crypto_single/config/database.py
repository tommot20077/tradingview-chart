"""Database configuration for crypto_single application.

This module provides database configuration classes for both PostgreSQL and SQLite
connections, with environment-specific defaults and validation.
"""

import os
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration for crypto_single application.

    Supports both PostgreSQL (production) and SQLite (development) databases
    with environment-specific defaults and validation.

    Attributes:
        database_url (str): Database connection URL
        pool_size (int): Connection pool size
        max_overflow (int): Maximum pool overflow
        pool_timeout (int): Pool timeout in seconds
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(default="sqlite+aiosqlite:///./crypto_single.db", description="Database connection URL")
    pool_size: int = Field(default=5, ge=1, description="Database connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Maximum pool overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validates database URL format.

        Args:
            v: Database URL string

        Returns:
            Validated database URL

        Raises:
            ValueError: If URL format is invalid
        """
        if not v or not v.strip():
            raise ValueError("Database URL cannot be empty")

        v = v.strip()

        try:
            parsed = urlparse(v)

            # Check for basic URL structure
            if not parsed.scheme:
                raise ValueError("Database URL must include a scheme")

            # Check for supported database types
            supported_schemes = {
                "postgresql",
                "postgresql+asyncpg",
                "postgresql+psycopg2",
                "sqlite",
                "sqlite+aiosqlite",
            }

            if parsed.scheme not in supported_schemes:
                raise ValueError(
                    f"Unsupported database scheme '{parsed.scheme}'. Supported schemes: {supported_schemes}"
                )

            # Validate PostgreSQL URLs
            if parsed.scheme.startswith("postgresql"):
                if not parsed.netloc or parsed.netloc.strip() in ("@", "", "user@"):
                    raise ValueError("PostgreSQL URL must include valid host information")
                # Check for incomplete netloc (user@ without host)
                if (
                    parsed.netloc.endswith("@")
                    and len(parsed.netloc.split("@")) == 2
                    and not parsed.netloc.split("@")[1]
                ):
                    raise ValueError("PostgreSQL URL must include valid host information")

            # Validate SQLite URLs
            if parsed.scheme.startswith("sqlite"):
                if parsed.scheme == "sqlite" and not parsed.path:
                    raise ValueError("SQLite URL must include a database path")
                if parsed.path == "/":
                    raise ValueError("SQLite URL must include a valid database path")

            # Production environment validation
            if os.getenv("ENVIRONMENT", "").lower() == "production":
                if parsed.scheme.startswith("sqlite"):
                    raise ValueError("SQLite databases are not allowed in production environment")
                if not parsed.hostname:
                    raise ValueError("Production database URL must include hostname")

            return v

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid database URL format: {e}")

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Validates pool size.

        Args:
            v: Pool size value

        Returns:
            Validated pool size
        """
        if v < 1:
            raise ValueError("Pool size must be at least 1")
        if v > 100:
            raise ValueError("Pool size should not exceed 100")
        return v

    @field_validator("pool_timeout")
    @classmethod
    def validate_pool_timeout(cls, v: int) -> int:
        """Validates pool timeout.

        Args:
            v: Pool timeout value

        Returns:
            Validated pool timeout
        """
        if v < 1:
            raise ValueError("Pool timeout must be at least 1 second")
        return v

    def get_database_name(self) -> str:
        """Extracts database name from URL.

        Returns:
            Database name
        """
        parsed = urlparse(self.database_url)
        if parsed.path:
            return parsed.path.lstrip("/")
        return "unknown"

    def get_host(self) -> str | None:
        """Extracts host from URL.

        Returns:
            Database host or None for SQLite
        """
        parsed = urlparse(self.database_url)
        return parsed.hostname

    def get_port(self) -> int | None:
        """Extracts port from URL.

        Returns:
            Database port or None
        """
        parsed = urlparse(self.database_url)
        return parsed.port

    def get_username(self) -> str | None:
        """Extracts username from URL.

        Returns:
            Database username or None
        """
        parsed = urlparse(self.database_url)
        return parsed.username

    def is_sqlite(self) -> bool:
        """Checks if database is SQLite.

        Returns:
            True if SQLite database
        """
        return "sqlite" in self.database_url.lower()

    def is_postgresql(self) -> bool:
        """Checks if database is PostgreSQL.

        Returns:
            True if PostgreSQL database
        """
        return "postgresql" in self.database_url.lower()

    def is_in_memory_db(self) -> bool:
        """Checks if database is in-memory.

        Returns:
            True if in-memory database
        """
        return ":memory:" in self.database_url

    def __str__(self) -> str:
        """String representation with masked credentials.

        Returns:
            String representation
        """
        parsed = urlparse(self.database_url)
        if parsed.password:
            # Mask password in string representation
            masked_url = self.database_url.replace(parsed.password, "***")
            return f"DatabaseConfig(url={masked_url}, pool_size={self.pool_size})"
        return f"DatabaseConfig(url={self.database_url}, pool_size={self.pool_size})"
