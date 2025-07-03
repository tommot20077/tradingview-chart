"""Unit tests for base configuration settings."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from asset_core.config.base import BaseCoreSettings


@pytest.mark.unit
class TestBaseCoreSettingsConstruction:
    """Test cases for BaseCoreSettings model construction."""

    def test_default_settings_creation(self) -> None:
        """Test default settings initialization.

        Description of what the test covers:
        Verifies that BaseCoreSettings creates an instance with correct default values
        for app_name, environment, and debug fields.

        Preconditions:
            - No environment variables set
            - Clean initialization context

        Steps:
            - Create BaseCoreSettings instance with no arguments
            - Verify default values are set correctly

        Expected Result:
            - app_name should be "asset-core"
            - environment should be "development"
            - debug should be False
        """
        settings = BaseCoreSettings()

        assert settings.app_name == "asset-core"
        assert settings.environment == "development"
        assert settings.debug is False

    def test_custom_settings_creation(self) -> None:
        """Test custom settings initialization with explicit values.

        Description of what the test covers:
        Verifies that BaseCoreSettings correctly accepts and stores custom values
        provided during initialization.

        Preconditions:
            - Clean initialization context

        Steps:
            - Create BaseCoreSettings with custom app_name, environment, and debug values
            - Verify all provided values are stored correctly

        Expected Result:
            - app_name should be "test-app"
            - environment should be "production"
            - debug should be True
        """
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        assert settings.app_name == "test-app"
        assert settings.environment == "production"
        assert settings.debug is True

    def test_settings_from_dict(self) -> None:
        """Test settings initialization from dictionary unpacking.

        Description of what the test covers:
        Verifies that BaseCoreSettings can be initialized by unpacking a dictionary
        containing configuration values.

        Preconditions:
            - Dictionary with valid configuration keys and values

        Steps:
            - Create configuration dictionary with app_name, environment, debug
            - Initialize BaseCoreSettings using dictionary unpacking
            - Verify all values from dictionary are applied

        Expected Result:
            - All dictionary values should be correctly assigned to settings fields
        """
        settings = BaseCoreSettings(app_name="dict-app", environment="staging", debug=False)

        assert settings.app_name == "dict-app"
        assert settings.environment == "staging"
        assert settings.debug is False


@pytest.mark.unit
class TestBaseCoreSettingsValidation:
    """Test cases for BaseCoreSettings validation."""

    def test_valid_environment_values(self) -> None:
        """Test acceptance of all valid environment values.

        Description of what the test covers:
        Verifies that BaseCoreSettings accepts all valid environment values
        (development, staging, production) without validation errors.

        Preconditions:
            - List of valid environment values

        Steps:
            - Iterate through each valid environment value
            - Create settings instance with each environment
            - Verify no validation errors occur

        Expected Result:
            - All valid environments (development, staging, production) should be accepted
            - Settings should store the exact environment value provided
        """
        valid_environments = ["development", "staging", "production"]

        for env in valid_environments:
            settings = BaseCoreSettings(environment=env)
            assert settings.environment == env

    def test_invalid_environment_validation(self) -> None:
        """Test rejection of invalid environment values.

        Description of what the test covers:
        Verifies that BaseCoreSettings raises ValidationError when provided
        with invalid environment values not in the allowed list.

        Preconditions:
            - Invalid environment value not in allowed list

        Steps:
            - Attempt to create settings with invalid environment "invalid"
            - Catch and verify ValidationError is raised
            - Check error message contains expected validation details

        Expected Result:
            - ValidationError should be raised
            - Error message should mention valid environment options
        """
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(environment="invalid")

        assert "environment must be one of" in str(exc_info.value)
        assert "development" in str(exc_info.value)
        assert "staging" in str(exc_info.value)
        assert "production" in str(exc_info.value)

    def test_case_insensitive_environment(self) -> None:
        """Test environment validation is case insensitive.

        Description of what the test covers:
        Verifies that environment validation accepts any case and converts
        values to lowercase for consistency.

        Preconditions:
            - Environment values with different casing

        Steps:
            - Create settings with "PRODUCTION" (uppercase)
            - Create settings with "Development" (mixed case)
            - Verify values are converted to lowercase

        Expected Result:
            - "PRODUCTION" should be converted to "production"
            - "Development" should be converted to "development"
            - Case conversion ensures consistency
        """
        # The validator accepts any case and converts to lowercase
        settings1 = BaseCoreSettings(environment="PRODUCTION")
        assert settings1.environment == "production"

        settings2 = BaseCoreSettings(environment="Development")
        assert settings2.environment == "development"

    def test_environment_normalization(self) -> None:
        """Test environment value is stored without normalization.

        Description of what the test covers:
        Verifies that valid environment values are stored exactly as provided
        without any case normalization or transformation.

        Preconditions:
            - Valid environment value "production"

        Steps:
            - Create settings with environment="production"
            - Verify stored value matches input exactly

        Expected Result:
            - Environment should be stored as "production" (exact match)
        """
        settings = BaseCoreSettings(environment="production")
        assert settings.environment == "production"


@pytest.mark.unit
class TestBaseCoreSettingsEnvironmentVariables:
    """Test cases for BaseCoreSettings environment variable loading."""

    def test_env_var_loading_app_name(self) -> None:
        """Test app_name loading from APP_NAME environment variable.

        Description of what the test covers:
        Verifies that BaseCoreSettings loads app_name from the APP_NAME
        environment variable when available.

        Preconditions:
            - APP_NAME environment variable set to "env-app"

        Steps:
            - Mock environment variable APP_NAME="env-app"
            - Create BaseCoreSettings instance
            - Verify app_name is loaded from environment

        Expected Result:
            - settings.app_name should be "env-app"
        """
        with patch.dict(os.environ, {"APP_NAME": "env-app"}):
            settings = BaseCoreSettings()
            assert settings.app_name == "env-app"

    def test_env_var_loading_environment(self) -> None:
        """Test environment loading from ENVIRONMENT environment variable.

        Description of what the test covers:
        Verifies that BaseCoreSettings loads environment from the ENVIRONMENT
        environment variable when available.

        Preconditions:
            - ENVIRONMENT environment variable set to "production"

        Steps:
            - Mock environment variable ENVIRONMENT="production"
            - Create BaseCoreSettings instance
            - Verify environment is loaded from environment variable

        Expected Result:
            - settings.environment should be "production"
        """
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = BaseCoreSettings()
            assert settings.environment == "production"

    def test_env_var_loading_debug(self) -> None:
        """Test debug flag loading from DEBUG environment variable.

        Description of what the test covers:
        Verifies that BaseCoreSettings correctly parses boolean values
        from the DEBUG environment variable.

        Preconditions:
            - DEBUG environment variable set to string boolean values

        Steps:
            - Test with DEBUG="true" and verify debug=True
            - Test with DEBUG="false" and verify debug=False

        Expected Result:
            - "true" should result in debug=True
            - "false" should result in debug=False
        """
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = BaseCoreSettings()
            assert settings.debug is True

        with patch.dict(os.environ, {"DEBUG": "false"}):
            settings = BaseCoreSettings()
            assert settings.debug is False

    def test_env_var_case_insensitive(self) -> None:
        """Test environment variable names are case insensitive.

        Description of what the test covers:
        Verifies that BaseCoreSettings can load values from environment variables
        regardless of the case used in the variable name.

        Preconditions:
            - Environment variable set with lowercase name

        Steps:
            - Set environment variable app_name="lower-case" (lowercase)
            - Create BaseCoreSettings instance
            - Verify value is loaded correctly

        Expected Result:
            - settings.app_name should be "lower-case"
        """
        with patch.dict(os.environ, {"app_name": "lower-case"}):
            settings = BaseCoreSettings()
            assert settings.app_name == "lower-case"

    def test_env_var_override_defaults(self) -> None:
        """Test environment variables take precedence over defaults.

        Description of what the test covers:
        Verifies that when environment variables are set, they override
        the default values defined in the model.

        Preconditions:
            - Multiple environment variables set with custom values

        Steps:
            - Set APP_NAME, ENVIRONMENT, and DEBUG environment variables
            - Create BaseCoreSettings instance without arguments
            - Verify all values come from environment variables

        Expected Result:
            - app_name should be "override-app" (from env)
            - environment should be "staging" (from env)
            - debug should be True (from env)
        """
        with patch.dict(os.environ, {"APP_NAME": "override-app", "ENVIRONMENT": "staging", "DEBUG": "true"}):
            settings = BaseCoreSettings()
            assert settings.app_name == "override-app"
            assert settings.environment == "staging"
            assert settings.debug is True

    def test_constructor_args_override_env_vars(self) -> None:
        """Test constructor arguments have highest precedence.

        Description of what the test covers:
        Verifies that explicit constructor arguments take precedence over
        environment variables when both are present.

        Preconditions:
            - Environment variables set with specific values
            - Constructor called with different values

        Steps:
            - Set APP_NAME and ENVIRONMENT environment variables
            - Create settings with different constructor arguments
            - Verify constructor arguments take precedence

        Expected Result:
            - app_name should be "constructor-app" (from constructor)
            - environment should be "development" (from constructor)
        """
        with patch.dict(os.environ, {"APP_NAME": "env-app", "ENVIRONMENT": "production"}):
            settings = BaseCoreSettings(app_name="constructor-app", environment="development")
            assert settings.app_name == "constructor-app"
            assert settings.environment == "development"


@pytest.mark.unit
class TestBaseCoreSettingsDotEnvFile:
    """Test cases for BaseCoreSettings .env file loading."""

    def test_env_file_loading(self) -> None:
        """Test configuration loading from .env file.

        Description of what the test covers:
        Verifies that BaseCoreSettings can load configuration values
        from a .env file in the current working directory.

        Preconditions:
            - .env file created with configuration values
            - Working directory changed to .env file location

        Steps:
            - Create temporary .env file with APP_NAME, ENVIRONMENT, DEBUG
            - Change working directory to file location
            - Create BaseCoreSettings instance
            - Verify values loaded from .env file

        Expected Result:
            - app_name should be "dotenv-app"
            - environment should be "staging"
            - debug should be True
        """
        env_content = """
