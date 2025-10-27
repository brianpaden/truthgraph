# Backend Documentation Organization Guide

**Author**: Backend System Architect
**Date**: 2025-10-26
**Project**: TruthGraph v0

## Executive Summary

This guide provides comprehensive architectural guidance for organizing markdown-based project documentation in a backend repository. It addresses the challenge of managing documentation when all project management (issues, features, planning) is done via markdown files rather than external tools.

**Problem**: 33+ markdown files at root level, unclear organization, difficult to distinguish active vs historical documentation.

**Solution**: Structured three-tier documentation system with clear separation of concerns: permanent docs, active planning, and historical archive.

## Documentation Philosophy

### Core Principles

1. **Separation of Concerns**: Permanent documentation (docs/), active planning (planning/), historical archive (archive/)
2. **Developer-First**: Easy to find, easy to maintain, easy to contribute
3. **Lifecycle Management**: Clear path from planning → implementation → completion → archive
4. **Discoverability**: Comprehensive indexes, clear naming, logical structure
5. **Scalability**: Structure that grows gracefully without becoming cluttered

### Documentation Types

| Type | Location | Purpose | Update Frequency |
|------|----------|---------|------------------|
| **Permanent** | `docs/` | Long-lived technical documentation | Rarely (major changes only) |
| **Active** | `planning/` | Work in progress, current planning | Frequently (daily/weekly) |
| **Historical** | `archive/` | Completed work, lessons learned | Never (read-only) |
| **Ephemeral** | `planning/features/in_progress/` | Short-term tracking | Moves to archive when done |

## Directory Structure

