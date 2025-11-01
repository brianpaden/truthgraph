# Profiling Scripts
## Performance Analysis Tools for TruthGraph ML Services

This directory contains profiling and optimization tools for analyzing and improving the performance of TruthGraph's ML services, specifically the embedding and NLI (Natural Language Inference) services.

---

## Overview

The profiling scripts help you:
- **Measure performance**: Throughput, latency, memory usage
- **Identify bottlenecks**: Find performance issues and optimization opportunities
- **Optimize configurations**: Determine optimal batch sizes and settings
- **Validate accuracy**: Ensure optimizations don't degrade model accuracy
- **Monitor trends**: Track performance over time

---

## Available Scripts

### Embedding Profiling (Feature 2.1)

| Script | Purpose | Documentation |
|--------|---------|---------------|
| `profile_batch_sizes.py` | Profile embedding batch sizes | [Profiling Guide](../../docs/profiling/profiling_guide.md) |
| `profile_memory.py` | Memory usage analysis | [Profiling Guide](../../docs/profiling/profiling_guide.md) |
| `profile_text_lengths.py` | Text length impact analysis | [Profiling Guide](../../docs/profiling/profiling_guide.md) |

### NLI Profiling (Feature 2.2)

| Script | Purpose | Documentation |
|--------|---------|---------------|
| `profile_nli.py` | Comprehensive NLI performance profiling | [NLI Profiling Guide](../../docs/profiling/nli_profiling_guide.md) |
| `nli_batch_optimization.py` | Batch size optimization with accuracy validation | [NLI Profiling Guide](../../docs/profiling/nli_profiling_guide.md) |

---

## Quick Start

### Profile NLI Service

```bash
# Basic profiling
python scripts/profiling/profile_nli.py

# With custom batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 8,16,32,64

# With more test data
python scripts/profiling/profile_nli.py --num-pairs 200
```

### Optimize NLI Batch Size

```bash
# Full optimization with accuracy validation
python scripts/profiling/nli_batch_optimization.py --validate-accuracy

# Test specific batch sizes
python scripts/profiling/nli_batch_optimization.py --batch-sizes 16,32,64
```

### Profile Embedding Service

```bash
# Profile batch sizes
python scripts/profiling/profile_batch_sizes.py

# Profile memory usage
python scripts/profiling/profile_memory.py

# Profile text length impact
python scripts/profiling/profile_text_lengths.py
```

---

## Results Location

Profiling results are saved to `scripts/profiling/results/` with timestamped filenames:

```
scripts/profiling/results/
├── nli_profile_2025-10-31.json              # NLI performance profile
├── nli_batch_analysis_2025-10-31.json       # NLI batch optimization
├── batch_size_profile_2025-10-31.json       # Embedding batch profile
├── memory_analysis_2025-10-31.json          # Embedding memory analysis
└── text_length_profile_2025-10-31.json      # Embedding text length analysis
```

---

## Performance Targets

### NLI Service (Feature 2.2)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Throughput | >2 pairs/sec | 77.48 pairs/sec | ✅ **38.7x target** |
| Latency | <500 ms/pair | 12.91 ms/pair | ✅ **38.7x faster** |
| Memory | <4GB total | <200 MB total | ✅ **Well under limit** |
| Accuracy | No degradation | 0.69 (constant) | ✅ **Zero degradation** |

### Embedding Service (Feature 2.1)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Throughput | >500 texts/sec | 1,493 texts/sec | ✅ **299% of target** |
| Memory | <2GB | 657 MB peak | ✅ **Well under limit** |
| Batch Size | Optimized | 64 (recommended) | ✅ **Optimal found** |

---

## Key Findings

### NLI Service Optimization (Feature 2.2)

**Performance**:
- **Best throughput**: 77.48 pairs/sec @ batch_size=32
- **Recommended**: 64.74 pairs/sec @ batch_size=16 (balanced)
- **Memory efficient**: 15.09 pairs/sec @ batch_size=1

**Key Insights**:
1. **Batch size critical**: 5.1x improvement from batch_size=1 to batch_size=32
2. **Accuracy maintained**: Perfect consistency (0.69) across all batch sizes
3. **Diminishing returns**: Returns slow after batch_size=16
4. **Memory scales linearly**: ~2.8 MB per batch size increment

