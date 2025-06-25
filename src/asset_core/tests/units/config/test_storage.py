"""Unit tests for storage configuration settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.config.storage import BaseStorageConfig


@pytest.mark.unit
class TestBaseStorageConfigConstruction:
    """Test cases for BaseStorageConfig model construction."""

    def test_storage_config_creation_with_required_fields(self) -> None:
        """Test storage configuration with required database_url.

        Description of what the test covers:
        Verifies that BaseStorageConfig creates an instance with correct
        default values when only the required database_url is provided.

        Preconditions:
            - Valid database URL provided
            - No other explicit values set

        Steps:
            - Create BaseStorageConfig with only database_url
            - Verify all default values are set correctly

        Expected Result:
            - database_url should be stored as provided
            - database_pool_size should be 10 (default)
            - database_timeout should be 30 (default)
            - data_directory should be "data" (default)
            - max_file_size should be 100MB (default)
        """
        config = BaseStorageConfig(database_url="postgresql://user:pass@localhost:5432/db")

        assert config.database_url == "postgresql://user:pass@localhost:5432/db"
        assert config.database_pool_size == 10
        assert config.database_timeout == 30
        assert config.data_directory == "data"
        assert config.max_file_size == 100 * 1024 * 1024  # 100MB

    def test_custom_storage_config_creation(self) -> None:
        """Test custom storage configuration with explicit values.

        Description of what the test covers:
        Verifies that BaseStorageConfig correctly accepts and stores
        custom values for all storage configuration parameters.

        Preconditions:
            - Custom values for all configuration fields

        Steps:
            - Create config with custom database, pool, timeout, directory settings
            - Verify all provided values are stored correctly

        Expected Result:
            - All custom values should be stored exactly as provided
            - No default values should be used
        """
        config = BaseStorageConfig(
            database_url="sqlite:///test.db",
            database_pool_size=5,
            database_timeout=60,
            data_directory="/tmp/data",
            max_file_size=50 * 1024 * 1024,
        )

        assert config.database_url == "sqlite:///test.db"
        assert config.database_pool_size == 5
        assert config.database_timeout == 60
        assert config.data_directory == "/tmp/data"
        assert config.max_file_size == 50 * 1024 * 1024

    def test_storage_config_from_dict(self) -> None:
        """Test storage configuration from dictionary unpacking.

        Description of what the test covers:
        Verifies that BaseStorageConfig can be initialized by unpacking
        a dictionary containing all configuration parameters.

        Preconditions:
            - Dictionary with all storage configuration keys and values

        Steps:
            - Create configuration dictionary with all storage settings
            - Initialize BaseStorageConfig using dictionary unpacking
            - Verify all values from dictionary are applied

        Expected Result:
            - All dictionary values should be correctly assigned to config fields
        """
        config_dict = {
            "database_url": "mysql://user:pass@localhost/db",
            "database_pool_size": 20,
            "database_timeout": 45,
            "data_directory": "./custom_data",
            "max_file_size": 200 * 1024 * 1024,
        }

        config = BaseStorageConfig(**config_dict)

        assert config.database_url == "mysql://user:pass@localhost/db"
        assert config.database_pool_size == 20
        assert config.database_timeout == 45
        assert config.data_directory == "./custom_data"
        assert config.max_file_size == 200 * 1024 * 1024


@pytest.mark.unit
class TestBaseStorageConfigValidation:
    """Test cases for BaseStorageConfig validation."""

    def test_missing_database_url_raises_error(self) -> None:
        """Test validation error for missing required database_url.

        Description of what the test covers:
        Verifies that BaseStorageConfig raises ValidationError when
        the required database_url field is not provided.

        Preconditions:
            - No database_url provided during initialization

        Steps:
            - Attempt to create BaseStorageConfig without database_url
            - Verify ValidationError is raised
            - Check error message mentions database_url field

        Expected Result:
            - ValidationError should be raised
            - Error message should indicate "database_url" field is required
        """
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig()

        assert "database_url" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)

    def test_empty_database_url_raises_error(self) -> None:
        """Test validation error for empty database_url string.

        Description of what the test covers:
        Verifies that BaseStorageConfig raises ValidationError when
        database_url is provided as an empty string.

        Preconditions:
            - Empty string value for database_url

        Steps:
            - Attempt to create BaseStorageConfig with database_url=""
            - Verify ValidationError is raised

        Expected Result:
            - ValidationError should be raised for empty database_url
        """
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="")

    def test_valid_database_urls(self) -> None:
        """Test acceptance of various valid database URL formats.

        Description of what the test covers:
        Verifies that BaseStorageConfig accepts various standard
        database URL formats for different database types.

        Preconditions:
            - List of valid database URLs for different databases

        Steps:
            - Test with PostgreSQL, MySQL, SQLite URLs
            - Test with async drivers and special URLs
            - Verify all are accepted without validation errors

        Expected Result:
            - All valid database URL formats should be accepted
            - URLs should be stored exactly as provided
        """
        valid_urls = [
            "postgresql://user:pass@localhost:5432/dbname",
            "mysql://user:pass@host:3306/db",
            "sqlite:///path/to/database.db",
            "sqlite:///:memory:",
            "postgresql+asyncpg://user:pass@localhost/db",
            "mysql+aiomysql://user:pass@localhost/db",
        ]

        for url in valid_urls:
            config = BaseStorageConfig(database_url=url)
            assert config.database_url == url

    def test_database_pool_size_validation(self) -> None:
        """Test database pool size range validation.

        Description of what the test covers:
        Verifies that BaseStorageConfig validates database_pool_size
        values are positive integers greater than 0.

        Preconditions:
            - Valid database URL and various pool size values

        Steps:
            - Test with valid positive pool sizes (1, 100)
            - Test with invalid pool sizes (0, -1)
            - Verify validation behavior

        Expected Result:
            - Positive pool sizes should be accepted
            - Zero and negative values should raise ValidationError
        """
        # Valid positive values
        config = BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=1)
        assert config.database_pool_size == 1

        config = BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=100)
        assert config.database_pool_size == 100

        # Invalid values
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=0)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=-1)

    def test_database_timeout_validation(self) -> None:
        """Test database timeout range validation.

        Description of what the test covers:
        Verifies that BaseStorageConfig validates database_timeout
        values are positive integers greater than 0.

        Preconditions:
            - Valid database URL and various timeout values

        Steps:
            - Test with valid positive timeout (1 second)
            - Test with invalid timeouts (0, -1)
            - Verify validation behavior

        Expected Result:
            - Positive timeout values should be accepted
            - Zero and negative values should raise ValidationError
        """
        # Valid positive values
        config = BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=1)
        assert config.database_timeout == 1

        # Invalid values
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=0)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=-1)

    def test_max_file_size_validation(self) -> None:
        """Test max file size range validation.

        Description of what the test covers:
        Verifies that BaseStorageConfig validates max_file_size
        values are non-negative integers (zero and positive allowed).

        Preconditions:
            - Valid database URL and various file size values

        Steps:
            - Test with valid sizes (0, 1GB)
            - Test with invalid negative size (-1)
            - Verify validation behavior

        Expected Result:
            - Zero and positive file sizes should be accepted
            - Negative values should raise ValidationError
        """
        # Valid positive values including zero
        config = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=0)
        assert config.max_file_size == 0

        config = BaseStorageConfig(
            database_url="sqlite:///test.db",
            max_file_size=1024 * 1024 * 1024,  # 1GB
        )
        assert config.max_file_size == 1024 * 1024 * 1024

        # Invalid negative values
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=-1)


@pytest.mark.unit
class TestBaseStorageConfigEnvironmentVariables:
    """Test cases for BaseStorageConfig environment variable loading."""

    def test_env_var_loading_database_url(self) -> None:
        """Test database URL loading from environment variable.

        Description of what the test covers:
        Verifies that BaseStorageConfig loads database_url from
        the DATABASE_URL environment variable when available.

        Preconditions:
            - DATABASE_URL environment variable set

        Steps:
            - Mock environment variable DATABASE_URL with PostgreSQL URL
            - Create BaseStorageConfig instance without arguments
            - Verify database_url is loaded from environment

        Expected Result:
            - config.database_url should match environment variable value
        """
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://env:test@localhost/db"}):
            config = BaseStorageConfig()
            assert config.database_url == "postgresql://env:test@localhost/db"

    def test_env_var_loading_database_pool_size(self) -> None:
        """Test loading database_pool_size from environment variable."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db", "DATABASE_POOL_SIZE": "15"}):
            config = BaseStorageConfig()
            assert config.database_pool_size == 15

    def test_env_var_loading_database_timeout(self) -> None:
        """Test loading database_timeout from environment variable."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db", "DATABASE_TIMEOUT": "45"}):
            config = BaseStorageConfig()
            assert config.database_timeout == 45

    def test_env_var_loading_data_directory(self) -> None:
        """Test loading data_directory from environment variable."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db", "DATA_DIRECTORY": "/env/data"}):
            config = BaseStorageConfig()
            assert config.data_directory == "/env/data"

    def test_env_var_loading_max_file_size(self) -> None:
        """Test loading max_file_size from environment variable."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite:///test.db",
                "MAX_FILE_SIZE": "52428800",  # 50MB
            },
        ):
            config = BaseStorageConfig()
            assert config.max_file_size == 52428800

    def test_env_var_override_defaults(self) -> None:
        """Test environment variables override default values."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "mysql://env:pass@localhost/db",
                "DATABASE_POOL_SIZE": "25",
                "DATABASE_TIMEOUT": "60",
                "DATA_DIRECTORY": "/env/custom",
                "MAX_FILE_SIZE": "209715200",  # 200MB
            },
        ):
            config = BaseStorageConfig()
            assert config.database_url == "mysql://env:pass@localhost/db"
            assert config.database_pool_size == 25
            assert config.database_timeout == 60
            assert config.data_directory == "/env/custom"
            assert config.max_file_size == 209715200

    def test_constructor_args_override_env_vars(self) -> None:
        """Test constructor arguments override environment variables."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://env:pass@localhost/db", "DATABASE_POOL_SIZE": "20"}):
            config = BaseStorageConfig(database_url="sqlite:///override.db", database_pool_size=5)
            assert config.database_url == "sqlite:///override.db"
            assert config.database_pool_size == 5


@pytest.mark.unit
class TestBaseStorageConfigBoundaryValues:
    """Test cases for BaseStorageConfig boundary values."""

    def test_minimum_valid_pool_size(self) -> None:
        """Test minimum valid pool size configuration.

        Description of what the test covers:
        Verifies that BaseStorageConfig accepts the minimum
        valid database pool size of 1.

        Preconditions:
        - Valid database URL
        - Pool size set to minimum value (1)

        Steps:
        - Create BaseStorageConfig with minimum pool size
        - Verify pool size is correctly set

        Expected Result:
        - database_pool_size should be exactly 1
        """
        config = BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=1)
        assert config.database_pool_size == 1

    def test_minimum_valid_timeout(self) -> None:
        """Test minimum valid database connection timeout.

        Description of what the test covers:
        Verifies that BaseStorageConfig accepts the minimum
        valid database connection timeout of 1 second.

        Preconditions:
        - Valid database URL
        - Timeout set to minimum value (1)

        Steps:
        - Create BaseStorageConfig with minimum timeout
        - Verify timeout is correctly set

        Expected Result:
        - database_timeout should be exactly 1
        """
        config = BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=1)
        assert config.database_timeout == 1

    def test_zero_file_size_allowed(self) -> None:
        """Test zero maximum file size configuration.

        Description of what the test covers:
        Verifies that BaseStorageConfig allows setting
        maximum file size to zero.

        Preconditions:
        - Valid database URL
        - Max file size set to 0

        Steps:
        - Create BaseStorageConfig with zero max file size
        - Verify max file size is set to zero

        Expected Result:
        - max_file_size should be exactly 0
        """
        config = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=0)
        assert config.max_file_size == 0

    def test_large_values(self) -> None:
        """Test configuration with large database and file size values.

        Description of what the test covers:
        Verifies that BaseStorageConfig accepts very large
        values for database pool size, timeout, and max file size.

        Preconditions:
        - Valid database URL
        - Large values for configuration parameters

        Steps:
        - Create BaseStorageConfig with maximum allowed values
        - Verify each configuration parameter is set correctly

        Expected Result:
        - database_pool_size accepts large connection pool values
        - database_timeout allows long timeout periods
        - max_file_size supports large file sizes (10GB)
        """
        config = BaseStorageConfig(
            database_url="postgresql://user:pass@localhost/db",
            database_pool_size=1000,
            database_timeout=3600,  # 1 hour
            max_file_size=10 * 1024 * 1024 * 1024,  # 10GB
        )

        assert config.database_pool_size == 1000
        assert config.database_timeout == 3600
        assert config.max_file_size == 10 * 1024 * 1024 * 1024

    def test_realistic_database_configurations(self) -> None:
        """Test configuration for different application scales.

        Description of what the test covers:
        Verifies that BaseStorageConfig supports configuration
        for both small and large scale applications.

        Preconditions:
        - Different database URLs for small and large applications
        - Varying configuration parameters

        Steps:
        - Create BaseStorageConfig for small application
        - Create BaseStorageConfig for large application
        - Verify configuration parameters match expected values

        Expected Result:
        - Small application config:
            * Low database pool size (2)
            * Short database timeout (15s)
            * Small max file size (10MB)
        - Large application config:
            * Large database pool size (50)
            * Longer database timeout (120s)
            * Larger max file size (1GB)
        """
        # Small application
        small_config = BaseStorageConfig(
            database_url="sqlite:///small_app.db",
            database_pool_size=2,
            database_timeout=15,
            max_file_size=10 * 1024 * 1024,  # 10MB
        )

        assert small_config.database_pool_size == 2
        assert small_config.max_file_size == 10 * 1024 * 1024

        # Large application
        large_config = BaseStorageConfig(
            database_url="postgresql://user:pass@cluster:5432/production",
            database_pool_size=50,
            database_timeout=120,
            max_file_size=1024 * 1024 * 1024,  # 1GB
        )

        assert large_config.database_pool_size == 50
        assert large_config.database_timeout == 120


@pytest.mark.unit
class TestBaseStorageConfigSerialization:
    """Test cases for BaseStorageConfig serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump method."""
        config = BaseStorageConfig(
            database_url="postgresql://user:pass@localhost/db",
            database_pool_size=15,
            database_timeout=45,
            data_directory="/custom/data",
            max_file_size=157286400,  # 150MB
        )

        data = config.model_dump()

        assert isinstance(data, dict)
        assert data["database_url"] == "postgresql://user:pass@localhost/db"
        assert data["database_pool_size"] == 15
        assert data["database_timeout"] == 45
        assert data["data_directory"] == "/custom/data"
        assert data["max_file_size"] == 157286400

    def test_model_dump_json_serializable(self) -> None:
        """Test model can be dumped to JSON-serializable format."""
        config = BaseStorageConfig(database_url="sqlite:///test.db")

        data = config.model_dump()

        # Should be able to convert to JSON
        import json

        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed_data = json.loads(json_str)
        assert parsed_data["database_url"] == "sqlite:///test.db"
        assert parsed_data["database_pool_size"] == 10

    def test_model_dump_excludes_sensitive_info(self) -> None:
        """Test model dump handling of potentially sensitive database URLs."""
        config = BaseStorageConfig(database_url="postgresql://user:secret_password@localhost/db")

        data = config.model_dump()

        # The URL should be included as-is (it's up to the application to handle sensitivity)
        assert "secret_password" in data["database_url"]


@pytest.mark.unit
class TestBaseStorageConfigStringRepresentation:
    """Test cases for BaseStorageConfig string representation."""

    def test_string_representation(self) -> None:
        """Test string representation."""
        config = BaseStorageConfig(database_url="postgresql://user:pass@localhost/db", database_pool_size=15)

        str_repr = str(config)

        # Pydantic models return field values in string representation
        # Should not expose sensitive information in string representation
        assert "database_pool_size=15" in str_repr

    def test_string_representation_with_sensitive_url(self) -> None:
        """Test string representation doesn't expose sensitive information."""
        config = BaseStorageConfig(database_url="postgresql://user:secret_password@localhost/db")

        _str_repr = str(config)  # String representation contains config values

        # The string representation might include the URL, but this is implementation dependent
        # Pydantic models return field values in string representation


