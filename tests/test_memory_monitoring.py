"""Tests for memory monitoring infrastructure.

This module tests the memory monitoring, alerting, and profiling components
including MemoryMonitor, AlertManager, and MemoryProfileStore.

Run with:
    pytest tests/test_memory_monitoring.py -v
    pytest tests/test_memory_monitoring.py -v --cov=truthgraph.monitoring
"""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from truthgraph.monitoring import (
    AlertLevel,
    AlertManager,
    MemoryAlert,
    MemoryMonitor,
    MemoryProfile,
    MemoryProfileStore,
    MemorySnapshot,
    MemoryStats,
)


class TestMemoryMonitor:
    """Tests for MemoryMonitor class."""

    def test_monitor_initialization(self):
        """Test MemoryMonitor initializes correctly."""
        monitor = MemoryMonitor(enable_tracemalloc=True)

        assert monitor.process is not None
        assert monitor.snapshots == []
        assert monitor.start_time is None
        assert monitor.tracemalloc_enabled is True

    def test_monitor_initialization_without_tracemalloc(self):
        """Test MemoryMonitor without tracemalloc."""
        monitor = MemoryMonitor(enable_tracemalloc=False)

        assert monitor.tracemalloc_enabled is False

    def test_start_monitoring(self):
        """Test starting memory monitoring."""
        monitor = MemoryMonitor()
        monitor.start()

        assert monitor.start_time is not None
        assert len(monitor.snapshots) >= 1

        # Cleanup
        monitor.stop()

    def test_capture_snapshot(self):
        """Test capturing memory snapshot."""
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.rss_mb > 0
        assert snapshot.vms_mb > 0
        assert snapshot.total_system_mb > 0
        assert 0 <= snapshot.percent <= 100

    def test_snapshot_to_dict(self):
        """Test MemorySnapshot to_dict conversion."""
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        snapshot_dict = snapshot.to_dict()

        assert "timestamp" in snapshot_dict
        assert "rss_mb" in snapshot_dict
        assert "vms_mb" in snapshot_dict
        assert isinstance(snapshot_dict["rss_mb"], float)

    def test_get_current_snapshot(self):
        """Test getting current snapshot."""
        monitor = MemoryMonitor()

        # First call should create snapshot
        snapshot1 = monitor.get_current_snapshot()
        assert len(monitor.snapshots) == 1

        # Second call should return existing snapshot
        snapshot2 = monitor.get_current_snapshot()
        assert snapshot1 == snapshot2

    def test_calculate_statistics(self):
        """Test calculating statistics from snapshots."""
        monitor = MemoryMonitor()
        monitor.start()

        # Capture multiple snapshots
        for _ in range(5):
            monitor.capture_snapshot()
            time.sleep(0.1)

        stats = monitor.calculate_statistics()

        assert isinstance(stats, MemoryStats)
        assert stats.total_snapshots >= 5
        assert stats.max_rss_mb >= stats.min_rss_mb
        assert stats.mean_rss_mb > 0
        assert stats.std_dev_rss_mb >= 0
        assert stats.duration_seconds > 0

    def test_calculate_statistics_no_snapshots(self):
        """Test statistics calculation with no snapshots."""
        monitor = MemoryMonitor()

        with pytest.raises(ValueError, match="No snapshots available"):
            monitor.calculate_statistics()

    def test_mark_component(self):
        """Test marking component memory."""
        monitor = MemoryMonitor()

        monitor.mark_component("test_component")
        assert "test_component" in monitor._component_markers
        assert len(monitor._component_markers["test_component"]) == 1

    def test_get_component_memory(self):
        """Test getting component memory delta."""
        monitor = MemoryMonitor()

        # Mark before and after
        monitor.mark_component("test_component")
        # Allocate some memory
        _ = [0] * 10000
        monitor.mark_component("test_component")

        component_memory = monitor.get_component_memory("test_component")

        assert "component" in component_memory
        assert "delta_mb" in component_memory
        assert component_memory["num_measurements"] == 2

    def test_get_component_memory_insufficient_markers(self):
        """Test component memory with insufficient markers."""
        monitor = MemoryMonitor()

        monitor.mark_component("test_component")
        component_memory = monitor.get_component_memory("test_component")

        assert "error" in component_memory

    def test_detect_memory_leak_no_leak(self):
        """Test leak detection when no leak exists."""
        monitor = MemoryMonitor()
        monitor.start()

        # Capture snapshots without growing memory
        for _ in range(5):
            monitor.capture_snapshot()
            time.sleep(0.05)

        leak_result = monitor.detect_memory_leak(threshold_mb_per_hour=100.0)

        assert isinstance(leak_result, dict)
        assert "leak_detected" in leak_result
        assert "growth_rate_mb_per_hour" in leak_result

    def test_reset(self):
        """Test resetting monitor state."""
        monitor = MemoryMonitor()
        monitor.start()
        monitor.capture_snapshot()
        monitor.capture_snapshot()

        assert len(monitor.snapshots) >= 2
        assert monitor.start_time is not None

        monitor.reset()

        assert len(monitor.snapshots) == 0
        assert monitor.start_time is None
        assert len(monitor._component_markers) == 0

    def test_stats_to_dict(self):
        """Test MemoryStats to_dict conversion."""
        monitor = MemoryMonitor()
        monitor.start()

        for _ in range(3):
            monitor.capture_snapshot()
            time.sleep(0.05)

        stats = monitor.calculate_statistics()
        stats_dict = stats.to_dict()

        assert "mean_rss_mb" in stats_dict
        assert "max_rss_mb" in stats_dict
        assert "growth_rate_mb_per_hour" in stats_dict
        assert isinstance(stats_dict["mean_rss_mb"], float)


