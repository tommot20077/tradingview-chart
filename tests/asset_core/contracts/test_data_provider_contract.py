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

        Resets the `is_connected` flag.
        """
        if self._is_connected:
            self._is_connected = False

    async def stream_trades(self, symbol: str, *, _start_from: datetime | None = None) -> AsyncIterator[Trade]:
        """Streams mock real-time trades for a given symbol.

        Args:
            symbol (str): The trading symbol for which to stream trades.
            _start_from (datetime | None): Optional datetime to start streaming from.
                                         (Ignored in this mock implementation).

        Yields:
            Trade: A mock `Trade` object.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
        """
        self._check_connected()
        self._check_not_closed()

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
        self, symbol: str, interval: KlineInterval, *, _start_from: datetime | None = None
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
        """
        self._check_connected()
        self._check_not_closed()

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
        """
        self._check_connected()
        self._check_not_closed()

        # Generate mock historical trades
        trades = []
        base_time = start_time
        count = min(limit or 100, 100)  # Cap at 100 for testing

        for i in range(count):
            trade = Trade(
                symbol=symbol,
                trade_id=f"hist_trade_{i}",
                price=49000.0 + i * 5,
                quantity=0.5 + i * 0.05,
                timestamp=base_time.replace(second=i % 60, microsecond=i * 1000),
                side="buy" if i % 2 == 0 else "sell",
                is_maker=i % 4 == 0,
            )
            trades.append(trade)

            # Respect end_time if provided
            if end_time and trade.timestamp >= end_time:
                break

        return trades

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
        """
        self._check_connected()
        self._check_not_closed()

        # Generate mock historical klines
        klines = []
        base_time = start_time
        count = min(limit or 50, 50)  # Cap at 50 for testing

        for i in range(count):
            open_time = base_time.replace(hour=i % 24, minute=0, second=0, microsecond=0)
            close_time = open_time.replace(minute=59, second=59, microsecond=999999)

            # Respect end_time if provided
            if end_time and open_time >= end_time:
                break

            kline = Kline(
                symbol=symbol,
                interval=interval,
                open_time=open_time,
                close_time=close_time,
                open_price=48000.0 + i * 50,
                high_price=48200.0 + i * 50,
                low_price=47800.0 + i * 50,
                close_price=48100.0 + i * 50,
                volume=200.0 + i * 5,
                quote_volume=9620000.0 + i * 10000,
                trades_count=2000 + i * 50,
            )
            klines.append(kline)

        return klines

    async def get_exchange_info(self) -> dict[str, Any]:
        """Retrieves mock exchange information.

        Returns:
            dict[str, Any]: A dictionary containing mock exchange details.

        Raises:
            RuntimeError: If the provider is not connected or is closed.
        """
        self._check_connected()
        self._check_not_closed()

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
        """
        self._check_connected()
        self._check_not_closed()

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
        self._check_connected()
        self._check_not_closed()

        # Simulate network ping
        await asyncio.sleep(0.001)
        return self._ping_latency

    async def close(self) -> None:
        """Closes the provider and cleans up resources.

        This method disconnects the provider and sets its internal state to closed.
        """
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

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Asynchronous context manager exit point.

        Automatically closes the provider upon exiting the `async with` block.

        Args:
            exc_type (Any): The type of the exception raised, if any.
            exc_val (Any): The exception instance raised, if any.
            exc_tb (Any): The traceback object, if an exception was raised.

        Returns:
            bool: False to propagate any exceptions that occurred within the block.
        """
        await self.close()
        return False


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
            AbstractDataProvider()  # Should raise TypeError due to abstract methods

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
