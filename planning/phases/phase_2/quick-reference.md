# Phase 2 Quick Reference Guide for Agents

**Duration**: 2 weeks | **Total Hours**: 60-80 | **Status**: Ready for Implementation

## One-Page Overview

### Phase 2 Goals
1. Implement embedding generation (sentence-transformers)
2. Enable semantic search (pgvector)
3. Build NLI verification (DeBERTa-v3)
4. Create verdict aggregation
5. Achieve <60s end-to-end verification

### Current Progress
- Phase 1: COMPLETE (FastAPI, database schema, basic API)
- Phase 2: NOT STARTED
- Missing: All ML components, retrieval, pipeline, testing

---

## Execution Timeline

```
Week 3:
  Mon-Tue  [A] Database Migration + env setup (4h)
  Wed-Fri  [B] Embeddings, NLI, Vector Search (parallel, 24-32h)

Week 4:
  Mon-Tue  [C] Hybrid Search + Aggregation (18h)
  Wed-Fri  [D] Pipeline + Corpus Script (12h)
           [E] API Integration (parallel, 12h)

Week 5:
  Mon-Tue  [F] Testing Suite (15h)
  Wed-Fri  [G] Optimization + Docs (10h)
           [H] Docker Config (6h)
           [I] Final Validation (4h)
```

---

## Agent Assignments & Hours

| Agent | Task | Hours | Phase |
|-------|------|-------|-------|
| **python-pro** | EmbeddingService, NLIVerifier, tests, corpus script, optimization | 38h | B,C,F,G |
| **database-architect** | Database schema, vector search, query optimization | 23h | A,B,G |
| **backend-architect** | Hybrid search, pipeline, architecture | 24h | C,D,E |
| **fastapi-pro** | API endpoints, models, integration | 12h | E |
| **test-automator** | Test fixtures, unit/integration tests, benchmarks | 25h | F,I |
| **deployment-engineer** | Docker config, deployment docs, migration support | 11h | H,A |

---

## Critical Path

1. Database Migration (4h) → Week 3, Day 1-2
2. EmbeddingService + NLIVerifier + Vector Search (24h) → Week 3, parallel
3. Hybrid Search (10h) → Week 4, Day 1-2
4. Pipeline (10h) → Week 4, Day 3-5
5. API Integration (8h) → Week 4-5, parallel
6. Testing (15h) → Week 5, Days 1-3
7. Optimization + Docker (16h) → Week 5, Days 3-5

**Minimum Sequential Path**: ~44 hours
**With Parallelization**: ~28-32 hours actual wall-clock time

---

## Success Criteria (Must Meet All)

✓ Latency: <60s for end-to-end claim verification
✓ Accuracy: >70% on 20+ test claims
✓ Models: Cache correctly, fast inference (>500 texts/s, >2 pairs/s)
✓ Resource: <4GB memory, handle 100+ concurrent claims
✓ Code: 100% type hints, comprehensive docstrings, zero linting errors

---

## Key Deliverables by Agent

### Python-Pro
```
truthgraph/ml/embeddings.py        (320 lines, 8h)
truthgraph/ml/verification.py      (260 lines, 8h)
scripts/embed_corpus.py            (170 lines, 6h)
tests/unit/test_embeddings.py      (mocks, 4h)
tests/unit/test_verification.py    (mocks, 4h)
Performance tuning & optimization (8h)
```

### Database-Architect
```
docker/migrations/002_evidence_embeddings.sql
truthgraph/retrieval/vector_search.py  (140 lines, 12h)
Query optimization & tuning (6h)
```

### Backend-Architect
```
truthgraph/retrieval/hybrid_search.py    (180 lines, 10h)
truthgraph/verification/pipeline.py      (260 lines, 10h)
Architecture review & integration (4h)
```

### FastAPI-Pro
```
truthgraph/api/verification_routes.py
Updates to truthgraph/models.py
tests/integration/test_api_verification.py
```

