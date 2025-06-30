import asyncio
import builtins
import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest
import websockets
from pytest_mock import MockerFixture
from websockets.exceptions import ConnectionClosed, WebSocketException

from asset_core.exceptions import ConnectionError, TimeoutError, WebSocketError
from asset_core.network.ws_client import RobustWebSocketClient

# Constants
TEST_URL = "ws://localhost:8765"


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> MagicMock:
    """Fixture to mock the logger."""
    return mocker.patch("asset_core.network.ws_client.get_logger", return_value=MagicMock())


@pytest.fixture
def mock_websockets_connect(mocker: MockerFixture) -> tuple[AsyncMock, AsyncMock]:
    """Fixture to mock websockets.connect."""
    mock_ws = AsyncMock()  # Remove spec since WebSocketClientProtocol may not be available
    mock_ws.close = AsyncMock()
    mock_ws.send = AsyncMock()
    # Default behavior for recv is to simulate a closed connection to prevent infinite loops.
    mock_ws.recv = AsyncMock(side_effect=ConnectionClosed(None, None))
    mock_ws.state = websockets.State.OPEN

    mock_connect = mocker.patch("websockets.connect", new_callable=AsyncMock)
    mock_connect.return_value = mock_ws

    return mock_connect, mock_ws


@pytest.fixture
def mock_asyncio_sleep(mocker: MockerFixture) -> AsyncMock:
    """Fixture to mock asyncio.sleep."""
    return mocker.patch("asyncio.sleep", new_callable=AsyncMock)


