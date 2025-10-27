# TruthGraph v0: MVP Roadmap Documentation

Welcome to the TruthGraph v0 (Minimum Viable Product) roadmap documentation. This simplified version focuses on delivering core fact-checking functionality quickly while maintaining a clear upgrade path to v1.

## Quick Navigation

### Start Here

1. **[00_overview.md](./00_overview.md)** - Executive summary, architecture, and design principles
   - Read this first to understand the v0 MVP vision
   - 4-5 week timeline
   - Modular monolith approach
   - Success criteria

### Implementation Phases

1. **[phase_01_foundation.md](./phase_01_foundation.md)** - Weeks 1-2: Docker, database, API
   - Docker Compose setup
   - PostgreSQL schema
   - FastAPI monolith structure
   - Basic React UI

2. **[phase_02_core_features.md](./phase_02_core_features.md)** - Weeks 3-5: ML, embeddings, verification
   - sentence-transformers for embeddings
   - pgvector for semantic search
   - DeBERTa-v3 for NLI verification
   - Verdict aggregation logic

### Technical Deep Dives

1. **[backend_architecture.md](./backend_architecture.md)** - Modular monolith design
   - API, Domain, Infrastructure layers
   - Repository pattern
   - Synchronous processing flow
   - Evolution path to v1 microservices

2. **[database_schema.md](./database_schema.md)** - PostgreSQL + pgvector design
   - Complete schema (claims, evidence, verdicts, embeddings)
   - Indexing strategy
   - pgvector configuration
   - Migration strategy

3. **[fastapi_implementation.md](./fastapi_implementation.md)** - FastAPI patterns
   - Application structure
   - Request/response models
   - Dependency injection
   - Error handling
   - Testing strategy

4. **[tech_stack.md](./tech_stack.md)** - Technology choices and rationale
   - Why Python 3.12+, FastAPI, PostgreSQL
   - **htmx vs React decision**: Use htmx for v0 (3x faster), migrate to React for v1
   - Why NOT microservices, Redis, FAISS for v0
   - Performance expectations
   - Migration path to v1

## Key Differences: v0 vs v1

| Aspect | v0 (MVP) | v1 (Production) |
|--------|----------|-----------------|
| **Timeline** | 4-5 weeks | 8-12 weeks |
| **Architecture** | Single FastAPI app | 4 microservices |
| **Frontend** | **htmx** (HTML-over-the-wire) | **React** (interactive graphs) |
| **Processing** | Synchronous | Event-driven (Redis Streams) |
| **Vector Store** | pgvector only | pgvector + FAISS |
| **Containers** | 3 (API, DB, UI) | 7+ (services + infra) |
| **Complexity** | Low | High |
| **Multi-Tenancy** | Single user | Multi-tenant ready |
| **Observability** | Basic logs | OpenTelemetry + Prometheus |

### Why htmx for v0? 🚀

**v0's simple UI** (forms, lists, results) is perfect for htmx:
- **3x faster development**: 2 weeks vs 4-5 weeks for React
- **No build tooling**: No webpack, npm, babel - just HTML templates
- **Backend team can build UI**: Python devs already know Jinja2
- **10x smaller bundle**: 14KB vs 140KB
- **Server-side rendering**: SEO-friendly, works without JS

**v1 needs React** because:
- Interactive reasoning graph visualization (Cytoscape.js, D3.js)
- Real-time WebSocket updates
- Temporal timeline charts
- Multimodal UI (images, PDFs, videos)

**Migration**: htmx → React takes 2-3 weeks (only rewrite complex pages)

