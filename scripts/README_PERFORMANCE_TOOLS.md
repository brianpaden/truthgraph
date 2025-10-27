# Performance Optimization Tools - Quick Start Guide

This directory contains performance optimization and profiling tools for TruthGraph's ML services.

---

## Quick Start

### 1. Run All Benchmarks (Baseline)

```bash
# Establish performance baseline
python scripts/benchmark_embeddings.py
python scripts/benchmark_nli.py
python scripts/benchmark_vector_search.py
```

### 2. Profile for Bottlenecks

```bash
# Profile all services
python scripts/profile_ml_services.py

# Check results
cat profiling_results/profiling_report.json
```

### 3. Optimize Batch Sizes

```bash
# Find optimal batch sizes for your hardware
python scripts/optimize_batch_sizes.py

# Results saved to: batch_size_optimization_results.json
```

### 4. Test End-to-End Performance

```bash
# Validate complete pipeline
python scripts/test_e2e_performance.py --warmup

# Should see: PASS <60s target
```

---

## Available Scripts

### Existing Benchmarks

| Script | Purpose | Runtime | Output |
|--------|---------|---------|--------|
| `benchmark_embeddings.py` | Test embedding throughput | ~2 min | >500 texts/s target |
| `benchmark_nli.py` | Test NLI throughput | ~1 min | >2 pairs/s target |
| `benchmark_vector_search.py` | Test vector search latency | ~1 min | <100ms target |

### New Performance Tools

| Script | Purpose | Runtime | Output |
|--------|---------|---------|--------|
| `profile_ml_services.py` | Identify bottlenecks | ~3 min | .prof files + JSON report |
| `optimize_batch_sizes.py` | Find optimal batch sizes | ~5 min | Batch size recommendations |
| `test_e2e_performance.py` | End-to-end validation | ~2 min | Component breakdown |

---

## Common Workflows

### Initial Setup

```bash
# 1. Profile current performance
python scripts/profile_ml_services.py --output-dir baseline_profile

# 2. Optimize batch sizes
python scripts/optimize_batch_sizes.py

# 3. Test end-to-end
python scripts/test_e2e_performance.py --num-claims 10
```

### After Code Changes

```bash
# 1. Re-run benchmarks
python scripts/benchmark_embeddings.py > benchmarks/after_changes.txt
python scripts/benchmark_nli.py >> benchmarks/after_changes.txt

# 2. Compare with baseline
diff benchmarks/baseline.txt benchmarks/after_changes.txt

# 3. Validate E2E still meets targets
python scripts/test_e2e_performance.py
```

### Production Deployment

```bash
# 1. Warmup test
python -c "
from truthgraph.services.ml.model_cache import ModelCache
cache = ModelCache.get_instance()
times = cache.warmup_all_models()
print(f'Warmup: {sum(times.values()):.1f}ms')
"

# 2. Smoke test
python scripts/test_e2e_performance.py --num-claims 3 --warmup

# 3. Load test (optional)
python scripts/test_e2e_performance.py --num-claims 20
```

---

## Script Details

### profile_ml_services.py

**Purpose**: Comprehensive performance profiling

**Usage**:
```bash
# Basic profiling
python scripts/profile_ml_services.py

# Profile specific service
python scripts/profile_ml_services.py --service embedding

# More samples for accuracy
python scripts/profile_ml_services.py --num-samples 2000

# Custom output directory
python scripts/profile_ml_services.py --output-dir ./my_results
```

**Output**:
- `profiling_results/*.prof` - cProfile data files
- `profiling_results/*.txt` - Text summaries
- `profiling_results/profiling_report.json` - Comprehensive JSON report

**Analyzing .prof files**:
```bash
# Install snakeviz for visual analysis
pip install snakeviz

# Open in browser
snakeviz profiling_results/embedding_batch.prof

# Or use pstats in Python
python -m pstats profiling_results/embedding_batch.prof
```

### optimize_batch_sizes.py

**Purpose**: Find optimal batch sizes for maximum throughput

**Usage**:
```bash
# Optimize all services
python scripts/optimize_batch_sizes.py

# Optimize specific service
python scripts/optimize_batch_sizes.py --service embedding

# Custom batch size range
python scripts/optimize_batch_sizes.py --min-batch 4 --max-batch 512

# Set memory limit (MB)
python scripts/optimize_batch_sizes.py --memory-limit 3000
```

