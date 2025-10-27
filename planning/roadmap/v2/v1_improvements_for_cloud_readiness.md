# V1 Improvements for Cloud Readiness

**Purpose**: Architectural refinements to v1 that will ease the transition to v2 cloud deployment

**Status**: Recommendations
**Last Updated**: 2025-10-22

---

## Overview

By making strategic architectural decisions in v1, we can significantly reduce the complexity and risk of migrating to v2 cloud. This document identifies "cloud-ready" patterns that work well locally but translate directly to cloud services.

**Principle**: Design v1 with abstractions that don't assume "local" - then cloud becomes a configuration change, not a rewrite.

---

## 1. Component Separation & Modularity

### Current v1 Plan Issues

- FastAPI monolith combining API, workers, and business logic
- Tight coupling between retrieval, reasoning, and storage
- Direct database access throughout the codebase

### Recommended Changes

#### 1.1 Service Boundaries from Day One

```text
Separate v1 into distinct services (still Docker Compose, but isolated):

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  API Gateway    │  │  Verification   │  │  Corpus         │
│  (FastAPI)      │  │  Service        │  │  Service        │
│  - Auth stub    │  │  - Claim parse  │  │  - Ingest       │
│  - Routing      │  │  - NLI verify   │  │  - Embed        │
│  - Validation   │  │  - Reasoning    │  │  - Search       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                     │
         └────────────────────┴─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Shared Data Layer│
                    │  (Abstracted)     │
                    └───────────────────┘
```

**Benefits**:

- Each service can scale independently in v2
- Clear API contracts between services
- Easier to replace components (e.g., swap search service)
- Can test services in isolation

**Implementation**:

- Use separate FastAPI apps in different containers
- Define service-to-service communication via HTTP/REST (not direct function calls)
- Add service discovery (even if just via Docker DNS in v1)

#### 1.2 Repository Structure

```text
truthgraph/
├── services/
│   ├── api/              # API Gateway service
│   ├── verification/     # Claim verification service
│   ├── corpus/           # Corpus management & search
│   ├── reasoning/        # Multi-hop reasoning engine
│   └── worker/           # Async background jobs
├── shared/               # Shared libraries
│   ├── models/           # Pydantic data models
│   ├── database/         # DB abstractions
│   ├── events/           # Event schemas
│   └── config/           # Shared configuration
├── infrastructure/
│   ├── docker/           # Docker Compose files
│   ├── kubernetes/       # K8s manifests (prepared, not used)
│   └── terraform/        # IaC (prepared, not used)
```

**Benefits**:

- Clear ownership boundaries
- Kubernetes manifests ready to go for v2
- Shared code is explicitly shared, not accidentally coupled

---

## 2. Data Layer Abstraction

### Current v1 Plan Issues - Data Layer Abstraction

- Direct SQLAlchemy imports throughout codebase
- Hardcoded FAISS file paths
- Redis commands scattered in business logic

### Recommended Changes - Data Layer Abstraction

#### 2.1 Repository Pattern with Adapters

```python
# shared/database/repositories.py
class ClaimRepository(ABC):
    @abstractmethod
    async def get(self, claim_id: str) -> Claim: ...

    @abstractmethod
    async def save(self, claim: Claim) -> str: ...

    @abstractmethod
    async def search(self, query: str) -> List[Claim]: ...

# Implementation for v1
class PostgresClaimRepository(ClaimRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, claim_id: str) -> Claim:
        # SQLAlchemy implementation
        ...

# Future v2 implementation (drop-in replacement)
class DynamoDBClaimRepository(ClaimRepository):
    def __init__(self, table_name: str, region: str):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

    async def get(self, claim_id: str) -> Claim:
        # DynamoDB implementation
        ...
```

**Benefits**:

- Swap PostgreSQL for RDS, Aurora, or even DynamoDB without changing business logic
- Easy to mock for testing
- Can add caching layer transparently

#### 2.2 Vector Store Abstraction

```python
# shared/retrieval/vector_store.py
class VectorStore(ABC):
    @abstractmethod
    async def index(self, embeddings: List[np.ndarray], metadata: List[Dict]) -> None: ...

    @abstractmethod
    async def search(self, query_embedding: np.ndarray, k: int) -> List[SearchResult]: ...

# v1: FAISS implementation
class FAISSVectorStore(VectorStore): ...

# v2: Pinecone implementation (same interface)
class PineconeVectorStore(VectorStore): ...

# v2: Weaviate implementation
class WeaviateVectorStore(VectorStore): ...
```

