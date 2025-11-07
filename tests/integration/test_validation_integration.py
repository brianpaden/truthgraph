"""Integration tests for validation layer.

Tests the complete validation flow including integration with API handlers
and edge case scenarios.
"""

import pytest

from truthgraph.validation import ClaimValidator, ValidationStatus


class TestValidationIntegration:
    """Test complete validation integration."""

    def test_end_to_end_valid_claim(self):
        """Test end-to-end validation of valid claim."""
        validator = ClaimValidator()
        claim = "The Earth orbits the Sun in an elliptical path"

        result = validator.validate(claim)

        assert result.status == ValidationStatus.VALID
        assert result.normalized_text is not None
        assert result.normalized_text == claim  # ASCII text unchanged
        assert not result.has_warnings()
        assert result.is_valid()

    def test_end_to_end_invalid_claim(self):
        """Test end-to-end validation of invalid claim."""
        validator = ClaimValidator()
        claim = ""

        result = validator.validate(claim)

        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "EMPTY_TEXT"
        assert result.error_type == "structure"
        assert result.message is not None
        assert result.suggestion is not None
        assert result.is_invalid()

    def test_end_to_end_warning_claim(self):
        """Test end-to-end validation of claim with warnings."""
        validator = ClaimValidator()
        claim = "Earth orbits"  # Minimal context

        result = validator.validate(claim)

        assert result.status == ValidationStatus.WARNING
        assert result.has_warnings()
        assert len(result.warnings) > 0
        assert result.normalized_text is not None
        assert result.is_valid()  # WARNING is still valid


class TestMultilingualIntegration:
    """Test integration with multilingual claims."""

    def test_greek_claim_integration(self):
        """Test Greek claim full validation."""
        validator = ClaimValidator()
        claim = "Η Γη είναι στρογγυλή και περιστρέφεται γύρω από τον Ήλιο"

        result = validator.validate(claim)

        # Will have warning due to high non-ASCII ratio
        assert result.status == ValidationStatus.WARNING
        assert result.normalized_text is not None
        # Greek should be preserved
        assert "Γη" in result.normalized_text
        assert "Ήλιο" in result.normalized_text

    def test_arabic_claim_integration(self):
        """Test Arabic claim full validation."""
        validator = ClaimValidator()
        claim = "الأرض كروية وتدور حول الشمس"

        result = validator.validate(claim)

        assert result.status == ValidationStatus.WARNING
        assert result.normalized_text is not None
        # Verify RTL text is detected in metadata
        assert result.metadata.get("has_rtl") is True

    def test_chinese_claim_integration(self):
        """Test Chinese claim full validation."""
        validator = ClaimValidator()
        claim = "地球是圆的并绕太阳运行"

        result = validator.validate(claim)

        # Chinese tokenization treats characters differently
        # Status could be WARNING or INVALID depending on word splitting
        assert result.status in [ValidationStatus.WARNING, ValidationStatus.INVALID]
        if result.is_valid():
            assert result.normalized_text is not None

    def test_mixed_language_claim(self):
        """Test mixed language claim."""
        validator = ClaimValidator()
        claim = "The Earth (地球 in Chinese, Γη in Greek) is round"

        result = validator.validate(claim)

        # Should process successfully
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert result.normalized_text is not None


class TestEdgeCaseCorpus:
    """Test validation with edge case corpus.

    These tests simulate processing the 34-claim edge case corpus
    mentioned in the requirements.
    """

    @pytest.fixture
    def edge_case_claims(self):
        """Edge case claims covering various scenarios."""
        return [
            # Valid claims
            "The Earth orbits the Sun",
            "Water is composed of hydrogen and oxygen",
            "Climate change is caused by greenhouse gases",

            # Minimal context (WARNING)
            "Earth orbits",
            "Water boils",

            # Long claims (WARNING)
            "This is a very long claim " + "with many words " * 50,

            # Multilingual (WARNING)
            "Η Γη είναι στρογγυλή",
            "الأرض كروية",
            "地球是圆的",

            # With emoji (VALID)
            "The Earth 🌍 is round",
            "Climate change 🌡️ is real",

            # With numbers and symbols
            "Water boils at 100°C",
            "Einstein's E = mc² equation",
            "Pi π ≈ 3.14159",

            # Invalid claims
            "",
            "   ",
            "Earth",  # Single word
            "!!!",  # No alphanumeric
            "Text with \ufffd replacement character",

            # Edge cases
            "A B",  # Exactly 2 words (minimal)
            "A B C",  # Exactly 3 words (no warning)
            "Café résumé naïve",  # Accented characters
            "שלום עולם",  # Hebrew (RTL)
            "Mix of English and 中文",  # Mixed scripts
        ]

    def test_edge_case_corpus_no_crashes(self, edge_case_claims):
        """Test all edge cases process without crashes."""
        validator = ClaimValidator()

        for claim in edge_case_claims:
            try:
                result = validator.validate(claim)
                # Should always return a result
                assert result is not None
                assert result.status in [
                    ValidationStatus.VALID,
                    ValidationStatus.WARNING,
                    ValidationStatus.INVALID,
                ]
            except Exception as e:
                pytest.fail(f"Validation crashed on claim '{claim}': {e}")

    def test_edge_case_corpus_categories(self, edge_case_claims):
        """Test edge cases are categorized correctly."""
        validator = ClaimValidator()
        results = validator.validate_batch(edge_case_claims)

        valid_count = sum(1 for r in results if r.status == ValidationStatus.VALID)
        warning_count = sum(1 for r in results if r.status == ValidationStatus.WARNING)
        invalid_count = sum(1 for r in results if r.status == ValidationStatus.INVALID)

        # Should have mix of all categories
        assert valid_count > 0
        assert warning_count > 0
        assert invalid_count > 0

        # Total should match input
        assert valid_count + warning_count + invalid_count == len(edge_case_claims)

    def test_edge_case_normalized_text_always_present(self, edge_case_claims):
        """Test normalized text is present for valid/warning claims."""
        validator = ClaimValidator()

        for claim in edge_case_claims:
            result = validator.validate(claim)
            if result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]:
                assert result.normalized_text is not None
                # Normalized text should not be empty for valid claims
                if claim.strip():
                    assert len(result.normalized_text) > 0


