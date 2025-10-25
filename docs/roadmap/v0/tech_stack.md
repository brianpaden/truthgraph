# TruthGraph v0: Technology Stack

## Executive Summary

This document explains **why we chose each technology** for TruthGraph v0 MVP. Every choice prioritizes simplicity, developer experience, and a clear upgrade path to v1.

**Core Philosophy**: Use proven, modern tools that work well for local-first applications and avoid premature optimization.

---

## Technology Selection Criteria

For v0 MVP, we evaluate technologies based on:

1. **Time to Value**: Can we build quickly? (<5 weeks timeline)
2. **Local-First Suitability**: Works well on developer laptops without cloud dependencies
3. **Developer Experience**: Good documentation, active community, modern tooling
4. **Evolution Path**: Can we upgrade to v1 without rewriting? (50-70% code reuse target)
5. **Resource Efficiency**: Runs on modest hardware (8GB RAM, 4 CPU cores)

---

## Backend Stack

### Python 3.12+

**Why Python?**
- Excellent ML/NLP ecosystem (transformers, sentence-transformers, scikit-learn)
- Fast prototyping for fact-checking logic
- Strong typing support (modern Python with type hints)
- Great for data processing and scientific computing

**Why Python 3.12+?**
- Modern syntax (`|` for unions, match statements, f-string improvements)
- Performance improvements (faster startup, better memory)
- Improved error messages
- Active long-term support (LTS through 2028)

**Alternatives Considered**:
- **TypeScript/Node.js**: Rejected - weaker ML ecosystem, harder to integrate Hugging Face models
- **Rust**: Rejected - slower development, overkill for MVP, steeper learning curve
- **Go**: Rejected - limited ML/NLP libraries

**Evolution to v1**: Same language, no migration needed ✅

---

### uv (Package Manager)

**Why uv?**
- **10-100x faster** than pip/poetry (written in Rust)
- Drop-in replacement for pip, virtualenv, pip-tools
- Simple lockfile format (compatible with pip)
- Modern, actively developed (by Astral, creators of ruff)
- Great for reproducible builds

**Example Speed Comparison**:
```bash
pip install                    # ~30 seconds
poetry install                 # ~45 seconds
uv pip install                 # ~2 seconds
```

**Alternatives Considered**:
- **pip + pip-tools**: Rejected - too slow, manual lockfile management
- **poetry**: Rejected - slow resolver, complex configuration
- **conda**: Rejected - heavyweight, slower, poor compatibility with Docker

**Evolution to v1**: Same tool, no migration needed ✅

---

### FastAPI (Web Framework)

**Why FastAPI?**
- **Modern async support** (when we need it in v1)
- Automatic OpenAPI/Swagger documentation
- Excellent validation with Pydantic
- High performance (on par with Node.js, Go)
- Great developer experience (auto-completion, type hints)
- Perfect for v0 synchronous endpoints AND v1 async endpoints

**Why NOT Flask/Django?**
- Flask: No built-in async support, manual OpenAPI docs
- Django: Too heavyweight for API-only service, slower, admin panel we don't need

**Evolution to v1**: Same framework, add async/await ✅

---

### SQLAlchemy 2.0 (ORM)

**Why SQLAlchemy 2.0?**
- Modern async support (asyncpg driver)
- Best-in-class ORM for Python
- Repository pattern friendly (abstract data access)
- Supports both raw SQL and ORM (flexibility)
- Excellent performance with connection pooling

**Why SQLAlchemy 2.0 Specifically?**
- Unified async/sync API
- Better type hints
- Improved performance
- Modern patterns (no more `session.commit()` in business logic)

**Alternatives Considered**:
- **Raw asyncpg**: Rejected - too low-level, manual query building
- **Tortoise ORM**: Rejected - smaller community, less mature
- **Peewee**: Rejected - no async support, simpler but limited

**Evolution to v1**: Same ORM, same patterns ✅

---

## Database Stack

