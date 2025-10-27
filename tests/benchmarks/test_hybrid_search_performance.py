"""Performance benchmarks for hybrid search service.

Tests performance targets:
- <150ms for hybrid search queries
- Scalability with different dataset sizes
- Impact of different weight configurations

Run with: pytest tests/benchmarks/test_hybrid_search_performance.py -v -s
"""

import os
import time
import pytest
import statistics
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Evidence, Embedding
from truthgraph.services.hybrid_search_service import HybridSearchService


# Database URL for testing
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph_test",
)


@pytest.fixture(scope="module")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    """Create test session factory."""
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(test_session_factory, test_engine):
    """Create a fresh database session for each test."""
    Base.metadata.create_all(test_engine)
    session = test_session_factory()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(test_engine)


def create_test_dataset(db_session, size=100):
    """Create a test dataset of specified size.

    Args:
        db_session: Database session
        size: Number of evidence documents to create
    """
    evidence_texts = [
        "Climate change affects global weather patterns and ecosystems.",
        "Machine learning algorithms improve with more training data.",
        "Python programming language is widely used in data science.",
        "Renewable energy sources include solar, wind, and hydroelectric.",
        "Quantum computing promises to revolutionize computational power.",
        "Biodiversity loss threatens ecosystem stability worldwide.",
        "Neural networks mimic biological brain structures.",
        "Carbon emissions contribute to atmospheric warming.",
        "Database indexing improves query performance significantly.",
        "Artificial intelligence applications span many industries.",
    ]

    evidence_list = []
    embedding_list = []

    for i in range(size):
        # Rotate through different text templates
        content = evidence_texts[i % len(evidence_texts)] + f" Document {i}."

        evidence_id = uuid4()

        # Create evidence
        evidence = Evidence(
            id=evidence_id,
            content=content,
            source_url=f"https://example.com/doc{i}",
            created_at=datetime.utcnow(),
        )
        evidence_list.append(evidence)

        # Create embedding (simple pattern based on document index)
        # Using 1536 dimensions
        embedding_pattern = [
            (i % 10) / 10.0 if j % (i % 5 + 1) == 0 else 0.01 for j in range(1536)
        ]

        embedding = Embedding(
            entity_type="evidence",
            entity_id=evidence_id,
            embedding=embedding_pattern,
            tenant_id="default",
            model_name="text-embedding-3-small",
        )
        embedding_list.append(embedding)

    # Batch insert for performance
    db_session.bulk_save_objects(evidence_list)
    db_session.bulk_save_objects(embedding_list)
    db_session.commit()

    return size


