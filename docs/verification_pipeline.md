# Verification Pipeline Orchestration

## Overview

The Verification Pipeline Service is the core orchestration layer for TruthGraph's ML-enhanced claim verification system. It coordinates multiple specialized services to provide end-to-end claim verification with evidence retrieval and natural language inference.

**Performance Target:** <60 seconds end-to-end for typical claims

## Architecture

### System Components

```mermaid
graph TB
    Client[Client/API] --> Pipeline[Verification Pipeline Service]
    Pipeline --> Cache[Result Cache]
    Pipeline --> Embedding[Embedding Service]
    Pipeline --> VectorSearch[Vector Search Service]
    Pipeline --> NLI[NLI Service]
    Pipeline --> Aggregation[Verdict Aggregation]
    Pipeline --> Storage[Database Storage]

    Embedding --> EmbModel[MiniLM Model]
    NLI --> NLIModel[DeBERTa Model]
    VectorSearch --> pgVector[PostgreSQL + pgvector]
    Storage --> DB[(PostgreSQL)]

    style Pipeline fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style Cache fill:#F39C12,stroke:#C87F0A,color:#fff
    style Embedding fill:#27AE60,stroke:#1E8449,color:#fff
    style VectorSearch fill:#8E44AD,stroke:#6C3483,color:#fff
    style NLI fill:#E74C3C,stroke:#C0392B,color:#fff
    style Aggregation fill:#3498DB,stroke:#2874A6,color:#fff
    style Storage fill:#95A5A6,stroke:#707B7C,color:#fff
```

### Pipeline Flow

```mermaid
sequenceDiagram
    participant Client
    participant Pipeline
    participant Cache
    participant Embedding
    participant VectorSearch
    participant NLI
    participant Aggregation
    participant Storage

    Client->>Pipeline: verify_claim(claim_text)

    Pipeline->>Cache: Check cache for claim
    alt Cache Hit
        Cache-->>Pipeline: Return cached result
        Pipeline-->>Client: Cached verification result
    else Cache Miss
        Pipeline->>Embedding: Generate embedding
        Embedding-->>Pipeline: Claim embedding vector

        Pipeline->>VectorSearch: Search similar evidence
        VectorSearch-->>Pipeline: Top-K evidence items

        alt No Evidence Found
            Pipeline->>Aggregation: Create INSUFFICIENT verdict
            Aggregation-->>Pipeline: INSUFFICIENT result
        else Evidence Found
            Pipeline->>NLI: Verify claim vs evidence (batch)
            NLI-->>Pipeline: NLI results for each pair

            Pipeline->>Aggregation: Aggregate NLI results
            Aggregation-->>Pipeline: Final verdict + confidence
        end

        Pipeline->>Storage: Store verification result
        Storage-->>Pipeline: Confirmation + result_id

        Pipeline->>Cache: Cache result
        Cache-->>Pipeline: Confirmation

        Pipeline-->>Client: Verification result
    end
```

## Pipeline Stages

### 1. Cache Check (Optional)

**Duration:** <1ms

The pipeline first checks an in-memory cache for recent verifications of the same claim:
- Claims are normalized (lowercase, trimmed) and hashed
- Cache entries have configurable TTL (default: 1 hour)
- Cache hit avoids full pipeline execution

```python
# Cache key generation
def _compute_claim_hash(claim_text: str) -> str:
    normalized = claim_text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

### 2. Claim Embedding Generation

**Duration:** 50-200ms (CPU), 10-50ms (GPU)

Generate semantic embedding for the claim using sentence-transformers:
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Normalized embeddings for cosine similarity
- Retry logic with exponential backoff

```python
claim_embedding = embedding_service.embed_text(claim_text)
# Returns: List[float] of length 384
```

### 3. Evidence Retrieval

**Duration:** 20-100ms

Search for semantically similar evidence using pgvector:
- Vector similarity search (cosine distance)
- Configurable top-K (default: 10 evidence items)
- Minimum similarity threshold (default: 0.5)
- Tenant-isolated for multi-tenancy

```python
search_results = vector_search_service.search_similar_evidence(
    db=db,
    query_embedding=claim_embedding,
    top_k=10,
    min_similarity=0.5,
    tenant_id="default"
)
```

**Search Result Structure:**
```python
@dataclass
class SearchResult:
    evidence_id: UUID
    content: str
    source_url: Optional[str]
    similarity: float  # 0.0 to 1.0
