"""Tests for trace ID functionality."""

import asyncio
import threading
import time
from collections.abc import Generator
from typing import Any

import pytest

from src.asset_core.asset_core.observability.trace_id import (
    TraceContext,
    TraceIdMiddleware,
    clear_trace_id,
    ensure_trace_id,
    format_trace_id,
    generate_trace_id,
    get_formatted_trace_id,
    get_or_create_trace_id,
    get_trace_id,
    set_trace_id,
    with_trace_id,
)


@pytest.mark.unit
class TestBasicTraceIdFunctionality:
    """Test basic trace ID generation and management."""

    def test_generate_trace_id(self) -> None:
        """Test automatic trace ID generation."""
        trace_id = generate_trace_id()
        assert isinstance(trace_id, str)
        assert len(trace_id) == 32
        assert "-" not in trace_id

    def test_set_and_get_trace_id(self) -> None:
        """Test trace ID storage and retrieval."""
        test_id = "test123"
        result = set_trace_id(test_id)
        assert result == test_id
        assert get_trace_id() == test_id

    def test_set_trace_id_auto_generate(self) -> None:
        """Test automatic generation when setting None trace ID."""
        result = set_trace_id(None)
        assert isinstance(result, str)
        assert len(result) == 32
        assert get_trace_id() == result

    def test_get_trace_id_none_when_not_set(self) -> None:
        """Test None return when no trace ID is set."""
        clear_trace_id()
        assert get_trace_id() is None

    def test_get_or_create_trace_id(self) -> None:
        """Test trace ID retrieval with automatic creation."""
        clear_trace_id()
        trace_id = get_or_create_trace_id()
        assert isinstance(trace_id, str)
        assert get_trace_id() == trace_id

    def test_ensure_trace_id(self) -> None:
        """Test trace ID existence guarantee."""
        clear_trace_id()
        trace_id = ensure_trace_id()
        assert isinstance(trace_id, str)
        assert get_trace_id() == trace_id

    def test_format_trace_id(self) -> None:
        """Test trace ID formatting for display."""
        assert format_trace_id("test123") == "test123"
        assert format_trace_id(None) == "no-trace"
        assert format_trace_id("") == "no-trace"

    def test_get_formatted_trace_id(self) -> None:
        """Test formatted trace ID retrieval from context."""
        clear_trace_id()
        assert get_formatted_trace_id() == "no-trace"

        set_trace_id("test123")
        assert get_formatted_trace_id() == "test123"


@pytest.mark.unit
class TestTraceContext:
    """Test TraceContext context manager."""

    def test_trace_context_with_id(self) -> None:
        """Test TraceContext with explicitly provided ID."""
        original_id = set_trace_id("original")

        with TraceContext("context_id") as ctx_id:
            assert ctx_id == "context_id"
            assert get_trace_id() == "context_id"

        assert get_trace_id() == original_id

    def test_trace_context_auto_generate(self) -> None:
        """Test TraceContext with automatic ID generation."""
        original_id = set_trace_id("original")

        with TraceContext() as ctx_id:
            assert isinstance(ctx_id, str)
            assert len(ctx_id) == 32
            assert get_trace_id() == ctx_id

        assert get_trace_id() == original_id

    def test_trace_context_nested(self) -> None:
        """Test nested trace contexts."""
        set_trace_id("level0")

        with TraceContext("level1"):
            assert get_trace_id() == "level1"

            with TraceContext("level2"):
                assert get_trace_id() == "level2"

            assert get_trace_id() == "level1"

        assert get_trace_id() == "level0"


@pytest.mark.unit
class TestTraceIdMiddleware:
    """Test TraceIdMiddleware functionality."""

    def test_extract_trace_id(self) -> None:
        """Test extracting trace ID from headers."""
        middleware = TraceIdMiddleware()

        headers: dict[str, Any] = {"X-Trace-Id": "test123"}
        assert middleware.extract_trace_id(headers) == "test123"

        headers = {"x-trace-id": "test456"}
        assert middleware.extract_trace_id(headers) == "test456"

        headers = {}
        assert middleware.extract_trace_id(headers) is None

    def test_inject_trace_id(self) -> None:
        """Test injecting trace ID into headers."""
        middleware = TraceIdMiddleware()
        set_trace_id("test123")

        headers: dict[str, Any] = {"Content-Type": "application/json"}
        result = middleware.inject_trace_id(headers)

        assert result["X-Trace-Id"] == "test123"
        assert result["Content-Type"] == "application/json"
        assert "X-Trace-Id" not in headers

    def test_inject_trace_id_no_trace(self) -> None:
        """Test injecting when no trace ID is set."""
        middleware = TraceIdMiddleware()
        clear_trace_id()

        headers: dict[str, Any] = {"Content-Type": "application/json"}
        result = middleware.inject_trace_id(headers)

        assert result == headers
        assert "X-Trace-Id" not in result

    def test_custom_header_name(self) -> None:
        """Test custom header name."""
        middleware = TraceIdMiddleware(header_name="X-Custom-Trace")
        set_trace_id("test123")

        headers: dict[str, Any] = {}
        result = middleware.inject_trace_id(headers)
        assert result["X-Custom-Trace"] == "test123"


