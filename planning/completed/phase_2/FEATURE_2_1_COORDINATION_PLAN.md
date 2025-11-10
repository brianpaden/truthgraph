# Feature 2.1: Embedding Service Profiling
## Comprehensive Coordination & Implementation Plan

**Date**: October 31, 2025
**Coordinator**: Context Manager (Anthropic Claude)
**Status**: READY TO START - NO BLOCKERS
**Agent**: python-pro
**Estimated Duration**: 8 hours
**Priority**: CRITICAL PATH

---

## EXECUTIVE SUMMARY

Feature 2.1 (Embedding Service Profiling) is the first Phase 2 performance optimization feature. With Feature 1.7 (Benchmark Baseline) now complete, this feature is **immediately unblocked and ready to start**.

### Current Status
- **Feature 1.7 Status**: COMPLETE (Oct 31, 2025) ✓
- **Current Baselines**: Embeddings 1,185 texts/sec (EXCEEDED 500 target by 137%)
- **Blockers**: NONE - Ready to start immediately
- **Phase 2 Progress**: 26% (7/27 features)

### Mission
Profile the embedding service to identify optimization opportunities and document recommendations for batch size, text length handling, and memory management.

### Success Criteria
- Identify current bottlenecks in embedding generation
- Test batch sizes: 8, 16, 32, 64, 128, 256
- Document memory usage per batch configuration
- Provide clear optimization recommendations
- Validate findings against Feature 1.7 baseline (1,185 texts/sec)
- Create reusable profiling utilities for other services

---

## CONTEXT & REQUIREMENTS

### Phase 2 Context

**Phase 2 Categories** (242 hours total):
1. ✓ Dataset & Testing (56h) - COMPLETE
2. **Performance Optimization** (56h) - IN PROGRESS
   - Feature 2.1: Embedding Service Profiling (8h) - **YOU ARE HERE**
   - Feature 2.2: NLI Service Optimization (8h)
   - Feature 2.3: Vector Search Index Optimization (10h)
   - Feature 2.4: Pipeline End-to-End Optimization (10h)
   - Feature 2.5: Memory Optimization & Analysis (6h)
   - Feature 2.6: Database Query Optimization (8h)
3. Validation Framework (52h) - PENDING
4. API Completion (44h) - PENDING
5. Documentation (34h) - PENDING

### Feature 2.1 Dependencies

**Depends On**:
- Feature 1.7 (Benchmark Baseline) - **COMPLETE ✓**
  - Baseline data: `scripts/benchmarks/results/baseline_embeddings_2025-10-27.json`
  - Baseline throughput: 1,185 texts/sec
  - Baseline latency: 6.66ms per single text
  - Peak memory: 537.9 MB

**Blocks**:
- Feature 2.4 (Pipeline E2E Optimization) - needs profiling results
- Potentially Features 2.5, 2.6 if optimization changes are made

**Parallel With**:
- Features 2.2, 2.3, 2.5 - can run simultaneously

### Execution Constraints

- **Duration**: 8 hours
- **Team**: 1 agent (python-pro)
- **Resources**: Access to embedding service, test data, profiling tools
- **No External Dependencies**: All tools already in project

---

## CURRENT CODEBASE STATE

### What Exists (Already Implemented)

#### 1. EmbeddingService (Core Component)
**File**: `c:\repos\truthgraph\truthgraph\services\ml\embedding_service.py`

**Key Details**:
- Singleton pattern (one model instance per process)
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Output: 384-dimensional embeddings (normalized)
- Batch processing support built-in
- Device detection: CUDA/MPS/CPU auto-detection
- Current performance: 1,185 texts/sec (batch 64)

**Methods**:
- `embed_text(text: str) -> list[float]` - Single text
- `embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]` - Multiple texts
- `get_device() -> str` - Current device (cpu/cuda/mps)

**Current Configuration**:
```python
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
DEFAULT_BATCH_SIZE = 64
EMBEDDING_NORMALIZE = True
```

