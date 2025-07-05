"""Exchange configuration for crypto_single application.

This module provides exchange configuration classes for different cryptocurrency
exchanges with multi-exchange support, dynamic registration, and security handling.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExchangeConfig(BaseSettings, ABC):
    """Abstract base class for exchange configurations.

    Provides common interface and functionality for all exchange configurations.
    All exchange-specific configs must inherit from this class.
    """

    @abstractmethod
    def get_base_url(self) -> str:
        """Get the base URL for the exchange API.

        Returns:
            Base API URL
        """
        pass

    @abstractmethod
    def get_testnet_base_url(self) -> str:
        """Get the testnet/sandbox base URL for the exchange API.

        Returns:
            Testnet base API URL
        """
        pass

    @abstractmethod
    def get_websocket_url(self, stream_type: str | None = None) -> str:
        """Get the WebSocket URL for the exchange.

        Args:
            stream_type: Optional stream type (e.g., 'ticker', 'depth', 'trade')

        Returns:
            WebSocket URL
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate exchange credentials.

        Returns:
            True if credentials are valid
        """
        pass


class BinanceConfig(ExchangeConfig):
    """Binance exchange configuration.

    Provides configuration for Binance exchange including API credentials,
    testnet support, and environment-specific validation.

    Attributes:
        api_key (str): Binance API key
        secret_key (str): Binance secret key
        testnet (bool): Whether to use testnet
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore", env_prefix="BINANCE_"
    )

    api_key: str | None = Field(default=None, description="Binance API key")
    secret_key: str | None = Field(default=None, description="Binance secret key")
    testnet: bool = Field(default=False, description="Whether to use Binance testnet")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        """Validates API key.

        Args:
            v: API key value

        Returns:
            Validated API key

        Raises:
            ValueError: If API key is invalid in production
        """
        # Production environment validation
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            if not v or not v.strip():
                raise ValueError("API key is required in production environment")

            v = v.strip()

            # Check for weak keys
            if len(v) < 10:
                raise ValueError("API key must be at least 10 characters in production")

            # Check for obviously weak test keys
            weak_keys = {"test", "demo", "sample", "example", "api-key"}
            if v.lower() in weak_keys:
                raise ValueError("Production API key appears to be a test key")

            # Check for invalid characters in production
            if any(char in v for char in [" ", "\n", "\r", "\t"]):
                raise ValueError("API key cannot contain spaces or newlines")

            return v

        # Development/staging allows None but validates format for non-empty values
        if v is not None:
            v = v.strip()

            # Check for invalid characters even in development
            if any(char in v for char in [" ", "\n", "\r", "\t"]):
                raise ValueError("API key cannot contain spaces or newlines")

            # Reject empty strings (after stripping)
            if not v:
                raise ValueError("API key cannot be empty or whitespace only")

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

            # Check for weak keys
            if len(v) < 10:
                raise ValueError("Secret key must be at least 10 characters in production")

            # Check for obviously weak test keys
            weak_keys = {"test", "demo", "sample", "example", "secret-key"}
            if v.lower() in weak_keys:
                raise ValueError("Production secret key appears to be a test key")

            # Check for invalid characters in production
            if any(char in v for char in [" ", "\n", "\r", "\t"]):
                raise ValueError("Secret key cannot contain spaces or newlines")

            return v

        # Development/staging allows None but validates format for non-empty values
        if v is not None:
            v = v.strip()

            # Check for invalid characters even in development
            if any(char in v for char in [" ", "\n", "\r", "\t"]):
                raise ValueError("Secret key cannot contain spaces or newlines")

            # Reject empty strings (after stripping)
            if not v:
                raise ValueError("Secret key cannot be empty or whitespace only")

        return v

    @field_validator("testnet")
    @classmethod
    def validate_testnet(cls, v: bool) -> bool:
        """Validates testnet setting.

        Args:
            v: Testnet boolean value

        Returns:
            Validated testnet setting

        Raises:
            ValueError: If testnet is True in production
        """
        # Production environment should not use testnet
        if os.getenv("ENVIRONMENT", "").lower() == "production" and v:
            raise ValueError("Testnet mode is not allowed in production environment")

        return v

    def get_base_url(self) -> str:
        """Get Binance base URL.

        Returns:
            Binance API base URL
        """
        if self.testnet:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"

    def get_testnet_base_url(self) -> str:
        """Get Binance testnet URL.

        Returns:
            Binance testnet API URL
        """
        return "https://testnet.binance.vision"

    def get_websocket_url(self, stream_type: str | None = None) -> str:
        """Get Binance WebSocket URL.

        Args:
            stream_type: Stream type (ticker, depth, trade, etc.)

        Returns:
            Binance WebSocket URL
        """
        base = "wss://testnet.binance.vision/ws" if self.testnet else "wss://stream.binance.com:9443/ws"

        # Add stream-specific suffix if needed
        if stream_type:
            return f"{base}/{stream_type}"

        return base

    def validate_credentials(self) -> bool:
        """Validate Binance credentials.

        Returns:
            True if credentials are present and valid format
        """
        # In development, credentials are optional
        if os.getenv("ENVIRONMENT", "").lower() == "development":
            return True

        # In production/staging, credentials are required
        return bool(self.api_key and self.secret_key)

    def __str__(self) -> str:
        """String representation with masked credentials.

        Returns:
            String representation with sensitive information masked
        """
        masked_api = self.api_key[:4] + "***" + self.api_key[-4:] if self.api_key and len(self.api_key) > 8 else "***"
        masked_secret = (
            self.secret_key[:4] + "***" + self.secret_key[-4:]
            if self.secret_key and len(self.secret_key) > 8
            else "***"
        )

        return f"BinanceConfig(api_key={masked_api}, secret_key={masked_secret}, testnet={self.testnet})"

    def __repr__(self) -> str:
        """Representation with masked credentials.

        Returns:
            String representation with sensitive information masked
        """
        return self.__str__()


