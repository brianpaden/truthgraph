# Edge Case Error Handling Architecture Review
## Feature 3.3: Edge Case Validation

**Date**: 2025-11-02
**Reviewer**: Backend System Architect
**Phase**: Phase 2 Validation Framework
**Status**: Architecture Review Complete

---

## Executive Summary

This document provides a comprehensive architectural review of error handling for edge case validation in the TruthGraph verification pipeline. The current system demonstrates solid foundational error handling but lacks specialized patterns for the 7 edge case categories identified in the test corpus.

**Current State**: Good foundation with retry logic and basic error containment
**Gap Analysis**: Missing specialized edge case detection and handling layers
**Recommended Approach**: Layered error handling with dedicated edge case detection service

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Edge Case Categories Analysis](#2-edge-case-categories-analysis)
3. [Identified Gaps](#3-identified-gaps)
4. [Recommended Architecture](#4-recommended-architecture)
5. [Error Handling Patterns](#5-error-handling-patterns)
6. [Implementation Guidance](#6-implementation-guidance)
7. [Integration Strategy](#7-integration-strategy)
8. [Monitoring & Observability](#8-monitoring--observability)

---

## 1. Current State Assessment

### 1.1 Existing Error Handling Mechanisms

#### **Verification Pipeline Service** (`verification_pipeline_service.py`)

**Strengths:**
- ✓ Retry decorator with exponential backoff
- ✓ Graceful degradation on storage failures
- ✓ Cache layer prevents redundant processing
- ✓ Empty evidence handling (returns INSUFFICIENT verdict)
- ✓ Structured logging with contextual information
- ✓ Exception wrapping with `RuntimeError`

**Current Error Handling:**
```python
@retry_on_failure(max_attempts=3, initial_delay=1.0, exceptions=(RuntimeError,))
def _generate_embedding_with_retry(self, claim_text: str) -> list[float]:
    """Generate embedding with retry logic."""
    return self.embedding_service.embed_text(claim_text)
```

**Verdict Determination Logic:**
```python
# Handles insufficient evidence
if not search_results:
    return self._create_insufficient_verdict(...)

# Handles low confidence scenarios
if weighted_support == max_score and weighted_support > HIGH_CONFIDENCE_THRESHOLD:
    verdict = VerdictLabel.SUPPORTED
elif len(evidence_items) < MIN_EVIDENCE_THRESHOLD:
    verdict = VerdictLabel.INSUFFICIENT
```

**Issues:**
- No explicit edge case type detection
- Threshold values are hardcoded (0.6 confidence, 2 evidence minimum)
- No handling for contradictory evidence conflicts
- Missing input validation for malformed claims
- No graceful handling of special characters/encoding issues

#### **NLI Service** (`nli_service.py`)

**Strengths:**
- ✓ Input validation (empty premise/hypothesis checks)
- ✓ Device detection and fallback (CUDA → MPS → CPU)
- ✓ Batch processing with memory management
- ✓ Proper exception wrapping

**Issues:**
- No handling for extremely long inputs (>512 tokens)
- No detection of contradictory batch results
- Limited error recovery (model loading failures are fatal)
- No fallback mechanism for inference failures

#### **Verdict Aggregation Service** (`verdict_aggregation_service.py`)

**Strengths:**
- ✓ Input validation for NLI results
- ✓ Conflict detection (`_detect_conflict` method)
- ✓ Multiple aggregation strategies
- ✓ Comprehensive validation of confidence scores

**Current Conflict Detection:**
```python
def _detect_conflict(self, support_score: float, refute_score: float) -> bool:
    """Detect if there's conflicting evidence."""
    return support_score >= self.CONFLICT_THRESHOLD and refute_score >= self.CONFLICT_THRESHOLD
```

**Issues:**
- Conflict detection exists but isn't fully leveraged in pipeline
- No special handling for high-conflict scenarios
- UNCERTAIN verdict doesn't distinguish between types of uncertainty

#### **API Layer** (`api/models.py`)

**Strengths:**
- ✓ Comprehensive Pydantic validation
- ✓ Standardized `ErrorResponse` model
- ✓ Field-level validation with descriptive messages

**Issues:**
- No validation for edge case inputs (special characters, extreme lengths)
- Generic error responses don't distinguish edge case types
- No structured error codes for different failure modes

### 1.2 Error Coverage Matrix

| Error Type | Detection | Handling | Recovery | Monitoring |
|------------|-----------|----------|----------|------------|
| Empty claim text | ✓ | ✓ | N/A | ✓ |
| No evidence found | ✓ | ✓ | N/A | ✓ |
| API failures | ✓ | Retry | Partial | ✓ |
| Database errors | ✓ | Rollback | No | ✓ |
| Model loading failures | ✓ | None | No | ✓ |
| Inference failures | Partial | None | No | ✓ |
| Missing evidence | ✓ | INSUFFICIENT | N/A | ✓ |
| **Contradictory evidence** | **Partial** | **Weak** | **No** | **Weak** |
| **Ambiguous claims** | **No** | **No** | **No** | **No** |
| **Malformed input** | **No** | **No** | **No** | **No** |
| **Long claims (>500 words)** | **No** | **No** | **No** | **No** |
| **Short claims (<3 words)** | **No** | **No** | **No** | **No** |
| **Special characters/Unicode** | **No** | **No** | **No** | **No** |
| **Adversarial examples** | **No** | **No** | **No** | **No** |

**Legend:** ✓ = Implemented, Partial = Basic implementation, Weak = Minimal, No = Not implemented

---

## 2. Edge Case Categories Analysis

Based on the Edge Case Corpus (34 test claims, 7 categories), here's how each category should be handled:

### 2.1 Insufficient Evidence (5 claims)

**Expected Behavior:** Return `INSUFFICIENT` verdict
**Current Handling:** ✓ Good
**Gap:** None - already handled correctly

```python
# Current implementation is adequate
if not search_results:
    return self._create_insufficient_verdict(...)
```

### 2.2 Contradictory Evidence (4 claims)

**Expected Behavior:** Return `CONFLICTING` verdict or confidence-balanced score
**Current Handling:** Partial - conflict detected but not properly surfaced
**Gap:** Verdict aggregation doesn't expose conflict status in final result

**Recommended Enhancement:**
```python
class VerdictLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"  # NEW: For contradictory evidence
```

**Detection Logic:**
```python
def _aggregate_verdict(self, ...):
    # ... existing logic ...

    # NEW: Check for conflicts
    if has_conflict and abs(weighted_support - weighted_refute) < CONFLICT_MARGIN:
        return VerificationPipelineResult(
            verdict=VerdictLabel.CONFLICTING,
            confidence=max(weighted_support, weighted_refute),
            reasoning=self._generate_conflict_reasoning(...)
        )
```

### 2.3 Ambiguous Evidence (5 claims)

**Expected Behavior:** Return `INSUFFICIENT` or `AMBIGUOUS` with lower confidence
**Current Handling:** Partial - low confidence scenarios return INSUFFICIENT
**Gap:** No distinction between "no evidence" and "weak/ambiguous evidence"

**Recommended Enhancement:**
- Add ambiguity score based on neutral_score dominance
- Distinguish INSUFFICIENT (no evidence) from AMBIGUOUS (weak evidence)

```python
# Detection pattern
if weighted_neutral > 0.6 and total_evidence > 0:
    return VerificationPipelineResult(
        verdict=VerdictLabel.AMBIGUOUS,
        confidence=weighted_neutral,
        reasoning="Evidence is tangentially related but not conclusive"
    )
```

### 2.4 Long Claims (5 claims, 150-280 words)

**Expected Behavior:** Process without truncation, ideally decompose
**Current Handling:** No explicit handling
**Gap:** Tokenization limits (512 tokens), no decomposition logic

**Risk:** Silent truncation in NLI model tokenization

**Recommended Enhancement:**
```python
class ClaimValidator:
    MAX_TOKENS = 512

    def validate_claim_length(self, claim_text: str) -> ValidationResult:
        """Detect and handle long claims."""
        tokens = self.tokenizer.encode(claim_text)

        if len(tokens) > self.MAX_TOKENS:
            return ValidationResult(
                is_valid=False,
                error_type="CLAIM_TOO_LONG",
                message=f"Claim exceeds {self.MAX_TOKENS} tokens",
                suggestion="Consider decomposing into sub-claims"
            )

        return ValidationResult(is_valid=True)
```

### 2.5 Short Claims (5 claims, 1-5 words)

**Expected Behavior:** Process with minimal context, may return INSUFFICIENT
**Current Handling:** No explicit handling
**Gap:** No detection or warning for claims lacking propositional content

**Recommended Enhancement:**
```python
def validate_claim_structure(claim_text: str) -> ValidationResult:
    """Validate claim has sufficient structure."""
    words = claim_text.split()

    if len(words) < 3:
        return ValidationResult(
            is_valid=True,  # Allow processing
            warning="SHORT_CLAIM",
            message="Claim has minimal context, verification may be limited"
        )

    if len(words) == 1:
        return ValidationResult(
            is_valid=False,
            error_type="NON_PROPOSITIONAL",
            message="Single-word input is not a verifiable claim"
        )
```

### 2.6 Special Characters & Multilingual (5 claims)

**Expected Behavior:** Handle Unicode correctly without errors
**Current Handling:** Unknown - likely works but not explicitly tested
**Gap:** No validation, no encoding error handling

**Recommended Enhancement:**
```python
def validate_encoding(claim_text: str) -> ValidationResult:
    """Ensure text is properly encoded."""
    try:
        # Test encoding round-trip
        encoded = claim_text.encode('utf-8')
        decoded = encoded.decode('utf-8')

        if decoded != claim_text:
            return ValidationResult(
                is_valid=False,
                error_type="ENCODING_ERROR",
                message="Text encoding is corrupted"
            )

        # Check for problematic characters
        if any(ord(c) == 0xFFFD for c in claim_text):  # Replacement character
            return ValidationResult(
                is_valid=False,
                error_type="INVALID_UNICODE",
                message="Text contains invalid Unicode sequences"
            )

        return ValidationResult(is_valid=True)

    except UnicodeError as e:
        return ValidationResult(
            is_valid=False,
            error_type="ENCODING_ERROR",
            message=f"Unicode encoding error: {e}"
        )
```

### 2.7 Adversarial Examples (5 claims)

**Expected Behavior:** Maintain robustness, recognize technical truth vs. misleading framing
**Current Handling:** None
**Gap:** No adversarial detection, no misleading claim flagging

**Recommended Enhancement:**
This is the most complex category and requires ML-based detection:

```python
class AdversarialDetector:
    """Detect potentially misleading claims."""

    def detect_cherry_picking(
        self,
        claim: str,
        evidence_items: list[EvidenceItem]
    ) -> AdversarialSignal:
        """Detect selective evidence presentation."""
        # Check if claim mentions specific timeframes/conditions
        # Check if evidence contradicts on different timeframes
        # Flag if temporal cherry-picking detected
        pass

    def detect_correlation_causation_confusion(
        self,
        claim: str,
        nli_results: list[NLIResult]
    ) -> AdversarialSignal:
        """Detect claims that confuse correlation with causation."""
        # Pattern matching for causal language
        # Check if evidence only supports correlation
        pass
```

**Note:** Full adversarial detection is out of scope for Phase 2. Recommend flagging high-risk claims for human review.

---

## 3. Identified Gaps

### 3.1 Architecture Gaps

| Gap | Impact | Priority | Effort |
|-----|--------|----------|--------|
| No dedicated edge case detection layer | Medium | High | Medium |
| Verdict labels don't include CONFLICTING/AMBIGUOUS | High | High | Low |
| No input validation service | Medium | High | Medium |
| Missing fallback mechanisms for ML failures | High | Medium | High |
| No decomposition logic for long claims | Low | Medium | High |
| No adversarial pattern detection | Low | Low | Very High |

### 3.2 Error Handling Gaps

| Gap | Current Behavior | Desired Behavior |
|-----|------------------|------------------|
| Contradictory evidence | Returns INSUFFICIENT or biased verdict | Return CONFLICTING with conflict details |
| Ambiguous evidence | Returns INSUFFICIENT | Return AMBIGUOUS with explanation |
| Malformed input | Raises ValueError | Gracefully handle with validation errors |
| Long claims | Silent truncation | Warn or decompose |
| Short claims | Processes normally | Warn about limited context |
| Encoding errors | Crashes or corrupts | Detect and reject with clear message |
| Model failures | Pipeline fails | Fallback to simpler methods |

### 3.3 Observability Gaps

| Metric | Currently Tracked | Needed |
|--------|-------------------|--------|
| Edge case detection rate | No | Yes |
| Conflict frequency | Partial (logged) | Dashboard metric |
| Ambiguous verdict rate | No | Yes |
| Input validation failures | No | Yes |
| Truncation events | No | Yes |
| Encoding error rate | No | Yes |

---

## 4. Recommended Architecture

### 4.1 Layered Error Handling Architecture

```
┌─────────────────────────────────────────────────────┐
│  API Layer                                          │
│  - Request validation (Pydantic)                    │
│  - Error response formatting                        │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│  Input Validation Layer  ◄── NEW                    │
│  - ClaimValidator                                   │
│  - EncodingValidator                                │
│  - LengthValidator                                  │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│  Edge Case Detection Layer  ◄── NEW                 │
│  - EdgeCaseClassifier                               │
│  - AmbiguityDetector                                │
│  - ConflictAnalyzer                                 │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│  Verification Pipeline                              │
│  - Embedding generation (with retry)                │
│  - Evidence retrieval (with fallback)               │
│  - NLI verification (with error handling)           │
│  - Verdict aggregation (conflict-aware)             │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│  Error Recovery Layer                               │
│  - Retry logic                                      │
│  - Graceful degradation                             │
│  - Fallback mechanisms                              │
└─────────────────────────────────────────────────────┘
```

### 4.2 Component Responsibilities

#### **Input Validation Layer** (New)
- Pre-flight checks before pipeline execution
- Encoding validation
- Length constraints
- Basic malformed input detection
- Return structured validation results

#### **Edge Case Detection Layer** (New)
- Classify claim type (standard, long, short, ambiguous)
- Detect potential conflicts during aggregation
- Flag adversarial patterns (basic)
- Provide detection confidence scores

#### **Verification Pipeline** (Enhanced)
- Integrate validation results
- Apply edge-case-aware thresholds
- Support CONFLICTING and AMBIGUOUS verdicts
- Enhanced error context in exceptions

#### **Error Recovery Layer** (Enhanced)
- Existing retry logic
- New fallback mechanisms for ML failures
- Graceful degradation paths
- Comprehensive error logging

---

## 5. Error Handling Patterns

### 5.1 Input Validation Pattern

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ValidationStatus(str, Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"

@dataclass
class ValidationResult:
    """Result of input validation."""
    status: ValidationStatus
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Optional[dict] = None

class ClaimValidator:
    """Validates claims before pipeline processing."""

    def validate(self, claim_text: str) -> ValidationResult:
        """Run all validation checks."""
        # Check encoding
        encoding_result = self._validate_encoding(claim_text)
        if encoding_result.status == ValidationStatus.INVALID:
            return encoding_result

        # Check length
        length_result = self._validate_length(claim_text)
        if length_result.status == ValidationStatus.INVALID:
            return length_result

        # Check structure
        structure_result = self._validate_structure(claim_text)
        if structure_result.status == ValidationStatus.INVALID:
            return structure_result

        # Aggregate warnings
        warnings = []
        if length_result.status == ValidationStatus.WARNING:
            warnings.append(length_result.message)
        if structure_result.status == ValidationStatus.WARNING:
            warnings.append(structure_result.message)

        if warnings:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="; ".join(warnings),
                metadata={"warnings": warnings}
            )

        return ValidationResult(status=ValidationStatus.VALID)

    def _validate_encoding(self, text: str) -> ValidationResult:
        """Validate text encoding."""
        try:
            # UTF-8 round-trip test
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')

            if decoded != text:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    error_type="encoding_error",
                    error_code="ENCODING_MISMATCH",
                    message="Text encoding round-trip failed"
                )

            # Check for replacement characters
            if '\ufffd' in text:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    error_type="invalid_unicode",
                    error_code="REPLACEMENT_CHAR",
                    message="Text contains invalid Unicode replacement characters"
                )

            return ValidationResult(status=ValidationStatus.VALID)

        except UnicodeError as e:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                error_type="encoding_error",
                error_code="UNICODE_ERROR",
                message=f"Unicode encoding error: {str(e)}"
            )

    def _validate_length(self, text: str) -> ValidationResult:
        """Validate text length."""
        words = text.split()
        word_count = len(words)

        # Too short
        if word_count == 1:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                error_type="claim_too_short",
                error_code="SINGLE_WORD_CLAIM",
                message="Single-word inputs cannot be verified as claims",
                suggestion="Provide a complete sentence or proposition"
            )

        if word_count < 3:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                error_type="claim_short",
                error_code="MINIMAL_CONTEXT",
                message=f"Claim has only {word_count} words, verification may be limited",
                metadata={"word_count": word_count}
            )

        # Too long (estimate tokens)
        estimated_tokens = word_count * 1.3  # Rough estimate
        if estimated_tokens > 450:  # Leave buffer under 512
            return ValidationResult(
                status=ValidationStatus.WARNING,
                error_type="claim_long",
                error_code="POTENTIAL_TRUNCATION",
                message=f"Claim is very long (~{int(estimated_tokens)} tokens), may be truncated",
                suggestion="Consider breaking into multiple claims",
                metadata={"word_count": word_count, "estimated_tokens": int(estimated_tokens)}
            )

        return ValidationResult(status=ValidationStatus.VALID)

    def _validate_structure(self, text: str) -> ValidationResult:
        """Validate claim has minimal propositional structure."""
        # Check if text ends with punctuation
        if not text.strip():
            return ValidationResult(
                status=ValidationStatus.INVALID,
                error_type="empty_claim",
                error_code="EMPTY_TEXT",
                message="Claim text cannot be empty"
            )

        # Check for basic sentence structure (has at least one word character)
        if not any(c.isalnum() for c in text):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                error_type="malformed_claim",
                error_code="NO_ALPHANUMERIC",
                message="Claim contains no alphanumeric characters"
            )

        return ValidationResult(status=ValidationStatus.VALID)
```

### 5.2 Edge Case Detection Pattern

```python
from dataclasses import dataclass
from enum import Enum

class EdgeCaseType(str, Enum):
    """Types of edge cases detected."""
    STANDARD = "standard"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    AMBIGUOUS_EVIDENCE = "ambiguous_evidence"
    LONG_CLAIM = "long_claim"
    SHORT_CLAIM = "short_claim"
    SPECIAL_CHARACTERS = "special_characters"
    ADVERSARIAL = "adversarial"

@dataclass
class EdgeCaseSignal:
    """Signal indicating edge case detection."""
    edge_case_type: EdgeCaseType
    confidence: float  # 0.0-1.0
    indicators: list[str]
    recommended_action: str
    metadata: dict

class EdgeCaseDetector:
    """Detects edge cases during verification."""

    def classify_claim(self, claim_text: str) -> EdgeCaseSignal:
        """Classify claim type before processing."""
        words = claim_text.split()
        word_count = len(words)

        # Check length-based edge cases
        if word_count < 3:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.SHORT_CLAIM,
                confidence=1.0,
                indicators=[f"word_count={word_count}"],
                recommended_action="process_with_low_confidence_threshold",
                metadata={"word_count": word_count}
            )

        if word_count > 150:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.LONG_CLAIM,
                confidence=1.0,
                indicators=[f"word_count={word_count}"],
                recommended_action="consider_decomposition",
                metadata={"word_count": word_count}
            )

        # Check for special characters
        non_ascii_ratio = sum(1 for c in claim_text if ord(c) > 127) / len(claim_text)
        if non_ascii_ratio > 0.1:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.SPECIAL_CHARACTERS,
                confidence=0.8,
                indicators=[f"non_ascii_ratio={non_ascii_ratio:.2f}"],
                recommended_action="ensure_unicode_handling",
                metadata={"non_ascii_ratio": non_ascii_ratio}
            )

        return EdgeCaseSignal(
            edge_case_type=EdgeCaseType.STANDARD,
            confidence=1.0,
            indicators=[],
            recommended_action="standard_processing",
            metadata={}
        )

    def detect_insufficient_evidence(
        self,
        evidence_items: list,
        min_required: int = 2
    ) -> EdgeCaseSignal:
        """Detect insufficient evidence scenario."""
        if len(evidence_items) == 0:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.INSUFFICIENT_EVIDENCE,
                confidence=1.0,
                indicators=["no_evidence_found"],
                recommended_action="return_insufficient_verdict",
                metadata={"evidence_count": 0}
            )

        if len(evidence_items) < min_required:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.INSUFFICIENT_EVIDENCE,
                confidence=0.7,
                indicators=["low_evidence_count"],
                recommended_action="flag_low_confidence",
                metadata={"evidence_count": len(evidence_items)}
            )

        return EdgeCaseSignal(
            edge_case_type=EdgeCaseType.STANDARD,
            confidence=1.0,
            indicators=[],
            recommended_action="standard_processing",
            metadata={}
        )

    def detect_contradictory_evidence(
        self,
        support_score: float,
        refute_score: float,
        conflict_threshold: float = 0.3
    ) -> EdgeCaseSignal:
        """Detect contradictory evidence scenario."""
        # Both scores are significant
        if support_score >= conflict_threshold and refute_score >= conflict_threshold:
            score_diff = abs(support_score - refute_score)

            if score_diff < 0.15:  # Very close scores
                return EdgeCaseSignal(
                    edge_case_type=EdgeCaseType.CONTRADICTORY_EVIDENCE,
                    confidence=0.9,
                    indicators=[
                        f"support={support_score:.2f}",
                        f"refute={refute_score:.2f}",
                        f"diff={score_diff:.2f}"
                    ],
                    recommended_action="return_conflicting_verdict",
                    metadata={
                        "support_score": support_score,
                        "refute_score": refute_score,
                        "score_difference": score_diff
                    }
                )

        return EdgeCaseSignal(
            edge_case_type=EdgeCaseType.STANDARD,
            confidence=1.0,
            indicators=[],
            recommended_action="standard_processing",
            metadata={}
        )

    def detect_ambiguous_evidence(
        self,
        neutral_score: float,
        max_score: float,
        ambiguity_threshold: float = 0.55
    ) -> EdgeCaseSignal:
        """Detect ambiguous/neutral evidence scenario."""
        # Neutral score dominates
        if neutral_score > ambiguity_threshold and neutral_score == max_score:
            return EdgeCaseSignal(
                edge_case_type=EdgeCaseType.AMBIGUOUS_EVIDENCE,
                confidence=0.8,
                indicators=[
                    f"neutral_score={neutral_score:.2f}",
                    "neutral_dominates"
                ],
                recommended_action="return_ambiguous_verdict",
                metadata={"neutral_score": neutral_score}
            )

        return EdgeCaseSignal(
            edge_case_type=EdgeCaseType.STANDARD,
            confidence=1.0,
            indicators=[],
            recommended_action="standard_processing",
            metadata={}
        )
