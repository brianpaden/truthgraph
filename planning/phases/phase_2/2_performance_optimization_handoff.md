# Performance Optimization Handoff

**Features**: 2.1-2.6
**Agent**: python-pro
**Total Effort**: 56 hours
**Status**: Planned (blocked by Feature 1.7)
**Priority**: High (critical for performance targets)

---

## Quick Navigation

**Master Index**: [v0_phase2_completion_handoff_MASTER.md](./v0_phase2_completion_handoff_MASTER.md)
**Quick Start**: [v0_phase2_quick_start.md](./v0_phase2_quick_start.md)
**Dataset & Testing**: [1_dataset_and_testing_handoff.md](./1_dataset_and_testing_handoff.md)
**Dependencies**: [dependencies_and_timeline.md](./dependencies_and_timeline.md)

**Related Handoffs**:
- [1_dataset_and_testing_handoff.md](./1_dataset_and_testing_handoff.md) (Feature 1.7 baseline blocks this)
- [3_validation_framework_handoff.md](./3_validation_framework_handoff.md) (accuracy framework)

---

## Category Overview

Performance optimization is critical to Phase 2 success. All 6 features target key performance bottlenecks:

1. **Feature 2.1**: Embedding throughput >500 texts/sec
2. **Feature 2.2**: NLI inference >2 pairs/sec
3. **Feature 2.3**: Vector search <3 sec for 10K items
4. **Feature 2.4**: End-to-end pipeline <60 seconds
5. **Feature 2.5**: Memory usage <4GB
6. **Feature 2.6**: Database query optimization -30% latency

### Execution Order

These features run in parallel but with dependencies:

**Phase 1 (Days 1-2, parallel)**:
- Feature 2.1: Embedding Service Profiling
- Feature 2.2: NLI Service Optimization
- Feature 2.3: Vector Search Index Optimization
- Feature 2.5: Memory Optimization & Analysis

**Phase 2 (Days 3-4, parallel)**:
- Feature 2.4: Pipeline End-to-End Optimization (depends on 2.1-2.3)
- Feature 2.6: Database Query Optimization

---

## Feature 2.1: Embedding Service Profiling

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: Depends on Feature 1.7

### Description

Profile and optimize embedding generation for throughput and memory.

### Requirements

- Identify bottlenecks in embedding generation
- Optimize batch sizes for CPU/GPU
- Reduce memory footprint
- Improve throughput to >500 texts/sec target
- Document optimization decisions
- Create profiling utilities

### Architecture

```text
scripts/profile/
├── profile_embeddings.py     # Profiling script
├── profile_nli.py            # NLI profiling
├── memory_analyzer.py        # Memory tracking
├── results/
│   ├── embedding_profile.txt
│   ├── memory_usage.json
│   └── optimization_log.md
└── README.md
```

### Implementation Steps

1. Create profiling framework with cProfile/pyinstrument
2. Profile embedding generation with various batch sizes
3. Identify CPU vs GPU bottlenecks
4. Test batch sizes: 8, 16, 32, 64, 128
5. Measure memory usage per batch
6. Test with different text lengths
7. Optimize based on findings
8. Document recommendations
9. Create automated profiling script
10. Validate improvements against baseline (Feature 1.7)

### Success Criteria

- Embedding throughput >500 texts/sec
- Memory usage documented
- Batch size recommendations provided
- Optimization documented
- Profiling script functional
- Results validated against Feature 1.7 baseline

### Key Testing Points

```python
def test_embedding_throughput_improvement():
    """Verify embedding throughput meets target."""
    baseline = load_baseline('baseline_2025-10-27.json')
    current = measure_embedding_throughput()

    assert current['throughput_per_sec'] >= baseline['embedding_throughput']
    assert current['throughput_per_sec'] > 500

def test_memory_usage_acceptable():
    """Verify memory stays within bounds."""
    memory_profile = profile_memory_with_embeddings()

    assert memory_profile['peak_memory_gb'] < 4
    assert memory_profile['per_batch_memory_mb'] < 500
```

