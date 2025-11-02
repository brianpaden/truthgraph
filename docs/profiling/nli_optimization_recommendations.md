# NLI Service Optimization Recommendations
## Actionable Implementation Guide

**Date**: October 31, 2025
**Feature ID**: 2.2
**Agent**: python-pro

---

## Overview

This document provides actionable, prioritized recommendations for optimizing the NLI service based on comprehensive profiling analysis. Each recommendation includes implementation details, expected impact, effort estimates, and testing strategies.

**Target Audience**: Developers implementing NLI optimizations
**Prerequisites**: Review `nli_optimization_analysis.md` for context

---

## Quick Reference

### Recommended Implementation Order

| Priority | Recommendation | Effort | Impact | Status |
|----------|---------------|--------|---------|--------|
| 1 | Adjust Default Batch Size | 5 min | +28% | Ready |
| 2 | Pre-truncate Inputs | 15 min | +10-20% | Ready |
| 3 | Implement Batch Accumulation | 30 min | Consistency | Ready |
| 4 | Add Performance Monitoring | 1 hour | Visibility | Recommended |
| 5 | GPU Acceleration | 2-4 hours | 2-5x | Optional |

**Combined Quick Wins (1-3)**: ~1 hour implementation, +30-50% improvement

---

## Priority 1: Immediate Optimizations (Quick Wins)

### Recommendation 1.1: Adjust Default Batch Size

**Priority**: CRITICAL
**Effort**: 5 minutes
**Expected Impact**: +28% throughput for default usage
**Risk**: None (backward compatible)

#### Current State

```python
# truthgraph/services/ml/nli_service.py, line 247
def verify_batch(
    self,
    pairs: list[tuple[str, str]],
    batch_size: int = 8,  # Current default
) -> list[NLIResult]:
```

**Current Performance**: 50.22 pairs/sec @ batch_size=8

#### Recommended Change

```python
# truthgraph/services/ml/nli_service.py, line 247
def verify_batch(
    self,
    pairs: list[tuple[str, str]],
    batch_size: int = 16,  # Optimized default
) -> list[NLIResult]:
```

**Expected Performance**: 64.74 pairs/sec @ batch_size=16

#### Implementation Steps

1. Open `truthgraph/services/ml/nli_service.py`
2. Locate line 247 (verify_batch method)
3. Change `batch_size: int = 8` to `batch_size: int = 16`
4. Update docstring to reflect new default
5. Commit change

#### Testing Strategy

```python
def test_default_batch_size_optimized():
    """Verify default batch size is optimized."""
    service = get_nli_service()

    # Create test pairs
    pairs = [("premise", "hypothesis") for _ in range(100)]

    # Measure with default (should use batch_size=16)
    import time
    start = time.perf_counter()
    results = service.verify_batch(pairs)  # No batch_size specified
    elapsed = time.perf_counter() - start

    throughput = len(pairs) / elapsed

    # Should achieve ~60+ pairs/sec with new default
    assert throughput > 60, f"Expected >60 pairs/sec, got {throughput:.2f}"
```

#### Rollback Plan

If issues arise:
1. Revert to `batch_size: int = 8`
2. No other changes needed (backward compatible)

---

### Recommendation 1.2: Pre-truncate Inputs

**Priority**: HIGH
**Effort**: 15 minutes
**Expected Impact**: +10-20% throughput, reduced memory variance
**Risk**: Low (preserves semantic content)

#### Current State

Inputs of arbitrary length are tokenized, leading to:
- Variable padding overhead
- Inconsistent batch processing time
- Wasted computation on padding tokens

**Profiling Evidence**:
- Test inputs: 18-66 characters (premise)
- Padding to 512 tokens (model max)
- Estimated 10-20% compute on padding

#### Recommended Implementation

Add input truncation before tokenization:

