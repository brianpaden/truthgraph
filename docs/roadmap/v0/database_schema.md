# TruthGraph v0 Database Schema

**Version**: 1.0
**Last Updated**: 2025-10-24
**Status**: Ready for Implementation

## Overview

This document provides comprehensive database architecture documentation for TruthGraph v0 MVP. The schema is designed for simplicity, immediate usability, and a clear evolution path to v1 multi-tenant architecture.

**Design Philosophy**:
- Single database (PostgreSQL 16 + pgvector) for all data and vectors
- Simple, normalized schema optimized for MVP scope
- UUID primary keys for future distributed system compatibility
- Clear upgrade path to v1 (no schema rewrites required)

---

## Table of Contents

1. [Database Technology Choice](#database-technology-choice)
2. [Complete Schema Design](#complete-schema-design)
3. [Indexing Strategy](#indexing-strategy)
4. [pgvector Configuration](#pgvector-configuration)
5. [Data Access Patterns](#data-access-patterns)
6. [Migrations](#migrations)
7. [Evolution to v1](#evolution-to-v1)
8. [Sample Data](#sample-data)

---

## Database Technology Choice

### PostgreSQL 16 + pgvector

**Decision**: Use PostgreSQL 16 with pgvector extension as the single database for both relational data and vector search.

#### Why PostgreSQL 16?

1. **ACID Guarantees**: Full transactional consistency for claim-evidence-verdict chains
2. **Mature Ecosystem**: Battle-tested, excellent tooling, wide community support
3. **Full-Text Search**: Built-in FTS capabilities with GIN indexes
4. **JSONB Support**: Flexible metadata storage without schema changes
5. **UUID Generation**: Native `gen_random_uuid()` function (PostgreSQL 13+)
6. **Extension System**: pgvector integration seamless

#### Why pgvector?

1. **Unified Storage**: Keep relational data and embeddings in same database
2. **Simplified Operations**: Single backup, single deployment, single connection pool
3. **Good Enough Performance**: For <100K vectors, pgvector performs well (sub-100ms queries)
4. **SQL Integration**: Join vector search with relational queries efficiently
5. **Index Support**: IVFFlat indexes for approximate nearest neighbor search

**Performance Characteristics for MVP Scope (<100K vectors)**:

| Operation | Performance | Notes |
|-----------|-------------|-------|
| Vector insert | ~5ms | Batch inserts recommended |
| Similarity search (top 10) | 50-150ms | With IVFFlat index |
| Full-text search | 10-50ms | With GIN index |
| Hybrid query (FTS + vector) | 100-200ms | Parallel execution |
| Index rebuild | 5-10 min | For 100K vectors |

#### Why NOT Dual Vector Stores (pgvector + FAISS)?

**v0 Rationale for pgvector-only**:

1. **Operational Simplicity**: One database to back up, monitor, and manage
2. **No Synchronization Issues**: Single source of truth eliminates data consistency concerns
3. **Sufficient Performance**: For MVP scope (<100K vectors), pgvector latency is acceptable (<200ms)
4. **Faster Development**: No FAISS index management, serialization, or warm-up logic
5. **Easier Testing**: Single database makes integration tests simpler

**Trade-offs**:
- pgvector is slower than FAISS for large-scale retrieval (>1M vectors)
- IVFFlat indexes less accurate than FAISS IndexIVFPQ at extreme scale
- No sharding/partitioning for vector search (all in one database)

**When to Add FAISS (v1)**:

Add FAISS when you observe:
- Vector corpus exceeds 500K-1M documents
- Retrieval latency consistently >500ms (P95)
- Need for multi-index strategies (e.g., separate indexes per tenant)
- Advanced index types (HNSW, IVF+PQ) not available in pgvector

**Migration Path**: FAISS can be added later as a read-through cache:
1. Keep pgvector as source of truth
2. Add FAISS index for fast retrieval (read-only)
3. Synchronize nightly or on-demand
4. Fall back to pgvector on FAISS cache miss

---

## Complete Schema Design

### Database Initialization

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation (legacy)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid() (modern)
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector for embeddings
```

### Core Tables

#### 1. `claims` - User-submitted claims to verify

```sql
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    source_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT claims_text_not_empty CHECK (length(trim(text)) > 0)
);

-- Indexes
CREATE INDEX idx_claims_submitted_at ON claims(submitted_at DESC);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);
CREATE INDEX idx_claims_metadata_gin ON claims USING gin(metadata);

-- Comments
COMMENT ON TABLE claims IS 'User-submitted claims awaiting or completed verification';
COMMENT ON COLUMN claims.id IS 'UUID primary key for distributed system compatibility';
COMMENT ON COLUMN claims.text IS 'The claim statement to verify';
COMMENT ON COLUMN claims.source_url IS 'Optional URL where claim was found';
COMMENT ON COLUMN claims.metadata IS 'Flexible JSONB for future extensibility (e.g., {"language": "en", "priority": "high"})';
COMMENT ON COLUMN claims.submitted_at IS 'When user submitted the claim (user-facing timestamp)';
COMMENT ON COLUMN claims.created_at IS 'When record was created in database';
COMMENT ON COLUMN claims.updated_at IS 'When record was last updated';
```

**Key Design Decisions**:
- **UUIDs**: Future-proof for distributed systems (can merge databases without ID conflicts)
- **TIMESTAMP WITH TIME ZONE**: Correct timezone handling for global users (future-proofing)
- **JSONB metadata**: Extensibility without schema changes (can add custom fields per use case)
- **NOT NULL constraints**: Enforce data integrity at database level
- **CHECK constraint**: Prevent empty claim text

#### 2. `evidence` - Corpus of evidence documents

```sql
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50) DEFAULT 'document',
    published_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT evidence_content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT evidence_source_type_valid CHECK (
        source_type IN ('document', 'article', 'manual_entry', 'wikipedia', 'scientific_paper', 'other')
    )
);

-- Indexes
CREATE INDEX idx_evidence_created_at ON evidence(created_at DESC);
CREATE INDEX idx_evidence_source_type ON evidence(source_type);
CREATE INDEX idx_evidence_published_at ON evidence(published_at DESC NULLS LAST);
CREATE INDEX idx_evidence_metadata_gin ON evidence USING gin(metadata);

-- Full-text search index
CREATE INDEX idx_evidence_fts ON evidence USING gin(to_tsvector('english', content));

-- Comments
COMMENT ON TABLE evidence IS 'Corpus of evidence documents for fact verification';
COMMENT ON COLUMN evidence.id IS 'UUID primary key';
COMMENT ON COLUMN evidence.content IS 'Full text content of evidence document (can be chunked)';
COMMENT ON COLUMN evidence.source_url IS 'URL where evidence was retrieved';
COMMENT ON COLUMN evidence.source_type IS 'Type of evidence source for filtering';
COMMENT ON COLUMN evidence.published_at IS 'When evidence was published (if known)';
COMMENT ON COLUMN evidence.metadata IS 'Flexible metadata (e.g., {"author": "...", "journal": "...", "chunk_index": 3})';
```

**Key Design Decisions**:
- **TEXT vs VARCHAR**: Use TEXT for content (no length limit)
- **Source type enum**: Constrained CHECK for data quality
- **Published date**: Optional, useful for temporal reasoning later
- **Full-text search**: GIN index on content for lexical search
- **Metadata examples**: Author, journal, chunk index, language, etc.

#### 3. `evidence_embeddings` - Vector embeddings for semantic search

```sql
CREATE TABLE evidence_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    embedding VECTOR(384) NOT NULL,
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT evidence_embeddings_unique_evidence UNIQUE(evidence_id)
);

-- Indexes
CREATE INDEX idx_embeddings_evidence_id ON evidence_embeddings(evidence_id);

-- Vector similarity index (IVFFlat for approximate nearest neighbor)
-- Note: Create this AFTER inserting data (see pgvector configuration section)
-- CREATE INDEX idx_embeddings_vector_cosine ON evidence_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Comments
COMMENT ON TABLE evidence_embeddings IS 'Dense vector embeddings for semantic similarity search';
COMMENT ON COLUMN evidence_embeddings.evidence_id IS 'Foreign key to evidence table (1:1 relationship)';
COMMENT ON COLUMN evidence_embeddings.embedding IS 'Vector embedding (384 dimensions for all-MiniLM-L6-v2)';
COMMENT ON COLUMN evidence_embeddings.model_name IS 'Name of embedding model used (for future model upgrades)';
COMMENT ON INDEX idx_embeddings_vector_cosine IS 'IVFFlat index for fast approximate nearest neighbor search';
```

**Key Design Decisions**:
- **1:1 relationship**: One embedding per evidence document (enforced by UNIQUE constraint)
- **CASCADE delete**: If evidence is deleted, embedding is automatically removed
- **Model name tracking**: Essential for future model upgrades (can re-embed with new models)
- **VECTOR(384)**: Fixed dimension for all-MiniLM-L6-v2 model
- **Deferred index creation**: Create IVFFlat index AFTER bulk inserts for better performance

**Why separate table for embeddings?**:
- **Size optimization**: VECTOR(384) adds ~1.5KB per row; separation reduces `evidence` table bloat
- **Index efficiency**: pgvector indexes work best on dedicated tables
- **Future flexibility**: Can have multiple embeddings per evidence (different models)

#### 4. `verdicts` - Verification results

```sql
CREATE TABLE verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    reasoning TEXT,
    evidence_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT verdicts_verdict_valid CHECK (
        verdict IN ('SUPPORTED', 'REFUTED', 'INSUFFICIENT')
    ),
    CONSTRAINT verdicts_confidence_range CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    CONSTRAINT verdicts_evidence_count_non_negative CHECK (
        evidence_count >= 0
    )
);

-- Indexes
CREATE INDEX idx_verdicts_claim_id ON verdicts(claim_id);
CREATE INDEX idx_verdicts_verdict ON verdicts(verdict);
CREATE INDEX idx_verdicts_created_at ON verdicts(created_at DESC);
CREATE INDEX idx_verdicts_confidence ON verdicts(confidence DESC);

-- Comments
COMMENT ON TABLE verdicts IS 'Verification results for claims';
COMMENT ON COLUMN verdicts.claim_id IS 'Foreign key to claims table (1:many relationship - can have multiple verdicts over time)';
COMMENT ON COLUMN verdicts.verdict IS 'Final verdict: SUPPORTED, REFUTED, or INSUFFICIENT';
COMMENT ON COLUMN verdicts.confidence IS 'Confidence score between 0.0 and 1.0';
COMMENT ON COLUMN verdicts.reasoning IS 'Human-readable explanation of verdict';
COMMENT ON COLUMN verdicts.evidence_count IS 'Number of evidence items used in verification';
COMMENT ON COLUMN verdicts.metadata IS 'Flexible metadata (e.g., {"model_version": "1.0", "processing_time_ms": 1234})';
```

**Key Design Decisions**:
- **Enum constraint**: Strict verdict values for data quality
- **Confidence bounds**: Enforced at database level (0.0 to 1.0)
- **1:many relationship**: A claim can have multiple verdicts over time (re-verification)
- **Reasoning field**: Human-readable explanation (generated by LLM or templated)
- **Evidence count**: Denormalized for quick access (avoids JOIN for counts)

#### 5. `verdict_evidence` - Links between verdicts and supporting/refuting evidence

```sql
CREATE TABLE verdict_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verdict_id UUID NOT NULL REFERENCES verdicts(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relationship VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    nli_label VARCHAR(20),
    nli_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT verdict_evidence_unique_pair UNIQUE(verdict_id, evidence_id),
    CONSTRAINT verdict_evidence_relationship_valid CHECK (
        relationship IN ('supports', 'refutes', 'neutral')
    ),
    CONSTRAINT verdict_evidence_confidence_range CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    CONSTRAINT verdict_evidence_nli_label_valid CHECK (
        nli_label IS NULL OR nli_label IN ('entailment', 'contradiction', 'neutral')
    ),
    CONSTRAINT verdict_evidence_nli_score_range CHECK (
        nli_score IS NULL OR (nli_score >= 0.0 AND nli_score <= 1.0)
    )
);

-- Indexes
CREATE INDEX idx_verdict_evidence_verdict_id ON verdict_evidence(verdict_id);
CREATE INDEX idx_verdict_evidence_evidence_id ON verdict_evidence(evidence_id);
CREATE INDEX idx_verdict_evidence_relationship ON verdict_evidence(relationship);

-- Comments
COMMENT ON TABLE verdict_evidence IS 'Many-to-many relationship between verdicts and evidence with relationship metadata';
COMMENT ON COLUMN verdict_evidence.verdict_id IS 'Foreign key to verdicts table';
COMMENT ON COLUMN verdict_evidence.evidence_id IS 'Foreign key to evidence table';
COMMENT ON COLUMN verdict_evidence.relationship IS 'How evidence relates to claim: supports, refutes, or neutral';
COMMENT ON COLUMN verdict_evidence.confidence IS 'Confidence in this relationship (aggregated across NLI and other signals)';
COMMENT ON COLUMN verdict_evidence.nli_label IS 'Raw NLI model output: entailment, contradiction, neutral';
COMMENT ON COLUMN verdict_evidence.nli_score IS 'Raw NLI model confidence score';
```

**Key Design Decisions**:
- **Many-to-many junction table**: A verdict uses multiple evidence items; evidence can support multiple verdicts
- **Unique constraint**: Prevent duplicate verdict-evidence pairs
- **Relationship tracking**: Explicit supports/refutes/neutral labels
- **NLI provenance**: Store raw NLI outputs for debugging and future re-scoring
- **Confidence separation**: Aggregated confidence vs raw NLI score

### Schema Diagram (ERD)

```
┌─────────────────┐
│     claims      │
├─────────────────┤
│ id (PK)         │
│ text            │
│ source_url      │
│ metadata        │
│ submitted_at    │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ 1:many
         │
         ▼
┌─────────────────┐         ┌──────────────────────┐
│    verdicts     │◄────────┤  verdict_evidence    │
├─────────────────┤  many:1 ├──────────────────────┤
│ id (PK)         │         │ id (PK)              │
│ claim_id (FK)   │         │ verdict_id (FK)      │
│ verdict         │         │ evidence_id (FK)     │
│ confidence      │         │ relationship         │
│ reasoning       │         │ confidence           │
│ evidence_count  │         │ nli_label            │
│ metadata        │         │ nli_score            │
│ created_at      │         │ created_at           │
│ updated_at      │         └──────────┬───────────┘
└─────────────────┘                    │ many:1
                                       │
                                       ▼
                               ┌─────────────────┐
                               │    evidence     │
                               ├─────────────────┤
                               │ id (PK)         │
                               │ content         │
                               │ source_url      │
                               │ source_type     │
                               │ published_at    │
                               │ metadata        │
                               │ created_at      │
                               │ updated_at      │
                               └────────┬────────┘
                                        │ 1:1
                                        ▼
                          ┌──────────────────────────┐
                          │  evidence_embeddings     │
                          ├──────────────────────────┤
                          │ id (PK)                  │
                          │ evidence_id (FK, UNIQUE) │
                          │ embedding (VECTOR)       │
                          │ model_name               │
                          │ created_at               │
                          └──────────────────────────┘
```

---

## Indexing Strategy

### Primary Keys (UUIDs)

All tables use UUID primary keys with `gen_random_uuid()`:

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Benefits**:
- **Distributed-friendly**: No central ID generator needed
- **Merge-safe**: Can merge databases without ID conflicts
- **Security**: Non-sequential IDs prevent enumeration attacks
- **Future-proof**: Compatible with distributed databases (CockroachDB, YugabyteDB)

**Trade-offs**:
- Slightly larger indexes (~16 bytes vs 4-8 bytes for integers)
- Random insertion order (can fragment B-tree indexes, mitigated by PostgreSQL)

### Foreign Key Indexes

All foreign keys have indexes for efficient JOINs:

```sql
-- On verdicts table
CREATE INDEX idx_verdicts_claim_id ON verdicts(claim_id);

-- On verdict_evidence table
CREATE INDEX idx_verdict_evidence_verdict_id ON verdict_evidence(verdict_id);
CREATE INDEX idx_verdict_evidence_evidence_id ON verdict_evidence(evidence_id);

-- On evidence_embeddings table
CREATE INDEX idx_embeddings_evidence_id ON evidence_embeddings(evidence_id);
```

**Query optimization**: These indexes enable fast lookups:
- "Get all verdicts for claim X"
- "Get all evidence for verdict Y"
- "Get embedding for evidence Z"

### Timestamp Indexes

For common "list recent X" queries:

```sql
CREATE INDEX idx_claims_submitted_at ON claims(submitted_at DESC);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);
CREATE INDEX idx_evidence_created_at ON evidence(created_at DESC);
CREATE INDEX idx_verdicts_created_at ON verdicts(created_at DESC);
```

**DESC ordering**: Optimizes `ORDER BY ... DESC LIMIT N` queries (most recent first).

### Full-Text Search Index

For lexical search on evidence content:

```sql
CREATE INDEX idx_evidence_fts ON evidence USING gin(to_tsvector('english', content));
```

**Usage**:
```sql
SELECT * FROM evidence
WHERE to_tsvector('english', content) @@ plainto_tsquery('english', 'climate change');
```

**Performance**:
- GIN index: Fast lookups (10-50ms for typical queries)
- Memory overhead: ~20-30% of text size
- Supports stemming, stop words, ranking

**Upgrade path**: Can add multiple language support:
```sql
-- Future: Multi-language FTS
CREATE INDEX idx_evidence_fts_english ON evidence USING gin(to_tsvector('english', content));
CREATE INDEX idx_evidence_fts_spanish ON evidence USING gin(to_tsvector('spanish', content));
```

### JSONB Indexes

For metadata queries:

```sql
CREATE INDEX idx_claims_metadata_gin ON claims USING gin(metadata);
CREATE INDEX idx_evidence_metadata_gin ON evidence USING gin(metadata);
```

**Usage**:
```sql
-- Find claims with high priority
SELECT * FROM claims WHERE metadata @> '{"priority": "high"}';

-- Find evidence from specific author
SELECT * FROM evidence WHERE metadata @> '{"author": "John Doe"}';
```

**Performance**: GIN indexes enable fast containment queries (`@>` operator).

### pgvector Similarity Index

For semantic search (see [pgvector Configuration](#pgvector-configuration) section):

```sql
CREATE INDEX idx_embeddings_vector_cosine ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Important**: Create this index AFTER bulk inserts (see below).

---

## pgvector Configuration

### Vector Dimensions

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
**Dimensions**: 384

```sql
CREATE TABLE evidence_embeddings (
    ...
    embedding VECTOR(384) NOT NULL,
    ...
);
```

**Why 384 dimensions?**:
- Good balance between quality and speed
- Fast on CPU (~1000 sentences/second)
- Smaller storage footprint than 768-dim models (BERT, Contriever)

### Index Type: IVFFlat

**IVFFlat** (Inverted File with Flat Quantization):
- Approximate nearest neighbor (ANN) search
- Faster than exact search for >10K vectors
- Trade-off: Slight accuracy loss (configurable)

**Index Creation** (AFTER bulk inserts):

```sql
-- 1. Insert all embeddings first
INSERT INTO evidence_embeddings (evidence_id, embedding, model_name)
SELECT ...;

-- 2. Create index (this is slow on large datasets)
CREATE INDEX idx_embeddings_vector_cosine ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 3. ANALYZE for query planner statistics
ANALYZE evidence_embeddings;
```

### Index Parameters

**`lists` parameter**: Number of clusters for IVFFlat index

**Rule of thumb**: `lists = sqrt(num_vectors)`

| Vector Count | Recommended lists | Index Build Time | Query Time |
|--------------|-------------------|------------------|------------|
| 10K | 100 | ~1 min | 50-100ms |
| 50K | 224 | ~5 min | 80-150ms |
| 100K | 316 | ~10 min | 100-200ms |
| 500K | 707 | ~30 min | 200-400ms |

**For v0 MVP (<100K vectors)**: `lists = 100` is a good starting point.

**Too few lists**: Slower queries (more vectors per cluster to scan)
**Too many lists**: Slower index builds, diminishing returns

### Distance Metrics

**Cosine distance** (recommended for normalized embeddings):

```sql
CREATE INDEX idx_embeddings_vector_cosine ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops);

-- Query
SELECT * FROM evidence_embeddings
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

**L2 distance** (Euclidean):

```sql
CREATE INDEX idx_embeddings_vector_l2 ON evidence_embeddings
    USING ivfflat (embedding vector_l2_ops);

-- Query
SELECT * FROM evidence_embeddings
ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

**Inner product**:

```sql
CREATE INDEX idx_embeddings_vector_ip ON evidence_embeddings
    USING ivfflat (embedding vector_ip_ops);

-- Query (note: <#> operator)
SELECT * FROM evidence_embeddings
ORDER BY embedding <#> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

**For all-MiniLM-L6-v2**: Use **cosine distance** (embeddings are normalized).

### Query Optimization

**Set `ivfflat.probes` for accuracy/speed trade-off**:

```sql
-- Default: probes = 1 (fastest, least accurate)
SET ivfflat.probes = 1;

-- Better accuracy: probes = 10 (10x slower, ~95% recall)
SET ivfflat.probes = 10;

-- Best accuracy: probes = lists (exact search, defeats purpose of index)
SET ivfflat.probes = 100;
```

**Recommendation for v0**: `ivfflat.probes = 5` (good balance).

**Per-session setting**:
```sql
-- Set for current session
SET ivfflat.probes = 5;

-- Set globally (requires superuser)
ALTER DATABASE truthgraph SET ivfflat.probes = 5;
```

### When to Rebuild Indexes

**Rebuild triggers**:
1. **After bulk inserts**: If you add >10% new vectors
2. **After model upgrade**: If you re-embed corpus with new model
3. **Performance degradation**: If queries become consistently slow

**Rebuild process**:

```sql
-- 1. Drop old index
DROP INDEX idx_embeddings_vector_cosine;

-- 2. Re-create with updated parameters
CREATE INDEX idx_embeddings_vector_cosine ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 316);  -- Adjusted for new vector count

