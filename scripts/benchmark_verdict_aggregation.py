"""Performance benchmarks for Verdict Aggregation Service.

This script benchmarks the aggregation service to ensure it meets the <10ms
performance target for aggregation operations.

Usage:
    python scripts/benchmark_verdict_aggregation.py
"""

import random
import statistics
import time
from typing import Any

from truthgraph.services.ml import (
    AggregationStrategy,
    NLILabel,
    NLIResult,
    get_verdict_aggregation_service,
)


def create_mock_nli_result(label: NLILabel, confidence: float) -> NLIResult:
    """Create a mock NLI result for benchmarking.

    Args:
        label: NLI label to assign
        confidence: Confidence score

    Returns:
        Mock NLIResult
    """
    if label == NLILabel.ENTAILMENT:
        scores = {
            "entailment": confidence,
            "neutral": (1.0 - confidence) * 0.6,
            "contradiction": (1.0 - confidence) * 0.4,
        }
    elif label == NLILabel.CONTRADICTION:
        scores = {
            "entailment": (1.0 - confidence) * 0.4,
            "neutral": (1.0 - confidence) * 0.6,
            "contradiction": confidence,
        }
    else:  # NEUTRAL
        scores = {
            "entailment": (1.0 - confidence) * 0.5,
            "neutral": confidence,
            "contradiction": (1.0 - confidence) * 0.5,
        }

    return NLIResult(label=label, confidence=confidence, scores=scores)


def benchmark_aggregation(
    name: str,
    nli_results: list[NLIResult],
    strategy: AggregationStrategy,
    iterations: int = 100,
) -> dict[str, Any]:
    """Benchmark a single aggregation scenario.

    Args:
        name: Name of the benchmark
        nli_results: List of NLI results to aggregate
        strategy: Aggregation strategy to use
        iterations: Number of iterations to run

    Returns:
        Dictionary with benchmark results
    """
    service = get_verdict_aggregation_service()
    times = []

    # Warmup run
    service.aggregate(nli_results, strategy=strategy)

    # Benchmark runs
    for _ in range(iterations):
        start = time.perf_counter()
        verdict = service.aggregate(nli_results, strategy=strategy)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to milliseconds

    return {
        "name": name,
        "strategy": strategy.value,
        "evidence_count": len(nli_results),
        "iterations": iterations,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "stddev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
        "p95_ms": statistics.quantiles(times, n=20)[18] if len(times) > 1 else times[0],
        "p99_ms": statistics.quantiles(times, n=100)[98] if len(times) > 1 else times[0],
        "verdict": verdict.verdict.value,
        "confidence": verdict.confidence,
    }


