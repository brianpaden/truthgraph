"""Unit tests for MetricsCollector."""

import asyncio
import time

import pytest

from truthgraph.monitoring.metrics_collector import MetricsCollector, get_metrics_collector
from truthgraph.monitoring.storage.metric_store import MetricStore


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()

        assert collector.store is not None
        assert collector.collection_interval == 10
        assert collector.start_time > 0
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_initialization_with_custom_store(self):
        """Test initialization with custom metric store."""
        custom_store = MetricStore(retention_seconds=1800)
        collector = MetricsCollector(store=custom_store, collection_interval=5)

        assert collector.store is custom_store
        assert collector.collection_interval == 5

    @pytest.mark.asyncio
    async def test_increment_counter(self):
        """Test incrementing a counter."""
        collector = MetricsCollector()

        await collector.increment_counter("api.requests")
        await collector.increment_counter("api.requests")
        await collector.increment_counter("api.requests")

        # Get the latest value
        latest = await collector.store.get_latest("api.requests")
        assert latest is not None
        assert latest.value == 3.0

    @pytest.mark.asyncio
    async def test_increment_counter_with_value(self):
        """Test incrementing counter by custom value."""
        collector = MetricsCollector()

        await collector.increment_counter("bytes.sent", 1024.0)
        await collector.increment_counter("bytes.sent", 2048.0)
        await collector.increment_counter("bytes.sent", 512.0)

        latest = await collector.store.get_latest("bytes.sent")
        assert latest is not None
        assert latest.value == 3584.0  # 1024 + 2048 + 512

    @pytest.mark.asyncio
    async def test_increment_counter_with_labels(self):
        """Test incrementing counter with labels."""
        collector = MetricsCollector()

        labels_post = {"method": "POST", "endpoint": "/verify"}
        labels_get = {"method": "GET", "endpoint": "/verify"}

        await collector.increment_counter("api.requests", labels=labels_post)
        await collector.increment_counter("api.requests", labels=labels_post)
        await collector.increment_counter("api.requests", labels=labels_get)

        # Should have 2 values recorded for the metric (different label combos)
        values = await collector.store.get_metric("api.requests")
        assert len(values) == 3  # 2 POST + 1 GET

    @pytest.mark.asyncio
    async def test_set_gauge(self):
        """Test setting gauge values."""
        collector = MetricsCollector()

        await collector.set_gauge("cpu.percent", 45.2)
        await asyncio.sleep(0.001)
        await collector.set_gauge("cpu.percent", 52.1)
        await asyncio.sleep(0.001)
        await collector.set_gauge("cpu.percent", 38.7)

        values = await collector.store.get_metric("cpu.percent")
        assert len(values) == 3
        assert values[0].value == 45.2
        assert values[1].value == 52.1
        assert values[2].value == 38.7

    @pytest.mark.asyncio
    async def test_set_gauge_with_labels(self):
        """Test setting gauge with labels."""
        collector = MetricsCollector()

        await collector.set_gauge("cpu.percent", 45.0, labels={"core": "0"})
        await collector.set_gauge("cpu.percent", 52.0, labels={"core": "1"})

        values = await collector.store.get_metric("cpu.percent")
        assert len(values) == 2

    @pytest.mark.asyncio
    async def test_record_histogram(self):
        """Test recording histogram observations."""
        collector = MetricsCollector()

        # Record response times
        await collector.record_histogram("api.response_time_ms", 123.4)
        await collector.record_histogram("api.response_time_ms", 156.7)
        await collector.record_histogram("api.response_time_ms", 98.2)
        await collector.record_histogram("api.response_time_ms", 234.5)

        values = await collector.store.get_metric("api.response_time_ms")
        assert len(values) == 4
        assert values[0].value == 123.4
        assert values[1].value == 156.7

    @pytest.mark.asyncio
    async def test_record_histogram_with_labels(self):
        """Test recording histogram with labels."""
        collector = MetricsCollector()

        await collector.record_histogram(
            "api.response_time_ms", 123.4, labels={"endpoint": "/verify"}
        )
        await collector.record_histogram(
            "api.response_time_ms", 56.7, labels={"endpoint": "/health"}
        )

        values = await collector.store.get_metric("api.response_time_ms")
        assert len(values) == 2

    @pytest.mark.asyncio
    async def test_get_uptime_seconds(self):
        """Test getting uptime."""
        collector = MetricsCollector()

        # Should be very close to 0 on creation
        uptime = await collector.get_uptime_seconds()
        assert uptime >= 0
        assert uptime < 2  # Should be under 2 seconds

        # Wait a bit and check again
        await asyncio.sleep(0.2)  # Increased delay for reliability
        uptime2 = await collector.get_uptime_seconds()
        assert uptime2 >= uptime  # Allow equal in case of rounding

    @pytest.mark.asyncio
    async def test_make_metric_key(self):
        """Test metric key generation for counters with labels."""
        collector = MetricsCollector()

        # No labels
        key1 = collector._make_metric_key("api.requests", None)
        assert key1 == "api.requests"

        # With labels (should be sorted)
        labels = {"endpoint": "/verify", "method": "POST"}
        key2 = collector._make_metric_key("api.requests", labels)
        assert key2 == 'api.requests{endpoint="/verify",method="POST"}'

        # Same labels, different order (should produce same key)
        labels_reversed = {"method": "POST", "endpoint": "/verify"}
        key3 = collector._make_metric_key("api.requests", labels_reversed)
        assert key2 == key3


