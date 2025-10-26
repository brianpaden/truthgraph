# Phase 2 Database Migration Documentation

**Version**: 1.0
**Created**: 2025-10-25
**Migration ID**: `phase2_ml_tables`

## Overview

This document describes the Phase 2 database migration that adds ML-enhanced verification capabilities to TruthGraph v0. The migration introduces three new tables to support:

1. **Vector embeddings** for semantic search
2. **NLI (Natural Language Inference)** results storage
3. **Aggregated verification** results

## Schema Changes

### New Tables

#### 1. `embeddings` Table

Stores vector embeddings for both evidence and claims, enabling semantic similarity search using pgvector.

**Columns**:
- `id` (UUID, PK): Unique identifier
- `entity_type` (VARCHAR(20), NOT NULL): Type of entity ('evidence' or 'claim')
- `entity_id` (UUID, NOT NULL): ID of the entity being embedded
- `embedding` (VECTOR(1536), NOT NULL): Vector embedding (1536 dimensions)
- `model_name` (VARCHAR(100), NOT NULL): Embedding model name (default: 'text-embedding-3-small')
- `model_version` (VARCHAR(50), NULLABLE): Model version for tracking
- `tenant_id` (VARCHAR(255), NOT NULL): Tenant isolation (default: 'default')
- `created_at` (TIMESTAMP, NOT NULL): Creation timestamp
- `updated_at` (TIMESTAMP, NOT NULL): Last update timestamp

**Indexes**:
- `idx_embeddings_tenant_id` - Tenant isolation
- `idx_embeddings_entity` - Entity lookups (composite: entity_type, entity_id)
- `idx_embeddings_entity_unique` - Unique constraint on entity
- `idx_embeddings_vector_cosine` - **IVFFlat index** for vector similarity (lists=100)

**Design Notes**:
- Uses **pgvector** extension for efficient vector operations
- IVFFlat index uses **cosine distance** operator for similarity search
- Lists parameter (100) should be adjusted based on corpus size (~sqrt(total_rows))
- Supports multi-tenancy through `tenant_id` column
- Polymorphic design allows embedding both evidence and claims

**Vector Dimensions**:
- Current: **1536 dimensions** (text-embedding-3-small)
- Alternative: **384 dimensions** (all-MiniLM-L6-v2 as per Phase 2 plan)
- Adjust based on your embedding model choice

---

#### 2. `nli_results` Table

Stores Natural Language Inference results for claim-evidence pairs, capturing entailment/contradiction/neutral predictions.

**Columns**:
- `id` (UUID, PK): Unique identifier
- `claim_id` (UUID, FK → claims.id, NOT NULL): Claim being verified
- `evidence_id` (UUID, FK → evidence.id, NOT NULL): Evidence used as premise
- `label` (VARCHAR(20), NOT NULL): NLI prediction ('ENTAILMENT', 'CONTRADICTION', 'NEUTRAL')
- `confidence` (FLOAT, NOT NULL): Probability of predicted label (0-1)
- `entailment_score` (FLOAT, NOT NULL): Score for ENTAILMENT class
- `contradiction_score` (FLOAT, NOT NULL): Score for CONTRADICTION class
- `neutral_score` (FLOAT, NOT NULL): Score for NEUTRAL class
- `model_name` (VARCHAR(100), NOT NULL): NLI model used (default: 'microsoft/deberta-v3-base')
- `model_version` (VARCHAR(50), NULLABLE): Model version
- `premise_text` (TEXT, NOT NULL): Evidence content (for auditability)
- `hypothesis_text` (TEXT, NOT NULL): Claim text (for auditability)
- `created_at` (TIMESTAMP, NOT NULL): Creation timestamp

**Indexes**:
- `idx_nli_results_claim_id` - Claim lookups
- `idx_nli_results_evidence_id` - Evidence lookups
- `idx_nli_results_claim_evidence` - Composite index for pair lookups
- `idx_nli_results_label` - Filter by label type

**Foreign Key Constraints**:
- `claim_id` → `claims.id` (ON DELETE CASCADE)
- `evidence_id` → `evidence.id` (ON DELETE CASCADE)

**Design Notes**:
- Stores **all three class scores** for full transparency
- Text fields stored for auditability and debugging
- Cascade deletes ensure referential integrity
- No unique constraint allows multiple verifications over time

---

#### 3. `verification_results` Table

Stores aggregated verification verdicts after processing multiple NLI results for a claim.

