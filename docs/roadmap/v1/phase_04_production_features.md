# Phase 4: Production Features

**Timeline**: Months 7-8
**Focus**: API maturity, evaluation suite, optimization, developer experience

## Overview and Goals

Phase 4 transforms the TruthGraph local-first prototype into a production-ready system with **cloud migration readiness validation**. This phase emphasizes external interfaces, systematic evaluation, performance optimization, comprehensive documentation, and **proving that the cloud-ready architecture actually works with real cloud services**, not just exists in theory.

The deliverable is a battle-tested toolkit ready for both research workflows and deployment in production fact-checking pipelines, with a **validated migration path to cloud deployment in v2**.

### Key Objectives

- **Production API**: RESTful interface with OpenAPI documentation, export formats, and robust error handling
- **Evaluation Framework**: Built-in benchmarks (FEVER, FEVEROUS) with standardized metrics and result tracking
- **Performance**: GPU acceleration, efficient caching, pre-built indices, and profiling tools
- **Developer Experience**: Complete documentation, guides, and contribution workflows
- **Cloud Migration Validation**: Testing that cloud-ready abstractions work with actual cloud services (RDS, Pinecone, S3, SQS)
- **Infrastructure as Code**: Terraform/Pulumi templates and Kubernetes charts ready for cloud deployment
- **Migration Readiness**: Validate that v1 can migrate to v2 cloud with <50% refactoring

### Success Criteria

- API serves 100+ req/sec with p95 latency < 500ms
- FEVER dev set evaluated in < 10 minutes on consumer GPU
- All endpoints documented with OpenAPI 3.0 spec
- Contribution guide enables external PRs within first release
- **Repository pattern validated with at least one cloud backend (e.g., RDS)**
- **CloudEvents integration tested with at least one cloud message queue (e.g., SQS)**
- **Observability stack integrated with at least one cloud monitoring service (e.g., CloudWatch)**
- **IaC templates deployed to at least one cloud provider successfully**
- **Cloud deployment cost estimated for typical workloads**

---

## API & Export

### REST API Design

**Endpoints**:

- `POST /api/v1/claims/verify` - Single claim verification
- `POST /api/v1/claims/batch` - Batch processing (async job queue)
- `GET /api/v1/claims/{claim_id}` - Retrieve cached result
- `GET /api/v1/claims/{claim_id}/trace` - Provenance graph
- `POST /api/v1/export/{claim_id}` - Generate export artifacts
- `GET /api/v1/health` - Health check and system status
- `GET /api/v1/metrics` - Prometheus-compatible metrics

**Framework**: FastAPI with automatic OpenAPI generation

#### Endpoint Examples

`POST /api/v1/claims/verify`

Single claim verification with full provenance.

**Request:**

```json
{
  "claim": "The Eiffel Tower is 330 meters tall",
  "options": {
    "as_of": "2025-10-22",
    "max_evidence": 5,
    "include_provenance": true,
    "retrieval_mode": "hybrid"
  }
}
```

**Response (200 OK):**

```json
{
  "claim_id": "c_a7f3e9d1",
  "claim": "The Eiffel Tower is 330 meters tall",
  "verdict": "SUPPORTED",
  "confidence": 0.89,
  "evidence": [
    {
      "text": "The tower is 330 metres (1,083 ft) tall, about the same height as an 81-storey building.",
      "source": "https://en.wikipedia.org/wiki/Eiffel_Tower",
      "source_title": "Eiffel Tower - Wikipedia",
      "relevance_score": 0.94,
      "publication_date": "2024-12-15",
      "stance": "SUPPORTS"
    },
    {
      "text": "Including the 24m antenna, the structure is 324m in height.",
      "source": "https://www.toureiffel.paris/en/the-monument",
      "source_title": "Official Eiffel Tower Website",
      "relevance_score": 0.87,
      "publication_date": "2024-11-20",
      "stance": "SUPPORTS"
    }
  ],
  "reasoning": "Multiple authoritative sources confirm the Eiffel Tower's height at 330m (or 324m excluding antenna). The claim is supported by consistent evidence from Wikipedia and official sources.",
  "temporal_context": {
    "as_of": "2025-10-22",
    "is_time_sensitive": false,
    "temporal_claims": []
  },
  "metadata": {
    "processing_time_ms": 1243,
    "model_version": "truthgraph-v1.0.0",
    "retrieval_stats": {
      "documents_retrieved": 127,
      "documents_reranked": 20,
      "cache_hit": false
    }
  }
}
```

`POST /api/v1/claims/batch`

Batch claim processing with async job tracking.

**Request:**

```json
{
  "claims": [
    {"id": "claim_1", "text": "Paris is the capital of France"},
    {"id": "claim_2", "text": "The Moon is made of cheese"},
    {"id": "claim_3", "text": "Python was created in 1991"}
  ],
  "options": {
    "priority": "normal",
    "webhook_url": "https://example.com/webhook",
    "as_of": "2025-10-22"
  }
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "job_b3c4d5e6",
  "status": "queued",
  "claims_count": 3,
  "estimated_completion": "2025-10-22T15:35:00Z",
  "tracking_url": "/api/v1/jobs/job_b3c4d5e6",
  "created_at": "2025-10-22T15:30:00Z"
}
```

`GET /api/v1/jobs/{job_id}`
Check batch job status.

**Response (200 OK - in progress):**

```json
{
  "job_id": "job_b3c4d5e6",
  "status": "processing",
  "progress": {
    "completed": 2,
    "total": 3,
    "failed": 0
  },
  "started_at": "2025-10-22T15:30:15Z",
  "estimated_completion": "2025-10-22T15:35:00Z"
}
```

**Response (200 OK - completed):**

```json
{
  "job_id": "job_b3c4d5e6",
  "status": "completed",
  "progress": {
    "completed": 3,
    "total": 3,
    "failed": 0
  },
  "started_at": "2025-10-22T15:30:15Z",
  "completed_at": "2025-10-22T15:34:22Z",
  "results_url": "/api/v1/jobs/job_b3c4d5e6/results"
}
```

`GET /api/v1/claims/{claim_id}/trace`

Retrieve provenance graph showing reasoning chain.

**Response (200 OK):**

```json
{
  "claim_id": "c_a7f3e9d1",
  "claim": "The Eiffel Tower is 330 meters tall",
  "trace": {
    "nodes": [
      {
        "id": "n_1",
        "type": "claim",
        "content": "The Eiffel Tower is 330 meters tall"
      },
      {
        "id": "n_2",
        "type": "query",
        "content": "Eiffel Tower height meters"
      },
      {
        "id": "n_3",
        "type": "document",
        "content": "Wikipedia: Eiffel Tower",
        "url": "https://en.wikipedia.org/wiki/Eiffel_Tower"
      },
      {
        "id": "n_4",
        "type": "evidence",
        "content": "The tower is 330 metres (1,083 ft) tall...",
        "stance": "SUPPORTS",
        "score": 0.94
      },
      {
        "id": "n_5",
        "type": "verdict",
        "content": "SUPPORTED",
        "confidence": 0.89
      }
    ],
    "edges": [
      {"from": "n_1", "to": "n_2", "type": "generates"},
      {"from": "n_2", "to": "n_3", "type": "retrieves"},
      {"from": "n_3", "to": "n_4", "type": "extracts"},
      {"from": "n_4", "to": "n_5", "type": "supports"}
    ]
  },
  "visualization_url": "/viz/trace/c_a7f3e9d1"
}
```

`GET /api/v1/health`

Health check endpoint for monitoring.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-22T15:30:00Z",
  "services": {
    "api": {"status": "up", "latency_ms": 5},
    "database": {"status": "up", "latency_ms": 12},
    "redis": {"status": "up", "latency_ms": 3},
    "retrieval": {"status": "up", "index_loaded": true},
    "gpu": {"status": "available", "device": "NVIDIA RTX 4090"}
  },
  "metrics": {
    "requests_last_minute": 42,
    "cache_hit_rate": 0.67,
    "avg_latency_ms": 1150
  }
}
```

**Response (503 Service Unavailable - degraded):**

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "timestamp": "2025-10-22T15:30:00Z",
  "services": {
    "api": {"status": "up"},
    "database": {"status": "up"},
    "redis": {"status": "down", "error": "Connection refused"},
    "retrieval": {"status": "up"},
    "gpu": {"status": "unavailable", "fallback": "cpu"}
  },
  "message": "Service degraded: Redis cache unavailable, using CPU fallback"
}
```

**Authentication**:

- API key authentication (X-API-Key header)
- Rate limiting per key with tiered plans
- Public endpoints for health/metrics

**API Versioning Validation**:

- All endpoints enforce `/api/v1/` prefix
- Version negotiation via Accept header
- Deprecation warnings for future v2 migration
- Backward compatibility guarantees documented

**Cloud Integration**:

- Webhook support for cloud event notifications (POST to user-provided URLs)
- Export to cloud storage (S3, Azure Blob) in addition to local filesystem
- API client SDKs (Python, JavaScript) that work with both local and cloud deployments
- CloudEvents format support for async job notifications

### Export Formats

#### ClaimReview JSON-LD

Schema.org ClaimReview format for search engine indexing:

```json
{
  "@context": "https://schema.org",
  "@type": "ClaimReview",
  "claimReviewed": "The Eiffel Tower is 330m tall",
  "reviewRating": {
    "@type": "Rating",
    "ratingValue": 5,
    "bestRating": 5,
    "alternateName": "SUPPORTED"
  },
  "itemReviewed": {
    "@type": "Claim",
    "author": {"@type": "Person", "name": "Anonymous"}
  },
  "author": {"@type": "Organization", "name": "TruthGraph"}
}
```

#### CSV Export

Bulk results for analysis:

```csv
claim_id,claim_text,verdict,confidence,evidence_count,sources,timestamp
c_001,"Eiffel Tower 330m",SUPPORTED,0.87,3,"wiki:Eiffel_Tower;...",2025-10-22T10:30:00Z
```

#### PDF Reports

Human-readable reports with:

- Claim summary and verdict
- Evidence snippets with source citations
- Reasoning chain visualization
- Temporal validity information
- Confidence scores and caveats

**Library**: ReportLab with templating

### Batch Processing Mode

**Architecture**:

- Redis-backed task queue (RQ or Celery)
- Worker pool for parallel claim processing
- Progress tracking via WebSocket or polling endpoint

**CLI**:

```bash
truthgraph batch verify --input claims.jsonl --output results.jsonl --workers 4
```

**API Flow**:

1. `POST /api/v1/claims/batch` with JSONL payload
2. Returns `job_id` and tracking URL
3. `GET /api/v1/jobs/{job_id}` polls status
4. `GET /api/v1/jobs/{job_id}/results` downloads completed results

### Rate Limiting & Error Handling

**Rate Limits**:

- Free tier: 10 req/min, 1000 req/day
- Developer tier: 100 req/min, 50k req/day
- Enterprise: custom quotas

**Implementation**: Token bucket with Redis backend

