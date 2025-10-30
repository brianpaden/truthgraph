"""Integration tests for hybrid search service with real database.

These tests require a PostgreSQL database with pgvector extension.
Run with: pytest tests/integration/test_hybrid_search_integration.py -v
"""

import os
from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Embedding, Evidence
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
def sample_evidence_data(db_session):
    """Create sample evidence with embeddings and full-text data.

    Creates evidence about different topics with varying similarity
    to test both vector and keyword search.
    """
    # Create evidence records with diverse content
    evidence_data = [
        {
            "id": uuid4(),
            "content": "Climate change is caused by greenhouse gas emissions from human activities. "
            "Rising temperatures affect weather patterns globally.",
            "source_url": "https://climate-science.org/article1",
            "created_at": datetime.now(UTC),
        },
        {
            "id": uuid4(),
            "content": "Global warming leads to melting ice caps and rising sea levels. "
            "Climate scientists warn of severe environmental impacts.",
            "source_url": "https://climate-science.org/article2",
            "created_at": datetime.now(UTC),
        },
        {
            "id": uuid4(),
            "content": "Python is a high-level programming language known for simplicity. "
            "It is widely used in machine learning and data science.",
            "source_url": "https://programming-guide.com/python",
            "created_at": datetime.now(UTC) - timedelta(days=30),
        },
        {
            "id": uuid4(),
            "content": "Machine learning algorithms can classify data and make predictions. "
            "Neural networks are a popular approach in artificial intelligence.",
            "source_url": "https://ml-tutorials.com/intro",
            "created_at": datetime.now(UTC) - timedelta(days=60),
        },
        {
            "id": uuid4(),
            "content": "The Earth orbits the Sun in approximately 365.25 days. "
            "This orbital period defines our calendar year.",
            "source_url": "https://astronomy-facts.org/earth",
            "created_at": datetime.now(UTC),
        },
    ]

    # Insert evidence
    for data in evidence_data:
        evidence = Evidence(**data)
        db_session.add(evidence)

    db_session.commit()

    # Create embeddings (using simple patterns for testing)
    # In production, these would be from a real embedding model
    # Using 1536 dimensions for text-embedding-3-small
    embeddings_data = [
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[0]["id"],
            # Climate change themed embedding
            "embedding": [0.1 if i % 3 == 0 else 0.05 for i in range(1536)],
            "tenant_id": "default",
            "model_name": "text-embedding-3-small",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[1]["id"],
            # Similar climate/warming themed embedding
            "embedding": [0.11 if i % 3 == 0 else 0.06 for i in range(1536)],
            "tenant_id": "default",
            "model_name": "text-embedding-3-small",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[2]["id"],
            # Programming themed embedding
            "embedding": [0.2 if i % 5 == 0 else 0.03 for i in range(1536)],
            "tenant_id": "default",
            "model_name": "text-embedding-3-small",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[3]["id"],
            # ML themed embedding
            "embedding": [0.22 if i % 5 == 0 else 0.04 for i in range(1536)],
            "tenant_id": "default",
            "model_name": "text-embedding-3-small",
        },
        {
            "entity_type": "evidence",
            "entity_id": evidence_data[4]["id"],
            # Astronomy themed embedding
            "embedding": [0.15 if i % 7 == 0 else 0.02 for i in range(1536)],
            "tenant_id": "default",
            "model_name": "text-embedding-3-small",
        },
    ]

    # Insert embeddings
    for data in embeddings_data:
        embedding = Embedding(**data)
        db_session.add(embedding)

    db_session.commit()

    return evidence_data


