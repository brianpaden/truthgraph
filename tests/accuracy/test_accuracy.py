"""Comprehensive test suite for accuracy testing framework.

Tests all components of the accuracy framework including:
- Metrics calculation
- Framework evaluation and reporting
- Regression detection
- Report generation
"""

import json
from pathlib import Path
from typing import Dict, List

import pytest

from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.metrics import AccuracyMetrics
from tests.accuracy.reporters import Reporter


class TestAccuracyMetrics:
    """Test AccuracyMetrics class."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = AccuracyMetrics()
        assert metrics.predictions == []
        assert metrics.labels == []
        assert metrics.categories == []

    def test_add_prediction(self):
        """Test adding predictions to metrics."""
        metrics = AccuracyMetrics()
        metrics.add_prediction("SUPPORTED", "SUPPORTED", "science")
        metrics.add_prediction("REFUTED", "REFUTED", "history")

        assert len(metrics.predictions) == 2
        assert len(metrics.labels) == 2
        assert len(metrics.categories) == 2

    def test_calculate_accuracy_perfect(self):
        """Test accuracy calculation with perfect predictions."""
        metrics = AccuracyMetrics()
        predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        assert metrics.calculate_accuracy() == 1.0

    def test_calculate_accuracy_partial(self):
        """Test accuracy calculation with partial correct predictions."""
        metrics = AccuracyMetrics()
        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        expected = 2 / 3  # 2 correct out of 3
        assert metrics.calculate_accuracy() == pytest.approx(expected)

    def test_calculate_accuracy_empty(self):
        """Test accuracy calculation with empty data."""
        metrics = AccuracyMetrics()
        assert metrics.calculate_accuracy() == 0.0

    def test_calculate_precision(self):
        """Test precision calculation."""
        metrics = AccuracyMetrics()

        # Create simple test case
        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        precision = metrics.calculate_precision()

        assert isinstance(precision, dict)
        assert all(v in precision for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"])
        assert all(0 <= v <= 1 for v in precision.values())

    def test_calculate_recall(self):
        """Test recall calculation."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        recall = metrics.calculate_recall()

        assert isinstance(recall, dict)
        assert all(v in recall for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"])
        assert all(0 <= v <= 1 for v in recall.values())

    def test_calculate_f1(self):
        """Test F1 score calculation."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        f1 = metrics.calculate_f1()

        assert isinstance(f1, dict)
        assert all(v in f1 for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"])
        assert all(0 <= v <= 1 for v in f1.values())

    def test_calculate_macro_f1(self):
        """Test macro F1 calculation."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        macro_f1 = metrics.calculate_macro_f1()

        assert isinstance(macro_f1, float)
        assert 0 <= macro_f1 <= 1

    def test_calculate_weighted_f1(self):
        """Test weighted F1 calculation."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        weighted_f1 = metrics.calculate_weighted_f1()

        assert isinstance(weighted_f1, float)
        assert 0 <= weighted_f1 <= 1

    def test_generate_confusion_matrix(self):
        """Test confusion matrix generation."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        cm = metrics.generate_confusion_matrix()

        assert isinstance(cm, dict)
        assert "SUPPORTED" in cm
        assert "REFUTED" in cm
        assert "INSUFFICIENT" in cm

        # Check structure
        for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            assert all(v in cm[verdict] for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"])

    def test_get_confusion_matrix_array(self):
        """Test confusion matrix as numpy array."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        cm_array = metrics.get_confusion_matrix_array()

        assert cm_array.shape == (3, 3)
        assert cm_array.sum() == len(predictions)

    def test_per_category_breakdown(self):
        """Test per-category accuracy breakdown."""
        metrics = AccuracyMetrics()

        # Add predictions from different categories
        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]
        categories = ["science", "science", "history", "health"]

        for pred, label, cat in zip(predictions, labels, categories):
            metrics.add_prediction(pred, label, cat)

        breakdown = metrics.per_category_breakdown()

        assert isinstance(breakdown, dict)
        assert "science" in breakdown
        assert "history" in breakdown
        assert "health" in breakdown

        # Check structure of each category
        for category, metrics_dict in breakdown.items():
            assert "accuracy" in metrics_dict
            assert "precision" in metrics_dict
            assert "recall" in metrics_dict
            assert "f1" in metrics_dict
            assert "samples" in metrics_dict

    def test_get_metrics_summary(self):
        """Test comprehensive metrics summary."""
        metrics = AccuracyMetrics()

        predictions = ["SUPPORTED", "SUPPORTED", "REFUTED", "INSUFFICIENT"]
        labels = ["SUPPORTED", "REFUTED", "REFUTED", "INSUFFICIENT"]

        for pred, label in zip(predictions, labels):
            metrics.add_prediction(pred, label)

        summary = metrics.get_metrics_summary()

        assert "total_samples" in summary
        assert "accuracy" in summary
        assert "macro_f1" in summary
        assert "weighted_f1" in summary
        assert "precision" in summary
        assert "recall" in summary
        assert "f1" in summary
        assert "confusion_matrix" in summary
        assert "per_category" in summary

    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = AccuracyMetrics()

        metrics.add_prediction("SUPPORTED", "SUPPORTED", "science")
        assert len(metrics.predictions) == 1

        metrics.reset()

        assert len(metrics.predictions) == 0
        assert len(metrics.labels) == 0
        assert len(metrics.categories) == 0


class TestAccuracyFramework:
    """Test AccuracyFramework class."""

    def test_framework_initialization(self, tmp_path):
        """Test framework initialization."""
        framework = AccuracyFramework(str(tmp_path))
        assert framework.results_dir == tmp_path
        assert tmp_path.exists()

    def test_evaluate_basic(self, tmp_path):
        """Test basic evaluation."""
        framework = AccuracyFramework(str(tmp_path))

        predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        results = framework.evaluate(predictions, verdicts)

        assert "timestamp" in results
        assert "total_samples" in results
        assert "accuracy" in results
        assert "precision" in results
        assert "recall" in results
        assert "f1" in results
        assert "confusion_matrix" in results

        assert results["accuracy"] == 1.0
        assert results["total_samples"] == 3

    def test_evaluate_with_categories(self, tmp_path):
        """Test evaluation with categories."""
        framework = AccuracyFramework(str(tmp_path))

        predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        categories = ["science", "history", "health"]

        results = framework.evaluate(predictions, verdicts, categories)

        assert "per_category" in results
        assert len(results["per_category"]) == 3

    def test_evaluate_length_mismatch(self, tmp_path):
        """Test evaluation with mismatched lengths."""
        framework = AccuracyFramework(str(tmp_path))

        predictions = ["SUPPORTED", "REFUTED"]
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        with pytest.raises(ValueError):
            framework.evaluate(predictions, verdicts)

    def test_detect_regression_positive(self, tmp_path):
        """Test regression detection when regression occurs."""
        framework = AccuracyFramework(str(tmp_path))

        baseline = {"accuracy": 0.85, "macro_f1": 0.82}
        current = {"accuracy": 0.75, "macro_f1": 0.70}

        is_regression, details = framework.detect_regression(current, baseline)

        assert is_regression is True
        assert details["is_regression"] is True

    def test_detect_regression_negative(self, tmp_path):
        """Test regression detection when no regression."""
        framework = AccuracyFramework(str(tmp_path))

        baseline = {"accuracy": 0.75, "macro_f1": 0.70}
        current = {"accuracy": 0.85, "macro_f1": 0.82}

        is_regression, details = framework.detect_regression(current, baseline)

        assert is_regression is False
        assert details["is_regression"] is False

    def test_detect_regression_threshold(self, tmp_path):
        """Test regression detection with custom threshold."""
        framework = AccuracyFramework(str(tmp_path))

        baseline = {"accuracy": 0.85, "macro_f1": 0.82}
        current = {"accuracy": 0.80, "macro_f1": 0.81}

        # Should not regress with 10% threshold
        is_regression, _ = framework.detect_regression(current, baseline, threshold=0.10)
        assert is_regression is False

        # Should regress with 1% threshold
        is_regression, _ = framework.detect_regression(current, baseline, threshold=0.01)
        assert is_regression is True

    def test_track_trend(self, tmp_path):
        """Test trend tracking."""
        framework = AccuracyFramework(str(tmp_path))

        results1 = {
            "timestamp": "2025-01-01T00:00:00",
            "accuracy": 0.70,
            "macro_f1": 0.68,
            "weighted_f1": 0.69,
            "total_samples": 100,
        }

        trend = framework.track_trend(results1, str(tmp_path / "history.json"))

        assert trend["entries"] == 1
        assert trend["current"]["accuracy"] == 0.70

        # Add second result
        results2 = {
            "timestamp": "2025-01-02T00:00:00",
            "accuracy": 0.75,
            "macro_f1": 0.73,
            "weighted_f1": 0.74,
            "total_samples": 100,
        }

        trend = framework.track_trend(results2, str(tmp_path / "history.json"))

        assert trend["entries"] == 2
        assert trend["previous"]["accuracy"] == 0.70
        assert trend["current"]["accuracy"] == 0.75
        assert "improvements" in trend

    def test_save_results_json(self, tmp_path):
        """Test saving results to JSON."""
        framework = AccuracyFramework(str(tmp_path))

        predictions = ["SUPPORTED", "REFUTED"]
        verdicts = ["SUPPORTED", "REFUTED"]
        results = framework.evaluate(predictions, verdicts)

        output_file = str(tmp_path / "results.json")
        saved_path = framework.save_results_json(results, output_file)

        assert Path(saved_path).exists()

        with open(saved_path, "r") as f:
            loaded = json.load(f)

        assert loaded["accuracy"] == 1.0
        assert loaded["total_samples"] == 2

    def test_save_confusion_matrix_csv(self, tmp_path):
        """Test saving confusion matrix to CSV."""
        framework = AccuracyFramework(str(tmp_path))

        predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        framework.evaluate(predictions, verdicts)

        output_file = str(tmp_path / "confusion_matrix.csv")
        saved_path = framework.save_confusion_matrix_csv(output_file)

        assert Path(saved_path).exists()

        with open(saved_path, "r") as f:
            content = f.read()

        assert "Predicted" in content
        assert "SUPPORTED" in content
        assert "REFUTED" in content

    def test_compare_evaluations(self, tmp_path):
        """Test comparing two evaluations."""
        framework = AccuracyFramework(str(tmp_path))

        results1 = {
            "accuracy": 0.70,
            "macro_f1": 0.68,
            "timestamp": "2025-01-01",
        }

        results2 = {
            "accuracy": 0.75,
            "macro_f1": 0.73,
            "timestamp": "2025-01-02",
        }

        comparison = framework.compare_evaluations(results1, results2)

        assert comparison["results1_accuracy"] == 0.70
        assert comparison["results2_accuracy"] == 0.75
        assert comparison["accuracy_delta"] == pytest.approx(0.05)


class TestReporter:
    """Test Reporter class."""

    def test_reporter_initialization(self, tmp_path):
        """Test reporter initialization."""
        reporter = Reporter(str(tmp_path))
        assert reporter.output_dir == tmp_path

    def test_generate_html_report(self, tmp_path):
        """Test HTML report generation."""
        reporter = Reporter(str(tmp_path))

        metrics = {
            "accuracy": 0.85,
            "macro_f1": 0.83,
            "weighted_f1": 0.84,
            "total_samples": 100,
            "timestamp": "2025-01-01T00:00:00",
            "precision": {
                "SUPPORTED": 0.87,
                "REFUTED": 0.82,
                "INSUFFICIENT": 0.84,
            },
            "recall": {
                "SUPPORTED": 0.85,
                "REFUTED": 0.84,
                "INSUFFICIENT": 0.80,
            },
            "f1": {
                "SUPPORTED": 0.86,
                "REFUTED": 0.83,
                "INSUFFICIENT": 0.82,
            },
            "confusion_matrix": {
                "SUPPORTED": {"SUPPORTED": 34, "REFUTED": 3, "INSUFFICIENT": 3},
                "REFUTED": {"SUPPORTED": 2, "REFUTED": 31, "INSUFFICIENT": 2},
                "INSUFFICIENT": {"SUPPORTED": 3, "REFUTED": 4, "INSUFFICIENT": 20},
            },
            "per_category": {},
        }

        output_file = str(tmp_path / "report.html")
        saved_path = reporter.generate_html_report(metrics, output_file)

        assert Path(saved_path).exists()

        with open(saved_path, "r") as f:
            content = f.read()

        assert "<!DOCTYPE html>" in content
        assert "Accuracy Testing Report" in content
        assert "85.0%" in content or "0.85" in content

    def test_generate_json_report(self, tmp_path):
        """Test JSON report generation."""
        reporter = Reporter(str(tmp_path))

        metrics = {
            "accuracy": 0.85,
            "macro_f1": 0.83,
            "total_samples": 100,
        }

        output_file = str(tmp_path / "report.json")
        saved_path = reporter.generate_json_report(metrics, output_file)

        assert Path(saved_path).exists()

        with open(saved_path, "r") as f:
            loaded = json.load(f)

        assert loaded["accuracy"] == 0.85

    def test_generate_summary(self):
        """Test text summary generation."""
        reporter = Reporter()

        metrics = {
            "accuracy": 0.85,
            "macro_f1": 0.83,
            "weighted_f1": 0.84,
            "total_samples": 100,
            "timestamp": "2025-01-01T00:00:00",
            "precision": {
                "SUPPORTED": 0.87,
                "REFUTED": 0.82,
                "INSUFFICIENT": 0.84,
            },
            "recall": {
                "SUPPORTED": 0.85,
                "REFUTED": 0.84,
                "INSUFFICIENT": 0.80,
            },
            "f1": {
                "SUPPORTED": 0.86,
                "REFUTED": 0.83,
                "INSUFFICIENT": 0.82,
            },
            "confusion_matrix": {
                "SUPPORTED": {"SUPPORTED": 34, "REFUTED": 3, "INSUFFICIENT": 3},
                "REFUTED": {"SUPPORTED": 2, "REFUTED": 31, "INSUFFICIENT": 2},
                "INSUFFICIENT": {"SUPPORTED": 3, "REFUTED": 4, "INSUFFICIENT": 20},
            },
            "per_category": {},
        }

        summary = reporter.generate_summary(metrics)

        assert isinstance(summary, str)
        assert "ACCURACY TESTING REPORT" in summary
        assert "85.0%" in summary or "0.85" in summary
        assert "CONFUSION MATRIX" in summary

    def test_save_summary(self, tmp_path):
        """Test saving text summary to file."""
        reporter = Reporter(str(tmp_path))

        metrics = {
            "accuracy": 0.85,
            "macro_f1": 0.83,
            "weighted_f1": 0.84,
            "total_samples": 100,
            "timestamp": "2025-01-01T00:00:00",
            "precision": {
                "SUPPORTED": 0.87,
                "REFUTED": 0.82,
                "INSUFFICIENT": 0.84,
            },
            "recall": {
                "SUPPORTED": 0.85,
                "REFUTED": 0.84,
                "INSUFFICIENT": 0.80,
            },
            "f1": {
                "SUPPORTED": 0.86,
                "REFUTED": 0.83,
                "INSUFFICIENT": 0.82,
            },
            "confusion_matrix": {
                "SUPPORTED": {"SUPPORTED": 34, "REFUTED": 3, "INSUFFICIENT": 3},
                "REFUTED": {"SUPPORTED": 2, "REFUTED": 31, "INSUFFICIENT": 2},
                "INSUFFICIENT": {"SUPPORTED": 3, "REFUTED": 4, "INSUFFICIENT": 20},
            },
            "per_category": {},
        }

        output_file = str(tmp_path / "summary.txt")
        saved_path = reporter.save_summary(metrics, output_file)

        assert Path(saved_path).exists()

        with open(saved_path, "r") as f:
            content = f.read()

        assert "ACCURACY TESTING REPORT" in content


class TestIntegration:
    """Integration tests for the full framework."""

    def test_end_to_end_workflow(self, tmp_path):
        """Test complete workflow from evaluation to reports."""
        # Setup
        framework = AccuracyFramework(str(tmp_path))
        reporter = Reporter(str(tmp_path))

        # Create test data
        predictions = [
            "SUPPORTED", "REFUTED", "INSUFFICIENT",
            "SUPPORTED", "SUPPORTED", "REFUTED"
        ]
        verdicts = [
            "SUPPORTED", "REFUTED", "INSUFFICIENT",
            "REFUTED", "SUPPORTED", "REFUTED"
        ]
        categories = [
            "science", "science", "science",
            "history", "history", "history"
        ]

        # Evaluate
        results = framework.evaluate(predictions, verdicts, categories)

        # Generate reports
        html_path = reporter.generate_html_report(
            results,
            str(tmp_path / "report.html")
        )
        json_path = reporter.generate_json_report(
            results,
            str(tmp_path / "report.json")
        )
        summary_path = reporter.save_summary(
            results,
            str(tmp_path / "summary.txt")
        )

        # Save framework outputs
        results_path = framework.save_results_json(
            results,
            str(tmp_path / "results.json")
        )
        cm_path = framework.save_confusion_matrix_csv(
            str(tmp_path / "confusion_matrix.csv")
        )

        # Verify all files exist
        assert Path(html_path).exists()
        assert Path(json_path).exists()
        assert Path(summary_path).exists()
        assert Path(results_path).exists()
        assert Path(cm_path).exists()

        # Verify content
        with open(json_path, "r") as f:
            data = json.load(f)
            assert data["total_samples"] == 6

    def test_regression_detection_workflow(self, tmp_path):
        """Test regression detection in realistic workflow."""
        framework = AccuracyFramework(str(tmp_path))

        # Baseline evaluation
        baseline_preds = ["SUPPORTED"] * 7 + ["REFUTED"] * 2 + ["INSUFFICIENT"]
        baseline_verdicts = ["SUPPORTED"] * 7 + ["REFUTED"] * 2 + ["INSUFFICIENT"]
        baseline_results = framework.evaluate(baseline_preds, baseline_verdicts)

        # Current evaluation with some errors
        current_preds = ["SUPPORTED"] * 6 + ["REFUTED"] + ["REFUTED"] * 2 + ["INSUFFICIENT"]
        current_verdicts = ["SUPPORTED"] * 7 + ["REFUTED"] * 2 + ["INSUFFICIENT"]
        current_results = framework.evaluate(current_preds, current_verdicts)

        # Detect regression
        is_regression, details = framework.detect_regression(
            current_results,
            baseline_results,
            threshold=0.05
        )

        # With 10% accuracy drop, should detect regression
        assert is_regression is True
