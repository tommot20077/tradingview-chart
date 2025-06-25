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
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> BaseCoreSettings:
    """Provide mock settings for testing."""

    class TestConfig(BaseCoreSettings):
        """Test configuration for unit tests."""

        environment: str = "test"
        log_level: str = "DEBUG"

        class Config:
            env_prefix = "TEST_"

    return TestConfig()


@pytest.fixture
def sample_trade() -> Trade:
    """Provide a sample Trade instance for testing."""
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
    """Provide a sample Kline instance for testing."""
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
    """Provide a sample BaseEvent instance for testing."""
    return BaseEvent(event_type=EventType.TRADE, priority=EventPriority.NORMAL, data={"test": "data"}, source="test")


@pytest.fixture
def sample_trade_data() -> dict[str, Any]:
    """Provide sample trade data for testing."""
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
    """Provide sample kline data for testing."""
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
    """Provide a mock websocket for testing."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.wait_closed = AsyncMock()
    return mock_ws


@pytest.fixture
def mock_logger() -> MagicMock:
    """Provide a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics_registry() -> MagicMock:
    """Provide a mock metrics registry for testing."""
    registry = MagicMock()
    registry.register = MagicMock()
    registry.collect = MagicMock(return_value=[])
    return registry


@pytest.fixture(autouse=True)
def reset_global_state() -> Any:
    """Reset any global state before each test."""
    # This fixture can be used to reset singletons, clear caches, etc.
    yield
    # Cleanup after test if needed


@pytest.fixture
def temp_env_vars(monkeypatch: Any) -> Any:
    """Provide a way to temporarily set environment variables."""

    def _set_env_vars(**kwargs: Any) -> None:
        for key, value in kwargs.items():
            monkeypatch.setenv(key, str(value))

    return _set_env_vars


@pytest.fixture
def boundary_values() -> dict[str, Any]:
    """Provide boundary values for testing edge cases."""
    return {
        "min_decimal": Decimal("0.00000001"),
        "max_decimal": Decimal("999999999.99999999"),
        "zero": Decimal("0"),
        "negative": Decimal("-1.0"),
        "very_large": Decimal("1e10"),
        "very_small": Decimal("1e-10"),
        "empty_string": "",
        "max_string_length": "x" * 1000,
        "unicode_string": "测试数据🚀",
        "past_timestamp": datetime(2020, 1, 1, tzinfo=UTC),
        "future_timestamp": datetime(2030, 12, 31, tzinfo=UTC),
    }


@pytest.fixture
def invalid_data_samples() -> dict[str, Any]:
    """Provide various invalid data samples for negative testing."""
    return {
        "invalid_price": ["", "abc", "-1", "0", None, []],
        "invalid_quantity": ["", "xyz", "-0.1", "0", None, {}],
        "invalid_symbol": ["", None, 123, [], {}],
        "invalid_timestamp": ["not_a_date", None, 123, ""],
        "invalid_side": ["invalid_side", "", None, 123],
        "invalid_interval": ["invalid_interval", "", None, 999],
    }
