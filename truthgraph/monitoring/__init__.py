"""Memory monitoring and alerting system for TruthGraph.

This module provides comprehensive memory monitoring capabilities including:
- Real-time memory usage tracking
- Memory leak detection
- Configurable alerting system
- Historical profile storage and analysis

Example:
    Basic monitoring:
    >>> from truthgraph.monitoring import MemoryMonitor
    >>> monitor = MemoryMonitor()
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> stats = monitor.stop()

    With alerting:
    >>> from truthgraph.monitoring import MemoryMonitor, AlertManager, AlertLevel
    >>> monitor = MemoryMonitor()
    >>> alerts = AlertManager()
    >>> alerts.set_threshold(AlertLevel.WARNING, rss_mb=2048)
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> snapshot = monitor.get_current_snapshot()
    >>> triggered = alerts.check_thresholds(snapshot)

    Historical analysis:
    >>> from truthgraph.monitoring import MemoryProfileStore
    >>> store = MemoryProfileStore()
    >>> profile_id = store.save_profile("test_run", monitor)
    >>> trend = store.analyze_trend("test_run", days=7)
"""

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

__all__ = [
    # Memory monitoring
    "MemoryMonitor",
    "MemorySnapshot",
    "MemoryStats",
    # Alerting
    "AlertLevel",
    "AlertManager",
    "MemoryAlert",
    # Profiling
    "MemoryProfile",
    "MemoryProfileStore",
    "MemoryTrend",
]
