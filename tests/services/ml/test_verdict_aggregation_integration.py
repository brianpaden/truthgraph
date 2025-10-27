"""Integration tests for Verdict Aggregation Service with realistic scenarios.

These tests simulate real-world scenarios with mock NLI results to validate
the aggregation service behavior in production-like conditions.
"""

import pytest

from truthgraph.services.ml import (
    AggregationStrategy,
    NLILabel,
    NLIResult,
    VerdictAggregationService,
    VerdictLabel,
    get_verdict_aggregation_service,
)


@pytest.fixture
def service():
    """Create a fresh service instance."""
    VerdictAggregationService._instance = None
    service = get_verdict_aggregation_service()
    yield service
    VerdictAggregationService._instance = None


class TestRealWorldScenarios:
    """Test real-world verification scenarios."""

    def test_scientific_claim_strong_support(self, service):
        """Test verification of a well-supported scientific claim.

        Scenario: Claim about Earth's rotation backed by multiple strong sources.
        """
        # Simulating: "Earth rotates on its axis once every 24 hours"
        # With evidence from multiple scientific sources
        results = [
            # NASA source - high confidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.96,
                scores={"entailment": 0.96, "neutral": 0.03, "contradiction": 0.01},
            ),
            # Textbook source - high confidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.94,
                scores={"entailment": 0.94, "neutral": 0.04, "contradiction": 0.02},
            ),
            # Encyclopedia source - high confidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
            # Research paper - slightly lower but still high
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.confidence > 0.9
        assert verdict.supporting_count == 4
        assert not verdict.has_conflict
        assert "High confidence" in verdict.explanation

    def test_controversial_claim_mixed_evidence(self, service):
        """Test verification of a controversial claim with mixed evidence.

        Scenario: Claim with both supporting and refuting evidence from different sources.
        """
        # Simulating a controversial health claim
        results = [
            # Supporting evidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.78,
                scores={"entailment": 0.78, "neutral": 0.15, "contradiction": 0.07},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.72,
                scores={"entailment": 0.72, "neutral": 0.18, "contradiction": 0.10},
            ),
            # Refuting evidence
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.82,
                scores={"entailment": 0.08, "neutral": 0.10, "contradiction": 0.82},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.76,
                scores={"entailment": 0.10, "neutral": 0.14, "contradiction": 0.76},
            ),
            # Neutral evidence
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.68,
                scores={"entailment": 0.20, "neutral": 0.68, "contradiction": 0.12},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.has_conflict
        assert "WARNING" in verdict.explanation
        assert "Conflicting evidence" in verdict.explanation
        # Could be any verdict depending on weights
        assert isinstance(verdict.verdict, VerdictLabel)

    def test_misinformation_clear_refutation(self, service):
        """Test verification of clear misinformation with strong refutation.

        Scenario: False claim with multiple sources refuting it.
        """
        # Simulating: "The Earth is flat" - clearly refuted
        results = [
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.98,
                scores={"entailment": 0.01, "neutral": 0.01, "contradiction": 0.98},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.96,
                scores={"entailment": 0.01, "neutral": 0.03, "contradiction": 0.96},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.94,
                scores={"entailment": 0.02, "neutral": 0.04, "contradiction": 0.94},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.REFUTED
        assert verdict.confidence > 0.95
        assert verdict.refuting_count == 3
        assert not verdict.has_conflict

    def test_ambiguous_claim_mostly_neutral(self, service):
        """Test verification of an ambiguous claim with mostly neutral evidence.

        Scenario: Opinion-based or subjective claim where evidence is inconclusive.
        """
        # Simulating an opinion or subjective statement
        results = [
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.82,
                scores={"entailment": 0.10, "neutral": 0.82, "contradiction": 0.08},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.76,
                scores={"entailment": 0.15, "neutral": 0.76, "contradiction": 0.09},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.79,
                scores={"entailment": 0.12, "neutral": 0.79, "contradiction": 0.09},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.58,
                scores={"entailment": 0.58, "neutral": 0.30, "contradiction": 0.12},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.UNCERTAIN
        assert verdict.neutral_count >= 3

    def test_insufficient_evidence_all_low_confidence(self, service):
        """Test claim with insufficient evidence (all low confidence).

        Scenario: Not enough reliable evidence to make a determination.
        """
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.48,
                scores={"entailment": 0.48, "neutral": 0.35, "contradiction": 0.17},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.45,
                scores={"entailment": 0.25, "neutral": 0.30, "contradiction": 0.45},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.42,
                scores={"entailment": 0.30, "neutral": 0.42, "contradiction": 0.28},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        # All filtered out, should be uncertain
        assert verdict.verdict == VerdictLabel.UNCERTAIN
        assert "excluded due to low confidence" in verdict.explanation


class TestStrategyComparisons:
    """Test comparing different aggregation strategies on same data."""

    def test_weighted_vs_majority_with_varying_confidence(self, service):
        """Compare weighted vote and majority vote with varying confidence levels."""
        # Scenario: Two high-confidence refutes vs three low-confidence supports
        results = [
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.95,
                scores={"entailment": 0.02, "neutral": 0.03, "contradiction": 0.95},
            ),
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.92,
                scores={"entailment": 0.03, "neutral": 0.05, "contradiction": 0.92},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.62,
                scores={"entailment": 0.62, "neutral": 0.25, "contradiction": 0.13},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.58,
                scores={"entailment": 0.58, "neutral": 0.28, "contradiction": 0.14},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.55,
                scores={"entailment": 0.55, "neutral": 0.30, "contradiction": 0.15},
            ),
        ]

        # Weighted vote should favor high-confidence refutations
        weighted = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        # Majority vote should favor the count (3 support vs 2 refute)
        majority = service.aggregate(results, strategy=AggregationStrategy.MAJORITY_VOTE)

        # Weighted likely refuted, majority likely supported
        assert weighted.verdict == VerdictLabel.REFUTED  # High confidence refutes win
        assert majority.verdict == VerdictLabel.SUPPORTED  # More votes win

    def test_strict_consensus_vs_weighted_vote(self, service):
        """Compare strict consensus with weighted vote."""
        # Scenario: Strong support but one dissenting voice
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.90,
                scores={"entailment": 0.90, "neutral": 0.07, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
            NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.75,
                scores={"entailment": 0.15, "neutral": 0.75, "contradiction": 0.10},
            ),
        ]

        weighted = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)
        consensus = service.aggregate(results, strategy=AggregationStrategy.STRICT_CONSENSUS)

        # Weighted should be SUPPORTED (strong majority)
        assert weighted.verdict == VerdictLabel.SUPPORTED
        assert not weighted.has_conflict

        # Strict consensus should be UNCERTAIN (not unanimous)
        assert consensus.verdict == VerdictLabel.UNCERTAIN
        assert consensus.has_conflict


