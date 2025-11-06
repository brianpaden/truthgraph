# Feature 3.4: Model Robustness Testing - Quick Start Guide

## Overview

Feature 3.4 provides a comprehensive robustness testing framework to evaluate the TruthGraph fact verification system's ability to handle input variations and challenging conditions across 5 dimensions.

## Quick Start

### Run All Robustness Tests

```bash
cd /c/repos/truthgraph
pytest tests/robustness/ -v
```

Expected output:
```
============================= 75 passed in 0.47s ==============================
```

### Run Specific Dimension Tests

```bash
# Test typo robustness
pytest tests/robustness/test_typos.py -v

# Test paraphrase robustness
pytest tests/robustness/test_paraphrasing.py -v

# Test adversarial robustness
pytest tests/robustness/test_adversarial.py -v

# Test noise robustness
pytest tests/robustness/test_noise.py -v

# Test multilingual robustness
pytest tests/robustness/test_multilingual.py -v
```

### Generate Robustness Reports

```bash
cd /c/repos/truthgraph
python tests/robustness/evaluate_robustness.py
```

This generates:
- `tests/robustness/results/robustness_report.json` - JSON metrics
- `tests/robustness/results/vulnerability_analysis.md` - Analysis report

## File Structure

```
tests/robustness/
├── __init__.py
├── conftest.py                           # Pytest fixtures
├── robustness_utils.py                   # Core framework
├── evaluate_robustness.py                # Evaluation script
├── test_typos.py                         # Typo tests
├── test_paraphrasing.py                  # Paraphrase tests
├── test_adversarial.py                   # Adversarial tests
├── test_noise.py                         # Noise tests
├── test_multilingual.py                  # Multilingual tests
├── data/
│   ├── typo_examples.json
│   ├── paraphrase_examples.json
│   ├── adversarial_examples.json
│   ├── noise_examples.json
│   └── multilingual_examples.json
└── results/
    ├── robustness_report.json            # Generated metrics
    └── vulnerability_analysis.md         # Generated analysis
```

## Robustness Dimensions

### 1. Typo Robustness (`test_typos.py`)
Tests handling of character-level errors:
- Single character typos
- Multiple typos per claim
- Repeated characters
- Punctuation errors

**Example**: "Th3 E4rth 1s r0und" should be handled like "The Earth is round"

### 2. Paraphrase Robustness (`test_paraphrasing.py`)
Tests handling of semantically equivalent claims:
- Synonym substitution
- Structural rearrangement
- Pronoun variation
- Active/passive voice

**Example**: "The Amazon produces oxygen" vs "Oxygen is produced by the Amazon"

### 3. Adversarial Robustness (`test_adversarial.py`)
Tests handling of adversarially designed examples:
- Double negation
- Contradiction injection
- Confidence confusion
- Scope shifting

**Example**: "It is not the case that vaccines do not prevent disease"

### 4. Noise Robustness (`test_noise.py`)
Tests handling of degraded/noisy input:
- Character corruption (OCR errors)
- Incomplete text
- Irrelevant information
- Hedging language

**Example**: "Water fr33z3s 4t z3r0 d3gr33s Celsius"

### 5. Multilingual Robustness (`test_multilingual.py`)
Tests handling of non-English claims:
- Spanish claims
- French claims
- German claims
- Translation consistency

**Example**: "La selva amazónica produce oxígeno" (Spanish)

## Core Classes

### RobustnessMetrics
Tracks metrics for a robustness dimension:
```python
from tests.robustness.robustness_utils import RobustnessMetrics

metrics = RobustnessMetrics(
    dimension="typo_robustness",
    base_accuracy=0.95,
    variant_accuracy=0.85,
)
print(f"Degradation: {metrics.accuracy_degradation:.1%}")
```

### RobustnessResult
Records result of a single test:
```python
from tests.robustness.robustness_utils import RobustnessResult

result = RobustnessResult(
    test_id="typo_001",
    dimension="typo_robustness",
    base_claim="The Earth is round",
    expected_verdict="SUPPORTED",
    category="science",
    variant_claim="Th3 E4rth 1s r0und",
    predicted_verdict="SUPPORTED",
    confidence=0.92,
    is_correct=True,
    variant_type="single_typo",
)
```

