# Cloud-Ready Architectural Patterns (v1 Implementation)

This document contains the cloud-ready patterns to be inserted into phase_01_local_mvp.md.
These patterns should appear after the "Quick Start Commands" section and before "Simplified Event Flow".

## Cloud-Ready Architectural Patterns

Phase 1 incorporates proven cloud-native patterns that provide immediate local benefits while dramatically reducing migration effort for Phase 2. These patterns are not theoretical - they're practical implementations that make the local system better.

### 1. Repository/Adapter Pattern for Data Access

**Local Benefit**: Swap databases easily for testing (SQLite for unit tests, PostgreSQL for integration)
**Cloud Benefit**: Migrate from PostgreSQL to Aurora, DynamoDB, or other managed services with minimal code changes

**Implementation**:

```python
# core/repositories/base.py
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class ClaimRepository(ABC):
    """Abstract repository for claim storage"""

    @abstractmethod
    async def create(self, claim: Claim) -> Claim:
        pass

    @abstractmethod
    async def get_by_id(self, claim_id: UUID, tenant_id: str) -> Optional[Claim]:
        pass

    @abstractmethod
    async def list(self, tenant_id: str, limit: int = 100) -> List[Claim]:
        pass

# adapters/postgres_claim_repository.py
class PostgresClaimRepository(ClaimRepository):
    """PostgreSQL implementation (v1)"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def create(self, claim: Claim) -> Claim:
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO claims (id, tenant_id, text, submitted_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, claim.id, claim.tenant_id, claim.text, claim.submitted_at, claim.metadata)
        return claim

    async def get_by_id(self, claim_id: UUID, tenant_id: str) -> Optional[Claim]:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM claims
                WHERE id = $1 AND tenant_id = $2
            """, claim_id, tenant_id)
        return Claim.from_row(row) if row else None

# adapters/dynamodb_claim_repository.py (v2 - future)
class DynamoDBClaimRepository(ClaimRepository):
    """DynamoDB implementation for cloud deployment"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    async def create(self, claim: Claim) -> Claim:
        self.table.put_item(Item=claim.to_dynamodb_item())
        return claim

    async def get_by_id(self, claim_id: UUID, tenant_id: str) -> Optional[Claim]:
        response = self.table.get_item(
            Key={'tenant_id': tenant_id, 'id': str(claim_id)}
        )
        return Claim.from_dynamodb_item(response['Item']) if 'Item' in response else None

# Dependency injection - swap implementations via config
def get_claim_repository(config: AppConfig) -> ClaimRepository:
    if config.database_type == "postgres":
        return PostgresClaimRepository(db_pool)
    elif config.database_type == "dynamodb":
        return DynamoDBClaimRepository(table_name=config.table_name)
    else:
        raise ValueError(f"Unsupported database: {config.database_type}")
```

### 2. Event-Driven Architecture with CloudEvents

**Local Benefit**: Standardized event schemas make debugging easier and enable event replay
**Cloud Benefit**: CloudEvents work identically with Redis Streams (v1), SQS, EventBridge, or Kafka (v2)

**CloudEvents Schema**:

```python
# core/events/schemas.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

@dataclass
class CloudEvent:
    """CloudEvents 1.0 specification"""
    specversion: str = "1.0"
    id: str = None
    source: str = None
    type: str = None
    datacontenttype: str = "application/json"
    time: datetime = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.time:
            self.time = datetime.utcnow()

# Event type definitions
class ClaimSubmittedEvent(CloudEvent):
    def __init__(self, claim_id: UUID, claim_text: str, tenant_id: str):
        super().__init__(
            source="api-gateway",
            type="com.truthgraph.claim.submitted.v1",
            data={
                "claim_id": str(claim_id),
                "claim_text": claim_text,
                "tenant_id": tenant_id,
                "submitted_at": datetime.utcnow().isoformat()
            }
        )

class EvidenceRetrievedEvent(CloudEvent):
    def __init__(self, claim_id: UUID, evidence_ids: List[UUID], tenant_id: str):
        super().__init__(
            source="corpus-service",
            type="com.truthgraph.evidence.retrieved.v1",
            data={
                "claim_id": str(claim_id),
                "evidence_ids": [str(e) for e in evidence_ids],
                "tenant_id": tenant_id,
                "evidence_count": len(evidence_ids)
            }
        )

class VerdictReadyEvent(CloudEvent):
    def __init__(self, claim_id: UUID, verdict: str, confidence: float, tenant_id: str):
        super().__init__(
            source="verification-service",
            type="com.truthgraph.verdict.ready.v1",
            data={
                "claim_id": str(claim_id),
                "verdict": verdict,
                "confidence": confidence,
                "tenant_id": tenant_id
            }
        )
```

