import asyncio
import builtins
import contextlib
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pytest_mock import MockerFixture
from websockets import State
from websockets.client import ClientConnection
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
    mock_connection = AsyncMock(spec=ClientConnection)

    # 2. 手動設定 state，這樣 client.is_connected 才能正常運作
    mock_connection.state = State.OPEN

    # 3. 確保重要的 awaitable 方法有預設回傳值
    mock_connection.close = AsyncMock()
    mock_connection.send = AsyncMock()
    mock_connection.recv = AsyncMock(side_effect=ConnectionClosed(None, None))

    # 使用 mocker 來 patch 正確的路徑，並確保它是 AsyncMock
    mock_connect_func = mocker.patch("asset_core.network.ws_client.websockets.connect", new_callable=AsyncMock)
    mock_connect_func.return_value = mock_connection

    return mock_connect_func, mock_connection


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

        await client.connect(timeout=5)

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
            await client.connect(timeout=5)

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
    async def test_connection_loop_successful_reconnection(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mocker: MockerFixture,
    ) -> None:
        """Test that the connection loop properly handles reconnection after initial failure."""
        mock_connect, mock_ws = mock_websockets_connect
        error_event = asyncio.Event()
        connect_event = asyncio.Event()
        sleep_event = asyncio.Event()

        mock_connect.side_effect = [
            WebSocketException("Initial connection failed"),
            mock_ws,
        ]
        mock_ws.recv.side_effect = [ConnectionClosed(None, None)]

        original_asyncio_sleep = asyncio.sleep

        async def mock_sleep_side_effect(_: float) -> None:
            sleep_event.set()
            await original_asyncio_sleep(0)  # Yield control immediately

        mocker.patch("asyncio.sleep", side_effect=mock_sleep_side_effect)

        client = RobustWebSocketClient(
            url=TEST_URL,
            on_error=lambda _: error_event.set(),
            on_connect=lambda: connect_event.set(),
            reconnect_interval=0.1,
            max_reconnect_attempts=3,
        )

        client._running = True
        connection_task = asyncio.create_task(client._connection_loop())

        try:
            # --- First Attempt (Failure) ---
            await asyncio.wait_for(error_event.wait(), timeout=1)
            # Wait for the sleep to be called after the first failure
            await asyncio.wait_for(sleep_event.wait(), timeout=1)
            assert mock_connect.call_count == 1

            # --- Second Attempt (Success) ---
            sleep_event.clear()  # Clear the event for the next sleep call
            await asyncio.wait_for(connect_event.wait(), timeout=1)
            assert mock_connect.call_count == 2

        finally:
            client._running = False
            connection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await connection_task

    @pytest.mark.asyncio
    async def test_close_method(
        self, mock_websockets_connect: tuple[AsyncMock, AsyncMock], mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Test the close method."""
        _, mock_ws = mock_websockets_connect
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)

        await client.connect(timeout=5)
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
    async def test_max_reconnect_attempts_stops_client_with_error_callback(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test that client stops running after max_reconnect_attempts is reached and calls on_error.

        This test verifies the scenario described in missing_tests.md:
        - max_reconnect_attempts reached
        - assert client stops running
        - assert on_error callback is invoked indicating permanent failure
        """
        mock_connect, _ = mock_websockets_connect

        # Configure connection to always fail
        mock_connect.side_effect = WebSocketException("Connection always fails")

        client = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            reconnect_interval=0.01,  # Very short interval for faster test
            max_reconnect_attempts=2,  # Small number for faster test
        )

        # Start the connection manually to control the test
        client._running = True
        connection_task = asyncio.create_task(client._connection_loop())

        # Wait for the connection task to complete (it should stop after max attempts)
        try:
            await asyncio.wait_for(connection_task, timeout=2.0)
        except builtins.TimeoutError:
            # If it didn't finish, that's a problem - cancel it
            connection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await connection_task
            raise AssertionError("Connection task should have stopped after max reconnect attempts")

        # Verify client stopped running after max attempts
        assert not client._running
        assert client._reconnect_count >= 2

        # Verify connection was attempted the expected number of times
        # Should be max_reconnect_attempts + 1 (initial attempt + retries)
        assert mock_connect.call_count >= 2

        # Verify on_error was called for each failed connection attempt
        assert mock_callbacks["on_error"].call_count >= 2

    @pytest.mark.asyncio
    async def test_unlimited_reconnect_attempts_continues_indefinitely(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test that client continues attempting reconnections with max_reconnect_attempts = -1."""
        mock_connect, _ = mock_websockets_connect

        # Configure connection to always fail
        mock_connect.side_effect = WebSocketException("Connection always fails")

        client = RobustWebSocketClient(
            url=TEST_URL,
            **mock_callbacks,
            reconnect_interval=0.01,  # Very short interval for faster test
            max_reconnect_attempts=-1,  # Unlimited attempts
        )

        # Start the connection manually to control the test
        client._running = True
        connection_task = asyncio.create_task(client._connection_loop())

        # Let the connection loop run for a short time
        await asyncio.sleep(0.1)

        # The client should still be running and attempting connections
        assert client._running
        assert client._reconnect_count > 0

        # Verify that multiple connection attempts were made
        initial_attempts = mock_connect.call_count
        assert initial_attempts > 0

        # Allow more time for additional attempts
        await asyncio.sleep(0.1)

        # Should continue making connection attempts
        assert mock_connect.call_count > initial_attempts
        assert client._running  # Should still be running

        # Clean up
        client._running = False
        connection_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await connection_task

    @pytest.mark.asyncio
    async def test_connection_state_management_during_lifecycle(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """Test that connection state is properly managed throughout the client lifecycle."""
        mock_connect, mock_connection = mock_websockets_connect

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)
        assert not client.is_connected
        assert not client._running
        assert client._reconnect_count == 0

        await client.connect(timeout=5)

        assert client.is_connected
        assert client._running  # type: ignore[unreachable]
        mock_connect.assert_called_once_with(TEST_URL, extra_headers={}, ping_interval=30, ping_timeout=10)
        mock_callbacks["on_connect"].assert_called_once()
        assert client._reconnect_count == 0

        await client.close()

        assert not client.is_connected
        assert not client._running
        mock_callbacks["on_disconnect"].assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_cancellation(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """測試客戶端能否優雅地處理連線任務被取消的情況。"""
        mock_connect, _ = mock_websockets_connect

        # 1. 模擬 connect() 會永遠阻塞
        never_set_event = asyncio.Event()
        mock_connect.side_effect = never_set_event.wait

        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks)
        assert not client.is_connected
        assert not client._running

        # 2. 在背景任務中啟動連線
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0)  # 讓事件循環執行 connect_task

        # 3. 驗證狀態變為「運行中」
        assert not client.is_connected
        assert client._running

        # 4. 取消連線任務
        connect_task.cancel()  # type: ignore[unreachable]

        # 5. 等待任務結束，並捕獲 CancelledError
        with pytest.raises(asyncio.CancelledError):
            await connect_task

        # 6. 驗證取消後，客戶端狀態已完全重置
        assert not client.is_connected
        # ****** 修正後的斷言 ******
        # 因為 `close()` 被呼叫，所以 `_running` 應該是 False
        assert not client._running

        # 7. 驗證回調
        mock_callbacks["on_connect"].assert_not_called()

        # ****** 修正後的斷言 ******
        # client.close() -> _connection_task.cancel() -> _connection_loop 的 finally 區塊
        # -> _disconnect() -> on_disconnect() 被呼叫。這是一個正確的清理流程。
        mock_callbacks["on_disconnect"].assert_called_once()

    # 測試案例 3: 連線失敗與重試
    @pytest.mark.asyncio
    async def test_reconnect_on_initial_failure(
        self,
        mock_websockets_connect: tuple[AsyncMock, AsyncMock],
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """測試客戶端在初次連線失敗時是否會自動重試。"""
        mock_connect, mock_connection = mock_websockets_connect

        # 1. 模擬第一次連線失敗，第二次成功
        connection_error = ConnectionError("Connection refused")
        mock_connect.side_effect = [connection_error, mock_connection]

        # 使用較短的重連間隔以加速測試
        client = RobustWebSocketClient(url=TEST_URL, **mock_callbacks, reconnect_interval=0.01)

        # 2. 執行連線，這會觸發一次失敗和一次成功的重試
        await client.connect(timeout=5)

        # 3. 驗證最終狀態
        assert client.is_connected
        assert client._running
        assert client._reconnect_count == 0  # 成功重連後計數器重置為0

        # 4. 驗證 mock 和 callback 的呼叫情況
        assert mock_connect.call_count == 2
        mock_connect.assert_has_calls(
            [
                call(TEST_URL, extra_headers={}, ping_interval=30, ping_timeout=10),
                call(TEST_URL, extra_headers={}, ping_interval=30, ping_timeout=10),
            ]
        )

        # `on_error` 應該在 _connection_loop 中被呼叫一次，錯誤會被包裝
        mock_callbacks["on_error"].assert_called_once()
        # 驗證錯誤類型和消息內容
        called_error = mock_callbacks["on_error"].call_args[0][0]
        assert isinstance(called_error, ConnectionError)
        # 錯誤消息可能包含 trace_id 和其他前綴，檢查核心錯誤消息
        error_str = str(called_error)
        assert "Failed to connect:" in error_str and "Connection refused" in error_str
        # `on_connect` 應該在第二次成功後被呼叫
        mock_callbacks["on_connect"].assert_called_once()
        # 在重連過程中，`on_disconnect` 也會被呼叫一次 (在失敗的連線嘗試後)
        mock_callbacks["on_disconnect"].assert_called_once()

        await client.close()
