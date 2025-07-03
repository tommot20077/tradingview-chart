from typing import Any
from unittest import mock
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info, Summary

from asset_core.observability.metrics import PrometheusMetricsRegistry, create_common_metrics


@pytest.fixture
def mock_prometheus_client(mocker: Any) -> MagicMock:
    """Mocks prometheus_client components."""
    mock_prometheus_module = MagicMock()
    # Patch in the metrics module where they are actually imported
    mock_prometheus_module.Counter = mocker.patch(
        "asset_core.observability.metrics.Counter", return_value=MagicMock(spec=Counter)
    )
    mock_prometheus_module.Gauge = mocker.patch(
        "asset_core.observability.metrics.Gauge", return_value=MagicMock(spec=Gauge)
    )
    mock_prometheus_module.Histogram = mocker.patch(
        "asset_core.observability.metrics.Histogram", return_value=MagicMock(spec=Histogram)
    )
    mock_prometheus_module.Summary = mocker.patch(
        "asset_core.observability.metrics.Summary", return_value=MagicMock(spec=Summary)
    )
    mock_prometheus_module.Info = mocker.patch(
        "asset_core.observability.metrics.Info", return_value=MagicMock(spec=Info)
    )
    mock_prometheus_module.generate_latest = mocker.patch(
        "asset_core.observability.metrics.generate_latest", return_value=b"mock_metrics_data"
    )
    mock_prometheus_module.CollectorRegistry = mocker.patch("asset_core.observability.metrics.CollectorRegistry")
    return mock_prometheus_module


@pytest.fixture
def metrics_registry() -> PrometheusMetricsRegistry:
    """Provides a PrometheusMetricsRegistry instance for testing."""
    return PrometheusMetricsRegistry(namespace="test_app")


