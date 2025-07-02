"""Test configuration and fixtures for asset_core tests."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_settings import SettingsConfigDict

from asset_core.config import BaseCoreSettings
from asset_core.models import BaseEvent, EventPriority, EventType, Kline, KlineInterval, \
    Trade, TradeSide


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Provides an instance of the default event loop for the test session.

    Description of what the fixture covers:
    This fixture ensures that asynchronous tests have a consistent event loop
    to run on throughout the entire test session. It creates a new event loop
    at the start of the session and closes it at the end.

    Preconditions:
    - `asyncio` module is available.

    Steps:
    - Get a new event loop policy.
    - Create a new event loop using the policy.
    - Yield the created event loop to the tests.
    - After all tests using this fixture are complete, close the event loop.

    Expected Result:
    - A functional `asyncio` event loop is provided for asynchronous tests.
    - The event loop is properly closed after the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> BaseCoreSettings:
    """Provides mock settings for testing.

    Description of what the fixture covers:
    This fixture provides a `BaseCoreSettings` instance with predefined values
    suitable for unit and integration tests. It uses an inner `TestConfig` class
    to define the mock settings, ensuring a consistent and isolated configuration
    for tests.

    Preconditions:
    - `BaseCoreSettings` class is defined and importable.

    Steps:
    - Defines an inner class `TestConfig` that inherits from `BaseCoreSettings`.
    - Sets `environment` to "test" and `log_level` to "DEBUG" within `TestConfig`.
    - Configures `TestConfig.Config` with `env_prefix = "TEST_"`.
    - Returns an instance of `TestConfig`.

    Expected Result:
    - A `BaseCoreSettings` instance with mock configuration values is returned,
      ready for use in tests that require application settings.
    """

    class TestConfig(BaseCoreSettings):
        """Test configuration for unit tests.

        Description of what the class covers:
        This class defines a mock configuration for testing purposes, inheriting
        from `BaseCoreSettings`. It sets default environment and log level values
        suitable for isolated unit and integration tests.

        Preconditions:
        - Inherits from `BaseCoreSettings`.

        Steps:
        - Defines `environment` as "test".
        - Defines `log_level` as "DEBUG".
        - Configures `env_prefix` to "TEST_" for environment variable loading.

        Expected Result:
        - Provides a consistent and isolated configuration for tests.
        """

        environment: str = "test"
        log_level: str = "DEBUG"

        model_config = SettingsConfigDict(
            env_prefix="TEST_",
        )

    return TestConfig()


@pytest.fixture
def sample_trade() -> Trade:
    """Provides a sample Trade instance for testing.

    Description of what the fixture covers:
    This fixture provides a pre-configured `Trade` object, useful for tests
    that require a valid and consistent trade data sample without needing
    to construct one repeatedly.

    Preconditions:
    - The `Trade` model is correctly defined and importable.
    - `Decimal`, `datetime` (with `UTC`), and `TradeSide` are available.

    Steps:
    - Creates a `Trade` instance with a fixed symbol, trade ID, price, quantity, side, and timestamp.

    Returns:
        Trade: A `Trade` object with predefined values for testing.
    """
    return Trade(
        symbol="BTCUSDT",
        trade_id="test_trade_123",
        price=Decimal("50000.50"),
        quantity=Decimal("0.001"),
        side=TradeSide.BUY,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_kline() -> Kline:
    """Provides a sample Kline instance for testing.

    Returns:
        Kline: A `Kline` object with predefined values for testing.
    """
    # Use a properly aligned time for 1-minute interval
    base_time = datetime(2023, 1, 1, 12, 5, 0, tzinfo=UTC)
    return Kline(
        symbol="BTCUSDT",
        interval=KlineInterval.MINUTE_1,
        open_time=base_time,
        close_time=base_time + timedelta(minutes=1),
        open_price=Decimal("50000.00"),
        high_price=Decimal("50100.00"),
        low_price=Decimal("49900.00"),
        close_price=Decimal("50050.00"),
        volume=Decimal("1.5"),
        quote_volume=Decimal("75000.00"),
        trades_count=10,
    )


@pytest.fixture
def sample_event() -> BaseEvent:
    """Provides a sample BaseEvent instance for testing.

    Description of what the fixture covers:
    This fixture provides a pre-configured `BaseEvent` object, useful for tests
    that require a generic event data sample without needing to construct one repeatedly.

    Preconditions:
    - The `BaseEvent`, `EventType`, and `EventPriority` models are correctly defined and importable.

    Steps:
    - Creates a `BaseEvent` instance with a specified event type (`EventType.TRADE`),
      priority (`EventPriority.NORMAL`), sample data (`{"test": "data"}`), and source (`"test"`).

    Returns:
        BaseEvent: A `BaseEvent` object with predefined values for testing.
    """
    return BaseEvent(event_type=EventType.TRADE, priority=EventPriority.NORMAL, data={"test": "data"}, source="test")


@pytest.fixture
def sample_trade_data() -> dict[str, Any]:
    """Provides sample trade data for testing.

    Description of what the fixture covers:
    This fixture provides a dictionary containing raw trade data, suitable for
    testing scenarios where data is received in a dictionary format before
    being converted into a `Trade` model.

    Preconditions:
    - `datetime` (with `UTC`) is available for timestamp generation.

    Steps:
    - Creates a dictionary with `symbol`, `trade_id`, `price` (as string),
      `quantity` (as string), `side` (as string), and `timestamp` (as ISO format string).

    Returns:
        dict[str, Any]: A dictionary containing sample trade data.
    """
    return {
        "symbol": "BTCUSDT",
        "trade_id": "test_trade_456",
        "price": "49999.99",
        "quantity": "0.002",
        "side": "sell",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_kline_data() -> dict[str, Any]:
    """Provides sample kline data for testing.

    Description of what the fixture covers:
    This fixture provides a dictionary containing raw kline data, suitable for
    testing scenarios where data is received in a dictionary format before
    being converted into a `Kline` model.

    Preconditions:
    - `datetime` (with `UTC`) and `timedelta` are available for timestamp generation.

    Steps:
    - Defines a `base_time` for timestamps.
    - Creates a dictionary with `symbol`, `interval` (as string), `open_time` (as ISO format string),
      `close_time` (as ISO format string), `open_price` (as string), `high_price` (as string),
      `low_price` (as string), `close_price` (as string), `volume` (as string),
      and `trade_count`.

    Returns:
        dict[str, Any]: A dictionary containing sample kline data.
    """
    base_time = datetime.now(UTC)
    return {
        "symbol": "ETHUSDT",
        "interval": "5m",
        "open_time": base_time.isoformat(),
        "close_time": (base_time + timedelta(minutes=5)).isoformat(),
        "open_price": "3000.00",
        "high_price": "3050.00",
        "low_price": "2980.00",
        "close_price": "3025.00",
        "volume": "10.5",
        "trade_count": 25,
    }


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Provides a mock websocket for testing asynchronous network interactions.

    Description of what the fixture covers:
    This fixture provides an `AsyncMock` object that simulates a websocket connection.
    It allows testing asynchronous network interactions without requiring a real
    websocket server.

    Preconditions:
    - `unittest.mock.AsyncMock` is available.

    Steps:
    - Creates an `AsyncMock` instance for the websocket.
    - Mocks the `send`, `recv`, `close`, and `wait_closed` methods as `AsyncMock`.

    Returns:
        AsyncMock: A mock object simulating a websocket connection with asynchronous methods.
    """
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.wait_closed = AsyncMock()
    return mock_ws


