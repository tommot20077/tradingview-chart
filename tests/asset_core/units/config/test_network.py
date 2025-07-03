"""ABOUTME: Unit tests for network configuration module
ABOUTME: Testing BaseNetworkConfig validation, defaults, and cross-field logic
"""

import pytest
from pydantic import ValidationError

from asset_core.config.network import BaseNetworkConfig


@pytest.mark.unit
class TestBaseNetworkConfig:
    """Unit tests for BaseNetworkConfig class."""

    def test_default_values(self) -> None:
        """Test that default values are correctly set."""
        config = BaseNetworkConfig()

        assert config.ws_reconnect_interval == 5
        assert config.ws_max_reconnect_attempts == 10
        assert config.ws_ping_interval == 30
        assert config.ws_ping_timeout == 10

    def test_explicit_initialization(self) -> None:
        """Test explicit initialization with custom values."""
        config = BaseNetworkConfig(
            ws_reconnect_interval=15, ws_max_reconnect_attempts=5, ws_ping_interval=60, ws_ping_timeout=20
        )

        assert config.ws_reconnect_interval == 15
        assert config.ws_max_reconnect_attempts == 5
        assert config.ws_ping_interval == 60
        assert config.ws_ping_timeout == 20

    def test_ping_timeout_validation_success(self) -> None:
        """Test that valid ping timeout configurations are accepted."""
        # Valid case: ping_timeout < ping_interval
        config = BaseNetworkConfig(ws_ping_interval=30, ws_ping_timeout=10)
        assert config.ws_ping_timeout < config.ws_ping_interval

        # Valid case: Different valid values
        config = BaseNetworkConfig(ws_ping_interval=60, ws_ping_timeout=20)
        assert config.ws_ping_timeout < config.ws_ping_interval

    def test_ping_timeout_validation_failure(self) -> None:
        """Test that invalid ping timeout configurations are rejected."""
        # Invalid case: ping_timeout >= ping_interval should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=15)

        assert "ws_ping_timeout must be less than ws_ping_interval when ping is enabled" in str(exc_info.value)

        # Edge case: ping_timeout == ping_interval should also fail
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=10)

        assert "ws_ping_timeout must be less than ws_ping_interval when ping is enabled" in str(exc_info.value)

    def test_ping_disabled_bypasses_timeout_validation(self) -> None:
        """Test that ping timeout validation is bypassed when ping is disabled."""
        # When ping_interval is 0 (disabled), timeout value becomes irrelevant
        config = BaseNetworkConfig(ws_ping_interval=0, ws_ping_timeout=10)
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 10  # Should be allowed

        # Even large timeout values should be allowed when ping is disabled
        config = BaseNetworkConfig(ws_ping_interval=0, ws_ping_timeout=100)
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 100

    def test_unlimited_reconnect_attempts(self) -> None:
        """Test that -1 means unlimited reconnect attempts."""
        config = BaseNetworkConfig(ws_max_reconnect_attempts=-1)
        assert config.ws_max_reconnect_attempts == -1

    def test_negative_value_validation(self) -> None:
        """Test validation of negative values."""
        # Valid negative value for unlimited attempts
        config = BaseNetworkConfig(ws_max_reconnect_attempts=-1)
        assert config.ws_max_reconnect_attempts == -1

        # Invalid negative values for other fields should be rejected
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout=-1)

    def test_zero_boundary_values(self) -> None:
        """Test that zero values are handled correctly."""
        # Zero should be valid for all fields
        config = BaseNetworkConfig(
            ws_reconnect_interval=0, ws_max_reconnect_attempts=0, ws_ping_interval=0, ws_ping_timeout=0
        )

        assert config.ws_reconnect_interval == 0
        assert config.ws_max_reconnect_attempts == 0
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 0

    def test_large_numeric_values(self) -> None:
        """Test handling of large but valid numeric values."""
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

    def test_type_validation(self) -> None:
        """Test type validation for integer fields."""
        # Valid integers should work
        config = BaseNetworkConfig(
            ws_reconnect_interval=5, ws_max_reconnect_attempts=10, ws_ping_interval=30, ws_ping_timeout=10
        )

        assert isinstance(config.ws_reconnect_interval, int)
        assert isinstance(config.ws_max_reconnect_attempts, int)
        assert isinstance(config.ws_ping_interval, int)
        assert isinstance(config.ws_ping_timeout, int)

        # Invalid types should raise ValidationError
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval="not-an-integer")

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_max_reconnect_attempts="not-an-integer")

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval="not-an-integer")

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout="not-an-integer")

    def test_field_constraints(self) -> None:
        """Test field constraints are properly enforced."""
        # All fields should be >= 0 except ws_max_reconnect_attempts which allows -1

        # Test minimum values for non-negative fields
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval=-2)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=-2)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout=-2)

        # Test minimum value for ws_max_reconnect_attempts (should be >= -1)
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_max_reconnect_attempts=-2)

    def test_model_config_settings(self) -> None:
        """Test that model configuration is properly set."""
        config = BaseNetworkConfig()

        # Check that model_config is properly configured
        assert hasattr(config, "model_config")
        assert config.model_config.get("str_strip_whitespace") is True
        assert config.model_config.get("extra") == "ignore"

    def test_field_descriptions(self) -> None:
        """Test that all fields have proper descriptions."""
        for field_name, field_info in BaseNetworkConfig.model_fields.items():
            assert field_info.description is not None
            assert len(field_info.description) > 0, f"Field {field_name} missing description"

    def test_none_values_rejected(self) -> None:
        """Test that None values are properly rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(
                ws_reconnect_interval=None, ws_max_reconnect_attempts=None, ws_ping_interval=None, ws_ping_timeout=None
            )

        errors = exc_info.value.errors()
        assert len(errors) == 4
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {
            "ws_reconnect_interval",
            "ws_max_reconnect_attempts",
            "ws_ping_interval",
            "ws_ping_timeout",
        }

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored due to model configuration."""
        # Should not raise error due to extra="ignore"
        config = BaseNetworkConfig(ws_reconnect_interval=5, unknown_field="should-be-ignored", another_unknown=123)

        assert config.ws_reconnect_interval == 5
        assert not hasattr(config, "unknown_field")
        assert not hasattr(config, "another_unknown")

    def test_serialization_compatibility(self) -> None:
        """Test that config can be serialized and deserialized."""
        original_config = BaseNetworkConfig(
            ws_reconnect_interval=15, ws_max_reconnect_attempts=5, ws_ping_interval=60, ws_ping_timeout=20
        )

        # Test model_dump
        data = original_config.model_dump()
        assert isinstance(data, dict)
        assert data["ws_reconnect_interval"] == 15
        assert data["ws_max_reconnect_attempts"] == 5
        assert data["ws_ping_interval"] == 60
        assert data["ws_ping_timeout"] == 20

        # Test that we can create a new instance from the data
        new_config = BaseNetworkConfig(**data)
        assert new_config.ws_reconnect_interval == original_config.ws_reconnect_interval
        assert new_config.ws_max_reconnect_attempts == original_config.ws_max_reconnect_attempts
        assert new_config.ws_ping_interval == original_config.ws_ping_interval
        assert new_config.ws_ping_timeout == original_config.ws_ping_timeout

    def test_cross_field_validation_edge_cases(self) -> None:
        """Test edge cases for cross-field validation."""
        # Boundary case: ping_timeout = ping_interval - 1 should work
        config = BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=9)
        assert config.ws_ping_timeout == 9
        assert config.ws_ping_interval == 10

        # Minimum gap between ping_interval and ping_timeout should work
        config = BaseNetworkConfig(ws_ping_interval=2, ws_ping_timeout=1)
        assert config.ws_ping_timeout == 1
        assert config.ws_ping_interval == 2

    def test_field_descriptions_content(self) -> None:
        """Test that field descriptions contain meaningful content."""
        descriptions = {
            field_name: field_info.description for field_name, field_info in BaseNetworkConfig.model_fields.items()
        }

        # Check that descriptions mention key concepts
        assert descriptions["ws_reconnect_interval"] is not None, "ws_reconnect_interval description is missing"
        assert "reconnection" in descriptions["ws_reconnect_interval"].lower()

        assert descriptions["ws_max_reconnect_attempts"] is not None, "ws_max_reconnect_attempts description is missing"
        assert "reconnection" in descriptions["ws_max_reconnect_attempts"].lower()

        assert descriptions["ws_ping_interval"] is not None, "ws_ping_interval description is missing"
        assert "ping" in descriptions["ws_ping_interval"].lower()

        assert descriptions["ws_ping_timeout"] is not None, "ws_ping_timeout description is missing"
        assert "ping" in descriptions["ws_ping_timeout"].lower()

        # Check for specific constraint information
        assert "unlimited" in descriptions["ws_max_reconnect_attempts"].lower()
        assert "-1" in descriptions["ws_max_reconnect_attempts"]

    def test_string_representation(self) -> None:
        """Test string representation contains key information."""
        config = BaseNetworkConfig(
            ws_reconnect_interval=15, ws_max_reconnect_attempts=5, ws_ping_interval=60, ws_ping_timeout=20
        )

        str_repr = str(config)

        # Should contain field values
        assert "15" in str_repr
        assert "5" in str_repr
        assert "60" in str_repr
        assert "20" in str_repr
