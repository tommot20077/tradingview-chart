#!/usr/bin/env python3
"""
Example: How to configure applications using asset_core.

This example demonstrates:
1. Using base configuration classes
2. Creating environment-specific configurations
3. Configuration validation
4. Loading configuration from files and environment variables
5. Extending configurations for custom applications
"""

import os
import tempfile

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.asset_core.asset_core.config.base import BaseCoreSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="trading_db", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    pool_size: int = Field(default=10, description="Connection pool size")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode."""
        allowed = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if v not in allowed:
            raise ValueError(f"ssl_mode must be one of {allowed}")
        return v

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Validate connection pool size."""
        if not 1 <= v <= 100:
            raise ValueError("pool_size must be between 1 and 100")
        return v

    @property
    def connection_url(self) -> str:
        """Generate database connection URL."""
        password_part = f":{self.password}" if self.password else ""
        return f"postgresql://{self.username}{password_part}@{self.host}:{self.port}/{self.name}"


class ExchangeConfig(BaseSettings):
    """Exchange API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EXCHANGE_",
        case_sensitive=False,
    )

    name: str = Field(..., description="Exchange name")
    api_key: str = Field(default="", description="API key")
    api_secret: str = Field(default="", description="API secret")
    testnet: bool = Field(default=True, description="Use testnet")
    rate_limit: int = Field(default=1200, description="Rate limit per minute")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate exchange name."""
        allowed = {"binance", "okx", "bybit", "coinbase"}
        if v.lower() not in allowed:
            raise ValueError(f"Unsupported exchange: {v}. Allowed: {allowed}")
        return v.lower()

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate rate limit."""
        if not 1 <= v <= 10000:
            raise ValueError("rate_limit must be between 1 and 10000")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout."""
        if not 1.0 <= v <= 300.0:
            raise ValueError("timeout must be between 1.0 and 300.0 seconds")
        return v


class TradingAppConfig(BaseCoreSettings):
    """Complete trading application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Override app name
    app_name: str = Field(default="trading-app", description="Application name")

    # Nested configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    exchange: ExchangeConfig = Field(default_factory=lambda: ExchangeConfig(name="binance"))

    # Trading-specific settings
    symbols: list[str] = Field(default=["BTCUSDT", "ETHUSDT"], description="Trading symbols")
    max_positions: int = Field(default=10, description="Maximum open positions")
    risk_percentage: float = Field(default=2.0, description="Risk percentage per trade")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        """Validate trading symbols."""
        if not v:
            raise ValueError("At least one symbol must be specified")

        # Normalize symbols to uppercase
        normalized = [symbol.upper().strip() for symbol in v]

        # Basic validation for common patterns
        for symbol in normalized:
            if not symbol or len(symbol) < 6:
                raise ValueError(f"Invalid symbol format: {symbol}")

        return normalized

    @field_validator("max_positions")
    @classmethod
    def validate_max_positions(cls, v: int) -> int:
        """Validate maximum positions."""
        if not 1 <= v <= 100:
            raise ValueError("max_positions must be between 1 and 100")
        return v

    @field_validator("risk_percentage")
    @classmethod
    def validate_risk_percentage(cls, v: float) -> float:
        """Validate risk percentage."""
        if not 0.1 <= v <= 10.0:
            raise ValueError("risk_percentage must be between 0.1 and 10.0")
        return v

    def get_symbol_config(self, symbol: str) -> dict:
        """Get configuration for a specific symbol."""
        return {
            "symbol": symbol,
            "risk_percentage": self.risk_percentage,
            "max_position_size": 1.0 / self.max_positions,
        }


def demonstrate_basic_configuration():
    """Demonstrate basic configuration usage."""
    print("1️⃣ Basic Configuration")
    print("-" * 30)

    # Create configuration with defaults
    config = BaseCoreSettings()
    print(f"App name: {config.app_name}")
    print(f"Environment: {config.environment}")
    print(f"Debug mode: {config.debug}")
    print(f"Is production: {config.is_production()}")
    print(f"Is development: {config.is_development()}")

    # Create configuration with custom values
    prod_config = BaseCoreSettings(app_name="trading-prod", environment="production", debug=False)
    print("\nProduction config:")
    print(f"  App name: {prod_config.app_name}")
    print(f"  Environment: {prod_config.environment}")
    print(f"  Is production: {prod_config.is_production()}")


def demonstrate_nested_configuration():
    """Demonstrate nested configuration structures."""
    print("\n2️⃣ Nested Configuration")
    print("-" * 30)

    # Create database configuration
    db_config = DatabaseConfig(
        host="prod-db.example.com",
        port=5432,
        name="trading_prod",
        username="trader",
        password="secret123",
        ssl_mode="require",
        pool_size=20,
    )

    print("Database config:")
    print(f"  Host: {db_config.host}")
    print(f"  Port: {db_config.port}")
    print(f"  Connection URL: {db_config.connection_url}")
    print(f"  Pool size: {db_config.pool_size}")

    # Create exchange configuration
    exchange_config = ExchangeConfig(
        name="binance", api_key="your_api_key_here", testnet=False, rate_limit=1200, timeout=30.0
    )

    print("\nExchange config:")
    print(f"  Name: {exchange_config.name}")
    print(f"  Testnet: {exchange_config.testnet}")
    print(f"  Rate limit: {exchange_config.rate_limit}")


def demonstrate_environment_variables():
    """Demonstrate loading configuration from environment variables."""
    print("\n3️⃣ Environment Variables")
    print("-" * 30)

    # Set some environment variables
    os.environ["APP_NAME"] = "env-trading-app"
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["DEBUG"] = "true"
    os.environ["DB_HOST"] = "staging-db.example.com"
    os.environ["DB_PORT"] = "5433"
    os.environ["EXCHANGE_NAME"] = "okx"
    os.environ["EXCHANGE_TESTNET"] = "false"

    try:
        # Load configuration from environment
        config = TradingAppConfig()

        print("Loaded from environment:")
        print(f"  App name: {config.app_name}")
        print(f"  Environment: {config.environment}")
        print(f"  Debug: {config.debug}")
        print(f"  DB host: {config.database.host}")
        print(f"  DB port: {config.database.port}")
        print(f"  Exchange: {config.exchange.name}")
        print(f"  Exchange testnet: {config.exchange.testnet}")

    finally:
        # Clean up environment variables
        for key in ["APP_NAME", "ENVIRONMENT", "DEBUG", "DB_HOST", "DB_PORT", "EXCHANGE_NAME", "EXCHANGE_TESTNET"]:
            os.environ.pop(key, None)


def demonstrate_configuration_files():
    """Demonstrate loading configuration from files."""
    print("\n4️⃣ Configuration Files")
    print("-" * 30)

    # Create temporary configuration file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("""
