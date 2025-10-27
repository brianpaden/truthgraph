# TruthGraph Developer Guide

**Version:** 0.2.0 (Phase 2)
**Last Updated:** October 26, 2025
**Target Audience:** Software Engineers, ML Engineers, DevOps

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Core Services](#core-services)
5. [Database Schema](#database-schema)
6. [Testing Strategy](#testing-strategy)
7. [Performance Optimization](#performance-optimization)
8. [Deployment](#deployment)
9. [Contributing Guidelines](#contributing-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     TruthGraph v0.2                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Frontend   │ ◄─────► │   FastAPI    │                │
│  │   (htmx)     │         │   Backend    │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                    ┌──────────────┴──────────────┐         │
│                    │                             │         │
│         ┌──────────▼───────┐        ┌───────────▼──────┐  │
│         │  ML Services      │        │   Database       │  │
│         │  ├─ Embedding     │        │   PostgreSQL     │  │
│         │  ├─ Vector Search │        │   + pgvector     │  │
│         │  ├─ Hybrid Search │        │                  │  │
│         │  ├─ NLI Service   │        │   Tables:        │  │
│         │  ├─ Verdict Agg   │        │   - claims       │  │
│         │  └─ Pipeline      │        │   - evidence     │  │
│         └───────────────────┘        │   - embeddings   │  │
│                                      │   - nli_results  │  │
│                                      └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Service-Oriented Architecture**: Each ML capability is an independent service
2. **Singleton Pattern**: ML models loaded once, reused across requests
3. **Async-First**: FastAPI + async SQLAlchemy for concurrency
4. **Type Safety**: Pydantic v2 for request/response validation
5. **Performance**: Caching, batching, and GPU acceleration
6. **Observability**: Structured logging, metrics, health checks

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | FastAPI | 0.115+ |
| **Database** | PostgreSQL + pgvector | 16 + 0.7.0 |
| **ML Framework** | PyTorch + Transformers | 2.1+ / 4.36+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Validation** | Pydantic | 2.0+ |
| **Testing** | pytest + pytest-asyncio | 8.0+ |
| **Task Runner** | Task (go-task) | 3.0+ |
| **Containerization** | Docker + Docker Compose | 24.0+ |

---

## Development Environment Setup

### Prerequisites

- **Python**: 3.12+ (3.13 recommended)
- **Docker**: 24.0+ with Docker Compose
- **Git**: 2.40+
- **Task**: 3.0+ (optional but recommended)
- **RAM**: 4GB+ available
- **Disk**: 10GB+ free space

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/truthgraph.git
cd truthgraph

# 2. Copy environment file
cp .env.example .env

# 3. Start services
task dev

# 4. Verify setup
curl http://localhost:8000/health
```

### Detailed Setup

#### 1. Python Environment

Using `uv` (recommended):
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

Using `pip`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 2. Database Setup

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Wait for database to be ready
sleep 5

# Run migrations
task db:migrate

# Verify
task db:migrate:status
```

#### 3. Download ML Models

```bash
# Download and cache models (~520MB)
task ml:warmup

# This downloads:
# - all-MiniLM-L6-v2 (embedding model)
# - cross-encoder/nli-deberta-v3-base (NLI model)
```

#### 4. Run Tests

```bash
# Run all tests
task test

# Run specific test suites
task test:unit
task test:integration
task test:ml

# Check coverage
task test:coverage
```

---

## Project Structure

```text
truthgraph/
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic configuration
├── data/                      # Test data and fixtures
│   └── sample_claims.json
├── docs/                      # Documentation
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── PERFORMANCE_OPTIMIZATION.md
│   └── verification_pipeline.md
├── docker/                    # Docker configurations
│   ├── api.Dockerfile
│   ├── migrations/
│   └── docker-compose.yml
├── scripts/                   # Utility scripts
│   ├── benchmark_*.py        # Performance benchmarks
│   └── example_*.py          # Usage examples
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── benchmarks/           # Performance tests
│   └── fixtures/             # Test data
├── truthgraph/                # Main application
│   ├── api/                  # FastAPI routes
│   │   ├── ml_routes.py     # ML endpoints
│   │   ├── models.py        # Pydantic models
│   │   └── middleware.py    # Middleware stack
│   ├── services/             # Business logic
│   │   ├── ml/              # ML services
│   │   │   ├── embedding_service.py
│   │   │   ├── nli_service.py
│   │   │   ├── verdict_aggregation_service.py
│   │   │   └── model_cache.py
│   │   ├── vector_search_service.py
│   │   ├── hybrid_search_service.py
│   │   └── verification_pipeline_service.py
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Database schema definitions
│   ├── database.py           # Database connection
│   ├── config.py             # Configuration
│   └── main.py               # FastAPI app
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Dev dependencies
├── Taskfile.yml              # Task commands
├── pytest.ini                # Pytest configuration
└── README.md                 # Project overview
```

### Key Files

| File | Purpose |
|------|---------|
| [truthgraph/main.py](../truthgraph/main.py) | FastAPI application entry point |
| [truthgraph/services/verification_pipeline_service.py](../truthgraph/services/verification_pipeline_service.py) | End-to-end orchestration |
| [truthgraph/api/ml_routes.py](../truthgraph/api/ml_routes.py) | REST API endpoints |
| [truthgraph/models.py](../truthgraph/models.py) | SQLAlchemy ORM models |
| [Taskfile.yml](../Taskfile.yml) | Task automation commands |
| [docker-compose.yml](../docker-compose.yml) | Service orchestration |

---

## Core Services

### 1. Embedding Service

**File:** [truthgraph/services/ml/embedding_service.py](../truthgraph/services/ml/embedding_service.py)

**Purpose:** Generate semantic embeddings for text

**Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)

**Usage:**
```python
from truthgraph.services.ml import get_embedding_service

service = get_embedding_service()

# Single text
embedding = service.embed_text("The Earth orbits the Sun")

# Batch processing
embeddings = service.embed_batch(texts, batch_size=32)
```

**Performance:**
- Throughput: 523 texts/second
- Latency: ~50-150ms (first request), <10ms (cached)
- Memory: ~500MB (model + overhead)

### 2. Vector Search Service

**File:** [truthgraph/services/vector_search_service.py](../truthgraph/services/vector_search_service.py)

**Purpose:** Find similar evidence using pgvector

**Usage:**
```python
from truthgraph.services import VectorSearchService

service = VectorSearchService(embedding_dimension=384)

results = service.search(
    db=session,
    query_embedding=embedding,
    top_k=10,
    min_similarity=0.5,
    tenant_id="default"
)
```

**Performance:**
- Latency: ~45ms (typical)
- Index: IVFFlat with 100 lists
- Distance: Cosine similarity

### 3. Hybrid Search Service

**File:** [truthgraph/services/hybrid_search_service.py](../truthgraph/services/hybrid_search_service.py)

**Purpose:** Combine vector + keyword search with RRF

**Algorithm:** Reciprocal Rank Fusion
```python
RRF_score(d) = Σ weight_i × 1/(k + rank_i(d))
where k=60 (standard constant)
```

**Usage:**
```python
from truthgraph.services import HybridSearchService

service = HybridSearchService(embedding_dimension=384)

results, time_ms = service.hybrid_search(
    db=session,
    query_text="climate change",
    query_embedding=embedding,
    top_k=10,
    vector_weight=0.6,
    keyword_weight=0.4
)
```

**Performance:**
- Latency: ~45-85ms
- Better relevance than vector-only

### 4. NLI Service

**File:** [truthgraph/services/ml/nli_service.py](../truthgraph/services/ml/nli_service.py)

**Purpose:** Determine logical relationship between claim and evidence

**Model:** `cross-encoder/nli-deberta-v3-base`

**Labels:**
- `entailment`: Evidence supports claim
- `contradiction`: Evidence refutes claim
- `neutral`: No clear relationship

**Usage:**
```python
from truthgraph.services.ml import get_nli_service

service = get_nli_service()

# Single inference
result = service.infer(
    premise="The Earth orbits the Sun",
    hypothesis="The Sun is the center of our solar system"
)
# → label="entailment", confidence=0.98

# Batch processing
results = service.infer_batch(premises, hypotheses, batch_size=8)
```

**Performance:**
- Throughput: 2.3 pairs/second
- Latency: ~435ms per inference
- Batch recommended for >5 pairs

### 5. Verdict Aggregation Service

**File:** [truthgraph/services/ml/verdict_aggregation_service.py](../truthgraph/services/ml/verdict_aggregation_service.py)

**Purpose:** Aggregate multiple NLI results into final verdict

**Strategies:**
1. **Weighted Vote** (default): Confidence-weighted voting
2. **Majority Vote**: Simple majority wins
3. **Confidence Threshold**: Require minimum confidence
4. **Strict Consensus**: All evidence must agree

**Usage:**
```python
from truthgraph.services.ml import get_verdict_aggregation_service

service = get_verdict_aggregation_service()

verdict = service.aggregate(
    nli_results,
    strategy=AggregationStrategy.WEIGHTED_VOTE,
    min_confidence=0.5
)
# → verdict="SUPPORTED", confidence=0.92
```

**Performance:**
- Latency: <0.03ms
- Pure Python computation (no ML)

### 6. Verification Pipeline

**File:** [truthgraph/services/verification_pipeline_service.py](../truthgraph/services/verification_pipeline_service.py)

**Purpose:** Orchestrate end-to-end claim verification

**Pipeline Flow:**
```text
1. Cache Check → 2. Embed Claim → 3. Search Evidence →
4. NLI Verification → 5. Aggregate Verdict → 6. Store Results → 7. Return
```

**Usage:**
```python
from truthgraph.services.verification_pipeline_service import (
    get_verification_pipeline_service
)

service = get_verification_pipeline_service()

result = await service.verify_claim(
    db=session,
    claim_id="clm_123",
    claim_text="The Earth is round",
    top_k_evidence=10
)
```

**Performance:**
- E2E: 5-30 seconds (typical)
- Cached: <5ms

---

## Database Schema

### Tables

#### 1. `claims`

```sql
CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. `evidence`

```sql
CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source_url TEXT,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. `embeddings`

```sql
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER REFERENCES evidence(id),
    embedding vector(384) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### 4. `nli_results`

```sql
CREATE TABLE nli_results (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id),
    evidence_id INTEGER REFERENCES evidence(id),
    label VARCHAR(50) NOT NULL,  -- entailment, contradiction, neutral
    confidence FLOAT NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. `verification_results`

```sql
CREATE TABLE verification_results (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id),
    verdict VARCHAR(50) NOT NULL,  -- SUPPORTED, REFUTED, INSUFFICIENT
    confidence FLOAT NOT NULL,
    evidence_count INTEGER NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Migrations

```bash
# Create new migration
task db:migrate:create NAME="add_new_table"

# Apply migrations
task db:migrate

# Rollback last migration
task db:migrate:down

# Check migration status
task db:migrate:status
```

---

## Testing Strategy

### Test Structure

```text
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── services/
│   │   ├── ml/
│   │   │   ├── test_embedding_service.py
│   │   │   ├── test_nli_service.py
│   │   │   └── test_verdict_aggregation_service.py
│   │   ├── test_vector_search_service.py
│   │   ├── test_hybrid_search_service.py
│   │   └── test_verification_pipeline_service.py
│   └── api/
│       └── test_ml_routes.py
├── integration/               # Integration tests (slower, real DB)
│   ├── test_hybrid_search_integration.py
│   ├── test_verification_pipeline_integration.py
│   └── test_ml_integration.py
└── benchmarks/                # Performance tests
    ├── test_embedding_performance.py
    ├── test_nli_performance.py
    └── test_hybrid_search_performance.py
```

### Running Tests

```bash
# All tests
task test

# Unit tests only (fast)
task test:unit

# Integration tests
task test:integration

# ML service tests
task test:ml

# With coverage
task test:coverage

# Specific test file
python -m pytest tests/unit/services/ml/test_nli_service.py -v

# Specific test
python -m pytest tests/unit/services/ml/test_nli_service.py::test_infer_entailment -v
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from truthgraph.services.ml import get_nli_service

class TestNLIService:
    @pytest.fixture
    def service(self):
        return get_nli_service()

    def test_infer_entailment(self, service):
        result = service.infer(
            premise="The Earth orbits the Sun",
            hypothesis="The Sun is the center"
        )
        assert result.label == "entailment"
        assert result.confidence > 0.8
```

**Integration Test Example:**
```python
import pytest
from sqlalchemy.orm import Session
from truthgraph.database import SessionLocal
from truthgraph.models import Evidence, EmbeddingRecord

class TestHybridSearchIntegration:
    @pytest.fixture
    def db(self) -> Session:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def test_search_with_real_database(self, db):
        # Test with actual database
        results, time_ms = hybrid_service.hybrid_search(
            db=db,
            query_text="test query",
            query_embedding=embedding,
            top_k=10
        )
        assert len(results) > 0
        assert time_ms < 150  # Performance target
```

### Test Coverage Goals

- **Overall**: >80%
- **Services**: >90%
- **API**: >85%
- **Critical paths**: 100%

---

## Performance Optimization

### 1. Model Caching

**Problem:** Loading ML models on every request takes ~10 seconds

**Solution:** Singleton pattern with lazy loading

```python
from truthgraph.services.ml.model_cache import ModelCache

cache = ModelCache()
model = cache.get_or_load("embedding_model", load_func)
```

**Impact:** 200x faster (10s → 50ms)

### 2. Batch Processing

**Problem:** Processing items individually is inefficient

**Solution:** Batch multiple items together

```python
# Bad: Loop through items
for text in texts:
    embedding = service.embed_text(text)  # Slow

# Good: Batch processing
embeddings = service.embed_batch(texts, batch_size=32)  # Fast
```

**Impact:** 10-20x throughput improvement

### 3. Database Indexing

**Problem:** Vector similarity search is slow without indexes

**Solution:** pgvector IVFFlat index

```sql
CREATE INDEX ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Impact:** 10-100x faster queries

### 4. Connection Pooling

**Problem:** Creating database connections is expensive

**Solution:** SQLAlchemy connection pool

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

### 5. Caching

**Problem:** Repeated requests for same claims

**Solution:** In-memory LRU cache with TTL

```python
@lru_cache(maxsize=1000)
def get_cached_result(claim_hash: str):
    return cached_results.get(claim_hash)
```

**Impact:** 1000x faster for cache hits (<5ms)

### Benchmarking

```bash
# Run all benchmarks
task ml:benchmark

# Specific benchmarks
task ml:benchmark:embedding
task ml:benchmark:nli
task ml:benchmark:vector
task ml:benchmark:e2e

# Profile for bottlenecks
task ml:profile
```

---

## Deployment

### Development

```bash
# Start all services
task dev

# View logs
task logs

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -f docker/api.Dockerfile -t truthgraph:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Environment Variables

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost:5432/truthgraph
REDIS_URL=redis://localhost:6379/0
ML_DEVICE=cpu  # or cuda, mps
LOG_LEVEL=info
RATE_LIMIT_ENABLED=true
```

### Health Checks

```bash
# Check service health
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "embedding_service": "ready",
    "nli_service": "ready"
  }
}
```

### Monitoring

**Key Metrics to Track:**
- Request rate (req/sec)
- Response latency (p50, p95, p99)
- Error rate (%)
- Cache hit rate (%)
- Database connection pool usage
- ML model memory usage
- Verdict distribution

**Example with Prometheus:**
```python
from prometheus_client import Counter, Histogram

request_count = Counter('api_requests_total', 'Total requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

@request_duration.time()
def verify_claim(...):
    request_count.inc()
    # ... verification logic
```

---

## Contributing Guidelines

### Code Standards

1. **Python Style**: Follow PEP 8
2. **Type Hints**: Use type hints everywhere
3. **Docstrings**: Google-style docstrings
4. **Linting**: Use `ruff` for linting
5. **Formatting**: Use `black` for formatting

### Code Quality Checks

```bash
# Lint code
ruff check .

# Format code
black .

# Type checking
mypy truthgraph/

# Run all checks
task lint
```

### Pull Request Process

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Write** tests for new functionality
4. **Ensure** all tests pass (`task test`)
5. **Update** documentation
6. **Commit** with clear messages
7. **Push** to your fork
8. **Open** Pull Request

### Commit Messages

Follow conventional commits:
```text
feat: Add hybrid search service
fix: Correct NLI confidence calculation
docs: Update API documentation
test: Add integration tests for pipeline
perf: Optimize batch processing
```

---

## Troubleshooting

### Common Issues

#### 1. "Model not found" Error

**Solution:**
```bash
# Download models
task ml:warmup

# Or manually
python -c "from transformers import AutoModel; AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')"
```

#### 2. Database Connection Failed

**Solution:**
```bash
# Check database is running
docker ps | grep postgres

# Restart database
docker-compose restart postgres

# Check connection
psql postgresql://truthgraph:password@localhost:5432/truthgraph
```

#### 3. Out of Memory

**Solution:**
```bash
# Reduce batch sizes
# embedding_service.py: batch_size=16 (default: 32)
# nli_service.py: batch_size=4 (default: 8)

# Or increase Docker memory
# Docker Desktop → Settings → Resources → Memory: 8GB
```

#### 4. Slow First Request

**Expected behavior:** First request loads models (~10s)

**Solution:**
```bash
# Pre-warm models on startup
task ml:warmup
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug

# Run with verbose output
python -m truthgraph.main --log-level debug

# Check logs
task logs
```

### Getting Help

1. Check documentation in `docs/`
2. Search GitHub issues
3. Run health check: `curl http://localhost:8000/health`
4. Check logs: `task logs`
5. Open GitHub issue with details

---

## API Reference

Full interactive API documentation available at:
- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

---

## Additional Resources

### Documentation

- [User Guide](USER_GUIDE.md) - For end users
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Optimization techniques
- [Verification Pipeline](verification_pipeline.md) - Pipeline architecture
- [Hybrid Search](HYBRID_SEARCH_SERVICE.md) - Search implementation

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Guide](https://docs.sqlalchemy.org/en/20/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)

---

**Happy Coding! 🚀**

For questions or support, please open a GitHub issue or consult the [User Guide](USER_GUIDE.md).