```

### 4. NLI Verification

**Duration:** 2-10 seconds (depends on evidence count, batch size)

Verify each claim-evidence pair using Natural Language Inference:
- Model: `cross-encoder/nli-deberta-v3-base`
- Batch processing for efficiency (batch_size=8 for CPU)
- Labels: ENTAILMENT, CONTRADICTION, NEUTRAL
- Confidence scores for each label

```python
pairs = [(evidence.content, claim_text) for evidence in search_results]
nli_results = nli_service.verify_batch(pairs, batch_size=8)
```

**NLI Result Structure:**
```python
@dataclass
class NLIResult:
    label: NLILabel  # ENTAILMENT | CONTRADICTION | NEUTRAL
    confidence: float  # 0.0 to 1.0
    scores: dict[str, float]  # All three label scores
```

### 5. Verdict Aggregation

**Duration:** <10ms

Aggregate NLI results into final verdict:

#### Aggregation Strategy

1. **Weight NLI scores by similarity**: More relevant evidence has higher influence
   ```python
   weighted_support = sum(nli_score * similarity for each evidence)
   ```

2. **Count evidence by label**:
   - Support count: Evidence labeled ENTAILMENT
   - Refute count: Evidence labeled CONTRADICTION
   - Neutral count: Evidence labeled NEUTRAL

3. **Determine verdict**:
   - **SUPPORTED**: `weighted_support > 0.6` and dominates other scores
   - **REFUTED**: `weighted_refute > 0.6` and dominates other scores
   - **INSUFFICIENT**: Not enough evidence or scores are inconclusive

4. **Calculate confidence**: Use the dominant weighted score as confidence

#### Verdict Thresholds

```python
HIGH_CONFIDENCE_THRESHOLD = 0.6
MIN_EVIDENCE_THRESHOLD = 2
```

### 6. Result Storage

**Duration:** 10-50ms

Store verification results in PostgreSQL:

#### Stored Data

1. **VerificationResult Table**:
   - Final verdict and confidence
   - Aggregated scores (support, refute, neutral)
   - Evidence counts by label
   - Human-readable reasoning
   - Pipeline metadata

2. **NLIResult Table** (one per evidence item):
   - Individual NLI predictions
   - All three class scores
   - Evidence and claim text (auditability)
   - Model metadata

### 7. Cache Update

**Duration:** <1ms

Cache the result for future requests:
- Cache key: SHA256 hash of normalized claim text
- Cache value: Complete VerificationPipelineResult
- Cache metadata: Timestamp for TTL calculation

## Data Structures

### VerificationPipelineResult

Complete result from pipeline execution:

```python
@dataclass
class VerificationPipelineResult:
    claim_id: UUID
    claim_text: str
    verdict: VerdictLabel  # SUPPORTED | REFUTED | INSUFFICIENT
    confidence: float  # 0.0 to 1.0
    support_score: float  # Weighted support score
    refute_score: float  # Weighted refutation score
    neutral_score: float  # Weighted neutral score
    evidence_items: list[EvidenceItem]  # Evidence with NLI results
    reasoning: str  # Human-readable explanation
    pipeline_duration_ms: float  # Total execution time
    retrieval_method: str  # "vector" | "hybrid" | "keyword"
    verification_result_id: Optional[UUID]  # Database ID if stored
```

### EvidenceItem

Evidence with NLI verification result:

```python
@dataclass
class EvidenceItem:
    evidence_id: UUID
    content: str
    source_url: Optional[str]
    similarity: float  # Vector similarity (0-1)
    nli_label: NLILabel  # ENTAILMENT | CONTRADICTION | NEUTRAL
    nli_confidence: float  # NLI confidence (0-1)
    nli_scores: dict[str, float]  # All NLI scores
```

## Error Handling & Resilience

### Retry Logic

Critical operations have automatic retry with exponential backoff:

```python
@retry_on_failure(
    max_attempts=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    exceptions=(RuntimeError,)
)
def _generate_embedding_with_retry(claim_text: str) -> list[float]:
    return self.embedding_service.embed_text(claim_text)
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: 1.0 second delay
- Attempt 3: 2.0 second delay
- Failure: Raise RuntimeError

### Graceful Degradation

The pipeline handles partial failures gracefully:

