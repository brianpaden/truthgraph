# Documentation Handoff

**Features**: 5.1-5.4
**Agent**: dx-optimizer
**Total Effort**: 34 hours
**Status**: Planned (can start in parallel with other work)
**Priority**: Medium (required for v0 release)

---

## Quick Navigation

**Master Index**: [v0_phase2_completion_handoff_MASTER.md](./v0_phase2_completion_handoff_MASTER.md)
**Quick Start**: [v0_phase2_quick_start.md](./v0_phase2_quick_start.md)
**Dependencies**: [dependencies_and_timeline.md](./dependencies_and_timeline.md)

**Related Handoffs**:
- [4_api_completion_handoff.md](./4_api_completion_handoff.md) (API to document)
- [2_performance_optimization_handoff.md](./2_performance_optimization_handoff.md) (performance guide)

---

## Category Overview

Documentation polish improves developer experience and makes the system usable. All 4 features can run in parallel with dependencies noted below.

### Execution Order

**Can start immediately**:
- Feature 5.1: Code Docstrings (10h) - Independent
- Feature 5.2: Troubleshooting Guide (8h) - Based on testing knowledge
- Feature 5.3: Usage Examples (10h) - Based on core functionality

**Start after optimization complete**:
- Feature 5.4: Performance & Optimization Guide (6h) - Depends on performance data

---

## Feature 5.1: Code Docstring Completion

**Status**: 📋 Planned
**Assigned To**: dx-optimizer
**Estimated Effort**: 10 hours
**Complexity**: Medium
**Blocker Status**: No blockers

### Description

Add comprehensive docstrings to all public functions and classes.

### Requirements

- Google-style docstrings
- Description of purpose
- Args documentation
- Returns documentation
- Raises documentation
- Examples where appropriate
- 100% coverage of public APIs

### Architecture

```text
truthgraph/
├── ml/
│   ├── embeddings.py       # With complete docstrings
│   ├── verification.py     # With complete docstrings
│   └── __init__.py         # With module docstring
├── retrieval/
│   ├── vector_search.py    # With complete docstrings
│   ├── hybrid_search.py    # With complete docstrings
│   └── __init__.py         # With module docstring
├── verification/
│   ├── aggregation.py      # With complete docstrings
│   ├── pipeline.py         # With complete docstrings
│   └── __init__.py         # With module docstring
└── ... (other modules)
```

### Docstring Template

**Module Level**

```python
"""Embedding service for text-to-vector conversion.

This module provides the EmbeddingService class for converting text inputs
to semantic vectors using pre-trained Sentence Transformers models.

Key Features:
  - Batch processing for efficiency
  - Configurable model selection
  - Caching for repeated embeddings
  - Error handling and fallbacks

Example:
  >>> from truthgraph.ml.embeddings import EmbeddingService
  >>> service = EmbeddingService()
  >>> embeddings = service.embed(["Hello world", "Test"])
  >>> embeddings.shape
  (2, 384)
"""
```

**Class Level**

```python
class EmbeddingService:
    """Service for generating embeddings from text.

    Wraps Sentence Transformers model for efficient batch embedding generation.
    Supports multiple model architectures and includes caching for performance.

    Attributes:
        model_name: Name of the Sentence Transformers model to use
        batch_size: Number of texts to process in each batch
        cache_size: Maximum number of cached embeddings

    Example:
        >>> service = EmbeddingService(model_name="all-MiniLM-L6-v2")
        >>> embeddings = service.embed(["Hello", "World"])
        >>> embeddings.shape
        (2, 384)
    """
```

**Function Level**

```python
def embed(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
    """Generate embeddings for a list of texts.

    Converts text inputs to semantic vector representations using the
    configured Sentence Transformers model. Supports batch processing for
    efficiency and caching for repeated inputs.

    Args:
        texts: List of text strings to embed
        batch_size: Override default batch size for this call

    Returns:
        numpy array of shape (len(texts), embedding_dim) containing vectors

    Raises:
        ValueError: If texts is empty or batch_size is invalid
        RuntimeError: If model fails to load or inference fails

    Example:
        >>> service = EmbeddingService()
        >>> texts = ["The Earth is round", "Water boils at 100C"]
        >>> embeddings = service.embed(texts)
        >>> embeddings.shape
        (2, 384)
        >>> # Use embeddings for similarity search, etc.
    """
```

### Implementation Steps

1. Audit all public functions/classes
2. Create docstring template
3. Add module-level docstrings
4. Add class docstrings
5. Add function/method docstrings
6. Add example code where helpful
7. Document exceptions
8. Use type hints in docstrings
9. Generate documentation
10. Validate with documentation generator

### Success Criteria

- 100% of public APIs documented
- Docstrings follow Google style
- Examples provided where useful
- Documentation builds successfully
- No warnings in doc generation
- All type hints included