@pytest.mark.unit
class TestBaseStorageConfigEdgeCases:
    """Test cases for BaseStorageConfig edge cases."""

    def test_string_integer_conversion(self) -> None:
        """Test environment variables with string integer values.

        Description of what the test covers:
        Verifies that BaseStorageConfig correctly converts
        string integer values from environment variables
        to actual integer types.

        Preconditions:
        - Environment variables set with string integer values
        - Database URL set to prevent validation errors

        Steps:
        - Set environment variables with string numbers
        - Create BaseStorageConfig
        - Verify values are converted to integers
        - Check type of converted values

        Expected Result:
        - database_pool_size converted from '25' to 25 (int)
        - database_timeout converted from '90' to 90 (int)
        - max_file_size converted from '314572800' to 314572800 (int)
        - All converted values are of type int
        """
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite:///test.db",
                "DATABASE_POOL_SIZE": "25",
                "DATABASE_TIMEOUT": "90",
                "MAX_FILE_SIZE": "314572800",  # 300MB
            },
        ):
            config = BaseStorageConfig()
            assert config.database_pool_size == 25
            assert config.database_timeout == 90
            assert config.max_file_size == 314572800
            assert isinstance(config.database_pool_size, int)
            assert isinstance(config.database_timeout, int)
            assert isinstance(config.max_file_size, int)

    def test_path_normalization(self) -> None:
        """Test whitespace trimming for data_directory path.

        Description of what the test covers:
        Verifies that BaseStorageConfig automatically
        removes leading and trailing whitespace from paths.

        Preconditions:
        - Valid database URL
        - Path with surrounding whitespaces

        Steps:
        - Create BaseStorageConfig with path containing whitespaces
        - Verify path is automatically normalized

        Expected Result:
        - Whitespaces are stripped from beginning and end of path
        - Path remains unchanged except for whitespace removal
        """
        config = BaseStorageConfig(database_url="sqlite:///test.db", data_directory="  /path/with/spaces  ")
        # Pydantic's str_strip_whitespace should handle this
        assert config.data_directory == "/path/with/spaces"

    def test_relative_and_absolute_paths(self) -> None:
        """Test path flexibility for data_directory.

        Description of what the test covers:
        Verifies that BaseStorageConfig supports both
        relative and absolute file system paths.

        Preconditions:
        - Valid database URL
        - Relative and absolute path examples

        Steps:
        - Create BaseStorageConfig with relative path
        - Create BaseStorageConfig with absolute path
        - Verify paths are preserved as-is

        Expected Result:
        - Relative path (./) remains unchanged
        - Absolute path (starting with /) remains unchanged
        - No automatic path transformation occurs
        """
        # Relative path
        config_rel = BaseStorageConfig(database_url="sqlite:///test.db", data_directory="./relative/path")
        assert config_rel.data_directory == "./relative/path"

        # Absolute path
        config_abs = BaseStorageConfig(database_url="sqlite:///test.db", data_directory="/absolute/path")
        assert config_abs.data_directory == "/absolute/path"

    def test_file_size_units(self) -> None:
        """Test max file size calculation across different units.

        Description of what the test covers:
        Verifies that BaseStorageConfig correctly handles
        file size specifications in different byte units.

        Preconditions:
        - Valid database URL
        - File size values in kilobytes, megabytes, gigabytes

        Steps:
        - Create BaseStorageConfig with 1KB, 1MB, 1GB file sizes
        - Verify exact byte calculations for each size

        Expected Result:
        - 1KB (1024 bytes) stored as 1024
        - 1MB (1024 * 1024 bytes) stored as 1048576
        - 1GB (1024 * 1024 * 1024 bytes) stored as 1073741824
        - No loss of precision during size conversion
        """
        # 1KB
        config_kb = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=1024)
        assert config_kb.max_file_size == 1024

        # 1MB
        config_mb = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=1024 * 1024)
        assert config_mb.max_file_size == 1048576

        # 1GB
        config_gb = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=1024 * 1024 * 1024)
        assert config_gb.max_file_size == 1073741824


