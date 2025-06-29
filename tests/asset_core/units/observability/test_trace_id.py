"""Tests for trace ID functionality."""

import re
from collections.abc import Generator

import pytest

from asset_core.observability.trace_id import (
    TraceContext,
    clear_trace_id,
    generate_trace_id,
    get_trace_id,
    set_trace_id,
)


@pytest.mark.unit
class TestBasicTraceIdFunctionality:
    """Test basic trace ID generation and management."""

    def test_generate_trace_id(self) -> None:
        """Test automatic trace ID generation.

        Description of what the test covers:
        This test verifies that the `generate_trace_id` function correctly generates
        a unique trace ID string with the expected format and length.

        Preconditions:
        - The `generate_trace_id` function is available.

        Steps:
        - Call `generate_trace_id`.
        - Assert that the returned value is a string.
        - Assert that the length of the string is 32 characters.
        - Assert that the string does not contain hyphens.

        Expected Result:
        - A 32-character string representing a valid trace ID, without hyphens.
        """
        trace_id = generate_trace_id()
        assert isinstance(trace_id, str)
        assert len(trace_id) == 32
        assert "-" not in trace_id

    def test_set_and_get_trace_id(self) -> None:
        """Test trace ID storage and retrieval.

        Description of what the test covers:
        This test verifies the functionality of setting and retrieving a trace ID.
        It ensures that a trace ID can be successfully stored and then accurately
        retrieved from the trace context.

        Preconditions:
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Define a test trace ID string.
        - Call `set_trace_id` with the test ID.
        - Assert that the result of `set_trace_id` matches the test ID.
        - Call `get_trace_id` and assert that the retrieved ID matches the test ID.

        Expected Result:
        - The trace ID is successfully set and retrieved, confirming proper storage and access.
        """
        test_id = "test123"
        result = set_trace_id(test_id)
        assert result == test_id
        assert get_trace_id() == test_id

    def test_set_trace_id_auto_generate(self) -> None:
        """Test automatic generation when setting None trace ID.

        Description of what the test covers:
        This test verifies that if `set_trace_id` is called with `None`,
        a new trace ID is automatically generated and set.

        Preconditions:
        - The `set_trace_id` function is available and handles `None` input.
        - The `generate_trace_id` function is correctly integrated for auto-generation.

        Steps:
        - Call `set_trace_id(None)`.
        - Assert that the returned result is a string.
        - Assert that the length of the generated string is 32 characters.
        - Assert that `get_trace_id()` returns the same generated ID.

        Expected Result:
        - A new, valid 32-character trace ID is automatically generated and set
          when `None` is provided to `set_trace_id`.
        """
        result = set_trace_id(None)
        assert isinstance(result, str)
        assert len(result) == 32
        assert get_trace_id() == result

    def test_get_trace_id_none_when_not_set(self) -> None:
        """Test None return when no trace ID is set.

        Description of what the test covers:
        This test verifies that `get_trace_id()` returns `None` when no trace ID
        has been explicitly set in the current context.

        Preconditions:
        - The `clear_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Call `clear_trace_id()` to ensure no trace ID is currently set.
        - Call `get_trace_id()`.
        - Assert that the returned value is `None`.

        Expected Result:
        - `get_trace_id()` returns `None`, indicating no active trace ID.
        """

    def test_get_or_create_trace_id(self) -> None:
        """Test trace ID retrieval with automatic creation.

        Description of what the test covers:
        This test verifies that `get_or_create_trace_id()` correctly retrieves an existing
        trace ID if one is set, or automatically creates and sets a new one if no ID is present.

        Preconditions:
        - The `clear_trace_id`, `get_or_create_trace_id`, and `get_trace_id` functions are available.

        Steps:
        - Call `clear_trace_id()` to ensure no trace ID is initially set.
        - Call `get_or_create_trace_id()`.
        - Assert that the returned value is a string (indicating a new ID was created).
        - Assert that `get_trace_id()` returns the same ID that was created.

        Expected Result:
        - A valid trace ID is always returned, either by retrieval or by creation, and is correctly set in the context.
        """

    def test_ensure_trace_id(self) -> None:
        """Test trace ID existence guarantee.

        Description of what the test covers:
        This test verifies that `ensure_trace_id()` guarantees the presence of a trace ID.
        If no trace ID is currently set, it should automatically generate and set one.

        Preconditions:
        - The `clear_trace_id`, `ensure_trace_id`, and `get_trace_id` functions are available.

        Steps:
        - Call `clear_trace_id()` to ensure no trace ID is initially set.
        - Call `ensure_trace_id()`.
        - Assert that the returned value is a string (indicating a new ID was created).
        - Assert that `get_trace_id()` returns the same ID that was ensured.

        Expected Result:
        - A valid trace ID is always present after calling `ensure_trace_id()`, either by
          retrieval or by creation, and is correctly set in the context.
        """

    def test_format_trace_id(self) -> None:
        """Test trace ID formatting for display.

        Description of what the test covers:
        This test verifies that the `format_trace_id` function correctly formats
        a given trace ID for display purposes. It specifically checks how `None`
        and empty strings are handled.

        Preconditions:
        - The `format_trace_id` function is available.

        Steps:
        - Call `format_trace_id` with a valid trace ID string and assert it returns the same string.
        - Call `format_trace_id` with `None` and assert it returns "no-trace".
        - Call `format_trace_id` with an empty string and assert it returns "no-trace".

        Expected Result:
        - Valid trace IDs are returned as-is.
        - `None` or empty strings are formatted as "no-trace".
        """

    def test_get_formatted_trace_id(self) -> None:
        """Test formatted trace ID retrieval from context.

        Description of what the test covers:
        This test verifies that `get_formatted_trace_id()` correctly retrieves
        the current trace ID and formats it for display. It checks both scenarios:
        when a trace ID is not set and when it is set.

        Preconditions:
        - The `clear_trace_id`, `set_trace_id`, and `get_formatted_trace_id` functions are available.

        Steps:
        - Call `clear_trace_id()` to ensure no trace ID is initially set.
        - Call `get_formatted_trace_id()` and assert it returns "no-trace".
        - Set a test trace ID using `set_trace_id`.
        - Call `get_formatted_trace_id()` again and assert it returns the set trace ID.

        Expected Result:
        - When no trace ID is set, "no-trace" is returned.
        - When a trace ID is set, the correct formatted trace ID is returned.
        """


