# Verification Pipeline Service

## Overview

The Verification Pipeline Service is the central orchestration layer for TruthGraph's ML-enhanced claim verification system. It coordinates embedding generation, evidence retrieval, NLI verification, and verdict aggregation into a seamless end-to-end pipeline.

**Performance Target:** < 60 seconds end-to-end

## Quick Start

```python
from truthgraph.services.verification_pipeline_service import (
    get_verification_pipeline_service
)
from truthgraph.db import SessionLocal

# Initialize service
service = get_verification_pipeline_service()

# Get database session
db = SessionLocal()

# Verify a claim
result = await service.verify_claim(
    db=db,
    claim_id=claim_id,
    claim_text="The Earth orbits around the Sun",
    top_k_evidence=10,
    min_similarity=0.5,
)

print(f"Verdict: {result.verdict}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Evidence: {len(result.evidence_items)} items")

db.close()
```

## Features

### Core Capabilities

- **End-to-End Orchestration**: Coordinates all verification steps in a single API call
- **Intelligent Caching**: In-memory cache for repeated claims (1-hour TTL)
- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Graceful Degradation**: Continues on partial failures, logs issues
- **Structured Results**: Comprehensive verdict with evidence and reasoning
- **Performance Optimized**: Batch NLI processing, singleton models, efficient search

### Pipeline Stages

1. **Cache Check**: Look for recent verification of same claim
2. **Embedding Generation**: Create semantic embedding for claim (384-dim)
3. **Evidence Retrieval**: Vector similarity search for relevant evidence
4. **NLI Verification**: Batch inference on claim-evidence pairs
5. **Verdict Aggregation**: Weight and combine NLI results
6. **Result Storage**: Save to database for audit trail
7. **Cache Update**: Store result for future queries

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Verification Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Cache Check (optional)        [<1ms]                   │
│           ↓                                                 │
│  2. Generate Embedding            [50-200ms]               │
│           ↓                                                 │
│  3. Search Evidence (Vector)      [20-100ms]               │
│           ↓                                                 │
│  4. NLI Verification (Batch)      [2-10s]                  │
│           ↓                                                 │
│  5. Aggregate Verdict             [<10ms]                  │
│           ↓                                                 │
│  6. Store Results                 [10-50ms]                │
│           ↓                                                 │
│  7. Update Cache                  [<1ms]                   │
│           ↓                                                 │
│     Return Result                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Service Initialization

```python
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService
)

service = VerificationPipelineService(
    embedding_dimension=384,      # 384 for MiniLM, 1536 for OpenAI
    cache_ttl_seconds=3600,       # 1 hour cache TTL
    embedding_service=None,       # Auto-initialize singleton
    nli_service=None,             # Auto-initialize singleton
    vector_search_service=None,   # Auto-initialize with dimension
)
```

### Verification Parameters

```python
result = await service.verify_claim(
    db=db_session,                # SQLAlchemy session (sync)
    claim_id=uuid4(),             # UUID of claim record
    claim_text="Claim to verify", # Text to verify
    top_k_evidence=10,            # Number of evidence items (default: 10)
    min_similarity=0.5,           # Similarity threshold (default: 0.5)
    tenant_id="default",          # Multi-tenancy support
    use_cache=True,               # Enable caching (default: True)
    store_result=True,            # Store in DB (default: True)
)
```

## Result Structure

### VerificationPipelineResult

```python
@dataclass
class VerificationPipelineResult:
    claim_id: UUID                       # Claim being verified
    claim_text: str                      # Original claim text
    verdict: VerdictLabel                # SUPPORTED | REFUTED | INSUFFICIENT
    confidence: float                    # Overall confidence (0-1)
    support_score: float                 # Weighted support score
    refute_score: float                  # Weighted refutation score
    neutral_score: float                 # Weighted neutral score
    evidence_items: list[EvidenceItem]   # Evidence with NLI results
    reasoning: str                       # Human-readable explanation
    pipeline_duration_ms: float          # Execution time
    retrieval_method: str                # "vector" | "hybrid" | "keyword"
    verification_result_id: UUID | None  # Database record ID
```

### EvidenceItem

```python
@dataclass
class EvidenceItem:
    evidence_id: UUID          # Evidence record ID
    content: str               # Evidence text
    source_url: str | None     # Source URL
    similarity: float          # Vector similarity (0-1)
    nli_label: NLILabel        # ENTAILMENT | CONTRADICTION | NEUTRAL
    nli_confidence: float      # NLI confidence (0-1)
    nli_scores: dict           # All NLI scores
```

## Verdict Aggregation

### Strategy

