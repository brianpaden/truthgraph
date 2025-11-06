# Regression Testing Framework

Automated regression detection for TruthGraph performance and accuracy metrics.

## Overview

The regression testing framework provides comprehensive monitoring of both performance and accuracy metrics to detect any degradation in TruthGraph's capabilities. It includes:

- **Baseline Management**: Store and version baseline metrics
- **Automated Detection**: Detect regressions against established baselines
- **CI/CD Integration**: Run regression tests automatically in GitHub Actions
- **Historical Tracking**: Track metrics evolution over time
- **Configurable Thresholds**: Set acceptable variance levels per metric

## Quick Start

### 1. Create Initial Baseline

Before running regression tests, establish a baseline:

```bash
# Run performance benchmarks
python scripts/benchmarks/benchmark_embeddings.py
python scripts/benchmarks/benchmark_nli.py

# Run accuracy tests (requires database)
pytest tests/accuracy/test_accuracy_baseline.py -v

# Create baseline
python scripts/update_baseline.py --version 0.1.0
```

### 2. Run Regression Tests

```bash
# Run all regression tests
pytest tests/regression/ -v

# Run only performance regression tests
pytest tests/regression/test_performance_regression.py -v

# Run only accuracy regression tests
pytest tests/regression/test_accuracy_regression.py -v
```

### 3. Update Baseline (After Intentional Changes)

```bash
# Update baseline after performance improvements or expected changes
python scripts/update_baseline.py --version 0.2.0
```

## Architecture

### Directory Structure

```
tests/regression/
├── __init__.py                          # Package exports
├── baseline_manager.py                  # Core baseline management
├── test_performance_regression.py       # Performance tests
├── test_accuracy_regression.py          # Accuracy tests
├── test_baseline_manager.py             # Unit tests
├── baselines/                           # Stored baselines
│   ├── baseline_2025-11-06.json        # Baseline files
│   └── baseline_history.csv            # Historical tracking
└── results/                             # Test results
    └── regression_report.json          # Latest regression report
```

### Core Components

#### 1. BaselineManager

Central component for managing baselines and detecting regressions.

```python
from tests.regression import BaselineManager

manager = BaselineManager()

# Create baseline
baseline = manager.create_baseline(
    version="0.1.0",
    performance_metrics={...},
    accuracy_metrics={...}
)

# Save baseline
manager.save_baseline(baseline)

# Detect regressions
regressions = manager.detect_regressions(
    baseline,
    current_performance,
    current_accuracy
)
```

#### 2. Performance Metrics

Tracks ML service and pipeline performance:

- **Embedding Service**:
  - Latency (avg, p95, p99)
  - Throughput (texts/sec)

- **NLI Service**:
  - Latency (avg, p95, p99)
  - Throughput (pairs/sec)

- **End-to-End Pipeline**:
  - Total latency
  - Throughput (claims/sec)

- **Memory Usage**:
  - Baseline, peak, loaded memory

#### 3. Accuracy Metrics

Tracks model accuracy and quality:

- **Overall Metrics**: Accuracy, precision, recall, F1 score
- **Per-Verdict Accuracy**: SUPPORTED, REFUTED, INSUFFICIENT
- **Category Breakdown**: Accuracy per claim category
- **Confusion Matrix**: Detailed classification results

## Regression Thresholds

### Performance Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Embedding Latency | +10% | Latency can increase by 10% |
| Embedding Throughput | -10% | Throughput can drop by 10% |
| NLI Latency | +10% | Latency can increase by 10% |
| NLI Throughput | -10% | Throughput can drop by 10% |
| E2E Latency | +15% | Pipeline latency can increase by 15% |
| E2E Throughput | -10% | Pipeline throughput can drop by 10% |
| Memory Peak | +20% | Peak memory can increase by 20% |

### Accuracy Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Overall Accuracy | -2% | Cannot drop more than 2% |
| Precision | -3% | Cannot drop more than 3% |
| Recall | -3% | Cannot drop more than 3% |
| F1 Score | -3% | Cannot drop more than 3% |
| Per-Verdict Accuracy | -5% | Individual verdicts can drop by 5% |

### Severity Levels

Regressions are classified by severity:

- **Low**: 0-5% over threshold
- **Medium**: 5-10% over threshold
- **High**: 10-20% over threshold
- **Critical**: >20% over threshold

## CI/CD Integration

### GitHub Actions Workflow

The regression tests run automatically on:

- **Push to main/develop**: Run tests, fail on regressions
- **Pull Requests**: Run tests, comment on PR if regressions detected
- **Daily Schedule**: Run tests at 2 AM UTC for monitoring
- **Manual Trigger**: Run with optional baseline update

### Workflow Configuration

See [.github/workflows/regression-tests.yml](../../.github/workflows/regression-tests.yml) for details.

### Manual Workflow Trigger

```bash
# Trigger workflow manually
gh workflow run regression-tests.yml

# Trigger with baseline update
gh workflow run regression-tests.yml -f update_baseline=true
```

## Baseline Management

### Creating Baselines

Baselines capture a snapshot of performance and accuracy at a specific point:

```bash
# Create baseline with specific version
python scripts/update_baseline.py --version 0.1.0

# Create baseline with auto-detected version
python scripts/update_baseline.py
```

### Baseline Format

Baselines are stored as JSON files:

