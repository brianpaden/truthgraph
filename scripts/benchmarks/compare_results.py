#!/usr/bin/env python3
"""Compare benchmark results and detect regressions.

This script compares benchmark results across different runs to detect
performance regressions and improvements.

Usage:
    python compare_results.py --baseline results/baseline_2025-10-27.json --current results/embeddings_2025-10-28.json
    python compare_results.py --list  # List all available results
    python compare_results.py --compare-all  # Compare all results to baseline
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class BenchmarkComparator:
    """Compare benchmark results and detect regressions."""

    def __init__(self, regression_threshold: float = 0.1):
        """Initialize comparator.

        Args:
            regression_threshold: Threshold for regression (0.1 = 10% slower is regression)
        """
        self.regression_threshold = regression_threshold

    def load_results(self, path: Path) -> dict[str, Any]:
        """Load benchmark results from JSON file."""
        with open(path) as f:
            return json.load(f)

    def compare_values(
        self, baseline: float, current: float, lower_is_better: bool = True
    ) -> dict[str, Any]:
        """Compare two values and determine if regression occurred.

        Args:
            baseline: Baseline value
            current: Current value
            lower_is_better: True if lower values are better (e.g., latency)

        Returns:
            Comparison result dictionary
        """
        if baseline == 0:
            return {
                "baseline": baseline,
                "current": current,
                "change_pct": 0.0,
                "is_regression": False,
                "is_improvement": current > 0 and not lower_is_better,
            }

        change_pct = ((current - baseline) / baseline) * 100

        if lower_is_better:
            is_regression = change_pct > (self.regression_threshold * 100)
            is_improvement = change_pct < 0
        else:
            is_regression = change_pct < -(self.regression_threshold * 100)
            is_improvement = change_pct > 0

        return {
            "baseline": baseline,
            "current": current,
            "change_pct": change_pct,
            "is_regression": is_regression,
            "is_improvement": is_improvement,
        }

    def compare_embeddings(
        self, baseline: dict[str, Any], current: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare embedding benchmark results."""
        comparison = {"component": "embeddings", "metrics": {}}

        # Single text latency
        if "single_text" in baseline["benchmarks"] and "single_text" in current["benchmarks"]:
            b_single = baseline["benchmarks"]["single_text"]
            c_single = current["benchmarks"]["single_text"]

            comparison["metrics"]["single_text_latency_ms"] = self.compare_values(
                b_single["avg_latency_ms"], c_single["avg_latency_ms"], lower_is_better=True
            )

        # Batch throughput
        if "batch_sizes" in baseline["benchmarks"] and "batch_sizes" in current["benchmarks"]:
            b_batch = baseline["benchmarks"]["batch_sizes"]
            c_batch = current["benchmarks"]["batch_sizes"]

            comparison["metrics"]["batch_throughput"] = self.compare_values(
                b_batch["best_throughput"], c_batch["best_throughput"], lower_is_better=False
            )

        # Memory usage
        if "memory" in baseline["benchmarks"] and "memory" in current["benchmarks"]:
            b_mem = baseline["benchmarks"]["memory"]
            c_mem = current["benchmarks"]["memory"]

            if not b_mem.get("skipped") and not c_mem.get("skipped"):
                comparison["metrics"]["peak_memory_mb"] = self.compare_values(
                    b_mem["peak_mb"], c_mem["peak_mb"], lower_is_better=True
                )

        return comparison

    def compare_nli(self, baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        """Compare NLI benchmark results."""
        comparison = {"component": "nli", "metrics": {}}

        # Single pair latency
        if "single_pair" in baseline["benchmarks"] and "single_pair" in current["benchmarks"]:
            b_single = baseline["benchmarks"]["single_pair"]
            c_single = current["benchmarks"]["single_pair"]

            comparison["metrics"]["single_pair_latency_ms"] = self.compare_values(
                b_single["avg_latency_ms"], c_single["avg_latency_ms"], lower_is_better=True
            )

            comparison["metrics"]["single_pair_throughput"] = self.compare_values(
                b_single["throughput_pairs_per_sec"],
                c_single["throughput_pairs_per_sec"],
                lower_is_better=False,
            )

        # Batch throughput
        if "batch_sizes" in baseline["benchmarks"] and "batch_sizes" in current["benchmarks"]:
            b_batch = baseline["benchmarks"]["batch_sizes"]
            c_batch = current["benchmarks"]["batch_sizes"]

            comparison["metrics"]["batch_throughput"] = self.compare_values(
                b_batch["best_throughput"], c_batch["best_throughput"], lower_is_better=False
            )

        # Memory
        if "memory" in baseline["benchmarks"] and "memory" in current["benchmarks"]:
            b_mem = baseline["benchmarks"]["memory"]
            c_mem = current["benchmarks"]["memory"]

            if not b_mem.get("skipped") and not c_mem.get("skipped"):
                comparison["metrics"]["peak_memory_mb"] = self.compare_values(
                    b_mem["peak_mb"], c_mem["peak_mb"], lower_is_better=True
                )

        return comparison

    def compare_vector_search(
        self, baseline: dict[str, Any], current: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare vector search benchmark results."""
        comparison = {"component": "vector_search", "metrics": {}}

        # Query latency
        if "query_latency" in baseline["benchmarks"] and "query_latency" in current["benchmarks"]:
            b_query = baseline["benchmarks"]["query_latency"]
            c_query = current["benchmarks"]["query_latency"]

            comparison["metrics"]["query_latency_ms"] = self.compare_values(
                b_query["mean_time_ms"], c_query["mean_time_ms"], lower_is_better=True
            )

        # Batch queries
        if "batch_queries" in baseline["benchmarks"] and "batch_queries" in current["benchmarks"]:
            b_batch = baseline["benchmarks"]["batch_queries"]
            c_batch = current["benchmarks"]["batch_queries"]

            comparison["metrics"]["batch_query_per_query_ms"] = self.compare_values(
                b_batch["mean_per_query_ms"], c_batch["mean_per_query_ms"], lower_is_better=True
            )

        return comparison

    def compare_pipeline(
        self, baseline: dict[str, Any], current: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare pipeline benchmark results."""
        comparison = {"component": "pipeline", "metrics": {}}

        # Latency
        if "latency" in baseline["benchmarks"] and "latency" in current["benchmarks"]:
            b_lat = baseline["benchmarks"]["latency"]
            c_lat = current["benchmarks"]["latency"]

            comparison["metrics"]["mean_duration_ms"] = self.compare_values(
                b_lat["mean_duration_ms"], c_lat["mean_duration_ms"], lower_is_better=True
            )

            comparison["metrics"]["p95_duration_ms"] = self.compare_values(
                b_lat["p95_duration_ms"], c_lat["p95_duration_ms"], lower_is_better=True
            )

        # Throughput
        if "throughput" in baseline["benchmarks"] and "throughput" in current["benchmarks"]:
            b_thr = baseline["benchmarks"]["throughput"]
            c_thr = current["benchmarks"]["throughput"]

            comparison["metrics"]["throughput_claims_per_sec"] = self.compare_values(
                b_thr["throughput_claims_per_sec"],
                c_thr["throughput_claims_per_sec"],
                lower_is_better=False,
            )

        return comparison

    def print_comparison(self, comparison: dict[str, Any]) -> None:
        """Print comparison results in formatted manner."""
        print(f"\n{comparison['component'].upper()} Comparison:")
        print("-" * 80)

        has_regression = False
        has_improvement = False

        for metric_name, metric_data in comparison["metrics"].items():
            baseline = metric_data["baseline"]
            current = metric_data["current"]
            change_pct = metric_data["change_pct"]
            is_regression = metric_data["is_regression"]
            is_improvement = metric_data["is_improvement"]

            # Status indicator
            if is_regression:
                status = "REGRESSION"
                indicator = "⚠"
                has_regression = True
            elif is_improvement:
                status = "IMPROVED"
                indicator = "✓"
                has_improvement = True
            else:
                status = "STABLE"
                indicator = "="

            print(
                f"  {indicator} {metric_name:30s} {baseline:10.2f} -> {current:10.2f} "
                f"({change_pct:+6.1f}%) [{status}]"
            )

        if has_regression:
            print("\n⚠ WARNING: Performance regressions detected!")
        elif has_improvement:
            print("\n✓ Performance improvements detected")
        else:
            print("\n= Performance stable")

    def generate_report(
        self, baseline_path: Path, current_path: Path, output_path: Path | None = None
    ) -> dict[str, Any]:
        """Generate comprehensive comparison report.

        Args:
            baseline_path: Path to baseline results
            current_path: Path to current results
            output_path: Optional path to save report

        Returns:
            Report dictionary
        """
        print("=" * 80)
        print("BENCHMARK COMPARISON REPORT")
        print("=" * 80)
        print(f"\nBaseline: {baseline_path.name}")
        print(f"Current:  {current_path.name}")

        baseline = self.load_results(baseline_path)
        current = self.load_results(current_path)

        report = {
            "timestamp": datetime.now().isoformat(),
            "baseline_file": str(baseline_path),
            "current_file": str(current_path),
            "baseline_timestamp": baseline.get("timestamp", "unknown"),
            "current_timestamp": current.get("timestamp", "unknown"),
            "comparisons": [],
            "summary": {"regressions": 0, "improvements": 0, "stable": 0},
        }

        # Detect component type and compare
        component_type = None

        if "benchmarks" in baseline and "benchmarks" in current:
            benchmarks = baseline.get("benchmarks", {})

            if "single_text" in benchmarks or "batch_sizes" in benchmarks:
                component_type = "embeddings"
                comparison = self.compare_embeddings(baseline, current)
            elif "single_pair" in benchmarks:
                component_type = "nli"
                comparison = self.compare_nli(baseline, current)
            elif "query_latency" in benchmarks:
                component_type = "vector_search"
                comparison = self.compare_vector_search(baseline, current)
            elif "latency" in benchmarks and "throughput" in benchmarks:
                component_type = "pipeline"
                comparison = self.compare_pipeline(baseline, current)

            if component_type:
                report["comparisons"].append(comparison)
                self.print_comparison(comparison)

                # Count regressions/improvements
                for metric_data in comparison["metrics"].values():
                    if metric_data["is_regression"]:
                        report["summary"]["regressions"] += 1
                    elif metric_data["is_improvement"]:
                        report["summary"]["improvements"] += 1
                    else:
                        report["summary"]["stable"] += 1

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Regressions:  {report['summary']['regressions']}")
        print(f"Improvements: {report['summary']['improvements']}")
        print(f"Stable:       {report['summary']['stable']}")

        # Save report
        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_path}")

        return report


def list_results(results_dir: Path) -> None:
    """List all available benchmark results."""
    print("Available benchmark results:")
    print("-" * 80)

    result_files = sorted(results_dir.glob("*.json"))

    if not result_files:
        print("No results found in", results_dir)
        return

    for result_file in result_files:
        try:
            with open(result_file) as f:
                data = json.load(f)
            timestamp = data.get("timestamp", "unknown")
            component = "unknown"

            if "benchmarks" in data:
                benchmarks = data["benchmarks"]
                if "single_text" in benchmarks:
                    component = "embeddings"
                elif "single_pair" in benchmarks:
                    component = "nli"
                elif "query_latency" in benchmarks:
                    component = "vector_search"
                elif "latency" in benchmarks and "throughput" in benchmarks:
                    component = "pipeline"

            print(f"  {result_file.name:40s} {timestamp:30s} [{component}]")

        except Exception as e:
            print(f"  {result_file.name:40s} [ERROR: {e}]")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare benchmark results and detect regressions"
    )
    parser.add_argument("--baseline", type=str, help="Path to baseline results JSON")
    parser.add_argument("--current", type=str, help="Path to current results JSON")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Regression threshold (0.1 = 10%% slower)",
    )
    parser.add_argument("--list", action="store_true", help="List all available results")
    parser.add_argument(
        "--output", type=str, help="Path to save comparison report JSON"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results",
        help="Directory containing results files",
    )

    args = parser.parse_args()

    # Get results directory
    results_dir = Path(__file__).parent / args.results_dir
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return 1

    # List results
    if args.list:
        list_results(results_dir)
        return 0

    # Compare results
    if not args.baseline or not args.current:
        print("Error: Both --baseline and --current are required for comparison")
        print("Use --list to see available results")
        return 1

    baseline_path = Path(args.baseline)
    current_path = Path(args.current)

    if not baseline_path.is_absolute():
        baseline_path = results_dir / baseline_path

    if not current_path.is_absolute():
        current_path = results_dir / current_path

    if not baseline_path.exists():
        print(f"Error: Baseline file not found: {baseline_path}")
        return 1

    if not current_path.exists():
        print(f"Error: Current file not found: {current_path}")
        return 1

    # Generate report
    output_path = None
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = results_dir / output_path

    comparator = BenchmarkComparator(regression_threshold=args.threshold)
    report = comparator.generate_report(baseline_path, current_path, output_path)

    # Exit with error if regressions detected
    return 1 if report["summary"]["regressions"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