-- 3. Update statistics
ANALYZE evidence_embeddings;
```

**Concurrent rebuild** (PostgreSQL 12+):

```sql
CREATE INDEX CONCURRENTLY idx_embeddings_vector_cosine_new ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 316);

-- Swap indexes
DROP INDEX idx_embeddings_vector_cosine;
ALTER INDEX idx_embeddings_vector_cosine_new RENAME TO idx_embeddings_vector_cosine;
```

### Performance Tuning Parameters

**PostgreSQL configuration** (add to `postgresql.conf` or Docker environment):

```ini
# Increase shared buffers for vector operations (default: 128MB)
shared_buffers = 2GB

# Increase work_mem for sorting/indexing (default: 4MB)
work_mem = 256MB

# Increase maintenance_work_mem for index builds (default: 64MB)
maintenance_work_mem = 1GB

# Enable parallel workers for faster queries
max_parallel_workers_per_gather = 4

# Increase effective_cache_size (estimate of OS cache)
effective_cache_size = 8GB
```

**Docker Compose override**:

```yaml
postgres:
  image: pgvector/pgvector:pg16
  command:
    - "postgres"
    - "-c"
    - "shared_buffers=2GB"
    - "-c"
    - "work_mem=256MB"
    - "-c"
    - "maintenance_work_mem=1GB"
