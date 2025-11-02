"""End-to-end performance benchmarking for VerificationPipelineService.

This script benchmarks the complete verification pipeline including:
- Embedding generation
- Evidence retrieval
- NLI verification
- Verdict aggregation
- Result storage

Performance target: <60s end-to-end for typical claim
"""

import argparse
import asyncio
import os
import statistics
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Claim
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
)


def setup_test_database(db_url: str):
    """Set up test database with sample data.

    Args:
        db_url: Database connection URL

    Returns:
        Tuple of (engine, SessionLocal, sample_claims)
    """
    engine = create_engine(db_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)

    # Create tables
    Base.metadata.create_all(engine)

    session = SessionLocal()

    # Create sample claims
    sample_claims = [
        Claim(
            id=uuid4(),
            text="The Earth orbits around the Sun",
            source_url="http://example.com/claim1",
        ),
        Claim(
            id=uuid4(),
            text="Water is composed of hydrogen and oxygen atoms",
            source_url="http://example.com/claim2",
        ),
        Claim(
            id=uuid4(),
            text="The speed of light in vacuum is approximately 299,792 kilometers per second",
            source_url="http://example.com/claim3",
        ),
        Claim(
            id=uuid4(),
            text="Python is a high-level programming language",
            source_url="http://example.com/claim4",
        ),
        Claim(
            id=uuid4(),
            text="The Great Wall of China is visible from space",
            source_url="http://example.com/claim5",
        ),
    ]

    for claim in sample_claims:
        session.add(claim)

    session.commit()
    session.close()

    return engine, SessionLocal, sample_claims


async def benchmark_single_verification(
    service: VerificationPipelineService,
    session,
    claim: Claim,
    use_cache: bool = False,
    store_result: bool = True,
) -> dict:
    """Benchmark a single claim verification.

    Args:
        service: Verification pipeline service
        session: Database session
        claim: Claim to verify
        use_cache: Whether to use caching
        store_result: Whether to store result

    Returns:
        Dictionary with benchmark results
    """
    start_time = time.time()

    result = await service.verify_claim(
        db=session,
        claim_id=claim.id,
        claim_text=claim.text,
        top_k_evidence=10,
        min_similarity=0.5,
        use_cache=use_cache,
        store_result=store_result,
    )

    end_time = time.time()
    total_duration_ms = (end_time - start_time) * 1000

    return {
        "claim_id": str(claim.id),
        "claim_text": claim.text[:50] + "..." if len(claim.text) > 50 else claim.text,
        "verdict": result.verdict.value,
        "confidence": result.confidence,
        "evidence_count": len(result.evidence_items),
        "total_duration_ms": total_duration_ms,
        "pipeline_duration_ms": result.pipeline_duration_ms,
        "met_target": total_duration_ms < 60000,  # <60s target
    }


