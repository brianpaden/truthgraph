"""Unit tests for vector search service.

These tests use mocks to avoid requiring a real database connection.
"""

from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest

from truthgraph.services.vector_search_service import (
    SearchResult,
    VectorSearchService,
)


class TestVectorSearchService:
    """Test suite for VectorSearchService."""

    @pytest.fixture
    def mock_db_with_cursor(self):
        """Create a mock database session with proper cursor nesting."""

        def _make_mock(fetchall_return=None, execute_side_effect=None):
            mock_cursor = MagicMock()
            if execute_side_effect:
                mock_cursor.execute.side_effect = execute_side_effect
            else:
                mock_cursor.execute.return_value = None

            if fetchall_return is not None:
                mock_cursor.fetchall.return_value = fetchall_return

            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_conn.cursor.return_value.__exit__.return_value = None

            mock_connection = MagicMock()
            mock_connection.connection = mock_conn

            db_mock = MagicMock()
            db_mock.connection.return_value = mock_connection

            return db_mock, mock_cursor

        return _make_mock

    def test_initialization_default_dimension(self):
        """Test service initializes with default 1536 dimensions."""
        service = VectorSearchService()
        assert service.embedding_dimension == 1536

    def test_initialization_384_dimension(self):
        """Test service initializes with 384 dimensions."""
        service = VectorSearchService(embedding_dimension=384)
        assert service.embedding_dimension == 384

    def test_initialization_invalid_dimension(self):
        """Test service raises error for invalid dimensions."""
        with pytest.raises(ValueError, match="Unsupported embedding dimension"):
            VectorSearchService(embedding_dimension=512)

    def test_search_similar_evidence_validates_dimension(self):
        """Test that search validates query embedding dimension."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Wrong dimension should raise error
        with pytest.raises(ValueError, match="must be 384-dimensional"):
            service.search_similar_evidence(
                db=db_mock,
                query_embedding=[0.1] * 1536,  # Wrong size
            )

    def test_search_similar_evidence_success(self):
        """Test successful vector search returns results."""
        service = VectorSearchService(embedding_dimension=384)

        # Create properly nested mocks for db.connection().connection.cursor()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                UUID("12345678-1234-5678-1234-567812345678"),
                "Test evidence content",
                "https://example.com",
                0.95,
            ),
            (
                UUID("87654321-4321-8765-4321-876543218765"),
                "Another evidence",
                "https://example.org",
                0.87,
            ),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_connection = MagicMock()
        mock_connection.connection = mock_conn

        db_mock = MagicMock()
        db_mock.connection.return_value = mock_connection

        # Execute search
        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_mock, query_embedding=query_embedding, top_k=10, min_similarity=0.5
        )

        # Verify results
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].evidence_id == UUID("12345678-1234-5678-1234-567812345678")
        assert results[0].content == "Test evidence content"
        assert results[0].source_url == "https://example.com"
        assert results[0].similarity == 0.95

        assert results[1].similarity == 0.87

        # Verify cursor was used
        mock_cursor.execute.assert_called_once()

    def test_search_similar_evidence_empty_results(self):
        """Test vector search with no matching results."""
        service = VectorSearchService(embedding_dimension=1536)

        # Create properly nested mocks
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_connection = MagicMock()
        mock_connection.connection = mock_conn

        db_mock = MagicMock()
        db_mock.connection.return_value = mock_connection

        # Execute search
        query_embedding = [0.1] * 1536
        results = service.search_similar_evidence(
            db=db_mock, query_embedding=query_embedding, min_similarity=0.9
        )

        # Verify empty results
        assert len(results) == 0
        assert isinstance(results, list)

    def test_search_similar_evidence_with_source_filter(self, mock_db_with_cursor):
        """Test vector search with source URL filter."""
        service = VectorSearchService(embedding_dimension=384)

        # Create mock with filtered results
        db_mock, mock_cursor = mock_db_with_cursor(
            fetchall_return=[
                (
                    uuid4(),
                    "Filtered evidence",
                    "https://example.com",
                    0.92,
                )
            ]
        )

        # Execute search with source filter
        query_embedding = [0.1] * 384
        results = service.search_similar_evidence(
            db=db_mock,
            query_embedding=query_embedding,
            source_filter="https://example.com",
        )

        # Verify filter was applied
        assert len(results) == 1
        assert results[0].source_url == "https://example.com"

        # Verify SQL was executed with source_filter parameter
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert sql
        assert "source_filter" in params
        assert params["source_filter"] == "https://example.com"

    def test_search_similar_evidence_database_error(self):
        """Test vector search handles database errors."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Mock database error
        db_mock.execute.side_effect = Exception("Database connection failed")

        # Execute search and expect RuntimeError
        query_embedding = [0.1] * 384
        with pytest.raises(RuntimeError, match="Vector search query failed"):
            service.search_similar_evidence(db=db_mock, query_embedding=query_embedding)

    def test_search_similar_evidence_tenant_isolation(self, mock_db_with_cursor):
        """Test vector search respects tenant isolation."""
        service = VectorSearchService(embedding_dimension=384)

        # Create mock with empty results
        db_mock, mock_cursor = mock_db_with_cursor(fetchall_return=[])

        # Execute search with custom tenant
        query_embedding = [0.1] * 384
        service.search_similar_evidence(
            db=db_mock, query_embedding=query_embedding, tenant_id="tenant_123"
        )

        # Verify tenant_id was passed to query
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params.get("tenant_id") == "tenant_123"

    def test_search_similar_evidence_batch_success(self):
        """Test batch vector search returns results for all queries."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Mock database responses
        mock_result_1 = MagicMock()
        mock_result_1.fetchall.return_value = [(uuid4(), "Evidence 1", None, 0.9)]

        mock_result_2 = MagicMock()
        mock_result_2.fetchall.return_value = [(uuid4(), "Evidence 2", None, 0.85)]

        db_mock.execute.side_effect = [mock_result_1, mock_result_2]

        # Execute batch search
        query_embeddings = [[0.1] * 384, [0.2] * 384]
        batch_results = service.search_similar_evidence_batch(
            db=db_mock, query_embeddings=query_embeddings
        )

        # Verify results
        assert len(batch_results) == 2
        assert len(batch_results[0]) == 1
        assert len(batch_results[1]) == 1
        assert batch_results[0][0].content == "Evidence 1"
        assert batch_results[1][0].content == "Evidence 2"

    def test_search_similar_evidence_batch_handles_errors(self):
        """Test batch search handles individual query failures."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # First query succeeds, second fails
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(uuid4(), "Evidence 1", None, 0.9)]

        db_mock.execute.side_effect = [
            mock_result,
            Exception("Query failed"),
        ]

        # Execute batch search
        query_embeddings = [[0.1] * 384, [0.2] * 384]
        batch_results = service.search_similar_evidence_batch(
            db=db_mock, query_embeddings=query_embeddings
        )

        # Verify first succeeded, second returned empty
        assert len(batch_results) == 2
        assert len(batch_results[0]) == 1
        assert len(batch_results[1]) == 0  # Failed query returns empty list

    def test_get_embedding_stats_success(self):
        """Test getting embedding statistics."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100, 5)  # 100 total, 5 null
        db_mock.execute.return_value = mock_result

        # Get stats
        stats = service.get_embedding_stats(db=db_mock, entity_type="evidence")

        # Verify stats
        assert stats["total_embeddings"] == 100
        assert stats["null_embedding_count"] == 5
        assert stats["has_null_embeddings"] is True
        assert stats["entity_type"] == "evidence"
        assert stats["tenant_id"] == "default"

    def test_get_embedding_stats_no_null_embeddings(self):
        """Test stats when no null embeddings exist."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Mock database response with no nulls
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (50, 0)  # 50 total, 0 null
        db_mock.execute.return_value = mock_result

        # Get stats
        stats = service.get_embedding_stats(db=db_mock)

        # Verify
        assert stats["has_null_embeddings"] is False
        assert stats["null_embedding_count"] == 0

    def test_get_embedding_stats_database_error(self):
        """Test stats handles database errors gracefully."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        # Mock database error
        db_mock.execute.side_effect = Exception("Connection lost")

        # Get stats
        stats = service.get_embedding_stats(db=db_mock)

        # Verify error is handled gracefully
        assert stats["total_embeddings"] == 0
        assert "error" in stats
        assert "Connection lost" in stats["error"]

    def test_similarity_threshold_conversion(self):
        """Test that similarity threshold is correctly converted to distance."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db_mock.execute.return_value = mock_result

        # Search with min_similarity=0.8
        query_embedding = [0.1] * 384
        service.search_similar_evidence(
            db=db_mock, query_embedding=query_embedding, min_similarity=0.8
        )

        # Verify max_distance = 1 - 0.8 = 0.2
        call_args = db_mock.execute.call_args
        params = call_args.args[1] if len(call_args.args) > 1 else {}
        assert params.get("max_distance") == pytest.approx(0.2, abs=0.001)

    def test_top_k_parameter(self):
        """Test that top_k parameter is passed correctly."""
        service = VectorSearchService(embedding_dimension=384)
        db_mock = Mock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db_mock.execute.return_value = mock_result

        # Search with top_k=5
        query_embedding = [0.1] * 384
        service.search_similar_evidence(db=db_mock, query_embedding=query_embedding, top_k=5)

        # Verify top_k was passed
        call_args = db_mock.execute.call_args
        params = call_args.args[1] if len(call_args.args) > 1 else {}
        assert params.get("top_k") == 5

        # Verify LIMIT clause in SQL
        sql = call_args[0][0].text
        assert "LIMIT :top_k" in sql


class TestSearchResult:
    """Test suite for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test SearchResult can be created with all fields."""
        result = SearchResult(
            evidence_id=UUID("12345678-1234-5678-1234-567812345678"),
            content="Test content",
            source_url="https://example.com",
            similarity=0.95,
        )

        assert result.evidence_id == UUID("12345678-1234-5678-1234-567812345678")
        assert result.content == "Test content"
        assert result.source_url == "https://example.com"
        assert result.similarity == 0.95

    def test_search_result_optional_source_url(self):
        """Test SearchResult with no source URL."""
        result = SearchResult(evidence_id=uuid4(), content="Test", source_url=None, similarity=0.8)

        assert result.source_url is None