**Benefits**:

- Can A/B test FAISS vs Pinecone vs Weaviate with config change
- Local development stays fast (FAISS)
- Production can use managed service

#### 2.3 Configuration-Based Adapter Selection

```python
# shared/config/settings.py
class Settings(BaseSettings):
    # Adapter selection
    claim_repository: Literal["postgres", "dynamodb"] = "postgres"
    vector_store: Literal["faiss", "pinecone", "weaviate"] = "faiss"
    queue: Literal["redis", "sqs", "rabbitmq"] = "redis"

    # Connection details
    postgres_url: str = "postgresql://..."
    redis_url: str = "redis://..."

    # Cloud-specific (unused in v1)
    aws_region: Optional[str] = None
    pinecone_api_key: Optional[str] = None

# Dependency injection
def get_claim_repository(settings: Settings) -> ClaimRepository:
    if settings.claim_repository == "postgres":
        return PostgresClaimRepository(get_db_session())
    elif settings.claim_repository == "dynamodb":
        return DynamoDBClaimRepository(settings.dynamodb_table, settings.aws_region)
```

**Benefits**:

- Same codebase runs locally or in cloud
- Can test cloud adapters locally with emulators (LocalStack)
- Feature flags for gradual migration

---

## 3. Event-Driven Architecture

### Current v1 Plan Issues - Event-Driven Architecture

- Direct service-to-service calls (tight coupling)
- Redis Streams used, but without formal event schemas
- Difficult to add event sourcing or audit trail later

### Recommended Changes - Event-Driven Architecture

#### 3.1 Define Event Schemas (CloudEvents Standard)

```python
# shared/events/schemas.py
from cloudevents.http import CloudEvent

class ClaimSubmitted(BaseModel):
    claim_id: str
    text: str
    source: str
    submitted_at: datetime
    tenant_id: Optional[str] = None  # For v2 multi-tenancy

class EvidenceRetrieved(BaseModel):
    claim_id: str
    evidence_ids: List[str]
    retrieval_method: str
    confidence_scores: List[float]

# Event bus abstraction
class EventBus(ABC):
    @abstractmethod
    async def publish(self, event_type: str, data: BaseModel) -> None: ...

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable) -> None: ...
```

**Benefits**:

- CloudEvents is cloud-agnostic (works with SQS, Pub/Sub, EventBridge, Kafka)
- Events become first-class API contracts
- Easy to add event replay, debugging, audit logs

#### 3.2 Event Bus Adapter Pattern

```python
# v1: Redis Streams
class RedisEventBus(EventBus):
    async def publish(self, event_type: str, data: BaseModel):
        await self.redis.xadd(
            f"events:{event_type}",
            {"data": data.model_dump_json()}
        )

# v2: AWS EventBridge
class EventBridgeEventBus(EventBus):
    async def publish(self, event_type: str, data: BaseModel):
        await self.eventbridge.put_events(
            Entries=[{
                'Source': 'truthgraph',
                'DetailType': event_type,
                'Detail': data.model_dump_json()
            }]
        )
```

**Benefits**:

- Change queue technology without rewriting business logic
- Can record all events for replay (event sourcing)
- Enables CQRS pattern in v2

#### 3.3 Async Workers from Day One

```python
# Don't do this (synchronous):
@app.post("/claims")
async def create_claim(claim: ClaimCreate):
    claim_id = await save_claim(claim)
    evidence = await retrieve_evidence(claim_id)  # Blocks API response
    verdict = await verify_claim(claim_id, evidence)  # Blocks API response
    return {"claim_id": claim_id, "verdict": verdict}

# Do this (async from start):
@app.post("/claims")
async def create_claim(claim: ClaimCreate):
    claim_id = await save_claim(claim)
    await event_bus.publish("ClaimSubmitted", ClaimSubmitted(claim_id=claim_id, ...))
    return {"claim_id": claim_id, "status": "processing"}

# Worker picks up event
async def handle_claim_submitted(event: ClaimSubmitted):
    evidence = await retrieve_evidence(event.claim_id)
    await event_bus.publish("EvidenceRetrieved", EvidenceRetrieved(...))

async def handle_evidence_retrieved(event: EvidenceRetrieved):
    verdict = await verify_claim(event.claim_id, event.evidence_ids)
    await event_bus.publish("VerificationComplete", VerificationComplete(...))
```

