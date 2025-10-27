# Verdict Aggregation Service

## Overview

The **Verdict Aggregation Service** combines multiple Natural Language Inference (NLI) results into a single, final verdict for claim verification. It implements sophisticated aggregation strategies that handle conflicting evidence, confidence weighting, and provide human-readable explanations.

## Features

- **Multiple Aggregation Strategies**: Weighted vote, majority vote, confidence threshold, and strict consensus
- **Conflict Detection**: Automatically detects and flags contradictory evidence
- **Confidence Scoring**: Provides normalized confidence scores for final verdicts
- **Human-Readable Explanations**: Generates clear explanations for all decisions
- **High Performance**: <1ms aggregation time (357x faster than 10ms target)
- **Comprehensive Testing**: 54+ tests with 100% coverage

## Architecture

### Core Components

1. **VerdictAggregationService**: Main singleton service for aggregation
2. **VerdictResult**: Dataclass containing aggregated verdict and metadata
3. **VerdictLabel**: Enum for final verdict labels (SUPPORTED, REFUTED, UNCERTAIN)
4. **AggregationStrategy**: Enum for different aggregation strategies

### Label Mapping

The service maps NLI labels to verdict labels:

| NLI Label      | Verdict Label |
|----------------|---------------|
| ENTAILMENT     | SUPPORTED     |
| CONTRADICTION  | REFUTED       |
| NEUTRAL        | UNCERTAIN     |

## Aggregation Strategies

### 1. Weighted Vote (Default)

**Best for**: Most general-purpose scenarios with varying evidence quality

```python
from truthgraph.services.ml import (
    get_verdict_aggregation_service,
    AggregationStrategy,
)

service = get_verdict_aggregation_service()
verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.WEIGHTED_VOTE
)
```

**How it works**:
- Each NLI result contributes to the final score weighted by its confidence
- Scores are normalized across all labels
- The label with the highest weighted score wins
- Automatically filters low-confidence evidence (default threshold: 0.5)

**Example**:
```
Evidence 1: ENTAILMENT (confidence: 0.95)  → weight: 0.95
Evidence 2: ENTAILMENT (confidence: 0.85)  → weight: 0.85
Evidence 3: NEUTRAL (confidence: 0.60)     → weight: 0.60

Total weights:
- SUPPORTED: 1.80
- REFUTED: 0.00
- UNCERTAIN: 0.60

Normalized scores:
- SUPPORTED: 0.75 (75%)
- REFUTED: 0.00 (0%)
- UNCERTAIN: 0.25 (25%)

Verdict: SUPPORTED with 75% confidence
```

### 2. Majority Vote

**Best for**: When all evidence has similar reliability

```python
verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.MAJORITY_VOTE
)
```

**How it works**:
- Each NLI result gets one vote regardless of confidence
- The label with the most votes wins
- Confidence is the proportion of votes received

**Example**:
```
Evidence 1: ENTAILMENT (confidence: 0.55)  → 1 vote
Evidence 2: ENTAILMENT (confidence: 0.60)  → 1 vote
Evidence 3: CONTRADICTION (confidence: 0.95)  → 1 vote

Vote counts:
- SUPPORTED: 2 votes
- REFUTED: 1 vote
- UNCERTAIN: 0 votes

Verdict: SUPPORTED with 67% confidence (2/3 votes)
```

### 3. Confidence Threshold

**Best for**: Critical decisions requiring high-quality evidence

```python
verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.CONFIDENCE_THRESHOLD
)
```

**How it works**:
- Only considers evidence with confidence ≥ 0.75 (HIGH_CONFIDENCE_THRESHOLD)
- Applies weighted voting to high-confidence evidence only
- Falls back to weighted vote if no high-confidence evidence exists

**Example**:
```
Evidence 1: ENTAILMENT (confidence: 0.85)     → included
Evidence 2: ENTAILMENT (confidence: 0.65)     → excluded (too low)
Evidence 3: CONTRADICTION (confidence: 0.60)  → excluded (too low)

Only Evidence 1 is used → Verdict: SUPPORTED
```

### 4. Strict Consensus

**Best for**: When unanimous agreement is required

```python
verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.STRICT_CONSENSUS
)
```

**How it works**:
- All evidence must agree on the same label
- Any disagreement results in UNCERTAIN verdict
- Confidence is the average of all evidence confidences

