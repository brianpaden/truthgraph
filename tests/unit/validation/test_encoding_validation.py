"""Unit tests for encoding validation."""

import pytest

from truthgraph.validation import ValidationStatus
from truthgraph.validation.validators import validate_encoding


class TestValidEncoding:
    """Test valid encoding scenarios."""

    def test_simple_ascii_text(self):
        """Test simple ASCII text passes."""
        result = validate_encoding("The Earth is round")
        assert result.status == ValidationStatus.VALID
        assert result.error_code is None

    def test_utf8_with_accents(self):
        """Test UTF-8 text with accented characters."""
        result = validate_encoding("café résumé naïve")
        assert result.status == ValidationStatus.VALID

    def test_utf8_with_emoji(self):
        """Test UTF-8 text with emoji."""
        result = validate_encoding("The Earth 🌍 is round 🌎")
        assert result.status == ValidationStatus.VALID

    def test_greek_characters(self):
        """Test Greek characters."""
        result = validate_encoding("Η Γη είναι στρογγυλή")
        assert result.status == ValidationStatus.VALID

    def test_arabic_characters(self):
        """Test Arabic characters (RTL)."""
        result = validate_encoding("الأرض كروية")
        assert result.status == ValidationStatus.VALID

    def test_chinese_characters(self):
        """Test Chinese characters."""
        result = validate_encoding("地球是圆的")
        assert result.status == ValidationStatus.VALID

    def test_mixed_scripts(self):
        """Test mixed scripts (multilingual)."""
        result = validate_encoding("Earth (English), 地球 (Chinese), Γη (Greek)")
        assert result.status == ValidationStatus.VALID

    def test_mathematical_symbols(self):
        """Test mathematical symbols."""
        result = validate_encoding("E = mc² and π ≈ 3.14159")
        assert result.status == ValidationStatus.VALID


class TestInvalidEncoding:
    """Test invalid encoding scenarios."""

    def test_replacement_character(self):
        """Test Unicode replacement character is detected."""
        result = validate_encoding("Invalid \ufffd character")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "REPLACEMENT_CHAR"
        assert result.error_type == "encoding"

    def test_multiple_replacement_characters(self):
        """Test multiple replacement characters."""
        result = validate_encoding("Multiple \ufffd invalid \ufffd characters")
        assert result.status == ValidationStatus.INVALID
        assert result.error_code == "REPLACEMENT_CHAR"
        assert "replacement_char_count" in result.metadata
        assert result.metadata["replacement_char_count"] == 2


class TestEncodingMetadata:
    """Test encoding validation metadata."""

    def test_valid_metadata(self):
        """Test valid encoding includes metadata."""
        result = validate_encoding("Valid UTF-8 text")
        assert result.metadata is not None
        assert "encoding" in result.metadata or "encoding_valid" in result.metadata

    def test_invalid_metadata(self):
        """Test invalid encoding includes error metadata."""
        result = validate_encoding("Invalid \ufffd text")
        assert result.metadata is not None
        assert "replacement_char_count" in result.metadata
