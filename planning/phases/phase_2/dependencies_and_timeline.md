# Dependencies & Timeline

**For**: Coordinators, all agents
**Purpose**: Critical path analysis, dependency matrix, timeline planning
**Read Time**: 15 minutes

---

## Critical Path Analysis

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2A: DATASET INFRASTRUCTURE (Complete)                 │
│ Features 1.1-1.6 already done                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2B: BASELINE ESTABLISHMENT (1 feature, 6h)            │
│ Feature 1.7: Benchmark Baseline (CRITICAL PATH)            │
│ No blockers - START IMMEDIATELY                             │
│ Blocks: All Features 2.1-2.6, Features 3.1-3.5             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2C: PARALLEL OPTIMIZATION (Days 1-2)                 │
│ Features 2.1-2.3, 2.5 (parallel)                           │
│ Blocks: Feature 2.4                                         │
│ Blocks: Feature 3.1 (validation)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2D: PIPELINE & VALIDATION (Days 3-4)                │
│ Features 2.4, 2.6, 3.1-3.5 (parallel)                      │
│ 2.4 depends on 2.1-2.3                                      │
│ 3.1-3.5 depend on test data (1.1-1.4) and optimizations    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2E: API & DOCUMENTATION (Days 5-6)                   │
│ Features 4.1-4.5, 5.1-5.4 (parallel)                       │
│ No blockers - can start anytime                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependency Matrix

### Complete Feature Dependency Map

| Feature | Depends On | Blocks | Critical? | Notes |
|---------|-----------|--------|-----------|-------|
| 1.1 | None | 1.2, 1.3, 1.4, 1.7 | Yes | Test data foundation |
| 1.2 | 1.1 | 3.1, 3.2 | Yes | FEVER dataset |
| 1.3 | 1.1 | 3.1, 3.2, 3.4 | Yes | Real-world validation |
| 1.4 | None | 3.3 | No | Edge case data |
| 1.5 | ML services | - | Yes | Corpus loader |
| 1.6 | None | 1.5 | No | Sample corpus |
| **1.7** | **All services** | **2.1-2.6, 3.1-3.5** | **Yes** | **CRITICAL BLOCKER** |
| 2.1 | 1.7 | - | No | Embedding profiling |
| 2.2 | 1.7 | - | No | NLI optimization |
| 2.3 | 1.7 | - | No | Vector search optimization |
| 2.4 | 2.1-2.3 | - | Yes | E2E optimization |
| 2.5 | 1.7 | - | No | Memory optimization |
| 2.6 | Services | - | No | Database optimization |
| 3.1 | 1.1, 1.3, 1.7 | 3.2-3.5 | Yes | Accuracy framework |
| 3.2 | 3.1 | - | Yes | Category evaluation |
| 3.3 | 1.4, 3.1 | - | No | Edge case validation |
| 3.4 | 3.1 | - | No | Robustness testing |
| 3.5 | 1.7, 3.1 | - | Yes | Regression tests |
| 4.1 | Pipeline | - | Yes | Endpoints |
| 4.2 | None | 4.1 | Yes | Models |
| 4.3 | 4.1 | - | Yes | Async processing |
| 4.4 | 4.1 | - | No | API documentation |
| 4.5 | 4.1 | - | Yes | Rate limiting |
| 5.1 | All code | - | No | Code docstrings |
| 5.2 | Testing | - | No | Troubleshooting |
| 5.3 | All code | - | No | Usage examples |
| 5.4 | 1.7, 2.x | - | No | Performance guide |

---

## Critical Path Items

### Must Complete First (Highest Priority)

1. **Feature 1.7: Benchmark Baseline** (6h)
   - No blockers, start immediately
   - Blocks 12 other features (2.1-2.6, 3.1-3.5)
   - Must complete before any optimization work

2. **Feature 3.1: Accuracy Framework** (8h)
   - Depends on 1.7 and test data (1.1-1.4, already done)
   - Blocks 4 other features (3.2-3.5)
   - Must complete before validation work