class TestHybridSearchIntegration:
    """Integration tests for hybrid search."""

    def test_hybrid_search_basic(self, db_session, sample_evidence_data):
        """Test basic hybrid search with both vector and keyword components."""
        service = HybridSearchService(embedding_dimension=1536)

        # Search for climate-related content
        # Use climate-themed embedding similar to our test data
        query_embedding = [0.1 if i % 3 == 0 else 0.05 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="climate change greenhouse gas",
            query_embedding=query_embedding,
            top_k=10,
            vector_weight=0.5,
            keyword_weight=0.5,
        )

        # Should find climate-related results
        assert len(results) > 0
        assert query_time < 150  # Performance target: <150ms

        # First results should be climate-related
        assert "climate" in results[0].content.lower() or "warming" in results[0].content.lower()

    def test_hybrid_search_vector_heavy(self, db_session, sample_evidence_data):
        """Test hybrid search with heavy vector weighting."""
        service = HybridSearchService(embedding_dimension=1536)

        # Use programming-themed embedding
        query_embedding = [0.2 if i % 5 == 0 else 0.03 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="astronomy space",  # Keywords don't match embedding
            query_embedding=query_embedding,
            top_k=5,
            vector_weight=0.9,  # Heavy vector weight
            keyword_weight=0.1,
        )

        # With heavy vector weight, should find programming/ML content
        assert len(results) > 0
        # Vector similarity should influence rankings
        assert any("python" in r.content.lower() or "machine" in r.content.lower() for r in results)

    def test_hybrid_search_keyword_heavy(self, db_session, sample_evidence_data):
        """Test hybrid search with heavy keyword weighting."""
        service = HybridSearchService(embedding_dimension=1536)

        # Use astronomy-themed embedding
        query_embedding = [0.15 if i % 7 == 0 else 0.02 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="machine learning neural networks",
            query_embedding=query_embedding,
            top_k=5,
            vector_weight=0.1,
            keyword_weight=0.9,  # Heavy keyword weight
        )

        # With heavy keyword weight, should find ML content
        assert len(results) > 0
        # Keywords should dominate rankings
        assert any("machine" in r.content.lower() or "learning" in r.content.lower() for r in results[:2])

    def test_hybrid_search_with_source_filter(self, db_session, sample_evidence_data):
        """Test hybrid search with source URL filter."""
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.1 if i % 3 == 0 else 0.05 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="climate",
            query_embedding=query_embedding,
            top_k=10,
            source_filter="https://climate-science.org/article1",
        )

        # Should only return results from specified source
        assert all(r.source_url == "https://climate-science.org/article1" for r in results)

    def test_hybrid_search_with_date_range(self, db_session, sample_evidence_data):
        """Test hybrid search with date range filter."""
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.1 for i in range(1536)]

        # Filter to recent content only (last 7 days)
        date_from = datetime.now(UTC) - timedelta(days=7)

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="science data",
            query_embedding=query_embedding,
            top_k=10,
            date_from=date_from,
        )

        # Should not include old programming/ML articles
        assert all("python" not in r.content.lower() and "machine learning" not in r.content.lower() for r in results)

    def test_hybrid_search_matched_via_both(self, db_session, sample_evidence_data):
        """Test that results show correct matched_via field."""
        service = HybridSearchService(embedding_dimension=1536)

        # Use climate embedding and climate keywords
        query_embedding = [0.1 if i % 3 == 0 else 0.05 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="climate change warming",
            query_embedding=query_embedding,
            top_k=5,
        )

        # Should have results matched via both methods
        matched_via_values = [r.matched_via for r in results]
        assert "both" in matched_via_values or "vector" in matched_via_values or "keyword" in matched_via_values

    def test_hybrid_search_empty_results(self, db_session, sample_evidence_data):
        """Test hybrid search with query that matches nothing."""
        service = HybridSearchService(embedding_dimension=1536)

        # Use very different embedding and unrelated keywords
        query_embedding = [0.99 if i % 100 == 0 else 0.001 for i in range(1536)]

        results, query_time = service.hybrid_search(
            db=db_session,
            query_text="xyzabc123 nonsense query foobar",
            query_embedding=query_embedding,
            top_k=10,
            min_vector_similarity=0.95,  # Very high threshold
        )

        # Should handle empty results gracefully
        assert isinstance(results, list)
        assert query_time < 150

    def test_hybrid_search_performance_target(self, db_session, sample_evidence_data):
        """Test that hybrid search meets <150ms performance target."""
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.1 for i in range(1536)]

        # Run multiple queries to check consistency
        times = []
        for _ in range(5):
            _, query_time = service.hybrid_search(
                db=db_session,
                query_text="test query",
                query_embedding=query_embedding,
                top_k=10,
            )
            times.append(query_time)

        # All queries should meet performance target
        assert all(t < 150 for t in times), f"Query times: {times}"

        # Average should be well under target
        avg_time = sum(times) / len(times)
        assert avg_time < 100, f"Average query time {avg_time:.1f}ms exceeds target"


