"""Task status tracking for background verification tasks.

This module provides data structures for tracking the lifecycle
of async verification tasks from creation to completion.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional


class TaskState(str, Enum):
    """Enumeration of possible task states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskMetadata:
    """Metadata tracking for a single verification task.

    Attributes:
        task_id: Unique identifier for the task
        claim_id: Original claim identifier from request
        claim_text: Claim text being verified
        state: Current task state
        created_at: Timestamp when task was created
        started_at: Timestamp when processing started (if started)
        completed_at: Timestamp when task finished (if done)
        progress: Progress percentage (0-100)
        result: Task result (if completed)
        error: Error message (if failed)
        retry_count: Number of retry attempts made
        options: Verification options passed with request
    """

    task_id: str
    claim_id: str
    claim_text: str
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    options: Optional[dict] = None

    def mark_processing(self) -> None:
        """Mark task as processing and record start time."""
        self.state = TaskState.PROCESSING
        self.started_at = datetime.now(UTC)
        self.progress = 10

    def mark_completed(self, result: Any) -> None:
        """Mark task as completed with result.

        Args:
            result: Task result to store
        """
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.result = result
        self.progress = 100

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error message.

        Args:
            error: Error message describing failure
        """
        self.state = TaskState.FAILED
        self.completed_at = datetime.now(UTC)
        self.error = error

    def update_progress(self, progress: int) -> None:
        """Update task progress percentage.

        Args:
            progress: Progress percentage (0-100)
        """
        self.progress = max(0, min(100, progress))

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1

    def is_done(self) -> bool:
        """Check if task is in a terminal state.

        Returns:
            True if task is completed or failed
        """
        return self.state in {TaskState.COMPLETED, TaskState.FAILED}

    def to_dict(self) -> dict:
        """Convert metadata to dictionary for serialization.

        Returns:
            Dictionary representation of task metadata
        """
        return {
            "task_id": self.task_id,
            "claim_id": self.claim_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
        }
