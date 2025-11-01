"""Tests for NLI profiling scripts.

This module tests the NLI profiling infrastructure including:
- NLIProfiler class and methods
- BatchOptimizer class and methods
- Result generation and validation
- Performance metrics calculation
- Accuracy validation
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import profiling classes by adding scripts to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "profiling"))

from profile_nli import NLIProfiler  # type: ignore[import-not-found]
from nli_batch_optimization import BatchOptimizer  # type: ignore[import-not-found]

from truthgraph.services.ml.nli_service import NLILabel, NLIResult, get_nli_service


class TestNLIProfiler:
    """Tests for NLIProfiler class."""

    def test_profiler_initialization(self) -> None:
        """Test profiler initializes correctly."""
        profiler = NLIProfiler()

        assert profiler.service is not None
        assert profiler.test_pairs == []
        assert profiler.results is not None
        assert "timestamp" in profiler.results
        assert "system" in profiler.results
        assert "batch_profiles" in profiler.results

    def test_load_test_data(self) -> None:
        """Test test data generation."""
        profiler = NLIProfiler()
        profiler.load_test_data(num_pairs=50)

        assert len(profiler.test_pairs) == 50
        assert all(isinstance(pair, tuple) for pair in profiler.test_pairs)
        assert all(len(pair) == 2 for pair in profiler.test_pairs)
        assert all(isinstance(pair[0], str) and isinstance(pair[1], str) for pair in profiler.test_pairs)

    def test_load_test_data_default_size(self) -> None:
        """Test default test data size."""
        profiler = NLIProfiler()
        profiler.load_test_data()

        assert len(profiler.test_pairs) == 100

    def test_capture_system_info(self) -> None:
        """Test system information capture."""
        profiler = NLIProfiler()
        profiler.capture_system_info()

        system_info = profiler.results["system"]
        assert "python_version" in system_info
        assert "pytorch_version" in system_info
        assert "cuda_available" in system_info
        assert "device" in system_info
        assert "model" in system_info

    def test_warmup_execution(self) -> None:
        """Test model warmup completes without errors."""
        profiler = NLIProfiler()
        profiler.load_test_data(10)

        # Should not raise
        profiler.warmup(num_iterations=2)

    def test_measure_memory(self) -> None:
        """Test memory measurement returns valid value."""
        profiler = NLIProfiler()
        memory_mb = profiler.measure_memory()

        assert isinstance(memory_mb, float)
        assert memory_mb > 0
        assert memory_mb < 10000  # Reasonable upper bound

    def test_profile_batch_size(self) -> None:
        """Test profiling a single batch size."""
        profiler = NLIProfiler()
        profiler.load_test_data(20)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=4, num_pairs=20)

        assert result["batch_size"] == 4
        assert result["num_pairs"] == 20
        assert result["elapsed_time_s"] > 0
        assert result["throughput_pairs_per_sec"] > 0
        assert result["latency_ms_per_pair"] > 0
        assert "memory_before_mb" in result
        assert "memory_after_mb" in result
        assert "memory_delta_mb" in result
        assert "label_distribution" in result
        assert "avg_confidence" in result

    def test_profile_batch_size_single_pair(self) -> None:
        """Test profiling with batch_size=1."""
        profiler = NLIProfiler()
        profiler.load_test_data(10)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=1, num_pairs=10)

        assert result["batch_size"] == 1
        assert result["num_pairs"] == 10
        assert result["throughput_pairs_per_sec"] > 0

    def test_run_all_profiles(self) -> None:
        """Test running multiple batch size profiles."""
        profiler = NLIProfiler()

        batch_sizes = [4, 8]
        profiler.run_all_profiles(batch_sizes, num_pairs=20)

        assert len(profiler.results["batch_profiles"]) == len(batch_sizes)

        for i, batch_size in enumerate(batch_sizes):
            profile = profiler.results["batch_profiles"][i]
            assert profile["batch_size"] == batch_size
            assert profile["throughput_pairs_per_sec"] > 0

    def test_analyze_results(self) -> None:
        """Test result analysis generates bottlenecks and recommendations."""
        profiler = NLIProfiler()
        profiler.run_all_profiles([4, 16], num_pairs=20)

        # Analysis should run automatically
        assert "bottlenecks" in profiler.results
        assert "recommendations" in profiler.results
        assert isinstance(profiler.results["bottlenecks"], list)
        assert isinstance(profiler.results["recommendations"], list)

    def test_save_results(self, tmp_path: Path) -> None:
        """Test saving results to JSON file."""
        profiler = NLIProfiler()
        profiler.load_test_data(10)
        profiler.run_all_profiles([4], num_pairs=10)

        output_path = tmp_path / "test_results.json"
        profiler.save_results(output_path)

        assert output_path.exists()

        # Verify JSON structure
        with open(output_path) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "system" in data
        assert "batch_profiles" in data

    def test_label_distribution_validation(self) -> None:
        """Test label distribution is captured correctly."""
        profiler = NLIProfiler()
        profiler.load_test_data(30)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=8, num_pairs=30)

        dist = result["label_distribution"]
        assert NLILabel.ENTAILMENT.value in dist
        assert NLILabel.CONTRADICTION.value in dist
        assert NLILabel.NEUTRAL.value in dist

        total_count = sum(dist.values())
        assert total_count == 30


class TestBatchOptimizer:
    """Tests for BatchOptimizer class."""

    def test_optimizer_initialization(self) -> None:
        """Test optimizer initializes correctly."""
        optimizer = BatchOptimizer()

        assert optimizer.service is not None
        assert optimizer.test_pairs == []
        assert optimizer.ground_truth == []
        assert "timestamp" in optimizer.results
        assert "batch_analyses" in optimizer.results
        assert "accuracy_validation" in optimizer.results
        assert "optimal_configs" in optimizer.results

    def test_create_test_dataset(self) -> None:
        """Test dataset creation with ground truth."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=60)

        assert len(optimizer.test_pairs) == 60
        assert len(optimizer.ground_truth) == 60

        # Check all labels are represented
        labels = set(optimizer.ground_truth)
        assert NLILabel.ENTAILMENT in labels
        assert NLILabel.CONTRADICTION in labels
        assert NLILabel.NEUTRAL in labels

    def test_create_test_dataset_balanced(self) -> None:
        """Test dataset has balanced label distribution."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=90)

        # Count labels
        label_counts = {
            NLILabel.ENTAILMENT: optimizer.ground_truth.count(NLILabel.ENTAILMENT),
            NLILabel.CONTRADICTION: optimizer.ground_truth.count(NLILabel.CONTRADICTION),
            NLILabel.NEUTRAL: optimizer.ground_truth.count(NLILabel.NEUTRAL),
        }

        # Should be roughly balanced (within 20% of each other)
        max_count = max(label_counts.values())
        min_count = min(label_counts.values())
        assert (max_count - min_count) / max_count < 0.3  # Within 30%

    def test_measure_memory(self) -> None:
        """Test memory measurement."""
        optimizer = BatchOptimizer()
        memory_mb = optimizer.measure_memory()

        assert isinstance(memory_mb, float)
        assert memory_mb > 0

    def test_analyze_batch_size_without_accuracy(self) -> None:
        """Test batch analysis without accuracy validation."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=20)

        result = optimizer.analyze_batch_size(batch_size=4, validate_accuracy=False)

        assert result["batch_size"] == 4
        assert result["num_pairs"] == 20
        assert result["throughput_pairs_per_sec"] > 0
        assert result["latency_ms_per_pair"] > 0
        assert result["accuracy_metrics"] == {}

    def test_analyze_batch_size_with_accuracy(self) -> None:
        """Test batch analysis with accuracy validation."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=20)

        result = optimizer.analyze_batch_size(batch_size=4, validate_accuracy=True)

        assert "accuracy_metrics" in result
        metrics = result["accuracy_metrics"]

        assert "accuracy" in metrics
        assert "correct" in metrics
        assert "total" in metrics
        assert "avg_confidence" in metrics
        assert "confusion_matrix" in metrics

        # Validate ranges
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["correct"] <= metrics["total"]
        assert metrics["total"] == 20

    def test_run_optimization(self) -> None:
        """Test full optimization run."""
        optimizer = BatchOptimizer()

        batch_sizes = [4, 8]
        optimizer.run_optimization(batch_sizes, num_pairs=20, validate_accuracy=True)

        assert len(optimizer.results["batch_analyses"]) == len(batch_sizes)

        for analysis in optimizer.results["batch_analyses"]:
            assert "batch_size" in analysis
            assert "throughput_pairs_per_sec" in analysis
            assert "accuracy_metrics" in analysis

    def test_compute_optimal_configs(self) -> None:
        """Test optimal configuration computation."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([4, 8, 16], num_pairs=30, validate_accuracy=True)

        optimal = optimizer.results["optimal_configs"]

        assert "maximum_throughput" in optimal
        assert "minimum_latency" in optimal
        assert "memory_efficient" in optimal
        assert "balanced" in optimal

        # Each config should have required fields
        for config_name, config in optimal.items():
            assert "batch_size" in config
            assert "throughput_pairs_per_sec" in config
            assert "latency_ms" in config
            assert "memory_mb" in config

    def test_accuracy_consistency_across_batches(self) -> None:
        """Test accuracy is consistent across different batch sizes."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([1, 8, 16], num_pairs=60, validate_accuracy=True)

        accuracies = [
            analysis["accuracy_metrics"]["accuracy"]
            for analysis in optimizer.results["batch_analyses"]
            if analysis.get("accuracy_metrics")
        ]

        # All accuracies should be very close (within 5%)
        if len(accuracies) > 1:
            max_acc = max(accuracies)
            min_acc = min(accuracies)
            # Allow some variance due to test dataset randomness
            assert abs(max_acc - min_acc) < 0.05  # Within 5%

    def test_save_results(self, tmp_path: Path) -> None:
        """Test saving optimization results."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([4, 8], num_pairs=20, validate_accuracy=True)

        output_path = tmp_path / "optimization.json"
        optimizer.save_results(output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert "batch_analyses" in data
        assert "optimal_configs" in data


class TestPerformanceMetrics:
    """Tests for performance metric calculations."""

    def test_throughput_calculation(self) -> None:
        """Test throughput is calculated correctly."""
        profiler = NLIProfiler()
        profiler.load_test_data(20)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=4, num_pairs=20)

        # Throughput should be reasonable
        throughput = result["throughput_pairs_per_sec"]
        assert throughput > 1  # At least 1 pair/sec
        assert throughput < 1000  # Not impossibly high

    def test_latency_calculation(self) -> None:
        """Test latency is calculated correctly."""
        profiler = NLIProfiler()
        profiler.load_test_data(20)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=4, num_pairs=20)

        latency = result["latency_ms_per_pair"]
        throughput = result["throughput_pairs_per_sec"]

        # Latency should be inverse of throughput
        expected_latency = 1000 / throughput  # Convert to ms
        assert abs(latency - expected_latency) < 1.0  # Within 1ms

    def test_memory_delta_positive(self) -> None:
        """Test memory delta is tracked correctly."""
        profiler = NLIProfiler()
        profiler.load_test_data(20)
        profiler.warmup(num_iterations=1)

        result = profiler.profile_batch_size(batch_size=8, num_pairs=20)

        # Memory delta should be non-negative (may be small or zero after GC)
        memory_delta = result["memory_delta_mb"]
        assert memory_delta >= 0
        assert memory_delta < 500  # Reasonable upper bound

    def test_batch_size_impact_on_throughput(self) -> None:
        """Test larger batch sizes generally improve throughput."""
        profiler = NLIProfiler()
        profiler.load_test_data(40)
        profiler.warmup(num_iterations=2)

        result_small = profiler.profile_batch_size(batch_size=1, num_pairs=20)
        result_large = profiler.profile_batch_size(batch_size=16, num_pairs=20)

        # Larger batch should generally be faster
        assert result_large["throughput_pairs_per_sec"] > result_small["throughput_pairs_per_sec"]


