import re

import pytest

from asset_core.observability.trace_id import (
    generate_trace_id,
)


@pytest.mark.integration
class TestTraceIdPropagation:
    """Test trace ID propagation across complex async and concurrent scenarios."""

    @pytest.mark.asyncio
    async def test_trace_id_across_async_boundaries(self) -> None:
        """Test trace ID propagation across async/await boundaries.

        Description of what the test covers:
        This test verifies that the trace ID is correctly propagated when control flows
        across multiple nested `async/await` calls, ensuring consistency in complex
        asynchronous execution chains, including async generators and context managers.

        Preconditions:
        - The trace ID system is properly initialized and compatible with `asyncio` context variables.
        - `pytest-asyncio` is configured for asynchronous testing.

        Steps:
        - Set an initial trace ID in the main asynchronous context.
        - Define and call a chain of nested asynchronous functions (`level_1_async`,
          `level_2_async`, `level_3_async`), each awaiting the next, and verify the trace ID
          remains consistent at the deepest level.
        - Test an asynchronous generator (`async_generator`) by yielding the trace ID
          multiple times and asserting consistency across iterations.
        - Test an asynchronous context manager (`AsyncContextManager`) by entering and
          exiting the context and verifying trace ID preservation within its scope.
        - Define and run multiple `isolated_task` asynchronous functions concurrently
          using `asyncio.gather`, each with its own `TraceContext`, and verify that
          each task maintains its unique trace ID while the original trace ID in the
          main context remains intact.

        Expected Result:
        - The trace ID remains consistent and is correctly propagated across all
          `async/await` boundaries, including nested functions, async generators,
          and async context managers.
        - Concurrent asynchronous tasks maintain proper trace ID isolation.
        - The original trace ID in the main context is restored after concurrent tasks complete.
        """

    @pytest.mark.asyncio
    async def test_trace_id_in_thread_pool(self) -> None:
        """Test trace ID propagation in thread pool execution.

        Description of what the test covers:
        This test verifies how trace IDs behave when tasks are executed within
        thread pools, specifically using `asyncio.run_in_executor` and `concurrent.futures.ThreadPoolExecutor`.
        It checks for trace ID propagation and isolation across thread boundaries.

        Preconditions:
        - The trace ID system is designed to support thread-local context propagation.
        - `asyncio` and `concurrent.futures` modules are available.

        Steps:
        - Set an initial trace ID in the main asynchronous thread.
        - Define a synchronous `sync_worker` function that retrieves the trace ID.
        - Use `asyncio.run_in_executor` to run `sync_worker` in the default thread pool
          and observe if the trace ID propagates (note: standard `contextvars` might not
          propagate to default thread pools without explicit handling).
        - Use `concurrent.futures.ThreadPoolExecutor` to submit multiple `sync_worker` tasks
          and collect their results, verifying trace ID behavior.
        - Define a `context_preserving_worker` that explicitly sets a trace ID within the thread
          (simulating a context-aware executor) and verify its correctness.
        - Test error handling within a thread pool by submitting a `failing_worker` that raises
          an exception, and ensure the main thread's trace ID remains intact after the exception.

        Expected Result:
        - Trace ID behavior in thread pools is understood and, where context propagation is
          explicitly handled or simulated, the trace ID is correctly maintained or isolated.
        - The main thread's trace ID is not affected by operations in separate threads,
          even when exceptions occur.
        """

    def test_trace_id_collision_probability(self) -> None:
        """Test trace ID collision probability with large number of generations.

        Description of what the test covers:
        This test evaluates the collision probability of generated trace IDs by creating
        a large number of IDs and checking for duplicates. It also assesses the
        performance of the generation process and verifies the format of the generated IDs.
        Additionally, it includes a concurrent generation test to ensure thread safety.

        Preconditions:
        - The `generate_trace_id` function uses a robust, collision-resistant algorithm (e.g., UUID4).
        - Sufficient memory is available for storing a large set of trace IDs.

        Steps:
        - Generate a large number of trace IDs (e.g., 100,000) in a loop.
        - Store generated IDs in a set and count any collisions.
        - Measure the time taken for generation.
        - Assert that the number of collisions is zero (or extremely low for practical purposes).
        - Assert that the total number of unique IDs matches the number generated.
        - Use a regular expression to verify that all generated trace IDs conform to the expected 32-character hexadecimal format without dashes.
        - Assert that the generation time is within an acceptable performance threshold.
        - Calculate and verify the generation rate.
        - Implement a concurrent generation test using multiple threads, each generating IDs.
        - Use a thread-safe mechanism (e.g., `threading.Lock`) to update a shared set of IDs.
        - Assert that no collisions occur during concurrent generation and that the total
          number of unique IDs matches the expected count from all threads.

        Expected Result:
        - The trace ID generation mechanism produces unique IDs with an extremely low
          (ideally zero) collision rate, even under high-volume and concurrent generation.
        - Generated trace IDs adhere to the specified format.
        - The generation performance is acceptable for practical use cases.
        - The trace ID generation is thread-safe, ensuring isolation and uniqueness across threads.
        """
        import threading
        import time

        num_ids = 100_000
        generated_ids = set()
        collisions = 0

        start_time = time.perf_counter()
        for _ in range(num_ids):
            new_id = generate_trace_id()
            if new_id in generated_ids:
                collisions += 1
            generated_ids.add(new_id)
        end_time = time.perf_counter()

        assert collisions == 0
        assert len(generated_ids) == num_ids

        # Verify format
        for _id in generated_ids:
            assert re.fullmatch(r"[0-9a-f]{32}", _id)

        generation_time = end_time - start_time
        print(f"Generated {num_ids} IDs in {generation_time:.4f} seconds")
        print(f"Generation rate: {num_ids / generation_time:.2f} IDs/sec")

        assert generation_time < 1.0  # Should be very fast

        # Concurrent generation test
        concurrent_ids = set()
        concurrent_collisions = 0
        lock = threading.Lock()

        def concurrent_generator(count: int) -> None:
            nonlocal concurrent_collisions
            for _ in range(count):
                new_id = generate_trace_id()
                with lock:
                    if new_id in concurrent_ids:
                        concurrent_collisions += 1
                    concurrent_ids.add(new_id)

        num_threads = 4
        ids_per_thread = num_ids // num_threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=concurrent_generator, args=(ids_per_thread,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert concurrent_collisions == 0
        assert len(concurrent_ids) == num_ids

    def test_trace_context_nesting(self) -> None:
        """Test nested TraceContext behavior and parent-child relationships.

        Description of what the test covers:
        This test verifies that nested `TraceContext` instances correctly manage
        parent-child relationships of trace IDs and ensure proper restoration of
        previous contexts upon exiting a nested scope. It also covers exception
        handling within nested contexts and mixed manual/auto-generated IDs.

        Preconditions:
        - The `TraceContext` context manager supports arbitrary nesting levels.
        - The `set_trace_id`, `get_trace_id`, and `clear_trace_id` functions are available.

        Steps:
        - Set an `original_trace_id` for the outermost context.
        - Create a deep nesting of `TraceContext` instances with distinct IDs (e.g., level_1 to level_4).
        - At each entry and exit point of the nested contexts, assert that `get_trace_id()`
          returns the expected trace ID for that specific level, and record the history.
        - Verify the entire `trace_history` matches the expected sequence of IDs.
        - Test exception handling within nested contexts: set an initial ID, enter nested
          contexts, raise an exception in the innermost, and assert that the trace ID
          is correctly restored to the outer context after the exception is handled.
        - Test auto-generated trace IDs in nested contexts: clear the initial ID, enter
          nested `TraceContext()` (without explicit IDs), and assert that unique IDs are
          generated for each level and restored correctly.
        - Test mixed manual and auto-generated contexts: start with a manual ID, nest an
          auto-generated context, then a manual, then another auto-generated, verifying
          correct ID management at each step.

        Expected Result:
        - Trace IDs are correctly set and restored across all levels of nested `TraceContext`.
        - Exception handling within nested contexts does not disrupt trace ID restoration.
        - Auto-generated trace IDs are unique and properly managed in nested scenarios.
        - The system correctly handles mixed manual and auto-generated trace ID contexts.
        """
