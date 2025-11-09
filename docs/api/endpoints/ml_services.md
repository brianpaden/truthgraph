# ML Services Endpoints

ML service endpoints provide direct access to individual components of the verification pipeline: embeddings, search, and NLI inference.

## Endpoints Overview

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/api/v1/embed` | POST | 10/min | Generate text embeddings |
| `/api/v1/search` | POST | 20/min | Search for evidence |
| `/api/v1/nli` | POST | 10/min | Single NLI inference |
| `/api/v1/nli/batch` | POST | 5/min | Batch NLI inference |
| `/api/v1/verdict/{claim_id}` | GET | 20/min | Retrieve stored verdict |

---

## POST /api/v1/embed

**Generate semantic text embeddings**

Convert text into 384-dimensional vectors using sentence-transformers for semantic similarity and search.

### Request

**Body:**
```json
{
  "texts": [
    "The Earth orbits the Sun",
    "Water freezes at 0 degrees Celsius"
  ],
  "batch_size": 32
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `texts` | array | Yes | - | List of texts (1-100 items) |
| `batch_size` | integer | No | 32 | Processing batch size (1-128) |

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "embeddings": [
    [0.123, -0.456, 0.789, ...],  // 384 dimensions
    [0.234, -0.567, 0.890, ...]
  ],
  "count": 2,
  "dimension": 384,
  "processing_time_ms": 125.5
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `embeddings` | array | List of 384-dim float vectors |
| `count` | integer | Number of embeddings generated |
| `dimension` | integer | Vector dimensionality (always 384) |
| `processing_time_ms` | float | Processing time in milliseconds |

### Examples

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["The Earth orbits the Sun"]
  }'
```

**Python:**
```python
import httpx
import numpy as np

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/embed",
        json={
            "texts": [
                "The Earth orbits the Sun",
                "Water freezes at 0 degrees Celsius"
            ]
        }
    )
    data = response.json()

    embeddings = np.array(data["embeddings"])
    print(f"Generated {embeddings.shape[0]} embeddings")
    print(f"Dimensions: {embeddings.shape[1]}")

    # Compute similarity
    from numpy.linalg import norm
    cos_sim = np.dot(embeddings[0], embeddings[1]) / (
        norm(embeddings[0]) * norm(embeddings[1])
    )
    print(f"Similarity: {cos_sim:.3f}")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/embed', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    texts: ['The Earth orbits the Sun']
  })
});

const data = await response.json();
console.log(`Generated ${data.count} embeddings`);
console.log(`Dimension: ${data.dimension}`);
```

### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "detail": "All texts must be non-empty strings"
}
```

**429 Too Many Requests** - Rate limit
```json
{
  "detail": "Rate limit exceeded: 10 per 1 minute"
}
```

### Use Cases

1. **Pre-compute embeddings** for caching
2. **Similarity comparison** between texts
3. **Clustering** related content
4. **Custom vector search** implementations

---

## POST /api/v1/search

**Search for relevant evidence**

Search evidence database using hybrid (semantic + keyword), pure vector, or keyword search.

### Request

**Body:**
```json
{
  "query": "climate change effects on polar ice caps",
  "limit": 10,
  "mode": "hybrid",
  "min_similarity": 0.5,
  "tenant_id": "default",
  "source_filter": "https://example.com"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text (1-1000 chars) |
| `limit` | integer | No | 10 | Max results to return (1-100) |
| `mode` | string | No | "hybrid" | Search mode: hybrid, vector, keyword |
| `min_similarity` | float | No | 0.0 | Min similarity threshold (0.0-1.0) |
| `tenant_id` | string | No | "default" | Tenant identifier |
| `source_filter` | string | No | null | Filter by source URL |

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "results": [
    {
      "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "Studies show that polar ice caps are melting at accelerating rates...",
      "source_url": "https://example.com/climate-study",
      "similarity": 0.87,
      "rank": 1
    }
  ],
  "count": 1,
  "query": "climate change effects on polar ice caps",
  "mode": "hybrid",
  "query_time_ms": 45.2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Ordered list of search results |
| `count` | integer | Number of results returned |
| `query` | string | Original search query |
| `mode` | string | Search mode used |
| `query_time_ms` | float | Query execution time |

**Result Item Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `evidence_id` | UUID | Unique evidence identifier |
| `content` | string | Evidence text content |
| `source_url` | string | Source URL (if available) |
| `similarity` | float | Similarity score (0.0-1.0) |
| `rank` | integer | Result rank (1-based) |

### Examples

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change effects",
    "limit": 5,
    "mode": "hybrid",
    "min_similarity": 0.5
  }'
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/search",
        json={
            "query": "climate change effects on polar ice caps",
            "limit": 10,
            "mode": "hybrid",
            "min_similarity": 0.5
        }
    )
    data = response.json()

    print(f"Found {data['count']} results in {data['query_time_ms']:.2f}ms")

    for result in data["results"]:
        print(f"\nRank {result['rank']}: {result['similarity']:.2f}")
        print(f"Source: {result['source_url']}")
        print(f"Content: {result['content'][:100]}...")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'climate change effects on polar ice caps',
    limit: 10,
    mode: 'hybrid',
    min_similarity: 0.5
  })
});

const data = await response.json();
console.log(`Found ${data.count} results`);

data.results.forEach(result => {
  console.log(`${result.rank}. ${result.content.substring(0, 100)}...`);
});
```