@pytest.mark.unit
class TestWithTraceIdDecorator:
    """Test with_trace_id decorator."""

    def test_sync_function_with_trace_id(self) -> None:
        """Test decorator on sync function."""

        @with_trace_id("decorator_test")
        def test_func() -> str | None:
            return get_trace_id()

        result = test_func()
        assert result == "decorator_test"

    def test_sync_function_auto_trace_id(self) -> None:
        """Test decorator with auto-generated trace ID."""

        @with_trace_id()
        def test_func() -> str | None:
            return get_trace_id()

        result = test_func()
        assert isinstance(result, str)
        assert len(result) == 32

    @pytest.mark.asyncio
    async def test_async_function_with_trace_id(self) -> None:
        """Test decorator on async function."""

        @with_trace_id("async_test")
        async def test_func() -> str | None:
            return get_trace_id()

        result = await test_func()
        assert result == "async_test"

    @pytest.mark.asyncio
    async def test_async_function_auto_trace_id(self) -> None:
        """Test decorator on async function with auto-generated ID."""

        @with_trace_id()
        async def test_func() -> str | None:
            return get_trace_id()

        result = await test_func()
        assert isinstance(result, str)
        assert len(result) == 32


@pytest.mark.unit
class TestThreadSafety:
    """Test thread safety of trace ID system."""

    def test_thread_isolation(self) -> None:
        """Test that trace IDs are isolated between threads."""
        results: dict[int, str | None] = {}

        def worker(thread_id: int) -> None:
            set_trace_id(f"thread_{thread_id}")
            time.sleep(0.1)
            results[thread_id] = get_trace_id()

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        for i in range(5):
            assert results[i] == f"thread_{i}"

    def test_context_isolation(self) -> None:
        """Test that contexts are isolated."""
        set_trace_id("main")

        def check_context() -> str | None:
            return get_trace_id()

        assert check_context() == "main"

        with TraceContext("context1"):
            assert check_context() == "context1"

        assert check_context() == "main"


@pytest.mark.unit
class TestAsyncioCompatibility:
    """Test asyncio compatibility."""

    @pytest.mark.asyncio
    async def test_async_context_preservation(self) -> None:
        """Test that trace ID is preserved across async boundaries."""
        set_trace_id("async_test")

        async def async_worker() -> str | None:
            await asyncio.sleep(0.01)
            return get_trace_id()

        result = await async_worker()
        assert result == "async_test"

    @pytest.mark.asyncio
    async def test_concurrent_async_tasks(self) -> None:
        """Test trace ID isolation in concurrent async tasks."""

        async def task_with_trace_id(task_id: int) -> str | None:
            with TraceContext(f"task_{task_id}"):
                await asyncio.sleep(0.01)
                return get_trace_id()

        tasks = [task_with_trace_id(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            assert result == f"task_{i}"


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_clear_trace_id(self) -> None:
        """Test clearing trace ID."""
        set_trace_id("test")
        assert get_trace_id() == "test"

        clear_trace_id()
        assert get_trace_id() is None

    def test_multiple_clear_calls(self) -> None:
        """Test multiple clear calls don't cause errors."""
        clear_trace_id()
        clear_trace_id()
        clear_trace_id()

    def test_context_exception_handling(self) -> None:
        """Test that context is properly restored even with exceptions."""
        set_trace_id("original")

        with pytest.raises(ValueError), TraceContext("context_test"):
            assert get_trace_id() == "context_test"
            raise ValueError("Test exception")

        assert get_trace_id() == "original"

    def test_empty_string_trace_id(self) -> None:
        """Test handling of empty string trace ID."""
        set_trace_id("")
        assert get_trace_id() == ""
        assert get_formatted_trace_id() == "no-trace"


@pytest.fixture(autouse=True)
def cleanup_trace_id() -> Generator[None, None, None]:
    """Cleanup trace ID after each test."""
    yield
    clear_trace_id()
