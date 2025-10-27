# Phase 2 Execution Summary & Visual Guide

## Project Status Dashboard

```text
PHASE 1 (Complete)
├── ✓ FastAPI backend
├── ✓ PostgreSQL database schema
├── ✓ Basic API endpoints (CRUD claims)
└── ✓ Docker + docker-compose setup

PHASE 2 (Ready to Start)
├── ⏳ ML Services (Embeddings, NLI)
├── ⏳ Retrieval (Vector & Hybrid Search)
├── ⏳ Aggregation & Pipeline
├── ⏳ API Integration
├── ⏳ Testing & Validation
└── ⏳ Deployment

Timeline: 2 weeks (60-80 hours)
Status: Ready for Implementation
```

---

## Dependency Graph (Visual)

```text
DATABASE MIGRATION (4h)
│
├─→ EMBEDDING SERVICE (8h)
│   ├─→ CORPUS SCRIPT (6h)
│   │
│   ├─→ HYBRID SEARCH (10h)
│   │   └─→ PIPELINE (10h)
│   │       ├─→ API ENDPOINTS (8h)
│   │       └─→ INTEGRATION TESTS (6h)
│   │
│   └─→ PERFORMANCE TEST (4h)
│
├─→ NLI VERIFICATION (8h, parallel)
│   ├─→ AGGREGATION (8h)
│   │   └─→ PIPELINE (10h)
│   │
│   └─→ NLI UNIT TESTS (4h)
│
├─→ VECTOR SEARCH (12h, parallel)
│   ├─→ HYBRID SEARCH (10h)
│   │   └─→ PIPELINE (10h)
│   │
│   └─→ VECTOR TESTS (4h)

PARALLEL TRACK
├─→ COMPREHENSIVE TESTING (15h)
├─→ PERFORMANCE OPTIMIZATION (10h)
├─→ DOCKER CONFIGURATION (6h)
└─→ DOCUMENTATION (6h)
```

---

## Task Assignment Matrix

```text
                    WEEK 3        WEEK 4           WEEK 5
                   Mon Tue|Wed Thu Fri|Mon Tue|Wed Thu Fri|
DATABASE        [===]
EMBEDDING         [=========]
NLI               [=========]
VECTOR              [============]
HYBRID              ........[==========]
AGGREGATION         ........[======]
PIPELINE            .............[==========]
API INT             .............[========]
CORPUS SCRIPT       ............[=====]
UNIT TESTS          ......[==========================]
INTEGRATION         .....[========================]
OPTIMIZATION        ..................[========]
DOCKER              ..................[======]
DOCS                .................[=====]
FINAL VAL           ..........................[==]

[===] = In Progress
.... = Waiting/Blocked
```

---

## Agent Workload Distribution

```text
Total Work: 141 hours over 2 weeks
With Parallelization: 28-32 hour critical path (1.8-2.4x factor)

┌─────────────────────────────────────────────────────┐
│ AGENT HOURS & SCHEDULE                              │
├─────────────────────────────────────────────────────┤
│ Python-Pro              38 hours ████████████████░░░ │
│ Database-Architect      23 hours ██████████░░░░░░░░░ │
│ Backend-Architect       24 hours ███████████░░░░░░░░ │
│ FastAPI-Pro             12 hours ██████░░░░░░░░░░░░░ │
│ Test-Automator          25 hours ████████████░░░░░░░ │
│ Deployment-Engineer     11 hours █████░░░░░░░░░░░░░░ │
├─────────────────────────────────────────────────────┤
│ TOTAL ALLOCATED         143 hours                    │
│ BUDGETED               60-80 hours (with parallelization)
└─────────────────────────────────────────────────────┘

Parallelization Factor: 1.8-2.4x
Actual Duration: 2 weeks
Critical Path: ~44 hours sequential
```

---

## Weekly Milestone Targets

```text
WEEK 3 - FOUNDATION
└─ Phase A: Database Migration           [4 hours]
└─ Phase B: Core ML Components          [24-32 hours parallel]
   ├─ EmbeddingService ✓
   ├─ NLIVerifier ✓
   └─ Vector Search ✓
EXIT CRITERIA:
  ✓ All Phase B components functional
  ✓ Unit tests passing
  ✓ No critical blockers
  ✓ Ready for Phase C


WEEK 4 - FEATURES
└─ Phase C: Advanced Retrieval          [18 hours]
   ├─ Hybrid Search ✓
   └─ Aggregation ✓
└─ Phase D: Pipeline Assembly           [10-12 hours]
   ├─ Verification Pipeline ✓
   └─ Corpus Embedding Script ✓
└─ Phase E: API Integration             [12 hours parallel]
   └─ Verification Endpoints ✓
EXIT CRITERIA:
  ✓ End-to-end pipeline <60 seconds
  ✓ API endpoints responding
  ✓ Integration tests passing
  ✓ Ready for validation


WEEK 5 - VALIDATION
└─ Phase F: Testing Suite               [15 hours]
   ├─ Unit Tests ✓
   ├─ Integration Tests ✓
   └─ Benchmarks ✓
└─ Phase G: Performance Optimization    [10 hours]
└─ Phase H: Docker Configuration        [6 hours]
└─ Phase I: Final Validation            [4 hours]
EXIT CRITERIA:
  ✓ 70%+ accuracy on test claims
  ✓ All latency targets met
  ✓ All tests passing
  ✓ Ready for production
```

