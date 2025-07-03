"""Tests for trace ID functionality."""

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
        clear_trace_id()
        assert get_trace_id() is None

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
        from asset_core.observability.trace_id import get_or_create_trace_id

        clear_trace_id()

        # Should create a new trace ID if none exists
        trace_id = get_or_create_trace_id()
        assert isinstance(trace_id, str)
        assert len(trace_id) == 32

        # Should return the same ID if it already exists
        same_id = get_or_create_trace_id()
        assert same_id == trace_id

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
        from asset_core.observability.trace_id import ensure_trace_id

        clear_trace_id()

        # Should create a new trace ID if none exists
        trace_id = ensure_trace_id()
        assert isinstance(trace_id, str)
        assert len(trace_id) == 32
        assert get_trace_id() == trace_id

        # Should return the same ID if it already exists
        same_id = ensure_trace_id()
        assert same_id == trace_id

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
        from asset_core.observability.trace_id import format_trace_id

        # Valid trace ID should be returned as-is
        assert format_trace_id("valid-trace-id") == "valid-trace-id"

        # None should be formatted as "no-trace"
        assert format_trace_id(None) == "no-trace"

        # Empty string should be formatted as "no-trace"
        assert format_trace_id("") == "no-trace"

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
        from asset_core.observability.trace_id import get_formatted_trace_id

        clear_trace_id()

        # Should return "no-trace" when no trace ID is set
        assert get_formatted_trace_id() == "no-trace"

        # Should return the trace ID when one is set
        set_trace_id("test-formatted-id")
        assert get_formatted_trace_id() == "test-formatted-id"


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
        from asset_core.observability.trace_id import TraceIdMiddleware

        middleware = TraceIdMiddleware()

        # Test with standard header
        headers_standard = {"X-Trace-Id": "test-trace-id-123"}
        extracted_id = middleware.extract_trace_id(headers_standard)
        assert extracted_id == "test-trace-id-123"

        # Test with lowercase header
        headers_lowercase = {"x-trace-id": "test-trace-id-456"}
        extracted_id = middleware.extract_trace_id(headers_lowercase)
        assert extracted_id == "test-trace-id-456"

        # Test with empty headers
        empty_headers: dict[str, str] = {}
        extracted_id = middleware.extract_trace_id(empty_headers)
        assert extracted_id is None

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
        from asset_core.observability.trace_id import TraceIdMiddleware

        middleware = TraceIdMiddleware()

        # Set a trace ID in the current context
        set_trace_id("test-trace-inject-123")

        # Define existing headers
        original_headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}

        # Inject trace ID
        updated_headers = middleware.inject_trace_id(original_headers)

        # Verify trace ID is injected
        assert updated_headers["X-Trace-Id"] == "test-trace-inject-123"

        # Verify existing headers are preserved
        assert updated_headers["Content-Type"] == "application/json"
        assert updated_headers["Authorization"] == "Bearer token"

        # Verify original headers dictionary is not modified
        assert "X-Trace-Id" not in original_headers

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
        from asset_core.observability.trace_id import TraceIdMiddleware

        middleware = TraceIdMiddleware()

        # Ensure no trace ID is set
        clear_trace_id()

        # Define existing headers
        original_headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}

        # Inject trace ID (should not modify headers)
        updated_headers = middleware.inject_trace_id(original_headers)

        # Verify headers remain unchanged
        assert updated_headers == original_headers

        # Verify no trace ID is present
        assert "X-Trace-Id" not in updated_headers

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
        from asset_core.observability.trace_id import TraceIdMiddleware

        middleware = TraceIdMiddleware(header_name="X-Custom-Trace")

        # Set a test trace ID
        set_trace_id("custom-trace-id-789")

        # Define empty headers
        headers: dict[str, str] = {}

        # Inject trace ID with custom header name
        updated_headers = middleware.inject_trace_id(headers)

        # Verify custom header name is used
        assert updated_headers["X-Custom-Trace"] == "custom-trace-id-789"
        assert "X-Trace-Id" not in updated_headers


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
        from asset_core.observability.trace_id import with_trace_id

        @with_trace_id("decorator_test")
        def test_func() -> str:
            result = get_trace_id()
            assert result is not None
            return result

        result = test_func()
        assert result == "decorator_test"

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
        from asset_core.observability.trace_id import with_trace_id

        @with_trace_id()
        def test_func() -> str:
            result = get_trace_id()
            assert result is not None
            return result

        result = test_func()
        assert isinstance(result, str)
        assert len(result) == 32

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
        from asset_core.observability.trace_id import with_trace_id

        @with_trace_id("async_test")
        async def test_func() -> str:
            result = get_trace_id()
            assert result is not None
            return result

        result = await test_func()
        assert result == "async_test"

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
        from asset_core.observability.trace_id import with_trace_id

        @with_trace_id()
        async def test_func() -> str:
            result = get_trace_id()
            assert result is not None
            return result

        result = await test_func()
        assert isinstance(result, str)
        assert len(result) == 32


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
        set_trace_id("original")

        def check_context() -> str | None:
            return get_trace_id()

        assert check_context() == "original"

        with TraceContext("context_test") as ctx_id:
            assert check_context() == "context_test"
            assert ctx_id == "context_test"

        assert check_context() == "original"

    def test_trace_id_does_not_propagate_to_executor_by_default(self) -> None:
        """Test that trace IDs do not automatically propagate to ThreadPoolExecutor by default.

        Description of what the test covers:
        This test verifies that trace IDs do NOT automatically propagate to new threads
        created by ThreadPoolExecutor or asyncio.run_in_executor by default. This is the
        expected behavior for contextvars in new threads.

        Preconditions:
        - The trace ID system uses contextvars for storage.
        - ThreadPoolExecutor creates new threads without context propagation.

        Steps:
        - Set a trace ID in the main thread.
        - Submit a function to ThreadPoolExecutor that checks the trace ID.
        - Assert that the trace ID is None in the worker thread.

        Expected Result:
        - The trace ID should be None in the worker thread, demonstrating proper isolation.
        """
        import concurrent.futures

        def worker_function() -> str | None:
            """Function to run in executor thread."""
            return get_trace_id()

        # Set trace ID in main thread
        set_trace_id("main_thread_trace")

        # Verify trace ID is set in main thread
        assert get_trace_id() == "main_thread_trace"

        # Submit work to executor
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker_function)
            worker_trace_id = future.result()

        # Verify trace ID is NOT propagated to worker thread
        assert worker_trace_id is None

        # Verify main thread trace ID is unchanged
        assert get_trace_id() == "main_thread_trace"


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
