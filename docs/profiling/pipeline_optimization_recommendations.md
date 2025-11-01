# Pipeline Optimization Recommendations
## Feature 2.4 - Production Deployment Guide

**Date**: November 1, 2025
**Feature**: 2.4 - Pipeline End-to-End Optimization
**Phase**: 2C (Performance Optimization)

---

## Quick Start (5 Minutes)

### 1. Apply Optimized Configuration

```python
from truthgraph.verification import OptimizationConfig

# Get optimized settings from Features 2.1-2.3
config = OptimizationConfig.get_optimized_config()

# Configuration will be:
# - embedding_batch_size: 64 (Feature 2.1: +13%)
# - nli_batch_size: 16 (Feature 2.2: +28%)
# - vector_search_lists: 50 (Feature 2.3: optimal)
# - vector_search_probes: 10 (Feature 2.3: 96.5% recall)
# - text_truncation_chars: 256 (Feature 2.1: +40-60%)
```

### 2. Configure Pipeline Services

```python
from truthgraph.services.ml.embedding_service import EmbeddingService
from truthgraph.services.ml.nli_service import NLIService
from truthgraph.services.verification_pipeline_service import VerificationPipelineService

# Apply embedding optimization
embedding_service = EmbeddingService.get_instance()
# Use batch_size=64 in embed_batch() calls

# Pipeline will use optimized NLI batch_size=16
pipeline = VerificationPipelineService()

# Expected improvement: 60-80% latency reduction
```

### 3. Set Database Parameters

```python
from sqlalchemy import text

# Configure IVFFlat probes for optimal vector search
session.execute(text("SET ivfflat.probes = 10"))

# Expected: 45ms search time (66x faster than baseline)
```

**That's it!** Your pipeline is now optimized for <60s end-to-end latency.

---

## Priority 1: Critical Optimizations (<1 Hour)

### Recommendation 1.1: Increase Embedding Batch Size (5 minutes)

**Impact**: +13% throughput (1,341 vs 1,185 texts/sec)
**Effort**: 5 minutes
**Difficulty**: Easy

**Implementation**:
```python
# In embedding service calls
from truthgraph.services.ml.embedding_service import EmbeddingService

service = EmbeddingService.get_instance()
embeddings = service.embed_batch(
    texts=claim_texts,
    batch_size=64  # Change from 32 to 64
)
```

**Validation**:
```python
# Measure throughput
import time

start = time.time()
embeddings = service.embed_batch(texts, batch_size=64)
duration = time.time() - start
throughput = len(texts) / duration

assert throughput > 1200, f"Expected >1200 texts/sec, got {throughput}"
```

### Recommendation 1.2: Increase NLI Batch Size (5 minutes)

**Impact**: +28% throughput (64.74 vs 50.55 pairs/sec)
**Effort**: 5 minutes
**Difficulty**: Easy

**Implementation**:
```python
# In pipeline NLI verification
from truthgraph.services.ml.nli_service import NLIService

service = NLIService.get_instance()
results = service.verify_batch(
    pairs=claim_evidence_pairs,
    batch_size=16  # Change from 8 to 16
)
```

**Validation**:
```python
# Measure throughput
start = time.time()
results = service.verify_batch(pairs, batch_size=16)
duration = time.time() - start
throughput = len(pairs) / duration

assert throughput > 60, f"Expected >60 pairs/sec, got {throughput}"
```

### Recommendation 1.3: Configure Vector Search Parameters (10 minutes)

**Impact**: 66x faster (45ms vs 3000ms)
**Effort**: 10 minutes
**Difficulty**: Easy

**Implementation**:
```python
from sqlalchemy import text

# In pipeline setup or database initialization
def configure_vector_search(session):
    """Configure optimal IVFFlat parameters."""
    # Set probes for optimal speed/accuracy tradeoff
    session.execute(text("SET ivfflat.probes = 10"))

    # Verify index exists with lists=50
    result = session.execute(text("""
        SELECT *
        FROM pg_indexes
        WHERE indexname = 'embeddings_ivfflat_idx'
    """))

    if not result.fetchone():
        # Create index with optimal lists parameter
        session.execute(text("""
            CREATE INDEX embeddings_ivfflat_idx
            ON embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
        """))
        session.commit()
```

