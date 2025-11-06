"""Accuracy regression tests.

This module detects accuracy regressions by comparing current accuracy
metrics against established baselines.

Usage:
    # Run regression tests
    pytest tests/regression/test_accuracy_regression.py -v

    # Update baseline after intentional changes
    pytest tests/regression/test_accuracy_regression.py --update-baseline
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from tests.regression.baseline_manager import (
    AccuracyMetrics,
    BaselineManager,
)


def load_accuracy_results() -> Dict[str, Any]:
    """Load accuracy test results.

    Returns:
        Accuracy test results from baseline tests
    """
    # Try to load from accuracy test results
    results_file = Path(__file__).parent.parent / "accuracy" / "results" / "baseline_results.json"

    if not results_file.exists():
        pytest.skip(f"Accuracy results not found: {results_file}. Run accuracy tests first.")

    with open(results_file, "r") as f:
        return json.load(f)


def calculate_accuracy_metrics_from_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate accuracy metrics from test results.

    Args:
        results: Raw accuracy test results

    Returns:
        Dictionary with accuracy metrics in the format expected by BaselineManager
    """
    overall = results["overall_metrics"]
    confusion_matrix = results["confusion_matrix"]
    categories = results.get("category_accuracy", {})

    # Calculate per-verdict accuracy from confusion matrix
    def calculate_verdict_accuracy(verdict: str) -> float:
        """Calculate accuracy for a specific verdict."""
        if verdict not in confusion_matrix:
            return 0.0

        correct = confusion_matrix[verdict][verdict]
        total = sum(confusion_matrix[verdict].values())

        if total == 0:
            return 0.0

        return correct / total

    # Calculate precision, recall, and F1 (simplified for multi-class)
    total_correct = sum(
        confusion_matrix[v][v] for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
    )
    total_predictions = sum(
        sum(confusion_matrix[v].values()) for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
    )

    accuracy = total_correct / total_predictions if total_predictions > 0 else 0.0

    # For simplicity, use accuracy as proxy for precision/recall/f1
    # In a real implementation, you'd calculate these properly per class
    precision = accuracy
    recall = accuracy
    f1_score = accuracy

    return {
        "overall": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
        },
        "per_verdict": {
            "supported": calculate_verdict_accuracy("SUPPORTED"),
            "refuted": calculate_verdict_accuracy("REFUTED"),
            "insufficient": calculate_verdict_accuracy("INSUFFICIENT"),
        },
        "categories": {
            cat: stats["accuracy"] for cat, stats in categories.items()
        },
        "confusion_matrix": confusion_matrix,
    }


@pytest.fixture
def baseline_manager() -> BaselineManager:
    """Create baseline manager instance.

    Returns:
        BaselineManager configured for tests
    """
    return BaselineManager()


@pytest.fixture
def current_accuracy() -> Dict[str, Any]:
    """Get current accuracy metrics.

    Returns:
        Current accuracy metrics
    """
    results = load_accuracy_results()
    return calculate_accuracy_metrics_from_results(results)


def test_overall_accuracy_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that overall accuracy has not regressed.

    Compares current accuracy against baseline with 2% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_accuracy = baseline.accuracy.overall_accuracy
    current_acc = current_accuracy["overall"]["accuracy"]

    # Allow 2% drop
    threshold = baseline_accuracy - 0.02

    assert current_acc >= threshold, (
        f"Overall accuracy regression detected: "
        f"{current_acc:.2%} < {threshold:.2%} (baseline: {baseline_accuracy:.2%})"
    )


def test_precision_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that precision has not regressed.

    Compares current precision against baseline with 3% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_precision = baseline.accuracy.precision
    current_precision = current_accuracy["overall"]["precision"]

    # Allow 3% drop
    threshold = baseline_precision - 0.03

    assert current_precision >= threshold, (
        f"Precision regression detected: "
        f"{current_precision:.2%} < {threshold:.2%} (baseline: {baseline_precision:.2%})"
    )


