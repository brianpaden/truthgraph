#!/usr/bin/env python3
"""Performance benchmark for vector search service.

This script benchmarks the vector search service with various corpus sizes
and query patterns to measure performance and validate the <100ms target.

Usage:
    python scripts/benchmark_vector_search.py
    python scripts/benchmark_vector_search.py --corpus-size 10000 --queries 100
"""

import argparse
import os
import sys
import time
from pathlib import Path
from statistics import mean, median, stdev
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Embedding, Evidence
from truthgraph.services.vector_search_service import VectorSearchService


def create_test_corpus(session, size: int, embedding_dim: int = 1536) -> None:
    """Create test corpus with evidence and embeddings.

    Args:
        session: Database session
        size: Number of evidence items to create
        embedding_dim: Dimension of embeddings (384 or 1536)
    """
    print(f"Creating test corpus with {size} items...")

    batch_size = 100
    for i in range(0, size, batch_size):
        batch_evidence = []
        batch_embeddings = []

        for j in range(min(batch_size, size - i)):
            evidence_id = uuid4()

            # Create evidence
            evidence = Evidence(
                id=evidence_id,
                content=f"Test evidence content {i + j}. This is sample text for benchmarking vector search performance.",
                source_url=f"https://example.com/evidence/{i + j}",
                source_type="benchmark",
            )
            batch_evidence.append(evidence)

            # Create embedding (mock, but realistic pattern)
            # Use different patterns to simulate real embeddings
            pattern_value = (i + j) / size
            embedding_vector = [pattern_value + (0.01 * k) for k in range(embedding_dim)]

            embedding = Embedding(
                entity_type="evidence",
                entity_id=evidence_id,
                embedding=embedding_vector,
                tenant_id="benchmark",
            )
            batch_embeddings.append(embedding)

        # Bulk insert
        session.bulk_save_objects(batch_evidence)
        session.bulk_save_objects(batch_embeddings)
        session.commit()

        if (i + batch_size) % 1000 == 0 or i + batch_size >= size:
            print(f"  Created {min(i + batch_size, size)}/{size} items...")

    print("Test corpus created successfully!")


def benchmark_queries(
    session, service: VectorSearchService, num_queries: int, top_k: int = 10
) -> dict:
    """Benchmark vector search queries.

    Args:
        session: Database session
        service: VectorSearchService instance
        num_queries: Number of queries to execute
        top_k: Number of results to return per query

    Returns:
        Dictionary with benchmark results
    """
    print(f"\nRunning {num_queries} benchmark queries (top_k={top_k})...")

    query_times = []
    result_counts = []

    for i in range(num_queries):
        # Create query embedding (varying patterns)
        query_pattern = i / num_queries
        query_embedding = [
            query_pattern + (0.01 * k) for k in range(service.embedding_dimension)
        ]

        # Measure query time
        start_time = time.time()
        results = service.search_similar_evidence(
            db=session,
            query_embedding=query_embedding,
            top_k=top_k,
            tenant_id="benchmark",
        )
        end_time = time.time()

        query_time_ms = (end_time - start_time) * 1000
        query_times.append(query_time_ms)
        result_counts.append(len(results))

        if (i + 1) % 10 == 0 or i == 0:
            print(
                f"  Query {i + 1}/{num_queries}: {query_time_ms:.2f}ms, {len(results)} results"
            )

    # Calculate statistics
    return {
        "num_queries": num_queries,
        "mean_time_ms": mean(query_times),
        "median_time_ms": median(query_times),
        "min_time_ms": min(query_times),
        "max_time_ms": max(query_times),
        "stdev_time_ms": stdev(query_times) if len(query_times) > 1 else 0.0,
        "mean_results": mean(result_counts),
        "total_time_ms": sum(query_times),
    }


def benchmark_batch_queries(
    session, service: VectorSearchService, batch_size: int = 10, num_batches: int = 10
) -> dict:
    """Benchmark batch vector search queries.

    Args:
        session: Database session
        service: VectorSearchService instance
        batch_size: Number of queries per batch
        num_batches: Number of batches to execute

    Returns:
        Dictionary with benchmark results
    """
    print(f"\nRunning {num_batches} batch queries (batch_size={batch_size})...")

    batch_times = []

    for i in range(num_batches):
        # Create batch of query embeddings
        query_embeddings = [
            [(i * batch_size + j) / 1000 + (0.01 * k) for k in range(service.embedding_dimension)]
            for j in range(batch_size)
        ]

        # Measure batch time
        start_time = time.time()
        results = service.search_similar_evidence_batch(
            db=session, query_embeddings=query_embeddings, tenant_id="benchmark"
        )
        end_time = time.time()

        batch_time_ms = (end_time - start_time) * 1000
        batch_times.append(batch_time_ms)

        if (i + 1) % 5 == 0 or i == 0:
            total_results = sum(len(r) for r in results)
            print(
                f"  Batch {i + 1}/{num_batches}: {batch_time_ms:.2f}ms, {total_results} total results"
            )

    return {
        "num_batches": num_batches,
        "batch_size": batch_size,
        "mean_batch_time_ms": mean(batch_times),
        "mean_per_query_ms": mean(batch_times) / batch_size,
        "total_time_ms": sum(batch_times),
    }


