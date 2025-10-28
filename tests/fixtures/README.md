# Test Claims Dataset Fixtures

Comprehensive test fixtures with known verdicts to validate TruthGraph accuracy and behavior across diverse claim verification scenarios.

## Overview

This directory contains curated test data designed to support comprehensive testing of the TruthGraph verification pipeline. The fixtures include:

- **25 diverse test claims** across 6 categories
- **55 evidence items** with semantic relevance to claims
- **Verified verdicts** based on expert judgment and scientific consensus
- **Edge case scenarios** for challenging verification situations
- **Pytest fixtures** for easy integration with tests

## Directory Structure

```
tests/fixtures/
├── test_claims.json          # Main test claims dataset (25 claims)
├── sample_evidence.json       # Evidence corpus (55 evidence items)
├── conftest.py               # Pytest fixtures and loaders
└── README.md                 # This documentation
```

## File Descriptions

### test_claims.json

Contains 25 diverse test claims with comprehensive metadata:

```json
{
  "metadata": {
    "version": "1.0",
    "created_date": "2025-10-27",
    "total_claims": 25,
    "categories": ["science", "politics", "health", "history", "current_events", "technology"],
    "verdict_types": ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
  },
  "claims": [
    {
      "id": "test_001",
      "text": "The Earth's average surface temperature has increased by approximately 1.1°C since pre-industrial times",
      "category": "science",
      "expected_verdict": "SUPPORTED",
      "confidence": 0.95,
      "reasoning": "Multiple peer-reviewed studies and IPCC reports confirm climate warming",
      "evidence_ids": ["ev_001", "ev_002", "ev_003"],
      "edge_case": null,
      "source": "IPCC Report 2021"
    }
  ]
}
```

#### Claim Fields

- **id**: Unique identifier (test_001 to test_025)
- **text**: The claim text to be verified
- **category**: Domain category (science, politics, health, history, current_events, technology)
- **expected_verdict**: Ground truth verdict (SUPPORTED, REFUTED, INSUFFICIENT)
- **confidence**: Expert confidence in the verdict (0.0 to 1.0)
- **reasoning**: Explanation for the verdict
- **evidence_ids**: List of relevant evidence item IDs
- **edge_case**: Type of challenging scenario (or null if standard)
- **source**: Primary source for the claim

### sample_evidence.json

Contains 55 evidence items with semantic relevance to the test claims:

```json
{
  "metadata": {
    "version": "1.0",
    "created_date": "2025-10-27",
    "total_evidence_items": 55,
    "sources": ["scientific_papers", "historical_records", "official_records", "medical_studies", "news_archives", "technical_documentation", "government_agencies"]
  },
  "evidence": [
    {
      "id": "ev_001",
      "content": "Global average temperatures have risen approximately 1.1 degrees Celsius...",
      "source": "IPCC AR6 Report",
      "url": "https://www.ipcc.ch/",
      "relevance": "high",
      "type": "scientific",
      "nli_label": "entailment"
    }
  ]
}
```

#### Evidence Fields

- **id**: Unique identifier (ev_001 to ev_055)
- **content**: Evidence text/paragraph
- **source**: Source document/publication name
- **url**: URL to source (for reference)
- **relevance**: Relevance level (high, medium, low)
- **type**: Evidence type category (scientific, historical, medical, political, technical)
- **nli_label**: Natural Language Inference label (entailment, contradiction, neutral)

## Claims Distribution

### By Verdict Type

| Verdict | Count | Claims |
|---------|-------|--------|
| SUPPORTED | 13 | test_001, test_002, test_003, test_004, test_008, test_009, test_010, test_014, test_015, test_016, test_018, test_019, test_021 |
| REFUTED | 7 | test_005, test_006, test_007, test_011, test_013, test_020, test_022 |
| INSUFFICIENT | 5 | test_012, test_023, test_024, and others |

### By Category

