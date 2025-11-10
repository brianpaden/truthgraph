# Feature 2.1: Embedding Service Profiling
## Quick Start for python-pro Agent

**Status**: READY TO START - NO BLOCKERS ✓
**Duration**: 8 hours
**Date**: October 31, 2025
**Coordinator**: Context Manager (Anthropic Claude)

---

## WHAT YOU'RE DOING

Profile the embedding service to identify optimization opportunities. Feature 1.7 (baseline) is complete at 1,185 texts/sec.

---

## QUICK FACTS

| Item | Value |
|------|-------|
| **Feature ID** | 2.1 |
| **Team** | You (python-pro) |
| **Duration** | 8 hours |
| **Complexity** | Medium |
| **Blockers** | NONE - Ready now |
| **Baseline** | 1,185 texts/sec (Feature 1.7) |
| **Dependencies** | Feature 1.7 (COMPLETE ✓) |
| **Blocks** | Feature 2.4 (needs profiling data) |

---

## YOUR MISSION (3 SENTENCES)

1. Create profiling scripts to analyze embedding service performance
2. Test batch sizes (8, 16, 32, 64, 128, 256) and measure throughput, latency, memory
3. Document findings and provide optimization recommendations for Feature 2.4

---

## WHAT EXISTS (DON'T REBUILD)

✓ EmbeddingService - `truthgraph/services/ml/embedding_service.py`
✓ Feature 1.7 baseline - `scripts/benchmarks/results/baseline_embeddings_2025-10-27.json`
✓ Benchmark framework - `scripts/benchmarks/benchmark_embeddings.py`
✓ Test data - `tests/fixtures/test_claims.json`, `data/samples/evidence_corpus.json`

---

## WHAT TO CREATE (8 HOURS)

### Profiling Scripts (3 files, ~550 lines total)
1. **`scripts/profile/profile_embeddings.py`** (250 lines)
   - Test batch sizes: 8, 16, 32, 64, 128, 256
   - Measure throughput, latency, memory per batch
   - Generate cProfile output

2. **`scripts/profile/memory_analyzer.py`** (150 lines)
   - Track peak memory usage
   - Detect memory leaks
   - Analyze memory per batch

3. **`scripts/profile/profile_text_length_impact.py`** (150 lines)
   - Test text lengths: 10, 50, 256, 512, 1024 chars
   - Measure throughput impact
   - Identify optimal text length

### Documentation (3 files, ~1000 lines total)
1. **`scripts/profile/PROFILING_REPORT.md`** (400 lines)
   - Executive summary
   - Detailed findings
   - Bottleneck analysis
   - Optimization recommendations

2. **`scripts/profile/OPTIMIZATION_LOG.md`** (300 lines)
   - Date and methodology
   - Results tables
   - Recommendations with effort/impact

3. **`scripts/profile/README.md`** (200 lines)
   - Usage guide
   - Example commands
   - Troubleshooting

### Results Files (JSON)
1. **`scripts/profile/results/embedding_profile.json`**
   - Batch size analysis
   - Identified bottlenecks
   - Recommendations

2. **`scripts/profile/results/memory_profile.json`**
   - Memory per batch size
   - Peak memory measurements

---

## 8-HOUR IMPLEMENTATION TIMELINE

| Hour | Task | Deliverable |
|------|------|-------------|
| 1-1.5 | Setup & baseline review | Profile dir, baselines loaded |
| 1.5-3 | Batch size profiling | profile_embeddings.py complete |
| 3-4.5 | Memory & text length | memory_analyzer.py, text_length script |
| 4.5-7 | Analysis & documentation | PROFILING_REPORT.md, findings |
| 7-8 | Integration & validation | Scripts production-ready, commit |

---

## SUCCESS CRITERIA (6 THINGS TO VERIFY)

- [ ] Profiling infrastructure working (scripts execute without errors)
- [ ] Bottlenecks identified and documented (specify CPU vs memory)
- [ ] Performance metrics captured (all 6 batch sizes tested)
- [ ] Batch size recommendations provided (with expected impact)
- [ ] Baseline comparison valid (no regression vs Feature 1.7)
- [ ] Code quality met (100% type hints, comprehensive docstrings)

---

## KEY RESOURCES

