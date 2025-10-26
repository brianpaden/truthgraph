#!/usr/bin/env python3
"""Comprehensive profiling script for ML services.

This script profiles all ML services to identify performance bottlenecks,
memory usage patterns, and optimization opportunities.

Features:
    - CPU profiling with cProfile
    - Memory profiling with memory_profiler (if available)
    - GPU utilization monitoring
    - Detailed timing breakdowns
    - Bottleneck identification
    - Optimization recommendations

Usage:
    python scripts/profile_ml_services.py
    python scripts/profile_ml_services.py --service embedding
    python scripts/profile_ml_services.py --service nli --num-samples 100
    python scripts/profile_ml_services.py --output-dir ./profiling_results
    python scripts/profile_ml_services.py --memory-profile

Performance Targets:
    - Embedding: >500 texts/second, <2GB memory
    - NLI: >2 pairs/second, <2GB memory
    - Total memory: <4GB
    - Model load time: <5 seconds
"""

import argparse
import cProfile
import gc
import io
import json
import pstats
import sys
import time
from pathlib import Path
from pstats import SortKey
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. Install with: pip install psutil")

try:
    from memory_profiler import profile as memory_profile

    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    print(
        "Warning: memory_profiler not installed. Install with: pip install memory-profiler"
    )

import torch

from truthgraph.services.ml.embedding_service import EmbeddingService
from truthgraph.services.ml.model_cache import ModelCache
from truthgraph.services.ml.nli_service import get_nli_service