### Search Modes

#### Hybrid Mode (Recommended)
Combines semantic vector search with keyword matching for best results.

```json
{
  "query": "machine learning applications",
  "mode": "hybrid"
}
```

#### Vector Mode
Pure semantic similarity search using embeddings.

```json
{
  "query": "artificial intelligence uses",
  "mode": "vector",
  "min_similarity": 0.6
}
```

#### Keyword Mode
Traditional text-based search (currently not implemented, returns 501).

```json
{
  "query": "exact phrase match",
  "mode": "keyword"
}
```

### Error Responses

**400 Bad Request** - Invalid parameters
```json
{
  "detail": "Query text cannot be empty"
}
```

**501 Not Implemented** - Unsupported mode
```json
{
  "detail": "Keyword search mode not yet implemented"
}
```

---

## POST /api/v1/nli

**Natural Language Inference (single pair)**

Determine the logical relationship between a premise (evidence) and hypothesis (claim).

### Request

**Body:**
```json
{
  "premise": "The Earth revolves around the Sun in an elliptical orbit",
  "hypothesis": "The Earth orbits the Sun"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `premise` | string | Yes | Premise text (1-2000 chars) |
| `hypothesis` | string | Yes | Hypothesis text (1-2000 chars) |

### Response

**Status Code:** `200 OK`

**Body:**
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Predicted label: entailment, contradiction, neutral |
| `confidence` | float | Confidence in predicted label (0.0-1.0) |
| `scores` | object | Probability scores for all three labels |
| `processing_time_ms` | float | Inference time in milliseconds |

### Label Meanings

- **entailment**: Premise supports/proves the hypothesis
- **contradiction**: Premise contradicts/disproves the hypothesis
- **neutral**: No clear logical relationship

### Examples

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/nli" \
  -H "Content-Type: application/json" \
  -d '{
    "premise": "The Earth revolves around the Sun",
    "hypothesis": "The Earth orbits the Sun"
  }'
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/nli",
        json={
            "premise": "The Earth revolves around the Sun in an elliptical orbit",
            "hypothesis": "The Earth orbits the Sun"
        }
    )
    data = response.json()

    print(f"Label: {data['label']}")
    print(f"Confidence: {data['confidence']:.2%}")
    print("\nAll scores:")
    for label, score in data["scores"].items():
        print(f"  {label}: {score:.2%}")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/nli', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    premise: 'The Earth revolves around the Sun',
    hypothesis: 'The Earth orbits the Sun'
  })
});

const data = await response.json();
console.log(`Label: ${data.label}`);
console.log(`Confidence: ${(data.confidence * 100).toFixed(1)}%`);
```

### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "detail": "Premise text cannot be empty"
}
```

---

## POST /api/v1/nli/batch

**Batch Natural Language Inference**

Process multiple premise-hypothesis pairs efficiently in one request.

### Request

**Body:**
```json
{
  "pairs": [
    ["The Earth orbits the Sun", "Earth revolves around Sun"],
    ["Water boils at 100°C", "Water freezes at 100°C"]
  ],
  "batch_size": 8
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pairs` | array | Yes | - | List of [premise, hypothesis] pairs (1-50) |
| `batch_size` | integer | No | 8 | Processing batch size (1-32) |

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "results": [
    {
      "label": "entailment",
      "confidence": 0.91,
      "scores": {
        "entailment": 0.91,
        "contradiction": 0.04,
        "neutral": 0.05
      }
    },
    {
      "label": "contradiction",
      "confidence": 0.87,
      "scores": {
        "entailment": 0.02,
        "contradiction": 0.87,
        "neutral": 0.11
      }
    }
  ],
  "count": 2,
  "total_processing_time_ms": 156.8
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | NLI results for each pair (same order as input) |
| `count` | integer | Number of results |
| `total_processing_time_ms` | float | Total processing time |

### Examples

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/nli/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "pairs": [
      ["The Earth orbits the Sun", "Earth revolves around Sun"],
      ["Water boils at 100°C", "Water freezes at 100°C"]
    ]
  }'
```

**Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    pairs = [
        ("The Earth orbits the Sun", "Earth revolves around Sun"),
        ("Water boils at 100°C", "Water freezes at 100°C"),
        ("Cats are mammals", "Cats are animals")
    ]

    response = await client.post(
        "http://localhost:8000/api/v1/nli/batch",
        json={"pairs": pairs}
    )
    data = response.json()

    print(f"Processed {data['count']} pairs in {data['total_processing_time_ms']:.2f}ms")

    for i, result in enumerate(data["results"]):
        premise, hypothesis = pairs[i]
        print(f"\n{i+1}. {hypothesis}")
        print(f"   Label: {result['label']} ({result['confidence']:.2%})")
```

**JavaScript:**
```javascript
const pairs = [
  ['The Earth orbits the Sun', 'Earth revolves around Sun'],
  ['Water boils at 100°C', 'Water freezes at 100°C']
];

const response = await fetch('http://localhost:8000/api/v1/nli/batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pairs })
});

