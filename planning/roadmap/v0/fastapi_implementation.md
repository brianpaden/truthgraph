# FastAPI Implementation Guide - TruthGraph v0

## Executive Summary

This document provides comprehensive guidance for implementing TruthGraph v0 as a **modular monolith** using FastAPI. Unlike v1's microservices architecture, v0 uses a single FastAPI application with clear module boundaries, synchronous operations, and straightforward deployment patterns.

**Key Architectural Principles**:
- **Single FastAPI instance** with organized modules (not separate services)
- **Synchronous by default** (acceptable latency for MVP, simpler to reason about)
- **Application factory pattern** for testability and configuration
- **Dependency injection** for clean architecture
- **Type-safe** with Pydantic V2 models
- **Clear evolution path** to v1 microservices

**Target Performance**:
- Claim submission: < 200ms
- Verification (with ML): < 60s
- Claim retrieval: < 100ms
- System memory: < 2GB

---

## Table of Contents

1. [Application Structure](#1-application-structure)
2. [API Routes Organization](#2-api-routes-organization)
3. [Request/Response Models](#3-requestresponse-models)
4. [Dependency Injection](#4-dependency-injection)
5. [Error Handling](#5-error-handling)
6. [Synchronous Endpoints](#6-synchronous-endpoints)
7. [Testing Strategy](#7-testing-strategy)
8. [Code Examples](#8-code-examples)
9. [Performance Considerations](#9-performance-considerations)
10. [Evolution to v1](#10-evolution-to-v1)

---

## 1. Application Structure

### 1.1 Directory Layout

```text
truthgraph/
├── __init__.py
├── main.py                    # Application entry point
├── app.py                     # Application factory
├── config.py                  # Configuration management
├── exceptions.py              # Custom exceptions
├── api/
│   ├── __init__.py
│   ├── dependencies.py        # Dependency injection
│   ├── models.py              # Request/response Pydantic models
│   └── routes/
│       ├── __init__.py
│       ├── claims.py          # Claim endpoints
│       ├── verdicts.py        # Verdict endpoints
│       └── health.py          # Health/metrics endpoints
├── db/
│   ├── __init__.py
│   ├── session.py             # Database connection management
│   ├── base.py                # Base SQLAlchemy models
│   └── models.py              # SQLAlchemy ORM models
├── repositories/
│   ├── __init__.py
│   ├── base.py                # Base repository pattern
│   ├── claims.py              # Claim data access
│   ├── evidence.py            # Evidence data access
│   └── verdicts.py            # Verdict data access
├── services/
│   ├── __init__.py
│   ├── verification.py        # Verification business logic
│   ├── embeddings.py          # Embedding generation
│   └── retrieval.py           # Evidence retrieval logic
├── ml/
│   ├── __init__.py
│   ├── models.py              # ML model loading
│   ├── embedder.py            # Embedding model wrapper
│   └── nli.py                 # NLI model wrapper
└── utils/
    ├── __init__.py
    └── logging.py             # Logging configuration
```

### 1.2 Application Factory Pattern

The application factory pattern provides flexibility for testing, multiple environments, and future microservices extraction.

**Benefits**:
- Test with different configurations
- Lazy initialization of resources
- Clear startup/shutdown lifecycle
- Easy to extract into separate services later

**Pattern**:
```python
# truthgraph/app.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .config import get_settings
from .api.routes import claims, verdicts, health
from .db.session import init_db, close_db
from .ml.models import load_models, unload_models
from .utils.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application lifespan events"""
    settings = get_settings()

    # Startup
    setup_logging(settings.log_level)
    logger.info("Starting TruthGraph API", version=settings.version)

    # Initialize database
    init_db(settings.database_url)
    logger.info("Database initialized")

    # Load ML models (lazy load on first use in v0)
    # Models will be loaded when first verification is requested
    logger.info("ML models ready for lazy loading")

    yield

    # Shutdown
    logger.info("Shutting down TruthGraph API")
    unload_models()
    close_db()
    logger.info("Cleanup complete")

def create_app() -> FastAPI:
    """Application factory"""
    settings = get_settings()

    app = FastAPI(
        title="TruthGraph v0",
        description="Local-first fact-checking system",
        version=settings.version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )

    # Middleware
    setup_middleware(app, settings)

    # Routes
    app.include_router(health.router, tags=["health"])
    app.include_router(claims.router, prefix="/api/v1", tags=["claims"])
    app.include_router(verdicts.router, prefix="/api/v1", tags=["verdicts"])

    # Exception handlers
    setup_exception_handlers(app)

    return app
```

### 1.3 Lifespan Events

FastAPI's lifespan events (startup/shutdown) manage resources that need initialization or cleanup.

**What to initialize on startup**:
- Database connection pool
- Logging configuration
- Load configuration
- Prepare ML models (but don't load into memory yet)
- Health check state

**What to clean up on shutdown**:
- Close database connections
- Unload ML models from memory
- Flush logs
- Close any open file handles

**Implementation**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for startup/shutdown events.

    Startup order:
    1. Logging
    2. Configuration
    3. Database connection
    4. ML model preparation

    Shutdown order (reverse):
    1. ML model cleanup
    2. Database connection close
    3. Final log flush
    """
    settings = get_settings()
    logger = setup_logging(settings.log_level)

    try:
        # Startup
        logger.info("application_starting", version=settings.version)

        # Database
        init_db(settings.database_url)
        logger.info("database_initialized")

        # ML models (prepare paths, don't load yet)
        prepare_ml_models()
        logger.info("ml_models_prepared")

        yield  # Application runs here

    finally:
        # Shutdown
        logger.info("application_shutting_down")

        # Cleanup in reverse order
        unload_models()
        logger.info("ml_models_unloaded")

        close_db()
        logger.info("database_closed")

        logger.info("application_stopped")
```

### 1.4 Middleware Configuration

**CORS Middleware** (for React frontend):
```python
from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Configure application middleware"""

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # ["http://localhost:5173"]
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware (for tracing)
    app.add_middleware(RequestIDMiddleware)

    # Logging middleware (log all requests)
    app.add_middleware(LoggingMiddleware)

    # Timeout middleware (prevent hanging requests)
    app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout)
```

**Custom Middleware Examples**:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
import uuid

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request"""
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            request_id=getattr(request.state, "request_id", None)
        )

        return response

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Timeout requests that take too long"""
    def __init__(self, app, timeout: int = 60):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                "request_timeout",
                path=request.url.path,
                timeout=self.timeout
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": "request_timeout",
                    "message": f"Request exceeded {self.timeout}s timeout"
                }
            )
```

---

## 2. API Routes Organization

### 2.1 Route Structure

All routes are organized under `/api/v1` prefix for versioning. Health/metrics endpoints are at root level.

```text
/                          Root (redirect to docs)
/health                    Health check
/metrics                   Basic metrics
/api/v1/claims            Claim operations
  ├─ POST /                Create claim
  ├─ GET /                 List claims (paginated)
  └─ GET /{id}             Get claim detail
/api/v1/verdicts          Verdict operations
  └─ GET /{claim_id}       Get verdict for claim
```

### 2.2 Route Organization Strategy

**Why organize by resource (not by function)**:
- RESTful convention
- Clear ownership boundaries
- Easy to extract into separate services later
- Intuitive for API consumers

**File structure**:
```python
# api/routes/claims.py - All claim-related endpoints
# api/routes/verdicts.py - All verdict-related endpoints
# api/routes/health.py - Health and metrics
```

### 2.3 Route Definitions

#### Claims Routes

```python
# api/routes/claims.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from uuid import UUID

from ..dependencies import get_claim_repository
from ..models import ClaimCreate, ClaimResponse, ClaimListResponse
from ...repositories.claims import ClaimRepository

router = APIRouter()

@router.post(
    "/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new claim",
    description="Submit a claim for verification. Returns immediately with claim ID."
)
def create_claim(
    claim: ClaimCreate,
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimResponse:
    """
    Create a new claim for verification.

    - **text**: The claim text to verify (required)
    - **source_url**: Optional URL where claim was found
    """
    db_claim = repo.create(claim)
    logger.info("claim_created", claim_id=str(db_claim.id))
    return db_claim

@router.get(
    "/claims",
    response_model=ClaimListResponse,
    summary="List all claims",
    description="Get paginated list of all claims"
)
def list_claims(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimListResponse:
    """
    List claims with pagination.

    Returns claims in reverse chronological order (newest first).
    """
    total = repo.count()
    items = repo.list(skip=skip, limit=limit)

    logger.info("claims_listed", count=len(items), total=total)

    return ClaimListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get(
    "/claims/{claim_id}",
    response_model=ClaimResponse,
    summary="Get claim by ID",
    description="Retrieve a specific claim and its verdict (if available)"
)
def get_claim(
    claim_id: UUID,
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimResponse:
    """
    Get a specific claim by ID.

    Includes verdict information if verification has completed.
    """
    claim = repo.get(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found"
        )

    logger.info("claim_retrieved", claim_id=str(claim_id))
    return claim
```

#### Verdict Routes

```python
# api/routes/verdicts.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from ..dependencies import get_verdict_repository
from ..models import VerdictResponse
from ...repositories.verdicts import VerdictRepository

router = APIRouter()

@router.get(
    "/verdicts/{claim_id}",
    response_model=VerdictResponse,
    summary="Get verdict for claim",
    description="Retrieve verification verdict and supporting evidence"
)
def get_verdict(
    claim_id: UUID,
    repo: VerdictRepository = Depends(get_verdict_repository)
) -> VerdictResponse:
    """
    Get the verdict for a specific claim.

    Returns 404 if claim hasn't been verified yet.
    """
    verdict = repo.get_by_claim(claim_id)
    if not verdict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verdict found for claim {claim_id}"
        )

    logger.info("verdict_retrieved", claim_id=str(claim_id))
    return verdict
```

#### Health Routes

```python
# api/routes/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..dependencies import get_db

router = APIRouter()

@router.get(
    "/health",
    summary="Health check",
    description="Check if API and database are responsive"
)
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Health check endpoint.

    Returns 200 if healthy, 503 if any component is unhealthy.
    """
    health_status = {
        "status": "ok",
        "components": {}
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "ok"
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        health_status["status"] = "degraded"
        health_status["components"]["database"] = "error"

    # Check ML models (if loaded)
    try:
        from ...ml.models import check_models_loaded
        if check_models_loaded():
            health_status["components"]["ml_models"] = "loaded"
        else:
            health_status["components"]["ml_models"] = "not_loaded"
    except Exception as e:
        logger.error("ml_health_check_failed", error=str(e))
        health_status["components"]["ml_models"] = "error"

    return health_status

@router.get(
    "/metrics",
    summary="Basic metrics",
    description="Get basic application metrics"
)
def get_metrics(db: Session = Depends(get_db)) -> dict:
    """
    Basic application metrics.

    Returns counts of claims, evidence, and verdicts.
    """
    from ...db.models import Claim, Evidence, Verdict

    return {
        "claims": {
            "total": db.query(Claim).count(),
            "with_verdict": db.query(Claim).join(Verdict).count()
        },
        "evidence": {
            "total": db.query(Evidence).count()
        },
        "verdicts": {
            "total": db.query(Verdict).count(),
            "supported": db.query(Verdict).filter(Verdict.verdict == "SUPPORTED").count(),
            "refuted": db.query(Verdict).filter(Verdict.verdict == "REFUTED").count(),
            "insufficient": db.query(Verdict).filter(Verdict.verdict == "INSUFFICIENT").count()
        }
    }
```

---

## 3. Request/Response Models

### 3.1 Pydantic Models Overview

Pydantic V2 provides:
- Runtime type validation
- Automatic JSON serialization
- OpenAPI schema generation
- Clear API contracts

**Model organization**:
- Request models: Validate incoming data
- Response models: Define outgoing data structure
- Internal models: Domain objects (optional)

### 3.2 Claim Models

```python
# api/models.py
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class ClaimCreate(BaseModel):
    """Request model for creating a claim"""
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The claim text to verify",
        examples=["The Earth is round"]
    )
    source_url: Optional[HttpUrl] = Field(
        None,
        description="Optional URL where the claim was found",
        examples=["https://example.com/article"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "The Earth is approximately spherical",
                "source_url": "https://example.com/science-article"
            }
        }
    )

class ClaimResponse(BaseModel):
    """Response model for claim data"""
    id: UUID = Field(..., description="Unique claim identifier")
    text: str = Field(..., description="The claim text")
    source_url: Optional[HttpUrl] = Field(None, description="Source URL if provided")
    submitted_at: datetime = Field(..., description="When the claim was submitted")
    verdict: Optional["VerdictSummary"] = Field(
        None,
        description="Verdict summary if verification is complete"
    )

    model_config = ConfigDict(
        from_attributes=True,  # Pydantic V2: replaces orm_mode
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "text": "The Earth is approximately spherical",
                "source_url": "https://example.com/science-article",
                "submitted_at": "2025-01-15T10:30:00Z",
                "verdict": {
                    "verdict": "SUPPORTED",
                    "confidence": 0.95
                }
            }
        }
    )

class VerdictSummary(BaseModel):
    """Embedded verdict summary in claim response"""
    verdict: str = Field(..., description="SUPPORTED, REFUTED, or INSUFFICIENT")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

class ClaimListResponse(BaseModel):
    """Response model for paginated claim list"""
    items: list[ClaimResponse] = Field(..., description="List of claims")
    total: int = Field(..., ge=0, description="Total number of claims")
    skip: int = Field(..., ge=0, description="Number of claims skipped")
    limit: int = Field(..., ge=1, le=100, description="Number of claims returned")

    @property
    def has_more(self) -> bool:
        """Check if there are more results"""
        return self.skip + len(self.items) < self.total
```

### 3.3 Verdict Models

```python
class VerdictResponse(BaseModel):
    """Response model for verdict data"""
    id: UUID = Field(..., description="Unique verdict identifier")
    claim_id: UUID = Field(..., description="ID of the claim being verified")
    verdict: str = Field(
        ...,
        description="Verdict classification",
        pattern="^(SUPPORTED|REFUTED|INSUFFICIENT)$"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    reasoning: str = Field(..., description="Explanation of the verdict")
    evidence: list["EvidenceSummary"] = Field(
        default_factory=list,
        description="Supporting or refuting evidence"
    )
    created_at: datetime = Field(..., description="When verdict was created")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "claim_id": "550e8400-e29b-41d4-a716-446655440000",
                "verdict": "SUPPORTED",
                "confidence": 0.95,
                "reasoning": "Strong scientific consensus and empirical evidence",
                "evidence": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440002",
                        "content": "NASA confirms Earth is an oblate spheroid...",
                        "relationship": "supports",
                        "confidence": 0.98
                    }
                ],
                "created_at": "2025-01-15T10:30:15Z"
            }
        }
    )

class EvidenceSummary(BaseModel):
    """Embedded evidence summary in verdict response"""
    id: UUID = Field(..., description="Evidence identifier")
    content: str = Field(..., max_length=500, description="Evidence snippet")
    relationship: str = Field(
        ...,
        description="Relationship to claim",
        pattern="^(supports|refutes|neutral)$"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this evidence relationship"
    )
```

### 3.4 Error Models

```python
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error code (machine-readable)")
    message: str = Field(..., description="Error message (human-readable)")
    details: Optional[dict] = Field(None, description="Additional error context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "claim_not_found",
                "message": "Claim with ID 550e8400-e29b-41d4-a716-446655440000 not found",
                "details": {"claim_id": "550e8400-e29b-41d4-a716-446655440000"}
            }
        }
    )

class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = Field(default="validation_error")
    message: str = Field(..., description="Validation error summary")
    details: list[dict] = Field(..., description="Field-level validation errors")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "message": "Request validation failed",
                "details": [
                    {
                        "loc": ["body", "text"],
                        "msg": "Field required",
                        "type": "missing"
                    }
                ]
            }
        }
    )
```

### 3.5 Model Validation Examples

```python
# Custom validators
from pydantic import field_validator, model_validator

class ClaimCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    source_url: Optional[HttpUrl] = None

    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not just whitespace"""
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v.strip()

    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validate source URL is accessible (optional check)"""
        if v is not None:
            # Could add additional URL validation here
            pass
        return v

# Model-level validation
class VerdictResponse(BaseModel):
    verdict: str
    confidence: float
    evidence: list[EvidenceSummary]

    @model_validator(mode='after')
    def validate_verdict_evidence_consistency(self):
        """Ensure verdict matches evidence relationships"""
        if self.verdict == "SUPPORTED":
            supporting = [e for e in self.evidence if e.relationship == "supports"]
            if not supporting:
                logger.warning(
                    "verdict_evidence_mismatch",
                    verdict=self.verdict,
                    evidence_count=len(self.evidence)
                )
        return self
```

---

## 4. Dependency Injection

### 4.1 Dependency Injection Overview

FastAPI's dependency injection system provides:
- Clean separation of concerns
- Easy testing (mock dependencies)
- Resource management (database sessions)
- Configuration injection
- Lazy initialization

**Common dependency types**:
- Database sessions
- Repository instances
- Configuration objects
- ML model instances
- Authentication/authorization

### 4.2 Database Session Dependency

```python
# api/dependencies.py
from sqlalchemy.orm import Session
from typing import Generator

from ..db.session import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Provides a database session for the request lifecycle.
    Automatically commits on success or rolls back on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit if no exception
    except Exception:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()  # Always close session
```

### 4.3 Repository Dependencies

```python
# api/dependencies.py (continued)
from ..repositories.claims import ClaimRepository
from ..repositories.verdicts import VerdictRepository
from ..repositories.evidence import EvidenceRepository

def get_claim_repository(
    db: Session = Depends(get_db)
) -> ClaimRepository:
    """Inject claim repository"""
    return ClaimRepository(db)

def get_verdict_repository(
    db: Session = Depends(get_db)
) -> VerdictRepository:
    """Inject verdict repository"""
    return VerdictRepository(db)

def get_evidence_repository(
    db: Session = Depends(get_db)
) -> EvidenceRepository:
    """Inject evidence repository"""
    return EvidenceRepository(db)

# Usage in routes
@router.get("/claims/{claim_id}")
def get_claim(
    claim_id: UUID,
    repo: ClaimRepository = Depends(get_claim_repository)
):
    return repo.get(claim_id)
```

### 4.4 ML Model Dependencies (Lazy Loading)

```python
# api/dependencies.py (continued)
from typing import Optional
from ..ml.embedder import Embedder
from ..ml.nli import NLIModel
from ..config import get_settings

# Module-level cache for models (loaded once)
_embedder: Optional[Embedder] = None
_nli_model: Optional[NLIModel] = None

def get_embedder() -> Embedder:
    """
    Get embedder model (lazy load).

    Loads model on first use and caches for subsequent requests.
    """
    global _embedder
    if _embedder is None:
        settings = get_settings()
        logger.info("loading_embedder_model")
        _embedder = Embedder(model_name=settings.embedding_model)
        logger.info("embedder_model_loaded")
    return _embedder

def get_nli_model() -> NLIModel:
    """
    Get NLI model (lazy load).

    Loads model on first use and caches for subsequent requests.
    """
    global _nli_model
    if _nli_model is None:
        settings = get_settings()
        logger.info("loading_nli_model")
        _nli_model = NLIModel(model_name=settings.nli_model)
        logger.info("nli_model_loaded")
    return _nli_model

def unload_models() -> None:
    """Unload models from memory (called on shutdown)"""
    global _embedder, _nli_model
    _embedder = None
    _nli_model = None
    logger.info("models_unloaded")
```

### 4.5 Configuration Dependency

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application configuration"""

    # App
    app_name: str = "TruthGraph v0"
    version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL"
    )

    # ML Models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nli_model: str = "microsoft/deberta-v3-base"

    # API
    cors_origins: list[str] = ["http://localhost:5173"]
    request_timeout: int = 60  # seconds

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Usage in dependencies
def get_config() -> Settings:
    """Configuration dependency"""
    return get_settings()
```

### 4.6 Dependency Injection Best Practices

**1. Use Depends() for all shared resources**:
```python
# Good
@router.get("/claims/{claim_id}")
def get_claim(
    claim_id: UUID,
    repo: ClaimRepository = Depends(get_claim_repository)
):
    return repo.get(claim_id)

# Bad (tightly coupled)
@router.get("/claims/{claim_id}")
def get_claim(claim_id: UUID):
    db = SessionLocal()  # Direct instantiation
    repo = ClaimRepository(db)
    return repo.get(claim_id)
```

**2. Chain dependencies**:
```python
def get_verification_service(
    embedder: Embedder = Depends(get_embedder),
    nli: NLIModel = Depends(get_nli_model),
    evidence_repo: EvidenceRepository = Depends(get_evidence_repository)
) -> VerificationService:
    """Inject verification service with its dependencies"""
    return VerificationService(
        embedder=embedder,
        nli=nli,
        evidence_repo=evidence_repo
    )
```

**3. Use generators for cleanup**:
```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Guaranteed cleanup
```

---

## 5. Error Handling

### 5.1 Error Handling Strategy

**Goals**:
- Consistent error format across all endpoints
- Appropriate HTTP status codes
- Helpful error messages for debugging
- Don't leak sensitive information
- Log errors with context

### 5.2 Custom Exception Classes

```python
# exceptions.py
from fastapi import HTTPException, status
from typing import Optional

class TruthGraphException(Exception):
    """Base exception for TruthGraph errors"""
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class ClaimNotFoundError(TruthGraphException):
    """Claim not found"""
    def __init__(self, claim_id: str):
        super().__init__(
            message=f"Claim {claim_id} not found",
            error_code="claim_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"claim_id": claim_id}
        )

class VerdictNotFoundError(TruthGraphException):
    """Verdict not found"""
    def __init__(self, claim_id: str):
        super().__init__(
            message=f"No verdict found for claim {claim_id}",
            error_code="verdict_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"claim_id": claim_id}
        )

class VerificationError(TruthGraphException):
    """Error during verification process"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="verification_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class DatabaseError(TruthGraphException):
    """Database operation failed"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class ModelLoadError(TruthGraphException):
    """ML model failed to load"""
    def __init__(self, model_name: str, error: str):
        super().__init__(
            message=f"Failed to load model {model_name}",
            error_code="model_load_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"model_name": model_name, "error": error}
        )
```

### 5.3 Global Exception Handlers

```python
# app.py (continued)
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers"""

    @app.exception_handler(TruthGraphException)
    async def truthgraph_exception_handler(
        request: Request,
        exc: TruthGraphException
    ) -> JSONResponse:
        """Handle custom TruthGraph exceptions"""
        logger.error(
            "truthgraph_exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
            details=exc.details
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        errors = exc.errors()

        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=errors
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": errors
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request,
        exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle database errors"""
        logger.error(
            "database_error",
            path=request.url.path,
            error=str(exc)
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "database_error",
                "message": "Database operation failed",
                "details": {}  # Don't leak DB details
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Catch-all for unexpected errors"""
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": {}  # Don't leak error details in production
            }
        )
```

### 5.4 Using Exceptions in Routes

```python
# api/routes/claims.py
@router.get("/claims/{claim_id}")
def get_claim(
    claim_id: UUID,
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimResponse:
    claim = repo.get(claim_id)
    if not claim:
        raise ClaimNotFoundError(str(claim_id))  # Custom exception

    logger.info("claim_retrieved", claim_id=str(claim_id))
    return claim

# api/routes/verdicts.py
@router.get("/verdicts/{claim_id}")
def get_verdict(
    claim_id: UUID,
    repo: VerdictRepository = Depends(get_verdict_repository)
) -> VerdictResponse:
    verdict = repo.get_by_claim(claim_id)
    if not verdict:
        raise VerdictNotFoundError(str(claim_id))  # Custom exception

    return verdict
```

### 5.5 Error Response Examples

**404 Not Found**:
```json
{
  "error": "claim_not_found",
  "message": "Claim 550e8400-e29b-41d4-a716-446655440000 not found",
  "details": {
    "claim_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**422 Validation Error**:
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [
    {
      "loc": ["body", "text"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

**500 Internal Server Error**:
```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred",
  "details": {}
}
```

---

## 6. Synchronous Endpoints

### 6.1 Why Synchronous for v0

**Rationale**:
- **Simpler to reason about**: Linear execution flow
- **Easier to debug**: Standard Python debugging works
- **Good enough performance**: 60s verification target is achievable
- **Less infrastructure**: No need for message queues, workers
- **Faster development**: Skip async complexity

**When to use async (v1)**:
- Long-running operations (>60s)
- High concurrency requirements
- Event-driven architecture
- Multiple I/O operations in parallel

### 6.2 Synchronous vs Async Trade-offs

| Aspect | Synchronous (v0) | Async (v1) |
|--------|------------------|------------|
| **Complexity** | Low | High |
| **Concurrency** | Limited by threads | High (thousands of connections) |
| **Resource usage** | Higher (thread per request) | Lower (event loop) |
| **Debugging** | Easier | More complex |
| **Database** | Standard SQLAlchemy | Async SQLAlchemy (asyncpg) |
| **Testing** | Standard pytest | pytest-asyncio required |
| **Error handling** | Try/except | Try/except + asyncio.CancelledError |

### 6.3 Synchronous Endpoint Patterns

**Standard CRUD operations**:
```python
@router.post("/claims")
def create_claim(
    claim: ClaimCreate,
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimResponse:
    """Synchronous claim creation (fast)"""
    return repo.create(claim)

@router.get("/claims/{claim_id}")
def get_claim(
    claim_id: UUID,
    repo: ClaimRepository = Depends(get_claim_repository)
) -> ClaimResponse:
    """Synchronous claim retrieval (fast)"""
    claim = repo.get(claim_id)
    if not claim:
        raise ClaimNotFoundError(str(claim_id))
    return claim
```

**Long-running operations** (verification):
```python
@router.post("/claims/{claim_id}/verify")
def verify_claim(
    claim_id: UUID,
    claim_repo: ClaimRepository = Depends(get_claim_repository),
    verification_service: VerificationService = Depends(get_verification_service)
) -> VerdictResponse:
    """
    Synchronous verification (may take 30-60s).

    Client will wait for response. This is acceptable for v0 MVP.
    In v1, this becomes async with webhook/polling.
    """
    claim = claim_repo.get(claim_id)
    if not claim:
        raise ClaimNotFoundError(str(claim_id))

    # This blocks but returns within 60s
    verdict = verification_service.verify(claim)

    return verdict
```

### 6.4 Timeout Handling

**Request-level timeout** (middleware):
```python
class TimeoutMiddleware(BaseHTTPMiddleware):
    """Timeout requests after specified duration"""
    def __init__(self, app, timeout: int = 60):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "request_timeout",
                    "message": f"Request exceeded {self.timeout}s timeout"
                }
            )
```

**Operation-level timeout** (function):
```python
import signal
from contextlib import contextmanager

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds: int):
    """Context manager for operation timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")

    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# Usage
def verify_claim(claim: Claim) -> Verdict:
    try:
        with timeout(55):  # 5s buffer before request timeout
            return perform_verification(claim)
    except TimeoutError:
        raise VerificationError("Verification timed out")
```

### 6.5 Blocking I/O Patterns

**Database operations** (blocking but fast):
```python
def create_claim(claim_data: ClaimCreate, db: Session) -> Claim:
    """Blocking database write (< 100ms)"""
    db_claim = Claim(**claim_data.dict())
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim
```

**ML model inference** (blocking but cached):
```python
def embed_text(text: str, embedder: Embedder) -> list[float]:
    """Blocking embedding generation (~ 100ms per text)"""
    return embedder.encode(text)

def check_entailment(premise: str, hypothesis: str, nli: NLIModel) -> dict:
    """Blocking NLI inference (~ 200ms per pair)"""
    return nli.predict(premise, hypothesis)
```

**Combined verification** (blocking, may take 30-60s):
```python
def verify_claim(claim: Claim, service: VerificationService) -> Verdict:
    """
    Full verification pipeline (synchronous).

    Steps:
    1. Embed claim (~ 100ms)
    2. Retrieve evidence (~ 500ms for 1000 docs)
    3. Run NLI on top-k evidence (~ 20s for 100 pairs)
    4. Aggregate results (~ 100ms)
    5. Save verdict (~ 100ms)

    Total: ~20-30s (within 60s timeout)
    """
    # All steps block but complete within timeout
    claim_embedding = service.embed_claim(claim.text)
    evidence_docs = service.retrieve_evidence(claim_embedding, top_k=100)
    nli_results = service.run_nli_batch(claim.text, evidence_docs)
    verdict = service.aggregate_verdict(nli_results)
    saved_verdict = service.save_verdict(claim.id, verdict)

    return saved_verdict
```

### 6.6 How to Add Async in v1

**Step 1: Make database async**:
```python
# v0 (sync)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# v1 (async)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**Step 2: Convert routes to async**:
```python
# v0 (sync)
@router.get("/claims/{claim_id}")
def get_claim(claim_id: UUID, db: Session = Depends(get_db)):
    return db.query(Claim).filter(Claim.id == claim_id).first()

# v1 (async)
@router.get("/claims/{claim_id}")
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    return result.scalar_one_or_none()
```

**Step 3: Use background tasks for long operations**:
```python
from fastapi import BackgroundTasks

@router.post("/claims/{claim_id}/verify")
async def verify_claim_async(
    claim_id: UUID,
    background_tasks: BackgroundTasks,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Async verification (v1).

    Returns immediately with 202 Accepted.
    Client polls /verdicts/{claim_id} for result.
    """
    background_tasks.add_task(service.verify, claim_id)

    return JSONResponse(
        status_code=202,
        content={
            "message": "Verification started",
            "claim_id": str(claim_id),
            "status_url": f"/api/v1/verdicts/{claim_id}"
        }
    )
```

---

## 7. Testing Strategy

### 7.1 Testing Pyramid

```text
        /\
       /  \
      / E2E \ (10%) - Full system tests
     /______\
    /        \
   /  Integ.  \ (30%) - API tests with test DB
  /____________\
 /              \
/  Unit Tests    \ (60%) - Pure function tests
/__________________\
```

### 7.2 Test Organization

```text
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_models.py       # Pydantic model tests
│   ├── test_repositories.py # Repository logic tests
│   └── test_services.py     # Service logic tests
├── integration/
│   ├── test_api_claims.py   # Claim endpoint tests
│   ├── test_api_verdicts.py # Verdict endpoint tests
│   └── test_database.py     # Database integration tests
└── e2e/
    └── test_verification.py # End-to-end verification flow
```

### 7.3 Test Fixtures

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from truthgraph.app import create_app
from truthgraph.db.base import Base
from truthgraph.db.session import get_db
from truthgraph.api.dependencies import get_embedder, get_nli_model

# Test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def mock_embedder():
    """Mock embedder for tests (avoid loading real model)"""
    class MockEmbedder:
        def encode(self, text: str) -> list[float]:
            # Return dummy embedding
            return [0.1] * 384

    return MockEmbedder()

@pytest.fixture(scope="session")
def mock_nli():
    """Mock NLI model for tests"""
    class MockNLI:
        def predict(self, premise: str, hypothesis: str) -> dict:
            # Return dummy prediction
            return {
                "label": "entailment",
                "score": 0.85
            }

    return MockNLI()

@pytest.fixture(scope="function")
def override_ml_models(mock_embedder, mock_nli):
    """Override ML model dependencies with mocks"""
    app = create_app()
    app.dependency_overrides[get_embedder] = lambda: mock_embedder
    app.dependency_overrides[get_nli_model] = lambda: mock_nli
    yield app
    app.dependency_overrides.clear()
```

### 7.4 Unit Tests

**Test Pydantic models**:
```python
# tests/unit/test_models.py
import pytest
from pydantic import ValidationError
from truthgraph.api.models import ClaimCreate, ClaimResponse

def test_claim_create_valid():
    """Test valid claim creation"""
    claim = ClaimCreate(
        text="The Earth is round",
        source_url="https://example.com"
    )
    assert claim.text == "The Earth is round"
    assert str(claim.source_url) == "https://example.com/"

def test_claim_create_text_required():
    """Test text field is required"""
    with pytest.raises(ValidationError) as exc_info:
        ClaimCreate()

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("text",) for e in errors)

def test_claim_create_text_min_length():
    """Test text minimum length validation"""
    with pytest.raises(ValidationError):
        ClaimCreate(text="Short")  # < 10 chars

def test_claim_create_text_max_length():
    """Test text maximum length validation"""
    with pytest.raises(ValidationError):
        ClaimCreate(text="x" * 5001)  # > 5000 chars

def test_claim_create_invalid_url():
    """Test invalid URL validation"""
    with pytest.raises(ValidationError):
        ClaimCreate(
            text="Valid claim text here",
            source_url="not-a-valid-url"
        )
```

**Test repository logic**:
```python
# tests/unit/test_repositories.py
import pytest
from uuid import uuid4
from truthgraph.repositories.claims import ClaimRepository
from truthgraph.db.models import Claim
from truthgraph.api.models import ClaimCreate

def test_create_claim(test_db):
    """Test claim creation"""
    repo = ClaimRepository(test_db)
    claim_data = ClaimCreate(text="Test claim")

    claim = repo.create(claim_data)

    assert claim.id is not None
    assert claim.text == "Test claim"
    assert claim.submitted_at is not None

def test_get_claim(test_db):
    """Test claim retrieval"""
    repo = ClaimRepository(test_db)

    # Create claim
    created = repo.create(ClaimCreate(text="Test claim"))

    # Retrieve claim
    retrieved = repo.get(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.text == created.text

def test_get_claim_not_found(test_db):
    """Test retrieving non-existent claim"""
    repo = ClaimRepository(test_db)

    claim = repo.get(uuid4())

    assert claim is None

def test_list_claims_pagination(test_db):
    """Test claim listing with pagination"""
    repo = ClaimRepository(test_db)

    # Create 25 claims
    for i in range(25):
        repo.create(ClaimCreate(text=f"Claim {i}"))

    # Get first page
    page1 = repo.list(skip=0, limit=10)
    assert len(page1) == 10

    # Get second page
    page2 = repo.list(skip=10, limit=10)
    assert len(page2) == 10

    # Get third page
    page3 = repo.list(skip=20, limit=10)
    assert len(page3) == 5

    # Verify no overlap
    page1_ids = {c.id for c in page1}
    page2_ids = {c.id for c in page2}
    assert page1_ids.isdisjoint(page2_ids)
```

### 7.5 Integration Tests

**Test API endpoints**:
```python
# tests/integration/test_api_claims.py
import pytest
from uuid import uuid4

def test_create_claim_success(client):
    """Test successful claim creation"""
    response = client.post(
        "/api/v1/claims",
        json={
            "text": "The Earth is round",
            "source_url": "https://example.com"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "The Earth is round"
    assert "id" in data
    assert "submitted_at" in data

def test_create_claim_validation_error(client):
    """Test claim creation with invalid data"""
    response = client.post(
        "/api/v1/claims",
        json={"text": "Short"}  # Too short
    )

    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"

def test_list_claims(client):
    """Test listing claims"""
    # Create some claims
    for i in range(5):
        client.post(
            "/api/v1/claims",
            json={"text": f"Test claim {i}"}
        )

    # List claims
    response = client.get("/api/v1/claims")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 5
    assert data["total"] == 5

def test_list_claims_pagination(client):
    """Test pagination"""
    # Create 25 claims
    for i in range(25):
        client.post(
            "/api/v1/claims",
            json={"text": f"Test claim {i}"}
        )

    # Get first page
    response = client.get("/api/v1/claims?skip=0&limit=10")
    data = response.json()
    assert len(data["items"]) == 10
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["total"] == 25

def test_get_claim_success(client):
    """Test retrieving a specific claim"""
    # Create claim
    create_response = client.post(
        "/api/v1/claims",
        json={"text": "Test claim"}
    )
    claim_id = create_response.json()["id"]

    # Get claim
    response = client.get(f"/api/v1/claims/{claim_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == claim_id
    assert data["text"] == "Test claim"

def test_get_claim_not_found(client):
    """Test retrieving non-existent claim"""
    response = client.get(f"/api/v1/claims/{uuid4()}")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "claim_not_found"
```

### 7.6 End-to-End Tests

**Test full verification flow**:
```python
# tests/e2e/test_verification.py
import pytest

def test_full_verification_flow(client, test_db):
    """Test complete claim verification flow"""
    # 1. Create claim
    create_response = client.post(
        "/api/v1/claims",
        json={"text": "The Earth is round"}
    )
    assert create_response.status_code == 201
    claim_id = create_response.json()["id"]

    # 2. Trigger verification (in v0, this could be automatic)
    # For now, assume verification happens in background

    # 3. Check claim includes verdict
    claim_response = client.get(f"/api/v1/claims/{claim_id}")
    assert claim_response.status_code == 200
    claim_data = claim_response.json()

    # Verdict might not be ready yet in real scenario
    # For test, we can mock or wait

    # 4. Get verdict details
    verdict_response = client.get(f"/api/v1/verdicts/{claim_id}")
    if verdict_response.status_code == 200:
        verdict_data = verdict_response.json()
        assert "verdict" in verdict_data
        assert verdict_data["verdict"] in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        assert 0.0 <= verdict_data["confidence"] <= 1.0
```

### 7.7 Test Coverage

**Run tests with coverage**:
```bash
pytest --cov=truthgraph --cov-report=html --cov-report=term

# Target: 70%+ coverage
# Focus on:
# - Core business logic (100% coverage)
# - API endpoints (90% coverage)
# - Error handlers (80% coverage)
# - Models and repositories (80% coverage)
```

**Coverage configuration** (.coveragerc):
```ini
[run]
source = truthgraph
omit =
    */tests/*
    */conftest.py
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

---

## 8. Code Examples

### 8.1 Complete main.py

```python
# truthgraph/main.py
"""
TruthGraph v0 - FastAPI application entry point.

This is a modular monolith with clear module boundaries:
- api/: HTTP routes and request handling
- db/: Database models and session management
- repositories/: Data access layer
- services/: Business logic
- ml/: ML model loading and inference

The application uses synchronous operations for simplicity
and acceptable performance (<60s for verification).
"""

import uvicorn
from .app import create_app
from .config import get_settings

# Create application instance
app = create_app()

def main() -> None:
    """Run the application"""
    settings = get_settings()

    uvicorn.run(
        "truthgraph.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
```

### 8.2 Complete api/routes/claims.py

```python
# truthgraph/api/routes/claims.py
"""
Claim API routes.

Handles claim submission, retrieval, and listing.
All operations are synchronous for v0.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated
from uuid import UUID
import structlog

from ..dependencies import get_claim_repository, get_verification_service
from ..models import ClaimCreate, ClaimResponse, ClaimListResponse
from ...repositories.claims import ClaimRepository
from ...services.verification import VerificationService
from ...exceptions import ClaimNotFoundError

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post(
    "/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new claim",
    description="Submit a claim for verification",
    responses={
        201: {"description": "Claim created successfully"},
        422: {"description": "Validation error"}
    }
)
def create_claim(
    claim: ClaimCreate,
    repo: Annotated[ClaimRepository, Depends(get_claim_repository)]
) -> ClaimResponse:
    """
    Create a new claim for verification.

    The claim is created immediately and returned with a unique ID.
    Verification happens asynchronously (in v0, on-demand).

    Args:
        claim: Claim data (text and optional source URL)
        repo: Claim repository (injected)

    Returns:
        Created claim with ID and timestamp

    Example:
        ```
        POST /api/v1/claims
        {
          "text": "The Earth is approximately spherical",
          "source_url": "https://example.com/article"
        }
        ```
    """
    db_claim = repo.create(claim)

    logger.info(
        "claim_created",
        claim_id=str(db_claim.id),
        text_length=len(claim.text)
    )

    return db_claim

@router.get(
    "/claims",
    response_model=ClaimListResponse,
    summary="List all claims",
    description="Get paginated list of claims",
    responses={
        200: {"description": "Claims retrieved successfully"}
    }
)
def list_claims(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    repo: Annotated[ClaimRepository, Depends(get_claim_repository)] = None
) -> ClaimListResponse:
    """
    List claims with pagination.

    Returns claims in reverse chronological order (newest first).

    Args:
        skip: Number of claims to skip (for pagination)
        limit: Maximum number of claims to return (1-100)
        repo: Claim repository (injected)

    Returns:
        Paginated list of claims with total count

    Example:
        ```
        GET /api/v1/claims?skip=0&limit=20
        ```
    """
    total = repo.count()
    items = repo.list(skip=skip, limit=limit)

    logger.info(
        "claims_listed",
        count=len(items),
        total=total,
        skip=skip,
        limit=limit
    )

    return ClaimListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get(
    "/claims/{claim_id}",
    response_model=ClaimResponse,
    summary="Get claim by ID",
    description="Retrieve a specific claim",
    responses={
        200: {"description": "Claim retrieved successfully"},
        404: {"description": "Claim not found"}
    }
)
def get_claim(
    claim_id: UUID,
    repo: Annotated[ClaimRepository, Depends(get_claim_repository)]
) -> ClaimResponse:
    """
    Get a specific claim by ID.

    Includes verdict information if verification has completed.

    Args:
        claim_id: Unique claim identifier
        repo: Claim repository (injected)

    Returns:
        Claim data with verdict (if available)

    Raises:
        ClaimNotFoundError: If claim doesn't exist

    Example:
        ```
        GET /api/v1/claims/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    claim = repo.get(claim_id)
    if not claim:
        logger.warning("claim_not_found", claim_id=str(claim_id))
        raise ClaimNotFoundError(str(claim_id))

    logger.info("claim_retrieved", claim_id=str(claim_id))
    return claim

@router.post(
    "/claims/{claim_id}/verify",
    response_model=ClaimResponse,
    summary="Trigger claim verification",
    description="Manually trigger verification for a claim",
    responses={
        200: {"description": "Verification completed"},
        404: {"description": "Claim not found"},
        504: {"description": "Verification timed out"}
    }
)
def verify_claim(
    claim_id: UUID,
    claim_repo: Annotated[ClaimRepository, Depends(get_claim_repository)],
    verification_service: Annotated[VerificationService, Depends(get_verification_service)]
) -> ClaimResponse:
    """
    Trigger verification for a claim.

    This is a synchronous operation that may take 30-60 seconds.
    In v0, this is acceptable. In v1, this becomes async with background tasks.

    Args:
        claim_id: Claim to verify
        claim_repo: Claim repository (injected)
        verification_service: Verification service (injected)

    Returns:
        Updated claim with verdict

    Raises:
        ClaimNotFoundError: If claim doesn't exist
        VerificationError: If verification fails
    """
    # Get claim
    claim = claim_repo.get(claim_id)
    if not claim:
        raise ClaimNotFoundError(str(claim_id))

    logger.info("verification_started", claim_id=str(claim_id))

    # Run verification (blocks for 30-60s)
    try:
        verdict = verification_service.verify(claim)
        logger.info(
            "verification_completed",
            claim_id=str(claim_id),
            verdict=verdict.verdict,
            confidence=verdict.confidence
        )
    except Exception as e:
        logger.error(
            "verification_failed",
            claim_id=str(claim_id),
            error=str(e),
            exc_info=True
        )
        raise

    # Return updated claim
    return claim_repo.get(claim_id)
```

### 8.3 Complete api/routes/verdicts.py

```python
# truthgraph/api/routes/verdicts.py
"""
Verdict API routes.

Handles verdict retrieval and evidence details.
"""

from fastapi import APIRouter, Depends, status
from typing import Annotated
from uuid import UUID
import structlog

from ..dependencies import get_verdict_repository
from ..models import VerdictResponse
from ...repositories.verdicts import VerdictRepository
from ...exceptions import VerdictNotFoundError

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get(
    "/verdicts/{claim_id}",
    response_model=VerdictResponse,
    summary="Get verdict for claim",
    description="Retrieve verification verdict and supporting evidence",
    responses={
        200: {"description": "Verdict retrieved successfully"},
        404: {"description": "Verdict not found"}
    }
)
def get_verdict(
    claim_id: UUID,
    repo: Annotated[VerdictRepository, Depends(get_verdict_repository)]
) -> VerdictResponse:
    """
    Get the verdict for a specific claim.

    Returns the verdict classification, confidence score,
    reasoning, and supporting/refuting evidence.

    Args:
        claim_id: ID of the claim to get verdict for
        repo: Verdict repository (injected)

    Returns:
        Verdict with evidence details

    Raises:
        VerdictNotFoundError: If claim hasn't been verified yet

    Example:
        ```
        GET /api/v1/verdicts/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    verdict = repo.get_by_claim(claim_id)
    if not verdict:
        logger.warning("verdict_not_found", claim_id=str(claim_id))
        raise VerdictNotFoundError(str(claim_id))

    logger.info(
        "verdict_retrieved",
        claim_id=str(claim_id),
        verdict=verdict.verdict,
        evidence_count=len(verdict.evidence)
    )

    return verdict
```

### 8.4 Complete api/dependencies.py

```python
# truthgraph/api/dependencies.py
"""
FastAPI dependency injection.

Provides database sessions, repositories, services,
and ML models to route handlers.
"""

from typing import Generator, Optional
from sqlalchemy.orm import Session
import structlog

from ..db.session import SessionLocal
from ..repositories.claims import ClaimRepository
from ..repositories.verdicts import VerdictRepository
from ..repositories.evidence import EvidenceRepository
from ..services.verification import VerificationService
from ..ml.embedder import Embedder
from ..ml.nli import NLIModel
from ..config import get_settings

logger = structlog.get_logger(__name__)

# =============================================================================
# Database Session
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Provides a database session for the request lifecycle.
    Automatically commits on success or rolls back on error.

    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# =============================================================================
# Repositories
# =============================================================================

def get_claim_repository(
    db: Session = Depends(get_db)
) -> ClaimRepository:
    """Inject claim repository"""
    return ClaimRepository(db)

def get_verdict_repository(
    db: Session = Depends(get_db)
) -> VerdictRepository:
    """Inject verdict repository"""
    return VerdictRepository(db)

def get_evidence_repository(
    db: Session = Depends(get_db)
) -> EvidenceRepository:
    """Inject evidence repository"""
    return EvidenceRepository(db)

# =============================================================================
# ML Models (Lazy Loading)
# =============================================================================

# Module-level cache for models
_embedder: Optional[Embedder] = None
_nli_model: Optional[NLIModel] = None

def get_embedder() -> Embedder:
    """
    Get embedder model (lazy load).

    Loads model on first use and caches for subsequent requests.
    This avoids loading models on startup (faster startup time).

    Returns:
        Embedder instance
    """
    global _embedder
    if _embedder is None:
        settings = get_settings()
        logger.info(
            "loading_embedder_model",
            model_name=settings.embedding_model
        )
        _embedder = Embedder(model_name=settings.embedding_model)
        logger.info("embedder_model_loaded")
    return _embedder

def get_nli_model() -> NLIModel:
    """
    Get NLI model (lazy load).

    Loads model on first use and caches for subsequent requests.

    Returns:
        NLI model instance
    """
    global _nli_model
    if _nli_model is None:
        settings = get_settings()
        logger.info(
            "loading_nli_model",
            model_name=settings.nli_model
        )
        _nli_model = NLIModel(model_name=settings.nli_model)
        logger.info("nli_model_loaded")
    return _nli_model

def unload_models() -> None:
    """
    Unload models from memory.

    Called during application shutdown.
    """
    global _embedder, _nli_model
    _embedder = None
    _nli_model = None
    logger.info("models_unloaded")

# =============================================================================
# Services
# =============================================================================

def get_verification_service(
    claim_repo: ClaimRepository = Depends(get_claim_repository),
    verdict_repo: VerdictRepository = Depends(get_verdict_repository),
    evidence_repo: EvidenceRepository = Depends(get_evidence_repository),
    embedder: Embedder = Depends(get_embedder),
    nli: NLIModel = Depends(get_nli_model)
) -> VerificationService:
    """
    Inject verification service with all dependencies.

    This demonstrates dependency chaining in FastAPI.
    All dependencies are resolved automatically.
    """
    return VerificationService(
        claim_repo=claim_repo,
        verdict_repo=verdict_repo,
        evidence_repo=evidence_repo,
        embedder=embedder,
        nli=nli
    )
```

### 8.5 Complete api/models.py

```python
# truthgraph/api/models.py
"""
Pydantic models for request/response validation.

These models define the API contract and provide:
- Request validation
- Response serialization
- OpenAPI schema generation
- Type safety
"""

from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

# =============================================================================
# Claim Models
# =============================================================================

class ClaimCreate(BaseModel):
    """Request model for creating a claim"""
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The claim text to verify"
    )
    source_url: Optional[HttpUrl] = Field(
        None,
        description="Optional URL where the claim was found"
    )

    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not just whitespace"""
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "The Earth is approximately spherical",
                "source_url": "https://example.com/science-article"
            }
        }
    )

class VerdictSummary(BaseModel):
    """Embedded verdict summary in claim response"""
    verdict: str = Field(..., description="SUPPORTED, REFUTED, or INSUFFICIENT")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

class ClaimResponse(BaseModel):
    """Response model for claim data"""
    id: UUID
    text: str
    source_url: Optional[HttpUrl] = None
    submitted_at: datetime
    verdict: Optional[VerdictSummary] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "text": "The Earth is approximately spherical",
                "source_url": "https://example.com/science-article",
                "submitted_at": "2025-01-15T10:30:00Z",
                "verdict": {
                    "verdict": "SUPPORTED",
                    "confidence": 0.95
                }
            }
        }
    )

class ClaimListResponse(BaseModel):
    """Response model for paginated claim list"""
    items: list[ClaimResponse]
    total: int = Field(..., ge=0)
    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=100)

    @property
    def has_more(self) -> bool:
        """Check if there are more results"""
        return self.skip + len(self.items) < self.total

# =============================================================================
# Verdict Models
# =============================================================================

class EvidenceSummary(BaseModel):
    """Embedded evidence summary in verdict response"""
    id: UUID
    content: str = Field(..., max_length=500)
    relationship: str = Field(..., pattern="^(supports|refutes|neutral)$")
    confidence: float = Field(..., ge=0.0, le=1.0)

class VerdictResponse(BaseModel):
    """Response model for verdict data"""
    id: UUID
    claim_id: UUID
    verdict: str = Field(..., pattern="^(SUPPORTED|REFUTED|INSUFFICIENT)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "claim_id": "550e8400-e29b-41d4-a716-446655440000",
                "verdict": "SUPPORTED",
                "confidence": 0.95,
                "reasoning": "Strong scientific consensus",
                "evidence": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440002",
                        "content": "NASA confirms Earth shape...",
                        "relationship": "supports",
                        "confidence": 0.98
                    }
                ],
                "created_at": "2025-01-15T10:30:15Z"
            }
        }
    )

# =============================================================================
# Error Models
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error code (machine-readable)")
    message: str = Field(..., description="Error message (human-readable)")
    details: Optional[dict] = Field(None, description="Additional error context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "claim_not_found",
                "message": "Claim not found",
                "details": {"claim_id": "550e8400-e29b-41d4-a716-446655440000"}
            }
        }
    )
```

---

## 9. Performance Considerations

### 9.1 Performance Targets

| Operation | Target | Acceptable | Notes |
|-----------|--------|------------|-------|
| POST /claims | < 200ms | < 500ms | Database write only |
| GET /claims | < 100ms | < 300ms | Paginated query |
| GET /claims/{id} | < 100ms | < 300ms | Single record fetch |
| POST /claims/{id}/verify | < 60s | < 90s | Full verification pipeline |
| GET /verdicts/{id} | < 100ms | < 300ms | Fetch with evidence join |
| System memory | < 2GB | < 4GB | With ML models loaded |

### 9.2 Lazy Loading ML Models

**Problem**: ML models are large (embedder: ~100MB, NLI: ~500MB)

**Solution**: Load on first use, not on startup

**Implementation**:
```python
# Bad: Load on startup (slow, wastes memory if unused)
embedder = Embedder()  # Loaded immediately
nli = NLIModel()  # Loaded immediately

# Good: Load on first use (fast startup, memory efficient)
_embedder: Optional[Embedder] = None

def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()  # Loaded only when needed
    return _embedder
```

**Benefits**:
- Fast startup (< 2s instead of 10-15s)
- Memory efficient (only load if used)
- Testable (can mock in tests)

### 9.3 Database Connection Pooling

**Problem**: Creating new connections is expensive (50-100ms)

**Solution**: Connection pool with SQLAlchemy

**Implementation**:
```python
# db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # Max 10 connections
    max_overflow=20,       # Allow 20 more if pool full
    pool_timeout=30,       # Wait 30s for connection
    pool_recycle=3600,     # Recycle connections after 1h
    pool_pre_ping=True,    # Test connections before use
    echo=False             # Don't log SQL (use in debug only)
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

**Tuning**:
- `pool_size`: Start with 10, increase if needed
- `max_overflow`: 2x pool_size is reasonable
- `pool_recycle`: Avoid stale connections (< DB timeout)
- `pool_pre_ping`: Small overhead but prevents errors

### 9.4 Query Optimization

**Use indexes**:
```sql
-- Fast claim lookup by ID
CREATE INDEX idx_claims_id ON claims(id);

-- Fast claim listing (newest first)
CREATE INDEX idx_claims_submitted_at ON claims(submitted_at DESC);

-- Fast verdict lookup by claim
CREATE INDEX idx_verdicts_claim_id ON verdicts(claim_id);

-- Fast evidence retrieval (for embeddings)
CREATE INDEX idx_evidence_embedding ON evidence USING ivfflat (embedding vector_cosine_ops);
```

**Eager loading** (avoid N+1 queries):
```python
# Bad: N+1 queries
claims = db.query(Claim).all()
for claim in claims:
    verdict = db.query(Verdict).filter(Verdict.claim_id == claim.id).first()
    # 1 query for claims + N queries for verdicts

# Good: Single query with join
from sqlalchemy.orm import joinedload

claims = db.query(Claim).options(joinedload(Claim.verdict)).all()
# Single query with LEFT JOIN
```

**Pagination**:
```python
# Always paginate large results
def list_claims(skip: int = 0, limit: int = 20):
    return db.query(Claim).offset(skip).limit(limit).all()
```

### 9.5 Response Time Breakdown

**Typical verification request** (POST /claims/{id}/verify):

```text
Total: ~30s

1. Embed claim (100ms)
   - Load model: 0ms (cached)
   - Inference: 100ms

2. Retrieve evidence (500ms)
   - Query embeddings: 300ms
   - Compute similarity: 200ms
   - Top-k selection: 10ms

3. Run NLI (25s)
   - Load model: 0ms (cached)
   - Inference: 100 pairs × 250ms = 25s

4. Aggregate results (100ms)
   - Compute verdict: 50ms
   - Format response: 50ms

5. Save verdict (100ms)
   - Database write: 100ms
```

**Optimization opportunities**:
- **Batch NLI inference**: 100 pairs × 250ms → 10 batches × 2.5s = 25s
- **Parallel NLI**: Use threading for CPU-bound tasks
- **Top-k selection**: Reduce from 100 to 50 pairs (13s saved)
- **GPU inference**: NLI 25s → 5s (80% faster)

### 9.6 Memory Management

**Monitor memory usage**:
```python
import psutil
import os

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Log memory at key points
logger.info("memory_usage", mb=get_memory_usage())
```

**Expected memory profile**:
```text
Baseline (no models): ~100MB
+ Embedder loaded: ~200MB
+ NLI loaded: ~700MB
+ Processing peak: ~1.2GB
```

**Memory optimization**:
- Use CPU inference (not GPU in v0)
- Unload models if not used for 1h
- Limit batch sizes (max 10 at a time)
- Use generators for large result sets

### 9.7 Timeout Strategy

**Request timeout** (middleware):
```python
# Entire request must complete in 60s
TimeoutMiddleware(app, timeout=60)
```

**Operation timeout** (verification):
```python
# Verification must complete in 55s (5s buffer)
def verify_claim(claim: Claim) -> Verdict:
    with timeout(55):
        return perform_verification(claim)
```

**Component timeouts**:
- Database query: 5s
- Embedding inference: 5s
- NLI inference (per batch): 10s
- Total verification: 55s

---

## 10. Evolution to v1

### 10.1 What Stays the Same

**1. Database schema**:
- Same tables (claims, evidence, verdicts)
- Same columns and types
- Only add new columns (no breaking changes)

**2. API contracts**:
- Same endpoints (/api/v1/claims, /api/v1/verdicts)
- Same request/response formats
- Add new endpoints (don't change existing)

**3. Domain models**:
- Same Pydantic models
- Same validation rules
- Add new fields (optional)

**4. Core logic**:
- Same verification algorithm
- Same ML models
- Same scoring rules

### 10.2 What Changes in v1

**1. Architecture: Monolith → Microservices**

```text
v0 (Monolith):
┌──────────────────────┐
│   FastAPI App        │
│  ├─ API routes       │
│  ├─ Services         │
│  ├─ Repositories     │
│  └─ ML models        │
└──────────────────────┘

v1 (Microservices):
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ API Gateway  │   │ Verification │   │   Corpus     │
│   Service    │──▶│   Service    │──▶│   Service    │
│ (FastAPI)    │   │ (FastAPI)    │   │ (FastAPI)    │
└──────────────┘   └──────────────┘   └──────────────┘
       │                   │
       ▼                   ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │ Redis/RabbitMQ│
└──────────────┘   └──────────────┘
```

**2. Processing: Sync → Async**

```python
# v0: Synchronous (blocks for 60s)
@router.post("/claims/{claim_id}/verify")
def verify_claim(claim_id: UUID) -> VerdictResponse:
    return verification_service.verify(claim_id)  # Blocks

# v1: Asynchronous (returns immediately)
@router.post("/claims/{claim_id}/verify")
async def verify_claim(
    claim_id: UUID,
    background_tasks: BackgroundTasks
) -> dict:
    background_tasks.add_task(verification_service.verify, claim_id)
    return {"status": "started", "claim_id": str(claim_id)}
```

**3. Communication: Direct → Event-Driven**

```python
# v0: Direct function call
verdict = verification_service.verify(claim)
verdict_repo.save(verdict)

# v1: Event-driven with message queue
await event_bus.publish(
    "claim.verification_requested",
    {"claim_id": str(claim_id)}
)
# Verification service subscribes to event
# Publishes "claim.verification_completed" when done
```

**4. Database: Sync → Async**

```python
# v0: Synchronous SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# v1: Async SQLAlchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

# Routes become async
@router.get("/claims/{claim_id}")
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    return result.scalar_one_or_none()
```

### 10.3 Migration Steps (v0 → v1)

**Phase 1: Add async support (no breaking changes)**
1. Add async database support (keep sync as fallback)
2. Add async routes (keep sync routes for compatibility)
3. Test both sync and async paths

**Phase 2: Extract services (no breaking changes)**
1. Extract verification service to separate container
2. Add message queue (Redis Streams)
3. Update verification to publish events
4. Keep sync API for backward compatibility

**Phase 3: Full microservices (breaking changes acceptable)**
1. Split into API Gateway + Verification Service + Corpus Service
2. Remove sync endpoints
3. Require async clients
4. Update deployment (Docker Compose → Kubernetes)

### 10.4 Code Mapping: v0 → v1

**API Gateway Service** (v1) = `api/` (v0)
```text
v0: truthgraph/api/routes/claims.py
v1: api-gateway/app/routes/claims.py
    (same endpoints, same logic, different service)
```

**Verification Service** (v1) = `services/verification.py` (v0)
```text
v0: truthgraph/services/verification.py
v1: verification-service/app/verification.py
    (same algorithm, now in separate service)
```

**Corpus Service** (v1) = `services/retrieval.py` + `repositories/evidence.py` (v0)
```text
v0: truthgraph/services/retrieval.py
    truthgraph/repositories/evidence.py
v1: corpus-service/app/retrieval.py
    corpus-service/app/repositories.py
    (same logic, separate service)
```

### 10.5 Evolution Checklist

**Prepare for v1 (do in v0)**:
- ✅ Use module boundaries (api/, services/, repositories/)
- ✅ Use dependency injection (easy to mock/replace)
- ✅ Use Pydantic models (portable between services)
- ✅ Use repository pattern (abstract data access)
- ✅ Use structured logging (add request IDs)
- ✅ Use configuration management (env vars, not hardcoded)

**Don't do in v0 (wait for v1)**:
- ❌ Don't add authentication (defer to v1)
- ❌ Don't add message queues (defer to v1)
- ❌ Don't add distributed tracing (defer to v1)
- ❌ Don't add Kubernetes (defer to v1)
- ❌ Don't add multi-tenancy (defer to v1)

**Signs you need v1**:
- Verification takes >60s consistently
- Need to scale independently (API vs verification)
- Need horizontal scaling (multiple instances)
- Need better observability (tracing, metrics)
- Need multi-user support

---

## Conclusion

This FastAPI implementation guide provides a comprehensive foundation for TruthGraph v0. Key takeaways:

1. **Modular Monolith**: Single FastAPI app with clear module boundaries for easy extraction to microservices later

2. **Synchronous First**: Accept higher latency for v0 in exchange for simpler code and faster development

3. **Type Safety**: Pydantic V2 models provide runtime validation and clear API contracts

4. **Dependency Injection**: FastAPI's DI system enables clean architecture and testability

5. **Error Handling**: Consistent error responses and proper logging throughout

6. **Performance**: Lazy loading, connection pooling, and query optimization keep latency acceptable

7. **Evolution Path**: Clear mapping from v0 monolith to v1 microservices

**Next Steps**:
1. Implement core application structure (main.py, app.py, config.py)
2. Set up database models and repositories
3. Implement claim and verdict routes
4. Add ML model loading and inference
5. Implement verification service
6. Write tests (unit, integration, e2e)
7. Optimize performance
8. Prepare for v1 migration

**Reference Documents**:
- [v0 Overview](./00_overview.md)
- [Phase 1: Foundation](./phase_01_foundation.md)
- [Phase 2: Core Features](./phase_02_core_features.md) (coming soon)
- [v1 Overview](../v1/00_overview.md)

---

**Version**: 1.0
**Last Updated**: 2025-01-24
**Status**: Ready for Implementation