#### 2. Benchmark Framework (Partially Complete)
**Files**: `c:\repos\truthgraph\scripts\benchmarks\`

**Existing**:
- ✓ `benchmark_embeddings.py` (474 lines) - Already benchmarks embeddings
- ✓ `compare_results.py` - Regression detection framework
- ✓ `run_all_benchmarks.py` - Orchestration script

**Current Baseline Data**:
- `baseline_embeddings_2025-10-27.json` - Reference performance
- Results tracked by timestamp

#### 3. Model Cache Service
**File**: `c:\repos\truthgraph\truthgraph\services\ml\model_cache.py`

**Purpose**: Cache loaded models to avoid reloading

**Relevant Methods**:
- `get_or_create_model()` - Retrieve cached model
- `memory_usage()` - Current memory footprint
- `clear_cache()` - Clear loaded models

#### 4. Test Data
**Locations**:
- `tests/fixtures/test_claims.json` - 25 test claims
- `data/samples/evidence_corpus.json` - 250 evidence documents
- `tests/accuracy/real_world_claims.json` - 28 real-world claims

---

## WHAT NEEDS TO BE DONE

### Feature 2.1 Deliverables

#### 1. Profiling Scripts (Primary Deliverable)

**Script 1: `profile_embeddings.py`** (200-250 lines)
```
Location: c:\repos\truthgraph\scripts\profile\
Purpose: Deep profiling of embedding service with cProfile and memory tracking
Outputs:
  - HTML call graph visualization
  - JSON profiling results
  - Memory usage breakdown
Features:
  - Test batch sizes: 8, 16, 32, 64, 128, 256
  - Measure CPU time per component
  - Track memory allocation
  - Identify bottlenecks
```

**Script 2: `memory_analyzer.py`** (150-200 lines)
```
Location: c:\repos\truthgraph\scripts\profile\
Purpose: Detailed memory profiling and leak detection
Outputs:
  - Memory profile JSON
  - Peak memory per batch size
  - Memory growth patterns
Features:
  - Track peak memory usage
  - Monitor per-batch memory
  - Detect memory leaks
  - Compare across batch sizes
```

**Script 3: `profile_text_length_impact.py`** (100-150 lines)
```
Location: c:\repos\truthgraph\scripts\profile\
Purpose: Measure how text length affects performance
Outputs:
  - Performance by text length
  - Throughput vs text length graph data
  - Recommendations for truncation
Features:
  - Test text lengths: 10, 50, 256, 512, 1024
  - Measure throughput impact
  - Identify sweet spots
