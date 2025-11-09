# Verification Endpoints

The verification endpoints provide synchronous and asynchronous claim verification with the full ML pipeline.

## Endpoints Overview

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/api/v1/verify` | POST | 5/min | Synchronous full verification |
| `/api/v1/claims/{claim_id}/verify` | POST | 5/min | Async verification (recommended) |
| `/api/v1/verdicts/{claim_id}` | GET | 20/min | Get verification result |
| `/api/v1/tasks/{task_id}` | GET | 20/min | Get task status |

---

## POST /api/v1/verify

**Full synchronous claim verification pipeline**

Executes the complete verification workflow and returns results immediately. Use this for simple queries or testing. For production, use the async endpoint.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "claim": "The Earth orbits the Sun",
  "tenant_id": "default",
  "max_evidence": 10,
  "confidence_threshold": 0.7,
  "search_mode": "hybrid"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `claim` | string | Yes | - | Claim text to verify (1-2000 chars) |
| `tenant_id` | string | No | "default" | Tenant identifier for multi-tenancy |
| `max_evidence` | integer | No | 10 | Max evidence items (1-50) |
| `confidence_threshold` | float | No | 0.7 | Min confidence for verdict (0.0-1.0) |
| `search_mode` | string | No | "hybrid" | Search mode: "hybrid", "vector", "keyword" |

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "verdict": "SUPPORTED",
  "confidence": 0.87,
  "evidence": [
    {
      "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "The Earth orbits the Sun in an elliptical path once every 365.25 days.",
      "source_url": "https://example.com/astronomy",
      "nli_label": "entailment",
      "nli_confidence": 0.91,
      "similarity": 0.85
    }
  ],
  "explanation": "The claim is supported by strong scientific evidence with high confidence.",
  "claim_id": "223e4567-e89b-12d3-a456-426614174000",
  "verification_id": "323e4567-e89b-12d3-a456-426614174000",
  "processing_time_ms": 1250.5
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | string | SUPPORTED, REFUTED, or INSUFFICIENT |
| `confidence` | float | Confidence score (0.0-1.0) |
| `evidence` | array | List of evidence items analyzed |
| `explanation` | string | Human-readable explanation |
| `claim_id` | UUID | Created claim ID |
| `verification_id` | UUID | Verification result ID |
| `processing_time_ms` | float | Total processing time |

### Examples

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "The Earth orbits the Sun",
    "max_evidence": 5
  }'
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/verify",
        json={
            "claim": "The Earth orbits the Sun",
            "max_evidence": 5
        }
    )
    result = response.json()
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']}")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    claim: 'The Earth orbits the Sun',
    max_evidence: 5
  })
});
const result = await response.json();
console.log(`Verdict: ${result.verdict}`);
```

### Error Responses

**400 Bad Request** - Invalid request
```json
{
  "detail": "Claim text cannot be empty"
}
```

**429 Too Many Requests** - Rate limit exceeded
```json
{
  "detail": "Rate limit exceeded: 5 per 1 minute"
}
```

**500 Internal Server Error** - Processing error
```json
{
  "detail": "Verification pipeline failed"
}
```

---

## POST /api/v1/claims/{claim_id}/verify

**Trigger asynchronous claim verification (RECOMMENDED)**

Queues a verification task in the background and returns immediately. Use this endpoint for production workloads to avoid timeouts.

### Request

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `claim_id` | string | Yes | Unique claim identifier |

**Body:**
```json
{
  "claim_id": "claim_123",
  "claim_text": "The Earth is round",
  "corpus_ids": ["wikipedia", "scientific_papers"],
  "options": {
    "max_evidence_items": 10,
    "confidence_threshold": 0.7,
    "return_reasoning": true,
    "search_mode": "hybrid"
  }
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claim_id` | string | Yes | Must match path parameter |
| `claim_text` | string | Yes | Claim to verify (1-5000 chars) |
| `corpus_ids` | array | No | Corpus IDs to search (null = all) |
| `options` | object | No | Verification options |
| `options.max_evidence_items` | integer | No | Max evidence (1-50, default: 10) |
| `options.confidence_threshold` | float | No | Min confidence (0.0-1.0, default: 0.5) |
| `options.return_reasoning` | boolean | No | Include reasoning (default: true) |
| `options.search_mode` | string | No | Search mode (default: "hybrid") |

### Response

**Status Code:** `202 Accepted`

