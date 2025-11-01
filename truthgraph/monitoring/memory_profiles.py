"""Historical memory profiling and analysis for tracking trends over time.

This module provides utilities for storing, retrieving, and analyzing memory
profiles across multiple runs. It enables trend analysis, performance regression
detection, and historical comparison of memory usage patterns.

The MemoryProfileStore persists memory profiles to disk and provides query
capabilities for analyzing memory trends and detecting anomalies.

Example:
    >>> from truthgraph.monitoring.memory_profiles import MemoryProfileStore
    >>> from truthgraph.monitoring.memory_monitor import MemoryMonitor
    >>>
    >>> store = MemoryProfileStore()
    >>> monitor = MemoryMonitor()
    >>> monitor.start()
    >>> # ... perform operations ...
    >>> stats = monitor.stop()
    >>> profile_id = store.save_profile("embedding_test", monitor, stats)
    >>> trend = store.analyze_trend("embedding_test", days=7)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from truthgraph.monitoring.memory_monitor import MemoryMonitor, MemorySnapshot, MemoryStats

logger = logging.getLogger(__name__)


@dataclass
class MemoryProfile:
    """Complete memory profile for a test run or operation.

    Attributes:
        profile_id: Unique identifier for this profile
        name: Descriptive name for the profile
        timestamp: ISO format timestamp when profile was created
        stats: Statistical analysis of memory usage
        snapshots: List of memory snapshots during operation
        metadata: Additional context (environment, config, etc.)
    """
    profile_id: str
    name: str
    timestamp: str
    stats: MemoryStats
    snapshots: List[MemorySnapshot]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "timestamp": self.timestamp,
            "stats": self.stats.to_dict(),
            "num_snapshots": len(self.snapshots),
            "first_snapshot": self.snapshots[0].to_dict() if self.snapshots else None,
            "last_snapshot": self.snapshots[-1].to_dict() if self.snapshots else None,
            "peak_snapshot": max(self.snapshots, key=lambda s: s.rss_mb).to_dict() if self.snapshots else None,
            "metadata": self.metadata
        }

    def to_dict_full(self) -> Dict[str, Any]:
        """Convert profile to dictionary with all snapshots."""
        data = self.to_dict()
        data["snapshots"] = [s.to_dict() for s in self.snapshots]
        return data


@dataclass
class MemoryTrend:
    """Analysis of memory trends over time.

    Attributes:
        name: Profile name being analyzed
        num_profiles: Number of profiles in trend
        time_range_days: Time range covered
        mean_rss_trend: Average RSS memory trend (MB/day)
        peak_rss_trend: Peak RSS memory trend (MB/day)
        regression_detected: Whether performance regression detected
        profiles: List of profiles in chronological order
    """
    name: str
    num_profiles: int
    time_range_days: float
    mean_rss_trend: float
    peak_rss_trend: float
    regression_detected: bool
    profiles: List[MemoryProfile]

    def to_dict(self) -> Dict[str, Any]:
        """Convert trend to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "num_profiles": self.num_profiles,
            "time_range_days": round(self.time_range_days, 2),
            "mean_rss_trend_mb_per_day": round(self.mean_rss_trend, 3),
            "peak_rss_trend_mb_per_day": round(self.peak_rss_trend, 3),
            "regression_detected": self.regression_detected,
            "first_profile_date": self.profiles[0].timestamp if self.profiles else None,
            "last_profile_date": self.profiles[-1].timestamp if self.profiles else None,
            "mean_rss_mb": round(
                sum(p.stats.mean_rss_mb for p in self.profiles) / len(self.profiles), 2
            ) if self.profiles else 0,
            "peak_rss_mb": max(p.stats.max_rss_mb for p in self.profiles) if self.profiles else 0
        }