**Columns**:
- `id` (UUID, PK): Unique identifier
- `claim_id` (UUID, FK → claims.id, NOT NULL): Claim being verified
- `verdict` (VARCHAR(20), NOT NULL): Final verdict ('SUPPORTED', 'REFUTED', 'INSUFFICIENT')
- `confidence` (FLOAT, NOT NULL): Overall confidence (0-1)
- `support_score` (FLOAT, NOT NULL): Weighted entailment score
- `refute_score` (FLOAT, NOT NULL): Weighted contradiction score
- `neutral_score` (FLOAT, NOT NULL): Weighted neutral score
- `evidence_count` (INTEGER, NOT NULL): Number of evidence items analyzed
- `supporting_evidence_count` (INTEGER, NOT NULL, DEFAULT 0): Count of supporting evidence
- `refuting_evidence_count` (INTEGER, NOT NULL, DEFAULT 0): Count of refuting evidence
- `neutral_evidence_count` (INTEGER, NOT NULL, DEFAULT 0): Count of neutral evidence
- `reasoning` (TEXT, NULLABLE): Human-readable explanation
- `nli_result_ids` (UUID[], NULLABLE): Array of NLI result IDs used
- `pipeline_version` (VARCHAR(50), NULLABLE): Pipeline version tracking
- `retrieval_method` (VARCHAR(50), NULLABLE): Retrieval method used ('vector', 'hybrid', 'keyword')
- `created_at` (TIMESTAMP, NOT NULL): Creation timestamp
- `updated_at` (TIMESTAMP, NOT NULL): Last update timestamp

**Indexes**:
- `idx_verification_results_claim_id` - Claim lookups
- `idx_verification_results_verdict` - Filter by verdict
- `idx_verification_results_confidence` - Sort by confidence (DESC)
- `idx_verification_results_created_at` - Time-based queries (DESC)

**Foreign Key Constraints**:
- `claim_id` → `claims.id` (ON DELETE CASCADE)

**Design Notes**:
- Aggregates multiple NLI results into a single verdict
- Tracks evidence breakdown for transparency
- Array of `nli_result_ids` provides full traceability
- Pipeline metadata enables versioning and A/B testing
- No unique constraint allows re-verification over time

---

## Migration Commands

### Running the Migration

**Upgrade to Phase 2**:
```bash
# Using Alembic
alembic upgrade head

# Or using Docker Compose
docker-compose exec api alembic upgrade head
```

**Check Current Version**:
```bash
alembic current
```

**Downgrade (Rollback)**:
```bash
alembic downgrade -1  # Down one revision
# or
alembic downgrade phase2_ml_tables~1  # To revision before phase2
```

---

## Database Requirements

### PostgreSQL Extensions

The migration requires the following PostgreSQL extensions:

1. **pgvector** (>=0.5.0) - Vector similarity search
2. **uuid-ossp** - UUID generation (already enabled in Phase 1)

**Installation** (if not using Docker):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**Docker Setup**:
The `pgvector/pgvector:pg16` image includes pgvector pre-installed.

---

## Performance Considerations

### Vector Index Tuning

The IVFFlat index on `embeddings.embedding` uses the following parameters:

- **Lists**: 100 (default)
- **Distance Operator**: `vector_cosine_ops` (cosine distance)

**Tuning Guidelines**:

| Corpus Size | Recommended Lists | Query Speed | Recall |
|-------------|-------------------|-------------|--------|
| < 1,000     | 10-50             | Fast        | 95%+   |
| 1,000-10,000| 50-100            | Medium      | 90%+   |
| 10,000-100K | 100-500           | Medium      | 85%+   |
| 100K-1M     | 500-1000          | Slower      | 80%+   |

**Re-indexing**:
```sql
-- Drop old index
DROP INDEX IF EXISTS idx_embeddings_vector_cosine;

-- Create new index with adjusted lists parameter
CREATE INDEX idx_embeddings_vector_cosine
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 250);  -- Adjust based on corpus size
```

**Query Tuning**:
```sql
-- Set probes parameter (higher = better recall but slower)
SET ivfflat.probes = 10;  -- Default is lists/10

-- Query example
SELECT entity_id, 1 - (embedding <-> $1::vector) AS similarity
FROM embeddings
WHERE entity_type = 'evidence'
ORDER BY embedding <-> $1::vector
LIMIT 10;
```

---

## Migration Testing

### Automated Tests

Run the migration test suite:

```bash
# Install test dependencies
uv pip install -e ".[dev]"

# Run migration tests
pytest tests/test_migrations.py -v

# Run specific test
pytest tests/test_migrations.py::TestPhase2Migration::test_ivfflat_index_exists -v
```

### Manual Verification

**1. Verify Tables Exist**:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('embeddings', 'nli_results', 'verification_results');
```

**2. Verify pgvector Extension**:
```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

**3. Verify Indexes**:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('embeddings', 'nli_results', 'verification_results')
ORDER BY tablename, indexname;
```

**4. Verify Foreign Keys**:
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('nli_results', 'verification_results');
```

---

## Backward Compatibility

### Existing Tables

The migration **does not modify** any Phase 1 tables:
- ✓ `claims` - Unchanged
- ✓ `evidence` - Unchanged
- ✓ `verdicts` - Unchanged
- ✓ `verdict_evidence` - Unchanged