def print_results(results: dict, target_ms: float = 100.0) -> None:
    """Print benchmark results in a formatted manner.

    Args:
        results: Dictionary with benchmark results
        target_ms: Target query time in milliseconds
    """
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)

    if "mean_time_ms" in results:
        print("\nQuery Statistics:")
        print(f"  Number of queries:  {results['num_queries']}")
        print(f"  Mean query time:    {results['mean_time_ms']:.2f}ms")
        print(f"  Median query time:  {results['median_time_ms']:.2f}ms")
        print(f"  Min query time:     {results['min_time_ms']:.2f}ms")
        print(f"  Max query time:     {results['max_time_ms']:.2f}ms")
        print(f"  Std deviation:      {results['stdev_time_ms']:.2f}ms")
        print(f"  Mean results:       {results['mean_results']:.1f}")

        # Check against target
        if results["mean_time_ms"] < target_ms:
            print(f"\n  ✓ PASSED: Mean query time < {target_ms}ms target")
        else:
            print(
                f"\n  ✗ FAILED: Mean query time exceeds {target_ms}ms target "
                f"(by {results['mean_time_ms'] - target_ms:.2f}ms)"
            )

    if "mean_batch_time_ms" in results:
        print("\nBatch Query Statistics:")
        print(f"  Number of batches:      {results['num_batches']}")
        print(f"  Batch size:             {results['batch_size']}")
        print(f"  Mean batch time:        {results['mean_batch_time_ms']:.2f}ms")
        print(f"  Mean per-query time:    {results['mean_per_query_ms']:.2f}ms")

    print("\n" + "=" * 60)


def main():
    """Main benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark vector search performance"
    )
    parser.add_argument(
        "--corpus-size",
        type=int,
        default=1000,
        help="Number of evidence items to create (default: 1000)",
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=50,
        help="Number of single queries to benchmark (default: 50)",
    )
    parser.add_argument(
        "--batch-queries",
        type=int,
        default=10,
        help="Number of batch queries to benchmark (default: 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Size of each batch query (default: 10)",
    )
    parser.add_argument(
        "--top-k", type=int, default=10, help="Number of results per query (default: 10)"
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=1536,
        choices=[384, 1536],
        help="Embedding dimension (default: 1536)",
    )
    parser.add_argument(
        "--skip-corpus-creation",
        action="store_true",
        help="Skip corpus creation (use existing data)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL (default: from DATABASE_URL env var)",
    )

    args = parser.parse_args()

    # Get database URL
    database_url = args.database_url or os.getenv(
        "DATABASE_URL", "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph"
    )

    print("Vector Search Performance Benchmark")
    print("=" * 60)
    print(f"Corpus size:      {args.corpus_size}")
    print(f"Single queries:   {args.queries}")
    print(f"Batch queries:    {args.batch_queries}")
    print(f"Batch size:       {args.batch_size}")
    print(f"Top-k:            {args.top_k}")
    print(f"Embedding dim:    {args.embedding_dim}")
    print(f"Database:         {database_url.split('@')[-1]}")
    print("=" * 60)

    # Create database engine and session
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Create tables if needed
        Base.metadata.create_all(engine)

        # Create test corpus
        if not args.skip_corpus_creation:
            # Clean up existing benchmark data
            session.execute(
                text("DELETE FROM embeddings WHERE tenant_id = 'benchmark'")
            )
            session.execute(
                text("DELETE FROM evidence WHERE source_type = 'benchmark'")
            )
            session.commit()

            create_test_corpus(session, args.corpus_size, args.embedding_dim)

        # Initialize service
        service = VectorSearchService(embedding_dimension=args.embedding_dim)

        # Get corpus stats
        stats = service.get_embedding_stats(
            db=session, entity_type="evidence", tenant_id="benchmark"
        )
        print("\nCorpus statistics:")
        print(f"  Total embeddings: {stats['total_embeddings']}")

        # Benchmark single queries
        single_results = benchmark_queries(
            session, service, args.queries, args.top_k
        )
        print_results(single_results)

        # Benchmark batch queries
        batch_results = benchmark_batch_queries(
            session, service, args.batch_size, args.batch_queries
        )
        print_results(batch_results)

        # Summary
        print("\nPerformance Summary:")
        print(
            f"  Single query avg:  {single_results['mean_time_ms']:.2f}ms "
            f"(target: <100ms)"
        )
        print(
            f"  Batch query avg:   {batch_results['mean_per_query_ms']:.2f}ms per query"
        )

        if single_results["mean_time_ms"] < 100:
            print("\n✓ Performance target achieved!")
        else:
            print(
                f"\n⚠ Performance target missed by {single_results['mean_time_ms'] - 100:.2f}ms"
            )
            print(
                "  Consider: adjusting IVFFlat lists parameter, increasing probes, or using GPU"
            )

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        session.close()
        engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(main())