```

---

## Data Access Patterns

### Common Query Patterns

#### 1. Insert Claim Workflow

**Step 1**: User submits claim via API

```sql
-- Insert claim
INSERT INTO claims (text, source_url, metadata)
VALUES (
    'The Earth is round',
    'https://example.com/article',
    '{"language": "en", "priority": "normal"}'::jsonb
)
RETURNING id, text, submitted_at, created_at;
```

**Step 2**: Trigger verification workflow (via Redis Streams or direct call)

#### 2. Search Evidence Workflow

**Step 2a**: Generate claim embedding (Python)

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
claim_text = "The Earth is round"
claim_embedding = model.encode(claim_text)  # Returns 384-dim vector
```

**Step 2b**: Hybrid retrieval (FTS + Vector Search)

**Full-Text Search**:
```sql
-- Lexical search
SELECT
    e.id,
    e.content,
    e.source_url,
    ts_rank(to_tsvector('english', e.content), plainto_tsquery('english', $1)) AS fts_rank
FROM evidence e
WHERE to_tsvector('english', e.content) @@ plainto_tsquery('english', $1)
ORDER BY fts_rank DESC
LIMIT 5;

-- Example: $1 = 'Earth round spherical'
```

**Vector Similarity Search**:
```sql
-- Semantic search
SELECT
    e.id,
    e.content,
    e.source_url,
    ee.embedding <=> $1::vector AS distance
FROM evidence e
JOIN evidence_embeddings ee ON e.id = ee.evidence_id
ORDER BY ee.embedding <=> $1::vector
LIMIT 5;

-- Example: $1 = '[0.012, -0.034, 0.056, ...]' (384-dim vector)
```

