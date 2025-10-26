#!/usr/bin/env python3
"""Performance benchmark script for EmbeddingService.

This script measures the performance of the embedding service under various
conditions and reports detailed metrics.

Usage:
    python scripts/benchmark_embeddings.py
    python scripts/benchmark_embeddings.py --batch-sizes 16,32,64,128
    python scripts/benchmark_embeddings.py --num-texts 5000
    python scripts/benchmark_embeddings.py --verbose

Performance Targets:
    - Throughput: >500 texts/second on CPU, >2000 on GPU
    - Memory: <2GB total usage
    - Latency: <100ms for single text
"""

import argparse
import gc
import sys
import time
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. Memory metrics will be limited.")

import torch

from truthgraph.services.ml.embedding_service import EmbeddingService


def format_bytes(bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics."""
    memory_stats = {}

    # Process memory
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        mem_info = process.memory_info()
        memory_stats["rss"] = mem_info.rss
        memory_stats["vms"] = mem_info.vms
        memory_stats["rss_formatted"] = format_bytes(mem_info.rss)
        memory_stats["vms_formatted"] = format_bytes(mem_info.vms)

    # GPU memory (if available)
    if torch.cuda.is_available():
        memory_stats["gpu_allocated"] = torch.cuda.memory_allocated()
        memory_stats["gpu_reserved"] = torch.cuda.memory_reserved()
        memory_stats["gpu_allocated_formatted"] = format_bytes(
            torch.cuda.memory_allocated()
        )
        memory_stats["gpu_reserved_formatted"] = format_bytes(torch.cuda.memory_reserved())

    return memory_stats


def benchmark_single_text(
    service: EmbeddingService,
    num_iterations: int = 100,
) -> dict[str, Any]:
    """Benchmark single text embedding performance.

    Args:
        service: EmbeddingService instance
        num_iterations: Number of iterations to run

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Single Text Embedding")
    print("=" * 80)

    test_text = "This is a test sentence for benchmarking single text embedding performance"

    # Warm up
    print("Warming up...")
    for _ in range(10):
        service.embed_text(test_text)

    # Run benchmark
    print(f"Running {num_iterations} iterations...")
    latencies = []

    for i in range(num_iterations):
        start_time = time.perf_counter()
        embedding = service.embed_text(test_text)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

        if (i + 1) % 20 == 0:
            print(f"  Completed {i + 1}/{num_iterations} iterations")

    # Calculate statistics
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    sorted_latencies = sorted(latencies)
    p50_latency = sorted_latencies[len(latencies) // 2]
    p95_latency = sorted_latencies[int(len(latencies) * 0.95)]
    p99_latency = sorted_latencies[int(len(latencies) * 0.99)]

    results = {
        "num_iterations": num_iterations,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "embedding_dimension": len(embedding),
    }

    # Print results
    print("\nResults:")
    print(f"  Iterations:         {num_iterations}")
    print(f"  Average latency:    {avg_latency:.2f} ms")
    print(f"  Min latency:        {min_latency:.2f} ms")
    print(f"  Max latency:        {max_latency:.2f} ms")
    print(f"  P50 latency:        {p50_latency:.2f} ms")
    print(f"  P95 latency:        {p95_latency:.2f} ms")
    print(f"  P99 latency:        {p99_latency:.2f} ms")
    print(f"  Embedding dim:      {len(embedding)}")

    # Check against target
    target_latency = 100.0  # ms
    status = "✓ PASS" if avg_latency < target_latency else "✗ FAIL"
    print(f"\nTarget: <{target_latency} ms average latency - {status}")

    return results


def benchmark_batch_processing(
    service: EmbeddingService,
    num_texts: int = 1000,
    batch_sizes: list[int] | None = None,
) -> dict[str, Any]:
    """Benchmark batch processing performance.

    Args:
        service: EmbeddingService instance
        num_texts: Number of texts to process
        batch_sizes: List of batch sizes to test

    Returns:
        Dictionary with benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Batch Processing")
    print("=" * 80)

    if batch_sizes is None:
        device = service.get_device()
        if device == "cuda":
            batch_sizes = [16, 32, 64, 128, 256]
        elif device == "mps":
            batch_sizes = [16, 32, 64, 128]
        else:  # CPU
            batch_sizes = [8, 16, 32, 64]

    # Generate test texts
    print(f"Generating {num_texts} test texts...")
    texts = [
        f"This is test sentence number {i} for benchmarking batch processing performance"
        for i in range(num_texts)
    ]

    results = {"num_texts": num_texts, "device": service.get_device(), "batch_results": []}

    # Test each batch size
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
            "elapsed_time": elapsed,
            "throughput": throughput,
            "num_embeddings": len(embeddings),
        }
        results["batch_results"].append(batch_result)

        print(f"  Elapsed time:       {elapsed:.2f} s")
        print(f"  Throughput:         {throughput:.1f} texts/second")

        # Memory stats
        memory = get_memory_usage()
        if "rss_formatted" in memory:
            print(f"  Memory (RSS):       {memory['rss_formatted']}")
        if "gpu_allocated_formatted" in memory:
            print(f"  GPU Memory:         {memory['gpu_allocated_formatted']}")

    # Find best batch size
    best_result = max(results["batch_results"], key=lambda x: x["throughput"])
    print("\nBest performance:")
    print(f"  Batch size:         {best_result['batch_size']}")
    print(f"  Throughput:         {best_result['throughput']:.1f} texts/second")

    # Check against target
    device = service.get_device()
    if device == "cuda":
        target_throughput = 2000
    elif device == "mps":
        target_throughput = 1000
    else:  # CPU
        target_throughput = 500

    status = "✓ PASS" if best_result["throughput"] > target_throughput else "✗ FAIL"
    print(f"\nTarget: >{target_throughput} texts/second on {device} - {status}")

    return results


def benchmark_memory_usage(
    service: EmbeddingService,
) -> dict[str, Any]:
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
        print("psutil not available, skipping detailed memory benchmarks")
        return {}

    # Get baseline memory
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    baseline_memory = get_memory_usage()
    print("\nBaseline memory (before model load):")
    print(f"  RSS:                {baseline_memory['rss_formatted']}")
    if "gpu_allocated_formatted" in baseline_memory:
        print(f"  GPU Memory:         {baseline_memory['gpu_allocated_formatted']}")

    # Load model
    service.embed_text("Load model")

    # Get memory after model load
    loaded_memory = get_memory_usage()
    print("\nMemory after model load:")
    print(f"  RSS:                {loaded_memory['rss_formatted']}")
    if "gpu_allocated_formatted" in loaded_memory:
        print(f"  GPU Memory:         {loaded_memory['gpu_allocated_formatted']}")

    # Calculate model memory
    model_memory_rss = loaded_memory["rss"] - baseline_memory["rss"]
    print("\nModel memory footprint:")
    print(f"  RSS increase:       {format_bytes(model_memory_rss)}")

    if "gpu_allocated" in loaded_memory:
        model_memory_gpu = (
            loaded_memory["gpu_allocated"] - baseline_memory.get("gpu_allocated", 0)
        )
        print(f"  GPU increase:       {format_bytes(model_memory_gpu)}")

    # Process large batch and measure peak memory
    print("\nProcessing large batch (5000 texts)...")
    large_texts = [f"Text {i}" for i in range(5000)]
    service.embed_batch(large_texts)

    peak_memory = get_memory_usage()
    print("\nPeak memory during batch processing:")
    print(f"  RSS:                {peak_memory['rss_formatted']}")
    if "gpu_allocated_formatted" in peak_memory:
        print(f"  GPU Memory:         {peak_memory['gpu_allocated_formatted']}")

    # Check against target
    target_memory = 2 * 1024 * 1024 * 1024  # 2GB
    total_memory = peak_memory["rss"]
    status = "✓ PASS" if total_memory < target_memory else "✗ FAIL"
    print(f"\nTarget: <2GB total memory usage - {status}")

    return {
        "baseline_rss": baseline_memory["rss"],
        "loaded_rss": loaded_memory["rss"],
        "peak_rss": peak_memory["rss"],
        "model_memory_rss": model_memory_rss,
    }


def main() -> None:
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(
        description="Benchmark EmbeddingService performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--num-texts",
        type=int,
        default=1000,
        help="Number of texts for batch benchmarks (default: 1000)",
    )
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default=None,
        help="Comma-separated list of batch sizes to test (e.g., '16,32,64')",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations for single text benchmark (default: 100)",
    )
    parser.add_argument(
        "--skip-single",
        action="store_true",
        help="Skip single text benchmark",
    )
    parser.add_argument(
        "--skip-batch",
        action="store_true",
        help="Skip batch processing benchmark",
    )
    parser.add_argument(
        "--skip-memory",
        action="store_true",
        help="Skip memory usage benchmark",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = None
    if args.batch_sizes:
        batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Print system info
    print("=" * 80)
    print("EMBEDDING SERVICE PERFORMANCE BENCHMARK")
    print("=" * 80)
    print("\nSystem Information:")
    print(f"  Python version:     {sys.version.split()[0]}")
    print(f"  PyTorch version:    {torch.__version__}")
    print(f"  CUDA available:     {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA device:        {torch.cuda.get_device_name(0)}")
    print(f"  MPS available:      {hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()}")
    print(f"  psutil available:   {PSUTIL_AVAILABLE}")

    # Initialize service
    print("\nInitializing EmbeddingService...")
    service = EmbeddingService.get_instance()
    device = service.get_device()
    print(f"  Device:             {device}")
    print(f"  Model:              {service.MODEL_NAME}")
    print(f"  Embedding dim:      {service.get_embedding_dimension()}")

    # Run benchmarks
    all_results = {}

    if not args.skip_single:
        all_results["single_text"] = benchmark_single_text(service, args.iterations)

    if not args.skip_batch:
        all_results["batch"] = benchmark_batch_processing(
            service, args.num_texts, batch_sizes
        )

    if not args.skip_memory:
        all_results["memory"] = benchmark_memory_usage(service)

    # Final summary
    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)

    # Overall pass/fail
    all_passed = True

    if "single_text" in all_results:
        avg_latency = all_results["single_text"]["avg_latency_ms"]
        passed = avg_latency < 100.0
        all_passed = all_passed and passed
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\nSingle text latency:    {avg_latency:.2f} ms - {status}")

    if "batch" in all_results:
        best = max(all_results["batch"]["batch_results"], key=lambda x: x["throughput"])
        throughput = best["throughput"]
        device = all_results["batch"]["device"]
        target = 2000 if device == "cuda" else 1000 if device == "mps" else 500
        passed = throughput > target
        all_passed = all_passed and passed
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"Batch throughput:       {throughput:.1f} texts/s on {device} - {status}")

    if "memory" in all_results and "peak_rss" in all_results["memory"]:
        peak_gb = all_results["memory"]["peak_rss"] / (1024**3)
        passed = peak_gb < 2.0
        all_passed = all_passed and passed
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"Peak memory usage:      {peak_gb:.2f} GB - {status}")

    print("\n" + "=" * 80)
    final_status = "✓ ALL BENCHMARKS PASSED" if all_passed else "✗ SOME BENCHMARKS FAILED"
    print(final_status)
    print("=" * 80)

    # Exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
