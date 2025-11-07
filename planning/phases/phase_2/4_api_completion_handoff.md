# API Completion Handoff

**Features**: 4.1-4.6
**Agent**: fastapi-pro, python-pro (4.6)
**Total Effort**: 58 hours
**Status**: Planned (can start in parallel with validation)
**Priority**: High (required for Phase 2 completion)

---

## Quick Navigation

**Master Index**: [v0_phase2_completion_handoff_MASTER.md](./v0_phase2_completion_handoff_MASTER.md)
**Quick Start**: [v0_phase2_quick_start.md](./v0_phase2_quick_start.md)
**Dependencies**: [dependencies_and_timeline.md](./dependencies_and_timeline.md)

**Related Handoffs**:
- [3_validation_framework_handoff.md](./3_validation_framework_handoff.md) (accuracy metrics)
- [5_documentation_handoff.md](./5_documentation_handoff.md) (API docs)

---

## Category Overview

API completion implements the HTTP endpoints for the verification pipeline. Features 4.1-4.5 focus on API implementation, while Feature 4.6 adds comprehensive input validation.

### Execution Order

**Recommended Approach**:

**Phase 1 (Day 1-2)**:
- Feature 4.2: Request/Response Models (6h) - Foundation
- Feature 4.6: Input Validation Layer (14h) - Can start immediately, complements 4.2
- Feature 4.1: Verification Endpoints (10h) - Uses models from 4.2, validation from 4.6
- Feature 4.5: Rate Limiting (8h) - Can run in parallel

**Phase 2 (Day 3-4)**:
- Feature 4.3: Async Background Processing (12h)
- Feature 4.4: API Documentation (8h) - Documents complete API

### Dependencies

All features depend on:
- Verification pipeline service (core implementation complete)
- Database schema for verdicts

No inter-feature dependencies, all can be parallelized.

---

## Feature 4.1: Verification Endpoints Implementation

**Status**: 📋 Planned
**Assigned To**: fastapi-pro
**Estimated Effort**: 10 hours
**Complexity**: Medium
**Blocker Status**: No blockers

### Description

Implement API endpoints for claim verification workflow.

### Requirements

- `POST /api/v1/claims/{id}/verify` - Trigger verification
- `GET /api/v1/verdicts/{claim_id}` - Get verdict
- Request/response model validation
- Error handling and status codes
- Async background processing
- Queue integration

### Architecture

```text
truthgraph/api/
├── routes.py                # Updated with verification routes
├── models.py                # Request/response models
└── verification_handlers.py # Business logic

truthgraph/workers/
├── verification_worker.py   # Background task handler
└── task_queue.py           # Queue management
```

### Endpoint Specifications

**Endpoint 1: POST /api/v1/claims/{id}/verify**

Request:
```json
{
  "claim_id": "claim_12345",
  "claim_text": "The Earth is round",
  "corpus_ids": ["corpus_1", "corpus_2"],  // Optional, uses default if omitted
  "options": {
    "max_evidence_items": 10,
    "confidence_threshold": 0.5,
    "return_reasoning": true
  }
}
```

Response:
```json
{
  "task_id": "task_abc123",
  "status": "processing",
  "created_at": "2025-10-31T10:00:00Z",
  "claim_id": "claim_12345"
}
```

**Endpoint 2: GET /api/v1/verdicts/{claim_id}**

Response (if complete):
```json
{
  "claim_id": "claim_12345",
  "claim_text": "The Earth is round",
  "verdict": "SUPPORTED",
  "confidence": 0.92,
  "reasoning": "Multiple sources confirm Earth is spherical",
  "evidence": [
    {
      "id": "evidence_1",
      "text": "Earth is an oblate spheroid",
      "source": "NASA",
      "relevance": 0.95
    }
  ],
  "verified_at": "2025-10-31T10:00:15Z"
}
```

### Implementation Steps

1. Create Pydantic request/response models (Feature 4.2)
2. Implement POST `/api/v1/claims/{id}/verify` endpoint
3. Implement GET `/api/v1/verdicts/{claim_id}` endpoint
4. Add error handling (claim not found, already verified, etc.)
5. Implement async background processing
6. Add queue integration
7. Implement status tracking
8. Add API documentation
9. Create endpoint tests
10. Validate with integration tests

### Error Handling