async def run_benchmark(
    db_url: str,
    num_iterations: int = 3,
    use_cache: bool = False,
    store_results: bool = False,
):
    """Run comprehensive pipeline benchmark.

    Args:
        db_url: Database connection URL
        num_iterations: Number of iterations per claim
        use_cache: Whether to enable caching
        store_results: Whether to store results in database
    """
    print("=" * 80)
    print("Verification Pipeline End-to-End Benchmark")
    print("=" * 80)
    print()
    print(f"Database URL: {db_url}")
    print(f"Iterations per claim: {num_iterations}")
    print(f"Caching enabled: {use_cache}")
    print(f"Store results: {store_results}")
    print()

    # Setup
    print("Setting up test database...")
    engine, SessionLocal, sample_claims = setup_test_database(db_url)
    print(f"Created {len(sample_claims)} sample claims")
    print()

    # Initialize service
    print("Initializing verification pipeline service...")
    service = VerificationPipelineService(embedding_dimension=384)
    print("Service initialized")
    print()

    # Warm up models
    print("Warming up ML models...")
    session = SessionLocal()
    if sample_claims:
        warmup_claim = sample_claims[0]
        try:
            await service.verify_claim(
                db=session,
                claim_id=warmup_claim.id,
                claim_text=warmup_claim.text,
                top_k_evidence=5,
                use_cache=False,
                store_result=False,
            )
            print("Models warmed up")
        except Exception as e:
            print(f"Warmup verification failed (expected if no evidence): {e}")
    session.close()
    print()

    # Run benchmarks
    print("Running benchmarks...")
    print("-" * 80)

    all_results = []
    all_durations = []

    for iteration in range(num_iterations):
        print(f"\nIteration {iteration + 1}/{num_iterations}")
        print("-" * 40)

        for i, claim in enumerate(sample_claims, 1):
            session = SessionLocal()
            try:
                result = await benchmark_single_verification(
                    service=service,
                    session=session,
                    claim=claim,
                    use_cache=use_cache,
                    store_result=store_results,
                )

                all_results.append(result)
                all_durations.append(result["total_duration_ms"])

                status = "✓ PASS" if result["met_target"] else "✗ FAIL"
                print(
                    f"  [{i}/{len(sample_claims)}] {status} | "
                    f"{result['total_duration_ms']:.0f}ms | "
                    f"{result['verdict']} ({result['confidence']:.2f}) | "
                    f"{result['evidence_count']} evidence | "
                    f"{result['claim_text']}"
                )

            except Exception as e:
                print(f"  [!] ERROR: {e}")
            finally:
                session.close()

    # Calculate statistics
    print()
    print("=" * 80)
    print("Benchmark Results")
    print("=" * 80)
    print()

    if all_durations:
        mean_duration = statistics.mean(all_durations)
        median_duration = statistics.median(all_durations)
        min_duration = min(all_durations)
        max_duration = max(all_durations)
        stdev_duration = statistics.stdev(all_durations) if len(all_durations) > 1 else 0

        passed = sum(1 for r in all_results if r["met_target"])
        total = len(all_results)

        print(f"Total verifications: {total}")
        print(f"Passed (<60s):       {passed} ({passed / total * 100:.1f}%)")
        print(f"Failed (>=60s):      {total - passed}")
        print()
        print("Duration Statistics (ms):")
        print(f"  Mean:     {mean_duration:.2f}")
        print(f"  Median:   {median_duration:.2f}")
        print(f"  Min:      {min_duration:.2f}")
        print(f"  Max:      {max_duration:.2f}")
        print(f"  Std Dev:  {stdev_duration:.2f}")
        print()

        # Performance assessment
        if mean_duration < 60000:
            print("✓ PASS: Average pipeline duration meets <60s target")
        else:
            print("✗ FAIL: Average pipeline duration exceeds 60s target")

        if max_duration < 60000:
            print("✓ PASS: All verifications completed within 60s")
        else:
            print("⚠ WARNING: Some verifications exceeded 60s")

        print()

        # Verdict distribution
        verdict_counts = {}
        for result in all_results:
            verdict = result["verdict"]
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        print("Verdict Distribution:")
        for verdict, count in verdict_counts.items():
            print(f"  {verdict}: {count} ({count / total * 100:.1f}%)")

        print()

        # Evidence statistics
        evidence_counts = [r["evidence_count"] for r in all_results]
        if evidence_counts:
            mean_evidence = statistics.mean(evidence_counts)
            print(f"Average evidence per claim: {mean_evidence:.1f}")

    else:
        print("No results collected")

    print()
    print("=" * 80)

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark verification pipeline end-to-end performance"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://truthgraph:changeme_to_secure_password@postgres:5432/truthgraph",
        ),
        help="Database URL (default: from DATABASE_URL env var or postgres:5432)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per claim (default: 3)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Enable result caching",
    )
    parser.add_argument(
        "--store-results",
        action="store_true",
        help="Store results in database",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_benchmark(
                db_url=args.db_url,
                num_iterations=args.iterations,
                use_cache=args.use_cache,
                store_results=args.store_results,
            )
        )
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBenchmark failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