### Documentation Generation

```bash
# Install dependencies
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# Generate docs
sphinx-build -b html docs docs/_build

# Check coverage
sphinx-coverage truthgraph/
```

### Docstring Validation

```python
def test_all_public_functions_have_docstrings():
    """Verify all public functions have docstrings."""
    from truthgraph import ml, retrieval, verification, api

    modules = [ml, retrieval, verification, api]

    for module in modules:
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith('_'):
                assert obj.__doc__, f"{name} missing docstring"

def test_docstring_quality():
    """Verify docstring quality."""
    from truthgraph.ml.embeddings import EmbeddingService

    service = EmbeddingService
    docstring = inspect.getdoc(service)

    # Check for key sections
    assert "Args:" in docstring or "Attributes:" in docstring
    assert "Returns:" in docstring or "Example:" in docstring
```

---

## Feature 5.2: Troubleshooting & FAQ Guide

**Status**: 📋 Planned
**Assigned To**: dx-optimizer
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: No blockers

### Description

Create comprehensive troubleshooting guides and FAQ for common issues.

### Requirements

- Common error messages and solutions
- Performance troubleshooting
- Model loading issues
- Database connection issues
- Memory issues
- Integration issues
- Deployment issues

### Architecture

```text
docs/guides/
├── troubleshooting.md       # Main guide
├── faq.md                   # FAQ document
└── troubleshooting/
    ├── models.md            # Model loading issues
    ├── performance.md       # Performance issues
    ├── database.md          # Database issues
    ├── memory.md            # Memory issues
    ├── integration.md       # Integration issues
    └── deployment.md        # Deployment issues
```

### Documentation Structure

**Main troubleshooting.md** (150 lines)

```markdown
# Troubleshooting Guide

## Quick Reference

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| "Model not found" | Missing model files | Run `python -m truthgraph download-models` |
| "Database connection refused" | Database not running | Start PostgreSQL: `pg_ctl start` |
| "Out of memory" | Batch size too large | Reduce batch_size in config |

## Decision Tree

```
Error in TruthGraph?
├─ During startup?
│  ├─ Can't load models? → See [Model Issues](./troubleshooting/models.md)
│  └─ Can't connect to DB? → See [Database Issues](./troubleshooting/database.md)
├─ During inference?
│  ├─ Too slow? → See [Performance Issues](./troubleshooting/performance.md)
│  └─ Out of memory? → See [Memory Issues](./troubleshooting/memory.md)
└─ During integration?
   └─ Can't call API? → See [Integration Issues](./troubleshooting/integration.md)
```
```

**Model Loading Issues** (50 lines)

```markdown
# Model Loading Issues

## Problem: "Model not found"

**Error Message:**
```
RuntimeError: Model 'all-MiniLM-L6-v2' not found
```

**Causes:**
- Sentence Transformers cache is empty
- Network issue preventing download
- Insufficient disk space

**Solutions:**

1. **Manual download:**
   ```bash
   python -m truthgraph download-models
   ```

1. **Specify model location:**
   ```python
   service = EmbeddingService(
       model_name="all-MiniLM-L6-v2",
       model_cache_dir="/path/to/cache"
   )
   ```

2. **Check disk space:**
   ```bash
   df -h  # Should have >1GB free
   ```
```

### FAQ Content

```markdown
# Frequently Asked Questions

## General

**Q: What's the minimum hardware needed?**
A: A CPU with 4GB RAM. GPU optional but recommended for throughput >500 texts/sec.

**Q: How accurate is the system?**
A: >70% accuracy on diverse test claims. Varies by claim category (science 81%, politics 73%).

**Q: Can I use custom models?**
A: Yes, see [Custom Models Guide](../guides/custom-models.md).

## Performance

**Q: Why is verification taking >60 seconds?**
A: Check [Performance Troubleshooting](./troubleshooting/performance.md). Common causes:
- Large corpus (>100K docs) - reduce with semantic filtering
- Network latency - check database connection
- Slow embedding model - switch to faster model

**Q: How do I improve throughput?**
A: See [Performance Optimization Guide](../performance/optimization-guide.md).

## Deployment

**Q: How do I deploy to production?**
A: See [Deployment Guide](../deployment/README.md).

**Q: Can I scale to multiple servers?**
A: Yes, see [Scaling Guide](../deployment/scaling.md).
```

### Success Criteria

- 20+ common issues documented
- Solutions tested
- FAQ complete
- Decision trees created
- Documentation clear
- Examples included

---

## Feature 5.3: Usage Examples & Tutorials

**Status**: 📋 Planned
**Assigned To**: dx-optimizer
**Estimated Effort**: 10 hours
**Complexity**: Medium
**Blocker Status**: No blockers

### Description

Create usage examples and tutorials for developers.

### Requirements

