# Hybrid Search Service - Quick Start Guide

## 5-Minute Setup

### 1. Import the Service

```python
from truthgraph.services import HybridSearchService
from truthgraph.services.ml import get_embedding_service
```

### 2. Initialize

```python
# Use 1536 for text-embedding-3-small, or 384 for all-MiniLM-L6-v2
hybrid_service = HybridSearchService(embedding_dimension=1536)
embedding_service = get_embedding_service()
```

### 3. Perform a Search

```python
# Your search query
query_text = "What are the effects of climate change?"

# Generate embedding for the query
query_embedding = embedding_service.embed_text(query_text)

# Hybrid search
results, query_time_ms = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    top_k=10,
)

# Display results
print(f"Found {len(results)} results in {query_time_ms:.1f}ms\n")

for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result.rank_score:.4f} (via: {result.matched_via})")
    print(f"   {result.content[:100]}...")
    if result.source_url:
        print(f"   Source: {result.source_url}")
    print()
```

## Common Use Cases

### Semantic-Focused Search (Vector-Heavy)

Best for: Conceptual queries, finding similar meanings

```python
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    vector_weight=0.8,    # 80% semantic
    keyword_weight=0.2,   # 20% keyword
)
```

### Keyword-Focused Search (Keyword-Heavy)

Best for: Exact term matching, technical terms, names

```python
results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    vector_weight=0.2,    # 20% semantic
    keyword_weight=0.8,   # 80% keyword
)
```

### Filtered Search

Filter by source, date, or tenant:

```python
from datetime import datetime, timedelta

results, _ = hybrid_service.hybrid_search(
    db=db_session,
    query_text=query_text,
    query_embedding=query_embedding,
    source_filter="https://example.com",           # Specific source
    date_from=datetime.utcnow() - timedelta(days=30),  # Last 30 days
    tenant_id="my_tenant",                         # Specific tenant
)
```

### Keyword-Only Search

Skip vector search (useful for debugging):

```python
results, query_time = hybrid_service.keyword_only_search(
    db=db_session,
    query_text="machine learning algorithms",
    top_k=10,
)
```

## Checking Coverage

See how many evidence documents have embeddings:

```python
stats = hybrid_service.get_search_stats(db=db_session)

print(f"Total evidence: {stats['total_evidence']}")
print(f"With embeddings: {stats['evidence_with_embeddings']}")
print(f"Coverage: {stats['embedding_coverage']:.1f}%")
```

## Understanding Results

Each `HybridSearchResult` contains:

```python
result.evidence_id       # UUID of the evidence
result.content          # Full text content
result.source_url       # Source URL (if available)
result.rank_score       # RRF score (higher = better)
result.vector_similarity  # Similarity from vector search (0-1, if found)
result.keyword_rank     # Rank position from keyword search (if found)
result.matched_via      # "vector", "keyword", or "both"
```

## Performance Tips

1. **Use balanced weights (0.5/0.5) as default**
2. **Keep top_k between 10-50 for best performance**
3. **Apply filters to narrow search space**
4. **Monitor query times and adjust as needed**

## Testing Your Setup

Run the test suite:

```bash
# Unit tests (fast, no DB needed for most)
pytest tests/unit/services/test_hybrid_search_service.py -v

# Integration tests (requires PostgreSQL with pgvector)
pytest tests/integration/test_hybrid_search_integration.py -v

# Performance benchmarks
pytest tests/benchmarks/test_hybrid_search_performance.py -v -s
```

## Troubleshooting

### "No results found"
- Check embedding coverage with `get_search_stats()`
- Try lowering `min_vector_similarity` (default is 0.0)
- Verify evidence exists in database

### "Slow queries"
- Check if IVFFlat index exists on embeddings table
- Reduce `top_k` value
- Apply filters to narrow search space

### "Irrelevant results"
- Adjust weight balance (try different ratios)
- Increase `min_vector_similarity` threshold
- Use more specific query text

## Next Steps

- Read the [comprehensive documentation](docs/HYBRID_SEARCH_SERVICE.md)
- Check the [implementation summary](HYBRID_SEARCH_IMPLEMENTATION_SUMMARY.md)
- Integrate into your verification pipeline

## API Reference

See [docs/HYBRID_SEARCH_SERVICE.md](docs/HYBRID_SEARCH_SERVICE.md) for complete API reference.

## Support

For issues or questions, check:
1. [Documentation](docs/HYBRID_SEARCH_SERVICE.md)
2. [Implementation Summary](HYBRID_SEARCH_IMPLEMENTATION_SUMMARY.md)
3. Test files for usage examples
