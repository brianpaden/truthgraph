# TruthGraph Benchmarking Framework

Comprehensive performance benchmarking and regression detection for TruthGraph ML Core components.

## Overview

This benchmarking framework provides:

- **Component benchmarks** for embeddings, NLI, vector search, and end-to-end pipeline
- **Performance baselines** tracked over time
- **Regression detection** to identify performance degradation
- **Reproducible results** with standardized test data

## Performance Targets

### Embeddings
- **Throughput**: >500 texts/second on CPU, >2000 on GPU
- **Single text latency**: <100ms
- **Memory usage**: <2GB

### NLI (Natural Language Inference)
- **Throughput**: >2 pairs/second on CPU
- **Single pair latency**: <500ms
- **Memory usage**: <2GB

### Vector Search
- **Query latency**: <3 seconds for 10K corpus
- **Query throughput**: >10 queries/second
- **Scalability**: Linear with corpus size

### End-to-End Pipeline
- **Latency**: <60 seconds per claim
- **Throughput**: >1 claim per minute
- **Success rate**: >95%

## Quick Start

### Run All Benchmarks

```bash
# Full benchmark suite
python scripts/benchmarks/run_all_benchmarks.py

# Quick run (fewer iterations)
python scripts/benchmarks/run_all_benchmarks.py --quick

# Generate baseline
python scripts/benchmarks/run_all_benchmarks.py --baseline
```

### Run Individual Benchmarks

```bash
# Embeddings
python scripts/benchmarks/benchmark_embeddings.py

# NLI
python scripts/benchmarks/benchmark_nli.py

# Vector Search
python scripts/benchmarks/benchmark_vector_search.py

# End-to-end Pipeline
python scripts/benchmarks/benchmark_pipeline.py
```

## Individual Benchmark Scripts

### benchmark_embeddings.py

Measures embedding service performance across multiple dimensions.

**Usage:**
```bash
python benchmark_embeddings.py [options]

Options:
  --num-texts N         Number of texts for batch benchmarks (default: 1000)
  --batch-sizes SIZES   Comma-separated batch sizes (e.g., '16,32,64')
  --iterations N        Iterations for single text benchmark (default: 100)
  --skip-single         Skip single text benchmark
  --skip-batch          Skip batch benchmark
  --skip-lengths        Skip text length benchmark
  --skip-memory         Skip memory benchmark
  --output FILE         Output JSON file path
```

**What it measures:**
- Single text embedding latency (P50, P95, P99)
- Batch processing throughput with various batch sizes
- Impact of text length (short, medium, long)
- Memory usage and model footprint

**Example:**
```bash
# Quick benchmark
python benchmark_embeddings.py --num-texts 500 --iterations 50

# Test specific batch sizes
python benchmark_embeddings.py --batch-sizes 16,32,64 --num-texts 2000

# Save to specific file
python benchmark_embeddings.py --output results/my_embeddings_test.json
```

### benchmark_nli.py

Measures NLI service performance for claim verification.

**Usage:**
```bash
python benchmark_nli.py [options]

Options:
  --num-pairs N         Number of pairs for batch benchmarks (default: 100)
  --batch-sizes SIZES   Comma-separated batch sizes (e.g., '2,4,8,16')
  --iterations N        Iterations for single pair benchmark (default: 50)
  --skip-single         Skip single pair benchmark
  --skip-batch          Skip batch benchmark
  --skip-lengths        Skip text length benchmark
  --skip-memory         Skip memory benchmark
  --output FILE         Output JSON file path
```

**What it measures:**
- Single pair inference latency
- Batch inference throughput with various batch sizes
- Impact of text length on inference time
- Memory usage during inference
- Label distribution (entailment, contradiction, neutral)

**Example:**
```bash
# Quick benchmark
python benchmark_nli.py --num-pairs 50 --iterations 30

# Test batch performance
python benchmark_nli.py --batch-sizes 1,2,4,8,16 --num-pairs 200
```

### benchmark_vector_search.py

Measures vector search performance with various corpus sizes.

