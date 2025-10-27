# TruthGraph Phase 2 - API Quick Reference

## Base URL
```url
http://localhost:8000
```

## Endpoints Overview

| Endpoint | Method | Purpose | Rate Limit |
|----------|--------|---------|------------|
| `/api/v1/embed` | POST | Generate embeddings | 10/min |
| `/api/v1/search` | POST | Search evidence | 10/min |
| `/api/v1/nli` | POST | Run NLI inference | 10/min |
| `/api/v1/nli/batch` | POST | Batch NLI | 10/min |
| `/api/v1/verify` | POST | Full verification | 10/min |
| `/api/v1/verdict/{id}` | GET | Get verdict | 10/min |
| `/health` | GET | Health check | 60/min |
| `/` | GET | API info | 60/min |

## Quick Examples

### 1. Generate Embeddings
```bash
curl -X POST http://localhost:8000/api/v1/embed \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["The Earth orbits the Sun"],
    "batch_size": 32
  }'
```

**Response:**
```json
{
  "embeddings": [[0.1, 0.2, ...]],
  "count": 1,
  "dimension": 384,
  "processing_time_ms": 125.5
}
```

### 2. Search for Evidence
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change effects",
    "limit": 5,
    "mode": "hybrid",
    "min_similarity": 0.5
  }'
```

**Response:**
```json
{
  "results": [
    {
      "evidence_id": "uuid",
      "content": "Evidence text...",
      "similarity": 0.87,
      "rank": 1
    }
  ],
  "count": 5,
  "query_time_ms": 45.2
}
```

### 3. Run NLI Inference
```bash
curl -X POST http://localhost:8000/api/v1/nli \
  -H "Content-Type: application/json" \
  -d '{
    "premise": "The Earth is round",
    "hypothesis": "The Earth is spherical"
  }'
```

**Response:**
```json
{
  "label": "entailment",
  "confidence": 0.92,
  "scores": {
    "entailment": 0.92,
    "contradiction": 0.03,
    "neutral": 0.05
  },
  "processing_time_ms": 85.3
}
```

### 4. Verify Claim (Full Pipeline)
```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "The Earth is 4.5 billion years old",
    "max_evidence": 10,
    "confidence_threshold": 0.7
  }'
```

**Response:**
```json
{
  "verdict": "SUPPORTED",
  "confidence": 0.87,
  "evidence": [...],
  "explanation": "The claim is supported...",
  "claim_id": "uuid",
  "verification_id": "uuid",
  "processing_time_ms": 1250.5
}
```

### 5. Get Verdict
```bash
curl http://localhost:8000/api/v1/verdict/{claim_id}
```

**Response:**
```json
{
  "claim_id": "uuid",
  "claim_text": "...",
  "verdict": "SUPPORTED",
  "confidence": 0.87,
  "evidence_count": 10,
  "created_at": "2025-10-26T12:00:00Z"
}
```

### 6. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-26T12:00:00Z",
  "services": {
    "database": {"status": "healthy"},
    "embedding_service": {"status": "healthy"},
    "nli_service": {"status": "healthy"}
  },
  "version": "2.0.0"
}
```

## Python Client Examples

### Basic Usage
```python
import requests

BASE_URL = "http://localhost:8000"

# Embed text
response = requests.post(
    f"{BASE_URL}/api/v1/embed",
    json={"texts": ["Hello world"]}
)
embeddings = response.json()["embeddings"]

# Search
response = requests.post(
    f"{BASE_URL}/api/v1/search",
    json={"query": "climate change", "limit": 10, "mode": "hybrid"}
)
results = response.json()["results"]

# Verify claim
response = requests.post(
    f"{BASE_URL}/api/v1/verify",
    json={
        "claim": "Water boils at 100C",
        "max_evidence": 10,
        "confidence_threshold": 0.7
    }
)
verdict = response.json()["verdict"]
```

### With Error Handling
```python
import requests

def verify_claim(claim: str) -> dict:
    """Verify a claim with error handling."""
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/verify",
            json={"claim": claim},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limit exceeded")
        elif e.response.status_code == 422:
            print("Invalid request:", e.response.json())
        raise
    except requests.exceptions.Timeout:
        print("Request timed out")
        raise

result = verify_claim("The Earth is flat")
print(f"Verdict: {result['verdict']}")
```

## Request Validation

### Field Limits
- `texts`: 1-100 items
- `batch_size`: 1-128
- `query`: 1-1000 characters
- `limit`: 1-100
- `max_evidence`: 1-50
- `pairs`: 1-50 pairs

### Required Fields
- All text fields must be non-empty strings
- UUIDs must be valid UUID format
- Confidence thresholds: 0.0-1.0
- Similarities: 0.0-1.0

## Response Headers

All responses include:
- `X-Request-ID`: Unique request identifier
- `X-Process-Time`: Processing time in milliseconds
- `X-RateLimit-Limit`: Rate limit for endpoint
- `X-RateLimit-Remaining`: Remaining requests

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "claim"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Rate Limit
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

### 404 Not Found
```json
{
  "error": "NotFound",
  "message": "Claim not found: {id}"
}
```

### 500 Internal Error
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "request_id": "req_abc123"
}
```

## Interactive Documentation

Access comprehensive API docs at:
- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

## Running the API

### Development
```bash
uvicorn truthgraph.main:app --reload --port 8000
```

### Production
```bash
uvicorn truthgraph.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker
```bash
docker run -p 8000:8000 truthgraph-api
```

## Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# API tests only
pytest tests/test_api_ml_endpoints.py -v

# Integration tests
pytest tests/test_ml_integration.py -v

# Specific test
pytest tests/test_api_ml_endpoints.py::TestVerifyEndpoint::test_verify_claim_with_evidence -v
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test (create locustfile.py first)
locust -f locustfile.py --host=http://localhost:8000
```

## Performance Tips

1. **Use batch endpoints** for multiple operations
2. **Cache embeddings** for repeated texts
3. **Set appropriate limits** to avoid timeouts
4. **Use async clients** (aiohttp) for concurrent requests
5. **Monitor rate limits** via response headers

## Monitoring

### Logs
```bash
# View logs
tail -f logs/truthgraph.log

# Filter by endpoint
grep "/api/v1/verify" logs/truthgraph.log
```

### Metrics
- Check `X-Process-Time` header for latency
- Monitor rate limit headers
- Use `/health` for service status

## Troubleshooting

### Slow Responses
- Check model loading (first request is slow)
- Reduce `max_evidence` or `limit`
- Use smaller `batch_size`

### Rate Limits
- Implement exponential backoff
- Use `Retry-After` header
- Consider authentication for higher limits

### Validation Errors
- Check required fields
- Verify data types
- Check min/max constraints
- Review OpenAPI docs

## Security Notes

1. **Production**: Restrict CORS origins
2. **Authentication**: Coming in Phase 3
3. **Rate Limiting**: Adjust per deployment
4. **Input Validation**: Always enabled via Pydantic
5. **HTTPS**: Use reverse proxy (nginx/traefik)

## Support

- **Documentation**: <http://localhost:8000/docs>
- **Issues**: GitHub Issues
- **Logs**: Check application logs for errors
- **Health**: GET /health for system status