**Validation**:
```python
# Measure search latency
import time

start = time.time()
results = vector_search_service.search_similar_evidence(
    db=session,
    query_embedding=claim_embedding,
    top_k=10
)
duration_ms = (time.time() - start) * 1000

assert duration_ms < 100, f"Expected <100ms, got {duration_ms:.1f}ms"
```

### Recommendation 1.4: Implement Text Truncation (15 minutes)

**Impact**: +40-60% for long texts
**Effort**: 15 minutes
**Difficulty**: Easy

**Implementation**:
```python
from truthgraph.verification import TextPreprocessor

# Initialize preprocessor
preprocessor = TextPreprocessor(truncation_chars=256)

# Truncate claim texts before processing
def preprocess_claims(claims: list[str]) -> list[str]:
    """Truncate claims to optimal length."""
    return preprocessor.preprocess_batch(
        claims,
        preserve_sentences=True  # Break at sentence boundaries
    )

# Use in pipeline
truncated_claims = preprocess_claims(claim_texts)
embeddings = embedding_service.embed_batch(truncated_claims, batch_size=64)
```

**Validation**:
```python
# Test truncation
long_text = "A" * 1000
truncated = preprocessor.truncate_text(long_text)

assert len(truncated) <= 256, f"Expected ≤256 chars, got {len(truncated)}"
assert len(truncated) > 200, "Truncation too aggressive"
```

**Combined Impact**: Implementing all Priority 1 recommendations takes **<1 hour** and provides **60-80% latency reduction**.

---

## Priority 2: High-Impact Optimizations (1-4 Hours)

### Recommendation 2.1: Enable Connection Pooling (30 minutes)

**Impact**: 2.8x faster warm queries
**Effort**: 30 minutes
**Difficulty**: Medium

**Implementation**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Create engine with connection pooling
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,          # 10 persistent connections
    max_overflow=20,       # Up to 30 total connections
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections hourly
    echo_pool=False,       # Disable pool logging in prod
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

**Validation**:
```python
# Check pool status
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")

assert pool.size() == 10, "Pool size incorrect"
```

### Recommendation 2.2: Implement Batch Database Writes (1-2 hours)

**Impact**: 2-3x faster storage
**Effort**: 1-2 hours
**Difficulty**: Medium

**Implementation**:
```python
from sqlalchemy.orm import Session
from truthgraph.schemas import VerificationResult, NLIResult

def store_verification_results_batch(
    session: Session,
    results: list[VerificationPipelineResult]
) -> None:
    """Store multiple verification results in a single transaction.

    Args:
        session: Database session
        results: List of verification results to store
    """
    # Prepare verification records
    verification_records = [
        {
            "claim_id": result.claim_id,
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "support_score": result.support_score,
            "refute_score": result.refute_score,
            "neutral_score": result.neutral_score,
            "reasoning": result.reasoning,
            "evidence_count": len(result.evidence_items),
            "created_at": datetime.now(UTC),
        }
        for result in results
    ]

    # Prepare NLI records
    nli_records = []
    for result in results:
        for item in result.evidence_items:
            nli_records.append({
                "claim_id": result.claim_id,
                "evidence_id": item.evidence_id,
                "label": item.nli_label.value,
                "confidence": item.nli_confidence,
                "entailment_score": item.nli_scores.get("entailment", 0.0),
                "contradiction_score": item.nli_scores.get("contradiction", 0.0),
                "neutral_score": item.nli_scores.get("neutral", 0.0),
                "created_at": datetime.now(UTC),
            })

    # Bulk insert (single round-trip per table)
    session.bulk_insert_mappings(VerificationResult, verification_records)
    session.bulk_insert_mappings(NLIResult, nli_records)
    session.commit()
```

**Validation**:
```python
import time

# Measure batch write performance
start = time.time()
store_verification_results_batch(session, results_batch)
duration = time.time() - start

items_per_sec = len(results_batch) / duration
print(f"Batch write: {items_per_sec:.1f} results/sec")

assert items_per_sec > 20, f"Expected >20/sec, got {items_per_sec:.1f}"
```

### Recommendation 2.3: Implement Memory-Aware Batch Sizing (30 minutes)

