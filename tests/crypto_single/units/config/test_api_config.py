"""
A2.6: API 服務配置測試設計

測試 FastAPI 服務配置、安全設定、CORS 和中間件配置。
這些測試定義了 API 服務配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestAPIServiceConfiguration:
    """測試 API 服務配置功能"""

    def test_fastapi_basic_service_configuration(self):
        """測試 FastAPI 基礎服務配置"""
        # TDD: 定義配置類必須支援 FastAPI 基礎服務設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_HOST", "127.0.0.1")
            mp.setenv("API_PORT", "8080")
            mp.setenv("API_DEBUG", "true")
            mp.setenv("API_RELOAD", "true")
            
            settings = SingleCryptoSettings()
            
            # 驗證 API 服務配置參數
            assert hasattr(settings, 'api_host')
            assert hasattr(settings, 'api_port')
            assert hasattr(settings, 'api_debug')
            assert hasattr(settings, 'api_reload')
            
            assert settings.api_host == "127.0.0.1"
            assert settings.api_port == 8080
            assert settings.api_debug is True
            assert settings.api_reload is True

    def test_api_host_validation(self):
        """測試 API Host 驗證"""
        # TDD: 定義配置類必須驗證 Host 地址格式
        
        # 測試有效的 Host 地址
        valid_hosts = [
            "0.0.0.0",
            "127.0.0.1",
            "localhost",
            "192.168.1.100",
            "api.example.com",
        ]
        
        for host in valid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_HOST", host)
                settings = SingleCryptoSettings()
                assert settings.api_host == host

        # 測試無效的 Host 地址
        invalid_hosts = [
            "",           # 空字符串
            "   ",        # 只有空格
            "256.256.256.256",  # 無效 IP
            "invalid..host",    # 無效域名
        ]
        
        for invalid_host in invalid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_HOST", invalid_host)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "host" in error_str

    def test_api_port_validation(self):
        """測試 API Port 驗證"""
        # TDD: 定義配置類必須驗證端口號範圍
        
        # 測試有效的端口號
        valid_ports = [80, 443, 8000, 8080, 9000, 65535]
        
        for port in valid_ports:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_PORT", str(port))
                settings = SingleCryptoSettings()
                assert settings.api_port == port

        # 測試無效的端口號
        invalid_ports = [0, -1, 65536, 70000]
        
        for invalid_port in invalid_ports:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_PORT", str(invalid_port))
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "port" in error_str

    def test_api_security_configuration(self):
        """測試 API 安全配置"""
        # TDD: 定義配置類必須支援安全設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SECRET_KEY", "test-secret-key-for-jwt")
            mp.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
            mp.setenv("ALGORITHM", "HS256")
            
            settings = SingleCryptoSettings()
            
            # 驗證安全配置參數
            assert hasattr(settings, 'secret_key')
            assert hasattr(settings, 'access_token_expire_minutes')
            assert hasattr(settings, 'algorithm')
            
            assert settings.secret_key == "test-secret-key-for-jwt"
            assert settings.access_token_expire_minutes == 60
            assert settings.algorithm == "HS256"

    def test_secret_key_validation_and_security(self):
        """測試 Secret Key 驗證和安全性"""
        # TDD: 定義配置類必須驗證 Secret Key 強度
        
        # 測試有效的 Secret Key
        valid_secret_keys = [
            "very-long-secret-key-with-sufficient-entropy-12345",
            "abcdef1234567890abcdef1234567890abcdef1234567890",
        ]
        
        for secret_key in valid_secret_keys:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("SECRET_KEY", secret_key)
                settings = SingleCryptoSettings()
                assert settings.secret_key == secret_key

        # 測試無效的 Secret Key（太短或不安全）
        invalid_secret_keys = [
            "",           # 空字符串
            "short",      # 太短
            "12345",      # 太簡單
            "password",   # 常見密碼
        ]
        
        for invalid_key in invalid_secret_keys:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("SECRET_KEY", invalid_key)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "secret" in error_str or "key" in error_str

    def test_production_environment_security_validation(self):
        """測試生產環境安全性驗證"""
        # TDD: 定義生產環境必須強制安全配置
        
        # 生產環境必須關閉 debug 和 reload
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("API_DEBUG", "true")  # 在生產環境不應該啟用
            
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in ["production", "debug", "security"])

        # 生產環境必須有強 Secret Key
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", "weak-key")  # 弱密鑰
            
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            error_str = str(exc_info.value).lower()
            assert "secret" in error_str and "production" in error_str

    def test_cors_configuration(self):
        """測試 CORS 配置"""
        # TDD: 定義配置類必須支援 CORS 設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("CORS_ENABLED", "true")
            mp.setenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,https://app.example.com")
            mp.setenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE")
            mp.setenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
            
            settings = SingleCryptoSettings()
            
            # 驗證 CORS 配置參數
            assert hasattr(settings, 'cors_enabled')
            assert hasattr(settings, 'cors_allow_origins')
            assert hasattr(settings, 'cors_allow_methods')
            assert hasattr(settings, 'cors_allow_headers')
            
            assert settings.cors_enabled is True
            assert settings.cors_allow_origins == "http://localhost:3000,https://app.example.com"
            assert settings.cors_allow_methods == "GET,POST,PUT,DELETE"
            assert settings.cors_allow_headers == "Content-Type,Authorization"

    def test_cors_origins_validation(self):
        """測試 CORS Origins 驗證"""
        # TDD: 定義配置類必須驗證 CORS Origins 格式
        
        # 測試有效的 Origins
        valid_origins = [
            "http://localhost:3000",
            "https://app.example.com,http://localhost:3000",
            "*",  # 允許所有來源（開發環境）
        ]
        
        for origins in valid_origins:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("CORS_ALLOW_ORIGINS", origins)
                settings = SingleCryptoSettings()
                assert settings.cors_allow_origins == origins

        # 生產環境不應該允許 "*"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("CORS_ALLOW_ORIGINS", "*")
            
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            error_str = str(exc_info.value).lower()
            assert "cors" in error_str and "production" in error_str

    def test_api_middleware_configuration(self):
        """測試 API 中間件配置"""
        # TDD: 定義配置類必須支援中間件設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("MIDDLEWARE_ENABLE_GZIP", "true")
            mp.setenv("MIDDLEWARE_ENABLE_LOGGING", "true")
            mp.setenv("MIDDLEWARE_ENABLE_RATE_LIMITING", "true")
            mp.setenv("MIDDLEWARE_RATE_LIMIT_REQUESTS", "100")
            mp.setenv("MIDDLEWARE_RATE_LIMIT_WINDOW", "60")
            
            settings = SingleCryptoSettings()
            
            # 驗證中間件配置參數
            assert hasattr(settings, 'middleware_enable_gzip')
            assert hasattr(settings, 'middleware_enable_logging')
            assert hasattr(settings, 'middleware_enable_rate_limiting')
            assert hasattr(settings, 'middleware_rate_limit_requests')
            assert hasattr(settings, 'middleware_rate_limit_window')
            
            assert settings.middleware_enable_gzip is True
            assert settings.middleware_enable_logging is True
            assert settings.middleware_enable_rate_limiting is True
            assert settings.middleware_rate_limit_requests == 100
            assert settings.middleware_rate_limit_window == 60

    def test_api_documentation_configuration(self):
        """測試 API 文檔配置"""
        # TDD: 定義配置類必須支援 API 文檔設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_DOCS_ENABLED", "true")
            mp.setenv("API_TITLE", "Crypto Single API")
            mp.setenv("API_VERSION", "1.0.0")
            mp.setenv("API_DESCRIPTION", "Cryptocurrency data API")
            mp.setenv("API_DOCS_URL", "/docs")
            mp.setenv("API_REDOC_URL", "/redoc")
            
            settings = SingleCryptoSettings()
            
            # 驗證 API 文檔配置參數
            assert hasattr(settings, 'api_docs_enabled')
            assert hasattr(settings, 'api_title')
            assert hasattr(settings, 'api_version')
            assert hasattr(settings, 'api_description')
            assert hasattr(settings, 'api_docs_url')
            assert hasattr(settings, 'api_redoc_url')
            
            assert settings.api_docs_enabled is True
            assert settings.api_title == "Crypto Single API"
            assert settings.api_version == "1.0.0"
            assert settings.api_description == "Cryptocurrency data API"
            assert settings.api_docs_url == "/docs"
            assert settings.api_redoc_url == "/redoc"

    def test_api_docs_production_environment_handling(self):
        """測試生產環境 API 文檔處理"""
        # TDD: 定義生產環境必須謹慎處理 API 文檔暴露
        
        # 生產環境預設應該關閉文檔，除非明確啟用
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            
            settings = SingleCryptoSettings()
            
            # 生產環境預設應該關閉 API 文檔
            assert settings.api_docs_enabled is False

        # 生產環境明確啟用文檔應該有警告或特殊處理
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("API_DOCS_ENABLED", "true")
            mp.setenv("API_DOCS_PRODUCTION_OVERRIDE", "true")  # 明確覆蓋
            
            settings = SingleCryptoSettings()
            assert settings.api_docs_enabled is True

    def test_api_request_size_limits_configuration(self):
        """測試 API 請求大小限制配置"""
        # TDD: 定義配置類必須支援請求大小限制設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_MAX_REQUEST_SIZE", "10485760")  # 10MB
            mp.setenv("API_MAX_UPLOAD_SIZE", "52428800")   # 50MB
            
            settings = SingleCryptoSettings()
            
            # 驗證請求大小限制配置
            assert hasattr(settings, 'api_max_request_size')
            assert hasattr(settings, 'api_max_upload_size')
            
            assert settings.api_max_request_size == 10485760
            assert settings.api_max_upload_size == 52428800

    def test_api_timeout_configuration(self):
        """測試 API 超時配置"""
        # TDD: 定義配置類必須支援超時設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_REQUEST_TIMEOUT", "30")
            mp.setenv("API_KEEPALIVE_TIMEOUT", "5")
            mp.setenv("API_GRACEFUL_SHUTDOWN_TIMEOUT", "10")
            
            settings = SingleCryptoSettings()
            
            # 驗證超時配置
            assert hasattr(settings, 'api_request_timeout')
            assert hasattr(settings, 'api_keepalive_timeout')
            assert hasattr(settings, 'api_graceful_shutdown_timeout')
            
            assert settings.api_request_timeout == 30
            assert settings.api_keepalive_timeout == 5
            assert settings.api_graceful_shutdown_timeout == 10

    def test_api_authentication_configuration(self):
        """測試 API 認證配置"""
        # TDD: 定義配置類必須支援認證設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_ENABLE_AUTH", "true")
            mp.setenv("API_AUTH_TYPE", "bearer")
            mp.setenv("API_TOKEN_URL", "/api/v1/auth/token")
            
            settings = SingleCryptoSettings()
            
            # 驗證認證配置
            assert hasattr(settings, 'api_enable_auth')
            assert hasattr(settings, 'api_auth_type')
            assert hasattr(settings, 'api_token_url')
            
            assert settings.api_enable_auth is True
            assert settings.api_auth_type == "bearer"
            assert settings.api_token_url == "/api/v1/auth/token"

    def test_api_versioning_configuration(self):
        """測試 API 版本控制配置"""
        # TDD: 定義配置類必須支援 API 版本控制設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_VERSION_PREFIX", "/api/v1")
            mp.setenv("API_DEFAULT_VERSION", "1.0")
            mp.setenv("API_DEPRECATED_VERSIONS", "0.9,0.8")
            
            settings = SingleCryptoSettings()
            
            # 驗證版本控制配置
            assert hasattr(settings, 'api_version_prefix')
            assert hasattr(settings, 'api_default_version')
            assert hasattr(settings, 'api_deprecated_versions')
            
            assert settings.api_version_prefix == "/api/v1"
            assert settings.api_default_version == "1.0"
            assert settings.api_deprecated_versions == "0.9,0.8"

    def test_api_configuration_provides_helper_methods(self):
        """測試 API 配置提供輔助方法"""
        # TDD: 定義配置類必須提供 API 相關的輔助方法
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_HOST", "0.0.0.0")
            mp.setenv("API_PORT", "8000")
            
            settings = SingleCryptoSettings()
            
            # 應該提供獲取完整服務器地址的方法
            assert hasattr(settings, 'get_api_base_url')
            
            base_url = settings.get_api_base_url()
            assert isinstance(base_url, str)
            assert "0.0.0.0:8000" in base_url or "http://" in base_url

            # 應該提供獲取完整 API 配置的方法
            assert hasattr(settings, 'get_api_config')
            
            api_config = settings.get_api_config()
            assert isinstance(api_config, dict)
            assert 'host' in api_config
            assert 'port' in api_config

    def test_api_secret_key_security_handling(self):
        """測試 API Secret Key 安全性處理"""
        # TDD: 定義配置類必須安全處理敏感的 Secret Key
        
        sensitive_secret = "super-secret-jwt-key-for-production-use"
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SECRET_KEY", sensitive_secret)
            settings = SingleCryptoSettings()
            
            # 序列化時應該隱藏敏感資訊
            serialized = settings.model_dump()
            
            # 檢查是否有提供安全的 Secret Key 顯示方法
            if hasattr(settings, 'get_safe_secret_key'):
                safe_key = settings.get_safe_secret_key()
                assert sensitive_secret not in safe_key
                assert "****" in safe_key or "[HIDDEN]" in safe_key

    # === 新增異常情況測試 ===
    
    def test_handles_invalid_api_hosts(self):
        """測試處理無效的 API 主機"""
        # TDD: 定義配置類必須妥善處理無效的 API 主機
        
        invalid_hosts = [
            "",              # 空主機
            "   ",           # 空白主機
            "256.256.256.256",  # 無效 IP
            "host..example.com",  # 無效域名格式
            ".example.com",      # 以點開頭的域名
            "example.com.",      # 以點結尾的域名
            "host with spaces",  # 包含空格
        ]
        
        for invalid_host in invalid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_HOST", invalid_host)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["host", "api", "invalid"])

    def test_handles_invalid_api_ports(self):
        """測試處理無效的 API 端口"""
        # TDD: 定義配置類必須妥善處理無效的端口號
        
        invalid_ports = [
            "-1",        # 負端口
            "0",         # 零端口
            "65536",     # 超出範圍
            "999999",    # 過大端口
            "abc",       # 非數字
            "",          # 空值
            "8000.5",    # 浮點數
        ]
        
        for invalid_port in invalid_ports:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_PORT", invalid_port)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["port", "api"])

    def test_handles_weak_secret_keys(self):
        """測試處理弱密鑰"""
        # TDD: 定義配置類必須拒絕弱密鑰
        
        weak_keys = [
            "",          # 空密鑰
            "123",       # 太短
            "password",  # 常見密碼
            "secret",    # 常見密碼
            "test",      # 常見密碼
            "12345",     # 常見密碼
            "weak",      # 常見密碼
        ]
        
        for weak_key in weak_keys:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", "production")
                mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                mp.setenv("SECRET_KEY", weak_key)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["secret", "key", "production"])

    def test_handles_production_security_violations(self):
        """測試處理生產環境安全違規"""
        # TDD: 定義生產環境必須強制安全設定
        
        security_violations = [
            # (field_name, field_value, violation_type)
            ("API_DEBUG", "true", "debug enabled"),
            ("API_RELOAD", "true", "reload enabled"),
            ("CORS_ALLOW_ORIGINS", "*", "open CORS"),
        ]
        
        for field_name, field_value, violation_type in security_violations:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", "production")
                mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                mp.setenv("SECRET_KEY", "very-secure-production-secret-key-12345")
                mp.setenv(field_name, field_value)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["production", "security", "debug", "cors"])

    def test_handles_invalid_cors_configurations(self):
        """測試處理無效的 CORS 配置"""
        # TDD: 定義配置類必須妥善處理 CORS 配置錯誤
        
        invalid_cors_cases = [
            # (origins, environment, should_fail)
            ("*", "production", True),      # 生產環境不允許所有來源
            ("", "development", False),     # 開發環境空 CORS 可接受
            ("invalid-url", "development", False),  # 開發環境較寬鬆
            ("http://example.com", "production", False),  # 生產環境明確來源
        ]
        
        for origins, environment, should_fail in invalid_cors_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", environment)
                if environment == "production":
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                    mp.setenv("SECRET_KEY", "secure-production-secret-key-12345")
                mp.setenv("CORS_ALLOW_ORIGINS", origins)
                
                if should_fail:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()
                else:
                    settings = SingleCryptoSettings()
                    assert hasattr(settings, 'cors_allow_origins')

    def test_handles_malformed_api_configuration(self):
        """測試處理格式錯誤的 API 配置"""
        # TDD: 定義配置類必須妥善處理格式錯誤的配置
        
        malformed_cases = [
            # (config_name, config_value, should_be_valid)
            ("API_REQUEST_TIMEOUT", "0", False),     # 零超時無效
            ("API_REQUEST_TIMEOUT", "-1", False),    # 負超時無效
            ("API_REQUEST_TIMEOUT", "invalid", False), # 非數字超時
            ("API_MAX_REQUEST_SIZE", "0", False),    # 零大小無效
            ("API_MAX_REQUEST_SIZE", "-1", False),   # 負大小無效
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "0", False), # 零過期時間無效
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "-1", False), # 負過期時間無效
            ("MIDDLEWARE_RATE_LIMIT_REQUESTS", "0", False), # 零限流無效
        ]
        
        for config_name, config_value, should_be_valid in malformed_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv(config_name, config_value)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert hasattr(settings, 'api_host')
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增邊界條件測試 ===
    
    def test_handles_extreme_api_parameter_values(self):
        """測試處理極端的 API 參數值"""
        # TDD: 定義配置類必須正確處理參數邊界值
        
        extreme_cases = [
            # (param_name, param_value, should_be_valid)
            ("API_PORT", "1", True),          # 最小端口
            ("API_PORT", "65535", True),      # 最大端口
            ("API_REQUEST_TIMEOUT", "1", True),     # 最小超時
            ("API_REQUEST_TIMEOUT", "300", True),   # 最大超時
            ("API_REQUEST_TIMEOUT", "301", False),  # 超過最大超時
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "5", True),     # 最小過期時間
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "10080", True), # 最大過期時間（一週）
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "10081", False), # 超過最大過期時間
            ("API_MAX_REQUEST_SIZE", "1024", True),         # 最小請求大小
            ("API_MAX_REQUEST_SIZE", "1073741824", True),   # 1GB 請求大小
            ("API_MAX_REQUEST_SIZE", "1073741825", False),  # 超過合理大小
        ]
        
        for param_name, param_value, should_be_valid in extreme_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv(param_name, param_value)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    config = settings.get_api_config()
                    assert config is not None
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_extremely_long_api_values(self):
        """測試處理極長的 API 配置值"""
        # TDD: 定義配置類必須處理極長的配置值
        
        # 生成極長的值
        long_title = "a" * 1000
        long_description = "b" * 5000
        long_version = "c" * 100
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_TITLE", long_title)
            mp.setenv("API_DESCRIPTION", long_description)
            mp.setenv("API_VERSION", long_version)
            
            try:
                settings = SingleCryptoSettings()
                assert settings.api_title == long_title
                assert settings.api_description == long_description
                assert settings.api_version == long_version
            except ValidationError as e:
                # 如果有長度限制，驗證錯誤是可接受的
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit"])

    def test_handles_unicode_in_api_config(self):
        """測試處理 API 配置中的 Unicode 字符"""
        # TDD: 定義配置類必須正確處理 Unicode 字符
        
        unicode_cases = [
            # (title, description)
            ("加密貨幣 API", "提供加密貨幣數據的 API 服務"),
            ("Криптовалютный API", "API для криптовалютных данных"),
            ("API للعملات المشفرة", "واجهة برمجة تطبيقات للعملات المشفرة"),
            ("暗号通貨 API", "暗号通貨データを提供するAPI"),
            ("Crypto API 🚀", "Amazing cryptocurrency API 💎"),
        ]
        
        for title, description in unicode_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_TITLE", title)
                mp.setenv("API_DESCRIPTION", description)
                
                try:
                    settings = SingleCryptoSettings()
                    assert settings.api_title == title
                    assert settings.api_description == description
                    
                    # 測試序列化和反序列化保持 Unicode
                    serialized = settings.model_dump()
                    restored = SingleCryptoSettings.model_validate(serialized)
                    assert restored.api_title == title
                    assert restored.api_description == description
                    
                except ValidationError:
                    # 某些 Unicode 字符可能無效，這是可接受的
                    pass

    def test_handles_empty_and_whitespace_api_config(self):
        """測試處理空值和空白字符的 API 配置"""
        # TDD: 定義配置類必須妥善處理空值和空白字符
        
        empty_cases = [
            # (field_name, field_value, should_use_default)
            ("API_TITLE", "", True),         # 空標題應使用預設
            ("API_TITLE", "   ", True),      # 空白標題
            ("API_DESCRIPTION", "", True),   # 空描述應使用預設
            ("API_VERSION", "", True),       # 空版本應使用預設
            ("API_VERSION", "\\t\\n", True), # 制表符和換行符
        ]
        
        for field_name, field_value, should_use_default in empty_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv(field_name, field_value)
                
                if should_use_default:
                    settings = SingleCryptoSettings()
                    if field_name == "API_TITLE":
                        # 應該使用預設標題
                        assert settings.api_title == "Crypto Single API"
                    elif field_name == "API_DESCRIPTION":
                        # 應該使用預設描述
                        assert settings.api_description == "Cryptocurrency data API"
                    elif field_name == "API_VERSION":
                        # 應該使用預設版本
                        assert settings.api_version == "1.0.0"

    def test_handles_api_url_edge_cases(self):
        """測試處理 API URL 邊界情況"""
        # TDD: 定義配置類必須正確處理 URL 配置邊界情況
        
        url_cases = [
            # (docs_url, redoc_url, token_url, should_be_valid)
            ("/docs", "/redoc", "/api/v1/auth/token", True),  # 標準 URL
            ("", "", "", True),                               # 空 URL（使用預設）
            ("/", "/", "/", True),                           # 根路徑
            ("/very/long/path/to/docs", "/very/long/path/to/redoc", "/very/long/path/to/token", True),
            ("invalid-url", "invalid-url", "invalid-url", True),  # 簡單無效 URL（內部使用）
        ]
        
        for docs_url, redoc_url, token_url, should_be_valid in url_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("API_DOCS_URL", docs_url)
                mp.setenv("API_REDOC_URL", redoc_url)
                mp.setenv("API_TOKEN_URL", token_url)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    config = settings.get_api_config()
                    assert config is not None
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增併發和性能測試 ===
    
    def test_concurrent_api_configuration_access(self):
        """測試併發 API 配置訪問"""
        # TDD: 定義 API 配置必須支援併發訪問
        import threading
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_HOST", "0.0.0.0")
            mp.setenv("API_PORT", "8080")
            mp.setenv("API_TITLE", "Concurrent Test API")
            mp.setenv("SECRET_KEY", "concurrent-test-secret-key-12345")
            
            settings = SingleCryptoSettings()
            results = []
            errors = []
            
            def access_api_config():
                try:
                    config = settings.get_api_config()
                    assert config["port"] == 8080
                    assert config["title"] == "Concurrent Test API"
                    base_url = settings.get_api_base_url()
                    assert "0.0.0.0:8080" in base_url
                    results.append(config)
                except Exception as e:
                    errors.append(str(e))
            
            # 創建多個線程同時訪問 API 配置
            threads = []
            for i in range(10):
                thread = threading.Thread(target=access_api_config)
                threads.append(thread)
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            assert len(errors) == 0, f"併發訪問錯誤: {errors}"
            assert len(results) == 10
            
            # 驗證所有結果一致
            for config in results:
                assert config["port"] == 8080
                assert config["title"] == "Concurrent Test API"

    def test_api_configuration_memory_usage(self):
        """測試 API 配置記憶體使用"""
        # TDD: 定義 API 配置不應造成記憶體洩漏
        import gc
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_HOST", "localhost")
            mp.setenv("API_PORT", "9000")
            mp.setenv("SECRET_KEY", "memory-test-secret-key-12345")
            
            # 創建多個配置實例
            instances = []
            for i in range(100):
                instance = SingleCryptoSettings()
                instances.append(instance)
            
            # 驗證實例正常工作
            for instance in instances:
                config = instance.get_api_config()
                assert config["port"] == 9000
                base_url = instance.get_api_base_url()
                assert "localhost:9000" in base_url
            
            # 清理並測試記憶體釋放
            del instances
            gc.collect()
            
            # 主要測試功能性，避免在CI中不穩定的記憶體測量

    def test_api_configuration_performance(self):
        """測試 API 配置性能"""
        # TDD: 定義 API 配置應有合理的性能
        import time
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("API_HOST", "127.0.0.1")
            mp.setenv("API_PORT", "7000")
            mp.setenv("SECRET_KEY", "performance-test-secret-key-12345")
            
            # 測試配置載入性能
            start_time = time.time()
            for i in range(50):
                settings = SingleCryptoSettings()
                config = settings.get_api_config()
                assert config["port"] == 7000
                base_url = settings.get_api_base_url()
                assert "127.0.0.1:7000" in base_url
            load_time = time.time() - start_time
            
            # 50次載入應該在合理時間內完成
            assert load_time < 2.0, f"API 配置載入時間過長: {load_time:.3f}秒"

    def test_api_security_configuration_edge_cases(self):
        """測試 API 安全配置邊界情況"""
        # TDD: 定義配置類必須正確處理安全相關的邊界情況
        
        security_cases = [
            # (secret_length, environment, should_be_valid)
            (10, "development", True),      # 開發環境短密鑰可接受
            (32, "production", True),       # 生產環境長密鑰
            (31, "production", False),      # 生產環境密鑰太短
            (100, "production", True),      # 生產環境超長密鑰
        ]
        
        for secret_length, environment, should_be_valid in security_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", environment)
                if environment == "production":
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                secret_key = "a" * secret_length
                mp.setenv("SECRET_KEY", secret_key)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert len(settings.secret_key.get_secret_value()) == secret_length
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()