---

## Feature 2.2: NLI Service Optimization

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: Depends on Feature 1.7

### Description

Optimize NLI inference for speed and accuracy.

### Requirements

- Profile NLI inference
- Find optimal batch size (target: 8 for CPU)
- Test with different input formats
- Optimize token handling
- Improve throughput to >2 pairs/sec
- Document optimization decisions
- Maintain accuracy (no degradation)

### Architecture

```text
scripts/profile/
├── profile_nli.py            # NLI profiling
├── nli_batch_optimization.py # Batch testing
├── results/
│   ├── nli_profile.txt
│   ├── batch_analysis.json
│   └── optimization_log.md
└── README.md
```

### Implementation Steps

1. Create NLI profiling framework
2. Test inference with batch sizes: 1, 4, 8, 16, 32
3. Profile token handling and padding
4. Test various input lengths
5. Measure accuracy vs batch size (should not degrade)
6. Find GPU/CPU optimal points
7. Document batch size recommendations
8. Create automated testing
9. Validate against accuracy benchmarks
10. Document final optimization

### Success Criteria

- NLI throughput >2 pairs/sec
- Batch size recommendations documented
- Accuracy maintained across batch sizes
- Profile completed and analyzed
- Optimization script created
- No accuracy degradation

### Key Testing Points

```python
def test_nli_throughput_improvement():
    """Verify NLI throughput meets target."""
    baseline = load_baseline('baseline_2025-10-27.json')
    current = measure_nli_throughput()

    assert current['pairs_per_sec'] >= baseline['nli_throughput']
    assert current['pairs_per_sec'] > 2

def test_nli_accuracy_maintained():
    """Verify accuracy doesn't degrade with optimization."""
    baseline_accuracy = load_baseline_accuracy()
    current_accuracy = measure_nli_accuracy_optimized()

    # Allow 1% accuracy loss due to optimization
    assert current_accuracy >= baseline_accuracy - 0.01
```

---

## Feature 2.3: Vector Search Index Optimization

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 10 hours
**Complexity**: Medium
**Blocker Status**: Depends on Feature 1.7

### Description

Optimize pgvector index parameters for search performance.

### Requirements

- Test IVFFlat index configurations
- Measure search latency with 10k+ items
- Optimize lists parameter
- Optimize probes parameter
- Balance accuracy vs speed
- Document recommendations
- Create benchmark with different corpus sizes

### Architecture

```text
scripts/benchmarks/
├── benchmark_vector_search.py
├── index_optimization.py     # IVFFlat parameter tuning
├── results/
│   ├── index_params.json
│   ├── search_latency.csv
│   └── optimization_report.md
└── README.md
```

### Implementation Steps

1. Create index configuration testing framework
2. Test IVFFlat with lists: 10, 25, 50, 100
3. Test probes: 1, 5, 10, 25
4. Measure search latency for each combination
5. Test with corpus sizes: 1k, 5k, 10k, 50k items
6. Measure accuracy impact of parameters
7. Document optimal configurations
8. Create automated index creation script
9. Test index rebuild performance
10. Validate improvements

### Success Criteria

- Search latency <3 seconds for 10k items
- Index parameters optimized
- Recommendations documented
- Testing framework created
- Automation script operational
- Results validated against baseline

### Key Testing Points

```python
def test_vector_search_latency():
    """Verify vector search meets latency target."""
    baseline = load_baseline('baseline_2025-10-27.json')
    current = measure_vector_search_latency(corpus_size=10000)

    assert current['avg_latency_sec'] <= baseline['search_latency']
    assert current['avg_latency_sec'] < 3

def test_search_accuracy_acceptable():
    """Verify search accuracy with optimized parameters."""
    optimal_params = {'lists': 50, 'probes': 10}
    accuracy = measure_search_accuracy(optimal_params)

    # Top-1 recall should be >95%
    assert accuracy['top1_recall'] > 0.95
```

