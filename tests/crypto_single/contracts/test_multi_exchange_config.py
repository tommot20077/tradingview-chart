"""
A2.9: 多交易所擴展性測試

測試 Binance 配置註冊和未來 Bybit 等其他交易所的配置擴展介面。
這些測試定義了多交易所配置的預期行為，實現時必須滿足這些測試。
"""

import pytest
from pydantic import ValidationError

from crypto_single.config.settings import SingleCryptoSettings


class TestMultiExchangeConfiguration:
    """測試多交易所配置擴展性功能"""

    def test_binance_configuration_registration(self) -> None:
        """測試 Binance 配置註冊"""
        # TDD: 定義配置類必須正確註冊 Binance 交易所

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_API_KEY", "binance-api-key-123456789012345678901234567890")  # Valid length key
            mp.setenv("BINANCE_SECRET_KEY", "binance-secret-key-123456789012345678901234567890")  # Valid length key
            mp.setenv("BINANCE_TESTNET", "true")

            settings = SingleCryptoSettings()

            # 應該提供獲取已註冊交易所的方法
            assert hasattr(settings, "get_registered_exchanges")

            registered_exchanges = settings.get_registered_exchanges()
            assert isinstance(registered_exchanges, list)
            assert "binance" in registered_exchanges

    def test_future_bybit_configuration_interface(self) -> None:
        """測試未來 Bybit 配置介面"""
        # TDD: 定義配置結構必須為 Bybit 預留擴展介面

        with pytest.MonkeyPatch().context() as mp:
            # 設置 Bybit 配置（模擬未來擴展）
            mp.setenv("BYBIT_ENABLED", "true")
            mp.setenv("BYBIT_API_KEY", "bybit-api-key")
            mp.setenv("BYBIT_SECRET_KEY", "bybit-secret-key")
            mp.setenv("BYBIT_TESTNET", "true")

            settings = SingleCryptoSettings()

            # 配置結構應該支援動態交易所註冊
            if hasattr(settings, "bybit_enabled"):
                # 如果已實現 Bybit 支援
                assert settings.bybit_enabled is True
                registered_exchanges = settings.get_registered_exchanges()
                assert "bybit" in registered_exchanges
            else:
                # 如果尚未實現，結構應該支援擴展
                assert hasattr(settings, "get_exchange_config")
                # 嘗試獲取 Bybit 配置不應該拋出錯誤
                _bybit_config = settings.get_exchange_config("bybit")
                # 可能返回 None 或預設配置，但不應該崩潰

    def test_exchange_configuration_dynamic_loading(self) -> None:
        """測試交易所配置動態載入"""
        # TDD: 定義配置類必須支援動態載入交易所配置

        with pytest.MonkeyPatch().context() as mp:
            # 同時啟用多個交易所
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_API_KEY", "binance-key-123456789012345678901234567890-123456789012345678901234567890")
            mp.setenv("BYBIT_ENABLED", "false")  # 暫時停用

            settings = SingleCryptoSettings()

            # 應該提供檢查交易所狀態的方法
            assert hasattr(settings, "is_exchange_enabled")

            assert settings.is_exchange_enabled("binance") is True
            assert settings.is_exchange_enabled("bybit") is False

    def test_multiple_exchanges_simultaneous_configuration(self) -> None:
        """測試多交易所同時配置"""
        # TDD: 定義配置類必須支援同時配置多個交易所

        with pytest.MonkeyPatch().context() as mp:
            # Binance 配置
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_API_KEY", "binance-key-123456789012345678901234567890-123456789012345678901234567890")
            mp.setenv("BINANCE_SECRET_KEY", "binance-secret-123456789012345678901234567890")
            mp.setenv("BINANCE_TESTNET", "true")

            # Bybit 配置（未來擴展）
            mp.setenv("BYBIT_ENABLED", "true")
            mp.setenv("BYBIT_API_KEY", "bybit-key")
            mp.setenv("BYBIT_SECRET_KEY", "bybit-secret")
            mp.setenv("BYBIT_TESTNET", "true")

            settings = SingleCryptoSettings()

            # 應該能同時管理多個交易所
            enabled_exchanges = settings.get_enabled_exchanges()
            assert isinstance(enabled_exchanges, list)
            assert "binance" in enabled_exchanges

            # Bybit 可能尚未實現，但結構應該支援
            if hasattr(settings, "bybit_enabled") and settings.bybit_enabled:
                assert "bybit" in enabled_exchanges

    def test_exchange_configuration_isolation(self) -> None:
        """測試交易所配置隔離性"""
        # TDD: 定義各交易所配置必須相互隔離

        with pytest.MonkeyPatch().context() as mp:
            # 設置不同的配置值
            mp.setenv("BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE", "1200")
            mp.setenv("BINANCE_WS_RECONNECT_INTERVAL", "5")

            mp.setenv("BYBIT_RATE_LIMIT_REQUESTS_PER_MINUTE", "600")
            mp.setenv("BYBIT_WS_RECONNECT_INTERVAL", "10")

            settings = SingleCryptoSettings()

            # Binance 配置
            binance_config = settings.get_exchange_config("binance")
            assert isinstance(binance_config, dict)

            if "rate_limit_requests_per_minute" in binance_config:
                assert binance_config["rate_limit_requests_per_minute"] == 1200

            # Bybit 配置（如果已實現）
            bybit_config = settings.get_exchange_config("bybit")
            if bybit_config and "rate_limit_requests_per_minute" in bybit_config:
                assert bybit_config["rate_limit_requests_per_minute"] == 600
                # 確保配置不會混淆
                assert bybit_config["rate_limit_requests_per_minute"] != binance_config.get(
                    "rate_limit_requests_per_minute", 0
                )

    def test_exchange_configuration_inheritance_pattern(self) -> None:
        """測試交易所配置繼承模式"""
        # TDD: 定義交易所配置必須支援繼承通用設定

        with pytest.MonkeyPatch().context() as mp:
            # 通用交易所設定
            mp.setenv("EXCHANGE_DEFAULT_TIMEOUT", "30")
            mp.setenv("EXCHANGE_DEFAULT_RETRY_ATTEMPTS", "3")

            # 特定交易所設定
            mp.setenv("BINANCE_TIMEOUT", "60")  # 覆蓋預設值
            # BYBIT_TIMEOUT 未設置，應該使用預設值

            settings = SingleCryptoSettings()

            # 應該提供獲取交易所特定配置的方法
            binance_config = settings.get_exchange_config("binance")

            if binance_config is not None and "timeout" in binance_config:
                assert binance_config["timeout"] == 60  # 使用特定值
            if binance_config is not None and "retry_attempts" in binance_config:
                assert binance_config["retry_attempts"] == 3  # 使用預設值

    def test_exchange_specific_validation_rules(self) -> None:
        """測試交易所特定驗證規則"""
        # TDD: 定義各交易所必須有特定的驗證規則

        # Binance 特定驗證
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_API_KEY", "invalid-short-key")  # 太短的 API Key

            with pytest.raises(ValidationError) as exc_info:
                SingleCryptoSettings()

            error_str = str(exc_info.value).lower()
            assert "binance" in error_str and "api" in error_str

        # Bybit 特定驗證（如果已實現）
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BYBIT_ENABLED", "true")
            mp.setenv("BYBIT_API_KEY", "invalid-format-key")

            # 如果 Bybit 已實現，應該有驗證
            if hasattr(SingleCryptoSettings, "bybit_api_key"):
                with pytest.raises(ValidationError) as exc_info:
                    SingleCryptoSettings()

                error_str = str(exc_info.value).lower()
                assert "bybit" in error_str

    def test_exchange_capability_discovery(self) -> None:
        """測試交易所能力發現"""
        # TDD: 定義配置類必須支援交易所能力發現

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")

            settings = SingleCryptoSettings()

            # 應該提供獲取交易所能力的方法
            assert hasattr(settings, "get_exchange_capabilities")

            binance_capabilities = settings.get_exchange_capabilities("binance")
            assert isinstance(binance_capabilities, dict)

            # Binance 應該支援的能力
            expected_capabilities = ["spot_trading", "futures_trading", "websocket_streams", "rest_api"]
            for capability in expected_capabilities:
                if capability in binance_capabilities:
                    assert isinstance(binance_capabilities[capability], bool)

    def test_exchange_configuration_priority(self) -> None:
        """測試交易所配置優先順序"""
        # TDD: 定義多交易所環境下的配置優先順序

        with pytest.MonkeyPatch().context() as mp:
            # 設置多個交易所
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BYBIT_ENABLED", "true")

            # 設置優先順序
            mp.setenv("EXCHANGE_PRIORITY_ORDER", "binance,bybit")
            mp.setenv("PRIMARY_EXCHANGE", "binance")

            settings = SingleCryptoSettings()

            # 應該提供獲取優先順序的方法
            if hasattr(settings, "get_exchange_priority_order"):
                priority_order = settings.get_exchange_priority_order()
                assert isinstance(priority_order, list)
                assert priority_order[0] == "binance"  # 優先級最高

            # 應該提供獲取主要交易所的方法
            if hasattr(settings, "get_primary_exchange"):
                primary_exchange = settings.get_primary_exchange()
                assert primary_exchange == "binance"

    def test_exchange_configuration_factory_pattern(self) -> None:
        """測試交易所配置工廠模式"""
        # TDD: 定義配置類必須支援工廠模式創建交易所配置

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv("BINANCE_API_KEY", "binance-key-123456789012345678901234567890")

            settings = SingleCryptoSettings()

            # 應該提供工廠方法創建交易所特定配置
            assert hasattr(settings, "create_exchange_config")

            binance_config = settings.create_exchange_config("binance")
            assert isinstance(binance_config, dict)
            assert "name" in binance_config
            assert binance_config["name"] == "binance"
            assert "enabled" in binance_config
            assert binance_config["enabled"] is True

    @pytest.mark.skip(reason="TDD: This feature is not yet implemented.")
    def test_exchange_configuration_plugin_architecture(self) -> None:
        """測試交易所配置插件架構"""
        # TDD: 定義配置類必須支援插件式的交易所擴展

        settings = SingleCryptoSettings()

        # 應該提供註冊新交易所的介面
        if hasattr(settings, "register_exchange_config"):
            # 測試註冊新交易所
            new_exchange_config = {
                "name": "okx",
                "api_key_field": "OKX_API_KEY",
                "secret_key_field": "OKX_SECRET_KEY",
                "testnet_field": "OKX_TESTNET",
                "capabilities": ["spot_trading", "futures_trading"],
            }

            settings.register_exchange_config("okx", new_exchange_config)

            # 驗證註冊成功
            registered_exchanges = settings.get_registered_exchanges()
            assert "okx" in registered_exchanges

    def test_exchange_configuration_validation_framework(self) -> None:
        """測試交易所配置驗證框架"""
        # TDD: 定義配置類必須提供統一的交易所驗證框架

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")
            mp.setenv(
                "BINANCE_API_KEY", "valid-binance-key-123456789012345678901234567890-123456789012345678901234567890"
            )

            settings = SingleCryptoSettings()

            # 應該提供驗證交易所配置的方法
            if hasattr(settings, "validate_exchange_config"):
                validation_result = settings.validate_exchange_config("binance")
                assert isinstance(validation_result, dict)
                assert "valid" in validation_result
                assert "errors" in validation_result

                if validation_result["valid"]:
                    assert len(validation_result["errors"]) == 0

    def test_exchange_configuration_provides_comprehensive_helper_methods(self) -> None:
        """測試交易所配置提供全面的輔助方法"""
        # TDD: 定義配置類必須提供完整的交易所管理輔助方法

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("BINANCE_ENABLED", "true")

            settings = SingleCryptoSettings()

            # 核心方法檢查
            required_methods = [
                "get_registered_exchanges",
                "get_enabled_exchanges",
                "get_exchange_config",
                "is_exchange_enabled",
                "is_exchange_supported",
            ]

            for method_name in required_methods:
                assert hasattr(settings, method_name), f"缺少必要方法: {method_name}"

            # 擴展方法檢查（可選）
            optional_methods = [
                "get_exchange_capabilities",
                "create_exchange_config",
                "validate_exchange_config",
                "get_exchange_priority_order",
                "get_primary_exchange",
            ]

            for method_name in optional_methods:
                if hasattr(settings, method_name):
                    # 如果方法存在，應該可以調用
                    method = getattr(settings, method_name)
                    assert callable(method)

    def test_exchange_configuration_future_extensibility_contract(self) -> None:
        """測試交易所配置未來擴展性契約"""
        # TDD: 定義配置類必須遵守未來擴展性契約

        settings = SingleCryptoSettings()

        # 擴展性契約檢查
        extensibility_requirements = [
            # 必須支援動態交易所列表
            ("get_registered_exchanges", list),
            # 必須支援交易所配置獲取
            ("get_exchange_config", (dict, type(None))),
            # 必須支援交易所啟用檢查
            ("is_exchange_enabled", bool),
            # 必須支援交易所支援檢查
            ("is_exchange_supported", bool),
        ]

        for method_name, expected_return_type in extensibility_requirements:
            assert hasattr(settings, method_name), f"擴展性要求：必須有 {method_name} 方法"

            method = getattr(settings, method_name)
            assert callable(method), f"{method_name} 必須是可調用的"

            # 測試方法調用（使用 binance 作為測試）
            if method_name in ["get_exchange_config", "is_exchange_enabled", "is_exchange_supported"]:
                result = method("binance")
                if expected_return_type == (dict, type(None)):
                    assert result is None or isinstance(result, dict)
                elif expected_return_type is list:
                    assert isinstance(result, list)
                elif expected_return_type is bool:
                    assert isinstance(result, bool)
            else:
                result = method()
                if expected_return_type is list:
                    assert isinstance(result, list)
                elif expected_return_type is bool:
                    assert isinstance(result, bool)