**Combined Hybrid Search** (parallel queries, merged in application):

```python
import asyncpg

async def hybrid_search(claim_text: str, claim_embedding: list, limit: int = 10):
    # Execute FTS and vector search in parallel
    fts_results = await db.fetch("""
        SELECT e.id, e.content, e.source_url,
               ts_rank(to_tsvector('english', e.content), plainto_tsquery('english', $1)) AS score
        FROM evidence e
        WHERE to_tsvector('english', e.content) @@ plainto_tsquery('english', $1)
        ORDER BY score DESC
        LIMIT $2
    """, claim_text, limit)

    vector_results = await db.fetch("""
        SELECT e.id, e.content, e.source_url,
               1.0 / (1.0 + (ee.embedding <=> $1::vector)) AS score
        FROM evidence e
        JOIN evidence_embeddings ee ON e.id = ee.evidence_id
        ORDER BY ee.embedding <=> $1::vector
        LIMIT $2
    """, claim_embedding, limit)

    # Merge and deduplicate (by evidence ID)
    # Re-rank by combined score (e.g., RRF - Reciprocal Rank Fusion)
    merged = merge_and_rerank(fts_results, vector_results)

    return merged[:limit]
```

#### 3. Store Verdict Workflow

**Step 3a**: Run NLI model on retrieved evidence (Python)

```python
from transformers import pipeline

nli = pipeline("text-classification", model="microsoft/deberta-v3-base")

claim = "The Earth is round"
evidence_list = [...]  # Retrieved evidence

nli_results = []
for evidence in evidence_list:
    result = nli({
        "text": claim,
        "text_pair": evidence['content']
    })
    nli_results.append({
        "evidence_id": evidence['id'],
        "label": result['label'],  # entailment, contradiction, neutral
        "score": result['score']
    })
```

**Step 3b**: Aggregate verdict

```python
def aggregate_verdict(nli_results):
    support_score = sum(r['score'] for r in nli_results if r['label'] == 'entailment')
    refute_score = sum(r['score'] for r in nli_results if r['label'] == 'contradiction')

    if support_score > 0.6 * len(nli_results):
        return 'SUPPORTED', support_score / len(nli_results)
    elif refute_score > 0.6 * len(nli_results):
        return 'REFUTED', refute_score / len(nli_results)
    else:
        return 'INSUFFICIENT', 0.5
```

**Step 3c**: Store verdict and evidence links

