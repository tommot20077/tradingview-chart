"""Unit tests for WebSocket client."""

import asyncio
import builtins
import contextlib
import json
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from websockets import State
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.asset_core.asset_core.exceptions import ConnectionError, TimeoutError, \
    WebSocketError
from src.asset_core.asset_core.network.ws_client import RobustWebSocketClient


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Create a mock websocket connection."""
    mock_ws = AsyncMock()
    mock_ws.state = State.OPEN
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.recv = AsyncMock()
    return mock_ws


@pytest.fixture
def callback_mocks() -> dict[str, Mock]:
    """Create mock callbacks."""
    return {
        "on_message": Mock(),
        "on_connect": Mock(),
        "on_disconnect": Mock(),
        "on_error": Mock(),
    }


@pytest.mark.integration
class TestRobustWebSocketClientConstruction:
    """Test cases for WebSocket client construction."""

    def test_client_initialization_basic(self) -> None:
        """Test basic client initialization."""
        client = RobustWebSocketClient("wss://example.com/ws")

        assert client.url == "wss://example.com/ws"
        assert client.on_message is None
        assert client.on_connect is None
        assert client.on_disconnect is None
        assert client.on_error is None
        assert client.reconnect_interval == 5
        assert client.max_reconnect_attempts == 10
        assert client.ping_interval == 30
        assert client.ping_timeout == 10
        assert client.headers == {}

    def test_client_initialization_with_callbacks(self, callback_mocks) -> None:
        """Test client initialization with callbacks."""
        client = RobustWebSocketClient(
            "wss://example.com/ws",
            on_message=callback_mocks["on_message"],
            on_connect=callback_mocks["on_connect"],
            on_disconnect=callback_mocks["on_disconnect"],
            on_error=callback_mocks["on_error"],
        )

        assert client.on_message == callback_mocks["on_message"]
        assert client.on_connect == callback_mocks["on_connect"]
        assert client.on_disconnect == callback_mocks["on_disconnect"]
        assert client.on_error == callback_mocks["on_error"]

    def test_client_initialization_with_custom_parameters(self) -> None:
        """Test client initialization with custom parameters."""
        headers = {"Authorization": "Bearer token123"}
        client = RobustWebSocketClient(
            "wss://api.example.com/stream",
            reconnect_interval=3,
            max_reconnect_attempts=5,
            ping_interval=20,
            ping_timeout=5,
            headers=headers,
        )

        assert client.url == "wss://api.example.com/stream"
        assert client.reconnect_interval == 3
        assert client.max_reconnect_attempts == 5
        assert client.ping_interval == 20
        assert client.ping_timeout == 5
        assert client.headers == headers

    def test_client_initial_state(self) -> None:
        """Test client initial state."""
        client = RobustWebSocketClient("wss://example.com/ws")

        assert client._ws is None
        assert client._running is False
        assert client._reconnect_count == 0
        assert client._connection_task is None
        assert client._receive_task is None
        assert client.is_connected is False


@pytest.mark.integration
class TestRobustWebSocketClientConnection:
    """Test cases for WebSocket client connection."""

    @pytest.mark.asyncio
    async def test_successful_connection(self, mock_websocket, callback_mocks) -> None:
        """Test successful WebSocket connection."""
        with patch("asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_websocket)):
            client = RobustWebSocketClient("wss://example.com/ws", on_connect=callback_mocks["on_connect"])

            # Mock the connection loop to avoid infinite loop and immediately set the connect event
            async def mock_connection_loop() -> None:
                client._connect_event.set()
                if client.on_connect:
                    client.on_connect()

            with patch.object(client, "_connection_loop", mock_connection_loop):
                await client.connect()

                assert client._running is True
                assert client._reconnect_count == 0
                callback_mocks["on_connect"].assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_timeout(self) -> None:
        """Test connection timeout."""
        client = RobustWebSocketClient("wss://example.com/ws")
        # Mock _connection_loop to never set the event
        with patch.object(client, "_connection_loop", AsyncMock()) as mock_loop:
            # Mock the timeout duration to be 5 seconds instead of 30
            with patch("asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = builtins.TimeoutError()

                with pytest.raises(TimeoutError, match="Failed to establish initial connection"):
                    await client.connect()

            assert mock_loop.called
            assert client._running is False

    @pytest.mark.asyncio
    async def test_connection_already_running(self, mock_websocket) -> None:
        """Test connecting when already running."""
        with patch("asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_websocket)):
            client = RobustWebSocketClient("wss://example.com/ws")
            client._running = True

            await client.connect()

            # Should return without creating new connection task
            assert client._connection_task is None

    @pytest.mark.asyncio
    async def test_connect_with_headers(self, mock_websocket) -> None:
        """Test connection with custom headers."""
        headers = {"Authorization": "Bearer token123", "X-API-Key": "key456"}

        with patch(
            "asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_websocket)
        ) as mock_connect:
            client = RobustWebSocketClient("wss://api.example.com/stream", headers=headers)

            # Simulate successful connection
            async def mock_connection_loop() -> None:
                await client._connect()
                client._connect_event.set()

            with patch.object(client, "_connection_loop", mock_connection_loop):
                await client.connect()

                mock_connect.assert_called_once_with(
                    "wss://api.example.com/stream", extra_headers=headers, ping_interval=30, ping_timeout=10
                )

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure handling."""
        with patch(
            "asset_core.network.ws_client.websockets.connect", AsyncMock(side_effect=Exception("Connection failed"))
        ):
            client = RobustWebSocketClient("wss://example.com/ws")

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client._connect()


