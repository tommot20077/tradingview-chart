"""
A2.8: 雙資料庫整合配置測試

測試 PostgreSQL（元數據）+ InfluxDB v3（時序資料）雙資料庫配置整合。
這些測試定義了雙資料庫配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestDualDatabaseConfiguration:
    """測試雙資料庫配置整合功能"""

    def test_postgresql_influxdb_dual_connection_configuration(self) -> None:
        """測試 PostgreSQL + InfluxDB v3 雙連接配置"""
        # TDD: 定義配置類必須同時支援兩種資料庫連接

        with pytest.MonkeyPatch().context() as mp:
            # PostgreSQL 配置
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_metadata")
            mp.setenv("DATABASE_POOL_SIZE", "10")

            # InfluxDB v3 配置
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "influxdb-token-12345")
            mp.setenv("INFLUXDB_DATABASE", "crypto_timeseries")
            mp.setenv("INFLUXDB_ORG", "crypto-org")

            settings = SingleCryptoSettings()

            # 驗證雙資料庫配置都存在
            assert hasattr(settings, "database_url")  # PostgreSQL
            assert hasattr(settings, "influxdb_host")  # InfluxDB

            # 驗證 PostgreSQL 配置
            assert "postgresql" in settings.database_url.lower()
            assert settings.database_pool_size == 10

            # 驗證 InfluxDB 配置
            assert settings.influxdb_host == "https://influxdb.example.com"
            assert settings.influxdb_database == "crypto_timeseries"

    def test_database_health_check_integration(self) -> None:
        """測試資料庫健康檢查整合"""
        # TDD: 定義配置類必須提供雙資料庫健康檢查設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 健康檢查配置
            mp.setenv("DATABASE_HEALTH_CHECK_INTERVAL", "30")
            mp.setenv("INFLUXDB_HEALTH_CHECK_INTERVAL", "60")
            mp.setenv("HEALTH_CHECK_TIMEOUT", "10")

            settings = SingleCryptoSettings()

            # 驗證健康檢查配置
            assert hasattr(settings, "database_health_check_interval")
            assert hasattr(settings, "influxdb_health_check_interval")
            assert hasattr(settings, "health_check_timeout")

            assert settings.database_health_check_interval == 30
            assert settings.influxdb_health_check_interval == 60
            assert settings.health_check_timeout == 10

    def test_database_connection_failure_handling(self) -> None:
        """測試資料庫連接失效時的錯誤處理配置"""
        # TDD: 定義配置類必須支援連接失效處理設定

        with pytest.MonkeyPatch().context() as mp:
            # 基礎配置
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 失效處理配置
            mp.setenv("DATABASE_RETRY_ATTEMPTS", "3")
            mp.setenv("DATABASE_RETRY_DELAY", "5")
            mp.setenv("INFLUXDB_RETRY_ATTEMPTS", "5")
            mp.setenv("INFLUXDB_RETRY_DELAY", "3")
            mp.setenv("DATABASE_CIRCUIT_BREAKER_ENABLED", "true")

            settings = SingleCryptoSettings()

            # 驗證失效處理配置
            assert hasattr(settings, "database_retry_attempts")
            assert hasattr(settings, "database_retry_delay")
            assert hasattr(settings, "influxdb_retry_attempts")
            assert hasattr(settings, "influxdb_retry_delay")
            assert hasattr(settings, "database_circuit_breaker_enabled")

            assert settings.database_retry_attempts == 3
            assert settings.database_retry_delay == 5
            assert settings.influxdb_retry_attempts == 5
            assert settings.influxdb_retry_delay == 3
            assert settings.database_circuit_breaker_enabled is True

    def test_environment_specific_database_selection(self) -> None:
        """測試不同環境的資料庫選擇"""
        # TDD: 定義不同環境必須選擇適當的資料庫組合

        # 開發環境：SQLite + 本地 InfluxDB
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")

            settings = SingleCryptoSettings()

            # 開發環境應該使用本地資料庫
            assert "sqlite" in settings.database_url.lower()
            assert "localhost" in settings.influxdb_host.lower() or "test" in settings.influxdb_host.lower()

        # 生產環境：PostgreSQL + 生產 InfluxDB
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@prod-pg:5432/crypto_prod")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.production.com")
            mp.setenv("INFLUXDB_TOKEN", "prod-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_production")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            mp.setenv("SECRET_KEY", "a" * 32)  # Valid production secret key
            mp.setenv("CORS_ALLOW_ORIGINS", "https://example.com")  # Valid CORS origins

            settings = SingleCryptoSettings()

            # 生產環境應該使用生產資料庫
            assert "postgresql" in settings.database_url.lower()
            assert "production" in settings.influxdb_host.lower()

    def test_database_configuration_validation_dependency(self) -> None:
        """測試資料庫配置驗證依賴關係"""
        # TDD: 定義資料庫配置必須有正確的依賴驗證

        # 只有 PostgreSQL 沒有 InfluxDB 應該失敗（在需要時序資料時）
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("ENABLE_TIMESERIES_DATA", "true")  # 啟用時序資料
            # 不設置 InfluxDB 配置

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "influxdb" in error_str or "timeseries" in error_str

        # 只有 InfluxDB 沒有元資料庫應該失敗
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")
            # 不設置 DATABASE_URL

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "database" in error_str or "metadata" in error_str

    def test_database_connection_pool_coordination(self) -> None:
        """測試資料庫連接池協調配置"""
        # TDD: 定義配置類必須協調雙資料庫的連接池設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 連接池配置
            mp.setenv("DATABASE_POOL_SIZE", "20")
            mp.setenv("DATABASE_MAX_OVERFLOW", "10")
            mp.setenv("INFLUXDB_CONNECTION_POOL_SIZE", "15")
            mp.setenv("INFLUXDB_MAX_CONNECTIONS", "25")

            settings = SingleCryptoSettings()

            # 驗證連接池配置
            assert settings.database_pool_size == 20
            assert settings.database_max_overflow == 10
            assert hasattr(settings, "influxdb_connection_pool_size")
            assert hasattr(settings, "influxdb_max_connections")

            assert settings.influxdb_connection_pool_size == 15
            assert settings.influxdb_max_connections == 25

    def test_database_transaction_coordination_configuration(self) -> None:
        """測試資料庫事務協調配置"""
        # TDD: 定義配置類必須支援跨資料庫事務協調設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 事務協調配置
            mp.setenv("ENABLE_CROSS_DATABASE_TRANSACTIONS", "false")  # 一般不支援
            mp.setenv("DATABASE_ISOLATION_LEVEL", "READ_COMMITTED")
            mp.setenv("INFLUXDB_WRITE_CONSISTENCY", "one")

            settings = SingleCryptoSettings()

            # 驗證事務協調配置
            assert hasattr(settings, "enable_cross_database_transactions")
            assert hasattr(settings, "database_isolation_level")
            assert hasattr(settings, "influxdb_write_consistency")

            assert settings.enable_cross_database_transactions is False
            assert settings.database_isolation_level == "READ_COMMITTED"
            assert settings.influxdb_write_consistency == "one"

    def test_database_backup_configuration(self) -> None:
        """測試資料庫備份配置"""
        # TDD: 定義配置類必須支援雙資料庫備份設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 備份配置
            mp.setenv("DATABASE_BACKUP_ENABLED", "true")
            mp.setenv("DATABASE_BACKUP_INTERVAL", "86400")  # 每日
            mp.setenv("INFLUXDB_BACKUP_ENABLED", "true")
            mp.setenv("INFLUXDB_BACKUP_RETENTION", "30")  # 30天

            settings = SingleCryptoSettings()

            # 驗證備份配置
            assert hasattr(settings, "database_backup_enabled")
            assert hasattr(settings, "database_backup_interval")
            assert hasattr(settings, "influxdb_backup_enabled")
            assert hasattr(settings, "influxdb_backup_retention")

            assert settings.database_backup_enabled is True
            assert settings.database_backup_interval == 86400
            assert settings.influxdb_backup_enabled is True
            assert settings.influxdb_backup_retention == 30

    def test_database_monitoring_configuration(self) -> None:
        """測試資料庫監控配置"""
        # TDD: 定義配置類必須支援雙資料庫監控設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 監控配置
            mp.setenv("DATABASE_METRICS_ENABLED", "true")
            mp.setenv("DATABASE_SLOW_QUERY_THRESHOLD", "1000")  # 1秒
            mp.setenv("INFLUXDB_METRICS_ENABLED", "true")
            mp.setenv("INFLUXDB_QUERY_TIMEOUT", "30")

            settings = SingleCryptoSettings()

            # 驗證監控配置
            assert hasattr(settings, "database_metrics_enabled")
            assert hasattr(settings, "database_slow_query_threshold")
            assert hasattr(settings, "influxdb_metrics_enabled")
            assert hasattr(settings, "influxdb_query_timeout")

            assert settings.database_metrics_enabled is True
            assert settings.database_slow_query_threshold == 1000
            assert settings.influxdb_metrics_enabled is True
            assert settings.influxdb_query_timeout == 30

    def test_database_configuration_provides_helper_methods(self) -> None:
        """測試資料庫配置提供輔助方法"""
        # TDD: 定義配置類必須提供雙資料庫相關的輔助方法

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            settings = SingleCryptoSettings()

            # 應該提供獲取資料庫配置的方法
            assert hasattr(settings, "get_metadata_db_config")
            assert hasattr(settings, "get_timeseries_db_config")
            assert hasattr(settings, "get_all_database_configs")

            metadata_config = settings.get_metadata_db_config()
            timeseries_config = settings.get_timeseries_db_config()
            all_configs = settings.get_all_database_configs()

            # 驗證返回的配置結構
            assert isinstance(metadata_config, dict)
            assert isinstance(timeseries_config, dict)
            assert isinstance(all_configs, dict)

            assert "url" in metadata_config
            assert "host" in timeseries_config
            assert "metadata" in all_configs
            assert "timeseries" in all_configs

    def test_database_failover_configuration(self) -> None:
        """測試資料庫故障轉移配置"""
        # TDD: 定義配置類必須支援故障轉移設定

        with pytest.MonkeyPatch().context() as mp:
            # 主資料庫配置
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@primary-db:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "https://primary-influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            # 故障轉移配置
            mp.setenv("DATABASE_FALLBACK_URL", "postgresql+asyncpg://user:pass@backup-db:5432/crypto_db")
            mp.setenv("INFLUXDB_FALLBACK_HOST", "https://backup-influxdb.example.com")
            mp.setenv("DATABASE_FAILOVER_ENABLED", "true")
            mp.setenv("DATABASE_FAILOVER_TIMEOUT", "30")

            settings = SingleCryptoSettings()

            # 驗證故障轉移配置
            assert hasattr(settings, "database_fallback_url")
            assert hasattr(settings, "influxdb_fallback_host")
            assert hasattr(settings, "database_failover_enabled")
            assert hasattr(settings, "database_failover_timeout")

            assert settings.database_fallback_url and "backup-db" in settings.database_fallback_url
            assert settings.influxdb_fallback_host and "backup-influxdb" in settings.influxdb_fallback_host
            assert settings.database_failover_enabled is True
            assert settings.database_failover_timeout == 30

    def test_database_configuration_validation_errors(self) -> None:
        """測試資料庫配置驗證錯誤"""
        # TDD: 定義配置類必須提供清晰的雙資料庫驗證錯誤訊息

        # 測試 PostgreSQL 配置錯誤
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "invalid-database-url")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "database" in error_str and ("url" in error_str or "postgresql" in error_str)

        # 測試 InfluxDB 配置錯誤
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/crypto_db")
            mp.setenv("INFLUXDB_HOST", "invalid-influxdb-host")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_ts")
            mp.setenv("INFLUXDB_ORG", "test-org")

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "influxdb" in error_str and "host" in error_str
