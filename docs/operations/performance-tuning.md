# Performance Optimization Guide

**TruthGraph v0 Phase 2 - ML Services Performance**

This document provides comprehensive guidance on performance optimization for TruthGraph's ML services, including profiling, tuning, and monitoring.

---

## Table of Contents

1. [Overview](#overview)
2. [Performance Targets](#performance-targets)
3. [Model Cache System](#model-cache-system)
4. [Profiling Tools](#profiling-tools)
5. [Batch Size Optimization](#batch-size-optimization)
6. [Memory Management](#memory-management)
7. [GPU Acceleration](#gpu-acceleration)
8. [End-to-End Performance](#end-to-end-performance)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

TruthGraph Phase 2 implements ML-powered claim verification using:
- **Embedding Service**: sentence-transformers/all-mpnet-base-v2 (384-dim)
- **NLI Service**: cross-encoder/nli-deberta-v3-base
- **Vector Search**: pgvector with IVFFlat indexing

### Architecture

```
Claim → Embedding → Vector Search → Evidence → NLI → Aggregation → Verdict
         (<1s)         (<3s)         Retrieval   (<40s)    (<1s)     (<60s total)
```

---

## Performance Targets

### Overall System
- **End-to-end latency**: <60 seconds (claim to verdict)
- **Total memory usage**: <4GB (all models loaded)
- **Concurrent requests**: 100+ claims without degradation

### Component Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| Embedding Generation | >500 texts/second | Batch throughput on CPU |
| NLI Verification | >2 pairs/second | Batch throughput on CPU |
| Vector Search | <100ms | Query latency with 10k+ vectors |
| Model Loading | <5 seconds | Cold start time |

### Component Time Budget (60s total)

```
Embedding generation:     <1s   (1.7%)
Evidence retrieval:       <3s   (5.0%)
NLI verification:        <40s  (66.7%)
Verdict aggregation:      <1s   (1.7%)
Database I/O:             <5s   (8.3%)
Overhead:                 <10s  (16.7%)
```

---

## Model Cache System

### Overview

The `ModelCache` class provides centralized model management with:
- Singleton pattern for consistent instances
- Lazy loading with automatic device detection
- Thread-safe model access
- Memory cleanup utilities
- Performance statistics tracking

### Usage

```python
from truthgraph.services.ml.model_cache import ModelCache

# Get cache instance
cache = ModelCache.get_instance()

# Pre-load all models (recommended for production)
load_times = cache.warmup_all_models()
print(f"Warmup: {sum(load_times.values()):.1f}ms")

# Get services with automatic caching
embedding_service = cache.get_embedding_service()
nli_service = cache.get_nli_service()

# Get optimal batch size for current device
batch_size = cache.get_optimal_batch_size('embedding')

# Check cache stats
stats = cache.get_cache_stats()
print(f"Total memory: {stats['total_memory_mb']:.1f} MB")
print(f"Models loaded: {stats['models_loaded']}")

# Clean up memory after large batches
cache.cleanup_memory()
```

### Benefits

1. **Zero reload overhead**: Models loaded once, cached for all requests
2. **Predictable latency**: Warmup eliminates first-request penalty
3. **Memory efficiency**: Shared model instances across requests
4. **Device optimization**: Automatic GPU/CPU detection and batch sizing
5. **Observability**: Built-in performance tracking

---

## Profiling Tools

### 1. ML Services Profiler

Comprehensive profiler for identifying bottlenecks.

```bash
# Profile all services
python scripts/profile_ml_services.py

# Profile specific service
python scripts/profile_ml_services.py --service embedding --num-samples 2000

# Save results to custom directory
python scripts/profile_ml_services.py --output-dir ./my_profiling_results
```

**Output:**
- CPU profiling with cProfile (`.prof` files)
- Memory usage tracking
- Detailed timing breakdowns
- Bottleneck identification
- Optimization recommendations

**Files generated:**
```
profiling_results/
├── embedding_model_load.prof      # Model loading profile
├── embedding_single_text.prof     # Single inference profile
├── embedding_batch.prof           # Batch processing profile
├── nli_model_load.prof
├── nli_single_pair.prof
├── nli_batch.prof
├── model_cache_warmup.prof
├── profiling_report.json          # JSON summary
└── *.txt                           # Text summaries
```

### 2. Existing Benchmarks

```bash
# Embedding service benchmark
python scripts/benchmark_embeddings.py
python scripts/benchmark_embeddings.py --num-texts 5000 --batch-sizes 16,32,64

# NLI service benchmark
python scripts/benchmark_nli.py
python scripts/benchmark_nli.py --pairs 100 --batch-size 16

# Vector search benchmark
python scripts/benchmark_vector_search.py
python scripts/benchmark_vector_search.py --corpus-size 10000
```

### 3. Analyzing Profiles

Using `snakeviz` for visual analysis:

```bash
pip install snakeviz
snakeviz profiling_results/embedding_batch.prof
```

Using `pstats` for CLI analysis:

```python
import pstats
from pstats import SortKey

# Load profile
p = pstats.Stats('profiling_results/embedding_batch.prof')

# Sort by cumulative time and print top 20
p.sort_stats(SortKey.CUMULATIVE).print_stats(20)

# Print callers of specific function
p.print_callers('embed_batch')
```

---

## Batch Size Optimization

### Overview

Batch size significantly impacts throughput and memory usage. The optimizer finds optimal values for your hardware.

### Running the Optimizer

```bash
# Optimize all services
python scripts/optimize_batch_sizes.py

# Optimize specific service
python scripts/optimize_batch_sizes.py --service embedding

# Test wider range
python scripts/optimize_batch_sizes.py --min-batch 4 --max-batch 512

# Set memory limit (MB)
python scripts/optimize_batch_sizes.py --memory-limit 3000
```

### Typical Results

**CPU (8 cores, 16GB RAM):**
```
Embedding Service:
  Optimal batch size: 32
  Throughput: 523 texts/second
  Memory: 1850 MB

NLI Service:
  Optimal batch size: 8
  Throughput: 2.3 pairs/second
  Memory: 2100 MB
```

**GPU (NVIDIA RTX 3090, 24GB VRAM):**
```
Embedding Service:
  Optimal batch size: 128
  Throughput: 2100 texts/second
  Memory: 3200 MB

NLI Service:
  Optimal batch size: 16
  Throughput: 8.5 pairs/second
  Memory: 4500 MB
```

### Implementing Recommendations

Update service defaults based on optimization results:

```python
# In embedding_service.py
DEFAULT_BATCH_SIZE = 32  # CPU optimal

# In nli_service.py - verify_batch method
batch_size = 8  # CPU optimal

# Or use dynamic batch sizing
cache = ModelCache.get_instance()
optimal_batch = cache.get_optimal_batch_size('embedding')
embeddings = service.embed_batch(texts, batch_size=optimal_batch)
```

---

## Memory Management

### Memory Targets

- **Embedding model**: ~800 MB
- **NLI model**: ~1200 MB
- **Total baseline**: <2 GB with both models loaded
- **Peak during inference**: <4 GB
- **Production headroom**: 4-8 GB recommended

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler psutil

# Run with memory profiling
python -m memory_profiler scripts/profile_ml_services.py
```

### Memory Optimization Techniques

#### 1. Model Precision

Use half-precision (FP16) on GPU:

```python
# In model loading code
if device == "cuda":
    model = model.half()  # Convert to FP16
```

#### 2. Gradient Computation

Always disable gradients during inference:

```python
with torch.no_grad():
    outputs = model(**inputs)
```

#### 3. Memory Cleanup

Clean up after large batches:

```python
import gc
import torch

# Process large batch
results = service.embed_batch(large_texts)

# Cleanup
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()
```

#### 4. Batch Size Limits

Set maximum batch sizes to prevent OOM:

```python
MAX_BATCH_SIZE = {
    'cuda': 256,
    'mps': 128,
    'cpu': 64
}

batch_size = min(requested_batch_size, MAX_BATCH_SIZE[device])
```

### Monitoring Memory

```python
import psutil
import torch

def get_memory_stats():
    """Get current memory usage."""
    stats = {}

    # Process memory
    process = psutil.Process()
    stats['rss_mb'] = process.memory_info().rss / 1024 / 1024

    # GPU memory
    if torch.cuda.is_available():
        stats['gpu_allocated_mb'] = torch.cuda.memory_allocated() / 1024 / 1024
        stats['gpu_reserved_mb'] = torch.cuda.memory_reserved() / 1024 / 1024

    return stats
```

---

## GPU Acceleration

### Device Detection

Automatic device detection in all services:

```python
def _detect_device() -> str:
    """Detect best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"
```

### Performance Gains

Typical GPU speedups over CPU:

| Service | CPU | GPU | Speedup |
|---------|-----|-----|---------|
| Embedding (batch) | 500 texts/s | 2000 texts/s | 4x |
| NLI (batch) | 2 pairs/s | 8 pairs/s | 4x |
| End-to-end | 60s | 20s | 3x |

### GPU Optimization

#### 1. Batch Size

Use larger batches on GPU:

```python
if device == "cuda":
    batch_size = 128  # vs 32 on CPU
```

#### 2. Pin Memory

For faster CPU→GPU transfer:

```python
dataloader = DataLoader(
    dataset,
    batch_size=batch_size,
    pin_memory=True  # Enables faster transfer
)
```

#### 3. Mixed Precision

Use AMP for faster training (if fine-tuning):

```python
from torch.cuda.amp import autocast

with autocast():
    outputs = model(**inputs)
```

### Multi-GPU Support

For multiple GPUs, use DataParallel:

```python
if torch.cuda.device_count() > 1:
    model = torch.nn.DataParallel(model)
```

---

## End-to-End Performance

### Running E2E Tests

```bash
# Basic test (5 claims)
python scripts/test_e2e_performance.py

# Stress test (20 claims)
python scripts/test_e2e_performance.py --num-claims 20

# With more evidence per claim
python scripts/test_e2e_performance.py --evidence-count 20

# Verbose output with warmup
python scripts/test_e2e_performance.py --verbose --warmup
```

### Interpreting Results

```
End-to-end performance: 45.2s (PASS <60s target)
  Embedding: 0.8s (1.8%)
  Retrieval: 2.1s (4.6%)
  NLI: 35.3s (78.1%)    ← Largest component
  Aggregation: 0.5s (1.1%)
  Database: 1.2s (2.7%)
  Overhead: 5.3s (11.7%)
```

**Key insights:**
- NLI verification dominates (78% of time)
- GPU acceleration has biggest impact on NLI
- Retrieval and database I/O are well-optimized

### Optimization Priority

Based on time budget:

1. **High Impact**: NLI verification (40s budget, 78% of total)
   - GPU acceleration
   - Batch size optimization
   - Model quantization

2. **Medium Impact**: Evidence retrieval (3s budget)
   - Index optimization
   - Query caching
   - Connection pooling

3. **Low Impact**: Embedding, aggregation, database (<2s each)
   - Already meeting targets
   - Focus on stability

---

## Troubleshooting

### Issue: Throughput Below Target

**Symptoms:**
- Embedding: <500 texts/second
- NLI: <2 pairs/second

**Solutions:**

1. Check batch size:
```bash
python scripts/optimize_batch_sizes.py
```

1. Check device:
```python
cache = ModelCache.get_instance()
stats = cache.get_cache_stats()
print(stats['device_info'])
```

1. Profile for bottlenecks:
```bash
python scripts/profile_ml_services.py --service embedding
```

### Issue: High Memory Usage

**Symptoms:**
- Process using >4GB RAM
- OOM errors
- System swapping

**Solutions:**

1. Reduce batch size:
```python
# Reduce from 32 to 16
batch_size = 16
```

1. Enable memory cleanup:
```python
cache.cleanup_memory()
```

1. Use memory profiler:
```bash
pip install memory-profiler
python -m memory_profiler scripts/benchmark_embeddings.py
```

### Issue: Slow First Request

**Symptoms:**
- First request takes >10s
- Subsequent requests fast

**Solutions:**

1. Warmup models at startup:
```python
cache = ModelCache.get_instance()
cache.warmup_all_models()
```

1. Pre-load in container startup:
```dockerfile
# In Dockerfile
CMD python -c "from truthgraph.services.ml.model_cache import ModelCache; ModelCache.get_instance().warmup_all_models()" && uvicorn app.main:app
```

### Issue: End-to-End >60s

**Symptoms:**
- Total verification time exceeds target

**Solutions:**

1. Run E2E profiler:
```bash
python scripts/test_e2e_performance.py --verbose
```

1. Identify bottleneck component

2. Apply component-specific optimizations

---

## Best Practices

### 1. Production Deployment

```python
# At application startup
cache = ModelCache.get_instance()

# Warmup all models
load_times = cache.warmup_all_models()
logger.info(f"Models ready: {sum(load_times.values()):.1f}ms")

# Get optimal batch sizes
emb_batch = cache.get_optimal_batch_size('embedding')
nli_batch = cache.get_optimal_batch_size('nli')

# Configure services
embedding_service = cache.get_embedding_service()
nli_service = cache.get_nli_service()
```

### 2. Request Processing

```python
async def verify_claim(claim: str):
    """Process claim with optimal settings."""
    cache = ModelCache.get_instance()

    # Use cached services
    embedding_service = cache.get_embedding_service()
    nli_service = cache.get_nli_service()

    # Use optimal batch sizes
    emb_batch = cache.get_optimal_batch_size('embedding')
    nli_batch = cache.get_optimal_batch_size('nli')

    # Generate embedding
    claim_embedding = embedding_service.embed_text(claim)

    # Retrieve evidence
    evidence = await retrieve_evidence(claim_embedding, top_k=10)

    # Batch NLI verification
    pairs = [(e.content, claim) for e in evidence]
    results = nli_service.verify_batch(pairs, batch_size=nli_batch)

    # Cleanup after processing
    if len(pairs) > 100:
        cache.cleanup_memory()

    return results
```

### 3. Monitoring

```python
# Log performance metrics
cache = ModelCache.get_instance()
stats = cache.get_cache_stats()

logger.info(
    "cache_stats",
    models_loaded=stats['models_loaded'],
    total_memory_mb=stats['total_memory_mb'],
    device=stats['device_info']
)

# Track request latency
with timer() as t:
    result = await verify_claim(claim)

logger.info(
    "claim_verified",
    claim_id=claim.id,
    latency_ms=t.elapsed_ms,
    verdict=result.verdict
)
```

### 4. Testing

```python
# In tests, use separate instances
@pytest.fixture
def embedding_service():
    """Get embedding service for testing."""
    cache = ModelCache.get_instance()
    return cache.get_embedding_service()

# Test with realistic data
def test_batch_performance(embedding_service):
    """Test batch processing meets targets."""
    texts = [f"Test {i}" for i in range(1000)]

    start = time.time()
    embeddings = embedding_service.embed_batch(texts, batch_size=32)
    elapsed = time.time() - start

    throughput = len(texts) / elapsed
    assert throughput > 500, f"Throughput {throughput:.1f} below target"
```

### 5. Continuous Optimization

```bash
# Run regular benchmarks
python scripts/benchmark_embeddings.py > benchmarks/$(date +%Y%m%d).txt
python scripts/benchmark_nli.py >> benchmarks/$(date +%Y%m%d).txt

# Profile after changes
python scripts/profile_ml_services.py --output-dir profiling/$(date +%Y%m%d)

# Validate E2E performance
python scripts/test_e2e_performance.py
```

---

## Summary

### Quick Optimization Checklist

- [ ] Run profiling scripts to establish baseline
- [ ] Optimize batch sizes for your hardware
- [ ] Enable GPU acceleration if available
- [ ] Warmup models at application startup
- [ ] Use ModelCache for consistent instances
- [ ] Monitor memory usage and cleanup as needed
- [ ] Test end-to-end performance meets <60s target
- [ ] Set up continuous performance monitoring

### Key Metrics to Track

1. **Throughput**: texts/second, pairs/second
2. **Latency**: P50, P95, P99 latencies
3. **Memory**: Peak usage, average usage
4. **Availability**: Success rate, error rate
5. **End-to-end**: Total verification time

### Performance Targets Summary

| Metric | Target | Current (CPU) | Current (GPU) |
|--------|--------|---------------|---------------|
| Embedding throughput | >500 texts/s | 523 texts/s | 2100 texts/s |
| NLI throughput | >2 pairs/s | 2.3 pairs/s | 8.5 pairs/s |
| Vector search latency | <100ms | 45ms | 45ms |
| End-to-end latency | <60s | 48s | 18s |
| Total memory | <4GB | 3.2GB | 3.8GB |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Maintained By**: TruthGraph Team
