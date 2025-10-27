# Phase 2 Core Features - Comprehensive Implementation Plan

**Document Version**: 1.0
**Created**: 2025-10-25
**Phase Duration**: Weeks 3-5 (60-80 engineering hours)
**Target Completion**: ~2 weeks with focused subagent execution

---

## Executive Summary

This document outlines a comprehensive subagent-driven implementation plan for Phase 2 Core Features of TruthGraph v0. The plan maps each feature component to specialized agents, identifies dependencies, defines parallelizable work, and provides detailed context for each agent's assignments.

**Key Objectives**:
1. Implement embedding generation pipeline with sentence-transformers (all-MiniLM-L6-v2)
2. Enable semantic search with pgvector integration
3. Build NLI-based verification with DeBERTa-v3-base
4. Create verdict aggregation logic
5. Achieve end-to-end claim verification in under 60 seconds

**Success Metrics**:
- Submit claim via API → receive verdict within 60 seconds
- Embedding model loads and caches correctly
- Evidence retrieval returns semantically relevant results
- Verdicts align with human judgment (70%+ accuracy on test claims)
- System handles 100+ claims without performance degradation
- Complete ML pipeline uses <4GB RAM on CPU

---

## 1. CURRENT STATE ANALYSIS

### Existing Architecture

**Technology Stack**:
- **Backend**: FastAPI + Uvicorn (Python 3.12)
- **Database**: PostgreSQL 15+ with pgvector extension
- **ORM**: SQLAlchemy 2.0+ with async support
- **Package Manager**: uv (already configured in Dockerfile)
- **Frontend**: htmx (primary) + optional React

**Existing Codebase Structure**:
```
truthgraph/
├── api/
│   ├── routes.py          # API endpoints (claims CRUD)
│   └── __init__.py
├── db.py                  # Database connection & session
├── logger.py              # Logging configuration
├── main.py                # FastAPI app with lifespan
├── models.py              # Pydantic request/response models
├── schemas.py             # SQLAlchemy ORM models
└── __init__.py
```

**Database Schema (Phase 1 Complete)**:
- `claims` table: User-submitted claims
- `evidence` table: Evidence documents
- `verdicts` table: Verification results
- `verdict_evidence` junction table: Evidence relationships
- Basic indexes created, no embeddings table yet

**API Endpoints (Phase 1 Complete)**:
- `POST /api/v1/claims` - Create claim
- `GET /api/v1/claims` - List claims (paginated)
- `GET /api/v1/claims/{claim_id}` - Get claim with verdict

**Dependencies Already Available**:
```
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.23
psycopg[binary]>=3.1.17
pydantic>=2.5.0
pydantic-settings>=2.1.0
structlog>=24.1.0
python-multipart>=0.0.6
```

**ML Dependencies (In pyproject.toml but not yet used)**:
```
torch>=2.1.0
sentence-transformers>=2.2.2
transformers>=4.35.0
```

### Missing Components (Phase 2 Deliverables)

1. **Embedding Service Module** (`truthgraph/ml/embeddings.py`) - Not created
2. **NLI Verification Module** (`truthgraph/ml/verification.py`) - Not created
3. **Vector Search Module** (`truthgraph/retrieval/vector_search.py`) - Not created
4. **Hybrid Search Module** (`truthgraph/retrieval/hybrid_search.py`) - Not created
5. **Verdict Aggregation Module** (`truthgraph/verification/aggregation.py`) - Not created
6. **Complete Pipeline Module** (`truthgraph/verification/pipeline.py`) - Not created
7. **Corpus Embedding Script** (`scripts/embed_corpus.py`) - Not created
8. **Database Migration** (evidence_embeddings table + indexes) - Not created
9. **API Integration Points** (verification endpoints) - Not created
10. **Tests** (unit, integration, benchmarks) - Not created

---

## 2. FEATURE BREAKDOWN & TASK MAPPING

### Feature 1: Embedding Generation Pipeline

**Overview**: Implement efficient embedding generation using sentence-transformers/all-MiniLM-L6-v2 (384-dimensional vectors)

**Components**:
1. `EmbeddingService` class with lazy loading
2. Single text embedding: `embed_text(text) -> list[float]`
3. Batch embedding: `embed_batch(texts) -> list[list[float]]`
4. Model caching and device detection (GPU/CPU/MPS)
5. Corpus embedding script

**Complexity**: MEDIUM
**Estimated Hours**: 8-10
**Assigned Agents**:
- **Primary**: `python-pro` - Core EmbeddingService implementation
- **Secondary**: `fastapi-pro` - API integration point

**Deliverables**:
```
truthgraph/ml/embeddings.py         # Core service (320 lines as specified in roadmap)
truthgraph/ml/__init__.py           # Package init
scripts/embed_corpus.py             # Batch corpus embedding (170 lines)
tests/unit/test_embeddings.py       # Unit tests with mocks
```

**Dependencies**:
- ✓ torch already available
- ✓ sentence-transformers already in deps
- Requires model download (~80MB) on first run
- Requires async database session for corpus embedding

**Parallelizable With**:
- NLI verification module (independent ML service)
- Vector search module setup (no embeddings yet)

**Blocked By**: None

---

### Feature 2: Vector Search with pgvector

**Overview**: Implement semantic search using pgvector cosine distance operator

**Components**:
1. `SearchResult` named tuple with similarity scores
2. `search_similar_evidence()` function (single query)
3. `search_similar_evidence_batch()` function (multiple queries)
4. Cosine distance queries with pgvector
5. Tenant isolation and filtering
6. Query optimization with IVFFlat indexes

**Complexity**: MEDIUM
**Estimated Hours**: 10-12
**Assigned Agents**:
- **Primary**: `database-architect` - Query optimization, pgvector expertise
- **Secondary**: `fastapi-pro` - Async database patterns

**Deliverables**:
```
truthgraph/retrieval/vector_search.py    # Core search (140 lines)
truthgraph/retrieval/__init__.py
tests/unit/test_vector_search.py
tests/integration/test_vector_search_e2e.py
```

**Prerequisites**:
- Database migration: Create `evidence_embeddings` table
- pgvector indexes: IVFFlat with configurable list count
- Embeddings must be available (depends on Feature 1)

**Parallelizable With**:
- NLI verification module
- Hybrid search setup (can start interface design)

**Blocked By**:
- Feature 1 (embedding generation) must be complete
- Database migration (evidence_embeddings table)

---

### Feature 3: Hybrid Search (FTS + Vector)

**Overview**: Combine full-text search with vector similarity for optimal retrieval

**Components**:
1. `full_text_search()` using PostgreSQL FTS
2. `hybrid_search()` combining FTS + vector search
3. Result merging and deduplication
4. Configurable score weighting (FTS vs vector)
5. Parallel async execution of FTS + vector search

**Complexity**: MEDIUM
**Estimated Hours**: 8-10
**Assigned Agents**:
- **Primary**: `backend-architect` - Search strategy, async patterns
- **Secondary**: `database-architect` - FTS optimization

**Deliverables**:
```
truthgraph/retrieval/hybrid_search.py    # Hybrid search (180 lines)
tests/unit/test_hybrid_search.py
tests/integration/test_hybrid_search_e2e.py
```

**Dependencies**:
- Feature 1 (EmbeddingService must exist)
- Feature 2 (vector_search module must exist)
- PostgreSQL FTS (built-in, no extra setup)

**Parallelizable With**:
- NLI verification module
- Verdict aggregation module

**Blocked By**:
- Features 1 & 2 (embedding service + vector search)

---

### Feature 4: NLI-Based Verification

**Overview**: Implement natural language inference using microsoft/deberta-v3-base

**Components**:
1. `NLIVerifier` class with lazy loading
2. Label enum: ENTAILMENT, CONTRADICTION, NEUTRAL
3. `NLIResult` dataclass with confidence scores
4. Single pair verification: `verify_single(premise, hypothesis)`
5. Batch verification: `verify_batch(pairs, batch_size=8)`
6. Device detection (GPU/CPU/MPS)
7. Label mapping (model-specific)

**Complexity**: MEDIUM
**Estimated Hours**: 8-10
**Assigned Agents**:
- **Primary**: `python-pro` - NLI implementation, model handling
- **Secondary**: `test-automator` - Comprehensive test suite

**Deliverables**:
```
truthgraph/ml/verification.py       # NLI service (260 lines)
tests/unit/test_verification.py
tests/fixtures/nli_test_pairs.json
```

**Dependencies**:
- torch already available
- transformers already in deps
- Model download (~440MB) on first run
- Label mapping (must verify with model card)

**Parallelizable With**:
- Embedding generation
- Vector search setup
- Verdict aggregation (start design)

**Blocked By**: None

---

