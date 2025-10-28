"""Vector search service for semantic similarity using pgvector.

This module provides vector search functionality over evidence and claim embeddings
using pgvector's cosine distance operator for semantic similarity.

Supports both embedding models:
- all-MiniLM-L6-v2: 384 dimensions
- text-embedding-3-small: 1536 dimensions
"""

import logging
from dataclasses import dataclass
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a vector similarity search.

    Attributes:
        evidence_id: UUID of the evidence document
        content: Full text content of the evidence
        source_url: URL source of the evidence (if available)
        similarity: Cosine similarity score (0.0 to 1.0, higher is more similar)
    """

    evidence_id: UUID
    content: str
    source_url: Optional[str]
    similarity: float


class VectorSearchService:
    """Service for performing vector similarity search on embeddings.

    This service uses pgvector's cosine distance operator (<->) to find
    semantically similar evidence documents to a query embedding.

    Supports polymorphic embeddings table with entity_type filtering.

    Performance characteristics:
        - Uses IVFFlat index for approximate nearest neighbor search
        - Target: <100ms query time for 10k+ vectors
        - Cosine distance: lower values = higher similarity
        - Returns similarity scores in [0, 1] range (1 = identical)

    Example:
        >>> service = VectorSearchService()
        >>> query_embedding = [0.1, 0.2, ...]  # 384 or 1536-dimensional
        >>> results = service.search_similar_evidence(
        ...     db=db_session,
        ...     query_embedding=query_embedding,
        ...     top_k=10,
        ...     min_similarity=0.5
        ... )
        >>> for result in results:
        ...     print(f"{result.similarity:.3f}: {result.content[:100]}")
    """

    def __init__(self, embedding_dimension: int = 1536) -> None:
        """Initialize the vector search service.

        Args:
            embedding_dimension: Dimension of embeddings (384 or 1536, default: 1536)
        """
        if embedding_dimension not in [384, 1536]:
            raise ValueError(f"Unsupported embedding dimension: {embedding_dimension}")
        self.embedding_dimension = embedding_dimension
        logger.info(f"VectorSearchService initialized with {embedding_dimension}-dim embeddings")

    def search_similar_evidence(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
        tenant_id: str = "default",
        source_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search for evidence similar to a query embedding.

        Uses pgvector's cosine distance operator for similarity search.
        Results are filtered by tenant_id for multi-tenancy support.

        Args:
            db: SQLAlchemy database session
            query_embedding: Query vector (384 or 1536-dimensional list of floats)
            top_k: Maximum number of results to return (default: 10)
            min_similarity: Minimum similarity threshold [0, 1] (default: 0.0)
            tenant_id: Tenant identifier for isolation (default: 'default')
            source_filter: Optional source URL filter (exact match)

        Returns:
            List of SearchResult objects ordered by similarity (highest first)

        Raises:
            ValueError: If query_embedding dimension doesn't match expected dimension
            RuntimeError: If database query fails

        Performance:
            - Typical query time: 20-80ms for 10k vectors
            - Uses IVFFlat index with lists=100 parameter
            - Set ivfflat.probes for accuracy/speed tradeoff

        Example:
            >>> results = service.search_similar_evidence(
            ...     db=session,
            ...     query_embedding=[0.1] * 1536,
            ...     top_k=5,
            ...     min_similarity=0.7
            ... )
        """
        # Validate embedding dimension
        if len(query_embedding) != self.embedding_dimension:
            raise ValueError(
                f"Query embedding must be {self.embedding_dimension}-dimensional, "
                f"got {len(query_embedding)}"
            )

        # Convert similarity threshold to distance threshold
        # Cosine distance = 1 - cosine similarity
        # So: similarity >= min_similarity means distance <= max_distance
        max_distance = 1.0 - min_similarity

        # Build the query
        # Note: pgvector's <-> operator returns cosine distance (0 = identical, 2 = opposite)
        # We convert to similarity score with: similarity = 1 - distance
        # Format embedding as PostgreSQL array literal
        embedding_array = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql_query = f"""
        SELECT
            e.id,
            e.content,
            e.source_url,
            1 - (emb.embedding <-> '{embedding_array}'::vector) AS similarity
        FROM evidence e
        JOIN embeddings emb ON e.id = emb.entity_id
        WHERE emb.entity_type = 'evidence'
            AND emb.tenant_id = %(tenant_id)s
            AND (emb.embedding <-> '{embedding_array}'::vector) <= %(max_distance)s
        """

        # Add optional source filter
        params = {
            "tenant_id": tenant_id,
            "max_distance": max_distance,
            "top_k": top_k,
        }

        if source_filter is not None:
            sql_query += "    AND e.source_url = %(source_filter)s\n"
            params["source_filter"] = source_filter

        # Order by distance (ascending = most similar first) and limit
        sql_query += f"""
        ORDER BY emb.embedding <-> '{embedding_array}'::vector ASC
        LIMIT %(top_k)s
        """

        try:
            # Execute raw SQL with psycopg cursor (bypass SQLAlchemy text() to avoid escaping)
            with db.connection().connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()

            # Convert to SearchResult objects
            search_results = [
                SearchResult(
                    evidence_id=row[0],
                    content=row[1],
                    source_url=row[2],
                    similarity=float(row[3]),
                )
                for row in rows
            ]

            logger.info(
                f"Vector search returned {len(search_results)} results "
                f"(top_k={top_k}, min_similarity={min_similarity:.2f}, tenant={tenant_id})"
            )

            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise RuntimeError(f"Vector search query failed: {e}") from e

    def search_similar_evidence_batch(
        self,
        db: Session,
        query_embeddings: list[list[float]],
        top_k: int = 10,
        min_similarity: float = 0.0,
        tenant_id: str = "default",
    ) -> list[list[SearchResult]]:
        """Search for evidence similar to multiple query embeddings.

        Performs multiple similarity searches in sequence. For better performance
        with large batches, consider parallelizing at the application layer.

        Args:
            db: SQLAlchemy database session
            query_embeddings: List of query vectors (each matching embedding_dimension)
            top_k: Maximum results per query (default: 10)
            min_similarity: Minimum similarity threshold (default: 0.0)
            tenant_id: Tenant identifier (default: 'default')

        Returns:
            List of result lists, one per query embedding

        Raises:
            ValueError: If any query_embedding is invalid
            RuntimeError: If database queries fail

        Example:
            >>> embeddings = [[0.1] * 1536, [0.2] * 1536]
            >>> batch_results = service.search_similar_evidence_batch(
            ...     db=session,
            ...     query_embeddings=embeddings,
            ...     top_k=5
            ... )
            >>> for i, results in enumerate(batch_results):
            ...     print(f"Query {i}: {len(results)} results")
        """
        batch_results = []

        for i, query_embedding in enumerate(query_embeddings):
            try:
                results = self.search_similar_evidence(
                    db=db,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    min_similarity=min_similarity,
                    tenant_id=tenant_id,
                )
                batch_results.append(results)
            except Exception as e:
                logger.error(f"Batch search failed for query {i}: {e}")
                # Return empty results for failed queries
                batch_results.append([])

        logger.info(
            f"Batch vector search completed: {len(query_embeddings)} queries, "
            f"total results: {sum(len(r) for r in batch_results)}"
        )

        return batch_results

    def get_embedding_stats(
        self,
        db: Session,
        entity_type: Literal["evidence", "claim"] = "evidence",
        tenant_id: str = "default",
    ) -> dict:
        """Get statistics about stored embeddings.

        Useful for monitoring and debugging.

        Args:
            db: SQLAlchemy database session
            entity_type: Type of entity to get stats for (default: 'evidence')
            tenant_id: Tenant identifier (default: 'default')

        Returns:
            Dictionary with statistics:
                - total_embeddings: Total count of embeddings
                - entity_type: Entity type queried
                - tenant_id: Tenant identifier
                - has_null_embeddings: Whether any embeddings are NULL

        Example:
            >>> stats = service.get_embedding_stats(session)
            >>> print(f"Total embeddings: {stats['total_embeddings']}")
        """
        sql_query = """
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN embedding IS NULL THEN 1 END) as null_count
        FROM embeddings
        WHERE entity_type = :entity_type AND tenant_id = :tenant_id
        """

        try:
            result = db.execute(
                text(sql_query), {"entity_type": entity_type, "tenant_id": tenant_id}
            )
            row = result.fetchone()

            stats = {
                "total_embeddings": row[0],
                "entity_type": entity_type,
                "tenant_id": tenant_id,
                "has_null_embeddings": row[1] > 0,
                "null_embedding_count": row[1],
            }

            logger.info(f"Embedding stats for {entity_type} in tenant '{tenant_id}': {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {
                "total_embeddings": 0,
                "entity_type": entity_type,
                "tenant_id": tenant_id,
                "has_null_embeddings": False,
                "null_embedding_count": 0,
                "error": str(e),
            }