| Category | Count | Coverage |
|----------|-------|----------|
| science | 8 | Climate, physics, astronomy, earth science |
| technology | 5 | AI, programming, internet, energy |
| health | 5 | Vaccines, medicine, misconceptions |
| history | 5 | Historical events, artifacts, discoveries |
| politics | 2 | Election results, leadership |
| current_events | 1 | Technology trends |

### By Edge Case Type

| Edge Case Type | Count | Purpose |
|----------------|-------|---------|
| insufficient_evidence | 5 | Test handling of ambiguous situations |
| contradictory_evidence | 4 | Test contradiction detection |
| ambiguous_evidence | 3 | Test nuanced interpretations |
| standard | 13 | Clear-cut verification scenarios |

## Test Coverage

### Supported Claims (13 examples)

Test cases where evidence strongly supports the claim:

- test_001: Climate warming (multiple confirming sources)
- test_002: Water boiling point (fundamental physics)
- test_003: Eiffel Tower completion date (historical fact)
- test_004: COVID-19 vaccine efficacy (clinical data)
- And 9 more...

### Refuted Claims (7 examples)

Test cases where evidence contradicts the claim:

- test_005: Moon landing conspiracy (contradicted by multiple evidence types)
- test_006: Vitamin C cures common cold (clinical contradictions)
- test_007: Brain usage myth (neuroscience contradiction)
- And 4 more...

### Insufficient Evidence Claims (5 examples)

Test cases with ambiguous or conflicting information:

- test_012: Internet invention attribution (depends on definition)
- test_023: Mars human exploration (future-dependent)
- test_024: Amazon oxygen production (conflicting estimates)
- And 2 more...

## Edge Case Scenarios

### Insufficient Evidence Scenarios

Claims where evidence is limited or conflicting:

- **test_012**: "The Internet was invented by Tim Berners-Lee"
  - Depends on definition (Internet vs. World Wide Web)
  - Multiple valid interpretations
  - Evidence: ev_026, ev_027

- **test_023**: "Mars has been visited by human astronauts"
  - Future-dependent claim as of 2025
  - Clear refutation status
  - Evidence: ev_050, ev_051

- **test_024**: "The Amazon rainforest produces 20% of the world's oxygen"
  - Expert estimates vary (6-9% vs. 20% claim)
  - Multiple methodologies yield different results
  - Evidence: ev_052, ev_053

### Contradictory Evidence Scenarios

Claims with conflicting evidence types:

- **test_020**: "Antibiotics can cure viral infections"
  - Medical fact contradicts common misconception
  - Evidence types: medical studies, WHO guidelines
  - Evidence: ev_044, ev_045

- **test_022**: "Vaccines contain microchips that track individuals"
  - Technological impossibility contradicts conspiracy theory
  - Evidence: vaccine science, fact-checking
  - Evidence: ev_048, ev_049

### Ambiguous Evidence Scenarios

Claims requiring nuanced interpretation:

- **test_012**: Ambiguous definition of "Internet"
  - Could refer to underlying infrastructure or services
  - Evidence supports both interpretations

- **test_025**: "AI can pass the Turing Test"
  - Depends on Turing Test definition and evaluator criteria
  - Modern systems achieve this with varying definitions

## Pytest Fixtures

The `conftest.py` provides comprehensive pytest fixtures for easy test data access:

### Session-Scoped Fixtures

```python
def test_something(test_claims, test_evidence):
    """Load all test data."""
    claims = test_claims["claims"]
    evidence = test_evidence["evidence"]
```

### Factory Fixtures

```python
def test_specific_claim(claim_by_id):
    """Get specific claim by ID."""
    claim = claim_by_id("test_001")
    assert claim["expected_verdict"] == "SUPPORTED"

def test_specific_evidence(evidence_by_id):
    """Get specific evidence by ID."""
    evidence = evidence_by_id("ev_001")
    assert evidence["nli_label"] == "entailment"
```

### Filtering Fixtures

```python
def test_supported_claims(claims_by_verdict):
    """Get claims by verdict type."""
    supported = claims_by_verdict("SUPPORTED")
    assert len(supported) == 13

def test_science_category(claims_by_category):
    """Get claims by category."""
    science = claims_by_category("science")
    assert len(science) == 8

def test_insufficient_evidence(claims_by_edge_case):
    """Get claims by edge case type."""
    insufficient = claims_by_edge_case("insufficient_evidence")
    assert len(insufficient) == 5
```

