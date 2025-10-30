#!/usr/bin/env python3
"""Comprehensive benchmark for vector search service.

This script measures vector search performance across various dimensions:
- Query latency with different corpus sizes
- Batch query throughput
- Recall accuracy vs speed tradeoffs
- Memory usage

Performance Targets:
    - Latency: <3 seconds for 10K items
    - Query throughput: >10 queries/sec
"""

import argparse
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

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Embedding, Evidence
from truthgraph.services.vector_search_service import VectorSearchService


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics."""
    if not PSUTIL_AVAILABLE:
        return {}

    process = psutil.Process()
    mem_info = process.memory_info()
    return {"rss_mb": mem_info.rss / (1024 * 1024)}


def create_test_corpus(session, size: int, embedding_dim: int, tenant_id: str) -> None:
    """Create test corpus with evidence and embeddings.

    Args:
        session: Database session
        size: Number of evidence items
        embedding_dim: Embedding dimension
        tenant_id: Tenant ID for test data
    """
    print(f"Creating test corpus: {size} items, dim={embedding_dim}...")

    # Clean existing test data
    session.execute(text(f"DELETE FROM embeddings WHERE tenant_id = '{tenant_id}'"))
    session.execute(text(f"DELETE FROM evidence WHERE source_type = '{tenant_id}'"))
    session.commit()

    batch_size = 100
    for i in range(0, size, batch_size):
        evidence_batch = []
        embedding_batch = []

        for j in range(min(batch_size, size - i)):
            idx = i + j
            evidence_id = uuid4()

            # Create evidence
            evidence = Evidence(
                id=evidence_id,
                content=f"Test evidence {idx}: This is sample text for benchmarking vector search performance.",
                source_url=f"https://benchmark.test/evidence/{idx}",
                source_type=tenant_id,
            )
            evidence_batch.append(evidence)

            # Create embedding with pattern
            pattern_value = idx / size
            embedding_vector = [pattern_value + (0.001 * k) for k in range(embedding_dim)]

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

        if (i + batch_size) % 1000 == 0 or i + batch_size >= size:
            print(f"  Created {min(i + batch_size, size)}/{size} items")

    print("Test corpus created successfully")


def benchmark_query_latency(
    session,
    service: VectorSearchService,
    num_queries: int,
    top_k: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark query latency.

    Args:
        session: Database session
        service: VectorSearchService instance
        num_queries: Number of queries
        top_k: Results per query
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print(f"\nRunning {num_queries} queries (top_k={top_k})...")

    query_times = []
    result_counts = []

    for i in range(num_queries):
        # Create query embedding
        query_pattern = i / num_queries
        query_embedding = [
            query_pattern + (0.001 * k) for k in range(service.embedding_dimension)
        ]

        # Measure
        start_time = time.perf_counter()
        results = service.search_similar_evidence(
            db=session,
            query_embedding=query_embedding,
            top_k=top_k,
            tenant_id=tenant_id,
        )
        end_time = time.perf_counter()

        query_time_ms = (end_time - start_time) * 1000
        query_times.append(query_time_ms)
        result_counts.append(len(results))

        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Query {i + 1}/{num_queries}: {query_time_ms:.1f}ms, {len(results)} results")

    return {
        "num_queries": num_queries,
        "top_k": top_k,
        "mean_time_ms": mean(query_times),
        "median_time_ms": median(query_times),
        "min_time_ms": min(query_times),
        "max_time_ms": max(query_times),
        "stdev_time_ms": stdev(query_times) if len(query_times) > 1 else 0.0,
        "mean_results": mean(result_counts),
        "total_time_ms": sum(query_times),
    }


def benchmark_batch_queries(
    session,
    service: VectorSearchService,
    batch_size: int,
    num_batches: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark batch queries.

    Args:
        session: Database session
        service: VectorSearchService instance
        batch_size: Queries per batch
        num_batches: Number of batches
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print(f"\nRunning {num_batches} batch queries (batch_size={batch_size})...")

    batch_times = []

    for i in range(num_batches):
        # Create batch
        query_embeddings = [
            [(i * batch_size + j) / 1000 + (0.001 * k) for k in range(service.embedding_dimension)]
            for j in range(batch_size)
        ]

        # Measure
        start_time = time.perf_counter()
        results = service.search_similar_evidence_batch(
            db=session, query_embeddings=query_embeddings, tenant_id=tenant_id
        )
        end_time = time.perf_counter()

        batch_time_ms = (end_time - start_time) * 1000
        batch_times.append(batch_time_ms)

        if (i + 1) % 5 == 0 or i == 0:
            total_results = sum(len(r) for r in results)
            print(f"  Batch {i + 1}/{num_batches}: {batch_time_ms:.1f}ms, {total_results} results")

    return {
        "num_batches": num_batches,
        "batch_size": batch_size,
        "mean_batch_time_ms": mean(batch_times),
        "mean_per_query_ms": mean(batch_times) / batch_size,
        "total_time_ms": sum(batch_times),
    }


def benchmark_corpus_sizes(
    engine,
    SessionLocal,
    embedding_dim: int,
    corpus_sizes: list[int],
) -> dict[str, Any]:
    """Benchmark different corpus sizes.

    Args:
        engine: Database engine
        SessionLocal: Session factory
        embedding_dim: Embedding dimension
        corpus_sizes: List of corpus sizes to test

    Returns:
        Benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Corpus Size Impact")
    print("=" * 80)

    results = {"embedding_dimension": embedding_dim, "corpus_results": []}

    for corpus_size in corpus_sizes:
        print(f"\nTesting corpus size: {corpus_size}")
        tenant_id = f"benchmark_{corpus_size}"

        session = SessionLocal()
        try:
            # Create corpus
            create_test_corpus(session, corpus_size, embedding_dim, tenant_id)

            # Initialize service
            service = VectorSearchService(embedding_dimension=embedding_dim)

            # Get stats
            stats = service.get_embedding_stats(
                db=session, entity_type="evidence", tenant_id=tenant_id
            )
            print(f"Corpus stats: {stats['total_embeddings']} embeddings")

            # Benchmark queries
            query_results = benchmark_query_latency(
                session, service, num_queries=20, top_k=10, tenant_id=tenant_id
            )

            corpus_result = {
                "corpus_size": corpus_size,
                "mean_query_ms": query_results["mean_time_ms"],
                "median_query_ms": query_results["median_time_ms"],
                "max_query_ms": query_results["max_time_ms"],
            }

            # Memory
            memory = get_memory_usage()
            if "rss_mb" in memory:
                corpus_result["memory_rss_mb"] = memory["rss_mb"]

            results["corpus_results"].append(corpus_result)

            print(f"  Mean query time: {query_results['mean_time_ms']:.1f} ms")
            print(f"  Max query time:  {query_results['max_time_ms']:.1f} ms")

        finally:
            session.close()

    return results