1. **No Evidence Found**: Return INSUFFICIENT verdict with confidence 0.0
2. **Storage Failure**: Log error but return result to client
3. **NLI Batch Failure**: Skip failed items, continue with successful ones
4. **Cache Failure**: Continue without caching, log warning

### Validation

Input validation at entry point:

```python
if not claim_text or not claim_text.strip():
    raise ValueError("Claim text cannot be empty")
```

## Performance Optimization

### Batching

- **NLI Verification**: Process all evidence pairs in batches (batch_size=8)
- **Vector Search**: Single query retrieves top-K results
- **Embedding**: Single embedding generation per claim

### Caching

Multi-level caching strategy:

1. **Pipeline Result Cache** (in-memory):
   - TTL: 1 hour (configurable)
   - Key: Claim text hash
   - Avoids full pipeline re-execution

2. **Model Cache** (singleton pattern):
   - Embedding model loaded once per process
   - NLI model loaded once per process
   - Shared across all pipeline instances

3. **Database Result Cache**:
   - Historical verification results in `verification_results` table
   - Can retrieve past verdicts for auditing

### Parallel Processing

Future optimization opportunity:
- Process multiple claims concurrently
- Parallel NLI inference with multiple workers
- Async database operations

## Usage Examples

### Basic Verification

```python
from truthgraph.services.verification_pipeline_service import (
    get_verification_pipeline_service
)
from truthgraph.db import SessionLocal

# Initialize service
service = get_verification_pipeline_service()

# Get database session
db = SessionLocal()

# Verify claim
result = await service.verify_claim(
    db=db,
    claim_id=claim_id,
    claim_text="The Earth orbits around the Sun",
    top_k_evidence=10,
    min_similarity=0.5,
    use_cache=True,
    store_result=True
)

print(f"Verdict: {result.verdict}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Evidence count: {len(result.evidence_items)}")
print(f"Duration: {result.pipeline_duration_ms:.0f}ms")
print(f"Reasoning: {result.reasoning}")

db.close()
```

### Custom Configuration

```python
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService
)
from truthgraph.services.ml.embedding_service import EmbeddingService
from truthgraph.services.ml.nli_service import NLIService
from truthgraph.services.vector_search_service import VectorSearchService

# Custom service configuration
service = VerificationPipelineService(
    embedding_service=EmbeddingService.get_instance(),
    nli_service=NLIService.get_instance(),
    vector_search_service=VectorSearchService(embedding_dimension=384),
    embedding_dimension=384,
    cache_ttl_seconds=7200  # 2 hours
)

# Use with custom parameters
result = await service.verify_claim(
    db=db,
    claim_id=claim_id,
    claim_text="Custom claim text",
    top_k_evidence=20,  # More evidence
    min_similarity=0.7,  # Higher threshold
    tenant_id="custom_tenant",
    use_cache=False,  # Bypass cache
    store_result=True
)
```

### Cache Management

```python
# Check cache status
cached_result = service._get_cached_result("Some claim text")
if cached_result:
    print("Cache hit!")
else:
    print("Cache miss")

# Clear cache manually
service.clear_cache()
print("Cache cleared")
```

## Performance Benchmarking

Run the included benchmark script:

```bash
python scripts/benchmark_verification_pipeline.py \
    --db-url "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph_test" \
    --iterations 5 \
    --use-cache \
    --store-results
```

**Expected Performance:**
- Mean duration: 5-30 seconds (with evidence)
- Median duration: 4-20 seconds
- 95th percentile: <60 seconds
- Cache hit latency: <10ms

## Testing

### Unit Tests

Run unit tests (15+ test cases):

```bash
pytest tests/unit/services/test_verification_pipeline_service.py -v
```

**Test Coverage:**
- Retry decorator functionality
- Service initialization
- Caching mechanisms
- Verdict aggregation logic
- Reasoning generation
- Error handling

### Integration Tests

Run integration tests (10+ test cases):

```bash
pytest tests/integration/test_verification_pipeline_integration.py -v -m integration
```

**Test Coverage:**
- End-to-end pipeline execution
- Database integration
- ML service integration
- Performance requirements
- Error handling and resilience

### Performance Tests

```bash
pytest tests/integration/test_verification_pipeline_integration.py -v -m slow
```

## Monitoring & Observability

### Structured Logging

