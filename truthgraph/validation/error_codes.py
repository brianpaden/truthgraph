"""Error code definitions for validation failures.

This module defines all validation error codes with their types, descriptions,
and suggested remediation actions. Error codes follow a consistent naming scheme:
- Prefix indicates severity (INVALID, WARNING)
- Category indicates validation type (TEXT, ENCODING, LENGTH, etc.)
"""

from dataclasses import dataclass
from typing import Literal

from truthgraph.validation.models import ValidationStatus


@dataclass(frozen=True)
class ErrorCodeDefinition:
    """Definition of a validation error code.

    Attributes:
        code: Unique error code identifier
        status: Validation status this error produces (INVALID or WARNING)
        error_type: Category of error (encoding, length, structure, etc.)
        description: Human-readable description of the error
        suggestion: Actionable suggestion to fix the error
    """

    code: str
    status: ValidationStatus
    error_type: str
    description: str
    suggestion: str


# INVALID error codes - These cause validation to fail
EMPTY_TEXT = ErrorCodeDefinition(
    code="EMPTY_TEXT",
    status=ValidationStatus.INVALID,
    error_type="structure",
    description="Claim text is empty or contains only whitespace",
    suggestion="Provide a non-empty claim with meaningful content",
)

SINGLE_WORD = ErrorCodeDefinition(
    code="SINGLE_WORD",
    status=ValidationStatus.INVALID,
    error_type="length",
    description="Claim contains only a single word",
    suggestion="Provide a claim with at least 2 words to enable proper verification",
)

ENCODING_MISMATCH = ErrorCodeDefinition(
    code="ENCODING_MISMATCH",
    status=ValidationStatus.INVALID,
    error_type="encoding",
    description="Text contains invalid UTF-8 encoding or byte sequences",
    suggestion="Ensure text is properly encoded as UTF-8",
)

REPLACEMENT_CHAR = ErrorCodeDefinition(
    code="REPLACEMENT_CHAR",
    status=ValidationStatus.INVALID,
    error_type="encoding",
    description="Text contains Unicode replacement characters (U+FFFD) indicating encoding errors",
    suggestion="Check the source encoding and convert properly to UTF-8",
)

NO_ALPHANUMERIC = ErrorCodeDefinition(
    code="NO_ALPHANUMERIC",
    status=ValidationStatus.INVALID,
    error_type="structure",
    description="Text contains no alphanumeric characters",
    suggestion="Provide text with at least some alphanumeric content",
)

INVALID_UNICODE = ErrorCodeDefinition(
    code="INVALID_UNICODE",
    status=ValidationStatus.INVALID,
    error_type="encoding",
    description="Text contains invalid Unicode sequences that cannot be normalized",
    suggestion="Remove or replace invalid Unicode characters",
)

# WARNING error codes - These generate warnings but allow processing
MINIMAL_CONTEXT = ErrorCodeDefinition(
    code="MINIMAL_CONTEXT",
    status=ValidationStatus.WARNING,
    error_type="length",
    description="Claim is very short (less than 3 words) and may lack context",
    suggestion="Consider providing more context for better verification accuracy",
)

POTENTIAL_TRUNCATION = ErrorCodeDefinition(
    code="POTENTIAL_TRUNCATION",
    status=ValidationStatus.WARNING,
    error_type="length",
    description="Claim is very long (>450 tokens estimated) and may be truncated",
    suggestion="Consider shortening the claim or splitting into multiple claims",
)

HIGH_NON_ASCII_RATIO = ErrorCodeDefinition(
    code="HIGH_NON_ASCII_RATIO",
    status=ValidationStatus.WARNING,
    error_type="special_characters",
    description="More than 50% of characters are non-ASCII",
    suggestion="Verify that the text encoding is correct and intentional",
)

EXCESSIVE_LENGTH = ErrorCodeDefinition(
    code="EXCESSIVE_LENGTH",
    status=ValidationStatus.WARNING,
    error_type="length",
    description="Claim exceeds recommended length (>500 words)",
    suggestion="Consider splitting into multiple focused claims for better accuracy",
)

# Error code registry for fast lookup
ERROR_CODES: dict[str, ErrorCodeDefinition] = {
    # INVALID codes
    EMPTY_TEXT.code: EMPTY_TEXT,
    SINGLE_WORD.code: SINGLE_WORD,
    ENCODING_MISMATCH.code: ENCODING_MISMATCH,
    REPLACEMENT_CHAR.code: REPLACEMENT_CHAR,
    NO_ALPHANUMERIC.code: NO_ALPHANUMERIC,
    INVALID_UNICODE.code: INVALID_UNICODE,
    # WARNING codes
    MINIMAL_CONTEXT.code: MINIMAL_CONTEXT,
    POTENTIAL_TRUNCATION.code: POTENTIAL_TRUNCATION,
    HIGH_NON_ASCII_RATIO.code: HIGH_NON_ASCII_RATIO,
    EXCESSIVE_LENGTH.code: EXCESSIVE_LENGTH,
}


def get_error_definition(code: str) -> ErrorCodeDefinition | None:
    """Get error code definition by code string.

    Args:
        code: Error code string (e.g., "EMPTY_TEXT")

    Returns:
        ErrorCodeDefinition if found, None otherwise
    """
    return ERROR_CODES.get(code)
