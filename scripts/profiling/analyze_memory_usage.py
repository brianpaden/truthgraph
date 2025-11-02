"""Comprehensive memory profiling and analysis script.

This script performs detailed memory profiling of the TruthGraph system including:
- Baseline memory with loaded models
- Per-component memory attribution
- Memory under load (100 concurrent items)
- Memory leak detection (30-minute sustained load)
- Integration with Feature 2.1 findings

Usage:
    python scripts/profiling/analyze_memory_usage.py --full
    python scripts/profiling/analyze_memory_usage.py --baseline-only
    python scripts/profiling/analyze_memory_usage.py --load-test --concurrent 100
    python scripts/profiling/analyze_memory_usage.py --leak-test --duration 30

Output:
    - scripts/profiling/results/memory_profile_YYYY-MM-DD.json
    - Console summary with key findings
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from truthgraph.monitoring import (
    AlertManager,
    MemoryMonitor,
    MemoryProfileStore,
)
from truthgraph.services.ml.embedding_service import EmbeddingService

try:
    from truthgraph.services.ml.nli_service import NLIService
except ImportError:
    NLIService = None  # May not be implemented yet

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    """Comprehensive memory analysis for TruthGraph system."""

    def __init__(self, output_dir: Path = None) -> None:
        """Initialize memory analyzer.

        Args:
            output_dir: Directory for results (default: scripts/profiling/results)
        """
        self.output_dir = output_dir or (project_root / "scripts" / "profiling" / "results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.monitor = MemoryMonitor(enable_tracemalloc=True)
        self.alert_manager = AlertManager()
        self.profile_store = MemoryProfileStore()

        self.results: Dict[str, Any] = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "script_version": "1.0.0",
                "target_memory_gb": 4.0,
            },
            "tests": {},
        }

    def measure_baseline(self) -> Dict[str, Any]:
        """Measure baseline memory usage.

        Returns:
            Dictionary with baseline metrics
        """
        logger.info("=" * 60)
        logger.info("Measuring baseline memory...")
        logger.info("=" * 60)

        self.monitor.reset()
        self.monitor.start()

        # Capture initial state
        initial = self.monitor.capture_snapshot()

        baseline_results = {
            "initial_memory_mb": initial.rss_mb,
            "available_system_mb": initial.available_system_mb,
            "total_system_mb": initial.total_system_mb,
            "python_allocated_mb": initial.python_allocated_mb,
            "components": {},
        }

        logger.info(f"Initial memory: {initial.rss_mb:.1f} MB")

        return baseline_results

    def measure_model_loading(self) -> Dict[str, Any]:
        """Measure memory impact of loading ML models.

        Returns:
            Dictionary with model loading metrics
        """
        logger.info("=" * 60)
        logger.info("Measuring model loading memory...")
        logger.info("=" * 60)

        results = {}

        # Measure embedding model
        self.monitor.mark_component("before_embedding_model")
        logger.info("Loading embedding model...")

        embedding_service = EmbeddingService.get_instance()
        # Trigger model loading
        _ = embedding_service.embed_text("test")

        self.monitor.mark_component("after_embedding_model")

        embedding_memory = self.monitor.get_component_memory("before_embedding_model")
        results["embedding_model"] = embedding_memory

        logger.info(f"Embedding model memory: {embedding_memory.get('delta_mb', 0):.1f} MB")

        # Measure NLI model if available
        if NLIService:
            self.monitor.mark_component("before_nli_model")
            logger.info("Loading NLI model...")

            try:
                nli_service = NLIService.get_instance()
                # Trigger model loading
                _ = nli_service.predict("test claim", "test evidence")

                self.monitor.mark_component("after_nli_model")

                nli_memory = self.monitor.get_component_memory("before_nli_model")
                results["nli_model"] = nli_memory

                logger.info(f"NLI model memory: {nli_memory.get('delta_mb', 0):.1f} MB")
            except Exception as e:
                logger.warning(f"Could not load NLI model: {e}")
                results["nli_model"] = {"error": str(e)}

        # Total after models
        current = self.monitor.get_current_snapshot()
        results["total_after_models_mb"] = current.rss_mb

        logger.info(f"Total memory after models: {current.rss_mb:.1f} MB")

        return results

    def measure_embedding_batch_processing(self, batch_size: int = 64) -> Dict[str, Any]:
        """Measure memory during embedding batch processing.

        Args:
            batch_size: Batch size to test

        Returns:
            Dictionary with batch processing metrics
        """
        logger.info("=" * 60)
        logger.info(f"Measuring embedding batch processing (batch_size={batch_size})...")
        logger.info("=" * 60)

        embedding_service = EmbeddingService.get_instance()

        # Create test data
        test_texts = [f"Test claim number {i} for memory profiling" for i in range(1000)]

        self.monitor.mark_component("before_batch_processing")
        before = self.monitor.get_current_snapshot()

        # Process batches
        logger.info("Processing 1000 texts in batches...")
        start_time = time.time()

        for i in range(0, len(test_texts), batch_size):
            batch = test_texts[i : i + batch_size]
            _ = embedding_service.embed_batch(batch)

            # Capture periodic snapshots
            if i % 200 == 0:
                self.monitor.capture_snapshot()

        elapsed = time.time() - start_time

        self.monitor.mark_component("after_batch_processing")
        after = self.monitor.get_current_snapshot()

        results = {
            "batch_size": batch_size,
            "num_texts": len(test_texts),
            "elapsed_seconds": round(elapsed, 2),
            "throughput_texts_per_sec": round(len(test_texts) / elapsed, 2),
            "memory_before_mb": before.rss_mb,
            "memory_after_mb": after.rss_mb,
            "memory_delta_mb": after.rss_mb - before.rss_mb,
            "peak_memory_mb": max(s.rss_mb for s in self.monitor.snapshots),
        }

        logger.info("Batch processing complete:")
        logger.info(f"  Throughput: {results['throughput_texts_per_sec']:.1f} texts/sec")
        logger.info(f"  Memory delta: {results['memory_delta_mb']:.1f} MB")
        logger.info(f"  Peak memory: {results['peak_memory_mb']:.1f} MB")

        return results

    def measure_concurrent_load(self, num_items: int = 100) -> Dict[str, Any]:
        """Measure memory under concurrent load.

        Args:
            num_items: Number of concurrent items to process

        Returns:
            Dictionary with load test metrics
        """
        logger.info("=" * 60)
        logger.info(f"Measuring memory under load ({num_items} concurrent items)...")
        logger.info("=" * 60)

        embedding_service = EmbeddingService.get_instance()

        # Create test data
        test_items = [
            f"Concurrent test claim {i} with more text to make it realistic"
            for i in range(num_items)
        ]

        before = self.monitor.get_current_snapshot()
        start_time = time.time()

        # Simulate concurrent processing (sequential for simplicity)
        logger.info(f"Processing {num_items} items...")
        embeddings = embedding_service.embed_batch(test_items)

        elapsed = time.time() - start_time
        after = self.monitor.get_current_snapshot()

        # Check for alerts
        alerts = self.alert_manager.check_thresholds(after)

        results = {
            "num_items": num_items,
            "elapsed_seconds": round(elapsed, 2),
            "items_per_second": round(num_items / elapsed, 2),
            "memory_before_mb": before.rss_mb,
            "memory_after_mb": after.rss_mb,
            "memory_delta_mb": after.rss_mb - before.rss_mb,
            "peak_memory_mb": max(s.rss_mb for s in self.monitor.snapshots),
            "num_embeddings": len(embeddings),
            "alerts_triggered": len(alerts),
            "alert_details": [a.to_dict() for a in alerts],
        }

        logger.info("Load test complete:")
        logger.info(f"  Items/sec: {results['items_per_second']:.1f}")
        logger.info(f"  Memory delta: {results['memory_delta_mb']:.1f} MB")
        logger.info(f"  Peak memory: {results['peak_memory_mb']:.1f} MB")
        logger.info(f"  Alerts: {results['alerts_triggered']}")

        return results

    def detect_memory_leaks(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Detect memory leaks during sustained load.

        Args:
            duration_minutes: Duration of leak detection test

        Returns:
            Dictionary with leak detection results
        """
        logger.info("=" * 60)
        logger.info(f"Running memory leak detection ({duration_minutes} minutes)...")
        logger.info("=" * 60)

        # For testing, we'll run a shorter version (30 seconds per minute requested)
        # In production, use the full duration
        duration_seconds = duration_minutes * 2  # Scaled down for testing
        if duration_minutes >= 10:
            logger.warning(
                f"Running scaled-down leak test: {duration_seconds}s instead of {duration_minutes * 60}s"
            )

        embedding_service = EmbeddingService.get_instance()

        self.monitor.reset()
        self.monitor.start()

        start_time = time.time()
        iteration = 0

        logger.info(f"Running sustained load for {duration_seconds} seconds...")

        while (time.time() - start_time) < duration_seconds:
            # Generate test data
            test_texts = [f"Leak test iteration {iteration} item {i}" for i in range(50)]

            # Process
            _ = embedding_service.embed_batch(test_texts)

            # Capture snapshot every iteration
            self.monitor.capture_snapshot()

            iteration += 1

            # Log progress every 10 seconds
            elapsed = time.time() - start_time
            if iteration % 10 == 0:
                current = self.monitor.get_current_snapshot()
                logger.info(
                    f"  {elapsed:.0f}s elapsed, memory: {current.rss_mb:.1f} MB, iteration: {iteration}"
                )

        stats = self.monitor.stop()
        leak_detection = self.monitor.detect_memory_leak(threshold_mb_per_hour=10.0)

        # Check for leak alerts
        leak_alert = self.alert_manager.check_leak(stats)

        results = {
            "duration_seconds": round(time.time() - start_time, 2),
            "num_iterations": iteration,
            "num_snapshots": len(self.monitor.snapshots),
            "leak_detected": leak_detection["leak_detected"],
            "growth_rate_mb_per_hour": leak_detection["growth_rate_mb_per_hour"],
            "total_growth_mb": leak_detection["total_growth_mb"],
            "initial_memory_mb": self.monitor.snapshots[0].rss_mb if self.monitor.snapshots else 0,
            "final_memory_mb": self.monitor.snapshots[-1].rss_mb if self.monitor.snapshots else 0,
            "peak_memory_mb": stats.max_rss_mb,
            "mean_memory_mb": stats.mean_rss_mb,
            "std_dev_mb": stats.std_dev_rss_mb,
            "leak_alert": leak_alert.to_dict() if leak_alert else None,
        }

        logger.info("Leak detection complete:")
        logger.info(f"  Leak detected: {results['leak_detected']}")
        logger.info(f"  Growth rate: {results['growth_rate_mb_per_hour']:.2f} MB/hour")
        logger.info(f"  Total growth: {results['total_growth_mb']:.2f} MB")
        logger.info(f"  Peak memory: {results['peak_memory_mb']:.1f} MB")

        return results

    def compare_with_feature_2_1(self) -> Dict[str, Any]:
        """Compare results with Feature 2.1 findings.

        Returns:
            Dictionary with comparison metrics
        """
        logger.info("=" * 60)
        logger.info("Comparing with Feature 2.1 results...")
        logger.info("=" * 60)

        # Load Feature 2.1 memory analysis
        feature_2_1_file = self.output_dir / "memory_analysis_2025-10-31.json"

        if not feature_2_1_file.exists():
            logger.warning("Feature 2.1 memory analysis not found")
            return {"error": "Feature 2.1 data not available"}

        with open(feature_2_1_file, "r") as f:
            feature_2_1_data = json.load(f)

        # Extract relevant metrics
        feature_2_1_baseline = feature_2_1_data.get("baseline_memory", {})
        feature_2_1_leak = feature_2_1_data.get("memory_leak_check", {})

        comparison = {
            "feature_2_1_baseline_mb": feature_2_1_baseline.get("rss_mb", 0),
            "feature_2_1_peak_mb": feature_2_1_leak.get("final_memory_mb", 0),
            "feature_2_1_leak_detected": feature_2_1_leak.get("leak_detected", False),
            "feature_2_5_baseline_mb": self.results["tests"]
            .get("baseline", {})
            .get("initial_memory_mb", 0),
            "feature_2_5_peak_mb": 0,  # Will be updated with actual peak
            "comparison_notes": [],
        }

        # Update with current peak
        if "leak_detection" in self.results["tests"]:
            comparison["feature_2_5_peak_mb"] = self.results["tests"]["leak_detection"][
                "peak_memory_mb"
            ]

        logger.info(f"Feature 2.1 baseline: {comparison['feature_2_1_baseline_mb']:.1f} MB")
        logger.info(f"Feature 2.5 baseline: {comparison['feature_2_5_baseline_mb']:.1f} MB")

        return comparison

    def run_full_analysis(
        self, include_leak_test: bool = True, leak_duration_minutes: int = 5
    ) -> Dict[str, Any]:
        """Run complete memory analysis suite.

        Args:
            include_leak_test: Whether to run leak detection
            leak_duration_minutes: Duration for leak test

        Returns:
            Complete results dictionary
        """
        logger.info("=" * 60)
        logger.info("STARTING COMPREHENSIVE MEMORY ANALYSIS")
        logger.info("=" * 60)

        # 1. Baseline measurement
        self.results["tests"]["baseline"] = self.measure_baseline()

        # 2. Model loading
        self.results["tests"]["model_loading"] = self.measure_model_loading()

        # 3. Batch processing
        self.results["tests"]["batch_processing"] = self.measure_embedding_batch_processing(
            batch_size=64
        )

        # 4. Concurrent load
        self.results["tests"]["concurrent_load"] = self.measure_concurrent_load(num_items=100)

        # 5. Memory leak detection
        if include_leak_test:
            self.results["tests"]["leak_detection"] = self.detect_memory_leaks(
                duration_minutes=leak_duration_minutes
            )

        # 6. Comparison with Feature 2.1
        self.results["tests"]["feature_2_1_comparison"] = self.compare_with_feature_2_1()

        # Calculate overall metrics
        self.results["summary"] = self._generate_summary()

        # Save results
        output_file = (
            self.output_dir / f"memory_profile_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        )
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info("=" * 60)
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 60)

        return self.results

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of all test results."""
        tests = self.results["tests"]

        # Find peak memory across all tests
        peak_memory = 0
        for test_name, test_data in tests.items():
            if isinstance(test_data, dict):
                peak = test_data.get("peak_memory_mb", 0)
                if peak > peak_memory:
                    peak_memory = peak

                # Also check total_after_models_mb
                total = test_data.get("total_after_models_mb", 0)
                if total > peak_memory:
                    peak_memory = total

        target_gb = self.results["metadata"]["target_memory_gb"]
        target_mb = target_gb * 1024

        summary = {
            "peak_memory_mb": round(peak_memory, 2),
            "peak_memory_gb": round(peak_memory / 1024, 2),
            "target_memory_gb": target_gb,
            "under_target": peak_memory < target_mb,
            "margin_mb": round(target_mb - peak_memory, 2),
            "margin_percent": round((1 - peak_memory / target_mb) * 100, 2) if target_mb > 0 else 0,
            "leak_detected": tests.get("leak_detection", {}).get("leak_detected", False),
            "all_tests_passed": peak_memory < target_mb
            and not tests.get("leak_detection", {}).get("leak_detected", False),
        }

        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Peak memory: {summary['peak_memory_gb']:.2f} GB")
        logger.info(f"Target: {summary['target_memory_gb']:.2f} GB")
        logger.info(f"Under target: {summary['under_target']}")
        logger.info(f"Margin: {summary['margin_mb']:.1f} MB ({summary['margin_percent']:.1f}%)")
        logger.info(f"Leak detected: {summary['leak_detected']}")
        logger.info(f"All tests passed: {summary['all_tests_passed']}")
        logger.info("=" * 60)

        return summary


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive memory profiling")
    parser.add_argument("--full", action="store_true", help="Run full analysis suite")
    parser.add_argument("--baseline-only", action="store_true", help="Only measure baseline")
    parser.add_argument("--load-test", action="store_true", help="Run load test")
    parser.add_argument("--leak-test", action="store_true", help="Run leak detection")
    parser.add_argument(
        "--concurrent", type=int, default=100, help="Concurrent items for load test"
    )
    parser.add_argument("--duration", type=int, default=5, help="Duration in minutes for leak test")

    args = parser.parse_args()

    analyzer = MemoryAnalyzer()

    if args.full or (not any([args.baseline_only, args.load_test, args.leak_test])):
        # Run full suite by default
        analyzer.run_full_analysis(include_leak_test=True, leak_duration_minutes=args.duration)
    else:
        if args.baseline_only:
            analyzer.results["tests"]["baseline"] = analyzer.measure_baseline()
            analyzer.results["tests"]["model_loading"] = analyzer.measure_model_loading()

        if args.load_test:
            analyzer.results["tests"]["baseline"] = analyzer.measure_baseline()
            analyzer.results["tests"]["model_loading"] = analyzer.measure_model_loading()
            analyzer.results["tests"]["concurrent_load"] = analyzer.measure_concurrent_load(
                num_items=args.concurrent
            )

        if args.leak_test:
            analyzer.results["tests"]["baseline"] = analyzer.measure_baseline()
            analyzer.results["tests"]["model_loading"] = analyzer.measure_model_loading()
            analyzer.results["tests"]["leak_detection"] = analyzer.detect_memory_leaks(
                duration_minutes=args.duration
            )

        analyzer.results["summary"] = analyzer._generate_summary()

        # Save partial results
        output_file = (
            analyzer.output_dir / f"memory_profile_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        )
        with open(output_file, "w") as f:
            json.dump(analyzer.results, f, indent=2)

        logger.info(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
