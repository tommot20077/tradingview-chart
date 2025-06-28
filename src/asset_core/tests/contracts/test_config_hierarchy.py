"""
Configuration hierarchy and composition tests.

Comprehensive tests to verify configuration inheritance patterns,
composition scenarios, and complex configuration hierarchies.
"""

import os
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import Field, ValidationError

from asset_core.config.base import BaseCoreSettings
from asset_core.config.network import BaseNetworkConfig
from asset_core.config.observability import BaseObservabilityConfig
from asset_core.config.storage import BaseStorageConfig


class CompositeApplicationConfig(BaseCoreSettings, BaseNetworkConfig, BaseObservabilityConfig, BaseStorageConfig):
    """Example composite configuration for testing multiple inheritance.

    Simulates a real application that needs all configuration modules.
    """

    # Application-specific fields
    api_key: str = Field(..., description="API key for external services")
    feature_flags: dict[str, bool] = Field(default_factory=dict, description="Feature toggle flags")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class NetworkStorageConfig(BaseNetworkConfig, BaseStorageConfig):
    """Example configuration combining network and storage settings.

    Tests selective inheritance patterns.
    """

    service_name: str = Field("network-storage-service", description="Service identifier")


class ExtendedCoreConfig(BaseCoreSettings):
    """Extended core configuration for testing inheritance extension.

    This class extends `BaseCoreSettings` to demonstrate how child classes
    can add new fields and override existing ones with additional validation.
    """

    # Additional core fields
    service_version: str = Field("1.0.0", description="Service version")
    max_workers: int = Field(default=4, ge=1, le=32, description="Maximum worker processes")

    # Override parent field with additional validation
    app_name: str = Field(..., min_length=3, max_length=50, description="Application name with length constraints")


