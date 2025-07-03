"""Unified configuration tests for asset_core.

This module consolidates all configuration tests to address the issues identified
in the missing_tests.md analysis:
- Redundant, incomplete, and flawed configuration tests
- Missing environment variable and .env file testing
- Missing strict type validation
- Missing cross-field business logic validation
- Missing unified string choice field validation
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from asset_core.config import BaseNetworkConfig, BaseObservabilityConfig, \
    BaseStorageConfig
from asset_core.config.base import BaseCoreSettings


@pytest.mark.unit
class TestConfigurationHierarchy:
    """Test configuration loading hierarchy: constructor > env vars > .env file > defaults."""

    def test_constructor_overrides_all(self) -> None:
        """Test that constructor arguments have highest precedence."""
        env_content = """
        APP_NAME=env-file-app
        ENVIRONMENT=staging
        DEBUG=true
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                with patch.dict(os.environ, {"APP_NAME": "env-var-app", "ENVIRONMENT": "production"}):
                    settings = BaseCoreSettings(app_name="constructor-app", environment="development", debug=False)

                    # Constructor should override everything
                    assert settings.app_name == "constructor-app"
                    assert settings.environment == "development"
                    assert settings.debug is False

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_env_vars_override_env_file(self) -> None:
        """Test that environment variables override .env file."""
        env_content = """
        APP_NAME=env-file-app
        ENVIRONMENT=staging
        DEBUG=false
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                with patch.dict(os.environ, {"APP_NAME": "env-var-app", "DEBUG": "true"}):
                    settings = BaseCoreSettings()

                    # Env vars should override .env file
                    assert settings.app_name == "env-var-app"  # From env var
                    assert settings.environment == "staging"  # From .env file
                    assert settings.debug is True  # From env var

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_env_file_overrides_defaults(self) -> None:
        """Test that .env file overrides model defaults."""
        env_content = """
        APP_NAME=env-file-app
        ENVIRONMENT=production
        DEBUG=true
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                settings = BaseCoreSettings()

                # .env file should override defaults
                assert settings.app_name == "env-file-app"
                assert settings.environment == "production"
                assert settings.debug is True

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_defaults_when_no_overrides(self) -> None:
        """Test that defaults are used when no overrides are present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                settings = BaseCoreSettings()

                # Should use defaults
                assert settings.app_name == "asset-core"
                assert settings.environment == "development"
                assert settings.debug is False

            finally:
                os.chdir(original_cwd)


@pytest.mark.unit
class TestStrictTypeValidation:
    """Test strict type validation for configuration fields."""

    def test_invalid_boolean_string_in_env_var(self) -> None:
        """Test that invalid boolean strings in env vars raise ValidationError."""
        with patch.dict(os.environ, {"DEBUG": "not-a-boolean"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings()

            # Should contain validation error for debug field
            errors = exc_info.value.errors()
            assert any(error["loc"] == ("debug",) for error in errors)

    def test_invalid_integer_string_in_env_var(self) -> None:
        """Test that invalid integer strings in env vars raise ValidationError."""
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "not-an-integer"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseNetworkConfig()

            # Should contain validation error for ws_reconnect_interval field
            errors = exc_info.value.errors()
            assert any(error["loc"] == ("ws_reconnect_interval",) for error in errors)

    def test_boolean_conversion_from_env_vars(self) -> None:
        """Test proper boolean conversion from various env var formats."""
        # Test various true representations
        for true_val in ["true", "True", "TRUE", "1", "yes", "on"]:
            with patch.dict(os.environ, {"DEBUG": true_val}):
                settings = BaseCoreSettings()
                assert settings.debug is True

        # Test various false representations
        for false_val in ["false", "False", "FALSE", "0", "no", "off"]:
            with patch.dict(os.environ, {"DEBUG": false_val}):
                settings = BaseCoreSettings()
                assert settings.debug is False

    def test_integer_conversion_from_env_vars(self) -> None:
        """Test proper integer conversion from env vars."""
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "15"}):
            config = BaseNetworkConfig()
            assert config.ws_reconnect_interval == 15

        with patch.dict(os.environ, {"WS_MAX_RECONNECT_ATTEMPTS": "-1"}):
            config = BaseNetworkConfig()
            assert config.ws_max_reconnect_attempts == -1

    def test_none_values_rejected(self) -> None:
        """Test that None values are rejected for typed fields."""
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(app_name=None, environment=None, debug=None)

        errors = exc_info.value.errors()
        assert len(errors) == 3
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"app_name", "environment", "debug"}

    def test_wrong_type_values_rejected(self) -> None:
        """Test that wrong type values are rejected."""
        with pytest.raises(ValidationError):
            BaseCoreSettings(debug="not-a-boolean")

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval="not-an-integer")


@pytest.mark.unit
class TestCrossFieldBusinessLogicValidation:
    """Test cross-field business logic validation."""

    def test_network_config_ping_timeout_validation(self) -> None:
        """Test that ping_timeout must be less than ping_interval when ping is enabled."""
        # Valid case: ping_timeout < ping_interval
        config = BaseNetworkConfig(ws_ping_interval=30, ws_ping_timeout=10)
        assert config.ws_ping_timeout < config.ws_ping_interval

        # Invalid case: ping_timeout >= ping_interval should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=15)

        assert "ws_ping_timeout must be less than ws_ping_interval when ping is enabled" in str(exc_info.value)

        # Edge case: ping_timeout == ping_interval should also fail
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=10)

    def test_network_config_zero_ping_interval_disables_ping(self) -> None:
        """Test that zero ping_interval disables ping functionality."""
        config = BaseNetworkConfig(ws_ping_interval=0, ws_ping_timeout=10)
        assert config.ws_ping_interval == 0
        # When ping is disabled, timeout value becomes irrelevant

    def test_network_config_unlimited_reconnect_attempts(self) -> None:
        """Test that -1 means unlimited reconnect attempts."""
        config = BaseNetworkConfig(ws_max_reconnect_attempts=-1)
        assert config.ws_max_reconnect_attempts == -1

    def test_network_config_negative_values_validation(self) -> None:
        """Test that negative values are properly validated."""
        # Valid negative value for unlimited attempts
        config = BaseNetworkConfig(ws_max_reconnect_attempts=-1)
        assert config.ws_max_reconnect_attempts == -1

        # Invalid negative values for other fields
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout=-1)


@pytest.mark.unit
class TestStringChoiceFieldValidation:
    """Test unified string choice field validation."""

    def test_environment_case_insensitive_validation(self) -> None:
        """Test that environment validation is case insensitive."""
        # Test all valid environments with different cases
        valid_envs = [
            ("development", "development"),
            ("DEVELOPMENT", "development"),
            ("Development", "development"),
            ("staging", "staging"),
            ("STAGING", "staging"),
            ("Staging", "staging"),
            ("production", "production"),
            ("PRODUCTION", "production"),
            ("Production", "production"),
        ]

        for input_env, expected_env in valid_envs:
            settings = BaseCoreSettings(environment=input_env)
            assert settings.environment == expected_env

    def test_environment_invalid_values_rejected(self) -> None:
        """Test that invalid environment values are rejected."""
        invalid_envs = ["invalid", "test", "dev", "prod", "stage", ""]

        for invalid_env in invalid_envs:
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings(environment=invalid_env)

            error_msg = str(exc_info.value)
            assert "environment must be one of" in error_msg
            assert "development" in error_msg
            assert "staging" in error_msg
            assert "production" in error_msg

    def test_log_level_case_insensitive_validation(self) -> None:
        """Test that log_level validation is case insensitive."""
        # Test various log levels with different cases
        valid_levels = [
            ("DEBUG", "DEBUG"),
            ("debug", "DEBUG"),
            ("Info", "INFO"),
            ("warning", "WARNING"),
            ("ERROR", "ERROR"),
        ]

        for input_level, expected_level in valid_levels:
            config = BaseObservabilityConfig(log_level=input_level)
            assert config.log_level == expected_level

    def test_log_format_case_insensitive_validation(self) -> None:
        """Test that log_format validation is case insensitive."""
        valid_formats = [
            ("json", "json"),
            ("JSON", "json"),
            ("Json", "json"),
            ("text", "text"),
            ("TEXT", "text"),
            ("Text", "text"),
        ]

        for input_format, expected_format in valid_formats:
            config = BaseObservabilityConfig(log_format=input_format)
            assert config.log_format == expected_format

        # Invalid formats should still be rejected
        invalid_formats = ["xml", "yaml", "invalid"]
        for invalid_format in invalid_formats:
            with pytest.raises(ValidationError):
                BaseObservabilityConfig(log_format=invalid_format)


@pytest.mark.unit
class TestConfigurationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_values(self) -> None:
        """Test handling of empty string values."""
        # Empty app_name should be allowed
        settings = BaseCoreSettings(app_name="")
        assert settings.app_name == ""

        # Empty environment should be rejected
        with pytest.raises(ValidationError):
            BaseCoreSettings(environment="")

    def test_whitespace_handling(self) -> None:
        """Test whitespace handling in configuration values."""
        # Test whitespace preservation for app_name
        settings = BaseCoreSettings(app_name="  test-app  ")
        assert settings.app_name == "  test-app  "

        # Network config has str_strip_whitespace=True but no string fields to test
        # This is documented behavior for network configuration

    def test_unicode_values(self) -> None:
        """Test handling of unicode values."""
        settings = BaseCoreSettings(app_name="测试应用")
        assert settings.app_name == "测试应用"

    def test_very_large_numeric_values(self) -> None:
        """Test handling of very large numeric values."""
        # Test large but valid values
        config = BaseNetworkConfig(
            ws_reconnect_interval=86400,  # 24 hours
            ws_max_reconnect_attempts=999999,
            ws_ping_interval=3600,  # 1 hour
            ws_ping_timeout=300,  # 5 minutes
        )
        assert config.ws_reconnect_interval == 86400
        assert config.ws_max_reconnect_attempts == 999999
        assert config.ws_ping_interval == 3600
        assert config.ws_ping_timeout == 300

    def test_zero_boundary_values(self) -> None:
        """Test zero boundary values."""
        # Zero should be valid for most fields
        config = BaseNetworkConfig(ws_reconnect_interval=0, ws_ping_interval=0, ws_ping_timeout=0)
        assert config.ws_reconnect_interval == 0
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 0


@pytest.mark.unit
class TestEnvironmentVariableNames:
    """Test environment variable name resolution."""

    def test_case_insensitive_env_var_names(self) -> None:
        """Test that environment variable names are case insensitive."""
        # Test various case combinations
        test_cases = [
            ("APP_NAME", "app_name", "test-app"),
            ("app_name", "app_name", "test-app"),
            ("App_Name", "app_name", "test-app"),
            ("ENVIRONMENT", "environment", "production"),
            ("environment", "environment", "production"),
            ("DEBUG", "debug", "true"),
            ("debug", "debug", "true"),
        ]

        for env_var, field_name, value in test_cases:
            with patch.dict(os.environ, {env_var: value}):
                settings = BaseCoreSettings()
                if field_name == "debug":
                    assert getattr(settings, field_name) is True
                else:
                    expected_value = value.lower() if field_name == "environment" else value
                    assert getattr(settings, field_name) == expected_value

    def test_env_var_prefix_handling(self) -> None:
        """Test environment variable prefix handling."""
        # Test that env vars without prefix work
        with patch.dict(os.environ, {"APP_NAME": "test-app"}):
            settings = BaseCoreSettings()
            assert settings.app_name == "test-app"


@pytest.mark.unit
class TestConfigurationSerialization:
    """Test configuration serialization and representation."""

    def test_model_dump_includes_all_fields(self) -> None:
        """Test that model_dump includes all configuration fields."""
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        data = settings.model_dump()

        assert isinstance(data, dict)
        assert "app_name" in data
        assert "environment" in data
        assert "debug" in data
        assert data["app_name"] == "test-app"
        assert data["environment"] == "production"
        assert data["debug"] is True

    def test_model_dump_excludes_sensitive_fields(self) -> None:
        """Test that sensitive fields can be excluded from serialization."""
        config = BaseStorageConfig(database_url="sqlite:///test.db")

        # Test that we can exclude sensitive fields like database_url
        data = config.model_dump(exclude={"database_url"})

        assert isinstance(data, dict)
        # database_url should be excluded
        assert "database_url" not in data
        assert "database_pool_size" in data  # Other fields should be present

    def test_json_serialization_compatibility(self) -> None:
        """Test that configuration can be serialized to JSON."""
        import json

        settings = BaseCoreSettings()
        data = settings.model_dump()

        # Should be able to serialize to JSON
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed_data = json.loads(json_str)
        assert parsed_data["app_name"] == "asset-core"
        assert parsed_data["environment"] == "development"
        assert parsed_data["debug"] is False

    def test_string_representation_contains_key_info(self) -> None:
        """Test that string representation contains key information."""
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        str_repr = str(settings)

        # Should contain key field values
        assert "test-app" in str_repr
        assert "production" in str_repr
        # Note: debug value representation may vary by Pydantic version


@pytest.mark.unit
class TestConfigurationInheritance:
    """Test configuration inheritance and composition."""

    def test_config_model_settings_inheritance(self) -> None:
        """Test that config model settings are properly inherited."""
        # Test that all config classes have proper model_config
        configs = [
            BaseCoreSettings(),
            BaseNetworkConfig(),
            BaseObservabilityConfig(),
            BaseStorageConfig(database_url="sqlite:///test.db"),
        ]

        for config in configs:
            assert hasattr(config, "model_config")
            # Check that extra configuration is set to ignore
            # model_config can be dict or ConfigDict object
            assert config.model_config.get("extra") == "ignore"

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored during initialization."""
        # Should not raise error due to extra="ignore"
        settings = BaseCoreSettings(app_name="test-app", unknown_field="should-be-ignored", another_unknown=123)

        assert settings.app_name == "test-app"
        assert not hasattr(settings, "unknown_field")
        assert not hasattr(settings, "another_unknown")

    def test_field_descriptions_present(self) -> None:
        """Test that all fields have proper descriptions."""
        # Check that field info includes descriptions
        for _field_name, field_info in BaseCoreSettings.model_fields.items():
            assert field_info.description is not None
            assert len(field_info.description) > 0


@pytest.mark.unit
class TestConfigurationValidationMessages:
    """Test validation error messages are clear and helpful."""

    def test_environment_validation_error_message(self) -> None:
        """Test that environment validation error message is clear."""
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(environment="invalid")

        error_msg = str(exc_info.value)
        assert "environment must be one of" in error_msg
        assert "development" in error_msg
        assert "staging" in error_msg
        assert "production" in error_msg

    def test_numeric_validation_error_message(self) -> None:
        """Test that numeric validation error messages are clear."""
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_reconnect_interval=-5)

        error_msg = str(exc_info.value)
        assert "ws_reconnect_interval" in error_msg

        # Check that the error indicates the constraint violation
        errors = exc_info.value.errors()
        field_error = next(error for error in errors if error["loc"] == ("ws_reconnect_interval",))
        assert "greater than or equal to" in field_error["msg"]

    def test_type_validation_error_message(self) -> None:
        """Test that type validation error messages are clear."""
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(debug="not-a-boolean")

        errors = exc_info.value.errors()
        debug_error = next(error for error in errors if error["loc"] == ("debug",))
        assert "bool" in debug_error["msg"].lower() or "boolean" in debug_error["msg"].lower()