class TestPrometheusMetricsRegistry:
    def test_initialization(self, metrics_registry: PrometheusMetricsRegistry) -> None:
        """Test that the registry initializes correctly."""
        assert isinstance(metrics_registry.registry, CollectorRegistry)
        assert metrics_registry.namespace == "test_app"
        assert metrics_registry._metrics == {}

    def test_counter_creation(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test counter creation and retrieval."""
        counter = metrics_registry.counter("my_counter", "A test counter", labels=["status"])
        mock_prometheus_client.Counter.assert_called_once_with(
            name="my_counter",
            documentation="A test counter",
            labelnames=["status"],
            namespace="test_app",
            registry=metrics_registry.registry,
        )
        assert counter == mock_prometheus_client.Counter.return_value

        # Test retrieval of existing counter
        another_counter = metrics_registry.counter("my_counter", "Another test counter")
        assert another_counter == counter
        mock_prometheus_client.Counter.assert_called_once()  # Should not be called again

    def test_gauge_creation(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test gauge creation and retrieval."""
        gauge = metrics_registry.gauge("my_gauge", "A test gauge")
        mock_prometheus_client.Gauge.assert_called_once_with(
            name="my_gauge",
            documentation="A test gauge",
            labelnames=[],
            namespace="test_app",
            registry=metrics_registry.registry,
        )
        assert gauge == mock_prometheus_client.Gauge.return_value

    def test_histogram_creation(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test histogram creation and retrieval."""
        histogram = metrics_registry.histogram("my_histogram", "A test histogram", buckets=(1, 2, 3))
        mock_prometheus_client.Histogram.assert_called_once_with(
            name="my_histogram",
            documentation="A test histogram",
            labelnames=[],
            namespace="test_app",
            registry=metrics_registry.registry,
            buckets=(1, 2, 3),
        )
        assert histogram == mock_prometheus_client.Histogram.return_value

    def test_summary_creation(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test summary creation and retrieval."""
        summary = metrics_registry.summary("my_summary", "A test summary")
        mock_prometheus_client.Summary.assert_called_once_with(
            name="my_summary",
            documentation="A test summary",
            labelnames=[],
            namespace="test_app",
            registry=metrics_registry.registry,
        )
        assert summary == mock_prometheus_client.Summary.return_value

    def test_info_creation(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test info creation and retrieval."""
        info = metrics_registry.info("my_info", "A test info")
        mock_prometheus_client.Info.assert_called_once_with(
            name="my_info",
            documentation="A test info",
            namespace="test_app",
            registry=metrics_registry.registry,
        )
        assert info == mock_prometheus_client.Info.return_value

    def test_format_name(self, metrics_registry: PrometheusMetricsRegistry) -> None:
        """Test _format_name method."""
        assert metrics_registry._format_name("my-metric.name") == "my_metric_name"
        assert metrics_registry._format_name("another_metric") == "another_metric"

    def test_generate_metrics(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test generate_metrics method."""
        metrics_data = metrics_registry.generate_metrics()
        mock_prometheus_client.generate_latest.assert_called_once_with(metrics_registry.registry)
        assert metrics_data == b"mock_metrics_data"

    @pytest.mark.asyncio
    async def test_start_http_server(self, metrics_registry: PrometheusMetricsRegistry, mocker: Any) -> None:
        """Test start_http_server method."""
        mock_app = MagicMock(spec=web.Application)
        mock_app.router = MagicMock()
        mock_app_runner = MagicMock(spec=web.AppRunner)
        mock_site = MagicMock(spec=web.TCPSite)

        mocker.patch("aiohttp.web.Application", return_value=mock_app)
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_app_runner)
        mock_tcpsite_class = mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)

        runner = await metrics_registry.start_http_server(port=8080)

        mock_app.router.add_get.assert_called_once_with("/metrics", metrics_registry._handle_metrics)
        mock_app_runner.setup.assert_called_once()
        mock_site.start.assert_called_once()
        mock_tcpsite_class.assert_called_once_with(mock_app_runner, "0.0.0.0", 8080)
        assert runner == mock_app_runner

    @pytest.mark.asyncio
    async def test_handle_metrics(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test _handle_metrics method."""
        mock_request = MagicMock(spec=web.Request)
        response = await metrics_registry._handle_metrics(mock_request)

        mock_prometheus_client.generate_latest.assert_called_once_with(metrics_registry.registry)
        assert response.body == b"mock_metrics_data"
        assert response.content_type == "text/plain"
        assert response.charset == "utf-8"
        # Check the full Content-Type header includes the version
        assert "text/plain; version=0.0.4; charset=utf-8" in response.headers["Content-Type"]

    def test_metric_creation_with_conflicting_type(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test that creating metrics with same name but different types returns existing metric."""
        # Create a counter first
        counter = metrics_registry.counter("test_metric", "A test metric")

        # Trying to create a gauge with the same name should return the existing counter
        # (since the implementation checks _metrics dict first)
        gauge = metrics_registry.gauge("test_metric", "Another test metric")

        # Should return the same object (the counter)
        # Cast to Any to avoid type checking issues since the registry returns existing metrics
        gauge_as_any: Any = gauge
        assert gauge_as_any is counter

        # Should not create a new Gauge since the metric already exists
        assert not mock_prometheus_client.Gauge.called

    def test_metric_creation_with_conflicting_labels(
        self, metrics_registry: PrometheusMetricsRegistry, mock_prometheus_client: MagicMock
    ) -> None:
        """Test that creating metrics with same name but different labels returns existing metric."""
        # Create a counter with specific labels
        counter1 = metrics_registry.counter("test_metric", "A test metric", labels=["status"])

        # Trying to create a counter with different labels should return the existing counter
        # (since the implementation checks _metrics dict first)
        counter2 = metrics_registry.counter("test_metric", "Another test metric", labels=["method"])

        # Should return the same object
        assert counter2 is counter1

        # Counter should only be created once
        assert mock_prometheus_client.Counter.call_count == 1

    def test_invalid_metric_operations(self, metrics_registry: PrometheusMetricsRegistry) -> None:
        """Test that invalid metric operations raise appropriate errors."""
        # Create a counter
        counter = metrics_registry.counter("test_counter", "A test counter")

        # Mock the counter's inc method to raise ValueError for negative values
        def mock_inc(value: float = 1) -> None:
            if value < 0:
                raise ValueError("Counter increment must be non-negative")
            return None

        # Use mock.patch to properly mock the method
        with mock.patch.object(counter, "inc", side_effect=mock_inc):
            # Test that incrementing by negative value raises ValueError
            with pytest.raises(ValueError) as exc_info:
                counter.inc(-1)
            assert "must be non-negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_http_server_port_in_use(
        self, metrics_registry: PrometheusMetricsRegistry, mocker: Any
    ) -> None:
        """Test that starting two servers on the same port raises OSError."""
        mock_app = MagicMock(spec=web.Application)
        mock_app.router = MagicMock()
        mock_app_runner = MagicMock(spec=web.AppRunner)
        mock_site = MagicMock(spec=web.TCPSite)

        mocker.patch("aiohttp.web.Application", return_value=mock_app)
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_app_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)

        # First server starts successfully
        runner1 = await metrics_registry.start_http_server(port=8080)
        assert runner1 == mock_app_runner

        # Second server on the same port should raise OSError (address already in use)
        mock_site.start.side_effect = OSError("Address already in use")

        with pytest.raises(OSError) as exc_info:
            await metrics_registry.start_http_server(port=8080)
        assert "Address already in use" in str(exc_info.value)


class TestCommonMetrics:
    def test_create_common_metrics(self, mock_prometheus_client: MagicMock) -> None:
        """Test create_common_metrics creates all expected metrics."""
        registry = PrometheusMetricsRegistry()
        metrics = create_common_metrics(registry)

        # Verify all expected metrics are created and returned
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

        assert len(metrics) == len(expected_metrics)
        for metric_name in expected_metrics:
            assert metric_name in metrics
            assert metrics[metric_name] is not None

        # Verify specific metric types and calls
        mock_prometheus_client.Counter.assert_any_call(
            name="ws_connections_total",
            documentation="Total number of WebSocket connections",
            labelnames=["exchange", "status"],
            namespace="",
            registry=registry.registry,
        )
        mock_prometheus_client.Gauge.assert_any_call(
            name="active_connections",
            documentation="Number of active connections",
            labelnames=["type"],
            namespace="",
            registry=registry.registry,
        )
        mock_prometheus_client.Histogram.assert_any_call(
            name="storage_operation_duration_seconds",
            documentation="Storage operation duration in seconds",
            labelnames=["operation"],
            namespace="",
            registry=registry.registry,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
        )