### RobustnessAnalyzer
Main analysis engine:
```python
from tests.robustness.robustness_utils import RobustnessAnalyzer

# Create analyzer
analyzer = RobustnessAnalyzer("tests/robustness/results")

# Add results
analyzer.add_result(result)

# Calculate metrics
metrics = analyzer.calculate_dimension_metrics("typo_robustness", 0.95)

# Identify vulnerabilities
vulnerabilities = analyzer.identify_vulnerabilities(threshold=0.15)

# Generate recommendations
recommendations = analyzer.generate_improvement_recommendations(vulnerabilities)

# Generate reports
analyzer.generate_json_report("robustness_report.json")
analyzer.generate_markdown_report(vulnerabilities, recommendations)
```

## Test Data

### Test Data Structure

Each test data file contains:
- Metadata (dimension, version, description)
- 10 test cases with:
  - Base claim (original English claim)
  - Expected verdict (SUPPORTED/REFUTED/INSUFFICIENT)
  - Category (science, health, technology, etc.)
  - 3 variations per test case (30 total variations)

### Accessing Test Data in Tests

```python
def test_example(typo_examples):
    # typo_examples is automatically loaded fixture
    test_cases = typo_examples.get("test_cases", [])
    for test_case in test_cases:
        claim = test_case["base_claim"]
        verdict = test_case["expected_verdict"]
        variations = test_case["variations"]
```

## Reports

### robustness_report.json
Machine-readable report with:
- Test metadata
- Per-dimension metrics
- Sample results

### vulnerability_analysis.md
Human-readable report with:
- Executive summary
- Per-dimension performance
- Identified vulnerabilities
- Improvement recommendations

## Integration with Verification Pipeline

The framework is designed to integrate with the actual verification pipeline:

```python
from tests.robustness.robustness_utils import RobustnessAnalyzer, RobustnessResult
from truthgraph.api.ml_routes import verify_claim  # Example

analyzer = RobustnessAnalyzer()

for test_case in test_cases:
    for variation in test_case["variations"]:
        # Call actual verification API
        response = verify_claim(VerifyRequest(claim=variation["text"]))

        # Record result
        result = RobustnessResult(
            test_id=test_case["id"],
            dimension="typo_robustness",
            base_claim=test_case["base_claim"],
            expected_verdict=test_case["expected_verdict"],
            category=test_case["category"],
            variant_claim=variation["text"],
            predicted_verdict=response.verdict,
            confidence=response.confidence,
            is_correct=response.verdict == test_case["expected_verdict"],
            variant_type=variation.get("typo_type", "unknown"),
        )
        analyzer.add_result(result)
```

## Common Tasks

### View Test Results
```bash
cd /c/repos/truthgraph
cat tests/robustness/results/vulnerability_analysis.md
```

### Check JSON Report
```bash
cd /c/repos/truthgraph
cat tests/robustness/results/robustness_report.json | python -m json.tool
```

### Run with Coverage
```bash
pytest tests/robustness/ --cov=tests.robustness --cov-report=html
```

### Run Specific Test
```bash
pytest tests/robustness/test_typos.py::TestTypoRobustness::test_load_typo_examples_fixture -v
```

## Debugging

### Increase Verbosity
```bash
pytest tests/robustness/ -vv --tb=long
```

### Run with Logging
```bash
pytest tests/robustness/ -v --log-cli-level=DEBUG
```

### Check Fixture Loading
```bash
pytest tests/robustness/ --fixtures | grep robustness
```

## Next Steps

1. **Integrate with Verification Pipeline**: Replace simulated verification with actual API calls
2. **Analyze Results**: Review vulnerability_analysis.md for weak areas
3. **Implement Improvements**: Use recommendations to enhance model robustness
4. **Re-evaluate**: Run tests again after improvements to measure impact
5. **Monitor Trends**: Track robustness metrics over time across versions

## Resources

- Full Documentation: `/c/repos/truthgraph/FEATURE_3_4_ROBUSTNESS_TESTING_REPORT.md`
- Test Data: `/c/repos/truthgraph/tests/robustness/data/`
- Test Code: `/c/repos/truthgraph/tests/robustness/test_*.py`
- Utilities: `/c/repos/truthgraph/tests/robustness/robustness_utils.py`

## Support

For issues or questions:
1. Check the full report in `FEATURE_3_4_ROBUSTNESS_TESTING_REPORT.md`
2. Review test code in `tests/robustness/`
3. Check generated reports in `tests/robustness/results/`
