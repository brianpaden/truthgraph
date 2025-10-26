# NLI Service Documentation

Natural Language Inference (NLI) verification service for TruthGraph v0.

## Overview

The NLI service determines the relationship between a premise (evidence) and a hypothesis (claim):
- **ENTAILMENT**: Evidence supports the claim
- **CONTRADICTION**: Evidence contradicts the claim
- **NEUTRAL**: Evidence is unrelated to the claim

## Quick Start

```python
from truthgraph.services.ml import get_nli_service

# Get service instance (loads model on first use)
service = get_nli_service()

# Verify single pair
result = service.verify_single(
    premise="Paris is the capital of France",
    hypothesis="Paris is in France"
)

print(result.label)        # NLILabel.ENTAILMENT
print(result.confidence)   # 0.95
print(result.scores)       # All three class scores
```

## API Reference

### get_nli_service()

Get the singleton NLI service instance.

**Returns**: `NLIService` instance

**Example**:
```python
service = get_nli_service()
```

### NLIService.verify_single(premise, hypothesis)

Verify a single premise-hypothesis pair.

**Parameters**:
- `premise` (str): Evidence text
- `hypothesis` (str): Claim text to verify

**Returns**: `NLIResult` with:
- `label`: NLILabel (ENTAILMENT, CONTRADICTION, or NEUTRAL)
- `confidence`: float (0.0-1.0)
- `scores`: dict with all three class probabilities

**Raises**:
- `ValueError`: If premise or hypothesis is empty
- `RuntimeError`: If model inference fails

**Example**:
```python
result = service.verify_single(
    premise="The Earth orbits the Sun",
    hypothesis="The Sun orbits the Earth"
)
assert result.label == NLILabel.CONTRADICTION
assert result.confidence > 0.8
```

### NLIService.verify_batch(pairs, batch_size=8)

Verify multiple premise-hypothesis pairs efficiently.

**Parameters**:
- `pairs`: list[tuple[str, str]] - List of (premise, hypothesis) tuples
- `batch_size`: int - Number of pairs per batch (default: 8)

**Returns**: list[NLIResult] in same order as input

**Raises**:
- `ValueError`: If pairs is empty or contains invalid pairs
- `RuntimeError`: If batch inference fails

**Example**:
```python
pairs = [
    ("Evidence 1", "Claim 1"),
    ("Evidence 2", "Claim 2"),
    ("Evidence 3", "Claim 3"),
]
results = service.verify_batch(pairs, batch_size=8)
```

### NLIService.get_model_info()

Get information about the loaded model.

**Returns**: dict with:
- `model_name`: str
- `device`: str (cuda/mps/cpu)
- `initialized`: bool

**Example**:
```python
info = service.get_model_info()
print(f"Using {info['device']}")
```

## Data Types

### NLILabel (Enum)

```python
class NLILabel(str, Enum):
    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"
```

### NLIResult (Dataclass)

```python
@dataclass
class NLIResult:
    label: NLILabel          # Predicted label
    confidence: float        # Confidence (0.0-1.0)
    scores: dict[str, float] # All class probabilities
```

## Performance Optimization

### Batch Size

- **CPU**: Use batch_size=8 (default)
- **GPU**: Increase to 16-32 for better throughput
- **Memory constrained**: Reduce to 4

```python
# GPU optimization
results = service.verify_batch(pairs, batch_size=32)
```

### Device Selection

The service auto-detects the best device:
1. CUDA (NVIDIA GPU)
2. MPS (Apple Silicon)
3. CPU (fallback)

To check device:
```python
info = service.get_model_info()
print(info['device'])  # cuda/mps/cpu
```

## Error Handling

### Input Validation

```python
try:
    result = service.verify_single("", "claim")
except ValueError as e:
    print(f"Invalid input: {e}")
```

### Inference Errors

```python
try:
    results = service.verify_batch(pairs)
except RuntimeError as e:
    print(f"Inference failed: {e}")
```

## Best Practices

### 1. Reuse Service Instance

```python
# Good - reuse instance
service = get_nli_service()
for evidence, claim in pairs:
    result = service.verify_single(evidence, claim)

# Bad - creates singleton but inefficient pattern
for evidence, claim in pairs:
    service = get_nli_service()  # Don't do this
    result = service.verify_single(evidence, claim)
```

### 2. Use Batch Processing

```python
# Good - efficient batch processing
pairs = [(e, c) for e, c in zip(evidence_list, claim_list)]
results = service.verify_batch(pairs, batch_size=8)

# Less efficient - single at a time
results = []
for evidence, claim in pairs:
    result = service.verify_single(evidence, claim)
    results.append(result)
```

### 3. Handle Long Texts

```python
# Texts are automatically truncated to 512 tokens
long_evidence = "..." * 1000  # Very long text
result = service.verify_single(long_evidence, claim)
# Works - automatically truncated
```

