#!/usr/bin/env python3
"""Comprehensive benchmark for NLI service.

This script measures NLI performance across various dimensions:
- Single pair inference latency
- Batch throughput with various batch sizes
- Different text lengths
- Memory usage
- Label distribution

Performance Targets:
    - Throughput: >2 pairs/second on CPU
    - Memory: <2GB total usage
"""

import argparse
import gc
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from truthgraph.services.ml import get_nli_service


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics."""
    if not PSUTIL_AVAILABLE:
        return {}

    process = psutil.Process()
    mem_info = process.memory_info()
    return {"rss_mb": mem_info.rss / (1024 * 1024), "vms_mb": mem_info.vms / (1024 * 1024)}


def generate_test_pairs(num_pairs: int, length_category: str = "medium") -> list[tuple[str, str]]:
    """Generate test claim-evidence pairs.

    Args:
        num_pairs: Number of pairs to generate
        length_category: 'short', 'medium', or 'long'

    Returns:
        List of (premise, hypothesis) tuples
    """
    templates = {
        "short": [
            ("Paris is the capital of France.", "Paris is in France."),
            ("Water boils at 100°C.", "Water boiling point is 100 degrees."),
            ("The Earth orbits the Sun.", "Earth goes around Sun."),
        ],
        "medium": [
            (
                "The capital of France is Paris, a major metropolitan area.",
                "Paris is located in France.",
            ),
            (
                "Research shows that renewable energy has increased by 35% in recent years.",
                "Renewable energy has declined significantly.",
            ),
            (
                "The Internet was invented in 1983 and revolutionized communication.",
                "The Internet was created in the 1980s.",
            ),
        ],
        "long": [
            (
                "Climate change research from the Intergovernmental Panel on Climate Change "
                "indicates that global temperatures have risen approximately 1.1 degrees Celsius "
                "since pre-industrial times, primarily due to human activities including fossil "
                "fuel combustion and deforestation.",
                "Global temperatures have increased due to human activities.",
            ),
            (
                "Advances in artificial intelligence and machine learning technologies have "
                "enabled significant improvements in natural language processing, computer vision, "
                "and predictive analytics across various industries including healthcare, finance, "
                "and transportation.",
                "AI has made progress in multiple application domains.",
            ),
            (
                "The COVID-19 pandemic, caused by the SARS-CoV-2 virus, resulted in widespread "
                "global disruptions to healthcare systems, economies, and daily life, prompting "
                "unprecedented international collaboration on vaccine development and public health "
                "measures.",
                "COVID-19 led to global disruptions and health responses.",
            ),
        ],
    }

    template_set = templates.get(length_category, templates["medium"])
    pairs = []

    for i in range(num_pairs):
        pairs.append(template_set[i % len(template_set)])

    return pairs


def benchmark_single_inference(service, iterations: int = 50) -> dict[str, Any]:
    """Benchmark single pair inference.

    Args:
        service: NLI service instance
        iterations: Number of iterations

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Single Pair Inference")
    print("=" * 80)

    test_pairs = generate_test_pairs(iterations, "medium")

    # Warm up
    print("Warming up...")
    for _ in range(5):
        service.verify_single(test_pairs[0][0], test_pairs[0][1])

    # Benchmark
    print(f"Running {iterations} iterations...")
    latencies = []
    labels = []

    for i, (premise, hypothesis) in enumerate(test_pairs):
        start_time = time.perf_counter()
        result = service.verify_single(premise, hypothesis)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)
        labels.append(result.label.value)

        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{iterations} iterations")

    # Calculate statistics
    latencies_sorted = sorted(latencies)
    avg_latency = sum(latencies) / len(latencies)

    # Label distribution
    label_counts = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1

    results = {
        "iterations": iterations,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "p50_latency_ms": latencies_sorted[len(latencies) // 2],
        "p95_latency_ms": latencies_sorted[int(len(latencies) * 0.95)],
        "p99_latency_ms": latencies_sorted[int(len(latencies) * 0.99)],
        "throughput_pairs_per_sec": 1000.0 / avg_latency,
        "label_distribution": label_counts,
    }

    # Print results
    print("\nResults:")
    print(f"  Iterations:         {results['iterations']}")
    print(f"  Average latency:    {results['avg_latency_ms']:.1f} ms")
    print(f"  Min latency:        {results['min_latency_ms']:.1f} ms")
    print(f"  Max latency:        {results['max_latency_ms']:.1f} ms")
    print(f"  P50 latency:        {results['p50_latency_ms']:.1f} ms")
    print(f"  P95 latency:        {results['p95_latency_ms']:.1f} ms")
    print(f"  P99 latency:        {results['p99_latency_ms']:.1f} ms")
    print(f"  Throughput:         {results['throughput_pairs_per_sec']:.2f} pairs/sec")
    print(f"  Label distribution: {label_counts}")

    # Check target (>2 pairs/sec means <500ms per pair)
    target = 500.0  # ms
    passed = avg_latency < target
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: <{target} ms per pair - {status}")

    results["target_ms"] = target
    results["passed"] = passed

    return results


def benchmark_batch_sizes(
    service, num_pairs: int = 100, batch_sizes: list[int] | None = None
) -> dict[str, Any]:
    """Benchmark various batch sizes.

    Args:
        service: NLI service instance
        num_pairs: Number of pairs to process
        batch_sizes: List of batch sizes to test

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Batch Size Optimization")
    print("=" * 80)

    if batch_sizes is None:
        batch_sizes = [1, 2, 4, 8, 16]

    test_pairs = generate_test_pairs(num_pairs, "medium")
    print(f"Generated {len(test_pairs)} test pairs")

    results = {"num_pairs": num_pairs, "batch_results": []}

    for batch_size in batch_sizes:
        print(f"\nTesting batch_size={batch_size}...")

        # Warm up
        warmup_pairs = test_pairs[: min(10, len(test_pairs))]
        service.verify_batch(warmup_pairs, batch_size=batch_size)
        gc.collect()

        # Benchmark
        start_time = time.perf_counter()
        batch_results = service.verify_batch(test_pairs, batch_size=batch_size)
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        throughput = num_pairs / elapsed
        avg_latency_ms = (elapsed / num_pairs) * 1000

        batch_result = {
            "batch_size": batch_size,
            "elapsed_time_s": elapsed,
            "throughput_pairs_per_sec": throughput,
            "avg_latency_ms": avg_latency_ms,
            "num_results": len(batch_results),
        }

        # Label distribution
        label_counts = {}
        for result in batch_results:
            label = result.label.value
            label_counts[label] = label_counts.get(label, 0) + 1
        batch_result["label_distribution"] = label_counts

        # Memory
        memory = get_memory_usage()
        if "rss_mb" in memory:
            batch_result["memory_rss_mb"] = memory["rss_mb"]

        results["batch_results"].append(batch_result)

        print(f"  Elapsed:     {elapsed:.2f} s")
        print(f"  Throughput:  {throughput:.2f} pairs/sec")
        print(f"  Avg latency: {avg_latency_ms:.1f} ms")
        if "rss_mb" in memory:
            print(f"  Memory RSS:  {memory['rss_mb']:.1f} MB")

    # Find best
    best = max(results["batch_results"], key=lambda x: x["throughput_pairs_per_sec"])
    results["best_batch_size"] = best["batch_size"]
    results["best_throughput"] = best["throughput_pairs_per_sec"]

    print("\nBest performance:")
    print(f"  Batch size:  {best['batch_size']}")
    print(f"  Throughput:  {best['throughput_pairs_per_sec']:.2f} pairs/sec")

    # Check target
    target = 2.0  # pairs/sec
    passed = best["throughput_pairs_per_sec"] > target
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: >{target} pairs/sec - {status}")

    results["target_throughput"] = target
    results["passed"] = passed

    return results


def benchmark_text_lengths(service, num_pairs: int = 50) -> dict[str, Any]:
    """Benchmark different text lengths.

    Args:
        service: NLI service instance
        num_pairs: Number of pairs per category

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Text Length Impact")
    print("=" * 80)

    categories = ["short", "medium", "long"]
    results = {"num_pairs_per_category": num_pairs, "length_results": []}

    for category in categories:
        print(f"\nTesting {category} texts...")
        pairs = generate_test_pairs(num_pairs, category)

        # Sample for display
        premise, hypothesis = pairs[0]
        print(f"  Sample premise length:    {len(premise)} chars")
        print(f"  Sample hypothesis length: {len(hypothesis)} chars")

        # Benchmark
        start_time = time.perf_counter()
        batch_results = service.verify_batch(pairs)
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        throughput = num_pairs / elapsed

        length_result = {
            "category": category,
            "sample_premise_chars": len(premise),
            "sample_hypothesis_chars": len(hypothesis),
            "elapsed_time_s": elapsed,
            "throughput_pairs_per_sec": throughput,
        }

        results["length_results"].append(length_result)

        print(f"  Elapsed:     {elapsed:.2f} s")
        print(f"  Throughput:  {throughput:.2f} pairs/sec")

    return results


def benchmark_memory(service) -> dict[str, Any]:
    """Benchmark memory usage.

    Args:
        service: NLI service instance

    Returns:
        Dictionary with memory statistics
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Memory Usage")
    print("=" * 80)

    if not PSUTIL_AVAILABLE:
        print("psutil not available, skipping memory benchmarks")
        return {"skipped": True}

    # Baseline
    gc.collect()
    baseline = get_memory_usage()
    print(f"\nBaseline RSS: {baseline.get('rss_mb', 0):.1f} MB")

    # After model load
    test_pairs = generate_test_pairs(1, "medium")
    service.verify_single(test_pairs[0][0], test_pairs[0][1])
    loaded = get_memory_usage()
    print(f"Loaded RSS:   {loaded.get('rss_mb', 0):.1f} MB")

    model_memory = loaded.get("rss_mb", 0) - baseline.get("rss_mb", 0)
    print(f"Model memory: {model_memory:.1f} MB")

    # Large batch
    print("\nProcessing large batch (100 pairs)...")
    large_pairs = generate_test_pairs(100, "medium")
    service.verify_batch(large_pairs)

    peak = get_memory_usage()
    print(f"Peak RSS:     {peak.get('rss_mb', 0):.1f} MB")

    # Check target
    target_mb = 2048
    passed = peak.get("rss_mb", 0) < target_mb
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: <{target_mb} MB - {status}")

    return {
        "baseline_mb": baseline.get("rss_mb", 0),
        "loaded_mb": loaded.get("rss_mb", 0),
        "peak_mb": peak.get("rss_mb", 0),
        "model_memory_mb": model_memory,
        "target_mb": target_mb,
        "passed": passed,
    }


def save_results(results: dict[str, Any], output_path: Path) -> None:
    """Save results to JSON file.

    Args:
        results: Results dictionary
        output_path: Path to save results
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def main() -> int:
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(
        description="Comprehensive NLI service benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--num-pairs", type=int, default=100, help="Number of pairs for batch benchmarks"
    )
    parser.add_argument(
        "--batch-sizes", type=str, help="Comma-separated batch sizes (e.g., '2,4,8,16')"
    )
    parser.add_argument(
        "--iterations", type=int, default=50, help="Iterations for single pair benchmark"
    )
    parser.add_argument("--skip-single", action="store_true", help="Skip single pair benchmark")
    parser.add_argument("--skip-batch", action="store_true", help="Skip batch benchmark")
    parser.add_argument("--skip-lengths", action="store_true", help="Skip text length benchmark")
    parser.add_argument("--skip-memory", action="store_true", help="Skip memory benchmark")
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (default: results/nli_TIMESTAMP.json)",
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = None
    if args.batch_sizes:
        batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Print system info
    print("=" * 80)
    print("NLI SERVICE COMPREHENSIVE BENCHMARK")
    print("=" * 80)
    print(f"\nPython version:     {sys.version.split()[0]}")
    print(f"psutil available:   {PSUTIL_AVAILABLE}")

    # Initialize service
    print("\nInitializing NLI service...")
    service = get_nli_service()
    info = service.get_model_info()
    print(f"Model:              {info['model_name']}")
    print(f"Device:             {info['device']}")
    print(f"Batch size:         {info.get('batch_size', 'N/A')}")

    # Run benchmarks
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python_version": sys.version.split()[0],
            "model": info["model_name"],
            "device": info["device"],
        },
        "benchmarks": {},
    }

    if not args.skip_single:
        all_results["benchmarks"]["single_pair"] = benchmark_single_inference(
            service, args.iterations
        )

    if not args.skip_batch:
        all_results["benchmarks"]["batch_sizes"] = benchmark_batch_sizes(
            service, args.num_pairs, batch_sizes
        )

    if not args.skip_lengths:
        all_results["benchmarks"]["text_lengths"] = benchmark_text_lengths(service)

    if not args.skip_memory:
        all_results["benchmarks"]["memory"] = benchmark_memory(service)

    # Summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    all_passed = True

    if "single_pair" in all_results["benchmarks"]:
        sp = all_results["benchmarks"]["single_pair"]
        passed = sp.get("passed", False)
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(
            f"\nSingle pair latency:    {sp['avg_latency_ms']:.1f} ms "
            f"({sp['throughput_pairs_per_sec']:.2f} pairs/sec) - {status}"
        )

    if "batch_sizes" in all_results["benchmarks"]:
        bs = all_results["benchmarks"]["batch_sizes"]
        passed = bs.get("passed", False)
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(
            f"Batch throughput:       {bs['best_throughput']:.2f} pairs/sec "
            f"(batch_size={bs['best_batch_size']}) - {status}"
        )

    if "memory" in all_results["benchmarks"]:
        mem = all_results["benchmarks"]["memory"]
        if not mem.get("skipped", False):
            passed = mem.get("passed", False)
            all_passed = all_passed and passed
            status = "PASS" if passed else "FAIL"
            print(f"Peak memory usage:      {mem['peak_mb']:.1f} MB - {status}")

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_path = Path(__file__).parent / "results" / f"nli_{timestamp}.json"

    save_results(all_results, output_path)

    print("\n" + "=" * 80)
    final_status = "ALL BENCHMARKS PASSED" if all_passed else "SOME BENCHMARKS FAILED"
    print(final_status)
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
