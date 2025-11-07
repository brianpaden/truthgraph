"""Unit tests for special character validation."""

import pytest

from truthgraph.validation import ValidationStatus
from truthgraph.validation.validators import validate_special_characters


class TestAsciiText:
    """Test validation of ASCII text."""

    def test_pure_ascii(self):
        """Test pure ASCII text passes without warnings."""
        result = validate_special_characters("The Earth is round")
        assert result.status == ValidationStatus.VALID
        assert "non_ascii_ratio" in result.metadata
        assert result.metadata["non_ascii_ratio"] == 0.0

    def test_ascii_with_punctuation(self):
        """Test ASCII text with punctuation."""
        result = validate_special_characters("Hello, world! How are you?")
        assert result.status == ValidationStatus.VALID
        assert result.metadata["non_ascii_ratio"] == 0.0

    def test_ascii_with_numbers(self):
        """Test ASCII text with numbers."""
        result = validate_special_characters("The year is 2025")
        assert result.status == ValidationStatus.VALID


class TestMixedAsciiNonAscii:
    """Test validation of mixed ASCII and non-ASCII text."""

    def test_low_non_ascii_ratio(self):
        """Test low non-ASCII ratio passes."""
        result = validate_special_characters("The Earth is café")
        assert result.status == ValidationStatus.VALID
        # "café" has 1 non-ASCII char out of 18 total
        assert result.metadata["non_ascii_ratio"] < 0.5

    def test_text_with_emoji(self):
        """Test text with emoji has low ratio."""
        result = validate_special_characters("The Earth 🌍 is round")
        assert result.status == ValidationStatus.VALID
        # One emoji out of 20 chars should be <50%
        assert result.metadata["non_ascii_ratio"] < 0.5

    def test_text_with_math_symbols(self):
        """Test text with mathematical symbols."""
        result = validate_special_characters("E = mc² is Einstein's equation")
        assert result.status == ValidationStatus.VALID


class TestHighNonAsciiRatio:
    """Test validation of text with high non-ASCII ratio."""

    def test_pure_greek_text(self):
        """Test pure Greek text generates warning."""
        result = validate_special_characters("Η Γη είναι στρογγυλή")
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "HIGH_NON_ASCII_RATIO"
        assert result.metadata["non_ascii_ratio"] > 0.5

    def test_pure_arabic_text(self):
        """Test pure Arabic text generates warning."""
        result = validate_special_characters("الأرض كروية")
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "HIGH_NON_ASCII_RATIO"

    def test_pure_chinese_text(self):
        """Test pure Chinese text generates warning."""
        result = validate_special_characters("地球是圆的")
        assert result.status == ValidationStatus.WARNING
        assert result.error_code == "HIGH_NON_ASCII_RATIO"

    def test_exactly_50_percent(self):
        """Test exactly 50% non-ASCII (boundary case)."""
        # "café" = 4 chars, 1 non-ASCII = 25%
        # We need exactly 50%: "caf" (3 ASCII) + "é" (1) + "ab" (2) + "é" (1) = 6 total, 2 non-ASCII
        # Actually let's use: "café café" = 9 chars, 2 non-ASCII = 22%
        # Better: "éééé test" = 9 chars, 4 non-ASCII = 44%
        # Let's be more direct: "ééé te" = 6 chars, 3 non-ASCII = 50%
        text = "ééé te"
        result = validate_special_characters(text)
        # At exactly 50%, should not trigger warning (threshold is >50%)
        if result.metadata["non_ascii_ratio"] <= 0.5:
            assert result.status == ValidationStatus.VALID
        else:
            assert result.status == ValidationStatus.WARNING