**Usage:**
```bash
python benchmark_vector_search.py [options]

Options:
  --corpus-sizes SIZES  Comma-separated corpus sizes (default: 1000,5000,10000)
  --embedding-dim DIM   Embedding dimension: 384 or 1536 (default: 384)
  --database-url URL    Database URL (default: from DATABASE_URL env)
  --output FILE         Output JSON file path
  --skip-corpus-sizes   Skip corpus size benchmark
```

**What it measures:**
- Query latency with different corpus sizes
- Batch query throughput
- Impact of top_k parameter
- Scalability with corpus growth
- Memory usage

**Example:**
```bash
# Test different corpus sizes
python benchmark_vector_search.py --corpus-sizes 1000,5000,10000

# Test with 1536-dim embeddings
python benchmark_vector_search.py --embedding-dim 1536 --corpus-sizes 5000,10000

# Use custom database
python benchmark_vector_search.py --database-url postgresql://localhost/testdb
```

**Note:** This benchmark creates test data in the database. Use a test database, not production!

### benchmark_pipeline.py

Measures end-to-end verification pipeline performance.

**Usage:**
```bash
python benchmark_pipeline.py [options]

Options:
  --claims-file FILE    Path to test claims JSON (default: tests/fixtures/test_claims.json)
  --num-evidence N      Number of evidence items (default: 1000)
  --embedding-dim DIM   Embedding dimension: 384 or 1536 (default: 384)
  --iterations N        Iterations per claim (default: 2)
  --database-url URL    Database URL
  --output FILE         Output JSON file path
  --skip-latency        Skip latency benchmark
  --skip-throughput     Skip throughput benchmark
```

**What it measures:**
- End-to-end claim verification latency
- Pipeline throughput (claims per second)
- Component breakdown (embedding, retrieval, NLI, aggregation)
- Success rate and error handling
- Verdict distribution
- Memory usage

**Example:**
```bash
# Standard benchmark
python benchmark_pipeline.py --num-evidence 1000 --iterations 2

# Quick test with fewer claims
python benchmark_pipeline.py --num-evidence 500 --iterations 1 --skip-throughput

# Use custom claims file
python benchmark_pipeline.py --claims-file my_test_claims.json
```

## Comparison and Regression Detection

### compare_results.py

Compare benchmark results and detect performance regressions.

**Usage:**
```bash
python compare_results.py [options]

Options:
  --baseline FILE       Path to baseline results JSON
  --current FILE        Path to current results JSON
  --threshold FLOAT     Regression threshold (default: 0.1 = 10%)
  --list                List all available results
  --output FILE         Path to save comparison report JSON
  --results-dir DIR     Directory containing results (default: results/)
```

**What it does:**
- Compares current results against baseline
- Detects performance regressions (>10% slower by default)
- Identifies performance improvements
- Generates detailed comparison reports
- Returns non-zero exit code if regressions detected

**Examples:**
```bash
# List all available results
python compare_results.py --list

# Compare against baseline
python compare_results.py \
  --baseline baseline_embeddings_2025-10-27.json \
  --current embeddings_2025-10-28.json

# Use stricter threshold (5%)
python compare_results.py \
  --baseline baseline_nli_2025-10-27.json \
  --current nli_2025-10-28.json \
  --threshold 0.05

# Save comparison report
python compare_results.py \
  --baseline baseline_pipeline_2025-10-27.json \
  --current pipeline_2025-10-28.json \
  --output comparison_report.json
```

## Results Directory Structure

```
scripts/benchmarks/results/
├── baseline_embeddings_2025-10-27.json      # Baseline results
├── baseline_nli_2025-10-27.json
├── baseline_vector_search_2025-10-27.json
├── baseline_pipeline_2025-10-27.json
├── embeddings_2025-10-28_143022.json        # Regular runs
├── nli_2025-10-28_143156.json
├── vector_search_2025-10-28_143342.json
├── pipeline_2025-10-28_144120.json
└── comparison_report.json                    # Comparison reports
```

## Result File Format

All benchmark results are saved as JSON files with this structure:

