# Error Codes Reference

Complete reference of HTTP status codes and error responses for the TruthGraph API.

## HTTP Status Codes

| Code | Status | Description | When It Occurs |
|------|--------|-------------|----------------|
| 200 | OK | Request successful | Successful GET/POST/PUT requests |
| 201 | Created | Resource created | Successful resource creation |
| 202 | Accepted | Async task accepted | Background task queued |
| 400 | Bad Request | Invalid request | Validation errors, malformed JSON |
| 404 | Not Found | Resource not found | Invalid claim_id, task_id, etc. |
| 409 | Conflict | Resource conflict | Duplicate claim, already verified |
| 422 | Unprocessable Entity | Validation error | Pydantic validation failure |
| 429 | Too Many Requests | Rate limit exceeded | Too many requests per time window |
| 500 | Internal Server Error | Server error | Unexpected server errors |
| 503 | Service Unavailable | Service down | Service temporarily unavailable |

---

## Error Response Format

All errors follow a consistent format:

### Simple Error
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Field validation error message",
      "type": "value_error.missing"
    }
  ]
}
```

### Rate Limit Error (429)
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded: 10 per 1 minute",
  "retry_after": 45
}
```

---

## Common Error Scenarios

### 1. Validation Errors (400)

#### Empty Claim Text
**Request:**
```json
{
  "claim": "",
  "max_evidence": 10
}
```

**Response:**
```json
{
  "detail": "Claim text cannot be empty"
}
```

**Solution:** Provide non-empty claim text (1-2000 characters).

---

#### Claim ID Mismatch
**Request:**
```bash
POST /api/v1/claims/claim_123/verify
{
  "claim_id": "claim_456",
  "claim_text": "..."
}
```

**Response:**
```json
{
  "detail": "Path claim_id 'claim_123' does not match request claim_id 'claim_456'"
}
```

**Solution:** Ensure path parameter matches request body `claim_id`.

---

#### Invalid Corpus IDs
**Request:**
```json
{
  "claim_id": "claim_123",
  "claim_text": "...",
  "corpus_ids": []
}
```

**Response:**
```json
{
  "detail": "corpus_ids cannot be empty list (use None instead)"
}
```

**Solution:** Use `null` or omit the field entirely to search all corpora.

---

#### Invalid Evidence Count
**Request:**
```json
{
  "claim": "...",
  "max_evidence": 100
}
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "max_evidence"],
      "msg": "ensure this value is less than or equal to 50",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**Solution:** Use `max_evidence` between 1 and 50.

---

### 2. Not Found Errors (404)

#### Claim Not Found
**Request:**
```bash
GET /api/v1/verdicts/nonexistent_claim
```

**Response:**
```json
{
  "detail": "No verification result found for claim: nonexistent_claim"
}
```

**Solution:** Verify the claim_id exists and has been verified.

---

#### Task Not Found
**Request:**
```bash
GET /api/v1/tasks/invalid_task_id
```

**Response:**
```json
{
  "detail": "Task 'invalid_task_id' not found"
}
```

**Solution:** Use the task_id returned from the verify endpoint.

---

#### Verdict Not Available Yet
**Request:**
```bash
GET /api/v1/verdicts/claim_123
```

**Response (202):**
```json
{
  "detail": "Verification in progress. Please check again later.",
  "status": "processing"
}
```

**Solution:** This is not an error - poll again after a short delay.

---

### 3. Conflict Errors (409)

#### Claim Already Verified
**Request:**
```bash
POST /api/v1/claims/claim_123/verify
```

**Response:**
```json
{
  "task_id": "task_existing",
  "status": "completed",
  "created_at": "2025-11-07T10:00:00Z",
  "completed_at": "2025-11-07T10:00:05Z",
  "result": {
    "verdict": "SUPPORTED",
    "confidence": 0.92
  },
  "progress_percentage": 100
}
```

**Solution:** This returns the existing result - no action needed.

---

### 4. Rate Limit Errors (429)

#### Rate Limit Exceeded
**Request:**
```bash
# 6th request within 1 minute to /api/v1/verify
POST /api/v1/verify
```

**Response:**
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded: 5 per 1 minute",
  "retry_after": 45
}
```

