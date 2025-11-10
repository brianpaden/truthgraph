"""Comprehensive monitoring and alerting system for TruthGraph.

This module provides monitoring capabilities including:
- Real-time memory usage tracking
- Memory leak detection
- Configurable alerting system
- Historical profile storage and analysis
- Metrics collection and time-series storage
- Health checking with circuit breaker pattern

Example:
    Memory monitoring:
    >>> from truthgraph.monitoring import MemoryMonitor
    >>> monitor = MemoryMonitor()
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> stats = monitor.stop()

    Metrics collection:
    >>> from truthgraph.monitoring import get_metrics_collector
    >>> collector = get_metrics_collector()
    >>> await collector.increment_counter("api.requests")
    >>> await collector.set_gauge("cpu.percent", 45.2)

    Health checking:
    >>> from truthgraph.monitoring import get_health_checker
    >>> checker = get_health_checker()
    >>> health = await checker.check_overall_health()
"""

from truthgraph.monitoring.health import HealthChecker, get_health_checker
from truthgraph.monitoring.memory_alerts import (
    AlertLevel,
    AlertManager,
    MemoryAlert,
)
from truthgraph.monitoring.memory_monitor import (
    MemoryMonitor,
    MemorySnapshot,
    MemoryStats,
)
from truthgraph.monitoring.memory_profiles import (
    MemoryProfile,
    MemoryProfileStore,
    MemoryTrend,
)
from truthgraph.monitoring.metrics_collector import (
    MetricsCollector,
    get_metrics_collector,
)
from truthgraph.monitoring.storage import (
    DetailedHealthResponse,
    HealthResponse,
    HealthStatus,
    MetricStore,
    MetricType,
    MetricValue,
    ServiceHealth,
)

__all__ = [
    # Memory monitoring
    "MemoryMonitor",
    "MemorySnapshot",
    "MemoryStats",
    # Memory alerting
    "AlertLevel",
    "AlertManager",
    "MemoryAlert",
    # Memory profiling
    "MemoryProfile",
    "MemoryProfileStore",
    "MemoryTrend",
    # Metrics collection
    "MetricsCollector",
    "get_metrics_collector",
    "MetricStore",
    "MetricType",
    "MetricValue",
    # Health checking
    "HealthChecker",
    "get_health_checker",
    "HealthStatus",
    "HealthResponse",
    "ServiceHealth",
    "DetailedHealthResponse",
]
