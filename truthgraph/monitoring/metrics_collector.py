"""Central metrics collection service for TruthGraph.

This module provides the main metrics collection interface, supporting
counters, gauges, and histograms with Prometheus-compatible naming.
Designed as a singleton for use with FastAPI dependency injection.
"""

import asyncio
import logging
import time

from truthgraph.monitoring.storage.metric_store import MetricStore

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Central service for collecting and recording application metrics.

    Implements a singleton pattern through FastAPI dependency injection.
    Supports three metric types:
    - COUNTER: Monotonically increasing values (e.g., request count)
    - GAUGE: Point-in-time values (e.g., CPU usage)
    - HISTOGRAM: Value distributions (e.g., response times)

    The collector runs a background loop at 10-second intervals to perform
    periodic collections (system metrics, aggregations, etc.).

    Attributes:
        store: MetricStore instance for persisting metrics
        collection_interval: Seconds between background collections (default 10)
        start_time: Unix timestamp when collector was initialized

    Example:
        >>> collector = MetricsCollector()
        >>> await collector.increment_counter("api.requests", labels={"endpoint": "/verify"})
        >>> await collector.set_gauge("cpu.percent", 45.2)
        >>> await collector.record_histogram("api.response_time_ms", 123.4)
    """

    def __init__(self, store: MetricStore | None = None, collection_interval: int = 10):
        """Initialize metrics collector.

        Args:
            store: MetricStore instance (creates new one if not provided)
            collection_interval: Seconds between background collection loops
        """
        self.store = store if store is not None else MetricStore()
        self.collection_interval = collection_interval
        self.start_time = time.time()
        self._running = False
        self._collection_task: asyncio.Task[None] | None = None
        self._counters: dict[str, float] = {}  # Track counter values
        self._counter_lock = asyncio.Lock()

    async def increment_counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric.

        Counters are monotonically increasing values. Use for counting events
        like requests, errors, tasks completed, etc.

        Args:
            name: Prometheus-style metric name (e.g., "api.requests.total")
            value: Amount to increment by (default 1.0)
            labels: Optional labels for dimensions (e.g., {"method": "POST"})

        Example:
            >>> await collector.increment_counter("api.requests.total")
            >>> await collector.increment_counter(
            ...     "api.requests.total",
            ...     labels={"endpoint": "/verify", "method": "POST"}
            ... )
        """
        # Generate unique key for counter with labels
        counter_key = self._make_metric_key(name, labels)

        async with self._counter_lock:
            current = self._counters.get(counter_key, 0.0)
            new_value = current + value
            self._counters[counter_key] = new_value

        # Record the new total value
        await self.store.record_metric(name, new_value, labels=labels)

    async def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge metric value.

        Gauges represent point-in-time values that can go up or down.
        Use for things like CPU usage, memory usage, queue depth, etc.

        Args:
            name: Prometheus-style metric name (e.g., "cpu.percent")
            value: Current gauge value
            labels: Optional labels for dimensions (e.g., {"core": "0"})

        Example:
            >>> await collector.set_gauge("cpu.percent", 45.2)
            >>> await collector.set_gauge("memory.rss.mb", 512.0)
            >>> await collector.set_gauge(
            ...     "queue.depth",
            ...     42,
            ...     labels={"queue": "verification"}
            ... )
        """
        await self.store.record_metric(name, value, labels=labels)

    async def record_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation.

        Histograms track distributions of values over time. Use for things
        like response times, request sizes, processing durations, etc.

        Args:
            name: Prometheus-style metric name (e.g., "api.response_time_ms")
            value: Observed value
            labels: Optional labels for dimensions (e.g., {"endpoint": "/verify"})

        Example:
            >>> await collector.record_histogram("api.response_time_ms", 123.4)
            >>> await collector.record_histogram(
            ...     "embedding.generation_time_ms",
            ...     456.7,
            ...     labels={"model": "all-MiniLM-L6-v2"}
            ... )
        """
        await self.store.record_metric(name, value, labels=labels)

    async def get_uptime_seconds(self) -> int:
        """Get application uptime in seconds.

        Returns:
            Number of seconds since collector was initialized.

        Example:
            >>> uptime = await collector.get_uptime_seconds()
            >>> print(f"Uptime: {uptime} seconds")
        """
        return int(time.time() - self.start_time)

    async def collect_system_metrics(self) -> None:
        """Collect system-level metrics (CPU, memory, etc.).

        This is called periodically by the background collection loop.
        Uses asyncio.to_thread() to avoid blocking the event loop with
        synchronous psutil calls.

        Example metrics collected:
        - system.cpu.percent
        - system.memory.rss.mb
        - system.memory.percent
        - system.open.file_descriptors (Unix only)
        """
        try:
            import psutil

            # Use asyncio.to_thread for blocking psutil calls
            process = await asyncio.to_thread(psutil.Process)

            # CPU usage (non-blocking for first call)
            cpu_percent = await asyncio.to_thread(process.cpu_percent, 0)
            await self.set_gauge("system.cpu.percent", cpu_percent)

            # Memory usage
            memory_info = await asyncio.to_thread(process.memory_info)
            await self.set_gauge("system.memory.rss.mb", memory_info.rss / 1024 / 1024)

            # Memory percent
            memory_percent = await asyncio.to_thread(process.memory_percent)
            await self.set_gauge("system.memory.percent", memory_percent)

            # File descriptors (Unix only)
            try:
                num_fds = await asyncio.to_thread(process.num_fds)
                await self.set_gauge("system.open.file_descriptors", num_fds)
            except AttributeError:
                # num_fds not available on Windows
                pass

        except ImportError:
            logger.warning("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}", exc_info=True)

    async def collect_metrics_store_stats(self) -> None:
        """Collect metrics about the metric store itself.

        Records metadata about the monitoring system:
        - monitoring.metrics.count
        - monitoring.entries.total
        - monitoring.memory.estimated_bytes
        """
        try:
            usage = await self.store.get_memory_usage()
            await self.set_gauge("monitoring.metrics.count", usage["metric_count"])
            await self.set_gauge("monitoring.entries.total", usage["total_entries"])
            await self.set_gauge("monitoring.memory.estimated_bytes", usage["estimated_bytes"])
        except Exception as e:
            logger.error(f"Error collecting metric store stats: {e}", exc_info=True)

    async def collect_loop(self) -> None:
        """Background collection loop for periodic metrics.

        Runs every collection_interval seconds to gather system metrics
        and other periodic measurements. Designed to be run as a background
        task in FastAPI lifespan.

        Example:
            >>> collector = MetricsCollector()
            >>> collection_task = asyncio.create_task(collector.collect_loop())
            >>> # ... application runs ...
            >>> collection_task.cancel()
        """
        logger.info(f"Starting metrics collection loop (interval: {self.collection_interval}s)")

        while self._running:
            try:
                # Collect various metrics
                await self.collect_system_metrics()
                await self.collect_metrics_store_stats()

                # Record collection timestamp
                await self.set_gauge("monitoring.last_collection_timestamp", time.time())

            except Exception as e:
                logger.error(f"Error in collection loop: {e}", exc_info=True)

            # Wait for next collection interval
            await asyncio.sleep(self.collection_interval)

    async def start(self) -> None:
        """Start the background collection loop.

        Creates an asyncio task for the collection loop. Should be called
        during application startup (FastAPI lifespan).

        Example:
            >>> collector = MetricsCollector()
            >>> await collector.start()
        """
        if self._collection_task is None or self._collection_task.done():
            self._running = True
            self._collection_task = asyncio.create_task(self.collect_loop())
            logger.info("Metrics collector started")

    async def stop(self) -> None:
        """Stop the background collection loop gracefully.

        Cancels the collection task and waits for it to finish. Should be
        called during application shutdown (FastAPI lifespan).

        Example:
            >>> await collector.stop()
        """
        self._running = False
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            logger.info("Metrics collector stopped")

    def _make_metric_key(self, name: str, labels: dict[str, str] | None) -> str:
        """Create a unique key for a metric with labels.

        Args:
            name: Metric name
            labels: Optional labels dictionary

        Returns:
            Unique string key combining name and sorted labels.

        Example:
            >>> collector._make_metric_key("api.requests", {"endpoint": "/verify", "method": "POST"})
            'api.requests{endpoint="/verify",method="POST"}'
        """
        if not labels:
            return name

        # Sort labels for consistent key generation
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Singleton instance for dependency injection
_metrics_collector_instance: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the singleton MetricsCollector instance.

    Use this function for FastAPI dependency injection to ensure
    the same collector instance is used throughout the application.

    Returns:
        Singleton MetricsCollector instance.

    Example:
        In FastAPI route:
        >>> from fastapi import Depends
        >>> @app.get("/api/metrics")
        >>> async def get_metrics(collector: MetricsCollector = Depends(get_metrics_collector)):
        ...     return await collector.store.get_all_metric_names()
    """
    global _metrics_collector_instance
    if _metrics_collector_instance is None:
        _metrics_collector_instance = MetricsCollector()
    return _metrics_collector_instance
