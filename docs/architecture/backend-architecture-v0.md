# TruthGraph v0: Backend Architecture

## Executive Summary

TruthGraph v0 uses a **modular monolith** architecture - a single FastAPI application with clear internal boundaries that can be extracted to microservices later. This design delivers the core fact-checking functionality quickly while maintaining clean separation of concerns that enables future scaling.

**Key Architecture Decisions**:

- **Modular Monolith**: Single deployment unit with clear module boundaries (not microservices yet)
- **Synchronous Processing**: Direct function calls for verification workflow (acceptable for MVP <60s latency)
- **Three-Layer Architecture**: API → Domain → Infrastructure separation
- **Repository Pattern**: Abstract data access for future flexibility
- **Dependency Injection**: FastAPI's built-in DI for testability
- **Local-First**: No cloud dependencies, works offline after setup

**Why Modular Monolith for v0?**

- Faster development and deployment (single codebase, single container)
- Easier debugging (no distributed tracing complexity)
- Simpler testing (no service mocking, network issues)
- Clear upgrade path to v1 microservices (extract modules → services)
- Sufficient for MVP scope (<1000 claims/day, <10s verification time)

---

## High-Level Architecture

### System Context

```text
┌─────────────────────────────────────────────────────────────┐
│                  TruthGraph v0 MVP System                   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │   React     │  │   FastAPI   │  │ PostgreSQL  │
     │  Frontend   │  │  Monolith   │  │ + pgvector  │
     │ (port 5173) │  │ (port 8000) │  │ (port 5432) │
     └─────────────┘  └─────────────┘  └─────────────┘
           │                  │                  │
           └──────────────────┴──────────────────┘
                         Docker Compose
```

### Component Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Monolith (port 8000)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   API Layer (api/)                    │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Claims    │  │  Evidence  │  │  Verdicts  │     │  │
│  │  │  Routes    │  │  Routes    │  │  Routes    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  • Request/Response models (Pydantic)                │  │
│  │  • Input validation                                   │  │
│  │  • HTTP error handling                                │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │                  Domain Layer (domain/)               │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │   Claim    │  │  Evidence  │  │  Verdict   │     │  │
│  │  │  Service   │  │  Service   │  │  Service   │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  • Business logic                                     │  │
│  │  • Verification workflow                              │  │
│  │  • Aggregation/reasoning logic                        │  │
│  │  • Domain models (entities)                           │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │            Infrastructure Layer (infrastructure/)     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Repository │  │ Embeddings │  │   Config   │     │  │
│  │  │  Pattern   │  │   Loader   │  │  Manager   │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  • Database access (SQLAlchemy)                       │  │
│  │  • ML model loading/caching                           │  │
│  │  • Configuration management                           │  │
│  │  • Logging infrastructure                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ PostgreSQL + pgvector │
            │  • Claims table       │
            │  • Evidence table     │
            │  • Verdicts table     │
            │  • Vector embeddings  │
            └───────────────────────┘
```

---

## Module Structure and Boundaries

### Code Organization

```text
backend/
├── truthgraph/                    # Main package
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/                       # API Layer - HTTP interface
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── claims.py          # POST/GET /api/v1/claims
│   │   │   ├── evidence.py        # POST/GET /api/v1/evidence
│   │   │   └── verdicts.py        # GET /api/v1/verdicts
│   │   ├── models/                # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── claims.py
│   │   │   ├── evidence.py
│   │   │   └── verdicts.py
│   │   └── dependencies.py        # FastAPI dependencies
│   │
│   ├── domain/                    # Domain Layer - Business logic
│   │   ├── __init__.py
│   │   ├── models/                # Domain entities
│   │   │   ├── __init__.py
│   │   │   ├── claim.py
│   │   │   ├── evidence.py
│   │   │   └── verdict.py
│   │   ├── services/              # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── claim_service.py
│   │   │   ├── evidence_service.py
│   │   │   └── verification_service.py
│   │   └── interfaces/            # Abstract interfaces
│   │       ├── __init__.py
│   │       └── repositories.py    # Repository interfaces
│   │
│   └── infrastructure/            # Infrastructure Layer
│       ├── __init__.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py      # DB connection management
│       │   ├── models.py          # SQLAlchemy ORM models
│       │   └── repositories.py    # Repository implementations
│       ├── ml/
│       │   ├── __init__.py
│       │   ├── embeddings.py      # Embedding model loading
│       │   └── nli.py             # NLI model loading
│       ├── config.py              # Configuration management
│       └── logging.py             # structlog setup
│
├── tests/                         # Tests mirror structure
│   ├── unit/
│   │   ├── api/
│   │   ├── domain/
│   │   └── infrastructure/
│   └── integration/
│
├── docker/                        # Docker configuration
│   ├── api.Dockerfile
│   └── init-db.sql
│
├── pyproject.toml                 # Python dependencies (uv)
├── docker-compose.yml
└── README.md
```

### Module Boundaries and Dependencies

**Dependency Flow** (inner layers don't depend on outer layers):

```text
API Layer ──depends on──> Domain Layer ──depends on──> Infrastructure Layer
     │                          │                              │
     │                          │                              │
     ▼                          ▼                              ▼
Request/Response          Business Logic                  External Systems
  Validation              Domain Models                   (DB, ML models)
```

**Key Rules**:

1. **API Layer** depends on Domain Layer (imports domain services and models)
2. **Domain Layer** is independent (only Python standard library + type hints)
3. **Infrastructure Layer** implements domain interfaces (dependency inversion)
4. **No circular dependencies** between layers
5. **Domain models** are separate from database models (ORM mapping in infrastructure)

**Why This Matters**:

- Domain logic can be tested without database or API
- Business rules are portable (can move to different framework/database)
- Clear extraction path: each module can become a service in v1

---

## API Layer Design

### RESTful API Structure

**Base Path**: `/api/v1/` (version prefix for future evolution)

**Endpoints**:

```text
POST   /api/v1/claims                    Create new claim
GET    /api/v1/claims                    List claims (paginated)
GET    /api/v1/claims/{claim_id}         Get claim details
POST   /api/v1/claims/{claim_id}/verify  Trigger verification (Phase 2)

POST   /api/v1/evidence                  Add evidence to corpus
GET    /api/v1/evidence                  List evidence (paginated)
GET    /api/v1/evidence/{evidence_id}    Get evidence details

GET    /api/v1/verdicts/{claim_id}       Get verification results

GET    /api/v1/health                    Health check
```

### Request/Response Patterns

**Consistent Response Structure**:

```json
// Success Response (200, 201)
{
  "data": { ... },          // Actual response payload
  "meta": {                 // Optional metadata
    "timestamp": "2025-01-15T10:30:00Z"
  }
}

// List Response (200)
{
  "data": {
    "items": [...],
    "total": 42,
    "skip": 0,
    "limit": 20
  }
}

// Error Response (4xx, 5xx)
{
  "error": {
    "code": "claim_not_found",
    "message": "Claim with ID abc123 not found",
    "details": {}           // Optional additional context
  }
}
```

### Input Validation Strategy

**Pydantic Models for Validation**:

```python
# api/models/claims.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID

class ClaimCreateRequest(BaseModel):
    """Request model for creating a claim"""
    text: str = Field(..., min_length=10, max_length=5000)
    source_url: Optional[HttpUrl] = None

    class Config:
        json_schema_extra = {
            "example": {
                "text": "The Earth is round",
                "source_url": "https://example.com/article"
            }
        }

class ClaimResponse(BaseModel):
    """Response model for claim data"""
    id: UUID
    text: str
    source_url: Optional[str]
    submitted_at: datetime
    verdict: Optional[VerdictSummary] = None

    class Config:
        from_attributes = True  # Allow ORM model conversion
```

**Validation Benefits**:

- Automatic type checking and conversion
- Clear error messages for invalid input
- Auto-generated OpenAPI/Swagger documentation
- Request/Response examples in docs

### Error Handling Strategy

**Layered Error Handling**:

```python
# api/routes/claims.py
from fastapi import APIRouter, HTTPException, status
from domain.services.claim_service import ClaimService, ClaimNotFoundError

router = APIRouter()

@router.get("/claims/{claim_id}")
async def get_claim(claim_id: str, claim_service: ClaimService = Depends()):
    try:
        claim = claim_service.get_claim(claim_id)
        return {"data": claim}
    except ClaimNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "claim_not_found",
                "message": str(e),
                "details": {"claim_id": claim_id}
            }
        )
    except Exception as e:
        logger.exception("Unexpected error getting claim", claim_id=claim_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_error",
                "message": "An unexpected error occurred"
            }
        )
```

**Error Mapping**:

| Domain Exception | HTTP Status | Error Code |
|-----------------|-------------|------------|
| `NotFoundError` | 404 | `{resource}_not_found` |
| `ValidationError` | 400 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `RateLimitError` | 429 | `rate_limit_exceeded` |
| Generic Exception | 500 | `internal_error` |

### API Versioning Approach

**URL Versioning** (simple, explicit):

- Current: `/api/v1/claims`
- Future: `/api/v2/claims` (breaking changes only)

**Versioning Strategy**:

1. **v1 is stable**: No breaking changes in v0 or v1
2. **Deprecation process**: Announce deprecation 6+ months before removal
3. **Backward compatibility**: New fields are optional, old fields remain
4. **Version in code**: Separate routers for each version

```python
# main.py
app.include_router(v1_router, prefix="/api/v1")
# Future: app.include_router(v2_router, prefix="/api/v2")
```

---

## Domain Layer Design

### Core Business Logic Organization

**Domain Services** (use case orchestration):

```python
# domain/services/verification_service.py
from typing import List
from domain.models.claim import Claim
from domain.models.evidence import Evidence
from domain.models.verdict import Verdict
from domain.interfaces.repositories import EvidenceRepository

class VerificationService:
    """
    Orchestrates the claim verification workflow.
    Pure business logic - no database or HTTP concerns.
    """

    def __init__(self, evidence_repo: EvidenceRepository):
        self.evidence_repo = evidence_repo

    def verify_claim(self, claim: Claim) -> Verdict:
        """
        Verify a claim using available evidence.

        Workflow:
        1. Retrieve relevant evidence (semantic search)
        2. For each evidence, determine support/refute/neutral
        3. Aggregate individual verdicts
        4. Return final verdict with confidence
        """
        # Step 1: Retrieve relevant evidence
        evidence_list = self.evidence_repo.search_similar(
            query=claim.text,
            limit=10
        )

        # Step 2: Evaluate each evidence
        individual_verdicts = []
        for evidence in evidence_list:
            verdict = self._evaluate_evidence(claim, evidence)
            individual_verdicts.append(verdict)

        # Step 3: Aggregate verdicts
        final_verdict = self._aggregate_verdicts(individual_verdicts)

        return final_verdict

    def _evaluate_evidence(self, claim: Claim, evidence: Evidence) -> str:
        """Use NLI model to determine if evidence supports/refutes claim"""
        # NLI logic here (Phase 2)
        pass

    def _aggregate_verdicts(self, verdicts: List[str]) -> Verdict:
        """Simple majority voting for MVP"""
        # Aggregation logic here (Phase 2)
        pass
```

### Domain Models (Entities)

**Pure Python classes** (no ORM, no database concerns):

```python
# domain/models/claim.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class Claim:
    """
    Domain model for a claim to be verified.

    This is the "truth" representation - business rules live here,
    not in database models or API models.
    """
    id: UUID
    text: str
    source_url: Optional[str]
    submitted_at: datetime

    def __post_init__(self):
        """Enforce business rules"""
        if len(self.text) < 10:
            raise ValueError("Claim text must be at least 10 characters")
        if len(self.text) > 5000:
            raise ValueError("Claim text cannot exceed 5000 characters")

    def is_verifiable(self) -> bool:
        """Determine if claim can be fact-checked"""
        # Business logic: check if claim is a factual statement
        # vs opinion, question, or command
        return True  # Simplified for MVP
```

**Separation of Concerns**:

- **Domain models** = business entities (Claim, Evidence, Verdict)
- **ORM models** = database representation (in infrastructure/)
- **API models** = request/response DTOs (in api/models/)

**Why Separate?**

- Domain models can evolve independently of database schema
- Business logic is testable without database
- Clear boundaries make v1 extraction easier

### Verification Workflow

**Synchronous Processing Flow** (acceptable for MVP):

```text
User Request
     │
     ▼
1. API Layer receives POST /claims/{id}/verify
     │
     ▼
2. ClaimService.verify_claim(claim_id)
     │
     ▼
3. VerificationService.verify_claim(claim)
     │
     ├──> 3a. Retrieve similar evidence (EmbeddingsService)
     │
     ├──> 3b. For each evidence:
     │         - Run NLI model (supports/refutes/neutral)
     │         - Record confidence score
     │
     ├──> 3c. Aggregate individual verdicts
     │         - Simple majority voting for MVP
     │         - Calculate aggregate confidence
     │
     └──> 3d. Create Verdict entity
     │
     ▼
4. VerdictRepository.save(verdict)
     │
     ▼
5. API Layer returns VerdictResponse
     │
     ▼
User sees result (JSON response)
```

**Latency Budget** (target <60s for MVP):

| Step | Target Latency | Notes |
|------|---------------|-------|
| Evidence retrieval | <2s | pgvector semantic search |
| NLI inference (10 evidence) | <5s | CPU inference acceptable for MVP |
| Aggregation | <100ms | Simple voting logic |
| Database operations | <1s | CRUD operations |
| **Total** | **<10s** | Comfortable margin for MVP |

**Why Synchronous is OK for MVP**:

- Target <1000 claims/day (avg ~1/min)
- Users expect to wait for results (not fire-and-forget)
- No need for queuing infrastructure (Redis Streams not needed yet)
- Easier debugging (no distributed workflow tracking)
- Can add async in v1 if load increases

### Reasoning and Aggregation Logic

**Simple Aggregation for v0** (no multi-hop reasoning):

```python
# domain/services/verification_service.py

