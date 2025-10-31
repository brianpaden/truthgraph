# Dataset & Testing Handoff

**Features**: 1.1-1.7
**Agents**: test-automator, python-pro
**Total Effort**: 56 hours
**Status**: 6 of 7 features complete (Features 1.1-1.6), Feature 1.7 ready to start
**Priority**: Critical path (Feature 1.7 blocks all performance optimization)

---

## Quick Navigation

**Master Index**: [v0_phase2_completion_handoff_MASTER.md](./v0_phase2_completion_handoff_MASTER.md)
**Quick Start**: [v0_phase2_quick_start.md](./v0_phase2_quick_start.md)
**Dependencies**: [dependencies_and_timeline.md](./dependencies_and_timeline.md)
**All Assignments**: [agent_assignments.md](./agent_assignments.md)

**Related Handoffs**:
- [2_performance_optimization_handoff.md](./2_performance_optimization_handoff.md) (depends on Feature 1.7)
- [3_validation_framework_handoff.md](./3_validation_framework_handoff.md) (uses test data from 1.1-1.4)

---

## Category Overview

This handoff covers the data infrastructure for Phase 2. Features 1.1-1.4 (test data creation) are already complete. Feature 1.5-1.7 (corpus loading, sample data, benchmarking) are ready to start immediately with no blockers.

### Completed Features (Review Only)

**Features 1.1-1.6 are archived in [completed_features_reference.md](./completed_features_reference.md)**

- ✓ 1.1: Test Claims Dataset Fixture
- ✓ 1.2: FEVER Dataset Integration
- ✓ 1.3: Real-World Claims Validation
- ✓ 1.4: Edge Case Corpus
- ✓ 1.5: Corpus Loading Script
- ✓ 1.6: Sample Corpus Creation

### Next Priority Features

**Feature 1.7: Benchmark Baseline Establishment** - READY TO START NOW
- Status: 📋 Planned
- Assigned To: python-pro
- Estimated Effort: 6 hours
- Complexity: Medium
- Blocker Status: **No blockers - highest priority**

---

## Feature 1.7: Benchmark Baseline Establishment

### Overview

Establish performance baselines for all major components. This feature is critical because:

1. **Unblocks all optimization work** - Features 2.1-2.6 depend on baseline measurements
2. **Defines success targets** - Baselines are the reference for regression detection
3. **Foundation for comparison** - All future performance work compares against these baselines

### Requirements

- Measure embedding throughput
- Measure NLI inference speed
- Measure vector search latency
- Measure end-to-end pipeline latency
- Document baseline results
- Create tracking system for regression detection

### Architecture

```text
scripts/benchmarks/
├── benchmark_embeddings.py
├── benchmark_nli.py
├── benchmark_vector_search.py
├── benchmark_pipeline.py
├── results/
│   ├── baseline_2025-10-27.json
│   └── comparison.csv
└── README.md
```

### Success Criteria

- [x] All components benchmarked
- [x] Results match or exceed performance targets:
  - Embedding throughput: >500 texts/sec
  - NLI inference: >2 pairs/sec
  - Vector search: <3 sec for 10K items
  - End-to-end: <60 sec
- [x] Baselines documented
- [x] Regression detection working
- [x] Comparison framework created

### Implementation Plan

1. Create benchmarking framework
2. Benchmark embedding throughput (target: >500/sec)
3. Benchmark NLI speed (target: >2 pairs/sec)
4. Benchmark vector search (target: <3 sec for 10K items)
5. Benchmark end-to-end (target: <60 sec)
6. Document baseline results
7. Create regression detection script
8. Set up automated baseline tracking

### Performance Targets

| Component | Target | Notes |
|-----------|--------|-------|
| Embedding Throughput | >500 texts/sec | On CPU with batch processing |
| NLI Inference | >2 pairs/sec | Natural Language Inference |
| Vector Search | <3 sec | For 10K items in database |
| End-to-End Pipeline | <60 sec | Complete verification workflow |
| Memory Usage | <4GB | With all models loaded |

