# TruthGraph User Guide

**Version:** 0.2.0 (Phase 2)
**Last Updated:** October 26, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Using the API](#using-the-api)
4. [Understanding Verdicts](#understanding-verdicts)
5. [Common Use Cases](#common-use-cases)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Introduction

TruthGraph is an AI-powered fact verification system that helps you verify claims by analyzing them against a database of evidence. It uses state-of-the-art machine learning models to:

- **Understand Claims**: Generate semantic embeddings to capture meaning
- **Find Evidence**: Search through evidence using vector similarity and keywords
- **Verify Claims**: Compare claims against evidence using Natural Language Inference
- **Deliver Verdicts**: Aggregate results into clear SUPPORTED, REFUTED, or INSUFFICIENT verdicts

### What Can TruthGraph Do?

- ✅ Verify factual claims against your evidence database
- ✅ Find relevant supporting or refuting evidence
- ✅ Provide confidence scores and explanations
- ✅ Handle batch processing for multiple claims
- ✅ Scale to handle 100+ concurrent requests

### What TruthGraph Cannot Do

- ❌ Verify claims without evidence in the database
- ❌ Understand sarcasm, jokes, or nuanced opinions
- ❌ Process images, videos, or audio (text-only)
- ❌ Make subjective judgments or ethical decisions

---

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- 4GB+ RAM available
- Internet connection (for first-time model download ~520MB)

### Quick Start

1. **Start TruthGraph Services**

```bash
# Clone the repository
git clone https://github.com/yourusername/truthgraph.git
cd truthgraph

# Start all services
task dev
```

1. **Wait for Services to Start** (~30 seconds)

```bash
# Check service health
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "embedding_service": "ready",
    "nli_service": "ready"
  }
}
```

1. **Access the Interactive API Documentation**

Open your browser to: <http://localhost:8000/docs>

---

## Using the API

### 1. Verify a Claim (Recommended)

The `/api/v1/verify` endpoint is the main entry point for fact-checking.

**Example: Verify a Scientific Claim**

```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "The Earth orbits around the Sun",
    "tenant_id": "default",
    "max_evidence": 10,
    "min_similarity": 0.5
  }'
```

**Response:**

```json
{
  "claim_id": "clm_abc123",
  "verdict": "SUPPORTED",
  "confidence": 0.92,
  "evidence_count": 5,
  "reasoning": "The claim is strongly supported by 5 pieces of evidence with high confidence. All evidence confirms the heliocentric model.",
  "evidence_items": [
    {
      "text": "The Earth takes 365.25 days to complete one orbit around the Sun",
      "similarity": 0.87,
      "nli_label": "entailment",
      "confidence": 0.95
    }
  ],
  "pipeline_duration_ms": 3240,
  "cached": false
}
```

### 2. Search for Evidence

Find relevant evidence without running full verification.

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change effects",
    "mode": "hybrid",
    "limit": 10,
    "min_similarity": 0.6
  }'
```

### 3. Generate Embeddings

Create semantic embeddings for your own text.

```bash
curl -X POST "http://localhost:8000/api/v1/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["The sky is blue", "Water is wet"],
    "batch_size": 32
  }'
```

### 4. Check Entailment (NLI)

Directly test if a hypothesis follows from a premise.

```bash
curl -X POST "http://localhost:8000/api/v1/nli" \
  -H "Content-Type: application/json" \
  -d '{
    "premise": "The Earth orbits the Sun",
    "hypothesis": "The Sun is at the center of our solar system"
  }'
```

**Response:**

```json
{
  "label": "entailment",
  "confidence": 0.98,
  "scores": {
    "entailment": 0.98,
    "contradiction": 0.01,
    "neutral": 0.01
  }
}
```

---

## Understanding Verdicts

### Verdict Types

#### ✅ SUPPORTED

The claim is backed by strong evidence.

- **Confidence > 0.7**: High confidence, strong evidence
- **Confidence 0.5-0.7**: Moderate confidence, some support
- **Confidence < 0.5**: Low confidence, weak support

**Example:**
```text
Claim: "Water boils at 100°C at sea level"
Verdict: SUPPORTED (confidence: 0.95)
```

#### ❌ REFUTED

The claim contradicts available evidence.

- **Confidence > 0.7**: Strong refutation
- **Confidence 0.5-0.7**: Moderate contradiction
- **Confidence < 0.5**: Weak contradiction

**Example:**
```text
Claim: "The Earth is flat"
Verdict: REFUTED (confidence: 0.91)
```

#### ⚠️ INSUFFICIENT

Not enough evidence to make a determination.

- **No Evidence Found**: No relevant evidence in database
- **Conflicting Evidence**: Evidence both supports and refutes
- **Low Confidence**: All evidence below confidence threshold

**Example:**
```text
Claim: "Aliens visited Earth in 2024"
Verdict: INSUFFICIENT (confidence: 0.42)
Reasoning: "No relevant evidence found in database"
```

### Confidence Scores

Confidence scores range from 0.0 to 1.0:

| Range | Interpretation |
|-------|----------------|
| 0.9 - 1.0 | Very High Confidence |
| 0.7 - 0.9 | High Confidence |
| 0.5 - 0.7 | Moderate Confidence |
| 0.3 - 0.5 | Low Confidence |
| 0.0 - 0.3 | Very Low Confidence |

---

## Common Use Cases

### Use Case 1: Fact-Checking News Articles

**Scenario:** You want to verify claims made in a news article.

```python
import requests