**Recommendations**:
- Use batch_size=16 for production (balanced)
- Implement batch accumulation for consistent batching
- Truncate inputs to 256 characters
- Target exceeded by 38.7x - no GPU needed

### Embedding Service Optimization (Feature 2.1)

**Performance**:
- **Peak throughput**: 1,493 texts/sec @ batch_size=256
- **Recommended**: 1,341 texts/sec @ batch_size=64
- **Memory efficient**: 1,018 texts/sec @ batch_size=32

**Key Insights**:
1. **Small batches inefficient**: 64.7% performance loss @ batch_size=8
2. **Text length impact**: 89% performance drop for long texts
3. **No memory leaks**: Stable over 10 iterations
4. **Optimal range**: batch_size=64-128

**Recommendations**:
- Increase default batch size to 64
- Truncate texts to 256 characters
- Implement memory-aware batch sizing

---

## Documentation

### Comprehensive Guides

- **[NLI Profiling Guide](../../docs/profiling/nli_profiling_guide.md)**: Complete guide to NLI profiling
- **[NLI Optimization Analysis](../../docs/profiling/nli_optimization_analysis.md)**: Detailed performance analysis
- **[NLI Optimization Recommendations](../../docs/profiling/nli_optimization_recommendations.md)**: Actionable optimization steps
- **[Embedding Service Analysis](../../docs/profiling/embedding_service_analysis.md)**: Embedding profiling results
- **[Profiling Guide](../../docs/profiling/profiling_guide.md)**: General profiling guide

### Quick References

**NLI Service**:
- Model: `cross-encoder/nli-deberta-v3-base`
- Optimal batch size: 16
- Expected throughput: 64.74 pairs/sec
- Memory usage: 51.5 MB delta

**Embedding Service**:
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Optimal batch size: 64
- Expected throughput: 1,341 texts/sec
- Memory usage: 530 MB total

---

## Testing

Tests for profiling infrastructure:

```bash
# Run all profiling tests
pytest tests/test_nli_profiling.py -v

# Run specific test class
pytest tests/test_nli_profiling.py::TestNLIProfiler -v

# Run with coverage
pytest tests/test_nli_profiling.py --cov=scripts/profiling
```

**Test Coverage**: 37 tests, 100% pass rate

---

## Common Use Cases

### 1. Pre-Deployment Performance Check

```bash
# Profile NLI performance before deployment
python scripts/profiling/profile_nli.py --batch-sizes 8,16,32

# Verify accuracy hasn't degraded
python scripts/profiling/nli_batch_optimization.py --validate-accuracy --num-pairs 200

# Review results
cat scripts/profiling/results/nli_profile_*.json
```

### 2. Troubleshooting Performance Issues

```bash
# Profile with multiple batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 1,4,8,16,32,64

# Compare with baseline
diff <(cat scripts/profiling/results/nli_profile_2025-10-30.json) \
     <(cat scripts/profiling/results/nli_profile_2025-10-31.json)
```

### 3. Optimizing for Specific Hardware

```bash
# Profile on GPU machine
CUDA_VISIBLE_DEVICES=0 python scripts/profiling/profile_nli.py --batch-sizes 32,64,128

# Compare CPU vs GPU
python scripts/profiling/profile_nli.py --batch-sizes 16,32 --output cpu_results.json
```

### 4. Continuous Performance Monitoring

```bash
# Add to CI/CD pipeline
python scripts/profiling/profile_nli.py --num-pairs 100 --output nightly_profile.json

# Alert if performance degrades
python -c "
import json
with open('nightly_profile.json') as f:
    data = json.load(f)
    throughput = data['batch_profiles'][0]['throughput_pairs_per_sec']
    if throughput < 50:  # Below acceptable threshold
        print('ALERT: Performance degraded')
        exit(1)
"
```

---

## Interpreting Results

### Console Output

Profiling scripts print summaries to console:

```
================================================================================
NLI PROFILING SUMMARY
================================================================================

System: cpu | Model: cross-encoder/nli-deberta-v3-base

Batch Size Performance:
--------------------------------------------------------------------------------
 Batch |    Pairs/Sec |   Latency (ms) |   Memory (MB)
--------------------------------------------------------------------------------
     1 |        14.35 |          69.69 |           2.5
     4 |        36.78 |          27.19 |          19.4
     8 |        50.22 |          19.91 |          31.1
    16 |        64.05 |          15.61 |          51.7
    32 |        68.52 |          14.59 |          67.6
```

