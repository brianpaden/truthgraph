# Vector Search Quick Reference

**Status**: ✅ Complete | **Performance Target**: <100ms | **Test Coverage**: 27 tests

---

## Quick Start

### 1. Apply Database Migration

```bash
# Via Docker
docker-compose exec postgres psql -U truthgraph -d truthgraph \
    -f /docker-entrypoint-initdb.d/migrations/002_embeddings.sql

# Or directly
psql -U truthgraph -d truthgraph -f docker/migrations/002_embeddings.sql
```

### 2. Basic Usage

```python
from truthgraph.services.vector_search_service import VectorSearchService

# Initialize (1536-dim for text-embedding-3-small)
service = VectorSearchService(embedding_dimension=1536)

# Search
results = service.search_similar_evidence(
    db=session,
    query_embedding=[0.1, 0.2, ...],  # 1536-dim vector
    top_k=10,
    min_similarity=0.7
)

# Process results
for r in results:
    print(f"{r.similarity:.3f}: {r.content}")
```

### 3. Run Tests

```bash
# Unit tests (fast, no DB)
pytest tests/unit/services/test_vector_search_service.py -v

# Integration tests (requires DB)
export TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/test"
pytest tests/integration/test_vector_search_integration.py -v

# Benchmark
python scripts/benchmark_vector_search.py --corpus-size 1000
```

## Common Operations

### Search with Filters

```python
# Filter by source
results = service.search_similar_evidence(
    db=session,
    query_embedding=vector,
    source_filter='https://example.com'
)

# Different tenant
results = service.search_similar_evidence(
    db=session,
    query_embedding=vector,
    tenant_id='customer_123'
)
```

### Batch Search

```python
query_embeddings = [[0.1]*1536, [0.2]*1536, [0.3]*1536]
batch_results = service.search_similar_evidence_batch(
    db=session,
    query_embeddings=query_embeddings
)
```

### Get Statistics

```python
stats = service.get_embedding_stats(db=session)
print(f"Total: {stats['total_embeddings']}")
```

## Performance Tuning

### Adjust IVFFlat Lists

```sql
-- In migration or ALTER INDEX
CREATE INDEX idx_embeddings_vector_similarity
    ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 500);  -- Increase for larger corpus
```

### Adjust Query-Time Probes

```sql
SET ivfflat.probes = 10;  -- More accurate, slower (default: 1)
```

### Choose Embedding Dimension

```python
# 384-dim: Faster, smaller (all-MiniLM-L6-v2)
service = VectorSearchService(embedding_dimension=384)

# 1536-dim: Higher quality (text-embedding-3-small)
service = VectorSearchService(embedding_dimension=1536)
```

## File Locations

```text
truthgraph/
├── services/
│   └── vector_search_service.py          # Main service (315 lines)
├── models.py                              # API models (updated)
└── schemas.py                             # ORM schema (updated)

docker/migrations/
└── 002_embeddings.sql                     # Database migration

tests/
├── unit/services/
│   └── test_vector_search_service.py      # Unit tests (348 lines, 17 tests)
└── integration/
    └── test_vector_search_integration.py  # Integration tests (336 lines, 10 tests)

scripts/
└── benchmark_vector_search.py             # Benchmark script (379 lines)

docs/
└── VECTOR_SEARCH_IMPLEMENTATION.md        # Full documentation
```

## Troubleshooting

### Slow Queries
1. Check index: `EXPLAIN ANALYZE SELECT ...`
2. Increase `lists` parameter
3. Adjust `ivfflat.probes`

### No Results
1. Check tenant_id matches
2. Lower min_similarity threshold
3. Verify embeddings exist: `SELECT COUNT(*) FROM embeddings`

### Import Errors
```bash
# Install dependencies
pip install sqlalchemy pgvector psycopg[binary] pydantic
```

## API Integration

```python
# models.py
from truthgraph.models import VectorSearchRequest, VectorSearchResponse

# FastAPI endpoint example
@app.post("/search", response_model=VectorSearchResponse)
def search_evidence(request: VectorSearchRequest, db: Session = Depends(get_db)):
    service = VectorSearchService(embedding_dimension=1536)
    results = service.search_similar_evidence(
        db=db,
        query_embedding=request.query_embedding,
        top_k=request.top_k,
        min_similarity=request.min_similarity
    )
    return VectorSearchResponse(
        results=results,
        total=len(results)
    )
```

## Performance Targets

| Corpus Size | Target Time | Lists Parameter |
|-------------|-------------|-----------------|
| <10k        | 20-50ms     | 100             |
| 10k-100k    | 50-100ms    | 500             |
| 100k+       | 80-150ms    | 1000            |

## Key Features

✅ Cosine distance similarity search
✅ Tenant isolation
✅ Source filtering
✅ Batch queries
✅ Configurable dimensions (384/1536)
✅ Top-k results
✅ Similarity thresholds
✅ Statistics and monitoring
✅ Comprehensive error handling
✅ 100% type hints

## Next Steps

1. ✅ Apply migration → Create embeddings table
2. ✅ Run unit tests → Validate logic
3. ⏳ Run integration tests → Validate with DB
4. ⏳ Run benchmark → Validate performance
5. ⏳ Tune index → Optimize for corpus size
6. ⏳ Integrate → Connect with embedding service

---

**Complete Documentation**: See `docs/VECTOR_SEARCH_IMPLEMENTATION.md`
**Implementation Summary**: See `VECTOR_SEARCH_SUMMARY.md`
