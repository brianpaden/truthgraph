"""Pipeline End-to-End Profiling Script for Feature 2.4.

This script profiles the complete verification pipeline to identify bottlenecks
and optimize for the <60 second end-to-end latency target.

Profiling stages:
1. Claim embedding generation
2. Evidence retrieval from vector store
3. Evidence embedding generation (if needed)
4. NLI inference (claim-evidence pairs)
5. Verdict aggregation
6. Result storage

Usage:
    python scripts/profiling/profile_pipeline.py --num-claims 20
    python scripts/profiling/profile_pipeline.py --num-claims 20 --optimize
    python scripts/profiling/profile_pipeline.py --num-claims 5 --profile-detail high
"""

import argparse
import cProfile
import json
import pstats
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""

    stage_name: str
    duration_ms: float
    memory_delta_mb: float
    item_count: int
    throughput: float  # items/sec
    details: dict[str, Any]


@dataclass
class PipelineProfile:
    """Complete profile of pipeline execution."""

    timestamp: str
    num_claims: int
    total_duration_ms: float
    avg_duration_per_claim_ms: float
    stages: list[StageMetrics]
    bottlenecks: list[dict[str, Any]]
    recommendations: list[str]
    optimizations_applied: dict[str, Any]
    target_met: bool  # <60s target


