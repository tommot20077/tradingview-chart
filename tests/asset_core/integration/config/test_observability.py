import os
from unittest.mock import patch

import pytest

from asset_core.config import BaseObservabilityConfig


@pytest.mark.integration
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