---

## Feature 2.4: Pipeline End-to-End Optimization

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 10 hours
**Complexity**: Medium
**Blocker Status**: Depends on Features 2.1-2.3

### Description

Optimize complete verification pipeline for <60 second target.

### Requirements

- Profile each pipeline stage
- Identify bottlenecks
- Optimize critical path
- Parallelize independent operations
- Reduce database round-trips
- Implement caching where appropriate
- Document optimization decisions

### Architecture

```text
truthgraph/verification/
├── pipeline.py               # Optimized pipeline
├── pipeline_optimizer.py     # Optimization utilities
└── caching.py               # Caching layer (if needed)

scripts/profile/
├── profile_pipeline.py       # Pipeline profiling
├── pipeline_analysis.py      # Bottleneck analysis
└── results/
    ├── pipeline_profile.json
    └── optimization_report.md
```

### Implementation Steps

1. Profile complete pipeline with cProfile
2. Identify slowest stages
3. Test parallel evidence retrieval
4. Optimize database queries
5. Implement query result caching (if beneficial)
6. Reduce API calls
7. Optimize evidence filtering
8. Test with 20 test claims
9. Measure improvement at each step
10. Document final optimization

### Success Criteria

- End-to-end latency <60 seconds
- Bottlenecks identified and documented
- Optimization improvements measured
- Profile analysis complete
- Recommendations implemented
- Results validated

### Key Testing Points

```python
def test_pipeline_latency():
    """Verify end-to-end pipeline meets latency target."""
    baseline = load_baseline('baseline_2025-10-27.json')
    current = measure_pipeline_latency()

    assert current['total_latency_sec'] <= baseline['e2e_latency']
    assert current['total_latency_sec'] < 60

def test_pipeline_component_timing():
    """Verify timing of each pipeline stage."""
    timing = measure_component_timing()

    # Each component should improve or stay same
    baseline_timing = load_baseline_timing()
    for component, current_time in timing.items():
        assert current_time <= baseline_timing[component] * 1.05  # Allow 5% variance
```

---

## Feature 2.5: Memory Optimization & Analysis

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 6 hours
**Complexity**: Medium
**Blocker Status**: Depends on Feature 1.7

### Description

Analyze and optimize memory usage across the system.

### Requirements

- Measure memory usage with loaded models
- Analyze per-component memory footprint
- Test under load (100+ concurrent claims)
- Implement memory monitoring
- Create alerts for memory leaks
- Document memory characteristics
- Validate <4GB target

### Architecture

```text
truthgraph/monitoring/
├── memory_monitor.py         # Memory tracking
├── memory_alerts.py          # Alert system
└── memory_profiles.py        # Historical tracking

scripts/profile/
├── analyze_memory_usage.py
└── results/
    ├── memory_profile.json
    └── memory_report.md
```

### Implementation Steps

1. Create memory monitoring utilities
2. Measure baseline memory with loaded models
3. Test embedding batch processing memory
4. Test NLI inference memory
5. Test with 100 concurrent items
6. Identify memory leaks
7. Implement memory optimization
8. Create continuous monitoring
9. Set up alerting
10. Document findings

### Success Criteria

- Memory usage <4GB validated
- Per-component memory measured
- Memory monitoring implemented
- Leaks identified and fixed
- Documentation complete
- No leaks detected in load testing

### Key Testing Points

```python
def test_memory_usage_limit():
    """Verify memory stays under 4GB limit."""
    memory_usage = measure_memory_with_loaded_models()

    assert memory_usage['peak_memory_gb'] < 4
    assert memory_usage['steady_state_memory_gb'] < 3.5

def test_no_memory_leaks():
    """Verify no memory leaks in long-running processes."""
    memory_trend = measure_memory_trend(duration_minutes=30)

    # Memory should stabilize, not grow unbounded
    assert memory_trend['growth_rate_mb_per_min'] < 10
```

---

## Feature 2.6: Database Query Optimization

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: Can run in parallel with Feature 2.4