def _aggregate_verdicts(self, individual_verdicts: List[EvidenceVerdict]) -> Verdict:
    """
    Aggregate individual evidence verdicts into final verdict.

    MVP Strategy: Simple majority voting
    - Count SUPPORTS vs REFUTES vs NEUTRAL
    - Final verdict = majority
    - Confidence = (majority_count / total_count)

    Phase 2: More sophisticated aggregation
    - Weight by evidence quality/recency
    - Multi-hop reasoning chains
    """
    supports = sum(1 for v in individual_verdicts if v.verdict == "SUPPORTS")
    refutes = sum(1 for v in individual_verdicts if v.verdict == "REFUTES")
    neutral = sum(1 for v in individual_verdicts if v.verdict == "NEUTRAL")

    total = len(individual_verdicts)

    if supports > refutes and supports > neutral:
        final_verdict = "SUPPORTED"
        confidence = supports / total
    elif refutes > supports and refutes > neutral:
        final_verdict = "REFUTED"
        confidence = refutes / total
    else:
        final_verdict = "INSUFFICIENT"
        confidence = max(supports, refutes, neutral) / total

    return Verdict(
        verdict=final_verdict,
        confidence=confidence,
        supporting_evidence=[v for v in individual_verdicts if v.verdict == "SUPPORTS"],
        refuting_evidence=[v for v in individual_verdicts if v.verdict == "REFUTES"],
        reasoning=self._generate_reasoning_text(individual_verdicts)
    )
```

**Future Enhancement Path (v1)**:

- Multi-hop reasoning (chain evidence)
- Weighted aggregation (evidence quality, recency)
- Contradiction detection (conflicting evidence)
- Temporal reasoning (claims that change over time)

### Domain Independence

**Key Principle**: Domain layer has zero dependencies on infrastructure.

```python
# ✅ GOOD - Domain depends on abstractions
from domain.interfaces.repositories import EvidenceRepository

class VerificationService:
    def __init__(self, evidence_repo: EvidenceRepository):
        self.evidence_repo = evidence_repo

# ❌ BAD - Domain depends on concrete infrastructure
from infrastructure.database.repositories import SQLAlchemyEvidenceRepository

class VerificationService:
    def __init__(self, evidence_repo: SQLAlchemyEvidenceRepository):
        self.evidence_repo = evidence_repo
```

**Benefits**:

- Domain logic testable with mock repositories
- Can swap PostgreSQL → MongoDB without changing domain
- Business rules are portable across implementations

---

## Infrastructure Layer Design

### Repository Pattern for Data Access

**Abstract Interface** (in domain layer):

```python
# domain/interfaces/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from domain.models.claim import Claim
from domain.models.evidence import Evidence

class ClaimRepository(ABC):
    """Abstract interface for claim persistence"""

    @abstractmethod
    def create(self, claim: Claim) -> Claim:
        """Create a new claim"""
        pass

    @abstractmethod
    def get_by_id(self, claim_id: UUID) -> Optional[Claim]:
        """Retrieve claim by ID"""
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 20) -> List[Claim]:
        """List claims with pagination"""
        pass

class EvidenceRepository(ABC):
    """Abstract interface for evidence persistence"""

    @abstractmethod
    def search_similar(self, query: str, limit: int = 10) -> List[Evidence]:
        """Search for similar evidence using embeddings"""
        pass
```

**Concrete Implementation** (in infrastructure layer):

```python
# infrastructure/database/repositories.py
from sqlalchemy.orm import Session
from domain.interfaces.repositories import ClaimRepository
from domain.models.claim import Claim
from infrastructure.database.models import ClaimORM

class SQLAlchemyClaimRepository(ClaimRepository):
    """SQLAlchemy implementation of ClaimRepository"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, claim: Claim) -> Claim:
        """Create claim in PostgreSQL"""
        db_claim = ClaimORM(
            id=claim.id,
            text=claim.text,
            source_url=claim.source_url,
            submitted_at=claim.submitted_at
        )
        self.session.add(db_claim)
        self.session.commit()
        self.session.refresh(db_claim)

        # Convert ORM model back to domain model
        return self._to_domain(db_claim)

    def get_by_id(self, claim_id: UUID) -> Optional[Claim]:
        """Retrieve claim from PostgreSQL"""
        db_claim = self.session.query(ClaimORM).filter(
            ClaimORM.id == claim_id
        ).first()

        return self._to_domain(db_claim) if db_claim else None

    def _to_domain(self, db_claim: ClaimORM) -> Claim:
        """Convert ORM model to domain model"""
        return Claim(
            id=db_claim.id,
            text=db_claim.text,
            source_url=db_claim.source_url,
            submitted_at=db_claim.submitted_at
        )
```

**Why Repository Pattern?**

- **Testability**: Mock repositories in unit tests (no database needed)
- **Flexibility**: Swap PostgreSQL → MongoDB by changing one file
- **Separation**: Domain logic doesn't know about SQLAlchemy
- **v1 extraction**: Repository becomes a REST API client when services split

### Database Connection Management

**Connection Pool Configuration**:

```python
# infrastructure/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

class DatabaseConnection:
    """Manages database connection and session lifecycle"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://truthgraph:password@localhost:5432/truthgraph"
        )

        # Connection pool configuration
        self.engine = create_engine(
            self.database_url,
            pool_size=10,           # Max 10 connections in pool
            max_overflow=20,        # Allow 20 additional connections
            pool_timeout=30,        # 30s wait for available connection
            pool_pre_ping=True,     # Verify connections before use
            echo=False              # Don't log SQL (use structlog instead)
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    @contextmanager
    def get_session(self) -> Session:
        """Provide a transactional scope around a series of operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Singleton instance
db_connection = DatabaseConnection()

# FastAPI dependency
def get_db() -> Session:
    """Dependency for FastAPI routes"""
    with db_connection.get_session() as session:
        yield session
```

**Connection Pool Benefits**:

- Reuse connections (avoid overhead of creating new connections)
- Limit concurrent connections (protect database)
- Automatic recovery from connection failures (`pool_pre_ping`)

### ML Model Loading and Caching

**Model Loader Pattern**:

```python
# infrastructure/ml/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingModel:
    """
    Manages embedding model lifecycle.

    - Loads model once on initialization
    - Caches in memory for subsequent calls
    - Thread-safe for concurrent requests
    """

    _instance = None  # Singleton pattern

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Load model once"""
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_dim = 384
        logger.info("Embedding model loaded successfully")

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for text.

        Args:
            texts: List of strings to embed

        Returns:
            np.ndarray: Shape (len(texts), 384)
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string"""
        return self.embed([query])[0]

# Global instance (loaded once on import)
embedding_model = EmbeddingModel()
```

**Model Caching Strategy**:

- **Singleton pattern**: Model loaded once per process
- **In-memory cache**: No disk I/O after initial load
- **Lazy loading**: Model loads on first request (not app startup)
- **Thread-safe**: Multiple requests can use same model instance

**Memory Considerations**:

| Model | Size on Disk | RAM Usage | Inference Speed (CPU) |
|-------|-------------|-----------|---------------------|
| all-MiniLM-L6-v2 | ~90MB | ~200MB | ~50 sentences/sec |
| DeBERTa-v3-base (NLI) | ~550MB | ~1GB | ~10 pairs/sec |

Total RAM: ~1.5GB for ML models + ~500MB for FastAPI = **~2GB target**

### Configuration Management

**Environment-Based Configuration**:

```python
# infrastructure/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application configuration.

    Loaded from environment variables or .env file.
    Validated with Pydantic.
    """

    # Database
    database_url: str = "postgresql://truthgraph:password@localhost:5432/truthgraph"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # or "console" for development

    # ML Models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nli_model: str = "microsoft/deberta-v3-base"

    # Verification
    evidence_retrieval_limit: int = 10
    verification_timeout: int = 60  # seconds

    # Feature Flags (for gradual rollout)
    enable_verification: bool = False  # Phase 1: False, Phase 2: True
    enable_embeddings: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton instance
settings = Settings()
```

**Usage in Code**:

```python
from infrastructure.config import settings

# Use settings anywhere
logger.setLevel(settings.log_level)
model = SentenceTransformer(settings.embedding_model)
```

**Benefits**:

- No hardcoded values (12-factor app principle)
- Type-safe configuration (Pydantic validation)
- Easy to test (override settings in tests)
- Clear documentation (all config in one place)

### Logging Infrastructure

**Structured Logging with structlog**:

```python
# infrastructure/logging.py
import structlog
import logging
from infrastructure.config import settings

def setup_logging():
    """
    Configure structlog for structured logging.

    Output format depends on environment:
    - Development: Human-readable console output
    - Production: JSON for log aggregation
    """

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add console or JSON renderer based on config
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure Python logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )

