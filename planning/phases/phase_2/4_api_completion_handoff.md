# API Completion Handoff

**Features**: 4.1-4.5
**Agent**: fastapi-pro
**Total Effort**: 44 hours
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

API completion implements the HTTP endpoints for the verification pipeline. All 5 features can run in parallel with no cross-dependencies (only depend on verification pipeline service being complete).

### Execution Order

**Recommended Approach**:

**Phase 1 (Day 1-2)**:
- Feature 4.2: Request/Response Models (6h) - Foundation
- Feature 4.1: Verification Endpoints (10h) - Uses models from 4.2
- Feature 4.5: Rate Limiting (8h) - Can run in parallel

**Phase 2 (Day 3)**:
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

```
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

## Timeline & Dependencies

### Week 1 (Days 1-3)

**Day 1-2**:
- Feature 4.2: Models (6h)
- Feature 4.1: Endpoints (10h)
- Feature 4.5: Rate limiting (8h)

**Day 3**:
- Feature 4.3: Async processing (12h)
- Feature 4.4: Documentation (8h)

### Critical Path

1. Models must be complete before endpoints
2. Endpoints must be complete before async processing
3. Documentation can happen in parallel

### Integration Points

- Works with verification pipeline (core service)
- Works with validation tests (Feature 3.x)
- Documentation used by DX (Feature 5.4)

---

## Progress Tracking

### Completion Checklist

- [ ] Feature 4.2 complete
- [ ] Feature 4.1 complete
- [ ] Feature 4.5 complete
- [ ] Feature 4.3 complete
- [ ] Feature 4.4 complete
- [ ] All endpoints tested
- [ ] Rate limiting verified
- [ ] Async processing validated
- [ ] Documentation complete
- [ ] All tests passing
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