```python
@router.post("/api/v1/claims/{claim_id}/verify")
async def verify_claim(claim_id: str, request: VerifyClaimRequest):
    try:
        # Verify claim exists
        claim = await get_claim(claim_id)
        if not claim:
            raise HTTPException(
                status_code=404,
                detail=f"Claim '{claim_id}' not found"
            )

        # Check if already verified
        existing_verdict = await get_verdict(claim_id)
        if existing_verdict:
            return {
                "status": "already_verified",
                "verdict": existing_verdict
            }

        # Queue verification task
        task_id = await queue_verification_task(claim, request.options)
        return {"task_id": task_id, "status": "queued"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Verification failed")
```

### Status Codes

| Code | Scenario |
|------|----------|
| 200 | Verdict retrieved successfully |
| 202 | Verification task accepted (async) |
| 400 | Invalid request (bad format, missing fields) |
| 404 | Claim or verdict not found |
| 409 | Conflict (already being verified) |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Success Criteria

- Both endpoints working
- Request validation working
- Error handling complete
- Async processing functional
- Tests passing
- Documentation complete

### Test Template

```python
@pytest.mark.asyncio
async def test_verify_endpoint_accepted():
    """Test verification endpoint accepts requests."""
    client = AsyncClient(app=app, base_url="http://test")
    request = VerifyClaimRequest(
        claim_id="test_claim",
        claim_text="Test claim",
        options={}
    )

    response = await client.post(
        "/api/v1/claims/test_claim/verify",
        json=request.dict()
    )

    assert response.status_code == 202
    assert "task_id" in response.json()

@pytest.mark.asyncio
async def test_verdict_endpoint_returns_result():
    """Test verdict endpoint returns verification result."""
    # Create and verify claim first
    claim_id = "test_claim"
    await verify_claim_and_wait(claim_id)

    client = AsyncClient(app=app, base_url="http://test")
    response = await client.get(f"/api/v1/verdicts/{claim_id}")

    assert response.status_code == 200
    result = response.json()
    assert result["claim_id"] == claim_id
    assert "verdict" in result
    assert "confidence" in result
```

---

## Feature 4.2: Request/Response Model Definition

**Status**: 📋 Planned
**Assigned To**: fastapi-pro
**Estimated Effort**: 6 hours
**Complexity**: Small
**Blocker Status**: No blockers (but 4.1 depends on this)

### Description

Define comprehensive Pydantic models for verification requests and responses.

### Requirements

- VerifyClaimRequest model
- VerificationResult model
- VerdictResponse model
- Evidence references
- Confidence scores
- Explanation/reasoning text
- Validation rules

### Architecture

```text
truthgraph/api/
├── models.py                # Updated models
└── schemas/
    ├── verification.py     # Verification schemas
    └── evidence.py         # Evidence schemas
```

### Model Definitions

**Request Models**

```python
from pydantic import BaseModel, Field

class VerificationOptions(BaseModel):
    max_evidence_items: int = Field(default=10, ge=1, le=50)
    confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    return_reasoning: bool = True

class VerifyClaimRequest(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier")
    claim_text: str = Field(..., description="Claim text to verify")
    corpus_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific corpus IDs to search"
    )
    options: Optional[VerificationOptions] = Field(default_factory=VerificationOptions)

    class Config:
        schema_extra = {
            "example": {
                "claim_id": "claim_123",
                "claim_text": "The Earth is round",
                "corpus_ids": ["wikipedia", "scientific_papers"],
                "options": {
                    "max_evidence_items": 5,
                    "confidence_threshold": 0.7,
                    "return_reasoning": True
                }
            }
        }
```

**Response Models**

```python
class EvidenceItem(BaseModel):
    id: str
    text: str
    source: str
    relevance: float = Field(ge=0, le=1)
    url: Optional[str] = None
    publication_date: Optional[str] = None

class VerificationResult(BaseModel):
    claim_id: str
    claim_text: str
    verdict: str = Field(..., description="SUPPORTED, REFUTED, NOT_ENOUGH_INFO")
    confidence: float = Field(ge=0, le=1)
    reasoning: Optional[str] = None
    evidence: List[EvidenceItem]
    verified_at: datetime
    processing_time_ms: int

class TaskStatus(BaseModel):
    task_id: str
    status: str = Field(..., description="pending, processing, completed, failed")
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[VerificationResult] = None
    error: Optional[str] = None
```

