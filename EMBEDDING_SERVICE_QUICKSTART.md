# Embedding Service - Quick Start Guide

## Installation

### 1. Install ML Dependencies

```bash
# Using pip
pip install torch sentence-transformers transformers

# Or using pyproject.toml
pip install -e ".[ml]"
```

### 2. Verify Installation

```python
# Test import
from truthgraph.services.ml import get_embedding_service

# Initialize (will download model on first run - ~80MB)
service = get_embedding_service()
print(f"Using device: {service.get_device()}")
```

## Basic Usage

### Single Text Embedding

```python
from truthgraph.services.ml import get_embedding_service

service = get_embedding_service()

# Generate embedding
embedding = service.embed_text("The Earth orbits the Sun")

print(f"Embedding dimension: {len(embedding)}")  # 384
print(f"First 5 values: {embedding[:5]}")
```

### Batch Processing (Recommended)

```python
# Much faster than processing individually
texts = [
    "Climate change is a global issue",
    "Artificial intelligence is transforming industries",
    "Renewable energy sources are becoming cheaper"
]

embeddings = service.embed_batch(texts)
print(f"Generated {len(embeddings)} embeddings")

# With custom batch size for GPU
embeddings = service.embed_batch(texts, batch_size=128)
```

## Running Tests

### Unit Tests (Fast - No Model Download)

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run unit tests with mocks
pytest tests/services/ml/test_embedding_service.py -v

# Expected output: All tests should pass
```

### Integration Tests (Downloads Model)

```bash
# Run integration tests (requires ~80MB model download first time)
pytest tests/integration/test_embedding_service_integration.py -v

# This will test:
# - Real model loading
# - Embedding generation
# - Performance validation
```

## Performance Benchmarking

```bash
# Run full benchmark suite
python scripts/benchmark_embeddings.py

# Quick benchmark
python scripts/benchmark_embeddings.py --num-texts 100 --skip-memory

# Custom batch sizes
python scripts/benchmark_embeddings.py --batch-sizes 16,32,64,128
```

### Expected Performance

| Device | Throughput | Single Text Latency |
|--------|------------|---------------------|
| CPU (4 cores) | 500-1000 texts/s | 20-50ms |
| GPU (CUDA) | 2000-5000 texts/s | 5-15ms |
| Apple Silicon (MPS) | 1000-2000 texts/s | 10-30ms |

## Code Quality Checks

```bash
# Linting with ruff
python -m ruff check truthgraph/services/ml/embedding_service.py

# Type checking with mypy
python -m mypy truthgraph/services/ml/embedding_service.py --ignore-missing-imports

# Both should return: All checks passed! / Success: no issues found
```

## Common Issues

### ModuleNotFoundError: 'sentence_transformers'

```bash
# Install ML dependencies
pip install sentence-transformers torch transformers
```

### Model Download Fails

```bash
# Check internet connection
# Models are cached in: ~/.cache/huggingface/hub/

# Manual download (if needed)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"
```

### CUDA Out of Memory

```python
# Reduce batch size
embeddings = service.embed_batch(texts, batch_size=16)  # Smaller batch
```

### Slow Performance on CPU

```python
# Increase batch size for better throughput
embeddings = service.embed_batch(texts, batch_size=64)  # Larger batch
```

## Next Steps

1. **Install dependencies**: `pip install -e ".[ml]"`
2. **Run tests**: `pytest tests/services/ml/test_embedding_service.py -v`
3. **Run benchmarks**: `python scripts/benchmark_embeddings.py`
4. **Integrate with your code**: See examples in implementation report

## File Locations

- **Service**: `truthgraph/services/ml/embedding_service.py`
- **Unit Tests**: `tests/services/ml/test_embedding_service.py`
- **Integration Tests**: `tests/integration/test_embedding_service_integration.py`
- **Benchmarks**: `scripts/benchmark_embeddings.py`
- **Documentation**: `EMBEDDING_SERVICE_IMPLEMENTATION_REPORT.md`

## Support

For detailed documentation, see: `EMBEDDING_SERVICE_IMPLEMENTATION_REPORT.md`

For issues or questions, refer to:
- Implementation plan: `PHASE_2_IMPLEMENTATION_PLAN.md`
- Project README: `README.md`
