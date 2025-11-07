"""Input validation layer for TruthGraph claims.

This package provides comprehensive input validation for claims before they
enter the verification pipeline. It includes:

- Encoding validation (UTF-8, Unicode errors)
- Length validation (word count, token estimation)
- Structure validation (non-empty, alphanumeric content)
- Special character validation (non-ASCII ratio, RTL detection)
- Unicode normalization (NFC form)

Public API:
    ClaimValidator: Main validation orchestrator
    ValidationResult: Validation result container
    ValidationStatus: Validation status enum (VALID, WARNING, INVALID)
    get_claim_validator: Get singleton validator instance

Example:
    >>> from truthgraph.validation import ClaimValidator, ValidationStatus
    >>> validator = ClaimValidator()
    >>> result = validator.validate("The Earth is round")
    >>> result.status == ValidationStatus.VALID
    True
    >>> result.normalized_text
    'The Earth is round'
"""

from truthgraph.validation.claim_validator import ClaimValidator, get_claim_validator
from truthgraph.validation.error_codes import ERROR_CODES, ErrorCodeDefinition, get_error_definition
from truthgraph.validation.models import ValidationResult, ValidationStatus
from truthgraph.validation.normalizers import normalize_unicode
from truthgraph.validation.validators import (
    validate_encoding,
    validate_length,
    validate_special_characters,
    validate_structure,
)

__all__ = [
    # Main classes
    "ClaimValidator",
    "ValidationResult",
    "ValidationStatus",
    # Factory functions
    "get_claim_validator",
    # Error codes
    "ErrorCodeDefinition",
    "ERROR_CODES",
    "get_error_definition",
    # Individual validators (for advanced usage)
    "validate_encoding",
    "validate_length",
    "validate_structure",
    "validate_special_characters",
    # Normalization (for advanced usage)
    "normalize_unicode",
]

__version__ = "0.1.0"
