# Tech Stack and Tooling

## Overview

TruthGraph is a local-first fact-checking system designed for developer experience, reproducibility, and offline operation. This document outlines the complete technology stack, tooling choices, and development workflow for the v1 implementation.

**Design Principles:**
- Local-first: All components run on developer machines
- Reproducible: Deterministic builds with locked dependencies
- Container-based: Docker Compose orchestrates all services
- Developer-friendly: Fast iteration cycles with modern tooling
- Type-safe: Static type checking where applicable
- Testable: Comprehensive test coverage with pytest

---

## Core Technology Stack

### Language: Python (managed via uv)

**Python 3.11+** serves as the primary language for backend, ML pipelines, and data processing.

- **uv**: Fast, modern Python package installer and resolver
  - Replaces pip and pip-tools
  - ~10-100x faster than pip
  - Built-in virtual environment management
  - Compatible with pyproject.toml and requirements.txt

**Why uv?**
- Speed: Dramatically faster dependency resolution and installation
- Reliability: Better dependency conflict resolution
- Modern: First-class support for PEP 621 (pyproject.toml)
- Simplicity: Single tool for virtual envs and packages

### API Framework: FastAPI

**FastAPI** powers the REST API layer for claim analysis, corpus queries, and fact-checking workflows.

**Key Features:**
- Async/await support for high concurrency
- Automatic OpenAPI documentation
- Pydantic models for request/response validation
- Type hints for IDE support and static analysis
- Dependency injection system

**Endpoints (planned):**
- `/api/v1/claims/analyze` - Submit claims for fact-checking
- `/api/v1/corpus/search` - Query evidence corpus
- `/api/v1/evidence/retrieve` - Fetch evidence for claims
- `/api/v1/verdicts/` - Retrieve fact-check verdicts

### Frontend: React

**React 18+** provides the web interface for claim submission, evidence browsing, and verdict visualization.

**Stack:**
- **Vite**: Fast development server and build tool
- **TypeScript**: Type safety in frontend code
- **React Query**: Server state management and caching
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: Component library (optional)

**Features:**
- Real-time claim analysis status
- Evidence highlighting and provenance display
- Interactive verdict explanations
- Corpus exploration interface

### Container: Docker & Docker Compose

**Docker Compose** orchestrates all services for local development and deployment.

**Services:**
- `api`: FastAPI backend
- `frontend`: React development server (dev) or nginx (prod)
- `postgres`: PostgreSQL with pgvector
- `redis`: Redis for queuing and caching
- `neo4j`: (optional) Graph database
- `opensearch`: (optional) Advanced search engine

**Benefits:**
- Consistent environments across machines
- Easy service discovery via container networking
- Volume persistence for databases and models
- Single command startup: `docker compose up`

---

## Storage & Data

### PostgreSQL (+ pgvector extension)

**Primary relational database** for structured data and vector similarity search.

**Schema (key tables):**
- `claims`: User-submitted claims
- `evidence_items`: Documents and snippets from corpus
- `verdicts`: Fact-check results with confidence scores
- `embeddings`: Vector representations (using pgvector)
- `provenance`: Source tracking and metadata

**pgvector Extension:**
- Native vector similarity search in PostgreSQL
- Supports inner product, L2 distance, cosine similarity
- Index types: IVFFlat, HNSW
- Integrates with SQL queries for hybrid retrieval

**Why PostgreSQL?**
- Mature, reliable, and well-understood
- ACID guarantees for critical data
- pgvector eliminates need for separate vector DB
- Excellent tooling and ecosystem

### Redis

**In-memory data store** for queuing, caching, and session management.

**Use Cases:**
- **Task queuing**: Background jobs for claim analysis
- **Caching**: Frequently accessed corpus items
- **Rate limiting**: API throttling
- **Session storage**: User sessions (if auth added)

**Libraries:**
- `redis-py`: Python client
- `rq` or `celery`: Task queue systems (TBD)

### FAISS (File-based Vector Indices)

**Facebook AI Similarity Search** for high-performance vector retrieval.

**Use Cases:**
- Fast k-NN search across large corpus embeddings
- Hybrid with PostgreSQL: FAISS for initial retrieval, pgvector for reranking
- File-based indices stored in Docker volumes

**Index Types:**
- `IndexFlatIP`: Exact search (small datasets)
- `IndexIVFFlat`: Inverted file index (medium datasets)
- `IndexHNSW`: Hierarchical navigable small world (large datasets)

**Integration:**
- Build indices during corpus ingestion
- Persist to disk: `/data/faiss_indices/`
- Load on API startup for sub-millisecond queries

### Parquet (Corpus Storage)

**Apache Parquet** for columnar corpus data storage.

**Benefits:**
- Efficient compression (10-100x vs CSV)
- Fast columnar reads for analytics
- Schema evolution support
- Interoperable with pandas, PyArrow, DuckDB

**Corpus Schema:**
```python
{
    "doc_id": str,
    "text": str,
    "title": str,
    "source": str,
    "publish_date": datetime,
    "embedding": List[float],  # Optional
    "metadata": dict
}
```

**Storage Location:**
- `/data/corpus/*.parquet`
- Partitioned by source or date for faster queries

---

## ML & NLP Stack

### Hugging Face Transformers

**Core library** for loading and running transformer models.

**Models Used:**
- **DeBERTa-v3-base** (NLI): Natural language inference for claim-evidence entailment
- **Contriever** (Embeddings): Dense retrieval embeddings
- **T5 or BART** (optional): Abstractive summarization

**Integration:**
- Models cached in `/data/models/` Docker volume
- Loaded on API startup or lazily on first request
- Inference via PyTorch or ONNX Runtime

### sentence-transformers

**Simplified interface** for sentence embeddings and semantic similarity.

**Key Models:**
- `sentence-transformers/contriever`: 768-dim embeddings
- `sentence-transformers/all-MiniLM-L6-v2`: Lightweight alternative