```python
# truthgraph/services/ml/nli_service.py

def _truncate_text(text: str, max_chars: int = 256) -> str:
    """Truncate text to maximum characters at word boundary.

    Args:
        text: Text to truncate
        max_chars: Maximum number of characters (default: 256)

    Returns:
        Truncated text at nearest word boundary
    """
    if len(text) <= max_chars:
        return text

    # Truncate at word boundary to preserve semantics
    truncated = text[:max_chars].rsplit(' ', 1)[0]
    return truncated if truncated else text[:max_chars]


def verify_single(self, premise: str, hypothesis: str) -> NLIResult:
    """Verify single premise-hypothesis pair using NLI.

    ...existing docstring...
    """
    if not premise or not premise.strip():
        raise ValueError("Premise cannot be empty")
    if not hypothesis or not hypothesis.strip():
        raise ValueError("Hypothesis cannot be empty")

    # NEW: Truncate inputs to consistent length
    premise = self._truncate_text(premise, max_chars=256)
    hypothesis = self._truncate_text(hypothesis, max_chars=256)

    # Ensure model is loaded
    self._load_model()

    # ...rest of method unchanged...


def verify_batch(
    self,
    pairs: list[tuple[str, str]],
    batch_size: int = 16,
) -> list[NLIResult]:
    """Verify multiple premise-hypothesis pairs in batches.

    ...existing docstring...
    """
    if not pairs:
        raise ValueError("Pairs list cannot be empty")

    # Validate all pairs
    for i, (premise, hypothesis) in enumerate(pairs):
        if not premise or not premise.strip():
            raise ValueError(f"Premise at index {i} cannot be empty")
        if not hypothesis or not hypothesis.strip():
            raise ValueError(f"Hypothesis at index {i} cannot be empty")

    # NEW: Truncate all inputs
    truncated_pairs = [
        (self._truncate_text(p, 256), self._truncate_text(h, 256))
        for p, h in pairs
    ]

    # Ensure model is loaded
    self._load_model()

    results: list[NLIResult] = []

    try:
        total_pairs = len(truncated_pairs)  # Changed from pairs
        logger.info(
            "nli_batch_inference_start",
            total_pairs=total_pairs,
            batch_size=batch_size,
        )

        # Process in batches
        for i in range(0, total_pairs, batch_size):
            batch_pairs = truncated_pairs[i : i + batch_size]  # Changed
            premises = [pair[0] for pair in batch_pairs]
            hypotheses = [pair[1] for pair in batch_pairs]

            # ...rest of method unchanged...
```

#### Testing Strategy

```python
def test_input_truncation():
    """Verify input truncation preserves semantics."""
    service = get_nli_service()

    # Long premise
    long_premise = "This is a very long premise. " * 20  # >500 chars
    hypothesis = "This is a hypothesis."

    # Should not error, should truncate
    result = service.verify_single(long_premise, hypothesis)

    assert result is not None
    assert isinstance(result, NLIResult)


def test_truncation_word_boundary():
    """Verify truncation happens at word boundaries."""
    from truthgraph.services.ml.nli_service import _truncate_text

    text = "The quick brown fox jumps over the lazy dog"
    truncated = _truncate_text(text, max_chars=20)

    # Should truncate at word boundary, not mid-word
    assert truncated.endswith((' ', 'quick', 'brown', 'fox'))
    assert len(truncated) <= 20
```

#### Configuration

Make truncation length configurable:

```python
class NLIService:
    """..."""

    # Class-level configuration
    _max_input_chars: ClassVar[int] = 256  # Configurable

    def _truncate_text(self, text: str, max_chars: int | None = None) -> str:
        """Truncate text using class default or override."""
        max_chars = max_chars or self._max_input_chars
        # ...rest of implementation...
```

---

### Recommendation 1.3: Implement Batch Accumulation

**Priority**: HIGH
**Effort**: 30 minutes
**Expected Impact**: Ensures consistent batch_size=16 usage
**Risk**: Low (adds latency buffer, but <100ms)

#### Problem Statement

Current implementation processes pairs immediately:
- API receives requests one at a time
- Each request processed individually (batch_size=1 performance)
- Batch processing benefits not realized

**Impact**:
- Real throughput: 15 pairs/sec (single-pair processing)
- Potential throughput: 64 pairs/sec (batch processing)
- **76% performance loss**

#### Recommended Implementation

Create batch accumulator for asynchronous request handling:

