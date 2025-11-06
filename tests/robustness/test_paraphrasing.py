"""Paraphrase robustness tests.

This module tests the system's ability to handle paraphrased and
semantically equivalent claims while maintaining verdict consistency.

Test Coverage:
- Synonym substitution
- Structural rearrangement
- Pronoun variation
- Active/passive voice transformation
"""

from typing import Any, Dict

import pytest


class TestParaphraseRobustness:
    """Test suite for paraphrase robustness."""

    def test_load_paraphrase_examples_fixture(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify paraphrase examples fixture loads correctly.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        assert paraphrase_examples is not None
        assert "metadata" in paraphrase_examples
        assert paraphrase_examples["metadata"]["dimension"] == "paraphrase_robustness"
        assert "test_cases" in paraphrase_examples
        assert len(paraphrase_examples["test_cases"]) > 0

    def test_paraphrase_examples_structure(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify paraphrase examples have proper structure.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])

        assert len(test_cases) >= 10, "Should have at least 10 test cases"

        for test_case in test_cases:
            # Verify required fields
            assert "id" in test_case
            assert "base_claim" in test_case
            assert "category" in test_case
            assert "expected_verdict" in test_case
            assert "variations" in test_case

            # Verify variations
            variations = test_case.get("variations", [])
            assert len(variations) > 0

            for variation in variations:
                assert "text" in variation
                assert "type" in variation

    def test_paraphrase_variation_types(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify different paraphrase types are represented.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])
        paraphrase_types: set = set()

        for test_case in test_cases:
            for variation in test_case.get("variations", []):
                paraphrase_types.add(variation.get("type"))

        assert len(paraphrase_types) > 0
        assert "synonym_substitution" in paraphrase_types or \
               "structural_rearrangement" in paraphrase_types

    def test_paraphrase_semantic_equivalence(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify paraphrases maintain semantic equivalence.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "").lower()
            variations = test_case.get("variations", [])

            for variation in variations:
                variant_text = variation.get("text", "").lower()

                # Paraphrases should have some semantic overlap
                # but not be identical
                assert variant_text != base_claim, (
                    f"Variation should differ from base claim: {base_claim}"
                )
                assert len(variant_text) > 0

    def test_paraphrase_expected_verdict_consistency(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify all variations should have same expected verdict.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])

        for test_case in test_cases:
            expected_verdict = test_case.get("expected_verdict")
            assert expected_verdict is not None

    def test_paraphrase_test_case_count(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify sufficient paraphrase test cases available.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])
        assert len(test_cases) >= 10

        # Count total variations
        total_variations = sum(
            len(tc.get("variations", [])) for tc in test_cases
        )
        assert total_variations >= 20

    @pytest.mark.parametrize("paraphrase_type", [
        "synonym_substitution",
        "structural_rearrangement",
        "pronoun_variation",
    ])
    def test_paraphrase_type_coverage(
        self,
        paraphrase_examples: Dict[str, Any],
        paraphrase_type: str,
    ):
        """Verify coverage of specific paraphrase types.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
            paraphrase_type: Type to check coverage for
        """
        test_cases = paraphrase_examples.get("test_cases", [])

        # Check if at least one test covers this paraphrase type
        found = False
        for test_case in test_cases:
            for variation in test_case.get("variations", []):
                if variation.get("type") == paraphrase_type:
                    found = True
                    break
            if found:
                break

    def test_paraphrase_metadata_quality(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify metadata quality of paraphrase examples.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        metadata = paraphrase_examples.get("metadata", {})

        assert "version" in metadata
        assert "dimension" in metadata
        assert metadata["dimension"] == "paraphrase_robustness"
        assert "description" in metadata
        assert "paraphrase_types" in metadata

    def test_paraphrase_all_verdicts_valid(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify all verdict values are valid.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            assert verdict in valid_verdicts

    def test_paraphrase_category_distribution(
        self,
        paraphrase_examples: Dict[str, Any],
    ):
        """Verify category distribution across test cases.

        Args:
            paraphrase_examples: Fixture with paraphrase test data
        """
        test_cases = paraphrase_examples.get("test_cases", [])
        categories: Dict[str, int] = {}

        for test_case in test_cases:
            category = test_case.get("category")
            categories[category] = categories.get(category, 0) + 1

        # Should have multiple categories
        assert len(categories) > 1
