"""Unit tests for task queue functionality."""

import asyncio

import pytest

from truthgraph.workers.task_queue import TaskQueue
from truthgraph.workers.task_status import TaskState


@pytest.mark.asyncio
async def test_task_queue_initialization():
    """Test task queue initialization with custom parameters."""
    queue = TaskQueue(max_workers=3, result_ttl_seconds=1800)

    assert queue.max_workers == 3
    assert queue.storage.ttl_seconds == 1800
    assert queue.is_running is False
    assert len(queue.workers) == 0


@pytest.mark.asyncio
async def test_queue_task():
    """Test queuing a task."""
    queue = TaskQueue(max_workers=2)

    async def dummy_task(task_metadata):
        """Dummy task for testing."""
        return {"result": "success"}

    task_metadata = await queue.queue_task(
        claim_id="test_claim_1",
        claim_text="Test claim",
        task_func=dummy_task,
        options={"test": True},
    )

    assert task_metadata.task_id.startswith("task_")
    assert task_metadata.claim_id == "test_claim_1"
    assert task_metadata.claim_text == "Test claim"
    assert task_metadata.state == TaskState.PENDING
    assert task_metadata.options == {"test": True}

    # Verify task is in queue
    assert task_metadata.task_id in queue.tasks


@pytest.mark.asyncio
async def test_get_task_status():
    """Test retrieving task status."""
    queue = TaskQueue()

    async def dummy_task(task_metadata):
        return {"result": "success"}

    task_metadata = await queue.queue_task(
        claim_id="test_claim",
        claim_text="Test claim",
        task_func=dummy_task,
    )

    # Get task status
    status = await queue.get_task_status(task_metadata.task_id)

    assert status is not None
    assert status.task_id == task_metadata.task_id
    assert status.claim_id == "test_claim"
    assert status.state == TaskState.PENDING


@pytest.mark.asyncio
async def test_get_task_status_not_found():
    """Test retrieving non-existent task."""
    queue = TaskQueue()

    status = await queue.get_task_status("nonexistent_task")

    assert status is None


@pytest.mark.asyncio
async def test_start_stop_workers():
    """Test starting and stopping worker pool."""
    queue = TaskQueue(max_workers=3)

    # Start workers
    await queue.start_workers()

    assert queue.is_running is True
    assert len(queue.workers) == 3

    # Stop workers
    await queue.stop_workers(timeout=5.0)

    assert queue.is_running is False
    assert len(queue.workers) == 0


@pytest.mark.asyncio
async def test_worker_processes_task():
    """Test that workers process queued tasks."""
    queue = TaskQueue(max_workers=2)

    # Flag to track task execution
    task_executed = False

    async def test_task(task_metadata):
        """Task that sets a flag."""
        nonlocal task_executed
        task_executed = True
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "completed"}

    # Start workers
    await queue.start_workers()

    try:
        # Queue task
        task_metadata = await queue.queue_task(
            claim_id="test_claim",
            claim_text="Test claim",
            task_func=test_task,
        )

        # Wait for task to be processed
        await asyncio.sleep(0.5)

        # Check task was executed
        assert task_executed is True

        # Check task status
        status = await queue.get_task_status(task_metadata.task_id)
        assert status.state == TaskState.COMPLETED
        assert status.result == {"status": "completed"}

    finally:
        await queue.stop_workers()


@pytest.mark.asyncio
async def test_worker_handles_task_failure():
    """Test that workers handle task failures gracefully."""
    queue = TaskQueue(max_workers=1)

    async def failing_task(task_metadata):
        """Task that raises an exception."""
        raise ValueError("Test error")

    # Start workers
    await queue.start_workers()

    try:
        # Queue failing task
        task_metadata = await queue.queue_task(
            claim_id="test_claim",
            claim_text="Test claim",
            task_func=failing_task,
        )

        # Wait for task to be processed
        await asyncio.sleep(0.5)

        # Check task status
        status = await queue.get_task_status(task_metadata.task_id)
        assert status.state == TaskState.FAILED
        assert "Test error" in status.error

    finally:
        await queue.stop_workers()


@pytest.mark.asyncio
async def test_result_storage():
    """Test storing and retrieving results."""
    queue = TaskQueue()

    async def task_with_result(task_metadata):
        """Task that returns a result."""
        return {"verdict": "SUPPORTED", "confidence": 0.95}

    # Start workers
    await queue.start_workers()

    try:
        # Queue task
        task_metadata = await queue.queue_task(
            claim_id="test_claim_123",
            claim_text="Test claim",
            task_func=task_with_result,
        )

        # Wait for completion
        await asyncio.sleep(0.5)

        # Get result from storage
        result = await queue.get_result("test_claim_123")

        assert result is not None
        assert result["verdict"] == "SUPPORTED"
        assert result["confidence"] == 0.95

    finally:
        await queue.stop_workers()


@pytest.mark.asyncio
async def test_queue_stats():
    """Test queue statistics."""
    queue = TaskQueue(max_workers=2)

    async def dummy_task(task_metadata):
        await asyncio.sleep(0.1)
        return {"status": "ok"}

    # Start workers
    await queue.start_workers()

    try:
        # Queue multiple tasks
        await queue.queue_task("claim1", "Test 1", dummy_task)
        await queue.queue_task("claim2", "Test 2", dummy_task)

        # Get stats
        stats = queue.get_stats()

        assert stats["workers_count"] == 2
        assert stats["is_running"] is True
        assert stats["total_tasks"] == 2

        # Wait for tasks to complete
        await asyncio.sleep(0.5)

        stats = queue.get_stats()
        assert stats["completed_tasks"] == 2

    finally:
        await queue.stop_workers()


@pytest.mark.asyncio
async def test_concurrent_task_processing():
    """Test processing multiple tasks concurrently."""
    queue = TaskQueue(max_workers=3)

    completed_tasks = []

    async def concurrent_task(task_metadata, task_id):
        """Task that tracks completion."""
        await asyncio.sleep(0.2)
        completed_tasks.append(task_id)
        return {"task_id": task_id}

    # Start workers
    await queue.start_workers()

    try:
        # Queue 5 tasks
        tasks = []
        for i in range(5):
            task_metadata = await queue.queue_task(
                claim_id=f"claim_{i}",
                claim_text=f"Test claim {i}",
                task_func=concurrent_task,
                task_id=i,
            )
            tasks.append(task_metadata)

        # Wait for all tasks to complete
        await asyncio.sleep(1.0)

        # Check all tasks completed
        assert len(completed_tasks) == 5
        assert set(completed_tasks) == {0, 1, 2, 3, 4}

        # Check all tasks have completed status
        for task_meta in tasks:
            status = await queue.get_task_status(task_meta.task_id)
            assert status.state == TaskState.COMPLETED

    finally:
        await queue.stop_workers()
