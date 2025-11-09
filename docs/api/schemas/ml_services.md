# ML Services Schemas

Data models for ML service endpoints (embeddings, search, NLI).

## Table of Contents

- [Embedding](#embedding)
  - [EmbedRequest](#embedrequest)
  - [EmbedResponse](#embedresponse)
- [Search](#search)
  - [SearchRequest](#searchrequest)
  - [SearchResponse](#searchresponse)
  - [SearchResultItem](#searchresultitem)
- [NLI](#nli)
  - [NLIRequest](#nlirequest)
  - [NLIResponse](#nliresponse)
  - [NLIBatchRequest](#nlibatchrequest)
  - [NLIBatchResponse](#nlibatchresponse)
  - [NLIScores](#nliscores)
- [Verdict](#verdict)
  - [VerdictResponse](#verdictresponse)

---

## Embedding

### EmbedRequest

Request model for embedding generation.

**Schema:**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `texts` | array[string] | Yes | - | 1-100 items | Texts to embed |
| `batch_size` | integer | No | 32 | 1-128 | Processing batch size |

**Example:**
```json
{
  "texts": [
    "The Earth orbits the Sun",
    "Water freezes at 0 degrees Celsius"
  ],
  "batch_size": 32
}
```

**Validation:**
- All texts must be non-empty strings
- Maximum 100 texts per request
- batch_size must be between 1 and 128

### EmbedResponse

Response model for embedding generation.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `embeddings` | array[array[float]] | List of 384-dimensional vectors |
| `count` | integer | Number of embeddings generated |
| `dimension` | integer | Vector dimensionality (always 384) |
| `processing_time_ms` | float | Processing time in milliseconds |

**Example:**
```json
{
  "embeddings": [
    [0.123, -0.456, 0.789, ...],
    [0.234, -0.567, 0.890, ...]
  ],
  "count": 2,
  "dimension": 384,
  "processing_time_ms": 125.5
}
```

---

## Search

### SearchRequest

Request model for evidence search.

**Schema:**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `query` | string | Yes | - | 1-1000 chars | Search query text |
| `limit` | integer | No | 10 | 1-100 | Max results to return |
| `mode` | string | No | "hybrid" | enum | Search mode |
| `min_similarity` | float | No | 0.0 | 0.0-1.0 | Min similarity threshold |
| `tenant_id` | string | No | "default" | max 255 chars | Tenant identifier |
| `source_filter` | string | No | null | - | Filter by source URL |

**Mode Values:**
- `hybrid`: Combines semantic + keyword search
- `vector`: Pure semantic similarity
- `keyword`: Traditional text search (not implemented)

**Example:**
```json
{
  "query": "climate change effects on polar ice caps",
  "limit": 10,
  "mode": "hybrid",
  "min_similarity": 0.5,
  "tenant_id": "default"
}
```

### SearchResponse

Response model for search results.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array[[SearchResultItem](#searchresultitem)] | Ordered search results |
| `count` | integer | Number of results returned |
| `query` | string | Original search query |
| `mode` | string | Search mode used |
| `query_time_ms` | float | Query execution time |

**Example:**
```json
{
  "results": [
    {
      "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "Climate research findings...",
      "source_url": "https://example.com/study",
      "similarity": 0.87,
      "rank": 1
    }
  ],
  "count": 1,
  "query": "climate change effects",
  "mode": "hybrid",
  "query_time_ms": 45.2
}
```

### SearchResultItem

Individual search result.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `evidence_id` | UUID | Unique evidence identifier |
| `content` | string | Evidence text content |
| `source_url` | string | Source URL (optional) |
| `similarity` | float | Similarity score (0.0-1.0) |
| `rank` | integer | Result rank (1-based) |

**Example:**
```json
{
  "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
  "content": "Studies show polar ice caps are melting at accelerating rates...",
  "source_url": "https://example.com/climate-study",
  "similarity": 0.87,
  "rank": 1
}
```

---

## NLI

### NLIRequest

Request model for single NLI inference.

**Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `premise` | string | Yes | 1-2000 chars | Premise text (evidence) |
| `hypothesis` | string | Yes | 1-2000 chars | Hypothesis text (claim) |

**Example:**
```json
{
  "premise": "The Earth revolves around the Sun in an elliptical orbit",
  "hypothesis": "The Earth orbits the Sun"
}
```

### NLIResponse

Response model for NLI inference.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Predicted label: entailment, contradiction, neutral |
| `confidence` | float | Confidence in predicted label (0.0-1.0) |
| `scores` | [NLIScores](#nliscores) | Probability scores for all labels |
| `processing_time_ms` | float | Inference time in milliseconds |

**Example:**
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

### NLIBatchRequest

Request model for batch NLI inference.

**Schema:**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `pairs` | array[tuple] | Yes | - | 1-50 items | (premise, hypothesis) pairs |
| `batch_size` | integer | No | 8 | 1-32 | Processing batch size |

**Example:**
```json
{
  "pairs": [
    ["Evidence text 1", "Claim text 1"],
    ["Evidence text 2", "Claim text 2"]
  ],
  "batch_size": 8
}
```

### NLIBatchResponse

Response model for batch NLI inference.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array[[NLIResponse](#nliresponse)] | NLI results for each pair |
| `count` | integer | Number of results |
| `total_processing_time_ms` | float | Total processing time |

**Example:**
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
    }
  ],
  "count": 1,
  "total_processing_time_ms": 156.8
}
```

### NLIScores

Probability scores for all NLI labels.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `entailment` | float | Entailment probability (0.0-1.0) |
| `contradiction` | float | Contradiction probability (0.0-1.0) |
| `neutral` | float | Neutral probability (0.0-1.0) |

**Example:**
```json
{
  "entailment": 0.92,
  "contradiction": 0.03,
  "neutral": 0.05
}
```

**Note:** Scores sum to approximately 1.0 (may have small floating-point variance).

---

## Verdict

### VerdictResponse

Response model for stored verdict retrieval.

**Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | UUID | Claim identifier |
| `claim_text` | string | Original claim text |
| `verdict` | string | SUPPORTED, REFUTED, or INSUFFICIENT |
| `confidence` | float | Verdict confidence (0.0-1.0) |
| `reasoning` | string | Explanation (optional) |
| `evidence_count` | integer | Total evidence analyzed |
| `supporting_evidence_count` | integer | Supporting evidence count |
| `refuting_evidence_count` | integer | Refuting evidence count |
| `created_at` | datetime | Verdict timestamp |

**Example:**
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

---

## TypeScript Types

```typescript
// Embedding
interface EmbedRequest {
  texts: string[];
  batch_size?: number;
}

interface EmbedResponse {
  embeddings: number[][];
  count: number;
  dimension: number;
  processing_time_ms: number;
}

// Search
interface SearchRequest {
  query: string;
  limit?: number;
  mode?: 'hybrid' | 'vector' | 'keyword';
  min_similarity?: number;
  tenant_id?: string;
  source_filter?: string | null;
}

interface SearchResultItem {
  evidence_id: string;
  content: string;
  source_url: string | null;
  similarity: number;
  rank: number;
}

interface SearchResponse {
  results: SearchResultItem[];
  count: number;
  query: string;
  mode: string;
  query_time_ms: number;
}

// NLI
interface NLIRequest {
  premise: string;
  hypothesis: string;
}

interface NLIScores {
  entailment: number;
  contradiction: number;
  neutral: number;
}

interface NLIResponse {
  label: 'entailment' | 'contradiction' | 'neutral';
  confidence: number;
  scores: NLIScores;
  processing_time_ms?: number;
}

interface NLIBatchRequest {
  pairs: [string, string][];
  batch_size?: number;
}

interface NLIBatchResponse {
  results: NLIResponse[];
  count: number;
  total_processing_time_ms: number;
}

// Verdict
interface VerdictResponse {
  claim_id: string;
  claim_text: string;
  verdict: 'SUPPORTED' | 'REFUTED' | 'INSUFFICIENT';
  confidence: number;
  reasoning: string | null;
  evidence_count: number;
  supporting_evidence_count: number;
  refuting_evidence_count: number;
  created_at: string;  // ISO 8601
}
```

---

## Python Models

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional
from uuid import UUID
from datetime import datetime

# Embedding
class EmbedRequest(BaseModel):
    texts: Annotated[list[str], Field(min_length=1, max_length=100)]
    batch_size: Annotated[int, Field(default=32, ge=1, le=128)] = 32

class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    count: int
    dimension: int
    processing_time_ms: float

# Search
class SearchRequest(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=1000)]
    limit: Annotated[int, Field(default=10, ge=1, le=100)] = 10
    mode: Literal["hybrid", "vector", "keyword"] = "hybrid"
    min_similarity: Annotated[float, Field(default=0.0, ge=0.0, le=1.0)] = 0.0
    tenant_id: str = "default"
    source_filter: Optional[str] = None

class SearchResultItem(BaseModel):
    evidence_id: UUID
    content: str
    source_url: Optional[str] = None
    similarity: Annotated[float, Field(ge=0.0, le=1.0)]
    rank: Annotated[int, Field(ge=1)]

class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    count: int
    query: str
    mode: str
    query_time_ms: float

# NLI
class NLIRequest(BaseModel):
    premise: Annotated[str, Field(min_length=1, max_length=2000)]
    hypothesis: Annotated[str, Field(min_length=1, max_length=2000)]

class NLIScores(BaseModel):
    entailment: Annotated[float, Field(ge=0.0, le=1.0)]
    contradiction: Annotated[float, Field(ge=0.0, le=1.0)]
    neutral: Annotated[float, Field(ge=0.0, le=1.0)]

class NLIResponse(BaseModel):
    label: Literal["entailment", "contradiction", "neutral"]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    scores: NLIScores
    processing_time_ms: Optional[float] = None

class NLIBatchRequest(BaseModel):
    pairs: Annotated[list[tuple[str, str]], Field(min_length=1, max_length=50)]
    batch_size: Annotated[int, Field(default=8, ge=1, le=32)] = 8

class NLIBatchResponse(BaseModel):
    results: list[NLIResponse]
    count: int
    total_processing_time_ms: float

# Verdict
class VerdictResponse(BaseModel):
    claim_id: UUID
    claim_text: str
    verdict: Literal["SUPPORTED", "REFUTED", "INSUFFICIENT"]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    reasoning: Optional[str] = None
    evidence_count: int
    supporting_evidence_count: int
    refuting_evidence_count: int
    created_at: datetime
```

---

## Validation Examples

### Valid Embedding Request

```python
request = EmbedRequest(
    texts=["Hello world", "Python is great"],
    batch_size=32
)
# ✓ Valid
```

### Invalid Embedding Request

```python
request = EmbedRequest(
    texts=[],  # Empty list
    batch_size=32
)
# ✗ ValidationError: ensure this value has at least 1 items
```

### Valid Search Request

```python
request = SearchRequest(
    query="machine learning",
    limit=10,
    mode="hybrid",
    min_similarity=0.5
)
# ✓ Valid
```

### Invalid Search Request

```python
request = SearchRequest(
    query="",  # Empty query
    limit=200  # Exceeds max
)
# ✗ ValidationError: query must be non-empty, limit must be <= 100
```

### Valid NLI Request

```python
request = NLIRequest(
    premise="The Earth orbits the Sun",
    hypothesis="Earth revolves around Sun"
)
# ✓ Valid
```

### Invalid NLI Batch Request

```python
request = NLIBatchRequest(
    pairs=[],  # Empty pairs
    batch_size=8
)
# ✗ ValidationError: ensure this value has at least 1 items
```

---

## See Also

- [ML Services Endpoints](../endpoints/ml_services.md)
- [Verification Schemas](verification.md)
- [Error Codes](../errors/error_codes.md)
- [API Overview](../README.md)