```text
c:/repos/truthgraph/
│
├── README.md                                    # Project overview only
├── CONTRIBUTING.md                              # Contribution guidelines
├── CHANGELOG.md                                 # Version history
│
├── docs/                                        # PERMANENT DOCUMENTATION
│   ├── README.md                                # Documentation index
│   │
│   ├── api/                                     # API Documentation
│   │   ├── README.md                            # API overview
│   │   ├── endpoints/                           # Endpoint documentation
│   │   │   ├── claims.md                        # Claims endpoints
│   │   │   ├── evidence.md                      # Evidence endpoints
│   │   │   ├── verification.md                  # Verification endpoints
│   │   │   └── ml.md                            # ML service endpoints
│   │   ├── schemas/                             # Data schemas
│   │   │   ├── claim_schema.md
│   │   │   └── verdict_schema.md
│   │   ├── authentication.md                    # Auth/authz
│   │   ├── error_codes.md                       # Error reference
│   │   ├── rate_limiting.md                     # Rate limits
│   │   └── versioning.md                        # API versioning
│   │
│   ├── architecture/                            # Architecture Documentation
│   │   ├── README.md                            # Architecture overview
│   │   ├── decisions/                           # ADRs
│   │   │   ├── 001-fastapi-framework.md
│   │   │   ├── 002-pgvector-choice.md
│   │   │   ├── 003-ml-service-integration.md
│   │   │   └── template.md
│   │   ├── system_design.md                     # High-level design
│   │   ├── service_architecture.md              # Microservices
│   │   ├── data_flow.md                         # Data flows
│   │   ├── tech_stack.md                        # Tech stack
│   │   └── scalability.md                       # Scaling patterns
│   │
│   ├── services/                                # Service Documentation
│   │   ├── README.md                            # Services overview
│   │   ├── hybrid_search.md                     # Hybrid search
│   │   ├── verification_pipeline.md             # Verification
│   │   ├── verdict_aggregation.md               # Verdict aggregation
│   │   ├── embedding_service.md                 # Embeddings
│   │   ├── nli_service.md                       # NLI
│   │   └── vector_search.md                     # Vector search
│   │
│   ├── database/                                # Database Documentation
│   │   ├── README.md                            # Database overview
│   │   ├── schema.md                            # Schema docs
│   │   ├── migrations/                          # Migration guides
│   │   │   ├── README.md
│   │   │   └── phase2_migration.md
│   │   ├── indexes.md                           # Index strategy
│   │   ├── query_patterns.md                    # Query patterns
│   │   └── pgvector_setup.md                    # pgvector config
│   │
│   ├── deployment/                              # Deployment Documentation
│   │   ├── README.md                            # Deployment overview
│   │   ├── docker.md                            # Docker deployment
│   │   ├── docker-ml.md                         # ML setup
│   │   ├── gpu-support.md                       # GPU config
│   │   ├── environment-variables.md             # Configuration
│   │   ├── health-checks.md                     # Health checks
│   │   └── troubleshooting.md                   # Troubleshooting
│   │
│   ├── development/                             # Development Guides
│   │   ├── README.md                            # Dev overview
│   │   ├── setup.md                             # Local setup
│   │   ├── testing.md                           # Testing guide
│   │   ├── code-style.md                        # Code conventions
│   │   └── debugging.md                         # Debugging
│   │
│   ├── operations/                              # Operations/Runbooks
│   │   ├── README.md                            # Ops overview
│   │   ├── monitoring.md                        # Monitoring
│   │   ├── performance-tuning.md                # Performance
│   │   ├── incident-response.md                 # Incident response
│   │   ├── backup-restore.md                    # Backups
│   │   └── scaling.md                           # Scaling guide
│   │
│   ├── guides/                                  # User-Facing Guides
│   │   ├── user-guide.md                        # User guide
│   │   ├── developer-guide.md                   # Developer guide
│   │   ├── api-quick-reference.md               # Quick reference
│   │   └── quickstart/                          # Quick starts
│   │       ├── hybrid-search.md
│   │       ├── embedding-service.md
│   │       └── migration.md
│   │
│   ├── research/                                # Research & Experiments
│   │   ├── README.md                            # Research overview
│   │   ├── experiments/                         # Experimental work
│   │   │   └── 00-bayesian.md
│   │   └── concept/                             # Concept docs
│   │       ├── compound-fact-reasoning.md
│   │       ├── explainable-reasoning-graph.md
│   │       ├── multimodal-fact-verification.md
│   │       └── temporal-fact-engine.md
│   │
│   └── integration/                             # Integration Guides
│       ├── README.md                            # Integration overview
│       ├── external-services.md                 # External integrations
│       └── webhooks.md                          # Webhooks
│
├── planning/                                    # ACTIVE PLANNING
│   ├── README.md                                # Planning overview
│   │
│   ├── roadmap/                                 # Product Roadmap
│   │   ├── README.md                            # Roadmap overview
│   │   ├── v0/                                  # Version 0
│   │   ├── v1/                                  # Version 1
│   │   └── v2/                                  # Version 2
│   │
│   ├── features/                                # Feature Planning
│   │   ├── README.md                            # Feature index
│   │   ├── in_progress/                         # Active features
│   │   │   └── feature_X.md
│   │   ├── planned/                             # Planned features
│   │   │   └── feature_Y.md
│   │   └── backlog/                             # Backlog
│   │       └── feature_ideas.md
│   │
│   ├── phases/                                  # Phase Planning
│   │   ├── phase_2/                             # Current phase
│   │   │   ├── plan.md                          # Original plan
│   │   │   ├── progress.md                      # LIVING DOC: daily updates
│   │   │   ├── quick-reference.md               # Quick ref
│   │   │   ├── tasks.md                         # Task breakdown
│   │   │   └── blockers.md                      # Current blockers
│   │   └── phase_3/                             # Next phase
│   │       └── plan.md
│   │
│   ├── technical_debt/                          # Technical Debt
│   │   ├── README.md                            # Debt index
│   │   ├── test-fixes-needed.md                 # Test issues
│   │   ├── performance-debt.md                  # Performance issues
│   │   └── refactoring-candidates.md            # Refactoring needs
│   │
│   └── tasks/                                   # Task Management
│       ├── README.md                            # Task overview
│       └── taskfile-updates.md                  # Taskfile changes
│
└── archive/                                     # HISTORICAL ARCHIVE
    ├── README.md                                # Archive index
    │
    ├── completed_features/                      # Completed Features
    │   ├── feature-5-verdict-aggregation.md
    │   ├── feature-6-implementation.md
    │   ├── feature-10-implementation.md
    │   └── feature-11-docker-delivery.md
    │
    ├── completed_phases/                        # Completed Phases
    │   ├── phase-1-completion.md
    │   └── phase-2-completion.md
    │
    ├── implementation_summaries/                # Implementation Summaries
    │   ├── api-integration-summary.md
    │   ├── docker-implementation-summary.md
    │   ├── embedding-service-summary.md
    │   └── hybrid-search-summary.md
    │
    └── deprecated/                              # Deprecated Docs
        └── old-api-design.md
```