```python
# truthgraph/services/ml/nli_batch_accumulator.py

"""Batch accumulator for NLI service.

Collects incoming NLI requests and processes them in batches for optimal
throughput. Implements timeout-based flushing to balance throughput and latency.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import structlog

from truthgraph.services.ml.nli_service import NLIResult, get_nli_service

logger = structlog.get_logger(__name__)


@dataclass
class PendingRequest:
    """Represents a pending NLI request."""

    premise: str
    hypothesis: str
    future: asyncio.Future[NLIResult]
    timestamp: float


class NLIBatchAccumulator:
    """Accumulates NLI requests for batch processing.

    This class collects incoming requests and processes them in batches
    to maximize throughput while minimizing latency.

    Attributes:
        target_batch_size: Ideal batch size for processing (default: 16)
        max_wait_ms: Maximum wait time before flushing (default: 100ms)
        buffer: List of pending requests
    """

    def __init__(
        self,
        target_batch_size: int = 16,
        max_wait_ms: int = 100,
    ) -> None:
        """Initialize batch accumulator.

        Args:
            target_batch_size: Target batch size for optimal performance
            max_wait_ms: Maximum wait time in milliseconds before flush
        """
        self.target_batch_size = target_batch_size
        self.max_wait_ms = max_wait_ms
        self.buffer: list[PendingRequest] = []
        self.service = get_nli_service()
        self._flush_task: asyncio.Task[Any] | None = None
        self._lock = asyncio.Lock()

    async def verify(self, premise: str, hypothesis: str) -> NLIResult:
        """Verify a single premise-hypothesis pair with batching.

        Args:
            premise: The evidence or premise text
            hypothesis: The claim or hypothesis to verify

        Returns:
            NLIResult containing label, confidence, and scores
        """
        async with self._lock:
            # Create future for this request
            future: asyncio.Future[NLIResult] = asyncio.Future()

            # Add to buffer
            request = PendingRequest(
                premise=premise,
                hypothesis=hypothesis,
                future=future,
                timestamp=time.time(),
            )
            self.buffer.append(request)

            # Check if we should flush immediately
            if len(self.buffer) >= self.target_batch_size:
                await self._flush()
            elif self._flush_task is None:
                # Start timeout-based flush
                self._flush_task = asyncio.create_task(self._flush_on_timeout())

        # Wait for result
        return await future

    async def _flush_on_timeout(self) -> None:
        """Flush buffer after timeout."""
        await asyncio.sleep(self.max_wait_ms / 1000.0)

        async with self._lock:
            if self.buffer:  # Check if buffer still has items
                await self._flush()

    async def _flush(self) -> None:
        """Flush current buffer and process as batch."""
        if not self.buffer:
            return

        # Take current buffer
        requests = self.buffer
        self.buffer = []
        self._flush_task = None

        try:
            # Extract pairs
            pairs = [(req.premise, req.hypothesis) for req in requests]

            # Process batch
            results = self.service.verify_batch(
                pairs,
                batch_size=self.target_batch_size,
            )

            # Resolve futures
            for request, result in zip(requests, results):
                if not request.future.done():
                    request.future.set_result(result)

            logger.info(
                "batch_processed",
                batch_size=len(requests),
                target=self.target_batch_size,
            )

        except Exception as e:
            # Reject all pending futures
            for request in requests:
                if not request.future.done():
                    request.future.set_exception(e)

            logger.error(
                "batch_processing_failed",
                error=str(e),
                batch_size=len(requests),
            )


# Global instance for use across application
_accumulator: NLIBatchAccumulator | None = None


def get_nli_accumulator() -> NLIBatchAccumulator:
    """Get or create the global NLI batch accumulator.

    Returns:
        The singleton NLIBatchAccumulator instance
    """
    global _accumulator
    if _accumulator is None:
        _accumulator = NLIBatchAccumulator(
            target_batch_size=16,
            max_wait_ms=100,
        )
    return _accumulator
```

#### Usage Example

```python
# In your API endpoint or service
from truthgraph.services.ml.nli_batch_accumulator import get_nli_accumulator

async def verify_claim(premise: str, hypothesis: str) -> dict:
    """API endpoint for claim verification."""
    accumulator = get_nli_accumulator()

    # This will batch with other concurrent requests
    result = await accumulator.verify(premise, hypothesis)

    return {
        "label": result.label.value,
        "confidence": result.confidence,
        "scores": result.scores,
    }
```

#### Testing Strategy

```python
@pytest.mark.asyncio
async def test_batch_accumulation():
    """Verify batch accumulator batches requests."""
    accumulator = NLIBatchAccumulator(target_batch_size=4, max_wait_ms=100)

    # Send 4 concurrent requests
    tasks = [
        accumulator.verify(f"Premise {i}", f"Hypothesis {i}")
        for i in range(4)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 4
    assert all(isinstance(r, NLIResult) for r in results)


@pytest.mark.asyncio
async def test_timeout_flush():
    """Verify accumulator flushes on timeout."""
    accumulator = NLIBatchAccumulator(target_batch_size=10, max_wait_ms=50)

    # Send only 1 request (less than batch size)
    result = await accumulator.verify("Test premise", "Test hypothesis")

    # Should still get result (flushed on timeout)
    assert isinstance(result, NLIResult)
```

#### Configuration Tuning

Adjust parameters based on traffic patterns:

```python
# High-throughput, latency-tolerant
accumulator = NLIBatchAccumulator(
    target_batch_size=32,  # Larger batches
    max_wait_ms=200,  # Longer wait
)

# Low-latency, moderate-throughput
accumulator = NLIBatchAccumulator(
    target_batch_size=8,  # Smaller batches
    max_wait_ms=50,  # Shorter wait
)

# Balanced (recommended)
accumulator = NLIBatchAccumulator(
    target_batch_size=16,
    max_wait_ms=100,
)
```

