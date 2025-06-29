"""
A2.7: 環境特定配置整合測試

測試開發、暫存、生產環境的配置載入、驗證和切換機制。
這些測試定義了環境特定配置的預期行為，實現時必須滿足這些測試。
"""

import os
import tempfile

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestEnvironmentSpecificConfiguration:
    """測試環境特定配置整合功能"""

    def test_development_environment_configuration_loading(self):
        """測試開發環境配置載入"""
        # TDD: 定義開發環境必須載入適當的預設配置
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            
            settings = SingleCryptoSettings()
            
            # 驗證開發環境特定配置
            assert settings.environment == "development"
            assert settings.is_development() is True
            assert settings.is_production() is False
            
            # 開發環境應該有寬鬆的設定
            assert settings.debug is True  # 開發環境預設啟用 debug
            assert "sqlite" in settings.database_url.lower()  # 預設使用 SQLite
            assert settings.api_docs_enabled is True  # 開發環境啟用 API 文檔
            assert settings.redis_enabled is False  # 開發環境預設使用記憶體快取

    def test_staging_environment_configuration_loading(self):
        """測試暫存環境配置載入"""
        # TDD: 定義暫存環境必須載入生產類似但較寬鬆的配置
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "staging")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@staging-db:5432/crypto_staging")
            mp.setenv("SECRET_KEY", "staging-secret-key-with-sufficient-length")
            
            settings = SingleCryptoSettings()
            
            # 驗證暫存環境特定配置
            assert settings.environment == "staging"
            assert settings.is_development() is False
            assert settings.is_production() is False
            
            # 暫存環境應該介於開發和生產之間
            assert settings.debug is False  # 暫存環境關閉 debug
            assert "postgresql" in settings.database_url.lower()  # 使用 PostgreSQL
            assert settings.api_docs_enabled is True  # 暫存環境可啟用文檔

    def test_production_environment_configuration_loading(self):
        """測試生產環境配置載入"""
        # TDD: 定義生產環境必須載入最嚴格的安全配置
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@prod-db:5432/crypto_production")
            mp.setenv("SECRET_KEY", "production-super-secret-key-with-high-entropy-12345")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.production.com")
            mp.setenv("INFLUXDB_TOKEN", "production-influxdb-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_production")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            settings = SingleCryptoSettings()
            
            # 驗證生產環境特定配置
            assert settings.environment == "production"
            assert settings.is_development() is False
            assert settings.is_production() is True
            
            # 生產環境應該有最嚴格的設定
            assert settings.debug is False  # 生產環境必須關閉 debug
            assert settings.api_reload is False  # 生產環境關閉 reload
            assert "postgresql" in settings.database_url.lower()  # 必須使用 PostgreSQL
            assert settings.api_docs_enabled is False  # 生產環境預設關閉文檔

    def test_environment_configuration_switching(self):
        """測試環境配置切換"""
        # TDD: 定義環境切換必須正確載入不同的配置值
        
        # 測試從開發環境切換到生產環境
        base_env_vars = {
            "SECRET_KEY": "test-secret-key-with-sufficient-length",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test_db",
            "INFLUXDB_HOST": "https://influxdb.test.com",
            "INFLUXDB_TOKEN": "test-token",
            "INFLUXDB_DATABASE": "test_db",
            "INFLUXDB_ORG": "test-org"
        }
        
        # 開發環境配置
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            for key, value in base_env_vars.items():
                mp.setenv(key, value)
            
            dev_settings = SingleCryptoSettings()
            assert dev_settings.debug is True
            assert dev_settings.api_docs_enabled is True

        # 生產環境配置
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            for key, value in base_env_vars.items():
                mp.setenv(key, value)
            
            prod_settings = SingleCryptoSettings()
            assert prod_settings.debug is False
            assert prod_settings.api_docs_enabled is False
            
            # 相同的基礎配置應該保持一致
            assert prod_settings.secret_key == dev_settings.secret_key
            assert prod_settings.database_url == dev_settings.database_url

    def test_sensitive_information_handling_across_environments(self):
        """測試敏感資訊在不同環境的處理"""
        # TDD: 定義敏感資訊必須在不同環境中得到適當保護
        
        sensitive_data = {
            "SECRET_KEY": "super-secret-production-key",
            "BINANCE_SECRET_KEY": "binance-secret-key",
            "REDIS_PASSWORD": "redis-password",
            "INFLUXDB_TOKEN": "influxdb-token"
        }
        
        for env in ["development", "staging", "production"]:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", env)
                # 設置必要的非敏感配置
                if env == "production":
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                    mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
                    mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
                    mp.setenv("INFLUXDB_ORG", "crypto-org")
                
                for key, value in sensitive_data.items():
                    mp.setenv(key, value)
                
                settings = SingleCryptoSettings()
                
                # 序列化時敏感資訊應該被保護
                serialized = settings.model_dump()
                
                # 檢查敏感資訊是否被正確處理
                serialized_str = str(serialized)
                for sensitive_value in sensitive_data.values():
                    # 敏感資訊不應該直接出現在序列化結果中
                    # 或者應該被遮蔽處理
                    if sensitive_value in serialized_str:
                        # 如果出現，應該是被遮蔽的形式
                        assert "****" in serialized_str or "[HIDDEN]" in serialized_str

    def test_environment_variable_priority_order(self):
        """測試環境變數優先順序"""
        # TDD: 定義環境變數的載入優先順序
        
        # 創建臨時 .env 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("APP_NAME=env-file-name\n")
            f.write("DEBUG=false\n")
            env_file_path = f.name
        
        try:
            with pytest.MonkeyPatch().context() as mp:
                # 環境變數應該優先於 .env 檔案
                mp.setenv("APP_NAME", "environment-variable-name")
                # DEBUG 只在 .env 檔案中設置
                
                settings = SingleCryptoSettings(_env_file=env_file_path)
                
                # 環境變數應該優先
                assert settings.app_name == "environment-variable-name"
                # .env 檔案的值應該被使用（如果環境變數中沒有）
                assert settings.debug is False
        finally:
            os.unlink(env_file_path)

    def test_required_configuration_validation_per_environment(self):
        """測試各環境必要配置驗證"""
        # TDD: 定義各環境必須有的必要配置驗證
        
        # 生產環境缺少必要配置應該失敗
        missing_configs = [
            ("DATABASE_URL", "生產環境必須指定資料庫"),
            ("SECRET_KEY", "生產環境必須有強密鑰"),
            ("INFLUXDB_HOST", "生產環境必須配置 InfluxDB"),
        ]
        
        for missing_config, description in missing_configs:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", "production")
                
                # 設置除了缺失配置外的其他必要配置
                if missing_config != "DATABASE_URL":
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                if missing_config != "SECRET_KEY":
                    mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length")
                if missing_config != "INFLUXDB_HOST":
                    mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
                    mp.setenv("INFLUXDB_TOKEN", "prod-token")
                    mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
                    mp.setenv("INFLUXDB_ORG", "crypto-org")
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "production" in error_str, f"錯誤訊息應該提及生產環境: {description}"

    def test_development_environment_defaults(self):
        """測試開發環境預設值"""
        # TDD: 定義開發環境必須提供合理的預設值
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            
            settings = SingleCryptoSettings()
            
            # 開發環境應該有方便開發的預設值
            assert settings.debug is True
            assert settings.api_reload is True
            assert settings.api_docs_enabled is True
            assert settings.cors_enabled is True
            assert "localhost" in settings.influxdb_host.lower() or "test" in settings.influxdb_host.lower()
            assert settings.redis_enabled is False  # 預設使用記憶體快取

    def test_configuration_inheritance_and_override(self):
        """測試配置繼承和覆蓋機制"""
        # TDD: 定義配置必須支援繼承和覆蓋機制
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", "production-secret-key")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
            mp.setenv("INFLUXDB_TOKEN", "prod-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            # 明確覆蓋生產環境預設值
            mp.setenv("API_DEBUG", "false")  # 明確設置
            mp.setenv("API_DOCS_ENABLED", "true")  # 覆蓋生產環境預設
            mp.setenv("API_DOCS_PRODUCTION_OVERRIDE", "true")  # 明確允許
            
            settings = SingleCryptoSettings()
            
            # 覆蓋值應該生效
            assert settings.api_debug is False
            assert settings.api_docs_enabled is True

    def test_environment_specific_validation_rules(self):
        """測試環境特定驗證規則"""
        # TDD: 定義不同環境必須有不同的驗證規則
        
        weak_secret = "weak"
        strong_secret = "strong-secret-key-with-sufficient-entropy-for-production"
        
        # 開發環境可以接受較弱的密鑰
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            mp.setenv("SECRET_KEY", weak_secret)
            
            # 開發環境應該可以接受較弱的配置
            settings = SingleCryptoSettings()
            assert settings.secret_key == weak_secret

        # 生產環境必須要求強密鑰
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", weak_secret)
            mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
            mp.setenv("INFLUXDB_TOKEN", "prod-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            with pytest.raises(ValidationError):
                SingleCryptoSettings()

        # 生產環境應該接受強密鑰
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", strong_secret)
            mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
            mp.setenv("INFLUXDB_TOKEN", "prod-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            settings = SingleCryptoSettings()
            assert settings.secret_key == strong_secret

    def test_configuration_provides_environment_helper_methods(self):
        """測試配置提供環境輔助方法"""
        # TDD: 定義配置類必須提供環境相關的輔助方法
        
        for env in ["development", "staging", "production"]:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", env)
                if env == "production":
                    # 提供生產環境必要配置
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                    mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length")
                    mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
                    mp.setenv("INFLUXDB_TOKEN", "prod-token")
                    mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
                    mp.setenv("INFLUXDB_ORG", "crypto-org")
                
                settings = SingleCryptoSettings()
                
                # 應該提供環境檢查方法
                assert hasattr(settings, 'get_environment_config')
                
                env_config = settings.get_environment_config()
                assert isinstance(env_config, dict)
                assert env_config['environment'] == env
                assert 'debug' in env_config
                assert 'api_docs_enabled' in env_config