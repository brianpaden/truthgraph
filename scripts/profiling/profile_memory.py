"""Memory profiling for embedding service.

This script performs detailed memory profiling of the EmbeddingService to identify
memory usage patterns, potential leaks, and optimization opportunities.

Usage:
    python scripts/profiling/profile_memory.py [--test-size 1000] [--iterations 5]

Key metrics tracked:
    - Baseline memory (model loaded)
    - Per-batch memory usage
    - Peak memory during processing
    - Memory growth patterns
    - Garbage collection impact

This helps identify:
    1. Memory scaling with batch size
    2. Memory leaks or accumulation
    3. Optimal batch size for memory constraints
    4. GC effectiveness
"""

import argparse
import gc
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import torch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from truthgraph.services.ml.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MemoryProfiler:
    """Profiles memory usage of the embedding service.

    This class tracks memory consumption patterns across different batch sizes
    and workload scenarios to identify memory bottlenecks and leaks.

    Attributes:
        service: The EmbeddingService singleton instance
        test_texts: List of test texts to profile
        results: Dictionary storing memory profiling results
    """

    def __init__(self, test_texts: list[str]) -> None:
        """Initialize the memory profiler.

        Args:
            test_texts: List of texts to use for profiling
        """
        self.service = EmbeddingService.get_instance()
        self.test_texts = test_texts
        self.results: dict[str, Any] = {
            "metadata": {},
            "memory_measurements": [],
            "batch_memory_analysis": [],
            "memory_leak_check": {},
            "recommendations": [],
        }

        logger.info(f"Initialized memory profiler with {len(test_texts)} texts")

    def get_detailed_memory_info(self) -> dict[str, float]:
        """Get detailed memory information about current process.

        Returns:
            Dictionary with various memory metrics in MB
        """
        process = psutil.Process()
        mem_info = process.memory_info()

        memory_dict = {
            "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        }

        # Add platform-specific metrics if available
        if hasattr(mem_info, "data"):
            memory_dict["data_mb"] = mem_info.data / 1024 / 1024

        # GPU memory if available
        if torch.cuda.is_available():
            memory_dict["cuda_allocated_mb"] = torch.cuda.memory_allocated() / 1024 / 1024
            memory_dict["cuda_reserved_mb"] = torch.cuda.memory_reserved() / 1024 / 1024

        return memory_dict

    def measure_baseline_memory(self) -> dict[str, float]:
        """Measure baseline memory with model loaded but before processing.

        Returns:
            Dictionary with baseline memory metrics
        """
        logger.info("Measuring baseline memory...")

        # Force garbage collection
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Ensure model is loaded
        _ = self.service.embed_text("Warmup text")

        # Wait for stabilization
        time.sleep(0.5)

        # Force GC again
        gc.collect()

        baseline = self.get_detailed_memory_info()
        logger.info(f"Baseline memory: {baseline['rss_mb']:.2f} MB")

        return baseline

    def profile_batch_memory(
        self,
        batch_size: int,
        num_iterations: int = 3,
    ) -> dict[str, Any]:
        """Profile memory usage for a specific batch size.

        Args:
            batch_size: Batch size to test
            num_iterations: Number of iterations to run for averaging

        Returns:
            Dictionary with memory profiling metrics
        """
        logger.info(f"\nProfiling memory for batch_size={batch_size}")

        # Clean up before measurement
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        time.sleep(0.2)

        baseline_memory = self.get_detailed_memory_info()
        peak_memory = baseline_memory.copy()
        memory_samples = []

        for iteration in range(num_iterations):
            # Measure memory before
            mem_before = self.get_detailed_memory_info()

            # Run embedding
            start_time = time.perf_counter()
            _ = self.service.embed_batch(
                self.test_texts,
                batch_size=batch_size,
                show_progress=False,
            )
            elapsed_time = time.perf_counter() - start_time

            # Measure memory after
            mem_after = self.get_detailed_memory_info()

            # Track peak
            for key in mem_after:
                if mem_after[key] > peak_memory.get(key, 0):
                    peak_memory[key] = mem_after[key]

            memory_samples.append({
                "iteration": iteration + 1,
                "before_rss_mb": mem_before["rss_mb"],
                "after_rss_mb": mem_after["rss_mb"],
                "delta_rss_mb": mem_after["rss_mb"] - mem_before["rss_mb"],
                "elapsed_time_s": elapsed_time,
            })

            # Small delay between iterations
            time.sleep(0.1)

        # Calculate statistics
        avg_delta = sum(s["delta_rss_mb"] for s in memory_samples) / len(memory_samples)
        max_delta = max(s["delta_rss_mb"] for s in memory_samples)
        min_delta = min(s["delta_rss_mb"] for s in memory_samples)

        result = {
            "batch_size": batch_size,
            "num_iterations": num_iterations,
            "baseline_memory_mb": baseline_memory["rss_mb"],
            "peak_memory_mb": peak_memory["rss_mb"],
            "avg_delta_mb": avg_delta,
            "max_delta_mb": max_delta,
            "min_delta_mb": min_delta,
            "memory_samples": memory_samples,
        }

        logger.info(f"  Baseline: {baseline_memory['rss_mb']:.1f} MB")
        logger.info(f"  Peak: {peak_memory['rss_mb']:.1f} MB")
        logger.info(f"  Avg delta: {avg_delta:.1f} MB")

        return result

    def check_memory_leaks(
        self,
        batch_size: int = 32,
        num_iterations: int = 10,
    ) -> dict[str, Any]:
        """Check for memory leaks by running multiple iterations.

        Args:
            batch_size: Batch size to use for testing
            num_iterations: Number of iterations to run

        Returns:
            Dictionary with leak detection results
        """
        logger.info(f"\nChecking for memory leaks with {num_iterations} iterations...")

        # Clean up before test
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        time.sleep(0.5)

        initial_memory = self.get_detailed_memory_info()["rss_mb"]
        memory_over_time = []

        for i in range(num_iterations):
            # Run embedding
            _ = self.service.embed_batch(
                self.test_texts[:100],  # Use subset for faster testing
                batch_size=batch_size,
                show_progress=False,
            )

            # Force GC
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Measure memory
            current_memory = self.get_detailed_memory_info()["rss_mb"]
            memory_over_time.append({
                "iteration": i + 1,
                "memory_mb": current_memory,
                "delta_from_initial_mb": current_memory - initial_memory,
            })

            time.sleep(0.05)

        # Analyze for leaks
        final_memory = memory_over_time[-1]["memory_mb"]
        memory_growth = final_memory - initial_memory
        growth_rate = memory_growth / num_iterations

        # Calculate trend (simple linear regression)
        iterations = [m["iteration"] for m in memory_over_time]
        memories = [m["memory_mb"] for m in memory_over_time]
        n = len(iterations)
        mean_iter = sum(iterations) / n
        mean_mem = sum(memories) / n
        numerator = sum((iterations[i] - mean_iter) * (memories[i] - mean_mem) for i in range(n))
        denominator = sum((iterations[i] - mean_iter) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0

        leak_detected = slope > 1.0  # Growing by >1MB per iteration

        result = {
            "num_iterations": num_iterations,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "total_growth_mb": memory_growth,
            "growth_rate_mb_per_iteration": growth_rate,
            "linear_trend_slope": slope,
            "leak_detected": leak_detected,
            "memory_over_time": memory_over_time,
        }

        logger.info(f"  Initial: {initial_memory:.1f} MB")
        logger.info(f"  Final: {final_memory:.1f} MB")
        logger.info(f"  Growth: {memory_growth:+.1f} MB")
        logger.info(f"  Leak detected: {leak_detected}")

        return result

    def analyze_memory_patterns(self) -> list[dict[str, Any]]:
        """Analyze memory usage patterns and generate insights.

        Returns:
            List of memory analysis findings
        """
        logger.info("\nAnalyzing memory patterns...")

        findings = []

        # Analyze memory scaling with batch size
        batch_results = self.results["batch_memory_analysis"]
        if len(batch_results) >= 2:
            batch_sizes = [r["batch_size"] for r in batch_results]
            peak_memories = [r["peak_memory_mb"] for r in batch_results]

            # Calculate memory growth rate
            memory_growth_rate = (peak_memories[-1] - peak_memories[0]) / (batch_sizes[-1] - batch_sizes[0])

            findings.append({
                "type": "memory_scaling",
                "finding": f"Memory grows at {memory_growth_rate:.2f} MB per batch size unit",
                "severity": "low" if memory_growth_rate < 2 else "medium",
                "recommendation": "Memory scaling is approximately linear" if memory_growth_rate < 2 else "Consider smaller batches for memory-constrained environments",
            })

        # Analyze leak detection results
        leak_check = self.results.get("memory_leak_check", {})
        if leak_check:
            if leak_check["leak_detected"]:
                findings.append({
                    "type": "memory_leak",
                    "finding": f"Potential memory leak detected: {leak_check['growth_rate_mb_per_iteration']:.2f} MB/iteration",
                    "severity": "high",
                    "recommendation": "Investigate model caching and tensor lifecycle management",
                })
            else:
                findings.append({
                    "type": "memory_stability",
                    "finding": "No memory leaks detected over multiple iterations",
                    "severity": "none",
                    "recommendation": "Memory management is working correctly",
                })

        # Find optimal batch size for memory
        if batch_results:
            # Find batch size with best throughput/memory ratio
            best_efficiency = None
            best_batch = None

            for result in batch_results:
                # Simple efficiency metric: throughput per MB of memory
                # Note: we'd need throughput data for this, so just use inverse of memory
                efficiency = 1.0 / result["peak_memory_mb"]

                if best_efficiency is None or efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_batch = result["batch_size"]

            findings.append({
                "type": "memory_efficiency",
                "finding": f"Batch size {best_batch} offers best memory efficiency",
                "severity": "info",
                "recommendation": f"Consider batch_size={best_batch} for memory-constrained deployments",
            })

        return findings

    def generate_recommendations(self) -> list[dict[str, Any]]:
        """Generate memory optimization recommendations.

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Get batch memory results
        batch_results = self.results.get("batch_memory_analysis", [])

        if batch_results:
            # Find lowest memory batch size
            min_memory_result = min(batch_results, key=lambda x: x["peak_memory_mb"])

            recommendations.append({
                "optimization": "Memory-Constrained Batch Size",
                "description": f"Use batch_size={min_memory_result['batch_size']} for minimal memory footprint",
                "expected_improvement": f"Reduces memory to {min_memory_result['peak_memory_mb']:.1f} MB",
                "effort": "low",
                "priority": "medium",
            })

        # Check if GPU memory would help
        if self.service.get_device() == "cpu" and torch.cuda.is_available():
            recommendations.append({
                "optimization": "GPU Memory Utilization",
                "description": "Move processing to GPU to free up system RAM",
                "expected_improvement": "Significant system memory reduction",
                "effort": "low",
                "priority": "medium",
            })

        # Garbage collection recommendation
        leak_check = self.results.get("memory_leak_check", {})
        if leak_check and not leak_check["leak_detected"]:
            recommendations.append({
                "optimization": "Periodic Garbage Collection",
                "description": "Current GC strategy is working well",
                "expected_improvement": "No change needed",
                "effort": "none",
                "priority": "low",
            })

        return recommendations

    def run_profiling(
        self,
        batch_sizes: list[int] | None = None,
        num_iterations: int = 3,
    ) -> dict[str, Any]:
        """Run complete memory profiling suite.

        Args:
            batch_sizes: List of batch sizes to test
            num_iterations: Number of iterations per batch size

        Returns:
            Complete memory profiling results
        """
        if batch_sizes is None:
            batch_sizes = [8, 16, 32, 64, 128, 256]

        logger.info("Starting memory profiling...")
        logger.info(f"Device: {self.service.get_device()}")

        # Measure baseline
        baseline = self.measure_baseline_memory()
        self.results["baseline_memory"] = baseline

        # Profile each batch size
        for batch_size in batch_sizes:
            result = self.profile_batch_memory(batch_size, num_iterations)
            self.results["batch_memory_analysis"].append(result)

        # Check for memory leaks
        leak_check = self.check_memory_leaks(batch_size=32, num_iterations=10)
        self.results["memory_leak_check"] = leak_check

        # Analyze patterns
        findings = self.analyze_memory_patterns()
        self.results["memory_patterns"] = findings

        # Generate recommendations
        recommendations = self.generate_recommendations()
        self.results["recommendations"] = recommendations

        # Add metadata
        self.results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "device": self.service.get_device(),
            "model": EmbeddingService.MODEL_NAME,
            "num_test_texts": len(self.test_texts),
            "batch_sizes_tested": batch_sizes,
            "cuda_available": torch.cuda.is_available(),
        }

        logger.info("\nMemory profiling complete!")

        return self.results

    def save_results(self, output_path: Path) -> None:
        """Save memory profiling results to JSON file.

        Args:
            output_path: Path to save results JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to: {output_path}")

    def print_summary(self) -> None:
        """Print memory profiling summary to console."""
        print("\n" + "="*60)
        print("MEMORY PROFILING SUMMARY")
        print("="*60)

        baseline = self.results.get("baseline_memory", {})
        print(f"\nBaseline Memory: {baseline.get('rss_mb', 0):.2f} MB")

        print(f"\nBatch Size Memory Usage:")
        print(f"{'Batch':>8} {'Baseline':>12} {'Peak':>12} {'Avg Δ':>12} {'Max Δ':>12}")
        print(f"{'Size':>8} {'(MB)':>12} {'(MB)':>12} {'(MB)':>12} {'(MB)':>12}")
        print("-" * 60)

        for result in self.results["batch_memory_analysis"]:
            print(
                f"{result['batch_size']:>8} "
                f"{result['baseline_memory_mb']:>12.1f} "
                f"{result['peak_memory_mb']:>12.1f} "
                f"{result['avg_delta_mb']:>12.1f} "
                f"{result['max_delta_mb']:>12.1f}"
            )

        # Memory leak check
        leak_check = self.results.get("memory_leak_check", {})
        if leak_check:
            print(f"\nMemory Leak Check:")
            print(f"  Iterations: {leak_check['num_iterations']}")
            print(f"  Initial: {leak_check['initial_memory_mb']:.1f} MB")
            print(f"  Final: {leak_check['final_memory_mb']:.1f} MB")
            print(f"  Growth: {leak_check['total_growth_mb']:+.1f} MB")
            print(f"  Leak detected: {leak_check['leak_detected']}")

        print("\n" + "="*60)


def load_test_data(num_texts: int = 1000) -> list[str]:
    """Load test texts for profiling.

    Args:
        num_texts: Number of texts to load

    Returns:
        List of test texts
    """
    test_claims_path = project_root / "tests" / "fixtures" / "test_claims.json"

    if not test_claims_path.exists():
        logger.warning(f"Test claims file not found: {test_claims_path}")
        return [f"Test claim {i} for memory profiling." for i in range(num_texts)]

    with open(test_claims_path) as f:
        data = json.load(f)

    claims = [claim["text"] for claim in data["claims"]]

    # Replicate to reach desired size
    texts = []
    while len(texts) < num_texts:
        texts.extend(claims)

    return texts[:num_texts]


def main() -> None:
    """Main entry point for memory profiling."""
    parser = argparse.ArgumentParser(
        description="Profile memory usage of EmbeddingService"
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=1000,
        help="Number of texts to use for testing (default: 1000)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per batch size (default: 3)",
    )
    parser.add_argument(
        "--batch-sizes",
        type=int,
        nargs="+",
        default=[8, 16, 32, 64, 128, 256],
        help="Batch sizes to test (default: 8 16 32 64 128 256)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/profiling/results",
        help="Output directory for results (default: scripts/profiling/results)",
    )

    args = parser.parse_args()

    # Load test data
    logger.info(f"Loading {args.test_size} test texts...")
    test_texts = load_test_data(args.test_size)

    # Create profiler
    profiler = MemoryProfiler(test_texts)

    # Run profiling
    results = profiler.run_profiling(
        batch_sizes=args.batch_sizes,
        num_iterations=args.iterations,
    )

    # Save results
    output_dir = project_root / args.output
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"memory_analysis_{timestamp}.json"
    profiler.save_results(output_path)

    # Print summary
    profiler.print_summary()

    logger.info(f"\nMemory profiling complete! Results saved to: {output_path}")


if __name__ == "__main__":
    main()
