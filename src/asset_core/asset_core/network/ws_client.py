"""Robust WebSocket client with auto-reconnection and heartbeat."""

import asyncio
import builtins
import json
from collections.abc import Callable
from typing import Any

import websockets
from websockets import State
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..exceptions import ConnectionError, TimeoutError, WebSocketError
from ..observability.logging import get_logger
from ..observability.trace_id import TraceContext

logger = get_logger(__name__)


class RobustWebSocketClient:
    """WebSocket client with automatic reconnection and heartbeat support, built on top of websockets.ClientConnection."""

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
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL
            on_message: Callback for received messages
            on_connect: Callback for connection established
            on_disconnect: Callback for connection lost
            on_error: Callback for errors
            reconnect_interval: Base interval between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts
            ping_interval: Interval between ping messages (seconds)
            ping_timeout: Timeout for ping responses (seconds)
            headers: Optional headers to send with connection
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
        """Connect to WebSocket server."""
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
        self._connect_event.clear()

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            finally:
                self._ws = None

        if self.on_disconnect:
            self.on_disconnect()

    async def _receive_loop(self) -> None:
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
        return self._ws is not None and self._ws.state is State.OPEN

    async def __aenter__(self) -> "RobustWebSocketClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