# Usage in code
import structlog
logger = structlog.get_logger(__name__)

logger.info("claim_created", claim_id="abc123", text="Earth is round")
# Output: {"event": "claim_created", "claim_id": "abc123", "text": "Earth is round", ...}
```

**Logging Best Practices**:

- **Structured fields**: Log data as key-value pairs (not string formatting)
- **Correlation IDs**: Add request_id to all logs for tracing
- **Log levels**: DEBUG (dev), INFO (normal), WARNING (degraded), ERROR (failure)
- **No PII**: Never log passwords, tokens, or sensitive data
- **Performance**: Avoid logging in tight loops (use sampling)

---

## Synchronous Processing Flow

### Request-to-Response Flow

**Detailed Sequence Diagram**:

```text
User → React Frontend → FastAPI → Domain Service → Repository → Database

1. User submits claim via UI
       │
       ▼
2. React POSTs to /api/v1/claims/{id}/verify
       │
       ▼
3. FastAPI route handler (api/routes/claims.py)
   - Validates request
   - Extracts claim_id
       │
       ▼
4. Injects ClaimService via FastAPI depends
       │
       ▼
5. ClaimService.verify_claim(claim_id)
   - Retrieves claim from repository
   - Calls VerificationService
       │
       ▼
6. VerificationService.verify_claim(claim)
   ┌─────────────────────────────────────────┐
   │ 6a. EvidenceRepository.search_similar() │
   │     - Generate embedding for claim      │
   │     - Query pgvector for similar docs   │
   │     - Return top 10 evidence            │
   │     (Target: <2s)                       │
   └─────────────────────────────────────────┘
       │
       ▼
   ┌─────────────────────────────────────────┐
   │ 6b. For each evidence:                  │
   │     - Run NLI model (claim, evidence)   │
   │     - Output: SUPPORTS/REFUTES/NEUTRAL  │
   │     - Record confidence score           │
   │     (Target: <5s for 10 evidence)       │
   └─────────────────────────────────────────┘
       │
       ▼
   ┌─────────────────────────────────────────┐
   │ 6c. Aggregate individual verdicts       │
   │     - Count supports/refutes/neutral    │
   │     - Calculate final verdict           │
   │     - Generate reasoning text           │
   │     (Target: <100ms)                    │
   └─────────────────────────────────────────┘
       │
       ▼
7. VerdictRepository.save(verdict)
   - Insert into verdicts table
   - Link verdict to evidence
       │
       ▼
8. Return VerdictResponse to API layer
       │
       ▼
9. FastAPI returns JSON response
       │
       ▼
10. React displays results to user

Total latency: ~8-10s (well under 60s budget)
```

### Why Synchronous is Acceptable for MVP

**Performance Analysis**:

| Scenario | Claims/Day | Peak Concurrent | Avg Response Time | Max Wait Time |
|----------|-----------|----------------|------------------|---------------|
| Single user | 10-50 | 1 | 10s | 10s |
| Small team (5 users) | 100-500 | 5 | 10s | 50s |
| **MVP Target** | **<1000** | **<10** | **<15s** | **<60s** |

**Why This Works**:

1. **Low concurrency**: <10 concurrent requests (no queueing needed)
2. **User expectations**: Users expect to wait for verification results
3. **Simple debugging**: Stack traces show full request path
4. **No infrastructure overhead**: No Redis, no workers, no event tracking

**When to Add Async** (v1 considerations):

- Concurrent requests > 50
- Response time > 60s
- Background processing needed (bulk imports)
- Multiple long-running steps (multi-hop reasoning)

### Error Handling and Timeouts

**Timeout Configuration**:

```python
# api/routes/claims.py
from fastapi import APIRouter, HTTPException, status
import asyncio

@router.post("/claims/{claim_id}/verify", response_model=VerdictResponse)
async def verify_claim(
    claim_id: str,
    claim_service: ClaimService = Depends(),
    timeout: int = 60  # 60 second timeout
):
    """
    Verify a claim (synchronous processing).

    Returns 202 if verification starts successfully.
    Returns 200 when verification completes.
    Returns 408 if timeout is exceeded.
    """
    try:
        # Wrap sync call in asyncio timeout
        verdict = await asyncio.wait_for(
            asyncio.to_thread(claim_service.verify_claim, claim_id),
            timeout=timeout
        )
        return {"data": verdict}

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "code": "verification_timeout",
                "message": f"Verification exceeded {timeout}s timeout",
                "details": {"claim_id": claim_id}
            }
        )
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="Claim not found")
    except Exception as e:
        logger.exception("Verification failed", claim_id=claim_id)
        raise HTTPException(status_code=500, detail="Verification failed")