```

### 5.3 Graceful Degradation Pattern

```python
class VerificationPipelineService:
    """Enhanced with graceful degradation."""

    async def verify_claim(self, ...):
        """Verify claim with graceful degradation."""

        # Step 1: Input validation
        validator = ClaimValidator()
        validation_result = validator.validate(claim_text)

        if validation_result.status == ValidationStatus.INVALID:
            raise ValueError(
                f"Invalid claim: {validation_result.message} "
                f"(error_code: {validation_result.error_code})"
            )

        # Log warnings but proceed
        if validation_result.status == ValidationStatus.WARNING:
            logger.warning(
                "claim_validation_warning",
                claim_id=str(claim_id),
                warnings=validation_result.metadata.get("warnings", [])
            )

        # Step 2: Edge case classification
        edge_detector = EdgeCaseDetector()
        edge_signal = edge_detector.classify_claim(claim_text)

        logger.info(
            "edge_case_detected",
            claim_id=str(claim_id),
            edge_case_type=edge_signal.edge_case_type.value,
            confidence=edge_signal.confidence
        )

        try:
            # Step 3: Generate embedding with fallback
            try:
                claim_embedding = self._generate_embedding_with_retry(claim_text)
            except RuntimeError as e:
                logger.error(
                    "embedding_generation_failed",
                    claim_id=str(claim_id),
                    error=str(e)
                )
                # Fallback: Use keyword search only
                return await self._fallback_keyword_verification(
                    db, claim_id, claim_text
                )

            # Step 4: Search with edge-case-aware thresholds
            if edge_signal.edge_case_type == EdgeCaseType.SHORT_CLAIM:
                min_similarity = max(min_similarity - 0.1, 0.0)  # Lower threshold
                logger.info("adjusted_similarity_threshold_for_short_claim")

            search_results = self._search_evidence_with_retry(...)

            # Step 5: Detect insufficient evidence
            insufficient_signal = edge_detector.detect_insufficient_evidence(
                search_results
            )

            if insufficient_signal.edge_case_type == EdgeCaseType.INSUFFICIENT_EVIDENCE:
                logger.info(
                    "insufficient_evidence_detected",
                    claim_id=str(claim_id),
                    evidence_count=len(search_results)
                )
                return self._create_insufficient_verdict(...)

            # Step 6: NLI verification with error handling
            try:
                evidence_items = await self._verify_evidence_batch(
                    claim_text, search_results
                )
            except RuntimeError as e:
                logger.error(
                    "nli_verification_failed",
                    claim_id=str(claim_id),
                    error=str(e)
                )
                # Fallback: Use similarity-only verdict
                return await self._fallback_similarity_verdict(
                    claim_id, claim_text, search_results
                )

            # Step 7: Aggregate with edge case awareness
            verdict_result = self._aggregate_verdict_with_edge_detection(
                claim_id=claim_id,
                claim_text=claim_text,
                evidence_items=evidence_items,
                edge_signal=edge_signal,
                edge_detector=edge_detector
            )

            return verdict_result

        except Exception as e:
            logger.error(
                "verification_pipeline_critical_failure",
                claim_id=str(claim_id),
                error=str(e),
                exc_info=True
            )
            # Last resort: Return safe INSUFFICIENT verdict
            return self._create_error_verdict(
                claim_id=claim_id,
                claim_text=claim_text,
                error_message=str(e)
            )

    def _aggregate_verdict_with_edge_detection(
        self,
        claim_id: UUID,
        claim_text: str,
        evidence_items: list[EvidenceItem],
        edge_signal: EdgeCaseSignal,
        edge_detector: EdgeCaseDetector
    ) -> VerificationPipelineResult:
        """Aggregate verdict with edge case detection."""

        # Calculate scores (existing logic)
        weighted_support, weighted_refute, weighted_neutral = ...

        # Detect contradictory evidence
        conflict_signal = edge_detector.detect_contradictory_evidence(
            weighted_support, weighted_refute
        )

        if conflict_signal.edge_case_type == EdgeCaseType.CONTRADICTORY_EVIDENCE:
            logger.warning(
                "contradictory_evidence_detected",
                claim_id=str(claim_id),
                support_score=weighted_support,
                refute_score=weighted_refute
            )
            return VerificationPipelineResult(
                verdict=VerdictLabel.CONFLICTING,
                confidence=max(weighted_support, weighted_refute),
                reasoning=self._generate_conflict_reasoning(...),
                edge_case_type=EdgeCaseType.CONTRADICTORY_EVIDENCE,
                edge_case_confidence=conflict_signal.confidence
            )

        # Detect ambiguous evidence
        ambiguous_signal = edge_detector.detect_ambiguous_evidence(
            weighted_neutral,
            max(weighted_support, weighted_refute, weighted_neutral)
        )

        if ambiguous_signal.edge_case_type == EdgeCaseType.AMBIGUOUS_EVIDENCE:
            logger.info(
                "ambiguous_evidence_detected",
                claim_id=str(claim_id),
                neutral_score=weighted_neutral
            )
            return VerificationPipelineResult(
                verdict=VerdictLabel.AMBIGUOUS,
                confidence=weighted_neutral,
                reasoning=self._generate_ambiguity_reasoning(...),
                edge_case_type=EdgeCaseType.AMBIGUOUS_EVIDENCE,
                edge_case_confidence=ambiguous_signal.confidence
            )

        # Standard verdict logic (existing)
        return self._standard_verdict_aggregation(...)

    async def _fallback_keyword_verification(
        self,
        db: Session,
        claim_id: UUID,
        claim_text: str
    ) -> VerificationPipelineResult:
        """Fallback to keyword-based verification when embedding fails."""
        logger.warning(
            "using_fallback_keyword_verification",
            claim_id=str(claim_id)
        )

        # Use keyword search (no embeddings required)
        # This is a degraded service but better than complete failure
        return VerificationPipelineResult(
            verdict=VerdictLabel.INSUFFICIENT,
            confidence=0.0,
            reasoning="Verification service degraded: using keyword-only search",
            is_degraded=True,
            degradation_reason="embedding_service_failure"
        )

    def _create_error_verdict(
        self,
        claim_id: UUID,
        claim_text: str,
        error_message: str
    ) -> VerificationPipelineResult:
        """Create safe verdict when pipeline fails catastrophically."""
        return VerificationPipelineResult(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=VerdictLabel.INSUFFICIENT,
            confidence=0.0,
            reasoning=f"Verification failed due to system error: {error_message}",
            is_error=True,
            error_message=error_message
        )
