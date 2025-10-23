# TruthGraph v1: Local-First Implementation Overview

## Executive Summary

TruthGraph v1 is a **local-first fact-checking system** designed for researchers, journalists, and analysts who need privacy-preserving, portable, and research-friendly tools for claim verification and evidence analysis.

The system runs entirely on a user's workstation via **Docker Compose**, providing:

- **Temporal awareness**: Track claims and evidence across time
- **Compound reasoning**: Multi-hop inference with explainable reasoning chains
- **Multimodal support**: Text, images, video, and documents
- **Privacy by default**: All data remains local; no cloud dependencies
- **Research-friendly**: Export data, inspect reasoning graphs, audit provenance

The architecture prioritizes **simplicity and portability** while maintaining a clear path to optional cloud scaling for teams or organizations.

---

## High-Level Architecture

### Core Components

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  API Gateway │  │ Verification │  │   Corpus     │          │
│  │  (FastAPI)   │  │   Service    │  │   Service    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┴──────────────────┘                   │
│                           │                                       │
│                           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Event Bus (Redis Streams)                      ││
│  │              CloudEvents-compliant schemas                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                       │
│  ┌──────────────┬─────────┴─────────┬──────────────┐           │
│  │  PostgreSQL  │  Redis (Cache)    │   Worker     │           │
│  │  + pgvector  │  + Queue          │   Service    │           │
│  └──────────────┴───────────────────┴──────────────┘           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Storage Layer: FAISS, Embeddings (sentence-transformers)  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │             React Frontend (port 5173)                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Decisions**:

- **Service separation from day one**: Even in local deployment, services are isolated
- **Event-driven architecture**: CloudEvents-compliant event schemas for future cloud migration
- **Repository/Adapter pattern**: Abstract data access for easy backend swapping

### Technology Stack

- **Backend**: Python 3.12+ (uv for dependency management), FastAPI (multiple services)
- **Database**: PostgreSQL 16+ with pgvector extension (abstracted via Repository pattern)
- **Vector Store**: FAISS for local retrieval (abstracted for cloud vector DB migration)
- **Queue**: Redis Streams with CloudEvents schemas (cloud-agnostic event format)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2 or similar)
- **Frontend**: React + TypeScript, Vite
- **Infrastructure**: Docker Compose (Kubernetes manifests prepared but unused)
- **Observability**: structlog (structured logging), OpenTelemetry (tracing), Prometheus (metrics)
- **Development**: Taskfile (go-task), ruff, pymarkdownlnt, Sphinx

**Cloud-Ready Stack Choices**: Technologies selected to support seamless migration to v2 cloud deployment with minimal refactoring (see [v2 Cloud Readiness Guide](../v2/v1_improvements_for_cloud_readiness.md))

---

## Key Design Principles

### 1. Privacy-First

- **No external API calls required** for core functionality
- All data (claims, evidence, embeddings, reasoning graphs) stored locally
- Optional integrations (fact-check APIs, LLM services) are explicit opt-ins

### 2. Portability

- Single `docker-compose up` to run the entire stack
- Data volumes are easily backed up, migrated, or archived
- Export capabilities for claims, evidence, and reasoning graphs

### 3. Research-Friendly

- **Explainable reasoning**: Full provenance tracking and reasoning graph visualization
- **Reproducible**: Pin model versions, export configurations
- **Inspectable**: Direct database access, structured logs, reasoning chain exports

### 4. Cloud-Ready Architecture (New for v1)

- **Design once, deploy anywhere**: Abstractions enable local or cloud deployment
- **Service-oriented from start**: API Gateway, Verification, Corpus, Worker services
- **Adapter pattern**: Swap PostgreSQL for RDS, FAISS for Pinecone via configuration
- **Event-driven**: CloudEvents-compliant schemas work with Redis, SQS, or EventBridge
- **Observability built-in**: OpenTelemetry tracing, structured logs, Prometheus metrics from Phase 1
- **Multi-tenant ready**: Database schema includes `tenant_id` (always "default" in v1)

### 5. Optional Scaling

