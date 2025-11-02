# NLI Profiling Guide
## How to Profile and Optimize NLI Service Performance

**Date**: October 31, 2025
**Feature ID**: 2.2
**Version**: 1.0

---

## Overview

This guide explains how to use the NLI profiling tools to measure performance, identify bottlenecks, and optimize your NLI service configuration. Whether you're troubleshooting performance issues or fine-tuning for production, this guide provides step-by-step instructions.

**Target Audience**: Developers, DevOps engineers, Performance engineers
**Prerequisites**: Python 3.12+, TruthGraph installation, ML dependencies installed

---

## Quick Start

### Run Basic Profile

```bash
# Profile with default settings (batch sizes 1,4,8,16,32)
python scripts/profiling/profile_nli.py

# Results saved to: scripts/profiling/results/nli_profile_YYYY-MM-DD.json
```

### Run With Custom Settings

```bash
# Custom batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 8,16,32,64

# More test pairs for better statistics
python scripts/profiling/profile_nli.py --num-pairs 200

# Custom output location
python scripts/profiling/profile_nli.py --output /path/to/results.json
```

### Run Batch Optimization with Accuracy Validation

```bash
# Full optimization analysis with accuracy validation
python scripts/profiling/nli_batch_optimization.py --validate-accuracy

# Results saved to: scripts/profiling/results/nli_batch_analysis_YYYY-MM-DD.json
```

---

## Profiling Scripts

### Script 1: `profile_nli.py` - General Performance Profiling

**Purpose**: Comprehensive performance profiling including throughput, latency, memory, and bottleneck analysis.

#### Usage

```bash
python scripts/profiling/profile_nli.py [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--batch-sizes` | Comma-separated batch sizes to test | `1,4,8,16,32` |
| `--num-pairs` | Number of test pairs to use | `100` |
| `--output` | Output path for results JSON | `scripts/profiling/results/nli_profile_YYYY-MM-DD.json` |

#### Example Commands

```bash
# Test specific batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 16,32,64

# Test with more pairs (better statistics)
python scripts/profiling/profile_nli.py --num-pairs 500

# Save to custom location
python scripts/profiling/profile_nli.py --output my_results.json

# Combined options
python scripts/profiling/profile_nli.py \
    --batch-sizes 8,16,32 \
    --num-pairs 200 \
    --output production_profile.json
```

#### Output

**Console Output**:
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

Bottlenecks Identified:
--------------------------------------------------------------------------------
1. [HIGH] Single-pair processing is 377.5% slower than optimal batch size

Recommendations:
--------------------------------------------------------------------------------
1. [HIGH] Use Optimal Batch Size
   Impact: 68.52 pairs/sec
2. [MEDIUM] Memory-Efficient Batch Size
   Impact: 14.35 pairs/sec with 2.5 MB memory
3. [MEDIUM] Truncate Long Inputs
   Impact: 10-30% improvement for long texts

