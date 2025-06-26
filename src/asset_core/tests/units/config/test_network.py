"""Unit tests for network configuration settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.config import BaseNetworkConfig


@pytest.mark.unit
class TestBaseNetworkConfigConstruction:
    """Test cases for BaseNetworkConfig model construction."""

    def test_default_network_config_creation(self):
        """Test default network configuration initialization.

        Description of what the test covers:
        Verifies that BaseNetworkConfig creates an instance with correct
        default values for all WebSocket-related configuration fields.

        Preconditions:
            - No environment variables set
            - Clean initialization context

        Steps:
            - Create BaseNetworkConfig instance with no arguments
            - Verify all default values are set correctly

        Expected Result:
            - ws_reconnect_interval should be 5 seconds
            - ws_max_reconnect_attempts should be 10
            - ws_ping_interval should be 30 seconds
            - ws_ping_timeout should be 10 seconds
        """
        config = BaseNetworkConfig()

        assert config.ws_reconnect_interval == 5
        assert config.ws_max_reconnect_attempts == 10
        assert config.ws_ping_interval == 30
        assert config.ws_ping_timeout == 10

    def test_custom_network_config_creation(self):
        """Test custom network configuration with explicit values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig correctly accepts and stores
        custom values for all WebSocket configuration parameters.

        Preconditions:
            - Custom values for all configuration fields

        Steps:
            - Create config with custom reconnect, attempts, ping values
            - Verify all provided values are stored correctly

        Expected Result:
            - ws_reconnect_interval should be 3
            - ws_max_reconnect_attempts should be 5
            - ws_ping_interval should be 15
            - ws_ping_timeout should be 5
        """
        config = BaseNetworkConfig(
            ws_reconnect_interval=3, ws_max_reconnect_attempts=5, ws_ping_interval=15, ws_ping_timeout=5
        )

        assert config.ws_reconnect_interval == 3
        assert config.ws_max_reconnect_attempts == 5
        assert config.ws_ping_interval == 15
        assert config.ws_ping_timeout == 5

    def test_network_config_from_dict(self):
        """Test network configuration from dictionary unpacking.

        Description of what the test covers:
        Verifies that BaseNetworkConfig can be initialized by unpacking
        a dictionary containing all configuration parameters.

        Preconditions:
            - Dictionary with all network configuration keys and values

        Steps:
            - Create configuration dictionary with all WebSocket settings
            - Initialize BaseNetworkConfig using dictionary unpacking
            - Verify all values from dictionary are applied

        Expected Result:
            - All dictionary values should be correctly assigned to config fields
        """
        config_dict = {
            "ws_reconnect_interval": 7,
            "ws_max_reconnect_attempts": 15,
            "ws_ping_interval": 45,
            "ws_ping_timeout": 12,
        }

        config = BaseNetworkConfig(**config_dict)

        assert config.ws_reconnect_interval == 7
        assert config.ws_max_reconnect_attempts == 15
        assert config.ws_ping_interval == 45
        assert config.ws_ping_timeout == 12


@pytest.mark.unit
class TestBaseNetworkConfigEnvironmentVariables:
    """Test cases for BaseNetworkConfig environment variable loading."""

    def test_env_var_loading_reconnect_interval(self):
        """Test reconnect interval loading from environment variable.

        Description of what the test covers:
        Verifies that BaseNetworkConfig loads ws_reconnect_interval
        from the WS_RECONNECT_INTERVAL environment variable.

        Preconditions:
            - WS_RECONNECT_INTERVAL environment variable set

        Steps:
            - Mock environment variable WS_RECONNECT_INTERVAL="8"
            - Create BaseNetworkConfig instance
            - Verify value is loaded from environment

        Expected Result:
            - config.ws_reconnect_interval should be 8
        """
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "8"}):
            config = BaseNetworkConfig()
            assert config.ws_reconnect_interval == 8

    def test_env_var_loading_max_reconnect_attempts(self):
        """Test max reconnect attempts loading from environment variable.

        Description of what the test covers:
        Verifies that BaseNetworkConfig loads ws_max_reconnect_attempts
        from the WS_MAX_RECONNECT_ATTEMPTS environment variable.

        Preconditions:
            - WS_MAX_RECONNECT_ATTEMPTS environment variable set

        Steps:
            - Mock environment variable WS_MAX_RECONNECT_ATTEMPTS="20"
            - Create BaseNetworkConfig instance
            - Verify value is loaded from environment

        Expected Result:
            - config.ws_max_reconnect_attempts should be 20
        """
        with patch.dict(os.environ, {"WS_MAX_RECONNECT_ATTEMPTS": "20"}):
            config = BaseNetworkConfig()
            assert config.ws_max_reconnect_attempts == 20

    def test_env_var_loading_ping_interval(self):
        """Test ping interval loading from environment variable.

        Description of what the test covers:
        Verifies that BaseNetworkConfig loads ws_ping_interval
        from the WS_PING_INTERVAL environment variable.

        Preconditions:
            - WS_PING_INTERVAL environment variable set

        Steps:
            - Mock environment variable WS_PING_INTERVAL="60"
            - Create BaseNetworkConfig instance
            - Verify value is loaded from environment

        Expected Result:
            - config.ws_ping_interval should be 60
        """
        with patch.dict(os.environ, {"WS_PING_INTERVAL": "60"}):
            config = BaseNetworkConfig()
            assert config.ws_ping_interval == 60

    def test_env_var_loading_ping_timeout(self):
        """Test ping timeout loading from environment variable.

        Description of what the test covers:
        Verifies that BaseNetworkConfig loads ws_ping_timeout
        from the WS_PING_TIMEOUT environment variable.

        Preconditions:
            - WS_PING_TIMEOUT environment variable set

        Steps:
            - Mock environment variable WS_PING_TIMEOUT="15"
            - Create BaseNetworkConfig instance
            - Verify value is loaded from environment

        Expected Result:
            - config.ws_ping_timeout should be 15
        """
        with patch.dict(os.environ, {"WS_PING_TIMEOUT": "15"}):
            config = BaseNetworkConfig()
            assert config.ws_ping_timeout == 15

    def test_env_var_override_defaults(self):
        """Test environment variables override default configuration.

        Description of what the test covers:
        Verifies that when environment variables are set, they override
        all default network configuration values.

        Preconditions:
            - All network configuration environment variables set

        Steps:
            - Set all WS_* environment variables with custom values
            - Create BaseNetworkConfig instance without arguments
            - Verify all values come from environment variables

        Expected Result:
            - All config values should match environment variable values
            - No default values should be used
        """
        with patch.dict(
            os.environ,
            {
                "WS_RECONNECT_INTERVAL": "2",
                "WS_MAX_RECONNECT_ATTEMPTS": "25",
                "WS_PING_INTERVAL": "20",
                "WS_PING_TIMEOUT": "8",
            },
        ):
            config = BaseNetworkConfig()
            assert config.ws_reconnect_interval == 2
            assert config.ws_max_reconnect_attempts == 25
            assert config.ws_ping_interval == 20
            assert config.ws_ping_timeout == 8

    def test_constructor_args_override_env_vars(self):
        """Test constructor precedence over environment variables.

        Description of what the test covers:
        Verifies that explicit constructor arguments take precedence
        over environment variables for network configuration.

        Preconditions:
            - Environment variables set for some fields
            - Constructor called with different values for same fields

        Steps:
            - Set WS_RECONNECT_INTERVAL and WS_PING_INTERVAL env vars
            - Create config with different constructor arguments
            - Verify constructor arguments take precedence

        Expected Result:
            - Values should come from constructor, not environment
        """
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "10", "WS_PING_INTERVAL": "40"}):
            config = BaseNetworkConfig(ws_reconnect_interval=1, ws_ping_interval=25)
            assert config.ws_reconnect_interval == 1
            assert config.ws_ping_interval == 25


@pytest.mark.unit
class TestBaseNetworkConfigValidation:
    """Test cases for BaseNetworkConfig validation."""

    def test_positive_integer_validation(self):
        """Test acceptance of positive integer values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig accepts positive integer values
        for all configuration fields without validation errors.

        Preconditions:
            - Positive integer values for all fields

        Steps:
            - Create config with all fields set to 1
            - Verify no validation errors occur
            - Verify values are stored correctly

        Expected Result:
            - All fields should accept value 1
            - Values should be stored as integers
        """
        # Test with valid positive integers
        config = BaseNetworkConfig(
            ws_reconnect_interval=1, ws_max_reconnect_attempts=1, ws_ping_interval=1, ws_ping_timeout=1
        )

        assert config.ws_reconnect_interval == 1
        assert config.ws_max_reconnect_attempts == 1
        assert config.ws_ping_interval == 1
        assert config.ws_ping_timeout == 1

    def test_zero_values_allowed(self):
        """Test zero values configuration.

        Description of what the test covers:
        Verifies that BaseNetworkConfig accepts zero values for all
        configuration fields, allowing disabled functionality.

        Preconditions:
        - Zero values for all network configuration fields

        Steps:
        - Create BaseNetworkConfig with all fields set to 0
        - Verify all values are correctly set to zero

        Expected Result:
        - All configuration fields should accept 0 values
        - Zero values disable corresponding features
        """
        config = BaseNetworkConfig(
            ws_reconnect_interval=0, ws_max_reconnect_attempts=0, ws_ping_interval=0, ws_ping_timeout=0
        )

        assert config.ws_reconnect_interval == 0
        assert config.ws_max_reconnect_attempts == 0
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 0

    def test_negative_values_rejected(self):
        """Test rejection of negative configuration values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig raises ValidationError
        when provided with negative values for any configuration field.

        Preconditions:
        - Negative values for different configuration fields

        Steps:
        - Attempt to create config with negative reconnect interval
        - Attempt to create config with invalid negative max attempts (-2, since -1 is allowed)
        - Attempt to create config with negative ping interval
        - Attempt to create config with negative ping timeout
        - Verify ValidationError is raised for each case

        Expected Result:
        - All invalid negative values should be rejected
        - ValidationError raised for each invalid field
        - Note: -1 is valid for ws_max_reconnect_attempts (unlimited)
        """
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_max_reconnect_attempts=-2)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=-1)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout=-1)

    def test_non_integer_values_rejected(self):
        """Test rejection of non-integer configuration values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig raises ValidationError
        when provided with non-integer values for configuration fields.

        Preconditions:
        - Various non-integer values (string, float, None, list)

        Steps:
        - Attempt to create config with string value
        - Attempt to create config with float value
        - Attempt to create config with None value
        - Attempt to create config with list value
        - Verify ValidationError is raised for each case

        Expected Result:
        - All non-integer values should be rejected
        - Only integer values should be accepted
        """
        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_reconnect_interval="not_an_int")

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_max_reconnect_attempts=3.14)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_interval=None)

        with pytest.raises(ValidationError):
            BaseNetworkConfig(ws_ping_timeout=[1, 2, 3])


@pytest.mark.unit
class TestBaseNetworkConfigBoundaryValues:
    """Test cases for BaseNetworkConfig boundary values."""

    def test_minimum_values(self):
        """Test minimum valid configuration values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig accepts the minimum
        valid values (0) for all configuration fields.

        Preconditions:
        - All configuration fields set to minimum value (0)

        Steps:
        - Create BaseNetworkConfig with all fields set to 0
        - Verify all minimum values are correctly stored

        Expected Result:
        - All fields should accept 0 as minimum value
        - Configuration should be valid with zero values
        """
        config = BaseNetworkConfig(
            ws_reconnect_interval=0, ws_max_reconnect_attempts=0, ws_ping_interval=0, ws_ping_timeout=0
        )

        assert config.ws_reconnect_interval == 0
        assert config.ws_max_reconnect_attempts == 0
        assert config.ws_ping_interval == 0
        assert config.ws_ping_timeout == 0

    def test_large_values(self):
        """Test configuration with large timeout values.

        Description of what the test covers:
        Verifies that BaseNetworkConfig accepts large values
        for all configuration fields without upper bound limitations.

        Preconditions:
        - Large values for all network configuration fields

        Steps:
        - Create BaseNetworkConfig with large timeout values
        - Verify all large values are correctly accepted

        Expected Result:
        - 3600 seconds (1 hour) reconnect interval accepted
        - 1000 reconnect attempts accepted
        - 7200 seconds (2 hours) ping interval accepted
        - 600 seconds (10 minutes) ping timeout accepted
        """
        config = BaseNetworkConfig(
            ws_reconnect_interval=3600,  # 1 hour
            ws_max_reconnect_attempts=1000,
            ws_ping_interval=7200,  # 2 hours
            ws_ping_timeout=600,  # 10 minutes
        )

        assert config.ws_reconnect_interval == 3600
        assert config.ws_max_reconnect_attempts == 1000
        assert config.ws_ping_interval == 7200
        assert config.ws_ping_timeout == 600

    def test_realistic_websocket_values(self):
        """Test realistic production WebSocket configuration.

        Description of what the test covers:
        Verifies that BaseNetworkConfig accepts realistic
        configuration values commonly used in production environments.

        Preconditions:
        - Practical values for production WebSocket connections

        Steps:
        - Create BaseNetworkConfig with common production values
        - Verify all realistic values are correctly accepted

        Expected Result:
        - 30 second reconnect interval (reasonable retry delay)
        - 3 reconnect attempts (limited retry count)
        - 30 second ping interval (standard keep-alive)
        - 10 second ping timeout (reasonable response time)
        """
        # Common production values
        config = BaseNetworkConfig(
            ws_reconnect_interval=30, ws_max_reconnect_attempts=3, ws_ping_interval=30, ws_ping_timeout=10
        )

        assert config.ws_reconnect_interval == 30
        assert config.ws_max_reconnect_attempts == 3
        assert config.ws_ping_interval == 30
        assert config.ws_ping_timeout == 10


@pytest.mark.unit
class TestBaseNetworkConfigSerialization:
    """Test cases for BaseNetworkConfig serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        config = BaseNetworkConfig(
            ws_reconnect_interval=5, ws_max_reconnect_attempts=8, ws_ping_interval=25, ws_ping_timeout=12
        )

        data = config.model_dump()

        assert isinstance(data, dict)
        assert data["ws_reconnect_interval"] == 5
        assert data["ws_max_reconnect_attempts"] == 8
        assert data["ws_ping_interval"] == 25
        assert data["ws_ping_timeout"] == 12

    def test_model_dump_json_serializable(self):
        """Test model can be dumped to JSON-serializable format."""
        config = BaseNetworkConfig()

        data = config.model_dump()

        # Should be able to convert to JSON
        import json

        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed_data = json.loads(json_str)
        assert parsed_data["ws_reconnect_interval"] == 5
        assert parsed_data["ws_max_reconnect_attempts"] == 10