```

### 5.4 Error Propagation vs. Containment Strategy

```python
# Error Containment Strategy

class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    INFO = "info"          # Log and continue
    WARNING = "warning"    # Log, flag, continue with degraded service
    ERROR = "error"        # Retry, then fallback
    CRITICAL = "critical"  # Abort pipeline, return safe verdict

ERROR_HANDLING_MATRIX = {
    # (Error Type, Severity, Action)
    "encoding_error": (ErrorSeverity.ERROR, "reject_with_validation_error"),
    "claim_too_short": (ErrorSeverity.WARNING, "process_with_warning"),
    "claim_too_long": (ErrorSeverity.WARNING, "process_with_truncation_warning"),
    "embedding_failure": (ErrorSeverity.ERROR, "retry_then_fallback_keyword"),
    "nli_failure": (ErrorSeverity.ERROR, "retry_then_fallback_similarity"),
    "database_error": (ErrorSeverity.CRITICAL, "abort_return_error_verdict"),
    "model_load_failure": (ErrorSeverity.CRITICAL, "abort_return_503"),
    "insufficient_evidence": (ErrorSeverity.INFO, "return_insufficient_verdict"),
    "contradictory_evidence": (ErrorSeverity.WARNING, "return_conflicting_verdict"),
}

def handle_error(error_type: str, context: dict):
    """Central error handling dispatcher."""
    severity, action = ERROR_HANDLING_MATRIX.get(
        error_type,
        (ErrorSeverity.ERROR, "default_error_handling")
    )

    if severity == ErrorSeverity.CRITICAL:
        # Don't try to recover, fail fast
        raise PipelineFailureError(f"Critical error: {error_type}")

    if severity == ErrorSeverity.ERROR:
        # Try recovery strategies
        return execute_recovery_action(action, context)

    if severity == ErrorSeverity.WARNING:
        # Log and continue with degraded service
        logger.warning(error_type, **context)
        return execute_degraded_action(action, context)

    # INFO: Just log
    logger.info(error_type, **context)
    return None