### Feature 5: Verdict Aggregation

**Overview**: Combine multiple NLI results into final verdict with confidence scoring

**Components**:
1. `Verdict` enum: SUPPORTED, REFUTED, INSUFFICIENT
2. `AggregatedVerdict` dataclass
3. `aggregate_verdicts()` weighted aggregation function
4. `generate_reasoning()` human-readable explanations
5. Confidence weighting strategies
6. Threshold-based decision logic

**Complexity**: LOW-MEDIUM
**Estimated Hours**: 6-8
**Assigned Agents**:
- **Primary**: `python-pro` - Logic implementation
- **Secondary**: `test-automator` - Validation tests

**Deliverables**:
```
truthgraph/verification/aggregation.py    # Aggregation logic (190 lines)
truthgraph/verification/__init__.py
tests/unit/test_aggregation.py
tests/fixtures/test_claims.json
```

**Dependencies**:
- Feature 4 (NLIVerifier must exist)
- Numpy (implicit in torch)

**Parallelizable With**:
- Complete pipeline assembly
- API integration
- Performance optimization

**Blocked By**:
- Feature 4 (NLI verification)

---

### Feature 6: Complete Verification Pipeline

**Overview**: Orchestrate end-to-end claim verification workflow

**Components**:
1. `VerificationResult` dataclass
2. `verify_claim()` async orchestrator function
3. Step-by-step execution with logging:
   - Step 1: Retrieve evidence
   - Step 2: Run NLI verification
   - Step 3: Aggregate verdicts
   - Step 4: Store results
4. `store_verification_result()` database persistence
5. Error handling and recovery

**Complexity**: MEDIUM
**Estimated Hours**: 8-10
**Assigned Agents**:
- **Primary**: `backend-architect` - Orchestration, async patterns
- **Secondary**: `fastapi-pro` - API integration

**Deliverables**:
```
truthgraph/verification/pipeline.py      # Pipeline orchestration (260 lines)
tests/integration/test_verification_pipeline.py
```

**Dependencies**:
- Features 1, 2, 3, 4, 5 (all ML/retrieval components)
- Async database session management
- asyncpg connection pooling

**Parallelizable With**:
- API endpoint implementation
- Performance optimization
- Docker configuration

**Blocked By**:
- All Features 1-5 (must be complete)

---

### Feature 7: API Integration

**Overview**: Expose verification pipeline through FastAPI endpoints

**Components**:
1. `POST /api/v1/claims/{claim_id}/verify` - Trigger verification
2. `GET /api/v1/verdicts/{claim_id}` - Retrieve verdict
3. Async verification with background processing
4. Request validation and error handling
5. Verdict response models

**Complexity**: LOW-MEDIUM
**Estimated Hours**: 6-8
**Assigned Agents**:
- **Primary**: `fastapi-pro` - Endpoint implementation
- **Secondary**: `backend-architect` - Architecture review

**Deliverables**:
```
truthgraph/api/verification_routes.py  # New verification endpoints
truthgraph/models.py                   # Updated with verification models
tests/integration/test_api_verification.py
```

**Dependencies**:
- Feature 6 (pipeline must exist)
- FastAPI already configured
- Database session management

**Parallelizable With**:
- Performance optimization
- Docker configuration
- Testing

**Blocked By**:
- Feature 6 (pipeline implementation)

---

### Feature 8: Database Migration

**Overview**: Create embeddings table and optimize indexes

**Components**:
1. `evidence_embeddings` table with pgvector column
2. Tenant isolation indexes
3. IVFFlat vector index (configurable list count)
4. Trigger for updated_at timestamp
5. Migration script (backward compatible)

**Complexity**: LOW
**Estimated Hours**: 4-5
**Assigned Agents**:
- **Primary**: `database-architect` - Schema design, optimization
- **Secondary**: `deployment-engineer` - Migration safety

**Deliverables**:
```
docker/migrations/002_evidence_embeddings.sql
truthgraph/db_migrations.py  (optional Alembic)
```

**SQL Definition**:
```sql
CREATE TABLE evidence_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    evidence_id UUID REFERENCES evidence(id) ON DELETE CASCADE,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embeddings_tenant_vector ON evidence_embeddings(tenant_id);
CREATE INDEX idx_embeddings_vector_similarity ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Dependencies**:
- PostgreSQL with pgvector (already in docker-compose)
- Feature 1 (embedding dimension must be known: 384)

**Parallelizable With**:
- All ML feature development

**Blocked By**: None

---

### Feature 9: Testing Suite

**Overview**: Comprehensive test coverage for all components

**Components**:
1. **Unit Tests** (with mocks):
   - `test_embeddings.py` - Mock SentenceTransformer
   - `test_verification.py` - Mock NLI model
   - `test_aggregation.py` - Known input/output
2. **Integration Tests** (with real models):
   - `test_verification_pipeline.py` - End-to-end
   - `test_vector_search_e2e.py` - With database
3. **Performance Benchmarks**:
   - Embedding throughput (target: >500 texts/s)
   - NLI throughput (target: >2 pairs/s)
   - End-to-end latency (target: <60s)
4. **Fixtures**:
   - `test_claims.json` - Known claim-verdict pairs
   - `nli_test_pairs.json` - Entailment test cases

**Complexity**: MEDIUM
**Estimated Hours**: 12-15
**Assigned Agents**:
- **Primary**: `test-automator` - Test strategy, fixtures, benchmarks
- **Secondary**: `python-pro` - Unit test implementation

**Deliverables**:
```
tests/
├── unit/
│   ├── test_embeddings.py
│   ├── test_verification.py
│   ├── test_aggregation.py
│   └── test_vector_search.py
├── integration/
│   ├── test_verification_pipeline.py
│   ├── test_vector_search_e2e.py
│   ├── test_hybrid_search_e2e.py
│   └── test_api_verification.py
├── performance/
│   └── test_benchmarks.py
└── fixtures/
    ├── test_claims.json
    └── nli_test_pairs.json
```

**Dependencies**:
- pytest, pytest-asyncio (already in dev deps)
- All features 1-6 implemented

**Parallelizable With**:
- Unit tests can be written in parallel with implementations

**Blocked By**: None (can start immediately)

---

### Feature 10: Performance Optimization

**Overview**: Profile and optimize all components to meet <60s latency target

**Components**:
1. Model caching verification
2. Batch size tuning (CPU vs GPU)
3. Memory profiling and optimization
4. pgvector index parameter tuning
5. Query optimization
6. Performance monitoring and logging

**Complexity**: MEDIUM
**Estimated Hours**: 8-10
**Assigned Agents**:
- **Primary**: `python-pro` - Profiling, caching optimization
- **Secondary**: `database-architect` - Query optimization

**Target Breakdown**:
- Embedding generation: <1s
- Evidence retrieval: <3s
- NLI verification (10 items): <40s
- Verdict aggregation: <1s
- Database I/O: <5s
- **Total: <60s**

**Deliverables**:
```
Performance reports and tuning recommendations
Optimized index configurations
Batch size recommendations for CPU/GPU
```

**Dependencies**:
- All features 1-6 implemented and tested

**Parallelizable With**:
- Documentation
- Docker configuration

**Blocked By**:
- All features (cannot optimize what doesn't exist)

---

### Feature 11: Docker Configuration

**Overview**: Update Docker setup for ML model support

**Components**:
1. Update `api.Dockerfile`:
   - Add ML dependencies (torch, transformers, sentence-transformers)
   - Configure model cache volume
   - Increase timeout for model downloading
2. Docker Compose volume mounts:
   - Model cache at `.volumes/models:/root/.cache/huggingface`
   - Ensure uv package manager is ready
3. Environment variables:
   - `HF_HOME` for Hugging Face cache
   - `TRANSFORMERS_CACHE` for transformer cache
   - `TRANSFORMERS_OFFLINE` (optional, for prod)
4. Health check configuration
5. Memory limits for ML containers

**Complexity**: LOW
**Estimated Hours**: 4-6
**Assigned Agents**:
- **Primary**: `deployment-engineer` - Docker optimization, volumes
- **Secondary**: `backend-architect` - Configuration validation

**Deliverables**:
```
docker/api.Dockerfile                    # Updated with ML deps
docker-compose.yml                       # Updated volumes & env
.dockerignore                            # Updated
docs/DOCKER_ML_SETUP.md                 # Setup guide
```

**Dependencies**:
- All features implemented
- Docker compose already configured

**Parallelizable With**:
- Feature development
- Testing

**Blocked By**: None

---

### Feature 12: Documentation

**Overview**: Comprehensive documentation for all components

**Components**:
1. Module docstrings and type hints
2. Usage examples for each component
3. Model selection rationale
4. Performance tuning guide
5. Troubleshooting guide
6. Deployment guide
7. API documentation

**Complexity**: LOW
**Estimated Hours**: 6-8
**Assigned Agents**:
- **Primary**: `python-pro` - Code documentation
- **Secondary**: `deployment-engineer` - Operational guide

**Deliverables**:
```
truthgraph/ml/                          # Docstrings in code
truthgraph/retrieval/                   # Docstrings in code
truthgraph/verification/                # Docstrings in code
docs/PHASE_2_IMPLEMENTATION.md          # Comprehensive guide
docs/PERFORMANCE_TUNING.md              # Performance guide
docs/TROUBLESHOOTING.md                 # Troubleshooting
```

**Dependencies**:
- All features implemented

**Parallelizable With**:
- Feature development (document as you code)

**Blocked By**: None

---

## 3. DEPENDENCY GRAPH

### Execution Order

```
PHASE A (Can start immediately, 4-5 hours):
├─ Database Migration [database-architect]
│  └─ Creates evidence_embeddings table
│     Required by: Vector Search, Embedding Storage