**Output**:
- Console: Detailed results and recommendations
- `batch_size_optimization_results.json` - Full results

**Typical Results**:
```text
Embedding Service (cpu):
  Recommended batch size: 32
  Expected throughput: 523 texts/second
  Memory usage: 1850 MB

NLI Service (cpu):
  Recommended batch size: 8
  Expected throughput: 2.3 pairs/second
  Memory usage: 2100 MB
```

### test_e2e_performance.py

**Purpose**: Validate end-to-end verification performance

**Usage**:
```bash
# Basic test
python scripts/test_e2e_performance.py

# More claims
python scripts/test_e2e_performance.py --num-claims 10

# More evidence per claim
python scripts/test_e2e_performance.py --evidence-count 20

# Verbose with warmup
python scripts/test_e2e_performance.py --verbose --warmup
```

**Output**:
```text
End-to-end performance: 48.32s (PASS <60s target)
  Embedding: 0.8s (1.7%)
  Retrieval: 2.1s (4.4%)
  NLI: 35.3s (73.0%)
  Aggregation: 0.5s (1.0%)
  Database: 0.1s (0.2%)
  Overhead: 5.3s (11.0%)
```

---

## Performance Targets

### Component Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| Embedding throughput | >500 texts/s | Batch processing on CPU |
| NLI throughput | >2 pairs/s | Batch processing on CPU |
| Vector search | <100ms | Single query latency |
| Model loading | <5s | Cold start time |
| Total memory | <4GB | All models loaded |

### End-to-End Target

**Total**: <60 seconds from claim to verdict

**Breakdown**:
- Embedding: <1s
- Retrieval: <3s
- NLI: <40s
- Aggregation: <1s
- Database: <5s
- Overhead: <10s

---

## Troubleshooting

### Performance Below Target

**Problem**: Throughput below 500 texts/s or 2 pairs/s

**Solution**:
```bash
# 1. Profile to find bottleneck
python scripts/profile_ml_services.py --service embedding

# 2. Optimize batch size
python scripts/optimize_batch_sizes.py --service embedding

# 3. Check device being used
python -c "
from truthgraph.services.ml.model_cache import ModelCache
cache = ModelCache.get_instance()
stats = cache.get_cache_stats()
print(stats['device_info'])
"
```

### High Memory Usage

**Problem**: Process using >4GB RAM

**Solution**:
```bash
# 1. Check current memory
python scripts/profile_ml_services.py --service cache

# 2. Reduce batch size
python scripts/optimize_batch_sizes.py --memory-limit 3000

# 3. Enable memory profiling
pip install memory-profiler
python -m memory_profiler scripts/benchmark_embeddings.py
```

### Slow First Request

**Problem**: First request takes >10 seconds

**Solution**:
```python
# Add to application startup
from truthgraph.services.ml.model_cache import ModelCache

cache = ModelCache.get_instance()
cache.warmup_all_models()  # Pre-load all models
```

### E2E >60 seconds

**Problem**: End-to-end verification exceeds target

**Solution**:
```bash
# 1. Profile E2E with breakdown
python scripts/test_e2e_performance.py --verbose

# 2. Identify slowest component
# 3. Profile that component specifically
python scripts/profile_ml_services.py --service [component]

# 4. Apply component-specific optimizations
```

---

## Model Cache Usage

### Basic Usage

```python
from truthgraph.services.ml.model_cache import ModelCache

# Get cache instance
cache = ModelCache.get_instance()

# Get services (loaded once, cached)
embedding_service = cache.get_embedding_service()
nli_service = cache.get_nli_service()

# Use services normally
embeddings = embedding_service.embed_batch(texts)
results = nli_service.verify_batch(pairs)
```

### Production Setup

```python
# In main.py or app startup
from fastapi import FastAPI
from truthgraph.services.ml.model_cache import ModelCache

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Warmup models at startup."""
    cache = ModelCache.get_instance()
    load_times = cache.warmup_all_models()
    print(f"Models ready: {sum(load_times.values()):.1f}ms")

@app.get("/health/models")
async def health_models():
    """Health check for models."""
    cache = ModelCache.get_instance()
    stats = cache.get_cache_stats()
    return {
        "models_loaded": stats["models_loaded"],
        "total_memory_mb": stats["total_memory_mb"],
        "device": stats["device_info"]
    }
```

