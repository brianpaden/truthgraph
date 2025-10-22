# Phase 1: Local MVP

**Timeline:** Months 1-2
**Goal:** Working fact-checker running locally via Docker

## Overview and Goals

Phase 1 establishes the foundation of TruthGraph as a local-first fact-checking system. The focus is on creating a fully functional MVP that runs entirely on a single machine using Docker Compose, with no external dependencies beyond pre-trained models.

> **Key Documentation References**:
> - **Technology Stack Details**: [tech_stack_and_tooling.md](tech_stack_and_tooling.md)
> - **Testing Approach**: See [Testing Strategy](#testing-strategy) section below
> - **Setup Instructions**: See [Quick Start Commands](#quick-start-commands) section below
> - **Common Issues**: See [Troubleshooting](#troubleshooting) section below

### Primary Objectives

1. **End-to-End Functionality**: Submit a claim, retrieve evidence, verify it, and receive a verdict
2. **Docker-Native Deployment**: All services containerized and orchestrated via docker-compose
3. **Simplified Architecture**: Redis Streams instead of Kafka, PostgreSQL instead of distributed databases
4. **Local-First Design**: No cloud dependencies, all data and models stored locally
5. **Developer Experience**: Easy setup with `docker-compose up`, clear logs, simple debugging

### Success Criteria

- Submit claim via API → receive verdict within 30 seconds
- Evidence retrieval from local knowledge base
- Basic NLI-based verification with confidence scores
- Provenance tracking for all claims and evidence
- Simple web UI for interaction
- Complete system runs on a single machine with 16GB RAM

## Docker Compose Stack Setup

> **Reference**: See [tech_stack_and_tooling.md](tech_stack_and_tooling.md) for detailed rationale on technology choices.

### Service Architecture

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    container_name: truthgraph-postgres
    environment:
      POSTGRES_DB: truthgraph
      POSTGRES_USER: truthgraph
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./volumes/postgres:/var/lib/postgresql/data
      - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U truthgraph"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - truthgraph-net

  redis:
    image: redis:7-alpine
    container_name: truthgraph-redis
    command: redis-server --appendonly yes
    volumes:
      - ./volumes/redis:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - truthgraph-net

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    container_name: truthgraph-api
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=truthgraph
      - POSTGRES_USER=truthgraph
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
      - NLI_MODEL=microsoft/deberta-v3-base
      - LOG_LEVEL=INFO
    volumes:
      - ./api:/app/api
      - ./volumes/models:/root/.cache/huggingface
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - truthgraph-net

  worker:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    container_name: truthgraph-worker
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=truthgraph
      - POSTGRES_USER=truthgraph
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
      - NLI_MODEL=microsoft/deberta-v3-base
      - LOG_LEVEL=INFO
    volumes:
      - ./ml:/app/ml
      - ./volumes/models:/root/.cache/huggingface
      - ./volumes/faiss-index:/app/faiss-index
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - truthgraph-net

  ui:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: truthgraph-ui
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    ports:
      - "5173:5173"
    depends_on:
      - api
    networks:
      - truthgraph-net

networks:
  truthgraph-net:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
```

### Volume Structure

```
truthgraph/
├── docker-compose.yml
├── .env
└── volumes/
    ├── postgres/          # PostgreSQL data directory
    ├── redis/             # Redis persistence (AOF)
    ├── models/            # Downloaded ML models
    │   ├── sentence-transformers/
    │   ├── deberta-v3-nli/
    │   └── faiss-index/
    └── knowledge-base/    # Initial corpus data
        ├── raw/           # Original documents
        └── processed/     # Chunked and embedded
```

### Network Configuration

- **Internal network**: `truthgraph-net` (bridge)
- **Exposed ports**:
  - `5432`: PostgreSQL (development only)
  - `6379`: Redis (development only)
  - `8000`: FastAPI API
  - `5173`: Vite dev server (UI)
- **Service discovery**: Docker DNS (service names as hostnames)
- **Health checks**: All services implement `/health` endpoints

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme_in_production

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Models (see tech_stack_and_tooling.md for model selection rationale)
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
NLI_MODEL=microsoft/deberta-v3-base
EMBEDDING_DIMENSION=384

# Application
LOG_LEVEL=INFO
MAX_EVIDENCE_ITEMS=10
VERIFICATION_THRESHOLD=0.7
API_HOST=0.0.0.0
API_PORT=8000

# Model Cache (for Hugging Face transformers)
MODEL_CACHE_DIR=/root/.cache/huggingface
```

### Quick Start Commands

**Prerequisites:**
- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- uv (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Task (task runner): See [tech_stack_and_tooling.md](tech_stack_and_tooling.md#task-runner-taskfile-go-task) for installation

**Setup and Run:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/truthgraph.git
cd truthgraph

# 2. Create environment file
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD

# 3. Create volumes directory structure
mkdir -p volumes/{postgres,redis,models,faiss-index,knowledge-base/{raw,processed}}

# 4. Initialize Python environment (for development)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# 5. Start all services with Docker Compose
docker compose up -d

# 6. Check service health
docker compose ps

# 7. Initialize database schema
docker compose exec api python -m scripts.init_db

# 8. Load sample knowledge base (optional)
docker compose exec api python -m scripts.load_corpus --path /data/knowledge-base/raw

# 9. Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - UI: http://localhost:5173
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379

# 10. View logs
docker compose logs -f

# Stop services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

**Using Taskfile (Recommended):**

If you have Task installed (see [tech_stack_and_tooling.md](tech_stack_and_tooling.md#task-runner-taskfile-go-task)):

```bash
# Setup project
task setup

# Start development environment
task dev

# Run tests
task test

# View logs
task logs

# Stop services
task down

# Full reset (removes all data)
task reset
```

## Simplified Event Flow

### Redis Streams Architecture

Instead of Kafka, Phase 1 uses Redis Streams for event-driven processing. This provides pub/sub, message persistence, and consumer groups without operational complexity.

> **Technical Rationale**: Redis Streams chosen over Kafka for Phase 1 due to lower operational overhead, simpler setup, and sufficient throughput for local MVP. See [tech_stack_and_tooling.md](tech_stack_and_tooling.md#redis) for details on Redis usage patterns.

### Event Streams

1. **claims-submitted**: New claims awaiting processing
2. **evidence-retrieval**: Claims ready for evidence gathering
3. **verification-pending**: Evidence collected, ready for NLI
4. **verdicts-ready**: Completed verifications

### Processing Pipeline

```
User submits claim
    ↓
API creates Claim record in PostgreSQL
    ↓
API publishes to 'claims-submitted' stream
    ↓
Worker consumes from stream
    ↓
Worker generates embeddings
    ↓
Worker retrieves evidence (FTS + pgvector + FAISS)
    ↓
Worker publishes to 'verification-pending' stream
    ↓
Verification worker runs NLI model
    ↓
Worker generates verdict + confidence
    ↓
Worker stores in PostgreSQL
    ↓
Worker publishes to 'verdicts-ready' stream
    ↓
API polls or subscribes for UI updates
```

### Message Schema

```json
{
  "stream": "claims-submitted",
  "message": {
    "claim_id": "uuid",
    "claim_text": "string",
    "submitted_at": "timestamp",
    "metadata": {
      "source": "api|ui",
      "user_id": "optional"
    }
  }
}
```

## Minimal Retrieval System

### Three-Tier Retrieval Strategy

Phase 1 implements a hybrid retrieval system combining lexical and semantic search:

#### 1. PostgreSQL Full-Text Search

**Purpose**: Fast lexical matching for exact phrases and keywords

```sql
-- FTS configuration
CREATE INDEX evidence_fts_idx ON evidence
USING gin(to_tsvector('english', content));

-- Example query
SELECT * FROM evidence
WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $claim)
ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery('english', $claim)) DESC
LIMIT 5;
```

#### 2. pgvector Semantic Search

**Purpose**: Dense vector similarity for semantic matching

```sql
-- pgvector extension
CREATE EXTENSION vector;

-- Embeddings table
CREATE TABLE evidence_embeddings (
    id UUID PRIMARY KEY,
    evidence_id UUID REFERENCES evidence(id),
    embedding VECTOR(384),  -- all-MiniLM-L6-v2 dimension
    created_at TIMESTAMP
);

-- Similarity search
SELECT e.* FROM evidence e
JOIN evidence_embeddings ee ON e.id = ee.evidence_id
ORDER BY ee.embedding <-> $claim_embedding
LIMIT 5;
```

#### 3. FAISS Dense Retrieval

**Purpose**: Ultra-fast approximate nearest neighbor search for large corpora

- **Index type**: IndexFlatIP (inner product) for MVP, upgrade to IndexIVFFlat later
- **Storage**: Serialized to disk, loaded on worker startup
- **Update strategy**: Rebuild nightly or on-demand
- **Integration**: FAISS returns IDs → lookup full records in PostgreSQL

### Embedding Pipeline

1. **Model**: `sentence-transformers/all-MiniLM-L6-v2`
   - Dimension: 384
   - Speed: ~1000 sentences/second on CPU
   - Quality: Good balance for MVP
   - **Rationale**: See [tech_stack_and_tooling.md](tech_stack_and_tooling.md#sentence-transformers) for comparison with Contriever and other embedding models

2. **Process**:
   - Chunk documents into 256-token segments
   - Generate embeddings in batches (32 per batch)
   - Store in both pgvector and FAISS index
   - Cache embeddings for reuse

### Retrieval Orchestration

```python
async def retrieve_evidence(claim: str, max_items: int = 10):
    # Generate claim embedding
    claim_embedding = embed_model.encode(claim)

    # Parallel retrieval
    fts_results = await fts_search(claim, limit=5)
    pgvector_results = await vector_search(claim_embedding, limit=5)
    faiss_results = await faiss_search(claim_embedding, limit=5)

    # Merge and deduplicate
    all_results = merge_results([fts_results, pgvector_results, faiss_results])

    # Re-rank by relevance
    ranked_results = rerank(claim, all_results, top_k=max_items)

    return ranked_results
```

## Basic Verification

### NLI-Based Verification

Phase 1 uses Natural Language Inference (NLI) to determine if evidence supports, contradicts, or is neutral to a claim.

#### Model Selection: DeBERTa-v3

- **Model**: `microsoft/deberta-v3-base` fine-tuned on MNLI
- **Input**: Premise (evidence) + Hypothesis (claim)
- **Output**: 3-class logits (entailment, contradiction, neutral)
- **Performance**: ~350ms per inference on CPU
- **Rationale**: DeBERTa-v3 selected for superior NLI performance over BERT/RoBERTa. See [tech_stack_and_tooling.md](tech_stack_and_tooling.md#model-details) for detailed model comparison and benchmarks.

#### Verification Logic

```python
def verify_claim(claim: str, evidence_list: List[Evidence]) -> Verdict:
    verdicts = []

    for evidence in evidence_list:
        # Run NLI model
        result = nli_model(
            premise=evidence.content,
            hypothesis=claim
        )

        verdicts.append({
            'evidence_id': evidence.id,
            'label': result['label'],  # entailment|contradiction|neutral
            'confidence': result['score'],
            'evidence_snippet': evidence.content[:200]
        })

    # Aggregate verdicts
    final_verdict = aggregate_verdicts(verdicts)

    return final_verdict
```

#### Verdict Aggregation

Simple majority voting with confidence weighting:

1. **Support score**: Sum of (confidence * weight) for entailment labels
2. **Refute score**: Sum of (confidence * weight) for contradiction labels
3. **Uncertainty score**: Sum of (confidence * weight) for neutral labels

**Final label**:
- `SUPPORTED` if support_score > 0.6
- `REFUTED` if refute_score > 0.6
- `INSUFFICIENT` otherwise

### Confidence Calculation

```python
confidence = max(support_score, refute_score) / len(evidence_list)
```

### Verdict Schema

```json
{
  "claim_id": "uuid",
  "verdict": "SUPPORTED|REFUTED|INSUFFICIENT",
  "confidence": 0.85,
  "evidence_count": 5,
  "supporting_evidence": ["uuid1", "uuid2"],
  "refuting_evidence": ["uuid3"],
  "neutral_evidence": ["uuid4", "uuid5"],
  "reasoning": "The claim is supported by 2 pieces of strong evidence...",
  "created_at": "timestamp"
}
```

## Provenance Storage

### PostgreSQL Schema

> **Technical Rationale**: PostgreSQL chosen over document stores or graph databases for Phase 1 due to ACID guarantees, mature tooling, and pgvector extension for hybrid relational+vector storage. See [tech_stack_and_tooling.md](tech_stack_and_tooling.md#postgresql--pgvector-extension) for detailed comparison.

```sql
-- Claims table
CREATE TABLE claims (
    id UUID PRIMARY KEY,
    text TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Evidence table
CREATE TABLE evidence (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Verdicts table
CREATE TABLE verdicts (
    id UUID PRIMARY KEY,
    claim_id UUID REFERENCES claims(id),
    verdict VARCHAR(20),
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evidence-Verdict relationships
CREATE TABLE verdict_evidence (
    verdict_id UUID REFERENCES verdicts(id),
    evidence_id UUID REFERENCES evidence(id),
    relationship VARCHAR(20),  -- supports|refutes|neutral
    confidence FLOAT,
    PRIMARY KEY (verdict_id, evidence_id)
);
```

### RDFLib Integration

For semantic provenance tracking and future reasoning capabilities:

> **Technical Rationale**: RDFLib provides standardized semantic web support (W3C PROV-O ontology) for provenance chains, enabling future integration with knowledge graphs and reasoning systems.

```python
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, PROV

# Define namespaces
TG = Namespace("http://truthgraph.org/ontology#")
graph = Graph()

# Store claim provenance
claim_uri = URIRef(f"http://truthgraph.org/claims/{claim_id}")
graph.add((claim_uri, RDF.type, TG.Claim))
graph.add((claim_uri, TG.text, Literal(claim_text)))
graph.add((claim_uri, PROV.generatedAtTime, Literal(timestamp)))

# Link evidence
evidence_uri = URIRef(f"http://truthgraph.org/evidence/{evidence_id}")
graph.add((verdict_uri, TG.basedOn, evidence_uri))
graph.add((evidence_uri, TG.supports, claim_uri))

# Serialize to PostgreSQL JSONB or separate RDF store
```

**Storage strategy**: Store RDF triples as JSONB in PostgreSQL for Phase 1, migrate to dedicated triplestore in Phase 2.

## Simple Web UI

### Technology Stack

- **Framework**: React 18 + TypeScript
- **Build tool**: Vite
- **Styling**: Tailwind CSS
- **State management**: React Query for server state
- **HTTP client**: Axios

> **Reference**: Frontend technology choices detailed in [tech_stack_and_tooling.md](tech_stack_and_tooling.md#frontend-react)

### UI Features

1. **Claim Submission**
   - Text input for claim
   - Submit button
   - Loading state during processing

2. **Results Display**
   - Verdict badge (Supported/Refuted/Insufficient)
   - Confidence meter
   - Evidence list with snippets
   - Expand/collapse for full evidence

3. **History**
   - List of previously submitted claims
   - Click to view details

### Key Components

```typescript
// ClaimSubmissionForm.tsx
// ResultsDisplay.tsx
// EvidenceCard.tsx
// ConfidenceMeter.tsx
// ClaimHistory.tsx
```

### API Integration

```typescript
// API endpoints
POST   /api/v1/claims              // Submit claim
GET    /api/v1/claims/{id}         // Get claim details
GET    /api/v1/verdicts/{claim_id} // Get verdict
GET    /api/v1/claims              // List claims
```

## Testing Strategy

> **Reference**: Complete testing guidelines in [tech_stack_and_tooling.md](tech_stack_and_tooling.md#testing-strategy)

### Test Levels

Phase 1 implements three levels of testing to ensure reliability and correctness:

#### 1. Unit Tests

**Scope**: Individual functions and classes in isolation

**Tools**:
- pytest for test execution
- pytest-mock for mocking
- pytest-asyncio for async tests

**Coverage Targets**:
- Core ML functions: 90%+
- API business logic: 85%+
- Database operations: 80%+
- Overall: 80%+

**Examples**:
```bash
# Run unit tests only
task test:unit

# Or directly with pytest
uv run pytest tests/unit -v

# With coverage
uv run pytest tests/unit --cov=api --cov=ml --cov-report=html
```

**Key Test Areas**:
- Embedding generation (mock transformers models)
- NLI verification logic
- Verdict aggregation algorithms
- Redis stream message formatting
- Database query builders

#### 2. Integration Tests

**Scope**: Component interactions and API endpoints

**Tools**:
- pytest-docker for test containers
- FastAPI TestClient for API testing
- Test PostgreSQL and Redis instances

**Setup**:
```python
# conftest.py fixture example
@pytest.fixture(scope="session")
def test_database():
    """Spin up test PostgreSQL container"""
    with DockerCompose("docker/test-compose.yml") as compose:
        compose.wait_for_service("postgres", timeout=30)
        yield compose.get_service_url("postgres")
```

**Examples**:
```bash
# Run integration tests
task test:integration

# Or directly
uv run pytest tests/integration -v
```

**Key Test Areas**:
- API endpoint flows (claim submission → verdict retrieval)
- Database transactions and rollbacks
- Redis stream publishing and consumption
- Retrieval pipeline (FTS + pgvector + FAISS)
- Worker job processing

#### 3. End-to-End Tests

**Scope**: Full user workflows through UI and API

**Tools**:
- Docker Compose for full stack
- httpx for API calls
- Playwright (optional) for UI testing

**Setup**:
```bash
# Start test environment
docker compose -f docker-compose.test.yml up -d

# Run E2E tests
uv run pytest tests/e2e -v

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

**Key Test Areas**:
- Submit claim → receive verdict (under 30s)
- Evidence retrieval quality (test with known claims)
- UI claim submission and results display
- System behavior under load (10 concurrent claims)

### Running Tests

**Quick Commands**:
```bash
# All tests with coverage
task test

# Watch mode (re-run on file changes)
task test:watch

# Specific test file
uv run pytest tests/unit/test_embeddings.py -v

# Specific test function
uv run pytest tests/unit/test_embeddings.py::test_batch_embedding -v

# With detailed output
uv run pytest -vv -s

# Stop on first failure
uv run pytest -x
```

### Test Data

**Fixtures Location**: `tests/fixtures/`
- `sample_claims.json`: Test claims with known verdicts
- `sample_evidence.json`: Pre-labeled evidence documents
- `test_corpus.parquet`: Small corpus for retrieval tests

**Generating Test Data**:
```bash
# Create test corpus
uv run python -m scripts.generate_test_data --output tests/fixtures/
```

### CI Integration

Tests run automatically on GitHub Actions (future):
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: task ci
```

**CI Pipeline**:
1. Lint code (ruff)
2. Type check (mypy)
3. Unit tests (fast, parallel)
4. Integration tests (Docker services)
5. Generate coverage report
6. Upload to codecov

### Performance Testing

**Targets**:
- Claim processing: < 30 seconds (end-to-end)
- Embedding generation: < 100ms per text
- NLI inference: < 500ms per evidence-claim pair
- Retrieval: < 2 seconds for 10 results
- API latency: < 200ms (excluding ML operations)

**Tools**:
```bash
# Load test API
locust -f tests/performance/locustfile.py --host http://localhost:8000
```

---

## Troubleshooting

### Common Setup Issues

#### Docker Compose Fails to Start

**Symptom**: `docker compose up` exits with errors

**Solutions**:
```bash
# 1. Check Docker is running
docker version

# 2. Verify .env file exists
ls -la .env

# 3. Check for port conflicts
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # API
lsof -i :5173  # Frontend

# 4. Remove old containers and volumes
docker compose down -v
docker system prune -f

# 5. Rebuild images
docker compose build --no-cache

# 6. Check logs
docker compose logs
```

#### PostgreSQL Connection Refused

**Symptom**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
```bash
# 1. Wait for PostgreSQL to be ready
docker compose logs postgres
# Look for "database system is ready to accept connections"

# 2. Check health status
docker compose ps

# 3. Test connection manually
docker compose exec postgres psql -U truthgraph -d truthgraph -c "SELECT 1;"

# 4. Verify environment variables
docker compose exec api env | grep POSTGRES

# 5. Reset database
docker compose down -v postgres
docker compose up -d postgres
sleep 10  # Wait for startup
```

#### Redis Connection Errors

**Symptom**: `redis.exceptions.ConnectionError`

**Solutions**:
```bash
# 1. Check Redis is running
docker compose exec redis redis-cli ping
# Should return "PONG"

# 2. Check Redis logs
docker compose logs redis

# 3. Verify connection from API container
docker compose exec api python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"

# 4. Clear Redis data
docker compose exec redis redis-cli FLUSHALL
```

#### Models Not Downloading

**Symptom**: `OSError: Model not found` or slow first startup

**Solutions**:
```bash
# 1. Pre-download models manually
uv run python -c "
from sentence_transformers import SentenceTransformer
from transformers import AutoModel

# Download embedding model
SentenceTransformer('all-MiniLM-L6-v2')

# Download NLI model
AutoModel.from_pretrained('microsoft/deberta-v3-base')
"

# 2. Verify models directory
ls -la volumes/models/

# 3. Set Hugging Face cache
export HF_HOME=$(pwd)/volumes/models
export TRANSFORMERS_CACHE=$(pwd)/volumes/models

# 4. Use offline mode after download
export TRANSFORMERS_OFFLINE=1
```

#### Out of Memory (OOM)

**Symptom**: Containers crash or `MemoryError`

**Solutions**:
```bash
# 1. Check available memory
docker stats

# 2. Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → Increase to 8GB+

# 3. Reduce batch sizes in .env
echo "EMBEDDING_BATCH_SIZE=8" >> .env
echo "NLI_BATCH_SIZE=4" >> .env

# 4. Use smaller models (trade-off: accuracy)
echo "SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2" >> .env
# Instead of larger models like Contriever

# 5. Disable FAISS (use pgvector only)
echo "ENABLE_FAISS=false" >> .env
```

#### pgvector Extension Not Found

**Symptom**: `ERROR: extension "vector" is not available`

**Solutions**:
```bash
# 1. Verify pgvector image
docker compose config | grep image
# Should show: pgvector/pgvector:pg15

# 2. Manually install extension
docker compose exec postgres psql -U truthgraph -d truthgraph -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Check extension is installed
docker compose exec postgres psql -U truthgraph -d truthgraph -c "\dx"
# Should list "vector"

# 4. If missing, rebuild database container
docker compose down -v postgres
docker compose up -d postgres
```

### Development Issues

#### Hot Reload Not Working

**Symptom**: Code changes don't reflect in running services

**Solutions**:
```bash
# 1. Verify volume mounts
docker compose config | grep volumes

# 2. Check file sync (Docker Desktop)
# Settings → Resources → File Sharing → Add project directory

# 3. Restart specific service
docker compose restart api

# 4. For UI, check Vite config
# frontend/vite.config.ts should have:
# server: { host: '0.0.0.0', port: 5173, watch: { usePolling: true } }
```

#### Slow Performance

**Symptom**: Claim processing takes > 60 seconds

**Solutions**:
```bash
# 1. Check if models are cached
docker compose logs api | grep "Loading model"
# Should only appear once at startup

# 2. Enable GPU (if available)
# docker-compose.yml:
#   worker:
#     deploy:
#       resources:
#         reservations:
#           devices:
#             - driver: nvidia
#               count: 1
#               capabilities: [gpu]

# 3. Profile slow operations
docker compose exec api python -m cProfile -s cumtime api/main.py

# 4. Check database indexes
docker compose exec postgres psql -U truthgraph -d truthgraph -c "\d evidence"
# Verify FTS and vector indexes exist

# 5. Optimize FAISS index
# For large corpora, use IndexIVFFlat instead of IndexFlatIP
```

#### Tests Failing

**Symptom**: `pytest` shows failures

**Solutions**:
```bash
# 1. Run with verbose output
uv run pytest -vv -s

# 2. Run single failing test
uv run pytest tests/unit/test_embeddings.py::test_specific_function -vv

# 3. Check test database is clean
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up -d

# 4. Update test fixtures
uv run python -m scripts.generate_test_data --force

# 5. Check for import errors
uv run python -c "import api.main; import ml.embeddings"
```

### Migration Issues

#### Alembic Migration Errors

**Symptom**: `alembic upgrade head` fails

**Solutions**:
```bash
# 1. Check current database version
docker compose exec api alembic current

# 2. View migration history
docker compose exec api alembic history

# 3. Manually fix schema and stamp version
docker compose exec postgres psql -U truthgraph -d truthgraph
# Run manual schema fixes
docker compose exec api alembic stamp head

# 4. Reset and re-migrate
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head

# 5. Fresh database (destructive)
docker compose down -v postgres
docker compose up -d postgres
sleep 10
docker compose exec api alembic upgrade head
```

### Getting Help

**Resources**:
- Check [tech_stack_and_tooling.md](tech_stack_and_tooling.md) for detailed configuration
- Review logs: `docker compose logs -f`
- Inspect container: `docker compose exec api bash`
- Database shell: `docker compose exec postgres psql -U truthgraph -d truthgraph`
- Redis CLI: `docker compose exec redis redis-cli`

**Debug Mode**:
```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker compose restart api worker

# View detailed logs
docker compose logs -f api worker
```

---

## TODO Checklist

### Infrastructure Setup

> See [tech_stack_and_tooling.md](tech_stack_and_tooling.md) for detailed configuration options

- [ ] Create `docker-compose.yml` with all services (postgres, redis, api, worker, ui)
- [ ] Create `.env.example` with complete configuration template
- [ ] Write `docker/api.Dockerfile` for FastAPI service
- [ ] Write `docker/worker.Dockerfile` for background worker
- [ ] Write `frontend/Dockerfile.dev` for Vite development server
- [ ] Configure PostgreSQL with pgvector extension (use pgvector/pgvector:pg15 image)
- [ ] Set up Redis with AOF persistence
- [ ] Set up volume mounts for models, data, and databases
- [ ] Configure health checks for all services
- [ ] Create `docker/init-db.sql` for initial database setup
- [ ] Create `Taskfile.yml` with common development tasks (setup, dev, test, lint)
- [ ] Test Docker Compose stack starts cleanly

### Database Layer

- [ ] Design PostgreSQL schema (claims, evidence, verdicts, relationships)
- [ ] Create migration files using Alembic
- [ ] Implement pgvector extension setup
- [ ] Create FTS indexes on evidence table
- [ ] Write database connection pooling logic (SQLAlchemy)
- [ ] Implement basic CRUD operations for entities
- [ ] Add database seeding script with sample evidence

### Event Processing

- [ ] Implement Redis Streams client wrapper
- [ ] Create producer functions for each event stream
- [ ] Implement consumer groups for workers
- [ ] Add event schema validation (Pydantic models)
- [ ] Write dead-letter queue handling for failed events
- [ ] Implement retry logic with exponential backoff
- [ ] Add event logging and monitoring

### Retrieval System

- [ ] Download and cache sentence-transformers model
- [ ] Implement embedding generation service
- [ ] Create PostgreSQL FTS query functions
- [ ] Implement pgvector similarity search
- [ ] Set up FAISS index creation and loading
- [ ] Write retrieval orchestration logic (parallel queries)
- [ ] Implement result merging and deduplication
- [ ] Add basic re-ranking function
- [ ] Create batch embedding pipeline for knowledge base

### Verification System

- [ ] Download and cache DeBERTa-v3 NLI model
- [ ] Implement NLI inference wrapper
- [ ] Create batch inference for multiple evidence items
- [ ] Write verdict aggregation logic
- [ ] Implement confidence calculation
- [ ] Add reasoning text generation
- [ ] Create verdict storage functions
- [ ] Add unit tests for verification logic

### Provenance Layer

- [ ] Set up RDFLib integration
- [ ] Define TruthGraph ontology (namespaces, classes, properties)
- [ ] Implement RDF triple generation for claims
- [ ] Add evidence provenance tracking
- [ ] Create verdict provenance chains
- [ ] Implement JSONB serialization for RDF
- [ ] Add provenance query functions

### API Development

- [ ] Set up FastAPI application structure
- [ ] Implement `/health` endpoint
- [ ] Create POST `/api/v1/claims` endpoint (Depends: Database, Event Processing)
- [ ] Create GET `/api/v1/claims/{id}` endpoint
- [ ] Create GET `/api/v1/verdicts/{claim_id}` endpoint
- [ ] Create GET `/api/v1/claims` listing endpoint
- [ ] Add request validation (Pydantic models)
- [ ] Implement error handling and logging
- [ ] Add CORS configuration for UI
- [ ] Write API documentation (OpenAPI)

### Worker Implementation

- [ ] Create worker service entry point
- [ ] Implement claims consumer (Depends: Retrieval System, Event Processing)
- [ ] Implement verification consumer (Depends: Verification System, Event Processing)
- [ ] Add graceful shutdown handling
- [ ] Implement worker health monitoring
- [ ] Add logging with structured output
- [ ] Create worker Dockerfile

### Web UI

- [ ] Initialize React + Vite project
- [ ] Set up Tailwind CSS
- [ ] Create ClaimSubmissionForm component
- [ ] Create ResultsDisplay component
- [ ] Create EvidenceCard component
- [ ] Create ConfidenceMeter component
- [ ] Implement API client with React Query
- [ ] Add loading and error states
- [ ] Create ClaimHistory component
- [ ] Add responsive design
- [ ] Write UI Dockerfile (nginx for production)

### Testing and Documentation

> See Testing Strategy section above for detailed test structure

- [ ] Set up pytest configuration in `pyproject.toml`
- [ ] Create test fixtures in `tests/fixtures/` (sample claims, evidence, corpus)
- [ ] Write unit tests for embedding generation (mock models)
- [ ] Write unit tests for NLI verification logic
- [ ] Write unit tests for verdict aggregation
- [ ] Write unit tests for Redis stream message formatting
- [ ] Create integration tests for API endpoints (using TestClient)
- [ ] Create integration tests for retrieval pipeline
- [ ] Create integration tests for worker job processing
- [ ] Add end-to-end test: submit claim → receive verdict (< 30s)
- [ ] Add end-to-end test: evidence retrieval quality
- [ ] Set up code coverage reporting (pytest-cov)
- [ ] Add performance tests (locust or similar)
- [ ] Create `docker-compose.test.yml` for test environment
- [ ] Write `README.md` with quick start guide
- [ ] Document API endpoints (OpenAPI/Swagger auto-generated)
- [ ] Add inline code documentation (docstrings)
- [ ] Create troubleshooting guide (see Troubleshooting section above)
- [ ] Document development workflow (using Task commands)
- [ ] Create CI/CD pipeline configuration (.github/workflows/test.yml)

### Initial Knowledge Base

- [ ] Identify sample corpus (Wikipedia dumps, fact-check databases)
- [ ] Create document chunking script
- [ ] Process and embed initial corpus
- [ ] Load into PostgreSQL and FAISS
- [ ] Verify retrieval quality with test queries

### Final Integration

- [ ] Test full pipeline end-to-end (Depends: All components)
- [ ] Verify Docker Compose brings up all services (`task dev`)
- [ ] Test claim submission through API
- [ ] Test claim submission through UI
- [ ] Validate verdict quality with 10+ known claims
- [ ] Check resource usage (memory should be < 8GB, CPU reasonable)
- [ ] Optimize bottlenecks (caching, batch sizes, indexing)
- [ ] Verify performance targets (< 30s claim processing)
- [ ] Run full test suite (`task test`)
- [ ] Run linters and type checks (`task lint && task type-check`)
- [ ] Generate and review code coverage report
- [ ] Create demo video or screenshots
- [ ] Update README.md with final setup instructions
- [ ] Tag v0.1.0 release

---

## Migration Notes

### From Existing Fact-Checking Systems

If you're migrating from or inspired by existing systems, consider these notes:

#### From ClaimBuster/ClaimReview Systems

**Data Migration**:
- ClaimReview JSON-LD can be imported directly into PostgreSQL
- Map ClaimReview properties to TruthGraph schema:
  - `claimReviewed` → `claims.text`
  - `reviewRating.ratingValue` → `verdicts.verdict` (map to SUPPORTED/REFUTED/INSUFFICIENT)
  - `itemReviewed` → `evidence.content`
  - `url` → `evidence.source_url`

**Example Import Script**:
```python
import json
from api.models import Claim, Evidence, Verdict

def import_claimreview(json_file):
    with open(json_file) as f:
        data = json.load(f)

    for review in data:
        claim = Claim(text=review['claimReviewed'])
        # ... map remaining fields
```

#### From FEVER Dataset

**Data Format**:
- FEVER provides claim-evidence pairs with labels (SUPPORTS/REFUTES/NOT ENOUGH INFO)
- Can be used directly for testing and validation

**Import Process**:
```bash
# 1. Download FEVER dataset
wget https://fever.ai/download/fever/train.jsonl

# 2. Import into TruthGraph
uv run python -m scripts.import_fever --input train.jsonl --limit 10000
```

#### From Manual Fact-Checking Databases

**Common Sources**:
- PolitiFact data
- Snopes archives
- FactCheck.org exports

**CSV/JSON Import**:
```bash
# Generic CSV import
uv run python -m scripts.import_corpus \
  --format csv \
  --input factcheck_data.csv \
  --text-column "claim" \
  --verdict-column "rating" \
  --source-column "url"
```

#### From Wikipedia Dumps

**Using Wikipedia as Knowledge Base**:
```bash
# 1. Download Wikipedia dump
wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2

# 2. Extract and process
uv run python -m scripts.process_wikipedia \
  --input enwiki-latest-pages-articles.xml.bz2 \
  --output data/corpus/wikipedia.parquet \
  --chunk-size 256

# 3. Generate embeddings
task corpus:embed

# 4. Build FAISS index
task corpus:index
```

### Breaking Changes from Earlier Prototypes

If you have earlier prototypes or proof-of-concepts:

**Database Schema Changes**:
- Unified `verdicts` table replaces separate support/refute tables
- Added `metadata` JSONB columns for extensibility
- Vector embeddings now use pgvector instead of separate vector DB

**API Changes**:
- RESTful endpoints instead of GraphQL (simplicity for Phase 1)
- Async/await throughout
- Standardized error responses

**Configuration Changes**:
- Environment variables replace YAML config files
- Docker Compose v2 syntax (`docker compose` not `docker-compose`)
- `uv` replaces `pip` and `pip-tools`

---

**Next Phase**: [Phase 2 - Enhanced Retrieval and Multi-Source Evidence](phase_02_enhanced_retrieval.md)
