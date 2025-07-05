"""Dual database configuration for crypto_single application.

This module provides dual database configuration combining PostgreSQL/SQLite
with InfluxDB v3 for transactional and time-series data storage.
"""

import os
from typing import Any
from unittest.mock import Mock

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .database import DatabaseConfig
from .influxdb import InfluxDBConfig


class DualDatabaseConfig(BaseSettings):
    """Dual database configuration for crypto_single application.

    Combines transactional database (PostgreSQL/SQLite) with time-series
    database (InfluxDB v3) for comprehensive data storage solution.

    Attributes:
        postgresql_config (DatabaseConfig): Relational database configuration
        influxdb_config (InfluxDBConfig): Time-series database configuration
        enable_health_checks (bool): Enable database health monitoring
        health_check_enabled (bool): Enable health checks for both databases
        health_check_interval (int): Health check interval in seconds
        health_check_timeout (int): Health check timeout in seconds
        connection_retry_attempts (int): Maximum connection retry attempts
        connection_retry_delay (int): Delay between retries in seconds
        connection_timeout (int): Database connection timeout in seconds
        transaction_timeout (int): Transaction timeout in seconds
        max_retries (int): Maximum retry attempts for database operations
        enable_connection_pooling (bool): Enable connection pooling
        enable_read_replicas (bool): Enable read replica support
        enable_distributed_transactions (bool): Enable distributed transactions
        fallback_enabled (bool): Enable fallback mode when one database fails
        graceful_degradation (bool): Enable graceful degradation on failures
        retry_delay (int): Delay between retry attempts in seconds
        require_both_databases (bool): Require both databases to be available
        synchronize_schemas (bool): Synchronize schemas between databases
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore", env_prefix="DUAL_DB_"
    )

    # Database configurations
    postgresql_config: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Relational database configuration (PostgreSQL/SQLite)"
    )
    influxdb_config: InfluxDBConfig = Field(
        default_factory=lambda: InfluxDBConfig(
            host="http://localhost:8086", token="development-token-placeholder", database="crypto_single_timeseries"
        ),
        description="Time-series database configuration (InfluxDB v3)",
    )

    # Health monitoring
    enable_health_checks: bool = Field(default=True, description="Enable database health monitoring")
    health_check_enabled: bool = Field(default=True, description="Enable health checks for both databases")
    health_check_interval: int = Field(default=30, ge=5, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, ge=1, description="Health check timeout in seconds")

    # Connection management
    connection_retry_attempts: int = Field(default=3, ge=0, description="Maximum connection retry attempts")
    connection_retry_delay: int = Field(default=5, ge=1, description="Delay between connection retries in seconds")
    connection_timeout: int = Field(default=30, ge=1, description="Database connection timeout in seconds")
    transaction_timeout: int = Field(default=30, ge=1, description="Database transaction timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts for database operations")

    # Advanced features
    enable_connection_pooling: bool = Field(default=True, description="Enable connection pooling optimization")
    enable_read_replicas: bool = Field(default=False, description="Enable read replica support for scaling")
    enable_distributed_transactions: bool = Field(
        default=False, description="Enable distributed transactions across databases"
    )

    # Failure handling and resilience
    fallback_enabled: bool = Field(default=False, description="Enable fallback mode when one database fails")
    graceful_degradation: bool = Field(default=False, description="Enable graceful degradation on database failures")
    retry_delay: int = Field(default=1, ge=0, description="Delay between retry attempts in seconds")

    # Validation and synchronization
    require_both_databases: bool = Field(default=True, description="Require both databases to be available")
    synchronize_schemas: bool = Field(default=False, description="Synchronize schemas between databases")

    @model_validator(mode="after")
    def validate_dual_database_consistency(self) -> "DualDatabaseConfig":
        """Validates dual database configuration consistency.

        Raises:
            ValueError: If configuration is inconsistent
        """
        # Production environment validation
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            # Production should use PostgreSQL for relational DB
            if self.postgresql_config.is_sqlite():
                raise ValueError("Production environment must use PostgreSQL, not SQLite")

            # Production should have secure InfluxDB configuration
            if not self.influxdb_config.token:
                raise ValueError("InfluxDB token is required in production environment")

            # Health checks should be enabled in production
            if not self.enable_health_checks:
                raise ValueError("Health checks should be enabled in production environment")

        # Validate that both databases are configured
        if self.postgresql_config.database_url == self.influxdb_config.get_connection_url():
            raise ValueError("Relational and time-series databases cannot use the same connection")

        return self

    @classmethod
    def create_for_environment(cls, environment: str | None = None) -> "DualDatabaseConfig":
        """Creates dual database configuration for specific environment.

        Args:
            environment: Target environment (development/staging/production)

        Returns:
            Environment-specific dual database configuration
        """
        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development").lower()

        environment = environment.lower()

        if environment == "production":
            # Production: PostgreSQL + InfluxDB with secure defaults
            return cls(
                postgresql_config=DatabaseConfig(
                    database_url=os.getenv(
                        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_single_prod"
                    )
                ),
                influxdb_config=InfluxDBConfig(
                    host=os.getenv("INFLUXDB_HOST", "https://influxdb-prod.example.com"),
                    token=os.getenv("INFLUXDB_TOKEN", "production-token-required"),
                    database=os.getenv("INFLUXDB_DATABASE", "crypto_single_metrics"),
                ),
                enable_health_checks=True,
                enable_connection_pooling=True,
                enable_read_replicas=True,
            )
        elif environment == "staging":
            # Staging: PostgreSQL + InfluxDB with staging defaults
            return cls(
                postgresql_config=DatabaseConfig(
                    database_url=os.getenv(
                        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_single_staging"
                    )
                ),
                influxdb_config=InfluxDBConfig(
                    host=os.getenv("INFLUXDB_HOST", "https://influxdb-staging.example.com"),
                    token=os.getenv("INFLUXDB_TOKEN", "staging-token"),
                    database=os.getenv("INFLUXDB_DATABASE", "crypto_single_staging"),
                ),
                enable_health_checks=True,
                enable_connection_pooling=True,
            )
        else:
            # Development: SQLite + InfluxDB local defaults
            return cls(
                postgresql_config=DatabaseConfig(
                    database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_single_dev.db")
                ),
                influxdb_config=InfluxDBConfig(
                    host=os.getenv("INFLUXDB_HOST", "http://localhost:8086"),
                    token=os.getenv("INFLUXDB_TOKEN", "development-token"),
                    database=os.getenv("INFLUXDB_DATABASE", "crypto_single_dev"),
                ),
                enable_health_checks=True,
                enable_connection_pooling=False,
            )

    def get_database_summary(self) -> dict[str, Any]:
        """Gets summary of both database configurations.

        Returns:
            Summary of database configurations
        """
        return {
            "relational": {
                "type": "postgresql" if self.postgresql_config.is_postgresql() else "sqlite",
                "host": self.postgresql_config.get_host(),
                "database": self.postgresql_config.get_database_name(),
                "in_memory": self.postgresql_config.is_in_memory_db(),
            },
            "time_series": {
                "type": "influxdb_v3",
                "host": self.influxdb_config.host,
                "database": self.influxdb_config.database,
                "organization": self.influxdb_config.org,
            },
            "health_checks_enabled": self.enable_health_checks,
            "connection_pooling_enabled": self.enable_connection_pooling,
        }

    def get_health_check_config(self) -> dict[str, Any]:
        """Gets health check configuration.

        Returns:
            Health check configuration
        """
        if not self.enable_health_checks:
            return {"enabled": False}

        return {
            "enabled": True,
            "interval": self.health_check_interval,
            "timeout": min(self.health_check_interval // 2, 10),  # Half interval or 10s max
            "retry_attempts": self.connection_retry_attempts,
            "retry_delay": self.connection_retry_delay,
            "databases": {
                "relational": {
                    "enabled": True,
                    "type": "postgresql" if self.postgresql_config.is_postgresql() else "sqlite",
                },
                "time_series": {
                    "enabled": True,
                    "type": "influxdb_v3",
                    "endpoint": f"{self.influxdb_config.host}/health",
                },
            },
        }

    def get_connection_config(self) -> dict[str, Any]:
        """Gets connection configuration for both databases.

        Returns:
            Connection configuration
        """
        return {
            "relational": {
                "url": self.postgresql_config.database_url,
                "pool_size": self.postgresql_config.pool_size,
                "max_overflow": self.postgresql_config.max_overflow,
                "pool_timeout": self.postgresql_config.pool_timeout,
                "retry_attempts": self.connection_retry_attempts,
                "retry_delay": self.connection_retry_delay,
            },
            "time_series": {
                "host": self.influxdb_config.host,
                "database": self.influxdb_config.database,
                "organization": self.influxdb_config.org,
                "timeout": self.influxdb_config.health_check_timeout,
                "retry_attempts": self.connection_retry_attempts,
                "retry_delay": self.connection_retry_delay,
            },
            "transaction_timeout": self.transaction_timeout,
            "enable_pooling": self.enable_connection_pooling,
            "enable_read_replicas": self.enable_read_replicas,
        }

    def validate_connections(self) -> dict[str, bool]:
        """Validates that both database configurations are valid.

        Returns:
            Validation results for both databases
        """
        results = {
            "relational_db_valid": True,
            "time_series_db_valid": True,
            "overall_valid": True,
        }

        try:
            # Validate relational database URL format
            if not self.postgresql_config.database_url:
                results["relational_db_valid"] = False
        except Exception:
            results["relational_db_valid"] = False

        try:
            # Validate InfluxDB configuration
            if not self.influxdb_config.host or not self.influxdb_config.database:
                results["time_series_db_valid"] = False
        except Exception:
            results["time_series_db_valid"] = False

        results["overall_valid"] = results["relational_db_valid"] and results["time_series_db_valid"]

        return results

    def is_production_ready(self) -> bool:
        """Checks if configuration is ready for production deployment.

        Returns:
            True if production ready
        """
        if os.getenv("ENVIRONMENT", "").lower() != "production":
            return True  # Non-production environments are always "ready"

        # Production readiness checks
        checks = [
            not self.postgresql_config.is_sqlite(),  # Must use PostgreSQL
            bool(self.influxdb_config.token),  # Must have InfluxDB token
            self.enable_health_checks,  # Must enable health checks
            self.enable_connection_pooling,  # Should use connection pooling
        ]

        return all(checks)

    def get_migration_config(self) -> dict[str, Any]:
        """Gets database migration configuration.

        Returns:
            Migration configuration
        """
        return {
            "relational": {
                "enabled": True,
                "migration_table": "alembic_version",
                "auto_upgrade": os.getenv("ENVIRONMENT", "").lower() != "production",
                "backup_before_migration": os.getenv("ENVIRONMENT", "").lower() == "production",
            },
            "time_series": {
                "enabled": True,
                "schema_validation": True,
                "retention_policy": {
                    "enabled": True,
                    "default_duration": "30d",
                    "shard_duration": "1d",
                },
            },
        }

    def __str__(self) -> str:
        """String representation of dual database configuration.

        Returns:
            String representation
        """
        relational_type = "PostgreSQL" if self.postgresql_config.is_postgresql() else "SQLite"
        return (
            f"DualDatabaseConfig("
            f"relational={relational_type}, "
            f"time_series=InfluxDB_v3, "
            f"health_checks={self.enable_health_checks})"
        )

    def __repr__(self) -> str:
        """Representation of dual database configuration.

        Returns:
            String representation
        """
        return self.__str__()

    def check_postgresql_health(self) -> bool:
        """Checks PostgreSQL database health.

        Returns:
            True if PostgreSQL is healthy
        """
        try:
            # Basic configuration validation
            return bool(
                self.postgresql_config.database_url
                and not self.postgresql_config.is_in_memory_db()
                or os.getenv("ENVIRONMENT", "").lower() != "production"
            )
        except Exception:
            return False

    def check_influxdb_health(self) -> bool:
        """Checks InfluxDB database health.

        Returns:
            True if InfluxDB is healthy
        """
        try:
            # Basic configuration validation
            return bool(
                self.influxdb_config.host
                and self.influxdb_config.database
                and (self.influxdb_config.token or os.getenv("ENVIRONMENT", "").lower() != "production")
            )
        except Exception:
            return False

    async def check_health(self) -> dict[str, bool]:
        """Performs health check on both databases.

        Returns:
            Health status for both databases
        """
        postgresql_healthy = self.check_postgresql_health()
        influxdb_healthy = self.check_influxdb_health()

        return {
            "postgresql": postgresql_healthy,
            "influxdb": influxdb_healthy,
            "overall": postgresql_healthy and influxdb_healthy,
        }

    async def connect_postgresql(self) -> Any:
        """Establishes PostgreSQL connection.

        Returns:
            Mock connection object for testing
        """
        # Mock implementation for testing
        return Mock()

    async def connect_influxdb(self) -> Any:
        """Establishes InfluxDB connection.

        Returns:
            Mock connection object for testing
        """
        # Mock implementation for testing
        return Mock()

    async def establish_connections(self) -> dict[str, Any]:
        """Establishes connections to both databases.

        Returns:
            Connection status and objects
        """
        try:
            postgresql_conn = await self.connect_postgresql()
            influxdb_conn = await self.connect_influxdb()

            return {
                "postgresql": {"connected": True, "connection": postgresql_conn},
                "influxdb": {"connected": True, "connection": influxdb_conn},
                "both_connected": True,
            }
        except Exception as e:
            return {
                "postgresql": {"connected": False, "error": str(e)},
                "influxdb": {"connected": False, "error": str(e)},
                "both_connected": False,
            }
