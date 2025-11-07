"""Background worker infrastructure for TruthGraph.

This package provides async background processing for long-running
verification tasks with proper error handling, retry logic, and
task status tracking.

Modules:
    task_queue: Task queue management with worker pool
    task_status: Task lifecycle tracking
    task_storage: Result persistence with TTL
    verification_worker: Verification-specific worker logic
"""

from truthgraph.workers.task_queue import TaskQueue, get_task_queue
from truthgraph.workers.task_status import TaskMetadata, TaskState
from truthgraph.workers.task_storage import TaskStorage, get_task_storage
from truthgraph.workers.verification_worker import VerificationWorker, get_verification_worker

__all__ = [
    "TaskQueue",
    "get_task_queue",
    "TaskMetadata",
    "TaskState",
    "TaskStorage",
    "get_task_storage",
    "VerificationWorker",
    "get_verification_worker",
]