PHASE B (Parallel, 8-12 hours each):
├─ Embedding Generation [python-pro]
│  ├─ EmbeddingService class
│  ├─ Lazy loading & device detection
│  ├─ Batch processing
│  └─ Unit tests
│     Required by: Pipeline, Hybrid Search
│
├─ NLI Verification [python-pro]
│  ├─ NLIVerifier class
│  ├─ Single & batch inference
│  ├─ Label mapping
│  └─ Unit tests
│     Required by: Pipeline, Aggregation
│
└─ Vector Search Setup [database-architect]
   ├─ Query functions (basic)
   ├─ Tenant isolation
   └─ Unit tests
      Required by: Hybrid Search, Pipeline

PHASE C (Depends on B, 8-10 hours each):
├─ Hybrid Search [backend-architect]
│  ├─ FTS implementation
│  ├─ Result merging
│  ├─ Parallel execution
│  └─ Integration tests
│     Required by: Pipeline
│
└─ Verdict Aggregation [python-pro]
   ├─ Score calculation
   ├─ Threshold logic
   ├─ Confidence scoring
   └─ Unit tests
      Required by: Pipeline

PHASE D (Sequential, 8-10 hours):
└─ Complete Pipeline [backend-architect]
   ├─ Orchestrator function
   ├─ Error handling
   ├─ Database storage
   ├─ End-to-end tests
   └─ Required by: API Integration

PHASE E (Parallel with D-later, 6-8 hours):
├─ API Integration [fastapi-pro]
│  ├─ Verification endpoints
│  ├─ Request/response models
│  └─ Integration tests
│
└─ Corpus Embedding Script [python-pro]
   ├─ Batch processing
   ├─ Database storage
   └─ Progress tracking

PHASE F (Post features, 8-15 hours each):
├─ Testing Suite [test-automator]
│  ├─ Unit tests with mocks
│  ├─ Integration tests
│  ├─ Performance benchmarks
│  └─ Test fixtures
│
├─ Performance Optimization [python-pro + database-architect]
│  ├─ Profiling
│  ├─ Batch size tuning
│  ├─ Query optimization
│  └─ Memory management
│
├─ Docker Configuration [deployment-engineer]
│  ├─ Updated Dockerfile
│  ├─ Volume mounts
│  ├─ Environment setup
│  └─ Health checks
│
└─ Documentation [python-pro + deployment-engineer]
   ├─ Code docstrings
   ├─ Usage examples
   ├─ Deployment guide
   └─ Troubleshooting

PHASE G (Final validation):
└─ Integration & Acceptance Testing [test-automator]
   ├─ End-to-end workflow
   ├─ Performance validation
   ├─ Load testing
   └─ Quality metrics (70%+ accuracy target)