class TestHybridSearchPerformance:
    """Performance benchmarks for hybrid search."""

    @pytest.mark.benchmark
    def test_hybrid_search_100_documents_performance(self, db_session):
        """Benchmark hybrid search with 100 documents."""
        create_test_dataset(db_session, size=100)
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.5 if i % 3 == 0 else 0.1 for i in range(1536)]

        # Warm-up query
        service.hybrid_search(
            db=db_session,
            query_text="climate change machine learning",
            query_embedding=query_embedding,
            top_k=10,
        )

        # Benchmark queries
        times = []
        num_runs = 10

        for _ in range(num_runs):
            start = time.time()
            results, query_time = service.hybrid_search(
                db=db_session,
                query_text="climate change machine learning",
                query_embedding=query_embedding,
                top_k=10,
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        # Statistics
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        stddev_time = statistics.stdev(times) if len(times) > 1 else 0

        print(f"\n=== Hybrid Search Performance (100 docs) ===")
        print(f"Runs: {num_runs}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Median: {median_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        print(f"Stddev: {stddev_time:.2f}ms")

        # Assert performance target
        assert avg_time < 150, f"Average time {avg_time:.2f}ms exceeds 150ms target"
        assert max_time < 200, f"Max time {max_time:.2f}ms exceeds 200ms threshold"

    @pytest.mark.benchmark
    def test_hybrid_search_500_documents_performance(self, db_session):
        """Benchmark hybrid search with 500 documents."""
        create_test_dataset(db_session, size=500)
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.5 if i % 3 == 0 else 0.1 for i in range(1536)]

        # Warm-up query
        service.hybrid_search(
            db=db_session,
            query_text="renewable energy quantum computing",
            query_embedding=query_embedding,
            top_k=10,
        )

        # Benchmark queries
        times = []
        num_runs = 10

        for _ in range(num_runs):
            start = time.time()
            results, query_time = service.hybrid_search(
                db=db_session,
                query_text="renewable energy quantum computing",
                query_embedding=query_embedding,
                top_k=10,
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        avg_time = statistics.mean(times)
        median_time = statistics.median(times)

        print(f"\n=== Hybrid Search Performance (500 docs) ===")
        print(f"Runs: {num_runs}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Median: {median_time:.2f}ms")

        # More lenient target for larger dataset
        assert avg_time < 200, f"Average time {avg_time:.2f}ms exceeds 200ms target"

    @pytest.mark.benchmark
    def test_keyword_only_search_performance(self, db_session):
        """Benchmark keyword-only search performance."""
        create_test_dataset(db_session, size=200)
        service = HybridSearchService(embedding_dimension=1536)

        # Warm-up
        service.keyword_only_search(
            db=db_session,
            query_text="climate change",
            top_k=10,
        )

        # Benchmark
        times = []
        num_runs = 10

        for _ in range(num_runs):
            start = time.time()
            results, query_time = service.keyword_only_search(
                db=db_session,
                query_text="climate change biodiversity",
                top_k=10,
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        avg_time = statistics.mean(times)

        print(f"\n=== Keyword-Only Search Performance ===")
        print(f"Runs: {num_runs}")
        print(f"Average: {avg_time:.2f}ms")

        # Keyword search should be very fast
        assert avg_time < 100, f"Keyword search {avg_time:.2f}ms exceeds 100ms target"

    @pytest.mark.benchmark
    def test_hybrid_search_weight_variations(self, db_session):
        """Benchmark hybrid search with different weight configurations."""
        create_test_dataset(db_session, size=100)
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.5 if i % 3 == 0 else 0.1 for i in range(1536)]
        query_text = "machine learning neural networks"

        weight_configs = [
            (0.5, 0.5, "Balanced"),
            (0.9, 0.1, "Vector-heavy"),
            (0.1, 0.9, "Keyword-heavy"),
            (1.0, 0.0, "Vector-only"),
            (0.0, 1.0, "Keyword-only"),
        ]

        print(f"\n=== Weight Configuration Performance ===")

        for vector_weight, keyword_weight, label in weight_configs:
            times = []
            num_runs = 5

            for _ in range(num_runs):
                start = time.time()
                results, query_time = service.hybrid_search(
                    db=db_session,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    top_k=10,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = statistics.mean(times)
            print(f"{label:20s} ({vector_weight:.1f}/{keyword_weight:.1f}): {avg_time:.2f}ms")

            # All configurations should be fast
            assert avg_time < 150

    @pytest.mark.benchmark
    def test_hybrid_search_top_k_variations(self, db_session):
        """Benchmark hybrid search with different top_k values."""
        create_test_dataset(db_session, size=200)
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.5 if i % 3 == 0 else 0.1 for i in range(1536)]

        top_k_values = [5, 10, 20, 50, 100]

        print(f"\n=== Top-K Performance ===")

        for top_k in top_k_values:
            times = []
            num_runs = 5

            for _ in range(num_runs):
                start = time.time()
                results, query_time = service.hybrid_search(
                    db=db_session,
                    query_text="climate renewable energy",
                    query_embedding=query_embedding,
                    top_k=top_k,
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = statistics.mean(times)
            print(f"top_k={top_k:3d}: {avg_time:.2f}ms")

            # Performance should scale reasonably with top_k
            if top_k <= 50:
                assert avg_time < 150


class TestHybridSearchScalability:
    """Test scalability characteristics."""

    @pytest.mark.benchmark
    def test_scalability_comparison(self, db_session):
        """Compare performance across different dataset sizes."""
        service = HybridSearchService(embedding_dimension=1536)
        query_embedding = [0.5 if i % 3 == 0 else 0.1 for i in range(1536)]

        sizes = [50, 100, 200]
        results_summary = []

        print(f"\n=== Scalability Analysis ===")

        for size in sizes:
            # Clear and create new dataset
            db_session.query(Embedding).delete()
            db_session.query(Evidence).delete()
            db_session.commit()

            create_test_dataset(db_session, size=size)

            # Warm-up
            service.hybrid_search(
                db=db_session,
                query_text="test query",
                query_embedding=query_embedding,
                top_k=10,
            )

            # Benchmark
            times = []
            for _ in range(5):
                start = time.time()
                _, query_time = service.hybrid_search(
                    db=db_session,
                    query_text="climate change energy",
                    query_embedding=query_embedding,
                    top_k=10,
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = statistics.mean(times)
            results_summary.append((size, avg_time))
            print(f"Dataset size {size:4d}: {avg_time:.2f}ms")

        # Verify sub-linear scaling (with IVFFlat index)
        # Performance shouldn't degrade too much with size
        for size, avg_time in results_summary:
            if size <= 200:
                assert avg_time < 200, f"Size {size}: {avg_time:.2f}ms too slow"


class TestRRFPerformance:
    """Test RRF algorithm performance."""

    @pytest.mark.benchmark
    def test_rrf_fusion_performance(self, db_session):
        """Benchmark RRF fusion with varying result set sizes."""
        service = HybridSearchService(embedding_dimension=1536)

        print(f"\n=== RRF Fusion Performance ===")

        result_sizes = [(10, 10), (50, 50), (100, 100), (200, 200)]

        for vec_size, kw_size in result_sizes:
            # Create mock results
            vector_results = [
                (uuid4(), f"content {i}", None, 0.9 - i * 0.01) for i in range(vec_size)
            ]

            keyword_results = [
                (uuid4(), f"content {i}", None, i + 1) for i in range(kw_size)
            ]

            # Benchmark RRF
            times = []
            for _ in range(100):  # More runs since RRF is fast
                start = time.time()
                merged = service._reciprocal_rank_fusion(
                    vector_results=vector_results,
                    keyword_results=keyword_results,
                    vector_weight=0.5,
                    keyword_weight=0.5,
                    k=60,
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = statistics.mean(times)
            print(f"Vector: {vec_size:3d}, Keyword: {kw_size:3d} -> {avg_time:.4f}ms")

            # RRF should be very fast (pure Python computation)
            assert avg_time < 1.0, f"RRF too slow: {avg_time:.4f}ms"