### Validation Rules

```python
class VerifyClaimRequest(BaseModel):
    claim_text: str

    @validator('claim_text')
    def claim_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Claim text cannot be empty')
        if len(v) > 5000:
            raise ValueError('Claim text exceeds 5000 characters')
        return v.strip()
```

### Success Criteria

- All models defined
- Validation rules working
- JSON schema valid
- Examples provided
- Tests passing
- Documentation complete

### Test Template

```python
def test_verify_claim_request_validation():
    """Test request validation."""
    # Valid request
    request = VerifyClaimRequest(
        claim_id="test",
        claim_text="The Earth is round"
    )
    assert request.claim_id == "test"

    # Invalid - empty claim
    with pytest.raises(ValidationError):
        VerifyClaimRequest(
            claim_id="test",
            claim_text=""
        )

    # Invalid - too long
    with pytest.raises(ValidationError):
        VerifyClaimRequest(
            claim_id="test",
            claim_text="x" * 6000
        )
```

---

## Feature 4.3: Async Background Processing

**Status**: 📋 Planned
**Assigned To**: fastapi-pro
**Estimated Effort**: 12 hours
**Complexity**: Large
**Blocker Status**: Depends on Feature 4.1

### Description

Implement asynchronous background job processing for long-running verifications.

### Requirements

- Task queue implementation (Celery/RQ/native asyncio)
- Job status tracking
- Result storage
- Error handling and retries
- Progress updates
- Webhook notifications (optional)

### Architecture

```text
truthgraph/workers/
├── task_queue.py            # Queue management
├── verification_worker.py   # Worker implementation
├── task_status.py          # Status tracking
└── task_storage.py         # Result persistence

truthgraph/api/
├── task_routes.py          # Task status endpoints
└── websocket_handler.py    # Real-time updates

config/
└── celery_config.py        # Queue configuration
```

### Implementation Approach

**Option 1: Celery (Recommended for scale)**

```python
from celery import Celery
from config.celery_config import app as celery_app

@celery_app.task(bind=True, max_retries=3)
def verify_claim_task(self, claim_id: str, claim_text: str, options: dict):
    """Background task for claim verification."""
    try:
        result = verify_claim(claim_text, options)
        store_result(claim_id, result)
        return result
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

**Option 2: Native asyncio (Simpler)**

```python
class TaskQueue:
    def __init__(self):
        self.tasks = {}
        self.results = {}

    async def queue_task(self, task_id: str, task_func, *args):
        """Queue an async task."""
        self.tasks[task_id] = asyncio.create_task(task_func(*args))

    async def get_status(self, task_id: str):
        """Get task status."""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        if task.done():
            return {
                "status": "completed",
                "result": task.result()
            }
        else:
            return {"status": "processing"}
```

### Status Tracking

```python
@router.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of background task."""
    status = task_queue.get_status(task_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": status.get("status"),
        "result": status.get("result"),
        "error": status.get("error")
    }
```

### Error Handling & Retries

```python
async def verify_with_retries(claim_id: str, max_retries: int = 3):
    """Verify with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return await verify_claim(claim_id)
        except TemporaryError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
        except PermanentError:
            raise
```

### WebSocket Updates (Optional)

```python
@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """Real-time task progress updates via WebSocket."""
    await websocket.accept()

    while True:
        status = task_queue.get_status(task_id)
        await websocket.send_json(status)

        if status.get("status") in ["completed", "failed"]:
            break

        await asyncio.sleep(1)

    await websocket.close()
```

### Success Criteria

- Task queue functional
- Status tracking working
- Results persisted
- Error recovery working
- Tests passing
- Documentation complete
- Scalable for 100+ concurrent tasks

### Test Template

```python
@pytest.mark.asyncio
async def test_task_queuing():
    """Test task queueing and status tracking."""
    queue = TaskQueue()

    # Queue task
    task_id = "test_task_1"
    await queue.queue_task(task_id, verify_claim, "claim_text", {})

    # Check status
    status = await queue.get_status(task_id)
    assert status["status"] in ["processing", "completed"]

    # Wait for completion
    await asyncio.sleep(2)
    status = await queue.get_status(task_id)
    assert status["status"] == "completed"