class MemoryProfileStore:
    """Persistent storage and analysis of memory profiles.

    This class manages a collection of memory profiles stored as JSON files
    on disk. It provides query, comparison, and trend analysis capabilities
    for tracking memory usage patterns over time.

    Attributes:
        storage_dir: Directory where profiles are stored
        index_file: Path to the profile index file
    """

    DEFAULT_STORAGE_DIR = Path("scripts/profiling/results/memory_profiles")

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        """Initialize profile store.

        Args:
            storage_dir: Directory for storing profiles (creates if needed)
        """
        self.storage_dir = storage_dir or self.DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.storage_dir / "index.json"
        self._ensure_index()

        logger.info(f"MemoryProfileStore initialized at {self.storage_dir}")

    def _ensure_index(self) -> None:
        """Ensure index file exists."""
        if not self.index_file.exists():
            self._write_index({"profiles": [], "by_name": {}})

    def _read_index(self) -> Dict[str, Any]:
        """Read the profile index."""
        with open(self.index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_index(self, index: Dict[str, Any]) -> None:
        """Write the profile index."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    def save_profile(
        self,
        name: str,
        monitor: MemoryMonitor,
        stats: Optional[MemoryStats] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a memory profile from a monitor.

        Args:
            name: Descriptive name for the profile
            monitor: MemoryMonitor instance with snapshots
            stats: Pre-calculated statistics (or None to calculate)
            metadata: Additional context to store with profile

        Returns:
            Profile ID (unique identifier)
        """
        if stats is None:
            stats = monitor.calculate_statistics()

        timestamp = datetime.utcnow().isoformat()
        profile_id = f"{name}_{timestamp.replace(':', '-').replace('.', '-')}"

        profile = MemoryProfile(
            profile_id=profile_id,
            name=name,
            timestamp=timestamp,
            stats=stats,
            snapshots=monitor.snapshots.copy(),
            metadata=metadata or {}
        )

        # Save full profile to file
        profile_file = self.storage_dir / f"{profile_id}.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict_full(), f, indent=2)

        # Update index
        index = self._read_index()
        index["profiles"].append({
            "profile_id": profile_id,
            "name": name,
            "timestamp": timestamp,
            "file": str(profile_file.name)
        })

        if name not in index["by_name"]:
            index["by_name"][name] = []
        index["by_name"][name].append(profile_id)

        self._write_index(index)

        logger.info(f"Saved memory profile: {profile_id}")
        return profile_id

    def get_profile(self, profile_id: str) -> Optional[MemoryProfile]:
        """Retrieve a profile by ID.

        Args:
            profile_id: Unique profile identifier

        Returns:
            MemoryProfile if found, None otherwise
        """
        profile_file = self.storage_dir / f"{profile_id}.json"

        if not profile_file.exists():
            logger.warning(f"Profile not found: {profile_id}")
            return None

        with open(profile_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Reconstruct profile from JSON
        # Filter out fields added by to_dict() that aren't in the dataclass
        stats_data = {
            k: v for k, v in data["stats"].items()
            if k in ['mean_rss_mb', 'max_rss_mb', 'min_rss_mb', 'std_dev_rss_mb',
                     'growth_rate_mb_per_sec', 'total_snapshots', 'duration_seconds']
        }
        stats = MemoryStats(**stats_data)
        snapshots = [MemorySnapshot(**s) for s in data.get("snapshots", [])]

        return MemoryProfile(
            profile_id=data["profile_id"],
            name=data["name"],
            timestamp=data["timestamp"],
            stats=stats,
            snapshots=snapshots,
            metadata=data.get("metadata", {})
        )

    def get_profiles_by_name(
        self,
        name: str,
        limit: Optional[int] = None
    ) -> List[MemoryProfile]:
        """Get all profiles for a specific name.

        Args:
            name: Profile name to search for
            limit: Maximum number of profiles to return (most recent first)

        Returns:
            List of matching profiles
        """
        index = self._read_index()
        profile_ids = index["by_name"].get(name, [])

        # Get most recent first
        profile_ids = list(reversed(profile_ids))

        if limit:
            profile_ids = profile_ids[:limit]

        profiles = []
        for profile_id in profile_ids:
            profile = self.get_profile(profile_id)
            if profile:
                profiles.append(profile)

        return profiles

    def analyze_trend(
        self,
        name: str,
        days: Optional[int] = None,
        regression_threshold_mb: float = 50.0
    ) -> Optional[MemoryTrend]:
        """Analyze memory trends for a profile name.

        Args:
            name: Profile name to analyze
            days: Number of days to include (None for all)
            regression_threshold_mb: Threshold for regression detection

        Returns:
            MemoryTrend with trend analysis, or None if insufficient data
        """
        profiles = self.get_profiles_by_name(name)

        if len(profiles) < 2:
            logger.warning(f"Insufficient profiles for trend analysis: {name}")
            return None

        # Filter by date range if specified
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            profiles = [
                p for p in profiles
                if datetime.fromisoformat(p.timestamp) >= cutoff
            ]

        if len(profiles) < 2:
            return None

        # Sort chronologically
        profiles.sort(key=lambda p: p.timestamp)

        # Calculate time range
        first_time = datetime.fromisoformat(profiles[0].timestamp)
        last_time = datetime.fromisoformat(profiles[-1].timestamp)
        time_range = (last_time - first_time).total_seconds() / 86400  # days

        # Calculate trends using linear regression
        mean_rss_values = [p.stats.mean_rss_mb for p in profiles]
        peak_rss_values = [p.stats.max_rss_mb for p in profiles]

        mean_rss_trend = self._calculate_trend(mean_rss_values, time_range)
        peak_rss_trend = self._calculate_trend(peak_rss_values, time_range)

        # Detect regression (memory increasing over time)
        regression_detected = (
            mean_rss_trend > regression_threshold_mb / max(time_range, 1) or
            peak_rss_trend > regression_threshold_mb / max(time_range, 1)
        )

        return MemoryTrend(
            name=name,
            num_profiles=len(profiles),
            time_range_days=time_range,
            mean_rss_trend=mean_rss_trend,
            peak_rss_trend=peak_rss_trend,
            regression_detected=regression_detected,
            profiles=profiles
        )

    def _calculate_trend(self, values: List[float], time_range_days: float) -> float:
        """Calculate linear trend (slope per day).

        Args:
            values: List of measurements
            time_range_days: Time range covered

        Returns:
            Trend in units per day
        """
        if len(values) < 2 or time_range_days <= 0:
            return 0.0

        n = len(values)
        # Create evenly spaced time points
        times = [i * time_range_days / (n - 1) for i in range(n)]

        # Linear regression
        sum_x = sum(times)
        sum_y = sum(values)
        sum_xy = sum(t * v for t, v in zip(times, values))
        sum_x2 = sum(t * t for t in times)

        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-10:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def compare_profiles(
        self,
        profile_id1: str,
        profile_id2: str
    ) -> Dict[str, Any]:
        """Compare two memory profiles.

        Args:
            profile_id1: First profile ID
            profile_id2: Second profile ID

        Returns:
            Dictionary with comparison metrics
        """
        p1 = self.get_profile(profile_id1)
        p2 = self.get_profile(profile_id2)

        if not p1 or not p2:
            return {"error": "One or both profiles not found"}

        mean_diff = p2.stats.mean_rss_mb - p1.stats.mean_rss_mb
        peak_diff = p2.stats.max_rss_mb - p1.stats.max_rss_mb
        mean_pct_change = (mean_diff / p1.stats.mean_rss_mb) * 100 if p1.stats.mean_rss_mb else 0
        peak_pct_change = (peak_diff / p1.stats.max_rss_mb) * 100 if p1.stats.max_rss_mb else 0

        return {
            "profile_1": {
                "id": p1.profile_id,
                "timestamp": p1.timestamp,
                "mean_rss_mb": round(p1.stats.mean_rss_mb, 2),
                "peak_rss_mb": round(p1.stats.max_rss_mb, 2)
            },
            "profile_2": {
                "id": p2.profile_id,
                "timestamp": p2.timestamp,
                "mean_rss_mb": round(p2.stats.mean_rss_mb, 2),
                "peak_rss_mb": round(p2.stats.max_rss_mb, 2)
            },
            "comparison": {
                "mean_rss_diff_mb": round(mean_diff, 2),
                "peak_rss_diff_mb": round(peak_diff, 2),
                "mean_rss_pct_change": round(mean_pct_change, 2),
                "peak_rss_pct_change": round(peak_pct_change, 2),
                "regression": mean_diff > 0 or peak_diff > 0
            }
        }

    def list_profiles(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all profiles in the store.

        Args:
            limit: Maximum number of profiles to return (most recent first)

        Returns:
            List of profile summaries
        """
        index = self._read_index()
        profiles = index["profiles"]

        # Most recent first
        profiles = list(reversed(profiles))

        if limit:
            profiles = profiles[:limit]

        return profiles

    def cleanup_old_profiles(self, days: int = 30) -> int:
        """Remove profiles older than specified days.

        Args:
            days: Age threshold for deletion

        Returns:
            Number of profiles deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        index = self._read_index()

        to_delete = []
        for profile_info in index["profiles"]:
            profile_time = datetime.fromisoformat(profile_info["timestamp"])
            if profile_time < cutoff:
                to_delete.append(profile_info)

        # Delete files and update index
        for profile_info in to_delete:
            profile_file = self.storage_dir / profile_info["file"]
            if profile_file.exists():
                profile_file.unlink()

            # Remove from by_name index
            name = profile_info["name"]
            if name in index["by_name"]:
                index["by_name"][name] = [
                    pid for pid in index["by_name"][name]
                    if pid != profile_info["profile_id"]
                ]

        # Update main index
        index["profiles"] = [p for p in index["profiles"] if p not in to_delete]
        self._write_index(index)

        logger.info(f"Deleted {len(to_delete)} old profiles")
        return len(to_delete)
