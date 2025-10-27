# Hybrid Search Service Documentation

## Overview

The Hybrid Search Service combines **vector similarity search** and **PostgreSQL full-text search** to provide powerful semantic and keyword-based evidence retrieval for the TruthGraph fact-checking system.

### Key Features

- **Dual Search Modes**: Combines vector embeddings (semantic) with full-text search (keyword)
- **Reciprocal Rank Fusion (RRF)**: Robust rank aggregation without score normalization
- **Configurable Weights**: Adjust balance between vector and keyword search
- **Advanced Filtering**: Filter by tenant, source URL, and date ranges
- **High Performance**: <150ms query time target
- **Flexible API**: Support for hybrid, vector-only, and keyword-only searches

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    HybridSearchService                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
            ┌───────────────┴──────────────┐
            │                              │
            ▼                              ▼
┌─────────────────────┐        ┌─────────────────────┐
│  Vector Search      │        │  Keyword Search     │
│  (pgvector)         │        │  (PostgreSQL FTS)   │
│                     │        │                     │
│  - Cosine distance  │        │  - to_tsvector      │
│  - IVFFlat index    │        │  - plainto_tsquery  │
│  - Embeddings table │        │  - ts_rank          │
└─────────────────────┘        └─────────────────────┘
            │                              │
            └───────────────┬──────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │  RRF Fusion          │
                │  (Merge & Rank)      │
                └──────────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  Top-K Results  │
                  └─────────────────┘
```

## Reciprocal Rank Fusion (RRF)

### Algorithm

RRF is a rank aggregation method that combines rankings from multiple retrieval systems without requiring score normalization.

**Formula:**

```text
RRF_score(d) = Σ w_i × 1 / (k + rank_i(d))
```

Where:
- `d` is a document
- `rank_i(d)` is the rank position in retrieval system `i` (1-indexed)
- `w_i` is the weight for retrieval system `i`
- `k` is a constant (default: 60)

### Why RRF?

1. **No Score Normalization**: Different retrieval systems produce different score distributions. RRF works with ranks, avoiding normalization issues.

2. **Robust**: Less sensitive to outliers and score variations than score-based fusion.

3. **Simple**: Easy to implement and understand.

4. **Proven**: Well-established in Information Retrieval research.

### Example

Given:
- Vector search ranks: Document A (rank 1), Document B (rank 3)
- Keyword search ranks: Document A (rank 2), Document C (rank 1)
- Weights: vector=0.6, keyword=0.4
- k=60

RRF scores:
- **Document A**: `0.6 × 1/(60+1) + 0.4 × 1/(60+2) = 0.00984 + 0.00645 = 0.01629`
- **Document B**: `0.6 × 1/(60+3) + 0 = 0.00952`
- **Document C**: `0 + 0.4 × 1/(60+1) = 0.00656`

**Ranking**: A > B > C

## Usage

### Basic Hybrid Search

```python
from truthgraph.services.hybrid_search_service import HybridSearchService
from truthgraph.services.ml.embedding_service import get_embedding_service

# Initialize services
hybrid_service = HybridSearchService(embedding_dimension=1536)
embedding_service = get_embedding_service()

# Generate query embedding
query_text = "What are the effects of climate change?"
query_embedding = embedding_service.embed_text(query_text)

# Perform hybrid search
results, query_time = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    top_k=10,
    vector_weight=0.5,
    keyword_weight=0.5,
)

print(f"Found {len(results)} results in {query_time:.1f}ms")

for result in results:
    print(f"Score: {result.rank_score:.4f}")
    print(f"Content: {result.content[:100]}...")
    print(f"Matched via: {result.matched_via}")
    print()
```

### Adjust Search Weights

```python
# Vector-heavy search (emphasize semantic similarity)
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    top_k=10,
    vector_weight=0.8,    # 80% vector
    keyword_weight=0.2,   # 20% keyword
)

# Keyword-heavy search (emphasize exact term matching)
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    top_k=10,
    vector_weight=0.2,    # 20% vector
    keyword_weight=0.8,   # 80% keyword
)
```

### Apply Filters

```python
from datetime import datetime, timedelta