**Usage:**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('facebook/contriever')
embeddings = model.encode(texts)
```

### spaCy

**Industrial-strength NLP** for linguistic preprocessing.

**Features Used:**
- Tokenization and sentence segmentation
- Named entity recognition (NER)
- Dependency parsing (optional)
- Pipeline: `en_core_web_sm` or `en_core_web_trf`

**Use Cases:**
- Extract entities from claims (people, organizations, dates)
- Chunk documents into sentences for evidence retrieval
- Linguistic feature extraction for provenance analysis

### Model Details

**DeBERTa-v3 (NLI)**
- Task: Natural language inference (entailment, neutral, contradiction)
- Model: `microsoft/deberta-v3-base` fine-tuned on MNLI
- Input: `[CLS] Claim [SEP] Evidence [SEP]`
- Output: 3-class logits (entailment score used for verdict)

**Contriever (Embeddings)**
- Task: Dense passage retrieval
- Model: `facebook/contriever` or `facebook/contriever-msmarco`
- Embedding dim: 768
- Trained with contrastive learning on web corpus

---

## Optional Services

### Neo4j (Graph Database)

**Graph database** for knowledge graph representation of claims, evidence, and entities.

**Use Cases:**
- Model relationships between claims (contradicts, supports)
- Entity disambiguation and linking
- Graph-based reasoning and explanation
- Provenance chains

**Integration:**
- Docker service: `neo4j:5.x`
- Python driver: `neo4j-driver`
- Cypher queries for graph traversal

**When to Enable:**
- Advanced reasoning over claim networks
- Multi-hop evidence chains
- Knowledge graph export

### OpenSearch (Advanced Search)

**Full-text search engine** (Elasticsearch fork) for corpus queries.

**Features:**
- BM25 ranking for keyword search
- Hybrid search: combine BM25 + vector similarity
- Faceted search by source, date, entities
- Real-time indexing

**Integration:**
- Docker service: `opensearchproject/opensearch:2.x`
- Python client: `opensearch-py`
- Indices: `corpus`, `claims`, `evidence`

**When to Enable:**
- Large corpus (>100k documents)
- Complex query requirements
- User-facing search interface

### Tesseract (OCR)

**Optical character recognition** for extracting text from images and scanned PDFs.

**Use Cases:**
- Ingest scanned documents into corpus
- Extract text from screenshots and memes
- Preprocess image-based evidence

**Integration:**
- Docker service: Custom Tesseract container
- Python wrapper: `pytesseract`
- Preprocessing: `Pillow`, `pdf2image`

**When to Enable:**
- Corpus includes image-based sources
- OCR required for evidence extraction

---

## Development Tools

### Task Runner: Taskfile (go-task)

**Modern task runner** replacing Makefiles with YAML-based task definitions.

**Installation:**
```bash
# Via package manager or direct download
brew install go-task/tap/go-task  # macOS
choco install go-task             # Windows
# Or download from https://taskfile.dev/installation/
```

**Complete Taskfile.yml Example:**

```yaml
version: '3'

vars:
  PYTHON: uv run python
  PYTEST: uv run pytest
  RUFF: uv run ruff
  MYPY: uv run mypy
  DOCKER_COMPOSE: docker compose

tasks:
  # Setup and Installation
  setup:
    desc: Initialize project and install dependencies
    cmds:
      - uv venv
      - uv pip install -e ".[dev]"
      - uv pip compile pyproject.toml -o requirements.txt
      - cmd: echo "Setup complete! Run 'task dev' to start services."
        silent: true

  install:
    desc: Install dependencies from lock file
    cmds:
      - uv pip sync requirements.txt

  # Development Services
  dev:
    desc: Start all development services
    cmds:
      - '{{.DOCKER_COMPOSE}} up -d'
      - cmd: echo "Services started. API: http://localhost:8000, Frontend: http://localhost:3000"
        silent: true

  dev:api:
    desc: Start API service only
    cmds:
      - '{{.DOCKER_COMPOSE}} up -d postgres redis'
      - '{{.PYTHON}} -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000'

  dev:frontend:
    desc: Start frontend development server
    dir: frontend
    cmds:
      - npm run dev

  stop:
    desc: Stop all services
    cmds:
      - '{{.DOCKER_COMPOSE}} down'

  restart:
    desc: Restart all services
    cmds:
      - task: stop
      - task: dev

  # Testing
  test:
    desc: Run all tests with coverage
    cmds:
      - '{{.PYTEST}} --cov=api --cov=ml --cov-report=html --cov-report=term'

  test:unit:
    desc: Run unit tests only
    cmds:
      - '{{.PYTEST}} tests/unit -v'

  test:integration:
    desc: Run integration tests only
    cmds:
      - '{{.PYTEST}} tests/integration -v'

  test:watch:
    desc: Run tests in watch mode
    cmds:
      - '{{.PYTEST}} -f tests/'

  # Code Quality
  lint:
    desc: Run all linters
    cmds:
      - task: lint:python
      - task: lint:docs

  lint:python:
    desc: Run Python linters
    cmds:
      - '{{.RUFF}} check .'
      - cmd: echo "Python linting complete"
        silent: true

  lint:docs:
    desc: Run Markdown linters
    cmds:
      - uv run pymarkdownlnt scan docs/
      - cmd: echo "Documentation linting complete"
        silent: true

  format:
    desc: Format all code
    cmds:
      - '{{.RUFF}} format .'
      - cmd: echo "Code formatting complete"
        silent: true

  format:check:
    desc: Check code formatting without modifying files
    cmds:
      - '{{.RUFF}} format --check .'

  type-check:
    desc: Run static type checking
    cmds:
      - '{{.MYPY}} api/ ml/'

  # Database Operations
  db:migrate:
    desc: Run database migrations
    cmds:
      - '{{.PYTHON}} -m alembic upgrade head'

  db:reset:
    desc: Reset database (WARNING: destructive)
    cmds:
      - '{{.DOCKER_COMPOSE}} down -v postgres'
      - '{{.DOCKER_COMPOSE}} up -d postgres'
      - task: db:migrate

  db:shell:
    desc: Open PostgreSQL shell
    cmds:
      - '{{.DOCKER_COMPOSE}} exec postgres psql -U truthgraph -d truthgraph'

  # Corpus Management
  corpus:load:
    desc: Load corpus from Parquet files
    cmds:
      - '{{.PYTHON}} -m scripts.load_corpus --path data/corpus'

  corpus:embed:
    desc: Generate embeddings for corpus
    cmds:
      - '{{.PYTHON}} -m ml.embeddings --corpus data/corpus --output data/faiss_indices

  corpus:index:
    desc: Build FAISS indices
    cmds:
      - '{{.PYTHON}} -m ml.build_index --input data/corpus --output data/faiss_indices

  # Documentation
  docs:build:
    desc: Build Sphinx documentation
    dir: docs
    cmds:
      - uv run sphinx-build -b html source build/html
      - cmd: echo "Documentation built at docs/build/html/index.html"
        silent: true

  docs:serve:
    desc: Serve documentation locally
    dir: docs
    cmds:
      - uv run python -m http.server 8080 -d build/html

  docs:clean:
    desc: Clean documentation build artifacts
    cmds:
      - rm -rf docs/build/

  # Cleanup
  clean:
    desc: Remove build artifacts and cache files
    cmds:
      - rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__
      - rm -rf htmlcov .coverage
      - rm -rf build/ dist/ *.egg-info
      - find . -type d -name "__pycache__" -exec rm -rf {} +
      - cmd: echo "Cleanup complete"
        silent: true

  clean:all:
    desc: Remove all generated files including data and models
    cmds:
      - task: clean
      - '{{.DOCKER_COMPOSE}} down -v'
      - rm -rf data/models data/faiss_indices
      - cmd: echo "Full cleanup complete (data preserved in data/corpus)"
        silent: true

  # CI/CD Simulation
  ci:
    desc: Run full CI pipeline locally
    cmds:
      - task: lint
      - task: type-check
      - task: test
      - cmd: echo "CI pipeline complete"
        silent: true

  # Model Management
  models:download:
    desc: Download and cache ML models
    cmds:
      - '{{.PYTHON}} -m scripts.download_models'

  # Utility
  logs:
    desc: Show logs from all services
    cmds:
      - '{{.DOCKER_COMPOSE}} logs -f'

  logs:api:
    desc: Show API logs only
    cmds:
      - '{{.DOCKER_COMPOSE}} logs -f api'

  shell:
    desc: Open Python shell with project context
    cmds:
      - '{{.PYTHON}} -i -m scripts.shell'

  check:
    desc: Run all checks (lint, type-check, test)
    cmds:
      - task: lint
      - task: type-check
      - task: test
