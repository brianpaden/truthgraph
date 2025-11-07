"""Integration tests for async background processing (Feature 4.3)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from truthgraph.main import app
from truthgraph.workers.task_queue import get_task_queue


@pytest.fixture
async def task_queue():
    """Get task queue instance for testing."""
    queue = get_task_queue(max_workers=2, result_ttl_seconds=60)
    await queue.start_workers()
    yield queue
    await queue.stop_workers()


@pytest.mark.asyncio
async def test_end_to_end_verification_workflow(task_queue):
    """Test complete end-to-end async verification workflow."""

    # Mock verification result
    mock_result = MagicMock()
    mock_result.verdict = "SUPPORTED"
    mock_result.confidence = 0.95
    mock_result.reasoning = "Test reasoning"
    mock_result.evidence_items = []

    async def mock_verification_task(task_metadata, **kwargs):
        """Mock verification task."""
        await asyncio.sleep(0.2)  # Simulate work
        from datetime import UTC, datetime

        from truthgraph.api.schemas.verification import VerificationResult

        return VerificationResult(
            claim_id=task_metadata.claim_id,
            claim_text=task_metadata.claim_text,
            verdict="SUPPORTED",
            confidence=0.95,
            reasoning="Test reasoning",
            evidence=[],
            verified_at=datetime.now(UTC),
            processing_time_ms=200,
        )

    # Queue task
    task_metadata = await task_queue.queue_task(
        claim_id="test_claim_integration",
        claim_text="Test claim for integration",
        task_func=mock_verification_task,
    )

    # Check initial status
    assert task_metadata.task_id.startswith("task_")
    assert task_metadata.state.value == "pending"

    # Wait for processing
    await asyncio.sleep(0.5)

    # Check final status
    status = await task_queue.get_task_status(task_metadata.task_id)
    assert status.state.value == "completed"
    assert status.result is not None
    assert status.result.verdict == "SUPPORTED"

    # Check result storage
    result = await task_queue.get_result("test_claim_integration")
    assert result is not None
    assert result.verdict == "SUPPORTED"


@pytest.mark.asyncio
async def test_concurrent_verification_tasks(task_queue):
    """Test processing multiple verification tasks concurrently."""

    async def mock_task(task_metadata, task_num):
        """Mock task that simulates processing."""
        await asyncio.sleep(0.1)
        return {"task_num": task_num, "status": "completed"}

    # Queue multiple tasks
    tasks = []
    for i in range(5):
        task_metadata = await task_queue.queue_task(
            claim_id=f"claim_{i}",
            claim_text=f"Test claim {i}",
            task_func=mock_task,
            task_num=i,
        )
        tasks.append(task_metadata)

    # Wait for all to complete
    await asyncio.sleep(1.0)

    # Check all completed
    for task_meta in tasks:
        status = await task_queue.get_task_status(task_meta.task_id)
        assert status.state.value == "completed"
        assert status.result["status"] == "completed"


@pytest.mark.asyncio
async def test_error_handling_in_async_processing(task_queue):
    """Test error handling for failed verification tasks."""

    async def failing_task(task_metadata):
        """Task that raises an error."""
        await asyncio.sleep(0.1)
        raise ValueError("Simulated processing error")

    # Queue failing task
    task_metadata = await task_queue.queue_task(
        claim_id="failing_claim",
        claim_text="This will fail",
        task_func=failing_task,
    )

    # Wait for processing
    await asyncio.sleep(0.3)

    # Check task failed
    status = await task_queue.get_task_status(task_metadata.task_id)
    assert status.state.value == "failed"
    assert "Simulated processing error" in status.error


@pytest.mark.asyncio
async def test_task_status_tracking(task_queue):
    """Test task status tracking during processing."""

    progress_updates = []

    async def slow_task(task_metadata):
        """Task that updates progress."""
        task_metadata.update_progress(25)
        await asyncio.sleep(0.1)
        task_metadata.update_progress(50)
        await asyncio.sleep(0.1)
        task_metadata.update_progress(75)
        await asyncio.sleep(0.1)
        return {"status": "completed"}

    # Queue task
    task_metadata = await task_queue.queue_task(
        claim_id="progress_claim",
        claim_text="Test progress tracking",
        task_func=slow_task,
    )

    # Poll progress
    for _ in range(10):
        status = await task_queue.get_task_status(task_metadata.task_id)
        progress_updates.append((status.state.value, status.progress))
        await asyncio.sleep(0.1)
        if status.state.value == "completed":
            break

    # Check we saw progress updates
    assert len(progress_updates) > 0
    final_status = progress_updates[-1]
    assert final_status[0] == "completed"
    assert final_status[1] == 100


@pytest.mark.asyncio
async def test_result_persistence_with_ttl(task_queue):
    """Test result storage with TTL expiration."""

    async def simple_task(task_metadata):
        """Simple task that returns a result."""
        return {"verdict": "SUPPORTED", "confidence": 0.9}

    # Queue task with short TTL storage
    storage = task_queue.storage
    storage.ttl_seconds = 1  # 1 second TTL

    task_metadata = await task_queue.queue_task(
        claim_id="ttl_claim",
        claim_text="Test TTL",
        task_func=simple_task,
    )

    # Wait for completion
    await asyncio.sleep(0.3)

    # Result should be available
    result = await task_queue.get_result("ttl_claim")
    assert result is not None

    # Wait for TTL expiration
    await asyncio.sleep(1.5)

    # Result should be expired
    result = await task_queue.get_result("ttl_claim")
    assert result is None


@pytest.mark.asyncio
async def test_queue_statistics(task_queue):
    """Test queue statistics reporting."""

    async def dummy_task(task_metadata):
        await asyncio.sleep(0.1)
        return {"status": "ok"}

    # Initial stats
    stats = task_queue.get_stats()
    initial_tasks = stats["total_tasks"]

    # Queue some tasks
    for i in range(3):
        await task_queue.queue_task(
            claim_id=f"stats_claim_{i}",
            claim_text=f"Test {i}",
            task_func=dummy_task,
        )

    # Check stats updated
    stats = task_queue.get_stats()
    assert stats["total_tasks"] == initial_tasks + 3
    assert stats["workers_count"] == 2
    assert stats["is_running"] is True

    # Wait for completion
    await asyncio.sleep(0.5)

    stats = task_queue.get_stats()
    assert stats["completed_tasks"] > 0


@pytest.mark.asyncio
async def test_graceful_shutdown_with_pending_tasks(task_queue):
    """Test graceful worker shutdown with pending tasks."""

    async def long_running_task(task_metadata):
        """Task that takes a while."""
        await asyncio.sleep(2.0)
        return {"status": "completed"}

    # Queue a long-running task
    task_metadata = await task_queue.queue_task(
        claim_id="long_claim",
        claim_text="Long running test",
        task_func=long_running_task,
    )

    # Wait a bit for task to start
    await asyncio.sleep(0.2)

    # Stop workers (should wait for task or timeout)
    await task_queue.stop_workers(timeout=1.0)

    assert task_queue.is_running is False
    assert len(task_queue.workers) == 0


@pytest.mark.asyncio
async def test_task_queue_resilience():
    """Test task queue resilience to worker failures."""
    queue = get_task_queue(max_workers=3)
    await queue.start_workers()

    try:
        failure_count = 0
        success_count = 0

        async def flaky_task(task_metadata, should_fail):
            """Task that sometimes fails."""
            nonlocal failure_count, success_count

            if should_fail:
                failure_count += 1
                raise RuntimeError("Intentional failure")
            else:
                success_count += 1
                return {"status": "success"}

        # Queue mix of failing and succeeding tasks
        for i in range(6):
            await queue.queue_task(
                claim_id=f"resilience_claim_{i}",
                claim_text=f"Test {i}",
                task_func=flaky_task,
                should_fail=(i % 2 == 0),  # Fail every other task
            )

        # Wait for all to process
        await asyncio.sleep(0.5)

        # Check results
        assert failure_count == 3
        assert success_count == 3

        # Queue should still be operational
        stats = queue.get_stats()
        assert stats["is_running"] is True

    finally:
        await queue.stop_workers()
