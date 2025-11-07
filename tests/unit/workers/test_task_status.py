"""Unit tests for task status tracking."""

from datetime import datetime

import pytest

from truthgraph.workers.task_status import TaskMetadata, TaskState


def test_task_metadata_initialization():
    """Test TaskMetadata initialization."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
        options={"max_evidence": 10},
    )

    assert task_meta.task_id == "task_123"
    assert task_meta.claim_id == "claim_456"
    assert task_meta.claim_text == "Test claim"
    assert task_meta.state == TaskState.PENDING
    assert task_meta.progress == 0
    assert task_meta.result is None
    assert task_meta.error is None
    assert task_meta.retry_count == 0
    assert task_meta.options == {"max_evidence": 10}
    assert isinstance(task_meta.created_at, datetime)


def test_mark_processing():
    """Test marking task as processing."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    task_meta.mark_processing()

    assert task_meta.state == TaskState.PROCESSING
    assert task_meta.started_at is not None
    assert task_meta.progress == 10


def test_mark_completed():
    """Test marking task as completed."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    result = {"verdict": "SUPPORTED", "confidence": 0.95}
    task_meta.mark_completed(result)

    assert task_meta.state == TaskState.COMPLETED
    assert task_meta.completed_at is not None
    assert task_meta.result == result
    assert task_meta.progress == 100


def test_mark_failed():
    """Test marking task as failed."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    task_meta.mark_failed("Database connection timeout")

    assert task_meta.state == TaskState.FAILED
    assert task_meta.completed_at is not None
    assert task_meta.error == "Database connection timeout"


def test_update_progress():
    """Test updating task progress."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    task_meta.update_progress(50)
    assert task_meta.progress == 50

    task_meta.update_progress(75)
    assert task_meta.progress == 75


def test_update_progress_bounds():
    """Test progress bounds checking."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    # Test lower bound
    task_meta.update_progress(-10)
    assert task_meta.progress == 0

    # Test upper bound
    task_meta.update_progress(150)
    assert task_meta.progress == 100


def test_increment_retry():
    """Test incrementing retry counter."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    assert task_meta.retry_count == 0

    task_meta.increment_retry()
    assert task_meta.retry_count == 1

    task_meta.increment_retry()
    assert task_meta.retry_count == 2


def test_is_done():
    """Test checking if task is in terminal state."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    # Pending task is not done
    assert task_meta.is_done() is False

    # Processing task is not done
    task_meta.mark_processing()
    assert task_meta.is_done() is False

    # Completed task is done
    task_meta.mark_completed({"result": "test"})
    assert task_meta.is_done() is True


def test_is_done_failed():
    """Test checking if failed task is done."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    task_meta.mark_failed("Error occurred")
    assert task_meta.is_done() is True


def test_to_dict():
    """Test converting metadata to dictionary."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
        options={"max_evidence": 5},
    )

    task_meta.mark_processing()
    task_meta.update_progress(25)

    task_dict = task_meta.to_dict()

    assert task_dict["task_id"] == "task_123"
    assert task_dict["claim_id"] == "claim_456"
    assert task_dict["state"] == "processing"
    assert task_dict["progress"] == 25
    assert task_dict["result"] is None
    assert task_dict["error"] is None
    assert task_dict["retry_count"] == 0
    assert isinstance(task_dict["created_at"], str)
    assert isinstance(task_dict["started_at"], str)


def test_task_lifecycle():
    """Test complete task lifecycle."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    # Initial state
    assert task_meta.state == TaskState.PENDING
    assert task_meta.progress == 0
    assert not task_meta.is_done()

    # Mark as processing
    task_meta.mark_processing()
    assert task_meta.state == TaskState.PROCESSING
    assert task_meta.started_at is not None
    assert not task_meta.is_done()

    # Update progress
    task_meta.update_progress(30)
    assert task_meta.progress == 30

    task_meta.update_progress(60)
    assert task_meta.progress == 60

    # Complete task
    result = {"verdict": "SUPPORTED"}
    task_meta.mark_completed(result)
    assert task_meta.state == TaskState.COMPLETED
    assert task_meta.completed_at is not None
    assert task_meta.result == result
    assert task_meta.progress == 100
    assert task_meta.is_done()


def test_task_lifecycle_with_retries():
    """Test task lifecycle with retry attempts."""
    task_meta = TaskMetadata(
        task_id="task_123",
        claim_id="claim_456",
        claim_text="Test claim",
    )

    # First attempt
    task_meta.mark_processing()
    task_meta.increment_retry()

    # Second attempt
    task_meta.increment_retry()

    assert task_meta.retry_count == 2

    # Finally succeed
    task_meta.mark_completed({"result": "success"})
    assert task_meta.state == TaskState.COMPLETED
    assert task_meta.retry_count == 2


def test_task_state_enum():
    """Test TaskState enum values."""
    assert TaskState.PENDING.value == "pending"
    assert TaskState.PROCESSING.value == "processing"
    assert TaskState.COMPLETED.value == "completed"
    assert TaskState.FAILED.value == "failed"

    # Test string comparison
    assert TaskState.PENDING == "pending"
    assert TaskState.COMPLETED == "completed"
