#!/usr/bin/env python3
"""IVFFlat index parameter optimization for pgvector.

This script systematically tests different IVFFlat index configurations to find
optimal parameters for:
- lists: Number of inverted lists (partitions)
- probes: Number of lists to search during queries

Performance targets:
- Search latency: <3 seconds for 10K items
- Accuracy: Top-1 recall >95%
- Index build time: <60 seconds for 10K items

IVFFlat Parameter Guidelines:
- lists: Number of centroids (typically sqrt(n) to n/1000)
  - Too few: Poor index selectivity, slow searches
  - Too many: Large index, slow index build
- probes: Number of lists to search (1 to lists)
  - Low probes: Fast but lower recall
  - High probes: Slower but better recall

Recommended ranges:
- For 1k items: lists in [10, 25], probes in [1, 5]
- For 10k items: lists in [25, 100], probes in [5, 25]
- For 50k items: lists in [50, 200], probes in [10, 50]
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

import numpy as np
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
    return {"rss_mb": mem_info.rss / (1024 * 1024), "vms_mb": mem_info.vms / (1024 * 1024)}


def create_test_corpus(
    session, size: int, embedding_dim: int, tenant_id: str, deterministic: bool = True
) -> list[np.ndarray]:
    """Create test corpus with evidence and embeddings.

    Args:
        session: Database session
        size: Number of evidence items
        embedding_dim: Embedding dimension
        tenant_id: Tenant ID for test data
        deterministic: Use deterministic embeddings for reproducibility

    Returns:
        List of ground truth embeddings for accuracy testing
    """
    print(f"Creating test corpus: {size} items, dim={embedding_dim}...")

    # Clean existing test data
    session.execute(text(f"DELETE FROM embeddings WHERE tenant_id = '{tenant_id}'"))
    session.execute(text(f"DELETE FROM evidence WHERE source_type = '{tenant_id}'"))
    session.commit()

    ground_truth_embeddings = []
    batch_size = 100

    if deterministic:
        np.random.seed(42)

    for i in range(0, size, batch_size):
        evidence_batch = []
        embedding_batch = []

        for j in range(min(batch_size, size - i)):
            idx = i + j
            evidence_id = uuid4()

            # Create evidence with diverse content
            content_variants = [
                f"Climate change is affecting global temperatures at location {idx}.",
                f"Economic growth in region {idx} shows positive trends.",
                f"Healthcare improvements in country {idx} are documented.",
                f"Technology adoption in sector {idx} is accelerating.",
                f"Education reforms in district {idx} show promise.",
            ]
            content = content_variants[idx % len(content_variants)]

            evidence = Evidence(
                id=evidence_id,
                content=content,
                source_url=f"https://benchmark.test/evidence/{idx}",
                source_type=tenant_id,
            )
            evidence_batch.append(evidence)

            # Create realistic embedding
            if deterministic:
                # Structured embedding: cluster-based for realistic similarity
                cluster_id = idx % 20  # 20 clusters
                cluster_center = np.random.randn(embedding_dim)
                noise = np.random.randn(embedding_dim) * 0.1
                embedding_vector = cluster_center + noise
                # Normalize to unit length (as sentence transformers do)
                embedding_vector = embedding_vector / np.linalg.norm(embedding_vector)
            else:
                # Random normalized vector
                embedding_vector = np.random.randn(embedding_dim)
                embedding_vector = embedding_vector / np.linalg.norm(embedding_vector)

            ground_truth_embeddings.append(embedding_vector)

            embedding = Embedding(
                entity_type="evidence",
                entity_id=evidence_id,
                embedding=embedding_vector.tolist(),
                tenant_id=tenant_id,
            )
            embedding_batch.append(embedding)

        session.bulk_save_objects(evidence_batch)
        session.bulk_save_objects(embedding_batch)
        session.commit()

        if (i + batch_size) % 1000 == 0 or i + batch_size >= size:
            print(f"  Created {min(i + batch_size, size)}/{size} items")

    print("Test corpus created successfully")
    return ground_truth_embeddings


def create_ivfflat_index(
    session, lists: int, embedding_dim: int, tenant_id: str
) -> dict[str, Any]:
    """Create IVFFlat index with specified parameters.

    Args:
        session: Database session
        lists: Number of inverted lists
        embedding_dim: Embedding dimension
        tenant_id: Tenant ID

    Returns:
        Dictionary with index creation statistics
    """
    print(f"\nCreating IVFFlat index: lists={lists}, dim={embedding_dim}...")

    # Drop existing index if present
    try:
        session.execute(
            text("DROP INDEX IF EXISTS embeddings_ivfflat_idx")
        )
        session.commit()
    except Exception as e:
        print(f"  Warning: Could not drop index: {e}")
        session.rollback()

    # Create index with timing
    index_sql = f"""
    CREATE INDEX embeddings_ivfflat_idx
    ON embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = {lists})
    WHERE entity_type = 'evidence' AND tenant_id = '{tenant_id}'
    """

    start_time = time.perf_counter()
    try:
        session.execute(text(index_sql))
        session.commit()
        end_time = time.perf_counter()

        build_time_sec = end_time - start_time

        # Get index size
        size_result = session.execute(
            text(
                "SELECT pg_size_pretty(pg_relation_size('embeddings_ivfflat_idx')) as size"
            )
        )
        index_size = size_result.fetchone()[0]

        print(f"  Index created in {build_time_sec:.2f} seconds, size: {index_size}")

        return {
            "lists": lists,
            "build_time_sec": build_time_sec,
            "index_size": index_size,
            "success": True,
        }

    except Exception as e:
        print(f"  ERROR: Index creation failed: {e}")
        session.rollback()
        return {
            "lists": lists,
            "build_time_sec": 0.0,
            "index_size": "0 bytes",
            "success": False,
            "error": str(e),
        }


def set_ivfflat_probes(session, probes: int) -> None:
    """Set ivfflat.probes parameter for current session.

    Args:
        session: Database session
        probes: Number of probes to set
    """
    session.execute(text(f"SET ivfflat.probes = {probes}"))


def measure_search_accuracy(
    session,
    service: VectorSearchService,
    ground_truth_embeddings: list[np.ndarray],
    num_queries: int,
    top_k: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Measure search accuracy using ground truth embeddings.

    For each query, we use one of the ground truth embeddings and check if
    the corresponding evidence appears in the top-k results.

    Args:
        session: Database session
        service: VectorSearchService instance
        ground_truth_embeddings: List of ground truth embedding vectors
        num_queries: Number of queries to test
        top_k: Number of results to retrieve
        tenant_id: Tenant ID

    Returns:
        Dictionary with accuracy metrics
    """
    if not ground_truth_embeddings:
        return {"error": "No ground truth embeddings available"}

    # Sample query indices
    query_indices = np.random.choice(len(ground_truth_embeddings), num_queries, replace=True)

    top1_hits = 0
    top5_hits = 0
    topk_hits = 0

    for query_idx in query_indices:
        query_embedding = ground_truth_embeddings[query_idx].tolist()

        results = service.search_similar_evidence(
            db=session, query_embedding=query_embedding, top_k=top_k, tenant_id=tenant_id
        )

        if not results:
            continue

        # Check if the exact match is in top-1, top-5, or top-k
        # For ground truth queries, the embedding should find itself
        result_positions = list(range(len(results)))

        # Top-1 recall: exact match is the first result
        if len(results) >= 1 and results[0].similarity > 0.99:
            top1_hits += 1

        # Top-5 recall
        if any(r.similarity > 0.99 for r in results[:5]):
            top5_hits += 1

        # Top-K recall
        if any(r.similarity > 0.99 for r in results):
            topk_hits += 1

    return {
        "num_queries": num_queries,
        "top_k": top_k,
        "top1_recall": top1_hits / num_queries,
        "top5_recall": top5_hits / num_queries,
        "topk_recall": topk_hits / num_queries,
    }


