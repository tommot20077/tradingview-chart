"""ABOUTME: Unit tests for base configuration module
ABOUTME: Testing BaseCoreSettings initialization, validation, and behavior
"""

import pytest
from pydantic import ValidationError

from asset_core.config.base import BaseCoreSettings


@pytest.mark.unit
class TestBaseCoreSettings:
    """Unit tests for BaseCoreSettings class."""

    def test_default_values(self) -> None:
        """Test that default values are correctly set."""
        settings = BaseCoreSettings()

        assert settings.app_name == "asset-core"
        assert settings.environment == "development"
        assert settings.debug is False

    def test_explicit_initialization(self) -> None:
        """Test explicit initialization with custom values."""
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        assert settings.app_name == "test-app"
        assert settings.environment == "production"
        assert settings.debug is True

    def test_environment_validation_case_insensitive(self) -> None:
        """Test that environment validation is case insensitive."""
        valid_environments = [
            ("development", "development"),
            ("Development", "development"),
            ("DEVELOPMENT", "development"),
            ("staging", "staging"),
            ("Staging", "staging"),
            ("STAGING", "staging"),
            ("production", "production"),
            ("Production", "production"),
            ("PRODUCTION", "production"),
        ]

        for input_env, expected_env in valid_environments:
            settings = BaseCoreSettings(environment=input_env)
            assert settings.environment == expected_env

    def test_environment_validation_invalid_values(self) -> None:
        """Test that invalid environment values are rejected."""
        invalid_environments = ["test", "dev", "prod", "stage", "invalid", ""]

        for invalid_env in invalid_environments:
            with pytest.raises(ValidationError) as exc_info:
                BaseCoreSettings(environment=invalid_env)

            error_msg = str(exc_info.value)
            assert "environment must be one of" in error_msg

    def test_is_production_method(self) -> None:
        """Test is_production method functionality."""
        prod_settings = BaseCoreSettings(environment="production")
        dev_settings = BaseCoreSettings(environment="development")
        staging_settings = BaseCoreSettings(environment="staging")

        assert prod_settings.is_production() is True
        assert dev_settings.is_production() is False
        assert staging_settings.is_production() is False

    def test_is_development_method(self) -> None:
        """Test is_development method functionality."""
        prod_settings = BaseCoreSettings(environment="production")
        dev_settings = BaseCoreSettings(environment="development")
        staging_settings = BaseCoreSettings(environment="staging")

        assert dev_settings.is_development() is True
        assert prod_settings.is_development() is False
        assert staging_settings.is_development() is False

    def test_model_config_settings(self) -> None:
        """Test that model configuration is properly set."""
        settings = BaseCoreSettings()

        # Check that model_config is properly configured
        assert hasattr(settings, "model_config")
        assert settings.model_config.get("env_file") == ".env"
        assert settings.model_config.get("env_file_encoding") == "utf-8"
        assert settings.model_config.get("case_sensitive") is False
        assert settings.model_config.get("extra") == "ignore"

    def test_field_descriptions(self) -> None:
        """Test that all fields have proper descriptions."""
        for field_name, field_info in BaseCoreSettings.model_fields.items():
            assert field_info.description is not None
            assert len(field_info.description) > 0, f"Field {field_name} missing description"

    def test_type_validation(self) -> None:
        """Test type validation for fields."""
        # Valid types should work
        settings = BaseCoreSettings(app_name="test", environment="development", debug=True)
        assert isinstance(settings.app_name, str)
        assert isinstance(settings.environment, str)
        assert isinstance(settings.debug, bool)

        # Invalid types should raise ValidationError
        with pytest.raises(ValidationError):
            BaseCoreSettings(debug="not-a-boolean")

    def test_none_values_rejected(self) -> None:
        """Test that None values are properly rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(app_name=None, environment=None, debug=None)

        errors = exc_info.value.errors()
        assert len(errors) == 3
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"app_name", "environment", "debug"}

    def test_empty_string_app_name_allowed(self) -> None:
        """Test that empty string app_name is allowed."""
        settings = BaseCoreSettings(app_name="")
        assert settings.app_name == ""

    def test_unicode_app_name_support(self) -> None:
        """Test that unicode characters are supported in app_name."""
        unicode_name = "测试应用"
        settings = BaseCoreSettings(app_name=unicode_name)
        assert settings.app_name == unicode_name

    def test_whitespace_handling_in_app_name(self) -> None:
        """Test whitespace handling in app_name field."""
        # Whitespace should be preserved in app_name
        app_name_with_spaces = "  test app  "
        settings = BaseCoreSettings(app_name=app_name_with_spaces)
        assert settings.app_name == app_name_with_spaces

    def test_serialization_compatibility(self) -> None:
        """Test that settings can be serialized and deserialized."""
        original_settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        # Test model_dump
        data = original_settings.model_dump()
        assert isinstance(data, dict)
        assert data["app_name"] == "test-app"
        assert data["environment"] == "production"
        assert data["debug"] is True

        # Test that we can create a new instance from the data
        new_settings = BaseCoreSettings(**data)
        assert new_settings.app_name == original_settings.app_name
        assert new_settings.environment == original_settings.environment
        assert new_settings.debug == original_settings.debug

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored due to model configuration."""
        # Should not raise error due to extra="ignore"
        settings = BaseCoreSettings(app_name="test-app", unknown_field="should-be-ignored", another_unknown=123)

        assert settings.app_name == "test-app"
        assert not hasattr(settings, "unknown_field")
        assert not hasattr(settings, "another_unknown")

    def test_string_representation(self) -> None:
        """Test string representation contains key information."""
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        str_repr = str(settings)

        # Should contain key field values
        assert "test-app" in str_repr
        assert "production" in str_repr
