"""Individual validation functions for claim text.

This module provides specific validation functions for different aspects
of claim text validation:
- Encoding validation (UTF-8, Unicode errors)
- Length validation (word count, token estimation)
- Structure validation (non-empty, alphanumeric content)
- Special character validation (non-ASCII ratio, RTL detection)

Each validator returns a ValidationResult indicating success, warnings, or failures.
"""

import re
import unicodedata
from typing import Optional

from truthgraph.validation.error_codes import (
    EMPTY_TEXT,
    ENCODING_MISMATCH,
    EXCESSIVE_LENGTH,
    HIGH_NON_ASCII_RATIO,
    MINIMAL_CONTEXT,
    NO_ALPHANUMERIC,
    POTENTIAL_TRUNCATION,
    REPLACEMENT_CHAR,
    SINGLE_WORD,
)
from truthgraph.validation.models import ValidationResult, ValidationStatus


def validate_encoding(text: str) -> ValidationResult:
    """Validate text encoding and detect encoding errors.

    Checks for:
    1. Valid UTF-8 encoding (Python strings are always Unicode, but check for errors)
    2. Unicode replacement characters (U+FFFD) indicating encoding problems
    3. Invalid Unicode sequences

    Args:
        text: Text to validate

    Returns:
        ValidationResult with status VALID or INVALID

    Example:
        >>> validate_encoding("Valid UTF-8 text")
        ValidationResult(status=ValidationStatus.VALID, ...)
        >>> validate_encoding("Invalid: \ufffd")
        ValidationResult(status=ValidationStatus.INVALID, error_code="REPLACEMENT_CHAR", ...)
    """
    # Check for Unicode replacement character (U+FFFD)
    # This indicates encoding errors when converting from other encodings
    if "\ufffd" in text:
        return ValidationResult(
            status=REPLACEMENT_CHAR.status,
            error_type=REPLACEMENT_CHAR.error_type,
            error_code=REPLACEMENT_CHAR.code,
            message=REPLACEMENT_CHAR.description,
            suggestion=REPLACEMENT_CHAR.suggestion,
            metadata={"replacement_char_count": text.count("\ufffd")},
        )

    # Try to encode as UTF-8 to catch any issues
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as e:
        return ValidationResult(
            status=ENCODING_MISMATCH.status,
            error_type=ENCODING_MISMATCH.error_type,
            error_code=ENCODING_MISMATCH.code,
            message=f"{ENCODING_MISMATCH.description}: {str(e)}",
            suggestion=ENCODING_MISMATCH.suggestion,
            metadata={"encode_error": str(e)},
        )

    # All checks passed
    return ValidationResult(
        status=ValidationStatus.VALID,
        metadata={"encoding": "utf-8", "encoding_valid": True},
    )


def validate_structure(text: str) -> ValidationResult:
    """Validate basic text structure.

    Checks for:
    1. Non-empty text (after stripping whitespace)
    2. Presence of at least one alphanumeric character

    Args:
        text: Text to validate

    Returns:
        ValidationResult with status VALID or INVALID

    Example:
        >>> validate_structure("The Earth is round")
        ValidationResult(status=ValidationStatus.VALID, ...)
        >>> validate_structure("   ")
        ValidationResult(status=ValidationStatus.INVALID, error_code="EMPTY_TEXT", ...)
        >>> validate_structure("!!!")
        ValidationResult(status=ValidationStatus.INVALID, error_code="NO_ALPHANUMERIC", ...)
    """
    # Check for empty or whitespace-only text
    if not text or not text.strip():
        return ValidationResult(
            status=EMPTY_TEXT.status,
            error_type=EMPTY_TEXT.error_type,
            error_code=EMPTY_TEXT.code,
            message=EMPTY_TEXT.description,
            suggestion=EMPTY_TEXT.suggestion,
            metadata={"text_length": len(text), "stripped_length": len(text.strip())},
        )

    # Check for at least one alphanumeric character
    # This handles special cases like emoji-only or punctuation-only text
    if not any(c.isalnum() for c in text):
        return ValidationResult(
            status=NO_ALPHANUMERIC.status,
            error_type=NO_ALPHANUMERIC.error_type,
            error_code=NO_ALPHANUMERIC.code,
            message=NO_ALPHANUMERIC.description,
            suggestion=NO_ALPHANUMERIC.suggestion,
            metadata={"text_length": len(text), "has_alphanumeric": False},
        )

    # All checks passed
    return ValidationResult(
        status=ValidationStatus.VALID,
        metadata={"text_length": len(text.strip()), "has_alphanumeric": True},
    )