@pytest.fixture
def mock_logger() -> MagicMock:
    """Provides a mock logger for testing logging interactions.

    Description of what the fixture covers:
    This fixture provides a `MagicMock` object that simulates a logger.
    It allows tests to verify logging calls without actually writing to log files
    or console, making tests faster and more predictable.

    Preconditions:
    - `unittest.mock.MagicMock` is available.

    Steps:
    - Creates a `MagicMock` instance.

    Returns:
        MagicMock: A mock object simulating a logger.
    """
    return MagicMock()


@pytest.fixture
def mock_metrics_registry() -> MagicMock:
    """Provides a mock metrics registry for testing metric collection.

    Description of what the fixture covers:
    This fixture provides a `MagicMock` object that simulates a Prometheus metrics registry.
    It allows tests to verify metric registration and collection without needing a real
    metrics server or complex setup.

    Preconditions:
    - `unittest.mock.MagicMock` is available.

    Steps:
    - Creates a `MagicMock` instance for the registry.
    - Mocks the `register` method.
    - Mocks the `collect` method to return an empty list.

    Returns:
        MagicMock: A mock object simulating a Prometheus metrics registry.
    """
    registry = MagicMock()
    registry.register = MagicMock()
    registry.collect = MagicMock(return_value=[])
    return registry


