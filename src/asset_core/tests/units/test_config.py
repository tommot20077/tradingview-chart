"""Tests for configuration models."""

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.config.base import BaseCoreSettings


@pytest.mark.unit
class TestBaseCoreSettings:
    """Test BaseCoreSettings configuration."""

    def test_default_settings(self) -> None:
        """Test default configuration values.

        Validates that BaseCoreSettings creates instance with correct default values.
        Preconditions:
            - BaseCoreSettings class available
        Steps:
            - Create BaseCoreSettings with no parameters
            - Verify default values
        Expected Result:
            - app_name="asset-core", environment="development", debug=False
        """
        settings = BaseCoreSettings()

        assert settings.app_name == "asset-core"
        assert settings.environment == "development"
        assert settings.debug is False

    def test_environment_validation(self) -> None:
        """Test environment validation.

        Validates that only allowed environment values are accepted.
        Preconditions:
            - BaseCoreSettings class available
        Steps:
            - Test valid environments: development, staging, production
            - Test invalid environment value
        Expected Result:
            - Valid environments accepted without error
            - Invalid environment raises ValidationError
        """
        # Valid environments
        for env in ["development", "staging", "production"]:
            settings = BaseCoreSettings(environment=env)
            assert settings.environment == env

        # Invalid environment
        with pytest.raises(ValidationError, match="environment must be one of"):
            BaseCoreSettings(environment="invalid")

    def test_environment_methods(self) -> None:
        """Test environment helper methods.

        Validates environment detection helper methods work correctly.
        Preconditions:
            - BaseCoreSettings class with helper methods available
        Steps:
            - Create settings with different environments
            - Test is_development() and is_production() methods
        Expected Result:
            - development: is_development()=True, is_production()=False
            - production: is_development()=False, is_production()=True
            - staging: is_development()=False, is_production()=False
        """
        dev_settings = BaseCoreSettings(environment="development")
        assert dev_settings.is_development() is True
        assert dev_settings.is_production() is False

        prod_settings = BaseCoreSettings(environment="production")
        assert prod_settings.is_development() is False
        assert prod_settings.is_production() is True

        staging_settings = BaseCoreSettings(environment="staging")
        assert staging_settings.is_development() is False
        assert staging_settings.is_production() is False

    def test_custom_app_name(self) -> None:
        """Test custom app name.

        Validates that custom app_name can be set.
        Preconditions:
            - BaseCoreSettings class available
        Steps:
            - Create BaseCoreSettings with custom app_name
            - Verify app_name is set correctly
        Expected Result:
            - app_name="my-trading-app"
        """
        settings = BaseCoreSettings(app_name="my-trading-app")
        assert settings.app_name == "my-trading-app"

    def test_debug_mode(self) -> None:
        """Test debug mode setting.

        Validates that debug mode can be enabled.
        Preconditions:
            - BaseCoreSettings class available
        Steps:
            - Create BaseCoreSettings with debug=True
            - Verify debug is set correctly
        Expected Result:
            - debug=True
        """
        settings = BaseCoreSettings(debug=True)
        assert settings.debug is True

    def test_case_insensitive_env_vars(self) -> None:
        """
        Test case insensitive environment variables.

        Validates that environment variables are handled case-insensitively.

        Preconditions:
            - BaseCoreSettings class with case insensitive config
        Steps:
            - Create BaseCoreSettings with uppercase ENVIRONMENT
            - Verify value is normalized to lowercase
        Expected Result:
            - ENVIRONMENT="PRODUCTION" => environment="production"
        """
        settings = BaseCoreSettings(environment="PRODUCTION")
        assert settings.environment == "production"
