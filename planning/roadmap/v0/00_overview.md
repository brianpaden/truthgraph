# TruthGraph v0: Minimal Viable Product Overview

## Executive Summary

TruthGraph v0 is a **simplified, local-first fact-checking system** designed for rapid development and immediate user value. It takes a pragmatic approach: start simple, deliver core functionality quickly, then evolve.

**Key Simplifications vs v1**:

- **Modular monolith** (not microservices) - Single FastAPI application with clear module boundaries
- **Synchronous operations** (not event-driven) - Direct API calls instead of Redis Streams
- **Single vector store** - pgvector only (not pgvector + FAISS dual approach)
- **Minimal observability** - structlog logging without full OpenTelemetry/Prometheus stack
- **Single-tenant schema** - Simpler database design (tenant_id can be added later if needed)
- **Practical scope** - Core verification only (no multimodal, no complex reasoning graphs yet)

**Timeline**: 4-5 weeks, split into two phases:
- **Phase 1 (Week 1-2)**: Foundation - Docker setup, API, database, basic UI
- **Phase 2 (Week 3-5)**: Core features - Embeddings, search, simple verification

**Target User**: Individual researchers, journalists, or fact-checkers who need a private, portable tool

---

## High-Level Architecture

### Simplified Component Diagram

```text
┌──────────────────────────────────────────────┐
│         TruthGraph v0 Docker Stack           │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │  React Frontend (port 5173)         │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │  FastAPI Monolith (port 8000)       │   │
│  │  ├─ API routes                      │   │
│  │  ├─ Embedding service               │   │
│  │  ├─ Retrieval logic                 │   │
│  │  ├─ Verification logic              │   │
│  │  └─ Database access layer           │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────┴──────────────────────┐   │
│  │  PostgreSQL + pgvector (port 5432)  │   │
│  └─────────────────────────────────────┘   │
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │  Basic structlog Logging             │   │
│  └─────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

### Key Architectural Decisions

1. **Monolith First**: Everything in one FastAPI app reduces operational complexity. Can split into services later if needed.

2. **Synchronous by Default**: Direct function calls instead of async queues. Simpler to reason about, easier to debug. For MVP scope, synchronous is fast enough.

3. **pgvector Only**: Store embeddings directly in PostgreSQL. Single database = simpler setup, backup, and management. FAISS can be added later if search performance becomes a bottleneck.

4. **Flat Database Schema**: No multi-tenant complexity. Single `tenant_id` not needed yet. Can be added in v1 when/if multi-user is required.

5. **Minimal ML Models**: Start with proven, efficient models:
   - **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, fast on CPU)
   - **NLI**: `microsoft/deberta-v3-base` (MNLI fine-tuned, accurate NLI)

6. **Simple Logging**: structlog with console output. No distributed tracing yet (too much infrastructure for MVP).

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.12+ | Fast development, ML libraries, asyncio support |
| **Backend Framework** | FastAPI | Modern, async, auto-docs, validation |
| **Package Manager** | uv | Fast, simple, better than pip/conda |
| **Database** | PostgreSQL 15+ | ACID, pgvector extension, full-text search |
| **Vector Storage** | pgvector | Embedded in PostgreSQL, no extra infrastructure |
| **Embeddings Model** | all-MiniLM-L6-v2 | Fast on CPU, good quality, 384 dimensions |
| **NLI Model** | microsoft/deberta-v3-base | Superior accuracy, MNLI fine-tuned |
| **Logging** | structlog | Structured, JSON-capable, minimal overhead |
| **Frontend** | **htmx** (recommended) or React | **htmx**: 3x faster, no build tools; React: if team prefers |
| **Container Orchestration** | Docker Compose | Simple, local-first, documented |
| **Task Runner** | Task (go-task) | Shell-agnostic alternative to Make |

---

## Design Principles

### 1. **Simplicity Over Completeness**
Focus on the happy path. Defer edge cases, advanced features, and error recovery to v1.

### 2. **Local-First**
No cloud dependencies, no API keys required, no vendor lock-in. Works offline after initial setup.

### 3. **Portable**
Single `docker-compose up` brings the whole system to life. Data is portable via standard database backups.

### 4. **Clear Module Boundaries**
Even though it's a monolith, code is organized by domain (api, models, retrieval, verification). Easy to extract services later.

### 5. **Test-Driven Where It Matters**
Focus on ML logic and critical paths. UI can be tested manually for MVP.

### 6. **Pragmatic Infrastructure**
Use minimal DevOps. Docker Compose, not Kubernetes. Structured logging, not full observability stack. One database, not a fleet.

### 7. **Frontend: htmx Over React (Recommended for v0)**

**Decision**: Use **htmx** instead of React for v0's simple UI needs.

**Why htmx for v0?**

- **3x faster development**: 2 weeks vs 4-5 weeks for same UI
- **No build tooling**: No webpack, npm, babel - just HTML templates
- **Backend team can build UI**: Python devs already know Jinja2 templates
- **10x smaller bundle**: 14KB vs 140KB (faster page loads)
- **Server-side rendering**: SEO-friendly, works without JavaScript

**v0 UI Requirements** (simple enough for htmx):

- Claim submission form (text input + button)
- Claim history list (paginated table)
- Verification results display (verdict, confidence, evidence)
- Loading states (<60s processing time)
- Error messages

**When to use React instead**: If your team already has React expertise and prefers it, or if you want to practice React for v1. htmx saves time but isn't mandatory.

**v1 Migration**: When v1 adds interactive reasoning graphs, real-time WebSocket updates, and temporal timelines, switch to React (estimated 2-3 week migration effort for complex pages only).

**See**: [tech_stack.md - htmx vs React](./tech_stack.md#htmx-vs-react-the-decision) for detailed comparison and code examples.

---

## Core Capabilities - v0 MVP

### 1. **Claim Submission**
- User pastes or uploads a claim
- System stores claim with basic metadata (submitted_at, source URL optional)
- Simple web form

### 2. **Evidence Retrieval**
- User can add evidence documents to a knowledge base (initially via CSV/JSON import)
- System retrieves relevant evidence using embeddings + semantic search
- Basic reranking by relevance

### 3. **Simple Verification**
- For each piece of evidence, determine if it supports/refutes/is neutral to the claim
- Use NLI (Natural Language Inference) model
- Aggregate verdicts using simple majority voting
- Return: verdict (SUPPORTED/REFUTED/INSUFFICIENT) + confidence score

### 4. **Result Display**
- Show verdict with confidence meter
- List supporting/refuting evidence
- Show evidence snippets

### 5. **Persistence**
- Store all claims, evidence, and verdicts in PostgreSQL
- Basic data export (JSON)

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Working claim submission, storage, and basic UI

**Deliverables**:
- Docker Compose with PostgreSQL, FastAPI, React
- Database schema (claims, evidence, verdicts tables)
- API endpoints: POST /claims, GET /claims/{id}, GET /claims (list)
- Simple React UI: claim submission form, claim history list
- structlog setup

**Success Criteria**:
- `docker-compose up` brings everything up
- Can submit a claim via API or UI
- Can retrieve claims
- All code in single FastAPI service

**Estimated effort**: 1-2 weeks

---

### Phase 2: Core Features (Weeks 3-5)

**Goal**: End-to-end verification with embeddings and NLI

**Deliverables**:
- Embedding pipeline (download model, embed documents)
- Evidence CSV/JSON import script
- pgvector integration (store + search embeddings)
- NLI-based verification service
- Verdict generation and storage
- Results display UI component
- Basic test coverage (unit tests for core logic)

**Success Criteria**:
- Submit claim → see results within 10-20 seconds (synchronous)
- Evidence relevance makes sense
- Verdicts align with common sense (at least 80% accuracy on 10 test claims)
- Full system uses <2GB RAM

**Estimated effort**: 2-3 weeks

---

## Success Criteria

### Phase 1 Success
- [x] Docker setup complete
- [x] Database initialized
- [x] Claim submission works (API + UI)
- [x] Basic code structure in place

### Phase 2 Success
- [x] End-to-end: claim submission → verdict (< 20s)
- [x] Embedding model loads and runs
- [x] Evidence retrieval returns relevant results
- [x] Verdicts make intuitive sense
- [x] System handles 100+ claims smoothly

### Code Quality
- [x] 70%+ test coverage on core logic (embeddings, verification, retrieval)
- [x] No hardcoded values (all config via environment variables)
- [x] Code is readable and documented
- [x] README with quick start

---

## Evolution: v0 → v1

This roadmap is **intentionally simple** so that v1 can add sophistication without rework.

### What Stays the Same
- Core domain models (claims, evidence, verdicts)
- API contracts (endpoints, request/response schemas)
- Database schema (can be extended with new columns, not replaced)
- ML models (same embedding and NLI models used initially)

### What Changes in v1
- **Architecture**: Monolith → Microservices (API Gateway, Verification Service, Corpus Service, Worker)
- **Async Processing**: Sync → Event-driven with Redis Streams
- **Vector Storage**: pgvector-only → pgvector + FAISS for speed
- **Multi-Tenancy**: Single user → Multi-tenant with auth
- **Observability**: structlog → structlog + OpenTelemetry + Prometheus
- **Features**: Basic verification → Multi-hop reasoning, temporal tracking, multimodal

### Design for Evolution
To make v0 → v1 upgrade smooth:

1. **Module Boundaries**: Even in monolith, organize by domain
   ```
   truthgraph/
   ├── api/           # FastAPI routes
   ├── models/        # Pydantic models
   ├── db/            # Database access (can become repositories in v1)
   ├── retrieval/     # Search logic
   ├── verification/  # NLI logic
   └── ml/            # ML model loading
   ```

2. **Repository Pattern** (optional for v0, required in v1): Wrap database access so we can swap PostgreSQL for something else later

3. **Event Schemas** (optional for v0): Even if using sync APIs now, design events that match CloudEvents format so async migration is natural

4. **Logging**: Use structlog with JSON output from day one (not just console)

---

## Quick Start Vision

After v0 is complete, getting started should take under 5 minutes:

```bash
# Clone and setup
git clone https://github.com/your-org/truthgraph.git
cd truthgraph
cp .env.example .env

