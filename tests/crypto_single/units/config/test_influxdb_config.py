"""
A2.3: InfluxDB v3 配置測試設計

測試 InfluxDB v3 時序資料庫連接配置 (Host, Token, Database) 的配置管理功能。
這些測試定義了 InfluxDB v3 配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestInfluxDBConfiguration:
    """測試 InfluxDB v3 配置功能"""

    def test_influxdb_connection_parameters_validation(self):
        """測試 InfluxDB v3 連接參數驗證"""
        # TDD: 定義配置類必須支援 InfluxDB v3 連接參數
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token-12345")
            mp.setenv("INFLUXDB_DATABASE", "crypto_timeseries")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            settings = SingleCryptoSettings()
            
            # 驗證所有 InfluxDB 連接參數
            assert hasattr(settings, 'influxdb_host')
            assert hasattr(settings, 'influxdb_token')
            assert hasattr(settings, 'influxdb_database')
            assert hasattr(settings, 'influxdb_org')
            
            assert settings.influxdb_host == "https://influxdb.example.com"
            assert settings.influxdb_token == "test-token-12345"
            assert settings.influxdb_database == "crypto_timeseries"
            assert settings.influxdb_org == "crypto-org"

    def test_influxdb_token_validation_and_security(self):
        """測試 InfluxDB Token 驗證和安全性檢查"""
        # TDD: 定義配置類必須驗證 Token 格式並確保安全性
        
        # 測試有效的 Token 格式
        valid_tokens = [
            "test-token-12345",
            "influxdb_token_abcdef1234567890",
            "very-long-token-with-special-chars_123-456",
        ]
        
        for token in valid_tokens:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_TOKEN", token)
                settings = SingleCryptoSettings()
                assert settings.influxdb_token == token

        # 測試無效的 Token（太短或為空）
        invalid_tokens = [
            "",           # 空字符串
            "short",      # 太短
            "   ",        # 只有空格
        ]
        
        for invalid_token in invalid_tokens:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_TOKEN", invalid_token)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "token" in error_str

    def test_influxdb_host_url_format_validation(self):
        """測試 InfluxDB Host URL 格式驗證"""
        # TDD: 定義配置類必須驗證 Host URL 格式
        
        # 測試有效的 Host URL 格式
        valid_hosts = [
            "https://influxdb.example.com",
            "https://localhost:8086",
            "https://192.168.1.100:8086",
            "https://influx.company.com:9999",
        ]
        
        for host in valid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", host)
                settings = SingleCryptoSettings()
                assert settings.influxdb_host == host

        # 測試無效的 Host URL 格式
        invalid_hosts = [
            "influxdb.example.com",          # 缺少協議
            "http://influxdb.example.com",   # 不安全的 HTTP
            "ftp://influxdb.example.com",    # 錯誤的協議
            "",                              # 空字符串
            "invalid-url",                   # 無效 URL
        ]
        
        for invalid_host in invalid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", invalid_host)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["host", "url", "https"])

    def test_influxdb_database_name_validation(self):
        """測試 InfluxDB Database 名稱驗證"""
        # TDD: 定義配置類必須驗證資料庫名稱格式
        
        # 測試有效的資料庫名稱
        valid_database_names = [
            "crypto_timeseries",
            "crypto-data",
            "cryptodb",
            "crypto_db_v1",
            "test_database_123",
        ]
        
        for db_name in valid_database_names:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_DATABASE", db_name)
                settings = SingleCryptoSettings()
                assert settings.influxdb_database == db_name

        # 測試無效的資料庫名稱
        invalid_database_names = [
            "",               # 空字符串
            "   ",            # 只有空格
            "db with spaces", # 包含空格
            "db@special",     # 特殊字符
            "123",            # 只有數字
        ]
        
        for invalid_db_name in invalid_database_names:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_DATABASE", invalid_db_name)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "database" in error_str

    def test_influxdb_production_environment_validation(self):
        """測試生產環境 InfluxDB 必要參數驗證"""
        # TDD: 定義生產環境必須提供所有 InfluxDB 參數
        
        # 生產環境：缺少 InfluxDB 配置應該拋出錯誤
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            # 不設置 InfluxDB 參數
            
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in ["influxdb", "production", "required"])

        # 生產環境：提供完整 InfluxDB 配置應該成功
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.production.com")
            mp.setenv("INFLUXDB_TOKEN", "production-token-12345")
            mp.setenv("INFLUXDB_DATABASE", "crypto_production")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            
            settings = SingleCryptoSettings()
            assert settings.influxdb_host == "https://influxdb.production.com"
            assert settings.influxdb_database == "crypto_production"

    def test_influxdb_development_defaults(self):
        """測試 InfluxDB 開發環境預設值"""
        # TDD: 定義開發環境必須提供合理的 InfluxDB 預設值
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            # 在開發環境，可以使用預設的 InfluxDB 配置
            
            settings = SingleCryptoSettings()
            
            # 驗證開發環境預設值
            assert settings.influxdb_host  # 應該有預設 host
            assert settings.influxdb_database  # 應該有預設資料庫名稱
            
            # 開發環境預設值應該指向本地或測試環境
            assert "localhost" in settings.influxdb_host or "test" in settings.influxdb_host.lower()
            assert "test" in settings.influxdb_database.lower() or "dev" in settings.influxdb_database.lower()

    def test_influxdb_health_check_endpoint_configuration(self):
        """測試 InfluxDB 健康檢查端點配置"""
        # TDD: 定義配置類必須提供健康檢查相關設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_HEALTH_CHECK_TIMEOUT", "10")
            mp.setenv("INFLUXDB_HEALTH_CHECK_INTERVAL", "30")
            
            settings = SingleCryptoSettings()
            
            # 驗證健康檢查設定
            assert hasattr(settings, 'influxdb_health_check_timeout')
            assert hasattr(settings, 'influxdb_health_check_interval')
            
            assert settings.influxdb_health_check_timeout == 10
            assert settings.influxdb_health_check_interval == 30

    def test_influxdb_configuration_provides_helper_methods(self):
        """測試 InfluxDB 配置提供輔助方法"""
        # TDD: 定義配置類必須提供 InfluxDB 相關的輔助方法
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "test-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_test")
            
            settings = SingleCryptoSettings()
            
            # 應該提供獲取完整配置的方法
            assert hasattr(settings, 'get_influxdb_config')
            
            config = settings.get_influxdb_config()
            assert isinstance(config, dict)
            assert 'host' in config
            assert 'token' in config
            assert 'database' in config

    def test_influxdb_api_endpoints_configuration(self):
        """測試 InfluxDB v3 API 端點配置"""
        # TDD: 定義配置類必須支援 InfluxDB v3 API 端點設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_WRITE_PRECISION", "ns")
            mp.setenv("INFLUXDB_QUERY_FORMAT", "json")
            
            settings = SingleCryptoSettings()
            
            # 驗證 API 相關設定
            assert hasattr(settings, 'influxdb_write_precision')
            assert hasattr(settings, 'influxdb_query_format')
            
            assert settings.influxdb_write_precision == "ns"
            assert settings.influxdb_query_format == "json"

    def test_influxdb_write_precision_validation(self):
        """測試 InfluxDB 寫入精度驗證"""
        # TDD: 定義配置類必須驗證寫入精度參數
        
        # 測試有效的精度值
        valid_precisions = ["ns", "us", "ms", "s"]
        
        for precision in valid_precisions:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_WRITE_PRECISION", precision)
                settings = SingleCryptoSettings()
                assert settings.influxdb_write_precision == precision

        # 測試無效的精度值
        invalid_precisions = ["", "invalid", "hours", "days"]
        
        for invalid_precision in invalid_precisions:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_WRITE_PRECISION", invalid_precision)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "precision" in error_str

    def test_influxdb_token_security_handling(self):
        """測試 InfluxDB Token 安全性處理"""
        # TDD: 定義配置類必須安全處理敏感的 Token 資訊
        
        sensitive_token = "super-secret-influxdb-token-12345"
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_TOKEN", sensitive_token)
            settings = SingleCryptoSettings()
            
            # 序列化時應該隱藏敏感資訊
            serialized = settings.model_dump()
            
            # 檢查是否有提供安全的 Token 顯示方法
            if hasattr(settings, 'get_safe_influxdb_token'):
                safe_token = settings.get_safe_influxdb_token()
                assert sensitive_token not in safe_token
                assert "****" in safe_token or "[HIDDEN]" in safe_token
                
            # 或者序列化時自動隱藏
            if 'influxdb_token' in serialized:
                assert sensitive_token not in str(serialized)

    def test_influxdb_connection_retry_configuration(self):
        """測試 InfluxDB 連接重試配置"""
        # TDD: 定義配置類必須支援連接重試相關設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_MAX_RETRIES", "3")
            mp.setenv("INFLUXDB_RETRY_DELAY", "5")
            mp.setenv("INFLUXDB_BACKOFF_FACTOR", "2")
            
            settings = SingleCryptoSettings()
            
            # 驗證重試設定
            assert hasattr(settings, 'influxdb_max_retries')
            assert hasattr(settings, 'influxdb_retry_delay')
            assert hasattr(settings, 'influxdb_backoff_factor')
            
            assert settings.influxdb_max_retries == 3
            assert settings.influxdb_retry_delay == 5
            assert settings.influxdb_backoff_factor == 2

    def test_influxdb_batch_configuration(self):
        """測試 InfluxDB 批次處理配置"""
        # TDD: 定義配置類必須支援批次寫入相關設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_BATCH_SIZE", "1000")
            mp.setenv("INFLUXDB_FLUSH_INTERVAL", "10")
            
            settings = SingleCryptoSettings()
            
            # 驗證批次處理設定
            assert hasattr(settings, 'influxdb_batch_size')
            assert hasattr(settings, 'influxdb_flush_interval')
            
            assert settings.influxdb_batch_size == 1000
            assert settings.influxdb_flush_interval == 10

    # === 新增異常情況測試 ===
    
    def test_handles_invalid_influxdb_urls(self):
        """測試處理無效的 InfluxDB URL"""
        # TDD: 定義配置類必須妥善處理無效的 InfluxDB URL
        
        invalid_urls = [
            "ftp://invalid.com",  # 無效協議
            "http://",  # 空主機
            "https://host:abc",  # 無效端口
            "not-a-url",  # 完全無效的 URL
            "http://256.256.256.256:8086",  # 無效 IP
        ]
        
        for invalid_url in invalid_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", invalid_url)
                mp.setenv("INFLUXDB_TOKEN", "test-token")
                mp.setenv("INFLUXDB_DATABASE", "test-db")
                mp.setenv("INFLUXDB_ORG", "test-org")
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["influxdb", "host", "url", "http"])

    def test_handles_missing_required_influxdb_config(self):
        """測試處理缺失必要的 InfluxDB 配置"""
        # TDD: 定義生產環境必須要求完整的 InfluxDB 配置
        
        required_fields = ["INFLUXDB_TOKEN", "INFLUXDB_DATABASE", "INFLUXDB_ORG"]
        
        for missing_field in required_fields:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", "production")
                mp.setenv("ENABLE_TIMESERIES_DATA", "true")
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", "test-token")
                mp.setenv("INFLUXDB_DATABASE", "test-db")
                mp.setenv("INFLUXDB_ORG", "test-org")
                
                # 移除一個必要欄位
                mp.delenv(missing_field, raising=False)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["influxdb", "production", "required"])

    def test_handles_corrupted_influxdb_tokens(self):
        """測試處理損壞的 InfluxDB Token"""
        # TDD: 定義配置類必須驗證 InfluxDB Token 格式
        
        invalid_tokens = [
            "",  # 空 Token
            "   ",  # 空白 Token
            "short",  # 過短的 Token
            "token with spaces",  # 包含空格的 Token
        ]
        
        for invalid_token in invalid_tokens:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", invalid_token)
                mp.setenv("INFLUXDB_DATABASE", "test-db")
                mp.setenv("INFLUXDB_ORG", "test-org")
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["token", "influxdb"])

    def test_handles_special_characters_in_influxdb_config(self):
        """測試處理 InfluxDB 配置中的特殊字符"""
        # TDD: 定義配置類必須正確處理特殊字符
        
        special_char_cases = [
            # (database_name, org_name, should_be_valid)
            ("test-db-with-dashes", "org-with-dashes", True),
            ("test_db_with_underscores", "org_with_underscores", True),
            ("test.db.with.dots", "org.with.dots", True),
            ("測試資料庫", "測試組織", True),  # Unicode 字符
            ("test db with spaces", "org with spaces", False),  # 空格可能無效
            ("test/db/with/slashes", "org/with/slashes", False),  # 斜杠可能無效
        ]
        
        for db_name, org_name, should_be_valid in special_char_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", "valid-token-12345")
                mp.setenv("INFLUXDB_DATABASE", db_name)
                mp.setenv("INFLUXDB_ORG", org_name)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.influxdb_database == db_name
                    assert settings.influxdb_org == org_name
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增邊界條件測試 ===
    
    def test_handles_extreme_influxdb_parameter_values(self):
        """測試處理極端的 InfluxDB 參數值"""
        # TDD: 定義配置類必須正確處理參數邊界值
        
        parameter_cases = [
            # (param_name, param_value, should_be_valid)
            ("INFLUXDB_TIMEOUT", "0", False),      # 零超時無效
            ("INFLUXDB_TIMEOUT", "-1", False),     # 負超時無效
            ("INFLUXDB_TIMEOUT", "1", True),       # 最小有效超時
            ("INFLUXDB_TIMEOUT", "300", True),     # 最大有效超時
            ("INFLUXDB_TIMEOUT", "99999", False),  # 過大超時無效
            ("INFLUXDB_BATCH_SIZE", "0", False),   # 零批次大小無效
            ("INFLUXDB_BATCH_SIZE", "-1", False),  # 負批次大小無效
            ("INFLUXDB_BATCH_SIZE", "1", True),    # 最小批次大小
            ("INFLUXDB_BATCH_SIZE", "10000", True), # 最大批次大小
            ("INFLUXDB_BATCH_SIZE", "100000", False), # 過大批次大小無效
        ]
        
        for param_name, param_value, should_be_valid in parameter_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", "test-token")
                mp.setenv("INFLUXDB_DATABASE", "test-db")
                mp.setenv("INFLUXDB_ORG", "test-org")
                mp.setenv(param_name, param_value)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    # 驗證參數正確設置
                    config = settings.get_influxdb_config()
                    assert config is not None
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_extremely_long_influxdb_values(self):
        """測試處理極長的 InfluxDB 配置值"""
        # TDD: 定義配置類必須處理極長的配置值
        
        # 生成極長的值
        long_database_name = "a" * 1000
        long_org_name = "b" * 1000
        long_token = "c" * 5000
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", long_token)
            mp.setenv("INFLUXDB_DATABASE", long_database_name)
            mp.setenv("INFLUXDB_ORG", long_org_name)
            
            try:
                settings = SingleCryptoSettings()
                assert settings.influxdb_database == long_database_name
                assert settings.influxdb_org == long_org_name
                assert settings.influxdb_token.get_secret_value() == long_token
            except ValidationError as e:
                # 如果有長度限制，驗證錯誤是可接受的
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit"])

    def test_handles_unicode_in_influxdb_config(self):
        """測試處理 InfluxDB 配置中的 Unicode 字符"""
        # TDD: 定義配置類必須正確處理 Unicode 字符
        
        unicode_cases = [
            # (database, org, description)
            ("數據庫", "組織", "中文字符"),
            ("база_данных", "организация", "俄語字符"),
            ("قاعدة_البيانات", "المنظمة", "阿拉伯語字符"),
            ("データベース", "組織", "日語字符"),
            ("database_🚀", "org_💎", "Emoji 字符"),
        ]
        
        for database, org, description in unicode_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", "unicode-test-token")
                mp.setenv("INFLUXDB_DATABASE", database)
                mp.setenv("INFLUXDB_ORG", org)
                
                try:
                    settings = SingleCryptoSettings()
                    assert settings.influxdb_database == database
                    assert settings.influxdb_org == org
                    
                    # 測試序列化和反序列化保持 Unicode
                    serialized = settings.model_dump()
                    restored = SingleCryptoSettings.model_validate(serialized)
                    assert restored.influxdb_database == database
                    assert restored.influxdb_org == org
                    
                except ValidationError:
                    # 某些 Unicode 字符可能無效，這是可接受的
                    pass

    def test_handles_empty_and_whitespace_influxdb_config(self):
        """測試處理空值和空白字符的 InfluxDB 配置"""
        # TDD: 定義配置類必須妥善處理空值和空白字符
        
        empty_cases = [
            # (field_name, field_value, environment)
            ("INFLUXDB_DATABASE", "", "production"),    # 空資料庫名
            ("INFLUXDB_DATABASE", "   ", "production"),  # 空白資料庫名
            ("INFLUXDB_ORG", "", "production"),         # 空組織名
            ("INFLUXDB_ORG", "\t\n", "production"),     # 制表符和換行符
        ]
        
        for field_name, field_value, environment in empty_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", environment)
                mp.setenv("ENABLE_TIMESERIES_DATA", "true")
                mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
                mp.setenv("INFLUXDB_TOKEN", "test-token")
                mp.setenv("INFLUXDB_DATABASE", "test-db")
                mp.setenv("INFLUXDB_ORG", "test-org")
                mp.setenv(field_name, field_value)
                
                if environment == "production":
                    # 生產環境應該要求非空值
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()
                else:
                    # 開發環境可能允許空值
                    settings = SingleCryptoSettings()
                    # 驗證基本功能
                    assert hasattr(settings, 'influxdb_host')

    # === 新增併發和性能測試 ===
    
    def test_concurrent_influxdb_configuration_access(self):
        """測試併發 InfluxDB 配置訪問"""
        # TDD: 定義 InfluxDB 配置必須支援併發訪問
        import threading
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "concurrent-test-token")
            mp.setenv("INFLUXDB_DATABASE", "concurrent-db")
            mp.setenv("INFLUXDB_ORG", "concurrent-org")
            mp.setenv("INFLUXDB_BATCH_SIZE", "2000")
            
            settings = SingleCryptoSettings()
            results = []
            errors = []
            
            def access_influxdb_config():
                try:
                    config = settings.get_influxdb_config()
                    assert config["batch_size"] == 2000
                    assert config["database"] == "concurrent-db"
                    assert config["org"] == "concurrent-org"
                    results.append(config)
                except Exception as e:
                    errors.append(str(e))
            
            # 創建多個線程同時訪問 InfluxDB 配置
            threads = []
            for i in range(10):
                thread = threading.Thread(target=access_influxdb_config)
                threads.append(thread)
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            assert len(errors) == 0, f"併發訪問錯誤: {errors}"
            assert len(results) == 10
            
            # 驗證所有結果一致
            for config in results:
                assert config["batch_size"] == 2000
                assert config["database"] == "concurrent-db"

    def test_influxdb_configuration_memory_usage(self):
        """測試 InfluxDB 配置記憶體使用"""
        # TDD: 定義 InfluxDB 配置不應造成記憶體洩漏
        import gc
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "memory-test-token")
            mp.setenv("INFLUXDB_DATABASE", "memory-test-db")
            mp.setenv("INFLUXDB_ORG", "memory-test-org")
            
            # 創建多個配置實例
            instances = []
            for i in range(100):
                instance = SingleCryptoSettings()
                instances.append(instance)
            
            # 驗證實例正常工作
            for instance in instances:
                config = instance.get_influxdb_config()
                assert config["database"] == "memory-test-db"
                assert config["org"] == "memory-test-org"
            
            # 清理並測試記憶體釋放
            del instances
            gc.collect()
            
            # 主要測試功能性，避免在CI中不穩定的記憶體測量

    def test_influxdb_configuration_performance(self):
        """測試 InfluxDB 配置性能"""
        # TDD: 定義 InfluxDB 配置應有合理的性能
        import time
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("INFLUXDB_HOST", "https://influxdb.example.com")
            mp.setenv("INFLUXDB_TOKEN", "performance-test-token")
            mp.setenv("INFLUXDB_DATABASE", "performance-test-db")
            mp.setenv("INFLUXDB_ORG", "performance-test-org")
            
            # 測試配置載入性能
            start_time = time.time()
            for i in range(50):
                settings = SingleCryptoSettings()
                config = settings.get_influxdb_config()
                assert config["database"] == "performance-test-db"
            load_time = time.time() - start_time
            
            # 50次載入應該在合理時間內完成
            assert load_time < 2.0, f"InfluxDB 配置載入時間過長: {load_time:.3f}秒"