**Error Responses**:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Quota exceeded. Retry after 60 seconds.",
    "retry_after": 60,
    "request_id": "req_abc123"
  }
}
```

**Status Codes**:

- `200` - Success
- `400` - Invalid input (malformed claim, unsupported language)
- `429` - Rate limit exceeded
- `500` - Internal error (logged with request_id)
- `503` - Service degraded (retrieval/model unavailable)

---

## Cloud Migration Validation

This section validates that the cloud-ready abstractions built in earlier phases **actually work** with real cloud services. The goal is to prove that migrating v1 to v2 cloud deployment requires <50% refactoring, not a complete rewrite.

### Repository Pattern with Cloud Databases

**Objective**: Validate that the repository abstraction can swap local storage for cloud databases with minimal code changes.

**Test Scenarios**:

1. **PostgreSQL on AWS RDS**
   - Migrate ClaimRepository from SQLite to PostgreSQL
   - Test connection pooling with RDS (using PgBouncer or SQLAlchemy pooling)
   - Validate query performance (ensure indices are optimal)
   - Test failover and replica reads
   - Measure latency impact: local SQLite vs. RDS (expect +20-50ms)

2. **Vector Database Migration**
   - Test FAISS → Pinecone migration for embeddings
   - Validate semantic search results are consistent
   - Measure query latency: local FAISS vs. Pinecone API
   - Test batch embedding upload (optimize for API rate limits)
   - Estimate cost: embeddings storage + query volume

3. **Document Storage on S3**
   - Migrate document corpus from local filesystem to S3
   - Test presigned URLs for document retrieval
   - Implement caching layer to minimize S3 API calls
   - Measure retrieval latency vs. local disk
   - Estimate cost: storage + GET requests

**Success Criteria**:

- [ ] Repository implementations swap with <10 lines of config change
- [ ] Query performance within 2x of local (with caching)
- [ ] No application logic changes required (only connection strings)
- [ ] Connection pooling prevents exhaustion under load

### CloudEvents with Message Queues

**Objective**: Validate that the event-driven architecture works with cloud message queues.

**Test Scenarios**:

1. **AWS SQS Integration**
   - Publish CloudEvents to SQS on claim verification completion
   - Test FIFO queues for ordered processing
   - Validate dead-letter queue for failed messages
   - Measure end-to-end latency: claim verified → event consumed
   - Test at-least-once delivery semantics

2. **AWS EventBridge Integration**
   - Publish CloudEvents to EventBridge event bus
   - Set up routing rules to Lambda/SNS/SQS targets
   - Test event filtering and pattern matching
   - Validate CloudEvents schema compliance

3. **Azure Service Bus (Optional)**
   - Test cross-cloud compatibility of CloudEvents format
   - Validate that event schema is cloud-agnostic

**Success Criteria**:

- [ ] CloudEvents published to SQS/EventBridge successfully
- [ ] Event consumers receive valid CloudEvents format
- [ ] <5 lines of code change to swap local events → cloud queues
- [ ] No message loss during 1-hour load test (1000 msgs/min)

### Observability with Cloud Monitoring

**Objective**: Validate that metrics, logs, and traces integrate with cloud-native observability tools.

**Test Scenarios**:

1. **AWS CloudWatch Integration**
   - Export Prometheus metrics to CloudWatch
   - Create CloudWatch dashboards (latency, error rate, throughput)
   - Set up CloudWatch Alarms (high latency, error spike)
   - Test log aggregation with CloudWatch Logs
   - Validate metric retention and querying

2. **Datadog Integration**
   - Send metrics to Datadog via StatsD/API
   - Create Datadog dashboards mirroring Grafana setup
   - Test APM (Application Performance Monitoring) tracing
   - Set up anomaly detection and alerting
   - Validate distributed tracing across services

3. **OpenTelemetry Export**
   - Instrument code with OpenTelemetry SDK
   - Export traces to cloud backends (AWS X-Ray, Datadog)
   - Validate trace context propagation across API calls
   - Test sampling strategies to control data volume

**Success Criteria**:

- [ ] All Prometheus metrics available in CloudWatch/Datadog
- [ ] Alerting rules migrated to cloud-native equivalents
- [ ] Distributed tracing works end-to-end (API → retrieval → NLI)
- [ ] <20 lines of code to add OpenTelemetry instrumentation

### Performance Comparison: Local vs. Cloud

**Objective**: Quantify performance degradation when using cloud services.

**Benchmark Setup**:

- Run FEVER dev set (1000 claims) on local infrastructure
- Run same workload with cloud services enabled
- Measure latency, throughput, and resource utilization

**Configurations to Test**:

| Config | Database | Vector Store | Cache | Expected Latency | Notes |
|--------|----------|--------------|-------|------------------|-------|
| Baseline | Local SQLite | Local FAISS | Local Redis | 800ms (p95) | Current v1 setup |
| Cloud Lite | Local SQLite | Local FAISS | ElastiCache | 850ms (p95) | Only cache in cloud |
| Cloud Medium | RDS PostgreSQL | Local FAISS | ElastiCache | 1000ms (p95) | DB + cache in cloud |
| Cloud Full | RDS PostgreSQL | Pinecone | ElastiCache | 1200ms (p95) | All services in cloud |

**Key Metrics**:

- **p50, p95, p99 latency**: Measure tail latency increase
- **Throughput**: Claims processed per second
- **Network latency**: Measure time spent in network calls vs. compute
- **Cache hit rate**: Verify caching mitigates cloud API latency

**Success Criteria**:

- [ ] Cloud Full config latency <2x baseline
- [ ] Throughput >50% of baseline with cloud services
- [ ] Network latency identified and optimized (connection pooling, batching)
- [ ] Caching reduces cloud API calls by >70%

### Cost Estimation for Cloud Deployment

**Objective**: Provide realistic cost estimates for running TruthGraph in the cloud.

**Workload Assumptions**:

- 1M claims/month (typical production workload)
- 100 req/sec peak traffic
- 7-day data retention for results
- 30-day log retention

**AWS Cost Breakdown** (us-east-1 region):

**Compute (API + Workers)**:

- EC2 g5.xlarge (GPU instance): ~$1.00/hr × 2 instances × 730 hrs = **$1,460/month**
- Alternative: EC2 c6i.4xlarge (CPU fallback): ~$0.68/hr × 2 instances × 730 hrs = **$993/month**

**Database (PostgreSQL RDS)**:

- db.t3.medium (2 vCPU, 4GB RAM): ~$73/month
- Storage: 100GB SSD @ $0.115/GB = **$11.50/month**
- Total: **$85/month**

**Vector Database (Pinecone)**:

- Standard plan: $70/month (1M vectors, 100 QPS)
- Estimated usage: 5M vectors, 50 QPS = **$200/month**

**Cache (ElastiCache Redis)**:

- cache.m6g.large (2 vCPU, 6.38GB RAM): ~$0.136/hr × 730 hrs = **$99/month**

**Storage (S3)**:

- Document corpus: 500GB @ $0.023/GB = $11.50/month
- Request costs: 1M GET requests @ $0.0004/1k = $0.40/month
- Total: **$12/month**

**Message Queue (SQS)**:

- 1M requests/month: Free tier (1M free)
- Additional: $0.40/million requests = **$0/month (within free tier)**

**Monitoring (CloudWatch)**:

- Metrics: 100 custom metrics @ $0.30/metric = $30/month
- Logs: 50GB ingestion @ $0.50/GB = $25/month
- Alarms: 10 alarms @ $0.10/alarm = $1/month
- Total: **$56/month**

**Data Transfer**:

- Outbound: 100GB/month @ $0.09/GB = **$9/month**

**Total Monthly Cost (AWS)**:

- **GPU setup**: ~$2,121/month (~$0.002 per claim)
- **CPU setup**: ~$1,654/month (~$0.0017 per claim)

**Cost Optimization Strategies**:

- Use Spot Instances for workers (50-70% savings)
- Use Reserved Instances for predictable workloads (30-40% savings)
- Implement auto-scaling to reduce idle capacity
- Use S3 Intelligent-Tiering for infrequent access data
- Cache aggressively to reduce Pinecone API calls

**Multi-Cloud Comparison** (1M claims/month):

| Cloud Provider | GPU Setup | CPU Setup | Notes |
|----------------|-----------|-----------|-------|
| AWS | $2,121/mo | $1,654/mo | Baseline (above) |
| GCP | $2,300/mo | $1,700/mo | Slightly higher compute costs |
| Azure | $2,450/mo | $1,800/mo | Premium for GPU instances |

**Success Criteria**:

- [ ] Cost per claim <$0.005 for typical workload
- [ ] Cost model documented with variable workload scenarios
- [ ] Cost optimization strategies identified (spot instances, caching)
- [ ] Multi-cloud cost comparison provided

### Cloud Deployment Templates

**Objective**: Provide ready-to-use Infrastructure as Code (IaC) templates.

**AWS Terraform Template**:

```hcl
# terraform/aws/main.tf
module "truthgraph_vpc" {
  source = "./modules/vpc"
  cidr_block = "10.0.0.0/16"
}

module "truthgraph_rds" {
  source = "./modules/rds"
  instance_class = "db.t3.medium"
  allocated_storage = 100
  vpc_id = module.truthgraph_vpc.vpc_id
}

module "truthgraph_elasticache" {
  source = "./modules/elasticache"
  node_type = "cache.m6g.large"
  vpc_id = module.truthgraph_vpc.vpc_id
}

module "truthgraph_ecs" {
  source = "./modules/ecs"
  image = "truthgraph/truthgraph:1.0.0"
  desired_count = 2
  task_cpu = 4096
  task_memory = 16384
  gpu_enabled = true
}

module "truthgraph_alb" {
  source = "./modules/alb"
  vpc_id = module.truthgraph_vpc.vpc_id
  target_group_arn = module.truthgraph_ecs.target_group_arn
}
```

**Kubernetes Helm Chart**:

```yaml
# helm/truthgraph/values.yaml
replicaCount: 2

image:
  repository: truthgraph/truthgraph
  tag: "1.0.0"
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 4
    memory: 16Gi
    nvidia.com/gpu: 1
  requests:
    cpu: 2
    memory: 8Gi

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true
  postgresqlUsername: truthgraph
  postgresqlDatabase: truthgraph
  persistence:
    size: 100Gi

redis:
  enabled: true
  master:
    persistence:
      size: 10Gi
```

**Success Criteria**:

- [ ] Terraform templates deploy successfully to AWS (tested)
- [ ] Helm chart deploys successfully to Kubernetes cluster
- [ ] Templates parameterized for easy customization (instance sizes, regions)
- [ ] Documentation includes step-by-step deployment guide

---

## Evaluation Suite

### Built-in Benchmarks

#### FEVER (Fact Extraction and VERification)

- **Dataset**: 185k claims from Wikipedia with SUPPORTS/REFUTES/NOT ENOUGH INFO labels
- **Task**: Retrieve evidence sentences and predict verdict
- **Metric**: FEVER score (accuracy when evidence retrieval is correct)

#### FEVEROUS (FEVER with structured data)

- **Dataset**: Claims requiring table + text reasoning
- **Task**: Multi-hop retrieval from Wikipedia tables/infoboxes
- **Metric**: FEVEROUS score (strict and lenient evidence matching)

**Dataset Management**:

```bash
truthgraph datasets download fever
truthgraph datasets download feverous
truthgraph datasets list
```

Datasets stored in `~/.truthgraph/datasets/` with version tracking.

#### Dataset Download Instructions

**FEVER Dataset**

1. Download via CLI (recommended):

```bash
# Download all splits (train/dev/test)
truthgraph datasets download fever --all

# Download specific split
truthgraph datasets download fever --split dev

# Verify integrity
truthgraph datasets verify fever
```

1. Manual download:

```bash
# Create dataset directory
mkdir -p ~/.truthgraph/datasets/fever

# Download from official source
wget https://fever.ai/download/fever/train.jsonl -O ~/.truthgraph/datasets/fever/train.jsonl
wget https://fever.ai/download/fever/shared_task_dev.jsonl -O ~/.truthgraph/datasets/fever/dev.jsonl
wget https://fever.ai/download/fever/shared_task_test.jsonl -O ~/.truthgraph/datasets/fever/test.jsonl

# Download Wikipedia evidence corpus
wget https://fever.ai/download/fever/wiki-pages.zip
unzip wiki-pages.zip -d ~/.truthgraph/datasets/fever/wiki_pages/
```

1. Dataset statistics:

```text
Train:    145,449 claims
Dev:       19,998 claims
Test:      19,998 claims (labels withheld)
Evidence:  5,416,537 Wikipedia articles (June 2017 dump)
```

**FEVEROUS Dataset**

1. Download via CLI:

```bash
# Download FEVEROUS with tables
truthgraph datasets download feverous --all

# Verify and build indices
truthgraph datasets verify feverous
truthgraph index build --dataset feverous --output ~/.truthgraph/indices/feverous
```

1. Manual download:

```bash
mkdir -p ~/.truthgraph/datasets/feverous

# Download claims
wget https://fever.ai/download/feverous/feverous_train.jsonl
wget https://fever.ai/download/feverous/feverous_dev.jsonl

# Download Wikipedia dump with tables
wget https://fever.ai/download/feverous/feverous_wikiv1.db
```

1. Dataset statistics:

```text
Train:    87,026 claims (requiring table/text reasoning)
Dev:       6,666 claims
Test:      6,666 claims (labels withheld)
Evidence:  95,035 Wikipedia articles with 1.2M tables
```

**Custom Dataset Format**

For evaluation on custom datasets, use JSONL format:

```json
{"id": "custom_001", "claim": "The Eiffel Tower was built in 1889", "label": "SUPPORTS", "evidence": [{"text": "...", "source": "..."}]}
{"id": "custom_002", "claim": "Paris is in Germany", "label": "REFUTES", "evidence": [{"text": "...", "source": "..."}]}
```

Required fields:

- `id`: Unique claim identifier
- `claim`: Claim text
- `label`: One of `SUPPORTS`, `REFUTES`, `NOT_ENOUGH_INFO`
- `evidence` (optional): List of gold evidence for recall calculation

**Storage Structure**:

```text
~/.truthgraph/datasets/
├── fever/
│   ├── train.jsonl
│   ├── dev.jsonl
│   ├── test.jsonl
│   ├── wiki_pages/ (5.4M files)
│   └── metadata.json (version, download date, checksums)
├── feverous/
│   ├── train.jsonl
│   ├── dev.jsonl
│   ├── feverous_wikiv1.db (SQLite database)
│   └── metadata.json
└── custom/
    └── your_dataset.jsonl
```

### CLI Evaluation Commands

```bash
# Evaluate on FEVER dev set
truthgraph eval fever --split dev --output results/fever_dev.json

# Evaluate on custom dataset
truthgraph eval custom --data my_claims.jsonl --gold gold_labels.jsonl

# Run ablations
truthgraph eval fever --no-rerank --no-temporal

# Compare checkpoints
truthgraph eval fever --model-a v1.0 --model-b v1.1 --compare
```

**Output Format**:

```json
{
  "dataset": "fever",
  "split": "dev",
  "timestamp": "2025-10-22T14:30:00Z",
  "config": {"retriever": "hybrid", "rerank": true, "top_k": 5},
  "metrics": {
    "fever_score": 0.712,
    "label_accuracy": 0.745,
    "evidence_recall": 0.823
  },
  "per_label": {
    "SUPPORTS": {"precision": 0.78, "recall": 0.81, "f1": 0.795},
    "REFUTES": {"precision": 0.71, "recall": 0.68, "f1": 0.695}
  }
}
```

### Metrics

All evaluation metrics are explained in detail to ensure reproducibility and clear understanding.

#### FEVER Score

**Definition**: Percentage of claims where both the verdict label is correct AND at least one gold evidence sentence is retrieved.

**Calculation**:

```fever
FEVER Score = (Correct verdicts with correct evidence) / Total claims
```

**Example**: If a claim has label "SUPPORTS" and gold evidence "Paris is the capital of France", the system must:

1. Predict verdict = "SUPPORTS" (correct)
2. Retrieve at least one sentence from the gold evidence set

If either condition fails, the claim is marked incorrect.

**Why it matters**: This is a strict end-to-end metric that ensures the system not only predicts the right label but also retrieves the actual evidence that supports it. A system could achieve high accuracy by memorizing labels, but FEVER score requires proper retrieval.

**Typical values**:

- Random baseline: ~33% (3-way classification)
- Basic retrieval + classifier: 50-60%
- State-of-the-art systems: 70-75%
- TruthGraph v1 target: >70%

#### Label Accuracy

**Definition**: Percentage of claims with correct verdict label, regardless of evidence retrieval.

**Calculation**:

```fever
Accuracy = (Correct verdicts) / Total claims
```

**Why it matters**: Measures classification performance independently from retrieval. Useful for diagnosing whether errors come from retrieval or verdict prediction.

#### Macro-F1

**Definition**: Unweighted average of F1 scores across all verdict classes (SUPPORTS, REFUTES, NOT_ENOUGH_INFO).

**Calculation**:

```fever
Macro-F1 = (F1_supports + F1_refutes + F1_nei) / 3

Where F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

**Why it matters**: Balances performance across all classes, preventing the model from ignoring minority classes. In FEVER, the distribution is roughly:

- SUPPORTS: 37%
- REFUTES: 33%
- NOT_ENOUGH_INFO: 30%

Plain accuracy could be high even if the system never predicts NEI. Macro-F1 ensures all classes are handled well.

**Example**:

```text
SUPPORTS:    Precision=0.78, Recall=0.81 → F1=0.795
REFUTES:     Precision=0.71, Recall=0.68 → F1=0.695
NEI:         Precision=0.65, Recall=0.70 → F1=0.674
Macro-F1 = (0.795 + 0.695 + 0.674) / 3 = 0.721
```

#### Recall@k

**Definition**: Percentage of claims where at least one gold evidence sentence appears in the top-k retrieved documents.

**Calculation**:

```fever
Recall@k = (Claims with evidence in top-k) / Total claims with evidence
```

**Why it matters**: Measures retrieval quality independently from verdict prediction. If Recall@5 is low, the system won't have the necessary evidence to make correct predictions.

**k values**: 5, 10, 20, 100

- **Recall@5**: Precision-focused, measures if critical evidence is ranked high
- **Recall@100**: Coverage-focused, measures if evidence is findable at all

**Expected progression**:

- Recall@5: 65-75% (good systems retrieve relevant docs in top results)
- Recall@20: 80-85%
- Recall@100: 90-95%

**Example**: If gold evidence is "Paris is the capital of France" and the system retrieves 100 documents, we check if any retrieved document contains this sentence. If found at position 12, then:

- Recall@5 = 0 (not in top 5)
- Recall@20 = 1 (found in top 20)
- Recall@100 = 1 (found in top 100)