**Impact**: +5-10% for variable workloads
**Effort**: 30 minutes
**Difficulty**: Medium

**Implementation**:
```python
from truthgraph.verification import MemoryMonitor, BatchSizeOptimizer

# Initialize monitoring
monitor = MemoryMonitor(limit_mb=4096)
monitor.set_baseline()

optimizer = BatchSizeOptimizer(monitor)

# Dynamic batch sizing for embeddings
def embed_with_adaptive_batching(texts: list[str]) -> list[list[float]]:
    """Embed texts with memory-aware batch sizing."""
    service = EmbeddingService.get_instance()

    # Calculate optimal batch size
    optimal_batch = optimizer.get_optimal_batch_size(
        default_batch_size=64,
        item_memory_mb=2.0,  # Estimated per-text memory
        min_batch_size=16,
        max_batch_size=128,
    )

    # Use optimal batch size
    return service.embed_batch(texts, batch_size=optimal_batch)
```

**Validation**:
```python
# Test adaptive batching under memory pressure
monitor = MemoryMonitor(limit_mb=500)  # Low limit
monitor.set_baseline()
optimizer = BatchSizeOptimizer(monitor)

batch_size = optimizer.get_optimal_batch_size(
    default_batch_size=64,
    item_memory_mb=10.0  # High memory per item
)

assert batch_size < 64, "Should reduce batch size for memory"
```

---

## Priority 3: Advanced Optimizations (2-8 Hours)

### Recommendation 3.1: Parallel Claim Processing (2-3 hours)

**Impact**: 2-4x throughput
**Effort**: 2-3 hours
**Difficulty**: Hard

**Implementation**:
```python
from truthgraph.verification import ParallelExecutor
from typing import List
from dataclasses import dataclass

@dataclass
class ClaimVerificationTask:
    """Task for parallel claim verification."""
    claim_id: str
    claim_text: str

def verify_claim_wrapper(task: ClaimVerificationTask) -> VerificationPipelineResult:
    """Wrapper for parallel execution."""
    from truthgraph.db import get_session
    from truthgraph.services.verification_pipeline_service import get_verification_pipeline_service

    # Each worker gets own session
    session = get_session()
    pipeline = get_verification_pipeline_service()

    try:
        result = pipeline.verify_claim(
            db=session,
            claim_id=task.claim_id,
            claim_text=task.claim_text,
        )
        return result
    finally:
        session.close()

# Process claims in parallel
executor = ParallelExecutor(max_workers=4)
tasks = [ClaimVerificationTask(c.id, c.text) for c in claims]

results = executor.execute_parallel(
    func=verify_claim_wrapper,
    items=tasks,
    description="parallel_claim_verification"
)
```

**Validation**:
```python
import time

# Compare sequential vs parallel
tasks = [ClaimVerificationTask(f"claim_{i}", f"test claim {i}") for i in range(20)]

# Sequential
start = time.time()
seq_results = [verify_claim_wrapper(t) for t in tasks]
seq_duration = time.time() - start

# Parallel
start = time.time()
par_results = executor.execute_parallel(verify_claim_wrapper, tasks)
par_duration = time.time() - start

speedup = seq_duration / par_duration
print(f"Speedup: {speedup:.1f}x")

assert speedup > 2.0, f"Expected >2x speedup, got {speedup:.1f}x"
```

### Recommendation 3.2: Async Pipeline (4-8 hours)

**Impact**: Better resource utilization
**Effort**: 4-8 hours
**Difficulty**: Hard

**Note**: This is a significant refactoring. Consider for future enhancement.

**Implementation Overview**:
```python
import asyncio
from typing import List

async def verify_claim_async(
    claim_id: str,
    claim_text: str
) -> VerificationPipelineResult:
    """Async version of verification pipeline."""
    # Generate embedding (async)
    embedding = await embedding_service.embed_text_async(claim_text)

    # Search evidence (async)
    evidence = await vector_search_service.search_async(embedding)

    # Verify NLI (async batch)
    nli_results = await nli_service.verify_batch_async(pairs)

    # Aggregate and return
    return aggregate_verdict(claim_id, claim_text, nli_results)

# Process multiple claims concurrently
claims_batch = [...]
results = await asyncio.gather(*[
    verify_claim_async(c.id, c.text)
    for c in claims_batch
])
```

