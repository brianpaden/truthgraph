"""Hybrid search service combining vector similarity and keyword search.

This module provides hybrid search functionality that combines:
1. Vector similarity search using pgvector (semantic search)
2. PostgreSQL full-text search (keyword search)
3. Reciprocal Rank Fusion (RRF) for result merging

The hybrid approach leverages the strengths of both methods:
- Vector search: Captures semantic meaning and context
- Keyword search: Exact term matching and traditional IR
- RRF: Robust rank aggregation without score normalization

Performance target: <150ms for hybrid queries
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from .vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from a hybrid search query.

    Attributes:
        evidence_id: UUID of the evidence document
        content: Full text content of the evidence
        source_url: URL source of the evidence (if available)
        rank_score: Combined RRF score (higher is better)
        vector_similarity: Cosine similarity from vector search (0-1, if found)
        keyword_rank: Rank position from keyword search (if found)
        matched_via: How this result was found ('vector', 'keyword', or 'both')
    """

    evidence_id: UUID
    content: str
    source_url: Optional[str]
    rank_score: float
    vector_similarity: Optional[float] = None
    keyword_rank: Optional[int] = None
    matched_via: str = "both"


class HybridSearchService:
    """Service for hybrid search combining vector and keyword search.

    This service implements a hybrid search strategy that:
    1. Performs parallel vector similarity search (using VectorSearchService)
    2. Performs PostgreSQL full-text keyword search
    3. Merges results using Reciprocal Rank Fusion (RRF)
    4. Returns ranked, deduplicated results

    Reciprocal Rank Fusion (RRF):
        RRF is a robust rank aggregation method that combines rankings from
        multiple retrieval systems without requiring score normalization.

        Formula: RRF_score(d) = Σ 1 / (k + rank(d))

        Where:
        - d is a document
        - rank(d) is the rank position in a retrieval system (1-indexed)
        - k is a constant (typically 60) to reduce impact of high ranks
        - Σ sums across all retrieval systems

        Benefits:
        - No score normalization needed
        - Robust to different score distributions
        - Simple and effective
        - Proven in IR research

    Performance characteristics:
        - Target: <150ms for hybrid queries
        - Parallel execution of vector + keyword search
        - Efficient RRF implementation with dict lookups
        - Minimal memory overhead

    Example:
        >>> service = HybridSearchService(embedding_dimension=1536)
        >>> results = service.hybrid_search(
        ...     db=db_session,
        ...     query_text="climate change effects",
        ...     query_embedding=[0.1, 0.2, ...],
        ...     top_k=10,
        ...     vector_weight=0.6,
        ...     keyword_weight=0.4
        ... )
        >>> for result in results:
        ...     print(f"{result.rank_score:.3f}: {result.content[:100]}")
    """

    # RRF constant - higher values reduce impact of high ranks
    # Standard value is 60 based on IR research
    RRF_K: int = 60

    def __init__(self, embedding_dimension: int = 1536) -> None:
        """Initialize the hybrid search service.

        Args:
            embedding_dimension: Dimension of embeddings (384 or 1536, default: 1536)
        """
        self.vector_service = VectorSearchService(embedding_dimension=embedding_dimension)
        self.embedding_dimension = embedding_dimension
        logger.info(f"HybridSearchService initialized with {embedding_dimension}-dim embeddings")

    def _keyword_search(
        self,
        db: Session,
        query_text: str,
        top_k: int = 50,
        tenant_id: str = "default",
        source_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[tuple[UUID, str, Optional[str], int]]:
        """Perform PostgreSQL full-text search on evidence content.

        Uses PostgreSQL's built-in full-text search with:
        - to_tsvector for document indexing
        - to_tsquery for query parsing
        - ts_rank for relevance scoring

        Args:
            db: SQLAlchemy database session
            query_text: Search query text
            top_k: Maximum number of results (default: 50)
            tenant_id: Tenant identifier (default: 'default')
            source_filter: Optional source URL filter
            date_from: Optional minimum creation date
            date_to: Optional maximum creation date

        Returns:
            List of tuples: (evidence_id, content, source_url, rank_position)
            Sorted by relevance (rank position 1 = most relevant)

        Raises:
            RuntimeError: If keyword search fails
        """
        # Build the full-text search query
        # Use plainto_tsquery for natural language queries (handles special chars)
        sql_query = """
        SELECT
            e.id,
            e.content,
            e.source_url,
            ts_rank(to_tsvector('english', e.content), query) as rank_score
        FROM evidence e,
             plainto_tsquery('english', :query_text) query
        WHERE to_tsvector('english', e.content) @@ query
        """

        params = {
            "query_text": query_text,
            "top_k": top_k,
        }

        # Add optional filters
        if source_filter:
            sql_query += "    AND e.source_url = :source_filter\n"
            params["source_filter"] = source_filter

        if date_from:
            sql_query += "    AND e.created_at >= :date_from\n"
            params["date_from"] = date_from

        if date_to:
            sql_query += "    AND e.created_at <= :date_to\n"
            params["date_to"] = date_to

        # Order by relevance and limit
        sql_query += """
        ORDER BY rank_score DESC
        LIMIT :top_k
        """

        try:
            result = db.execute(text(sql_query), params)
            rows = result.fetchall()

            # Convert to ranked results (rank position starts at 1)
            ranked_results = [(row[0], row[1], row[2], i + 1) for i, row in enumerate(rows)]

            logger.debug(
                f"Keyword search returned {len(ranked_results)} results "
                f"for query: '{query_text[:50]}...'"
            )

            return ranked_results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}", exc_info=True)
            raise RuntimeError(f"Keyword search query failed: {e}") from e

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[tuple[UUID, str, Optional[str], float]],
        keyword_results: list[tuple[UUID, str, Optional[str], int]],
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        k: int = 60,
    ) -> list[HybridSearchResult]:
        """Merge vector and keyword results using Reciprocal Rank Fusion.

        RRF Formula: RRF_score(d) = vector_weight * 1/(k + vector_rank(d)) +
                                     keyword_weight * 1/(k + keyword_rank(d))

        Args:
            vector_results: Vector search results (evidence_id, content, source_url, similarity)
            keyword_results: Keyword search results (evidence_id, content, source_url, rank)
            vector_weight: Weight for vector search contribution (default: 0.5)
            keyword_weight: Weight for keyword search contribution (default: 0.5)
            k: RRF constant (default: 60)

        Returns:
            List of HybridSearchResult objects sorted by RRF score (descending)

        Note:
            - Weights don't need to sum to 1.0 but typically do
            - Higher weights emphasize that retrieval method
            - k=60 is standard in IR research
        """
        # Normalize weights to sum to 1.0
        total_weight = vector_weight + keyword_weight
        if total_weight == 0:
            raise ValueError("At least one weight must be > 0")

        vector_weight = vector_weight / total_weight
        keyword_weight = keyword_weight / total_weight

        # Build lookup dictionaries for fast access
        # Vector results: evidence_id -> (content, source_url, similarity, rank_position)
        vector_dict = {
            result[0]: (result[1], result[2], result[3], i + 1)
            for i, result in enumerate(vector_results)
        }

        # Keyword results: evidence_id -> (content, source_url, rank_position)
        keyword_dict = {result[0]: (result[1], result[2], result[3]) for result in keyword_results}

        # Collect all unique evidence IDs
        all_evidence_ids = set(vector_dict.keys()) | set(keyword_dict.keys())

        # Calculate RRF scores for all documents
        hybrid_results = []

        for evidence_id in all_evidence_ids:
            rrf_score = 0.0
            content = ""
            source_url = None
            vector_similarity = None
            keyword_rank = None
            matched_via = ""

            # Add vector contribution if present
            if evidence_id in vector_dict:
                vec_content, vec_source, vec_sim, vec_rank = vector_dict[evidence_id]
                rrf_score += vector_weight * (1.0 / (k + vec_rank))
                content = vec_content
                source_url = vec_source
                vector_similarity = vec_sim
                matched_via = "vector"

            # Add keyword contribution if present
            if evidence_id in keyword_dict:
                kw_content, kw_source, kw_rank = keyword_dict[evidence_id]
                rrf_score += keyword_weight * (1.0 / (k + kw_rank))

                # Use keyword content if not already set
                if not content:
                    content = kw_content
                    source_url = kw_source

                keyword_rank = kw_rank
                matched_via = "keyword" if matched_via == "" else "both"

            hybrid_results.append(
                HybridSearchResult(
                    evidence_id=evidence_id,
                    content=content,
                    source_url=source_url,
                    rank_score=rrf_score,
                    vector_similarity=vector_similarity,
                    keyword_rank=keyword_rank,
                    matched_via=matched_via,
                )
            )

        # Sort by RRF score (descending)
        hybrid_results.sort(key=lambda x: x.rank_score, reverse=True)

        logger.debug(
            f"RRF fusion: {len(vector_results)} vector + {len(keyword_results)} keyword "
            f"-> {len(hybrid_results)} unique results"
        )

        return hybrid_results

    def hybrid_search(
        self,
        db: Session,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 10,
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        min_vector_similarity: float = 0.0,
        tenant_id: str = "default",
        source_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[HybridSearchResult], float]:
        """Perform hybrid search combining vector and keyword search.

        This is the main entry point for hybrid search. It:
        1. Executes vector similarity search
        2. Executes keyword full-text search
        3. Merges results using Reciprocal Rank Fusion
        4. Returns top-k ranked results

        Args:
            db: SQLAlchemy database session
            query_text: Natural language query text (for keyword search)
            query_embedding: Query embedding vector (for vector search)
            top_k: Maximum number of results to return (default: 10)
            vector_weight: Weight for vector search (default: 0.5)
            keyword_weight: Weight for keyword search (default: 0.5)
            min_vector_similarity: Minimum similarity for vector search (default: 0.0)
            tenant_id: Tenant identifier (default: 'default')
            source_filter: Optional source URL filter
            date_from: Optional minimum creation date
            date_to: Optional maximum creation date

        Returns:
            Tuple of (results, query_time_ms):
            - results: List of HybridSearchResult objects
            - query_time_ms: Total query time in milliseconds

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If search fails

        Example:
            >>> results, time_ms = service.hybrid_search(
            ...     db=session,
            ...     query_text="climate change impacts",
            ...     query_embedding=[0.1] * 1536,
            ...     top_k=10,
            ...     vector_weight=0.6,
            ...     keyword_weight=0.4
            ... )
            >>> print(f"Found {len(results)} results in {time_ms:.1f}ms")
        """
        start_time = time.time()

        # Validate inputs
        if len(query_embedding) != self.embedding_dimension:
            raise ValueError(
                f"Query embedding must be {self.embedding_dimension}-dimensional, "
                f"got {len(query_embedding)}"
            )

        if not query_text:
            raise ValueError("Query text cannot be empty")

        if vector_weight < 0 or keyword_weight < 0:
            raise ValueError("Weights must be non-negative")

        if vector_weight + keyword_weight == 0:
            raise ValueError("At least one weight must be positive")

        try:
            # Fetch more results than needed for RRF fusion
            # This ensures we have enough candidates after deduplication
            retrieval_k = max(top_k * 3, 50)

            # 1. Vector similarity search
            vector_results_objs = self.vector_service.search_similar_evidence(
                db=db,
                query_embedding=query_embedding,
                top_k=retrieval_k,
                min_similarity=min_vector_similarity,
                tenant_id=tenant_id,
                source_filter=source_filter,
            )

            # Convert to tuple format for RRF
            vector_results = [
                (r.evidence_id, r.content, r.source_url, r.similarity) for r in vector_results_objs
            ]

            # 2. Keyword full-text search
            keyword_results = self._keyword_search(
                db=db,
                query_text=query_text,
                top_k=retrieval_k,
                tenant_id=tenant_id,
                source_filter=source_filter,
                date_from=date_from,
                date_to=date_to,
            )

            # 3. Merge using Reciprocal Rank Fusion
            hybrid_results = self._reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                k=self.RRF_K,
            )

            # 4. Return top-k results
            final_results = hybrid_results[:top_k]

            # Calculate query time
            query_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Hybrid search completed in {query_time_ms:.1f}ms: "
                f"{len(final_results)} results (vector: {len(vector_results)}, "
                f"keyword: {len(keyword_results)}, weights: {vector_weight:.2f}/"
                f"{keyword_weight:.2f})"
            )

            return final_results, query_time_ms

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            raise RuntimeError(f"Hybrid search failed: {e}") from e

    def keyword_only_search(
        self,
        db: Session,
        query_text: str,
        top_k: int = 10,
        tenant_id: str = "default",
        source_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[HybridSearchResult], float]:
        """Perform keyword-only search (for comparison or fallback).

        Args:
            db: SQLAlchemy database session
            query_text: Search query text
            top_k: Maximum number of results (default: 10)
            tenant_id: Tenant identifier (default: 'default')
            source_filter: Optional source URL filter
            date_from: Optional minimum creation date
            date_to: Optional maximum creation date

        Returns:
            Tuple of (results, query_time_ms)

        Example:
            >>> results, time_ms = service.keyword_only_search(
            ...     db=session,
            ...     query_text="machine learning",
            ...     top_k=10
            ... )
        """
        start_time = time.time()

        keyword_results = self._keyword_search(
            db=db,
            query_text=query_text,
            top_k=top_k,
            tenant_id=tenant_id,
            source_filter=source_filter,
            date_from=date_from,
            date_to=date_to,
        )

        # Convert to HybridSearchResult format
        results = [
            HybridSearchResult(
                evidence_id=result[0],
                content=result[1],
                source_url=result[2],
                rank_score=1.0 / (self.RRF_K + result[3]),  # RRF score
                keyword_rank=result[3],
                matched_via="keyword",
            )
            for result in keyword_results
        ]

        query_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Keyword-only search completed in {query_time_ms:.1f}ms: {len(results)} results"
        )

        return results, query_time_ms

    def get_search_stats(
        self,
        db: Session,
        tenant_id: str = "default",
    ) -> dict:
        """Get statistics about searchable evidence.

        Args:
            db: SQLAlchemy database session
            tenant_id: Tenant identifier (default: 'default')

        Returns:
            Dictionary with statistics:
                - total_evidence: Total evidence documents
                - evidence_with_embeddings: Evidence with vector embeddings
                - embedding_coverage: Percentage with embeddings

        Example:
            >>> stats = service.get_search_stats(session)
            >>> print(f"Coverage: {stats['embedding_coverage']:.1f}%")
        """
        # Get total evidence count
        evidence_count_query = "SELECT COUNT(*) FROM evidence"
        evidence_count = db.execute(text(evidence_count_query)).scalar()

        # Get embedding stats from vector service
        embedding_stats = self.vector_service.get_embedding_stats(
            db=db, entity_type="evidence", tenant_id=tenant_id
        )

        coverage = (
            (embedding_stats["total_embeddings"] / evidence_count * 100)
            if evidence_count > 0
            else 0.0
        )

        return {
            "total_evidence": evidence_count,
            "evidence_with_embeddings": embedding_stats["total_embeddings"],
            "embedding_coverage": coverage,
            "tenant_id": tenant_id,
        }