```json
{
  "timestamp": "2025-10-27T14:30:45.123456",
  "system": {
    "python_version": "3.12.0",
    "pytorch_version": "2.1.0",
    "device": "cpu",
    "model": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "benchmarks": {
    "single_text": {
      "avg_latency_ms": 45.2,
      "p95_latency_ms": 52.1,
      "passed": true
    },
    "batch_sizes": {
      "best_batch_size": 32,
      "best_throughput": 678.5,
      "passed": true
    }
  }
}
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e ".[ml,dev]"

      - name: Run benchmarks
        run: |
          python scripts/benchmarks/run_all_benchmarks.py --quick

      - name: Compare against baseline
        run: |
          python scripts/benchmarks/compare_results.py \
            --baseline results/baseline_embeddings_2025-10-27.json \
            --current results/embeddings_*.json
```

## Best Practices

### Establishing Baselines

1. **Run on stable hardware**: Use consistent hardware for baseline measurements
2. **Warm up models**: First run may be slower due to model loading
3. **Multiple iterations**: Run at least 3 times and take average
4. **Document conditions**: Record system specs, Python version, library versions

```bash
# Generate baselines
python run_all_benchmarks.py --baseline

# Move to baseline directory
mkdir -p baselines/$(date +%Y-%m-%d)
cp results/baseline_*.json baselines/$(date +%Y-%m-%d)/
```

### Detecting Regressions

1. **Set appropriate thresholds**: 10% is default, adjust based on component
2. **Run before merging**: Always benchmark before merging major changes
3. **Investigate failures**: Don't ignore regressions, investigate root cause
4. **Track over time**: Keep historical results for trend analysis

### Optimization Workflow

1. **Establish baseline**: `python run_all_benchmarks.py --baseline`
2. **Make optimization**: Modify code
3. **Run benchmark**: `python benchmark_<component>.py`
4. **Compare results**: `python compare_results.py --baseline ... --current ...`
5. **Verify improvement**: Check for improvements without regressions elsewhere
6. **Update baseline**: If consistently better, update baseline

## Troubleshooting

### Benchmarks Running Slow

- Check if GPU/CUDA is properly configured
- Verify no other processes consuming resources
- Use `--quick` flag for faster iteration during development

### Database Connection Issues

- Ensure PostgreSQL is running: `systemctl status postgresql`
- Check DATABASE_URL environment variable
- Use test database, not production
- Grant proper permissions for test user

### Memory Issues

- Reduce batch sizes: `--batch-sizes 8,16`
- Reduce corpus size: `--corpus-sizes 1000,5000`
- Close other applications
- Check available RAM: `free -h`

### Inconsistent Results

- Warm up models before benchmarking (done automatically)
- Run multiple iterations: `--iterations 10`
- Check for background processes
- Ensure consistent system load

## Advanced Usage

### Custom Test Data

```python
# Create custom test claims
import json

claims = [
    {"text": "Your custom claim 1", "category": "test"},
    {"text": "Your custom claim 2", "category": "test"},
]

with open("custom_claims.json", "w") as f:
    json.dump({"claims": claims}, f)

# Use custom claims
python benchmark_pipeline.py --claims-file custom_claims.json
```

### Profiling

For detailed profiling, use Python's cProfile:

```bash
python -m cProfile -o profile.stats benchmark_embeddings.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Continuous Monitoring

Set up automated benchmarking:

```bash
#!/bin/bash
# daily_benchmark.sh

DATE=$(date +%Y-%m-%d)
python scripts/benchmarks/run_all_benchmarks.py --quick

# Compare against baseline
python scripts/benchmarks/compare_results.py \
  --baseline results/baseline_embeddings_*.json \
  --current results/embeddings_*.json \
  || echo "REGRESSION DETECTED!" | mail -s "Performance Alert" team@example.com
```

## Contributing

When adding new benchmarks:

1. Follow existing script structure
2. Include `--output` parameter for JSON results
3. Add `--skip-*` flags for optional components
4. Document performance targets
5. Update this README

## Related Documentation

- [Performance Tools README](../README_PERFORMANCE_TOOLS.md)
- [Corpus Loading Guide](../README_CORPUS_LOADING.md)
- [Testing Guide](../../tests/README.md)

## Support

For questions or issues:
- Open a GitHub issue
- Check existing benchmark results in `results/`
- Review system requirements in main README