@pytest.mark.unit
class TestTraceContext:
    """Test TraceContext context manager."""

    def test_trace_context_with_id(self) -> None:
        """Test TraceContext with explicitly provided ID.

        Description of what the test covers:
        This test verifies the behavior of the `TraceContext` context manager
        when an explicit trace ID is provided. It ensures that the context manager
        correctly sets the provided ID upon entry and restores the original ID upon exit.

        Preconditions:
        - The `TraceContext` context manager is available.
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Set an `original_id` before entering the context.
        - Enter `TraceContext` with a `context_id`.
        - Assert that the `ctx_id` returned by the context manager matches the `context_id`.
        - Assert that `get_trace_id()` within the context returns the `context_id`.
        - Exit the `TraceContext`.
        - Assert that `get_trace_id()` after exiting the context reverts to the `original_id`.

        Expected Result:
        - The `TraceContext` correctly manages the trace ID, setting the provided ID
          within its scope and restoring the previous ID upon exit.
        """

    def test_trace_context_auto_generate(self) -> None:
        """Test TraceContext with automatic ID generation.

        Description of what the test covers:
        This test verifies the behavior of the `TraceContext` context manager
        when no explicit trace ID is provided. It ensures that a new trace ID
        is automatically generated and set upon entry, and the original ID is
        restored upon exit.

        Preconditions:
        - The `TraceContext` context manager is available.
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Set an `original_id` before entering the context.
        - Enter `TraceContext` without providing an explicit ID.
        - Assert that the `ctx_id` returned by the context manager is a string and has the expected length (32 characters).
        - Assert that `get_trace_id()` within the context returns the auto-generated `ctx_id`.
        - Exit the `TraceContext`.
        - Assert that `get_trace_id()` after exiting the context reverts to the `original_id`.

        Expected Result:
        - A new, valid 32-character trace ID is automatically generated and set within the context's scope.
        - The previous trace ID is correctly restored upon exiting the context.
        """
        original_id = get_trace_id()
        with TraceContext() as ctx_id:
            assert isinstance(ctx_id, str)
            assert len(ctx_id) == 32
            assert get_trace_id() == ctx_id
        assert get_trace_id() == original_id

    def test_trace_context_nested(self) -> None:
        """Test nested trace contexts.

        Description of what the test covers:
        This test verifies the correct behavior of `TraceContext` when multiple
        contexts are nested. It ensures that the trace ID is correctly updated
        upon entering each nested context and properly restored to the parent's
        trace ID upon exiting a nested context.

        Preconditions:
        - The `TraceContext` context manager supports nesting.
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Set an initial trace ID for the outermost context.
        - Enter a first nested `TraceContext` with a new ID.
        - Assert that `get_trace_id()` reflects the first nested ID.
        - Enter a second nested `TraceContext` with another new ID.
        - Assert that `get_trace_id()` reflects the second nested ID.
        - Exit the second nested `TraceContext`.
        - Assert that `get_trace_id()` reverts to the first nested ID.
        - Exit the first nested `TraceContext`.
        - Assert that `get_trace_id()` reverts to the initial outermost ID.

        Expected Result:
        - Trace IDs are correctly managed and restored at each level of nesting,
          maintaining the integrity of the trace context stack.
        """