- Start local, scale to cloud when needed
- Architecture supports migration to managed services (RDS, ElastiCache, S3)
- Queue-based design enables horizontal scaling of workers
- See [v2 Cloud Migration Tasks](../v2/cloud_migration_tasks.md) for cloud deployment path

### 6. Developer Experience

- Modern tooling (uv, ruff, Taskfile)
- Comprehensive docs (Sphinx)
- Clear separation of concerns (API, storage, retrieval, reasoning)
- Contract testing between services for independent deployment

---

## Local vs Cloud Architecture Decisions

| Aspect | Local (v1) | Cloud (Future) |
|--------|-----------|----------------|
| **Database** | PostgreSQL in Docker | AWS RDS, Azure PostgreSQL, or similar |
| **Vector Store** | FAISS + pgvector | Pinecone, Weaviate, or managed pgvector |
| **Queue** | Redis in Docker | AWS SQS, Azure Service Bus, or managed Redis |
| **Storage** | Local volumes | S3, Azure Blob, or object storage |
| **Embeddings** | Local sentence-transformers | Hosted embedding APIs (OpenAI, Cohere) |
| **LLM Integration** | Optional local/API | Managed LLM services (OpenAI, Anthropic) |
| **Deployment** | Docker Compose | Kubernetes, ECS, or serverless |
| **Scaling** | Vertical (more RAM/CPU) | Horizontal (multiple workers, replicas) |
| **Auth** | Single-user (no auth) | Multi-tenant with OAuth/SAML |
| **Cost** | Hardware only | Pay-as-you-go infrastructure |

**Decision Rationale**: Local deployment maximizes privacy, minimizes costs for individual users, and avoids vendor lock-in. However, v1 is architected with cloud migration in mind - abstractions and patterns enable v2 cloud deployment with 50-70% less refactoring effort.

---

## Cloud-Ready Architecture Improvements

To ease the transition to v2 cloud deployment, v1 incorporates several "cloud-ready" patterns that work well locally but translate directly to cloud services:

### Service Separation

- **Pattern**: Multiple FastAPI services (API Gateway, Verification, Corpus, Worker) instead of monolith
- **Local benefit**: Clear boundaries, easier testing
- **Cloud benefit**: Services scale independently in Kubernetes, no microservice refactoring needed

### Repository/Adapter Pattern

- **Pattern**: Abstract all data access (PostgreSQL, FAISS, Redis) behind interfaces
- **Local benefit**: Easy to mock for testing, swap implementations
- **Cloud benefit**: Change `VECTOR_STORE=faiss` to `VECTOR_STORE=pinecone` in config - zero code changes

### Event-Driven with CloudEvents

- **Pattern**: All async work uses CloudEvents-compliant event schemas
- **Local benefit**: Audit trail, replay capability, clear contracts
- **Cloud benefit**: Same events work with Redis Streams (v1), SQS (v2), or EventBridge (v2)

### Observability from Day One

- **Pattern**: Structured logging (structlog), distributed tracing (OpenTelemetry), metrics (Prometheus) in Phase 1
- **Local benefit**: Easier debugging, performance visibility
- **Cloud benefit**: Logs/traces/metrics flow to CloudWatch/Datadog without instrumentation changes

### Multi-Tenant Database Schema

- **Pattern**: All tables include `tenant_id` column (always "default" in v1)
- **Local benefit**: Can test multi-tenant logic locally
- **Cloud benefit**: Zero schema changes needed for SaaS multi-tenancy in v2

### Configuration Management

- **Pattern**: Adapter-based secrets (env vars → Secrets Manager), feature flags
- **Local benefit**: Environment-specific configs, easier testing
- **Cloud benefit**: Same codebase runs locally or in AWS/Azure/GCP

**ROI**: These patterns add ~20% upfront effort in v1 but reduce v2 migration effort by 50-70%. See [v1 Improvements for Cloud Readiness](../v2/v1_improvements_for_cloud_readiness.md) for detailed implementation guidance.

---

## Core Capabilities

### Claim Verification

