"""Task result storage with TTL for completed verification tasks.

This module provides in-memory storage for task results with automatic
expiration based on time-to-live (TTL). For production, this can be
migrated to Redis or another distributed cache.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class TaskStorage:
    """In-memory task result storage with TTL.

    Stores verification results with automatic cleanup after TTL expires.
    Thread-safe for async operations.

    Attributes:
        results: Dictionary mapping claim_id to (result, expiry_time)
        ttl: Time-to-live for stored results (default: 1 hour)
        cleanup_task: Background task for cleaning expired results
    """

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize task storage.

        Args:
            ttl_seconds: Time-to-live for results in seconds (default: 3600 = 1 hour)
        """
        self.results: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.ttl_seconds = ttl_seconds

        logger.info(
            "task_storage_initialized",
            ttl_seconds=ttl_seconds,
        )

    async def store_result(self, claim_id: str, result: Any) -> None:
        """Store verification result with TTL.

        Args:
            claim_id: Claim identifier
            result: Verification result to store
        """
        async with self._lock:
            expiry_time = datetime.now(UTC) + self.ttl
            self.results[claim_id] = (result, expiry_time)

            logger.debug(
                "result_stored",
                claim_id=claim_id,
                expiry_time=expiry_time.isoformat(),
            )

    async def get_result(self, claim_id: str) -> Optional[Any]:
        """Retrieve verification result if not expired.

        Args:
            claim_id: Claim identifier

        Returns:
            Verification result if available and not expired, None otherwise
        """
        async with self._lock:
            if claim_id not in self.results:
                return None

            result, expiry_time = self.results[claim_id]

            # Check if expired
            if datetime.now(UTC) > expiry_time:
                # Remove expired result
                del self.results[claim_id]
                logger.debug(
                    "result_expired",
                    claim_id=claim_id,
                )
                return None

            logger.debug(
                "result_retrieved",
                claim_id=claim_id,
            )
            return result

    async def delete_result(self, claim_id: str) -> bool:
        """Delete a stored result.

        Args:
            claim_id: Claim identifier

        Returns:
            True if result was deleted, False if not found
        """
        async with self._lock:
            if claim_id in self.results:
                del self.results[claim_id]
                logger.debug(
                    "result_deleted",
                    claim_id=claim_id,
                )
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Clean up expired results.

        Returns:
            Number of results cleaned up
        """
        async with self._lock:
            now = datetime.now(UTC)
            expired_keys = [
                claim_id
                for claim_id, (_, expiry_time) in self.results.items()
                if now > expiry_time
            ]

            for claim_id in expired_keys:
                del self.results[claim_id]

            if expired_keys:
                logger.info(
                    "expired_results_cleaned",
                    count=len(expired_keys),
                )

            return len(expired_keys)

    async def start_cleanup_loop(self, interval_seconds: int = 300) -> None:
        """Start background task to periodically clean up expired results.

        Args:
            interval_seconds: Cleanup interval in seconds (default: 300 = 5 minutes)
        """
        if self.cleanup_task is not None:
            logger.warning("cleanup_loop_already_running")
            return

        async def cleanup_loop():
            """Background loop for cleaning expired results."""
            logger.info(
                "cleanup_loop_started",
                interval_seconds=interval_seconds,
            )
            try:
                while True:
                    await asyncio.sleep(interval_seconds)
                    count = await self.cleanup_expired()
                    if count > 0:
                        logger.info(
                            "cleanup_cycle_completed",
                            expired_count=count,
                        )
            except asyncio.CancelledError:
                logger.info("cleanup_loop_cancelled")
                raise

        self.cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_loop(self) -> None:
        """Stop background cleanup task."""
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("cleanup_loop_stopped")

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        return {
            "total_results": len(self.results),
            "ttl_seconds": self.ttl_seconds,
        }

    async def clear(self) -> None:
        """Clear all stored results."""
        async with self._lock:
            count = len(self.results)
            self.results.clear()
            logger.info(
                "storage_cleared",
                count=count,
            )


# Global singleton instance
_storage_instance: Optional[TaskStorage] = None


def get_task_storage(ttl_seconds: int = 3600) -> TaskStorage:
    """Get or create global task storage instance.

    Args:
        ttl_seconds: Time-to-live for results (default: 3600 = 1 hour)

    Returns:
        TaskStorage instance
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = TaskStorage(ttl_seconds=ttl_seconds)
    return _storage_instance