```

---

## 6. Implementation Guidance

### 6.1 Phase 1: Input Validation Layer (Week 1)

**Priority**: High
**Effort**: 12-16 hours
**Blockers**: None
**Owner**: Python-Pro or Backend-Architect

**Tasks:**
1. **Create validation module** (`truthgraph/validation/claim_validator.py`)
   - Implement `ClaimValidator` class
   - Implement `ValidationResult` dataclass
   - Add encoding validation
   - Add length validation
   - Add structure validation
   - Write unit tests (pytest)

2. **Integrate with API layer**
   - Add validation to `VerifyRequest` processing
   - Return structured validation errors
   - Update `ErrorResponse` model with validation codes

3. **Integrate with pipeline**
   - Call validator before pipeline execution
   - Handle `ValidationStatus.INVALID` → reject
   - Handle `ValidationStatus.WARNING` → log and proceed

**Code Changes:**
```
CREATE: truthgraph/validation/__init__.py
CREATE: truthgraph/validation/claim_validator.py
MODIFY: truthgraph/services/verification_pipeline_service.py
MODIFY: truthgraph/api/ml_routes.py
CREATE: tests/unit/validation/test_claim_validator.py
```

**Success Criteria:**
- All 7 validation cases covered
- 100% test coverage for validator
- Integration tests passing
- API returns structured validation errors

### 6.2 Phase 2: Edge Case Detection Layer (Week 2)

**Priority**: High
**Effort**: 16-20 hours
**Blockers**: Phase 1 completion
**Owner**: Backend-Architect

**Tasks:**
1. **Create edge case detection module** (`truthgraph/detection/edge_case_detector.py`)
   - Implement `EdgeCaseDetector` class
   - Implement `EdgeCaseSignal` dataclass
   - Add `classify_claim` method
   - Add `detect_insufficient_evidence` method
   - Add `detect_contradictory_evidence` method
   - Add `detect_ambiguous_evidence` method
   - Write unit tests

2. **Extend verdict labels**
   - Add `CONFLICTING` to `VerdictLabel` enum
   - Add `AMBIGUOUS` to `VerdictLabel` enum
   - Update database schema (migration)
   - Update API models

3. **Integrate with pipeline**
   - Call detector at appropriate points
   - Use edge signals to adjust thresholds
   - Return new verdict types when detected

**Code Changes:**
```
CREATE: truthgraph/detection/__init__.py
CREATE: truthgraph/detection/edge_case_detector.py
MODIFY: truthgraph/services/verification_pipeline_service.py
MODIFY: truthgraph/schemas.py (add verdict labels)
MODIFY: truthgraph/api/models.py (add verdict labels)
CREATE: alembic/versions/xxx_add_conflicting_ambiguous_verdicts.py
CREATE: tests/unit/detection/test_edge_case_detector.py
```

**Success Criteria:**
- All 7 edge case types detectable
- Conflict detection accuracy >80%
- Ambiguity detection accuracy >70%
- CONFLICTING/AMBIGUOUS verdicts returned correctly
- Database migration succeeds

### 6.3 Phase 3: Enhanced Aggregation (Week 2)

**Priority**: High
**Effort**: 8-12 hours
**Blockers**: Phase 2 completion
**Owner**: Python-Pro

**Tasks:**
1. **Update verdict aggregation service**
   - Modify `_aggregate_verdict` to use edge detector
   - Add `_generate_conflict_reasoning` method
   - Add `_generate_ambiguity_reasoning` method
   - Update existing reasoning generation

2. **Add verdict result metadata**
   - Add `edge_case_type` field to result
   - Add `edge_case_confidence` field
   - Add `has_conflict` flag (already exists, ensure used)

3. **Write integration tests**
   - Test with contradictory evidence corpus
   - Test with ambiguous evidence corpus
   - Verify correct verdict labels returned

**Code Changes:**
```
MODIFY: truthgraph/services/ml/verdict_aggregation_service.py
MODIFY: truthgraph/services/verification_pipeline_service.py
CREATE: tests/integration/test_edge_case_verdicts.py
```

**Success Criteria:**
- Contradictory evidence returns CONFLICTING (>90%)
- Ambiguous evidence returns AMBIGUOUS (>80%)
- Reasoning clearly explains edge case type
- Integration tests pass for all edge cases

### 6.4 Phase 4: Graceful Degradation (Week 3)

**Priority**: Medium
**Effort**: 12-16 hours
**Blockers**: Phase 1-3 completion
**Owner**: Backend-Architect

**Tasks:**
1. **Implement fallback mechanisms**
   - Add `_fallback_keyword_verification` method
   - Add `_fallback_similarity_verdict` method
   - Add `_create_error_verdict` method

2. **Add error recovery logic**
   - Wrap embedding generation with fallback
   - Wrap NLI verification with fallback
   - Add graceful failure for DB errors

3. **Add degradation flags**
   - Add `is_degraded` field to result
   - Add `degradation_reason` field
   - Log degradation events

**Code Changes:**
```
MODIFY: truthgraph/services/verification_pipeline_service.py
CREATE: tests/integration/test_degradation.py
MODIFY: truthgraph/api/models.py (add degradation fields)
```

**Success Criteria:**
- Pipeline doesn't crash on ML failures
- Fallback methods return reasonable verdicts
- Degradation logged and surfaced in API
- Integration tests verify fallback paths

### 6.5 Phase 5: Monitoring & Observability (Week 3)

**Priority**: Medium
**Effort**: 8-12 hours
**Blockers**: Phase 1-4 completion
**Owner**: DevOps/Deployment-Engineer

**Tasks:**
1. **Add edge case metrics**
   - Edge case detection rate by type
   - Validation failure rate by code
   - Conflict/ambiguity verdict rate
   - Degradation event rate

2. **Create monitoring dashboard**
   - Grafana dashboard for edge cases
   - Alerts for high validation failure rates
   - Alerts for high degradation rates

3. **Enhance structured logging**
   - Add edge case context to all logs
   - Add validation context
   - Add degradation context

**Code Changes:**
```
CREATE: grafana/dashboards/edge_cases.json
MODIFY: truthgraph/services/verification_pipeline_service.py (add metrics)
MODIFY: truthgraph/monitoring/memory_monitor.py (add edge case metrics)
```

**Success Criteria:**
- Dashboard displays edge case metrics
- Alerts fire on anomalies
- Logs include edge case context
- Metrics exportable to Prometheus/CloudWatch

---

## 7. Integration Strategy

### 7.1 Integration with Feature 3.1 (Test Fixtures)

**Integration Points:**
- Use edge case corpus fixtures in integration tests
- Validate all 34 edge case claims with new system
- Ensure expected verdicts match edge case definitions

**Test Coverage:**
```python
@pytest.mark.integration
@pytest.mark.parametrize("edge_case_category", [
    "insufficient_evidence",
    "contradictory_evidence",
    "ambiguous_evidence",
    "long_claims",
    "short_claims",
    "special_characters",
    "adversarial_examples"
])
async def test_edge_case_handling(
    edge_case_category,
    all_edge_cases,
    verification_pipeline_service,
    test_db
):
    """Test that each edge case category is handled correctly."""
    claims = all_edge_cases[edge_case_category]["claims"]

    for claim in claims:
        result = await verification_pipeline_service.verify_claim(
            db=test_db,
            claim_id=uuid4(),
            claim_text=claim["text"],
            use_cache=False
        )

        # Verify result matches expected behavior
        assert result.edge_case_type.value == edge_case_category

        # Verify verdict matches expected (with some flexibility)
        expected_verdict = claim["expected_verdict"]
        if expected_verdict == "CONFLICTING":
            assert result.verdict == VerdictLabel.CONFLICTING
        elif expected_verdict == "AMBIGUOUS":
            assert result.verdict in [VerdictLabel.AMBIGUOUS, VerdictLabel.INSUFFICIENT]
        # ... etc
