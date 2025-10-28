"""Verdict Aggregation Service for combining multiple NLI results.

This module aggregates multiple NLI (Natural Language Inference) results into a single
final verdict using various strategies including weighted voting, confidence-based
aggregation, and conflict detection.

Example:
    >>> service = get_verdict_aggregation_service()
    >>> nli_results = [
    ...     NLIResult(label=NLILabel.ENTAILMENT, confidence=0.95, scores={...}),
    ...     NLIResult(label=NLILabel.ENTAILMENT, confidence=0.87, scores={...}),
    ...     NLIResult(label=NLILabel.NEUTRAL, confidence=0.65, scores={...}),
    ... ]
    >>> verdict = service.aggregate(nli_results)
    >>> print(verdict.verdict)  # VerdictLabel.SUPPORTED
    >>> print(verdict.confidence)  # 0.85
    >>> print(verdict.explanation)  # Human-readable reasoning
"""

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import structlog

from .nli_service import NLILabel, NLIResult

logger = structlog.get_logger(__name__)


class VerdictLabel(str, Enum):
    """Final verdict labels after aggregating NLI results."""

    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    UNCERTAIN = "UNCERTAIN"


class AggregationStrategy(str, Enum):
    """Strategy for aggregating NLI results."""

    WEIGHTED_VOTE = "weighted_vote"  # Weight votes by confidence scores
    MAJORITY_VOTE = "majority_vote"  # Simple majority voting
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Require minimum confidence
    STRICT_CONSENSUS = "strict_consensus"  # All evidence must agree


@dataclass
class VerdictResult:
    """Result of verdict aggregation from multiple NLI results.

    Attributes:
        verdict: Final verdict label (SUPPORTED, REFUTED, or UNCERTAIN)
        confidence: Overall confidence score (0.0-1.0)
        support_score: Weighted score for supporting evidence
        refute_score: Weighted score for refuting evidence
        neutral_score: Weighted score for neutral evidence
        evidence_count: Total number of evidence items analyzed
        supporting_count: Count of supporting evidence
        refuting_count: Count of refuting evidence
        neutral_count: Count of neutral evidence
        has_conflict: Whether contradictory evidence exists
        explanation: Human-readable explanation of the verdict
        strategy_used: Aggregation strategy that was applied
    """

    verdict: VerdictLabel
    confidence: float
    support_score: float
    refute_score: float
    neutral_score: float
    evidence_count: int
    supporting_count: int
    refuting_count: int
    neutral_count: int
    has_conflict: bool
    explanation: str
    strategy_used: str