### PostgreSQL 16 + pgvector

**Why PostgreSQL?**
- **ACID guarantees** (data integrity is critical)
- Excellent JSON support (JSONB for metadata)
- Robust full-text search (GIN indexes)
- pgvector extension for vector similarity search
- Proven at scale (millions of rows, billions of vectors)
- Great tooling (pgAdmin, psql, monitoring)

**Why PostgreSQL 16?**
- Latest stable version (Oct 2023)
- Performance improvements (bulk loading, parallelism)
- Better JSONB indexing
- Improved monitoring

**Why pgvector?**
- Native PostgreSQL extension (no separate vector DB)
- Supports cosine, L2, inner product similarity
- IVFFlat index for fast approximate search
- Good performance for <100K-1M vectors
- One database = simpler architecture

**Alternatives Considered**:
- **MySQL**: Rejected - weaker JSON support, no pgvector equivalent
- **SQLite**: Rejected - no vector extension, single-writer limitation
- **MongoDB**: Rejected - no ACID, harder to reason about, vector search not mature

**Evolution to v1**: Same database, add `tenant_id` columns ✅

---

### Why NO FAISS for v0?

**Decision**: Use pgvector ONLY (defer FAISS to v1)

**Rationale**:
- **Simplicity**: One data store vs two (no sync logic needed)
- **Good Enough**: pgvector handles <100K vectors with <500ms latency
- **Easier Debugging**: One source of truth for data
- **Faster Development**: No index management, rebuilding, etc.

**When to Add FAISS (v1)**:
- Corpus grows >100K vectors
- Search latency >500ms (p95)
- Need exact nearest neighbor guarantees
- User data shows need for performance

**Migration Path**: Add FAISS in v1 with dual-store pattern (like v1 roadmap)

---

## Machine Learning Stack

### Hugging Face Transformers

**Why Transformers Library?**
- De facto standard for NLP models
- 100K+ pre-trained models available
- Excellent documentation
- Active development (Meta, Google, OpenAI contribute)
- Great local caching (no re-downloads)

**Alternatives Considered**:
- **spaCy**: Rejected - limited transformer support, smaller model ecosystem
- **AllenNLP**: Rejected - less maintained, harder to use
- **Custom PyTorch**: Rejected - reinventing the wheel, slower development

**Evolution to v1**: Same library, add model versioning ✅

---

### sentence-transformers (Embeddings)

**Model**: all-MiniLM-L6-v2

**Why sentence-transformers?**
- Purpose-built for semantic similarity
- Pre-trained on massive corpora
- Fast inference (1000+ sentences/second on CPU)
- Small model size (90MB for all-MiniLM-L6-v2)

**Why all-MiniLM-L6-v2?**
- **384 dimensions** (fast, low memory)
- **Good performance** (83.9% on STS benchmark)
- **Fast** (13K sentences/sec on CPU)
- **Small** (90MB model size)
- **Balanced** (best speed/quality trade-off for MVP)

**Model Comparison**:

| Model | Dimensions | Speed (CPU) | Size | STS Score |
|-------|-----------|-------------|------|-----------|
| all-MiniLM-L6-v2 | 384 | 13K sent/s | 90MB | 83.9% |
| all-mpnet-base-v2 | 768 | 3K sent/s | 420MB | 86.8% |
| Contriever | 768 | 2K sent/s | 440MB | 82.5% |
| E5-large | 1024 | 1K sent/s | 1.3GB | 88.1% |

**Decision**: Use all-MiniLM-L6-v2 for v0 (3x faster, 4.6x smaller than alternatives)

**Evolution to v1**: Can swap models via config (model path is configurable) ✅

---

### DeBERTa-v3 (NLI Verification)

**Model**: microsoft/deberta-v3-base (MNLI fine-tuned)

**Why DeBERTa-v3?**
- **Best NLI performance** (90.6% accuracy on MNLI)
- Better than BERT, RoBERTa, ELECTRA
- Disentangled attention mechanism (more nuanced reasoning)
- Available in multiple sizes (base for v0, large for v1)

