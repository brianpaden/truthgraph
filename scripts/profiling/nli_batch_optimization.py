"""NLI Batch Size Optimization Script.

This script performs detailed analysis of batch size impact on NLI inference,
including accuracy validation, memory profiling, and performance trade-offs.

Usage:
    python scripts/profiling/nli_batch_optimization.py [--batch-sizes 1,4,8,16,32]

Example:
    python scripts/profiling/nli_batch_optimization.py --batch-sizes 1,4,8,16,32 --validate-accuracy
"""

import argparse
import gc
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import structlog

from truthgraph.services.ml.nli_service import NLILabel, get_nli_service

logger = structlog.get_logger(__name__)


class BatchOptimizer:
    """Optimizer for NLI batch size selection.

    This class analyzes the trade-offs between batch size, throughput,
    latency, memory usage, and accuracy to find optimal configurations.

    Attributes:
        service: NLI service instance
        test_pairs: Test data for profiling
        ground_truth: Expected labels for accuracy validation
        results: Dictionary storing optimization results
    """

    def __init__(self) -> None:
        """Initialize the batch optimizer."""
        self.service = get_nli_service()
        self.test_pairs: list[tuple[str, str]] = []
        self.ground_truth: list[NLILabel] = []
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "batch_analyses": [],
            "accuracy_validation": {},
            "optimal_configs": {},
        }

    def create_test_dataset(self, num_pairs: int = 100) -> None:
        """Create test dataset with known ground truth labels.

        Args:
            num_pairs: Number of test pairs to generate
        """
        logger.info("creating_test_dataset", num_pairs=num_pairs)

        # Entailment pairs
        entailment_pairs = [
            (
                "The Earth revolves around the Sun.",
                "Our planet orbits the Sun.",
                NLILabel.ENTAILMENT,
            ),
            (
                "Paris is the capital of France.",
                "France's capital city is Paris.",
                NLILabel.ENTAILMENT,
            ),
            (
                "Water boils at 100 degrees Celsius at sea level.",
                "At standard pressure, water reaches boiling point at 100°C.",
                NLILabel.ENTAILMENT,
            ),
            (
                "The Pacific Ocean is the largest ocean.",
                "No ocean is larger than the Pacific.",
                NLILabel.ENTAILMENT,
            ),
            (
                "Mount Everest is 8,849 meters tall.",
                "Mount Everest's height exceeds 8,800 meters.",
                NLILabel.ENTAILMENT,
            ),
        ]

        # Contradiction pairs
        contradiction_pairs = [
            (
                "The Earth is flat.",
                "The Earth is spherical.",
                NLILabel.CONTRADICTION,
            ),
            (
                "London is the capital of France.",
                "Paris is the capital of France.",
                NLILabel.CONTRADICTION,
            ),
            (
                "Water freezes at 100 degrees Celsius.",
                "Water freezes at 0 degrees Celsius.",
                NLILabel.CONTRADICTION,
            ),
            (
                "The Atlantic is larger than the Pacific.",
                "The Pacific Ocean is the largest ocean.",
                NLILabel.CONTRADICTION,
            ),
            (
                "K2 is taller than Everest.",
                "Mount Everest is the highest mountain.",
                NLILabel.CONTRADICTION,
            ),
        ]

        # Neutral pairs
        neutral_pairs = [
            (
                "The Earth orbits the Sun.",
                "Mars has two moons.",
                NLILabel.NEUTRAL,
            ),
            (
                "Paris is the capital of France.",
                "The Eiffel Tower is 330 meters tall.",
                NLILabel.NEUTRAL,
            ),
            (
                "Water is made of H2O.",
                "Ice cream tastes good.",
                NLILabel.NEUTRAL,
            ),
            (
                "The Pacific Ocean is very deep.",
                "Dolphins are intelligent mammals.",
                NLILabel.NEUTRAL,
            ),
            (
                "Mountains are formed by tectonic activity.",
                "Rivers flow downhill.",
                NLILabel.NEUTRAL,
            ),
        ]

        # Build dataset
        self.test_pairs = []
        self.ground_truth = []

        all_pairs = entailment_pairs + contradiction_pairs + neutral_pairs

        for i in range(num_pairs):
            premise, hypothesis, label = all_pairs[i % len(all_pairs)]
            self.test_pairs.append((premise, hypothesis))
            self.ground_truth.append(label)

        logger.info(
            "test_dataset_created",
            total_pairs=len(self.test_pairs),
            entailment_count=sum(1 for l in self.ground_truth if l == NLILabel.ENTAILMENT),
            contradiction_count=sum(1 for l in self.ground_truth if l == NLILabel.CONTRADICTION),
            neutral_count=sum(1 for l in self.ground_truth if l == NLILabel.NEUTRAL),
        )

    def measure_memory(self) -> float:
        """Measure current process memory in MB.

        Returns:
            Memory usage in megabytes
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def analyze_batch_size(
        self,
        batch_size: int,
        validate_accuracy: bool = True,
    ) -> dict[str, Any]:
        """Analyze performance and accuracy for a specific batch size.

        Args:
            batch_size: Batch size to analyze
            validate_accuracy: Whether to validate accuracy

        Returns:
            Dictionary with analysis results
        """
        logger.info(
            "analyzing_batch_size",
            batch_size=batch_size,
            validate_accuracy=validate_accuracy,
        )

        # Memory baseline
        gc.collect()
        memory_before = self.measure_memory()

        # Throughput test
        start_time = time.perf_counter()

        if batch_size == 1:
            results = []
            for premise, hypothesis in self.test_pairs:
                result = self.service.verify_single(premise, hypothesis)
                results.append(result)
        else:
            results = self.service.verify_batch(self.test_pairs, batch_size=batch_size)

        end_time = time.perf_counter()

        # Memory after
        memory_after = self.measure_memory()
        gc.collect()

        # Calculate metrics
        elapsed = end_time - start_time
        throughput = len(self.test_pairs) / elapsed if elapsed > 0 else 0
        latency_ms = (elapsed / len(self.test_pairs)) * 1000

        # Accuracy validation
        accuracy_metrics = {}
        if validate_accuracy:
            correct = 0
            total = len(results)

            label_confusion: dict[str, dict[str, int]] = {
                NLILabel.ENTAILMENT.value: {
                    NLILabel.ENTAILMENT.value: 0,
                    NLILabel.CONTRADICTION.value: 0,
                    NLILabel.NEUTRAL.value: 0,
                },
                NLILabel.CONTRADICTION.value: {
                    NLILabel.ENTAILMENT.value: 0,
                    NLILabel.CONTRADICTION.value: 0,
                    NLILabel.NEUTRAL.value: 0,
                },
                NLILabel.NEUTRAL.value: {
                    NLILabel.ENTAILMENT.value: 0,
                    NLILabel.CONTRADICTION.value: 0,
                    NLILabel.NEUTRAL.value: 0,
                },
            }

            confidence_sum = 0.0

            for i, result in enumerate(results):
                predicted = result.label
                expected = self.ground_truth[i]

                if predicted == expected:
                    correct += 1

                label_confusion[expected.value][predicted.value] += 1
                confidence_sum += result.confidence

            accuracy = correct / total if total > 0 else 0
            avg_confidence = confidence_sum / total if total > 0 else 0

            accuracy_metrics = {
                "accuracy": accuracy,
                "correct": correct,
                "total": total,
                "avg_confidence": avg_confidence,
                "confusion_matrix": label_confusion,
            }

        analysis = {
            "batch_size": batch_size,
            "num_pairs": len(self.test_pairs),
            "elapsed_time_s": elapsed,
            "throughput_pairs_per_sec": throughput,
            "latency_ms_per_pair": latency_ms,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_delta_mb": memory_after - memory_before,
            "accuracy_metrics": accuracy_metrics,
        }

        logger.info(
            "batch_analysis_complete",
            batch_size=batch_size,
            throughput=f"{throughput:.2f}",
            accuracy=f"{accuracy_metrics.get('accuracy', 0):.4f}" if accuracy_metrics else "N/A",
        )

        return analysis

    def run_optimization(
        self,
        batch_sizes: list[int],
        num_pairs: int = 100,
        validate_accuracy: bool = True,
    ) -> None:
        """Run optimization analysis for all batch sizes.

        Args:
            batch_sizes: List of batch sizes to test
            num_pairs: Number of test pairs to use
            validate_accuracy: Whether to validate accuracy
        """
        logger.info(
            "starting_optimization",
            batch_sizes=batch_sizes,
            num_pairs=num_pairs,
        )

        # Create test dataset
        self.create_test_dataset(num_pairs)

        # Warmup
        logger.info("warmup_start")
        for i in range(3):
            _ = self.service.verify_single(
                self.test_pairs[i][0],
                self.test_pairs[i][1],
            )
        gc.collect()
        logger.info("warmup_complete")

        # Analyze each batch size
        for batch_size in batch_sizes:
            analysis = self.analyze_batch_size(batch_size, validate_accuracy)
            self.results["batch_analyses"].append(analysis)

            # Small delay
            time.sleep(0.5)
            gc.collect()

        # Compute optimal configurations
        self.compute_optimal_configs()

    def compute_optimal_configs(self) -> None:
        """Compute optimal batch size configurations for different scenarios."""
        if not self.results["batch_analyses"]:
            return

        analyses = self.results["batch_analyses"]

        # Best throughput
        best_throughput = max(a["throughput_pairs_per_sec"] for a in analyses)
        best_throughput_config = next(
            a for a in analyses if a["throughput_pairs_per_sec"] == best_throughput
        )

        # Best latency (lowest ms/pair)
        best_latency = min(a["latency_ms_per_pair"] for a in analyses)
        best_latency_config = next(a for a in analyses if a["latency_ms_per_pair"] == best_latency)

        # Most memory efficient
        min_memory = min(a["memory_delta_mb"] for a in analyses)
        memory_efficient_config = next(a for a in analyses if a["memory_delta_mb"] == min_memory)

        # Balanced config (good throughput, acceptable memory)
        balanced_scores = []
        for a in analyses:
            # Normalize metrics (0-1 scale)
            throughput_score = a["throughput_pairs_per_sec"] / best_throughput
            memory_score = 1 - (a["memory_delta_mb"] / max(x["memory_delta_mb"] for x in analyses))
            # Weighted average: 70% throughput, 30% memory
            balanced_score = 0.7 * throughput_score + 0.3 * memory_score
            balanced_scores.append((balanced_score, a))

        balanced_config = max(balanced_scores, key=lambda x: x[0])[1]

        self.results["optimal_configs"] = {
            "maximum_throughput": {
                "batch_size": best_throughput_config["batch_size"],
                "throughput_pairs_per_sec": best_throughput_config["throughput_pairs_per_sec"],
                "latency_ms": best_throughput_config["latency_ms_per_pair"],
                "memory_mb": best_throughput_config["memory_delta_mb"],
            },
            "minimum_latency": {
                "batch_size": best_latency_config["batch_size"],
                "throughput_pairs_per_sec": best_latency_config["throughput_pairs_per_sec"],
                "latency_ms": best_latency_config["latency_ms_per_pair"],
                "memory_mb": best_latency_config["memory_delta_mb"],
            },
            "memory_efficient": {
                "batch_size": memory_efficient_config["batch_size"],
                "throughput_pairs_per_sec": memory_efficient_config["throughput_pairs_per_sec"],
                "latency_ms": memory_efficient_config["latency_ms_per_pair"],
                "memory_mb": memory_efficient_config["memory_delta_mb"],
            },
            "balanced": {
                "batch_size": balanced_config["batch_size"],
                "throughput_pairs_per_sec": balanced_config["throughput_pairs_per_sec"],
                "latency_ms": balanced_config["latency_ms_per_pair"],
                "memory_mb": balanced_config["memory_delta_mb"],
            },
        }

        # Accuracy validation summary
        if any(a.get("accuracy_metrics") for a in analyses):
            accuracy_summary = {}
            for a in analyses:
                if a.get("accuracy_metrics"):
                    accuracy_summary[f"batch_{a['batch_size']}"] = {
                        "accuracy": a["accuracy_metrics"]["accuracy"],
                        "avg_confidence": a["accuracy_metrics"]["avg_confidence"],
                    }
            self.results["accuracy_validation"] = accuracy_summary

        logger.info("optimal_configs_computed")

    def save_results(self, output_path: str | Path) -> None:
        """Save optimization results to JSON file.

        Args:
            output_path: Path to save results
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info("results_saved", path=str(output_path))

    def print_summary(self) -> None:
        """Print optimization summary to console."""
        print("\n" + "=" * 80)
        print("NLI BATCH OPTIMIZATION SUMMARY")
        print("=" * 80)

        print("\nBatch Size Analysis:")
        print("-" * 80)
        print(
            f"{'Batch':>6} | {'Pairs/Sec':>12} | {'Latency (ms)':>14} | {'Memory (MB)':>13} | {'Accuracy':>10}"
        )
        print("-" * 80)

        for analysis in self.results["batch_analyses"]:
            accuracy_str = "N/A"
            if analysis.get("accuracy_metrics"):
                accuracy_str = f"{analysis['accuracy_metrics']['accuracy']:.4f}"

            print(
                f"{analysis['batch_size']:>6} | "
                f"{analysis['throughput_pairs_per_sec']:>12.2f} | "
                f"{analysis['latency_ms_per_pair']:>14.2f} | "
                f"{analysis['memory_delta_mb']:>13.1f} | "
                f"{accuracy_str:>10}"
            )

        if self.results.get("optimal_configs"):
            print("\nOptimal Configurations:")
            print("-" * 80)

            configs = self.results["optimal_configs"]

            print(f"Maximum Throughput: batch_size={configs['maximum_throughput']['batch_size']}")
            print(f"  - {configs['maximum_throughput']['throughput_pairs_per_sec']:.2f} pairs/sec")

            print(f"\nBalanced (Recommended): batch_size={configs['balanced']['batch_size']}")
            print(f"  - {configs['balanced']['throughput_pairs_per_sec']:.2f} pairs/sec")
            print(f"  - {configs['balanced']['memory_mb']:.1f} MB memory")

            print(f"\nMemory Efficient: batch_size={configs['memory_efficient']['batch_size']}")
            print(f"  - {configs['memory_efficient']['throughput_pairs_per_sec']:.2f} pairs/sec")
            print(f"  - {configs['memory_efficient']['memory_mb']:.1f} MB memory")

        print("\n" + "=" * 80)


def main() -> None:
    """Main entry point for batch optimization script."""
    parser = argparse.ArgumentParser(description="Optimize NLI batch size")
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default="1,4,8,16,32",
        help="Comma-separated batch sizes to test (default: 1,4,8,16,32)",
    )
    parser.add_argument(
        "--num-pairs",
        type=int,
        default=100,
        help="Number of test pairs (default: 100)",
    )
    parser.add_argument(
        "--validate-accuracy",
        action="store_true",
        default=True,
        help="Validate accuracy at each batch size (default: True)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: scripts/profiling/results/nli_batch_analysis_YYYY-MM-DD.json)",
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Default output path
    if args.output is None:
        today = datetime.now().strftime("%Y-%m-%d")
        args.output = f"scripts/profiling/results/nli_batch_analysis_{today}.json"

    # Run optimization
    optimizer = BatchOptimizer()
    optimizer.run_optimization(batch_sizes, args.num_pairs, args.validate_accuracy)

    # Print summary
    optimizer.print_summary()

    # Save results
    optimizer.save_results(args.output)

    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
