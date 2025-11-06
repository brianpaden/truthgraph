"""Tests for baseline manager functionality.

This module tests the baseline management system including data models,
persistence, and regression detection logic.

Usage:
    pytest tests/regression/test_baseline_manager.py -v
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from tests.regression.baseline_manager import (
    AccuracyMetrics,
    Baseline,
    BaselineManager,
    PerformanceMetrics,
    Regression,
)


@pytest.fixture
def temp_baseline_dir():
    """Create temporary directory for baselines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def baseline_manager(temp_baseline_dir):
    """Create baseline manager with temporary directory."""
    return BaselineManager(baseline_dir=temp_baseline_dir)


@pytest.fixture
def sample_performance_metrics():
    """Create sample performance metrics."""
    return {
        "embedding": {
            "latency_ms": 10.0,
            "throughput": 500.0,
            "p95_latency_ms": 15.0,
            "p99_latency_ms": 20.0,
        },
        "nli": {
            "latency_ms": 50.0,
            "throughput": 20.0,
            "p95_latency_ms": 60.0,
            "p99_latency_ms": 70.0,
        },
        "e2e": {
            "latency_seconds": 5.0,
            "throughput_claims_per_sec": 0.2,
        },
        "memory": {
            "baseline_mb": 500.0,
            "peak_mb": 1000.0,
            "loaded_mb": 800.0,
        },
    }


@pytest.fixture
def sample_accuracy_metrics():
    """Create sample accuracy metrics."""
    return {
        "overall": {
            "accuracy": 0.75,
            "precision": 0.76,
            "recall": 0.74,
            "f1_score": 0.75,
        },
        "per_verdict": {
            "supported": 0.80,
            "refuted": 0.70,
            "insufficient": 0.75,
        },
        "categories": {
            "politics": 0.72,
            "science": 0.78,
            "health": 0.75,
        },
        "confusion_matrix": {
            "SUPPORTED": {"SUPPORTED": 8, "REFUTED": 1, "INSUFFICIENT": 1},
            "REFUTED": {"SUPPORTED": 1, "REFUTED": 7, "INSUFFICIENT": 2},
            "INSUFFICIENT": {"SUPPORTED": 0, "REFUTED": 1, "INSUFFICIENT": 4},
        },
    }


