# FEVER Dataset Integration for TruthGraph

This directory contains test fixtures derived from the FEVER (Fact Extraction and VERification) dataset, integrated for TruthGraph testing and benchmarking.

## Overview

FEVER is a large-scale dataset for fact extraction and verification that contains fact claims with Wikipedia-based evidence. The dataset has been adapted to TruthGraph's schema for comprehensive testing of the verification pipeline.

**Source**: <https://fever.ai/dataset/fever.html>
**Paper**: <https://arxiv.org/abs/1803.05355>
**License**: Creative Commons Attribution 4.0 International

## Files

### Core Fixtures

- **fever_sample_claims.json**: Collection of test claims converted to TruthGraph format
  - 25 sample claims (balanced across verdict types)
  - Organized by expected verdict (SUPPORTED, REFUTED, INSUFFICIENT)
  - Includes evidence references and reasoning

- **fever_sample_evidence.json**: Evidence corpus for the sample claims
  - Wikipedia-based evidence references
  - Evidence linked to specific claims
  - Source information and article titles

- **fever_mapping.json**: Claim-to-verdict mapping
  - Direct mapping of claim IDs to verdicts
  - Evidence ID associations
  - Evidence index with source details

- **fever_stats.json**: Processing statistics
  - Label distribution metrics
  - Evidence coverage statistics
  - Claim categorization

## Schema Mapping

The FEVER dataset has been mapped to TruthGraph schema as follows:

| FEVER Field | TruthGraph Field | Description |
|-------------|------------------|-------------|
| `id` | `reference_id` | Original FEVER claim ID |
| `claim` | `text` | The claim text |
| `label` | `expected_verdict` | Verdict (see mapping below) |
| `evidence` | `evidence_ids` + `evidence_references` | Wikipedia evidence references |
| N/A | `id` | Generated TruthGraph ID (fever_XXXXXX) |
| N/A | `category` | Always "fever_dataset" |
| N/A | `source` | Always "FEVER_Dataset" |

### Verdict Mapping

| FEVER Label | TruthGraph Verdict | Description |
|-------------|-------------------|-------------|
| SUPPORTS | SUPPORTED | Evidence strongly supports the claim |
| REFUTES | REFUTED | Evidence strongly refutes the claim |
| NOT ENOUGH INFO | INSUFFICIENT | Insufficient evidence to determine |

## Dataset Composition

### Sample Size

- **Total Claims**: 25
- **Supported Claims**: 9 (36%)
- **Refuted Claims**: 8 (32%)
- **Insufficient Claims**: 8 (32%)

### Evidence Coverage

- **Claims with Evidence**: 17 (68%)
- **Claims without Evidence**: 8 (32%)
- **Total Evidence Items**: 20
- **Average Evidence per Claim**: 0.8

### Topics Covered

The sample fixtures cover diverse topics including:

- **Science**: Climate, physics, astronomy, biology
- **History**: Historical figures, events, empires
- **Geography**: Natural landmarks, geographical facts
- **Technology**: Programming, internet history
- **Culture**: Literature, art, architecture

## Evidence Strategy

The FEVER dataset originally references specific Wikipedia sentences in the format:
```text
[annotation_id, evidence_id, article_title, sentence_id]
```

For the test fixtures, evidence is represented as:
- **Source Reference**: Article title and sentence ID (e.g., "Gadsden_flag (sentence 0)")
- **Source Type**: Always "wikipedia"
- **Content**: Descriptive evidence reference

This approach allows:
1. Testing with Wikipedia-based evidence references
2. Flexibility for future real Wikipedia content integration
3. Realistic verification pipeline testing

## Usage in Tests

### Loading Fixtures with Pytest

```python
@pytest.fixture
def fever_claims(fever_sample_claims):
    """Get FEVER sample claims fixture."""
    return fever_sample_claims

def test_verification_with_fever_data(fever_claims):
    """Test verification pipeline with FEVER data."""
    claim = fever_claims['claims'][0]
    assert claim['expected_verdict'] in ['SUPPORTED', 'REFUTED', 'INSUFFICIENT']
```

### Accessing Fixtures

The fixtures are made available through `conftest.py`:

```python
# In tests/fixtures/conftest.py
@pytest.fixture(scope="session")
def fever_sample_claims():
    """Load FEVER sample claims fixture."""
    ...

@pytest.fixture(scope="session")
def fever_sample_evidence():
    """Load FEVER sample evidence fixture."""
    ...

@pytest.fixture(scope="session")
def fever_mapping():
    """Load FEVER claim-to-verdict mapping."""
    ...
```

## Processing Pipeline

The fixtures were created using the FEVER processing pipeline:

### Step 1: Download Dataset

```bash
python scripts/download_fever_dataset.py --dev-only --output-dir ./data/fever
```

Downloads the FEVER dev set (~19K claims) to a local directory.

### Step 2: Process Data

```bash
python scripts/process_fever_data.py \
  --input ./data/fever/fever.dev.jsonl \
  --output-dir ./fever_processed \
  --sample-size 100 \
  --seed 42
```

Converts FEVER format to TruthGraph schema and creates balanced samples.

### Step 3: Load Fixtures

```bash
python scripts/load_fever_sample.py \
  --input-dir ./fever_processed \
  --output-dir ./tests/fixtures/fever \
  --validate
```

Validates and loads processed data into test fixtures.

## Verification Examples

### Example 1: Supported Claim