### Advanced Features

```python
# Get optimal batch size for current device
batch_size = cache.get_optimal_batch_size('embedding')

# Process with optimal settings
embeddings = embedding_service.embed_batch(
    texts,
    batch_size=batch_size
)

# Clean up memory after large batches
if len(texts) > 1000:
    cache.cleanup_memory()

# Monitor cache statistics
stats = cache.get_cache_stats()
print(f"Embedding accesses: {stats['model_stats']['embedding']['access_count']}")
print(f"NLI accesses: {stats['model_stats']['nli']['access_count']}")
```

---

## GPU Acceleration

### Enabling GPU

GPU is automatically detected and used if available:

```python
from truthgraph.services.ml.model_cache import ModelCache

cache = ModelCache.get_instance()
stats = cache.get_cache_stats()

# Check device
device_info = stats['device_info']
print(f"CUDA available: {device_info['cuda_available']}")
if device_info['cuda_available']:
    print(f"Device: {device_info['cuda_device']}")
```

### Expected Speedups

| Component | CPU | GPU | Speedup |
|-----------|-----|-----|---------|
| Embedding (batch) | 500 texts/s | 2000 texts/s | 4x |
| NLI (batch) | 2 pairs/s | 8 pairs/s | 4x |
| End-to-end | 60s | 20s | 3x |

### GPU-Optimized Batch Sizes

```bash
# Run optimizer with GPU
python scripts/optimize_batch_sizes.py

# Typical GPU results:
# Embedding: batch_size=128 (vs 32 on CPU)
# NLI: batch_size=16 (vs 8 on CPU)
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .[ml]
          pip install psutil

      - name: Run benchmarks
        run: |
          python scripts/benchmark_embeddings.py
          python scripts/benchmark_nli.py

      - name: Test E2E performance
        run: |
          python scripts/test_e2e_performance.py --num-claims 5

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: performance-results
          path: |
            profiling_results/
            batch_size_optimization_results.json
```

---

## Monitoring in Production

### Metrics to Track

```python
from prometheus_client import Histogram, Gauge

# Latency
embedding_latency = Histogram('embedding_latency_seconds', 'Embedding latency')
nli_latency = Histogram('nli_latency_seconds', 'NLI latency')
e2e_latency = Histogram('e2e_latency_seconds', 'E2E latency')

# Memory
memory_usage = Gauge('model_memory_mb', 'Model memory usage')

# Cache stats
cache_hits = Counter('cache_hits_total', 'Cache hits')
```

### Logging

```python
import structlog

logger = structlog.get_logger(__name__)

# Log cache stats periodically
cache = ModelCache.get_instance()
stats = cache.get_cache_stats()

logger.info(
    "cache_stats",
    models_loaded=stats['models_loaded'],
    total_memory_mb=stats['total_memory_mb'],
    embedding_accesses=stats['model_stats']['embedding']['access_count']
)
```

---

## Additional Resources

- **Full Documentation**: `docs/PERFORMANCE_OPTIMIZATION.md`
- **Implementation Summary**: `docs/FEATURE_10_IMPLEMENTATION_SUMMARY.md`
- **Model Cache API**: `truthgraph/services/ml/model_cache.py`

---

## Quick Reference

### Performance Checklist

- [ ] Run baseline benchmarks
- [ ] Profile for bottlenecks
- [ ] Optimize batch sizes
- [ ] Test E2E performance
- [ ] Warmup models at startup
- [ ] Monitor memory usage
- [ ] Enable GPU if available
- [ ] Set up continuous monitoring

### Common Commands

```bash
# Baseline
python scripts/benchmark_embeddings.py
python scripts/benchmark_nli.py

# Optimize
python scripts/profile_ml_services.py
python scripts/optimize_batch_sizes.py

# Validate
python scripts/test_e2e_performance.py
```

### Performance Targets Quick Reference

```text
✓ Embedding: >500 texts/s
✓ NLI: >2 pairs/s
✓ E2E: <60s
✓ Memory: <4GB
✓ Model load: <5s
✓ Vector search: <100ms
```

---

**Last Updated**: 2025-10-25
**Maintained By**: TruthGraph Team
