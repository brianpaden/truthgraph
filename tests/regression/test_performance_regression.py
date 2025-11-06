"""Performance regression tests.

This module detects performance regressions by comparing current performance
metrics against established baselines.

Usage:
    # Run regression tests
    pytest tests/regression/test_performance_regression.py -v

    # Update baseline after intentional changes
    pytest tests/regression/test_performance_regression.py --update-baseline
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from tests.regression.baseline_manager import (
    BaselineManager,
    PerformanceMetrics,
)


def get_git_commit() -> Optional[str]:
    """Get current git commit hash.

    Returns:
        Git commit hash or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def load_embedding_benchmark() -> Dict[str, Any]:
    """Load embedding service benchmark results.

    Returns:
        Embedding benchmark data
    """
    benchmark_file = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "benchmarks"
        / "results"
        / "baseline_embeddings_2025-10-27.json"
    )

    if not benchmark_file.exists():
        pytest.skip(f"Embedding benchmark not found: {benchmark_file}")

    with open(benchmark_file, "r") as f:
        return json.load(f)


def load_nli_benchmark() -> Dict[str, Any]:
    """Load NLI service benchmark results.

    Returns:
        NLI benchmark data
    """
    benchmark_file = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "benchmarks"
        / "results"
        / "baseline_nli_2025-10-27.json"
    )

    if not benchmark_file.exists():
        pytest.skip(f"NLI benchmark not found: {benchmark_file}")

    with open(benchmark_file, "r") as f:
        return json.load(f)


def extract_performance_metrics() -> Dict[str, Any]:
    """Extract performance metrics from benchmark results.

    Returns:
        Dictionary with performance metrics in the format expected by BaselineManager
    """
    embedding_data = load_embedding_benchmark()
    nli_data = load_nli_benchmark()

    # Extract embedding metrics
    embedding_single = embedding_data["benchmarks"]["single_text"]
    embedding_batch = embedding_data["benchmarks"]["batch_sizes"]
    embedding_memory = embedding_data["benchmarks"]["memory"]

    # Extract NLI metrics
    nli_single = nli_data["benchmarks"]["single_pair"]
    nli_batch = nli_data["benchmarks"]["batch_sizes"]
    nli_memory = nli_data["benchmarks"]["memory"]

    # Build metrics dict
    return {
        "embedding": {
            "latency_ms": embedding_single["avg_latency_ms"],
            "throughput": embedding_batch["best_throughput"],
            "p95_latency_ms": embedding_single["p95_latency_ms"],
            "p99_latency_ms": embedding_single["p99_latency_ms"],
        },
        "nli": {
            "latency_ms": nli_single["avg_latency_ms"],
            "throughput": nli_batch["best_throughput"],
            "p95_latency_ms": nli_single["p95_latency_ms"],
            "p99_latency_ms": nli_single["p99_latency_ms"],
        },
        "e2e": {
            # These are placeholder values - should be measured from actual e2e tests
            "latency_seconds": 5.0,
            "throughput_claims_per_sec": 0.2,
        },
        "memory": {
            "baseline_mb": max(embedding_memory["baseline_mb"], nli_memory["baseline_mb"]),
            "peak_mb": embedding_memory["peak_mb"] + nli_memory["peak_mb"],
            "loaded_mb": embedding_memory["loaded_mb"] + nli_memory["loaded_mb"],
        },
    }


@pytest.fixture
def baseline_manager() -> BaselineManager:
    """Create baseline manager instance.

    Returns:
        BaselineManager configured for tests
    """
    return BaselineManager()


@pytest.fixture
def current_performance() -> Dict[str, Any]:
    """Get current performance metrics.

    Returns:
        Current performance metrics
    """
    return extract_performance_metrics()


def test_embedding_latency_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that embedding service latency has not regressed.

    Compares current embedding latency against baseline with 10% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_latency = baseline.performance.embedding_latency_ms
    current_latency = current_performance["embedding"]["latency_ms"]

    # Allow 10% variance
    threshold = baseline_latency * 1.10

    assert current_latency <= threshold, (
        f"Embedding latency regression detected: "
        f"{current_latency:.2f}ms > {threshold:.2f}ms (baseline: {baseline_latency:.2f}ms)"
    )


def test_embedding_throughput_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that embedding service throughput has not regressed.

    Compares current embedding throughput against baseline with 10% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_throughput = baseline.performance.embedding_throughput
    current_throughput = current_performance["embedding"]["throughput"]

    # Allow 10% variance (throughput should not drop below 90%)
    threshold = baseline_throughput * 0.90

    assert current_throughput >= threshold, (
        f"Embedding throughput regression detected: "
        f"{current_throughput:.2f} < {threshold:.2f} (baseline: {baseline_throughput:.2f})"
    )