@pytest.mark.asyncio
async def test_task_error_handling():
    """Test error handling in task processing."""
    queue = TaskQueue()

    # Queue task that will fail
    task_id = "test_task_fail"
    await queue.queue_task(task_id, failing_task)

    # Wait and check error
    await asyncio.sleep(1)
    status = await queue.get_status(task_id)
    assert status["status"] == "failed"
    assert "error" in status
```

---

## Feature 4.4: API Documentation & Examples

**Status**: 📋 Planned
**Assigned To**: fastapi-pro
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: Depends on Features 4.1, 4.2

### Description

Create comprehensive API documentation with examples and usage patterns.

### Requirements

- OpenAPI/Swagger documentation
- Usage examples (curl, Python, JavaScript)
- Authentication documentation
- Rate limiting documentation
- Error code reference
- Integration examples
- Troubleshooting guide

### Architecture

```text
docs/api/
├── endpoints/
│   ├── verification.md     # Verification API docs
│   └── verdicts.md        # Verdicts API docs
├── examples/
│   ├── verify_claim.py    # Python example
│   ├── verify_claim.js    # JavaScript example
│   ├── verify_claim.sh    # cURL example
│   └── verify_claim.md    # Markdown walkthrough
├── schemas/
│   └── verification.md    # Schema documentation
├── errors/
│   └── error_codes.md     # Error documentation
└── README.md              # API overview
```

### Documentation Generation

FastAPI auto-generates OpenAPI/Swagger docs at `/docs` and `/redoc`, but we'll enhance with:

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """Custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="TruthGraph Verification API",
        version="1.0.0",
        description="Real-time claim verification using ML-powered evidence retrieval",
        routes=app.routes,
    )

    # Custom security scheme
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Example Documentation

**curl Example**
```bash
# Trigger verification
curl -X POST "http://localhost:8000/api/v1/claims/claim_123/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_text": "The Earth is round",
    "options": {
      "max_evidence_items": 5,
      "confidence_threshold": 0.7
    }
  }'

# Check verdict
curl -X GET "http://localhost:8000/api/v1/verdicts/claim_123"
```

**Python Example**
```python
import httpx
import asyncio

async def verify_claim():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/claims/claim_123/verify",
            json={
                "claim_text": "The Earth is round",
                "options": {"max_evidence_items": 5}
            }
        )
        task_id = response.json()["task_id"]

        # Poll for result
        while True:
            result = await client.get(
                f"http://localhost:8000/api/v1/verdicts/claim_123"
            )
            if result.json().get("verdict"):
                return result.json()
            await asyncio.sleep(1)
```

### Success Criteria

- OpenAPI docs generated
- Usage examples complete
- All endpoints documented
- Error codes documented
- Examples tested
- Documentation clear

---

## Feature 4.5: Rate Limiting & Throttling

**Status**: 📋 Planned
**Assigned To**: fastapi-pro
**Estimated Effort**: 8 hours
**Complexity**: Medium
**Blocker Status**: Depends on Feature 4.1

### Description

Implement rate limiting to protect API from abuse and ensure fair resource allocation.

### Requirements

- Per-user rate limiting
- Per-IP rate limiting
- Different limits for different endpoints
- Clear rate limit headers
- Graceful degradation
- Monitoring and alerting
- Configuration system

### Architecture

```text
truthgraph/api/
├── middleware.py            # Rate limiting middleware
├── rate_limit.py           # Rate limit logic
├── config.py               # Configuration
└── monitoring.py           # Monitoring

tests/
└── test_rate_limiting.py   # Tests
```

### Implementation

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/claims/{claim_id}/verify")
@limiter.limit("10/minute")
async def verify_claim(request: Request, claim_id: str):
    """Verify claim with rate limiting."""
    # Implementation

# Custom rate limit per endpoint
@app.get("/api/v1/health")
@limiter.limit("100/minute")
async def health_check():
    return {"status": "ok"}
```

### Rate Limit Headers

```text
RateLimit-Limit: 10
RateLimit-Remaining: 8
RateLimit-Reset: 1635695400
Retry-After: 12
```

### Configuration

```yaml
rate_limits:
  default: "10/minute"
  endpoints:
    /api/v1/claims/{id}/verify: "5/minute"
    /api/v1/verdicts/{id}: "20/minute"
    /api/v1/health: "100/minute"
  burst: "15"  # Allow burst to 15
```

### Success Criteria

