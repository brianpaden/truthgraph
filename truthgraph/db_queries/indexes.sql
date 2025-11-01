-- Database Query Optimization: Index Definitions
-- Feature 2.6: Database Query Optimization
-- Created: 2025-11-01
--
-- This file contains optimized index definitions for:
-- 1. Evidence retrieval queries
-- 2. Verdict storage operations
-- 3. NLI result lookups
-- 4. Vector search optimization
--
-- Performance targets:
-- - 30%+ latency reduction
-- - No N+1 queries
-- - Efficient join operations
-- - Fast batch operations

-- ============================================================================
-- EVIDENCE TABLE INDEXES
-- ============================================================================

-- Primary key index (automatically created)
-- CREATE UNIQUE INDEX evidence_pkey ON evidence(id);

-- Index for source_url filtering (used in retrieval queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_source_url
ON evidence(source_url)
WHERE source_url IS NOT NULL;

-- Index for source_type filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_source_type
ON evidence(source_type)
WHERE source_type IS NOT NULL;

-- Composite index for credibility-based sorting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_credibility_created
ON evidence(credibility_score DESC NULLS LAST, created_at DESC)
WHERE credibility_score IS NOT NULL;

-- Index for recent evidence queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_created_at
ON evidence(created_at DESC);

-- Full-text search index for keyword search (if needed)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_content_fts
-- ON evidence USING gin(to_tsvector('english', content));

-- ============================================================================
-- EMBEDDINGS TABLE INDEXES
-- ============================================================================

-- Composite unique index on entity (automatically created by migration)
-- CREATE UNIQUE INDEX idx_embeddings_entity_unique ON embeddings(entity_type, entity_id);

-- Tenant isolation index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_tenant_id
ON embeddings(tenant_id);

-- Composite index for tenant + entity type queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_tenant_entity_type
ON embeddings(tenant_id, entity_type);

-- IVFFlat vector index (created by migration, but including for reference)
-- Optimal configuration from Feature 2.3:
-- - lists = 50 for 10K corpus
-- - probes = 10 for balanced accuracy/speed
--
-- To rebuild with optimal parameters:
-- DROP INDEX IF EXISTS idx_embeddings_vector_cosine;
-- CREATE INDEX idx_embeddings_vector_cosine
-- ON embeddings
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 50);
--
-- Set probes at session level:
-- SET ivfflat.probes = 10;

-- Index for updated_at (monitoring and cleanup)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_updated_at
ON embeddings(updated_at DESC);

-- ============================================================================
-- NLI_RESULTS TABLE INDEXES
-- ============================================================================

-- Index on claim_id (high cardinality, frequent lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_claim_id
ON nli_results(claim_id);

-- Index on evidence_id (for reverse lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_evidence_id
ON nli_results(evidence_id);

-- Composite index for claim-evidence pair lookups (prevents N+1 queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_claim_evidence
ON nli_results(claim_id, evidence_id);

-- Index on label for filtering by NLI prediction type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_label
ON nli_results(label);

-- Composite index for claim + confidence (sorted queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_claim_confidence
ON nli_results(claim_id, confidence DESC);

-- Composite index for claim + label (filtered aggregations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_claim_label
ON nli_results(claim_id, label);

-- Index on created_at for temporal queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nli_results_created_at
ON nli_results(created_at DESC);

-- ============================================================================
-- VERIFICATION_RESULTS TABLE INDEXES
-- ============================================================================

-- Index on claim_id (one-to-one or one-to-many relationship)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_claim_id
ON verification_results(claim_id);

-- Index on verdict for filtering by result type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_verdict
ON verification_results(verdict);

-- Index on confidence for ranking/filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_confidence
ON verification_results(confidence DESC);

-- Index on created_at for temporal queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_created_at
ON verification_results(created_at DESC);

-- Composite index for claim + created_at (latest result per claim)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_claim_created
ON verification_results(claim_id, created_at DESC);

-- Composite index for verdict + confidence (filtered ranking)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_verdict_confidence
ON verification_results(verdict, confidence DESC);

-- GIN index on nli_result_ids array for containment queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_nli_ids
ON verification_results USING gin(nli_result_ids);

-- Index on retrieval_method for performance analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_results_retrieval_method
ON verification_results(retrieval_method)
WHERE retrieval_method IS NOT NULL;

-- ============================================================================
-- CLAIMS TABLE INDEXES
-- ============================================================================

-- Assuming claims table exists with these common patterns:

-- Index on created_at/submitted_at for temporal queries
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_claims_submitted_at
-- ON claims(submitted_at DESC);

-- Index on text for exact match lookups (if needed)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_claims_text_hash
-- ON claims(md5(text));

-- Full-text search index on claim text
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_claims_text_fts
-- ON claims USING gin(to_tsvector('english', text));

-- ============================================================================
-- MAINTENANCE AND OPTIMIZATION
-- ============================================================================

-- Update table statistics for query planner
-- Run after bulk inserts or major data changes
-- ANALYZE evidence;
-- ANALYZE embeddings;
-- ANALYZE nli_results;
-- ANALYZE verification_results;

-- Check index usage statistics
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY idx_scan DESC;

-- Find unused indexes (consider dropping)
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as size
-- FROM pg_stat_user_indexes
-- WHERE idx_scan = 0
--     AND indexrelname NOT LIKE '%pkey'
--     AND schemaname = 'public'
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- PERFORMANCE MONITORING
-- ============================================================================

-- Monitor sequential scans vs index scans
-- SELECT
--     relname as table_name,
--     seq_scan,
--     seq_tup_read,
--     idx_scan,
--     idx_tup_fetch,
--     CASE
--         WHEN seq_scan + idx_scan > 0
--         THEN round(100.0 * idx_scan / (seq_scan + idx_scan), 2)
--         ELSE 0
--     END as index_scan_ratio
-- FROM pg_stat_user_tables
-- WHERE schemaname = 'public'
-- ORDER BY seq_scan DESC;

-- Check for missing indexes (high sequential scans on large tables)
-- SELECT
--     relname as table_name,
--     seq_scan,
--     seq_tup_read,
--     n_live_tup as live_rows,
--     round(seq_tup_read::numeric / NULLIF(seq_scan, 0), 2) as avg_rows_per_scan
-- FROM pg_stat_user_tables
-- WHERE schemaname = 'public'
--     AND seq_scan > 0
--     AND n_live_tup > 1000
-- ORDER BY seq_scan * n_live_tup DESC;

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. CONCURRENTLY: All indexes use CREATE INDEX CONCURRENTLY to avoid locking
--    the table during index creation. This is safe for production.
--
-- 2. IF NOT EXISTS: Prevents errors if indexes already exist from migrations.
--
-- 3. Composite Indexes: Order matters! Most selective columns should come first.
--    For (claim_id, created_at), queries filtering by claim_id can use the index.
--
-- 4. Partial Indexes: WHERE clauses create smaller indexes for specific queries.
--    Example: idx_evidence_source_url only indexes non-NULL source_urls.
--
-- 5. Index Maintenance: Run VACUUM ANALYZE after bulk operations to update
--    statistics and help the query planner make optimal decisions.
--
-- 6. Index Size: Monitor index sizes with:
--    SELECT pg_size_pretty(pg_indexes_size('table_name'));
--
-- 7. Vector Index Tuning: See Feature 2.3 report for optimal IVFFlat parameters:
--    - lists = 50 for 10K corpus (adjust as corpus grows)
--    - probes = 10 for balanced performance (5 for speed, 25 for accuracy)