## Backend-Specific Considerations

### 1. API Documentation Structure

**Location**: `docs/api/`

**Key files**:
- `README.md` - API overview, authentication, base URLs
- `endpoints/` - One file per resource or logical grouping
- `schemas/` - Request/response schemas with examples
- `authentication.md` - Auth/authz patterns (JWT, OAuth, API keys)
- `error_codes.md` - Standardized error responses
- `rate_limiting.md` - Rate limiting policies
- `versioning.md` - API versioning strategy

**Example endpoint documentation** (`docs/api/endpoints/claims.md`):
```markdown
# Claims API

## POST /api/v1/claims

Create a new claim for verification.

### Request

**Headers**:
- `Content-Type: application/json`
- `Authorization: Bearer <token>`

**Body**:
json
{
  "text": "The Earth is flat.",
  "source": "https://example.com/article",
  "context": "Scientific claim"
}


### Response

**Success (201 Created)**:
json
{
  "id": "claim_123",
  "text": "The Earth is flat.",
  "status": "pending",
  "created_at": "2025-10-26T12:00:00Z"
}


**Errors**:
- `400 Bad Request` - Invalid claim text
- `401 Unauthorized` - Missing or invalid token
- `429 Too Many Requests` - Rate limit exceeded

### Rate Limits
- 100 requests per minute per user
- 10,000 requests per day per user

### Example

bash
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"text": "The Earth is flat.", "source": "https://example.com"}'
```

### 2. Architecture Decision Records (ADRs)

**Location**: `docs/architecture/decisions/`

**Naming**: `NNN-short-title.md` (e.g., `001-fastapi-framework.md`)

**Template** (`docs/architecture/decisions/template.md`):
```markdown
# ADR NNN: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Date
YYYY-MM-DD

## Context
What is the issue that we're seeing that is motivating this decision or change?

Include:
- Business/technical problem
- Requirements and constraints
- Current situation
- Why this decision is needed now

## Decision
What is the change that we're proposing and/or doing?

Include:
- Clear statement of the decision
- Key components affected
- Implementation approach
- Timeline (if applicable)

## Consequences

### Positive
- What becomes easier
- Benefits gained
- Problems solved

### Negative
- What becomes more complex
- Technical debt introduced
- Trade-offs accepted

### Neutral
- Things that change but aren't clearly better or worse

## Alternatives Considered

### Alternative 1: [Name]
**Description**: Brief description
**Pros**:
- Advantage 1
- Advantage 2
**Cons**:
- Disadvantage 1
- Disadvantage 2
**Rejected because**: Reason for rejection

### Alternative 2: [Name]
...

## Implementation Notes
- Key implementation details
- Migration path (if applicable)
- Rollback strategy

## Related Decisions
- ADR 003: Related decision
- ADR 005: Supersedes this decision

## References
- External resources
- Related documentation
- Discussion links
```

