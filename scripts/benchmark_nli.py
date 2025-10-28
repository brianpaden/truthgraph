"""Performance benchmark script for NLI service.

This script measures throughput, latency, and memory usage of the NLI service
to validate performance targets.

Usage:
    python scripts/benchmark_nli.py
    python scripts/benchmark_nli.py --pairs 100 --batch-size 16
    python scripts/benchmark_nli.py --iterations 5 --device cpu
"""

import argparse
import gc
import sys
import time
from pathlib import Path

import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from truthgraph.services.ml import get_nli_service  # noqa: E402

logger = structlog.get_logger(__name__)


def measure_memory() -> float:
    """Measure current memory usage in MB.

    Returns:
        Memory usage in MB
    """
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        logger.warning("psutil not installed, skipping memory measurement")
        return 0.0


def generate_test_pairs(n: int) -> list[tuple[str, str]]:
    """Generate test claim-evidence pairs.

    Args:
        n: Number of pairs to generate

    Returns:
        List of (premise, hypothesis) tuples
    """
    pairs = []
    templates = [
        (
            "The capital of {country} is {city}, a major metropolitan area.",
            "{city} is located in {country}.",
        ),
        (
            "Research shows that {topic} has increased by {percent}% in recent years.",
            "{topic} has declined significantly.",
        ),
        (
            "The {item} was invented in {year} and revolutionized {field}.",
            "The {item} was created in the {year}s.",
        ),
    ]

    countries_cities = [
        ("France", "Paris"),
        ("Japan", "Tokyo"),
        ("Brazil", "Brasilia"),
        ("Germany", "Berlin"),
    ]

    topics_percents = [
        ("renewable energy adoption", "35"),
        ("electric vehicle sales", "42"),
        ("remote work", "28"),
    ]

    items_years_fields = [
        ("internet", "1983", "communication"),
        ("smartphone", "2007", "mobile technology"),
        ("laser", "1960", "optics"),
    ]

    for i in range(n):
        template_idx = i % len(templates)

        if template_idx == 0:
            country, city = countries_cities[i % len(countries_cities)]
            premise = templates[0][0].format(country=country, city=city)
            hypothesis = templates[0][1].format(city=city, country=country)
        elif template_idx == 1:
            topic, percent = topics_percents[i % len(topics_percents)]
            premise = templates[1][0].format(topic=topic, percent=percent)
            hypothesis = templates[1][1].format(topic=topic)
        else:
            item, year, field = items_years_fields[i % len(items_years_fields)]
            premise = templates[2][0].format(item=item, year=year, field=field)
            hypothesis = templates[2][1].format(item=item, year=year)

        pairs.append((premise, hypothesis))

    return pairs


def benchmark_single_inference(
    service, pairs: list[tuple[str, str]], iterations: int
) -> dict[str, float]:
    """Benchmark single pair inference.

    Args:
        service: NLI service instance
        pairs: Test pairs to use
        iterations: Number of iterations

    Returns:
        Dictionary with benchmark results
    """
    logger.info("benchmarking_single_inference", iterations=iterations)

    latencies = []

    for i in range(iterations):
        premise, hypothesis = pairs[i % len(pairs)]

        start_time = time.time()
        result = service.verify_single(premise, hypothesis)
        elapsed = time.time() - start_time

        latencies.append(elapsed)

        if i == 0:
            logger.info(
                "first_result",
                label=result.label.value,
                confidence=f"{result.confidence:.3f}",
                latency_ms=f"{elapsed * 1000:.1f}",
            )

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    return {
        "avg_latency_ms": avg_latency * 1000,
        "min_latency_ms": min_latency * 1000,
        "max_latency_ms": max_latency * 1000,
        "throughput_pairs_per_sec": 1.0 / avg_latency,
    }


def benchmark_batch_inference(
    service, pairs: list[tuple[str, str]], batch_size: int, iterations: int
) -> dict[str, float]:
    """Benchmark batch inference.

    Args:
        service: NLI service instance
        pairs: Test pairs to use
        batch_size: Batch size for inference
        iterations: Number of iterations

    Returns:
        Dictionary with benchmark results
    """
    logger.info(
        "benchmarking_batch_inference",
        batch_size=batch_size,
        iterations=iterations,
    )

    throughputs = []

    for i in range(iterations):
        # Use different subset each iteration
        start_idx = (i * batch_size) % len(pairs)
        batch_pairs = pairs[start_idx : start_idx + batch_size]

        if len(batch_pairs) < batch_size:
            batch_pairs = pairs[:batch_size]

        start_time = time.time()
        results = service.verify_batch(batch_pairs, batch_size=batch_size)
        elapsed = time.time() - start_time

        throughput = len(results) / elapsed
        throughputs.append(throughput)

        if i == 0:
            label_counts = {}
            for result in results:
                label = result.label.value
                label_counts[label] = label_counts.get(label, 0) + 1

            logger.info(
                "first_batch_result",
                batch_size=len(results),
                latency_ms=f"{elapsed * 1000:.1f}",
                throughput=f"{throughput:.2f}",
                label_distribution=label_counts,
            )

    avg_throughput = sum(throughputs) / len(throughputs)
    min_throughput = min(throughputs)
    max_throughput = max(throughputs)

    return {
        "avg_throughput_pairs_per_sec": avg_throughput,
        "min_throughput_pairs_per_sec": min_throughput,
        "max_throughput_pairs_per_sec": max_throughput,
        "avg_latency_per_pair_ms": (1000.0 / avg_throughput),
    }


