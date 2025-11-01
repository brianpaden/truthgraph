# Accuracy Testing Framework - Quick Start Guide

## Installation

The framework is already integrated into the TruthGraph project. No additional installation needed.

```bash
cd /c/repos/truthgraph
```

## Basic Usage

### 1. Evaluate Accuracy

```python
from tests.accuracy import AccuracyFramework

# Initialize framework
framework = AccuracyFramework()

# Prepare your data
predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
expected_verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

# Run evaluation
results = framework.evaluate(predictions, expected_verdicts)

# Check results
print(f"Accuracy: {results['accuracy']:.1%}")
print(f"Macro F1: {results['macro_f1']:.4f}")
```

### 2. Generate Reports

```python
from tests.accuracy import Reporter

reporter = Reporter()

# Generate HTML report
html_path = reporter.generate_html_report(results)
print(f"Report: {html_path}")

# View in browser
# Open: tests/accuracy/results/accuracy_report.html
```

### 3. Category Analysis

```python
# Evaluate with categories
categories = ["science", "history", "health"]
results = framework.evaluate(predictions, expected_verdicts, categories)

# View per-category metrics
for category, metrics in results["per_category"].items():
    print(f"{category}: {metrics['accuracy']:.1%}")
```

### 4. Detect Regressions

```python
# Load baseline results
baseline = framework.load_results("baseline_results.json")

# Check current against baseline
is_regression, details = framework.detect_regression(results, baseline)

if is_regression:
    print("WARNING: Accuracy regression detected!")
```

### 5. Track Trends

```python
# Add to history
trend = framework.track_trend(results)

# View trend
print(f"Entries: {trend['entries']}")
print(f"Current: {trend['current']['accuracy']:.1%}")
if trend['previous']:
    print(f"Previous: {trend['previous']['accuracy']:.1%}")
```

## Running Tests

### Run All Accuracy Tests

```bash
# All tests
pytest tests/accuracy/test_accuracy.py tests/accuracy/test_validation_with_data.py -v

# Specific test class
pytest tests/accuracy/test_accuracy.py::TestAccuracyMetrics -v

# Specific test
pytest tests/accuracy/test_accuracy.py::TestAccuracyMetrics::test_calculate_accuracy_perfect -v
```

### Generate Sample Reports

```bash
# Generate reports with sample data
python -c "
import sys
sys.path.insert(0, '.')
from tests.accuracy import AccuracyFramework, Reporter

# Load test data and evaluate
# (See FRAMEWORK_DOCUMENTATION.md for full example)
"
```

## Report Formats

### HTML Report
- **Location**: `tests/accuracy/results/accuracy_report.html`
- **Format**: Interactive visualization with CSS styling
- **Use**: View in web browser

### JSON Report
- **Location**: `tests/accuracy/results/accuracy_results.json`
- **Format**: Machine-readable JSON
- **Use**: Programmatic access, tool integration

### CSV Confusion Matrix
- **Location**: `tests/accuracy/results/confusion_matrix.csv`
- **Format**: Comma-separated values
- **Use**: Import to Excel/spreadsheet tools

### Text Summary
- **Location**: `tests/accuracy/results/accuracy_summary.txt`
- **Format**: Human-readable text
- **Use**: Email reports, logs

## Key Metrics

| Metric | Meaning | Target |
|--------|---------|--------|
| Accuracy | Overall correctness | >70% |
| Precision | Positive prediction accuracy per verdict | >0.75 |
| Recall | True positive rate per verdict | >0.75 |
| F1 Score | Harmonic mean of precision/recall | >0.70 |
| Macro F1 | Average F1 across verdicts | >0.70 |

## Verdict Types

- **SUPPORTED**: Claim is supported by evidence
- **REFUTED**: Claim is contradicted by evidence
- **INSUFFICIENT**: Not enough evidence

## Common Tasks

### Task 1: Evaluate New Model Version

```python
from tests.accuracy import AccuracyFramework, Reporter

framework = AccuracyFramework()
reporter = Reporter()

# Get predictions from new model
predictions = get_model_predictions(test_claims)
expected = get_expected_verdicts(test_claims)

# Evaluate
results = framework.evaluate(predictions, expected)

# Report
reporter.generate_html_report(results)
reporter.generate_json_report(results)
```

### Task 2: Find Regression Issues

```python
# Load baseline
baseline = framework.load_results("tests/accuracy/results/baseline.json")

# Check current
is_regression, details = framework.detect_regression(results, baseline, threshold=0.05)

if is_regression:
    # Print regression details
    for metric, data in details["metrics_checked"].items():
        if data["regressed"]:
            print(f"REGRESSED: {metric}")
            print(f"  Baseline: {data['baseline']:.4f}")
            print(f"  Current:  {data['current']:.4f}")
            print(f"  Delta:    {data['delta']:.4f}")
```