```

**Usage:**
```bash
task setup           # Initialize project
task dev             # Start all services
task test            # Run tests with coverage
task lint            # Check code quality
task ci              # Run full CI pipeline locally
```

### Linting: ruff (Python), pymarkdownlnt (Markdown)

**ruff**: Extremely fast Python linter (10-100x faster than Flake8).

**Features:**
- Replaces Flake8, isort, pyupgrade, and more
- Configurable via `pyproject.toml`
- Auto-fix for many rule violations
- 500+ rules from popular linters

**Configuration:**
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line too long
```

**pymarkdownlnt**: Markdown linting for documentation consistency.

**Rules:**
- Heading styles and structure
- Link validity
- Code block formatting
- Consistent list styles

### Formatting: ruff format

**ruff format**: Fast Python code formatter (Black-compatible).

**Features:**
- 30x faster than Black
- Near-identical output to Black
- Integrated with ruff linter
- No config needed (opinionated)

**Usage:**
```bash
ruff format .           # Format all files
ruff format --check .   # Check without modifying
```

### Documentation: Sphinx

**Sphinx**: Documentation generator for Python projects.

**Formats:**
- HTML for web hosting (GitHub Pages, Read the Docs)
- PDF via LaTeX
- Markdown rendering with MyST

**Extensions:**
- `sphinx.ext.autodoc`: Generate docs from docstrings
- `sphinx.ext.napoleon`: Support Google/NumPy docstring styles
- `sphinx-autodoc-typehints`: Type hint rendering
- `myst-parser`: Markdown support

**Structure:**
```
docs/
  source/
    conf.py
    index.rst
    api/
    guides/
    roadmap/
```

### Testing: pytest

**pytest**: Modern Python testing framework.

**Features:**
- Simple test discovery and execution
- Fixtures for setup/teardown
- Parametrized tests
- Plugins: coverage, asyncio, docker

**Structure:**
```
tests/
  unit/
    test_embeddings.py
    test_nli.py
  integration/
    test_api.py
    test_corpus.py
  conftest.py  # Shared fixtures
```

**Key Plugins:**
- `pytest-cov`: Code coverage reporting
- `pytest-asyncio`: Test async functions
- `pytest-docker`: Spin up containers for tests

### Type Checking: mypy

**mypy**: Static type checker for Python.

**Benefits:**
- Catch type errors before runtime
- Improve IDE autocomplete
- Document function signatures
- Gradual typing (opt-in)

**Configuration:**
```toml
[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

---

## Project Structure

### Recommended Directory Layout

```
truthgraph/
├── api/                      # FastAPI backend
│   ├── main.py
│   ├── routers/
│   ├── models/               # Pydantic models
│   ├── services/             # Business logic
│   └── dependencies.py
├── frontend/                 # React frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── ml/                       # ML pipelines and models
│   ├── embeddings.py
│   ├── nli.py
│   ├── retrieval.py
│   └── inference.py
├── data/                     # Local data (gitignored)
│   ├── corpus/               # Parquet files
│   ├── models/               # Hugging Face cache
│   ├── faiss_indices/
│   └── postgres/             # PostgreSQL data
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docs/
│   ├── source/
│   └── roadmap/
├── docker/
│   ├── api.Dockerfile
│   └── frontend.Dockerfile
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── Taskfile.yml
└── README.md
```

### Docker Volume Mappings

**Development:**
```yaml
volumes:
  - ./api:/app/api              # Hot reload for API
  - ./data/postgres:/var/lib/postgresql/data
  - ./data/models:/root/.cache/huggingface
  - ./data/corpus:/data/corpus
  - ./data/faiss_indices:/data/faiss_indices
```

**Production:**
- Named volumes for databases
- Read-only mounts for code
- Separate volume for logs

### Configuration Management

**Environment Variables:**
- `.env` file for local overrides (gitignored)
- `.env.example` template committed to repo
- Docker Compose reads `.env` automatically

**Complete .env.example:**

```bash
# =============================================================================
# TruthGraph Configuration
# =============================================================================
# Copy this file to .env and adjust values as needed for local development
# See docs/roadmap/v1/tech_stack_and_tooling.md for detailed configuration guide

# =============================================================================
# Application Settings
# =============================================================================
ENV=development  # Options: development, production, test
DEBUG=true
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# =============================================================================
# API Configuration
# =============================================================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=true  # Auto-reload on code changes (development only)

# CORS Settings (adjust for production)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# =============================================================================
# Database Configuration
# =============================================================================
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme_secure_password  # CHANGE IN PRODUCTION

# Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# Database URL (auto-constructed if not set)
# DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# =============================================================================
# Redis Configuration
# =============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Leave empty for no password
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}

# Redis Cache Settings
CACHE_TTL=3600  # Cache time-to-live in seconds
CACHE_PREFIX=truthgraph:

# =============================================================================
# Machine Learning Models
# =============================================================================
# Model Cache Directory (where Hugging Face models are stored)
MODEL_CACHE_DIR=/root/.cache/huggingface
HF_HOME=${MODEL_CACHE_DIR}

