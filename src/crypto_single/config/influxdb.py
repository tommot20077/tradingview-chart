"""InfluxDB v3 configuration for crypto_single application.

This module provides InfluxDB v3 configuration classes for time-series data storage
with security validation and environment-specific requirements.
"""

import os
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfluxDBConfig(BaseSettings):
    """InfluxDB v3 configuration for crypto_single application.

    Provides configuration for InfluxDB v3 time-series database with security
    validation and environment-specific requirements.

    Attributes:
        host (str): InfluxDB host URL
        token (str): InfluxDB authentication token
        database (str): InfluxDB database name
        org (str): InfluxDB organization name
        health_check_timeout (int): Health check timeout in seconds
        health_check_retries (int): Number of health check retries
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore", env_prefix="INFLUXDB_"
    )

    host: str = Field(description="InfluxDB host URL")
    token: str = Field(description="InfluxDB authentication token")
    database: str = Field(description="InfluxDB database name")
    org: str | None = Field(default=None, description="InfluxDB organization name")
    health_check_timeout: int = Field(default=30, ge=1, description="Health check timeout in seconds")
    health_check_retries: int = Field(default=3, ge=0, description="Number of health check retries")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validates InfluxDB host URL.

        Args:
            v: Host URL string

        Returns:
            Validated host URL

        Raises:
            ValueError: If URL format is invalid or security requirements not met
        """
        if not v:
            raise ValueError("InfluxDB host cannot be empty")

        try:
            parsed = urlparse(v)

            # Must be a valid URL
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("InfluxDB host must be a valid URL")

            # Check supported schemes
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Unsupported scheme '{parsed.scheme}'. Use 'http' or 'https'")

            # Production environment must use HTTPS
            if os.getenv("ENVIRONMENT", "").lower() == "production" and parsed.scheme != "https":
                raise ValueError("Production environment requires HTTPS for InfluxDB host")

            return v

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid InfluxDB host URL: {e}")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validates InfluxDB authentication token.

        Args:
            v: Authentication token

        Returns:
            Validated token

        Raises:
            ValueError: If token is invalid
        """
        if not v or not v.strip():
            raise ValueError("InfluxDB token cannot be empty")

        # Production environment token validation
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            if len(v.strip()) < 10:
                raise ValueError("Production InfluxDB token must be at least 10 characters long")

            # Check for obviously weak tokens
            weak_tokens = {"test", "token", "password", "123", "abc", "dev"}
            if v.strip().lower() in weak_tokens:
                raise ValueError("Production InfluxDB token appears to be a weak test token")

        return v.strip()

    @field_validator("database")
    @classmethod
    def validate_database(cls, v: str) -> str:
        """Validates InfluxDB database name.

        Args:
            v: Database name

        Returns:
            Validated database name

        Raises:
            ValueError: If database name is invalid
        """
        if not v or not v.strip():
            raise ValueError("InfluxDB database name cannot be empty")

        # Basic database name validation
        db_name = v.strip()
        if len(db_name) > 64:
            raise ValueError("Database name cannot exceed 64 characters")

        # Check for invalid characters (basic validation)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", db_name):
            raise ValueError("Database name can only contain letters, numbers, underscores, and hyphens")

        return db_name

    @field_validator("org")
    @classmethod
    def validate_org(cls, v: str | None) -> str | None:
        """Validates InfluxDB organization name.

        Args:
            v: Organization name

        Returns:
            Validated organization name or None
        """
        if v is None or not v.strip():
            return None

        org_name = v.strip()
        if len(org_name) > 64:
            raise ValueError("Organization name cannot exceed 64 characters")

        return org_name

    def get_health_check_url(self) -> str:
        """Generates health check URL.

        Returns:
            Health check endpoint URL
        """
        parsed = urlparse(self.host)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # InfluxDB v3 health check endpoint
        if parsed.path:
            return f"{base}{parsed.path}/health"
        return f"{base}/health"

    def get_write_url(self) -> str:
        """Generates write API URL.

        Returns:
            Write API endpoint URL
        """
        parsed = urlparse(self.host)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # InfluxDB v3 write endpoint
        if parsed.path:
            return f"{base}{parsed.path}/api/v2/write"
        return f"{base}/api/v2/write"

    def get_query_url(self) -> str:
        """Generates query API URL.

        Returns:
            Query API endpoint URL
        """
        parsed = urlparse(self.host)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # InfluxDB v3 query endpoint
        if parsed.path:
            return f"{base}{parsed.path}/api/v2/query"
        return f"{base}/api/v2/query"

    def get_connection_headers(self) -> dict:
        """Generates connection headers.

        Returns:
            Dictionary of HTTP headers for InfluxDB connection
        """
        headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.org:
            headers["Influx-Org"] = self.org

        return headers

    def get_connection_url(self) -> str:
        """Generates full connection URL for InfluxDB.

        Returns:
            Full connection URL string
        """
        return f"{self.host}/{self.database}"

    def __str__(self) -> str:
        """String representation with masked token.

        Returns:
            String representation with sensitive information masked
        """
        # Mask the token in string representation
        masked_token = self.token[:4] + "***" + self.token[-4:] if len(self.token) > 8 else "***"

        return f"InfluxDBConfig(host={self.host}, database={self.database}, token={masked_token}, org={self.org})"

    def __repr__(self) -> str:
        """Representation with masked token.

        Returns:
            String representation with sensitive information masked
        """
        return self.__str__()
