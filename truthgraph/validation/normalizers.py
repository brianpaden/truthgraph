"""Text normalization utilities for validation.

This module provides Unicode normalization functions that ensure consistent
text representation while preserving semantic meaning. It uses NFC (Canonical
Decomposition followed by Canonical Composition) normalization, which is the
recommended Unicode normalization form for most applications.

Key Features:
- NFC normalization (canonical composition)
- Preservation of emoji, math symbols, Greek letters
- Proper handling of combining characters
- Safe for multilingual text
"""

import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to NFC form.

    Applies Unicode Normalization Form C (NFC), which uses canonical
    decomposition followed by canonical composition. This is the recommended
    normalization form for most text processing applications.

    NFC normalization:
    - Combines decomposed characters (e.g., 'e' + combining acute → 'é')
    - Preserves precomposed characters where possible
    - Safe for emoji, mathematical symbols, and multilingual text
    - Maintains semantic equivalence

    Examples:
        >>> normalize_unicode("café")  # Already NFC
        'café'
        >>> normalize_unicode("café")  # NFD form with combining acute
        'café'
        >>> normalize_unicode("Η Γη είναι στρογγυλή")  # Greek
        'Η Γη είναι στρογγυλή'
        >>> normalize_unicode("E = mc²")  # Math symbols preserved
        'E = mc²'
        >>> normalize_unicode("The Earth 🌍 is round")  # Emoji preserved
        'The Earth 🌍 is round'

    Args:
        text: Input text to normalize

    Returns:
        NFC-normalized text

    Raises:
        ValueError: If text contains invalid Unicode that cannot be normalized
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")

    try:
        # Apply NFC normalization
        normalized = unicodedata.normalize("NFC", text)
        return normalized
    except Exception as e:
        raise ValueError(f"Failed to normalize Unicode text: {e}") from e


def is_normalized(text: str, form: str = "NFC") -> bool:
    """Check if text is already in specified normalization form.

    Args:
        text: Text to check
        form: Normalization form to check (NFC, NFD, NFKC, NFKD)

    Returns:
        True if text is already normalized in the specified form

    Example:
        >>> is_normalized("café")  # Check if already NFC
        True
        >>> is_normalized("café", "NFC")  # Decomposed form
        False
    """
    try:
        return unicodedata.normalize(form, text) == text
    except Exception:
        return False


def get_unicode_categories(text: str) -> dict[str, int]:
    """Get counts of Unicode character categories in text.

    Returns a dictionary with counts of different Unicode categories:
    - Lu: Uppercase letters
    - Ll: Lowercase letters
    - Lt: Titlecase letters
    - Lm: Modifier letters
    - Lo: Other letters (e.g., Chinese, Japanese)
    - Nd: Decimal numbers
    - Nl: Letter numbers
    - No: Other numbers
    - Pc: Connector punctuation
    - Pd: Dash punctuation
    - Ps: Open punctuation
    - Pe: Close punctuation
    - Pi: Initial punctuation
    - Pf: Final punctuation
    - Po: Other punctuation
    - Sm: Math symbols
    - Sc: Currency symbols
    - Sk: Modifier symbols
    - So: Other symbols (includes emoji)
    - Zs: Space separator
    - Zl: Line separator
    - Zp: Paragraph separator
    - Cc: Control characters
    - Cf: Format characters
    - Cs: Surrogate characters
    - Co: Private use characters
    - Cn: Unassigned characters

    Args:
        text: Text to analyze

    Returns:
        Dictionary mapping category codes to counts

    Example:
        >>> get_unicode_categories("Hello 123! 🌍")
        {'Lu': 1, 'Ll': 4, 'Zs': 2, 'Nd': 3, 'Po': 1, 'So': 1}
    """
    categories: dict[str, int] = {}
    for char in text:
        category = unicodedata.category(char)
        categories[category] = categories.get(category, 0) + 1
    return categories
