"""ABOUTME: Unit tests for storage configuration module
ABOUTME: Testing BaseStorageConfig validation, database settings, and file storage configuration
"""

import pytest
from pydantic import ValidationError

from asset_core.config.storage import BaseStorageConfig


@pytest.mark.unit
class TestBaseStorageConfig:
    """Unit tests for BaseStorageConfig class."""

    def test_default_values_with_required_fields(self) -> None:
        """Test that default values are correctly set when required fields are provided."""
        config = BaseStorageConfig(database_url="sqlite:///test.db")

        assert config.database_url == "sqlite:///test.db"
        assert config.database_pool_size == 10
        assert config.database_timeout == 30
        assert config.data_directory == "data"
        assert config.max_file_size == 100 * 1024 * 1024  # 100 MB

    def test_explicit_initialization(self) -> None:
        """Test explicit initialization with custom values."""
        config = BaseStorageConfig(
            database_url="postgresql://user:password@localhost:5432/db",
            database_pool_size=20,
            database_timeout=60,
            data_directory="/custom/data",
            max_file_size=200 * 1024 * 1024,
        )

        assert config.database_url == "postgresql://user:password@localhost:5432/db"
        assert config.database_pool_size == 20
        assert config.database_timeout == 60
        assert config.data_directory == "/custom/data"
        assert config.max_file_size == 200 * 1024 * 1024

    def test_database_url_required(self) -> None:
        """Test that database_url is required."""
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig()

        errors = exc_info.value.errors()
        db_url_error = next(error for error in errors if error["loc"] == ("database_url",))
        assert "missing" in db_url_error["msg"].lower() or "required" in db_url_error["msg"].lower()

    def test_database_url_validation(self) -> None:
        """Test database_url validation constraints."""
        # Valid database URLs
        valid_urls = [
            "sqlite:///test.db",
            "sqlite:////absolute/path/test.db",
            "postgresql://user:password@localhost:5432/db",
            "mysql://user:password@localhost:3306/db",
            "redis://localhost:6379/0",
            "mongodb://localhost:27017/db",
            "file:///path/to/db",
            "memory://",
        ]

        for url in valid_urls:
            config = BaseStorageConfig(database_url=url)
            assert config.database_url == url

        # Invalid database URLs (empty string)
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig(database_url="")

        errors = exc_info.value.errors()
        db_url_error = next(error for error in errors if error["loc"] == ("database_url",))
        assert "at least 1 character" in db_url_error["msg"] or "too short" in db_url_error["msg"]

    def test_database_pool_size_validation(self) -> None:
        """Test database_pool_size validation constraints."""
        # Valid pool sizes
        valid_sizes = [1, 5, 10, 20, 100]

        for size in valid_sizes:
            config = BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=size)
            assert config.database_pool_size == size

        # Invalid pool sizes (zero and negative)
        invalid_sizes = [0, -1, -10]

        for size in invalid_sizes:
            with pytest.raises(ValidationError) as exc_info:
                BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=size)

            errors = exc_info.value.errors()
            pool_error = next(error for error in errors if error["loc"] == ("database_pool_size",))
            assert "greater than 0" in pool_error["msg"]

    def test_database_timeout_validation(self) -> None:
        """Test database_timeout validation constraints."""
        # Valid timeout values
        valid_timeouts = [1, 10, 30, 60, 300]

        for timeout in valid_timeouts:
            config = BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=timeout)
            assert config.database_timeout == timeout

        # Invalid timeout values (zero and negative)
        invalid_timeouts = [0, -1, -30]

        for timeout in invalid_timeouts:
            with pytest.raises(ValidationError) as exc_info:
                BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=timeout)

            errors = exc_info.value.errors()
            timeout_error = next(error for error in errors if error["loc"] == ("database_timeout",))
            assert "greater than 0" in timeout_error["msg"]

    def test_max_file_size_validation(self) -> None:
        """Test max_file_size validation constraints."""
        # Valid file sizes (including zero)
        valid_sizes = [0, 1024, 1024 * 1024, 100 * 1024 * 1024, 1024 * 1024 * 1024]

        for size in valid_sizes:
            config = BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=size)
            assert config.max_file_size == size

        # Invalid file sizes (negative)
        invalid_sizes = [-1, -1024, -1024 * 1024]

        for size in invalid_sizes:
            with pytest.raises(ValidationError) as exc_info:
                BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=size)

            errors = exc_info.value.errors()
            size_error = next(error for error in errors if error["loc"] == ("max_file_size",))
            assert "greater than or equal to 0" in size_error["msg"]

    def test_float_to_int_conversion(self) -> None:
        """Test that float values are converted to integers for numeric fields."""
        config = BaseStorageConfig(
            database_url="sqlite:///test.db", database_pool_size=10.0, database_timeout=30.0, max_file_size=100.0
        )

        assert isinstance(config.database_pool_size, int)
        assert isinstance(config.database_timeout, int)
        assert isinstance(config.max_file_size, int)
        assert config.database_pool_size == 10
        assert config.database_timeout == 30
        assert config.max_file_size == 100

    def test_non_integer_float_values_rejected(self) -> None:
        """Test that non-integer float values are rejected."""
        # Non-integer floats should raise ValidationError
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=10.5)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_timeout=30.7)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=100.3)

    def test_type_validation(self) -> None:
        """Test type validation for all fields."""
        # Valid types should work
        config = BaseStorageConfig(
            database_url="sqlite:///test.db",
            database_pool_size=10,
            database_timeout=30,
            data_directory="/data",
            max_file_size=1024 * 1024,
        )

        assert isinstance(config.database_url, str)
        assert isinstance(config.database_pool_size, int)
        assert isinstance(config.database_timeout, int)
        assert isinstance(config.data_directory, str)
        assert isinstance(config.max_file_size, int)

        # Invalid types should raise ValidationError
        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url=123)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size="ten")

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", database_timeout="thirty")

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", data_directory=123)

        with pytest.raises(ValidationError):
            BaseStorageConfig(database_url="sqlite:///test.db", max_file_size="large")

    def test_model_config_settings(self) -> None:
        """Test that model configuration is properly set."""
        config = BaseStorageConfig(database_url="sqlite:///test.db")

        # Check that model_config is properly configured
        assert hasattr(config, "model_config")
        assert config.model_config.get("str_strip_whitespace") is True
        assert config.model_config.get("extra") == "ignore"

    def test_field_descriptions(self) -> None:
        """Test that all fields have proper descriptions."""
        for field_name, field_info in BaseStorageConfig.model_fields.items():
            assert field_info.description is not None
            assert len(field_info.description) > 0, f"Field {field_name} missing description"

    def test_none_values_rejected(self) -> None:
        """Test that None values are properly rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig(
                database_url=None,
                database_pool_size=None,
                database_timeout=None,
                data_directory=None,
                max_file_size=None,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 5
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {
            "database_url",
            "database_pool_size",
            "database_timeout",
            "data_directory",
            "max_file_size",
        }

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored due to model configuration."""
        # Should not raise error due to extra="ignore"
        config = BaseStorageConfig(
            database_url="sqlite:///test.db", unknown_field="should-be-ignored", another_unknown=123
        )

        assert config.database_url == "sqlite:///test.db"
        assert not hasattr(config, "unknown_field")
        assert not hasattr(config, "another_unknown")

    def test_serialization_compatibility(self) -> None:
        """Test that config can be serialized and deserialized."""
        original_config = BaseStorageConfig(
            database_url="postgresql://user:password@localhost:5432/db",
            database_pool_size=20,
            database_timeout=60,
            data_directory="/custom/data",
            max_file_size=200 * 1024 * 1024,
        )

        # Test model_dump
        data = original_config.model_dump()
        assert isinstance(data, dict)
        assert data["database_url"] == "postgresql://user:password@localhost:5432/db"
        assert data["database_pool_size"] == 20
        assert data["database_timeout"] == 60
        assert data["data_directory"] == "/custom/data"
        assert data["max_file_size"] == 200 * 1024 * 1024

        # Test that we can create a new instance from the data
        new_config = BaseStorageConfig(**data)
        assert new_config.database_url == original_config.database_url
        assert new_config.database_pool_size == original_config.database_pool_size
        assert new_config.database_timeout == original_config.database_timeout
        assert new_config.data_directory == original_config.data_directory
        assert new_config.max_file_size == original_config.max_file_size

    def test_serialization_excludes_sensitive_fields(self) -> None:
        """Test that sensitive fields can be excluded from serialization."""
        config = BaseStorageConfig(database_url="postgresql://user:password@localhost:5432/db")

        # Test that we can exclude sensitive fields like database_url
        data = config.model_dump(exclude={"database_url"})

        assert isinstance(data, dict)
        # database_url should be excluded
        assert "database_url" not in data
        # Other fields should be present
        assert "database_pool_size" in data
        assert "database_timeout" in data
        assert "data_directory" in data
        assert "max_file_size" in data

    def test_field_descriptions_content(self) -> None:
        """Test that field descriptions contain meaningful content."""
        descriptions = {
            field_name: field_info.description for field_name, field_info in BaseStorageConfig.model_fields.items()
        }

        # Check that descriptions mention key concepts
        assert descriptions["database_url"] is not None, "database_url field must have a description"
        assert "database" in descriptions["database_url"].lower()
        assert "connection" in descriptions["database_url"].lower()

        assert descriptions["database_pool_size"] is not None, "database_pool_size field must have a description"
        assert "pool" in descriptions["database_pool_size"].lower()

        assert descriptions["database_timeout"] is not None, "database_timeout field must have a description"
        assert "timeout" in descriptions["database_timeout"].lower()

        assert descriptions["data_directory"] is not None, "data_directory field must have a description"
        assert "directory" in descriptions["data_directory"].lower() or "path" in descriptions["data_directory"].lower()

        assert descriptions["max_file_size"] is not None, "max_file_size field must have a description"
        assert "size" in descriptions["max_file_size"].lower() and "file" in descriptions["max_file_size"].lower()

    def test_string_representation(self) -> None:
        """Test string representation contains key information."""
        config = BaseStorageConfig(
            database_url="postgresql://user:password@localhost:5432/db",
            database_pool_size=20,
            database_timeout=60,
            data_directory="/custom/data",
            max_file_size=200 * 1024 * 1024,
        )

        str_repr = str(config)

        # Should contain non-sensitive field values
        assert "20" in str_repr
        assert "60" in str_repr
        assert "/custom/data" in str_repr
        # Database URL might be partially obscured or fully shown - depends on Pydantic

    def test_boundary_values(self) -> None:
        """Test boundary values for numeric fields."""
        # Minimum valid values
        config = BaseStorageConfig(
            database_url="sqlite:///test.db", database_pool_size=1, database_timeout=1, max_file_size=0
        )
        assert config.database_pool_size == 1
        assert config.database_timeout == 1
        assert config.max_file_size == 0

        # Large valid values
        config = BaseStorageConfig(
            database_url="sqlite:///test.db",
            database_pool_size=1000,
            database_timeout=3600,  # 1 hour
            max_file_size=10 * 1024 * 1024 * 1024,  # 10 GB
        )
        assert config.database_pool_size == 1000
        assert config.database_timeout == 3600
        assert config.max_file_size == 10 * 1024 * 1024 * 1024

    def test_data_directory_paths(self) -> None:
        """Test various data directory path formats."""
        path_formats = [
            "data",
            "./data",
            "../data",
            "/absolute/path/data",
            "~/user/data",
            "C:\\Windows\\Data",  # Windows path
            "/mnt/storage/data",  # Unix mount point
            "data/subdir/nested",  # Nested path
        ]

        for path in path_formats:
            config = BaseStorageConfig(database_url="sqlite:///test.db", data_directory=path)
            assert config.data_directory == path

    def test_database_url_formats(self) -> None:
        """Test various database URL formats."""
        url_formats = [
            "sqlite:///:memory:",  # In-memory SQLite
            "sqlite:///relative/path.db",  # Relative path
            "sqlite:////absolute/path.db",  # Absolute path
            "postgresql://localhost/db",  # No credentials
            "postgresql://user@localhost/db",  # Username only
            "postgresql://user:pass@localhost/db",  # Full credentials
            "postgresql://user:pass@localhost:5432/db",  # With port
            "mysql+pymysql://user:pass@localhost/db",  # Driver specification
            "redis://localhost:6379/0",  # Redis
            "mongodb://user:pass@localhost:27017/db?authSource=admin",  # MongoDB with query params
        ]

        for url in url_formats:
            config = BaseStorageConfig(database_url=url)
            assert config.database_url == url

    def test_validation_error_messages(self) -> None:
        """Test that validation error messages are helpful."""
        # Test database_url missing error
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig()

        errors = exc_info.value.errors()
        db_url_error = next(error for error in errors if error["loc"] == ("database_url",))
        assert "required" in db_url_error["msg"].lower() or "missing" in db_url_error["msg"].lower()

        # Test database_pool_size constraint error
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig(database_url="sqlite:///test.db", database_pool_size=0)

        errors = exc_info.value.errors()
        pool_error = next(error for error in errors if error["loc"] == ("database_pool_size",))
        assert "greater than 0" in pool_error["msg"]

        # Test max_file_size constraint error
        with pytest.raises(ValidationError) as exc_info:
            BaseStorageConfig(database_url="sqlite:///test.db", max_file_size=-1)

        errors = exc_info.value.errors()
        size_error = next(error for error in errors if error["loc"] == ("max_file_size",))
        assert "greater than or equal to 0" in size_error["msg"]
