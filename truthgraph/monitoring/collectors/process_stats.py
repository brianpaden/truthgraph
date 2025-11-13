"""Process and database statistics collector.

Monitors Python process resources (CPU, memory), database connection pool health,
query latency, and asyncio event loop performance.
"""

import asyncio
import gc
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProcessStatsCollector:
    """Collects process, database, and event loop metrics.

    Uses asyncio.to_thread() for blocking psutil calls to avoid blocking
    the event loop.

    Metrics collected:
    - app.process.memory.rss_mb (gauge): Resident set size in MB
    - app.process.memory.vms_mb (gauge): Virtual memory size in MB
    - app.process.memory.percent (gauge): Memory usage percentage
    - app.process.cpu.percent (gauge): CPU usage percentage
    - app.gc.collections (counter): Garbage collection cycles
    - app.gc.uncollectable (gauge): Uncollectable objects
    - app.threads.count (gauge): Active thread count
    - app.asyncio.tasks.count (gauge): Active async tasks
    - asyncio.event_loop.lag_ms (gauge): Event loop lag in milliseconds
    - asyncio.event_loop.pending_callbacks (gauge): Pending callback count
    - db.connection.pool.size (gauge): Database connection pool size
    - db.connection.pool.active (gauge): Active database connections
    - db.connection.pool.idle (gauge): Idle database connections
    - db.query.duration_ms (histogram): Database query latency

    Attributes:
        metrics_collector: MetricsCollector instance for recording metrics
        last_event_loop_check: Timestamp of last event loop health check

    Example:
        >>> collector = ProcessStatsCollector(metrics_collector)
        >>> await collector.collect_stats()
    """

    def __init__(self, metrics_collector: Any):
        """Initialize process stats collector.

        Args:
            metrics_collector: MetricsCollector instance for recording metrics
        """
        self.metrics_collector = metrics_collector
        self._last_event_loop_check = time.time()
        self._last_gc_counts = [0, 0, 0]

    async def collect_stats(self) -> None:
        """Collect all process and database statistics.

        Runs various collectors concurrently where possible.
        """
        await asyncio.gather(
            self.collect_process_stats(),
            self.collect_gc_stats(),
            self.collect_asyncio_stats(),
            self.collect_event_loop_health(),
            self.collect_database_stats(),
            return_exceptions=True,
        )

    async def collect_process_stats(self) -> None:
        """Collect CPU and memory statistics for the Python process.

        Uses asyncio.to_thread() for blocking psutil calls.
        """
        try:
            import psutil

            # Get process handle in thread pool
            process = await asyncio.to_thread(psutil.Process)

            # Memory stats
            memory_info = await asyncio.to_thread(process.memory_info)
            await self.metrics_collector.set_gauge(
                "app.process.memory.rss_mb", memory_info.rss / (1024 * 1024)
            )
            await self.metrics_collector.set_gauge(
                "app.process.memory.vms_mb", memory_info.vms / (1024 * 1024)
            )

            # Memory percent
            memory_percent = await asyncio.to_thread(process.memory_percent)
            await self.metrics_collector.set_gauge("app.process.memory.percent", memory_percent)

            # CPU percent (non-blocking for first call)
            cpu_percent = await asyncio.to_thread(process.cpu_percent, 0)
            await self.metrics_collector.set_gauge("app.process.cpu.percent", cpu_percent)

            # Thread count
            num_threads = await asyncio.to_thread(process.num_threads)
            await self.metrics_collector.set_gauge("app.threads.count", num_threads)

        except ImportError:
            logger.debug("psutil not available, skipping process stats")
        except Exception as e:
            logger.error(f"Error collecting process stats: {e}", exc_info=True)

    async def collect_gc_stats(self) -> None:
        """Collect garbage collection statistics."""
        try:
            # Get GC stats (not blocking)
            gc_counts = gc.get_count()

            # Calculate collections since last check
            collections = [
                gc_counts[i] - self._last_gc_counts[i] for i in range(len(gc_counts))
            ]

            # Record total collections
            total_collections = sum(collections)
            if total_collections > 0:
                await self.metrics_collector.increment_counter(
                    "app.gc.collections", total_collections
                )

            self._last_gc_counts = list(gc_counts)

            # Uncollectable objects
            uncollectable = len(gc.garbage)
            await self.metrics_collector.set_gauge("app.gc.uncollectable", uncollectable)

        except Exception as e:
            logger.error(f"Error collecting GC stats: {e}", exc_info=True)

    async def collect_asyncio_stats(self) -> None:
        """Collect asyncio task statistics."""
        try:
            # Get current event loop
            loop = asyncio.get_running_loop()

            # Count active tasks
            tasks = asyncio.all_tasks(loop)
            await self.metrics_collector.set_gauge("app.asyncio.tasks.count", len(tasks))

        except Exception as e:
            logger.error(f"Error collecting asyncio stats: {e}", exc_info=True)

    async def collect_event_loop_health(self) -> None:
        """Measure event loop lag and callback queue depth.

        Event loop lag is measured by scheduling a callback and measuring
        how long it takes to execute.
        """
        try:
            # Measure event loop lag
            lag_start = time.time()
            await asyncio.sleep(0)  # Yield to event loop
            lag_ms = (time.time() - lag_start) * 1000

            await self.metrics_collector.set_gauge("asyncio.event_loop.lag_ms", lag_ms)

            # Get event loop
            loop = asyncio.get_running_loop()

            # Approximate pending callbacks by checking if loop is running
            # Note: This is a simplified metric - actual callback queue depth
            # is not directly accessible in Python's asyncio
            # We can track the number of ready callbacks indirectly
            pending_callbacks = 0
            if hasattr(loop, "_ready"):
                pending_callbacks = len(loop._ready)

            await self.metrics_collector.set_gauge(
                "asyncio.event_loop.pending_callbacks", pending_callbacks
            )

        except Exception as e:
            logger.error(f"Error collecting event loop health: {e}", exc_info=True)

    async def collect_database_stats(self) -> None:
        """Collect database connection pool statistics.

        Monitors SQLAlchemy connection pool if available.
        """
        try:
            from truthgraph.db import engine

            # Get pool statistics
            pool = engine.pool

            # Pool size configuration
            pool_size = pool.size()
            await self.metrics_collector.set_gauge("db.connection.pool.size", pool_size)

            # Checked out connections (active)
            checked_out = pool.checkedout()
            await self.metrics_collector.set_gauge("db.connection.pool.active", checked_out)

            # Available connections (idle)
            # Note: pool.checkedin() would give us checked-in connections
            # Idle = Size - Active (if pool isn't overflowed)
            idle = max(0, pool_size - checked_out)
            await self.metrics_collector.set_gauge("db.connection.pool.idle", idle)

        except Exception as e:
            logger.debug(f"Error collecting database stats: {e}")

    async def check_database_health(self) -> tuple[str, str]:
        """Check database connectivity and health.

        Returns:
            Tuple of (status, message) where status is "healthy", "degraded", or "unhealthy".
        """
        try:
            from truthgraph.db import SessionLocal

            # Time the database check
            start = time.time()

            # Simple connectivity test
            db = SessionLocal()
            try:
                result = db.execute("SELECT 1").scalar()
                response_time_ms = int((time.time() - start) * 1000)

                if result == 1:
                    return ("healthy", f"Database connected (response: {response_time_ms}ms)")
                else:
                    return ("unhealthy", "Database returned unexpected result")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Database health check failed: {e}", exc_info=True)
            return ("unhealthy", f"Database error: {str(e)}")

    async def check_ml_services_health(self) -> dict[str, tuple[str, str]]:
        """Check health of ML services (embedding and NLI).

        Returns:
            Dictionary mapping service name to (status, message) tuple.
        """
        results = {}

        # Check embedding service
        try:
            from truthgraph.services.ml.embedding_service import get_embedding_service

            start = time.time()
            svc = get_embedding_service()
            is_loaded = svc.is_loaded()
            response_time_ms = int((time.time() - start) * 1000)

            if is_loaded:
                status = "healthy"
                message = f"Model loaded (response: {response_time_ms}ms)"
            else:
                status = "degraded"
                message = "Model not loaded (lazy loading enabled)"

            results["embedding_service"] = (status, message)

        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            results["embedding_service"] = ("unhealthy", f"Error: {str(e)}")

        # Check NLI service
        try:
            from truthgraph.services.ml.nli_service import get_nli_service

            start = time.time()
            svc = get_nli_service()
            info = svc.get_model_info()
            response_time_ms = int((time.time() - start) * 1000)

            if info.get("initialized", False):
                status = "healthy"
                message = f"Model initialized (response: {response_time_ms}ms)"
            else:
                status = "degraded"
                message = "Model not initialized (lazy loading enabled)"

            results["nli_service"] = (status, message)

        except Exception as e:
            logger.error(f"NLI service health check failed: {e}")
            results["nli_service"] = ("unhealthy", f"Error: {str(e)}")

        return results

    async def get_process_details(self) -> dict[str, Any]:
        """Get detailed process information.

        Returns:
            Dictionary with detailed process statistics.
        """
        try:
            import psutil

            process = await asyncio.to_thread(psutil.Process)

            memory_info = await asyncio.to_thread(process.memory_info)
            cpu_percent = await asyncio.to_thread(process.cpu_percent, 0)
            num_threads = await asyncio.to_thread(process.num_threads)

            # Get event loop
            loop = asyncio.get_running_loop()
            tasks = asyncio.all_tasks(loop)

            return {
                "process": {
                    "pid": process.pid,
                    "cpu_percent": cpu_percent,
                    "memory_rss_mb": memory_info.rss / (1024 * 1024),
                    "memory_vms_mb": memory_info.vms / (1024 * 1024),
                    "num_threads": num_threads,
                },
                "asyncio": {
                    "active_tasks": len(tasks),
                    "task_names": [t.get_name() for t in list(tasks)[:10]],  # First 10
                },
                "gc": {
                    "collections": gc.get_count(),
                    "uncollectable": len(gc.garbage),
                },
            }

        except Exception as e:
            logger.error(f"Error getting process details: {e}", exc_info=True)
            return {
                "error": str(e),
            }
