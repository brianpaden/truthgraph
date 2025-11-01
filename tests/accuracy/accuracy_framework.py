"""Accuracy testing framework for fact verification pipeline.

This module provides comprehensive framework for:
- Running accuracy evaluations
- Tracking trends over time
- Detecting regressions
- Generating reports
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tests.accuracy.metrics import AccuracyMetrics


class AccuracyFramework:
    """Framework for comprehensive accuracy testing and evaluation."""

    def __init__(self, results_dir: str = "tests/accuracy/results"):
        """Initialize the accuracy framework.

        Args:
            results_dir: Directory to store results and reports
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = AccuracyMetrics()
        self.evaluation_results = None
        self.timestamp = None

    def evaluate(
        self,
        predictions: List[str],
        expected_verdicts: List[str],
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run complete accuracy evaluation.

        Args:
            predictions: List of predicted verdicts
            expected_verdicts: List of expected verdicts
            categories: Optional list of claim categories

        Returns:
            Dictionary with evaluation results and metrics
        """
        if len(predictions) != len(expected_verdicts):
            raise ValueError(
                f"Predictions and expected verdicts length mismatch: "
                f"{len(predictions)} vs {len(expected_verdicts)}"
            )

        # Reset and add predictions
        self.metrics.reset()
        for pred, expected, cat in zip(
            predictions, expected_verdicts,
            categories or [None] * len(predictions)
        ):
            self.metrics.add_prediction(pred, expected, cat)

        self.timestamp = datetime.now().isoformat()

        # Generate evaluation results
        self.evaluation_results = {
            "timestamp": self.timestamp,
            "total_samples": len(predictions),
            "accuracy": self.metrics.calculate_accuracy(),
            "macro_f1": self.metrics.calculate_macro_f1(),
            "weighted_f1": self.metrics.calculate_weighted_f1(),
            "precision": self.metrics.calculate_precision(),
            "recall": self.metrics.calculate_recall(),
            "f1": self.metrics.calculate_f1(),
            "confusion_matrix": self.metrics.generate_confusion_matrix(),
            "per_category": self.metrics.per_category_breakdown(),
            "predictions": predictions,
            "expected": expected_verdicts,
            "categories": categories,
        }

        return self.evaluation_results

    def detect_regression(
        self,
        current: Dict[str, Any],
        baseline: Dict[str, Any],
        threshold: float = 0.05,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Detect accuracy regressions.

        Args:
            current: Current evaluation results
            baseline: Baseline evaluation results
            threshold: Regression threshold (default 5%)

        Returns:
            Tuple of (is_regression, regression_details)
        """
        if not baseline or not current:
            return False, {"error": "Missing baseline or current results"}

        is_regression = False
        regression_details = {
            "is_regression": False,
            "threshold": threshold,
            "metrics_checked": {},
        }

        # Check accuracy regression
        baseline_accuracy = baseline.get("accuracy", 0)
        current_accuracy = current.get("accuracy", 0)
        accuracy_delta = baseline_accuracy - current_accuracy

        regression_details["metrics_checked"]["accuracy"] = {
            "baseline": baseline_accuracy,
            "current": current_accuracy,
            "delta": accuracy_delta,
            "regressed": accuracy_delta > threshold,
        }

        if accuracy_delta > threshold:
            is_regression = True

        # Check F1 regression
        baseline_f1 = baseline.get("macro_f1", 0)
        current_f1 = current.get("macro_f1", 0)
        f1_delta = baseline_f1 - current_f1

        regression_details["metrics_checked"]["macro_f1"] = {
            "baseline": baseline_f1,
            "current": current_f1,
            "delta": f1_delta,
            "regressed": f1_delta > threshold,
        }

        if f1_delta > threshold:
            is_regression = True

        # Check per-verdict precision
        baseline_precision = baseline.get("precision", {})
        current_precision = current.get("precision", {})

        regression_details["metrics_checked"]["precision"] = {}
        for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            baseline_p = baseline_precision.get(verdict, 0)
            current_p = current_precision.get(verdict, 0)
            p_delta = baseline_p - current_p

            regression_details["metrics_checked"]["precision"][verdict] = {
                "baseline": baseline_p,
                "current": current_p,
                "delta": p_delta,
                "regressed": p_delta > threshold,
            }

            if p_delta > threshold:
                is_regression = True

        regression_details["is_regression"] = is_regression

        return is_regression, regression_details

    def track_trend(
        self,
        results: Dict[str, Any],
        history_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Track accuracy trend over time.

        Args:
            results: Current evaluation results
            history_file: Path to history file (default: history.json in results_dir)

        Returns:
            Dictionary with trend information
        """
        if history_file is None:
            history_file = str(self.results_dir / "history.json")

        history_path = Path(history_file)

        # Load existing history
        history = []
        if history_path.exists():
            try:
                with open(history_path, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []

        # Add current results to history
        history_entry = {
            "timestamp": results.get("timestamp", datetime.now().isoformat()),
            "accuracy": results.get("accuracy", 0),
            "macro_f1": results.get("macro_f1", 0),
            "weighted_f1": results.get("weighted_f1", 0),
            "samples": results.get("total_samples", 0),
        }

        history.append(history_entry)

        # Save updated history
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

        # Calculate trend
        trend = {
            "entries": len(history),
            "current": history_entry,
            "previous": history[-2] if len(history) > 1 else None,
            "improvements": {},
            "regressions": {},
        }

        if len(history) > 1:
            previous = history[-2]
            current = history[-1]

            # Calculate deltas
            for metric in ["accuracy", "macro_f1", "weighted_f1"]:
                delta = current[metric] - previous[metric]
                if delta > 0.01:  # Improvement
                    trend["improvements"][metric] = delta
                elif delta < -0.01:  # Regression
                    trend["regressions"][metric] = abs(delta)

        return trend

    def save_results_json(
        self, results: Optional[Dict[str, Any]] = None,
        output_file: Optional[str] = None
    ) -> str:
        """Save evaluation results to JSON.

        Args:
            results: Results to save (uses latest if None)
            output_file: Output file path

        Returns:
            Path to saved file
        """
        if results is None:
            results = self.evaluation_results

        if results is None:
            raise ValueError("No results to save. Run evaluate() first.")

        if output_file is None:
            output_file = str(self.results_dir / "accuracy_results.json")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert numpy types for JSON serialization
        results_copy = self._make_json_serializable(results)

        with open(output_path, "w") as f:
            json.dump(results_copy, f, indent=2)

        return str(output_path)

    def save_confusion_matrix_csv(
        self,
        output_file: Optional[str] = None
    ) -> str:
        """Save confusion matrix to CSV.

        Args:
            output_file: Output file path

        Returns:
            Path to saved file
        """
        if self.evaluation_results is None:
            raise ValueError("No results to save. Run evaluate() first.")

        if output_file is None:
            output_file = str(self.results_dir / "confusion_matrix.csv")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        confusion_matrix = self.evaluation_results.get("confusion_matrix", {})
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        with open(output_path, "w") as f:
            # Write header
            f.write("Predicted," + ",".join(verdicts) + "\n")

            # Write rows
            for actual in verdicts:
                row_data = confusion_matrix.get(actual, {})
                counts = [str(row_data.get(pred, 0)) for pred in verdicts]
                f.write(f"{actual}," + ",".join(counts) + "\n")

        return str(output_path)

    def load_results(self, results_file: str) -> Dict[str, Any]:
        """Load evaluation results from file.

        Args:
            results_file: Path to results file

        Returns:
            Loaded results dictionary
        """
        with open(results_file, "r") as f:
            results = json.load(f)

        self.evaluation_results = results
        return results

    def compare_evaluations(
        self,
        results1: Dict[str, Any],
        results2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare two evaluation results.

        Args:
            results1: First evaluation results
            results2: Second evaluation results

        Returns:
            Comparison report
        """
        comparison = {
            "results1_accuracy": results1.get("accuracy", 0),
            "results2_accuracy": results2.get("accuracy", 0),
            "accuracy_delta": results2.get("accuracy", 0) - results1.get("accuracy", 0),
            "results1_f1": results1.get("macro_f1", 0),
            "results2_f1": results2.get("macro_f1", 0),
            "f1_delta": results2.get("macro_f1", 0) - results1.get("macro_f1", 0),
            "timestamp1": results1.get("timestamp"),
            "timestamp2": results2.get("timestamp"),
        }

        return comparison

    @staticmethod
    def _make_json_serializable(obj: Any) -> Any:
        """Convert numpy and other types to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable object
        """
        if isinstance(obj, dict):
            return {k: AccuracyFramework._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AccuracyFramework._make_json_serializable(item) for item in obj]
        elif hasattr(obj, "item"):  # numpy types
            return obj.item()
        elif isinstance(obj, float):
            return round(obj, 4)
        else:
            return obj