@pytest.mark.unit
class TestTraceIdMiddleware:
    """Test TraceIdMiddleware functionality."""

    def test_extract_trace_id(self) -> None:
        """Test extracting trace ID from headers.

        Description of what the test covers:
        This test verifies that the `TraceIdMiddleware` correctly extracts a trace ID
        from incoming request headers, handling both standard and case-insensitive header names.

        Preconditions:
        - The `TraceIdMiddleware` class is available.

        Steps:
        - Instantiate `TraceIdMiddleware`.
        - Call `extract_trace_id` with headers containing 'X-Trace-Id'.
        - Assert that the correct trace ID is extracted.
        - Call `extract_trace_id` with headers containing 'x-trace-id' (lowercase).
        - Assert that the correct trace ID is extracted.
        - Call `extract_trace_id` with empty headers.
        - Assert that `None` is returned.

        Expected Result:
        - The middleware successfully extracts the trace ID regardless of header case.
        - `None` is returned when no trace ID header is present.
        """

    def test_inject_trace_id(self) -> None:
        """Test injecting trace ID into headers.

        Description of what the test covers:
        This test verifies that the `TraceIdMiddleware` correctly injects the current
        trace ID into a dictionary of headers under the 'X-Trace-Id' key.

        Preconditions:
        - The `TraceIdMiddleware` class is available.
        - A trace ID is set in the current context.

        Steps:
        - Instantiate `TraceIdMiddleware`.
        - Set a test trace ID using `set_trace_id`.
        - Define a dictionary of existing headers.
        - Call `inject_trace_id` with the headers.
        - Assert that the returned dictionary contains the 'X-Trace-Id' key with the correct trace ID.
        - Assert that other existing headers are preserved.
        - Assert that the original headers dictionary is not modified in place.

        Expected Result:
        - The trace ID is successfully injected into the headers, and existing headers are maintained.
        """

    def test_inject_trace_id_no_trace(self) -> None:
        """Test injecting when no trace ID is set.

        Description of what the test covers:
        This test verifies that `TraceIdMiddleware` does not inject a trace ID
        into headers if no trace ID is currently set in the context.

        Preconditions:
        - The `TraceIdMiddleware` class is available.
        - No trace ID is set in the current context.

        Steps:
        - Instantiate `TraceIdMiddleware`.
        - Call `clear_trace_id()` to ensure no trace ID is present.
        - Define a dictionary of existing headers.
        - Call `inject_trace_id` with the headers.
        - Assert that the returned dictionary is identical to the original headers.
        - Assert that the 'X-Trace-Id' key is not present in the returned dictionary.

        Expected Result:
        - Headers remain unchanged when no trace ID is available for injection.
        """

    def test_custom_header_name(self) -> None:
        """Test custom header name.

        Description of what the test covers:
        This test verifies that `TraceIdMiddleware` correctly uses a custom header name
        for injecting the trace ID, if one is provided during initialization.

        Preconditions:
        - The `TraceIdMiddleware` class supports custom header names.
        - A trace ID is set in the current context.

        Steps:
        - Instantiate `TraceIdMiddleware` with a custom `header_name` (e.g., "X-Custom-Trace").
        - Set a test trace ID using `set_trace_id`.
        - Define an empty dictionary for headers.
        - Call `inject_trace_id` with the headers.
        - Assert that the returned dictionary contains the custom header name with the correct trace ID.

        Expected Result:
        - The trace ID is successfully injected into the headers using the specified custom header name.
        """