def benchmark_memory(service, pairs: list[tuple[str, str]], batch_size: int) -> dict[str, float]:
    """Benchmark memory usage.

    Args:
        service: NLI service instance
        pairs: Test pairs to use
        batch_size: Batch size for inference

    Returns:
        Dictionary with memory measurements
    """
    logger.info("benchmarking_memory")

    # Measure baseline
    gc.collect()
    baseline_memory = measure_memory()

    # Load model
    service.verify_single(pairs[0][0], pairs[0][1])
    gc.collect()
    loaded_memory = measure_memory()

    # Process batch
    service.verify_batch(pairs[:batch_size], batch_size=batch_size)
    gc.collect()
    after_batch_memory = measure_memory()

    # Process large batch
    large_batch_size = min(len(pairs), 50)
    service.verify_batch(pairs[:large_batch_size], batch_size=batch_size)
    gc.collect()
    after_large_batch_memory = measure_memory()

    return {
        "baseline_mb": baseline_memory,
        "model_loaded_mb": loaded_memory,
        "after_batch_mb": after_batch_memory,
        "after_large_batch_mb": after_large_batch_memory,
        "model_size_mb": loaded_memory - baseline_memory,
        "peak_usage_mb": after_large_batch_memory,
    }


def run_benchmark(
    num_pairs: int,
    batch_size: int,
    iterations: int,
    device: str | None = None,
) -> None:
    """Run complete benchmark suite.

    Args:
        num_pairs: Number of test pairs to generate
        batch_size: Batch size for batch inference
        iterations: Number of iterations for each benchmark
        device: Force specific device (cpu/cuda/mps) or None for auto-detect
    """
    logger.info(
        "starting_nli_benchmark",
        num_pairs=num_pairs,
        batch_size=batch_size,
        iterations=iterations,
        device=device or "auto",
    )

    # Generate test pairs
    pairs = generate_test_pairs(num_pairs)
    logger.info("test_pairs_generated", count=len(pairs))

    # Get NLI service
    service = get_nli_service()

    # Override device if specified
    if device:
        service.device = device

    # Get model info
    info = service.get_model_info()
    logger.info("nli_service_info", **info)

    # Warm up
    logger.info("warming_up_model")
    service.verify_single(pairs[0][0], pairs[0][1])

    # Benchmark single inference
    single_results = benchmark_single_inference(service, pairs, min(iterations, 10))
    logger.info("single_inference_results", **single_results)

    # Benchmark batch inference
    batch_results = benchmark_batch_inference(service, pairs, batch_size, iterations)
    logger.info("batch_inference_results", **batch_results)

    # Benchmark memory
    memory_results = benchmark_memory(service, pairs, batch_size)
    logger.info("memory_results", **memory_results)

    # Print summary
    print("\n" + "=" * 80)
    print("NLI SERVICE PERFORMANCE BENCHMARK RESULTS")
    print("=" * 80)

    print(f"\nModel: {info['model_name']}")
    print(f"Device: {info['device']}")
    print(f"Test Pairs: {num_pairs}")
    print(f"Batch Size: {batch_size}")
    print(f"Iterations: {iterations}")

    print("\n--- SINGLE INFERENCE ---")
    print(f"Average Latency: {single_results['avg_latency_ms']:.1f} ms")
    print(f"Min Latency: {single_results['min_latency_ms']:.1f} ms")
    print(f"Max Latency: {single_results['max_latency_ms']:.1f} ms")
    print(f"Throughput: {single_results['throughput_pairs_per_sec']:.2f} pairs/sec")

    print("\n--- BATCH INFERENCE ---")
    print(f"Average Throughput: {batch_results['avg_throughput_pairs_per_sec']:.2f} pairs/sec")
    print(f"Min Throughput: {batch_results['min_throughput_pairs_per_sec']:.2f} pairs/sec")
    print(f"Max Throughput: {batch_results['max_throughput_pairs_per_sec']:.2f} pairs/sec")
    print(f"Avg Latency per Pair: {batch_results['avg_latency_per_pair_ms']:.1f} ms")

    print("\n--- MEMORY USAGE ---")
    print(f"Baseline: {memory_results['baseline_mb']:.1f} MB")
    print(f"Model Loaded: {memory_results['model_loaded_mb']:.1f} MB")
    print(f"Model Size: {memory_results['model_size_mb']:.1f} MB")
    print(f"Peak Usage: {memory_results['peak_usage_mb']:.1f} MB")

    print("\n--- TARGET VALIDATION ---")
    target_throughput = 2.0
    target_memory = 2000.0  # 2GB in MB

    throughput_ok = batch_results["avg_throughput_pairs_per_sec"] >= target_throughput
    memory_ok = memory_results["peak_usage_mb"] <= target_memory

    print(
        f"Throughput Target (>2 pairs/sec): {'PASS' if throughput_ok else 'FAIL'} "
        f"({batch_results['avg_throughput_pairs_per_sec']:.2f} pairs/sec)"
    )
    print(
        f"Memory Target (<2GB): {'PASS' if memory_ok else 'FAIL'} ({memory_results['peak_usage_mb']:.0f} MB)"
    )

    print("\n" + "=" * 80)

    if throughput_ok and memory_ok:
        print("ALL TARGETS MET!")
    else:
        print("SOME TARGETS NOT MET - Review configuration and hardware")

    print("=" * 80 + "\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark NLI service performance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--pairs",
        type=int,
        default=50,
        help="Number of test pairs to generate",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for batch inference",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations for benchmarks",
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda", "mps"],
        default=None,
        help="Force specific device (default: auto-detect)",
    )

    args = parser.parse_args()

    run_benchmark(
        num_pairs=args.pairs,
        batch_size=args.batch_size,
        iterations=args.iterations,
        device=args.device,
    )


if __name__ == "__main__":
    main()