---

## Success Metrics Checklist

```text
HARD REQUIREMENTS (Must Meet)

Latency & Performance
┌─────────────────────────────────────────────────┐
│ [ ] <60s end-to-end verification                │
│ [ ] >500 texts/sec embedding throughput         │
│ [ ] >2 pairs/sec NLI throughput                 │
│ [ ] <4GB memory usage on CPU                    │
│ [ ] Handles 100+ concurrent claims              │
└─────────────────────────────────────────────────┘

Accuracy & Quality
┌─────────────────────────────────────────────────┐
│ [ ] >70% accuracy on 20+ test claims            │
│ [ ] All models cache correctly (singleton)      │
│ [ ] Device detection works (GPU/CPU/MPS)        │
│ [ ] Zero linting errors (ruff)                  │
│ [ ] 100% type hints on public APIs              │
└─────────────────────────────────────────────────┘

Functional Completeness
┌─────────────────────────────────────────────────┐
│ [ ] All 6 core features implemented             │
│ [ ] All API endpoints operational               │
│ [ ] Database persistence working                │
│ [ ] Error handling for edge cases               │
│ [ ] Comprehensive docstrings                    │
└─────────────────────────────────────────────────┘

Testing & Validation
┌─────────────────────────────────────────────────┐
│ [ ] >80% code coverage                          │
│ [ ] Unit tests with mocks passing               │
│ [ ] Integration tests with real models passing  │
│ [ ] Performance benchmarks validated            │
│ [ ] Load tested (10+ concurrent)                │
└─────────────────────────────────────────────────┘
```

---

## Component Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐        ┌──────────────────┐            │
│  │   VERIFICATION   │        │  API ROUTES      │            │
│  │   ENDPOINTS      │────────│  /verify         │            │
│  │  (New in P2)     │        │  /verdicts       │            │
│  └────────┬─────────┘        └──────────────────┘            │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │        VERIFICATION PIPELINE (Orchestrator)        │    │
│  │  1. Retrieve Evidence (Hybrid Search)               │    │
│  │  2. Run NLI Verification                            │    │
│  │  3. Aggregate Verdicts                              │    │
│  │  4. Store Results                                   │    │
│  └───┬──────────────┬──────────────┬──────────────────┘    │
│      │              │              │                       │
│      ▼              ▼              ▼                       │
│  ┌───────────┐  ┌────────────┐  ┌─────────────────┐       │
│  │  HYBRID   │  │ NLI MODEL  │  │ EVIDENCE        │       │
│  │  SEARCH   │  │ (Evidence  │  │ AGGREGATION     │       │
│  │           │  │  Scoring)  │  │ (Verdict Logic) │       │
│  └─────┬─────┘  └────────────┘  └─────────────────┘       │
│        │                                                    │
│        └────┬────────────────────┬──────────────┐          │
│             │                    │              │          │
│             ▼                    ▼              ▼          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           FTS + VECTOR SEARCH                        │ │
│  │  1. Full-Text Search (PostgreSQL)                    │ │
│  │  2. Vector Similarity (pgvector <-> operator)        │ │
│  │  3. Merge & Re-rank Results                          │ │
│  └──────────────┬───────────────────────────────────────┘ │
│                 │                                          │
│                 ▼                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │        EMBEDDING SERVICE (Singleton)                 │ │
│  │  - Lazy load sentence-transformers                   │ │
│  │  - Device detection (GPU/CPU/MPS)                    │ │
│  │  - Batch encoding with caching                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │    POSTGRESQL DATABASE        │
            ├───────────────────────────────┤
            │ ✓ claims                      │
            │ ✓ evidence                    │
            │ ✓ evidence_embeddings (NEW)   │
            │ ✓ verdicts (NEW results)      │
            │ ✓ verdict_evidence (NEW)      │
            │ ✓ pgvector indices (NEW)      │
            └───────────────────────────────┘