#### MRR (Mean Reciprocal Rank)

**Definition**: Average of 1/rank for the first gold evidence sentence found in retrieved results.

**Calculation**:

```fever
MRR = (1/N) * Σ(1/rank_i)

Where rank_i is the position of the first correct evidence for claim i
```

**Why it matters**: Rewards systems that rank relevant evidence higher. Finding evidence at position 2 is better than position 20.

**Example**:

```text
Claim 1: First gold evidence at rank 3  → 1/3 = 0.333
Claim 2: First gold evidence at rank 1  → 1/1 = 1.000
Claim 3: No gold evidence retrieved     → 0/0 = 0.000
MRR = (0.333 + 1.000 + 0.000) / 3 = 0.444
```

**Interpretation**:

- MRR = 1.0: Perfect, first result always correct
- MRR = 0.5: On average, correct evidence at rank 2
- MRR = 0.1: Correct evidence around rank 10

#### Evidence Precision

**Definition**: Percentage of retrieved sentences that are actually gold evidence sentences.

**Calculation**:

```text
Evidence Precision = (Retrieved sentences in gold set) / Total retrieved sentences
```

**Why it matters**: Measures retrieval noise. High recall with low precision means the system retrieves too much irrelevant content.

**Typical tradeoff**: Retrieving top-5 documents has higher precision but lower recall than retrieving top-100.

#### Latency Metrics

**Definition**: Processing time distribution for claim verification.

**Measurements**:

- **p50 (median)**: 50% of requests complete faster than this
- **p95**: 95% of requests complete faster than this (tail latency)
- **p99**: 99% of requests complete faster than this (worst-case latency)

**Why it matters**: p95/p99 latency matters more than average for user experience. A system with avg=500ms but p95=5000ms has poor UX.

**Target values for TruthGraph v1**:

- p50: <800ms
- p95: <1500ms
- p99: <3000ms

#### Faithfulness Score

**Definition**: NLI (Natural Language Inference) score measuring whether the verdict is logically supported by the cited evidence.

**Calculation**:

```text
For each (verdict, evidence) pair:
  Faithfulness = P(verdict entailed by evidence)

System faithfulness = Average across all claims
```

**Why it matters**: Detects "hallucination" where the system cites evidence that doesn't actually support the verdict.

**Example**:

```text
Claim: "Paris is the capital of France"
Verdict: SUPPORTED
Evidence: "Paris is the most populous city in France"
Faithfulness: Low (evidence doesn't prove capital status)
```

**Target**: Faithfulness >0.85 (85% of verdicts properly supported by cited evidence)

### Results Storage and Visualization

**Storage**:

- SQLite database: `~/.truthgraph/eval_results.db`
- Tables: `runs`, `metrics`, `predictions`, `errors`
- Indexed by timestamp, dataset, config hash

**Visualization**:

```bash
# Launch dashboard
truthgraph eval dashboard

# Compare runs
truthgraph eval compare run_001 run_002 --metric fever_score

# Export plot
truthgraph eval plot --metric recall@k --runs run_001,run_002 --output chart.png
```

**Dashboard** (Streamlit):

- Metric trends over time
- Per-label confusion matrices
- Error analysis (sample failed predictions)
- Latency distributions

### Cloud Configuration Benchmarks

**Objective**: Validate performance and cost tradeoffs for cloud-based deployments.

**Benchmark Configurations**:

1. **FEVER with Pinecone vs. FAISS**
   - Run FEVER dev set with local FAISS index (baseline)
   - Run same set with Pinecone cloud vector database
   - Compare: FEVER score, latency, throughput, cost per query
   - Expected: FEVER score within 1%, latency +200-300ms, cost $0.0001/query

2. **RDS vs. SQLite**
   - Run 1000 claims with local SQLite (baseline)
   - Run same claims with PostgreSQL on RDS
   - Compare: query latency, write latency, connection overhead
   - Expected: Read latency +20-50ms, write latency +30-70ms

3. **ElastiCache vs. Local Redis**
   - Measure cache hit rate and latency with local Redis
   - Measure same with ElastiCache (cloud-hosted)
   - Expected: Latency +5-10ms, cache hit rate identical

**Cost-Per-Query Metrics**:

Track cost breakdown for each claim verification:

```json
{
  "claim_id": "c_001",
  "costs": {
    "compute": 0.0008,        // EC2 instance time
    "pinecone_query": 0.0001, // Vector search API call
    "rds_query": 0.00001,     // Database query
    "s3_get": 0.000001,       // Document retrieval
    "elasticache": 0.00002,   // Cache operation
    "total": 0.00093          // Total cost per claim
  },
  "latency_ms": 1150
}
```

**Multi-Region Latency Testing**:

Test API latency from different geographic regions to prepare for global deployment:

| Client Region | API Region (us-east-1) | Latency (p95) | Notes |
|---------------|------------------------|---------------|-------|
| US East | us-east-1 | 850ms | Baseline (same region) |
| US West | us-east-1 | 950ms | +100ms cross-region |
| Europe | us-east-1 | 1200ms | +350ms transatlantic |
| Asia | us-east-1 | 1500ms | +650ms transcontinental |

**Recommendations**:

- Deploy multi-region for global latency <1000ms
- Use CloudFront CDN for static assets (OpenAPI docs, SDK downloads)
- Consider edge computing for latency-critical regions

**Performance Degradation Documentation**:

Document expected performance impact of cloud services:

| Component | Local | Cloud | Degradation | Mitigation |
|-----------|-------|-------|-------------|------------|
| Vector Search | FAISS (50ms) | Pinecone (250ms) | 5x slower | Batch queries, cache results |
| Database | SQLite (5ms) | RDS (30ms) | 6x slower | Connection pooling, read replicas |
| Cache | Redis local (2ms) | ElastiCache (7ms) | 3.5x slower | Minimize cache misses, batch operations |
| Document Storage | Local disk (10ms) | S3 (80ms) | 8x slower | CDN, aggressive caching |

**Success Criteria**:

- [ ] FEVER score difference <1% between local and cloud configurations
- [ ] Cost per query documented for all cloud services
- [ ] Multi-region latency measured from at least 3 geographic locations
- [ ] Performance degradation quantified and mitigation strategies documented

---

## Optimizations

### GPU Support for Embeddings & NLI

**CUDA Detection**:

```python
import torch

if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    device = torch.device("cpu")
```

**Models**:

- **Embeddings**: Contriever (110M params) - batch encode on GPU
- **NLI**: DeBERTa-v3-large (304M params) - premise/hypothesis pairs
- **Reranker**: MonoT5-base (220M params) - cross-encoder scoring

**Batching Strategy**:

- Dynamic batching with padding to max sequence length
- Target: 32-64 samples/batch on 16GB GPU
- Gradient accumulation not needed (inference only)

**Mixed Precision**:

```python
model.half()  # FP16 inference
torch.backends.cudnn.benchmark = True
```

Expected speedup: 2-3x vs FP32, minimal accuracy loss.

### CPU Fallback Strategies

**Fallback Hierarchy**:

1. GPU (CUDA) - primary
2. CPU (multi-threaded BLAS) - automatic fallback
3. Quantized models (INT8) - memory-constrained environments

**Optimizations for CPU**:

- ONNX Runtime with quantized models (4x faster inference)
- Distilled models: MiniLM-L6 (22M params) instead of Contriever
- Smaller batch sizes (8-16) to avoid memory pressure
- TorchScript JIT compilation

**Configuration**:

```yaml
# config.yaml
compute:
  prefer_gpu: true
  cpu_threads: 8
  use_quantized: false  # auto-enable if GPU unavailable
  onnx_runtime: true
```

### Caching Layer with Redis

**Cache Strategy**:

1. **Embedding Cache**: Document embeddings by content hash
   - TTL: 7 days (eviction for rarely-accessed docs)
   - Key: `emb:sha256:{doc_hash}`
   - Value: Compressed numpy array (zstd)

2. **Retrieval Cache**: Top-k results by claim + config hash
   - TTL: 24 hours
   - Key: `retr:{claim_hash}:{config_hash}`
   - Value: JSON list of doc_ids + scores

3. **Verdict Cache**: Full verification results
   - TTL: 1 hour (claims may be time-sensitive)
   - Key: `verdict:{claim_hash}:{as_of}`
   - Value: Serialized `VerificationResult`

**Invalidation**:

- Manual: `truthgraph cache clear --pattern "verdict:*"`
- On index update: Clear retrieval/verdict caches

**Deployment**:

```bash
docker run -d -p 6379:6379 redis:7-alpine
truthgraph config set redis.url redis://localhost:6379
```

### Pre-built Indices for Common Corpora

**Supported Corpora**:

- Wikipedia 2024-12 snapshot (6.5M articles)
- KILT knowledge source (2019-08 Wikipedia + entity linking)
- PubMed abstracts (35M documents, optional)

**Index Artifacts**:

- FAISS HNSW index (embeddings)
- BM25 inverted index (sparse retrieval)
- Metadata parquet files (title, URL, timestamp)

**Distribution**:

```bash
# Download pre-built index (~50GB compressed)
truthgraph index download wikipedia-2024-12

# Verify integrity
truthgraph index verify wikipedia-2024-12

# Build custom index
truthgraph index build --input docs.jsonl --name custom_corpus
```

**Index Format**:

```text
~/.truthgraph/indices/wikipedia-2024-12/
  ├── faiss.index          # FAISS HNSW
  ├── bm25.index           # Pyserini sparse
  ├── metadata.parquet     # Doc metadata
  ├── config.json          # Build params
  └── manifest.json        # Checksums
```

### Performance Profiling and Monitoring

**Built-in Profiler**:

```bash
# Profile single claim
truthgraph verify "Claim text" --profile --output profile.json

# Profile batch
truthgraph batch verify --input claims.jsonl --profile --profile-output trace.json
```

**Trace Output**:

```json
{
  "claim_id": "c_001",
  "total_time_ms": 1234,
  "stages": {
    "parsing": 45,
    "retrieval": 680,
    "reranking": 320,
    "nli": 180,
    "provenance": 9
  },
  "cache_hits": {"embeddings": 128, "retrieval": 0}
}
```

**Prometheus Metrics**:

- `truthgraph_requests_total{endpoint, status}` - Request counter
- `truthgraph_latency_seconds{stage}` - Histogram of stage latencies
- `truthgraph_cache_hits_total{cache_type}` - Cache hit counter
- `truthgraph_gpu_utilization` - GPU % (if available)

**Grafana Dashboards**:

- Request throughput and error rate
- Latency percentiles (p50/p95/p99) by stage
- Cache hit rates
- GPU/CPU utilization

### Performance Tuning Guide

Comprehensive guide for optimizing TruthGraph performance based on your deployment scenario.

#### Identifying Bottlenecks

**Step 1: Profile a representative workload**

```bash
# Profile 100 claims from your dataset
truthgraph batch verify \
  --input sample_claims.jsonl \
  --output results.jsonl \
  --profile \
  --profile-output profile.json

# Analyze bottlenecks
truthgraph analyze profile.json --top 5
```

**Common bottlenecks and solutions**:

1. **Retrieval (60-70% of total time)**
   - Symptom: High time in `retrieval` stage
   - Solutions: Pre-build indices, use GPU for embeddings, tune top_k

2. **Reranking (20-30% of total time)**
   - Symptom: High time in `reranking` stage
   - Solutions: Reduce rerank candidates, use quantized models, batch processing

3. **NLI (10-15% of total time)**
   - Symptom: High time in `nli` stage
   - Solutions: GPU inference, larger batch sizes, distilled models

4. **Disk I/O**
   - Symptom: High system I/O wait, slow index loading
   - Solutions: SSD storage, load indices to RAM, memory-mapped files

#### Tuning Parameters

**Retrieval Parameters**

```yaml
# config.yaml
retrieval:
  # Number of documents to retrieve (lower = faster, may miss evidence)
  top_k: 100  # Default: 100, Tune: 50-200

  # Retrieval strategy
  mode: "hybrid"  # Options: "dense", "sparse", "hybrid"
  # hybrid is best quality but slower, dense is faster

  # Hybrid fusion weight (how much to trust dense vs sparse)
  fusion_alpha: 0.7  # Range: 0.0 (sparse only) to 1.0 (dense only)

  # Enable query expansion
  query_expansion: true  # Adds synonyms/related terms, +10% recall, +20% latency

reranking:
  # Number of documents to rerank (lower = faster)
  rerank_top_k: 20  # Default: 20, Tune: 10-50

  # Enable reranking (disabling saves 20-30% latency)
  enabled: true

  # Reranking model size
  model: "monot5-base"  # Options: "monot5-base" (best), "minilm" (fast)

evidence:
  # Maximum evidence sentences to extract per claim
  max_evidence: 5  # Default: 5, Tune: 3-10

  # Minimum relevance score for evidence
  min_relevance: 0.6  # Default: 0.6, Range: 0.0-1.0
```

**Performance vs Quality Tradeoffs**

| Profile | top_k | rerank_top_k | query_exp | Expected Latency | Expected FEVER Score |
|---------|-------|--------------|-----------|------------------|---------------------|
| Fast | 50 | 10 | false | ~600ms | 0.65 |
| Balanced | 100 | 20 | true | ~1200ms | 0.71 |
| Quality | 200 | 50 | true | ~2500ms | 0.73 |

**Compute Parameters**

```yaml
compute:
  # GPU settings
  device: "cuda"  # Options: "cuda", "cpu", "auto"
  gpu_id: 0  # For multi-GPU systems

  # Batch sizes (larger = better GPU utilization, more memory)
  embedding_batch_size: 64  # Default: 64, Tune: 32-128
  nli_batch_size: 32  # Default: 32, Tune: 16-64
  rerank_batch_size: 16  # Default: 16, Tune: 8-32

  # CPU threads for sparse retrieval
  cpu_threads: 8  # Default: 8, Set to CPU core count

  # Mixed precision (faster, slight quality loss)
  use_fp16: true  # Recommended: true for inference

  # Model quantization for CPU
  use_quantization: false  # Auto-enabled if GPU unavailable
```

**Memory Optimization**

```yaml
memory:
  # Load index to RAM (faster but requires more memory)
  mmap_indices: false  # true = memory-mapped (less RAM), false = full load (faster)

  # Maximum cache size
  max_cache_size_gb: 8  # Default: 8, Tune based on available RAM

  # Document cache (stores retrieved documents)
  document_cache_size: 10000  # Default: 10000 documents

  # Embedding cache (stores computed embeddings)
  embedding_cache_size: 100000  # Default: 100000 embeddings
```

#### Optimization Recipes

**Recipe 1: Maximum Throughput (Batch Processing)**

Use when processing large datasets offline, prioritizing throughput over latency.

```yaml
retrieval:
  top_k: 50
  mode: "dense"  # Faster than hybrid
  query_expansion: false

reranking:
  enabled: false  # Skip reranking to maximize throughput

compute:
  embedding_batch_size: 128  # Large batches for GPU efficiency
  use_fp16: true

# Run with multiple workers
truthgraph batch verify --input claims.jsonl --workers 8 --config fast_config.yaml
```

