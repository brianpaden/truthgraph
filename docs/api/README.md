# TruthGraph API Documentation

**Version:** 2.0.0
**Base URL:** `http://localhost:8000`
**OpenAPI Spec:** `/openapi.json`
**Interactive Docs:** `/docs` (Swagger UI) and `/redoc` (ReDoc)

## Overview

TruthGraph is an AI-powered fact-checking system that provides real-time claim verification using ML-powered evidence retrieval and Natural Language Inference (NLI). The API enables you to verify claims, search for evidence, generate embeddings, and analyze claim-evidence relationships.

## Quick Start

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

### 2. Verify a Claim (Simple)

```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Earth orbits the Sun"}'
```

### 3. Verify a Claim (Async with Polling)

```bash
# Trigger verification
curl -X POST "http://localhost:8000/api/v1/claims/claim_123/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "claim_123",
    "claim_text": "The Earth is round"
  }'

# Poll for results
curl "http://localhost:8000/api/v1/verdicts/claim_123"
```

## Architecture

TruthGraph uses a **hybrid verification pipeline**:

1. **Evidence Retrieval**: Semantic vector search + keyword search
2. **NLI Analysis**: Natural Language Inference to determine entailment/contradiction
3. **Verdict Aggregation**: Combine evidence signals into final verdict
4. **Async Processing**: Background task queue for long-running verifications

## API Endpoints

### Verification Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v1/verify` | POST | Full verification pipeline (sync) | 5/min |
| `/api/v1/claims/{claim_id}/verify` | POST | Trigger async verification | 5/min |
| `/api/v1/verdicts/{claim_id}` | GET | Get verification result | 20/min |
| `/api/v1/tasks/{task_id}` | GET | Get task status | 20/min |

See: [Verification Endpoints Documentation](endpoints/verification.md)

### ML Service Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v1/embed` | POST | Generate text embeddings | 10/min |
| `/api/v1/search` | POST | Hybrid/vector/keyword search | 20/min |
| `/api/v1/nli` | POST | Natural Language Inference | 10/min |
| `/api/v1/nli/batch` | POST | Batch NLI inference | 5/min |
| `/api/v1/verdict/{claim_id}` | GET | Get stored verdict | 20/min |

See: [ML Services Documentation](endpoints/ml_services.md)

### System Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/health` | GET | Health check all services | 100/min |
| `/rate-limit-stats` | GET | Rate limit statistics | 60/min |
| `/` | GET | API information | 60/min |

## ML Models

### Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Use Case**: Semantic similarity and vector search

### NLI Model
- **Model**: `microsoft/deberta-v3-base` (fine-tuned on MNLI)
- **Labels**: entailment, contradiction, neutral
- **Use Case**: Claim-evidence relationship analysis

### Vector Database
- **Engine**: PostgreSQL with pgvector extension
- **Index**: IVFFlat for efficient similarity search
- **Distance Metric**: Cosine similarity

## Rate Limiting

All endpoints are rate-limited **per IP address**. Rate limit information is included in response headers:

```
RateLimit-Limit: 10
RateLimit-Remaining: 7
RateLimit-Reset: 1699012345
Retry-After: 45
```

### Rate Limit Tiers

- **Heavy Operations** (5/min): Full verification, batch NLI
- **Medium Operations** (10/min): Embeddings, single NLI
- **Light Operations** (20/min): Search, verdict retrieval
- **Health Checks** (100/min): System monitoring
- **Default** (60/min): All other endpoints

When you exceed the rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded: 10 per 1 minute",
  "retry_after": 45
}
```

## Authentication

**Current Version**: No authentication required (development mode)

**Production**: Will use Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/verify
```

## Request/Response Format

### Content Type
All requests must use `Content-Type: application/json`

### Response Structure

**Success Response**:
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

**Error Response**:
```json
{
  "detail": "Error message"
}
```

**Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Field validation error",
      "type": "value_error"
    }
  ]
}
}
```

## Common HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Async task accepted |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (e.g., already verified) |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Error Handling

See the [Error Codes Reference](errors/error_codes.md) for detailed error information.

## Examples

### cURL Examples
- [Basic Verification](examples/verify_claim.sh)
- [Complete Walkthrough](examples/verify_claim.md)

### Python Examples
- [Async Client](examples/verify_claim.py)
- [Batch Processing](examples/batch_verification.py)

### JavaScript Examples
- [Fetch API](examples/verify_claim.js)
- [Axios Client](examples/verify_claim_axios.js)

## Data Schemas

Detailed schema documentation:
- [Verification Schemas](schemas/verification.md)
- [Evidence Schemas](schemas/evidence.md)
- [ML Service Schemas](schemas/ml_services.md)

## Best Practices

### 1. Use Async Verification for Production

For production workloads, use the async verification endpoint to avoid timeouts:

```python
# Trigger async verification
response = client.post("/api/v1/claims/claim_123/verify", json=request)
task_id = response.json()["task_id"]

# Poll for results
while True:
    result = client.get(f"/api/v1/verdicts/claim_123")
    if result.status_code == 200:
        break
    time.sleep(1)
```

### 2. Implement Exponential Backoff

When polling for results, use exponential backoff:

```python
import time

def poll_with_backoff(claim_id, max_attempts=10):
    delay = 1
    for attempt in range(max_attempts):
        result = client.get(f"/api/v1/verdicts/{claim_id}")
        if result.status_code == 200:
            return result.json()
        time.sleep(delay)
        delay = min(delay * 2, 30)  # Cap at 30 seconds
    raise TimeoutError("Verification timeout")
```

### 3. Handle Rate Limits Gracefully

Respect `Retry-After` headers:

```python
response = client.post("/api/v1/verify", json=request)
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
    response = client.post("/api/v1/verify", json=request)
```

### 4. Use Batch Operations

For multiple NLI checks, use batch endpoints:

```python
# Instead of multiple single requests
pairs = [("evidence1", "claim1"), ("evidence2", "claim2")]
response = client.post("/api/v1/nli/batch", json={"pairs": pairs})
```

### 5. Monitor Health Endpoints

Regularly check `/health` before making requests:

```python
health = client.get("/health").json()
if health["status"] != "healthy":
    # Fallback or retry logic
    pass
```

## Troubleshooting

### Common Issues

**1. 422 Validation Error**
- Check request body matches schema
- Ensure required fields are present
- Verify field types and constraints

**2. 429 Rate Limit Exceeded**
- Reduce request frequency
- Implement exponential backoff
- Cache results when possible

**3. 500 Internal Server Error**
- Check `/health` endpoint
- Review server logs
- Verify database connectivity

**4. Slow Responses**
- Use async endpoints for heavy operations
- Reduce `max_evidence` parameter
- Enable result caching

### Getting Help

- **API Documentation**: `/docs` (Swagger UI)
- **OpenAPI Spec**: `/openapi.json`
- **Health Status**: `/health`
- **Rate Limit Stats**: `/rate-limit-stats`

## API Versioning

Current version: **v1** (included in URL path)

Future versions will be available at:
- `/api/v2/...`
- `/api/v3/...`

Old versions will be maintained for backward compatibility.

## Development vs Production

### Development Mode
- Base URL: `http://localhost:8000`
- No authentication
- Relaxed rate limits
- Detailed error messages

### Production Mode
- Base URL: `https://api.truthgraph.com`
- Bearer token authentication
- Strict rate limits
- Sanitized error messages
- HTTPS required

## Next Steps

1. **Read**: [Verification Endpoints](endpoints/verification.md)
2. **Try**: [cURL Examples](examples/verify_claim.sh)
3. **Build**: [Python Client](examples/verify_claim.py)
4. **Learn**: [Error Handling](errors/error_codes.md)