**Example ADR** (`docs/architecture/decisions/002-pgvector-choice.md`):
```markdown
# ADR 002: Use pgvector for Vector Storage

## Status
Accepted

## Date
2025-09-15

## Context
TruthGraph requires efficient semantic search capabilities for evidence retrieval. We need to store and query high-dimensional embeddings (384-dimensional vectors from all-MiniLM-L6-v2).

Requirements:
- Store 100K+ document embeddings
- Cosine similarity search with <100ms latency
- Integration with existing PostgreSQL database
- Support for hybrid search (vector + traditional filters)
- Production-ready with community support

Current situation:
- Already using PostgreSQL 16 for relational data
- Need to avoid additional infrastructure complexity
- Team has PostgreSQL expertise, no Elasticsearch/Pinecone experience

## Decision
We will use pgvector extension for PostgreSQL to store and query vector embeddings.

Key components:
- pgvector extension on PostgreSQL 16
- HNSW indexes for approximate nearest neighbor search
- Cosine distance operator for similarity
- Integration with existing SQLAlchemy models

## Consequences

### Positive
- Single database system (PostgreSQL) for all data
- Native SQL joins between vector and relational data
- ACID transactions for consistency
- Familiar PostgreSQL operations and tooling
- Lower operational complexity (no separate vector DB)
- Excellent hybrid search support (vector + filters)

### Negative
- Lower performance than specialized vector databases (Pinecone, Weaviate) at massive scale
- Limited to PostgreSQL ecosystem
- Requires PostgreSQL 14+ with pgvector extension
- HNSW index builds can be slow for large datasets

### Neutral
- Need to tune HNSW parameters (m, ef_construction)
- Vector dimension size affects index performance
- Requires PostgreSQL tuning for vector workloads

## Alternatives Considered

### Alternative 1: Pinecone
**Description**: Managed vector database service
**Pros**:
- Best-in-class vector search performance
- Fully managed, no ops burden
- Scales to billions of vectors
**Cons**:
- Additional service dependency and cost
- Data residency outside PostgreSQL
- Eventual consistency model
- Network latency for cross-service joins
**Rejected because**: Adds operational complexity, cost, and data is split across two systems

### Alternative 2: Elasticsearch with dense_vector
**Description**: Use Elasticsearch for vector search
**Pros**:
- Mature search platform
- Good text + vector hybrid search
- Rich query DSL
**Cons**:
- Additional infrastructure (Elasticsearch cluster)
- Complex deployment and tuning
- Data duplication (PostgreSQL + Elasticsearch)
- Higher operational burden
**Rejected because**: Too much complexity for v0, team lacks Elasticsearch expertise

### Alternative 3: In-memory vector store (FAISS)
**Description**: Use FAISS library for in-memory vector search
**Pros**:
- Fastest search performance
- No external dependencies
**Cons**:
- No persistence (rebuild on restart)
- No ACID transactions
- Complex distributed synchronization
- Limited by single-machine RAM
**Rejected because**: Not production-ready, no persistence guarantees

## Implementation Notes
- Install pgvector extension: `CREATE EXTENSION vector;`
- Use HNSW index: `CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);`
- Tune HNSW parameters based on dataset size (start with m=16, ef_construction=64)
- Monitor query performance and adjust as needed
- Consider partitioning for datasets >1M vectors

Migration path:
1. Install pgvector extension in PostgreSQL
2. Add vector column to documents table
3. Create HNSW index
4. Populate embeddings from ML service
5. Test query performance

## Related Decisions
- ADR 001: FastAPI Framework - Uses SQLAlchemy for PostgreSQL
- ADR 003: ML Service Integration - Generates embeddings

## References
- pgvector GitHub: https://github.com/pgvector/pgvector
- HNSW algorithm: https://arxiv.org/abs/1603.09320
- PostgreSQL vector performance: https://www.timescale.com/blog/pgvector-vs-pinecone/
```

### 3. Service Documentation

**Two-tier approach**:

1. **Service-level READMEs** (in code): `truthgraph/services/ml/README_VERDICT_AGGREGATION.md`
   - Implementation details
   - Code structure
   - Internal APIs
   - Developer-focused

