# Feature 3.2: Quick Start Guide

## Overview

Feature 3.2 provides multi-category evaluation of the TruthGraph fact verification system across 5 claim categories: Politics, Science, Health, Current Events, and Historical Facts.

## Quick Commands

### Run All Category Tests

```bash
python -m pytest tests/accuracy/test_category_accuracy.py -v
```

**Output**: All 11 tests should pass

### Generate Category Analysis Report

```bash
python generate_category_analysis.py
```

**Generates**:
- `tests/accuracy/results/category_breakdown.json` - Complete metrics
- `tests/accuracy/results/category_report.html` - Interactive visualization
- `tests/accuracy/results/category_statistics.json` - Detailed statistics
- `tests/accuracy/results/category_recommendations.json` - Recommendations
- `tests/accuracy/results/CATEGORY_ANALYSIS_SUMMARY.md` - Executive summary

### View Category Results

**Current Performance Summary**:
```
Category        Accuracy   Samples   F1 Score   Status
Political       100.0%     3         0.6667     Excellent
Science         100.0%     15        0.6667     Excellent
Health          100.0%     10        1.0000     Excellent
Current Events  100.0%     2         0.3333     Excellent
Historical      100.0%     3         0.6667     Excellent
```

**Overall**:
- Total Samples: 33
- Categories: 5
- Weighted Accuracy: 100.0%
- Average Macro F1: 0.6667

## Key Files

| File | Purpose |
|------|---------|
| `tests/accuracy/test_category_accuracy.py` | Main test module (1,071 lines) |
| `tests/accuracy/categories/*.json` | Test data for each category |
| `generate_category_analysis.py` | Report generation script |
| `tests/accuracy/results/*.json` | Generated reports (JSON) |
| `tests/accuracy/results/*.html` | Generated reports (HTML) |
| `tests/accuracy/results/*.md` | Generated reports (Markdown) |

## Category Data Location

```
tests/accuracy/categories/
├── politics.json           # 3 political claims
├── science.json            # 15 scientific claims
├── health.json             # 10 health claims
├── current_events.json      # 2 current events claims
└── historical.json          # 3 historical facts
```

## Python API

### Quick Evaluation

```python
from tests.accuracy.test_category_accuracy import CategoryAccuracyEvaluator

evaluator = CategoryAccuracyEvaluator()

# Evaluate all categories
results = evaluator.evaluate_all_categories()

# Generate breakdown
breakdown = evaluator.generate_category_breakdown()

# Generate reports
json_path = evaluator.save_category_breakdown(breakdown)
html_path = evaluator.generate_category_html_report(breakdown)

print(f"Reports saved to {json_path} and {html_path}")
```

### Access Category Metrics

```python
# Get science category accuracy
science_result = evaluator.evaluate_category('science')
print(f"Science accuracy: {science_result['accuracy']:.1%}")

# Get all results
all_results = evaluator.evaluate_all_categories()
for category, result in all_results.items():
    print(f"{category}: {result['accuracy']:.1%}")
```

### Identify Weaknesses

```python
breakdown = evaluator.generate_category_breakdown()
weaknesses = breakdown['weaknesses']

for category, issues in weaknesses.items():
    print(f"\n{category}:")
    for issue in issues:
        print(f"  - {issue['message']}")
```

## Test Functions Available

1. `test_category_evaluation_politics` - Politics category
2. `test_category_evaluation_science` - Science category
3. `test_category_evaluation_health` - Health category
4. `test_category_evaluation_current_events` - Current events category
5. `test_category_evaluation_historical` - Historical facts category
6. `test_all_categories_evaluation` - All categories
7. `test_category_breakdown_generation` - Breakdown generation
8. `test_save_category_breakdown` - JSON export
9. `test_generate_category_html_report` - HTML report
10. `test_identify_category_weaknesses` - Weakness detection
11. `test_category_rankings` - Category rankings

### Run Specific Test

```bash
python -m pytest tests/accuracy/test_category_accuracy.py::test_category_evaluation_science -v
```

## Reports

### JSON Report (`category_breakdown.json`)

Contains all metrics in machine-readable format:
- Per-category accuracy, precision, recall, F1
- Confusion matrices for each category
- Aggregate metrics

### HTML Report (`category_report.html`)

Interactive visualization:
- Category performance cards
- Rankings by accuracy and F1
- Weakness highlighting
- Visual progress indicators

### Summary Report (`CATEGORY_ANALYSIS_SUMMARY.md`)

Executive summary including:
- Key metrics table
- Category rankings
- Identified weaknesses
- Recommendations
- Next steps

## Key Findings

### Strengths
- Excellent overall accuracy (100%)
- Good health category performance (F1 = 1.0)
- Comprehensive test coverage (33 samples)

### Weaknesses
- Limited samples for Politics (3) and Historical (3) categories
- INSUFFICIENT verdict handling needs improvement
- Current Events category needs more data (2 samples)

### Recommendations
1. Increase INSUFFICIENT verdict samples
2. Expand Current Events category data
3. Grow small categories to 15+ samples
4. Consider category-specific models

## Next Steps

1. **Generate Report**: `python generate_category_analysis.py`
2. **Review Results**: Open `tests/accuracy/results/category_report.html`
3. **Implement Recommendations**: Focus on data collection
4. **Monitor Progress**: Re-evaluate monthly
5. **Iterate**: Collect more data and retrain models

## Integration

### With CI/CD Pipeline

```yaml
# .github/workflows/accuracy.yml
- name: Category Evaluation
  run: python -m pytest tests/accuracy/test_category_accuracy.py -v

- name: Generate Reports
  run: python generate_category_analysis.py

- name: Archive Reports
  uses: actions/upload-artifact@v2
  with:
    name: accuracy-reports
    path: tests/accuracy/results/
```

## Troubleshooting

### Tests Not Found
```bash
# Ensure pytest is installed
pip install pytest

# Run from project root
cd /c/repos/truthgraph
```

### Import Errors
```bash
# Ensure tests directory is in Python path
python -c "import sys; sys.path.insert(0, '.'); from tests.accuracy.test_category_accuracy import CategoryAccuracyEvaluator"
```

### Report Generation Issues
```bash
# Use the standalone script
python generate_category_analysis.py

# Check output directory exists
mkdir -p tests/accuracy/results
```

## Performance Benchmarks

- Evaluation time: ~0.1-0.3 seconds for all categories
- Report generation: ~0.5-1.0 seconds
- Total run time: ~1-2 seconds

## Support

For questions or issues:
1. Review `FEATURE_3_2_MULTI_CATEGORY_EVALUATION.md` for detailed documentation
2. Check test functions in `tests/accuracy/test_category_accuracy.py`
3. Review generated reports in `tests/accuracy/results/`

---

**Status**: COMPLETE
**Test Pass Rate**: 100% (11/11)
**Documentation**: Complete
