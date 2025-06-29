"""Simplified unit tests for WebSocket client."""

import asyncio
import contextlib
import json
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from websockets import State
from websockets.exceptions import ConnectionClosed, WebSocketException

from asset_core.exceptions import ConnectionError, WebSocketError
from asset_core.network.ws_client import RobustWebSocketClient


@pytest.mark.integration
class TestRobustWebSocketClientBasics:
    """Test cases for basic WebSocket client functionality."""

    def test_client_initialization(self) -> None:
        """Test client initialization."""
        client = RobustWebSocketClient("wss://example.com/ws")

        assert client.url == "wss://example.com/ws"
        assert client.reconnect_interval == 5
        assert client.max_reconnect_attempts == 10
        assert client.ping_interval == 30
        assert client.ping_timeout == 10
        assert client.headers == {}
        assert client._ws is None
        assert client._running is False
        assert client.is_connected is False

    def test_client_with_callbacks(self) -> None:
        """Test client with callback functions."""
        on_message = Mock()
        on_connect = Mock()
        on_disconnect = Mock()
        on_error = Mock()

        client = RobustWebSocketClient(
            "wss://example.com/ws",
            on_message=on_message,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            on_error=on_error,
        )

        assert client.on_message == on_message
        assert client.on_connect == on_connect
        assert client.on_disconnect == on_disconnect
        assert client.on_error == on_error

    def test_client_with_custom_settings(self) -> None:
        """Test client with custom settings."""
        headers = {"Authorization": "Bearer token"}
        client = RobustWebSocketClient(
            "wss://api.example.com/stream",
            reconnect_interval=3,
            max_reconnect_attempts=5,
            ping_interval=20,
            ping_timeout=8,
            headers=headers,
        )

        assert client.reconnect_interval == 3
        assert client.max_reconnect_attempts == 5
        assert client.ping_interval == 20
        assert client.ping_timeout == 8
        assert client.headers == headers


@pytest.mark.integration
class TestWebSocketProperties:
    """Test WebSocket property methods."""

    def test_is_connected_with_none_websocket(self) -> None:
        """Test is_connected when websocket is None."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None
        assert client.is_connected is False

    def test_is_connected_with_open_websocket(self) -> None:
        """Test is_connected when websocket is open."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = Mock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws
        assert client.is_connected is True

    def test_is_connected_with_closed_websocket(self) -> None:
        """Test is_connected when websocket is closed."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = Mock()
        mock_ws.state = State.CLOSED
        client._ws = mock_ws
        assert client.is_connected is False


@pytest.mark.integration
class TestWebSocketSending:
    """Test WebSocket message sending."""

    @pytest.mark.asyncio
    async def test_send_string_message(self) -> None:
        """Test sending string message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        await client.send("test message")
        mock_ws.send.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_send_dict_message(self) -> None:
        """Test sending dictionary message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        message_dict = {"type": "subscribe", "channel": "trades"}
        await client.send(message_dict)

        expected_json = json.dumps(message_dict)
        mock_ws.send.assert_called_once_with(expected_json)

    @pytest.mark.asyncio
    async def test_send_when_not_connected(self) -> None:
        """Test sending when not connected."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None

        with pytest.raises(WebSocketError, match="Not connected"):
            await client.send("test message")

    @pytest.mark.asyncio
    async def test_send_with_connection_closed(self) -> None:
        """Test sending when connection is closed."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        mock_ws.send.side_effect = ConnectionClosed(None, None)
        client._ws = mock_ws

        with pytest.raises(WebSocketError, match="Failed to send message: Connection is closed"):
            await client.send("test message")

    @pytest.mark.asyncio
    async def test_send_with_exception(self) -> None:
        """Test sending with general exception."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        mock_ws.send.side_effect = Exception("Send failed")
        client._ws = mock_ws

        with pytest.raises(WebSocketError, match="Failed to send message: Send failed"):
            await client.send("test message")


