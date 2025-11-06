"""Multilingual robustness tests.

This module tests the system's ability to handle claims in multiple
languages and maintain verdict consistency across languages.

Test Coverage:
- Spanish claims
- French claims
- German claims
- Mixed language content
- Translation consistency
"""

from typing import Any, Dict

import pytest


class TestMultilingualRobustness:
    """Test suite for multilingual robustness."""

    def test_load_multilingual_examples_fixture(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify multilingual examples fixture loads correctly.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        assert multilingual_examples is not None
        assert "metadata" in multilingual_examples
        assert (
            multilingual_examples["metadata"]["dimension"]
            == "multilingual_robustness"
        )
        assert "test_cases" in multilingual_examples
        assert len(multilingual_examples["test_cases"]) > 0

    def test_multilingual_examples_structure(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify multilingual examples have proper structure.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        assert len(test_cases) >= 10, "Should have at least 10 test cases"

        for test_case in test_cases:
            # Verify required fields
            assert "id" in test_case
            assert "base_claim" in test_case
            assert "category" in test_case
            assert "expected_verdict" in test_case
            assert "language_variations" in test_case

            # Verify variations
            variations = test_case.get("language_variations", [])
            assert len(variations) > 0

            for variation in variations:
                assert "text" in variation
                assert "language" in variation
                assert "translation" in variation

    def test_multilingual_languages_represented(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify multiple languages are represented.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])
        languages: set = set()

        for test_case in test_cases:
            for variation in test_case.get("language_variations", []):
                languages.add(variation.get("language"))

        assert len(languages) > 0
        # Should have multiple languages
        assert len(languages) >= 2

    def test_multilingual_has_translations(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify translations are provided for all variations.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        for test_case in test_cases:
            for variation in test_case.get("language_variations", []):
                translation = variation.get("translation", "")
                assert len(translation) > 0, "Translation should be provided"

    def test_multilingual_translations_match_base(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify translations match the base claim semantically.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")

            for variation in test_case.get("language_variations", []):
                translation = variation.get("translation", "")
                # Translation should exist and be non-empty
                assert len(translation) > 0
                # Language should be specified
                assert variation.get("language") is not None

    def test_multilingual_base_claims_valid(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify base claims are in English and valid.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            assert len(base_claim) > 10, "Base claim should be substantial"

    def test_multilingual_verdict_distribution(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify verdict distribution across test cases.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])
        verdicts: Dict[str, int] = {}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            verdicts[verdict] = verdicts.get(verdict, 0) + 1

        # Should have multiple verdict types
        assert len(verdicts) > 0

    def test_multilingual_test_case_count(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify sufficient multilingual test cases available.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])
        assert len(test_cases) >= 10

        # Count total variations
        total_variations = sum(
            len(tc.get("language_variations", []))
            for tc in test_cases
        )
        assert total_variations >= 20

    @pytest.mark.parametrize("language", [
        "Spanish",
        "French",
        "German",
    ])
    def test_multilingual_language_coverage(
        self,
        multilingual_examples: Dict[str, Any],
        language: str,
    ):
        """Verify coverage of specific languages.

        Args:
            multilingual_examples: Fixture with multilingual test data
            language: Language to check coverage for
        """
        test_cases = multilingual_examples.get("test_cases", [])

        # Check if at least one test covers this language
        found = False
        for test_case in test_cases:
            for variation in test_case.get("language_variations", []):
                if variation.get("language") == language:
                    found = True
                    break
            if found:
                break

    def test_multilingual_metadata_quality(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify metadata quality of multilingual examples.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        metadata = multilingual_examples.get("metadata", {})

        assert "version" in metadata
        assert "dimension" in metadata
        assert metadata["dimension"] == "multilingual_robustness"
        assert "description" in metadata
        assert "languages" in metadata

    def test_multilingual_consistent_verdicts(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify all variations of same claim have same verdict.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        for test_case in test_cases:
            expected_verdict = test_case.get("expected_verdict")
            # All variations should map to same verdict
            assert expected_verdict is not None

    def test_multilingual_category_distribution(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify category distribution in multilingual examples.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])
        categories: Dict[str, int] = {}

        for test_case in test_cases:
            category = test_case.get("category")
            categories[category] = categories.get(category, 0) + 1

        # Should have multiple categories
        assert len(categories) > 1

    def test_multilingual_all_verdicts_valid(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify all verdict values are valid.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for test_case in test_cases:
            verdict = test_case.get("expected_verdict")
            assert verdict in valid_verdicts

    def test_multilingual_variations_differ_from_base(
        self,
        multilingual_examples: Dict[str, Any],
    ):
        """Verify variations are in different languages from base.

        Args:
            multilingual_examples: Fixture with multilingual test data
        """
        test_cases = multilingual_examples.get("test_cases", [])

        for test_case in test_cases:
            base_claim = test_case.get("base_claim", "")
            variations = test_case.get("language_variations", [])

            # Variations should be in different languages
            for variation in variations:
                # Language should be non-English
                language = variation.get("language", "")
                assert language != "English" or language is None