**Response Headers:**
```
RateLimit-Limit: 5
RateLimit-Remaining: 0
RateLimit-Reset: 1699012345
Retry-After: 45
```

**Solution:** Wait for the time specified in `Retry-After` header (seconds).

**Python Example:**
```python
import time

response = client.post("/api/v1/verify", json=request_data)

if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    print(f"Rate limited. Waiting {retry_after} seconds...")
    time.sleep(retry_after)
    # Retry request
    response = client.post("/api/v1/verify", json=request_data)
```

---

### 5. Validation Errors (422)

#### Pydantic Validation Failure
**Request:**
```json
{
  "texts": "not a list",
  "batch_size": 1000
}
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "texts"],
      "msg": "value is not a valid list",
      "type": "type_error.list"
    },
    {
      "loc": ["body", "batch_size"],
      "msg": "ensure this value is less than or equal to 128",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**Solution:** Fix field types and values to match schema requirements.

---

#### Missing Required Field
**Request:**
```json
{
  "max_evidence": 10
}
```

**Response:**
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

**Solution:** Include all required fields in the request.

---

### 6. Server Errors (500)

#### Internal Server Error
**Response:**
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "request_id": "req_abc123"
}
```

**Common Causes:**
- Database connection failure
- ML model loading error
- Out of memory
- Unhandled exception

**Solution:**
1. Check `/health` endpoint for service status
2. Retry request with exponential backoff
3. Contact support if persistent

---

#### Verification Pipeline Failed
**Request:**
```bash
POST /api/v1/verify
```

**Response:**
```json
{
  "detail": "Verification pipeline failed"
}
```

**Common Causes:**
- Evidence retrieval failed
- NLI inference error
- Database write error

**Solution:**
1. Check API health: `GET /health`
2. Verify database connectivity
3. Check server logs for details
4. Retry with simpler parameters (reduce max_evidence)

---

#### Service Unavailable (503)
**Response:**
```json
{
  "detail": "Service temporarily unavailable"
}
```

**Common Causes:**
- Server under maintenance
- Database connection pool exhausted
- ML service not loaded

**Solution:**
1. Wait and retry
2. Check `/health` for service status
3. Implement exponential backoff

---

## Rate Limit Details

### Endpoint Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/verify` | 5 | per minute |
| `/api/v1/claims/{claim_id}/verify` | 5 | per minute |
| `/api/v1/embed` | 10 | per minute |
| `/api/v1/search` | 20 | per minute |
| `/api/v1/nli` | 10 | per minute |
| `/api/v1/nli/batch` | 5 | per minute |
| `/api/v1/verdicts/{claim_id}` | 20 | per minute |
| `/api/v1/verdict/{claim_id}` | 20 | per minute |
| `/api/v1/tasks/{task_id}` | 20 | per minute |
| `/health` | 100 | per minute |
| Default | 60 | per minute |

### Rate Limit Headers

Every response includes rate limit headers:

```
RateLimit-Limit: 10        # Maximum requests allowed
RateLimit-Remaining: 7     # Requests remaining in window
RateLimit-Reset: 1699012345  # Unix timestamp when limit resets
```

When rate limited (429 response):
```
Retry-After: 45  # Seconds to wait before retrying
```

---

## Error Handling Best Practices

### 1. Implement Retry Logic

```python
import time
from typing import Optional

def retry_with_backoff(func, max_retries=3):
    """Retry function with exponential backoff."""
    delay = 1

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Last attempt, re-raise error

            # Check if retryable error
            if hasattr(e, 'response'):
                status = e.response.status_code
                if status == 429:
                    # Rate limit - use Retry-After header
                    retry_after = int(e.response.headers.get("Retry-After", delay))
                    time.sleep(retry_after)
                elif status >= 500:
                    # Server error - exponential backoff
                    time.sleep(delay)
                    delay *= 2
                else:
                    # Client error - don't retry
                    raise
```

