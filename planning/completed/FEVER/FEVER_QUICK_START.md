# FEVER Dataset Integration - Quick Start Guide

## What is FEVER?

FEVER (Fact Extraction and VERification) is a dataset of 180K factual claims with Wikipedia-based evidence. TruthGraph integrates a 25-claim sample for testing and benchmarking the verification pipeline.

## Ready-to-Use Fixtures

No download or processing needed! All fixtures are pre-configured in your test directory.

### Location
```text
tests/fixtures/fever/
├── fever_sample_claims.json      # 25 test claims
├── fever_sample_evidence.json     # 20 evidence items
├── fever_mapping.json             # Claim-to-verdict mapping
├── fever_stats.json               # Dataset statistics
└── README.md                      # Detailed documentation
```

## Using FEVER Fixtures in Tests

### Load All FEVER Claims
```python
def test_verification(fever_sample_claims):
    """Access all FEVER claims."""
    claims = fever_sample_claims['claims']
    assert len(claims) == 25

    for claim in claims:
        text = claim['text']
        expected_verdict = claim['expected_verdict']
        # Your test logic here
```

### Get Claims by Verdict
```python
def test_supported_claims(fever_supported_claims):
    """Test only SUPPORTED claims."""
    for claim in fever_supported_claims:
        assert claim['expected_verdict'] == 'SUPPORTED'

def test_refuted_claims(fever_refuted_claims):
    """Test only REFUTED claims."""
    for claim in fever_refuted_claims:
        assert claim['expected_verdict'] == 'REFUTED'

def test_insufficient_claims(fever_insufficient_claims):
    """Test only INSUFFICIENT claims."""
    for claim in fever_insufficient_claims:
        assert claim['expected_verdict'] == 'INSUFFICIENT'
```

### Get Specific Claim by ID
```python
def test_specific_claim(fever_claim_by_id):
    """Test a specific claim."""
    claim = fever_claim_by_id('fever_000001')
    assert claim['text'] == 'The Gadsden flag was named by Christopher Gadsden.'
    assert claim['expected_verdict'] == 'SUPPORTED'
```

### Get Claims with Evidence
```python
def test_with_evidence(fever_claims_with_evidence):
    """Test claims that have associated evidence."""
    for claim in fever_claims_with_evidence:
        assert len(claim['evidence_ids']) > 0

def test_without_evidence(fever_claims_without_evidence):
    """Test claims without evidence."""
    for claim in fever_claims_without_evidence:
        assert len(claim['evidence_ids']) == 0
```

### Get Evidence Items
```python
def test_evidence(fever_sample_evidence):
    """Access evidence corpus."""
    evidence = fever_sample_evidence['evidence']

    for ev in evidence:
        source = ev['source_reference']  # e.g., "Gadsden_flag (sentence 0)"
        source_type = ev['source_type']  # always "wikipedia"
        content = ev['content']
```

### Get Evidence by ID
```python
def test_specific_evidence(evidence_by_id):
    """Get specific evidence item."""
    evidence = fever_evidence_by_id('fever_000001_ev_000')
    assert evidence['source_type'] == 'wikipedia'
```

### Get Fixture Metadata
```python
def test_with_metadata(fever_fixture_metadata):
    """Access fixture statistics."""
    metadata = fever_fixture_metadata

    print(f"Total claims: {metadata['total_claims']}")
    print(f"Total evidence: {metadata['total_evidence']}")
    print(f"Verdict distribution: {metadata['verdict_distribution']}")
    # {SUPPORTED: 11, REFUTED: 7, INSUFFICIENT: 7}
```

## Quick Reference - All Available Fixtures

### Session Fixtures (Load once per test session)
- `fever_sample_claims` - All 25 claims with metadata
- `fever_sample_evidence` - All 20 evidence items
- `fever_mapping` - Claim-to-verdict mapping
- `fever_stats` - Processing statistics

### Factory Fixtures (Generate filtered results)
- `fever_claim_by_id(claim_id)` - Get specific claim
- `fever_claims_by_verdict(verdict)` - Filter by verdict

### Convenience Fixtures (Pre-filtered)
- `fever_supported_claims` - All SUPPORTED claims
- `fever_refuted_claims` - All REFUTED claims
- `fever_insufficient_claims` - All INSUFFICIENT claims
- `fever_claims_with_evidence` - Claims with evidence
- `fever_claims_without_evidence` - Claims without evidence

### Metadata Fixtures
- `fever_fixture_metadata` - Statistics and metadata
- `verify_fever_fixture_integrity()` - Integrity check

## Dataset Statistics

```text
Claims:
  Total:       25
  Supported:   11 (44%)
  Refuted:      7 (28%)
  Insufficient: 7 (28%)

Evidence:
  Total Items:  20
  With Evidence: 17 claims (68%)
  Without:       8 claims (32%)
```

## Claim Structure

```json
{
  "id": "fever_000001",
  "text": "The Gadsden flag was named by Christopher Gadsden.",
  "category": "fever_dataset",
  "expected_verdict": "SUPPORTED",
  "evidence_ids": ["fever_000001_ev_000"],
  "confidence": 0.9,
  "source": "FEVER_Dataset",
  "reference_id": 137334
}
```

## Evidence Structure

```json
{
  "id": "fever_000001_ev_000",
  "content": "Evidence from: Gadsden_flag (sentence 0)",
  "source_reference": "Gadsden_flag (sentence 0)",
  "source_type": "wikipedia",
  "claim_id": "fever_000001"
}
```

