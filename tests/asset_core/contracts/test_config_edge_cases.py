"""
Configuration edge cases and boundary tests.

Comprehensive tests for configuration edge cases, error scenarios,
and boundary conditions that might occur in production environments.
"""

import os
import tempfile
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import Field, ValidationError
from pydantic_settings import SettingsConfigDict

from asset_core.config.base import BaseCoreSettings
from asset_core.config.network import BaseNetworkConfig
from asset_core.config.storage import BaseStorageConfig


class TestConfigurationEdgeCases:
    """Test cases for configuration edge cases and boundary conditions.

    Verifies that configuration classes handle unusual inputs,
    malformed data, and edge cases gracefully.
    """

    def test_missing_required_config_fields(self) -> None:
        """Test behavior when required configuration fields are missing.

        Description of what the test covers.
        Verifies that clear error messages are provided when required
        fields are not provided in various scenarios.

        Expected Result:
        - `ValidationError` raised for missing required fields.
        - Error messages clearly indicate which fields are missing.
        - Multiple missing fields are all reported.
        """

        # Test a config class with truly required fields
        class RequiredFieldConfig(BaseCoreSettings):
            required_field: str = Field(..., description="Required field without default")

        with pytest.raises(ValidationError) as exc_info:
            RequiredFieldConfig()

        error_details = exc_info.value.errors()
        required_errors = [e for e in error_details if e["loc"] == ("required_field",)]
        assert len(required_errors) > 0
        assert required_errors[0]["type"] == "missing"

        # Test BaseStorageConfig missing database_url (now required)
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig()

        error_details = exc_info.value.errors()
        db_url_errors = [e for e in error_details if e["loc"] == ("database_url",)]
        assert len(db_url_errors) > 0
        assert db_url_errors[0]["type"] == "missing"

        # Test multiple missing required fields
        class RequiredFieldsConfig(BaseCoreSettings, BaseStorageConfig):
            api_token: str = Field(..., description="Required API token")
            service_id: str = Field(..., description="Required service ID")

        with pytest.raises(ValidationError) as exc_info:
            RequiredFieldsConfig()

        error_details = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in error_details if error["type"] == "missing"}

        # Check for fields without defaults (database_url is now required)
        expected_missing = {"database_url", "api_token", "service_id"}
        assert expected_missing.issubset(missing_fields)

    def test_invalid_type_coercion_scenarios(self) -> None:
        """Test invalid type coercion and conversion scenarios.

        Description of what the test covers.
        Verifies that type conversion failures are handled gracefully
        and provide meaningful error messages.

        Expected Result:
        - Type conversion errors provide clear messages.
        - Invalid types are rejected appropriately.
        - Edge cases in type conversion are handled.
        """
        # Test invalid integer coercion
        with pytest.raises(ValidationError) as exc_info:
            BaseNetworkConfig(ws_reconnect_interval="not_a_number")

        error_details = exc_info.value.errors()
        type_errors = [e for e in error_details if "ws_reconnect_interval" in str(e["loc"])]
        assert len(type_errors) > 0

        # Test invalid boolean coercion
        with pytest.raises(ValidationError) as exc_info:
            BaseCoreSettings(app_name="test", debug="maybe")  # Invalid boolean

        error_details = exc_info.value.errors()
        bool_errors = [e for e in error_details if "debug" in str(e["loc"])]
        assert len(bool_errors) > 0

        # Test float to int coercion edge cases (only whole numbers work in Pydantic v2)
        config = BaseStorageConfig(
            database_url="test://localhost/db",
            database_pool_size=15.0,  # Whole number float - should be converted to int
            database_timeout=30.0,  # Whole number float - should be converted to int
        )

        assert config.database_pool_size == 15  # Converted to int
        assert config.database_timeout == 30  # Converted to int

        # Test fractional float values are rejected
        with pytest.raises(ValidationError):
            BaseStorageConfig(
                database_url="test://localhost/db",
                database_pool_size=15.7,  # Fractional float should fail
            )

        # Test extreme float values
        with pytest.raises(ValidationError):
            BaseStorageConfig(
                database_url="test://localhost/db",
                database_pool_size=float("inf"),  # Should fail validation
            )

    def test_circular_dependency_config_scenarios(self) -> None:
        """Test configuration scenarios with potential circular dependencies.

        Description of what the test covers.
        Verifies that configurations don't create circular dependencies
        or infinite recursion in validation or serialization.

        Expected Result:
        - No circular dependencies in configuration loading.
        - Serialization completes without infinite recursion.
        - Validation doesn't cause stack overflow.
        """

        # Create a config that references itself (potential circular dependency)
        class SelfReferencingConfig(BaseCoreSettings):
            reference_app: str = Field(default="", description="Reference to another app")

            def __init__(self, **data: Any) -> None:
                # Set reference_app to the same as app_name (self-reference)
                if "reference_app" not in data and "app_name" in data:
                    data["reference_app"] = data["app_name"]
                super().__init__(**data)

        config = SelfReferencingConfig(app_name="self_ref_app")

        # Verify no circular dependency issues
        assert config.app_name == "self_ref_app"
        assert config.reference_app == "self_ref_app"

        # Test serialization doesn't cause infinite recursion
        serialized = config.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["app_name"] == "self_ref_app"
        assert serialized["reference_app"] == "self_ref_app"

        # Test nested serialization
        nested_data = {"config": serialized}
        assert isinstance(nested_data, dict)

    def test_extremely_large_config_values(self) -> None:
        """Test configuration with extremely large values.

        Description of what the test covers.
        Verifies that very large values are handled appropriately
        and don't cause memory or performance issues.

        Expected Result:
        - Large strings are handled correctly.
        - Large numbers are validated appropriately.
        - Memory usage remains reasonable.
        """
        # Test very long strings
        very_long_string = "x" * 10000

        config = BaseCoreSettings(app_name=very_long_string)
        assert config.app_name == very_long_string
        assert len(config.app_name) == 10000

        # Test large integer values
        large_config = BaseNetworkConfig(ws_reconnect_interval=999999, ws_max_reconnect_attempts=1000000)

        assert large_config.ws_reconnect_interval == 999999
        assert large_config.ws_max_reconnect_attempts == 1000000

        # Test very long database URL
        long_db_url = "postgresql://user:pass@" + "x" * 1000 + ".example.com/database"
        storage_config = BaseStorageConfig(database_url=long_db_url)
        assert storage_config.database_url == long_db_url

        # Test serialization with large values
        serialized = storage_config.model_dump()
        assert len(serialized["database_url"]) > 1000

    def test_special_characters_in_config_values(self) -> None:
        """Test configuration with special characters and Unicode.

        Description of what the test covers.
        Verifies that special characters, Unicode, and encoded strings
        are handled correctly in configuration values.

        Expected Result:
        - Unicode characters are preserved correctly.
        - Special characters don't break validation.
        - Encoding issues are handled gracefully.
        """
        # Test Unicode characters
        unicode_app_name = "应用程序名称_тест_アプリ"
        config = BaseCoreSettings(app_name=unicode_app_name)
        assert config.app_name == unicode_app_name

        # Test special characters in database URL
        special_db_url = "postgresql://user:p@ss!w0rd$#@localhost:5432/db_name-test"
        storage_config = BaseStorageConfig(database_url=special_db_url)
        assert storage_config.database_url == special_db_url

        # Test environment variables with special characters
        env_vars = {
            "APP_NAME": "app-with-dashes_and_underscores",
            "DATABASE_URL": "sqlite:///path/to/database-file_with.special.db",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = BaseCoreSettings()
            storage_config = BaseStorageConfig()

            assert config.app_name == "app-with-dashes_and_underscores"
            assert storage_config.database_url == "sqlite:///path/to/database-file_with.special.db"

        # Test JSON serialization with special characters
        serialized = config.model_dump()
        import json

        json_string = json.dumps(serialized)  # Should not raise exception
        assert isinstance(json_string, str)

    def test_malformed_env_file_handling(self) -> None:
        """Test handling of malformed .env files.

        Description of what the test covers.
        Verifies that malformed .env files are handled gracefully
        without crashing the application.

        Expected Result:
        - Malformed .env files don't crash configuration loading.
        - Valid entries in malformed files are still processed.
        - Clear error messages for parsing issues.
        """
        # Create a malformed .env file
        malformed_env_content = """
# Valid entries
APP_NAME=test_app
ENVIRONMENT=development

# Malformed entries
INVALID_LINE_NO_EQUALS
ANOTHER_INVALID=
=MISSING_KEY_NAME
KEY_WITH_SPACES IN_NAME=value

# Valid entry after malformed ones
DEBUG=true
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(malformed_env_content)
            env_file_path = f.name

        try:
            # Create config class that uses the malformed .env file
            class TestConfig(BaseCoreSettings):
                model_config = SettingsConfigDict(env_file=env_file_path, env_file_encoding="utf-8")

            # Should still work and load valid entries
            config = TestConfig()

            # Valid entries should be loaded
            assert config.app_name == "test_app"
            assert config.environment == "development"
            assert config.debug is True

        finally:
            # Clean up
            os.unlink(env_file_path)

    def test_environment_variable_injection_security(self) -> None:
        """Test security aspects of environment variable injection.

        Description of what the test covers.
        Verifies that environment variable loading doesn't create
        security vulnerabilities or allow code injection.

        Expected Result:
        - Environment variables are treated as data, not code.
        - No code execution from environment values.
        - Proper sanitization of dangerous characters.
        """
        # Test potentially dangerous environment variable values
        dangerous_env_vars = {
            "APP_NAME": "$(rm -rf /)",  # Shell command injection attempt
            "DATABASE_URL": "postgresql://user:password;DROP TABLE users;--@localhost/db",  # SQL injection attempt
            "DEBUG": '__import__("os").system("echo hacked")',  # Python code injection attempt
        }

        with patch.dict(os.environ, dangerous_env_vars, clear=False), pytest.raises(ValidationError):
            # Boolean parsing will fail for invalid values, so we should expect ValidationError
            config = BaseCoreSettings()

        # Test with a config that doesn't have boolean validation issues
        dangerous_env_vars_safe = {
            "APP_NAME": "$(rm -rf /)",  # Shell command injection attempt
            "DATABASE_URL": "postgresql://user:password;DROP TABLE users;--@localhost/db",  # SQL injection attempt
        }

        with patch.dict(os.environ, dangerous_env_vars_safe, clear=True):
            config = BaseCoreSettings()
            storage_config = BaseStorageConfig()

            # Values should be treated as literal strings, not executed
            assert config.app_name == "$(rm -rf /)"
            assert storage_config.database_url == "postgresql://user:password;DROP TABLE users;--@localhost/db"

        # Verify no actual code execution occurred (if this were real, the test would fail)
        # The values should be stored as literal strings
        serialized = config.model_dump()
        assert "$(rm -rf /)" in str(serialized)

    def test_configuration_encoding_edge_cases(self) -> None:
        """Test configuration handling with different text encodings.

        Description of what the test covers.
        Verifies that configurations handle various text encodings
        correctly without data corruption.

        Expected Result:
        - Different encodings are handled correctly.
        - No data corruption during encoding conversion.
        - Proper fallback for unsupported encodings.
        """
        # Test UTF-8 with BOM
        utf8_bom_content = "APP_NAME=utf8_bom_app\nENVIRONMENT=production\n"

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", suffix=".env", delete=False) as f:
            f.write(utf8_bom_content)
            env_file_path = f.name

        try:

            class UTF8Config(BaseCoreSettings):
                model_config = SettingsConfigDict(
                    env_file=env_file_path,
                    env_file_encoding="utf-8-sig",  # Use utf-8-sig to handle BOM
                )

            utf8_config = UTF8Config()
            assert utf8_config.app_name == "utf8_bom_app"
            assert utf8_config.environment == "production"

        finally:
            os.unlink(env_file_path)

        # Test Latin-1 encoding
        latin1_content = "APP_NAME=app_with_ñ_character\nENVIRONMENT=development\n"

        with tempfile.NamedTemporaryFile(mode="w", encoding="latin-1", suffix=".env", delete=False) as f:
            f.write(latin1_content)
            env_file_path = f.name

        try:

            class Latin1Config(BaseCoreSettings):
                model_config = SettingsConfigDict(env_file=env_file_path, env_file_encoding="latin-1")

            latin1_config = Latin1Config()
            assert "ñ" in latin1_config.app_name

        finally:
            os.unlink(env_file_path)

    def test_configuration_memory_usage_limits(self) -> None:
        """Test configuration behavior under memory constraints.

        Description of what the test covers.
        Verifies that configuration loading doesn't consume
        excessive memory even with large configurations.

        Expected Result:
        - Memory usage remains reasonable.
        - Large configurations don't cause memory exhaustion.
        - Proper cleanup of temporary objects.
        """
        import gc

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create many configuration instances
        configs = []
        for i in range(100):
            config = BaseCoreSettings(app_name=f"memory_test_app_{i}", environment="development")
            configs.append(config)

        # Verify configurations are created correctly
        assert len(configs) == 100
        assert all(config.app_name.startswith("memory_test_app_") for config in configs)

        # Check memory usage increase is reasonable
        gc.collect()
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects

        # Should not create an excessive number of objects (allow some tolerance)
        assert object_increase < 10000  # Reasonable threshold

        # Clean up
        del configs
        gc.collect()

    def test_configuration_thread_safety_concerns(self) -> None:
        """Test configuration behavior in multi-threaded scenarios.

        Description of what the test covers.
        Verifies that configuration loading and validation
        is thread-safe and doesn't cause race conditions.

        Expected Result:
        - No race conditions in configuration loading.
        - Thread-safe validation and serialization.
        - Consistent behavior across threads.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        errors = []

        def create_config(thread_id: int) -> dict[str, Any] | None:
            """Create configuration in a thread."""
            try:
                config = BaseCoreSettings(
                    app_name=f"thread_test_{thread_id}",
                    environment="development",
                    debug=thread_id % 2 == 0,  # Alternate boolean values
                )

                # Simulate some work
                time.sleep(0.01)

                return {
                    "thread_id": thread_id,
                    "app_name": config.app_name,
                    "environment": config.environment,
                    "debug": config.debug,
                    "serialized": config.model_dump(),
                }
            except Exception as e:
                errors.append((thread_id, str(e)))
                return None

        # Run configuration creation in multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_config, i) for i in range(50)]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify all configurations were created correctly
        assert len(results) == 50

        # Verify each configuration has correct values
        for result in results:
            thread_id = result["thread_id"]
            assert result["app_name"] == f"thread_test_{thread_id}"
            assert result["environment"] == "development"
            assert result["debug"] == (thread_id % 2 == 0)
            assert isinstance(result["serialized"], dict)

    def test_configuration_performance_with_large_inheritance_chains(self) -> None:
        """Test configuration performance with deep inheritance chains.

        Description of what the test covers.
        Verifies that deep inheritance chains don't cause
        significant performance degradation.

        Expected Result:
        - Performance remains acceptable with deep inheritance.
        - No exponential time complexity.
        - Memory usage scales linearly.
        """
        import time

        # Create a deep inheritance chain
        class Level1Config(BaseCoreSettings):
            level1_field: str = Field(default="level1", description="Level 1 field")

        class Level2Config(Level1Config):
            level2_field: str = Field(default="level2", description="Level 2 field")

        class Level3Config(Level2Config):
            level3_field: str = Field(default="level3", description="Level 3 field")

        class Level4Config(Level3Config):
            level4_field: str = Field(default="level4", description="Level 4 field")

        class Level5Config(Level4Config):
            level5_field: str = Field(default="level5", description="Level 5 field")

        # Measure configuration creation time
        start_time = time.time()

        for i in range(100):
            config = Level5Config(app_name=f"performance_test_{i}")
            assert config.app_name.startswith("performance_test_")
            assert config.level1_field == "level1"
            assert config.level5_field == "level5"

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Should complete in reasonable time (allow 5 seconds for 100 creations)
        assert elapsed_time < 5.0, f"Configuration creation too slow: {elapsed_time:.2f}s"

        # Test serialization performance
        config = Level5Config(app_name="serialization_performance_test")

        start_time = time.time()
        for _ in range(1000):
            serialized = config.model_dump()
            assert isinstance(serialized, dict)
            assert len(serialized) >= 5  # Should have at least 5 fields from inheritance

        end_time = time.time()
        serialization_time = end_time - start_time

        # Serialization should be fast
        assert serialization_time < 2.0, f"Serialization too slow: {serialization_time:.2f}s"