```

### 7.2 Integration with Feature 3.3 Tests

The existing test file (`tests/fixtures/edge_cases/test_edge_cases.py`) focuses on **data validation**. We need to add **behavior validation** tests.

**New Test Module:**
```python
# tests/integration/test_edge_case_behavior.py

"""Integration tests for edge case handling behavior."""

class TestEdgeCaseHandling:
    """Test system behavior for each edge case category."""

    @pytest.mark.integration
    async def test_insufficient_evidence_returns_insufficient(
        self, edge_case_insufficient_evidence, verification_service, test_db
    ):
        """Test that claims with no evidence return INSUFFICIENT."""
        claims = edge_case_insufficient_evidence["claims"]

        for claim in claims:
            result = await verification_service.verify_claim(
                db=test_db,
                claim_id=uuid4(),
                claim_text=claim["text"]
            )

            assert result.verdict == VerdictLabel.INSUFFICIENT
            assert result.edge_case_type == EdgeCaseType.INSUFFICIENT_EVIDENCE
            assert len(result.evidence_items) == 0

    @pytest.mark.integration
    async def test_contradictory_evidence_returns_conflicting(
        self, edge_case_contradictory, verification_service, test_db_with_evidence
    ):
        """Test that contradictory evidence returns CONFLICTING."""
        claims = edge_case_contradictory["claims"]

        for claim in claims:
            # Insert contradictory evidence into DB
            self._insert_contradictory_evidence(test_db_with_evidence, claim)

            result = await verification_service.verify_claim(
                db=test_db_with_evidence,
                claim_id=uuid4(),
                claim_text=claim["text"]
            )

            assert result.verdict == VerdictLabel.CONFLICTING
            assert result.edge_case_type == EdgeCaseType.CONTRADICTORY_EVIDENCE
            assert result.has_conflict == True
            assert abs(result.support_score - result.refute_score) < 0.2

    @pytest.mark.integration
    async def test_ambiguous_evidence_lower_confidence(
        self, edge_case_ambiguous, verification_service, test_db_with_evidence
    ):
        """Test that ambiguous evidence has lower confidence."""
        claims = edge_case_ambiguous["claims"]

        for claim in claims:
            result = await verification_service.verify_claim(
                db=test_db_with_evidence,
                claim_id=uuid4(),
                claim_text=claim["text"]
            )

            # Should return AMBIGUOUS or INSUFFICIENT with low confidence
            assert result.verdict in [VerdictLabel.AMBIGUOUS, VerdictLabel.INSUFFICIENT]
            assert result.confidence < 0.6  # Low confidence threshold
            assert result.neutral_score > result.support_score
            assert result.neutral_score > result.refute_score

    @pytest.mark.integration
    async def test_long_claims_no_truncation(
        self, edge_case_long_claims, verification_service, test_db
    ):
        """Test that long claims don't cause errors."""
        claims = edge_case_long_claims["claims"]

        for claim in claims:
            word_count = len(claim["text"].split())
            assert word_count >= 150  # Verify it's actually long

            # Should not raise exception
            result = await verification_service.verify_claim(
                db=test_db,
                claim_id=uuid4(),
                claim_text=claim["text"]
            )

            # Verify metadata indicates long claim
            assert result.edge_case_type == EdgeCaseType.LONG_CLAIM
            # Should complete successfully
            assert result.pipeline_duration_ms > 0

    @pytest.mark.integration
    async def test_short_claims_process_successfully(
        self, edge_case_short_claims, verification_service, test_db
    ):
        """Test that short claims are processed (with warnings)."""
        claims = edge_case_short_claims["claims"]

        for claim in claims:
            word_count = len(claim["text"].split())

            if word_count >= 2:  # 2+ words should process
                result = await verification_service.verify_claim(
                    db=test_db,
                    claim_id=uuid4(),
                    claim_text=claim["text"]
                )

                assert result.edge_case_type == EdgeCaseType.SHORT_CLAIM
                assert result is not None  # Should complete
            else:  # Single word should be rejected
                with pytest.raises(ValueError, match="SINGLE_WORD_CLAIM"):
                    await verification_service.verify_claim(
                        db=test_db,
                        claim_id=uuid4(),
                        claim_text=claim["text"]
                    )

    @pytest.mark.integration
    async def test_special_characters_unicode_handling(
        self, edge_case_special_characters, verification_service, test_db
    ):
        """Test that special characters and Unicode are handled correctly."""
        claims = edge_case_special_characters["claims"]

        for claim in claims:
            # Should not raise encoding errors
            result = await verification_service.verify_claim(
                db=test_db,
                claim_id=uuid4(),
                claim_text=claim["text"]
            )

            # Verify text is preserved correctly
            assert result.claim_text == claim["text"]
            # Should complete successfully
            assert result is not None