- Rate limiting working
- Headers correct
- Monitoring operational
- Configuration flexible
- Tests passing
- Documentation complete

---

## Feature 4.6: Input Validation Layer

**Status**: 📋 Planned
**Assigned To**: python-pro
**Estimated Effort**: 14 hours
**Complexity**: Medium
**Blocker Status**: No blockers (can start immediately, complements Feature 4.2)
**Priority**: High (foundational for edge case handling)

### Description

Implement a comprehensive input validation layer that provides encoding validation, length constraints, Unicode normalization, and special character handling before claims enter the verification pipeline. This layer complements the basic Pydantic API validation (Feature 4.2) by adding deep input sanitization and edge case detection at the application layer.

**Key Distinction from Feature 4.2:**
- Feature 4.2: API-level schema validation (required fields, basic types, length limits)
- Feature 4.6: Application-level input validation (encoding, Unicode, special characters, pipeline safety)

### Requirements

**Functional Requirements**:
1. **Encoding Validation**: UTF-8 validation, invalid Unicode detection, encoding error recovery
2. **Length Validation**: Word count (min 2, max 500), token estimation (512 token limit), truncation warnings
3. **Unicode Normalization**: NFC normalization, combining characters, emoji preservation, math notation
4. **Special Character Validation**: Non-ASCII ratio detection, RTL text support, Greek/mathematical symbols
5. **Structure Validation**: Non-empty verification, alphanumeric presence, whitespace-only rejection
6. **Error Recovery**: Structured validation results (VALID, WARNING, INVALID), clear error messages, actionable suggestions

**Non-Functional Requirements**:
- Performance: <10ms validation overhead per claim
- Reliability: 100% Unicode-safe operation
- Compatibility: No breaking changes to existing API
- Testability: >90% test coverage
- Observability: Structured logging of validation events

### Architecture

```text
truthgraph/
├── validation/
│   ├── __init__.py
│   ├── claim_validator.py       # Main validator class
│   ├── validators.py            # Individual validator functions
│   ├── normalizers.py           # Text normalization utilities
│   ├── error_codes.py           # Validation error code definitions
│   └── models.py                # ValidationResult models
│
├── api/
│   └── ml_routes.py             # MODIFIED: Add validation integration
│
└── services/
    └── verification_pipeline_service.py  # MODIFIED: Add validation calls

tests/
├── unit/validation/
│   ├── test_claim_validator.py
│   ├── test_encoding_validation.py
│   ├── test_length_validation.py
│   ├── test_unicode_normalization.py
│   └── test_special_characters.py
└── integration/
    ├── test_validation_integration.py
    └── test_validation_edge_cases.py
```

### Implementation Steps

**Phase 1: Core Validation Infrastructure** (4 hours)
1. Create validation models and error codes (1h)
2. Implement error code definitions (0.5h)
3. Create individual validator functions (1.5h)
4. Implement Unicode normalizer (1h)

**Phase 2: Main Validator Class** (3 hours)
5. Implement ClaimValidator orchestrator (2h)
6. Create validation package initialization (0.5h)
7. Add validation configuration (0.5h)

**Phase 3: Integration** (3 hours)
8. Integrate with API layer (1.5h)
9. Integrate with verification pipeline (1h)
10. Add validation error responses to API models (0.5h)

**Phase 4: Testing** (4 hours)
11. Unit tests for validators (2h)
12. Integration tests (1.5h)
13. Edge case corpus integration tests (0.5h)

### Core Components

**ClaimValidator Class**:
```python
class ClaimValidator:
    """Orchestrates all claim validation checks."""

    def __init__(
        self,
        min_words: int = 2,
        max_words: int = 500,
        max_tokens_estimate: int = 450
    ):
        self.min_words = min_words
        self.max_words = max_words
        self.max_tokens_estimate = max_tokens_estimate

    def validate(self, claim_text: str) -> ValidationResult:
        """Run all validation checks on claim text.

        Validation order:
        1. Encoding validation (must pass)
        2. Structure validation (must pass)
        3. Length validation (may warn)
        4. Special character validation (may warn)
        5. Unicode normalization (always applied)
        """
        # Implementation steps...

    def validate_batch(self, claim_texts: List[str]) -> List[ValidationResult]:
        """Validate multiple claims in batch."""
```