- Basic usage examples
- Integration tutorials
- Advanced use cases
- Performance optimization guides
- Custom model examples
- Deployment walkthroughs

### Architecture

```text
docs/guides/tutorials/
├── getting_started.md       # Basic setup
├── basic_usage.md           # Simple examples
├── integration.md           # Integration examples
├── advanced_usage.md        # Advanced patterns
├── custom_models.md         # Custom model setup
├── performance.md           # Performance tuning
├── deployment.md            # Deployment guide
└── examples/
    ├── simple_verification.py
    ├── batch_verification.py
    ├── custom_models.py
    ├── api_integration.py
    └── performance_tuning.py
```

### Example: Basic Usage

**docs/guides/tutorials/basic_usage.md**

```markdown
# Basic Usage Guide

## Install TruthGraph

```bash
pip install truthgraph
```

## Verify a Single Claim

```python
from truthgraph import TruthGraph

# Initialize
tg = TruthGraph()

# Verify a claim
result = tg.verify("The Earth is round")

print(f"Verdict: {result['verdict']}")
print(f"Confidence: {result['confidence']}")
print(f"Evidence: {result['evidence'][0]['text']}")
```

## Verify Multiple Claims

```python
claims = [
    "The Earth is round",
    "Water boils at 100C",
    "Gravity doesn't exist"
]

results = tg.verify_batch(claims)

for claim, result in zip(claims, results):
    print(f"{claim}: {result['verdict']} ({result['confidence']:.0%})")
```

## Advanced Options

```python
result = tg.verify(
    "The Earth is round",
    options={
        "max_evidence_items": 5,
        "confidence_threshold": 0.7,
        "return_reasoning": True
    }
)
```
```

### Example: Integration

**docs/guides/tutorials/api_integration.py**

```python
"""Example: Integration with TruthGraph API."""

import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Trigger verification
        response = await client.post(
            "http://localhost:8000/api/v1/claims/claim_123/verify",
            json={
                "claim_text": "The Earth is round",
                "options": {"max_evidence_items": 5}
            }
        )
        task_id = response.json()["task_id"]
        print(f"Task queued: {task_id}")

        # Poll for result
        for attempt in range(60):  # 60 second timeout
            result = await client.get(
                f"http://localhost:8000/api/v1/verdicts/claim_123"
            )
            if "verdict" in result.json():
                print(f"Result: {result.json()}")
                return

            await asyncio.sleep(1)

        print("Timeout waiting for result")

asyncio.run(main())
```

### Example: Performance Tuning

**docs/guides/tutorials/performance_tuning.py**

```python
"""Example: Performance tuning for batch processing."""

from truthgraph import TruthGraph

# Create service with optimized settings
tg = TruthGraph(
    embedding_batch_size=64,      # Larger batch for throughput
    nli_batch_size=16,
    max_workers=4                 # Parallel processing
)

# Process 1000 claims efficiently
claims = [f"Claim {i}" for i in range(1000)]
results = tg.verify_batch(
    claims,
    batch_size=64,
    show_progress=True
)

# Analyze results
correct = sum(1 for r in results if r['confidence'] > 0.7)
print(f"High confidence: {correct}/{len(results)}")
```

### Success Criteria

- 6+ example scripts provided
- All examples tested and working
- Tutorials comprehensive
- Deployment guide complete
- Examples executable
- Clear instructions

---

## Feature 5.4: Performance & Optimization Guide

**Status**: 📋 Planned
**Assigned To**: dx-optimizer
**Estimated Effort**: 6 hours
**Complexity**: Small
**Blocker Status**: Depends on Feature 2.x completion

### Description

Create comprehensive guide for performance optimization and tuning.

### Requirements

- Batch size recommendations
- Model selection guide
- Database optimization
- Caching strategies
- Deployment optimization
- Resource allocation
- Monitoring recommendations

### Architecture

```text
docs/performance/
├── optimization_guide.md    # Main guide
├── batch_size_tuning.md    # Batch size guide
├── model_selection.md      # Model selection
├── database_optimization.md
├── caching_strategies.md   # Caching guide
├── deployment_optimization.md
├── monitoring.md           # Monitoring guide
└── benchmarks/
    ├── embedding_benchmarks.md
    ├── nli_benchmarks.md
    ├── search_benchmarks.md
    └── pipeline_benchmarks.md
```

### Content: Batch Size Tuning

**docs/performance/batch_size_tuning.md**

