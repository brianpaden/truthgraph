"""Unit tests for HybridSearchService.

Tests the hybrid search functionality including:
- RRF algorithm correctness
- Weight handling
- Result deduplication
- Error handling
- Edge cases

Run with: pytest tests/unit/services/test_hybrid_search_service.py -v
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from truthgraph.services.hybrid_search_service import (
    HybridSearchResult,
    HybridSearchService,
)
from truthgraph.services.vector_search_service import SearchResult


class TestHybridSearchServiceInit:
    """Test HybridSearchService initialization."""

    def test_init_default_dimension(self):
        """Test initialization with default embedding dimension."""
        service = HybridSearchService()
        assert service.embedding_dimension == 1536
        assert service.vector_service.embedding_dimension == 1536

    def test_init_custom_dimension_384(self):
        """Test initialization with 384-dimensional embeddings."""
        service = HybridSearchService(embedding_dimension=384)
        assert service.embedding_dimension == 384
        assert service.vector_service.embedding_dimension == 384

    def test_init_custom_dimension_1536(self):
        """Test initialization with 1536-dimensional embeddings."""
        service = HybridSearchService(embedding_dimension=1536)
        assert service.embedding_dimension == 1536

    def test_init_invalid_dimension(self):
        """Test initialization with invalid embedding dimension raises error."""
        with pytest.raises(ValueError, match="Unsupported embedding dimension"):
            HybridSearchService(embedding_dimension=512)

    def test_rrf_k_constant(self):
        """Test RRF constant is set correctly."""
        service = HybridSearchService()
        assert service.RRF_K == 60


class TestReciprocalRankFusion:
    """Test Reciprocal Rank Fusion algorithm."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = HybridSearchService(embedding_dimension=1536)

    def test_rrf_both_sources_same_results(self):
        """Test RRF when both vector and keyword return same results."""
        # Same evidence found by both methods
        evidence_id = uuid4()
        content = "Test content"
        source_url = "https://example.com"

        vector_results = [(evidence_id, content, source_url, 0.9)]
        keyword_results = [(evidence_id, content, source_url, 1)]

        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.5,
            keyword_weight=0.5,
            k=60,
        )

        assert len(merged) == 1
        assert merged[0].evidence_id == evidence_id
        assert merged[0].matched_via == "both"
        assert merged[0].vector_similarity == 0.9
        assert merged[0].keyword_rank == 1

    def test_rrf_only_vector_results(self):
        """Test RRF with only vector results."""
        evidence_id = uuid4()
        content = "Vector only content"
        source_url = "https://example.com"

        vector_results = [(evidence_id, content, source_url, 0.8)]
        keyword_results = []

        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.6,
            keyword_weight=0.4,
            k=60,
        )

        assert len(merged) == 1
        assert merged[0].evidence_id == evidence_id
        assert merged[0].matched_via == "vector"
        assert merged[0].vector_similarity == 0.8
        assert merged[0].keyword_rank is None

    def test_rrf_only_keyword_results(self):
        """Test RRF with only keyword results."""
        evidence_id = uuid4()
        content = "Keyword only content"
        source_url = "https://example.com"

        vector_results = []
        keyword_results = [(evidence_id, content, source_url, 2)]

        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.5,
            keyword_weight=0.5,
            k=60,
        )

        assert len(merged) == 1
        assert merged[0].evidence_id == evidence_id
        assert merged[0].matched_via == "keyword"
        assert merged[0].vector_similarity is None
        assert merged[0].keyword_rank == 2

    def test_rrf_multiple_results_ranking(self):
        """Test RRF correctly ranks multiple results."""
        id1, id2, id3 = uuid4(), uuid4(), uuid4()

        # id1: rank 1 in vector, rank 2 in keyword
        # id2: rank 2 in vector, rank 1 in keyword
        # id3: only in vector, rank 3

        vector_results = [
            (id1, "content1", None, 0.95),
            (id2, "content2", None, 0.85),
            (id3, "content3", None, 0.75),
        ]

        keyword_results = [
            (id2, "content2", None, 1),
            (id1, "content1", None, 2),
        ]

        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.5,
            keyword_weight=0.5,
            k=60,
        )

        # id1 and id2 should rank higher than id3 (found in both)
        # Exact order depends on RRF calculation
        assert len(merged) == 3

        # id1 RRF = 0.5 * 1/(60+1) + 0.5 * 1/(60+2) = 0.5/61 + 0.5/62
        # id2 RRF = 0.5 * 1/(60+2) + 0.5 * 1/(60+1) = 0.5/62 + 0.5/61
        # id3 RRF = 0.5 * 1/(60+3) = 0.5/63

        # id1 and id2 should have similar scores (both found in both lists)
        assert merged[0].evidence_id in [id1, id2]
        assert merged[1].evidence_id in [id1, id2]
        assert merged[2].evidence_id == id3

    def test_rrf_weight_normalization(self):
        """Test RRF normalizes weights to sum to 1.0."""
        id1 = uuid4()

        vector_results = [(id1, "content", None, 0.9)]
        keyword_results = [(id1, "content", None, 1)]

        # Pass weights that don't sum to 1.0
        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.3,  # Will be normalized to 0.3/0.7
            keyword_weight=0.4,  # Will be normalized to 0.4/0.7
            k=60,
        )

        assert len(merged) == 1
        # Should not raise error - weights are normalized internally

    def test_rrf_zero_weights_error(self):
        """Test RRF raises error when all weights are zero."""
        vector_results = [(uuid4(), "content", None, 0.9)]
        keyword_results = []

        with pytest.raises(ValueError, match="At least one weight must be > 0"):
            self.service._reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
                vector_weight=0.0,
                keyword_weight=0.0,
                k=60,
            )

    def test_rrf_custom_k_value(self):
        """Test RRF with custom k value."""
        id1 = uuid4()
        vector_results = [(id1, "content", None, 0.9)]
        keyword_results = [(id1, "content", None, 1)]

        # With k=30 instead of 60
        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.5,
            keyword_weight=0.5,
            k=30,
        )

        assert len(merged) == 1
        # Higher k reduces impact of rank position
        # Lower k increases impact of rank position

    def test_rrf_unequal_weights(self):
        """Test RRF with unequal vector and keyword weights."""
        id1 = uuid4()
        id2 = uuid4()
        content = "Test content"

        # id1 ranks higher in vector, id2 ranks higher in keyword
        vector_results = [(id1, content, None, 0.9), (id2, content, None, 0.7)]
        keyword_results = [(id2, content, None, 1), (id1, content, None, 2)]

        # Heavy vector weighting - should favor id1
        merged_vector_heavy = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.9,
            keyword_weight=0.1,
            k=60,
        )

        # Heavy keyword weighting - should favor id2
        merged_keyword_heavy = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.1,
            keyword_weight=0.9,
            k=60,
        )

        # Both should return both results
        assert len(merged_vector_heavy) == 2
        assert len(merged_keyword_heavy) == 2

        # Top result should differ based on weights
        assert merged_vector_heavy[0].evidence_id == id1  # Vector-heavy favors id1
        assert merged_keyword_heavy[0].evidence_id == id2  # Keyword-heavy favors id2

    def test_rrf_empty_inputs(self):
        """Test RRF with empty inputs."""
        merged = self.service._reciprocal_rank_fusion(
            vector_results=[],
            keyword_results=[],
            vector_weight=0.5,
            keyword_weight=0.5,
            k=60,
        )

        assert len(merged) == 0

    def test_rrf_deduplication(self):
        """Test RRF properly deduplicates results."""
        id1 = uuid4()
        id2 = uuid4()

        # id1 appears in both, id2 only in vector
        vector_results = [
            (id1, "content1", None, 0.9),
            (id2, "content2", None, 0.8),
        ]

        keyword_results = [
            (id1, "content1", None, 1),
        ]

        merged = self.service._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.5,
            keyword_weight=0.5,
            k=60,
        )

        # Should have exactly 2 unique results
        assert len(merged) == 2
        evidence_ids = [r.evidence_id for r in merged]
        assert id1 in evidence_ids
        assert id2 in evidence_ids


