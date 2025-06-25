"""Prometheus metrics registry and helpers."""

from typing import Any

from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)


class PrometheusMetricsRegistry:
    """Wrapper for Prometheus metrics registry with convenience methods."""

    def __init__(self, namespace: str | None = None) -> None:
        """Initialize metrics registry.

        Args:
            namespace: Optional namespace prefix for all metrics
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
        """Create or get a counter metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Optional label names
            **kwargs: Additional arguments for Counter

        Returns:
            Counter instance
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
        """Create or get a gauge metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Optional label names
            **kwargs: Additional arguments for Gauge

        Returns:
            Gauge instance
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
        """Create or get a histogram metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Optional label names
            buckets: Optional histogram buckets
            **kwargs: Additional arguments for Histogram

        Returns:
            Histogram instance
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
        """Create or get a summary metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Optional label names
            **kwargs: Additional arguments for Summary

        Returns:
            Summary instance
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
        """Create or get an info metric.

        Args:
            name: Metric name
            description: Metric description
            **kwargs: Additional arguments for Info

        Returns:
            Info instance
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
        """Format metric name."""
        # Replace non-alphanumeric characters with underscores
        return name.replace("-", "_").replace(".", "_")

    def generate_metrics(self) -> bytes:
        """Generate metrics in Prometheus format.

        Returns:
            Metrics data in Prometheus text format
        """
        return generate_latest(self.registry)

    async def start_http_server(self, port: int = 9090) -> web.AppRunner:
        """Start HTTP server for metrics endpoint.

        Args:
            port: Port to listen on

        Returns:
            AppRunner instance for server management
        """
        app = web.Application()
        app.router.add_get("/metrics", self._handle_metrics)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        return runner

    async def _handle_metrics(self, _: web.Request) -> web.Response:
        """Handle metrics endpoint request."""
        metrics_data = self.generate_metrics()
        return web.Response(
            body=metrics_data,
            content_type=CONTENT_TYPE_LATEST,
        )


# Common metrics definitions
def create_common_metrics(
    registry: PrometheusMetricsRegistry,
) -> dict[str, Counter | Gauge | Histogram | Summary | Info]:
    """Create common metrics for monitoring.

    Args:
        registry: Metrics registry

    Returns:
        Dictionary of common metrics
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
