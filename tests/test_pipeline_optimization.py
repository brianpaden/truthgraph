"""Tests for pipeline optimization (Feature 2.4).

These tests verify the pipeline optimization infrastructure, including:
- OptimizationConfig
- MemoryMonitor
- BatchSizeOptimizer
- ParallelExecutor
- TextPreprocessor
- PerformanceTracker
"""

import time
from pathlib import Path

from truthgraph.verification import (
    BatchSizeOptimizer,
    MemoryMonitor,
    OptimizationConfig,
    ParallelExecutor,
    PerformanceTracker,
    TextPreprocessor,
)


class TestOptimizationConfig:
    """Tests for OptimizationConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = OptimizationConfig()

        assert config.embedding_batch_size == 64
        assert config.nli_batch_size == 16
        assert config.vector_search_lists == 50
        assert config.vector_search_probes == 10
        assert config.text_truncation_chars == 256

    def test_optimized_config(self) -> None:
        """Test optimized configuration from Features 2.1-2.3."""
        config = OptimizationConfig.get_optimized_config()

        # Feature 2.1: Embedding optimization
        assert config.embedding_batch_size == 64

        # Feature 2.2: NLI optimization
        assert config.nli_batch_size == 16

        # Feature 2.3: Vector search optimization
        assert config.vector_search_lists == 50
        assert config.vector_search_probes == 10

        # Text truncation
        assert config.text_truncation_chars == 256

        # Parallel processing enabled
        assert config.parallel_claim_processing is True

    def test_conservative_config(self) -> None:
        """Test conservative configuration for memory-constrained environments."""
        config = OptimizationConfig.get_conservative_config()

        assert config.embedding_batch_size == 32
        assert config.nli_batch_size == 8
        assert config.vector_search_lists == 25
        assert config.vector_search_probes == 5
        assert config.memory_limit_mb == 2048
        assert config.parallel_claim_processing is False

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = OptimizationConfig(
            embedding_batch_size=128,
            nli_batch_size=32,
            text_truncation_chars=512,
        )

        assert config.embedding_batch_size == 128
        assert config.nli_batch_size == 32
        assert config.text_truncation_chars == 512


class TestMemoryMonitor:
    """Tests for MemoryMonitor."""

    def test_memory_monitor_initialization(self) -> None:
        """Test memory monitor initialization."""
        monitor = MemoryMonitor(limit_mb=4096)

        assert monitor.limit_mb == 4096
        assert monitor.baseline_memory_mb is None

    def test_get_current_memory(self) -> None:
        """Test getting current memory usage."""
        monitor = MemoryMonitor()
        memory_mb = monitor.get_current_memory_mb()

        assert memory_mb > 0
        assert memory_mb < 10000  # Reasonable upper bound

    def test_set_baseline(self) -> None:
        """Test setting memory baseline."""
        monitor = MemoryMonitor()
        monitor.set_baseline()

        assert monitor.baseline_memory_mb is not None
        assert monitor.baseline_memory_mb > 0

    def test_get_delta_mb(self) -> None:
        """Test getting memory delta."""
        monitor = MemoryMonitor()
        monitor.set_baseline()

        delta = monitor.get_delta_mb()

        # Delta should be small initially
        assert -100 < delta < 100  # Within 100MB variance

    def test_check_limit(self) -> None:
        """Test memory limit checking."""
        monitor = MemoryMonitor(limit_mb=10000)  # High limit

        # Should be within limit
        assert monitor.check_limit() is True

    def test_get_available_mb(self) -> None:
        """Test getting available memory."""
        monitor = MemoryMonitor(limit_mb=4096)
        available = monitor.get_available_mb()

        assert available >= 0
        assert available <= 4096


class TestBatchSizeOptimizer:
    """Tests for BatchSizeOptimizer."""

    def test_optimizer_initialization(self) -> None:
        """Test batch size optimizer initialization."""
        monitor = MemoryMonitor()
        optimizer = BatchSizeOptimizer(monitor)

        assert optimizer.memory_monitor is monitor

    def test_get_optimal_batch_size_with_plenty_memory(self) -> None:
        """Test optimal batch size calculation with plenty of memory."""
        monitor = MemoryMonitor(limit_mb=10000)
        monitor.set_baseline()
        optimizer = BatchSizeOptimizer(monitor)

        optimal = optimizer.get_optimal_batch_size(default_batch_size=64, item_memory_mb=1.0)

        # Should return default since plenty of memory
        assert optimal == 64

    def test_get_optimal_batch_size_constrained(self) -> None:
        """Test optimal batch size with memory constraints."""
        monitor = MemoryMonitor(limit_mb=100)
        monitor.set_baseline()
        optimizer = BatchSizeOptimizer(monitor)

        optimal = optimizer.get_optimal_batch_size(
            default_batch_size=64,
            item_memory_mb=10.0,  # 10MB per item
            min_batch_size=1,
        )

        # Should be reduced due to memory constraints
        assert 1 <= optimal < 64

    def test_min_max_batch_size_constraints(self) -> None:
        """Test min/max batch size constraints."""
        monitor = MemoryMonitor()
        monitor.set_baseline()
        optimizer = BatchSizeOptimizer(monitor)

        optimal = optimizer.get_optimal_batch_size(
            default_batch_size=64,
            item_memory_mb=0.1,
            min_batch_size=16,
            max_batch_size=32,
        )

        assert 16 <= optimal <= 32


class TestParallelExecutor:
    """Tests for ParallelExecutor."""

    def test_parallel_executor_initialization(self) -> None:
        """Test parallel executor initialization."""
        executor = ParallelExecutor(max_workers=4)

        assert executor.max_workers == 4

    def test_execute_parallel_basic(self) -> None:
        """Test basic parallel execution."""

        def square(x: int) -> int:
            return x * x

        executor = ParallelExecutor(max_workers=2)
        items = [1, 2, 3, 4, 5]

        results = executor.execute_parallel(square, items)

        assert results == [1, 4, 9, 16, 25]

    def test_execute_parallel_empty_list(self) -> None:
        """Test parallel execution with empty list."""

        def noop(x: int) -> int:
            return x

        executor = ParallelExecutor()
        results = executor.execute_parallel(noop, [])

        assert results == []

    def test_execute_parallel_with_errors(self) -> None:
        """Test parallel execution handles errors gracefully."""

        def maybe_fail(x: int) -> int:
            if x == 3:
                raise ValueError("Test error")
            return x * 2

        executor = ParallelExecutor(max_workers=2)
        items = [1, 2, 3, 4, 5]

        results = executor.execute_parallel(maybe_fail, items)

        # Error should be logged and result should be None for that item
        assert results[0] == 2  # 1 * 2
        assert results[1] == 4  # 2 * 2
        assert results[2] is None  # Error case
        assert results[3] == 8  # 4 * 2
        assert results[4] == 10  # 5 * 2

    def test_execute_parallel_performance(self) -> None:
        """Test that parallel execution is actually faster."""

        def slow_task(x: int) -> int:
            time.sleep(0.01)  # 10ms delay
            return x

        # Sequential (single worker)
        executor_seq = ParallelExecutor(max_workers=1)
        start_seq = time.time()
        executor_seq.execute_parallel(slow_task, list(range(10)))
        duration_seq = time.time() - start_seq

        # Parallel (4 workers)
        executor_par = ParallelExecutor(max_workers=4)
        start_par = time.time()
        executor_par.execute_parallel(slow_task, list(range(10)))
        duration_par = time.time() - start_par

        # Parallel should be faster
        # With 10 items and 4 workers vs 1 worker, expect ~3x speedup
        assert duration_par < duration_seq * 0.7  # At least 30% faster


class TestTextPreprocessor:
    """Tests for TextPreprocessor."""

    def test_preprocessor_initialization(self) -> None:
        """Test text preprocessor initialization."""
        preprocessor = TextPreprocessor(truncation_chars=256)

        assert preprocessor.truncation_chars == 256

    def test_truncate_short_text(self) -> None:
        """Test truncating text that's already short."""
        preprocessor = TextPreprocessor(truncation_chars=256)
        text = "This is a short text."

        result = preprocessor.truncate_text(text)

        assert result == text

    def test_truncate_long_text(self) -> None:
        """Test truncating long text."""
        preprocessor = TextPreprocessor(truncation_chars=50)
        text = "This is a very long text that exceeds the maximum character limit and should be truncated."

        result = preprocessor.truncate_text(text)

        assert len(result) <= 50
        assert result.startswith("This is a very long text")

    def test_truncate_preserve_sentences(self) -> None:
        """Test truncating with sentence preservation."""
        preprocessor = TextPreprocessor(truncation_chars=50)
        text = "First sentence here. Second sentence that will be cut. Third sentence."

        result = preprocessor.truncate_text(text, preserve_sentences=True)

        # Should try to break at sentence boundary
        assert len(result) <= 50
        # Should either end with punctuation or be intelligently truncated
        assert result.startswith("First sentence here")

    def test_truncate_no_sentence_preservation(self) -> None:
        """Test truncating without sentence preservation."""
        preprocessor = TextPreprocessor(truncation_chars=30)
        text = "This is a long text without clear sentence boundaries"

        result = preprocessor.truncate_text(text, preserve_sentences=False)

        assert len(result) <= 30

    def test_preprocess_batch(self) -> None:
        """Test batch preprocessing."""
        preprocessor = TextPreprocessor(truncation_chars=20)
        texts = [
            "Short",
            "This is a medium length text",
            "Another text here that is quite long and should be truncated",
        ]

        results = preprocessor.preprocess_batch(texts)

        assert len(results) == 3
        assert results[0] == "Short"
        assert len(results[1]) <= 20
        assert len(results[2]) <= 20


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_tracker_initialization(self) -> None:
        """Test performance tracker initialization."""
        tracker = PerformanceTracker()

        assert tracker.metrics == {}
        assert tracker.stage_timings == {}

    def test_record_metric(self) -> None:
        """Test recording a metric."""
        tracker = PerformanceTracker()

        tracker.record_metric("throughput", 100.5)
        tracker.record_metric("throughput", 105.2)

        assert "throughput" in tracker.metrics
        assert len(tracker.metrics["throughput"]) == 2

    def test_record_stage_timing(self) -> None:
        """Test recording stage timing."""
        tracker = PerformanceTracker()

        tracker.record_stage_timing("embedding", 150.0)
        tracker.record_stage_timing("embedding", 145.0)

        assert "embedding" in tracker.stage_timings
        assert len(tracker.stage_timings["embedding"]) == 2

    def test_get_average(self) -> None:
        """Test getting average metric."""
        tracker = PerformanceTracker()

        tracker.record_metric("latency", 10.0)
        tracker.record_metric("latency", 20.0)
        tracker.record_metric("latency", 30.0)

        avg = tracker.get_average("latency")

        assert avg == 20.0

    def test_get_average_no_data(self) -> None:
        """Test getting average with no data."""
        tracker = PerformanceTracker()

        avg = tracker.get_average("nonexistent")

        assert avg == 0.0

    def test_get_stage_average(self) -> None:
        """Test getting average stage timing."""
        tracker = PerformanceTracker()

        tracker.record_stage_timing("nli", 100.0)
        tracker.record_stage_timing("nli", 200.0)

        avg = tracker.get_stage_average("nli")

        assert avg == 150.0

    def test_get_summary(self) -> None:
        """Test getting performance summary."""
        tracker = PerformanceTracker()

        tracker.record_metric("throughput", 100)
        tracker.record_metric("throughput", 200)
        tracker.record_stage_timing("embedding", 50)
        tracker.record_stage_timing("nli", 100)

        summary = tracker.get_summary()

        assert "metrics" in summary
        assert "stages" in summary
        assert "throughput" in summary["metrics"]
        assert "embedding" in summary["stages"]
        assert "nli" in summary["stages"]

        # Check metric summary
        assert summary["metrics"]["throughput"]["count"] == 2
        assert summary["metrics"]["throughput"]["average"] == 150.0
        assert summary["metrics"]["throughput"]["min"] == 100
        assert summary["metrics"]["throughput"]["max"] == 200

        # Check stage summary
        assert summary["stages"]["embedding"]["count"] == 1
        assert summary["stages"]["embedding"]["average_ms"] == 50.0
        assert summary["stages"]["nli"]["total_ms"] == 100.0


