# Verification Schemas

Data models for claim verification requests and responses.

## Table of Contents

- [VerifyClaimRequest](#verifyclaimrequest)
- [VerificationOptions](#verificationoptions)
- [VerificationResult](#verificationresult)
- [TaskStatus](#taskstatus)
- [EvidenceItem](#evidenceitem)

---

## VerifyClaimRequest

Request model for async claim verification endpoint.

### Schema

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `claim_id` | string | Yes | min_length=1 | Unique claim identifier |
| `claim_text` | string | Yes | 1-5000 chars | Claim text to verify |
| `corpus_ids` | array[string] | No | - | Specific corpus IDs to search (null = all) |
| `options` | [VerificationOptions](#verificationoptions) | No | - | Verification configuration options |

### Example

```json
{
  "claim_id": "claim_123",
  "claim_text": "The Earth orbits around the Sun",
  "corpus_ids": ["wikipedia", "scientific_papers"],
  "options": {
    "max_evidence_items": 5,
    "confidence_threshold": 0.7,
    "return_reasoning": true,
    "search_mode": "hybrid"
  }
}
```

### Validation Rules

- **claim_text**: Cannot be empty after stripping whitespace
- **claim_text**: Maximum 5000 characters
- **corpus_ids**: Cannot be empty array (use null instead)
- **corpus_ids**: All IDs must be non-empty strings

### Python Model

```python
from pydantic import BaseModel, Field
from typing import Optional, Annotated

class VerifyClaimRequest(BaseModel):
    claim_id: Annotated[str, Field(min_length=1)]
    claim_text: Annotated[str, Field(min_length=1, max_length=5000)]
    corpus_ids: Optional[list[str]] = None
    options: Optional[VerificationOptions] = None
```

---

## VerificationOptions

Configuration options for verification behavior.

### Schema

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `max_evidence_items` | integer | No | 10 | 1-50 | Maximum evidence items to retrieve |
| `confidence_threshold` | float | No | 0.5 | 0.0-1.0 | Minimum confidence for verdict |
| `return_reasoning` | boolean | No | true | - | Include reasoning explanation |
| `search_mode` | string | No | "hybrid" | enum | Search strategy: hybrid, vector, keyword |

### Example

```json
{
  "max_evidence_items": 10,
  "confidence_threshold": 0.7,
  "return_reasoning": true,
  "search_mode": "hybrid"
}
```

### Search Mode Values

- **hybrid**: Combines semantic vector search with keyword matching (recommended)
- **vector**: Pure semantic similarity using embeddings
- **keyword**: Traditional text-based search (not yet implemented)

### Python Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal

class VerificationOptions(BaseModel):
    max_evidence_items: Annotated[int, Field(default=10, ge=1, le=50)] = 10
    confidence_threshold: Annotated[float, Field(default=0.5, ge=0.0, le=1.0)] = 0.5
    return_reasoning: Annotated[bool, Field(default=True)] = True
    search_mode: Annotated[
        Literal["hybrid", "vector", "keyword"],
        Field(default="hybrid")
    ] = "hybrid"
```

---

## VerificationResult

Complete verification result with verdict and evidence.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | string | Original claim identifier |
| `claim_text` | string | Original claim text verified |
| `verdict` | string | Final verdict: SUPPORTED, REFUTED, NOT_ENOUGH_INFO |
| `confidence` | float | Confidence in verdict (0.0-1.0) |
| `reasoning` | string | Human-readable explanation (optional) |
| `evidence` | array[[EvidenceItem](#evidenceitem)] | Evidence items analyzed |
| `verified_at` | datetime | Verification completion timestamp |
| `processing_time_ms` | integer | Total processing time in milliseconds |
| `corpus_ids_searched` | array[string] | Corpus IDs searched (optional) |
| `validation_warnings` | array[string] | Input validation warnings (optional) |

### Example

```json
{
  "claim_id": "claim_123",
  "claim_text": "The Earth orbits around the Sun",
  "verdict": "SUPPORTED",
  "confidence": 0.95,
  "reasoning": "Multiple high-quality scientific sources confirm that Earth orbits the Sun. This is a well-established astronomical fact supported by centuries of observations.",
  "evidence": [
    {
      "id": "evidence_abc123",
      "text": "The Earth orbits the Sun once every 365.25 days in an elliptical path.",
      "source": "Astronomy Textbook",
      "relevance": 0.98,
      "url": "https://example.com/astronomy",
      "publication_date": "2023-01-15",
      "nli_label": "entailment",
      "nli_confidence": 0.96
    }
  ],
  "verified_at": "2025-11-06T10:30:00Z",
  "processing_time_ms": 1250,
  "corpus_ids_searched": ["wikipedia", "scientific_papers"],
  "validation_warnings": null
}
```

### Verdict Values

- **SUPPORTED**: Claim is supported by evidence (high entailment scores)
- **REFUTED**: Claim is contradicted by evidence (high contradiction scores)
- **NOT_ENOUGH_INFO**: Insufficient evidence or confidence to make a determination

### Python Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional
from datetime import datetime

class VerificationResult(BaseModel):
    claim_id: str
    claim_text: str
    verdict: Literal["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO"]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    reasoning: Optional[str] = None
    evidence: list[EvidenceItem]
    verified_at: datetime
    processing_time_ms: Annotated[int, Field(ge=0)]
    corpus_ids_searched: Optional[list[str]] = None
    validation_warnings: Optional[list[str]] = None
```

---

## TaskStatus

Status tracking for asynchronous verification tasks.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique task identifier |
| `status` | string | Task status: pending, processing, completed, failed |
| `created_at` | datetime | Task creation timestamp |
| `completed_at` | datetime | Completion timestamp (if done) |
| `result` | [VerificationResult](#verificationresult) | Verification result (if completed) |
| `error` | string | Error message (if failed) |
| `progress_percentage` | integer | Progress indicator (0-100) |

### Status Values

- **pending**: Task queued but not yet started
- **processing**: Task currently being executed
- **completed**: Task finished successfully (result available)
- **failed**: Task failed with error

### Example (Pending)

```json
{
  "task_id": "task_xyz789",
  "status": "pending",
  "created_at": "2025-11-06T10:29:00Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 0
}
```

### Example (Processing)

```json
{
  "task_id": "task_xyz789",
  "status": "processing",
  "created_at": "2025-11-06T10:29:00Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "progress_percentage": 45
}
```

### Example (Completed)

```json
{
  "task_id": "task_xyz789",
  "status": "completed",
  "created_at": "2025-11-06T10:29:00Z",
  "completed_at": "2025-11-06T10:30:30Z",
  "result": {
    "claim_id": "claim_123",
    "claim_text": "The Earth orbits around the Sun",
    "verdict": "SUPPORTED",
    "confidence": 0.95,
    "reasoning": "Multiple sources confirm this astronomical fact.",
    "evidence": [],
    "verified_at": "2025-11-06T10:30:30Z",
    "processing_time_ms": 1500
  },
  "error": null,
  "progress_percentage": 100
}
```

### Example (Failed)

```json
{
  "task_id": "task_xyz789",
  "status": "failed",
  "created_at": "2025-11-06T10:29:00Z",
  "completed_at": "2025-11-06T10:29:15Z",
  "result": null,
  "error": "Failed to retrieve evidence: Database connection timeout",
  "progress_percentage": null
}
```

### Validation Rules

- **result**: Can only be present when status is "completed"
- **error**: Can only be present when status is "failed"
- **completed_at**: Can only be present when status is "completed" or "failed"

### Python Model

```python
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal, Optional
from datetime import datetime

class TaskStatus(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[VerificationResult] = None
    error: Optional[str] = None
    progress_percentage: Optional[Annotated[int, Field(ge=0, le=100)]] = None

    @field_validator("result")
    @classmethod
    def validate_result(cls, v, info):
        if v is not None and info.data.get("status") != "completed":
            raise ValueError("Result only allowed when status is 'completed'")
        return v
```

---

## EvidenceItem

Individual evidence item from the knowledge base.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique evidence identifier |
| `text` | string | Evidence text content |
| `source` | string | Evidence source name |
| `relevance` | float | Semantic relevance to claim (0.0-1.0) |
| `url` | string | Source URL (optional) |
| `publication_date` | string | Publication date (optional) |
| `nli_label` | string | NLI relationship: entailment, contradiction, neutral |
| `nli_confidence` | float | NLI confidence score (0.0-1.0) |

### Example

```json
{
  "id": "evidence_abc123",
  "text": "The Earth orbits the Sun once every 365.25 days in an elliptical path.",
  "source": "Astronomy Textbook 2023",
  "relevance": 0.98,
  "url": "https://example.com/astronomy/earth-orbit",
  "publication_date": "2023-01-15",
  "nli_label": "entailment",
  "nli_confidence": 0.96
}
```

### NLI Label Values

- **entailment**: Evidence supports/proves the claim
- **contradiction**: Evidence contradicts/disproves the claim
- **neutral**: No clear logical relationship

### Python Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional

class EvidenceItem(BaseModel):
    id: str
    text: str
    source: str
    relevance: Annotated[float, Field(ge=0.0, le=1.0)]
    url: Optional[str] = None
    publication_date: Optional[str] = None
    nli_label: Literal["entailment", "contradiction", "neutral"]
    nli_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
```

---

## Request/Response Examples

### Simple Verification Request

```json
{
  "claim": "Water freezes at 0 degrees Celsius",
  "max_evidence": 5,
  "confidence_threshold": 0.7
}
```

### Async Verification Request

```json
{
  "claim_id": "claim_water_freeze",
  "claim_text": "Water freezes at 0 degrees Celsius",
  "corpus_ids": ["physics", "chemistry"],
  "options": {
    "max_evidence_items": 5,
    "confidence_threshold": 0.7,
    "return_reasoning": true,
    "search_mode": "hybrid"
  }
}
```

### Verification Response

```json
{
  "claim_id": "claim_water_freeze",
  "claim_text": "Water freezes at 0 degrees Celsius",
  "verdict": "SUPPORTED",
  "confidence": 0.94,
  "reasoning": "Strong scientific consensus confirms water freezes at 0°C under standard atmospheric pressure.",
  "evidence": [
    {
      "id": "evidence_123",
      "text": "Water freezes at 0 degrees Celsius (32 degrees Fahrenheit) at standard atmospheric pressure.",
      "source": "Physics Handbook",
      "relevance": 0.99,
      "url": "https://example.com/physics/phase-changes",
      "nli_label": "entailment",
      "nli_confidence": 0.97
    }
  ],
  "verified_at": "2025-11-07T10:30:00Z",
  "processing_time_ms": 850,
  "corpus_ids_searched": ["physics", "chemistry"]
}
```

---

## TypeScript Types

For TypeScript/JavaScript clients:

```typescript
interface VerifyClaimRequest {
  claim_id: string;
  claim_text: string;
  corpus_ids?: string[] | null;
  options?: VerificationOptions | null;
}

interface VerificationOptions {
  max_evidence_items?: number;
  confidence_threshold?: number;
  return_reasoning?: boolean;
  search_mode?: 'hybrid' | 'vector' | 'keyword';
}

interface VerificationResult {
  claim_id: string;
  claim_text: string;
  verdict: 'SUPPORTED' | 'REFUTED' | 'NOT_ENOUGH_INFO';
  confidence: number;
  reasoning?: string | null;
  evidence: EvidenceItem[];
  verified_at: string;  // ISO 8601 datetime
  processing_time_ms: number;
  corpus_ids_searched?: string[] | null;
  validation_warnings?: string[] | null;
}

interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;  // ISO 8601 datetime
  completed_at?: string | null;
  result?: VerificationResult | null;
  error?: string | null;
  progress_percentage?: number | null;
}

interface EvidenceItem {
  id: string;
  text: string;
  source: string;
  relevance: number;
  url?: string | null;
  publication_date?: string | null;
  nli_label: 'entailment' | 'contradiction' | 'neutral';
  nli_confidence: number;
}
```

---

## OpenAPI Schema

Full OpenAPI 3.1 schema available at:
- **Endpoint**: `/openapi.json`
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)

Example usage:
```bash
curl http://localhost:8000/openapi.json > openapi.json
```

---

## Validation Examples

### Valid Request

```python
request = VerifyClaimRequest(
    claim_id="claim_123",
    claim_text="The Earth orbits the Sun",
    options=VerificationOptions(
        max_evidence_items=5,
        confidence_threshold=0.7
    )
)
# ✓ Valid
```

### Invalid Request - Empty Claim

```python
request = VerifyClaimRequest(
    claim_id="claim_123",
    claim_text="   ",  # Empty after strip
)
# ✗ ValidationError: Claim text cannot be empty
```

### Invalid Request - Exceeds Max Evidence

```python
request = VerifyClaimRequest(
    claim_id="claim_123",
    claim_text="Valid claim",
    options=VerificationOptions(
        max_evidence_items=100  # Exceeds limit
    )
)
# ✗ ValidationError: ensure this value is less than or equal to 50
```

### Invalid Request - Empty Corpus IDs

```python
request = VerifyClaimRequest(
    claim_id="claim_123",
    claim_text="Valid claim",
    corpus_ids=[]  # Empty list not allowed
)
# ✗ ValidationError: corpus_ids cannot be empty list (use None instead)
```

---

## See Also

- [Verification Endpoints](../endpoints/verification.md)
- [ML Services Schemas](ml_services.md)
- [Error Codes](../errors/error_codes.md)
- [API Overview](../README.md)
