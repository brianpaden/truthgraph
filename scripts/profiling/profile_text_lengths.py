"""Text length impact profiling for embedding service.

This script analyzes how text length affects embedding generation performance.
Understanding this relationship helps optimize text preprocessing and truncation strategies.

Usage:
    python scripts/profiling/profile_text_lengths.py [--batch-size 32] [--iterations 3]

Key measurements:
    - Throughput vs text length
    - Latency vs text length
    - Tokenization overhead
    - Optimal text length range

This helps determine:
    1. Whether to truncate long texts
    2. Optimal character limit for performance
    3. Tokenization vs inference time split
    4. Performance curve characteristics
"""

import argparse
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


class TextLengthProfiler:
    """Profiles the impact of text length on embedding performance.

    This class measures how text length affects throughput, latency, and
    resource usage to inform text preprocessing strategies.

    Attributes:
        service: The EmbeddingService singleton instance
        results: Dictionary storing profiling results
    """

    def __init__(self) -> None:
        """Initialize the text length profiler."""
        self.service = EmbeddingService.get_instance()
        self.results: dict[str, Any] = {
            "metadata": {},
            "length_results": [],
            "analysis": {},
            "recommendations": [],
        }

        logger.info("Initialized text length profiler")

    def generate_text_of_length(self, target_length: int) -> str:
        """Generate a text string of approximately target length.

        Args:
            target_length: Target length in characters

        Returns:
            Text string close to target length
        """
        base_text = (
            "This is a test sentence for evaluating embedding performance. "
            "The embedding service processes texts of varying lengths to generate "
            "semantic vector representations. Understanding how text length impacts "
            "performance helps optimize the system for production workloads. "
            "Longer texts require more tokenization and processing time. "
        )

        # Repeat base text to reach target length
        repetitions = (target_length // len(base_text)) + 1
        text = (base_text * repetitions)[:target_length]

        return text

    def create_test_corpus(
        self,
        length: int,
        num_texts: int = 500,
    ) -> list[str]:
        """Create a corpus of texts with specified length.

        Args:
            length: Target character length for each text
            num_texts: Number of texts to generate

        Returns:
            List of texts with consistent length
        """
        return [self.generate_text_of_length(length) for _ in range(num_texts)]

    def profile_text_length(
        self,
        text_length: int,
        batch_size: int = 32,
        num_texts: int = 500,
        iterations: int = 3,
    ) -> dict[str, Any]:
        """Profile performance with specific text length.

        Args:
            text_length: Character length of texts to test
            batch_size: Batch size for processing
            num_texts: Number of texts to process
            iterations: Number of iterations for averaging

        Returns:
            Dictionary with performance metrics for this text length
        """
        logger.info(f"\nProfiling text length: {text_length} characters")

        # Create test corpus
        texts = self.create_test_corpus(text_length, num_texts)
        actual_avg_length = sum(len(t) for t in texts) / len(texts)

        logger.info(f"  Generated {len(texts)} texts, avg length: {actual_avg_length:.1f} chars")

        # Track metrics across iterations
        throughputs = []
        latencies = []
        memories = []

        for iteration in range(iterations):
            # Memory baseline
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024

            # Run embedding generation
            start_time = time.perf_counter()

            embeddings = self.service.embed_batch(
                texts,
                batch_size=batch_size,
                show_progress=False,
            )

            elapsed_time = time.perf_counter() - start_time

            # Memory after
            mem_after = process.memory_info().rss / 1024 / 1024

            # Calculate metrics
            throughput = len(texts) / elapsed_time
            latency_per_text = (elapsed_time / len(texts)) * 1000  # ms
            memory_delta = mem_after - mem_before

            throughputs.append(throughput)
            latencies.append(latency_per_text)
            memories.append(memory_delta)

            logger.debug(f"  Iteration {iteration + 1}: {throughput:.2f} texts/sec")

            # Small delay between iterations
            time.sleep(0.1)

        # Calculate statistics
        avg_throughput = sum(throughputs) / len(throughputs)
        avg_latency = sum(latencies) / len(latencies)
        avg_memory = sum(memories) / len(memories)

        result = {
            "text_length_chars": text_length,
            "actual_avg_length": actual_avg_length,
            "num_texts": num_texts,
            "batch_size": batch_size,
            "iterations": iterations,
            "avg_throughput_texts_per_sec": avg_throughput,
            "avg_latency_ms_per_text": avg_latency,
            "avg_memory_delta_mb": avg_memory,
            "throughputs": throughputs,
            "latencies": latencies,
        }

        logger.info(f"  Avg throughput: {avg_throughput:.2f} texts/sec")
        logger.info(f"  Avg latency: {avg_latency:.3f} ms/text")

        return result

    def analyze_results(self) -> dict[str, Any]:
        """Analyze text length impact on performance.

        Returns:
            Dictionary with analysis findings
        """
        logger.info("\n" + "="*60)
        logger.info("ANALYZING TEXT LENGTH IMPACT")
        logger.info("="*60)

        length_results = self.results["length_results"]

        if len(length_results) < 2:
            logger.warning("Not enough data points for analysis")
            return {}

        # Extract data for analysis
        lengths = [r["text_length_chars"] for r in length_results]
        throughputs = [r["avg_throughput_texts_per_sec"] for r in length_results]
        latencies = [r["avg_latency_ms_per_text"] for r in length_results]

        # Find best and worst performance
        best_idx = throughputs.index(max(throughputs))
        worst_idx = throughputs.index(min(throughputs))

        best_result = length_results[best_idx]
        worst_result = length_results[worst_idx]

        # Calculate performance degradation
        performance_drop = (
            (best_result["avg_throughput_texts_per_sec"] - worst_result["avg_throughput_texts_per_sec"])
            / best_result["avg_throughput_texts_per_sec"]
        ) * 100

        # Estimate relationship (linear approximation)
        # Calculate correlation between length and throughput
        mean_length = sum(lengths) / len(lengths)
        mean_throughput = sum(throughputs) / len(throughputs)

        numerator = sum((lengths[i] - mean_length) * (throughputs[i] - mean_throughput) for i in range(len(lengths)))
        denominator_x = sum((lengths[i] - mean_length) ** 2 for i in range(len(lengths)))
        denominator_y = sum((throughputs[i] - mean_throughput) ** 2 for i in range(len(throughputs)))

        if denominator_x > 0 and denominator_y > 0:
            correlation = numerator / ((denominator_x * denominator_y) ** 0.5)
        else:
            correlation = 0

        analysis = {
            "best_performance": {
                "text_length": best_result["text_length_chars"],
                "throughput": best_result["avg_throughput_texts_per_sec"],
                "latency": best_result["avg_latency_ms_per_text"],
            },
            "worst_performance": {
                "text_length": worst_result["text_length_chars"],
                "throughput": worst_result["avg_throughput_texts_per_sec"],
                "latency": worst_result["avg_latency_ms_per_text"],
            },
            "performance_drop_percent": performance_drop,
            "length_throughput_correlation": correlation,
            "relationship": "strong_negative" if correlation < -0.7 else "moderate_negative" if correlation < -0.3 else "weak",
        }

        logger.info(f"\nBest performance: {best_result['text_length_chars']} chars")
        logger.info(f"  Throughput: {best_result['avg_throughput_texts_per_sec']:.2f} texts/sec")

        logger.info(f"\nWorst performance: {worst_result['text_length_chars']} chars")
        logger.info(f"  Throughput: {worst_result['avg_throughput_texts_per_sec']:.2f} texts/sec")

        logger.info(f"\nPerformance drop: {performance_drop:.1f}%")
        logger.info(f"Correlation: {correlation:.3f} ({analysis['relationship']})")

        return analysis

    def generate_recommendations(self) -> list[dict[str, Any]]:
        """Generate recommendations based on text length profiling.

        Returns:
            List of actionable recommendations
        """
        recommendations = []
        analysis = self.results.get("analysis", {})

        if not analysis:
            return recommendations

        best_perf = analysis.get("best_performance", {})
        worst_perf = analysis.get("worst_performance", {})
        perf_drop = analysis.get("performance_drop_percent", 0)

        # Recommend text truncation if long texts are slow
        if perf_drop > 30:
            optimal_length = best_perf.get("text_length", 256)
            recommendations.append({
                "optimization": "Text Truncation",
                "description": f"Truncate texts to {optimal_length} characters for optimal performance",
                "expected_improvement": f"{perf_drop:.1f}% throughput improvement for long texts",
                "effort": "low",
                "priority": "high",
                "implementation": f"Add text[:{optimal_length}] preprocessing step",
            })

        # Recommend optimal range
        length_results = self.results["length_results"]
        good_performers = [
            r for r in length_results
            if r["avg_throughput_texts_per_sec"] >= best_perf.get("throughput", 0) * 0.9
        ]

        if good_performers:
            max_good_length = max(r["text_length_chars"] for r in good_performers)
            recommendations.append({
                "optimization": "Optimal Text Length Range",
                "description": f"Process texts up to {max_good_length} characters without significant performance impact",
                "expected_improvement": "Maintains >90% of peak performance",
                "effort": "low",
                "priority": "medium",
                "implementation": f"Set max_length={max_good_length} in preprocessing",
            })

        # Check if very short texts are also inefficient
        if len(length_results) > 0:
            shortest_result = min(length_results, key=lambda x: x["text_length_chars"])
            if shortest_result["avg_throughput_texts_per_sec"] < best_perf.get("throughput", 0) * 0.8:
                recommendations.append({
                    "optimization": "Minimum Text Length",
                    "description": "Very short texts may have overhead; consider batching or padding",
                    "expected_improvement": "5-10% improvement for short texts",
                    "effort": "medium",
                    "priority": "low",
                    "implementation": "Batch short texts together or pad to minimum length",
                })

        return recommendations

    def run_profiling(
        self,
        text_lengths: list[int] | None = None,
        batch_size: int = 32,
        num_texts: int = 500,
        iterations: int = 3,
    ) -> dict[str, Any]:
        """Run complete text length profiling suite.

        Args:
            text_lengths: List of text lengths to test (characters)
            batch_size: Batch size for processing
            num_texts: Number of texts per length test
            iterations: Number of iterations per test

        Returns:
            Complete profiling results
        """
        if text_lengths is None:
            text_lengths = [10, 50, 100, 256, 512, 1024]

        logger.info("Starting text length profiling...")
        logger.info(f"Text lengths: {text_lengths}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Texts per test: {num_texts}")
        logger.info(f"Iterations: {iterations}")

        # Profile each text length
        for length in text_lengths:
            result = self.profile_text_length(
                text_length=length,
                batch_size=batch_size,
                num_texts=num_texts,
                iterations=iterations,
            )
            self.results["length_results"].append(result)

        # Analyze results
        analysis = self.analyze_results()
        self.results["analysis"] = analysis

        # Generate recommendations
        recommendations = self.generate_recommendations()
        self.results["recommendations"] = recommendations

        # Add metadata
        self.results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "device": self.service.get_device(),
            "model": EmbeddingService.MODEL_NAME,
            "batch_size": batch_size,
            "num_texts_per_test": num_texts,
            "iterations": iterations,
            "text_lengths_tested": text_lengths,
        }

        logger.info("\nText length profiling complete!")

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
        """Print text length profiling summary to console."""
        print("\n" + "="*60)
        print("TEXT LENGTH PROFILING SUMMARY")
        print("="*60)

        print(f"\nDevice: {self.results['metadata']['device']}")
        print(f"Batch size: {self.results['metadata']['batch_size']}")

        print(f"\nPerformance by Text Length:")
        print(f"{'Length':>10} {'Throughput':>15} {'Latency':>12} {'Memory Δ':>12}")
        print(f"{'(chars)':>10} {'(texts/sec)':>15} {'(ms/text)':>12} {'(MB)':>12}")
        print("-" * 60)

        for result in self.results["length_results"]:
            print(
                f"{result['text_length_chars']:>10} "
                f"{result['avg_throughput_texts_per_sec']:>15.2f} "
                f"{result['avg_latency_ms_per_text']:>12.3f} "
                f"{result['avg_memory_delta_mb']:>12.1f}"
            )

        # Analysis summary
        analysis = self.results.get("analysis", {})
        if analysis:
            print(f"\n\nAnalysis:")
            best = analysis.get("best_performance", {})
            worst = analysis.get("worst_performance", {})

            print(f"  Best: {best.get('text_length', 0)} chars @ {best.get('throughput', 0):.2f} texts/sec")
            print(f"  Worst: {worst.get('text_length', 0)} chars @ {worst.get('throughput', 0):.2f} texts/sec")
            print(f"  Performance drop: {analysis.get('performance_drop_percent', 0):.1f}%")
            print(f"  Relationship: {analysis.get('relationship', 'unknown')}")

        # Recommendations
        recommendations = self.results.get("recommendations", [])
        if recommendations:
            print(f"\n\nTop Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"\n{i}. {rec['optimization']}")
                print(f"   {rec['description']}")
                print(f"   Expected: {rec['expected_improvement']}")
                print(f"   Effort: {rec['effort']}, Priority: {rec['priority']}")

        print("\n" + "="*60)


def main() -> None:
    """Main entry point for text length profiling."""
    parser = argparse.ArgumentParser(
        description="Profile impact of text length on embedding performance"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size to use for testing (default: 32)",
    )
    parser.add_argument(
        "--num-texts",
        type=int,
        default=500,
        help="Number of texts per length test (default: 500)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per test (default: 3)",
    )
    parser.add_argument(
        "--text-lengths",
        type=int,
        nargs="+",
        default=[10, 50, 100, 256, 512, 1024],
        help="Text lengths to test in characters (default: 10 50 100 256 512 1024)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/profiling/results",
        help="Output directory for results (default: scripts/profiling/results)",
    )

    args = parser.parse_args()

    # Create profiler
    profiler = TextLengthProfiler()

    # Run profiling
    results = profiler.run_profiling(
        text_lengths=args.text_lengths,
        batch_size=args.batch_size,
        num_texts=args.num_texts,
        iterations=args.iterations,
    )

    # Save results
    output_dir = project_root / args.output
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"text_length_profile_{timestamp}.json"
    profiler.save_results(output_path)

    # Print summary
    profiler.print_summary()

    logger.info(f"\nText length profiling complete! Results saved to: {output_path}")


if __name__ == "__main__":
    main()
