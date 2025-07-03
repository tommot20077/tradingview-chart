"""
Contract tests for AbstractDataProvider interface.

Comprehensive tests to verify that any implementation of AbstractDataProvider
follows the expected behavioral contracts and interface specifications.
"""

import abc
import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade
from asset_core.providers.base import AbstractDataProvider
from .base_contract_test import AsyncContractTestMixin, BaseContractTest, \
    MockImplementationBase


class MockDataProvider(AbstractDataProvider, MockImplementationBase):
    """Mock implementation of AbstractDataProvider for contract testing.

    Provides a complete implementation that follows the interface contract
    while using mock data for testing purposes.
    """

    def __init__(self, provider_name: str = "mock_provider"):
        super().__init__()
        self._provider_name = provider_name
        self._ping_latency = 50.0  # Mock latency in ms

        # Predefined valid symbols for testing
        self._valid_symbols = {"BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"}

        # Predefined historical data for testing
        self._predefined_trades = self._generate_predefined_trades()
        self._predefined_klines = self._generate_predefined_klines()

    def _generate_predefined_trades(self) -> dict[str, list[Trade]]:
        """Generate predefined trade data for testing."""
        trades_data = {}
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for symbol in self._valid_symbols:
            trades = []
            base_price = 50000.0 if symbol == "BTCUSDT" else 3000.0

            # Generate 200 trades across different time periods
            for i in range(200):
                trade = Trade(
                    symbol=symbol,
                    trade_id=f"predefined_trade_{symbol}_{i}",
                    price=base_price + i * 10,
                    quantity=1.0 + i * 0.1,
                    timestamp=base_time.replace(
                        hour=i // 10, minute=(i % 10) * 6, second=i % 60, microsecond=(i * 1000) % 1000000
                    ),
                    side="buy" if i % 2 == 0 else "sell",
                    is_maker=i % 3 == 0,
                )
                trades.append(trade)

            trades_data[symbol] = trades

        return trades_data

    def _generate_predefined_klines(self) -> dict[tuple[str, KlineInterval], list[Kline]]:
        """Generate predefined kline data for testing."""
        klines_data = {}
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        for symbol in self._valid_symbols:
            for interval in [KlineInterval.MINUTE_1, KlineInterval.HOUR_1, KlineInterval.DAY_1]:
                klines = []
                base_price = 50000.0 if symbol == "BTCUSDT" else 3000.0

                # Generate 50 klines across different time periods
                for i in range(50):
                    if interval == KlineInterval.MINUTE_1:
                        # Use hours and minutes for MINUTE_1 interval
                        hour_part = i // 60
                        minute_part = i % 60
                        open_time = base_time.replace(hour=hour_part, minute=minute_part, second=0, microsecond=0)
                        close_time = open_time.replace(second=59, microsecond=999999)
                    elif interval == KlineInterval.HOUR_1:
                        # Use day and hour for HOUR_1 interval
                        day_part = (i // 24) + 1
                        hour_part = i % 24
                        open_time = base_time.replace(day=day_part, hour=hour_part, minute=0, second=0, microsecond=0)
                        close_time = open_time.replace(minute=59, second=59, microsecond=999999)
                    else:  # DAY_1
                        # Use day for DAY_1 interval
                        day_part = (i % 28) + 1
                        open_time = base_time.replace(day=day_part, hour=0, minute=0, second=0, microsecond=0)
                        close_time = open_time.replace(hour=23, minute=59, second=59, microsecond=999999)

                    kline = Kline(
                        symbol=symbol,
                        interval=interval,
                        open_time=open_time,
                        close_time=close_time,
                        open_price=base_price + i * 50,
                        high_price=base_price + i * 50 + 100,
                        low_price=base_price + i * 50 - 100,
                        close_price=base_price + i * 50 + 25,
                        volume=100.0 + i * 10,
                        quote_volume=base_price * 100 + i * 10000,
                        trades_count=1000 + i * 100,
                    )
                    klines.append(kline)

                klines_data[(symbol, interval)] = klines

        return klines_data

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self) -> None:
        """Connects to the mock data provider.

        Simulates a connection process with a small delay.

        Raises:
            RuntimeError: If the provider is already connected or closed.
        """
        self._check_not_closed()
        if self._is_connected:
            raise RuntimeError("Already connected")

        # Simulate connection process
        await asyncio.sleep(0.01)  # Small delay to simulate network
        self._is_connected = True

    async def disconnect(self) -> None:
        """Disconnects from the mock data provider.

        Resets the `is_connected` flag. This operation is idempotent.
        """
        self._is_connected = False

    async def stream_trades(self, symbol: str, *, start_from: datetime | None = None) -> AsyncIterator[Trade]:  # noqa: ARG002
        """Streams mock real-time trades for a given symbol.

        Args:
            symbol (str): The trading symbol for which to stream trades.
            _start_from (datetime | None): Optional datetime to start streaming from.
                                         (Ignored in this mock implementation).

        Yields:
            Trade: A mock `Trade` object.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
            ValueError: If the symbol is not found.
        """
        self._check_not_closed()
        self._check_connected()

        # Check if symbol exists in our predefined valid symbols
        if symbol not in self._valid_symbols:
            raise ValueError(f"Symbol '{symbol}' not found")

        # Generate mock trades
        base_time = datetime.now(UTC)
        for i in range(10):  # Stream 10 mock trades
            trade = Trade(
                symbol=symbol,
                trade_id=f"mock_trade_{i}",
                price=50000.0 + i * 10,
                quantity=1.0 + i * 0.1,
                timestamp=base_time.replace(microsecond=i * 1000),
                side="buy" if i % 2 == 0 else "sell",
                is_maker=i % 3 == 0,
            )
            yield trade
            await asyncio.sleep(0.001)  # Small delay between trades

    async def stream_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        *,
        start_from: datetime | None = None,  # noqa: ARG002
    ) -> AsyncIterator[Kline]:
        """Streams mock real-time klines for a given symbol and interval.

        Args:
            symbol (str): The trading symbol for which to stream klines.
            interval (KlineInterval): The Kline interval.
            _start_from (datetime | None): Optional datetime to start streaming from.
                                         (Ignored in this mock implementation).

        Yields:
            Kline: A mock `Kline` object.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
            ValueError: If the symbol is not found.
        """
        self._check_not_closed()
        self._check_connected()

        # Check if symbol exists in our predefined valid symbols
        if symbol not in self._valid_symbols:
            raise ValueError(f"Symbol '{symbol}' not found")

        # Generate mock klines
        base_time = datetime.now(UTC)
        for i in range(5):  # Stream 5 mock klines
            open_time = base_time.replace(minute=i, second=0, microsecond=0)
            close_time = open_time.replace(minute=i, second=59, microsecond=999999)

            kline = Kline(
                symbol=symbol,
                interval=interval,
                open_time=open_time,
                close_time=close_time,
                open_price=50000.0 + i * 100,
                high_price=50100.0 + i * 100,
                low_price=49900.0 + i * 100,
                close_price=50050.0 + i * 100,
                volume=100.0 + i * 10,
                quote_volume=5005000.0 + i * 1000,
                trades_count=1000 + i * 100,
            )
            yield kline
            await asyncio.sleep(0.01)  # Small delay between klines

    async def fetch_historical_trades(
        self, symbol: str, start_time: datetime, end_time: datetime, *, limit: int | None = None
    ) -> list[Trade]:
        """Fetches mock historical trades for a given symbol within a time range.

        Args:
            symbol (str): The trading symbol.
            start_time (datetime): The start time for the historical data.
            end_time (datetime): The end time for the historical data.
            limit (int | None): Optional maximum number of trades to fetch.

        Returns:
            list[Trade]: A list of mock `Trade` objects.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
            ValueError: If start_time > end_time.
        """
        self._check_not_closed()
        self._check_connected()

        # Validate time range
        if start_time > end_time:
            raise ValueError("start_time cannot be greater than end_time")

        # Handle edge case where start_time equals end_time
        if start_time == end_time:
            return []

        # Handle edge case where limit is 0
        if limit is not None and limit <= 0:
            return []

        # Get predefined trades for the symbol
        if symbol not in self._predefined_trades:
            return []  # Return empty list for non-existent symbols

        all_trades = self._predefined_trades[symbol]

        # Filter trades by time range
        filtered_trades = [trade for trade in all_trades if start_time <= trade.timestamp < end_time]

        # Apply limit if specified
        if limit is not None:
            filtered_trades = filtered_trades[:limit]

        return filtered_trades

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int | None = None,
    ) -> list[Kline]:
        """Fetches mock historical klines for a given symbol and interval within a time range.

        Args:
            symbol (str): The trading symbol.
            interval (KlineInterval): The Kline interval.
            start_time (datetime): The start time for the historical data.
            end_time (datetime): The end time for the historical data.
            limit (int | None): Optional maximum number of klines to fetch.

        Returns:
            list[Kline]: A list of mock `Kline` objects.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
            ValueError: If start_time > end_time.
        """
        self._check_not_closed()
        self._check_connected()

        # Validate time range
        if start_time > end_time:
            raise ValueError("start_time cannot be greater than end_time")

        # Handle edge case where start_time equals end_time
        if start_time == end_time:
            return []

        # Handle edge case where limit is 0
        if limit is not None and limit <= 0:
            return []

        # Get predefined klines for the symbol and interval
        key = (symbol, interval)
        if key not in self._predefined_klines:
            return []  # Return empty list for non-existent symbols or intervals

        all_klines = self._predefined_klines[key]

        # Filter klines by time range
        filtered_klines = [kline for kline in all_klines if start_time <= kline.open_time < end_time]

        # Apply limit if specified
        if limit is not None:
            filtered_klines = filtered_klines[:limit]

        return filtered_klines

    async def get_exchange_info(self) -> dict[str, Any]:
        """Retrieves mock exchange information.

        Returns:
            dict[str, Any]: A dictionary containing mock exchange details.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
        """
        self._check_not_closed()
        self._check_connected()

        return {
            "exchange": "MockExchange",
            "status": "normal",
            "server_time": datetime.now(UTC).isoformat(),
            "rate_limits": [
                {"type": "requests", "interval": "minute", "limit": 1200},
                {"type": "orders", "interval": "second", "limit": 10},
            ],
            "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
        }

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Retrieves mock symbol-specific information.

        Args:
            symbol (str): The trading symbol for which to retrieve information.

        Returns:
            dict[str, Any]: A dictionary containing mock symbol details.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
            ValueError: If the symbol is not found.
        """
        self._check_not_closed()
        self._check_connected()

        # Check if symbol exists in our predefined valid symbols
        if symbol not in self._valid_symbols:
            raise ValueError(f"Symbol '{symbol}' not found")

        return {
            "symbol": symbol,
            "status": "trading",
            "base_asset": symbol[:-4] if symbol.endswith("USDT") else symbol[:3],
            "quote_asset": "USDT" if symbol.endswith("USDT") else symbol[3:],
            "price_precision": 2,
            "quantity_precision": 8,
            "min_price": "0.01",
            "max_price": "1000000.00",
            "min_quantity": "0.00001",
            "max_quantity": "9000.00",
        }

    async def ping(self) -> float:
        """Checks connectivity and returns mock latency.

        Returns:
            float: A mock latency value in milliseconds.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
        """
        self._check_not_closed()
        self._check_connected()

        # Simulate network ping
        await asyncio.sleep(0.001)
        return self._ping_latency

    async def close(self) -> None:
        """Closes the provider and cleans up resources.

        This method disconnects the provider and sets its internal state to closed.
        This operation is idempotent.
        """
        if not self._is_closed:
            await self.disconnect()
            self._is_closed = True

    async def __aenter__(self) -> "MockDataProvider":
        """Asynchronous context manager entry point.

        Automatically connects the provider upon entering the `async with` block.

        Returns:
            MockDataProvider: The instance of the provider itself.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Asynchronous context manager exit point.

        Automatically closes the provider upon exiting the `async with` block.

        Args:
            exc_type (Any): The type of the exception raised, if any.
            exc_val (Any): The exception instance raised, if any.
            exc_tb (Any): The traceback object, if an exception was raised.

        """
        await self.close()


class TestAbstractDataProviderContract(BaseContractTest, AsyncContractTestMixin):
    """Contract tests for AbstractDataProvider interface.

    These tests verify that any implementation of AbstractDataProvider
    follows the expected behavioral contracts and interface specifications.
    """

    @pytest.fixture
    async def provider(self) -> MockDataProvider:
        """Provides a mock data provider instance for testing.

        Returns:
            MockDataProvider: An instance of the mock data provider.
        """
        return MockDataProvider("test_provider")

    def test_required_methods_defined(self) -> None:
        """Test that all required abstract methods are defined in the interface.

        Description of what the test covers.
        Verifies that `AbstractDataProvider` declares all necessary methods
        as abstract and that they have the correct signatures.

        Expected Result:
        - All required methods are present as abstract methods.
        - Method signatures match the expected interface.
        """
        abstract_methods = self.get_abstract_methods(AbstractDataProvider)

        required_methods = {
            "name",
            "connect",
            "disconnect",
            "stream_trades",
            "stream_klines",
            "fetch_historical_trades",
            "fetch_historical_klines",
            "get_exchange_info",
            "get_symbol_info",
            "ping",
            "close",
            "is_connected",
        }

        # All required methods should be abstract
        assert required_methods.issubset(set(abstract_methods)), (
            f"Missing abstract methods: {required_methods - set(abstract_methods)}"
        )

    def test_method_signatures(self) -> None:
        """Test that all abstract methods have correct signatures.

        Description of what the test covers.
        Verifies parameter types, return types, and async/sync designation
        for all methods in the interface.

        Expected Result:
        - All methods have correct parameter and return type annotations.
        - Async methods are properly marked as async.
        """
        # Test key method signatures
        connect_sig = self.get_method_signature(AbstractDataProvider, "connect")
        assert len(connect_sig.parameters) == 1  # only self

        stream_trades_sig = self.get_method_signature(AbstractDataProvider, "stream_trades")
        assert len(stream_trades_sig.parameters) == 3  # self, symbol, start_from
        assert "symbol" in stream_trades_sig.parameters
        assert "start_from" in stream_trades_sig.parameters

        fetch_historical_trades_sig = self.get_method_signature(AbstractDataProvider, "fetch_historical_trades")
        assert len(fetch_historical_trades_sig.parameters) == 5  # self, symbol, start_time, end_time, limit
        assert "symbol" in fetch_historical_trades_sig.parameters
        assert "start_time" in fetch_historical_trades_sig.parameters
        assert "end_time" in fetch_historical_trades_sig.parameters
        assert "limit" in fetch_historical_trades_sig.parameters

        # Test that core methods are async
        assert self.is_async_method(AbstractDataProvider, "connect")
        assert self.is_async_method(AbstractDataProvider, "disconnect")
        assert self.is_async_method(AbstractDataProvider, "stream_trades")
        assert self.is_async_method(AbstractDataProvider, "stream_klines")
        assert self.is_async_method(AbstractDataProvider, "fetch_historical_trades")
        assert self.is_async_method(AbstractDataProvider, "fetch_historical_klines")
        assert self.is_async_method(AbstractDataProvider, "get_exchange_info")
        assert self.is_async_method(AbstractDataProvider, "get_symbol_info")
        assert self.is_async_method(AbstractDataProvider, "ping")
        assert self.is_async_method(AbstractDataProvider, "close")

        # Test that properties are not async methods
        assert not self.is_async_method(AbstractDataProvider, "name")
        assert not self.is_async_method(AbstractDataProvider, "is_connected")

    def test_async_context_manager_protocol(self) -> None:
        """Test that the provider implements async context manager protocol.

        Description of what the test covers.
        Verifies that `__aenter__` and `__aexit__` methods are present and
        that they work correctly for resource management.

        Expected Result:
        - Provider has `__aenter__` and `__aexit__` methods.
        - Can be used in `async with` statements.
        """
        # Test that AbstractDataProvider has async context manager methods
        assert hasattr(AbstractDataProvider, "__aenter__")
        assert hasattr(AbstractDataProvider, "__aexit__")
        assert callable(AbstractDataProvider.__aenter__)
        assert callable(AbstractDataProvider.__aexit__)

        # Test that these methods are async
        assert self.is_async_method(AbstractDataProvider, "__aenter__")
        assert self.is_async_method(AbstractDataProvider, "__aexit__")

    def test_inheritance_chain(self) -> None:
        """Test that AbstractDataProvider correctly inherits from abc.ABC.

        Description of what the test covers.
        Verifies that the abstract provider follows proper inheritance patterns
        for abstract base classes.

        Expected Result:
        - `AbstractDataProvider` should inherit from `abc.ABC`.
        - Should be properly marked as abstract class.
        """

        # Test inheritance from ABC
        assert issubclass(AbstractDataProvider, abc.ABC)

        # Test that the class itself is abstract (cannot be instantiated)
        with pytest.raises(TypeError):
            AbstractDataProvider()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_mock_implementation_completeness(self, provider: MockDataProvider) -> None:
        """Test that the mock implementation provides complete interface coverage.

        Description of what the test covers.
        Creates a complete mock implementation and verifies that all methods
        work correctly and follow the expected behavioral contracts.

        Expected Result:
        - All abstract methods are implemented.
        - Methods return expected types.
        - State transitions work correctly.
        """
        # Test that all abstract methods are implemented
        abstract_methods = self.get_abstract_methods(AbstractDataProvider)

        # Properties that should be implemented as properties, not methods
        expected_properties = {"name", "is_connected"}

        for method_name in abstract_methods:
            assert hasattr(provider, method_name), f"Missing method: {method_name}"
            method = getattr(provider, method_name)

            if method_name in expected_properties:
                # For properties, check they can be accessed (not callable)
                try:
                    _ = method  # Try to access the property
                    assert not callable(method), f"Property {method_name} should not be callable"
                except AttributeError:
                    pytest.fail(f"Property {method_name} is not accessible")
            else:
                assert callable(method), f"Method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_connection_state_management(self, provider: MockDataProvider) -> None:
        """Test connection state management and transitions.

        Description of what the test covers.
        Verifies that connection states are properly managed and that
        operations fail appropriately based on connection state.

        Preconditions:
        - Provider is initialized but not connected.

        Steps:
        - Verify initial disconnected state.
        - Connect and verify connected state.
        - Test that operations work when connected.
        - Disconnect and verify disconnected state.
        - Test that operations fail when disconnected.

        Expected Result:
        - Connection state is properly tracked.
        - Operations respect connection state requirements.
        - State transitions work correctly.
        """
        # Test initial state (should be disconnected)
        assert not provider.is_connected

        # Test that operations fail when not connected
        await self.assert_method_raises_when_not_ready(provider, "stream_trades", RuntimeError, "BTCUSDT")

        await self.assert_method_raises_when_not_ready(provider, "ping", RuntimeError)

        # Test connection
        await provider.connect()
        assert provider.is_connected

        # Test that connecting again raises error
        with pytest.raises(RuntimeError, match="Already connected"):  # type: ignore[unreachable]
            await provider.connect()

        # Test that operations work when connected
        ping_result = await provider.ping()
        assert isinstance(ping_result, int | float)
        assert ping_result >= 0

        # Test disconnection
        await provider.disconnect()
        assert not provider.is_connected

        # Test that operations fail again after disconnect
        await self.assert_method_raises_when_not_ready(provider, "ping", RuntimeError)

    @pytest.mark.asyncio
    async def test_provider_name_property(self, provider: MockDataProvider) -> None:
        """Test that provider name property works correctly.

        Description of what the test covers.
        Verifies that the `name` property returns a string identifier
        for the provider.

        Expected Result:
        - `name` property returns a non-empty string.
        - `name` is consistent across calls.
        """
        name = provider.name
        assert isinstance(name, str)
        assert len(name) > 0

        # Name should be consistent
        assert provider.name == name

    @pytest.mark.asyncio
    async def test_trade_streaming_interface(self, provider: MockDataProvider) -> None:
        """Test real-time trade streaming functionality.

        Description of what the test covers.
        Verifies that `stream_trades` returns an async iterator that
        yields `Trade` objects with correct data.

        Expected Result:
        - `stream_trades` returns async iterator.
        - Yields `Trade` objects with valid data.
        - Stream can be consumed properly.
        """
        await provider.connect()

        symbol = "BTCUSDT"
        trades_received = []

        # Test streaming trades
        async for trade in provider.stream_trades(symbol):
            trades_received.append(trade)
            assert isinstance(trade, Trade)
            assert trade.symbol == symbol
            assert isinstance(trade.price, int | float | Decimal)
            assert trade.price > 0
            assert isinstance(trade.quantity, int | float | Decimal)
            assert trade.quantity > 0
            assert isinstance(trade.timestamp, datetime)
            assert trade.side in ["buy", "sell"]

            # Break after getting a few trades for testing
            if len(trades_received) >= 3:
                break

        assert len(trades_received) >= 3

    @pytest.mark.asyncio
    async def test_kline_streaming_interface(self, provider: MockDataProvider) -> None:
        """Test real-time kline streaming functionality.

        Description of what the test covers.
        Verifies that `stream_klines` returns an async iterator that
        yields `Kline` objects with correct data.

        Expected Result:
        - `stream_klines` returns async iterator.
        - Yields `Kline` objects with valid data.
        - OHLC data is properly formatted.
        """
        await provider.connect()

        symbol = "ETHUSDT"
        interval = KlineInterval.MINUTE_1
        klines_received = []

        # Test streaming klines
        async for kline in provider.stream_klines(symbol, interval):
            klines_received.append(kline)
            assert isinstance(kline, Kline)
            assert kline.symbol == symbol
            assert kline.interval == interval
            assert isinstance(kline.open_time, datetime)
            assert isinstance(kline.close_time, datetime)
            assert kline.close_time > kline.open_time

            # Validate OHLC data
            assert kline.open_price > 0
            assert kline.high_price >= kline.open_price
            assert kline.low_price <= kline.open_price
            assert kline.close_price > 0
            assert kline.volume >= 0

            # Break after getting a few klines for testing
            if len(klines_received) >= 2:
                break

        assert len(klines_received) >= 2

    async def test_historical_trade_fetching(self, provider: MockDataProvider) -> None:
        """Test historical trade data fetching.

        Description of what the test covers.
        Verifies that `fetch_historical_trades` returns trade data
        within specified time ranges and limits.

        Expected Result:
        - Returns list of `Trade` objects.
        - Respects time range parameters.
        - Respects limit parameter.
        - Data is properly formatted.
        """
        await provider.connect()

        symbol = "ADAUSDT"
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 1, tzinfo=UTC)

        # Test basic historical fetch
        trades = await provider.fetch_historical_trades(symbol, start_time, end_time)
        assert isinstance(trades, list)
        assert len(trades) > 0
        assert all(isinstance(trade, Trade) for trade in trades)

        # Test with time range
        trades_with_range = await provider.fetch_historical_trades(symbol, start_time, end_time)
        assert isinstance(trades_with_range, list)
        assert all(isinstance(trade, Trade) for trade in trades_with_range)

        # Test with limit
        limited_trades = await provider.fetch_historical_trades(symbol, start_time, end_time, limit=5)
        assert len(limited_trades) == 5

    @pytest.mark.asyncio
    async def test_historical_kline_fetching(self, provider: MockDataProvider) -> None:
        """Test historical kline data fetching.

        Description of what the test covers.
        Verifies that `fetch_historical_klines` returns kline data
        within specified parameters.

        Expected Result:
        - Returns list of `Kline` objects.
        - Respects time range and interval parameters.
        - Respects limit parameter.
        - Data is properly formatted.
        """
        await provider.connect()

        symbol = "SOLUSDT"
        interval = KlineInterval.HOUR_1
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = datetime(2024, 1, 2, tzinfo=UTC)

        # Test basic historical fetch
        klines = await provider.fetch_historical_klines(symbol, interval, start_time, end_time)
        assert isinstance(klines, list)
        assert len(klines) > 0
        assert all(isinstance(kline, Kline) for kline in klines)

        # Test with time range
        klines_with_range = await provider.fetch_historical_klines(symbol, interval, start_time, end_time)
        assert isinstance(klines_with_range, list)
        assert all(isinstance(kline, Kline) for kline in klines_with_range)

        # Test with limit
        limited_klines = await provider.fetch_historical_klines(symbol, interval, start_time, end_time, limit=3)
        assert len(limited_klines) <= 3  # May be less due to time range constraints

    @pytest.mark.asyncio
    async def test_exchange_info_interface(self, provider: MockDataProvider) -> None:
        """Test exchange information retrieval.

        Description of what the test covers.
        Verifies that `get_exchange_info` returns structured
        information about the exchange.

        Expected Result:
        - Returns dictionary with exchange metadata.
        - Contains expected fields.
        - Data is properly formatted.
        """
        await provider.connect()

        exchange_info = await provider.get_exchange_info()
        assert isinstance(exchange_info, dict)

        # Should contain basic exchange information
        expected_fields = {"exchange", "status", "server_time"}
        assert all(field in exchange_info for field in expected_fields)

    async def test_symbol_info_interface(self, provider: MockDataProvider) -> None:
        """Test symbol-specific information retrieval.

        Description of what the test covers.
        Verifies that `get_symbol_info` returns detailed information
        about a specific trading symbol.

        Expected Result:
        - Returns dictionary with symbol metadata.
        - Contains trading specifications.
        - Data is properly formatted.
        """
        await provider.connect()

        symbol = "BTCUSDT"
        symbol_info = await provider.get_symbol_info(symbol)
        assert isinstance(symbol_info, dict)

        # Should contain the requested symbol
        assert symbol_info["symbol"] == symbol

        # Should contain basic symbol information
        expected_fields = {"symbol", "status", "base_asset", "quote_asset"}
        assert all(field in symbol_info for field in expected_fields)

    async def test_ping_latency_measurement(self, provider: MockDataProvider) -> None:
        """Test connectivity and latency measurement.

        Description of what the test covers.
        Verifies that `ping` returns latency measurements in milliseconds
        and can be used to monitor connection quality.

        Expected Result:
        - Returns numeric latency value.
        - Latency is in reasonable range (0-10000ms).
        - Consistent measurements over multiple calls.
        """
        await provider.connect()

        # Test single ping
        latency = await provider.ping()
        assert isinstance(latency, int | float)
        assert 0 <= latency <= 10000  # Reasonable latency range

        # Test multiple pings for consistency
        latencies = []
        for _ in range(3):
            ping_result = await provider.ping()
            latencies.append(ping_result)
            assert isinstance(ping_result, int | float)
            assert ping_result >= 0

        # All measurements should be reasonable
        assert all(0 <= lat <= 10000 for lat in latencies)

    @pytest.mark.asyncio
    async def test_async_context_manager_behavior(self, provider: MockDataProvider) -> None:
        """
        Test async context manager resource management.

        Ensures that the provider properly implements async context
        manager protocol and handles connection lifecycle.

        Expected Result:
            - Can be used in async with statements
            - Automatically connects on enter
            - Automatically closes on exit
        """
        # Test context manager usage
        async with provider as ctx_provider:
            assert ctx_provider is not None  # Context manager should return something
            assert provider.is_connected

            # Should be able to use provider methods
            ping_result = await ctx_provider.ping()
            assert ping_result >= 0

        # Should be closed after context exit
        assert provider.is_closed

    @pytest.mark.asyncio
    async def test_closed_state_handling(self, provider: MockDataProvider) -> None:
        """
        Test that operations fail appropriately when provider is closed.

        Verifies that attempting to use a closed provider raises
        appropriate exceptions.

        Expected Result:
            - Operations raise RuntimeError when provider is closed
            - Error messages are clear and helpful
        """
        # Close the provider
        await provider.close()

        # Test that operations fail when closed
        await self.assert_method_raises_when_not_ready(provider, "connect", RuntimeError)

        await self.assert_method_raises_when_not_ready(provider, "stream_trades", RuntimeError, "BTCUSDT")

        await self.assert_method_raises_when_not_ready(provider, "ping", RuntimeError)

    @pytest.mark.asyncio
    async def test_historical_data_boundary_conditions(self, provider: MockDataProvider) -> None:
        """Test various time range and limit boundary conditions for historical data fetching.

        Description of what the test covers:
        This test verifies that the historical data fetching methods handle edge cases
        and boundary conditions correctly, including equal start/end times, invalid
        time ranges, zero/negative limits, and empty result scenarios.

        Expected Result:
        - start_time == end_time should return empty list
        - start_time > end_time should raise ValueError
        - limit=0 should return empty list
        - limit=1 should return single result
        - Very large limits should be handled gracefully
        - Time ranges with no data should return empty list
        """
        await provider.connect()

        symbol = "BTCUSDT"
        base_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 1, tzinfo=UTC)

        # Test start_time == end_time (should return empty list)
        trades = await provider.fetch_historical_trades(symbol, base_time, base_time)
        assert trades == []

        klines = await provider.fetch_historical_klines(symbol, KlineInterval.MINUTE_1, base_time, base_time)
        assert klines == []

        # Test start_time > end_time (should raise ValueError)
        future_time = datetime(2024, 1, 2, tzinfo=UTC)
        with pytest.raises(ValueError, match="start_time cannot be greater than end_time"):
            await provider.fetch_historical_trades(symbol, future_time, base_time)

        with pytest.raises(ValueError, match="start_time cannot be greater than end_time"):
            await provider.fetch_historical_klines(symbol, KlineInterval.MINUTE_1, future_time, base_time)

        # Test limit=0 (should return empty list)
        trades = await provider.fetch_historical_trades(symbol, base_time, end_time, limit=0)
        assert trades == []

        klines = await provider.fetch_historical_klines(symbol, KlineInterval.MINUTE_1, base_time, end_time, limit=0)
        assert klines == []

        # Test limit=1 (should return single result)
        trades = await provider.fetch_historical_trades(symbol, base_time, end_time, limit=1)
        assert len(trades) == 1
        assert isinstance(trades[0], Trade)

        klines = await provider.fetch_historical_klines(symbol, KlineInterval.MINUTE_1, base_time, end_time, limit=1)
        assert len(klines) == 1
        assert isinstance(klines[0], Kline)

        # Test very large limit (should be handled gracefully)
        trades = await provider.fetch_historical_trades(symbol, base_time, end_time, limit=999999)
        assert isinstance(trades, list)
        assert len(trades) >= 0

        klines = await provider.fetch_historical_klines(
            symbol, KlineInterval.MINUTE_1, base_time, end_time, limit=999999
        )
        assert isinstance(klines, list)
        assert len(klines) >= 0

        # Test time range with no data (future date range)
        future_start = datetime(2025, 1, 1, tzinfo=UTC)
        future_end = datetime(2025, 1, 2, tzinfo=UTC)

        trades = await provider.fetch_historical_trades(symbol, future_start, future_end)
        assert trades == []

        klines = await provider.fetch_historical_klines(symbol, KlineInterval.MINUTE_1, future_start, future_end)
        assert klines == []

    @pytest.mark.asyncio
    async def test_get_symbol_info_nonexistent_symbol(self, provider: MockDataProvider) -> None:
        """Test error handling for non-existent symbols in get_symbol_info.

        Description of what the test covers:
        This test verifies that the get_symbol_info method correctly handles
        requests for symbols that don't exist in the provider's symbol list,
        raising appropriate exceptions with clear error messages.

        Expected Result:
        - Valid symbols should return proper symbol info
        - Invalid symbols should raise ValueError with descriptive message
        - Error handling should be consistent
        """
        await provider.connect()

        # Test valid symbol - should work
        valid_symbol = "BTCUSDT"
        symbol_info = await provider.get_symbol_info(valid_symbol)
        assert isinstance(symbol_info, dict)
        assert symbol_info["symbol"] == valid_symbol
        assert "status" in symbol_info
        assert "base_asset" in symbol_info
        assert "quote_asset" in symbol_info

        # Test non-existent symbol - should raise ValueError
        invalid_symbol = "NONEXISTENT"
        with pytest.raises(ValueError, match=f"Symbol '{invalid_symbol}' not found"):
            await provider.get_symbol_info(invalid_symbol)

        # Test another non-existent symbol with different format
        invalid_symbol2 = "FAKECOIN"
        with pytest.raises(ValueError, match=f"Symbol '{invalid_symbol2}' not found"):
            await provider.get_symbol_info(invalid_symbol2)

        # Test empty symbol
        with pytest.raises(ValueError, match="Symbol '' not found"):
            await provider.get_symbol_info("")

    @pytest.mark.asyncio
    async def test_stream_exception_handling(self, provider: MockDataProvider) -> None:
        """Test exception handling for streaming methods.

        Description of what the test covers:
        This test verifies that streaming methods properly handle error conditions
        such as streaming non-existent symbols and connection issues, raising
        appropriate exceptions before or during stream generation.

        Expected Result:
        - Streaming non-existent symbols should raise ValueError
        - Connection state should be properly validated
        - Error messages should be clear and helpful
        """
        await provider.connect()

        # Test streaming trades for non-existent symbol
        invalid_symbol = "NONEXISTENT"
        with pytest.raises(ValueError, match=f"Symbol '{invalid_symbol}' not found"):
            async for _ in provider.stream_trades(invalid_symbol):
                break  # Should not reach here due to exception

        # Test streaming klines for non-existent symbol
        with pytest.raises(ValueError, match=f"Symbol '{invalid_symbol}' not found"):
            async for _ in provider.stream_klines(invalid_symbol, KlineInterval.MINUTE_1):
                break  # Should not reach here due to exception

        # Test streaming when not connected
        await provider.disconnect()

        valid_symbol = "BTCUSDT"
        with pytest.raises(RuntimeError, match="Not connected"):
            async for _ in provider.stream_trades(valid_symbol):
                break  # Should not reach here due to exception

        with pytest.raises(RuntimeError, match="Not connected"):
            async for _ in provider.stream_klines(valid_symbol, KlineInterval.MINUTE_1):
                break  # Should not reach here due to exception

        # Test streaming when closed
        await provider.close()

        with pytest.raises(RuntimeError, match="Already closed"):
            async for _ in provider.stream_trades(valid_symbol):
                break  # Should not reach here due to exception

        with pytest.raises(RuntimeError, match="Already closed"):
            async for _ in provider.stream_klines(valid_symbol, KlineInterval.MINUTE_1):
                break  # Should not reach here due to exception

    @pytest.mark.asyncio
    async def test_connection_management_idempotency(self, provider: MockDataProvider) -> None:
        """Test idempotent behavior of connection management methods.

        Description of what the test covers:
        This test verifies that disconnect and close operations are idempotent,
        meaning they can be called multiple times without causing errors or
        side effects, ensuring robust resource management.

        Expected Result:
        - Multiple calls to disconnect should not raise errors
        - Multiple calls to close should not raise errors
        - State should remain consistent after multiple operations
        - Operations should be safe to call in any order
        """
        await provider.connect()
        assert provider.is_connected

        # Test multiple disconnect calls (should be idempotent)
        await provider.disconnect()
        assert not provider.is_connected
        assert not provider.is_closed  # type: ignore[unreachable]

        # Second disconnect should not raise error
        await provider.disconnect()
        assert not provider.is_connected
        assert not provider.is_closed

        # Third disconnect should not raise error
        await provider.disconnect()
        assert not provider.is_connected
        assert not provider.is_closed

        # Test multiple close calls (should be idempotent)
        await provider.close()
        assert not provider.is_connected
        assert provider.is_closed

        # Second close should not raise error
        await provider.close()
        assert not provider.is_connected
        assert provider.is_closed

        # Third close should not raise error
        await provider.close()
        assert not provider.is_connected
        assert provider.is_closed

        # Test disconnect after close (should be safe)
        await provider.disconnect()
        assert not provider.is_connected
        assert provider.is_closed

        # Test another provider instance for different scenario
        provider2 = MockDataProvider("test_provider_2")

        # Test close without connect (should be idempotent)
        await provider2.close()
        assert not provider2.is_connected
        assert provider2.is_closed

        # Test multiple close calls on never-connected provider
        await provider2.close()
        await provider2.close()
        assert not provider2.is_connected
        assert provider2.is_closed