claims = [
    "The unemployment rate fell to 3.5% in September 2024",
    "COVID-19 vaccines are 95% effective",
    "The stock market hit an all-time high"
]

for claim in claims:
    response = requests.post(
        "http://localhost:8000/api/v1/verify",
        json={
            "claim": claim,
            "tenant_id": "news_org",
            "max_evidence": 5
        }
    )
    result = response.json()
    print(f"{claim}")
    print(f"→ {result['verdict']} (confidence: {result['confidence']:.2%})")
    print(f"→ {result['reasoning']}\n")
```

### Use Case 2: Building Evidence Database

**Scenario:** You're importing evidence from various sources.

```python
from truthgraph.services.ml import get_embedding_service
from sqlalchemy.orm import Session

embedder = get_embedding_service()

# Process documents
for doc in documents:
    # Generate embedding
    embedding = embedder.embed_text(doc.text)

    # Store in database
    evidence = Evidence(
        content=doc.text,
        source_url=doc.url,
        tenant_id="my_org"
    )
    db.add(evidence)

    # Store embedding
    emb_record = EmbeddingRecord(
        evidence_id=evidence.id,
        embedding=embedding,
        model_name="all-MiniLM-L6-v2",
        dimension=384
    )
    db.add(emb_record)

db.commit()
```

### Use Case 3: Batch Verification

**Scenario:** You need to verify hundreds of claims efficiently.

```python
import asyncio
import aiohttp

async def verify_claim(session, claim):
    async with session.post(
        "http://localhost:8000/api/v1/verify",
        json={"claim": claim, "tenant_id": "batch"}
    ) as response:
        return await response.json()

async def batch_verify(claims):
    async with aiohttp.ClientSession() as session:
        tasks = [verify_claim(session, claim) for claim in claims]
        results = await asyncio.gather(*tasks)
        return results

# Verify 100 claims concurrently
results = asyncio.run(batch_verify(claims))
```

### Use Case 4: Monitoring API Performance

**Scenario:** You want to track API performance and cache hit rates.

```python
response = requests.post(
    "http://localhost:8000/api/v1/verify",
    json={"claim": "Example claim", "tenant_id": "monitor"}
)

# Check response headers
process_time = response.headers.get("X-Process-Time")
cached = response.json().get("cached", False)