```

#### 2. Documentation & Analysis

**File 1: `PROFILING_REPORT.md`** (400-500 lines)
```
Contents:
- Executive summary of findings
- Detailed profiling results
- Batch size recommendations
- Memory usage breakdown
- Text length impact analysis
- CPU bottleneck identification
- Optimization recommendations
- Quick wins identified
```

**File 2: `OPTIMIZATION_LOG.md`** (200-300 lines)
```
Contents:
- Date and methodology
- Profiling conditions (device, system)
- Batch size test results table
- Memory usage comparison
- Performance bottlenecks found
- Recommended improvements
```

**File 3: Inline code comments** in profiling scripts
```
- Explain profiling methodology
- Document parameter choices
- Explain output metrics
- Reference baseline comparisons
```

#### 3. Results & Metrics (JSON Format)

**File: `embedding_profile.json`**
```json
{
  "metadata": {
    "timestamp": "2025-10-31T...",
    "device": "cpu|cuda|mps",
    "system": "...",
    "baseline_throughput": 1185.0
  },
  "batch_size_analysis": {
    "8": { "throughput": X, "latency_p50": X, "memory_mb": X },
    "16": { ... },
    "32": { ... },
    "64": { ... },
    "128": { ... },
    "256": { ... }
  },
  "bottlenecks": [
    {
      "component": "model.forward()",
      "time_percent": 45.3,
      "suggestions": [...]
    },
    ...
  ],
  "recommendations": [
    {
      "optimization": "batch_size_tuning",
      "expected_improvement": "10-20%",
      "effort": "low",
      "priority": "high"
    },
    ...
  ]
}
```

#### 4. Baseline Validation

**Create comparison report**: Compare current measurements against Feature 1.7 baseline
- Ensure consistent methodology
- Document any variance reasons
- Validate no regression

---

## IMPLEMENTATION PLAN (8 hours)

### Hour 1-1.5: Setup & Baseline Understanding
**Tasks**:
1. Review Feature 1.7 baseline data structure and results
2. Understand existing benchmark_embeddings.py (already created)
3. Review EmbeddingService implementation
4. Identify profiling tools: cProfile, memory_profiler, psutil
5. Set up scripts/profile/ directory structure

**Deliverables**:
- Profile directory structure created
- Baseline data loaded and understood
- Profiling methodology documented

### Hour 1.5-3: Batch Size Profiling
**Tasks**:
1. Create `profile_embeddings.py` with cProfile integration
2. Implement batch size tests (8, 16, 32, 64, 128, 256)
3. Measure:
   - Throughput (texts/sec)
   - Latency (ms per batch)
   - Memory usage per batch
   - CPU time breakdown
4. Generate profiling output (HTML, JSON)
5. Run tests with Feature 1.7 test data (1000 texts)

**Deliverables**:
- profile_embeddings.py script complete
- Batch size test results (all sizes tested)
- Profiling output files

### Hour 3-4.5: Memory Analysis & Text Length Impact
**Tasks**:
1. Create `memory_analyzer.py`
   - Track memory over time
   - Detect peaks and valleys
   - Monitor for leaks
2. Create `profile_text_length_impact.py`
   - Test text lengths: 10, 50, 256, 512, 1024 chars
   - Measure throughput impact
   - Identify optimal range
3. Analyze memory patterns from results

**Deliverables**:
- memory_analyzer.py complete
- profile_text_length_impact.py complete
- Memory and text length analysis results

### Hour 4.5-7: Analysis & Documentation
**Tasks**:
1. Analyze all profiling results
2. Identify bottlenecks:
   - Tokenization overhead
   - Model forward pass time
   - Memory allocation patterns
3. Document findings in `PROFILING_REPORT.md`:
   - Batch size recommendations
   - Optimal memory configuration
   - Text length truncation strategy
   - Identification of quick wins
4. Compare against Feature 1.7 baseline
   - Validate consistency
   - Document any variance
5. Create `OPTIMIZATION_LOG.md` with actionable steps

**Deliverables**:
- PROFILING_REPORT.md (400+ lines)
- OPTIMIZATION_LOG.md (200+ lines)
- Analysis of bottlenecks
- Recommendations with estimated impact

### Hour 7-8: Integration & Validation
**Tasks**:
1. Package profiling scripts:
   - Add command-line arguments
   - Error handling
   - Progress output
2. Create README for profile directory
3. Validate profiling results:
   - Run against baseline
   - Check consistency
   - Verify no anomalies
4. Documentation review:
   - Ensure clarity
   - Add usage examples
   - Cross-reference Feature 1.7
5. Commit and prepare for Feature 2.4

**Deliverables**:
- All scripts production-ready
- README.md for profile directory
- Commit ready with proper documentation
- Handoff notes for Feature 2.4

---

## KEY PROFILING AREAS

### 1. Batch Size Analysis
**What to Measure**:
- Throughput (texts/second) for each batch size
- Latency per batch (ms)
- Memory per batch (MB)
- CPU utilization %
- GPU utilization % (if available)

**Test Batch Sizes**: 8, 16, 32, 64, 128, 256

**Expected Findings**:
- Larger batches typically faster (amortized overhead)
- Memory grows linearly with batch size
- There's a sweet spot (likely 64-128)
- GPU may have different optimal size than CPU

### 2. CPU Bottleneck Identification
**What to Profile**:
- Model initialization time
- Tokenization time
- Model forward pass time
- Post-processing time
- Memory overhead

**cProfile Output Analysis**:
- Function call count and time
- Time per function (cumulative vs local)
- Call graph visualization
- Identify hot spots

**Expected Findings**:
- Model forward pass likely dominant (45-60%)
- Tokenization overhead (10-20%)
- Memory allocation not typically bottleneck

### 3. Memory Usage Analysis
**What to Measure**:
- Initial model loading memory
- Memory per batch size
- Peak memory vs steady state
- Memory growth with text length
- Garbage collection impact

**Tools**:
- `memory_profiler` for line-by-line memory
- `psutil` for process-level memory
- `torch.cuda.memory_allocated()` for GPU memory

**Expected Findings**:
- Model weights: ~50 MB
- Per-text overhead: ~1-5 KB
- Batch size impact: Linear growth
- Long texts increase memory proportionally

### 4. Text Length Impact
**What to Test**:
- Short text (10 chars): "Hello"
- Medium text (50 chars): Normal sentences
- Standard text (256 chars): Typical evidence
- Long text (512 chars): Extended passages
- Very long text (1024 chars): Document excerpts

**Measurements**:
- Throughput vs length
- Latency vs length
- Memory vs length
- Tokenization overhead % by length

**Expected Findings**:
- Short text: Fast, low memory
- Sweet spot: 128-512 chars
- 1024+ chars: Diminishing returns
- Truncation could improve throughput 2-3x

---

## SUCCESS CRITERIA (DETAILED)

### Criterion 1: Profiling Infrastructure In Place ✓
- [ ] `profile_embeddings.py` created and functional
- [ ] `memory_analyzer.py` created and functional
- [ ] `profile_text_length_impact.py` created and functional
- [ ] All scripts have proper error handling
- [ ] All scripts have CLI arguments for customization
- [ ] Scripts runnable in 2-5 minutes for quick tests

### Criterion 2: Bottlenecks Identified & Documented ✓
- [ ] CPU bottleneck analysis complete
- [ ] Memory bottleneck analysis complete
- [ ] Text length impact quantified
- [ ] Profiling results in JSON format
- [ ] HTML call graph generated
- [ ] All findings documented in PROFILING_REPORT.md

### Criterion 3: Performance Metrics Captured ✓
- [ ] Throughput measured for 6 batch sizes
- [ ] Memory usage documented per batch
- [ ] Latency metrics (P50, P95, P99) captured
- [ ] Text length impact measured
- [ ] Comparison with Feature 1.7 baseline complete
- [ ] No regression detected

### Criterion 4: Optimization Recommendations Provided ✓
- [ ] Batch size recommendations documented
- [ ] Memory optimization strategies identified
- [ ] Text truncation strategy documented
- [ ] Quick wins identified with effort/impact
- [ ] Actionable recommendations for Feature 2.4
- [ ] Implementation roadmap provided

### Criterion 5: Code Quality Standards ✓
- [ ] 100% type hints on all functions
- [ ] Comprehensive docstrings
- [ ] Error handling for all I/O operations
- [ ] Logging statements for debugging
- [ ] No hardcoded values (use config)
- [ ] Follows project style guide

### Criterion 6: Testing & Validation ✓
- [ ] Baseline comparison shows no regression
- [ ] Results reproducible (run multiple times)
- [ ] Edge cases handled (very short/long text)
- [ ] CPU and memory limits not exceeded
- [ ] All test cases pass
- [ ] Documentation examples work

---

## RISKS & MITIGATION

### Risk 1: Profiling Overhead Affects Results
**Impact**: Medium | **Likelihood**: Medium
**Mitigation**:
- Use sampling-based profiling (not call tracing)
- Run profiling in separate process
- Compare with baseline methodology
- Document profiling overhead

### Risk 2: Results Vary Between Runs
**Impact**: Low | **Likelihood**: Medium
**Mitigation**:
- Fix random seeds where applicable
- Run multiple iterations
- Report P50, P95, P99 statistics
- Note system load during testing

### Risk 3: Optimization Discoveries Block Feature 2.4
**Impact**: High | **Likelihood**: Low
**Mitigation**:
- Document findings, don't implement
- Provide clear recommendations only
- Feature 2.4 will decide what to implement
- Keep implementation separate

### Risk 4: Memory Profiling Adds Overhead
**Impact**: Low | **Likelihood**: Medium
**Mitigation**:
- Use lightweight memory tracking
- Optional detailed profiling mode
- Compare with/without profiling
- Document overhead

### Risk 5: Platform-Specific Results (GPU vs CPU)
**Impact**: Medium | **Likelihood**: High
**Mitigation**:
- Profile on standard test CPU environment
- Note device used in results
- Provide GPU-specific guidance if available
- Document assumptions

**Mitigation Strategy**:
- Regular baseline checks (hourly during development)
- Automated regression detection
- Escalate if deviation > 5%

---

## FILES TO CREATE

### Profiling Scripts

1. **`c:\repos\truthgraph\scripts\profile\profile_embeddings.py`**
   - Purpose: Main embedding profiling with cProfile
   - Size: 200-250 lines
   - Dependencies: cProfile, torch, sentence-transformers
   - Runtime: 5-10 minutes for full profile

2. **`c:\repos\truthgraph\scripts\profile\memory_analyzer.py`**
   - Purpose: Detailed memory analysis and leak detection
   - Size: 150-200 lines
   - Dependencies: psutil, gc, torch
   - Runtime: 3-5 minutes

3. **`c:\repos\truthgraph\scripts\profile\profile_text_length_impact.py`**
   - Purpose: Text length impact on performance
   - Size: 100-150 lines
   - Dependencies: torch, sentence-transformers
   - Runtime: 2-3 minutes

### Documentation

1. **`c:\repos\truthgraph\scripts\profile\PROFILING_REPORT.md`**
   - Purpose: Comprehensive profiling analysis
   - Size: 400-500 lines
   - Includes: Results, bottlenecks, recommendations

2. **`c:\repos\truthgraph\scripts\profile\OPTIMIZATION_LOG.md`**
   - Purpose: Actionable optimization log
   - Size: 200-300 lines
   - Includes: Date, methodology, recommendations

3. **`c:\repos\truthgraph\scripts\profile\README.md`**
   - Purpose: Usage guide for profiling tools
   - Size: 150-200 lines
   - Includes: Quick start, example commands

### Results

1. **`c:\repos\truthgraph\scripts\profile\results\embedding_profile.json`**
   - Purpose: Machine-readable profiling results
   - Contains: Batch analysis, bottlenecks, metrics

2. **`c:\repos\truthgraph\scripts\profile\results\memory_profile.json`**
   - Purpose: Memory usage data
   - Contains: Per-batch memory, peak memory

3. **`c:\repos\truthgraph\scripts\profile\results\profiling_<timestamp>.html`**
   - Purpose: Visual cProfile output
   - Generated by: pstats visualization

---

## TECHNICAL APPROACH

### Profiling Methodology

**Step 1: Warm-up Run**
```python
# Pre-load model and JIT compile
for _ in range(10):
    service.embed_text("Warm up text")