**Why Base (not Large)?**
- **Faster inference**: 350ms vs 800ms per example
- **Smaller memory**: 440MB vs 1.3GB
- **Good enough**: 88.2% MNLI accuracy (vs 91.0% for large)

**Model Comparison**:

| Model | MNLI Accuracy | Inference Time | Size |
|-------|---------------|----------------|------|
| DeBERTa-v3-base | 88.2% | 350ms | 440MB |
| DeBERTa-v3-large | 91.0% | 800ms | 1.3GB |
| RoBERTa-large | 90.2% | 750ms | 1.2GB |
| BERT-large | 86.7% | 600ms | 1.1GB |

**Decision**: Use DeBERTa-v3-base for v0 (2x faster, acceptable accuracy)

**Evolution to v1**: Swap to large model via config if needed ✅

---

## Frontend Stack

### htmx vs React: The Decision

**TLDR**: For v0, **consider using htmx** instead of React. For v1, **switch to React** when complexity warrants it.

#### Why htmx for v0?

**v0 UI Requirements** (simple):
- Claim submission form
- Claim history list
- Verification results display
- Loading states (<60s processing)
- Error messages

**htmx Advantages for MVP**:

1. **3x Faster Development**: 2 weeks vs 4-5 weeks for same UI
2. **No Build Tooling**: No webpack, npm, babel - just HTML templates
3. **Backend Team Can Build UI**: Python devs already know Jinja2
4. **Smaller Bundle**: 14KB vs 140KB (10x smaller)
5. **Server-Side Rendering**: SEO-friendly, works without JS
6. **Good Enough**: v0 doesn't need complex interactivity

**htmx Example**:
```html
<form hx-post="/api/claims/verify"
      hx-target="#results"
      hx-indicator="#spinner">
  <textarea name="claim_text"></textarea>
  <button>Verify</button>
  <div id="spinner" class="htmx-indicator">Processing...</div>
</form>
<div id="results"></div>
```

**FastAPI returns HTML** (not JSON):
```python
@app.post("/api/claims/verify")
async def verify(claim_text: str = Form(...)):
    result = verify_claim(claim_text)
    return templates.TemplateResponse("verdict.html", {"result": result})
```

#### Why React for v1?

**v1 UI Requirements** (complex):
- Interactive reasoning graph visualization (Cytoscape.js, D3.js)
- Real-time WebSocket updates
- Temporal timeline charts
- Multimodal display (images, PDFs, videos)
- Advanced filtering and search

**React Advantages for v1**:

1. **Rich Component Ecosystem**: Graph libraries, chart libraries, PDF viewers
2. **WebSocket Support**: Clean state management for real-time updates
3. **Type Safety**: TypeScript for complex data structures
4. **State Management**: React Context/Zustand for complex UI state
5. **Better for Complex UX**: Interactive graphs can't be done server-side

**Migration Path**: htmx (v0) → React (v1)
- **Incremental**: Rewrite complex pages only (30-40%)
- **Coexistence**: htmx and React can run side-by-side
- **Effort**: 2-3 weeks to migrate complex pages

#### Decision Matrix

| Criteria | htmx (v0) | React (v0) | Winner |
|----------|-----------|------------|--------|
| Time to MVP | 2 weeks | 4-5 weeks | **htmx (2x faster)** |
| Simplicity | 9/10 | 5/10 | **htmx** |
| Team Skillset | 10/10 (Python) | 4/10 (need frontend) | **htmx** |
| Bundle Size | 14KB | 140KB | **htmx (10x smaller)** |
| Interactivity (v0) | 4/10 | 9/10 | htmx (good enough) |
| Interactivity (v1) | 2/10 | 9/10 | **React (needed)** |
| Graph Viz | 2/10 | 10/10 | **React** |
| Real-time | 4/10 | 9/10 | **React** |