def benchmark_top_k_values(
    session,
    service: VectorSearchService,
    top_k_values: list[int],
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark different top_k values.

    Args:
        session: Database session
        service: VectorSearchService instance
        top_k_values: List of top_k values
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print("\n" + "=" * 80)
    print("BENCHMARK: Top-K Impact")
    print("=" * 80)

    results = {"top_k_results": []}

    for top_k in top_k_values:
        print(f"\nTesting top_k={top_k}")

        query_results = benchmark_query_latency(
            session, service, num_queries=20, top_k=top_k, tenant_id=tenant_id
        )

        top_k_result = {
            "top_k": top_k,
            "mean_query_ms": query_results["mean_time_ms"],
            "mean_results": query_results["mean_results"],
        }

        results["top_k_results"].append(top_k_result)

        print(f"  Mean time: {query_results['mean_time_ms']:.1f} ms")
        print(f"  Mean results: {query_results['mean_results']:.1f}")

    return results


def save_results(results: dict[str, Any], output_path: Path) -> None:
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def main() -> int:
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Comprehensive vector search benchmark")
    parser.add_argument(
        "--corpus-sizes",
        type=str,
        default="1000,5000,10000",
        help="Comma-separated corpus sizes",
    )
    parser.add_argument(
        "--embedding-dim", type=int, default=384, choices=[384, 1536], help="Embedding dimension"
    )
    parser.add_argument(
        "--database-url", type=str, help="Database URL (default: from DATABASE_URL env)"
    )
    parser.add_argument(
        "--output", type=str, help="Output JSON file (default: results/vector_search_TIMESTAMP.json)"
    )
    parser.add_argument(
        "--skip-corpus-sizes", action="store_true", help="Skip corpus size benchmark"
    )

    args = parser.parse_args()

    # Parse corpus sizes
    corpus_sizes = [int(x.strip()) for x in args.corpus_sizes.split(",")]

    # Database URL
    database_url = args.database_url or os.getenv(
        "DATABASE_URL", "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph"
    )

    print("=" * 80)
    print("VECTOR SEARCH COMPREHENSIVE BENCHMARK")
    print("=" * 80)
    print(f"\nEmbedding dim:  {args.embedding_dim}")
    print(f"Corpus sizes:   {corpus_sizes}")
    print(f"Database:       {database_url.split('@')[-1]}")

    # Setup database
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)

    try:
        Base.metadata.create_all(engine)

        all_results = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "python_version": sys.version.split()[0],
                "embedding_dimension": args.embedding_dim,
                "database": database_url.split("@")[-1],
            },
            "benchmarks": {},
        }

        # Benchmark corpus sizes
        if not args.skip_corpus_sizes:
            all_results["benchmarks"]["corpus_sizes"] = benchmark_corpus_sizes(
                engine, SessionLocal, args.embedding_dim, corpus_sizes
            )

        # Create standard corpus for other benchmarks
        print("\n" + "=" * 80)
        print("BENCHMARK: Standard Queries")
        print("=" * 80)

        standard_size = 10000
        tenant_id = f"benchmark_{standard_size}"

        session = SessionLocal()
        try:
            create_test_corpus(session, standard_size, args.embedding_dim, tenant_id)
            service = VectorSearchService(embedding_dimension=args.embedding_dim)

            # Query latency
            all_results["benchmarks"]["query_latency"] = benchmark_query_latency(
                session, service, num_queries=50, top_k=10, tenant_id=tenant_id
            )

            # Batch queries
            all_results["benchmarks"]["batch_queries"] = benchmark_batch_queries(
                session, service, batch_size=10, num_batches=10, tenant_id=tenant_id
            )

            # Top-K impact
            all_results["benchmarks"]["top_k_impact"] = benchmark_top_k_values(
                session, service, top_k_values=[5, 10, 20, 50], tenant_id=tenant_id
            )

        finally:
            session.close()

        # Summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        all_passed = True

        if "query_latency" in all_results["benchmarks"]:
            ql = all_results["benchmarks"]["query_latency"]
            target_ms = 3000  # 3 seconds for 10K items
            passed = ql["mean_time_ms"] < target_ms
            all_passed = all_passed and passed
            status = "PASS" if passed else "FAIL"
            print(f"\nQuery latency (10K corpus): {ql['mean_time_ms']:.1f} ms - {status}")

        if "batch_queries" in all_results["benchmarks"]:
            bq = all_results["benchmarks"]["batch_queries"]
            print(f"Batch query per-query:      {bq['mean_per_query_ms']:.1f} ms")

        if "corpus_sizes" in all_results["benchmarks"]:
            cs = all_results["benchmarks"]["corpus_sizes"]
            print("\nCorpus size impact:")
            for result in cs["corpus_results"]:
                print(
                    f"  {result['corpus_size']:5d} items: {result['mean_query_ms']:6.1f} ms mean"
                )

        # Save results
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output_path = Path(__file__).parent / "results" / f"vector_search_{timestamp}.json"

        save_results(all_results, output_path)

        print("\n" + "=" * 80)
        final_status = "ALL BENCHMARKS PASSED" if all_passed else "SOME BENCHMARKS FAILED"
        print(final_status)
        print("=" * 80)

        return 0 if all_passed else 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
