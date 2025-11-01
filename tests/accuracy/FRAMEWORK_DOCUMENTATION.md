# Accuracy Testing Framework Documentation

## Overview

The Accuracy Testing Framework provides comprehensive tools for measuring, tracking, and reporting on the accuracy of the TruthGraph fact verification pipeline. It supports evaluation across multiple verdict types, categories, and tracks performance trends over time.

## Architecture

The framework consists of three core modules:

### 1. Metrics Module (`metrics.py`)

Calculates comprehensive accuracy metrics including:

- **Accuracy**: Overall correctness rate
- **Precision**: Per-verdict positive prediction rate
- **Recall**: Per-verdict true positive rate
- **F1 Score**: Harmonic mean of precision and recall
- **Macro F1**: Average F1 across all verdicts
- **Weighted F1**: F1 weighted by class support
- **Confusion Matrix**: 3x3 matrix showing prediction distribution

#### Key Classes

**`AccuracyMetrics`**

Main class for metric calculation.

```python
from tests.accuracy.metrics import AccuracyMetrics

metrics = AccuracyMetrics()

# Add predictions
metrics.add_prediction("SUPPORTED", "SUPPORTED", category="science")
metrics.add_prediction("REFUTED", "REFUTED", category="history")

# Calculate metrics
accuracy = metrics.calculate_accuracy()  # float between 0 and 1
precision = metrics.calculate_precision()  # Dict[str, float]
recall = metrics.calculate_recall()  # Dict[str, float]
f1 = metrics.calculate_f1()  # Dict[str, float]

# Get confusion matrix
cm = metrics.generate_confusion_matrix()  # Dict[str, Dict[str, int]]

# Per-category analysis
breakdown = metrics.per_category_breakdown()  # Dict[str, Dict[str, float]]

# Get full summary
summary = metrics.get_metrics_summary()
```

### 2. Framework Module (`accuracy_framework.py`)

Orchestrates evaluations, trend tracking, and regression detection.

#### Key Classes

**`AccuracyFramework`**

Main framework for running evaluations.

```python
from tests.accuracy.accuracy_framework import AccuracyFramework

framework = AccuracyFramework(results_dir="tests/accuracy/results")

# Run evaluation
predictions = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
categories = ["science", "history", "health"]

results = framework.evaluate(predictions, verdicts, categories)

# Results contain:
# {
#   "timestamp": "2025-11-01T03:35:24",
#   "total_samples": 3,
#   "accuracy": 1.0,
#   "macro_f1": 1.0,
#   "weighted_f1": 1.0,
#   "precision": {"SUPPORTED": 1.0, ...},
#   "recall": {"SUPPORTED": 1.0, ...},
#   "f1": {"SUPPORTED": 1.0, ...},
#   "confusion_matrix": {...},
#   "per_category": {...}
# }

# Detect regressions
baseline = {...}  # Previous results
current = results
is_regression, details = framework.detect_regression(current, baseline, threshold=0.05)

# Track trends
trend = framework.track_trend(results, history_file="history.json")

# Save outputs
json_path = framework.save_results_json(results)
csv_path = framework.save_confusion_matrix_csv()
```

### 3. Reporter Module (`reporters.py`)

Generates reports in multiple formats for human and machine consumption.

#### Key Classes

**`Reporter`**

Main class for report generation.

```python
from tests.accuracy.reporters import Reporter

reporter = Reporter(output_dir="tests/accuracy/results")

# Generate HTML report (interactive visualization)
html_path = reporter.generate_html_report(
    metrics=results,
    output_file="accuracy_report.html",
    title="Accuracy Report"
)

# Generate JSON report (machine-readable)
json_path = reporter.generate_json_report(metrics=results)

# Generate text summary
summary = reporter.generate_summary(metrics=results)
text_path = reporter.save_summary(metrics=results)
```

## Usage Examples

### Basic Evaluation

```python
from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.reporters import Reporter

# Initialize
framework = AccuracyFramework()
reporter = Reporter()

# Get predictions from your system
predictions = get_predictions_from_system(claims)
expected_verdicts = get_expected_verdicts(claims)

# Evaluate
results = framework.evaluate(predictions, expected_verdicts)

# Report
html_report = reporter.generate_html_report(results)
print(f"Report generated: {html_report}")
```

### Category-Based Analysis