**Benefits**:

- API stays responsive even with slow operations
- Workers can scale independently in v2
- Can add retries, dead-letter queues easily

---

## 4. Configuration Management

### Current v1 Plan Issues - Configuration Management

- `.env` files with hardcoded values
- No separation of config from secrets
- Environment-specific config scattered across files

### Recommended Changes - Configuration Management

#### 4.1 Hierarchical Configuration

```python
# shared/config/settings.py
class Settings(BaseSettings):
    # Environment
    env: Literal["local", "dev", "staging", "prod"] = "local"

    # Feature flags (for gradual v2 migration)
    use_cloud_storage: bool = False
    use_managed_vector_db: bool = False
    enable_multi_tenancy: bool = False

    # Observability
    log_level: str = "INFO"
    enable_tracing: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Load environment-specific overrides
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
                YamlConfigSettingsSource(settings_cls=cls),  # config/local.yaml
            )
```

#### 4.2 Secrets Management Abstraction

```python
# shared/config/secrets.py
class SecretsManager(ABC):
    @abstractmethod
    async def get_secret(self, key: str) -> str: ...

# v1: Environment variables
class EnvSecretsManager(SecretsManager):
    async def get_secret(self, key: str) -> str:
        return os.getenv(key)

# v2: AWS Secrets Manager
class AWSSecretsManager(SecretsManager):
    async def get_secret(self, key: str) -> str:
        response = await self.client.get_secret_value(SecretId=key)
        return response['SecretString']

# Usage
db_password = await secrets_manager.get_secret("DB_PASSWORD")
```

**Benefits**:

- Same code works with .env (v1) or Secrets Manager (v2)
- Can rotate secrets without code changes
- Audit secret access

---

## 5. Observability from Day One

### Current v1 Plan Issues - Observability from Day One

- Basic logging without structure
- Metrics added in Phase 4 (too late)
- No correlation IDs for tracing

### Recommended Changes - Observability from Day One

#### 5.1 Structured Logging + Correlation IDs

```python
# shared/observability/logging.py
import structlog

logger = structlog.get_logger()

# Every request gets a correlation ID
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# All logs include correlation ID automatically
logger.info("claim_submitted", claim_id=claim_id, user_id=user_id)
# Output: {"event": "claim_submitted", "claim_id": "...", "correlation_id": "...", "timestamp": "..."}
```

**Benefits**:

- Logs are machine-readable (easy to send to CloudWatch, Datadog)
- Can trace requests across services
- Works locally (stdout) or cloud (log aggregation)

#### 5.2 OpenTelemetry from Start

```python
# shared/observability/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

def setup_tracing(settings: Settings):
    provider = TracerProvider()

    if settings.env == "local":
        # Console output for local dev
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # Send to Jaeger, Datadog, AWS X-Ray, etc.
        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        ))

    trace.set_tracer_provider(provider)

# Usage
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("verify_claim")
async def verify_claim(claim_id: str):
    span = trace.get_current_span()
    span.set_attribute("claim_id", claim_id)
    # ... business logic
```

**Benefits**:

- Distributed tracing works day one (critical for debugging)
- Same instrumentation works with any backend (Jaeger, X-Ray, Datadog)
- Performance bottlenecks visible immediately

#### 5.3 Prometheus Metrics with Standard Labels

```python
# shared/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Use labels for future multi-tenancy
claims_submitted = Counter(
    'claims_submitted_total',
    'Total claims submitted',
    ['tenant_id', 'source']  # tenant_id = "default" in v1
)

verification_duration = Histogram(
    'verification_duration_seconds',
    'Time to verify claim',
    ['verdict', 'claim_type']
)

# Usage
claims_submitted.labels(tenant_id=tenant_id, source="api").inc()
with verification_duration.labels(verdict="supported").time():
    result = await verify_claim(claim_id)
```

**Benefits**:

- Metrics are multi-tenant ready (just use "default" in v1)
- Can split metrics by customer in v2 without code changes
- Standard Prometheus format works with Grafana, Datadog, CloudWatch