# Embedding Model
EMBEDDING_MODEL=facebook/contriever
EMBEDDING_DIM=768
EMBEDDING_BATCH_SIZE=32

# NLI Model (Natural Language Inference)
NLI_MODEL=microsoft/deberta-v3-base
NLI_BATCH_SIZE=16

# Model Loading
MODEL_DEVICE=cpu  # Options: cpu, cuda, mps (for Apple Silicon)
MODEL_PRECISION=fp32  # Options: fp32, fp16, bf16

# FAISS Index Settings
FAISS_INDEX_TYPE=IVFFlat  # Options: Flat, IVFFlat, HNSW
FAISS_NLIST=100  # Number of clusters for IVF indices
FAISS_NPROBE=10  # Number of clusters to search

# =============================================================================
# Corpus Configuration
# =============================================================================
CORPUS_DIR=/data/corpus
CORPUS_FORMAT=parquet
MAX_CORPUS_SIZE_GB=100

# Retrieval Settings
TOP_K_RETRIEVAL=100  # Number of candidates to retrieve
TOP_K_RERANK=10     # Number of results after reranking

# =============================================================================
# Optional Services
# =============================================================================
# Neo4j Graph Database (disabled by default)
NEO4J_ENABLED=false
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme_neo4j_password

# OpenSearch (disabled by default)
OPENSEARCH_ENABLED=false
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=changeme_opensearch_password
OPENSEARCH_URL=https://${OPENSEARCH_USER}:${OPENSEARCH_PASSWORD}@${OPENSEARCH_HOST}:${OPENSEARCH_PORT}

# Tesseract OCR (disabled by default)
TESSERACT_ENABLED=false
TESSERACT_LANG=eng
TESSERACT_DPI=300

# =============================================================================
# Frontend Configuration
# =============================================================================
FRONTEND_PORT=3000
VITE_API_URL=http://localhost:8000

# =============================================================================
# Security & Authentication
# =============================================================================
# Secret key for JWT tokens (generate with: openssl rand -hex 32)
SECRET_KEY=changeme_your_secret_key_here_use_openssl_rand_hex_32

# JWT Settings
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# =============================================================================
# Task Queue (if using Celery/RQ)
# =============================================================================
TASK_QUEUE_ENABLED=false
TASK_QUEUE_BROKER=${REDIS_URL}
TASK_QUEUE_BACKEND=${REDIS_URL}

# =============================================================================
# Monitoring & Observability
# =============================================================================
# Logging
LOG_FORMAT=json  # Options: json, text
LOG_FILE=/var/log/truthgraph/app.log

# Metrics (if using Prometheus)
METRICS_ENABLED=false
METRICS_PORT=9090

# Sentry (Error tracking)
SENTRY_ENABLED=false
SENTRY_DSN=

# =============================================================================
# Development Tools
# =============================================================================
# Enable development features
DEV_MODE=true
HOT_RELOAD=true

# Profiling
PROFILE_ENABLED=false

# =============================================================================
# Testing Configuration
# =============================================================================
TEST_DATABASE_URL=postgresql://truthgraph:test@localhost:5433/truthgraph_test
TEST_REDIS_URL=redis://localhost:6380/0

# =============================================================================
# Docker Volume Paths (for development)
# =============================================================================
DATA_DIR=./data
MODELS_DIR=${DATA_DIR}/models
CORPUS_DIR=${DATA_DIR}/corpus
INDICES_DIR=${DATA_DIR}/faiss_indices
POSTGRES_DATA_DIR=${DATA_DIR}/postgres
```

---

## Development Workflow

### Setting Up Local Environment

**Prerequisites:**
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Task (`brew install go-task` or equivalent)
- Git

**Initial Setup:**
```bash
# Clone repository
git clone https://github.com/your-org/truthgraph.git
cd truthgraph

# Create .env from template
cp .env.example .env

# Install dependencies
task setup

# Start services
task dev

# Run migrations (if applicable)
task migrate

# Load sample corpus
task corpus:load
```

**Development Loop:**
1. Make code changes (hot reload enabled for API and frontend)
2. Run tests: `task test`
3. Check formatting: `task lint`
4. Commit changes
5. CI runs full test suite

### Running with Taskfile

**Common Commands:**
```bash
task dev              # Start all services
task dev:api          # Start API only
task dev:frontend     # Start frontend only

task test             # Run all tests
task test:unit        # Unit tests only
task test:integration # Integration tests only

task lint             # Run linters
task format           # Format code
task type-check       # Run mypy

task docs:build       # Build Sphinx docs
task docs:serve       # Serve docs locally

task clean            # Remove build artifacts
task reset            # Reset database and volumes
```

**Custom Tasks:**
Add project-specific tasks to `Taskfile.yml`:
```yaml
corpus:load:
  desc: Load corpus from Parquet files
  cmds:
    - uv run python -m scripts.load_corpus --path data/corpus

embeddings:build:
  desc: Generate embeddings for corpus
  cmds:
    - uv run python -m ml.embeddings --corpus data/corpus --output data/faiss_indices
```

### Testing Strategy

**Levels:**
1. **Unit Tests**: Test individual functions and classes
   - Fast, no external dependencies
   - Mock databases and ML models
   - Target: >80% coverage

2. **Integration Tests**: Test component interactions
   - Use test database (Docker)
   - Real models (small/cached)
   - Test API endpoints end-to-end

3. **E2E Tests** (optional): Test full user workflows
   - Selenium/Playwright for frontend
   - Full stack running in Docker

**Running Tests:**
```bash
pytest                          # All tests
pytest tests/unit               # Unit only
pytest -k "test_embeddings"     # Match pattern
pytest --cov=api --cov-report=html  # Coverage report
```

### Documentation Generation

**Build Docs:**
```bash
task docs:build
# Output: docs/build/html/index.html
```

**Auto-rebuild on Changes:**
```bash
sphinx-autobuild docs/source docs/build/html
```

**Hosting:**
- **Read the Docs**: Automatic builds from GitHub
- **GitHub Pages**: Deploy from `gh-pages` branch
- **Local**: `python -m http.server -d docs/build/html`

---

## Dependencies Management

### Using uv for Python Packages

**Why uv?**
- Faster than pip (10-100x for large projects)
- Better dependency resolution
- Built-in virtual environment management
- Lock file generation for reproducibility

**Workflow:**

**1. Define dependencies in `pyproject.toml`:**
```toml
[project]
name = "truthgraph"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "redis>=5.0.0",
    "transformers>=4.35.0",
    "sentence-transformers>=2.2.0",
    "faiss-cpu>=1.7.4",
    "pyarrow>=14.0.0",
    "spacy>=3.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

