"""NLI Service Profiling Script.

This script profiles the NLI service for throughput, latency, and memory usage
across different batch sizes. It identifies bottlenecks and provides recommendations
for optimal performance.

Usage:
    python scripts/profiling/profile_nli.py [--batch-sizes 1,4,8,16,32] [--num-pairs 100]

Example:
    python scripts/profiling/profile_nli.py --batch-sizes 1,4,8,16,32 --num-pairs 100
"""

import argparse
import cProfile
import gc
import json
import pstats
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import psutil
import structlog

from truthgraph.services.ml.nli_service import NLILabel, get_nli_service

logger = structlog.get_logger(__name__)


class NLIProfiler:
    """Profiler for NLI service performance analysis.

    This class provides comprehensive profiling of NLI inference including:
    - Throughput measurement (pairs/sec)
    - Latency analysis (ms/pair)
    - Memory usage tracking
    - Batch size optimization
    - Accuracy validation
    - Bottleneck identification

    Attributes:
        service: NLI service instance
        test_pairs: List of (premise, hypothesis) pairs for testing
        results: Dictionary storing profiling results
    """

    def __init__(self) -> None:
        """Initialize the NLI profiler."""
        self.service = get_nli_service()
        self.test_pairs: list[tuple[str, str]] = []
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "batch_profiles": [],
            "bottlenecks": [],
            "recommendations": [],
        }

    def load_test_data(self, num_pairs: int = 100) -> None:
        """Load or generate test NLI pairs.

        Creates realistic test pairs with varied lengths and relationships.

        Args:
            num_pairs: Number of test pairs to generate
        """
        logger.info("loading_test_data", num_pairs=num_pairs)

        # Generate diverse test pairs with different relationships
        premises = [
            "The Earth orbits around the Sun.",
            "Paris is the capital of France.",
            "Water freezes at 0 degrees Celsius.",
            "The Pacific Ocean is the largest ocean on Earth.",
            "Mount Everest is the highest mountain in the world.",
            "The speed of light is approximately 299,792 kilometers per second.",
            "DNA contains genetic information.",
            "The human body has 206 bones.",
            "Shakespeare wrote Romeo and Juliet.",
            "The Great Wall of China is visible from space.",
        ]

        hypotheses_entailment = [
            "The Sun is at the center of our solar system.",
            "France has a capital city named Paris.",
            "Water becomes solid at zero degrees Celsius.",
            "The Pacific is Earth's biggest ocean.",
            "Mount Everest has the highest elevation globally.",
            "Light travels at about 300,000 km/s.",
            "Genetic data is stored in DNA.",
            "Adult humans typically have over 200 bones.",
            "Romeo and Juliet was written by Shakespeare.",
            "Astronauts can see the Great Wall from orbit.",
        ]

        hypotheses_contradiction = [
            "The Sun orbits around the Earth.",
            "London is the capital of France.",
            "Water boils at 0 degrees Celsius.",
            "The Atlantic Ocean is larger than the Pacific.",
            "K2 is taller than Mount Everest.",
            "Light travels slower than sound.",
            "DNA is not related to genetics.",
            "Humans have fewer than 100 bones.",
            "Charles Dickens wrote Romeo and Juliet.",
            "The Great Wall is invisible from any distance.",
        ]

        hypotheses_neutral = [
            "Mars has two moons.",
            "The Eiffel Tower is in Paris.",
            "Ice cream is delicious.",
            "Coral reefs are diverse ecosystems.",
            "Mount Kilimanjaro is in Africa.",
            "Einstein developed the theory of relativity.",
            "Proteins are made of amino acids.",
            "The heart pumps blood.",
            "The Mona Lisa is displayed in the Louvre.",
            "Birds can fly.",
        ]

        self.test_pairs = []

        # Create balanced dataset with all three relationships
        for i in range(num_pairs):
            premise_idx = i % len(premises)

            if i % 3 == 0:  # Entailment
                hypothesis = hypotheses_entailment[premise_idx]
            elif i % 3 == 1:  # Contradiction
                hypothesis = hypotheses_contradiction[premise_idx]
            else:  # Neutral
                hypothesis = hypotheses_neutral[premise_idx]

            self.test_pairs.append((premises[premise_idx], hypothesis))

        logger.info(
            "test_data_loaded",
            num_pairs=len(self.test_pairs),
            unique_premises=len(premises),
        )

    def capture_system_info(self) -> None:
        """Capture system information for the report."""
        import sys

        import torch

        model_info = self.service.get_model_info()

        self.results["system"] = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": model_info["device"],
            "model": self.service._model_name,
            "initialized": model_info["initialized"],
        }

        logger.info("system_info_captured", **self.results["system"])

    def warmup(self, num_iterations: int = 5) -> None:
        """Warmup the NLI model before profiling.

        Args:
            num_iterations: Number of warmup iterations
        """
        logger.info("warmup_start", iterations=num_iterations)

        if not self.test_pairs:
            self.load_test_data(10)

        for i in range(num_iterations):
            _ = self.service.verify_single(
                self.test_pairs[i % len(self.test_pairs)][0],
                self.test_pairs[i % len(self.test_pairs)][1],
            )

        gc.collect()
        logger.info("warmup_complete")

    def measure_memory(self) -> float:
        """Measure current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024

    def profile_batch_size(
        self,
        batch_size: int,
        num_pairs: int | None = None,
    ) -> dict[str, Any]:
        """Profile NLI inference at a specific batch size.

        Args:
            batch_size: Batch size to test
            num_pairs: Number of pairs to test (uses all if None)

        Returns:
            Dictionary with profiling results for this batch size
        """
        if num_pairs is None:
            test_pairs = self.test_pairs
        else:
            test_pairs = self.test_pairs[:num_pairs]

        num_pairs = len(test_pairs)

        logger.info(
            "profiling_batch_size",
            batch_size=batch_size,
            num_pairs=num_pairs,
        )

        # Memory before
        gc.collect()
        memory_before = self.measure_memory()

        # Profile with cProfile
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()

        # Run inference
        if batch_size == 1:
            # Single pair at a time
            results = []
            for premise, hypothesis in test_pairs:
                result = self.service.verify_single(premise, hypothesis)
                results.append(result)
        else:
            # Batch processing
            results = self.service.verify_batch(test_pairs, batch_size=batch_size)

        end_time = time.perf_counter()

        profiler.disable()

        # Memory after
        memory_after = self.measure_memory()
        gc.collect()
        memory_final = self.measure_memory()

        # Calculate metrics
        elapsed_time = end_time - start_time
        throughput = num_pairs / elapsed_time if elapsed_time > 0 else 0
        latency_ms = (elapsed_time / num_pairs) * 1000 if num_pairs > 0 else 0

        # Extract profiling stats
        stats_io = StringIO()
        stats = pstats.Stats(profiler, stream=stats_io)
        stats.sort_stats("cumulative")
        stats.print_stats(20)  # Top 20 functions

        profile_text = stats_io.getvalue()

        # Validate accuracy (check label distribution)
        label_counts = {
            NLILabel.ENTAILMENT.value: 0,
            NLILabel.CONTRADICTION.value: 0,
            NLILabel.NEUTRAL.value: 0,
        }

        confidence_sum = 0.0
        for result in results:
            label_counts[result.label.value] += 1
            confidence_sum += result.confidence

        avg_confidence = confidence_sum / len(results) if results else 0.0

        result_dict = {
            "batch_size": batch_size,
            "num_pairs": num_pairs,
            "elapsed_time_s": elapsed_time,
            "throughput_pairs_per_sec": throughput,
            "latency_ms_per_pair": latency_ms,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_final_mb": memory_final,
            "memory_delta_mb": memory_after - memory_before,
            "label_distribution": label_counts,
            "avg_confidence": avg_confidence,
            "profile_stats": profile_text[:1000],  # First 1000 chars
        }

        logger.info(
            "batch_profile_complete",
            batch_size=batch_size,
            throughput=f"{throughput:.2f}",
            latency_ms=f"{latency_ms:.2f}",
        )

        return result_dict

    def run_all_profiles(
        self,
        batch_sizes: list[int],
        num_pairs: int = 100,
    ) -> None:
        """Run profiling for all specified batch sizes.

        Args:
            batch_sizes: List of batch sizes to test
            num_pairs: Number of pairs to test per batch size
        """
        logger.info(
            "starting_profiling",
            batch_sizes=batch_sizes,
            num_pairs=num_pairs,
        )

        # Load test data
        self.load_test_data(num_pairs)

        # Capture system info
        self.capture_system_info()

        # Warmup
        self.warmup()

        # Profile each batch size
        for batch_size in batch_sizes:
            result = self.profile_batch_size(batch_size, num_pairs)
            self.results["batch_profiles"].append(result)

            # Small delay between runs
            time.sleep(0.5)
            gc.collect()

        # Analyze results
        self.analyze_results()

    def analyze_results(self) -> None:
        """Analyze profiling results to identify bottlenecks and generate recommendations."""
        if not self.results["batch_profiles"]:
            logger.warning("no_results_to_analyze")
            return

        profiles = self.results["batch_profiles"]

        # Find best throughput
        best_throughput = max(p["throughput_pairs_per_sec"] for p in profiles)
        best_batch = next(p for p in profiles if p["throughput_pairs_per_sec"] == best_throughput)

        # Find most memory efficient
        min_memory = min(p["memory_delta_mb"] for p in profiles)
        memory_efficient = next(p for p in profiles if p["memory_delta_mb"] == min_memory)

        # Identify bottlenecks
        bottlenecks = []

        # Check if small batches are inefficient
        batch_1 = next((p for p in profiles if p["batch_size"] == 1), None)
        if batch_1 and best_batch["batch_size"] > 1:
            improvement = (
                (best_batch["throughput_pairs_per_sec"] - batch_1["throughput_pairs_per_sec"])
                / batch_1["throughput_pairs_per_sec"]
                * 100
            )
            if improvement > 50:
                bottlenecks.append(
                    {
                        "type": "small_batch_overhead",
                        "severity": "high",
                        "description": f"Single-pair processing is {improvement:.1f}% slower than optimal batch size",
                        "evidence": {
                            "batch_1_throughput": batch_1["throughput_pairs_per_sec"],
                            "optimal_throughput": best_batch["throughput_pairs_per_sec"],
                            "optimal_batch_size": best_batch["batch_size"],
                        },
                    }
                )

        # Check memory scaling
        max_memory = max(p["memory_delta_mb"] for p in profiles)
        if max_memory > 100:  # If memory delta exceeds 100MB
            bottlenecks.append(
                {
                    "type": "memory_scaling",
                    "severity": "medium",
                    "description": f"Memory usage increases to {max_memory:.1f} MB at large batch sizes",
                    "evidence": {
                        "min_memory_mb": min_memory,
                        "max_memory_mb": max_memory,
                        "memory_scaling_factor": max_memory / min_memory if min_memory > 0 else 0,
                    },
                }
            )

        # Check if target met
        target_throughput = 2.0  # pairs/sec
        if best_throughput < target_throughput:
            bottlenecks.append(
                {
                    "type": "performance_target_miss",
                    "severity": "critical",
                    "description": f"Target throughput of {target_throughput} pairs/sec not met",
                    "evidence": {
                        "target": target_throughput,
                        "achieved": best_throughput,
                        "shortfall": target_throughput - best_throughput,
                    },
                }
            )

        self.results["bottlenecks"] = bottlenecks

        # Generate recommendations
        recommendations = []

        # Recommend optimal batch size
        recommendations.append(
            {
                "priority": "high",
                "title": "Use Optimal Batch Size",
                "description": f"Use batch_size={best_batch['batch_size']} for maximum throughput",
                "expected_impact": f"{best_throughput:.2f} pairs/sec",
                "implementation": f"Set batch_size={best_batch['batch_size']} in verify_batch() calls",
            }
        )

        # Memory-aware recommendation
        if memory_efficient["batch_size"] != best_batch["batch_size"]:
            recommendations.append(
                {
                    "priority": "medium",
                    "title": "Memory-Efficient Batch Size",
                    "description": f"For memory-constrained environments, use batch_size={memory_efficient['batch_size']}",
                    "expected_impact": f"{memory_efficient['throughput_pairs_per_sec']:.2f} pairs/sec with {memory_efficient['memory_delta_mb']:.1f} MB memory",
                    "implementation": f"Set batch_size={memory_efficient['batch_size']} when memory is limited",
                }
            )

        # Input length optimization
        recommendations.append(
            {
                "priority": "medium",
                "title": "Truncate Long Inputs",
                "description": "Truncate premises and hypotheses to 256 tokens to reduce processing time",
                "expected_impact": "10-30% improvement for long texts",
                "implementation": "Add max_length=256 to preprocessing step",
            }
        )

        self.results["recommendations"] = recommendations

        logger.info(
            "analysis_complete",
            num_bottlenecks=len(bottlenecks),
            num_recommendations=len(recommendations),
        )

    def save_results(self, output_path: str | Path) -> None:
        """Save profiling results to JSON file.

        Args:
            output_path: Path to save results JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info("results_saved", path=str(output_path))

    def print_summary(self) -> None:
        """Print a summary of profiling results to console."""
        print("\n" + "=" * 80)
        print("NLI PROFILING SUMMARY")
        print("=" * 80)

        print(
            f"\nSystem: {self.results['system']['device']} | Model: {self.results['system']['model']}"
        )

        print("\nBatch Size Performance:")
        print("-" * 80)
        print(f"{'Batch':>6} | {'Pairs/Sec':>12} | {'Latency (ms)':>14} | {'Memory (MB)':>13}")
        print("-" * 80)

        for profile in self.results["batch_profiles"]:
            print(
                f"{profile['batch_size']:>6} | "
                f"{profile['throughput_pairs_per_sec']:>12.2f} | "
                f"{profile['latency_ms_per_pair']:>14.2f} | "
                f"{profile['memory_delta_mb']:>13.1f}"
            )

        if self.results["bottlenecks"]:
            print("\nBottlenecks Identified:")
            print("-" * 80)
            for i, bottleneck in enumerate(self.results["bottlenecks"], 1):
                print(f"{i}. [{bottleneck['severity'].upper()}] {bottleneck['description']}")

        if self.results["recommendations"]:
            print("\nRecommendations:")
            print("-" * 80)
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"{i}. [{rec['priority'].upper()}] {rec['title']}")
                print(f"   Impact: {rec['expected_impact']}")

        print("\n" + "=" * 80)


def main() -> None:
    """Main entry point for NLI profiling script."""
    parser = argparse.ArgumentParser(description="Profile NLI service performance")
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default="1,4,8,16,32",
        help="Comma-separated list of batch sizes to test (default: 1,4,8,16,32)",
    )
    parser.add_argument(
        "--num-pairs",
        type=int,
        default=100,
        help="Number of test pairs to use (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for results JSON (default: scripts/profiling/results/nli_profile_YYYY-MM-DD.json)",
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Default output path
    if args.output is None:
        today = datetime.now().strftime("%Y-%m-%d")
        args.output = f"scripts/profiling/results/nli_profile_{today}.json"

    # Run profiling
    profiler = NLIProfiler()
    profiler.run_all_profiles(batch_sizes, args.num_pairs)

    # Print summary
    profiler.print_summary()

    # Save results
    profiler.save_results(args.output)

    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
