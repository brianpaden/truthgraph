"""Comprehensive tests for edge case data handlers.

Tests cover:
- Data loader functionality and validation
- Classifier accuracy and edge cases
- Results handler aggregation and reporting
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from tests.accuracy.edge_cases import (
    EdgeCaseClassifier,
    EdgeCaseDataLoader,
    EdgeCaseResultsHandler,
)


class TestEdgeCaseDataLoader:
    """Tests for EdgeCaseDataLoader."""

    def test_load_all_edge_cases(self):
        """Test loading all edge cases successfully."""
        loader = EdgeCaseDataLoader()
        data = loader.load_all_edge_cases()

        assert "metadata" in data
        assert "claims" in data
        assert isinstance(data["claims"], list)
        assert len(data["claims"]) > 0

    def test_load_edge_cases_by_category(self):
        """Test loading edge cases filtered by category."""
        loader = EdgeCaseDataLoader()

        # Test each valid category
        for category in loader.EDGE_CASE_CATEGORIES:
            claims = loader.load_edge_cases(category)
            assert isinstance(claims, list)

            # Verify all claims have this category
            for claim in claims:
                assert category in claim["edge_case_type"]

    def test_load_edge_cases_invalid_category(self):
        """Test that invalid category raises ValueError."""
        loader = EdgeCaseDataLoader()

        with pytest.raises(ValueError, match="Unknown category"):
            loader.load_edge_cases("invalid_category")

    def test_validate_edge_case_data_valid(self):
        """Test validation passes for valid data."""
        loader = EdgeCaseDataLoader()
        data = loader.load_all_edge_cases()

        assert loader.validate_edge_case_data(data) is True
        assert len(loader.get_validation_errors()) == 0

    def test_validate_edge_case_data_missing_metadata(self):
        """Test validation fails when metadata is missing."""
        loader = EdgeCaseDataLoader()
        invalid_data = {"claims": []}

        assert loader.validate_edge_case_data(invalid_data) is False
        errors = loader.get_validation_errors()
        assert any("metadata" in error.lower() for error in errors)

    def test_validate_edge_case_data_missing_claims(self):
        """Test validation fails when claims are missing."""
        loader = EdgeCaseDataLoader()
        invalid_data = {"metadata": {"version": "1.0"}}

        assert loader.validate_edge_case_data(invalid_data) is False
        errors = loader.get_validation_errors()
        assert any("claims" in error.lower() for error in errors)

    def test_get_claims_by_verdict(self):
        """Test filtering claims by expected verdict."""
        loader = EdgeCaseDataLoader()

        for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            claims = loader.get_claims_by_verdict(verdict)
            assert isinstance(claims, list)

            # Verify all claims have correct verdict
            for claim in claims:
                assert claim["expected_verdict"] == verdict

    def test_get_claims_by_complexity(self):
        """Test filtering claims by complexity score."""
        loader = EdgeCaseDataLoader()

        # Test different complexity ranges
        low_complexity = loader.get_claims_by_complexity(0.0, 0.3)
        high_complexity = loader.get_claims_by_complexity(0.7, 1.0)

        # Verify complexity scores are in range
        for claim in low_complexity:
            assert 0.0 <= claim["complexity_score"] <= 0.3

        for claim in high_complexity:
            assert 0.7 <= claim["complexity_score"] <= 1.0

    def test_get_multilingual_claims(self):
        """Test getting multilingual claims organized by language."""
        loader = EdgeCaseDataLoader()
        multilingual = loader.get_multilingual_claims()

        assert isinstance(multilingual, dict)

        # Verify all claims are multilingual
        for lang, claims in multilingual.items():
            for claim in claims:
                assert "multilingual" in claim["edge_case_type"]
                assert claim.get("language") == lang

    def test_get_statistics(self):
        """Test dataset statistics calculation."""
        loader = EdgeCaseDataLoader()
        stats = loader.get_statistics()

        assert "total_claims" in stats
        assert "edge_case_counts" in stats
        assert "verdict_counts" in stats
        assert "complexity_stats" in stats
        assert "languages" in stats

        # Verify counts are positive
        assert stats["total_claims"] > 0

        # Verify complexity stats
        complexity = stats["complexity_stats"]
        assert 0.0 <= complexity["min"] <= 1.0
        assert 0.0 <= complexity["max"] <= 1.0
        assert 0.0 <= complexity["avg"] <= 1.0

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        loader = EdgeCaseDataLoader()

        # Load data to cache it
        loader.load_all_edge_cases()
        assert loader._cached_data is not None

        # Clear cache
        loader.clear_cache()
        assert loader._cached_data is None

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        loader = EdgeCaseDataLoader(data_path=Path("/nonexistent/path.json"))

        with pytest.raises(FileNotFoundError):
            loader.load_all_edge_cases()

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            loader = EdgeCaseDataLoader(data_path=temp_path)
            with pytest.raises(ValueError, match="Invalid JSON"):
                loader.load_all_edge_cases()
        finally:
            temp_path.unlink()


class TestEdgeCaseClassifier:
    """Tests for EdgeCaseClassifier."""

    def test_classify_long_claim(self):
        """Test classification of long claims."""
        classifier = EdgeCaseClassifier()

        long_claim = " ".join(["word"] * 100)  # 100 words
        categories = classifier.classify_claim(long_claim)

        assert "long_claims" in categories
        assert classifier.is_long_claim(long_claim)

    def test_classify_short_claim(self):
        """Test classification of short claims."""
        classifier = EdgeCaseClassifier()

        short_claim = "Water is wet"  # 3 words
        categories = classifier.classify_claim(short_claim)

        assert "short_claims" in categories
        assert classifier.is_short_claim(short_claim)

    def test_classify_special_characters(self):
        """Test detection of special characters."""
        classifier = EdgeCaseClassifier()

        # Greek letters
        greek_claim = "The ratio π is approximately 3.14159"
        assert classifier.has_special_characters(greek_claim)

        # Subscripts
        subscript_claim = "Water is H₂O"
        assert classifier.has_special_characters(subscript_claim)

        # Mathematical symbols
        integral_claim = "The integral ∫ of the function"
        assert classifier.has_special_characters(integral_claim)

    def test_classify_multilingual(self):
        """Test detection of multilingual content."""
        classifier = EdgeCaseClassifier()

        # Chinese
        chinese_claim = "人工智能正在改变世界"
        assert classifier.is_multilingual(chinese_claim)

        # French (with Latin characters - should not be multilingual)
        french_claim = "La Tour Eiffel a été construite en 1889"
        assert not classifier.is_multilingual(french_claim)

        # Russian (Cyrillic)
        russian_claim = "Москва столица России"
        assert classifier.is_multilingual(russian_claim)

    def test_classify_ambiguous_phrasing(self):
        """Test detection of ambiguous phrasing."""
        classifier = EdgeCaseClassifier()

        ambiguous_claims = [
            "Some studies suggest coffee is healthy",
            "Research may indicate benefits",
            "The evidence is debated",
            "Opinions vary on this topic",
        ]

        for claim in ambiguous_claims:
            assert classifier.has_ambiguous_phrasing(claim)

    def test_classify_complex_technical(self):
        """Test detection of complex technical content."""
        classifier = EdgeCaseClassifier()

        technical_claims = [
            "Quantum entanglement is a phenomenon in physics",
            "The mitochondria are the powerhouse of the cell",
            "CRISPR-Cas9 enables gene editing",
            "Chemical formula H2O represents water",
        ]

        for claim in technical_claims:
            assert classifier.is_complex_technical(claim)

    def test_count_words(self):
        """Test word counting."""
        classifier = EdgeCaseClassifier()

        assert classifier.count_words("Hello world") == 2
        assert classifier.count_words("One two three four five") == 5
        assert classifier.count_words("  Extra   spaces  ") == 2

    def test_analyze_claim(self):
        """Test comprehensive claim analysis."""
        classifier = EdgeCaseClassifier()

        claim = "The quantum phenomenon involves π calculations"
        analysis = classifier.analyze_claim(claim)

        assert "text" in analysis
        assert "edge_case_categories" in analysis
        assert "word_count" in analysis
        assert "char_count" in analysis
        assert "is_long" in analysis
        assert "is_short" in analysis
        assert "has_special_chars" in analysis
        assert "detected_scripts" in analysis

    def test_batch_classify(self):
        """Test batch classification of multiple claims."""
        classifier = EdgeCaseClassifier()

        claims = [
            "Short",
            "This is a normal length claim",
            " ".join(["word"] * 100),  # Long claim
        ]

        results = classifier.batch_classify(claims)

        assert len(results) == 3
        assert results[0]["is_short"]
        assert not results[1]["is_short"] and not results[1]["is_long"]
        assert results[2]["is_long"]

    def test_get_category_statistics(self):
        """Test category statistics calculation."""
        classifier = EdgeCaseClassifier()

        claims = [
            "Short",
            "Also short",
            " ".join(["word"] * 100),  # Long
            "Water is H₂O",  # Special chars (subscript)
        ]

        stats = classifier.get_category_statistics(claims)

        assert "_summary" in stats
        assert stats["_summary"]["total_claims"] == 4
        assert "short_claims" in stats
        assert "long_claims" in stats
        assert "special_characters" in stats


class TestEdgeCaseResultsHandler:
    """Tests for EdgeCaseResultsHandler."""

    def test_add_result(self):
        """Test adding individual results."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            claim_id="test_001",
            claim_text="Test claim",
            edge_case_types=["short_claims"],
            expected_verdict="SUPPORTED",
            predicted_verdict="SUPPORTED",
            confidence_score=0.95,
        )

        assert len(handler.results) == 1
        assert handler.results[0].claim_id == "test_001"
        assert handler.results[0].passed is True

    def test_add_result_failure(self):
        """Test adding failed result."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            claim_id="test_002",
            claim_text="Test claim",
            edge_case_types=["long_claims"],
            expected_verdict="SUPPORTED",
            predicted_verdict="REFUTED",
        )

        assert handler.results[0].passed is False

    def test_add_result_error(self):
        """Test adding result with error."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            claim_id="test_003",
            claim_text="Test claim",
            edge_case_types=["complex_technical"],
            expected_verdict="INSUFFICIENT",
            error="Processing failed",
        )

        assert handler.results[0].passed is False
        assert handler.results[0].error == "Processing failed"

    def test_aggregate_results_empty(self):
        """Test aggregating empty results."""
        handler = EdgeCaseResultsHandler()
        results = handler.aggregate_results()

        assert results["total_tests"] == 0
        assert results["passed_tests"] == 0
        assert results["pass_rate"] == 0.0

    def test_aggregate_results_basic(self):
        """Test basic results aggregation."""
        handler = EdgeCaseResultsHandler()

        # Add mixed results
        handler.add_result(
            "test_001",
            "Claim 1",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
            0.95,
        )
        handler.add_result(
            "test_002", "Claim 2", ["long_claims"], "REFUTED", "SUPPORTED"
        )
        handler.add_result(
            "test_003",
            "Claim 3",
            ["special_characters"],
            "INSUFFICIENT",
            error="Failed",
        )

        results = handler.aggregate_results()

        assert results["total_tests"] == 3
        assert results["passed_tests"] == 1
        assert results["failed_tests"] == 1
        assert results["error_tests"] == 1
        assert 0.0 < results["pass_rate"] < 1.0

    def test_aggregate_by_category(self):
        """Test aggregation by edge case category."""
        handler = EdgeCaseResultsHandler()

        # Add results for different categories
        handler.add_result(
            "test_001",
            "Claim 1",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
        )
        handler.add_result(
            "test_002",
            "Claim 2",
            ["short_claims"],
            "REFUTED",
            "REFUTED",
        )
        handler.add_result(
            "test_003",
            "Claim 3",
            ["long_claims"],
            "SUPPORTED",
            "REFUTED",
        )

        results = handler.aggregate_results()
        by_category = results["results_by_category"]

        assert "short_claims" in by_category
        assert "long_claims" in by_category
        assert by_category["short_claims"]["total"] == 2
        assert by_category["short_claims"]["passed"] == 2
        assert by_category["long_claims"]["total"] == 1
        assert by_category["long_claims"]["passed"] == 0

    def test_aggregate_by_verdict(self):
        """Test aggregation by expected verdict."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            "test_001",
            "Claim 1",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
        )
        handler.add_result(
            "test_002",
            "Claim 2",
            ["long_claims"],
            "SUPPORTED",
            "REFUTED",
        )
        handler.add_result(
            "test_003",
            "Claim 3",
            ["complex_technical"],
            "REFUTED",
            "REFUTED",
        )

        results = handler.aggregate_results()
        by_verdict = results["results_by_verdict"]

        assert "SUPPORTED" in by_verdict
        assert "REFUTED" in by_verdict
        assert by_verdict["SUPPORTED"]["total"] == 2
        assert by_verdict["REFUTED"]["total"] == 1

    def test_save_and_load_results(self):
        """Test saving and loading results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = EdgeCaseResultsHandler(output_dir=Path(temp_dir))

            # Add some results
            handler.add_result(
                "test_001",
                "Claim 1",
                ["short_claims"],
                "SUPPORTED",
                "SUPPORTED",
                0.95,
            )

            # Save results
            output_path = handler.save_results()
            assert Path(output_path).exists()

            # Load results
            loaded = handler.load_results(output_path)
            assert loaded["total_tests"] == 1
            assert loaded["passed_tests"] == 1

    def test_generate_summary(self):
        """Test summary generation."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            "test_001",
            "Claim 1",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
            0.95,
        )

        summary = handler.generate_summary()

        assert "EDGE CASE VALIDATION RESULTS SUMMARY" in summary
        assert "Total Tests: 1" in summary
        assert "Passed: 1" in summary
        assert "Pass Rate:" in summary

    def test_clear_results(self):
        """Test clearing results."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            "test_001",
            "Claim",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
        )
        assert len(handler.results) == 1

        handler.clear_results()
        assert len(handler.results) == 0

    def test_edge_case_metrics(self):
        """Test edge case handling metrics calculation."""
        handler = EdgeCaseResultsHandler()

        handler.add_result(
            "test_001",
            "Claim 1",
            ["short_claims"],
            "SUPPORTED",
            "SUPPORTED",
            confidence_score=0.9,
            execution_time_ms=100.0,
        )
        handler.add_result(
            "test_002",
            "Claim 2",
            ["long_claims"],
            "REFUTED",
            "REFUTED",
            confidence_score=0.8,
            execution_time_ms=200.0,
        )

        results = handler.aggregate_results()
        metrics = results["edge_case_handling_metrics"]

        assert "avg_confidence" in metrics
        assert "avg_execution_time_ms" in metrics
        assert "error_rate" in metrics
        assert metrics["avg_confidence"] == pytest.approx(0.85, abs=0.01)
        assert metrics["avg_execution_time_ms"] == pytest.approx(150.0, abs=0.1)
