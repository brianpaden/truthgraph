# Documentation Structure: Visual Reference

**Quick visual guide to the new documentation structure**

---

## Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         REPOSITORY ROOT                          │
│                                                                   │
│  README.md  CONTRIBUTING.md  CHANGELOG.md                       │
│  (Only these 3 markdown files should remain at root)             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
        ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
        │    docs/      │   │  planning/   │   │   archive/   │
        │  PERMANENT    │   │    ACTIVE    │   │  HISTORICAL  │
        └──────────────┘   └──────────────┘   └──────────────┘
```

---

## Tier 1: docs/ (Permanent Documentation)

**Purpose**: Long-lived technical documentation that rarely changes

```
docs/
│
├── api/                     # API documentation
│   ├── endpoints/           # Endpoint details
│   ├── schemas/             # Data schemas
│   └── authentication.md    # Auth/authz
│
├── architecture/            # System architecture
│   ├── decisions/           # ADRs (001-xxx.md)
│   ├── system_design.md     # High-level design
│   └── tech_stack.md        # Technology choices
│
├── services/                # Service documentation
│   ├── hybrid_search.md
│   ├── verification_pipeline.md
│   └── verdict_aggregation.md
│
├── database/                # Database documentation
│   ├── schema.md
│   ├── migrations/
│   └── query_patterns.md
│
├── deployment/              # Deployment guides
│   ├── docker.md
│   ├── docker-ml.md
│   └── troubleshooting.md
│
├── development/             # Development guides
│   ├── setup.md
│   ├── testing.md
│   └── debugging.md
│
├── operations/              # Operations/runbooks
│   ├── monitoring.md
│   ├── performance-tuning.md
│   └── incident-response.md
│
├── guides/                  # User guides
│   ├── user-guide.md
│   ├── developer-guide.md
│   └── quickstart/
│
├── research/                # Research & experiments
│   ├── experiments/
│   └── concept/
│
└── integration/             # Integration guides
    └── external-services.md
```

**Update frequency**: Monthly or less
**Content**: API docs, architecture, services, deployment, operations
**Audience**: All developers, operators, users

---

## Tier 2: planning/ (Active Planning)

**Purpose**: Work in progress, current planning, frequently updated

```
planning/
│
├── roadmap/                 # Product roadmap
│   ├── v0/                  # Version roadmaps
│   ├── v1/
│   └── v2/
│
├── features/                # Feature lifecycle
│   ├── in_progress/         # 🚧 Currently implementing
│   │   ├── feature_12.md
│   │   └── feature_13.md
│   ├── planned/             # 📋 Next up
│   │   ├── feature_14.md
│   │   └── feature_15.md
│   └── backlog/             # 💡 Future ideas
│       └── feature_ideas.md
│
├── phases/                  # Phase-based planning
│   ├── phase_2/             # Current phase
│   │   ├── plan.md          # 📄 Original plan
│   │   ├── progress.md      # 🔄 LIVING DOC (daily updates)
│   │   ├── tasks.md         # ✅ Task breakdown
│   │   └── blockers.md      # 🚫 Current blockers
│   └── phase_3/             # Next phase
│       └── plan.md
│
├── technical_debt/          # Technical debt tracking
│   ├── README.md            # Debt index
│   ├── test-fixes-needed.md # 🐛 Test issues
│   ├── performance-debt.md  # ⚡ Performance issues
│   └── refactoring-candidates.md
│
└── tasks/                   # Task management
    └── taskfile-updates.md  # Taskfile change log
```

**Update frequency**: Daily/weekly
**Content**: Active features, phase progress, technical debt
**Audience**: Development team

---

## Tier 3: archive/ (Historical Archive)

**Purpose**: Completed work, lessons learned, read-only

```
archive/
│
├── completed_features/      # ✓ Completed features
│   ├── feature-5-verdict-aggregation.md
│   ├── feature-6-implementation.md
│   ├── feature-10-implementation.md
│   └── feature-11-docker-delivery.md
│
├── completed_phases/        # ✓ Completed phases
│   ├── phase-1-completion.md
│   └── phase-2-completion.md
│
├── implementation_summaries/# 📊 Implementation summaries
│   ├── api-integration-summary.md
│   ├── docker-implementation-summary.md
│   ├── embedding-service-summary.md
│   ├── hybrid-search-summary.md
│   └── nli-service-summary.md
│
└── deprecated/              # ⚠️ Deprecated docs
    └── old-api-design.md
```

**Update frequency**: Never (read-only)
**Content**: Completed features, phase reports, implementation summaries
**Audience**: Historical reference, onboarding, lessons learned

---

## Feature Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      FEATURE LIFECYCLE                           │
└─────────────────────────────────────────────────────────────────┘

1. PLANNING                  2. IN PROGRESS              3. COMPLETE
   ┌──────────────┐             ┌──────────────┐           ┌──────────────┐
   │ planning/    │    Start    │ planning/    │  Done     │  archive/    │
   │ features/    │ ────────>   │ features/    │ ───────>  │ completed_   │
   │ planned/     │             │ in_progress/ │           │ features/    │
   └──────────────┘             └──────────────┘           └──────────────┘

   Status: 📋 Planned         Status: 🚧 In Progress      Status: ✓ Completed
   Updates: Occasional        Updates: Frequent           Updates: Never (read-only)
```

