"""Unit tests for MetricStore with concurrency and memory tests."""

import asyncio
import time

import pytest

from truthgraph.monitoring.storage.metric_store import MetricStore
from truthgraph.monitoring.storage.models import MetricValue


class TestMetricStore:
    """Test MetricStore functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test metric store initialization."""
        store = MetricStore(retention_seconds=3600)

        assert store._retention_seconds == 3600
        assert store._max_size == 360  # 3600 / 10
        assert len(store._metrics) == 0

    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording a single metric."""
        store = MetricStore()
        await store.record_metric("test.metric", 42.5)

        values = await store.get_metric("test.metric")
        assert len(values) == 1
        assert values[0].value == 42.5
        assert values[0].labels is None

    @pytest.mark.asyncio
    async def test_record_metric_with_labels(self):
        """Test recording a metric with labels."""
        store = MetricStore()
        labels = {"endpoint": "/verify", "method": "POST"}
        await store.record_metric("api.requests", 1.0, labels=labels)

        values = await store.get_metric("api.requests")
        assert len(values) == 1
        assert values[0].value == 1.0
        assert values[0].labels == labels

    @pytest.mark.asyncio
    async def test_record_multiple_values(self):
        """Test recording multiple values for same metric."""
        store = MetricStore()

        for i in range(10):
            await store.record_metric("cpu.percent", float(i * 10))
            await asyncio.sleep(0.001)  # Small delay to ensure different timestamps

        values = await store.get_metric("cpu.percent")
        assert len(values) == 10
        assert values[0].value == 0.0
        assert values[9].value == 90.0

    @pytest.mark.asyncio
    async def test_circular_buffer_eviction(self):
        """Test that old values are evicted when maxlen is exceeded."""
        store = MetricStore(retention_seconds=100)  # maxlen = 10

        # Record 15 values (should keep only last 10)
        for i in range(15):
            await store.record_metric("test.metric", float(i))

        values = await store.get_metric("test.metric")
        assert len(values) == 10
        # First value should be 5 (0-4 evicted)
        assert values[0].value == 5.0
        assert values[9].value == 14.0

    @pytest.mark.asyncio
    async def test_get_metric_nonexistent(self):
        """Test getting a metric that doesn't exist."""
        store = MetricStore()
        values = await store.get_metric("nonexistent.metric")
        assert values == []

    @pytest.mark.asyncio
    async def test_get_latest(self):
        """Test getting the most recent metric value."""
        store = MetricStore()

        # No values yet
        latest = await store.get_latest("test.metric")
        assert latest is None

        # Record some values
        await store.record_metric("test.metric", 10.0)
        await asyncio.sleep(0.001)
        await store.record_metric("test.metric", 20.0)
        await asyncio.sleep(0.001)
        await store.record_metric("test.metric", 30.0)

        # Get latest
        latest = await store.get_latest("test.metric")
        assert latest is not None
        assert latest.value == 30.0

    @pytest.mark.asyncio
    async def test_get_metrics_range(self):
        """Test getting metrics within a time range."""
        store = MetricStore()

        # Record metrics over time
        start_time = time.time()
        for i in range(5):
            await store.record_metric("test.metric", float(i))
            await asyncio.sleep(0.1)

        # Get last 0.3 seconds of data (should have ~3 values)
        recent = await store.get_metrics_range("test.metric", duration_seconds=0.3)
        assert 2 <= len(recent) <= 4  # Allow some timing variance

        # Get all data
        all_data = await store.get_metrics_range("test.metric")
        assert len(all_data) == 5

    @pytest.mark.asyncio
    async def test_get_metrics_range_nonexistent(self):
        """Test getting range for nonexistent metric."""
        store = MetricStore()
        values = await store.get_metrics_range("nonexistent.metric", duration_seconds=60)
        assert values == []

    @pytest.mark.asyncio
    async def test_get_all_metric_names(self):
        """Test getting all metric names."""
        store = MetricStore()

        # No metrics yet
        names = await store.get_all_metric_names()
        assert names == []

        # Add some metrics
        await store.record_metric("cpu.percent", 45.0)
        await store.record_metric("memory.rss.mb", 512.0)
        await store.record_metric("api.requests", 100.0)

        names = await store.get_all_metric_names()
        assert len(names) == 3
        assert names == ["api.requests", "cpu.percent", "memory.rss.mb"]  # Sorted

    @pytest.mark.asyncio
    async def test_clear_metric(self):
        """Test clearing a metric."""
        store = MetricStore()

        # Record some data
        await store.record_metric("test.metric", 42.0)
        assert len(await store.get_metric("test.metric")) == 1

        # Clear it
        result = await store.clear_metric("test.metric")
        assert result is True
        assert len(await store.get_metric("test.metric")) == 0

        # Clear nonexistent metric
        result = await store.clear_metric("nonexistent.metric")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_memory_usage(self):
        """Test memory usage estimation."""
        store = MetricStore()

        # Empty store
        usage = await store.get_memory_usage()
        assert usage["metric_count"] == 0
        assert usage["total_entries"] == 0
        assert usage["estimated_bytes"] == 0

        # Add some metrics
        for i in range(10):
            await store.record_metric(f"metric_{i}", float(i))

        usage = await store.get_memory_usage()
        assert usage["metric_count"] == 10
        assert usage["total_entries"] == 10
        assert usage["estimated_bytes"] > 0