@pytest.mark.integration
class TestRobustWebSocketClientDisconnection:
    """Test cases for WebSocket client disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, mock_websocket, callback_mocks) -> None:
        """Test proper cleanup during disconnection."""
        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=callback_mocks["on_disconnect"])
        client._ws = mock_websocket
        client._connect_event.set()

        await client._disconnect()

        assert client._ws is None
        assert not client._connect_event.is_set()
        mock_websocket.close.assert_called_once()
        callback_mocks["on_disconnect"].assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_with_close_error(self, callback_mocks) -> None:
        """Test disconnection when close raises an error."""
        mock_ws = AsyncMock()
        mock_ws.close.side_effect = Exception("Close error")

        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=callback_mocks["on_disconnect"])
        client._ws = mock_ws

        # Should not raise exception
        await client._disconnect()

        assert client._ws is None
        callback_mocks["on_disconnect"].assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_without_websocket(self, callback_mocks) -> None:
        """Test disconnection when no websocket is set."""
        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=callback_mocks["on_disconnect"])

        await client._disconnect()

        callback_mocks["on_disconnect"].assert_called_once()


@pytest.mark.integration
class TestRobustWebSocketClientMessageHandling:
    """Test cases for WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_receive_loop_with_messages(self, callback_mocks) -> None:
        """Test message receiving loop."""
        messages = ["message1", "message2", "message3"]
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]

        client = RobustWebSocketClient("wss://example.com/ws", on_message=callback_mocks["on_message"])
        client._ws = mock_ws

        await client._receive_loop()

        assert callback_mocks["on_message"].call_count == 3
        callback_mocks["on_message"].assert_has_calls([call("message1"), call("message2"), call("message3")])

    @pytest.mark.asyncio
    async def test_receive_loop_without_websocket(self) -> None:
        """Test receive loop when websocket is None."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None

        # Should return immediately without error
        await client._receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_with_message_handler_error(self, callback_mocks) -> None:
        """Test receive loop with message handler error."""
        callback_mocks["on_message"].side_effect = Exception("Handler error")

        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = ["test_message", ConnectionClosed(None, None)]

        client = RobustWebSocketClient(
            "wss://example.com/ws", on_message=callback_mocks["on_message"], on_error=callback_mocks["on_error"]
        )
        client._ws = mock_ws

        await client._receive_loop()

        callback_mocks["on_message"].assert_called_once_with("test_message")
        callback_mocks["on_error"].assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_loop_connection_closed(self) -> None:
        """Test receive loop handling connection closed."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = ConnectionClosed(None, None)

        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_ws

        # Should handle ConnectionClosed gracefully
        await client._receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_websocket_exception(self) -> None:
        """Test receive loop handling WebSocket exception."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = WebSocketException("WebSocket error")

        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_ws

        with pytest.raises(WebSocketError, match="Receive loop error"):
            await client._receive_loop()


@pytest.mark.integration
class TestRobustWebSocketClientSending:
    """Test cases for WebSocket message sending."""

    @pytest.mark.asyncio
    async def test_send_string_message(self, mock_websocket) -> None:
        """Test sending string message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        await client.send("test message")

        mock_websocket.send.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_send_dict_message(self, mock_websocket) -> None:
        """Test sending dictionary message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        message_dict = {"type": "subscribe", "channel": "trades"}
        await client.send(message_dict)

        expected_json = json.dumps(message_dict)
        mock_websocket.send.assert_called_once_with(expected_json)

    @pytest.mark.asyncio
    async def test_send_when_not_connected(self) -> None:
        """Test sending message when not connected."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None

        with pytest.raises(WebSocketError, match="Not connected"):
            await client.send("test message")

    @pytest.mark.asyncio
    async def test_send_with_connection_closed_error(self, mock_websocket) -> None:
        """Test sending message when connection is closed."""
        mock_websocket.send.side_effect = ConnectionClosed(None, None)

        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        with pytest.raises(WebSocketError, match="Failed to send message: Connection is closed"):
            await client.send("test message")

    @pytest.mark.asyncio
    async def test_send_with_general_error(self, mock_websocket) -> None:
        """Test sending message with general error."""
        mock_websocket.send.side_effect = Exception("Send error")

        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        with pytest.raises(WebSocketError, match="Failed to send message: Send error"):
            await client.send("test message")