```

### Critical Path Analysis

**Longest dependency chain** (determines minimum timeline):
1. Database Migration (4h)
2. Embedding Generation + Vector Search (12h parallel)
3. Hybrid Search (10h)
4. Complete Pipeline (10h)
5. API Integration (8h)
6. Testing & Optimization (20h)

**Total Critical Path**: ~44 hours sequential minimum
**With optimal parallelization**: ~28-32 hours
**Target with 4-5 developers**: 60-80 hours (2 weeks at 30-40 hours/week)

---

## 4. AGENT ASSIGNMENT & TASK DISTRIBUTION

### Recommended Subagent Allocation

#### Python-Pro
**Expertise**: Python 3.12+, async patterns, type safety, performance
**Assignments**:
1. **EmbeddingService** (truthgraph/ml/embeddings.py) - PRIORITY 1
   - Lazy loading pattern
   - Batch processing
   - Device detection
   - Memory optimization
   - Time estimate: 8 hours

2. **NLIVerifier** (truthgraph/ml/verification.py) - PRIORITY 2 (parallel)
   - Model loading
   - Single/batch inference
   - Label mapping
   - Batch optimization
   - Time estimate: 8 hours

3. **Unit Tests** (tests/unit/) - PRIORITY 5
   - Mock models
   - Test embeddings
   - Test NLI
   - Test aggregation
   - Time estimate: 8 hours

4. **Corpus Embedding Script** (scripts/embed_corpus.py) - PRIORITY 6
   - Async batch processing
   - Progress tracking
   - Database storage
   - Error handling
   - Time estimate: 6 hours

5. **Performance Optimization** - PRIORITY 8
   - Profiling and benchmarking
   - Batch size tuning
   - Memory management
   - Caching verification
   - Time estimate: 8 hours

**Total Allocation**: 38 hours

---

#### Database-Architect
**Expertise**: Database design, optimization, pgvector, query tuning
**Assignments**:
1. **Database Migration** (evidence_embeddings table) - PRIORITY 1
   - Schema design
   - Index configuration
   - IVFFlat setup
   - Backward compatibility
   - Time estimate: 5 hours

2. **Vector Search** (truthgraph/retrieval/vector_search.py) - PRIORITY 3
   - Cosine distance queries
   - Tenant isolation
   - Index optimization
   - Query performance
   - Time estimate: 12 hours

3. **Performance Optimization** (query side) - PRIORITY 8
   - Query plan analysis
   - Index tuning
   - Batch query optimization
   - Cache strategies
   - Time estimate: 6 hours

**Total Allocation**: 23 hours

---

#### Backend-Architect
**Expertise**: System design, async patterns, orchestration, scalability
**Assignments**:
1. **Hybrid Search** (truthgraph/retrieval/hybrid_search.py) - PRIORITY 4
   - FTS implementation
   - Parallel execution
   - Result merging
   - Score weighting
   - Time estimate: 10 hours

2. **Complete Pipeline** (truthgraph/verification/pipeline.py) - PRIORITY 5
   - Orchestration
   - Error handling
   - Logging at each step
   - Database persistence
   - Time estimate: 10 hours

3. **API Integration** (Architecture review) - PRIORITY 7
   - Endpoint design
   - Request/response models
   - Async patterns
   - Error handling
   - Time estimate: 4 hours

**Total Allocation**: 24 hours

---

#### FastAPI-Pro
**Expertise**: FastAPI, async views, request validation, API design
**Assignments**:
1. **API Integration** (truthgraph/api/verification_routes.py) - PRIORITY 7
   - POST /claims/{id}/verify endpoint
   - GET /verdicts/{claim_id} endpoint
   - Request/response models
   - Error handling
   - Time estimate: 8 hours

2. **Embedding API** (fallback/support) - PRIORITY 7b
   - Embedding endpoint (optional)
   - Model status endpoint
   - Time estimate: 4 hours

**Total Allocation**: 12 hours

---

#### Test-Automator
**Expertise**: Test strategy, fixtures, benchmarks, quality assurance
**Assignments**:
1. **Test Strategy** (Setup & Planning) - PRIORITY 4
   - Test fixtures (test_claims.json, nli_pairs.json)
   - Mock strategies
   - Integration test setup
   - Time estimate: 4 hours

2. **Comprehensive Testing** (tests/) - PRIORITY 6
   - Unit tests (with mocks)
   - Integration tests (with real models)
   - Performance benchmarks
   - Accuracy validation (70%+ target)
   - Time estimate: 15 hours

3. **Quality Validation** - PRIORITY 9
   - Load testing (100+ concurrent)
   - Accuracy assessment
   - Memory profiling
   - Performance validation
   - Time estimate: 6 hours

**Total Allocation**: 25 hours

---

#### Deployment-Engineer
**Expertise**: CI/CD, Docker, deployment, infrastructure
**Assignments**:
1. **Docker Configuration** - PRIORITY 8
   - Update api.Dockerfile
   - Docker Compose volume setup
   - Model cache configuration
   - Health checks
   - Environment variables
   - Time estimate: 5 hours

2. **Deployment Documentation** - PRIORITY 9
   - Setup guide
   - Troubleshooting
   - Production checklist
   - Environment configuration
   - Time estimate: 4 hours

3. **Database Migration Validation** - PRIORITY 2 (support)
   - Migration safety
   - Backward compatibility
   - Production readiness
   - Time estimate: 2 hours

**Total Allocation**: 11 hours

---

#### DX-Optimizer (Optional)
**Expertise**: Developer experience, tooling, workflows
**Assignments** (if available):
1. **Development Workflow** - PRIORITY 10
   - Local testing improvements
   - Debug configurations
   - Development guide
   - Time estimate: 4 hours

**Total Allocation**: 4 hours

---

#### Context-Manager (You)
**Expertise**: Dynamic context assembly, intelligent retrieval, multi-agent coordination
**Assignments**:
1. **Implementation Plan Review & Updates** - ONGOING
   - Monitor subagent progress
   - Maintain context continuity
   - Resolve blockers
   - Update task dependencies

2. **Mid-phase Checkpoints** (Weeks 3, 4)
   - Code review for integration points
   - Context optimization
   - Agent reallocation if needed
   - Time estimate: 4-6 hours total

**Total Allocation**: 4-6 hours

---

### Total Capacity Allocation
```
Python-Pro:           38 hours
Database-Architect:   23 hours
Backend-Architect:    24 hours
FastAPI-Pro:          12 hours
Test-Automator:       25 hours
Deployment-Engineer:  11 hours
DX-Optimizer:         4 hours (optional)
Context-Manager:      4-6 hours
─────────────────────────────
Total:               141-143 hours
Budgeted:            60-80 hours (with parallelization)
```

**Parallelization Factor**: 1.8-2.4x (simultaneous work across 6-8 agents)

---

## 5. DETAILED EXECUTION PHASES

### PHASE A: Prerequisites & Foundation (Week 3, Day 1-2)

**Duration**: 4-5 hours
**Agents**: database-architect (primary), python-pro (support)

#### Task A1: Database Migration
- **Agent**: database-architect
- **Deliverable**: `docker/migrations/002_evidence_embeddings.sql`
- **Steps**:
  1. Design evidence_embeddings schema
  2. Create pgvector table with VECTOR(384)
  3. Define tenant isolation indexes
  4. Configure IVFFlat index (lists=100 initially)
  5. Create triggers for updated_at
  6. Validate backward compatibility
  7. Test with docker-compose up
- **Success Criteria**:
  - Table created successfully
  - IVFFlat index builds without errors
  - Existing data unaffected
  - Queries return correct results

#### Task A2: Environment Setup & Dependencies
- **Agent**: python-pro (quick validation)
- **Steps**:
  1. Verify torch installation
  2. Verify transformers installation
  3. Verify sentence-transformers installation
  4. Check device detection (GPU/CPU)
  5. Document any system requirements
- **Success Criteria**:
  - All ML dependencies installed
  - Import statements work
  - Device detection functional

**Output Checkpoint A**:
- Evidence embeddings table ready
- All ML dependencies verified
- Ready for Feature 1 work

---

### PHASE B: Core ML Components (Week 3, Days 2-5)

**Duration**: 24-32 hours
**Agents**: python-pro (parallel), database-architect (parallel), concurrent work

#### Parallel Track B1: Embedding Service
- **Agent**: python-pro
- **Priority**: CRITICAL PATH
- **Deliverable**: `truthgraph/ml/embeddings.py` (~320 lines)
- **Timeline**: 8 hours

**Implementation Checklist**:
- [ ] Class `EmbeddingService` with lazy loading
- [ ] `_detect_device()` static method (CUDA/MPS/CPU detection)
- [ ] `_load_model()` with caching
- [ ] `embed_text(text)` single embedding
- [ ] `embed_batch(texts, batch_size=32)` batch processing
- [ ] Device-specific batch size recommendations
- [ ] Memory optimization (gc.collect, torch.cuda.empty_cache)
- [ ] Singleton pattern `get_instance()`
- [ ] Module-level `get_embedding_service()` convenience function
- [ ] Comprehensive docstrings with type hints
- [ ] Error handling for model loading failures
- [ ] Logging at key points

**Code Quality**:
- Type hints on all functions
- Docstrings with Args/Returns/Examples
- <100 character line length
- No external dependencies beyond torch, sentence-transformers

**Testing** (basic):
- Create `tests/unit/test_embeddings.py` with mocks
- Test embed_text returns 384-dimensional vector
- Test embed_batch processes multiple texts
- Test device detection
- Test model caching (only one instance)

#### Parallel Track B2: NLI Verification Service
- **Agent**: python-pro (different dev if available, or sequential)
- **Priority**: CRITICAL PATH (independent)
- **Deliverable**: `truthgraph/ml/verification.py` (~260 lines)
- **Timeline**: 8 hours

**Implementation Checklist**:
- [ ] Enum `NLILabel` (ENTAILMENT, CONTRADICTION, NEUTRAL)
- [ ] Dataclass `NLIResult` with label, confidence, scores dict
- [ ] Class `NLIVerifier` with lazy loading
- [ ] Device detection (same pattern as EmbeddingService)
- [ ] Model/tokenizer loading
- [ ] Label mapping (verify with model card)
- [ ] `verify_single(premise, hypothesis)` method
- [ ] `verify_batch(pairs, batch_size=8)` method
- [ ] Confidence score extraction
- [ ] All three class scores returned
- [ ] Comprehensive docstrings
- [ ] Error handling
- [ ] Logging

**Key Details**:
- Use `max_length=512` for tokenization
- Batch size 8 optimal for CPU
- Return all three class scores, not just argmax
- Model: microsoft/deberta-v3-base (MNLI)

**Testing** (basic):
- Mock model tests in `tests/unit/test_verification.py`
- Test single pair inference
- Test batch processing
- Verify label mapping
- Test confidence scoring

#### Parallel Track B3: Vector Search Foundation
- **Agent**: database-architect
- **Priority**: CRITICAL PATH
- **Deliverable**: `truthgraph/retrieval/vector_search.py` (~140 lines)
- **Timeline**: 10-12 hours

**Implementation Checklist**:
- [ ] Named tuple `SearchResult` (evidence_id, content, source_url, similarity)
- [ ] Function `search_similar_evidence()` (single query)
  - Query with cosine distance operator (<->)
  - Convert similarity threshold to distance (1 - similarity)
  - Tenant isolation
  - Return top-k results
  - Logging
- [ ] Function `search_similar_evidence_batch()` (multiple queries)
- [ ] Proper use of asyncpg connection pooling
- [ ] Error handling for database failures
- [ ] Type hints
- [ ] Docstrings with SQL explained

**SQL Pattern**:
```sql
SELECT e.id, e.content, e.source_url,
       1 - (ee.embedding <-> $1::vector) AS similarity