```markdown
# Batch Size Tuning Guide

## Embedding Batch Sizes

### CPU Optimization

| Batch Size | Throughput | Memory | Notes |
|-----------|-----------|--------|-------|
| 1 | 50 texts/sec | 50MB | Too slow for production |
| 8 | 150 texts/sec | 200MB | Good balance |
| 16 | 250 texts/sec | 350MB | Recommended for CPU |
| 32 | 350 texts/sec | 600MB | Higher memory cost |
| 64 | 400 texts/sec | 1GB | Diminishing returns |

### GPU Optimization

| Batch Size | Throughput | Memory | Notes |
|-----------|-----------|--------|-------|
| 16 | 500 texts/sec | 2GB | Good starting point |
| 32 | 1000 texts/sec | 3GB | Recommended for GPU |
| 64 | 1500 texts/sec | 5GB | High throughput |

### How to Set

```python
service = EmbeddingService(
    batch_size=32  # Tune based on your hardware
)

# Or override per call
embeddings = service.embed(texts, batch_size=64)
```

### Tuning Steps

1. Start with recommended batch size
2. Measure throughput
3. Increase batch size while monitoring memory
4. Stop when memory approaches limit
5. Use optimal batch size
```

### Content: Model Selection

**docs/performance/model_selection.md**

```markdown
# Model Selection Guide

## Embedding Models

### Recommended Models

| Model | Speed | Quality | Memory | Recommended For |
|-------|-------|---------|--------|-----------------|
| all-MiniLM-L6-v2 | 500/sec | 82% | 80MB | General use (recommended) |
| all-mpnet-base-v2 | 100/sec | 89% | 450MB | High accuracy needed |
| all-DistilRoBERTa-v1 | 600/sec | 81% | 160MB | Maximum throughput |

### How to Switch

```python
from truthgraph import TruthGraph

# Use different model
tg = TruthGraph(
    embedding_model="all-mpnet-base-v2"  # Higher quality
)
```

## NLI Models

| Model | Speed | Accuracy | Recommended |
|-------|-------|----------|-------------|
| XLNET-base | 2 pairs/sec | 91% | Production |
| XLNET-large | 0.5 pairs/sec | 94% | High accuracy only |
| ELECTRA-base | 5 pairs/sec | 88% | Maximum throughput |

### Accuracy vs Speed Tradeoff

Use this decision tree:
- Need >90% accuracy? → XLNET-base
- Need 500+ texts/sec? → ELECTRA-base
- Balanced? → XLNET-base (recommended)
```

### Content: Monitoring

**docs/performance/monitoring.md**

```markdown
# Performance Monitoring

## Key Metrics to Monitor

1. **End-to-End Latency**: Total time for full verification
   - Target: <60 seconds
   - Alert threshold: >80 seconds

2. **Embedding Throughput**: Texts embedded per second
   - Target: >500 texts/sec
   - Alert threshold: <400 texts/sec

3. **Memory Usage**: Peak memory with loaded models
   - Target: <4GB
   - Alert threshold: >3.5GB

4. **Database Query Latency**: Time for evidence retrieval
   - Target: <1 second
   - Alert threshold: >2 seconds

## Monitoring Setup

```python
from truthgraph.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

# Start monitoring
with monitor.track("verification"):
    result = tg.verify("claim")

# Get metrics
metrics = monitor.get_metrics()
print(f"Latency: {metrics['latency_ms']}ms")
print(f"Memory: {metrics['memory_mb']}MB")
```

## Automated Alerts

Set up prometheus/grafana for continuous monitoring.
```

### Success Criteria

- Performance guide comprehensive
- Recommendations data-driven
- Benchmarks included
- Deployment guide complete
- All recommendations tested
- Clear instructions

---

## Timeline & Dependencies

### Week 1 (Days 1-3)

**Can start immediately**:
- Feature 5.1: Code Docstrings (10h)
- Feature 5.2: Troubleshooting Guide (8h)
- Feature 5.3: Usage Examples (10h)

**Start after Week 2 optimization**:
- Feature 5.4: Performance Guide (6h) - Depends on 2.x

### Parallel Execution

All features can run in parallel except 5.4 which depends on performance work completion.

---

## Progress Tracking

### Completion Checklist

- [ ] Feature 5.1 complete
- [ ] All public APIs documented
- [ ] Feature 5.2 complete
- [ ] 20+ issues documented
- [ ] Feature 5.3 complete
- [ ] 6+ example scripts working
- [ ] Feature 5.4 complete
- [ ] Performance guide data-driven
- [ ] All documentation built
- [ ] No doc generation warnings
- [ ] All features marked complete

---

## Related Files

**For Background Context**:
- [4_api_completion_handoff.md](./4_api_completion_handoff.md) - API to document
- [2_performance_optimization_handoff.md](./2_performance_optimization_handoff.md) - Performance data
- [dependencies_and_timeline.md](./dependencies_and_timeline.md) - Timeline
- [agent_assignments.md](./agent_assignments.md) - Deliverables

---

**Navigation**: [Master Index](./v0_phase2_completion_handoff_MASTER.md) | [Quick Start](./v0_phase2_quick_start.md) | [Dependencies](./dependencies_and_timeline.md) | [Previous: API](./4_api_completion_handoff.md)
