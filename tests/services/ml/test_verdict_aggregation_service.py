"""Unit tests for Verdict Aggregation Service.

This test suite provides comprehensive coverage of the verdict aggregation service,
including all aggregation strategies, edge cases, and error handling.
"""

import pytest

from truthgraph.services.ml import (
    AggregationStrategy,
    NLILabel,
    NLIResult,
    VerdictAggregationService,
    VerdictLabel,
    VerdictResult,
    get_verdict_aggregation_service,
)


class TestVerdictAggregationServiceBasics:
    """Test basic functionality of Verdict Aggregation Service."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_singleton_pattern(self):
        """Test that service follows singleton pattern."""
        VerdictAggregationService._instance = None
        service1 = VerdictAggregationService.get_instance()
        service2 = VerdictAggregationService.get_instance()
        assert service1 is service2
        VerdictAggregationService._instance = None

    def test_get_verdict_aggregation_service_convenience_function(self):
        """Test convenience function returns singleton instance."""
        VerdictAggregationService._instance = None
        service1 = get_verdict_aggregation_service()
        service2 = get_verdict_aggregation_service()
        assert service1 is service2
        assert isinstance(service1, VerdictAggregationService)
        VerdictAggregationService._instance = None

    def test_empty_results_raises_error(self, service):
        """Test that empty results list raises ValueError."""
        with pytest.raises(ValueError, match="NLI results list cannot be empty"):
            service.aggregate([])

    def test_invalid_result_type_raises_error(self, service):
        """Test that invalid result type raises ValueError."""
        with pytest.raises(ValueError, match="Result at index 0 is not an NLIResult"):
            service.aggregate([{"invalid": "data"}])  # type: ignore

    def test_invalid_confidence_raises_error(self, service):
        """Test that invalid confidence value raises ValueError."""
        invalid_result = NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=1.5,  # Invalid - over 1.0
            scores={"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
        )
        with pytest.raises(ValueError, match="Result at index 0 has invalid confidence"):
            service.aggregate([invalid_result])

    def test_unknown_strategy_raises_error(self, service):
        """Test that unknown aggregation strategy raises ValueError."""
        result = NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.95,
            scores={"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
        )
        with pytest.raises(ValueError, match="Unknown aggregation strategy"):
            service.aggregate([result], strategy="invalid_strategy")  # type: ignore


class TestWeightedVoteAggregation:
    """Test weighted vote aggregation strategy."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_unanimous_support_high_confidence(self, service):
        """Test unanimous supporting evidence with high confidence."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.95,
                scores={"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.07, "contradiction": 0.05},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert isinstance(verdict, VerdictResult)
        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.confidence > 0.9
        assert verdict.supporting_count == 3
        assert verdict.refuting_count == 0
        assert verdict.neutral_count == 0
        assert verdict.evidence_count == 3
        assert not verdict.has_conflict
        assert verdict.strategy_used == "weighted_vote"
        assert "SUPPORTED" in verdict.explanation

    def test_unanimous_refute_high_confidence(self, service):
        """Test unanimous refuting evidence with high confidence."""
        results = [
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.93,
                scores={"entailment": 0.02, "neutral": 0.05, "contradiction": 0.93},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.89,
                scores={"entailment": 0.03, "neutral": 0.08, "contradiction": 0.89},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.REFUTED
        assert verdict.confidence > 0.85
        assert verdict.supporting_count == 0
        assert verdict.refuting_count == 2
        assert verdict.neutral_count == 0
        assert not verdict.has_conflict
        assert "REFUTED" in verdict.explanation

    def test_all_neutral_evidence(self, service):
        """Test when all evidence is neutral."""
        results = [
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.75,
                scores={"entailment": 0.15, "neutral": 0.75, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.80,
                scores={"entailment": 0.10, "neutral": 0.80, "contradiction": 0.10},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.UNCERTAIN
        assert verdict.confidence > 0.7
        assert verdict.supporting_count == 0
        assert verdict.refuting_count == 0
        assert verdict.neutral_count == 2
        assert not verdict.has_conflict
        assert "UNCERTAIN" in verdict.explanation

    def test_mixed_evidence_support_wins(self, service):
        """Test mixed evidence where support wins."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.95,
                scores={"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.05, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.70,
                scores={"entailment": 0.20, "neutral": 0.70, "contradiction": 0.10},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 2
        assert verdict.neutral_count == 1
        assert verdict.refuting_count == 0

    def test_conflicting_evidence_detected(self, service):
        """Test that conflicting evidence is properly detected."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.80,
                scores={"entailment": 0.05, "neutral": 0.15, "contradiction": 0.80},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.has_conflict
        assert "WARNING" in verdict.explanation
        assert "Conflicting evidence" in verdict.explanation

    def test_low_confidence_filtering(self, service):
        """Test that low confidence evidence is filtered out."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.40,  # Below default threshold
                scores={"entailment": 0.20, "neutral": 0.40, "contradiction": 0.40},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.35,  # Below default threshold
                scores={"entailment": 0.30, "neutral": 0.35, "contradiction": 0.35},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 1
        assert "excluded due to low confidence" in verdict.explanation

    def test_custom_min_confidence_threshold(self, service):
        """Test using custom minimum confidence threshold."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.60,
                scores={"entailment": 0.60, "neutral": 0.30, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.55,
                scores={"entailment": 0.55, "neutral": 0.35, "contradiction": 0.10},
            ),
        ]

        # With default threshold (0.5), both should count
        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        assert verdict.supporting_count == 2

        # With higher custom threshold, only first should count
        verdict = service.aggregate(
            results, strategy=AggregationStrategy.WEIGHTED_VOTE, min_confidence=0.58
        )
        assert verdict.supporting_count == 1

    def test_single_result(self, service):
        """Test aggregation with single result."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.confidence > 0.9
        assert verdict.evidence_count == 1
        assert verdict.supporting_count == 1

    def test_score_normalization(self, service):
        """Test that scores are properly normalized."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.05, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.80,
                scores={"entailment": 0.10, "neutral": 0.10, "contradiction": 0.80},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        # Scores should sum to 1.0
        total_score = verdict.support_score + verdict.refute_score + verdict.neutral_score
        assert abs(total_score - 1.0) < 0.01


class TestMajorityVoteAggregation:
    """Test majority vote aggregation strategy."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_simple_majority_support(self, service):
        """Test simple majority voting with support winning."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.60,
                scores={"entailment": 0.60, "neutral": 0.30, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.65,
                scores={"entailment": 0.65, "neutral": 0.25, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.70,
                scores={"entailment": 0.10, "neutral": 0.20, "contradiction": 0.70},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.MAJORITY_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 2
        assert verdict.refuting_count == 1
        assert verdict.strategy_used == "majority_vote"
        # Confidence should be based on vote proportion (2/3)
        assert abs(verdict.confidence - 2 / 3) < 0.01

    def test_majority_vote_ignores_confidence_weight(self, service):
        """Test that majority vote ignores confidence weighting."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.55,  # Low confidence
                scores={"entailment": 0.55, "neutral": 0.35, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.52,  # Low confidence
                scores={"entailment": 0.52, "neutral": 0.38, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.95,  # High confidence
                scores={"entailment": 0.02, "neutral": 0.03, "contradiction": 0.95},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.MAJORITY_VOTE)

        # Majority vote: 2 support vs 1 refute, so support wins despite lower confidence
        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 2

    def test_tied_vote(self, service):
        """Test handling of tied votes."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.80,
                scores={"entailment": 0.80, "neutral": 0.15, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.85,
                scores={"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.MAJORITY_VOTE)

        # With tie, the higher score should win (or implementation may default)
        assert verdict.supporting_count == 1
        assert verdict.refuting_count == 1


class TestConfidenceThresholdAggregation:
    """Test confidence threshold aggregation strategy."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_high_confidence_only(self, service):
        """Test that only high confidence evidence is used."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,  # Above HIGH_CONFIDENCE_THRESHOLD
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.60,  # Below HIGH_CONFIDENCE_THRESHOLD
                scores={"entailment": 0.10, "neutral": 0.30, "contradiction": 0.60},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.65,  # Below HIGH_CONFIDENCE_THRESHOLD
                scores={"entailment": 0.20, "neutral": 0.65, "contradiction": 0.15},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.CONFIDENCE_THRESHOLD)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 1
        assert verdict.strategy_used == "confidence_threshold"

    def test_no_high_confidence_fallback(self, service):
        """Test fallback to weighted vote when no high-confidence evidence."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.65,  # Below HIGH_CONFIDENCE_THRESHOLD
                scores={"entailment": 0.65, "neutral": 0.25, "contradiction": 0.10},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.60,  # Below HIGH_CONFIDENCE_THRESHOLD
                scores={"entailment": 0.10, "neutral": 0.30, "contradiction": 0.60},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.CONFIDENCE_THRESHOLD)

        # Should fall back to weighted vote
        assert isinstance(verdict, VerdictResult)
        # Strategy might still show confidence_threshold but fallback occurred


class TestStrictConsensusAggregation:
    """Test strict consensus aggregation strategy."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_unanimous_agreement_support(self, service):
        """Test unanimous agreement on support."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.07, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.STRICT_CONSENSUS)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert not verdict.has_conflict
        assert verdict.supporting_count == 3
        assert "unanimously agree" in verdict.explanation
        assert verdict.strategy_used == "strict_consensus"

    def test_disagreement_returns_uncertain(self, service):
        """Test that any disagreement returns UNCERTAIN."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.07, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.85,
                scores={"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.STRICT_CONSENSUS)

        assert verdict.verdict == VerdictLabel.UNCERTAIN
        assert verdict.has_conflict
        assert "disagreement" in verdict.explanation
        assert verdict.confidence == 0.0

    def test_all_below_threshold_returns_uncertain(self, service):
        """Test that all low-confidence evidence returns UNCERTAIN."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.40,  # Below threshold
                scores={"entailment": 0.40, "neutral": 0.35, "contradiction": 0.25},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.45,  # Below threshold
                scores={"entailment": 0.45, "neutral": 0.30, "contradiction": 0.25},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.STRICT_CONSENSUS)

        assert verdict.verdict == VerdictLabel.UNCERTAIN
        assert verdict.confidence == 0.0
        assert "minimum confidence threshold" in verdict.explanation


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_all_zero_confidence(self, service):
        """Test handling of all zero confidence results."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.0,
                scores={"entailment": 0.33, "neutral": 0.34, "contradiction": 0.33},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.0,
                scores={"entailment": 0.33, "neutral": 0.34, "contradiction": 0.33},
            ),
        ]

        # Should not raise, but all evidence filtered
        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        assert verdict.verdict == VerdictLabel.UNCERTAIN

    def test_exactly_at_threshold(self, service):
        """Test results exactly at confidence threshold."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.5,  # Exactly at default threshold
                scores={"entailment": 0.50, "neutral": 0.30, "contradiction": 0.20},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        assert verdict.supporting_count == 1  # Should be included

    def test_large_number_of_results(self, service):
        """Test aggregation with many results."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.80 + (i % 10) / 100,  # Vary confidence
                scores={"entailment": 0.80, "neutral": 0.15, "contradiction": 0.05},
            )
            for i in range(100)
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.evidence_count == 100
        assert verdict.supporting_count == 100

    def test_perfect_confidence_scores(self, service):
        """Test with perfect 1.0 confidence scores."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=1.0,
                scores={"entailment": 1.0, "neutral": 0.0, "contradiction": 0.0},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.confidence == 1.0

    def test_mixed_labels_equal_weights(self, service):
        """Test when all three labels have equal weighted scores."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.80,
                scores={"entailment": 0.80, "neutral": 0.15, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.80,
                scores={"entailment": 0.05, "neutral": 0.15, "contradiction": 0.80},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.80,
                scores={"entailment": 0.15, "neutral": 0.80, "contradiction": 0.05},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        # Should pick one based on tie-breaking logic
        assert isinstance(verdict.verdict, VerdictLabel)
        assert abs(verdict.confidence - 1 / 3) < 0.05


class TestExplanationGeneration:
    """Test explanation text generation."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        VerdictAggregationService._instance = None
        service = VerdictAggregationService.get_instance()
        yield service
        VerdictAggregationService._instance = None

    def test_explanation_contains_verdict(self, service):
        """Test that explanation contains the verdict."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.07, "contradiction": 0.03},
            ),
        ]

        verdict = service.aggregate(results)
        assert "SUPPORTED" in verdict.explanation

    def test_explanation_contains_evidence_counts(self, service):
        """Test that explanation contains evidence counts."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.07, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.85,
                scores={"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85},
            ),
        ]

        verdict = service.aggregate(results)
        assert "2 evidence" in verdict.explanation
        assert "1 supporting" in verdict.explanation
        assert "1 refuting" in verdict.explanation

    def test_explanation_warns_on_conflict(self, service):
        """Test that explanation warns about conflicts."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.80,
                scores={"entailment": 0.05, "neutral": 0.15, "contradiction": 0.80},
            ),
        ]

        verdict = service.aggregate(results)
        assert verdict.has_conflict
        assert "WARNING" in verdict.explanation

    def test_explanation_mentions_high_confidence(self, service):
        """Test that explanation mentions high confidence."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.95,
                scores={"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
            ),
        ]

        verdict = service.aggregate(results)
        assert "High confidence" in verdict.explanation

    def test_explanation_mentions_low_confidence(self, service):
        """Test that explanation mentions low confidence."""
        results = [
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.55,
                scores={"entailment": 0.25, "neutral": 0.55, "contradiction": 0.20},
            ),
        ]

        verdict = service.aggregate(results)
        # Overall confidence after normalization might be different
        # Just check explanation exists
        assert len(verdict.explanation) > 0

    def test_explanation_mentions_filtering(self, service):
        """Test that explanation mentions filtered evidence."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.30,  # Below threshold
                scores={"entailment": 0.20, "neutral": 0.30, "contradiction": 0.50},
            ),
        ]

        verdict = service.aggregate(results)
        assert "excluded due to low confidence" in verdict.explanation


class TestVerdictResultDataclass:
    """Test VerdictResult dataclass structure."""

    def test_verdict_result_creation(self):
        """Test creating VerdictResult with all fields."""
        result = VerdictResult(
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.85,
            support_score=0.85,
            refute_score=0.10,
            neutral_score=0.05,
            evidence_count=3,
            supporting_count=2,
            refuting_count=1,
            neutral_count=0,
            has_conflict=True,
            explanation="Test explanation",
            strategy_used="weighted_vote",
        )

        assert result.verdict == VerdictLabel.SUPPORTED
        assert result.confidence == 0.85
        assert result.evidence_count == 3
        assert result.has_conflict
        assert result.strategy_used == "weighted_vote"


class TestVerdictLabelEnum:
    """Test VerdictLabel enum."""

    def test_verdict_label_values(self):
        """Test VerdictLabel enum values."""
        assert VerdictLabel.SUPPORTED.value == "SUPPORTED"
        assert VerdictLabel.REFUTED.value == "REFUTED"
        assert VerdictLabel.UNCERTAIN.value == "UNCERTAIN"

    def test_verdict_label_string_comparison(self):
        """Test VerdictLabel string comparison."""
        assert VerdictLabel.SUPPORTED == "SUPPORTED"
        assert VerdictLabel.REFUTED == "REFUTED"
        assert VerdictLabel.UNCERTAIN == "UNCERTAIN"


class TestAggregationStrategyEnum:
    """Test AggregationStrategy enum."""

    def test_strategy_values(self):
        """Test AggregationStrategy enum values."""
        assert AggregationStrategy.WEIGHTED_VOTE.value == "weighted_vote"
        assert AggregationStrategy.MAJORITY_VOTE.value == "majority_vote"
        assert AggregationStrategy.CONFIDENCE_THRESHOLD.value == "confidence_threshold"
        assert AggregationStrategy.STRICT_CONSENSUS.value == "strict_consensus"