**Event Publisher Adapters**:

```python
# adapters/event_publisher.py
from abc import ABC, abstractmethod

class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: CloudEvent) -> None:
        pass

class RedisStreamPublisher(EventPublisher):
    """Redis Streams implementation (v1)"""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def publish(self, event: CloudEvent) -> None:
        stream_name = self._get_stream_name(event.type)
        await self.redis.xadd(
            stream_name,
            {
                'event_id': event.id,
                'event_type': event.type,
                'source': event.source,
                'data': json.dumps(event.data),
                'timestamp': event.time.isoformat()
            }
        )

    def _get_stream_name(self, event_type: str) -> str:
        # Map event types to stream names
        mapping = {
            "com.truthgraph.claim.submitted.v1": "claims-submitted",
            "com.truthgraph.evidence.retrieved.v1": "verification-pending",
            "com.truthgraph.verdict.ready.v1": "verdicts-ready"
        }
        return mapping.get(event_type, "default-stream")

class SQSEventPublisher(EventPublisher):
    """AWS SQS/EventBridge implementation (v2 - future)"""

    def __init__(self, queue_url: str):
        self.sqs = boto3.client('sqs')
        self.queue_url = queue_url

    async def publish(self, event: CloudEvent) -> None:
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps({
                'specversion': event.specversion,
                'id': event.id,
                'source': event.source,
                'type': event.type,
                'datacontenttype': event.datacontenttype,
                'time': event.time.isoformat(),
                'data': event.data
            })
        )
```

### 3. Observability from Day One

**Local Benefit**: Catch bugs faster with structured logs, trace performance bottlenecks, monitor service health
**Cloud Benefit**: Same observability stack works with CloudWatch, DataDog, or any OTLP-compatible backend

**Structured Logging with structlog**:

```python
# core/logging/config.py
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

def configure_logging(service_name: str, log_level: str = "INFO"):
    """Configure structured logging for all services"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(service_name=service_name)

# Usage in services
logger = configure_logging("api-gateway")

# Add context to all logs in a request
logger = logger.bind(
    request_id=request_id,
    tenant_id=tenant_id,
    claim_id=claim_id
)

logger.info("claim_submitted", claim_text=claim.text[:50])
logger.error("database_error", error=str(e), query=query)
```

**OpenTelemetry Tracing**:

```python
# core/observability/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def configure_tracing(service_name: str, otlp_endpoint: str):
    """Configure distributed tracing"""

    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Configure OTLP exporter (works with Jaeger, Prometheus, CloudWatch)
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Auto-instrument frameworks
    FastAPIInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()

    return trace.get_tracer(service_name)

# Usage
tracer = configure_tracing("verification-service", "http://prometheus:9090")

@tracer.start_as_current_span("verify_claim")
async def verify_claim(claim_id: UUID, evidence_ids: List[UUID]):
    span = trace.get_current_span()
    span.set_attribute("claim_id", str(claim_id))
    span.set_attribute("evidence_count", len(evidence_ids))

    # ... verification logic ...

    span.set_attribute("verdict", verdict.label)
    span.set_attribute("confidence", verdict.confidence)
```

**Prometheus Metrics**:

```python
# core/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
claims_submitted = Counter(
    'truthgraph_claims_submitted_total',
    'Total number of claims submitted',
    ['tenant_id', 'source']
)

verification_duration = Histogram(
    'truthgraph_verification_duration_seconds',
    'Time spent verifying claims',
    ['tenant_id', 'verdict'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

active_workers = Gauge(
    'truthgraph_active_workers',
    'Number of active worker processes',
    ['service_name']
)

# Usage in services
claims_submitted.labels(tenant_id="default", source="api").inc()

with verification_duration.labels(tenant_id="default", verdict="SUPPORTED").time():
    verdict = await verify_claim(claim, evidence)
```

### 4. Multi-Tenant Database Schema

**Local Benefit**: Test multi-tenant features without multiple databases, simulate production data patterns
**Cloud Benefit**: Zero schema changes needed when adding real tenants in v2

**Schema Design**:

```sql
-- All tables include tenant_id for data isolation
-- In v1: tenant_id is always 'default'
-- In v2: tenant_id maps to real customer/organization IDs

CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    text TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Composite index for tenant-scoped queries
CREATE INDEX idx_claims_tenant_submitted ON claims(tenant_id, submitted_at DESC);
CREATE INDEX idx_claims_tenant_id ON claims(tenant_id, id);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_evidence_tenant ON evidence(tenant_id);
CREATE INDEX idx_evidence_fts ON evidence USING gin(to_tsvector('english', content));

-- Multi-tenant evidence embeddings
CREATE TABLE evidence_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    evidence_id UUID REFERENCES evidence(id) ON DELETE CASCADE,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embeddings_tenant_vector ON evidence_embeddings(tenant_id)
    INCLUDE (embedding);
CREATE INDEX idx_embeddings_vector_similarity ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_verdicts_tenant_claim ON verdicts(tenant_id, claim_id);
CREATE INDEX idx_verdicts_tenant_created ON verdicts(tenant_id, created_at DESC);

-- Row-level security (enabled in v2, prepared in v1)
-- ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation ON claims
--   USING (tenant_id = current_setting('app.current_tenant')::text);
```

