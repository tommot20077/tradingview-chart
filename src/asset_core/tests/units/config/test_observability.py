"""Unit tests for observability configuration settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.config import BaseObservabilityConfig


@pytest.mark.unit
class TestBaseObservabilityConfigConstruction:
    """Test cases for BaseObservabilityConfig model construction."""

    def test_default_observability_config_creation(self) -> None:
        """Test default observability configuration initialization.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig creates an instance with
        correct default values for logging and metrics configuration.

        Preconditions:
            - No environment variables set
            - Clean initialization context

        Steps:
            - Create BaseObservabilityConfig instance with no arguments
            - Verify all default values are set correctly

        Expected Result:
            - log_level should be "INFO"
            - log_format should be "json"
            - metrics_enabled should be True
            - metrics_port should be 9090
        """
        config = BaseObservabilityConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.metrics_enabled is True
        assert config.metrics_port == 9090

    def test_custom_observability_config_creation(self) -> None:
        """Test custom observability configuration with explicit values.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig correctly accepts and stores
        custom values for all logging and metrics parameters.

        Preconditions:
            - Custom values for all configuration fields

        Steps:
            - Create config with custom log_level, log_format, metrics settings
            - Verify all provided values are stored correctly

        Expected Result:
            - log_level should be "DEBUG"
            - log_format should be "text"
            - metrics_enabled should be False
            - metrics_port should be 8080
        """
        config = BaseObservabilityConfig(log_level="DEBUG", log_format="text", metrics_enabled=False, metrics_port=8080)

        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.metrics_enabled is False
        assert config.metrics_port == 8080

    def test_observability_config_from_dict(self) -> None:
        """Test observability configuration from dictionary unpacking.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig can be initialized by
        unpacking a dictionary containing all configuration parameters.

        Preconditions:
            - Dictionary with all observability configuration keys

        Steps:
            - Create configuration dictionary with all settings
            - Initialize BaseObservabilityConfig using dictionary unpacking
            - Verify all values from dictionary are applied

        Expected Result:
            - All dictionary values should be correctly assigned to config fields
        """
        config_dict = {"log_level": "WARNING", "log_format": "text", "metrics_enabled": True, "metrics_port": 9091}

        config = BaseObservabilityConfig(**config_dict)

        assert config.log_level == "WARNING"
        assert config.log_format == "text"
        assert config.metrics_enabled is True
        assert config.metrics_port == 9091


@pytest.mark.unit
class TestBaseObservabilityConfigValidation:
    """Test cases for BaseObservabilityConfig validation."""

    def test_valid_log_levels(self) -> None:
        """Test acceptance of all valid log levels.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts all standard
        logging levels without validation errors.

        Preconditions:
            - List of valid log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Steps:
            - Iterate through each valid log level
            - Create config instance with each level
            - Verify no validation errors occur

        Expected Result:
            - All valid log levels should be accepted
            - Values should be stored exactly as provided
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = BaseObservabilityConfig(log_level=level)
            assert config.log_level == level

    def test_case_insensitive_log_level(self) -> None:
        """Test log level case normalization to uppercase.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig automatically normalizes
        log level values to uppercase regardless of input case.

        Preconditions:
            - Log level values in various cases

        Steps:
            - Test with "debug" (lowercase) expecting "DEBUG"
            - Test with "Info" (mixed case) expecting "INFO"
            - Test with "warning" (lowercase) expecting "WARNING"

        Expected Result:
            - All log levels should be normalized to uppercase
            - "debug" → "DEBUG", "Info" → "INFO", etc.
        """
        config = BaseObservabilityConfig(log_level="debug")
        assert config.log_level == "DEBUG"

        config = BaseObservabilityConfig(log_level="Info")
        assert config.log_level == "INFO"

        config = BaseObservabilityConfig(log_level="warning")
        assert config.log_level == "WARNING"

    def test_invalid_log_level_validation(self) -> None:
        """Test rejection of invalid log level values.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig raises ValidationError
        when provided with log levels not in the allowed list.

        Preconditions:
            - Invalid log level value not in allowed list

        Steps:
            - Attempt to create config with log_level="INVALID"
            - Catch and verify ValidationError is raised
            - Check error message contains valid options

        Expected Result:
            - ValidationError should be raised
            - Error message should list valid log level options
        """
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(log_level="INVALID")

        assert "log_level must be one of" in str(exc_info.value)
        assert "DEBUG" in str(exc_info.value)
        assert "INFO" in str(exc_info.value)

    def test_valid_log_formats(self) -> None:
        """Test acceptance of all valid log formats.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts all supported
        log format values (json and text).

        Preconditions:
            - List of valid log formats

        Steps:
            - Test with "json" format
            - Test with "text" format
            - Verify both are accepted without errors

        Expected Result:
            - Both "json" and "text" formats should be accepted
            - Values should be stored exactly as provided
        """
        valid_formats = ["json", "text"]

        for format_type in valid_formats:
            config = BaseObservabilityConfig(log_format=format_type)
            assert config.log_format == format_type

    def test_invalid_log_format_validation(self) -> None:
        """Test rejection of invalid log format values.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig raises ValidationError
        when provided with unsupported log format values.

        Preconditions:
            - Invalid log format value not in allowed list

        Steps:
            - Attempt to create config with log_format="xml"
            - Catch and verify ValidationError is raised
            - Check error message contains valid format options

        Expected Result:
            - ValidationError should be raised
            - Error message should list "json" and "text" as valid options
        """
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(log_format="xml")

        assert "log_format must be one of" in str(exc_info.value)
        assert "json" in str(exc_info.value)
        assert "text" in str(exc_info.value)

    def test_log_format_case_sensitive(self) -> None:
        """Test log format case sensitivity enforcement.

        Description of what the test covers:
        Verifies that log format validation is case-sensitive and
        rejects values with incorrect casing.

        Preconditions:
            - Log format values with incorrect casing

        Steps:
            - Attempt to create config with log_format="JSON" (uppercase)
            - Attempt to create config with log_format="Text" (mixed case)
            - Verify ValidationError is raised for both

        Expected Result:
            - ValidationError should be raised for "JSON"
            - ValidationError should be raised for "Text"
            - Only exact case matches should be accepted
        """
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_format="JSON")

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_format="Text")

    def test_metrics_port_validation(self) -> None:
        """Test metrics port range validation.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig validates metrics_port
        values are within valid port number range (1-65535).

        Preconditions:
            - Valid and invalid port number values

        Steps:
            - Test with valid ports (8080, 65535)
            - Test with invalid ports (-1, 0, 65536)
            - Verify validation behavior

        Expected Result:
            - Valid ports should be accepted
            - Invalid ports should raise ValidationError
        """
        # Valid port numbers
        config = BaseObservabilityConfig(metrics_port=8080)
        assert config.metrics_port == 8080

        config = BaseObservabilityConfig(metrics_port=65535)
        assert config.metrics_port == 65535

        # Invalid port numbers
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port=-1)

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port=0)

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port=65536)