- Ingest claims from text, URLs, or documents
- Extract entities, dates, and structured metadata
- Store with provenance (source, timestamp, author)

### Evidence Retrieval

- Semantic search over evidence corpus using embeddings
- Keyword search with BM25 or PostgreSQL full-text search
- Cross-reference external fact-check databases (optional)

### Reasoning Graphs

- Multi-hop reasoning: chain evidence to support or refute claims
- Explainable: visualize reasoning paths, confidence scores
- Temporal reasoning: track claim mutations and evidence updates

### Multimodal Support

- Text: articles, tweets, transcripts
- Images: OCR, reverse image search, metadata extraction
- Video: frame sampling, transcript extraction
- Documents: PDF parsing, table extraction

### Provenance Tracking

- Every claim, evidence, and reasoning step is attributed
- Audit logs for all user actions
- Export full reasoning chains for reproducibility

---

## Implementation Roadmap

The v1 implementation is divided into four phases:

### Phase 1: Local MVP

**Goal**: Basic local deployment with claim ingestion and storage + cloud-ready foundations
**Document**: [phase_01_local_mvp.md](./phase_01_local_mvp.md)

- Docker Compose setup (PostgreSQL, Redis, separated FastAPI services, React)
- Service separation: API Gateway, Verification, Corpus, Worker
- Repository pattern for database abstraction
- CloudEvents-based event schemas
- Observability: structlog, OpenTelemetry, Prometheus
- Multi-tenant database schema (tenant_id = "default")
- Basic claim CRUD API
- Simple web UI for claim submission

### Phase 2: Core Features

**Goal**: Evidence retrieval and basic reasoning
**Document**: [phase_02_core_features.md](./phase_02_core_features.md)

- Embedding generation (sentence-transformers)
- FAISS + pgvector integration
- Semantic search API
- Basic reasoning engine (single-hop verification)
- Evidence storage and linking

### Phase 3: Enhanced Capabilities

**Goal**: Multi-hop reasoning, temporal awareness, multimodal support
**Document**: [phase_03_enhanced_capabilities.md](./phase_03_enhanced_capabilities.md)

- Multi-hop reasoning graphs
- Temporal claim tracking
- Image and document processing
- Provenance tracking and visualization
- Reasoning graph UI

### Phase 4: Production Features

**Goal**: Polish, performance, documentation, and release readiness
**Document**: [phase_04_production_features.md](./phase_04_production_features.md)

- Performance optimization (caching, indexing)
- Comprehensive testing (unit, integration, e2e)
- User documentation and tutorials
- Export/import capabilities
- Backup and restore tools
- Monitoring and logging

### Technology Stack & Tooling

**Document**: [tech_stack_and_tooling.md](./tech_stack_and_tooling.md)

Detailed justifications for all technology choices, alternative evaluations, and future considerations.

---

## Quick Start Vision

After v1 is complete, a new user should be able to get started in **under 5 minutes**:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/truthgraph.git
cd truthgraph

# 2. Start the stack (downloads images, initializes DB)
task up

# 3. Open the web interface
# Browser opens automatically to http://localhost:5173

# 4. Submit your first claim
# Paste a claim, add evidence, view reasoning graph