## Mapping Structure

```json
{
  "fever_000001": {
    "text": "The Gadsden flag was named by Christopher Gadsden.",
    "expected_verdict": "SUPPORTED",
    "evidence_ids": ["fever_000001_ev_000"],
    "reference_id": 137334
  }
}
```

## Common Test Patterns

### Pattern 1: Test All Verdicts
```python
def test_all_verdict_types(fever_supported_claims, fever_refuted_claims, fever_insufficient_claims):
    """Test that all verdict types work."""
    all_claims = (
        fever_supported_claims +
        fever_refuted_claims +
        fever_insufficient_claims
    )

    for claim in all_claims:
        result = verify_claim(claim['text'])
        assert result['verdict'] == claim['expected_verdict']
```

### Pattern 2: Benchmark with FEVER
```python
@pytest.mark.benchmark
def test_fever_throughput(benchmark, fever_sample_claims):
    """Benchmark verification speed."""
    def verify_all():
        for claim in fever_sample_claims['claims']:
            verify_claim(claim['text'])

    result = benchmark(verify_all)
    # Check performance against baseline
```

### Pattern 3: Test Evidence Integration
```python
def test_evidence_retrieval(fever_claims_with_evidence, fever_sample_evidence):
    """Test evidence retrieval."""
    evidence_map = {ev['id']: ev for ev in fever_sample_evidence['evidence']}

    for claim in fever_claims_with_evidence:
        for ev_id in claim['evidence_ids']:
            evidence = evidence_map[ev_id]
            assert evidence['source_type'] == 'wikipedia'
```

### Pattern 4: Test Schema Compliance
```python
def test_schema_compliance(fever_sample_claims, verify_fever_fixture_integrity):
    """Test FEVER fixture schema compliance."""
    result = verify_fever_fixture_integrity()

    assert result['is_valid'], f"Validation errors: {result['issues']}"
    assert result['claim_count'] == 25
    assert result['evidence_count'] == 20
```

## Running FEVER Tests

### Run All FEVER Fixture Tests
```bash
cd /c/repos/truthgraph
python -m pytest tests/fixtures/test_fever_fixtures.py -v
```

### Run Specific Test Category
```bash
# Test fixture loading
python -m pytest tests/fixtures/test_fever_fixtures.py::TestFEVERFixturesLoading -v

# Test data consistency
python -m pytest tests/fixtures/test_fever_fixtures.py::TestFEVERMappingConsistency -v

# Test factory fixtures
python -m pytest tests/fixtures/test_fever_fixtures.py::TestFEVERFactoryFixtures -v
```

### Run Tests with Your Own Tests
```bash
# Run FEVER tests + your tests
python -m pytest tests/fixtures/test_fever_fixtures.py tests/my_test.py -v

# Run only FEVER-marked tests
python -m pytest -m fever -v
```

## Extending FEVER Fixtures

### Create Larger Samples

Download full dataset:
```bash
python scripts/download_fever_dataset.py --dev-only --output-dir ./data/fever
```

Process larger sample:
```bash
python scripts/process_fever_data.py \
  --input ./data/fever/fever.dev.jsonl \
  --output-dir ./fever_processed_500 \
  --sample-size 500
```

Load into separate fixtures:
```bash
python scripts/load_fever_sample.py \
  --input-dir ./fever_processed_500 \
  --output-dir ./tests/fixtures/fever_large
```

### Add Real Wikipedia Content

Extend evidence with actual Wikipedia text:
```python
import wikipedia

# For each evidence item
for evidence in fever_sample_evidence['evidence']:
    source = evidence['source_reference']
    article, sentence_id = parse_reference(source)

    try:
        content = wikipedia.page(article).content
        # Extract specific sentence
        evidence['full_text'] = extract_sentence(content, sentence_id)
    except:
        pass
```

## Schema Mapping Reference

| FEVER Field | TruthGraph Field | Example |
|-------------|------------------|---------|
| claim | text | "The Gadsden flag was named by Christopher Gadsden." |
| label | expected_verdict | SUPPORTED, REFUTED, INSUFFICIENT |
| evidence | evidence_ids | ["fever_000001_ev_000"] |
| id | reference_id | 137334 |

## Troubleshooting

### Fixture Not Found
**Error**: `FEVER sample claims fixture file not found`
**Solution**: Ensure `/c/repos/truthgraph/tests/fixtures/fever/` directory and files exist

### Validation Fails
**Error**: `FEVER fixture integrity check failed`
**Solution**: Run validation test:
```bash
python -m pytest tests/fixtures/test_fever_fixtures.py::TestFEVERFixtureIntegrity -v
```

### Import Issues
**Error**: `No module named 'conftest'`
**Solution**: Make sure pytest can discover fixtures:
```bash
python -m pytest --fixtures | grep fever_
```

## Documentation

For detailed information, see:
- `/c/repos/truthgraph/tests/fixtures/fever/README.md` - Full documentation
- `/c/repos/truthgraph/FEVER_INTEGRATION_SUMMARY.md` - Implementation details

## Key Resources

- FEVER Website: <https://fever.ai/>
- FEVER GitHub: <https://github.com/facebookresearch/FEVER-evidence-retrieval>
- Paper: Thorne et al., "FEVER: a Large-scale Dataset for Fact Extraction and VERification"

## Next Steps

1. Use FEVER fixtures in your verification tests
2. Run benchmarks with the provided claims
3. Extend fixtures with real Wikipedia content (optional)
4. Integrate with your ML pipeline

Happy testing!
