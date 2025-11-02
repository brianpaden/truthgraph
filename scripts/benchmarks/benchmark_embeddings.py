#!/usr/bin/env python3
"""Comprehensive benchmark for EmbeddingService.

This script measures embedding performance across various dimensions:
- Single text latency
- Batch throughput with various batch sizes
- Different text lengths
- Memory usage
- Reproducibility

Performance Targets:
    - Throughput: >500 texts/second on CPU
    - Single text latency: <100ms
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

import torch

from truthgraph.services.ml.embedding_service import EmbeddingService


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics."""
    memory_stats = {}

    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        mem_info = process.memory_info()
        memory_stats["rss"] = mem_info.rss
        memory_stats["vms"] = mem_info.vms
        memory_stats["rss_mb"] = mem_info.rss / (1024 * 1024)

    if torch.cuda.is_available():
        memory_stats["gpu_allocated"] = torch.cuda.memory_allocated()
        memory_stats["gpu_reserved"] = torch.cuda.memory_reserved()
        memory_stats["gpu_allocated_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)

    return memory_stats


def generate_test_texts(num_texts: int, length_category: str = "medium") -> list[str]:
    """Generate test texts of various lengths.

    Args:
        num_texts: Number of texts to generate
        length_category: 'short', 'medium', or 'long'

    Returns:
        List of test texts
    """
    templates = {
        "short": "Test sentence {i}.",
        "medium": "This is test sentence number {i} for benchmarking embedding performance with typical length.",
        "long": (
            "This is a longer test sentence number {i} designed for benchmarking embedding "
            "performance with extended text lengths. It contains multiple clauses and provides "
            "a more realistic representation of actual input text that the system might "
            "encounter in production environments when processing various types of claims "
            "and evidence from diverse sources."
        ),
    }

    template = templates.get(length_category, templates["medium"])
    return [template.format(i=i) for i in range(num_texts)]


def benchmark_single_text(service: EmbeddingService, iterations: int = 100) -> dict[str, Any]:
    """Benchmark single text embedding latency.

    Args:
        service: EmbeddingService instance
        iterations: Number of iterations

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Single Text Latency")
    print("=" * 80)

    test_text = "This is a test sentence for benchmarking single text embedding performance"

    # Warm up
    print("Warming up...")
    for _ in range(10):
        service.embed_text(test_text)

    # Benchmark
    print(f"Running {iterations} iterations...")
    latencies = []

    for i in range(iterations):
        start_time = time.perf_counter()
        embedding = service.embed_text(test_text)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

        if (i + 1) % 20 == 0:
            print(f"  Completed {i + 1}/{iterations} iterations")

    # Calculate statistics
    latencies_sorted = sorted(latencies)
    results = {
        "iterations": iterations,
        "avg_latency_ms": sum(latencies) / len(latencies),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "p50_latency_ms": latencies_sorted[len(latencies) // 2],
        "p95_latency_ms": latencies_sorted[int(len(latencies) * 0.95)],
        "p99_latency_ms": latencies_sorted[int(len(latencies) * 0.99)],
        "embedding_dimension": len(embedding),
    }

    # Print results
    print("\nResults:")
    print(f"  Iterations:         {results['iterations']}")
    print(f"  Average latency:    {results['avg_latency_ms']:.2f} ms")
    print(f"  Min latency:        {results['min_latency_ms']:.2f} ms")
    print(f"  Max latency:        {results['max_latency_ms']:.2f} ms")
    print(f"  P50 latency:        {results['p50_latency_ms']:.2f} ms")
    print(f"  P95 latency:        {results['p95_latency_ms']:.2f} ms")
    print(f"  P99 latency:        {results['p99_latency_ms']:.2f} ms")
    print(f"  Embedding dim:      {results['embedding_dimension']}")

    # Check target
    target = 100.0
    passed = results["avg_latency_ms"] < target
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: <{target} ms - {status}")

    results["target_ms"] = target
    results["passed"] = passed

    return results


def benchmark_batch_sizes(
    service: EmbeddingService,
    num_texts: int = 1000,
    batch_sizes: list[int] | None = None,
) -> dict[str, Any]:
    """Benchmark various batch sizes.

    Args:
        service: EmbeddingService instance
        num_texts: Number of texts to process
        batch_sizes: List of batch sizes to test

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Batch Size Optimization")
    print("=" * 80)

    if batch_sizes is None:
        device = service.get_device()
        if device == "cuda":
            batch_sizes = [16, 32, 64, 128, 256]
        elif device == "mps":
            batch_sizes = [16, 32, 64, 128]
        else:
            batch_sizes = [8, 16, 32, 64]

    texts = generate_test_texts(num_texts, "medium")
    print(f"Generated {len(texts)} test texts")

    results = {"num_texts": num_texts, "device": service.get_device(), "batch_results": []}

    for batch_size in batch_sizes:
        print(f"\nTesting batch_size={batch_size}...")

        # Warm up
        service.embed_batch(texts[:100], batch_size=batch_size)
        gc.collect()

        # Benchmark
        start_time = time.perf_counter()
        embeddings = service.embed_batch(texts, batch_size=batch_size)
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        throughput = num_texts / elapsed

        batch_result = {
            "batch_size": batch_size,
            "elapsed_time_s": elapsed,
            "throughput_texts_per_sec": throughput,
            "num_embeddings": len(embeddings),
        }

        # Memory stats
        memory = get_memory_usage()
        if "rss_mb" in memory:
            batch_result["memory_rss_mb"] = memory["rss_mb"]
        if "gpu_allocated_mb" in memory:
            batch_result["memory_gpu_mb"] = memory["gpu_allocated_mb"]

        results["batch_results"].append(batch_result)

        print(f"  Elapsed:     {elapsed:.2f} s")
        print(f"  Throughput:  {throughput:.1f} texts/sec")
        if "rss_mb" in memory:
            print(f"  Memory RSS:  {memory['rss_mb']:.1f} MB")

    # Find best
    best = max(results["batch_results"], key=lambda x: x["throughput_texts_per_sec"])
    results["best_batch_size"] = best["batch_size"]
    results["best_throughput"] = best["throughput_texts_per_sec"]

    print("\nBest performance:")
    print(f"  Batch size:  {best['batch_size']}")
    print(f"  Throughput:  {best['throughput_texts_per_sec']:.1f} texts/sec")

    # Check target
    device = service.get_device()
    target = 2000 if device == "cuda" else 1000 if device == "mps" else 500
    passed = best["throughput_texts_per_sec"] > target
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: >{target} texts/sec on {device} - {status}")

    results["target_throughput"] = target
    results["passed"] = passed

    return results


def benchmark_text_lengths(service: EmbeddingService, num_texts: int = 500) -> dict[str, Any]:
    """Benchmark different text lengths.

    Args:
        service: EmbeddingService instance
        num_texts: Number of texts per category

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Text Length Impact")
    print("=" * 80)

    categories = ["short", "medium", "long"]
    results = {"num_texts_per_category": num_texts, "length_results": []}

    for category in categories:
        print(f"\nTesting {category} texts...")
        texts = generate_test_texts(num_texts, category)

        # Sample for display
        sample_text = texts[0]
        print(f"  Sample length: {len(sample_text)} chars")
        print(f"  Sample: {sample_text[:80]}...")

        # Benchmark
        start_time = time.perf_counter()
        embeddings = service.embed_batch(texts)
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        throughput = num_texts / elapsed

        length_result = {
            "category": category,
            "sample_length_chars": len(sample_text),
            "elapsed_time_s": elapsed,
            "throughput_texts_per_sec": throughput,
        }

        results["length_results"].append(length_result)

        print(f"  Elapsed:     {elapsed:.2f} s")
        print(f"  Throughput:  {throughput:.1f} texts/sec")

    return results


def benchmark_memory(service: EmbeddingService) -> dict[str, Any]:
    """Benchmark memory usage.

    Args:
        service: EmbeddingService instance

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
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    baseline = get_memory_usage()
    print(f"\nBaseline RSS: {baseline.get('rss_mb', 0):.1f} MB")

    # After model load
    service.embed_text("Load model")
    loaded = get_memory_usage()
    print(f"Loaded RSS:   {loaded.get('rss_mb', 0):.1f} MB")

    model_memory = loaded.get("rss_mb", 0) - baseline.get("rss_mb", 0)
    print(f"Model memory: {model_memory:.1f} MB")

    # Large batch
    print("\nProcessing large batch (5000 texts)...")
    large_texts = generate_test_texts(5000, "medium")
    service.embed_batch(large_texts)

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
        description="Comprehensive EmbeddingService benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--num-texts", type=int, default=1000, help="Number of texts for batch benchmarks"
    )
    parser.add_argument(
        "--batch-sizes", type=str, help="Comma-separated batch sizes (e.g., '16,32,64')"
    )
    parser.add_argument(
        "--iterations", type=int, default=100, help="Iterations for single text benchmark"
    )
    parser.add_argument("--skip-single", action="store_true", help="Skip single text benchmark")
    parser.add_argument("--skip-batch", action="store_true", help="Skip batch benchmark")
    parser.add_argument("--skip-lengths", action="store_true", help="Skip text length benchmark")
    parser.add_argument("--skip-memory", action="store_true", help="Skip memory benchmark")
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (default: results/embeddings_TIMESTAMP.json)",
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = None
    if args.batch_sizes:
        batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Print system info
    print("=" * 80)
    print("EMBEDDING SERVICE COMPREHENSIVE BENCHMARK")
    print("=" * 80)
    print(f"\nPython version:     {sys.version.split()[0]}")
    print(f"PyTorch version:    {torch.__version__}")
    print(f"CUDA available:     {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device:        {torch.cuda.get_device_name(0)}")
    print(f"psutil available:   {PSUTIL_AVAILABLE}")

    # Initialize service
    print("\nInitializing EmbeddingService...")
    service = EmbeddingService.get_instance()
    print(f"Device:             {service.get_device()}")
    print(f"Model:              {service.MODEL_NAME}")
    print(f"Embedding dim:      {service.get_embedding_dimension()}")

    # Run benchmarks
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python_version": sys.version.split()[0],
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": service.get_device(),
            "model": service.MODEL_NAME,
            "embedding_dimension": service.get_embedding_dimension(),
        },
        "benchmarks": {},
    }

    if not args.skip_single:
        all_results["benchmarks"]["single_text"] = benchmark_single_text(service, args.iterations)

    if not args.skip_batch:
        all_results["benchmarks"]["batch_sizes"] = benchmark_batch_sizes(
            service, args.num_texts, batch_sizes
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

    if "single_text" in all_results["benchmarks"]:
        st = all_results["benchmarks"]["single_text"]
        passed = st.get("passed", False)
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"\nSingle text latency:    {st['avg_latency_ms']:.2f} ms - {status}")

    if "batch_sizes" in all_results["benchmarks"]:
        bs = all_results["benchmarks"]["batch_sizes"]
        passed = bs.get("passed", False)
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(
            f"Batch throughput:       {bs['best_throughput']:.1f} texts/sec "
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
        output_path = Path(__file__).parent / "results" / f"embeddings_{timestamp}.json"

    save_results(all_results, output_path)

    print("\n" + "=" * 80)
    final_status = "ALL BENCHMARKS PASSED" if all_passed else "SOME BENCHMARKS FAILED"
    print(final_status)
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
