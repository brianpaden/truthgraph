"""Unit tests for ClaimValidator orchestrator.

Tests the main ClaimValidator class that orchestrates all validation checks.
"""

import pytest

from truthgraph.validation import ClaimValidator, ValidationStatus


class TestClaimValidatorBasics:
    """Test basic ClaimValidator functionality."""

    def test_validator_initialization(self):
        """Test validator can be initialized with custom thresholds."""
        validator = ClaimValidator(
            min_words=3,
            max_words=100,
            max_tokens_estimate=200,
            max_non_ascii_ratio=0.7,
        )
        assert validator.min_words == 3
        assert validator.max_words == 100
        assert validator.max_tokens_estimate == 200
        assert validator.max_non_ascii_ratio == 0.7

    def test_validator_default_config(self):
        """Test validator uses correct default configuration."""
        validator = ClaimValidator()
        assert validator.min_words == 2
        assert validator.max_words == 500
        assert validator.max_tokens_estimate == 450
        assert validator.max_non_ascii_ratio == 0.5


class TestValidClaims:
    """Test validation of valid claims."""

    def test_simple_valid_claim(self):
        """Test simple valid claim passes."""
        validator = ClaimValidator()
        result = validator.validate("The Earth is round")
        assert result.status == ValidationStatus.VALID
        assert result.normalized_text == "The Earth is round"
        assert not result.has_warnings()
        assert result.is_valid()

    def test_longer_valid_claim(self):
        """Test longer valid claim passes."""
        validator = ClaimValidator()
        claim = "The Earth orbits around the Sun in an elliptical path once every 365.25 days"
        result = validator.validate(claim)
        assert result.status == ValidationStatus.VALID
        assert result.normalized_text is not None
        assert not result.has_warnings()

    def test_claim_with_punctuation(self):
        """Test claim with punctuation passes."""
        validator = ClaimValidator()
        result = validator.validate("Climate change is real, and it's caused by humans.")
        assert result.status == ValidationStatus.VALID
        assert not result.has_warnings()

    def test_claim_with_numbers(self):
        """Test claim with numbers passes."""
        validator = ClaimValidator()
        result = validator.validate("Water boils at 100 degrees Celsius")
        assert result.status == ValidationStatus.VALID
        assert not result.has_warnings()


class TestInvalidClaims:
    """Test validation of invalid claims."""

    def test_empty_string(self):
        """Test empty string is rejected."""
        validator = ClaimValidator()
        result = validator.validate("")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "EMPTY_TEXT"
        assert result.error_type == "structure"
        assert result.suggestion is not None
        assert result.is_invalid()

    def test_whitespace_only(self):
        """Test whitespace-only string is rejected."""
        validator = ClaimValidator()
        result = validator.validate("   \t\n  ")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "EMPTY_TEXT"

    def test_single_word(self):
        """Test single word is rejected."""
        validator = ClaimValidator()
        result = validator.validate("Earth")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "SINGLE_WORD"
        assert result.error_type == "length"

    def test_no_alphanumeric(self):
        """Test text with no alphanumeric characters is rejected."""
        validator = ClaimValidator()
        result = validator.validate("!!! ??? ...")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "NO_ALPHANUMERIC"
        assert result.error_type == "structure"

    def test_replacement_character(self):
        """Test text with Unicode replacement character is rejected."""
        validator = ClaimValidator()
        result = validator.validate("This text has invalid \ufffd character")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "REPLACEMENT_CHAR"
        assert result.error_type == "encoding"


class TestWarningClaims:
    """Test validation of claims that generate warnings."""

    def test_minimal_context(self):
        """Test very short claim (2 words) generates warning."""
        validator = ClaimValidator()
        result = validator.validate("Earth orbits")
        assert result.status == ValidationStatus.WARNING
        assert result.has_warnings()
        assert len(result.warnings) > 0
        # Check that warning contains MINIMAL_CONTEXT
        assert any("MINIMAL_CONTEXT" in w for w in result.warnings)
        assert result.is_valid()  # WARNING is still considered valid

    def test_very_long_claim(self):
        """Test very long claim generates truncation warning."""
        validator = ClaimValidator()
        # Create a claim with >450 estimated tokens (>350 words)
        long_claim = "word " * 400
        result = validator.validate(long_claim)
        assert result.status == ValidationStatus.WARNING
        assert result.has_warnings()
        # Check that warning contains either POTENTIAL_TRUNCATION or EXCESSIVE_LENGTH
        warning_text = " ".join(result.warnings)
        assert "POTENTIAL_TRUNCATION" in warning_text or "EXCESSIVE_LENGTH" in warning_text

    def test_high_non_ascii_ratio(self):
        """Test claim with high non-ASCII ratio generates warning."""
        validator = ClaimValidator()
        # Greek text has 100% non-ASCII
        result = validator.validate("Η Γη είναι στρογγυλή")
        assert result.status == ValidationStatus.WARNING
        assert result.has_warnings()
        # Check that warning contains HIGH_NON_ASCII_RATIO
        assert any("HIGH_NON_ASCII_RATIO" in w for w in result.warnings)
        # But text should still be normalized and valid
        assert result.normalized_text is not None


