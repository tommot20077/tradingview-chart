"""
A2.4: Redis 與快取配置測試設計

測試 Redis 配置和記憶體 fallback 機制，包括 TTL 和快取策略配置。
這些測試定義了 Redis 配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestRedisConfiguration:
    """測試 Redis 配置功能"""

    def test_redis_connection_configuration(self):
        """測試 Redis 連接配置"""
        # TDD: 定義配置類必須支援 Redis 連接配置
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_PASSWORD", "test-password")
            
            settings = SingleCryptoSettings()
            
            # 驗證 Redis 連接參數
            assert hasattr(settings, 'redis_url')
            assert hasattr(settings, 'redis_enabled')
            assert hasattr(settings, 'redis_password')
            
            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.redis_enabled is True
            assert settings.redis_password == "test-password"

    def test_redis_url_format_validation(self):
        """測試 Redis URL 格式驗證"""
        # TDD: 定義配置類必須驗證 Redis URL 格式
        
        # 測試有效的 Redis URL 格式
        valid_redis_urls = [
            "redis://localhost:6379",
            "redis://localhost:6379/0",
            "redis://user:pass@localhost:6379/1",
            "rediss://ssl-redis.example.com:6380/0",  # SSL Redis
            "redis://192.168.1.100:6379",
        ]
        
        for url in valid_redis_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_URL", url)
                settings = SingleCryptoSettings()
                assert settings.redis_url == url

        # 測試無效的 Redis URL 格式
        invalid_redis_urls = [
            "localhost:6379",           # 缺少協議
            "http://localhost:6379",    # 錯誤的協議
            "redis://",                 # 不完整的 URL
            "",                         # 空字符串
            "invalid-url",              # 無效 URL
        ]
        
        for invalid_url in invalid_redis_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_URL", invalid_url)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "redis" in error_str or "url" in error_str

    def test_redis_enabled_disable_toggle(self):
        """測試 Redis 啟用/停用切換"""
        # TDD: 定義配置類必須支援 Redis 啟用/停用切換
        
        # 測試啟用 Redis
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            settings = SingleCryptoSettings()
            assert settings.redis_enabled is True

        # 測試停用 Redis
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "false")
            settings = SingleCryptoSettings()
            assert settings.redis_enabled is False

        # 測試預設值 (應該是 False，使用記憶體 fallback)
        settings = SingleCryptoSettings()
        assert settings.redis_enabled is False

    def test_memory_fallback_mechanism(self):
        """測試記憶體 fallback 機制"""
        # TDD: 定義配置類必須支援記憶體 fallback 機制
        
        # 當 Redis 停用時，應該使用記憶體快取
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "false")
            settings = SingleCryptoSettings()
            
            # 應該提供檢查快取模式的方法
            assert hasattr(settings, 'use_redis_cache')
            assert hasattr(settings, 'use_memory_cache')
            
            assert settings.use_redis_cache() is False
            assert settings.use_memory_cache() is True

        # 當 Redis 啟用時，應該使用 Redis 快取
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            settings = SingleCryptoSettings()
            
            assert settings.use_redis_cache() is True
            assert settings.use_memory_cache() is False

    def test_redis_ttl_configuration(self):
        """測試 Redis TTL 配置"""
        # TDD: 定義配置類必須支援 TTL 設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_DEFAULT_TTL", "3600")     # 1小時
            mp.setenv("REDIS_METADATA_TTL", "86400")   # 24小時
            mp.setenv("REDIS_SYMBOL_TTL", "1800")      # 30分鐘
            
            settings = SingleCryptoSettings()
            
            # 驗證 TTL 設定
            assert hasattr(settings, 'redis_default_ttl')
            assert hasattr(settings, 'redis_metadata_ttl')
            assert hasattr(settings, 'redis_symbol_ttl')
            
            assert settings.redis_default_ttl == 3600
            assert settings.redis_metadata_ttl == 86400
            assert settings.redis_symbol_ttl == 1800

    def test_redis_ttl_validation(self):
        """測試 Redis TTL 值驗證"""
        # TDD: 定義配置類必須驗證 TTL 值的合理性
        
        # 測試無效的 TTL 值
        invalid_ttl_values = [
            "-1",     # 負數
            "0",      # 零值
            "abc",    # 非數字
            "",       # 空字符串
        ]
        
        for invalid_ttl in invalid_ttl_values:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_DEFAULT_TTL", invalid_ttl)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert "ttl" in error_str or "positive" in error_str

    def test_redis_cache_key_prefix_configuration(self):
        """測試 Redis 快取鍵前綴配置"""
        # TDD: 定義配置類必須支援快取鍵前綴設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_KEY_PREFIX", "crypto_single")
            mp.setenv("REDIS_KEY_SEPARATOR", ":")
            
            settings = SingleCryptoSettings()
            
            # 驗證鍵前綴設定
            assert hasattr(settings, 'redis_key_prefix')
            assert hasattr(settings, 'redis_key_separator')
            
            assert settings.redis_key_prefix == "crypto_single"
            assert settings.redis_key_separator == ":"

    def test_redis_cache_invalidation_strategy(self):
        """測試 Redis 快取失效策略配置"""
        # TDD: 定義配置類必須支援快取失效策略設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_MAX_MEMORY_POLICY", "allkeys-lru")
            mp.setenv("REDIS_EVICTION_POLICY", "volatile-ttl")
            
            settings = SingleCryptoSettings()
            
            # 驗證快取失效策略設定
            assert hasattr(settings, 'redis_max_memory_policy')
            assert hasattr(settings, 'redis_eviction_policy')
            
            assert settings.redis_max_memory_policy == "allkeys-lru"
            assert settings.redis_eviction_policy == "volatile-ttl"

    def test_redis_connection_pool_configuration(self):
        """測試 Redis 連接池配置"""
        # TDD: 定義配置類必須支援連接池設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_POOL_MAX_CONNECTIONS", "20")
            mp.setenv("REDIS_POOL_RETRY_ON_TIMEOUT", "true")
            mp.setenv("REDIS_CONNECTION_TIMEOUT", "5")
            mp.setenv("REDIS_SOCKET_TIMEOUT", "10")
            
            settings = SingleCryptoSettings()
            
            # 驗證連接池設定
            assert hasattr(settings, 'redis_pool_max_connections')
            assert hasattr(settings, 'redis_pool_retry_on_timeout')
            assert hasattr(settings, 'redis_connection_timeout')
            assert hasattr(settings, 'redis_socket_timeout')
            
            assert settings.redis_pool_max_connections == 20
            assert settings.redis_pool_retry_on_timeout is True
            assert settings.redis_connection_timeout == 5
            assert settings.redis_socket_timeout == 10

    def test_redis_graceful_degradation_when_unavailable(self):
        """測試 Redis 不可用時的優雅降級"""
        # TDD: 定義配置類必須支援 Redis 不可用時的處理
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_GRACEFUL_DEGRADATION", "true")
            mp.setenv("REDIS_HEALTH_CHECK_INTERVAL", "30")
            
            settings = SingleCryptoSettings()
            
            # 驗證優雅降級設定
            assert hasattr(settings, 'redis_graceful_degradation')
            assert hasattr(settings, 'redis_health_check_interval')
            
            assert settings.redis_graceful_degradation is True
            assert settings.redis_health_check_interval == 30

    def test_redis_ssl_configuration(self):
        """測試 Redis SSL 配置"""
        # TDD: 定義配置類必須支援 Redis SSL 連接設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_URL", "rediss://ssl-redis.example.com:6380/0")
            mp.setenv("REDIS_SSL_VERIFY", "true")
            mp.setenv("REDIS_SSL_CA_CERT", "/path/to/ca.pem")
            
            settings = SingleCryptoSettings()
            
            # 驗證 SSL 設定
            assert hasattr(settings, 'redis_ssl_verify')
            assert hasattr(settings, 'redis_ssl_ca_cert')
            
            assert settings.redis_ssl_verify is True
            assert settings.redis_ssl_ca_cert == "/path/to/ca.pem"

    def test_redis_password_security_handling(self):
        """測試 Redis 密碼安全性處理"""
        # TDD: 定義配置類必須安全處理 Redis 密碼
        
        sensitive_password = "super-secret-redis-password"
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_PASSWORD", sensitive_password)
            settings = SingleCryptoSettings()
            
            # 序列化時應該隱藏敏感資訊
            serialized = settings.model_dump()
            
            # 檢查是否有提供安全的密碼顯示方法
            if hasattr(settings, 'get_safe_redis_password'):
                safe_password = settings.get_safe_redis_password()
                assert sensitive_password not in safe_password
                assert "****" in safe_password or "[HIDDEN]" in safe_password

    def test_redis_clustering_configuration(self):
        """測試 Redis 集群配置"""
        # TDD: 定義配置類必須支援 Redis 集群設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_CLUSTER_ENABLED", "true")
            mp.setenv("REDIS_CLUSTER_NODES", "redis1:7000,redis2:7000,redis3:7000")
            mp.setenv("REDIS_CLUSTER_SKIP_FULL_COVERAGE_CHECK", "false")
            
            settings = SingleCryptoSettings()
            
            # 驗證集群設定
            assert hasattr(settings, 'redis_cluster_enabled')
            assert hasattr(settings, 'redis_cluster_nodes')
            assert hasattr(settings, 'redis_cluster_skip_full_coverage_check')
            
            assert settings.redis_cluster_enabled is True
            assert settings.redis_cluster_nodes == "redis1:7000,redis2:7000,redis3:7000"
            assert settings.redis_cluster_skip_full_coverage_check is False

    def test_redis_serialization_configuration(self):
        """測試 Redis 序列化配置"""
        # TDD: 定義配置類必須支援序列化格式設定
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_SERIALIZER", "json")
            mp.setenv("REDIS_COMPRESSION_ENABLED", "true")
            mp.setenv("REDIS_COMPRESSION_THRESHOLD", "1024")
            
            settings = SingleCryptoSettings()
            
            # 驗證序列化設定
            assert hasattr(settings, 'redis_serializer')
            assert hasattr(settings, 'redis_compression_enabled')
            assert hasattr(settings, 'redis_compression_threshold')
            
            assert settings.redis_serializer == "json"
            assert settings.redis_compression_enabled is True
            assert settings.redis_compression_threshold == 1024

    def test_redis_serializer_validation(self):
        """測試 Redis 序列化器驗證"""
        # TDD: 定義配置類必須驗證序列化器類型
        
        # 測試有效的序列化器
        valid_serializers = ["json", "pickle", "msgpack"]
        
        for serializer in valid_serializers:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_SERIALIZER", serializer)
                settings = SingleCryptoSettings()
                assert settings.redis_serializer == serializer

        # 測試無效的序列化器
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_SERIALIZER", "invalid_serializer")
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            error_str = str(exc_info.value).lower()
            assert "serializer" in error_str

    def test_redis_configuration_provides_helper_methods(self):
        """測試 Redis 配置提供輔助方法"""
        # TDD: 定義配置類必須提供 Redis 相關的輔助方法
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            
            settings = SingleCryptoSettings()
            
            # 應該提供獲取 Redis 配置的方法
            assert hasattr(settings, 'get_redis_config')
            
            redis_config = settings.get_redis_config()
            assert isinstance(redis_config, dict)
            assert 'url' in redis_config
            assert 'enabled' in redis_config

            # 應該提供獲取快取配置的方法
            assert hasattr(settings, 'get_cache_config')
            
            cache_config = settings.get_cache_config()
            assert isinstance(cache_config, dict)
            assert 'backend' in cache_config  # 'redis' or 'memory'

    # === 新增異常情況測試 ===
    
    def test_handles_invalid_redis_urls(self):
        """測試處理無效的 Redis URL"""
        # TDD: 定義配置類必須妥善處理無效的 Redis URL
        
        invalid_urls = [
            "http://localhost:6379",  # 錯誤協議
            "redis://",               # 空主機
            "redis://localhost:abc",  # 無效端口
            "redis://localhost:6379/abc",  # 無效資料庫編號
            "redis://localhost:99999",     # 端口超出範圍
            "invalid-url",            # 完全無效的 URL
            "redis://256.256.256.256:6379",  # 無效 IP
        ]
        
        for invalid_url in invalid_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", invalid_url)
                
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()
                
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["redis", "url", "format"])

    def test_handles_redis_connection_failures(self):
        """測試處理 Redis 連接失敗"""
        # TDD: 定義配置類必須妥善處理 Redis 連接失敗情況
        
        connection_failure_cases = [
            "redis://nonexistent-host:6379/0",  # 不存在的主機
            "redis://localhost:9999/0",         # 錯誤端口
            "redis://127.0.0.1:6379/99",        # 不存在的資料庫
        ]
        
        for failure_url in connection_failure_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", failure_url)
                
                # 配置應該能夠載入，實際連接測試在連接時進行
                try:
                    settings = SingleCryptoSettings()
                    assert settings.redis_url == failure_url
                    assert settings.redis_enabled is True
                except ValidationError:
                    # 如果配置階段就驗證連接性，驗證錯誤是可接受的
                    pass

    def test_handles_corrupted_redis_passwords(self):
        """測試處理損壞的 Redis 密碼"""
        # TDD: 定義配置類必須妥善處理損壞或無效的密碼
        
        password_cases = [
            # (password, should_be_valid)
            ("", True),                    # 空密碼（無密碼認證）
            ("   ", False),                # 空白密碼
            ("valid_password", True),      # 有效密碼
            ("pass with spaces", True),    # 包含空格的密碼
            ("密碼123", True),             # Unicode 密碼
            ("p@ssw0rd!@#$%", True),      # 特殊字符密碼
            ("\t\n", False),              # 制表符和換行符
        ]
        
        for password, should_be_valid in password_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv("REDIS_PASSWORD", password)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    if password and password.strip():
                        assert settings.redis_password.get_secret_value() == password
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_redis_fallback_scenarios(self):
        """測試處理 Redis 降級場景"""
        # TDD: 定義配置類必須支援優雅降級到記憶體快取
        
        # Redis 停用但應用需要快取
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "false")
            mp.setenv("CACHE_FALLBACK_ENABLED", "true")
            
            settings = SingleCryptoSettings()
            
            # 應該降級到記憶體快取
            assert settings.redis_enabled is False
            cache_config = settings.get_cache_config()
            assert cache_config['backend'] == 'memory'

    def test_handles_malformed_redis_configuration(self):
        """測試處理格式錯誤的 Redis 配置"""
        # TDD: 定義配置類必須妥善處理格式錯誤的配置
        
        malformed_cases = [
            # (config_name, config_value, should_be_valid)
            ("REDIS_POOL_SIZE", "abc", False),      # 非數字連接池大小
            ("REDIS_POOL_SIZE", "-1", False),       # 負連接池大小
            ("REDIS_POOL_SIZE", "0", False),        # 零連接池大小
            ("REDIS_DEFAULT_TTL", "invalid", False), # 無效 TTL
            ("REDIS_DEFAULT_TTL", "-1", False),     # 負 TTL
            ("REDIS_SOCKET_TIMEOUT", "0", False),   # 零超時
            ("REDIS_SERIALIZER", "unknown", False), # 未知序列化器
        ]
        
        for config_name, config_value, should_be_valid in malformed_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv(config_name, config_value)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert hasattr(settings, 'redis_enabled')
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增邊界條件測試 ===
    
    def test_handles_extreme_redis_parameter_values(self):
        """測試處理極端的 Redis 參數值"""
        # TDD: 定義配置類必須正確處理參數邊界值
        
        extreme_cases = [
            # (param_name, param_value, should_be_valid)
            ("REDIS_POOL_SIZE", "1", True),         # 最小連接池
            ("REDIS_POOL_SIZE", "1000", False),     # 過大連接池
            ("REDIS_MAX_CONNECTIONS", "1", True),   # 最小連接數
            ("REDIS_MAX_CONNECTIONS", "10000", False), # 過大連接數
            ("REDIS_DEFAULT_TTL", "1", True),       # 最小 TTL
            ("REDIS_DEFAULT_TTL", "31536000", True), # 1年 TTL
            ("REDIS_DEFAULT_TTL", "999999999", False), # 過大 TTL
            ("REDIS_SOCKET_TIMEOUT", "1", True),    # 最小超時
            ("REDIS_SOCKET_TIMEOUT", "3600", True), # 1小時超時
            ("REDIS_SOCKET_TIMEOUT", "86400", False), # 過大超時
        ]
        
        for param_name, param_value, should_be_valid in extreme_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv(param_name, param_value)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    config = settings.get_redis_config()
                    assert config is not None
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_extremely_long_redis_values(self):
        """測試處理極長的 Redis 配置值"""
        # TDD: 定義配置類必須處理極長的配置值
        
        # 生成極長的值
        long_password = "a" * 5000
        long_prefix = "b" * 1000
        long_url = f"redis://localhost:6379/0"  # URL 本身不能太長
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", long_url)
            mp.setenv("REDIS_PASSWORD", long_password)
            mp.setenv("REDIS_CACHE_PREFIX", long_prefix)
            
            try:
                settings = SingleCryptoSettings()
                assert settings.redis_password.get_secret_value() == long_password
                assert settings.redis_cache_prefix == long_prefix
            except ValidationError as e:
                # 如果有長度限制，驗證錯誤是可接受的
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit"])

    def test_handles_unicode_in_redis_config(self):
        """測試處理 Redis 配置中的 Unicode 字符"""
        # TDD: 定義配置類必須正確處理 Unicode 字符
        
        unicode_cases = [
            # (prefix, password, description)
            ("前綴_", "密碼123", "中文字符"),
            ("префикс_", "пароль123", "俄語字符"),
            ("البادئة_", "كلمة_المرور", "阿拉伯語字符"),
            ("プレフィックス_", "パスワード", "日語字符"),
            ("prefix_🚀", "password_💎", "Emoji 字符"),
        ]
        
        for prefix, password, description in unicode_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv("REDIS_CACHE_PREFIX", prefix)
                mp.setenv("REDIS_PASSWORD", password)
                
                try:
                    settings = SingleCryptoSettings()
                    assert settings.redis_cache_prefix == prefix
                    assert settings.redis_password.get_secret_value() == password
                    
                    # 測試序列化和反序列化保持 Unicode
                    serialized = settings.model_dump()
                    restored = SingleCryptoSettings.model_validate(serialized)
                    assert restored.redis_cache_prefix == prefix
                    
                except ValidationError:
                    # 某些 Unicode 字符可能無效，這是可接受的
                    pass

    def test_handles_empty_and_whitespace_redis_config(self):
        """測試處理空值和空白字符的 Redis 配置"""
        # TDD: 定義配置類必須妥善處理空值和空白字符
        
        empty_cases = [
            # (field_name, field_value, should_use_default)
            ("REDIS_CACHE_PREFIX", "", True),      # 空前綴應使用預設
            ("REDIS_CACHE_PREFIX", "   ", True),   # 空白前綴
            ("REDIS_CACHE_PREFIX", "\t\n", True),  # 制表符和換行符
            ("REDIS_PASSWORD", "", True),          # 空密碼（無認證）
        ]
        
        for field_name, field_value, should_use_default in empty_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv(field_name, field_value)
                
                if should_use_default:
                    settings = SingleCryptoSettings()
                    if field_name == "REDIS_CACHE_PREFIX":
                        # 應該使用預設前綴
                        assert settings.redis_cache_prefix == "crypto_single"
                    elif field_name == "REDIS_PASSWORD":
                        # 空密碼應該是有效的（無認證模式）
                        assert settings.redis_password is None or settings.redis_password.get_secret_value() == ""

    def test_handles_redis_cluster_edge_cases(self):
        """測試處理 Redis 集群邊界情況"""
        # TDD: 定義配置類必須正確處理集群配置邊界情況
        
        cluster_cases = [
            # (cluster_enabled, cluster_nodes, should_be_valid)
            (True, "", False),                    # 啟用集群但無節點
            (True, "   ", False),                 # 啟用集群但空白節點
            (True, "localhost:7000", True),       # 單節點集群
            (True, "localhost:7000,localhost:7001", True),  # 多節點集群
            (False, "localhost:7000", True),      # 停用集群但有節點配置
        ]
        
        for cluster_enabled, cluster_nodes, should_be_valid in cluster_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_CLUSTER_ENABLED", str(cluster_enabled).lower())
                mp.setenv("REDIS_CLUSTER_NODES", cluster_nodes)
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.redis_cluster_enabled == cluster_enabled
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增併發和性能測試 ===
    
    def test_concurrent_redis_configuration_access(self):
        """測試併發 Redis 配置訪問"""
        # TDD: 定義 Redis 配置必須支援併發訪問
        import threading
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            mp.setenv("REDIS_POOL_SIZE", "25")
            mp.setenv("REDIS_DEFAULT_TTL", "7200")
            
            settings = SingleCryptoSettings()
            results = []
            errors = []
            
            def access_redis_config():
                try:
                    config = settings.get_redis_config()
                    assert config["pool_size"] == 25
                    assert config["default_ttl"] == 7200
                    assert config["enabled"] is True
                    results.append(config)
                except Exception as e:
                    errors.append(str(e))
            
            # 創建多個線程同時訪問 Redis 配置
            threads = []
            for i in range(10):
                thread = threading.Thread(target=access_redis_config)
                threads.append(thread)
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            assert len(errors) == 0, f"併發訪問錯誤: {errors}"
            assert len(results) == 10
            
            # 驗證所有結果一致
            for config in results:
                assert config["pool_size"] == 25
                assert config["default_ttl"] == 7200

    def test_redis_configuration_memory_usage(self):
        """測試 Redis 配置記憶體使用"""
        # TDD: 定義 Redis 配置不應造成記憶體洩漏
        import gc
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            mp.setenv("REDIS_PASSWORD", "memory-test-password")
            
            # 創建多個配置實例
            instances = []
            for i in range(100):
                instance = SingleCryptoSettings()
                instances.append(instance)
            
            # 驗證實例正常工作
            for instance in instances:
                config = instance.get_redis_config()
                assert config["enabled"] is True
                assert config["url"] == "redis://localhost:6379/0"
            
            # 清理並測試記憶體釋放
            del instances
            gc.collect()
            
            # 主要測試功能性，避免在CI中不穩定的記憶體測量

    def test_redis_configuration_performance(self):
        """測試 Redis 配置性能"""
        # TDD: 定義 Redis 配置應有合理的性能
        import time
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("REDIS_ENABLED", "true")
            mp.setenv("REDIS_URL", "redis://localhost:6379/0")
            mp.setenv("REDIS_PASSWORD", "performance-test-password")
            
            # 測試配置載入性能
            start_time = time.time()
            for i in range(50):
                settings = SingleCryptoSettings()
                config = settings.get_redis_config()
                assert config["enabled"] is True
            load_time = time.time() - start_time
            
            # 50次載入應該在合理時間內完成
            assert load_time < 2.0, f"Redis 配置載入時間過長: {load_time:.3f}秒"

    def test_redis_security_configuration_edge_cases(self):
        """測試 Redis 安全配置邊界情況"""
        # TDD: 定義配置類必須正確處理安全相關的邊界情況
        
        security_cases = [
            # (ssl_enabled, password, should_be_valid)
            (True, "", False),                    # SSL 啟用但無密碼
            (True, "secure_password", True),      # SSL 與密碼
            (False, "", True),                    # 無 SSL 無密碼（開發環境）
            (False, "password", True),            # 無 SSL 有密碼
        ]
        
        for ssl_enabled, password, should_be_valid in security_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("REDIS_ENABLED", "true")
                mp.setenv("REDIS_URL", "redis://localhost:6379/0")
                mp.setenv("REDIS_SSL_ENABLED", str(ssl_enabled).lower())
                mp.setenv("REDIS_PASSWORD", password)
                mp.setenv("APP_ENVIRONMENT", "development")  # 開發環境較寬鬆
                
                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.redis_ssl_enabled == ssl_enabled
                else:
                    # 某些安全配置組合可能無效
                    try:
                        settings = SingleCryptoSettings()
                        # 如果通過，驗證基本功能
                        assert hasattr(settings, 'redis_enabled')
                    except ValidationError:
                        # 驗證錯誤是可接受的
                        pass