### Specialized Fixtures

```python
def test_high_confidence(high_confidence_claims):
    """Access high-confidence claims."""
    assert all(c["confidence"] > 0.90 for c in high_confidence_claims)

def test_nli_labels(evidence_by_nli_label):
    """Get evidence by NLI label."""
    entailments = evidence_by_nli_label("entailment")
    contradictions = evidence_by_nli_label("contradiction")
```

### Sample Fixtures

```python
def test_with_samples(sample_supported_claim, sample_refuted_claim, sample_insufficient_claim):
    """Use pre-selected sample claims."""
    assert sample_supported_claim["id"] == "test_001"
    assert sample_refuted_claim["id"] == "test_005"
```

### Metadata and Validation

```python
def test_fixture_stats(fixture_metadata):
    """Access fixture statistics."""
    stats = fixture_metadata()
    assert stats["total_claims"] == 25
    assert stats["total_evidence"] == 55

def test_fixture_integrity(verify_fixture_integrity):
    """Validate fixture integrity."""
    result = verify_fixture_integrity()
    assert result["is_valid"]
    assert len(result["issues"]) == 0
```

## Available Fixtures Reference

| Fixture Name | Type | Purpose |
|--------------|------|---------|
| `test_claims` | Session | Load all test claims |
| `test_evidence` | Session | Load all evidence items |
| `claim_by_id` | Function | Get claim by ID (factory) |
| `evidence_by_id` | Function | Get evidence by ID (factory) |
| `claims_by_verdict` | Function | Filter claims by verdict (factory) |
| `claims_by_category` | Function | Filter claims by category (factory) |
| `claims_by_edge_case` | Function | Filter claims by edge case (factory) |
| `high_confidence_claims` | Function | Get claims with confidence > 0.90 |
| `evidence_by_nli_label` | Function | Filter evidence by NLI label (factory) |
| `evidence_by_type` | Function | Filter evidence by source type (factory) |
| `fixture_metadata` | Function | Get fixture statistics |
| `verify_fixture_integrity` | Function | Validate fixture data integrity |
| `sample_supported_claim` | Function | Pre-selected test_001 claim |
| `sample_refuted_claim` | Function | Pre-selected test_005 claim |
| `sample_insufficient_claim` | Function | Pre-selected test_024 claim |
| `sample_high_confidence_evidence` | Function | Pre-selected ev_001 evidence |
| `sample_contradiction_evidence` | Function | Pre-selected ev_011 evidence |
| `sample_neutral_evidence` | Function | Pre-selected ev_026 evidence |

## Usage Examples

### Example 1: Test Verdict Accuracy

```python
def test_verdict_accuracy(claims_by_verdict):
    """Test that verdict classification is accurate."""
    supported_claims = claims_by_verdict("SUPPORTED")

    # Verify all supported claims have high confidence
    for claim in supported_claims:
        assert claim["confidence"] >= 0.80, f"Claim {claim['id']} has low confidence"
```

### Example 2: Test Evidence Relevance

```python
def test_evidence_relevance(claim_by_id, evidence_by_id):
    """Test that evidence is relevant to claims."""
    claim = claim_by_id("test_001")

    for ev_id in claim["evidence_ids"]:
        evidence = evidence_by_id(ev_id)
        assert evidence["relevance"] in ["high", "medium"], f"Evidence {ev_id} has low relevance"
```

### Example 3: Test Edge Cases

```python
def test_edge_case_handling(claims_by_edge_case):
    """Test handling of edge case scenarios."""
    insufficient = claims_by_edge_case("insufficient_evidence")
    contradictory = claims_by_edge_case("contradictory_evidence")

    assert len(insufficient) == 5
    assert len(contradictory) == 4

    # Verify insufficient evidence claims have moderate confidence
    for claim in insufficient:
        assert 0.5 <= claim["confidence"] <= 0.8
```