### 2. Handle Specific Errors

```python
async def safe_verify(claim: str):
    """Verify claim with proper error handling."""
    try:
        response = await client.post("/api/v1/verify", json={"claim": claim})

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 400:
            # Validation error
            error = response.json()
            print(f"Invalid request: {error['detail']}")
            return None

        elif response.status_code == 429:
            # Rate limit
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited. Retry after {retry_after}s")
            await asyncio.sleep(retry_after)
            return await safe_verify(claim)

        elif response.status_code >= 500:
            # Server error
            print("Server error. Retrying...")
            await asyncio.sleep(5)
            return await safe_verify(claim)

    except Exception as e:
        print(f"Request failed: {e}")
        return None
```

### 3. Validate Before Sending

```python
def validate_verify_request(claim: str, max_evidence: int) -> Optional[str]:
    """Validate request before sending."""
    if not claim or not claim.strip():
        return "Claim cannot be empty"

    if len(claim) > 2000:
        return "Claim exceeds 2000 characters"

    if max_evidence < 1 or max_evidence > 50:
        return "max_evidence must be between 1 and 50"

    return None  # Valid


# Usage
error = validate_verify_request(claim, max_evidence)
if error:
    print(f"Validation error: {error}")
else:
    # Send request
    response = client.post("/api/v1/verify", json={"claim": claim})
```

### 4. Monitor Rate Limits

```python
def check_rate_limits(response):
    """Monitor rate limit headers."""
    limit = response.headers.get("RateLimit-Limit")
    remaining = response.headers.get("RateLimit-Remaining")
    reset = response.headers.get("RateLimit-Reset")

    if remaining:
        remaining_pct = int(remaining) / int(limit) * 100
        if remaining_pct < 20:
            print(f"Warning: Only {remaining} requests remaining")

    return {
        "limit": limit,
        "remaining": remaining,
        "reset": reset
    }
```

### 5. Log Errors

```python
import logging

logger = logging.getLogger(__name__)

def log_api_error(response, request_data):
    """Log API errors for debugging."""
    logger.error(
        "API request failed",
        extra={
            "status_code": response.status_code,
            "url": response.url,
            "request_data": request_data,
            "response_body": response.text,
            "headers": dict(response.headers),
        }
    )
```

---

## Troubleshooting Guide

### Problem: "Claim text cannot be empty"

**Cause:** Empty or whitespace-only claim text

**Solutions:**
- Ensure claim is non-empty after stripping whitespace
- Check for null/undefined values
- Validate input before sending

---

### Problem: Rate limit exceeded

**Cause:** Too many requests in time window

**Solutions:**
- Implement rate limiting client-side
- Use exponential backoff
- Cache results to avoid duplicate requests
- Upgrade to higher rate limit tier (if available)

---

### Problem: Task not found

**Cause:** Invalid task_id or task expired

**Solutions:**
- Use task_id from verify response
- Don't poll tasks older than 1 hour (default TTL)
- Use verdict endpoint instead for final results

---

### Problem: Verification timeout

**Cause:** Long-running verification or slow services

**Solutions:**
- Increase client timeout (default 30s may be too short)
- Use async endpoints with polling
- Reduce max_evidence parameter
- Check /health for service issues

---

### Problem: "Verdict not found"

**Cause:** Claim hasn't been verified yet

**Solutions:**
- Trigger verification first
- Wait for task completion
- Check task status before polling verdict

---

## Getting Help

If you encounter persistent errors:

1. **Check API Health**: `GET /health`
2. **Review Logs**: Check server logs for details
3. **Rate Limit Stats**: `GET /rate-limit-stats`
4. **API Documentation**: `/docs` (Swagger UI)
5. **OpenAPI Spec**: `/openapi.json`

For support:
- Email: support@truthgraph.com
- GitHub Issues: https://github.com/truthgraph/truthgraph/issues
- Documentation: https://docs.truthgraph.com