class TestKeywordSearch:
    """Test keyword search functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = HybridSearchService(embedding_dimension=1536)

    def test_keyword_search_basic(self):
        """Test basic keyword search execution."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (uuid4(), "Earth orbits Sun", "https://example.com", 0.9),
            (uuid4(), "Sun is a star", "https://example.com", 0.7),
        ]
        mock_db.execute.return_value = mock_result

        results = self.service._keyword_search(
            db=mock_db,
            query_text="solar system",
            top_k=10,
        )

        assert len(results) == 2
        assert results[0][3] == 1  # First result has rank 1
        assert results[1][3] == 2  # Second result has rank 2

    def test_keyword_search_with_source_filter(self):
        """Test keyword search with source filter."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        self.service._keyword_search(
            db=mock_db,
            query_text="test query",
            source_filter="https://example.com",
        )

        # Verify source filter was included in query
        call_args = mock_db.execute.call_args
        assert "source_filter" in call_args[0][1]

    def test_keyword_search_with_date_range(self):
        """Test keyword search with date range filters."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 12, 31)

        self.service._keyword_search(
            db=mock_db,
            query_text="test query",
            date_from=date_from,
            date_to=date_to,
        )

        # Verify date filters were included
        call_args = mock_db.execute.call_args
        assert "date_from" in call_args[0][1]
        assert "date_to" in call_args[0][1]

    def test_keyword_search_error_handling(self):
        """Test keyword search error handling."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(RuntimeError, match="Keyword search query failed"):
            self.service._keyword_search(
                db=mock_db,
                query_text="test query",
            )


class TestHybridSearch:
    """Test hybrid search main method."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = HybridSearchService(embedding_dimension=1536)

    def test_hybrid_search_validation_embedding_dimension(self):
        """Test hybrid search validates embedding dimension."""
        mock_db = Mock()

        with pytest.raises(ValueError, match="Query embedding must be"):
            self.service.hybrid_search(
                db=mock_db,
                query_text="test",
                query_embedding=[0.1] * 100,  # Wrong dimension
            )

    def test_hybrid_search_validation_empty_text(self):
        """Test hybrid search validates query text is not empty."""
        mock_db = Mock()

        with pytest.raises(ValueError, match="Query text cannot be empty"):
            self.service.hybrid_search(
                db=mock_db,
                query_text="",
                query_embedding=[0.1] * 1536,
            )

    def test_hybrid_search_validation_negative_weights(self):
        """Test hybrid search validates weights are non-negative."""
        mock_db = Mock()

        with pytest.raises(ValueError, match="Weights must be non-negative"):
            self.service.hybrid_search(
                db=mock_db,
                query_text="test",
                query_embedding=[0.1] * 1536,
                vector_weight=-0.5,
            )

    def test_hybrid_search_validation_zero_weights(self):
        """Test hybrid search validates at least one weight is positive."""
        mock_db = Mock()

        with pytest.raises(ValueError, match="At least one weight must be positive"):
            self.service.hybrid_search(
                db=mock_db,
                query_text="test",
                query_embedding=[0.1] * 1536,
                vector_weight=0.0,
                keyword_weight=0.0,
            )

    @patch.object(HybridSearchService, "_keyword_search")
    @patch.object(HybridSearchService, "_reciprocal_rank_fusion")
    def test_hybrid_search_successful_execution(self, mock_rrf, mock_keyword, monkeypatch):
        """Test successful hybrid search execution."""
        # Mock vector search
        mock_vector_results = [
            SearchResult(
                evidence_id=uuid4(),
                content="Vector result",
                source_url=None,
                similarity=0.9,
            )
        ]

        monkeypatch.setattr(
            self.service.vector_service,
            "search_similar_evidence",
            lambda **kwargs: mock_vector_results,
        )

        # Mock keyword search
        mock_keyword.return_value = [
            (uuid4(), "Keyword result", None, 1),
        ]

        # Mock RRF
        mock_rrf.return_value = [
            HybridSearchResult(
                evidence_id=uuid4(),
                content="Merged result",
                source_url=None,
                rank_score=0.5,
                matched_via="both",
            )
        ]

        mock_db = Mock()
        results, query_time = self.service.hybrid_search(
            db=mock_db,
            query_text="test query",
            query_embedding=[0.1] * 1536,
            top_k=10,
        )

        assert len(results) == 1
        assert query_time > 0  # Should track query time
        assert isinstance(query_time, float)

    def test_hybrid_search_top_k_limiting(self):
        """Test hybrid search limits results to top_k."""
        # Create many mock results
        mock_hybrid_results = [
            HybridSearchResult(
                evidence_id=uuid4(),
                content=f"Result {i}",
                source_url=None,
                rank_score=1.0 - (i * 0.1),
                matched_via="both",
            )
            for i in range(20)
        ]

        with patch.object(
            self.service, "_reciprocal_rank_fusion", return_value=mock_hybrid_results
        ):
            with patch.object(
                self.service.vector_service, "search_similar_evidence", return_value=[]
            ):
                with patch.object(self.service, "_keyword_search", return_value=[]):
                    mock_db = Mock()
                    results, _ = self.service.hybrid_search(
                        db=mock_db,
                        query_text="test",
                        query_embedding=[0.1] * 1536,
                        top_k=5,
                    )

                    assert len(results) == 5