```python
# With categories
categories = [claim.category for claim in claims]
results = framework.evaluate(predictions, expected_verdicts, categories)

# Access per-category metrics
for category, metrics in results["per_category"].items():
    print(f"{category}: {metrics['accuracy']:.1%}")
```

### Regression Detection

```python
# Load baseline from previous run
baseline_results = framework.load_results("baseline_results.json")

# Current evaluation
current_results = framework.evaluate(predictions, verdicts)

# Check for regressions
is_regression, details = framework.detect_regression(
    current_results,
    baseline_results,
    threshold=0.05  # 5% threshold
)

if is_regression:
    print("WARNING: Accuracy regression detected!")
    for metric, data in details["metrics_checked"].items():
        print(f"  {metric}: {data['baseline']} -> {data['current']}")
```

### Trend Tracking

```python
# Add to history
trend = framework.track_trend(results, history_file="history.json")

# View trend
print(f"Total entries: {trend['entries']}")
if trend["previous"]:
    print(f"Previous accuracy: {trend['previous']['accuracy']:.1%}")
print(f"Current accuracy: {trend['current']['accuracy']:.1%}")
print(f"Improvements: {trend['improvements']}")
```

## Verdict Formats

The framework supports three verdict types:

- **SUPPORTED**: Claim is supported by evidence
- **REFUTED**: Claim is contradicted by evidence
- **INSUFFICIENT**: Not enough evidence to determine

## Metrics Interpretation

### Accuracy

Percentage of predictions that match expected verdicts.

- 90%+ : Excellent performance
- 80-90%: Good performance
- 70-80%: Acceptable performance
- <70%: Below target (requires investigation)

### Precision & Recall

For each verdict type:

- **Precision**: Of all predictions of this type, how many were correct?
- **Recall**: Of all actual cases of this type, how many were correctly identified?

### F1 Score

Harmonic mean of precision and recall for each verdict.

- Balances precision and recall
- Higher is better (0-1 scale)
- Use macro F1 for overall performance across verdicts
- Use weighted F1 to account for class imbalance

### Confusion Matrix

3x3 matrix showing prediction distribution:

```
           SUPPORTED  REFUTED  INSUFFICIENT
SUPPORTED     TP         FP         FP
REFUTED       FN         TP         FP
INSUFFICIENT  FN         FN         TP
```

Where:
- TP = True Positive (correct prediction)
- FP = False Positive (incorrect prediction)
- FN = False Negative (missed prediction)

## Report Formats

### HTML Report

Interactive visual report with:
- Overall metrics dashboard
- Per-verdict performance table
- Confusion matrix visualization
- Per-category breakdown
- Professional styling

View in web browser: `accuracy_report.html`

### JSON Report

Machine-readable format containing all metrics and data.

Useful for:
- Integration with other tools
- Automated comparison
- Programmatic access

### CSV Confusion Matrix

Comma-separated values format showing the confusion matrix.

Columns: SUPPORTED, REFUTED, INSUFFICIENT
Rows: SUPPORTED, REFUTED, INSUFFICIENT

### Text Summary

Human-readable text report with all metrics and breakdowns.

Useful for:
- Quick review
- Email reports
- Logs and records

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Accuracy Testing

on: [push, pull_request]

jobs:
  accuracy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -e .
      - name: Run accuracy tests
        run: pytest tests/accuracy/test_accuracy.py -v
      - name: Generate reports
        run: python tests/accuracy/generate_sample_reports.py
      - name: Upload HTML report
        uses: actions/upload-artifact@v2
        with:
          name: accuracy-reports
          path: tests/accuracy/results/