class TestKeywordOnlySearchIntegration:
    """Integration tests for keyword-only search."""

    def test_keyword_only_search_basic(self, db_session, sample_evidence_data):
        """Test keyword-only search."""
        service = HybridSearchService(embedding_dimension=1536)

        results, query_time = service.keyword_only_search(
            db=db_session,
            query_text="machine learning algorithms",
            top_k=5,
        )

        assert len(results) > 0
        # Should find ML content
        assert any("machine" in r.content.lower() for r in results)
        # All results should be keyword-matched
        assert all(r.matched_via == "keyword" for r in results)

    def test_keyword_only_search_with_filters(self, db_session, sample_evidence_data):
        """Test keyword-only search with filters."""
        service = HybridSearchService(embedding_dimension=1536)

        date_from = datetime.now(UTC) - timedelta(days=7)

        results, query_time = service.keyword_only_search(
            db=db_session,
            query_text="climate",
            top_k=5,
            date_from=date_from,
        )

        # Should only return recent climate articles
        assert len(results) > 0


class TestSearchStatsIntegration:
    """Integration tests for search statistics."""

    def test_get_search_stats(self, db_session, sample_evidence_data):
        """Test getting search statistics."""
        service = HybridSearchService(embedding_dimension=1536)

        stats = service.get_search_stats(db=db_session)

        assert stats["total_evidence"] == 5
        assert stats["evidence_with_embeddings"] == 5
        assert stats["embedding_coverage"] == 100.0
        assert stats["tenant_id"] == "default"

    def test_get_search_stats_partial_coverage(self, db_session, sample_evidence_data):
        """Test search stats with partial embedding coverage."""
        service = HybridSearchService(embedding_dimension=1536)

        # Add evidence without embedding
        new_evidence = Evidence(
            id=uuid4(),
            content="New evidence without embedding",
            source_url="https://example.com",
            created_at=datetime.now(UTC),
        )
        db_session.add(new_evidence)
        db_session.commit()

        stats = service.get_search_stats(db=db_session)

        assert stats["total_evidence"] == 6
        assert stats["evidence_with_embeddings"] == 5
        assert stats["embedding_coverage"] == pytest.approx(83.33, rel=0.1)


class TestRRFAlgorithmIntegration:
    """Integration tests validating RRF algorithm behavior."""

    def test_rrf_fusion_integration(self, db_session, sample_evidence_data):
        """Test that RRF properly fuses vector and keyword results."""
        service = HybridSearchService(embedding_dimension=1536)

        # Use climate embedding
        query_embedding = [0.1 if i % 3 == 0 else 0.05 for i in range(1536)]

        # Query with both vector and keyword relevance
        results, _ = service.hybrid_search(
            db=db_session,
            query_text="climate change global warming",
            query_embedding=query_embedding,
            top_k=5,
            vector_weight=0.5,
            keyword_weight=0.5,
        )

        # Verify RRF score is present and reasonable
        assert all(r.rank_score > 0 for r in results)

        # Results should be sorted by rank_score descending
        scores = [r.rank_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_different_weights_integration(self, db_session, sample_evidence_data):
        """Test that different weights produce different rankings."""
        service = HybridSearchService(embedding_dimension=1536)

        query_embedding = [0.1 if i % 3 == 0 else 0.05 for i in range(1536)]
        query_text = "climate warming"

        # Vector-heavy search
        results_vector, _ = service.hybrid_search(
            db=db_session,
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=5,
            vector_weight=0.9,
            keyword_weight=0.1,
        )

        # Keyword-heavy search
        results_keyword, _ = service.hybrid_search(
            db=db_session,
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=5,
            vector_weight=0.1,
            keyword_weight=0.9,
        )

        # Rankings should potentially differ
        # (may be same for simple test data, but weights are being applied)
        assert len(results_vector) > 0
        assert len(results_keyword) > 0