@pytest.fixture
def sample_baseline(baseline_manager, sample_performance_metrics, sample_accuracy_metrics):
    """Create sample baseline."""
    return baseline_manager.create_baseline(
        version="0.1.0",
        performance_metrics=sample_performance_metrics,
        accuracy_metrics=sample_accuracy_metrics,
        git_commit="abc123",
        metadata={"test": True},
    )


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics data class."""

    def test_to_dict(self, sample_performance_metrics):
        """Test converting performance metrics to dictionary."""
        metrics = PerformanceMetrics.from_dict(sample_performance_metrics)
        result = metrics.to_dict()

        assert result["embedding"]["latency_ms"] == 10.0
        assert result["nli"]["throughput"] == 20.0
        assert result["memory"]["peak_mb"] == 1000.0

    def test_from_dict(self, sample_performance_metrics):
        """Test creating performance metrics from dictionary."""
        metrics = PerformanceMetrics.from_dict(sample_performance_metrics)

        assert metrics.embedding_latency_ms == 10.0
        assert metrics.nli_throughput == 20.0
        assert metrics.memory_peak_mb == 1000.0

    def test_roundtrip(self, sample_performance_metrics):
        """Test that dict -> object -> dict preserves data."""
        metrics = PerformanceMetrics.from_dict(sample_performance_metrics)
        result = metrics.to_dict()

        assert result == sample_performance_metrics


class TestAccuracyMetrics:
    """Tests for AccuracyMetrics data class."""

    def test_to_dict(self, sample_accuracy_metrics):
        """Test converting accuracy metrics to dictionary."""
        metrics = AccuracyMetrics.from_dict(sample_accuracy_metrics)
        result = metrics.to_dict()

        assert result["overall"]["accuracy"] == 0.75
        assert result["per_verdict"]["supported"] == 0.80
        assert "politics" in result["categories"]

    def test_from_dict(self, sample_accuracy_metrics):
        """Test creating accuracy metrics from dictionary."""
        metrics = AccuracyMetrics.from_dict(sample_accuracy_metrics)

        assert metrics.overall_accuracy == 0.75
        assert metrics.supported_accuracy == 0.80
        assert metrics.category_accuracies["politics"] == 0.72

    def test_roundtrip(self, sample_accuracy_metrics):
        """Test that dict -> object -> dict preserves data."""
        metrics = AccuracyMetrics.from_dict(sample_accuracy_metrics)
        result = metrics.to_dict()

        # Note: roundtrip should preserve structure
        assert result["overall"] == sample_accuracy_metrics["overall"]
        assert result["per_verdict"] == sample_accuracy_metrics["per_verdict"]


class TestBaseline:
    """Tests for Baseline data class."""

    def test_to_dict(self, sample_baseline):
        """Test converting baseline to dictionary."""
        result = sample_baseline.to_dict()

        assert result["version"] == "0.1.0"
        assert result["git_commit"] == "abc123"
        assert "performance" in result
        assert "accuracy" in result
        assert result["metadata"]["test"] is True

    def test_from_dict(self, sample_baseline):
        """Test creating baseline from dictionary."""
        data = sample_baseline.to_dict()
        baseline = Baseline.from_dict(data)

        assert baseline.version == "0.1.0"
        assert baseline.git_commit == "abc123"
        assert baseline.performance.embedding_latency_ms == 10.0
        assert baseline.accuracy.overall_accuracy == 0.75

    def test_roundtrip(self, sample_baseline):
        """Test that dict -> object -> dict preserves data."""
        data = sample_baseline.to_dict()
        baseline = Baseline.from_dict(data)
        result = baseline.to_dict()

        assert result["version"] == data["version"]
        assert result["git_commit"] == data["git_commit"]


class TestBaselineManager:
    """Tests for BaselineManager functionality."""

    def test_save_baseline(self, baseline_manager, sample_baseline):
        """Test saving baseline to disk."""
        filepath = baseline_manager.save_baseline(sample_baseline)

        assert filepath.exists()
        assert filepath.suffix == ".json"

        # Verify content
        with open(filepath, "r") as f:
            data = json.load(f)

        assert data["version"] == "0.1.0"

    def test_load_baseline(self, baseline_manager, sample_baseline):
        """Test loading baseline from disk."""
        # Save baseline first
        baseline_manager.save_baseline(sample_baseline, name="test_baseline")

        # Load it back
        loaded = baseline_manager.load_baseline("test_baseline")

        assert loaded.version == sample_baseline.version
        assert loaded.git_commit == sample_baseline.git_commit

    def test_load_most_recent_baseline(self, baseline_manager, sample_baseline):
        """Test loading most recent baseline when no name specified."""
        # Save two baselines
        baseline_manager.save_baseline(sample_baseline, name="baseline_2025-01-01")
        baseline_manager.save_baseline(sample_baseline, name="baseline_2025-01-02")

        # Load without name should get most recent
        loaded = baseline_manager.load_baseline()

        assert loaded is not None

    def test_load_baseline_not_found(self, baseline_manager):
        """Test loading non-existent baseline raises error."""
        with pytest.raises(FileNotFoundError):
            baseline_manager.load_baseline("nonexistent")

    def test_list_baselines(self, baseline_manager, sample_baseline):
        """Test listing all baselines."""
        # Save multiple baselines
        baseline_manager.save_baseline(sample_baseline, name="baseline_2025-01-01")
        baseline_manager.save_baseline(sample_baseline, name="baseline_2025-01-02")

        baselines = baseline_manager.list_baselines()

        assert len(baselines) == 2
        assert "baseline_2025-01-02" in baselines
        assert "baseline_2025-01-01" in baselines

    def test_create_baseline(
        self, baseline_manager, sample_performance_metrics, sample_accuracy_metrics
    ):
        """Test creating baseline from metrics."""
        baseline = baseline_manager.create_baseline(
            version="0.2.0",
            performance_metrics=sample_performance_metrics,
            accuracy_metrics=sample_accuracy_metrics,
            git_commit="def456",
        )

        assert baseline.version == "0.2.0"
        assert baseline.git_commit == "def456"
        assert baseline.performance.embedding_latency_ms == 10.0
        assert baseline.accuracy.overall_accuracy == 0.75

    def test_detect_no_regressions(
        self,
        baseline_manager,
        sample_baseline,
        sample_performance_metrics,
        sample_accuracy_metrics,
    ):
        """Test that no regressions are detected when metrics are identical."""
        regressions = baseline_manager.detect_regressions(
            sample_baseline,
            sample_performance_metrics,
            sample_accuracy_metrics,
        )

        assert len(regressions) == 0

    def test_detect_performance_regression_latency(
        self,
        baseline_manager,
        sample_baseline,
        sample_performance_metrics,
        sample_accuracy_metrics,
    ):
        """Test detecting performance regression in latency."""
        # Increase latency by 20% (exceeds 10% threshold)
        degraded_performance = sample_performance_metrics.copy()
        degraded_performance["embedding"]["latency_ms"] = 12.5  # 25% increase

        regressions = baseline_manager.detect_regressions(
            sample_baseline,
            degraded_performance,
            sample_accuracy_metrics,
        )

        perf_regressions = [r for r in regressions if r.category == "performance"]
        assert len(perf_regressions) > 0

        # Find embedding latency regression
        embedding_reg = next(
            (r for r in perf_regressions if r.metric_name == "embedding_latency_ms"),
            None,
        )
        assert embedding_reg is not None
        assert embedding_reg.current_value > embedding_reg.baseline_value

    def test_detect_performance_regression_throughput(
        self,
        baseline_manager,
        sample_baseline,
        sample_performance_metrics,
        sample_accuracy_metrics,
    ):
        """Test detecting performance regression in throughput."""
        # Decrease throughput by 20% (exceeds 10% threshold)
        degraded_performance = sample_performance_metrics.copy()
        degraded_performance["embedding"]["throughput"] = 400.0  # 20% decrease

        regressions = baseline_manager.detect_regressions(
            sample_baseline,
            degraded_performance,
            sample_accuracy_metrics,
        )

        perf_regressions = [r for r in regressions if r.category == "performance"]
        assert len(perf_regressions) > 0

        # Find embedding throughput regression
        throughput_reg = next(
            (r for r in perf_regressions if r.metric_name == "embedding_throughput"),
            None,
        )
        assert throughput_reg is not None
        assert throughput_reg.current_value < throughput_reg.baseline_value

    def test_detect_accuracy_regression(
        self,
        baseline_manager,
        sample_baseline,
        sample_performance_metrics,
        sample_accuracy_metrics,
    ):
        """Test detecting accuracy regression."""
        # Decrease accuracy by 5% (exceeds 2% threshold)
        degraded_accuracy = sample_accuracy_metrics.copy()
        degraded_accuracy["overall"]["accuracy"] = 0.70  # 5% decrease

        regressions = baseline_manager.detect_regressions(
            sample_baseline,
            sample_performance_metrics,
            degraded_accuracy,
        )

        acc_regressions = [r for r in regressions if r.category == "accuracy"]
        assert len(acc_regressions) > 0

        # Find overall accuracy regression
        acc_reg = next(
            (r for r in acc_regressions if r.metric_name == "overall_accuracy"),
            None,
        )
        assert acc_reg is not None
        assert acc_reg.current_value < acc_reg.baseline_value

    def test_regression_severity_levels(
        self,
        baseline_manager,
        sample_baseline,
        sample_performance_metrics,
        sample_accuracy_metrics,
    ):
        """Test that regression severity is correctly calculated."""
        # Create critical regression (30% increase in latency)
        critical_performance = sample_performance_metrics.copy()
        critical_performance["embedding"]["latency_ms"] = 13.0  # 30% increase

        regressions = baseline_manager.detect_regressions(
            sample_baseline,
            critical_performance,
            sample_accuracy_metrics,
        )

        # Should have at least one high or critical severity regression
        severities = [r.severity for r in regressions]
        assert "high" in severities or "critical" in severities

    def test_save_history_entry(
        self, baseline_manager, sample_baseline, temp_baseline_dir
    ):
        """Test saving history entry."""
        baseline_manager.save_history_entry(sample_baseline, [])

        history_file = temp_baseline_dir / "baseline_history.csv"
        assert history_file.exists()

        # Verify content
        with open(history_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2  # Header + 1 entry
        assert "timestamp" in lines[0]
        assert "0.1.0" in lines[1]


class TestRegression:
    """Tests for Regression data class."""

    def test_to_dict(self):
        """Test converting regression to dictionary."""
        regression = Regression(
            metric_name="embedding_latency_ms",
            category="performance",
            baseline_value=10.0,
            current_value=12.0,
            delta=2.0,
            delta_percent=0.20,
            severity="medium",
            threshold_exceeded=0.10,
            message="Latency increased by 20%",
        )

        result = regression.to_dict()

        assert result["metric_name"] == "embedding_latency_ms"
        assert result["severity"] == "medium"
        assert result["delta_percent"] == 0.20
