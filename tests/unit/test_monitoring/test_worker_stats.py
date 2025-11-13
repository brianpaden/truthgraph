"""Unit tests for Worker statistics collector."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, UTC

import pytest

from truthgraph.monitoring.collectors.worker_stats import WorkerStatsCollector
from truthgraph.monitoring.metrics_collector import MetricsCollector
from truthgraph.workers.task_status import TaskMetadata, TaskState


@pytest.fixture
def mock_metrics_collector():
    """Create a mock metrics collector."""
    collector = Mock(spec=MetricsCollector)
    collector.set_gauge = AsyncMock()
    collector.increment_counter = AsyncMock()
    return collector


@pytest.fixture
def mock_task_queue():
    """Create a mock task queue."""
    queue = Mock()
    queue.max_workers = 5
    queue.is_running = True
    queue.queue = Mock()
    queue.queue.qsize.return_value = 2
    queue.tasks = {}
    return queue


@pytest.fixture
def worker_collector(mock_metrics_collector, mock_task_queue):
    """Create worker stats collector with mocks."""
    return WorkerStatsCollector(mock_metrics_collector, mock_task_queue)


class TestWorkerStatsCollector:
    """Test cases for WorkerStatsCollector."""

    @pytest.mark.asyncio
    async def test_initialization(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test collector initialization."""
        assert worker_collector.metrics_collector == mock_metrics_collector
        assert worker_collector._task_queue == mock_task_queue
        assert worker_collector._last_completed_count == 0
        assert worker_collector._total_tasks == 0

    @pytest.mark.asyncio
    async def test_collect_stats_no_queue(self, mock_metrics_collector):
        """Test collection when task queue is unavailable."""
        collector = WorkerStatsCollector(mock_metrics_collector, None)

        with patch.object(collector, "_get_task_queue", return_value=None):
            # Should not raise exception
            await collector.collect_stats()

        # No metrics should be recorded
        mock_metrics_collector.set_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_stats_basic_metrics(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test basic metrics collection."""
        # Setup task queue with no tasks
        mock_task_queue.tasks = {}

        await worker_collector.collect_stats()

        # Verify basic metrics were recorded
        mock_metrics_collector.set_gauge.assert_any_call("workers.pool.size", 5)
        mock_metrics_collector.set_gauge.assert_any_call("queue.tasks.pending", 2)
        mock_metrics_collector.set_gauge.assert_any_call("workers.active.count", 0)
        mock_metrics_collector.set_gauge.assert_any_call("workers.idle.count", 5)

    @pytest.mark.asyncio
    async def test_collect_stats_with_active_workers(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test metrics collection with active workers."""
        # Create mock task metadata
        task1 = Mock(spec=TaskMetadata)
        task1.state = Mock()
        task1.state.value = "processing"

        task2 = Mock(spec=TaskMetadata)
        task2.state = Mock()
        task2.state.value = "processing"

        task3 = Mock(spec=TaskMetadata)
        task3.state = Mock()
        task3.state.value = "completed"

        mock_task_queue.tasks = {
            "task1": task1,
            "task2": task2,
            "task3": task3,
        }

        await worker_collector.collect_stats()

        # Verify active/idle workers
        mock_metrics_collector.set_gauge.assert_any_call("workers.active.count", 2)
        mock_metrics_collector.set_gauge.assert_any_call("workers.idle.count", 3)
        mock_metrics_collector.set_gauge.assert_any_call("queue.tasks.processing", 2)

    @pytest.mark.asyncio
    async def test_collect_stats_task_counts(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test task state counting."""
        # Create tasks with different states
        processing_task = Mock(spec=TaskMetadata)
        processing_task.state = Mock()
        processing_task.state.value = "processing"

        completed_task = Mock(spec=TaskMetadata)
        completed_task.state = Mock()
        completed_task.state.value = "completed"

        failed_task = Mock(spec=TaskMetadata)
        failed_task.state = Mock()
        failed_task.state.value = "failed"

        mock_task_queue.tasks = {
            "task1": processing_task,
            "task2": completed_task,
            "task3": failed_task,
        }

        await worker_collector.collect_stats()

        # Verify task state metrics
        mock_metrics_collector.set_gauge.assert_any_call("queue.tasks.processing", 1)
        mock_metrics_collector.increment_counter.assert_any_call("queue.tasks.completed", 1)
        mock_metrics_collector.increment_counter.assert_any_call("queue.tasks.failed", 1)

    @pytest.mark.asyncio
    async def test_collect_stats_error_rate(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test error rate calculation."""
        # Create 8 completed and 2 failed tasks (20% error rate)
        mock_task_queue.tasks = {}

        for i in range(8):
            task = Mock(spec=TaskMetadata)
            task.state = Mock()
            task.state.value = "completed"
            mock_task_queue.tasks[f"task{i}"] = task

        for i in range(8, 10):
            task = Mock(spec=TaskMetadata)
            task.state = Mock()
            task.state.value = "failed"
            mock_task_queue.tasks[f"task{i}"] = task

        await worker_collector.collect_stats()

        # Verify error rate is calculated correctly (20%)
        mock_metrics_collector.set_gauge.assert_any_call("task.error.rate", 20.0)

    @pytest.mark.asyncio
    async def test_collect_stats_zero_error_rate(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test error rate when no tasks have finished."""
        mock_task_queue.tasks = {}

        await worker_collector.collect_stats()

        # Should set error rate to 0
        mock_metrics_collector.set_gauge.assert_any_call("task.error.rate", 0.0)

    @pytest.mark.asyncio
    async def test_check_health_healthy(self, worker_collector, mock_task_queue):
        """Test health check when everything is healthy."""
        # Setup healthy state
        processing_task = Mock(spec=TaskMetadata)
        processing_task.state = Mock()
        processing_task.state.value = "processing"

        mock_task_queue.tasks = {"task1": processing_task}
        mock_task_queue.queue.qsize.return_value = 10

        status, message = await worker_collector.check_health()

        assert status == "healthy"
        assert "workers active" in message

    @pytest.mark.asyncio
    async def test_check_health_degraded_queue_backup(self, worker_collector, mock_task_queue):
        """Test health check with queue backup."""
        mock_task_queue.queue.qsize.return_value = 75  # Queue backup

        status, message = await worker_collector.check_health()

        assert status == "degraded"
        assert "Queue backup" in message

    @pytest.mark.asyncio
    async def test_check_health_degraded_error_rate(self, worker_collector, mock_task_queue):
        """Test health check with elevated error rate."""
        # Create tasks with 7% error rate
        completed_task = Mock(spec=TaskMetadata)
        completed_task.state = Mock()
        completed_task.state.value = "completed"

        failed_task = Mock(spec=TaskMetadata)
        failed_task.state = Mock()
        failed_task.state.value = "failed"

        mock_task_queue.tasks = {}
        for i in range(93):
            mock_task_queue.tasks[f"completed{i}"] = completed_task
        for i in range(7):
            mock_task_queue.tasks[f"failed{i}"] = failed_task

        mock_task_queue.queue.qsize.return_value = 10

        status, message = await worker_collector.check_health()

        assert status == "degraded"
        assert "error rate" in message.lower()

    @pytest.mark.asyncio
    async def test_check_health_unhealthy_workers_stopped(self, worker_collector, mock_task_queue):
        """Test health check when workers are not running."""
        mock_task_queue.is_running = False

        status, message = await worker_collector.check_health()

        assert status == "unhealthy"
        assert "not running" in message

    @pytest.mark.asyncio
    async def test_check_health_unhealthy_queue_critical(self, worker_collector, mock_task_queue):
        """Test health check with critical queue depth."""
        mock_task_queue.queue.qsize.return_value = 150

        status, message = await worker_collector.check_health()

        assert status == "unhealthy"
        assert "critical" in message.lower()

    @pytest.mark.asyncio
    async def test_check_health_unhealthy_high_error_rate(self, worker_collector, mock_task_queue):
        """Test health check with high error rate."""
        # Create tasks with 15% error rate
        completed_task = Mock(spec=TaskMetadata)
        completed_task.state = Mock()
        completed_task.state.value = "completed"

        failed_task = Mock(spec=TaskMetadata)
        failed_task.state = Mock()
        failed_task.state.value = "failed"

        mock_task_queue.tasks = {}
        for i in range(85):
            mock_task_queue.tasks[f"completed{i}"] = completed_task
        for i in range(15):
            mock_task_queue.tasks[f"failed{i}"] = failed_task

        mock_task_queue.queue.qsize.return_value = 10

        status, message = await worker_collector.check_health()

        assert status == "unhealthy"
        assert "error rate" in message.lower()

    @pytest.mark.asyncio
    async def test_get_worker_details(self, worker_collector, mock_task_queue):
        """Test detailed worker information retrieval."""
        # Setup task queue state
        processing_task = Mock(spec=TaskMetadata)
        processing_task.state = Mock()
        processing_task.state.value = "processing"

        completed_task = Mock(spec=TaskMetadata)
        completed_task.state = Mock()
        completed_task.state.value = "completed"

        failed_task = Mock(spec=TaskMetadata)
        failed_task.state = Mock()
        failed_task.state.value = "failed"

        mock_task_queue.tasks = {
            "task1": processing_task,
            "task2": completed_task,
            "task3": failed_task,
        }
        mock_task_queue.queue.qsize.return_value = 5

        details = await worker_collector.get_worker_details()

        assert details["available"] is True
        assert details["running"] is True
        assert details["pool_size"] == 5
        assert details["active_workers"] == 1
        assert details["idle_workers"] == 4
        assert details["queue"]["pending"] == 5
        assert details["queue"]["processing"] == 1
        assert details["queue"]["completed"] == 1
        assert details["queue"]["failed"] == 1
        assert details["statistics"]["total_tasks"] == 3

    @pytest.mark.asyncio
    async def test_get_worker_details_unavailable(self, mock_metrics_collector):
        """Test getting details when queue is unavailable."""
        collector = WorkerStatsCollector(mock_metrics_collector, None)

        with patch.object(collector, "_get_task_queue", return_value=None):
            details = await collector.get_worker_details()

            assert details["available"] is False
            assert "error" in details

    @pytest.mark.asyncio
    async def test_collect_stats_handles_exception(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test that collection handles exceptions gracefully."""
        mock_task_queue.queue.qsize.side_effect = Exception("Queue error")

        # Should not raise exception
        await worker_collector.collect_stats()

    @pytest.mark.asyncio
    async def test_throughput_calculation(self, worker_collector, mock_metrics_collector, mock_task_queue):
        """Test throughput calculation over time."""
        import time

        # Setup initial state
        completed_task = Mock(spec=TaskMetadata)
        completed_task.state = Mock()
        completed_task.state.value = "completed"

        mock_task_queue.tasks = {"task1": completed_task}

        # First collection
        worker_collector._last_throughput_time = time.time() - 11  # 11 seconds ago
        worker_collector._last_completed_count = 0

        await worker_collector.collect_stats()

        # Should calculate throughput (1 task / 11 seconds ≈ 0.091)
        # Verify throughput was recorded
        calls = [call for call in mock_metrics_collector.set_gauge.call_args_list
                 if call[0][0] == "queue.throughput.tasks_per_second"]
        assert len(calls) > 0
