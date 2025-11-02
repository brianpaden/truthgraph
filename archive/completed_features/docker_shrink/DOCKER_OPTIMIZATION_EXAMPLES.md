# Docker Image Optimization - Code Examples

## Phase 1: Quick Wins (Immediate Implementation - 15 minutes)

### Change 1: Remove Test Files from Dockerfile

**File: `docker/api.Dockerfile`**

**Before (lines 101-107):**
```dockerfile
# Copy tests for development/testing
# Updated: 2025-10-30 - Fixed SQL assertion in test_top_k_parameter
COPY tests ./tests

# Copy performance scripts for benchmarking and optimization
# Updated: 2025-10-30 - Fixed database connection issues
COPY scripts ./scripts
```

**After:**
```dockerfile
# Tests are not included in production image
# They can be mounted at runtime for testing:
# docker run -v $(pwd)/tests:/app/tests truthgraph-api python -m pytest
```

**Impact:** -3.75 MB (2.75 MB tests + 980 kB scripts)

---

### Change 2: Fix pyproject.toml ML Dependencies

**File: `pyproject.toml`**

**Before (lines 52-58):**
```toml
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
]
```

**After:**
```toml
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
]
```

**Explanation:**
- pytest and pytest-asyncio are development dependencies
- They should be in the `dev` group, not `ml` group
- Removes 80-100 MB from image

**Testing to verify it was removed:**
```bash
# Build with change
docker build -t truthgraph-api:test -f docker/api.Dockerfile .

# Check pytest is NOT installed
docker run --rm truthgraph-api:test python -c "import pytest" 2>&1 | grep -q "No module" && echo "OK - pytest not installed"

# Check ML libraries ARE installed
docker run --rm truthgraph-api:test python -c "import torch; print(f'PyTorch {torch.__version__}')"
```

**Impact:** -100 MB (transitive dependencies removed)

---

### Change 3: Improve APT Cleanup

**File: `docker/api.Dockerfile`**

**Before (lines 25-31):**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
```

**After:**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/tmp/* \
    && rm -rf /tmp/*
```

**Explanation:**
- `apt-get clean` - removes unused package files
- `apt-get autoclean` - removes cached package files
- `apt-get autoremove` - removes unneeded packages
- `rm -rf /var/cache/apt/*` - removes APT package cache
- `rm -rf /var/tmp/* /tmp/*` - removes temporary files

**Impact:** -50-150 MB (APT cache cleanup)

**Total Phase 1 Impact:** -230 MB reduction (7.8 GB final)

---

## Phase 2: Build Tool Optimization (1 hour)

### Complete Refactored Dockerfile

**File: `docker/api.Dockerfile` (Complete rewrite)**

This version properly separates build and runtime stages:

```dockerfile
# syntax=docker/dockerfile:1.6

# TruthGraph v0 API Dockerfile - Optimized Multi-stage Build
# Phase 2: Better layer management and build tool cleanup

ARG INCLUDE_DEV=0

# ============================================================================
# Stage 1: Base stage with core system dependencies
# ============================================================================
FROM python:3.12-slim AS base

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/tmp/* \
    && rm -rf /tmp/*

# ============================================================================
# Stage 2: Builder stage - Install uv and build dependencies
# ============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# ============================================================================
# Stage 3: Dependencies stage - Install Python packages
# ============================================================================
FROM builder AS deps-stage

ARG INCLUDE_DEV

# Copy only dependency metadata (not source code)
# This ensures good layer caching
COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install dependencies without any development tools
# Using cache mounts for faster builds
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    EXTRA_SPEC=".[ml]"; \
    /root/.local/bin/uv pip install --system "${EXTRA_SPEC}"

# ============================================================================
# Stage 4: Runtime stage - Final minimal production image
# ============================================================================
FROM base AS runtime

WORKDIR /app

# Copy only the compiled packages, NOT build tools or uv
# This is the key difference - we copy the site-packages directly
COPY --from=deps-stage /usr/local/lib/python3.12/site-packages \
    /usr/local/lib/python3.12/site-packages

# Copy Python executable (if needed)
COPY --from=deps-stage /usr/local/bin/python* /usr/local/bin/

# Don't copy /root/.local (contains uv, not needed)
# Don't copy build tools (they stay in builder stage)

# Copy application code
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock
COPY truthgraph ./truthgraph
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Install the application package itself (not dependencies)
# Note: uv is in builder stage, we need Python's pip in runtime
RUN python3 -m pip install --no-deps --no-build-isolation .

# Setup runtime environment
RUN mkdir -p /root/.cache/huggingface && \
    useradd -m -u 1000 appuser || true

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HF_HOME=/root/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", \
    "truthgraph.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--reload"]
```