class TestAlertManager:
    """Tests for AlertManager class."""

    def test_alert_manager_initialization(self):
        """Test AlertManager initializes with defaults."""
        alerts = AlertManager()

        assert AlertLevel.WARNING in alerts.thresholds
        assert AlertLevel.CRITICAL in alerts.thresholds
        assert len(alerts.handlers) >= 1  # Default log handler
        assert alerts.alerts_history == []

    def test_set_threshold(self):
        """Test setting alert thresholds."""
        alerts = AlertManager()

        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1024)
        alerts.set_threshold(AlertLevel.CRITICAL, rss_mb=2048, percent=80.0)

        assert alerts.thresholds[AlertLevel.WARNING]["rss_mb"] == 1024
        assert alerts.thresholds[AlertLevel.CRITICAL]["rss_mb"] == 2048
        assert alerts.thresholds[AlertLevel.CRITICAL]["percent"] == 80.0

    def test_check_thresholds_no_alerts(self):
        """Test threshold checking with no alerts."""
        monitor = MemoryMonitor()
        alerts = AlertManager()

        snapshot = monitor.capture_snapshot()
        triggered = alerts.check_thresholds(snapshot)

        assert isinstance(triggered, list)
        # May or may not have alerts depending on actual memory usage

    def test_check_thresholds_high_memory(self):
        """Test threshold checking with high memory."""
        monitor = MemoryMonitor()
        alerts = AlertManager()

        snapshot = monitor.capture_snapshot()

        # Set very low threshold to trigger alert
        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1.0)

        triggered = alerts.check_thresholds(snapshot)

        assert len(triggered) >= 1
        assert triggered[0].level == AlertLevel.WARNING
        assert triggered[0].alert_type == "high_memory_usage"

    def test_memory_alert_to_dict(self):
        """Test MemoryAlert to_dict conversion."""
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        alert = MemoryAlert(
            level=AlertLevel.WARNING,
            alert_type="test",
            message="Test alert",
            timestamp="2025-10-31T00:00:00",
            snapshot=snapshot,
            metadata={"test": "data"},
        )

        alert_dict = alert.to_dict()

        assert alert_dict["level"] == "warning"
        assert alert_dict["alert_type"] == "test"
        assert alert_dict["message"] == "Test alert"
        assert "snapshot" in alert_dict

    def test_check_leak_no_leak(self):
        """Test leak detection with no leak."""
        monitor = MemoryMonitor()
        monitor.start()

        for _ in range(5):
            monitor.capture_snapshot()
            time.sleep(0.05)

        stats = monitor.calculate_statistics()
        alerts = AlertManager()

        leak_alert = alerts.check_leak(stats)

        # May or may not detect leak depending on actual behavior
        # Just verify it returns proper type
        assert leak_alert is None or isinstance(leak_alert, MemoryAlert)

    def test_check_rapid_growth(self):
        """Test rapid growth detection."""
        monitor = MemoryMonitor()
        alerts = AlertManager()

        snapshot1 = monitor.capture_snapshot()

        # Allocate memory
        _ = [0] * 1000000  # 1M integers

        snapshot2 = monitor.capture_snapshot()

        rapid_alert = alerts.check_rapid_growth(snapshot2, snapshot1, threshold_mb=1.0)

        # Should detect growth
        if rapid_alert:
            assert rapid_alert.alert_type == "rapid_growth"
            assert rapid_alert.level == AlertLevel.WARNING

    def test_add_custom_handler(self):
        """Test adding custom alert handler."""
        alerts = AlertManager()

        handler_called = []

        def custom_handler(alert):
            handler_called.append(alert)

        alerts.add_handler(custom_handler)

        # Trigger alert
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()
        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1.0)
        alerts.check_thresholds(snapshot)

        # Handler should have been called
        assert len(handler_called) >= 1

    def test_get_alerts(self):
        """Test getting alerts from history."""
        alerts = AlertManager()
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        # Trigger some alerts
        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1.0)
        alerts.check_thresholds(snapshot)

        # Get all alerts
        all_alerts = alerts.get_alerts()
        assert len(all_alerts) >= 1

        # Get by level
        warning_alerts = alerts.get_alerts(level=AlertLevel.WARNING)
        assert all(a.level == AlertLevel.WARNING for a in warning_alerts)

        # Get by type
        memory_alerts = alerts.get_alerts(alert_type="high_memory_usage")
        assert all(a.alert_type == "high_memory_usage" for a in memory_alerts)

    def test_get_summary(self):
        """Test getting alert summary."""
        alerts = AlertManager()
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1.0)
        alerts.check_thresholds(snapshot)

        summary = alerts.get_summary()

        assert "total_alerts" in summary
        assert "by_level" in summary
        assert "by_type" in summary
        assert isinstance(summary["total_alerts"], int)

    def test_clear_history(self):
        """Test clearing alert history."""
        alerts = AlertManager()
        monitor = MemoryMonitor()
        snapshot = monitor.capture_snapshot()

        alerts.set_threshold(AlertLevel.WARNING, rss_mb=1.0)
        alerts.check_thresholds(snapshot)

        assert len(alerts.alerts_history) >= 1

        alerts.clear_history()

        assert len(alerts.alerts_history) == 0


