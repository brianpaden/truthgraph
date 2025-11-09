# Complete Verification Walkthrough

This guide walks through a complete claim verification workflow step-by-step.

## Scenario

We want to verify the claim: **"The Earth is approximately 4.54 billion years old"**

## Step 1: Check API Health

Before starting, verify the API is healthy:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T10:00:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "message": "Database connection OK"
    },
    "embedding_service": {
      "status": "healthy",
      "message": "Embedding service available (loaded: true)"
    },
    "nli_service": {
      "status": "healthy",
      "message": "NLI service available (initialized: true)"
    }
  },
  "version": "2.0.0"
}
```

All services are healthy - we're ready to proceed!

## Step 2: Trigger Async Verification

Use the async endpoint for production workloads:

```bash
curl -X POST "http://localhost:8000/api/v1/claims/claim_earth_age/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "claim_earth_age",
    "claim_text": "The Earth is approximately 4.54 billion years old",
    "options": {
      "max_evidence_items": 10,
      "confidence_threshold": 0.7,
      "return_reasoning": true,
      "search_mode": "hybrid"
    }
  }'
```

**Response (202 Accepted):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "pending",
  "created_at": "2025-11-07T10:00:01Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 0
}
```

The verification is queued! Note the `task_id` for polling.

## Step 3: Poll Task Status

Check the task progress:

```bash
curl "http://localhost:8000/api/v1/tasks/task_abc123xyz"
```

**Response (Processing):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "processing",
  "created_at": "2025-11-07T10:00:01Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 45
}
```

Still processing... Let's wait a moment and try again.

**Response (Completed):**
```json
{
  "task_id": "task_abc123xyz",
  "status": "completed",
  "created_at": "2025-11-07T10:00:01Z",
  "completed_at": "2025-11-07T10:00:05Z",
  "result": {
    "claim_id": "claim_earth_age",
    "verdict": "SUPPORTED",
    "confidence": 0.92
  },
  "error": null,
  "progress_percentage": 100
}
```

Task completed! Now retrieve the full verdict.

## Step 4: Get Complete Verdict

Retrieve the detailed verification result:

```bash
curl "http://localhost:8000/api/v1/verdicts/claim_earth_age"
```

**Response (200 OK):**
```json
{
  "claim_id": "claim_earth_age",
  "claim_text": "The Earth is approximately 4.54 billion years old",
  "verdict": "SUPPORTED",
  "confidence": 0.92,
  "reasoning": "Analysis of 10 scientific evidence items shows strong support for this claim. The age of 4.54 billion years is widely accepted in the scientific community based on radiometric dating of meteorites and Earth rocks.",
  "evidence": [
    {
      "id": "evidence_1",
      "text": "Radiometric dating of meteorites indicates Earth formed approximately 4.54 billion years ago, consistent with other solar system bodies.",
      "source": "Geological Survey Report 2023",
      "relevance": 0.96,
      "url": "https://example.com/geology/earth-age",
      "publication_date": "2023-03-15",
      "nli_label": "entailment",
      "nli_confidence": 0.94
    },
    {
      "id": "evidence_2",
      "text": "The oldest Earth rocks dated using uranium-lead isotope methods are approximately 4.4 billion years old, supporting the 4.54 billion year estimate.",
      "source": "Nature Geoscience",
      "relevance": 0.93,
      "url": "https://example.com/nature/earth-rocks",
      "publication_date": "2022-11-08",
      "nli_label": "entailment",
      "nli_confidence": 0.91
    },
    {
      "id": "evidence_3",
      "text": "Multiple independent dating methods converge on an Earth age of 4.54 ± 0.05 billion years.",
      "source": "Annual Review of Earth Sciences",
      "relevance": 0.98,
      "url": "https://example.com/review/dating-methods",
      "publication_date": "2023-01-20",
      "nli_label": "entailment",
      "nli_confidence": 0.96
    }
  ],
  "verified_at": "2025-11-07T10:00:05Z",
  "processing_time_ms": 4250,
  "corpus_ids_searched": ["scientific_papers", "geology_database"]
}
```

## Step 5: Analyze the Result

### Verdict Analysis

- **Verdict**: SUPPORTED
- **Confidence**: 92% (very high confidence)
- **Evidence Count**: 10 items analyzed (showing top 3)
- **Processing Time**: 4.25 seconds

### Evidence Breakdown

All evidence items show:
- **NLI Label**: entailment (supporting the claim)
- **High Relevance**: 0.93-0.98 similarity scores
- **High NLI Confidence**: 0.91-0.96 confidence

### Reasoning

The system provided a clear explanation:
> "Analysis of 10 scientific evidence items shows strong support for this claim. The age of 4.54 billion years is widely accepted in the scientific community based on radiometric dating of meteorites and Earth rocks."

## Alternative: Simple Synchronous Verification

For simpler use cases, use the synchronous endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "The Earth is approximately 4.54 billion years old",
    "max_evidence": 10,
    "confidence_threshold": 0.7
  }'
```