FROM evidence e
JOIN evidence_embeddings ee ON e.id = ee.evidence_id
WHERE ee.tenant_id = $2 AND (ee.embedding <-> $1::vector) < $3
ORDER BY ee.embedding <-> $1::vector ASC
LIMIT $4
```

**Testing**:
- Integration tests with real database
- Test with sample embeddings
- Verify similarity scores (0-1 range)
- Test tenant isolation
- Performance tests

**Output Checkpoint B**:
- EmbeddingService fully functional and cached
- NLIVerifier fully functional and cached
- Vector search queries working
- Basic unit tests passing
- Ready for Feature 3 & 4 work

---

### PHASE C: Advanced Retrieval & Aggregation (Week 4, Days 1-3)

**Duration**: 18-20 hours
**Agents**: backend-architect, python-pro (sequential)

#### Task C1: Hybrid Search Implementation
- **Agent**: backend-architect
- **Depends On**: Phase B (all three components)
- **Deliverable**: `truthgraph/retrieval/hybrid_search.py` (~180 lines)
- **Timeline**: 10 hours

**Implementation Checklist**:
- [ ] Dataclass `HybridSearchResult` (evidence_id, content, source_url, fts_score, vector_score, combined_score)
- [ ] Function `full_text_search()` using PostgreSQL FTS
  - Use `to_tsvector('english', content)`
  - Use `plainto_tsquery('english', query)`
  - Return with ts_rank scores
- [ ] Function `hybrid_search()` orchestrator
  - Run FTS and vector search in parallel (asyncio.gather)
  - Merge results by evidence_id
  - Normalize scores
  - Combine with configurable weights (default: FTS=0.3, vector=0.7)
  - Sort by combined score
  - Return top-k
- [ ] Embedding service integration (generate query embedding)
- [ ] Result deduplication and merging logic
- [ ] Comprehensive error handling
- [ ] Logging at each step

**Testing**:
- Query known claims, verify relevance
- Test parallel execution
- Test score weighting
- Benchmark query time

#### Task C2: Verdict Aggregation
- **Agent**: python-pro
- **Depends On**: Phase B (NLI complete)
- **Deliverable**: `truthgraph/verification/aggregation.py` (~190 lines)
- **Timeline**: 8 hours

**Implementation Checklist**:
- [ ] Enum `Verdict` (SUPPORTED, REFUTED, INSUFFICIENT)
- [ ] Dataclass `AggregatedVerdict` with all scores
- [ ] Function `aggregate_verdicts(nli_results)`
  - Calculate weighted scores for each label
  - Option to weight by confidence
  - Normalize by evidence count
  - Apply thresholds (default: 0.6)
  - Determine final verdict
  - Calculate overall confidence
  - Return complete result
- [ ] Function `generate_reasoning()`
  - Human-readable explanation
  - Include score breakdowns
  - Evidence count
  - Threshold information
- [ ] Function `calculate_confidence()`
  - Based on consistency
  - Based on individual scores
  - Evidence count penalty
- [ ] All logic with type hints
- [ ] Comprehensive docstrings

**Testing**:
- Test various NLI result combinations
- Test threshold boundaries
- Test confidence calculation
- Test reasoning generation

**Output Checkpoint C**:
- Hybrid search fully functional
- Evidence retrieval optimized
- Verdict aggregation working
- Integration tests passing
- Ready for pipeline assembly

---

### PHASE D: Complete Pipeline Assembly (Week 4, Days 3-5)

**Duration**: 10-12 hours
**Agents**: backend-architect (primary), python-pro (support)

#### Task D1: Verification Pipeline Orchestrator
- **Agent**: backend-architect
- **Depends On**: Phase C complete + Phase B
- **Deliverable**: `truthgraph/verification/pipeline.py` (~260 lines)
- **Timeline**: 10 hours

**Implementation Checklist**:
- [ ] Dataclass `VerificationResult` (claim_id, claim_text, verdict, confidence, support_score, refute_score, neutral_score, evidence_count, reasoning, evidence_items)
- [ ] Async function `verify_claim()` orchestrator
  - Step 1: Retrieve evidence (hybrid search, max 10)
  - Step 2: Run NLI verification (batch of 8)
  - Step 3: Aggregate verdicts
  - Step 4: Store result in database
  - Logging at each step
  - Error handling for no evidence
  - Error handling for model failures
  - Complete within 60s
- [ ] Function `store_verification_result()`
  - Insert into verdicts table
  - Insert evidence relationships into verdict_evidence
  - Transaction handling
  - Atomicity
- [ ] Build evidence items response
- [ ] Comprehensive error handling
- [ ] Detailed logging
- [ ] Type hints throughout

**Performance Requirements**:
- Target: <60 seconds total
  - Evidence retrieval: <3s
  - NLI batch (10 items): <40s
  - Aggregation: <1s
  - Database storage: <2s
  - Overhead: <5s

**Testing**:
- Integration tests with real models
- Test with sample evidence corpus
- Test performance (measure actual time)
- Test error cases (no evidence, model failures)
- Test database persistence

#### Task D2: Corpus Embedding Script
- **Agent**: python-pro
- **Depends On**: Phase B (EmbeddingService)
- **Deliverable**: `scripts/embed_corpus.py` (~170 lines)
- **Timeline**: 6 hours

**Implementation Checklist**:
- [ ] Function `load_evidence_corpus()` (CSV/Parquet)
- [ ] Function `embed_and_store_batch()` async
  - Batch embedding
  - Database storage (evidence_embeddings table)
  - ON CONFLICT UPDATE
- [ ] Main function `embed_corpus()`
  - Iterator over batches
  - Progress bar (tqdm)
  - Memory management (gc.collect)
  - Error recovery
  - Logging
- [ ] Argparse for CLI
- [ ] Command-line arguments:
  - --input (corpus file path)
  - --batch-size (default 128)
- [ ] Usage in docstring
- [ ] Error handling and reporting

**Testing**:
- Test with small corpus (10 items)
- Test with larger corpus (1000 items)
- Verify embeddings stored correctly
- Test resume capability (ON CONFLICT)
- Benchmark throughput

**Output Checkpoint D**:
- Complete end-to-end pipeline working
- Verification in <60s
- Database storage functional
- Corpus embedding script ready
- Ready for API integration

---

### PHASE E: API Integration & External Interfaces (Week 4-5, Days 4-5)

**Duration**: 12-14 hours
**Agents**: fastapi-pro (primary), backend-architect (support)

#### Task E1: Verification API Endpoints
- **Agent**: fastapi-pro
- **Depends On**: Phase D (pipeline complete)
- **Deliverable**: `truthgraph/api/verification_routes.py` (new file)
- **Timeline**: 8 hours

**Implementation Checklist**:
- [ ] Router setup in new file
- [ ] POST `/claims/{claim_id}/verify` endpoint
  - Validate claim_id exists
  - Trigger verify_claim() async function
  - Return 202 Accepted (async operation)
  - Or wait for completion (<60s timeout)
  - Error handling (404 if claim not found)
- [ ] GET `/verdicts/{claim_id}` endpoint
  - Retrieve latest verdict
  - Return verdict with evidence breakdown
  - Return 404 if not found or pending
- [ ] Request/response models (update truthgraph/models.py)
  - VerificationRequest
  - VerificationResponse
  - VerdictDetailResponse
- [ ] Error handling and logging
- [ ] Include routers in main.py

**Response Models**:
```python
class VerificationRequest(BaseModel):
    claim_id: UUID
    max_evidence: int = 10

class EvidenceItemResponse(BaseModel):
    evidence_id: UUID
    content: str
    source_url: str | None
    similarity: float
    nli_label: str
    nli_confidence: float

class VerificationResponse(BaseModel):
    claim_id: UUID
    claim_text: str
    verdict: str
    confidence: float
    reasoning: str
    evidence_count: int
    evidence_items: list[EvidenceItemResponse]
