"""Test configuration and fixtures for asset_core tests."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.asset_core.asset_core.config import BaseCoreSettings
from src.asset_core.asset_core.models import BaseEvent, EventPriority, EventType, Kline, \
    KlineInterval, Trade, TradeSide


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Provides an instance of the default event loop for the test session.

    This fixture ensures that asynchronous tests have a consistent event loop
    to run on.

    Yields:
        Any: The event loop instance.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> BaseCoreSettings:
    """Provides mock settings for testing.

    This fixture returns a `BaseCoreSettings` instance with predefined
    values suitable for unit and integration tests.

    Returns:
        BaseCoreSettings: A mock settings object.
    """

    class TestConfig(BaseCoreSettings):
        """Test configuration for unit tests."""

        environment: str = "test"
        log_level: str = "DEBUG"

        class Config:
            env_prefix = "TEST_"

    return TestConfig()


@pytest.fixture
def sample_trade() -> Trade:
    """Provides a sample Trade instance for testing.

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
    base_time = datetime(2023, 1, 1, 12, 5, 0, tzinfo=UTC)  # Aligned to minute boundary
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

    Returns:
        BaseEvent: A `BaseEvent` object with predefined values for testing.
    """
    return BaseEvent(event_type=EventType.TRADE, priority=EventPriority.NORMAL, data={"test": "data"}, source="test")


@pytest.fixture
def sample_trade_data() -> dict[str, Any]:
    """Provides sample trade data for testing.

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

    Returns:
        AsyncMock: A mock object simulating a websocket connection with `send`,
                   `recv`, `close`, and `wait_closed` methods.
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

    Returns:
        MagicMock: A mock object simulating a logger.
    """
    return MagicMock()


@pytest.fixture
def mock_metrics_registry() -> MagicMock:
    """Provides a mock metrics registry for testing metric collection.

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

    This fixture is automatically used by all tests (`autouse=True`)
    to ensure a clean and isolated environment for each test function.

    Yields:
        Any: Yields control to the test function.
    """
    # This fixture can be used to reset singletons, clear caches, etc.
    yield
    # Cleanup after test if needed


@pytest.fixture
def temp_env_vars(monkeypatch: Any) -> Any:
    """Provides a way to temporarily set environment variables for tests.

    Args:
        monkeypatch (Any): The pytest `monkeypatch` fixture for modifying environment variables.

    Returns:
        Callable[[Any], None]: A callable that takes keyword arguments to set environment variables.
    """

    def _set_env_vars(**kwargs: Any) -> None:
        for key, value in kwargs.items():
            monkeypatch.setenv(key, str(value))

    return _set_env_vars


@pytest.fixture
def boundary_values() -> dict[str, Any]:
    """Provides boundary values for testing edge cases.

    Returns:
        dict[str, Any]: A dictionary containing various boundary values
                        for numbers, strings, and timestamps.
    """
    return {
        "min_decimal": Decimal("0.000000000001"),  # Updated to 12 decimal places minimum
        "max_decimal": Decimal("1000000000"),  # Updated to new maximum price
        "zero": Decimal("0"),
        "negative": Decimal("-1.0"),
        "very_large": Decimal("1e10"),
        "very_small": Decimal("1e-12"),  # Updated to 12 decimal places precision
        "min_price": Decimal("0.000000000001"),  # 1E-12 minimum price
        "max_price": Decimal("1000000000"),  # 1B maximum price
        "min_volume": Decimal("0.001"),  # Updated minimum volume
        "max_volume": Decimal("10000000000"),  # Updated maximum volume (10B)
        "empty_string": "",
        "max_string_length": "x" * 1000,
        "unicode_string": "测试数据🚀",
        "past_timestamp": datetime(2020, 1, 1, tzinfo=UTC),
        "future_timestamp": datetime(2030, 12, 31, tzinfo=UTC),
    }


@pytest.fixture
def invalid_data_samples() -> dict[str, Any]:
    """Provides various invalid data samples for negative testing.

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