### Testing Requirements

- Benchmark reproducibility (run multiple times, consistent results)
- Result validation (compare against published model benchmarks)
- Documentation completeness

### Testing Code Template

```python
import pytest
from tests.benchmarks.benchmark_embeddings import BenchmarkEmbeddings
from tests.benchmarks.benchmark_pipeline import BenchmarkPipeline

def test_embedding_throughput():
    """Test embedding throughput meets target."""
    benchmark = BenchmarkEmbeddings()
    results = benchmark.run_throughput_test()

    # Target: >500 texts/sec
    assert results['throughput_per_sec'] > 500

    print(f"Embedding throughput: {results['throughput_per_sec']:.1f} texts/sec")

def test_nli_throughput():
    """Test NLI inference speed meets target."""
    benchmark = BenchmarkNLI()
    results = benchmark.run_inference_test()

    # Target: >2 pairs/sec
    assert results['pairs_per_sec'] > 2

    print(f"NLI throughput: {results['pairs_per_sec']:.2f} pairs/sec")

def test_vector_search_latency():
    """Test vector search latency meets target."""
    benchmark = BenchmarkVectorSearch()
    results = benchmark.run_search_test(corpus_size=10000)

    # Target: <3 seconds for 10K items
    assert results['avg_latency_sec'] < 3

    print(f"Vector search latency: {results['avg_latency_sec']:.2f} sec")

def test_e2e_pipeline_latency():
    """Test end-to-end pipeline latency meets target."""
    benchmark = BenchmarkPipeline()
    results = benchmark.run_pipeline_test()

    # Target: <60 seconds
    assert results['total_latency_sec'] < 60

    print(f"E2E pipeline latency: {results['total_latency_sec']:.1f} sec")
```

### Key Files to Create/Modify

1. `scripts/benchmarks/benchmark_embeddings.py` (200 lines)
   - EmbeddingBenchmark class
   - Throughput measurement methods
   - Results tracking

2. `scripts/benchmarks/benchmark_nli.py` (180 lines)
   - NLI inference benchmarking
   - Batch size testing
   - Accuracy validation during benchmarking

3. `scripts/benchmarks/benchmark_vector_search.py` (200 lines)
   - Vector search latency measurement
   - Different corpus sizes
   - Index configuration testing

4. `scripts/benchmarks/benchmark_pipeline.py` (220 lines)
   - End-to-end pipeline benchmarking
   - Component timing breakdown
   - Latency attribution

5. `scripts/benchmarks/results/baseline_2025-10-27.json`
   - JSON with baseline results
   - Component breakdowns
   - Metadata (date, system, models used)

6. `scripts/benchmarks/README.md` (150 lines)
   - How to run benchmarks
   - Interpreting results
   - Setting new baselines

### Dependencies

- All ML services must be implemented
- Test corpus (from Feature 1.5 or 1.6)
- Verification pipeline service

### What This Enables

Once Feature 1.7 completes, these features can start immediately:
- Feature 2.1: Embedding Service Profiling
- Feature 2.2: NLI Service Optimization
- Feature 2.3: Vector Search Index Optimization
- Feature 2.4: Pipeline End-to-End Optimization
- Feature 2.5: Memory Optimization & Analysis
- Feature 2.6: Database Query Optimization

---

## Implementation Workflow

### For test-automator (Features 1.1-1.4)

**Status**: All complete! ✓

See [completed_features_reference.md](./completed_features_reference.md) for summaries and outcomes.

### For python-pro (Features 1.5-1.7)

**Feature 1.5 Status**: ✓ Complete
**Feature 1.6 Status**: ✓ Complete
**Feature 1.7 Status**: 📋 Ready to start

**Next Steps for python-pro**:

