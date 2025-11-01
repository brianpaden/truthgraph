"""Accuracy testing framework for TruthGraph fact verification pipeline.

This package provides comprehensive tools for measuring, tracking, and reporting
on the accuracy of the fact verification system.

Main Components:
- metrics.py: Calculate precision, recall, F1, accuracy
- accuracy_framework.py: Framework for evaluation and reporting
- reporters.py: Generate reports in HTML, JSON, and text formats

Usage:
    from tests.accuracy import AccuracyFramework, Reporter

    # Evaluate
    framework = AccuracyFramework()
    results = framework.evaluate(predictions, expected_verdicts)

    # Report
    reporter = Reporter()
    reporter.generate_html_report(results)
"""

from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.metrics import AccuracyMetrics
from tests.accuracy.reporters import Reporter

__all__ = [
    "AccuracyMetrics",
    "AccuracyFramework",
    "Reporter",
]

__version__ = "1.0.0"
__author__ = "TruthGraph Team"
