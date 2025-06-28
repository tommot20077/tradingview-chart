"""Tests for provider interfaces."""

from abc import ABC
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide
from asset_core.providers.base import AbstractDataProvider


class MockDataProvider(AbstractDataProvider):
    """Mock implementation of AbstractDataProvider for testing."""

    def __init__(self, name: str = "mock"):
        self._name = name
        self._connected = False

    @property
    def name(self) -> str:
        return self._name

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def stream_trades(
        self,
        symbol: str,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Trade]:
        """Mock trade streaming."""

        async def generator() -> AsyncIterator[Trade]:
            if not self._connected:
                raise RuntimeError("Provider not connected")

            trade = Trade(
                symbol=symbol,
                trade_id="mock_123",
                price=Decimal("50000"),
                quantity=Decimal("0.01"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )
            yield trade

        return generator()

    def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,
    ) -> AsyncIterator[Kline]:
        """Mock kline streaming."""

        async def generator() -> AsyncIterator[Kline]:
            if not self._connected:
                raise RuntimeError("Provider not connected")

            open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            kline = Kline(
                symbol=symbol,
                interval=interval,
                open_time=open_time,
                close_time=open_time + KlineInterval.to_timedelta(interval),
                open_price=Decimal("50000"),
                high_price=Decimal("50100"),
                low_price=Decimal("49900"),
                close_price=Decimal("50050"),
                volume=Decimal("100"),
                quote_volume=Decimal("5000000"),
                trades_count=100,
            )
            yield kline

        return generator()

    async def fetch_historical_trades(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Trade]:
        """Mock historical trades fetch."""
        if not self._connected:
            raise RuntimeError("Provider not connected")

        return [
            Trade(
                symbol=symbol,
                trade_id="hist_123",
                price=Decimal("49500"),
                quantity=Decimal("0.005"),
                side=TradeSide.SELL,
                timestamp=start_time,
            )
        ]

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Kline]:
        """Mock historical klines fetch."""
        if not self._connected:
            raise RuntimeError("Provider not connected")

        return [
            Kline(
                symbol=symbol,
                interval=interval,
                open_time=start_time,
                close_time=start_time + KlineInterval.to_timedelta(interval),
                open_price=Decimal("49000"),
                high_price=Decimal("49200"),
                low_price=Decimal("48800"),
                close_price=Decimal("49100"),
                volume=Decimal("50"),
                quote_volume=Decimal("2455000"),
                trades_count=50,
            )
        ]

    async def get_exchange_info(self) -> dict[str, Any]:
        """Mock exchange info."""
        return {
            "exchange": "mock_exchange",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "status": "TRADING",
        }

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Mock symbol info."""
        return {
            "symbol": symbol,
            "status": "TRADING",
            "price_precision": 2,
            "quantity_precision": 8,
        }

    async def ping(self) -> float:
        """Mock ping."""
        return 10.5

    async def close(self) -> None:
        """Mock close."""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected


@pytest.mark.unit
class TestAbstractDataProvider:
    """Test AbstractDataProvider interface."""

    def test_is_abstract(self) -> None:
        """Test that AbstractDataProvider is abstract."""
        assert issubclass(AbstractDataProvider, ABC)

        with pytest.raises(TypeError):
            AbstractDataProvider()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_mock_provider_basic_operations(self) -> None:
        """Test basic operations of mock provider."""
        provider = MockDataProvider("test_provider")

        assert provider.name == "test_provider"
        assert not provider.is_connected

        await provider.connect()
        assert provider.is_connected

        await provider.disconnect()
        assert not provider.is_connected

    @pytest.mark.asyncio
    async def test_mock_provider_context_manager(self) -> None:
        """Test provider as async context manager."""
        provider = MockDataProvider()

        assert not provider.is_connected

        async with provider:
            assert provider.is_connected

        assert not provider.is_connected

    @pytest.mark.asyncio
    async def test_mock_provider_stream_trades(self) -> None:
        """Test streaming trades from mock provider."""
        provider = MockDataProvider()

        with pytest.raises(RuntimeError, match="Provider not connected"):
            async for _trade in provider.stream_trades("BTCUSDT"):
                pass

        await provider.connect()

        trades = []
        async for trade in provider.stream_trades("BTCUSDT"):
            trades.append(trade)
            break

        assert len(trades) == 1
        assert isinstance(trades[0], Trade)
        assert trades[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_mock_provider_stream_klines(self) -> None:
        """Test streaming klines from mock provider."""
        provider = MockDataProvider()

        await provider.connect()

        klines = []
        async for kline in provider.stream_klines("BTCUSDT", KlineInterval.MINUTE_1):
            klines.append(kline)
            break

        assert len(klines) == 1
        assert isinstance(klines[0], Kline)
        assert klines[0].symbol == "BTCUSDT"
        assert klines[0].interval == KlineInterval.MINUTE_1

    @pytest.mark.asyncio
    async def test_mock_provider_historical_trades(self) -> None:
        """Test fetching historical trades."""
        provider = MockDataProvider()

        await provider.connect()

        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)

        trades = await provider.fetch_historical_trades("BTCUSDT", start_time, end_time)

        assert len(trades) == 1
        assert isinstance(trades[0], Trade)
        assert trades[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_mock_provider_historical_klines(self) -> None:
        """Test fetching historical klines."""
        provider = MockDataProvider()

        await provider.connect()

        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)

        klines = await provider.fetch_historical_klines("BTCUSDT", KlineInterval.MINUTE_1, start_time, end_time)

        assert len(klines) == 1
        assert isinstance(klines[0], Kline)
        assert klines[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_mock_provider_exchange_info(self) -> None:
        """Test getting exchange info."""
        provider = MockDataProvider()

        info = await provider.get_exchange_info()

        assert isinstance(info, dict)
        assert "exchange" in info
        assert "symbols" in info

    @pytest.mark.asyncio
    async def test_mock_provider_symbol_info(self) -> None:
        """Test getting symbol info."""
        provider = MockDataProvider()

        info = await provider.get_symbol_info("BTCUSDT")

        assert isinstance(info, dict)
        assert info["symbol"] == "BTCUSDT"
        assert "price_precision" in info

    @pytest.mark.asyncio
    async def test_mock_provider_ping(self) -> None:
        """Test provider ping."""
        provider = MockDataProvider()

        latency = await provider.ping()

        assert isinstance(latency, float)
        assert latency > 0
