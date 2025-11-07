"""Unit tests for length validation."""

import pytest

from truthgraph.validation import ValidationStatus
from truthgraph.validation.validators import validate_length


class TestValidLength:
    """Test valid length scenarios."""

    def test_normal_length(self):
        """Test normal length claim (5 words)."""
        result = validate_length("The Earth orbits the Sun")
        assert result.status == ValidationStatus.VALID
        assert result.error_code is None
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 5

    def test_medium_length(self):
        """Test medium length claim (20 words)."""
        text = "The Earth is the third planet from the Sun and the only astronomical object known to harbor life"
        result = validate_length(text)
        assert result.status == ValidationStatus.VALID

    def test_three_words(self):
        """Test three words (above minimal context threshold)."""
        result = validate_length("The Earth orbits")
        assert result.status == ValidationStatus.VALID
        assert not result.warnings


class TestInvalidLength:
    """Test invalid length scenarios."""

    def test_single_word(self):
        """Test single word is rejected."""
        result = validate_length("Earth")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "SINGLE_WORD"
        assert result.error_type == "length"
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 1

    def test_zero_words(self):
        """Test empty text is rejected."""
        result = validate_length("")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "SINGLE_WORD"


class TestWarningLength:
    """Test length warning scenarios."""

    def test_two_words_minimal_context(self):
        """Test two words generates minimal context warning."""
        result = validate_length("Earth orbits")
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "MINIMAL_CONTEXT"
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 2

    def test_very_long_tokens(self):
        """Test very long text generates truncation warning."""
        # Create text with >450 estimated tokens (>350 words)
        long_text = "word " * 400
        result = validate_length(long_text)
        assert result.status == ValidationStatus.WARNING
        assert result.error_code in ["POTENTIAL_TRUNCATION", "EXCESSIVE_LENGTH"]

    def test_excessive_word_count(self):
        """Test excessive word count generates warning."""
        # Create text with >500 words
        long_text = "word " * 550
        result = validate_length(long_text, max_words=500)
        assert result.status == ValidationStatus.WARNING
        # Could be EXCESSIVE_LENGTH or POTENTIAL_TRUNCATION depending on token count
        assert result.error_code in ["EXCESSIVE_LENGTH", "POTENTIAL_TRUNCATION"]


class TestCustomThresholds:
    """Test custom length thresholds."""

    def test_custom_min_words(self):
        """Test custom minimum word count."""
        result = validate_length("The Earth is", min_words=5)
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "SINGLE_WORD"

    def test_custom_max_words(self):
        """Test custom maximum word count."""
        long_text = "word " * 15
        result = validate_length(long_text, max_words=10)
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "EXCESSIVE_LENGTH"

    def test_custom_max_tokens(self):
        """Test custom maximum token estimate."""
        text = "word " * 100
        result = validate_length(text, max_tokens_estimate=100)
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "POTENTIAL_TRUNCATION"


class TestTokenEstimation:
    """Test token estimation logic."""

    def test_token_estimation_present(self):
        """Test token estimation is included in metadata."""
        result = validate_length("The Earth orbits the Sun")
        assert "estimated_tokens" in result.metadata
        assert result.metadata["estimated_tokens"] > 0

    def test_token_estimation_heuristic(self):
        """Test token estimation uses ~1.3x multiplier."""
        result = validate_length("word " * 100)
        word_count = result.metadata["word_count"]
        estimated_tokens = result.metadata["estimated_tokens"]
        # Should be roughly 1.3x word count
        assert estimated_tokens > word_count
        assert estimated_tokens < word_count * 1.5


class TestLengthMetadata:
    """Test length validation metadata."""

    def test_metadata_includes_word_count(self):
        """Test metadata includes word count."""
        result = validate_length("The Earth is round")
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 4

    def test_metadata_includes_estimated_tokens(self):
        """Test metadata includes estimated tokens."""
        result = validate_length("The Earth is round")
        assert "estimated_tokens" in result.metadata

    def test_metadata_includes_thresholds(self):
        """Test metadata includes threshold values on validation."""
        result = validate_length("Earth", min_words=2)
        assert "min_words" in result.metadata
        assert result.metadata["min_words"] == 2