class TestConfigurationHierarchy:
    """Test cases for configuration inheritance and composition patterns.

    Verifies that configuration classes can be properly inherited and composed
    to create complex application configurations.
    """

    def test_multiple_config_inheritance(self):
        """Test that a class can inherit from multiple configuration classes.

        Description of what the test covers.
        Verifies that field conflicts are resolved correctly and all
        functionality from parent classes is preserved.

        Expected Result:
        - All parent class fields are available.
        - Field resolution follows MRO (Method Resolution Order).
        - No field conflicts or name collisions.
        - All validators from parent classes work correctly.
        """
        # Test basic instantiation with minimal required fields
        config = CompositeApplicationConfig(
            app_name="test_app", database_url="postgresql://user:pass@localhost/test", api_key="test_api_key_12345"
        )

        # Verify all parent class fields are accessible
        assert hasattr(config, "app_name")  # From BaseCoreSettings
        assert hasattr(config, "ws_reconnect_interval")  # From BaseNetworkConfig
        assert hasattr(config, "log_level")  # From BaseObservabilityConfig
        assert hasattr(config, "database_url")  # From BaseStorageConfig
        assert hasattr(config, "api_key")  # From CompositeApplicationConfig itself

        # Verify field values
        assert config.app_name == "test_app"
        assert config.database_url == "postgresql://user:pass@localhost/test"
        assert config.api_key == "test_api_key_12345"

        # Verify default values from all parent classes
        assert config.environment == "development"  # BaseCoreSettings default
        assert config.ws_reconnect_interval == 5  # BaseNetworkConfig default
        assert config.log_level == "INFO"  # BaseObservabilityConfig default
        assert config.database_pool_size == 10  # BaseStorageConfig default

    def test_selective_config_inheritance(self):
        """Test that classes can selectively inherit from specific config modules.

        Description of what the test covers.
        Verifies that applications can choose which configuration modules
        they need without being forced to include all of them.

        Expected Result:
        - Only selected parent class fields are available.
        - All inherited functionality works correctly.
        - Missing modules don't cause issues.
        """
        config = NetworkStorageConfig(database_url="sqlite:///test.db", service_name="test_service")

        # Should have network and storage fields
        assert hasattr(config, "ws_reconnect_interval")
        assert hasattr(config, "database_url")
        assert hasattr(config, "service_name")

        # Should NOT have core or observability fields
        assert not hasattr(config, "app_name")
        assert not hasattr(config, "log_level")

        # Verify field values and defaults
        assert config.database_url == "sqlite:///test.db"
        assert config.service_name == "test_service"
        assert config.ws_reconnect_interval == 5  # Default from BaseNetworkConfig
        assert config.database_pool_size == 10  # Default from BaseStorageConfig

    def test_config_field_precedence_in_inheritance(self):
        """Test field precedence when the same field is defined in multiple parents.

        Description of what the test covers.
        Verifies that Python's Method Resolution Order (MRO) is correctly
        followed for field definitions and validators.

        Expected Result:
        - Field definitions follow MRO.
        - Later classes in inheritance chain take precedence.
        - Validators are properly inherited and applied.
        """

        # Create a class that has potential field conflicts
        class ConflictTestConfig(BaseCoreSettings, BaseNetworkConfig):
            # Both parents could potentially have conflicting fields
            # Test that MRO resolves this correctly
            timeout: int = Field(default=30, description="Custom timeout field")

        config = ConflictTestConfig(app_name="test_conflict")

        # Verify MRO is respected
        mro = ConflictTestConfig.__mro__
        assert BaseCoreSettings in mro
        assert BaseNetworkConfig in mro

        # Verify field access works correctly
        assert config.app_name == "test_conflict"
        assert config.timeout == 30

        # Verify that we can access fields from both parents
        assert hasattr(config, "environment")  # From BaseCoreSettings
        assert hasattr(config, "ws_reconnect_interval")  # From BaseNetworkConfig

    def test_extended_config_validation_enhancement(self):
        """Test that child classes can enhance parent class validation.

        Description of what the test covers.
        Verifies that child classes can add additional validation
        constraints to fields inherited from parent classes.

        Expected Result:
        - Child class validators are applied in addition to parent validators.
        - Enhanced validation catches additional error cases.
        - Valid values that meet all constraints work correctly.
        """
        # Test valid configuration that meets enhanced constraints
        config = ExtendedCoreConfig(
            app_name="MyApp",  # Meets min_length=3, max_length=50
            service_version="2.1.0",
            max_workers=8,
        )

        assert config.app_name == "MyApp"
        assert config.service_version == "2.1.0"
        assert config.max_workers == 8

        # Test that enhanced validation catches violations
        with pytest.raises(ValidationError) as exc_info:
            ExtendedCoreConfig(
                app_name="AB",  # Violates min_length=3
                service_version="1.0.0",
            )

        error_details = exc_info.value.errors()
        app_name_errors = [e for e in error_details if e["loc"] == ("app_name",)]
        assert len(app_name_errors) > 0
        assert "at least 3 characters" in str(app_name_errors[0]["msg"])

        # Test max_length validation
        with pytest.raises(ValidationError) as exc_info:
            ExtendedCoreConfig(
                app_name="A" * 51,  # Violates max_length=50
                service_version="1.0.0",
            )

        error_details = exc_info.value.errors()
        app_name_errors = [e for e in error_details if e["loc"] == ("app_name",)]
        assert len(app_name_errors) > 0
        assert "at most 50 characters" in str(app_name_errors[0]["msg"])

        # Test max_workers range validation
        with pytest.raises(ValidationError) as exc_info:
            ExtendedCoreConfig(
                app_name="ValidApp",
                max_workers=0,  # Violates ge=1
            )

        error_details = exc_info.value.errors()
        workers_errors = [e for e in error_details if e["loc"] == ("max_workers",)]
        assert len(workers_errors) > 0
        assert "greater than or equal to 1" in str(workers_errors[0]["msg"])

    def test_cross_config_environment_variable_loading(self):
        """Test environment variable loading with multiple inheritance.

        Description of what the test covers.
        Verifies that environment variables are correctly loaded
        for all fields across multiple inherited configuration classes.

        Expected Result:
        - Environment variables work for all inherited fields.
        - No conflicts between environment variable names.
        - Proper type conversion for all field types.
        """
        env_vars = {
            "APP_NAME": "env_test_app",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "WS_RECONNECT_INTERVAL": "10",
            "WS_MAX_RECONNECT_ATTEMPTS": "5",
            "LOG_LEVEL": "WARNING",
            "METRICS_ENABLED": "true",
            "DATABASE_URL": "postgresql://user:pass@localhost/envtest",
            "DATABASE_POOL_SIZE": "20",
            "API_KEY": "env_api_key_67890",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = CompositeApplicationConfig()

            # Verify environment variables loaded correctly
            assert config.app_name == "env_test_app"
            assert config.environment == "production"
            assert config.debug is False
            assert config.ws_reconnect_interval == 10
            assert config.ws_max_reconnect_attempts == 5
            assert config.log_level == "WARNING"
            assert config.metrics_enabled is True
            assert config.database_url == "postgresql://user:pass@localhost/envtest"
            assert config.database_pool_size == 20
            assert config.api_key == "env_api_key_67890"

    def test_config_serialization_with_inheritance(self):
        """Test configuration serialization with multiple inheritance.

        Description of what the test covers.
        Verifies that configurations with complex inheritance
        can be properly serialized and deserialized.

        Expected Result:
        - `model_dump()` includes all inherited fields.
        - Serialized data can recreate the configuration.
        - No information loss during serialization.
        """
        original_config = CompositeApplicationConfig(
            app_name="serialization_test",
            environment="staging",
            debug=True,
            ws_reconnect_interval=15,
            log_level="DEBUG",
            metrics_enabled=True,
            database_url="postgresql://test:test@localhost/serialize",
            database_pool_size=5,
            api_key="serialize_key_123",
            feature_flags={"feature_a": True, "feature_b": False},
        )

        # Test serialization
        serialized = original_config.model_dump()

        # Verify all fields are included
        expected_fields = {
            "app_name",
            "environment",
            "debug",  # BaseCoreSettings
            "ws_reconnect_interval",
            "ws_max_reconnect_attempts",
            "ws_ping_interval",
            "ws_ping_timeout",  # BaseNetworkConfig
            "log_level",
            "log_format",
            "metrics_enabled",
            "metrics_port",  # BaseObservabilityConfig
            "database_url",
            "database_pool_size",
            "database_timeout",
            "data_directory",
            "max_file_size",  # BaseStorageConfig
            "api_key",
            "feature_flags",  # CompositeApplicationConfig
        }

        assert set(serialized.keys()) == expected_fields

        # Test deserialization
        recreated_config = CompositeApplicationConfig(**serialized)

        # Verify all values match
        assert recreated_config.app_name == original_config.app_name
        assert recreated_config.environment == original_config.environment
        assert recreated_config.debug == original_config.debug
        assert recreated_config.ws_reconnect_interval == original_config.ws_reconnect_interval
        assert recreated_config.log_level == original_config.log_level
        assert recreated_config.database_url == original_config.database_url
        assert recreated_config.api_key == original_config.api_key
        assert recreated_config.feature_flags == original_config.feature_flags

    def test_config_method_inheritance(self):
        """Test that methods from parent configuration classes are inherited correctly.

        Description of what the test covers.
        Verifies that utility methods and properties from parent classes
        are available and work correctly in child classes.

        Expected Result:
        - All parent class methods are accessible.
        - Method functionality is preserved.
        - Method overriding works correctly when needed.
        """
        config = CompositeApplicationConfig(
            app_name="method_test",
            environment="production",
            database_url="postgresql://test:test@localhost/methods",
            api_key="method_key_456",
        )

        # Test methods from BaseCoreSettings
        assert hasattr(config, "is_production")
        assert hasattr(config, "is_development")

        assert config.is_production() is True
        assert config.is_development() is False

        # Change environment and test again
        config.environment = "development"
        assert config.is_production() is False
        assert config.is_development() is True

    def test_config_validation_error_aggregation(self):
        """Test that validation errors from multiple inherited classes are properly aggregated.

        Description of what the test covers.
        Verifies that when multiple fields from different parent classes
        have validation errors, all errors are reported together.

        Expected Result:
        - All validation errors are collected and reported.
        - Errors from different parent classes are included.
        - Error messages are clear and specific.
        """
        with pytest.raises(ValidationError) as exc_info:
            CompositeApplicationConfig(
                app_name="",  # Invalid: empty string (BaseCoreSettings)
                environment="invalid_env",  # Invalid: not in allowed values (BaseCoreSettings)
                ws_reconnect_interval=-1,  # Invalid: negative value (BaseNetworkConfig)
                log_level="INVALID_LEVEL",  # Invalid: not in allowed levels (BaseObservabilityConfig)
                database_url="",  # Invalid: empty string (BaseStorageConfig)
                database_pool_size=0,  # Invalid: must be > 0 (BaseStorageConfig)
                api_key="",  # Invalid: empty string (CompositeApplicationConfig)
            )

        error_details = exc_info.value.errors()

        # Should have errors from all configuration classes
        error_fields = {error["loc"][0] for error in error_details}

        expected_error_fields = {
            "app_name",  # BaseCoreSettings
            "environment",  # BaseCoreSettings
            "ws_reconnect_interval",  # BaseNetworkConfig
            "log_level",  # BaseObservabilityConfig
            "database_url",  # BaseStorageConfig
            "database_pool_size",  # BaseStorageConfig
            "api_key",  # CompositeApplicationConfig
        }

        # Verify we have errors from multiple parent classes
        assert len(error_fields.intersection(expected_error_fields)) >= 5

        # Verify specific error messages are meaningful
        error_messages = [error["msg"] for error in error_details]
        # Check for common validation error patterns (adjust based on actual Pydantic v2 messages)
        has_length_error = any(
            "at least 1 character" in msg or "String should have at least 1 character" in msg for msg in error_messages
        )
        has_range_error = any(
            "greater than or equal to 0" in msg or "Input should be greater than or equal to 0" in msg
            for msg in error_messages
        )

        # At least one of these should be true for our test case
        assert has_length_error or has_range_error, f"Expected validation errors not found in: {error_messages}"

    def test_diamond_inheritance_resolution(self):
        """Test diamond inheritance pattern resolution.

        Description of what the test covers.
        Creates a scenario where multiple inheritance could create
        diamond inheritance patterns and verifies proper resolution.

        Expected Result:
        - MRO is correctly calculated.
        - No duplicate method calls.
        - Field conflicts resolved predictably.
        """

        # Create a diamond inheritance scenario
        class BaseA(BaseCoreSettings):
            shared_field: str = Field(default="from_a", description="Shared field from A")

        class BaseB(BaseCoreSettings):
            shared_field: str = Field(default="from_b", description="Shared field from B")

        class DiamondConfig(BaseA, BaseB):
            app_specific: str = Field(default="diamond_test", description="App specific field")

        config = DiamondConfig(app_name="diamond_app")

        # Verify MRO resolves the diamond correctly
        mro = DiamondConfig.__mro__

        # Should resolve to: DiamondConfig -> BaseA -> BaseB -> BaseCoreSettings -> BaseSettings -> object
        assert DiamondConfig in mro
        assert BaseA in mro
        assert BaseB in mro
        assert BaseCoreSettings in mro

        # Verify field resolution follows MRO (BaseA should win over BaseB)
        assert config.shared_field == "from_a"
        assert config.app_specific == "diamond_test"
        assert config.app_name == "diamond_app"

    def test_configuration_composition_vs_inheritance(self):
        """Test configuration composition patterns as an alternative to inheritance.

        Description of what the test covers.
        Verifies that configurations can be composed rather than inherited
        for more flexible architecture patterns.

        Expected Result:
        - Composition provides access to all configuration data.
        - Type safety is maintained.
        - Configuration updates work correctly.
        """
        # Create separate configuration instances
        core_config = BaseCoreSettings(app_name="composed_app", environment="production")
        network_config = BaseNetworkConfig(ws_reconnect_interval=8, ws_max_reconnect_attempts=3)
        storage_config = BaseStorageConfig(
            database_url="postgresql://composed:test@localhost/compose", database_pool_size=15
        )

        # Create a composition class
        class ComposedAppConfiguration:
            def __init__(self, core: BaseCoreSettings, network: BaseNetworkConfig, storage: BaseStorageConfig):
                self.core = core
                self.network = network
                self.storage = storage

            def to_dict(self) -> dict[str, Any]:
                return {
                    "core": self.core.model_dump(),
                    "network": self.network.model_dump(),
                    "storage": self.storage.model_dump(),
                }

            @property
            def is_production(self) -> bool:
                return self.core.is_production()

        composed_config = ComposedAppConfiguration(core_config, network_config, storage_config)

        # Verify composition provides access to all data
        assert composed_config.core.app_name == "composed_app"
        assert composed_config.network.ws_reconnect_interval == 8
        assert composed_config.storage.database_pool_size == 15
        assert composed_config.is_production is True

        # Verify serialization works
        serialized = composed_config.to_dict()
        assert "core" in serialized
        assert "network" in serialized
        assert "storage" in serialized
        assert serialized["core"]["app_name"] == "composed_app"
