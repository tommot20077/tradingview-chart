"""ABOUTME: Consolidated configuration tests for all config modules
ABOUTME: Testing the primary contract of Pydantic Settings models with environmental loading
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
class TestConfigEnvironmentalLoading:
    """Test environmental loading from various sources (constructor > env vars > .env file > defaults)."""

    def test_constructor_overrides_environment_variables(self) -> None:
        """Test that constructor arguments take precedence over environment variables."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "env-app",
                "ENVIRONMENT": "production",
                "DEBUG": "true",
                "WS_RECONNECT_INTERVAL": "15",
                "LOG_LEVEL": "WARNING",
                "METRICS_PORT": "8080",
            },
        ):
            # Constructor should override env vars
            base_settings = BaseCoreSettings(app_name="constructor-app", environment="development", debug=False)

            network_config = BaseNetworkConfig(ws_reconnect_interval=20)

            observability_config = BaseObservabilityConfig(log_level="DEBUG", metrics_port=9090)

            # Verify constructor values win
            assert base_settings.app_name == "constructor-app"
            assert base_settings.environment == "development"
            assert base_settings.debug is False
            assert network_config.ws_reconnect_interval == 20
            assert observability_config.log_level == "DEBUG"
            assert observability_config.metrics_port == 9090

    def test_environment_variables_load_correctly(self) -> None:
        """Test that environment variables are properly loaded and converted."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "env-test-app",
                "ENVIRONMENT": "staging",
                "DEBUG": "true",
                "WS_RECONNECT_INTERVAL": "25",
                "WS_MAX_RECONNECT_ATTEMPTS": "-1",
                "WS_PING_INTERVAL": "45",
                "WS_PING_TIMEOUT": "15",
                "LOG_LEVEL": "error",
                "LOG_FORMAT": "TEXT",
                "METRICS_ENABLED": "false",
                "METRICS_PORT": "8090",
            },
        ):
            base_settings = BaseCoreSettings()
            network_config = BaseNetworkConfig()
            observability_config = BaseObservabilityConfig()

            # Verify environment variables are loaded and converted
            assert base_settings.app_name == "env-test-app"
            assert base_settings.environment == "staging"
            assert base_settings.debug is True
            assert network_config.ws_reconnect_interval == 25
            assert network_config.ws_max_reconnect_attempts == -1
            assert network_config.ws_ping_interval == 45
            assert network_config.ws_ping_timeout == 15
            assert observability_config.log_level == "ERROR"
            assert observability_config.log_format == "text"
            assert observability_config.metrics_enabled is False
            assert observability_config.metrics_port == 8090

    def test_env_file_loading_with_defaults(self) -> None:
        """Test that .env file values override defaults when no other overrides are present."""
        env_content = """
        APP_NAME=env-file-app
        ENVIRONMENT=production
        DEBUG=true
        WS_RECONNECT_INTERVAL=30
        LOG_LEVEL=WARNING
        METRICS_PORT=7090
        DATABASE_URL=sqlite:///env_test.db
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

                # Load configs without any overrides
                base_settings = BaseCoreSettings()
                network_config = BaseNetworkConfig()
                observability_config = BaseObservabilityConfig()
                storage_config = BaseStorageConfig()

                # Verify .env file values are loaded
                assert base_settings.app_name == "env-file-app"
                assert base_settings.environment == "production"
                assert base_settings.debug is True
                assert network_config.ws_reconnect_interval == 30
                assert observability_config.log_level == "WARNING"
                assert observability_config.metrics_port == 7090
                assert storage_config.database_url == "sqlite:///env_test.db"

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_model_defaults_when_no_overrides(self) -> None:
        """Test that model defaults are used when no env vars or .env file present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Clear any relevant environment variables
                with patch.dict(os.environ, {}, clear=False):
                    # Remove potentially interfering env vars
                    for key in list(os.environ.keys()):
                        if key.upper() in [
                            "APP_NAME",
                            "ENVIRONMENT",
                            "DEBUG",
                            "WS_RECONNECT_INTERVAL",
                            "WS_MAX_RECONNECT_ATTEMPTS",
                            "WS_PING_INTERVAL",
                            "WS_PING_TIMEOUT",
                            "LOG_LEVEL",
                            "LOG_FORMAT",
                            "METRICS_ENABLED",
                            "METRICS_PORT",
                        ]:
                            del os.environ[key]

                    base_settings = BaseCoreSettings()
                    network_config = BaseNetworkConfig()
                    observability_config = BaseObservabilityConfig()

                    # Verify defaults are used
                    assert base_settings.app_name == "asset-core"
                    assert base_settings.environment == "development"
                    assert base_settings.debug is False
                    assert network_config.ws_reconnect_interval == 5
                    assert network_config.ws_max_reconnect_attempts == 10
                    assert network_config.ws_ping_interval == 30
                    assert network_config.ws_ping_timeout == 10
                    assert observability_config.log_level == "INFO"
                    assert observability_config.log_format == "json"
                    assert observability_config.metrics_enabled is True
                    assert observability_config.metrics_port == 9090

            finally:
                os.chdir(original_cwd)


@pytest.mark.unit
class TestConfigTypeValidation:
    """Test strict type validation from environment variables."""

    def test_boolean_env_var_validation(self) -> None:
        """Test that boolean environment variables are strictly validated."""
        # Valid boolean representations should work
        valid_true_values = ["true", "True", "TRUE", "1", "yes", "on"]
        valid_false_values = ["false", "False", "FALSE", "0", "no", "off"]

        for true_val in valid_true_values:
            with patch.dict(os.environ, {"DEBUG": true_val}):
                settings = BaseCoreSettings()
                assert settings.debug is True

        for false_val in valid_false_values:
            with patch.dict(os.environ, {"DEBUG": false_val}):
                settings = BaseCoreSettings()
                assert settings.debug is False

        # Invalid boolean values should raise ValidationError
        with patch.dict(os.environ, {"DEBUG": "not-a-boolean"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings()

            errors = exc_info.value.errors()
            assert any(error["loc"] == ("debug",) for error in errors)

    def test_integer_env_var_validation(self) -> None:
        """Test that integer environment variables are strictly validated."""
        # Valid integer values should work
        with patch.dict(
            os.environ, {"WS_RECONNECT_INTERVAL": "15", "WS_MAX_RECONNECT_ATTEMPTS": "-1", "METRICS_PORT": "8080"}
        ):
            network_config = BaseNetworkConfig()
            observability_config = BaseObservabilityConfig()

            assert network_config.ws_reconnect_interval == 15
            assert network_config.ws_max_reconnect_attempts == -1
            assert observability_config.metrics_port == 8080

        # Invalid integer values should raise ValidationError
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "not-an-integer"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseNetworkConfig()

            errors = exc_info.value.errors()
            assert any(error["loc"] == ("ws_reconnect_interval",) for error in errors)

    def test_string_choice_field_validation(self) -> None:
        """Test validation of string choice fields with case insensitivity."""
        # Environment field validation
        valid_environments = ["development", "DEVELOPMENT", "staging", "STAGING", "production", "PRODUCTION"]
        for env in valid_environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                settings = BaseCoreSettings()
                assert settings.environment.lower() in ["development", "staging", "production"]

        # Log level field validation
        valid_log_levels = [
            "debug",
            "DEBUG",
            "info",
            "INFO",
            "warning",
            "WARNING",
            "error",
            "ERROR",
            "critical",
            "CRITICAL",
        ]
        for level in valid_log_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                config = BaseObservabilityConfig()
                assert config.log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Log format field validation
        valid_log_formats = ["json", "JSON", "text", "TEXT"]
        for format_val in valid_log_formats:
            with patch.dict(os.environ, {"LOG_FORMAT": format_val}):
                config = BaseObservabilityConfig()
                assert config.log_format.lower() in ["json", "text"]

        # Invalid choice values should raise ValidationError
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings()

            error_msg = str(exc_info.value)
            assert "environment must be one of" in error_msg


@pytest.mark.unit
class TestConfigCrossFieldValidation:
    """Test cross-field business logic validation."""

    def test_network_ping_timeout_cross_field_validation(self) -> None:
        """Test that ping_timeout must be less than ping_interval when ping is enabled."""
        # Valid configuration should work
        with patch.dict(os.environ, {"WS_PING_INTERVAL": "30", "WS_PING_TIMEOUT": "10"}):
            config = BaseNetworkConfig()
            assert config.ws_ping_timeout < config.ws_ping_interval

        # Invalid configuration should raise ValidationError
        with patch.dict(os.environ, {"WS_PING_INTERVAL": "10", "WS_PING_TIMEOUT": "15"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseNetworkConfig()

            assert "ws_ping_timeout must be less than ws_ping_interval when ping is enabled" in str(exc_info.value)

        # When ping is disabled (interval = 0), timeout validation is bypassed
        with patch.dict(os.environ, {"WS_PING_INTERVAL": "0", "WS_PING_TIMEOUT": "100"}):
            config = BaseNetworkConfig()
            assert config.ws_ping_interval == 0
            assert config.ws_ping_timeout == 100

    def test_storage_required_fields_validation(self) -> None:
        """Test that required fields in storage config are enforced."""
        # DATABASE_URL is required - should raise ValidationError when missing
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig()

        errors = exc_info.value.errors()
        db_url_error = next(error for error in errors if error["loc"] == ("database_url",))
        assert "required" in db_url_error["msg"].lower() or "missing" in db_url_error["msg"].lower()

        # Should work when DATABASE_URL is provided via env var
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            config = BaseStorageConfig()
            assert config.database_url == "sqlite:///test.db"


@pytest.mark.unit
class TestConfigFieldConstraints:
    """Test field-level constraints and validation."""

    def test_numeric_field_constraints(self) -> None:
        """Test that numeric field constraints are properly enforced."""
        # Test positive constraints
        with patch.dict(
            os.environ,
            {"WS_RECONNECT_INTERVAL": "-1", "WS_PING_INTERVAL": "-1", "WS_PING_TIMEOUT": "-1", "METRICS_PORT": "0"},
        ):
            # These should raise ValidationError due to constraint violations
            with pytest.raises(ValidationError):
                BaseNetworkConfig()

            with pytest.raises(ValidationError):
                BaseObservabilityConfig()

        # Test that -1 is valid for max_reconnect_attempts (unlimited)
        with patch.dict(os.environ, {"WS_MAX_RECONNECT_ATTEMPTS": "-1"}):
            config = BaseNetworkConfig()
            assert config.ws_max_reconnect_attempts == -1

        # Test port range constraints
        with patch.dict(os.environ, {"METRICS_PORT": "65536"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseObservabilityConfig()

            errors = exc_info.value.errors()
            port_error = next(error for error in errors if error["loc"] == ("metrics_port",))
            assert "less than or equal to 65535" in port_error["msg"]

    def test_string_field_constraints(self) -> None:
        """Test string field validation and constraints."""
        # Test minimum length constraints
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            with pytest.raises(ValidationError) as exc_info:
                BaseStorageConfig()

            errors = exc_info.value.errors()
            db_url_error = next(error for error in errors if error["loc"] == ("database_url",))
            assert "at least 1 character" in db_url_error["msg"] or "too short" in db_url_error["msg"]

        # Test that empty app_name is allowed
        with patch.dict(os.environ, {"APP_NAME": ""}):
            settings = BaseCoreSettings()
            assert settings.app_name == ""


@pytest.mark.unit
class TestConfigEnvironmentVariableNames:
    """Test environment variable name resolution and case sensitivity."""

    def test_case_insensitive_env_var_names(self) -> None:
        """Test that environment variable names are case insensitive."""
        # Test various case combinations for the same field
        test_cases = [
            ("APP_NAME", "test-app-upper"),
            ("app_name", "test-app-lower"),
            ("App_Name", "test-app-mixed"),
        ]

        for env_var, value in test_cases:
            with patch.dict(os.environ, {env_var: value}, clear=True):
                settings = BaseCoreSettings()
                assert settings.app_name == value

    def test_field_name_to_env_var_mapping(self) -> None:
        """Test that field names map correctly to environment variable names."""
        # Test that both snake_case field names and UPPER_CASE env vars work
        field_env_mappings = [
            ("DEBUG", "debug", "true"),
            ("WS_RECONNECT_INTERVAL", "ws_reconnect_interval", "15"),
            ("LOG_LEVEL", "log_level", "DEBUG"),
            ("METRICS_ENABLED", "metrics_enabled", "false"),
        ]

        for env_var, field_name, value in field_env_mappings:
            with patch.dict(os.environ, {env_var: value}):
                if field_name in ["debug"]:
                    settings = BaseCoreSettings()
                    assert hasattr(settings, field_name)
                elif field_name.startswith("ws_"):
                    network_config = BaseNetworkConfig()
                    assert hasattr(network_config, field_name)
                elif field_name.startswith("log_") or field_name.startswith("metrics_"):
                    observability_config = BaseObservabilityConfig()
                    assert hasattr(observability_config, field_name)


@pytest.mark.unit
class TestConfigErrorMessages:
    """Test that validation error messages are clear and helpful."""

    def test_choice_field_error_messages(self) -> None:
        """Test that choice field error messages list valid options."""
        # Environment validation error
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings()

            error_msg = str(exc_info.value)
            assert "environment must be one of" in error_msg
            assert "development" in error_msg
            assert "staging" in error_msg
            assert "production" in error_msg

        # Log level validation error
        with patch.dict(os.environ, {"LOG_LEVEL": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseObservabilityConfig()

            error_msg = str(exc_info.value)
            assert "log_level must be one of" in error_msg
            assert "DEBUG" in error_msg
            assert "INFO" in error_msg

    def test_constraint_error_messages(self) -> None:
        """Test that constraint violation error messages are informative."""
        # Numeric constraint error
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "-5"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseNetworkConfig()

            errors = exc_info.value.errors()
            field_error = next(error for error in errors if error["loc"] == ("ws_reconnect_interval",))
            assert "greater than or equal to" in field_error["msg"]

        # Cross-field validation error
        with patch.dict(os.environ, {"WS_PING_INTERVAL": "10", "WS_PING_TIMEOUT": "15"}):
            with pytest.raises(ValidationError) as exc_info:
                BaseNetworkConfig()

            assert "ws_ping_timeout must be less than ws_ping_interval when ping is enabled" in str(exc_info.value)


@pytest.mark.unit
class TestConfigModelConfiguration:
    """Test that model configuration settings are properly applied."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored due to extra='ignore' setting."""
        with patch.dict(
            os.environ,
            {"APP_NAME": "test-app", "UNKNOWN_FIELD": "should-be-ignored", "ANOTHER_UNKNOWN": "also-ignored"},
        ):
            settings = BaseCoreSettings()

            # Known field should be set
            assert settings.app_name == "test-app"

            # Unknown fields should be ignored
            assert not hasattr(settings, "unknown_field")
            assert not hasattr(settings, "another_unknown")

    def test_case_insensitive_env_var_processing(self) -> None:
        """Test that case_sensitive=False is working correctly."""
        # Test that various case combinations work for env var names
        with patch.dict(
            os.environ, {"app_name": "test-lowercase", "APP_NAME": "test-uppercase", "App_Name": "test-mixed"}
        ):
            # The last one set should win (depends on dict order)
            settings = BaseCoreSettings()
            assert settings.app_name in ["test-lowercase", "test-uppercase", "test-mixed"]

    def test_string_whitespace_stripping(self) -> None:
        """Test str_strip_whitespace behavior where applicable."""
        # For config classes that have str_strip_whitespace=True
        with patch.dict(
            os.environ,
            {
                "WS_RECONNECT_INTERVAL": "  15  ",  # Should be stripped and converted
                "LOG_LEVEL": "  INFO  ",  # Should be stripped
            },
        ):
            network_config = BaseNetworkConfig()
            observability_config = BaseObservabilityConfig()

            assert network_config.ws_reconnect_interval == 15
            assert observability_config.log_level == "INFO"