@pytest.fixture(autouse=True)
def reset_global_state() -> Any:
    """Resets any global state before each test.

    Description of what the fixture covers:
    This fixture is automatically used by all tests (`autouse=True`)
    to ensure a clean and isolated environment for each test function.
    It yields control to the test and can include cleanup logic after the test.

    Preconditions:
    - None specific, designed for general test setup.

    Steps:
    - Yields control to the test function.
    - (Optional) Includes a section for cleanup logic to be executed after the test.

    Expected Result:
    - Each test runs in a fresh, isolated state, free from side effects of previous tests.
    """
    yield


@pytest.fixture
def temp_env_vars(monkeypatch: Any) -> Any:
    """Provides a way to temporarily set environment variables for tests.

    Description of what the fixture covers:
    This fixture provides a convenient way to temporarily set and unset environment
    variables within tests using the `monkeypatch` fixture. This is crucial for
    testing components that rely on environment-based configuration.

    Preconditions:
    - The `pytest` `monkeypatch` fixture is available.

    Args:
        monkeypatch (Any): The pytest `monkeypatch` fixture for modifying environment variables.

    Returns:
        Callable[[Any], None]: A callable that takes keyword arguments to set environment variables.

    Steps:
    - Defines an inner function `_set_env_vars` that iterates through keyword arguments.
    - For each key-value pair, it uses `monkeypatch.setenv` to set the environment variable.
    - Returns the `_set_env_vars` callable.

    Expected Result:
    - Environment variables are temporarily set for the duration of the test where `_set_env_vars` is called.
    - The original environment is restored after the test completes.
    """

    def _set_env_vars(**kwargs: Any) -> None:
        for key, value in kwargs.items():
            monkeypatch.setenv(key, str(value))

    return _set_env_vars


@pytest.fixture
def boundary_values() -> dict[str, Any]:
    """Provides boundary values for testing edge cases.

    Description of what the fixture covers:
    This fixture provides a dictionary containing various boundary values for
    different data types (numbers, strings, timestamps). These values are crucial
    for testing edge cases and ensuring robust validation and handling within models
    and functions.

    Preconditions:
    - `Decimal`, `datetime` (with `UTC`) are available for data generation.

    Steps:
    - Defines a dictionary with keys representing different boundary value categories.
    - Includes minimum and maximum decimal values, zero, negative, very large, and very small decimals.
    - Includes empty string, maximum string length, and unicode string examples.
    - Includes past and future timestamp examples.

    Returns:
        dict[str, Any]: A dictionary containing various boundary values for testing.

    Expected Result:
    - A dictionary of boundary values is returned, suitable for testing edge cases.
    """
    return {
        "min_decimal": Decimal("0.000000000001"),
        "max_decimal": Decimal("1000000000"),
        "zero": Decimal("0"),
        "negative": Decimal("-1.0"),
        "very_large": Decimal("1e10"),
        "very_small": Decimal("1e-12"),
        "min_price": Decimal("0.000000000001"),
        "max_price": Decimal("1000000000"),
        "min_volume": Decimal("0.001"),
        "max_volume": Decimal("10000000000"),
        "empty_string": "",
        "max_string_length": "x" * 1000,
        "unicode_string": "测试数据🚀",
        "past_timestamp": datetime(2020, 1, 1, tzinfo=UTC),
        "future_timestamp": datetime(2030, 12, 31, tzinfo=UTC),
    }


@pytest.fixture
def invalid_data_samples() -> dict[str, Any]:
    """Provides various invalid data samples for negative testing.

    Description of what the fixture covers:
    This fixture provides a dictionary containing various invalid data samples,
    categorized by field type. These samples are used for negative testing to
    ensure that models and functions correctly reject invalid inputs and raise
    appropriate errors.

    Preconditions:
    - None specific, designed to provide diverse invalid data.

    Steps:
    - Defines a dictionary with keys representing different field types (e.g., `invalid_price`, `invalid_symbol`).
    - Each key maps to a list of invalid values, including incorrect types, empty values, and out-of-range values.

    Returns:
        dict[str, Any]: A dictionary containing lists of invalid data samples
                        categorized by field type.
    """
    return {
        "invalid_price": ["", "abc", "-1", "0", None, []],
        "invalid_quantity": ["", "xyz", "-0.1", "0", None, {}],
        "invalid_symbol": ["", None, 123, [], {}],
        "invalid_timestamp": ["not_a_date", None, 123, ""],
        "invalid_side": ["invalid_side", "", None, 123],
        "invalid_interval": ["invalid_interval", "", None, 999],
    }
