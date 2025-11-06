"""Baseline management for regression testing.

This module provides functionality for storing, loading, and comparing
performance and accuracy baselines to detect regressions in TruthGraph.

Usage:
    from tests.regression.baseline_manager import BaselineManager

    manager = BaselineManager()

    # Save new baseline
    baseline = manager.create_baseline(
        performance_metrics={...},
        accuracy_metrics={...}
    )
    manager.save_baseline(baseline)

    # Load and compare
    current = manager.load_baseline()
    regressions = manager.detect_regressions(current, new_metrics)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics for regression testing."""

    # Embedding service metrics
    embedding_latency_ms: float
    embedding_throughput: float
    embedding_p95_latency_ms: float
    embedding_p99_latency_ms: float

    # NLI service metrics
    nli_latency_ms: float
    nli_throughput: float
    nli_p95_latency_ms: float
    nli_p99_latency_ms: float

    # End-to-end pipeline metrics
    e2e_latency_seconds: float
    e2e_throughput_claims_per_sec: float

    # Memory metrics
    memory_baseline_mb: float
    memory_peak_mb: float
    memory_loaded_mb: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "embedding": {
                "latency_ms": self.embedding_latency_ms,
                "throughput": self.embedding_throughput,
                "p95_latency_ms": self.embedding_p95_latency_ms,
                "p99_latency_ms": self.embedding_p99_latency_ms,
            },
            "nli": {
                "latency_ms": self.nli_latency_ms,
                "throughput": self.nli_throughput,
                "p95_latency_ms": self.nli_p95_latency_ms,
                "p99_latency_ms": self.nli_p99_latency_ms,
            },
            "e2e": {
                "latency_seconds": self.e2e_latency_seconds,
                "throughput_claims_per_sec": self.e2e_throughput_claims_per_sec,
            },
            "memory": {
                "baseline_mb": self.memory_baseline_mb,
                "peak_mb": self.memory_peak_mb,
                "loaded_mb": self.memory_loaded_mb,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """Create from dictionary."""
        return cls(
            embedding_latency_ms=data["embedding"]["latency_ms"],
            embedding_throughput=data["embedding"]["throughput"],
            embedding_p95_latency_ms=data["embedding"]["p95_latency_ms"],
            embedding_p99_latency_ms=data["embedding"]["p99_latency_ms"],
            nli_latency_ms=data["nli"]["latency_ms"],
            nli_throughput=data["nli"]["throughput"],
            nli_p95_latency_ms=data["nli"]["p95_latency_ms"],
            nli_p99_latency_ms=data["nli"]["p99_latency_ms"],
            e2e_latency_seconds=data["e2e"]["latency_seconds"],
            e2e_throughput_claims_per_sec=data["e2e"]["throughput_claims_per_sec"],
            memory_baseline_mb=data["memory"]["baseline_mb"],
            memory_peak_mb=data["memory"]["peak_mb"],
            memory_loaded_mb=data["memory"]["loaded_mb"],
        )


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for regression testing."""

    overall_accuracy: float
    precision: float
    recall: float
    f1_score: float

    # Per-verdict metrics
    supported_accuracy: float
    refuted_accuracy: float
    insufficient_accuracy: float

    # Category metrics
    category_accuracies: Dict[str, float] = field(default_factory=dict)

    # Confusion matrix
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall": {
                "accuracy": self.overall_accuracy,
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
            },
            "per_verdict": {
                "supported": self.supported_accuracy,
                "refuted": self.refuted_accuracy,
                "insufficient": self.insufficient_accuracy,
            },
            "categories": self.category_accuracies,
            "confusion_matrix": self.confusion_matrix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccuracyMetrics":
        """Create from dictionary."""
        return cls(
            overall_accuracy=data["overall"]["accuracy"],
            precision=data["overall"]["precision"],
            recall=data["overall"]["recall"],
            f1_score=data["overall"]["f1_score"],
            supported_accuracy=data["per_verdict"]["supported"],
            refuted_accuracy=data["per_verdict"]["refuted"],
            insufficient_accuracy=data["per_verdict"]["insufficient"],
            category_accuracies=data.get("categories", {}),
            confusion_matrix=data.get("confusion_matrix", {}),
        )


@dataclass
class Baseline:
    """Complete baseline data for regression testing."""

    version: str
    timestamp: datetime
    git_commit: Optional[str]
    performance: PerformanceMetrics
    accuracy: AccuracyMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "git_commit": self.git_commit,
            "performance": self.performance.to_dict(),
            "accuracy": self.accuracy.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baseline":
        """Create from dictionary."""
        return cls(
            version=data["version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            git_commit=data.get("git_commit"),
            performance=PerformanceMetrics.from_dict(data["performance"]),
            accuracy=AccuracyMetrics.from_dict(data["accuracy"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Regression:
    """Detected regression information."""

    metric_name: str
    category: str  # 'performance' or 'accuracy'
    baseline_value: float
    current_value: float
    delta: float
    delta_percent: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    threshold_exceeded: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "category": self.category,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "severity": self.severity,
            "threshold_exceeded": self.threshold_exceeded,
            "message": self.message,
        }


class BaselineManager:
    """Manages baselines for regression testing."""

    def __init__(self, baseline_dir: Optional[Path] = None):
        """Initialize baseline manager.

        Args:
            baseline_dir: Directory for storing baselines (default: tests/regression/baselines)
        """
        if baseline_dir is None:
            baseline_dir = Path(__file__).parent / "baselines"

        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        # Regression thresholds
        self.performance_thresholds = {
            "embedding_latency_ms": 0.10,  # 10% increase allowed
            "embedding_throughput": -0.10,  # 10% decrease allowed
            "nli_latency_ms": 0.10,
            "nli_throughput": -0.10,
            "e2e_latency_seconds": 0.15,  # 15% increase allowed
            "e2e_throughput_claims_per_sec": -0.10,
            "memory_peak_mb": 0.20,  # 20% increase allowed
        }

        self.accuracy_thresholds = {
            "overall_accuracy": -0.02,  # 2% drop not allowed
            "precision": -0.03,
            "recall": -0.03,
            "f1_score": -0.03,
            "supported_accuracy": -0.05,
            "refuted_accuracy": -0.05,
            "insufficient_accuracy": -0.05,
        }

    def save_baseline(self, baseline: Baseline, name: Optional[str] = None) -> Path:
        """Save a baseline to disk.

        Args:
            baseline: Baseline to save
            name: Optional custom name (default: baseline_YYYY-MM-DD)

        Returns:
            Path to saved baseline file
        """
        if name is None:
            name = f"baseline_{baseline.timestamp.strftime('%Y-%m-%d')}"

        if not name.endswith(".json"):
            name += ".json"

        filepath = self.baseline_dir / name

        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f, indent=2)

        return filepath

    def load_baseline(self, name: Optional[str] = None) -> Baseline:
        """Load a baseline from disk.

        Args:
            name: Baseline name or path. If None, loads most recent baseline.

        Returns:
            Loaded baseline

        Raises:
            FileNotFoundError: If baseline not found
        """
        if name is None:
            # Load most recent baseline
            baselines = sorted(self.baseline_dir.glob("baseline_*.json"), reverse=True)
            if not baselines:
                raise FileNotFoundError("No baselines found")
            filepath = baselines[0]
        else:
            if not name.endswith(".json"):
                name += ".json"
            filepath = self.baseline_dir / name

        if not filepath.exists():
            raise FileNotFoundError(f"Baseline not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        return Baseline.from_dict(data)

    def list_baselines(self) -> List[str]:
        """List all available baselines.

        Returns:
            List of baseline names (without .json extension)
        """
        baselines = sorted(self.baseline_dir.glob("baseline_*.json"), reverse=True)
        return [b.stem for b in baselines]

    def create_baseline(
        self,
        version: str,
        performance_metrics: Dict[str, Any],
        accuracy_metrics: Dict[str, Any],
        git_commit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Baseline:
        """Create a new baseline from metrics.

        Args:
            version: Version string (e.g., "0.1.0")
            performance_metrics: Performance metrics dict
            accuracy_metrics: Accuracy metrics dict
            git_commit: Git commit hash
            metadata: Additional metadata

        Returns:
            Created baseline
        """
        performance = PerformanceMetrics.from_dict(performance_metrics)
        accuracy = AccuracyMetrics.from_dict(accuracy_metrics)

        return Baseline(
            version=version,
            timestamp=datetime.now(),
            git_commit=git_commit,
            performance=performance,
            accuracy=accuracy,
            metadata=metadata or {},
        )

    def detect_regressions(
        self,
        baseline: Baseline,
        current_performance: Dict[str, Any],
        current_accuracy: Dict[str, Any],
    ) -> List[Regression]:
        """Detect regressions by comparing current metrics to baseline.

        Args:
            baseline: Baseline to compare against
            current_performance: Current performance metrics
            current_accuracy: Current accuracy metrics

        Returns:
            List of detected regressions
        """
        regressions: List[Regression] = []

        # Check performance regressions
        regressions.extend(
            self._check_performance_regressions(baseline.performance, current_performance)
        )

        # Check accuracy regressions
        regressions.extend(self._check_accuracy_regressions(baseline.accuracy, current_accuracy))

        return regressions

    def _check_performance_regressions(
        self, baseline: PerformanceMetrics, current: Dict[str, Any]
    ) -> List[Regression]:
        """Check for performance regressions."""
        regressions: List[Regression] = []
        current_perf = PerformanceMetrics.from_dict(current)

        # Check each metric
        metrics_to_check = [
            ("embedding_latency_ms", current_perf.embedding_latency_ms, True),
            ("embedding_throughput", current_perf.embedding_throughput, False),
            ("nli_latency_ms", current_perf.nli_latency_ms, True),
            ("nli_throughput", current_perf.nli_throughput, False),
            ("e2e_latency_seconds", current_perf.e2e_latency_seconds, True),
            (
                "e2e_throughput_claims_per_sec",
                current_perf.e2e_throughput_claims_per_sec,
                False,
            ),
            ("memory_peak_mb", current_perf.memory_peak_mb, True),
        ]

        for metric_name, current_value, higher_is_worse in metrics_to_check:
            baseline_value = getattr(baseline, metric_name)
            threshold = self.performance_thresholds.get(metric_name, 0.10)

            if higher_is_worse:
                # For latency and memory, higher is worse
                delta_percent = (current_value - baseline_value) / baseline_value
                if delta_percent > threshold:
                    regression = self._create_regression(
                        metric_name,
                        "performance",
                        baseline_value,
                        current_value,
                        delta_percent,
                        threshold,
                    )
                    regressions.append(regression)
            else:
                # For throughput, lower is worse
                delta_percent = (current_value - baseline_value) / baseline_value
                if delta_percent < threshold:
                    regression = self._create_regression(
                        metric_name,
                        "performance",
                        baseline_value,
                        current_value,
                        delta_percent,
                        threshold,
                    )
                    regressions.append(regression)

        return regressions

    def _check_accuracy_regressions(
        self, baseline: AccuracyMetrics, current: Dict[str, Any]
    ) -> List[Regression]:
        """Check for accuracy regressions."""
        regressions: List[Regression] = []
        current_acc = AccuracyMetrics.from_dict(current)

        # Check each metric (for accuracy, lower is always worse)
        metrics_to_check = [
            ("overall_accuracy", current_acc.overall_accuracy),
            ("precision", current_acc.precision),
            ("recall", current_acc.recall),
            ("f1_score", current_acc.f1_score),
            ("supported_accuracy", current_acc.supported_accuracy),
            ("refuted_accuracy", current_acc.refuted_accuracy),
            ("insufficient_accuracy", current_acc.insufficient_accuracy),
        ]

        for metric_name, current_value in metrics_to_check:
            baseline_value = getattr(baseline, metric_name)
            threshold = self.accuracy_thresholds.get(metric_name, -0.02)

            delta_percent = (current_value - baseline_value) / baseline_value
            if delta_percent < threshold:
                regression = self._create_regression(
                    metric_name,
                    "accuracy",
                    baseline_value,
                    current_value,
                    delta_percent,
                    threshold,
                )
                regressions.append(regression)

        return regressions

    def _create_regression(
        self,
        metric_name: str,
        category: str,
        baseline_value: float,
        current_value: float,
        delta_percent: float,
        threshold: float,
    ) -> Regression:
        """Create a regression object with severity assessment."""
        delta = current_value - baseline_value

        # Determine severity based on how much threshold was exceeded
        threshold_exceeded = abs(delta_percent) - abs(threshold)

        if threshold_exceeded >= 0.20:  # 20% over threshold
            severity = "critical"
        elif threshold_exceeded >= 0.10:  # 10% over threshold
            severity = "high"
        elif threshold_exceeded >= 0.05:  # 5% over threshold
            severity = "medium"
        else:
            severity = "low"

        # Create message
        if category == "performance":
            if "throughput" in metric_name:
                message = (
                    f"{metric_name} decreased by {abs(delta_percent):.2%} "
                    f"(from {baseline_value:.2f} to {current_value:.2f})"
                )
            else:
                message = (
                    f"{metric_name} increased by {delta_percent:.2%} "
                    f"(from {baseline_value:.2f} to {current_value:.2f})"
                )
        else:  # accuracy
            message = (
                f"{metric_name} decreased by {abs(delta_percent):.2%} "
                f"(from {baseline_value:.2%} to {current_value:.2%})"
            )

        return Regression(
            metric_name=metric_name,
            category=category,
            baseline_value=baseline_value,
            current_value=current_value,
            delta=delta,
            delta_percent=delta_percent,
            severity=severity,
            threshold_exceeded=threshold_exceeded,
            message=message,
        )

    def save_history_entry(self, baseline: Baseline, regressions: List[Regression]) -> None:
        """Save a history entry for tracking baseline evolution.

        Args:
            baseline: The baseline being compared
            regressions: List of detected regressions
        """
        history_file = self.baseline_dir / "baseline_history.csv"

        # Create header if file doesn't exist
        if not history_file.exists():
            with open(history_file, "w") as f:
                f.write(
                    "timestamp,version,git_commit,overall_accuracy,e2e_latency_seconds,"
                    "embedding_throughput,nli_throughput,memory_peak_mb,regression_count,"
                    "critical_regressions,high_regressions\n"
                )

        # Count regressions by severity
        critical = sum(1 for r in regressions if r.severity == "critical")
        high = sum(1 for r in regressions if r.severity == "high")

        # Append entry
        with open(history_file, "a") as f:
            f.write(
                f"{baseline.timestamp.isoformat()},"
                f"{baseline.version},"
                f"{baseline.git_commit or 'unknown'},"
                f"{baseline.accuracy.overall_accuracy:.4f},"
                f"{baseline.performance.e2e_latency_seconds:.2f},"
                f"{baseline.performance.embedding_throughput:.2f},"
                f"{baseline.performance.nli_throughput:.2f},"
                f"{baseline.performance.memory_peak_mb:.2f},"
                f"{len(regressions)},"
                f"{critical},"
                f"{high}\n"
            )