class TestKeywordOnlySearch:
    """Test keyword-only search method."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = HybridSearchService(embedding_dimension=1536)

    @patch.object(HybridSearchService, "_keyword_search")
    def test_keyword_only_search_successful(self, mock_keyword):
        """Test successful keyword-only search."""
        id1 = uuid4()
        mock_keyword.return_value = [
            (id1, "Keyword result", "https://example.com", 1),
        ]

        mock_db = Mock()
        results, query_time = self.service.keyword_only_search(
            db=mock_db,
            query_text="test query",
            top_k=10,
        )

        assert len(results) == 1
        assert results[0].evidence_id == id1
        assert results[0].matched_via == "keyword"
        assert results[0].keyword_rank == 1
        assert query_time > 0

    @patch.object(HybridSearchService, "_keyword_search")
    def test_keyword_only_search_with_filters(self, mock_keyword):
        """Test keyword-only search with filters."""
        mock_keyword.return_value = []

        mock_db = Mock()
        date_from = datetime(2024, 1, 1)

        self.service.keyword_only_search(
            db=mock_db,
            query_text="test",
            source_filter="https://example.com",
            date_from=date_from,
        )

        # Verify filters were passed
        call_kwargs = mock_keyword.call_args[1]
        assert call_kwargs["source_filter"] == "https://example.com"
        assert call_kwargs["date_from"] == date_from


class TestSearchStats:
    """Test search statistics method."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = HybridSearchService(embedding_dimension=1536)

    def test_get_search_stats_full_coverage(self):
        """Test search stats with 100% embedding coverage."""
        mock_db = Mock()

        # Mock evidence count
        mock_result = Mock()
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        # Mock embedding stats
        with patch.object(
            self.service.vector_service,
            "get_embedding_stats",
            return_value={"total_embeddings": 100},
        ):
            stats = self.service.get_search_stats(mock_db)

            assert stats["total_evidence"] == 100
            assert stats["evidence_with_embeddings"] == 100
            assert stats["embedding_coverage"] == 100.0

    def test_get_search_stats_partial_coverage(self):
        """Test search stats with partial embedding coverage."""
        mock_db = Mock()

        # Mock evidence count
        mock_result = Mock()
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        # Mock embedding stats (50% coverage)
        with patch.object(
            self.service.vector_service,
            "get_embedding_stats",
            return_value={"total_embeddings": 50},
        ):
            stats = self.service.get_search_stats(mock_db)

            assert stats["total_evidence"] == 100
            assert stats["evidence_with_embeddings"] == 50
            assert stats["embedding_coverage"] == 50.0

    def test_get_search_stats_zero_evidence(self):
        """Test search stats with no evidence."""
        mock_db = Mock()

        # Mock evidence count
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        # Mock embedding stats
        with patch.object(
            self.service.vector_service,
            "get_embedding_stats",
            return_value={"total_embeddings": 0},
        ):
            stats = self.service.get_search_stats(mock_db)

            assert stats["total_evidence"] == 0
            assert stats["evidence_with_embeddings"] == 0
            assert stats["embedding_coverage"] == 0.0