See [tech_stack.md - htmx vs React](./tech_stack.md#htmx-vs-react-the-decision) for detailed analysis.

## Reading Order

### For Developers

1. Start with [00_overview.md](./00_overview.md) to understand the vision
2. Read [tech_stack.md](./tech_stack.md) for technology decisions
3. Follow [phase_01_foundation.md](./phase_01_foundation.md) to set up infrastructure
4. Implement using [backend_architecture.md](./backend_architecture.md) and [fastapi_implementation.md](./fastapi_implementation.md)
5. Add ML features from [phase_02_core_features.md](./phase_02_core_features.md)
6. Reference [database_schema.md](./database_schema.md) as needed

### For Product Managers

1. Read [00_overview.md](./00_overview.md) for vision and success criteria
2. Review [phase_01_foundation.md](./phase_01_foundation.md) and [phase_02_core_features.md](./phase_02_core_features.md) for timelines
3. Understand [tech_stack.md](./tech_stack.md) for technology trade-offs

### For Architects

1. Start with [00_overview.md](./00_overview.md) for design principles
2. Deep dive into [backend_architecture.md](./backend_architecture.md)
3. Review [database_schema.md](./database_schema.md) for data design
4. Understand evolution path to v1 in each document

## Quick Start (Implementation)

```bash
# 1. Read the overview
cat 00_overview.md

# 2. Set up Phase 1 infrastructure
# Follow phase_01_foundation.md

# 3. Implement backend structure
# Follow backend_architecture.md

# 4. Add ML features
# Follow phase_02_core_features.md

# 5. Deploy
docker compose up -d
```

## Document Status

| Document | Status | Completeness |
|----------|--------|--------------|
| 00_overview.md | ✅ Final | 100% |
| phase_01_foundation.md | ✅ Final | 100% |
| phase_02_core_features.md | ✅ Final | 100% |
| backend_architecture.md | ✅ Final | 100% |
| database_schema.md | ✅ Final | 100% |
| fastapi_implementation.md | ✅ Final | 100% |
| tech_stack.md | ✅ Final | 100% |

## Evolution to v1

All v0 documents include sections on evolution to v1:
- What stays the same ✅
- What changes 🔄
- Migration steps
- Estimated effort

**Key Principle**: v0 is designed for easy evolution, not as throwaway code.

**Expected Code Reuse**: 50-70% of v0 code can be reused in v1 with minimal changes.

## Architecture Decision Records (ADRs)

Key architectural decisions documented in [00_overview.md](./00_overview.md#architecture-decision-records-adrs):
- **ADR-001**: Monolith vs Microservices (chose monolith)
- **ADR-002**: Synchronous vs Asynchronous (chose synchronous)
- **ADR-003**: pgvector Only (defer FAISS)
- **ADR-004**: No Multi-Tenancy (add in v1)
- **ADR-005**: htmx vs React (chose htmx for v0, React for v1)

## Related Documentation

### v1 Roadmap (Production-Ready)
- [v1 Overview](../v1/00_overview.md) - Full architecture with microservices
- [v1 Phase 1](../v1/phase_01_local_mvp.md) - Service extraction from v0

### Comparison
- v0 is **local-first, single-user, simple**
- v1 is **cloud-ready, multi-tenant, complex**
- v0 → v1 migration is **planned, not accidental**

## Getting Help

- **Questions about v0 architecture?** See [backend_architecture.md](./backend_architecture.md)
- **Database design questions?** See [database_schema.md](./database_schema.md)
- **FastAPI implementation?** See [fastapi_implementation.md](./fastapi_implementation.md)
- **Technology choices?** See [tech_stack.md](./tech_stack.md)
- **ML/NLP implementation?** See [phase_02_core_features.md](./phase_02_core_features.md)

## Contributing

When updating v0 documentation:
1. Keep it **simple** (avoid complexity creep)
2. Maintain **evolution path** to v1
3. Update **all related documents** (consistency)
4. Include **code examples** (practical guidance)
5. Document **trade-offs** (help readers make decisions)

## Success Criteria

v0 is considered successful when:
- ✅ Submit claim → get verdict in <60 seconds
- ✅ Runs on single machine (8GB RAM)
- ✅ 5-10 users provide positive feedback
- ✅ Code is clean enough to evolve to v1

## Timeline Summary

- **Week 1-2**: Phase 1 (Foundation)
- **Week 3-5**: Phase 2 (Core Features)
- **Week 5**: Testing, documentation, feedback
- **Total**: 4-5 weeks to working MVP

---

**Last Updated**: 2025-10-23
**Status**: Complete
**Version**: 1.0