class TestProfilingScripts:
    """Tests for profiling scripts existence and basic functionality."""

    def test_profile_pipeline_script_exists(self) -> None:
        """Test that profile_pipeline.py exists."""
        script_path = Path("scripts/profiling/profile_pipeline.py")
        assert script_path.exists()

    def test_pipeline_analysis_script_exists(self) -> None:
        """Test that pipeline_analysis.py exists."""
        script_path = Path("scripts/profiling/pipeline_analysis.py")
        assert script_path.exists()

    def test_profiling_results_directory(self) -> None:
        """Test that results directory can be created."""
        results_dir = Path("scripts/profiling/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        assert results_dir.exists()
        assert results_dir.is_dir()


class TestIntegration:
    """Integration tests for pipeline optimization."""

    def test_full_optimization_workflow(self) -> None:
        """Test complete optimization workflow."""
        # 1. Create optimized config
        config = OptimizationConfig.get_optimized_config()

        # 2. Initialize monitor
        monitor = MemoryMonitor(limit_mb=config.memory_limit_mb)
        monitor.set_baseline()

        # 3. Initialize optimizer
        optimizer = BatchSizeOptimizer(monitor)

        # 4. Get optimal batch size
        batch_size = optimizer.get_optimal_batch_size(
            default_batch_size=config.embedding_batch_size,
            item_memory_mb=2.0,
        )

        assert batch_size > 0

        # 5. Initialize preprocessor
        preprocessor = TextPreprocessor(truncation_chars=config.text_truncation_chars)

        # 6. Process test texts
        texts = ["Short text", "A" * 1000]  # One short, one long
        processed = preprocessor.preprocess_batch(texts)

        assert len(processed) == 2
        assert all(len(t) <= config.text_truncation_chars for t in processed)

        # 7. Track performance
        tracker = PerformanceTracker()
        tracker.record_stage_timing("test_stage", 100.0)
        summary = tracker.get_summary()

        assert "test_stage" in summary["stages"]

    def test_optimization_config_applied_correctly(self) -> None:
        """Test that optimization config values match Feature 2.1-2.3 findings."""
        config = OptimizationConfig.get_optimized_config()

        # Feature 2.1: Embedding batch_size=64 for +13% improvement
        assert config.embedding_batch_size == 64

        # Feature 2.2: NLI batch_size=16 for +28% improvement
        assert config.nli_batch_size == 16

        # Feature 2.3: Vector search lists=50, probes=10 for 45ms latency
        assert config.vector_search_lists == 50
        assert config.vector_search_probes == 10

        # Feature 2.1: Text truncation=256 for +40-60% improvement
        assert config.text_truncation_chars == 256

        # Feature 2.5: Memory limit=4096MB
        assert config.memory_limit_mb == 4096
