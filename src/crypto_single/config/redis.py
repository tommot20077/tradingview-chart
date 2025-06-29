"""Redis cache configuration for crypto_single application.

This module provides Redis cache configuration classes with memory fallback,
TTL management, and graceful degradation when Redis is unavailable.
"""

from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseSettings):
    """Redis cache configuration for crypto_single application.

    Provides Redis caching configuration with memory fallback and graceful
    degradation when Redis is unavailable.

    Attributes:
        redis_url (str): Redis connection URL
        enabled (bool): Whether Redis is enabled
        fallback_to_memory (bool): Whether to fallback to memory cache
        max_connections (int): Maximum Redis connections
        connection_timeout (int): Connection timeout in seconds
        socket_timeout (int): Socket timeout in seconds
        default_ttl (int): Default TTL in seconds
        key_prefix (str): Key prefix for all cache keys
        key_separator (str): Key separator character
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore", env_prefix="REDIS_"
    )

    redis_url: str | None = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    enabled: bool = Field(default=False, description="Whether Redis is enabled")
    fallback_to_memory: bool = Field(
        default=True, description="Whether to fallback to memory cache when Redis unavailable"
    )
    max_connections: int = Field(default=10, ge=1, description="Maximum Redis connections in pool")
    connection_timeout: int = Field(default=10, ge=1, description="Connection timeout in seconds")
    socket_timeout: int = Field(default=5, ge=1, description="Socket timeout in seconds")
    default_ttl: int = Field(default=300, ge=0, description="Default TTL in seconds (0 = no expiration)")
    short_ttl: int = Field(default=60, ge=0, description="Short TTL in seconds")
    long_ttl: int = Field(default=3600, ge=0, description="Long TTL in seconds")
    key_prefix: str = Field(default="crypto_single:", description="Key prefix for all cache keys")
    key_separator: str = Field(default=":", description="Key separator character")
    memory_cache_size: int = Field(default=1000, ge=1, description="Memory cache size when Redis unavailable")
    memory_cache_ttl: int = Field(default=300, ge=0, description="Memory cache TTL in seconds")
    eviction_policy: str = Field(default="allkeys-lru", description="Redis eviction policy")
    max_memory_policy: str = Field(default="volatile-lru", description="Redis max memory policy")
    graceful_degradation: bool = Field(default=True, description="Continue without caching when Redis fails")
    health_check_interval: int = Field(default=30, ge=1, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, ge=1, description="Health check timeout in seconds")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str | None) -> str | None:
        """Validates Redis URL format.

        Args:
            v: Redis URL string

        Returns:
            Validated Redis URL

        Raises:
            ValueError: If URL format is invalid
        """
        if v is None:
            return None

        if not v.strip():
            raise ValueError("Redis URL cannot be empty")

        v = v.strip()

        try:
            parsed = urlparse(v)

            # Check for basic URL structure
            if not parsed.scheme:
                raise ValueError("Redis URL must include a scheme")

            # Check for supported schemes
            supported_schemes = {"redis", "rediss"}  # rediss for SSL

            if parsed.scheme not in supported_schemes:
                raise ValueError(f"Unsupported Redis scheme '{parsed.scheme}'. Supported schemes: {supported_schemes}")

            # Validate host
            if not parsed.hostname:
                raise ValueError("Redis URL must include a hostname")

            # Validate port
            if parsed.port is not None and (parsed.port < 1 or parsed.port > 65535):
                raise ValueError("Redis port must be between 1 and 65535")

            return v

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid Redis URL format: {e}")

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Validates max connections.

        Args:
            v: Max connections value

        Returns:
            Validated max connections
        """
        if v < 1:
            raise ValueError("Max connections must be at least 1")
        if v > 1000:
            raise ValueError("Max connections should not exceed 1000")
        return v

    @field_validator("connection_timeout", "socket_timeout")
    @classmethod
    def validate_timeouts(cls, v: int) -> int:
        """Validates timeout values.

        Args:
            v: Timeout value

        Returns:
            Validated timeout
        """
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        return v

    @field_validator("default_ttl", "short_ttl", "long_ttl", "memory_cache_ttl")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Validates TTL values.

        Args:
            v: TTL value

        Returns:
            Validated TTL
        """
        if v < 0:
            raise ValueError("TTL cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_configuration_consistency(self) -> "RedisConfig":
        """Validates configuration consistency.

        Raises:
            ValueError: If configuration is inconsistent
        """
        # If Redis is enabled, URL must be provided
        if self.enabled and not self.redis_url:
            raise ValueError("Redis URL is required when Redis is enabled")

        return self

    def should_use_memory_fallback(self) -> bool:
        """Determines if memory fallback should be used.

        Returns:
            True if should use memory fallback
        """
        return not self.enabled or self.fallback_to_memory

    def generate_key(self, *parts: str) -> str:
        """Generates a cache key from parts.

        Args:
            *parts: Key parts to join

        Returns:
            Generated cache key
        """
        # Filter out empty parts
        valid_parts = [str(part) for part in parts if part]
        if not valid_parts:
            raise ValueError("At least one key part must be provided")

        key = self.key_prefix + self.key_separator.join(valid_parts)
        return key

    def is_valid_key(self, key: str) -> bool:
        """Validates cache key format.

        Args:
            key: Cache key to validate

        Returns:
            True if key is valid
        """
        if not key or not key.strip():
            return False

        key = key.strip()

        # Check for invalid characters
        invalid_chars = {" ", "\n", "\r", "\t"}
        if any(char in key for char in invalid_chars):
            return False

        # Check key length (Redis has 512MB limit, but we'll be more conservative)
        return not len(key.encode("utf-8")) > 1024

    def get_redis_host(self) -> str:
        """Extracts host from Redis URL.

        Returns:
            Redis host
        """
        parsed = urlparse(self.redis_url)
        return str(parsed.hostname or "localhost")

    def get_redis_port(self) -> int:
        """Extracts port from Redis URL.

        Returns:
            Redis port
        """
        parsed = urlparse(self.redis_url)
        return parsed.port or 6379

    def get_redis_db(self) -> int:
        """Extracts database number from Redis URL.

        Returns:
            Redis database number
        """
        parsed = urlparse(self.redis_url)
        if parsed.path and parsed.path != "/":
            try:
                return int(str(parsed.path).lstrip("/"))
            except ValueError:
                pass
        return 0

    def get_redis_password(self) -> str | None:
        """Extracts password from Redis URL.

        Returns:
            Redis password or None
        """
        parsed = urlparse(self.redis_url)
        return str(parsed.password) if parsed.password else None

    def __str__(self) -> str:
        """String representation with masked password.

        Returns:
            String representation with sensitive information masked
        """
        # Mask password in URL if present
        if self.redis_url:
            parsed = urlparse(self.redis_url)
            if parsed.password:
                password_str = str(parsed.password)
                masked_url = self.redis_url.replace(password_str, "***")
                url_display = masked_url
            else:
                url_display = self.redis_url
        else:
            url_display = "None"

        return f"RedisConfig(url={url_display}, enabled={self.enabled}, fallback_to_memory={self.fallback_to_memory})"

    def __repr__(self) -> str:
        """Representation with masked password.

        Returns:
            String representation with sensitive information masked
        """
        return self.__str__()
