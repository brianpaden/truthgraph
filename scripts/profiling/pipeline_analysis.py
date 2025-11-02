"""Pipeline Analysis Script for Feature 2.4.

This script analyzes profiling results to identify bottlenecks, compare
baseline vs optimized performance, and generate detailed recommendations.

Usage:
    python scripts/profiling/pipeline_analysis.py
    python scripts/profiling/pipeline_analysis.py --compare baseline.json optimized.json
    python scripts/profiling/pipeline_analysis.py --input pipeline_profile_2025-11-01.json
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BottleneckAnalysis:
    """Analysis of a performance bottleneck."""

    stage_name: str
    severity: str  # HIGH, MEDIUM, LOW
    duration_ms: float
    percentage_of_total: float
    memory_delta_mb: float
    throughput: float
    root_causes: list[str]
    optimization_impact: str  # Expected improvement
    implementation_effort: str  # Time to implement
    priority: int  # 1-5 (1 = highest)


@dataclass
class ComparisonResult:
    """Comparison between baseline and optimized runs."""

    baseline_duration_ms: float
    optimized_duration_ms: float
    improvement_ms: float
    improvement_percentage: float
    baseline_met_target: bool
    optimized_met_target: bool
    stage_improvements: dict[str, float]


class PipelineAnalyzer:
    """Analyzer for pipeline profiling results."""

    def __init__(self):
        """Initialize pipeline analyzer."""
        self.baseline_profile: dict[str, Any] | None = None
        self.optimized_profile: dict[str, Any] | None = None

    def load_profile(self, file_path: Path) -> dict[str, Any]:
        """Load profiling results from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Profile dictionary
        """
        logger.info("loading_profile", file_path=str(file_path))

        with open(file_path) as f:
            profile = json.load(f)

        logger.info(
            "profile_loaded",
            num_claims=profile.get("num_claims"),
            total_duration_ms=profile.get("total_duration_ms"),
        )

        return profile

    def analyze_bottlenecks(self, profile: dict[str, Any]) -> list[BottleneckAnalysis]:
        """Analyze bottlenecks in pipeline profile.

        Args:
            profile: Pipeline profile dictionary

        Returns:
            List of bottleneck analyses
        """
        logger.info("analyzing_bottlenecks")

        bottlenecks = []
        stages = profile.get("stages", [])
        total_duration = sum(stage["duration_ms"] for stage in stages)

        for stage in stages:
            duration_ms = stage["duration_ms"]
            percentage = (duration_ms / total_duration * 100) if total_duration > 0 else 0

            # Determine severity
            if percentage > 40:
                severity = "HIGH"
                priority = 1
            elif percentage > 20:
                severity = "MEDIUM"
                priority = 2
            elif percentage > 10:
                severity = "LOW"
                priority = 3
            else:
                continue  # Skip minor stages

            # Identify root causes based on stage
            root_causes = self._identify_root_causes(stage["stage_name"], stage)

            # Estimate optimization impact
            impact = self._estimate_optimization_impact(stage["stage_name"], percentage)

            # Estimate implementation effort
            effort = self._estimate_implementation_effort(stage["stage_name"])

            bottleneck = BottleneckAnalysis(
                stage_name=stage["stage_name"],
                severity=severity,
                duration_ms=duration_ms,
                percentage_of_total=percentage,
                memory_delta_mb=stage["memory_delta_mb"],
                throughput=stage["throughput"],
                root_causes=root_causes,
                optimization_impact=impact,
                implementation_effort=effort,
                priority=priority,
            )

            bottlenecks.append(bottleneck)

        # Sort by priority then duration
        bottlenecks.sort(key=lambda x: (x.priority, -x.duration_ms))

        logger.info("bottlenecks_analyzed", count=len(bottlenecks))

        return bottlenecks

    def _identify_root_causes(self, stage_name: str, stage_data: dict) -> list[str]:
        """Identify root causes of bottleneck for a stage.

        Args:
            stage_name: Name of the stage
            stage_data: Stage metrics data

        Returns:
            List of root cause descriptions
        """
        causes = []

        if stage_name == "claim_embedding_generation":
            if stage_data["throughput"] < 500:
                causes.append(
                    "Low throughput - batch size may be too small (target: >500 texts/sec)"
                )
            if stage_data["memory_delta_mb"] > 100:
                causes.append("High memory usage - consider smaller batch sizes")
            causes.append("Feature 2.1: Optimal batch_size=64 for embeddings")

        elif stage_name == "nli_verification":
            if stage_data["throughput"] < 50:
                causes.append(
                    "Low throughput - batch size may be too small (target: >60 pairs/sec)"
                )
            causes.append("Feature 2.2: Optimal batch_size=16 for NLI")
            causes.append("Consider parallel processing for multiple claims concurrently")

        elif stage_name == "evidence_retrieval":
            causes.append("Feature 2.3: Optimal vector search params - lists=50, probes=10")
            if stage_data["duration_ms"] > 500:
                causes.append("High latency - ensure IVFFlat index is created and configured")
            causes.append("Enable connection pooling for database queries")

        elif stage_name == "result_storage":
            causes.append("Database writes are synchronous - consider batching")
            causes.append("Implement connection pooling if not enabled")
            causes.append("Use bulk insert operations")

        elif stage_name == "verdict_aggregation":
            if stage_data["duration_ms"] > 100:
                causes.append("Aggregation logic may be inefficient - consider vectorization")

        return causes

    def _estimate_optimization_impact(self, stage_name: str, percentage: float) -> str:
        """Estimate the impact of optimizing a stage.

        Args:
            stage_name: Name of the stage
            percentage: Percentage of total pipeline time

        Returns:
            Impact description
        """
        if stage_name == "claim_embedding_generation":
            return f"+13% throughput (Feature 2.1), reduces {percentage:.1f}% of pipeline by ~13%"
        elif stage_name == "nli_verification":
            return f"+28% throughput (Feature 2.2), reduces {percentage:.1f}% of pipeline by ~28%"
        elif stage_name == "evidence_retrieval":
            return f"66x faster (Feature 2.3), reduces {percentage:.1f}% of pipeline by ~98%"
        elif stage_name == "result_storage":
            return "2-3x faster with batching and connection pooling"
        else:
            return f"Moderate improvement expected for {percentage:.1f}% of pipeline"

    def _estimate_implementation_effort(self, stage_name: str) -> str:
        """Estimate implementation effort for optimization.

        Args:
            stage_name: Name of the stage

        Returns:
            Effort description
        """
        if stage_name == "claim_embedding_generation":
            return "5 minutes (change batch_size constant)"
        elif stage_name == "nli_verification":
            return "5 minutes (change batch_size constant)"
        elif stage_name == "evidence_retrieval":
            return "10 minutes (configure index parameters)"
        elif stage_name == "result_storage":
            return "1-2 hours (implement batch writes and pooling)"
        else:
            return "Variable"

    def compare_profiles(self, baseline_path: Path, optimized_path: Path) -> ComparisonResult:
        """Compare baseline and optimized profiles.

        Args:
            baseline_path: Path to baseline profile
            optimized_path: Path to optimized profile

        Returns:
            Comparison result
        """
        logger.info(
            "comparing_profiles",
            baseline=str(baseline_path),
            optimized=str(optimized_path),
        )

        baseline = self.load_profile(baseline_path)
        optimized = self.load_profile(optimized_path)

        baseline_duration = baseline["total_duration_ms"]
        optimized_duration = optimized["total_duration_ms"]
        improvement_ms = baseline_duration - optimized_duration
        improvement_pct = (improvement_ms / baseline_duration * 100) if baseline_duration > 0 else 0

        # Compare individual stages
        stage_improvements = {}
        baseline_stages = {s["stage_name"]: s["duration_ms"] for s in baseline.get("stages", [])}
        optimized_stages = {s["stage_name"]: s["duration_ms"] for s in optimized.get("stages", [])}

        for stage_name in baseline_stages:
            if stage_name in optimized_stages:
                baseline_time = baseline_stages[stage_name]
                optimized_time = optimized_stages[stage_name]
                improvement = (
                    (baseline_time - optimized_time) / baseline_time * 100
                    if baseline_time > 0
                    else 0
                )
                stage_improvements[stage_name] = improvement

        result = ComparisonResult(
            baseline_duration_ms=baseline_duration,
            optimized_duration_ms=optimized_duration,
            improvement_ms=improvement_ms,
            improvement_percentage=improvement_pct,
            baseline_met_target=baseline.get("target_met", False),
            optimized_met_target=optimized.get("target_met", False),
            stage_improvements=stage_improvements,
        )

        logger.info("comparison_complete", improvement_percentage=f"{improvement_pct:.1f}%")

        return result

    def generate_report(
        self,
        profile: dict[str, Any],
        bottlenecks: list[BottleneckAnalysis],
        output_path: Path | None = None,
    ) -> Path:
        """Generate detailed analysis report.

        Args:
            profile: Pipeline profile
            bottlenecks: List of bottleneck analyses
            output_path: Optional output path

        Returns:
            Path to generated report
        """
        if output_path is None:
            results_dir = Path("docs/profiling")
            results_dir.mkdir(parents=True, exist_ok=True)
            output_path = results_dir / "pipeline_bottleneck_analysis.md"

        # Generate markdown report
        lines = []
        lines.append("# Pipeline Bottleneck Analysis")
        lines.append("")
        lines.append(f"**Generated**: {profile['timestamp']}")
        lines.append(f"**Claims Processed**: {profile['num_claims']}")
        lines.append(f"**Total Duration**: {profile['total_duration_ms']:.2f} ms")
        lines.append(f"**Avg Duration/Claim**: {profile['avg_duration_per_claim_ms']:.2f} ms")
        lines.append(f"**Target Met (<60s)**: {'✅ YES' if profile['target_met'] else '❌ NO'}")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        if profile["target_met"]:
            lines.append("✅ The pipeline **meets** the <60 second target for end-to-end latency.")
        else:
            lines.append(
                "❌ The pipeline **does not meet** the <60 second target. Optimization required."
            )
        lines.append("")
        lines.append(f"Identified **{len(bottlenecks)} bottlenecks** for optimization:")
        high = sum(1 for b in bottlenecks if b.severity == "HIGH")
        medium = sum(1 for b in bottlenecks if b.severity == "MEDIUM")
        low = sum(1 for b in bottlenecks if b.severity == "LOW")
        lines.append(f"- HIGH severity: {high}")
        lines.append(f"- MEDIUM severity: {medium}")
        lines.append(f"- LOW severity: {low}")
        lines.append("")

        # Stage Breakdown
        lines.append("## Stage Breakdown")
        lines.append("")
        lines.append("| Stage | Duration (ms) | % of Total | Memory (MB) | Throughput |")
        lines.append("|-------|--------------|------------|-------------|------------|")

        total_duration = sum(stage["duration_ms"] for stage in profile.get("stages", []))
        for stage in profile.get("stages", []):
            pct = (stage["duration_ms"] / total_duration * 100) if total_duration > 0 else 0
            lines.append(
                f"| {stage['stage_name']} | "
                f"{stage['duration_ms']:.2f} | "
                f"{pct:.1f}% | "
                f"{stage['memory_delta_mb']:.2f} | "
                f"{stage['throughput']:.2f} items/s |"
            )
        lines.append("")

        # Bottlenecks
        lines.append("## Identified Bottlenecks")
        lines.append("")

        for i, bottleneck in enumerate(bottlenecks, 1):
            lines.append(f"### {i}. {bottleneck.stage_name} [{bottleneck.severity}]")
            lines.append("")
            lines.append("**Metrics**:")
            lines.append(f"- Duration: {bottleneck.duration_ms:.2f} ms")
            lines.append(f"- Percentage of Total: {bottleneck.percentage_of_total:.1f}%")
            lines.append(f"- Memory Delta: {bottleneck.memory_delta_mb:.2f} MB")
            lines.append(f"- Throughput: {bottleneck.throughput:.2f} items/sec")
            lines.append("")
            lines.append("**Root Causes**:")
            for cause in bottleneck.root_causes:
                lines.append(f"- {cause}")
            lines.append("")
            lines.append(f"**Optimization Impact**: {bottleneck.optimization_impact}")
            lines.append(f"**Implementation Effort**: {bottleneck.implementation_effort}")
            lines.append(f"**Priority**: {bottleneck.priority} (1=highest)")
            lines.append("")

        # Recommendations
        lines.append("## Optimization Recommendations")
        lines.append("")
        lines.append(
            "Based on the bottleneck analysis, implement these optimizations in priority order:"
        )
        lines.append("")

        for i, bottleneck in enumerate(bottlenecks, 1):
            lines.append(f"{i}. **{bottleneck.stage_name}** (Priority {bottleneck.priority})")
            lines.append(f"   - {bottleneck.optimization_impact}")
            lines.append(f"   - Effort: {bottleneck.implementation_effort}")
            lines.append("")

        # Integration with Features 2.1-2.3
        lines.append("## Integration with Previous Features")
        lines.append("")
        lines.append("### Feature 2.1: Embedding Service Profiling")
        lines.append("- **Optimal batch_size**: 64")
        lines.append("- **Expected improvement**: +13% throughput")
        lines.append("- **Text truncation**: 256 characters (+40-60% for long texts)")
        lines.append("")
        lines.append("### Feature 2.2: NLI Service Optimization")
        lines.append("- **Optimal batch_size**: 16")
        lines.append("- **Expected improvement**: +28% throughput")
        lines.append("- **Target**: 64.74 pairs/sec")
        lines.append("")
        lines.append("### Feature 2.3: Vector Search Optimization")
        lines.append("- **Optimal parameters**: lists=50, probes=10")
        lines.append("- **Expected latency**: 45ms for 10K corpus")
        lines.append("- **Improvement**: 66x better than 3s baseline")
        lines.append("")

        # Write report
        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        logger.info("report_generated", output_path=str(output_path))

        return output_path

    def print_comparison(self, comparison: ComparisonResult) -> None:
        """Print comparison summary.

        Args:
            comparison: Comparison result
        """
        print("\n" + "=" * 80)
        print("BASELINE VS OPTIMIZED COMPARISON")
        print("=" * 80)
        print(f"\nBaseline Duration: {comparison.baseline_duration_ms:.2f} ms")
        print(f"Optimized Duration: {comparison.optimized_duration_ms:.2f} ms")
        print(
            f"Improvement: {comparison.improvement_ms:.2f} ms ({comparison.improvement_percentage:.1f}%)"
        )
        print("")
        print(f"Baseline Met Target: {'✅ YES' if comparison.baseline_met_target else '❌ NO'}")
        print(f"Optimized Met Target: {'✅ YES' if comparison.optimized_met_target else '❌ NO'}")

        if comparison.stage_improvements:
            print("\n" + "-" * 80)
            print("STAGE-BY-STAGE IMPROVEMENTS")
            print("-" * 80)

            for stage, improvement in comparison.stage_improvements.items():
                symbol = "✅" if improvement > 0 else "⚠️"
                print(f"{symbol} {stage}: {improvement:+.1f}%")

        print("\n" + "=" * 80)


def main() -> None:
    """Main entry point for pipeline analysis."""
    parser = argparse.ArgumentParser(description="Analyze pipeline profiling results")
    parser.add_argument(
        "--input",
        type=Path,
        help="Input profile JSON file (default: latest in results/)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("BASELINE", "OPTIMIZED"),
        help="Compare two profile files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for analysis report (default: docs/profiling/)",
    )

    args = parser.parse_args()

    analyzer = PipelineAnalyzer()

    if args.compare:
        # Comparison mode
        baseline_path, optimized_path = args.compare
        comparison = analyzer.compare_profiles(baseline_path, optimized_path)
        analyzer.print_comparison(comparison)

    else:
        # Analysis mode
        if args.input:
            profile_path = args.input
        else:
            # Find latest profile
            results_dir = Path("scripts/profiling/results")
            profile_files = sorted(results_dir.glob("pipeline_profile_*.json"))
            if not profile_files:
                print("Error: No profile files found in results/")
                return
            profile_path = profile_files[-1]
            print(f"Using latest profile: {profile_path}")

        # Load and analyze
        profile = analyzer.load_profile(profile_path)
        bottlenecks = analyzer.analyze_bottlenecks(profile)

        # Generate report
        report_path = analyzer.generate_report(profile, bottlenecks, args.output)
        print(f"\nAnalysis report generated: {report_path}")

        # Print summary
        print(f"\nFound {len(bottlenecks)} bottlenecks:")
        for bottleneck in bottlenecks:
            print(
                f"  [{bottleneck.severity}] {bottleneck.stage_name}: "
                f"{bottleneck.percentage_of_total:.1f}% of pipeline"
            )


if __name__ == "__main__":
    main()