```

**Step 2: Batch Size Testing**
```python
for batch_size in [8, 16, 32, 64, 128, 256]:
    texts = load_test_texts(1000)  # Fixed size
    start = time.perf_counter()
    service.embed_batch(texts, batch_size=batch_size)
    latency = time.perf_counter() - start
    throughput = len(texts) / latency
```

**Step 3: Memory Tracking**
```python
gc.collect()
torch.cuda.empty_cache()  # if available
baseline_memory = get_memory()

# Run embedding
result_memory = get_memory()
peak_memory = track_peak_during_execution()
```

**Step 4: cProfile Integration**
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()

# Run embeddings
service.embed_batch(texts)

profiler.disable()
profiler.dump_stats("embedding_profile.prof")
```

**Step 5: Results Analysis**
```python
import pstats
stats = pstats.Stats("embedding_profile.prof")
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Output Format

**JSON Structure**:
```json
{
  "metadata": {
    "timestamp": "ISO 8601",
    "device": "cpu|cuda|mps",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "test_size": 1000,
    "system_info": {...}
  },
  "batch_size_analysis": {
    "8": {
      "throughput_texts_per_sec": 850,
      "latency_ms_per_batch": 9.4,
      "memory_mb": 256,
      "iterations": 50
    },
    ...
  },
  "bottlenecks": [
    {
      "function": "model.forward()",
      "time_ms": 5.2,
      "percent_of_total": 45.3,
      "calls": 1000
    },
    ...
  ],
  "recommendations": [
    {
      "optimization": "Set batch_size=64 as default",
      "estimated_improvement_percent": 5,
      "effort": "low",
      "priority": "high"
    },
    ...
  ]
}
```

---

## INTEGRATION WITH PHASE 2

### How Feature 2.1 Enables Feature 2.4
Feature 2.1 profiling results will guide Feature 2.4 (Pipeline E2E Optimization):
- Batch size findings → Apply to pipeline embedding stage
- Memory bottleneck identification → Optimization targets
- Text length impact → Input preprocessing strategy
- CPU profiling → Parallelization opportunities

### Baseline Comparison Workflow
1. Load Feature 1.7 baseline: 1,185 texts/sec
2. Run profiling with same test data
3. Compare batch size 64 throughput (Feature 1.7's optimal)
4. Document any variance (should be <1%)
5. Validate profiling methodology consistency

### Handoff to Feature 2.4
Deliverables for next feature:
- Complete profiling results
- Bottleneck analysis with actionable insights
- Batch size and memory recommendations
- Implementation roadmap
- Performance improvement opportunities prioritized

---

## TESTING & VALIDATION

### Unit Tests to Create

**Test File**: `tests/profiling/test_profile_embeddings.py`

```python
def test_profile_embeddings_script_exists():
    """Verify profiling script can be imported."""
    assert Path("scripts/profile/profile_embeddings.py").exists()