@pytest.mark.integration
class TestWebSocketReceiving:
    """Test WebSocket message receiving."""

    @pytest.mark.asyncio
    async def test_receive_loop_without_websocket(self) -> None:
        """Test receive loop when websocket is None."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._ws = None

        # Should return immediately without error
        await client._receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_with_messages(self) -> None:
        """Test receive loop with string messages."""
        on_message = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_message=on_message)

        messages = ["message1", "message2", "message3"]
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]
        client._ws = mock_ws

        await client._receive_loop()

        assert on_message.call_count == 3
        on_message.assert_any_call("message1")
        on_message.assert_any_call("message2")
        on_message.assert_any_call("message3")

    @pytest.mark.asyncio
    async def test_receive_loop_with_non_string_messages(self) -> None:
        """Test receive loop ignores non-string messages."""
        on_message = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_message=on_message)

        messages = [b"binary", 123, None, "string_message"]
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]
        client._ws = mock_ws

        await client._receive_loop()

        # Only string message should be processed
        on_message.assert_called_once_with("string_message")

    @pytest.mark.asyncio
    async def test_receive_loop_with_handler_error(self) -> None:
        """Test receive loop with message handler error."""
        on_message = Mock(side_effect=Exception("Handler error"))
        on_error = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_message=on_message, on_error=on_error)

        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = ["test_message", ConnectionClosed(None, None)]
        client._ws = mock_ws

        await client._receive_loop()

        on_message.assert_called_once_with("test_message")
        on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_loop_with_connection_closed(self) -> None:
        """Test receive loop handles ConnectionClosed."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = ConnectionClosed(None, None)
        client._ws = mock_ws

        # Should not raise exception
        await client._receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_with_websocket_exception(self) -> None:
        """Test receive loop with WebSocket exception."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = WebSocketException("WebSocket error")
        client._ws = mock_ws

        with pytest.raises(WebSocketError, match="Receive loop error"):
            await client._receive_loop()


@pytest.mark.integration
class TestWebSocketDisconnection:
    """Test WebSocket disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_with_websocket(self) -> None:
        """Test disconnection with active websocket."""
        on_disconnect = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=on_disconnect)

        mock_ws = AsyncMock()
        client._ws = mock_ws
        client._connect_event.set()

        await client._disconnect()

        assert client._ws is None
        assert not client._connect_event.is_set()
        mock_ws.close.assert_called_once()
        on_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_with_close_error(self) -> None:
        """Test disconnection when close fails."""
        on_disconnect = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=on_disconnect)

        mock_ws = AsyncMock()
        mock_ws.close.side_effect = Exception("Close error")
        client._ws = mock_ws

        # Should not raise exception
        await client._disconnect()

        assert client._ws is None
        on_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_without_websocket(self) -> None:
        """Test disconnection without websocket."""
        on_disconnect = Mock()
        client = RobustWebSocketClient("wss://example.com/ws", on_disconnect=on_disconnect)
        client._ws = None

        await client._disconnect()

        on_disconnect.assert_called_once()


@pytest.mark.integration
class TestWebSocketConnection:
    """Test WebSocket connection methods."""

    @pytest.mark.asyncio
    async def test_connect_method_basic_setup(self) -> None:
        """Test connect method basic setup."""
        client = RobustWebSocketClient("wss://example.com/ws")

        # Mock the connection process to avoid complexity
        with patch.object(client, "_connection_loop", AsyncMock()) as mock_loop:
            # Immediately set the event to simulate successful connection
            async def set_event() -> None:
                client._connect_event.set()

            mock_loop.side_effect = set_event

            await client.connect()

            assert client._running is True
            assert client._reconnect_count == 0
            mock_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_when_already_running(self) -> None:
        """Test connect when already running."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True

        await client.connect()

        # Should return without creating connection task
        assert client._connection_task is None

    @pytest.mark.asyncio
    async def test_connect_failure_establishes_connection(self) -> None:
        """Test connection failure in _connect method."""
        client = RobustWebSocketClient("wss://example.com/ws")

        with (
            patch(
                "asset_core.network.ws_client.websockets.connect", AsyncMock(side_effect=Exception("Connection failed"))
            ),
            pytest.raises(ConnectionError, match="Failed to connect"),
        ):
            await client._connect()


@pytest.mark.integration
class TestWebSocketClosing:
    """Test WebSocket closing."""

    @pytest.mark.asyncio
    async def test_close_basic(self) -> None:
        """Test basic close functionality."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True

        await client.close()

        assert client._running is False

    @pytest.mark.asyncio
    async def test_close_with_connection_task(self) -> None:
        """Test close with active connection task."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True

        # Create a real task and then mock its methods
        async def dummy_coro() -> None:
            await asyncio.sleep(1000)  # Long running task

        task = asyncio.create_task(dummy_coro())
        # Use setattr to avoid mypy method assignment error
        mock_cancel = Mock(wraps=task.cancel)
        setattr(task, "cancel", mock_cancel)
        client._connection_task = task

        await client.close()

        assert client._running is False
        mock_cancel.assert_called_once()

        # Clean up the task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_close_with_connected_websocket(self) -> None:
        """Test close with connected websocket."""
        client = RobustWebSocketClient("wss://example.com/ws")
        client._running = True

        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        await client.close()

        assert client._running is False
        mock_ws.close.assert_called_once()


@pytest.mark.integration
class TestWebSocketAsyncContext:
    """Test WebSocket async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager_basic(self) -> None:
        """Test basic async context manager usage."""

        # Mock the entire connection process
        async def mock_connect(self: Any) -> None:
            self._running = True
            self._connect_event.set()

        async def mock_close(self: Any) -> None:
            self._running = False

        with (
            patch.object(RobustWebSocketClient, "connect", mock_connect),
            patch.object(RobustWebSocketClient, "close", mock_close),
        ):
            async with RobustWebSocketClient("wss://example.com/ws") as client:
                assert isinstance(client, RobustWebSocketClient)
                assert client._running is True

            # After exiting async context, client should be closed
            assert client._running is False

    @pytest.mark.asyncio
    async def test_async_context_manager_with_exception(self) -> None:
        """Test async context manager when exception occurs."""

        async def mock_connect(self: Any) -> None:
            self._running = True
            self._connect_event.set()

        async def mock_close(self: Any) -> None:
            self._running = False

        with (
            patch.object(RobustWebSocketClient, "connect", mock_connect),
            patch.object(RobustWebSocketClient, "close", mock_close),
        ):
            try:
                async with RobustWebSocketClient("wss://example.com/ws") as client:
                    assert client._running is True
                    raise ValueError("Test exception")
            except ValueError:
                pass

            assert client._running is False