### Test-Automator
```
tests/fixtures/test_claims.json          (Known verdicts)
tests/fixtures/nli_test_pairs.json       (NLI test cases)
tests/unit/test_aggregation.py
tests/unit/test_vector_search.py
tests/integration/test_verification_pipeline.py
tests/integration/test_hybrid_search_e2e.py
tests/performance/test_benchmarks.py
conftest.py (fixtures)
```

### Deployment-Engineer
```
docker/api.Dockerfile (updated)
docker-compose.yml (updated)
docs/DOCKER_ML_SETUP.md
docs/DEPLOYMENT.md
```

---

## Before You Start

Each agent should:
1. Read main implementation plan: `PHASE_2_IMPLEMENTATION_PLAN.md`
2. Read detailed section for your agent (Section 11)
3. Check dependencies - can you start or waiting on someone?
4. Understand success criteria for your deliverables
5. Join the Phase 2 coordination channel

---

## Critical Context for ML Work

### Embedding Service (384-dim vectors)
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Size: ~80MB
- Speed: ~1000 texts/second (CPU)
- Batch size: 32 (CPU), 128+ (GPU)
- Format: Normalized floats, cosine similarity

### NLI Verification (3-class)
- Model: `microsoft/deberta-v3-base` (MNLI)
- Size: ~440MB
- Speed: ~350ms per inference (CPU), >2 pairs/s batched
- Batch size: 8 (CPU), 32+ (GPU)
- Classes: ENTAILMENT (0), NEUTRAL (1), CONTRADICTION (2)
- Return all 3 scores, not just argmax

### Vector Search (pgvector)
- Database: PostgreSQL 15+ with pgvector extension
- Table: `evidence_embeddings` (VECTOR(384))
- Operator: `<->` (cosine distance)
- Index: IVFFlat with lists=100 (tunable)
- Similarity = 1 - distance (0-1 range)

### Latency Budget (<60s total)
- Evidence retrieval: <3s
- NLI batch (10 items): <40s (bottleneck)
- Aggregation: <1s
- Database storage: <2s
- Overhead: <5s

---

## Dependencies & Availability

Already Available:
- ✓ FastAPI + Uvicorn
- ✓ SQLAlchemy 2.0+ with async
- ✓ PostgreSQL + pgvector
- ✓ torch, transformers, sentence-transformers
- ✓ pytest, pytest-asyncio
- ✓ Python 3.12, uv package manager

Will Be Created:
- [ ] Database migration (evidence_embeddings table)
- [ ] All 6 ML/retrieval modules
- [ ] API endpoints
- [ ] Test suite
- [ ] Docker ML configuration

---

## Blockers & Escalation

If blocked, ping context-manager (@context-manager) with:
1. What you're trying to do
2. What's blocking you
3. What you need unblocked
4. Timeline impact

**Target resolution**: <2 hours

---

## Weekly Checkpoints

**End of Week 3**: Phase B complete
- Embeddings, NLI, vector search all working
- Unit tests passing
- No critical blockers

**Mid-week 4**: Phase C-D in progress
- Hybrid search operational
- Pipeline orchestrator complete
- Integration tests running

**End of Week 4**: Phase D-E complete
- Full pipeline end-to-end working
- API endpoints responding
- Performance near targets

**Week 5**: Phase F-H in progress
- Comprehensive test suite
- Performance optimized
- Docker configuration
- Documentation complete

---

## Code Standards (Must Follow)

All code must have:
1. ✓ Type hints on all public functions
2. ✓ Docstrings with Args/Returns/Examples
3. ✓ <100 character line length
4. ✓ Error handling with logging
5. ✓ No external deps beyond specified
6. ✓ Pass ruff linting (configured in pyproject.toml)
7. ✓ Pass mypy type checking

---

## Testing Requirements

**Unit Tests**: Use mocks for ML models
```python
@patch("truthgraph.ml.embeddings.SentenceTransformer")
def test_embed_single(mock_model):
    # Your test here
```