class TestPerformance:
    """Test validation performance requirements."""

    def test_validation_under_10ms(self):
        """Test validation completes in <10ms per claim."""
        import time

        validator = ClaimValidator()
        claim = "The Earth orbits the Sun in an elliptical path"

        # Warm up
        validator.validate(claim)

        # Measure
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            validator.validate(claim)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        # Should be well under 10ms per claim
        assert avg_time_ms < 10.0, f"Validation took {avg_time_ms:.2f}ms (target: <10ms)"

    def test_batch_validation_scales(self):
        """Test batch validation scales linearly."""
        import time

        validator = ClaimValidator()
        claims = ["The Earth orbits the Sun"] * 100

        # Warm up
        validator.validate_batch(claims[:10])

        # Measure batch
        start = time.perf_counter()
        results = validator.validate_batch(claims)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / len(claims)

        assert len(results) == len(claims)
        assert avg_time_ms < 10.0, f"Batch avg: {avg_time_ms:.2f}ms per claim"


class TestValidationMetadataFlow:
    """Test validation metadata flows through the system."""

    def test_metadata_includes_all_checks(self):
        """Test metadata includes information from all validators."""
        validator = ClaimValidator()
        claim = "The Earth orbits the Sun"

        result = validator.validate(claim)

        # Should have metadata from all validators
        assert "word_count" in result.metadata
        assert "estimated_tokens" in result.metadata
        assert "non_ascii_ratio" in result.metadata
        assert "has_rtl" in result.metadata
        assert "has_emoji" in result.metadata

    def test_metadata_encoding_info(self):
        """Test metadata includes encoding information."""
        validator = ClaimValidator()
        claim = "The Earth is round"

        result = validator.validate(claim)

        # Should have encoding validation info
        assert "encoding_valid" in result.metadata or "encoding" in result.metadata

    def test_metadata_normalization_info(self):
        """Test metadata includes normalization information."""
        validator = ClaimValidator()
        # Use valid claim with multiple words
        claim = "café test example"

        result = validator.validate(claim)

        assert result.status == ValidationStatus.VALID
        assert "normalized" in result.metadata
        assert result.metadata["normalized"] is True


class TestValidationResultAPI:
    """Test ValidationResult API methods."""

    def test_is_valid_method(self):
        """Test is_valid() method."""
        validator = ClaimValidator()

        valid_result = validator.validate("The Earth is round")
        assert valid_result.is_valid() is True

        warning_result = validator.validate("Earth orbits")
        assert warning_result.is_valid() is True  # WARNING is still valid

        invalid_result = validator.validate("")
        assert invalid_result.is_valid() is False

    def test_is_invalid_method(self):
        """Test is_invalid() method."""
        validator = ClaimValidator()

        valid_result = validator.validate("The Earth is round")
        assert valid_result.is_invalid() is False

        invalid_result = validator.validate("")
        assert invalid_result.is_invalid() is True

    def test_has_warnings_method(self):
        """Test has_warnings() method."""
        validator = ClaimValidator()

        valid_result = validator.validate("The Earth is round")
        assert valid_result.has_warnings() is False

        warning_result = validator.validate("Earth orbits")
        assert warning_result.has_warnings() is True

    def test_to_dict_method(self):
        """Test to_dict() serialization."""
        validator = ClaimValidator()
        result = validator.validate("The Earth is round")

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "status" in result_dict
        assert "metadata" in result_dict
        assert "normalized_text" in result_dict
        assert "warnings" in result_dict