```

**Error Recovery Strategy**:

| Error Type | Recovery Action | User Experience |
|-----------|----------------|-----------------|
| Timeout (>60s) | Return 408, log for investigation | "Verification took too long, please try again" |
| Model load failure | Return 503, retry on next request | "System initializing, please wait" |
| Database connection | Return 503, reconnect automatically | "Temporary database issue" |
| Validation error | Return 400, clear error message | "Invalid input: claim text too short" |

### Future: How to Add Async Processing

**When MVP needs async** (v1 upgrade path):

1. **Add Redis Streams** to docker-compose.yml
2. **Create VerificationWorker** service (separate container)
3. **Modify API endpoint**:
   ```python
   # POST /claims/{id}/verify returns 202 Accepted immediately
   @router.post("/claims/{claim_id}/verify", status_code=202)
   def verify_claim(claim_id: str):
       # Publish event to Redis Stream
       event = {"type": "verification.requested", "claim_id": claim_id}
       redis_client.xadd("verification-stream", event)
       return {"status": "queued", "claim_id": claim_id}

   # GET /claims/{id}/verdict polls for results
   @router.get("/claims/{claim_id}/verdict")
   def get_verdict(claim_id: str):
       verdict = verdict_repo.get_by_claim_id(claim_id)
       if not verdict:
           return {"status": "processing"}
       return {"status": "complete", "data": verdict}
   ```
4. **Worker consumes events**:
   ```python
   # worker.py
   while True:
       events = redis_client.xread({"verification-stream": last_id})
       for event in events:
           claim_id = event["claim_id"]
           verdict = verification_service.verify_claim(claim_id)
           verdict_repo.save(verdict)
   ```

**Migration effort**: ~2-3 days (add Redis, create worker, update API)

---

## Code Organization Deep Dive

### Directory Structure Rationale

**Principle**: Organize by layer and feature, not by technical role.

```text
backend/
├── truthgraph/                    # Single Python package (modular monolith)
│   │
│   ├── api/                       # HTTP interface (adapts to web)
│   │   ├── routes/                # Grouped by resource (not one big routes.py)
│   │   │   ├── claims.py          # All claim endpoints
│   │   │   ├── evidence.py        # All evidence endpoints
│   │   │   └── verdicts.py        # All verdict endpoints
│   │   ├── models/                # Request/Response DTOs
│   │   │   ├── claims.py          # ClaimCreateRequest, ClaimResponse
│   │   │   ├── evidence.py
│   │   │   └── verdicts.py
│   │   └── dependencies.py        # FastAPI dependency injection setup
│   │
│   ├── domain/                    # Business logic (framework-independent)
│   │   ├── models/                # Domain entities (pure Python)
│   │   │   ├── claim.py           # Claim dataclass
│   │   │   ├── evidence.py
│   │   │   └── verdict.py
│   │   ├── services/              # Use case orchestration
│   │   │   ├── claim_service.py   # Claim CRUD logic
│   │   │   ├── evidence_service.py
│   │   │   └── verification_service.py  # Core verification logic
│   │   └── interfaces/            # Abstract interfaces (dependency inversion)
│   │       └── repositories.py    # Repository contracts
│   │
│   └── infrastructure/            # External system integrations
│       ├── database/
│       │   ├── connection.py      # SQLAlchemy engine, session management
│       │   ├── models.py          # ORM models (SQLAlchemy)
│       │   └── repositories.py    # Repository implementations
│       ├── ml/
│       │   ├── embeddings.py      # SentenceTransformer wrapper
│       │   └── nli.py             # DeBERTa NLI wrapper
│       ├── config.py              # Pydantic settings
│       └── logging.py             # structlog setup
```

**Why This Structure?**

| Decision | Rationale | v1 Benefit |
|----------|-----------|-----------|
| Separate api/domain/infrastructure | Clear boundaries, testable layers | Each layer → microservice |
| Group routes by resource | Easier to find related endpoints | Claim routes → Claim service |
| Domain models ≠ ORM models | Domain logic independent of database | Portable business rules |
| Interfaces in domain/ | Dependency inversion principle | Mock repositories in tests |

### Package Dependencies

**Allowed dependency directions**:

```text
api/ ──────> domain/ ──────> infrastructure/
             (imports)        (implements interfaces)

api/         ← Can import from domain/
domain/      ← Cannot import from api/ or infrastructure/
infrastructure/ ← Can import from domain/ (interfaces only)
```

**Enforced with import checks**:

```python
# pyproject.toml (future: add import linter)
[tool.import-linter]
root_packages = ["truthgraph"]

[[tool.import-linter.contracts]]
name = "Domain independence"
type = "forbidden"
source_modules = ["truthgraph.domain"]
forbidden_modules = ["truthgraph.api", "truthgraph.infrastructure"]
```

### Module Extraction Examples

**Current (v0)**: Monolith

```python
# api/routes/claims.py
from domain.services.claim_service import ClaimService
from domain.services.verification_service import VerificationService

@router.post("/claims/{claim_id}/verify")
def verify_claim(claim_id: str):
    claim = claim_service.get_claim(claim_id)
    verdict = verification_service.verify_claim(claim)  # Direct function call
    return verdict
```

**Future (v1)**: Microservices

```python
# api-gateway/routes/claims.py
import httpx

@router.post("/claims/{claim_id}/verify")
async def verify_claim(claim_id: str):
    # Call Verification Service via HTTP
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VERIFICATION_SERVICE_URL}/verify",
            json={"claim_id": claim_id}
        )
        verdict = response.json()
    return verdict
```

**Migration effort**: Replace function call with HTTP client (~1 line change)

---

## Design Patterns

### Repository Pattern (Data Access Abstraction)

**Pattern**: Separate persistence logic from business logic using abstract interfaces.

**Implementation**:

```python
# Step 1: Define interface in domain layer
from abc import ABC, abstractmethod

class ClaimRepository(ABC):
    @abstractmethod
    def create(self, claim: Claim) -> Claim:
        pass

# Step 2: Implement in infrastructure layer
class SQLAlchemyClaimRepository(ClaimRepository):
    def create(self, claim: Claim) -> Claim:
        # SQLAlchemy-specific code
        pass

# Step 3: Use interface in domain services
class ClaimService:
    def __init__(self, repo: ClaimRepository):  # Depend on interface, not implementation
        self.repo = repo

# Step 4: Inject implementation at runtime
claim_service = ClaimService(repo=SQLAlchemyClaimRepository(session))
```

**Benefits**:

- Test ClaimService with mock repository (no database)
- Swap PostgreSQL → MongoDB by implementing new repository
- Domain layer has zero database dependencies

**v1 Evolution**: Repository interface stays same, implementation becomes HTTP client.

### Dependency Injection (FastAPI Depends)

**Pattern**: Inject dependencies at runtime instead of hardcoding in constructors.

**Implementation**:

```python
# api/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from infrastructure.database.connection import get_db
from infrastructure.database.repositories import SQLAlchemyClaimRepository
from domain.services.claim_service import ClaimService

def get_claim_repository(db: Session = Depends(get_db)) -> ClaimRepository:
    """Factory function for claim repository"""
    return SQLAlchemyClaimRepository(db)

def get_claim_service(repo: ClaimRepository = Depends(get_claim_repository)) -> ClaimService:
    """Factory function for claim service"""
    return ClaimService(repo)