def test_memory_analyzer_functions():
    """Test memory analyzer core functions."""
    analyzer = MemoryAnalyzer()
    assert analyzer.get_memory_usage() > 0

def test_baseline_comparison():
    """Verify profiling doesn't regress from baseline."""
    baseline = load_baseline()
    current = measure_embedding_throughput()

    # Allow 1% variance
    assert current['throughput_per_sec'] > baseline['throughput_per_sec'] * 0.99

def test_batch_size_range():
    """Test all batch sizes return results."""
    for batch_size in [8, 16, 32, 64, 128, 256]:
        result = profile_batch_size(batch_size)
        assert result['throughput'] > 0
        assert result['memory_mb'] > 0
```

### Integration Tests

**Verify**:
1. Scripts run without errors
2. JSON output valid format
3. Results reproducible (±2% variance)
4. No memory leaks detected
5. Performance within expected range

### Manual Validation

**Checklist**:
- [ ] Run profile_embeddings.py standalone
- [ ] Verify HTML output generated
- [ ] Verify JSON results readable
- [ ] Compare batch size results are reasonable
- [ ] Memory results match psutil measurements
- [ ] Text length impact shows expected trend
- [ ] Documentation examples work
- [ ] Scripts handle edge cases (empty text, very long text)

---

## DELIVERABLES CHECKLIST

### Scripts (3)
- [ ] `profile_embeddings.py` - Batch size and CPU profiling
- [ ] `memory_analyzer.py` - Memory usage analysis
- [ ] `profile_text_length_impact.py` - Text length impact study

### Documentation (3)
- [ ] `PROFILING_REPORT.md` - Comprehensive analysis
- [ ] `OPTIMIZATION_LOG.md` - Actionable recommendations
- [ ] `README.md` - Usage guide for profiling tools

### Results (3)
- [ ] `embedding_profile.json` - Machine-readable results
- [ ] `memory_profile.json` - Memory analysis results
- [ ] `profiling_<timestamp>.html` - cProfile visualization

### Tests (1)
- [ ] `tests/profiling/test_profile_embeddings.py` - Validation tests

### Integration (1)
- [ ] Git commit with all changes
- [ ] All tests passing
- [ ] Documentation complete

**Total**: 11 deliverables

---

## SUCCESS METRICS

### Code Metrics
- **Type Hint Coverage**: 100% of functions
- **Docstring Coverage**: 100% of public APIs
- **Test Coverage**: 80%+ of new code
- **Cyclomatic Complexity**: <10 per function
- **Lint Score**: 10/10 (no warnings)

### Performance Metrics
- **Throughput Match to Baseline**: ±1%
- **Memory Usage**: <1 GB peak
- **Profiling Overhead**: <5% of measured time
- **Results Reproducibility**: ±2% between runs

### Quality Metrics
- **Documentation Completeness**: 100% of code documented
- **Example Coverage**: 3+ usage examples
- **Error Handling**: All edge cases covered
- **User Experience**: Scripts < 2 minutes to run

---

## NEXT STEPS

### Immediate (Day of Kickoff)
1. Create scripts/profile/ directory structure
2. Review Feature 1.7 baseline in detail
3. Review EmbeddingService implementation
4. Set up profiling environment
5. Create initial script skeletons

### During Implementation
1. Develop scripts iteratively
2. Test each script individually
3. Compare results with baseline continuously
4. Document findings as you go
5. Iterate on recommendations

### Before Handoff to Feature 2.4
1. Complete all profiling runs
2. Validate results consistency
3. Write comprehensive documentation
4. Create optimization recommendations
5. Prepare handoff summary for Feature 2.4

### Coordination Touchpoints
1. Daily check-in with context-manager
2. Report any blocking issues immediately
3. Share preliminary findings by hour 4
4. Final results review before handoff
5. Coordinate transition to Feature 2.4

---

## RESOURCES & REFERENCES

### Existing Code to Reference
- `truthgraph/services/ml/embedding_service.py` - Core service
- `truthgraph/services/ml/model_cache.py` - Model caching
- `scripts/benchmarks/benchmark_embeddings.py` - Baseline benchmark
- `scripts/profile_ml_services.py` - Example profiling approach

### Documentation to Review
- `scripts/benchmarks/README.md` - Benchmark methodology
- `FEATURE_1_7_FINAL_REPORT.md` - Feature 1.7 results
- `planning/phases/phase_2/2_performance_optimization_handoff.md` - Feature details

### Test Data
- `tests/fixtures/test_claims.json` - 25 test claims
- `data/samples/evidence_corpus.json` - 250 evidence documents
- Load via existing fixture patterns in tests/

### Tools & Libraries
- **Profiling**: cProfile, memory_profiler, psutil
- **Visualization**: pstats, snakeviz (optional)
- **Data**: json, csv
- **Analysis**: statistics, numpy (if available)

---

## QUESTIONS FOR CLARIFICATION

Before starting, confirm:

1. **Device to Profile On**: CPU only? Or GPU if available?
   - **Answer**: Profile on CPU (primary platform), note GPU if available

2. **Test Data Size**: 1,000 texts ok? Or larger?
   - **Answer**: 1,000 texts good for profiling (quick runtime)

3. **Batch Size Range**: 8-256 covers testing needs?
   - **Answer**: Yes, covers practical range from small to large

4. **Documentation Level**: How detailed should recommendations be?
   - **Answer**: Actionable with implementation effort and expected impact

5. **Integration with Existing Benchmarks**: Reuse existing scripts or create new?
   - **Answer**: Create new in scripts/profile/, can reference benchmark scripts

---

## SUMMARY

Feature 2.1 is **ready to start immediately** with no blockers. The codebase already has:
- ✓ Working embedding service with batch processing
- ✓ Feature 1.7 baseline data for comparison
- ✓ Benchmark infrastructure in place
- ✓ Test data and fixtures ready

The 8-hour implementation will deliver:
- ✓ Production-ready profiling scripts
- ✓ Comprehensive bottleneck analysis
- ✓ Actionable optimization recommendations
- ✓ Clear handoff to Feature 2.4

**Agent python-pro**: You have everything you need to succeed. Start with Hour 1-1.5 setup phase and proceed through the implementation plan. The context-manager will be available for any clarifications.

**Coordinator Role**: I will track progress, manage dependencies with other features, and ensure smooth handoff to Feature 2.4.

---

**Status**: READY FOR IMPLEMENTATION ✓
**Blocker Check**: NONE - ALL DEPENDENCIES MET ✓
**Recommended Start**: IMMEDIATELY
**Estimated Completion**: 8 hours from kickoff
**Next Feature**: 2.4 (Pipeline E2E Optimization) - unblocked on completion

---

## Document Control

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | Oct 31, 2025 | Context Manager | DRAFT |
| 1.1 | Oct 31, 2025 | Context Manager | READY FOR REVIEW |

---

**Prepared by**: Context Manager (Anthropic Claude)
**For Agent**: python-pro
**Phase**: 2 (ML Core Implementation)
**Priority**: CRITICAL PATH
**Timeline**: 8 hours, immediate start