**Recommendation**:
- **v0**: Use htmx (faster, simpler, good enough)
- **v1**: Migrate to React (complexity justifies it)

---

### React 18 + TypeScript (If Not Using htmx)

**Why React?**
- Most popular frontend framework (huge ecosystem)
- Excellent TypeScript support
- Great developer tools (React DevTools)
- Large talent pool
- Component reusability

**Why TypeScript?**
- Type safety (catch bugs at compile time)
- Better IDE support (auto-completion, refactoring)
- Self-documenting code
- Easier collaboration

**Alternatives Considered**:
- **htmx**: Recommended for v0 (see above)
- **Vue**: Rejected - smaller ecosystem, less familiar to team
- **Svelte**: Rejected - cutting-edge but smaller community
- **Vanilla JS**: Rejected - no type safety, harder to maintain

**Evolution to v1**: Same stack (or migrate from htmx) ✅

---

### Vite (Build Tool)

**Why Vite?**
- **Lightning fast** HMR (Hot Module Replacement)
- Modern ESM-based development
- Faster than Webpack (10-100x for dev server start)
- Simple configuration
- Excellent TypeScript support

**Speed Comparison**:
```bash
Webpack dev server start:    15-30 seconds
Vite dev server start:        0.5-2 seconds
```

**Alternatives Considered**:
- **Create React App**: Rejected - slow, deprecated, complex eject process
- **Next.js**: Rejected - server-side rendering overkill for v0
- **Webpack**: Rejected - slow, complex configuration

**Evolution to v1**: Same tool ✅

---

### Tailwind CSS (Styling)

**Why Tailwind?**
- Utility-first (rapid prototyping)
- No CSS file bloat (purges unused styles)
- Responsive design built-in
- Great with component libraries
- Consistent design system

**Alternatives Considered**:
- **Bootstrap**: Rejected - heavier, harder to customize
- **CSS Modules**: Rejected - more boilerplate
- **Styled Components**: Rejected - runtime overhead

**Evolution to v1**: Same styling ✅

---

## Development Tools

### Taskfile (go-task)

**Why Taskfile?**
- **Simpler than Makefiles** (YAML syntax, not shell scripts)
- Cross-platform (works on Windows, Mac, Linux)
- Built-in dependency management
- No cryptic `$@` and `$<` variables
- Modern, actively maintained

**Example**:
```yaml
tasks:
  dev:
    desc: Start development environment
    cmds:
      - docker compose up -d
```

**Alternatives Considered**:
- **Makefile**: Rejected - complex syntax, platform issues
- **npm scripts**: Rejected - requires Node.js for Python project
- **Just**: Rejected - less mature, smaller community

**Evolution to v1**: Same task runner ✅

---

### ruff (Linter + Formatter)

**Why ruff?**
- **10-100x faster** than flake8/black (written in Rust)
- Replaces 10+ tools (flake8, isort, black, pylint, etc.)
- Built-in auto-fix
- Great error messages
- Drop-in replacement for existing tools

**Speed Comparison**:
```bash
flake8 + isort + black:      ~8 seconds
ruff check + ruff format:    ~0.1 seconds (80x faster)
```

**Alternatives Considered**:
- **flake8 + black + isort**: Rejected - slow, multiple tools
- **pylint**: Rejected - very slow, complex configuration

**Evolution to v1**: Same linter ✅

---

### pymarkdownlnt (Markdown Linter)

**Why pymarkdownlnt?**
- Python-based (consistent with backend)
- Comprehensive ruleset (MD001-MD999)
- Auto-fix support
- Good performance

**Alternatives Considered**:
- **markdownlint-cli**: Rejected - requires Node.js
- **mdl**: Rejected - requires Ruby

**Evolution to v1**: Same linter ✅

---

### pytest (Testing)

**Why pytest?**
- Best Python testing framework
- Simple assertion syntax (no `self.assertEqual`)
- Excellent fixture system
- Great plugin ecosystem (pytest-asyncio, pytest-cov, pytest-mock)
- Parallel test execution