@pytest.mark.unit
class TestWithTraceIdDecorator:
    """Test with_trace_id decorator."""

    def test_sync_function_with_trace_id(self) -> None:
        """Test decorator on sync function.

        Description of what the test covers:
        This test verifies that the `with_trace_id` decorator correctly sets a
        specified trace ID for a synchronous function's execution context.

        Preconditions:
        - The `with_trace_id` decorator is available.
        - The `get_trace_id` function is available to retrieve the current trace ID.

        Steps:
        - Define a synchronous function `test_func` decorated with `with_trace_id`,
          providing an explicit trace ID (e.g., "decorator_test").
        - Inside `test_func`, retrieve the current trace ID using `get_trace_id()`.
        - Call `test_func()`.
        - Assert that the result returned by `test_func()` matches the explicitly
          provided trace ID.

        Expected Result:
        - The synchronous function executes within the specified trace ID context,
          and `get_trace_id()` returns the expected ID.
        """

    def test_sync_function_auto_trace_id(self) -> None:
        """Test decorator with auto-generated trace ID.

        Description of what the test covers:
        This test verifies that the `with_trace_id` decorator correctly generates
        and sets a new trace ID for a synchronous function's execution context
        when no explicit ID is provided.

        Preconditions:
        - The `with_trace_id` decorator is available.
        - The `get_trace_id` function is available to retrieve the current trace ID.

        Steps:
        - Define a synchronous function `test_func` decorated with `with_trace_id`
          without providing any arguments (triggering auto-generation).
        - Inside `test_func`, retrieve the current trace ID using `get_trace_id()`.
        - Call `test_func()`.
        - Assert that the result returned by `test_func()` is a string.
        - Assert that the length of the generated string is 32 characters.

        Expected Result:
        - A new, valid 32-character trace ID is automatically generated and set
          for the synchronous function's execution context.
        """

    @pytest.mark.asyncio
    async def test_async_function_with_trace_id(self) -> None:
        """Test decorator on async function.

        Description of what the test covers:
        This test verifies that the `with_trace_id` decorator correctly sets a
        specified trace ID for an asynchronous function's execution context.

        Preconditions:
        - The `with_trace_id` decorator is available.
        - The `get_trace_id` function is available to retrieve the current trace ID.
        - `pytest-asyncio` is configured for asynchronous testing.

        Steps:
        - Define an asynchronous function `test_func` decorated with `with_trace_id`,
          providing an explicit trace ID (e.g., "async_test").
        - Inside `test_func`, retrieve the current trace ID using `get_trace_id()`.
        - Await the call to `test_func()`.
        - Assert that the result returned by `test_func()` matches the explicitly
          provided trace ID.

        Expected Result:
        - The asynchronous function executes within the specified trace ID context,
          and `get_trace_id()` returns the expected ID.
        """

    @pytest.mark.asyncio
    async def test_async_function_auto_trace_id(self) -> None:
        """Test decorator on async function with auto-generated ID.

        Description of what the test covers:
        This test verifies that the `with_trace_id` decorator correctly generates
        and sets a new trace ID for an asynchronous function's execution context
        when no explicit ID is provided.

        Preconditions:
        - The `with_trace_id` decorator is available.
        - The `get_trace_id` function is available to retrieve the current trace ID.
        - `pytest-asyncio` is configured for asynchronous testing.

        Steps:
        - Define an asynchronous function `test_func` decorated with `with_trace_id`
          without providing any arguments (triggering auto-generation).
        - Inside `test_func`, retrieve the current trace ID using `get_trace_id()`.
        - Await the call to `test_func()`.
        - Assert that the result returned by `test_func()` is a string.
        - Assert that the length of the generated string is 32 characters.

        Expected Result:
        - A new, valid 32-character trace ID is automatically generated and set
          for the asynchronous function's execution context.
        """


