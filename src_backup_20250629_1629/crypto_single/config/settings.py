"""
Crypto Single Application Configuration Settings

This module defines the complete configuration structure for the crypto_single application,
inheriting from asset_core's BaseCoreSettings and extending it with application-specific
configuration options for databases, exchanges, APIs, and more.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, computed_field, SecretStr
from src.asset_core.asset_core.config.base import BaseCoreSettings


class SingleCryptoSettings(BaseCoreSettings):
    """
    Crypto Single Application Configuration Settings
    
    This class extends BaseCoreSettings to provide comprehensive configuration
    management for the crypto_single application, supporting:
    
    - Multiple database backends (PostgreSQL/SQLite + InfluxDB v3)
    - Multi-exchange data sources (Binance, with extensibility for Bybit, etc.)
    - Redis caching with memory fallback
    - FastAPI service configuration
    - Environment-specific validation and defaults
    - TDD-driven configuration validation
    """
    
    # Inherit model_config from BaseCoreSettings
    # Do not override model_config to ensure proper environment variable inheritance
    
    # === Application Settings (Override defaults) ===
    app_name: str = Field(default="crypto-single", description="Application name")

    environment: str = Field(
        default="development", 
        alias="APP_ENVIRONMENT",
        description="Environment (development, staging, production)"
    )
    
    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, v: str) -> str:
        """Validate app name and handle empty values."""
        if not v or v.isspace():
            return "crypto-single"  # Use default for empty values
        return v.strip()
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validates the environment field to ensure it's one of the allowed values."""
        # Handle empty values by using default
        if not v or v.isspace():
            return "development"  # Use default for empty values
        
        # Convert to lowercase for case-insensitive validation
        v = v.lower()
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v
    
    @field_validator("debug", mode="before")
    @classmethod
    def validate_debug(cls, v) -> bool:
        """Validate debug field and handle empty values."""
        # Handle empty string values
        if isinstance(v, str):
            if not v or v.isspace():
                return False  # Use default for empty values
            # Convert string to boolean
            return v.lower() in {"true", "1", "yes", "on"}
        # Handle boolean values directly
        return bool(v)
    
    # === Database Configuration ===
    
    # PostgreSQL/SQLite for metadata
    database_url: str = Field(
        default="",
        description="Database URL for metadata storage"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, ge=0, le=100, description="Database max overflow connections")
    
    # Health check and retry configuration
    database_health_check_interval: int = Field(default=30, ge=5, description="Database health check interval (seconds)")
    database_retry_attempts: int = Field(default=3, ge=1, le=10, description="Database retry attempts")
    database_retry_delay: int = Field(default=5, ge=1, le=60, description="Database retry delay (seconds)")
    database_circuit_breaker_enabled: bool = Field(default=True, description="Enable database circuit breaker")
    
    # Backup and monitoring
    database_backup_enabled: bool = Field(default=False, description="Enable database backup")
    database_backup_interval: int = Field(default=86400, ge=3600, description="Database backup interval (seconds)")
    database_metrics_enabled: bool = Field(default=True, description="Enable database metrics")
    database_slow_query_threshold: int = Field(default=1000, ge=100, description="Slow query threshold (milliseconds)")
    
    # Failover
    database_fallback_url: Optional[str] = Field(default=None, description="Database fallback URL")
    database_failover_enabled: bool = Field(default=False, description="Enable database failover")
    database_failover_timeout: int = Field(default=30, ge=5, description="Database failover timeout (seconds)")
    
    # Database isolation
    database_isolation_level: str = Field(default="READ_COMMITTED", description="Database isolation level")
    
    # === InfluxDB v3 Configuration ===
    
    influxdb_host: str = Field(default="", description="InfluxDB host URL")
    influxdb_token: SecretStr = Field(default="", description="InfluxDB authentication token")
    influxdb_database: str = Field(default="", description="InfluxDB database name")
    influxdb_org: str = Field(default="", description="InfluxDB organization")
    
    # InfluxDB connection settings
    influxdb_connection_pool_size: int = Field(default=10, ge=1, le=50, description="InfluxDB connection pool size")
    influxdb_max_connections: int = Field(default=20, ge=1, le=100, description="InfluxDB max connections")
    influxdb_timeout: int = Field(default=30, ge=5, le=300, description="InfluxDB request timeout (seconds)")
    influxdb_retry_attempts: int = Field(default=3, ge=1, le=10, description="InfluxDB retry attempts")
    influxdb_retry_delay: int = Field(default=2, ge=1, le=30, description="InfluxDB retry delay (seconds)")
    
    # InfluxDB health check and monitoring
    influxdb_health_check_interval: int = Field(default=60, ge=10, description="InfluxDB health check interval (seconds)")
    influxdb_metrics_enabled: bool = Field(default=True, description="Enable InfluxDB metrics")
    influxdb_query_timeout: int = Field(default=30, ge=5, description="InfluxDB query timeout (seconds)")
    
    # InfluxDB backup and failover
    influxdb_backup_enabled: bool = Field(default=False, description="Enable InfluxDB backup")
    influxdb_backup_retention: int = Field(default=30, ge=1, description="InfluxDB backup retention (days)")
    influxdb_fallback_host: Optional[str] = Field(default=None, description="InfluxDB fallback host")
    
    # InfluxDB write settings
    influxdb_write_precision: str = Field(default="ns", description="InfluxDB write precision")
    influxdb_write_consistency: str = Field(default="one", description="InfluxDB write consistency")
    influxdb_batch_size: int = Field(default=1000, ge=1, le=10000, description="InfluxDB batch size")
    influxdb_flush_interval: int = Field(default=5, ge=1, le=60, description="InfluxDB flush interval (seconds)")
    
    # === Redis Configuration ===
    
    redis_enabled: bool = Field(default=False, description="Enable Redis caching")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_password: Optional[SecretStr] = Field(default=None, description="Redis password")
    
    # Redis connection pool
    redis_pool_size: int = Field(default=10, ge=1, le=100, description="Redis connection pool size")
    redis_max_connections: int = Field(default=20, ge=1, le=200, description="Redis max connections")
    redis_socket_timeout: int = Field(default=5, ge=1, le=60, description="Redis socket timeout (seconds)")
    redis_socket_connect_timeout: int = Field(default=5, ge=1, le=60, description="Redis connect timeout (seconds)")
    
    # Redis TTL settings
    redis_default_ttl: int = Field(default=3600, ge=60, description="Redis default TTL (seconds)")
    redis_cache_prefix: str = Field(default="crypto_single", description="Redis cache key prefix")
    
    # Redis SSL and clustering
    redis_ssl_enabled: bool = Field(default=False, description="Enable Redis SSL")
    redis_cluster_enabled: bool = Field(default=False, description="Enable Redis clustering")
    
    # Redis serialization
    redis_serializer: str = Field(default="json", description="Redis serializer (json/pickle/msgpack)")
    
    # === Exchange Configuration (Binance + Multi-exchange support) ===
    
    # Binance configuration
    binance_enabled: bool = Field(default=True, description="Enable Binance data source")
    binance_api_key: Optional[SecretStr] = Field(default=None, description="Binance API key")
    binance_secret_key: Optional[SecretStr] = Field(default=None, description="Binance secret key")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")
    binance_trading_enabled: bool = Field(default=False, description="Enable Binance trading features")
    
    # Binance rate limiting
    binance_rate_limit_requests_per_minute: int = Field(default=1200, ge=100, le=6000, description="Binance rate limit requests per minute")
    binance_rate_limit_weight_per_minute: int = Field(default=1000, ge=100, le=6000, description="Binance rate limit weight per minute")
    binance_rate_limit_orders_per_second: int = Field(default=10, ge=1, le=100, description="Binance rate limit orders per second")
    
    # Binance WebSocket configuration
    binance_ws_reconnect_interval: int = Field(default=5, ge=1, le=60, description="Binance WebSocket reconnect interval (seconds)")
    binance_ws_max_reconnect_attempts: int = Field(default=10, ge=1, le=100, description="Binance WebSocket max reconnect attempts")
    binance_ws_ping_interval: int = Field(default=30, ge=10, le=300, description="Binance WebSocket ping interval (seconds)")
    binance_ws_ping_timeout: int = Field(default=10, ge=1, le=60, description="Binance WebSocket ping timeout (seconds)")
    
    # Binance data configuration
    binance_default_symbols: str = Field(default="BTCUSDT,ETHUSDT", description="Binance default symbols")
    binance_symbol_refresh_interval: int = Field(default=3600, ge=60, description="Binance symbol refresh interval (seconds)")
    binance_enable_trades: bool = Field(default=True, description="Enable Binance trade data")
    binance_enable_klines: bool = Field(default=True, description="Enable Binance kline data")
    binance_enable_ticker: bool = Field(default=False, description="Enable Binance ticker data")
    binance_enable_depth: bool = Field(default=False, description="Enable Binance depth data")
    
    # Future exchange support (Bybit, etc.)
    bybit_enabled: bool = Field(default=False, description="Enable Bybit data source")
    
    # Exchange priority and fallback
    primary_exchange: str = Field(default="binance", description="Primary exchange")
    exchange_priority_order: str = Field(default="binance", description="Exchange priority order (comma-separated)")
    
    # === API Service Configuration ===
    
    # FastAPI basic settings
    api_host: str = Field(default="127.0.0.1", description="API service host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API service port")
    api_debug: bool = Field(default=False, description="API debug mode")
    api_reload: bool = Field(default=False, description="API auto-reload")
    
    # API security
    secret_key: SecretStr = Field(default="", description="Secret key for JWT and security")
    access_token_expire_minutes: int = Field(default=60, ge=5, le=10080, description="Access token expiration (minutes)")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    
    # API CORS
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_allow_origins: str = Field(default="*", description="CORS allowed origins")
    cors_allow_methods: str = Field(default="GET,POST,PUT,DELETE", description="CORS allowed methods")
    cors_allow_headers: str = Field(default="Content-Type,Authorization", description="CORS allowed headers")
    
    # API middleware
    middleware_enable_gzip: bool = Field(default=True, description="Enable gzip middleware")
    middleware_enable_logging: bool = Field(default=True, description="Enable logging middleware")
    middleware_enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting middleware")
    middleware_rate_limit_requests: int = Field(default=100, ge=1, le=10000, description="Rate limit requests per window")
    middleware_rate_limit_window: int = Field(default=60, ge=1, le=3600, description="Rate limit window (seconds)")
    
    # API documentation
    api_docs_enabled: bool = Field(default=True, description="Enable API documentation")
    api_title: str = Field(default="Crypto Single API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(default="Cryptocurrency data API", description="API description")
    api_docs_url: str = Field(default="/docs", description="API docs URL")
    api_redoc_url: str = Field(default="/redoc", description="API ReDoc URL")
    api_docs_production_override: bool = Field(default=False, description="Override docs disabling in production")
    
    # API request limits
    api_max_request_size: int = Field(default=10485760, ge=1024, description="Max request size (bytes)")
    api_max_upload_size: int = Field(default=52428800, ge=1024, description="Max upload size (bytes)")
    
    # API timeouts
    api_request_timeout: int = Field(default=30, ge=1, le=300, description="API request timeout (seconds)")
    api_keepalive_timeout: int = Field(default=5, ge=1, le=300, description="API keepalive timeout (seconds)")
    api_graceful_shutdown_timeout: int = Field(default=10, ge=1, le=60, description="API graceful shutdown timeout (seconds)")
    
    # API authentication
    api_enable_auth: bool = Field(default=False, description="Enable API authentication")
    api_auth_type: str = Field(default="bearer", description="API authentication type")
    api_token_url: str = Field(default="/api/v1/auth/token", description="API token URL")
    
    # API versioning
    api_version_prefix: str = Field(default="/api/v1", description="API version prefix")
    api_default_version: str = Field(default="1.0", description="API default version")
    api_deprecated_versions: str = Field(default="", description="API deprecated versions")
    
    # === Cross-cutting Configuration ===
    
    # Health check
    health_check_timeout: int = Field(default=10, ge=1, le=60, description="Health check timeout (seconds)")
    
    # Cross-database transaction support
    enable_cross_database_transactions: bool = Field(default=False, description="Enable cross-database transactions")
    enable_timeseries_data: bool = Field(default=True, description="Enable timeseries data collection")
    
    # === Field Validators ===
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key_strength(cls, v: SecretStr) -> SecretStr:
        """Validate secret key strength, especially in production."""
        if isinstance(v, SecretStr):
            secret_value = v.get_secret_value()
        else:
            secret_value = str(v)
            v = SecretStr(secret_value)
            
        # In production, require strong secret keys
        import os
        environment = os.getenv("APP_ENVIRONMENT", "development").lower()
        # Treat empty environment as development
        if not environment or environment.isspace():
            environment = "development"
        
        if environment == "production":
            if len(secret_value) < 32:
                raise ValueError("Production environment requires secret key with at least 32 characters")
            if secret_value in ["weak", "password", "secret", "12345", "test"]:
                raise ValueError("Production environment prohibits common/weak secret keys")
        
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            # Set default based on environment
            import os
            environment = os.getenv("APP_ENVIRONMENT", "development").lower()
            # Treat empty environment as development
            if not environment or environment.isspace():
                environment = "development"
            if environment == "development":
                return "sqlite+aiosqlite:///./crypto_single_dev.db"
            else:
                raise ValueError("DATABASE_URL is required for non-development environments")
        
        # Validate URL format
        if not (v.startswith("postgresql://") or v.startswith("postgresql+asyncpg://") or 
                v.startswith("sqlite://") or v.startswith("sqlite+aiosqlite://")):
            raise ValueError("Database URL must be PostgreSQL or SQLite format")
        
        return v
    
    @field_validator("influxdb_host")
    @classmethod
    def validate_influxdb_host(cls, v: str) -> str:
        """Validate InfluxDB host URL."""
        if not v:
            # Set default based on environment
            import os
            environment = os.getenv("APP_ENVIRONMENT", "development").lower()
            # Treat empty environment as development
            if not environment or environment.isspace():
                environment = "development"
            if environment == "development":
                return "http://localhost:8086"
            elif environment == "production":
                # Production requires explicit InfluxDB configuration
                timeseries_enabled = os.getenv("ENABLE_TIMESERIES_DATA", "true").lower() == "true"
                if timeseries_enabled:
                    raise ValueError("Production environment with timeseries data requires INFLUXDB_HOST")
                else:
                    return ""
            
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("InfluxDB host must be a valid HTTP/HTTPS URL")
        
        return v
    
    @field_validator("api_host")
    @classmethod
    def validate_api_host(cls, v: str) -> str:
        """Validate API host address."""
        if not v or v.isspace():
            raise ValueError("API host cannot be empty")
        
        # Basic validation for common invalid formats
        if ".." in v or v.startswith(".") or v.endswith("."):
            raise ValueError("Invalid API host format")
        
        # Check for invalid IP addresses
        if v.count('.') == 3:  # Might be IP address
            parts = v.split('.')
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        raise ValueError("Invalid IP address format")
            except ValueError:
                pass  # Not an IP, continue with other validations
        
        return v.strip()
    
    @field_validator("cors_allow_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins, especially in production."""
        import os
        environment = os.getenv("APP_ENVIRONMENT", "development").lower()
        # Treat empty environment as development
        if not environment or environment.isspace():
            environment = "development"
        
        if environment == "production" and v == "*":
            raise ValueError("Production environment should not allow all CORS origins (*)")
        
        return v
    
    @field_validator("api_debug", "api_reload")
    @classmethod
    def validate_production_debug_settings(cls, v: bool, info) -> bool:
        """Validate that debug/reload are disabled in production."""
        import os
        environment = os.getenv("APP_ENVIRONMENT", "development").lower()
        # Treat empty environment as development
        if not environment or environment.isspace():
            environment = "development"
        
        if environment == "production" and v is True:
            field_name = info.field_name
            raise ValueError(f"Production environment requires {field_name} to be disabled")
        
        return v
    
    @field_validator("api_docs_enabled")
    @classmethod
    def validate_api_docs_production(cls, v: bool) -> bool:
        """Validate API docs settings in production."""
        import os
        environment = os.getenv("APP_ENVIRONMENT", "development").lower()
        # Treat empty environment as development
        if not environment or environment.isspace():
            environment = "development"
        docs_override = os.getenv("API_DOCS_PRODUCTION_OVERRIDE", "false").lower() == "true"
        
        if environment == "production" and v and not docs_override:
            return False  # Disable docs in production unless explicitly overridden
        
        return v
    
    @field_validator("binance_api_key")
    @classmethod
    def validate_binance_credentials(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validate Binance API credentials in production trading mode."""
        import os
        environment = os.getenv("APP_ENVIRONMENT", "development").lower()
        # Treat empty environment as development
        if not environment or environment.isspace():
            environment = "development"
        trading_enabled = os.getenv("BINANCE_TRADING_ENABLED", "false").lower() == "true"
        testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        
        if environment == "production" and trading_enabled and not testnet:
            if not v or not v.get_secret_value():
                raise ValueError("Production trading requires Binance API credentials")
            
            # Basic format validation
            api_key = v.get_secret_value()
            if len(api_key) < 10:
                raise ValueError("Binance API key appears to be too short")
        
        return v
    
    # === Computed Fields and Helper Methods ===
    
    @computed_field
    @property
    def is_production_environment(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @computed_field
    @property
    def is_development_environment(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get complete database configuration."""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "health_check_interval": self.database_health_check_interval,
            "retry_attempts": self.database_retry_attempts,
            "retry_delay": self.database_retry_delay,
            "circuit_breaker_enabled": self.database_circuit_breaker_enabled,
            "backup_enabled": self.database_backup_enabled,
            "metrics_enabled": self.database_metrics_enabled,
            "failover_enabled": self.database_failover_enabled,
            "fallback_url": self.database_fallback_url,
        }
    
    def get_influxdb_config(self) -> Dict[str, Any]:
        """Get complete InfluxDB configuration."""
        return {
            "host": self.influxdb_host,
            "token": self.influxdb_token.get_secret_value() if self.influxdb_token else "",
            "database": self.influxdb_database,
            "org": self.influxdb_org,
            "connection_pool_size": self.influxdb_connection_pool_size,
            "max_connections": self.influxdb_max_connections,
            "timeout": self.influxdb_timeout,
            "retry_attempts": self.influxdb_retry_attempts,
            "retry_delay": self.influxdb_retry_delay,
            "write_precision": self.influxdb_write_precision,
            "batch_size": self.influxdb_batch_size,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get complete Redis configuration."""
        return {
            "enabled": self.redis_enabled,
            "url": self.redis_url,
            "password": self.redis_password.get_secret_value() if self.redis_password else None,
            "pool_size": self.redis_pool_size,
            "max_connections": self.redis_max_connections,
            "default_ttl": self.redis_default_ttl,
            "cache_prefix": self.redis_cache_prefix,
            "ssl_enabled": self.redis_ssl_enabled,
            "cluster_enabled": self.redis_cluster_enabled,
            "serializer": self.redis_serializer,
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get complete API configuration."""
        return {
            "host": self.api_host,
            "port": self.api_port,
            "debug": self.api_debug,
            "reload": self.api_reload,
            "docs_enabled": self.api_docs_enabled,
            "title": self.api_title,
            "version": self.api_version,
            "description": self.api_description,
        }
    
    def get_api_base_url(self) -> str:
        """Get complete API base URL."""
        protocol = "https" if self.environment == "production" else "http"
        return f"{protocol}://{self.api_host}:{self.api_port}"
    
    # === Exchange Management Methods ===
    
    def get_registered_exchanges(self) -> List[str]:
        """Get list of registered exchanges."""
        exchanges = []
        if self.binance_enabled:
            exchanges.append("binance")
        if self.bybit_enabled:
            exchanges.append("bybit")
        return exchanges
    
    def get_enabled_exchanges(self) -> List[str]:
        """Get list of enabled exchanges."""
        return self.get_registered_exchanges()  # Currently same as registered
    
    def is_exchange_enabled(self, exchange_name: str) -> bool:
        """Check if specific exchange is enabled."""
        if exchange_name == "binance":
            return self.binance_enabled
        elif exchange_name == "bybit":
            return self.bybit_enabled
        return False
    
    def is_exchange_supported(self, exchange_name: str) -> bool:
        """Check if exchange is supported by the system."""
        supported_exchanges = ["binance", "bybit"]  # Future extensibility
        return exchange_name in supported_exchanges
    
    def get_exchange_config(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific exchange."""
        if exchange_name == "binance" and self.binance_enabled:
            return {
                "name": "binance",
                "enabled": self.binance_enabled,
                "api_key": self.binance_api_key.get_secret_value() if self.binance_api_key else None,
                "testnet": self.binance_testnet,
                "trading_enabled": self.binance_trading_enabled,
                "rate_limit_requests_per_minute": self.binance_rate_limit_requests_per_minute,
                "ws_reconnect_interval": self.binance_ws_reconnect_interval,
            }
        elif exchange_name == "bybit" and self.bybit_enabled:
            # Future Bybit implementation
            return {"name": "bybit", "enabled": False}
        return None
    
    def get_binance_base_url(self) -> str:
        """Get Binance base URL based on testnet setting."""
        if self.binance_testnet:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    def get_binance_ws_url(self) -> str:
        """Get Binance WebSocket URL based on testnet setting."""
        if self.binance_testnet:
            return "wss://testnet.binance.vision/ws"
        return "wss://stream.binance.com:9443/ws"
    
    def is_binance_enabled(self) -> bool:
        """Check if Binance is enabled."""
        return self.binance_enabled
    
    def is_binance_trading_enabled(self) -> bool:
        """Check if Binance trading is enabled."""
        return self.binance_enabled and self.binance_trading_enabled
    
    def is_binance_testnet(self) -> bool:
        """Check if Binance testnet is enabled."""
        return self.binance_testnet
    
    def get_binance_full_config(self) -> Dict[str, Any]:
        """Get complete Binance configuration."""
        return {
            "api_key": self.binance_api_key.get_secret_value() if self.binance_api_key else None,
            "testnet": self.binance_testnet,
            "trading_enabled": self.binance_trading_enabled,
            "base_url": self.get_binance_base_url(),
            "ws_url": self.get_binance_ws_url(),
            "rate_limits": {
                "requests_per_minute": self.binance_rate_limit_requests_per_minute,
                "weight_per_minute": self.binance_rate_limit_weight_per_minute,
                "orders_per_second": self.binance_rate_limit_orders_per_second,
            },
            "websocket": {
                "reconnect_interval": self.binance_ws_reconnect_interval,
                "max_reconnect_attempts": self.binance_ws_max_reconnect_attempts,
                "ping_interval": self.binance_ws_ping_interval,
                "ping_timeout": self.binance_ws_ping_timeout,
            },
            "data_types": {
                "trades": self.binance_enable_trades,
                "klines": self.binance_enable_klines,
                "ticker": self.binance_enable_ticker,
                "depth": self.binance_enable_depth,
            },
        }
    
    # === Database Helper Methods ===
    
    def get_metadata_db_config(self) -> Dict[str, Any]:
        """Get metadata database configuration."""
        return self.get_database_config()
    
    def get_timeseries_db_config(self) -> Dict[str, Any]:
        """Get timeseries database configuration."""
        return self.get_influxdb_config()
    
    def get_all_database_configs(self) -> Dict[str, Any]:
        """Get all database configurations."""
        return {
            "metadata": self.get_metadata_db_config(),
            "timeseries": self.get_timeseries_db_config(),
        }
    
    # === Environment Helper Methods ===
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "api_debug": self.api_debug,
            "api_docs_enabled": self.api_docs_enabled,
            "cors_enabled": self.cors_enabled,
        }
    
    # === Security Helper Methods ===
    
    def get_safe_secret_key(self) -> str:
        """Get masked secret key for safe display."""
        if self.secret_key:
            secret_value = self.secret_key.get_secret_value()
            if len(secret_value) > 8:
                return secret_value[:4] + "****" + secret_value[-4:]
            else:
                return "****"
        return "[NOT_SET]"
    
    def get_safe_binance_credentials(self) -> Dict[str, str]:
        """Get masked Binance credentials for safe display."""
        result = {}
        
        if self.binance_api_key:
            api_key = self.binance_api_key.get_secret_value()
            if len(api_key) > 8:
                result["api_key"] = api_key[:4] + "****" + api_key[-4:]
            else:
                result["api_key"] = "****"
        else:
            result["api_key"] = "[NOT_SET]"
        
        if self.binance_secret_key:
            secret_key = self.binance_secret_key.get_secret_value()
            if len(secret_key) > 8:
                result["secret_key"] = secret_key[:4] + "****" + secret_key[-4:]
            else:
                result["secret_key"] = "****"
        else:
            result["secret_key"] = "[NOT_SET]"
        
        return result
    
    # === Future Extensibility Methods ===
    
    def get_exchange_capabilities(self, exchange_name: str) -> Dict[str, bool]:
        """Get capabilities for specific exchange."""
        if exchange_name == "binance":
            return {
                "spot_trading": True,
                "futures_trading": True,
                "websocket_streams": True,
                "rest_api": True,
                "historical_data": True,
            }
        elif exchange_name == "bybit":
            return {
                "spot_trading": True,
                "futures_trading": True,
                "websocket_streams": True,
                "rest_api": True,
                "historical_data": True,
            }
        return {}
    
    def get_exchange_priority_order(self) -> List[str]:
        """Get exchange priority order."""
        return [exchange.strip() for exchange in self.exchange_priority_order.split(",") if exchange.strip()]
    
    def get_primary_exchange(self) -> str:
        """Get primary exchange."""
        return self.primary_exchange
    
    def create_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Create exchange configuration using factory pattern."""
        base_config = {
            "name": exchange_name,
            "enabled": self.is_exchange_enabled(exchange_name),
        }
        
        specific_config = self.get_exchange_config(exchange_name)
        if specific_config:
            base_config.update(specific_config)
        
        return base_config
    
    def validate_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Validate exchange configuration."""
        config = self.get_exchange_config(exchange_name)
        errors = []
        
        if not config:
            errors.append(f"Exchange {exchange_name} is not configured")
        else:
            # Validate specific exchange requirements
            if exchange_name == "binance":
                if config.get("trading_enabled") and not config.get("api_key"):
                    errors.append("Binance trading requires API key")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "config": config,
        }
    
    # Future plugin architecture placeholder
    def register_exchange_config(self, exchange_name: str, config: Dict[str, Any]) -> None:
        """Register new exchange configuration (future extensibility)."""
        # This would be implemented when we add dynamic exchange registration
        raise NotImplementedError("Dynamic exchange registration not yet implemented")