**Example**:
```
Scenario 1 (Unanimous):
Evidence 1: ENTAILMENT (confidence: 0.90)
Evidence 2: ENTAILMENT (confidence: 0.85)
Evidence 3: ENTAILMENT (confidence: 0.92)
→ Verdict: SUPPORTED with 89% confidence (average)

Scenario 2 (Disagreement):
Evidence 1: ENTAILMENT (confidence: 0.90)
Evidence 2: CONTRADICTION (confidence: 0.85)
→ Verdict: UNCERTAIN with 0% confidence (conflict detected)
```

## Usage Examples

### Basic Usage

```python
from truthgraph.services.ml import (
    NLIResult,
    NLILabel,
    get_verdict_aggregation_service,
)

# Create NLI results (from NLI service)
nli_results = [
    NLIResult(
        label=NLILabel.ENTAILMENT,
        confidence=0.92,
        scores={"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03}
    ),
    NLIResult(
        label=NLILabel.ENTAILMENT,
        confidence=0.88,
        scores={"entailment": 0.88, "neutral": 0.08, "contradiction": 0.04}
    ),
]

# Aggregate results
service = get_verdict_aggregation_service()
verdict = service.aggregate(nli_results)

# Access results
print(f"Verdict: {verdict.verdict}")  # SUPPORTED
print(f"Confidence: {verdict.confidence:.2%}")  # 100.00%
print(f"Explanation: {verdict.explanation}")
print(f"Supporting: {verdict.supporting_count}")  # 2
print(f"Refuting: {verdict.refuting_count}")  # 0
print(f"Neutral: {verdict.neutral_count}")  # 0
print(f"Has Conflict: {verdict.has_conflict}")  # False
```

### Custom Confidence Threshold

```python
# Use custom minimum confidence threshold
verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.WEIGHTED_VOTE,
    min_confidence=0.7  # Override default 0.5
)
```

### Handling Conflicting Evidence

```python
# Mixed evidence that conflicts
conflicting_results = [
    NLIResult(
        label=NLILabel.ENTAILMENT,
        confidence=0.85,
        scores={"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05}
    ),
    NLIResult(
        label=NLILabel.CONTRADICTION,
        confidence=0.80,
        scores={"entailment": 0.05, "neutral": 0.15, "contradiction": 0.80}
    ),
]

verdict = service.aggregate(conflicting_results)

if verdict.has_conflict:
    print("WARNING: Conflicting evidence detected!")
    print(verdict.explanation)
    # Output: "WARNING: Conflicting evidence detected. Both supporting
    #          and refuting evidence exist with significant confidence."
```

### Real-World Claim Verification

```python
from truthgraph.services.ml import get_nli_service, get_verdict_aggregation_service

# Step 1: Get evidence (e.g., from vector search)
claim = "Climate change is caused by human activities"
evidence_texts = [
    "Scientific consensus shows human activities are primary driver...",
    "Carbon emissions from fossil fuels have increased...",
    "Research indicates natural factors play minor role...",
]

# Step 2: Run NLI on all evidence
nli_service = get_nli_service()
nli_results = []

for evidence in evidence_texts:
    result = nli_service.verify_single(
        premise=evidence,
        hypothesis=claim
    )
    nli_results.append(result)

# Step 3: Aggregate into final verdict
agg_service = get_verdict_aggregation_service()
verdict = agg_service.aggregate(nli_results)

# Step 4: Present results
print(f"Claim: {claim}")
print(f"Verdict: {verdict.verdict}")
print(f"Confidence: {verdict.confidence:.1%}")
print(f"Evidence analyzed: {verdict.evidence_count}")
print(f"Explanation: {verdict.explanation}")
```

## Configuration

### Thresholds

The service uses configurable thresholds for decision-making:

```python
class VerdictAggregationService:
    MIN_CONFIDENCE_THRESHOLD = 0.5      # Minimum confidence to count evidence
    HIGH_CONFIDENCE_THRESHOLD = 0.75    # High confidence threshold
    CONFLICT_THRESHOLD = 0.3            # Min score to flag conflict
    MIN_EVIDENCE_FOR_VERDICT = 1        # Minimum evidence needed
```

### Custom Thresholds

```python
# Override at runtime
verdict = service.aggregate(
    nli_results,
    min_confidence=0.65  # More strict than default 0.5
)

# Or modify class constants (not recommended for production)
VerdictAggregationService.MIN_CONFIDENCE_THRESHOLD = 0.6
```

## Explanation Generation

The service automatically generates human-readable explanations:

### Example Explanations

**High Confidence Support**:
```
Claim is SUPPORTED with 95.0% confidence. Analyzed 3 evidence items:
3 supporting, 0 refuting, 0 neutral. High confidence verdict -
strong evidence consensus.
```

