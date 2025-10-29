# Real-World Claims Accuracy Testing

## Overview

This module implements comprehensive accuracy testing for TruthGraph against real-world claims from public fact-checking sources. It establishes baseline accuracy metrics and enables version-to-version performance comparison.

## Dataset

### Real-World Claims (`real_world_claims.json`)

**Statistics:**
- Total claims: 28
- Fact-checking sources: 6 (Snopes, FactCheck.org, PolitiFact, Reuters Fact Check, AP Fact Check, Full Fact)
- Categories: 6 (health, politics, science, technology, history, current_events)
- Verdict distribution:
  - SUPPORTED: 10 claims (36%)
  - REFUTED: 12 claims (43%)
  - INSUFFICIENT: 6 claims (21%)

### Real-World Evidence (`real_world_evidence.json`)

**Statistics:**
- Total evidence items: 56
- Evidence types: multiple sources including scientific papers, medical studies, official records
- NLI label distribution:
  - Entailment (supporting): 30 items (54%)
  - Contradiction (refuting): 16 items (29%)
  - Neutral: 10 items (18%)

## Dataset Sources

Evidence and reasoning extracted from:
- OECD Health Statistics Database
- National Geographic fact-checks
- CDC and WHO guidelines
- NASA official statements
- Peer-reviewed scientific journals
- Fact-checker organizations: Snopes, FactCheck.org, Reuters, AP, Full Fact

## Claim Categories

The dataset covers diverse domains:

1. **Health** (~14% of claims)
   - Medical facts (fluoride, vaccines, sugar effects)
   - Medical myths (mobile phones, antibiotics for viruses)

2. **Science** (~32% of claims)
   - Physics and astronomy
   - Environmental science
   - Biology and evolution
   - Brain science

3. **Technology** (~14% of claims)
   - Programming language history
   - Electrical properties
   - Transatlantic communication

4. **History** (~18% of claims)
   - Historical events (Great Wall, Titanic, moon landing)
   - Famous artifacts (Mona Lisa)

5. **Politics** (~7% of claims)
   - Electoral facts
   - Leadership records

6. **Current Events** (~4% of claims)
   - Recent developments

## Verdict Mapping

### Fact-Checker Verdicts → TruthGraph Format

**Snopes Mapping:**
- TRUE → SUPPORTED
- FALSE → REFUTED
- MIXTURE/MOSTLY_TRUE/MOSTLY_FALSE → INSUFFICIENT (case-by-case)
- UNPROVEN → INSUFFICIENT

**FactCheck.org Mapping:**
- TRUE → SUPPORTED
- FALSE → REFUTED
- Article conclusion analysis → SUPPORTED/REFUTED/INSUFFICIENT

**PolitiFact Mapping:**
- TRUE/MOSTLY_TRUE → SUPPORTED
- FALSE/PANTS_ON_FIRE → REFUTED
- HALF_TRUE → INSUFFICIENT

**Reuters Fact Check Mapping:**
- CLAIM TRUE → SUPPORTED
- CLAIM FALSE → REFUTED
- UNDETERMINED/MIXTURE → INSUFFICIENT

**AP Fact Check Mapping:**
- TRUE → SUPPORTED
- FALSE → REFUTED
- UNDETERMINED → INSUFFICIENT

**Full Fact Mapping:**
- CORRECT → SUPPORTED
- INCORRECT → REFUTED
- UNVERIFIABLE → INSUFFICIENT

## Data Format

### Claim Object
```json
{
  "id": "rw_001",
  "text": "The United States has the highest per capita healthcare spending in the world",
  "category": "health",
  "expected_verdict": "SUPPORTED",
  "confidence": 0.95,
  "source": "FactCheck.org",
  "source_url": "https://www.factcheck.org",
  "fact_checker_verdict": "TRUE",
  "fact_checker_reasoning": "OECD health data confirms...",
  "date_checked": "2024-10-15",
  "evidence_ids": ["rw_ev_001", "rw_ev_002"]
}
```

### Evidence Object
```json
{
  "id": "rw_ev_001",
  "content": "OECD health statistics show the United States spends approximately...",
  "source": "OECD Health Statistics Database",
  "url": "https://www.oecd.org/health/",
  "relevance": "high",
  "supports_claim": true,
  "excerpt_from_fact_checker": true,
  "nli_label": "entailment"
}
```

