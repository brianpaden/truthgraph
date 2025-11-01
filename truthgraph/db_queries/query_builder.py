"""Query optimization utilities and query builder helpers.

This module provides utilities for:
1. Dynamic query construction with proper parameter binding
2. Query performance analysis with EXPLAIN ANALYZE
3. Index usage recommendations
4. Connection pool management helpers
5. Query caching strategies

Usage:
    builder = QueryBuilder(session)

    # Analyze query performance
    analysis = builder.explain_analyze(query_text, params)

    # Build optimized queries
    query = builder.build_similarity_search(
        embedding=query_vec,
        filters={"tenant_id": "default"},
        top_k=20
    )
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Utility class for building and optimizing database queries.

    Provides methods for:
    - Query performance analysis
    - Dynamic query construction
    - Index recommendations
    - Query timing and profiling
    """

    def __init__(self, session: Session) -> None:
        """Initialize query builder.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def explain_analyze(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        format_type: str = "text",
    ) -> Dict[str, Any]:
        """Execute EXPLAIN ANALYZE to profile query performance.

        Args:
            query: SQL query to analyze
            params: Query parameters
            format_type: Output format (text, json, yaml, xml)

        Returns:
            Dictionary with query plan and performance metrics

        Example:
            >>> builder = QueryBuilder(session)
            >>> analysis = builder.explain_analyze(
            ...     "SELECT * FROM evidence WHERE id = :id",
            ...     {"id": evidence_id}
            ... )
            >>> print(f"Execution time: {analysis['execution_time_ms']}ms")
        """
        try:
            params = params or {}

            # Wrap query with EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT {format_type.upper()}) {query}"

            start_time = time.time()
            result = self.session.execute(text(explain_query), params)
            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            rows = result.fetchall()

            if format_type == "json":
                # PostgreSQL returns JSON as a single row
                import json
                plan_data = json.loads(rows[0][0])
            else:
                # Text format: concatenate all rows
                plan_data = "\n".join(row[0] for row in rows)

            analysis = {
                "query": query,
                "execution_time_ms": execution_time,
                "plan": plan_data,
                "format": format_type,
            }

            # Extract key metrics if JSON format
            if format_type == "json" and isinstance(plan_data, list):
                plan = plan_data[0].get("Plan", {})
                analysis["planning_time_ms"] = plan_data[0].get("Planning Time", 0)
                analysis["actual_execution_time_ms"] = plan_data[0].get("Execution Time", 0)
                analysis["total_cost"] = plan.get("Total Cost", 0)
                analysis["actual_rows"] = plan.get("Actual Rows", 0)
                analysis["node_type"] = plan.get("Node Type", "Unknown")

            logger.info(f"Query analysis completed in {execution_time:.2f}ms")
            return analysis

        except Exception as e:
            logger.error(f"Query analysis failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "execution_time_ms": 0,
            }

    def analyze_index_usage(
        self,
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """Analyze index usage for a table.

        Returns statistics about which indexes are being used
        and which might be missing.

        Args:
            table_name: Name of table to analyze

        Returns:
            List of index statistics

        Example:
            >>> indices = builder.analyze_index_usage("evidence")
            >>> for idx in indices:
            ...     print(f"{idx['index_name']}: {idx['scans']} scans")
        """
        try:
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                WHERE tablename = :table_name
                ORDER BY idx_scan DESC
            """)

            result = self.session.execute(query, {"table_name": table_name})
            rows = result.fetchall()

            indices = []
            for row in rows:
                indices.append({
                    "schema": row[0],
                    "table": row[1],
                    "index_name": row[2],
                    "scans": row[3],
                    "tuples_read": row[4],
                    "tuples_fetched": row[5],
                    "size": row[6],
                    "is_used": row[3] > 0,
                })

            logger.info(f"Analyzed {len(indices)} indices for table {table_name}")
            return indices

        except Exception as e:
            logger.error(f"Index analysis failed: {e}", exc_info=True)
            return []

    def get_missing_indexes_recommendations(
        self,
        table_name: str,
    ) -> List[str]:
        """Get recommendations for missing indexes.

        Analyzes query patterns and suggests indexes that could improve performance.

        Args:
            table_name: Table to analyze

        Returns:
            List of recommended index creation statements

        Example:
            >>> recommendations = builder.get_missing_indexes_recommendations("nli_results")
            >>> for rec in recommendations:
            ...     print(rec)
        """
        try:
            # Check for sequential scans on large tables
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    n_live_tup
                FROM pg_stat_user_tables
                WHERE tablename = :table_name
            """)

            result = self.session.execute(query, {"table_name": table_name})
            row = result.fetchone()

            if not row:
                return []

            recommendations = []

            seq_scans = row[2] or 0
            idx_scans = row[4] or 0
            live_rows = row[5] or 0

            # If sequential scans dominate and table is large, recommend indexes
            if seq_scans > idx_scans and live_rows > 1000:
                recommendations.append(
                    f"-- High sequential scans detected on {table_name} "
                    f"({seq_scans} seq vs {idx_scans} idx scans)\n"
                    f"-- Consider adding indexes on frequently queried columns"
                )

                # Table-specific recommendations
                if table_name == "nli_results":
                    if not self._index_exists(table_name, "idx_nli_results_claim_evidence"):
                        recommendations.append(
                            "CREATE INDEX CONCURRENTLY idx_nli_results_claim_evidence "
                            "ON nli_results(claim_id, evidence_id);"
                        )

                elif table_name == "embeddings":
                    if not self._index_exists(table_name, "idx_embeddings_tenant_entity"):
                        recommendations.append(
                            "CREATE INDEX CONCURRENTLY idx_embeddings_tenant_entity "
                            "ON embeddings(tenant_id, entity_type, entity_id);"
                        )

                elif table_name == "verification_results":
                    if not self._index_exists(table_name, "idx_verification_results_claim_created"):
                        recommendations.append(
                            "CREATE INDEX CONCURRENTLY idx_verification_results_claim_created "
                            "ON verification_results(claim_id, created_at DESC);"
                        )

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get index recommendations: {e}", exc_info=True)
            return []

    def _index_exists(self, table_name: str, index_name: str) -> bool:
        """Check if an index exists.

        Args:
            table_name: Table name
            index_name: Index name

        Returns:
            True if index exists
        """
        try:
            query = text("""
                SELECT 1
                FROM pg_indexes
                WHERE tablename = :table_name
                AND indexname = :index_name
            """)

            result = self.session.execute(
                query,
                {"table_name": table_name, "index_name": index_name}
            )
            return result.fetchone() is not None

        except Exception:
            return False

    @contextmanager
    def timing(self, operation_name: str):
        """Context manager for timing database operations.

        Args:
            operation_name: Name of operation for logging

        Yields:
            Dictionary that will contain timing results

        Example:
            >>> with builder.timing("evidence_retrieval") as timing_result:
            ...     evidence = queries.batch_get_evidence_by_ids(session, ids)
            >>> print(f"Operation took {timing_result['duration_ms']}ms")
        """
        timing_result = {"operation": operation_name}
        start_time = time.time()

        try:
            yield timing_result
        finally:
            duration = (time.time() - start_time) * 1000
            timing_result["duration_ms"] = duration
            logger.info(f"{operation_name} completed in {duration:.2f}ms")

    def build_similarity_search_query(
        self,
        embedding: List[float],
        entity_type: str = "evidence",
        tenant_id: str = "default",
        top_k: int = 20,
        min_similarity: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Build optimized similarity search query.

        Constructs a parameterized query for vector similarity search
        with optional filters.

        Args:
            embedding: Query embedding vector
            entity_type: Type of entity to search
            tenant_id: Tenant identifier
            top_k: Maximum results
            min_similarity: Minimum similarity threshold
            filters: Additional filters (e.g., source_url)

        Returns:
            Tuple of (query_string, parameters)

        Example:
            >>> query, params = builder.build_similarity_search_query(
            ...     embedding=query_vec,
            ...     filters={"source_url": "https://example.com"}
            ... )
            >>> results = session.execute(text(query), params).fetchall()
        """
        filters = filters or {}
        embedding_array = "[" + ",".join(str(x) for x in embedding) + "]"

        # Base query
        query_parts = ["""
            SELECT
                e.id,
                e.content,
                e.source_url,
                1 - (emb.embedding <-> :embedding_vec::vector) AS similarity
            FROM evidence e
            JOIN embeddings emb
                ON e.id = emb.entity_id
                AND emb.entity_type = :entity_type
            WHERE emb.tenant_id = :tenant_id
        """]

        params: Dict[str, Any] = {
            "embedding_vec": embedding_array,
            "entity_type": entity_type,
            "tenant_id": tenant_id,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }

        # Add similarity filter
        if min_similarity > 0:
            max_distance = 1.0 - min_similarity
            query_parts.append("    AND (emb.embedding <-> :embedding_vec::vector) <= :max_distance")
            params["max_distance"] = max_distance

        # Add additional filters
        for key, value in filters.items():
            if key == "source_url":
                query_parts.append(f"    AND e.source_url = :filter_{key}")
                params[f"filter_{key}"] = value
            elif key == "source_type":
                query_parts.append(f"    AND e.source_type = :filter_{key}")
                params[f"filter_{key}"] = value

        # Add ordering and limit
        query_parts.append("""
            ORDER BY emb.embedding <-> :embedding_vec::vector ASC
            LIMIT :top_k
        """)

        query = "\n".join(query_parts)
        return query, params

    def set_ivfflat_probes(self, probes: int) -> None:
        """Set IVFFlat probes parameter for session.

        Higher probes = more accuracy but slower.
        Recommended: 10-25 for balanced performance.

        Args:
            probes: Number of lists to probe (1-lists value)

        Example:
            >>> builder.set_ivfflat_probes(10)
            >>> # Subsequent vector searches use 10 probes
        """
        try:
            self.session.execute(text(f"SET ivfflat.probes = {probes}"))
            logger.info(f"Set ivfflat.probes to {probes}")
        except Exception as e:
            logger.error(f"Failed to set ivfflat.probes: {e}")

    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns information about database connections and pool usage.

        Returns:
            Dictionary with pool statistics
        """
        try:
            engine = self.session.get_bind()

            # Get pool statistics
            pool = engine.pool

            stats = {
                "pool_size": pool.size(),
                "checked_out_connections": pool.checkedout(),
                "overflow_connections": pool.overflow(),
                "max_overflow": pool._max_overflow,
                "total_connections": pool.size() + pool.overflow(),
            }

            # Get active connections from PostgreSQL
            query = text("""
                SELECT
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)

            result = self.session.execute(query)
            row = result.fetchone()

            if row:
                stats["db_total_connections"] = row[0]
                stats["db_active_connections"] = row[1]
                stats["db_idle_connections"] = row[2]

            return stats

        except Exception as e:
            logger.error(f"Failed to get connection pool stats: {e}")
            return {"error": str(e)}

    def vacuum_analyze_table(self, table_name: str) -> None:
        """Run VACUUM ANALYZE on a table to update statistics.

        Important for query optimizer to make good decisions.
        Run after bulk inserts/updates.

        Args:
            table_name: Table to vacuum analyze

        Example:
            >>> builder.vacuum_analyze_table("embeddings")
        """
        try:
            # VACUUM cannot run inside a transaction
            self.session.commit()
            self.session.connection().connection.set_isolation_level(0)

            query = f"VACUUM ANALYZE {table_name}"
            self.session.execute(text(query))

            logger.info(f"VACUUM ANALYZE completed for {table_name}")

        except Exception as e:
            logger.error(f"VACUUM ANALYZE failed: {e}", exc_info=True)
        finally:
            # Reset isolation level
            try:
                self.session.connection().connection.set_isolation_level(1)
            except Exception:
                pass

    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a table.

        Args:
            table_name: Table to analyze

        Returns:
            Dictionary with table statistics
        """
        try:
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                                   pg_relation_size(schemaname||'.'||tablename)) as indexes_size,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_ratio,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE tablename = :table_name
            """)

            result = self.session.execute(query, {"table_name": table_name})
            row = result.fetchone()

            if not row:
                return {"error": f"Table {table_name} not found"}

            stats = {
                "schema": row[0],
                "table": row[1],
                "total_size": row[2],
                "table_size": row[3],
                "indexes_size": row[4],
                "live_rows": row[5],
                "dead_rows": row[6],
                "dead_ratio_percent": float(row[7]) if row[7] else 0.0,
                "last_vacuum": row[8],
                "last_autovacuum": row[9],
                "last_analyze": row[10],
                "last_autoanalyze": row[11],
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
            return {"error": str(e)}