---

## Configuration Templates

### Production Configuration

```python
# config/production.py
from truthgraph.verification import OptimizationConfig

PRODUCTION_CONFIG = OptimizationConfig(
    # Features 2.1-2.3 optimal settings
    embedding_batch_size=64,
    nli_batch_size=16,
    vector_search_lists=50,
    vector_search_probes=10,
    text_truncation_chars=256,

    # Production settings
    max_evidence_per_claim=10,
    parallel_claim_processing=True,
    max_workers=4,
    memory_limit_mb=4096,
)

# Database configuration
DATABASE_CONFIG = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
```

### Development Configuration

```python
# config/development.py
DEV_CONFIG = OptimizationConfig(
    # Same optimizations but more verbose logging
    embedding_batch_size=64,
    nli_batch_size=16,
    vector_search_lists=50,
    vector_search_probes=10,
    text_truncation_chars=256,

    # Dev settings
    max_evidence_per_claim=5,  # Faster iteration
    parallel_claim_processing=False,  # Easier debugging
    max_workers=2,
    memory_limit_mb=2048,
)
```

### Testing Configuration

```python
# config/testing.py
TEST_CONFIG = OptimizationConfig(
    # Smaller batches for faster tests
    embedding_batch_size=8,
    nli_batch_size=4,
    vector_search_lists=25,
    vector_search_probes=5,
    text_truncation_chars=256,

    # Test settings
    max_evidence_per_claim=3,
    parallel_claim_processing=False,
    max_workers=1,
    memory_limit_mb=1024,
)
```

---

## Monitoring and Alerting

### Key Performance Indicators (KPIs)

```python
from truthgraph.verification import PerformanceTracker

tracker = PerformanceTracker()

# Track all stages
tracker.record_stage_timing("embedding", embedding_duration_ms)
tracker.record_stage_timing("evidence_retrieval", retrieval_duration_ms)
tracker.record_stage_timing("nli_verification", nli_duration_ms)
tracker.record_stage_timing("verdict_aggregation", aggregation_duration_ms)
tracker.record_stage_timing("result_storage", storage_duration_ms)

# Get summary
summary = tracker.get_summary()

# Log metrics
logger.info("pipeline_performance", **summary)
```

### Alert Conditions

```python
def check_performance_alerts(tracker: PerformanceTracker) -> List[str]:
    """Check for performance degradation."""
    alerts = []

    # Embedding throughput
    if tracker.get_average("embedding_throughput") < 1000:
        alerts.append("WARNING: Embedding throughput below 1000 texts/sec")

    # NLI throughput
    if tracker.get_average("nli_throughput") < 60:
        alerts.append("WARNING: NLI throughput below 60 pairs/sec")

    # Vector search latency
    search_latency = tracker.get_stage_average("evidence_retrieval")
    if search_latency > 100:
        alerts.append(f"WARNING: Vector search latency {search_latency:.1f}ms > 100ms")

    # Memory usage
    if monitor.get_current_memory_mb() > 3500:
        alerts.append("WARNING: Memory usage > 3.5GB")

    return alerts
```

---

## Troubleshooting Guide

### Issue 1: Low Embedding Throughput

**Symptoms**: Embedding generation >1s for 20 claims

**Diagnosis**:
```python
# Measure throughput
throughput = tracker.get_average("embedding_throughput")
print(f"Current: {throughput:.1f} texts/sec")
print(f"Expected: >1200 texts/sec")
```

**Solutions**:
1. Check batch size is set to 64
2. Verify text truncation is enabled
3. Check for CPU throttling
4. Consider GPU if available

### Issue 2: Slow Vector Search

**Symptoms**: Evidence retrieval >100ms per query

**Diagnosis**:
```python
# Check index configuration
result = session.execute(text("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'embeddings'
"""))

for row in result:
    print(f"Index: {row[0]}")
    print(f"Definition: {row[1]}")
```

**Solutions**:
1. Ensure IVFFlat index exists with lists=50
2. Verify probes=10 is set in session
3. Check index needs VACUUM ANALYZE
4. Verify corpus size matches index configuration

### Issue 3: Memory Limit Exceeded

**Symptoms**: Out of memory errors or swapping