@pytest.mark.integration
class TestWebSocketReconnection:
    """Test WebSocket reconnection logic."""

    def test_reconnection_backoff_calculation(self) -> None:
        """Test exponential backoff calculation."""
        client = RobustWebSocketClient("wss://example.com/ws", reconnect_interval=1)

        # Test backoff progression
        test_cases = [
            (0, 1),  # 1 * 2^0 = 1
            (1, 2),  # 1 * 2^1 = 2
            (2, 4),  # 1 * 2^2 = 4
            (3, 8),  # 1 * 2^3 = 8
            (5, 32),  # 1 * 2^5 = 32 (max backoff is 2^5)
            (10, 32),  # 1 * 2^5 = 32 (capped at 5)
        ]

        for reconnect_count, expected_wait in test_cases:
            client._reconnect_count = reconnect_count
            wait_time = client.reconnect_interval * (2 ** min(client._reconnect_count, 5))
            assert wait_time == expected_wait


@pytest.mark.integration
class TestWebSocketEdgeCases:
    """Test WebSocket edge cases."""

    def test_empty_headers_initialization(self) -> None:
        """Test initialization with empty headers."""
        client = RobustWebSocketClient("wss://example.com/ws", headers={})
        assert client.headers == {}

    def test_none_headers_initialization(self) -> None:
        """Test initialization with None headers."""
        client = RobustWebSocketClient("wss://example.com/ws", headers=None)
        assert client.headers == {}

    @pytest.mark.asyncio
    async def test_send_very_large_message(self) -> None:
        """Test sending very large message."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        large_message = "x" * 100000
        await client.send(large_message)

        mock_ws.send.assert_called_once_with(large_message)

    @pytest.mark.asyncio
    async def test_send_complex_dict(self) -> None:
        """Test sending complex dictionary."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        complex_dict = {
            "type": "order",
            "data": {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 1.5,
                "metadata": {"timestamp": 1234567890, "nested": ["item1", "item2"]},
            },
        }

        await client.send(complex_dict)

        expected_json = json.dumps(complex_dict)
        mock_ws.send.assert_called_once_with(expected_json)


@pytest.mark.network
@pytest.mark.integration
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_message_processing_lifecycle(self) -> None:
        """Test complete message processing lifecycle."""
        received_messages = []

        def on_message(message: Any) -> None:
            received_messages.append(message)

        client = RobustWebSocketClient("wss://example.com/ws", on_message=on_message)

        # Simulate multiple messages
        messages = ["msg1", "msg2", "msg3"]
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]
        client._ws = mock_ws

        await client._receive_loop()

        assert received_messages == messages

    @pytest.mark.asyncio
    async def test_error_handling_integration(self) -> None:
        """Test integrated error handling."""
        errors = []

        def on_error(error: Any) -> None:
            errors.append(error)

        def on_message(message: Any) -> None:
            if message == "error_message":
                raise ValueError("Test error")

        client = RobustWebSocketClient("wss://example.com/ws", on_message=on_message, on_error=on_error)

        messages = ["good_message", "error_message", "another_good_message"]
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = messages + [ConnectionClosed(None, None)]
        client._ws = mock_ws

        await client._receive_loop()

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_concurrent_send_operations(self) -> None:
        """Test multiple concurrent send operations."""
        client = RobustWebSocketClient("wss://example.com/ws")
        mock_ws = AsyncMock()
        mock_ws.state = State.OPEN
        client._ws = mock_ws

        # Send multiple messages concurrently
        messages = [f"message_{i}" for i in range(10)]
        tasks = [client.send(msg) for msg in messages]

        await asyncio.gather(*tasks)

        assert mock_ws.send.call_count == 10
        sent_messages = [call.args[0] for call in mock_ws.send.call_args_list]
        assert set(sent_messages) == set(messages)