class TestMetricsCollectorBackground:
    """Test background collection loop."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping collector."""
        collector = MetricsCollector(collection_interval=1)

        # Start collector
        await collector.start()
        assert collector._running is True
        assert collector._collection_task is not None
        assert not collector._collection_task.done()

        # Let it run for a bit
        await asyncio.sleep(0.5)

        # Stop collector
        await collector.stop()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_collect_metrics_store_stats(self):
        """Test collecting metric store statistics."""
        collector = MetricsCollector()

        # Add some metrics
        await collector.increment_counter("test.counter")
        await collector.set_gauge("test.gauge", 42.0)

        # Collect stats
        await collector.collect_metrics_store_stats()

        # Check that monitoring metrics were recorded
        metric_count = await collector.store.get_latest("monitoring.metrics.count")
        assert metric_count is not None
        assert metric_count.value >= 2  # At least the 2 test metrics

        total_entries = await collector.store.get_latest("monitoring.entries.total")
        assert total_entries is not None
        assert total_entries.value >= 2

    @pytest.mark.asyncio
    async def test_collection_loop_runs(self):
        """Test that collection loop actually runs periodically."""
        collector = MetricsCollector(collection_interval=0.1)  # Fast interval for testing

        # Start collector
        await collector.start()

        # Wait for a few collection cycles
        await asyncio.sleep(0.35)

        # Stop collector
        await collector.stop()

        # Check that monitoring metrics were collected
        last_collection = await collector.store.get_latest(
            "monitoring.last_collection_timestamp"
        )
        assert last_collection is not None
        assert last_collection.value > 0


class TestMetricsCollectorConcurrency:
    """Test concurrent access to metrics collector."""

    @pytest.mark.asyncio
    async def test_concurrent_counter_increments(self):
        """Test concurrent counter increments from multiple tasks."""
        collector = MetricsCollector()

        async def increment_task(task_id: int, count: int):
            """Increment counter multiple times."""
            for _ in range(count):
                await collector.increment_counter("concurrent.counter")

        # Run 10 tasks, each incrementing 50 times
        tasks = [increment_task(i, 50) for i in range(10)]
        await asyncio.gather(*tasks)

        # Final counter value should be exactly 500
        latest = await collector.store.get_latest("concurrent.counter")
        assert latest is not None
        assert latest.value == 500.0

    @pytest.mark.asyncio
    async def test_concurrent_gauge_sets(self):
        """Test concurrent gauge sets from multiple tasks."""
        collector = MetricsCollector()

        async def set_gauge_task(task_id: int, count: int):
            """Set gauge values multiple times."""
            for i in range(count):
                await collector.set_gauge("concurrent.gauge", float(task_id * 100 + i))

        # Run 5 tasks, each setting 20 values
        tasks = [set_gauge_task(i, 20) for i in range(5)]
        await asyncio.gather(*tasks)

        # Should have 100 total values recorded
        values = await collector.store.get_metric("concurrent.gauge")
        assert len(values) == 100

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self):
        """Test concurrent mix of counters, gauges, and histograms."""
        collector = MetricsCollector()

        async def counter_task():
            for _ in range(50):
                await collector.increment_counter("test.counter")

        async def gauge_task():
            for i in range(50):
                await collector.set_gauge("test.gauge", float(i))

        async def histogram_task():
            for i in range(50):
                await collector.record_histogram("test.histogram", float(i * 10))

        # Run all tasks concurrently
        await asyncio.gather(counter_task(), gauge_task(), histogram_task())

        # Verify all metrics were recorded correctly
        counter_latest = await collector.store.get_latest("test.counter")
        assert counter_latest is not None
        assert counter_latest.value == 50.0

        gauge_values = await collector.store.get_metric("test.gauge")
        assert len(gauge_values) == 50

        histogram_values = await collector.store.get_metric("test.histogram")
        assert len(histogram_values) == 50


class TestGetMetricsCollector:
    """Test singleton instance function."""

    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns singleton."""
        # Reset global instance first
        import truthgraph.monitoring.metrics_collector as mc_module
        mc_module._metrics_collector_instance = None

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Should be the same instance
        assert collector1 is collector2

    def test_get_metrics_collector_creates_instance(self):
        """Test that get_metrics_collector creates instance if needed."""
        import truthgraph.monitoring.metrics_collector as mc_module
        mc_module._metrics_collector_instance = None

        collector = get_metrics_collector()
        assert collector is not None
        assert isinstance(collector, MetricsCollector)