---

## Documentation Discovery Map

**"Where do I find...?"**

```
┌─────────────────────────────────────────────────────────────────┐
│ Question                    │ Location                          │
├─────────────────────────────────────────────────────────────────┤
│ API endpoint details?       │ docs/api/endpoints/               │
│ How to authenticate?        │ docs/api/authentication.md        │
│ System architecture?        │ docs/architecture/system_design.md│
│ Why did we choose X?        │ docs/architecture/decisions/      │
│ How does service Y work?    │ docs/services/Y.md                │
│ Database schema?            │ docs/database/schema.md           │
│ How to deploy?              │ docs/deployment/docker.md         │
│ How to set up dev env?      │ docs/development/setup.md         │
│ How to run tests?           │ docs/development/testing.md       │
│ How to monitor?             │ docs/operations/monitoring.md     │
│ Quick start guide?          │ docs/guides/quickstart/           │
│ User guide?                 │ docs/guides/user-guide.md         │
│ Product roadmap?            │ planning/roadmap/                 │
│ What's being worked on?     │ planning/features/in_progress/    │
│ What's next?                │ planning/features/planned/        │
│ Current phase status?       │ planning/phases/phase_N/progress.md│
│ Known issues?               │ planning/technical_debt/          │
│ How was feature X built?    │ archive/completed_features/feature-X.md   │
│ Phase completion report?    │ archive/completed_phases/         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Color-Coded Status System

```
📄 Static        - Rarely changes (docs/)
🔄 Living        - Frequently updated (planning/phases/*/progress.md)
📋 Planned       - Not yet started (planning/features/planned/)
🚧 In Progress   - Currently working (planning/features/in_progress/)
✓  Completed     - Done and archived (archive/completed_features/)
🐛 Bug/Issue     - Known problems (planning/technical_debt/)
⚠️  Deprecated    - No longer valid (archive/deprecated/)
💡 Idea          - Future consideration (planning/features/backlog/)
```

---

## Documentation Type Matrix

```
┌──────────────────────────────────────────────────────────────────┐
│ Type              │ Location      │ Frequency │ Audience          │
├──────────────────────────────────────────────────────────────────┤
│ API docs          │ docs/api/     │ Rare      │ All devs          │
│ Architecture      │ docs/arch/    │ Rare      │ Architects, leads │
│ Service docs      │ docs/services/│ Rare      │ Service owners    │
│ Deployment        │ docs/deploy/  │ Rare      │ Ops, devs         │
│ User guides       │ docs/guides/  │ Rare      │ End users         │
│ Feature plans     │ planning/     │ Frequent  │ Dev team          │
│ Phase progress    │ planning/     │ Daily     │ Dev team          │
│ Technical debt    │ planning/debt/│ Weekly    │ Dev team, leads   │
│ Completed work    │ archive/      │ Never     │ Historical ref    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Migration Quick Reference

**Current Structure (33+ files at root) → New Structure (3 files at root)**

```
BEFORE                              AFTER
──────────────────────────────────────────────────────────────────

Root (33 .md files)                Root (3 .md files)
├── API_QUICK_REFERENCE.md         ├── README.md
├── DOCKER_README.md               ├── CONTRIBUTING.md
├── HYBRID_SEARCH_*.md             └── CHANGELOG.md
├── PHASE_2_*.md
├── FEATURE_*.md                   docs/ (permanent)
├── TEST_FIXES_*.md                ├── api/
├── ... (27 more)                  ├── architecture/
                                   ├── services/
docs/ (some structure)             ├── database/
├── DOCKER_ML_SETUP.md             ├── deployment/
├── DEVELOPER_GUIDE.md             ├── development/
├── concept/                       ├── operations/
├── roadmap/                       ├── guides/
└── experiments/                   ├── research/
                                   │   ├── concept/
                                   │   └── experiments/
                                   └── integration/

                                   planning/ (active)
                                   ├── roadmap/
                                   ├── features/
                                   │   ├── in_progress/
                                   │   ├── planned/
                                   │   └── backlog/
                                   ├── phases/
                                   ├── technical_debt/
                                   └── tasks/

                                   archive/ (historical)
                                   ├── completed_features/
                                   ├── completed_phases/
                                   ├── implementation_summaries/
                                   └── deprecated/
```

---

## Daily Workflow Visual

```
┌─────────────────────────────────────────────────────────────────┐
│                      DAILY WORKFLOW                              │
└─────────────────────────────────────────────────────────────────┘

Morning
────────
1. Check active features
   → ls planning/features/in_progress/

2. Review phase progress
   → cat planning/phases/phase_2/progress.md

3. Check blockers
   → cat planning/phases/phase_2/blockers.md


During Development
──────────────────
1. Update feature notes
   → vim planning/features/in_progress/feature_X.md

2. Reference service docs
   → cat docs/services/service_name.md

3. Check API contracts
   → cat docs/api/endpoints/resource.md


End of Day
──────────
1. Update phase progress
   → vim planning/phases/phase_2/progress.md

2. Log any new blockers
   → vim planning/phases/phase_2/blockers.md

3. Commit documentation changes
   → git add . && git commit -m "docs: update progress"


Weekly
──────
1. Move completed features to archive
   → mv planning/features/in_progress/X.md archive/completed_features/

2. Review technical debt
   → cat planning/technical_debt/README.md

3. Check for root clutter
   → ls -1 *.md
```

---

## Backend-Specific Highlights

```
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND-SPECIFIC DOCUMENTATION                      │
└─────────────────────────────────────────────────────────────────┘

API Documentation                Architecture Decisions
─────────────────                ──────────────────────
docs/api/                        docs/architecture/decisions/
├── endpoints/                   ├── 001-fastapi-framework.md
│   ├── claims.md                ├── 002-pgvector-choice.md
│   ├── evidence.md              ├── 003-ml-service-integration.md
│   └── verification.md          └── template.md
├── schemas/
├── authentication.md            System Design
├── error_codes.md               ─────────────
├── rate_limiting.md             docs/architecture/
└── versioning.md                ├── system_design.md
                                 ├── service_architecture.md
Service Documentation            ├── data_flow.md
─────────────────────            └── tech_stack.md
docs/services/
├── hybrid_search.md             Database Documentation
├── verification_pipeline.md     ──────────────────────
├── verdict_aggregation.md       docs/database/
├── embedding_service.md         ├── schema.md
├── nli_service.md               ├── migrations/
└── vector_search.md             ├── indexes.md
                                 └── query_patterns.md

Deployment & Operations          Integration Guides
───────────────────────          ──────────────────
docs/deployment/                 docs/integration/
├── docker.md                    ├── external-services.md
├── docker-ml.md                 └── webhooks.md
├── gpu-support.md
└── troubleshooting.md           Research & Experiments
                                 ───────────────────────
docs/operations/                 docs/research/
├── monitoring.md                ├── experiments/
├── performance-tuning.md        │   └── 00-bayesian.md
└── incident-response.md         └── concept/
                                     ├── compound-fact-reasoning.md
                                     └── temporal-fact-engine.md
```

---

## Key Principles (Visual)

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENTATION PRINCIPLES                     │
└─────────────────────────────────────────────────────────────────┘

1. SEPARATION OF CONCERNS
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ Permanent   │  │   Active    │  │ Historical  │
   │   docs/     │  │ planning/   │  │  archive/   │
   └─────────────┘  └─────────────┘  └─────────────┘

2. CLEAR LIFECYCLE
   Planned → In Progress → Completed → Archived

3. EASY DISCOVERY
   README indexes + Clear naming + Logical structure

4. SCALABLE STRUCTURE
   Grows without root-level clutter

5. DEVELOPER-FIRST
   Easy to find, easy to maintain, easy to contribute
```

---

## Navigation Shortcuts

```bash
# Quick navigation aliases (add to .bashrc or .zshrc)
alias docs-api="cd c:/repos/truthgraph/docs/api"
alias docs-arch="cd c:/repos/truthgraph/docs/architecture"
alias docs-services="cd c:/repos/truthgraph/docs/services"
alias plan-features="cd c:/repos/truthgraph/planning/features/in_progress"
alias plan-phase="cd c:/repos/truthgraph/planning/phases/phase_2"
alias archive-features="cd c:/repos/truthgraph/archive/completed_features"

# Quick search functions
function docs-find() { grep -r "$1" c:/repos/truthgraph/docs/; }
function plan-find() { grep -r "$1" c:/repos/truthgraph/planning/; }
```

---

## Success Checklist Visual

```
Pre-Migration
─────────────
[ ] Read DOCUMENTATION_ORGANIZATION_GUIDE.md
[ ] Review DOCUMENTATION_MIGRATION_PLAN.md
[ ] Backup current state (git branch backup-before-docs-reorg)
[ ] Team alignment on new structure

Migration
─────────
[ ] Create directory structure
[ ] Move permanent docs → docs/
[ ] Move active planning → planning/
[ ] Move historical docs → archive/
[ ] Create README.md indexes
[ ] Update root README.md

Post-Migration
──────────────
[ ] Verify no markdown files at root (except 3)
[ ] Fix broken links
[ ] Update Taskfile.yml paths
[ ] Test that nothing broke
[ ] Commit changes
[ ] Communicate to team
[ ] Archive migration guides
```

---

**Quick Reference Complete!**

For detailed information, see:
- **DOCUMENTATION_ORGANIZATION_GUIDE.md** - Comprehensive guide
- **DOCUMENTATION_MIGRATION_PLAN.md** - Migration steps
- **DOCUMENTATION_REORGANIZATION_SUMMARY.md** - Executive summary
