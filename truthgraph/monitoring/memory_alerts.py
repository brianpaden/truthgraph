"""Memory alerting system for monitoring and notifications.

This module provides a configurable alerting system for memory-related events
including high memory usage, memory leaks, and rapid memory growth. Alerts can
be logged, sent to monitoring systems, or trigger custom handlers.

The AlertManager integrates with MemoryMonitor to provide real-time alerting
with configurable thresholds and notification channels.

Example:
    >>> from truthgraph.monitoring.memory_monitor import MemoryMonitor
    >>> from truthgraph.monitoring.memory_alerts import AlertManager, AlertLevel
    >>>
    >>> monitor = MemoryMonitor()
    >>> alert_manager = AlertManager()
    >>> alert_manager.set_threshold(AlertLevel.WARNING, rss_mb=2048)
    >>> alert_manager.set_threshold(AlertLevel.CRITICAL, rss_mb=3500)
    >>>
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> alerts = alert_manager.check_thresholds(monitor.get_current_snapshot())
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from truthgraph.monitoring.memory_monitor import MemorySnapshot, MemoryStats

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MemoryAlert:
    """Represents a memory-related alert.

    Attributes:
        level: Severity level of the alert
        alert_type: Type of alert (high_memory, leak, rapid_growth, etc.)
        message: Human-readable alert message
        timestamp: ISO format timestamp when alert was triggered
        snapshot: Associated memory snapshot
        metadata: Additional context-specific data
    """
    level: AlertLevel
    alert_type: str
    message: str
    timestamp: str
    snapshot: Optional[MemorySnapshot] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            "level": self.level.value,
            "alert_type": self.alert_type,
            "message": self.message,
            "timestamp": self.timestamp,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "metadata": self.metadata
        }


class AlertManager:
    """Manages memory alerts with configurable thresholds and handlers.

    The AlertManager monitors memory usage and generates alerts when configured
    thresholds are exceeded. It supports multiple alert levels and can trigger
    custom handlers for each alert type.

    Attributes:
        thresholds: Dictionary of thresholds by alert level
        handlers: List of alert handler functions
        alerts_history: List of all triggered alerts
    """

    def __init__(self) -> None:
        """Initialize alert manager with default thresholds."""
        self.thresholds: Dict[AlertLevel, Dict[str, float]] = {
            AlertLevel.INFO: {},
            AlertLevel.WARNING: {},
            AlertLevel.CRITICAL: {}
        }

        self.handlers: List[Callable[[MemoryAlert], None]] = [
            self._default_log_handler
        ]

        self.alerts_history: List[MemoryAlert] = []

        # Set default thresholds
        self.set_threshold(AlertLevel.WARNING, rss_mb=2048)  # 2GB
        self.set_threshold(AlertLevel.CRITICAL, rss_mb=3500)  # 3.5GB
        self.set_threshold(AlertLevel.WARNING, growth_mb_per_hour=50)
        self.set_threshold(AlertLevel.CRITICAL, growth_mb_per_hour=100)

    def set_threshold(self, level: AlertLevel, **kwargs: float) -> None:
        """Set alert threshold for a specific level.

        Args:
            level: Alert level to configure
            **kwargs: Threshold values (e.g., rss_mb=2048, percent=80.0)
        """
        self.thresholds[level].update(kwargs)
        logger.info(f"Set {level.value} thresholds: {kwargs}")

    def add_handler(self, handler: Callable[[MemoryAlert], None]) -> None:
        """Add custom alert handler.

        Args:
            handler: Function that takes MemoryAlert and performs action
        """
        self.handlers.append(handler)
        logger.info(f"Added alert handler: {handler.__name__}")

    def check_thresholds(self, snapshot: MemorySnapshot) -> List[MemoryAlert]:
        """Check if current snapshot exceeds any thresholds.

        Args:
            snapshot: Current memory snapshot to check

        Returns:
            List of triggered alerts
        """
        alerts: List[MemoryAlert] = []

        # Check RSS memory thresholds
        for level in [AlertLevel.CRITICAL, AlertLevel.WARNING, AlertLevel.INFO]:
            rss_threshold = self.thresholds[level].get("rss_mb")
            if rss_threshold and snapshot.rss_mb >= rss_threshold:
                alert = MemoryAlert(
                    level=level,
                    alert_type="high_memory_usage",
                    message=f"Memory usage ({snapshot.rss_mb:.1f} MB) exceeded {level.value} threshold ({rss_threshold} MB)",
                    timestamp=datetime.utcnow().isoformat(),
                    snapshot=snapshot,
                    metadata={
                        "threshold_mb": rss_threshold,
                        "current_mb": snapshot.rss_mb,
                        "percent_of_system": snapshot.percent
                    }
                )
                alerts.append(alert)
                break  # Only trigger highest severity alert

        # Check memory percentage thresholds
        for level in [AlertLevel.CRITICAL, AlertLevel.WARNING, AlertLevel.INFO]:
            percent_threshold = self.thresholds[level].get("percent")
            if percent_threshold and snapshot.percent >= percent_threshold:
                alert = MemoryAlert(
                    level=level,
                    alert_type="high_memory_percent",
                    message=f"Memory usage ({snapshot.percent:.1f}%) exceeded {level.value} threshold ({percent_threshold}%)",
                    timestamp=datetime.utcnow().isoformat(),
                    snapshot=snapshot,
                    metadata={
                        "threshold_percent": percent_threshold,
                        "current_percent": snapshot.percent,
                        "rss_mb": snapshot.rss_mb
                    }
                )
                alerts.append(alert)
                break

        # Trigger handlers for all alerts
        for alert in alerts:
            self._trigger_alert(alert)

        return alerts

    def check_leak(self, stats: MemoryStats) -> Optional[MemoryAlert]:
        """Check for memory leak based on growth rate.

        Args:
            stats: Memory statistics with growth rate

        Returns:
            MemoryAlert if leak detected, None otherwise
        """
        growth_per_hour = stats.growth_rate_mb_per_sec * 3600

        # Check critical threshold first
        for level in [AlertLevel.CRITICAL, AlertLevel.WARNING]:
            threshold = self.thresholds[level].get("growth_mb_per_hour")
            if threshold and abs(growth_per_hour) >= threshold:
                alert = MemoryAlert(
                    level=level,
                    alert_type="memory_leak",
                    message=f"Potential memory leak detected: {growth_per_hour:.2f} MB/hour growth",
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "growth_mb_per_hour": growth_per_hour,
                        "threshold_mb_per_hour": threshold,
                        "duration_minutes": round(stats.duration_seconds / 60, 2),
                        "total_growth_mb": round(stats.max_rss_mb - stats.min_rss_mb, 2)
                    }
                )
                self._trigger_alert(alert)
                return alert

        return None

    def check_rapid_growth(
        self,
        current: MemorySnapshot,
        previous: MemorySnapshot,
        threshold_mb: float = 100
    ) -> Optional[MemoryAlert]:
        """Check for rapid memory growth between snapshots.

        Args:
            current: Current memory snapshot
            previous: Previous memory snapshot
            threshold_mb: Growth threshold in MB

        Returns:
            MemoryAlert if rapid growth detected, None otherwise
        """
        growth = current.rss_mb - previous.rss_mb

        if growth >= threshold_mb:
            alert = MemoryAlert(
                level=AlertLevel.WARNING,
                alert_type="rapid_growth",
                message=f"Rapid memory growth detected: {growth:.1f} MB increase",
                timestamp=datetime.utcnow().isoformat(),
                snapshot=current,
                metadata={
                    "growth_mb": growth,
                    "threshold_mb": threshold_mb,
                    "previous_mb": previous.rss_mb,
                    "current_mb": current.rss_mb
                }
            )
            self._trigger_alert(alert)
            return alert

        return None

    def _trigger_alert(self, alert: MemoryAlert) -> None:
        """Trigger alert by calling all registered handlers.

        Args:
            alert: Alert to trigger
        """
        self.alerts_history.append(alert)

        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")

    def _default_log_handler(self, alert: MemoryAlert) -> None:
        """Default handler that logs alerts.

        Args:
            alert: Alert to log
        """
        if alert.level == AlertLevel.CRITICAL:
            logger.critical(f"[MEMORY ALERT] {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"[MEMORY ALERT] {alert.message}")
        else:
            logger.info(f"[MEMORY ALERT] {alert.message}")

    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MemoryAlert]:
        """Get alerts from history with optional filtering.

        Args:
            level: Filter by alert level
            alert_type: Filter by alert type
            limit: Maximum number of alerts to return (most recent first)

        Returns:
            List of filtered alerts
        """
        alerts = self.alerts_history

        if level:
            alerts = [a for a in alerts if a.level == level]

        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        # Return most recent first
        alerts = list(reversed(alerts))

        if limit:
            alerts = alerts[:limit]

        return alerts

    def clear_history(self) -> None:
        """Clear all alerts from history."""
        self.alerts_history.clear()
        logger.info("Cleared alert history")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of alerts by level and type.

        Returns:
            Dictionary with alert counts and statistics
        """
        by_level = {level.value: 0 for level in AlertLevel}
        by_type: Dict[str, int] = {}

        for alert in self.alerts_history:
            by_level[alert.level.value] += 1
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1

        return {
            "total_alerts": len(self.alerts_history),
            "by_level": by_level,
            "by_type": by_type,
            "most_recent": self.alerts_history[-1].to_dict() if self.alerts_history else None
        }
