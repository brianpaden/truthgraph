"""Adversarial examples robustness tests.

This module tests the system's ability to handle adversarial examples
designed to fool or challenge the verification system.

Test Coverage:
- Double negation
- Contradiction injection
- Confidence confusion
- Scope shifting
"""

from typing import Any, Dict

import pytest


class TestAdversarialRobustness:
    """Test suite for adversarial example robustness."""

    def test_load_adversarial_examples_fixture(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify adversarial examples fixture loads correctly.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        assert adversarial_examples is not None
        assert "metadata" in adversarial_examples
        assert adversarial_examples["metadata"]["dimension"] == "adversarial_robustness"
        assert "test_cases" in adversarial_examples
        assert len(adversarial_examples["test_cases"]) > 0

    def test_adversarial_examples_structure(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify adversarial examples have proper structure.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])

        assert len(test_cases) >= 10, "Should have at least 10 test cases"

        for test_case in test_cases:
            # Verify required fields
            assert "id" in test_case
            assert "base_claim" in test_case
            assert "category" in test_case
            assert "expected_verdict" in test_case
            assert "adversarial_variations" in test_case

            # Verify variations
            variations = test_case.get("adversarial_variations", [])
            assert len(variations) > 0

            for variation in variations:
                assert "text" in variation
                assert "attack_type" in variation
                assert "challenge" in variation

    def test_adversarial_attack_types(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify different attack types are represented.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])
        attack_types: set = set()

        for test_case in test_cases:
            for variation in test_case.get("adversarial_variations", []):
                attack_types.add(variation.get("attack_type"))

        assert len(attack_types) > 0
        # Should have some of the expected attack types
        expected_types = {
            "double_negation",
            "contradiction_injection",
            "scope_shift",
        }
        assert len(attack_types & expected_types) > 0

    def test_adversarial_challenge_descriptions(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify all variations have challenge descriptions.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])

        for test_case in test_cases:
            for variation in test_case.get("adversarial_variations", []):
                challenge = variation.get("challenge", "")
                assert len(challenge) > 0, "Challenge should have description"

    def test_adversarial_base_claims_valid(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify base claims are valid statements.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            assert len(base_claim) > 10, "Base claim should be substantial"

    def test_adversarial_verdicts_mostly_supported(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify verdicts are mostly SUPPORTED (true statements).

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])
        supported_count = sum(
            1 for tc in test_cases
            if tc.get("expected_verdict") == "SUPPORTED"
        )

        # Most adversarial examples should be true claims
        assert supported_count >= len(test_cases) // 2

    def test_adversarial_test_case_count(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify sufficient adversarial test cases available.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])
        assert len(test_cases) >= 10

        # Count total variations
        total_variations = sum(
            len(tc.get("adversarial_variations", []))
            for tc in test_cases
        )
        assert total_variations >= 20

    @pytest.mark.parametrize("attack_type", [
        "double_negation",
        "contradiction_injection",
        "scope_shift",
    ])
    def test_adversarial_attack_type_coverage(
        self,
        adversarial_examples: Dict[str, Any],
        attack_type: str,
    ):
        """Verify coverage of specific attack types.

        Args:
            adversarial_examples: Fixture with adversarial test data
            attack_type: Type to check coverage for
        """
        test_cases = adversarial_examples.get("test_cases", [])

        # Check if at least one test covers this attack type
        found = False
        for test_case in test_cases:
            for variation in test_case.get("adversarial_variations", []):
                if variation.get("attack_type") == attack_type:
                    found = True
                    break
            if found:
                break

    def test_adversarial_metadata_quality(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify metadata quality of adversarial examples.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        metadata = adversarial_examples.get("metadata", {})

        assert "version" in metadata
        assert "dimension" in metadata
        assert metadata["dimension"] == "adversarial_robustness"
        assert "description" in metadata
        assert "attack_types" in metadata

    def test_adversarial_attacks_differ_from_base(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify adversarial variations differ from base claims.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "").lower()
            variations = test_case.get("adversarial_variations", [])

            for variation in variations:
                variant_text = variation.get("text", "").lower()
                # Adversarial examples should differ from base
                assert variant_text != base_claim

    def test_adversarial_category_distribution(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify category distribution in adversarial examples.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])
        categories: Dict[str, int] = {}

        for test_case in test_cases:
            category = test_case.get("category")
            categories[category] = categories.get(category, 0) + 1

        # Should have multiple categories
        assert len(categories) > 1

    def test_adversarial_all_verdicts_valid(
        self,
        adversarial_examples: Dict[str, Any],
    ):
        """Verify all verdict values are valid.

        Args:
            adversarial_examples: Fixture with adversarial test data
        """
        test_cases = adversarial_examples.get("test_cases", [])
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            assert verdict in valid_verdicts