def run_benchmarks() -> None:
    """Run all benchmarks and display results."""
    print("=" * 80)
    print("Verdict Aggregation Service Performance Benchmarks")
    print("=" * 80)
    print()
    print("Target: <10ms per aggregation")
    print()

    benchmarks = []

    # Benchmark 1: Small dataset (3 evidence items) - Weighted Vote
    print("Running Benchmark 1: Small dataset (3 items, weighted vote)...")
    results_small = [
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.92),
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.88),
        create_mock_nli_result(NLILabel.NEUTRAL, 0.70),
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Small dataset - Weighted Vote",
            results_small,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=1000,
        )
    )

    # Benchmark 2: Medium dataset (10 evidence items) - Weighted Vote
    print("Running Benchmark 2: Medium dataset (10 items, weighted vote)...")
    results_medium = [
        create_mock_nli_result(
            random.choice([NLILabel.ENTAILMENT, NLILabel.CONTRADICTION, NLILabel.NEUTRAL]),
            random.uniform(0.6, 0.95),
        )
        for _ in range(10)
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Medium dataset - Weighted Vote",
            results_medium,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=1000,
        )
    )

    # Benchmark 3: Large dataset (50 evidence items) - Weighted Vote
    print("Running Benchmark 3: Large dataset (50 items, weighted vote)...")
    results_large = [
        create_mock_nli_result(
            random.choice([NLILabel.ENTAILMENT, NLILabel.CONTRADICTION, NLILabel.NEUTRAL]),
            random.uniform(0.6, 0.95),
        )
        for _ in range(50)
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Large dataset - Weighted Vote",
            results_large,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=500,
        )
    )

    # Benchmark 4: Very large dataset (100 evidence items) - Weighted Vote
    print("Running Benchmark 4: Very large dataset (100 items, weighted vote)...")
    results_very_large = [
        create_mock_nli_result(
            random.choice([NLILabel.ENTAILMENT, NLILabel.CONTRADICTION, NLILabel.NEUTRAL]),
            random.uniform(0.6, 0.95),
        )
        for _ in range(100)
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Very large dataset - Weighted Vote",
            results_very_large,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=500,
        )
    )

    # Benchmark 5: Majority Vote strategy
    print("Running Benchmark 5: Medium dataset (10 items, majority vote)...")
    benchmarks.append(
        benchmark_aggregation(
            "Medium dataset - Majority Vote",
            results_medium,
            AggregationStrategy.MAJORITY_VOTE,
            iterations=1000,
        )
    )

    # Benchmark 6: Confidence Threshold strategy
    print("Running Benchmark 6: Medium dataset (10 items, confidence threshold)...")
    benchmarks.append(
        benchmark_aggregation(
            "Medium dataset - Confidence Threshold",
            results_medium,
            AggregationStrategy.CONFIDENCE_THRESHOLD,
            iterations=1000,
        )
    )

    # Benchmark 7: Strict Consensus strategy
    print("Running Benchmark 7: Medium dataset (10 items, strict consensus)...")
    benchmarks.append(
        benchmark_aggregation(
            "Medium dataset - Strict Consensus",
            results_medium,
            AggregationStrategy.STRICT_CONSENSUS,
            iterations=1000,
        )
    )

    # Benchmark 8: Conflicting evidence scenario
    print("Running Benchmark 8: Conflicting evidence (weighted vote)...")
    results_conflict = [
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.90),
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.85),
        create_mock_nli_result(NLILabel.CONTRADICTION, 0.88),
        create_mock_nli_result(NLILabel.CONTRADICTION, 0.82),
        create_mock_nli_result(NLILabel.NEUTRAL, 0.75),
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Conflicting evidence - Weighted Vote",
            results_conflict,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=1000,
        )
    )

    # Benchmark 9: Low confidence filtering scenario
    print("Running Benchmark 9: Mixed confidence levels (weighted vote)...")
    results_mixed_conf = [
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.92),
        create_mock_nli_result(NLILabel.ENTAILMENT, 0.45),  # Below threshold
        create_mock_nli_result(NLILabel.CONTRADICTION, 0.38),  # Below threshold
        create_mock_nli_result(NLILabel.NEUTRAL, 0.85),
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Mixed confidence - Weighted Vote",
            results_mixed_conf,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=1000,
        )
    )

    # Benchmark 10: Extreme scale (200 evidence items)
    print("Running Benchmark 10: Extreme scale (200 items, weighted vote)...")
    results_extreme = [
        create_mock_nli_result(
            random.choice([NLILabel.ENTAILMENT, NLILabel.CONTRADICTION, NLILabel.NEUTRAL]),
            random.uniform(0.6, 0.95),
        )
        for _ in range(200)
    ]
    benchmarks.append(
        benchmark_aggregation(
            "Extreme scale - Weighted Vote",
            results_extreme,
            AggregationStrategy.WEIGHTED_VOTE,
            iterations=200,
        )
    )

    # Display results
    print()
    print("=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print()

    # Print summary table
    print(f"{'Benchmark':<40} {'Evidence':<10} {'Mean (ms)':<12} {'P95 (ms)':<12} {'Status':<10}")
    print("-" * 84)

    all_passed = True
    for b in benchmarks:
        status = "PASS" if b["mean_ms"] < 10.0 else "FAIL"
        if status == "FAIL":
            all_passed = False
        status_marker = "[PASS]" if status == "PASS" else "[FAIL]"

        print(
            f"{b['name']:<40} {b['evidence_count']:<10} "
            f"{b['mean_ms']:>10.3f}  {b['p95_ms']:>10.3f}  "
            f"{status_marker}"
        )

    print("-" * 84)
    print()

    # Print detailed statistics
    print("DETAILED STATISTICS")
    print("-" * 80)
    for b in benchmarks:
        print()
        print(f"Benchmark: {b['name']}")
        print(f"  Strategy:      {b['strategy']}")
        print(f"  Evidence:      {b['evidence_count']} items")
        print(f"  Iterations:    {b['iterations']}")
        print(f"  Verdict:       {b['verdict']}")
        print(f"  Confidence:    {b['confidence']:.3f}")
        print(f"  Mean:          {b['mean_ms']:.3f} ms")
        print(f"  Median:        {b['median_ms']:.3f} ms")
        print(f"  Std Dev:       {b['stddev_ms']:.3f} ms")
        print(f"  Min:           {b['min_ms']:.3f} ms")
        print(f"  Max:           {b['max_ms']:.3f} ms")
        print(f"  P95:           {b['p95_ms']:.3f} ms")
        print(f"  P99:           {b['p99_ms']:.3f} ms")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    avg_mean = statistics.mean([b["mean_ms"] for b in benchmarks])
    avg_p95 = statistics.mean([b["p95_ms"] for b in benchmarks])

    print(f"Total benchmarks run:       {len(benchmarks)}")
    print(f"Average mean time:          {avg_mean:.3f} ms")
    print(f"Average P95 time:           {avg_p95:.3f} ms")
    print(f"Target performance (<10ms): {'ACHIEVED' if all_passed else 'NOT MET'}")

    if all_passed:
        print()
        print("SUCCESS: All benchmarks passed! Aggregation service meets performance target.")
    else:
        print()
        print("WARNING: Some benchmarks exceeded 10ms threshold.")
        print("         This may be acceptable for very large datasets (>100 items).")

    print()
    print("=" * 80)


if __name__ == "__main__":
    run_benchmarks()