**2. Create virtual environment and install:**
```bash
uv venv                 # Create .venv/
uv pip install -e .     # Install project
uv pip install -e ".[dev]"  # Include dev dependencies
```

**3. Generate lock file:**
```bash
uv pip compile pyproject.toml -o requirements.txt
```

**4. Install from lock file (CI/production):**
```bash
uv pip sync requirements.txt
```

### pyproject.toml Structure

**Complete Example:**
```toml
[project]
name = "truthgraph"
version = "0.1.0"
description = "Local-first fact-checking system with ML-powered claim verification"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]
requires-python = ">=3.11"
keywords = ["fact-checking", "nlp", "machine-learning", "truth-verification"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    # Core API
    "fastapi>=0.104.0,<0.110.0",
    "uvicorn[standard]>=0.24.0,<0.30.0",
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0",
    "python-multipart>=0.0.6",  # For file uploads

    # Database
    "sqlalchemy>=2.0.0,<3.0.0",
    "alembic>=1.12.0",  # Database migrations
    "psycopg2-binary>=2.9.0,<3.0.0",
    "pgvector>=0.2.0,<0.3.0",
    "redis>=5.0.0,<6.0.0",

    # ML/NLP
    "transformers>=4.35.0,<5.0.0",
    "sentence-transformers>=2.2.0,<3.0.0",
    "torch>=2.1.0,<3.0.0",
    "faiss-cpu>=1.7.4,<2.0.0",  # Use faiss-gpu for GPU support
    "spacy>=3.7.0,<4.0.0",
    "tokenizers>=0.15.0",

    # Data Processing
    "pyarrow>=14.0.0,<15.0.0",
    "pandas>=2.1.0,<3.0.0",
    "numpy>=1.24.0,<2.0.0",
    "duckdb>=0.9.0",  # Fast analytics on Parquet

    # Utilities
    "python-dotenv>=1.0.0",  # Environment variable loading
    "httpx>=0.25.0",  # Async HTTP client
    "pyyaml>=6.0.0",  # YAML parsing
    "tenacity>=8.2.0",  # Retry logic
    "loguru>=0.7.0",  # Enhanced logging
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.4.0,<8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-docker>=2.0.0",
    "pytest-mock>=3.12.0",
    "httpx>=0.25.0",  # For TestClient

    # Code Quality
    "ruff>=0.1.6,<0.2.0",
    "mypy>=1.7.0,<2.0.0",
    "pymarkdownlnt>=0.9.0",

    # Type Stubs
    "types-redis>=4.6.0",
    "types-pyyaml>=6.0.0",

    # Documentation
    "sphinx>=7.2.0",
    "sphinx-rtd-theme>=2.0.0",
    "myst-parser>=2.0.0",
    "sphinx-autodoc-typehints>=1.25.0",

    # Utilities
    "ipython>=8.17.0",
    "ipdb>=0.13.0",  # Debugger
]

graph = [
    "neo4j>=5.14.0,<6.0.0",
]

search = [
    "opensearch-py>=2.4.0,<3.0.0",
]

ocr = [
    "pytesseract>=0.3.10",
    "pdf2image>=1.16.0",
    "pillow>=10.1.0",
]

# All optional dependencies combined
all = [
    "truthgraph[graph,search,ocr]",
]

[project.urls]
Homepage = "https://github.com/your-org/truthgraph"
Documentation = "https://truthgraph.readthedocs.io"
Repository = "https://github.com/your-org/truthgraph"
Issues = "https://github.com/your-org/truthgraph/issues"

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "."}
packages = ["api", "ml"]

[tool.setuptools.package-data]
api = ["py.typed"]
ml = ["py.typed"]

# Ruff Configuration
[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = [
    ".venv",
    "data",
    "docs",
    "__pycache__",
]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "T10",    # flake8-debugger
    "EM",     # flake8-errmsg
    "ISC",    # flake8-implicit-str-concat
    "ICN",    # flake8-import-conventions
    "PIE",    # flake8-pie
    "PT",     # flake8-pytest-style
    "Q",      # flake8-quotes
    "RET",    # flake8-return
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "ARG",    # flake8-unused-arguments
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate
    "PL",     # pylint
    "RUF",    # ruff-specific rules
]

ignore = [
    "E501",   # Line too long (handled by formatter)
    "PLR0913", # Too many arguments
    "PLR0911", # Too many return statements
    "PLR2004", # Magic value used in comparison
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ARG001",  # Unused function argument (fixtures)
    "S101",    # Use of assert detected
]

[tool.ruff.lint.isort]
known-first-party = ["api", "ml"]
force-single-line = false
lines-after-imports = 2

# MyPy Configuration
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = "normal"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = [
    "transformers.*",
    "sentence_transformers.*",
    "faiss.*",
    "spacy.*",
]
ignore_missing_imports = true

# Pytest Configuration
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--showlocals",
]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
    "gpu: Tests requiring GPU",
]
asyncio_mode = "auto"

# Coverage Configuration
[tool.coverage.run]
source = ["api", "ml"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
precision = 2
show_missing = true
```

### Lock Files and Reproducibility

**Benefits:**
- **Deterministic builds**: Same dependencies across all environments
- **Security**: Pin exact versions with known vulnerabilities
- **Debugging**: Reproduce exact environment from bug reports

**Best Practices:**
1. Commit `requirements.txt` (lock file) to Git
2. Regenerate lock file when updating dependencies
3. Use lock file in Dockerfile for consistent container builds
4. Document update process in CONTRIBUTING.md

**Update Workflow:**
```bash
# Update specific package
uv pip install --upgrade fastapi
uv pip compile pyproject.toml -o requirements.txt

# Update all packages
uv pip install --upgrade-package "*"
uv pip compile pyproject.toml -o requirements.txt

# Test and commit
task test
git add requirements.txt
git commit -m "deps: update fastapi to 0.105.0"
```

---

## Resource Requirements

### Minimum System Requirements

**For Development:**
- **CPU**: 4 cores (Intel i5/AMD Ryzen 5 or equivalent)
- **RAM**: 16 GB
- **Storage**: 50 GB free space (SSD recommended)
- **OS**: Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+)
- **Docker**: Docker Desktop 4.0+ or Docker Engine 20.10+