class ExchangeRegistry:
    """Registry for managing exchange configurations.

    Provides dynamic registration and retrieval of exchange configuration classes.
    """

    def __init__(self) -> None:
        self._exchanges: dict[str, type[ExchangeConfig]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(self, name: str, config_class: type[ExchangeConfig], metadata: dict[str, Any] | None = None) -> None:
        """Register an exchange configuration class.

        Args:
            name: Exchange name
            config_class: Exchange configuration class
            metadata: Optional metadata about the exchange
        """
        if not issubclass(config_class, ExchangeConfig):
            raise ValueError("Config class must inherit from ExchangeConfig")

        self._exchanges[name] = config_class
        self._metadata[name] = metadata or {}

    def get(self, name: str) -> type[ExchangeConfig]:
        """Get exchange configuration class by name.

        Args:
            name: Exchange name

        Returns:
            Exchange configuration class

        Raises:
            KeyError: If exchange is not registered
        """
        if name not in self._exchanges:
            raise KeyError(f"Exchange '{name}' is not registered")
        return self._exchanges[name]

    def get_metadata(self, name: str) -> dict[str, Any]:
        """Get exchange metadata by name.

        Args:
            name: Exchange name

        Returns:
            Exchange metadata
        """
        return self._metadata.get(name, {})

    def create_config(self, name: str, config_data: dict[str, Any]) -> ExchangeConfig:
        """Create exchange configuration instance.

        Args:
            name: Exchange name
            config_data: Configuration data

        Returns:
            Exchange configuration instance
        """
        config_class = self.get(name)
        return config_class(**config_data)

    def list_exchanges(self) -> list[str]:
        """List all registered exchanges.

        Returns:
            List of exchange names
        """
        return list(self._exchanges.keys())


class ExchangeConfigManager:
    """Manager for handling multiple exchange configurations.

    Provides high-level interface for managing exchange configurations,
    loading from environment, and coordinating multiple exchanges.
    """

    def __init__(self) -> None:
        self.registry = ExchangeRegistry()
        self._configs: dict[str, ExchangeConfig] = {}

        # Register built-in exchanges
        self._register_builtin_exchanges()

    def _register_builtin_exchanges(self) -> None:
        """Register built-in exchange configurations."""
        self.registry.register(
            "binance",
            BinanceConfig,
            {
                "name": "Binance",
                "supported_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                "supports_testnet": True,
                "rate_limits": {"orders": 1200, "requests": 6000},
            },
        )

    def register_exchange(
        self, name: str, config_class: type[ExchangeConfig], metadata: dict[str, Any] | None = None
    ) -> None:
        """Register a new exchange.

        Args:
            name: Exchange name
            config_class: Exchange configuration class
            metadata: Optional metadata
        """
        self.registry.register(name, config_class, metadata)

    def get_available_exchanges(self) -> list[str]:
        """Get list of available exchanges.

        Returns:
            List of exchange names
        """
        return self.registry.list_exchanges()

    def create_exchange_config(self, name: str, config_data: dict[str, Any]) -> ExchangeConfig:
        """Create exchange configuration.

        Args:
            name: Exchange name
            config_data: Configuration data

        Returns:
            Exchange configuration instance
        """
        return self.registry.create_config(name, config_data)

    def configure_exchanges(self, configs: dict[str, dict[str, Any]]) -> dict[str, ExchangeConfig]:
        """Configure multiple exchanges.

        Args:
            configs: Dictionary of exchange configurations

        Returns:
            Dictionary of configured exchange instances
        """
        configured = {}

        for name, config_data in configs.items():
            configured[name] = self.registry.create_config(name, config_data)

        self._configs = configured
        return configured

    def load_configurations_from_environment(self) -> dict[str, ExchangeConfig]:
        """Load exchange configurations from environment variables.

        Returns:
            Dictionary of configured exchange instances
        """
        enabled_exchanges = os.getenv("EXCHANGES_ENABLED", "").split(",")
        enabled_exchanges = [ex.strip() for ex in enabled_exchanges if ex.strip()]

        if not enabled_exchanges:
            return {}

        configs = {}
        for exchange_name in enabled_exchanges:
            if exchange_name in self.registry.list_exchanges():
                # Create instance with environment variable loading
                config_class = self.registry.get(exchange_name)
                configs[exchange_name] = config_class()

        self._configs = configs
        return configs

    def load_configurations(self, config_data: dict[str, dict[str, Any]]) -> dict[str, ExchangeConfig]:
        """Load exchange configurations from data.

        Args:
            config_data: Configuration data

        Returns:
            Dictionary of configured exchange instances
        """
        return self.configure_exchanges(config_data)

    def load_exchange_plugin(self, name: str) -> type[ExchangeConfig]:
        """Load exchange as plugin (mock implementation).

        Args:
            name: Exchange name

        Returns:
            Exchange configuration class

        Raises:
            ImportError: If exchange plugin not found
        """
        return self._load_exchange_plugin(name)

    def _load_exchange_plugin(self, name: str) -> type[ExchangeConfig]:
        """Internal method to load exchange plugin.

        Args:
            name: Exchange name

        Returns:
            Exchange configuration class

        Raises:
            ImportError: If exchange plugin not found
        """
        # This is a mock implementation for the plugin pattern
        # In a real implementation, this would dynamically import exchange modules
        if name == "binance":
            return BinanceConfig
        raise ImportError(f"Exchange plugin {name} not found")