### 4. Use Confidence Scores

```python
result = service.verify_single(evidence, claim)

# Access all scores for threshold-based logic
if result.scores['entailment'] > 0.7:
    verdict = "SUPPORTED"
elif result.scores['contradiction'] > 0.7:
    verdict = "REFUTED"
else:
    verdict = "INSUFFICIENT"
```

## Model Information

- **Model**: cross-encoder/nli-deberta-v3-base
- **Size**: ~440MB
- **Max Length**: 512 tokens
- **Download**: First use only (cached afterward)
- **Label Mapping**: CONTRADICTION (0), ENTAILMENT (1), NEUTRAL (2)

## Performance Benchmarks

Run benchmarks:
```bash
python scripts/benchmark_nli.py
```

Expected performance (CPU):
- Throughput: 2.5-4.0 pairs/second
- Latency: 300-500ms per pair
- Memory: ~800MB-1.2GB

## Testing

### Unit Tests (Fast)
```bash
pytest tests/services/ml/test_nli_service.py -v -m "not integration"
```

### Integration Tests (Downloads Model)
```bash
pytest tests/services/ml/test_nli_integration.py -v
```

### Benchmark
```bash
python scripts/benchmark_nli.py --pairs 50 --batch-size 8
```

## Troubleshooting

### Model Download Fails

**Problem**: Network error during model download
**Solution**:
```bash
# Set Hugging Face cache directory
export HF_HOME=/path/to/cache
# Or download manually from huggingface.co
```

### Out of Memory

**Problem**: CUDA out of memory
**Solution**: Reduce batch size
```python
results = service.verify_batch(pairs, batch_size=4)
```

### Slow Performance

**Problem**: Inference is slow
**Solution**: Check device and use GPU if available
```python
info = service.get_model_info()
if info['device'] == 'cpu':
    print("Consider using GPU for better performance")
```

## Advanced Usage

### Custom Confidence Thresholds

```python
def classify_with_threshold(result, threshold=0.7):
    if result.confidence < threshold:
        return "UNCERTAIN"
    return result.label.value.upper()

result = service.verify_single(evidence, claim)
classification = classify_with_threshold(result, threshold=0.8)
```

### Filtering Results

```python
# Get only high-confidence entailments
results = service.verify_batch(pairs)
supported = [
    r for r in results
    if r.label == NLILabel.ENTAILMENT and r.confidence > 0.7
]
```

### Aggregating Multiple Evidence

```python
# Verify claim against multiple evidence pieces
claim = "Paris is in France"
evidence_list = [
    "Paris is the capital of France",
    "The Eiffel Tower is in Paris",
    "Paris is a major European city",
]

pairs = [(e, claim) for e in evidence_list]
results = service.verify_batch(pairs)

# Count labels
support_count = sum(1 for r in results if r.label == NLILabel.ENTAILMENT)
contradict_count = sum(1 for r in results if r.label == NLILabel.CONTRADICTION)

if support_count > contradict_count:
    verdict = "SUPPORTED"
elif contradict_count > support_count:
    verdict = "REFUTED"
else:
    verdict = "INSUFFICIENT"
```

## Integration Example

```python
from truthgraph.services.ml import get_nli_service, NLILabel

# Initialize service
nli_service = get_nli_service()

# Claim verification workflow
def verify_claim(claim_text, evidence_texts):
    """Verify claim against evidence."""

    # Create pairs
    pairs = [(evidence, claim_text) for evidence in evidence_texts]

    # Batch inference
    results = nli_service.verify_batch(pairs, batch_size=8)

    # Aggregate
    scores = {
        'support': sum(r.confidence for r in results if r.label == NLILabel.ENTAILMENT),
        'refute': sum(r.confidence for r in results if r.label == NLILabel.CONTRADICTION),
        'neutral': sum(r.confidence for r in results if r.label == NLILabel.NEUTRAL),
    }

    # Determine verdict
    if scores['support'] > scores['refute']:
        return 'SUPPORTED', scores['support'] / len(results)
    elif scores['refute'] > scores['support']:
        return 'REFUTED', scores['refute'] / len(results)
    else:
        return 'INSUFFICIENT', 0.5

# Example usage
claim = "Climate change is caused by human activities"
evidence = [
    "Scientists agree that greenhouse gases from human activities cause global warming",
    "The Earth's climate has warmed significantly since the industrial revolution",
]

verdict, confidence = verify_claim(claim, evidence)
print(f"Verdict: {verdict} (confidence: {confidence:.2f})")
```

## Support

For issues or questions:
1. Check this documentation
2. Review test files for examples
3. Run benchmarks to validate setup
4. Check model device and memory

## License

Part of TruthGraph v0 - Apache 2.0 License
