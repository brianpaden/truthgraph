# Health Monitoring - Comprehensive Metrics Reference

**Purpose**: Quick reference for all metrics collected by health monitoring system
**Status**: Part of Features 4.7 & 5.5
**Last Updated**: 2025-11-06

---

## Quick Navigation

**By Domain**:
- [API Health Metrics](#api-health-metrics) - Request processing, error rates
- [Service Dependency Health](#service-dependency-health) - Database, ML services
- [Docker Container Metrics](#docker-container-metrics) - Resource usage, health
- [Async Worker Pool Metrics](#async-worker-pool-metrics) - Workers, queue, tasks
- [Application Memory Metrics](#application-memory-metrics) - Process, GC, threads
- [ML Pipeline Metrics](#ml-pipeline-metrics) - Cache, search performance
- [System-Level Metrics](#system-level-metrics) - Docker, volumes

**By Alert Type**:
- [Critical Alerts](#critical-alerts) - Must address immediately
- [Warning Alerts](#warning-alerts) - Investigate and optimize
- [Informational](#informational) - Track trends

**By Collection Method**:
- [Real-Time Counters](#real-time-counters) - Continuous tracking
- [Periodic Samples](#periodic-samples) - Sampled every 10-60 seconds
- [Background Tasks](#background-tasks) - Computed on schedule
- [Health Checks](#health-checks) - On-demand testing

---

## API Health Metrics

### Request Processing Metrics

| Metric | Type | Unit | Normal Range | Alert | Collection |
|--------|------|------|--------------|-------|------------|
| `api.requests.total` | Counter | requests | Increases with load | None | Middleware on every request |
| `api.requests.current_active` | Gauge | count | 0-50 | > 100 | Middleware entry/exit |
| `api.requests.duration_ms` | Histogram | ms | 50-2000 | p95 > 5000 | Middleware timing |
| `api.requests.error_rate` | Gauge | % | < 1% | > 5% | Status code tracking |
| `api.requests.success_count` | Counter | count | Increases | None | Status 200-299 |
| `api.requests.redirect_count` | Counter | count | Low | None | Status 300-399 |
| `api.requests.error_4xx_count` | Counter | count | Low | None | Status 400-499 |
| `api.requests.error_5xx_count` | Counter | count | Very low | > 0 | Status 500-599 |

**Collection**: Middleware intercepts all HTTP requests
**Aggregation**: Per-second rates calculated every 10 seconds
**Retention**: 1 hour (360 data points at 10-second intervals)

### Endpoint-Specific Metrics

| Metric | Endpoint | Type | Unit | Normal | Alert | Purpose |
|--------|----------|------|------|--------|-------|---------|
| `api.endpoint.verify.requests` | POST /api/v1/claims/{id}/verify | Counter | req | Varies | None | Verification volume |
| `api.endpoint.verify.duration_ms` | POST /api/v1/claims/{id}/verify | Histogram | ms | 100-5000 | p95 > 10000 | Verification latency |
| `api.endpoint.verdict.requests` | GET /api/v1/verdicts/{claim_id} | Counter | req | Varies | None | Verdict retrieval |
| `api.endpoint.verdict.duration_ms` | GET /api/v1/verdicts/{claim_id} | Histogram | ms | 10-500 | p95 > 2000 | Verdict lookup speed |
| `api.endpoint.health.requests` | GET /api/v1/health | Counter | req | Regular | > 100/min | Health check volume |
| `api.endpoint.health.duration_ms` | GET /api/v1/health | Histogram | ms | 5-50 | > 500 | Health check overhead |
| `api.endpoint.search.requests` | Vector/keyword search | Counter | req | Varies | None | Search volume |
| `api.endpoint.search.duration_ms` | Vector/keyword search | Histogram | ms | 50-500 | p95 > 2000 | Search latency |

**Use**: Identify slow endpoints and request patterns
**Actions**:
- If verify latency high: Check ML pipeline, database performance
- If search latency high: Check vector DB index, keyword search index
- If health latency high: Reduce health check frequency or scope

---

## Service Dependency Health

### Database Connectivity

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `db.connection.pool.size` | Gauge | conn | 5-20 | None | None |
| `db.connection.pool.active` | Gauge | conn | 1-10 | > 80% pool | > 95% pool |
| `db.connection.pool.idle` | Gauge | conn | 0-15 | None | None |
| `db.connection.pool.wait_count` | Counter | count | 0 | > 0 | > 10 |
| `db.connection.pool.timeout_count` | Counter | count | 0 | > 0 | > 5 |
| `db.query.count` | Counter | queries | Increases | None | None |
| `db.query.duration_ms` | Histogram | ms | 5-500 | p95 > 2000 | p99 > 5000 |
| `db.query.error_count` | Counter | errors | 0 | > 0 | > 1% of queries |
| `db.health.status` | Status | enum | healthy | degraded | unhealthy |

**Connection Pool Monitoring**:
- Track active connections to detect contention
- Alert when > 80% of pool is in use (connection exhaustion risk)
- Monitor wait times if connections not immediately available

**Query Performance**:
- p50 < 100ms (typical query)
- p95 < 500ms (slow query threshold)
- p99 < 2000ms (very slow query)

**Actions**:
- If pool nearly full: Add connection pooling capacity or optimize queries
- If query times high: Check query optimization, index health, table locks
- If timeouts occur: Reduce connection timeout or investigate blocking

### ML Services

| Metric | Service | Type | Unit | Normal | Alert |
|--------|---------|------|------|--------|-------|
| `ml.embedding.available` | Embeddings | Status | bool | true | false |
| `ml.embedding.duration_ms` | Embeddings | Histogram | ms | 50-500 | p95 > 2000 |
| `ml.embedding.batch_size_avg` | Embeddings | Gauge | items | 1-128 | None |
| `ml.embedding.cache.hits` | Embeddings | Counter | hits | High | None |
| `ml.embedding.cache.misses` | Embeddings | Counter | misses | Low | None |
| `ml.embedding.cache.hit_rate` | Embeddings | Gauge | % | > 70% | < 50% |
| `ml.nli.available` | NLI | Status | bool | true | false |
| `ml.nli.duration_ms` | NLI | Histogram | ms | 100-1000 | p95 > 3000 |
| `ml.nli.batch_size_avg` | NLI | Gauge | pairs | 1-64 | None |
| `ml.nli.cache.hits` | NLI | Counter | hits | High | None |
| `ml.nli.cache.misses` | NLI | Counter | misses | Low | None |
| `ml.nli.cache.hit_rate` | NLI | Gauge | % | > 80% | < 60% |
| `ml.model.memory_mb` | Both | Gauge | mb | 400+700 | > 1500 |
| `ml.model.load_time_ms` | Both | Histogram | ms | 500-2000 | > 5000 |

**Cache Monitoring**:
- Embedding cache hit rate indicates text deduplication
- NLI cache hit rate indicates evidence deduplication
- Low hit rates = high model execution overhead

**Service Availability**:
- If embedding service unavailable: Cannot generate embeddings
- If NLI service unavailable: Cannot make verdicts
- Monitor startup time after container restart

**Actions**:
- If cache hit rate low: Increase cache size or optimize cache key strategy
- If service unavailable: Check model loading logs, disk space, memory
- If latency high: Check GPU availability, batch size optimization

---

## Docker Container Metrics

### Resource Utilization (Per Service)

**API Container**
| Metric | Type | Unit | Limit | Normal | Alert | Critical |
|--------|------|------|-------|--------|-------|----------|
| `container.api.cpu.percent` | Gauge | % | 100 | 10-30 | > 80 | > 95 |
| `container.api.memory.usage_mb` | Gauge | mb | 4000 | 800-1500 | > 3200 | > 3900 |
| `container.api.memory.percent` | Gauge | % | 100 | 20-40 | > 80 | > 98 |
| `container.api.network.bytes_in` | Counter | bytes | None | Varies | None | None |
| `container.api.network.bytes_out` | Counter | bytes | None | Varies | None | None |

**PostgreSQL Container**
| Metric | Type | Unit | Limit | Normal | Alert | Critical |
|--------|------|------|-------|--------|-------|----------|
| `container.postgres.cpu.percent` | Gauge | % | 100 | 5-15 | > 80 | > 95 |
| `container.postgres.memory.usage_mb` | Gauge | mb | 2000 | 1200-1800 | > 1600 | > 1980 |
| `container.postgres.memory.percent` | Gauge | % | 100 | 60-90 | > 90 | > 99 |
| `container.postgres.network.bytes_in` | Counter | bytes | None | Varies | None | None |
| `container.postgres.network.bytes_out` | Counter | bytes | None | Varies | None | None |

**Frontend Container** (if running)
| Metric | Type | Unit | Limit | Normal | Alert | Critical |
|--------|------|------|-------|--------|-------|----------|
| `container.frontend.cpu.percent` | Gauge | % | 100 | < 5 idle, 10-20 load | > 50 | > 80 |
| `container.frontend.memory.usage_mb` | Gauge | mb | 512 | 100-200 | > 400 | > 500 |
| `container.frontend.memory.percent` | Gauge | % | 100 | 20-40 | > 80 | > 98 |

**General Resource Guidelines**:
- CPU: Peak < 80%, sustained < 50%
- Memory: Peak < 85%, sustained < 65%
- Critical level: Approaching actual limits (should trigger scaling)

### Container Health

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `container.{service}.status` | Status | enum | running | paused/stopped | exited |
| `container.{service}.restart_count` | Counter | count | 0 | > 0 | > 3 in 1 hour |
| `container.{service}.uptime_seconds` | Gauge | sec | > 86400 | 60-3600 | < 60 |
| `container.{service}.health_status` | Status | enum | healthy | unhealthy | None |
| `container.{service}.exit_code` | Gauge | code | 0 | None | != 0 |

**Interpretation**:
- Restart count > 0: Container crashed and restarted (investigate logs)
- Uptime < 60s: Recent restart (cold start, possible issue)
- Exit code != 0: Process exited abnormally
- Health status unhealthy: Failed health check, might not be responding

### Volume Usage

| Metric | Type | Unit | Notes |
|--------|------|------|-------|
| `docker.volumes.postgres.size_mb` | Gauge | mb | Database data directory |
| `docker.volumes.models.size_mb` | Gauge | mb | ML model cache (~520 mb) |
| `docker.volumes.total.size_mb` | Gauge | mb | Sum of all volumes |

**Alert Thresholds**:
- Postgres: > 5000 mb (5 GB) for development
- Models: Should be ~520 mb (if less, models not cached)
- Total: > 10000 mb (10 GB) for development

---

## Async Worker Pool Metrics

### Worker Status

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `workers.pool.size` | Gauge | workers | 5 | None | None |
| `workers.active.count` | Gauge | workers | 0-5 | None | None |
| `workers.idle.count` | Gauge | workers | 0-5 | 0 | None |
| `workers.health.status` | Status | enum | healthy | degraded | unhealthy |

**Idle Workers**:
- 0 idle = all workers busy (queue may be building up)
- Check if queue is also growing (throughput problem)

### Task Queue Metrics

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `queue.tasks.total` | Counter | tasks | Increases | None | None |
| `queue.tasks.pending` | Gauge | tasks | 0-10 | > 50 | > 200 |
| `queue.tasks.processing` | Gauge | tasks | 0-5 | None | None |
| `queue.tasks.completed` | Counter | tasks | Increases | None | None |
| `queue.tasks.failed` | Counter | tasks | Low | > 10% | > 20% |
| `queue.throughput.tasks_per_second` | Gauge | task/s | 0.1-5 | < 0.01 | = 0 |

**Queue Depth Monitoring**:
- Pending = how many tasks waiting for a worker
- Processing = how many workers are busy
- If pending grows but processing stable: Queue backing up (throughput issue)

**Failure Rate**:
- Normal: < 1%
- Alert: > 5%
- Critical: > 10% or rate increasing

### Task Processing Metrics

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `task.duration_ms` | Histogram | ms | 100-10000 | p95 > 30000 | p99 > 60000 |
| `task.duration_by_type` | Histogram | ms | Varies by type | Per type threshold | Per type threshold |
| `task.retries.count` | Histogram | retries | 0 (most) | p95 > 2 | p99 > 3 |
| `task.error.rate` | Gauge | % | < 1% | > 5% | > 10% |
| `task.queue.latency_ms` | Histogram | ms | 10-100 | p95 > 1000 | p99 > 5000 |
| `task.wait_time.min` | Gauge | ms | 0 | None | > 300000 |
| `task.wait_time.max` | Gauge | ms | Varies | > 600000 | None |
| `task.wait_time.avg` | Gauge | ms | 50-200 | > 1000 | > 5000 |

**Latency Analysis**:
- Queue latency: Time from queue to worker start
- Processing duration: Time worker spends on task
- Total latency: Queue latency + processing duration

**Retry Analysis**:
- High retry rate: Transient errors (database timeouts, service unavailable)
- Increasing retries: System becoming unstable
- Check error messages in logs

**Actions**:
- If queue backing up: Add more workers or optimize task execution
- If latency high: Identify bottleneck (queue delay vs processing time)
- If retry rate high: Fix underlying service issue
- If failure rate high: Check error logs and fix root cause

---

## Application Memory Metrics

### Python Process

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `app.process.memory.rss_mb` | Gauge | mb | 500-1500 | > 2000 | > 3000 |
| `app.process.memory.vms_mb` | Gauge | mb | 1500-4000 | > 4000 | > 5000 |
| `app.process.memory.percent` | Gauge | % | 5-20 | > 30 | > 50 |
| `app.process.memory.trend` | Trend | mb/sec | Flat | > 5 mb/sec | > 20 mb/sec |
| `app.process.open_files` | Gauge | files | 10-50 | > 500 | > 900 |
| `app.process.open_connections` | Gauge | conn | 5-20 | > 100 | > 500 |

**Memory Trend**:
- Flat = stable memory usage (good)
- Growing slowly = normal accumulation (check over time)
- Growing rapidly: Possible memory leak, restart may help

**RSS (Resident Set Size)**:
- Actual physical memory in use
- Large RSS = models loaded, many objects in memory

**VMS (Virtual Memory Size)**:
- Total address space reserved
- Can be much larger than RSS (includes memory-mapped files, etc.)

### Garbage Collection

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `app.gc.collections` | Counter | collections | Regular | Excessive | None |
| `app.gc.collection_time_ms` | Histogram | ms | < 100 | > 1000 | > 5000 |
| `app.gc.objects_tracked` | Gauge | objects | Varies | > 1000000 | > 5000000 |
| `app.gc.uncollectable` | Gauge | objects | 0 | > 0 | > 10 |

**GC Monitoring**:
- Uncollectable > 0: Possible circular references (memory leak indicator)
- Collection time spike: GC pausing application (pause time pollution)
- Excessive collections: Object creation outpacing collection

### Threads & Async

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `app.threads.count` | Gauge | threads | 10-20 | > 50 | > 100 |
| `app.threads.active` | Gauge | threads | 2-10 | > 30 | > 50 |
| `app.asyncio.tasks.count` | Gauge | tasks | 5-20 | > 100 | > 500 |
| `app.asyncio.tasks.pending` | Gauge | tasks | 0-10 | > 50 | > 100 |

**Thread Explosion**:
- Normal: 10-20 threads for typical workload
- Alert: > 50 (thread creation issue)
- Critical: > 100 (thread leak)

**Async Task Explosion**:
- Normal: 5-20 tasks (workers + internal)
- Alert: > 100 (task creation issue)
- Critical: > 500 (task leak)

---

## ML Pipeline Metrics

### Cache Performance

| Metric | Type | Unit | Normal | Alert | Action |
|--------|------|------|--------|-------|--------|
| `ml.cache.hits` | Counter | hits | High | None | None |
| `ml.cache.misses` | Counter | misses | Low | None | None |
| `ml.cache.hit_rate` | Gauge | % | > 70% | < 50% | Increase cache size |
| `ml.cache.size_entries` | Gauge | entries | Increases | None | Monitor growth |
| `ml.cache.memory_mb` | Gauge | mb | Varies | > 1000 | Trim cache |

**Cache Hit Rate**:
- > 80%: Excellent (good deduplication)
- 70-80%: Good (typical)
- 50-70%: Fair (consider increase)
- < 50%: Poor (cache not effective or too small)

### Vector Search

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `ml.search.query_count` | Counter | queries | Increases | None | None |
| `ml.search.duration_ms` | Histogram | ms | 50-500 | p95 > 2000 | p99 > 5000 |
| `ml.search.results.returned` | Gauge | results | 1-100 | None | None |
| `ml.search.results.avg_count` | Gauge | results | 5-20 | None | None |
| `ml.search.index.size_mb` | Gauge | mb | Grows | > 10000 | Vacuum/optimize |
| `ml.search.index.health` | Status | enum | healthy | degraded | rebuilding |

**Search Latency**:
- p50 < 100ms (fast typical query)
- p95 < 500ms (acceptable)
- p99 < 2000ms (slow outliers)

**Index Health**:
- Degraded: Consider rebuild/optimization
- Large size: Can be optimized to reduce memory

---

## System-Level Metrics

### Docker Compose Status

| Metric | Type | Unit | Normal | Alert | Critical |
|--------|------|------|--------|-------|----------|
| `docker.containers.running` | Gauge | containers | 3-4 | < 3 | < 3 |
| `docker.containers.healthy` | Gauge | containers | 3-4 | < running count | < running count |
| `docker.containers.unhealthy` | Gauge | containers | 0 | > 0 | > 0 |
| `docker.network.status` | Status | enum | connected | isolated | None |

**Service Status**:
- API: Critical (no endpoints if down)
- PostgreSQL: Critical (no data if down)
- Frontend: Medium (UI unavailable, API still works)
- Redis: Low (optional, affects caching only)

---

## Critical Alerts

Actions required immediately:

| Alert | Severity | Check | Action |
|-------|----------|-------|--------|
| Service unavailable (health check fails) | CRITICAL | Check logs, restart container | Investigate root cause |
| Memory usage > 90% | CRITICAL | Check memory trend, kill memory leak | Restart service or add resources |
| Database connection pool exhausted | CRITICAL | Check active queries, add connections | Optimize slow queries |
| Queue depth > 200 | CRITICAL | Check task failure rate, worker health | Scale workers or optimize tasks |
| Task failure rate > 20% | CRITICAL | Check error logs, service dependencies | Fix root cause |
| Disk space < 5% | CRITICAL | Check volume sizes, clean old data | Expand storage |

---

## Warning Alerts

Investigate and optimize:

| Alert | Severity | Check | Action |
|--------|----------|-------|--------|
| API latency p95 > 5 seconds | WARNING | Check slow endpoint, database queries | Optimize hotspot |
| Worker utilization > 80% | WARNING | Check queue depth, task duration | Scale workers or optimize |
| Cache hit rate < 50% | WARNING | Check cache strategy, size | Tune cache |
| Task retry rate > 5% | WARNING | Check error logs | Fix transient issues |
| Memory usage > 70% | WARNING | Check memory trend | Monitor for leak |
| CPU usage > 80% sustained | WARNING | Profile code, check expensive operations | Optimize |

---

## Informational

Track trends but no action required:

| Metric | Purpose | When to Review |
|--------|---------|-----------------|
| Total requests | Request volume | Weekly |
| Endpoint usage | Which endpoints popular | Weekly |
| Task throughput | Worker efficiency | Daily |
| Cache hit rate trends | Deduplication effectiveness | Weekly |
| Error patterns | Which errors common | Daily |
| Resource utilization trends | Capacity planning | Weekly |

---

## Implementation Reference

### What Gets Collected Where

```
Middleware (Every Request)
├── api.requests.total
├── api.requests.current_active
├── api.requests.duration_ms
└── api.requests.error_rate

Health Check Endpoint (On Demand)
├── db.health.status
├── ml.embedding.available
├── ml.nli.available
└── workers.health.status

Background Task (Every 10 seconds)
├── docker.containers.{*}
├── container.{service}.{*}
└── worker pool stats

Per-Request/Query
├── db.query.duration_ms
├── ml.embedding.duration_ms
├── ml.nli.duration_ms
└── task.duration_ms

Task Queue Operations
├── queue.tasks.{*}
└── task.{*}
```

### Dashboard Charts

**System Overview**:
- Overall health status (gauge: healthy/warning/critical)
- API requests per second (line chart, last hour)
- Error rate (gauge + trend)
- Worker pool status (gauge: active/idle)

**Resource Usage**:
- CPU per container (gauge charts, current)
- Memory per container (gauge + trend)
- Memory vs limit (stacked bar, all containers)
- Network I/O (line chart, bytes/sec)

**Performance**:
- API latency (histogram: p50, p95, p99)
- Database query latency (histogram)
- Task duration (histogram)
- Cache hit rate (gauge + trend)

**Reliability**:
- Task success rate (gauge)
- Error breakdown (pie chart: 4xx, 5xx, etc.)
- Container restart count (bar chart)
- Service availability (gauge)

---

**Document Version**: 1.0
**Status**: Part of Feature 4.7 & 5.5 Specification
**Related Documents**: 6_health_monitoring_handoff.md