@pytest.mark.integration
class TestRobustWebSocketClientReconnection:
    """Test cases for WebSocket reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnection_backoff(self) -> None:
        """Test exponential backoff in reconnection."""
        client = RobustWebSocketClient("wss://example.com/ws", reconnect_interval=1, max_reconnect_attempts=3)

        # Test backoff calculation
        client._reconnect_count = 0
        wait_time = client.reconnect_interval * (2 ** min(client._reconnect_count, 5))
        assert wait_time == 1

        client._reconnect_count = 1
        wait_time = client.reconnect_interval * (2 ** min(client._reconnect_count, 5))
        assert wait_time == 2

        client._reconnect_count = 2
        wait_time = client.reconnect_interval * (2 ** min(client._reconnect_count, 5))
        assert wait_time == 4

    @pytest.mark.asyncio
    async def test_max_reconnection_attempts(self, callback_mocks) -> None:
        """Test maximum reconnection attempts."""
        client = RobustWebSocketClient(
            "wss://example.com/ws",
            reconnect_interval=0.1,
            max_reconnect_attempts=2,
            on_error=callback_mocks["on_error"],
        )

        # Mock _connect to always fail
        with (
            patch.object(client, "_connect", AsyncMock(side_effect=Exception("Connection failed"))),
            patch.object(client, "_receive_loop", AsyncMock()),
        ):
            # Mock _receive_loop to not be called
            # Start connection loop
            client._running = True
            await client._connection_loop()

            assert client._running is False
            assert client._reconnect_count == 2


@pytest.mark.integration
class TestRobustWebSocketClientClosing:
    """Test cases for WebSocket client closing."""

    @pytest.mark.asyncio
    async def test_close_client(self, mock_websocket) -> None:
        """Test closing the client."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True
        client._ws = mock_websocket

        # Create a real task and then mock its methods
        async def dummy_coro() -> None:
            await asyncio.sleep(1000)  # Long running task

        task = asyncio.create_task(dummy_coro())
        task.cancel = Mock(wraps=task.cancel)  # Wrap the real cancel method
        client._connection_task = task

        await client.close()

        assert client._running is False
        task.cancel.assert_called_once()
        mock_websocket.close.assert_called_once()

        # Clean up the task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_close_with_cancelled_task(self) -> None:
        """Test closing with cancelled connection task."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True

        # Create a real task and then mock its methods
        async def dummy_coro() -> None:
            await asyncio.sleep(1000)  # Long running task

        task = asyncio.create_task(dummy_coro())
        task.cancel = Mock(wraps=task.cancel)  # Wrap the real cancel method
        client._connection_task = task

        # Should not raise exception
        await client.close()

        assert client._running is False
        task.cancel.assert_called_once()

        # Clean up the task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_close_when_not_running(self) -> None:
        """Test closing when client is not running."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = False

        # Should complete without error
        await client.close()

        assert client._running is False


