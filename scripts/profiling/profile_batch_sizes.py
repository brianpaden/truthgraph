"""Batch size profiling for embedding service.

This script profiles the EmbeddingService with different batch sizes to identify
optimal performance configurations and bottlenecks. It uses cProfile for detailed
function-level profiling and tracks throughput, latency, and memory metrics.

Usage:
    python scripts/profiling/profile_batch_sizes.py [--test-size 1000] [--output results/]

Performance baseline (Feature 1.7):
    - Best throughput: 1,185 texts/sec @ batch_size=64
    - Target: >500 texts/sec
    - Memory: <2GB

This profiling helps identify:
    1. Optimal batch size for throughput
    2. CPU bottlenecks (tokenization, forward pass)
    3. Memory scaling patterns
    4. Function-level performance hotspots
"""

import argparse
import cProfile
import gc
import json
import logging
import pstats
import sys
import time
from datetime import datetime
from io import StringIO
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


class BatchSizeProfiler:
    """Profiles embedding service with different batch sizes.

    This class conducts comprehensive performance profiling across multiple batch sizes,
    measuring throughput, latency, memory usage, and CPU bottlenecks.

    Attributes:
        service: The EmbeddingService singleton instance
        test_texts: List of test texts to profile
        batch_sizes: List of batch sizes to test
        results: Dictionary storing profiling results
    """

    def __init__(
        self,
        test_texts: list[str],
        batch_sizes: list[int] | None = None,
    ) -> None:
        """Initialize the batch size profiler.

        Args:
            test_texts: List of texts to use for profiling
            batch_sizes: List of batch sizes to test. Defaults to [8, 16, 32, 64, 128, 256]
        """
        self.service = EmbeddingService.get_instance()
        self.test_texts = test_texts
        self.batch_sizes = batch_sizes or [8, 16, 32, 64, 128, 256]
        self.results: dict[str, Any] = {
            "metadata": {},
            "batch_results": [],
            "profiling_stats": {},
            "bottlenecks": [],
            "recommendations": [],
        }

        logger.info(f"Initialized profiler with {len(test_texts)} texts")
        logger.info(f"Testing batch sizes: {self.batch_sizes}")

    def warmup(self, iterations: int = 10) -> None:
        """Warm up the model to ensure JIT compilation and caching.

        Args:
            iterations: Number of warmup iterations to run
        """
        logger.info(f"Running {iterations} warmup iterations...")
        warmup_text = "This is a warmup text to initialize the model."

        for i in range(iterations):
            self.service.embed_text(warmup_text)

        logger.info("Warmup complete")

    def get_memory_usage(self) -> float:
        """Get current process memory usage in MB.

        Returns:
            Memory usage in MB
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def profile_batch_size(self, batch_size: int) -> dict[str, Any]:
        """Profile embedding generation with a specific batch size.

        Args:
            batch_size: Batch size to test

        Returns:
            Dictionary with profiling metrics including throughput, latency, memory
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Profiling batch_size={batch_size}")
        logger.info(f"{'='*60}")

        # Clean up memory before test
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        baseline_memory = self.get_memory_usage()

        # Profile with cProfile
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()

        # Run embedding generation
        embeddings = self.service.embed_batch(
            self.test_texts,
            batch_size=batch_size,
            show_progress=False,
        )

        end_time = time.perf_counter()
        profiler.disable()

        # Calculate metrics
        elapsed_time = end_time - start_time
        throughput = len(self.test_texts) / elapsed_time
        latency_per_text = (elapsed_time / len(self.test_texts)) * 1000  # ms
        peak_memory = self.get_memory_usage()
        memory_delta = peak_memory - baseline_memory

        # Extract profiling statistics
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")

        # Get top functions by cumulative time
        stream = StringIO()
        stats.stream = stream
        stats.print_stats(20)
        profiling_output = stream.getvalue()

        result = {
            "batch_size": batch_size,
            "num_texts": len(self.test_texts),
            "elapsed_time_s": elapsed_time,
            "throughput_texts_per_sec": throughput,
            "latency_ms_per_text": latency_per_text,
            "baseline_memory_mb": baseline_memory,
            "peak_memory_mb": peak_memory,
            "memory_delta_mb": memory_delta,
            "num_embeddings": len(embeddings),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0,
            "profiling_summary": profiling_output[:1000],  # First 1000 chars
        }

        logger.info(f"Throughput: {throughput:.2f} texts/sec")
        logger.info(f"Latency: {latency_per_text:.3f} ms/text")
        logger.info(f"Memory: {baseline_memory:.1f} -> {peak_memory:.1f} MB (Δ{memory_delta:.1f})")

        return result

    def analyze_bottlenecks(self) -> list[dict[str, Any]]:
        """Analyze profiling results to identify performance bottlenecks.

        Returns:
            List of bottleneck findings with descriptions and recommendations
        """
        logger.info("\n" + "="*60)
        logger.info("ANALYZING BOTTLENECKS")
        logger.info("="*60)

        bottlenecks = []

        # Analyze throughput scaling
        throughputs = [r["throughput_texts_per_sec"] for r in self.results["batch_results"]]
        best_throughput_idx = throughputs.index(max(throughputs))
        best_batch = self.results["batch_results"][best_throughput_idx]

        bottlenecks.append({
            "type": "optimal_batch_size",
            "finding": f"Best throughput at batch_size={best_batch['batch_size']}",
            "metric": f"{best_batch['throughput_texts_per_sec']:.2f} texts/sec",
            "recommendation": f"Use batch_size={best_batch['batch_size']} for optimal performance",
            "priority": "high",
        })

        # Analyze memory scaling
        memory_deltas = [r["memory_delta_mb"] for r in self.results["batch_results"]]
        max_memory_delta = max(memory_deltas)

        if max_memory_delta > 100:
            bottlenecks.append({
                "type": "memory_usage",
                "finding": f"Memory increases up to {max_memory_delta:.1f}MB with large batches",
                "metric": f"Max memory delta: {max_memory_delta:.1f}MB",
                "recommendation": "Consider memory constraints when choosing batch size",
                "priority": "medium",
            })

        # Compare with baseline
        baseline_throughput = 1184.92  # From Feature 1.7
        baseline_batch = 64

        current_result = next(
            (r for r in self.results["batch_results"] if r["batch_size"] == baseline_batch),
            None
        )

        if current_result:
            current_throughput = current_result["throughput_texts_per_sec"]
            variance_pct = ((current_throughput - baseline_throughput) / baseline_throughput) * 100

            bottlenecks.append({
                "type": "baseline_comparison",
                "finding": f"Current performance vs Feature 1.7 baseline",
                "metric": f"{variance_pct:+.2f}% variance at batch_size={baseline_batch}",
                "recommendation": "Performance consistent with baseline" if abs(variance_pct) < 5 else "Investigate performance deviation",
                "priority": "high" if abs(variance_pct) > 5 else "low",
            })

        # Analyze small batch inefficiency
        small_batch = self.results["batch_results"][0]  # batch_size=8
        efficiency = (small_batch["throughput_texts_per_sec"] / best_batch["throughput_texts_per_sec"]) * 100

        if efficiency < 60:
            bottlenecks.append({
                "type": "small_batch_inefficiency",
                "finding": f"Small batches (size={small_batch['batch_size']}) are {100-efficiency:.1f}% slower",
                "metric": f"{efficiency:.1f}% efficiency vs optimal",
                "recommendation": "Avoid small batch sizes in production",
                "priority": "medium",
            })

        return bottlenecks

    def generate_recommendations(self) -> list[dict[str, Any]]:
        """Generate optimization recommendations based on profiling results.

        Returns:
            List of actionable recommendations with effort/impact estimates
        """
        recommendations = []

        # Find optimal batch size
        throughputs = [r["throughput_texts_per_sec"] for r in self.results["batch_results"]]
        best_idx = throughputs.index(max(throughputs))
        best_batch = self.results["batch_results"][best_idx]

        recommendations.append({
            "optimization": "Batch Size Configuration",
            "description": f"Set DEFAULT_BATCH_SIZE to {best_batch['batch_size']}",
            "expected_improvement": "Baseline (already optimal)",
            "effort": "low",
            "priority": "high",
            "implementation": f"Update EmbeddingService.DEFAULT_BATCH_SIZE = {best_batch['batch_size']}",
        })

        # Check if GPU would help
        if self.service.get_device() == "cpu":
            recommendations.append({
                "optimization": "GPU Acceleration",
                "description": "Test with CUDA GPU if available",
                "expected_improvement": "2-5x throughput improvement",
                "effort": "medium",
                "priority": "medium",
                "implementation": "Ensure torch with CUDA support is installed",
            })

        # Batch processing strategy
        recommendations.append({
            "optimization": "Adaptive Batch Sizing",
            "description": "Adjust batch size based on input text count",
            "expected_improvement": "5-10% improvement for variable workloads",
            "effort": "medium",
            "priority": "low",
            "implementation": "Add logic to select batch_size based on len(texts)",
        })

        return recommendations

    def run_profiling(self) -> dict[str, Any]:
        """Run complete profiling suite across all batch sizes.

        Returns:
            Complete profiling results including metrics and analysis
        """
        logger.info("Starting batch size profiling...")
        logger.info(f"Test configuration: {len(self.test_texts)} texts")
        logger.info(f"Device: {self.service.get_device()}")

        # Warmup
        self.warmup()

        # Profile each batch size
        for batch_size in self.batch_sizes:
            result = self.profile_batch_size(batch_size)
            self.results["batch_results"].append(result)

            # Short pause between tests
            time.sleep(0.5)

        # Analyze results
        self.results["bottlenecks"] = self.analyze_bottlenecks()
        self.results["recommendations"] = self.generate_recommendations()

        # Add metadata
        self.results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "device": self.service.get_device(),
            "model": EmbeddingService.MODEL_NAME,
            "embedding_dimension": EmbeddingService.EMBEDDING_DIMENSION,
            "num_test_texts": len(self.test_texts),
            "batch_sizes_tested": self.batch_sizes,
            "python_version": sys.version.split()[0],
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
        }

        logger.info("\n" + "="*60)
        logger.info("PROFILING COMPLETE")
        logger.info("="*60)

        return self.results

    def save_results(self, output_path: Path) -> None:
        """Save profiling results to JSON file.

        Args:
            output_path: Path to save results JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to: {output_path}")

    def print_summary(self) -> None:
        """Print a summary of profiling results to console."""
        print("\n" + "="*60)
        print("PROFILING SUMMARY")
        print("="*60)
        print(f"\nDevice: {self.results['metadata']['device']}")
        print(f"Test size: {self.results['metadata']['num_test_texts']} texts")
        print(f"\nBatch Size Performance:")
        print(f"{'Batch':>8} {'Throughput':>15} {'Latency':>12} {'Memory Δ':>12}")
        print(f"{'Size':>8} {'(texts/sec)':>15} {'(ms/text)':>12} {'(MB)':>12}")
        print("-" * 60)

        for result in self.results["batch_results"]:
            print(
                f"{result['batch_size']:>8} "
                f"{result['throughput_texts_per_sec']:>15.2f} "
                f"{result['latency_ms_per_text']:>12.3f} "
                f"{result['memory_delta_mb']:>12.1f}"
            )

        print(f"\n\nTop Bottlenecks:")
        for i, bottleneck in enumerate(self.results["bottlenecks"][:5], 1):
            print(f"\n{i}. {bottleneck['type'].upper()}")
            print(f"   Finding: {bottleneck['finding']}")
            print(f"   Metric: {bottleneck['metric']}")
            print(f"   Recommendation: {bottleneck['recommendation']}")

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
        logger.info("Using synthetic test data")
        return [f"Test claim number {i} for profiling the embedding service." for i in range(num_texts)]

    with open(test_claims_path) as f:
        data = json.load(f)

    # Extract claim texts
    claims = [claim["text"] for claim in data["claims"]]

    # Replicate to reach desired size
    texts = []
    while len(texts) < num_texts:
        texts.extend(claims)

    return texts[:num_texts]


def main() -> None:
    """Main entry point for batch size profiling."""
    parser = argparse.ArgumentParser(
        description="Profile EmbeddingService with different batch sizes"
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=1000,
        help="Number of texts to use for testing (default: 1000)",
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
    logger.info(f"Loaded {len(test_texts)} texts")

    # Create profiler
    profiler = BatchSizeProfiler(test_texts, batch_sizes=args.batch_sizes)

    # Run profiling
    results = profiler.run_profiling()

    # Save results
    output_dir = project_root / args.output
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"batch_size_profile_{timestamp}.json"
    profiler.save_results(output_path)

    # Print summary
    profiler.print_summary()

    logger.info(f"\nProfiling complete! Results saved to: {output_path}")


if __name__ == "__main__":
    main()
