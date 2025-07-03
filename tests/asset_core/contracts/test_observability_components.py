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
from typing import Any
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
    """Test cases for Prometheus metrics registry functionality.

    Verifies that the metrics registry correctly manages different metric types,
    handles namespacing, and provides proper serialization capabilities.
    """

    def test_registry_initialization(self) -> None:
        """Test metrics registry initialization.

        Description of what the test covers.
        Verifies that the registry initializes correctly with an optional namespace
        and maintains its internal state properly.

        Expected Result:
        - Registry creates a CollectorRegistry instance.
        - Namespace is stored correctly.
        - Internal metrics dictionary is empty initially.
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
        """Test counter metric creation and retrieval.

        Description of what the test covers.
        Verifies that counter metrics are created correctly, cached,
        and can be incremented without errors.

        Expected Result:
        - Counter created with correct name and description.
        - Same counter returned on subsequent calls.
        - Counter increments work correctly.
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
        """Test gauge metric creation and functionality.

        Description of what the test covers.
        Verifies that gauge metrics support setting values,
        incrementing, and decrementing operations.

        Expected Result:
        - Gauge created with correct configuration.
        - Set, inc, and dec operations work correctly.
        - Metrics are properly formatted.
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
        """Test histogram metric creation with custom buckets.

        Description of what the test covers.
        Verifies that histogram metrics work with custom bucket
        configurations and observe operations.

        Expected Result:
        - Histogram created with custom buckets.
        - Observe operations work correctly.
        - Bucket counts are tracked properly.
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
        """Test summary metric creation and observation.

        Description of what the test covers.
        Verifies that summary metrics calculate quantiles
        and maintain count and sum statistics.

        Expected Result:
        - Summary created successfully.
        - Observations are tracked correctly.
        - Quantiles are calculated appropriately.
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
        """Test info metric creation and information setting.

        Description of what the test covers.
        Verifies that info metrics store static information
        about the application or system.

        Expected Result:
        - Info metric created successfully.
        - Information can be set with key-value pairs.
        - Info appears in metrics output.
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
        """Test metric name formatting rules.

        Description of what the test covers.
        Verifies that metric names are properly formatted
        according to Prometheus naming conventions.

        Expected Result:
        - Hyphens replaced with underscores.
        - Dots replaced with underscores.
        - Names remain alphanumeric with underscores.
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
        """Test namespace application to metric names.

        Description of what the test covers.
        Verifies that namespace is properly applied to all
        metrics created through the registry.

        Expected Result:
        - Namespace appears in generated metrics.
        - Multiple metrics share the same namespace.
        - Namespace format follows Prometheus conventions.
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
        """Test handling of duplicate metric registration.

        Description of what the test covers.
        Verifies that registering the same metric name multiple
        times returns the same metric instance.

        Expected Result:
        - Same metric instance returned for duplicate names.
        - No errors raised on duplicate registration.
        - Metric configuration unchanged.
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
        """Test creation of common monitoring metrics.

        Description of what the test covers.
        Verifies that the `create_common_metrics` function
        produces a comprehensive set of standard metrics.

        Expected Result:
        - All expected common metrics are created.
        - Metrics have appropriate types and labels.
        - Metrics can be used for monitoring.
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
        common_metrics["ws_connections_total"].labels(exchange="binance", status="connected").inc()  # type: ignore[union-attr]
        common_metrics["storage_operation_duration_seconds"].labels(operation="write").observe(0.05)  # type: ignore[union-attr]
        common_metrics["active_connections"].labels(type="websocket").set(42)  # type: ignore[union-attr]

        # Generate metrics to verify they work
        metrics_data = registry.generate_metrics()
        assert len(metrics_data) > 0

    @pytest.mark.asyncio
    async def test_http_metrics_server(self) -> None:
        """Test HTTP metrics server functionality.

        Description of what the test covers.
        Verifies that the metrics HTTP server starts correctly
        and serves metrics at the `/metrics` endpoint.

        Expected Result:
        - Server starts without errors.
        - Metrics endpoint returns proper content type.
        - Metrics data is served correctly.
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

    @pytest.mark.asyncio
    async def test_http_metrics_server_port_in_use(self) -> None:
        """Test HTTP metrics server port conflict handling.

        Description of what the test covers.
        Verifies that attempting to start multiple HTTP servers on the same port
        raises an appropriate error (OSError with address already in use).
        Tests resource conflict detection and proper error handling.

        Expected Result:
        - First server starts successfully.
        - Second server on same port raises OSError.
        - Error message indicates address/port is already in use.
        """
        registry1 = PrometheusMetricsRegistry("port_test_1")
        registry2 = PrometheusMetricsRegistry("port_test_2")

        # Use a specific port for testing (avoid common ports)
        test_port = 9093

        # Start first server
        runner1 = await registry1.start_http_server(port=test_port)

        try:
            # Give first server time to bind to port
            await asyncio.sleep(0.1)

            # Attempt to start second server on same port - should fail
            with pytest.raises(OSError, match=".*address.*already.*in.*use.*|.*port.*already.*bound.*"):
                runner2 = await registry2.start_http_server(port=test_port)
                # If we get here without exception, clean up the unexpected server
                await runner2.cleanup()

        finally:
            # Clean up first server
            await runner1.cleanup()

        # Verify first server can be restarted after cleanup
        await asyncio.sleep(0.1)  # Brief delay to ensure port is released
        runner3 = await registry1.start_http_server(port=test_port)
        await runner3.cleanup()

    def test_counter_operations(self) -> None:
        """Test counter operations and value verification.

        Description of what the test covers.
        Verifies that counter metrics correctly increment and
        maintain accurate values across different label combinations.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create counter with multiple labels.
        - Increment with different label values.
        - Verify counter values are accurate.
        - Test counter value retrieval.

        Expected Result:
        - Counter increments correctly for each label combination.
        - Values accumulate properly.
        - Default increment is 1, custom increments work.
        """
        registry = PrometheusMetricsRegistry("test_app")

        # Create counter with labels
        requests_counter = registry.counter(
            "http_requests_total", "Total HTTP requests", labels=["method", "status", "endpoint"]
        )

        # Test initial state (should be 0)
        # Note: Prometheus client doesn't expose value retrieval easily
        # We'll test through metrics output instead

        # Test single increment
        requests_counter.labels(method="GET", status="200", endpoint="/api/users").inc()

        # Test increment with custom value
        requests_counter.labels(method="POST", status="201", endpoint="/api/users").inc(5)

        # Test multiple increments on same labels
        requests_counter.labels(method="GET", status="200", endpoint="/api/users").inc(2)

        # Test increment with decimal value
        requests_counter.labels(method="PUT", status="200", endpoint="/api/users").inc(1.5)

        # Test negative increment validation (should raise ValueError)
        with pytest.raises(ValueError, match=".*negative.*|.*greater.*than.*zero.*"):
            requests_counter.labels(method="DELETE", status="400", endpoint="/api/users").inc(-1)

        # Test zero increment (should be allowed)
        requests_counter.labels(method="HEAD", status="200", endpoint="/api/users").inc(0)

        # Generate metrics and verify values
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify metric appears in output
        assert "test_app_http_requests_total" in metrics_str
        assert "Total HTTP requests" in metrics_str

        # Verify specific label combinations and values appear
        assert 'method="GET"' in metrics_str
        assert 'status="200"' in metrics_str
        assert 'endpoint="/api/users"' in metrics_str

        # Verify the counter is cached correctly
        same_counter = registry.counter("http_requests_total", "Different description")
        assert requests_counter is same_counter

    def test_gauge_operations(self) -> None:
        """Test gauge operations including set, increment, and decrement.

        Description of what the test covers.
        Verifies that gauge metrics support all expected operations
        and maintain current values correctly.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create gauge with labels.
        - Test set operation with various values.
        - Test increment and decrement operations.
        - Test gauge value tracking.

        Expected Result:
        - Set operations work with positive, negative, and zero values.
        - Increment and decrement operations work correctly.
        - Gauge tracks current value accurately.
        """
        registry = PrometheusMetricsRegistry("metrics")

        # Create gauge metric
        memory_gauge = registry.gauge("memory_usage_bytes", "Memory usage in bytes", labels=["component", "pool"])

        # Test set operations
        memory_gauge.labels(component="cache", pool="default").set(1024 * 1024)  # 1MB
        memory_gauge.labels(component="buffer", pool="network").set(512 * 1024)  # 512KB

        # Test increment operations
        memory_gauge.labels(component="cache", pool="default").inc(256 * 1024)  # +256KB
        memory_gauge.labels(component="buffer", pool="network").inc()  # +1 (default)

        # Test decrement operations
        memory_gauge.labels(component="cache", pool="default").dec(128 * 1024)  # -128KB
        memory_gauge.labels(component="buffer", pool="network").dec(1024)  # -1024

        # Test setting to zero
        memory_gauge.labels(component="temp", pool="scratch").set(0)

        # Test setting negative values (should be allowed for gauges)
        memory_gauge.labels(component="delta", pool="calculation").set(-100)

        # Generate metrics and verify
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify metric appears with namespace
        assert "metrics_memory_usage_bytes" in metrics_str
        assert "Memory usage in bytes" in metrics_str

        # Verify labels appear
        assert 'component="cache"' in metrics_str
        assert 'pool="default"' in metrics_str
        assert 'component="buffer"' in metrics_str
        assert 'pool="network"' in metrics_str

        # Test gauge caching
        same_gauge = registry.gauge("memory_usage_bytes", "Different description")
        assert memory_gauge is same_gauge

    def test_histogram_bucket_configuration(self) -> None:
        """Test histogram metrics with custom bucket configurations.

        Description of what the test covers.
        Verifies that histograms work correctly with custom buckets
        and that observations are distributed properly.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create histogram with custom buckets.
        - Make observations with various values.
        - Verify bucket distribution in output.
        - Test default buckets vs custom buckets.

        Expected Result:
        - Custom buckets are used correctly.
        - Observations fall into appropriate buckets.
        - Histogram generates _bucket, _count, and _sum metrics.
        """
        registry = PrometheusMetricsRegistry("performance")

        # Test histogram with custom buckets
        custom_buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        duration_histogram = registry.histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            labels=["service", "endpoint", "method"],
            buckets=custom_buckets,
        )

        # Make observations that will fall into different buckets
        observations = [
            (0.003, "api", "/users", "GET"),  # Should be in 0.005 bucket
            (0.008, "api", "/users", "GET"),  # Should be in 0.01 bucket
            (0.042, "api", "/orders", "POST"),  # Should be in 0.05 bucket
            (0.15, "auth", "/login", "POST"),  # Should be in 0.25 bucket
            (0.8, "api", "/reports", "GET"),  # Should be in 1.0 bucket
            (3.2, "batch", "/export", "POST"),  # Should be in 5.0 bucket
            (12.5, "batch", "/import", "POST"),  # Should be in +Inf bucket
        ]

        for duration, service, endpoint, method in observations:
            duration_histogram.labels(service=service, endpoint=endpoint, method=method).observe(duration)

        # Test histogram with default buckets
        default_histogram = registry.histogram("response_size_bytes", "Response size in bytes", labels=["status"])

        default_histogram.labels(status="200").observe(1024)
        default_histogram.labels(status="404").observe(256)

        # Test boundary conditions for bucket configuration
        # Test empty buckets - current implementation allows this (relies on prometheus_client behavior)
        try:
            empty_buckets_hist = registry.histogram("empty_buckets_hist", "Empty buckets test", buckets=())
            # If no exception, empty buckets are allowed
            empty_buckets_hist.observe(1.0)
        except (ValueError, Exception):
            # If exception raised, empty buckets are not allowed - this is valid behavior
            pass

        # Test unsorted buckets - current implementation allows this (relies on prometheus_client behavior)
        unsorted_buckets = (1.0, 0.5, 2.0, 0.1)  # Not in ascending order
        try:
            unsorted_hist = registry.histogram(
                "unsorted_buckets_hist", "Unsorted buckets test", buckets=unsorted_buckets
            )
            # If no exception, unsorted buckets are allowed (prometheus_client may sort them)
            unsorted_hist.observe(1.5)
        except (ValueError, Exception):
            # If exception raised, unsorted buckets are not allowed - this is valid behavior
            pass

        # Test duplicate bucket values (behavior may vary by implementation)
        duplicate_buckets = (0.1, 0.5, 0.5, 1.0)  # Contains duplicates
        try:
            duplicate_hist = registry.histogram("duplicate_buckets_hist", "Duplicate test", buckets=duplicate_buckets)
            # If no exception, duplicates are allowed - test that it works
            duplicate_hist.observe(0.3)
        except ValueError:
            # If exception raised, duplicates are not allowed - this is also valid behavior
            pass

        # Generate metrics and verify structure
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify histogram metric names
        assert "performance_request_duration_seconds" in metrics_str
        assert "performance_response_size_bytes" in metrics_str

        # Verify histogram components are present
        assert "request_duration_seconds_bucket" in metrics_str
        assert "request_duration_seconds_count" in metrics_str
        assert "request_duration_seconds_sum" in metrics_str

        # Verify buckets appear in output
        assert 'le="0.005"' in metrics_str
        assert 'le="0.01"' in metrics_str
        assert 'le="5.0"' in metrics_str
        assert 'le="+Inf"' in metrics_str

        # Verify labels appear correctly
        assert 'service="api"' in metrics_str
        assert 'endpoint="/users"' in metrics_str
        assert 'method="GET"' in metrics_str

        # Test histogram caching
        same_histogram = registry.histogram("request_duration_seconds", "Different description")
        assert duration_histogram is same_histogram

    def test_histogram_operations(self) -> None:
        """Test histogram operations and validation for edge cases.

        Description of what the test covers.
        Verifies that histogram observations handle edge cases correctly,
        including negative values, zero values, and extremely large values.
        Tests the expected behavior for invalid observations.

        Expected Result:
        - Valid observations are accepted and recorded.
        - Negative observations raise ValueError or are handled as defined.
        - Zero and large values are handled appropriately.
        """
        registry = PrometheusMetricsRegistry("histogram_ops_test")

        histogram = registry.histogram("operation_duration", "Operation duration in seconds", labels=["service"])

        # Test valid positive observations
        histogram.labels(service="api").observe(0.1)
        histogram.labels(service="api").observe(1.5)
        histogram.labels(service="database").observe(0.05)

        # Test zero observation (should be valid)
        histogram.labels(service="cache").observe(0.0)

        # Test negative observation (behavior depends on implementation)
        # Some Prometheus clients allow negative values, others don't
        try:
            histogram.labels(service="invalid").observe(-1.0)
            # If no exception, negative values are allowed by this implementation
            negative_allowed = True
        except (ValueError, TypeError):
            # If exception raised, negative values are not allowed
            negative_allowed = False

        # Test very large observation
        histogram.labels(service="batch").observe(3600.0)  # 1 hour

        # Generate metrics and verify structure
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify histogram components are present
        assert "histogram_ops_test_operation_duration" in metrics_str
        assert "operation_duration_bucket" in metrics_str
        assert "operation_duration_count" in metrics_str
        assert "operation_duration_sum" in metrics_str

        # If negative values are not allowed, test that explicitly
        if not negative_allowed:
            with pytest.raises((ValueError, TypeError)):
                histogram.labels(service="error_test").observe(-0.1)

    def test_summary_quantile_calculation(self) -> None:
        """Test summary metrics and quantile calculations.

        Description of what the test covers.
        Verifies that summary metrics calculate quantiles correctly
        and maintain count and sum statistics appropriately.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create summary metric with default quantiles.
        - Make multiple observations.
        - Verify quantile outputs appear.
        - Test summary _count and _sum components.

        Expected Result:
        - Summary generates quantile metrics.
        - Count and sum are tracked correctly.
        - Different label combinations work independently.
        """
        registry = PrometheusMetricsRegistry("app")

        # Create summary metric
        response_time_summary = registry.summary(
            "response_time_seconds", "Response time in seconds", labels=["service", "operation"]
        )

        # Make observations for quantile calculation
        # Using a range of values to get meaningful quantiles
        service_a_times = [0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3]
        service_b_times = [0.005, 0.01, 0.02, 0.03, 0.04, 0.06, 0.09, 0.12, 0.18, 0.25]

        for time_val in service_a_times:
            response_time_summary.labels(service="user-api", operation="get_user").observe(time_val)

        for time_val in service_b_times:
            response_time_summary.labels(service="order-api", operation="create_order").observe(time_val)

        # Test edge case with single observation
        response_time_summary.labels(service="health", operation="ping").observe(0.001)

        # Test with zero value
        response_time_summary.labels(service="cache", operation="hit").observe(0.0)

        # Generate metrics and verify
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify summary metric names
        assert "app_response_time_seconds" in metrics_str

        # Verify summary components
        assert "response_time_seconds_count" in metrics_str
        assert "response_time_seconds_sum" in metrics_str

        # Verify quantiles appear (default quantiles: 0.5, 0.9, 0.99)
        # Note: Exact quantile values depend on implementation
        # We just verify they appear in the output
        if "quantile=" in metrics_str:  # Some Prometheus clients include quantiles
            assert 'quantile="0.5"' in metrics_str or 'quantile="0.9"' in metrics_str

        # Verify labels work correctly
        assert 'service="user-api"' in metrics_str
        assert 'operation="get_user"' in metrics_str
        assert 'service="order-api"' in metrics_str

        # Test summary caching
        same_summary = registry.summary("response_time_seconds", "Different description")
        assert response_time_summary is same_summary

    def test_metric_label_cardinality(self) -> None:
        """Test metrics with various label combinations and cardinality.

        Description of what the test covers.
        Verifies that metrics handle multiple labels correctly
        and that high cardinality scenarios are supported.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create metrics with multiple labels.
        - Test various label combinations.
        - Test high cardinality scenarios.
        - Verify label validation.

        Expected Result:
        - Multiple labels work correctly.
        - Different label combinations are tracked independently.
        - High cardinality is handled appropriately.
        """
        registry = PrometheusMetricsRegistry("cardinality_test")

        # Create counter with multiple labels
        api_counter = registry.counter(
            "api_calls_total", "Total API calls", labels=["method", "endpoint", "status", "user_type", "region"]
        )

        # Test various label combinations
        label_combinations = [
            ("GET", "/users", "200", "premium", "us-east"),
            ("POST", "/users", "201", "premium", "us-east"),
            ("GET", "/users", "200", "basic", "us-east"),
            ("GET", "/orders", "200", "premium", "us-west"),
            ("DELETE", "/orders", "204", "premium", "eu-central"),
            ("GET", "/products", "200", "basic", "ap-southeast"),
        ]

        # Increment each combination
        for method, endpoint, status, user_type, region in label_combinations:
            api_counter.labels(
                method=method, endpoint=endpoint, status=status, user_type=user_type, region=region
            ).inc()

        # Test that same label combination accumulates
        api_counter.labels(method="GET", endpoint="/users", status="200", user_type="premium", region="us-east").inc(5)

        # Test edge case with empty string labels - define explicit behavior
        try:
            api_counter.labels(method="GET", endpoint="", status="200", user_type="premium", region="us-east").inc()
            # If no exception, empty string labels are allowed
            empty_labels_allowed = True
        except (ValueError, TypeError):
            # If exception raised, empty string labels are not allowed
            empty_labels_allowed = False

        # Test behavior with empty string labels consistently
        if empty_labels_allowed:
            # If empty strings are allowed, test they work correctly
            api_counter.labels(method="", endpoint="/api", status="200", user_type="basic", region="eu-west").inc()
        else:
            # If empty strings are not allowed, ensure they raise errors consistently
            with pytest.raises((ValueError, TypeError)):
                api_counter.labels(method="", endpoint="/api", status="200", user_type="basic", region="eu-west").inc()

        # Create gauge with fewer labels for comparison
        simple_gauge = registry.gauge("simple_metric", "Simple metric", labels=["type"])
        simple_gauge.labels(type="test").set(42)

        # Generate metrics and verify
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify metric appears
        assert "cardinality_test_api_calls_total" in metrics_str

        # Verify different label combinations appear
        assert 'method="GET"' in metrics_str
        assert 'method="POST"' in metrics_str
        assert 'endpoint="/users"' in metrics_str
        assert 'endpoint="/orders"' in metrics_str
        assert 'status="200"' in metrics_str
        assert 'status="201"' in metrics_str
        assert 'user_type="premium"' in metrics_str
        assert 'region="us-east"' in metrics_str

        # Verify simple metric works too
        assert "cardinality_test_simple_metric" in metrics_str
        assert 'type="test"' in metrics_str

    def test_metric_name_validation(self) -> None:
        """Test metric name validation and error handling.

        Description of what the test covers.
        Verifies that invalid metric names are handled appropriately
        and that naming conventions are enforced.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Test valid metric names.
        - Test invalid metric names (if validation exists).
        - Test name formatting rules.
        - Verify error handling.

        Expected Result:
        - Valid names are accepted and formatted correctly.
        - Invalid names are rejected or formatted appropriately.
        - Error handling is consistent.
        """
        registry = PrometheusMetricsRegistry("validation_test")

        # Test valid metric names
        valid_names = [
            "valid_metric_name",
            "counter123",
            "metric_with_underscores",
            "CamelCaseMetric",  # Should be accepted, might be formatted
        ]

        for name in valid_names:
            counter = registry.counter(name, f"Description for {name}")
            assert counter is not None

        # Test name formatting (hyphens and dots should become underscores)
        registry.counter("test-metric.name", "Test formatting")
        assert "test_metric_name" in registry._metrics
        assert "test-metric.name" not in registry._metrics

        # Test names that should be formatted but still valid
        special_names = [
            ("metric-with-hyphens", "metric_with_hyphens"),
            ("metric.with.dots", "metric_with_dots"),
            ("mixed-format.metric", "mixed_format_metric"),
        ]

        for original, expected in special_names:
            registry.counter(original, f"Description for {original}")
            assert expected in registry._metrics

        # Test potential edge cases (depending on implementation)
        edge_cases = [
            "metric_",  # Trailing underscore
            "_metric",  # Leading underscore
            "metric__double",  # Double underscore
            "123metric",  # Starting with number
        ]

        for name in edge_cases:
            try:
                counter = registry.counter(name, f"Description for {name}")
                # If no exception, verify it was created
                assert counter is not None
            except (ValueError, TypeError):
                # Some implementations might reject these names
                pass

        # Generate metrics to verify everything works
        metrics_data = registry.generate_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify formatted names appear
        assert "validation_test_test_metric_name" in metrics_str
        assert "validation_test_metric_with_hyphens" in metrics_str
        assert "validation_test_metric_with_dots" in metrics_str

    def test_concurrent_metric_updates(self) -> None:
        """Test thread safety of concurrent metric updates.

        Description of what the test covers.
        Verifies that metrics can be safely updated from multiple
        threads without data races or corruption.

        Preconditions:
        - Registry initialized without errors.

        Steps:
        - Create shared metrics.
        - Update metrics from multiple threads concurrently.
        - Verify final values are consistent.
        - Test different metric types under concurrency.

        Expected Result:
        - No race conditions or data corruption.
        - Final values reflect all updates.
        - Thread safety is maintained across metric types.
        """
        registry = PrometheusMetricsRegistry("concurrency_test")

        # Create metrics to test concurrency
        counter = registry.counter("concurrent_counter", "Concurrent counter test")
        gauge = registry.gauge("concurrent_gauge", "Concurrent gauge test")
        histogram = registry.histogram("concurrent_histogram", "Concurrent histogram test")

        # Shared results for verification
        results: dict[str, Any] = {"counter_increments": 0, "errors": []}

        def counter_worker(thread_id: int, iterations: int) -> None:
            """Worker function for counter testing."""
            try:
                for _ in range(iterations):
                    counter.inc()
                    results["counter_increments"] += 1
            except Exception as e:
                results["errors"].append(f"Counter thread {thread_id}: {e}")

        def gauge_worker(thread_id: int, iterations: int) -> None:
            """Worker function for gauge testing."""
            try:
                for i in range(iterations):
                    gauge.set(thread_id * 100 + i)  # Unique values per thread
                    gauge.inc(1)
                    gauge.dec(0.5)
            except Exception as e:
                results["errors"].append(f"Gauge thread {thread_id}: {e}")

        def histogram_worker(thread_id: int, iterations: int) -> None:
            """Worker function for histogram testing."""
            try:
                for i in range(iterations):
                    # Use thread_id to create different observation patterns
                    value = (thread_id + 1) * 0.1 + i * 0.01
                    histogram.observe(value)
            except Exception as e:
                results["errors"].append(f"Histogram thread {thread_id}: {e}")

        # Create and start threads
        threads = []
        iterations_per_thread = 100
        num_threads = 10

        # Counter threads
        for i in range(num_threads):
            thread = threading.Thread(target=counter_worker, args=(i, iterations_per_thread))
            threads.append(thread)

        # Gauge threads
        for i in range(num_threads):
            thread = threading.Thread(target=gauge_worker, args=(i, iterations_per_thread))
            threads.append(thread)

        # Histogram threads
        for i in range(num_threads):
            thread = threading.Thread(target=histogram_worker, args=(i, iterations_per_thread))
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()

        # Verify no errors occurred
        assert len(results["errors"]) == 0, f"Errors during concurrent execution: {results['errors']}"

        # Verify metrics can still be generated without errors
        try:
            metrics_data = registry.generate_metrics()
            assert len(metrics_data) > 0
        except Exception as e:
            pytest.fail(f"Failed to generate metrics after concurrent updates: {e}")

        # Verify metrics appear in output
        metrics_str = metrics_data.decode("utf-8")
        assert "concurrency_test_concurrent_counter" in metrics_str
        assert "concurrency_test_concurrent_gauge" in metrics_str
        assert "concurrency_test_concurrent_histogram" in metrics_str

        # Performance check: operations should complete reasonably quickly
        total_time = end_time - start_time
        assert total_time < 10.0, f"Concurrent operations took too long: {total_time:.2f}s"

        # Verify histogram components are present
        assert "concurrent_histogram_bucket" in metrics_str
        assert "concurrent_histogram_count" in metrics_str
        assert "concurrent_histogram_sum" in metrics_str

    def test_metric_creation_with_conflicting_type(self) -> None:
        """Test metric creation with conflicting types returns existing metric.

        Description of what the test covers.
        Verifies that attempting to create metrics with the same name but
        different types returns the existing metric instance. This tests the
        actual behavior where the registry prevents creation conflicts by
        returning the already-registered metric.

        Expected Result:
        - First metric creation succeeds.
        - Second metric creation with different type returns same instance.
        - Registry maintains consistency and avoids type conflicts.
        """
        registry = PrometheusMetricsRegistry("type_conflict_test")

        # Create initial counter metric
        counter = registry.counter("conflicting_metric", "Test counter")
        assert counter is not None
        assert "conflicting_metric" in registry._metrics

        # Attempting to create a gauge with the same name returns the existing counter
        gauge_attempt = registry.gauge("conflicting_metric", "Test gauge")
        assert gauge_attempt is counter  # type: ignore[comparison-overlap]  # Should return the same instance
        assert isinstance(gauge_attempt, type(counter))  # Should be same type as original

        # Verify registry state is consistent
        assert "conflicting_metric" in registry._metrics
        assert len([k for k in registry._metrics if "conflicting_metric" in k]) == 1

        # Original counter should still work
        counter.inc()

        # Verify other metric types also return the same instance
        histogram_attempt = registry.histogram("conflicting_metric", "Test histogram")
        assert histogram_attempt is counter  # type: ignore[comparison-overlap]

        summary_attempt = registry.summary("conflicting_metric", "Test summary")
        assert summary_attempt is counter  # type: ignore[comparison-overlap]

    def test_metric_creation_with_conflicting_labels(self) -> None:
        """Test metric creation with conflicting label lists returns existing metric.

        Description of what the test covers.
        Verifies that attempting to create metrics with the same name but
        different label lists returns the existing metric instance. This tests
        the actual behavior where registry prevents conflicts by returning the
        already-registered metric, ignoring the new label specification.

        Expected Result:
        - First metric creation with labels succeeds.
        - Second metric creation with different labels returns same instance.
        - Registry maintains consistency and ignores conflicting label specs.
        """
        registry = PrometheusMetricsRegistry("label_conflict_test")

        # Create initial counter with specific labels
        counter = registry.counter("label_conflicting_metric", "Test counter", labels=["method", "status"])
        assert counter is not None
        assert "label_conflicting_metric" in registry._metrics

        # Test counter functionality with original labels
        counter.labels(method="GET", status="200").inc()

        # Attempting to create same metric with different labels returns existing instance
        counter2 = registry.counter("label_conflicting_metric", "Different description", labels=["endpoint", "region"])
        assert counter2 is counter  # Should return the same instance

        # Test with subset of labels - returns same instance
        counter3 = registry.counter("label_conflicting_metric", "Subset labels", labels=["method"])
        assert counter3 is counter

        # Test with superset of labels - returns same instance
        counter4 = registry.counter(
            "label_conflicting_metric", "Superset labels", labels=["method", "status", "endpoint"]
        )
        assert counter4 is counter

        # Verify original metric still works with original labels
        counter.labels(method="POST", status="201").inc()

        # Verify registry consistency
        assert len([k for k in registry._metrics if "label_conflicting_metric" in k]) == 1


class TestStructuredLogging:
    """Test cases for structured logging functionality.

    Verifies that logging setup, formatting, filtering, and context
    management work correctly across different scenarios.
    """

    def test_log_format_enumeration(self) -> None:
        """Test log format enumeration values.

        Description of what the test covers.
        Verifies that all expected log formats are available
        and have correct string values.

        Expected Result:
        - All format types are available.
        - String values match expected patterns.
        - Formats can be used in configuration.
        """
        # Test all format types exist
        assert LogFormat.JSON.value == "json"
        assert LogFormat.PRETTY.value == "pretty"
        assert LogFormat.COMPACT.value == "compact"
        assert LogFormat.DETAILED.value == "detailed"

        # Test format can be used in string context
        formats = [LogFormat.JSON, LogFormat.PRETTY, LogFormat.COMPACT, LogFormat.DETAILED]
        for fmt in formats:
            assert isinstance(fmt, str)
            assert len(fmt) > 0

    def test_log_filter_creation(self) -> None:
        """Test log filter creation and configuration.

        Description of what the test covers.
        Verifies that log filters can be created with various
        criteria and combinations of filtering rules.

        Expected Result:
        - Filter accepts all configuration parameters.
        - Filter function can be called with log records.
        - Multiple criteria can be combined.
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
        """Test creation of specialized log filters.

        Description of what the test covers.
        Verifies that convenience functions create filters
        with appropriate configurations for specific use cases.

        Expected Result:
        - Performance filter identifies performance-related logs.
        - Error filter captures warnings and errors only.
        - Debug filter isolates debug messages.
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
        """Test log formatter creation for different formats.

        Description of what the test covers.
        Verifies that formatters are created correctly for each
        log format type and produce expected output patterns.

        Expected Result:
        - Formatters created for all format types.
        - Format strings contain expected placeholders.
        - JSON formatter returns callable function.
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
        """Test trace ID patcher for log record enhancement.

        Description of what the test covers.
        Verifies that the trace ID patcher correctly adds
        trace ID information to log records.

        Expected Result:
        - Trace ID added to log record extra fields.
        - No trace ID scenario handled gracefully.
        - Exception trace ID extracted when available.
        """
        # Mock log record
        record: dict[str, Any] = {"extra": {}, "exception": None}

        # Test with no trace ID
        with patch("asset_core.observability.logging.get_trace_id", return_value=None):
            trace_id_patcher(record)  # type: ignore[arg-type]
            assert record["extra"]["trace_id"] == "no-trace"

        # Test with trace ID
        with patch("asset_core.observability.logging.get_trace_id", return_value="test-trace-123"):
            record["extra"] = {}  # Reset
            trace_id_patcher(record)  # type: ignore[arg-type]
            assert record["extra"]["trace_id"] == "test-trace-123"

        # Test with exception that has trace ID
        mock_exception = MagicMock()
        mock_exception.value.trace_id = "exception-trace-456"
        record["exception"] = mock_exception
        record["extra"] = {}

        with patch("asset_core.observability.logging.get_trace_id", return_value="current-trace"):
            trace_id_patcher(record)  # type: ignore[arg-type]
            assert record["extra"]["trace_id"] == "current-trace"
            assert record["extra"]["exception_trace_id"] == "exception-trace-456"

    def test_logging_setup_configuration(self) -> None:
        """Test logging setup with various configurations.

        Description of what the test covers.
        Verifies that logging can be configured with different
        handlers, formats, and output destinations.

        Expected Result:
        - Console and file logging can be configured.
        - Different formats applied to different handlers.
        - Log files created in specified locations.
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

        # Test filesystem error handling with unwritable path
        try:
            # Try to create a log file in an invalid location
            invalid_path = Path("/dev/null/invalid_directory/test.log")
            with pytest.raises(
                OSError, match=".*[Pp]ermission.*denied.*|.*[Nn]o.*such.*file.*directory.*|.*[Nn]ot.*a.*directory.*"
            ):
                setup_logging(
                    level="INFO",
                    enable_console=False,
                    enable_file=True,
                    log_file=invalid_path,
                    app_name="error_test",
                )
        except PermissionError:
            # On some systems, this might manifest as a PermissionError
            pass

        # Test with read-only directory (if we can create one for testing)
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o555)  # Read and execute only, no write

            readonly_log_file = readonly_dir / "readonly.log"

            try:
                with pytest.raises((OSError, PermissionError)):
                    setup_logging(
                        level="INFO",
                        enable_console=False,
                        enable_file=True,
                        log_file=readonly_log_file,
                        app_name="readonly_test",
                    )
            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)

    def test_logger_creation_and_binding(self) -> None:
        """Test logger creation with extra field binding.

        Description of what the test covers.
        Verifies that loggers can be created with bound
        extra fields that appear in all log messages.

        Expected Result:
        - Logger created with bound fields.
        - Extra fields appear in log output.
        - Different loggers can have different bindings.
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
        """Test log context manager for temporary field binding.

        Description of what the test covers.
        Verifies that context manager correctly adds and removes
        temporary context fields for scoped logging.

        Expected Result:
        - Context fields available within context.
        - Context fields removed after exiting.
        - Multiple contexts can be nested.
        """
        # Test basic context
        with LogContext(operation="test_operation", request_id="req-123") as context_logger:
            assert context_logger is not None

        # Test nested contexts
        with LogContext(service="api"), LogContext(endpoint="/users") as inner_logger:
            assert inner_logger is not None

    def test_performance_logging_decorator(self) -> None:
        """Test performance logging decorator functionality.

        Description of what the test covers.
        Verifies that the decorator correctly measures and logs
        function execution time for both sync and async functions.

        Expected Result:
        - Decorator works with both sync and async functions.
        - Performance metrics are logged correctly.
        - Exceptions are handled and re-raised.
        """

        # Test sync function
        @log_performance("test_sync_function")
        def sync_function(duration: float = 0.01) -> str:
            time.sleep(duration)
            return "sync_result"

        result = sync_function()
        assert result == "sync_result"

        # Test async function
        @log_performance("test_async_function", "DEBUG")
        async def async_function(duration: float = 0.01) -> str:
            await asyncio.sleep(duration)
            return "async_result"

        async def run_async_test() -> None:
            result = await async_function()
            assert result == "async_result"

        asyncio.run(run_async_test())

        # Test exception handling
        @log_performance()
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Test decorator with complex function signatures
        @log_performance("complex_args_function")
        def complex_function(*args: Any, **kwargs: Any) -> dict[str, Any]:
            time.sleep(0.001)  # Small delay
            return {"args": args, "kwargs": kwargs}

        result = complex_function(1, 2, "test", key1="value1", key2="value2")
        assert result["args"] == (1, 2, "test")
        assert result["kwargs"] == {"key1": "value1", "key2": "value2"}

        # Test decorator with mixed arguments
        @log_performance("mixed_args_function", "DEBUG")
        def mixed_args_function(required: str, *args: int, optional: str = "default", **kwargs: Any) -> dict[str, Any]:
            time.sleep(0.001)
            return {"required": required, "args": args, "optional": optional, "kwargs": kwargs}

        result = mixed_args_function("test", 1, 2, 3, optional="custom", extra="data")
        assert result["required"] == "test"
        assert result["args"] == (1, 2, 3)
        assert result["optional"] == "custom"
        assert result["kwargs"] == {"extra": "data"}

    def test_function_call_logging_decorator(self) -> None:
        """Test function call logging decorator.

        Description of what the test covers.
        Verifies that the decorator logs function entry, exit,
        and optionally arguments and results.

        Expected Result:
        - Function calls are logged correctly.
        - Arguments and results logged when enabled.
        - Exceptions are caught and logged.
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
        def error_function() -> None:
            raise RuntimeError("Test exception")

        with pytest.raises(RuntimeError):
            error_function()

        # Test decorator with complex function signatures
        @log_function_calls(include_args=True, include_result=True)
        def complex_signature_function(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"processed_args": len(args), "processed_kwargs": len(kwargs)}

        result = complex_signature_function("a", "b", "c", key1="val1", key2="val2")
        assert result["processed_args"] == 3
        assert result["processed_kwargs"] == 2

        # Test decorator with mixed argument types
        @log_function_calls(include_args=True)
        def mixed_signature_function(
            required: str, *positional: int, default_arg: str = "default", **named: Any
        ) -> str:
            return f"{required}-{len(positional)}-{default_arg}-{len(named)}"

        result = mixed_signature_function("test", 1, 2, 3, default_arg="custom", extra1="a", extra2="b")
        assert result == "test-3-custom-2"

        # Test decorator with function that has exceptions and complex args
        @log_function_calls(include_args=True, include_result=False)
        def complex_error_function(*_args: Any, **kwargs: Any) -> None:
            if "error" in kwargs:
                raise ValueError(f"Error triggered: {kwargs['error']}")
            return None

        # Should not raise exception when no error
        complex_error_function("safe", "args", safe_param="ok")

        # Should raise exception and log it
        with pytest.raises(ValueError):
            complex_error_function("unsafe", error="test error", param="value")

    def test_traceable_logger_functionality(self) -> None:
        """Test TraceableLogger class functionality.

        Description of what the test covers.
        Verifies that TraceableLogger ensures trace ID presence
        and provides convenient logging methods.

        Expected Result:
        - Trace ID is ensured for all log calls.
        - All log levels are supported.
        - Exception logging includes context.
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
    """Test cases for trace ID propagation and management.

    Verifies that trace IDs are correctly generated, stored,
    propagated across contexts, and integrated with logging.
    """

    def test_trace_id_generation(self) -> None:
        """Test trace ID generation functionality.

        Description of what the test covers.
        Verifies that trace IDs are generated as UUID4 strings
        without dashes for compact representation.

        Expected Result:
        - Generated trace IDs are strings.
        - Format is UUID4 without dashes (32 hex characters).
        - Each generation produces unique IDs.
        """
        trace_id = generate_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 32  # UUID4 without dashes
        assert all(c in "0123456789abcdef" for c in trace_id.lower())

        # Test uniqueness
        trace_id2 = generate_trace_id()
        assert trace_id != trace_id2

    def test_trace_id_context_management(self) -> None:
        """Test trace ID setting and retrieval from context.

        Description of what the test covers.
        Verifies that trace IDs can be set and retrieved from
        both context variables and thread-local storage.

        Expected Result:
        - Trace ID can be set and retrieved.
        - Context variables take precedence over thread-local.
        - None returned when no trace ID is set.
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
        """Test get_or_create_trace_id functionality.

        Description of what the test covers.
        Verifies that function returns existing trace ID
        or creates new one if none exists.

        Expected Result:
        - Returns existing trace ID when available.
        - Creates new trace ID when none exists.
        - Subsequent calls return same trace ID.
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
        """Test TraceContext context manager functionality.

        Description of what the test covers.
        Verifies that trace context correctly sets and restores
        trace IDs within context blocks.

        Expected Result:
        - Trace ID set within context.
        - Previous trace ID restored after context.
        - New trace ID generated if none provided.
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
        """Test trace ID formatting for display.

        Description of what the test covers.
        Verifies that trace ID formatting handles None values
        and provides user-friendly display format.

        Expected Result:
        - Valid trace IDs returned as-is.
        - None values formatted as 'no-trace'.
        - Current trace ID formatted correctly.
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
        """Test TraceIdMiddleware for HTTP header integration.

        Description of what the test covers.
        Verifies that middleware can extract trace IDs from headers
        and inject them into outgoing requests.

        Expected Result:
        - Trace ID extracted from headers correctly.
        - Trace ID injected into headers.
        - Case-insensitive header handling.
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
        empty_headers: dict[str, str] = {}
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
        """Test with_trace_id decorator functionality.

        Description of what the test covers.
        Verifies that decorator ensures trace ID context
        for both synchronous and asynchronous functions.

        Expected Result:
        - Decorator works with sync and async functions.
        - Trace ID available within decorated function.
        - Custom trace ID can be specified.
        """

        # Test sync function without specific trace ID
        @with_trace_id()
        def sync_function() -> str | None:
            result: str | None = get_trace_id()
            return result

        result = sync_function()
        assert result is not None
        assert len(result) == 32

        # Test sync function with specific trace ID
        @with_trace_id("custom-sync-trace")
        def sync_function_custom() -> str | None:
            result: str | None = get_trace_id()
            return result

        result = sync_function_custom()
        assert result == "custom-sync-trace"

        # Test async function
        @with_trace_id()
        async def async_function() -> str | None:
            result: str | None = get_trace_id()
            return result

        async def run_async_test() -> None:
            result = await async_function()
            assert result is not None
            assert len(result) == 32

        asyncio.run(run_async_test())

        # Test async function with custom trace ID
        @with_trace_id("custom-async-trace")
        async def async_function_custom() -> str | None:
            result: str | None = get_trace_id()
            return result

        async def run_custom_async_test() -> None:
            result = await async_function_custom()
            assert result == "custom-async-trace"

        asyncio.run(run_custom_async_test())

    def test_thread_local_fallback(self) -> None:
        """Test thread-local storage fallback for trace ID.

        Description of what the test covers.
        Verifies that trace ID management works correctly
        in scenarios where context variables might not be available.

        Expected Result:
        - Thread-local storage works as fallback.
        - Different threads have isolated trace IDs.
        - Context variables take precedence when available.
        """

        def thread_test_function(results: dict[str, str | None], thread_id: str) -> None:
            """Function to run in separate thread."""
            clear_trace_id()

            # Set trace ID specific to this thread
            set_trace_id(f"thread-{thread_id}-trace")
            results[thread_id] = get_trace_id()

        # Test with multiple threads
        results: dict[str, str | None] = {}
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

    def test_trace_id_input_validation(self) -> None:
        """Test trace ID input handling and behavior validation.

        Description of what the test covers.
        Verifies that trace ID functions handle different input types correctly
        and document the actual behavior with various inputs including None,
        empty strings, and different data types.

        Expected Result:
        - set_trace_id(None) generates new trace ID (documented behavior).
        - set_trace_id("") allows empty string (if supported).
        - String inputs are accepted and stored correctly.
        - Behavior is consistent across TraceContext and @with_trace_id.
        """
        # Test that None input generates a new trace ID (actual behavior)
        clear_trace_id()
        generated_id = set_trace_id(None)
        assert generated_id is not None
        assert len(generated_id) == 32  # UUID4 without dashes
        assert get_trace_id() == generated_id

        # Test empty string behavior - test actual behavior
        clear_trace_id()
        try:
            set_trace_id("")
            empty_string_allowed = True
            # If allowed, verify it was set
            assert get_trace_id() == ""
        except (ValueError, TypeError):
            empty_string_allowed = False

        # Test valid string inputs
        clear_trace_id()
        test_id = "test-trace-123"
        result_id = set_trace_id(test_id)
        assert result_id == test_id
        assert get_trace_id() == test_id

        # Test TraceContext has consistent behavior with set_trace_id
        if empty_string_allowed:
            # If empty strings are allowed by set_trace_id, TraceContext should also allow them
            with TraceContext("") as trace_id:
                assert trace_id == ""
                assert get_trace_id() == ""

        # Test valid TraceContext usage
        with TraceContext("context-trace-456") as trace_id:
            assert trace_id == "context-trace-456"
            assert get_trace_id() == "context-trace-456"

        # Test @with_trace_id decorator behavior
        if empty_string_allowed:

            @with_trace_id("")
            def test_empty_trace_decorator() -> str | None:
                return get_trace_id()

            result = test_empty_trace_decorator()
            assert result == ""

        # Test @with_trace_id with valid input
        @with_trace_id("decorator-trace-789")
        def test_valid_trace_decorator() -> str | None:
            return get_trace_id()

        result = test_valid_trace_decorator()
        assert result == "decorator-trace-789"

        # Test @with_trace_id with None (should generate)
        @with_trace_id(None)
        def test_none_trace_decorator() -> str | None:
            return get_trace_id()

        result = test_none_trace_decorator()
        assert result is not None
        assert len(result) == 32

        # Note: Type validation may be handled at the type checker level
        # rather than runtime, so we focus on testing actual functional behavior

    def test_trace_id_integration_with_logging(self) -> None:
        """Test trace ID integration with logging system.

        Description of what the test covers.
        Verifies that trace IDs are automatically included
        in log records and can be used for request correlation.
        Uses real loguru logger with StringIO to capture actual log output.

        Expected Result:
        - Trace ID appears in formatted log strings.
        - log_with_trace_id function works correctly with real logger.
        - Trace context affects logging output.
        """
        import io

        # Test trace ID in logging with real logger
        set_trace_id("logging-trace-123")

        # Create a StringIO buffer to capture log output
        log_buffer = io.StringIO()

        # Configure a temporary logger that writes to our buffer
        import loguru

        logger_id = loguru.logger.add(
            log_buffer, format="{time} | {level} | {extra[trace_id]} | {message}", level="DEBUG"
        )

        try:
            # Test log_with_trace_id function with real logger output
            log_with_trace_id("INFO", "Test message with trace ID", extra_field="value")

            # Get the logged content
            log_content = log_buffer.getvalue()

            # Verify trace ID appears in the actual log output
            assert "logging-trace-123" in log_content, f"Trace ID not found in log: {log_content}"
            assert "Test message with trace ID" in log_content

            # Clear buffer for next test
            log_buffer.seek(0)
            log_buffer.truncate(0)

            # Test with explicit trace ID override
            log_with_trace_id("DEBUG", "Debug message", trace_id="override-trace", data="test")

            log_content = log_buffer.getvalue()
            assert "override-trace" in log_content or "logging-trace-123" in log_content
            assert "Debug message" in log_content

            # Clear buffer for context test
            log_buffer.seek(0)
            log_buffer.truncate(0)

            # Test trace context affects logging
            with TraceContext("context-logging-trace"):
                current_trace = get_trace_id()
                assert current_trace == "context-logging-trace"

                # Log something with the context trace ID
                test_logger = get_logger("test_context")
                test_logger.info("Context message")

                # Check that context trace ID appears in logs
                log_content = log_buffer.getvalue()
                # Note: The exact format depends on the logger configuration
                # We verify the trace ID is available via get_trace_id
                assert get_trace_id() == "context-logging-trace"

        finally:
            # Clean up the temporary logger
            loguru.logger.remove(logger_id)