2. **Documentation-level docs**: `docs/services/verdict_aggregation.md`
   - Architecture and design
   - External API contracts
   - Integration patterns
   - User-focused

**Service documentation template** (`docs/services/template.md`):
```markdown
# [Service Name] Service

## Overview
Brief description of service purpose and responsibilities.

## Service Boundaries
- What this service owns
- What this service does NOT own
- Clear boundaries with other services

## Architecture

### Components
- Component 1: Responsibility
- Component 2: Responsibility

### Data Model
- Key entities owned by this service
- Relationships to other services' entities

### Dependencies
- Upstream services
- Downstream services
- External services

## API Contract

### Endpoints

#### POST /api/v1/service/action
Description, request/response schemas, examples

### Events Published
- Event name: When published, payload schema

### Events Consumed
- Event name: How processed, side effects

## Integration Patterns

### Synchronous Communication
- REST API endpoints
- gRPC methods (if applicable)

### Asynchronous Communication
- Message queues
- Event streams

### Error Handling
- Error codes returned
- Retry policies
- Fallback strategies

## Configuration

### Environment Variables
- `SERVICE_CONFIG_1`: Description, default value
- `SERVICE_CONFIG_2`: Description, default value

### Feature Flags
- `feature_x_enabled`: Description

### Resource Requirements
- CPU: X cores
- Memory: Y GB
- Storage: Z GB

## Observability

### Key Metrics
- `service_requests_total` - Total requests
- `service_latency_seconds` - Request latency
- `service_errors_total` - Error count

### Logging
- Log format: JSON structured logs
- Key log events: request start, request end, errors
- Correlation ID: `X-Request-ID` header

### Tracing
- Trace propagation: OpenTelemetry
- Key spans: service entry, database query, external call

## Resilience

### Circuit Breakers
- Upstream service X: 50% error rate, 10s timeout

### Retry Policies
- Exponential backoff: 100ms, 200ms, 400ms
- Max retries: 3

### Timeouts
- Database queries: 5s
- External API calls: 10s

### Fallback Strategies
- Cached response when service unavailable
- Degraded mode: partial functionality

## Performance

### Expected Latency
- P50: <50ms
- P95: <200ms
- P99: <500ms

### Throughput
- Target: 1000 requests/second
- Max: 5000 requests/second

### Optimization Strategies
- Connection pooling
- Caching strategy
- Async processing

## Testing

### Unit Tests
- Coverage target: 80%
- Test doubles: Mocks for external services

### Integration Tests
- Database integration
- Message queue integration

### Performance Tests
- Load testing: 2000 RPS
- Stress testing: 10000 RPS

## Deployment

### Service Dependencies
- PostgreSQL 16+
- Redis 7+
- RabbitMQ 3.12+

### Health Checks
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

### Scaling
- Stateless: Can horizontally scale
- Scaling trigger: CPU > 70%

## Troubleshooting

### Common Issues

#### Issue 1: High latency
**Symptoms**: P95 latency > 1s
**Diagnosis**: Check database query performance
**Resolution**: Add indexes, optimize queries

#### Issue 2: Service unavailable
**Symptoms**: 503 errors
**Diagnosis**: Check upstream service health
**Resolution**: Restart service, check circuit breaker state

## Related Documentation
- [API Documentation](../api/endpoints/service.md)
- [Architecture Decision](../architecture/decisions/003-service-design.md)
- [Database Schema](../database/schema.md#service-tables)
```

### 4. Feature Lifecycle Management

**Feature states**:
- **Planned**: `planning/features/planned/feature_X.md`
- **In Progress**: `planning/features/in_progress/feature_X.md`
- **Completed**: `archive/completed_features/feature_X.md`