const data = await response.json();
console.log(`Processed ${data.count} pairs`);

data.results.forEach((result, i) => {
  console.log(`${i+1}. ${result.label} (${(result.confidence * 100).toFixed(1)}%)`);
});
```

### Performance Tips

1. **Batch size**: Use batch_size=8 for balanced performance
2. **Max pairs**: Keep pairs ≤ 50 for best results
3. **Async processing**: Use async/await for non-blocking calls
4. **Caching**: Cache results for identical pairs

---

## GET /api/v1/verdict/{claim_id}

**Retrieve stored verification verdict**

Get the most recent verification result for a claim from the database.

### Request

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `claim_id` | UUID | Yes | Claim UUID |

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "claim_id": "123e4567-e89b-12d3-a456-426614174000",
  "claim_text": "The Earth is approximately 4.54 billion years old",
  "verdict": "SUPPORTED",
  "confidence": 0.87,
  "reasoning": "Strong geological evidence supports this claim",
  "evidence_count": 10,
  "supporting_evidence_count": 8,
  "refuting_evidence_count": 0,
  "created_at": "2025-10-26T12:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | UUID | Claim identifier |
| `claim_text` | string | Original claim text |
| `verdict` | string | SUPPORTED, REFUTED, or INSUFFICIENT |
| `confidence` | float | Verdict confidence (0.0-1.0) |
| `reasoning` | string | Explanation of verdict |
| `evidence_count` | integer | Total evidence analyzed |
| `supporting_evidence_count` | integer | Supporting evidence count |
| `refuting_evidence_count` | integer | Refuting evidence count |
| `created_at` | datetime | Verdict timestamp |

### Examples

**cURL:**
```bash
curl "http://localhost:8000/api/v1/verdict/123e4567-e89b-12d3-a456-426614174000"
```

**Python:**
```python
import httpx
from uuid import UUID

async with httpx.AsyncClient() as client:
    claim_id = UUID("123e4567-e89b-12d3-a456-426614174000")

    response = await client.get(
        f"http://localhost:8000/api/v1/verdict/{claim_id}"
    )
    data = response.json()

    print(f"Claim: {data['claim_text']}")
    print(f"Verdict: {data['verdict']} ({data['confidence']:.2%})")
    print(f"Evidence: {data['evidence_count']} items")
    print(f"Reasoning: {data['reasoning']}")
```

### Error Responses

**404 Not Found** - Claim or verdict not found
```json
{
  "detail": "Claim not found: 123e4567-e89b-12d3-a456-426614174000"
}
```

---

## Rate Limiting by Endpoint

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/v1/embed` | 10/min | GPU/CPU intensive |
| `/api/v1/search` | 20/min | Database queries |
| `/api/v1/nli` | 10/min | ML inference |
| `/api/v1/nli/batch` | 5/min | Heavy computation |
| `/api/v1/verdict/{claim_id}` | 20/min | Database reads |

Monitor via headers:
```
RateLimit-Limit: 10
RateLimit-Remaining: 7
RateLimit-Reset: 1699012345
```

## Common Workflows

### Custom Verification Pipeline

Build your own verification using individual services:

```python
async def custom_verify(claim: str):
    # 1. Generate claim embedding
    embed_response = await client.post("/api/v1/embed", json={"texts": [claim]})
    claim_embedding = embed_response.json()["embeddings"][0]

    # 2. Search for evidence
    search_response = await client.post(
        "/api/v1/search",
        json={"query": claim, "limit": 5, "mode": "hybrid"}
    )
    evidence = search_response.json()["results"]

    # 3. Run NLI on each evidence item
    pairs = [(item["content"], claim) for item in evidence]
    nli_response = await client.post("/api/v1/nli/batch", json={"pairs": pairs})
    nli_results = nli_response.json()["results"]

    # 4. Aggregate results
    entailment_count = sum(1 for r in nli_results if r["label"] == "entailment")
    contradiction_count = sum(1 for r in nli_results if r["label"] == "contradiction")

    if entailment_count > contradiction_count:
        verdict = "SUPPORTED"
    elif contradiction_count > entailment_count:
        verdict = "REFUTED"
    else:
        verdict = "INSUFFICIENT"

    return {"verdict": verdict, "evidence": evidence, "nli_results": nli_results}
```

### Similarity Search

Use embeddings for custom similarity:

```python
async def find_similar(query: str, candidates: list[str]):
    # Generate embeddings
    all_texts = [query] + candidates
    response = await client.post("/api/v1/embed", json={"texts": all_texts})
    embeddings = np.array(response.json()["embeddings"])

    # Compute similarities
    query_emb = embeddings[0]
    candidate_embs = embeddings[1:]

    similarities = [
        np.dot(query_emb, cand) / (np.linalg.norm(query_emb) * np.linalg.norm(cand))
        for cand in candidate_embs
    ]

    # Return sorted results
    results = sorted(zip(candidates, similarities), key=lambda x: x[1], reverse=True)
    return results
```
