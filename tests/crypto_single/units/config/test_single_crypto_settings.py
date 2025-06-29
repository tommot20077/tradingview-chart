"""
A2.1: 基礎配置類測試設計

測試 SingleCryptoSettings 正確繼承 BaseCoreSettings 並提供基礎配置功能。
這些測試定義了配置類的預期行為，實現時必須滿足這些測試。
"""

import os
import tempfile

import pytest
from pydantic import ValidationError

from asset_core.config.base import BaseCoreSettings


class TestSingleCryptoSettings:
    """測試 SingleCryptoSettings 基礎配置功能"""

    def test_inherits_from_base_core_settings(self):
        """測試 SingleCryptoSettings 正確繼承 BaseCoreSettings"""
        # TDD: 這個測試定義了 SingleCryptoSettings 必須繼承 BaseCoreSettings
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 驗證繼承關係
        assert issubclass(SingleCryptoSettings, BaseCoreSettings)
        
        # 驗證實例化後仍保持繼承關係
        settings = SingleCryptoSettings()
        assert isinstance(settings, BaseCoreSettings)
        assert isinstance(settings, SingleCryptoSettings)

    def test_loads_environment_variables_correctly(self):
        """測試環境變數載入機制"""
        # TDD: 定義配置類必須能正確載入環境變數
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 設置測試環境變數
        test_env = {
            "APP_NAME": "crypto-single-test",
            "APP_ENVIRONMENT": "development", 
            "DEBUG": "true"
        }
        
        with pytest.MonkeyPatch().context() as mp:
            # 設置環境變數
            for key, value in test_env.items():
                mp.setenv(key, value)
            
            # 創建配置實例
            settings = SingleCryptoSettings()
            
            # 驗證環境變數正確載入
            assert settings.app_name == "crypto-single-test"
            assert settings.environment == "development"
            assert settings.debug is True

    def test_loads_from_env_file(self):
        """測試從 .env 檔案載入配置"""
        # TDD: 定義配置類必須支援 .env 檔案載入
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 創建臨時 .env 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("APP_NAME=test-from-env\n")
            f.write("APP_ENVIRONMENT=staging\n")
            f.write("DEBUG=false\n")
            env_file_path = f.name
        
        try:
            # 使用指定的 .env 檔案創建配置
            settings = SingleCryptoSettings(_env_file=env_file_path)
            
            # 驗證從檔案正確載入
            assert settings.app_name == "test-from-env"
            assert settings.environment == "staging"
            assert settings.debug is False
        finally:
            # 清理臨時檔案
            os.unlink(env_file_path)

    def test_validates_required_fields(self):
        """測試必要欄位驗證"""
        # TDD: 定義配置類必須驗證必要欄位
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 測試 app_name 是否有合理預設值或驗證
        settings = SingleCryptoSettings()
        assert hasattr(settings, 'app_name')
        assert isinstance(settings.app_name, str)
        assert len(settings.app_name) > 0
        
        # 測試 environment 欄位驗證
        assert hasattr(settings, 'environment')
        assert settings.environment in ["development", "staging", "production"]
        
        # 測試 debug 欄位
        assert hasattr(settings, 'debug')
        assert isinstance(settings.debug, bool)

    def test_validates_environment_field_values(self):
        """測試 environment 欄位值驗證"""
        # TDD: 定義 environment 欄位必須只接受有效值
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 測試有效的 environment 值
        valid_environments = ["development", "staging", "production"]
        
        for env in valid_environments:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", env)
                # Provide required configuration for non-development environments
                if env != "development":
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
                    mp.setenv("SECRET_KEY", "test-secret-key-with-sufficient-length")
                    mp.setenv("INFLUXDB_HOST", "https://influxdb.test.com")
                    mp.setenv("CORS_ALLOW_ORIGINS", "https://test.example.com")
                settings = SingleCryptoSettings()
                assert settings.environment == env

        # 測試無效的 environment 值應該拋出驗證錯誤
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "invalid_env")
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            
            # 驗證錯誤訊息包含 environment 相關資訊
            assert "environment" in str(exc_info.value).lower()

    def test_provides_sensible_defaults(self):
        """測試預設值設定合理性"""
        # TDD: 定義配置類必須提供合理的預設值
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 在沒有環境變數的情況下創建配置
        settings = SingleCryptoSettings()
        
        # 驗證預設值合理性
        assert settings.app_name == "crypto-single"  # 合理的應用名稱
        assert settings.environment == "development"  # 安全的預設環境
        assert settings.debug is False  # 安全的預設 debug 設定

    def test_provides_environment_check_methods(self):
        """測試環境檢查方法"""
        # TDD: 定義配置類必須提供環境檢查便利方法
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 測試 development 環境
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "development")
            settings = SingleCryptoSettings()
            assert settings.is_development() is True
            assert settings.is_production() is False

        # 測試 production 環境
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
            mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length")
            mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
            mp.setenv("INFLUXDB_TOKEN", "prod-token")
            mp.setenv("INFLUXDB_DATABASE", "crypto_prod")
            mp.setenv("INFLUXDB_ORG", "crypto-org")
            mp.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")
            
            settings = SingleCryptoSettings()
            assert settings.is_development() is False
            assert settings.is_production() is True

    def test_model_serialization_deserialization(self):
        """測試配置模型序列化/反序列化"""
        # TDD: 定義配置類必須支援序列化和反序列化
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 創建配置實例
        original_settings = SingleCryptoSettings(
            app_name="test-serialize",
            environment="development",
            debug=True
        )
        
        # 測試序列化為字典
        settings_dict = original_settings.model_dump()
        assert isinstance(settings_dict, dict)
        assert settings_dict["app_name"] == "test-serialize"
        assert settings_dict["environment"] == "development"
        assert settings_dict["debug"] is True
        
        # 測試從字典反序列化
        restored_settings = SingleCryptoSettings.model_validate(settings_dict)
        assert restored_settings.app_name == original_settings.app_name
        assert restored_settings.environment == original_settings.environment
        assert restored_settings.debug == original_settings.debug

    def test_case_insensitive_environment_variables(self):
        """測試環境變數大小寫不敏感"""
        # TDD: 定義配置類必須支援大小寫不敏感的環境變數
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 測試小寫環境變數
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("app_name", "lowercase-test")
            mp.setenv("debug", "true")
            settings = SingleCryptoSettings()
            assert settings.app_name == "lowercase-test"
            assert settings.debug is True

        # 測試混合大小寫環境變數
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("App_Name", "mixedcase-test")
            mp.setenv("DEBUG", "false")
            settings = SingleCryptoSettings()
            assert settings.app_name == "mixedcase-test"
            assert settings.debug is False

    def test_ignores_extra_fields(self):
        """測試忽略額外欄位"""
        # TDD: 定義配置類必須忽略未定義的額外欄位
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 嘗試使用包含額外欄位的字典創建配置
        config_data = {
            "app_name": "test-extra-fields",
            "environment": "development",
            "debug": False,
            "unknown_field": "should_be_ignored",
            "another_extra": 12345
        }
        
        # 應該成功創建配置，忽略額外欄位
        settings = SingleCryptoSettings.model_validate(config_data)
        assert settings.app_name == "test-extra-fields"
        assert settings.environment == "development"
        assert settings.debug is False
        
        # 驗證額外欄位確實被忽略（不會出現在序列化結果中）
        serialized = settings.model_dump()
        assert "unknown_field" not in serialized
        assert "another_extra" not in serialized

    # === 新增異常情況測試 ===
    
    def test_handles_corrupted_env_file(self):
        """測試處理損壞的 .env 檔案"""
        # TDD: 定義配置類必須妥善處理損壞的 .env 檔案
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 創建包含無效內容的 .env 檔案
        corrupted_contents = [
            "INVALID_LINE_WITHOUT_EQUALS\n",
            "=VALUE_WITHOUT_KEY\n", 
            "KEY=\n",  # 有鍵但值為空
            "KEY==DOUBLE_EQUALS\n",
            "KEY=VALUE\nINVALID_LINE\nANOTHER_KEY=VALUE\n"  # 混合有效和無效行
        ]
        
        for corrupted_content in corrupted_contents:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write(corrupted_content)
                env_file_path = f.name
            
            try:
                # 應該能夠處理損壞的檔案而不崩潰
                settings = SingleCryptoSettings(_env_file=env_file_path)
                # 應該使用預設值而不是崩潰
                assert hasattr(settings, 'app_name')
                assert hasattr(settings, 'environment')
                assert hasattr(settings, 'debug')
            except Exception as e:
                # 如果拋出異常，應該是具體的、可理解的錯誤
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["env", "file", "format", "parse"])
            finally:
                os.unlink(env_file_path)

    def test_handles_missing_env_file(self):
        """測試處理不存在的 .env 檔案"""
        # TDD: 定義配置類必須妥善處理不存在的 .env 檔案
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 使用不存在的檔案路徑
        non_existent_path = "/tmp/non_existent_env_file_12345.env"
        
        # 應該能夠處理不存在的檔案而不崩潰
        settings = SingleCryptoSettings(_env_file=non_existent_path)
        
        # 應該使用預設值
        assert settings.app_name == "crypto-single"
        assert settings.environment == "development"
        assert settings.debug is False

    def test_handles_file_permission_errors(self):
        """測試處理檔案權限問題"""
        # TDD: 定義配置類必須妥善處理檔案權限錯誤
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 創建 .env 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("APP_NAME=permission-test\n")
            env_file_path = f.name
        
        try:
            # 移除讀取權限（如果系統支援）
            import stat
            os.chmod(env_file_path, stat.S_IWUSR)  # 只保留寫權限
            
            # 應該能夠處理權限錯誤而不崩潰
            try:
                settings = SingleCryptoSettings(_env_file=env_file_path)
                # 如果成功載入，應該使用預設值或拋出明確錯誤
                assert hasattr(settings, 'app_name')
            except PermissionError:
                # 如果拋出權限錯誤，這是可接受的
                pass
            except Exception as e:
                # 其他異常應該是具體的、可理解的錯誤
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["permission", "access", "file"])
                
        finally:
            # 恢復權限並清理
            os.chmod(env_file_path, stat.S_IRUSR | stat.S_IWUSR)
            os.unlink(env_file_path)

    def test_handles_malformed_environment_variables(self):
        """測試處理格式錯誤的環境變數"""
        # TDD: 定義配置類必須妥善處理格式錯誤的環境變數
        from crypto_single.config.settings import SingleCryptoSettings
        
        malformed_cases = [
            # (env_var_name, env_var_value, expected_behavior)
            ("DEBUG", "not_a_boolean", "should_use_default_or_raise_validation_error"),
            ("DEBUG", "1", "should_parse_as_true"),
            ("DEBUG", "0", "should_parse_as_false"),
            ("DEBUG", "yes", "should_parse_as_true"),
            ("DEBUG", "no", "should_parse_as_false"),
            ("APP_ENVIRONMENT", "INVALID_ENV", "should_raise_validation_error"),
            ("APP_ENVIRONMENT", "", "should_use_default_or_raise_validation_error"),
        ]
        
        for env_name, env_value, expected in malformed_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv(env_name, env_value)
                
                if "should_raise_validation_error" in expected:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()
                elif "should_parse_as_true" in expected:
                    settings = SingleCryptoSettings()
                    assert settings.debug is True
                elif "should_parse_as_false" in expected:
                    settings = SingleCryptoSettings()
                    assert settings.debug is False
                else:
                    # 應該使用預設值或優雅處理
                    try:
                        settings = SingleCryptoSettings()
                        assert hasattr(settings, 'debug')
                        assert hasattr(settings, 'environment')
                    except ValidationError:
                        # 驗證錯誤是可接受的
                        pass

    # === 新增邊界條件測試 ===
    
    def test_handles_extremely_long_values(self):
        """測試處理極長的配置值"""
        # TDD: 定義配置類必須妥善處理極長的配置值
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 測試極長的字符串值
        extremely_long_name = "a" * 10000  # 10KB 字符串
        extremely_long_env = "production"  # 仍然是有效值
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_NAME", extremely_long_name)
            mp.setenv("APP_ENVIRONMENT", extremely_long_env)
            # Provide required production configuration
            if extremely_long_env == "production":
                mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length")
                mp.setenv("INFLUXDB_HOST", "https://influxdb.prod.com")
                mp.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")
            
            # 應該能夠處理極長值（根據實際需求可能接受或拒絕）
            try:
                settings = SingleCryptoSettings()
                # 如果接受，值應該被正確保存
                assert settings.app_name == extremely_long_name
                assert settings.environment == extremely_long_env
            except ValidationError as e:
                # 如果拒絕，應該有明確的長度限制錯誤訊息
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit"])

    def test_handles_special_characters_in_values(self):
        """測試配置值中的特殊字符處理"""
        # TDD: 定義配置類必須正確處理特殊字符
        from crypto_single.config.settings import SingleCryptoSettings
        
        special_char_tests = [
            ("app-with-dashes", "development"),
            ("app_with_underscores", "development"),
            ("app.with.dots", "development"),
            ("app with spaces", "development"),
            ("app@with#special$chars", "development"),
            ("app漢字test", "development"),  # Unicode 中文字符
            ("app🚀emoji", "development"),  # Unicode emoji
            ("app\"with'quotes", "development"),
        ]
        
        for app_name, environment in special_char_tests:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_NAME", app_name)
                mp.setenv("APP_ENVIRONMENT", environment)
                
                # 應該能夠處理特殊字符
                settings = SingleCryptoSettings()
                assert settings.app_name == app_name
                assert settings.environment == environment

    def test_handles_null_and_empty_values(self):
        """
        測試 null 和空值的處理 - 可接受的邊界情況
        
        這個測試確保配置類在接收到空值時能優雅地回退到預設值，
        但只在開發環境中測試，避免觸發生產環境的嚴格驗證規則。
        
        邊界條件:
        - 空字符串 -> 應使用預設值
        - 僅在 development 環境測試，避免 production 驗證衝突
        """
        # TDD: 定義配置類必須妥善處理 null 和空值
        from crypto_single.config.settings import SingleCryptoSettings
        
        # 只在 development 環境測試空值處理，避免 production 環境的驗證錯誤
        with pytest.MonkeyPatch().context() as mp:
            # 確保處於 development 環境
            mp.setenv("APP_ENVIRONMENT", "development")
            
            empty_value_tests = [
                # (env_var_name, env_var_value, expected_default)
                ("APP_NAME", "", "crypto-single"),  # 空字符串應使用預設值
                ("DEBUG", "", False),  # 空 debug 值應使用預設值
            ]
            
            for env_name, env_value, expected_default in empty_value_tests:
                # 為每個測試案例設置獨立的環境
                with pytest.MonkeyPatch().context() as inner_mp:
                    inner_mp.setenv("APP_ENVIRONMENT", "development")  # 確保 development 環境
                    inner_mp.setenv(env_name, env_value)
                    
                    settings = SingleCryptoSettings()
                    # 驗證使用預設值而不是空值
                    if env_name == "APP_NAME":
                        assert settings.app_name == expected_default
                    elif env_name == "DEBUG":
                        assert settings.debug == expected_default
        
        # 單獨測試環境變數空值處理
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "")  # 空環境字符串
            mp.setenv("APP_NAME", "test-app")  # 設置其他必要值
            
            settings = SingleCryptoSettings()
            # 空環境應回退到 development 預設值
            assert settings.environment == "development"

    def test_handles_unicode_characters(self):
        """測試 Unicode 字符處理"""
        # TDD: 定義配置類必須正確處理 Unicode 字符
        from crypto_single.config.settings import SingleCryptoSettings
        
        unicode_tests = [
            ("crypto-測試", "development"),  # 中日韓字符
            ("crypto-тест", "development"),  # 西里爾字母
            ("crypto-اختبار", "development"),  # 阿拉伯字母
            ("crypto-🚀💎📈", "development"),  # Emoji
            ("crypto-𝓊𝓃𝒾𝒸𝑜𝒹𝑒", "development"),  # 數學字母符號
        ]
        
        for app_name, environment in unicode_tests:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_NAME", app_name)
                mp.setenv("APP_ENVIRONMENT", environment)
                
                # 應該能夠正確處理 Unicode 字符
                settings = SingleCryptoSettings()
                assert settings.app_name == app_name
                assert settings.environment == environment
                
                # 序列化和反序列化應該保持 Unicode 字符
                serialized = settings.model_dump()
                assert serialized["app_name"] == app_name
                
                restored = SingleCryptoSettings.model_validate(serialized)
                assert restored.app_name == app_name

    # === 新增通用測試場景 ===
    
    def test_concurrent_configuration_access(self):
        """測試併發訪問配置的安全性"""
        # TDD: 定義配置類必須支援併發訪問而不出現競態條件
        from crypto_single.config.settings import SingleCryptoSettings
        import threading

        # 設置共享配置
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_NAME", "concurrent-test")
            mp.setenv("APP_ENVIRONMENT", "development")
            mp.setenv("DEBUG", "true")
            
            settings = SingleCryptoSettings()
            results = []
            errors = []
            
            def access_config():
                """並發訪問配置的函數"""
                try:
                    # 讀取配置
                    name = settings.app_name
                    env = settings.environment
                    debug = settings.debug
                    
                    # 序列化配置
                    serialized = settings.model_dump()
                    
                    # 檢查一致性
                    assert name == "concurrent-test"
                    assert env == "development"
                    assert debug is True
                    assert serialized["app_name"] == name
                    
                    results.append((name, env, debug))
                    
                except Exception as e:
                    errors.append(str(e))
            
            # 創建多個線程同時訪問配置
            threads = []
            for i in range(10):
                thread = threading.Thread(target=access_config)
                threads.append(thread)
            
            # 啟動所有線程
            for thread in threads:
                thread.start()
            
            # 等待所有線程完成
            for thread in threads:
                thread.join()
            
            # 驗證結果
            assert len(errors) == 0, f"併發訪問出現錯誤: {errors}"
            assert len(results) == 10, f"預期10個結果，但得到 {len(results)} 個"
            
            # 驗證所有結果一致
            for name, env, debug in results:
                assert name == "concurrent-test"
                assert env == "development"
                assert debug is True

    def test_thread_safety_of_configuration(self):
        """
        測試配置的線程安全性 - 可接受的邊界情況
        
        這個測試驗證多線程環境下配置類的實例化安全性，
        但在 development 環境中進行，避免 production 環境的嚴格驗證需求。
        
        邊界條件:
        - 多線程同時創建實例
        - 使用 development 環境避免 production 驗證衝突
        - 驗證線程安全性和配置一致性
        """
        # TDD: 定義配置類必須是線程安全的
        from crypto_single.config.settings import SingleCryptoSettings
        import threading
        
        # 在 development 環境測試線程安全性，避免 production 驗證複雜性
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_NAME", "thread-safety-test")
            mp.setenv("APP_ENVIRONMENT", "development")  # 使用 development 避免驗證錯誤
            mp.setenv("DEBUG", "false")  # 明確設置以確保一致性
            
            instances = []
            errors = []
            
            def create_instance():
                """創建配置實例的函數"""
                try:
                    instance = SingleCryptoSettings()
                    instances.append(instance)
                except Exception as e:
                    errors.append(str(e))
            
            # 創建多個線程同時創建實例
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_instance)
                threads.append(thread)
            
            # 啟動所有線程
            for thread in threads:
                thread.start()
            
            # 等待所有線程完成
            for thread in threads:
                thread.join()
            
            # 驗證結果
            assert len(errors) == 0, f"線程安全測試出現錯誤: {errors}"
            assert len(instances) == 5, f"預期5個實例，但得到 {len(instances)} 個"
            
            # 驗證所有實例配置一致
            for instance in instances:
                assert instance.app_name == "thread-safety-test"
                assert instance.environment == "development"
                assert instance.debug is False
                
            # 額外驗證：所有實例都是獨立的物件但配置相同
            first_instance = instances[0]
            for instance in instances[1:]:
                # 不同的物件
                assert instance is not first_instance
                # 但配置相同
                assert instance.model_dump() == first_instance.model_dump()

    def test_memory_usage_with_large_configs(self):
        """測試大型配置的記憶體使用情況"""
        # TDD: 定義配置類必須有效處理大型配置而不過度消耗記憶體
        from crypto_single.config.settings import SingleCryptoSettings
        import gc

        # 獲取初始記憶體使用情況
        gc.collect()  # 強制垃圾回收
        
        # 創建多個配置實例
        instances = []
        
        with pytest.MonkeyPatch().context() as mp:
            # 設置大量環境變數模擬大型配置
            for i in range(100):
                mp.setenv(f"LARGE_CONFIG_VAR_{i}", f"value_{i}_{'x' * 100}")
            
            mp.setenv("APP_NAME", "memory-test")
            mp.setenv("APP_ENVIRONMENT", "development")
            
            # 創建多個實例
            for i in range(50):
                instance = SingleCryptoSettings()
                instances.append(instance)
        
        # 驗證實例正常工作
        for instance in instances:
            assert instance.app_name == "memory-test"
            assert instance.environment == "development"
            
            # 測試序列化不會造成記憶體問題
            serialized = instance.model_dump()
            assert isinstance(serialized, dict)
        
        # 清理並驗證記憶體可以被釋放
        del instances
        gc.collect()
        
        # 這個測試主要確保不會有明顯的記憶體洩漏
        # 實際的記憶體量測試在CI環境中可能不穩定，所以主要測試功能性

    def test_configuration_loading_performance(self):
        """測試配置載入性能"""
        # TDD: 定義配置類必須有合理的載入性能
        from crypto_single.config.settings import SingleCryptoSettings
        import time
        
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_NAME", "performance-test")
            mp.setenv("APP_ENVIRONMENT", "development")
            mp.setenv("DEBUG", "true")
            
            # 測試單次載入時間
            start_time = time.time()
            settings = SingleCryptoSettings()
            single_load_time = time.time() - start_time
            
            # 單次載入應該在合理時間內完成（例如：< 1秒）
            assert single_load_time < 1.0, f"單次載入時間過長: {single_load_time:.3f}秒"
            
            # 測試多次載入的平均時間
            load_times = []
            for i in range(10):
                start_time = time.time()
                instance = SingleCryptoSettings()
                load_time = time.time() - start_time
                load_times.append(load_time)
                
                # 驗證每個實例都正確載入
                assert instance.app_name == "performance-test"
                assert instance.environment == "development"
                assert instance.debug is True
            
            # 計算平均載入時間
            avg_load_time = sum(load_times) / len(load_times)
            assert avg_load_time < 0.1, f"平均載入時間過長: {avg_load_time:.3f}秒"
            
            # 測試序列化性能
            start_time = time.time()
            for i in range(100):
                serialized = settings.model_dump()
            serialization_time = time.time() - start_time
            
            assert serialization_time < 1.0, f"序列化時間過長: {serialization_time:.3f}秒"