3. **Features 2.1-2.3: Performance Profiling** (24h parallel)
   - Depend on 1.7
   - Block 2.4 (end-to-end optimization)
   - Must complete before pipeline optimization

### Critical Sequence

```
Day 1: Feature 1.7 (6h) ──┐
                          ├─→ Day 2: Features 2.1-2.3 (24h parallel) ──┐
Day 1: Feature 3.1 (8h) ──┐                                            ├─→ Days 3-4: E2E + Validation
                                                                        ├─→ Feature 2.4 (10h)
Days 2-3: Features 4.1-4.5 (44h parallel, no dependencies) ────────────┘
Days 2-3: Features 5.1-5.3 (28h parallel, mostly independent) ─────────→ Day 5
```

### Sequential Dependencies (Must Wait For)

```
1.7 → 2.1, 2.2, 2.3, 2.5
1.7 → 3.1
2.1-2.3 → 2.4
3.1 → 3.2, 3.3, 3.4, 3.5
4.2 → 4.1
4.1 → 4.3
2.x → 5.4
```

---

## Timeline Estimate

### Week 1: Foundation & Optimization

**Day 1 (Monday)**
- Start Feature 1.7 (6h) - Benchmark baseline
- Start Feature 3.1 (8h) - Accuracy framework
- Start Features 4.2 (6h) - API models
- Start Features 5.1 (10h) - Code docstrings

**Days 2-3 (Tuesday-Wednesday)**
- Features 2.1-2.3 (24h parallel) - Performance profiling
- Features 4.1, 4.5 (18h parallel) - API endpoints
- Feature 5.2 (8h) - Troubleshooting
- Feature 5.3 (10h) - Usage examples

**Days 4-5 (Thursday-Friday)**
- Feature 2.4 (10h) - E2E optimization
- Feature 2.6 (8h) - Database optimization
- Features 3.2-3.5 (34h parallel) - Validation
- Features 4.3, 4.4 (20h parallel) - Async & docs

**Week 1 Totals**:
- 242 hours of work
- ~40 hours per agent per week (6 agents)
- All core work complete by Friday EOD

### Week 2: Buffer & Hardening

**Days 6-7 (Monday-Tuesday)**
- Feature 5.4 (6h) - Performance guide
- Integration testing
- Cross-feature validation
- Bug fixes and refinements

**Days 8-10 (Wednesday-Friday)**
- Final testing
- Performance validation against targets
- Documentation final review
- Deployment preparation

**Week 2 Totals**:
- ~40 hours of buffer and validation
- Final hardening and quality assurance

### Wall-Clock Timeline

- **Total Hours**: 242h of work + 40h buffer = 282h
- **Team Capacity**: 6 agents × 40h/week = 240h/week
- **Duration**: ~1.2 weeks optimal, 2 weeks comfortable
- **Recommended**: Use 2-week timeline with 1 week buffer for unknowns

---

## Parallelization Opportunities

### Phase 2B: Baseline (Day 1)

**No parallelization needed** - single feature (1.7)

```
python-pro: Feature 1.7 (6h)
```

### Phase 2C: Optimization (Days 2-3)

**Can run in parallel** - Features 2.1-2.3, 2.5 independent

```
python-pro: 2.1 (8h) ┐
python-pro: 2.2 (8h) ├─ Parallel (Days 2-3)
python-pro: 2.3 (10h)┤
python-pro: 2.5 (6h) ┘
```

### Phase 2D: E2E & Validation (Days 3-4)

**Can run in parallel** - different agents

```
python-pro: 2.4 (10h), 2.6 (8h)
test-automator: 3.1 (8h), 3.2 (10h), 3.3 (8h), 3.4 (10h), 3.5 (6h)
```

### Phase 2E: API & Docs (Days 3-6)

**Can run in parallel** - different agents, no blockers

```
fastapi-pro: 4.1 (10h), 4.2 (6h), 4.3 (12h), 4.4 (8h), 4.5 (8h)
dx-optimizer: 5.1 (10h), 5.2 (8h), 5.3 (10h)
```

---

## Resource Allocation

### Recommended Team Structure