# api/routes/claims.py
@router.post("/claims")
def create_claim(
    request: ClaimCreateRequest,
    service: ClaimService = Depends(get_claim_service)  # Injected automatically
):
    claim = service.create_claim(request.text, request.source_url)
    return claim
```

**Benefits**:

- Easy to test (override dependencies in tests)
- Clear dependency graph (explicit in function signature)
- Single Responsibility (routes don't create services)

**Testing with DI**:

```python
# tests/test_api.py
from fastapi.testclient import TestClient

def test_create_claim():
    # Override dependency with mock
    def mock_claim_service():
        return MockClaimService()

    app.dependency_overrides[get_claim_service] = mock_claim_service

    client = TestClient(app)
    response = client.post("/api/v1/claims", json={"text": "Test"})
    assert response.status_code == 201
```

### Configuration Pattern (Environment-Based Settings)

**Pattern**: Externalize configuration, validate with Pydantic.

**Implementation**:

```python
# infrastructure/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()  # Loads from environment or .env

# Usage
from infrastructure.config import settings
print(settings.database_url)  # Never hardcoded!
```

**Benefits**:

- 12-factor app compliance (config in environment)
- Type-safe (Pydantic validation)
- Easy to test (override settings in tests)
- Clear documentation (all config in one place)

### Service Layer Pattern (Business Logic Orchestration)

**Pattern**: Separate business logic from API and persistence.

**Implementation**:

```python
# domain/services/claim_service.py
class ClaimService:
    """
    Orchestrates claim-related operations.

    Responsibilities:
    - Validate business rules
    - Coordinate repository calls
    - Handle errors and logging
    """

    def __init__(self, claim_repo: ClaimRepository, verdict_repo: VerdictRepository):
        self.claim_repo = claim_repo
        self.verdict_repo = verdict_repo

    def create_claim(self, text: str, source_url: Optional[str] = None) -> Claim:
        """Create a new claim (business logic)"""
        # Business rule: Check for duplicate claims
        existing = self.claim_repo.find_by_text(text)
        if existing:
            raise DuplicateClaimError(f"Claim already exists: {existing.id}")

        # Create domain model
        claim = Claim(
            id=uuid4(),
            text=text,
            source_url=source_url,
            submitted_at=datetime.utcnow()
        )

        # Persist via repository
        return self.claim_repo.create(claim)
```

**Why Not Put Logic in API Routes?**

```python
# ❌ BAD - Business logic in API layer
@router.post("/claims")
def create_claim(request: ClaimCreateRequest, db: Session = Depends(get_db)):
    # Business logic mixed with HTTP concerns
    existing = db.query(Claim).filter(Claim.text == request.text).first()
    if existing:
        raise HTTPException(400, "Duplicate claim")
    claim = Claim(...)
    db.add(claim)
    db.commit()
    return claim

# ✅ GOOD - Business logic in service layer
@router.post("/claims")
def create_claim(request: ClaimCreateRequest, service: ClaimService = Depends()):
    try:
        claim = service.create_claim(request.text, request.source_url)
        return claim
    except DuplicateClaimError as e:
        raise HTTPException(400, str(e))
```

**Benefits**:

- Testable without HTTP (test ClaimService directly)
- Reusable (CLI, API, background jobs use same service)
- Single place for business rules

---

## Evolution to v1 Microservices

### Service Extraction Strategy

**v0 Monolith → v1 Microservices Migration**:

```text
┌─────────────────────────────────────┐
│       v0 FastAPI Monolith           │
│  ┌─────────┐  ┌─────────┐          │       ┌────────────────────────┐
│  │   API   │  │ Domain  │          │       │   v1 API Gateway       │
│  │  Layer  │→ │ Services│          │       │  (FastAPI)             │
│  └─────────┘  └────┬────┘          │       └──────┬─────────────────┘
│                    │                │              │
│  ┌─────────────────▼──────────┐    │       ┌──────▼──────────────────┐
│  │  Infrastructure Layer      │    │  ══>  │  Verification Service   │
│  │  • Repositories            │    │       │  (FastAPI)              │
│  │  • ML Models               │    │       └─────────────────────────┘
│  │  • Database                │    │              │
│  └────────────────────────────┘    │       ┌──────▼──────────────────┐
│                                     │       │  Corpus Service         │
└─────────────────────────────────────┘       │  (FastAPI)              │
                                              └─────────────────────────┘
                                                     │
                                              ┌──────▼──────────────────┐
                                              │  Worker Service         │
                                              │  (Background jobs)      │
                                              └─────────────────────────┘
```

### Module → Service Mapping

**Extraction Plan**:

| v0 Module | v1 Service | Responsibilities | Data Ownership |
|-----------|------------|-----------------|----------------|
| `api/routes/` | **API Gateway** | Request routing, authentication, rate limiting | None (stateless) |
| `domain/services/verification_service.py` | **Verification Service** | NLI inference, verdict aggregation | Verdicts table |
| `domain/services/evidence_service.py` | **Corpus Service** | Evidence storage, semantic search | Evidence table, embeddings |
| Background jobs (future) | **Worker Service** | Async processing, batch imports | Job queue |
| `infrastructure/database/` | Stays in each service | Database access (each service has own DB) | Service-specific tables |

### API Gateway Extraction

**Current (v0)**: All routes in monolith

```python
# api/routes/claims.py
@router.post("/claims/{claim_id}/verify")
def verify_claim(claim_id: str, service: VerificationService = Depends()):
    verdict = service.verify_claim(claim_id)  # Local function call
    return verdict
```

**Future (v1)**: API Gateway routes to services

```python
# api-gateway/routes/claims.py
import httpx

VERIFICATION_SERVICE = os.getenv("VERIFICATION_SERVICE_URL", "http://verification:8001")

@router.post("/claims/{claim_id}/verify")
async def verify_claim(claim_id: str):
    # Route to Verification Service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VERIFICATION_SERVICE}/verify",
            json={"claim_id": claim_id},
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
```

**Migration Steps**:

1. Create new FastAPI app for API Gateway
2. Copy routing logic from `api/routes/`
3. Replace service calls with HTTP clients
4. Add service discovery (environment variables or Consul)
5. Deploy alongside monolith (gradual migration)

### Verification Service Extraction

**Current (v0)**: Domain service in monolith

```python
# domain/services/verification_service.py
class VerificationService:
    def verify_claim(self, claim: Claim) -> Verdict:
        evidence = self.evidence_repo.search_similar(claim.text)
        verdicts = [self._evaluate_evidence(claim, e) for e in evidence]
        return self._aggregate_verdicts(verdicts)
```

**Future (v1)**: Standalone FastAPI service

```python
# verification-service/main.py
app = FastAPI()

@app.post("/verify")
def verify_claim(request: VerifyClaimRequest):
    # Same logic as v0 VerificationService.verify_claim()
    claim = claim_repo.get_by_id(request.claim_id)
    evidence = corpus_service_client.search_similar(claim.text)  # HTTP call to Corpus Service
    verdicts = [evaluate_evidence(claim, e) for e in evidence]
    return aggregate_verdicts(verdicts)