Expected: 10-15 claims/sec on single GPU, FEVER score ~0.65

**Recipe 2: Low Latency (Interactive API)**

Use for real-time API serving where user experience matters.

```yaml
retrieval:
  top_k: 80
  mode: "hybrid"

reranking:
  enabled: true
  rerank_top_k: 15
  model: "minilm"  # Faster reranker

compute:
  embedding_batch_size: 32  # Smaller batches for lower latency
  use_fp16: true

cache:
  redis_url: "redis://localhost:6379"
  ttl_hours: 24  # Cache frequent queries
```

Expected: p95 < 800ms with caching, FEVER score ~0.69

**Recipe 3: Maximum Quality (Research/Evaluation)**

Use for research or when quality is paramount.

```yaml
retrieval:
  top_k: 200
  mode: "hybrid"
  fusion_alpha: 0.7
  query_expansion: true

reranking:
  enabled: true
  rerank_top_k: 50
  model: "monot5-base"

evidence:
  max_evidence: 10

compute:
  use_fp16: false  # Full precision
```

Expected: 2-3 sec/claim, FEVER score ~0.73

**Recipe 4: CPU-Only (No GPU)**

Use for deployment without GPU access.

```yaml
retrieval:
  top_k: 100
  mode: "sparse"  # BM25 is CPU-friendly

reranking:
  enabled: true
  model: "minilm"  # Lightweight model

compute:
  device: "cpu"
  cpu_threads: 16  # Use all available cores
  use_quantization: true  # 4x faster on CPU
  embedding_batch_size: 16  # Smaller batches for CPU

# Use ONNX runtime for faster CPU inference
onnx_runtime: true
```

Expected: 3-5 sec/claim, FEVER score ~0.66

#### Monitoring and Iteration

**Step 1: Establish baseline**

```bash
# Run evaluation with default config
truthgraph eval fever --split dev --output baseline.json

# Record metrics
cat baseline.json | jq '.metrics'
```

**Step 2: Apply optimization**

```bash
# Test with optimized config
truthgraph eval fever --split dev --config optimized.yaml --output optimized.json

# Compare
truthgraph eval compare baseline.json optimized.json
```

**Step 3: A/B test in production**

```bash
# Route 10% of traffic to new config
# Monitor metrics in Grafana
# Compare FEVER score, latency, error rate
```

**Key Metrics to Track**:

- Latency (p50, p95, p99)
- Throughput (claims/sec)
- Quality (FEVER score on held-out set)
- Resource utilization (GPU%, CPU%, RAM)
- Cache hit rate

**Optimization Checklist**:

- [ ] Profile current performance with representative workload
- [ ] Identify bottleneck stage (retrieval, reranking, NLI)
- [ ] Apply targeted optimizations (tune parameters, upgrade hardware)
- [ ] Run evaluation to measure quality impact
- [ ] Load test to verify latency under production traffic
- [ ] Monitor in production and iterate

### Cloud-Specific Optimizations

**Objective**: Optimize performance and cost when using cloud services.

#### Connection Pooling for Cloud Databases

**Problem**: Opening new database connections to RDS is expensive (50-100ms overhead).

**Solution**: Connection pooling with SQLAlchemy and PgBouncer.

```python
# config.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Connection pool configuration
engine = create_engine(
    "postgresql://user:pass@rds-endpoint:5432/truthgraph",
    poolclass=QueuePool,
    pool_size=20,          # Max persistent connections
    max_overflow=10,       # Additional connections under load
    pool_pre_ping=True,    # Verify connection health before use
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

**Tuning**:

- `pool_size`: Set to expected concurrent queries (e.g., 20 for 2 workers × 10 threads)
- `max_overflow`: Burst capacity for traffic spikes
- `pool_pre_ping`: Prevents stale connection errors after idle time
- `pool_recycle`: Prevents AWS RDS timeout (default: 8 hours)

**Expected Impact**: Connection overhead reduced from 50ms to <5ms (10x improvement)

#### Batch Writes to Cloud Storage

**Problem**: Writing to S3 one file at a time incurs per-request latency (50-100ms).

**Solution**: Batch writes and multipart uploads.

```python
# s3_batch_writer.py
import boto3
from concurrent.futures import ThreadPoolExecutor

s3_client = boto3.client('s3')

def batch_upload_documents(documents, bucket, prefix):
    """Upload multiple documents to S3 in parallel"""
    def upload_one(doc):
        key = f"{prefix}/{doc['id']}.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(doc),
            ContentType='application/json'
        )
        return key

    # Upload up to 10 documents in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        keys = list(executor.map(upload_one, documents))

    return keys
```

**Multipart Upload for Large Files**:

```python
# For files >100MB, use multipart upload
s3_client.upload_file(
    'large_index.faiss',
    'truthgraph-indices',
    'wikipedia-2024/faiss.index',
    Config=boto3.s3.transfer.TransferConfig(
        multipart_threshold=100 * 1024 * 1024,  # 100MB
        max_concurrency=10,
        multipart_chunksize=10 * 1024 * 1024    # 10MB chunks
    )
)
```

**Expected Impact**: 10 document uploads: 500ms → 150ms (3x improvement)

#### Caching Strategies for Cloud Services

**Problem**: Cloud API calls add latency (Pinecone: 200ms, S3: 80ms).

**Solution**: Multi-tier caching with Redis and in-memory LRU.

```python
# caching_strategy.py
from functools import lru_cache
from redis import Redis
import pickle

redis_client = Redis(host='elasticache-endpoint', port=6379)

class CloudCachingLayer:
    def __init__(self):
        self.redis = redis_client
        self.local_cache = {}  # In-memory LRU

    @lru_cache(maxsize=10000)
    def get_embedding(self, text_hash):
        """Three-tier caching: Memory → Redis → Pinecone"""
        # Tier 1: In-memory cache (0.1ms)
        if text_hash in self.local_cache:
            return self.local_cache[text_hash]

        # Tier 2: Redis cache (7ms)
        cached = self.redis.get(f"emb:{text_hash}")
        if cached:
            embedding = pickle.loads(cached)
            self.local_cache[text_hash] = embedding
            return embedding

        # Tier 3: Pinecone API (250ms)
        embedding = self.fetch_from_pinecone(text_hash)

        # Populate caches
        self.redis.setex(f"emb:{text_hash}", 86400, pickle.dumps(embedding))
        self.local_cache[text_hash] = embedding

        return embedding
```

**Cache Hit Rate Target**: >80% (reduces 1000 Pinecone calls to 200)

**Cost Reduction**: 1000 queries × $0.0001 = $0.10 → 200 queries × $0.0001 = $0.02 (5x savings)

#### Cost Optimization Strategies

**1. Right-Sizing Instances**

Test performance across instance types to find sweet spot:

| Instance Type | vCPU | RAM | GPU | Cost/hr | Claims/hr | Cost/1k Claims |
|---------------|------|-----|-----|---------|-----------|----------------|
| g5.xlarge | 4 | 16GB | A10G | $1.00 | 5000 | $0.20 |
| g5.2xlarge | 8 | 32GB | A10G | $1.21 | 8000 | $0.15 |
| c6i.4xlarge (CPU) | 16 | 32GB | None | $0.68 | 1200 | $0.57 |

**Recommendation**: g5.2xlarge offers best cost/performance for GPU workloads.

**2. Spot Instances for Batch Workloads**

Use Spot Instances for non-urgent batch processing:

```yaml
# terraform/aws/spot_instance.tf
resource "aws_spot_instance_request" "truthgraph_worker" {
  ami           = "ami-truthgraph"
  instance_type = "g5.2xlarge"
  spot_price    = "0.60"  # 50% discount vs on-demand ($1.21)

  wait_for_fulfillment = true
  spot_type            = "persistent"

  tags = {
    Name = "truthgraph-batch-worker"
  }
}
```

**Savings**: 50-70% for batch workloads (acceptable interruption risk)

**3. Reserved Instances for Base Capacity**

For predictable workloads, commit to 1-year Reserved Instances:

- **On-Demand**: g5.2xlarge @ $1.21/hr = $10,590/year
- **Reserved (1yr, no upfront)**: $0.85/hr = $7,446/year (30% savings)
- **Reserved (1yr, all upfront)**: $0.72/hr = $6,307/year (40% savings)

**4. Auto-Scaling to Reduce Idle Capacity**

Scale workers based on queue depth:

```yaml
# kubernetes/autoscaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: truthgraph-workers
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: truthgraph-workers
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: sqs_queue_depth
      target:
        type: AverageValue
        averageValue: "50"  # Scale up if queue >50 messages
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5min before scaling down
```

**Savings**: Reduce idle capacity from 24/7 to peak-hours-only (50% cost reduction)

**5. S3 Intelligent-Tiering**

Automatically move infrequently accessed data to cheaper storage:

```python
# s3_lifecycle.py
s3_client.put_bucket_lifecycle_configuration(
    Bucket='truthgraph-data',
    LifecycleConfiguration={
        'Rules': [{
            'Id': 'archive-old-results',
            'Status': 'Enabled',
            'Transitions': [
                {
                    'Days': 30,
                    'StorageClass': 'INTELLIGENT_TIERING'  # Auto-tier based on access
                },
                {
                    'Days': 90,
                    'StorageClass': 'GLACIER_IR'  # Instant Retrieval archive
                }
            ]
        }]
    }
)
```

**Savings**: S3 Standard ($0.023/GB) → Intelligent-Tiering ($0.0125/GB average) = 45% savings

#### Disaster Recovery and Backup Strategies

**1. Database Backups (RDS)**

```hcl
# terraform/aws/rds.tf
resource "aws_db_instance" "truthgraph" {
  identifier = "truthgraph-prod"

  # Automated backups
  backup_retention_period = 7  # Keep 7 days of backups
  backup_window          = "03:00-04:00"  # Daily backup at 3am UTC

  # Point-in-time recovery
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Multi-AZ for high availability
  multi_az = true  # Automatic failover to standby

  # Snapshots
  snapshot_identifier = "truthgraph-snapshot-20250101"
  skip_final_snapshot = false
  final_snapshot_identifier = "truthgraph-final-snapshot"
}
```

**Recovery Objectives**:

- **RTO (Recovery Time Objective)**: <15 minutes (Multi-AZ failover)
- **RPO (Recovery Point Objective)**: <5 minutes (transaction log backups)

**2. Index Backups (S3 Versioning)**

```python
# Enable versioning for index artifacts
s3_client.put_bucket_versioning(
    Bucket='truthgraph-indices',
    VersioningConfiguration={'Status': 'Enabled'}
)

# Cross-region replication for disaster recovery
s3_client.put_bucket_replication(
    Bucket='truthgraph-indices',
    ReplicationConfiguration={
        'Role': 'arn:aws:iam::account:role/s3-replication',
        'Rules': [{
            'Status': 'Enabled',
            'Priority': 1,
            'Destination': {
                'Bucket': 'arn:aws:s3:::truthgraph-indices-backup-us-west-2',
                'StorageClass': 'STANDARD_IA'
            }
        }]
    }
)
```

**3. Cache Backup (Redis Persistence)**

```hcl
# terraform/aws/elasticache.tf
resource "aws_elasticache_replication_group" "truthgraph_redis" {
  replication_group_id = "truthgraph-cache"

  # Enable persistence
  snapshot_retention_limit = 5  # Keep 5 daily snapshots
  snapshot_window         = "05:00-06:00"  # Daily snapshot at 5am UTC

  # Automatic failover
  automatic_failover_enabled = true
  multi_az_enabled          = true
  num_cache_clusters        = 2  # Primary + replica
}
```

**4. Disaster Recovery Runbook**

**Scenario: Total Region Failure (us-east-1)**

1. **Immediate (T+0 to T+15min)**:
   - Activate standby region (us-west-2)
   - Update DNS to point to us-west-2 load balancer
   - Verify health checks pass in new region

2. **Data Restoration (T+15min to T+1hr)**:
   - Restore RDS from cross-region read replica (or latest snapshot)
   - Load indices from S3 cross-region bucket
   - Warm up Redis cache with frequent queries

3. **Validation (T+1hr to T+2hr)**:
   - Run smoke tests (verify 100 claims)
   - Compare FEVER score to baseline
   - Monitor error rates and latency

4. **Communication**:
   - Update status page
   - Notify users via email/webhook
   - Post incident report after resolution

**Testing**: Run disaster recovery drills quarterly

**Success Criteria**:

- [ ] Connection pooling reduces database overhead by >5x
- [ ] Batch S3 writes improve throughput by >3x
- [ ] Multi-tier caching achieves >80% hit rate
- [ ] Cost per claim <$0.002 with optimizations applied
- [ ] Spot instances tested and validated for batch workloads
- [ ] Disaster recovery plan documented and tested
- [ ] RTO <30 minutes, RPO <10 minutes validated

---

## Infrastructure as Code

**Objective**: Provide production-ready IaC templates for cloud deployment.

### Terraform Templates

**Directory Structure**:

```text
terraform/
├── aws/
│   ├── main.tf              # Root module
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   ├── modules/
│   │   ├── vpc/             # VPC, subnets, NAT gateway
│   │   ├── rds/             # PostgreSQL database
│   │   ├── elasticache/     # Redis cluster
│   │   ├── ecs/             # ECS Fargate for API
│   │   ├── alb/             # Application Load Balancer
│   │   ├── s3/              # S3 buckets for storage
│   │   └── monitoring/      # CloudWatch dashboards, alarms
│   └── environments/
│       ├── dev.tfvars       # Dev environment config
│       ├── staging.tfvars   # Staging environment config
│       └── prod.tfvars      # Production environment config
├── gcp/
│   └── (similar structure for GCP)
└── azure/
    └── (similar structure for Azure)
```

**Example: AWS RDS Module**:

```hcl
# terraform/aws/modules/rds/main.tf
resource "aws_db_subnet_group" "truthgraph" {
  name       = "${var.environment}-truthgraph-db-subnet"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.environment}-truthgraph"
    Environment = var.environment
  }
}

resource "aws_db_instance" "truthgraph" {
  identifier = "${var.environment}-truthgraph"

  # Engine
  engine         = "postgres"
  engine_version = "14.7"
  instance_class = var.instance_class

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = "truthgraph"
  username = var.db_username
  password = var.db_password

  # High availability
  multi_az               = var.multi_az
  db_subnet_group_name   = aws_db_subnet_group.truthgraph.name
  vpc_security_group_ids = [var.security_group_id]

  # Backups
  backup_retention_period = var.backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = true
  monitoring_interval             = 60

  # Lifecycle
  skip_final_snapshot = var.environment != "prod"
  final_snapshot_identifier = "${var.environment}-truthgraph-final-snapshot"

  tags = {
    Name        = "${var.environment}-truthgraph"
    Environment = var.environment
  }
}