```

### 7.3 Backward Compatibility Strategy

**Database Migration:**
```sql
-- alembic/versions/xxx_add_edge_case_verdicts.py
"""Add CONFLICTING and AMBIGUOUS verdict labels."""

def upgrade():
    # Add new verdict labels (PostgreSQL enum extension)
    op.execute("""
        ALTER TYPE verdict_label
        ADD VALUE IF NOT EXISTS 'CONFLICTING';

        ALTER TYPE verdict_label
        ADD VALUE IF NOT EXISTS 'AMBIGUOUS';
    """)

    # Add edge case metadata columns
    op.add_column('verification_results',
        sa.Column('edge_case_type', sa.String(50), nullable=True))
    op.add_column('verification_results',
        sa.Column('edge_case_confidence', sa.Float, nullable=True))
    op.add_column('verification_results',
        sa.Column('is_degraded', sa.Boolean, default=False))
    op.add_column('verification_results',
        sa.Column('degradation_reason', sa.String(255), nullable=True))

def downgrade():
    # Remove columns (keep enum values for safety)
    op.drop_column('verification_results', 'degradation_reason')
    op.drop_column('verification_results', 'is_degraded')
    op.drop_column('verification_results', 'edge_case_confidence')
    op.drop_column('verification_results', 'edge_case_type')
```

**API Versioning:**
- New verdict labels (`CONFLICTING`, `AMBIGUOUS`) are additive
- Existing clients will receive these as new values
- Old verdicts (`SUPPORTED`, `REFUTED`, `INSUFFICIENT`) unchanged
- No breaking changes to existing API contracts

**Feature Flag:**
```python
# Configuration for gradual rollout
EDGE_CASE_DETECTION_ENABLED = os.getenv("EDGE_CASE_DETECTION_ENABLED", "true") == "true"

if EDGE_CASE_DETECTION_ENABLED:
    edge_signal = edge_detector.classify_claim(claim_text)
else:
    edge_signal = None  # Fall back to standard processing
```

---

## 8. Monitoring & Observability

### 8.1 Key Metrics

**Edge Case Detection Metrics:**
```python
# Prometheus/CloudWatch metrics
edge_case_detections_total = Counter(
    'edge_case_detections_total',
    'Total number of edge cases detected',
    ['edge_case_type']
)

validation_failures_total = Counter(
    'validation_failures_total',
    'Total number of validation failures',
    ['error_code']
)

verdict_by_type = Counter(
    'verdicts_total',
    'Total verdicts issued',
    ['verdict_label', 'edge_case_type']
)

conflict_score_difference = Histogram(
    'conflict_score_difference',
    'Score difference in conflicting evidence scenarios',
    buckets=[0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.0]
)

pipeline_degradation_events = Counter(
    'pipeline_degradation_events_total',
    'Total degradation events',
    ['degradation_reason']
)
```

**Dashboard Widgets:**
1. **Edge Case Distribution** (Pie chart)
   - Breakdown of edge case types detected
   - Standard vs. edge cases ratio

2. **Validation Failure Rate** (Time series)
   - Validation failures over time
   - Breakdown by error code

3. **Verdict Distribution** (Stacked bar chart)
   - SUPPORTED / REFUTED / INSUFFICIENT / CONFLICTING / AMBIGUOUS
   - Trend over time

4. **Conflict Detection** (Gauge + histogram)
   - Current conflict rate
   - Score difference distribution

5. **Degradation Events** (Time series + alert)
   - Degradation event rate
   - Alert when exceeds threshold

### 8.2 Alerting Rules

```yaml
# alerting_rules.yml

