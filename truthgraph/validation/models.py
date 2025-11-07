"""Validation models and data structures.

This module defines the core data models used throughout the validation layer,
including validation results, status enums, and metadata structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ValidationStatus(str, Enum):
    """Status of validation check.

    VALID: Input passed all validation checks
    WARNING: Input passed critical checks but has warnings
    INVALID: Input failed validation and cannot be processed
    """

    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


@dataclass
class ValidationResult:
    """Result of input validation with detailed information.

    This dataclass captures all information about a validation check,
    including status, error details, suggestions, and normalized text.

    Attributes:
        status: Validation status (VALID, WARNING, INVALID)
        error_type: Type of validation error (e.g., "encoding", "length")
        error_code: Specific error code (e.g., "EMPTY_TEXT", "ENCODING_MISMATCH")
        message: Human-readable error message
        suggestion: Actionable suggestion to fix the validation error
        metadata: Additional context about the validation (word count, etc.)
        normalized_text: NFC-normalized version of input text
        warnings: List of warning messages for non-critical issues
    """

    status: ValidationStatus
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    normalized_text: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if validation passed (VALID or WARNING).

        Returns:
            True if status is VALID or WARNING, False if INVALID
        """
        return self.status in (ValidationStatus.VALID, ValidationStatus.WARNING)

    def is_invalid(self) -> bool:
        """Check if validation failed (INVALID).

        Returns:
            True if status is INVALID, False otherwise
        """
        return self.status == ValidationStatus.INVALID

    def has_warnings(self) -> bool:
        """Check if validation has warnings.

        Returns:
            True if status is WARNING or warnings list is non-empty
        """
        return self.status == ValidationStatus.WARNING or len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary format.

        Returns:
            Dictionary representation of validation result
        """
        return {
            "status": self.status.value,
            "error_type": self.error_type,
            "error_code": self.error_code,
            "message": self.message,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
            "normalized_text": self.normalized_text,
            "warnings": self.warnings,
        }