**ValidationResult Model**:
```python
@dataclass
class ValidationResult:
    """Result of input validation."""
    status: ValidationStatus  # VALID, WARNING, INVALID
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Optional[dict] = None
    normalized_text: Optional[str] = None
```

### Validation Error Codes

| Code | Type | Description | Action |
|------|------|-------------|--------|
| `EMPTY_TEXT` | INVALID | Empty or whitespace-only | Reject |
| `SINGLE_WORD` | INVALID | Single word claim | Reject |
| `ENCODING_MISMATCH` | INVALID | UTF-8 encoding failure | Reject |
| `REPLACEMENT_CHAR` | INVALID | Invalid Unicode (U+FFFD) | Reject |
| `NO_ALPHANUMERIC` | INVALID | No meaningful content | Reject |
| `MINIMAL_CONTEXT` | WARNING | Very short (<3 words) | Warn + Process |
| `POTENTIAL_TRUNCATION` | WARNING | Very long (>450 tokens) | Warn + Process |
| `HIGH_NON_ASCII_RATIO` | WARNING | >50% non-ASCII characters | Warn + Process |

### Integration with Existing Features

**Feature 4.2 (Request/Response Models)**:
- Complementary validation layers
- Feature 4.2: Schema validation (Pydantic)
- Feature 4.6: Content validation (ClaimValidator)
- Sequential: Request → Pydantic (4.2) → ClaimValidator (4.6) → Pipeline

**Feature 4.1 (Verification Endpoints)**:
```python
@router.post("/api/v1/claims/verify")
async def verify_claim(request: VerifyRequest):
    # Pydantic validates (4.2)
    validation_result = claim_validator.validate(request.claim_text)

    if validation_result.status == ValidationStatus.INVALID:
        raise HTTPException(400, detail=validation_result.message)

    # Use normalized text
    normalized = validation_result.normalized_text
    result = await verification_service.verify_claim(
        claim_text=normalized,
        validation_metadata=validation_result.metadata
    )
```

**Feature 3.3 (Edge Case Validation)**:
- ClaimValidator detects input-level edge cases
- EdgeCaseDetector handles pipeline-level cases
- Validation metadata flows from ClaimValidator → Pipeline → EdgeCaseDetector

### Success Criteria

**Functional**:
- ✅ All encoding errors detected and rejected with clear messages
- ✅ Length validation prevents single-word claims and warns on edge cases
- ✅ Unicode normalization applied to all claims (NFC form)
- ✅ Special characters (Greek, emoji, RTL) handled without errors
- ✅ Validation errors include error codes, messages, and suggestions
- ✅ ValidationResult includes normalized text for pipeline
- ✅ Integration with API endpoints complete (4.1)
- ✅ All 34 edge case corpus claims processed without crashes

**Non-Functional**:
- ✅ Validation overhead <10ms per claim (measured)
- ✅ Unit test coverage >90% for validation module
- ✅ No breaking changes to existing API
- ✅ Documentation complete and clear
- ✅ Monitoring dashboard operational

### Test Requirements

```python
def test_validator_rejects_empty():
    """Test validator rejects empty claims."""
    validator = ClaimValidator()
    result = validator.validate("")
    assert result.status == ValidationStatus.INVALID
    assert result.error_code == "EMPTY_TEXT"

def test_validator_handles_unicode():
    """Test validator handles multilingual Unicode."""
    validator = ClaimValidator()
    result = validator.validate("Η Γη είναι στρογγυλή")  # Greek
    assert result.status == ValidationStatus.VALID
    assert result.normalized_text is not None

def test_api_rejects_invalid_input(client):
    """Test API rejects invalid claims."""
    response = client.post("/api/v1/claims/verify", json={
        "claim_text": "",
        "options": {}
    })
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_TEXT"

def test_validation_edge_cases(edge_case_corpus):
    """Test validation handles all edge case categories."""
    validator = ClaimValidator()
    for category, data in edge_case_corpus.items():
        for claim in data["claims"]:
            result = validator.validate(claim["text"])
            assert result is not None  # Should not crash
```

### Documentation

**Full implementation guide**: [planning/features/feature_4_6_input_validation_layer.md](../features/feature_4_6_input_validation_layer.md)