class PerformanceProfiler:
    """Comprehensive performance profiler for ML services."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize the profiler.

        Args:
            output_dir: Directory to save profiling results
        """
        self.output_dir = output_dir or Path("./profiling_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: dict[str, Any] = {}

    def get_memory_info(self) -> dict[str, float]:
        """Get current memory usage information.

        Returns:
            Dictionary with memory statistics in MB
        """
        memory_info = {}

        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            mem = process.memory_info()
            memory_info["rss_mb"] = mem.rss / 1024 / 1024
            memory_info["vms_mb"] = mem.vms / 1024 / 1024

        if torch.cuda.is_available():
            memory_info["cuda_allocated_mb"] = torch.cuda.memory_allocated() / 1024 / 1024
            memory_info["cuda_reserved_mb"] = torch.cuda.memory_reserved() / 1024 / 1024

        return memory_info

    def profile_embedding_service(
        self, num_samples: int = 1000, batch_size: int = 32
    ) -> dict[str, Any]:
        """Profile the embedding service.

        Args:
            num_samples: Number of texts to process
            batch_size: Batch size for processing

        Returns:
            Dictionary with profiling results
        """
        print("\n" + "=" * 80)
        print("PROFILING: Embedding Service")
        print("=" * 80)

        service = EmbeddingService.get_instance()
        results: dict[str, Any] = {
            "service": "embedding",
            "num_samples": num_samples,
            "batch_size": batch_size,
        }

        # Memory before model load
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        memory_before = self.get_memory_info()
        results["memory_before_load"] = memory_before

        # Profile model loading
        print("\nProfiling model loading...")
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        service.embed_text("warmup")  # Trigger model load
        load_time = (time.perf_counter() - start_time) * 1000

        profiler.disable()

        results["model_load_time_ms"] = load_time
        print(f"  Model load time: {load_time:.1f} ms")

        # Memory after model load
        memory_after = self.get_memory_info()
        results["memory_after_load"] = memory_after

        if "rss_mb" in memory_before and "rss_mb" in memory_after:
            model_memory = memory_after["rss_mb"] - memory_before["rss_mb"]
            results["model_memory_mb"] = model_memory
            print(f"  Model memory: {model_memory:.1f} MB")

        # Save model loading profile
        self._save_profile_stats(
            profiler, "embedding_model_load", "Model loading hotspots:"
        )

        # Profile single text embedding
        print("\nProfiling single text embedding...")
        profiler = cProfile.Profile()
        test_text = "This is a test sentence for profiling single text embedding"

        profiler.enable()
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            service.embed_text(test_text)
            latencies.append((time.perf_counter() - start) * 1000)
        profiler.disable()

        results["single_text_avg_latency_ms"] = sum(latencies) / len(latencies)
        results["single_text_min_latency_ms"] = min(latencies)
        results["single_text_max_latency_ms"] = max(latencies)

        print(f"  Average latency: {results['single_text_avg_latency_ms']:.2f} ms")

        self._save_profile_stats(
            profiler, "embedding_single_text", "Single text embedding hotspots:"
        )

        # Profile batch processing
        print(f"\nProfiling batch processing ({num_samples} texts)...")
        test_texts = [f"Test sentence number {i} for batch profiling" for i in range(num_samples)]

        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        embeddings = service.embed_batch(test_texts, batch_size=batch_size)
        elapsed = time.perf_counter() - start_time

        profiler.disable()

        throughput = num_samples / elapsed
        results["batch_elapsed_time_s"] = elapsed
        results["batch_throughput_texts_per_sec"] = throughput

        print(f"  Elapsed time: {elapsed:.2f} s")
        print(f"  Throughput: {throughput:.1f} texts/second")

        # Check target
        target = 500
        status = "PASS" if throughput > target else "FAIL"
        print(f"  Target (>500 texts/s): {status}")
        results["throughput_target_met"] = throughput > target

        self._save_profile_stats(
            profiler, "embedding_batch", "Batch processing hotspots:"
        )

        # Memory after batch
        memory_peak = self.get_memory_info()
        results["memory_peak"] = memory_peak

        if "rss_mb" in memory_peak:
            print(f"  Peak memory: {memory_peak['rss_mb']:.1f} MB")

        return results

    def profile_nli_service(
        self, num_samples: int = 100, batch_size: int = 8
    ) -> dict[str, Any]:
        """Profile the NLI service.

        Args:
            num_samples: Number of pairs to process
            batch_size: Batch size for processing

        Returns:
            Dictionary with profiling results
        """
        print("\n" + "=" * 80)
        print("PROFILING: NLI Service")
        print("=" * 80)

        service = get_nli_service()
        results: dict[str, Any] = {
            "service": "nli",
            "num_samples": num_samples,
            "batch_size": batch_size,
        }

        # Memory before model load
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        memory_before = self.get_memory_info()
        results["memory_before_load"] = memory_before

        # Profile model loading
        print("\nProfiling model loading...")
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        service.verify_single("warmup premise", "warmup hypothesis")
        load_time = (time.perf_counter() - start_time) * 1000

        profiler.disable()

        results["model_load_time_ms"] = load_time
        print(f"  Model load time: {load_time:.1f} ms")

        # Memory after model load
        memory_after = self.get_memory_info()
        results["memory_after_load"] = memory_after

        if "rss_mb" in memory_before and "rss_mb" in memory_after:
            model_memory = memory_after["rss_mb"] - memory_before["rss_mb"]
            results["model_memory_mb"] = model_memory
            print(f"  Model memory: {model_memory:.1f} MB")

        self._save_profile_stats(profiler, "nli_model_load", "Model loading hotspots:")

        # Profile single pair inference
        print("\nProfiling single pair inference...")
        profiler = cProfile.Profile()

        profiler.enable()
        latencies = []
        for i in range(50):
            premise = f"Test premise {i} for profiling single pair inference"
            hypothesis = f"Test hypothesis {i} for profiling"
            start = time.perf_counter()
            service.verify_single(premise, hypothesis)
            latencies.append((time.perf_counter() - start) * 1000)
        profiler.disable()

        results["single_pair_avg_latency_ms"] = sum(latencies) / len(latencies)
        results["single_pair_throughput_pairs_per_sec"] = 1000 / results[
            "single_pair_avg_latency_ms"
        ]

        print(f"  Average latency: {results['single_pair_avg_latency_ms']:.1f} ms")
        print(
            f"  Throughput: {results['single_pair_throughput_pairs_per_sec']:.2f} pairs/sec"
        )

        self._save_profile_stats(
            profiler, "nli_single_pair", "Single pair inference hotspots:"
        )

        # Profile batch inference
        print(f"\nProfiling batch inference ({num_samples} pairs)...")
        test_pairs = [
            (
                f"Premise {i}: This is evidence text for testing",
                f"Hypothesis {i}: This is a claim to verify",
            )
            for i in range(num_samples)
        ]

        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        results_list = service.verify_batch(test_pairs, batch_size=batch_size)
        elapsed = time.perf_counter() - start_time

        profiler.disable()

        throughput = num_samples / elapsed
        results["batch_elapsed_time_s"] = elapsed
        results["batch_throughput_pairs_per_sec"] = throughput

        print(f"  Elapsed time: {elapsed:.2f} s")
        print(f"  Throughput: {throughput:.2f} pairs/second")

        # Check target
        target = 2.0
        status = "PASS" if throughput > target else "FAIL"
        print(f"  Target (>2 pairs/s): {status}")
        results["throughput_target_met"] = throughput > target

        self._save_profile_stats(profiler, "nli_batch", "Batch inference hotspots:")

        # Memory after batch
        memory_peak = self.get_memory_info()
        results["memory_peak"] = memory_peak

        if "rss_mb" in memory_peak:
            print(f"  Peak memory: {memory_peak['rss_mb']:.1f} MB")

        return results

    def profile_model_cache(self) -> dict[str, Any]:
        """Profile the model cache system.

        Returns:
            Dictionary with profiling results
        """
        print("\n" + "=" * 80)
        print("PROFILING: Model Cache System")
        print("=" * 80)

        cache = ModelCache.get_instance()
        results: dict[str, Any] = {"service": "model_cache"}

        # Memory before loading
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        memory_before = self.get_memory_info()

        # Profile warmup
        print("\nProfiling model warmup...")
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        load_times = cache.warmup_all_models()
        warmup_time = (time.perf_counter() - start_time) * 1000

        profiler.disable()

        results["warmup_time_ms"] = warmup_time
        results["individual_load_times"] = load_times

        print(f"  Total warmup time: {warmup_time:.1f} ms")
        for model, time_ms in load_times.items():
            print(f"    {model}: {time_ms:.1f} ms")

        self._save_profile_stats(profiler, "model_cache_warmup", "Warmup hotspots:")

        # Get cache stats
        stats = cache.get_cache_stats()
        results["cache_stats"] = stats

        print(f"\nCache statistics:")
        print(f"  Models loaded: {stats['models_loaded']}")
        print(f"  Total memory: {stats['total_memory_mb']:.1f} MB")

        # Memory after loading
        memory_after = self.get_memory_info()

        if "rss_mb" in memory_before and "rss_mb" in memory_after:
            total_memory = memory_after["rss_mb"]
            results["total_memory_mb"] = total_memory
            print(f"  Process RSS: {total_memory:.1f} MB")

            # Check target
            target = 4000  # 4GB
            status = "PASS" if total_memory < target else "FAIL"
            print(f"  Target (<4GB): {status}")
            results["memory_target_met"] = total_memory < target

        return results

    def _save_profile_stats(
        self, profiler: cProfile.Profile, name: str, title: str
    ) -> None:
        """Save profiling statistics to file and print summary.

        Args:
            profiler: cProfile.Profile instance
            name: Name for the output file
            title: Title to print
        """
        # Save to file
        stats_file = self.output_dir / f"{name}.prof"
        profiler.dump_stats(str(stats_file))

        # Print summary
        print(f"\n{title}")
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(10)  # Top 10 functions
        print(s.getvalue())

        # Save text summary
        text_file = self.output_dir / f"{name}.txt"
        with open(text_file, "w") as f:
            ps = pstats.Stats(profiler, stream=f)
            ps.sort_stats(SortKey.CUMULATIVE)
            ps.print_stats()

        print(f"  Detailed stats saved to: {stats_file}")
        print(f"  Text summary saved to: {text_file}")

    def generate_report(self) -> None:
        """Generate comprehensive profiling report."""
        print("\n" + "=" * 80)
        print("PROFILING REPORT SUMMARY")
        print("=" * 80)

        # Save results to JSON
        report_file = self.output_dir / "profiling_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\nFull report saved to: {report_file}")

        # Print summary
        print("\nPerformance Summary:")

        if "embedding" in self.results:
            emb = self.results["embedding"]
            print(f"\nEmbedding Service:")
            print(f"  Model load time: {emb.get('model_load_time_ms', 0):.1f} ms")
            print(
                f"  Single text latency: {emb.get('single_text_avg_latency_ms', 0):.2f} ms"
            )
            print(
                f"  Batch throughput: {emb.get('batch_throughput_texts_per_sec', 0):.1f} texts/s"
            )
            if "model_memory_mb" in emb:
                print(f"  Model memory: {emb['model_memory_mb']:.1f} MB")

        if "nli" in self.results:
            nli = self.results["nli"]
            print(f"\nNLI Service:")
            print(f"  Model load time: {nli.get('model_load_time_ms', 0):.1f} ms")
            print(
                f"  Single pair latency: {nli.get('single_pair_avg_latency_ms', 0):.1f} ms"
            )
            print(
                f"  Batch throughput: {nli.get('batch_throughput_pairs_per_sec', 0):.2f} pairs/s"
            )
            if "model_memory_mb" in nli:
                print(f"  Model memory: {nli['model_memory_mb']:.1f} MB")

        if "model_cache" in self.results:
            cache = self.results["model_cache"]
            print(f"\nModel Cache:")
            print(f"  Total warmup time: {cache.get('warmup_time_ms', 0):.1f} ms")
            if "total_memory_mb" in cache:
                print(f"  Total memory: {cache['total_memory_mb']:.1f} MB")

        # Identify bottlenecks
        print("\n" + "=" * 80)
        print("BOTTLENECK ANALYSIS")
        print("=" * 80)

        bottlenecks = []

        if "embedding" in self.results:
            emb = self.results["embedding"]
            if emb.get("batch_throughput_texts_per_sec", 0) < 500:
                bottlenecks.append(
                    f"Embedding throughput ({emb.get('batch_throughput_texts_per_sec', 0):.1f} texts/s) below target (500 texts/s)"
                )

        if "nli" in self.results:
            nli = self.results["nli"]
            if nli.get("batch_throughput_pairs_per_sec", 0) < 2:
                bottlenecks.append(
                    f"NLI throughput ({nli.get('batch_throughput_pairs_per_sec', 0):.2f} pairs/s) below target (2 pairs/s)"
                )

        if "model_cache" in self.results:
            cache = self.results["model_cache"]
            if cache.get("total_memory_mb", 0) > 4000:
                bottlenecks.append(
                    f"Total memory ({cache.get('total_memory_mb', 0):.1f} MB) exceeds target (4000 MB)"
                )

        if bottlenecks:
            print("\nIdentified bottlenecks:")
            for i, bottleneck in enumerate(bottlenecks, 1):
                print(f"  {i}. {bottleneck}")

            print("\nOptimization recommendations:")
            print("  1. Review profiling .prof files for hotspots")
            print("  2. Consider increasing batch sizes for better throughput")
            print("  3. Enable GPU acceleration if available")
            print("  4. Optimize batch size with optimize_batch_sizes.py script")
        else:
            print("\nNo critical bottlenecks identified. All targets met!")

        print("\n" + "=" * 80)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Profile ML services for performance analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--service",
        type=str,
        choices=["embedding", "nli", "cache", "all"],
        default="all",
        help="Which service to profile (default: all)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=1000,
        help="Number of samples for profiling (default: 1000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size (default: service-specific optimal)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./profiling_results"),
        help="Output directory for profiling results",
    )
    parser.add_argument(
        "--memory-profile",
        action="store_true",
        help="Enable detailed memory profiling (requires memory_profiler)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ML SERVICES PERFORMANCE PROFILER")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Service: {args.service}")
    print(f"  Samples: {args.num_samples}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Memory profiling: {args.memory_profile}")

    if args.memory_profile and not MEMORY_PROFILER_AVAILABLE:
        print("\nWarning: memory_profiler not available")
        print("Install with: pip install memory-profiler")

    profiler = PerformanceProfiler(output_dir=args.output_dir)

    # Run profiling
    if args.service == "all" or args.service == "embedding":
        batch_size = args.batch_size or 32
        profiler.results["embedding"] = profiler.profile_embedding_service(
            num_samples=args.num_samples, batch_size=batch_size
        )

    if args.service == "all" or args.service == "nli":
        batch_size = args.batch_size or 8
        profiler.results["nli"] = profiler.profile_nli_service(
            num_samples=min(args.num_samples, 100), batch_size=batch_size
        )

    if args.service == "all" or args.service == "cache":
        profiler.results["model_cache"] = profiler.profile_model_cache()

    # Generate report
    profiler.generate_report()

    print("\nProfiling complete!")


if __name__ == "__main__":
    main()