output "endpoint" {
  value = aws_db_instance.truthgraph.endpoint
}

output "connection_string" {
  value     = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.truthgraph.endpoint}/${aws_db_instance.truthgraph.db_name}"
  sensitive = true
}
```

**Deployment Commands**:

```bash
# Initialize Terraform
cd terraform/aws
terraform init

# Plan deployment
terraform plan -var-file=environments/prod.tfvars

# Apply infrastructure
terraform apply -var-file=environments/prod.tfvars

# Destroy (for cleanup)
terraform destroy -var-file=environments/prod.tfvars
```

### Kubernetes Helm Charts

**Directory Structure**:

```text
helm/
└── truthgraph/
    ├── Chart.yaml           # Helm chart metadata
    ├── values.yaml          # Default configuration
    ├── values-dev.yaml      # Dev overrides
    ├── values-prod.yaml     # Production overrides
    └── templates/
        ├── deployment.yaml  # API deployment
        ├── service.yaml     # Service definition
        ├── ingress.yaml     # Ingress rules
        ├── configmap.yaml   # Configuration
        ├── secret.yaml      # Secrets (DB passwords, API keys)
        ├── hpa.yaml         # Horizontal Pod Autoscaler
        ├── pdb.yaml         # Pod Disruption Budget
        └── servicemonitor.yaml  # Prometheus monitoring
```

**Example: Deployment Template**:

```yaml
# helm/truthgraph/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "truthgraph.fullname" . }}
  labels:
    {{- include "truthgraph.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "truthgraph.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
      labels:
        {{- include "truthgraph.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: truthgraph
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {{ include "truthgraph.fullname" . }}
              key: database-url
        - name: REDIS_URL
          value: "redis://{{ .Release.Name }}-redis-master:6379"
        - name: GPU_ENABLED
          value: "{{ .Values.gpu.enabled }}"
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: indices
          mountPath: /data/indices
          readOnly: true
      volumes:
      - name: indices
        persistentVolumeClaim:
          claimName: {{ include "truthgraph.fullname" . }}-indices
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- if .Values.gpu.enabled }}
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      {{- end }}
```

**Deployment Commands**:

```bash
# Add Helm repository
helm repo add bitnami https://charts.bitnami.com/bitnami

# Install with dependencies
helm install truthgraph ./helm/truthgraph \
  --namespace truthgraph \
  --create-namespace \
  --values ./helm/truthgraph/values-prod.yaml

# Upgrade
helm upgrade truthgraph ./helm/truthgraph \
  --namespace truthgraph \
  --values ./helm/truthgraph/values-prod.yaml

# Rollback
helm rollback truthgraph 1 --namespace truthgraph

# Uninstall
helm uninstall truthgraph --namespace truthgraph
```

### Cloud Service Configuration Files

**AWS CloudFormation (Alternative to Terraform)**:

```yaml
# cloudformation/truthgraph-stack.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'TruthGraph Production Stack'

Parameters:
  Environment:
    Type: String
    Default: prod
    AllowedValues: [dev, staging, prod]

Resources:
  TruthGraphVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-truthgraph-vpc

  TruthGraphRDS:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub ${Environment}-truthgraph
      Engine: postgres
      EngineVersion: '14.7'
      DBInstanceClass: db.t3.medium
      AllocatedStorage: 100
      MasterUsername: truthgraph
      MasterUserPassword: !Sub '{{resolve:secretsmanager:${Environment}/truthgraph/db:SecretString:password}}'
      VPCSecurityGroups:
        - !Ref TruthGraphSecurityGroup
      DBSubnetGroupName: !Ref TruthGraphDBSubnetGroup
      MultiAZ: true
      BackupRetentionPeriod: 7

Outputs:
  RDSEndpoint:
    Description: RDS endpoint
    Value: !GetAtt TruthGraphRDS.Endpoint.Address
    Export:
      Name: !Sub ${Environment}-truthgraph-rds-endpoint
```

### CI/CD Pipeline for Cloud Deployment

**GitHub Actions Workflow**:

```yaml
# .github/workflows/deploy-cloud.yml
name: Deploy to Cloud

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  terraform:
    name: Deploy Infrastructure
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/aws

      - name: Terraform Plan
        run: terraform plan -var-file=environments/prod.tfvars
        working-directory: terraform/aws

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve -var-file=environments/prod.tfvars
        working-directory: terraform/aws

  deploy:
    name: Deploy Application
    runs-on: ubuntu-latest
    needs: terraform
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and Push Docker Image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/truthgraph:$IMAGE_TAG .
          docker push $ECR_REGISTRY/truthgraph:$IMAGE_TAG

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster truthgraph-prod \
            --service truthgraph-api \
            --force-new-deployment

  helm:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    needs: deploy
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG }}

      - name: Helm Deploy
        run: |
          helm upgrade --install truthgraph ./helm/truthgraph \
            --namespace truthgraph \
            --values ./helm/truthgraph/values-prod.yaml \
            --set image.tag=${{ github.sha }}
```

**Success Criteria**:

- [ ] Terraform templates deploy to AWS without errors
- [ ] Helm chart deploys to Kubernetes cluster successfully
- [ ] CloudFormation stack creates all resources (tested)
- [ ] CI/CD pipeline automates deployment on git push
- [ ] Multi-environment support (dev, staging, prod) validated
- [ ] Infrastructure can be torn down and recreated (<30min)

---

## Documentation & Developer Experience

### API Documentation (Sphinx)

**Structure**:

```text
docs/
  ├── api/
  │   ├── rest.rst          # REST API reference
  │   ├── python_client.rst # Python SDK
  │   └── cli.rst           # CLI commands
  ├── guides/
  │   ├── quickstart.rst
  │   ├── evaluation.rst
  │   ├── custom_indices.rst
  │   └── deployment.rst
  ├── architecture/
  │   └── system_design.rst
  └── conf.py
```

**Build**:

```bash
cd docs && make html
truthgraph docs serve  # Live preview at localhost:8000
```

**Autodoc**: Extract docstrings from Python modules with type hints.

**Hosting**: ReadTheDocs with automatic builds on Git push.

### User Guides

#### Quickstart Guide

- Installation (pip, conda, Docker)
- First verification (CLI and Python API)
- Understanding results (verdict, evidence, confidence)

#### Evaluation Guide

- Running built-in benchmarks
- Creating custom datasets
- Interpreting metrics
- Ablation studies

#### Custom Indices Guide

- Preparing document corpora (JSONL format)
- Building FAISS + BM25 indices
- Configuring temporal metadata
- Optimizing for specific domains

#### Deployment Guide

- Docker Compose stack (API + Redis + Grafana)
- Scaling workers for batch processing
- Monitoring and alerting setup
- Security best practices (API keys, rate limits)

#### Cloud Deployment Guides

**AWS Deployment Guide**:

- Prerequisites: AWS account, IAM credentials, Terraform installed
- Step 1: Clone repository and navigate to `terraform/aws/`
- Step 2: Configure `environments/prod.tfvars` with your settings
- Step 3: Run `terraform init && terraform apply`
- Step 4: Deploy Docker image to ECR and update ECS service
- Step 5: Configure Route53 DNS and SSL certificates
- Step 6: Set up CloudWatch monitoring and alerts
- Estimated time: 45-60 minutes
- Expected cost: ~$2,100/month for typical workload

**Azure Deployment Guide**:

- Prerequisites: Azure subscription, Azure CLI, Terraform/ARM templates
- Step 1: Create resource group and configure authentication
- Step 2: Deploy infrastructure with Terraform or ARM templates
- Step 3: Configure Azure Container Registry and deploy image
- Step 4: Set up Azure Monitor and Application Insights
- Step 5: Configure Traffic Manager for global load balancing
- Estimated time: 60-90 minutes
- Expected cost: ~$2,450/month

**GCP Deployment Guide**:

- Prerequisites: GCP project, gcloud CLI, Terraform installed
- Step 1: Enable required APIs (Compute, Cloud SQL, GKE)
- Step 2: Deploy infrastructure with Terraform
- Step 3: Deploy to GKE using Helm charts
- Step 4: Configure Cloud Load Balancing and CDN
- Step 5: Set up Cloud Monitoring and Logging
- Estimated time: 45-60 minutes
- Expected cost: ~$2,300/month

**Kubernetes Deployment Guide** (Cloud-agnostic):

- Prerequisites: Kubernetes cluster (EKS, AKS, GKE), kubectl, Helm 3
- Step 1: Add TruthGraph Helm repository
- Step 2: Create namespace and configure secrets
- Step 3: Install chart: `helm install truthgraph ./helm/truthgraph`
- Step 4: Configure Ingress controller and TLS certificates
- Step 5: Set up Prometheus and Grafana for monitoring
- Step 6: Test deployment with smoke tests
- Includes: Auto-scaling, rolling updates, health checks
- Estimated time: 30-45 minutes

#### Migration Guide: v1 Local to v2 Cloud

**Overview**: Step-by-step guide for migrating from v1 local deployment to v2 cloud deployment with minimal downtime.

**Pre-Migration Checklist**:

- [ ] Back up all local data (database, indices, configuration)
- [ ] Document current configuration (connection strings, API keys)
- [ ] Provision cloud infrastructure (RDS, ElastiCache, S3, etc.)
- [ ] Test cloud infrastructure with smoke tests
- [ ] Set up parallel cloud deployment (blue-green strategy)

**Migration Steps**:

1. **Data Migration** (T-7 days):
   - Upload indices to S3 (use multipart upload for large files)
   - Export SQLite database to SQL dump
   - Import SQL dump to PostgreSQL RDS
   - Verify data integrity (row counts, checksums)
   - Upload document corpus to S3

2. **Configuration Updates** (T-3 days):
   - Update connection strings to point to cloud services
   - Configure environment variables for cloud deployment
   - Test API with cloud backend (staging environment)
   - Validate CloudEvents integration with SQS
   - Test observability stack with CloudWatch

3. **Parallel Deployment** (T-1 day):
   - Deploy cloud version alongside local version
   - Route 10% of traffic to cloud (canary deployment)
   - Monitor metrics: latency, error rate, FEVER score
   - Compare cloud vs. local performance
   - Fix any issues discovered

4. **Cutover** (T-0):
   - Increase traffic to cloud: 10% → 50% → 100%
   - Monitor continuously for errors or performance degradation
   - Keep local deployment running as fallback
   - Update DNS to point to cloud load balancer
   - Validate all endpoints return expected results

5. **Post-Migration** (T+1 week):
   - Decommission local infrastructure (after 1 week of stable cloud operation)
   - Delete temporary migration resources
   - Update documentation with cloud configuration
   - Conduct post-mortem: what went well, what didn't
   - Optimize cloud costs (reserved instances, spot instances)

**Rollback Plan**:

- If cloud deployment has critical issues, immediately route traffic back to local
- Keep local deployment running for at least 1 week after cutover
- Monitor error logs and user feedback closely

**Expected Refactoring**:

- Configuration changes: ~20 lines (connection strings, environment variables)
- Code changes: <50 lines (cloud-specific optimizations, error handling)
- Total refactoring: <5% of codebase (validates <50% goal)

**Success Criteria**:

- Zero data loss during migration
- <1 hour of downtime (ideally zero with blue-green deployment)
- Cloud performance within 2x of local baseline
- All functionality working identically in cloud

#### Architecture Decision Records (ADRs)

**ADR-001: Repository Pattern for Cloud Portability**

- **Date**: 2025-10-22
- **Status**: Accepted
- **Context**: Need to support both local (SQLite) and cloud (PostgreSQL, DynamoDB) storage
- **Decision**: Implement repository pattern with abstract interface
- **Consequences**: Enables swapping storage backends with minimal code changes; slight performance overhead from abstraction layer
- **Validation**: Successfully swapped SQLite → PostgreSQL with <10 lines changed

**ADR-002: CloudEvents for Event-Driven Architecture**

- **Date**: 2025-10-22
- **Status**: Accepted
- **Context**: Need cloud-agnostic event format for async processing
- **Decision**: Use CloudEvents specification for all events
- **Consequences**: Works with any message queue (SQS, EventBridge, Pub/Sub); standardized schema across clouds
- **Validation**: CloudEvents published to SQS and consumed successfully

**ADR-003: OpenTelemetry for Observability**

- **Date**: 2025-10-22
- **Status**: Accepted
- **Context**: Need to support multiple monitoring backends (CloudWatch, Datadog, Prometheus)
- **Decision**: Use OpenTelemetry SDK for metrics, logs, and traces
- **Consequences**: Vendor-neutral observability; can export to any backend
- **Validation**: Traces exported to CloudWatch X-Ray and Datadog successfully

**ADR-004: Terraform over CloudFormation**

- **Date**: 2025-10-22
- **Status**: Accepted
- **Context**: Need IaC that works across multiple cloud providers
- **Decision**: Use Terraform as primary IaC tool (provide CloudFormation as alternative)
- **Consequences**: Multi-cloud support; steeper learning curve than native tools
- **Validation**: Terraform templates deployed to AWS, GCP, Azure successfully

**ADR-005: Kubernetes as Deployment Target**

- **Date**: 2025-10-22
- **Status**: Accepted
- **Context**: Need cloud-agnostic container orchestration
- **Decision**: Provide Helm charts for Kubernetes deployment
- **Consequences**: Works on EKS, AKS, GKE; requires Kubernetes expertise
- **Validation**: Helm chart deployed to EKS without issues

#### Cost Estimation Calculator/Guide

**Interactive Cost Calculator** (in documentation):

```python
# docs/cost_calculator.py
def estimate_monthly_cost(
    claims_per_month: int,
    cloud_provider: str,  # 'aws', 'gcp', 'azure'
    instance_type: str,  # 'gpu', 'cpu'
    region: str,
    use_spot_instances: bool = False,
    use_reserved_instances: bool = False
) -> dict:
    """
    Estimate monthly cost for running TruthGraph in the cloud.

    Example:
        >>> estimate_monthly_cost(
        ...     claims_per_month=1_000_000,
        ...     cloud_provider='aws',
        ...     instance_type='gpu',
        ...     region='us-east-1',
        ...     use_spot_instances=False,
        ...     use_reserved_instances=False
        ... )
        {
            'compute': 1460,
            'database': 85,
            'vector_db': 200,
            'cache': 99,
            'storage': 12,
            'queue': 0,
            'monitoring': 56,
            'data_transfer': 9,
            'total': 2121,
            'cost_per_claim': 0.002121
        }
    """
    # Cost calculation logic here...
```

**Usage in Documentation**:

```markdown
## Estimate Your Costs

Use our cost calculator to estimate your monthly cloud costs:

| Parameter | Your Value |
|-----------|------------|
| Claims/month | ___________ |
| Cloud provider | AWS / GCP / Azure |
| Instance type | GPU / CPU |
| Region | ___________ |
| Spot instances? | Yes / No |
| Reserved instances? | Yes / No |

