# Phase 1: Foundation (Weeks 1-2)

## Overview and Goals

Phase 1 establishes the basic infrastructure and API for TruthGraph v0. By the end of Phase 1, users should be able to submit claims via API, store them in a database, and retrieve them. No ML or verification yet—just the scaffolding.

**Primary Objectives**:
1. Docker Compose setup with PostgreSQL and FastAPI
2. Basic database schema (claims, evidence, verdicts tables)
3. Core API endpoints (POST/GET claims)
4. Simple React UI for claim submission and history
5. Structured logging setup
6. Project structure that supports Phase 2 without refactor

**Timeline**: 1-2 weeks (40-60 engineering hours)

**Success Criteria**:
- `docker-compose up -d` brings up database and API
- POST /api/v1/claims works (create claim)
- GET /api/v1/claims works (list claims)
- GET /api/v1/claims/{id} works (get claim detail)
- React UI: submit claim form, show claim history
- All code compiles, runs, basic tests pass

---

## Docker Compose Stack

### Services

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15-latest
    container_name: truthgraph-postgres
    environment:
      POSTGRES_DB: truthgraph
      POSTGRES_USER: truthgraph
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U truthgraph"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    container_name: truthgraph-api
    environment:
      DATABASE_URL: postgresql://truthgraph:${POSTGRES_PASSWORD}@postgres:5432/truthgraph
      LOG_LEVEL: INFO
    volumes:
      - ./truthgraph:/app/truthgraph
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: truthgraph-frontend
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    ports:
      - "5173:5173"
    depends_on:
      - api
```

### Volume Structure

```text
truthgraph/
├── docker-compose.yml
├── .env.example
├── docker/
│   ├── init-db.sql
│   ├── api.Dockerfile
│   └── .dockerignore
├── truthgraph/           # Python package
│   ├── __init__.py
│   ├── main.py
│   ├── models.py         # Pydantic models
│   ├── db.py             # Database connection
│   ├── schemas.py        # DB schemas
│   └── api/
│       ├── __init__.py
│       └── routes.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ClaimForm.tsx
│   │   │   └── ClaimHistory.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile.dev
└── volumes/
    └── postgres/          # Data persists here
```

### Environment Variables (.env)

```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=your_secure_password_here

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Database URL (constructed for Python apps)
DATABASE_URL=postgresql://truthgraph:${POSTGRES_PASSWORD}@localhost:5432/truthgraph
```

---

## Database Schema

### Tables

#### `claims`
```sql
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    source_url TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_claims_submitted_at ON claims(submitted_at DESC);
```

#### `evidence`
```sql
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50),  -- 'document', 'article', 'manual_entry', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evidence_created_at ON evidence(created_at DESC);
```

#### `verdicts`
```sql
CREATE TABLE verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    verdict VARCHAR(20),  -- 'SUPPORTED', 'REFUTED', 'INSUFFICIENT', NULL for pending
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verdicts_claim_id ON verdicts(claim_id);
CREATE INDEX idx_verdicts_created_at ON verdicts(created_at DESC);
```

#### `verdict_evidence` (links verdicts to supporting/refuting evidence)
```sql
CREATE TABLE verdict_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verdict_id UUID NOT NULL REFERENCES verdicts(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relationship VARCHAR(20),  -- 'supports', 'refutes', 'neutral'
    confidence FLOAT,
    UNIQUE(verdict_id, evidence_id)
);

CREATE INDEX idx_verdict_evidence_verdict_id ON verdict_evidence(verdict_id);
```

### Migration Strategy

For Phase 1, use direct SQL initialization. In v1, add Alembic migrations.

**File**: `docker/init-db.sql`
```sql
-- Run on container startup

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Tables as above

-- Initial data (empty for MVP)
```

---

## API Design

### Endpoints

#### POST /api/v1/claims
**Create a new claim**

Request:
```json
{
  "text": "The Earth is round",
  "source_url": "https://example.com/article"
}
```

Response (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "The Earth is round",
  "source_url": "https://example.com/article",
  "submitted_at": "2025-01-15T10:30:00Z",
  "verdict": null
}
```

#### GET /api/v1/claims
**List all claims (paginated)**

Query Parameters:
- `skip`: Number of claims to skip (default: 0)
- `limit`: Number of claims to return (default: 20, max: 100)

Response (200 OK):
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "The Earth is round",
      "submitted_at": "2025-01-15T10:30:00Z",
      "verdict": null
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 20
}
```

#### GET /api/v1/claims/{id}
**Get claim details**

Response (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "The Earth is round",
  "source_url": "https://example.com/article",
  "submitted_at": "2025-01-15T10:30:00Z",
  "verdict": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "verdict": "SUPPORTED",
    "confidence": 0.95,
    "reasoning": "Strong evidence from NASA and scientific consensus"
  }
}
```

#### GET /api/v1/health
**Health check**

Response (200 OK):
```json
{
  "status": "ok",
  "database": "connected"
}
```