```

**Migration Steps**:

1. Create new FastAPI app for Verification Service
2. Copy `domain/services/verification_service.py` logic
3. Replace `evidence_repo` with HTTP client to Corpus Service
4. Expose `/verify` endpoint
5. Update API Gateway to route to new service

### Corpus Service Extraction

**Current (v0)**: Evidence repository in monolith

```python
# infrastructure/database/repositories.py
class EvidenceRepository:
    def search_similar(self, query: str, limit: int) -> List[Evidence]:
        embedding = embedding_model.embed_query(query)
        results = db.query(...).filter(...)  # pgvector search
        return results
```

**Future (v1)**: Standalone service with dedicated database

```python
# corpus-service/main.py
app = FastAPI()

@app.post("/search")
def search_similar(request: SearchRequest):
    embedding = embedding_model.embed_query(request.query)
    results = evidence_repo.search_by_embedding(embedding, request.limit)
    return {"results": results}

@app.post("/evidence")
def add_evidence(request: AddEvidenceRequest):
    evidence = Evidence(...)
    evidence_repo.create(evidence)
    return {"id": evidence.id}
```

**Migration Steps**:

1. Create new FastAPI app for Corpus Service
2. Copy evidence-related logic
3. Create dedicated `evidence` database (or shared DB with service ownership)
4. Expose `/search` and `/evidence` endpoints
5. Update Verification Service to call Corpus Service

### Worker Service Extraction

**Future (v1)**: Async background processing

```python
# worker-service/main.py
import redis
from redis.streams import StreamReader

redis_client = redis.Redis(...)

def process_verification_event(event: dict):
    claim_id = event["claim_id"]
    # Call Verification Service
    response = httpx.post(f"{VERIFICATION_SERVICE}/verify", json={"claim_id": claim_id})
    # Store result
    verdict_repo.save(response.json())

# Worker loop
reader = StreamReader(redis_client, "verification-stream")
for event in reader.read():
    process_verification_event(event)
```

**When to Add Workers** (v1 decision point):

- Async processing needed (fire-and-forget)
- Long-running tasks (>60s)
- Batch operations (import 1000s of evidence)
- Scheduled jobs (periodic re-verification)

### Database Strategy: Shared vs Dedicated

**v0**: Single PostgreSQL database (all tables)

```sql
-- Single database: truthgraph
CREATE TABLE claims (...);
CREATE TABLE evidence (...);
CREATE TABLE verdicts (...);
```

**v1 Option 1**: Shared database with service ownership

```sql
-- Same database, but each service owns specific tables
-- API Gateway: No tables (stateless)
-- Verification Service: verdicts, verdict_evidence
-- Corpus Service: evidence
-- All services: claims (read-only for Verification/Corpus)
```

**v1 Option 2**: Dedicated databases per service

```sql
-- verification-db
CREATE TABLE verdicts (...);
CREATE TABLE verdict_evidence (...);

-- corpus-db
CREATE TABLE evidence (...);

-- Note: Claims might be duplicated or accessed via API
```

**Recommendation for v1**: Start with **shared database** (easier migration), move to dedicated databases if services need independent scaling.

### What Stays the Same

**Unchanged in v1**:

- Domain models (Claim, Evidence, Verdict entities)
- Business logic (verification algorithm, aggregation)
- Database schema (same tables, maybe reorganized)
- ML models (same embedding/NLI models)
- API contracts (same request/response formats)

**Why This Matters**:

- Frontend doesn't need changes (same API)
- Business logic is reused (not rewritten)
- Data is migrated (not recreated)
- Tests mostly reusable (update mocks to HTTP clients)

### What Changes in v1

**New in v1**:

| Aspect | v0 Monolith | v1 Microservices |
|--------|------------|------------------|
| **Deployment** | Single container | 4+ containers (gateway, verification, corpus, worker) |
| **Communication** | Function calls | HTTP + Redis Streams |
| **Observability** | Single app logs | Distributed tracing, correlation IDs |
| **Testing** | Unit + integration | + Contract testing, service mocking |
| **Scaling** | Vertical (bigger instance) | Horizontal (more replicas) |
| **Deployment** | Deploy all at once | Independent service deployments |
| **Failures** | One crash = all down | Circuit breakers, graceful degradation |

**Migration Complexity**:

- Low complexity: Repository → HTTP client (mostly mechanical)
- Medium complexity: Add service discovery, distributed tracing
- High complexity: Handle distributed transactions (sagas), eventual consistency

**Estimated Migration Effort**: 2-3 weeks (assuming v0 has clean module boundaries)

---

## Practical Implementation Guidance

### Getting Started Checklist

**Phase 1: Foundation**

- [ ] Set up project structure (`api/`, `domain/`, `infrastructure/`)
- [ ] Configure Docker Compose (PostgreSQL, FastAPI, React)
- [ ] Implement database connection management
- [ ] Create SQLAlchemy ORM models
- [ ] Implement repository pattern for Claims
- [ ] Create ClaimService (domain layer)
- [ ] Implement Claims API routes (POST, GET)
- [ ] Set up structlog logging
- [ ] Write unit tests for ClaimService
- [ ] Write integration tests for API endpoints

**Phase 2: Core Features**

- [ ] Add Evidence ORM model and repository
- [ ] Implement EmbeddingModel loader (singleton pattern)
- [ ] Add pgvector similarity search to EvidenceRepository
- [ ] Create VerificationService (domain layer)
- [ ] Implement NLI model loader
- [ ] Implement verification workflow (retrieve → evaluate → aggregate)
- [ ] Add `/claims/{id}/verify` endpoint
- [ ] Add `/verdicts/{claim_id}` endpoint
- [ ] Write tests for VerificationService
- [ ] Optimize embedding/NLI performance

### Development Workflow

**Daily Development Loop**:

```bash
# 1. Start local environment
docker-compose up -d

# 2. Make code changes (hot-reload enabled)
# Edit files in truthgraph/

# 3. Run tests
docker-compose exec api pytest tests/

# 4. Check logs
docker-compose logs -f api

# 5. Test API manually
curl http://localhost:8000/api/v1/claims

# 6. Stop environment
docker-compose down
```

### Testing Strategy

**Test Pyramid**:

```text
              ▲
             ╱│╲
            ╱ │ ╲
           ╱  │  ╲   10% - E2E Tests (full workflow)
          ╱───│───╲
         ╱    │    ╲
        ╱     │     ╲  30% - Integration Tests (API + DB)
       ╱──────│──────╲
      ╱       │       ╲
     ╱        │        ╲
    ╱─────────│─────────╲  60% - Unit Tests (domain logic)
   ╱                     ╲
```

**Unit Tests** (domain layer):

```python
# tests/unit/domain/test_verification_service.py
def test_aggregate_verdicts_majority_supports():
    service = VerificationService(mock_evidence_repo)
    verdicts = [
        EvidenceVerdict(verdict="SUPPORTS", confidence=0.9),
        EvidenceVerdict(verdict="SUPPORTS", confidence=0.8),
        EvidenceVerdict(verdict="REFUTES", confidence=0.6),
    ]
    result = service._aggregate_verdicts(verdicts)
    assert result.verdict == "SUPPORTED"
    assert result.confidence == 2/3