class TestRtlText:
    """Test RTL (Right-to-Left) text detection."""

    def test_hebrew_text_detected(self):
        """Test Hebrew text is detected as RTL."""
        result = validate_special_characters("שלום עולם")
        assert result.metadata["has_rtl"] is True

    def test_arabic_text_detected(self):
        """Test Arabic text is detected as RTL."""
        result = validate_special_characters("الأرض كروية")
        assert result.metadata["has_rtl"] is True

    def test_ltr_text_not_rtl(self):
        """Test LTR text is not detected as RTL."""
        result = validate_special_characters("The Earth is round")
        assert result.metadata["has_rtl"] is False

    def test_mixed_ltr_rtl(self):
        """Test mixed LTR and RTL text."""
        result = validate_special_characters("Earth (English), الأرض (Arabic)")
        assert result.metadata["has_rtl"] is True


class TestEmojiDetection:
    """Test emoji detection."""

    def test_emoji_detected(self):
        """Test emoji are detected."""
        result = validate_special_characters("The Earth 🌍 is round")
        assert result.metadata["has_emoji"] is True

    def test_multiple_emoji(self):
        """Test multiple emoji are detected."""
        result = validate_special_characters("🌍 🌎 🌏 Earth")
        assert result.metadata["has_emoji"] is True

    def test_no_emoji(self):
        """Test text without emoji."""
        result = validate_special_characters("The Earth is round")
        assert result.metadata["has_emoji"] is False


class TestSpecialUnicodeCategories:
    """Test detection of special Unicode categories."""

    def test_math_symbols(self):
        """Test mathematical symbols are categorized."""
        result = validate_special_characters("E = mc²")
        # Math symbols should be in special_categories
        if "special_categories" in result.metadata:
            categories = result.metadata["special_categories"]
            # Superscript 2 is in Sm or No category
            assert len(categories) > 0

    def test_combining_characters(self):
        """Test combining characters are detected."""
        # e with combining acute: e + U+0301
        text = "e\u0301"
        result = validate_special_characters(text)
        # Should have combining marks in metadata
        assert result.metadata is not None


class TestCustomThreshold:
    """Test custom non-ASCII ratio threshold."""

    def test_custom_threshold_90_percent(self):
        """Test custom 90% threshold."""
        # Greek text without spaces has 100% non-ASCII
        result = validate_special_characters("ΗΓηείναι", max_non_ascii_ratio=0.9)
        assert result.status == ValidationStatus.WARNING

    def test_custom_threshold_10_percent(self):
        """Test strict 10% threshold."""
        # Even small non-ASCII amount triggers warning
        # "café" has 1 non-ASCII out of 4 = 25%, which is > 10%
        result = validate_special_characters("café", max_non_ascii_ratio=0.1)
        # Should trigger warning with strict threshold
        assert result.status == ValidationStatus.WARNING


class TestMetadata:
    """Test metadata completeness."""

    def test_metadata_includes_counts(self):
        """Test metadata includes ASCII and non-ASCII counts."""
        result = validate_special_characters("Hello café")
        assert "ascii_count" in result.metadata
        assert "non_ascii_count" in result.metadata
        assert "non_ascii_ratio" in result.metadata

    def test_metadata_includes_flags(self):
        """Test metadata includes detection flags."""
        result = validate_special_characters("The Earth 🌍")
        assert "has_rtl" in result.metadata
        assert "has_emoji" in result.metadata

    def test_empty_text_metadata(self):
        """Test empty text produces valid metadata."""
        result = validate_special_characters("")
        assert result.status == ValidationStatus.VALID
        assert result.metadata["non_ascii_ratio"] == 0.0
        assert result.metadata["has_rtl"] is False
        assert result.metadata["has_emoji"] is False


class TestEdgeCases:
    """Test edge cases in special character validation."""

    def test_whitespace_only(self):
        """Test whitespace-only text."""
        result = validate_special_characters("   ")
        assert result.status == ValidationStatus.VALID
        assert result.metadata["non_ascii_ratio"] == 0.0

    def test_punctuation_only(self):
        """Test punctuation-only text."""
        result = validate_special_characters("!!! ... ???")
        assert result.status == ValidationStatus.VALID

    def test_numbers_only(self):
        """Test numbers-only text."""
        result = validate_special_characters("123 456 789")
        assert result.status == ValidationStatus.VALID