@pytest.mark.unit
class TestBaseObservabilityConfigEnvironmentVariables:
    """Test cases for BaseObservabilityConfig environment variable loading."""

    def test_env_var_loading_log_level(self) -> None:
        """Test log_level loading from environment variable.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig correctly loads
        log_level value from LOG_LEVEL environment variable.

        Preconditions:
        - LOG_LEVEL environment variable set to "ERROR"

        Steps:
        - Set LOG_LEVEL environment variable
        - Create BaseObservabilityConfig with no arguments
        - Verify log_level is loaded from environment

        Expected Result:
        - config.log_level should be "ERROR" from environment variable
        """
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            config = BaseObservabilityConfig()
            assert config.log_level == "ERROR"

    def test_env_var_loading_log_format(self) -> None:
        """Test log_format loading from environment variable.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig correctly loads
        log_format value from LOG_FORMAT environment variable.

        Preconditions:
        - LOG_FORMAT environment variable set to "text"

        Steps:
        - Set LOG_FORMAT environment variable
        - Create BaseObservabilityConfig with no arguments
        - Verify log_format is loaded from environment

        Expected Result:
        - config.log_format should be "text" from environment variable
        """
        with patch.dict(os.environ, {"LOG_FORMAT": "text"}):
            config = BaseObservabilityConfig()
            assert config.log_format == "text"

    def test_env_var_loading_metrics_enabled(self) -> None:
        """Test metrics_enabled loading from environment variable.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig correctly loads
        and converts metrics_enabled boolean from environment variable.

        Preconditions:
        - METRICS_ENABLED environment variable set to string boolean values

        Steps:
        - Set METRICS_ENABLED to "false", verify False conversion
        - Set METRICS_ENABLED to "true", verify True conversion
        - Create BaseObservabilityConfig instances

        Expected Result:
        - "false" string should convert to False boolean
        - "true" string should convert to True boolean
        """
        with patch.dict(os.environ, {"METRICS_ENABLED": "false"}):
            config = BaseObservabilityConfig()
            assert config.metrics_enabled is False

        with patch.dict(os.environ, {"METRICS_ENABLED": "true"}):
            config = BaseObservabilityConfig()
            assert config.metrics_enabled is True

    def test_env_var_loading_metrics_port(self) -> None:
        """Test metrics_port loading from environment variable.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig correctly loads
        and converts metrics_port from string to integer.

        Preconditions:
        - METRICS_PORT environment variable set to "8081"

        Steps:
        - Set METRICS_PORT environment variable to string value
        - Create BaseObservabilityConfig with no arguments
        - Verify metrics_port is converted to integer

        Expected Result:
        - config.metrics_port should be 8081 (integer) from environment
        """
        with patch.dict(os.environ, {"METRICS_PORT": "8081"}):
            config = BaseObservabilityConfig()
            assert config.metrics_port == 8081

    def test_env_var_case_normalization(self) -> None:
        """Test environment variable case normalization."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            config = BaseObservabilityConfig()
            assert config.log_level == "DEBUG"

    def test_env_var_override_defaults(self) -> None:
        """Test environment variables override default values."""
        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "CRITICAL", "LOG_FORMAT": "text", "METRICS_ENABLED": "false", "METRICS_PORT": "9999"},
        ):
            config = BaseObservabilityConfig()
            assert config.log_level == "CRITICAL"
            assert config.log_format == "text"
            assert config.metrics_enabled is False
            assert config.metrics_port == 9999

    def test_constructor_args_override_env_vars(self) -> None:
        """Test constructor arguments override environment variables."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR", "METRICS_PORT": "8888"}):
            config = BaseObservabilityConfig(log_level="DEBUG", metrics_port=7777)
            assert config.log_level == "DEBUG"
            assert config.metrics_port == 7777