def validate_length(
    text: str,
    min_words: int = 2,
    max_words: int = 500,
    max_tokens_estimate: int = 450,
) -> ValidationResult:
    """Validate text length constraints.

    Checks for:
    1. Single-word claims (INVALID)
    2. Very short claims (<3 words) (WARNING)
    3. Very long claims (>max_words or >max_tokens_estimate) (WARNING)

    Token estimation uses a simple heuristic: tokens ≈ words * 1.3
    This accounts for subword tokenization in modern language models.

    Args:
        text: Text to validate
        min_words: Minimum word count (default: 2)
        max_words: Maximum word count (default: 500)
        max_tokens_estimate: Maximum estimated tokens (default: 450)

    Returns:
        ValidationResult with status VALID, WARNING, or INVALID

    Example:
        >>> validate_length("Earth")  # Single word
        ValidationResult(status=ValidationStatus.INVALID, error_code="SINGLE_WORD", ...)
        >>> validate_length("Earth orbits")  # Minimal context
        ValidationResult(status=ValidationStatus.WARNING, error_code="MINIMAL_CONTEXT", ...)
        >>> validate_length("The Earth orbits the Sun")  # Valid
        ValidationResult(status=ValidationStatus.VALID, ...)
    """
    # Count words (split on whitespace)
    words = text.split()
    word_count = len(words)

    # Estimate token count (rough heuristic: tokens ≈ words * 1.3)
    # This accounts for subword tokenization (e.g., "running" -> ["run", "##ning"])
    estimated_tokens = int(word_count * 1.3)

    # Single word is INVALID
    if word_count < min_words:
        return ValidationResult(
            status=SINGLE_WORD.status,
            error_type=SINGLE_WORD.error_type,
            error_code=SINGLE_WORD.code,
            message=SINGLE_WORD.description,
            suggestion=SINGLE_WORD.suggestion,
            metadata={
                "word_count": word_count,
                "min_words": min_words,
                "estimated_tokens": estimated_tokens,
            },
        )

    # Very short (<3 words) is WARNING
    if word_count < 3:
        return ValidationResult(
            status=MINIMAL_CONTEXT.status,
            error_type=MINIMAL_CONTEXT.error_type,
            error_code=MINIMAL_CONTEXT.code,
            message=MINIMAL_CONTEXT.description,
            suggestion=MINIMAL_CONTEXT.suggestion,
            metadata={
                "word_count": word_count,
                "min_words": min_words,
                "estimated_tokens": estimated_tokens,
            },
        )

    # Very long (>max_tokens_estimate) is WARNING
    if estimated_tokens > max_tokens_estimate:
        return ValidationResult(
            status=POTENTIAL_TRUNCATION.status,
            error_type=POTENTIAL_TRUNCATION.error_type,
            error_code=POTENTIAL_TRUNCATION.code,
            message=f"{POTENTIAL_TRUNCATION.description} (estimated {estimated_tokens} tokens)",
            suggestion=POTENTIAL_TRUNCATION.suggestion,
            metadata={
                "word_count": word_count,
                "estimated_tokens": estimated_tokens,
                "max_tokens_estimate": max_tokens_estimate,
            },
        )

    # Excessive word count (>max_words) is WARNING
    if word_count > max_words:
        return ValidationResult(
            status=EXCESSIVE_LENGTH.status,
            error_type=EXCESSIVE_LENGTH.error_type,
            error_code=EXCESSIVE_LENGTH.code,
            message=f"{EXCESSIVE_LENGTH.description} ({word_count} words)",
            suggestion=EXCESSIVE_LENGTH.suggestion,
            metadata={
                "word_count": word_count,
                "max_words": max_words,
                "estimated_tokens": estimated_tokens,
            },
        )

    # All checks passed
    return ValidationResult(
        status=ValidationStatus.VALID,
        metadata={
            "word_count": word_count,
            "estimated_tokens": estimated_tokens,
            "length_valid": True,
        },
    )


