"""Worker pool and task queue statistics collector.

Monitors the async worker pool performance including active workers, task queue depth,
throughput metrics, and task success/failure rates.
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WorkerStatsCollector:
    """Collects metrics from the async worker pool and task queue.

    Tracks worker utilization, queue depth, task throughput, and
    task completion rates.

    Metrics collected:
    - workers.pool.size (gauge): Configured worker pool size
    - workers.active.count (gauge): Currently active workers
    - workers.idle.count (gauge): Idle workers waiting for tasks
    - queue.tasks.pending (gauge): Tasks waiting for processing
    - queue.tasks.processing (gauge): Tasks currently being processed
    - queue.tasks.total (counter): Total tasks processed since startup
    - queue.tasks.completed (counter): Successfully completed tasks
    - queue.tasks.failed (counter): Failed tasks
    - queue.throughput.tasks_per_second (gauge): Task processing rate
    - task.error.rate (gauge): Task failure rate percentage

    Attributes:
        metrics_collector: MetricsCollector instance for recording metrics
        task_queue: TaskQueue instance to monitor (optional, lazy-loaded)
        last_completed_count: Previous completed task count for throughput calculation
        last_throughput_time: Last time throughput was calculated

    Example:
        >>> collector = WorkerStatsCollector(metrics_collector)
        >>> await collector.collect_stats()
    """

    def __init__(self, metrics_collector: Any, task_queue: Any | None = None):
        """Initialize worker stats collector.

        Args:
            metrics_collector: MetricsCollector instance for recording metrics
            task_queue: Optional TaskQueue instance (lazy-loaded if not provided)
        """
        self.metrics_collector = metrics_collector
        self._task_queue = task_queue
        self._last_completed_count = 0
        self._last_throughput_time = time.time()
        self._total_tasks = 0

    def _get_task_queue(self) -> Any | None:
        """Get or lazy-load TaskQueue instance.

        Returns:
            TaskQueue instance or None if not available.
        """
        if self._task_queue is None:
            try:
                from truthgraph.workers.task_queue import get_task_queue

                self._task_queue = get_task_queue()
            except Exception as e:
                logger.warning(f"TaskQueue not available: {e}")
                return None

        return self._task_queue

    async def collect_stats(self) -> None:
        """Collect worker pool and task queue statistics.

        Gathers metrics from the TaskQueue and records them using the
        MetricsCollector.
        """
        task_queue = self._get_task_queue()
        if task_queue is None:
            # Task queue not available, skip collection
            return

        try:
            # Pool size
            await self.metrics_collector.set_gauge("workers.pool.size", task_queue.max_workers)

            # Queue depth
            queue_size = task_queue.queue.qsize()
            await self.metrics_collector.set_gauge("queue.tasks.pending", queue_size)

            # Active/idle workers
            # Count how many workers are currently processing tasks
            active_workers = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "processing"
            )
            idle_workers = task_queue.max_workers - active_workers

            await self.metrics_collector.set_gauge("workers.active.count", active_workers)
            await self.metrics_collector.set_gauge("workers.idle.count", idle_workers)

            # Task state counts
            processing_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "processing"
            )
            completed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "completed"
            )
            failed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "failed"
            )

            await self.metrics_collector.set_gauge("queue.tasks.processing", processing_count)

            # Total tasks (cumulative counter)
            total_tasks = len(task_queue.tasks)
            if total_tasks > self._total_tasks:
                # Increment counter by difference
                await self.metrics_collector.increment_counter(
                    "queue.tasks.total", total_tasks - self._total_tasks
                )
                self._total_tasks = total_tasks

            # Completed and failed counters
            await self.metrics_collector.increment_counter("queue.tasks.completed", completed_count)
            await self.metrics_collector.increment_counter("queue.tasks.failed", failed_count)

            # Calculate throughput (tasks/second)
            current_time = time.time()
            time_delta = current_time - self._last_throughput_time

            if time_delta >= 10.0:  # Calculate throughput every 10 seconds
                completed_delta = completed_count - self._last_completed_count
                throughput = completed_delta / time_delta if time_delta > 0 else 0.0

                await self.metrics_collector.set_gauge(
                    "queue.throughput.tasks_per_second", round(throughput, 3)
                )

                # Update state for next calculation
                self._last_completed_count = completed_count
                self._last_throughput_time = current_time

            # Calculate error rate
            total_finished = completed_count + failed_count
            if total_finished > 0:
                error_rate = (failed_count / total_finished) * 100.0
                await self.metrics_collector.set_gauge("task.error.rate", round(error_rate, 2))
            else:
                await self.metrics_collector.set_gauge("task.error.rate", 0.0)

        except Exception as e:
            logger.error(f"Error collecting worker stats: {e}", exc_info=True)

    async def check_health(self) -> tuple[str, str]:
        """Check worker pool health status.

        Returns:
            Tuple of (status, message) where status is "healthy", "degraded", or "unhealthy".

        Health criteria:
        - healthy: Workers running, queue depth < 50, error rate < 5%
        - degraded: Queue depth 50-100 or error rate 5-10%
        - unhealthy: No workers running or queue depth > 100 or error rate > 10%
        """
        task_queue = self._get_task_queue()
        if task_queue is None:
            return ("unhealthy", "Task queue not available")

        try:
            # Check if workers are running
            if not task_queue.is_running:
                return ("unhealthy", "Workers not running")

            # Check queue depth
            queue_size = task_queue.queue.qsize()
            if queue_size > 100:
                return ("unhealthy", f"Queue depth critical: {queue_size} tasks")

            # Count failed tasks
            failed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "failed"
            )
            completed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "completed"
            )

            total_finished = completed_count + failed_count
            if total_finished > 0:
                error_rate = (failed_count / total_finished) * 100.0
                if error_rate > 10:
                    return ("unhealthy", f"High error rate: {error_rate:.1f}%")
                elif error_rate > 5:
                    return ("degraded", f"Elevated error rate: {error_rate:.1f}%")

            # Check for queue backup
            if queue_size > 50:
                return ("degraded", f"Queue backup: {queue_size} tasks pending")

            # All checks passed
            active_workers = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "processing"
            )
            return (
                "healthy",
                f"{active_workers}/{task_queue.max_workers} workers active, {queue_size} tasks pending",
            )

        except Exception as e:
            logger.error(f"Error checking worker health: {e}", exc_info=True)
            return ("unhealthy", f"Health check error: {str(e)}")

    async def get_worker_details(self) -> dict[str, Any]:
        """Get detailed worker pool information.

        Returns:
            Dictionary with detailed worker statistics.
        """
        task_queue = self._get_task_queue()
        if task_queue is None:
            return {
                "available": False,
                "error": "Task queue not available",
            }

        try:
            # Gather all statistics
            active_workers = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "processing"
            )
            idle_workers = task_queue.max_workers - active_workers

            pending_count = task_queue.queue.qsize()
            processing_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "processing"
            )
            completed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "completed"
            )
            failed_count = sum(
                1
                for task_metadata in task_queue.tasks.values()
                if task_metadata.state.value == "failed"
            )

            total_finished = completed_count + failed_count
            success_rate = (
                (completed_count / total_finished * 100.0) if total_finished > 0 else 100.0
            )

            return {
                "available": True,
                "running": task_queue.is_running,
                "pool_size": task_queue.max_workers,
                "active_workers": active_workers,
                "idle_workers": idle_workers,
                "queue": {
                    "pending": pending_count,
                    "processing": processing_count,
                    "completed": completed_count,
                    "failed": failed_count,
                },
                "statistics": {
                    "total_tasks": len(task_queue.tasks),
                    "success_rate": round(success_rate, 2),
                    "error_rate": round(100.0 - success_rate, 2),
                },
            }

        except Exception as e:
            logger.error(f"Error getting worker details: {e}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
            }
