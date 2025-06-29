"""Robust WebSocket client with auto-reconnection and heartbeat.

This module provides a `RobustWebSocketClient` class that extends the basic
WebSocket client functionality with features like automatic reconnection,
heartbeat (ping/pong) mechanisms, and comprehensive error handling.
It is designed to maintain a stable and reliable connection for real-time
data streaming.
"""

import asyncio
import builtins
import json
from collections.abc import Callable
from typing import Any

import websockets
from websockets import State
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, WebSocketException

from asset_core.exceptions import ConnectionError, TimeoutError, WebSocketError
from asset_core.observability.logging import get_logger
from asset_core.observability.trace_id import TraceContext

logger = get_logger(__name__)


class RobustWebSocketClient:
    """A robust WebSocket client with automatic reconnection, heartbeat, and comprehensive error handling.

    This client is built upon `websockets.ClientConnection` and provides enhanced
    reliability for real-time data streaming applications. It manages connection
    lifecycle, including initial connection, automatic reconnections on disconnects,
    and sending/receiving messages with proper error handling.
    """

    def __init__(
        self,
        url: str,
        *,
        on_message: Callable[[str], None] | None = None,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        ping_interval: int = 30,
        ping_timeout: int = 10,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initializes a new RobustWebSocketClient instance.

        Args:
            url: The WebSocket URL to connect to.
            on_message: An optional callback function to be called when a message is received.
                        It takes the received message (string) as an argument.
            on_connect: An optional callback function to be called when the WebSocket connection is successfully established.
            on_disconnect: An optional callback function to be called when the WebSocket connection is closed.
            on_error: An optional callback function to be called when an error occurs.
                      It takes the exception object as an argument.
            reconnect_interval: The base time in seconds to wait before attempting a reconnection.
                                This interval increases exponentially with each failed attempt.
            max_reconnect_attempts: The maximum number of reconnection attempts before giving up.
                                    Set to -1 for unlimited attempts.
            ping_interval: The interval in seconds at which ping frames are sent to keep the connection alive.
                           Set to `None` to disable ping/pong.
            ping_timeout: The maximum time in seconds to wait for a pong response after sending a ping.
                          If no pong is received within this time, the connection is considered broken.
            headers: An optional dictionary of HTTP headers to send during the WebSocket handshake.
        """
        self.url = url
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.headers = headers or {}

        self._ws: ClientConnection | None = None
        self._running = False
        self._reconnect_count = 0
        self._connection_task: asyncio.Task | None = None
        self._receive_task: asyncio.Task | None = None
        self._connect_event = asyncio.Event()

    async def connect(self) -> None:
        """Establishes the WebSocket connection and starts the connection management loop.

        This method initiates the connection process, including handling initial
        connection attempts and setting up the background tasks for maintaining
        the connection and receiving messages.

        Raises:
            TimeoutError: If the initial connection cannot be established within a timeout period.
            ConnectionError: If there's a persistent issue preventing connection.
        """
        with TraceContext() as trace_id:
            if self._running:
                return

            logger.info("Starting WebSocket connection", trace_id=trace_id, url=self.url)
            self._running = True
            self._reconnect_count = 0
            self._connection_task = asyncio.create_task(self._connection_loop())

            try:
                await asyncio.wait_for(self._connect_event.wait(), timeout=30)
                logger.info("WebSocket connection established successfully", trace_id=trace_id)
            except builtins.TimeoutError:
                logger.error("WebSocket connection timeout", trace_id=trace_id)
                await self.close()
                raise TimeoutError("Failed to establish initial connection")

    async def _connection_loop(self) -> None:
        """Manages the WebSocket connection lifecycle, including reconnection attempts.

        This internal method runs in a separate task and continuously tries to
        maintain an active WebSocket connection. It handles disconnections,
        implements exponential backoff for reconnection attempts, and manages
        the message receiving loop.
        """
        while self._running:
            try:
                await self._connect()
                self._reconnect_count = 0
                self._receive_task = asyncio.create_task(self._receive_loop())
                await self._receive_task

            except Exception as e:
                if not isinstance(e, asyncio.CancelledError):
                    logger.error("Connection loop error", error=str(e), error_type=type(e).__name__)
                    if self.on_error:
                        self.on_error(e)

            finally:
                await self._disconnect()

            if self._running and self._reconnect_count < self.max_reconnect_attempts:
                wait_time = self.reconnect_interval * (2 ** min(self._reconnect_count, 5))
                logger.info(
                    "Scheduling reconnection",
                    wait_time=wait_time,
                    attempt=self._reconnect_count + 1,
                    max_attempts=self.max_reconnect_attempts,
                )
                self._reconnect_count += 1
                await asyncio.sleep(wait_time)
            elif self._running:
                logger.error(
                    "Max reconnection attempts reached, stopping connection",
                    attempts=self._reconnect_count,
                    max_attempts=self.max_reconnect_attempts,
                )
                self._running = False

    async def _connect(self) -> None:
        """Performs a single attempt to establish a WebSocket connection.

        This method is called by the `_connection_loop` to try and connect to
        the WebSocket server. It handles the actual `websockets.connect` call
        and invokes the `on_connect` callback upon success.

        Raises:
            ConnectionError: If the connection attempt fails.
        """
        logger.info("Attempting WebSocket connection", url=self.url, headers=bool(self.headers))

        try:
            self._ws = await websockets.connect(
                self.url,
                extra_headers=self.headers,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )

            logger.info(
                "WebSocket connection established",
                url=self.url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )
            self._connect_event.set()

            if self.on_connect:
                self.on_connect()

        except Exception as e:
            logger.error(
                "Failed to establish WebSocket connection", url=self.url, error=str(e), error_type=type(e).__name__
            )
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def _disconnect(self) -> None:
        """Closes the current WebSocket connection.

        This internal method handles the graceful shutdown of the underlying
        WebSocket connection and invokes the `on_disconnect` callback.
        """
        try:
            if self._ws is not None:
                logger.debug("Closing WebSocket connection")
                await self._ws.close()
                logger.debug("WebSocket connection closed")
            else:
                logger.debug("No active WebSocket connection to close")
        except Exception as e:
            logger.warning(f"Error closing WebSocket connection: {e}")
        finally:
            self._ws = None
            self._connect_event.clear()

            # Always call the disconnect callback, even if there was no connection
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception as e:
                    logger.error(f"Error in disconnect callback: {e}")
                    if self.on_error:
                        self.on_error(e)

    async def _receive_loop(self) -> None:
        """Continuously receives messages from the WebSocket connection.

        This internal method runs in a separate task and processes incoming
        messages, invoking the `on_message` callback for each received message.
        It also handles connection closure and WebSocket-specific errors.

        Raises:
            WebSocketError: If a WebSocket-specific error occurs during message reception.
        """
        if not self._ws:
            return

        try:
            while True:
                try:
                    message = await self._ws.recv()
                    if isinstance(message, str) and self.on_message:
                        try:
                            self.on_message(message)
                        except Exception as e:
                            logger.error(
                                "Error in message handler",
                                error=str(e),
                                error_type=type(e).__name__,
                                message_length=len(message) if isinstance(message, str) else None,
                            )
                            if self.on_error:
                                self.on_error(e)
                except ConnectionClosed as e:
                    logger.info(
                        "WebSocket connection closed",
                        close_code=getattr(e, "code", None),
                        close_reason=getattr(e, "reason", None),
                    )
                    break
        except WebSocketException as e:
            logger.error("WebSocket error in receive loop", error=str(e), error_type=type(e).__name__)
            raise WebSocketError(f"Receive loop error: {e}") from e

    async def send(self, message: str | dict[str, Any]) -> None:
        """Sends a message over the WebSocket connection.

        The message can be a string or a dictionary (which will be JSON-serialized).

        Args:
            message: The message to send. Can be a string or a dictionary.

        Raises:
            WebSocketError: If the client is not connected or if sending the message fails.
        """
        if not self.is_connected or self._ws is None:
            logger.warning("Attempted to send message while not connected")
            raise WebSocketError("Not connected")

        original_message = message
        if isinstance(message, dict):
            message = json.dumps(message)

        try:
            await self._ws.send(message)
            logger.debug(
                "Message sent successfully", message_type=type(original_message).__name__, message_length=len(message)
            )
        except ConnectionClosed:
            logger.error("Failed to send message: connection closed")
            raise WebSocketError("Failed to send message: Connection is closed.") from None
        except Exception as e:
            logger.error(
                "Failed to send message", error=str(e), error_type=type(e).__name__, message_length=len(message)
            )
            raise WebSocketError(f"Failed to send message: {e}") from e

    async def close(self) -> None:
        """Closes the WebSocket client, terminating all connections and tasks.

        This method ensures a graceful shutdown, cancelling any running tasks
        and closing the underlying WebSocket connection.
        """
        logger.info("Closing WebSocket client", is_running=self._running, is_connected=self.is_connected)
        self._running = False

        if self._connection_task and not self._connection_task.done():
            logger.debug("Cancelling connection task")
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                logger.debug("Connection task cancelled successfully")
                pass

        if self.is_connected:
            await self._disconnect()

        logger.info("WebSocket client closed successfully")

    @property
    def is_connected(self) -> bool:
        """Checks if the WebSocket client is currently connected.

        Returns:
            `True` if the underlying WebSocket connection is open, `False` otherwise.
        """
        return self._ws is not None and self._ws.state is State.OPEN

    async def __aenter__(self) -> "RobustWebSocketClient":
        """Enters the asynchronous context, establishing the WebSocket connection.

        Returns:
            The `RobustWebSocketClient` instance.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the asynchronous context, ensuring the WebSocket client is closed.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
            exc_val: The exception instance.
            exc_tb: The traceback object.
        """
        await self.close()