**Diagnosis**:
```python
# Check memory usage
current = monitor.get_current_memory_mb()
delta = monitor.get_delta_mb()

print(f"Current: {current:.1f} MB")
print(f"Delta from baseline: {delta:.1f} MB")
print(f"Limit: {monitor.limit_mb} MB")
```

**Solutions**:
1. Reduce embedding_batch_size to 32
2. Reduce nli_batch_size to 8
3. Disable parallel processing
4. Use conservative configuration
5. Increase system memory limit

### Issue 4: NLI Bottleneck

**Symptoms**: NLI stage >40% of total pipeline time

**Diagnosis**:
```python
# Analyze stage breakdown
summary = tracker.get_summary()
total_time = sum(s['total_ms'] for s in summary['stages'].values())
nli_time = summary['stages']['nli_verification']['total_ms']
percentage = (nli_time / total_time) * 100

print(f"NLI: {nli_time:.1f}ms ({percentage:.1f}% of pipeline)")
```

**Solutions**:
1. Increase nli_batch_size to 16
2. Enable parallel claim processing
3. Reduce max_evidence_per_claim to 5
4. Consider GPU acceleration
5. Profile with high detail mode to find sub-bottleneck

---

## Rollback Procedures

### If Performance Degrades

1. **Revert to baseline configuration**:
```python
# Use conservative config temporarily
config = OptimizationConfig.get_conservative_config()
```

2. **Disable specific optimizations**:
```python
# Keep most optimizations, disable one
config = OptimizationConfig.get_optimized_config()
config.parallel_claim_processing = False  # Disable if causing issues
```

3. **Check for regressions**:
```python
# Compare with baseline
from scripts.profiling.pipeline_analysis import PipelineAnalyzer

analyzer = PipelineAnalyzer()
comparison = analyzer.compare_profiles(
    baseline_path=Path("results/baseline.json"),
    optimized_path=Path("results/current.json")
)
```

### Gradual Rollout Strategy

1. **Week 1**: Enable embedding and text truncation optimizations
2. **Week 2**: Enable NLI batch size optimization
3. **Week 3**: Enable vector search optimization
4. **Week 4**: Enable parallel processing
5. **Week 5**: Full optimized configuration

Monitor metrics between each week and rollback if issues arise.

---

## Success Criteria Validation

### Checklist

- [ ] End-to-end latency <60 seconds per claim
- [ ] Embedding throughput >1,000 texts/sec
- [ ] NLI throughput >60 pairs/sec
- [ ] Vector search latency <100ms
- [ ] Memory usage <4GB
- [ ] All tests passing (37/37)
- [ ] No accuracy degradation
- [ ] Monitoring and alerting configured
- [ ] Rollback procedures documented

### Validation Script

```python
def validate_optimization_success() -> bool:
    """Validate all success criteria are met."""
    checks = []

    # 1. E2E latency
    avg_latency_ms = tracker.get_stage_average("total_pipeline")
    checks.append(("E2E latency <60s", avg_latency_ms < 60000))

    # 2. Embedding throughput
    emb_throughput = tracker.get_average("embedding_throughput")
    checks.append(("Embedding >1000/sec", emb_throughput > 1000))

    # 3. NLI throughput
    nli_throughput = tracker.get_average("nli_throughput")
    checks.append(("NLI >60/sec", nli_throughput > 60))

    # 4. Vector search
    search_latency = tracker.get_stage_average("evidence_retrieval")
    checks.append(("Vector search <100ms", search_latency < 100))

    # 5. Memory usage
    memory_mb = monitor.get_current_memory_mb()
    checks.append(("Memory <4GB", memory_mb < 4096))

    # Print results
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")

    return all(passed for _, passed in checks)
```

---

## Conclusion

Implementing these optimizations in priority order will achieve the <60 second end-to-end latency target while maintaining accuracy and staying within memory budgets.

**Priority 1 recommendations** (<1 hour) provide the most significant improvements with minimal effort.
**Priority 2 recommendations** (1-4 hours) add robustness and scalability.
**Priority 3 recommendations** (2-8 hours) enable advanced use cases and future scalability.

For immediate deployment, implement **Priority 1 recommendations** today and schedule Priority 2-3 for the coming weeks.