**Feature template** (`planning/features/template.md`):
```markdown
# Feature X: [Feature Name]

## Status
[Planned | In Progress | Completed]

## Priority
[P0: Critical | P1: High | P2: Medium | P3: Low]

## Overview
Brief description of the feature and its business value.

## Requirements

### Functional Requirements
- FR1: User can do X
- FR2: System must provide Y
- FR3: API supports Z

### Non-Functional Requirements
- NFR1: Response time < 200ms
- NFR2: Handle 1000 concurrent users
- NFR3: 99.9% uptime

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Architecture

### Service Boundaries
- Services affected: Service A, Service B
- New services needed: None

### API Changes
- New endpoints:
  - `POST /api/v1/new-endpoint`
- Modified endpoints:
  - `GET /api/v1/existing-endpoint` - Add new parameter

### Database Changes
- New tables: `feature_x_data`
- Modified tables: `existing_table` - Add column `feature_x_id`
- Migrations needed: Yes

### Event Changes
- New events published:
  - `feature.x.created`
- New events consumed:
  - `user.action.occurred`

## Dependencies

### Blocked By
- Feature Y must be completed first

### Depends On
- Service Z must be available

### External Dependencies
- Third-party API integration needed

## Implementation Plan

### Phase 1: Foundation
- [ ] Design database schema
- [ ] Create API contracts
- [ ] Set up service skeleton

### Phase 2: Core Implementation
- [ ] Implement business logic
- [ ] Add database integration
- [ ] Create API endpoints

### Phase 3: Integration
- [ ] Integrate with Service A
- [ ] Add event handlers
- [ ] Update frontend

### Phase 4: Polish
- [ ] Add error handling
- [ ] Add observability
- [ ] Write documentation

### Phase 5: Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Performance tests

### Phase 6: Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Monitor metrics

## Technical Debt

### Known Issues
- Issue 1: Temporary workaround for X (will be fixed in Feature Y)

### Future Improvements
- Improvement 1: Optimize query performance
- Improvement 2: Add caching layer

## Risks

### Risk 1: Performance bottleneck
**Likelihood**: Medium
**Impact**: High
**Mitigation**: Load testing, caching strategy

### Risk 2: External API reliability
**Likelihood**: Low
**Impact**: High
**Mitigation**: Circuit breaker, fallback response

## Timeline

- **Start Date**: 2025-10-26
- **Target Completion**: 2025-11-15
- **Actual Completion**: TBD

## Metrics

### Success Metrics
- Metric 1: Feature usage > 1000 users/day
- Metric 2: Response time < 200ms
- Metric 3: Error rate < 0.1%

### Monitoring
- Dashboard: link
- Alerts: Alert when error rate > 1%

## Lessons Learned
(To be filled after completion)

- What went well:
- What could be improved:
- Unexpected challenges:

## Related Documentation
- [Architecture Decision](../docs/architecture/decisions/005-feature-x-design.md)
- [API Documentation](../docs/api/endpoints/feature-x.md)
- [Service Documentation](../docs/services/feature-x-service.md)
```

## Development Workflow Integration

### Weekly Planning Workflow

```bash
# Monday: Review planning status
cd planning/

# Check active features
ls features/in_progress/

# Review phase progress
cat phases/phase_2/progress.md

# Check technical debt
cat technical_debt/README.md

# Wednesday: Update progress
vim phases/phase_2/progress.md  # Update with this week's progress

# Friday: Move completed features to archive
mv features/in_progress/feature_X.md ../archive/completed_features/
```

### Feature Development Workflow

```bash
# 1. Create feature plan
vim planning/features/planned/feature_13.md

# 2. Start implementation
mv planning/features/planned/feature_13.md planning/features/in_progress/
vim planning/features/in_progress/feature_13.md  # Update status

# 3. During development: Update progress
vim planning/features/in_progress/feature_13.md  # Add notes, blockers

# 4. Complete feature
mv planning/features/in_progress/feature_13.md archive/completed_features/
vim archive/completed_features/feature_13.md  # Add lessons learned
```

### Phase Management Workflow