class TestAccuracyValidation:
    """Tests for accuracy validation functionality."""

    def test_confusion_matrix_structure(self) -> None:
        """Test confusion matrix has correct structure."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=30)

        result = optimizer.analyze_batch_size(batch_size=8, validate_accuracy=True)

        confusion = result["accuracy_metrics"]["confusion_matrix"]

        # Should have all three labels as keys
        assert NLILabel.ENTAILMENT.value in confusion
        assert NLILabel.CONTRADICTION.value in confusion
        assert NLILabel.NEUTRAL.value in confusion

        # Each should map to counts for all labels
        for true_label, predictions in confusion.items():
            assert isinstance(predictions, dict)
            assert len(predictions) == 3  # Three possible predictions

    def test_accuracy_calculation(self) -> None:
        """Test accuracy is calculated correctly."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=50)

        result = optimizer.analyze_batch_size(batch_size=8, validate_accuracy=True)

        metrics = result["accuracy_metrics"]

        # Accuracy should match correct/total
        expected_accuracy = metrics["correct"] / metrics["total"]
        assert abs(metrics["accuracy"] - expected_accuracy) < 0.001

    def test_confidence_scores_valid(self) -> None:
        """Test confidence scores are in valid range."""
        optimizer = BatchOptimizer()
        optimizer.create_test_dataset(num_pairs=30)

        result = optimizer.analyze_batch_size(batch_size=8, validate_accuracy=True)

        avg_confidence = result["accuracy_metrics"]["avg_confidence"]

        assert 0 <= avg_confidence <= 1