**Breakdown:**
- Base system: 4 GB
- Docker services: 6 GB
  - PostgreSQL: 1 GB
  - Redis: 500 MB
  - API: 2 GB
  - Frontend: 500 MB
  - ML models in memory: 2 GB
- Development tools: 2 GB
- Working memory: 4 GB

### Recommended System Requirements

**For Development:**
- **CPU**: 8+ cores (Intel i7/AMD Ryzen 7 or equivalent)
- **RAM**: 32 GB
- **Storage**: 100 GB free space on SSD
- **GPU**: NVIDIA GPU with 8+ GB VRAM (optional, for faster inference)
- **OS**: Same as minimum

**Breakdown:**
- Base system: 4 GB
- Docker services: 8 GB
- Multiple ML models loaded: 8 GB
- Large corpus in memory: 8 GB
- Development tools and IDE: 4 GB

**For Production (single node):**
- **CPU**: 16+ cores
- **RAM**: 64 GB
- **Storage**: 500 GB SSD (NVMe recommended)
- **GPU**: NVIDIA GPU with 16+ GB VRAM (for production workloads)
- **Network**: 1 Gbps+

### Storage Requirements

**By Component:**
- **PostgreSQL database**: 5-20 GB (depends on corpus size and claim history)
- **ML models cache**: 5-10 GB
  - DeBERTa-v3-base: ~1.5 GB
  - Contriever: ~500 MB
  - spaCy models: ~500 MB
  - Tokenizers and configs: ~500 MB
- **FAISS indices**: 1-10 GB (depends on corpus size and index type)
  - Rule of thumb: ~4 bytes per dimension per vector
  - For 1M documents with 768-dim embeddings: ~3 GB
- **Corpus (Parquet)**: Variable
  - 100k documents: ~1-2 GB
  - 1M documents: ~10-20 GB
  - 10M documents: ~100-200 GB
- **Docker images**: 10-15 GB
- **Logs and temporary files**: 5-10 GB

**Total Estimated:**
- **Minimum setup**: 50 GB
- **Recommended setup**: 100 GB
- **Large corpus (1M+ docs)**: 200+ GB

### Network Requirements

**Development:**
- **Bandwidth**: Standard broadband (10+ Mbps)
- **Initial setup**: 5-10 GB download (Docker images, ML models)
- **Ongoing**: Minimal (mainly for package updates)

**Production:**
- **Bandwidth**: 100+ Mbps recommended
- **Latency**: <50ms for API responses
- **Concurrent users**: Scale horizontally for >100 concurrent users

### GPU Recommendations

**Development (optional):**
- Any NVIDIA GPU with CUDA support
- Minimum 6 GB VRAM
- Use for faster model inference and batch processing

**Production:**
- NVIDIA A100 (40-80 GB): Best for large-scale inference
- NVIDIA A10 (24 GB): Good balance of cost and performance
- NVIDIA T4 (16 GB): Budget-friendly option

**Note:** CPU-only deployment is fully supported but 5-10x slower for inference.

---

## Troubleshooting Common Issues

### Installation and Setup Issues

**1. Docker Compose fails to start services**

**Symptom:** `docker compose up` fails with port conflicts or container errors.

**Solutions:**
```bash
# Check if ports are already in use
netstat -an | grep "5432\|6379\|8000\|3000"

# Stop conflicting services
sudo systemctl stop postgresql
sudo systemctl stop redis

# Reset Docker state
docker compose down -v
docker system prune -af

# Restart Docker daemon
sudo systemctl restart docker  # Linux
# Or restart Docker Desktop on Windows/Mac
```

**2. uv installation or Python environment issues**

**Symptom:** `uv: command not found` or virtual environment creation fails.

**Solutions:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to .bashrc or .zshrc)
export PATH="$HOME/.cargo/bin:$PATH"

# Create fresh virtual environment
rm -rf .venv
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
```

**3. PostgreSQL connection refused**

**Symptom:** API fails to connect to PostgreSQL.

**Solutions:**
```bash
# Check if PostgreSQL container is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Verify environment variables
cat .env | grep POSTGRES

# Restart PostgreSQL
docker compose restart postgres

# Connect manually to verify
docker compose exec postgres psql -U truthgraph -d truthgraph
```

### ML Model Issues

**4. Model download fails or times out**

**Symptom:** Transformers fails to download models from Hugging Face.

**Solutions:**
```bash
# Set longer timeout
export HF_HUB_TIMEOUT=600

# Download models manually
python -c "
from transformers import AutoModel
model = AutoModel.from_pretrained('facebook/contriever')
"

# Use cached models
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

**5. Out of memory errors during inference**

**Symptom:** `RuntimeError: CUDA out of memory` or system freezes.

**Solutions:**
```bash
# Reduce batch size in .env
EMBEDDING_BATCH_SIZE=8
NLI_BATCH_SIZE=4

# Use CPU instead of GPU
MODEL_DEVICE=cpu

# Use half precision (if GPU supports it)
MODEL_PRECISION=fp16

# Limit PyTorch threads
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

**6. FAISS index build fails**

**Symptom:** `RuntimeError: faiss index training failed`.

**Solutions:**
```bash
# Use simpler index type
FAISS_INDEX_TYPE=Flat

# Reduce index parameters
FAISS_NLIST=50

# Build index in chunks
python -m ml.build_index --chunk-size 10000
```

### Performance Issues

**7. Slow API response times**

**Symptom:** API requests take >5 seconds.

**Diagnostics:**
```bash
# Check resource usage
docker stats

# Profile API endpoint
time curl http://localhost:8000/api/v1/claims/analyze
```

**Solutions:**
- Enable Redis caching
- Preload models on startup
- Use FAISS indices instead of brute-force search
- Increase API workers: `API_WORKERS=8`
- Add connection pooling for database

**8. High memory usage**

**Symptom:** System runs out of memory or swaps heavily.

**Solutions:**
```bash
# Limit Docker memory
docker compose down
# Add to docker-compose.yml services:
#   mem_limit: 8g

# Unload unused models
# Implement lazy loading in code

# Use smaller models
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Development Workflow Issues

**9. Hot reload not working**

**Symptom:** Code changes don't reflect in running API.

**Solutions:**
```bash
# Verify volume mounts in docker-compose.yml
docker compose config

# Restart with logs
docker compose restart api
docker compose logs -f api

# Check file watcher limits (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**10. Tests fail with database errors**

**Symptom:** `pytest` fails with "database does not exist".

**Solutions:**
```bash
# Create test database
docker compose exec postgres createdb -U truthgraph truthgraph_test

# Use separate test database URL
export TEST_DATABASE_URL=postgresql://truthgraph:test@localhost:5433/truthgraph_test