print(f"Process time: {process_time}ms")
print(f"Cached: {cached}")
```

---

## Troubleshooting

### Problem: "Service Unhealthy" Error

**Symptoms:**
```json
{
  "status": "unhealthy",
  "services": {
    "database": "disconnected"
  }
}
```

**Solutions:**
1. Check database is running: `docker ps | grep postgres`
2. Restart services: `task dev`
3. Check logs: `task logs`

### Problem: Slow First Request (~10 seconds)

**Cause:** ML models need to be loaded into memory on first use.

**Solutions:**
1. Pre-warm models: `task ml:warmup`
2. Use model caching (already enabled by default)
3. Subsequent requests will be fast (~50-200ms)

### Problem: "No Evidence Found"

**Cause:** The claim has no relevant evidence in your database.

**Solutions:**
1. Add more evidence to your database
2. Lower `min_similarity` threshold (default: 0.5)
3. Check if evidence exists: `task db:query "SELECT COUNT(*) FROM evidence"`

### Problem: Rate Limit Exceeded

**Symptoms:**
```json
{
  "detail": "Rate limit exceeded: 10 requests per minute"
}
```

**Solutions:**
1. Wait for rate limit window to reset (1 minute)
2. Adjust rate limits in configuration
3. Use batch endpoints for multiple items

### Problem: Low Confidence Verdicts

**Cause:** Evidence quality or relevance issues.

**Solutions:**
1. Review evidence quality in database
2. Add more diverse evidence sources
3. Lower confidence thresholds if appropriate
4. Check evidence similarity scores

---

## Best Practices

### 1. Evidence Quality

✅ **Do:**
- Use authoritative, fact-checked sources
- Include diverse perspectives
- Keep evidence text concise (1-3 sentences)
- Add source URLs and metadata
- Update evidence regularly

❌ **Don't:**
- Use opinion pieces as evidence
- Include extremely long text passages
- Mix multiple facts in one evidence item
- Forget to cite sources

### 2. Claim Formulation

✅ **Do:**
- Make claims specific and testable
- Use clear, unambiguous language
- Keep claims to one fact per request
- Use present tense when possible

❌ **Don't:**
- Ask questions (convert to statements)
- Use vague language ("maybe", "possibly")
- Combine multiple claims
- Use sarcasm or irony

**Good Claims:**
- "The Earth's average temperature increased by 1.1°C since 1880"
- "Python was first released in 1991"
- "The human body contains approximately 37 trillion cells"

**Bad Claims:**
- "Isn't climate change real?" (question)
- "Some people say vaccines work" (vague)
- "The Earth is round and orbits the Sun" (multiple claims)

### 3. Performance Optimization

**For Low-Latency Applications:**
```python
# Use smaller top_k values
verify(claim, max_evidence=3)  # Faster

# Cache aggressively (automatic)
# Repeat queries are <5ms

# Use hybrid search for better relevance
search(query, mode="hybrid")
```

**For High-Throughput Applications:**
```python
# Use batch endpoints
nli_batch(premises, hypotheses, batch_size=16)

# Process multiple claims concurrently
# System handles 100+ concurrent requests
```

### 4. Monitoring and Logging

**Track Key Metrics:**
- Verdict distribution (SUPPORTED/REFUTED/INSUFFICIENT)
- Average confidence scores
- Cache hit rate
- Evidence retrieval quality
- API latency (p50, p95, p99)

**Example Monitoring Code:**
```python
import structlog

logger = structlog.get_logger()

result = verify_claim(claim)

logger.info(
    "verification_complete",
    claim_id=result["claim_id"],
    verdict=result["verdict"],
    confidence=result["confidence"],
    duration_ms=result["pipeline_duration_ms"],
    cached=result["cached"]
)
```

### 5. Security Considerations

**Multi-Tenancy:**
- Always set `tenant_id` to isolate data
- Use unique tenant IDs per organization
- Evidence is filtered by tenant automatically

**Rate Limiting:**
- Respect rate limits (10 req/min for ML endpoints)
- Use batch endpoints for multiple items
- Cache results when possible

**Data Privacy:**
- Claims and evidence are stored in database
- Use appropriate database access controls
- Consider encryption for sensitive data

---

## API Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/verify` | 10 req/min | 60 seconds |
| `/api/v1/embed` | 10 req/min | 60 seconds |
| `/api/v1/nli` | 10 req/min | 60 seconds |
| `/api/v1/search` | 60 req/min | 60 seconds |
| `/health` | Unlimited | - |

**Rate Limit Headers:**
```text
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1698765432
```

---

## Support and Resources

### Documentation

- **API Reference**: <http://localhost:8000/docs>
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Architecture**: [PHASE_2_IMPLEMENTATION_PLAN.md](../PHASE_2_IMPLEMENTATION_PLAN.md)
- **Performance**: [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)

### Getting Help

1. **Interactive Docs**: <http://localhost:8000/docs>
2. **GitHub Issues**: <https://github.com/yourusername/truthgraph/issues>
3. **Documentation**: Check the `docs/` folder

### Contributing

We welcome contributions! See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for:
- Setting up development environment
- Running tests
- Code standards
- Pull request process

---

## Quick Reference

### Essential Commands

```bash
# Start services
task dev

# Check health
curl http://localhost:8000/health

# View logs
task logs

# Run tests
task test

# Database migration
task db:migrate

# Warm up ML models
task ml:warmup

# Run benchmarks
task ml:benchmark
```

### Essential Endpoints

```bash
# Verify claim
POST /api/v1/verify

# Search evidence
POST /api/v1/search

# Generate embeddings
POST /api/v1/embed

# Check entailment
POST /api/v1/nli

# Health check
GET /health
```

---

**Happy Fact-Checking! 🔍✨**

For more detailed technical information, see the [Developer Guide](DEVELOPER_GUIDE.md).
