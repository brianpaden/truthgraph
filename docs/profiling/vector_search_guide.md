# Vector Search Usage Guide

**Feature**: 2.3 - Vector Search Index Optimization
**Date**: 2025-10-31
**Audience**: Backend Developers, ML Engineers
**Difficulty**: Beginner to Intermediate

---

## Overview

This guide shows you how to use TruthGraph's optimized vector search functionality with pgvector IVFFlat indexes. You'll learn to:

1. Execute basic vector similarity searches
2. Configure index parameters for your use case
3. Optimize for different accuracy/speed requirements
4. Monitor and troubleshoot performance
5. Run benchmarks and profiling

**Prerequisites**:
- PostgreSQL 15+ with pgvector extension installed
- Python 3.12+ with truthgraph package
- Basic understanding of vector embeddings

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Configuration](#advanced-configuration)
4. [Running Benchmarks](#running-benchmarks)
5. [Performance Optimization](#performance-optimization)
6. [Common Scenarios](#common-scenarios)
7. [API Reference](#api-reference)
8. [FAQ](#faq)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install PostgreSQL with pgvector
sudo apt-get install postgresql-15 postgresql-15-pgvector

# Or using Docker
docker run -d \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  ankane/pgvector
```

### 2. Create Index

```sql
-- Connect to database
psql postgresql://localhost/truthgraph

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create optimized index (10K corpus)
CREATE INDEX embeddings_ivfflat_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE entity_type = 'evidence';
```

### 3. Use in Python

```python
from truthgraph.db import SessionLocal
from truthgraph.services.vector_search_service import VectorSearchService
from sqlalchemy import text

# Initialize service
service = VectorSearchService(embedding_dimension=384)

# Get database session
session = SessionLocal()

# Set optimal probes
session.execute(text("SET ivfflat.probes = 10"))

# Generate or load query embedding
query_embedding = [0.1, 0.2, 0.3, ...]  # 384-dimensional vector

# Search for similar evidence
results = service.search_similar_evidence(
    db=session,
    query_embedding=query_embedding,
    top_k=10,
    min_similarity=0.5
)

# Process results
for result in results:
    print(f"Similarity: {result.similarity:.3f}")
    print(f"Content: {result.content[:100]}...")
    print(f"URL: {result.source_url}")
    print()

session.close()
```

---

## Basic Usage

### Searching for Similar Evidence

```python
from truthgraph.services.vector_search_service import VectorSearchService
from truthgraph.db import SessionLocal

# Initialize
service = VectorSearchService(embedding_dimension=384)
session = SessionLocal()

# Search
results = service.search_similar_evidence(
    db=session,
    query_embedding=query_vector,  # Your 384-dim vector
    top_k=10,                       # Return top 10 results
    min_similarity=0.5,             # Filter by similarity threshold
    tenant_id="default",            # Multi-tenancy support
)

# Results are ordered by similarity (highest first)
for i, result in enumerate(results, 1):
    print(f"{i}. [{result.similarity:.3f}] {result.content}")
```

### Batch Queries

For multiple queries at once:

```python
# Multiple query embeddings
query_embeddings = [
    embedding1,  # 384-dim vector
    embedding2,
    embedding3,
]

# Batch search
batch_results = service.search_similar_evidence_batch(
    db=session,
    query_embeddings=query_embeddings,
    top_k=5,
    tenant_id="default"
)

# Process each query's results
for query_idx, results in enumerate(batch_results):
    print(f"\nQuery {query_idx + 1} results:")
    for result in results:
        print(f"  - {result.similarity:.3f}: {result.content[:50]}...")
```

### Getting Embedding Statistics

```python
# Check corpus statistics
stats = service.get_embedding_stats(
    db=session,
    entity_type="evidence",
    tenant_id="default"
)

print(f"Total embeddings: {stats['total_embeddings']}")
print(f"Has null embeddings: {stats['has_null_embeddings']}")
print(f"Null count: {stats['null_embedding_count']}")
```

---

## Advanced Configuration

### Configuring Probes for Accuracy vs Speed

```python
from sqlalchemy import text

def search_with_accuracy_mode(session, query_embedding, mode="balanced"):
    """Search with different accuracy modes."""

    # Configure probes based on mode
    probes_config = {
        "fast": 5,       # 33ms, 92% recall
        "balanced": 10,  # 45ms, 96.5% recall (recommended)
        "accurate": 25,  # 78ms, 98.7% recall
    }

    probes = probes_config.get(mode, 10)
    session.execute(text(f"SET LOCAL ivfflat.probes = {probes}"))

    # Execute search
    service = VectorSearchService(embedding_dimension=384)
    return service.search_similar_evidence(
        db=session,
        query_embedding=query_embedding,
        top_k=10
    )

# Usage
results_fast = search_with_accuracy_mode(session, query, mode="fast")
results_accurate = search_with_accuracy_mode(session, query, mode="accurate")
```

### Dynamic Index Selection

For multi-tenant applications with varying corpus sizes:

```python
def get_optimal_config(corpus_size: int) -> dict:
    """Get optimal index configuration for corpus size."""

    if corpus_size < 5000:
        return {"lists": 25, "probes": 5}
    elif corpus_size < 20000:
        return {"lists": 50, "probes": 10}
    elif corpus_size < 100000:
        return {"lists": 100, "probes": 15}
    else:
        return {"lists": 200, "probes": 20}

# Get corpus size
count = session.execute(
    text("SELECT COUNT(*) FROM embeddings WHERE tenant_id = :tid"),
    {"tid": tenant_id}
).scalar()

# Apply optimal configuration
config = get_optimal_config(count)
session.execute(text(f"SET ivfflat.probes = {config['probes']}"))
```

### Connection Pooling for Performance

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create engine with pooling
engine = create_engine(
    "postgresql+psycopg://user:pass@localhost/truthgraph",
    pool_size=10,           # Keep 10 connections warm
    max_overflow=20,        # Allow 20 additional connections
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True      # Validate connections before use
)

SessionLocal = sessionmaker(bind=engine)

# Get session with warm cache
def get_db():
    session = SessionLocal()
    # Set probes for this session
    session.execute(text("SET ivfflat.probes = 10"))
    return session
```

---

## Running Benchmarks

### Basic Benchmark

Test vector search performance:

```bash
cd scripts/benchmarks

# Basic benchmark (default: 1K, 5K, 10K corpus)
python benchmark_vector_search.py

# Custom corpus sizes
python benchmark_vector_search.py --corpus-sizes 5000,10000,20000

# Test with 1536-dim embeddings
python benchmark_vector_search.py --embedding-dim 1536
```

### Index Parameter Optimization

Find optimal lists and probes for your data:

```bash
# Full optimization run
python index_optimization.py \
  --corpus-sizes 10000 \
  --lists 10,25,50,100 \
  --probes 1,5,10,25

# Quick test
python index_optimization.py \
  --corpus-sizes 5000 \
  --lists 25,50 \
  --probes 5,10
```

### Benchmark with Index Parameters

```bash
# Test specific index configurations
python benchmark_vector_search.py \
  --test-index-params \
  --lists 25,50,100 \
  --probes 5,10,15 \
  --corpus-sizes 10000
```

### Output Files

Results are saved to `scripts/benchmarks/results/`:

```bash
# JSON results
results/vector_search_2025-10-31.json
results/index_params_2025-10-31.json

# CSV results
results/search_latency_2025-10-31.csv
```

### Analyzing Results

```python
import json
import pandas as pd

# Load JSON results
with open("results/vector_search_2025-10-31.json") as f:
    results = json.load(f)

# Extract corpus size performance
corpus_results = results["benchmarks"]["corpus_sizes"]["corpus_results"]
df = pd.DataFrame(corpus_results)

print(df[["corpus_size", "mean_query_ms", "median_query_ms"]])

# Load CSV results
latency_df = pd.read_csv("results/search_latency_2025-10-31.csv")

# Plot latency vs corpus size
import matplotlib.pyplot as plt
plt.plot(latency_df["corpus_size"], latency_df["mean_latency_ms"])
plt.xlabel("Corpus Size")
plt.ylabel("Latency (ms)")
plt.title("Search Latency vs Corpus Size")
plt.show()
```

---

## Performance Optimization

### Warmup Cache

Avoid slow first query:

```python
def warmup_vector_cache(session):
    """Warmup query cache with dummy searches."""
    dummy_vector = [0.1] * 384

    for _ in range(3):
        session.execute(
            text("""
                SELECT id FROM embeddings
                WHERE entity_type = 'evidence'
                ORDER BY embedding <-> :vector
                LIMIT 1
            """),
            {"vector": dummy_vector}
        )

# Call on application startup
warmup_vector_cache(session)
```

### Monitoring Performance

```python
import time
from contextlib import contextmanager

@contextmanager
def measure_query_time(operation: str):
    """Context manager to measure query time."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        print(f"{operation}: {duration_ms:.1f}ms")

# Usage
with measure_query_time("Vector search"):
    results = service.search_similar_evidence(
        db=session,
        query_embedding=query_vector,
        top_k=10
    )
```

### Profiling Queries

```sql
-- Enable query timing
\timing on

-- Analyze query plan
EXPLAIN ANALYZE
SELECT id, content, 1 - (embedding <-> '[0.1]'::vector) AS similarity
FROM embeddings
WHERE entity_type = 'evidence'
ORDER BY embedding <-> '[0.1]'::vector
LIMIT 10;

-- Should show:
-- "Index Scan using embeddings_ivfflat_idx on embeddings"
-- Execution Time: ~45ms
```

---

## Common Scenarios

### Scenario 1: Real-Time Search (Low Latency)

**Goal**: Sub-50ms latency, acceptable accuracy

```python
# Configuration
session.execute(text("SET ivfflat.probes = 5"))

# Fast search
results = service.search_similar_evidence(
    db=session,
    query_embedding=query_vector,
    top_k=10,
    min_similarity=0.6  # Higher threshold for speed
)

# Expected: ~33ms latency, ~92% recall
```

### Scenario 2: Batch Processing (High Throughput)

**Goal**: Process 1000s of queries efficiently

```python
# Use batching
batch_size = 100
query_batches = [
    query_embeddings[i:i+batch_size]
    for i in range(0, len(query_embeddings), batch_size)
]

all_results = []
for batch in query_batches:
    batch_results = service.search_similar_evidence_batch(
        db=session,
        query_embeddings=batch,
        top_k=5
    )
    all_results.extend(batch_results)

# Process ~20 queries/second
```

### Scenario 3: High-Accuracy Search

**Goal**: Maximum recall, latency acceptable

```python
# Configuration for accuracy
session.execute(text("SET ivfflat.probes = 25"))

# Accurate search
results = service.search_similar_evidence(
    db=session,
    query_embedding=query_vector,
    top_k=20,           # Get more results
    min_similarity=0.3  # Lower threshold
)

# Expected: ~78ms latency, ~98.7% recall
```

### Scenario 4: Multi-Tenant Application

**Goal**: Isolated search per tenant

```python
def search_for_tenant(tenant_id: str, query_embedding: list[float]):
    """Search within specific tenant's data."""

    # Tenant-specific corpus size might vary
    count = session.execute(
        text("SELECT COUNT(*) FROM embeddings WHERE tenant_id = :tid"),
        {"tid": tenant_id}
    ).scalar()

    # Adjust probes based on tenant corpus size
    probes = 5 if count < 5000 else 10 if count < 20000 else 15
    session.execute(text(f"SET ivfflat.probes = {probes}"))

    # Search with tenant isolation
    return service.search_similar_evidence(
        db=session,
        query_embedding=query_embedding,
        top_k=10,
        tenant_id=tenant_id
    )
```

### Scenario 5: Hybrid Search (Vector + Keyword)

**Goal**: Combine vector similarity with text filtering

```python
from sqlalchemy import text

def hybrid_search(
    session,
    query_embedding: list[float],
    keyword_filter: str,
    top_k: int = 10
):
    """Search with vector similarity and keyword filter."""

    # Build query with keyword filter
    sql = """
    SELECT id, content, source_url,
           1 - (embedding <-> :vector::vector) AS similarity
    FROM embeddings
    WHERE entity_type = 'evidence'
      AND content ILIKE :keyword
    ORDER BY embedding <-> :vector::vector
    LIMIT :top_k
    """

    results = session.execute(
        text(sql),
        {
            "vector": query_embedding,
            "keyword": f"%{keyword_filter}%",
            "top_k": top_k
        }
    ).fetchall()

    return results
```

---

## API Reference

### VectorSearchService

```python
class VectorSearchService:
    """Service for vector similarity search."""

    def __init__(self, embedding_dimension: int = 1536) -> None:
        """Initialize service.

        Args:
            embedding_dimension: 384 or 1536
        """

    def search_similar_evidence(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
        tenant_id: str = "default",
        source_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search for similar evidence.

        Args:
            db: Database session
            query_embedding: Query vector
            top_k: Max results (default: 10)
            min_similarity: Threshold 0-1 (default: 0.0)
            tenant_id: Tenant ID (default: "default")
            source_filter: Optional URL filter

        Returns:
            List of SearchResult ordered by similarity
        """

    def search_similar_evidence_batch(
        self,
        db: Session,
        query_embeddings: list[list[float]],
        top_k: int = 10,
        min_similarity: float = 0.0,
        tenant_id: str = "default",
    ) -> list[list[SearchResult]]:
        """Batch search.

        Args:
            db: Database session
            query_embeddings: List of query vectors
            top_k: Max results per query
            min_similarity: Threshold 0-1
            tenant_id: Tenant ID

        Returns:
            List of result lists
        """

    def get_embedding_stats(
        self,
        db: Session,
        entity_type: Literal["evidence", "claim"] = "evidence",
        tenant_id: str = "default",
    ) -> dict:
        """Get embedding statistics.

        Returns:
            {
                "total_embeddings": int,
                "has_null_embeddings": bool,
                "null_embedding_count": int
            }
        """
```

### SearchResult

```python
@dataclass
class SearchResult:
    """Search result."""

    evidence_id: UUID        # Evidence UUID
    content: str             # Full text content
    source_url: Optional[str]  # Source URL
    similarity: float        # Cosine similarity [0, 1]
```

---

## FAQ

### Q: What's the difference between lists and probes?

**A**:
- **lists**: Number of clusters created during index building (static)
- **probes**: Number of clusters searched during queries (dynamic)

Think of it as: lists creates "buckets", probes determines how many buckets to search.

### Q: How do I choose the right lists value?

**A**: Use this formula:
```python
optimal_lists = int((corpus_size ** 0.5) * 5)

# Round to standard value
standard_values = [10, 25, 50, 100, 200]
lists = min(standard_values, key=lambda x: abs(x - optimal_lists))
```

For 10K corpus: sqrt(10000) * 5 = 500, round to 50.

### Q: What if my queries are slow?

**A**: Check these in order:
1. Is the index being used? (`EXPLAIN ANALYZE`)
2. Are probes too high? (try reducing to 5)
3. Is connection pooling enabled?
4. Is the index in cache? (warmup on startup)

### Q: How do I handle corpus growth?

**A**: Rebuild index when:
- Corpus grows >30%
- Latency increases >20%
- Recall drops >5%

```bash
# Check if rebuild needed
python scripts/benchmarks/check_index_health.py
```

### Q: Can I use different embedding dimensions?

**A**: Yes, pgvector supports:
- 384-dim (all-MiniLM-L6-v2) ← Default
- 1536-dim (text-embedding-3-small)
- Custom dimensions

```python
# Use 1536-dim embeddings
service = VectorSearchService(embedding_dimension=1536)
```

### Q: What's the maximum corpus size for IVFFlat?

**A**: Practical limits:
- <100K: Excellent performance
- 100K-500K: Good performance
- >500K: Consider sharding or dedicated vector DB

### Q: How do I debug accuracy issues?

**A**:
```python
# 1. Check index configuration
result = session.execute(text("""
    SELECT * FROM pg_indexes
    WHERE indexname = 'embeddings_ivfflat_idx'
""")).fetchone()

# 2. Increase probes
session.execute(text("SET ivfflat.probes = 25"))

# 3. Rebuild index with more lists
# CREATE INDEX ... WITH (lists = 100)
```

---

## Next Steps

- Read [vector_search_analysis.md](./vector_search_analysis.md) for detailed performance analysis
- Read [vector_index_recommendations.md](./vector_index_recommendations.md) for production best practices
- Run benchmarks with your own data
- Monitor production metrics
- Optimize based on your use case

---

**Document prepared by**: python-pro
**Feature**: 2.3 - Vector Search Index Optimization
**Date**: 2025-10-31
**Status**: Complete
