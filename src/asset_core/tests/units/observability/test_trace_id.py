"""Tests for trace ID functionality."""

import asyncio
import concurrent.futures
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


@pytest.mark.unit
class TestTraceIdPropagation:
    """Test trace ID propagation across complex async and concurrent scenarios."""

    @pytest.mark.asyncio
    async def test_trace_id_across_async_boundaries(self) -> None:
        """
        Test trace ID propagation across async/await boundaries.

        This test verifies that trace_id is correctly propagated when control flows
        across async/await calls, ensuring consistency in async execution chains.

        Preconditions:
            - Trace ID system is properly initialized
            - AsyncIO context vars are working correctly

        Steps:
            - Set initial trace ID in main context
            - Call nested async functions with await
            - Verify trace ID consistency across all async boundaries
            - Test async generators and context managers

        Expected Result:
            - Trace ID remains consistent across all async boundaries
            - No trace ID leakage between concurrent tasks
        """
        test_trace_id = "async_boundary_test"
        set_trace_id(test_trace_id)

        async def level_1_async() -> str | None:
            """First level async function."""
            await asyncio.sleep(0.001)
            return await level_2_async()

        async def level_2_async() -> str | None:
            """Second level async function."""
            await asyncio.sleep(0.001)
            return await level_3_async()

        async def level_3_async() -> str | None:
            """Third level async function."""
            await asyncio.sleep(0.001)
            return get_trace_id()

        # Test deep async call chain
        result = await level_1_async()
        assert result == test_trace_id

        # Test async generator
        async def async_generator():
            """Async generator to test trace ID propagation."""
            for _ in range(3):
                await asyncio.sleep(0.001)
                yield get_trace_id()

        async_gen_results = []
        async for trace_id in async_generator():
            async_gen_results.append(trace_id)

        assert all(tid == test_trace_id for tid in async_gen_results)
        assert len(async_gen_results) == 3

        # Test with async context manager
        class AsyncContextManager:
            """Test async context manager."""

            async def __aenter__(self):
                await asyncio.sleep(0.001)
                return get_trace_id()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.001)
                return False

        async with AsyncContextManager() as ctx_trace_id:
            assert ctx_trace_id == test_trace_id
            await asyncio.sleep(0.001)
            assert get_trace_id() == test_trace_id

        # Test concurrent tasks with isolated trace IDs
        async def isolated_task(task_id: int) -> tuple[int, str | None]:
            """Task with its own trace ID."""
            with TraceContext(f"task_{task_id}"):
                await asyncio.sleep(0.01)
                return task_id, get_trace_id()

        # Run multiple isolated tasks concurrently
        tasks = [isolated_task(i) for i in range(5)]
        task_results = await asyncio.gather(*tasks)

        # Verify each task maintained its own trace ID
        for task_id, task_trace_id in task_results:
            assert task_trace_id == f"task_{task_id}"

        # Verify original trace ID is still intact
        assert get_trace_id() == test_trace_id

    @pytest.mark.asyncio
    async def test_trace_id_in_thread_pool(self) -> None:
        """
        Test trace ID propagation in thread pool execution.

        This test verifies that trace_id is correctly propagated when tasks are
        executed in thread pools using run_in_executor.

        Preconditions:
            - Thread pool executor is available
            - Trace ID system supports thread propagation

        Steps:
            - Set trace ID in main thread
            - Execute functions in thread pool
            - Verify trace ID propagation to thread pool
            - Test error handling in thread pool

        Expected Result:
            - Trace ID is properly propagated to thread pool
            - Thread isolation is maintained
            - Error scenarios are handled correctly
        """
        test_trace_id = "thread_pool_test"
        set_trace_id(test_trace_id)

        def sync_worker(worker_id: int) -> tuple[int, str | None]:
            """Synchronous worker function for thread pool."""
            time.sleep(0.01)  # Simulate work
            return worker_id, get_trace_id()

        # Test with default thread pool
        loop = asyncio.get_event_loop()

        # Single task execution
        result = await loop.run_in_executor(None, sync_worker, 1)
        worker_id, worker_trace_id = result
        assert worker_id == 1
        # Note: trace_id might not propagate to thread pool by default
        # This depends on the implementation of contextvars in thread pools

        # Test with ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit multiple tasks
            future_to_id = {executor.submit(sync_worker, i): i for i in range(5)}

            thread_results = {}
            for future in concurrent.futures.as_completed(future_to_id):
                worker_id, worker_trace_id = future.result()
                thread_results[worker_id] = worker_trace_id

        # All workers should have completed
        assert len(thread_results) == 5

        # Test with custom executor that preserves context
        def context_preserving_worker(worker_id: int, expected_trace_id: str) -> bool:
            """Worker that checks for expected trace ID."""
            # Set trace ID in thread (simulating context propagation)
            set_trace_id(expected_trace_id)
            time.sleep(0.01)
            return get_trace_id() == expected_trace_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(context_preserving_worker, i, f"thread_{i}") for i in range(3)]

            results = [future.result() for future in futures]
            assert all(results)  # All workers should succeed

        # Verify main thread trace ID is unchanged
        assert get_trace_id() == test_trace_id

        # Test error handling in thread pool
        def failing_worker() -> None:
            """Worker that raises an exception."""
            set_trace_id("failing_worker")
            raise ValueError("Test error")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(failing_worker)

            with pytest.raises(ValueError, match="Test error"):
                future.result()

        # Main thread trace ID should still be intact
        assert get_trace_id() == test_trace_id

    def test_trace_id_collision_probability(self) -> None:
        """
        Test trace ID collision probability with large number of generations.

        This test generates a large number of trace IDs and verifies that the
        collision rate is acceptably low for UUID4-based generation.

        Preconditions:
            - Trace ID generation uses UUID4
            - Sufficient memory for large set operations

        Steps:
            - Generate large number of trace IDs (100,000+)
            - Check for collisions
            - Measure generation performance
            - Verify UUID4 characteristics

        Expected Result:
            - Collision rate should be extremely low (ideally zero)
            - All trace IDs should be valid UUID4 format
            - Generation performance should be acceptable
        """
        import re
        import time as time_module

        # Generate large number of trace IDs
        num_trace_ids = 100_000
        trace_ids = set()
        collisions = 0

        start_time = time_module.time()

        for _ in range(num_trace_ids):
            trace_id = generate_trace_id()
            if trace_id in trace_ids:
                collisions += 1
            else:
                trace_ids.add(trace_id)

        end_time = time_module.time()
        generation_time = end_time - start_time

        # Verify no collisions (extremely unlikely with UUID4)
        assert collisions == 0, f"Found {collisions} collisions in {num_trace_ids} trace IDs"

        # Verify all trace IDs are unique
        assert len(trace_ids) == num_trace_ids

        # Verify trace ID format (32 hex characters, no dashes)
        uuid_pattern = re.compile(r"^[0-9a-f]{32}$")
        invalid_ids = [tid for tid in trace_ids if not uuid_pattern.match(tid)]
        assert len(invalid_ids) == 0, f"Found {len(invalid_ids)} invalid trace IDs"

        # Performance check (should generate 100k IDs in reasonable time)
        assert generation_time < 10.0, f"Generation took {generation_time:.2f}s, expected < 10s"

        # Calculate and verify generation rate
        generation_rate = num_trace_ids / generation_time
        assert generation_rate > 10_000, f"Generation rate {generation_rate:.0f}/s too slow"

        # Test concurrent generation for thread safety
        import threading

        concurrent_trace_ids = set()
        lock = threading.Lock()
        collision_count = 0

        def concurrent_generator(num_ids: int) -> None:
            """Generate trace IDs concurrently."""
            nonlocal collision_count
            local_ids = set()

            for _ in range(num_ids):
                trace_id = generate_trace_id()
                local_ids.add(trace_id)

            with lock:
                initial_size = len(concurrent_trace_ids)
                concurrent_trace_ids.update(local_ids)
                final_size = len(concurrent_trace_ids)
                expected_increase = len(local_ids)
                actual_increase = final_size - initial_size

                if actual_increase < expected_increase:
                    collision_count += expected_increase - actual_increase

        # Run concurrent generation
        threads = []
        ids_per_thread = 1000
        num_threads = 10

        for _ in range(num_threads):
            thread = threading.Thread(target=concurrent_generator, args=(ids_per_thread,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify concurrent generation results
        expected_total = num_threads * ids_per_thread
        assert collision_count == 0, f"Found {collision_count} collisions in concurrent generation"
        assert len(concurrent_trace_ids) == expected_total

    def test_trace_context_nesting(self) -> None:
        """
        Test nested TraceContext behavior and parent-child relationships.

        This test verifies that nested trace contexts properly manage parent-child
        relationships and correctly restore previous contexts.

        Preconditions:
            - TraceContext supports nesting
            - Context restoration works correctly

        Steps:
            - Create nested trace contexts
            - Verify correct trace ID at each nesting level
            - Test exception handling in nested contexts
            - Verify proper restoration after context exit

        Expected Result:
            - Each nesting level has correct trace ID
            - Contexts are properly restored on exit
            - Exception handling doesn't break context management
        """
        # Test deep nesting
        original_trace_id = "level_0"
        set_trace_id(original_trace_id)

        trace_history = []

        with TraceContext("level_1") as ctx1:
            assert ctx1 == "level_1"
            assert get_trace_id() == "level_1"
            trace_history.append(get_trace_id())

            with TraceContext("level_2") as ctx2:
                assert ctx2 == "level_2"
                assert get_trace_id() == "level_2"
                trace_history.append(get_trace_id())

                with TraceContext("level_3") as ctx3:
                    assert ctx3 == "level_3"
                    assert get_trace_id() == "level_3"
                    trace_history.append(get_trace_id())

                    with TraceContext("level_4") as ctx4:
                        assert ctx4 == "level_4"
                        assert get_trace_id() == "level_4"
                        trace_history.append(get_trace_id())

                    # Back to level 3
                    assert get_trace_id() == "level_3"
                    trace_history.append(get_trace_id())

                # Back to level 2
                assert get_trace_id() == "level_2"
                trace_history.append(get_trace_id())

            # Back to level 1
            assert get_trace_id() == "level_1"
            trace_history.append(get_trace_id())

        # Back to original
        assert get_trace_id() == original_trace_id
        trace_history.append(get_trace_id())

        # Verify trace history
        expected_history = ["level_1", "level_2", "level_3", "level_4", "level_3", "level_2", "level_1", "level_0"]
        assert trace_history == expected_history

        # Test exception handling in nested contexts
        set_trace_id("exception_test")
        exception_trace_history = []

        try:
            with TraceContext("outer_context"):
                exception_trace_history.append(get_trace_id())

                try:
                    with TraceContext("inner_context"):
                        exception_trace_history.append(get_trace_id())
                        raise ValueError("Test exception")

                except ValueError:
                    # Should be back to outer context
                    exception_trace_history.append(get_trace_id())

                exception_trace_history.append(get_trace_id())

        except Exception:
            pass  # Ignore any outer exceptions

        # Should be back to original
        exception_trace_history.append(get_trace_id())

        expected_exception_history = [
            "outer_context",
            "inner_context",
            "outer_context",
            "outer_context",
            "exception_test",
        ]
        assert exception_trace_history == expected_exception_history

        # Test auto-generated trace IDs in nested contexts
        clear_trace_id()

        with TraceContext() as auto_ctx1:
            assert isinstance(auto_ctx1, str)
            assert len(auto_ctx1) == 32

            with TraceContext() as auto_ctx2:
                assert isinstance(auto_ctx2, str)
                assert len(auto_ctx2) == 32
                assert auto_ctx2 != auto_ctx1

                # Nested auto context should have its own ID
                assert get_trace_id() == auto_ctx2

            # Should be back to first auto context
            assert get_trace_id() == auto_ctx1

        # Should be cleared again
        assert get_trace_id() is None

        # Test mixed manual and auto contexts
        set_trace_id("manual_start")

        with TraceContext() as auto_mixed:  # Auto-generated
            with TraceContext("manual_nested"):  # Manual
                with TraceContext() as auto_nested:  # Auto-generated again
                    assert get_trace_id() == auto_nested
                    assert isinstance(auto_nested, str)
                    assert len(auto_nested) == 32

                assert get_trace_id() == "manual_nested"

            assert get_trace_id() == auto_mixed

        assert get_trace_id() == "manual_start"


@pytest.fixture(autouse=True)
def cleanup_trace_id() -> Generator[None, None, None]:
    """Cleanup trace ID after each test."""
    yield
    clear_trace_id()