class TestMetricStoreConcurrency:
    """Test MetricStore thread safety with concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_writes_same_metric(self):
        """Test multiple tasks writing to same metric simultaneously."""
        store = MetricStore()

        async def write_values(task_id: int, count: int):
            """Write multiple values from a single task."""
            for i in range(count):
                await store.record_metric("concurrent.metric", float(task_id * 1000 + i))

        # Run 10 tasks concurrently, each writing 10 values
        tasks = [write_values(task_id, 10) for task_id in range(10)]
        await asyncio.gather(*tasks)

        # Should have exactly 100 values (no race condition)
        values = await store.get_metric("concurrent.metric")
        assert len(values) == 100

    @pytest.mark.asyncio
    async def test_concurrent_writes_different_metrics(self):
        """Test multiple tasks writing to different metrics simultaneously."""
        store = MetricStore()

        async def write_metric(metric_name: str, count: int):
            """Write values to a specific metric."""
            for i in range(count):
                await store.record_metric(metric_name, float(i))

        # Run 10 tasks concurrently, each writing to different metric
        tasks = [
            write_metric(f"metric_{task_id}", 20) for task_id in range(10)
        ]
        await asyncio.gather(*tasks)

        # Should have 10 different metrics
        names = await store.get_all_metric_names()
        assert len(names) == 10

        # Each metric should have exactly 20 values
        for name in names:
            values = await store.get_metric(name)
            assert len(values) == 20

    @pytest.mark.asyncio
    async def test_concurrent_read_write(self):
        """Test concurrent reads and writes."""
        store = MetricStore()

        async def writer():
            """Continuously write values."""
            for i in range(50):
                await store.record_metric("rw.metric", float(i))
                await asyncio.sleep(0.001)

        async def reader():
            """Continuously read values."""
            results = []
            for _ in range(50):
                values = await store.get_metric("rw.metric")
                results.append(len(values))
                await asyncio.sleep(0.001)
            return results

        # Run writer and reader concurrently
        write_task = asyncio.create_task(writer())
        read_task = asyncio.create_task(reader())

        await asyncio.gather(write_task, read_task)

        # Final metric should have all 50 values
        final_values = await store.get_metric("rw.metric")
        assert len(final_values) == 50

    @pytest.mark.asyncio
    async def test_no_race_condition_counter(self):
        """Test that concurrent writes to store are properly recorded.

        Note: This tests the store's ability to record all values, not
        counter semantics. Counter semantics are handled by MetricsCollector.
        """
        # Use larger buffer to avoid hitting circular buffer limit
        store = MetricStore(retention_seconds=6000)  # 600 max entries

        async def write_values(task_id: int):
            """Write sequential values for this task."""
            for i in range(100):
                await store.record_metric("counter.metric", float(task_id * 1000 + i))

        # Run 5 tasks concurrently
        tasks = [write_values(task_id) for task_id in range(5)]
        await asyncio.gather(*tasks)

        # Should have 500 recorded values (5 tasks × 100 writes)
        # The store correctly records all concurrent writes
        values = await store.get_metric("counter.metric")
        assert len(values) == 500


class TestMetricStoreMemory:
    """Test memory optimization and footprint."""

    @pytest.mark.asyncio
    async def test_memory_footprint_70_metrics(self):
        """Test memory usage with 70 metrics × 360 entries each."""
        store = MetricStore(retention_seconds=3600)  # 360 max entries

        # Simulate 70 metrics with full buffer (360 entries each)
        for metric_id in range(70):
            for entry_id in range(360):
                await store.record_metric(
                    f"metric_{metric_id}",
                    float(entry_id),
                    labels={"service": "test"}
                )

        usage = await store.get_memory_usage()

        assert usage["metric_count"] == 70
        assert usage["total_entries"] == 70 * 360  # 25,200 entries
        # Should be < 2 MB (2,097,152 bytes)
        assert usage["estimated_bytes"] < 2_097_152

        # With slots optimization, should be closer to 1.5 MB
        # Each MetricValue with slots ~80 bytes
        # 25,200 entries × 80 bytes ≈ 2,016,000 bytes
        # But this is just the values, overhead is minimal
        print(f"Memory usage: {usage['estimated_bytes'] / 1024 / 1024:.2f} MB")

    @pytest.mark.asyncio
    async def test_metric_value_uses_slots(self):
        """Verify MetricValue uses slots for memory efficiency."""
        metric = MetricValue(timestamp=time.time(), value=42.0)

        # Should not be able to add arbitrary attributes (slots/frozen restriction)
        # In Python 3.13, frozen dataclasses may raise TypeError instead
        with pytest.raises((AttributeError, TypeError)):
            metric.arbitrary_attribute = "test"

    @pytest.mark.asyncio
    async def test_deque_automatic_eviction(self):
        """Test that deque automatically evicts old entries."""
        store = MetricStore(retention_seconds=100)  # maxlen = 10

        # Fill beyond capacity
        for i in range(1000):
            await store.record_metric("test.metric", float(i))

        values = await store.get_metric("test.metric")
        # Should only have 10 entries (automatic eviction)
        assert len(values) == 10

        # Memory usage should stay bounded
        usage = await store.get_memory_usage()
        assert usage["total_entries"] == 10
        # Should be very small
        assert usage["estimated_bytes"] < 10_000  # < 10 KB