================================================================================
```

**JSON Output** (`results/nli_profile_YYYY-MM-DD.json`):
```json
{
  "timestamp": "2025-10-31T21:02:49...",
  "system": {
    "python_version": "3.13.7",
    "pytorch_version": "2.9.0+cpu",
    "cuda_available": false,
    "device": "cpu",
    "model": "cross-encoder/nli-deberta-v3-base"
  },
  "batch_profiles": [
    {
      "batch_size": 1,
      "throughput_pairs_per_sec": 14.35,
      "latency_ms_per_pair": 69.69,
      "memory_delta_mb": 2.5,
      "label_distribution": {...},
      "avg_confidence": 0.99,
      "profile_stats": "..."
    },
    ...
  ],
  "bottlenecks": [...],
  "recommendations": [...]
}
```

---

### Script 2: `nli_batch_optimization.py` - Batch Size Optimization

**Purpose**: Detailed batch size analysis with accuracy validation and optimal configuration recommendations.

#### Usage

```bash
python scripts/profiling/nli_batch_optimization.py [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--batch-sizes` | Comma-separated batch sizes to test | `1,4,8,16,32` |
| `--num-pairs` | Number of test pairs | `100` |
| `--validate-accuracy` | Enable accuracy validation | `True` |
| `--output` | Output path for results JSON | `scripts/profiling/results/nli_batch_analysis_YYYY-MM-DD.json` |

#### Example Commands

```bash
# Full optimization with accuracy validation
python scripts/profiling/nli_batch_optimization.py --validate-accuracy

# Test larger batch sizes (for GPU)
python scripts/profiling/nli_batch_optimization.py --batch-sizes 16,32,64,128

# More pairs for accuracy confidence
python scripts/profiling/nli_batch_optimization.py --num-pairs 500 --validate-accuracy
```

#### Output

**Console Output**:
```
================================================================================
NLI BATCH OPTIMIZATION SUMMARY
================================================================================

Batch Size Analysis:
--------------------------------------------------------------------------------
 Batch |    Pairs/Sec |   Latency (ms) |   Memory (MB) |   Accuracy
--------------------------------------------------------------------------------
     1 |        15.09 |          66.27 |           2.6 |     0.6900
     4 |        36.89 |          27.11 |          15.9 |     0.6900
     8 |        51.71 |          19.34 |          35.1 |     0.6900
    16 |        64.74 |          15.45 |          51.5 |     0.6900
    32 |        77.48 |          12.91 |          90.4 |     0.6900

Optimal Configurations:
--------------------------------------------------------------------------------
Maximum Throughput: batch_size=32
  - 77.48 pairs/sec

Balanced (Recommended): batch_size=16
  - 64.74 pairs/sec
  - 51.5 MB memory

Memory Efficient: batch_size=1
  - 15.09 pairs/sec
  - 2.6 MB memory

================================================================================
```

---

## Interpreting Results

### Throughput (pairs/sec)

**What it means**: Number of premise-hypothesis pairs processed per second.

**How to interpret**:
- **>60 pairs/sec**: Excellent performance
- **30-60 pairs/sec**: Good performance
- **10-30 pairs/sec**: Acceptable for low-volume use
- **<10 pairs/sec**: Poor performance, optimization needed

**Target**: >2 pairs/sec (current achievement: 77.48 pairs/sec = **38.7x target**)

### Latency (ms/pair)

**What it means**: Average time to process one pair.

**How to interpret**:
- **<20 ms**: Excellent latency
- **20-50 ms**: Good latency
- **50-100 ms**: Acceptable latency
- **>100 ms**: High latency, may impact user experience

**Relationship to throughput**: `Latency (ms) ≈ 1000 / Throughput (pairs/sec)`

### Memory Delta (MB)

**What it means**: Memory increase during batch processing.

**How to interpret**:
- **<50 MB**: Low memory usage
- **50-100 MB**: Moderate memory usage
- **100-200 MB**: High memory usage
- **>200 MB**: Very high memory usage, may cause issues

**Note**: Total memory includes model weights (~200 MB) + delta

### Accuracy

**What it means**: Percentage of correct predictions on test dataset.

**How to interpret**:
- **>0.90**: Excellent accuracy
- **0.70-0.90**: Good accuracy
- **0.50-0.70**: Moderate accuracy (current: 0.69)
- **<0.50**: Poor accuracy, model issues

**Important**: Test dataset is intentionally challenging. Production accuracy may differ.

### Confidence

**What it means**: Average model confidence in predictions (0.0-1.0).

**How to interpret**:
- **>0.95**: Very confident (current: >0.99)
- **0.80-0.95**: Confident
- **0.60-0.80**: Moderate confidence
- **<0.60**: Low confidence, unreliable predictions

**Note**: High confidence doesn't guarantee correctness.

---

## Common Scenarios

### Scenario 1: Choosing Optimal Batch Size

**Goal**: Find the best batch size for your use case.

**Steps**:

1. Run profiling with multiple batch sizes:
```bash
python scripts/profiling/profile_nli.py --batch-sizes 1,4,8,16,32,64
```

1. Review results:
   - Maximum throughput: Highest pairs/sec (usually largest batch size)
   - Balanced: Good throughput + acceptable memory
   - Memory-efficient: Lowest memory usage

2. Choose based on constraints:
   - **No memory constraints**: Use maximum throughput batch size
   - **Memory limited**: Use smallest batch size that meets throughput target
   - **Balanced**: Use recommended batch size (typically batch_size=16)

**Example**:
```
Your results:
- batch_size=32: 77 pairs/sec, 90 MB
- batch_size=16: 65 pairs/sec, 51 MB  ← RECOMMENDED
- batch_size=8:  51 pairs/sec, 35 MB

Target: >50 pairs/sec
Memory limit: <75 MB

Decision: Use batch_size=16 (meets throughput, within memory limit)
```

### Scenario 2: Troubleshooting Low Throughput

**Symptom**: Throughput significantly below expected.

**Diagnostic Steps**:

1. Check actual batch size being used:
```python
# Add logging in your code
logger.info("batch_size_used", size=len(pairs))
```

1. Profile current configuration:
```bash
python scripts/profiling/profile_nli.py --batch-sizes 1,8,16
```

1. Compare results:
   - If batch_size=1 performance: You're processing one pair at a time
   - If between 1 and optimal: Batch size is too small
   - If same across all sizes: Model or system issue

**Solutions**:
- Increase batch size to 16
- Implement batch accumulation (see recommendations doc)
- Check for serial processing in code

### Scenario 3: Memory Pressure Issues

**Symptom**: Out-of-memory errors or swapping.

**Diagnostic Steps**:

1. Profile memory at different batch sizes:
```bash
python scripts/profiling/profile_nli.py --batch-sizes 4,8,16,32
```

1. Identify memory budget:
   - Total available memory
   - Memory used by other services
   - Memory budget for NLI service

2. Choose appropriate batch size:
   - batch_size=4: ~16 MB
   - batch_size=8: ~35 MB
   - batch_size=16: ~51 MB
   - batch_size=32: ~90 MB

**Solutions**:
- Reduce batch size to fit memory budget
- Enable model quantization (50% memory reduction)
- Process smaller batches more frequently

### Scenario 4: Accuracy Validation

**Goal**: Verify model accuracy hasn't degraded.

**Steps**:

1. Run optimization with accuracy validation:
```bash
python scripts/profiling/nli_batch_optimization.py \
    --validate-accuracy \
    --num-pairs 200
```

1. Review accuracy metrics:
   - Check accuracy across all batch sizes
   - Verify no degradation with larger batches
   - Review confusion matrix for error patterns

2. Compare with baseline:
   - Previous accuracy measurements
   - Expected model accuracy (from model card)
   - Acceptable accuracy threshold

**Acceptable Ranges**:
- **No degradation**: Same accuracy across batch sizes (current: 0.69 constant)
- **Minor variation**: ±1% acceptable (e.g., 0.68-0.70)
- **Significant drop**: >2% degradation requires investigation

### Scenario 5: GPU vs CPU Comparison

**Goal**: Determine if GPU acceleration is beneficial.

**Steps**:

1. Profile on CPU:
```bash
# On CPU machine
python scripts/profiling/profile_nli.py --batch-sizes 16,32,64 --output cpu_results.json
```

1. Profile on GPU:
```bash
# On GPU machine
python scripts/profiling/profile_nli.py --batch-sizes 16,32,64,128 --output gpu_results.json
```

1. Compare results:
   - Throughput improvement
   - Memory usage
   - Cost/benefit analysis

**Expected Results**:
- CPU: 64-77 pairs/sec @ batch_size=16-32
- GPU (CUDA): 150-300 pairs/sec @ batch_size=64
- GPU (MPS): 100-200 pairs/sec @ batch_size=32

**Decision Criteria**:
- **Use GPU if**: Throughput requirement >100 pairs/sec, GPU available
- **Stay on CPU if**: Current performance sufficient, no GPU available

---

## Programmatic Usage

### Using Profiler in Code

```python
from scripts.profiling.profile_nli import NLIProfiler

# Create profiler
profiler = NLIProfiler()

# Load test data
profiler.load_test_data(num_pairs=100)

# Run profiling
profiler.run_all_profiles(
    batch_sizes=[8, 16, 32],
    num_pairs=100
)

# Get results
results = profiler.results

# Access specific metrics
for profile in results["batch_profiles"]:
    print(f"Batch {profile['batch_size']}: {profile['throughput_pairs_per_sec']:.2f} pairs/sec")

# Save results
profiler.save_results("my_profile.json")
```

### Using Batch Optimizer in Code

```python
from scripts.profiling.nli_batch_optimization import BatchOptimizer

# Create optimizer
optimizer = BatchOptimizer()

# Run optimization
optimizer.run_optimization(
    batch_sizes=[8, 16, 32],
    num_pairs=100,
    validate_accuracy=True
)

# Get optimal configs
optimal = optimizer.results["optimal_configs"]
print(f"Recommended batch size: {optimal['balanced']['batch_size']}")
print(f"Expected throughput: {optimal['balanced']['throughput_pairs_per_sec']:.2f}")

# Save results
optimizer.save_results("optimization.json")
```

---

## Troubleshooting

### Issue: Script fails to run

**Symptoms**: Import errors, module not found

**Solutions**:
```bash
# Install ML dependencies
pip install -e ".[ml]"

# Verify installation
python -c "from truthgraph.services.ml.nli_service import get_nli_service; print('OK')"
```

### Issue: Model download fails

**Symptoms**: Network errors, timeout during model load

**Solutions**:
```bash
# Pre-download model
python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('cross-encoder/nli-deberta-v3-base'); \
    AutoModelForSequenceClassification.from_pretrained('cross-encoder/nli-deberta-v3-base')"

# Or set cache directory
export TRANSFORMERS_CACHE=/path/to/cache
```

### Issue: Results vary between runs

**Symptoms**: Different throughput on repeated runs

**Causes**:
- Model warmup state
- System load
- Memory pressure
- CPU frequency scaling

**Solutions**:
- Run multiple iterations and average results
- Ensure system is idle during profiling
- Use `--num-pairs 200` for better statistics
- Check for background processes

### Issue: Out of memory

**Symptoms**: OOM errors, system freezing

**Solutions**:
- Reduce batch size: `--batch-sizes 1,4,8`
- Reduce test pairs: `--num-pairs 50`
- Close other applications
- Monitor memory: `watch -n 1 free -h`

---

## Best Practices

### 1. Profile on Production-Like Hardware

- Same CPU/GPU as production
- Similar memory availability
- Comparable system load

### 2. Use Sufficient Test Data

- Minimum 100 pairs for reliability
- 200+ pairs for high confidence
- Representative of production data

### 3. Run Multiple Iterations

```bash
# Run 3 times and average
for i in {1..3}; do
    python scripts/profiling/profile_nli.py --output run_$i.json
done
```

### 4. Document Configuration

Record system configuration with results:
- CPU model and cores
- Memory (total/available)
- GPU model (if applicable)
- Python/PyTorch versions
- System load during profiling

### 5. Version Control Results

```bash
# Save results to git
git add scripts/profiling/results/
git commit -m "NLI profiling results for v2.0"
git tag profiling-v2.0
```

---

## Advanced Usage

### Custom Test Data

```python
from scripts.profiling.profile_nli import NLIProfiler

profiler = NLIProfiler()

# Load your own test pairs
profiler.test_pairs = [
    ("Your premise 1", "Your hypothesis 1"),
    ("Your premise 2", "Your hypothesis 2"),
    # ...
]

# Run profiling
profiler.run_all_profiles([8, 16, 32], num_pairs=None)
```

### Custom Metrics

```python
# Add custom metric collection
def profile_with_custom_metrics(batch_size: int):
    import time
    import psutil

    # Measure CPU usage
    cpu_before = psutil.cpu_percent(interval=0.1)

    # Run inference
    start = time.perf_counter()
    results = service.verify_batch(pairs, batch_size=batch_size)
    elapsed = time.perf_counter() - start

    cpu_after = psutil.cpu_percent(interval=0.1)

    return {
        "throughput": len(pairs) / elapsed,
        "cpu_usage_percent": (cpu_before + cpu_after) / 2,
        # Add more custom metrics
    }
```

---

## Related Documentation

- **Analysis**: `nli_optimization_analysis.md` - Detailed performance analysis
- **Recommendations**: `nli_optimization_recommendations.md` - Implementation guide
- **API**: `truthgraph/services/ml/nli_service.py` - Service implementation

---

## Appendix: Quick Reference

### Command Cheatsheet

```bash
# Basic profiling
python scripts/profiling/profile_nli.py

# With accuracy validation
python scripts/profiling/nli_batch_optimization.py --validate-accuracy

# Custom batch sizes
python scripts/profiling/profile_nli.py --batch-sizes 16,32,64

# More test data
python scripts/profiling/profile_nli.py --num-pairs 500

# GPU profiling (on GPU machine)
python scripts/profiling/profile_nli.py --batch-sizes 32,64,128
```

### Interpretation Cheatsheet

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Throughput | >60 pairs/sec | 30-60 | <30 |
| Latency | <20 ms | 20-50 ms | >50 ms |
| Memory | <50 MB | 50-100 MB | >100 MB |
| Accuracy | >0.85 | 0.65-0.85 | <0.65 |
| Confidence | >0.90 | 0.70-0.90 | <0.70 |

---

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Author**: python-pro agent
