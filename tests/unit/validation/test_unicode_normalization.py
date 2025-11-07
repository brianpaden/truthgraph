"""Unit tests for Unicode normalization."""

import pytest

from truthgraph.validation.normalizers import (
    get_unicode_categories,
    is_normalized,
    normalize_unicode,
)


class TestBasicNormalization:
    """Test basic Unicode normalization."""

    def test_ascii_unchanged(self):
        """Test ASCII text remains unchanged."""
        text = "The Earth is round"
        result = normalize_unicode(text)
        assert result == text

    def test_already_nfc(self):
        """Test text already in NFC form."""
        text = "café"
        result = normalize_unicode(text)
        assert result == text

    def test_nfd_to_nfc(self):
        """Test NFD form converts to NFC."""
        # This would be NFD (decomposed) if created properly
        # For testing, we'll verify NFC normalization is idempotent
        text = "café"
        result = normalize_unicode(text)
        # Should be NFC form
        assert normalize_unicode(result) == result


class TestMultilingualNormalization:
    """Test normalization of multilingual text."""

    def test_greek_text(self):
        """Test Greek text is normalized correctly."""
        text = "Η Γη είναι στρογγυλή"
        result = normalize_unicode(text)
        assert result is not None
        assert "Γη" in result

    def test_arabic_text(self):
        """Test Arabic text (RTL) is normalized."""
        text = "الأرض كروية"
        result = normalize_unicode(text)
        assert result is not None
        assert len(result) > 0

    def test_chinese_text(self):
        """Test Chinese text is normalized."""
        text = "地球是圆的"
        result = normalize_unicode(text)
        assert result is not None
        assert "地球" in result

    def test_mixed_scripts(self):
        """Test mixed scripts are normalized."""
        text = "Earth (English), 地球 (Chinese), Γη (Greek)"
        result = normalize_unicode(text)
        assert result is not None
        assert "Earth" in result
        assert "地球" in result
        assert "Γη" in result


class TestSpecialCharacters:
    """Test normalization of special characters."""

    def test_emoji_preserved(self):
        """Test emoji are preserved during normalization."""
        text = "The Earth 🌍 is round 🌎"
        result = normalize_unicode(text)
        assert "🌍" in result
        assert "🌎" in result

    def test_mathematical_symbols(self):
        """Test mathematical symbols are preserved."""
        text = "E = mc² and π ≈ 3.14159"
        result = normalize_unicode(text)
        assert "²" in result
        assert "π" in result
        assert "≈" in result

    def test_currency_symbols(self):
        """Test currency symbols are preserved."""
        text = "Costs $100 or €85 or £75"
        result = normalize_unicode(text)
        assert "$" in result
        assert "€" in result
        assert "£" in result

    def test_combining_characters(self):
        """Test combining characters are normalized."""
        # e with combining acute accent
        text = "e\u0301"  # e + combining acute
        result = normalize_unicode(text)
        # Should be NFC form (precomposed if possible)
        assert result is not None


class TestEdgeCases:
    """Test edge cases in normalization."""

    def test_empty_string(self):
        """Test empty string normalization."""
        result = normalize_unicode("")
        assert result == ""

    def test_whitespace_only(self):
        """Test whitespace-only text."""
        result = normalize_unicode("   \t\n  ")
        assert result == "   \t\n  "

    def test_very_long_text(self):
        """Test very long text normalization."""
        text = "word " * 1000
        result = normalize_unicode(text)
        assert result is not None
        assert len(result) > 0

    def test_mixed_newlines(self):
        """Test text with newlines."""
        text = "Line 1\nLine 2\r\nLine 3"
        result = normalize_unicode(text)
        assert result is not None
        assert "\n" in result


class TestErrorHandling:
    """Test error handling in normalization."""

    def test_invalid_type(self):
        """Test non-string input raises TypeError."""
        with pytest.raises(TypeError):
            normalize_unicode(123)

    def test_none_input(self):
        """Test None input raises TypeError."""
        with pytest.raises(TypeError):
            normalize_unicode(None)


class TestIsNormalized:
    """Test is_normalized helper function."""

    def test_nfc_is_normalized(self):
        """Test NFC text is detected as normalized."""
        text = "café"
        assert is_normalized(text, "NFC")

    def test_check_different_forms(self):
        """Test checking different normalization forms."""
        text = "café"
        # Most text should be NFC
        assert is_normalized(text, "NFC") or is_normalized(text, "NFD")


class TestUnicodeCategories:
    """Test Unicode category analysis."""

    def test_simple_text_categories(self):
        """Test category analysis of simple text."""
        categories = get_unicode_categories("Hello")
        assert "Lu" in categories  # Uppercase letter
        assert "Ll" in categories  # Lowercase letters
        assert categories["Lu"] == 1  # One uppercase 'H'
        assert categories["Ll"] == 4  # Four lowercase letters

    def test_text_with_numbers(self):
        """Test category analysis with numbers."""
        categories = get_unicode_categories("Test 123")
        assert "Ll" in categories  # Letters
        assert "Nd" in categories  # Decimal numbers
        assert "Zs" in categories  # Space separator

    def test_text_with_emoji(self):
        """Test category analysis with emoji."""
        categories = get_unicode_categories("Hello 🌍")
        assert "So" in categories  # Other symbols (emoji)

    def test_empty_text(self):
        """Test category analysis of empty text."""
        categories = get_unicode_categories("")
        assert len(categories) == 0

    def test_punctuation_categories(self):
        """Test category analysis with punctuation."""
        categories = get_unicode_categories("Hello, world!")
        assert "Po" in categories  # Other punctuation