**Application-Level Tenant Isolation**:

```python
# core/models/base.py
from uuid import uuid4

class TenantScopedModel:
    """Base model for all tenant-scoped entities"""

    def __init__(self, tenant_id: str = "default"):
        self.id = uuid4()
        self.tenant_id = tenant_id  # Always "default" in v1

    @classmethod
    def get_tenant_id(cls, request: Request) -> str:
        """Extract tenant ID from request context

        v1: Always returns 'default'
        v2: Extract from JWT token, subdomain, or API key
        """
        # v1 implementation
        return "default"

        # v2 implementation (future)
        # tenant_id = request.state.tenant_id  # Set by auth middleware
        # return tenant_id

# All queries must be tenant-scoped
async def get_claim(claim_id: UUID, tenant_id: str) -> Optional[Claim]:
    """Never query without tenant_id - prevents data leakage"""
    query = """
        SELECT * FROM claims
        WHERE id = $1 AND tenant_id = $2
    """
    row = await db.fetchrow(query, claim_id, tenant_id)
    return Claim.from_row(row) if row else None
```

### 5. Configuration Management with Adapters

**Local Benefit**: Environment-specific configs without code changes, easier testing
**Cloud Benefit**: Swap environment variables for AWS Secrets Manager, Parameter Store, or Vault

**Configuration Abstraction**:

```python
# core/config/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class ConfigProvider(ABC):
    """Abstract configuration provider"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def get_secret(self, key: str) -> str:
        pass

class EnvConfigProvider(ConfigProvider):
    """Environment variables (v1)"""

    def get(self, key: str, default: Any = None) -> Any:
        return os.getenv(key, default)

    def get_secret(self, key: str) -> str:
        # In v1, secrets are just env vars
        secret = os.getenv(key)
        if not secret:
            raise ValueError(f"Secret {key} not found")
        return secret

class AWSSecretsManagerProvider(ConfigProvider):
    """AWS Secrets Manager (v2 - future)"""

    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self.ssm_client = boto3.client('ssm')
        self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        # Get from Parameter Store
        try:
            response = self.ssm_client.get_parameter(Name=key)
            return response['Parameter']['Value']
        except ClientError:
            return default

    def get_secret(self, key: str) -> str:
        # Get from Secrets Manager with caching
        if key in self._cache:
            return self._cache[key]

        response = self.secrets_client.get_secret_value(SecretId=key)
        secret = json.loads(response['SecretString'])
        self._cache[key] = secret
        return secret

# Application config
class AppConfig:
    def __init__(self, provider: ConfigProvider):
        self.provider = provider

    @property
    def database_url(self) -> str:
        return self.provider.get_secret("DATABASE_URL")

    @property
    def redis_url(self) -> str:
        return self.provider.get("REDIS_URL", "redis://localhost:6379")

    @property
    def log_level(self) -> str:
        return self.provider.get("LOG_LEVEL", "INFO")

# Dependency injection
def get_config() -> AppConfig:
    if os.getenv("ENV") == "production":
        provider = AWSSecretsManagerProvider()
    else:
        provider = EnvConfigProvider()

    return AppConfig(provider)
```

### Pattern Benefits Summary

| Pattern | Local Benefit | Cloud Migration Reduction |
|---------|--------------|---------------------------|
| Repository/Adapter | Easy test mocking, swap DBs | 70% - just swap repository implementation |
| CloudEvents | Standardized debugging, event replay | 80% - same events work with SQS/EventBridge |
| Observability | Find bugs faster, performance insights | 90% - same logs/traces in CloudWatch |
| Multi-Tenant Schema | Test tenant features locally | 95% - zero schema changes needed |
| Config Adapters | Environment-specific configs | 85% - swap config provider only |

### Overall Migration Effort Reduction: 50-70%

The patterns above mean migrating to cloud in v2 primarily involves:

1. Swapping adapter implementations (database, events, config)
2. Deploying to ECS/Lambda instead of Docker Compose
3. Updating infrastructure-as-code (Terraform/CDK)

**No changes needed to**:

- Core business logic
- Event schemas
- Database schemas
- API contracts
- Service boundaries
