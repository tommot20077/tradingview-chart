"""Global trace ID management for request correlation.

This module provides utilities for generating, setting, retrieving, and managing
trace IDs across asynchronous and synchronous operations. It uses `contextvars`
for asynchronous context propagation and a thread-local fallback for broader
compatibility, ensuring that a unique trace ID can be associated with a flow
of execution for improved observability and debugging.
"""

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
    """Generates a new, unique trace ID.

    The generated ID is a UUID4 string with hyphens removed for a more compact representation.

    Returns:
        A new, unique trace ID string.
    """
    return str(uuid.uuid4()).replace("-", "")


def set_trace_id(trace_id: str | None = None) -> str:
    """Sets the current trace ID in the `contextvars` and thread-local storage.

    This function ensures that the trace ID is propagated across asynchronous
    contexts and also provides a fallback for synchronous, thread-bound operations.

    Args:
        trace_id: An optional trace ID string to set. If `None`, a new unique
                  trace ID will be generated.

    Returns:
        The trace ID that was set (either the provided one or a newly generated one).
    """
    if trace_id is None:
        trace_id = generate_trace_id()

    trace_id_context.set(trace_id)
    _thread_local.trace_id = trace_id
    return trace_id


def get_trace_id() -> str | None:
    """Retrieves the current trace ID from the `contextvars` or thread-local storage.

    This function provides a consistent way to access the trace ID associated
    with the current execution flow, regardless of whether it's an asynchronous
    or synchronous context.

    Returns:
        The current trace ID string, or `None` if no trace ID is set.
    """
    trace_id = trace_id_context.get()
    if trace_id is not None:
        return trace_id

    return getattr(_thread_local, "trace_id", None)


def get_or_create_trace_id() -> str:
    """Retrieves the current trace ID, generating a new one if none is set.

    This function guarantees that a trace ID will always be available for the
    current execution context.

    Returns:
        The current trace ID string, or a newly generated one.
    """
    trace_id = get_trace_id()
    if trace_id is None:
        trace_id = set_trace_id()
    return trace_id


def clear_trace_id() -> None:
    """Clears the current trace ID from both `contextvars` and thread-local storage.

    This is useful for ensuring that trace IDs do not leak across unrelated
    operations or requests.
    """
    trace_id_context.set(None)
    with contextlib.suppress(AttributeError):
        delattr(_thread_local, "trace_id")


class TraceContext:
    """A context manager for temporarily setting and managing a trace ID within a block.

    When entering the context, a specified or newly generated trace ID is set.
    Upon exiting, the previous trace ID (if any) is restored, ensuring proper
    isolation of trace IDs for different operations.
    """

    def __init__(self, trace_id: str | None = None):
        """Initializes the TraceContext.

        Args:
            trace_id: Optional. The trace ID to set for this context. If `None`,
                      a new unique trace ID will be generated.
        """
        self.trace_id = trace_id
        self.token: contextvars.Token[str | None] | None = None

    def __enter__(self) -> str:
        """Enters the context, setting the trace ID.

        Returns:
            The trace ID that is active within this context.
        """
        if self.trace_id is None:
            self.trace_id = generate_trace_id()

        self.token = trace_id_context.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exits the context, restoring the previous trace ID.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
            exc_val: The exception instance.
            exc_tb: The traceback object.
        """
        if self.token is not None:
            trace_id_context.reset(self.token)


def ensure_trace_id() -> str:
    """Ensures that a trace ID is set for the current execution context.

    If no trace ID is currently active, a new one is generated and set.
    This function is useful at the entry points of operations that require
    traceability.

    Returns:
        The current (or newly created) trace ID string.
    """
    trace_id = get_trace_id()
    if trace_id is None:
        trace_id = set_trace_id()
    return trace_id


def format_trace_id(trace_id: str | None) -> str:
    """Formats a trace ID for display, providing a default string for `None` values.

    Args:
        trace_id: The trace ID string to format, or `None`.

    Returns:
        The formatted trace ID string, or "no-trace" if the input was `None`.
    """
    return trace_id if trace_id else "no-trace"


def get_formatted_trace_id() -> str:
    """Retrieves the current trace ID and formats it for display.

    Returns:
        The formatted trace ID string, or "no-trace" if no trace ID is set.
    """
    return format_trace_id(get_trace_id())


class TraceIdMiddleware:
    """Middleware for automatically managing trace IDs in HTTP requests/responses.

    This middleware extracts trace IDs from incoming request headers and injects
    the current trace ID into outgoing response headers, facilitating end-to-end
    traceability across service boundaries.
    """

    def __init__(self, header_name: str = "X-Trace-Id"):
        """Initializes the TraceIdMiddleware.

        Args:
            header_name: The name of the HTTP header to use for trace ID propagation.
                         Defaults to "X-Trace-Id".
        """
        self.header_name = header_name

    def extract_trace_id(self, headers: dict[str, str]) -> str | None:
        """Extracts the trace ID from a dictionary of HTTP headers.

        It checks for the trace ID header in both its original and lowercase forms.

        Args:
            headers: A dictionary representing HTTP request headers.

        Returns:
            The extracted trace ID string, or `None` if not found.
        """
        return headers.get(self.header_name) or headers.get(self.header_name.lower())

    def inject_trace_id(self, headers: dict[str, str]) -> dict[str, str]:
        """Injects the current trace ID into a dictionary of HTTP headers.

        If a trace ID is currently active, it will be added to the headers under
        the configured `header_name`.

        Args:
            headers: A dictionary representing HTTP response headers.

        Returns:
            A new dictionary with the trace ID injected, or the original dictionary
            if no trace ID was active.
        """
        trace_id = get_trace_id()
        if trace_id:
            headers = headers.copy()
            headers[self.header_name] = trace_id
        return headers


def with_trace_id(trace_id: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A decorator that ensures the decorated function executes within a specific trace ID context.

    This decorator can be applied to both synchronous and asynchronous functions.
    It sets a new trace ID for the duration of the function's execution, or uses
    a provided trace ID if specified.

    Args:
        trace_id: Optional. A specific trace ID to use for the function's execution.
                  If `None`, a new trace ID will be generated.

    Returns:
        A decorator that wraps the function to manage its trace ID context.

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