**Body:**
```json
{
  "task_id": "task_abc123xyz",
  "status": "pending",
  "created_at": "2025-11-06T10:30:00Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 0
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique task identifier for polling |
| `status` | string | pending, processing, completed, or failed |
| `created_at` | datetime | Task creation timestamp |
| `completed_at` | datetime | Completion timestamp (if done) |
| `result` | object | Verification result (if completed) |
| `error` | string | Error message (if failed) |
| `progress_percentage` | integer | Progress indicator (0-100) |

### Workflow

```
1. POST /api/v1/claims/{claim_id}/verify
   ↓
   Returns: task_id, status="pending"

2. Poll GET /api/v1/tasks/{task_id}
   ↓
   Returns: status="processing", progress=45%

3. Poll GET /api/v1/verdicts/{claim_id}
   ↓
   Returns: 202 (still processing) or 200 (completed)

4. Get final result from verdict endpoint
   ↓
   Returns: Full VerificationResult
```

### Examples

**cURL:**
```bash
# Trigger verification
curl -X POST "http://localhost:8000/api/v1/claims/claim_123/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "claim_123",
    "claim_text": "The Earth is round",
    "options": {
      "max_evidence_items": 5,
      "confidence_threshold": 0.7
    }
  }'

# Response:
# {
#   "task_id": "task_abc123",
#   "status": "pending",
#   "created_at": "2025-11-06T10:30:00Z"
# }
```

**Python (with polling):**
```python
import httpx
import asyncio
import time

async def verify_claim_async(claim_id: str, claim_text: str):
    async with httpx.AsyncClient() as client:
        # Trigger verification
        response = await client.post(
            f"http://localhost:8000/api/v1/claims/{claim_id}/verify",
            json={
                "claim_id": claim_id,
                "claim_text": claim_text,
                "options": {
                    "max_evidence_items": 5,
                    "confidence_threshold": 0.7
                }
            }
        )
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"Task created: {task_id}")

        # Poll for result (with exponential backoff)
        delay = 1
        max_attempts = 30

        for attempt in range(max_attempts):
            # Check verdict endpoint
            result = await client.get(
                f"http://localhost:8000/api/v1/verdicts/{claim_id}"
            )

            if result.status_code == 200:
                # Verification complete
                return result.json()
            elif result.status_code == 202:
                # Still processing
                print(f"Attempt {attempt + 1}: Still processing...")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 10)  # Cap at 10 seconds
            else:
                # Error
                raise Exception(f"Error: {result.status_code}")

        raise TimeoutError("Verification timeout after 30 attempts")