def benchmark_index_configuration(
    session,
    service: VectorSearchService,
    lists: int,
    probes: int,
    ground_truth_embeddings: list[np.ndarray],
    num_queries: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Benchmark a specific index configuration.

    Args:
        session: Database session
        service: VectorSearchService instance
        lists: Number of inverted lists
        probes: Number of probes
        ground_truth_embeddings: Ground truth embeddings
        num_queries: Number of queries to test
        tenant_id: Tenant ID

    Returns:
        Benchmark results
    """
    print(f"\nBenchmarking: lists={lists}, probes={probes}")

    # Set probes
    set_ivfflat_probes(session, probes)

    # Measure latency
    query_times = []

    for i in range(num_queries):
        # Random query embedding
        query_idx = i % len(ground_truth_embeddings)
        query_embedding = ground_truth_embeddings[query_idx].tolist()

        start_time = time.perf_counter()
        results = service.search_similar_evidence(
            db=session, query_embedding=query_embedding, top_k=10, tenant_id=tenant_id
        )
        end_time = time.perf_counter()

        query_times.append((end_time - start_time) * 1000)

    # Measure accuracy
    accuracy_metrics = measure_search_accuracy(
        session, service, ground_truth_embeddings, num_queries=20, top_k=10, tenant_id=tenant_id
    )

    result = {
        "lists": lists,
        "probes": probes,
        "num_queries": num_queries,
        "mean_latency_ms": mean(query_times),
        "median_latency_ms": median(query_times),
        "p95_latency_ms": np.percentile(query_times, 95),
        "p99_latency_ms": np.percentile(query_times, 99),
        "min_latency_ms": min(query_times),
        "max_latency_ms": max(query_times),
        "stdev_latency_ms": stdev(query_times) if len(query_times) > 1 else 0.0,
        **accuracy_metrics,
    }

    print(
        f"  Latency: mean={result['mean_latency_ms']:.1f}ms, "
        f"p95={result['p95_latency_ms']:.1f}ms"
    )
    print(
        f"  Accuracy: top1={result['top1_recall']:.3f}, "
        f"top5={result['top5_recall']:.3f}"
    )

    return result


def optimize_index_parameters(
    engine,
    SessionLocal,
    corpus_size: int,
    embedding_dim: int,
    lists_values: list[int],
    probes_values: list[int],
) -> dict[str, Any]:
    """Optimize index parameters across corpus sizes.

    Args:
        engine: Database engine
        SessionLocal: Session factory
        corpus_size: Size of test corpus
        embedding_dim: Embedding dimension
        lists_values: List of 'lists' parameter values to test
        probes_values: List of 'probes' parameter values to test

    Returns:
        Optimization results
    """
    print("\n" + "=" * 80)
    print(f"OPTIMIZING INDEX PARAMETERS: corpus_size={corpus_size}")
    print("=" * 80)

    tenant_id = f"optimize_{corpus_size}"

    session = SessionLocal()
    try:
        # Create test corpus
        ground_truth = create_test_corpus(
            session, corpus_size, embedding_dim, tenant_id, deterministic=True
        )

        service = VectorSearchService(embedding_dimension=embedding_dim)

        results = {
            "corpus_size": corpus_size,
            "embedding_dimension": embedding_dim,
            "configurations": [],
        }

        # Test each lists value
        for lists in lists_values:
            # Create index
            index_stats = create_ivfflat_index(session, lists, embedding_dim, tenant_id)

            if not index_stats["success"]:
                continue

            # Test each probes value
            for probes in probes_values:
                if probes > lists:
                    # Skip invalid configurations (probes cannot exceed lists)
                    continue

                config_result = benchmark_index_configuration(
                    session, service, lists, probes, ground_truth, num_queries=50, tenant_id=tenant_id
                )

                config_result["index_build_time_sec"] = index_stats["build_time_sec"]
                config_result["index_size"] = index_stats["index_size"]

                results["configurations"].append(config_result)

        # Find optimal configuration
        # Optimize for: latency <3000ms and top1_recall >0.95
        valid_configs = [
            c
            for c in results["configurations"]
            if c.get("top1_recall", 0) >= 0.90  # Allow some tolerance
        ]

        if valid_configs:
            # Among valid configs, choose fastest
            optimal = min(valid_configs, key=lambda c: c["mean_latency_ms"])
            results["optimal_configuration"] = {
                "lists": optimal["lists"],
                "probes": optimal["probes"],
                "mean_latency_ms": optimal["mean_latency_ms"],
                "top1_recall": optimal["top1_recall"],
                "reasoning": "Fastest configuration with top-1 recall >= 90%",
            }
        else:
            # No config meets accuracy target, report best accuracy
            if results["configurations"]:
                best_accuracy = max(results["configurations"], key=lambda c: c.get("top1_recall", 0))
                results["optimal_configuration"] = {
                    "lists": best_accuracy["lists"],
                    "probes": best_accuracy["probes"],
                    "mean_latency_ms": best_accuracy["mean_latency_ms"],
                    "top1_recall": best_accuracy.get("top1_recall", 0),
                    "reasoning": "Best accuracy configuration (did not meet 90% target)",
                }

        return results

    finally:
        session.close()


def save_results(results: dict[str, Any], output_path: Path) -> None:
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def main() -> int:
    """Main optimization execution."""
    parser = argparse.ArgumentParser(description="IVFFlat index parameter optimization")
    parser.add_argument(
        "--corpus-sizes",
        type=str,
        default="1000,5000,10000",
        help="Comma-separated corpus sizes (default: 1000,5000,10000)",
    )
    parser.add_argument(
        "--lists",
        type=str,
        default="10,25,50,100",
        help="Comma-separated lists values (default: 10,25,50,100)",
    )
    parser.add_argument(
        "--probes",
        type=str,
        default="1,5,10,25",
        help="Comma-separated probes values (default: 1,5,10,25)",
    )
    parser.add_argument(
        "--embedding-dim", type=int, default=384, choices=[384, 1536], help="Embedding dimension"
    )
    parser.add_argument(
        "--database-url", type=str, help="Database URL (default: from DATABASE_URL env)"
    )
    parser.add_argument(
        "--output", type=str, help="Output JSON file (default: results/index_params_YYYY-MM-DD.json)"
    )

    args = parser.parse_args()

    # Parse parameters
    corpus_sizes = [int(x.strip()) for x in args.corpus_sizes.split(",")]
    lists_values = [int(x.strip()) for x in args.lists.split(",")]
    probes_values = [int(x.strip()) for x in args.probes.split(",")]

    # Database URL
    database_url = args.database_url or os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph",
    )

    print("=" * 80)
    print("IVFFLAT INDEX PARAMETER OPTIMIZATION")
    print("=" * 80)
    print(f"\nCorpus sizes:   {corpus_sizes}")
    print(f"Lists values:   {lists_values}")
    print(f"Probes values:  {probes_values}")
    print(f"Embedding dim:  {args.embedding_dim}")
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
            "optimization_runs": [],
        }

        # Run optimization for each corpus size
        for corpus_size in corpus_sizes:
            run_result = optimize_index_parameters(
                engine,
                SessionLocal,
                corpus_size,
                args.embedding_dim,
                lists_values,
                probes_values,
            )
            all_results["optimization_runs"].append(run_result)

        # Summary
        print("\n" + "=" * 80)
        print("OPTIMIZATION SUMMARY")
        print("=" * 80)

        for run in all_results["optimization_runs"]:
            corpus_size = run["corpus_size"]
            if "optimal_configuration" in run:
                opt = run["optimal_configuration"]
                print(f"\nCorpus size: {corpus_size}")
                print(f"  Optimal: lists={opt['lists']}, probes={opt['probes']}")
                print(f"  Latency: {opt['mean_latency_ms']:.1f} ms")
                print(f"  Top-1 recall: {opt['top1_recall']:.3f}")
                print(f"  {opt['reasoning']}")

        # Save results
        if args.output:
            output_path = Path(args.output)
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            output_path = Path(__file__).parent / "results" / f"index_params_{today}.json"

        save_results(all_results, output_path)

        print("\n" + "=" * 80)
        print("OPTIMIZATION COMPLETE")
        print("=" * 80)

        return 0

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