class TestScalability:
    """Test service with varying amounts of evidence."""

    def test_minimal_evidence_single_source(self, service):
        """Test with minimal evidence (single source)."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.evidence_count == 1

    def test_moderate_evidence_5_to_10_sources(self, service):
        """Test with moderate evidence (5-10 sources)."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.80 + i * 0.02,
                scores={"entailment": 0.80, "neutral": 0.15, "contradiction": 0.05},
            )
            for i in range(7)
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.evidence_count == 7
        assert verdict.supporting_count == 7

    def test_large_evidence_50_plus_sources(self, service):
        """Test with large amount of evidence (50+ sources)."""
        # Simulate 50 sources with realistic distribution
        results = []

        # 35 supporting
        for i in range(35):
            results.append(
                NLIResult(
                    label=NLILabel.ENTAILMENT,
                    confidence=0.70 + (i % 20) * 0.01,
                    scores={"entailment": 0.80, "neutral": 0.15, "contradiction": 0.05},
                )
            )

        # 10 refuting
        for i in range(10):
            results.append(
                NLIResult(
                    label=NLILabel.CONTRADICTION,
                    confidence=0.65 + (i % 15) * 0.01,
                    scores={"entailment": 0.05, "neutral": 0.15, "contradiction": 0.80},
                )
            )

        # 5 neutral
        for i in range(5):
            results.append(
                NLIResult(
                    label=NLILabel.NEUTRAL,
                    confidence=0.60 + (i % 10) * 0.01,
                    scores={"entailment": 0.20, "neutral": 0.70, "contradiction": 0.10},
                )
            )

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.evidence_count == 50
        assert verdict.verdict == VerdictLabel.SUPPORTED  # Strong majority
        assert verdict.supporting_count >= 30