```bash
# Phase planning
vim planning/phases/phase_3/plan.md

# During phase: Daily/weekly updates
vim planning/phases/phase_3/progress.md

# Track blockers
vim planning/phases/phase_3/blockers.md

# Complete phase
cp planning/phases/phase_3/progress.md archive/completed_phases/phase_3_completion.md
vim archive/completed_phases/phase_3_completion.md  # Add summary
```

## Naming Conventions

### File Naming

**General rules**:
- Use lowercase with underscores: `vector_search_service.md`
- Use descriptive names: `verdict_aggregation.md` not `va.md`
- Use consistent suffixes:
  - `_service.md` - Service documentation
  - `_api.md` - API documentation
  - `_schema.md` - Schema documentation
  - `_guide.md` - User/developer guides
  - `_quickstart.md` - Quick start guides

**Feature naming**:
- Format: `feature-N-short-name.md`
- Examples:
  - `feature-5-verdict-aggregation.md`
  - `feature-13-webhook-integration.md`

**ADR naming**:
- Format: `NNN-short-title.md` (zero-padded)
- Examples:
  - `001-fastapi-framework.md`
  - `025-caching-strategy.md`

**Phase naming**:
- Format: `phase_N/` directories
- Examples:
  - `phase_2/plan.md`
  - `phase_2/progress.md`

### Directory Naming

- Use plural for collections: `services/`, `features/`, `decisions/`
- Use singular for single-purpose: `database/`, `deployment/`, `development/`
- Use descriptive names: `quickstart/` not `qs/`

## Best Practices

### 1. Documentation Front Matter

Add metadata to important documents:

```markdown
---
title: Hybrid Search Service
category: service
tags: [search, ml, vector, embedding]
status: stable
owner: backend-team
last_updated: 2025-10-26
related_docs:
  - api/endpoints/ml.md
  - architecture/decisions/003-ml-service-integration.md
---

# Hybrid Search Service

[Content continues...]
```

### 2. Cross-Referencing

Always link related documentation:

```markdown
## Related Documentation
- [API Endpoints](../api/endpoints/ml.md) - ML API endpoints
- [Vector Search Service](vector_search.md) - Vector search implementation
- [Architecture Decision](../architecture/decisions/003-ml-service-integration.md) - ML integration ADR
- [Performance Tuning](../operations/performance_tuning.md) - Optimization guide
```

### 3. Code Examples

Include runnable examples:

```markdown
## Example: Create Claim

bash
# Create a new claim
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token_here" \
  -d '{
    "text": "The Earth orbits the Sun.",
    "source": "https://science.example.com/article",
    "context": "Astronomy fact"
  }'


**Expected response**:
json
{
  "id": "claim_abc123",
  "text": "The Earth orbits the Sun.",
  "status": "pending",
  "created_at": "2025-10-26T12:00:00Z",
  "verification_url": "/api/v1/claims/claim_abc123/verification"
}

```

### 4. Diagrams

Use Mermaid for architecture diagrams:

```markdown
## System Architecture

mermaid
graph TD
    A[Client] -->|HTTP| B[API Gateway]
    B -->|gRPC| C[Verification Service]
    B -->|REST| D[Search Service]
    C -->|Query| E[PostgreSQL]
    C -->|Publish| F[RabbitMQ]
    D -->|Vector Search| E
    G[ML Service] -->|Subscribe| F
    G -->|Embed| H[Model Cache]

```

### 5. Status Indicators

Use clear status indicators:

```markdown
## Status: Stable ✓

## Status: In Progress 🚧

## Status: Deprecated ⚠️

## Status: Experimental 🧪
```

## Tooling and Automation

### 1. Markdown Linting

Add to CI pipeline:

```bash
# .github/workflows/docs-lint.yml
name: Documentation Lint

on: [push, pull_request]

jobs:
  markdown-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Lint markdown files
        uses: articulate/actions-markdownlint@v1
        with:
          config: .markdownlint.json
          files: '**/*.md'
```

