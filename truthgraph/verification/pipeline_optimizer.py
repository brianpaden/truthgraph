"""Pipeline Optimization Utilities for Feature 2.4.

This module provides utilities for optimizing the verification pipeline based on
findings from Features 2.1, 2.2, and 2.3. It includes:
- Batch size optimization
- Memory-aware processing
- Parallel execution strategies
- Performance monitoring

Key optimizations:
- Embedding: batch_size=64 (Feature 2.1)
- NLI: batch_size=16 (Feature 2.2)
- Vector search: lists=50, probes=10 (Feature 2.3)
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import psutil
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class OptimizationConfig:
    """Configuration for pipeline optimizations.

    Attributes:
        embedding_batch_size: Batch size for embedding generation (default: 64 from Feature 2.1)
        nli_batch_size: Batch size for NLI inference (default: 16 from Feature 2.2)
        vector_search_lists: IVFFlat lists parameter (default: 50 from Feature 2.3)
        vector_search_probes: IVFFlat probes parameter (default: 10 from Feature 2.3)
        text_truncation_chars: Max text length (default: 256 from Feature 2.1)
        max_evidence_per_claim: Max evidence items to retrieve (default: 10)
        parallel_claim_processing: Enable parallel processing (default: False)
        max_workers: Max parallel workers (default: 4)
        memory_limit_mb: Memory limit in MB (default: 4096 from Feature 2.5)
    """

    embedding_batch_size: int = 64
    nli_batch_size: int = 16
    vector_search_lists: int = 50
    vector_search_probes: int = 10
    text_truncation_chars: int = 256
    max_evidence_per_claim: int = 10
    parallel_claim_processing: bool = False
    max_workers: int = 4
    memory_limit_mb: int = 4096

    @classmethod
    def get_optimized_config(cls) -> "OptimizationConfig":
        """Get optimized configuration based on Features 2.1-2.3.

        Returns:
            OptimizationConfig with optimal settings
        """
        return cls(
            embedding_batch_size=64,  # Feature 2.1: +13% improvement
            nli_batch_size=16,  # Feature 2.2: +28% improvement
            vector_search_lists=50,  # Feature 2.3: optimal for 10K corpus
            vector_search_probes=10,  # Feature 2.3: 96.5% recall, 45ms latency
            text_truncation_chars=256,  # Feature 2.1: +40-60% for long texts
            max_evidence_per_claim=10,
            parallel_claim_processing=True,
            max_workers=4,
            memory_limit_mb=4096,  # Feature 2.5: target memory budget
        )

    @classmethod
    def get_conservative_config(cls) -> "OptimizationConfig":
        """Get conservative configuration for memory-constrained environments.

        Returns:
            OptimizationConfig with conservative settings
        """
        return cls(
            embedding_batch_size=32,
            nli_batch_size=8,
            vector_search_lists=25,
            vector_search_probes=5,
            text_truncation_chars=256,
            max_evidence_per_claim=5,
            parallel_claim_processing=False,
            max_workers=2,
            memory_limit_mb=2048,
        )


class MemoryMonitor:
    """Monitor memory usage during pipeline execution."""

    def __init__(self, limit_mb: int = 4096):
        """Initialize memory monitor.

        Args:
            limit_mb: Memory limit in MB
        """
        self.limit_mb = limit_mb
        self.process = psutil.Process()
        self.baseline_memory_mb: float | None = None

    def get_current_memory_mb(self) -> float:
        """Get current memory usage in MB.

        Returns:
            Current memory in MB
        """
        return float(self.process.memory_info().rss / 1024 / 1024)

    def set_baseline(self) -> None:
        """Set baseline memory measurement."""
        self.baseline_memory_mb = self.get_current_memory_mb()
        logger.info("memory_baseline_set", baseline_mb=self.baseline_memory_mb)

    def get_delta_mb(self) -> float:
        """Get memory delta from baseline.

        Returns:
            Memory delta in MB
        """
        if self.baseline_memory_mb is None:
            self.set_baseline()

        current = self.get_current_memory_mb()
        delta = current - (self.baseline_memory_mb or 0)

        return delta

    def check_limit(self) -> bool:
        """Check if memory limit is exceeded.

        Returns:
            True if within limit, False if exceeded
        """
        current = self.get_current_memory_mb()
        within_limit = current < self.limit_mb

        if not within_limit:
            logger.warning(
                "memory_limit_exceeded",
                current_mb=current,
                limit_mb=self.limit_mb,
            )

        return within_limit

    def get_available_mb(self) -> float:
        """Get available memory before hitting limit.

        Returns:
            Available memory in MB
        """
        current = self.get_current_memory_mb()
        return max(0, self.limit_mb - current)


class BatchSizeOptimizer:
    """Optimize batch sizes dynamically based on memory constraints."""

    def __init__(self, memory_monitor: MemoryMonitor):
        """Initialize batch size optimizer.

        Args:
            memory_monitor: Memory monitor instance
        """
        self.memory_monitor = memory_monitor

    def get_optimal_batch_size(
        self,
        default_batch_size: int,
        item_memory_mb: float,
        min_batch_size: int = 1,
        max_batch_size: int = 256,
    ) -> int:
        """Calculate optimal batch size based on available memory.

        Args:
            default_batch_size: Default batch size
            item_memory_mb: Estimated memory per item in MB
            min_batch_size: Minimum batch size
            max_batch_size: Maximum batch size

        Returns:
            Optimal batch size
        """
        available_mb = self.memory_monitor.get_available_mb()

        # Calculate max batch size that fits in memory
        max_items = int(available_mb / item_memory_mb) if item_memory_mb > 0 else max_batch_size

        # Constrain to range
        optimal = min(max(min_batch_size, max_items), max_batch_size, default_batch_size)

        if optimal < default_batch_size:
            logger.warning(
                "batch_size_reduced_for_memory",
                default=default_batch_size,
                optimal=optimal,
                available_mb=available_mb,
            )

        return optimal


class ParallelExecutor:
    """Execute pipeline operations in parallel for better throughput."""

    def __init__(self, max_workers: int = 4):
        """Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers

    def execute_parallel(
        self,
        func: Callable[[T], Any],
        items: list[T],
        description: str = "parallel_execution",
    ) -> list[Any]:
        """Execute function in parallel over items.

        Args:
            func: Function to execute
            items: List of items to process
            description: Description for logging

        Returns:
            List of results
        """
        if not items:
            return []

        logger.info(
            f"{description}_start",
            num_items=len(items),
            max_workers=self.max_workers,
        )

        start_time = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(func, item): i for i, item in enumerate(items)
            }

            # Collect results in order
            ordered_results: dict[int, Any] = {}
            for future in as_completed(future_to_item):
                index = future_to_item[future]
                try:
                    result = future.result()
                    ordered_results[index] = result
                except Exception as e:
                    logger.error(
                        f"{description}_item_failed",
                        index=index,
                        error=str(e),
                    )
                    ordered_results[index] = None

        # Return in original order
        results = [ordered_results[i] for i in range(len(items))]

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"{description}_complete",
            num_items=len(items),
            duration_ms=duration_ms,
            items_per_sec=len(items) / (duration_ms / 1000) if duration_ms > 0 else 0,
        )

        return results