# Reset test database
task db:reset
pytest
```

### Docker-Specific Issues

**11. Docker build fails with "no space left on device"**

**Solutions:**
```bash
# Clean up Docker resources
docker system prune -af --volumes

# Check Docker disk usage
docker system df

# Increase Docker Desktop disk limit (Mac/Windows)
# Docker Desktop → Settings → Resources → Disk image size
```

**12. Permission denied errors in Docker volumes**

**Symptom:** Container cannot write to mounted volumes.

**Solutions (Linux):**
```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) data/

# Or run containers with user ID
# Add to docker-compose.yml:
#   user: "${UID}:${GID}"
```

---

## Alternative Choices Considered

This section explains key technology decisions and why certain tools were chosen over alternatives.

### Package Manager: uv vs pip/poetry/pipenv

**Chosen: uv**

**Alternatives considered:**
- **pip + pip-tools**: Traditional standard, but slow dependency resolution
- **Poetry**: Popular, feature-rich, but slower and larger dependency tree
- **Pipenv**: Good developer experience but slower than uv
- **conda**: Great for scientific packages but heavyweight and opinionated

**Why uv?**
- **Performance**: 10-100x faster than pip, crucial for CI/CD
- **Simplicity**: Single tool for venvs and packages
- **Compatibility**: Works with standard `pyproject.toml`, easy migration
- **Modern**: Built in Rust, actively developed by Astral (ruff creators)
- **Lock files**: Built-in support for reproducible builds

**Trade-offs:**
- Newer tool (less mature than pip/poetry)
- Smaller ecosystem of plugins
- Some edge cases with complex dependency trees

### Task Runner: Taskfile vs Make/Just/npm scripts

**Chosen: Taskfile (go-task)**

**Alternatives considered:**
- **Make**: Universal, but arcane syntax and platform inconsistencies
- **Just**: Modern Make alternative, good but less feature-rich
- **npm scripts**: Simple but limited to Node.js ecosystem
- **Invoke (Python)**: Python-native but requires Python setup first
- **Bash scripts**: Maximum flexibility but poor discoverability

**Why Taskfile?**
- **YAML syntax**: Easy to read and write, no tabs/spaces issues
- **Cross-platform**: Works identically on Windows/Mac/Linux
- **Variables and templating**: Clean task composition
- **Dependencies**: Task prerequisites and parallel execution
- **Documentation**: Built-in task descriptions (`task --list`)

**Trade-offs:**
- Requires separate installation (not bundled with OS)
- Less universal than Make
- Smaller community than npm scripts

### API Framework: FastAPI vs Flask/Django/aiohttp

**Chosen: FastAPI**

**Alternatives considered:**
- **Flask**: Mature, simple, but synchronous and manual validation
- **Django + DRF**: Feature-complete but heavyweight for API-only
- **aiohttp**: Fast async but low-level, requires more boilerplate
- **Tornado**: Good async support but older ecosystem
- **Starlette**: FastAPI's foundation, but FastAPI adds useful abstractions

**Why FastAPI?**
- **Performance**: Async/await support, comparable to Node.js/Go
- **Developer experience**: Automatic OpenAPI docs, type hints, IDE support
- **Validation**: Pydantic models prevent entire class of bugs
- **Modern**: Built for Python 3.7+ with type hints as first-class feature
- **Ecosystem**: Growing rapidly, excellent community

**Trade-offs:**
- Newer than Flask (less battle-tested)
- Learning curve for async programming
- Fewer plugins than Django ecosystem

### Vector Database: pgvector vs Pinecone/Weaviate/Qdrant

**Chosen: pgvector (PostgreSQL extension)**

**Alternatives considered:**
- **Pinecone**: Managed, scalable, but cloud-only (violates local-first)
- **Weaviate**: Feature-rich, but separate service to manage
- **Qdrant**: Fast, modern, but additional complexity
- **Milvus**: Scalable, but heavy and complex for v1
- **ChromaDB**: Simple, but less mature and limited scale
- **FAISS**: Chosen as complement for speed, but not a full database

**Why pgvector?**
- **Simplicity**: One database for relational and vector data
- **Local-first**: No external dependencies or cloud services
- **ACID guarantees**: Transactions, consistency, reliability
- **Mature**: PostgreSQL is battle-tested over 25+ years
- **Cost**: No separate vector DB licensing or hosting
- **SQL integration**: Join vector similarity with relational queries

**Trade-offs:**
- Performance: Slower than specialized vector DBs at scale (>10M vectors)
- Features: Less advanced filtering and metadata search
- Scaling: Requires PostgreSQL scaling strategies

**Note:** FAISS used alongside pgvector for speed-critical retrieval.

### Linter: ruff vs Flake8/pylint/Black

**Chosen: ruff (for both linting and formatting)**

**Alternatives considered:**
- **Flake8 + Black + isort**: Traditional stack, proven but slow
- **pylint**: Comprehensive but very slow and opinionated
- **Black**: Popular formatter but Python-based (slower)
- **autopep8**: Conservative formatter but limited rules

**Why ruff?**
- **Speed**: Written in Rust, 10-100x faster than Python linters
- **All-in-one**: Replaces Flake8, isort, pyupgrade, and others
- **Compatibility**: Black-compatible formatting
- **Active development**: Rapidly improving, backed by Astral
- **Configuration**: Simple, works with pyproject.toml

**Trade-offs:**
- Newer tool (less mature than Black/Flake8)
- Some advanced pylint checks not implemented
- Occasional bugs in rapidly evolving codebase

### Container Orchestration: Docker Compose vs Kubernetes/Nomad

**Chosen: Docker Compose**

**Alternatives considered:**
- **Kubernetes**: Industry standard, but massive overkill for local-first
- **Docker Swarm**: Simpler than K8s but declining ecosystem
- **Nomad**: Good balance but additional tool to learn
- **Podman**: Docker alternative, but less widespread adoption

**Why Docker Compose?**
- **Simplicity**: Single YAML file, easy to understand
- **Local-first**: Perfect for developer machines
- **Universal**: Works identically on all platforms
- **Learning curve**: Gentle, most developers familiar with Docker
- **Transition**: Easy to migrate to K8s later if needed

**Trade-offs:**
- Not designed for production clustering
- Limited scaling capabilities
- No built-in service mesh or advanced networking

### Frontend: React vs Vue/Svelte/Angular

**Chosen: React 18+**

**Alternatives considered:**
- **Vue 3**: Simpler, gentler learning curve
- **Svelte**: Fastest, smallest bundles, compile-time framework
- **Angular**: Enterprise-grade, but heavyweight and opinionated
- **Solid.js**: Modern, React-like but smaller
- **Preact**: Tiny React alternative but smaller ecosystem

**Why React?**
- **Ecosystem**: Largest library of components and tools
- **Talent pool**: Most developers know React
- **Maturity**: Battle-tested in production at scale
- **TypeScript support**: First-class, excellent DX
- **Tooling**: Best dev tools, IDE support, documentation

**Trade-offs:**
- Bundle size larger than Svelte/Preact
- Learning curve for hooks and modern patterns
- Verbosity compared to Vue template syntax

### ML Framework: PyTorch vs TensorFlow/JAX

**Chosen: PyTorch** (via Transformers)

**Alternatives considered:**
- **TensorFlow**: Mature, but more complex API
- **JAX**: Fast, functional, but smaller ecosystem for NLP
- **ONNX Runtime**: Fast inference but requires model conversion

**Why PyTorch?**
- **Hugging Face ecosystem**: Best support for transformers models
- **Pythonic**: Intuitive, feels like NumPy
- **Research to production**: Easy transition
- **Community**: Dominant in NLP research
- **Dynamic graphs**: Easier debugging than TensorFlow

**Trade-offs:**
- Slightly slower than TensorFlow for some workloads
- Larger model files than optimized formats
- Less deployment tooling than TensorFlow Serving

---

## CI/CD Setup Guidance

### GitHub Actions Workflow

**Recommended CI/CD pipeline for TruthGraph projects:**

**File: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"
  UV_VERSION: "0.1.0"

jobs:
  lint:
    name: Lint and Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/uv
            .venv
          key: ${{ runner.os }}-uv-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: |
          uv venv
          uv pip sync requirements.txt

      - name: Run ruff linting
        run: uv run ruff check .

      - name: Run ruff format check
        run: uv run ruff format --check .

      - name: Lint documentation
        run: uv run pymarkdownlnt scan docs/

  type-check:
    name: Type Checking
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/uv
            .venv
          key: ${{ runner.os }}-uv-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: |
          uv venv
          uv pip sync requirements.txt

      - name: Run mypy
        run: uv run mypy api/ ml/

  test:
    name: Test Suite
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: truthgraph
          POSTGRES_PASSWORD: test
          POSTGRES_DB: truthgraph_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/uv
            .venv
          key: ${{ runner.os }}-uv-${{ hashFiles('requirements.txt') }}

      - name: Cache ML models
        uses: actions/cache@v3
        with:
          path: ~/.cache/huggingface
          key: ${{ runner.os }}-huggingface-${{ hashFiles('**/pyproject.toml') }}

      - name: Install dependencies
        run: |
          uv venv
          uv pip sync requirements.txt

      - name: Run tests
        env:
          TEST_DATABASE_URL: postgresql://truthgraph:test@localhost:5432/truthgraph_test
          TEST_REDIS_URL: redis://localhost:6379/0
        run: |
          uv run pytest --cov=api --cov=ml --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  build-docker:
    name: Build Docker Images
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api.Dockerfile
          push: false
          tags: truthgraph-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: docker/frontend.Dockerfile
          push: false
          tags: truthgraph-frontend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### GitLab CI/CD

**File: `.gitlab-ci.yml`**

```yaml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  PYTHON_VERSION: "3.11"
  DOCKER_DRIVER: overlay2

