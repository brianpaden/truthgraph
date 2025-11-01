"""Accuracy metrics calculation module.

This module provides comprehensive accuracy metrics calculation including:
- Precision, recall, F1 score per verdict
- Overall accuracy
- Confusion matrix generation
- Per-category accuracy analysis
"""

from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


class AccuracyMetrics:
    """Calculate and manage accuracy metrics for verdict verification."""

    VERDICT_TYPES = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

    def __init__(self):
        """Initialize metrics calculator."""
        self.predictions = []
        self.labels = []
        self.categories = []

    def add_prediction(
        self,
        predicted_verdict: str,
        expected_verdict: str,
        category: str = None,
    ) -> None:
        """Add a prediction to the metrics calculation.

        Args:
            predicted_verdict: The predicted verdict
            expected_verdict: The expected/actual verdict
            category: Optional category for breakdown analysis
        """
        self.predictions.append(predicted_verdict)
        self.labels.append(expected_verdict)
        if category:
            self.categories.append(category)

    def calculate_precision(self) -> Dict[str, float]:
        """Calculate precision for each verdict type.

        Returns:
            Dictionary with precision scores for each verdict
        """
        if not self.predictions or not self.labels:
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

        try:
            # Create label arrays for multi-class precision
            label_indices = {v: i for i, v in enumerate(self.VERDICT_TYPES)}
            y_true = np.array([label_indices.get(v, -1) for v in self.labels])
            y_pred = np.array([label_indices.get(v, -1) for v in self.predictions])

            # Filter out unknown verdicts
            valid_mask = (y_true >= 0) & (y_pred >= 0)
            y_true = y_true[valid_mask]
            y_pred = y_pred[valid_mask]

            if len(y_true) == 0:
                return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

            precision_scores = precision_score(
                y_true, y_pred, labels=list(range(len(self.VERDICT_TYPES))),
                zero_division=0, average=None
            )

            return {
                verdict: float(score)
                for verdict, score in zip(self.VERDICT_TYPES, precision_scores)
            }
        except Exception as e:
            print(f"Error calculating precision: {e}")
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

    def calculate_recall(self) -> Dict[str, float]:
        """Calculate recall for each verdict type.

        Returns:
            Dictionary with recall scores for each verdict
        """
        if not self.predictions or not self.labels:
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

        try:
            label_indices = {v: i for i, v in enumerate(self.VERDICT_TYPES)}
            y_true = np.array([label_indices.get(v, -1) for v in self.labels])
            y_pred = np.array([label_indices.get(v, -1) for v in self.predictions])

            valid_mask = (y_true >= 0) & (y_pred >= 0)
            y_true = y_true[valid_mask]
            y_pred = y_pred[valid_mask]

            if len(y_true) == 0:
                return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

            recall_scores = recall_score(
                y_true, y_pred, labels=list(range(len(self.VERDICT_TYPES))),
                zero_division=0, average=None
            )

            return {
                verdict: float(score)
                for verdict, score in zip(self.VERDICT_TYPES, recall_scores)
            }
        except Exception as e:
            print(f"Error calculating recall: {e}")
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

    def calculate_f1(self) -> Dict[str, float]:
        """Calculate F1 score for each verdict type.

        Returns:
            Dictionary with F1 scores for each verdict
        """
        if not self.predictions or not self.labels:
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

        try:
            label_indices = {v: i for i, v in enumerate(self.VERDICT_TYPES)}
            y_true = np.array([label_indices.get(v, -1) for v in self.labels])
            y_pred = np.array([label_indices.get(v, -1) for v in self.predictions])

            valid_mask = (y_true >= 0) & (y_pred >= 0)
            y_true = y_true[valid_mask]
            y_pred = y_pred[valid_mask]

            if len(y_true) == 0:
                return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

            f1_scores = f1_score(
                y_true, y_pred, labels=list(range(len(self.VERDICT_TYPES))),
                zero_division=0, average=None
            )

            return {
                verdict: float(score)
                for verdict, score in zip(self.VERDICT_TYPES, f1_scores)
            }
        except Exception as e:
            print(f"Error calculating F1: {e}")
            return {verdict: 0.0 for verdict in self.VERDICT_TYPES}

    def calculate_accuracy(self) -> float:
        """Calculate overall accuracy.

        Returns:
            Overall accuracy as a float between 0 and 1
        """
        if not self.predictions or not self.labels:
            return 0.0

        if len(self.predictions) != len(self.labels):
            return 0.0

        correct = sum(
            1 for pred, label in zip(self.predictions, self.labels)
            if pred == label
        )
        return correct / len(self.predictions)

    def calculate_macro_f1(self) -> float:
        """Calculate macro-averaged F1 score.

        Returns:
            Macro F1 score
        """
        f1_scores = self.calculate_f1()
        if not f1_scores:
            return 0.0
        return sum(f1_scores.values()) / len(f1_scores)

    def calculate_weighted_f1(self) -> float:
        """Calculate weighted F1 score based on support.

        Returns:
            Weighted F1 score
        """
        if not self.labels:
            return 0.0

        try:
            label_indices = {v: i for i, v in enumerate(self.VERDICT_TYPES)}
            y_true = np.array([label_indices.get(v, -1) for v in self.labels])
            y_pred = np.array([label_indices.get(v, -1) for v in self.predictions])

            valid_mask = (y_true >= 0) & (y_pred >= 0)
            y_true = y_true[valid_mask]
            y_pred = y_pred[valid_mask]

            if len(y_true) == 0:
                return 0.0

            return float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
        except Exception as e:
            print(f"Error calculating weighted F1: {e}")
            return 0.0

    def generate_confusion_matrix(self) -> Dict[str, Dict[str, int]]:
        """Generate confusion matrix for verdict predictions.

        Returns:
            Nested dictionary representing the confusion matrix
        """
        matrix = {
            verdict: {v: 0 for v in self.VERDICT_TYPES}
            for verdict in self.VERDICT_TYPES
        }

        for pred, label in zip(self.predictions, self.labels):
            if label in matrix and pred in matrix[label]:
                matrix[label][pred] += 1

        return matrix

    def get_confusion_matrix_array(self) -> np.ndarray:
        """Get confusion matrix as numpy array.

        Returns:
            3x3 confusion matrix array
        """
        label_indices = {v: i for i, v in enumerate(self.VERDICT_TYPES)}
        y_true = np.array([label_indices.get(v, -1) for v in self.labels])
        y_pred = np.array([label_indices.get(v, -1) for v in self.predictions])

        valid_mask = (y_true >= 0) & (y_pred >= 0)
        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        if len(y_true) == 0:
            return np.zeros((3, 3), dtype=int)

        return confusion_matrix(
            y_true, y_pred,
            labels=list(range(len(self.VERDICT_TYPES)))
        )

    def per_category_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Calculate metrics per category.

        Returns:
            Dictionary with accuracy, precision, recall, F1 per category
        """
        if not self.categories:
            return {}

        category_metrics = {}
        unique_categories = set(self.categories)

        for category in unique_categories:
            cat_metrics = AccuracyMetrics()

            # Filter predictions and labels for this category
            for pred, label, cat in zip(self.predictions, self.labels, self.categories):
                if cat == category:
                    cat_metrics.add_prediction(pred, label, cat)

            if cat_metrics.predictions:
                category_metrics[category] = {
                    "accuracy": cat_metrics.calculate_accuracy(),
                    "precision": cat_metrics.calculate_precision(),
                    "recall": cat_metrics.calculate_recall(),
                    "f1": cat_metrics.calculate_f1(),
                    "macro_f1": cat_metrics.calculate_macro_f1(),
                    "samples": len(cat_metrics.predictions),
                }

        return category_metrics

    def get_metrics_summary(self) -> Dict[str, any]:
        """Get comprehensive metrics summary.

        Returns:
            Dictionary with all calculated metrics
        """
        return {
            "total_samples": len(self.predictions),
            "accuracy": self.calculate_accuracy(),
            "macro_f1": self.calculate_macro_f1(),
            "weighted_f1": self.calculate_weighted_f1(),
            "precision": self.calculate_precision(),
            "recall": self.calculate_recall(),
            "f1": self.calculate_f1(),
            "confusion_matrix": self.generate_confusion_matrix(),
            "per_category": self.per_category_breakdown(),
        }

    def reset(self) -> None:
        """Reset metrics calculator."""
        self.predictions = []
        self.labels = []
        self.categories = []