All operations emit structured logs using `structlog`:

```python
logger.info(
    "verification_pipeline_complete",
    claim_id=str(claim_id),
    verdict=verdict_result.verdict.value,
    confidence=verdict_result.confidence,
    evidence_count=len(evidence_items),
    total_duration_ms=total_duration
)
```

### Key Metrics to Monitor

1. **Pipeline Duration**: Total end-to-end time
2. **Cache Hit Rate**: Percentage of cached results
3. **Evidence Retrieval Count**: Average evidence per claim
4. **Verdict Distribution**: SUPPORTED/REFUTED/INSUFFICIENT ratios
5. **Confidence Scores**: Average confidence by verdict type
6. **Error Rates**: Retry counts, failure rates

### Logging Events

- `verification_pipeline_start`: Pipeline execution begins
- `claim_embedding_generated`: Embedding created
- `evidence_retrieved`: Evidence search complete
- `nli_verification_complete`: NLI batch processed
- `verdict_aggregated`: Final verdict determined
- `verification_result_stored`: Result saved to database
- `verification_pipeline_complete`: Pipeline finished
- `cache_hit`: Result served from cache
- `cache_expired`: Cache entry expired
- `operation_failed_retrying`: Retry in progress
- `operation_failed_max_retries`: All retries exhausted

## Future Enhancements

### Planned Features

1. **Hybrid Search Integration**:
   - Combine vector search with keyword search
   - Improve evidence retrieval quality

2. **Advanced Verdict Aggregation**:
   - ML-based aggregation model
   - Source credibility weighting
   - Temporal evidence analysis

3. **Async/Parallel Processing**:
   - Concurrent claim verification
   - Parallel NLI inference
   - Non-blocking database operations

4. **Enhanced Caching**:
   - Distributed cache (Redis)
   - Evidence-level caching
   - Partial result caching

5. **Explainability**:
   - Attention visualization
   - Evidence highlighting
   - Counterfactual explanations

6. **Real-time Updates**:
   - WebSocket support for live verification
   - Progress streaming
   - Partial results

## Troubleshooting

### Common Issues

#### Pipeline Timeout

**Problem**: Pipeline exceeds 60s target

**Solutions:**
- Reduce `top_k_evidence` parameter
- Increase `min_similarity` threshold (fewer results)
- Decrease NLI batch size (faster individual batches)
- Enable caching for repeated claims
- Check database query performance

#### Low Confidence Verdicts

**Problem**: Most verdicts are INSUFFICIENT with low confidence

**Solutions:**
- Lower `min_similarity` threshold (more evidence)
- Increase `top_k_evidence` (more diverse evidence)
- Verify evidence database is populated
- Check embedding quality

#### Memory Issues

**Problem**: High memory usage or OOM errors

**Solutions:**
- Reduce NLI batch size
- Implement batch size auto-tuning based on available memory
- Clear model cache periodically
- Use smaller embedding model (if acceptable)

#### Cache Growing Too Large

**Problem**: In-memory cache consuming excessive memory

**Solutions:**
- Reduce `cache_ttl_seconds`
- Implement LRU eviction policy
- Clear cache periodically with `service.clear_cache()`
- Consider external cache (Redis)

## API Reference

See inline documentation in `verification_pipeline_service.py` for detailed API reference.

### Key Methods

- `verify_claim()`: Main pipeline entry point
- `_generate_embedding_with_retry()`: Embedding generation with retry
- `_search_evidence_with_retry()`: Evidence search with retry
- `_verify_evidence_batch()`: Batch NLI verification
- `_aggregate_verdict()`: Verdict aggregation
- `_store_verification_result()`: Database storage
- `clear_cache()`: Clear result cache

### Configuration Parameters

- `embedding_dimension`: Embedding vector dimension (384 or 1536)
- `cache_ttl_seconds`: Cache time-to-live
- `top_k_evidence`: Number of evidence items to retrieve
- `min_similarity`: Minimum similarity threshold
- `tenant_id`: Tenant identifier for isolation

## Contributing

When modifying the verification pipeline:

1. Maintain <60s performance target
2. Add comprehensive tests (unit + integration)
3. Update documentation and diagrams
4. Run benchmarks before/after changes
5. Consider backward compatibility
6. Add structured logging for new operations

## License

Part of TruthGraph Phase 2 ML-Enhanced Verification System