```json
{
  "id": "fever_000001",
  "text": "The Gadsden flag was named by Christopher Gadsden.",
  "expected_verdict": "SUPPORTED",
  "evidence_ids": ["fever_000001_ev_000"],
  "source": "FEVER_Dataset"
}
```

Evidence: Gadsden_flag Wikipedia article, sentence 0

### Example 2: Refuted Claim

```json
{
  "id": "fever_000002",
  "text": "Python is a programming language created by Tim Peters.",
  "expected_verdict": "REFUTED",
  "evidence_ids": ["fever_000002_ev_000"],
  "source": "FEVER_Dataset"
}
```

Evidence: Python_programming_language Wikipedia article, sentence 1

### Example 3: Insufficient Claim

```json
{
  "id": "fever_000003",
  "text": "The exact gravitational constant was first precisely measured in the 21st century.",
  "expected_verdict": "INSUFFICIENT",
  "evidence_ids": [],
  "source": "FEVER_Dataset"
}
```

No evidence references available.

## Testing Workflow

### Unit Tests

```python
def test_fever_claims_structure(fever_sample_claims):
    """Verify FEVER claims structure."""
    assert 'claims' in fever_sample_claims
    assert len(fever_sample_claims['claims']) > 0

    claim = fever_sample_claims['claims'][0]
    assert 'id' in claim
    assert 'text' in claim
    assert 'expected_verdict' in claim

def test_fever_verdict_distribution(fever_sample_claims):
    """Verify balanced verdict distribution."""
    claims = fever_sample_claims['claims']
    verdicts = [c['expected_verdict'] for c in claims]

    supported = verdicts.count('SUPPORTED')
    refuted = verdicts.count('REFUTED')
    insufficient = verdicts.count('INSUFFICIENT')

    # Check reasonable balance
    assert supported > 0
    assert refuted > 0
    assert insufficient > 0
```

### Integration Tests

```python
def test_verification_pipeline_with_fever(fever_sample_claims, verification_service):
    """Test verification pipeline with FEVER data."""
    claim = fever_sample_claims['claims'][0]

    result = verification_service.verify(claim['text'])

    assert result['verdict'] in ['SUPPORTED', 'REFUTED', 'INSUFFICIENT']
    assert 'confidence' in result
```

### Benchmark Tests

```python
def test_fever_benchmark_performance(fever_sample_claims, benchmark):
    """Benchmark verification performance with FEVER data."""

    def verify_claims():
        for claim in fever_sample_claims['claims']:
            verification_service.verify(claim['text'])

    result = benchmark(verify_claims)
    assert result.stats.median < 1000  # ms
```

## Statistics

### Label Distribution

- **SUPPORTED**: 9 claims (36%)
- **REFUTED**: 8 claims (32%)
- **INSUFFICIENT**: 8 claims (32%)

The distribution is intentionally balanced to test all verdict types equally.

### Statistics Evidence Coverage

- **With Evidence**: 17 claims (68%)
- **Without Evidence**: 8 claims (32%)

This reflects realistic fact verification scenarios where some claims lack sufficient evidence.

### Evidence Complexity

- **Single Evidence**: 15 claims
- **Multiple Evidence**: 2 claims (Supported claims often have multiple supporting sources)
- **No Evidence**: 8 claims

## Integration with Benchmarking

The FEVER fixtures can be used for comprehensive benchmarking:

```python
# Benchmark claim processing speed
@pytest.mark.benchmark
def test_fever_processing_throughput(benchmark, fever_sample_claims):
    """Benchmark processing throughput."""
    benchmark(process_claims, fever_sample_claims['claims'])

# Benchmark evidence retrieval
@pytest.mark.benchmark
def test_fever_evidence_retrieval(benchmark, fever_sample_evidence):
    """Benchmark evidence retrieval speed."""
    benchmark(retrieve_evidence, fever_sample_evidence['evidence'])
```

## Extending the Fixtures

To create larger datasets for more comprehensive testing:

```bash
# Create a 500-claim sample
python scripts/process_fever_data.py \
  --input ./data/fever/fever.dev.jsonl \
  --output-dir ./fever_processed_large \
  --sample-size 500 \
  --seed 42

# Load into separate fixtures
python scripts/load_fever_sample.py \
  --input-dir ./fever_processed_large \
  --output-dir ./tests/fixtures/fever_large
```

## References

### FEVER Dataset

- **Homepage**: <https://fever.ai/>
- **GitHub**: <https://github.com/facebookresearch/FEVER-evidence-retrieval>
- **Paper**: Thorne et al., "FEVER: a Large-scale Dataset for Fact Extraction and VERification"
- **Download**: <https://fever.ai/dataset/fever.html>

### Related Resources

- **Wikipedia API**: For real evidence retrieval
- **FEVER Leaderboard**: <https://fever.ai/leaderboard>
- **FEVER Evaluation Scripts**: <https://github.com/facebookresearch/FEVER-evidence-retrieval>

## Notes

- The sample fixtures contain 25 representative claims from the full FEVER dev set
- Evidence references are Wikipedia-based but simplified for testing
- Actual Wikipedia content retrieval can be implemented using the Wikipedia API
- The fixtures maintain the original FEVER verdict labels and evidence structure
- All data is publicly available under Creative Commons Attribution 4.0

## Maintenance

To update FEVER fixtures when needed:

1. Download the latest FEVER dataset
2. Run the processing pipeline with updated parameters
3. Validate the new fixtures
4. Update this README with new statistics

For questions or issues with FEVER fixtures, refer to:
- FEVER Dataset Documentation
- TruthGraph Testing Documentation
- Feature 1.2 Implementation Notes
