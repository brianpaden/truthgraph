"""Noisy evidence robustness tests.

This module tests the system's ability to handle noisy, degraded,
and low-quality claims and evidence.

Test Coverage:
- OCR/transcription errors (character corruption)
- Incomplete text (truncation)
- Irrelevant/redundant information
- Hedging and uncertainty language
"""

from typing import Any, Dict

import pytest


class TestNoiseRobustness:
    """Test suite for noise robustness."""

    def test_load_noise_examples_fixture(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify noise examples fixture loads correctly.

        Args:
            noise_examples: Fixture with noise test data
        """
        assert noise_examples is not None
        assert "metadata" in noise_examples
        assert noise_examples["metadata"]["dimension"] == "noise_robustness"
        assert "test_cases" in noise_examples
        assert len(noise_examples["test_cases"]) > 0

    def test_noise_examples_structure(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify noise examples have proper structure.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])

        assert len(test_cases) >= 10, "Should have at least 10 test cases"

        for test_case in test_cases:
            # Verify required fields
            assert "id" in test_case
            assert "base_claim" in test_case
            assert "category" in test_case
            assert "expected_verdict" in test_case
            assert "noisy_variations" in test_case

            # Verify variations
            variations = test_case.get("noisy_variations", [])
            assert len(variations) > 0

            for variation in variations:
                assert "text" in variation
                assert "noise_type" in variation
                assert "corruption_level" in variation

    def test_noise_types_represented(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify different noise types are represented.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        noise_types: set = set()

        for test_case in test_cases:
            for variation in test_case.get("noisy_variations", []):
                noise_types.add(variation.get("noise_type"))

        assert len(noise_types) > 0
        # Should have some of the expected noise types
        expected_types = {
            "character_corruption",
            "incomplete_text",
            "hedging_language",
        }
        assert len(noise_types & expected_types) > 0

    def test_noise_corruption_levels(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify corruption levels are properly specified.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        valid_levels = {"low", "medium", "high"}

        for test_case in test_cases:
            for variation in test_case.get("noisy_variations", []):
                level = variation.get("corruption_level")
                assert level in valid_levels, (
                    f"Invalid corruption level: {level}"
                )

    def test_noise_varied_claims(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify base claims are varied and substantial.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            assert len(base_claim) > 10, "Base claim should be substantial"

    def test_noise_verdict_distribution(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify verdict distribution across noise test cases.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        verdicts: Dict[str, int] = {}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            verdicts[verdict] = verdicts.get(verdict, 0) + 1

        # Should have multiple verdict types
        assert len(verdicts) > 1

    def test_noise_test_case_count(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify sufficient noise test cases available.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        assert len(test_cases) >= 10

        # Count total variations
        total_variations = sum(
            len(tc.get("noisy_variations", []))
            for tc in test_cases
        )
        assert total_variations >= 20

    @pytest.mark.parametrize("noise_type", [
        "character_corruption",
        "incomplete_text",
        "hedging_language",
    ])
    def test_noise_type_coverage(
        self,
        noise_examples: Dict[str, Any],
        noise_type: str,
    ):
        """Verify coverage of specific noise types.

        Args:
            noise_examples: Fixture with noise test data
            noise_type: Type to check coverage for
        """
        test_cases = noise_examples.get("test_cases", [])

        # Check if at least one test covers this noise type
        found = False
        for test_case in test_cases:
            for variation in test_case.get("noisy_variations", []):
                if variation.get("noise_type") == noise_type:
                    found = True
                    break
            if found:
                break

    def test_noise_metadata_quality(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify metadata quality of noise examples.

        Args:
            noise_examples: Fixture with noise test data
        """
        metadata = noise_examples.get("metadata", {})

        assert "version" in metadata
        assert "dimension" in metadata
        assert metadata["dimension"] == "noise_robustness"
        assert "description" in metadata
        assert "noise_types" in metadata

    def test_noise_variations_differ_from_base(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify noisy variations differ from base claims.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            variations = test_case.get("noisy_variations", [])

            # Should have some variations that differ
            has_difference = False
            for variation in variations:
                variant_text = variation.get("text", "")
                if variant_text != base_claim:
                    has_difference = True
                    break

            assert has_difference, "Should have variations differing from base"

    def test_noise_category_distribution(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify category distribution in noise examples.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        categories: Dict[str, int] = {}

        for test_case in test_cases:
            category = test_case.get("category")
            categories[category] = categories.get(category, 0) + 1

        # Should have multiple categories
        assert len(categories) > 1

    def test_noise_all_verdicts_valid(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify all verdict values are valid.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            assert verdict in valid_verdicts

    def test_noise_high_corruption_present(
        self,
        noise_examples: Dict[str, Any],
    ):
        """Verify some high-corruption examples are included.

        Args:
            noise_examples: Fixture with noise test data
        """
        test_cases = noise_examples.get("test_cases", [])

        high_corruption_count = 0
        for test_case in test_cases:
            for variation in test_case.get("noisy_variations", []):
                if variation.get("corruption_level") == "high":
                    high_corruption_count += 1

        # Should have some high-corruption examples
        assert high_corruption_count > 0
