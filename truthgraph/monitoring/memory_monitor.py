"""Memory monitoring utilities for tracking system and process memory usage.

This module provides real-time memory monitoring capabilities with support for
tracking process memory, detecting memory leaks, and generating alerts when
memory usage exceeds configured thresholds.

The MemoryMonitor class integrates with psutil for system-level metrics,
tracemalloc for Python-level tracking, and provides a clean API for continuous
monitoring in production environments.

Performance targets:
    - Peak memory usage <4GB
    - Memory leak detection <10 MB/hour growth
    - Real-time monitoring with minimal overhead
    - Per-component memory attribution

Example:
    >>> monitor = MemoryMonitor()
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> snapshot = monitor.get_current_snapshot()
    >>> print(f"Memory: {snapshot['rss_mb']:.1f} MB")
    >>> monitor.stop()
"""

import gc
import logging
import os
import sys
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time.

    Attributes:
        timestamp: ISO format timestamp when snapshot was taken
        process_id: PID of the monitored process
        rss_mb: Resident set size in MB (actual physical memory)
        vms_mb: Virtual memory size in MB
        percent: Percentage of system memory used by process
        available_system_mb: Available system memory in MB
        total_system_mb: Total system memory in MB
        python_allocated_mb: Python-specific memory allocation (tracemalloc)
        num_threads: Number of active threads
        num_fds: Number of open file descriptors (Unix only)
        cpu_percent: CPU usage percentage
    """

    timestamp: str
    process_id: int
    rss_mb: float
    vms_mb: float
    percent: float
    available_system_mb: float
    total_system_mb: float
    python_allocated_mb: float
    num_threads: int
    num_fds: int
    cpu_percent: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "process_id": self.process_id,
            "rss_mb": round(self.rss_mb, 2),
            "vms_mb": round(self.vms_mb, 2),
            "percent": round(self.percent, 2),
            "available_system_mb": round(self.available_system_mb, 2),
            "total_system_mb": round(self.total_system_mb, 2),
            "python_allocated_mb": round(self.python_allocated_mb, 2),
            "num_threads": self.num_threads,
            "num_fds": self.num_fds,
            "cpu_percent": round(self.cpu_percent, 2),
        }


@dataclass
class MemoryStats:
    """Statistical analysis of memory usage over time.

    Attributes:
        mean_rss_mb: Average RSS memory usage
        max_rss_mb: Peak RSS memory usage
        min_rss_mb: Minimum RSS memory usage
        std_dev_rss_mb: Standard deviation of RSS
        growth_rate_mb_per_sec: Linear growth rate (for leak detection)
        total_snapshots: Number of snapshots analyzed
        duration_seconds: Time period covered
    """

    mean_rss_mb: float
    max_rss_mb: float
    min_rss_mb: float
    std_dev_rss_mb: float
    growth_rate_mb_per_sec: float
    total_snapshots: int
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for JSON serialization."""
        return {
            "mean_rss_mb": round(self.mean_rss_mb, 2),
            "max_rss_mb": round(self.max_rss_mb, 2),
            "min_rss_mb": round(self.min_rss_mb, 2),
            "std_dev_rss_mb": round(self.std_dev_rss_mb, 2),
            "growth_rate_mb_per_sec": round(self.growth_rate_mb_per_sec, 6),
            "growth_rate_mb_per_hour": round(self.growth_rate_mb_per_sec * 3600, 2),
            "total_snapshots": self.total_snapshots,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class MemoryMonitor:
    """Real-time memory monitoring with leak detection and alerting.

    This class provides comprehensive memory monitoring capabilities including:
    - Real-time process memory tracking
    - Python-level memory allocation tracking (tracemalloc)
    - Memory leak detection via linear regression
    - Statistical analysis of memory patterns
    - Component-level memory attribution

    The monitor can run continuously with periodic snapshots or be used for
    one-time measurements. It integrates with the alert system to notify
    when memory usage exceeds configured thresholds.

    Attributes:
        process: psutil.Process instance for current process
        snapshots: List of memory snapshots over time
        start_time: Timestamp when monitoring started
        tracemalloc_enabled: Whether Python tracemalloc is active
    """

    def __init__(self, enable_tracemalloc: bool = True) -> None:
        """Initialize memory monitor.

        Args:
            enable_tracemalloc: Whether to enable Python-level memory tracking.
                Adds some overhead but provides detailed allocation info.
        """
        self.process = psutil.Process(os.getpid())
        self.snapshots: List[MemorySnapshot] = []
        self.start_time: Optional[float] = None
        self.tracemalloc_enabled = enable_tracemalloc
        self._component_markers: Dict[str, List[float]] = defaultdict(list)

        if self.tracemalloc_enabled and not tracemalloc.is_tracing():
            tracemalloc.start()
            logger.info("Started tracemalloc for detailed Python memory tracking")

    def start(self) -> None:
        """Start continuous monitoring.

        Captures initial baseline snapshot and records start time.
        """
        self.start_time = time.time()
        initial_snapshot = self.capture_snapshot()
        logger.info(
            f"Memory monitoring started: {initial_snapshot.rss_mb:.1f} MB RSS, "
            f"{initial_snapshot.percent:.1f}% of system memory"
        )

    def stop(self) -> MemoryStats:
        """Stop monitoring and return statistics.

        Returns:
            MemoryStats object with statistical analysis of all snapshots
        """
        final_snapshot = self.capture_snapshot()
        stats = self.calculate_statistics()

        logger.info(
            f"Memory monitoring stopped: {final_snapshot.rss_mb:.1f} MB RSS, "
            f"Peak: {stats.max_rss_mb:.1f} MB, "
            f"Growth: {stats.growth_rate_mb_per_sec * 3600:.2f} MB/hour"
        )

        return stats

    def capture_snapshot(self) -> MemorySnapshot:
        """Capture current memory state.

        Returns:
            MemorySnapshot with current memory metrics
        """
        # Force garbage collection for accurate measurement
        gc.collect()

        # Get process memory info
        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()

        # Get system memory info
        sys_mem = psutil.virtual_memory()

        # Get Python-specific memory if tracemalloc is enabled
        python_allocated_mb = 0.0
        if self.tracemalloc_enabled and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            python_allocated_mb = current / (1024 * 1024)

        # Get thread and file descriptor info
        num_threads = self.process.num_threads()
        num_fds = 0
        try:
            if sys.platform != "win32":
                num_fds = self.process.num_fds()
        except (AttributeError, psutil.AccessDenied):
            pass

        # Get CPU usage
        cpu_percent = self.process.cpu_percent(interval=0.1)

        snapshot = MemorySnapshot(
            timestamp=datetime.utcnow().isoformat(),
            process_id=self.process.pid,
            rss_mb=mem_info.rss / (1024 * 1024),
            vms_mb=mem_info.vms / (1024 * 1024),
            percent=mem_percent,
            available_system_mb=sys_mem.available / (1024 * 1024),
            total_system_mb=sys_mem.total / (1024 * 1024),
            python_allocated_mb=python_allocated_mb,
            num_threads=num_threads,
            num_fds=num_fds,
            cpu_percent=cpu_percent,
        )

        self.snapshots.append(snapshot)
        return snapshot

    def get_current_snapshot(self) -> MemorySnapshot:
        """Get the most recent snapshot.

        Returns:
            Most recent MemorySnapshot, or captures new one if none exist
        """
        if not self.snapshots:
            return self.capture_snapshot()
        return self.snapshots[-1]

    def calculate_statistics(self) -> MemoryStats:
        """Calculate statistical metrics from all snapshots.

        Returns:
            MemoryStats with mean, max, min, std dev, and growth rate

        Raises:
            ValueError: If no snapshots have been captured
        """
        if not self.snapshots:
            raise ValueError("No snapshots available for statistics")

        rss_values = [s.rss_mb for s in self.snapshots]
        n = len(rss_values)

        # Calculate basic statistics
        mean_rss = sum(rss_values) / n
        max_rss = max(rss_values)
        min_rss = min(rss_values)

        # Calculate standard deviation
        variance = sum((x - mean_rss) ** 2 for x in rss_values) / n
        std_dev = variance**0.5

        # Calculate growth rate using linear regression
        growth_rate = 0.0
        if n >= 2 and self.start_time:
            duration = time.time() - self.start_time
            if duration > 0:
                # Simple linear regression: slope = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
                times = [(i * duration / (n - 1)) for i in range(n)]
                sum_x = sum(times)
                sum_y = sum(rss_values)
                sum_xy = sum(t * m for t, m in zip(times, rss_values))
                sum_x2 = sum(t * t for t in times)

                denominator = n * sum_x2 - sum_x * sum_x
                if abs(denominator) > 1e-10:
                    growth_rate = (n * sum_xy - sum_x * sum_y) / denominator

        return MemoryStats(
            mean_rss_mb=mean_rss,
            max_rss_mb=max_rss,
            min_rss_mb=min_rss,
            std_dev_rss_mb=std_dev,
            growth_rate_mb_per_sec=growth_rate,
            total_snapshots=n,
            duration_seconds=time.time() - self.start_time if self.start_time else 0,
        )

    def mark_component(self, component_name: str) -> None:
        """Mark memory usage for a specific component.

        This allows attributing memory usage to different system components
        by capturing memory before and after component initialization/usage.

        Args:
            component_name: Name of the component (e.g., "embedding_model")
        """
        snapshot = self.capture_snapshot()
        self._component_markers[component_name].append(snapshot.rss_mb)
        logger.debug(f"Marked memory for component '{component_name}': {snapshot.rss_mb:.1f} MB")

    def get_component_memory(self, component_name: str) -> Dict[str, float]:
        """Get memory usage attributed to a component.

        Args:
            component_name: Name of the component

        Returns:
            Dictionary with memory metrics for the component
        """
        markers = self._component_markers.get(component_name, [])
        if len(markers) < 2:
            return {"error": "Insufficient markers for component"}

        # Calculate delta between first and last marker
        delta = markers[-1] - markers[0]

        return {
            "component": component_name,
            "initial_mb": round(markers[0], 2),
            "current_mb": round(markers[-1], 2),
            "delta_mb": round(delta, 2),
            "num_measurements": len(markers),
        }

    def detect_memory_leak(self, threshold_mb_per_hour: float = 10.0) -> Dict[str, Any]:
        """Detect potential memory leaks based on growth rate.

        Args:
            threshold_mb_per_hour: Growth rate threshold for leak detection

        Returns:
            Dictionary with leak detection results
        """
        stats = self.calculate_statistics()
        growth_per_hour = stats.growth_rate_mb_per_sec * 3600

        leak_detected = abs(growth_per_hour) > threshold_mb_per_hour

        return {
            "leak_detected": leak_detected,
            "growth_rate_mb_per_hour": round(growth_per_hour, 2),
            "threshold_mb_per_hour": threshold_mb_per_hour,
            "duration_minutes": round(stats.duration_seconds / 60, 2),
            "total_growth_mb": round(stats.max_rss_mb - self.snapshots[0].rss_mb, 2)
            if self.snapshots
            else 0,
        }

    def get_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations using tracemalloc.

        Args:
            limit: Number of top allocations to return

        Returns:
            List of top allocations with file, line, and size info
        """
        if not self.tracemalloc_enabled or not tracemalloc.is_tracing():
            return []

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        allocations = []
        for stat in top_stats[:limit]:
            allocations.append(
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": round(stat.size / (1024 * 1024), 3),
                    "count": stat.count,
                }
            )

        return allocations

    def reset(self) -> None:
        """Reset monitoring state and clear all snapshots."""
        self.snapshots.clear()
        self._component_markers.clear()
        self.start_time = None
        gc.collect()
        logger.info("Memory monitor reset")