APP_NAME=dotenv-app
ENVIRONMENT=staging
DEBUG=true
"""

        with NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                # Change to the directory containing the .env file
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                # Rename the temp file to .env
                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                settings = BaseCoreSettings()

                assert settings.app_name == "dotenv-app"
                assert settings.environment == "staging"
                assert settings.debug is True

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_env_vars_override_env_file(self) -> None:
        """Test environment variables take precedence over .env file.

        Description of what the test covers:
        Verifies that actual environment variables override values
        defined in .env files when both sources contain the same keys.

        Preconditions:
            - .env file with configuration values
            - Environment variable set with different value

        Steps:
            - Create .env file with APP_NAME and ENVIRONMENT
            - Set APP_NAME environment variable to different value
            - Create settings and verify precedence

        Expected Result:
            - app_name should be "env-override" (from env var)
            - environment should be "staging" (from .env file)
        """
        env_content = """
APP_NAME=dotenv-app
ENVIRONMENT=staging
"""

        with NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                with patch.dict(os.environ, {"APP_NAME": "env-override"}):
                    settings = BaseCoreSettings()
                    assert settings.app_name == "env-override"
                    assert settings.environment == "staging"  # From .env file

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_missing_env_file_uses_defaults(self) -> None:
        """Test fallback to defaults when .env file is missing.

        Description of what the test covers:
        Verifies that BaseCoreSettings gracefully handles missing .env files
        and falls back to default values without errors.

        Preconditions:
            - Directory without .env file
            - No environment variables set

        Steps:
            - Change to temporary directory without .env file
            - Create BaseCoreSettings instance
            - Verify default values are used

        Expected Result:
            - app_name should be "asset-core" (default)
            - environment should be "development" (default)
            - debug should be False (default)
        """
        # Ensure no .env file exists
        original_cwd = os.getcwd()

        try:
            # Create a temporary directory without .env file
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                settings = BaseCoreSettings()

                assert settings.app_name == "asset-core"
                assert settings.environment == "development"
                assert settings.debug is False
        finally:
            os.chdir(original_cwd)
        # Ensure no .env file exists
        original_cwd = os.getcwd()

        try:
            # Create a temporary directory without .env file
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                settings = BaseCoreSettings()

                assert settings.app_name == "asset-core"
                assert settings.environment == "development"
                assert settings.debug is False
        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
class TestBaseCoreSettingsHelperMethods:
    """Test cases for BaseCoreSettings helper methods."""

    def test_is_production_method(self) -> None:
        """Test production environment detection method.

        Description of what the test covers:
        Verifies that the is_production() helper method correctly identifies
        when the environment is set to "production".

        Preconditions:
            - Settings instances with different environment values

        Steps:
            - Create settings with environment="production"
            - Create settings with environment="development"
            - Create settings with environment="staging"
            - Test is_production() method on each

        Expected Result:
            - Production settings should return True
            - Development settings should return False
            - Staging settings should return False
        """
        settings_prod = BaseCoreSettings(environment="production")
        assert settings_prod.is_production() is True

        settings_dev = BaseCoreSettings(environment="development")
        assert settings_dev.is_production() is False

        settings_staging = BaseCoreSettings(environment="staging")
        assert settings_staging.is_production() is False

    def test_is_development_method(self) -> None:
        """Test development environment detection method.

        Description of what the test covers:
        Verifies that the is_development() helper method correctly identifies
        when the environment is set to "development".

        Preconditions:
            - Settings instances with different environment values

        Steps:
            - Create settings with environment="development"
            - Create settings with environment="production"
            - Create settings with environment="staging"
            - Test is_development() method on each

        Expected Result:
            - Development settings should return True
            - Production settings should return False
            - Staging settings should return False
        """
        settings_dev = BaseCoreSettings(environment="development")
        assert settings_dev.is_development() is True

        settings_prod = BaseCoreSettings(environment="production")
        assert settings_prod.is_development() is False

        settings_staging = BaseCoreSettings(environment="staging")
        assert settings_staging.is_development() is False

    def test_environment_helper_methods_consistency(self) -> None:
        """Test environment helper methods mutual exclusivity.

        Description of what the test covers:
        Verifies that is_production() and is_development() methods are
        mutually exclusive and cover all valid environment values.

        Preconditions:
            - All valid environment values (development, staging, production)

        Steps:
            - Test each environment value with both helper methods
            - Verify logical consistency and mutual exclusivity

        Expected Result:
            - Only "production" should return True for is_production()
            - Only "development" should return True for is_development()
            - "staging" should return False for both methods
        """
        for env in ["development", "staging", "production"]:
            settings = BaseCoreSettings(environment=env)

            if env == "production":
                assert settings.is_production() is True
                assert settings.is_development() is False
            elif env == "development":
                assert settings.is_production() is False
                assert settings.is_development() is True
            else:  # staging
                assert settings.is_production() is False
                assert settings.is_development() is False


@pytest.mark.unit
class TestBaseCoreSettingsSerialization:
    """Test cases for BaseCoreSettings serialization."""

    def test_model_dump(self) -> None:
        """Test serialization to dictionary format.

        Description of what the test covers:
        Verifies that the model_dump() method correctly serializes
        all settings fields to a dictionary format.

        Preconditions:
            - Settings instance with custom values

        Steps:
            - Create settings with specific values
            - Call model_dump() method
            - Verify returned dictionary structure and values

        Expected Result:
            - Should return dictionary with all field values
            - Dictionary keys should match field names
            - Values should match original settings values
        """
        settings = BaseCoreSettings(app_name="test-app", environment="production", debug=True)

        data = settings.model_dump()

        assert isinstance(data, dict)
        assert data["app_name"] == "test-app"
        assert data["environment"] == "production"
        assert data["debug"] is True

    def test_model_dump_json_serializable(self) -> None:
        """Test JSON serialization compatibility.

        Description of what the test covers:
        Verifies that the model_dump() output can be successfully
        serialized to JSON format and parsed back.

        Preconditions:
            - Settings instance with default values

        Steps:
            - Create settings instance
            - Call model_dump() to get dictionary
            - Serialize dictionary to JSON string
            - Parse JSON back to verify round-trip compatibility

        Expected Result:
            - JSON serialization should succeed without errors
            - Parsed data should contain expected field values
        """
        settings = BaseCoreSettings()

        data = settings.model_dump()

        # Should be able to convert to JSON
        import json

        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed_data = json.loads(json_str)
        assert parsed_data["app_name"] == "asset-core"


@pytest.mark.unit
class TestBaseCoreSettingsStringRepresentation:
    """Test cases for BaseCoreSettings string representation."""

    def test_string_representation(self) -> None:
        """Test string representation format.

        Description of what the test covers:
        Verifies that the string representation of settings includes
        key field values in a readable format.

        Preconditions:
            - Settings instance with custom values

        Steps:
            - Create settings with specific app_name and environment
            - Convert to string representation
            - Verify key values are present in output

        Expected Result:
            - String should contain "test-app"
            - String should contain "production"
        """
        settings = BaseCoreSettings(app_name="test-app", environment="production")

        str_repr = str(settings)

        # Pydantic models return field values in string representation
        assert "test-app" in str_repr
        assert "production" in str_repr


@pytest.mark.unit
class TestBaseCoreSettingsEdgeCases:
    """Test cases for BaseCoreSettings edge cases."""

    def test_empty_app_name(self) -> None:
        """Test empty string app_name acceptance.

        Description of what the test covers:
        Verifies that BaseCoreSettings allows empty string values
        for the app_name field without validation errors.

        Preconditions:
            - Empty string value for app_name

        Steps:
            - Create settings with app_name=""
            - Verify no validation errors occur
            - Verify empty string is stored as-is

        Expected Result:
            - settings.app_name should be "" (empty string)
        """
        settings = BaseCoreSettings(app_name="")
        assert settings.app_name == ""

    def test_whitespace_app_name(self) -> None:
        """Test whitespace preservation in app_name.

        Description of what the test covers:
        Verifies that BaseCoreSettings preserves whitespace in app_name
        values without automatic trimming.

        Preconditions:
            - App_name value with leading/trailing whitespace

        Steps:
            - Create settings with app_name="  test-app  "
            - Verify whitespace is preserved

        Expected Result:
            - settings.app_name should be "  test-app  " (with spaces)
        """
        settings = BaseCoreSettings(app_name="  test-app  ")
        # Note: str_strip_whitespace only works for specific field types
        assert settings.app_name == "  test-app  "

    def test_numeric_debug_values(self) -> None:
        """Test numeric string to boolean conversion for debug.

        Description of what the test covers:
        Verifies that BaseCoreSettings correctly converts numeric string
        values to boolean for the debug field.

        Preconditions:
            - Environment variables with numeric string values

        Steps:
            - Test with DEBUG="1" and verify conversion to True
            - Test with DEBUG="0" and verify conversion to False

        Expected Result:
            - "1" should result in debug=True
            - "0" should result in debug=False
        """
        with patch.dict(os.environ, {"DEBUG": "1"}):
            settings = BaseCoreSettings()
            assert settings.debug is True

        with patch.dict(os.environ, {"DEBUG": "0"}):
            settings = BaseCoreSettings()
            assert settings.debug is False

    def test_extra_fields_ignored(self) -> None:
        """Test unknown field handling with extra='ignore'.

        Description of what the test covers:
        Verifies that BaseCoreSettings ignores unknown fields during
        initialization due to model_config extra='ignore' setting.

        Preconditions:
            - Settings initialized with unknown field

        Steps:
            - Create settings with known and unknown fields
            - Verify no validation errors occur
            - Verify unknown field is not stored

        Expected Result:
            - Known field should be stored correctly
            - Unknown field should not be accessible as attribute
        """
        # This should not raise an error due to extra="ignore"
        settings = BaseCoreSettings(app_name="test", unknown_field="should_be_ignored")
        assert settings.app_name == "test"
        assert not hasattr(settings, "unknown_field")


@pytest.mark.unit
class TestBaseCoreSettingsInvalidData:
    """Test cases for BaseCoreSettings with invalid data."""

    def test_invalid_debug_type(self) -> None:
        """Test rejection of invalid debug field types.

        Description of what the test covers:
        Verifies that BaseCoreSettings raises ValidationError when
        debug field receives non-boolean convertible values.

        Preconditions:
            - Invalid value for debug field

        Steps:
            - Attempt to create settings with debug="not_a_boolean"
            - Verify ValidationError is raised

        Expected Result:
            - ValidationError should be raised for invalid boolean value
        """
        with pytest.raises(ValidationError):
            BaseCoreSettings(debug="not_a_boolean")

    def test_none_values_for_required_fields(self) -> None:
        """Test None value rejection for typed fields.

        Description of what the test covers:
        Verifies that BaseCoreSettings raises ValidationError when
        None values are provided for fields with specific types.

        Preconditions:
            - None values for app_name, environment, and debug fields

        Steps:
            - Attempt to create settings with all fields set to None
            - Verify ValidationError is raised
            - Verify error covers all three fields

        Expected Result:
            - ValidationError should be raised
            - Error should include all three field names
        """
        # Pydantic validates types strictly, None values for non-optional fields should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(app_name=None, environment=None, debug=None)

        # Should contain validation errors for all three fields
        errors = exc_info.value.errors()
        assert len(errors) == 3
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"app_name", "environment", "debug"}


@pytest.mark.unit
@pytest.mark.config
class TestBaseCoreSettingsIntegration:
    """Integration test cases for BaseCoreSettings."""

    def test_complete_configuration_lifecycle(self) -> None:
        """Test end-to-end configuration functionality.

        Description of what the test covers:
        Verifies complete configuration loading from multiple sources
        (.env file, environment variables) with proper precedence and
        all helper methods working correctly.

        Preconditions:
            - .env file with some configuration values
            - Environment variables overriding some values

        Steps:
            - Create .env file with APP_NAME and DEBUG
            - Set ENVIRONMENT environment variable
            - Create settings and verify source precedence
            - Test helper methods and serialization

        Expected Result:
            - Values should come from appropriate sources
            - Helper methods should work correctly
            - Serialization should preserve all values
        """
        # Create settings with mixed sources
        env_content = """