```sql
BEGIN;

-- Insert verdict
INSERT INTO verdicts (claim_id, verdict, confidence, reasoning, evidence_count)
VALUES (
    $1,  -- claim_id
    $2,  -- verdict (SUPPORTED, REFUTED, INSUFFICIENT)
    $3,  -- confidence
    $4,  -- reasoning text
    $5   -- evidence_count
)
RETURNING id;

-- Insert verdict-evidence links
INSERT INTO verdict_evidence (verdict_id, evidence_id, relationship, confidence, nli_label, nli_score)
VALUES
    ($verdict_id, $evidence_id_1, 'supports', 0.92, 'entailment', 0.92),
    ($verdict_id, $evidence_id_2, 'supports', 0.87, 'entailment', 0.87),
    ($verdict_id, $evidence_id_3, 'refutes', 0.15, 'contradiction', 0.15);

COMMIT;
```

#### 4. Common Query Examples

**Get claim with latest verdict**:
```sql
SELECT
    c.id,
    c.text,
    c.source_url,
    c.submitted_at,
    v.verdict,
    v.confidence,
    v.reasoning,
    v.evidence_count,
    v.created_at AS verdict_created_at
FROM claims c
LEFT JOIN LATERAL (
    SELECT * FROM verdicts
    WHERE claim_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) v ON true
WHERE c.id = $1;
```

**Get verdict with supporting/refuting evidence**:
```sql
SELECT
    v.id AS verdict_id,
    v.verdict,
    v.confidence,
    v.reasoning,
    e.id AS evidence_id,
    e.content AS evidence_content,
    e.source_url,
    ve.relationship,
    ve.confidence AS evidence_confidence,
    ve.nli_label,
    ve.nli_score
FROM verdicts v
JOIN verdict_evidence ve ON v.id = ve.verdict_id
JOIN evidence e ON ve.evidence_id = e.id
WHERE v.claim_id = $1
ORDER BY ve.confidence DESC;
```

**List recent claims with verdicts**:
```sql
SELECT
    c.id,
    c.text,
    c.submitted_at,
    v.verdict,
    v.confidence
FROM claims c
LEFT JOIN LATERAL (
    SELECT verdict, confidence FROM verdicts
    WHERE claim_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) v ON true
ORDER BY c.submitted_at DESC
LIMIT 20;
```

**Find evidence supporting a specific verdict**:
```sql
SELECT
    e.id,
    e.content,
    e.source_url,
    ve.confidence
FROM verdict_evidence ve
JOIN evidence e ON ve.evidence_id = e.id
WHERE ve.verdict_id = $1
  AND ve.relationship = 'supports'
ORDER BY ve.confidence DESC;
```

---

## Migrations

### Using Alembic for Schema Versioning

**Alembic** is the standard migration tool for SQLAlchemy-based projects.

#### Initial Setup

**1. Install Alembic**:
```bash
uv add alembic
```

**2. Initialize Alembic**:
```bash
uv run alembic init alembic
```

This creates:
```
truthgraph/
├── alembic/
│   ├── versions/       # Migration scripts
│   ├── env.py          # Alembic environment
│   └── script.py.mako  # Template for new migrations
└── alembic.ini         # Configuration
```

**3. Configure `alembic.ini`**:
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://truthgraph:password@localhost:5432/truthgraph

# Or use environment variable
# sqlalchemy.url = driver://user:pass@localhost/dbname
# Leave blank and set in env.py
```

**4. Configure `alembic/env.py`** (read DB URL from environment):
```python
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your SQLAlchemy models
from truthgraph.models import Base

# Read database URL from environment
config = context.config
db_url = os.getenv("DATABASE_URL", "postgresql://truthgraph:password@localhost:5432/truthgraph")
config.set_main_option("sqlalchemy.url", db_url)

# Use your models' metadata for autogenerate
target_metadata = Base.metadata

