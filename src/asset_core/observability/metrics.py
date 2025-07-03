"""Prometheus metrics registry and helpers.

This module provides a `PrometheusMetricsRegistry` class for managing and exposing
Prometheus metrics within the `asset_core` library. It simplifies the creation
and registration of various metric types (Counter, Gauge, Histogram, Summary, Info)
and includes functionality to start an HTTP server for exposing these metrics.
"""

from typing import Any

from aiohttp import web
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)


class PrometheusMetricsRegistry:
    """Wrapper for Prometheus metrics registry with convenience methods.

    This class provides a simplified interface for creating, registering, and
    managing Prometheus metrics (Counters, Gauges, Histograms, Summaries, Info).
    It encapsulates the `prometheus_client` library and offers methods to generate
    metrics data and start an HTTP server for exposing metrics.

    Attributes:
        registry (CollectorRegistry): The underlying Prometheus collector registry.
        namespace (str | None): An optional namespace prefix for all metrics created by this registry.
    """

    def __init__(self, namespace: str | None = None) -> None:
        """Initializes a new PrometheusMetricsRegistry instance.

        Args:
            namespace: An optional string to prefix all metric names created by this registry.
                       Useful for distinguishing metrics from different applications or services.
        """
        self.registry = CollectorRegistry()
        self.namespace = namespace
        self._metrics: dict[str, Counter | Gauge | Histogram | Summary | Info] = {}

    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> Counter:
        """Creates or retrieves a Prometheus Counter metric.

        Counters are cumulative metrics that only ever go up.

        Args:
            name: The base name of the metric.
            description: A brief explanation of the metric.
            labels: An optional list of label names (e.g., ["status", "code"]).
            **kwargs: Additional keyword arguments passed to the `prometheus_client.Counter` constructor.

        Returns:
            A `Counter` instance.
        """
        metric_name = self._format_name(name)
        if metric_name not in self._metrics:
            self._metrics[metric_name] = Counter(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                namespace=self.namespace or "",
                registry=self.registry,
                **kwargs,
            )
        return self._metrics[metric_name]  # type: ignore

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> Gauge:
        """Creates or retrieves a Prometheus Gauge metric.

        Gauges represent a single numerical value that can arbitrarily go up and down.

        Args:
            name: The base name of the metric.
            description: A brief explanation of the metric.
            labels: An optional list of label names.
            **kwargs: Additional keyword arguments passed to the `prometheus_client.Gauge` constructor.

        Returns:
            A `Gauge` instance.
        """
        metric_name = self._format_name(name)
        if metric_name not in self._metrics:
            self._metrics[metric_name] = Gauge(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                namespace=self.namespace or "",
                registry=self.registry,
                **kwargs,
            )
        return self._metrics[metric_name]  # type: ignore

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
        **kwargs: Any,
    ) -> Histogram:
        """Creates or retrieves a Prometheus Histogram metric.

        Histograms sample observations (e.g., request durations) and count them
        in configurable buckets.

        Args:
            name: The base name of the metric.
            description: A brief explanation of the metric.
            labels: An optional list of label names.
            buckets: An optional tuple of bucket upper bounds. If `None`, default buckets are used.
            **kwargs: Additional keyword arguments passed to the `prometheus_client.Histogram` constructor.

        Returns:
            A `Histogram` instance.
        """
        metric_name = self._format_name(name)
        if metric_name not in self._metrics:
            kwargs_with_buckets = kwargs.copy()
            if buckets:
                kwargs_with_buckets["buckets"] = buckets

            self._metrics[metric_name] = Histogram(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                namespace=self.namespace or "",
                registry=self.registry,
                **kwargs_with_buckets,
            )
        return self._metrics[metric_name]  # type: ignore

    def summary(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> Summary:
        """Creates or retrieves a Prometheus Summary metric.

        Summaries observe individual events and provide quantiles over a sliding time window.

        Args:
            name: The base name of the metric.
            description: A brief explanation of the metric.
            labels: An optional list of label names.
            **kwargs: Additional keyword arguments passed to the `prometheus_client.Summary` constructor.

        Returns:
            A `Summary` instance.
        """
        metric_name = self._format_name(name)
        if metric_name not in self._metrics:
            self._metrics[metric_name] = Summary(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                namespace=self.namespace or "",
                registry=self.registry,
                **kwargs,
            )
        return self._metrics[metric_name]  # type: ignore

    def info(
        self,
        name: str,
        description: str,
        **kwargs: Any,
    ) -> Info:
        """Creates or retrieves a Prometheus Info metric.

        Info metrics are used to expose static, unchanging information about the target.

        Args:
            name: The base name of the metric.
            description: A brief explanation of the metric.
            **kwargs: Additional keyword arguments passed to the `prometheus_client.Info` constructor.

        Returns:
            An `Info` instance.
        """
        metric_name = self._format_name(name)
        if metric_name not in self._metrics:
            self._metrics[metric_name] = Info(
                name=metric_name,
                documentation=description,
                namespace=self.namespace or "",
                registry=self.registry,
                **kwargs,
            )
        return self._metrics[metric_name]  # type: ignore

    def _format_name(self, name: str) -> str:
        """Formats a metric name to be Prometheus-compliant.

        Replaces non-alphanumeric characters (like hyphens and dots) with underscores.

        Args:
            name: The original metric name.

        Returns:
            The formatted, Prometheus-compliant metric name.
        """
        # Replace non-alphanumeric characters with underscores
        return name.replace("-", "_").replace(".", "_")

    def generate_metrics(self) -> bytes:
        """Generates the current metrics data in Prometheus text exposition format.

        Returns:
            A `bytes` object containing the metrics data, ready to be served.
        """
        return generate_latest(self.registry)

    async def start_http_server(self, port: int = 9090) -> web.AppRunner:
        """Starts a simple HTTP server to expose the Prometheus metrics endpoint.

        This server listens on all interfaces (`0.0.0.0`) and serves the metrics
        at the `/metrics` path.

        Args:
            port: The port number on which the HTTP server will listen. Defaults to 9090.

        Returns:
            An `aiohttp.web.AppRunner` instance, which can be used to manage the server's lifecycle.

        Raises:
            OSError: If the specified port is already in use or other network issues occur.
        """
        app = web.Application()
        app.router.add_get("/metrics", self._handle_metrics)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        return runner

    async def _handle_metrics(self, _: web.Request) -> web.Response:
        """Handles HTTP requests to the `/metrics` endpoint.

        This method generates the current Prometheus metrics and returns them
        as an `aiohttp.web.Response`.

        Args:
            _: The `aiohttp.web.Request` object (unused).

        Returns:
            An `aiohttp.web.Response` containing the metrics data.
        """
        metrics_data = self.generate_metrics()
        return web.Response(
            body=metrics_data,
            content_type="text/plain; version=0.0.4",
            charset="utf-8",
        )


# Common metrics definitions
def create_common_metrics(
    registry: PrometheusMetricsRegistry,
) -> dict[str, Counter | Gauge | Histogram | Summary | Info]:
    """Creates and registers a set of common, predefined metrics for application monitoring.

    These metrics cover various aspects such as WebSocket connections, data processing
    (trades, klines), storage operations, and error rates.

    Args:
        registry: The `PrometheusMetricsRegistry` instance to which the metrics will be added.

    Returns:
        A dictionary mapping metric names (strings) to their corresponding Prometheus metric objects.
    """
    metrics = {
        # WebSocket metrics
        "ws_connections_total": registry.counter(
            "ws_connections_total",
            "Total number of WebSocket connections",
            labels=["exchange", "status"],
        ),
        "ws_messages_received_total": registry.counter(
            "ws_messages_received_total",
            "Total number of WebSocket messages received",
            labels=["exchange", "message_type"],
        ),
        "ws_reconnects_total": registry.counter(
            "ws_reconnects_total",
            "Total number of WebSocket reconnections",
            labels=["exchange"],
        ),
        # Data processing metrics
        "trades_processed_total": registry.counter(
            "trades_processed_total",
            "Total number of trades processed",
            labels=["exchange", "symbol"],
        ),
        "klines_processed_total": registry.counter(
            "klines_processed_total",
            "Total number of klines processed",
            labels=["exchange", "symbol", "interval"],
        ),
        # Storage metrics
        "storage_operations_total": registry.counter(
            "storage_operations_total",
            "Total number of storage operations",
            labels=["operation", "status"],
        ),
        "storage_operation_duration_seconds": registry.histogram(
            "storage_operation_duration_seconds",
            "Storage operation duration in seconds",
            labels=["operation"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
        ),
        # Error metrics
        "errors_total": registry.counter(
            "errors_total",
            "Total number of errors",
            labels=["error_type", "component"],
        ),
        # System metrics
        "active_connections": registry.gauge(
            "active_connections",
            "Number of active connections",
            labels=["type"],
        ),
        "processing_lag_seconds": registry.gauge(
            "processing_lag_seconds",
            "Processing lag in seconds",
            labels=["exchange", "symbol"],
        ),
    }

    return metrics  # type: ignore