This returns the complete result immediately (may timeout for complex claims).

## Complete Python Example

```python
import httpx
import asyncio
import time


async def verify_claim_complete(claim_id: str, claim_text: str):
    """Complete verification workflow with polling."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Check health
        health = await client.get("http://localhost:8000/health")
        if health.json()["status"] != "healthy":
            raise Exception("API not healthy")

        print("✓ API is healthy")

        # 2. Trigger verification
        response = await client.post(
            f"http://localhost:8000/api/v1/claims/{claim_id}/verify",
            json={
                "claim_id": claim_id,
                "claim_text": claim_text,
                "options": {
                    "max_evidence_items": 10,
                    "confidence_threshold": 0.7,
                    "return_reasoning": True,
                },
            },
        )

        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✓ Task created: {task_id}")

        # 3. Poll for completion
        delay = 1
        max_attempts = 30

        for attempt in range(1, max_attempts + 1):
            # Check verdict
            verdict_response = await client.get(
                f"http://localhost:8000/api/v1/verdicts/{claim_id}"
            )

            if verdict_response.status_code == 200:
                result = verdict_response.json()
                print(f"✓ Verification complete (attempt {attempt})")

                # Print results
                print(f"\nClaim: {result['claim_text']}")
                print(f"Verdict: {result['verdict']}")
                print(f"Confidence: {result['confidence']:.2%}")
                print(f"Evidence: {len(result['evidence'])} items")
                print(f"\nReasoning:\n{result['reasoning']}")

                print("\nTop Evidence:")
                for i, evidence in enumerate(result["evidence"][:3], 1):
                    print(f"\n{i}. {evidence['text'][:100]}...")
                    print(f"   Source: {evidence.get('source', 'N/A')}")
                    print(f"   NLI: {evidence['nli_label']} ({evidence['nli_confidence']:.2%})")

                return result

            elif verdict_response.status_code == 202:
                print(f"  Attempt {attempt}: Processing... (wait {delay}s)")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 10)

            else:
                raise Exception(f"Error {verdict_response.status_code}")

        raise TimeoutError("Verification timeout")


# Run the example
result = asyncio.run(
    verify_claim_complete(
        "claim_earth_age",
        "The Earth is approximately 4.54 billion years old"
    )
)
```

**Output:**
```
✓ API is healthy
✓ Task created: task_abc123xyz
  Attempt 1: Processing... (wait 1s)
  Attempt 2: Processing... (wait 1s)
✓ Verification complete (attempt 3)

Claim: The Earth is approximately 4.54 billion years old
Verdict: SUPPORTED
Confidence: 92.00%
Evidence: 10 items

Reasoning:
Analysis of 10 scientific evidence items shows strong support for this claim...

Top Evidence:

1. Radiometric dating of meteorites indicates Earth formed approximately 4.54 billion years ago...
   Source: Geological Survey Report 2023
   NLI: entailment (94.00%)

2. The oldest Earth rocks dated using uranium-lead isotope methods are approximately 4.4 billion...
   Source: Nature Geoscience
   NLI: entailment (91.00%)

3. Multiple independent dating methods converge on an Earth age of 4.54 ± 0.05 billion years.
   Source: Annual Review of Earth Sciences
   NLI: entailment (96.00%)
```

## Error Handling

### Handle Rate Limits

```python
response = await client.post("/api/v1/verify", json=request_data)

if response.status_code == 429:
    # Rate limit exceeded
    retry_after = int(response.headers.get("Retry-After", 60))
    print(f"Rate limited. Retry after {retry_after} seconds")
    await asyncio.sleep(retry_after)
    # Retry request
```

### Handle Validation Errors

```python
if response.status_code == 400:
    error = response.json()
    print(f"Validation error: {error['detail']}")
```

### Handle Server Errors

```python
if response.status_code >= 500:
    print("Server error. Try again later.")
    # Implement retry with exponential backoff
```

## Best Practices

1. **Use Async Endpoints**: For production, always use async verification
2. **Implement Polling**: Use exponential backoff when polling
3. **Check Health First**: Verify API health before making requests
4. **Handle Rate Limits**: Respect `Retry-After` headers
5. **Cache Results**: Store verdicts to avoid re-verification
6. **Set Timeouts**: Don't wait indefinitely for results
7. **Monitor Progress**: Use task status endpoint for long operations

## Next Steps

- Review [Verification API Documentation](../endpoints/verification.md)
- Explore [ML Services](../endpoints/ml_services.md)
- Check [Error Codes](../errors/error_codes.md)
- Read [Schema Documentation](../schemas/verification.md)
