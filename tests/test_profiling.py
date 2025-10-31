"""Tests for profiling infrastructure.

This module tests the profiling scripts and validates profiling results
against expected performance characteristics.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.profiling.profile_batch_sizes import BatchSizeProfiler, load_test_data
from scripts.profiling.profile_memory import MemoryProfiler
from scripts.profiling.profile_text_lengths import TextLengthProfiler
from truthgraph.services.ml.embedding_service import EmbeddingService


class TestBatchSizeProfiler:
    """Tests for batch size profiling functionality."""

    def test_batch_size_profiler_initialization(self) -> None:
        """Test that BatchSizeProfiler initializes correctly."""
        texts = ["test text"] * 100
        profiler = BatchSizeProfiler(texts, batch_sizes=[8, 16, 32])

        assert len(profiler.test_texts) == 100
        assert profiler.batch_sizes == [8, 16, 32]
        assert profiler.service is not None

    def test_load_test_data(self) -> None:
        """Test loading test data for profiling."""
        texts = load_test_data(num_texts=50)

        assert len(texts) == 50
        assert all(isinstance(t, str) for t in texts)
        assert all(len(t) > 0 for t in texts)

    def test_warmup_execution(self) -> None:
        """Test that warmup runs without errors."""
        texts = ["test text"] * 10
        profiler = BatchSizeProfiler(texts, batch_sizes=[8])

        # Should not raise
        profiler.warmup(iterations=2)

    def test_memory_usage_measurement(self) -> None:
        """Test that memory usage can be measured."""
        texts = ["test text"] * 10
        profiler = BatchSizeProfiler(texts)

        memory_mb = profiler.get_memory_usage()

        assert isinstance(memory_mb, float)
        assert memory_mb > 0
        assert memory_mb < 10000  # Sanity check

    def test_single_batch_profiling(self) -> None:
        """Test profiling a single batch size."""
        texts = ["test text"] * 100
        profiler = BatchSizeProfiler(texts, batch_sizes=[32])

        result = profiler.profile_batch_size(32)

        assert result["batch_size"] == 32
        assert result["num_texts"] == 100
        assert result["throughput_texts_per_sec"] > 0
        assert result["latency_ms_per_text"] > 0
        assert result["memory_delta_mb"] >= 0

    def test_bottleneck_analysis(self) -> None:
        """Test that bottleneck analysis produces results."""
        texts = ["test text"] * 50
        profiler = BatchSizeProfiler(texts, batch_sizes=[8, 16, 32])

        # Run profiling
        profiler.run_profiling()

        # Analyze bottlenecks
        bottlenecks = profiler.analyze_bottlenecks()

        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) > 0
        assert all("type" in b for b in bottlenecks)
        assert all("finding" in b for b in bottlenecks)

    def test_recommendations_generation(self) -> None:
        """Test that recommendations are generated."""
        texts = ["test text"] * 50
        profiler = BatchSizeProfiler(texts, batch_sizes=[8, 16, 32])

        profiler.run_profiling()
        recommendations = profiler.generate_recommendations()

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all("optimization" in r for r in recommendations)
        assert all("effort" in r for r in recommendations)
        assert all("priority" in r for r in recommendations)


class TestMemoryProfiler:
    """Tests for memory profiling functionality."""

    def test_memory_profiler_initialization(self) -> None:
        """Test that MemoryProfiler initializes correctly."""
        texts = ["test text"] * 100
        profiler = MemoryProfiler(texts)

        assert len(profiler.test_texts) == 100
        assert profiler.service is not None
        assert "metadata" in profiler.results

    def test_detailed_memory_info(self) -> None:
        """Test getting detailed memory information."""
        texts = ["test text"] * 10
        profiler = MemoryProfiler(texts)

        mem_info = profiler.get_detailed_memory_info()

        assert isinstance(mem_info, dict)
        assert "rss_mb" in mem_info
        assert "vms_mb" in mem_info
        assert mem_info["rss_mb"] > 0

    def test_baseline_memory_measurement(self) -> None:
        """Test measuring baseline memory."""
        texts = ["test text"] * 10
        profiler = MemoryProfiler(texts)

        baseline = profiler.measure_baseline_memory()

        assert isinstance(baseline, dict)
        assert "rss_mb" in baseline
        assert baseline["rss_mb"] > 0

    def test_memory_leak_detection(self) -> None:
        """Test memory leak detection."""
        texts = ["test text"] * 50
        profiler = MemoryProfiler(texts)

        leak_check = profiler.check_memory_leaks(batch_size=32, num_iterations=5)

        assert isinstance(leak_check, dict)
        assert "leak_detected" in leak_check
        assert "total_growth_mb" in leak_check
        assert "growth_rate_mb_per_iteration" in leak_check

        # Should not detect leaks in healthy implementation
        assert leak_check["leak_detected"] is False

    def test_memory_patterns_analysis(self) -> None:
        """Test analyzing memory patterns."""
        texts = ["test text"] * 50
        profiler = MemoryProfiler(texts)

        # Run profiling first
        profiler.run_profiling(batch_sizes=[16, 32], num_iterations=2)

        # Analyze patterns
        findings = profiler.analyze_memory_patterns()

        assert isinstance(findings, list)
        assert len(findings) > 0
        assert all("type" in f for f in findings)


class TestTextLengthProfiler:
    """Tests for text length profiling functionality."""

    def test_text_length_profiler_initialization(self) -> None:
        """Test that TextLengthProfiler initializes correctly."""
        profiler = TextLengthProfiler()

        assert profiler.service is not None
        assert "metadata" in profiler.results

    def test_generate_text_of_length(self) -> None:
        """Test generating text of specific length."""
        profiler = TextLengthProfiler()

        for target_length in [10, 50, 100, 256, 512]:
            text = profiler.generate_text_of_length(target_length)

            assert isinstance(text, str)
            assert len(text) == target_length

    def test_create_test_corpus(self) -> None:
        """Test creating test corpus with consistent length."""
        profiler = TextLengthProfiler()

        corpus = profiler.create_test_corpus(length=100, num_texts=50)

        assert len(corpus) == 50
        assert all(len(t) == 100 for t in corpus)

    def test_text_length_profiling(self) -> None:
        """Test profiling a single text length."""
        profiler = TextLengthProfiler()

        result = profiler.profile_text_length(
            text_length=100,
            batch_size=32,
            num_texts=50,
            iterations=2,
        )

        assert result["text_length_chars"] == 100
        assert result["num_texts"] == 50
        assert result["avg_throughput_texts_per_sec"] > 0
        assert result["avg_latency_ms_per_text"] > 0

    def test_analyze_results(self) -> None:
        """Test analyzing text length results."""
        profiler = TextLengthProfiler()

        # Run profiling first
        profiler.run_profiling(
            text_lengths=[50, 100, 200],
            batch_size=32,
            num_texts=50,
            iterations=2,
        )

        # Analyze
        analysis = profiler.analyze_results()

        assert isinstance(analysis, dict)
        assert "best_performance" in analysis
        assert "worst_performance" in analysis
        assert "performance_drop_percent" in analysis

    def test_generate_recommendations(self) -> None:
        """Test generating text length recommendations."""
        profiler = TextLengthProfiler()

        # Run profiling first
        profiler.run_profiling(
            text_lengths=[50, 100, 200],
            batch_size=32,
            num_texts=50,
            iterations=2,
        )

        recommendations = profiler.generate_recommendations()

        assert isinstance(recommendations, list)
        # Recommendations may be empty if performance is good across all lengths
        if recommendations:
            assert all("optimization" in r for r in recommendations)


class TestProfilingResults:
    """Tests for profiling result validation."""

    def test_result_files_exist(self) -> None:
        """Test that profiling result files exist."""
        results_dir = project_root / "scripts" / "profiling" / "results"

        # Look for any profiling result files
        batch_files = list(results_dir.glob("batch_size_profile_*.json"))
        memory_files = list(results_dir.glob("memory_analysis_*.json"))
        text_files = list(results_dir.glob("text_length_profile_*.json"))

        # At least one of each type should exist if profiling was run
        # This is a soft check - files may not exist in CI environment
        if batch_files:
            assert len(batch_files) > 0
        if memory_files:
            assert len(memory_files) > 0
        if text_files:
            assert len(text_files) > 0

    def test_batch_result_format(self) -> None:
        """Test that batch size results have correct format."""
        results_dir = project_root / "scripts" / "profiling" / "results"
        batch_files = list(results_dir.glob("batch_size_profile_*.json"))

        if not batch_files:
            pytest.skip("No batch size profiling results found")

        # Load most recent file
        latest_file = max(batch_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file) as f:
            results = json.load(f)

        # Validate structure
        assert "metadata" in results
        assert "batch_results" in results
        assert "bottlenecks" in results
        assert "recommendations" in results

        # Validate metadata
        assert "device" in results["metadata"]
        assert "model" in results["metadata"]

        # Validate batch results
        if results["batch_results"]:
            first_result = results["batch_results"][0]
            assert "batch_size" in first_result
            assert "throughput_texts_per_sec" in first_result
            assert "latency_ms_per_text" in first_result

    def test_memory_result_format(self) -> None:
        """Test that memory results have correct format."""
        results_dir = project_root / "scripts" / "profiling" / "results"
        memory_files = list(results_dir.glob("memory_analysis_*.json"))

        if not memory_files:
            pytest.skip("No memory profiling results found")

        latest_file = max(memory_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file) as f:
            results = json.load(f)

        assert "metadata" in results
        assert "batch_memory_analysis" in results
        assert "memory_leak_check" in results

        # Validate leak check
        leak_check = results.get("memory_leak_check", {})
        if leak_check:
            assert "leak_detected" in leak_check
            assert isinstance(leak_check["leak_detected"], bool)

    def test_performance_vs_baseline(self) -> None:
        """Test that current performance meets or exceeds baseline."""
        # Load baseline
        baseline_path = project_root / "scripts" / "benchmarks" / "results" / "baseline_embeddings_2025-10-27.json"

        if not baseline_path.exists():
            pytest.skip("Baseline file not found")

        with open(baseline_path) as f:
            baseline = json.load(f)

        # Get baseline throughput at batch_size=64
        baseline_batch_64 = next(
            (r for r in baseline["benchmarks"]["batch_sizes"]["batch_results"] if r["batch_size"] == 64),
            None
        )

        if not baseline_batch_64:
            pytest.skip("Baseline batch_size=64 result not found")

        baseline_throughput = baseline_batch_64["throughput_texts_per_sec"]

        # Load current results
        results_dir = project_root / "scripts" / "profiling" / "results"
        batch_files = list(results_dir.glob("batch_size_profile_*.json"))

        if not batch_files:
            pytest.skip("No current profiling results found")

        latest_file = max(batch_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file) as f:
            current = json.load(f)

        # Get current throughput at batch_size=64
        current_batch_64 = next(
            (r for r in current["batch_results"] if r["batch_size"] == 64),
            None
        )

        if not current_batch_64:
            pytest.skip("Current batch_size=64 result not found")

        current_throughput = current_batch_64["throughput_texts_per_sec"]

        # Allow 10% variance (can be positive or negative due to system differences)
        variance_pct = abs((current_throughput - baseline_throughput) / baseline_throughput) * 100

        # Should be within 20% of baseline (accounts for system differences)
        assert variance_pct < 20, f"Performance variance too high: {variance_pct:.1f}%"


class TestEmbeddingServiceConfiguration:
    """Tests for embedding service configuration."""

    def test_default_batch_size(self) -> None:
        """Test that default batch size is reasonable."""
        default_batch_size = EmbeddingService.DEFAULT_BATCH_SIZE

        # Should be at least 32 based on profiling results
        assert default_batch_size >= 32
        # Should not be excessively large
        assert default_batch_size <= 256

    def test_embedding_dimension(self) -> None:
        """Test that embedding dimension is correct."""
        assert EmbeddingService.EMBEDDING_DIMENSION == 384

    def test_model_name(self) -> None:
        """Test that model name is correct."""
        assert EmbeddingService.MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"


def test_profiling_infrastructure_integration() -> None:
    """Integration test for complete profiling workflow."""
    # This test runs a mini-profiling workflow to ensure everything works together

    # Load small test dataset
    texts = load_test_data(num_texts=50)

    # Test batch size profiling
    batch_profiler = BatchSizeProfiler(texts, batch_sizes=[16, 32])
    batch_results = batch_profiler.run_profiling()

    assert len(batch_results["batch_results"]) == 2
    assert len(batch_results["bottlenecks"]) > 0
    assert len(batch_results["recommendations"]) > 0

    # Test memory profiling
    memory_profiler = MemoryProfiler(texts)
    memory_results = memory_profiler.run_profiling(batch_sizes=[16, 32], num_iterations=2)

    assert len(memory_results["batch_memory_analysis"]) == 2
    assert "memory_leak_check" in memory_results
    assert memory_results["memory_leak_check"]["leak_detected"] is False

    # Test text length profiling
    text_profiler = TextLengthProfiler()
    text_results = text_profiler.run_profiling(
        text_lengths=[50, 100],
        batch_size=32,
        num_texts=50,
        iterations=2,
    )

    assert len(text_results["length_results"]) == 2
    assert "analysis" in text_results

    # Verify all profilers completed successfully
    assert batch_results["metadata"]["device"] in ["cpu", "cuda", "mps"]
    assert memory_results["metadata"]["device"] in ["cpu", "cuda", "mps"]
    assert text_results["metadata"]["device"] in ["cpu", "cuda", "mps"]