# 5. Export your research
task export --format json --output my_research.json
```

**Key Experience Goals**:

- No manual configuration required (sensible defaults)
- Clear feedback during startup (progress logs)
- Intuitive UI for non-technical users
- Fast initial response times (<2s for simple claims)
- Easy data export for external analysis

---

## Success Criteria for v1 - MVP

### Functional Requirements

- [ ] Successfully runs on Windows, macOS, and Linux via Docker Compose
- [ ] Ingest and store claims with structured metadata
- [ ] Generate embeddings and perform semantic search
- [ ] Execute multi-hop reasoning with explainable output
- [ ] Track temporal changes to claims and evidence
- [ ] Process text, images, and PDF documents
- [ ] Export reasoning graphs and provenance data
- [ ] Handle 10,000+ claims and 100,000+ evidence items without performance degradation

### Non-Functional Requirements

- [ ] **Startup time**: <60 seconds from `docker-compose up` to ready state
- [ ] **Search latency**: <500ms for semantic search (p95)
- [ ] **Reasoning latency**: <5s for 3-hop reasoning chains (p95)
- [ ] **Privacy**: Zero external API calls for core functionality (without opt-in)
- [ ] **Data portability**: Full export/import in <5 minutes for 10K claims
- [ ] **Documentation**: 90%+ coverage of user-facing features
- [ ] **Code quality**: 80%+ test coverage, ruff-compliant, type-checked

### User Experience

- [ ] Users can submit a claim and see initial results within 10 seconds
- [ ] Reasoning graphs are visually clear and interactive
- [ ] Error messages are actionable (not stack traces)
- [ ] System state is always visible (loading indicators, progress bars)
- [ ] Data export is one-click and produces usable formats (JSON, CSV, Markdown)

### Community & Adoption

- [ ] Published on GitHub with MIT or Apache 2.0 license
- [ ] At least 3 external contributors submit PRs
- [ ] Used by at least 10 external researchers/journalists
- [ ] Documented in 2+ blog posts or talks

---

## Next Steps - MVP

1. **Review this overview** with stakeholders and incorporate feedback
2. **Read phase documents** in order (Phase 1 → Phase 2 → Phase 3 → Phase 4)
3. **Review tech stack decisions** in [tech_stack_and_tooling.md](./tech_stack_and_tooling.md)
4. **Begin Phase 1 implementation** following the MVP plan
5. **Iterate rapidly** with weekly check-ins and user feedback

---

## Related Documentation - MVP

### V1 Implementation Guides

- [Phase 1: Local MVP](./phase_01_local_mvp.md)
- [Phase 2: Core Features](./phase_02_core_features.md)
- [Phase 3: Enhanced Capabilities](./phase_03_enhanced_capabilities.md)
- [Phase 4: Production Features](./phase_04_production_features.md)
- [Technology Stack & Tooling](./tech_stack_and_tooling.md)

### V2 Cloud Migration

- [Cloud Migration Tasks](../v2/cloud_migration_tasks.md) - Component replacements and cloud architecture changes
- [V1 Improvements for Cloud Readiness](../v2/v1_improvements_for_cloud_readiness.md) - Architectural patterns to implement in v1 for easier v2 migration

---

## Document Structure

This roadmap is organized into focused documents that build progressively:

- **00_overview.md** (this document): High-level vision, architecture, and success criteria
- **phase_01_local_mvp.md**: Foundation - Docker setup, basic APIs, minimal UI
- **phase_02_core_features.md**: Core functionality - embeddings, search, basic reasoning
- **phase_03_enhanced_capabilities.md**: Advanced features - multi-hop reasoning, temporal tracking, multimodal
- **phase_04_production_features.md**: Polish - performance, testing, documentation, release prep
- **tech_stack_and_tooling.md**: Deep dive into technology choices and rationale

**Navigation Tips**:

- Read documents sequentially if you're new to the project
- Each phase document includes detailed acceptance criteria and implementation notes
- Cross-references link to specific sections for deeper exploration
- All phase documents follow the same structure: Goals, Features, Success Criteria, Dependencies

---

## Getting Started with This Roadmap

### For Contributors

1. **Start here**: Read this overview to understand the vision and architecture
2. **Deep dive**: Review [tech_stack_and_tooling.md](./tech_stack_and_tooling.md) to understand technology decisions
3. **Pick a phase**: Check current project status, then read the relevant phase document
4. **Implement**: Follow the acceptance criteria in each phase document as your checklist
5. **Test**: Refer to success criteria to validate your implementation

### For Project Managers

- Use the **Success Criteria** section below to track overall progress
- Each phase document has granular acceptance criteria for sprint planning
- The comparison table (Local vs Cloud) clarifies scope boundaries for v1
- Quick Start Vision defines the target user experience

### For Stakeholders

- **Executive Summary** provides the 30-second pitch
- **Key Design Principles** explain architectural decisions
- **Core Capabilities** outline what users can do with the system
- **What's Next After v1** section (below) previews future directions

---

## Local-First Philosophy: Why It Matters

TruthGraph v1 is **intentionally local-first**, not as a limitation, but as a core feature:

### Privacy and Trust

- **No data leakage**: Sensitive research stays on your hardware
- **No tracking**: No analytics, telemetry, or usage data leaves your machine
- **No vendor dependency**: Your data isn't held hostage by a service provider
- **Auditable**: Inspect every API call, database query, and reasoning step

### Autonomy and Control

- **Offline capable**: Work without internet access (after initial setup)
- **Your rules**: No terms of service changes, no forced updates, no feature removal
- **Data ownership**: 100% control over backups, retention, and deletion
- **Reproducibility**: Exact same environment can be recreated years later

### Cost and Sustainability

- **Zero recurring costs**: No subscriptions, API fees, or per-query charges
- **Resource efficient**: Runs on modest hardware (8GB RAM, 4 CPU cores)
- **Long-term viability**: Not dependent on startup funding or corporate priorities
- **Academic-friendly**: No budget required for proof-of-concept research

### Research Integrity

- **Deterministic**: Same inputs produce same outputs (given fixed model versions)
- **Transparent**: Full access to data, models, and reasoning processes
- **Portable**: Share complete research environments via Docker images
- **Citation-ready**: Export complete provenance for academic papers

**The Cloud Path**: While v1 is local-first, the architecture explicitly supports cloud migration for teams, organizations, or high-scale use cases. This is a **choice**, not a compromise.

---

## What's Next After v1

TruthGraph v1 establishes the foundation, but the vision extends further:

### Short-Term Updates (v1.x)

- **Performance tuning**: Faster embeddings, optimized indexing, query caching
- **Model flexibility**: Swap embedding models, support custom fine-tuned models
- **UI polish**: Keyboard shortcuts, dark mode, accessibility improvements
- **Integrations**: Browser extension, Obsidian plugin, API client libraries

### Mid-Term Evolution (v2.0)

- **Collaborative workflows**: Multi-user support, shared workspaces, comments
- **Advanced reasoning**: Probabilistic inference, contradiction detection, claim clustering
- **Enhanced multimodal**: Video analysis, audio transcription, live web scraping
- **Cloud-optional**: Deploy to AWS/Azure/GCP with one-command migration

### Long-Term Vision (v3.0+)

- **Federated fact-checking**: P2P networks for sharing evidence without centralization
- **Active learning**: System proposes claims to investigate based on gaps in evidence
- **Cross-lingual support**: Translate claims, search multilingual evidence
- **Automated monitoring**: Track evolving claims over time, alert on new evidence

### Community-Driven Development

- **Plugin ecosystem**: Let users extend reasoning engines, add custom data sources
- **Model marketplace**: Share fine-tuned models for specific domains (medical, political, etc.)
- **Dataset contributions**: Curated evidence corpora for common fact-checking domains
- **Research partnerships**: Collaborate with universities on novel reasoning techniques

**Principle**: Future development will maintain backward compatibility and the local-first option. Cloud features will be **additive**, not replacements.

---

## Success Criteria for v1

### Functional Requirements - Success Criteria for v1

- [ ] Successfully runs on Windows, macOS, and Linux via Docker Compose
- [ ] Ingest and store claims with structured metadata (source, timestamp, entities)
- [ ] Generate embeddings and perform semantic search over evidence
- [ ] Execute multi-hop reasoning (up to 5 hops) with explainable output
- [ ] Track temporal changes to claims and evidence over time
- [ ] Process text, images, and PDF documents with metadata extraction
- [ ] Export reasoning graphs and provenance data in multiple formats
- [ ] Handle 10,000+ claims and 100,000+ evidence items without performance degradation
- [ ] Support claim mutation tracking (how claims evolve over time)
- [ ] Provide confidence scores for reasoning chains with transparent calculation

### Non-Functional Requirements - Success Criteria for v1

- [ ] **Startup time**: <60 seconds from `docker-compose up` to ready state
- [ ] **Search latency**: <500ms for semantic search over 100K items (p95)
- [ ] **Reasoning latency**: <5s for 3-hop reasoning chains (p95)
- [ ] **Memory footprint**: <4GB RAM for typical workloads (10K claims)
- [ ] **Privacy**: Zero external API calls for core functionality (without opt-in)
- [ ] **Data portability**: Full export/import in <5 minutes for 10K claims
- [ ] **Documentation**: 90%+ coverage of user-facing features with examples
- [ ] **Code quality**: 80%+ test coverage, ruff-compliant, type-checked (mypy strict)
- [ ] **Security**: No hardcoded credentials, secure defaults, dependency scanning

### User Experience - Success Criteria for v1

- [ ] Users can submit a claim and see initial results within 10 seconds
- [ ] Reasoning graphs are visually clear and interactive (zoom, filter, export)
- [ ] Error messages are actionable with suggested fixes (not stack traces)
- [ ] System state is always visible (loading indicators, progress bars, status messages)
- [ ] Data export is one-click and produces usable formats (JSON, CSV, Markdown, GraphML)
- [ ] First-run experience includes sample data and interactive tutorial
- [ ] Keyboard shortcuts for power users (search, navigate, export)
- [ ] Mobile-responsive UI for reviewing results on tablets

### Reliability & Maintainability

- [ ] **Crash recovery**: System gracefully recovers from container restarts
- [ ] **Data integrity**: Database migrations tested and reversible
- [ ] **Logging**: Structured logs with clear severity levels and context
- [ ] **Monitoring**: Health check endpoints for all services
- [ ] **Backup/restore**: Automated backup scripts with verification
- [ ] **Upgrade path**: Clear migration guide from future v1.x versions

### Cloud Readiness (Architecture Quality)

- [ ] **Service isolation**: Can deploy API/Verification/Corpus/Worker services independently
- [ ] **Adapter pattern**: Can swap FAISS for Pinecone via config (tested with emulator)
- [ ] **Event schemas**: All async work uses CloudEvents-compliant schemas
- [ ] **Observability**: Correlation IDs in all logs, distributed tracing works across services
- [ ] **Multi-tenant schema**: Database includes tenant_id columns on all tables
- [ ] **Contract tests**: Service-to-service API contracts validated in CI/CD

### Community & Adoption - Success Criteria for v1

- [ ] Published on GitHub with MIT or Apache 2.0 license
- [ ] At least 3 external contributors submit PRs
- [ ] Used by at least 10 external researchers/journalists with documented case studies
- [ ] Documented in 2+ blog posts or conference talks
- [ ] Active community channel (Discord, Slack, or forum) with response SLA

---

## Next Steps

1. **Review this overview** with stakeholders and incorporate feedback
2. **Read phase documents** in order (Phase 1 → Phase 2 → Phase 3 → Phase 4)
3. **Review tech stack decisions** in [tech_stack_and_tooling.md](./tech_stack_and_tooling.md)
4. **Begin Phase 1 implementation** following the MVP plan
5. **Iterate rapidly** with weekly check-ins and user feedback

---

## Related Documentation

### V1 Implementation Guides - Related Documentation

- [Phase 1: Local MVP](./phase_01_local_mvp.md)
- [Phase 2: Core Features](./phase_02_core_features.md)
- [Phase 3: Enhanced Capabilities](./phase_03_enhanced_capabilities.md)
- [Phase 4: Production Features](./phase_04_production_features.md)
- [Technology Stack & Tooling](./tech_stack_and_tooling.md)

### V2 Cloud Migration - Related Documentation

- [Cloud Migration Tasks](../v2/cloud_migration_tasks.md) - Component replacements and cloud architecture changes
- [V1 Improvements for Cloud Readiness](../v2/v1_improvements_for_cloud_readiness.md) - Architectural patterns to implement in v1 for easier v2 migration

---

**Document Version**: 3.0 (Cloud-Ready)
**Last Updated**: 2025-10-22
**Status**: Enhanced - Ready for Review