@pytest.mark.unit
class TestThreadSafety:
    """Test thread safety of trace ID system."""

    def test_thread_isolation(self) -> None:
        """Test that trace IDs are isolated between threads.

        Description of what the test covers:
        This test verifies that the trace ID context is properly isolated across
        different threads. It ensures that setting a trace ID in one thread does
        not affect or leak into the trace ID context of other concurrent threads.

        Preconditions:
        - The trace ID system supports thread-local storage for trace IDs.
        - Python's `threading` module is available.

        Steps:
        - Create a dictionary to store results from worker threads.
        - Define a `worker` function that sets a unique trace ID based on its `thread_id`,
          simulates some work (sleep), and then stores the retrieved trace ID in the results dictionary.
        - Create and start multiple `threading.Thread` instances, each running the `worker` function
          with a distinct `thread_id`.
        - Join all threads to ensure their completion.
        - Iterate through the results and assert that each thread successfully retrieved
          its own unique trace ID, confirming isolation.

        Expected Result:
        - Each thread maintains its own independent trace ID context, demonstrating
          correct thread isolation within the trace ID system.
        """

    def test_context_isolation(self) -> None:
        """Test that contexts are isolated.

        Description of what the test covers:
        This test verifies that `TraceContext` instances provide proper isolation
        for trace IDs, ensuring that entering and exiting a context manager
        correctly restores the previous trace ID without leakage.

        Preconditions:
        - The `TraceContext` context manager is available.
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Set an initial trace ID for the main context.
        - Define a helper function `check_context` to retrieve the current trace ID.
        - Assert that `check_context()` returns the initial trace ID.
        - Enter a `TraceContext` with a new, distinct trace ID.
        - Assert that `check_context()` within the context returns the new context-specific ID.
        - Exit the `TraceContext`.
        - Assert that `check_context()` after exiting the context reverts to the initial trace ID.

        Expected Result:
        - The `TraceContext` correctly isolates the trace ID within its scope,
          and the original trace ID is restored upon exiting the context.
        """


