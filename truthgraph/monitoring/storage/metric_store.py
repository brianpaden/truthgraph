"""Thread-safe in-memory time-series storage for metrics.

This module provides a memory-efficient circular buffer implementation for
storing metric values with automatic eviction of old data. Designed to handle
concurrent access from multiple async workers.
"""

import asyncio
import time
from collections import deque
from typing import Any

from truthgraph.monitoring.storage.models import MetricValue


class MetricStore:
    """Thread-safe in-memory storage for time-series metrics.

    Uses collections.deque with maxlen for automatic circular buffer behavior.
    Optimized for:
    - 70+ metrics with 360 entries each (1 hour at 10s intervals)
    - Concurrent access from 5 async workers
    - Memory footprint < 2 MB
    - Lock-free reads for performance

    The store uses asyncio.Lock for write operations to prevent race conditions
    when multiple workers record metrics simultaneously.

    Attributes:
        retention_seconds: How long to retain metric data (default 3600 = 1 hour)
        max_size: Maximum entries per metric (retention_seconds / 10)

    Example:
        >>> store = MetricStore(retention_seconds=3600)
        >>> await store.record_metric("api.requests", 42.0, labels={"endpoint": "/verify"})
        >>> values = await store.get_metric("api.requests")
        >>> recent = await store.get_metrics_range("api.requests", duration_seconds=300)
    """

    def __init__(self, retention_seconds: int = 3600):
        """Initialize metric store.

        Args:
            retention_seconds: Duration to retain metrics in seconds (default 1 hour)
        """
        self._retention_seconds = retention_seconds
        self._max_size = retention_seconds // 10  # 10 second collection interval
        self._metrics: dict[str, deque[MetricValue]] = {}
        self._lock = asyncio.Lock()

    async def record_metric(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a metric value with timestamp and optional labels.

        Thread-safe operation that creates a new deque if the metric doesn't exist.
        Uses asyncio.Lock to prevent race conditions during concurrent writes.

        Args:
            name: Metric name (e.g., "api.requests.count")
            value: Numeric metric value
            labels: Optional labels for metric dimensions (e.g., {"service": "api"})

        Example:
            >>> await store.record_metric("cpu.percent", 45.2)
            >>> await store.record_metric("requests.count", 1, labels={"endpoint": "/health"})
        """
        metric_value = MetricValue(
            timestamp=time.time(), value=value, labels=labels if labels else None
        )

        async with self._lock:
            if name not in self._metrics:
                # Create new deque with maxlen for automatic eviction
                self._metrics[name] = deque(maxlen=self._max_size)
            self._metrics[name].append(metric_value)

    async def get_metric(self, name: str) -> list[MetricValue]:
        """Retrieve all stored values for a metric.

        Returns a snapshot of all values currently in the circular buffer.
        This operation is read-only and doesn't require locking for performance.

        Args:
            name: Metric name to retrieve

        Returns:
            List of MetricValue objects, ordered oldest to newest.
            Empty list if metric doesn't exist.

        Example:
            >>> values = await store.get_metric("api.requests")
            >>> len(values)
            360
        """
        if name not in self._metrics:
            return []
        # Return a snapshot copy to avoid mutation issues
        return list(self._metrics[name])

    async def get_metrics_range(
        self, name: str, duration_seconds: int | None = None
    ) -> list[MetricValue]:
        """Retrieve metric values within a time range.

        Args:
            name: Metric name to retrieve
            duration_seconds: How far back to look (default: all available data)

        Returns:
            List of MetricValue objects within the time range, ordered oldest to newest.
            Empty list if metric doesn't exist or no values in range.

        Example:
            >>> # Get last 5 minutes of data
            >>> recent = await store.get_metrics_range("cpu.percent", duration_seconds=300)
        """
        if name not in self._metrics:
            return []

        values = list(self._metrics[name])

        if duration_seconds is None:
            return values

        cutoff_time = time.time() - duration_seconds
        return [v for v in values if v.timestamp >= cutoff_time]

    async def get_latest(self, name: str) -> MetricValue | None:
        """Get the most recent value for a metric.

        Args:
            name: Metric name to retrieve

        Returns:
            Most recent MetricValue or None if metric doesn't exist or is empty.

        Example:
            >>> latest = await store.get_latest("cpu.percent")
            >>> if latest:
            ...     print(f"Current CPU: {latest.value}%")
        """
        if name not in self._metrics or len(self._metrics[name]) == 0:
            return None
        return self._metrics[name][-1]

    async def get_all_metric_names(self) -> list[str]:
        """Get names of all metrics currently stored.

        Returns:
            List of metric names, sorted alphabetically.

        Example:
            >>> names = await store.get_all_metric_names()
            >>> print(names)
            ['api.requests.count', 'cpu.percent', 'memory.rss.mb']
        """
        return sorted(self._metrics.keys())

    async def clear_metric(self, name: str) -> bool:
        """Clear all values for a specific metric.

        Args:
            name: Metric name to clear

        Returns:
            True if metric existed and was cleared, False if metric didn't exist.

        Example:
            >>> await store.clear_metric("test.metric")
            True
        """
        async with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False

    async def get_memory_usage(self) -> dict[str, Any]:
        """Estimate memory usage of the metric store.

        Returns:
            Dictionary with memory statistics:
            - metric_count: Number of unique metrics
            - total_entries: Total number of metric values stored
            - estimated_bytes: Rough memory footprint estimate

        Example:
            >>> usage = await store.get_memory_usage()
            >>> print(f"Using ~{usage['estimated_bytes'] / 1024 / 1024:.2f} MB")
        """
        metric_count = len(self._metrics)
        total_entries = sum(len(deque) for deque in self._metrics.values())

        # Rough estimate: MetricValue with slots ~80 bytes each
        # Plus overhead for deque and dict structures
        estimated_bytes = (total_entries * 80) + (metric_count * 200)

        return {
            "metric_count": metric_count,
            "total_entries": total_entries,
            "estimated_bytes": estimated_bytes,
            "max_entries_per_metric": self._max_size,
            "retention_seconds": self._retention_seconds,
        }