```

**Integration Tests** (API + database):

```python
# tests/integration/test_claims_api.py
from fastapi.testclient import TestClient

def test_create_and_retrieve_claim(client: TestClient, db: Session):
    # Create claim
    response = client.post("/api/v1/claims", json={
        "text": "Test claim",
        "source_url": "https://example.com"
    })
    assert response.status_code == 201
    claim_id = response.json()["data"]["id"]

    # Retrieve claim
    response = client.get(f"/api/v1/claims/{claim_id}")
    assert response.status_code == 200
    assert response.json()["data"]["text"] == "Test claim"
```

**E2E Tests** (full workflow):

```python
# tests/e2e/test_verification_workflow.py
def test_full_verification_workflow(client: TestClient):
    # 1. Add evidence
    client.post("/api/v1/evidence", json={"content": "Earth is round..."})

    # 2. Create claim
    response = client.post("/api/v1/claims", json={"text": "Earth is flat"})
    claim_id = response.json()["data"]["id"]

    # 3. Trigger verification
    response = client.post(f"/api/v1/claims/{claim_id}/verify")
    assert response.status_code == 200

    # 4. Check verdict
    verdict = response.json()["data"]
    assert verdict["verdict"] == "REFUTED"
```

### Code Quality Guidelines

**Linting and Formatting**:

```bash
# Format code
ruff format truthgraph/

# Check linting
ruff check truthgraph/

# Type checking
mypy truthgraph/
```

**Code Review Checklist**:

- [ ] Domain logic is in domain layer (not API or infrastructure)
- [ ] No hardcoded values (use config)
- [ ] Proper error handling (domain exceptions → HTTP errors)
- [ ] Structured logging with context (no print statements)
- [ ] Type hints on all functions
- [ ] Docstrings on public functions
- [ ] Unit tests cover business logic
- [ ] No circular imports between layers

### Common Pitfalls to Avoid

**Pitfall 1**: Mixing layers

```python
# ❌ BAD - Domain service depends on FastAPI
from fastapi import HTTPException

class ClaimService:
    def create_claim(self, text: str):
        if not text:
            raise HTTPException(400, "Text required")  # Domain shouldn't know HTTP

# ✅ GOOD - Domain raises domain exception
class ClaimService:
    def create_claim(self, text: str):
        if not text:
            raise ValidationError("Text required")  # API layer converts to HTTP error
```

**Pitfall 2**: Anemic domain models

```python
# ❌ BAD - Domain model is just data (no behavior)
@dataclass
class Claim:
    text: str

# Service has all the logic
class ClaimService:
    def is_verifiable(self, claim: Claim) -> bool:
        return len(claim.text) > 10  # Logic should be in domain model

# ✅ GOOD - Domain model has behavior
@dataclass
class Claim:
    text: str

    def is_verifiable(self) -> bool:
        return len(self.text) > 10  # Logic lives with data
```

**Pitfall 3**: Repository leakage

```python
# ❌ BAD - Exposing ORM models outside infrastructure
class ClaimRepository:
    def get_by_id(self, claim_id: str) -> ClaimORM:  # Returns ORM model
        return db.query(ClaimORM).filter(...).first()

# ✅ GOOD - Return domain models
class ClaimRepository:
    def get_by_id(self, claim_id: str) -> Claim:  # Returns domain model
        db_claim = db.query(ClaimORM).filter(...).first()
        return self._to_domain(db_claim)  # Convert ORM → domain
```

### Performance Optimization Tips

**Database Query Optimization**:

```python
# Avoid N+1 queries
# ❌ BAD
claims = claim_repo.list()
for claim in claims:
    verdict = verdict_repo.get_by_claim_id(claim.id)  # N queries

# ✅ GOOD
claims = claim_repo.list_with_verdicts()  # 1 query with join
```

**Model Loading Optimization**:

```python
# Lazy load models
# ❌ BAD - Load on app startup (blocks startup)
app = FastAPI()
embedding_model = EmbeddingModel()  # Loaded immediately

# ✅ GOOD - Load on first request (fast startup)
app = FastAPI()
embedding_model = None

@app.on_event("startup")
async def startup():
    # Don't block, load in background
    asyncio.create_task(preload_models())
```

**Caching Strategies**:

```python
# Cache frequent queries
from functools import lru_cache

@lru_cache(maxsize=100)
def get_evidence_by_id(evidence_id: str) -> Evidence:
    # Cached for repeated access
    return evidence_repo.get_by_id(evidence_id)
```

---

## Summary

### Key Architecture Decisions

1. **Modular Monolith**: Single FastAPI app with clear module boundaries
   - Faster development than microservices
   - Easy extraction to services in v1
   - Sufficient for MVP scale (<1000 claims/day)

2. **Three-Layer Architecture**: API → Domain → Infrastructure
   - Clear separation of concerns
   - Domain logic is framework-independent
   - Easy to test each layer independently

3. **Repository Pattern**: Abstract data access behind interfaces
   - Domain doesn't depend on database
   - Can swap PostgreSQL → MongoDB via config
   - Repositories become HTTP clients in v1

4. **Synchronous Processing**: Direct function calls for verification
   - <60s latency acceptable for MVP
   - Simpler debugging (no distributed tracing)
   - Can add async (Redis Streams) in v1 when needed

5. **Dependency Injection**: FastAPI's built-in DI for services
   - Easy to test (override dependencies)
   - Clear dependency graph
   - Single Responsibility Principle

### v0 → v1 Upgrade Path

**Module Extraction Strategy**:

- `api/routes/` → API Gateway service
- `domain/services/verification_service.py` → Verification Service
- `domain/services/evidence_service.py` → Corpus Service
- Background jobs → Worker Service

**Migration Steps**:

1. Create new FastAPI apps for each service
2. Copy module code to new service
3. Replace function calls with HTTP clients
4. Add service discovery (env vars or Consul)
5. Deploy alongside monolith (gradual migration)

**Estimated Effort**: 2-3 weeks (with clean module boundaries)

### Next Steps

1. **Implement Phase 1**: Docker setup, database, basic API (Week 1-2)
2. **Implement Phase 2**: Embeddings, search, verification (Week 3-5)
3. **Document as You Go**: README, API docs, architecture decisions
4. **Test Continuously**: 70%+ test coverage on domain logic
5. **Plan v1 Migration**: Review service boundaries, identify breaking points

### Related Documentation

- [v0 Overview](./00_overview.md) - Vision and scope
- [Phase 1: Foundation](./phase_01_foundation.md) - Docker, database, API basics
- [v1 Overview](../v1/00_overview.md) - Target microservices architecture

---

**Document Version**: 1.0
**Last Updated**: 2025-01-15
**Status**: Ready for Implementation