| Agent | Hours/Week | Features | Priority |
|-------|-----------|----------|----------|
| python-pro | 40h | 1.5-1.7, 2.1-2.6 | **Critical** |
| test-automator | 40h | 1.1-1.4 (done), 3.1-3.5 | **Critical** |
| fastapi-pro | 40h | 4.1-4.5 | **High** |
| dx-optimizer | 40h | 5.1-5.4 | **Medium** |

### Utilization Rates (Ideal)

```
Week 1:
- python-pro: 56h (6h baseline + 24h profiling + 10h E2E + 8h DB) = Over capacity, needs split
- test-automator: 52h (8h framework + 34h validation) = Over capacity, needs split

Adjusted (2 agents per role):
- 2x python-pro: 28h each
- 2x test-automator: 26h each
- 1x fastapi-pro: 44h
- 1x dx-optimizer: 28h (spread over 2 weeks)
```

---

## Blocking Dependencies Timeline

### Critical Blockers

```
Feature 1.7 (6h, Day 1)
    ├─ Blocks 2.1 (8h, Day 2)
    ├─ Blocks 2.2 (8h, Day 2)
    ├─ Blocks 2.3 (10h, Day 2)
    ├─ Blocks 2.5 (6h, Day 2)
    ├─ Blocks 3.1 (8h, Day 1 in parallel)
    └─ Blocks 3.5 (6h, Day 3)

Features 2.1-2.3 (24h, Days 2-3)
    └─ Block 2.4 (10h, Day 3)

Feature 3.1 (8h, Day 1)
    ├─ Blocks 3.2 (10h, Day 3)
    ├─ Blocks 3.3 (8h, Day 3)
    └─ Blocks 3.4 (10h, Day 3)
```

### Non-Critical Dependencies

- Features 4.1-4.5: No blockers, can start anytime
- Features 5.1-5.3: No blockers, can start anytime
- Feature 5.4: Depends on 2.x (performance data), not blocking

---

## Risk Mitigation

### Feature 1.7 Delay Mitigation

If Feature 1.7 takes >6h (worst case 10h):
- Delay: All downstream features delayed by 4h
- Impact: E2E completion delayed by ~1 day
- Mitigation: Have 2 agents dedicated to 1.7, track daily

### Feature 3.1 Delay Mitigation

If Feature 3.1 takes >8h (worst case 12h):
- Delay: Validation features (3.2-3.5) delayed by 4h
- Impact: Validation incomplete by target date
- Mitigation: Have test-automator assign extra resources

### Feature 2.4 Delay Mitigation

If Feature 2.4 takes >10h (worst case 15h):
- Delay: E2E optimization incomplete
- Impact: May not hit <60 sec target
- Mitigation: Parallelize with other work, have contingency models

---

## Execution Checklist

### Pre-Kickoff (Today)

- [ ] All agents read this document
- [ ] Confirm resource availability
- [ ] Set up monitoring dashboard
- [ ] Brief all agents on critical path
- [ ] Confirm Feature 1.7 can start immediately

### Daily Standup Items

- Feature 1.7 progress (blocker for everything)
- Feature 3.1 progress (blocker for validation)
- Any unplanned blockers
- Resource adjustments needed
- Performance tracking

### Weekly Review (Friday EOD)

- Compare actual vs planned progress
- Adjust timeline if needed
- Identify any emerging risks
- Plan for next week
- Update stakeholders

---

## Related Files

**Master Index**: [v0_phase2_completion_handoff_MASTER.md](./v0_phase2_completion_handoff_MASTER.md)
**Quick Start**: [v0_phase2_quick_start.md](./v0_phase2_quick_start.md)
**All Assignments**: [agent_assignments.md](./agent_assignments.md)
**Success Criteria**: [success_criteria_and_risks.md](./success_criteria_and_risks.md)

---

**Navigation**: [Master Index](./v0_phase2_completion_handoff_MASTER.md) | [Quick Start](./v0_phase2_quick_start.md) | [Agent Assignments](./agent_assignments.md) | [Success & Risks](./success_criteria_and_risks.md)