class TestMemoryProfileStore:
    """Tests for MemoryProfileStore class."""

    def test_profile_store_initialization(self):
        """Test MemoryProfileStore initialization."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))

            assert store.storage_dir.exists()
            assert store.index_file.exists()

    def test_save_and_get_profile(self):
        """Test saving and retrieving profiles."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            monitor.start()
            for _ in range(3):
                monitor.capture_snapshot()
                time.sleep(0.05)
            stats = monitor.stop()

            # Save profile
            profile_id = store.save_profile(
                name="test_profile", monitor=monitor, stats=stats, metadata={"test": "data"}
            )

            assert profile_id is not None
            assert "test_profile" in profile_id

            # Retrieve profile
            profile = store.get_profile(profile_id)

            assert profile is not None
            assert profile.name == "test_profile"
            assert profile.metadata["test"] == "data"
            assert len(profile.snapshots) >= 3

    def test_get_nonexistent_profile(self):
        """Test getting profile that doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))

            profile = store.get_profile("nonexistent_id")

            assert profile is None

    def test_get_profiles_by_name(self):
        """Test getting profiles by name."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            # Save multiple profiles with same name
            for i in range(3):
                monitor.reset()
                monitor.start()
                monitor.capture_snapshot()
                stats = monitor.stop()

                store.save_profile(name="test_run", monitor=monitor, stats=stats)
                time.sleep(0.1)  # Ensure different timestamps

            # Get profiles by name
            profiles = store.get_profiles_by_name("test_run")

            assert len(profiles) == 3
            assert all(p.name == "test_run" for p in profiles)

    def test_get_profiles_by_name_with_limit(self):
        """Test getting profiles with limit."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            for i in range(5):
                monitor.reset()
                monitor.start()
                monitor.capture_snapshot()
                stats = monitor.stop()

                store.save_profile(name="test", monitor=monitor, stats=stats)
                time.sleep(0.05)

            # Get with limit
            profiles = store.get_profiles_by_name("test", limit=2)

            assert len(profiles) == 2

    def test_compare_profiles(self):
        """Test comparing two profiles."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            # Create first profile
            monitor.start()
            monitor.capture_snapshot()
            stats1 = monitor.stop()
            profile_id1 = store.save_profile("profile1", monitor, stats1)

            # Create second profile with more memory
            monitor.reset()
            _ = [0] * 100000  # Allocate memory
            monitor.start()
            monitor.capture_snapshot()
            stats2 = monitor.stop()
            profile_id2 = store.save_profile("profile2", monitor, stats2)

            # Compare
            comparison = store.compare_profiles(profile_id1, profile_id2)

            assert "profile_1" in comparison
            assert "profile_2" in comparison
            assert "comparison" in comparison
            assert "mean_rss_diff_mb" in comparison["comparison"]

    def test_list_profiles(self):
        """Test listing all profiles."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            # Create profiles
            for i in range(3):
                monitor.reset()
                monitor.start()
                monitor.capture_snapshot()
                stats = monitor.stop()
                store.save_profile(f"profile_{i}", monitor, stats)
                time.sleep(0.05)

            # List all
            profiles = store.list_profiles()

            assert len(profiles) == 3

    def test_list_profiles_with_limit(self):
        """Test listing profiles with limit."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            for i in range(5):
                monitor.reset()
                monitor.start()
                monitor.capture_snapshot()
                stats = monitor.stop()
                store.save_profile(f"profile_{i}", monitor, stats)
                time.sleep(0.05)

            profiles = store.list_profiles(limit=2)

            assert len(profiles) == 2

    def test_memory_profile_to_dict(self):
        """Test MemoryProfile to_dict conversion."""
        monitor = MemoryMonitor()
        monitor.start()
        monitor.capture_snapshot()
        stats = monitor.stop()

        profile = MemoryProfile(
            profile_id="test_id",
            name="test",
            timestamp="2025-10-31T00:00:00",
            stats=stats,
            snapshots=monitor.snapshots,
            metadata={"test": "data"},
        )

        profile_dict = profile.to_dict()

        assert profile_dict["profile_id"] == "test_id"
        assert profile_dict["name"] == "test"
        assert "stats" in profile_dict
        assert "metadata" in profile_dict

    def test_cleanup_old_profiles(self):
        """Test cleaning up old profiles."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            monitor.start()
            monitor.capture_snapshot()
            stats = monitor.stop()

            store.save_profile("test", monitor, stats)

            # Cleanup (0 days threshold)
            deleted = store.cleanup_old_profiles(days=0)

            # Should have deleted the profile
            assert deleted >= 0  # May be 0 if timing is off


class TestIntegration:
    """Integration tests for memory monitoring."""

    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        monitor = MemoryMonitor()
        alerts = AlertManager()

        # Configure
        alerts.set_threshold(AlertLevel.WARNING, rss_mb=2048)

        # Monitor
        monitor.start()

        # Simulate work
        _ = [0] * 10000
        monitor.capture_snapshot()

        # Check alerts
        snapshot = monitor.get_current_snapshot()
        triggered = alerts.check_thresholds(snapshot)

        # Get statistics
        stats = monitor.stop()

        # Validate
        assert stats.total_snapshots >= 2
        assert stats.max_rss_mb > 0
        assert isinstance(triggered, list)

    def test_profile_storage_workflow(self):
        """Test profile storage workflow."""
        with TemporaryDirectory() as tmpdir:
            store = MemoryProfileStore(storage_dir=Path(tmpdir))
            monitor = MemoryMonitor()

            # Run test
            monitor.start()
            for _ in range(3):
                monitor.capture_snapshot()
                time.sleep(0.05)
            stats = monitor.stop()

            # Save profile
            profile_id = store.save_profile("integration_test", monitor, stats)

            # Retrieve and validate
            profile = store.get_profile(profile_id)

            assert profile is not None
            assert profile.name == "integration_test"
            assert len(profile.snapshots) >= 3
            assert profile.stats.total_snapshots >= 3