**Conflicting Evidence**:
```
Claim is UNCERTAIN with 55.0% confidence. Analyzed 5 evidence items:
2 supporting, 2 refuting, 1 neutral. WARNING: Conflicting evidence
detected. Both supporting and refuting evidence exist with significant
confidence.
```

**Low Confidence**:
```
Claim is UNCERTAIN with 35.0% confidence. Analyzed 4 evidence items:
1 supporting, 0 refuting, 0 neutral. 3 items excluded due to low
confidence. Low confidence verdict - consider gathering more evidence.
```

## Performance

### Benchmarks

Performance results from `scripts/benchmark_verdict_aggregation.py`:

| Dataset Size | Mean Time | P95 Time | Status |
|--------------|-----------|----------|--------|
| 3 items      | 0.031 ms  | 0.039 ms | PASS   |
| 10 items     | 0.004 ms  | 0.005 ms | PASS   |
| 50 items     | 0.042 ms  | 0.048 ms | PASS   |
| 100 items    | 0.049 ms  | 0.059 ms | PASS   |
| 200 items    | 0.060 ms  | 0.072 ms | PASS   |

**Average Performance**: 0.028 ms (357x faster than 10ms target)

### Scalability

The service maintains excellent performance even with large evidence sets:

- **1-10 evidence items**: ~0.005 ms
- **10-50 evidence items**: ~0.04 ms
- **50-100 evidence items**: ~0.05 ms
- **100-200 evidence items**: ~0.06 ms

Performance scales linearly with evidence count at O(n) complexity.

## Testing

### Test Coverage

The implementation includes comprehensive testing:

- **38 unit tests** in `test_verdict_aggregation_service.py`
- **16 integration tests** in `test_verdict_aggregation_integration.py`
- **10 performance benchmarks** in `benchmark_verdict_aggregation.py`
- **Total**: 54+ tests covering all functionality

### Running Tests

```bash
# Run unit tests
pytest tests/services/ml/test_verdict_aggregation_service.py -v

# Run integration tests
pytest tests/services/ml/test_verdict_aggregation_integration.py -v

# Run performance benchmarks
python scripts/benchmark_verdict_aggregation.py
```

### Test Categories

1. **Basic Functionality**: Singleton, validation, error handling
2. **Weighted Vote**: Unanimous, mixed, conflicting, filtering
3. **Majority Vote**: Simple majority, tie-breaking
4. **Confidence Threshold**: High-confidence only, fallback
5. **Strict Consensus**: Unanimous agreement, disagreement
6. **Edge Cases**: Zero confidence, thresholds, large datasets
7. **Explanations**: Content validation, warnings, recommendations
8. **Integration**: Real-world scenarios, strategy comparisons, scalability

## Error Handling

### Common Errors

```python
# Empty results list
try:
    verdict = service.aggregate([])
except ValueError as e:
    print(e)  # "NLI results list cannot be empty"

# Invalid result type
try:
    verdict = service.aggregate([{"invalid": "data"}])
except ValueError as e:
    print(e)  # "Result at index 0 is not an NLIResult"

# Invalid confidence value
invalid_result = NLIResult(
    label=NLILabel.ENTAILMENT,
    confidence=1.5,  # Invalid - over 1.0
    scores={...}
)
try:
    verdict = service.aggregate([invalid_result])
except ValueError as e:
    print(e)  # "Result at index 0 has invalid confidence: 1.5"
```

## Best Practices

### 1. Choose the Right Strategy

- **Weighted Vote**: Default choice for most scenarios
- **Majority Vote**: When evidence quality is uniform
- **Confidence Threshold**: For critical decisions
- **Strict Consensus**: When unanimous agreement is required

### 2. Handle Conflicts

Always check for conflicts in production:

```python
verdict = service.aggregate(nli_results)

if verdict.has_conflict:
    # Log warning
    logger.warning(
        "Conflicting evidence detected",
        claim_id=claim_id,
        supporting=verdict.supporting_count,
        refuting=verdict.refuting_count
    )

    # Consider additional validation
    if verdict.confidence < 0.6:
        return "NEEDS_REVIEW"
```

### 3. Set Appropriate Thresholds

Adjust confidence thresholds based on your use case:

```python
# High-stakes decision (medical, legal)
verdict = service.aggregate(nli_results, min_confidence=0.8)

# General fact-checking
verdict = service.aggregate(nli_results, min_confidence=0.5)

# Exploratory analysis
verdict = service.aggregate(nli_results, min_confidence=0.3)
```

### 4. Monitor Evidence Quality