# Usage
result = asyncio.run(verify_claim_async("claim_123", "The Earth is round"))
print(f"Verdict: {result['verdict']}")
```

**JavaScript (with polling):**
```javascript
async function verifyClaimAsync(claimId, claimText) {
  // Trigger verification
  const response = await fetch(
    `http://localhost:8000/api/v1/claims/${claimId}/verify`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        claim_id: claimId,
        claim_text: claimText,
        options: {
          max_evidence_items: 5,
          confidence_threshold: 0.7
        }
      })
    }
  );

  const taskData = await response.json();
  console.log(`Task created: ${taskData.task_id}`);

  // Poll for result
  let delay = 1000;
  const maxAttempts = 30;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const result = await fetch(
      `http://localhost:8000/api/v1/verdicts/${claimId}`
    );

    if (result.status === 200) {
      return await result.json();
    } else if (result.status === 202) {
      console.log(`Attempt ${attempt + 1}: Still processing...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay = Math.min(delay * 1.5, 10000);
    } else {
      throw new Error(`Error: ${result.status}`);
    }
  }

  throw new Error('Verification timeout');
}

// Usage
const result = await verifyClaimAsync('claim_123', 'The Earth is round');
console.log(`Verdict: ${result.verdict}`);
```

### Error Responses

**400 Bad Request** - Validation error
```json
{
  "detail": "Path claim_id 'claim_123' does not match request claim_id 'claim_456'"
}
```

**409 Conflict** - Already verified
```json
{
  "task_id": "task_existing",
  "status": "completed",
  "result": { "verdict": "SUPPORTED" }
}
```

---

## GET /api/v1/verdicts/{claim_id}

**Retrieve verification verdict for a claim**

Get the complete verification result for a claim. Returns 200 when ready, 202 if still processing.

### Request

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `claim_id` | string | Yes | Claim identifier |

### Response

**Status Code:** `200 OK` (when ready) or `202 Accepted` (still processing)

**Body (200 OK):**
```json
{
  "claim_id": "claim_123",
  "claim_text": "The Earth orbits around the Sun",
  "verdict": "SUPPORTED",
  "confidence": 0.95,
  "reasoning": "Multiple high-quality scientific sources confirm this claim.",
  "evidence": [
    {
      "id": "evidence_abc123",
      "text": "The Earth orbits the Sun once every 365.25 days.",
      "source": "Astronomy Textbook",
      "relevance": 0.98,
      "url": "https://example.com/astronomy",
      "nli_label": "entailment",
      "nli_confidence": 0.96
    }
  ],
  "verified_at": "2025-11-06T10:30:30Z",
  "processing_time_ms": 1250
}
```

**Body (202 Accepted):**
```json
{
  "detail": "Verification in progress. Please check again later.",
  "status": "processing"
}
```

### Examples

**cURL:**
```bash
curl "http://localhost:8000/api/v1/verdicts/claim_123"
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/verdicts/claim_123"
    )

    if response.status_code == 200:
        result = response.json()
        print(f"Verdict: {result['verdict']}")
    elif response.status_code == 202:
        print("Still processing...")
```

### Error Responses

**404 Not Found** - Claim not found
```json
{
  "detail": "No verification result found for claim: claim_123"
}
```

---

## GET /api/v1/tasks/{task_id}

**Get background task status**

Poll task progress and check for completion or errors.

### Request

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task identifier from verify endpoint |

### Response

**Status Code:** `200 OK`

**Body (processing):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "processing",
  "created_at": "2025-11-06T10:30:00Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 45
}
```

**Body (completed):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "completed",
  "created_at": "2025-11-06T10:30:00Z",
  "completed_at": "2025-11-06T10:30:30Z",
  "result": {
    "claim_id": "claim_123",
    "verdict": "SUPPORTED",
    "confidence": 0.95
  },
  "error": null,
  "progress_percentage": 100
}
```

**Body (failed):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "failed",
  "created_at": "2025-11-06T10:30:00Z",
  "completed_at": "2025-11-06T10:30:15Z",
  "result": null,
  "error": "Failed to retrieve evidence: Database connection timeout",
  "progress_percentage": null
}
```

### Examples

**cURL:**
```bash
curl "http://localhost:8000/api/v1/tasks/task_abc123xyz"
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/tasks/task_abc123xyz"
    )
    task = response.json()

    if task["status"] == "completed":
        print("Task completed!")
        print(f"Verdict: {task['result']['verdict']}")
    elif task["status"] == "failed":
        print(f"Task failed: {task['error']}")
    else:
        print(f"Progress: {task['progress_percentage']}%")
```

### Error Responses

**404 Not Found** - Task not found
```json
{
  "detail": "Task 'task_xyz' not found"
}
```

---

## Polling Best Practices

### Recommended Polling Strategy

```python
import time

def poll_for_result(claim_id: str, max_wait_seconds: int = 60):
    """Poll for verification result with exponential backoff."""
    start_time = time.time()
    delay = 1  # Start with 1 second

    while time.time() - start_time < max_wait_seconds:
        response = client.get(f"/api/v1/verdicts/{claim_id}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            # Still processing, wait and retry
            time.sleep(delay)
            delay = min(delay * 1.5, 10)  # Cap at 10 seconds
        else:
            # Error
            raise Exception(f"Error {response.status_code}")

    raise TimeoutError("Verification timeout")
```

### Polling Timeline

- **0-10s**: Poll every 1s (fast claims complete quickly)
- **10-30s**: Poll every 2-5s (most claims complete here)
- **30-60s**: Poll every 5-10s (complex claims)
- **60s+**: Timeout or reduce polling frequency

### Using Progress Percentage

```python
async def poll_with_progress(task_id: str):
    """Poll task status and show progress."""
    while True:
        response = await client.get(f"/api/v1/tasks/{task_id}")
        task = response.json()

        if task["status"] == "completed":
            return task["result"]
        elif task["status"] == "failed":
            raise Exception(task["error"])

        # Show progress
        progress = task.get("progress_percentage", 0)
        print(f"Progress: {progress}%")

        await asyncio.sleep(2)
```

## Rate Limiting

All verification endpoints are rate-limited to **5 requests/minute** due to computational cost.

Monitor rate limits using headers:
```
RateLimit-Limit: 5
RateLimit-Remaining: 3
RateLimit-Reset: 1699012345
```

When rate limited (429), wait for `Retry-After` seconds:
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
```