**Code to Review**:
- `truthgraph/services/ml/embedding_service.py` - The service you're profiling
- `scripts/benchmarks/benchmark_embeddings.py` - Reference benchmark

**Data to Use**:
- Feature 1.7 baseline: `scripts/benchmarks/results/baseline_embeddings_2025-10-27.json`
- Test texts: Load from `tests/fixtures/test_claims.json` or `data/samples/evidence_corpus.json`

**Tools Available**:
- cProfile (stdlib)
- psutil (already installed)
- torch.cuda.memory_allocated() (if GPU available)
- memory_profiler (pip install if needed)

---

## TESTING APPROACH

**Before Running Tests**:
1. Review Feature 1.7 baseline methodology
2. Understand EmbeddingService batch processing
3. Prepare test data (1000 texts)

**During Profiling**:
1. Run warm-up iterations (10 texts)
2. Profile with increasing batch sizes
3. Measure latency, throughput, memory
4. Compare against Feature 1.7

**Validation**:
1. Results match baseline methodology
2. No regression in throughput (±1%)
3. Memory usage reasonable (<1GB)
4. Results reproducible (run 2-3 times)

---

## COMMON BOTTLENECKS (WHAT YOU'LL LIKELY FIND)

1. **Model Forward Pass** (40-50% of time)
   - Expected: Normal, hard to optimize
   - Recommendation: Accept as baseline

2. **Tokenization** (10-15% of time)
   - Expected: Text preprocessing overhead
   - Recommendation: Maybe batch tokenization

3. **Memory Growth** (Linear with batch size)
   - Expected: Scales proportionally
   - Recommendation: Find sweet spot (likely 64-128)

4. **Text Length Impact** (Major)
   - Expected: Longer text = slower
   - Recommendation: Consider truncation at 256 chars

---

## QUESTIONS? ASK CONTEXT-MANAGER

Key clarifications you might need:
- "Should I profile GPU if available, or CPU only?" → CPU primary, note GPU if useful
- "What if I find major optimization opportunity?" → Document, don't implement (that's Feature 2.4)
- "How detailed should recommendations be?" → Include effort level and estimated impact %
- "Can I reuse existing benchmark code?" → Yes, reference it. Create new in scripts/profile/

---

## WHAT HAPPENS AFTER

Feature 2.4 (Pipeline E2E Optimization) will use your:
- Batch size recommendations
- Bottleneck analysis
- Memory findings
- Quick wins list

Your profiling results become the foundation for all optimization work.

---

## SUCCESS LOOKS LIKE

**By end of 8 hours, you will have**:

✓ 3 working profiling scripts
✓ Comprehensive profiling results (JSON)
✓ Detailed analysis document (400+ lines)
✓ Optimization recommendations with priorities
✓ No regression vs Feature 1.7 baseline
✓ All code production-ready with tests

✓ **Handoff to Feature 2.4 with complete intelligence**

---

## NEXT STEPS

1. **Right now** (5 min):
   - Read this document
   - Read full coordination plan: `FEATURE_2_1_COORDINATION_PLAN.md`

2. **Next 15 min**:
   - Review Feature 1.7 baseline
   - Review EmbeddingService code
   - Check existing benchmark script

3. **Hour 1** (Setup):
   - Create scripts/profile/ directory
   - Create scripts/profile/results/ subdirectory
   - Load baseline data
   - Prepare test data

4. **Hours 2-7** (Implementation):
   - Follow the 8-hour timeline
   - Build and test each script
   - Document as you go

5. **Hour 8** (Finalization):
   - Validate all results
   - Complete documentation
   - Prepare for git commit

**Start now. You have everything you need.**

---

## CONTEXT MANAGER SUPPORT

I'm here to:
- Answer questions about requirements
- Help resolve blockers
- Validate approach decisions
- Coordinate with other agents
- Track progress to schedule

Report blockers immediately. Everything else can be discussed during daily standups.

---

**Ready?** → Open `FEATURE_2_1_COORDINATION_PLAN.md` for full details
**In a hurry?** → Jump to "8-HOUR IMPLEMENTATION TIMELINE" section above
**Need details?** → See full coordination plan for technical approach

---

**Status**: READY TO IMPLEMENT
**Coordinator**: Context Manager (Anthropic Claude)
**Date**: October 31, 2025