class VerdictAggregationService:
    """Service for aggregating multiple NLI results into final verdicts.

    This service implements various aggregation strategies to combine multiple
    NLI predictions into a single verdict. It handles conflicting evidence,
    low confidence scores, and provides explanations for decisions.

    Performance target: <10ms for aggregation (no ML inference needed)

    Thread safety: This class is thread-safe (stateless operations).
    """

    _instance: ClassVar["VerdictAggregationService | None"] = None

    # Configuration thresholds
    MIN_CONFIDENCE_THRESHOLD: ClassVar[float] = 0.5  # Minimum confidence to count
    HIGH_CONFIDENCE_THRESHOLD: ClassVar[float] = 0.75  # High confidence threshold
    CONFLICT_THRESHOLD: ClassVar[float] = 0.3  # Min score difference to flag conflict
    MIN_EVIDENCE_FOR_VERDICT: ClassVar[int] = 1  # Minimum evidence needed

    # Label mapping from NLI to Verdict
    _LABEL_TO_VERDICT: ClassVar[dict[NLILabel, VerdictLabel]] = {
        NLILabel.ENTAILMENT: VerdictLabel.SUPPORTED,
        NLILabel.CONTRADICTION: VerdictLabel.REFUTED,
        NLILabel.NEUTRAL: VerdictLabel.UNCERTAIN,
    }

    def __init__(self) -> None:
        """Initialize Verdict Aggregation Service."""
        pass

    @classmethod
    def get_instance(cls) -> "VerdictAggregationService":
        """Get singleton instance of Verdict Aggregation Service.

        Returns:
            The singleton VerdictAggregationService instance
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info("verdict_aggregation_service_created")
        return cls._instance

    def aggregate(
        self,
        nli_results: list[NLIResult],
        strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_VOTE,
        min_confidence: float | None = None,
    ) -> VerdictResult:
        """Aggregate multiple NLI results into a final verdict.

        Args:
            nli_results: List of NLI results to aggregate
            strategy: Aggregation strategy to use (default: weighted_vote)
            min_confidence: Minimum confidence threshold (overrides default)

        Returns:
            VerdictResult containing final verdict and aggregation details

        Raises:
            ValueError: If nli_results is empty or contains invalid data

        Example:
            >>> service = get_verdict_aggregation_service()
            >>> results = [NLIResult(...), NLIResult(...)]
            >>> verdict = service.aggregate(results)
        """
        if not nli_results:
            raise ValueError("NLI results list cannot be empty")

        # Validate inputs
        for i, result in enumerate(nli_results):
            if not isinstance(result, NLIResult):
                raise ValueError(f"Result at index {i} is not an NLIResult")
            if result.confidence < 0.0 or result.confidence > 1.0:
                raise ValueError(f"Result at index {i} has invalid confidence: {result.confidence}")

        # Use default or provided min_confidence
        min_conf = min_confidence if min_confidence is not None else self.MIN_CONFIDENCE_THRESHOLD

        # Route to appropriate strategy
        if strategy == AggregationStrategy.WEIGHTED_VOTE:
            return self._aggregate_weighted_vote(nli_results, min_conf)
        elif strategy == AggregationStrategy.MAJORITY_VOTE:
            return self._aggregate_majority_vote(nli_results, min_conf)
        elif strategy == AggregationStrategy.CONFIDENCE_THRESHOLD:
            return self._aggregate_confidence_threshold(nli_results, min_conf)
        elif strategy == AggregationStrategy.STRICT_CONSENSUS:
            return self._aggregate_strict_consensus(nli_results, min_conf)
        else:
            raise ValueError(f"Unknown aggregation strategy: {strategy}")

    def _aggregate_weighted_vote(
        self, nli_results: list[NLIResult], min_confidence: float
    ) -> VerdictResult:
        """Aggregate using weighted voting based on confidence scores.

        Each NLI result contributes to the final score weighted by its confidence.
        This is the default and most robust strategy.

        Args:
            nli_results: List of NLI results
            min_confidence: Minimum confidence threshold

        Returns:
            VerdictResult with weighted aggregation
        """
        # Filter by confidence threshold
        filtered_results = [r for r in nli_results if r.confidence >= min_confidence]

        # Calculate counts
        total_count = len(nli_results)
        supporting = [r for r in filtered_results if r.label == NLILabel.ENTAILMENT]
        refuting = [r for r in filtered_results if r.label == NLILabel.CONTRADICTION]
        neutral = [r for r in filtered_results if r.label == NLILabel.NEUTRAL]

        supporting_count = len(supporting)
        refuting_count = len(refuting)
        neutral_count = len(neutral)

        # Calculate weighted scores
        support_score = sum(r.confidence for r in supporting)
        refute_score = sum(r.confidence for r in refuting)
        neutral_score = sum(r.confidence for r in neutral)

        # Normalize scores
        total_score = support_score + refute_score + neutral_score
        if total_score > 0:
            support_score_norm = support_score / total_score
            refute_score_norm = refute_score / total_score
            neutral_score_norm = neutral_score / total_score
        else:
            # No valid evidence - all uncertain
            support_score_norm = 0.0
            refute_score_norm = 0.0
            neutral_score_norm = 1.0

        # Determine verdict and confidence
        scores = {
            VerdictLabel.SUPPORTED: support_score_norm,
            VerdictLabel.REFUTED: refute_score_norm,
            VerdictLabel.UNCERTAIN: neutral_score_norm,
        }
        verdict = max(scores, key=scores.get)  # type: ignore
        confidence = scores[verdict]

        # Detect conflicts
        has_conflict = self._detect_conflict(support_score_norm, refute_score_norm)

        # Generate explanation
        explanation = self._generate_explanation(
            verdict=verdict,
            confidence=confidence,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            total_count=total_count,
            has_conflict=has_conflict,
            filtered_count=len(filtered_results),
        )

        logger.debug(
            "verdict_aggregation_complete",
            verdict=verdict.value,
            confidence=confidence,
            evidence_count=total_count,
            strategy="weighted_vote",
        )

        return VerdictResult(
            verdict=verdict,
            confidence=confidence,
            support_score=support_score_norm,
            refute_score=refute_score_norm,
            neutral_score=neutral_score_norm,
            evidence_count=total_count,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            has_conflict=has_conflict,
            explanation=explanation,
            strategy_used="weighted_vote",
        )

    def _aggregate_majority_vote(
        self, nli_results: list[NLIResult], min_confidence: float
    ) -> VerdictResult:
        """Aggregate using simple majority voting (count-based).

        Each NLI result gets one vote regardless of confidence.
        Useful when all evidence has similar reliability.

        Args:
            nli_results: List of NLI results
            min_confidence: Minimum confidence threshold

        Returns:
            VerdictResult with majority vote aggregation
        """
        # Filter by confidence threshold
        filtered_results = [r for r in nli_results if r.confidence >= min_confidence]

        total_count = len(nli_results)
        supporting_count = sum(1 for r in filtered_results if r.label == NLILabel.ENTAILMENT)
        refuting_count = sum(1 for r in filtered_results if r.label == NLILabel.CONTRADICTION)
        neutral_count = sum(1 for r in filtered_results if r.label == NLILabel.NEUTRAL)

        # Calculate simple vote proportions
        filtered_count = len(filtered_results)
        if filtered_count > 0:
            support_score = supporting_count / filtered_count
            refute_score = refuting_count / filtered_count
            neutral_score = neutral_count / filtered_count
        else:
            support_score = 0.0
            refute_score = 0.0
            neutral_score = 1.0

        # Determine verdict
        scores = {
            VerdictLabel.SUPPORTED: support_score,
            VerdictLabel.REFUTED: refute_score,
            VerdictLabel.UNCERTAIN: neutral_score,
        }
        verdict = max(scores, key=scores.get)  # type: ignore
        confidence = scores[verdict]

        # Detect conflicts
        has_conflict = self._detect_conflict(support_score, refute_score)

        # Generate explanation
        explanation = self._generate_explanation(
            verdict=verdict,
            confidence=confidence,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            total_count=total_count,
            has_conflict=has_conflict,
            filtered_count=filtered_count,
        )

        return VerdictResult(
            verdict=verdict,
            confidence=confidence,
            support_score=support_score,
            refute_score=refute_score,
            neutral_score=neutral_score,
            evidence_count=total_count,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            has_conflict=has_conflict,
            explanation=explanation,
            strategy_used="majority_vote",
        )

    def _aggregate_confidence_threshold(
        self, nli_results: list[NLIResult], min_confidence: float
    ) -> VerdictResult:
        """Aggregate using high-confidence evidence only.

        Only considers evidence above HIGH_CONFIDENCE_THRESHOLD.
        More conservative approach for critical decisions.

        Args:
            nli_results: List of NLI results
            min_confidence: Minimum confidence threshold (uses HIGH_CONFIDENCE_THRESHOLD)

        Returns:
            VerdictResult with high-confidence aggregation
        """
        # Use high confidence threshold instead
        high_conf = self.HIGH_CONFIDENCE_THRESHOLD

        # Filter by high confidence threshold
        high_conf_results = [r for r in nli_results if r.confidence >= high_conf]

        # If no high-confidence results, fall back to weighted vote
        if not high_conf_results:
            logger.warning(
                "no_high_confidence_evidence",
                total_count=len(nli_results),
                threshold=high_conf,
            )
            # Fall back to weighted vote with original threshold
            return self._aggregate_weighted_vote(nli_results, min_confidence)

        # Count high-confidence evidence
        total_count = len(nli_results)
        supporting_count = sum(1 for r in high_conf_results if r.label == NLILabel.ENTAILMENT)
        refuting_count = sum(1 for r in high_conf_results if r.label == NLILabel.CONTRADICTION)
        neutral_count = sum(1 for r in high_conf_results if r.label == NLILabel.NEUTRAL)

        # Calculate weighted scores from high-confidence evidence
        support_score = sum(
            r.confidence for r in high_conf_results if r.label == NLILabel.ENTAILMENT
        )
        refute_score = sum(
            r.confidence for r in high_conf_results if r.label == NLILabel.CONTRADICTION
        )
        neutral_score = sum(r.confidence for r in high_conf_results if r.label == NLILabel.NEUTRAL)

        total_score = support_score + refute_score + neutral_score
        if total_score > 0:
            support_score_norm = support_score / total_score
            refute_score_norm = refute_score / total_score
            neutral_score_norm = neutral_score / total_score
        else:
            support_score_norm = 0.0
            refute_score_norm = 0.0
            neutral_score_norm = 1.0

        # Determine verdict
        scores = {
            VerdictLabel.SUPPORTED: support_score_norm,
            VerdictLabel.REFUTED: refute_score_norm,
            VerdictLabel.UNCERTAIN: neutral_score_norm,
        }
        verdict = max(scores, key=scores.get)  # type: ignore
        confidence = scores[verdict]

        # Detect conflicts
        has_conflict = self._detect_conflict(support_score_norm, refute_score_norm)

        # Generate explanation
        explanation = self._generate_explanation(
            verdict=verdict,
            confidence=confidence,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            total_count=total_count,
            has_conflict=has_conflict,
            filtered_count=len(high_conf_results),
        )

        return VerdictResult(
            verdict=verdict,
            confidence=confidence,
            support_score=support_score_norm,
            refute_score=refute_score_norm,
            neutral_score=neutral_score_norm,
            evidence_count=total_count,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            has_conflict=has_conflict,
            explanation=explanation,
            strategy_used="confidence_threshold",
        )

    def _aggregate_strict_consensus(
        self, nli_results: list[NLIResult], min_confidence: float
    ) -> VerdictResult:
        """Aggregate requiring unanimous agreement among evidence.

        All evidence must agree on the same verdict (after filtering).
        Returns UNCERTAIN if any disagreement exists.

        Args:
            nli_results: List of NLI results
            min_confidence: Minimum confidence threshold

        Returns:
            VerdictResult with strict consensus requirement
        """
        # Filter by confidence threshold
        filtered_results = [r for r in nli_results if r.confidence >= min_confidence]

        if not filtered_results:
            # No valid evidence
            return VerdictResult(
                verdict=VerdictLabel.UNCERTAIN,
                confidence=0.0,
                support_score=0.0,
                refute_score=0.0,
                neutral_score=1.0,
                evidence_count=len(nli_results),
                supporting_count=0,
                refuting_count=0,
                neutral_count=len(nli_results),
                has_conflict=False,
                explanation="No evidence meets minimum confidence threshold for strict consensus.",
                strategy_used="strict_consensus",
            )

        # Check for unanimous agreement
        labels = {r.label for r in filtered_results}

        if len(labels) > 1:
            # Disagreement exists - return UNCERTAIN
            total_count = len(nli_results)
            supporting_count = sum(1 for r in filtered_results if r.label == NLILabel.ENTAILMENT)
            refuting_count = sum(1 for r in filtered_results if r.label == NLILabel.CONTRADICTION)
            neutral_count = sum(1 for r in filtered_results if r.label == NLILabel.NEUTRAL)

            return VerdictResult(
                verdict=VerdictLabel.UNCERTAIN,
                confidence=0.0,
                support_score=0.0,
                refute_score=0.0,
                neutral_score=1.0,
                evidence_count=total_count,
                supporting_count=supporting_count,
                refuting_count=refuting_count,
                neutral_count=neutral_count,
                has_conflict=True,
                explanation=f"Evidence shows disagreement: {supporting_count} supporting, {refuting_count} refuting, {neutral_count} neutral. Strict consensus requires unanimous agreement.",
                strategy_used="strict_consensus",
            )

        # Unanimous agreement
        unanimous_label = labels.pop()
        verdict = self._LABEL_TO_VERDICT[unanimous_label]

        # Calculate average confidence
        avg_confidence = sum(r.confidence for r in filtered_results) / len(filtered_results)

        total_count = len(nli_results)
        supporting_count = sum(1 for r in filtered_results if r.label == NLILabel.ENTAILMENT)
        refuting_count = sum(1 for r in filtered_results if r.label == NLILabel.CONTRADICTION)
        neutral_count = sum(1 for r in filtered_results if r.label == NLILabel.NEUTRAL)

        # Set scores based on verdict
        if verdict == VerdictLabel.SUPPORTED:
            support_score = 1.0
            refute_score = 0.0
            neutral_score = 0.0
        elif verdict == VerdictLabel.REFUTED:
            support_score = 0.0
            refute_score = 1.0
            neutral_score = 0.0
        else:
            support_score = 0.0
            refute_score = 0.0
            neutral_score = 1.0

        explanation = f"All {len(filtered_results)} evidence items unanimously agree on {verdict.value}. Average confidence: {avg_confidence:.2f}."

        return VerdictResult(
            verdict=verdict,
            confidence=avg_confidence,
            support_score=support_score,
            refute_score=refute_score,
            neutral_score=neutral_score,
            evidence_count=total_count,
            supporting_count=supporting_count,
            refuting_count=refuting_count,
            neutral_count=neutral_count,
            has_conflict=False,
            explanation=explanation,
            strategy_used="strict_consensus",
        )

    def _detect_conflict(self, support_score: float, refute_score: float) -> bool:
        """Detect if there's conflicting evidence.

        Conflict is detected when both support and refute scores exceed threshold.

        Args:
            support_score: Normalized support score
            refute_score: Normalized refute score

        Returns:
            True if conflict detected, False otherwise
        """
        return support_score >= self.CONFLICT_THRESHOLD and refute_score >= self.CONFLICT_THRESHOLD

    def _generate_explanation(
        self,
        verdict: VerdictLabel,
        confidence: float,
        supporting_count: int,
        refuting_count: int,
        neutral_count: int,
        total_count: int,
        has_conflict: bool,
        filtered_count: int,
    ) -> str:
        """Generate human-readable explanation for the verdict.

        Args:
            verdict: Final verdict
            confidence: Confidence score
            supporting_count: Number of supporting evidence
            refuting_count: Number of refuting evidence
            neutral_count: Number of neutral evidence
            total_count: Total evidence count
            has_conflict: Whether conflict was detected
            filtered_count: Number of evidence after filtering

        Returns:
            Human-readable explanation string
        """
        # Build explanation parts
        parts = []

        # Verdict statement
        if verdict == VerdictLabel.SUPPORTED:
            parts.append(f"Claim is SUPPORTED with {confidence:.1%} confidence.")
        elif verdict == VerdictLabel.REFUTED:
            parts.append(f"Claim is REFUTED with {confidence:.1%} confidence.")
        else:
            parts.append(f"Claim is UNCERTAIN with {confidence:.1%} confidence.")

        # Evidence breakdown
        parts.append(
            f"Analyzed {total_count} evidence items: "
            f"{supporting_count} supporting, {refuting_count} refuting, {neutral_count} neutral."
        )

        # Filtering note
        if filtered_count < total_count:
            excluded = total_count - filtered_count
            parts.append(f"{excluded} items excluded due to low confidence.")

        # Conflict warning
        if has_conflict:
            parts.append(
                "WARNING: Conflicting evidence detected. "
                "Both supporting and refuting evidence exist with significant confidence."
            )

        # Recommendation
        if confidence < self.MIN_CONFIDENCE_THRESHOLD:
            parts.append("Low confidence verdict - consider gathering more evidence.")
        elif confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            parts.append("High confidence verdict - strong evidence consensus.")

        return " ".join(parts)


def get_verdict_aggregation_service() -> VerdictAggregationService:
    """Get the singleton Verdict Aggregation Service instance.

    This is a convenience function for accessing the service.

    Returns:
        The singleton VerdictAggregationService instance

    Example:
        >>> service = get_verdict_aggregation_service()
        >>> verdict = service.aggregate(nli_results)
    """
    return VerdictAggregationService.get_instance()