---

## 6. API Design for Evolution

### Current v1 Plan Issues - API Design for Evolution

- No API versioning strategy
- REST API without forward compatibility
- No pagination, filtering, or expansion patterns

### Recommended Changes - API Design for Evolution

#### 6.1 API Versioning from Day One

```python
# Version in URL
@app.post("/api/v1/claims")
async def create_claim_v1(claim: ClaimCreateV1):
    ...

# Can add v2 later without breaking v1 clients
@app.post("/api/v2/claims")
async def create_claim_v2(claim: ClaimCreateV2):
    ...

# Or use header-based versioning
@app.post("/claims")
async def create_claim(
    claim: ClaimCreate,
    api_version: str = Header(default="v1", alias="X-API-Version")
):
    if api_version == "v1":
        return await create_claim_v1(claim)
    elif api_version == "v2":
        return await create_claim_v2(claim)
```

#### 6.2 Pagination, Filtering, Sorting (RFC 7233)

```python
@app.get("/api/v1/claims")
async def list_claims(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Optional[str] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = "desc",
    filter: Optional[str] = Query(default=None),  # JSON filter expression
):
    # Return with pagination metadata
    return {
        "data": claims,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total_count,
            "has_more": offset + limit < total_count
        }
    }
```

#### 6.3 Expand/Include Pattern (Sparse Fieldsets)

```python
@app.get("/api/v1/claims/{claim_id}")
async def get_claim(
    claim_id: str,
    expand: List[str] = Query(default=[]),  # ?expand=evidence,reasoning_chain
):
    claim = await claim_repo.get(claim_id)

    response = claim.dict()

    if "evidence" in expand:
        response["evidence"] = await evidence_repo.get_by_claim(claim_id)

    if "reasoning_chain" in expand:
        response["reasoning_chain"] = await reasoning_repo.get_chain(claim_id)

    return response
```

**Benefits**:

- Reduces over-fetching (important when services are remote in v2)
- Clients can opt-in to expensive data
- Supports GraphQL-like flexibility without GraphQL complexity

---

## 7. Multi-Tenancy Preparation

### Current v1 Plan Issues - Multi-Tenancy Preparation

- Single-user assumption throughout
- No tenant isolation in database schema
- No resource quotas or rate limiting

### Recommended Changes - Multi-Tenancy Preparation

#### 7.1 Tenant-Aware Data Models (Even for Single Tenant)

```python
# shared/models/claim.py
class Claim(BaseModel):
    id: str
    tenant_id: str = "default"  # Always "default" in v1, real IDs in v2
    text: str
    created_at: datetime
    created_by: Optional[str] = None  # Null in v1, user_id in v2

# Database schema
CREATE TABLE claims (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR(255),

    -- Indexes ready for multi-tenancy
    INDEX idx_tenant_created (tenant_id, created_at)
);

# All queries include tenant filter
async def get_claims(tenant_id: str = "default"):
    return await db.execute(
        select(Claim).where(Claim.tenant_id == tenant_id)
    )
```

**Benefits**:

- Zero code changes needed for multi-tenancy in v2
- Can test multi-tenant logic locally (create test tenants)
- Database already optimized for tenant queries

#### 7.2 Resource Quotas and Rate Limiting

```python
# shared/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=lambda: get_tenant_id() or get_remote_address())

@app.post("/api/v1/claims")
@limiter.limit("100/hour")  # Per tenant in v2, per IP in v1
async def create_claim(claim: ClaimCreate):
    ...

# Quota enforcement
async def check_quota(tenant_id: str, resource: str):
    quota = await quota_service.get_quota(tenant_id, resource)
    usage = await quota_service.get_usage(tenant_id, resource)
    if usage >= quota.limit:
        raise HTTPException(429, "Quota exceeded")
```

**Benefits**:

- Rate limiting works day one (important for public v1 demos)
- Easy to add per-tenant quotas in v2
- Prevents abuse in both v1 and v2

---

## 8. Testing Strategy for Cloud Migration

### Recommended Changes - Testing Strategy for Cloud Migration

#### 8.1 Contract Testing Between Services - Testing Strategy for Cloud Migration