---

## Priority 2: Short-Term Optimizations

### Recommendation 2.1: Add Performance Monitoring

**Priority**: HIGH
**Effort**: 1 hour
**Expected Impact**: Visibility into production performance
**Risk**: None

#### Implementation

Add structured logging for key metrics:

```python
# In NLIService.verify_batch()

import time

def verify_batch(
    self,
    pairs: list[tuple[str, str]],
    batch_size: int = 16,
) -> list[NLIResult]:
    """..."""

    start_time = time.perf_counter()

    # ...existing implementation...

    elapsed = time.perf_counter() - start_time
    throughput = len(pairs) / elapsed

    logger.info(
        "nli_batch_complete",
        batch_size=batch_size,
        num_pairs=len(pairs),
        elapsed_time_s=elapsed,
        throughput_pairs_per_sec=throughput,
        avg_confidence=sum(r.confidence for r in results) / len(results),
    )

    return results
```

#### Metrics to Collect

1. **Throughput**: pairs/sec
2. **Latency**: ms/pair (P50, P95, P99)
3. **Batch Size**: actual batch sizes used
4. **Memory**: delta per batch
5. **Accuracy**: if ground truth available

---

### Recommendation 2.2: Input Length Analysis

**Priority**: MEDIUM
**Effort**: 30 minutes
**Expected Impact**: Identify optimal truncation length
**Risk**: None (analysis only)

#### Implementation

Log input lengths to identify patterns:

```python
def verify_batch(self, pairs, batch_size=16):
    """..."""

    # Log input lengths
    premise_lengths = [len(p) for p, _ in pairs]
    hypothesis_lengths = [len(h) for _, h in pairs]

    logger.info(
        "nli_input_lengths",
        premise_avg=sum(premise_lengths) / len(premise_lengths),
        premise_max=max(premise_lengths),
        hypothesis_avg=sum(hypothesis_lengths) / len(hypothesis_lengths),
        hypothesis_max=max(hypothesis_lengths),
    )

    # Continue processing...
```

#### Analysis

After 1 week of production data:
1. Review length distributions
2. Adjust truncation threshold if needed
3. Identify outliers (very long inputs)

---

## Priority 3: Medium-Term Optimizations

### Recommendation 3.1: GPU Acceleration

**Priority**: MEDIUM (Optional)
**Effort**: 2-4 hours
**Expected Impact**: 2-5x throughput improvement
**Risk**: Low (fallback to CPU if GPU unavailable)

#### Current State

Model detects GPU but performance not benchmarked:

```python
@staticmethod
def _detect_device() -> str:
    """Detect available compute device (GPU/CPU/MPS)."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"
```

#### Recommended Implementation

1. **Profile GPU Performance**:

```python
# Run profiling on GPU-enabled machine
python scripts/profiling/profile_nli.py --batch-sizes 8,16,32,64,128
```

1. **Optimize Batch Size for GPU**:

GPU typically benefits from larger batches (32-64).

1. **Benchmark CPU vs GPU**:

```python
def benchmark_device(device: str, batch_size: int):
    """Benchmark NLI on specific device."""
    # Force device
    service = NLIService()
    service.device = device
    service._load_model()

    # Benchmark
    # ...
```

#### Expected Results

- CPU: 77 pairs/sec @ batch_size=32
- GPU (CUDA): 150-300 pairs/sec @ batch_size=64
- GPU (MPS/M1): 100-200 pairs/sec @ batch_size=32

#### When to Use GPU

**Use GPU if**:
- Throughput requirements >100 pairs/sec
- GPU available and idle
- Memory budget allows larger batches

**Stay on CPU if**:
- Current throughput (77 pairs/sec) is sufficient
- No GPU available
- GPU needed for other services

---

### Recommendation 3.2: Model Quantization

**Priority**: LOW (Optional)
**Effort**: 4-8 hours
**Expected Impact**: 50% memory reduction, 5-10% throughput reduction
**Risk**: Medium (potential accuracy impact)

#### Implementation

```python
import torch
from torch.quantization import quantize_dynamic

# After model loading in _load_model()
if self.device == "cpu":  # Quantization primarily for CPU
    self.model = quantize_dynamic(
        self.model,
        {torch.nn.Linear},
        dtype=torch.qint8
    )
    logger.info("model_quantized", dtype="int8")
```

#### Trade-offs

- **Memory**: 50% reduction (184M params → 92M effective)
- **Throughput**: 5-10% reduction (acceptable)
- **Accuracy**: <1% potential reduction (test carefully)