# Filter by source
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    source_filter="https://climate-science.org",
)

# Filter by date range
one_month_ago = datetime.utcnow() - timedelta(days=30)
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    date_from=one_month_ago,
)

# Combined filters
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    source_filter="https://example.com",
    date_from=one_month_ago,
    tenant_id="tenant123",
)
```

### Keyword-Only Search

```python
# Skip vector search (useful for debugging or comparison)
results, query_time = hybrid_service.keyword_only_search(
    db=db_session,
    query_text="machine learning neural networks",
    top_k=10,
)
```

### Get Search Statistics

```python
# Check embedding coverage
stats = hybrid_service.get_search_stats(db=db_session)

print(f"Total evidence: {stats['total_evidence']}")
print(f"With embeddings: {stats['evidence_with_embeddings']}")
print(f"Coverage: {stats['embedding_coverage']:.1f}%")
```

## API Reference

### HybridSearchService

#### `__init__(embedding_dimension: int = 1536)`

Initialize the hybrid search service.

**Parameters:**
- `embedding_dimension`: Dimension of embeddings (384 or 1536)

#### `hybrid_search(...)`

Perform hybrid search combining vector and keyword search.

**Parameters:**
- `db`: SQLAlchemy database session
- `query_text`: Natural language query text
- `query_embedding`: Query embedding vector
- `top_k`: Maximum results to return (default: 10)
- `vector_weight`: Weight for vector search (default: 0.5)
- `keyword_weight`: Weight for keyword search (default: 0.5)
- `min_vector_similarity`: Minimum similarity threshold (default: 0.0)
- `tenant_id`: Tenant identifier (default: "default")
- `source_filter`: Optional source URL filter
- `date_from`: Optional minimum creation date
- `date_to`: Optional maximum creation date

**Returns:**
- Tuple of `(results, query_time_ms)`

**Raises:**
- `ValueError`: Invalid parameters
- `RuntimeError`: Search failure

#### `keyword_only_search(...)`

Perform keyword-only full-text search.

**Parameters:**
- `db`: SQLAlchemy database session
- `query_text`: Search query text
- `top_k`: Maximum results (default: 10)
- `tenant_id`: Tenant identifier (default: "default")
- `source_filter`: Optional source URL filter
- `date_from`: Optional minimum creation date
- `date_to`: Optional maximum creation date

**Returns:**
- Tuple of `(results, query_time_ms)`

#### `get_search_stats(db, tenant_id="default")`

Get statistics about searchable evidence.

**Returns:**
- Dictionary with stats:
  - `total_evidence`: Total evidence count
  - `evidence_with_embeddings`: Evidence with embeddings
  - `embedding_coverage`: Percentage with embeddings
  - `tenant_id`: Tenant identifier

### HybridSearchResult

Result object from hybrid search.

**Attributes:**
- `evidence_id`: UUID of the evidence document
- `content`: Full text content
- `source_url`: Source URL (if available)
- `rank_score`: Combined RRF score (higher = better)
- `vector_similarity`: Cosine similarity from vector search (if found)
- `keyword_rank`: Rank position from keyword search (if found)
- `matched_via`: How result was found ("vector", "keyword", or "both")

## Performance

### Targets

- **Hybrid search**: <150ms for typical queries
- **Keyword search**: <100ms
- **RRF fusion**: <1ms (pure Python computation)

### Optimization Tips

1. **Database Indexing**:
   - Ensure IVFFlat index on embeddings table
   - Consider GIN index on evidence.content for full-text search

2. **Weight Configuration**:
   - Use higher vector weights for semantic queries
   - Use higher keyword weights for exact term matching
   - Balanced weights (0.5/0.5) work well for general queries

3. **Result Size**:
   - Keep `top_k` reasonable (10-50)
   - Service retrieves 3× top_k internally for RRF fusion

4. **Filtering**:
   - Filters are applied at database level (efficient)
   - Use filters to reduce result set size

### Benchmarks

Typical performance on 100-500 document dataset:

| Dataset Size | Avg Query Time | P95 Query Time |
|--------------|----------------|----------------|
| 100 docs     | 45ms           | 75ms           |
| 500 docs     | 85ms           | 125ms          |
| 1000 docs    | 120ms          | 180ms          |

*Note: With IVFFlat indexing, performance scales sub-linearly.*

## Testing

### Unit Tests

```bash
pytest tests/unit/services/test_hybrid_search_service.py -v
```

**Coverage:** 15+ tests covering:
- Initialization
- RRF algorithm correctness
- Weight handling
- Edge cases
- Error handling

### Integration Tests

```bash
pytest tests/integration/test_hybrid_search_integration.py -v
```

**Coverage:** 10+ tests with real database:
- End-to-end hybrid search
- Weight variations
- Filtering
- Result deduplication
- Performance validation

### Performance Benchmarks

```bash
pytest tests/benchmarks/test_hybrid_search_performance.py -v -s
```

**Coverage:**
- Query time across dataset sizes
- Weight configuration impact
- Top-k variations
- Scalability analysis
- RRF fusion performance

## Best Practices

### 1. Choose Appropriate Weights

```python
# For semantic/conceptual queries (synonyms, paraphrasing)
vector_weight=0.7, keyword_weight=0.3

