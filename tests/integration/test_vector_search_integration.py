"""Integration tests for vector search service with real database.

These tests require a PostgreSQL database with pgvector extension.
Run with: pytest tests/integration/test_vector_search_integration.py
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Embedding, Evidence
from truthgraph.services.vector_search_service import VectorSearchService

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
    # Create tables
    Base.metadata.create_all(test_engine)

    session = test_session_factory()
    yield session

    # Rollback and cleanup
    session.rollback()
    session.close()

    # Drop all tables
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def sample_evidence_with_embeddings(db_session):
    """Create sample evidence with embeddings for testing."""
    # Create evidence records
    evidence_data = [
        {
            "id": uuid4(),
            "content": "The Earth orbits the Sun in approximately 365.25 days.",
            "source_url": "https://example.com/astronomy",
        },
        {
            "id": uuid4(),
            "content": "Water boils at 100 degrees Celsius at sea level.",
            "source_url": "https://example.com/physics",
        },
        {
            "id": uuid4(),
            "content": "Python is a high-level programming language.",
            "source_url": "https://example.com/programming",
        },
    ]

    # Insert evidence
    for data in evidence_data:
        evidence = Evidence(**data)
        db_session.add(evidence)

    db_session.commit()

    # Create mock embeddings (using simple patterns for testing)
    # In reality, these would be from a real embedding model
    # Using 384 dimensions for all-MiniLM-L6-v2 model
    embeddings_data = [
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[0]["id"],
            "embedding": [0.1] * 384,  # Mock embedding
            "tenant_id": "default",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[1]["id"],
            "embedding": [0.2] * 384,  # Different pattern
            "tenant_id": "default",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[2]["id"],
            "embedding": [0.3] * 384,  # Different pattern
            "tenant_id": "default",
        },
    ]

    for data in embeddings_data:
        embedding = Embedding(**data)
        db_session.add(embedding)

    db_session.commit()

    return evidence_data, embeddings_data


@pytest.mark.integration
class TestVectorSearchIntegration:
    """Integration tests for VectorSearchService."""

    def test_search_similar_evidence_basic(self, db_session, sample_evidence_with_embeddings):
        """Test basic vector search functionality."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Search with embedding similar to first item
        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=10, min_similarity=0.0
        )

        # Should return results
        assert len(results) > 0
        # First result should be most similar (same pattern)
        assert results[0].similarity > 0.9

    def test_search_with_high_similarity_threshold(
        self, db_session, sample_evidence_with_embeddings
    ):
        """Test search with high similarity threshold."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Search with very high threshold
        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, min_similarity=0.99
        )

        # Should return exact or near-exact matches only
        assert all(r.similarity >= 0.99 for r in results)

    def test_search_with_top_k_limit(self, db_session, sample_evidence_with_embeddings):
        """Test search respects top_k limit."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Search with top_k=2
        query_embedding = [0.15] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=2
        )

        # Should return at most 2 results
        assert len(results) <= 2

    def test_search_with_tenant_isolation(self, db_session, sample_evidence_with_embeddings):
        """Test tenant isolation in search."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Add embedding with different tenant
        different_tenant_evidence = Evidence(
            id=uuid4(),
            content="Different tenant content",
            source_url="https://tenant2.com",
        )
        db_session.add(different_tenant_evidence)
        db_session.commit()

        different_tenant_embedding = Embedding(
            entity_type="evidence",
            entity_id=different_tenant_evidence.id,
            embedding=[0.1] * 384,  # Same pattern as default tenant
            tenant_id="tenant2",
        )
        db_session.add(different_tenant_embedding)
        db_session.commit()

        # Search in default tenant
        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, tenant_id="default"
        )

        # Should not return results from different tenant
        assert all("tenant2.com" not in (r.source_url or "") for r in results)

        # Search in tenant2
        results_tenant2 = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, tenant_id="tenant2"
        )

        # Should only return tenant2 results
        assert len(results_tenant2) > 0
        assert all("tenant2.com" in (r.source_url or "") for r in results_tenant2)

    def test_search_with_source_filter(self, db_session, sample_evidence_with_embeddings):
        """Test search with source URL filtering."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Search filtered by source
        query_embedding = [0.15] * 384
        results = service.search_similar_evidence(
            db=db_session,
            query_embedding=query_embedding,
            source_filter="https://example.com/astronomy",
        )

        # Should only return results from that source
        assert len(results) > 0
        assert all(r.source_url == "https://example.com/astronomy" for r in results)

    def test_search_returns_correct_content(self, db_session, sample_evidence_with_embeddings):
        """Test that search returns complete evidence content."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=1
        )

        # Verify content is returned
        assert len(results) > 0
        assert len(results[0].content) > 0
        assert results[0].evidence_id is not None

    def test_batch_search(self, db_session, sample_evidence_with_embeddings):
        """Test batch vector search."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        # Multiple queries
        query_embeddings = [[0.1] * 384, [0.2] * 384, [0.3] * 384]

        batch_results = service.search_similar_evidence_batch(
            db=db_session, query_embeddings=query_embeddings, top_k=5
        )

        # Should return results for each query
        assert len(batch_results) == 3
        assert all(isinstance(results, list) for results in batch_results)

    def test_embedding_stats(self, db_session, sample_evidence_with_embeddings):
        """Test getting embedding statistics."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        stats = service.get_embedding_stats(db=db_session, entity_type="evidence")

        # Verify stats
        assert stats["total_embeddings"] == 3
        assert stats["entity_type"] == "evidence"
        assert stats["tenant_id"] == "default"
        assert stats["has_null_embeddings"] is False

    def test_empty_database(self, db_session):
        """Test search on empty database."""
        service = VectorSearchService(embedding_dimension=384)

        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(db=db_session, query_embedding=query_embedding)

        # Should return empty results
        assert len(results) == 0

    def test_similarity_scores_ordered(self, db_session, sample_evidence_with_embeddings):
        """Test that results are ordered by similarity (highest first)."""
        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        query_embedding = [0.15] * 384
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=10
        )

        # Verify results are sorted by similarity descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity >= results[i + 1].similarity


@pytest.mark.skipif(
    os.getenv("TEST_DATABASE_URL") is None,
    reason="TEST_DATABASE_URL not set, skipping integration tests",
)
class TestVectorSearchPerformance:
    """Performance tests for vector search (requires test database)."""

    def test_query_performance_small_corpus(self, db_session, sample_evidence_with_embeddings):
        """Test query performance on small corpus."""
        import time

        evidence_data, embeddings_data = sample_evidence_with_embeddings
        service = VectorSearchService(embedding_dimension=384)

        query_embedding = [0.15] * 384

        # Measure query time
        start_time = time.time()
        results = service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=10
        )
        end_time = time.time()
        assert results

        query_time_ms = (end_time - start_time) * 1000

        # Should complete quickly (< 100ms for small corpus)
        assert query_time_ms < 100, f"Query took {query_time_ms:.2f}ms (expected < 100ms)"
        print(f"Query time: {query_time_ms:.2f}ms")