The complete 3,000-line implementation guide includes:
- Detailed module specifications
- Complete code examples (7 examples)
- Validation rules reference (30+ error codes)
- Testing strategy with 50+ test cases
- Performance optimization guidance
- Configuration management
- Migration path (4-phase rollout)
- Monitoring and metrics
- 40+ task implementation checklist

### Performance Targets

| Operation | Target | Measured |
|-----------|--------|----------|
| Encoding validation | <2ms | TBD |
| Length validation | <1ms | TBD |
| Unicode normalization | <5ms | TBD |
| Structure validation | <1ms | TBD |
| **Total validation** | **<10ms** | **TBD** |

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Validation too strict | Medium | High | Conservative thresholds, extensive testing |
| Unicode changes semantics | Low | Medium | Use NFC (canonical), test with multilingual corpus |
| Performance overhead >10ms | Low | Medium | Profile and optimize, cache validator instance |
| Breaking changes | Low | High | Additive changes only, feature flag for rollout |

### Dependencies

**Upstream Dependencies**: None (can start immediately)

**Downstream Dependencies**:
- Feature 4.1 (Verification Endpoints): Uses validation in request handling
- Feature 3.3 (Edge Case Validation): Receives validation metadata
- Feature 4.3 (Async Processing): Background jobs validate inputs
- Feature 4.4 (API Documentation): Documents validation error codes

**Parallel Dependencies**:
- Feature 4.2 (Request/Response Models): Different validation layers
- Feature 4.5 (Rate Limiting): Independent concerns

---

## Timeline & Dependencies

### Week 1-2 (Days 1-4)

**Day 1-2**:
- Feature 4.2: Models (6h)
- Feature 4.6: Input Validation Layer (14h) - Can start immediately
- Feature 4.1: Endpoints (10h) - Uses models from 4.2, validation from 4.6
- Feature 4.5: Rate limiting (8h)

**Day 3-4**:
- Feature 4.3: Async processing (12h)
- Feature 4.4: Documentation (8h)

**Total**: 58 hours (vs. 44 hours original plan)

### Critical Path

1. Feature 4.2 (Models) must be complete before Feature 4.1 (Endpoints)
2. Feature 4.6 (Validation) should be complete before Feature 4.1 (Endpoints) for full integration
3. Feature 4.1 (Endpoints) must be complete before Feature 4.3 (Async processing)
4. Feature 4.4 (Documentation) can happen in parallel
5. Feature 4.5 (Rate limiting) can happen in parallel

### Feature Integration Points

- **Feature 4.6 (Validation)** → Feature 4.1 (Endpoints): Endpoints call validation
- **Feature 4.6 (Validation)** → Feature 3.3 (Edge Case): Validation metadata flows to edge case detection
- **Feature 4.1 (Endpoints)** → Feature 4.3 (Async): Background tasks use endpoints
- **All Features** → Feature 4.4 (Documentation): API docs cover all features
- **Works with**: Verification pipeline (core service), validation tests (Feature 3.x)
- **Documentation used by**: DX (Feature 5.4)

---

## Progress Tracking

### Completion Checklist

- [X] Feature 4.2 complete (Request/Response Models)
- [X] Feature 4.6 complete (Input Validation Layer)
- [X] Feature 4.1 complete (Verification Endpoints)
- [ ] Feature 4.5 complete (Rate Limiting)
- [X] Feature 4.3 complete (Async Background Processing)
- [ ] Feature 4.4 complete (API Documentation)
- [ ] All endpoints tested
- [ ] Input validation tested with edge cases
- [ ] Rate limiting verified
- [ ] Async processing validated
- [ ] Documentation complete
- [ ] All unit tests passing (>90% coverage for validation)
- [ ] Integration tests passing

---

## Related Files

**For Background Context**:
- [dependencies_and_timeline.md](./dependencies_and_timeline.md) - Full dependency graph
- [agent_assignments.md](./agent_assignments.md) - Deliverables
- [success_criteria_and_risks.md](./success_criteria_and_risks.md) - Success targets

**For Next Steps**:
- [5_documentation_handoff.md](./5_documentation_handoff.md) - Documentation features

---

**Navigation**: [Master Index](./v0_phase2_completion_handoff_MASTER.md) | [Quick Start](./v0_phase2_quick_start.md) | [Dependencies](./dependencies_and_timeline.md) | [Previous: Validation](./3_validation_framework_handoff.md) | [Next: Documentation](./5_documentation_handoff.md)