@pytest.mark.unit
class TestBaseObservabilityConfigBoundaryValues:
    """Test cases for BaseObservabilityConfig boundary values."""

    def test_minimum_valid_port(self) -> None:
        """Test minimum valid metrics port configuration.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts the minimum
        valid port number (1) for metrics endpoint.

        Preconditions:
        - Port number set to minimum valid value (1)

        Steps:
        - Create BaseObservabilityConfig with metrics_port=1
        - Verify port is correctly set

        Expected Result:
        - metrics_port should be exactly 1
        """
        config = BaseObservabilityConfig(metrics_port=1)
        assert config.metrics_port == 1

    def test_maximum_valid_port(self) -> None:
        """Test maximum valid metrics port configuration.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts the maximum
        valid port number (65535) for metrics endpoint.

        Preconditions:
        - Port number set to maximum valid value (65535)

        Steps:
        - Create BaseObservabilityConfig with metrics_port=65535
        - Verify port is correctly set

        Expected Result:
        - metrics_port should be exactly 65535
        """
        config = BaseObservabilityConfig(metrics_port=65535)
        assert config.metrics_port == 65535

    def test_common_port_numbers(self) -> None:
        """Test commonly used port numbers for metrics.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts commonly
        used port numbers for metrics endpoints.

        Preconditions:
        - List of common port numbers for web services

        Steps:
        - Iterate through common ports (80, 443, 8080, etc.)
        - Create BaseObservabilityConfig for each port
        - Verify each port is correctly accepted

        Expected Result:
        - All common port numbers should be accepted
        - Port values should be stored exactly as provided
        """
        common_ports = [80, 443, 8080, 8443, 9090, 9091, 3000, 5000]

        for port in common_ports:
            config = BaseObservabilityConfig(metrics_port=port)
            assert config.metrics_port == port

    def test_all_log_levels_with_formats(self) -> None:
        """Test all log level and format combinations.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig accepts all valid
        combinations of log levels with log formats.

        Preconditions:
        - List of all valid log levels
        - List of all valid log formats

        Steps:
        - Create nested loop for all level-format combinations
        - Create BaseObservabilityConfig for each combination
        - Verify both level and format are correctly set

        Expected Result:
        - All valid combinations should be accepted
        - Each log level should work with both json and text formats
        """
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_formats = ["json", "text"]

        for level in log_levels:
            for format_type in log_formats:
                config = BaseObservabilityConfig(log_level=level, log_format=format_type)
                assert config.log_level == level
                assert config.log_format == format_type