```json
{
  "version": "0.1.0",
  "timestamp": "2025-11-06T10:00:00",
  "git_commit": "abc123",
  "performance": {
    "embedding": {
      "latency_ms": 10.0,
      "throughput": 500.0,
      "p95_latency_ms": 15.0,
      "p99_latency_ms": 20.0
    },
    "nli": {...},
    "e2e": {...},
    "memory": {...}
  },
  "accuracy": {
    "overall": {
      "accuracy": 0.75,
      "precision": 0.76,
      "recall": 0.74,
      "f1_score": 0.75
    },
    "per_verdict": {...},
    "categories": {...}
  },
  "metadata": {
    "created_by": "scripts/update_baseline.py"
  }
}
```

### Historical Tracking

All baselines are tracked in `baseline_history.csv`:

```csv
timestamp,version,git_commit,overall_accuracy,e2e_latency_seconds,...
2025-11-06T10:00:00,0.1.0,abc123,0.75,5.0,500.0,20.0,1000.0
```

### Baseline Updates

Update baselines when:

1. **Intentional Performance Changes**: After optimization work
2. **Expected Accuracy Changes**: After model updates
3. **Infrastructure Changes**: After hardware/config changes
4. **Major Releases**: At milestone releases

**Never** update baselines to hide regressions without investigation.

## Regression Detection

### Running Detection

```python
from tests.regression import BaselineManager

manager = BaselineManager()

# Load baseline
baseline = manager.load_baseline()

# Get current metrics
current_perf = {...}  # From benchmarks
current_acc = {...}   # From accuracy tests

# Detect regressions
regressions = manager.detect_regressions(
    baseline,
    current_perf,
    current_acc
)

# Analyze results
for regression in regressions:
    print(f"[{regression.severity}] {regression.message}")
```

### Regression Output

When regressions are detected, you'll see:

```
======================================================================
PERFORMANCE REGRESSION DETECTED
======================================================================

[HIGH] embedding_latency_ms increased by 25%
  (from 10.00ms to 12.50ms)
  Threshold: 15.00% over limit

[MEDIUM] nli_throughput decreased by 12%
  (from 20.00 to 17.60)
  Threshold: 2.00% over limit

======================================================================
```

## Testing

### Unit Tests

Test the baseline management system:

```bash
pytest tests/regression/test_baseline_manager.py -v
```

Coverage includes:

- Data model serialization/deserialization
- Baseline persistence and loading
- Regression detection logic
- Severity classification
- Historical tracking

### Integration Tests

Test end-to-end regression detection:

```bash
# Performance regression tests
pytest tests/regression/test_performance_regression.py -v

# Accuracy regression tests
pytest tests/regression/test_accuracy_regression.py -v
```

## Troubleshooting

### No Baseline Found

**Error**: `FileNotFoundError: No baselines found`

**Solution**: Create initial baseline:
```bash
python scripts/update_baseline.py
```

### Benchmark Results Missing

**Error**: `Embedding benchmark not found`

**Solution**: Run benchmarks:
```bash
python scripts/benchmarks/benchmark_embeddings.py
python scripts/benchmarks/benchmark_nli.py
```

### Accuracy Results Missing

**Error**: `Accuracy results not found`

**Solution**: Run accuracy tests:
```bash
pytest tests/accuracy/test_accuracy_baseline.py -v
```

### False Positives

If tests fail due to normal variance:

1. Check if variance is within expected range
2. Run tests multiple times to confirm
3. Consider adjusting thresholds if consistently hitting limits
4. Update baseline if changes are intentional

### CI/CD Failures

If regression tests fail in CI/CD:

1. Review the regression report in workflow logs
2. Check if changes are intentional
3. Run tests locally to reproduce
4. Update baseline if appropriate
5. Investigate and fix if true regression

## Best Practices

### 1. Baseline Management

- ✅ Create baselines at stable points
- ✅ Version baselines semantically
- ✅ Document baseline changes in commit messages
- ✅ Keep baseline history for trend analysis
- ❌ Don't update baselines to hide problems
- ❌ Don't create baselines during unstable periods

### 2. Threshold Tuning

- ✅ Set thresholds based on expected variance
- ✅ Tighter thresholds for critical metrics
- ✅ Looser thresholds for high-variance metrics
- ✅ Document threshold rationale
- ❌ Don't set thresholds too loose (miss regressions)
- ❌ Don't set thresholds too tight (false positives)

### 3. Regression Response

- ✅ Investigate all regressions
- ✅ Document findings
- ✅ Fix true regressions before merging
- ✅ Update baseline for intentional changes
- ❌ Don't ignore regressions
- ❌ Don't bypass tests without review

### 4. CI/CD Integration

- ✅ Run regression tests on all PRs
- ✅ Block merges on critical regressions
- ✅ Monitor daily regression test runs
- ✅ Alert team on failures
- ❌ Don't skip regression tests
- ❌ Don't allow failing tests in main

## Future Enhancements

Planned improvements:

1. **Visualization**: Web dashboard for regression trends
2. **Automated Analysis**: ML-based anomaly detection
3. **Performance Profiling**: Integration with profilers
4. **Multi-Environment**: Track regressions across environments
5. **Slack Integration**: Real-time alerts on regressions
6. **Historical Comparison**: Compare against multiple baselines

## References

- [Feature 3.5 Requirements](../../planning/phases/phase_2/3_validation_framework_handoff.md)
- [Performance Benchmarks](../../scripts/benchmarks/)
- [Accuracy Testing](../accuracy/)
- [CI/CD Workflows](../../.github/workflows/)

## Support

For questions or issues:

1. Check this documentation
2. Review test examples
3. Check workflow logs
4. Consult Feature 3.5 requirements
5. Open GitHub issue with details