**Integration Tests**: Use real models + database
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_verify_claim(db_pool):
    # Your test here
```

**Benchmarks**: Measure performance
```python
def test_embedding_throughput():
    # Should be >500 texts/second
```

---

## Performance Targets (Measure & Report)

| Component | Target | Measure By |
|-----------|--------|-----------|
| Embedding | >500 texts/s | Batch of 1000 |
| NLI | >2 pairs/s | Batch of 100 |
| Vector Search | <3s | 10k items, 10 results |
| End-to-End | <60s | Full pipeline |
| Memory | <4GB | Loaded models + data |
| Accuracy | >70% | 20+ test claims |

---

## Common Issues & Solutions

### Issue: Models download fails
**Solution**: Implement retry logic, pre-download in Docker, offline mode

### Issue: Memory > 4GB
**Solution**: Profile, optimize batch sizes, consider quantization

### Issue: Vector search too slow
**Solution**: Tune IVFFlat index (lists parameter), check EXPLAIN ANALYZE

### Issue: Accuracy < 70%
**Solution**: Check label mapping, adjust aggregation thresholds, validate fixtures

### Issue: Performance > 60s
**Solution**: Profile each component, optimize bottleneck (likely NLI), batch size tuning

---

## Key Files & Locations

```
truthgraph/                          # Main package
├── ml/                              # ML services
│   ├── embeddings.py               # (Python-Pro)
│   └── verification.py             # (Python-Pro)
├── retrieval/                       # Search services
│   ├── vector_search.py            # (Database-Architect)
│   └── hybrid_search.py            # (Backend-Architect)
├── verification/                    # Aggregation & Pipeline
│   ├── aggregation.py              # (Python-Pro)
│   └── pipeline.py                 # (Backend-Architect)
└── api/
    └── verification_routes.py      # (FastAPI-Pro)

tests/
├── unit/                           # Mocked tests
├── integration/                    # Real component tests
├── performance/                    # Benchmarks
└── fixtures/                       # Test data

docker/
└── migrations/002_evidence_embeddings.sql  # (DB-Architect)

scripts/
└── embed_corpus.py                 # (Python-Pro)
```

---

## Getting Help

1. **Questions about requirements?** → Read detailed section in main plan
2. **Blocked on dependency?** → Check blockers section, ping context-manager
3. **Code review?** → Submit PR with tests, link to checklist
4. **Performance issue?** → Profile first, share results, get optimization advice
5. **Architecture question?** → Discuss in context-manager coordination

---

## When You're Done

1. ✓ All tests passing
2. ✓ Code review approved
3. ✓ Deliverables match checklist
4. ✓ Documentation updated
5. ✓ Metrics validated
6. ✓ Notify context-manager for checkpoint

---

## Resources

- **Main Plan**: `PHASE_2_IMPLEMENTATION_PLAN.md` (detailed, 400+ lines)
- **Roadmap**: `docs/roadmap/v0/phase_02_core_features.md` (specs, examples)
- **Architecture**: `docs/roadmap/v0/backend_architecture.md`
- **Tech Stack**: `docs/roadmap/v0/tech_stack.md`
- **Database**: `docs/roadmap/v0/database_schema.md`

---

## Quick Execution Checklist

**Week 3 Start**:
- [ ] Read main implementation plan
- [ ] Read detailed section for your agent
- [ ] Check dependencies
- [ ] Set up development environment
- [ ] Attend phase kickoff
- [ ] First code commit ready

**Week 3-4**:
- [ ] Code written per checklist
- [ ] Unit tests passing
- [ ] Tests added for coverage
- [ ] Code reviews done
- [ ] Integrated with other components
- [ ] Performance validated

**Week 4-5 End**:
- [ ] All deliverables complete
- [ ] All success criteria met
- [ ] Tests at 80%+ pass rate
- [ ] Documentation complete
- [ ] Ready for deployment

---

**Version**: 1.0
**Last Updated**: 2025-10-25
**Status**: Ready for Agent Briefing