class TextPreprocessor:
    """Preprocess text for optimal pipeline performance."""

    def __init__(self, truncation_chars: int = 256):
        """Initialize text preprocessor.

        Args:
            truncation_chars: Maximum text length
        """
        self.truncation_chars = truncation_chars

    def truncate_text(self, text: str, preserve_sentences: bool = True) -> str:
        """Truncate text to maximum length.

        Args:
            text: Text to truncate
            preserve_sentences: Try to preserve sentence boundaries

        Returns:
            Truncated text
        """
        if len(text) <= self.truncation_chars:
            return text

        truncated = text[: self.truncation_chars]

        if preserve_sentences:
            # Try to break at sentence boundary
            for delimiter in [".", "!", "?", ";", ","]:
                last_delim = truncated.rfind(delimiter)
                if last_delim > self.truncation_chars * 0.7:  # At least 70% through
                    return truncated[: last_delim + 1].strip()

        return truncated.strip()

    def preprocess_batch(
        self, texts: list[str], preserve_sentences: bool = True
    ) -> list[str]:
        """Preprocess batch of texts.

        Args:
            texts: List of texts
            preserve_sentences: Try to preserve sentence boundaries

        Returns:
            List of preprocessed texts
        """
        return [
            self.truncate_text(text, preserve_sentences) for text in texts
        ]


class PerformanceTracker:
    """Track performance metrics for pipeline optimization."""

    def __init__(self):
        """Initialize performance tracker."""
        self.metrics: dict[str, list[float]] = {}
        self.stage_timings: dict[str, list[float]] = {}

    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
        """
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)

    def record_stage_timing(self, stage: str, duration_ms: float) -> None:
        """Record stage timing.

        Args:
            stage: Stage name
            duration_ms: Duration in milliseconds
        """
        if stage not in self.stage_timings:
            self.stage_timings[stage] = []
        self.stage_timings[stage].append(duration_ms)

    def get_average(self, name: str) -> float:
        """Get average value for a metric.

        Args:
            name: Metric name

        Returns:
            Average value or 0 if no data
        """
        values = self.metrics.get(name, [])
        return sum(values) / len(values) if values else 0.0

    def get_stage_average(self, stage: str) -> float:
        """Get average timing for a stage.

        Args:
            stage: Stage name

        Returns:
            Average timing in ms or 0 if no data
        """
        timings = self.stage_timings.get(stage, [])
        return sum(timings) / len(timings) if timings else 0.0

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all metrics.

        Returns:
            Dictionary with metric summaries
        """
        summary = {
            "metrics": {
                name: {
                    "count": len(values),
                    "average": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                }
                for name, values in self.metrics.items()
            },
            "stages": {
                stage: {
                    "count": len(timings),
                    "average_ms": sum(timings) / len(timings) if timings else 0,
                    "total_ms": sum(timings),
                }
                for stage, timings in self.stage_timings.items()
            },
        }

        return summary


def configure_database_for_optimization(
    db_session: Any, config: OptimizationConfig
) -> None:
    """Configure database session for optimal performance.

    Args:
        db_session: Database session
        config: Optimization configuration

    Returns:
        None
    """
    from sqlalchemy import text

    try:
        # Set IVFFlat probes for vector search
        db_session.execute(
            text(f"SET ivfflat.probes = {config.vector_search_probes}")
        )

        logger.info(
            "database_configured",
            probes=config.vector_search_probes,
            lists=config.vector_search_lists,
        )

    except Exception as e:
        logger.warning(
            "database_configuration_failed",
            error=str(e),
        )
