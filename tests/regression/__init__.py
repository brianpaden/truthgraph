"""Regression testing framework for TruthGraph.

This package provides comprehensive regression detection for both performance
and accuracy metrics. It includes baseline management, automated regression
detection, and CI/CD integration.

Modules:
    baseline_manager: Core baseline management and regression detection
    test_performance_regression: Performance regression tests
    test_accuracy_regression: Accuracy regression tests
    test_baseline_manager: Unit tests for baseline manager

Usage:
    # Run all regression tests
    pytest tests/regression/ -v

    # Update baseline
    python scripts/update_baseline.py

    # Run only performance tests
    pytest tests/regression/test_performance_regression.py -v

    # Run only accuracy tests
    pytest tests/regression/test_accuracy_regression.py -v
"""

from tests.regression.baseline_manager import (
    AccuracyMetrics,
    Baseline,
    BaselineManager,
    PerformanceMetrics,
    Regression,
)

__all__ = [
    "BaselineManager",
    "Baseline",
    "PerformanceMetrics",
    "AccuracyMetrics",
    "Regression",
]