@pytest.mark.unit
class TestBaseObservabilityConfigSerialization:
    """Test cases for BaseObservabilityConfig serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump method."""
        config = BaseObservabilityConfig(
            log_level="WARNING", log_format="text", metrics_enabled=False, metrics_port=8080
        )

        data = config.model_dump()

        assert isinstance(data, dict)
        assert data["log_level"] == "WARNING"
        assert data["log_format"] == "text"
        assert data["metrics_enabled"] is False
        assert data["metrics_port"] == 8080

    def test_model_dump_json_serializable(self) -> None:
        """Test model can be dumped to JSON-serializable format."""
        config = BaseObservabilityConfig()

        data = config.model_dump()

        # Should be able to convert to JSON
        import json

        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed_data = json.loads(json_str)
        assert parsed_data["log_level"] == "INFO"
        assert parsed_data["log_format"] == "json"
        assert parsed_data["metrics_enabled"] is True
        assert parsed_data["metrics_port"] == 9090


@pytest.mark.unit
class TestBaseObservabilityConfigStringRepresentation:
    """Test cases for BaseObservabilityConfig string representation."""

    def test_string_representation(self) -> None:
        """Test string representation."""
        config = BaseObservabilityConfig(log_level="DEBUG", metrics_port=8080)

        str_repr = str(config)

        # Pydantic models return field values in string representation
        assert "log_level='DEBUG'" in str_repr
        assert "metrics_port=8080" in str_repr


@pytest.mark.unit
class TestBaseObservabilityConfigEdgeCases:
    """Test cases for BaseObservabilityConfig edge cases."""

    def test_boolean_string_conversion(self) -> None:
        """Test boolean string values are converted."""
        with patch.dict(os.environ, {"METRICS_ENABLED": "1"}):
            config = BaseObservabilityConfig()
            assert config.metrics_enabled is True

        with patch.dict(os.environ, {"METRICS_ENABLED": "0"}):
            config = BaseObservabilityConfig()
            assert config.metrics_enabled is False

    def test_port_string_conversion(self) -> None:
        """Test port string values are converted to integers."""
        with patch.dict(os.environ, {"METRICS_PORT": "9091"}):
            config = BaseObservabilityConfig()
            assert config.metrics_port == 9091
            assert isinstance(config.metrics_port, int)

    def test_extra_fields_ignored(self) -> None:
        """Test extra fields are ignored if model allows it."""
        config = BaseObservabilityConfig(log_level="INFO", unknown_field="should_be_ignored")
        assert config.log_level == "INFO"
        assert not hasattr(config, "unknown_field")

    def test_logging_configuration_combinations(self) -> None:
        """Test realistic logging configuration combinations."""
        # Development configuration
        dev_config = BaseObservabilityConfig(log_level="DEBUG", log_format="text", metrics_enabled=True)
        assert dev_config.log_level == "DEBUG"
        assert dev_config.log_format == "text"

        # Production configuration
        prod_config = BaseObservabilityConfig(log_level="WARNING", log_format="json", metrics_enabled=True)
        assert prod_config.log_level == "WARNING"
        assert prod_config.log_format == "json"


@pytest.mark.unit
class TestBaseObservabilityConfigInvalidData:
    """Test cases for BaseObservabilityConfig with invalid data."""

    def test_invalid_port_types(self) -> None:
        """Test invalid port types."""
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port="not_a_number")

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port=3.14)

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_port=None)

    def test_invalid_boolean_types(self) -> None:
        """Test invalid boolean types for metrics_enabled."""
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_enabled="not_a_bool")

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(metrics_enabled=123)

    def test_none_values_for_fields(self) -> None:
        """Test None values for fields."""
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_level=None)

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_format=None)

    def test_empty_string_values(self) -> None:
        """Test empty string values."""
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_level="")

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_format="")


