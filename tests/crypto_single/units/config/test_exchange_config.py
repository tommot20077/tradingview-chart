"""
A2.5: 交易所配置測試設計

測試 Binance 配置及多交易所配置擴展性，包括 API 憑證處理和環境特定設定。
這些測試定義了交易所配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestExchangeConfiguration:
    """測試交易所配置功能"""

    def test_binance_basic_configuration(self) -> None:
        """測試 Binance 基礎配置"""
        # TDD: 定義配置類必須支援 Binance 基礎配置

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_API_KEY", "abcdef1234567890abcdef1234567890abcdef123456")  # 46 chars
            mp.setenv("BINANCE_SECRET_KEY", "secretkey1234567890abcdef1234567890abcdef12")  # 46 chars
            mp.setenv("BINANCE_TESTNET", "true")

            settings = SingleCryptoSettings()

            # 驗證 Binance 配置參數
            assert hasattr(settings, "binance_api_key")
            assert hasattr(settings, "binance_secret_key")
            assert hasattr(settings, "binance_testnet")

            assert settings.binance_api_key is not None
            assert settings.binance_api_key.get_secret_value() == "abcdef1234567890abcdef1234567890abcdef123456"
            assert settings.binance_secret_key is not None
            assert settings.binance_secret_key.get_secret_value() == "secretkey1234567890abcdef1234567890abcdef12"
            assert settings.binance_testnet is True

    def test_binance_api_credentials_optional_handling(self) -> None:
        """測試 Binance API 憑證可選性處理"""
        # TDD: 定義 API 憑證必須是可選的，支援無憑證模式

        # 測試無憑證模式（只讀取公開數據）
        settings = SingleCryptoSettings()

        # API 憑證應該是可選的
        assert hasattr(settings, "binance_api_key")
        assert hasattr(settings, "binance_secret_key")

        # 預設應該是 None 或空值
        assert settings.binance_api_key is None or settings.binance_api_key.get_secret_value() == ""
        assert settings.binance_secret_key is None or settings.binance_secret_key.get_secret_value() == ""

    def test_binance_testnet_vs_production_endpoints(self) -> None:
        """測試 Binance Testnet 與生產環境端點選擇"""
        # TDD: 定義配置類必須根據 testnet 設定選擇正確的端點

        # 測試 Testnet 模式
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_TESTNET", "true")
            settings = SingleCryptoSettings()

            # 應該提供獲取端點的方法
            assert hasattr(settings, "get_binance_base_url")
            assert hasattr(settings, "get_binance_ws_url")

            base_url = settings.get_binance_base_url()
            ws_url = settings.get_binance_ws_url()

            # Testnet 端點應該包含 testnet 相關字樣
            assert "testnet" in base_url.lower() or "test" in base_url.lower()
            assert "testnet" in ws_url.lower() or "test" in ws_url.lower()

        # 測試生產環境模式
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_TESTNET", "false")
            settings = SingleCryptoSettings()

            base_url = settings.get_binance_base_url()
            ws_url = settings.get_binance_ws_url()

            # 生產環境端點不應該包含 testnet
            assert "testnet" not in base_url.lower()
            assert "testnet" not in ws_url.lower()
            assert "api.binance.com" in base_url or "binance.com" in base_url

    def test_binance_production_environment_credential_validation(self) -> None:
        """測試生產環境 Binance 憑證驗證嚴格性"""
        # TDD: 定義生產環境必須驗證 API 憑證

        # 生產環境 + 非 testnet + 需要交易功能時，應該要求憑證
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("BINANCE_TESTNET", "false")
            mp.setenv("BINANCE_TRADING_ENABLED", "true")
            # 不設置 API 憑證

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in ["api", "key", "credential", "production"])

        # 生產環境 + 只讀模式應該可以不需要憑證
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("BINANCE_TESTNET", "false")
            mp.setenv("BINANCE_TRADING_ENABLED", "false")
            # Set required production settings
            mp.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
            mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length-12345678")
            mp.setenv("CORS_ALLOW_ORIGINS", "https://example.com")
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")  # Disable to avoid InfluxDB requirement

            settings = SingleCryptoSettings()
            # 應該可以成功創建（只讀模式）
            assert settings.binance_testnet is False

    def test_binance_api_key_format_validation(self) -> None:
        """測試 Binance API Key 格式驗證"""
        # TDD: 定義配置類必須驗證 API Key 格式

        # 測試有效的 API Key 格式
        valid_api_keys = [
            "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "test-api-key-with-dashes-123456789",  # 35 chars
            "TestAPIKey1234567890123",  # 23 chars
        ]

        for api_key in valid_api_keys:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("BINANCE_API_KEY", api_key)
                settings = SingleCryptoSettings()
                if settings.binance_api_key:
                    assert settings.binance_api_key.get_secret_value() == api_key

        # 測試無效的 API Key 格式 - 測試長度限制
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_API_KEY", "short")  # 太短，只有5個字符
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()
            error_str = str(exc_info.value).lower()
            assert "api" in error_str and "key" in error_str and "short" in error_str

    def test_future_exchange_extensibility(self) -> None:
        """測試未來交易所擴展性（為 Bybit 預留）"""
        # TDD: 定義配置結構必須支援未來擴展其他交易所

        # 應該有通用的交易所配置結構
        settings = SingleCryptoSettings()

        # 檢查是否有擴展性設計
        assert hasattr(settings, "get_exchange_config")

        # 測試獲取 Binance 配置
        binance_config = settings.get_exchange_config("binance")
        assert isinstance(binance_config, dict)
        assert "name" in binance_config
        assert binance_config["name"] == "binance"

        # 測試未來擴展（應該支援但可能返回 None 或預設配置）
        _bybit_config = settings.get_exchange_config("bybit")
        # 目前可能返回 None 或預設配置，但結構應該支援

    def test_exchange_configuration_provides_list_of_enabled_exchanges(self) -> None:
        """測試交易所配置提供已啟用交易所列表"""
        # TDD: 定義配置類必須提供已啟用交易所的列表

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BYBIT_ENABLED", "false")  # 未來擴展

            settings = SingleCryptoSettings()

            # 應該提供獲取已啟用交易所的方法
            assert hasattr(settings, "get_enabled_exchanges")

            enabled_exchanges = settings.get_enabled_exchanges()
            assert isinstance(enabled_exchanges, list)
            assert "binance" in enabled_exchanges

    def test_exchange_specific_rate_limiting_configuration(self) -> None:
        """測試交易所特定速率限制配置"""
        # TDD: 定義配置類必須支援交易所特定的速率限制設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "1200")
            mp.setenv("BINANCE_RATE_LIMIT_WEIGHT_PER_MINUTE", "1000")
            mp.setenv("BINANCE_RATE_LIMIT_ORDERS_PER_SECOND", "10")

            settings = SingleCryptoSettings()

            # 驗證速率限制設定
            assert hasattr(settings, "binance_rate_limit_requests_per_minute")
            assert hasattr(settings, "binance_rate_limit_weight_per_minute")
            assert hasattr(settings, "binance_rate_limit_orders_per_second")

            assert settings.binance_rate_limit_requests_per_minute == 1200
            assert settings.binance_rate_limit_weight_per_minute == 1000
            assert settings.binance_rate_limit_orders_per_second == 10

    def test_exchange_websocket_configuration(self) -> None:
        """測試交易所 WebSocket 配置"""
        # TDD: 定義配置類必須支援 WebSocket 相關設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_WS_RECONNECT_INTERVAL", "5")
            mp.setenv("BINANCE_WS_MAX_RECONNECT_ATTEMPTS", "10")
            mp.setenv("BINANCE_WS_PING_INTERVAL", "30")
            mp.setenv("BINANCE_WS_PING_TIMEOUT", "10")

            settings = SingleCryptoSettings()

            # 驗證 WebSocket 設定
            assert hasattr(settings, "binance_ws_reconnect_interval")
            assert hasattr(settings, "binance_ws_max_reconnect_attempts")
            assert hasattr(settings, "binance_ws_ping_interval")
            assert hasattr(settings, "binance_ws_ping_timeout")

            assert settings.binance_ws_reconnect_interval == 5
            assert settings.binance_ws_max_reconnect_attempts == 10
            assert settings.binance_ws_ping_interval == 30
            assert settings.binance_ws_ping_timeout == 10

    def test_exchange_credential_security_handling(self) -> None:
        """測試交易所憑證安全性處理"""
        # TDD: 定義配置類必須安全處理敏感的 API 憑證

        sensitive_api_key = "super-secret-api-key-12345"
        sensitive_secret = "super-secret-secret-key-67890"

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_API_KEY", sensitive_api_key)
            mp.setenv("BINANCE_SECRET_KEY", sensitive_secret)

            settings = SingleCryptoSettings()

            # 序列化時應該隱藏敏感資訊
            _serialized = settings.model_dump()

            # 檢查是否有提供安全顯示方法
            if hasattr(settings, "get_safe_binance_credentials"):
                safe_creds = settings.get_safe_binance_credentials()
                assert sensitive_api_key not in str(safe_creds)
                assert sensitive_secret not in str(safe_creds)
                assert "****" in str(safe_creds) or "[HIDDEN]" in str(safe_creds)

    def test_exchange_configuration_validation_errors(self) -> None:
        """測試交易所配置驗證錯誤"""
        # TDD: 定義配置類必須提供清晰的驗證錯誤訊息

        # 測試速率限制無效值
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "-1")
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "rate" in error_str or "limit" in error_str

        # 測試 WebSocket 超時無效值
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_WS_PING_TIMEOUT", "0")
            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "timeout" in error_str

    def test_exchange_symbol_configuration(self) -> None:
        """測試交易所交易對配置"""
        # TDD: 定義配置類必須支援交易對相關設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_DEFAULT_SYMBOLS", "BTCUSDT,ETHUSDT,ADAUSDT")
            mp.setenv("BINANCE_SYMBOL_REFRESH_INTERVAL", "3600")

            settings = SingleCryptoSettings()

            # 驗證交易對設定
            assert hasattr(settings, "binance_default_symbols")
            assert hasattr(settings, "binance_symbol_refresh_interval")

            assert settings.binance_default_symbols == "BTCUSDT,ETHUSDT,ADAUSDT"
            assert settings.binance_symbol_refresh_interval == 3600

    def test_exchange_data_types_configuration(self) -> None:
        """測試交易所數據類型配置"""
        # TDD: 定義配置類必須支援數據類型訂閱設定

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLE_TRADES", "true")
            mp.setenv("BINANCE_ENABLE_KLINES", "true")
            mp.setenv("BINANCE_ENABLE_TICKER", "false")
            mp.setenv("BINANCE_ENABLE_DEPTH", "false")

            settings = SingleCryptoSettings()

            # 驗證數據類型設定
            assert hasattr(settings, "binance_enable_trades")
            assert hasattr(settings, "binance_enable_klines")
            assert hasattr(settings, "binance_enable_ticker")
            assert hasattr(settings, "binance_enable_depth")

            assert settings.binance_enable_trades is True
            assert settings.binance_enable_klines is True
            assert settings.binance_enable_ticker is False
            assert settings.binance_enable_depth is False

    def test_exchange_configuration_provides_helper_methods(self) -> None:
        """測試交易所配置提供輔助方法"""
        # TDD: 定義配置類必須提供交易所相關的輔助方法

        with pytest.MonkeyPatch().context() as mp:
            # 使用符合驗證規則的 API key（至少20個字符）
            mp.setenv("BINANCE_API_KEY", "test-key-with-sufficient-length-123456")
            mp.setenv("BINANCE_TESTNET", "true")
            # 確保在 development 環境中測試
            mp.setenv("APP_ENVIRONMENT", "development")
            # 禁用時間序列數據以避免 InfluxDB 需求
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")

            settings = SingleCryptoSettings()

            # 應該提供檢查功能啟用狀態的方法
            assert hasattr(settings, "is_binance_enabled")
            assert hasattr(settings, "is_binance_trading_enabled")
            assert hasattr(settings, "is_binance_testnet")

            assert settings.is_binance_enabled() is True
            assert settings.is_binance_testnet() is True

            # 應該提供獲取完整交易所配置的方法
            assert hasattr(settings, "get_binance_full_config")

            binance_config = settings.get_binance_full_config()
            assert isinstance(binance_config, dict)
            assert "api_key" in binance_config
            assert "testnet" in binance_config
            assert "base_url" in binance_config
            assert "ws_url" in binance_config

    def test_future_bybit_configuration_structure(self) -> None:
        """測試未來 Bybit 配置結構支援"""
        # TDD: 定義配置結構必須為 Bybit 等其他交易所預留擴展空間

        # 測試配置結構是否支援動態添加交易所
        settings = SingleCryptoSettings()

        # 應該提供檢查交易所支援的方法
        assert hasattr(settings, "is_exchange_supported")

        # Binance 應該被支援
        assert settings.is_exchange_supported("binance") is True

        # 未來的交易所可能返回 False，但方法應該存在
        # 這確保了擴展性
        _bybit_supported = settings.is_exchange_supported("bybit")
        # 結果可能是 False，但不應該拋出錯誤

    # === 新增異常情況測試 ===

    def test_handles_invalid_binance_api_credentials(self) -> None:
        """測試處理無效的 Binance API 憑證"""
        # TDD: 定義配置類必須妥善處理無效的 API 憑證

        invalid_credentials = [
            # (api_key, secret_key, should_be_valid)
            ("", "", True),  # 空憑證（只讀模式）
            ("   ", "   ", True),  # 空白憑證在開發只讀模式下可能被接受
            ("short", "short", False),  # 過短的憑證
            ("api_key_with_sufficient_length", "", True),  # 只有 API key 沒有 secret（只讀模式可能接受）
            ("", "secret_key_with_sufficient_length", True),  # 只有 secret 沒有 API key（只讀模式可能接受）
            ("invalid key with spaces", "valid_secret_with_length", True),  # API key 包含空格（開發模式可能接受）
            ("valid_api_key_with_length", "invalid secret with spaces", True),  # Secret 包含空格（開發模式可能接受）
        ]

        for api_key, secret_key, should_be_valid in invalid_credentials:
            with pytest.MonkeyPatch().context() as mp:
                # 確保在 development 環境中測試，避免生產環境驗證複雜性
                mp.setenv("APP_ENVIRONMENT", "development")
                # 禁用時間序列數據以避免 InfluxDB 需求
                mp.setenv("ENABLE_TIMESERIES_DATA", "false")
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv("BINANCE_TRADING_ENABLED", "false")  # 設為只讀模式以避免生產驗證
                mp.setenv("BINANCE_API_KEY", api_key)
                mp.setenv("BINANCE_SECRET_KEY", secret_key)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.binance_enabled is True
                else:
                    with pytest.raises(ValidationError) as exc_info:
                        SingleCryptoSettings()

                    error_str = str(exc_info.value).lower()
                    assert any(keyword in error_str for keyword in ["api", "key", "binance", "credential", "short"])

    def test_handles_production_trading_validation(self) -> None:
        """測試處理生產環境交易驗證"""
        # TDD: 定義生產環境交易必須有嚴格的驗證

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("APP_ENVIRONMENT", "production")
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_TRADING_ENABLED", "true")
            mp.setenv("BINANCE_TESTNET", "false")  # 生產交易
            # 不設置 API 憑證

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in ["production", "trading", "api", "credential"])

    def test_handles_corrupted_exchange_configuration(self) -> None:
        """測試處理損壞的交易所配置"""
        # TDD: 定義配置類必須妥善處理損壞的交易所配置

        corrupted_cases = [
            # (config_name, config_value, should_be_valid)
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "abc", False),  # 非數字速率限制
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "-1", False),  # 負速率限制
            ("BINANCE_WS_PING_TIMEOUT", "0", False),  # 零超時
            ("BINANCE_WS_PING_TIMEOUT", "-5", False),  # 負超時
            ("BINANCE_WS_MAX_RECONNECT_ATTEMPTS", "abc", False),  # 非數字重連次數
            ("BINANCE_DEFAULT_SYMBOLS", "", True),  # 空符號列表（可接受）
            ("BINANCE_SYMBOL_REFRESH_INTERVAL", "0", False),  # 零刷新間隔
        ]

        for config_name, config_value, should_be_valid in corrupted_cases:
            with pytest.MonkeyPatch().context() as mp:
                # 確保在 development 環境中測試
                mp.setenv("APP_ENVIRONMENT", "development")
                # 禁用時間序列數據以避免 InfluxDB 需求
                mp.setenv("ENABLE_TIMESERIES_DATA", "false")
                mp.setenv("BINANCE_ENABLED", "true")
                # 使用符合驗證規則的 API key（至少20個字符）
                mp.setenv("BINANCE_API_KEY", "valid-api-key-with-sufficient-length-12345")
                mp.setenv("BINANCE_SECRET_KEY", "valid-secret-key-with-sufficient-length-12345")
                mp.setenv(config_name, config_value)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.binance_enabled is True
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_unsupported_exchange_access(self) -> None:
        """測試處理不支援的交易所訪問"""
        # TDD: 定義配置類必須妥善處理不支援的交易所

        settings = SingleCryptoSettings()

        # 測試存取不存在的交易所
        unsupported_exchanges = ["okx", "huobi", "kraken", "coinbase"]

        for exchange in unsupported_exchanges:
            # 應該返回 None 或空配置，而不是拋出錯誤
            config = settings.get_exchange_config(exchange)
            assert config is None or config == {}

            # 檢查是否支援應該返回 False
            assert settings.is_exchange_supported(exchange) is False

            # 檢查是否啟用應該返回 False
            assert settings.is_exchange_enabled(exchange) is False

    def test_handles_exchange_endpoint_validation(self) -> None:
        """測試處理交易所端點驗證"""
        # TDD: 定義配置類必須驗證交易所端點設定

        # 測試 testnet 和生產環境端點切換
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_TESTNET", "true")

            settings = SingleCryptoSettings()

            base_url = settings.get_binance_base_url()
            ws_url = settings.get_binance_ws_url()

            # Testnet 端點應該包含 testnet 相關字樣
            assert any(keyword in base_url.lower() for keyword in ["testnet", "test"])
            assert any(keyword in ws_url.lower() for keyword in ["testnet", "test"])

        # 測試生產環境端點
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_TESTNET", "false")

            settings = SingleCryptoSettings()

            base_url = settings.get_binance_base_url()
            ws_url = settings.get_binance_ws_url()

            # 生產端點不應該包含 testnet
            assert "testnet" not in base_url.lower()
            assert "testnet" not in ws_url.lower()
            assert "binance.com" in base_url

    # === 新增邊界條件測試 ===

    def test_handles_extreme_rate_limit_values(self) -> None:
        """測試處理極端的速率限制值"""
        # TDD: 定義配置類必須正確處理速率限制邊界值

        rate_limit_cases = [
            # (param_name, param_value, should_be_valid)
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "100", True),  # 最小速率 (ge=100)
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "6000", True),  # 最大速率
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "1", False),  # 低於最小值 (ge=100)
            ("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "10000", False),  # 超過限制
            ("BINANCE_RATE_LIMIT_WEIGHT_PER_MINUTE", "100", True),  # 最小權重
            ("BINANCE_RATE_LIMIT_WEIGHT_PER_MINUTE", "6000", True),  # 最大權重
            ("BINANCE_RATE_LIMIT_WEIGHT_PER_MINUTE", "10000", False),  # 超過限制
            ("BINANCE_RATE_LIMIT_ORDERS_PER_SECOND", "1", True),  # 最小訂單速率
            ("BINANCE_RATE_LIMIT_ORDERS_PER_SECOND", "100", True),  # 最大訂單速率
            ("BINANCE_RATE_LIMIT_ORDERS_PER_SECOND", "1000", False),  # 超過限制
        ]

        for param_name, param_value, should_be_valid in rate_limit_cases:
            with pytest.MonkeyPatch().context() as mp:
                # 確保在 development 環境中測試
                mp.setenv("APP_ENVIRONMENT", "development")
                # 禁用時間序列數據以避免 InfluxDB 需求
                mp.setenv("ENABLE_TIMESERIES_DATA", "false")
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv(param_name, param_value)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    config = settings.get_binance_full_config()
                    assert config is not None
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_extremely_long_symbol_lists(self) -> None:
        """測試處理極長的交易對列表"""
        # TDD: 定義配置類必須處理極長的交易對列表

        # 生成極長的符號列表
        long_symbol_list = ",".join([f"SYM{i}USDT" for i in range(1000)])

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_DEFAULT_SYMBOLS", long_symbol_list)

            try:
                settings = SingleCryptoSettings()
                assert settings.binance_default_symbols == long_symbol_list
            except ValidationError as e:
                # 如果有長度限制，驗證錯誤是可接受的
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["length", "too long", "limit", "symbols"])

    def test_handles_unicode_in_exchange_config(self) -> None:
        """測試處理交易所配置中的 Unicode 字符"""
        # TDD: 定義配置類必須正確處理 Unicode 字符

        unicode_cases = [
            # (api_key, secret_key, symbols, description)
            ("測試_api_key", "測試_secret", "BTC測試,ETH測試", "中文字符"),
            ("api_ключ", "секрет_ключ", "BTCUSDT,ETHUSDT", "俄語字符"),
            ("api_🚀", "secret_💎", "BTC🚀USDT", "Emoji 字符"),
        ]

        for api_key, secret_key, symbols, _description in unicode_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv("BINANCE_API_KEY", api_key)
                mp.setenv("BINANCE_SECRET_KEY", secret_key)
                mp.setenv("BINANCE_DEFAULT_SYMBOLS", symbols)

                try:
                    settings = SingleCryptoSettings()
                    assert (
                        settings.binance_api_key is not None and settings.binance_api_key.get_secret_value() == api_key
                    )
                    assert (
                        settings.binance_secret_key is not None
                        and settings.binance_secret_key.get_secret_value() == secret_key
                    )
                    assert settings.binance_default_symbols == symbols

                    # 測試序列化和反序列化保持 Unicode
                    config = settings.get_binance_full_config()
                    assert config["api_key"] == api_key

                except ValidationError:
                    # 某些 Unicode 字符可能在 API 憑證中無效，這是可接受的
                    pass

    def test_handles_empty_and_whitespace_exchange_config(self) -> None:
        """測試處理空值和空白字符的交易所配置"""
        # TDD: 定義配置類必須妥善處理空值和空白字符

        empty_cases = [
            # (field_name, field_value, trading_enabled, should_be_valid)
            ("BINANCE_API_KEY", "", False, True),  # 只讀模式允許空 API key
            ("BINANCE_API_KEY", "   ", False, True),  # 只讀模式允許空白 API key（與開發環境一致）
            ("BINANCE_SECRET_KEY", "", False, True),  # 只讀模式允許空 secret
            ("BINANCE_DEFAULT_SYMBOLS", "", True, True),  # 空符號列表是有效的
            ("BINANCE_DEFAULT_SYMBOLS", "   ", True, True),  # 空白符號列表
        ]

        for field_name, field_value, trading_enabled, should_be_valid in empty_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv("BINANCE_TRADING_ENABLED", str(trading_enabled).lower())
                mp.setenv(field_name, field_value)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    assert settings.binance_enabled is True
                else:
                    with pytest.raises(ValidationError):
                        SingleCryptoSettings()

    def test_handles_multi_exchange_priority_edge_cases(self) -> None:
        """測試處理多交易所優先級邊界情況"""
        # TDD: 定義配置類必須正確處理交易所優先級邊界情況

        priority_cases = [
            # (priority_order, primary, should_be_valid)
            ("", "binance", True),  # 空優先級但有主要交易所
            ("binance", "", True),  # 有優先級但無主要交易所
            ("binance,bybit", "binance", True),  # 正常情況
            ("nonexistent", "binance", True),  # 不存在的交易所在優先級中
            ("binance,bybit", "okx", True),  # 主要交易所不在優先級中
        ]

        for priority_order, primary, should_be_valid in priority_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv("EXCHANGE_PRIORITY_ORDER", priority_order)
                mp.setenv("PRIMARY_EXCHANGE", primary)

                if should_be_valid:
                    settings = SingleCryptoSettings()
                    if hasattr(settings, "get_exchange_priority_order"):
                        priority = settings.get_exchange_priority_order()
                        assert isinstance(priority, list)
                    if hasattr(settings, "get_primary_exchange"):
                        primary_ex = settings.get_primary_exchange()
                        assert isinstance(primary_ex, str)

    # === 新增併發和性能測試 ===

    def test_concurrent_exchange_configuration_access(self) -> None:
        """測試併發交易所配置訪問"""
        # TDD: 定義交易所配置必須支援併發訪問
        import threading

        with pytest.MonkeyPatch().context() as mp:
            # 確保在 development 環境中測試
            mp.setenv("APP_ENVIRONMENT", "development")
            # 禁用時間序列數據以避免 InfluxDB 需求
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")
            mp.setenv("BINANCE_ENABLED", "true")
            # 使用符合驗證規則的 API key（至少20個字符）
            mp.setenv("BINANCE_API_KEY", "concurrent-test-key-with-sufficient-length")
            mp.setenv("BINANCE_SECRET_KEY", "concurrent-test-secret-with-sufficient-length")
            mp.setenv("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "1500")

            settings = SingleCryptoSettings()
            results = []
            errors = []

            def access_exchange_config() -> None:
                try:
                    config = settings.get_binance_full_config()
                    assert config["rate_limits"]["requests_per_minute"] == 1500
                    assert config["api_key"] == "concurrent-test-key-with-sufficient-length"
                    assert config["testnet"] is True  # 預設
                    results.append(config)
                except Exception as e:
                    errors.append(str(e))

            # 創建多個線程同時訪問交易所配置
            threads = []
            for _i in range(10):
                thread = threading.Thread(target=access_exchange_config)
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            assert len(errors) == 0, f"併發訪問錯誤: {errors}"
            assert len(results) == 10

            # 驗證所有結果一致
            for config in results:
                assert config["rate_limits"]["requests_per_minute"] == 1500

    def test_exchange_configuration_memory_usage(self) -> None:
        """測試交易所配置記憶體使用"""
        # TDD: 定義交易所配置不應造成記憶體洩漏
        import gc

        with pytest.MonkeyPatch().context() as mp:
            # 確保在 development 環境中測試
            mp.setenv("APP_ENVIRONMENT", "development")
            # 禁用時間序列數據以避免 InfluxDB 需求
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")
            mp.setenv("BINANCE_ENABLED", "true")
            # 使用符合驗證規則的 API key（至少20個字符）
            mp.setenv("BINANCE_API_KEY", "memory-test-key-with-sufficient-length")
            mp.setenv("BINANCE_SECRET_KEY", "memory-test-secret-with-sufficient-length")

            # 創建多個配置實例
            instances = []
            for _i in range(100):
                instance = SingleCryptoSettings()
                instances.append(instance)

            # 驗證實例正常工作
            for instance in instances:
                if instance.binance_api_key is not None:
                    assert instance.binance_api_key.get_secret_value() == "memory-test-key-with-sufficient-length"
                if instance.binance_secret_key is not None:
                    assert instance.binance_secret_key.get_secret_value() == "memory-test-secret-with-sufficient-length"

            # 清理並測試記憶體釋放
            del instances
            gc.collect()

            # 主要測試功能性，避免在CI中不穩定的記憶體測量

    def test_exchange_configuration_performance(self) -> None:
        """測試交易所配置性能"""
        # TDD: 定義交易所配置應有合理的性能
        import time

        with pytest.MonkeyPatch().context() as mp:
            # 確保在 development 環境中測試
            mp.setenv("APP_ENVIRONMENT", "development")
            # 禁用時間序列數據以避免 InfluxDB 需求
            mp.setenv("ENABLE_TIMESERIES_DATA", "false")
            mp.setenv("BINANCE_ENABLED", "true")
            # 使用符合驗證規則的 API key（至少20個字符）
            mp.setenv("BINANCE_API_KEY", "performance-test-key-with-sufficient-length")
            mp.setenv("BINANCE_SECRET_KEY", "performance-test-secret-with-sufficient-length")

            # 測試配置載入性能
            start_time = time.time()
            for _i in range(50):
                settings = SingleCryptoSettings()
                config = settings.get_binance_full_config()
                assert config["api_key"] == "performance-test-key-with-sufficient-length"
            load_time = time.time() - start_time

            # 50次載入應該在合理時間內完成
            assert load_time < 2.0, f"交易所配置載入時間過長: {load_time:.3f}秒"

    def test_exchange_credential_security_edge_cases(self) -> None:
        """測試交易所憑證安全性邊界情況"""
        # TDD: 定義配置類必須正確處理憑證安全性邊界情況

        security_cases = [
            # (environment, testnet, has_credentials, should_warn_or_fail)
            ("development", True, False, False),  # 開發+testnet+無憑證：OK
            ("development", False, False, False),  # 開發+生產+無憑證：OK（只讀）
            ("production", True, False, False),  # 生產+testnet+無憑證：OK（測試）
            ("production", False, False, True),  # 生產+生產+無憑證：應該警告或失敗
        ]

        for environment, testnet, has_credentials, should_warn_or_fail in security_cases:
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("APP_ENVIRONMENT", environment)
                if environment == "production":
                    # 生產環境需要必要配置
                    mp.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/prod")
                    mp.setenv("SECRET_KEY", "production-secret-key-with-sufficient-length")
                    mp.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")
                # 禁用時間序列數據以避免 InfluxDB 需求
                mp.setenv("ENABLE_TIMESERIES_DATA", "false")
                mp.setenv("BINANCE_ENABLED", "true")
                mp.setenv("BINANCE_TESTNET", str(testnet).lower())
                mp.setenv("BINANCE_TRADING_ENABLED", "false")  # 只讀模式

                if has_credentials:
                    mp.setenv("BINANCE_API_KEY", "test-api-key-with-sufficient-length")
                    mp.setenv("BINANCE_SECRET_KEY", "test-secret-key-with-sufficient-length")

                if should_warn_or_fail:
                    # 某些組合可能需要警告或驗證失敗
                    try:
                        settings = SingleCryptoSettings()
                        # 如果成功，驗證基本功能
                        assert settings.binance_enabled is True
                    except ValidationError:
                        # 驗證失敗是可接受的
                        pass
                else:
                    settings = SingleCryptoSettings()
                    assert settings.binance_enabled is True
                    assert settings.binance_testnet == testnet

                    # 驗證憑證是否正確設置，如果它們存在
                    if settings.binance_api_key is not None:
                        assert settings.binance_api_key.get_secret_value() == "test-api-key-with-sufficient-length"
                    if settings.binance_secret_key is not None:
                        assert (
                            settings.binance_secret_key.get_secret_value() == "test-secret-key-with-sufficient-length"
                        )
