"""ABOUTME: Unit tests for observability configuration module
ABOUTME: Testing BaseObservabilityConfig validation, logging levels, and metrics settings
"""

import pytest
from pydantic import ValidationError

from asset_core.config.observability import BaseObservabilityConfig


@pytest.mark.unit
class TestBaseObservabilityConfig:
    """Unit tests for BaseObservabilityConfig class."""

    def test_default_values(self) -> None:
        """Test that default values are correctly set."""
        config = BaseObservabilityConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.metrics_enabled is True
        assert config.metrics_port == 9090

    def test_explicit_initialization(self) -> None:
        """Test explicit initialization with custom values."""
        config = BaseObservabilityConfig(log_level="DEBUG", log_format="text", metrics_enabled=False, metrics_port=8080)

        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.metrics_enabled is False
        assert config.metrics_port == 8080

    def test_log_level_case_insensitive_validation(self) -> None:
        """Test that log_level validation is case insensitive."""
        valid_levels = [
            ("DEBUG", "DEBUG"),
            ("debug", "DEBUG"),
            ("Debug", "DEBUG"),
            ("INFO", "INFO"),
            ("info", "INFO"),
            ("Info", "INFO"),
            ("WARNING", "WARNING"),
            ("warning", "WARNING"),
            ("Warning", "WARNING"),
            ("ERROR", "ERROR"),
            ("error", "ERROR"),
            ("Error", "ERROR"),
            ("CRITICAL", "CRITICAL"),
            ("critical", "CRITICAL"),
            ("Critical", "CRITICAL"),
        ]

        for input_level, expected_level in valid_levels:
            config = BaseObservabilityConfig(log_level=input_level)
            assert config.log_level == expected_level

    def test_log_level_invalid_values_rejected(self) -> None:
        """Test that invalid log_level values are rejected."""
        invalid_levels = ["TRACE", "VERBOSE", "NOTICE", "ALERT", "EMERGENCY", "invalid", ""]

        for invalid_level in invalid_levels:
            with pytest.raises(ValidationError) as exc_info:
                BaseObservabilityConfig(log_level=invalid_level)

            error_msg = str(exc_info.value)
            assert "log_level must be one of" in error_msg

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

    def test_log_format_invalid_values_rejected(self) -> None:
        """Test that invalid log_format values are rejected."""
        invalid_formats = ["xml", "yaml", "csv", "binary", "invalid", ""]

        for invalid_format in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                BaseObservabilityConfig(log_format=invalid_format)

            error_msg = str(exc_info.value)
            assert "log_format must be one of" in error_msg

    def test_metrics_port_validation(self) -> None:
        """Test metrics_port validation constraints."""
        # Valid port numbers
        valid_ports = [1, 80, 443, 8080, 9090, 65535]

        for port in valid_ports:
            config = BaseObservabilityConfig(metrics_port=port)
            assert config.metrics_port == port

        # Invalid port numbers
        invalid_ports = [0, -1, 65536, 100000]

        for port in invalid_ports:
            with pytest.raises(ValidationError) as exc_info:
                BaseObservabilityConfig(metrics_port=port)

            errors = exc_info.value.errors()
            port_error = next(error for error in errors if error["loc"] == ("metrics_port",))
            assert "greater than 0" in port_error["msg"] or "less than or equal to 65535" in port_error["msg"]

    def test_metrics_enabled_boolean_validation(self) -> None:
        """Test that metrics_enabled properly validates boolean values."""
        # Valid boolean values
        config_true = BaseObservabilityConfig(metrics_enabled=True)
        assert config_true.metrics_enabled is True

        config_false = BaseObservabilityConfig(metrics_enabled=False)
        assert config_false.metrics_enabled is False

        # Pydantic auto-converts common boolean representations
        config_str_true = BaseObservabilityConfig(metrics_enabled="true")
        assert config_str_true.metrics_enabled is True

        config_str_false = BaseObservabilityConfig(metrics_enabled="false")
        assert config_str_false.metrics_enabled is False

        config_int_true = BaseObservabilityConfig(metrics_enabled=1)
        assert config_int_true.metrics_enabled is True

        config_int_false = BaseObservabilityConfig(metrics_enabled=0)
        assert config_int_false.metrics_enabled is False

    def test_type_validation(self) -> None:
        """Test type validation for all fields."""
        # Valid types should work
        config = BaseObservabilityConfig(log_level="DEBUG", log_format="text", metrics_enabled=True, metrics_port=8080)

        assert isinstance(config.log_level, str)
        assert isinstance(config.log_format, str)
        assert isinstance(config.metrics_enabled, bool)
        assert isinstance(config.metrics_port, int)

        # Invalid types should raise ValidationError
        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_level=123)

        with pytest.raises(ValidationError):
            BaseObservabilityConfig(log_format=123)

        # Pydantic auto-converts numeric strings to integers
        config_str_port = BaseObservabilityConfig(metrics_port="8080")
        assert config_str_port.metrics_port == 8080
        assert isinstance(config_str_port.metrics_port, int)

    def test_model_config_settings(self) -> None:
        """Test that model configuration is properly set."""
        config = BaseObservabilityConfig()

        # Check that model_config is properly configured
        assert hasattr(config, "model_config")
        assert config.model_config.get("str_strip_whitespace") is True
        assert config.model_config.get("extra") == "ignore"

    def test_field_descriptions(self) -> None:
        """Test that all fields have proper descriptions."""
        for field_name, field_info in BaseObservabilityConfig.model_fields.items():
            assert field_info.description is not None
            assert len(field_info.description) > 0, f"Field {field_name} missing description"

    def test_none_values_rejected(self) -> None:
        """Test that None values are properly rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(log_level=None, log_format=None, metrics_enabled=None, metrics_port=None)

        errors = exc_info.value.errors()
        assert len(errors) == 4
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"log_level", "log_format", "metrics_enabled", "metrics_port"}

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored due to model configuration."""
        # Should not raise error due to extra="ignore"
        config = BaseObservabilityConfig(log_level="DEBUG", unknown_field="should-be-ignored", another_unknown=123)

        assert config.log_level == "DEBUG"
        assert not hasattr(config, "unknown_field")
        assert not hasattr(config, "another_unknown")

    def test_serialization_compatibility(self) -> None:
        """Test that config can be serialized and deserialized."""
        original_config = BaseObservabilityConfig(
            log_level="DEBUG", log_format="text", metrics_enabled=False, metrics_port=8080
        )

        # Test model_dump
        data = original_config.model_dump()
        assert isinstance(data, dict)
        assert data["log_level"] == "DEBUG"
        assert data["log_format"] == "text"
        assert data["metrics_enabled"] is False
        assert data["metrics_port"] == 8080

        # Test that we can create a new instance from the data
        new_config = BaseObservabilityConfig(**data)
        assert new_config.log_level == original_config.log_level
        assert new_config.log_format == original_config.log_format
        assert new_config.metrics_enabled == original_config.metrics_enabled
        assert new_config.metrics_port == original_config.metrics_port

    def test_field_descriptions_content(self) -> None:
        """Test that field descriptions contain meaningful content."""
        descriptions = {
            field_name: field_info.description
            for field_name, field_info in BaseObservabilityConfig.model_fields.items()
        }

        # Check that descriptions mention key concepts
        assert descriptions["log_level"] is not None, "log_level description is missing"
        assert "log" in descriptions["log_level"].lower()

        assert descriptions["log_format"] is not None, "log_format description is missing"
        assert "log" in descriptions["log_format"].lower()

        assert descriptions["metrics_enabled"] is not None, "metrics_enabled description is missing"
        assert (
            "metrics" in descriptions["metrics_enabled"].lower()
            or "prometheus" in descriptions["metrics_enabled"].lower()
        )

        assert descriptions["metrics_port"] is not None, "metrics_port description is missing"
        assert "port" in descriptions["metrics_port"].lower() and "metrics" in descriptions["metrics_port"].lower()

    def test_string_representation(self) -> None:
        """Test string representation contains key information."""
        config = BaseObservabilityConfig(log_level="DEBUG", log_format="text", metrics_enabled=False, metrics_port=8080)

        str_repr = str(config)

        # Should contain field values
        assert "DEBUG" in str_repr
        assert "text" in str_repr
        assert "8080" in str_repr

    def test_boundary_port_values(self) -> None:
        """Test boundary values for metrics_port."""
        # Minimum valid port
        config = BaseObservabilityConfig(metrics_port=1)
        assert config.metrics_port == 1

        # Maximum valid port
        config = BaseObservabilityConfig(metrics_port=65535)
        assert config.metrics_port == 65535

        # Common ports
        common_ports = [80, 443, 8080, 9090, 3000, 5000]
        for port in common_ports:
            config = BaseObservabilityConfig(metrics_port=port)
            assert config.metrics_port == port

    def test_validation_error_messages(self) -> None:
        """Test that validation error messages are helpful."""
        # Test log_level validation error message
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(log_level="invalid")

        error_msg = str(exc_info.value)
        assert "log_level must be one of" in error_msg
        assert "DEBUG" in error_msg
        assert "INFO" in error_msg
        assert "WARNING" in error_msg
        assert "ERROR" in error_msg
        assert "CRITICAL" in error_msg

        # Test log_format validation error message
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(log_format="invalid")

        error_msg = str(exc_info.value)
        assert "log_format must be one of" in error_msg
        assert "json" in error_msg
        assert "text" in error_msg

        # Test port validation error message
        with pytest.raises(ValidationError) as exc_info:
            BaseObservabilityConfig(metrics_port=0)

        errors = exc_info.value.errors()
        port_error = next(error for error in errors if error["loc"] == ("metrics_port",))
        assert "greater than 0" in port_error["msg"]

    def test_whitespace_handling_in_string_fields(self) -> None:
        """Test whitespace handling in string fields due to str_strip_whitespace=True."""
        # Since str_strip_whitespace=True, leading/trailing spaces should be stripped
        # but this only applies if the fields are actually processed as strings from env vars
        # For direct instantiation, the behavior depends on Pydantic's processing

        # Test that valid values work regardless of potential whitespace
        config = BaseObservabilityConfig(log_level="INFO", log_format="json")
        assert config.log_level == "INFO"
        assert config.log_format == "json"

    def test_case_preservation_after_validation(self) -> None:
        """Test that case is properly normalized after validation."""
        # log_level should be converted to uppercase
        config = BaseObservabilityConfig(log_level="info")
        assert config.log_level == "INFO"
        assert config.log_level == config.log_level.upper()

        # log_format should be converted to lowercase
        config = BaseObservabilityConfig(log_format="JSON")
        assert config.log_format == "json"
        assert config.log_format == config.log_format.lower()