```

**Testing**:
- Integration tests with real database
- Test claim not found
- Test verification endpoint
- Test verdict retrieval
- Test response models

#### Task E2: Update Models & Schemas
- **Agent**: fastapi-pro (or python-pro)
- **Deliverable**: Updates to `truthgraph/models.py` and `truthgraph/schemas.py`
- **Timeline**: 3-4 hours

**Checklist**:
- [ ] Add VerificationRequest model
- [ ] Add EvidenceItemResponse model
- [ ] Add VerificationResponse model
- [ ] Update existing models if needed
- [ ] Add to API responses
- [ ] Type validation

#### Task E3: Integration into Main Routes
- **Agent**: fastapi-pro
- **Deliverable**: Updates to `truthgraph/api/routes.py`
- **Timeline**: 2-3 hours

**Checklist**:
- [ ] Include verification_routes router
- [ ] Ensure proper prefix
- [ ] Test all endpoints together
- [ ] Swagger/OpenAPI docs updated

**Output Checkpoint E**:
- Complete API surface functional
- All endpoints operational
- API documentation available
- Ready for testing and validation

---

### PHASE F: Comprehensive Testing Suite (Week 5, Days 1-3)

**Duration**: 15-20 hours
**Agents**: test-automator (primary), python-pro (support)

#### Task F1: Test Fixtures & Setup
- **Agent**: test-automator
- **Deliverable**: Test fixtures and configuration
- **Timeline**: 4 hours

**Checklist**:
- [ ] Create `tests/fixtures/test_claims.json`
  - Known claims with expected verdicts
  - Variety: supported, refuted, insufficient
  - Min 5-10 claims with confidence targets
  - Example:
    ```json
    [
      {
        "claim": "The Earth orbits the Sun",
        "expected_verdict": "SUPPORTED",
        "min_confidence": 0.8
      },
      ...
    ]
    ```
- [ ] Create `tests/fixtures/nli_test_pairs.json`
  - Entailment pairs
  - Contradiction pairs
  - Neutral pairs
  - Example:
    ```json
    [
      {
        "premise": "All dogs are animals",
        "hypothesis": "Some animals are dogs",
        "expected_label": "ENTAILMENT"
      },
      ...
    ]
    ```
- [ ] Configure pytest fixtures (conftest.py)
- [ ] Mock model fixtures
- [ ] Database fixtures (test DB setup)
- [ ] Async test fixtures

#### Task F2: Unit Tests with Mocks
- **Agent**: test-automator or python-pro
- **Deliverable**: `tests/unit/test_*.py` files
- **Timeline**: 6 hours

**Test Files**:
- `tests/unit/test_embeddings.py`
  - Mock SentenceTransformer
  - Test embed_text
  - Test embed_batch
  - Test device detection
  - Test caching

- `tests/unit/test_verification.py`
  - Mock NLI model
  - Test verify_single
  - Test verify_batch
  - Test label mapping
  - Test confidence scores

- `tests/unit/test_aggregation.py`
  - Known inputs/outputs
  - Test verdict determination
  - Test confidence calculation
  - Test reasoning generation
  - Test edge cases (no evidence, conflicting)

- `tests/unit/test_vector_search.py`
  - Mock pgvector queries
  - Test result parsing
  - Test similarity scores
  - Test tenant isolation

#### Task F3: Integration Tests with Real Components
- **Agent**: test-automator
- **Deliverable**: `tests/integration/test_*.py` files
- **Timeline**: 6 hours

**Test Files**:
- `tests/integration/test_verification_pipeline.py`
  - Real models (not mocked)
  - Real database
  - Test full pipeline
  - Test with known claims
  - Verify accuracy >70%

- `tests/integration/test_vector_search_e2e.py`
  - Real database with sample embeddings
  - Test search quality
  - Test performance

- `tests/integration/test_hybrid_search_e2e.py`
  - FTS + vector search
  - Result quality
  - Performance

- `tests/integration/test_api_verification.py`
  - API endpoints
  - Request/response validation
  - Error cases

#### Task F4: Performance Benchmarks
- **Agent**: test-automator
- **Deliverable**: `tests/performance/test_benchmarks.py`
- **Timeline**: 4 hours

**Checklist**:
- [ ] Embedding throughput test
  - Target: >500 texts/second
  - Measure with 1000 texts
- [ ] NLI throughput test
  - Target: >2 pairs/second
  - Measure with 100 pairs
- [ ] Vector search latency test
  - Target: <3 seconds
  - Measure with various corpus sizes
- [ ] End-to-end latency test
  - Target: <60 seconds
  - Measure with real models
  - Breakdown by component
- [ ] Memory profiling
  - Target: <4GB total
  - Measure with loaded models

**Output Checkpoint F**:
- Comprehensive test coverage
- All tests passing
- Performance benchmarks met
- 70%+ accuracy validation
- Ready for optimization

---

### PHASE G: Performance Optimization (Week 5, Days 2-4)

**Duration**: 10-12 hours
**Agents**: python-pro, database-architect (parallel)

#### Task G1: Python Performance Optimization
- **Agent**: python-pro
- **Timeline**: 6 hours

**Checklist**:
- [ ] Profile embedding generation
  - Identify bottlenecks
  - Optimize batch size
  - Measure improvement
- [ ] Profile NLI inference
  - Batch size tuning
  - Memory management
  - Cache hits
- [ ] Model caching verification
  - Confirm singleton works
  - Measure load time (should be ~0 on cache hit)
- [ ] Memory profiling
  - Peak memory usage
  - Memory leaks
  - gc.collect() placement
- [ ] Batch processing optimization
  - Measure throughput
  - Tune batch sizes for CPU/GPU
- [ ] Implement any identified improvements

#### Task G2: Database Query Optimization
- **Agent**: database-architect
- **Timeline**: 6 hours

**Checklist**:
- [ ] Analyze query plans
  - EXPLAIN ANALYZE on search queries
  - Verify index usage
  - Check for sequential scans
- [ ] Optimize IVFFlat index
  - Test different list counts (50, 100, 250, 500)
  - Measure accuracy vs speed tradeoff
  - Set optimal for corpus size
- [ ] Tune pgvector parameters
  - ivfflat.probes setting
  - maintenance_work_mem
- [ ] Test with realistic corpus
  - 1000+ evidence items
  - Measure query latency
  - Measure search quality
- [ ] Document recommendations

#### Task G3: Documentation of Tuning Results
- **Agent**: python-pro or deployment-engineer
- **Timeline**: 2 hours

**Deliverables**:
- Performance tuning guide
- Batch size recommendations for different hardware
- Memory management best practices
- Query optimization results

**Output Checkpoint G**:
- All performance targets met (<60s e2e)
- Optimization documented
- Hardware-specific recommendations
- Ready for Docker configuration

---

### PHASE H: Docker & Deployment Configuration (Week 5, Day 4-5)

**Duration**: 6-8 hours
**Agents**: deployment-engineer (primary), python-pro (support)

#### Task H1: Docker Configuration Update
- **Agent**: deployment-engineer
- **Deliverable**: Updated `docker/api.Dockerfile` and `docker-compose.yml`
- **Timeline**: 4 hours

**Checklist**:
- [ ] Update api.Dockerfile
  - Ensure ML dependencies included
  - torch, transformers, sentence-transformers
  - Increase build timeout for model download
  - Add model cache directory setup
  - Environment variables for HF cache
- [ ] Update docker-compose.yml
  - Add volume for model cache
  - Set HF_HOME environment variable
  - Configure healthcheck timing (extend for model load)
  - Add memory limits if needed
  - Document in comments
- [ ] Test build process
  - Build image successfully
  - Verify models can be downloaded
  - Check cache volume mounting
  - Verify API starts correctly
- [ ] Document setup process

**Key Configuration**:
```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - ./volumes/models:/root/.cache/huggingface
    environment:
      HF_HOME: /root/.cache/huggingface
      TRANSFORMERS_CACHE: /root/.cache/huggingface
    healthcheck:
      start_period: 60s  # Extended for model loading