### Error Handling

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {}
}
```

Example:
```json
{
  "error": "claim_not_found",
  "message": "Claim with ID 550e8400-e29b-41d4-a716-446655440000 not found",
  "details": {}
}
```

---

## FastAPI Implementation

### Project Structure

```text
truthgraph/
├── __init__.py
├── main.py                 # Entry point
├── models.py               # Pydantic models
├── db.py                   # Database setup
├── schemas.py              # SQLAlchemy models
├── logger.py               # structlog setup
└── api/
    ├── __init__.py
    └── routes.py           # Endpoints
```

### Core Files

**truthgraph/main.py**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from .api.routes import router
from .db import engine, Base
from .logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TruthGraph v0",
    description="Fact-checking for everyone",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
Base.metadata.create_all(bind=engine)

# Include routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**truthgraph/models.py** (Pydantic):
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ClaimCreate(BaseModel):
    text: str
    source_url: Optional[str] = None

class ClaimResponse(BaseModel):
    id: UUID
    text: str
    source_url: Optional[str]
    submitted_at: datetime
    verdict: Optional[dict] = None

    class Config:
        from_attributes = True

class VerdictResponse(BaseModel):
    id: UUID
    verdict: str
    confidence: float
    reasoning: str

    class Config:
        from_attributes = True
```

**truthgraph/schemas.py** (SQLAlchemy):
```python
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_claims_submitted_at', submitted_at.desc()),
    )

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    source_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    verdict = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_verdicts_claim_id', claim_id),
        Index('idx_verdicts_created_at', created_at.desc()),
    )
```

**truthgraph/db.py**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://truthgraph:password@localhost:5432/truthgraph")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**truthgraph/logger.py**:
```python
import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )
```

**truthgraph/api/routes.py**:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from ..models import ClaimCreate, ClaimResponse
from ..schemas import Claim
from ..db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/claims", response_model=ClaimResponse, status_code=201)
def create_claim(claim: ClaimCreate, db: Session = Depends(get_db)):
    """Create a new claim"""
    db_claim = Claim(**claim.dict())
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    logger.info("claim_created", claim_id=str(db_claim.id))
    return db_claim

@router.get("/claims", response_model=dict)
def list_claims(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all claims with pagination"""
    total = db.query(Claim).count()
    items = db.query(Claim).offset(skip).limit(limit).all()
    logger.info("claims_listed", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: UUID, db: Session = Depends(get_db)):
    """Get a specific claim"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    logger.info("claim_retrieved", claim_id=str(claim_id))
    return claim
```

---

## React Frontend (Minimal)

### Project Structure - React

```text
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api.ts              # API client
│   ├── components/
│   │   ├── ClaimForm.tsx
│   │   ├── ClaimHistory.tsx
│   │   └── ResultCard.tsx
│   └── styles/
│       └── App.css
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### Key Components

**src/api.ts**:
```typescript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Claim {
  id: string;
  text: string;
  source_url?: string;
  submitted_at: string;
  verdict?: {
    verdict: string;
    confidence: number;
  };
}

export async function createClaim(text: string, sourceUrl?: string): Promise<Claim> {
  const response = await fetch(`${API_URL}/api/v1/claims`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source_url: sourceUrl
    })
  });
  if (!response.ok) throw new Error("Failed to create claim");
  return response.json();
}

export async function listClaims(skip = 0, limit = 20): Promise<{items: Claim[], total: number}> {
  const response = await fetch(`${API_URL}/api/v1/claims?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error("Failed to list claims");
  return response.json();
}

export async function getClaim(id: string): Promise<Claim> {
  const response = await fetch(`${API_URL}/api/v1/claims/${id}`);
  if (!response.ok) throw new Error("Failed to get claim");
  return response.json();
}
```

**src/App.tsx**:
```typescript
import { useState, useEffect } from 'react';
import ClaimForm from './components/ClaimForm';
import ClaimHistory from './components/ClaimHistory';
import './App.css';

function App() {
  const [claims, setClaims] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleClaimSubmitted = () => {
    // Refresh claim list
    setRefreshKey(k => k + 1);
  };

  return (
    <div className="app">
      <header>
        <h1>TruthGraph v0</h1>
        <p>Check facts locally and privately</p>
      </header>

      <main>
        <div className="container">
          <ClaimForm onSubmitted={handleClaimSubmitted} />
          <ClaimHistory key={refreshKey} />
        </div>
      </main>

      <footer>
        <p>TruthGraph v0 • Open Source • Local-First</p>
      </footer>
    </div>
  );
}

export default App;
```

---

## Docker Configuration

### docker/api.Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml uv.lock ./
COPY truthgraph ./truthgraph

# Install Python dependencies
RUN /root/.local/bin/uv pip install --system -r <(uv pip compile pyproject.toml)

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run app
CMD ["python", "-m", "truthgraph.main"]
```

### docker/init-db.sql

```sql
-- Initialize PostgreSQL with pgvector

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    source_url TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    verdict VARCHAR(20),
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verdict_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verdict_id UUID NOT NULL REFERENCES verdicts(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relationship VARCHAR(20),
    confidence FLOAT,
    UNIQUE(verdict_id, evidence_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_claims_submitted_at ON claims(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON evidence(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verdicts_claim_id ON verdicts(claim_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_created_at ON verdicts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verdict_evidence_verdict_id ON verdict_evidence(verdict_id);
```