class PipelineProfiler:
    """Profiler for end-to-end verification pipeline.

    This profiler measures timing and memory for each pipeline stage,
    identifies bottlenecks, and generates optimization recommendations.
    """

    def __init__(self, optimize: bool = False, profile_detail: str = "medium"):
        """Initialize pipeline profiler.

        Args:
            optimize: Whether to apply optimizations from Features 2.1-2.3
            profile_detail: Level of detail ('low', 'medium', 'high')
        """
        self.optimize = optimize
        self.profile_detail = profile_detail
        self.stage_metrics: list[StageMetrics] = []
        self.test_claims: list[dict[str, str]] = []

        # Optimization settings from Features 2.1-2.3
        self.optimizations = {
            "embedding_batch_size": 64 if optimize else 32,  # Feature 2.1
            "nli_batch_size": 16 if optimize else 8,  # Feature 2.2
            "vector_search_lists": 50 if optimize else 100,  # Feature 2.3
            "vector_search_probes": 10 if optimize else 5,  # Feature 2.3
            "parallel_evidence_retrieval": optimize,
            "text_truncation": 256 if optimize else None,
        }

        logger.info(
            "pipeline_profiler_initialized",
            optimize=optimize,
            profile_detail=profile_detail,
            optimizations=self.optimizations,
        )

    def create_test_corpus(self, num_claims: int = 20) -> list[dict[str, str]]:
        """Create test corpus of claims for profiling.

        Args:
            num_claims: Number of test claims to generate

        Returns:
            List of test claim dictionaries
        """
        logger.info("creating_test_corpus", num_claims=num_claims)

        # Generate diverse test claims
        test_claims = [
            {
                "id": str(uuid4()),
                "text": "The Earth orbits the Sun in approximately 365.25 days",
                "category": "science",
            },
            {
                "id": str(uuid4()),
                "text": "Water boils at 100 degrees Celsius at sea level atmospheric pressure",
                "category": "science",
            },
            {
                "id": str(uuid4()),
                "text": "The capital of France is Paris and has been since 987 AD",
                "category": "geography",
            },
            {
                "id": str(uuid4()),
                "text": "Python is a high-level programming language created by Guido van Rossum",
                "category": "technology",
            },
            {
                "id": str(uuid4()),
                "text": "The human body contains approximately 37.2 trillion cells",
                "category": "biology",
            },
            {
                "id": str(uuid4()),
                "text": "Mount Everest is the highest mountain on Earth at 8,849 meters",
                "category": "geography",
            },
            {
                "id": str(uuid4()),
                "text": "The speed of light in vacuum is approximately 299,792,458 meters per second",
                "category": "physics",
            },
            {
                "id": str(uuid4()),
                "text": "DNA was first isolated by Friedrich Miescher in 1869",
                "category": "biology",
            },
            {
                "id": str(uuid4()),
                "text": "The Roman Empire fell in 476 AD when the last emperor was deposed",
                "category": "history",
            },
            {
                "id": str(uuid4()),
                "text": "Photosynthesis converts light energy into chemical energy in plants",
                "category": "biology",
            },
            {
                "id": str(uuid4()),
                "text": "The Great Wall of China is visible from space with the naked eye",
                "category": "false_claim",
            },
            {
                "id": str(uuid4()),
                "text": "Vaccines cause autism and other developmental disorders in children",
                "category": "false_claim",
            },
            {
                "id": str(uuid4()),
                "text": "Climate change is a natural cycle unrelated to human activities",
                "category": "false_claim",
            },
            {
                "id": str(uuid4()),
                "text": "5G networks spread coronavirus and weaken immune systems",
                "category": "false_claim",
            },
            {
                "id": str(uuid4()),
                "text": "The moon landing in 1969 was faked by NASA in a Hollywood studio",
                "category": "false_claim",
            },
            {
                "id": str(uuid4()),
                "text": "Artificial intelligence will replace all human jobs by 2030",
                "category": "speculative",
            },
            {
                "id": str(uuid4()),
                "text": "Quantum computers will break all current encryption methods immediately",
                "category": "speculative",
            },
            {
                "id": str(uuid4()),
                "text": "Eating carrots improves night vision significantly in humans",
                "category": "myth",
            },
            {
                "id": str(uuid4()),
                "text": "You only use 10% of your brain capacity at any given time",
                "category": "myth",
            },
            {
                "id": str(uuid4()),
                "text": "Lightning never strikes the same place twice due to electrical discharge",
                "category": "myth",
            },
        ]

        # Return requested number of claims
        self.test_claims = test_claims[:num_claims]

        logger.info("test_corpus_created", num_claims=len(self.test_claims))
        return self.test_claims

    def profile_stage(
        self,
        stage_name: str,
        func: Any,
        *args: Any,
        item_count: int = 1,
        **kwargs: Any,
    ) -> tuple[Any, StageMetrics]:
        """Profile a single pipeline stage.

        Args:
            stage_name: Name of the stage
            func: Function to profile
            args: Positional arguments for function
            item_count: Number of items processed (for throughput)
            kwargs: Keyword arguments for function

        Returns:
            Tuple of (function result, stage metrics)
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Measure initial memory
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Time execution
        start_time = time.time()

        # Execute function
        if self.profile_detail == "high":
            # Use cProfile for detailed profiling
            profiler = cProfile.Profile()
            profiler.enable()
            result = func(*args, **kwargs)
            profiler.disable()

            # Get top functions
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
            ps.print_stats(10)
            profile_output = s.getvalue()
        else:
            result = func(*args, **kwargs)
            profile_output = "Detailed profiling disabled"

        # Measure duration and memory
        duration_ms = (time.time() - start_time) * 1000
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta_mb = memory_after - memory_before

        # Calculate throughput
        throughput = (item_count / duration_ms * 1000) if duration_ms > 0 else 0

        # Create metrics
        metrics = StageMetrics(
            stage_name=stage_name,
            duration_ms=duration_ms,
            memory_delta_mb=memory_delta_mb,
            item_count=item_count,
            throughput=throughput,
            details={
                "memory_before_mb": memory_before,
                "memory_after_mb": memory_after,
                "profile_output": (profile_output if self.profile_detail == "high" else None),
            },
        )

        self.stage_metrics.append(metrics)

        logger.info(
            "stage_profiled",
            stage=stage_name,
            duration_ms=f"{duration_ms:.2f}",
            memory_delta_mb=f"{memory_delta_mb:.2f}",
            throughput=f"{throughput:.2f}",
        )

        return result, metrics

    def profile_complete_pipeline(self, num_claims: int = 20) -> PipelineProfile:
        """Profile the complete verification pipeline.

        Args:
            num_claims: Number of claims to process

        Returns:
            Complete pipeline profile with metrics
        """
        logger.info(
            "starting_pipeline_profiling",
            num_claims=num_claims,
            optimize=self.optimize,
        )

        pipeline_start = time.time()

        # Create test corpus
        test_claims = self.create_test_corpus(num_claims)

        # Stage 1: Claim embedding generation (batch)
        logger.info("profiling_stage_1_embeddings")

        def generate_embeddings_batch() -> list[list[float]]:
            """Simulate embedding generation."""
            from truthgraph.services.ml.embedding_service import EmbeddingService

            service = EmbeddingService.get_instance()
            texts = [claim["text"] for claim in test_claims]

            # Apply text truncation if optimized
            if self.optimizations["text_truncation"]:
                texts = [text[: self.optimizations["text_truncation"]] for text in texts]

            return service.embed_batch(texts, batch_size=self.optimizations["embedding_batch_size"])

        embeddings, emb_metrics = self.profile_stage(
            "claim_embedding_generation",
            generate_embeddings_batch,
            item_count=num_claims,
        )

        # Stage 2: Evidence retrieval (simulated - would use vector search)
        logger.info("profiling_stage_2_evidence_retrieval")

        def retrieve_evidence() -> list[list[dict]]:
            """Simulate evidence retrieval for each claim."""
            # In real pipeline: vector search with optimized parameters
            # Here: simulate 10 evidence items per claim
            all_evidence = []
            for claim in test_claims:
                evidence = [
                    {
                        "id": str(uuid4()),
                        "content": f"Evidence {i} for: {claim['text'][:50]}",
                        "similarity": 0.9 - (i * 0.05),
                    }
                    for i in range(10)
                ]
                all_evidence.append(evidence)
            return all_evidence

        evidence_sets, evidence_metrics = self.profile_stage(
            "evidence_retrieval",
            retrieve_evidence,
            item_count=num_claims * 10,  # 10 evidence per claim
        )

        # Stage 3: NLI verification (batch per claim)
        logger.info("profiling_stage_3_nli_verification")

        def verify_nli_batch() -> list[list[dict]]:
            """Simulate NLI verification for all claim-evidence pairs."""
            from truthgraph.services.ml.nli_service import NLIService

            service = NLIService.get_instance()
            all_results = []

            for claim, evidence_set in zip(test_claims, evidence_sets):
                # Create pairs (premise, hypothesis)
                pairs = [(ev["content"], claim["text"]) for ev in evidence_set]

                # Batch verify with optimized batch size
                results = service.verify_batch(
                    pairs, batch_size=self.optimizations["nli_batch_size"]
                )

                all_results.append([asdict(r) for r in results])

            return all_results

        nli_results, nli_metrics = self.profile_stage(
            "nli_verification",
            verify_nli_batch,
            item_count=num_claims * 10,  # All pairs
        )

        # Stage 4: Verdict aggregation
        logger.info("profiling_stage_4_verdict_aggregation")

        def aggregate_verdicts() -> list[dict]:
            """Aggregate NLI results into verdicts."""
            verdicts = []
            for claim, results in zip(test_claims, nli_results):
                # Simple aggregation
                entailment_count = sum(1 for r in results if r["label"] == "entailment")
                contradiction_count = sum(1 for r in results if r["label"] == "contradiction")

                if entailment_count > contradiction_count:
                    verdict = "SUPPORTED"
                    confidence = entailment_count / len(results)
                elif contradiction_count > entailment_count:
                    verdict = "REFUTED"
                    confidence = contradiction_count / len(results)
                else:
                    verdict = "INSUFFICIENT"
                    confidence = 0.5

                verdicts.append(
                    {
                        "claim_id": claim["id"],
                        "verdict": verdict,
                        "confidence": confidence,
                    }
                )

            return verdicts

        verdicts, verdict_metrics = self.profile_stage(
            "verdict_aggregation", aggregate_verdicts, item_count=num_claims
        )

        # Stage 5: Result storage (simulated)
        logger.info("profiling_stage_5_result_storage")

        def store_results() -> int:
            """Simulate storing results in database."""
            # In real pipeline: database writes
            # Here: simulate serialization time
            time.sleep(0.01 * num_claims)  # 10ms per claim
            return num_claims

        stored_count, storage_metrics = self.profile_stage(
            "result_storage", store_results, item_count=num_claims
        )

        # Calculate total duration
        total_duration_ms = (time.time() - pipeline_start) * 1000
        avg_duration_ms = total_duration_ms / num_claims

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()

        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)

        # Check if target met
        target_met = avg_duration_ms < 60000  # <60s per claim

        # Create profile
        profile = PipelineProfile(
            timestamp=datetime.now(UTC).isoformat(),
            num_claims=num_claims,
            total_duration_ms=total_duration_ms,
            avg_duration_per_claim_ms=avg_duration_ms,
            stages=[asdict(m) for m in self.stage_metrics],
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            optimizations_applied=self.optimizations,
            target_met=target_met,
        )

        logger.info(
            "pipeline_profiling_complete",
            total_duration_ms=f"{total_duration_ms:.2f}",
            avg_duration_ms=f"{avg_duration_ms:.2f}",
            target_met=target_met,
            num_bottlenecks=len(bottlenecks),
        )

        return profile

    def _identify_bottlenecks(self) -> list[dict[str, Any]]:
        """Identify performance bottlenecks from stage metrics.

        Returns:
            List of bottleneck descriptions with severity
        """
        bottlenecks = []

        # Calculate total duration
        total_duration = sum(m.duration_ms for m in self.stage_metrics)

        for metrics in self.stage_metrics:
            percentage = (metrics.duration_ms / total_duration * 100) if total_duration > 0 else 0

            # Flag stages taking >20% of total time
            if percentage > 20:
                severity = "HIGH" if percentage > 40 else "MEDIUM"
                bottlenecks.append(
                    {
                        "stage": metrics.stage_name,
                        "severity": severity,
                        "duration_ms": metrics.duration_ms,
                        "percentage_of_total": percentage,
                        "throughput": metrics.throughput,
                        "recommendation": f"Optimize {metrics.stage_name} - consuming {percentage:.1f}% of pipeline time",
                    }
                )

        # Sort by duration (descending)
        bottlenecks.sort(key=lambda x: x["duration_ms"], reverse=True)

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: list[dict]) -> list[str]:
        """Generate optimization recommendations.

        Args:
            bottlenecks: List of identified bottlenecks

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if not self.optimize:
            recommendations.append(
                "Run with --optimize flag to apply optimizations from Features 2.1-2.3"
            )
            recommendations.append(
                "Expected improvement: Embedding batch_size 64 (+13%), NLI batch_size 16 (+28%), Vector search optimized (+66x)"
            )

        for bottleneck in bottlenecks:
            stage = bottleneck["stage"]

            if stage == "claim_embedding_generation":
                if self.optimizations["embedding_batch_size"] < 64:
                    recommendations.append(
                        "Increase embedding batch_size to 64 (Feature 2.1 optimal)"
                    )
                if not self.optimizations["text_truncation"]:
                    recommendations.append(
                        "Enable text truncation to 256 chars (Feature 2.1, +40-60% improvement)"
                    )

            elif stage == "nli_verification":
                if self.optimizations["nli_batch_size"] < 16:
                    recommendations.append("Increase NLI batch_size to 16 (Feature 2.2 optimal)")
                recommendations.append("Consider parallel NLI processing for multiple claims")

            elif stage == "evidence_retrieval":
                recommendations.append(
                    f"Optimize vector search: lists={self.optimizations['vector_search_lists']}, probes={self.optimizations['vector_search_probes']} (Feature 2.3)"
                )
                if not self.optimizations["parallel_evidence_retrieval"]:
                    recommendations.append("Enable parallel evidence retrieval for multiple claims")

            elif stage == "result_storage":
                recommendations.append("Consider batch database writes")
                recommendations.append("Implement connection pooling")

        return recommendations

    def save_results(self, profile: PipelineProfile, output_path: Path | None = None) -> Path:
        """Save profiling results to JSON file.

        Args:
            profile: Pipeline profile to save
            output_path: Optional output path (default: auto-generated)

        Returns:
            Path to saved file
        """
        if output_path is None:
            results_dir = Path("scripts/profiling/results")
            results_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            output_path = results_dir / f"pipeline_profile_{timestamp}.json"

        # Convert to dict
        profile_dict = asdict(profile)

        # Save
        with open(output_path, "w") as f:
            json.dump(profile_dict, f, indent=2)

        logger.info("profile_saved", output_path=str(output_path))

        return output_path

    def print_summary(self, profile: PipelineProfile) -> None:
        """Print human-readable summary of profiling results.

        Args:
            profile: Pipeline profile to summarize
        """
        print("\n" + "=" * 80)
        print("PIPELINE PROFILING SUMMARY")
        print("=" * 80)
        print(f"\nTimestamp: {profile.timestamp}")
        print(f"Claims Processed: {profile.num_claims}")
        print(f"Optimizations: {'ENABLED' if self.optimize else 'DISABLED'}")
        print(f"\nTotal Duration: {profile.total_duration_ms:.2f} ms")
        print(f"Avg Duration/Claim: {profile.avg_duration_per_claim_ms:.2f} ms")
        print(f"Target Met (<60s): {'✅ YES' if profile.target_met else '❌ NO'}")

        print("\n" + "-" * 80)
        print("STAGE BREAKDOWN")
        print("-" * 80)

        for stage in profile.stages:
            stage_dict = stage if isinstance(stage, dict) else asdict(stage)
            print(f"\n{stage_dict['stage_name']}:")
            print(f"  Duration: {stage_dict['duration_ms']:.2f} ms")
            print(f"  Memory Delta: {stage_dict['memory_delta_mb']:.2f} MB")
            print(f"  Items: {stage_dict['item_count']}")
            print(f"  Throughput: {stage_dict['throughput']:.2f} items/sec")

        if profile.bottlenecks:
            print("\n" + "-" * 80)
            print("BOTTLENECKS IDENTIFIED")
            print("-" * 80)

            for bottleneck in profile.bottlenecks:
                print(f"\n[{bottleneck['severity']}] {bottleneck['stage']}")
                print(f"  Duration: {bottleneck['duration_ms']:.2f} ms")
                print(f"  Percentage: {bottleneck['percentage_of_total']:.1f}%")
                print(f"  Recommendation: {bottleneck['recommendation']}")

        if profile.recommendations:
            print("\n" + "-" * 80)
            print("OPTIMIZATION RECOMMENDATIONS")
            print("-" * 80)

            for i, rec in enumerate(profile.recommendations, 1):
                print(f"\n{i}. {rec}")

        print("\n" + "=" * 80)


def main() -> None:
    """Main entry point for pipeline profiling."""
    parser = argparse.ArgumentParser(description="Profile the verification pipeline end-to-end")
    parser.add_argument(
        "--num-claims",
        type=int,
        default=20,
        help="Number of claims to profile (default: 20)",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Apply optimizations from Features 2.1-2.3",
    )
    parser.add_argument(
        "--profile-detail",
        choices=["low", "medium", "high"],
        default="medium",
        help="Profiling detail level (default: medium)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for results (default: auto-generated)",
    )

    args = parser.parse_args()

    # Create profiler
    profiler = PipelineProfiler(optimize=args.optimize, profile_detail=args.profile_detail)

    # Run profiling
    print(f"\nProfiling pipeline with {args.num_claims} claims (optimize={args.optimize})...")
    profile = profiler.profile_complete_pipeline(num_claims=args.num_claims)

    # Save results
    output_path = profiler.save_results(profile, args.output)
    print(f"\nResults saved to: {output_path}")

    # Print summary
    profiler.print_summary(profile)


if __name__ == "__main__":
    main()