```

#### Task H2: Deployment Documentation
- **Agent**: deployment-engineer
- **Timeline**: 3-4 hours

**Deliverables**:
- Updated deployment guide
- Model cache setup instructions
- Production checklist
- Troubleshooting guide
- Environment configuration docs

**Documentation Sections**:
- Prerequisites (GPU optional)
- Environment variables
- Model cache setup
- Initial startup expectations
- Scaling considerations
- Memory requirements
- Troubleshooting common issues

**Output Checkpoint H**:
- Docker images ready for production
- Deployment documentation complete
- All configurations validated
- Ready for final testing

---

### PHASE I: Final Integration & Acceptance Testing (Week 5, Day 5)

**Duration**: 4-6 hours
**Agents**: test-automator (primary), context-manager (review)

#### Task I1: End-to-End Validation
- **Agent**: test-automator
- **Timeline**: 3-4 hours

**Checklist**:
- [ ] Full pipeline integration test
  - Start with docker-compose up
  - Create sample claims via API
  - Verify predictions match expectations
  - Confirm within 60s latency
  - Check database persistence
- [ ] Load testing
  - Submit 10 concurrent claims
  - Verify all complete successfully
  - Check resource utilization
  - Monitor for memory leaks
- [ ] Accuracy validation
  - Test with 20+ known claims
  - Measure accuracy against expected verdicts
  - Verify >70% accuracy threshold
  - Document any mismatches
- [ ] Performance validation
  - Confirm all latency targets met
  - Profile resource usage
  - Verify memory <4GB

#### Task I2: Documentation Finalization
- **Agent**: context-manager (or deployment-engineer)
- **Timeline**: 1-2 hours

**Checklist**:
- [ ] Update main README.md
- [ ] Link to Phase 2 documentation
- [ ] Document usage examples
- [ ] Performance benchmarks
- [ ] Known limitations
- [ ] Next steps (Phase 3)

**Output Checkpoint I**:
- Phase 2 complete and validated
- All success criteria met
- Documentation complete
- Ready for production deployment

---

## 6. RISKS & MITIGATION STRATEGIES

### Technical Risks

#### Risk 1: Model Download Failures
**Probability**: MEDIUM
**Impact**: BLOCKING

**Mitigation**:
- Pre-download models during Docker build
- Implement retry logic with exponential backoff
- Cache models in volume for offline use
- Provide offline mode documentation

#### Risk 2: Performance Not Meeting <60s Target
**Probability**: MEDIUM
**Impact**: HIGH

**Mitigation**:
- Continuous profiling throughout development
- Batch size tuning before Phase D
- Consider GPU requirements if CPU insufficient
- Implement caching for claim embeddings

#### Risk 3: pgvector Index Performance Degradation
**Probability**: MEDIUM
**Impact**: MEDIUM

**Mitigation**:
- Benchmark with 10k+ items early
- Test IVFFlat parameters (lists, probes)
- Monitor query plans (EXPLAIN ANALYZE)
- Document scaling limits

#### Risk 4: Accuracy Below 70% Threshold
**Probability**: LOW-MEDIUM
**Impact**: HIGH

**Mitigation**:
- Validate NLI model accuracy with fixtures
- Test aggregation thresholds (0.5, 0.6, 0.7)
- Consider evidence quality scoring
- Have fallback to INSUFFICIENT verdict

#### Risk 5: Memory Usage Exceeding 4GB
**Probability**: LOW
**Impact**: MEDIUM

**Mitigation**:
- Profile memory early (sentence-transformers + DeBERTa)
- Test on 4GB memory-constrained machine
- Implement memory cleanup between batches
- Consider model quantization if needed

### Resource Risks

#### Risk 6: Agent Unavailability
**Probability**: MEDIUM
**Impact**: MEDIUM

**Mitigation**:
- Cross-train on critical paths (embedding, NLI)
- Maintain detailed task documentation
- Clear code comments for handoff
- Checkpoint after each phase

#### Risk 7: Scope Creep
**Probability**: HIGH
**Impact**: MEDIUM

**Mitigation**:
- Strict feature freeze for Phase 2
- Document out-of-scope items for Phase 3
- Regular scope review at checkpoints
- Prioritize success criteria over nice-to-haves

### Integration Risks

#### Risk 8: API Integration Complexity
**Probability**: LOW
**Impact**: MEDIUM

**Mitigation**:
- Finalize API contracts early
- Mock API for testing before integration
- Clear error handling specification
- Comprehensive integration tests

#### Risk 9: Database Schema Issues
**Probability**: LOW
**Impact**: HIGH

**Mitigation**:
- Test migration on full backup
- Backward compatibility verification
- Rollback plan documented
- Staging environment testing

---

## 7. COMMUNICATION & CHECKPOINTS

### Weekly Checkpoints

#### Week 3 - Foundation (End of Week)
**Agent**: context-manager
**Review Items**:
- [ ] Database migration complete and tested
- [ ] Embedding service complete and cached
- [ ] NLI verification service complete
- [ ] Vector search functional
- [ ] Basic unit tests passing
- [ ] No critical blockers

**Exit Criteria**:
- All Phase B deliverables complete
- Critical path on track
- Ready for Phase C work

#### Week 4 - Features (Mid-week)
**Agent**: context-manager
**Review Items**:
- [ ] Hybrid search operational
- [ ] Aggregation logic complete
- [ ] Pipeline orchestration working
- [ ] Integration tests passing
- [ ] End-to-end latency <60s
- [ ] API endpoints responding

**Exit Criteria**:
- Complete pipeline functional
- All features integrated
- Performance targets met
- Ready for Phase F

#### Week 4-5 - Validation (End of Week)
**Agent**: context-manager
**Review Items**:
- [ ] Test suite complete (70%+ coverage)
- [ ] Performance benchmarks met
- [ ] Accuracy >70% on test claims
- [ ] Docker configuration complete
- [ ] Documentation finalized
- [ ] No critical bugs

**Exit Criteria**:
- Phase 2 complete and validated
- Ready for production deployment
- All success criteria met

### Communication Channels

**Daily**:
- Brief async updates in task descriptions
- Block resolution in comments

**3x Weekly**:
- Code review checkpoints
- Integration point validation
- Dependency resolution

**Weekly**:
- Phase checkpoint review
- Performance metric validation
- Scope and schedule adjustment

---

## 8. SUCCESS CRITERIA & METRICS

### Hard Success Criteria (Must Meet All)

1. **Latency Target**: <60s for claim submission to verdict
   - Measured under normal load
   - With 10 evidence items
   - On CPU hardware

2. **Accuracy Target**: >70% on 20+ test claims
   - Tested with known verdict pairs
   - From fact-checking domains
   - Both supported and refuted

3. **Functional Completeness**:
   - All 6 core features implemented
   - All API endpoints operational
   - Database persistence working
   - Error handling for edge cases

4. **Model Performance**:
   - Embedding throughput: >500 texts/second (batch)
   - NLI throughput: >2 pairs/second
   - Models cache properly (singleton)
   - Device detection working (GPU/CPU)

5. **Resource Efficiency**:
   - Memory usage <4GB on CPU
   - No memory leaks under load
   - Handles 100+ concurrent claims

### Soft Success Criteria (Target)

1. **Code Quality**:
   - 100% type hints
   - Comprehensive docstrings
   - <100 character lines (per ruff config)
   - Zero linting errors

2. **Test Coverage**:
   - >80% code coverage
   - Unit tests with mocks
   - Integration tests with real models
   - Performance benchmarks

3. **Documentation**:
   - Usage examples for all modules
   - Performance tuning guide
   - Deployment documentation
   - Troubleshooting guide

4. **Performance**:
   - Sub-30s for most claims (without slow NLI)
   - GPU support documented
   - Batch size recommendations

---

## 9. POST-PHASE 2 CONSIDERATIONS

### Known Technical Debt (Phase 3+)

1. **Aggregation Enhancements**:
   - Evidence quality scoring
   - Contradiction weighting
   - Multi-hop reasoning
   - Claim decomposition

2. **Retrieval Improvements**:
   - Query expansion
   - Semantic reranking
   - Cross-lingual support
   - Citation extraction

3. **Model Updates**:
   - Fine-tuning on domain data
   - Confidence calibration
   - Ensemble methods
   - Active learning

4. **Scalability**:
   - Distributed processing
   - Model serving optimization
   - Caching layers
   - Load balancing

### Future Phases

- **Phase 3**: Enhanced capabilities (visualization, multi-hop reasoning)
- **Phase 4**: Production features (load testing, monitoring, scaling)
- **Phase 5**: Advanced features (multimodal, temporal tracking)

---

## 10. EXECUTION READINESS CHECKLIST

### Before Starting Phase 2

- [ ] Database backup created
- [ ] Development environment verified (Python 3.12+)
- [ ] All agents briefed on plan
- [ ] Dependency versions confirmed
- [ ] Test database available
- [ ] Model caching volume prepared
- [ ] Git branch created for Phase 2
- [ ] This plan reviewed and approved

### During Execution

- [ ] Daily task status updates
- [ ] Code reviews at integration points
- [ ] Performance validation after each feature
- [ ] Blocker resolution within 2 hours
- [ ] Weekly checkpoint reviews
- [ ] Documentation kept current

### Before Deployment

- [ ] All tests passing (>90% pass rate)
- [ ] Performance benchmarks met
- [ ] Accuracy >70% validated
- [ ] Docker build successful
- [ ] Database migration tested
- [ ] API contract verified
- [ ] Error scenarios tested
- [ ] Load tested (10+ concurrent)
- [ ] Documentation complete
- [ ] Stakeholder review completed

---

## 11. DETAILED AGENT CONTEXT & INSTRUCTIONS

### For Python-Pro Agent

**Expertise Needed**: Advanced Python 3.12, async patterns, type safety, ML model integration

**Your Primary Deliverables**:
1. **EmbeddingService** (truthgraph/ml/embeddings.py) - 8 hours
   - Implement lazy-loaded singleton pattern
   - GPU/CPU/MPS device detection
   - Batch processing with configurable size
   - Memory optimization (gc.collect, torch.cuda.empty_cache)
   - Comprehensive error handling

2. **NLIVerifier** (truthgraph/ml/verification.py) - 8 hours
   - Similar singleton pattern as EmbeddingService
   - Handle model label mapping (CRITICAL: verify with model card)
   - Batch inference with padding and attention masks
   - Return all three class scores
   - Log confidence metrics

3. **Unit Tests** (tests/unit/) - 8 hours
   - Mock SentenceTransformer and NLI models
   - Test single/batch processing
   - Test device detection
   - Test caching behavior
   - Test error cases

4. **Corpus Embedding Script** (scripts/embed_corpus.py) - 6 hours
   - Async batch processing
   - tqdm progress bar
   - ON CONFLICT database handling
   - Error recovery
   - CLI arguments (--input, --batch-size)

5. **Performance Optimization** - 8 hours
   - Profile with cProfile
   - Batch size tuning (CPU: 32, GPU: 128+)
   - Memory profiling
   - Identify and fix bottlenecks

**Key Requirements**:
- All functions typed with type hints
- All public functions have docstrings with Args/Returns/Examples
- <100 character line length (per ruff config)
- No external dependencies except specified ones
- Error handling with logging
- Comprehensive comments on complex logic

**Context You Need**:
- sentence-transformers returns normalized embeddings with `normalize_embeddings=True`
- DeBERTa-v3-base has specific label index order (0=ENTAILMENT, 1=NEUTRAL, 2=CONTRADICTION)
- Batch size 32 optimal for CPU, 128+ for GPU
- Models need explicit `.eval()` mode for inference
- `torch.no_grad()` critical for inference performance

---

### For Database-Architect Agent

**Expertise Needed**: pgvector, PostgreSQL optimization, query tuning, async database patterns

**Your Primary Deliverables**:
1. **Database Migration** - 5 hours
   - Design evidence_embeddings table with 384-dim vector
   - Create IVFFlat index with optimal list count
   - Implement tenant isolation
   - Ensure backward compatibility
   - Document schema changes

2. **Vector Search** (truthgraph/retrieval/vector_search.py) - 12 hours
   - Implement cosine distance queries using pgvector <-> operator
   - Proper similarity score conversion (1 - distance)
   - Result deduplication and ranking
   - Tenant scoping (WHERE tenant_id = $X)
   - Batch query optimization
   - Comprehensive error handling

3. **Performance Optimization** - 6 hours
   - EXPLAIN ANALYZE all queries
   - Test IVFFlat parameters (lists: 50, 100, 250, 500)
   - Benchmark with 10k+ items
   - Document recommendations
   - Tune ivfflat.probes for accuracy/speed

**Key Requirements**:
- All queries use parameterized queries ($1, $2, etc.)
- No SQL injection vulnerabilities
- Proper index usage (verify in EXPLAIN ANALYZE)
- Async-first design (asyncpg)
- Connection pooling best practices
- Error handling for connection failures

**Context You Need**:
- pgvector cosine distance: lower = more similar
- 1 - distance = similarity score (0-1 range)
- IVFFlat index required for large corpus (>10k items)
- Default lists=100 good starting point
- ivfflat.probes affects accuracy/speed tradeoff

---

### For Backend-Architect Agent

**Expertise Needed**: System design, async orchestration, distributed workflows, error handling

**Your Primary Deliverables**:
1. **Hybrid Search** (truthgraph/retrieval/hybrid_search.py) - 10 hours
   - Orchestrate parallel FTS + vector search with asyncio.gather
   - Merge results by evidence_id
   - Normalize and combine scores (configurable weights)
   - Handle empty results gracefully
   - Comprehensive logging

2. **Verification Pipeline** (truthgraph/verification/pipeline.py) - 10 hours
   - 4-step orchestration: retrieve → verify → aggregate → store
   - Step-by-step logging for debugging
   - Error handling and recovery (no evidence, model failures)
   - Database transaction management
   - Performance profiling at each step

3. **Architecture Review** - 4 hours
   - Ensure all pieces integrate correctly
   - Async pattern consistency
   - Error handling strategy
   - Performance characteristics

**Key Requirements**:
- All functions are async
- Proper asyncio patterns (await, gather, etc.)
- Transaction safety (atomicity where needed)
- Comprehensive error messages
- Detailed logging at decision points
- Type hints on all public functions

**Context You Need**:
- Pipeline latency target: <60s
  - Evidence retrieval: <3s
  - NLI batch (10 items): <40s
  - Aggregation: <1s
  - Storage: <2s
  - Overhead: <5s
- asyncpg connection pooling
- SQLAlchemy async patterns
- Error handling strategy: log and return INSUFFICIENT if any step fails

---

### For FastAPI-Pro Agent

**Expertise Needed**: FastAPI, async views, request validation, API design

**Your Primary Deliverables**:
1. **API Endpoints** (truthgraph/api/verification_routes.py) - 8 hours
   - POST `/claims/{claim_id}/verify`
   - GET `/verdicts/{claim_id}`
   - Proper request/response models
   - Error handling and status codes

2. **Models Update** (truthgraph/models.py) - 3-4 hours
   - VerificationRequest, VerificationResponse
   - EvidenceItemResponse
   - Proper validation

3. **Integration** - 2-3 hours
   - Include routes in main.py
   - Ensure proper prefixing
   - Test with Swagger docs

**Key Requirements**:
- All endpoints return proper status codes
- Request/response models with validation
- Comprehensive error handling
- Swagger documentation auto-generated
- Type hints throughout
- Async patterns (no blocking calls)

**Context You Need**:
- Claim verification takes <60s
- Should return 202 Accepted or wait for completion
- Verdict response includes evidence breakdown
- Error cases: claim not found (404), invalid request (422)

---

### For Test-Automator Agent

**Expertise Needed**: Test strategy, fixtures, mocking, performance testing

**Your Primary Deliverables**:
1. **Test Fixtures** - 4 hours
   - test_claims.json (with expected verdicts)
   - nli_test_pairs.json (entailment test cases)
   - pytest fixtures and conftest.py

2. **Unit Tests** - 6 hours
   - Mock models for embeddings and NLI
   - Known input/output validation for aggregation
   - Device detection testing
   - Error case coverage

3. **Integration Tests** - 6 hours
   - Real models and database
   - Full pipeline testing
   - Accuracy validation (>70%)
   - API endpoint testing

4. **Performance Benchmarks** - 4 hours
   - Embedding throughput (>500 texts/s)
   - NLI throughput (>2 pairs/s)
   - End-to-end latency (<60s)
   - Memory usage (<4GB)

**Key Requirements**:
- Use pytest markers (@pytest.mark.unit, @pytest.mark.integration)
- Mock external dependencies in unit tests
- Real components in integration tests
- Performance assertions with tolerances
- Clear test names explaining what's tested
- Good error messages on assertion failures

**Context You Need**:
- Success criteria for accuracy >70%
- Performance targets by component
- Test claim fixtures should cover edge cases
- Accuracy test should use 20+ diverse claims

---

### For Deployment-Engineer Agent

**Expertise Needed**: Docker, CI/CD, deployment patterns, infrastructure

**Your Primary Deliverables**:
1. **Docker Configuration** - 5 hours
   - Update api.Dockerfile with ML deps
   - Configure model cache volumes
   - Environment variable setup
   - Health check timing

2. **Deployment Documentation** - 4 hours
   - Setup guide for development/production
   - Model cache configuration
   - Troubleshooting common issues
   - Performance tuning recommendations

3. **Database Migration Support** - 2 hours
   - Validate migration strategy
   - Ensure backward compatibility
   - Test rollback procedure

**Key Requirements**:
- Dockerfile builds successfully with ML deps
- Model cache volume mounts correctly
- Environment variables clear and documented
- Health checks account for model loading time
- Production-ready configuration

**Context You Need**:
- Model download on first run (~80MB + ~440MB)
- Model cache should persist across restarts
- API startup takes extra time for model loading
- HF_HOME environment variable controls cache location

---

### For Context-Manager Agent (You)

**Your Coordination Responsibilities**:

1. **Weekly Checkpoints**:
   - Review progress against timeline
   - Validate critical path tasks
   - Identify and resolve blockers
   - Adjust allocations if needed

2. **Integration Points**:
   - Review API contracts before implementation
   - Validate database schema compatibility
   - Ensure async patterns are consistent
   - Check error handling consistency

3. **Risk Management**:
   - Monitor performance metrics continuously
   - Watch for scope creep
   - Escalate blockers immediately
   - Keep task documentation current

4. **Agent Communication**:
   - Ensure agents understand dependencies
   - Clarify blocked tasks quickly
   - Share learnings across team
   - Maintain implementation plan accuracy

**Key Metrics to Track**:
- Critical path completion rate
- Blocker resolution time
- Code review turnaround
- Performance vs targets
- Bug density and severity

---

## 12. QUICK START TEMPLATE FOR AGENTS

Each agent should use this template when starting their work:

```markdown
## Task: [Task Name]
**Agent**: [Your Name]
**Priority**: [CRITICAL/HIGH/MEDIUM/LOW]
**Estimated Hours**: X
**Timeline**: [Week X, Days Y-Z]