# Start everything
docker-compose up -d

# Load sample evidence (optional)
docker-compose exec api python -m scripts.load_sample_corpus

# Open browser
open http://localhost:5173

# Submit a claim and see results
```

---

## What v0 Does NOT Include

Explicitly deferred to v1 or later:

- **Multi-hop reasoning**: Single-hop evidence retrieval and verification only
- **Multimodal support**: Text claims and evidence only (no images, PDFs, video)
- **Temporal reasoning**: No tracking how claims evolve over time
- **Multi-user/multi-tenant**: Single user, no authentication
- **Advanced search**: Basic semantic search only (no complex filters, faceting)
- **Visualization**: Results are text-based (no interactive graphs yet)
- **Export features**: Can export claims as JSON, nothing fancier
- **Full observability**: No OpenTelemetry, Prometheus, or complex logging infrastructure
- **Horizontal scaling**: Single container, no load balancing
- **Cloud deployment**: Local Docker Compose only

---

## Success Metrics

A v0 is successful if:

1. **Developer onboarding**: New contributor can set up and run tests in < 30 minutes
2. **User onboarding**: New user can submit a claim and see results in < 5 minutes
3. **Verdict quality**: System verdicts match human judgment on 10+ test claims (at least 70% agreement)
4. **Performance**: End-to-end claim processing in < 20 seconds
5. **Code quality**: 70%+ test coverage, no linting errors, builds cleanly
6. **Documentation**: Clear README, API docs, inline code comments

---

## Related Documentation

- **[Phase 1: Foundation](./phase_01_foundation.md)** - Docker setup, database, API basics
- **[Phase 2: Core Features](./phase_02_core_features.md)** - Embeddings, search, verification
- **[Technology Stack](./tech_stack.md)** - Detailed technology choices and rationale
- **[v1 Overview](../v1/00_overview.md)** - Where we're headed after v0
- **[v1 Cloud-Ready Patterns](../v1/cloud_ready_patterns.md)** - For reference, optional patterns in v0

---

## Document Structure

This v0 roadmap is split into focused documents:

- **00_overview.md** (this document): Vision, architecture, scope
- **phase_01_foundation.md**: Detailed Phase 1 tasks and implementation notes
- **phase_02_core_features.md**: Detailed Phase 2 tasks and implementation notes
- **tech_stack.md**: Deep dive into technology choices and alternatives

**Navigation**:
- Start here if you're new to the project
- Read phase documents for implementation details
- Check tech_stack.md for "why we chose X over Y"

---

## Getting Started

### For Contributors

1. Read this overview
2. Review [tech_stack.md](./tech_stack.md) for technology rationale
3. Check current project status
4. Read the relevant phase document
5. Follow the phase TODO checklist

### For Project Managers

- Use success criteria above to track progress
- Each phase has granular acceptance criteria
- Expect ~4-5 weeks for v0 complete
- v1 can begin after Phase 2 is stable

### For Users (After v0 Complete)

1. Clone repository
2. Copy `.env.example` to `.env`
3. Run `docker-compose up`
4. Open http://localhost:5173
5. Upload evidence corpus (sample provided)
6. Submit claims and verify

---

## Questions & Feedback

This v0 roadmap intentionally simplifies v1 to focus on rapid delivery. Key design decisions:

- **Why monolith instead of microservices?** → Simpler to build, test, and deploy for MVP. Easier to refactor into services once we understand the domain better.
- **Why sync instead of async?** → Less infrastructure overhead, easier to understand data flow, fast enough for MVP scope.
- **Why pgvector-only?** → Single database = single backup, single deployment target. FAISS adds complexity without MVP benefit.
- **Why only text claims?** → Multimodal adds 2-3x complexity. Start with what most users need (text), add images/PDFs in v1.

**Trade-offs**: v0 won't scale to millions of claims or handle complex reasoning. That's okay. v1 is designed to extend v0 without major rewrites.

---

**Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Ready for Implementation
