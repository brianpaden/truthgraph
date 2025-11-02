#!/usr/bin/env python3
"""Comprehensive benchmark for end-to-end verification pipeline.

This script measures complete pipeline performance including:
- Embedding generation
- Evidence retrieval
- NLI verification
- Verdict aggregation
- Result storage

Performance Targets:
    - End-to-end latency: <60 seconds per claim
    - Throughput: >1 claim per minute
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Embedding, Evidence
from truthgraph.services.verification_pipeline_service import VerificationPipelineService


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics."""
    if not PSUTIL_AVAILABLE:
        return {}

    process = psutil.Process()
    mem_info = process.memory_info()
    return {"rss_mb": mem_info.rss / (1024 * 1024)}


def load_test_claims(claims_file: Path) -> list[dict[str, Any]]:
    """Load test claims from JSON file.

    Args:
        claims_file: Path to test claims JSON

    Returns:
        List of claim dictionaries
    """
    with open(claims_file) as f:
        data = json.load(f)
    return data.get("claims", [])


def create_test_evidence_corpus(
    session, num_evidence: int, embedding_dim: int, tenant_id: str
) -> None:
    """Create test evidence corpus.

    Args:
        session: Database session
        num_evidence: Number of evidence items
        embedding_dim: Embedding dimension
        tenant_id: Tenant ID
    """
    print(f"Creating test evidence corpus: {num_evidence} items...")

    evidence_templates = [
        "The Earth's global average surface temperature has increased by approximately 1.1°C since the pre-industrial period.",
        "Water has a boiling point of 100 degrees Celsius at standard atmospheric pressure at sea level.",
        "The Eiffel Tower in Paris was completed in 1889 as the entrance arch for the World's Fair.",
        "COVID-19 vaccines have been shown to reduce severe illness and death from the disease.",
        "The Apollo 11 moon landing in 1969 was extensively documented and verified by independent sources.",
        "Clinical studies show vitamin C has minimal effect on preventing or curing the common cold.",
        "Neuroscience research demonstrates that humans actively use all regions of their brain.",
        "Python programming language was created by Guido van Rossum with first release in 1991.",
        "Donald Trump was elected as the 45th President of the United States in 2016.",
        "Joe Biden was inaugurated as the 46th President of the United States in January 2021.",
    ]

    batch_size = 100
    for i in range(0, num_evidence, batch_size):
        evidence_batch = []
        embedding_batch = []

        for j in range(min(batch_size, num_evidence - i)):
            idx = i + j
            evidence_id = uuid4()

            # Cycle through templates
            content = evidence_templates[idx % len(evidence_templates)]
            content = f"{content} (Evidence #{idx})"

            evidence = Evidence(
                id=evidence_id,
                content=content,
                source_url=f"https://test.com/evidence/{idx}",
                source_type="test_corpus",
            )
            evidence_batch.append(evidence)

            # Create embedding
            pattern = idx / num_evidence
            embedding_vector = [pattern + (0.001 * k) for k in range(embedding_dim)]

            embedding = Embedding(
                entity_type="evidence",
                entity_id=evidence_id,
                embedding=embedding_vector,
                tenant_id=tenant_id,
            )
            embedding_batch.append(embedding)

        session.bulk_save_objects(evidence_batch)
        session.bulk_save_objects(embedding_batch)
        session.commit()

        if (i + batch_size) % 500 == 0 or i + batch_size >= num_evidence:
            print(f"  Created {min(i + batch_size, num_evidence)}/{num_evidence} items")