The pipeline aggregates NLI results using similarity-weighted scoring:

1. **Weight NLI scores by similarity**: More relevant evidence has higher influence
2. **Count evidence by label**: Track support/refute/neutral counts
3. **Determine verdict**: Based on weighted scores and thresholds
4. **Calculate confidence**: Use dominant weighted score

### Thresholds

```python
HIGH_CONFIDENCE_THRESHOLD = 0.6  # Minimum score for SUPPORTED/REFUTED
MIN_EVIDENCE_THRESHOLD = 2       # Minimum evidence for confident verdict
```

### Verdict Rules

- **SUPPORTED**: `weighted_support > 0.6` and dominates other scores
- **REFUTED**: `weighted_refute > 0.6` and dominates other scores
- **INSUFFICIENT**: Not enough evidence or inconclusive scores

## Performance

### Benchmarking

Run the benchmark script:

```bash
python scripts/benchmark_verification_pipeline.py \
    --db-url "postgresql://user:pass@localhost/db" \
    --iterations 5
```

### Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| End-to-end duration | <60s | 5-30s |
| Embedding generation | <200ms | 50-150ms |
| Evidence retrieval | <100ms | 20-80ms |
| NLI verification (10 items) | <10s | 3-8s |
| Cache hit latency | <10ms | <5ms |

### Optimization Tips

1. **Reduce Evidence Count**: Lower `top_k_evidence` for faster processing
2. **Increase Similarity Threshold**: Higher `min_similarity` returns fewer results
3. **Enable Caching**: Set `use_cache=True` for repeated claims
4. **Use GPU**: Significantly faster embedding and NLI inference
5. **Adjust Batch Size**: Tune NLI batch size for your hardware

## Error Handling

### Retry Logic

Critical operations have automatic retry:

- **Embedding Generation**: 3 attempts with exponential backoff
- **Evidence Search**: 2 attempts with exponential backoff
- **Backoff Schedule**: 1s, 2s, 4s delays

### Graceful Degradation

The pipeline handles failures gracefully:

- **No Evidence**: Returns INSUFFICIENT verdict
- **Storage Failure**: Logs error, returns result to client
- **Partial NLI Failure**: Continues with successful results
- **Cache Failure**: Bypasses cache, logs warning

### Validation

```python
# Invalid input raises ValueError
await service.verify_claim(
    db=db,
    claim_id=uuid4(),
    claim_text="",  # ❌ ValueError: Claim text cannot be empty
)
```

## Caching

### Cache Mechanism

- **Storage**: In-memory dictionary
- **Key**: SHA256 hash of normalized claim text
- **TTL**: Configurable (default: 1 hour)
- **Normalization**: Lowercase, strip whitespace

### Cache Management

```python
# Check cache
cached = service._get_cached_result("Some claim")
if cached:
    print("Cache hit!")

# Clear cache
service.clear_cache()
```

### Cache Behavior

```python
# First call - executes full pipeline
result1 = await service.verify_claim(db, id1, "The Earth is round", use_cache=True)
# Duration: ~5-10 seconds

# Second call - cache hit
result2 = await service.verify_claim(db, id2, "the earth is round", use_cache=True)
# Duration: <5ms (99%+ faster)
```

## Testing

### Unit Tests (25 tests)

```bash
pytest tests/unit/services/test_verification_pipeline_service.py -v
```

**Coverage:**
- Retry decorator (4 tests)
- Service initialization (2 tests)
- Caching mechanisms (7 tests)
- Verdict aggregation (5 tests)
- Reasoning generation (4 tests)
- Retry wrappers (2 tests)
- Insufficient verdicts (1 test)

### Integration Tests (10+ tests)

```bash
pytest tests/integration/test_verification_pipeline_integration.py -v -m integration
```

**Coverage:**
- End-to-end pipeline execution
- Caching behavior
- Database integration
- Error handling
- Performance requirements

## Examples

### Basic Usage

See `examples/verification_pipeline_example.py` for a complete example.

### Custom Configuration

```python
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService
)

# Custom service with 2-hour cache
service = VerificationPipelineService(
    embedding_dimension=384,
    cache_ttl_seconds=7200,  # 2 hours
)

# Verify with custom parameters
result = await service.verify_claim(
    db=db,
    claim_id=claim_id,
    claim_text="Custom claim",
    top_k_evidence=20,      # More evidence
    min_similarity=0.7,     # Higher threshold
    tenant_id="custom",     # Custom tenant
)
```

### Batch Processing