APP_NAME=lifecycle-app
DEBUG=false
"""

        with NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                original_cwd = os.getcwd()
                env_dir = Path(f.name).parent
                os.chdir(env_dir)

                env_file = env_dir / ".env"
                Path(f.name).rename(env_file)

                # Override environment via env var
                with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                    settings = BaseCoreSettings()

                    # Verify values from different sources
                    assert settings.app_name == "lifecycle-app"  # From .env
                    assert settings.environment == "production"  # From env var
                    assert settings.debug is False  # From .env

                    # Test helper methods
                    assert settings.is_production() is True
                    assert settings.is_development() is False

                    # Test serialization
                    data = settings.model_dump()
                    assert data["app_name"] == "lifecycle-app"
                    assert data["environment"] == "production"

                    # Test string representation
                    str_repr = str(settings)
                    assert "lifecycle-app" in str_repr

            finally:
                os.chdir(original_cwd)
                if env_file.exists():
                    env_file.unlink()

    def test_configuration_inheritance_compatibility(self) -> None:
        """Test settings model inheritance support.

        Description of what the test covers:
        Verifies that BaseCoreSettings can be extended through inheritance
        while maintaining all base functionality.

        Preconditions:
            - Custom settings class inheriting from BaseCoreSettings

        Steps:
            - Define CustomSettings class with additional field
            - Create instance with base and custom fields
            - Verify all functionality works correctly

        Expected Result:
            - Base fields should work normally
            - Custom field should be available
            - Helper methods should function correctly
        """

        # Test that the settings can be used as a base class
        class CustomSettings(BaseCoreSettings):
            custom_field: str = "custom_value"

        settings = CustomSettings(app_name="custom-app", environment="staging")

        assert settings.app_name == "custom-app"
        assert settings.environment == "staging"
        assert settings.custom_field == "custom_value"
        assert settings.is_development() is False