## Running Tests

### Run All Accuracy Tests
```bash
pytest tests/accuracy/ -v
```

### Run Specific Test Categories
```bash
# Run only fixture validation tests
pytest tests/accuracy/test_accuracy_baseline.py::test_real_world_claims_structure -v

# Run category coverage test
pytest tests/accuracy/test_accuracy_baseline.py::test_category_coverage -v

# Run all tests with accuracy marker
pytest tests/accuracy/ -m accuracy -v
```

### Run Baseline Accuracy Test (Requires Database)
```bash
# Requires TruthGraph services and database connection
pytest tests/accuracy/test_accuracy_baseline.py::test_baseline_accuracy -v
```

## Pytest Fixtures

### Claim Fixtures

#### `real_world_claims`
Loads all real-world claims with metadata.

```python
def test_claims(real_world_claims):
    assert len(real_world_claims["claims"]) >= 20
```

#### `real_world_claims_by_category`
Factory fixture to filter claims by category.

```python
def test_health_claims(real_world_claims_by_category):
    health_claims = real_world_claims_by_category("health")
    assert len(health_claims) > 0
```

#### `real_world_claims_by_verdict`
Factory fixture to filter claims by expected verdict.

```python
def test_supported_claims(real_world_claims_by_verdict):
    supported = real_world_claims_by_verdict("SUPPORTED")
    assert len(supported) > 0
```

#### `real_world_claims_by_source`
Factory fixture to filter claims by fact-checking source.

```python
def test_snopes_claims(real_world_claims_by_source):
    snopes = real_world_claims_by_source("Snopes")
    assert len(snopes) > 0
```

### Evidence Fixtures

#### `real_world_evidence`
Loads all real-world evidence items with metadata.

```python
def test_evidence(real_world_evidence):
    assert len(real_world_evidence["evidence"]) >= 30
```

### Metadata Fixtures

#### `real_world_claims_summary`
Returns summary statistics about claims dataset.

```python
def test_summary(real_world_claims_summary):
    assert real_world_claims_summary["total_claims"] >= 20
    assert len(real_world_claims_summary["categories"]) >= 4
```

#### `real_world_evidence_summary`
Returns summary statistics about evidence dataset.

### Utility Fixtures

#### `accuracy_results`
Creates an AccuracyResults tracker for measuring test results.

```python
def test_accuracy(accuracy_results):
    accuracy_results.add_result(...)
    assert accuracy_results.get_accuracy() >= 0.5
```

#### `results_dir`
Gets path to results directory (creates if needed).

```python
def test_save(results_dir):
    results_file = results_dir / "results.json"
```

## Accuracy Measurement

### AccuracyResults Class

Tracks and computes accuracy metrics:

```python
results = AccuracyResults()

# Add results
results.add_result(
    claim_id="rw_001",
    claim_text="Claim text",
    expected_verdict="SUPPORTED",
    actual_verdict="SUPPORTED",
    confidence=0.95,
    category="health",
    source="FactCheck.org",
    evidence_count=5
)

# Get metrics
overall_accuracy = results.get_accuracy()  # 0.95
category_accuracy = results.get_category_accuracy("health")  # 0.95
source_accuracy = results.get_source_accuracy("FactCheck.org")  # 0.95

# Serialize results
results_dict = results.to_dict()
```

### Confusion Matrix

Tracks prediction accuracy by verdict type:

```text
Expected vs Actual:
                SUPPORTED  REFUTED  INSUFFICIENT
SUPPORTED           8         1           1
REFUTED             0        11           1
INSUFFICIENT        1         0           5
```

## Baseline Results

Initial baseline accuracy will be established after running the full pipeline test. Results are saved to `results/baseline_results.json`.

Expected structure:
```json
{
  "metadata": {
    "timestamp": "2025-10-27T...",
    "duration_seconds": 125.4
  },
  "overall_metrics": {
    "total_claims": 28,
    "correct_verdicts": 20,
    "incorrect_verdicts": 8,
    "accuracy": 0.714,
    "accuracy_percentage": "71.4%"
  },
  "confusion_matrix": { ... },
  "category_accuracy": { ... },
  "source_accuracy": { ... },
  "detailed_results": [ ... ]
}
```