1. Review Features 1.5-1.6 completion summaries in [completed_features_reference.md](./completed_features_reference.md)
2. Start Feature 1.7 (Benchmark Baseline) immediately - no blockers
3. Ensure benchmarks use test data from Features 1.5-1.6
4. When Feature 1.7 completes, immediately notify test-automator that Feature 3.1 can start
5. Then move to [2_performance_optimization_handoff.md](./2_performance_optimization_handoff.md) for Features 2.1-2.6

---

## Related Files & Documentation

### Test Data Locations

From completed features (1.1-1.4):
- `tests/fixtures/test_claims.json` - 25 test claims with verdicts
- `tests/fixtures/fever_sample_claims.json` - 25 FEVER claims
- `tests/accuracy/real_world_claims.json` - 28 real-world validated claims
- `tests/fixtures/edge_cases/` - 7 edge case categories with 34 claims

### Corpus Data Locations

From completed features (1.5-1.6):
- `data/samples/evidence_corpus.json` - 250 evidence documents
- `data/samples/evidence_corpus.csv` - Same data in CSV format
- `scripts/embed_corpus.py` - Production-ready corpus loader

### Performance References

For benchmarking, reference these model speeds:
- Sentence Transformers (embeddings): ~1,000 texts/sec on CPU (with optimization)
- XLNET-based NLI: ~5 pairs/sec on CPU (with batch size 8)
- pgvector search: <1 sec for 10K items (with proper indexing)

### Documentation References

- [Performance Testing Guide](../../../docs/guides/performance-testing.md)
- [Benchmarking Standards](../../../docs/performance/benchmarking-standards.md)
- [Profiling Guide](../../../docs/guides/profiling.md)

---

## Progress Tracking

### Completion Checklist for Feature 1.7

- [ ] Create benchmarking framework
- [ ] Implement embedding throughput benchmark
- [ ] Implement NLI inference benchmark
- [ ] Implement vector search latency benchmark
- [ ] Implement end-to-end pipeline benchmark
- [ ] Collect baseline results
- [ ] Document baseline results in JSON
- [ ] Create regression detection script
- [ ] Set up comparison framework
- [ ] Write documentation
- [ ] All tests passing
- [ ] Feature marked complete

### Handoff Completion Checklist

- [ ] Feature 1.7 complete
- [ ] Baselines documented
- [ ] Regression detection working
- [ ] All benchmarking code merged
- [ ] Ready for Features 2.1-2.6 to start

---

## Frequently Asked Questions

**Q: Why is Feature 1.7 so important?**
A: It blocks all 6 optimization features. Without baselines, we can't measure optimization improvements or detect regressions.

**Q: Can features 2.1-2.6 start before 1.7 is complete?**
A: No, they all depend on 1.7 baselines. This is the critical path.

**Q: How long should each benchmark take to run?**
A: Each individual benchmark (embedding, NLI, search) should take 5-15 seconds. Full suite should complete in ~2 minutes.

**Q: Where do I run the benchmarks?**
A: Create `scripts/benchmarks/run_all.py` that runs all benchmarks and produces a report.

**Q: What if benchmarks don't meet targets?**
A: Document the actual numbers and proceed. Optimization work (Features 2.1-2.6) will improve them.

---

## Related Files

**For Background Context**:
- [completed_features_reference.md](./completed_features_reference.md) - Features 1.1-1.6 details
- [dependencies_and_timeline.md](./dependencies_and_timeline.md) - Full dependency graph
- [agent_assignments.md](./agent_assignments.md) - All agent deliverables

**For Next Steps**:
- [2_performance_optimization_handoff.md](./2_performance_optimization_handoff.md) - Features 2.1-2.6
- [3_validation_framework_handoff.md](./3_validation_framework_handoff.md) - Features 3.1-3.5

---

**Navigation**: [Master Index](./v0_phase2_completion_handoff_MASTER.md) | [Quick Start](./v0_phase2_quick_start.md) | [Dependencies](./dependencies_and_timeline.md) | [Next: Performance](./2_performance_optimization_handoff.md)
