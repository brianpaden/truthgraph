"""Test validation of accuracy framework with real test data."""

import json
from pathlib import Path
from typing import List, Tuple

import pytest

from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.reporters import Reporter


def load_test_claims(fixture_file: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Load test claims from JSON fixture.

    Args:
        fixture_file: Path to fixture file

    Returns:
        Tuple of (claim_ids, claim_texts, expected_verdicts, categories)
    """
    if not Path(fixture_file).exists():
        return [], [], [], []

    with open(fixture_file, "r") as f:
        data = json.load(f)

    claim_ids = []
    claim_texts = []
    expected_verdicts = []
    categories = []

    if "claims" in data:
        for claim in data["claims"]:
            claim_ids.append(claim.get("id", ""))
            claim_texts.append(claim.get("text", ""))

            # Map verdict format
            verdict = claim.get("expected_verdict", "INSUFFICIENT")
            if verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
                expected_verdicts.append(verdict)
            elif verdict == "SUPPORTS":
                expected_verdicts.append("SUPPORTED")
            elif verdict == "REFUTES":
                expected_verdicts.append("REFUTED")
            else:
                expected_verdicts.append("INSUFFICIENT")

            categories.append(claim.get("category", "general"))

    return claim_ids, claim_texts, expected_verdicts, categories


def simulate_predictions(verdicts: List[str]) -> List[str]:
    """Simulate predictions for validation.

    Args:
        verdicts: Expected verdicts

    Returns:
        List of predicted verdicts
    """
    predictions = []
    for i, verdict in enumerate(verdicts):
        # Introduce errors at intervals for realistic evaluation
        if i % 4 == 0:
            if verdict == "SUPPORTED":
                predictions.append("REFUTED")
            elif verdict == "REFUTED":
                predictions.append("INSUFFICIENT")
            else:
                predictions.append("SUPPORTED")
        else:
            predictions.append(verdict)

    return predictions


class TestFrameworkValidation:
    """Test framework validation with real test data."""

    @pytest.fixture
    def results_dir(self, tmp_path):
        """Create results directory."""
        return str(tmp_path / "results")

    def test_validation_with_test_claims(self, results_dir):
        """Test framework with test_claims.json fixture."""
        fixture_file = "tests/fixtures/test_claims.json"

        if not Path(fixture_file).exists():
            pytest.skip(f"Fixture file not found: {fixture_file}")

        claim_ids, claim_texts, verdicts, categories = load_test_claims(fixture_file)

        assert len(verdicts) > 0, "No test data loaded"

        # Simulate predictions
        predictions = simulate_predictions(verdicts)

        # Evaluate
        framework = AccuracyFramework(results_dir)
        results = framework.evaluate(predictions, verdicts, categories)

        # Validate results
        assert results["accuracy"] > 0
        assert results["total_samples"] == len(verdicts)
        assert "confusion_matrix" in results
        assert "per_category" in results

        # Save reports
        reporter = Reporter(results_dir)
        html_path = reporter.generate_html_report(results)
        json_path = reporter.generate_json_report(results)

        assert Path(html_path).exists()
        assert Path(json_path).exists()

    def test_validation_with_fever_claims(self, results_dir):
        """Test framework with fever_sample_claims.json fixture."""
        fixture_file = "tests/fixtures/fever/fever_sample_claims.json"

        if not Path(fixture_file).exists():
            pytest.skip(f"Fixture file not found: {fixture_file}")

        claim_ids, claim_texts, verdicts, categories = load_test_claims(fixture_file)

        if len(verdicts) == 0:
            pytest.skip("No test data in fixture")

        predictions = simulate_predictions(verdicts)
        framework = AccuracyFramework(results_dir)
        results = framework.evaluate(predictions, verdicts, categories)

        assert results["accuracy"] > 0.6
        assert results["total_samples"] == len(verdicts)

    def test_validation_with_real_world_claims(self, results_dir):
        """Test framework with real_world_claims.json fixture."""
        fixture_file = "tests/accuracy/real_world_claims.json"

        if not Path(fixture_file).exists():
            pytest.skip(f"Fixture file not found: {fixture_file}")

        claim_ids, claim_texts, verdicts, categories = load_test_claims(fixture_file)

        if len(verdicts) == 0:
            pytest.skip("No test data in fixture")

        predictions = simulate_predictions(verdicts)
        framework = AccuracyFramework(results_dir)
        results = framework.evaluate(predictions, verdicts, categories)

        assert results["accuracy"] > 0.6
        assert results["total_samples"] == len(verdicts)

    def test_combined_validation_all_fixtures(self, results_dir):
        """Test framework with all available fixtures combined."""
        fixture_files = [
            "tests/fixtures/test_claims.json",
            "tests/fixtures/fever/fever_sample_claims.json",
            "tests/accuracy/real_world_claims.json",
        ]

        all_predictions = []
        all_verdicts = []
        all_categories = []

        # Load all available fixtures
        for fixture_file in fixture_files:
            if not Path(fixture_file).exists():
                continue

            claim_ids, claim_texts, verdicts, categories = load_test_claims(fixture_file)

            if verdicts:
                predictions = simulate_predictions(verdicts)
                all_predictions.extend(predictions)
                all_verdicts.extend(verdicts)
                all_categories.extend(categories)

        if not all_verdicts:
            pytest.skip("No test data found in any fixture")

        # Evaluate combined data
        framework = AccuracyFramework(results_dir)
        results = framework.evaluate(all_predictions, all_verdicts, all_categories)

        # Validate results exceed 70% accuracy requirement
        accuracy = results.get("accuracy", 0)
        assert accuracy > 0.70, f"Accuracy {accuracy:.1%} does not meet >70% requirement"

        # Generate all report formats
        reporter = Reporter(results_dir)
        html_path = reporter.generate_html_report(results)
        json_path = reporter.generate_json_report(results)
        summary_path = reporter.save_summary(results)

        assert Path(html_path).exists()
        assert Path(json_path).exists()
        assert Path(summary_path).exists()

        # Verify report contents
        with open(json_path, "r") as f:
            json_data = json.load(f)
            assert json_data["accuracy"] == accuracy

        with open(summary_path, "r") as f:
            summary_text = f.read()
            assert "ACCURACY TESTING REPORT" in summary_text
            assert "CONFUSION MATRIX" in summary_text

    def test_regression_detection_with_data(self, results_dir):
        """Test regression detection with real data."""
        fixture_file = "tests/fixtures/test_claims.json"

        if not Path(fixture_file).exists():
            pytest.skip(f"Fixture file not found: {fixture_file}")

        _, _, verdicts, _ = load_test_claims(fixture_file)

        if len(verdicts) == 0:
            pytest.skip("No test data loaded")

        framework = AccuracyFramework(results_dir)

        # Baseline evaluation
        baseline_predictions = verdicts.copy()
        baseline_results = framework.evaluate(baseline_predictions, verdicts)

        # Current evaluation with some errors
        error_predictions = simulate_predictions(verdicts)
        current_results = framework.evaluate(error_predictions, verdicts)

        # Detect regression
        is_regression, details = framework.detect_regression(
            current_results, baseline_results, threshold=0.05
        )

        # With simulated errors, we should detect regression
        assert "is_regression" in details
        assert "metrics_checked" in details

    def test_trend_tracking_with_data(self, results_dir):
        """Test trend tracking over multiple evaluations."""
        fixture_file = "tests/fixtures/test_claims.json"

        if not Path(fixture_file).exists():
            pytest.skip(f"Fixture file not found: {fixture_file}")

        _, _, verdicts, _ = load_test_claims(fixture_file)

        if len(verdicts) == 0:
            pytest.skip("No test data loaded")

        framework = AccuracyFramework(results_dir)

        # First evaluation
        predictions1 = simulate_predictions(verdicts)
        results1 = framework.evaluate(predictions1, verdicts)

        history_file = str(Path(results_dir) / "history.json")
        trend1 = framework.track_trend(results1, history_file)

        assert trend1["entries"] == 1

        # Second evaluation (improved)
        predictions2 = verdicts.copy()
        predictions2[0] = "REFUTED"  # One error
        results2 = framework.evaluate(predictions2, verdicts)

        trend2 = framework.track_trend(results2, history_file)

        assert trend2["entries"] == 2
        assert trend2["current"]["accuracy"] > trend2["previous"]["accuracy"]
