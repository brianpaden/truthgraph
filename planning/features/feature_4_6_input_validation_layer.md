# Feature 4.6: Input Validation Layer - Implementation Guide

**Phase**: 4 - Production Features
**Priority**: High
**Complexity**: Medium
**Timeline**: 1-2 weeks
**Dependencies**: Feature 4.1 (API), Feature 4.3 (Background Tasks)

## Executive Summary

This document provides detailed implementation guidance for adding a comprehensive input validation layer to TruthGraph's verification pipeline. This validation layer goes beyond basic API request validation to provide robust, security-focused input validation throughout the system with <10ms overhead per validation.

### Key Goals

1. **Security**: Prevent injection attacks, encoding exploits, and malformed input
2. **Reliability**: Ensure consistent handling of edge cases (unicode, special chars, length)
3. **Performance**: Add validation with <10ms overhead per claim
4. **Developer Experience**: Provide clear, actionable error messages
5. **Maintainability**: Centralize validation logic with configuration-driven rules

---

## Table of Contents

1. [Module Structure](#1-module-structure)
2. [ClaimValidator Class Design](#2-claimvalidator-class-design)
3. [Validation Rules Reference](#3-validation-rules-reference)
4. [Error Response Design](#4-error-response-design)
5. [Testing Strategy](#5-testing-strategy)
6. [Performance Optimization](#6-performance-optimization)
7. [Configuration Management](#7-configuration-management)
8. [Integration Points](#8-integration-points)
9. [Migration Path](#9-migration-path)
10. [Code Examples](#10-code-examples)
11. [Implementation Checklist](#11-implementation-checklist)
12. [Performance Benchmarks](#12-performance-benchmarks)

---

## 1. Module Structure

### Directory Layout

```
truthgraph/validation/
├── __init__.py                    # Public API exports
├── claim_validator.py             # Main ClaimValidator orchestrator
├── encoding_validator.py          # UTF-8 and encoding validation
├── unicode_normalizer.py          # Unicode normalization and handling
├── length_validator.py            # Length checks and truncation detection
├── special_char_validator.py      # Special character validation
├── validation_errors.py           # Custom exception hierarchy
├── validation_config.py           # Configuration models
└── validation_result.py           # Result dataclasses
```

### Module Responsibilities

#### `__init__.py`
```python
"""Input validation layer for TruthGraph claims and evidence.

Public API:
    ClaimValidator: Main validation orchestrator
    ValidationError: Base exception class
    ValidationResult: Validation result container
    ValidationConfig: Configuration model
"""

from .claim_validator import ClaimValidator
from .validation_config import ValidationConfig, ValidationProfile
from .validation_errors import (
    ValidationError,
    EncodingValidationError,
    LengthValidationError,
    UnicodeValidationError,
    SpecialCharValidationError,
)
from .validation_result import ValidationResult, ValidationSeverity

__all__ = [
    "ClaimValidator",
    "ValidationConfig",
    "ValidationProfile",
    "ValidationError",
    "EncodingValidationError",
    "LengthValidationError",
    "UnicodeValidationError",
    "SpecialCharValidationError",
    "ValidationResult",
    "ValidationSeverity",
]
```

#### `validation_errors.py`

Custom exception hierarchy with error codes and suggestions.

```python
"""Custom exception hierarchy for validation errors."""

from typing import Optional


class ValidationError(ValueError):
    """Base exception for all validation errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., VAL_001)
        field: Field name that failed validation
        suggestion: Suggested fix for the error
        severity: Error severity (error, warning, info)
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
        severity: str = "error",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.field = field
        self.suggestion = suggestion
        self.severity = severity

    def to_dict(self) -> dict[str, str | None]:
        """Convert exception to dictionary format."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "field": self.field,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


class EncodingValidationError(ValidationError):
    """Raised when text encoding is invalid or unsupported."""

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_ENC_001",
        **kwargs,
    ):
        super().__init__(message, error_code, **kwargs)


class LengthValidationError(ValidationError):
    """Raised when text length is outside acceptable bounds."""

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_LEN_001",
        **kwargs,
    ):
        super().__init__(message, error_code, **kwargs)


class UnicodeValidationError(ValidationError):
    """Raised when unicode handling fails or contains problematic characters."""

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_UNI_001",
        **kwargs,
    ):
        super().__init__(message, error_code, **kwargs)


class SpecialCharValidationError(ValidationError):
    """Raised when special characters are invalid or pose security risk."""

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_CHAR_001",
        **kwargs,
    ):
        super().__init__(message, error_code, **kwargs)
```

#### `validation_result.py`

Result dataclasses for validation outcomes.

```python
"""Validation result models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"      # Validation failed, input rejected
    WARNING = "warning"  # Potential issue, input accepted
    INFO = "info"        # Informational message


@dataclass(frozen=True)
class ValidationIssue:
    """Individual validation issue."""

    code: str
    message: str
    severity: ValidationSeverity
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of validation operation.

    Attributes:
        valid: Whether input passed validation
        normalized_text: Normalized/sanitized version of input
        issues: List of validation issues found
        metadata: Additional validation metadata
    """

    valid: bool
    normalized_text: Optional[str] = None
    issues: list[ValidationIssue] = field(default_factory=list)
    metadata: dict[str, any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """Check if result has any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    def get_errors(self) -> list[ValidationIssue]:
        """Get all error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def get_warnings(self) -> list[ValidationIssue]:
        """Get all warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "valid": self.valid,
            "normalized_text": self.normalized_text,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata,
        }
```

#### `validation_config.py`

Configuration models using Pydantic.

```python
"""Validation configuration models."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator


class ValidationProfile(str, Enum):
    """Predefined validation profiles."""

    STRICT = "strict"       # Maximum validation, reject edge cases
    STANDARD = "standard"   # Balanced validation (default)
    LENIENT = "lenient"     # Minimal validation, accept most inputs
    CUSTOM = "custom"       # User-defined configuration


class ValidationConfig(BaseModel):
    """Configuration for claim validation.

    This model defines all validation thresholds and behavior.
    Can be loaded from environment variables or configuration files.
    """

    # Profile
    profile: ValidationProfile = ValidationProfile.STANDARD

    # Length limits
    min_length: Annotated[int, Field(ge=1)] = 1
    max_length: Annotated[int, Field(le=10000)] = 2000
    max_word_count: Annotated[int, Field(gt=0)] = 500

    # Encoding
    allowed_encodings: list[str] = Field(default_factory=lambda: ["utf-8"])
    normalize_encoding: bool = True
    strip_bom: bool = True

    # Unicode
    unicode_normalization: str = "NFC"  # NFC, NFD, NFKC, NFKD
    allow_rtl_scripts: bool = True
    max_combining_chars: int = 10
    check_homoglyphs: bool = True

    # Special characters
    allowed_char_categories: set[str] = Field(
        default_factory=lambda: {
            "Lu", "Ll", "Lt", "Lm", "Lo",  # Letters
            "Nd", "Nl", "No",               # Numbers
            "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po",  # Punctuation
            "Zs", "Zl", "Zp",               # Separators
            "Sm", "Sc", "Sk", "So",         # Symbols
        }
    )
    disallowed_control_chars: bool = True
    allow_zero_width_chars: bool = False

    # Structure
    normalize_whitespace: bool = True
    max_consecutive_whitespace: int = 5
    strip_leading_trailing: bool = True

    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    @field_validator("unicode_normalization")
    @classmethod
    def validate_normalization_form(cls, v: str) -> str:
        """Validate Unicode normalization form."""
        if v not in {"NFC", "NFD", "NFKC", "NFKD"}:
            raise ValueError(f"Invalid normalization form: {v}")
        return v

    @classmethod
    def strict(cls) -> "ValidationConfig":
        """Create strict validation profile."""
        return cls(
            profile=ValidationProfile.STRICT,
            min_length=5,
            max_length=1000,
            max_word_count=200,
            check_homoglyphs=True,
            allow_zero_width_chars=False,
            disallowed_control_chars=True,
        )

    @classmethod
    def lenient(cls) -> "ValidationConfig":
        """Create lenient validation profile."""
        return cls(
            profile=ValidationProfile.LENIENT,
            min_length=1,
            max_length=5000,
            max_word_count=1000,
            check_homoglyphs=False,
            allow_zero_width_chars=True,
            disallowed_control_chars=False,
        )
```

#### `encoding_validator.py`

UTF-8 and encoding validation.

```python
"""Encoding validation for text inputs."""

import unicodedata
from typing import Optional

from .validation_config import ValidationConfig
from .validation_errors import EncodingValidationError
from .validation_result import ValidationIssue, ValidationSeverity


class EncodingValidator:
    """Validates text encoding and handles encoding issues.

    Checks:
    - Valid UTF-8 encoding
    - BOM detection and removal
    - Encoding detection for non-UTF-8
    - Replacement character detection
    """

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate(self, text: str) -> tuple[str, list[ValidationIssue]]:
        """Validate and normalize text encoding.

        Args:
            text: Input text to validate

        Returns:
            Tuple of (normalized_text, issues)

        Raises:
            EncodingValidationError: If encoding is invalid and cannot be recovered
        """
        issues: list[ValidationIssue] = []
        normalized = text

        # Check for BOM
        if text.startswith('\ufeff'):
            if self.config.strip_bom:
                normalized = text[1:]
                issues.append(ValidationIssue(
                    code="VAL_ENC_001",
                    message="BOM detected and removed",
                    severity=ValidationSeverity.INFO,
                    field="text",
                ))
            else:
                issues.append(ValidationIssue(
                    code="VAL_ENC_002",
                    message="BOM detected in text",
                    severity=ValidationSeverity.WARNING,
                    field="text",
                    suggestion="Remove BOM character from input",
                ))

        # Check for replacement characters (indicates encoding issues)
        replacement_count = normalized.count('\ufffd')
        if replacement_count > 0:
            raise EncodingValidationError(
                message=f"Text contains {replacement_count} replacement character(s) "
                        f"indicating encoding corruption",
                error_code="VAL_ENC_003",
                field="text",
                suggestion="Ensure text is properly encoded as UTF-8",
            )

        # Check for null bytes (security concern)
        if '\x00' in normalized:
            raise EncodingValidationError(
                message="Text contains null bytes",
                error_code="VAL_ENC_004",
                field="text",
                suggestion="Remove null bytes from input",
            )

        # Verify can be encoded to UTF-8
        try:
            normalized.encode('utf-8')
        except UnicodeEncodeError as e:
            raise EncodingValidationError(
                message=f"Text cannot be encoded as UTF-8: {e}",
                error_code="VAL_ENC_005",
                field="text",
                suggestion="Ensure all characters are valid UTF-8",
            )

        return normalized, issues
```

#### `unicode_normalizer.py`

Unicode normalization and validation.

```python
"""Unicode normalization and validation."""

import unicodedata
from typing import Optional

from .validation_config import ValidationConfig
from .validation_errors import UnicodeValidationError
from .validation_result import ValidationIssue, ValidationSeverity


class UnicodeNormalizer:
    """Handles Unicode normalization and validation.

    Features:
    - Unicode normalization (NFC/NFD/NFKC/NFKD)
    - RTL script detection and handling
    - Combining character validation
    - Homoglyph detection
    - Mixed-script detection
    """

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate_and_normalize(self, text: str) -> tuple[str, list[ValidationIssue]]:
        """Validate and normalize Unicode text.

        Args:
            text: Input text to validate

        Returns:
            Tuple of (normalized_text, issues)

        Raises:
            UnicodeValidationError: If Unicode validation fails
        """
        issues: list[ValidationIssue] = []

        # Apply Unicode normalization
        normalized = unicodedata.normalize(self.config.unicode_normalization, text)

        if normalized != text:
            issues.append(ValidationIssue(
                code="VAL_UNI_001",
                message=f"Text normalized using {self.config.unicode_normalization}",
                severity=ValidationSeverity.INFO,
                field="text",
            ))

        # Check for excessive combining characters
        combining_count = self._count_combining_chars(normalized)
        if combining_count > self.config.max_combining_chars:
            raise UnicodeValidationError(
                message=f"Text contains {combining_count} combining characters "
                        f"(max: {self.config.max_combining_chars})",
                error_code="VAL_UNI_002",
                field="text",
                suggestion="Reduce number of combining diacritical marks",
            )

        # Detect RTL scripts
        has_rtl = self._has_rtl_chars(normalized)
        if has_rtl and not self.config.allow_rtl_scripts:
            raise UnicodeValidationError(
                message="Text contains right-to-left script characters",
                error_code="VAL_UNI_003",
                field="text",
                suggestion="RTL scripts not allowed in current validation profile",
            )

        if has_rtl:
            issues.append(ValidationIssue(
                code="VAL_UNI_004",
                message="Text contains RTL script characters",
                severity=ValidationSeverity.INFO,
                field="text",
            ))

        # Check for homoglyphs (if enabled)
        if self.config.check_homoglyphs:
            homoglyph_issues = self._detect_homoglyphs(normalized)
            issues.extend(homoglyph_issues)

        # Detect mixed scripts
        script_info = self._analyze_scripts(normalized)
        if len(script_info) > 3:
            issues.append(ValidationIssue(
                code="VAL_UNI_005",
                message=f"Text contains {len(script_info)} different scripts: "
                        f"{', '.join(script_info)}",
                severity=ValidationSeverity.WARNING,
                field="text",
                suggestion="Mixed scripts may indicate suspicious input",
            ))

        return normalized, issues

    def _count_combining_chars(self, text: str) -> int:
        """Count combining characters in text."""
        return sum(1 for c in text if unicodedata.combining(c))

    def _has_rtl_chars(self, text: str) -> bool:
        """Check if text contains RTL script characters."""
        rtl_categories = {'R', 'AL'}  # Right-to-left, Arabic letter
        return any(
            unicodedata.bidirectional(c) in rtl_categories
            for c in text
        )

    def _analyze_scripts(self, text: str) -> list[str]:
        """Analyze Unicode scripts present in text."""
        scripts = set()
        for char in text:
            if char.isspace() or char in ".,;:!?-()[]{}":
                continue  # Skip whitespace and common punctuation
            try:
                script = unicodedata.name(char).split()[0]
                scripts.add(script)
            except ValueError:
                pass  # Character has no name
        return sorted(scripts)

    def _detect_homoglyphs(self, text: str) -> list[ValidationIssue]:
        """Detect potential homoglyph attacks.

        Simplified implementation - checks for common homoglyphs.
        Production should use comprehensive homoglyph database.
        """
        issues = []

        # Common Latin-Cyrillic homoglyphs
        homoglyph_pairs = {
            ('a', 'а'),  # Latin a vs Cyrillic a
            ('e', 'е'),  # Latin e vs Cyrillic e
            ('o', 'о'),  # Latin o vs Cyrillic o
            ('p', 'р'),  # Latin p vs Cyrillic p
            ('c', 'с'),  # Latin c vs Cyrillic c
        }

        for latin, cyrillic in homoglyph_pairs:
            if cyrillic in text:
                issues.append(ValidationIssue(
                    code="VAL_UNI_006",
                    message=f"Text contains potential homoglyph: '{cyrillic}' "
                            f"(Cyrillic) looks like '{latin}' (Latin)",
                    severity=ValidationSeverity.WARNING,
                    field="text",
                    suggestion="Check for unintentional non-Latin characters",
                ))

        return issues
```

#### `length_validator.py`

Length validation and truncation detection.

```python
"""Length validation for text inputs."""

from .validation_config import ValidationConfig
from .validation_errors import LengthValidationError
from .validation_result import ValidationIssue, ValidationSeverity


class LengthValidator:
    """Validates text length constraints.

    Checks:
    - Minimum/maximum character length
    - Maximum word count
    - Truncation detection
    - Empty text detection
    """

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate(self, text: str) -> list[ValidationIssue]:
        """Validate text length.

        Args:
            text: Input text to validate

        Returns:
            List of validation issues

        Raises:
            LengthValidationError: If length constraints are violated
        """
        issues: list[ValidationIssue] = []

        # Check minimum length
        if len(text) < self.config.min_length:
            raise LengthValidationError(
                message=f"Text too short: {len(text)} characters "
                        f"(minimum: {self.config.min_length})",
                error_code="VAL_LEN_001",
                field="text",
                suggestion=f"Provide at least {self.config.min_length} characters",
            )

        # Check maximum length
        if len(text) > self.config.max_length:
            raise LengthValidationError(
                message=f"Text too long: {len(text)} characters "
                        f"(maximum: {self.config.max_length})",
                error_code="VAL_LEN_002",
                field="text",
                suggestion=f"Reduce text to {self.config.max_length} characters or less",
            )

        # Check word count
        word_count = len(text.split())
        if word_count > self.config.max_word_count:
            raise LengthValidationError(
                message=f"Text has too many words: {word_count} "
                        f"(maximum: {self.config.max_word_count})",
                error_code="VAL_LEN_003",
                field="text",
                suggestion=f"Reduce to {self.config.max_word_count} words or less",
            )

        # Detect potential truncation
        truncation_indicators = ['...', '…', '[truncated]', '(cont.)']
        for indicator in truncation_indicators:
            if text.rstrip().endswith(indicator):
                issues.append(ValidationIssue(
                    code="VAL_LEN_004",
                    message=f"Text appears truncated (ends with '{indicator}')",
                    severity=ValidationSeverity.WARNING,
                    field="text",
                    suggestion="Provide complete text without truncation",
                ))
                break

        # Check for suspiciously short claims
        if word_count < 3:
            issues.append(ValidationIssue(
                code="VAL_LEN_005",
                message=f"Very short claim: {word_count} word(s)",
                severity=ValidationSeverity.WARNING,
                field="text",
                suggestion="Claims should typically be complete sentences",
            ))

        return issues
```

#### `special_char_validator.py`

Special character validation.

```python
"""Special character validation for security and compatibility."""

import re
import unicodedata
from typing import Optional

from .validation_config import ValidationConfig
from .validation_errors import SpecialCharValidationError
from .validation_result import ValidationIssue, ValidationSeverity


class SpecialCharValidator:
    """Validates special characters and control codes.

    Security checks:
    - Control characters (potential injection)
    - Zero-width characters (steganography/obfuscation)
    - Invalid Unicode categories
    - Suspicious patterns
    """

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate(self, text: str) -> tuple[str, list[ValidationIssue]]:
        """Validate special characters in text.

        Args:
            text: Input text to validate

        Returns:
            Tuple of (normalized_text, issues)

        Raises:
            SpecialCharValidationError: If disallowed characters found
        """
        issues: list[ValidationIssue] = []
        normalized = text

        # Check for control characters
        if self.config.disallowed_control_chars:
            control_chars = self._find_control_chars(text)
            if control_chars:
                # Allow common whitespace control chars
                allowed_control = {'\n', '\r', '\t'}
                disallowed = [c for c in control_chars if c not in allowed_control]

                if disallowed:
                    raise SpecialCharValidationError(
                        message=f"Text contains {len(disallowed)} disallowed "
                                f"control character(s): "
                                f"{', '.join(repr(c) for c in disallowed[:3])}",
                        error_code="VAL_CHAR_001",
                        field="text",
                        suggestion="Remove control characters from input",
                    )

        # Check for zero-width characters
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space (BOM)
        ]

        for zwc in zero_width_chars:
            if zwc in text:
                if not self.config.allow_zero_width_chars:
                    raise SpecialCharValidationError(
                        message=f"Text contains zero-width character: {repr(zwc)}",
                        error_code="VAL_CHAR_002",
                        field="text",
                        suggestion="Remove invisible zero-width characters",
                    )
                else:
                    issues.append(ValidationIssue(
                        code="VAL_CHAR_003",
                        message=f"Text contains zero-width character: {repr(zwc)}",
                        severity=ValidationSeverity.INFO,
                        field="text",
                    ))

        # Validate Unicode categories
        invalid_chars = self._find_invalid_categories(text)
        if invalid_chars:
            raise SpecialCharValidationError(
                message=f"Text contains {len(invalid_chars)} character(s) "
                        f"with disallowed Unicode categories",
                error_code="VAL_CHAR_004",
                field="text",
                suggestion="Remove unsupported characters",
            )

        # Check for suspicious patterns
        suspicious = self._detect_suspicious_patterns(text)
        issues.extend(suspicious)

        return normalized, issues

    def _find_control_chars(self, text: str) -> list[str]:
        """Find control characters in text."""
        return [c for c in text if unicodedata.category(c) == 'Cc']

    def _find_invalid_categories(self, text: str) -> list[str]:
        """Find characters with disallowed Unicode categories."""
        invalid = []
        for char in text:
            category = unicodedata.category(char)
            if category not in self.config.allowed_char_categories:
                invalid.append(char)
        return invalid

    def _detect_suspicious_patterns(self, text: str) -> list[ValidationIssue]:
        """Detect suspicious character patterns."""
        issues = []

        # Excessive repetition of special characters
        special_char_pattern = r'([^\w\s])\1{5,}'
        matches = re.finditer(special_char_pattern, text)
        for match in matches:
            issues.append(ValidationIssue(
                code="VAL_CHAR_005",
                message=f"Excessive repetition of special character: '{match.group(1)}'",
                severity=ValidationSeverity.WARNING,
                field="text",
                suggestion="Check for input errors or spam",
            ))

        # Mixed directional formatting (potential spoofing)
        directional_marks = [
            '\u202a',  # Left-to-right embedding
            '\u202b',  # Right-to-left embedding
            '\u202c',  # Pop directional formatting
            '\u202d',  # Left-to-right override
            '\u202e',  # Right-to-left override
        ]

        found_marks = [mark for mark in directional_marks if mark in text]
        if len(found_marks) > 1:
            issues.append(ValidationIssue(
                code="VAL_CHAR_006",
                message="Text contains multiple directional formatting marks",
                severity=ValidationSeverity.WARNING,
                field="text",
                suggestion="Remove directional formatting characters",
            ))

        return issues
```

---

## 2. ClaimValidator Class Design

The `ClaimValidator` is the main orchestrator that coordinates all validation steps.

### Class Definition

```python
"""Main claim validator orchestrator."""

import hashlib
import time
from functools import lru_cache
from typing import Optional

import structlog

from .encoding_validator import EncodingValidator
from .length_validator import LengthValidator
from .special_char_validator import SpecialCharValidator
from .unicode_normalizer import UnicodeNormalizer
from .validation_config import ValidationConfig
from .validation_errors import ValidationError
from .validation_result import ValidationIssue, ValidationResult, ValidationSeverity

logger = structlog.get_logger(__name__)


class ClaimValidator:
    """Main validator for claim text inputs.

    Orchestrates all validation steps:
    1. Encoding validation
    2. Length validation
    3. Unicode normalization
    4. Special character validation
    5. Structural validation

    Features:
    - Configurable validation profiles
    - Result caching for performance
    - Detailed error reporting
    - Early exit on errors (fail-fast)

    Usage:
        >>> config = ValidationConfig.standard()
        >>> validator = ClaimValidator(config)
        >>> result = validator.validate("The Earth orbits the Sun")
        >>> if result.valid:
        ...     text = result.normalized_text
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize validator with configuration.

        Args:
            config: Validation configuration (uses standard profile if None)
        """
        self.config = config or ValidationConfig()

        # Initialize component validators
        self.encoding_validator = EncodingValidator(self.config)
        self.length_validator = LengthValidator(self.config)
        self.unicode_normalizer = UnicodeNormalizer(self.config)
        self.special_char_validator = SpecialCharValidator(self.config)

        logger.info(
            "claim_validator_initialized",
            profile=self.config.profile.value,
            min_length=self.config.min_length,
            max_length=self.config.max_length,
            caching_enabled=self.config.enable_caching,
        )

    def validate(self, text: str, *, fail_fast: bool = True) -> ValidationResult:
        """Validate claim text.

        Args:
            text: Claim text to validate
            fail_fast: Stop on first error (default: True)

        Returns:
            ValidationResult with normalized text and issues

        Raises:
            ValidationError: If validation fails and fail_fast=True

        Example:
            >>> result = validator.validate("Test claim")
            >>> if result.valid:
            ...     print(f"Valid: {result.normalized_text}")
            ... else:
            ...     for error in result.get_errors():
            ...         print(f"Error: {error.message}")
        """
        start_time = time.perf_counter()
        all_issues: list[ValidationIssue] = []
        normalized = text

        try:
            # Step 1: Basic sanitization
            if self.config.strip_leading_trailing:
                normalized = normalized.strip()

            # Check for empty text after stripping
            if not normalized:
                return ValidationResult(
                    valid=False,
                    issues=[ValidationIssue(
                        code="VAL_001",
                        message="Text is empty after normalization",
                        severity=ValidationSeverity.ERROR,
                        field="text",
                        suggestion="Provide non-empty text",
                    )],
                )

            # Step 2: Encoding validation (fail-fast)
            try:
                normalized, encoding_issues = self.encoding_validator.validate(normalized)
                all_issues.extend(encoding_issues)
            except ValidationError as e:
                if fail_fast:
                    raise
                all_issues.append(self._error_to_issue(e))

            # Step 3: Length validation (fail-fast)
            try:
                length_issues = self.length_validator.validate(normalized)
                all_issues.extend(length_issues)
            except ValidationError as e:
                if fail_fast:
                    raise
                all_issues.append(self._error_to_issue(e))

            # Step 4: Unicode normalization (fail-fast)
            try:
                normalized, unicode_issues = self.unicode_normalizer.validate_and_normalize(
                    normalized
                )
                all_issues.extend(unicode_issues)
            except ValidationError as e:
                if fail_fast:
                    raise
                all_issues.append(self._error_to_issue(e))

            # Step 5: Special character validation (fail-fast)
            try:
                normalized, char_issues = self.special_char_validator.validate(normalized)
                all_issues.extend(char_issues)
            except ValidationError as e:
                if fail_fast:
                    raise
                all_issues.append(self._error_to_issue(e))

            # Step 6: Structural validation (whitespace)
            if self.config.normalize_whitespace:
                original = normalized
                normalized = self._normalize_whitespace(normalized)
                if normalized != original:
                    all_issues.append(ValidationIssue(
                        code="VAL_002",
                        message="Whitespace normalized",
                        severity=ValidationSeverity.INFO,
                        field="text",
                    ))

            # Validation succeeded
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Check if we have any errors despite not raising
            has_errors = any(i.severity == ValidationSeverity.ERROR for i in all_issues)

            result = ValidationResult(
                valid=not has_errors,
                normalized_text=normalized,
                issues=all_issues,
                metadata={
                    "validation_time_ms": round(elapsed_ms, 2),
                    "profile": self.config.profile.value,
                    "original_length": len(text),
                    "normalized_length": len(normalized),
                },
            )

            logger.debug(
                "validation_completed",
                valid=result.valid,
                issues_count=len(all_issues),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return result

        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Unexpected error during validation
            logger.error(
                "validation_unexpected_error",
                error=str(e),
                exc_info=True,
            )
            raise ValidationError(
                message=f"Unexpected validation error: {e}",
                error_code="VAL_999",
                field="text",
            ) from e

    def validate_batch(
        self,
        texts: list[str],
        *,
        fail_fast: bool = False,
    ) -> list[ValidationResult]:
        """Validate multiple claims in batch.

        Args:
            texts: List of claim texts to validate
            fail_fast: Stop on first error (default: False for batch)

        Returns:
            List of ValidationResult objects

        Example:
            >>> claims = ["Claim 1", "Claim 2", "Claim 3"]
            >>> results = validator.validate_batch(claims)
            >>> valid_claims = [
            ...     r.normalized_text for r in results if r.valid
            ... ]
        """
        start_time = time.perf_counter()
        results = []

        for i, text in enumerate(texts):
            try:
                result = self.validate(text, fail_fast=fail_fast)
                results.append(result)
            except ValidationError as e:
                if fail_fast:
                    raise
                # Create failed result
                results.append(ValidationResult(
                    valid=False,
                    issues=[self._error_to_issue(e)],
                ))

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "batch_validation_completed",
            total_count=len(texts),
            valid_count=sum(1 for r in results if r.valid),
            invalid_count=sum(1 for r in results if not r.valid),
            elapsed_ms=round(elapsed_ms, 2),
            avg_per_text_ms=round(elapsed_ms / len(texts), 2) if texts else 0,
        )

        return results

    @staticmethod
    def _error_to_issue(error: ValidationError) -> ValidationIssue:
        """Convert ValidationError to ValidationIssue."""
        return ValidationIssue(
            code=error.error_code,
            message=error.message,
            severity=ValidationSeverity.ERROR,
            field=error.field,
            suggestion=error.suggestion,
        )

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        - Collapse multiple spaces to single space
        - Normalize line breaks
        - Remove excessive consecutive whitespace
        """
        import re

        # Normalize line breaks to \n
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')

        # Collapse multiple spaces
        normalized = re.sub(r' {2,}', ' ', normalized)

        # Limit consecutive whitespace
        max_ws = self.config.max_consecutive_whitespace
        normalized = re.sub(
            f'\\s{{{max_ws + 1},}}',
            ' ' * max_ws,
            normalized
        )

        return normalized

    def validate_cached(self, text: str) -> ValidationResult:
        """Validate with caching enabled.

        Uses LRU cache to avoid revalidating identical text.
        Cache key is SHA-256 hash of text + config profile.

        Args:
            text: Claim text to validate

        Returns:
            ValidationResult (may be cached)
        """
        if not self.config.enable_caching:
            return self.validate(text)

        cache_key = self._compute_cache_key(text)
        return self._validate_with_cache(cache_key, text)

    @lru_cache(maxsize=1000)
    def _validate_with_cache(self, cache_key: str, text: str) -> ValidationResult:
        """Internal cached validation (decorated with lru_cache)."""
        result = self.validate(text)
        result.metadata["cached"] = False
        return result

    def _compute_cache_key(self, text: str) -> str:
        """Compute cache key for text."""
        content = f"{self.config.profile.value}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear validation cache."""
        self._validate_with_cache.cache_clear()
        logger.info("validation_cache_cleared")
```

---

## 3. Validation Rules Reference

### Error Codes

#### Encoding Errors (VAL_ENC_XXX)

| Code | Severity | Message | Suggestion |
|------|----------|---------|------------|
| VAL_ENC_001 | INFO | BOM detected and removed | None (auto-fixed) |
| VAL_ENC_002 | WARNING | BOM detected in text | Remove BOM character |
| VAL_ENC_003 | ERROR | Replacement characters found | Ensure UTF-8 encoding |
| VAL_ENC_004 | ERROR | Null bytes in text | Remove null bytes |
| VAL_ENC_005 | ERROR | Cannot encode as UTF-8 | Use valid UTF-8 characters |

#### Length Errors (VAL_LEN_XXX)

| Code | Severity | Message | Suggestion |
|------|----------|---------|------------|
| VAL_LEN_001 | ERROR | Text too short | Provide more text |
| VAL_LEN_002 | ERROR | Text too long | Reduce length |
| VAL_LEN_003 | ERROR | Too many words | Reduce word count |
| VAL_LEN_004 | WARNING | Text appears truncated | Provide complete text |
| VAL_LEN_005 | WARNING | Very short claim | Use complete sentence |

#### Unicode Errors (VAL_UNI_XXX)

| Code | Severity | Message | Suggestion |
|------|----------|---------|------------|
| VAL_UNI_001 | INFO | Text normalized | None (auto-fixed) |
| VAL_UNI_002 | ERROR | Too many combining chars | Reduce diacritics |
| VAL_UNI_003 | ERROR | RTL scripts not allowed | Use LTR scripts only |
| VAL_UNI_004 | INFO | RTL characters detected | None (informational) |
| VAL_UNI_005 | WARNING | Multiple scripts detected | Check for typos |
| VAL_UNI_006 | WARNING | Homoglyph detected | Use Latin characters |

#### Character Errors (VAL_CHAR_XXX)

| Code | Severity | Message | Suggestion |
|------|----------|---------|------------|
| VAL_CHAR_001 | ERROR | Control characters found | Remove control chars |
| VAL_CHAR_002 | ERROR | Zero-width characters | Remove invisible chars |
| VAL_CHAR_003 | INFO | Zero-width char allowed | None (informational) |
| VAL_CHAR_004 | ERROR | Invalid Unicode category | Use supported characters |
| VAL_CHAR_005 | WARNING | Excessive special char repetition | Check for spam |
| VAL_CHAR_006 | WARNING | Multiple directional marks | Remove formatting |

#### General Errors (VAL_XXX)

| Code | Severity | Message | Suggestion |
|------|----------|---------|------------|
| VAL_001 | ERROR | Empty text | Provide non-empty text |
| VAL_002 | INFO | Whitespace normalized | None (auto-fixed) |
| VAL_999 | ERROR | Unexpected validation error | Contact support |

### Validation Profiles

#### STRICT Profile

```python
ValidationConfig(
    profile=ValidationProfile.STRICT,
    min_length=5,
    max_length=1000,
    max_word_count=200,
    check_homoglyphs=True,
    allow_zero_width_chars=False,
    disallowed_control_chars=True,
)
```

**Use cases**: API endpoints, public submissions, untrusted input

#### STANDARD Profile (Default)

```python
ValidationConfig(
    profile=ValidationProfile.STANDARD,
    min_length=1,
    max_length=2000,
    max_word_count=500,
    check_homoglyphs=True,
    allow_zero_width_chars=False,
    disallowed_control_chars=True,
)
```

**Use cases**: General purpose, verified users, batch processing

#### LENIENT Profile

```python
ValidationConfig(
    profile=ValidationProfile.LENIENT,
    min_length=1,
    max_length=5000,
    max_word_count=1000,
    check_homoglyphs=False,
    allow_zero_width_chars=True,
    disallowed_control_chars=False,
)
```

**Use cases**: Testing, development, administrative operations

---

## 4. Error Response Design

### JSON Schema

```json
{
  "type": "object",
  "required": ["valid", "issues"],
  "properties": {
    "valid": {
      "type": "boolean",
      "description": "Whether input passed validation"
    },
    "normalized_text": {
      "type": ["string", "null"],
      "description": "Normalized/sanitized version of input (null if invalid)"
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["code", "message", "severity"],
        "properties": {
          "code": {
            "type": "string",
            "pattern": "^VAL_[A-Z]+_\\d{3}$",
            "description": "Machine-readable error code"
          },
          "message": {
            "type": "string",
            "description": "Human-readable error message"
          },
          "severity": {
            "type": "string",
            "enum": ["error", "warning", "info"],
            "description": "Issue severity level"
          },
          "field": {
            "type": ["string", "null"],
            "description": "Field that caused the issue"
          },
          "suggestion": {
            "type": ["string", "null"],
            "description": "Suggested fix for the issue"
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "description": "Additional validation metadata",
      "properties": {
        "validation_time_ms": {
          "type": "number",
          "description": "Validation time in milliseconds"
        },
        "profile": {
          "type": "string",
          "description": "Validation profile used"
        },
        "original_length": {
          "type": "integer",
          "description": "Original text length"
        },
        "normalized_length": {
          "type": "integer",
          "description": "Normalized text length"
        }
      }
    }
  }
}
```

### Example Responses

#### Success with Normalization

```json
{
  "valid": true,
  "normalized_text": "The Earth orbits the Sun",
  "issues": [
    {
      "code": "VAL_002",
      "message": "Whitespace normalized",
      "severity": "info",
      "field": "text",
      "suggestion": null
    }
  ],
  "metadata": {
    "validation_time_ms": 2.34,
    "profile": "standard",
    "original_length": 26,
    "normalized_length": 24
  }
}
```

#### Validation Error

```json
{
  "valid": false,
  "normalized_text": null,
  "issues": [
    {
      "code": "VAL_LEN_002",
      "message": "Text too long: 2500 characters (maximum: 2000)",
      "severity": "error",
      "field": "text",
      "suggestion": "Reduce text to 2000 characters or less"
    }
  ],
  "metadata": {
    "validation_time_ms": 1.12,
    "profile": "standard",
    "original_length": 2500,
    "normalized_length": null
  }
}
```

#### Multiple Warnings

```json
{
  "valid": true,
  "normalized_text": "This claim contains مرحبا mixed scripts",
  "issues": [
    {
      "code": "VAL_UNI_004",
      "message": "Text contains RTL script characters",
      "severity": "info",
      "field": "text",
      "suggestion": null
    },
    {
      "code": "VAL_UNI_005",
      "message": "Text contains 2 different scripts: LATIN, ARABIC",
      "severity": "warning",
      "field": "text",
      "suggestion": "Mixed scripts may indicate suspicious input"
    }
  ],
  "metadata": {
    "validation_time_ms": 3.45,
    "profile": "standard",
    "original_length": 40,
    "normalized_length": 40
  }
}
```

---

## 5. Testing Strategy

### Test Structure

```
tests/unit/validation/
├── __init__.py
├── test_claim_validator.py           # Main validator tests
├── test_encoding_validator.py        # Encoding tests
├── test_unicode_normalizer.py        # Unicode tests
├── test_length_validator.py          # Length tests
├── test_special_char_validator.py    # Special char tests
├── test_validation_config.py         # Configuration tests
└── test_validation_integration.py    # Integration tests

tests/fixtures/validation/
├── __init__.py
├── conftest.py                       # Test fixtures
├── valid_claims.json                 # Valid test cases
├── invalid_claims.json               # Invalid test cases
└── edge_cases.json                   # Edge case claims
```

### Test Categories

#### 1. Unit Tests

Test each validator component independently.

```python
"""Unit tests for encoding validator."""

import pytest
from truthgraph.validation import (
    EncodingValidationError,
    ValidationConfig,
)
from truthgraph.validation.encoding_validator import EncodingValidator


class TestEncodingValidator:
    """Unit tests for EncodingValidator."""

    @pytest.fixture
    def validator(self) -> EncodingValidator:
        """Create validator with default config."""
        return EncodingValidator(ValidationConfig())

    def test_valid_utf8(self, validator: EncodingValidator):
        """Test validation of valid UTF-8 text."""
        text = "The Earth orbits the Sun"
        normalized, issues = validator.validate(text)

        assert normalized == text
        assert len(issues) == 0

    def test_bom_removal(self, validator: EncodingValidator):
        """Test BOM detection and removal."""
        text = '\ufeffHello World'
        normalized, issues = validator.validate(text)

        assert normalized == 'Hello World'
        assert len(issues) == 1
        assert issues[0].code == "VAL_ENC_001"

    def test_replacement_character_error(self, validator: EncodingValidator):
        """Test error on replacement characters."""
        text = 'Invalid \ufffd character'

        with pytest.raises(EncodingValidationError) as exc_info:
            validator.validate(text)

        assert exc_info.value.error_code == "VAL_ENC_003"
        assert "replacement character" in exc_info.value.message.lower()

    def test_null_byte_error(self, validator: EncodingValidator):
        """Test error on null bytes."""
        text = 'Text with \x00 null byte'

        with pytest.raises(EncodingValidationError) as exc_info:
            validator.validate(text)

        assert exc_info.value.error_code == "VAL_ENC_004"
```

#### 2. Integration Tests

Test full validation pipeline.

```python
"""Integration tests for ClaimValidator."""

import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig, ValidationProfile


class TestClaimValidatorIntegration:
    """Integration tests for full validation pipeline."""

    @pytest.fixture
    def validator(self) -> ClaimValidator:
        """Create validator with standard config."""
        return ClaimValidator(ValidationConfig())

    def test_valid_claim(self, validator: ClaimValidator):
        """Test validation of valid claim."""
        result = validator.validate("The Earth is approximately 4.54 billion years old")

        assert result.valid
        assert result.normalized_text is not None
        assert result.metadata["validation_time_ms"] < 10  # Performance requirement

    def test_length_error(self, validator: ClaimValidator):
        """Test length validation error."""
        long_text = "x" * 3000  # Exceeds default max_length
        result = validator.validate(long_text, fail_fast=False)

        assert not result.valid
        assert any(issue.code == "VAL_LEN_002" for issue in result.get_errors())

    def test_batch_validation(self, validator: ClaimValidator):
        """Test batch validation."""
        claims = [
            "Valid claim 1",
            "Valid claim 2",
            "",  # Invalid: empty
            "Valid claim 3",
        ]

        results = validator.validate_batch(claims, fail_fast=False)

        assert len(results) == 4
        assert results[0].valid
        assert results[1].valid
        assert not results[2].valid
        assert results[3].valid
```

#### 3. Edge Case Tests

Use Feature 3.3 test data for comprehensive edge case coverage.

```python
"""Edge case tests using Feature 3.3 test data."""

import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig


@pytest.fixture
def strict_validator() -> ClaimValidator:
    """Create validator with strict profile."""
    return ClaimValidator(ValidationConfig.strict())


@pytest.fixture
def lenient_validator() -> ClaimValidator:
    """Create validator with lenient profile."""
    return ClaimValidator(ValidationConfig.lenient())


class TestEdgeCases:
    """Test validation with edge case data from Feature 3.3."""

    def test_special_characters(
        self,
        edge_case_special_characters,
        strict_validator,
    ):
        """Test special character handling."""
        for claim_data in edge_case_special_characters["claims"]:
            text = claim_data["text"]
            result = strict_validator.validate(text, fail_fast=False)

            # Should handle special chars without crashing
            assert result is not None

    def test_long_claims(
        self,
        edge_case_long_claims,
        strict_validator,
        lenient_validator,
    ):
        """Test long claim handling."""
        for claim_data in edge_case_long_claims["claims"]:
            text = claim_data["text"]

            # Strict validator should reject very long claims
            strict_result = strict_validator.validate(text, fail_fast=False)
            assert not strict_result.valid

            # Lenient validator may accept
            lenient_result = lenient_validator.validate(text, fail_fast=False)
            # Depends on length, but should not crash
            assert lenient_result is not None

    def test_short_claims(self, edge_case_short_claims, strict_validator):
        """Test short claim handling."""
        for claim_data in edge_case_short_claims["claims"]:
            text = claim_data["text"]
            result = strict_validator.validate(text, fail_fast=False)

            # Should warn about short claims
            if result.valid and len(text.split()) < 3:
                assert any(
                    issue.code == "VAL_LEN_005"
                    for issue in result.get_warnings()
                )
```

#### 4. Property-Based Tests

Use Hypothesis for generative testing.

```python
"""Property-based tests for validation."""

from hypothesis import given, strategies as st
import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig


@pytest.fixture
def validator() -> ClaimValidator:
    """Create validator for property tests."""
    return ClaimValidator(ValidationConfig())


class TestValidationProperties:
    """Property-based tests using Hypothesis."""

    @given(st.text(min_size=1, max_size=100))
    def test_validation_never_crashes(
        self,
        validator: ClaimValidator,
        text: str,
    ):
        """Test that validation never crashes on any text."""
        try:
            result = validator.validate(text, fail_fast=False)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Validation crashed on text: {repr(text)}, error: {e}")

    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=10,
            max_size=100,
        )
    )
    def test_normal_text_validates(self, validator: ClaimValidator, text: str):
        """Test that normal Latin text always validates."""
        result = validator.validate(text, fail_fast=False)
        # May have warnings but should not have errors for normal text
        assert not result.has_errors or len(text.strip()) == 0

    @given(st.text(min_size=1, max_size=100))
    def test_validation_idempotent(self, validator: ClaimValidator, text: str):
        """Test that validating twice gives same result."""
        try:
            result1 = validator.validate(text, fail_fast=False)
            result2 = validator.validate(text, fail_fast=False)

            assert result1.valid == result2.valid
            assert result1.normalized_text == result2.normalized_text
        except Exception:
            # If first validation raises, second should too
            with pytest.raises(Exception):
                validator.validate(text, fail_fast=False)
```

#### 5. Performance Tests

```python
"""Performance tests for validation."""

import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig


class TestValidationPerformance:
    """Performance benchmarks for validation."""

    @pytest.fixture
    def validator(self) -> ClaimValidator:
        """Create validator for performance tests."""
        return ClaimValidator(ValidationConfig())

    def test_single_validation_performance(
        self,
        validator: ClaimValidator,
        benchmark,
    ):
        """Test single validation performance (<10ms requirement)."""
        text = "The Earth orbits the Sun in approximately 365.25 days"

        result = benchmark(validator.validate, text)

        assert result.valid
        assert result.metadata["validation_time_ms"] < 10

    def test_batch_validation_performance(
        self,
        validator: ClaimValidator,
        benchmark,
    ):
        """Test batch validation performance."""
        claims = [f"Test claim number {i}" for i in range(100)]

        results = benchmark(validator.validate_batch, claims)

        assert len(results) == 100
        # Average should be under 10ms per claim
        total_time = sum(r.metadata["validation_time_ms"] for r in results)
        assert total_time / 100 < 10

    @pytest.mark.parametrize("text_length", [10, 100, 500, 1000, 2000])
    def test_performance_scales_linearly(
        self,
        validator: ClaimValidator,
        text_length: int,
        benchmark,
    ):
        """Test that performance scales linearly with text length."""
        text = "word " * (text_length // 5)  # ~5 chars per word

        result = benchmark(validator.validate, text)

        # Should scale roughly linearly, allow some overhead
        expected_max_ms = 0.01 * text_length + 5
        assert result.metadata["validation_time_ms"] < expected_max_ms
```

### Test Fixtures

```python
"""Pytest fixtures for validation tests."""

import json
from pathlib import Path
import pytest
from truthgraph.validation import ValidationConfig, ClaimValidator


@pytest.fixture
def validation_test_data_dir() -> Path:
    """Get validation test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def valid_claims(validation_test_data_dir: Path) -> list[dict]:
    """Load valid claim test cases."""
    with open(validation_test_data_dir / "valid_claims.json") as f:
        return json.load(f)


@pytest.fixture
def invalid_claims(validation_test_data_dir: Path) -> list[dict]:
    """Load invalid claim test cases."""
    with open(validation_test_data_dir / "invalid_claims.json") as f:
        return json.load(f)


@pytest.fixture
def standard_validator() -> ClaimValidator:
    """Create validator with standard profile."""
    return ClaimValidator(ValidationConfig())


@pytest.fixture
def strict_validator() -> ClaimValidator:
    """Create validator with strict profile."""
    return ClaimValidator(ValidationConfig.strict())


@pytest.fixture
def lenient_validator() -> ClaimValidator:
    """Create validator with lenient profile."""
    return ClaimValidator(ValidationConfig.lenient())
```

---

## 6. Performance Optimization

### Optimization Strategies

#### 1. Early Validation (Fail Fast)

```python
# Check cheapest validations first
def validate(self, text: str, fail_fast: bool = True):
    # 1. Empty check (fastest)
    if not text.strip():
        return ValidationResult(valid=False, ...)

    # 2. Length check (very fast)
    if len(text) > self.config.max_length:
        raise LengthValidationError(...)

    # 3. Encoding (fast)
    text, issues = self.encoding_validator.validate(text)

    # 4. Unicode normalization (moderate)
    text, issues = self.unicode_normalizer.validate_and_normalize(text)

    # 5. Special char validation (expensive)
    text, issues = self.special_char_validator.validate(text)
```

#### 2. Caching Validation Results

```python
# Use LRU cache for repeated validations
from functools import lru_cache
import hashlib

class ClaimValidator:
    @lru_cache(maxsize=1000)
    def _validate_cached(self, cache_key: str, text: str) -> ValidationResult:
        return self.validate(text)

    def validate_cached(self, text: str) -> ValidationResult:
        """Validate with caching."""
        cache_key = hashlib.sha256(
            f"{self.config.profile.value}:{text}".encode()
        ).hexdigest()
        return self._validate_cached(cache_key, text)
```

Cache hit rate: Target >70% in production workloads.

#### 3. Lazy Evaluation

```python
# Only run expensive checks if needed
class ClaimValidator:
    def validate(self, text: str):
        # Skip homoglyph detection if not configured
        if not self.config.check_homoglyphs:
            # Skip expensive Unicode analysis
            pass

        # Skip RTL checks if not needed
        if not self._has_non_latin(text):
            # Skip bidirectional analysis
            pass
```

#### 4. Batch Processing

```python
# Process multiple claims efficiently
def validate_batch(self, texts: list[str]) -> list[ValidationResult]:
    # Could parallelize if needed
    results = []
    for text in texts:
        result = self.validate(text)
        results.append(result)
    return results
```

Consider parallel validation for large batches (>100 claims).

#### 5. Profiling Strategy

```python
# Profile validation performance
import cProfile
import pstats

def profile_validation():
    validator = ClaimValidator()
    test_claims = load_test_claims()

    profiler = cProfile.Profile()
    profiler.enable()

    for claim in test_claims:
        validator.validate(claim)

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
```

**Profile targets**:
- Encoding validation: <1ms
- Length validation: <0.5ms
- Unicode normalization: <3ms
- Special char validation: <2ms
- Total: <10ms (including overhead)

### Memory Optimization

```python
# Use generators for large batches
def validate_batch_streaming(
    self,
    texts: Iterable[str],
) -> Iterator[ValidationResult]:
    """Stream validation results to avoid memory buildup."""
    for text in texts:
        yield self.validate(text)

# Clear cache periodically
validator.clear_cache()  # Clear LRU cache
```

---

## 7. Configuration Management

### Configuration Sources

1. **Default values**: Built into `ValidationConfig`
2. **Environment variables**: Override via env vars
3. **Configuration files**: YAML/TOML configuration
4. **Runtime overrides**: Programmatic configuration

### Environment Variables

```bash
# Validation profile
TRUTHGRAPH_VALIDATION_PROFILE=strict

# Length limits
TRUTHGRAPH_VALIDATION_MIN_LENGTH=5
TRUTHGRAPH_VALIDATION_MAX_LENGTH=2000
TRUTHGRAPH_VALIDATION_MAX_WORD_COUNT=500

# Unicode
TRUTHGRAPH_VALIDATION_UNICODE_NORMALIZATION=NFC
TRUTHGRAPH_VALIDATION_CHECK_HOMOGLYPHS=true

# Performance
TRUTHGRAPH_VALIDATION_ENABLE_CACHING=true
TRUTHGRAPH_VALIDATION_CACHE_TTL=3600
```

### Configuration File

```yaml
# config/validation.yaml
validation:
  profile: standard

  length:
    min_length: 1
    max_length: 2000
    max_word_count: 500

  encoding:
    allowed_encodings:
      - utf-8
    normalize_encoding: true
    strip_bom: true

  unicode:
    normalization: NFC
    allow_rtl_scripts: true
    max_combining_chars: 10
    check_homoglyphs: true

  special_chars:
    disallowed_control_chars: true
    allow_zero_width_chars: false

  structure:
    normalize_whitespace: true
    max_consecutive_whitespace: 5
    strip_leading_trailing: true

  performance:
    enable_caching: true
    cache_ttl_seconds: 3600
```

### Loading Configuration

```python
"""Configuration loading utilities."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings

from truthgraph.validation import ValidationConfig, ValidationProfile


class ValidationSettings(BaseSettings):
    """Validation settings from environment."""

    validation_profile: ValidationProfile = ValidationProfile.STANDARD
    validation_min_length: int = 1
    validation_max_length: int = 2000
    validation_max_word_count: int = 500
    validation_check_homoglyphs: bool = True
    validation_enable_caching: bool = True

    class Config:
        env_prefix = "TRUTHGRAPH_"
        case_sensitive = False


def load_config_from_env() -> ValidationConfig:
    """Load configuration from environment variables."""
    settings = ValidationSettings()

    return ValidationConfig(
        profile=settings.validation_profile,
        min_length=settings.validation_min_length,
        max_length=settings.validation_max_length,
        max_word_count=settings.validation_max_word_count,
        check_homoglyphs=settings.validation_check_homoglyphs,
        enable_caching=settings.validation_enable_caching,
    )


def load_config_from_file(path: Path) -> ValidationConfig:
    """Load configuration from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    val_config = data.get("validation", {})

    return ValidationConfig(
        profile=ValidationProfile(val_config.get("profile", "standard")),
        min_length=val_config.get("length", {}).get("min_length", 1),
        max_length=val_config.get("length", {}).get("max_length", 2000),
        # ... etc
    )


def get_validator(
    config_file: Optional[Path] = None,
) -> "ClaimValidator":
    """Get configured validator instance.

    Priority:
    1. Config file (if provided)
    2. Environment variables
    3. Defaults
    """
    from truthgraph.validation import ClaimValidator

    if config_file and config_file.exists():
        config = load_config_from_file(config_file)
    else:
        config = load_config_from_env()

    return ClaimValidator(config)
```

---

## 8. Integration Points

### 8.1 API Endpoints (Feature 4.1)

Integrate validation into FastAPI request handlers.

```python
"""API integration for validation."""

from fastapi import APIRouter, HTTPException, Depends
from truthgraph.api.models import VerifyRequest, VerifyResponse
from truthgraph.validation import (
    ClaimValidator,
    ValidationError,
    ValidationResult,
)

router = APIRouter()


def get_claim_validator() -> ClaimValidator:
    """Dependency injection for claim validator."""
    from truthgraph.validation.config_loader import get_validator
    return get_validator()


@router.post("/api/v1/claims/verify", response_model=VerifyResponse)
async def verify_claim(
    request: VerifyRequest,
    validator: ClaimValidator = Depends(get_claim_validator),
):
    """Verify a claim with input validation."""
    # Validate claim text
    try:
        validation_result = validator.validate(request.claim)

        if not validation_result.valid:
            # Return 400 with validation errors
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Claim text failed validation",
                    "validation_errors": [
                        issue.to_dict()
                        for issue in validation_result.get_errors()
                    ],
                },
            )

        # Use normalized text for processing
        normalized_claim = validation_result.normalized_text

        # Log validation warnings if any
        if validation_result.has_warnings:
            logger.warning(
                "claim_validation_warnings",
                warnings=[w.to_dict() for w in validation_result.get_warnings()],
            )

        # Continue with verification pipeline
        result = await verification_service.verify(
            claim=normalized_claim,
            tenant_id=request.tenant_id,
            max_evidence=request.max_evidence,
        )

        return result

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": e.message,
                "error_code": e.error_code,
                "suggestion": e.suggestion,
            },
        )
```

### 8.2 Background Tasks (Feature 4.3)

Validate claims in batch processing jobs.

```python
"""Background task integration."""

from typing import List
from truthgraph.validation import ClaimValidator, ValidationResult


async def process_batch_claims(
    claims: List[str],
    validator: ClaimValidator,
):
    """Process batch of claims with validation."""
    # Validate all claims first
    validation_results = validator.validate_batch(
        claims,
        fail_fast=False,  # Continue validation for all claims
    )

    # Separate valid and invalid claims
    valid_claims = []
    invalid_claims = []

    for i, result in enumerate(validation_results):
        if result.valid:
            valid_claims.append({
                "index": i,
                "text": result.normalized_text,
                "warnings": [w.to_dict() for w in result.get_warnings()],
            })
        else:
            invalid_claims.append({
                "index": i,
                "text": claims[i],
                "errors": [e.to_dict() for e in result.get_errors()],
            })

    # Log validation summary
    logger.info(
        "batch_validation_complete",
        total=len(claims),
        valid=len(valid_claims),
        invalid=len(invalid_claims),
    )

    # Process only valid claims
    for claim_data in valid_claims:
        await verification_service.verify(claim_data["text"])

    # Store validation errors for invalid claims
    for claim_data in invalid_claims:
        await store_validation_failure(
            claim_data["text"],
            claim_data["errors"],
        )
```

### 8.3 Evidence Corpus Loading

Validate evidence documents during corpus loading.

```python
"""Evidence validation during corpus loading."""

from scripts.corpus_loaders.base_loader import BaseCorpusLoader
from truthgraph.validation import ClaimValidator, ValidationConfig


class ValidatedCorpusLoader(BaseCorpusLoader):
    """Corpus loader with validation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use lenient profile for evidence (more permissive)
        self.validator = ClaimValidator(ValidationConfig.lenient())

    def load_document(self, document: dict) -> Optional[dict]:
        """Load and validate document."""
        content = document.get("content", "")

        # Validate evidence content
        result = self.validator.validate(content, fail_fast=False)

        if not result.valid:
            logger.warning(
                "evidence_validation_failed",
                doc_id=document.get("id"),
                errors=[e.to_dict() for e in result.get_errors()],
            )
            return None  # Skip invalid document

        # Use normalized content
        document["content"] = result.normalized_text

        # Track validation warnings
        if result.has_warnings:
            document["validation_warnings"] = [
                w.to_dict() for w in result.get_warnings()
            ]

        return document
```

### 8.4 Test Fixtures

Integrate with pytest fixtures.

```python
"""Test fixture integration."""

import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig


@pytest.fixture
def claim_validator() -> ClaimValidator:
    """Provide claim validator for tests."""
    return ClaimValidator(ValidationConfig())


@pytest.fixture
def validated_claim(claim_validator: ClaimValidator):
    """Provide factory for validated claims."""
    def _validate(text: str) -> str:
        result = claim_validator.validate(text)
        if not result.valid:
            raise ValueError(f"Invalid claim: {result.get_errors()}")
        return result.normalized_text

    return _validate


# Usage in tests
def test_verification_pipeline(validated_claim):
    """Test verification with validated claim."""
    claim = validated_claim("The Earth orbits the Sun")
    result = verify_claim(claim)
    assert result.verdict == "SUPPORTED"
```

---

## 9. Migration Path

### Phase 1: Core Implementation (Week 1)

**Goal**: Implement validation layer with no external dependencies.

**Tasks**:
1. Create module structure
2. Implement error classes
3. Implement configuration
4. Implement encoding validator
5. Implement length validator
6. Write unit tests

**Deliverable**: Working validation layer (not yet integrated)

### Phase 2: Extended Validation (Week 1)

**Goal**: Add Unicode and special character validation.

**Tasks**:
1. Implement Unicode normalizer
2. Implement special char validator
3. Implement ClaimValidator orchestrator
4. Add caching support
5. Write integration tests

**Deliverable**: Complete validation layer

### Phase 3: Integration (Week 2)

**Goal**: Integrate with existing codebase.

**Tasks**:
1. Add validation to API endpoints
2. Add validation to background tasks
3. Add validation to corpus loaders
4. Update test fixtures
5. Add configuration loading

**Deliverable**: Fully integrated validation

### Phase 4: Testing & Optimization (Week 2)

**Goal**: Comprehensive testing and performance tuning.

**Tasks**:
1. Run edge case tests (Feature 3.3)
2. Property-based tests with Hypothesis
3. Performance profiling and optimization
4. Documentation and examples
5. Code review and refinement

**Deliverable**: Production-ready validation layer

### Backward Compatibility

**Strategy**: Add validation gradually without breaking existing code.

```python
# Add validation flag to existing functions
async def verify_claim(
    claim: str,
    validate_input: bool = True,  # Default to enabled
):
    """Verify claim with optional validation."""
    if validate_input:
        validator = get_claim_validator()
        result = validator.validate(claim)
        if not result.valid:
            raise ValidationError(...)
        claim = result.normalized_text

    # Continue with existing verification logic
    return await verification_service.verify(claim)
```

**Feature Flag**:
```python
# Environment variable for gradual rollout
TRUTHGRAPH_ENABLE_INPUT_VALIDATION=true

# Check feature flag
if settings.enable_input_validation:
    validator.validate(claim)
```

### Monitoring During Rollout

```python
# Track validation metrics
@router.post("/api/v1/claims/verify")
async def verify_claim(request: VerifyRequest):
    try:
        result = validator.validate(request.claim)

        # Log validation metrics
        logger.info(
            "validation_result",
            valid=result.valid,
            issues_count=len(result.issues),
            validation_time_ms=result.metadata["validation_time_ms"],
            profile=result.metadata["profile"],
        )

        if not result.valid:
            # Track validation failures
            metrics.increment("validation.failures")
            for error in result.get_errors():
                metrics.increment(f"validation.error.{error.code}")

    except Exception as e:
        # Track unexpected errors
        metrics.increment("validation.exceptions")
        logger.error("validation_exception", error=str(e))
        raise
```

---

## 10. Code Examples

### Example 1: Basic Usage

```python
"""Basic validation example."""

from truthgraph.validation import ClaimValidator, ValidationConfig

# Create validator with default configuration
validator = ClaimValidator()

# Validate a claim
claim = "The Earth orbits the Sun"
result = validator.validate(claim)

if result.valid:
    print(f"Valid claim: {result.normalized_text}")
    print(f"Validation time: {result.metadata['validation_time_ms']}ms")
else:
    print("Validation failed:")
    for error in result.get_errors():
        print(f"  - {error.message}")
        if error.suggestion:
            print(f"    Suggestion: {error.suggestion}")
```

### Example 2: Batch Validation

```python
"""Batch validation example."""

from truthgraph.validation import ClaimValidator

validator = ClaimValidator()

claims = [
    "The Earth orbits the Sun",
    "Water boils at 100 degrees Celsius",
    "",  # Invalid: empty
    "x" * 3000,  # Invalid: too long
    "The Moon is made of cheese",
]

# Validate batch
results = validator.validate_batch(claims, fail_fast=False)

# Process results
for i, result in enumerate(results):
    print(f"\nClaim {i + 1}: {claims[i][:50]}...")
    if result.valid:
        print(f"  ✓ Valid (time: {result.metadata['validation_time_ms']:.2f}ms)")
        if result.has_warnings:
            for warning in result.get_warnings():
                print(f"  ⚠ Warning: {warning.message}")
    else:
        print("  ✗ Invalid")
        for error in result.get_errors():
            print(f"    Error: {error.message}")

# Summary
valid_count = sum(1 for r in results if r.valid)
print(f"\nSummary: {valid_count}/{len(results)} claims valid")
```

### Example 3: Custom Validation Profile

```python
"""Custom validation configuration."""

from truthgraph.validation import (
    ClaimValidator,
    ValidationConfig,
    ValidationProfile,
)

# Create custom configuration
config = ValidationConfig(
    profile=ValidationProfile.CUSTOM,
    min_length=10,
    max_length=500,
    max_word_count=100,
    check_homoglyphs=True,
    allow_zero_width_chars=False,
    unicode_normalization="NFC",
)

validator = ClaimValidator(config)

# Use custom validator
result = validator.validate("Custom validated claim")
print(f"Profile: {result.metadata['profile']}")
```

### Example 4: Error Handling

```python
"""Comprehensive error handling example."""

from truthgraph.validation import (
    ClaimValidator,
    ValidationError,
    EncodingValidationError,
    LengthValidationError,
)

validator = ClaimValidator()

def validate_and_process(claim: str):
    """Validate and process claim with error handling."""
    try:
        result = validator.validate(claim)

        if not result.valid:
            # Handle validation failure
            error_codes = [e.code for e in result.get_errors()]
            print(f"Validation failed: {error_codes}")
            return None

        # Log warnings
        for warning in result.get_warnings():
            print(f"Warning: {warning.message}")

        # Process normalized claim
        return process_claim(result.normalized_text)

    except LengthValidationError as e:
        print(f"Length error: {e.message}")
        print(f"Suggestion: {e.suggestion}")
        return None

    except EncodingValidationError as e:
        print(f"Encoding error: {e.message}")
        return None

    except ValidationError as e:
        print(f"Validation error: {e.error_code} - {e.message}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

# Test with various inputs
test_claims = [
    "Valid claim",
    "",  # Empty
    "x" * 3000,  # Too long
    "Text with \x00 null byte",  # Encoding issue
]

for claim in test_claims:
    result = validate_and_process(claim)
    print(f"Result: {result}\n")
```

### Example 5: Async Usage

```python
"""Async validation example for FastAPI."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from truthgraph.validation import ClaimValidator, ValidationError

app = FastAPI()
validator = ClaimValidator()


class ClaimRequest(BaseModel):
    claim: str


class ClaimResponse(BaseModel):
    claim: str
    valid: bool
    normalized: str
    warnings: list[dict]


@app.post("/validate", response_model=ClaimResponse)
async def validate_claim_endpoint(request: ClaimRequest):
    """Validate claim via API."""
    try:
        # Run validation (synchronous, but fast <10ms)
        result = validator.validate(request.claim)

        if not result.valid:
            # Return 400 with error details
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_failed",
                    "issues": [e.to_dict() for e in result.get_errors()],
                },
            )

        return ClaimResponse(
            claim=request.claim,
            valid=result.valid,
            normalized=result.normalized_text,
            warnings=[w.to_dict() for w in result.get_warnings()],
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "code": e.error_code,
                "message": e.message,
                "suggestion": e.suggestion,
            },
        )
```

### Example 6: Caching for Performance

```python
"""Caching example for high-performance scenarios."""

from truthgraph.validation import ClaimValidator, ValidationConfig

# Enable caching
config = ValidationConfig(enable_caching=True, cache_ttl_seconds=3600)
validator = ClaimValidator(config)

# First validation - cache miss
claim = "The Earth orbits the Sun"
result1 = validator.validate_cached(claim)
print(f"First validation: {result1.metadata['validation_time_ms']:.2f}ms")
print(f"Cached: {result1.metadata.get('cached', False)}")

# Second validation - cache hit
result2 = validator.validate_cached(claim)
print(f"Second validation: {result2.metadata['validation_time_ms']:.2f}ms")
print(f"Cached: {result2.metadata.get('cached', True)}")

# Clear cache when needed
validator.clear_cache()
```

### Example 7: Integration with Verification Pipeline

```python
"""Complete integration example."""

from truthgraph.validation import ClaimValidator, ValidationConfig
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
)

# Initialize services
validator = ClaimValidator(ValidationConfig())
verification_service = VerificationPipelineService()


async def verify_claim_with_validation(
    claim: str,
    tenant_id: str = "default",
) -> dict:
    """Verify claim with input validation."""
    # Step 1: Validate input
    validation_result = validator.validate(claim)

    if not validation_result.valid:
        return {
            "status": "validation_failed",
            "errors": [e.to_dict() for e in validation_result.get_errors()],
        }

    # Step 2: Use normalized claim for verification
    normalized_claim = validation_result.normalized_text

    # Step 3: Run verification pipeline
    verification_result = await verification_service.verify(
        claim=normalized_claim,
        tenant_id=tenant_id,
    )

    # Step 4: Add validation metadata to result
    verification_result["validation"] = {
        "normalized": normalized_claim != claim,
        "warnings": [w.to_dict() for w in validation_result.get_warnings()],
        "validation_time_ms": validation_result.metadata["validation_time_ms"],
    }

    return verification_result


# Usage
result = await verify_claim_with_validation(
    "  The Earth orbits the Sun  "  # Has extra whitespace
)

print(f"Verdict: {result['verdict']}")
print(f"Normalized: {result['validation']['normalized']}")
```

---

## 11. Implementation Checklist

### Module Implementation

- [ ] Create `truthgraph/validation/` directory structure
- [ ] Implement `validation_errors.py` with exception hierarchy
- [ ] Implement `validation_result.py` with result dataclasses
- [ ] Implement `validation_config.py` with Pydantic models
- [ ] Implement `encoding_validator.py`
- [ ] Implement `length_validator.py`
- [ ] Implement `unicode_normalizer.py`
- [ ] Implement `special_char_validator.py`
- [ ] Implement `claim_validator.py` orchestrator
- [ ] Implement `__init__.py` with public API exports

### Configuration & Loading

- [ ] Create configuration loader utilities
- [ ] Add environment variable support
- [ ] Create YAML configuration schema
- [ ] Add configuration validation
- [ ] Document configuration options

### Testing

- [ ] Write unit tests for each validator component
- [ ] Write integration tests for ClaimValidator
- [ ] Add edge case tests using Feature 3.3 data
- [ ] Add property-based tests with Hypothesis
- [ ] Add performance benchmarks with pytest-benchmark
- [ ] Add test fixtures for validation
- [ ] Achieve >90% code coverage

### Integration

- [ ] Integrate with API endpoints (Feature 4.1)
- [ ] Add validation to `/api/v1/claims/verify`
- [ ] Add validation to batch endpoints
- [ ] Integrate with background tasks (Feature 4.3)
- [ ] Add validation to corpus loaders
- [ ] Update test fixtures to use validation
- [ ] Add validation to verification pipeline

### Documentation

- [ ] Write API documentation for validation module
- [ ] Create user guide for validation
- [ ] Document error codes and messages
- [ ] Create configuration guide
- [ ] Add code examples to documentation
- [ ] Update main README with validation info

### Performance & Optimization

- [ ] Profile validation performance
- [ ] Optimize slow validation steps
- [ ] Implement caching strategy
- [ ] Add performance monitoring
- [ ] Verify <10ms requirement met
- [ ] Optimize memory usage

### Deployment & Monitoring

- [ ] Add validation metrics to monitoring
- [ ] Create validation dashboards
- [ ] Add alerting for validation failures
- [ ] Document monitoring strategy
- [ ] Create runbook for validation issues

### Code Quality

- [ ] Run ruff linting
- [ ] Run mypy type checking
- [ ] Fix all type errors
- [ ] Run pytest with coverage
- [ ] Review code for security issues
- [ ] Get code review approval

---

## 12. Performance Benchmarks

### Target Performance Metrics

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Single validation | <10ms | p95 latency |
| Batch validation (100) | <500ms | Total time |
| Encoding validation | <1ms | Average |
| Length validation | <0.5ms | Average |
| Unicode normalization | <3ms | Average |
| Special char validation | <2ms | Average |
| Cache hit validation | <0.1ms | Average |
| Memory per validation | <1KB | Peak usage |

### Benchmark Suite

```python
"""Performance benchmarks for validation."""

import pytest
from truthgraph.validation import ClaimValidator, ValidationConfig


class TestPerformanceBenchmarks:
    """Benchmark suite for validation performance."""

    @pytest.fixture
    def validator(self):
        return ClaimValidator(ValidationConfig())

    @pytest.fixture
    def test_claims(self):
        """Generate test claims of various lengths."""
        return {
            "short": "Test claim",
            "medium": " ".join(["word"] * 50),
            "long": " ".join(["word"] * 200),
            "max": " ".join(["word"] * 400),  # Max word count
        }

    def test_benchmark_short_claim(self, validator, test_claims, benchmark):
        """Benchmark short claim validation."""
        result = benchmark(validator.validate, test_claims["short"])
        assert result.valid
        assert result.metadata["validation_time_ms"] < 10

    def test_benchmark_medium_claim(self, validator, test_claims, benchmark):
        """Benchmark medium claim validation."""
        result = benchmark(validator.validate, test_claims["medium"])
        assert result.valid
        assert result.metadata["validation_time_ms"] < 10

    def test_benchmark_long_claim(self, validator, test_claims, benchmark):
        """Benchmark long claim validation."""
        result = benchmark(validator.validate, test_claims["long"])
        assert result.valid
        assert result.metadata["validation_time_ms"] < 10

    def test_benchmark_batch_100(self, validator, benchmark):
        """Benchmark batch validation of 100 claims."""
        claims = [f"Test claim number {i}" for i in range(100)]
        results = benchmark(validator.validate_batch, claims)

        assert len(results) == 100
        total_time = sum(r.metadata["validation_time_ms"] for r in results)
        assert total_time < 500  # 500ms for 100 claims

    def test_benchmark_cache_hit(self, validator, benchmark):
        """Benchmark cached validation."""
        claim = "Cached test claim"

        # Prime cache
        validator.validate_cached(claim)

        # Benchmark cache hit
        result = benchmark(validator.validate_cached, claim)
        assert result.valid
        # Cache hits should be very fast
        # (Note: benchmark overhead may make this >0.1ms)

    def test_benchmark_unicode_heavy(self, validator, benchmark):
        """Benchmark Unicode-heavy text."""
        claim = "Test with émojis 🎉 and ăccénts and مرحبا"
        result = benchmark(validator.validate, claim)
        assert result.valid
        assert result.metadata["validation_time_ms"] < 10
```

### Expected Results

Based on Python 3.12+ on modern hardware (Intel i7/Apple M1):

```
benchmark_short_claim:     Mean: 2.3ms  (p95: 3.1ms)
benchmark_medium_claim:    Mean: 4.7ms  (p95: 6.2ms)
benchmark_long_claim:      Mean: 8.1ms  (p95: 9.8ms)
benchmark_batch_100:       Mean: 287ms  (2.87ms per claim)
benchmark_cache_hit:       Mean: 0.05ms (50μs)
benchmark_unicode_heavy:   Mean: 3.8ms  (p95: 5.1ms)
```

All benchmarks should meet <10ms requirement for single validations.

---

## Summary

This implementation guide provides a complete roadmap for adding a production-ready input validation layer to TruthGraph. The validation layer:

1. **Comprehensive**: Covers encoding, length, Unicode, special characters, and structure
2. **Fast**: <10ms overhead per validation with caching
3. **Secure**: Prevents injection attacks and encoding exploits
4. **Developer-Friendly**: Clear error messages with suggestions
5. **Configurable**: Multiple profiles and runtime configuration
6. **Well-Tested**: >90% coverage with unit, integration, and property-based tests
7. **Production-Ready**: Monitoring, logging, and performance optimization

### Implementation Timeline

- **Week 1**: Core implementation and extended validation
- **Week 2**: Integration, testing, and optimization

### Key Files to Create

1. `truthgraph/validation/claim_validator.py` (~400 lines)
2. `truthgraph/validation/encoding_validator.py` (~150 lines)
3. `truthgraph/validation/unicode_normalizer.py` (~250 lines)
4. `truthgraph/validation/length_validator.py` (~100 lines)
5. `truthgraph/validation/special_char_validator.py` (~200 lines)
6. `truthgraph/validation/validation_config.py` (~150 lines)
7. `truthgraph/validation/validation_errors.py` (~100 lines)
8. `truthgraph/validation/validation_result.py` (~100 lines)
9. `tests/unit/validation/test_*.py` (~1500 lines total)

**Total LOC**: ~3000 lines (including tests and docs)

### Next Steps

1. Review this implementation guide
2. Get stakeholder approval
3. Create feature branch: `feature/4.6-input-validation`
4. Begin Phase 1 implementation
5. Iterate with code reviews
6. Deploy to staging for testing
7. Roll out to production with monitoring

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Author**: Claude (Anthropic)
**Status**: Ready for Implementation