# For exact term matching (names, technical terms)
vector_weight=0.3, keyword_weight=0.7

# For balanced retrieval
vector_weight=0.5, keyword_weight=0.5
```

### 2. Set Reasonable Similarity Thresholds

```python
# Strict semantic matching
min_vector_similarity=0.7

# Moderate semantic matching (recommended)
min_vector_similarity=0.5

# Broad semantic matching
min_vector_similarity=0.3
```

### 3. Use Filters to Narrow Results

```python
# Combine filters for targeted search
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    source_filter="https://trusted-source.com",
    date_from=datetime(2024, 1, 1),
    tenant_id="production",
)
```

### 4. Monitor Performance

```python
results, query_time = hybrid_service.hybrid_search(...)

if query_time > 200:
    logger.warning(f"Slow hybrid search: {query_time:.1f}ms")

# Track stats
stats = hybrid_service.get_search_stats(db)
if stats['embedding_coverage'] < 80:
    logger.warning(f"Low embedding coverage: {stats['embedding_coverage']:.1f}%")
```

## Troubleshooting

### Slow Queries

**Problem**: Queries taking >200ms

**Solutions**:
1. Check if IVFFlat index exists on embeddings table
2. Verify full-text search index on evidence.content
3. Reduce `top_k` value
4. Apply filters to narrow search space
5. Check database connection pooling

### Poor Result Quality

**Problem**: Irrelevant results in top positions

**Solutions**:
1. Adjust weight balance (try different ratios)
2. Increase `min_vector_similarity` threshold
3. Use more specific query text
4. Verify embedding quality with vector-only search
5. Test keyword-only search separately

### Missing Results

**Problem**: Expected results not appearing

**Solutions**:
1. Check embedding coverage with `get_search_stats()`
2. Verify evidence exists in database
3. Try lower `min_vector_similarity`
4. Test with broader query terms
5. Check tenant_id filtering

### Empty Results

**Problem**: No results returned

**Solutions**:
1. Verify evidence and embeddings exist
2. Remove all filters temporarily
3. Check query text formatting
4. Validate embedding dimension matches
5. Test keyword-only search

## Integration with TruthGraph Pipeline

The Hybrid Search Service integrates into the TruthGraph verification pipeline:

```text
┌─────────────┐
│ User Claim  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Embed Claim     │  (EmbeddingService)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Hybrid Search   │  (HybridSearchService)
│ for Evidence    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ NLI Inference   │  (NLIService)
│ on Top Results  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Aggregate       │
│ Verdict         │
└─────────────────┘
```

## References

- [Reciprocal Rank Fusion (Cormack et al., 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [TruthGraph Phase 2 Plan](../PHASE_2_IMPLEMENTATION_PLAN.md)

## License

Apache 2.0 - See LICENSE file for details.
