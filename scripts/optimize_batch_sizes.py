#!/usr/bin/env python3
"""Batch size optimization script for ML services.

This script tests different batch sizes to find the optimal configuration
for maximum throughput while respecting memory constraints.

Features:
    - Tests range of batch sizes for each service
    - Measures throughput and memory usage
    - Identifies optimal batch size per device type
    - Generates recommendations
    - Saves results for analysis

Usage:
    python scripts/optimize_batch_sizes.py
    python scripts/optimize_batch_sizes.py --service embedding
    python scripts/optimize_batch_sizes.py --min-batch 4 --max-batch 256
    python scripts/optimize_batch_sizes.py --num-samples 2000
    python scripts/optimize_batch_sizes.py --memory-limit 4000

Example output:
    Optimal batch sizes:
      Embedding (CPU): 32 -> 523 texts/second
      NLI (CPU): 8 -> 2.3 pairs/second
"""

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

from truthgraph.services.ml.embedding_service import EmbeddingService
from truthgraph.services.ml.nli_service import get_nli_service

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. Memory monitoring will be limited.")


class BatchSizeOptimizer:
    """Optimizer for finding optimal batch sizes."""

    def __init__(self, memory_limit_mb: float = 4000):
        """Initialize the optimizer.

        Args:
            memory_limit_mb: Maximum memory usage in MB
        """
        self.memory_limit_mb = memory_limit_mb
        self.results: dict[str, Any] = {}

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB.

        Returns:
            Memory usage in MB (RSS if psutil available, else 0)
        """
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        return 0.0

    def optimize_embedding_batch_size(
        self,
        min_batch: int = 4,
        max_batch: int = 256,
        num_samples: int = 1000,
    ) -> dict[str, Any]:
        """Find optimal batch size for embedding service.

        Args:
            min_batch: Minimum batch size to test
            max_batch: Maximum batch size to test
            num_samples: Number of samples to process

        Returns:
            Dictionary with optimization results
        """
        print("\n" + "=" * 80)
        print("OPTIMIZING: Embedding Service Batch Size")
        print("=" * 80)

        service = EmbeddingService.get_instance()
        device = service.get_device()

        print(f"\nDevice: {device}")
        print(f"Testing batch sizes from {min_batch} to {max_batch}")
        print(f"Number of samples: {num_samples}")

        # Generate test data
        texts = [f"Test text number {i} for batch size optimization" for i in range(num_samples)]

        # Test different batch sizes
        batch_sizes = []
        current = min_batch
        while current <= max_batch:
            batch_sizes.append(current)
            current *= 2

        results = []

        for batch_size in batch_sizes:
            print(f"\nTesting batch_size={batch_size}...")

            # Cleanup before test
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            memory_before = self.get_memory_usage()

            try:
                # Warmup
                service.embed_batch(texts[:100], batch_size=batch_size, show_progress=False)

                # Benchmark
                start_time = time.perf_counter()
                embeddings = service.embed_batch(texts, batch_size=batch_size, show_progress=False)
                elapsed = time.perf_counter() - start_time

                memory_after = self.get_memory_usage()
                memory_used = memory_after - memory_before

                throughput = num_samples / elapsed

                result = {
                    "batch_size": batch_size,
                    "elapsed_time_s": elapsed,
                    "throughput_texts_per_sec": throughput,
                    "memory_before_mb": memory_before,
                    "memory_after_mb": memory_after,
                    "memory_used_mb": memory_used,
                    "num_embeddings": len(embeddings),
                    "success": True,
                }

                results.append(result)

                print(f"  Throughput: {throughput:.1f} texts/second")
                print(f"  Memory used: {memory_used:.1f} MB")

                # Check memory limit
                if memory_after > self.memory_limit_mb:
                    print(f"  WARNING: Memory exceeds limit ({self.memory_limit_mb} MB)")
                    break

            except Exception as e:
                print(f"  ERROR: {e}")
                results.append(
                    {
                        "batch_size": batch_size,
                        "success": False,
                        "error": str(e),
                    }
                )
                break

        # Find optimal batch size
        successful_results = [r for r in results if r.get("success", False)]

        if not successful_results:
            print("\nNo successful runs!")
            return {"device": device, "results": results, "optimal": None}

        # Filter by memory constraint
        valid_results = [r for r in successful_results if r["memory_after_mb"] <= self.memory_limit_mb]

        if not valid_results:
            print(f"\nWARNING: No batch sizes fit within memory limit ({self.memory_limit_mb} MB)")
            valid_results = successful_results

        # Find highest throughput
        optimal = max(valid_results, key=lambda x: x["throughput_texts_per_sec"])

        print("\n" + "-" * 80)
        print("OPTIMAL CONFIGURATION:")
        print(f"  Batch size: {optimal['batch_size']}")
        print(f"  Throughput: {optimal['throughput_texts_per_sec']:.1f} texts/second")
        print(f"  Memory: {optimal['memory_after_mb']:.1f} MB")

        # Check against target
        target = 500
        status = "PASS" if optimal["throughput_texts_per_sec"] > target else "FAIL"
        print(f"  Target (>500 texts/s): {status}")

        return {
            "device": device,
            "results": results,
            "optimal": optimal,
            "target_met": optimal["throughput_texts_per_sec"] > target,
        }

    def optimize_nli_batch_size(
        self,
        min_batch: int = 2,
        max_batch: int = 32,
        num_samples: int = 100,
    ) -> dict[str, Any]:
        """Find optimal batch size for NLI service.

        Args:
            min_batch: Minimum batch size to test
            max_batch: Maximum batch size to test
            num_samples: Number of samples to process

        Returns:
            Dictionary with optimization results
        """
        print("\n" + "=" * 80)
        print("OPTIMIZING: NLI Service Batch Size")
        print("=" * 80)

        service = get_nli_service()
        model_info = service.get_model_info()
        device = model_info["device"]

        print(f"\nDevice: {device}")
        print(f"Testing batch sizes from {min_batch} to {max_batch}")
        print(f"Number of samples: {num_samples}")

        # Generate test data
        pairs = [
            (
                f"Premise {i}: This is evidence text for testing batch optimization",
                f"Hypothesis {i}: This is a claim to verify for testing",
            )
            for i in range(num_samples)
        ]

        # Test different batch sizes
        batch_sizes = []
        current = min_batch
        while current <= max_batch:
            batch_sizes.append(current)
            current *= 2

        results = []

        for batch_size in batch_sizes:
            print(f"\nTesting batch_size={batch_size}...")

            # Cleanup before test
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            memory_before = self.get_memory_usage()

            try:
                # Warmup
                service.verify_batch(pairs[:10], batch_size=batch_size)

                # Benchmark
                start_time = time.perf_counter()
                nli_results = service.verify_batch(pairs, batch_size=batch_size)
                elapsed = time.perf_counter() - start_time

                memory_after = self.get_memory_usage()
                memory_used = memory_after - memory_before

                throughput = num_samples / elapsed

                result = {
                    "batch_size": batch_size,
                    "elapsed_time_s": elapsed,
                    "throughput_pairs_per_sec": throughput,
                    "memory_before_mb": memory_before,
                    "memory_after_mb": memory_after,
                    "memory_used_mb": memory_used,
                    "num_results": len(nli_results),
                    "success": True,
                }

                results.append(result)

                print(f"  Throughput: {throughput:.2f} pairs/second")
                print(f"  Memory used: {memory_used:.1f} MB")

                # Check memory limit
                if memory_after > self.memory_limit_mb:
                    print(f"  WARNING: Memory exceeds limit ({self.memory_limit_mb} MB)")
                    break

            except Exception as e:
                print(f"  ERROR: {e}")
                results.append(
                    {
                        "batch_size": batch_size,
                        "success": False,
                        "error": str(e),
                    }
                )
                break

        # Find optimal batch size
        successful_results = [r for r in results if r.get("success", False)]

        if not successful_results:
            print("\nNo successful runs!")
            return {"device": device, "results": results, "optimal": None}

        # Filter by memory constraint
        valid_results = [r for r in successful_results if r["memory_after_mb"] <= self.memory_limit_mb]

        if not valid_results:
            print(f"\nWARNING: No batch sizes fit within memory limit ({self.memory_limit_mb} MB)")
            valid_results = successful_results

        # Find highest throughput
        optimal = max(valid_results, key=lambda x: x["throughput_pairs_per_sec"])

        print("\n" + "-" * 80)
        print("OPTIMAL CONFIGURATION:")
        print(f"  Batch size: {optimal['batch_size']}")
        print(f"  Throughput: {optimal['throughput_pairs_per_sec']:.2f} pairs/second")
        print(f"  Memory: {optimal['memory_after_mb']:.1f} MB")

        # Check against target
        target = 2.0
        status = "PASS" if optimal["throughput_pairs_per_sec"] > target else "FAIL"
        print(f"  Target (>2 pairs/s): {status}")

        return {
            "device": device,
            "results": results,
            "optimal": optimal,
            "target_met": optimal["throughput_pairs_per_sec"] > target,
        }

    def generate_recommendations(self) -> None:
        """Generate batch size recommendations based on results."""
        print("\n" + "=" * 80)
        print("BATCH SIZE RECOMMENDATIONS")
        print("=" * 80)

        if "embedding" in self.results and self.results["embedding"]["optimal"]:
            emb = self.results["embedding"]
            opt = emb["optimal"]
            print(f"\nEmbedding Service ({emb['device']}):")
            print(f"  Recommended batch size: {opt['batch_size']}")
            print(f"  Expected throughput: {opt['throughput_texts_per_sec']:.1f} texts/second")
            print(f"  Memory usage: {opt['memory_after_mb']:.1f} MB")

        if "nli" in self.results and self.results["nli"]["optimal"]:
            nli = self.results["nli"]
            opt = nli["optimal"]
            print(f"\nNLI Service ({nli['device']}):")
            print(f"  Recommended batch size: {opt['batch_size']}")
            print(f"  Expected throughput: {opt['throughput_pairs_per_sec']:.2f} pairs/second")
            print(f"  Memory usage: {opt['memory_after_mb']:.1f} MB")

        print("\nImplementation:")
        print("  Update service defaults with optimal batch sizes")
        print("  Add device-specific batch size selection")
        print("  Consider batch size as configuration parameter")

        # Save results
        output_file = Path("batch_size_optimization_results.json")
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nResults saved to: {output_file}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize batch sizes for ML services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--service",
        type=str,
        choices=["embedding", "nli", "all"],
        default="all",
        help="Which service to optimize (default: all)",
    )
    parser.add_argument(
        "--min-batch",
        type=int,
        default=None,
        help="Minimum batch size to test (default: service-specific)",
    )
    parser.add_argument(
        "--max-batch",
        type=int,
        default=None,
        help="Maximum batch size to test (default: service-specific)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=None,
        help="Number of samples to process (default: service-specific)",
    )
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=4000,
        help="Memory limit in MB (default: 4000)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("BATCH SIZE OPTIMIZER")
    print("=" * 80)
    print("\nConfiguration:")
    print(f"  Service: {args.service}")
    print(f"  Memory limit: {args.memory_limit} MB")

    optimizer = BatchSizeOptimizer(memory_limit_mb=args.memory_limit)

    # Run optimization
    if args.service == "all" or args.service == "embedding":
        min_batch = args.min_batch or 4
        max_batch = args.max_batch or 256
        num_samples = args.num_samples or 1000

        optimizer.results["embedding"] = optimizer.optimize_embedding_batch_size(
            min_batch=min_batch,
            max_batch=max_batch,
            num_samples=num_samples,
        )

    if args.service == "all" or args.service == "nli":
        min_batch = args.min_batch or 2
        max_batch = args.max_batch or 32
        num_samples = args.num_samples or 100

        optimizer.results["nli"] = optimizer.optimize_nli_batch_size(
            min_batch=min_batch,
            max_batch=max_batch,
            num_samples=num_samples,
        )

    # Generate recommendations
    optimizer.generate_recommendations()

    print("\nOptimization complete!")


if __name__ == "__main__":
    main()
