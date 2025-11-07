"""Async task queue with worker pool for background processing.

This module implements a native asyncio-based task queue with a worker pool
for processing verification tasks in the background. Uses asyncio.Queue for
task distribution and manages worker lifecycle.

For production scale, this can be migrated to Celery + Redis.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional

import structlog

from truthgraph.workers.task_status import TaskMetadata, TaskState
from truthgraph.workers.task_storage import TaskStorage, get_task_storage

logger = structlog.get_logger(__name__)


class TaskQueue:
    """Async task queue with worker pool.

    Manages background task processing with:
    - asyncio.Queue for task distribution
    - Worker pool for parallel processing
    - Task status tracking
    - Result storage with TTL
    - Graceful shutdown

    Attributes:
        queue: asyncio.Queue for pending tasks
        tasks: Dictionary mapping task_id to TaskMetadata
        storage: Result storage with TTL
        max_workers: Maximum number of concurrent workers
        workers: List of worker tasks
        is_running: Flag indicating if queue is active
    """

    def __init__(
        self,
        max_workers: int = 5,
        result_ttl_seconds: int = 3600,
    ):
        """Initialize task queue.

        Args:
            max_workers: Maximum concurrent workers (default: 5)
            result_ttl_seconds: TTL for results in seconds (default: 3600 = 1 hour)
        """
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, TaskMetadata] = {}
        self.storage: TaskStorage = get_task_storage(ttl_seconds=result_ttl_seconds)
        self.max_workers = max_workers
        self.workers: list[asyncio.Task] = []
        self.is_running = False
        self._lock = asyncio.Lock()

        logger.info(
            "task_queue_initialized",
            max_workers=max_workers,
            result_ttl_seconds=result_ttl_seconds,
        )

    async def queue_task(
        self,
        claim_id: str,
        claim_text: str,
        task_func: Callable,
        options: Optional[dict] = None,
        **kwargs: Any,
    ) -> TaskMetadata:
        """Queue a verification task for background processing.

        Args:
            claim_id: Unique claim identifier
            claim_text: Claim text to verify
            task_func: Async function to execute
            options: Optional verification options
            **kwargs: Additional arguments for task_func

        Returns:
            TaskMetadata with task_id and initial status
        """
        # Generate unique task ID
        task_id = f"task_{uuid.uuid4().hex[:16]}"

        # Create task metadata
        task_metadata = TaskMetadata(
            task_id=task_id,
            claim_id=claim_id,
            claim_text=claim_text,
            state=TaskState.PENDING,
            created_at=datetime.now(UTC),
            options=options,
        )

        # Store task metadata
        async with self._lock:
            self.tasks[task_id] = task_metadata

        # Queue task for processing
        await self.queue.put(
            {
                "task_id": task_id,
                "claim_id": claim_id,
                "claim_text": claim_text,
                "task_func": task_func,
                "options": options,
                "kwargs": kwargs,
            }
        )

        logger.info(
            "task_queued",
            task_id=task_id,
            claim_id=claim_id,
            queue_size=self.queue.qsize(),
        )

        return task_metadata

    async def get_task_status(self, task_id: str) -> Optional[TaskMetadata]:
        """Get current status of a task.

        Args:
            task_id: Unique task identifier

        Returns:
            TaskMetadata if task exists, None otherwise
        """
        async with self._lock:
            return self.tasks.get(task_id)

    async def get_result(self, claim_id: str) -> Optional[Any]:
        """Get verification result for a claim.

        Args:
            claim_id: Claim identifier

        Returns:
            Verification result if available, None otherwise
        """
        return await self.storage.get_result(claim_id)

    async def start_workers(self) -> None:
        """Start worker pool for processing tasks."""
        if self.is_running:
            logger.warning("workers_already_running")
            return

        self.is_running = True

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # Start storage cleanup loop
        await self.storage.start_cleanup_loop(interval_seconds=300)

        logger.info(
            "workers_started",
            worker_count=self.max_workers,
        )

    async def stop_workers(self, timeout: float = 30.0) -> None:
        """Stop all workers gracefully.

        Args:
            timeout: Maximum time to wait for workers to finish (seconds)
        """
        if not self.is_running:
            logger.warning("workers_not_running")
            return

        logger.info("stopping_workers", worker_count=len(self.workers))

        self.is_running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("worker_shutdown_timeout", timeout=timeout)

        self.workers.clear()

        # Stop storage cleanup loop
        await self.storage.stop_cleanup_loop()

        logger.info("workers_stopped")

    async def _worker(self, worker_id: str) -> None:
        """Background worker that processes queued tasks.

        Args:
            worker_id: Unique identifier for this worker
        """
        logger.info("worker_started", worker_id=worker_id)

        try:
            while self.is_running:
                try:
                    # Get task from queue with timeout
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                    logger.info(
                        "worker_processing_task",
                        worker_id=worker_id,
                        task_id=task["task_id"],
                        claim_id=task["claim_id"],
                    )

                    # Process task
                    await self._process_task(task)

                    # Mark task as done in queue
                    self.queue.task_done()

                except asyncio.TimeoutError:
                    # No tasks available, continue loop
                    continue
                except Exception as e:
                    logger.error(
                        "worker_error",
                        worker_id=worker_id,
                        error=str(e),
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("worker_cancelled", worker_id=worker_id)
            raise

        finally:
            logger.info("worker_stopped", worker_id=worker_id)

    async def _process_task(self, task: dict) -> None:
        """Process a single task.

        Args:
            task: Task dictionary with task_id, claim_id, task_func, etc.
        """
        task_id = task["task_id"]
        claim_id = task["claim_id"]

        # Get task metadata
        async with self._lock:
            task_metadata = self.tasks.get(task_id)

        if task_metadata is None:
            logger.error("task_metadata_not_found", task_id=task_id)
            return

        try:
            # Mark as processing
            task_metadata.mark_processing()

            logger.info(
                "task_processing_started",
                task_id=task_id,
                claim_id=claim_id,
            )

            # Execute task function
            task_func = task["task_func"]
            kwargs = task["kwargs"]
            result = await task_func(
                task_metadata=task_metadata,
                **kwargs,
            )

            # Mark as completed
            task_metadata.mark_completed(result)

            # Store result
            await self.storage.store_result(claim_id, result)

            logger.info(
                "task_completed",
                task_id=task_id,
                claim_id=claim_id,
            )

        except Exception as e:
            # Mark as failed
            error_message = str(e)
            task_metadata.mark_failed(error_message)

            logger.error(
                "task_failed",
                task_id=task_id,
                claim_id=claim_id,
                error=error_message,
                exc_info=True,
            )

    def get_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        return {
            "queue_size": self.queue.qsize(),
            "total_tasks": len(self.tasks),
            "pending_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.PENDING
            ),
            "processing_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.PROCESSING
            ),
            "completed_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.COMPLETED
            ),
            "failed_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.FAILED
            ),
            "workers_count": len(self.workers),
            "is_running": self.is_running,
            "storage_stats": self.storage.get_stats(),
        }


# Global singleton instance
_queue_instance: Optional[TaskQueue] = None


def get_task_queue(
    max_workers: int = 5,
    result_ttl_seconds: int = 3600,
) -> TaskQueue:
    """Get or create global task queue instance.

    Args:
        max_workers: Maximum concurrent workers (default: 5)
        result_ttl_seconds: TTL for results (default: 3600 = 1 hour)

    Returns:
        TaskQueue instance
    """
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = TaskQueue(
            max_workers=max_workers,
            result_ttl_seconds=result_ttl_seconds,
        )
    return _queue_instance