## Version Tracking

To track accuracy improvements across versions:

1. Run baseline test: `pytest tests/accuracy/test_accuracy_baseline.py::test_baseline_accuracy`
2. Results save to `results/baseline_results.json`
3. Future runs create timestamped files or update comparison log
4. Use `results/comparison_log.csv` to track trends

Example comparison log:
```csv
timestamp,version,accuracy,correct,total,duration_seconds
2025-10-27T10:00:00,1.0.0,0.714,20,28,125.4
2025-10-28T10:00:00,1.0.1,0.750,21,28,120.1
```

## Integration with TruthGraph

The accuracy tests integrate with:

1. **Verification Pipeline Service** (`truthgraph.services.verification_pipeline_service`)
   - Runs end-to-end verification
   - Returns verdict and confidence scores
   - Retrieves evidence items

2. **Evidence Database**
   - Real-world evidence corpus should be loaded
   - Vector search retrieves relevant evidence
   - NLI verification rates claim-evidence pairs

3. **ML Services**
   - Embedding service generates claim embeddings
   - NLI service provides entailment/contradiction labels
   - Vector search finds similar evidence

## Ethical Considerations

- All claims sourced from public fact-checking sites
- Sources properly attributed with URLs
- Evidence summarized, not verbatim copied
- Date of fact-check recorded for reproducibility
- No copyrighted content included

## Contributing New Claims

To add claims to the dataset:

1. **Source Selection**: Choose from established fact-checkers
2. **Verification**: Confirm claim has clear verdict
3. **Format**: Follow JSON structure exactly
4. **Evidence**: Extract 1-3 key evidence items per claim
5. **Validation**: Ensure all evidence IDs are referenced
6. **Testing**: Run `pytest tests/accuracy/ -v` to validate

Example addition:
```json
{
  "id": "rw_029",
  "text": "New claim text",
  "category": "science",
  "expected_verdict": "SUPPORTED",
  "confidence": 0.93,
  "source": "Snopes",
  "source_url": "https://www.snopes.com/...",
  "fact_checker_verdict": "TRUE",
  "fact_checker_reasoning": "Clear explanation",
  "date_checked": "2025-10-27",
  "evidence_ids": ["rw_ev_057", "rw_ev_058"]
}
```

## Troubleshooting

### Fixtures Not Found
- Ensure `real_world_claims.json` and `real_world_evidence.json` exist in `tests/accuracy/`
- Check file paths are correct

### Invalid JSON
- Validate JSON syntax with: `python -m json.tool real_world_claims.json`
- Check for missing commas, brackets, quotes

### Evidence References Invalid
- Run: `pytest tests/accuracy/test_accuracy_baseline.py::test_real_world_evidence_references -v`
- Check evidence IDs in claims match evidence file IDs

### Database Connection Required
- Baseline accuracy test requires active database
- Use `-m "not baseline"` to skip database-dependent tests
- Ensure TruthGraph services are initialized

## Performance Notes

- Fixture loading: ~100ms (session scope)
- Structure validation: ~10ms per test
- Baseline accuracy test: ~2-5 seconds per claim (depends on evidence corpus size)
- Total baseline run: ~2-3 minutes for 28 claims

## Future Enhancements

1. **Expanded Dataset**
   - Add 50-100 more real-world claims
   - Include more edge cases
   - Add multilingual claims

2. **Comparison Framework**
   - Automated version comparison
   - Performance trend analysis
   - Regression detection

3. **Category-Specific Testing**
   - Separate accuracy targets by category
   - Domain-specific benchmarks

4. **Evidence Corpus Integration**
   - Automatic corpus loading
   - Mock evidence for offline testing
   - Evidence similarity validation

## References

- Fact-checking sources:
  - <https://www.snopes.com>
  - <https://www.factcheck.org>
  - <https://www.politifact.com>
  - <https://www.reuters.com/fact-check>
  - <https://apnews.com/APFactCheck>
  - <https://fullfact.org>

- Related datasets:
  - FEVER dataset (Feature 1.2)
  - Test claims fixture (Feature 1.1)

## License

Real-world claims and evidence sourced from public fact-checking sources.
Test code is part of TruthGraph project.