**How to Read**:
- **Pairs/Sec**: Higher is better (target: >2)
- **Latency (ms)**: Lower is better (target: <500)
- **Memory (MB)**: Memory delta during processing

### JSON Results

Results are saved as JSON for programmatic analysis:

```json
{
  "timestamp": "2025-10-31T21:02:49...",
  "system": {
    "device": "cpu",
    "model": "cross-encoder/nli-deberta-v3-base"
  },
  "batch_profiles": [
    {
      "batch_size": 16,
      "throughput_pairs_per_sec": 64.74,
      "latency_ms_per_pair": 15.45,
      "memory_delta_mb": 51.5,
      "accuracy_metrics": {...}
    }
  ],
  "bottlenecks": [...],
  "recommendations": [...]
}
```

---

## Best Practices

### 1. Run Multiple Iterations

```bash
# Run 3 times and average for reliability
for i in {1..3}; do
    python scripts/profiling/profile_nli.py --output run_$i.json
done

# Analyze variance
python -c "
import json
import glob
throughputs = []
for file in glob.glob('run_*.json'):
    with open(file) as f:
        data = json.load(f)
        throughputs.append(data['batch_profiles'][0]['throughput_pairs_per_sec'])
print(f'Average: {sum(throughputs)/len(throughputs):.2f}')
print(f'Variance: {max(throughputs) - min(throughputs):.2f}')
"
```

### 2. Document System Configuration

Always record:
- Hardware: CPU/GPU model, cores, memory
- Software: Python, PyTorch, CUDA versions
- Load: Other running processes
- Environment: Development, staging, production

### 3. Version Control Results

```bash
# Commit profiling results
git add scripts/profiling/results/
git commit -m "NLI profiling results for v2.2"
git tag profiling-nli-v2.2
```

### 4. Set Up Monitoring

```python
# Add to production monitoring
from scripts.profiling.profile_nli import NLIProfiler

profiler = NLIProfiler()
metrics = profiler.profile_batch_size(batch_size=16, num_pairs=10)

# Log to monitoring system
logger.info(
    "nli_performance_check",
    throughput=metrics["throughput_pairs_per_sec"],
    latency=metrics["latency_ms_per_pair"],
    memory=metrics["memory_delta_mb"]
)
```

---

## Troubleshooting

### Issue: Low Throughput

**Symptoms**: Throughput significantly below expected

**Diagnosis**:
```bash
# Check actual batch size
python scripts/profiling/profile_nli.py --batch-sizes 1,8,16,32
```

**Solutions**:
- Increase batch size to 16+
- Implement batch accumulation
- Check for serial processing

### Issue: High Memory Usage

**Symptoms**: Out of memory errors

**Diagnosis**:
```bash
# Profile memory at different batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 1,4,8,16
```

**Solutions**:
- Reduce batch size
- Enable model quantization
- Check for memory leaks

### Issue: Inconsistent Results

**Symptoms**: Results vary significantly between runs

**Diagnosis**:
- Check system load: `top` or `htop`
- Monitor temperature: CPU throttling
- Verify no other ML models running

**Solutions**:
- Run during low-load periods
- Close unnecessary applications
- Use `--num-pairs 200` for better statistics

---

## Contributing

When adding new profiling scripts:

1. Follow existing naming convention: `profile_*.py`
2. Save results to `scripts/profiling/results/`
3. Add tests to `tests/test_*_profiling.py`
4. Update this README
5. Document in `docs/profiling/`

---

## References

### Related Features

- **Feature 2.1**: Embedding Service Profiling
- **Feature 2.2**: NLI Service Optimization
- **Feature 2.3**: Vector Search Index Optimization
- **Feature 2.4**: Pipeline End-to-End Optimization
- **Feature 2.5**: Memory Optimization & Analysis

### External Documentation

- [DeBERTa-v3-base Model Card](https://huggingface.co/cross-encoder/nli-deberta-v3-base)
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [PyTorch Performance Tuning](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)

---

**Last Updated**: October 31, 2025
**Maintainer**: python-pro agent
**Version**: 1.0