def validate_special_characters(text: str, max_non_ascii_ratio: float = 0.5) -> ValidationResult:
    """Validate special character usage and non-ASCII content.

    Checks for:
    1. High ratio of non-ASCII characters (>50%) (WARNING)
    2. Presence of RTL (Right-To-Left) text markers
    3. Emoji and special Unicode blocks

    This validation is intentionally permissive to support multilingual content.
    Greek letters, mathematical symbols, emoji, and RTL text are all VALID.

    Args:
        text: Text to validate
        max_non_ascii_ratio: Maximum ratio of non-ASCII chars before warning (default: 0.5)

    Returns:
        ValidationResult with status VALID or WARNING

    Example:
        >>> validate_special_characters("The Earth is round")  # ASCII
        ValidationResult(status=ValidationStatus.VALID, ...)
        >>> validate_special_characters("Η Γη είναι στρογγυλή")  # Greek (all non-ASCII)
        ValidationResult(status=ValidationStatus.WARNING, ...)
        >>> validate_special_characters("The Earth 🌍 is round")  # Mixed with emoji
        ValidationResult(status=ValidationStatus.VALID, ...)
    """
    if not text:
        return ValidationResult(
            status=ValidationStatus.VALID,
            metadata={"non_ascii_ratio": 0.0, "has_rtl": False, "has_emoji": False},
        )

    # Count ASCII vs non-ASCII characters
    ascii_count = sum(1 for c in text if ord(c) < 128)
    non_ascii_count = len(text) - ascii_count
    non_ascii_ratio = non_ascii_count / len(text) if len(text) > 0 else 0.0

    # Detect RTL (Right-To-Left) text
    # Hebrew: U+0590 to U+05FF
    # Arabic: U+0600 to U+06FF
    rtl_pattern = re.compile(r"[\u0590-\u05FF\u0600-\u06FF]")
    has_rtl = bool(rtl_pattern.search(text))

    # Detect emoji (simplified check for common emoji blocks)
    # Emoji: U+1F300 to U+1F9FF (various blocks)
    # Also check for variation selectors and emoji modifiers
    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF]")
    has_emoji = bool(emoji_pattern.search(text))

    # Count special Unicode categories
    special_categories = {
        "Sm": 0,  # Math symbols
        "Sc": 0,  # Currency symbols
        "So": 0,  # Other symbols (includes many emoji)
        "Mn": 0,  # Non-spacing marks (combining characters)
        "Mc": 0,  # Spacing combining marks
        "Me": 0,  # Enclosing marks
    }

    for char in text:
        category = unicodedata.category(char)
        if category in special_categories:
            special_categories[category] += 1

    metadata = {
        "non_ascii_ratio": round(non_ascii_ratio, 3),
        "ascii_count": ascii_count,
        "non_ascii_count": non_ascii_count,
        "has_rtl": has_rtl,
        "has_emoji": has_emoji,
        "special_categories": {k: v for k, v in special_categories.items() if v > 0},
    }

    # High non-ASCII ratio is WARNING (but not INVALID)
    # This supports multilingual content while alerting users
    if non_ascii_ratio > max_non_ascii_ratio:
        return ValidationResult(
            status=HIGH_NON_ASCII_RATIO.status,
            error_type=HIGH_NON_ASCII_RATIO.error_type,
            error_code=HIGH_NON_ASCII_RATIO.code,
            message=f"{HIGH_NON_ASCII_RATIO.description} ({int(non_ascii_ratio * 100)}%)",
            suggestion=HIGH_NON_ASCII_RATIO.suggestion,
            metadata=metadata,
        )

    # All checks passed
    return ValidationResult(
        status=ValidationStatus.VALID,
        metadata=metadata,
    )