Track evidence quality metrics:

```python
verdict = service.aggregate(nli_results)

# Log metrics
logger.info(
    "verdict_generated",
    verdict=verdict.verdict,
    confidence=verdict.confidence,
    evidence_count=verdict.evidence_count,
    supporting_count=verdict.supporting_count,
    refuting_count=verdict.refuting_count,
    neutral_count=verdict.neutral_count,
    has_conflict=verdict.has_conflict,
)
```

### 5. Store Results

Store aggregation results in the database:

```python
from truthgraph.models import VerificationResult

# Create database record
verification = VerificationResult(
    claim_id=claim_id,
    verdict=verdict.verdict.value,
    confidence=verdict.confidence,
    support_score=verdict.support_score,
    refute_score=verdict.refute_score,
    neutral_score=verdict.neutral_score,
    evidence_count=verdict.evidence_count,
    supporting_evidence_count=verdict.supporting_count,
    refuting_evidence_count=verdict.refuting_count,
    neutral_evidence_count=verdict.neutral_count,
    reasoning=verdict.explanation,
    pipeline_version="1.0",
)
```

## Integration with TruthGraph Pipeline

The Verdict Aggregation Service is part of the complete verification pipeline:

```
1. User submits claim
2. Claim embedding generated → EmbeddingService
3. Similar evidence retrieved → VectorSearchService
4. Evidence verified against claim → NLIService (multiple pairs)
5. NLI results aggregated → VerdictAggregationService ← YOU ARE HERE
6. Final verdict stored → Database
7. Results returned to user
```

## API Reference

### `VerdictAggregationService`

```python
class VerdictAggregationService:
    """Service for aggregating NLI results into final verdicts."""

    def aggregate(
        self,
        nli_results: list[NLIResult],
        strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_VOTE,
        min_confidence: float | None = None,
    ) -> VerdictResult:
        """Aggregate multiple NLI results into a final verdict."""
```

### `VerdictResult`

```python
@dataclass
class VerdictResult:
    """Result of verdict aggregation."""
    verdict: VerdictLabel
    confidence: float
    support_score: float
    refute_score: float
    neutral_score: float
    evidence_count: int
    supporting_count: int
    refuting_count: int
    neutral_count: int
    has_conflict: bool
    explanation: str
    strategy_used: str
```

### `VerdictLabel`

```python
class VerdictLabel(str, Enum):
    """Final verdict labels."""
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    UNCERTAIN = "UNCERTAIN"
```

### `AggregationStrategy`

```python
class AggregationStrategy(str, Enum):
    """Aggregation strategies."""
    WEIGHTED_VOTE = "weighted_vote"
    MAJORITY_VOTE = "majority_vote"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    STRICT_CONSENSUS = "strict_consensus"
```

## Troubleshooting

### Issue: All evidence filtered out

**Symptom**: Verdict is UNCERTAIN with 0 confidence

**Cause**: All evidence below minimum confidence threshold

**Solution**: Lower threshold or gather more evidence
```python
verdict = service.aggregate(nli_results, min_confidence=0.3)
```

### Issue: Unexpected conflicts

**Symptom**: Frequent conflict warnings

**Cause**: Evidence sources may be contradictory or claim is controversial

**Solution**: Review evidence quality and consider manual review
```python
if verdict.has_conflict and verdict.confidence < 0.6:
    # Flag for human review
    mark_for_manual_review(claim_id)
```

### Issue: Low confidence verdicts

**Symptom**: Confidence consistently below 0.5

**Cause**: Weak or neutral evidence, or evidence quality issues

**Solution**: Improve evidence retrieval or NLI model
```python
# Check evidence quality
avg_nli_confidence = sum(r.confidence for r in nli_results) / len(nli_results)
if avg_nli_confidence < 0.6:
    logger.warning("Low quality evidence", avg_confidence=avg_nli_confidence)
```

## Future Enhancements

Potential improvements for future versions:

1. **Bayesian Aggregation**: Incorporate prior probabilities
2. **Source Reliability Weighting**: Weight by source trustworthiness
3. **Temporal Decay**: Weight recent evidence more heavily
4. **Multi-Label Support**: Handle nuanced verdicts
5. **Uncertainty Quantification**: Provide uncertainty bounds
6. **Explanation Customization**: Template-based explanations

## References

- NLI Service Documentation: `README_NLI.md`
- Database Schema: `truthgraph/models.py` (VerificationResult)
- Implementation Plan: `PHASE_2_IMPLEMENTATION_PLAN.md`

## License

Apache 2.0 - See LICENSE file for details.