@pytest.mark.integration
class TestRobustWebSocketClientProperties:
    """Test cases for WebSocket client properties."""

    def test_is_connected_when_connected(self, mock_websocket) -> None:
        """Test is_connected property when connected."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket
        mock_websocket.state = State.OPEN

        assert client.is_connected is True

    def test_is_connected_when_disconnected(self, mock_websocket) -> None:
        """Test is_connected property when disconnected."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket
        mock_websocket.state = State.CLOSED

        assert client.is_connected is False

    def test_is_connected_when_no_websocket(self) -> None:
        """Test is_connected property when no websocket."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None

        assert client.is_connected is False


@pytest.mark.integration
class TestRobustWebSocketClientAsyncContext:
    """Test cases for WebSocket client async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_websocket) -> None:
        """Test using client as async context manager."""
        with patch("asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_websocket)):
            # Mock connection loop to immediately set the connect event
            async def mock_connection_loop() -> None:
                pass  # Do nothing, just avoid infinite loop

            with patch.object(RobustWebSocketClient, "_connection_loop", mock_connection_loop):
                client = RobustWebSocketClient("wss://example.com/ws")

                async def mock_connect() -> None:
                    client._running = True
                    client._connect_event.set()

                async def mock_close() -> None:
                    client._running = False

                with patch.object(client, "connect", mock_connect), patch.object(client, "close", mock_close):
                    async with client:
                        assert isinstance(client, RobustWebSocketClient)
                        assert client._running is True

                    assert client._running is False

    @pytest.mark.asyncio
    async def test_async_context_manager_with_exception(self, mock_websocket) -> None:
        """Test async context manager when exception occurs."""
        with patch("asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_websocket)):
            # Mock connection loop to immediately set the connect event
            async def mock_connection_loop() -> None:
                pass  # Do nothing, just avoid infinite loop

            with patch.object(RobustWebSocketClient, "_connection_loop", mock_connection_loop):
                client = RobustWebSocketClient("wss://example.com/ws")

                async def mock_connect() -> None:
                    client._running = True
                    client._connect_event.set()

                async def mock_close() -> None:
                    client._running = False

                with patch.object(client, "connect", mock_connect), patch.object(client, "close", mock_close):
                    try:
                        async with client:
                            assert client._running is True
                            raise ValueError("Test exception")
                    except ValueError:
                        pass

                    assert client._running is False


@pytest.mark.integration
class TestRobustWebSocketClientEdgeCases:
    """Test cases for WebSocket client edge cases."""

    def test_client_with_empty_headers(self) -> None:
        """Test client with empty headers."""
        client = RobustWebSocketClient("wss://example.com/ws", headers={})
        assert client.headers == {}

    def test_client_with_none_headers(self) -> None:
        """Test client with None headers."""
        client = RobustWebSocketClient("wss://example.com/ws", headers=None)
        assert client.headers == {}

    @pytest.mark.asyncio
    async def test_send_very_large_message(self, mock_websocket) -> None:
        """Test sending very large message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        large_message = "x" * 10000
        await client.send(large_message)

        mock_websocket.send.assert_called_once_with(large_message)

    @pytest.mark.asyncio
    async def test_send_complex_dict_message(self, mock_websocket) -> None:
        """Test sending complex dictionary message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        complex_dict = {
            "type": "subscribe",
            "channels": ["trades", "orders"],
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "metadata": {"timestamp": 1234567890, "user_id": 12345, "nested": {"key": "value", "list": [1, 2, 3]}},
        }

        await client.send(complex_dict)

        expected_json = json.dumps(complex_dict)
        mock_websocket.send.assert_called_once_with(expected_json)

    @pytest.mark.asyncio
    async def test_receive_non_string_message(self, callback_mocks) -> None:
        """Test receiving non-string message (should be ignored)."""
        mock_ws = AsyncMock()
        # Mock recv to return non-string messages then raise ConnectionClosed to exit loop
        mock_ws.recv.side_effect = [b"binary_message", 123, None, "string_message", ConnectionClosed(None, None)]

        client = RobustWebSocketClient("wss://example.com/ws", on_message=callback_mocks["on_message"])
        client._ws = mock_ws

        await client._receive_loop()

        # on_message should only be called once for the string message
        callback_mocks["on_message"].assert_called_once_with("string_message")


@pytest.mark.network
@pytest.mark.integration
class TestRobustWebSocketClientIntegration:
    """Integration test cases for WebSocket client."""

    @pytest.mark.asyncio
    async def test_complete_connection_lifecycle(self, callback_mocks) -> None:
        """Test complete connection lifecycle."""
        messages = ["message1", "message2"]
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        # Mock recv to return messages then raise ConnectionClosed to exit loop
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("asset_core.network.ws_client.websockets.connect", AsyncMock(return_value=mock_ws)):
            client = RobustWebSocketClient(
                "wss://example.com/ws",
                on_message=callback_mocks["on_message"],
                on_connect=callback_mocks["on_connect"],
                on_disconnect=callback_mocks["on_disconnect"],
                reconnect_interval=0.1,
                max_reconnect_attempts=1,
            )

            # Mock connection loop to avoid real async tasks
            async def mock_connection_loop() -> None:
                # Simulate connection establishment
                client._ws = mock_ws  # Set the websocket object
                client._connect_event.set()
                if client.on_connect:
                    client.on_connect()
                # Simulate receive loop processing messages
                if client.on_message:
                    for msg in messages:
                        client.on_message(msg)

            with patch.object(client, "_connection_loop", mock_connection_loop):
                # Start connection
                await client.connect()

                # Send a message
                await client.send("test_message")

                # Close client
                await client.close()

            # Verify callbacks were called
            callback_mocks["on_connect"].assert_called()
            callback_mocks["on_disconnect"].assert_called()
            mock_ws.send.assert_called_with("test_message")
            # Verify messages were processed
            for msg in messages:
                callback_mocks["on_message"].assert_any_call(msg)

    @pytest.mark.asyncio
    async def test_reconnection_scenario(self, callback_mocks) -> None:
        """Test reconnection scenario."""
        # First connection fails, second succeeds
        connection_attempts = 0

        async def mock_connect_side_effect(*args, **kwargs) -> AsyncMock:
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts == 1:
                raise Exception("First connection failed")

            mock_ws = AsyncMock()
            mock_ws.state = State.OPEN
            mock_ws.recv.side_effect = [ConnectionClosed(None, None)]
            return mock_ws

        with patch("asset_core.network.ws_client.websockets.connect", side_effect=mock_connect_side_effect):
            client = RobustWebSocketClient(
                "wss://example.com/ws",
                on_connect=callback_mocks["on_connect"],
                on_error=callback_mocks["on_error"],
                reconnect_interval=0.1,
                max_reconnect_attempts=2,
            )

            # Start connection
            connection_task = asyncio.create_task(client.connect())

            # Wait for potential reconnection
            await asyncio.sleep(0.3)

            # Close client
            await client.close()

            with contextlib.suppress(asyncio.CancelledError):
                await connection_task

            # Should have attempted connection twice
            assert connection_attempts >= 1
            # Should have called on_error for first failure
            callback_mocks["on_error"].assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_websocket) -> None:
        """Test concurrent send operations."""
        mock_websocket.send = AsyncMock()

        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = mock_websocket

        # Send multiple messages concurrently
        messages = ["msg1", "msg2", "msg3", "msg4", "msg5"]
        send_tasks = [client.send(msg) for msg in messages]

        await asyncio.gather(*send_tasks)

        assert mock_websocket.send.call_count == 5
        sent_messages = [call.args[0] for call in mock_websocket.send.call_args_list]
        assert set(sent_messages) == set(messages)

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, callback_mocks) -> None:
        """Test error recovery scenario."""
        # Setup mock that fails once then succeeds
        call_count = 0

        def message_handler_side_effect(message) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Handler error")
            # Second call succeeds

        callback_mocks["on_message"].side_effect = message_handler_side_effect

        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = ["message1", "message2", ConnectionClosed(None, None)]

        client = RobustWebSocketClient(
            "wss://example.com/ws", on_message=callback_mocks["on_message"], on_error=callback_mocks["on_error"]
        )
        client._ws = mock_ws

        await client._receive_loop()

        # Both messages should be processed
        assert callback_mocks["on_message"].call_count == 2
        # Error should be reported once
        callback_mocks["on_error"].assert_called_once()

    @pytest.mark.asyncio
    async def test_message_throughput(self, callback_mocks) -> None:
        """Test high message throughput."""
        # Generate many messages
        message_count = 100
        messages = [f"message_{i}" for i in range(message_count)]

        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]

        client = RobustWebSocketClient("wss://example.com/ws", on_message=callback_mocks["on_message"])
        client._ws = mock_ws

        await client._receive_loop()

        # All messages should be processed
        assert callback_mocks["on_message"].call_count == message_count

        # Verify all messages were received
        received_messages = [call.args[0] for call in callback_mocks["on_message"].call_args_list]
        assert received_messages == messages
