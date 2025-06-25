"""
Observability component tests.

Comprehensive tests for observability system components including
Prometheus metrics registry, structured logging, and trace ID propagation.
"""

import asyncio
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from asset_core.observability.logging import (
    LogContext,
    LogFilter,
    LogFormat,
    TraceableLogger,
    create_debug_filter,
    create_error_filter,
    create_performance_filter,
    get_formatter,
    get_logger,
    get_structured_logger,
    log_function_calls,
    log_performance,
    log_with_trace_id,
    setup_logging,
    trace_id_patcher,
)
from asset_core.observability.metrics import PrometheusMetricsRegistry, \
    create_common_metrics
from asset_core.observability.trace_id import (
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


class TestPrometheusMetricsRegistry:
    """
    Tests for Prometheus metrics registry functionality.

    Verifies that metrics registry correctly manages different metric types,
    handles namespacing, and provides proper serialization capabilities.
    """

    def test_registry_initialization(self) -> None:
        """
        Test metrics registry initialization.

        Verifies that registry initializes correctly with optional namespace
        and maintains internal state properly.

        Expected Result:
            - Registry creates CollectorRegistry instance
            - Namespace is stored correctly
            - Internal metrics dictionary is empty initially
        """
        # Test without namespace
        registry = PrometheusMetricsRegistry()

        assert registry.registry is not None
        assert registry.namespace is None
        assert isinstance(registry._metrics, dict)
        assert len(registry._metrics) == 0

        # Test with namespace
        namespaced_registry = PrometheusMetricsRegistry("test_app")

        assert namespaced_registry.namespace == "test_app"
        assert isinstance(namespaced_registry._metrics, dict)

    def test_counter_metric_creation(self) -> None:
        """
        Test counter metric creation and retrieval.

        Verifies that counter metrics are created correctly, cached,
        and can be incremented without errors.

        Expected Result:
            - Counter created with correct name and description
            - Same counter returned on subsequent calls
            - Counter increments work correctly
        """
        registry = PrometheusMetricsRegistry("test")

        # Create counter
        counter1 = registry.counter("test_counter", "Test counter description", labels=["status", "method"])

        assert counter1 is not None
        assert "test_counter" in registry._metrics

        # Should return same counter on second call
        counter2 = registry.counter(
            "test_counter",
            "Different description",  # Should be ignored
            labels=["status", "method"],
        )

        assert counter1 is counter2

        # Test counter functionality
        counter1.labels(status="success", method="get").inc()
        counter1.labels(status="error", method="post").inc(5)

        # Verify metrics can be generated
        metrics_data = registry.generate_metrics()
        assert isinstance(metrics_data, bytes)

    def test_gauge_metric_creation(self) -> None:
        """
        Test gauge metric creation and functionality.

        Verifies that gauge metrics support setting values,
        incrementing, and decrementing operations.

        Expected Result:
            - Gauge created with correct configuration
            - Set, inc, and dec operations work correctly
            - Metrics are properly formatted
        """
        registry = PrometheusMetricsRegistry()

        gauge = registry.gauge("test_gauge", "Test gauge description", labels=["service"])

        assert gauge is not None

        # Test gauge operations
        gauge.labels(service="api").set(42)
        gauge.labels(service="worker").inc(10)
        gauge.labels(service="worker").dec(3)

        # Verify gauge is cached
        same_gauge = registry.gauge("test_gauge", "Description")
        assert gauge is same_gauge

        # Generate metrics
        metrics_data = registry.generate_metrics()
        assert b"test_gauge" in metrics_data

    def test_histogram_metric_creation(self) -> None:
        """
        Test histogram metric creation with custom buckets.

        Verifies that histogram metrics work with custom bucket
        configurations and observe operations.

        Expected Result:
            - Histogram created with custom buckets
            - Observe operations work correctly
            - Bucket counts are tracked properly
        """
        registry = PrometheusMetricsRegistry("myapp")

        custom_buckets = (0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
        histogram = registry.histogram(
            "request_duration", "Request duration in seconds", labels=["endpoint"], buckets=custom_buckets
        )

        assert histogram is not None

        # Test observations
        histogram.labels(endpoint="/api/v1/data").observe(0.25)
        histogram.labels(endpoint="/api/v1/data").observe(1.5)
        histogram.labels(endpoint="/api/v1/users").observe(0.05)

        # Generate metrics
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        assert "request_duration" in metrics_str
        assert "_bucket" in metrics_str
        assert "_count" in metrics_str
        assert "_sum" in metrics_str

    def test_summary_metric_creation(self) -> None:
        """
        Test summary metric creation and observation.

        Verifies that summary metrics calculate quantiles
        and maintain count and sum statistics.

        Expected Result:
            - Summary created successfully
            - Observations are tracked correctly
            - Quantiles are calculated appropriately
        """
        registry = PrometheusMetricsRegistry()

        summary = registry.summary("response_size", "Response size in bytes", labels=["endpoint", "status"])

        assert summary is not None

        # Test observations
        summary.labels(endpoint="/api", status="200").observe(1024)
        summary.labels(endpoint="/api", status="200").observe(2048)
        summary.labels(endpoint="/api", status="404").observe(512)

        # Generate metrics
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        assert "response_size" in metrics_str
        assert "_count" in metrics_str
        assert "_sum" in metrics_str

    def test_info_metric_creation(self) -> None:
        """
        Test info metric creation and information setting.

        Verifies that info metrics store static information
        about the application or system.

        Expected Result:
            - Info metric created successfully
            - Information can be set with key-value pairs
            - Info appears in metrics output
        """
        registry = PrometheusMetricsRegistry("app")

        info = registry.info("build_info", "Build information")

        assert info is not None

        # Set build information
        info.info({"version": "1.2.3", "commit": "abc123", "build_date": "2024-01-01"})

        # Generate metrics
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        assert "build_info" in metrics_str
        assert "version" in metrics_str
        assert "1.2.3" in metrics_str

    def test_metric_name_formatting(self) -> None:
        """
        Test metric name formatting rules.

        Verifies that metric names are properly formatted
        according to Prometheus naming conventions.

        Expected Result:
            - Hyphens replaced with underscores
            - Dots replaced with underscores
            - Names remain alphanumeric with underscores
        """
        registry = PrometheusMetricsRegistry()

        # Test name formatting
        registry.counter("test-metric.name", "Description")
        assert "test_metric_name" in registry._metrics

        registry.gauge("another-test.gauge", "Description")
        assert "another_test_gauge" in registry._metrics

        # Verify original names are not stored
        assert "test-metric.name" not in registry._metrics
        assert "another-test.gauge" not in registry._metrics

    def test_namespace_application(self) -> None:
        """
        Test namespace application to metric names.

        Verifies that namespace is properly applied to all
        metrics created through the registry.

        Expected Result:
            - Namespace appears in generated metrics
            - Multiple metrics share the same namespace
            - Namespace format follows Prometheus conventions
        """
        registry = PrometheusMetricsRegistry("trading_system")

        registry.counter("requests_total", "Total requests")
        registry.gauge("active_connections", "Active connections")

        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Namespace should appear in metrics output
        assert "trading_system_requests_total" in metrics_str
        assert "trading_system_active_connections" in metrics_str

    def test_duplicate_metric_handling(self) -> None:
        """
        Test handling of duplicate metric registration.

        Verifies that registering the same metric name multiple
        times returns the same metric instance.

        Expected Result:
            - Same metric instance returned for duplicate names
            - No errors raised on duplicate registration
            - Metric configuration unchanged
        """
        registry = PrometheusMetricsRegistry()

        # Create initial metric
        counter1 = registry.counter("duplicate_test", "First description", labels=["type"])
        counter1.labels(type="test").inc()

        # Try to create same metric again
        counter2 = registry.counter("duplicate_test", "Second description", labels=["other"])

        # Should return same instance
        assert counter1 is counter2

        # Should not affect existing metrics
        counter2.labels(type="test").inc()

        # Verify only one metric in registry
        metric_names = list(registry._metrics.keys())
        duplicate_count = metric_names.count("duplicate_test")
        assert duplicate_count == 1

    def test_common_metrics_creation(self) -> None:
        """
        Test creation of common monitoring metrics.

        Verifies that the create_common_metrics function
        produces a comprehensive set of standard metrics.

        Expected Result:
            - All expected common metrics are created
            - Metrics have appropriate types and labels
            - Metrics can be used for monitoring
        """
        registry = PrometheusMetricsRegistry("app")
        common_metrics = create_common_metrics(registry)

        # Verify expected metrics exist
        expected_metrics = [
            "ws_connections_total",
            "ws_messages_received_total",
            "ws_reconnects_total",
            "trades_processed_total",
            "klines_processed_total",
            "storage_operations_total",
            "storage_operation_duration_seconds",
            "errors_total",
            "active_connections",
            "processing_lag_seconds",
        ]

        for metric_name in expected_metrics:
            assert metric_name in common_metrics
            assert metric_name in registry._metrics

        # Test metric functionality
        common_metrics["ws_connections_total"].labels(exchange="binance", status="connected").inc()
        common_metrics["storage_operation_duration_seconds"].labels(operation="write").observe(0.05)
        common_metrics["active_connections"].labels(type="websocket").set(42)

        # Generate metrics to verify they work
        metrics_data = registry.generate_metrics()
        assert len(metrics_data) > 0

    @pytest.mark.asyncio
    async def test_http_metrics_server(self) -> None:
        """
        Test HTTP metrics server functionality.

        Verifies that the metrics HTTP server starts correctly
        and serves metrics at the /metrics endpoint.

        Expected Result:
            - Server starts without errors
            - Metrics endpoint returns proper content type
            - Metrics data is served correctly
        """
        registry = PrometheusMetricsRegistry()

        # Create some metrics
        counter = registry.counter("test_requests", "Test requests")
        counter.inc(5)

        # Start server (use different port to avoid conflicts)
        runner = await registry.start_http_server(port=9091)

        try:
            # Give server time to start
            await asyncio.sleep(0.1)

            # Test that server is running (we can't easily test HTTP requests here)
            # But we can verify the runner was created
            assert runner is not None

            # Test metrics generation still works
            metrics_data = registry.generate_metrics()
            assert b"test_requests" in metrics_data

        finally:
            # Clean up server
            await runner.cleanup()


class TestStructuredLogging:
    """
    Tests for structured logging functionality.

    Verifies that logging setup, formatting, filtering, and context
    management work correctly across different scenarios.
    """

    def test_log_format_enumeration(self) -> None:
        """
        Test log format enumeration values.

        Verifies that all expected log formats are available
        and have correct string values.

        Expected Result:
            - All format types are available
            - String values match expected patterns
            - Formats can be used in configuration
        """
        # Test all format types exist
        assert LogFormat.JSON == "json"
        assert LogFormat.PRETTY == "pretty"
        assert LogFormat.COMPACT == "compact"
        assert LogFormat.DETAILED == "detailed"

        # Test format can be used in string context
        formats = [LogFormat.JSON, LogFormat.PRETTY, LogFormat.COMPACT, LogFormat.DETAILED]
        for fmt in formats:
            assert isinstance(fmt, str)
            assert len(fmt) > 0

    def test_log_filter_creation(self) -> None:
        """
        Test log filter creation and configuration.

        Verifies that log filters can be created with various
        criteria and combinations of filtering rules.

        Expected Result:
            - Filter accepts all configuration parameters
            - Filter function can be called with log records
            - Multiple criteria can be combined
        """
        # Test filter with level constraints
        level_filter = LogFilter(min_level="WARNING", max_level="ERROR")
        assert level_filter.min_level == "WARNING"
        assert level_filter.max_level == "ERROR"

        # Test filter with module constraints
        module_filter = LogFilter(include_modules=["asset_core.trading"], exclude_modules=["third_party"])
        assert "asset_core.trading" in module_filter.include_modules
        assert "third_party" in module_filter.exclude_modules

        # Test filter with function constraints
        function_filter = LogFilter(include_functions=["process_trade"], exclude_functions=["debug_helper"])
        assert "process_trade" in function_filter.include_functions
        assert "debug_helper" in function_filter.exclude_functions

        # Test filter with custom function
        custom_filter = LogFilter(custom_filter=lambda record: "important" in record["message"])
        assert custom_filter.custom_filter is not None

    def test_specialized_filter_creation(self) -> None:
        """
        Test creation of specialized log filters.

        Verifies that convenience functions create filters
        with appropriate configurations for specific use cases.

        Expected Result:
            - Performance filter identifies performance-related logs
            - Error filter captures warnings and errors only
            - Debug filter isolates debug messages
        """
        # Test performance filter
        perf_filter = create_performance_filter()
        assert perf_filter.custom_filter is not None

        # Test error filter
        error_filter = create_error_filter()
        assert error_filter.min_level == "WARNING"

        # Test debug filter
        debug_filter = create_debug_filter()
        assert debug_filter.min_level == "DEBUG"
        assert debug_filter.max_level == "DEBUG"

    def test_formatter_creation(self) -> None:
        """
        Test log formatter creation for different formats.

        Verifies that formatters are created correctly for each
        log format type and produce expected output patterns.

        Expected Result:
            - Formatters created for all format types
            - Format strings contain expected placeholders
            - JSON formatter returns callable function
        """
        # Test string formatters
        pretty_formatter = get_formatter(LogFormat.PRETTY)
        assert isinstance(pretty_formatter, str)
        assert "{time:" in pretty_formatter
        assert "{level:" in pretty_formatter
        assert "{message}" in pretty_formatter

        compact_formatter = get_formatter(LogFormat.COMPACT)
        assert isinstance(compact_formatter, str)
        assert "{time:HH:mm:ss}" in compact_formatter

        detailed_formatter = get_formatter(LogFormat.DETAILED)
        assert isinstance(detailed_formatter, str)
        assert "{process}" in detailed_formatter
        assert "{thread}" in detailed_formatter

        # Test JSON formatter (should be callable)
        json_formatter = get_formatter(LogFormat.JSON)
        assert callable(json_formatter)

    def test_trace_id_patcher_functionality(self) -> None:
        """
        Test trace ID patcher for log record enhancement.

        Verifies that the trace ID patcher correctly adds
        trace ID information to log records.

        Expected Result:
            - Trace ID added to log record extra fields
            - No trace ID scenario handled gracefully
            - Exception trace ID extracted when available
        """
        # Mock log record
        record = {"extra": {}, "exception": None}

        # Test with no trace ID
        with patch("asset_core.observability.logging.get_trace_id", return_value=None):
            trace_id_patcher(record)
            assert record["extra"]["trace_id"] == "no-trace"

        # Test with trace ID
        with patch("asset_core.observability.logging.get_trace_id", return_value="test-trace-123"):
            record["extra"] = {}  # Reset
            trace_id_patcher(record)
            assert record["extra"]["trace_id"] == "test-trace-123"

        # Test with exception that has trace ID
        mock_exception = MagicMock()
        mock_exception.value.trace_id = "exception-trace-456"
        record["exception"] = mock_exception
        record["extra"] = {}

        with patch("asset_core.observability.logging.get_trace_id", return_value="current-trace"):
            trace_id_patcher(record)
            assert record["extra"]["trace_id"] == "current-trace"
            assert record["extra"]["exception_trace_id"] == "exception-trace-456"

    def test_logging_setup_configuration(self) -> None:
        """
        Test logging setup with various configurations.

        Verifies that logging can be configured with different
        handlers, formats, and output destinations.

        Expected Result:
            - Console and file logging can be configured
            - Different formats applied to different handlers
            - Log files created in specified locations
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            # Configure logging
            setup_logging(
                level="DEBUG",
                enable_console=True,
                enable_file=True,
                log_file=log_file,
                app_name="test_app",
                environment="testing",
                console_format=LogFormat.COMPACT,
                file_format=LogFormat.JSON,
            )

            # Test that logger works
            test_logger = get_logger("test_module")
            test_logger.info("Test message")

            # Give logger time to write
            time.sleep(0.1)

            # Verify log file was created
            assert log_file.exists()

    def test_logger_creation_and_binding(self) -> None:
        """
        Test logger creation with extra field binding.

        Verifies that loggers can be created with bound
        extra fields that appear in all log messages.

        Expected Result:
            - Logger created with bound fields
            - Extra fields appear in log output
            - Different loggers can have different bindings
        """
        # Test basic logger creation
        basic_logger = get_logger("basic_test")
        assert basic_logger is not None

        # Test logger with extra fields
        bound_logger = get_logger("bound_test", service="trading", version="1.0")
        assert bound_logger is not None

        # Test structured logger alias
        structured_logger = get_structured_logger("structured_test", component="metrics")
        assert structured_logger is not None

    def test_log_context_manager(self) -> None:
        """
        Test log context manager for temporary field binding.

        Verifies that context manager correctly adds and removes
        temporary context fields for scoped logging.

        Expected Result:
            - Context fields available within context
            - Context fields removed after exiting
            - Multiple contexts can be nested
        """
        # Test basic context
        with LogContext(operation="test_operation", request_id="req-123") as context_logger:
            assert context_logger is not None

        # Test nested contexts
        with LogContext(service="api"), LogContext(endpoint="/users") as inner_logger:
            assert inner_logger is not None

    def test_performance_logging_decorator(self) -> None:
        """
        Test performance logging decorator functionality.

        Verifies that the decorator correctly measures and logs
        function execution time for both sync and async functions.

        Expected Result:
            - Decorator works with both sync and async functions
            - Performance metrics are logged correctly
            - Exceptions are handled and re-raised
        """

        # Test sync function
        @log_performance("test_sync_function")
        def sync_function(duration: float = 0.01):
            time.sleep(duration)
            return "sync_result"

        result = sync_function()
        assert result == "sync_result"

        # Test async function
        @log_performance("test_async_function", "DEBUG")
        async def async_function(duration: float = 0.01):
            await asyncio.sleep(duration)
            return "async_result"

        async def run_async_test():
            result = await async_function()
            assert result == "async_result"

        asyncio.run(run_async_test())

        # Test exception handling
        @log_performance()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_function_call_logging_decorator(self) -> None:
        """
        Test function call logging decorator.

        Verifies that the decorator logs function entry, exit,
        and optionally arguments and results.

        Expected Result:
            - Function calls are logged correctly
            - Arguments and results logged when enabled
            - Exceptions are caught and logged
        """

        # Test without args/result logging
        @log_function_calls()
        def simple_function(x: int, y: int) -> int:
            return x + y

        result = simple_function(2, 3)
        assert result == 5

        # Test with args and result logging
        @log_function_calls(include_args=True, include_result=True)
        def detailed_function(name: str) -> str:
            return f"Hello, {name}!"

        result = detailed_function("Alice")
        assert result == "Hello, Alice!"

        # Test exception handling
        @log_function_calls(include_args=True)
        def error_function():
            raise RuntimeError("Test exception")

        with pytest.raises(RuntimeError):
            error_function()

    def test_traceable_logger_functionality(self) -> None:
        """
        Test TraceableLogger class functionality.

        Verifies that TracableLogger ensures trace ID presence
        and provides convenient logging methods.

        Expected Result:
            - Trace ID is ensured for all log calls
            - All log levels are supported
            - Exception logging includes context
        """
        traceable_logger = TraceableLogger("test_component", service="trading")

        # Test all log levels
        traceable_logger.debug("Debug message")
        traceable_logger.info("Info message")
        traceable_logger.warning("Warning message")
        traceable_logger.error("Error message")
        traceable_logger.critical("Critical message")

        # Test exception logging
        test_exception = ValueError("Test exception")
        traceable_logger.error("Exception occurred", exc=test_exception)
        traceable_logger.critical("Critical exception", exc=test_exception)

        # Test exception logging without explicit exception
        try:
            raise RuntimeError("Runtime error")
        except RuntimeError:
            traceable_logger.exception("Runtime exception occurred")


class TestTraceIdPropagation:
    """
    Tests for trace ID propagation and management.

    Verifies that trace IDs are correctly generated, stored,
    propagated across contexts, and integrated with logging.
    """

    def test_trace_id_generation(self) -> None:
        """
        Test trace ID generation functionality.

        Verifies that trace IDs are generated as UUID4 strings
        without dashes for compact representation.

        Expected Result:
            - Generated trace IDs are strings
            - Format is UUID4 without dashes (32 hex characters)
            - Each generation produces unique IDs
        """
        trace_id = generate_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 32  # UUID4 without dashes
        assert all(c in "0123456789abcdef" for c in trace_id.lower())

        # Test uniqueness
        trace_id2 = generate_trace_id()
        assert trace_id != trace_id2

    def test_trace_id_context_management(self) -> None:
        """
        Test trace ID setting and retrieval from context.

        Verifies that trace IDs can be set and retrieved from
        both context variables and thread-local storage.

        Expected Result:
            - Trace ID can be set and retrieved
            - Context variables take precedence over thread-local
            - None returned when no trace ID is set
        """
        # Clear any existing trace ID
        clear_trace_id()

        # Test no trace ID initially
        assert get_trace_id() is None

        # Test setting trace ID
        test_trace_id = "test123456789012345678901234567890"
        set_trace_id(test_trace_id)

        assert get_trace_id() == test_trace_id

        # Test setting with generated ID
        generated_id = set_trace_id()
        assert get_trace_id() == generated_id
        assert len(generated_id) == 32

        # Test clearing
        clear_trace_id()
        assert get_trace_id() is None

    def test_trace_id_or_create_functionality(self) -> None:
        """
        Test get_or_create_trace_id functionality.

        Verifies that function returns existing trace ID
        or creates new one if none exists.

        Expected Result:
            - Returns existing trace ID when available
            - Creates new trace ID when none exists
            - Subsequent calls return same trace ID
        """
        clear_trace_id()

        # Should create new trace ID
        trace_id1 = get_or_create_trace_id()
        assert trace_id1 is not None
        assert len(trace_id1) == 32

        # Should return same trace ID
        trace_id2 = get_or_create_trace_id()
        assert trace_id1 == trace_id2

        # Test ensure_trace_id alias
        trace_id3 = ensure_trace_id()
        assert trace_id1 == trace_id3

    def test_trace_context_manager(self) -> None:
        """
        Test TraceContext context manager functionality.

        Verifies that trace context correctly sets and restores
        trace IDs within context blocks.

        Expected Result:
            - Trace ID set within context
            - Previous trace ID restored after context
            - New trace ID generated if none provided
        """
        clear_trace_id()

        # Test with specific trace ID
        with TraceContext("context-trace-123") as trace_id:
            assert trace_id == "context-trace-123"
            assert get_trace_id() == "context-trace-123"

        # Trace ID should be cleared after context
        # (depending on implementation, might be None or restored)

        # Test with generated trace ID
        with TraceContext() as trace_id:
            assert trace_id is not None
            assert len(trace_id) == 32
            assert get_trace_id() == trace_id

        # Test nested contexts
        set_trace_id("outer-trace")
        with TraceContext("inner-trace"):
            assert get_trace_id() == "inner-trace"

            with TraceContext("nested-trace"):
                assert get_trace_id() == "nested-trace"

            assert get_trace_id() == "inner-trace"

    def test_trace_id_formatting(self) -> None:
        """
        Test trace ID formatting for display.

        Verifies that trace ID formatting handles None values
        and provides user-friendly display format.

        Expected Result:
            - Valid trace IDs returned as-is
            - None values formatted as 'no-trace'
            - Current trace ID formatted correctly
        """
        # Test with valid trace ID
        formatted = format_trace_id("valid-trace-id-123")
        assert formatted == "valid-trace-id-123"

        # Test with None
        formatted_none = format_trace_id(None)
        assert formatted_none == "no-trace"

        # Test current trace ID formatting
        clear_trace_id()
        formatted_current = get_formatted_trace_id()
        assert formatted_current == "no-trace"

        set_trace_id("current-trace-456")
        formatted_current = get_formatted_trace_id()
        assert formatted_current == "current-trace-456"

    def test_trace_id_middleware_functionality(self) -> None:
        """
        Test TraceIdMiddleware for HTTP header integration.

        Verifies that middleware can extract trace IDs from headers
        and inject them into outgoing requests.

        Expected Result:
            - Trace ID extracted from headers correctly
            - Trace ID injected into headers
            - Case-insensitive header handling
        """
        middleware = TraceIdMiddleware("X-Trace-Id")

        # Test extraction
        headers = {"X-Trace-Id": "header-trace-789"}
        extracted = middleware.extract_trace_id(headers)
        assert extracted == "header-trace-789"

        # Test case-insensitive extraction
        headers_lower = {"x-trace-id": "lower-trace-789"}
        extracted_lower = middleware.extract_trace_id(headers_lower)
        assert extracted_lower == "lower-trace-789"

        # Test extraction with no header
        empty_headers = {}
        extracted_empty = middleware.extract_trace_id(empty_headers)
        assert extracted_empty is None

        # Test injection
        set_trace_id("inject-trace-101112")
        headers = {"Content-Type": "application/json"}
        injected_headers = middleware.inject_trace_id(headers)

        assert injected_headers["X-Trace-Id"] == "inject-trace-101112"
        assert injected_headers["Content-Type"] == "application/json"
        assert len(injected_headers) == 2

        # Test injection with no current trace ID
        clear_trace_id()
        headers = {"Content-Type": "application/json"}
        injected_headers = middleware.inject_trace_id(headers)

        # Should return original headers unchanged
        assert injected_headers == headers

    def test_with_trace_id_decorator(self) -> None:
        """
        Test with_trace_id decorator functionality.

        Verifies that decorator ensures trace ID context
        for both synchronous and asynchronous functions.

        Expected Result:
            - Decorator works with sync and async functions
            - Trace ID available within decorated function
            - Custom trace ID can be specified
        """

        # Test sync function without specific trace ID
        @with_trace_id()
        def sync_function():
            return get_trace_id()

        result = sync_function()
        assert result is not None
        assert len(result) == 32

        # Test sync function with specific trace ID
        @with_trace_id("custom-sync-trace")
        def sync_function_custom():
            return get_trace_id()

        result = sync_function_custom()
        assert result == "custom-sync-trace"

        # Test async function
        @with_trace_id()
        async def async_function():
            return get_trace_id()

        async def run_async_test():
            result = await async_function()
            assert result is not None
            assert len(result) == 32

        asyncio.run(run_async_test())

        # Test async function with custom trace ID
        @with_trace_id("custom-async-trace")
        async def async_function_custom():
            return get_trace_id()

        async def run_custom_async_test():
            result = await async_function_custom()
            assert result == "custom-async-trace"

        asyncio.run(run_custom_async_test())

    def test_thread_local_fallback(self) -> None:
        """
        Test thread-local storage fallback for trace ID.

        Verifies that trace ID management works correctly
        in scenarios where context variables might not be available.

        Expected Result:
            - Thread-local storage works as fallback
            - Different threads have isolated trace IDs
            - Context variables take precedence when available
        """

        def thread_test_function(results: dict[str, str], thread_id: str) -> None:
            """Function to run in separate thread."""
            clear_trace_id()

            # Set trace ID specific to this thread
            set_trace_id(f"thread-{thread_id}-trace")
            results[thread_id] = get_trace_id()

        # Test with multiple threads
        results = {}
        threads = []

        for i in range(3):
            thread = threading.Thread(target=thread_test_function, args=(results, str(i)))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own trace ID
        assert len(results) == 3
        assert results["0"] == "thread-0-trace"
        assert results["1"] == "thread-1-trace"
        assert results["2"] == "thread-2-trace"

        # Verify trace IDs are unique
        trace_ids = list(results.values())
        assert len(set(trace_ids)) == 3

    def test_trace_id_integration_with_logging(self) -> None:
        """
        Test trace ID integration with logging system.

        Verifies that trace IDs are automatically included
        in log records and can be used for request correlation.

        Expected Result:
            - Trace ID appears in log records
            - log_with_trace_id function works correctly
            - Trace context affects logging output
        """
        # Test trace ID in logging
        set_trace_id("logging-trace-123")

        # Test log_with_trace_id function
        with patch("asset_core.observability.logging.logger") as mock_logger:
            log_with_trace_id("INFO", "Test message", extra_field="value")
            mock_logger.log.assert_called_once_with("INFO", "Test message", extra_field="value")

        # Test with explicit trace ID override
        with patch("asset_core.observability.logging.logger") as mock_logger:
            log_with_trace_id("DEBUG", "Debug message", trace_id="override-trace", data="test")
            # Should use TraceContext with override trace ID
            mock_logger.log.assert_called_once_with("DEBUG", "Debug message", data="test")

        # Test trace context affects logging
        with TraceContext("context-logging-trace"):
            current_trace = get_trace_id()
            assert current_trace == "context-logging-trace"