**Alternatives Considered**:
- **unittest**: Rejected - verbose, boilerplate-heavy
- **nose**: Rejected - deprecated

**Evolution to v1**: Same testing framework ✅

---

## Infrastructure Stack

### Docker Compose

**Why Docker Compose?**
- **Simple multi-container orchestration**
- Perfect for local development
- One command setup (`docker compose up`)
- Volume management for data persistence
- Network isolation
- Health checks

**Why NOT Kubernetes for v0?**
- Overkill for single-user local deployment
- Complex setup (minikube, k3s, etc.)
- Slower iteration (longer build/deploy cycles)
- Higher learning curve

**Alternatives Considered**:
- **Podman**: Rejected - less mature on Windows
- **Kubernetes (k3s)**: Rejected - too complex for MVP
- **Docker Swarm**: Rejected - deprecated

**Evolution to v1**: Can add Kubernetes option, Docker Compose still works ✅

---

### structlog (Logging)

**Why structlog?**
- **Structured logging** (JSON output)
- Context preservation (request IDs, user IDs)
- Easy to parse and analyze
- Good performance
- Excellent for distributed systems (even monoliths)

**Example Output**:
```json
{
  "event": "claim_verified",
  "claim_id": "123",
  "verdict": "SUPPORTED",
  "confidence": 0.85,
  "timestamp": "2025-10-23T10:30:00Z",
  "level": "info"
}
```

**Alternatives Considered**:
- **Standard logging**: Rejected - unstructured, harder to parse
- **loguru**: Rejected - nice but not structured by default

**Evolution to v1**: Add OpenTelemetry on top (same logs) ✅

---

## What We're NOT Using (and Why)

### Redis (Deferred to v1)

**Why NOT Redis for v0?**
- **No caching needed yet** (premature optimization)
- **No queue needed** (synchronous processing works)
- **Simpler stack** (one less container, one less dependency)

**When to Add (v1)**:
- Search latency >500ms (add caching)
- Processing time >60s (add async queue)
- Multiple concurrent users (add session storage)

---

### Event-Driven Architecture (Deferred to v1)

**Why NOT Events for v0?**
- **Synchronous is simpler** (easier to debug)
- **<60s latency is acceptable** for research use
- **Eventual consistency is complex** (not needed for single-user)

**When to Add (v1)**:
- Multi-user support
- Long-running operations (>60s)
- Need for audit trail beyond database logs

---

### Microservices (Deferred to v1)

**Why NOT Microservices for v0?**
- **Modular monolith is faster to build** (no inter-service communication)
- **Easier to debug** (single process, single log stream)
- **Lower resource overhead** (one container vs 4+)
- **Sufficient for MVP** (single-user, local-first)

**When to Add (v1)**:
- Need independent scaling (e.g., more workers than APIs)
- Multi-team development
- Cloud deployment with managed services

---

### Full Observability Stack (Deferred to v1)

**Why NOT OpenTelemetry + Prometheus for v0?**
- **Structured logs are enough** (80% of debugging needs)
- **No distributed tracing needed** (single process)
- **Simpler setup** (no metrics collection, no dashboards)

**When to Add (v1)**:
- Microservices architecture (distributed tracing)
- Performance debugging (latency breakdowns)
- Production monitoring (SLO tracking)

---

## Technology Decision Matrix

| Technology | v0 | v1 | Why Different? |
|------------|----|----|----------------|
| Python | 3.12+ | 3.12+ | Same |
| Package Manager | uv | uv | Same |
| Web Framework | FastAPI (sync) | FastAPI (async) | Add async/await |
| Database | PostgreSQL + pgvector | PostgreSQL + pgvector + FAISS | Add FAISS for scale |
| Cache | None | Redis | Add for performance |
| Queue | None | Redis Streams | Add for async processing |
| Architecture | Monolith | Microservices | Extract services |
| Containers | 3 (API, DB, UI) | 7+ (services + infra) | Add services + observability |
| Observability | structlog | structlog + OpenTelemetry + Prometheus | Add distributed tracing |
| Frontend | React + Vite | React + Vite | Same |

