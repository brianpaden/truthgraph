# Embedding Service Profiling Guide
## How to Profile and Optimize the Embedding Service

**Date**: October 31, 2025
**Feature**: 2.1 - Embedding Service Profiling
**Audience**: Developers, DevOps Engineers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Profiling Scripts](#profiling-scripts)
4. [Interpreting Results](#interpreting-results)
5. [Common Scenarios](#common-scenarios)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Introduction

This guide explains how to profile the EmbeddingService to identify performance bottlenecks and optimization opportunities. Three profiling scripts are provided:

1. **`profile_batch_sizes.py`** - Profile different batch sizes for optimal throughput
2. **`profile_memory.py`** - Analyze memory usage and detect leaks
3. **`profile_text_lengths.py`** - Measure impact of text length on performance

All scripts are located in `scripts/profiling/` and generate JSON results + console summaries.

---

## Quick Start

### Prerequisites

```bash
# Ensure all dependencies are installed
pip install torch sentence-transformers psutil

# Verify environment
python -c "import torch; print(f'PyTorch {torch.__version__}')"
python -c "import sentence_transformers; print('sentence-transformers OK')"
```

### Run All Profiling Scripts

```bash
# Navigate to project root
cd c:\repos\truthgraph

# 1. Profile batch sizes (5-10 minutes)
python scripts/profiling/profile_batch_sizes.py --test-size 1000

# 2. Profile memory usage (3-5 minutes)
python scripts/profiling/profile_memory.py --test-size 1000 --iterations 3

# 3. Profile text length impact (2-3 minutes)
python scripts/profiling/profile_text_lengths.py --batch-size 32 --num-texts 500

# View results
ls scripts/profiling/results/
```

### Quick Interpretation

After running the scripts, check these key metrics:

```bash
# Best batch size for throughput
grep "best_throughput" scripts/profiling/results/batch_size_profile_*.json

# Memory leak status
grep "leak_detected" scripts/profiling/results/memory_analysis_*.json

# Text length impact
grep "performance_drop_percent" scripts/profiling/results/text_length_profile_*.json
```

---

## Profiling Scripts

### 1. Batch Size Profiling

**Script**: `scripts/profiling/profile_batch_sizes.py`

**Purpose**: Identify optimal batch size for maximum throughput while monitoring memory usage.

**Usage**:
```bash
python scripts/profiling/profile_batch_sizes.py [OPTIONS]

Options:
  --test-size INT        Number of texts to test (default: 1000)
  --batch-sizes INT...   Batch sizes to test (default: 8 16 32 64 128 256)
  --output PATH          Output directory (default: scripts/profiling/results)

Examples:
  # Default profiling
  python scripts/profiling/profile_batch_sizes.py

  # Custom test size and batch sizes
  python scripts/profiling/profile_batch_sizes.py --test-size 2000 --batch-sizes 32 64 128

  # Quick test with fewer batch sizes
  python scripts/profiling/profile_batch_sizes.py --test-size 500 --batch-sizes 32 64 128
```

**Output**:
- `batch_size_profile_YYYY-MM-DD.json` - Complete profiling results
- Console summary with performance table

**Example Output**:
```
============================================================
PROFILING SUMMARY
============================================================

Device: cpu
Test size: 1000 texts

Batch Size Performance:
   Batch      Throughput       Latency    Memory D
    Size     (texts/sec)     (ms/text)        (MB)
------------------------------------------------------------
       8           527.40        1.896        26.6
      16           782.22        1.278        26.6
      32         1,018.18        0.982        18.5
      64         1,340.54        0.746        29.9
     128         1,478.27        0.676        48.8
     256         1,493.41        0.670        73.3

Top Bottlenecks:

1. OPTIMAL_BATCH_SIZE
   Finding: Best throughput at batch_size=256
   Metric: 1493.41 texts/sec
   Recommendation: Use batch_size=256 for optimal performance
```

**What to Look For**:
- **Best throughput batch size** - Use this for production
- **Memory vs throughput trade-off** - Balance based on constraints
- **Diminishing returns point** - Where throughput gains flatten
- **Baseline comparison** - Ensure no regression

---

### 2. Memory Profiling

**Script**: `scripts/profiling/profile_memory.py`

**Purpose**: Analyze memory usage patterns, detect leaks, and identify memory-efficient configurations.

**Usage**:
```bash
python scripts/profiling/profile_memory.py [OPTIONS]

Options:
  --test-size INT        Number of texts to test (default: 1000)
  --iterations INT       Iterations per batch size (default: 3)
  --batch-sizes INT...   Batch sizes to test (default: 8 16 32 64 128 256)
  --output PATH          Output directory (default: scripts/profiling/results)

Examples:
  # Default profiling
  python scripts/profiling/profile_memory.py

  # More iterations for stable measurements
  python scripts/profiling/profile_memory.py --iterations 5

  # Focus on specific batch sizes
  python scripts/profiling/profile_memory.py --batch-sizes 32 64 128
```

**Output**:
- `memory_analysis_YYYY-MM-DD.json` - Complete memory profiling data
- Console summary with memory usage table and leak detection

**Example Output**:
```
============================================================
MEMORY PROFILING SUMMARY
============================================================

Baseline Memory: 430.28 MB

Batch Size Memory Usage:
   Batch     Baseline         Peak       Avg D      Max D
    Size         (MB)         (MB)        (MB)       (MB)
------------------------------------------------------------
       8        430.3        467.1        12.3       26.9
      16        456.5        487.1         9.4       22.0
      32        476.1        500.1         6.9       14.7
      64        491.4        527.2        10.1       15.0
     128        517.2        592.9        22.6       34.9
     256        583.4        657.7        24.0       33.4

Memory Leak Check:
  Iterations: 10
  Initial: 655.3 MB
  Final: 655.3 MB
  Growth: +0.0 MB
  Leak detected: False
```

**What to Look For**:
- **Baseline memory** - Starting point before processing
- **Memory delta by batch size** - How much memory each batch needs
- **Leak detection** - Should always be False
- **Memory efficiency** - Best balance of performance and memory

---

### 3. Text Length Impact Profiling

**Script**: `scripts/profiling/profile_text_lengths.py`

**Purpose**: Measure how text length affects performance to determine optimal text preprocessing strategy.

**Usage**:
```bash
python scripts/profiling/profile_text_lengths.py [OPTIONS]

Options:
  --batch-size INT       Batch size to use (default: 32)
  --num-texts INT        Texts per length test (default: 500)
  --iterations INT       Iterations per test (default: 3)
  --text-lengths INT...  Text lengths in chars (default: 10 50 100 256 512 1024)
  --output PATH          Output directory (default: scripts/profiling/results)

Examples:
  # Default profiling
  python scripts/profiling/profile_text_lengths.py

  # Test with larger batch size
  python scripts/profiling/profile_text_lengths.py --batch-size 64

  # Test specific text lengths
  python scripts/profiling/profile_text_lengths.py --text-lengths 50 100 200 400 800

  # Quick test with fewer iterations
  python scripts/profiling/profile_text_lengths.py --iterations 2 --num-texts 300
```

**Output**:
- `text_length_profile_YYYY-MM-DD.json` - Complete text length analysis
- Console summary with performance by length

**Example Output**:
```
============================================================
TEXT LENGTH PROFILING SUMMARY
============================================================

Device: cpu
Batch size: 32

Performance by Text Length:
    Length      Throughput       Latency    Memory D
   (chars)     (texts/sec)     (ms/text)        (MB)
------------------------------------------------------------
        10         1,219.09        1.605        27.2
        50         1,063.58        0.940         7.9
       100           812.82        1.230         2.2
       256           482.21        2.074        13.9
       512           273.15        3.661        19.2
      1024           132.50        7.548        33.1

Analysis:
  Best: 10 chars @ 1219.09 texts/sec
  Worst: 1024 chars @ 132.50 texts/sec
  Performance drop: 89.1%
  Relationship: strong_negative

Top Recommendations:

1. Text Truncation
   Truncate texts to 10 characters for optimal performance
   Expected: 89.1% throughput improvement for long texts
   Effort: low, Priority: high
```

**What to Look For**:
- **Performance drop percentage** - How much long texts hurt performance
- **Correlation coefficient** - Strength of length-performance relationship
- **Optimal text length range** - Where to truncate for best balance
- **Recommendations** - Suggested text preprocessing strategies

---

## Interpreting Results

### Understanding JSON Output

All profiling scripts generate JSON files in `scripts/profiling/results/`. Here's what each section means:

#### Batch Size Profile JSON

```json
{
  "metadata": {
    "timestamp": "2025-10-31T...",
    "device": "cpu",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "num_test_texts": 1000,
    "batch_sizes_tested": [8, 16, 32, 64, 128, 256]
  },
  "batch_results": [
    {
      "batch_size": 64,
      "throughput_texts_per_sec": 1340.54,  // Higher is better
      "latency_ms_per_text": 0.746,         // Lower is better
      "memory_delta_mb": 29.9               // Memory overhead
    }
  ],
  "bottlenecks": [
    {
      "type": "optimal_batch_size",
      "finding": "Best throughput at batch_size=256",
      "recommendation": "Use batch_size=256 for optimal performance"
    }
  ],
  "recommendations": [
    {
      "optimization": "Batch Size Configuration",
      "expected_improvement": "13% throughput improvement",
      "effort": "low",
      "priority": "high"
    }
  ]
}
```

**Key Metrics**:
- `throughput_texts_per_sec` - Primary performance metric (higher = better)
- `latency_ms_per_text` - Per-text processing time (lower = better)
- `memory_delta_mb` - Additional memory needed (minimize if constrained)

#### Memory Analysis JSON

```json
{
  "batch_memory_analysis": [
    {
      "batch_size": 64,
      "baseline_memory_mb": 491.4,  // Memory before processing
      "peak_memory_mb": 527.2,      // Maximum memory during processing
      "avg_delta_mb": 10.1          // Average additional memory needed
    }
  ],
  "memory_leak_check": {
    "leak_detected": false,         // Should always be false
    "total_growth_mb": 0.0,         // Memory growth over time
    "growth_rate_mb_per_iteration": 0.0
  }
}
```

**Warning Signs**:
- `leak_detected: true` - Investigate immediately
- `total_growth_mb > 50` - Potential memory leak
- `peak_memory_mb > 1000` - May exceed resource limits

#### Text Length Profile JSON

```json
{
  "length_results": [
    {
      "text_length_chars": 256,
      "avg_throughput_texts_per_sec": 482.21,
      "avg_latency_ms_per_text": 2.074
    }
  ],
  "analysis": {
    "performance_drop_percent": 89.1,        // Total performance loss
    "length_throughput_correlation": -0.88,  // Negative = slower with length
    "relationship": "strong_negative"        // Interpretation
  }
}
```

**Correlation Interpretation**:
- Strong negative (< -0.7): Text length significantly impacts performance
- Moderate negative (-0.3 to -0.7): Noticeable but manageable impact
- Weak (> -0.3): Text length has minimal effect

---

## Common Scenarios

### Scenario 1: New Deployment

**Goal**: Establish baseline performance for new environment

**Steps**:
```bash
# 1. Run all profiling scripts
python scripts/profiling/profile_batch_sizes.py --test-size 1000
python scripts/profiling/profile_memory.py --test-size 1000
python scripts/profiling/profile_text_lengths.py

# 2. Review all outputs
cd scripts/profiling/results
ls -la

# 3. Document findings
# - Best batch size: [from batch_size_profile]
# - Memory characteristics: [from memory_analysis]
# - Text length strategy: [from text_length_profile]

# 4. Apply recommendations
# - Update DEFAULT_BATCH_SIZE in embedding_service.py
# - Implement text truncation if needed
# - Set up monitoring alerts
```

### Scenario 2: Performance Regression Investigation

**Goal**: Identify why performance has degraded

**Steps**:
```bash
# 1. Run batch size profiling to compare with baseline
python scripts/profiling/profile_batch_sizes.py --test-size 1000

# 2. Compare with baseline
diff scripts/profiling/results/batch_size_profile_YYYY-MM-DD.json \
     scripts/benchmarks/results/baseline_embeddings_2025-10-27.json

# 3. Check for memory issues
python scripts/profiling/profile_memory.py --test-size 1000 --iterations 5

# 4. Look for:
# - Throughput drop >5% at any batch size
# - Memory leak detected = true
# - Increased memory usage
# - Baseline comparison showing regression
```

### Scenario 3: Optimizing for Memory-Constrained Environment

**Goal**: Find best performance within memory budget

**Steps**:
```bash
# 1. Profile with focus on smaller batch sizes
python scripts/profiling/profile_batch_sizes.py --batch-sizes 8 16 32 64

# 2. Run memory profiling
python scripts/profiling/profile_memory.py --batch-sizes 8 16 32 64

# 3. Find batch size where:
# - peak_memory_mb < your_memory_budget
# - throughput_texts_per_sec is maximized
#
# Example: If budget is 500 MB, use batch_size=32
#   - Peak memory: 500 MB
#   - Throughput: 1,018 texts/sec
```

### Scenario 4: Preparing for Production with Long Texts

**Goal**: Optimize for workload with long documents

**Steps**:
```bash
# 1. Profile text lengths
python scripts/profiling/profile_text_lengths.py \
  --text-lengths 100 200 400 800 1600 \
  --batch-size 32

# 2. Analyze performance drop
# If drop >50%, implement text truncation

# 3. Test truncation impact
# Modify embedding_service.py to truncate to 256 chars
# Re-run profiling to verify improvement

# 4. Document truncation policy
# - Max length: 256 chars
# - Truncation method: sentence boundary
# - Expected throughput improvement: 40-60%
```

### Scenario 5: Testing GPU Performance

**Goal**: Compare GPU vs CPU performance

**Steps**:
```bash
# 1. Verify GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# 2. Profile on GPU with larger batch sizes
python scripts/profiling/profile_batch_sizes.py \
  --test-size 1000 \
  --batch-sizes 64 128 256 512

# 3. Compare with CPU baseline
# Expected: 2-5x improvement with GPU

# 4. Document GPU configuration
# - Optimal batch size for GPU: typically 256-512
# - GPU memory usage
# - Performance comparison
```

---

## Troubleshooting

### Issue 1: Scripts Run Slowly

**Symptoms**: Profiling takes >10 minutes per script

**Causes & Solutions**:
```bash
# Cause: Test size too large
# Solution: Reduce test size
python scripts/profiling/profile_batch_sizes.py --test-size 500

# Cause: Too many batch sizes tested
# Solution: Test fewer batch sizes
python scripts/profiling/profile_batch_sizes.py --batch-sizes 32 64 128

# Cause: Too many iterations
# Solution: Reduce iterations
python scripts/profiling/profile_memory.py --iterations 2
```

### Issue 2: Out of Memory Errors

**Symptoms**: Script crashes with "Out of memory"

**Solutions**:
```bash
# Solution 1: Test smaller batch sizes
python scripts/profiling/profile_batch_sizes.py --batch-sizes 8 16 32

# Solution 2: Reduce test size
python scripts/profiling/profile_batch_sizes.py --test-size 500

# Solution 3: Close other applications
# Free up system memory before profiling

# Solution 4: Enable memory cleanup
# Add to script: gc.collect() between tests
```

### Issue 3: Inconsistent Results

**Symptoms**: Different results on repeated runs

**Causes & Solutions**:
```bash
# Cause: System load varying
# Solution: Run when system is idle

# Cause: Not enough warmup
# Solution: Increase warmup iterations in script

# Cause: Too few test texts
# Solution: Increase test size
python scripts/profiling/profile_batch_sizes.py --test-size 2000

# Cause: Thermal throttling
# Solution: Monitor CPU temperature, ensure cooling
```

### Issue 4: Import Errors

**Symptoms**: "ModuleNotFoundError" when running scripts

**Solutions**:
```bash
# Install missing dependencies
pip install torch sentence-transformers psutil

# Verify installation
python -c "import torch, sentence_transformers, psutil; print('OK')"

# Check Python path
python -c "import sys; print(sys.path)"

# Run from project root
cd c:\repos\truthgraph
python scripts/profiling/profile_batch_sizes.py
```

### Issue 5: Unicode Encoding Errors

**Symptoms**: "UnicodeEncodeError" in console output

**Solution**:
```bash
# Set UTF-8 encoding for Windows
chcp 65001

# Or redirect output to file
python scripts/profiling/profile_batch_sizes.py > output.txt 2>&1

# Results are always saved to JSON correctly
# Just view JSON file instead of console output
```

---

## Best Practices

### 1. Establish Baseline Before Changes

Always profile before making any changes to establish a baseline:

```bash
# Before optimizing
python scripts/profiling/profile_batch_sizes.py --test-size 1000
mv scripts/profiling/results/batch_size_profile_*.json baseline_before.json

# After optimizing
python scripts/profiling/profile_batch_sizes.py --test-size 1000
mv scripts/profiling/results/batch_size_profile_*.json baseline_after.json

# Compare
diff baseline_before.json baseline_after.json
```

### 2. Profile on Production-Like Hardware

Test on hardware similar to production:
- Same CPU/GPU type
- Similar memory constraints
- Same operating system
- Similar system load

### 3. Run Multiple Iterations

For stable measurements, run multiple times:

```bash
# Run 3 times and average results
for i in {1..3}; do
  python scripts/profiling/profile_batch_sizes.py --test-size 1000
  sleep 60  # Cool down between runs
done

# Compare results for consistency
```

### 4. Monitor System During Profiling

Use system monitoring tools:

```bash
# Open in separate terminal
# Monitor CPU
watch -n 1 "ps aux | grep python | grep -v grep"

# Monitor memory
watch -n 1 "free -h"

# Monitor GPU (if applicable)
watch -n 1 "nvidia-smi"
```

### 5. Document All Findings

Maintain a profiling log:

```markdown
## Profiling Log

### 2025-10-31: Initial Baseline
- Batch size: 32
- Throughput: 1,018 texts/sec
- Memory: 485 MB
- Device: CPU

### 2025-11-01: After Optimization
- Batch size: 64
- Throughput: 1,341 texts/sec (+31.7%)
- Memory: 510 MB (+5.2%)
- Device: CPU
```

### 6. Version Control Results

Save profiling results in version control:

```bash
# Create profiling results directory
mkdir -p profiling_results/baseline

# Copy baseline results
cp scripts/profiling/results/*.json profiling_results/baseline/

# Commit to git
git add profiling_results/
git commit -m "Add profiling baseline results"
```

### 7. Automate Profiling in CI/CD

Add profiling to CI/CD pipeline:

```yaml
# .github/workflows/profiling.yml
name: Performance Profiling

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run profiling
        run: |
          python scripts/profiling/profile_batch_sizes.py --test-size 500
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: profiling-results
          path: scripts/profiling/results/
```

---

## Advanced Usage

### Custom Test Data

Use your own test data:

```python
# scripts/profiling/profile_custom_data.py

import json
from pathlib import Path
from profile_batch_sizes import BatchSizeProfiler

# Load custom data
with open('my_custom_data.json') as f:
    custom_texts = [item['text'] for item in json.load(f)]

# Run profiling
profiler = BatchSizeProfiler(custom_texts, batch_sizes=[32, 64, 128])
results = profiler.run_profiling()

# Save results
output_path = Path('scripts/profiling/results/custom_profile.json')
profiler.save_results(output_path)
profiler.print_summary()
```

### Programmatic Analysis

Analyze results programmatically:

```python
import json

# Load results
with open('scripts/profiling/results/batch_size_profile_2025-10-31.json') as f:
    results = json.load(f)

# Find optimal batch size
batch_results = results['batch_results']
optimal = max(batch_results, key=lambda x: x['throughput_texts_per_sec'])

print(f"Optimal batch size: {optimal['batch_size']}")
print(f"Throughput: {optimal['throughput_texts_per_sec']:.2f} texts/sec")
print(f"Memory: {optimal['memory_delta_mb']:.1f} MB")

# Check for regression
baseline_throughput = 1184.92  # Feature 1.7 baseline
current_throughput = next(r for r in batch_results if r['batch_size'] == 64)['throughput_texts_per_sec']
variance = ((current_throughput - baseline_throughput) / baseline_throughput) * 100

if variance < -5:
    print(f"WARNING: Performance regression: {variance:.1f}%")
else:
    print(f"Performance: {variance:+.1f}% vs baseline")
```

---

## Reference

### Profiling Script Locations

```
scripts/profiling/
├── profile_batch_sizes.py      # Batch size profiling
├── profile_memory.py            # Memory profiling
├── profile_text_lengths.py      # Text length profiling
└── results/                     # Output directory
    ├── batch_size_profile_YYYY-MM-DD.json
    ├── memory_analysis_YYYY-MM-DD.json
    └── text_length_profile_YYYY-MM-DD.json
```

### Documentation Locations

```
docs/profiling/
├── embedding_service_analysis.md        # Detailed analysis report
├── optimization_recommendations.md      # Optimization guide
└── profiling_guide.md                   # This guide
```

### Related Scripts

```
scripts/benchmarks/
├── benchmark_embeddings.py      # Feature 1.7 baseline benchmark
├── compare_results.py           # Compare profiling results
└── results/
    └── baseline_embeddings_2025-10-27.json  # Baseline data
```

---

## Support

For questions or issues with profiling:

1. Check this guide's troubleshooting section
2. Review the comprehensive analysis: `docs/profiling/embedding_service_analysis.md`
3. Review optimization recommendations: `docs/profiling/optimization_recommendations.md`
4. Check existing profiling results in `scripts/profiling/results/`
5. Review baseline benchmarks in `scripts/benchmarks/results/`

---

**Document Status**: COMPLETE
**Last Updated**: October 31, 2025
**Feature**: 2.1 - Embedding Service Profiling