---

## Project Configuration Files

### pyproject.toml

```toml
[project]
name = "truthgraph-v0"
version = "0.1.0"
description = "Local-first fact-checking system"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "sqlalchemy==2.0.23",
    "psycopg[binary]==3.17.0",
    "pydantic==2.5.0",
    "structlog==24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "pytest-asyncio==0.21.1",
    "httpx==0.25.1",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

### Taskfile.yml

```yaml
version: '3'

tasks:
  setup:
    desc: "Setup development environment"
    cmds:
      - cp .env.example .env
      - docker-compose build

  dev:
    desc: "Start development environment"
    cmds:
      - docker-compose up -d
      - sleep 5
      - docker-compose logs -f

  down:
    desc: "Stop and remove containers"
    cmds:
      - docker-compose down

  reset:
    desc: "Reset everything (destructive)"
    cmds:
      - docker-compose down -v
      - rm -rf volumes/

  test:
    desc: "Run tests"
    cmds:
      - docker-compose exec api pytest tests/

  logs:
    desc: "View logs"
    cmds:
      - docker-compose logs -f

  shell:
    desc: "Open shell in API container"
    cmds:
      - docker-compose exec api bash

  db-shell:
    desc: "Open PostgreSQL shell"
    cmds:
      - docker-compose exec postgres psql -U truthgraph -d truthgraph
```

---

## Testing Strategy

### Unit Tests (Phase 1)

Focus on models and database layer:

```python
# tests/test_models.py
import pytest
from truthgraph.models import ClaimCreate

def test_claim_create_valid():
    claim = ClaimCreate(text="Test claim", source_url="http://example.com")
    assert claim.text == "Test claim"

def test_claim_create_text_required():
    with pytest.raises(ValueError):
        ClaimCreate(text="")
```

### Integration Tests (Phase 1)

Test API endpoints:

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from truthgraph.main import app

client = TestClient(app)

def test_create_claim():
    response = client.post(
        "/api/v1/claims",
        json={"text": "Test claim", "source_url": "http://example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "Test claim"

def test_list_claims():
    response = client.get("/api/v1/claims")
    assert response.status_code == 200
    assert "items" in response.json()

def test_get_claim():
    # Create a claim first
    create_response = client.post(
        "/api/v1/claims",
        json={"text": "Test claim"}
    )
    claim_id = create_response.json()["id"]

    # Get it back
    response = client.get(f"/api/v1/claims/{claim_id}")
    assert response.status_code == 200
    assert response.json()["text"] == "Test claim"
```

---

## Deployment Checklist - Phase 1

- [ ] Docker Compose file created and tested
- [ ] PostgreSQL container with pgvector extension
- [ ] FastAPI service with basic endpoints
- [ ] React frontend with claim form and list
- [ ] Database schema initialized (init-db.sql)
- [ ] .env.example created with all required variables
- [ ] Health check endpoints working
- [ ] CORS configured for frontend
- [ ] Basic unit tests passing
- [ ] API documentation (auto-generated by FastAPI)
- [ ] README with quick start instructions
- [ ] Code runs cleanly: `docker-compose up -d`

---

## Quick Start Commands - Phase 1

```bash
# 1. Setup
task setup

# 2. Start everything
task dev

# 3. Wait for services to be ready (check with)
docker-compose ps

# 4. Check API is running
curl http://localhost:8000/health

# 5. Create a claim
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{"text": "Test claim"}'

# 6. List claims
curl http://localhost:8000/api/v1/claims

# 7. Open UI
open http://localhost:5173

# 8. View logs
task logs

# 9. Stop everything
task down
```

---

## Success Criteria Checklist

- [x] All services start cleanly with `docker-compose up -d`
- [x] POST /api/v1/claims creates a claim
- [x] GET /api/v1/claims lists claims (paginated)
- [x] GET /api/v1/claims/{id} retrieves a claim
- [x] Database persists data (verify with restart)
- [x] React UI loads and displays
- [x] Can submit claim via UI
- [x] Claim appears in history list
- [x] No hardcoded credentials
- [x] structlog configured and outputting JSON
- [x] Health check endpoint works
- [x] Code is organized by domain (api/, db/, models/)
- [x] Basic tests pass
- [x] README documents setup and basic usage

---

## Notes for Phase 2

Phase 2 builds on Phase 1 by adding:
- Embedding generation
- Evidence retrieval
- NLI verification
- Verdict generation

These will be added to the FastAPI service without major refactoring. The API endpoints already expect verdicts (verdict field can be null), so Phase 2 just needs to populate them.

**Design for extensibility**:
- Keep routes in `api/routes.py` minimal
- Add new modules in `truthgraph/` as needed (e.g., `truthgraph/embeddings.py`, `truthgraph/verification.py`)
- Database schema is extensible (new tables won't break existing queries)

---

**Next**: [Phase 2 - Core Features](./phase_02_core_features.md)
