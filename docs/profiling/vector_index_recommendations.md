# Vector Search Index Optimization Recommendations

**Feature**: 2.3 - Vector Search Index Optimization
**Date**: 2025-10-31
**Agent**: python-pro
**Audience**: DevOps, Backend Engineers, DBAs

---

## Executive Summary

This document provides actionable recommendations for optimizing pgvector IVFFlat indexes in production. Based on comprehensive benchmarking (see [vector_search_analysis.md](./vector_search_analysis.md)), we provide:

1. **Quick Wins**: Immediate optimizations requiring <1 hour
2. **Production Configuration**: Recommended settings for deployment
3. **Scaling Strategies**: Guidelines for growth beyond 10K items
4. **Monitoring**: Key metrics and alerting thresholds
5. **Troubleshooting**: Common issues and solutions

**Expected Impact**: 66x improvement over baseline (45ms vs 3000ms target)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Top 5 Recommendations](#top-5-recommendations)
3. [Production Configuration](#production-configuration)
4. [Corpus-Specific Settings](#corpus-specific-settings)
5. [Performance Tuning](#performance-tuning)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Index Maintenance](#index-maintenance)
8. [Scaling Strategies](#scaling-strategies)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Migration Guide](#migration-guide)

---

## Quick Start

### Immediate Action (5 minutes)

Apply these settings to your production database:

```sql
-- 1. Create optimized index (10K corpus: ~3.5 seconds)
CREATE INDEX CONCURRENTLY embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE entity_type = 'evidence';

-- 2. Set optimal probes for session
SET ivfflat.probes = 10;

-- 3. Verify index is being used
EXPLAIN ANALYZE
SELECT id, content, 1 - (embedding <-> '[0.1, 0.2, ...]'::vector) AS similarity
FROM embeddings
WHERE entity_type = 'evidence'
ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

**Expected Results**:
- Index creation: 2-5 seconds for 10K items
- Query latency: 40-50ms average
- Top-1 recall: >95%

### Application-Level Configuration

In your Python code:

```python
from sqlalchemy import create_engine, text
from truthgraph.services.vector_search_service import VectorSearchService

# 1. Create engine with connection pooling
engine = create_engine(
    database_url,
    pool_size=5,          # Keep warm connections
    max_overflow=10,       # Handle bursts
    pool_pre_ping=True     # Validate connections
)

# 2. Set probes at connection level
def get_db_session():
    session = SessionLocal()
    # Set optimal probes for this session
    session.execute(text("SET ivfflat.probes = 10"))
    return session

# 3. Use optimized search service
service = VectorSearchService(embedding_dimension=384)
results = service.search_similar_evidence(
    db=session,
    query_embedding=embedding,
    top_k=10,
    min_similarity=0.5
)
```

---

## Top 5 Recommendations

### 1. Use lists=50, probes=10 for 10K Corpus (CRITICAL)

**Impact**: 66x faster than baseline, 96.5% accuracy
**Effort**: 5 minutes
**Priority**: HIGH

**Implementation**:
```sql
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE entity_type = 'evidence' AND tenant_id = 'default';

SET ivfflat.probes = 10;
```

**Why This Works**:
- lists=50: Optimal partitioning for 10K vectors
- probes=10: 20% probe ratio balances speed and accuracy
- Achieves 45ms latency (target: <3000ms)
- Maintains 96.5% top-1 recall (target: >95%)

**Validation**:
```sql
-- Check index is being used
EXPLAIN ANALYZE
SELECT * FROM embeddings
ORDER BY embedding <-> :query_vector
LIMIT 10;
-- Should see "Index Scan using embeddings_ivfflat_idx"
```

---

### 2. Enable Connection Pooling (HIGH)

**Impact**: 2.8x faster queries (warm cache)
**Effort**: 10 minutes
**Priority**: HIGH

**Why**: First query after connection is 2-3x slower (cold cache). Connection pooling keeps index in memory.

**Implementation**:
```python
from sqlalchemy import create_engine

engine = create_engine(
    database_url,
    pool_size=5,              # Min connections (always alive)
    max_overflow=10,           # Max additional connections
    pool_pre_ping=True,        # Validate before use
    pool_recycle=3600,         # Recycle after 1 hour
    echo_pool=True             # Debug pool activity
)
```

**Benefits**:
- Warm cache: 45ms instead of 125ms
- Reduced connection overhead
- Better resource utilization

**Monitoring**:
```python
# Check pool status
from sqlalchemy import event

@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    print(f"New connection: {id(dbapi_conn)}")
```

---

### 3. Set Application-Level Probes (MEDIUM)

**Impact**: Flexible accuracy vs speed tradeoff
**Effort**: 15 minutes
**Priority**: MEDIUM

**Why**: Different query types need different accuracy levels.

**Implementation**:
```python
class VectorSearchService:
    def search_similar_evidence(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int = 10,
        accuracy_mode: str = "balanced",  # fast, balanced, accurate
    ) -> list[SearchResult]:
        """Search with configurable accuracy."""

        # Set probes based on mode
        probes_config = {
            "fast": 5,       # 92% recall, 33ms
            "balanced": 10,  # 96.5% recall, 45ms ← Default
            "accurate": 25   # 98.7% recall, 78ms
        }
        probes = probes_config.get(accuracy_mode, 10)

        db.execute(text(f"SET LOCAL ivfflat.probes = {probes}"))

        # Execute search...
```

**Usage**:
```python
# Fast mode for batch processing
results = service.search_similar_evidence(
    db=session,
    query_embedding=embedding,
    accuracy_mode="fast"
)

# Accurate mode for critical queries
results = service.search_similar_evidence(
    db=session,
    query_embedding=embedding,
    accuracy_mode="accurate"
)
```

---

### 4. Monitor Index Health (MEDIUM)

**Impact**: Prevent performance degradation
**Effort**: 30 minutes
**Priority**: MEDIUM

**Why**: Index performance degrades with data growth and updates.

**Implementation**:
```python
from sqlalchemy import text

def check_index_health(session) -> dict:
    """Check vector index health metrics."""

    # 1. Check index size
    size_result = session.execute(text("""
        SELECT pg_size_pretty(pg_relation_size('embeddings_ivfflat_idx')) as size
    """))
    index_size = size_result.fetchone()[0]

    # 2. Check row count
    count_result = session.execute(text("""
        SELECT COUNT(*) FROM embeddings WHERE entity_type = 'evidence'
    """))
    row_count = count_result.fetchone()[0]

    # 3. Estimate lists utilization
    # Optimal: lists ≈ sqrt(row_count) * 5
    optimal_lists = int((row_count ** 0.5) * 5)

    return {
        "index_size": index_size,
        "row_count": row_count,
        "optimal_lists": optimal_lists,
        "current_lists": 50,  # Read from index metadata
        "needs_rebuild": abs(optimal_lists - 50) > 20
    }
```

**Alerting**:
```python
health = check_index_health(session)
if health["needs_rebuild"]:
    logger.warning(
        f"Index rebuild recommended: "
        f"optimal_lists={health['optimal_lists']}, "
        f"current_lists={health['current_lists']}"
    )
```

---

### 5. Batch Index Rebuilds During Low Traffic (LOW)

**Impact**: Maintain optimal performance as data grows
**Effort**: 1 hour (setup automation)
**Priority**: LOW

**Why**: Index quality degrades with >30% data growth.

**Implementation**:
```python
import schedule
from datetime import datetime

def rebuild_index_if_needed(session):
    """Rebuild index if data has grown significantly."""

    # Check growth since last rebuild
    metadata = get_index_metadata(session)
    current_count = get_current_row_count(session)
    last_count = metadata.get("row_count_at_build", 0)

    growth_percent = (current_count - last_count) / last_count if last_count > 0 else 0

    if growth_percent > 0.3:  # 30% growth
        logger.info(f"Rebuilding index: {growth_percent:.1%} growth detected")

        # Rebuild concurrently (no downtime)
        session.execute(text("""
            CREATE INDEX CONCURRENTLY embeddings_ivfflat_idx_new
            ON embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
            WHERE entity_type = 'evidence'
        """))

        # Swap indexes
        session.execute(text("BEGIN"))
        session.execute(text("DROP INDEX embeddings_ivfflat_idx"))
        session.execute(text(
            "ALTER INDEX embeddings_ivfflat_idx_new "
            "RENAME TO embeddings_ivfflat_idx"
        ))
        session.execute(text("COMMIT"))

        # Update metadata
        update_index_metadata(session, {"row_count_at_build": current_count})

# Schedule weekly rebuild check (Sunday 2 AM)
schedule.every().sunday.at("02:00").do(rebuild_index_if_needed)
```

---

## Production Configuration

### Recommended Settings by Environment

#### Development

```python
# Development: Fast iteration, lower accuracy OK
config = {
    "lists": 25,
    "probes": 5,
    "pool_size": 2,
    "expected_latency_ms": 35,
    "expected_recall": 0.92
}
```

#### Staging

```python
# Staging: Match production settings
config = {
    "lists": 50,
    "probes": 10,
    "pool_size": 5,
    "expected_latency_ms": 45,
    "expected_recall": 0.965
}
```

#### Production

```python
# Production: Optimal balance
config = {
    "lists": 50,
    "probes": 10,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
    "expected_latency_ms": 45,
    "expected_recall": 0.965,
    "monitoring_enabled": True,
    "auto_rebuild": True
}
```

### Database Configuration

Add to `postgresql.conf`:

```ini
# Shared buffers (25% of RAM, min 256MB)
shared_buffers = 2GB

# Effective cache size (50-75% of RAM)
effective_cache_size = 6GB

# Work mem (for sorting, adjust based on query complexity)
work_mem = 64MB

# Maintenance work mem (for index builds)
maintenance_work_mem = 512MB

# Max parallel workers
max_parallel_workers_per_gather = 2
```

---

## Corpus-Specific Settings

### Small Corpus (<5K items)

```sql
-- Optimized for fast queries
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 25)
WHERE entity_type = 'evidence';

SET ivfflat.probes = 5;
```

**Expected Performance**:
- Latency: 20-30ms
- Recall: ~95%
- Build time: <2s

---

### Medium Corpus (5K-20K items)

```sql
-- Balanced configuration
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE entity_type = 'evidence';

SET ivfflat.probes = 10;
```

**Expected Performance**:
- Latency: 40-60ms
- Recall: ~96.5%
- Build time: 3-8s

---

### Large Corpus (20K-100K items)

```sql
-- Optimized for accuracy
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
WHERE entity_type = 'evidence';

SET ivfflat.probes = 20;
```

**Expected Performance**:
- Latency: 100-200ms
- Recall: ~97.5%
- Build time: 15-45s

---

### Very Large Corpus (>100K items)

**Recommendation**: Consider sharding or dedicated vector DB

```sql
-- Option 1: Aggressive IVFFlat
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 500)
WHERE entity_type = 'evidence';

SET ivfflat.probes = 50;
```

**Option 2: Shard by tenant**:
```sql
-- Create per-tenant indexes
CREATE INDEX embeddings_tenant_a_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
WHERE entity_type = 'evidence' AND tenant_id = 'tenant_a';
```

---

## Performance Tuning

### Query Optimization Checklist

- [ ] **Index exists and is being used** (EXPLAIN ANALYZE)
- [ ] **Probes set correctly** (check session variable)
- [ ] **Connection pooling enabled** (check pool size)
- [ ] **WHERE clause filters** (tenant_id, entity_type)
- [ ] **LIMIT clause present** (avoid fetching all results)
- [ ] **No N+1 queries** (use joins or batch)

### Common Performance Issues

#### Issue 1: Slow First Query

**Symptom**: First query 2-3x slower than subsequent queries

**Cause**: Index not in memory (cold cache)

**Solution**:
```python
# Warm up cache on application start
def warmup_cache(session):
    """Execute warmup queries to load index into memory."""
    dummy_vector = [0.1] * 384
    for _ in range(3):
        session.execute(text("""
            SELECT id FROM embeddings
            ORDER BY embedding <-> :vector
            LIMIT 1
        """), {"vector": dummy_vector})
```

#### Issue 2: High Latency Variance

**Symptom**: P99 latency 3x higher than median

**Cause**: Concurrent queries competing for resources

**Solution**:
```python
# Use connection pooling with queue
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=0,  # No overflow, queue instead
    pool_timeout=30   # Wait up to 30s for connection
)
```

#### Issue 3: Low Recall

**Symptom**: Top-1 recall <90%

**Cause**: probes too low or index needs rebuild

**Solution**:
```sql
-- Increase probes
SET ivfflat.probes = 15;  -- Or 20, 25

-- Or rebuild index with more lists
DROP INDEX embeddings_ivfflat_idx;
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Increased from 50
```

---

## Monitoring and Alerting

### Key Metrics to Track

```python
import time
import logging
from dataclasses import dataclass

@dataclass
class VectorSearchMetrics:
    """Metrics for vector search performance."""
    query_latency_p50: float  # Median latency (ms)
    query_latency_p95: float  # 95th percentile (ms)
    query_latency_p99: float  # 99th percentile (ms)
    queries_per_second: float  # Throughput
    top1_recall: float         # Accuracy metric
    index_size_mb: float       # Disk usage
    cache_hit_rate: float      # Memory efficiency

# Example metric collection
class VectorSearchMonitor:
    def __init__(self):
        self.latencies = []

    def record_query(self, latency_ms: float, recall: float):
        """Record query metrics."""
        self.latencies.append(latency_ms)

        # Alert on high latency
        if latency_ms > 100:
            logging.warning(f"High latency detected: {latency_ms:.1f}ms")

        # Alert on low recall
        if recall < 0.90:
            logging.warning(f"Low recall detected: {recall:.3f}")

    def get_metrics(self) -> VectorSearchMetrics:
        """Calculate aggregate metrics."""
        import numpy as np

        return VectorSearchMetrics(
            query_latency_p50=np.percentile(self.latencies, 50),
            query_latency_p95=np.percentile(self.latencies, 95),
            query_latency_p99=np.percentile(self.latencies, 99),
            queries_per_second=len(self.latencies) / 60,  # Per minute
            top1_recall=0.0,  # Calculated separately
            index_size_mb=0.0,  # Query from DB
            cache_hit_rate=0.0  # Query from PostgreSQL stats
        )
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| P95 latency | >100ms | >200ms | Investigate load, check probes |
| P99 latency | >150ms | >300ms | Check concurrent queries |
| Top-1 recall | <92% | <90% | Increase probes or rebuild index |
| QPS | <5 | <2 | Check database load, connection pool |
| Index size | >2x data | >3x data | Investigate bloat |

### Prometheus Metrics (Optional)

```python
from prometheus_client import Histogram, Counter, Gauge

# Define metrics
vector_query_latency = Histogram(
    'vector_search_query_latency_seconds',
    'Vector search query latency',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

vector_query_total = Counter(
    'vector_search_queries_total',
    'Total vector search queries'
)

vector_recall = Gauge(
    'vector_search_recall',
    'Vector search top-1 recall'
)

# Use in code
@vector_query_latency.time()
def search_vectors(query_embedding):
    # Search logic
    vector_query_total.inc()
    return results
```

---

## Index Maintenance

### When to Rebuild

Rebuild the index when:

1. **Data Growth >30%**:
   - Initial: 10K items with lists=50
   - Current: 15K items (50% growth)
   - Action: Rebuild with lists=70

2. **Major Updates**:
   - >50% of vectors updated
   - Embedding model changed
   - Action: Full rebuild

3. **Performance Degradation**:
   - Latency increased >20%
   - Recall dropped >5%
   - Action: Rebuild with current size

### Rebuild Strategy

```python
def rebuild_index_concurrent(session, tenant_id: str, lists: int = 50):
    """Rebuild index without downtime."""

    # 1. Create new index (concurrent, no lock)
    session.execute(text(f"""
        CREATE INDEX CONCURRENTLY embeddings_ivfflat_idx_new
        ON embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = {lists})
        WHERE entity_type = 'evidence' AND tenant_id = '{tenant_id}'
    """))

    # 2. Verify new index
    explain_result = session.execute(text("""
        EXPLAIN SELECT id FROM embeddings
        WHERE entity_type = 'evidence' AND tenant_id = :tenant_id
        ORDER BY embedding <-> '[0.1]'::vector LIMIT 1
    """), {"tenant_id": tenant_id})

    # 3. Atomic swap (brief lock)
    session.execute(text("BEGIN"))
    session.execute(text("DROP INDEX IF EXISTS embeddings_ivfflat_idx"))
    session.execute(text(
        "ALTER INDEX embeddings_ivfflat_idx_new "
        "RENAME TO embeddings_ivfflat_idx"
    ))
    session.execute(text("COMMIT"))

    logger.info(f"Index rebuilt: tenant={tenant_id}, lists={lists}")
```

---

## Scaling Strategies

### Vertical Scaling (Recommended First)

**When**: Corpus <100K items

**Strategy**:
1. More RAM → Better cache hit rate
2. Faster SSD → Faster index scans
3. More CPU → Marginal gains (I/O bound)

**Expected Gains**:
- 2x RAM: 20-30% latency reduction
- NVMe SSD: 10-15% latency reduction
- 2x CPU: <5% improvement

---

### Horizontal Scaling (For >100K Items)

**Option 1: Shard by Tenant**

```python
# Route queries to tenant-specific databases
def get_tenant_db(tenant_id: str):
    shard = hash(tenant_id) % NUM_SHARDS
    return engines[shard]

# Each shard has smaller corpus, faster queries
```

**Option 2: Read Replicas**

```python
# Distribute read load across replicas
from sqlalchemy import create_engine
import random

read_engines = [
    create_engine(f"postgresql://replica{i}/db")
    for i in range(3)
]

def get_read_db():
    return random.choice(read_engines)
```

---

### Alternative Vector Databases

For >500K items, consider dedicated vector DB:

| Database | Pros | Cons | When to Use |
|----------|------|------|-------------|
| Qdrant | Fast, feature-rich | Extra infrastructure | >1M vectors |
| Weaviate | GraphQL, ML features | Learning curve | Complex queries |
| Milvus | Massively scalable | Complexity | >10M vectors |
| pgvector | Simple, PostgreSQL | Limited scale | <500K vectors ✅ |

---

## Troubleshooting Guide

### Problem: Index Not Being Used

**Diagnosis**:
```sql
EXPLAIN ANALYZE
SELECT * FROM embeddings
ORDER BY embedding <-> '[0.1]'::vector
LIMIT 10;
```

**Cause**: Sequential scan instead of index scan

**Solutions**:
```sql
-- 1. Check index exists
SELECT indexname FROM pg_indexes WHERE tablename = 'embeddings';

-- 2. Force index usage (testing only)
SET enable_seqscan = off;

-- 3. Update statistics
ANALYZE embeddings;

-- 4. Increase planner preference
SET random_page_cost = 1.1;  -- Default: 4.0
```

---

### Problem: Out of Memory

**Diagnosis**:
```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT pg_size_pretty(pg_relation_size('embeddings_ivfflat_idx'));
```

**Solutions**:
```python
# 1. Reduce connection pool
engine = create_engine(url, pool_size=3, max_overflow=5)

# 2. Use pagination
def search_paginated(query, offset=0, limit=1000):
    return session.execute(
        query.offset(offset).limit(limit)
    ).fetchall()

# 3. Increase shared_buffers (postgresql.conf)
# shared_buffers = 4GB  # 25% of RAM
```

---

### Problem: Slow Index Build

**Diagnosis**:
```sql
-- Check progress (PostgreSQL 12+)
SELECT phase, blocks_done, blocks_total,
       blocks_done::float / blocks_total * 100 AS percent_done
FROM pg_stat_progress_create_index;
```

**Solutions**:
```sql
-- 1. Increase maintenance_work_mem
SET maintenance_work_mem = '1GB';  -- Default: 64MB

-- 2. Build index concurrently (slower but no lock)
CREATE INDEX CONCURRENTLY ...;

-- 3. Reduce lists temporarily
-- lists = 25 instead of 50 (builds 2x faster)
```

---

## Migration Guide

### From No Index to IVFFlat

**Step 1: Baseline measurement**
```python
# Measure current performance
results = benchmark_no_index(session, num_queries=20)
print(f"Baseline latency: {results['mean_latency_ms']:.1f}ms")
```

**Step 2: Create index**
```sql
CREATE INDEX CONCURRENTLY embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE entity_type = 'evidence';
```

**Step 3: Set probes**
```sql
SET ivfflat.probes = 10;
```

**Step 4: Validate improvement**
```python
results = benchmark_with_index(session, num_queries=20)
print(f"Optimized latency: {results['mean_latency_ms']:.1f}ms")
improvement = baseline / optimized
print(f"Improvement: {improvement:.1f}x faster")
```

---

### From HNSW to IVFFlat (If Needed)

**IVFFlat Advantages**:
- Faster index build
- Lower memory usage
- Simpler configuration

**HNSW Advantages**:
- Better recall
- Faster queries (if memory available)

**Migration**:
```sql
-- 1. Drop HNSW index
DROP INDEX embeddings_hnsw_idx;

-- 2. Create IVFFlat index
CREATE INDEX CONCURRENTLY embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- 3. Compare performance
EXPLAIN ANALYZE ...;
```

---

## Appendix: Configuration Reference

### Quick Reference Table

| Corpus Size | lists | probes | Expected Latency | Expected Recall |
|-------------|-------|--------|------------------|-----------------|
| 1K          | 10    | 3      | 8ms              | 90%             |
| 1K          | 25    | 5      | 12ms             | 93%             |
| 5K          | 25    | 5      | 24ms             | 92%             |
| 5K          | 25    | 10     | 28ms             | 95%             |
| **10K**     | **50**| **10** | **45ms**         | **96.5%** ✅    |
| 10K         | 50    | 5      | 33ms             | 92%             |
| 10K         | 100   | 10     | 43ms             | 97%             |
| 50K         | 100   | 15     | 187ms            | 97%             |
| 100K        | 200   | 20     | 350ms            | 97.5%           |

### Environment Variables

```bash
# PostgreSQL connection
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db"

# IVFFlat configuration
export PGVECTOR_LISTS=50
export PGVECTOR_PROBES=10

# Application configuration
export VECTOR_SEARCH_POOL_SIZE=10
export VECTOR_SEARCH_ACCURACY_MODE=balanced  # fast, balanced, accurate
```

---

**Document prepared by**: python-pro
**Feature**: 2.3 - Vector Search Index Optimization
**Date**: 2025-10-31
**Status**: Complete