**Key Improvements:**
1. Separate builder stage - build tools don't leak into runtime
2. Only copy site-packages, not /root/.local
3. Better layer caching - no source code in dependency layer
4. Cleaner separation of concerns

**Impact:** -800 MB to -1.2 GB

**Total Phase 1+2 Impact:** -1.8 to -2.0 GB (6.0-6.2 GB final)

---

## Phase 3: Architectural Separation (Advanced)

### Option A: Core-Only API Image

**File: `docker/api-core.Dockerfile` (No ML)**

```dockerfile
# syntax=docker/dockerfile:1.6

# TruthGraph API - Core only (no ML)
# Size: 1.5-2.0 GB
# Use when ML inference is not needed locally

ARG INCLUDE_DEV=0

FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*

FROM builder AS deps-stage

COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install ONLY core dependencies (no ml group)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system .

FROM base AS runtime

WORKDIR /app

COPY --from=deps-stage /usr/local/lib/python3.12/site-packages \
    /usr/local/lib/python3.12/site-packages
COPY --from=deps-stage /usr/local/bin/python* /usr/local/bin/

COPY pyproject.toml ./
COPY truthgraph ./truthgraph
COPY alembic.ini ./
COPY alembic ./alembic

RUN python3 -m pip install --no-deps --no-build-isolation . && \
    mkdir -p /root/.cache/huggingface && \
    useradd -m -u 1000 appuser || true

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HF_HOME=/root/.cache/huggingface

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", \
    "truthgraph.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000"]
```

**Build it:**
```bash
docker build -t truthgraph-api:core -f docker/api-core.Dockerfile .
docker images truthgraph-api:core --format "{{.Size}}"
# Expected: 1.5-2.0 GB
```

---

### Option B: ML Inference Service Image

**File: `docker/ml-inference.Dockerfile` (ML only)**

```dockerfile
# syntax=docker/dockerfile:1.6

# TruthGraph ML Inference Service
# Size: 5.0-6.0 GB
# Deploy separately on GPU infrastructure

FROM python:3.12-slim AS base

WORKDIR /ml

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*

FROM builder AS ml-deps

COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install only ML dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system ".[ml]"

FROM base AS runtime

WORKDIR /ml

COPY --from=ml-deps /usr/local/lib/python3.12/site-packages \
    /usr/local/lib/python3.12/site-packages
COPY --from=ml-deps /usr/local/bin/python* /usr/local/bin/

# ML inference service - simplified, no full API
COPY truthgraph/ml ./truthgraph/ml
COPY truthgraph/__init__.py ./truthgraph/__init__.py

RUN mkdir -p /root/.cache/huggingface && \
    useradd -m -u 1000 mluser || true

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface

EXPOSE 8001

CMD ["python", "-m", "uvicorn", \
    "truthgraph.ml:app", \
    "--host", "0.0.0.0", \
    "--port", "8001"]
```

---

### Option C: Compose Setup for Multi-Image Deployment

**File: `docker-compose.prod.yml`**

```yaml
version: '3.9'

services:
  api-core:
    image: truthgraph-api:core
    container_name: truthgraph-api-core
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/truthgraph
      - ML_SERVICE_URL=http://ml-inference:8001
      - PYTHON_ENV=production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - ml-inference
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - truthgraph-network

  ml-inference:
    image: truthgraph-api:ml
    container_name: truthgraph-ml-inference
    environment:
      - CUDA_VISIBLE_DEVICES=0  # GPU configuration
      - HF_HOME=/root/.cache/huggingface
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - truthgraph-network
    volumes:
      - huggingface-cache:/root/.cache/huggingface

  postgres:
    image: postgres:15-alpine
    container_name: truthgraph-postgres
    environment:
      - POSTGRES_USER=truthgraph
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=truthgraph
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - truthgraph-network

volumes:
  postgres-data:
  huggingface-cache:

networks:
  truthgraph-network:
    driver: bridge
```

---

## Testing and Validation

### Test Phase 1 Changes