### Example 4: Test Verification Pipeline

```python
def test_verification_pipeline(test_claims, test_evidence):
    """Test full verification pipeline with fixtures."""
    for claim in test_claims["claims"]:
        # Run verification
        result = verify_claim(claim["text"])

        # Validate against expected verdict
        assert result["verdict"] == claim["expected_verdict"]
        assert result["confidence"] >= 0.6
```

### Example 5: Fixture Validation

```python
def test_fixtures_valid(verify_fixture_integrity):
    """Ensure all fixtures are valid."""
    validation = verify_fixture_integrity()

    assert validation["is_valid"], f"Fixture issues: {validation['issues']}"
    assert validation["claim_count"] == 25
    assert validation["evidence_count"] == 55
```

## Quality Metrics

### Fixture Statistics

- **Total Claims**: 25
- **Total Evidence Items**: 55
- **Average Claims per Category**: 4.2
- **Average Evidence per Claim**: 2.2
- **Average Verdict Confidence**: 0.88
- **High Confidence Claims** (>0.90): 19/25 (76%)

### Coverage Analysis

- **Verdict Type Coverage**: All 3 types (SUPPORTED, REFUTED, INSUFFICIENT)
- **Category Coverage**: All 6 categories represented
- **Edge Case Coverage**: 12/25 claims (48%) are edge cases
- **NLI Label Coverage**: All 3 labels (entailment, contradiction, neutral)
- **Evidence Type Coverage**: 7 different source types

## Maintenance and Updates

### How to Add New Claims

1. Add claim object to `test_claims.json` with unique ID
2. Add related evidence items to `sample_evidence.json`
3. Update claim's `evidence_ids` array to reference new evidence
4. Ensure all required fields are populated
5. Run fixture validation tests
6. Update this README with new statistics

### Data Validation

Before committing fixture changes:

```python
from tests.fixtures.conftest import *

def test_fixtures():
    # Validate fixture integrity
    validation = verify_fixture_integrity()
    assert validation["is_valid"]
```

### Version Management

- Version tracked in metadata: `1.0`
- Update version when making breaking changes
- Maintain backward compatibility with existing tests

## References and Sources

Test data sourced from:

- **Scientific Claims**: IPCC reports, NASA, peer-reviewed journals
- **Historical Claims**: Wikipedia, National Archives, historical records
- **Medical Claims**: CDC, WHO, clinical trial databases
- **Technology Claims**: Official documentation, research papers
- **Political Claims**: Electoral records, government archives

## Integration Notes

### With Verification Pipeline

These fixtures integrate with `truthgraph/services/verification_pipeline_service.py`:

1. Claims can be directly passed to verification pipeline
2. Expected verdicts serve as ground truth for accuracy metrics
3. Evidence items can be used for retrieval evaluation
4. Confidence scores validate model calibration

### With Database Tests

When testing with actual database:

```python
def test_with_database(db_session, test_claims, test_evidence):
    """Create database records from fixtures."""
    for claim in test_claims["claims"]:
        # Create database Claim object
        db_claim = Claim(text=claim["text"])
        db_session.add(db_claim)

    db_session.commit()
```

## Testing Best Practices

1. **Use Specific Fixtures**: Select appropriate fixture for your test
2. **Validate Before Use**: Use `verify_fixture_integrity()` in setup
3. **Document Expectations**: Explain why specific claims are expected
4. **Test Edge Cases**: Prioritize edge case claims for robustness
5. **Maintain Fixture Purity**: Don't modify fixtures in tests
6. **Use Categories**: Group tests by claim category or verdict type

## Support and Questions

For questions about fixtures or to report issues:

1. Check fixture metadata: `fixture_metadata()`
2. Validate integrity: `verify_fixture_integrity()`
3. Review this README for usage patterns
4. Check claim reasoning field for verification logic

## License and Attribution

Test fixtures created for TruthGraph v0 Phase 2 testing.

Data sourced from public fact-checking datasets and verified sources.

All claims and evidence are documented with source attribution.