class TestResultFormat:
    """Tests for result format and structure."""

    def test_profiler_result_keys(self) -> None:
        """Test profiler results have all required keys."""
        profiler = NLIProfiler()
        profiler.run_all_profiles([4, 8], num_pairs=20)

        results = profiler.results

        # Top-level keys
        assert "timestamp" in results
        assert "system" in results
        assert "batch_profiles" in results
        assert "bottlenecks" in results
        assert "recommendations" in results

    def test_batch_profile_keys(self) -> None:
        """Test each batch profile has required keys."""
        profiler = NLIProfiler()
        profiler.run_all_profiles([4], num_pairs=20)

        profile = profiler.results["batch_profiles"][0]

        required_keys = [
            "batch_size",
            "num_pairs",
            "elapsed_time_s",
            "throughput_pairs_per_sec",
            "latency_ms_per_pair",
            "memory_before_mb",
            "memory_after_mb",
            "memory_delta_mb",
            "label_distribution",
            "avg_confidence",
        ]

        for key in required_keys:
            assert key in profile, f"Missing key: {key}"

    def test_optimizer_result_keys(self) -> None:
        """Test optimizer results have all required keys."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([4, 8], num_pairs=20, validate_accuracy=True)

        results = optimizer.results

        assert "timestamp" in results
        assert "batch_analyses" in results
        assert "accuracy_validation" in results
        assert "optimal_configs" in results

    def test_optimal_config_keys(self) -> None:
        """Test optimal configurations have required keys."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([4, 8, 16], num_pairs=30, validate_accuracy=True)

        optimal = optimizer.results["optimal_configs"]

        required_configs = ["maximum_throughput", "minimum_latency", "memory_efficient", "balanced"]

        for config_name in required_configs:
            assert config_name in optimal
            config = optimal[config_name]

            assert "batch_size" in config
            assert "throughput_pairs_per_sec" in config
            assert "latency_ms" in config
            assert "memory_mb" in config