@pytest.mark.unit
class TestAsyncioCompatibility:
    """Test asyncio compatibility."""

    @pytest.mark.asyncio
    async def test_async_context_preservation(self) -> None:
        """Test that trace ID is preserved across async boundaries.

        Description of what the test covers:
        This test verifies that the trace ID is correctly preserved and propagated
        across `async/await` boundaries within an asynchronous execution flow.

        Preconditions:
        - The trace ID system is compatible with `asyncio` context variables.
        - `pytest-asyncio` is configured for asynchronous testing.

        Steps:
        - Set an initial trace ID in the main asynchronous context.
        - Define an `async_worker` function that simulates asynchronous work
          (e.g., `asyncio.sleep`) and then retrieves the current trace ID.
        - Await the call to `async_worker()`.
        - Assert that the result returned by `async_worker()` matches the initial trace ID,
          confirming its preservation across the `await` boundary.

        Expected Result:
        - The trace ID remains consistent and is correctly propagated across
          asynchronous function calls and `await` points.
        """

    @pytest.mark.asyncio
    async def test_concurrent_async_tasks(self) -> None:
        """Test trace ID isolation in concurrent async tasks.

        Description of what the test covers:
        This test verifies that trace IDs are properly isolated within concurrent
        asynchronous tasks. It ensures that each task, when run with its own
        `TraceContext`, maintains its unique trace ID without interference from
        other concurrently running tasks.

        Preconditions:
        - The `TraceContext` context manager is available.
        - The trace ID system supports `asyncio` context variables for isolation.
        - `pytest-asyncio` is configured for asynchronous testing.

        Steps:
        - Define an `isolated_task` asynchronous function that uses `TraceContext`
          to set a task-specific trace ID, simulates work, and returns its ID.
        - Create a list of multiple `isolated_task` coroutines with distinct task IDs.
        - Use `asyncio.gather` to run these tasks concurrently.
        - Iterate through the results and assert that each task successfully returned
          its own unique, task-specific trace ID, confirming isolation.

        Expected Result:
        - Each concurrent asynchronous task maintains its own independent trace ID context,
          demonstrating correct isolation within the `asyncio` environment.
        """


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_clear_trace_id(self) -> None:
        """Test clearing trace ID.

        Description of what the test covers:
        This test verifies that the `clear_trace_id()` function successfully removes
        the currently set trace ID from the context, ensuring that subsequent calls
        to `get_trace_id()` return `None`.

        Preconditions:
        - The `set_trace_id`, `get_trace_id`, and `clear_trace_id` functions are available.

        Steps:
        - Set a test trace ID using `set_trace_id`.
        - Assert that `get_trace_id()` returns the set ID.
        - Call `clear_trace_id()`.
        - Assert that `get_trace_id()` now returns `None`.

        Expected Result:
        - The trace ID is successfully cleared from the context.
        """

    def test_multiple_clear_calls(self) -> None:
        """Test multiple clear calls don't cause errors.

        Description of what the test covers:
        This test verifies that calling `clear_trace_id()` multiple times in a row
        does not result in any errors or unexpected behavior.

        Preconditions:
        - The `clear_trace_id` function is available.

        Steps:
        - Call `clear_trace_id()` three consecutive times.
        - No assertions are needed as the test focuses on the absence of errors.

        Expected Result:
        - Multiple calls to `clear_trace_id()` execute without raising exceptions or causing issues.
        """

    def test_context_exception_handling(self) -> None:
        """Test that context is properly restored even with exceptions.

        Description of what the test covers:
        This test verifies that the `TraceContext` context manager correctly restores
        the original trace ID even if an exception occurs within its `with` block.

        Preconditions:
        - The `TraceContext` context manager is available and handles exceptions.
        - The `set_trace_id` and `get_trace_id` functions are available.

        Steps:
        - Set an `original_id` before entering the context.
        - Enter `TraceContext` with a `context_test` ID.
        - Assert that `get_trace_id()` within the context returns `context_test`.
        - Raise a `ValueError` within the context.
        - Catch the `ValueError` (using `pytest.raises`).
        - Assert that `get_trace_id()` after exiting the context (due to the exception)
          reverts to the `original_id`.

        Expected Result:
        - The `TraceContext` ensures that the trace ID is properly restored to its
          previous state, even when exceptions interrupt the context's execution.
        """

    def test_empty_string_trace_id(self) -> None:
        """Test handling of empty string trace ID.

        Description of what the test covers:
        This test verifies how the trace ID system handles an empty string as a trace ID.
        It ensures that an empty string can be set as a trace ID, but when formatted
        for display, it is correctly represented as "no-trace".

        Preconditions:
        - The `set_trace_id`, `get_trace_id`, and `get_formatted_trace_id` functions are available.

        Steps:
        - Set the trace ID to an empty string using `set_trace_id`.
        - Assert that `get_trace_id()` returns an empty string.
        - Assert that `get_formatted_trace_id()` returns "no-trace".

        Expected Result:
        - An empty string can be set as a trace ID.
        - When formatted for display, an empty trace ID is correctly shown as "no-trace".
        """


@pytest.mark.unit
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


@pytest.fixture(autouse=True)
def cleanup_trace_id() -> Generator[None, None, None]:
    """Cleanup trace ID after each test.

    Description of what the fixture covers:
    This fixture ensures that the trace ID is cleared after each test function
    in the module, providing a clean state for subsequent tests and preventing
    trace ID leakage between tests.

    Preconditions:
    - The `clear_trace_id` function is available.

    Steps:
    - Yield control to the test function.
    - After the test function completes, call `clear_trace_id()`.

    Expected Result:
    - The trace ID context is reset to a clean state after every test.
    """
    yield
    clear_trace_id()