# Trading Application Configuration
APP_NAME=file-trading-app
ENVIRONMENT=production
DEBUG=false

# Database Configuration
DB_HOST=prod-database.internal
DB_PORT=5432
DB_NAME=trading_production
DB_USERNAME=prod_trader
DB_PASSWORD=super_secure_password
DB_SSL_MODE=require
DB_POOL_SIZE=25

# Exchange Configuration
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=prod_api_key_12345
EXCHANGE_TESTNET=false
EXCHANGE_RATE_LIMIT=1500
EXCHANGE_TIMEOUT=45.0

# Trading Configuration
SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT,DOTUSDT
MAX_POSITIONS=15
RISK_PERCENTAGE=1.5
""")
        config_file = f.name

    try:
        # Load configuration from file
        config = TradingAppConfig(_env_file=config_file)

        print(f"Loaded from file ({config_file}):")
        print(f"  App name: {config.app_name}")
        print(f"  Environment: {config.environment}")
        print(f"  Symbols: {config.symbols}")
        print(f"  Max positions: {config.max_positions}")
        print(f"  Risk percentage: {config.risk_percentage}%")
        print(f"  DB connection: {config.database.connection_url}")
        print(f"  Exchange: {config.exchange.name} (testnet: {config.exchange.testnet})")

        # Demonstrate symbol-specific configuration
        print("\nSymbol configurations:")
        for symbol in config.symbols[:2]:  # Show first 2 symbols
            symbol_config = config.get_symbol_config(symbol)
            print(f"  {symbol}: {symbol_config}")

    finally:
        # Clean up temporary file
        os.unlink(config_file)


def demonstrate_configuration_validation():
    """Demonstrate configuration validation."""
    print("\n5️⃣ Configuration Validation")
    print("-" * 30)

    # Test valid configuration
    try:
        valid_config = ExchangeConfig(name="binance", rate_limit=1200, timeout=30.0)
        print(f"✅ Valid exchange config: {valid_config.name}")
    except Exception as e:
        print(f"❌ Validation error: {e}")

    # Test invalid exchange name
    try:
        invalid_config = ExchangeConfig(name="invalid_exchange", rate_limit=1200, timeout=30.0)
        print(f"Should not reach here: {invalid_config.name}")
    except Exception as e:
        print(f"❌ Expected validation error: {e}")

    # Test invalid rate limit
    try:
        invalid_config = ExchangeConfig(
            name="binance",
            rate_limit=50000,  # Too high
            timeout=30.0,
        )
        print(f"Should not reach here: {invalid_config.rate_limit}")
    except Exception as e:
        print(f"❌ Expected validation error: {e}")

    # Test invalid symbols
    try:
        invalid_config = TradingAppConfig(
            symbols=["BTC", "E"]  # Too short
        )
        print(f"Should not reach here: {invalid_config.symbols}")
    except Exception as e:
        print(f"❌ Expected validation error: {e}")


def main():
    """Main demonstration function."""
    print("⚙️  Configuration System Example")
    print("=" * 50)

    demonstrate_basic_configuration()
    demonstrate_nested_configuration()
    demonstrate_environment_variables()
    demonstrate_configuration_files()
    demonstrate_configuration_validation()

    print("\n✅ Configuration examples completed!")
    print("\nKey takeaways:")
    print("- Use CoreSettings as base for all application configurations")
    print("- Leverage Pydantic validation for robust configuration")
    print("- Support both environment variables and configuration files")
    print("- Implement custom validation for business logic")
    print("- Use nested configurations for complex applications")


if __name__ == "__main__":
    main()