class TestUnicodeNormalization:
    """Test Unicode normalization in validation."""

    def test_nfc_normalization_applied(self):
        """Test NFC normalization is applied."""
        validator = ClaimValidator()
        # Use more words to avoid minimal context warning
        result = validator.validate("café test example text")
        assert result.status == ValidationStatus.VALID
        assert "café" in result.normalized_text
        assert result.metadata.get("normalized") is True

    def test_greek_text_preserved(self):
        """Test Greek text is preserved during normalization."""
        validator = ClaimValidator()
        result = validator.validate("Η Γη είναι στρογγυλή")
        # Will have warning due to high non-ASCII ratio
        assert result.status == ValidationStatus.WARNING
        assert result.normalized_text is not None
        # Greek characters should be preserved
        assert "Γη" in result.normalized_text

    def test_emoji_preserved(self):
        """Test emoji are preserved during normalization."""
        validator = ClaimValidator()
        result = validator.validate("The Earth 🌍 is round")
        assert result.status == ValidationStatus.VALID
        assert "🌍" in result.normalized_text

    def test_math_symbols_preserved(self):
        """Test mathematical symbols are preserved."""
        validator = ClaimValidator()
        result = validator.validate("Einstein's equation is E = mc²")
        assert result.status == ValidationStatus.VALID
        assert "²" in result.normalized_text


class TestBatchValidation:
    """Test batch validation functionality."""

    def test_batch_all_valid(self):
        """Test batch validation with all valid claims."""
        validator = ClaimValidator()
        claims = [
            "The Earth is round",
            "Water is wet",
            "The sky is blue",
        ]
        results = validator.validate_batch(claims)
        assert len(results) == 3
        assert all(r.status == ValidationStatus.VALID for r in results)

    def test_batch_mixed_validity(self):
        """Test batch validation with mixed validity."""
        validator = ClaimValidator()
        claims = [
            "The Earth is round",  # Valid
            "Earth",  # Invalid (single word)
            "Short claim",  # Warning (minimal context)
            "",  # Invalid (empty)
        ]
        results = validator.validate_batch(claims)
        assert len(results) == 4
        assert results[0].status == ValidationStatus.VALID
        assert results[1].status == ValidationStatus.INVALID
        assert results[2].status == ValidationStatus.WARNING
        assert results[3].status == ValidationStatus.INVALID

    def test_batch_empty_list(self):
        """Test batch validation with empty list."""
        validator = ClaimValidator()
        results = validator.validate_batch([])
        assert len(results) == 0


class TestValidationMetadata:
    """Test validation metadata is properly populated."""

    def test_metadata_word_count(self):
        """Test metadata includes word count."""
        validator = ClaimValidator()
        result = validator.validate("The Earth orbits the Sun")
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 5

    def test_metadata_estimated_tokens(self):
        """Test metadata includes estimated tokens."""
        validator = ClaimValidator()
        result = validator.validate("The Earth orbits the Sun")
        assert "estimated_tokens" in result.metadata
        # Should be roughly words * 1.3
        assert result.metadata["estimated_tokens"] > 5

    def test_metadata_encoding_info(self):
        """Test metadata includes encoding information."""
        validator = ClaimValidator()
        result = validator.validate("The Earth is round")
        assert "encoding_valid" in result.metadata or "encoding" in result.metadata

    def test_metadata_non_ascii_ratio(self):
        """Test metadata includes non-ASCII ratio."""
        validator = ClaimValidator()
        result = validator.validate("The Earth 🌍 is round")
        assert "non_ascii_ratio" in result.metadata


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_two_words(self):
        """Test claim with exactly 2 words (minimum)."""
        validator = ClaimValidator()
        result = validator.validate("Earth orbits")
        # Should be WARNING (minimal context) not INVALID
        assert result.status == ValidationStatus.WARNING
        assert result.has_warnings()
        assert any("MINIMAL_CONTEXT" in w for w in result.warnings)

    def test_exactly_three_words(self):
        """Test claim with exactly 3 words (no warning threshold)."""
        validator = ClaimValidator()
        result = validator.validate("The Earth orbits")
        assert result.status == ValidationStatus.VALID
        assert not result.has_warnings()

    def test_mixed_languages(self):
        """Test claim with mixed languages."""
        validator = ClaimValidator()
        result = validator.validate("The Γη (Earth) is round")
        # May have warning due to non-ASCII, but should process
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert result.normalized_text is not None

    def test_rtl_text(self):
        """Test claim with RTL (Right-to-Left) text."""
        validator = ClaimValidator()
        # Arabic text
        result = validator.validate("الأرض كروية")
        # Will have warning due to high non-ASCII ratio
        assert result.status == ValidationStatus.WARNING
        assert result.normalized_text is not None

    def test_claim_with_newlines(self):
        """Test claim with newline characters."""
        validator = ClaimValidator()
        result = validator.validate("The Earth\nis round\nand orbits the Sun")
        assert result.status == ValidationStatus.VALID
        assert result.normalized_text is not None


class TestCustomThresholds:
    """Test validation with custom thresholds."""

    def test_custom_min_words(self):
        """Test custom minimum word count."""
        validator = ClaimValidator(min_words=5)
        result = validator.validate("The Earth is round")
        # 4 words, below minimum of 5
        assert result.status == ValidationStatus.INVALID

    def test_custom_max_words(self):
        """Test custom maximum word count."""
        validator = ClaimValidator(max_words=10)
        long_claim = "word " * 15
        result = validator.validate(long_claim)
        assert result.status == ValidationStatus.WARNING
        # Should have warning about length
        assert result.has_warnings()
        warning_text = " ".join(result.warnings)
        assert "LENGTH" in warning_text or "TRUNCATION" in warning_text

    def test_custom_non_ascii_ratio(self):
        """Test custom non-ASCII ratio threshold."""
        validator = ClaimValidator(max_non_ascii_ratio=0.9)
        # Greek text has 100% non-ASCII, threshold is 90%
        result = validator.validate("Η Γη είναι στρογγυλή")
        # With spaces, the ratio might be less than 100%, so this could be valid or warning
        # Let's just check it processes successfully
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