groups:
  - name: edge_case_alerts
    interval: 5m
    rules:
      - alert: HighValidationFailureRate
        expr: rate(validation_failures_total[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High validation failure rate detected"
          description: "Validation failure rate is {{ $value }} failures/sec"

      - alert: HighDegradationRate
        expr: rate(pipeline_degradation_events_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High pipeline degradation rate"
          description: "Pipeline degradation rate is {{ $value }} events/sec"

      - alert: ExcessiveConflictingVerdicts
        expr: |
          rate(verdicts_total{verdict_label="CONFLICTING"}[1h])
          / rate(verdicts_total[1h]) > 0.3
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High rate of conflicting evidence"
          description: "{{ $value | humanizePercentage }} of verdicts are conflicting"

      - alert: ModelInferenceFailures
        expr: rate(nli_inference_failed_total[5m]) > 0.02
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "NLI model inference failures detected"
          description: "Model failure rate is {{ $value }} failures/sec"
```

### 8.3 Structured Logging

**Enhanced Log Context:**
```python
logger.info(
    "edge_case_detection",
    claim_id=str(claim_id),
    edge_case_type=edge_signal.edge_case_type.value,
    edge_case_confidence=edge_signal.confidence,
    indicators=edge_signal.indicators,
    recommended_action=edge_signal.recommended_action,
    metadata=edge_signal.metadata
)

logger.warning(
    "validation_failure",
    claim_id=str(claim_id),
    error_type=validation_result.error_type,
    error_code=validation_result.error_code,
    message=validation_result.message,
    suggestion=validation_result.suggestion
)

logger.warning(
    "pipeline_degradation",
    claim_id=str(claim_id),
    degradation_reason=degradation_reason,
    fallback_method=fallback_method,
    original_error=str(original_error)
)

logger.info(
    "verdict_with_edge_case",
    claim_id=str(claim_id),
    verdict=result.verdict.value,
    confidence=result.confidence,
    edge_case_type=result.edge_case_type.value if result.edge_case_type else None,
    has_conflict=result.has_conflict,
    is_degraded=result.is_degraded
)
```

**Log Aggregation Queries:**
```
# Splunk/ELK queries for analysis

# Edge case distribution
source="verification_pipeline" edge_case_type=*
| stats count by edge_case_type

# Validation failures by code
source="verification_pipeline" validation_failure
| stats count by error_code

# Conflicting verdicts analysis
source="verification_pipeline" verdict=CONFLICTING
| stats avg(support_score) avg(refute_score) avg(confidence)

# Degradation events
source="verification_pipeline" pipeline_degradation
| stats count by degradation_reason
| sort -count
```

### 8.4 Health Check Integration

**Enhanced Health Check:**
```python
# truthgraph/api/ml_routes.py

@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check with edge case detection system status."""

    services = {}
    overall_status = "healthy"

    # Database check
    try:
        db.execute("SELECT 1")
        services["database"] = ServiceStatus(status="healthy", latency_ms=5.0)
    except Exception as e:
        services["database"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )
        overall_status = "unhealthy"

    # Embedding service check
    try:
        embedding_service = EmbeddingService.get_instance()
        start = time.time()
        embedding_service.embed_text("test")
        latency = (time.time() - start) * 1000
        services["embedding_service"] = ServiceStatus(
            status="healthy",
            latency_ms=latency
        )
    except Exception as e:
        services["embedding_service"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )
        overall_status = "degraded"  # Can still function with fallback

    # NLI service check
    try:
        nli_service = NLIService.get_instance()
        start = time.time()
        nli_service.verify_single("premise", "hypothesis")
        latency = (time.time() - start) * 1000
        services["nli_service"] = ServiceStatus(
            status="healthy",
            latency_ms=latency
        )
    except Exception as e:
        services["nli_service"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )
        overall_status = "degraded"

    # Edge case detector check (NEW)
    try:
        detector = EdgeCaseDetector()
        detector.classify_claim("test claim")
        services["edge_case_detector"] = ServiceStatus(status="healthy")
    except Exception as e:
        services["edge_case_detector"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )
        overall_status = "degraded"

    # Validator check (NEW)
    try:
        validator = ClaimValidator()
        validator.validate("test claim")
        services["claim_validator"] = ServiceStatus(status="healthy")
    except Exception as e:
        services["claim_validator"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        services=services,
        version="2.1.0"  # Increment for edge case handling
    )
```

---

## 9. Error Codes Reference

### 9.1 Validation Error Codes

| Error Code | Type | Description | Action |
|------------|------|-------------|--------|
| `EMPTY_TEXT` | INVALID | Claim text is empty | Reject |
| `ENCODING_MISMATCH` | INVALID | UTF-8 round-trip failed | Reject |
| `REPLACEMENT_CHAR` | INVALID | Invalid Unicode replacement character | Reject |
| `UNICODE_ERROR` | INVALID | Unicode encoding error | Reject |
| `SINGLE_WORD_CLAIM` | INVALID | Single word is not verifiable | Reject |
| `NO_ALPHANUMERIC` | INVALID | No alphanumeric characters | Reject |
| `MINIMAL_CONTEXT` | WARNING | Very short claim (<3 words) | Process with warning |
| `POTENTIAL_TRUNCATION` | WARNING | Claim may be truncated (>450 tokens) | Process with warning |

### 9.2 Edge Case Type Codes

| Edge Case Type | Code | Detection Criteria | Verdict Mapping |
|----------------|------|-------------------|-----------------|
| Standard | `STANDARD` | Default | Standard logic |
| Insufficient Evidence | `INSUFFICIENT_EVIDENCE` | No evidence found | INSUFFICIENT |
| Contradictory Evidence | `CONTRADICTORY_EVIDENCE` | Support ≈ Refute scores | CONFLICTING |
| Ambiguous Evidence | `AMBIGUOUS_EVIDENCE` | Neutral score dominates | AMBIGUOUS |
| Long Claim | `LONG_CLAIM` | >150 words | Standard logic |
| Short Claim | `SHORT_CLAIM` | <3 words | Standard logic (adjusted threshold) |
| Special Characters | `SPECIAL_CHARACTERS` | >10% non-ASCII | Standard logic |
| Adversarial | `ADVERSARIAL` | Pattern detection | Flag for review |

### 9.3 Degradation Reason Codes

| Reason Code | Description | Fallback Method |
|-------------|-------------|-----------------|
| `embedding_service_failure` | Embedding generation failed | Keyword search only |
| `nli_service_failure` | NLI inference failed | Similarity-based verdict |
| `database_connection_lost` | Database unavailable | Return error verdict |
| `model_not_loaded` | ML model failed to load | Service unavailable (503) |
| `timeout_exceeded` | Operation timed out | Partial results or error verdict |

---

## 10. Success Criteria & Acceptance Tests

### 10.1 Success Criteria

**Functional Requirements:**
- ✓ All 7 edge case categories detected correctly (>85% accuracy)
- ✓ `CONFLICTING` verdict returned for contradictory evidence
- ✓ `AMBIGUOUS` verdict returned for weak/neutral evidence
- ✓ Input validation rejects malformed inputs with clear errors
- ✓ Special characters and Unicode handled without crashes
- ✓ Long claims processed without truncation errors
- ✓ Short claims processed with appropriate warnings
- ✓ Pipeline gracefully degrades on ML failures

**Non-Functional Requirements:**
- ✓ <10ms overhead for validation layer
- ✓ <20ms overhead for edge case detection
- ✓ No performance degradation to existing pipeline (<5%)
- ✓ 100% backward compatibility (existing verdicts unchanged)
- ✓ All edge cases logged with structured context
- ✓ Monitoring dashboard displays edge case metrics

### 10.2 Acceptance Test Suite

**Test Coverage:**
```
Edge Case Handling Tests:
├── Insufficient Evidence (5 claims) ........... 100%
├── Contradictory Evidence (4 claims) .......... 100%
├── Ambiguous Evidence (5 claims) .............. 100%
├── Long Claims (5 claims) ..................... 100%
├── Short Claims (5 claims) .................... 100%
├── Special Characters (5 claims) .............. 100%
└── Adversarial Examples (5 claims) ............ 80% (pattern detection)

Validation Tests:
├── Encoding validation ........................ 100%
├── Length validation .......................... 100%
├── Structure validation ....................... 100%
└── Error message clarity ...................... 100%

Degradation Tests:
├── Embedding failure fallback ................. 100%
├── NLI failure fallback ....................... 100%
├── Database error handling .................... 100%
└── Graceful failure ........................... 100%

Integration Tests:
├── End-to-end edge case verification .......... 100%
├── API error responses ........................ 100%
├── Backward compatibility ..................... 100%
└── Monitoring integration ..................... 100%
```

**Run All Tests:**
```bash
# Unit tests
pytest tests/unit/validation/ -v
pytest tests/unit/detection/ -v

# Integration tests
pytest tests/integration/test_edge_case_behavior.py -v
pytest tests/integration/test_degradation.py -v

# Full edge case corpus
pytest tests/fixtures/edge_cases/test_edge_cases.py -v

# Performance tests (no degradation)
pytest tests/performance/test_edge_case_overhead.py -v
```

---

## 11. Risk Assessment & Mitigation

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Edge case detection adds latency | Medium | Medium | Profile and optimize, cache classification results |
| New verdict labels break clients | Low | High | Additive changes only, document in API changelog |
| Fallback mechanisms return poor verdicts | Medium | Medium | Extensive testing, flag degraded results clearly |
| Validation too strict, rejects valid claims | Medium | High | Conservative thresholds, allow warnings vs. errors |
| Special character handling has edge cases | Medium | Low | Comprehensive Unicode test suite |
| Conflict detection false positives | Medium | Medium | Tune thresholds based on evaluation data |

### 11.2 Risk Mitigation Strategies

**Performance Risk Mitigation:**
- Profile validation and detection layers before deployment
- Cache validation results for repeated claims
- Use async operations where possible
- Set timeout limits for detection operations

**Compatibility Risk Mitigation:**
- Feature flag for gradual rollout
- Comprehensive backward compatibility tests
- Monitor error rates after deployment
- Quick rollback plan if issues arise

**Quality Risk Mitigation:**
- Extensive testing with edge case corpus (34 claims)
- Manual review of verdicts for each edge case type
- Confidence threshold tuning with validation data
- A/B testing of new vs. old verdict logic

---

## 12. Conclusion & Recommendations

### 12.1 Summary of Findings

**Current State:**
- Solid foundation with retry logic and basic error handling
- Good handling of insufficient evidence scenarios
- Limited specialized handling for edge cases
- No distinction between edge case types in verdicts

**Recommended Improvements:**
1. **High Priority:**
   - Add input validation layer (encoding, length, structure)
   - Add edge case detection layer (classify claim types)
   - Extend verdict labels (CONFLICTING, AMBIGUOUS)
   - Enhance verdict aggregation with conflict/ambiguity detection

2. **Medium Priority:**
   - Implement graceful degradation for ML failures
   - Add comprehensive monitoring and alerting
   - Create observability dashboard for edge cases

3. **Low Priority:**
   - Advanced adversarial pattern detection (ML-based)
   - Claim decomposition for very long claims
   - Automated confidence threshold tuning

### 12.2 Implementation Roadmap

**Week 1: Foundation**
- Day 1-2: Input validation layer
- Day 3-4: Integration with API and pipeline
- Day 5: Unit and integration tests

**Week 2: Edge Case Detection**
- Day 1-2: Edge case detection layer
- Day 3: Verdict label extensions (DB + API)
- Day 4-5: Enhanced aggregation logic

**Week 3: Polish & Observability**
- Day 1-2: Graceful degradation mechanisms
- Day 3: Monitoring dashboard and alerts
- Day 4-5: End-to-end testing with edge case corpus

**Total Effort**: ~60-70 hours across 3 weeks

### 12.3 Success Metrics

**Measure success by:**
- Edge case detection accuracy >85%
- Validation error clarity (manual review of error messages)
- Zero crashes on special characters or encoding issues
- Degradation events <1% of total verifications
- Performance overhead <5% on standard claims
- All 34 edge case corpus claims handled correctly

### 12.4 Next Steps

1. **Review this document** with stakeholders and team
2. **Prioritize phases** based on business needs
3. **Assign owners** to each phase (suggested in implementation guidance)
4. **Create feature branch** (`feature/edge-case-handling`)
5. **Begin Phase 1** (Input Validation Layer)
6. **Iterate and test** with edge case corpus throughout

---

## Appendices

### Appendix A: Code Structure

```
truthgraph/
├── validation/
│   ├── __init__.py
│   └── claim_validator.py         # NEW: Input validation
├── detection/
│   ├── __init__.py
│   └── edge_case_detector.py      # NEW: Edge case detection
├── services/
│   ├── ml/
│   │   ├── nli_service.py         # Enhanced: Better error handling
│   │   └── verdict_aggregation_service.py  # Enhanced: Conflict/ambiguity detection
│   └── verification_pipeline_service.py    # Enhanced: Graceful degradation
├── api/
│   ├── models.py                  # Enhanced: New verdict labels, error codes
│   └── ml_routes.py               # Enhanced: Validation integration
├── monitoring/
│   └── edge_case_metrics.py       # NEW: Edge case metrics
└── schemas.py                     # Enhanced: New verdict enum values

tests/
├── unit/
│   ├── validation/
│   │   └── test_claim_validator.py        # NEW
│   └── detection/
│       └── test_edge_case_detector.py     # NEW
├── integration/
│   ├── test_edge_case_behavior.py         # NEW
│   └── test_degradation.py                # NEW
└── fixtures/
    └── edge_cases/
        └── test_edge_cases.py             # EXISTING: Data validation

alembic/
└── versions/
    └── xxx_add_edge_case_verdicts.py      # NEW: Database migration
```

### Appendix B: Configuration

```python
# truthgraph/config/edge_case_config.py

"""Configuration for edge case handling."""

from dataclasses import dataclass

@dataclass
class EdgeCaseConfig:
    """Configuration for edge case detection and handling."""

    # Feature flags
    edge_case_detection_enabled: bool = True
    validation_enabled: bool = True
    graceful_degradation_enabled: bool = True

    # Validation thresholds
    min_claim_words: int = 2
    max_claim_words: int = 500
    max_tokens_estimate: int = 450

    # Detection thresholds
    conflict_threshold: float = 0.3
    conflict_margin: float = 0.15
    ambiguity_threshold: float = 0.55
    non_ascii_threshold: float = 0.1

    # Performance settings
    validation_timeout_ms: int = 100
    detection_timeout_ms: int = 200

    # Monitoring
    enable_metrics: bool = True
    enable_detailed_logging: bool = True
```

### Appendix C: References

**Internal Documentation:**
- Edge Case Corpus README: `tests/fixtures/edge_cases/README.md`
- Phase 2 Implementation Plan: `planning/phases/phase_2/README.md`
- Verification Pipeline Documentation: `truthgraph/services/README_VERIFICATION_PIPELINE.md`

**External Resources:**
- Natural Language Inference: https://paperswithcode.com/task/natural-language-inference
- Graceful Degradation Patterns: https://www.martinfowler.com/articles/patterns-of-distributed-systems/
- Error Handling Best Practices: https://12factor.net/

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Author**: Backend System Architect
**Status**: Ready for Review
**Next Review**: After Phase 1 implementation

---