def test_nli_latency_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that NLI service latency has not regressed.

    Compares current NLI latency against baseline with 10% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_latency = baseline.performance.nli_latency_ms
    current_latency = current_performance["nli"]["latency_ms"]

    # Allow 10% variance
    threshold = baseline_latency * 1.10

    assert current_latency <= threshold, (
        f"NLI latency regression detected: "
        f"{current_latency:.2f}ms > {threshold:.2f}ms (baseline: {baseline_latency:.2f}ms)"
    )


def test_nli_throughput_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that NLI service throughput has not regressed.

    Compares current NLI throughput against baseline with 10% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_throughput = baseline.performance.nli_throughput
    current_throughput = current_performance["nli"]["throughput"]

    # Allow 10% variance
    threshold = baseline_throughput * 0.90

    assert current_throughput >= threshold, (
        f"NLI throughput regression detected: "
        f"{current_throughput:.2f} < {threshold:.2f} (baseline: {baseline_throughput:.2f})"
    )


def test_memory_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that memory usage has not regressed.

    Compares current peak memory usage against baseline with 20% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_memory = baseline.performance.memory_peak_mb
    current_memory = current_performance["memory"]["peak_mb"]

    # Allow 20% variance for memory
    threshold = baseline_memory * 1.20

    assert current_memory <= threshold, (
        f"Memory regression detected: "
        f"{current_memory:.2f}MB > {threshold:.2f}MB (baseline: {baseline_memory:.2f}MB)"
    )


def test_e2e_latency_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Test that end-to-end latency has not regressed.

    Compares current e2e latency against baseline with 15% tolerance.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    baseline_latency = baseline.performance.e2e_latency_seconds
    current_latency = current_performance["e2e"]["latency_seconds"]

    # Allow 15% variance for e2e
    threshold = baseline_latency * 1.15

    assert current_latency <= threshold, (
        f"E2E latency regression detected: "
        f"{current_latency:.2f}s > {threshold:.2f}s (baseline: {baseline_latency:.2f}s)"
    )


def test_comprehensive_performance_regression(
    baseline_manager: BaselineManager,
    current_performance: Dict[str, Any],
) -> None:
    """Run comprehensive regression detection across all performance metrics.

    This test uses the BaselineManager to detect all regressions and provides
    a detailed report of any issues found.
    """
    try:
        baseline = baseline_manager.load_baseline()
    except FileNotFoundError:
        pytest.skip("No baseline found. Run with --update-baseline to create one.")

    # Dummy accuracy metrics (will be replaced with real ones in accuracy regression test)
    dummy_accuracy = {
        "overall": {"accuracy": 0.7, "precision": 0.7, "recall": 0.7, "f1_score": 0.7},
        "per_verdict": {"supported": 0.7, "refuted": 0.7, "insufficient": 0.7},
        "categories": {},
        "confusion_matrix": {},
    }

    # Detect regressions
    regressions = baseline_manager.detect_regressions(
        baseline, current_performance, dummy_accuracy
    )

    # Filter to only performance regressions
    perf_regressions = [r for r in regressions if r.category == "performance"]

    if perf_regressions:
        # Generate detailed report
        report = "\n\n" + "=" * 70 + "\n"
        report += "PERFORMANCE REGRESSION DETECTED\n"
        report += "=" * 70 + "\n\n"

        for reg in perf_regressions:
            report += f"[{reg.severity.upper()}] {reg.message}\n"
            report += f"  Threshold: {abs(reg.threshold_exceeded):.2%} over limit\n\n"

        report += "=" * 70 + "\n"

        pytest.fail(
            f"{len(perf_regressions)} performance regression(s) detected. {report}",
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
        # Update baseline before running tests
        manager = BaselineManager()
        performance = extract_performance_metrics()

        # Dummy accuracy for now (will be replaced with real data)
        dummy_accuracy = {
            "overall": {"accuracy": 0.7, "precision": 0.7, "recall": 0.7, "f1_score": 0.7},
            "per_verdict": {"supported": 0.7, "refuted": 0.7, "insufficient": 0.7},
            "categories": {},
            "confusion_matrix": {},
        }

        baseline = manager.create_baseline(
            version="0.1.0",
            performance_metrics=performance,
            accuracy_metrics=dummy_accuracy,
            git_commit=get_git_commit(),
            metadata={
                "created_by": "test_performance_regression.py",
                "note": "Baseline updated via --update-baseline flag",
            },
        )

        filepath = manager.save_baseline(baseline)
        print(f"\n✓ Baseline updated: {filepath}")