# Cache configuration
.cache_template: &cache_config
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .venv/
      - .cache/uv/

lint:
  stage: lint
  image: python:3.11-slim
  <<: *cache_config
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv venv
    - uv pip sync requirements.txt
  script:
    - uv run ruff check .
    - uv run ruff format --check .
    - uv run pymarkdownlnt scan docs/

type-check:
  stage: lint
  image: python:3.11-slim
  <<: *cache_config
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv venv
    - uv pip sync requirements.txt
  script:
    - uv run mypy api/ ml/

test:
  stage: test
  image: python:3.11-slim
  services:
    - postgres:16
    - redis:7-alpine
  variables:
    POSTGRES_DB: truthgraph_test
    POSTGRES_USER: truthgraph
    POSTGRES_PASSWORD: test
    TEST_DATABASE_URL: postgresql://truthgraph:test@postgres:5432/truthgraph_test
    TEST_REDIS_URL: redis://redis:6379/0
  <<: *cache_config
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv venv
    - uv pip sync requirements.txt
  script:
    - uv run pytest --cov=api --cov=ml --cov-report=xml --cov-report=term
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -f docker/api.Dockerfile -t $CI_REGISTRY_IMAGE/api:$CI_COMMIT_SHA .
    - docker build -f docker/frontend.Dockerfile -t $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA ./frontend
  only:
    - main
    - develop
```

### Pre-commit Hooks

**File: `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=10000']
      - id: check-merge-conflict
      - id: check-toml

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

**Installation:**
```bash
# Install pre-commit
uv pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Continuous Deployment

**Docker Compose for Production:**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: truthgraph-api:${VERSION}
    restart: always
    environment:
      - ENV=production
      - DEBUG=false
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: truthgraph-frontend:${VERSION}
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
```

### Version and Tooling Specifications

**Critical Version Requirements:**

- **Python**: 3.11 or 3.12 (3.11.0+ for best compatibility)
- **PostgreSQL**: 14+ (16+ recommended for best pgvector performance)
- **Redis**: 6+ (7+ recommended)
- **Docker**: 20.10+ (24+ recommended)
- **Docker Compose**: 2.0+ (bundled with Docker Desktop)
- **Node.js**: 18+ LTS (20+ recommended for frontend)

**Tool Versions (locked in pyproject.toml):**
- **FastAPI**: 0.104.0 - 0.110.0
- **Transformers**: 4.35.0 - 5.0.0
- **PyTorch**: 2.1.0 - 3.0.0
- **ruff**: 0.1.6 - 0.2.0
- **pytest**: 7.4.0 - 8.0.0

**Why version locking matters:**
- Reproducible builds across environments
- Prevents breaking changes from automatic updates
- Security: Can track and patch specific versions
- Debugging: Easier to reproduce issues with exact versions

---

## Summary

TruthGraph's tech stack prioritizes:
- **Speed**: uv, ruff, FastAPI, FAISS
- **Reliability**: PostgreSQL, Docker, type checking
- **Simplicity**: Taskfile, pyproject.toml, minimal config
- **Reproducibility**: Lock files, containers, versioned models

This foundation supports rapid iteration while maintaining production-grade quality and local-first operation.
