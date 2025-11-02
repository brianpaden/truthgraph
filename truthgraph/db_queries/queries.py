"""Optimized database queries for evidence retrieval and verdict storage.

This module provides highly optimized database query implementations that:
1. Eliminate N+1 query patterns through eager loading and joins
2. Implement batch operations for bulk inserts and updates
3. Use proper indexing for fast lookups
4. Reduce database round-trips with combined queries
5. Leverage PostgreSQL-specific optimizations

Performance targets:
- 30%+ latency reduction vs naive implementations
- No N+1 queries
- Efficient use of indexes
- Batch operations for all bulk data access

Usage:
    queries = OptimizedQueries()

    # Batch evidence retrieval
    evidence_list = queries.batch_get_evidence_by_ids(session, evidence_ids)

    # Optimized verdict storage with related data
    result_id = queries.create_verification_result_with_nli(
        session, claim_id, verdict_data, nli_results
    )
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OptimizedQueries:
    """Optimized database queries for high-performance data access.

    This class provides methods that are optimized for:
    - Minimal database round-trips
    - Proper use of indexes
    - Batch operations
    - Elimination of N+1 queries
    - Efficient joins
    """

    # Evidence Retrieval Queries

    def batch_get_evidence_by_ids(
        self,
        session: Session,
        evidence_ids: List[UUID],
        include_embeddings: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve multiple evidence items in a single query.

        Eliminates N+1 queries by fetching all evidence in one batch.
        Optionally includes embeddings via join.

        Args:
            session: Database session
            evidence_ids: List of evidence UUIDs to retrieve
            include_embeddings: Whether to join and include embeddings

        Returns:
            List of evidence dictionaries with all fields

        Performance:
            - Single query vs N queries (eliminates N+1)
            - Uses IN clause with index on evidence.id
            - Optional LEFT JOIN for embeddings (single query)
            - Expected: <10ms for 100 items
        """
        if not evidence_ids:
            return []

        try:
            if include_embeddings:
                # Use LEFT JOIN to include embeddings in single query
                query = text("""
                    SELECT
                        e.id,
                        e.content,
                        e.source_url,
                        e.source_type,
                        e.credibility_score,
                        e.publication_date,
                        e.created_at,
                        emb.embedding,
                        emb.model_name,
                        emb.id as embedding_id
                    FROM evidence e
                    LEFT JOIN embeddings emb
                        ON e.id = emb.entity_id
                        AND emb.entity_type = 'evidence'
                    WHERE e.id = ANY(:evidence_ids)
                    ORDER BY e.created_at DESC
                """)
                result = session.execute(
                    query, {"evidence_ids": [str(eid) for eid in evidence_ids]}
                )
            else:
                # Simple evidence-only query
                query = text("""
                    SELECT
                        id,
                        content,
                        source_url,
                        source_type,
                        credibility_score,
                        publication_date,
                        created_at
                    FROM evidence
                    WHERE id = ANY(:evidence_ids)
                    ORDER BY created_at DESC
                """)
                result = session.execute(
                    query, {"evidence_ids": [str(eid) for eid in evidence_ids]}
                )

            rows = result.fetchall()

            evidence_list = []
            for row in rows:
                evidence = {
                    "id": row[0],
                    "content": row[1],
                    "source_url": row[2],
                    "source_type": row[3] if len(row) > 3 else None,
                    "credibility_score": row[4] if len(row) > 4 else None,
                    "publication_date": row[5] if len(row) > 5 else None,
                    "created_at": row[6] if len(row) > 6 else None,
                }

                if include_embeddings and len(row) > 7:
                    evidence["embedding"] = {
                        "vector": row[7],
                        "model_name": row[8],
                        "embedding_id": row[9],
                    }

                evidence_list.append(evidence)

            logger.info(
                f"Batch retrieved {len(evidence_list)} evidence items "
                f"(include_embeddings={include_embeddings})"
            )
            return evidence_list

        except Exception as e:
            logger.error(f"Batch evidence retrieval failed: {e}", exc_info=True)
            raise

    def get_evidence_with_similarity_scores(
        self,
        session: Session,
        claim_id: UUID,
        query_embedding: List[float],
        top_k: int = 20,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Retrieve evidence with pre-computed similarity scores in single query.

        Combines evidence retrieval and similarity scoring into one query
        to minimize round-trips.

        Args:
            session: Database session
            claim_id: Claim being verified
            query_embedding: Query vector for similarity
            top_k: Maximum number of results
            tenant_id: Tenant identifier

        Returns:
            List of evidence with similarity scores

        Performance:
            - Single query combines JOIN + vector search
            - Uses IVFFlat index for vector similarity
            - Expected: <50ms for 10K corpus
        """
        try:
            embedding_array = "[" + ",".join(str(x) for x in query_embedding) + "]"

            query = text("""
                SELECT
                    e.id,
                    e.content,
                    e.source_url,
                    e.source_type,
                    e.credibility_score,
                    1 - (emb.embedding <-> :embedding_vec::vector) AS similarity,
                    emb.model_name
                FROM evidence e
                JOIN embeddings emb
                    ON e.id = emb.entity_id
                    AND emb.entity_type = 'evidence'
                WHERE emb.tenant_id = :tenant_id
                ORDER BY emb.embedding <-> :embedding_vec::vector ASC
                LIMIT :top_k
            """)

            result = session.execute(
                query,
                {
                    "embedding_vec": embedding_array,
                    "tenant_id": tenant_id,
                    "top_k": top_k,
                },
            )

            rows = result.fetchall()

            evidence_list = []
            for row in rows:
                evidence_list.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "source_url": row[2],
                        "source_type": row[3],
                        "credibility_score": row[4],
                        "similarity": float(row[5]),
                        "model_name": row[6],
                    }
                )

            logger.info(
                f"Retrieved {len(evidence_list)} evidence items with similarity scores "
                f"for claim {claim_id}"
            )
            return evidence_list

        except Exception as e:
            logger.error(f"Evidence retrieval with similarity failed: {e}", exc_info=True)
            raise

    # NLI Result Queries

    def batch_create_nli_results(
        self,
        session: Session,
        nli_results: List[Dict[str, Any]],
    ) -> List[UUID]:
        """Create multiple NLI results in a single batch insert.

        Uses PostgreSQL's efficient multi-row INSERT with RETURNING
        to get all IDs in one query.

        Args:
            session: Database session
            nli_results: List of NLI result dictionaries

        Returns:
            List of created NLI result IDs

        Performance:
            - Single INSERT vs N INSERTs
            - Expected: <20ms for 100 rows
            - ~10-50x faster than individual inserts
        """
        if not nli_results:
            return []

        try:
            # Build VALUES clause for batch insert
            values_clauses = []
            params: Dict[str, Any] = {}

            for i, nli in enumerate(nli_results):
                values_clauses.append(f"""(
                    :claim_id_{i}::uuid,
                    :evidence_id_{i}::uuid,
                    :label_{i},
                    :confidence_{i},
                    :entailment_score_{i},
                    :contradiction_score_{i},
                    :neutral_score_{i},
                    :model_name_{i},
                    :model_version_{i},
                    :premise_text_{i},
                    :hypothesis_text_{i}
                )""")

                params[f"claim_id_{i}"] = str(nli["claim_id"])
                params[f"evidence_id_{i}"] = str(nli["evidence_id"])
                params[f"label_{i}"] = nli["label"]
                params[f"confidence_{i}"] = nli["confidence"]
                params[f"entailment_score_{i}"] = nli["entailment_score"]
                params[f"contradiction_score_{i}"] = nli["contradiction_score"]
                params[f"neutral_score_{i}"] = nli["neutral_score"]
                params[f"model_name_{i}"] = nli.get("model_name", "microsoft/deberta-v3-base")
                params[f"model_version_{i}"] = nli.get("model_version")
                params[f"premise_text_{i}"] = nli["premise_text"]
                params[f"hypothesis_text_{i}"] = nli["hypothesis_text"]

            query = text(f"""
                INSERT INTO nli_results (
                    claim_id,
                    evidence_id,
                    label,
                    confidence,
                    entailment_score,
                    contradiction_score,
                    neutral_score,
                    model_name,
                    model_version,
                    premise_text,
                    hypothesis_text
                ) VALUES {", ".join(values_clauses)}
                RETURNING id
            """)

            result = session.execute(query, params)
            ids = [row[0] for row in result.fetchall()]

            session.commit()

            logger.info(f"Batch created {len(ids)} NLI results")
            return ids

        except Exception as e:
            session.rollback()
            logger.error(f"Batch NLI result creation failed: {e}", exc_info=True)
            raise

    def get_nli_results_for_claim(
        self,
        session: Session,
        claim_id: UUID,
        include_evidence: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve all NLI results for a claim.

        Optionally includes evidence content via JOIN to avoid N+1 queries.

        Args:
            session: Database session
            claim_id: Claim UUID
            include_evidence: Whether to include evidence text

        Returns:
            List of NLI results with optional evidence

        Performance:
            - Single query with optional JOIN
            - Uses index on nli_results.claim_id
            - Expected: <10ms for 100 results
        """
        try:
            if include_evidence:
                query = text("""
                    SELECT
                        nli.id,
                        nli.claim_id,
                        nli.evidence_id,
                        nli.label,
                        nli.confidence,
                        nli.entailment_score,
                        nli.contradiction_score,
                        nli.neutral_score,
                        nli.model_name,
                        nli.created_at,
                        e.content as evidence_content,
                        e.source_url as evidence_source
                    FROM nli_results nli
                    LEFT JOIN evidence e ON nli.evidence_id = e.id
                    WHERE nli.claim_id = :claim_id
                    ORDER BY nli.confidence DESC
                """)
            else:
                query = text("""
                    SELECT
                        id,
                        claim_id,
                        evidence_id,
                        label,
                        confidence,
                        entailment_score,
                        contradiction_score,
                        neutral_score,
                        model_name,
                        created_at
                    FROM nli_results
                    WHERE claim_id = :claim_id
                    ORDER BY confidence DESC
                """)

            result = session.execute(query, {"claim_id": str(claim_id)})
            rows = result.fetchall()

            nli_list = []
            for row in rows:
                nli_result = {
                    "id": row[0],
                    "claim_id": row[1],
                    "evidence_id": row[2],
                    "label": row[3],
                    "confidence": float(row[4]),
                    "entailment_score": float(row[5]),
                    "contradiction_score": float(row[6]),
                    "neutral_score": float(row[7]),
                    "model_name": row[8],
                    "created_at": row[9],
                }

                if include_evidence and len(row) > 10:
                    nli_result["evidence"] = {
                        "content": row[10],
                        "source_url": row[11],
                    }

                nli_list.append(nli_result)

            logger.info(
                f"Retrieved {len(nli_list)} NLI results for claim {claim_id} "
                f"(include_evidence={include_evidence})"
            )
            return nli_list

        except Exception as e:
            logger.error(f"NLI results retrieval failed: {e}", exc_info=True)
            raise

    # Verification Result Queries

    def create_verification_result_with_nli(
        self,
        session: Session,
        claim_id: UUID,
        verdict: str,
        confidence: float,
        scores: Dict[str, float],
        evidence_counts: Dict[str, int],
        nli_result_ids: List[UUID],
        reasoning: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Create verification result and link to NLI results in single transaction.

        Efficiently stores verdict with all related data in one operation.

        Args:
            session: Database session
            claim_id: Claim UUID
            verdict: Final verdict (SUPPORTED, REFUTED, INSUFFICIENT)
            confidence: Overall confidence score
            scores: Dictionary with support_score, refute_score, neutral_score
            evidence_counts: Dictionary with supporting/refuting/neutral counts
            nli_result_ids: List of NLI result UUIDs
            reasoning: Optional explanation
            metadata: Optional metadata (pipeline_version, retrieval_method, etc.)

        Returns:
            Created verification result ID

        Performance:
            - Single INSERT operation
            - Transaction ensures consistency
            - Expected: <5ms
        """
        try:
            meta = metadata or {}

            query = text("""
                INSERT INTO verification_results (
                    claim_id,
                    verdict,
                    confidence,
                    support_score,
                    refute_score,
                    neutral_score,
                    evidence_count,
                    supporting_evidence_count,
                    refuting_evidence_count,
                    neutral_evidence_count,
                    reasoning,
                    nli_result_ids,
                    pipeline_version,
                    retrieval_method
                ) VALUES (
                    :claim_id::uuid,
                    :verdict,
                    :confidence,
                    :support_score,
                    :refute_score,
                    :neutral_score,
                    :evidence_count,
                    :supporting_evidence_count,
                    :refuting_evidence_count,
                    :neutral_evidence_count,
                    :reasoning,
                    :nli_result_ids::uuid[],
                    :pipeline_version,
                    :retrieval_method
                )
                RETURNING id
            """)

            result = session.execute(
                query,
                {
                    "claim_id": str(claim_id),
                    "verdict": verdict,
                    "confidence": confidence,
                    "support_score": scores.get("support_score", 0.0),
                    "refute_score": scores.get("refute_score", 0.0),
                    "neutral_score": scores.get("neutral_score", 0.0),
                    "evidence_count": len(nli_result_ids),
                    "supporting_evidence_count": evidence_counts.get("supporting", 0),
                    "refuting_evidence_count": evidence_counts.get("refuting", 0),
                    "neutral_evidence_count": evidence_counts.get("neutral", 0),
                    "reasoning": reasoning,
                    "nli_result_ids": [str(nid) for nid in nli_result_ids],
                    "pipeline_version": meta.get("pipeline_version"),
                    "retrieval_method": meta.get("retrieval_method"),
                },
            )

            result_id = result.fetchone()[0]
            session.commit()

            logger.info(
                f"Created verification result {result_id} for claim {claim_id} "
                f"with {len(nli_result_ids)} NLI results"
            )
            return result_id

        except Exception as e:
            session.rollback()
            logger.error(f"Verification result creation failed: {e}", exc_info=True)
            raise

    def get_verification_result_with_details(
        self,
        session: Session,
        claim_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve verification result with all related data in single query.

        Uses JOINs to fetch verification result, claim, and NLI results
        in one efficient query.

        Args:
            session: Database session
            claim_id: Claim UUID

        Returns:
            Complete verification result with all details, or None if not found

        Performance:
            - Single query with multiple JOINs
            - Uses indexes on all JOIN columns
            - Expected: <15ms for complete result
        """
        try:
            query = text("""
                SELECT
                    vr.id,
                    vr.claim_id,
                    vr.verdict,
                    vr.confidence,
                    vr.support_score,
                    vr.refute_score,
                    vr.neutral_score,
                    vr.evidence_count,
                    vr.supporting_evidence_count,
                    vr.refuting_evidence_count,
                    vr.neutral_evidence_count,
                    vr.reasoning,
                    vr.nli_result_ids,
                    vr.pipeline_version,
                    vr.retrieval_method,
                    vr.created_at,
                    vr.updated_at,
                    c.text as claim_text,
                    c.source_url as claim_source
                FROM verification_results vr
                JOIN claims c ON vr.claim_id = c.id
                WHERE vr.claim_id = :claim_id
                ORDER BY vr.created_at DESC
                LIMIT 1
            """)

            result = session.execute(query, {"claim_id": str(claim_id)})
            row = result.fetchone()

            if not row:
                return None

            verification_result = {
                "id": row[0],
                "claim_id": row[1],
                "verdict": row[2],
                "confidence": float(row[3]),
                "scores": {
                    "support": float(row[4]),
                    "refute": float(row[5]),
                    "neutral": float(row[6]),
                },
                "evidence_counts": {
                    "total": row[7],
                    "supporting": row[8],
                    "refuting": row[9],
                    "neutral": row[10],
                },
                "reasoning": row[11],
                "nli_result_ids": row[12],
                "pipeline_version": row[13],
                "retrieval_method": row[14],
                "created_at": row[15],
                "updated_at": row[16],
                "claim": {
                    "text": row[17],
                    "source_url": row[18],
                },
            }

            logger.info(f"Retrieved verification result for claim {claim_id}")
            return verification_result

        except Exception as e:
            logger.error(f"Verification result retrieval failed: {e}", exc_info=True)
            raise

    # Batch Embedding Operations

    def batch_create_embeddings(
        self,
        session: Session,
        embeddings: List[Dict[str, Any]],
    ) -> List[UUID]:
        """Create multiple embeddings in a single batch insert.

        Highly efficient bulk embedding storage using PostgreSQL's
        multi-row INSERT with vector type support.

        Args:
            session: Database session
            embeddings: List of embedding dictionaries with:
                - entity_type: 'evidence' or 'claim'
                - entity_id: UUID
                - embedding: List of floats
                - model_name: Model identifier
                - tenant_id: Tenant identifier

        Returns:
            List of created embedding IDs

        Performance:
            - Single INSERT for all embeddings
            - Expected: <50ms for 100 embeddings
            - ~20-100x faster than individual inserts
        """
        if not embeddings:
            return []

        try:
            values_clauses = []
            params: Dict[str, Any] = {}

            for i, emb in enumerate(embeddings):
                embedding_vec = "[" + ",".join(str(x) for x in emb["embedding"]) + "]"

                values_clauses.append(f"""(
                    :entity_type_{i},
                    :entity_id_{i}::uuid,
                    '{embedding_vec}'::vector,
                    :model_name_{i},
                    :model_version_{i},
                    :tenant_id_{i}
                )""")

                params[f"entity_type_{i}"] = emb["entity_type"]
                params[f"entity_id_{i}"] = str(emb["entity_id"])
                params[f"model_name_{i}"] = emb.get("model_name", "all-MiniLM-L6-v2")
                params[f"model_version_{i}"] = emb.get("model_version")
                params[f"tenant_id_{i}"] = emb.get("tenant_id", "default")

            query = text(f"""
                INSERT INTO embeddings (
                    entity_type,
                    entity_id,
                    embedding,
                    model_name,
                    model_version,
                    tenant_id
                ) VALUES {", ".join(values_clauses)}
                ON CONFLICT (entity_type, entity_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    model_version = EXCLUDED.model_version,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """)

            result = session.execute(query, params)
            ids = [row[0] for row in result.fetchall()]

            session.commit()

            logger.info(f"Batch created/updated {len(ids)} embeddings")
            return ids

        except Exception as e:
            session.rollback()
            logger.error(f"Batch embedding creation failed: {e}", exc_info=True)
            raise

    # Analytics and Monitoring Queries

    def get_query_performance_stats(
        self,
        session: Session,
        table_name: str,
    ) -> Dict[str, Any]:
        """Get query performance statistics for a table.

        Uses PostgreSQL system catalogs to analyze query performance.

        Args:
            session: Database session
            table_name: Table to analyze

        Returns:
            Dictionary with performance statistics
        """
        try:
            query = text("""
                SELECT
                    relname as table_name,
                    seq_scan as sequential_scans,
                    seq_tup_read as rows_read_sequentially,
                    idx_scan as index_scans,
                    idx_tup_fetch as rows_fetched_via_index,
                    n_tup_ins as rows_inserted,
                    n_tup_upd as rows_updated,
                    n_tup_del as rows_deleted,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                WHERE relname = :table_name
            """)

            result = session.execute(query, {"table_name": table_name})
            row = result.fetchone()

            if not row:
                return {"error": f"Table {table_name} not found"}

            stats = {
                "table_name": row[0],
                "sequential_scans": row[1],
                "rows_read_sequentially": row[2],
                "index_scans": row[3],
                "rows_fetched_via_index": row[4],
                "rows_inserted": row[5],
                "rows_updated": row[6],
                "rows_deleted": row[7],
                "live_rows": row[8],
                "dead_rows": row[9],
                "index_scan_ratio": (row[3] / (row[1] + row[3]) if (row[1] + row[3]) > 0 else 0.0),
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get query performance stats: {e}")
            return {"error": str(e)}