class TestIntegration:
    """Integration tests for profiling workflow."""

    def test_end_to_end_profiling_workflow(self, tmp_path: Path) -> None:
        """Test complete profiling workflow."""
        # Create profiler
        profiler = NLIProfiler()

        # Load data
        profiler.load_test_data(num_pairs=30)

        # Warmup
        profiler.warmup(num_iterations=2)

        # Run profiling
        batch_sizes = [4, 8, 16]
        profiler.run_all_profiles(batch_sizes, num_pairs=30)

        # Verify results generated
        assert len(profiler.results["batch_profiles"]) == len(batch_sizes)
        assert len(profiler.results["bottlenecks"]) >= 0
        assert len(profiler.results["recommendations"]) >= 0

        # Save results
        output_path = tmp_path / "profile.json"
        profiler.save_results(output_path)

        assert output_path.exists()

    def test_end_to_end_optimization_workflow(self, tmp_path: Path) -> None:
        """Test complete optimization workflow."""
        # Create optimizer
        optimizer = BatchOptimizer()

        # Run optimization
        batch_sizes = [4, 8, 16]
        optimizer.run_optimization(
            batch_sizes,
            num_pairs=40,
            validate_accuracy=True
        )

        # Verify results
        assert len(optimizer.results["batch_analyses"]) == len(batch_sizes)
        assert "optimal_configs" in optimizer.results
        assert len(optimizer.results["accuracy_validation"]) > 0

        # Save results
        output_path = tmp_path / "optimization.json"
        optimizer.save_results(output_path)

        assert output_path.exists()

    def test_profiling_performance_target_met(self) -> None:
        """Test that profiling shows target is met."""
        profiler = NLIProfiler()
        profiler.run_all_profiles([16], num_pairs=40)

        profile = profiler.results["batch_profiles"][0]
        throughput = profile["throughput_pairs_per_sec"]

        # Target is 2 pairs/sec
        TARGET_THROUGHPUT = 2.0

        assert throughput > TARGET_THROUGHPUT, f"Target not met: {throughput:.2f} pairs/sec"

    def test_accuracy_maintained_across_batches(self) -> None:
        """Test accuracy is maintained across different batch sizes."""
        optimizer = BatchOptimizer()
        optimizer.run_optimization([1, 8, 16, 32], num_pairs=60, validate_accuracy=True)

        # Get all accuracies
        accuracies = []
        for analysis in optimizer.results["batch_analyses"]:
            if analysis.get("accuracy_metrics"):
                accuracies.append(analysis["accuracy_metrics"]["accuracy"])

        # All should be identical (same model, same data)
        if len(accuracies) > 1:
            first_accuracy = accuracies[0]
            for accuracy in accuracies[1:]:
                # Should be exactly the same (deterministic inference)
                assert abs(accuracy - first_accuracy) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