### Description

Optimize database queries for evidence retrieval and verdict storage.

### Requirements

- Analyze query performance
- Create appropriate indexes
- Optimize join operations
- Reduce N+1 queries
- Batch database operations
- Document optimization decisions
- Measure query improvement

### Architecture

```text
truthgraph/db/
├── queries.py               # Optimized queries
├── query_builder.py        # Query optimization utilities
└── indexes.sql             # Index definitions

scripts/benchmarks/
├── benchmark_queries.py
└── results/
    ├── query_performance.json
    └── optimization_report.md
```

### Implementation Steps

1. Analyze current queries with EXPLAIN ANALYZE
2. Identify slow queries
3. Create missing indexes
4. Optimize join operations
5. Implement batch operations
6. Reduce round-trips
7. Test query performance
8. Validate accuracy
9. Document recommendations
10. Measure improvement

### Success Criteria

- Query latency reduced by 30%+
- No N+1 queries remaining
- Indexes optimized
- Batch operations implemented
- Documentation complete
- Results validated

### Key Testing Points

```python
def test_query_latency_improvement():
    """Verify query performance improves by 30%."""
    baseline = load_baseline_query_performance()
    current = measure_query_performance()

    improvement = (baseline - current) / baseline
    assert improvement >= 0.30  # 30% improvement

def test_no_n_plus_one_queries():
    """Verify N+1 query patterns are eliminated."""
    query_log = profile_queries()

    for query_group in query_log.get_duplicate_queries():
        # No query should appear more than once per batch
        assert query_group['count'] <= 1
```

---

## Execution Timeline

### Week 1 (Days 1-2): Parallel Profiling

**All of these run in parallel**:
- Feature 2.1: Embedding profiling (8h)
- Feature 2.2: NLI optimization (8h)
- Feature 2.3: Vector search optimization (10h)
- Feature 2.5: Memory optimization (6h)

**Dependencies**: Feature 1.7 must be complete before starting

### Week 2 (Days 3-4): Integration & E2E

**Start after Week 1 complete**:
- Feature 2.4: Pipeline optimization (10h) - depends on 2.1-2.3
- Feature 2.6: Database optimization (8h) - parallel with 2.4

### Expected Outcomes

- All individual components optimized
- End-to-end pipeline meets <60 sec target
- Memory stays under 4GB
- Database queries optimized
- Performance improvements documented
- Ready for validation testing (Feature 3.1)

---

## Progress Tracking

### Completion Checklist

- [ ] Feature 1.7 (baseline) complete and available
- [ ] Feature 2.1 complete
- [ ] Feature 2.2 complete
- [ ] Feature 2.3 complete
- [ ] Feature 2.5 complete
- [ ] All parallel optimizations validated
- [ ] Feature 2.4 complete
- [ ] Feature 2.6 complete
- [ ] All features integrated
- [ ] All tests passing
- [ ] All features marked complete

### Key Validation Points

After each feature:
- Baseline comparison (improvement or maintained)
- Test coverage >80%
- No performance regressions
- Memory usage acceptable
- All related tests passing

---

## Related Files

**For Background Context**:
- [1_dataset_and_testing_handoff.md](./1_dataset_and_testing_handoff.md) - Feature 1.7 baseline
- [dependencies_and_timeline.md](./dependencies_and_timeline.md) - Full dependency graph
- [agent_assignments.md](./agent_assignments.md) - All deliverables

**For Next Steps**:
- [3_validation_framework_handoff.md](./3_validation_framework_handoff.md) - Validation testing
- [success_criteria_and_risks.md](./success_criteria_and_risks.md) - Success targets

---

**Navigation**: [Master Index](./v0_phase2_completion_handoff_MASTER.md) | [Quick Start](./v0_phase2_quick_start.md) | [Dependencies](./dependencies_and_timeline.md) | [Previous: Dataset](./1_dataset_and_testing_handoff.md) | [Next: Validation](./3_validation_framework_handoff.md)
