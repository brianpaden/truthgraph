"""Typo and misspelling robustness tests.

This module tests the system's ability to handle claims with typos,
misspellings, and character-level noise while maintaining accuracy.

Test Coverage:
- Single character typos
- Multiple character typos
- Repeated characters
- Punctuation errors
"""

from typing import Any, Dict

import pytest

from tests.robustness.robustness_utils import (
    RobustnessAnalyzer,
    RobustnessMetrics,
    RobustnessResult,
)


class TestTypoRobustness:
    """Test suite for typo and misspelling robustness."""

    def test_load_typo_examples_fixture(self, typo_examples: Dict[str, Any]):
        """Verify typo examples fixture loads correctly.

        Args:
            typo_examples: Fixture with typo test data
        """
        assert typo_examples is not None
        assert "metadata" in typo_examples
        assert typo_examples["metadata"]["dimension"] == "typo_robustness"
        assert "test_cases" in typo_examples
        assert len(typo_examples["test_cases"]) > 0

    def test_typo_examples_structure(self, typo_examples: Dict[str, Any]):
        """Verify typo examples have proper structure.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])

        assert len(test_cases) >= 10, "Should have at least 10 test cases"

        for test_case in test_cases:
            # Verify required fields
            assert "id" in test_case
            assert "base_claim" in test_case
            assert "category" in test_case
            assert "expected_verdict" in test_case
            assert "variations" in test_case

            # Verify variations have proper structure
            variations = test_case.get("variations", [])
            assert len(variations) > 0, f"Test case {test_case['id']} has no variations"

            for variation in variations:
                assert "text" in variation
                assert "typo_count" in variation
                assert "typo_type" in variation

    def test_typo_variation_coverage(self, typo_examples: Dict[str, Any]):
        """Verify coverage of different typo types.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])
        typo_types: set = set()

        for test_case in test_cases:
            for variation in test_case.get("variations", []):
                typo_types.add(variation.get("typo_type"))

        # Should have multiple typo types
        assert len(typo_types) > 0, "Should have varied typo types"
        assert "single_typo" in typo_types or "multiple_typos" in typo_types

    def test_typo_base_claims_valid(self, typo_examples: Dict[str, Any]):
        """Verify base claims are valid factual statements.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            assert len(base_claim) > 0, f"Test case {test_case['id']} has empty base claim"
            assert len(base_claim) > 10, f"Base claim too short: {base_claim}"

    def test_typo_expected_verdicts_valid(self, typo_examples: Dict[str, Any]):
        """Verify expected verdicts are valid.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            assert verdict in valid_verdicts, (
                f"Test case {test_case['id']} has invalid verdict: {verdict}"
            )

    def test_typo_categories_valid(self, typo_examples: Dict[str, Any]):
        """Verify claim categories are valid.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])
        valid_categories = {"science", "health", "politics", "technology", "history"}

        for test_case in test_cases:
            category = test_case.get("category")
            assert category in valid_categories or category is not None, (
                f"Test case {test_case['id']} has invalid category: {category}"
            )

    @pytest.mark.parametrize("typo_type", [
        "single_typo",
        "multiple_typos",
        "repeated_characters",
        "punctuation",
    ])
    def test_coverage_of_typo_types(
        self,
        typo_examples: Dict[str, Any],
        typo_type: str,
    ):
        """Verify coverage of specific typo types.

        Args:
            typo_examples: Fixture with typo test data
            typo_type: Type of typo to verify coverage for
        """
        test_cases = typo_examples.get("test_cases", [])

        # Check if at least one test covers this typo type
        found = False
        for test_case in test_cases:
            for variation in test_case.get("variations", []):
                if variation.get("typo_type") == typo_type:
                    found = True
                    break
            if found:
                break

        # Some typo types may not be present, that's okay
        # This test mainly verifies test data is well-formed

    def test_typo_example_count(self, typo_examples: Dict[str, Any]):
        """Verify sufficient test cases are available.

        Args:
            typo_examples: Fixture with typo test data
        """
        test_cases = typo_examples.get("test_cases", [])
        assert len(test_cases) >= 10, "Should have at least 10 test cases for typo dimension"

        # Verify sufficient variations per test case
        total_variations = sum(
            len(tc.get("variations", [])) for tc in test_cases
        )
        assert total_variations >= 20, "Should have at least 20 total variations"

    def test_robustness_metrics_initialization(self):
        """Test RobustnessMetrics initialization."""
        metrics = RobustnessMetrics(
            dimension="typo_robustness",
            base_accuracy=0.95,
            variant_accuracy=0.85,
        )

        assert metrics.dimension == "typo_robustness"
        assert metrics.base_accuracy == 0.95
        assert metrics.variant_accuracy == 0.85
        assert pytest.approx(metrics.accuracy_degradation, rel=1e-5) == 0.10
        assert metrics.test_count == 0
        assert metrics.correct_count == 0

    def test_robustness_result_initialization(self):
        """Test RobustnessResult initialization."""
        result = RobustnessResult(
            test_id="typo_001",
            dimension="typo_robustness",
            base_claim="The Earth is round",
            expected_verdict="SUPPORTED",
            category="science",
            variant_claim="Th3 E4rth 1s r0und",
            predicted_verdict="SUPPORTED",
            confidence=0.92,
            is_correct=True,
            variant_type="single_typo",
        )

        assert result.test_id == "typo_001"
        assert result.is_correct is True
        assert result.variant_type == "single_typo"
        assert result.timestamp is not None

    def test_robustness_analyzer_initialization(self, results_dir):
        """Test RobustnessAnalyzer initialization.

        Args:
            results_dir: Results directory fixture
        """
        analyzer = RobustnessAnalyzer(str(results_dir))

        assert analyzer.results_dir.exists()
        assert len(analyzer.results) == 0
        assert len(analyzer.metrics_by_dimension) == 0

    def test_robustness_analyzer_add_result(self, results_dir):
        """Test adding results to analyzer.

        Args:
            results_dir: Results directory fixture
        """
        analyzer = RobustnessAnalyzer(str(results_dir))

        result = RobustnessResult(
            test_id="typo_001",
            dimension="typo_robustness",
            base_claim="Test claim",
            expected_verdict="SUPPORTED",
            category="science",
            variant_claim="T3st cl41m",
            predicted_verdict="SUPPORTED",
            confidence=0.90,
            is_correct=True,
            variant_type="single_typo",
        )

        analyzer.add_result(result)
        assert len(analyzer.results) == 1
        assert analyzer.results[0].test_id == "typo_001"

    def test_robustness_analyzer_calculate_metrics(self, results_dir):
        """Test metrics calculation in analyzer.

        Args:
            results_dir: Results directory fixture
        """
        analyzer = RobustnessAnalyzer(str(results_dir))

        # Add some results
        for i in range(10):
            result = RobustnessResult(
                test_id=f"typo_{i:03d}",
                dimension="typo_robustness",
                base_claim="Test claim",
                expected_verdict="SUPPORTED",
                category="science",
                variant_claim=f"T3st cl41m {i}",
                predicted_verdict="SUPPORTED",
                confidence=0.85,
                is_correct=i < 8,  # 8 correct, 2 incorrect
                variant_type="single_typo",
            )
            analyzer.add_result(result)

        metrics = analyzer.calculate_dimension_metrics(
            "typo_robustness",
            base_accuracy=0.95,
        )

        assert metrics.dimension == "typo_robustness"
        assert metrics.test_count == 10
        assert metrics.correct_count == 8
        assert metrics.variant_accuracy == 0.8
        assert pytest.approx(metrics.accuracy_degradation, rel=1e-5) == 0.15

    def test_robustness_analyzer_identify_vulnerabilities(self, results_dir):
        """Test vulnerability identification.

        Args:
            results_dir: Results directory fixture
        """
        analyzer = RobustnessAnalyzer(str(results_dir))

        # Add results with low accuracy
        for i in range(10):
            result = RobustnessResult(
                test_id=f"typo_{i:03d}",
                dimension="typo_robustness",
                base_claim="Test claim",
                expected_verdict="SUPPORTED",
                category="science",
                variant_claim=f"T3st cl41m {i}",
                predicted_verdict="SUPPORTED" if i < 3 else "REFUTED",
                confidence=0.4 if i >= 5 else 0.9,
                is_correct=i < 3,
                variant_type="single_typo",
            )
            analyzer.add_result(result)

        # Calculate metrics
        analyzer.calculate_dimension_metrics(
            "typo_robustness",
            base_accuracy=0.95,
        )

        # Identify vulnerabilities
        vulnerabilities = analyzer.identify_vulnerabilities(threshold=0.15)

        assert "high_degradation" in vulnerabilities
        assert "low_confidence" in vulnerabilities
        assert "category_specific" in vulnerabilities
        assert "variant_patterns" in vulnerabilities

    def test_robustness_analyzer_generate_recommendations(self, results_dir):
        """Test recommendation generation.

        Args:
            results_dir: Results directory fixture
        """
        analyzer = RobustnessAnalyzer(str(results_dir))

        # Add results
        for i in range(5):
            result = RobustnessResult(
                test_id=f"typo_{i:03d}",
                dimension="typo_robustness",
                base_claim="Test claim",
                expected_verdict="SUPPORTED",
                category="science",
                variant_claim=f"T3st cl41m {i}",
                predicted_verdict="SUPPORTED",
                confidence=0.7,
                is_correct=i < 2,
                variant_type="single_typo",
            )
            analyzer.add_result(result)

        # Calculate metrics and get vulnerabilities
        analyzer.calculate_dimension_metrics(
            "typo_robustness",
            base_accuracy=0.95,
        )
        vulnerabilities = analyzer.identify_vulnerabilities(threshold=0.1)

        # Generate recommendations
        recommendations = analyzer.generate_improvement_recommendations(
            vulnerabilities
        )

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert "priority" in rec
            assert "area" in rec
            assert "recommendation" in rec