---

## Dependency Versions

### Backend (pyproject.toml)

```toml
[project]
name = "truthgraph"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.23",
    "asyncpg>=0.29.0",
    "psycopg2-binary>=2.9.9",  # For Alembic migrations
    "alembic>=1.12.1",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "transformers>=4.35.0",
    "sentence-transformers>=2.2.2",
    "torch>=2.1.0",
    "pgvector>=0.2.4",
    "structlog>=23.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "httpx>=0.25.1",  # For TestClient
    "ruff>=0.1.6",
    "mypy>=1.7.1",
]
```

### Frontend (package.json)

```json
{
  "name": "truthgraph-ui",
  "version": "0.1.0",
  "type": "module",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-query": "^5.8.4",
    "axios": "^1.6.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.2",
    "vite": "^5.0.2",
    "tailwindcss": "^3.3.5",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.31"
  }
}
```

---

## Installation Guide

### Prerequisites

```bash
# Required
- Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux)
- Python 3.12+
- Node.js 18+ (for frontend)

# Recommended
- uv (Python package manager): curl -LsSf https://astral.sh/uv/install.sh | sh
- Task (task runner): winget install Task.Task
```

### Quick Start

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository
git clone https://github.com/your-org/truthgraph.git
cd truthgraph

# 3. Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install dependencies
uv pip install -e ".[dev]"

# 5. Set up environment
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD

# 6. Start services
task up

# 7. Open browser
# http://localhost:5173
```

---

## Performance Expectations

### v0 Performance Targets

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| **Startup Time** | <30s | <60s | Cold start with model download |
| **Claim Verification** | <30s | <60s | End-to-end (embed + search + NLI) |
| **Embedding Generation** | <100ms | <200ms | Single text (384-dim) |
| **Search Latency** | <200ms | <500ms | Top-10 results from 10K corpus |
| **NLI Inference** | <300ms | <500ms | Single claim-evidence pair |
| **Memory Footprint** | <2GB | <4GB | Total (API + DB + models) |
| **Disk Space** | <2GB | <5GB | Models + DB + embeddings |

### Hardware Requirements

**Minimum**:
- 8GB RAM
- 4 CPU cores
- 10GB disk space

**Recommended**:
- 16GB RAM
- 8 CPU cores
- 20GB disk space
- SSD (for faster model loading)

**Optional**:
- GPU (NVIDIA with CUDA) - 10x faster inference

---

## Migration Path to v1

### What Changes?

1. **Add Redis** (caching + queuing)
2. **Extract Services** (API Gateway, Verification, Corpus, Worker)
3. **Add CloudEvents** (event-driven architecture)
4. **Add FAISS** (dual vector stores)
5. **Add Observability** (OpenTelemetry, Prometheus)
6. **Add Multi-Tenancy** (`tenant_id` columns)

### What Stays the Same?

✅ Python language
✅ FastAPI framework
✅ PostgreSQL database
✅ SQLAlchemy ORM
✅ ML models
✅ React frontend
✅ Development tools (uv, ruff, pytest)

### Estimated Migration Effort

- **Code Changes**: 30-40% (mostly extracting services, adding async)
- **New Code**: 20-30% (CloudEvents, observability, multi-tenancy)
- **Configuration**: 10-15% (Docker Compose → Kubernetes, env vars → secrets)
- **Total Time**: 2-4 weeks

---

## Document Metadata

**Version**: 1.0
**Date**: 2025-10-23
**Status**: Final
**Author**: TruthGraph Team (Claude Code assisted)
**Related Documents**:
- [v0 Overview](./00_overview.md)
- [Backend Architecture](./backend_architecture.md)
- [Database Schema](./database_schema.md)
- [FastAPI Implementation](./fastapi_implementation.md)
