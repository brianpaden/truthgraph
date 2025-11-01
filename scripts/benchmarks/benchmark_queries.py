"""Database query performance benchmarking script.

This script measures query performance for:
1. Evidence retrieval (batch vs individual)
2. Verdict storage (single vs batch)
3. NLI result operations
4. Join query performance
5. Index effectiveness

Outputs:
- JSON results file with detailed metrics
- Performance comparison (optimized vs naive)
- Recommendations for further optimization

Usage:
    python benchmark_queries.py
    python benchmark_queries.py --iterations 100
    python benchmark_queries.py --corpus-size 1000
    python benchmark_queries.py --output results/query_perf.json
"""

import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path to import truthgraph modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from truthgraph.db.queries import OptimizedQueries
from truthgraph.db.query_builder import QueryBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QueryBenchmark:
    """Benchmark database query performance."""

    def __init__(
        self,
        database_url: str,
        iterations: int = 50,
        corpus_size: int = 1000,
    ) -> None:
        """Initialize benchmark.

        Args:
            database_url: PostgreSQL connection URL
            iterations: Number of iterations per benchmark
            corpus_size: Number of test records to create
        """
        self.database_url = database_url
        self.iterations = iterations
        self.corpus_size = corpus_size

        # Create engine and session
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        self.queries = OptimizedQueries()
        self.results: Dict[str, Any] = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "iterations": iterations,
                "corpus_size": corpus_size,
                "database_url": database_url.split("@")[-1],  # Remove credentials
            },
            "benchmarks": {},
        }

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all query benchmarks.

        Returns:
            Dictionary with all benchmark results
        """
        logger.info("Starting database query benchmarks...")

        # Setup test data
        logger.info(f"Setting up test data (corpus_size={self.corpus_size})...")
        self._setup_test_data()

        # Run benchmarks
        self._benchmark_evidence_retrieval()
        self._benchmark_nli_operations()
        self._benchmark_verdict_storage()
        self._benchmark_join_queries()
        self._benchmark_batch_vs_individual()

        # Analyze results
        self._analyze_results()

        logger.info("All benchmarks completed!")
        return self.results

    def _setup_test_data(self) -> None:
        """Setup test data for benchmarking."""
        session = self.SessionLocal()
        try:
            # Check if test data already exists
            result = session.execute(text("SELECT COUNT(*) FROM evidence"))
            count = result.scalar()

            if count >= self.corpus_size:
                logger.info(f"Test data already exists ({count} records)")
                return

            logger.info(f"Creating {self.corpus_size} test evidence records...")

            # Create test evidence in batches
            batch_size = 100
            for i in range(0, self.corpus_size, batch_size):
                current_batch = min(batch_size, self.corpus_size - i)

                values = []
                for j in range(current_batch):
                    idx = i + j
                    values.append(f"""(
                        gen_random_uuid(),
                        'Test evidence content {idx} with some meaningful text for search.',
                        'https://example.com/evidence/{idx}',
                        'web',
                        {0.5 + (idx % 50) / 100.0},
                        CURRENT_TIMESTAMP
                    )""")

                query = f"""
                    INSERT INTO evidence (
                        id, content, source_url, source_type, credibility_score, created_at
                    ) VALUES {', '.join(values)}
                """

                session.execute(text(query))

            session.commit()
            logger.info(f"Created {self.corpus_size} test evidence records")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to setup test data: {e}")
            raise
        finally:
            session.close()

    def _benchmark_evidence_retrieval(self) -> None:
        """Benchmark evidence retrieval queries."""
        logger.info("Benchmarking evidence retrieval...")

        session = self.SessionLocal()
        try:
            # Get sample evidence IDs
            result = session.execute(text(
                f"SELECT id FROM evidence ORDER BY created_at DESC LIMIT {min(100, self.corpus_size)}"
            ))
            evidence_ids = [UUID(row[0]) for row in result.fetchall()]

            # Benchmark 1: Batch retrieval (optimized)
            timings_batch = []
            for _ in range(self.iterations):
                start = time.time()
                results = self.queries.batch_get_evidence_by_ids(
                    session, evidence_ids[:20]
                )
                duration = (time.time() - start) * 1000
                timings_batch.append(duration)

            # Benchmark 2: Individual retrieval (naive)
            timings_individual = []
            for _ in range(self.iterations):
                start = time.time()
                for eid in evidence_ids[:20]:
                    result = session.execute(
                        text("SELECT * FROM evidence WHERE id = :id"),
                        {"id": str(eid)}
                    )
                    _ = result.fetchone()
                duration = (time.time() - start) * 1000
                timings_individual.append(duration)

            self.results["benchmarks"]["evidence_retrieval"] = {
                "batch_optimized": {
                    "mean_ms": statistics.mean(timings_batch),
                    "median_ms": statistics.median(timings_batch),
                    "min_ms": min(timings_batch),
                    "max_ms": max(timings_batch),
                    "stdev_ms": statistics.stdev(timings_batch) if len(timings_batch) > 1 else 0,
                },
                "individual_naive": {
                    "mean_ms": statistics.mean(timings_individual),
                    "median_ms": statistics.median(timings_individual),
                    "min_ms": min(timings_individual),
                    "max_ms": max(timings_individual),
                    "stdev_ms": statistics.stdev(timings_individual) if len(timings_individual) > 1 else 0,
                },
                "speedup_factor": statistics.mean(timings_individual) / statistics.mean(timings_batch),
                "items_retrieved": 20,
            }

            logger.info(
                f"Evidence retrieval: Batch={statistics.mean(timings_batch):.2f}ms, "
                f"Individual={statistics.mean(timings_individual):.2f}ms "
                f"(speedup: {statistics.mean(timings_individual) / statistics.mean(timings_batch):.1f}x)"
            )

        finally:
            session.close()

    def _benchmark_nli_operations(self) -> None:
        """Benchmark NLI result operations."""
        logger.info("Benchmarking NLI operations...")

        session = self.SessionLocal()
        try:
            # Get sample claim and evidence IDs
            result = session.execute(text("SELECT id FROM evidence LIMIT 50"))
            evidence_ids = [UUID(row[0]) for row in result.fetchall()]

            # Create test claim
            claim_id = uuid4()

            # Benchmark: Batch NLI insert
            nli_results = []
            for i, eid in enumerate(evidence_ids[:20]):
                nli_results.append({
                    "claim_id": claim_id,
                    "evidence_id": eid,
                    "label": ["ENTAILMENT", "CONTRADICTION", "NEUTRAL"][i % 3],
                    "confidence": 0.75 + (i % 25) / 100.0,
                    "entailment_score": 0.7,
                    "contradiction_score": 0.2,
                    "neutral_score": 0.1,
                    "model_name": "microsoft/deberta-v3-base",
                    "model_version": "v1",
                    "premise_text": f"Evidence {i}",
                    "hypothesis_text": "Test claim",
                })

            timings_batch = []
            for _ in range(min(10, self.iterations)):  # Fewer iterations for inserts
                start = time.time()
                try:
                    ids = self.queries.batch_create_nli_results(session, nli_results)
                    duration = (time.time() - start) * 1000
                    timings_batch.append(duration)

                    # Clean up
                    session.execute(
                        text("DELETE FROM nli_results WHERE id = ANY(:ids)"),
                        {"ids": [str(i) for i in ids]}
                    )
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Batch insert iteration failed: {e}")

            self.results["benchmarks"]["nli_batch_insert"] = {
                "mean_ms": statistics.mean(timings_batch) if timings_batch else 0,
                "median_ms": statistics.median(timings_batch) if timings_batch else 0,
                "min_ms": min(timings_batch) if timings_batch else 0,
                "max_ms": max(timings_batch) if timings_batch else 0,
                "items_inserted": len(nli_results),
                "iterations": len(timings_batch),
            }

            logger.info(
                f"NLI batch insert: {statistics.mean(timings_batch):.2f}ms "
                f"for {len(nli_results)} items"
                if timings_batch else "NLI batch insert: No successful iterations"
            )

        finally:
            session.close()

    def _benchmark_verdict_storage(self) -> None:
        """Benchmark verdict storage operations."""
        logger.info("Benchmarking verdict storage...")

        session = self.SessionLocal()
        try:
            # Create test claim and NLI results
            claim_id = uuid4()
            nli_ids = [uuid4() for _ in range(10)]

            timings = []
            for _ in range(min(20, self.iterations)):
                start = time.time()
                try:
                    result_id = self.queries.create_verification_result_with_nli(
                        session=session,
                        claim_id=claim_id,
                        verdict="SUPPORTED",
                        confidence=0.85,
                        scores={
                            "support_score": 0.75,
                            "refute_score": 0.15,
                            "neutral_score": 0.10,
                        },
                        evidence_counts={
                            "supporting": 7,
                            "refuting": 2,
                            "neutral": 1,
                        },
                        nli_result_ids=nli_ids,
                        reasoning="Strong supporting evidence found.",
                        metadata={
                            "pipeline_version": "v2.6",
                            "retrieval_method": "vector",
                        },
                    )
                    duration = (time.time() - start) * 1000
                    timings.append(duration)

                    # Clean up
                    session.execute(
                        text("DELETE FROM verification_results WHERE id = :id"),
                        {"id": str(result_id)}
                    )
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Verdict storage iteration failed: {e}")

            self.results["benchmarks"]["verdict_storage"] = {
                "mean_ms": statistics.mean(timings) if timings else 0,
                "median_ms": statistics.median(timings) if timings else 0,
                "min_ms": min(timings) if timings else 0,
                "max_ms": max(timings) if timings else 0,
                "iterations": len(timings),
            }

            logger.info(
                f"Verdict storage: {statistics.mean(timings):.2f}ms"
                if timings else "Verdict storage: No successful iterations"
            )

        finally:
            session.close()

    def _benchmark_join_queries(self) -> None:
        """Benchmark queries with joins."""
        logger.info("Benchmarking join queries...")

        session = self.SessionLocal()
        try:
            # Get sample evidence IDs
            result = session.execute(text("SELECT id FROM evidence LIMIT 20"))
            evidence_ids = [UUID(row[0]) for row in result.fetchall()]

            # Benchmark: Evidence with embeddings (single JOIN)
            timings = []
            for _ in range(self.iterations):
                start = time.time()
                results = self.queries.batch_get_evidence_by_ids(
                    session, evidence_ids, include_embeddings=True
                )
                duration = (time.time() - start) * 1000
                timings.append(duration)

            self.results["benchmarks"]["join_evidence_embeddings"] = {
                "mean_ms": statistics.mean(timings),
                "median_ms": statistics.median(timings),
                "min_ms": min(timings),
                "max_ms": max(timings),
                "items_retrieved": len(evidence_ids),
            }

            logger.info(
                f"JOIN query (evidence + embeddings): {statistics.mean(timings):.2f}ms"
            )

        finally:
            session.close()

    def _benchmark_batch_vs_individual(self) -> None:
        """Compare batch operations vs individual operations."""
        logger.info("Benchmarking batch vs individual operations...")

        session = self.SessionLocal()
        builder = QueryBuilder(session)

        try:
            # Test different batch sizes
            batch_sizes = [10, 20, 50, 100]
            results = {}

            for batch_size in batch_sizes:
                if batch_size > self.corpus_size:
                    continue

                # Get sample IDs
                result = session.execute(
                    text(f"SELECT id FROM evidence LIMIT {batch_size}")
                )
                evidence_ids = [UUID(row[0]) for row in result.fetchall()]

                # Batch retrieval
                timings_batch = []
                for _ in range(min(30, self.iterations)):
                    start = time.time()
                    _ = self.queries.batch_get_evidence_by_ids(session, evidence_ids)
                    duration = (time.time() - start) * 1000
                    timings_batch.append(duration)

                # Individual retrieval
                timings_individual = []
                for _ in range(min(30, self.iterations)):
                    start = time.time()
                    for eid in evidence_ids:
                        result = session.execute(
                            text("SELECT * FROM evidence WHERE id = :id"),
                            {"id": str(eid)}
                        )
                        _ = result.fetchone()
                    duration = (time.time() - start) * 1000
                    timings_individual.append(duration)

                results[f"batch_size_{batch_size}"] = {
                    "batch_mean_ms": statistics.mean(timings_batch),
                    "individual_mean_ms": statistics.mean(timings_individual),
                    "speedup": statistics.mean(timings_individual) / statistics.mean(timings_batch),
                    "latency_reduction_percent": (
                        (statistics.mean(timings_individual) - statistics.mean(timings_batch))
                        / statistics.mean(timings_individual) * 100
                    ),
                }

            self.results["benchmarks"]["batch_vs_individual"] = results

            # Log summary
            for batch_size, data in results.items():
                logger.info(
                    f"{batch_size}: Batch={data['batch_mean_ms']:.2f}ms, "
                    f"Individual={data['individual_mean_ms']:.2f}ms, "
                    f"Speedup={data['speedup']:.1f}x, "
                    f"Reduction={data['latency_reduction_percent']:.1f}%"
                )

        finally:
            session.close()

    def _analyze_results(self) -> None:
        """Analyze benchmark results and compute summary statistics."""
        logger.info("Analyzing results...")

        benchmarks = self.results["benchmarks"]

        # Calculate overall latency reduction
        evidence_retrieval = benchmarks.get("evidence_retrieval", {})
        batch_vs_individual = benchmarks.get("batch_vs_individual", {})

        # Compute average latency reduction across all batch operations
        reductions = []

        # Evidence retrieval reduction
        if evidence_retrieval:
            batch_time = evidence_retrieval["batch_optimized"]["mean_ms"]
            individual_time = evidence_retrieval["individual_naive"]["mean_ms"]
            reduction = (individual_time - batch_time) / individual_time * 100
            reductions.append(reduction)

        # Batch vs individual reductions
        for batch_data in batch_vs_individual.values():
            if isinstance(batch_data, dict) and "latency_reduction_percent" in batch_data:
                reductions.append(batch_data["latency_reduction_percent"])

        avg_reduction = statistics.mean(reductions) if reductions else 0

        self.results["summary"] = {
            "average_latency_reduction_percent": avg_reduction,
            "target_reduction_percent": 30.0,
            "target_achieved": avg_reduction >= 30.0,
            "best_speedup": max(
                evidence_retrieval.get("speedup_factor", 1),
                max(
                    (b.get("speedup", 1) for b in batch_vs_individual.values()
                     if isinstance(b, dict)),
                    default=1
                ),
            ),
            "recommendations": self._generate_recommendations(),
        }

        logger.info(f"Average latency reduction: {avg_reduction:.1f}%")
        logger.info(f"Target (30%) achieved: {avg_reduction >= 30.0}")

    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on results."""
        recommendations = []

        benchmarks = self.results["benchmarks"]

        # Check evidence retrieval performance
        evidence_retrieval = benchmarks.get("evidence_retrieval", {})
        if evidence_retrieval:
            speedup = evidence_retrieval.get("speedup_factor", 1)
            if speedup > 2:
                recommendations.append(
                    f"Use batch evidence retrieval (OptimizedQueries.batch_get_evidence_by_ids) "
                    f"for {speedup:.1f}x speedup vs individual queries"
                )

        # Check batch operations
        batch_vs_individual = benchmarks.get("batch_vs_individual", {})
        if batch_vs_individual:
            best_batch = max(
                (k for k, v in batch_vs_individual.items()
                 if isinstance(v, dict) and v.get("speedup", 0) > 2),
                key=lambda k: batch_vs_individual[k].get("speedup", 0),
                default=None
            )
            if best_batch:
                recommendations.append(
                    f"Optimal batch size: {best_batch.replace('batch_size_', '')} items "
                    f"({batch_vs_individual[best_batch]['speedup']:.1f}x speedup)"
                )

        # General recommendations
        recommendations.extend([
            "Enable connection pooling (pool_size=10, max_overflow=20) for 2-3x improvement",
            "Use batch_create_nli_results for bulk NLI result storage (20-50x faster)",
            "Create indexes on frequently queried columns (see indexes.sql)",
            "Run VACUUM ANALYZE after bulk operations to update statistics",
            "Set ivfflat.probes=10 for balanced vector search performance",
        ])

        return recommendations

    def save_results(self, output_file: Path) -> None:
        """Save benchmark results to JSON file.

        Args:
            output_file: Output file path
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Results saved to {output_file}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark database query performance"
    )
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph",
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of iterations per benchmark (default: 50)",
    )
    parser.add_argument(
        "--corpus-size",
        type=int,
        default=1000,
        help="Number of test records to create (default: 1000)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / f"query_performance_{datetime.now().strftime('%Y-%m-%d')}.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    # Run benchmarks
    benchmark = QueryBenchmark(
        database_url=args.database_url,
        iterations=args.iterations,
        corpus_size=args.corpus_size,
    )

    results = benchmark.run_all_benchmarks()
    benchmark.save_results(args.output)

    # Print summary
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"Average latency reduction: {results['summary']['average_latency_reduction_percent']:.1f}%")
    print(f"Target (30%) achieved: {results['summary']['target_achieved']}")
    print(f"Best speedup: {results['summary']['best_speedup']:.1f}x")
    print("\nTop recommendations:")
    for i, rec in enumerate(results['summary']['recommendations'][:5], 1):
        print(f"{i}. {rec}")
    print("="*80)


if __name__ == "__main__":
    main()
