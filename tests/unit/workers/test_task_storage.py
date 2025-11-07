"""Unit tests for task result storage with TTL."""

import asyncio
from datetime import datetime, timedelta

import pytest

from truthgraph.workers.task_storage import TaskStorage


@pytest.mark.asyncio
async def test_storage_initialization():
    """Test storage initialization."""
    storage = TaskStorage(ttl_seconds=1800)

    assert storage.ttl_seconds == 1800
    assert storage.ttl == timedelta(seconds=1800)
    assert len(storage.results) == 0


@pytest.mark.asyncio
async def test_store_and_get_result():
    """Test storing and retrieving results."""
    storage = TaskStorage(ttl_seconds=3600)

    # Store result
    result = {"verdict": "SUPPORTED", "confidence": 0.95}
    await storage.store_result("claim_123", result)

    # Retrieve result
    retrieved = await storage.get_result("claim_123")

    assert retrieved == result


@pytest.mark.asyncio
async def test_get_nonexistent_result():
    """Test retrieving non-existent result."""
    storage = TaskStorage()

    result = await storage.get_result("nonexistent_claim")

    assert result is None


@pytest.mark.asyncio
async def test_result_expiration():
    """Test that results expire after TTL."""
    storage = TaskStorage(ttl_seconds=1)  # 1 second TTL

    # Store result
    result = {"verdict": "SUPPORTED"}
    await storage.store_result("claim_123", result)

    # Result should be available immediately
    retrieved = await storage.get_result("claim_123")
    assert retrieved == result

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Result should be expired
    retrieved = await storage.get_result("claim_123")
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_result():
    """Test deleting a stored result."""
    storage = TaskStorage()

    # Store result
    await storage.store_result("claim_123", {"verdict": "SUPPORTED"})

    # Delete result
    deleted = await storage.delete_result("claim_123")
    assert deleted is True

    # Result should be gone
    result = await storage.get_result("claim_123")
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_result():
    """Test deleting non-existent result."""
    storage = TaskStorage()

    deleted = await storage.delete_result("nonexistent_claim")
    assert deleted is False


@pytest.mark.asyncio
async def test_cleanup_expired_results():
    """Test manual cleanup of expired results."""
    storage = TaskStorage(ttl_seconds=1)

    # Store multiple results
    await storage.store_result("claim_1", {"verdict": "SUPPORTED"})
    await storage.store_result("claim_2", {"verdict": "REFUTED"})
    await storage.store_result("claim_3", {"verdict": "NOT_ENOUGH_INFO"})

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Cleanup expired results
    count = await storage.cleanup_expired()

    assert count == 3
    assert len(storage.results) == 0


@pytest.mark.asyncio
async def test_cleanup_mixed_expiration():
    """Test cleanup with mix of expired and valid results."""
    storage = TaskStorage(ttl_seconds=2)

    # Store first result
    await storage.store_result("claim_old", {"verdict": "SUPPORTED"})

    # Wait 1.5 seconds
    await asyncio.sleep(1.5)

    # Store second result (newer)
    await storage.store_result("claim_new", {"verdict": "REFUTED"})

    # Wait for first to expire (but not second)
    await asyncio.sleep(1.0)

    # Cleanup
    count = await storage.cleanup_expired()

    assert count == 1  # Only old result expired
    assert len(storage.results) == 1

    # New result should still be available
    result = await storage.get_result("claim_new")
    assert result is not None


@pytest.mark.asyncio
async def test_storage_stats():
    """Test storage statistics."""
    storage = TaskStorage(ttl_seconds=1800)

    # Empty storage
    stats = storage.get_stats()
    assert stats["total_results"] == 0
    assert stats["ttl_seconds"] == 1800

    # Store some results
    await storage.store_result("claim_1", {"verdict": "SUPPORTED"})
    await storage.store_result("claim_2", {"verdict": "REFUTED"})

    stats = storage.get_stats()
    assert stats["total_results"] == 2


@pytest.mark.asyncio
async def test_clear_storage():
    """Test clearing all results."""
    storage = TaskStorage()

    # Store multiple results
    await storage.store_result("claim_1", {"verdict": "SUPPORTED"})
    await storage.store_result("claim_2", {"verdict": "REFUTED"})
    await storage.store_result("claim_3", {"verdict": "NOT_ENOUGH_INFO"})

    assert len(storage.results) == 3

    # Clear storage
    await storage.clear()

    assert len(storage.results) == 0


@pytest.mark.asyncio
async def test_concurrent_access():
    """Test concurrent read/write access."""
    storage = TaskStorage()

    async def store_result(claim_id, verdict):
        await storage.store_result(claim_id, {"verdict": verdict})

    async def get_result(claim_id):
        return await storage.get_result(claim_id)

    # Store multiple results concurrently
    await asyncio.gather(
        store_result("claim_1", "SUPPORTED"),
        store_result("claim_2", "REFUTED"),
        store_result("claim_3", "NOT_ENOUGH_INFO"),
    )

    # Retrieve results concurrently
    results = await asyncio.gather(
        get_result("claim_1"),
        get_result("claim_2"),
        get_result("claim_3"),
    )

    assert len(results) == 3
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_cleanup_loop_lifecycle():
    """Test cleanup loop start and stop."""
    storage = TaskStorage(ttl_seconds=1)

    # Start cleanup loop
    await storage.start_cleanup_loop(interval_seconds=1)

    assert storage.cleanup_task is not None

    # Store and expire some results
    await storage.store_result("claim_1", {"verdict": "SUPPORTED"})
    await asyncio.sleep(1.5)

    # Wait for cleanup to run
    await asyncio.sleep(1.5)

    # Result should be cleaned up automatically
    result = await storage.get_result("claim_1")
    assert result is None

    # Stop cleanup loop
    await storage.stop_cleanup_loop()

    assert storage.cleanup_task is None


@pytest.mark.asyncio
async def test_overwrite_existing_result():
    """Test overwriting an existing result."""
    storage = TaskStorage()

    # Store initial result
    await storage.store_result("claim_123", {"verdict": "SUPPORTED"})

    # Overwrite with new result
    await storage.store_result("claim_123", {"verdict": "REFUTED"})

    # Get result
    result = await storage.get_result("claim_123")

    assert result["verdict"] == "REFUTED"
