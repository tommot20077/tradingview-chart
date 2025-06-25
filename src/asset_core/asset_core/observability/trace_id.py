"""Global trace ID management for request correlation."""

import contextlib
import contextvars
import threading
import uuid
from collections.abc import Callable
from typing import Any

# Context variable to store the current trace ID
trace_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

# Thread-local fallback for cases where contextvars are not available
_thread_local = threading.local()


def generate_trace_id() -> str:
    """Generate a new unique trace ID.

    Returns:
        A UUID4 string without dashes for compact representation
    """
    return str(uuid.uuid4()).replace("-", "")


def set_trace_id(trace_id: str | None = None) -> str:
    """Set the current trace ID in context and thread-local storage.

    Args:
        trace_id: Optional trace ID to set. If None, generates a new one.

    Returns:
        The trace ID that was set
    """
    if trace_id is None:
        trace_id = generate_trace_id()

    trace_id_context.set(trace_id)
    _thread_local.trace_id = trace_id
    return trace_id


def get_trace_id() -> str | None:
    """Get the current trace ID from context with thread-local fallback.

    Returns:
        Current trace ID or None if not set
    """
    trace_id = trace_id_context.get()
    if trace_id is not None:
        return trace_id

    return getattr(_thread_local, "trace_id", None)


def get_or_create_trace_id() -> str:
    """Get the current trace ID or create a new one if not set.

    Returns:
        Current trace ID or a newly generated one
    """
    trace_id = get_trace_id()
    if trace_id is None:
        trace_id = set_trace_id()
    return trace_id


def clear_trace_id() -> None:
    """Clear the current trace ID from context and thread-local storage."""
    trace_id_context.set(None)
    with contextlib.suppress(AttributeError):
        delattr(_thread_local, "trace_id")


class TraceContext:
    """Context manager for setting trace ID within a block."""

    def __init__(self, trace_id: str | None = None):
        """Initialize with optional trace ID.

        Args:
            trace_id: Optional trace ID. If None, generates a new one.
        """
        self.trace_id = trace_id
        self.token: contextvars.Token[str | None] | None = None

    def __enter__(self) -> str:
        """Enter context and set trace ID.

        Returns:
            The trace ID that was set
        """
        if self.trace_id is None:
            self.trace_id = generate_trace_id()

        self.token = trace_id_context.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context and restore previous trace ID."""
        if self.token is not None:
            trace_id_context.reset(self.token)


def ensure_trace_id() -> str:
    """Ensure a trace ID exists, creating one if necessary.

    This is useful for initializing trace ID at application startup
    or in situations where you need to guarantee a trace ID exists.

    Returns:
        The current or newly created trace ID
    """
    trace_id = get_trace_id()
    if trace_id is None:
        trace_id = set_trace_id()
    return trace_id


def format_trace_id(trace_id: str | None) -> str:
    """Format trace ID for display, handling None values.

    Args:
        trace_id: The trace ID to format

    Returns:
        Formatted trace ID or 'no-trace' if None
    """
    return trace_id if trace_id else "no-trace"


def get_formatted_trace_id() -> str:
    """Get the current trace ID formatted for display.

    Returns:
        Formatted trace ID or 'no-trace' if not set
    """
    return format_trace_id(get_trace_id())


class TraceIdMiddleware:
    """Middleware to automatically manage trace IDs across async operations."""

    def __init__(self, header_name: str = "X-Trace-Id"):
        """Initialize middleware.

        Args:
            header_name: HTTP header name to look for trace ID
        """
        self.header_name = header_name

    def extract_trace_id(self, headers: dict[str, str]) -> str | None:
        """Extract trace ID from HTTP headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Trace ID if found in headers, None otherwise
        """
        return headers.get(self.header_name) or headers.get(self.header_name.lower())

    def inject_trace_id(self, headers: dict[str, str]) -> dict[str, str]:
        """Inject current trace ID into HTTP headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Headers with trace ID injected
        """
        trace_id = get_trace_id()
        if trace_id:
            headers = headers.copy()
            headers[self.header_name] = trace_id
        return headers


def with_trace_id(trace_id: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to ensure function runs with a trace ID.

    Args:
        trace_id: Optional specific trace ID to use

    Usage:
        @with_trace_id()
        def my_function():
            # This function will always have a trace ID
            pass

        @with_trace_id("custom-trace-id")
        async def async_function():
            # This function will run with the specified trace ID
            pass
    """
    import functools

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with TraceContext(trace_id):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with TraceContext(trace_id):
                return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
