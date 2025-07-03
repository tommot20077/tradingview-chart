import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

from asset_core.config.base import BaseCoreSettings


@pytest.mark.integration
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