### Sync vs Async Support

- **Phase 1** code uses **sync SQLAlchemy** (`truthgraph/db.py`)
- **Phase 2** code uses **async SQLAlchemy** (`truthgraph/db_async.py`)
- Both can coexist - use `db_async.py` for new ML pipeline code

**Example**:
```python
# Phase 1 (sync) - still works
from truthgraph.db import get_db, SessionLocal

# Phase 2 (async) - new ML code
from truthgraph.db_async import get_async_session, AsyncSessionLocal
```

---

## Rollback Plan

### Safe Rollback

The migration can be safely rolled back if needed:

```bash
# Rollback Phase 2 migration
alembic downgrade -1

# Verify rollback
alembic current
```

**What Gets Removed**:
- ✓ `embeddings` table (and all data)
- ✓ `nli_results` table (and all data)
- ✓ `verification_results` table (and all data)
- ✗ pgvector extension (preserved for safety)

**What Remains Intact**:
- ✓ All Phase 1 tables and data
- ✓ All Phase 1 functionality
- ✓ Existing API endpoints

### Data Backup

**Before migration**:
```bash
# Backup entire database
docker-compose exec postgres pg_dump -U truthgraph truthgraph > backup_pre_phase2.sql

# Backup specific tables (Phase 1)
docker-compose exec postgres pg_dump -U truthgraph -t claims -t evidence -t verdicts -t verdict_evidence truthgraph > backup_phase1_tables.sql
```

**Restore if needed**:
```bash
# Restore full backup
docker-compose exec -T postgres psql -U truthgraph truthgraph < backup_pre_phase2.sql
```

---

## Troubleshooting

### Common Issues

#### 1. pgvector Extension Not Found

**Error**:
```
ERROR: extension "vector" is not available
```

**Solution**:
```bash
# Ensure using pgvector-enabled image
docker-compose down
docker-compose up -d postgres

# Or manually install pgvector
# (if using non-Docker PostgreSQL)
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### 2. Migration Timeout on Large Corpus

**Error**:
```
ERROR: canceling statement due to statement timeout
```

**Solution**:
```sql
-- Increase statement timeout
SET statement_timeout = '10min';

-- Then re-run migration
```

#### 3. IVFFlat Index Build Fails

**Error**:
```
ERROR: IVFFlat index build failed
```

**Solution**:
```sql
-- Increase maintenance_work_mem for index building
SET maintenance_work_mem = '1GB';

-- Manually rebuild index
CREATE INDEX idx_embeddings_vector_cosine
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### 4. Foreign Key Violation on Downgrade

**Error**:
```
ERROR: cannot drop table embeddings because other objects depend on it
```

**Solution**:
This shouldn't happen as CASCADE is used, but if it does:
```sql
-- Drop tables manually in reverse order
DROP TABLE IF EXISTS verification_results CASCADE;
DROP TABLE IF EXISTS nli_results CASCADE;
DROP TABLE IF EXISTS embeddings CASCADE;
```

---

## Next Steps

After successful migration:

1. ✓ Verify all tests pass: `pytest tests/test_migrations.py -v`
2. ✓ Run embedding generation: See `scripts/embed_corpus.py`
3. ✓ Test vector search: See `truthgraph/retrieval/vector_search.py`
4. ✓ Implement NLI verification: See `truthgraph/ml/verification.py`
5. ✓ Build complete pipeline: See `truthgraph/verification/pipeline.py`

---

## Schema Diagram

```
┌─────────────────────┐
│      claims         │
│  (Phase 1)          │
└──────┬──────────────┘
       │
       │ 1:N
       ▼
┌──────────────────────┐         ┌─────────────────────┐
│  verification_results│◄────────│   nli_results       │
│  (Phase 2)           │  N:1    │   (Phase 2)         │
│                      │         │                     │
│ - verdict            │         │ - label             │
│ - confidence         │         │ - confidence        │
│ - support_score      │         │ - entailment_score  │
│ - refute_score       │         │ - contradiction_s.. │
│ - neutral_score      │         │ - neutral_score     │
│ - nli_result_ids[]   │         │                     │
└──────────────────────┘         └──────┬──────────────┘
                                        │
                                        │ N:1
                                        ▼
                          ┌─────────────────────┐
                          │     evidence        │
                          │  (Phase 1)          │
                          └──────┬──────────────┘
                                 │
                                 │ 1:1
                                 ▼
                          ┌─────────────────────┐
                          │   embeddings        │
                          │  (Phase 2)          │
                          │                     │
                          │ - embedding (vector)│
                          │ - entity_type       │
                          │ - entity_id         │
                          └─────────────────────┘
```

---

## References

- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **pgvector Documentation**: https://github.com/pgvector/pgvector
- **SQLAlchemy 2.0 Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Phase 2 Implementation Plan**: `PHASE_2_IMPLEMENTATION_PLAN.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Migration Status**: Ready for deployment
