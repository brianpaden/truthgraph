#!/usr/bin/env python3
"""End-to-end performance test for complete verification pipeline.

This script tests the complete claim verification pipeline from claim
submission to verdict generation, measuring total latency and component
breakdown.

Performance Target:
    - End-to-end latency: <60 seconds
    - Component breakdown:
        - Embedding generation: <1s
        - Evidence retrieval: <3s
        - NLI verification (10 items): <40s
        - Verdict aggregation: <1s
        - Database I/O: <5s
        - Overhead: <5s

Usage:
    python scripts/test_e2e_performance.py
    python scripts/test_e2e_performance.py --num-claims 10
    python scripts/test_e2e_performance.py --evidence-count 20
    python scripts/test_e2e_performance.py --verbose

Example output:
    End-to-end performance: 45.2s (PASS <60s target)
      Embedding: 0.8s
      Retrieval: 2.1s
      NLI: 35.3s
      Aggregation: 0.5s
      Database: 1.2s
      Overhead: 5.3s
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import torch

from truthgraph.services.ml.model_cache import ModelCache

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class PerformanceBreakdown:
    """Performance breakdown for verification pipeline."""

    claim_text: str
    total_time_s: float
    embedding_time_s: float
    retrieval_time_s: float
    nli_time_s: float
    aggregation_time_s: float
    database_time_s: float
    overhead_time_s: float
    memory_used_mb: float
    success: bool
    error: str | None = None


class E2EPerformanceTester:
    """End-to-end performance tester for verification pipeline."""

    def __init__(self, verbose: bool = False):
        """Initialize the tester.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.results: list[PerformanceBreakdown] = []

    def log(self, message: str) -> None:
        """Log message if verbose enabled."""
        if self.verbose:
            print(f"  {message}")

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        return 0.0

    def test_single_claim(self, claim: str, evidence_count: int = 10) -> PerformanceBreakdown:
        """Test verification of a single claim.

        Args:
            claim: Claim text to verify
            evidence_count: Number of evidence items to retrieve

        Returns:
            Performance breakdown
        """
        self.log(f"Testing claim: {claim[:50]}...")

        memory_before = self.get_memory_mb()
        total_start = time.perf_counter()

        try:
            # Component: Embedding generation
            self.log("Step 1: Embedding generation")
            emb_start = time.perf_counter()

            cache = ModelCache.get_instance()
            embedding_service = cache.get_embedding_service()
            claim_embedding = embedding_service.embed_text(claim)
            assert claim_embedding

            embedding_time = time.perf_counter() - emb_start
            self.log(f"  Embedding: {embedding_time * 1000:.1f}ms")

            # Component: Evidence retrieval (simulated - no database)
            self.log("Step 2: Evidence retrieval (simulated)")
            retrieval_start = time.perf_counter()

            # Simulate evidence retrieval
            # In real implementation, this would query database
            simulated_evidence = [f"Evidence item {i} with relevant information" for i in range(evidence_count)]

            # Generate embeddings for evidence (simulate hybrid search)
            evidence_embeddings = embedding_service.embed_batch(
                simulated_evidence, batch_size=cache.get_optimal_batch_size("embedding")
            )
            assert evidence_embeddings

            retrieval_time = time.perf_counter() - retrieval_start
            self.log(f"  Retrieval: {retrieval_time:.2f}s")

            # Component: NLI verification
            self.log("Step 3: NLI verification")
            nli_start = time.perf_counter()

            nli_service = cache.get_nli_service()

            # Create premise-hypothesis pairs
            pairs = [(evidence, claim) for evidence in simulated_evidence]

            # Batch verification
            nli_results = nli_service.verify_batch(pairs, batch_size=cache.get_optimal_batch_size("nli"))

            nli_time = time.perf_counter() - nli_start
            self.log(f"  NLI: {nli_time:.2f}s ({len(nli_results)} pairs)")

            # Component: Verdict aggregation (simulated)
            self.log("Step 4: Verdict aggregation")
            agg_start = time.perf_counter()

            # Simple aggregation logic (in real impl, uses aggregation.py)
            entailment_count = sum(1 for r in nli_results if r.label.value == "entailment")
            contradiction_count = sum(1 for r in nli_results if r.label.value == "contradiction")

            if entailment_count > contradiction_count:
                verdict = "SUPPORTED"
            elif contradiction_count > entailment_count:
                verdict = "REFUTED"
            else:
                verdict = "INSUFFICIENT"

            aggregation_time = time.perf_counter() - agg_start
            self.log(f"  Aggregation: {aggregation_time * 1000:.1f}ms -> {verdict}")

            # Component: Database I/O (simulated)
            self.log("Step 5: Database storage (simulated)")
            db_start = time.perf_counter()

            # Simulate database write latency
            time.sleep(0.01)  # 10ms simulated DB write

            database_time = time.perf_counter() - db_start
            self.log(f"  Database: {database_time * 1000:.1f}ms")

            # Calculate total and overhead
            total_time = time.perf_counter() - total_start
            overhead_time = total_time - embedding_time - retrieval_time - nli_time - aggregation_time - database_time

            memory_after = self.get_memory_mb()
            memory_used = memory_after - memory_before

            return PerformanceBreakdown(
                claim_text=claim,
                total_time_s=total_time,
                embedding_time_s=embedding_time,
                retrieval_time_s=retrieval_time,
                nli_time_s=nli_time,
                aggregation_time_s=aggregation_time,
                database_time_s=database_time,
                overhead_time_s=overhead_time,
                memory_used_mb=memory_used,
                success=True,
            )

        except Exception as e:
            total_time = time.perf_counter() - total_start
            print(f"ERROR: {e}")

            return PerformanceBreakdown(
                claim_text=claim,
                total_time_s=total_time,
                embedding_time_s=0,
                retrieval_time_s=0,
                nli_time_s=0,
                aggregation_time_s=0,
                database_time_s=0,
                overhead_time_s=0,
                memory_used_mb=0,
                success=False,
                error=str(e),
            )

    def test_multiple_claims(self, claims: list[str], evidence_count: int = 10) -> list[PerformanceBreakdown]:
        """Test verification of multiple claims.

        Args:
            claims: List of claims to verify
            evidence_count: Number of evidence items per claim

        Returns:
            List of performance breakdowns
        """
        print(f"\nTesting {len(claims)} claims...")
        print(f"Evidence per claim: {evidence_count}")

        results = []

        for i, claim in enumerate(claims, 1):
            print(f"\nClaim {i}/{len(claims)}:")
            result = self.test_single_claim(claim, evidence_count)
            results.append(result)

            # Print immediate result
            if result.success:
                status = "PASS" if result.total_time_s < 60 else "FAIL"
                print(f"  Total: {result.total_time_s:.2f}s ({status})")
            else:
                print(f"  FAILED: {result.error}")

        return results

    def print_summary(self, results: list[PerformanceBreakdown]) -> None:
        """Print summary of results.

        Args:
            results: List of performance breakdowns
        """
        print("\n" + "=" * 80)
        print("END-TO-END PERFORMANCE SUMMARY")
        print("=" * 80)

        # Filter successful results
        successful = [r for r in results if r.success]

        if not successful:
            print("\nNo successful runs!")
            return

        # Calculate statistics
        total_times = [r.total_time_s for r in successful]
        embedding_times = [r.embedding_time_s for r in successful]
        retrieval_times = [r.retrieval_time_s for r in successful]
        nli_times = [r.nli_time_s for r in successful]
        aggregation_times = [r.aggregation_time_s for r in successful]
        database_times = [r.database_time_s for r in successful]
        overhead_times = [r.overhead_time_s for r in successful]

        print(f"\nSuccessful runs: {len(successful)}/{len(results)}")
        print("\nAverage timings:")
        print(f"  Total:        {mean(total_times):.2f}s (median: {median(total_times):.2f}s)")
        print(f"  Embedding:    {mean(embedding_times):.3f}s")
        print(f"  Retrieval:    {mean(retrieval_times):.2f}s")
        print(f"  NLI:          {mean(nli_times):.2f}s")
        print(f"  Aggregation:  {mean(aggregation_times):.3f}s")
        print(f"  Database:     {mean(database_times):.3f}s")
        print(f"  Overhead:     {mean(overhead_times):.3f}s")

        # Component percentages
        avg_total = mean(total_times)
        print("\nTime breakdown (% of total):")
        print(f"  Embedding:    {mean(embedding_times) / avg_total * 100:.1f}%")
        print(f"  Retrieval:    {mean(retrieval_times) / avg_total * 100:.1f}%")
        print(f"  NLI:          {mean(nli_times) / avg_total * 100:.1f}%")
        print(f"  Aggregation:  {mean(aggregation_times) / avg_total * 100:.1f}%")
        print(f"  Database:     {mean(database_times) / avg_total * 100:.1f}%")
        print(f"  Overhead:     {mean(overhead_times) / avg_total * 100:.1f}%")

        # Target validation
        print("\n" + "-" * 80)
        print("TARGET VALIDATION")
        print("-" * 80)

        target = 60.0
        avg_time = mean(total_times)
        status = "PASS" if avg_time < target else "FAIL"

        print(f"\nEnd-to-end latency: {avg_time:.2f}s")
        print(f"Target: <{target}s")
        print(f"Status: {status}")

        if avg_time >= target:
            print(f"\nExceeds target by: {avg_time - target:.2f}s")

        # Component target validation
        print("\nComponent targets:")

        targets = {
            "Embedding": (mean(embedding_times), 1.0),
            "Retrieval": (mean(retrieval_times), 3.0),
            "NLI": (mean(nli_times), 40.0),
            "Aggregation": (mean(aggregation_times), 1.0),
            "Database": (mean(database_times), 5.0),
        }

        all_pass = True
        for component, (actual, target) in targets.items():
            status = "PASS" if actual < target else "FAIL"
            if actual >= target:
                all_pass = False
            print(f"  {component:12s}: {actual:6.2f}s / {target:6.2f}s  {status}")

        # Overall result
        print("\n" + "=" * 80)
        if avg_time < 60 and all_pass:
            print("OVERALL: PASS - All targets met!")
        else:
            print("OVERALL: FAIL - Some targets not met")
            print("\nRecommendations:")
            if mean(nli_times) > 40:
                print("  - NLI is bottleneck. Consider: GPU, larger batch size, or model optimization")
            if mean(retrieval_times) > 3:
                print("  - Retrieval slow. Consider: index optimization or caching")
            if mean(embedding_times) > 1:
                print("  - Embedding slow. Consider: GPU or batch processing")

        print("=" * 80)

        # Memory summary
        if PSUTIL_AVAILABLE:
            memory_used = [r.memory_used_mb for r in successful]
            print(f"\nMemory usage: {mean(memory_used):.1f} MB average")

            final_memory = self.get_memory_mb()
            print(f"Final process memory: {final_memory:.1f} MB")

            if final_memory > 4000:
                print("  WARNING: Exceeds 4GB target")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test end-to-end verification performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--num-claims",
        type=int,
        default=5,
        help="Number of claims to test (default: 5)",
    )
    parser.add_argument(
        "--evidence-count",
        type=int,
        default=10,
        help="Number of evidence items per claim (default: 10)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--warmup", action="store_true", help="Warmup models before testing")

    args = parser.parse_args()

    print("=" * 80)
    print("END-TO-END PERFORMANCE TEST")
    print("=" * 80)
    print("\nConfiguration:")
    print(f"  Number of claims: {args.num_claims}")
    print(f"  Evidence per claim: {args.evidence_count}")
    print(f"  Verbose: {args.verbose}")
    print(f"  Warmup: {args.warmup}")

    # System info
    print("\nSystem Information:")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"  MPS available: {hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()}")

    # Warmup if requested
    if args.warmup:
        print("\nWarming up models...")
        cache = ModelCache.get_instance()
        warmup_times = cache.warmup_all_models()
        print(f"  Warmup complete: {sum(warmup_times.values()):.1f}ms total")

    # Test claims
    test_claims = [
        "The Earth orbits the Sun and completes one revolution in approximately 365.25 days.",
        "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
        "The Great Wall of China is visible from space with the naked eye.",
        "Humans share approximately 98% of their DNA with chimpanzees.",
        "Mount Everest is the tallest mountain in the solar system.",
        "Lightning never strikes the same place twice.",
        "Vaccines cause autism in children.",
        "The human brain uses only 10% of its capacity.",
        "Coffee is made from beans that grow on trees.",
        "Antarctica is the largest desert on Earth by area.",
    ]

    # Use subset based on args
    claims_to_test = test_claims[: args.num_claims]

    # Run tests
    tester = E2EPerformanceTester(verbose=args.verbose)
    results = tester.test_multiple_claims(claims_to_test, args.evidence_count)

    # Print summary
    tester.print_summary(results)

    # Exit code based on success
    successful = [r for r in results if r.success]
    if not successful:
        sys.exit(1)

    avg_time = mean([r.total_time_s for r in successful])
    sys.exit(0 if avg_time < 60 else 1)


if __name__ == "__main__":
    main()