```

---

## ML Models Integration

```text
┌─────────────────────────────────────────────┐
│       EMBEDDING SERVICE                     │
│  sentence-transformers/all-MiniLM-L6-v2    │
│                                             │
│  Input:  Text/Claim                        │
│  Output: 384-dimensional vector            │
│  Speed:  ~1000 texts/second (CPU)          │
│  Memory: ~80MB model + batches              │
│  Device: Auto-detect GPU/CPU/MPS           │
│  Caching: Singleton pattern                │
│  Use: Embedding claims & evidence          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│       NLI VERIFIER                          │
│  microsoft/deberta-v3-base (MNLI)           │
│                                             │
│  Input:  (Premise, Hypothesis) pairs       │
│  Output: ENTAILMENT / NEUTRAL / CONTRADICTION
│  Speed:  >2 pairs/second (CPU, batched)     │
│  Memory: ~440MB model + batch               │
│  Device: Auto-detect GPU/CPU/MPS           │
│  Caching: Singleton pattern                │
│  Use: Evidence-Claim verification          │
│  Scores: All 3 probabilities returned      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│       PGVECTOR SEARCH                       │
│  PostgreSQL 15+ with pgvector               │
│                                             │
│  Input:  Query embedding (384-dim)         │
│  Output: Top-K similar evidence             │
│  Operator: <-> (cosine distance)           │
│  Speed:  <3 seconds for 10K corpus         │
│  Index:  IVFFlat (lists=100 tunable)       │
│  Score:  Cosine similarity (0-1)            │
│  Use: Evidence retrieval                    │
└─────────────────────────────────────────────┘
```

---

## Latency Budget Breakdown

```text
Target: <60 seconds total
Status: Design Phase

┌─────────────────────────────────────────────────┐
│ Component             │ Target │ Typical        │
├─────────────────────────────────────────────────┤
│ Claim Embedding       │ <1s    │ 0.5s           │
│ Evidence Retrieval    │ <3s    │ 2s             │
│ NLI Verification      │ <40s   │ 35s (bottleneck)
│ Verdict Aggregation   │ <1s    │ 0.5s           │
│ Database Storage      │ <2s    │ 1s             │
│ Network/Overhead      │ <5s    │ 3s             │
├─────────────────────────────────────────────────┤
│ TOTAL                 │ <60s   │ ~40s (typical) │
└─────────────────────────────────────────────────┘

Optimization Priority:
1. NLI inference (highest impact)
2. Evidence retrieval
3. Embedding generation
4. Database queries
```

---

## Risk Heat Map

```text
SEVERITY vs PROBABILITY

            MEDIUM              HIGH
             PROB               PROB
┌────────────────────────────────────────┐
│ Model Download Failures      ▲         │
│ (Med Impact)                 │         │
│                              │         │
│ pgvector Index Perf ◄────────┼─────────│
│ (Med Impact)        │        │         │
│                     │        │         │
│ Performance < 60s ◄─┘        │         │
│ (High Impact)                │         │
│                              │         │
│ Accuracy < 70% ◄─────────────┼────────▲
│ (High Impact)                │        │
│                              ▼        │
│ Memory > 4GB        Agent Unavail    │
│ (Med Impact)        (Med Impact)     │
│                                      │
└──────────────────────────────────────┘

Mitigation:
• Continuous performance monitoring
• Cross-training on critical paths
• Pre-download models in Docker
• Memory profiling early
• Regular checkpoint reviews
```

---

## File Structure (Created & Modified)

```text
truthgraph/
├── ml/
│   ├── __init__.py                    (NEW)
│   ├── embeddings.py                  (NEW - 320 lines)
│   └── verification.py                (NEW - 260 lines)
│
├── retrieval/
│   ├── __init__.py                    (NEW)
│   ├── vector_search.py               (NEW - 140 lines)
│   └── hybrid_search.py               (NEW - 180 lines)
│
├── verification/
│   ├── __init__.py                    (NEW)
│   ├── aggregation.py                 (NEW - 190 lines)
│   └── pipeline.py                    (NEW - 260 lines)
│
├── api/
│   ├── routes.py                      (MODIFIED - add verdict routes)
│   └── verification_routes.py         (NEW)
│
├── models.py                          (MODIFIED - add response models)
└── schemas.py                         (MODIFIED - add relations)

scripts/
└── embed_corpus.py                    (NEW - 170 lines)

docker/
├── api.Dockerfile                     (MODIFIED - add ML deps)
├── migrations/
│   └── 002_evidence_embeddings.sql    (NEW)
└── init-db.sql                        (MODIFIED - no changes needed)

tests/
├── unit/
│   ├── test_embeddings.py             (NEW)
│   ├── test_verification.py           (NEW)
│   ├── test_aggregation.py            (NEW)
│   └── test_vector_search.py          (NEW)
│
├── integration/
│   ├── test_verification_pipeline.py  (NEW)
│   ├── test_vector_search_e2e.py      (NEW)
│   ├── test_hybrid_search_e2e.py      (NEW)
│   └── test_api_verification.py       (NEW)
│
├── performance/
│   └── test_benchmarks.py             (NEW)
│
├── fixtures/
│   ├── test_claims.json               (NEW)
│   └── nli_test_pairs.json            (NEW)
│
└── conftest.py                        (NEW - pytest fixtures)