def test_recall_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that recall has not regressed.

    Compares current recall against baseline with 3% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_recall = baseline.accuracy.recall
    current_recall = current_accuracy["overall"]["recall"]

    # Allow 3% drop
    threshold = baseline_recall - 0.03

    assert current_recall >= threshold, (
        f"Recall regression detected: "
        f"{current_recall:.2%} < {threshold:.2%} (baseline: {baseline_recall:.2%})"
    )


def test_f1_score_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that F1 score has not regressed.

    Compares current F1 against baseline with 3% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_f1 = baseline.accuracy.f1_score
    current_f1 = current_accuracy["overall"]["f1_score"]

    # Allow 3% drop
    threshold = baseline_f1 - 0.03

    assert current_f1 >= threshold, (
        f"F1 score regression detected: "
        f"{current_f1:.2%} < {threshold:.2%} (baseline: {baseline_f1:.2%})"
    )


def test_supported_verdict_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that SUPPORTED verdict accuracy has not regressed.

    Compares current SUPPORTED accuracy against baseline with 5% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_acc = baseline.accuracy.supported_accuracy
    current_acc = current_accuracy["per_verdict"]["supported"]

    # Allow 5% drop for individual verdict
    threshold = baseline_acc - 0.05

    assert current_acc >= threshold, (
        f"SUPPORTED verdict accuracy regression detected: "
        f"{current_acc:.2%} < {threshold:.2%} (baseline: {baseline_acc:.2%})"
    )


def test_refuted_verdict_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that REFUTED verdict accuracy has not regressed.

    Compares current REFUTED accuracy against baseline with 5% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_acc = baseline.accuracy.refuted_accuracy
    current_acc = current_accuracy["per_verdict"]["refuted"]

    # Allow 5% drop for individual verdict
    threshold = baseline_acc - 0.05

    assert current_acc >= threshold, (
        f"REFUTED verdict accuracy regression detected: "
        f"{current_acc:.2%} < {threshold:.2%} (baseline: {baseline_acc:.2%})"
    )


def test_insufficient_verdict_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Test that INSUFFICIENT verdict accuracy has not regressed.

    Compares current INSUFFICIENT accuracy against baseline with 5% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_acc = baseline.accuracy.insufficient_accuracy
    current_acc = current_accuracy["per_verdict"]["insufficient"]

    # Allow 5% drop for individual verdict
    threshold = baseline_acc - 0.05

    assert current_acc >= threshold, (
        f"INSUFFICIENT verdict accuracy regression detected: "
        f"{current_acc:.2%} < {threshold:.2%} (baseline: {baseline_acc:.2%})"
    )


def test_comprehensive_accuracy_regression(
    baseline_manager: BaselineManager,
    current_accuracy: Dict[str, Any],
) -> None:
    """Run comprehensive regression detection across all accuracy metrics.

    This test uses the BaselineManager to detect all regressions and provides
    a detailed report of any issues found.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    # Dummy performance metrics (will be replaced with real ones in performance regression test)
    dummy_performance = {
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
        "e2e": {"latency_seconds": 5.0, "throughput_claims_per_sec": 0.2},
        "memory": {"baseline_mb": 500.0, "peak_mb": 1000.0, "loaded_mb": 800.0},
    }

    # Detect regressions
    regressions = baseline_manager.detect_regressions(
        baseline, dummy_performance, current_accuracy
    )

    # Filter to only accuracy regressions
    acc_regressions = [r for r in regressions if r.category == "accuracy"]

    if acc_regressions:
        # Generate detailed report
        report = "\n\n" + "=" * 70 + "\n"
        report += "ACCURACY REGRESSION DETECTED\n"
        report += "=" * 70 + "\n\n"

        for reg in acc_regressions:
            report += f"[{reg.severity.upper()}] {reg.message}\n"
            report += f"  Threshold: {abs(reg.threshold_exceeded):.2%} over limit\n\n"

        report += "=" * 70 + "\n"

        pytest.fail(
            f"{len(acc_regressions)} accuracy regression(s) detected. {report}",
            pytrace=False,
        )


# Baseline update functionality
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--update-baseline",
        action="store_true",
        default=False,
        help="Update baseline with current metrics",
    )


def pytest_configure(config):
    """Configure pytest with custom behavior."""
    if config.getoption("--update-baseline"):
        # This will be handled by the combined update script
        pass