### Task 3: Category Performance

```python
# Add categories to evaluation
results = framework.evaluate(predictions, expected, categories)

# Find worst performing categories
performance = {}
for cat, metrics in results["per_category"].items():
    performance[cat] = metrics["accuracy"]

worst = min(performance, key=performance.get)
print(f"Worst performing: {worst} ({performance[worst]:.1%})")
```

### Task 4: Historical Tracking

```python
# Save results periodically
for date, results in daily_evaluations:
    framework.track_trend(results, "history.json")

# Load history
with open("history.json") as f:
    history = json.load(f)

# Plot trend
import matplotlib.pyplot as plt
accuracies = [e["accuracy"] for e in history]
plt.plot(accuracies)
plt.show()
```

## API Quick Reference

### AccuracyFramework

```python
# Main class for evaluations
framework = AccuracyFramework(results_dir="tests/accuracy/results")

# Run evaluation
results = framework.evaluate(predictions, expected_verdicts, categories)

# Regression detection
is_regress, details = framework.detect_regression(current, baseline, threshold=0.05)

# Track trends
trend = framework.track_trend(results, history_file="history.json")

# Save/load results
framework.save_results_json(results, "file.json")
framework.save_confusion_matrix_csv("cm.csv")
results = framework.load_results("file.json")
```

### Reporter

```python
# Main class for reports
reporter = Reporter(output_dir="tests/accuracy/results")

# Generate reports
html_path = reporter.generate_html_report(metrics)
json_path = reporter.generate_json_report(metrics)
text_path = reporter.save_summary(metrics)

# Get summary as string
summary = reporter.generate_summary(metrics)
```

### AccuracyMetrics

```python
# Low-level metrics calculation
metrics = AccuracyMetrics()

# Add predictions
metrics.add_prediction(predicted, expected, category)

# Calculate metrics
acc = metrics.calculate_accuracy()
precision = metrics.calculate_precision()
recall = metrics.calculate_recall()
f1 = metrics.calculate_f1()
cm = metrics.generate_confusion_matrix()

# Category breakdown
breakdown = metrics.per_category_breakdown()

# Get all at once
summary = metrics.get_metrics_summary()
```

## Files Reference

| File | Purpose |
|------|---------|
| `tests/accuracy/metrics.py` | Metric calculations |
| `tests/accuracy/accuracy_framework.py` | Main framework |
| `tests/accuracy/reporters.py` | Report generation |
| `tests/accuracy/test_accuracy.py` | Unit tests (33 tests) |
| `tests/accuracy/test_validation_with_data.py` | Integration tests (6 tests) |
| `tests/accuracy/FRAMEWORK_DOCUMENTATION.md` | Full documentation |
| `FEATURE_3_1_ACCURACY_FRAMEWORK_REPORT.md` | Implementation report |

## Troubleshooting

### "Accuracy is low"
1. Check confusion matrix for error patterns
2. Review failing cases
3. Consider category-specific improvements
4. Check data quality

### "Regression detected"
1. Review recent changes to model
2. Check data differences
3. Compare error patterns
4. Verify threshold is appropriate

### "Report generation failed"
1. Verify output directory exists
2. Check file permissions
3. Ensure valid metrics data
4. Check for file encoding issues

## Next Steps

1. **Read Full Documentation**: `tests/accuracy/FRAMEWORK_DOCUMENTATION.md`
2. **Review Implementation Report**: `FEATURE_3_1_ACCURACY_FRAMEWORK_REPORT.md`
3. **Explore Sample Reports**: View `tests/accuracy/results/accuracy_report.html`
4. **Run Tests**: `pytest tests/accuracy/ -v`
5. **Integrate into Pipeline**: Add to CI/CD workflow

## Support

For detailed API documentation, usage examples, and troubleshooting:
- See: `tests/accuracy/FRAMEWORK_DOCUMENTATION.md`
- Examples: `tests/accuracy/test_accuracy.py` and `test_validation_with_data.py`
- Report: `FEATURE_3_1_ACCURACY_FRAMEWORK_REPORT.md`

## Summary

The Accuracy Testing Framework provides production-ready tools for:
- Measuring accuracy across multiple verdict types
- Detecting performance regressions
- Tracking trends over time
- Generating comprehensive reports
- Per-category performance analysis

**Current Status**: 39 tests passing, 73.1% accuracy on 78 test claims, ready for production use.
