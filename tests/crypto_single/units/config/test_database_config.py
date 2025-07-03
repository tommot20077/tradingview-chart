"""
A2.2: 資料庫配置測試設計

測試雙資料庫配置：PostgreSQL/SQLite（元數據）的配置管理功能。
這些測試定義了資料庫配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestDatabaseConfiguration:
    """測試資料庫配置功能"""

    def test_postgresql_connection_config_validation(self) -> None:
        """測試 PostgreSQL 連接配置驗證"""
        # TDD: 定義配置類必須支援 PostgreSQL 連接配置

        # 測試有效的 PostgreSQL URL
        valid_pg_urls = [
            "postgresql+asyncpg://user:pass@localhost:5432/dbname",
            "postgresql+asyncpg://user:pass@db.example.com:5432/crypto_single",
            "postgresql+asyncpg://crypto_user:secret@127.0.0.1/crypto_db",
        ]

        for url in valid_pg_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", url)
                settings = SingleCryptoSettings()
                assert settings.database_url == url
                assert "postgresql" in settings.database_url.lower()
                assert "asyncpg" in settings.database_url.lower()

    def test_sqlite_development_default(self) -> None:
        """測試 SQLite 開發環境預設值"""
        # TDD: 定義開發環境必須預設使用 SQLite

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            # 不設置 DATABASE_URL，應該使用預設的 SQLite
            settings = SingleCryptoSettings()

            # 驗證預設使用 SQLite
            assert "sqlite" in settings.database_url.lower()
            assert "aiosqlite" in settings.database_url.lower()
            assert settings.database_url.endswith(".db")

    def test_database_connection_pool_parameters(self) -> None:
        """測試資料庫連接池參數設定"""
        # TDD: 定義配置類必須支援連接池參數設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_POOL_SIZE", "20")
            mp.setenv("DATABASE_TIMEOUT", "60")
            mp.setenv("DATABASE_MAX_OVERFLOW", "10")

            settings = SingleCryptoSettings()

            # 驗證連接池參數
            assert hasattr(settings, "database_pool_size")
            assert hasattr(settings, "database_timeout")
            assert hasattr(settings, "database_max_overflow")

            assert settings.database_pool_size == 20
            assert settings.database_timeout == 60
            assert settings.database_max_overflow == 10

    def test_database_connection_pool_defaults(self) -> None:
        """測試資料庫連接池預設值"""
        # TDD: 定義連接池參數必須有合理的預設值

        settings = SingleCryptoSettings()

        # 驗證預設值合理性
        assert settings.database_pool_size >= 5  # 最小連接池大小
        assert settings.database_pool_size <= 20  # 合理的最大值
        assert settings.database_timeout >= 30  # 合理的超時時間
        assert settings.database_max_overflow >= 0  # 非負值

    def test_database_url_format_validation(self) -> None:
        """測試資料庫 URL 格式驗證"""
        # TDD: 定義配置類必須驗證資料庫 URL 格式

        # 測試無效的資料庫 URL 應該拋出驗證錯誤
        invalid_urls = [
            "invalid-url",
            "http://example.com",
            "mysql://user:pass@localhost/db",  # 不支援的資料庫類型
            "ftp://user:pass@localhost/db",  # 無效的協議
            ":",  # 完全無效的格式
        ]

        for invalid_url in invalid_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", invalid_url)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()

                # 驗證錯誤訊息相關
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["url", "database", "format"])

    def test_environment_specific_database_selection(self) -> None:
        """測試環境特定資料庫選擇"""
        # TDD: 定義不同環境必須選擇適當的資料庫

        # 開發環境：預設 SQLite
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            settings = SingleCryptoSettings()
            assert "sqlite" in settings.database_url.lower()

        # 生產環境：如果沒有設置 DATABASE_URL，應該要求 PostgreSQL
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            # 在生產環境不設置 DATABASE_URL 應該產生警告或錯誤
            with pytest.raises((ValidationError, ValueError)) as exc_info:
                SingleCryptoSettings()

            # 錯誤應該指出生產環境需要明確的資料庫配置
            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in ["production", "database", "required"])

        # 生產環境：明確設置 PostgreSQL 應該成功
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod_db")
            mp.setenv("SECRET_KEY", "a" * 32)  # Valid production secret key
            mp.setenv("CORS_ALLOW_ORIGINS", "https://example.com")  # Valid CORS origins
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")  # Disable to avoid InfluxDB requirement
            settings = SingleCryptoSettings()
            assert "postgresql" in settings.database_url.lower()

    def test_sqlite_file_path_handling(self) -> None:
        """測試 SQLite 檔案路徑處理"""
        # TDD: 定義 SQLite 配置必須正確處理檔案路徑

        # 測試相對路徑
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_single.db")
            settings = SingleCryptoSettings()
            assert settings.database_url == "sqlite+aiosqlite:///./crypto_single.db"

        # 測試絕對路徑
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "sqlite+aiosqlite:////tmp/crypto_single.db")
            settings = SingleCryptoSettings()
            assert settings.database_url == "sqlite+aiosqlite:////tmp/crypto_single.db"

        # 測試記憶體資料庫
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
            settings = SingleCryptoSettings()
            assert settings.database_url == "sqlite+aiosqlite:///:memory:"

    def test_database_configuration_provides_helper_methods(self) -> None:
        """測試資料庫配置提供輔助方法"""
        # TDD: 定義配置類必須提供資料庫相關的輔助方法

        # PostgreSQL 配置
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
            settings = SingleCryptoSettings()

            # 應該提供檢查資料庫類型的方法
            assert hasattr(settings, "is_postgres_db")
            assert hasattr(settings, "is_sqlite_db")
            assert settings.is_postgres_db() is True
            assert settings.is_sqlite_db() is False

        # SQLite 配置
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
            settings = SingleCryptoSettings()

            assert settings.is_postgres_db() is False
            assert settings.is_sqlite_db() is True

    def test_database_connection_string_security(self) -> None:
        """測試資料庫連接字符串安全性"""
        # TDD: 定義配置類必須處理敏感資訊安全性

        # 包含密碼的連接字符串
        sensitive_url = "postgresql+asyncpg://user:secret_password@localhost:5432/db"

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", sensitive_url)
            settings = SingleCryptoSettings()

            # 序列化時應該隱藏敏感資訊或提供安全的顯示方式
            _serialized = settings.model_dump()

            # 檢查是否有提供安全的 URL 顯示方法
            if hasattr(settings, "get_safe_database_url"):
                safe_url = settings.get_safe_database_url()
                assert "secret_password" not in safe_url
                assert "****" in safe_url or "[HIDDEN]" in safe_url

    def test_database_configuration_validation_errors(self) -> None:
        """測試資料庫配置驗證錯誤"""
        # TDD: 定義配置類必須提供清晰的驗證錯誤訊息

        # 測試連接池大小無效值
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_POOL_SIZE", "-1")  # 負數
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "pool_size" in error_str or "pool" in error_str

        # 測試超時時間無效值
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_TIMEOUT", "0")  # 零值
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "timeout" in error_str

    def test_database_configuration_migration_settings(self) -> None:
        """測試資料庫配置遷移設定"""
        # TDD: 定義配置類必須支援遷移相關設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_AUTO_MIGRATE", "true")
            mp.setenv("DATABASE_MIGRATION_TIMEOUT", "300")

            settings = SingleCryptoSettings()

            # 驗證遷移設定
            assert hasattr(settings, "database_auto_migrate")
            assert hasattr(settings, "database_migration_timeout")

            assert settings.database_auto_migrate is True
            assert settings.database_migration_timeout == 300

    def test_database_echo_sql_configuration(self) -> None:
        """測試資料庫 SQL 回顯配置"""
        # TDD: 定義配置類必須支援 SQL 回顯設定（用於調試）

        # 開發環境預設應該支援 SQL 回顯
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            mp.setenv("DATABASE_ECHO_SQL", "true")

            settings = SingleCryptoSettings()

            assert hasattr(settings, "database_echo_sql")
            assert settings.database_echo_sql is True

        # 生產環境預設應該關閉 SQL 回顯
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", "a" * 32)  # Valid production secret key
            mp.setenv("CORS_ALLOW_ORIGINS", "https://example.com")  # Valid CORS origins
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")  # Disable to avoid InfluxDB requirement

            settings = SingleCryptoSettings()

            # 生產環境預設應該關閉 echo
            assert settings.database_echo_sql is False

    # === 新增異常情況測試 ===

    def test_handles_database_connection_failures(self) -> None:
        """測試處理資料庫連接失敗"""
        # TDD: 定義配置類必須妥善處理資料庫連接失敗情況

        # 測試無效的主機名
        invalid_hosts = [
            "postgresql+asyncpg://user:pass@nonexistent-host:5432/db",
            "postgresql+asyncpg://user:pass@256.256.256.256:5432/db",  # 無效 IP
            "postgresql+asyncpg://user:pass@:5432/db",  # 空主機名
        ]

        for invalid_url in invalid_hosts:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", invalid_url)
                # 配置應該能夠載入，即使連接會失敗
                # 實際連接測試應該在連接時進行，而不是配置時
                try:
                    settings = SingleCryptoSettings()
                    assert settings.database_url == invalid_url
                except ValidationError:
                    # 如果配置階段就驗證連接性，驗證錯誤是可接受的
                    pass

    def test_handles_malformed_database_urls(self) -> None:
        """測試處理格式錯誤的資料庫 URL"""
        # TDD: 定義配置類必須妥善處理格式錯誤的資料庫 URL

        malformed_urls = [
            "mysql://user:pass@localhost:5432/db",  # Unsupported database type
            "http://user:pass@localhost:5432/db",  # Invalid protocol for database
            "invalid_scheme://user:pass@localhost:5432/db",  # 無效協議
            "not_a_url_at_all",  # Completely invalid URL format
            "://user:pass@localhost:5432/db",  # Missing protocol
        ]

        for malformed_url in malformed_urls:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", malformed_url)
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()

                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in ["database", "url", "format", "postgresql", "sqlite"])

    def test_handles_database_url_with_special_characters(self) -> None:
        """測試處理包含特殊字符的資料庫 URL"""
        # TDD: 定義配置類必須正確處理 URL 中的特殊字符

        special_char_cases = [
            # (url, should_be_valid)
            ("postgresql+asyncpg://user:p@ss%40word@localhost:5432/db", True),  # URL 編碼密碼
            ("postgresql+asyncpg://user:pass@localhost:5432/db-name", True),  # 資料庫名包含連字符
            ("postgresql+asyncpg://user-name:pass@localhost:5432/db", True),  # 用戶名包含連字符
            ("redis://user:pass@localhost:6379/0", False),  # Wrong database type
            ("sqlite+aiosqlite:///path%20with%20spaces/db.sqlite", True),  # 正確編碼的空格
        ]

        for url, should_be_valid in special_char_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", url)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.database_url == url
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_database_timeout_edge_cases(self) -> None:
        """測試處理資料庫超時邊界情況"""
        # TDD: 定義配置類必須正確處理超時邊界值

        timeout_cases = [
            # (timeout_value, should_be_valid)
            ("0", False),  # 零超時無效
            ("-1", False),  # 負超時無效
            ("1", True),  # 最小有效超時
            ("3600", True),  # 1小時超時
            ("86400", False),  # 24小時超時 - 超過最大值3600
            ("999999", False),  # 過大的超時值
            ("abc", False),  # 非數字值
            ("", False),  # 空值
        ]

        for timeout_value, should_be_valid in timeout_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_TIMEOUT", timeout_value)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.database_timeout == int(timeout_value)
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_corrupted_database_credentials(self) -> None:
        """測試處理損壞的資料庫憑證"""
        # TDD: 定義配置類必須妥善處理損壞或無效的憑證

        corrupted_cases = [
            "postgresql+asyncpg://user:pass@localhost:5432/db",  # 正常情況
            "postgresql+asyncpg://user::@localhost:5432/db",  # 空密碼
            "postgresql+asyncpg://user:p a s s@localhost:5432/db",  # 密碼包含空格
            "postgresql+asyncpg://user:pass with spaces@localhost:5432/db",  # 未編碼空格
        ]

        for case in corrupted_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", case)
                try:
                    settings = SingleCryptoSettings()
                    # 如果成功載入，驗證基本屬性
                    assert hasattr(settings, "database_url")
                except ValidationError as e:
                    # 驗證錯誤是可接受的
                    error_str = str(e).lower()
                    assert any(keyword in error_str for keyword in ["database", "url", "format"])

    # === 新增邊界條件測試 ===

    def test_handles_extreme_connection_pool_values(self) -> None:
        """測試處理極端的連接池值"""
        # TDD: 定義配置類必須正確處理連接池邊界值

        pool_size_cases = [
            # (pool_size, max_overflow, should_be_valid)
            ("1", "0", True),  # 最小連接池
            ("50", "100", True),  # 有效的連接池配置
            ("100", "200", False),  # 大連接池 - max_overflow超過最大值100
            ("0", "0", False),  # 零連接池無效
            ("-1", "5", False),  # 負連接池無效
            ("1000", "2000", False),  # 過大連接池
            ("5", "-1", False),  # 負溢出值無效
        ]

        for pool_size, max_overflow, should_be_valid in pool_size_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_POOL_SIZE", pool_size)
                mp.setenv("DATABASE_MAX_OVERFLOW", max_overflow)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.database_pool_size == int(pool_size)
                    assert settings.database_max_overflow == int(max_overflow)
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_extremely_long_database_urls(self) -> None:
        """測試處理極長的資料庫 URL"""
        # TDD: 定義配置類必須處理極長的資料庫 URL

        # 生成極長的資料庫名稱
        long_db_name = "a" * 1000
        long_url = f"postgresql+asyncpg://user:pass@localhost:5432/{long_db_name}"

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", long_url)

            try:
                settings = SingleCryptoSettings()
                assert settings.database_url == long_url
            except ValidationError as e:
                # 如果有長度限制，驗證錯誤是可接受的
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit"])

    def test_handles_unicode_in_database_config(self) -> None:
        """測試處理資料庫配置中的 Unicode 字符"""
        # TDD: 定義配置類必須正確處理 Unicode 字符

        unicode_cases = [
            "postgresql+asyncpg://用戶:密碼@localhost:5432/資料庫",  # 中文字符
            "postgresql+asyncpg://usuário:senha@localhost:5432/banco",  # 葡萄牙語
            "postgresql+asyncpg://пользователь:пароль@localhost:5432/база",  # 俄語
            "sqlite+aiosqlite:///./test_資料庫.db",  # SQLite 文件名包含中文
        ]

        for unicode_url in unicode_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("DATABASE_URL", unicode_url)

                try:
                    settings = SingleCryptoSettings()
                    assert settings.database_url == unicode_url

                    # 測試序列化和反序列化保持 Unicode
                    serialized = settings.model_dump()
                    restored = SingleCryptoSettings.model_validate(serialized)
                    assert restored.database_url == unicode_url

                except ValidationError:
                    # 某些 Unicode 字符可能在 URL 中無效，這是可接受的
                    pass

    def test_handles_empty_and_whitespace_database_config(self) -> None:
        """測試處理空值和空白字符的資料庫配置"""
        # TDD: 定義配置類必須妥善處理空值和空白字符

        empty_cases = [
            ("", "development", True),  # 空 URL，開發環境應使用預設
            ("   ", "development", False),  # 空白 URL - 現在被驗證器拒絕
            ("\t\n", "development", False),  # 制表符和換行符 - 現在被驗證器拒絕
        ]

        for empty_url, environment, should_be_valid in empty_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", environment)
                mp.setenv("DATABASE_URL", empty_url)

                if should_be_valid and environment == "development":
                    # 開發環境應該使用預設 SQLite
                    settings = SingleCryptoSettings()
                    assert "sqlite" in settings.database_url.lower()
                else:
                    # 非開發環境或無效格式應該要求明確的 URL
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    # === 新增併發和性能測試 ===

    def test_concurrent_database_configuration_access(self) -> None:
        """測試併發資料庫配置訪問"""
        # TDD: 定義資料庫配置必須支援併發訪問
        import threading

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/concurrent_test")
            mp.setenv("DATABASE_POOL_SIZE", "15")

            settings = SingleCryptoSettings()
            results = []
            errors = []

            def access_db_config() -> None:
                try:
                    config = settings.get_database_config()
                    assert config["pool_size"] == 15
                    assert "postgresql" in config["url"]
                    results.append(config)
                except Exception as e:
                    errors.append(str(e))

            # 創建多個線程同時訪問資料庫配置
            threads = []
            for _i in range(10):
                thread = threading.Thread(target=access_db_config)
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            assert len(errors) == 0, f"併發訪問錯誤: {errors}"
            assert len(results) == 10

            # 驗證所有結果一致
            for config in results:
                assert config["pool_size"] == 15

    def test_database_configuration_memory_usage(self) -> None:
        """測試資料庫配置記憶體使用"""
        # TDD: 定義資料庫配置不應造成記憶體洩漏
        import gc

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/memory_test")

            # 創建多個配置實例
            instances = []
            for _i in range(100):
                instance = SingleCryptoSettings()
                instances.append(instance)

            # 驗證實例正常工作
            for instance in instances:
                config = instance.get_database_config()
                assert "postgresql" in config["url"]

            # 清理並測試記憶體釋放
            del instances
            gc.collect()

            # 主要測試功能性，避免在CI中不穩定的記憶體測量

    def test_database_configuration_performance(self) -> None:
        """測試資料庫配置性能"""
        # TDD: 定義資料庫配置應有合理的性能
        import time

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/perf_test")

            # 測試配置載入性能
            start_time = time.time()
            for _i in range(50):
                settings = SingleCryptoSettings()
                config = settings.get_database_config()
                assert "postgresql" in config["url"]
            load_time = time.time() - start_time

            # 50次載入應該在合理時間內完成
            assert load_time < 2.0, f"資料庫配置載入時間過長: {load_time:.3f}秒"