```bash
# 1. Build with Phase 1 changes
cd /path/to/truthgraph
docker build -t truthgraph-api:phase1 -f docker/api.Dockerfile .

# 2. Check size
docker images truthgraph-api:phase1 --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
# Expected: ~7.8 GB (compared to 8.03 GB currently)

# 3. Verify tests are NOT in image
docker run --rm truthgraph-api:phase1 ls -la /app/tests 2>&1 | grep -q "No such file" && \
  echo "PASS: Tests not in image" || echo "FAIL: Tests still present"

# 4. Verify scripts are NOT in image
docker run --rm truthgraph-api:phase1 ls -la /app/scripts 2>&1 | grep -q "No such file" && \
  echo "PASS: Scripts not in image" || echo "FAIL: Scripts still present"

# 5. Verify pytest is NOT installed
docker run --rm truthgraph-api:phase1 python -c "import pytest" 2>&1 | grep -q "No module" && \
  echo "PASS: pytest not installed" || echo "FAIL: pytest still installed"

# 6. Verify ML libraries ARE installed
docker run --rm truthgraph-api:phase1 python -c "import torch; print(f'PyTorch: {torch.__version__}')"
docker run --rm truthgraph-api:phase1 python -c "from sentence_transformers import SentenceTransformer; print('SentenceTransformers OK')"
docker run --rm truthgraph-api:phase1 python -c "from transformers import AutoModel; print('Transformers OK')"

# 7. Verify application works
docker run --rm truthgraph-api:phase1 python -c "from truthgraph import __version__; print(f'TruthGraph: {__version__}')"

# 8. Layer history
docker history truthgraph-api:phase1 --human | head -20
```

### Test Phase 2 Changes

```bash
# 1. Build refactored Dockerfile
docker build -t truthgraph-api:phase2 -f docker/api.Dockerfile .

# 2. Check size
docker images truthgraph-api:phase2 --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
# Expected: ~6.2 GB (20% reduction from original)

# 3. Check build time
time docker build -t truthgraph-api:phase2 -f docker/api.Dockerfile .

# 4. Layer analysis
docker history truthgraph-api:phase2 --human | grep -E "COPY|RUN" | head -20

# 5. Verify functionality
docker run --rm truthgraph-api:phase2 python -m pytest --version 2>&1 | grep -q "No module" && \
  echo "PASS: pytest not installed" || echo "FAIL"

# 6. Test application startup
timeout 30 docker run --rm truthgraph-api:phase2 python -c "
import sys
sys.path.insert(0, '/app')
from truthgraph.main import app
print('Application loaded successfully')
" || echo "Startup test timed out or failed"
```

### Test Phase 3 Changes

```bash
# Build both images
docker build -t truthgraph-api:core -f docker/api-core.Dockerfile .
docker build -t truthgraph-api:ml -f docker/ml-inference.Dockerfile .

# Compare sizes
echo "=== Size Comparison ==="
docker images truthgraph-api:* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Test core API (no ML)
docker run --rm truthgraph-api:core python -c "
import sys
try:
    import torch
    print('FAIL: torch should not be in core image')
except ImportError:
    print('PASS: Core image has no PyTorch')
"

# Test ML image
docker run --rm truthgraph-api:ml python -c "
import torch
print(f'PASS: ML image has PyTorch {torch.__version__}')
"

# Test composition
docker-compose -f docker-compose.prod.yml up -d
sleep 5
curl http://localhost:8000/health
curl http://localhost:8001/health
docker-compose -f docker-compose.prod.yml down
```

---

## Size Comparison Summary

```
Original Image:     8.03 GB
Phase 1 Changes:    7.80 GB (-230 MB, -2.8%)
Phase 2 Changes:    6.20 GB (-1.8 GB, -23%)
Phase 3a (Core):    1.80 GB (-6.2 GB, -77%)
Phase 3b (ML):      5.30 GB (separate image)
```

---

## Checklist for Implementation

### Phase 1: Quick Wins
- [ ] Update `docker/api.Dockerfile` - remove COPY tests and scripts
- [ ] Update `pyproject.toml` - remove pytest from ml dependencies
- [ ] Update `docker/api.Dockerfile` - improve APT cleanup
- [ ] Build and test
- [ ] Commit changes
- [ ] Document in CHANGELOG

### Phase 2: Build Optimization
- [ ] Refactor `docker/api.Dockerfile` with separate builder stage
- [ ] Update to use direct site-packages copy (not /root/.local)
- [ ] Test all functionality
- [ ] Measure build time
- [ ] Commit changes

### Phase 3: Architectural Separation
- [ ] Create `docker/api-core.Dockerfile`
- [ ] Create `docker/ml-inference.Dockerfile`
- [ ] Create `docker-compose.prod.yml`
- [ ] Test multi-container setup
- [ ] Update deployment documentation
- [ ] Plan rollout strategy

---

## Rollback Plan

Each phase is backward compatible:
- Phase 1 is a drop-in replacement (same image)
- Phase 2 is a drop-in replacement (same image)
- Phase 3 requires dual-image deployment

To rollback Phase 1 or 2:
```bash
git checkout docker/api.Dockerfile pyproject.toml
docker build -t truthgraph-api:latest -f docker/api.Dockerfile .
```

To rollback Phase 3:
```bash
git checkout docker-compose.prod.yml
# Remove new Dockerfiles: api-core.Dockerfile, ml-inference.Dockerfile
docker-compose -f docker-compose.prod.yml down
docker-compose up -d  # Use original compose file
```