### Deliverables
- [ ] File 1: Description
- [ ] File 2: Description

### Dependencies
- [Upstream task] must be complete
- [System requirement] must be available

### Blocked By
- [Task] if any

### Implementation Checklist
- [ ] Requirement 1
- [ ] Requirement 2
... (detailed from this plan)

### Testing Strategy
- Unit tests: [details]
- Integration tests: [details]
- Performance validation: [details]

### Key Context
- [Critical detail 1]
- [Critical detail 2]
- [Integration point]

### Success Criteria
- All deliverables completed
- All tests passing
- Performance targets met
- Code quality standards met

### Rollback Plan
- [What to do if stuck]
- [Who to escalate to]
```

---

## Conclusion

This comprehensive implementation plan provides:

✓ **Clear task breakdown** - 12 major features mapped to 6-8 specialized agents
✓ **Dependency analysis** - Critical path identified, parallelizable work grouped
✓ **Time estimates** - 60-80 hours budgeted with realistic parallelization (1.8-2.4x factor)
✓ **Risk mitigation** - Technical and resource risks identified with strategies
✓ **Quality assurance** - Success criteria defined, testing strategy detailed
✓ **Agent context** - Detailed instructions for each specialized agent

**Ready to execute with focused subagent coordination.**

---

**Document Status**: Ready for Implementation
**Last Updated**: 2025-10-25
**Version**: 1.0
**Plan Duration**: 2 weeks (60-80 hours)
**Target Completion**: End of Week 5