class TestConfidenceLevels:
    """Test behavior across different confidence level ranges."""

    def test_very_high_confidence_unanimous(self, service):
        """Test with very high confidence unanimous evidence (>0.9)."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.96,
                scores={"entailment": 0.96, "neutral": 0.03, "contradiction": 0.01},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.94,
                scores={"entailment": 0.94, "neutral": 0.04, "contradiction": 0.02},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.confidence > 0.9
        assert "High confidence" in verdict.explanation

    def test_medium_confidence_range(self, service):
        """Test with medium confidence evidence (0.6-0.8)."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.72,
                scores={"entailment": 0.72, "neutral": 0.20, "contradiction": 0.08},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.68,
                scores={"entailment": 0.68, "neutral": 0.22, "contradiction": 0.10},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        # When all evidence points to same verdict, normalized confidence is 1.0
        # This is correct - 100% of weighted score goes to SUPPORTED
        assert verdict.confidence == 1.0
        assert verdict.support_score == 1.0

    def test_borderline_confidence_near_threshold(self, service):
        """Test with confidence levels near the threshold (0.45-0.55)."""
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.52,
                scores={"entailment": 0.52, "neutral": 0.30, "contradiction": 0.18},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.48,  # Just below threshold
                scores={"entailment": 0.48, "neutral": 0.32, "contradiction": 0.20},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.54,
                scores={"entailment": 0.54, "neutral": 0.28, "contradiction": 0.18},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        # One should be filtered, two should count
        assert verdict.supporting_count == 2


class TestProductionEdgeCases:
    """Test edge cases that might occur in production."""

    def test_temporal_evidence_changing_over_time(self, service):
        """Test scenario where evidence changes over time.

        Simulates verification done at different times with different results.
        """
        # Old evidence - supported
        old_results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.85,
                scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            ),
        ]

        # New evidence - refuted
        new_results = [
            NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.90,
                scores={"entailment": 0.03, "neutral": 0.07, "contradiction": 0.90},
            ),
        ]

        # Combined evidence shows conflict
        combined = old_results + new_results

        verdict = service.aggregate(combined, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.has_conflict
        assert "WARNING" in verdict.explanation

    def test_duplicate_similar_evidence(self, service):
        """Test handling of duplicate or very similar evidence."""
        # Same evidence source cited multiple times
        results = [
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04},
            ),
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.88,
                scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        # Should still aggregate correctly
        assert verdict.verdict == VerdictLabel.SUPPORTED
        assert verdict.supporting_count == 3

    def test_multilingual_evidence_simulation(self, service):
        """Test simulating evidence from multiple languages.

        Different confidence levels might occur due to translation quality.
        """
        results = [
            # English source - high confidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.92,
                scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            ),
            # Translated source - slightly lower confidence
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.78,
                scores={"entailment": 0.78, "neutral": 0.15, "contradiction": 0.07},
            ),
            # Another translated source
            NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=0.75,
                scores={"entailment": 0.75, "neutral": 0.17, "contradiction": 0.08},
            ),
        ]

        verdict = service.aggregate(results, strategy=AggregationStrategy.WEIGHTED_VOTE)

        assert verdict.verdict == VerdictLabel.SUPPORTED
        # Weighted average accounts for varying confidence
        assert verdict.supporting_count == 3