```

## Performance Baselines

### Expected Accuracy

With the current TruthGraph pipeline:

- **Science/Health**: 80-85% (well-documented facts)
- **History**: 75-80% (historical records)
- **Current Events**: 70-75% (recent, complex)
- **Politics**: 65-70% (contentious, opinion-heavy)
- **Overall**: >70% (minimum requirement)

## Troubleshooting

### Low Accuracy on Specific Categories

1. Check confusion matrix for error patterns
2. Review failing cases in detail
3. Consider category-specific improvements
4. Update training data for underperforming categories

### Regression Detection Issues

- Verify baseline results are representative
- Check threshold settings (default: 5%)
- Review recent changes to model/data

### Report Generation Failures

- Verify output directory exists and is writable
- Check for file encoding issues
- Ensure valid metrics data is provided

## API Reference

### AccuracyMetrics

#### Methods

- `add_prediction(pred, expected, category=None)` - Add a prediction
- `calculate_accuracy()` -> float - Overall accuracy
- `calculate_precision()` -> Dict[str, float] - Per-verdict precision
- `calculate_recall()` -> Dict[str, float] - Per-verdict recall
- `calculate_f1()` -> Dict[str, float] - Per-verdict F1
- `calculate_macro_f1()` -> float - Average F1
- `calculate_weighted_f1()` -> float - Weighted F1
- `generate_confusion_matrix()` -> Dict - Confusion matrix
- `get_confusion_matrix_array()` -> np.ndarray - Array format
- `per_category_breakdown()` -> Dict - Category metrics
- `get_metrics_summary()` -> Dict - Complete summary
- `reset()` - Clear all data

### AccuracyFramework

#### Methods

- `evaluate(predictions, verdicts, categories=None)` -> Dict - Run evaluation
- `detect_regression(current, baseline, threshold=0.05)` -> Tuple - Check for regression
- `track_trend(results, history_file=None)` -> Dict - Track trends
- `save_results_json(results, output_file=None)` -> str - Save JSON
- `save_confusion_matrix_csv(output_file=None)` -> str - Save CSV
- `load_results(results_file)` -> Dict - Load previous results
- `compare_evaluations(results1, results2)` -> Dict - Compare two runs

### Reporter

#### Methods

- `generate_html_report(metrics, output_file=None, title=None)` -> str - HTML report
- `generate_json_report(metrics, output_file=None)` -> str - JSON report
- `generate_summary(metrics)` -> str - Text summary
- `save_summary(metrics, output_file=None)` -> str - Save summary

## Files and Directories

```
tests/accuracy/
├── metrics.py                          # Metric calculations
├── accuracy_framework.py               # Core framework
├── reporters.py                        # Report generation
├── test_accuracy.py                    # Unit tests (33 tests)
├── test_validation_with_data.py        # Integration tests (6 tests)
├── validate_framework.py               # Validation script
├── generate_sample_reports.py          # Report generation script
├── FRAMEWORK_DOCUMENTATION.md          # This file
├── real_world_claims.json              # Test data (28 claims)
├── real_world_evidence.json            # Supporting evidence
└── results/                            # Generated outputs
    ├── accuracy_report.html            # Interactive HTML report
    ├── accuracy_results.json           # Full metrics in JSON
    ├── accuracy_summary.txt            # Text summary
    ├── confusion_matrix.csv            # Confusion matrix
    └── history.json                    # Trend history
```

## Test Coverage

The framework has comprehensive test coverage:

- **Metrics Tests** (15 tests)
  - Accuracy calculation
  - Precision, recall, F1
  - Confusion matrix generation
  - Per-category breakdown
  - Edge cases and empty data

- **Framework Tests** (11 tests)
  - Evaluation workflow
  - Regression detection
  - Trend tracking
  - File I/O operations

- **Reporter Tests** (5 tests)
  - HTML generation
  - JSON generation
  - Text summary

- **Integration Tests** (2 tests)
  - End-to-end workflows
  - Multi-fixture validation

- **Validation Tests** (6 tests)
  - Real test data validation
  - Combined fixture evaluation
  - Requirement verification

**Total: 39 tests, >80% code coverage**

## Future Enhancements

Potential improvements for future versions:

1. **Comparative Analytics**
   - Compare against baseline over time
   - Trend analysis with statistical significance

2. **Advanced Visualizations**
   - ROC curves per verdict type
   - Precision-recall curves
   - Performance by confidence level

3. **Export Formats**
   - Excel/CSV with pivot tables
   - PDF reports
   - Markdown reports

4. **Integration**
   - Prometheus metrics export
   - Integration with monitoring systems
   - Real-time dashboards

5. **Advanced Metrics**
   - Matthews Correlation Coefficient
   - Cohen's Kappa
   - ROC AUC scores

## Support and Contributions

For issues or questions:
1. Check troubleshooting section above
2. Review test cases for usage examples
3. Check generated HTML report for visualization
4. Review individual test results

## Version History

### Version 1.0 (November 2025)
- Initial release
- Core metrics calculation
- Framework for evaluation
- Report generation (HTML, JSON, text, CSV)
- Regression detection
- Trend tracking
- Comprehensive test suite
- Validation with real test data