docs/
├── PHASE_2_IMPLEMENTATION_PLAN.md     (THIS FILE)
├── PERFORMANCE_TUNING.md              (NEW)
├── DOCKER_ML_SETUP.md                 (NEW)
└── TROUBLESHOOTING.md                 (NEW)

Total Files Created: ~30
Total Files Modified: ~5
Total Lines of Code: ~2000 (core + tests)
```

---

## Integration Test Data Requirements

```text
INITIAL DATA SETUP

Evidence Corpus (for testing):
  - Minimum: 100 evidence items
  - For benchmarking: 1000+ items
  - Source: Mix of real + synthetic
  - Content: Factual statements in various domains

Test Claims (with ground truth):
  - Supported claims: 5+ examples
  - Refuted claims: 5+ examples
  - Insufficient evidence: 3+ examples
  - Accuracy target: >70% on all

NLI Test Pairs:
  - Entailment pairs: 20+
  - Contradiction pairs: 20+
  - Neutral pairs: 20+
  - Known accuracy targets for each

Performance Test Corpus:
  - 10K evidence items
  - Known query times
  - Benchmark baseline
```

---

## Phase 3 Preparation (Post Phase 2)

```text
PHASE 2 COMPLETION ───→ PHASE 3 CONSIDERATIONS

What Phase 2 Enables:
  ✓ Basic end-to-end verification
  ✓ Single-hop reasoning
  ✓ Basic evidence aggregation
  ✓ Foundational ML pipeline

Phase 3 Enhancements (Future):
  □ Multi-hop reasoning
  □ Evidence quality scoring
  □ Temporal tracking
  □ Visualization
  □ Advanced aggregation strategies
  □ Fine-tuning on domain data
  □ Ensemble methods
  □ Distributed processing

Known Limitations (Phase 2):
  • Single hop only (no claim decomposition)
  • No temporal reasoning
  • No visualization
  • Fixed model parameters
  • No active learning

Documentation:
  - Leave hooks for future enhancements
  - Document aggregation threshold tuning
  - Note performance bottlenecks
  - Record accuracy edge cases
```

---

## Quick Troubleshooting Guide

```text
PROBLEM: Models fail to download
SOLUTION:
  1. Check HF_HOME environment variable
  2. Implement retry logic in model loading
  3. Pre-download during Docker build
  4. Check network connectivity

PROBLEM: Performance > 60s
SOLUTION:
  1. Profile with cProfile (likely NLI bottleneck)
  2. Increase batch size for NLI (up to 16)
  3. Reduce evidence items (try 5 instead of 10)
  4. Consider GPU deployment

PROBLEM: Accuracy < 70%
SOLUTION:
  1. Verify NLI label mapping matches model
  2. Check aggregation thresholds
  3. Validate test fixtures
  4. Analyze mismatches (false positives/negatives)

PROBLEM: Memory > 4GB
SOLUTION:
  1. Profile memory usage
  2. Add gc.collect() between batches
  3. Reduce batch sizes
  4. Check for memory leaks in async code

PROBLEM: Vector search too slow
SOLUTION:
  1. Check EXPLAIN ANALYZE query plans
  2. Tune IVFFlat index parameters
  3. Ensure indexes built correctly
  4. Monitor for sequential scans
```

---

## Deployment Checklist

```text
BEFORE PRODUCTION DEPLOYMENT

Functionality:
  ☐ All tests passing (>90%)
  ☐ All endpoints tested
  ☐ Error handling for edge cases
  ☐ Logging at critical points
  ☐ Database backup created

Performance:
  ☐ <60s latency validated
  ☐ >500 texts/s embedding throughput
  ☐ >2 pairs/s NLI throughput
  ☐ <4GB memory usage
  ☐ Concurrent load tested

Quality:
  ☐ >70% accuracy on test claims
  ☐ 100% type hints
  ☐ Zero linting errors
  ☐ >80% test coverage
  ☐ Code review approved

Infrastructure:
  ☐ Docker build successful
  ☐ Models cached in volume
  ☐ Environment variables set
  ☐ Health checks configured
  ☐ Monitoring enabled

Documentation:
  ☐ API documentation complete
  ☐ Deployment guide written
  ☐ Troubleshooting guide created
  ☐ Performance tuning documented
  ☐ Known limitations listed
```

---

**Status**: Ready for Immediate Implementation
**Next Step**: Brief all agents on their assignments
**Target Start**: Week 3 Monday
**Target Completion**: Week 5 Friday
**Estimated Team Effort**: 60-80 hours (with parallelization factor 1.8-2.4x)