### 2. Link Checking

Check for broken links:

```bash
# Install markdown-link-check
npm install -g markdown-link-check

# Check all markdown files
find . -name "*.md" -exec markdown-link-check {} \;
```

### 3. Root Clutter Check

Add to Taskfile.yml:

```yaml
tasks:
  docs:check-root:
    desc: Check for markdown clutter in root
    cmds:
      - |
        ROOT_MD_COUNT=$(find . -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "CONTRIBUTING.md" -not -name "CHANGELOG.md" | wc -l)
        if [ $ROOT_MD_COUNT -gt 0 ]; then
          echo "ERROR: Found $ROOT_MD_COUNT markdown files in root (should be 3 max)"
          find . -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "CONTRIBUTING.md" -not -name "CHANGELOG.md"
          exit 1
        fi
        echo "✓ Root directory is clean"
```

### 4. Documentation Generation

Generate API documentation from OpenAPI spec:

```yaml
tasks:
  docs:generate-api:
    desc: Generate API documentation from OpenAPI spec
    cmds:
      - redocly build-docs openapi.yaml -o docs/api/generated.html
```

### 5. Weekly Review Reminder

Add to Taskfile.yml:

```yaml
tasks:
  docs:review:
    desc: Weekly documentation review checklist
    cmds:
      - |
        echo "📋 Weekly Documentation Review"
        echo ""
        echo "1. Review active features:"
        ls -1 planning/features/in_progress/
        echo ""
        echo "2. Move completed features to archive:"
        echo "   mv planning/features/in_progress/feature_X.md archive/completed_features/"
        echo ""
        echo "3. Update phase progress:"
        echo "   vim planning/phases/phase_N/progress.md"
        echo ""
        echo "4. Review technical debt:"
        echo "   cat planning/technical_debt/README.md"
```

## Maintenance Cadence

### Daily
- Update `planning/phases/phase_N/progress.md` with current progress
- Add blockers to `planning/phases/phase_N/blockers.md`

### Weekly
- Review `planning/features/in_progress/` - move completed to archive
- Update `planning/technical_debt/README.md`
- Check for root-level markdown clutter

### Monthly
- Review `docs/` for outdated documentation
- Update architecture diagrams
- Review and update ADRs if decisions changed

### Quarterly
- Comprehensive documentation audit
- Archive old roadmap versions
- Clean up deprecated documentation

## Migration Checklist

- [ ] Create directory structure (docs/, planning/, archive/)
- [ ] Create README.md indexes for each major directory
- [ ] Move permanent documentation to docs/
- [ ] Move active planning to planning/
- [ ] Move historical documentation to archive/
- [ ] Update root README.md with new structure
- [ ] Fix broken links across all documentation
- [ ] Update Taskfile.yml with new paths
- [ ] Add CI checks for documentation (linting, link checking, root clutter)
- [ ] Document the documentation process (meta!)
- [ ] Communicate new structure to team
- [ ] Archive this migration guide once complete

## Summary

This documentation organization system provides:

1. **Clear separation**: Permanent (docs/), active (planning/), historical (archive/)
2. **Backend focus**: API docs, ADRs, service docs, database docs
3. **Developer experience**: Easy navigation, clear naming, comprehensive indexes
4. **Scalability**: Grows gracefully without root-level clutter
5. **Workflow integration**: Supports feature lifecycle from planning to archive

The structure is designed specifically for backend projects with markdown-based project management, ensuring documentation remains organized, discoverable, and maintainable as the project scales.

## Next Steps

1. Review the proposed structure
2. Run the migration script (see DOCUMENTATION_MIGRATION_PLAN.md)
3. Update README.md to reference new structure
4. Add CI checks for documentation quality
5. Share with team and gather feedback
6. Iterate and refine based on usage

---

**Document Status**: Proposed
**Review Date**: TBD
**Owner**: Backend System Architect