#### Testing

```python
def test_quantized_accuracy():
    """Verify quantization doesn't degrade accuracy."""
    # Benchmark accuracy before quantization
    original_accuracy = measure_accuracy(model)

    # Quantize
    model_quantized = quantize_dynamic(model, ...)

    # Benchmark accuracy after
    quantized_accuracy = measure_accuracy(model_quantized)

    # Should be within 1%
    assert abs(original_accuracy - quantized_accuracy) < 0.01
```

---

## Priority 4: Long-Term Optimizations

### Recommendation 4.1: ONNX Runtime

**Priority**: LOW (Future)
**Effort**: 8-16 hours
**Expected Impact**: 20-40% throughput improvement
**Risk**: Medium (conversion complexity)

#### Overview

Convert PyTorch model to ONNX for optimized inference.

#### Benefits

- Graph optimizations
- Better multi-threading
- Production-optimized runtime
- Cross-platform deployment

#### Implementation Steps

1. Export model to ONNX
2. Optimize ONNX graph
3. Integrate ONNX Runtime
4. Benchmark performance
5. Validate accuracy

#### When to Implement

- When throughput requirements exceed 150 pairs/sec
- For production-critical deployments
- If cross-platform support needed

---

## Implementation Roadmap

### Week 1: Quick Wins

**Days 1-2**:
- [ ] Implement Recommendation 1.1 (5 min)
- [ ] Implement Recommendation 1.2 (15 min)
- [ ] Test changes (30 min)
- [ ] Deploy to staging

**Days 3-5**:
- [ ] Implement Recommendation 1.3 (30 min)
- [ ] Implement Recommendation 2.1 (1 hour)
- [ ] Integration testing (2 hours)
- [ ] Deploy to staging

**Expected Impact**: +30-50% throughput improvement

### Week 2: Monitoring and Validation

**Days 1-7**:
- [ ] Monitor staging performance
- [ ] Collect metrics (Recommendation 2.2)
- [ ] Analyze traffic patterns
- [ ] Adjust configuration if needed
- [ ] Deploy to production

### Month 2-3: Medium-Term (Optional)

**If needed**:
- [ ] Evaluate GPU acceleration (Recommendation 3.1)
- [ ] Benchmark GPU performance
- [ ] Test model quantization (Recommendation 3.2)
- [ ] Deploy if beneficial

---

## Success Criteria

### Performance Targets

- [ ] Throughput >60 pairs/sec (current: 64.74 @ batch_size=16)
- [ ] Latency P95 <20 ms/pair (current: 15.45 ms)
- [ ] Memory usage <100 MB delta (current: 51.5 MB)
- [ ] Accuracy maintained (current: 0.69, ±1% acceptable)

### Production Readiness

- [ ] Batch accumulation implemented
- [ ] Input truncation implemented
- [ ] Performance monitoring active
- [ ] Alerts configured
- [ ] Documentation updated

### Validation

- [ ] All tests passing
- [ ] Load testing completed
- [ ] Staging validation successful
- [ ] Production metrics monitored

---

## Rollback Procedures

### If Performance Degrades

1. Check batch_size configuration
2. Verify input truncation is working
3. Check for memory pressure
4. Review error logs

### If Accuracy Degrades

1. Disable input truncation temporarily
2. Verify model version
3. Check test dataset
4. Review recent changes

### Emergency Rollback

```bash
# Revert all changes
git revert <commit-hash>

# Or revert specific files
git checkout HEAD~1 -- truthgraph/services/ml/nli_service.py

# Redeploy
./deploy.sh staging
```

---

## Appendix: Configuration Examples

### Production Configuration (Recommended)

```python
# config/nli_service.py

NLI_CONFIG = {
    "batch_size": 16,
    "max_input_chars": 256,
    "accumulator_batch_size": 16,
    "accumulator_max_wait_ms": 100,
    "device": "auto",  # auto-detect
}
```

### High-Throughput Configuration

```python
NLI_CONFIG = {
    "batch_size": 32,
    "max_input_chars": 256,
    "accumulator_batch_size": 32,
    "accumulator_max_wait_ms": 200,
    "device": "cuda",  # if available
}
```

### Low-Latency Configuration

```python
NLI_CONFIG = {
    "batch_size": 8,
    "max_input_chars": 256,
    "accumulator_batch_size": 8,
    "accumulator_max_wait_ms": 50,
    "device": "cpu",
}
```

---

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Author**: python-pro agent
**Related Documents**:
- `nli_optimization_analysis.md` - Detailed analysis
- `nli_profiling_guide.md` - Profiling tools usage