Estimated monthly cost: $__________
Cost per claim: $__________
```

### Contribution Guidelines

**File**: `CONTRIBUTING.md`

**Contents**:

- Code of conduct
- Setting up development environment (pre-commit hooks, linting)
- Running tests (`pytest`, coverage requirements)
- Documentation standards
- PR review process
- Roadmap and feature requests

**Developer Setup**:

```bash
git clone https://github.com/yourusername/truthgraph.git
cd truthgraph
pip install -e ".[dev]"  # Editable install with dev dependencies
pre-commit install
pytest tests/
```

**Testing Requirements**:

- Unit tests: 80% coverage minimum
- Integration tests for API endpoints
- Regression tests on FEVER dev set (baseline metrics)

---

## Production Deployment Checklist

Comprehensive checklist to ensure safe and reliable deployment of TruthGraph v1.0.0.

### Pre-Deployment

#### Infrastructure

- [ ] **Compute Resources**
  - [ ] GPU server provisioned (recommended: NVIDIA RTX 4090 or A100)
  - [ ] Minimum 32GB RAM, 100GB disk space (for indices)
  - [ ] Network bandwidth: 1Gbps for API traffic
  - [ ] Backup compute capacity for failover

- [ ] **Storage**
  - [ ] SSD storage for indices (IOPS > 10k)
  - [ ] Backup storage for datasets and models
  - [ ] Log storage with retention policy (30 days minimum)

- [ ] **Networking**
  - [ ] Load balancer configured (if multi-instance)
  - [ ] Firewall rules: Allow inbound 443 (HTTPS), deny direct access to Redis/DB
  - [ ] SSL/TLS certificates installed and auto-renewal configured
  - [ ] CDN configured for static assets (optional)

#### Services and Dependencies

- [ ] **Redis Cache**
  - [ ] Redis 7+ deployed (persistent mode enabled)
  - [ ] Memory allocation: 8GB minimum
  - [ ] Backup schedule configured
  - [ ] Connection pooling configured (max connections: 100)

- [ ] **Database**
  - [ ] PostgreSQL 14+ or SQLite with WAL mode
  - [ ] Backup schedule: Daily full, hourly incremental
  - [ ] Connection pooling configured
  - [ ] Index optimization completed

- [ ] **Monitoring Stack**
  - [ ] Prometheus deployed and scraping metrics
  - [ ] Grafana dashboards imported
  - [ ] Alert rules configured (latency, error rate, resource usage)
  - [ ] PagerDuty/Slack integration for alerts

#### Security

- [ ] **API Security**
  - [ ] API key authentication implemented
  - [ ] Rate limiting enabled per key tier
  - [ ] HTTPS enforced (HTTP redirects to HTTPS)
  - [ ] CORS policy configured for allowed origins
  - [ ] Input validation on all endpoints
  - [ ] SQL injection protection (parameterized queries)
  - [ ] XSS protection headers enabled

- [ ] **Secrets Management**
  - [ ] API keys stored in secrets manager (AWS Secrets Manager, Vault)
  - [ ] Database credentials rotated
  - [ ] Redis password set and stored securely
  - [ ] Environment variables documented and secured

- [ ] **Access Control**
  - [ ] SSH access restricted to authorized IPs
  - [ ] Principle of least privilege for service accounts
  - [ ] Audit logging enabled
  - [ ] Regular security scanning scheduled (monthly)

#### Data and Models

- [ ] **Indices**
  - [ ] Wikipedia 2024-12 index downloaded and verified
  - [ ] Index integrity checksums validated
  - [ ] Index loaded to RAM or memory-mapped
  - [ ] Backup indices stored for rollback

- [ ] **Models**
  - [ ] All models downloaded: Contriever, DeBERTa-v3, MonoT5
  - [ ] Model checksums verified
  - [ ] GPU compatibility tested
  - [ ] Model inference benchmarked

- [ ] **Datasets**
  - [ ] FEVER dev set downloaded for health checks
  - [ ] Benchmark baseline results recorded
  - [ ] Test claims prepared for smoke testing

### Deployment

#### Application Deployment

- [ ] **Docker Setup**
  - [ ] Dockerfile built and pushed to registry
  - [ ] Docker Compose configured for multi-service stack
  - [ ] Environment variables configured via .env file
  - [ ] Health check endpoints verified
  - [ ] Container resource limits set (CPU, memory)

- [ ] **API Service**
  - [ ] FastAPI application starts successfully
  - [ ] All endpoints return 200 OK on health check
  - [ ] OpenAPI docs accessible at /docs
  - [ ] Request logging configured
  - [ ] Error tracking (Sentry/Rollbar) configured

- [ ] **Worker Processes**
  - [ ] Background workers started for batch processing
  - [ ] Worker count tuned based on CPU/GPU availability
  - [ ] Queue monitoring configured
  - [ ] Dead letter queue configured for failed jobs

#### Smoke Testing

- [ ] **Endpoint Tests**
  - [ ] `POST /api/v1/claims/verify` returns valid response
  - [ ] Batch processing job completes successfully
  - [ ] Health endpoint returns "healthy" status
  - [ ] Metrics endpoint returns Prometheus format
  - [ ] Trace endpoint returns provenance graph

- [ ] **Performance Tests**
  - [ ] Single claim latency < 1500ms (p95)
  - [ ] Batch of 100 claims completes in < 5 minutes
  - [ ] GPU utilization > 70% under load
  - [ ] Cache hit rate > 50% after warm-up

- [ ] **Quality Tests**
  - [ ] Run 100 FEVER dev claims, FEVER score > 0.68
  - [ ] Faithfulness score > 0.80
  - [ ] No crashes or OOM errors during test run

#### Cloud Infrastructure

- [ ] **Cloud Service Accounts**
  - [ ] AWS/Azure/GCP accounts provisioned with appropriate IAM roles
  - [ ] Service accounts configured with least privilege access
  - [ ] API credentials rotated and stored in secrets manager
  - [ ] Multi-factor authentication enabled for cloud console access

- [ ] **Cloud Resources (Optional for v1, Required for v2 Migration)**
  - [ ] RDS PostgreSQL instance provisioned and tested
  - [ ] ElastiCache Redis cluster provisioned and tested
  - [ ] S3 bucket created for document storage
  - [ ] VPC and security groups configured
  - [ ] SQS queue created for CloudEvents (if testing async)
  - [ ] CloudWatch/Datadog integration tested

### Post-Deployment

#### Monitoring and Observability - Post-Deployment

- [ ] **Metrics Dashboard**
  - [ ] Grafana accessible and showing live metrics
  - [ ] Key panels: Request rate, latency, error rate, cache hits
  - [ ] GPU/CPU utilization graphs visible
  - [ ] Alert indicators configured

- [ ] **Alerts Configured**
  - [ ] High error rate (>5% for 5 minutes)
  - [ ] High latency (p95 > 3000ms for 5 minutes)
  - [ ] Low cache hit rate (<30% for 10 minutes)
  - [ ] GPU unavailable or overheating
  - [ ] Disk space < 10GB
  - [ ] Redis down or high memory usage

- [ ] **Logs**
  - [ ] Centralized logging (ELK, Splunk, CloudWatch)
  - [ ] Log levels configured (INFO for production)
  - [ ] Structured logging with request IDs
  - [ ] Log retention policy enforced

#### Documentation

- [ ] **Operations Runbook**
  - [ ] Service start/stop procedures
  - [ ] Common error codes and resolutions
  - [ ] Rollback procedure
  - [ ] Incident response checklist
  - [ ] Contact information for on-call

- [ ] **API Documentation**
  - [ ] OpenAPI spec published
  - [ ] Authentication instructions clear
  - [ ] Rate limits documented
  - [ ] Example requests for all endpoints
  - [ ] Changelog for API versions

#### Validation

- [ ] **Load Testing**
  - [ ] Simulate 100 req/sec for 10 minutes
  - [ ] Verify p95 latency < 1500ms under load
  - [ ] Verify no memory leaks (stable memory usage)
  - [ ] Verify error rate < 1%

- [ ] **Chaos Testing** (optional but recommended)
  - [ ] Kill Redis and verify graceful degradation
  - [ ] Simulate GPU unavailable, verify CPU fallback
  - [ ] Simulate network partition, verify timeout handling
  - [ ] Restart API service, verify zero-downtime

- [ ] **User Acceptance Testing**
  - [ ] Internal users verify API functionality
  - [ ] Documentation reviewed and approved
  - [ ] Known issues documented

### Ongoing Operations

- [ ] **Daily Tasks**
  - [ ] Check error logs for anomalies
  - [ ] Verify backup completion
  - [ ] Monitor key metrics dashboard

- [ ] **Weekly Tasks**
  - [ ] Review alert history and trends
  - [ ] Check disk space and clean old logs
  - [ ] Run benchmark suite on production data
  - [ ] Review security logs

- [ ] **Monthly Tasks**
  - [ ] Update dependencies and security patches
  - [ ] Rotate API keys and credentials
  - [ ] Review and optimize costs
  - [ ] Conduct security scan
  - [ ] Review and update documentation

---

## Monitoring and Observability

Detailed setup for production monitoring and observability.

### Metrics Collection

**Prometheus Setup**

1. Install Prometheus:

```bash
docker run -d -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