```python
# tests/contracts/test_verification_service.py
import pact

def test_verification_service_contract():
    """API Gateway expects Verification Service to accept this format"""
    pact.given("a valid claim") \
        .upon_receiving("a verification request") \
        .with_request(method="POST", path="/verify", body={"claim_id": "..."}) \
        .will_respond_with(200, body={"verdict": "supported", "confidence": 0.9})
```

**Benefits**:

- Ensures services can be deployed independently in v2
- Catches breaking changes before production
- Works with local or remote services

#### 8.2 Cloud Adapter Integration Tests

```python
# tests/integration/test_adapters.py
@pytest.mark.parametrize("vector_store", ["faiss", "pinecone"])
async def test_vector_store_search(vector_store):
    """Same test runs against FAISS (local) and Pinecone (cloud)"""
    store = get_vector_store(vector_store)

    await store.index([embedding1, embedding2], [meta1, meta2])
    results = await store.search(query_embedding, k=2)

    assert len(results) == 2
    assert results[0].score > results[1].score
```

**Benefits**:

- Can test cloud services locally with emulators
- Confidence that cloud migration won't break functionality
- Easy A/B testing of different vector stores

---

## 9. Tool Stack Adjustments

### Recommended Changes - Tool Stack Adjustments

#### 9.1 Use Cloud-Agnostic Tools When Possible

| Category | v1 (Original) | v1 (Cloud-Ready) | v2 (Cloud) |
|----------|---------------|------------------|------------|
| **Logging** | Python logging | structlog + OpenTelemetry | Same (send to CloudWatch) |
| **Metrics** | Prometheus | Prometheus + OTLP exporter | Same (send to Datadog/CloudWatch) |
| **Tracing** | None → Jaeger (Phase 4) | OpenTelemetry from start | Same (send to X-Ray/Datadog) |
| **Queue** | Redis Streams | Redis with CloudEvents schema | SQS/EventBridge (same interface) |
| **Secrets** | .env files | Adapter pattern (env → Secrets Manager) | AWS Secrets Manager |
| **Config** | .env only | Pydantic Settings + YAML | Same + AWS AppConfig |

#### 9.2 Add Cloud Emulators to Dev Stack

```yaml
# docker-compose.dev.yaml
services:
  localstack:  # Emulates AWS services (S3, SQS, DynamoDB, Secrets Manager)
    image: localstack/localstack
    environment:
      SERVICES: s3,sqs,dynamodb,secretsmanager

  azurite:  # Emulates Azure Blob Storage
    image: mcr.microsoft.com/azure-storage/azurite

  fake-gcs-server:  # Emulates Google Cloud Storage
    image: fsouza/fake-gcs-server
```

**Benefits**:

- Test cloud code paths without cloud accounts
- CI/CD can test cloud adapters
- Faster iteration (no network latency)

---

## 10. Database Schema Design

### Recommended Changes - Database Schema Design

#### 10.1 Cloud-Optimized Schema Patterns - Database Schema Design

```sql
-- Use UUIDs for primary keys (better for distributed systems)
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    ...
);

-- Composite indexes for common query patterns
CREATE INDEX idx_tenant_status_created ON claims(tenant_id, status, created_at DESC);

-- Partition-ready tables (for future sharding)
CREATE TABLE evidence (
    id UUID PRIMARY KEY,
    claim_id UUID NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    ...
) PARTITION BY RANGE (created_at);  -- Can partition by month

-- JSON columns for flexible schemas (avoid ALTER TABLE in production)
ALTER TABLE claims ADD COLUMN metadata JSONB;
CREATE INDEX idx_claims_metadata_gin ON claims USING GIN(metadata);
```

**Benefits**:

- UUIDs prevent ID conflicts when merging databases
- Partitioning reduces index size as data grows
- JSONB avoids schema migrations for optional fields

#### 10.2 Migration Strategy for Schema Changes

```python
# Use Alembic from day one
# alembic/versions/001_initial_schema.py
def upgrade():
    op.create_table('claims', ...)
    op.create_index('idx_tenant_created', 'claims', ['tenant_id', 'created_at'])

def downgrade():
    op.drop_index('idx_tenant_created')
    op.drop_table('claims')
```

**Benefits**:

- Database changes are versioned and reversible
- Can deploy schema changes independently of code
- Works with RDS, Aurora, Cloud SQL

---

## 11. Frontend Architecture