```python
# Process multiple claims
claims = [
    ("claim-1", "Claim text 1"),
    ("claim-2", "Claim text 2"),
    ("claim-3", "Claim text 3"),
]

results = []
for claim_id, claim_text in claims:
    result = await service.verify_claim(
        db=db,
        claim_id=claim_id,
        claim_text=claim_text,
    )
    results.append(result)

# Analyze results
for result in results:
    print(f"{result.claim_text}: {result.verdict} ({result.confidence:.0%})")
```

## Monitoring

### Structured Logging

All operations emit structured logs:

```python
# Log events
- verification_pipeline_start
- claim_embedding_generated
- evidence_retrieved
- nli_verification_complete
- verdict_aggregated
- verification_result_stored
- verification_pipeline_complete
- cache_hit / cache_expired
- operation_failed_retrying
```

### Key Metrics

Monitor these metrics in production:

1. **Pipeline Duration**: Total end-to-end time
2. **Cache Hit Rate**: Percentage of cached results
3. **Evidence Count**: Average evidence per claim
4. **Verdict Distribution**: SUPPORTED/REFUTED/INSUFFICIENT ratios
5. **Confidence Scores**: Average by verdict type
6. **Error Rates**: Retry counts, failure rates

### Example Logging

```python
import structlog

logger = structlog.get_logger(__name__)

# Logs are structured JSON
logger.info(
    "verification_pipeline_complete",
    claim_id=str(claim_id),
    verdict="SUPPORTED",
    confidence=0.85,
    evidence_count=10,
    total_duration_ms=5432.1,
)
```

## Troubleshooting

### Pipeline Timeout

**Problem**: Pipeline exceeds 60s target

**Solutions**:
- Reduce `top_k_evidence` (default: 10)
- Increase `min_similarity` threshold (default: 0.5)
- Enable caching for repeated claims
- Check database query performance
- Consider GPU acceleration

### Low Confidence

**Problem**: Most verdicts are INSUFFICIENT

**Solutions**:
- Lower `min_similarity` for more evidence
- Increase `top_k_evidence` for diversity
- Verify evidence database is populated
- Check embedding quality

### Memory Issues

**Problem**: High memory usage

**Solutions**:
- Reduce NLI batch size (default: 8)
- Clear model cache periodically
- Implement LRU cache eviction
- Monitor cache size

### Database Errors

**Problem**: Storage failures

**Solutions**:
- Check database connection
- Verify schema migrations are applied
- Check for constraint violations
- Review database logs

## Future Enhancements

### Planned Features

1. **Hybrid Search**: Combine vector + keyword search
2. **Advanced Aggregation**: ML-based verdict model
3. **Async/Parallel**: Concurrent claim processing
4. **Distributed Cache**: Redis for multi-instance deployment
5. **Real-time Streaming**: WebSocket progress updates
6. **Explainability**: Attention visualization, evidence highlighting

## API Reference

### Main Methods

#### `verify_claim()`

```python
async def verify_claim(
    self,
    db: Session,
    claim_id: UUID,
    claim_text: str,
    top_k_evidence: int = 10,
    min_similarity: float = 0.5,
    tenant_id: str = "default",
    use_cache: bool = True,
    store_result: bool = True,
) -> VerificationPipelineResult:
    """Execute end-to-end verification pipeline."""
```

#### `clear_cache()`

```python
def clear_cache(self) -> None:
    """Clear all cached verification results."""
```

### Helper Methods

- `_generate_embedding_with_retry()`: Embedding with retry
- `_search_evidence_with_retry()`: Search with retry
- `_verify_evidence_batch()`: Batch NLI inference
- `_aggregate_verdict()`: Verdict aggregation
- `_store_verification_result()`: Database storage

## Dependencies

### Required Services

- **EmbeddingService**: Generates semantic embeddings
- **NLIService**: Natural Language Inference verification
- **VectorSearchService**: Vector similarity search
- **Database**: PostgreSQL with pgvector extension

### Python Packages

- `sqlalchemy`: Database ORM
- `sentence-transformers`: Embedding generation
- `transformers`: NLI model
- `torch`: Deep learning framework
- `structlog`: Structured logging

## Contributing

When modifying the verification pipeline:

1. ✅ Maintain <60s performance target
2. ✅ Add comprehensive tests (unit + integration)
3. ✅ Update documentation
4. ✅ Run benchmarks before/after changes
5. ✅ Consider backward compatibility
6. ✅ Add structured logging for new operations

## License

Part of TruthGraph Phase 2 ML-Enhanced Verification System

---

**For detailed documentation, see:** `docs/verification_pipeline.md`

**For examples, see:** `examples/verification_pipeline_example.py`

**For benchmarks, see:** `scripts/benchmark_verification_pipeline.py`