@pytest.mark.unit
class TestBaseNetworkConfigStringRepresentation:
    """Test cases for BaseNetworkConfig string representation."""

    def test_string_representation(self):
        """Test string representation."""
        config = BaseNetworkConfig(ws_reconnect_interval=3, ws_max_reconnect_attempts=7)

        str_repr = str(config)

        # Pydantic models return field values in string representation
        assert "ws_reconnect_interval=3" in str_repr
        assert "ws_max_reconnect_attempts=7" in str_repr


@pytest.mark.unit
class TestBaseNetworkConfigEdgeCases:
    """Test cases for BaseNetworkConfig edge cases."""

    def test_string_integer_conversion(self):
        """Test string integer values are converted."""
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "15", "WS_MAX_RECONNECT_ATTEMPTS": "50"}):
            config = BaseNetworkConfig()
            assert config.ws_reconnect_interval == 15
            assert config.ws_max_reconnect_attempts == 50
            assert isinstance(config.ws_reconnect_interval, int)
            assert isinstance(config.ws_max_reconnect_attempts, int)

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored if model allows it."""
        # This should not raise an error if BaseNetworkConfig inherits ignore behavior
        config = BaseNetworkConfig(ws_reconnect_interval=5, unknown_field="should_be_ignored")
        assert config.ws_reconnect_interval == 5
        assert not hasattr(config, "unknown_field")

    def test_timeout_vs_interval_relationships(self):
        """Test logical relationships between timeout and interval values."""
        # Test that ping timeout can be less than ping interval (normal case)
        config = BaseNetworkConfig(ws_ping_interval=30, ws_ping_timeout=10)
        assert config.ws_ping_timeout < config.ws_ping_interval

        # Test that ping timeout can be equal to ping interval
        config = BaseNetworkConfig(ws_ping_interval=30, ws_ping_timeout=30)
        assert config.ws_ping_timeout == config.ws_ping_interval

        # Test that ping timeout can be greater than ping interval (unusual but valid)
        config = BaseNetworkConfig(ws_ping_interval=10, ws_ping_timeout=30)
        assert config.ws_ping_timeout > config.ws_ping_interval


@pytest.mark.unit
class TestBaseNetworkConfigInvalidData:
    """Test cases for BaseNetworkConfig with invalid data."""

    def test_invalid_string_integers(self):
        """Test invalid string integer values."""
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "not_a_number"}), pytest.raises(ValidationError):
            BaseNetworkConfig()

    def test_float_values_converted_to_int(self):
        """Test float values with fractional parts are rejected."""
        # Pydantic validates integers strictly - fractional floats should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_reconnect_interval=5.7, ws_max_reconnect_attempts=10.9)

        # Should contain validation errors for both fields
        errors = exc_info.value.errors()
        assert len(errors) == 2
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"ws_reconnect_interval", "ws_max_reconnect_attempts"}

        # However, whole number floats should work
        config = BaseNetworkConfig(ws_reconnect_interval=5.0, ws_max_reconnect_attempts=10.0)
        assert config.ws_reconnect_interval == 5
        assert config.ws_max_reconnect_attempts == 10
        assert isinstance(config.ws_reconnect_interval, int)
        assert isinstance(config.ws_max_reconnect_attempts, int)

    def test_bool_values_converted_to_int(self):
        """Test boolean values are converted to integers."""
        config = BaseNetworkConfig(
            ws_reconnect_interval=True,  # Should become 1  # type: ignore
            ws_max_reconnect_attempts=False,  # Should become 0  # type: ignore
        )

        assert config.ws_reconnect_interval == 1
        assert config.ws_max_reconnect_attempts == 0


@pytest.mark.unit
@pytest.mark.config
class TestBaseNetworkConfigIntegration:
    """Integration test cases for BaseNetworkConfig."""

    def test_complete_network_configuration(self):
        """Test complete network configuration with all features."""
        with patch.dict(os.environ, {"WS_RECONNECT_INTERVAL": "15", "WS_PING_INTERVAL": "45"}):
            config = BaseNetworkConfig(ws_max_reconnect_attempts=5, ws_ping_timeout=20)

            # Verify mixed sources
            assert config.ws_reconnect_interval == 15  # From env var
            assert config.ws_max_reconnect_attempts == 5  # From constructor
            assert config.ws_ping_interval == 45  # From env var
            assert config.ws_ping_timeout == 20  # From constructor

            # Test serialization
            data = config.model_dump()
            assert data["ws_reconnect_interval"] == 15
            assert data["ws_max_reconnect_attempts"] == 5

            # Test all values are integers
            for value in data.values():
                assert isinstance(value, int)

    def test_websocket_configuration_realism(self):
        """Test realistic WebSocket configuration scenarios."""
        # Scenario 1: High-frequency trading setup
        hft_config = BaseNetworkConfig(
            ws_reconnect_interval=1,  # Quick reconnection
            ws_max_reconnect_attempts=5,
            ws_ping_interval=5,  # Frequent pings
            ws_ping_timeout=2,
        )

        assert hft_config.ws_ping_timeout < hft_config.ws_ping_interval
        assert hft_config.ws_reconnect_interval > 0

        # Scenario 2: Stable connection setup
        stable_config = BaseNetworkConfig(
            ws_reconnect_interval=30,  # Less frequent reconnection
            ws_max_reconnect_attempts=3,
            ws_ping_interval=60,  # Less frequent pings
            ws_ping_timeout=10,
        )

        assert stable_config.ws_ping_timeout < stable_config.ws_ping_interval
        assert stable_config.ws_reconnect_interval > hft_config.ws_reconnect_interval

    def test_configuration_inheritance_compatibility(self):
        """Test extension of BaseNetworkConfig through inheritance.

        Description of what the test covers:
        Verifies that BaseNetworkConfig supports extension
        with additional network fields while preserving
        base WebSocket functionality.

        Preconditions:
        - Base network configuration with custom fields
        - Reconnect interval and ping interval for configuration

        Steps:
        - Define CustomBaseNetworkConfig inheriting from base
        - Add custom field: custom_timeout
        - Create config instance with base and custom parameters
        - Verify base and custom configuration are preserved

        Expected Result:
        - Base fields (ws_reconnect_interval, ws_ping_interval) maintained
        - Custom field added with default value
        - Ability to override both base and custom configuration
        """

        class CustomBaseNetworkConfig(BaseNetworkConfig):
            custom_timeout: int = 100

        config = CustomBaseNetworkConfig(ws_reconnect_interval=5, ws_ping_interval=30)

        assert config.ws_reconnect_interval == 5
        assert config.ws_ping_interval == 30
        assert config.custom_timeout == 100
