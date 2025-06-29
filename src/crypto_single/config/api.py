"""API service configuration for crypto_single application.

This module provides API service configuration classes for FastAPI with security
settings, CORS configuration, middleware setup, and production environment validation.
"""

import os
import re
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIConfig(BaseSettings):
    """API service configuration for crypto_single application.

    Provides FastAPI configuration with security settings, CORS, middleware,
    and environment-specific validation for production deployments.

    Attributes:
        host (str): API server host
        port (int): API server port
        debug (bool): Debug mode enabled
        reload (bool): Auto-reload for development
        secret_key (str): Secret key for JWT tokens
        algorithm (str): JWT algorithm
        access_token_expire_minutes (int): Access token expiration
        refresh_token_expire_minutes (int): Refresh token expiration
        cors_enabled (bool): Enable CORS middleware
        cors_origins (list[str]): Allowed CORS origins
        cors_methods (list[str]): Allowed CORS methods
        cors_headers (list[str]): Allowed CORS headers
        cors_allow_credentials (bool): Allow credentials in CORS
        middleware_enabled (bool): Enable custom middleware
        rate_limiting_enabled (bool): Enable rate limiting
        rate_limit_requests (int): Rate limit requests per window
        rate_limit_window (int): Rate limit window in seconds
        compression_enabled (bool): Enable response compression
        request_logging_enabled (bool): Enable request logging
        docs_enabled (bool): Enable API documentation
        openapi_url (str): OpenAPI JSON endpoint
        docs_url (str): Swagger UI endpoint
        redoc_url (str): ReDoc endpoint
        title (str): API title
        description (str): API description
        version (str): API version
        contact_email (str): Contact email
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore", env_prefix="API_"
    )

    # Server configuration
    host: str = Field(default="127.0.0.1", description="API server host")
    port: int = Field(default=8000, ge=1, le=65535, description="API server port")
    debug: bool = Field(default=False, description="Debug mode enabled")
    reload: bool = Field(default=False, description="Auto-reload for development")

    # Security configuration
    secret_key: str | None = Field(default=None, description="Secret key for JWT tokens and sessions")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="Access token expiration in minutes")
    refresh_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        ge=1,
        description="Refresh token expiration in minutes",
    )

    # CORS configuration
    cors_enabled: bool = Field(default=True, description="Enable CORS middleware")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"], description="Allowed CORS origins"
    )
    cors_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="Allowed CORS methods"
    )
    cors_headers: list[str] = Field(
        default_factory=lambda: ["Content-Type", "Authorization", "Accept"], description="Allowed CORS headers"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS requests")

    # Middleware configuration
    middleware_enabled: bool = Field(default=True, description="Enable custom middleware")
    rate_limiting_enabled: bool = Field(default=True, description="Enable rate limiting middleware")
    rate_limit_requests: int = Field(default=100, ge=1, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    compression_enabled: bool = Field(default=True, description="Enable response compression")
    request_logging_enabled: bool = Field(default=True, description="Enable request logging middleware")

    # Documentation configuration
    docs_enabled: bool = Field(default=True, description="Enable API documentation")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI JSON endpoint")
    docs_url: str = Field(default="/docs", description="Swagger UI endpoint")
    redoc_url: str = Field(default="/redoc", description="ReDoc endpoint")

    # API metadata
    title: str = Field(default="Crypto Single API", description="API title")
    description: str = Field(
        default="FastAPI application for single cryptocurrency trading", description="API description"
    )
    version: str = Field(default="1.0.0", description="API version")
    contact_email: str | None = Field(default=None, description="Contact email for API support")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validates host format.

        Args:
            v: Host string

        Returns:
            Validated host

        Raises:
            ValueError: If host format is invalid
        """
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")

        v = v.strip()

        # Check for spaces
        if " " in v:
            raise ValueError("Host cannot contain spaces")

        # Basic IP address validation
        if v not in ["localhost", "0.0.0.0"]:
            # Simple IP validation
            ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            if re.match(ip_pattern, v):
                # Validate IP octets
                octets = v.split(".")
                for octet in octets:
                    if int(octet) > 255:
                        raise ValueError("Invalid IP address format")

        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validates port number.

        Args:
            v: Port number

        Returns:
            Validated port

        Raises:
            ValueError: If port is invalid
        """
        if v < 1 or v > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str | None) -> str | None:
        """Validates secret key.

        Args:
            v: Secret key value

        Returns:
            Validated secret key

        Raises:
            ValueError: If secret key is invalid in production
        """
        # Production environment validation
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            if not v or not v.strip():
                raise ValueError("Secret key is required in production environment")

            v = v.strip()

            # Check for minimum length in production
            if len(v) < 32:
                raise ValueError("Secret key must be at least 32 characters in production")

            # Check for obviously weak keys
            weak_keys = {"secret", "key", "test", "demo", "sample", "example", "password"}
            if v.lower() in weak_keys:
                raise ValueError("Production secret key appears to be a test key")

            return v

        # Development/staging allows None but validates format for non-empty values
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Secret key cannot be empty if provided")

        return v

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validates JWT algorithm.

        Args:
            v: Algorithm string

        Returns:
            Validated algorithm

        Raises:
            ValueError: If algorithm is not supported
        """
        supported_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in supported_algorithms:
            raise ValueError(f"Unsupported algorithm '{v}'. Supported algorithms: {supported_algorithms}")
        return v

    @field_validator("debug")
    @classmethod
    def validate_debug(cls, v: bool) -> bool:
        """Validates debug mode setting.

        Args:
            v: Debug boolean value

        Returns:
            Validated debug setting

        Raises:
            ValueError: If debug is True in production
        """
        # Production environment should not use debug mode
        if os.getenv("ENVIRONMENT", "").lower() == "production" and v:
            raise ValueError("Debug mode is not allowed in production environment")

        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validates CORS origins.

        Args:
            v: List of CORS origins

        Returns:
            Validated CORS origins
        """
        if not v:
            return v

        # Check for empty origins
        valid_origins = []
        for origin in v:
            if origin and origin.strip():
                valid_origins.append(origin.strip())

        return valid_origins

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str | None) -> str | None:
        """Validates contact email format.

        Args:
            v: Email string

        Returns:
            Validated email

        Raises:
            ValueError: If email format is invalid
        """
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")

        return v

    @model_validator(mode="after")
    def validate_configuration_consistency(self) -> "APIConfig":
        """Validates configuration consistency.

        Raises:
            ValueError: If configuration is inconsistent
        """
        # Production environment checks
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            # Secret key is required in production
            if not self.secret_key:
                raise ValueError("Secret key is required in production environment")

            # CORS security check
            if self.cors_enabled and "*" in self.cors_origins and self.cors_allow_credentials:
                raise ValueError("CORS wildcard origins with credentials is not allowed in production")

        return self

    def get_server_url(self) -> str:
        """Gets the full server URL.

        Returns:
            Full server URL
        """
        protocol = "https" if os.getenv("ENVIRONMENT", "").lower() == "production" else "http"
        if self.port in (80, 443):
            return f"{protocol}://{self.host}"
        return f"{protocol}://{self.host}:{self.port}"

    def get_cors_config(self) -> dict[str, Any]:
        """Gets CORS configuration dictionary.

        Returns:
            CORS configuration
        """
        if not self.cors_enabled:
            return {}

        return {
            "allow_origins": self.cors_origins,
            "allow_methods": self.cors_methods,
            "allow_headers": self.cors_headers,
            "allow_credentials": self.cors_allow_credentials,
        }

    def get_docs_config(self) -> dict[str, Any]:
        """Gets documentation configuration.

        Returns:
            Docs configuration
        """
        if not self.docs_enabled:
            return {
                "openapi_url": None,
                "docs_url": None,
                "redoc_url": None,
            }

        return {
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "openapi_url": self.openapi_url,
            "docs_url": self.docs_url,
            "redoc_url": self.redoc_url,
            "contact": {"email": self.contact_email} if self.contact_email else None,
        }

    def is_production(self) -> bool:
        """Checks if running in production environment.

        Returns:
            True if production environment
        """
        return os.getenv("ENVIRONMENT", "").lower() == "production"

    def __str__(self) -> str:
        """String representation with masked secret key.

        Returns:
            String representation with sensitive information masked
        """
        masked_secret = None
        if self.secret_key:
            masked_secret = self.secret_key[:4] + "***" + self.secret_key[-4:] if len(self.secret_key) > 8 else "***"

        return f"APIConfig(host={self.host}, port={self.port}, debug={self.debug}, secret_key={masked_secret})"

    def __repr__(self) -> str:
        """Representation with masked secret key.

        Returns:
            String representation with sensitive information masked
        """
        return self.__str__()