# ... (rest of Alembic boilerplate)
```

#### Initial Migration Script

**Generate initial migration**:
```bash
uv run alembic revision --autogenerate -m "Initial schema"
```

This creates `alembic/versions/xxxx_initial_schema.py`.

**Manual migration** (`alembic/versions/0001_initial_schema.py`):

```python
"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-10-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Create claims table
    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(text)) > 0", name='claims_text_not_empty')
    )
    op.create_index('idx_claims_submitted_at', 'claims', ['submitted_at'], postgresql_using='btree', postgresql_ops={'submitted_at': 'DESC'})
    op.create_index('idx_claims_created_at', 'claims', ['created_at'], postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_claims_metadata_gin', 'claims', ['metadata'], postgresql_using='gin')

    # Create evidence table
    op.create_table(
        'evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_type', sa.VARCHAR(50), server_default='document', nullable=False),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(content)) > 0", name='evidence_content_not_empty'),
        sa.CheckConstraint("source_type IN ('document', 'article', 'manual_entry', 'wikipedia', 'scientific_paper', 'other')", name='evidence_source_type_valid')
    )
    op.create_index('idx_evidence_created_at', 'evidence', ['created_at'], postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_evidence_source_type', 'evidence', ['source_type'])
    op.create_index('idx_evidence_published_at', 'evidence', ['published_at'], postgresql_using='btree', postgresql_ops={'published_at': 'DESC NULLS LAST'})
    op.create_index('idx_evidence_metadata_gin', 'evidence', ['metadata'], postgresql_using='gin')

    # Full-text search index (requires raw SQL)
    op.execute("""
        CREATE INDEX idx_evidence_fts ON evidence
        USING gin(to_tsvector('english', content))
    """)

    # Create evidence_embeddings table
    op.create_table(
        'evidence_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('evidence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),  # Vector type requires custom handling
        sa.Column('model_name', sa.VARCHAR(100), server_default='all-MiniLM-L6-v2', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('evidence_id', name='evidence_embeddings_unique_evidence')
    )
    op.create_index('idx_embeddings_evidence_id', 'evidence_embeddings', ['evidence_id'])

    # Vector column (requires raw SQL for pgvector)
    op.execute("""
        ALTER TABLE evidence_embeddings
        ALTER COLUMN embedding TYPE VECTOR(384) USING embedding::vector
    """)

    # Create verdicts table
    op.create_table(
        'verdicts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('verdict', sa.VARCHAR(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('evidence_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.CheckConstraint("verdict IN ('SUPPORTED', 'REFUTED', 'INSUFFICIENT')", name='verdicts_verdict_valid'),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name='verdicts_confidence_range'),
        sa.CheckConstraint("evidence_count >= 0", name='verdicts_evidence_count_non_negative')
    )
    op.create_index('idx_verdicts_claim_id', 'verdicts', ['claim_id'])
    op.create_index('idx_verdicts_verdict', 'verdicts', ['verdict'])
    op.create_index('idx_verdicts_created_at', 'verdicts', ['created_at'], postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_verdicts_confidence', 'verdicts', ['confidence'], postgresql_using='btree', postgresql_ops={'confidence': 'DESC'})

    # Create verdict_evidence table
    op.create_table(
        'verdict_evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('verdict_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship', sa.VARCHAR(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('nli_label', sa.VARCHAR(20), nullable=True),
        sa.Column('nli_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['verdict_id'], ['verdicts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('verdict_id', 'evidence_id', name='verdict_evidence_unique_pair'),
        sa.CheckConstraint("relationship IN ('supports', 'refutes', 'neutral')", name='verdict_evidence_relationship_valid'),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name='verdict_evidence_confidence_range'),
        sa.CheckConstraint("nli_label IS NULL OR nli_label IN ('entailment', 'contradiction', 'neutral')", name='verdict_evidence_nli_label_valid'),
        sa.CheckConstraint("nli_score IS NULL OR (nli_score >= 0.0 AND nli_score <= 1.0)", name='verdict_evidence_nli_score_range')
    )
    op.create_index('idx_verdict_evidence_verdict_id', 'verdict_evidence', ['verdict_id'])
    op.create_index('idx_verdict_evidence_evidence_id', 'verdict_evidence', ['evidence_id'])
    op.create_index('idx_verdict_evidence_relationship', 'verdict_evidence', ['relationship'])


def downgrade():
    op.drop_table('verdict_evidence')
    op.drop_table('verdicts')
    op.drop_table('evidence_embeddings')
    op.drop_table('evidence')
    op.drop_table('claims')
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
```

#### Adding pgvector Extension

**In migration script** (see above):
```python
def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    # ... table creation
```

**Verify extension**:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

#### Safe Migration Practices

**1. Always test migrations in development first**:
```bash
# Development database
export DATABASE_URL="postgresql://truthgraph:dev@localhost:5432/truthgraph_dev"
uv run alembic upgrade head

# Rollback test
uv run alembic downgrade -1
```

**2. Use transactions** (Alembic does this by default):
```python
# alembic.ini
[alembic]
transaction_per_migration = true
```

**3. Add data migrations carefully**:
```python
def upgrade():
    # Schema change
    op.add_column('claims', sa.Column('language', sa.VARCHAR(5), server_default='en'))

    # Data migration (separate from schema change)
    op.execute("""
        UPDATE claims
        SET language = metadata->>'language'
        WHERE metadata ? 'language'
    """)
```

**4. Zero-downtime migrations** (for production):

**Adding a column** (safe):
```python
def upgrade():
    # Add nullable column first
    op.add_column('claims', sa.Column('priority', sa.VARCHAR(10), nullable=True))

    # Backfill in batches (avoid table locks)
    op.execute("""
        UPDATE claims SET priority = 'normal' WHERE priority IS NULL
    """)

    # Make NOT NULL after backfill (in separate migration)
    # op.alter_column('claims', 'priority', nullable=False)
```

**Dropping a column** (safe):
```python
# Migration 1: Mark column as deprecated (update application to ignore)
# (Deploy application)

# Migration 2: Drop column
def upgrade():
    op.drop_column('claims', 'old_field')
```

**5. Run migrations in production**:
```bash
# Dry run (show SQL without executing)
uv run alembic upgrade head --sql

# Actual migration
uv run alembic upgrade head

# Verify
uv run alembic current
uv run alembic history
```

#### Docker Integration

**Add migration to Docker entrypoint**:

`docker/entrypoint.sh`:
```bash
#!/bin/bash
set -e

# Wait for PostgreSQL
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Run migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Start application
exec "$@"
```

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy requirements
COPY pyproject.toml uv.lock ./
RUN uv pip install --system .

# Copy application
COPY . .

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "truthgraph.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Evolution to v1

### Adding Multi-Tenancy

**Goal**: Support multiple users/tenants while maintaining data isolation.

**Changes Required**:

1. **Add `tenant_id` column to all tables**
2. **Update indexes for tenant-scoped queries**
3. **Add row-level security policies** (optional but recommended)
4. **Update application queries** to filter by tenant

#### Migration Script: Add tenant_id

`alembic/versions/0002_add_multi_tenancy.py`:

```python
"""Add multi-tenancy support

Revision ID: 0002
Revises: 0001
Create Date: 2025-11-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column to claims
    op.add_column('claims', sa.Column('tenant_id', sa.VARCHAR(255), server_default='default', nullable=False))
    op.create_index('idx_claims_tenant_id', 'claims', ['tenant_id'])
    op.create_index('idx_claims_tenant_submitted', 'claims', ['tenant_id', 'submitted_at'],
                    postgresql_using='btree', postgresql_ops={'submitted_at': 'DESC'})

    # Add tenant_id column to evidence
    op.add_column('evidence', sa.Column('tenant_id', sa.VARCHAR(255), server_default='default', nullable=False))
    op.create_index('idx_evidence_tenant_id', 'evidence', ['tenant_id'])

    # Add tenant_id column to evidence_embeddings
    op.add_column('evidence_embeddings', sa.Column('tenant_id', sa.VARCHAR(255), server_default='default', nullable=False))
    op.create_index('idx_embeddings_tenant_id', 'evidence_embeddings', ['tenant_id'])

    # Add tenant_id column to verdicts
    op.add_column('verdicts', sa.Column('tenant_id', sa.VARCHAR(255), server_default='default', nullable=False))
    op.create_index('idx_verdicts_tenant_id', 'verdicts', ['tenant_id'])
    op.create_index('idx_verdicts_tenant_claim', 'verdicts', ['tenant_id', 'claim_id'])

    # Add tenant_id column to verdict_evidence
    op.add_column('verdict_evidence', sa.Column('tenant_id', sa.VARCHAR(255), server_default='default', nullable=False))
    op.create_index('idx_verdict_evidence_tenant_id', 'verdict_evidence', ['tenant_id'])

    # Add comments
    op.execute("""
        COMMENT ON COLUMN claims.tenant_id IS 'Tenant identifier: "default" in v0, real tenant IDs in v1+';
        COMMENT ON COLUMN evidence.tenant_id IS 'Tenant identifier: "default" in v0, real tenant IDs in v1+';
        COMMENT ON COLUMN verdicts.tenant_id IS 'Tenant identifier: "default" in v0, real tenant IDs in v1+';
    """)


def downgrade():
    # Drop tenant_id columns and indexes
    op.drop_index('idx_verdict_evidence_tenant_id', table_name='verdict_evidence')
    op.drop_column('verdict_evidence', 'tenant_id')

    op.drop_index('idx_verdicts_tenant_claim', table_name='verdicts')
    op.drop_index('idx_verdicts_tenant_id', table_name='verdicts')
    op.drop_column('verdicts', 'tenant_id')

    op.drop_index('idx_embeddings_tenant_id', table_name='evidence_embeddings')
    op.drop_column('evidence_embeddings', 'tenant_id')

    op.drop_index('idx_evidence_tenant_id', table_name='evidence')
    op.drop_column('evidence', 'tenant_id')

    op.drop_index('idx_claims_tenant_submitted', table_name='claims')
    op.drop_index('idx_claims_tenant_id', table_name='claims')
    op.drop_column('claims', 'tenant_id')
```

#### Adding Row-Level Security Policies

**Enable RLS** (after adding tenant_id):

```sql
-- Enable row-level security on all tables
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE verdicts ENABLE ROW LEVEL SECURITY;
ALTER TABLE verdict_evidence ENABLE ROW LEVEL SECURITY;

-- Create policies for tenant isolation
CREATE POLICY tenant_isolation_claims ON claims
    USING (tenant_id = current_setting('app.current_tenant', true)::text);

CREATE POLICY tenant_isolation_evidence ON evidence
    USING (tenant_id = current_setting('app.current_tenant', true)::text);

CREATE POLICY tenant_isolation_evidence_embeddings ON evidence_embeddings
    USING (tenant_id = current_setting('app.current_tenant', true)::text);

CREATE POLICY tenant_isolation_verdicts ON verdicts
    USING (tenant_id = current_setting('app.current_tenant', true)::text);

CREATE POLICY tenant_isolation_verdict_evidence ON verdict_evidence
    USING (tenant_id = current_setting('app.current_tenant', true)::text);
```

**Set tenant context in application** (Python):

```python
async def set_tenant_context(conn, tenant_id: str):
    """Set current tenant for RLS policies"""
    await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

# Usage in request handler
async with db.acquire() as conn:
    await set_tenant_context(conn, tenant_id)
    # All queries in this connection are now tenant-scoped
    result = await conn.fetch("SELECT * FROM claims")
```

#### Partitioning by Tenant

**When to partition**: If you have >100 tenants and >10M claims.

**Partition strategy**:

```sql
-- Create partitioned table
CREATE TABLE claims_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    -- ... other columns
    PRIMARY KEY (tenant_id, id)  -- Partition key must be in PK
) PARTITION BY HASH (tenant_id);

-- Create partitions (e.g., 16 partitions)
CREATE TABLE claims_partition_0 PARTITION OF claims_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);

CREATE TABLE claims_partition_1 PARTITION OF claims_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);

-- ... repeat for partitions 2-15
```

**Trade-offs**:
- **Pro**: Query performance (only scans relevant partitions)
- **Pro**: Easier tenant data deletion (drop partition)
- **Con**: More complex migrations
- **Con**: Requires partition key in all queries

### What Stays the Same

**No breaking changes**:
- Core table structure (claims, evidence, verdicts schema)
- API contracts (endpoints, request/response formats)
- UUID primary keys
- JSONB metadata columns
- pgvector embeddings (can keep using same model)

**Migration is additive**:
- Add columns (tenant_id)
- Add indexes (tenant-scoped composites)
- Add policies (RLS)
- No data rewrites required

### What Changes in v1

**Application layer**:
- Extract tenant_id from JWT/API key
- Pass tenant_id to all queries
- Filter all queries by tenant_id

**Example query changes**:

**v0 (single-tenant)**:
```sql
SELECT * FROM claims WHERE id = $1;
```

**v1 (multi-tenant)**:
```sql
SELECT * FROM claims WHERE id = $1 AND tenant_id = $2;
```

**v1 with RLS** (tenant_id implicit):
```sql
-- Set tenant context first
SET LOCAL app.current_tenant = 'tenant_abc';

-- Query (RLS filters automatically)
SELECT * FROM claims WHERE id = $1;
```

---

## Sample Data

### Sample SQL Inserts for Testing

#### Sample Claims

```sql
-- Insert sample claims
INSERT INTO claims (id, text, source_url, metadata) VALUES
(
    '550e8400-e29b-41d4-a716-446655440001',
    'The Earth is approximately spherical in shape',
    'https://en.wikipedia.org/wiki/Earth',
    '{"language": "en", "domain": "science", "priority": "normal"}'::jsonb
),
(
    '550e8400-e29b-41d4-a716-446655440002',
    'Vaccines cause autism',
    'https://example.com/misinformation',
    '{"language": "en", "domain": "health", "priority": "high", "flagged": true}'::jsonb
),
(
    '550e8400-e29b-41d4-a716-446655440003',
    'Climate change is primarily caused by human activities',
    'https://www.ipcc.ch/',
    '{"language": "en", "domain": "climate", "priority": "high"}'::jsonb
),
(
    '550e8400-e29b-41d4-a716-446655440004',
    'The Great Wall of China is visible from space',
    NULL,
    '{"language": "en", "domain": "geography", "priority": "low"}'::jsonb
);
```

#### Sample Evidence

```sql
-- Insert sample evidence documents
INSERT INTO evidence (id, content, source_url, source_type, published_at, metadata) VALUES
(
    '660e8400-e29b-41d4-a716-446655440001',
    'Earth is the third planet from the Sun and the only astronomical object known to harbor life. While large volumes of water can be found throughout the Solar System, only Earth sustains liquid surface water. About 71% of Earth''s surface is made up of the ocean. The remaining 29% is land consisting of continents and islands. Earth is roughly spherical in shape, with a slight bulge at the equator.',
    'https://en.wikipedia.org/wiki/Earth',
    'wikipedia',
    '2025-01-01 00:00:00+00',
    '{"title": "Earth", "section": "Overview", "language": "en"}'::jsonb
),
(
    '660e8400-e29b-41d4-a716-446655440002',
    'The MMR vaccine has been extensively studied and is not associated with an increased risk of autism. A comprehensive review by the Institute of Medicine found no credible evidence linking vaccines to autism. Multiple large-scale studies involving millions of children have consistently shown no connection between vaccines and autism spectrum disorders.',
    'https://www.cdc.gov/vaccinesafety/concerns/autism.html',
    'scientific_paper',
    '2024-03-15 00:00:00+00',
    '{"author": "CDC", "title": "Vaccine Safety", "language": "en"}'::jsonb
),
(
    '660e8400-e29b-41d4-a716-446655440003',
    'The Intergovernmental Panel on Climate Change (IPCC) has concluded with high confidence that human influence has been the dominant cause of observed warming since the mid-20th century. The burning of fossil fuels, deforestation, and industrial activities have increased greenhouse gas concentrations in the atmosphere, leading to a warming effect.',
    'https://www.ipcc.ch/report/ar6/wg1/',
    'scientific_paper',
    '2021-08-09 00:00:00+00',
    '{"author": "IPCC", "report": "AR6 WG1", "language": "en"}'::jsonb
),
(
    '660e8400-e29b-41d4-a716-446655440004',
    'The Great Wall of China is NOT visible from space with the naked eye. This is a common misconception. Astronauts have reported that the Wall is very difficult to see from low Earth orbit, and impossible to see from the Moon. The claim likely originated from a misinterpretation of statements about what can be seen from space under ideal conditions with magnification.',
    'https://www.nasa.gov/vision/space/workinginspace/great_wall.html',
    'article',
    '2005-05-01 00:00:00+00',
    '{"author": "NASA", "title": "Great Wall of China Visibility from Space", "language": "en"}'::jsonb
);
```

#### Sample Embeddings (Placeholder)

```sql
-- Insert sample embeddings (use actual embeddings from your model)
-- These are placeholder vectors; replace with real embeddings from all-MiniLM-L6-v2

INSERT INTO evidence_embeddings (evidence_id, embedding, model_name) VALUES
(
    '660e8400-e29b-41d4-a716-446655440001',
    '[' || array_to_string(array_fill(0.0::float, ARRAY[384]), ',') || ']'::vector,
    'all-MiniLM-L6-v2'
),
(
    '660e8400-e29b-41d4-a716-446655440002',
    '[' || array_to_string(array_fill(0.0::float, ARRAY[384]), ',') || ']'::vector,
    'all-MiniLM-L6-v2'
),
(
    '660e8400-e29b-41d4-a716-446655440003',
    '[' || array_to_string(array_fill(0.0::float, ARRAY[384]), ',') || ']'::vector,
    'all-MiniLM-L6-v2'
),
(
    '660e8400-e29b-41d4-a716-446655440004',
    '[' || array_to_string(array_fill(0.0::float, ARRAY[384]), ',') || ']'::vector,
    'all-MiniLM-L6-v2'
);

-- Note: To generate real embeddings, use Python:
-- from sentence_transformers import SentenceTransformer
-- model = SentenceTransformer('all-MiniLM-L6-v2')
-- embedding = model.encode("Your text here").tolist()
```

#### Sample Verdicts

```sql
-- Insert sample verdicts
INSERT INTO verdicts (id, claim_id, verdict, confidence, reasoning, evidence_count) VALUES
(
    '770e8400-e29b-41d4-a716-446655440001',
    '550e8400-e29b-41d4-a716-446655440001',
    'SUPPORTED',
    0.95,
    'The claim that Earth is approximately spherical is strongly supported by scientific evidence. Multiple authoritative sources confirm Earth''s spherical shape with a slight equatorial bulge.',
    1
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    '550e8400-e29b-41d4-a716-446655440002',
    'REFUTED',
    0.98,
    'The claim that vaccines cause autism has been thoroughly debunked by extensive scientific research. Multiple large-scale studies involving millions of children have found no causal link between vaccines and autism spectrum disorders.',
    1
),
(
    '770e8400-e29b-41d4-a716-446655440003',
    '550e8400-e29b-41d4-a716-446655440003',
    'SUPPORTED',
    0.92,
    'The claim is supported by authoritative scientific consensus. The IPCC and numerous climate scientists have concluded with high confidence that human activities are the dominant cause of recent climate change.',
    1
),
(
    '770e8400-e29b-41d4-a716-446655440004',
    '550e8400-e29b-41d4-a716-446655440004',
    'REFUTED',
    0.89,
    'The claim is refuted by NASA and astronaut testimony. The Great Wall of China is not visible from space with the naked eye, contrary to popular belief.',
    1
);
```

#### Sample Verdict-Evidence Links

```sql
-- Insert verdict-evidence relationships
INSERT INTO verdict_evidence (verdict_id, evidence_id, relationship, confidence, nli_label, nli_score) VALUES
(
    '770e8400-e29b-41d4-a716-446655440001',
    '660e8400-e29b-41d4-a716-446655440001',
    'supports',
    0.95,
    'entailment',
    0.95
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    '660e8400-e29b-41d4-a716-446655440002',
    'refutes',
    0.98,
    'contradiction',
    0.98
),
(
    '770e8400-e29b-41d4-a716-446655440003',
    '660e8400-e29b-41d4-a716-446655440003',
    'supports',
    0.92,
    'entailment',
    0.92
),
(
    '770e8400-e29b-41d4-a716-446655440004',
    '660e8400-e29b-41d4-a716-446655440004',
    'refutes',
    0.89,
    'contradiction',
    0.89
);
```

### Evidence Corpus Structure

**For bulk loading**:

**CSV format** (`corpus.csv`):
```csv
content,source_url,source_type,published_at,metadata
"Earth is roughly spherical...","https://en.wikipedia.org/wiki/Earth","wikipedia","2025-01-01","{""title"": ""Earth""}"
"The MMR vaccine has been extensively studied...","https://www.cdc.gov/","scientific_paper","2024-03-15","{""author"": ""CDC""}"
```

**JSONL format** (`corpus.jsonl`):
```jsonl
{"content": "Earth is roughly spherical...", "source_url": "https://en.wikipedia.org/wiki/Earth", "source_type": "wikipedia", "metadata": {"title": "Earth"}}
{"content": "The MMR vaccine has been extensively studied...", "source_url": "https://www.cdc.gov/", "source_type": "scientific_paper", "metadata": {"author": "CDC"}}
```

**Bulk loading script** (`scripts/load_corpus.py`):

```python
import json
import asyncpg
from sentence_transformers import SentenceTransformer

async def load_corpus(file_path: str):
    conn = await asyncpg.connect('postgresql://truthgraph:password@localhost:5432/truthgraph')
    model = SentenceTransformer('all-MiniLM-L6-v2')

    with open(file_path) as f:
        for line in f:
            doc = json.loads(line)

            # Insert evidence
            evidence_id = await conn.fetchval("""
                INSERT INTO evidence (content, source_url, source_type, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, doc['content'], doc.get('source_url'), doc.get('source_type'), json.dumps(doc.get('metadata', {})))

            # Generate and insert embedding
            embedding = model.encode(doc['content']).tolist()
            await conn.execute("""
                INSERT INTO evidence_embeddings (evidence_id, embedding)
                VALUES ($1, $2)
            """, evidence_id, embedding)

    await conn.close()
```

### Test Claims with Known Verdicts

**For end-to-end testing**:

```python
TEST_CLAIMS = [
    {
        "text": "The Earth is approximately spherical",
        "expected_verdict": "SUPPORTED",
        "expected_confidence": ">0.8"
    },
    {
        "text": "Vaccines cause autism",
        "expected_verdict": "REFUTED",
        "expected_confidence": ">0.9"
    },
    {
        "text": "Climate change is caused by human activities",
        "expected_verdict": "SUPPORTED",
        "expected_confidence": ">0.8"
    },
    {
        "text": "The Great Wall of China is visible from space",
        "expected_verdict": "REFUTED",
        "expected_confidence": ">0.7"
    },
    {
        "text": "Water boils at 100 degrees Celsius at sea level",
        "expected_verdict": "SUPPORTED",
        "expected_confidence": ">0.9"
    },
]
```

---

## Conclusion

This comprehensive database schema documentation provides:

- **Technology rationale**: Why PostgreSQL + pgvector (and why NOT FAISS for MVP)
- **Complete schema**: All tables, columns, constraints, indexes
- **pgvector configuration**: Dimensions, index types, tuning parameters
- **Access patterns**: Common queries with SQL examples
- **Migration strategy**: Alembic setup, safe practices, Docker integration
- **Evolution path**: Clear upgrade to v1 multi-tenancy (additive changes only)
- **Sample data**: Test data for development and validation

**Next Steps**:
1. Review this schema with team
2. Create initial Alembic migration (`0001_initial_schema.py`)
3. Test schema with sample data
4. Integrate with FastAPI application
5. Benchmark query performance with realistic data volumes

**Related Documentation**:
- `docs/roadmap/v0/00_overview.md` - Project overview
- `docs/roadmap/v0/phase_01_foundation.md` - Implementation details
- `docs/roadmap/v1/phase_01_local_mvp.md` - v1 multi-tenant schema reference

---

**Document Version**: 1.0
**Schema Version**: v0 (single-tenant)
**PostgreSQL Version**: 16+
**pgvector Version**: 0.5.0+