@pytest.mark.unit
@pytest.mark.config
class TestBaseObservabilityConfigIntegration:
    """Integration test cases for BaseObservabilityConfig."""

    def test_complete_observability_configuration(self) -> None:
        """Test complete observability configuration with all features."""
        with patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "warning",  # Should be normalized to uppercase
                "METRICS_ENABLED": "true",
            },
        ):
            config = BaseObservabilityConfig(log_format="text", metrics_port=8080)

            # Verify mixed sources and normalization
            assert config.log_level == "WARNING"  # From env var, normalized
            assert config.log_format == "text"  # From constructor
            assert config.metrics_enabled is True  # From env var
            assert config.metrics_port == 8080  # From constructor

            # Test serialization preserves all values
            data = config.model_dump()
            assert data["log_level"] == "WARNING"
            assert data["log_format"] == "text"
            assert data["metrics_enabled"] is True
            assert data["metrics_port"] == 8080

    def test_logging_level_hierarchy(self) -> None:
        """Test logging level hierarchy understanding."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_values = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        for level in levels:
            config = BaseObservabilityConfig(log_level=level)
            assert config.log_level == level

            # Verify level can be used for logging hierarchy decisions
            import logging

            log_level_value = getattr(logging, level)
            assert log_level_value == level_values[level]

    def test_metrics_and_logging_coordination(self) -> None:
        """Test coordinated metrics and logging configuration."""
        # Scenario 1: High observability (debug with metrics)
        high_obs_config = BaseObservabilityConfig(
            log_level="DEBUG", log_format="json", metrics_enabled=True, metrics_port=9090
        )

        assert high_obs_config.log_level == "DEBUG"
        assert high_obs_config.metrics_enabled is True

        # Scenario 2: Minimal observability (error only, no metrics)
        minimal_config = BaseObservabilityConfig(log_level="ERROR", log_format="text", metrics_enabled=False)

        assert minimal_config.log_level == "ERROR"
        assert minimal_config.metrics_enabled is False

    def test_configuration_inheritance_compatibility(self) -> None:
        """Test extension of BaseObservabilityConfig through inheritance.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig supports extension
        with additional observability fields while preserving
        base logging and metrics functionality.

        Preconditions:
        - Base observability configuration with custom fields
        - Log level and metrics port for configuration

        Steps:
        - Define CustomBaseObservabilityConfig inheriting from base
        - Add custom fields: custom_log_file, trace_enabled
        - Create config instance with base and custom parameters
        - Verify base and custom configuration are preserved

        Expected Result:
        - Base fields (log_level, metrics_port) maintained
        - Custom fields added with default values
        - Ability to override both base and custom configuration
        """

        class CustomBaseObservabilityConfig(BaseObservabilityConfig):
            custom_log_file: str = "/var/log/custom.log"
            trace_enabled: bool = False

        config = CustomBaseObservabilityConfig(log_level="WARNING", metrics_port=9091)

        assert config.log_level == "WARNING"
        assert config.metrics_port == 9091
        assert config.custom_log_file == "/var/log/custom.log"
        assert config.trace_enabled is False

    def test_environment_specific_configurations(self) -> None:
        """Test observability configuration across environments.

        Description of what the test covers:
        Verifies that BaseObservabilityConfig supports different
        observability configurations for development and production
        environments with distinct logging and monitoring needs.

        Preconditions:
        - Environment variables for development setup
        - Environment variables for production setup

        Steps:
        - Set development environment variables (DEBUG, text format)
        - Create BaseObservabilityConfig for development
        - Set production environment variables (WARNING, json format)
        - Create BaseObservabilityConfig for production
        - Verify configuration matches environment requirements

        Expected Result:
        - Development config:
            * DEBUG log level for detailed debugging
            * Text format for human readability
            * Metrics enabled for monitoring
        - Production config:
            * WARNING log level for important events only
            * JSON format for structured logging
            * Metrics enabled with standard port
        """
        # Development environment
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "LOG_FORMAT": "text", "METRICS_ENABLED": "true"}):
            dev_config = BaseObservabilityConfig()
            assert dev_config.log_level == "DEBUG"
            assert dev_config.log_format == "text"
            assert dev_config.metrics_enabled is True

        # Production environment
        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "WARNING", "LOG_FORMAT": "json", "METRICS_ENABLED": "true", "METRICS_PORT": "9090"},
        ):
            prod_config = BaseObservabilityConfig()
            assert prod_config.log_level == "WARNING"
            assert prod_config.log_format == "json"
            assert prod_config.metrics_enabled is True
            assert prod_config.metrics_port == 9090