### Recommended Changes - Frontend Architecture

#### 11.1 Backend-for-Frontend (BFF) Pattern

```text
┌─────────────┐
│   React     │
│   Frontend  │
└──────┬──────┘
       │
       │ REST/GraphQL
       ▼
┌─────────────┐
│  BFF API    │  ← Tailored for frontend needs
│  (Next.js   │     (pagination, aggregation, etc.)
│   API routes)│
└──────┬──────┘
       │
       │ Internal APIs
       ▼
┌─────────────────────────────────┐
│  Microservices                  │
│  (Verification, Corpus, etc.)   │
└─────────────────────────────────┘
```

**Benefits**:

- Frontend doesn't need to know about microservices
- Can cache/aggregate at BFF layer
- Easy to add GraphQL without changing backend services

#### 11.2 API Client with Retry/Circuit Breaker

```typescript
// frontend/src/api/client.ts
import axios from 'axios';
import axiosRetry from 'axios-retry';

const apiClient = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

// Retry transient failures
axiosRetry(apiClient, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) => {
    return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
           error.response?.status === 429; // Rate limited
  },
});
```

**Benefits**:

- Resilient to network issues (important in cloud with distributed services)
- Handles rate limiting gracefully
- Works locally or with remote API

---

## Summary: Priority Changes for v1

### High Priority (Do in Phase 1)

1. **Service separation** - Even if small, split API/Worker/Corpus from day one
2. **Repository pattern** - Abstract database access
3. **Structured logging** - Use structlog with correlation IDs
4. **Tenant-aware schema** - Add `tenant_id` to all tables (default to "default")
5. **API versioning** - Use `/api/v1/` prefix
6. **Event schemas** - Use CloudEvents for all async work

### Medium Priority (Do in Phase 2-3)

1. **Vector store abstraction** - Interface for FAISS/Pinecone/Weaviate
2. **OpenTelemetry tracing** - Add distributed tracing early
3. **Configuration hierarchy** - Pydantic Settings with YAML overrides
4. **Rate limiting** - Add slowapi middleware
5. **Contract tests** - Test service-to-service contracts

### Low Priority (Can defer to Phase 4 or v2)

1. **Cloud emulators** - LocalStack for testing cloud code paths
2. **BFF pattern** - Can add when frontend complexity grows
3. **Database partitioning** - Only needed at scale

---

## Migration Checklist

When implementing v1 with these changes, verify:

- [ ] Can run all tests with `VECTOR_STORE=faiss` and `VECTOR_STORE=pinecone` (with emulator)
- [ ] Can switch from PostgreSQL to DynamoDB (with LocalStack) via config change
- [ ] All logs include correlation IDs and are JSON-formatted
- [ ] API has `/api/v1/` prefix and versioning strategy documented
- [ ] Services communicate via events, not direct function calls
- [ ] Database schema includes `tenant_id` column on all tables
- [ ] Metrics have `tenant_id` label (always "default" in v1)
- [ ] Secrets are loaded via abstraction (env vars → Secrets Manager later)
- [ ] Distributed tracing works across services (view in Jaeger UI)
- [ ] Can deploy each service independently (even if not needed in v1)

---

## Expected ROI

By implementing these patterns in v1:

- **50-70% reduction** in v2 migration effort (no rewrites, just config changes)
- **Zero downtime migration** possible (run v1 and v2 side-by-side with feature flags)
- **Earlier bug detection** (cloud-like testing in v1)
- **Better developer experience** (clearer boundaries, better observability)

**Cost**: ~20% more upfront effort in v1 (abstractions, extra containers, tracing setup)
**Benefit**: 3x faster v2 development + higher quality + easier debugging

---

## References

- [The Twelve-Factor App](https://12factor.net/) - Cloud-native design principles
- [CloudEvents Specification](https://cloudevents.io/) - Event format standard
- [OpenTelemetry](https://opentelemetry.io/) - Observability standard
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Data access abstraction
- [Contract Testing with Pact](https://docs.pact.io/) - Microservice testing

---

**Next Steps**:

1. Review these recommendations with v1 architecture decisions
2. Update Phase 1 plan to include service separation and repository pattern
3. Add observability setup to Phase 1 (not Phase 4)
4. Create adapter interfaces for database, vector store, queue in shared library
