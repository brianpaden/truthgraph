# Phase 2 Migration - Quick Start Guide

## Prerequisites

1. PostgreSQL 15+ with pgvector extension (included in `pgvector/pgvector:pg16` Docker image)
2. Alembic installed: `uv pip install alembic pgvector asyncpg`
3. Backup of existing database (recommended)

## Quick Migration Steps

### 1. Backup Database (Recommended)

```bash
# Create backup
docker-compose exec postgres pg_dump -U truthgraph truthgraph > backup_$(date +%Y%m%d).sql
```

### 2. Run Migration

```bash
# Using Alembic directly
alembic upgrade head

# Or using Docker Compose
docker-compose exec api alembic upgrade head
```

### 3. Verify Migration

```bash
# Check current version
alembic current

# Run tests
pytest tests/test_migrations.py -v
```

### 4. Verify Tables Created

```sql
-- Connect to database
docker-compose exec postgres psql -U truthgraph truthgraph

-- Check tables
\dt

-- Verify pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Verify indexes
\di+ idx_embeddings_vector_cosine
```

## Rollback (If Needed)

```bash
# Rollback to previous version
alembic downgrade -1

# Verify rollback
alembic current
```

## What Was Created

- ✓ `embeddings` table - Vector embeddings with IVFFlat index
- ✓ `nli_results` table - NLI verification pairs
- ✓ `verification_results` table - Aggregated verdicts
- ✓ Indexes for performance
- ✓ Foreign key constraints
- ✓ Triggers for updated_at timestamps

## Next Steps

1. Install ML dependencies: `uv pip install -e ".[ml]"`
2. Implement embedding generation: See `truthgraph/ml/embeddings.py`
3. Implement NLI verification: See `truthgraph/ml/verification.py`
4. Build verification pipeline: See `truthgraph/verification/pipeline.py`

## Troubleshooting

**pgvector not found**:
- Ensure using `pgvector/pgvector:pg16` Docker image
- Or manually install: <https://github.com/pgvector/pgvector>

**Migration timeout**:
```sql
SET statement_timeout = '10min';
```

**Full documentation**: See `docs/PHASE2_DATABASE_MIGRATION.md`