async def benchmark_single_claim(
    service: VerificationPipelineService,
    session,
    claim_text: str,
    claim_id: uuid4,
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark single claim verification.

    Args:
        service: Pipeline service
        session: Database session
        claim_text: Claim text
        claim_id: Claim ID
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    start_time = time.perf_counter()

    try:
        result = await service.verify_claim(
            db=session,
            claim_id=claim_id,
            claim_text=claim_text,
            top_k_evidence=10,
            min_similarity=0.3,
            use_cache=False,
            store_result=False,
            tenant_id=tenant_id,
        )

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        return {
            "success": True,
            "duration_ms": duration_ms,
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "evidence_count": len(result.evidence_items),
            "pipeline_duration_ms": result.pipeline_duration_ms,
        }

    except Exception as e:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        return {
            "success": False,
            "duration_ms": duration_ms,
            "error": str(e),
        }


async def benchmark_pipeline_latency(
    service: VerificationPipelineService,
    SessionLocal,
    test_claims: list[dict[str, Any]],
    num_iterations: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark pipeline latency.

    Args:
        service: Pipeline service
        SessionLocal: Session factory
        test_claims: List of test claims
        num_iterations: Number of iterations
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Pipeline Latency")
    print("=" * 80)

    print(f"Running {num_iterations} iterations with {len(test_claims)} claims...")

    all_durations = []
    all_results = []
    verdict_counts = {}

    for iteration in range(num_iterations):
        print(f"\nIteration {iteration + 1}/{num_iterations}")

        for i, claim_data in enumerate(test_claims):
            claim_text = claim_data["text"]
            claim_id = uuid4()

            session = SessionLocal()
            try:
                result = await benchmark_single_claim(
                    service, session, claim_text, claim_id, tenant_id
                )

                all_results.append(result)

                if result["success"]:
                    all_durations.append(result["duration_ms"])
                    verdict = result["verdict"]
                    verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

                    status = "PASS" if result["duration_ms"] < 60000 else "FAIL"
                    print(
                        f"  [{i + 1}/{len(test_claims)}] {status} {result['duration_ms']:.0f}ms "
                        f"{verdict} ({result['confidence']:.2f}) {result['evidence_count']} evidence"
                    )
                else:
                    print(f"  [{i + 1}/{len(test_claims)}] ERROR: {result.get('error', 'Unknown')}")

            finally:
                session.close()

    # Calculate statistics
    if all_durations:
        durations_sorted = sorted(all_durations)

        results = {
            "total_verifications": len(all_results),
            "successful": len(all_durations),
            "failed": len(all_results) - len(all_durations),
            "mean_duration_ms": mean(all_durations),
            "median_duration_ms": median(all_durations),
            "min_duration_ms": min(all_durations),
            "max_duration_ms": max(all_durations),
            "p95_duration_ms": durations_sorted[int(len(durations_sorted) * 0.95)],
            "p99_duration_ms": durations_sorted[int(len(durations_sorted) * 0.99)],
            "stdev_duration_ms": stdev(all_durations) if len(all_durations) > 1 else 0,
            "verdict_distribution": verdict_counts,
            "passed_count": sum(1 for d in all_durations if d < 60000),
        }

        # Print results
        print("\nResults:")
        print(f"  Total verifications:  {results['total_verifications']}")
        print(f"  Successful:           {results['successful']}")
        print(f"  Failed:               {results['failed']}")
        print(f"  Mean duration:        {results['mean_duration_ms']:.1f} ms")
        print(f"  Median duration:      {results['median_duration_ms']:.1f} ms")
        print(f"  Min duration:         {results['min_duration_ms']:.1f} ms")
        print(f"  Max duration:         {results['max_duration_ms']:.1f} ms")
        print(f"  P95 duration:         {results['p95_duration_ms']:.1f} ms")
        print(f"  P99 duration:         {results['p99_duration_ms']:.1f} ms")
        print(f"  Passed (<60s):        {results['passed_count']}/{results['successful']}")
        print(f"  Verdict distribution: {verdict_counts}")

        # Check target
        target_ms = 60000
        passed = results["mean_duration_ms"] < target_ms
        status = "PASS" if passed else "FAIL"
        print(f"\nTarget: <{target_ms / 1000:.0f}s average - {status}")

        results["target_ms"] = target_ms
        results["passed"] = passed

        return results
    else:
        return {"error": "No successful verifications"}


async def benchmark_throughput(
    service: VerificationPipelineService,
    SessionLocal,
    test_claims: list[dict[str, Any]],
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark pipeline throughput.

    Args:
        service: Pipeline service
        SessionLocal: Session factory
        test_claims: List of test claims
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Pipeline Throughput")
    print("=" * 80)

    print(f"Processing {len(test_claims)} claims sequentially...")

    start_time = time.perf_counter()
    successful = 0

    for i, claim_data in enumerate(test_claims):
        claim_text = claim_data["text"]
        claim_id = uuid4()

        session = SessionLocal()
        try:
            result = await benchmark_single_claim(service, session, claim_text, claim_id, tenant_id)

            if result["success"]:
                successful += 1

            if (i + 1) % 5 == 0:
                elapsed = time.perf_counter() - start_time
                rate = (i + 1) / elapsed
                print(f"  Processed {i + 1}/{len(test_claims)} ({rate:.2f} claims/sec)")

        finally:
            session.close()

    end_time = time.perf_counter()
    total_time = end_time - start_time

    results = {
        "total_claims": len(test_claims),
        "successful": successful,
        "total_time_s": total_time,
        "throughput_claims_per_sec": successful / total_time,
        "avg_time_per_claim_s": total_time / successful if successful > 0 else 0,
    }

    print("\nResults:")
    print(f"  Total time:         {results['total_time_s']:.1f} s")
    print(f"  Throughput:         {results['throughput_claims_per_sec']:.2f} claims/sec")
    print(f"  Avg per claim:      {results['avg_time_per_claim_s']:.1f} s")

    # Check target (>1 claim per minute = >0.0167 claims/sec)
    target = 0.0167
    passed = results["throughput_claims_per_sec"] > target
    status = "PASS" if passed else "FAIL"
    print(f"\nTarget: >1 claim/minute - {status}")

    results["target_claims_per_sec"] = target
    results["passed"] = passed

    return results


def save_results(results: dict[str, Any], output_path: Path) -> None:
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


async def main_async() -> int:
    """Async main function."""
    parser = argparse.ArgumentParser(description="Comprehensive pipeline benchmark")
    parser.add_argument(
        "--claims-file",
        type=str,
        default="tests/fixtures/test_claims.json",
        help="Path to test claims JSON",
    )
    parser.add_argument(
        "--num-evidence", type=int, default=1000, help="Number of evidence items to create"
    )
    parser.add_argument(
        "--embedding-dim", type=int, default=384, choices=[384, 1536], help="Embedding dimension"
    )
    parser.add_argument("--iterations", type=int, default=2, help="Iterations per claim")
    parser.add_argument(
        "--database-url", type=str, help="Database URL (default: from DATABASE_URL env)"
    )
    parser.add_argument(
        "--output", type=str, help="Output JSON file (default: results/pipeline_TIMESTAMP.json)"
    )
    parser.add_argument("--skip-latency", action="store_true", help="Skip latency benchmark")
    parser.add_argument("--skip-throughput", action="store_true", help="Skip throughput benchmark")

    args = parser.parse_args()

    # Database URL from env var or use default
    # Default uses 'postgres' host for Docker container, change to 'localhost' for local dev
    database_url = args.database_url or os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://truthgraph:changeme_to_secure_password@postgres:5432/truthgraph",
    )

    print("=" * 80)
    print("VERIFICATION PIPELINE COMPREHENSIVE BENCHMARK")
    print("=" * 80)
    print(f"\nClaims file:    {args.claims_file}")
    print(f"Evidence count: {args.num_evidence}")
    print(f"Embedding dim:  {args.embedding_dim}")
    print(f"Iterations:     {args.iterations}")
    print(f"Database:       {database_url.split('@')[-1]}")

    # Load claims
    claims_path = Path(args.claims_file)
    if not claims_path.is_absolute():
        claims_path = project_root / claims_path

    test_claims = load_test_claims(claims_path)
    print(f"\nLoaded {len(test_claims)} test claims")

    # Setup database
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)

    try:
        Base.metadata.create_all(engine)

        # Create evidence corpus
        tenant_id = "benchmark_pipeline"
        session = SessionLocal()
        try:
            create_test_evidence_corpus(session, args.num_evidence, args.embedding_dim, tenant_id)
        finally:
            session.close()

        # Initialize service
        print("\nInitializing verification pipeline...")
        service = VerificationPipelineService(embedding_dimension=args.embedding_dim)

        # Warm up
        print("Warming up models...")
        session = SessionLocal()
        try:
            if test_claims:
                await benchmark_single_claim(
                    service, session, test_claims[0]["text"], uuid4(), tenant_id
                )
        finally:
            session.close()

        # Run benchmarks
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "python_version": sys.version.split()[0],
                "embedding_dimension": args.embedding_dim,
                "num_evidence": args.num_evidence,
                "database": database_url.split("@")[-1],
            },
            "benchmarks": {},
        }

        if not args.skip_latency:
            all_results["benchmarks"]["latency"] = await benchmark_pipeline_latency(
                service,
                SessionLocal,
                test_claims[: min(5, len(test_claims))],
                args.iterations,
                tenant_id,
            )

        if not args.skip_throughput:
            all_results["benchmarks"]["throughput"] = await benchmark_throughput(
                service, SessionLocal, test_claims[: min(10, len(test_claims))], tenant_id
            )

        # Memory
        memory = get_memory_usage()
        if "rss_mb" in memory:
            all_results["memory_usage_mb"] = memory["rss_mb"]
            print(f"\nPeak memory usage: {memory['rss_mb']:.1f} MB")

        # Summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        all_passed = True

        if "latency" in all_results["benchmarks"]:
            lat = all_results["benchmarks"]["latency"]
            if "passed" in lat:
                passed = lat["passed"]
                all_passed = all_passed and passed
                status = "PASS" if passed else "FAIL"
                print(f"\nPipeline latency:       {lat['mean_duration_ms'] / 1000:.1f}s - {status}")

        if "throughput" in all_results["benchmarks"]:
            thr = all_results["benchmarks"]["throughput"]
            if "passed" in thr:
                passed = thr["passed"]
                all_passed = all_passed and passed
                status = "PASS" if passed else "FAIL"
                print(
                    f"Pipeline throughput:    {thr['throughput_claims_per_sec']:.3f} claims/sec - {status}"
                )

        # Save results
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output_path = Path(__file__).parent / "results" / f"pipeline_{timestamp}.json"

        save_results(all_results, output_path)

        print("\n" + "=" * 80)
        final_status = "ALL BENCHMARKS PASSED" if all_passed else "SOME BENCHMARKS FAILED"
        print(final_status)
        print("=" * 80)

        return 0 if all_passed else 1

    finally:
        engine.dispose()


def main() -> int:
    """Main entry point."""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nBenchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