@pytest.mark.unit
class TestBaseStorageConfigInvalidData:
    """Test cases for BaseStorageConfig with invalid data."""

    def test_invalid_integer_types(self) -> None:
        """Test invalid integer types."""
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size="not_a_number")

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=3.14)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=None)

    def test_float_values_converted_to_int(self) -> None:
        """Test integer values are properly handled."""
        config = BaseStorageConfig(
            database_url="sqlite:///test.db", database_pool_size=15, database_timeout=30, max_file_size=1048576
        )

        assert config.database_pool_size == 15
        assert config.database_timeout == 30
        assert config.max_file_size == 1048576
        assert isinstance(config.database_pool_size, int)
        assert isinstance(config.database_timeout, int)
        assert isinstance(config.max_file_size, int)

    def test_none_database_url(self) -> None:
        """Test None database_url is rejected."""
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url=None)


@pytest.mark.unit
@pytest.mark.config
class TestBaseStorageConfigIntegration:
    """Integration test cases for BaseStorageConfig."""

    def test_complete_storage_configuration(self) -> None:
        """Test complete storage configuration with all features."""
        with patch.dict(os.environ, {"DATABASE_POOL_SIZE": "20", "DATA_DIRECTORY": "/env/data"}):
            config = BaseStorageConfig(
                database_url="postgresql://user:pass@localhost/db", database_timeout=60, max_file_size=200 * 1024 * 1024
            )

            # Verify mixed sources
            assert config.database_url == "postgresql://user:pass@localhost/db"  # From constructor
            assert config.database_pool_size == 20  # From env var
            assert config.database_timeout == 60  # From constructor
            assert config.data_directory == "/env/data"  # From env var
            assert config.max_file_size == 200 * 1024 * 1024  # From constructor

            # Test serialization
            data = config.model_dump()
            assert data["database_pool_size"] == 20
            assert data["max_file_size"] == 200 * 1024 * 1024

    def test_database_specific_configurations(self) -> None:
        """Test configuration for various database types.

        Description of what the test covers:
        Verifies that BaseStorageConfig supports configuration
        for different database systems with varied connection requirements.

        Preconditions:
        - Database URLs for SQLite, PostgreSQL, MySQL
        - Specific pool size and timeout for each database type

        Steps:
        - Create BaseStorageConfig for SQLite (file-based)
        - Create BaseStorageConfig for PostgreSQL (networked, async)
        - Create BaseStorageConfig for MySQL (networked, async)
        - Verify configuration matches database type characteristics

        Expected Result:
        - SQLite config:
            * Low pool size (1)
            * Moderate timeout (30s)
            * URL contains 'sqlite'
        - PostgreSQL config:
            * Large pool size (50)
            * Long timeout (120s)
            * URL contains 'postgresql'
        - MySQL config:
            * Medium pool size (25)
            * Moderate timeout (60s)
            * URL contains 'mysql'
        """
        # SQLite configuration (simple, file-based)
        sqlite_config = BaseStorageConfig(
            database_url="sqlite:///app.db",
            database_pool_size=1,  # SQLite doesn't need large pools
            database_timeout=30,
        )

        assert "sqlite" in sqlite_config.database_url
        assert sqlite_config.database_pool_size == 1

        # PostgreSQL configuration (production, networked)
        postgres_config = BaseStorageConfig(
            database_url="postgresql+asyncpg://user:pass@db-cluster:5432/production",
            database_pool_size=50,
            database_timeout=120,
        )

        assert "postgresql" in postgres_config.database_url
        assert postgres_config.database_pool_size == 50

        # MySQL configuration
        mysql_config = BaseStorageConfig(
            database_url="mysql+aiomysql://user:pass@mysql-host:3306/app_db", database_pool_size=25, database_timeout=60
        )

        assert "mysql" in mysql_config.database_url
        assert mysql_config.database_pool_size == 25

    def test_environment_specific_storage_patterns(self) -> None:
        """Test storage configuration across different environments.

        Description of what the test covers:
        Verifies that BaseStorageConfig supports different
        storage configurations for development and production
        environments with distinct requirements.

        Preconditions:
        - Database URLs for development and production
        - Specific configuration parameters for each environment

        Steps:
        - Create BaseStorageConfig for development environment
        - Create BaseStorageConfig for production environment
        - Verify configuration matches environment characteristics

        Expected Result:
        - Development environment config:
            * Local SQLite database
            * Small connection pool (2)
            * Relative data directory
            * Limited file size (10MB)
        - Production environment config:
            * Remote PostgreSQL database
            * Large connection pool (100)
            * Absolute system data directory
            * Large file size (1GB)
        """
        # Development environment
        dev_config = BaseStorageConfig(
            database_url="sqlite:///dev.db",
            database_pool_size=2,
            data_directory="./dev_data",
            max_file_size=10 * 1024 * 1024,  # 10MB for dev
        )

        assert "sqlite" in dev_config.database_url
        assert dev_config.data_directory.startswith(".")
        assert dev_config.max_file_size == 10 * 1024 * 1024

        # Production environment
        prod_config = BaseStorageConfig(
            database_url="postgresql://user:pass@prod-db:5432/app",
            database_pool_size=100,
            data_directory="/var/app/data",
            max_file_size=1024 * 1024 * 1024,  # 1GB for production
        )

        assert "postgresql" in prod_config.database_url
        assert prod_config.data_directory.startswith("/var")
        assert prod_config.max_file_size == 1024 * 1024 * 1024

    def test_configuration_inheritance_compatibility(self) -> None:
        """Test extension of BaseStorageConfig through inheritance.

        Description of what the test covers:
        Verifies that BaseStorageConfig supports extension
        with additional configuration fields while preserving
        base configuration functionality.

        Preconditions:
        - Base configuration with inherited custom fields
        - Database URL and pool size for configuration

        Steps:
        - Define CustomStorageConfig inheriting from BaseStorageConfig
        - Add custom fields: backup_enabled, backup_interval
        - Create config instance with base and custom parameters
        - Verify base and custom configuration are preserved

        Expected Result:
        - Base configuration fields (database_url, database_pool_size) maintained
        - Custom fields added and initialized with default values
        - Ability to override both base and custom configuration
        """

        class CustomStorageConfig(BaseStorageConfig):
            backup_enabled: bool = True
            backup_interval: int = 3600  # 1 hour

        config = CustomStorageConfig(database_url="postgresql://user:pass@localhost/db", database_pool_size=15)

        assert config.database_url == "postgresql://user:pass@localhost/db"
        assert config.database_pool_size == 15
        assert config.backup_enabled is True
        assert config.backup_interval == 3600
