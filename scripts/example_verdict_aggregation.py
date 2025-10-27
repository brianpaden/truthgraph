"""Example usage of the Verdict Aggregation Service.

This script demonstrates how to use the verdict aggregation service
to combine multiple NLI results into a final verdict.

Usage:
    python scripts/example_verdict_aggregation.py
"""

from truthgraph.services.ml import (
    AggregationStrategy,
    NLILabel,
    NLIResult,
    get_verdict_aggregation_service,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_verdict(verdict, title: str = "Verdict") -> None:
    """Print formatted verdict results."""
    print(f"{title}:")
    print(f"  Verdict:       {verdict.verdict.value}")
    print(f"  Confidence:    {verdict.confidence:.1%}")
    print(f"  Evidence:      {verdict.evidence_count} items")
    print(f"    Supporting:  {verdict.supporting_count}")
    print(f"    Refuting:    {verdict.refuting_count}")
    print(f"    Neutral:     {verdict.neutral_count}")
    print(f"  Has Conflict:  {verdict.has_conflict}")
    print(f"  Strategy:      {verdict.strategy_used}")
    print()
    print("  Scores:")
    print(f"    Support:     {verdict.support_score:.3f}")
    print(f"    Refute:      {verdict.refute_score:.3f}")
    print(f"    Neutral:     {verdict.neutral_score:.3f}")
    print()
    print("  Explanation:")
    print(f"    {verdict.explanation}")
    print()


def example_1_strong_support() -> None:
    """Example 1: Strong supporting evidence."""
    print_section("Example 1: Strong Supporting Evidence")

    print("Scenario: Claim about scientific fact with strong evidence")
    print("Claim: 'The Earth orbits the Sun'")
    print()

    # Simulate NLI results from multiple high-quality sources
    nli_results = [
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
        NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.92,
            scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
        ),
    ]

    service = get_verdict_aggregation_service()
    verdict = service.aggregate(nli_results, strategy=AggregationStrategy.WEIGHTED_VOTE)

    print_verdict(verdict)


def example_2_conflicting_evidence() -> None:
    """Example 2: Conflicting evidence."""
    print_section("Example 2: Conflicting Evidence")

    print("Scenario: Controversial claim with mixed evidence")
    print("Claim: 'Coffee is healthy'")
    print()

    # Simulate conflicting NLI results
    nli_results = [
        NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.82,
            scores={"entailment": 0.82, "neutral": 0.12, "contradiction": 0.06},
        ),
        NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.78,
            scores={"entailment": 0.78, "neutral": 0.15, "contradiction": 0.07},
        ),
        NLIResult(
            label=NLILabel.CONTRADICTION,
            confidence=0.85,
            scores={"entailment": 0.06, "neutral": 0.09, "contradiction": 0.85},
        ),
        NLIResult(
            label=NLILabel.NEUTRAL,
            confidence=0.70,
            scores={"entailment": 0.20, "neutral": 0.70, "contradiction": 0.10},
        ),
    ]

    service = get_verdict_aggregation_service()
    verdict = service.aggregate(nli_results, strategy=AggregationStrategy.WEIGHTED_VOTE)

    print_verdict(verdict)


def example_3_strategy_comparison() -> None:
    """Example 3: Compare different aggregation strategies."""
    print_section("Example 3: Strategy Comparison")

    print("Scenario: Compare different strategies on same evidence")
    print("Evidence: 2 high-confidence refutes vs 3 low-confidence supports")
    print()

    nli_results = [
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

    service = get_verdict_aggregation_service()

    # Weighted vote - should favor high-confidence refutes
    weighted = service.aggregate(nli_results, strategy=AggregationStrategy.WEIGHTED_VOTE)
    print_verdict(weighted, "Strategy 1: Weighted Vote")

    # Majority vote - should favor the count
    majority = service.aggregate(nli_results, strategy=AggregationStrategy.MAJORITY_VOTE)
    print_verdict(majority, "Strategy 2: Majority Vote")

    # Strict consensus - should return UNCERTAIN
    consensus = service.aggregate(nli_results, strategy=AggregationStrategy.STRICT_CONSENSUS)
    print_verdict(consensus, "Strategy 3: Strict Consensus")


def example_4_low_confidence_filtering() -> None:
    """Example 4: Low confidence evidence filtering."""
    print_section("Example 4: Low Confidence Filtering")

    print("Scenario: Mixed confidence levels with filtering")
    print()

    nli_results = [
        NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.85,
            scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
        ),
        NLIResult(
            label=NLILabel.CONTRADICTION,
            confidence=0.40,  # Below threshold
            scores={"entailment": 0.20, "neutral": 0.40, "contradiction": 0.40},
        ),
        NLIResult(
            label=NLILabel.NEUTRAL,
            confidence=0.35,  # Below threshold
            scores={"entailment": 0.30, "neutral": 0.35, "contradiction": 0.35},
        ),
    ]

    service = get_verdict_aggregation_service()

    # Default threshold (0.5)
    verdict = service.aggregate(nli_results, strategy=AggregationStrategy.WEIGHTED_VOTE)
    print_verdict(verdict, "With Default Threshold (0.5)")

    # Lower threshold (0.3)
    verdict_lower = service.aggregate(
        nli_results,
        strategy=AggregationStrategy.WEIGHTED_VOTE,
        min_confidence=0.3,
    )
    print_verdict(verdict_lower, "With Lower Threshold (0.3)")


def example_5_misinformation() -> None:
    """Example 5: Clear misinformation refutation."""
    print_section("Example 5: Clear Misinformation")

    print("Scenario: False claim with strong refutation")
    print("Claim: 'The Earth is flat'")
    print()

    nli_results = [
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

    service = get_verdict_aggregation_service()
    verdict = service.aggregate(nli_results, strategy=AggregationStrategy.WEIGHTED_VOTE)

    print_verdict(verdict)


def main() -> None:
    """Run all examples."""
    print()
    print("=" * 80)
    print("  VERDICT AGGREGATION SERVICE - EXAMPLES")
    print("=" * 80)

    # Run all examples
    example_1_strong_support()
    example_2_conflicting_evidence()
    example_3_strategy_comparison()
    example_4_low_confidence_filtering()
    example_5_misinformation()

    # Summary
    print_section("Summary")
    print("The Verdict Aggregation Service successfully combines multiple NLI results")
    print("into final verdicts using various strategies:")
    print()
    print("  - Weighted Vote:         Best for general use, weights by confidence")
    print("  - Majority Vote:         Best when evidence has similar quality")
    print("  - Confidence Threshold:  Best for critical decisions")
    print("  - Strict Consensus:      Best when unanimity is required")
    print()
    print("Key features:")
    print("  - Automatic conflict detection")
    print("  - Confidence-based filtering")
    print("  - Human-readable explanations")
    print("  - <1ms aggregation performance")
    print()
    print("For more information, see:")
    print("  - Documentation: truthgraph/services/ml/README_VERDICT_AGGREGATION.md")
    print("  - Tests: tests/services/ml/test_verdict_aggregation*.py")
    print("  - Benchmarks: scripts/benchmark_verdict_aggregation.py")
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