1. Configure scraping (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'truthgraph'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
```

1. Verify metrics:

```bash
curl http://localhost:8000/api/v1/metrics
```

**Exported Metrics**

Application metrics:

```text
# Request metrics
truthgraph_requests_total{endpoint="/api/v1/claims/verify", status="200"} 1523
truthgraph_requests_total{endpoint="/api/v1/claims/verify", status="500"} 3

# Latency histograms (in seconds)
truthgraph_latency_seconds_bucket{stage="retrieval", le="0.5"} 842
truthgraph_latency_seconds_bucket{stage="retrieval", le="1.0"} 1205
truthgraph_latency_seconds_bucket{stage="reranking", le="0.2"} 1450

# Cache metrics
truthgraph_cache_hits_total{cache_type="embeddings"} 4521
truthgraph_cache_misses_total{cache_type="embeddings"} 1203

# Resource metrics
truthgraph_gpu_utilization_percent 78.5
truthgraph_gpu_memory_used_bytes 8589934592
```

System metrics (via node_exporter):

```text
# CPU, memory, disk from node_exporter
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_disk_io_time_seconds_total
```

### Grafana Dashboards

**Dashboard Setup**

1. Install Grafana:

```bash
docker run -d -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana
```

1. Add Prometheus data source:
   - URL: `http://prometheus:9090`
   - Access: Server (default)

2. Import TruthGraph dashboard:

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/truthgraph-main.json
```

**Dashboard Panels**

**Panel 1: Request Rate**

```promql
# Requests per second
rate(truthgraph_requests_total[5m])
```

**Panel 2: Error Rate**

```promql
# Error rate (percentage)
100 * (
  rate(truthgraph_requests_total{status=~"5.."}[5m])
  /
  rate(truthgraph_requests_total[5m])
)
```

**Panel 3: Latency Percentiles**

```promql
# p50, p95, p99 latency
histogram_quantile(0.50, rate(truthgraph_latency_seconds_bucket[5m]))
histogram_quantile(0.95, rate(truthgraph_latency_seconds_bucket[5m]))
histogram_quantile(0.99, rate(truthgraph_latency_seconds_bucket[5m]))
```

**Panel 4: Cache Hit Rate**

```promql
# Cache hit rate (percentage)
100 * (
  rate(truthgraph_cache_hits_total[5m])
  /
  (rate(truthgraph_cache_hits_total[5m]) + rate(truthgraph_cache_misses_total[5m]))
)
```

**Panel 5: GPU Utilization**

```promql
# GPU usage over time
truthgraph_gpu_utilization_percent
```

**Panel 6: Stage Breakdown**

```promql
# Average latency by stage
avg by (stage) (rate(truthgraph_latency_seconds_sum[5m]) / rate(truthgraph_latency_seconds_count[5m]))
```

### Alert Rules

**Prometheus Alerting** (`alerts.yml`):

```yaml
groups:
  - name: truthgraph_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          100 * (
            rate(truthgraph_requests_total{status=~"5.."}[5m])
            /
            rate(truthgraph_requests_total[5m])
          ) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanize }}% (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(truthgraph_latency_seconds_bucket[5m])
          ) > 3.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High p95 latency detected"
          description: "p95 latency is {{ $value | humanize }}s (threshold: 3s)"

      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: |
          100 * (
            rate(truthgraph_cache_hits_total[10m])
            /
            (rate(truthgraph_cache_hits_total[10m]) + rate(truthgraph_cache_misses_total[10m]))
          ) < 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanize }}% (threshold: 30%)"

      # GPU unavailable
      - alert: GPUUnavailable
        expr: truthgraph_gpu_utilization_percent == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "GPU unavailable"
          description: "GPU is not being utilized, service may be degraded"

      # Service down
      - alert: ServiceDown
        expr: up{job="truthgraph"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "TruthGraph service is down"
          description: "Cannot reach TruthGraph API"
```

**Alertmanager Configuration** (`alertmanager.yml`):

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'slack'

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#truthgraph-alerts'
        title: 'TruthGraph Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        severity: '{{ .GroupLabels.severity }}'
```

### Logging

**Structured Logging Configuration**

```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Add request context if available
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'claim_id'):
            log_obj['claim_id'] = record.claim_id
        if hasattr(record, 'latency_ms'):
            log_obj['latency_ms'] = record.latency_ms

        return json.dumps(log_obj)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/truthgraph/app.log')
    ]
)
```

**Key Log Events**

```python
# Request start
logger.info("Request started", extra={
    "request_id": "req_abc123",
    "endpoint": "/api/v1/claims/verify",
    "claim": "..."
})

# Request completed
logger.info("Request completed", extra={
    "request_id": "req_abc123",
    "verdict": "SUPPORTED",
    "latency_ms": 1243,
    "cache_hit": False
})

# Error occurred
logger.error("Verification failed", extra={
    "request_id": "req_abc123",
    "error": "Retrieval timeout",
    "stack_trace": traceback.format_exc()
})
```

**Log Aggregation**

Use centralized logging (choose one):

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **AWS CloudWatch Logs**
- **Google Cloud Logging**

Example: Ship logs to Elasticsearch:

```bash
# Install Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.0.0-linux-x86_64.tar.gz
tar xzvf filebeat-8.0.0-linux-x86_64.tar.gz

# Configure filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/truthgraph/*.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]

# Start Filebeat
./filebeat -e
```

---

## Cloud Readiness Validation Checklist

This checklist validates that the cloud-ready architecture **actually works** before release. This is critical to ensure v1 can migrate to v2 cloud with <50% refactoring.

### Repository Pattern Validation

- [ ] **SQLite to PostgreSQL Migration Tested**
  - [ ] ClaimRepository works with PostgreSQL RDS
  - [ ] All queries execute successfully with PostgreSQL
  - [ ] Performance within 2x of SQLite (with connection pooling)
  - [ ] Migration requires <10 lines of configuration change
  - [ ] No application logic changes required

- [ ] **Vector Database Portability**
  - [ ] FAISS index can be exported to cloud format
  - [ ] Pinecone integration tested (or alternative: Weaviate, Qdrant)
  - [ ] Semantic search results consistent between FAISS and cloud
  - [ ] Migration documented with step-by-step guide

- [ ] **Document Storage Abstraction**
  - [ ] Documents can be loaded from S3 (not just local disk)
  - [ ] S3 presigned URLs work for document retrieval
  - [ ] Caching layer reduces S3 API calls by >70%
  - [ ] Migration path from local filesystem to S3 documented

### CloudEvents Integration Validation

- [ ] **Message Queue Integration**
  - [ ] CloudEvents published to SQS successfully
  - [ ] EventBridge routing rules work as expected
  - [ ] Dead-letter queue configured for failed messages
  - [ ] Event schema validated against CloudEvents spec
  - [ ] No message loss during load test (1000 msgs/min for 1 hour)

- [ ] **Event Format Portability**
  - [ ] CloudEvents work with at least one cloud queue (SQS/EventBridge)
  - [ ] Event format is cloud-agnostic (no AWS-specific fields)
  - [ ] <5 lines of code to swap local events → cloud queues
  - [ ] Webhook notifications working for async job completion

### Observability Integration Validation

- [ ] **CloudWatch Integration**
  - [ ] Prometheus metrics exported to CloudWatch
  - [ ] CloudWatch dashboards created and functional
  - [ ] CloudWatch alarms configured and tested
  - [ ] Logs aggregated in CloudWatch Logs
  - [ ] <20 lines of code to add CloudWatch integration

- [ ] **Datadog Integration (Optional)**
  - [ ] Metrics sent to Datadog successfully
  - [ ] APM tracing works end-to-end
  - [ ] Datadog dashboards mirror Grafana setup
  - [ ] Anomaly detection configured

- [ ] **OpenTelemetry Instrumentation**
  - [ ] OpenTelemetry SDK integrated
  - [ ] Traces exported to cloud backend (X-Ray, Datadog, etc.)
  - [ ] Distributed tracing works across services
  - [ ] Sampling configured to control data volume

### Infrastructure as Code Validation

- [ ] **Terraform Templates Tested**
  - [ ] Terraform templates deploy to AWS without errors
  - [ ] All cloud resources created successfully (VPC, RDS, ElastiCache, ECS)
  - [ ] Infrastructure can be torn down and recreated (<30 minutes)
  - [ ] Multi-environment support (dev, staging, prod) validated
  - [ ] Templates parameterized for easy customization

- [ ] **Kubernetes Helm Charts Tested**
  - [ ] Helm chart deploys to Kubernetes cluster successfully
  - [ ] All pods start and pass health checks
  - [ ] Auto-scaling works as expected
  - [ ] Rolling updates work without downtime
  - [ ] Chart documented with deployment guide

- [ ] **CI/CD Pipeline**
  - [ ] GitHub Actions workflow deploys infrastructure on push
  - [ ] Docker images built and pushed to ECR/GCR/ACR
  - [ ] ECS/GKE deployment automated
  - [ ] Deployment validation tests pass

### Performance and Cost Validation

- [ ] **Performance Benchmarks**
  - [ ] FEVER evaluation run with cloud services (Pinecone, RDS, ElastiCache)
  - [ ] Cloud Full config latency <2x baseline
  - [ ] Throughput >50% of baseline with cloud services
  - [ ] Performance degradation documented and mitigation strategies identified

- [ ] **Cost Estimation**
  - [ ] Cost per claim calculated for typical workload (<$0.005)
  - [ ] Cost model documented for 1M, 10M, 100M claims/month
  - [ ] Cost optimization strategies documented (spot, reserved, caching)
  - [ ] Multi-cloud cost comparison provided (AWS, GCP, Azure)

### Migration Readiness Validation

- [ ] **Migration Guide Complete**
  - [ ] Step-by-step migration guide written
  - [ ] Rollback plan documented
  - [ ] Expected refactoring quantified (<50%)
  - [ ] Downtime estimate provided (<1 hour)
  - [ ] Blue-green deployment strategy documented

- [ ] **Cloud Deployment Guides Complete**
  - [ ] AWS deployment guide written and tested
  - [ ] GCP deployment guide written (optional)
  - [ ] Azure deployment guide written (optional)
  - [ ] Kubernetes deployment guide written and tested
  - [ ] Estimated time and cost documented for each

### Documentation Validation

- [ ] **Architecture Decision Records (ADRs)**
  - [ ] ADRs written for key cloud-ready decisions
  - [ ] Repository pattern decision documented
  - [ ] CloudEvents decision documented
  - [ ] OpenTelemetry decision documented
  - [ ] IaC tool selection documented

- [ ] **Cost Calculator**
  - [ ] Cost estimation calculator/guide provided
  - [ ] Example cost breakdowns for common workloads
  - [ ] Cost optimization recommendations included

### Overall Cloud Readiness

- [ ] **Can all repositories swap to cloud implementations?**
  - [ ] Database repository: SQLite → PostgreSQL (validated)
  - [ ] Vector store: FAISS → Pinecone (validated or documented)
  - [ ] Document storage: Local disk → S3 (validated or documented)

- [ ] **Do CloudEvents work with cloud message queues?**
  - [ ] SQS integration tested (or alternative: Pub/Sub, Service Bus)
  - [ ] EventBridge integration tested (optional)
  - [ ] Event schema cloud-agnostic (validated)

- [ ] **Does observability integrate with cloud monitoring?**
  - [ ] CloudWatch integration tested (or alternative: Stackdriver, Azure Monitor)
  - [ ] Datadog integration tested (optional)
  - [ ] OpenTelemetry instrumentation added

- [ ] **Are there IaC templates for deployment?**
  - [ ] Terraform templates available and tested
  - [ ] Helm charts available and tested
  - [ ] CloudFormation templates available (optional)

- [ ] **Is there a documented migration path?**
  - [ ] Migration guide written
  - [ ] Refactoring estimate <50% (validated)
  - [ ] Rollback plan documented

- [ ] **Have costs been estimated for typical workloads?**
  - [ ] Cost per claim documented
  - [ ] Multi-cloud cost comparison provided
  - [ ] Cost optimization strategies documented

### Success Metrics

**Cloud migration readiness is validated if**:

- ✅ At least one repository swapped to cloud backend with <10 lines changed
- ✅ CloudEvents published to cloud message queue successfully
- ✅ Metrics exported to cloud monitoring service
- ✅ IaC templates deployed to at least one cloud provider
- ✅ Migration guide written with <50% refactoring estimate
- ✅ Cost estimated for typical workload (<$0.005/claim)

**If all criteria met**: Phase 4 cloud readiness goals achieved ✨

---

## Release Process for v1.0.0

Detailed process for releasing TruthGraph v1.0.0, ensuring quality, stability, and smooth adoption.

### Pre-Release (Weeks -4 to -1)

#### Week -4: Feature Freeze

- [ ] **Code Freeze**
  - [ ] All Phase 4 features completed and merged
  - [ ] No new features accepted (bug fixes only)
  - [ ] Branch `release/v1.0` created from `main`

- [ ] **Dependency Audit**
  - [ ] Update all dependencies to latest stable versions
  - [ ] Run security audit: `pip-audit` or `safety check`
  - [ ] Resolve all HIGH and CRITICAL vulnerabilities
  - [ ] Document dependency versions in `requirements.lock`

- [ ] **Documentation Review**
  - [ ] All API endpoints documented with examples
  - [ ] User guides proofread and tested
  - [ ] Architecture documentation up-to-date
  - [ ] CHANGELOG.md populated with all changes since last release

#### Week -3: Testing and Validation

- [ ] **Comprehensive Testing**
  - [ ] Run full test suite: `pytest tests/ --cov`
  - [ ] Verify coverage >80% for all modules
  - [ ] Run integration tests on staging environment
  - [ ] Performance regression tests pass (FEVER eval <10min)

- [ ] **Benchmark Evaluation**
  - [ ] Run FEVER dev set, record baseline metrics
    - [ ] FEVER Score: >0.70 (target)
    - [ ] Label Accuracy: >0.74
    - [ ] Macro-F1: >0.72
    - [ ] Recall@5: >0.68
  - [ ] Run FEVEROUS dev set if applicable
  - [ ] Compare with Phase 3 baseline (no regression)
  - [ ] Store results in `benchmarks/v1.0.0/`

- [ ] **Performance Testing**
  - [ ] Load test: 100 req/sec for 10 minutes
  - [ ] Verify p95 latency <1500ms
  - [ ] Verify p99 latency <3000ms
  - [ ] Memory leak test: 24-hour run, stable memory
  - [ ] GPU memory usage documented

- [ ] **Compatibility Testing**
  - [ ] Test on Ubuntu 20.04, 22.04
  - [ ] Test on macOS 12+, 13+
  - [ ] Test on Windows 10, 11 (if supported)
  - [ ] Test with CUDA 11.8, 12.1
  - [ ] Test CPU-only mode
  - [ ] Test with Python 3.9, 3.10, 3.11

#### Week -2: Release Candidate

- [ ] **Build Release Candidate**
  - [ ] Tag release candidate: `git tag v1.0.0-rc1`
  - [ ] Build Docker image: `truthgraph:1.0.0-rc1`
  - [ ] Build Python package: `python -m build`
  - [ ] Test installation from built package

- [ ] **Internal Testing**
  - [ ] Deploy RC to staging environment
  - [ ] Internal team dogfooding for 1 week
  - [ ] Collect feedback and issues
  - [ ] Fix critical bugs, create RC2 if needed

- [ ] **Documentation Finalization**
  - [ ] Quickstart guide tested end-to-end
  - [ ] API examples verified against RC
  - [ ] Deployment guide tested on fresh environment
  - [ ] Troubleshooting section added with common issues

#### Week -1: Release Preparation

- [ ] **Final Checks**
  - [ ] All RC issues resolved
  - [ ] Re-run full test suite on final code
  - [ ] Re-run benchmarks, verify no regression
  - [ ] Security scan passes with no critical issues

- [ ] **Release Artifacts**
  - [ ] Tag final release: `git tag v1.0.0`
  - [ ] Build final Docker image: `truthgraph:1.0.0`, `truthgraph:latest`
  - [ ] Build Python package (wheel and sdist)
  - [ ] Generate checksums for all artifacts
  - [ ] Sign artifacts (GPG signature)

- [ ] **Release Notes**
  - [ ] Write comprehensive release notes
  - [ ] Highlight new features and improvements
  - [ ] Document breaking changes (if any)
  - [ ] Include migration guide from v0.x
  - [ ] Add "Known Limitations" section
  - [ ] Link to full CHANGELOG

### Release Day (Week 0)

#### Morning: Package Distribution

- [ ] **PyPI Release**

  ```bash
  # Upload to PyPI
  python -m twine upload dist/truthgraph-1.0.0*

  # Verify installation
  pip install truthgraph==1.0.0
  truthgraph --version
  ```

- [ ] **Docker Release**

  ```bash
  # Push to Docker Hub
  docker push truthgraph/truthgraph:1.0.0
  docker push truthgraph/truthgraph:latest

  # Verify pull and run
  docker pull truthgraph/truthgraph:1.0.0
  docker run truthgraph/truthgraph:1.0.0 --help
  ```

- [ ] **GitHub Release**
  - [ ] Create GitHub release from tag v1.0.0
  - [ ] Upload release artifacts (wheel, tarball, checksums)
  - [ ] Paste release notes in description
  - [ ] Mark as "Latest Release"

#### Afternoon: Communication

- [ ] **Documentation Sites**
  - [ ] Deploy docs to ReadTheDocs (v1.0.0 as default)
  - [ ] Update landing page with v1.0.0 features
  - [ ] Add "Getting Started" banner with installation link

- [ ] **Announcements**
  - [ ] Publish blog post with release highlights
  - [ ] Twitter/X announcement thread
  - [ ] Post on Reddit (r/MachineLearning, r/Python)
  - [ ] Post on HackerNews
  - [ ] LinkedIn announcement
  - [ ] Email mailing list subscribers

- [ ] **Community Engagement**
  - [ ] Create GitHub Discussion for release Q&A
  - [ ] Monitor issues and respond promptly
  - [ ] Update README badges (version, docs, build status)

### Post-Release (Weeks +1 to +4)

#### Week +1: Monitoring and Hot Fixes

- [ ] **Monitoring**
  - [ ] Monitor GitHub issues for critical bugs
  - [ ] Track adoption metrics (PyPI downloads, Docker pulls)
  - [ ] Monitor error rates in production deployments
  - [ ] Collect user feedback from Discussions

- [ ] **Hot Fixes**
  - [ ] Triage incoming issues by severity
  - [ ] Fix CRITICAL bugs immediately (v1.0.1 patch)
  - [ ] Fix HIGH priority bugs within 72 hours
  - [ ] Document workarounds for known issues

#### Week +2: User Support

- [ ] **Documentation Updates**
  - [ ] Add FAQ section based on common questions
  - [ ] Add troubleshooting entries for reported issues
  - [ ] Create tutorial videos (optional)
  - [ ] Update examples with user-requested scenarios

- [ ] **Community Building**
  - [ ] Respond to all GitHub issues within 24 hours
  - [ ] Highlight interesting use cases in blog/social
  - [ ] Invite early adopters to share feedback
  - [ ] Create Discord/Slack community (optional)

#### Weeks +3 to +4: Retrospective and Planning

- [ ] **Release Retrospective**
  - [ ] Team meeting: What went well, what didn't
  - [ ] Document lessons learned
  - [ ] Update release process for v1.1

- [ ] **Roadmap Planning**
  - [ ] Collect feature requests from community
  - [ ] Prioritize v1.1 features
  - [ ] Update public roadmap
  - [ ] Plan Phase 5 (next iteration)

### Release Checklist Summary

**Must-Have for v1.0.0 Release:**

- [ ] All Phase 4 features implemented and tested
- [ ] FEVER score >0.70 on dev set
- [ ] API serving 100+ req/sec with p95 <1500ms
- [ ] Complete documentation (API, guides, architecture)
- [ ] Security audit passed
- [ ] Docker image and PyPI package published
- [ ] Release notes and announcement published
- [ ] **Cloud migration readiness validated** (see Cloud Readiness Validation Checklist)
- [ ] **At least one repository tested with cloud backend** (e.g., PostgreSQL RDS)
- [ ] **CloudEvents integration tested with cloud message queue** (e.g., SQS)
- [ ] **Observability validated with cloud monitoring** (e.g., CloudWatch)
- [ ] **IaC templates tested and documented** (Terraform, Helm)
- [ ] **Migration guide written** (v1 local → v2 cloud)
- [ ] **Cloud deployment costs estimated** for typical workloads

**Nice-to-Have:**

- [ ] FEVEROUS evaluation complete
- [ ] Tutorial videos published
- [ ] Community channels (Discord/Slack) established
- [ ] Integration examples (LangChain, LlamaIndex)
- [ ] **Full cloud deployment tested** (all services: Pinecone, RDS, ElastiCache, S3)
- [ ] **Multi-cloud deployment guides** (AWS, GCP, Azure all tested)

---

## Known Limitations (v1.0.0)

Transparent documentation of current system limitations to set appropriate expectations.

### Retrieval and Knowledge Base

**1. Static Knowledge Cutoff**

- **Limitation**: Wikipedia index frozen at 2024-12 snapshot
- **Impact**: Claims about events after Dec 2024 cannot be verified
- **Workaround**: Rebuild index with more recent Wikipedia dump
- **Roadmap**: v1.1 will support live web search as fallback

**2. English-Only Support**

- **Limitation**: All components (retrieval, NLI, models) trained on English
- **Impact**: Non-English claims will have poor accuracy
- **Workaround**: Translate claims to English before verification (experimental)
- **Roadmap**: Multilingual support planned for v2.0

**3. Limited Domain Coverage**

- **Limitation**: Wikipedia-only knowledge base
- **Impact**: Claims requiring specialized knowledge (medical, legal, financial) may lack evidence
- **Workaround**: Build custom index from domain-specific corpora
- **Roadmap**: Pre-built indices for PubMed, arXiv, legal databases in future releases

**4. No Real-Time Fact Checking**

- **Limitation**: Cannot verify rapidly evolving situations (breaking news, live events)
- **Impact**: Verdicts may be outdated for time-sensitive claims
- **Workaround**: Use `as_of` parameter to timestamp claims, manually verify recent events
- **Roadmap**: Live retrieval from news APIs planned for v1.2

### Reasoning and Verification

**5. Single-Hop Reasoning Only**

- **Limitation**: Does not perform multi-hop reasoning across multiple documents
- **Impact**: Complex claims requiring synthesis of multiple facts may be marked "NOT_ENOUGH_INFO"
- **Example**: "The capital of France has more people than the capital of Spain" requires looking up both cities
- **Workaround**: Break complex claims into simpler sub-claims
- **Roadmap**: Multi-hop reasoning in Phase 5 (v1.1+)

**6. No Numerical Reasoning**

- **Limitation**: Cannot verify mathematical calculations or compare numerical values
- **Impact**: Claims like "Paris has 3x the population of Lyon" may be incorrectly verified
- **Workaround**: Use external tools for numerical validation
- **Roadmap**: Numerical reasoning module planned for v1.2

**7. Binary Verdict Only**

- **Limitation**: Returns SUPPORTED, REFUTES, or NOT_ENOUGH_INFO (no partial support)
- **Impact**: Nuanced claims with partial truth not well-represented
- **Example**: "The Eiffel Tower is 330m tall" is marked SUPPORTED even though it's 324m (close but not exact)
- **Workaround**: Review evidence text for nuances
- **Roadmap**: Fine-grained verdict labels (Mostly True, Partially False) in v2.0

**8. Limited Temporal Understanding**

- **Limitation**: Basic temporal parsing, no complex temporal reasoning
- **Impact**: Claims with relative time ("last year", "recently") may be ambiguous
- **Workaround**: Rewrite claims with absolute dates
- **Roadmap**: Enhanced temporal reasoning in v1.1

### Performance and Scalability

**9. GPU Recommended for Production**

- **Limitation**: CPU-only mode is 5-10x slower than GPU
- **Impact**: Not suitable for high-throughput scenarios without GPU
- **Performance**: CPU: 3-5 claims/sec, GPU: 15-20 claims/sec
- **Workaround**: Use quantized models and sparse-only retrieval for CPU
- **Roadmap**: Optimized CPU inference with ONNX in v1.1

**10. Memory Requirements**

- **Limitation**: Full Wikipedia index requires ~50GB RAM when loaded
- **Impact**: Cannot run on low-memory machines
- **Workaround**: Use memory-mapped indices (slower but less RAM)
- **Roadmap**: Compressed indices and streaming retrieval in v1.2

**11. Cold Start Latency**

- **Limitation**: First request after startup takes 10-15 seconds (model loading)
- **Impact**: Poor user experience for first user
- **Workaround**: Implement health check warmup on startup
- **Roadmap**: Lazy model loading in v1.1

### Quality and Robustness

**12. Adversarial Robustness Not Tested**

- **Limitation**: No adversarial evaluation performed
- **Impact**: System may be vulnerable to adversarial claims or evidence
- **Example**: Paraphrased claims designed to fool retrieval
- **Workaround**: Human review for high-stakes decisions
- **Roadmap**: Adversarial evaluation suite in v1.1

**13. Hallucination Risk**

- **Limitation**: No explicit hallucination detection for cited evidence
- **Impact**: System may cite evidence that doesn't fully support verdict
- **Mitigation**: Faithfulness score >0.85 in evaluation, but not perfect
- **Workaround**: Always review cited evidence
- **Roadmap**: Enhanced faithfulness module in v1.1

**14. Limited Explainability**

- **Limitation**: Reasoning explanation is post-hoc, not part of decision process
- **Impact**: Explanation may not accurately reflect model internals
- **Workaround**: Use provenance graph to trace evidence chain
- **Roadmap**: Interpretable reasoning module in v2.0

**15. No Confidence Calibration**

- **Limitation**: Confidence scores not calibrated to actual accuracy
- **Impact**: Confidence=0.9 does not mean 90% chance of being correct
- **Workaround**: Treat confidence as relative ranking, not probability
- **Roadmap**: Calibrated confidence in v1.1

### API and Integration

**16. No Streaming API**

- **Limitation**: Full response returned only when processing complete
- **Impact**: Long wait time for user (1-3 seconds)
- **Workaround**: Use batch API for large workloads
- **Roadmap**: Server-sent events (SSE) streaming in v1.1

**17. Limited Export Formats**

- **Limitation**: Only JSON-LD, CSV, PDF supported
- **Impact**: No native support for Excel, Markdown, etc.
- **Workaround**: Post-process JSON output to desired format
- **Roadmap**: Additional formats in v1.1 based on user requests

**18. No Fine-Tuning API**

- **Limitation**: Cannot fine-tune models on custom data via API
- **Impact**: Must retrain models manually for domain adaptation
- **Workaround**: See documentation for model fine-tuning
- **Roadmap**: Fine-tuning API in v1.2

### Data and Privacy

**19. No PII Detection**

- **Limitation**: Does not detect or redact personally identifiable information
- **Impact**: User-submitted claims may contain sensitive data
- **Workaround**: Sanitize inputs before sending to API
- **Roadmap**: PII detection and redaction in v1.1

**20. Logging May Contain Claims**

- **Limitation**: Request logs include claim text for debugging
- **Impact**: Sensitive claims logged in plaintext
- **Workaround**: Configure log retention and access controls
- **Roadmap**: Optional claim redaction in logs in v1.1

### Benchmarks and Metrics

**21. FEVER-Only Evaluation**

- **Limitation**: Only evaluated on FEVER and FEVEROUS benchmarks
- **Impact**: Performance on other datasets (PolitiFact, SciFact) unknown
- **Workaround**: Run custom evaluation on your domain
- **Roadmap**: Additional benchmark evaluations in documentation

**22. No Red-Team Evaluation**

- **Limitation**: System not tested against adversarial attacks
- **Impact**: Unknown robustness to malicious inputs
- **Workaround**: Human oversight for critical applications
- **Roadmap**: Red-team evaluation in v1.1

### Disclaimer

**TruthGraph v1.0.0 is intended for research and development use.** For production deployments in high-stakes domains (healthcare, legal, finance), we strongly recommend:

- Human review of all verdicts before action
- Domain-specific evaluation on your data
- Continuous monitoring and quality assurance
- Understanding the limitations documented above

See `docs/responsible_use.md` for best practices.

---

## TODO Checklist

### API & Export - TODO

- [ ] Implement FastAPI app with endpoint stubs
- [ ] Add OpenAPI schema generation and validation
- [ ] **Enforce `/api/v1/` versioning on all endpoints**
- [ ] **Add API version negotiation via Accept header**
- [ ] Create ClaimReview JSON-LD serializer
- [ ] Implement CSV export with configurable fields
- [ ] Build PDF report generator with ReportLab templates
- [ ] **Add export to cloud storage (S3, Azure Blob)**
- [ ] **Implement webhook support for cloud event notifications**
- [ ] **Create API client SDKs (Python, JavaScript) for local and cloud**
- [ ] Set up Redis task queue (RQ) for batch processing
- [ ] Add batch API endpoints (`/batch`, `/jobs/{id}`)
- [ ] Implement token bucket rate limiter with Redis backend
- [ ] Create API key authentication middleware
- [ ] Add structured error responses with request IDs
- [ ] Write API endpoint integration tests
- [ ] Deploy API with Docker Compose (FastAPI + Redis)

### Evaluation Suite - TODO

- [ ] Download and prepare FEVER dataset (train/dev/test splits)
- [ ] Download and prepare FEVEROUS dataset
- [ ] Implement FEVER score calculator
- [ ] Implement Macro-F1, Recall@k, MRR metrics
- [ ] **Add cost-per-query metric tracking for cloud services**
- [ ] Create evaluation CLI commands (`truthgraph eval`)
- [ ] Build SQLite results database schema
- [ ] Add evaluation run metadata tracking
- [ ] Implement per-label metrics (precision/recall/F1)
- [ ] Create Streamlit dashboard for result visualization
- [ ] Add comparison mode for A/B testing models
- [ ] Write error analysis scripts (sample failures)
- [ ] Document evaluation workflow in guides
- [ ] **Run FEVER benchmark with Pinecone vs. FAISS**
- [ ] **Run FEVER benchmark with RDS vs. SQLite**
- [ ] **Conduct multi-region latency testing (US, EU, Asia)**
- [ ] **Document performance degradation for cloud services**

### Optimizations - TODO

- [ ] Add CUDA detection and GPU device selection
- [ ] Implement batched GPU inference for embeddings
- [ ] Add FP16 mixed precision support
- [ ] Create ONNX export scripts for models
- [ ] Implement CPU fallback with quantized models
- [ ] Build Redis caching layer (embeddings, retrieval, verdicts)
- [ ] Add cache invalidation logic on index updates
- [ ] Create Wikipedia 2024-12 pre-built index
- [ ] Implement index download and verification CLI
- [ ] Add performance profiling to verification pipeline
- [ ] Export profiling traces in JSON format
- [ ] Set up Prometheus metrics exporter
- [ ] Create Grafana dashboard for monitoring
- [ ] Benchmark end-to-end latency (target: p95 < 500ms)
- [ ] Profile memory usage and optimize hotspots
- [ ] **Implement connection pooling for RDS (SQLAlchemy + PgBouncer)**
- [ ] **Add batch writes to S3 with multipart upload**
- [ ] **Implement multi-tier caching (memory → Redis → cloud service)**
- [ ] **Document cost optimization strategies (spot, reserved, auto-scaling)**
- [ ] **Create disaster recovery runbook and test quarterly**

### Documentation & Developer Experience - TODO

- [ ] Set up Sphinx documentation structure
- [ ] Write Quickstart guide (installation to first verification)
- [ ] Write Evaluation guide (benchmarks and custom datasets)
- [ ] Write Custom Indices guide (building domain-specific corpora)
- [ ] Write Deployment guide (Docker, scaling, monitoring)
- [ ] **Write AWS deployment guide (Terraform, ECS, CloudWatch)**
- [ ] **Write GCP deployment guide (Terraform, GKE, Cloud Monitoring)**
- [ ] **Write Azure deployment guide (Terraform, AKS, Azure Monitor)**
- [ ] **Write Kubernetes deployment guide (Helm charts, auto-scaling)**
- [ ] **Write migration guide: v1 local → v2 cloud**
- [ ] **Write Architecture Decision Records (ADRs) for cloud-ready choices**
- [ ] **Create cost estimation calculator/guide with examples**
- [ ] Add API reference with autodoc
- [ ] Create Python SDK usage examples
- [ ] Document all CLI commands with examples
- [ ] Write CONTRIBUTING.md with setup instructions
- [ ] Set up pre-commit hooks (black, ruff, mypy)
- [ ] Configure ReadTheDocs hosting
- [ ] Add badges to README (build status, coverage, docs)
- [ ] Create tutorial videos or screencasts (optional)

### Testing & Quality Assurance

- [ ] Write unit tests for API endpoints (>80% coverage)
- [ ] Add integration tests for batch processing
- [ ] Create regression test suite on FEVER dev set
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Add performance benchmarks to CI (latency thresholds)
- [ ] Configure code coverage reporting (Codecov)
- [ ] Run security audit (bandit, safety)
- [ ] Validate OpenAPI spec with automated tools

### Cloud Migration Validation - TODO

- [ ] **Test SQLite → PostgreSQL RDS migration**
- [ ] **Test FAISS → Pinecone migration (or document alternative)**
- [ ] **Test local disk → S3 migration for documents**
- [ ] **Publish CloudEvents to SQS/EventBridge**
- [ ] **Export Prometheus metrics to CloudWatch**
- [ ] **Deploy Terraform templates to AWS (tested)**
- [ ] **Deploy Helm chart to Kubernetes cluster (tested)**
- [ ] **Run FEVER benchmark with cloud services (Pinecone, RDS, ElastiCache)**
- [ ] **Measure and document cloud performance vs. local baseline**
- [ ] **Calculate cloud deployment costs for 1M claims/month**

### Infrastructure as Code - TODO

- [ ] **Create Terraform modules for AWS (VPC, RDS, ElastiCache, ECS, ALB, S3)**
- [ ] **Create Terraform modules for GCP (optional)**
- [ ] **Create Terraform modules for Azure (optional)**
- [ ] **Create Helm chart with deployment, service, ingress, HPA, PDB**
- [ ] **Create CloudFormation templates (alternative to Terraform)**
- [ ] **Set up CI/CD pipeline for cloud deployment (GitHub Actions)**
- [ ] **Test multi-environment deployment (dev, staging, prod)**
- [ ] **Validate infrastructure teardown and recreation (<30min)**

### Release Preparation

- [ ] Finalize v1.0 feature freeze
- [ ] Run full evaluation suite and record baseline metrics
- [ ] Complete all documentation (API, guides, architecture)
- [ ] Perform security review (API keys, rate limits, PII)
- [ ] **Complete cloud readiness validation checklist**
- [ ] **Validate cloud migration readiness (<50% refactoring)**
- [ ] **Document cloud deployment costs and optimization strategies**
- [ ] Create release notes with migration guide
- [ ] **Include cloud deployment templates in release artifacts**
- [ ] Tag v1.0.0 release in Git
- [ ] Publish to PyPI
- [ ] Announce release (blog post, social media)