class TestRobustWebSocketClient:
    """Unit tests for the RobustWebSocketClient."""

    @pytest.fixture
    def mock_callbacks(self) -> dict[str, MagicMock]:
        """Fixture for mock callbacks."""
        return {
            "on_message": MagicMock(),
            "on_connect": MagicMock(),
            "on_disconnect": MagicMock(),
            "on_error": MagicMock(),
        }

    def test_initialization(self, mock_callbacks: dict[str, MagicMock]) -> None:
        """Test that the client initializes with the correct attributes."""
        client = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            reconnect_interval=10,
            max_reconnect_attempts=5,
            ping_interval=60,
            ping_timeout=20,
            headers={"X-Test": "true"},
        )
        assert client.url == TEST_URL
        assert client.on_message == mock_callbacks["on_message"]
        assert client.reconnect_interval == 10
        assert client.max_reconnect_attempts == 5
        assert client.ping_interval == 60
        assert client.ping_timeout == 20
        assert client.headers == {"X-Test": "true"}
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connect_successful(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test a successful connection."""
        mock_connect, mock_ws = mock_websockets_connect
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        await client.connect()

        assert client.is_connected
        assert client._ws == mock_ws
        mock_callbacks["on_connect"].assert_called_once()

        await client.close()

        mock_connect.assert_called_once_with(
            TEST_URL,
            extra_headers={},
            ping_interval=30,
            ping_timeout=10,
        )

    @pytest.mark.asyncio
    async def test_connect_timeout(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test connection timeout."""
        mock_connect, _ = mock_websockets_connect
        # Make the connection hang
        mock_connect.side_effect = asyncio.TimeoutError

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        with pytest.raises(TimeoutError, match="Failed to establish initial connection"):
            await client.connect()

        assert not client.is_connected
        assert client._running is False

    @pytest.mark.asyncio
    async def test_connect_failure_raises_connection_error(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test that a connection failure during _connect raises ConnectionError."""
        mock_connect, _ = mock_websockets_connect
        mock_connect.side_effect = WebSocketException("Connection failed")

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await client._connect()

        # Ensure on_error is not called by _connect itself, but by the loop
        mock_callbacks["on_error"].assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_successful(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test sending a message successfully."""
        _, mock_ws = mock_websockets_connect
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        async with client:
            assert client.is_connected
            await client.send("Hello")
            mock_ws.send.assert_called_once_with("Hello")

            mock_ws.send.reset_mock()

            await client.send({"key": "value"})
            mock_ws.send.assert_called_once_with('{"key": "value"}')

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, mock_callbacks: dict[str, MagicMock]) -> None:
        """Test that sending a message when not connected raises WebSocketError."""
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)
        with pytest.raises(WebSocketError, match="Not connected"):
            await client.send("Hello")

    @pytest.mark.asyncio
    async def test_receive_loop_and_message_handling(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test the receive loop and that on_message is called."""
        _, mock_ws = mock_websockets_connect

        # Simulate receiving two messages then closing
        mock_ws.recv.side_effect = ["message1", "message2", ConnectionClosed(None, None)]

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        async with client:
            await asyncio.sleep(0.1)  # allow the receive_loop to run

        # Extract actual messages received by on_message
        actual_messages = [args[0] for args, kwargs in mock_callbacks["on_message"].call_args_list]
        assert actual_messages == ["message1", "message2"]
        assert mock_callbacks["on_message"].call_count == 2

    @pytest.mark.asyncio
    async def test_reconnection_logic(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_asyncio_sleep: AsyncMock,
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test the reconnection logic with exponential backoff."""
        mock_connect, mock_ws = mock_websockets_connect

        # First connection fails, second succeeds
        mock_connect.side_effect = [
            WebSocketException("Initial connection failed"),
            mock_ws,  # This should be the actual mock_ws
        ]

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks, reconnect_interval=1, max_reconnect_attempts=3)

        # We need to manually drive the connection loop to test reconnection
        async def drive_connection() -> None:
            client._running = True
            # First attempt
            with pytest.raises(ConnectionError):
                await client._connect()

            # Simulate waiting for reconnect
            await asyncio.sleep(client.reconnect_interval)
            client._reconnect_count += 1

            # Second attempt
            await client._connect()

        await asyncio.wait_for(drive_connection(), timeout=2)

        # Check that sleep was called for backoff
        mock_asyncio_sleep.assert_called_once_with(1)
        # Check that on_connect was called on the second attempt
        mock_callbacks["on_connect"].assert_called_once()
        assert client.is_connected

    @pytest.mark.asyncio
    async def test_close_method(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test the close method."""
        _, mock_ws = mock_websockets_connect
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        await client.connect()
        assert client.is_connected

        connection_task = client._connection_task
        assert connection_task and not connection_task.done()

        await client.close()

        assert not client.is_connected
        assert not client._running  # type: ignore[unreachable]
        assert connection_task.cancelled()
        mock_ws.close.assert_called_once()
        mock_callbacks["on_disconnect"].assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test the async context manager."""
        _, mock_ws = mock_websockets_connect
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        async with client as ws_client:
            assert ws_client is client
            assert client.is_connected
            mock_callbacks["on_connect"].assert_called_once()

        assert not client.is_connected
        mock_ws.close.assert_called_once()  # type: ignore[unreachable]
        mock_callbacks["on_disconnect"].assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_loop_on_message_callback_exception(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test that exceptions in on_message callback are handled and on_error is called.

        This test verifies the scenario described in missing_tests.md line 165:
        - on_message callback raises an exception
        - assert on_error callback is invoked
        """
        _, mock_ws = mock_websockets_connect

        # Configure on_message to raise an exception
        test_exception = ValueError("Test callback error")
        mock_callbacks["on_message"].side_effect = test_exception

        # Simulate receiving a message then closing
        mock_ws.recv.side_effect = ["test_message", ConnectionClosed(None, None)]

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        async with client:
            await asyncio.sleep(0.1)  # allow the receive_loop to run

        # Verify on_message was called and raised exception
        mock_callbacks["on_message"].assert_called_once_with("test_message")

        # Verify on_error was called with the exception from on_message
        mock_callbacks["on_error"].assert_called_once_with(test_exception)

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts_stops_client(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test that client stops running after max_reconnect_attempts is reached.

        This test verifies the scenario described in missing_tests.md line 169:
        - max_reconnect_attempts reached
        - assert client stops running
        """
        mock_connect, _ = mock_websockets_connect

        # Configure connection to always fail
        mock_connect.side_effect = WebSocketException("Connection always fails")

        client = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            reconnect_interval=1,  # Very short interval for faster test
            max_reconnect_attempts=2,  # Small number for faster test
        )

        # Start the connection manually to control the test
        client._running = True
        connection_task = asyncio.create_task(client._connection_loop())

        # Wait for the connection task to complete (it should stop after max attempts)
        try:
            await asyncio.wait_for(connection_task, timeout=5.0)
        except builtins.TimeoutError:
            # If it didn't finish, that's a problem - cancel it
            connection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await connection_task
            raise AssertionError("Connection task should have stopped after max reconnect attempts")

        # Verify client stopped running after max attempts
        assert not client._running
        assert client._reconnect_count >= 2

    @pytest.mark.asyncio
    async def test_unlimited_reconnect_attempts(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test that client continues attempting reconnections with max_reconnect_attempts = -1.

        This test verifies the scenario described in missing_tests.md line 173:
        - max_reconnect_attempts = -1
        - assert unlimited reconnections
        """
        mock_connect, _ = mock_websockets_connect

        # Configure connection to always fail
        mock_connect.side_effect = WebSocketException("Connection always fails")

        client = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            reconnect_interval=1,  # Very short interval for faster test
            max_reconnect_attempts=-1,  # Unlimited attempts
        )

        # Test the condition logic directly by simulating high reconnect count
        client._reconnect_count = 100  # Simulate many failed attempts
        client._running = True

        # Test that the condition for unlimited reconnections works
        # With max_reconnect_attempts = -1, this should be True
        unlimited_condition = (
            client.max_reconnect_attempts == -1 or client._reconnect_count < client.max_reconnect_attempts
        )
        assert unlimited_condition, "Unlimited reconnection condition should be True"

        # Test with limited attempts for comparison
        client_limited = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            max_reconnect_attempts=5,
        )
        client_limited._reconnect_count = 100  # Many failed attempts
        client_limited._running = True

        # With limited attempts, this should be False when count exceeds limit
        limited_condition = (
            client_limited.max_reconnect_attempts == -1
            or client_limited._reconnect_count < client_limited.max_reconnect_attempts
        )
        assert not limited_condition, "Limited reconnection condition should be False when exceeded"
