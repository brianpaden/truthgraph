"""Main ClaimValidator orchestrator for comprehensive input validation.

This module provides the ClaimValidator class which orchestrates all validation
checks in the correct order and combines results into a final validation decision.

Validation Order:
1. Encoding validation (must pass)
2. Structure validation (must pass)
3. Length validation (may warn)
4. Special character validation (may warn)
5. Unicode normalization (always applied)
"""

from typing import Optional

import structlog

from truthgraph.validation.models import ValidationResult, ValidationStatus
from truthgraph.validation.normalizers import normalize_unicode
from truthgraph.validation.validators import (
    validate_encoding,
    validate_length,
    validate_special_characters,
    validate_structure,
)

logger = structlog.get_logger(__name__)


class ClaimValidator:
    """Orchestrator for claim text validation.

    This class runs all validation checks in the proper order and combines
    results into a final validation decision. It supports configurable thresholds
    and provides detailed validation results with normalized text.

    Validation follows a fail-fast approach for critical checks (encoding, structure)
    and collects warnings for non-critical checks (length, special characters).

    Attributes:
        min_words: Minimum word count for valid claims (default: 2)
        max_words: Maximum word count before warning (default: 500)
        max_tokens_estimate: Maximum estimated tokens before warning (default: 450)
        max_non_ascii_ratio: Maximum non-ASCII ratio before warning (default: 0.5)

    Example:
        >>> validator = ClaimValidator()
        >>> result = validator.validate("The Earth is round")
        >>> result.status
        <ValidationStatus.VALID: 'valid'>
        >>> result.normalized_text
        'The Earth is round'

        >>> result = validator.validate("")
        >>> result.status
        <ValidationStatus.INVALID: 'invalid'>
        >>> result.error_code
        'EMPTY_TEXT'
    """

    def __init__(
        self,
        min_words: int = 2,
        max_words: int = 500,
        max_tokens_estimate: int = 450,
        max_non_ascii_ratio: float = 0.5,
    ):
        """Initialize ClaimValidator with configuration.

        Args:
            min_words: Minimum word count for valid claims (default: 2)
            max_words: Maximum word count before warning (default: 500)
            max_tokens_estimate: Maximum estimated tokens before warning (default: 450)
            max_non_ascii_ratio: Maximum non-ASCII ratio before warning (default: 0.5)
        """
        self.min_words = min_words
        self.max_words = max_words
        self.max_tokens_estimate = max_tokens_estimate
        self.max_non_ascii_ratio = max_non_ascii_ratio

        logger.info(
            "claim_validator_initialized",
            min_words=min_words,
            max_words=max_words,
            max_tokens_estimate=max_tokens_estimate,
            max_non_ascii_ratio=max_non_ascii_ratio,
        )

    def validate(self, claim_text: str) -> ValidationResult:
        """Run all validation checks on claim text.

        Validation order:
        1. Encoding validation (must pass) - INVALID on failure
        2. Structure validation (must pass) - INVALID on failure
        3. Length validation (may warn) - WARNING on edge cases
        4. Special character validation (may warn) - WARNING on high non-ASCII
        5. Unicode normalization (always applied)

        Args:
            claim_text: Claim text to validate

        Returns:
            ValidationResult with status, errors, warnings, and normalized text

        Example:
            >>> validator = ClaimValidator()
            >>> result = validator.validate("The Earth orbits the Sun")
            >>> result.status
            <ValidationStatus.VALID: 'valid'>
            >>> result.normalized_text
            'The Earth orbits the Sun'
        """
        # Track all warnings collected during validation
        warnings: list[str] = []
        combined_metadata: dict = {}

        # Phase 1: Critical validations (fail-fast on INVALID)
        # ====================================================

        # 1. Encoding validation (must pass)
        encoding_result = validate_encoding(claim_text)
        combined_metadata.update(encoding_result.metadata)

        if encoding_result.status == ValidationStatus.INVALID:
            logger.warning(
                "validation_failed_encoding",
                error_code=encoding_result.error_code,
                message=encoding_result.message,
            )
            return encoding_result

        # 2. Structure validation (must pass)
        structure_result = validate_structure(claim_text)
        combined_metadata.update(structure_result.metadata)

        if structure_result.status == ValidationStatus.INVALID:
            logger.warning(
                "validation_failed_structure",
                error_code=structure_result.error_code,
                message=structure_result.message,
            )
            return structure_result

        # Phase 2: Length and special character validation (collect warnings)
        # ====================================================================

        # 3. Length validation (may warn)
        length_result = validate_length(
            claim_text,
            min_words=self.min_words,
            max_words=self.max_words,
            max_tokens_estimate=self.max_tokens_estimate,
        )
        combined_metadata.update(length_result.metadata)

        if length_result.status == ValidationStatus.INVALID:
            logger.warning(
                "validation_failed_length",
                error_code=length_result.error_code,
                message=length_result.message,
            )
            return length_result

        if length_result.status == ValidationStatus.WARNING:
            warnings.append(
                f"{length_result.error_code}: {length_result.message} - {length_result.suggestion}"
            )
            logger.info(
                "validation_warning_length",
                error_code=length_result.error_code,
                message=length_result.message,
            )

        # 4. Special character validation (may warn)
        special_char_result = validate_special_characters(
            claim_text,
            max_non_ascii_ratio=self.max_non_ascii_ratio,
        )
        combined_metadata.update(special_char_result.metadata)

        if special_char_result.status == ValidationStatus.WARNING:
            warnings.append(
                f"{special_char_result.error_code}: {special_char_result.message} - "
                f"{special_char_result.suggestion}"
            )
            logger.info(
                "validation_warning_special_chars",
                error_code=special_char_result.error_code,
                message=special_char_result.message,
            )

        # Phase 3: Unicode normalization (always applied)
        # ================================================

        # 5. Unicode normalization
        try:
            normalized_text = normalize_unicode(claim_text)
            combined_metadata["normalized"] = True
            combined_metadata["normalization_changed"] = normalized_text != claim_text
        except ValueError as e:
            # Normalization failed - this is INVALID
            logger.error(
                "validation_failed_normalization",
                error=str(e),
            )
            return ValidationResult(
                status=ValidationStatus.INVALID,
                error_type="encoding",
                error_code="INVALID_UNICODE",
                message=f"Failed to normalize Unicode: {str(e)}",
                suggestion="Remove or replace invalid Unicode characters",
                metadata=combined_metadata,
            )

        # Phase 4: Return final result
        # ==============================

        # Determine final status
        final_status = ValidationStatus.WARNING if warnings else ValidationStatus.VALID

        logger.info(
            "validation_completed",
            status=final_status.value,
            warnings_count=len(warnings),
            text_length=len(claim_text),
            word_count=combined_metadata.get("word_count"),
        )

        return ValidationResult(
            status=final_status,
            normalized_text=normalized_text,
            warnings=warnings,
            metadata=combined_metadata,
        )

    def validate_batch(self, claim_texts: list[str]) -> list[ValidationResult]:
        """Validate multiple claims in batch.

        This method validates multiple claims sequentially. For production use
        with large batches, consider using async/parallel processing.

        Args:
            claim_texts: List of claim texts to validate

        Returns:
            List of ValidationResult objects, one per claim

        Example:
            >>> validator = ClaimValidator()
            >>> claims = ["The Earth is round", "Water is wet"]
            >>> results = validator.validate_batch(claims)
            >>> all(r.status == ValidationStatus.VALID for r in results)
            True
        """
        results = []
        for i, claim_text in enumerate(claim_texts):
            try:
                result = self.validate(claim_text)
                results.append(result)
            except Exception as e:
                logger.error(
                    "validation_batch_error",
                    index=i,
                    error=str(e),
                    exc_info=True,
                )
                # Return INVALID result for this claim
                results.append(
                    ValidationResult(
                        status=ValidationStatus.INVALID,
                        error_type="internal",
                        error_code="VALIDATION_ERROR",
                        message=f"Validation failed: {str(e)}",
                        suggestion="Check claim text and try again",
                        metadata={"error": str(e), "batch_index": i},
                    )
                )

        logger.info(
            "validation_batch_completed",
            total_claims=len(claim_texts),
            valid_count=sum(1 for r in results if r.status == ValidationStatus.VALID),
            warning_count=sum(1 for r in results if r.status == ValidationStatus.WARNING),
            invalid_count=sum(1 for r in results if r.status == ValidationStatus.INVALID),
        )

        return results


# Singleton instance for global access
_validator_instance: Optional[ClaimValidator] = None


def get_claim_validator() -> ClaimValidator:
    """Get or create singleton ClaimValidator instance.

    Returns:
        ClaimValidator instance with default configuration

    Example:
        >>> validator = get_claim_validator()
        >>> result = validator.validate("The Earth is round")
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ClaimValidator()
    return _validator_instance
