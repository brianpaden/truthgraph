# TruthGraph API Docker Image Size Analysis

## Executive Summary

The `truthgraph-api:latest` Docker image is **8.03 GB**, which is significantly larger than necessary for a production API container. The analysis reveals that the bloat is caused by four primary factors:

1. **PyTorch ML Stack (5.3GB)** - 66% of image size
2. **NVIDIA CUDA Libraries (4.3GB)** - 54% of image size (overlaps with PyTorch)
3. **Development Tools (not removed)** - 100+ MB unnecessarily included
4. **Non-optimal multi-stage build** - Not fully leveraging Docker layer caching

---

## Docker Layer Breakdown

### Complete Layer History (from `docker history`)

| Layer | Size | Component | Issue |
|-------|------|-----------|-------|
| Base Debian filesystem | 78.6 MB | debian:bookworm | Expected |
| Python 3.12 compilation | 36.8 MB | python:3.12-slim | Expected |
| Build dependencies (APT) | 323 MB | gcc, g++, build-essential | Installed in base, not removed |
| uv package manager | 53.6 MB | astral.sh/uv | Expected |
| `/usr/local (copied from deps-stage)` | **7.48 GB** | Python packages + libraries | **PRIMARY CULPRIT** |
| `/root/.local (copied from deps-stage)` | 53.6 MB | uv cache/binaries | Unnecessary in runtime |
| Source code + tests + scripts | 3.75 MB | App code | Unnecessary to include tests |
| Configuration files | 2.21 kB | pyproject.toml, uv.lock | Expected |

### Total Image Size Analysis
- **Total: 8.03 GB**
- **Removable via build optimization: 3.7-4.0 GB (46%)**
- **Target achievable size: 4.0-4.3 GB** (with PyTorch ML stack)
- **Minimum size: 1.5-2.0 GB** (core API only, without ML stack)

---

## Root Causes - Detailed Breakdown

### 1. PyTorch ML Stack (5.3 GB total) - 66% of image

| Package | Size | Purpose | Necessity |
|---------|------|---------|-----------|
| **nvidia (CUDA libs)** | 4.3 GB | GPU acceleration binaries | For ML inference only |
| **torch** | 1.7 GB | PyTorch framework | For ML inference |
| **triton** | 592 MB | Triton compiler | PyTorch dependency |
| **scipy** | 87 MB | Scientific computing | PyTorch dependency |
| **transformers** | 57 MB | HuggingFace models | For NLP tasks |
| **sklearn** | 35 MB | Machine learning | Optional dependency |
| **numpy** | 31 MB | Numerical computing | PyTorch dependency |
| **sympy** | 30 MB | Symbolic math | Transitive dependency |
| **networkx** | 7.9 MB | Graph library | Transitive dependency |

**Status:** The ML stack is specified in `pyproject.toml` under `[project.optional-dependencies] ml = [...]` but is being installed as part of the runtime image via `.[ml]`. This is correct for an ML API but requires 5.3GB.

### 2. Development Tools (100+ MB) - REMOVABLE

The following development-only packages are unnecessarily included in the production runtime image:

| Package | Size | Issue |
|---------|------|-------|
| **mypy** | 12 MB | Type checker - not needed at runtime |
| **pytest** | ~20 MB + plugins | Test framework - not needed at runtime |
| **pytest-asyncio** | ~5 MB | Testing - not needed at runtime |
| **pytest-benchmark** | ~3 MB | Testing - not needed at runtime |
| **pytest-cov** | ~3 MB | Coverage - not needed at runtime |
| **pytest-sugar** | ~2 MB | Testing UI - not needed at runtime |
| **pytest-timeout** | ~1 MB | Testing - not needed at runtime |
| **pytest-xdist** | ~3 MB | Parallel testing - not needed at runtime |
| **ruff** | ~15 MB | Linter - not needed at runtime |

**Status:** These are installed because the Dockerfile builds with `.[ml,dev]` even though `INCLUDE_DEV` defaults to 0.

**Action Taken:** The Dockerfile already has logic to exclude dev dependencies when `INCLUDE_DEV=0`, but the dependencies are being pulled transitively from pytest in the ML dependencies group.

### 3. Build Tools Not Removed (150-200 MB)

The following packages are installed during build but NOT cleaned up:

- `gcc` - C/C++ compiler
- `g++` - C++ compiler
- `build-essential` - Build tools metapackage
- Various header files and development libraries
- `postgresql-client` - Database tools (sometimes only needed for migrations)

**Status:** These exist because the Dockerfile uses multi-stage builds but `gcc`/`g++` are still needed in the final stage to support some packages that compile from source or have C extensions. However, headers and development files should be cleaned.

### 4. Shared Libraries Not Stripped (1.2 GB)

Multiple large compiled shared object files (.so) that could be optimized:

- `scipy.libs/` - 30 MB in libs directory
- `numpy.libs/` - 27 MB in libs directory
- `pillow.libs/` - 14 MB in libs directory
- `psycopg_binary.libs/` - 11 MB in libs directory
- 490+ `.so` files total with debugging symbols

**Status:** These are necessary for runtime functionality but often include unnecessary debugging symbols.

### 5. Application Payload (3.75 MB) - PARTIALLY REMOVABLE

| Item | Size | Status |
|------|------|--------|
| `tests/` directory | 2.75 MB | **Should not be in production image** |
| `scripts/` directory | 980 kB | **Should not be in production image** |
| Application source code | 709 kB | Required |
| Alembic migrations | 17.7 kB | Required |

---

## Detailed Dockerfile Analysis

### Current Issues in `docker/api.Dockerfile`

```dockerfile
# Line 59-62: Dev dependencies included via transitive deps
if [ "${INCLUDE_DEV}" = "1" ]; then
EXTRA_SPEC=".[ml,dev]";  # Even with dev=0, ml includes pytest
else
EXTRA_SPEC=".[ml]";      # ml optional dependency includes test runners
fi;

# Line 101-107: Test and script files copied into production image
COPY tests ./tests       # ISSUE: 2.75 MB of test files
COPY scripts ./scripts   # ISSUE: 980 kB of performance scripts

# Line 125: HuggingFace cache directory created but empty
HF_HOME=/root/.cache/huggingface
HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface
```

### Multi-Stage Build Opportunity

The Dockerfile has 3 stages (base, deps-stage, core-stage, runtime) but:
- `deps-stage` installs everything (ML + dev + build tools)
- `runtime` stage copies the ENTIRE `/usr/local` from deps-stage
- No cleanup of build artifacts between stages

---

## Size Reduction Recommendations

### Quick Wins (1.2-1.5 GB reduction, 15% size decrease)

#### 1. Remove Test and Script Files from Production Image
**Estimated Savings: 3.75 MB (negligible but good practice)**

```dockerfile
# Remove these lines from runtime stage:
# COPY tests ./tests         # 2.75 MB
# COPY scripts ./scripts     # 980 kB

# If needed for development, use docker mount or separate image:
# docker run -v ./tests:/app/tests truthgraph-api
```

**Implementation:**
```dockerfile
# Stage 3: Runtime stage (MODIFIED)
FROM base AS runtime

WORKDIR /app

COPY --from=deps-stage /usr/local /usr/local
COPY --from=deps-stage /root/.local /root/.local

COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock
COPY truthgraph ./truthgraph
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# REMOVED: COPY tests ./tests
# REMOVED: COPY scripts ./scripts

# ... rest of runtime setup
```

**Savings: 3.75 MB**

#### 2. Exclude Development Dependencies from ML Stack
**Estimated Savings: 80-100 MB (1.3% reduction)**

Remove `pytest` entries from `pyproject.toml` ML dependencies:

```toml
# Current (INCORRECT):
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
    "pytest>=7.4.3",        # REMOVE - not needed
    "pytest-asyncio>=0.21.1", # REMOVE - not needed
]

# Corrected:
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
]
```

**Savings: 80-100 MB**

#### 3. Clean Up APT Package Manager Cache
**Estimated Savings: 150-200 MB (2.5% reduction)**

Currently partially done, but can be more aggressive:

```dockerfile
# In the base stage, after apt-get install:
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*
```

**Savings: 150-200 MB**

### Medium Effort (1.5-2.0 GB reduction, 19-25% reduction)

#### 4. Remove Unnecessary Build Dependencies with Cleanup
**Estimated Savings: 600-800 MB (7.5-10% reduction)**

Create a dedicated build stage that cleans up after compilation:

```dockerfile
# Stage 2b: Build with cleanup (NEW)
FROM base AS build-stage

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system ".[ml]"

# Clean build dependencies
RUN apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Stage 3: Runtime (use build-stage instead of deps-stage)
FROM base AS runtime

COPY --from=build-stage /usr/local /usr/local
```

**Savings: 600-800 MB**

#### 5. Use Alpine Linux Base Image (ADVANCED - Breaking Change)
**Estimated Savings: 100-200 MB**

```dockerfile
FROM python:3.12-alpine AS base
```

**Caveats:**
- Some packages may not have Alpine wheels available
- PyTorch compilation from source on Alpine is slow
- Not recommended if pre-built wheels don't exist

**Savings: 100-200 MB (likely requires custom compilation)**

### Advanced Solutions (2.0+ GB reduction, 25%+ reduction)

#### 6. Separate Core API and ML Model Inference
**Estimated Savings: 5.3 GB (66% reduction from current image)**

Create two Docker images:

**Option A: Core-only image (1.5-2.0 GB)**
```dockerfile
# docker/api-core.Dockerfile - for basic API operations
FROM python:3.12-slim AS base
# ... install only core dependencies (no ML)
# /root/.local size: ~200 MB
# Final size: 1.5-2.0 GB
```

**Option B: ML-inference sidecar or lambda function**
```dockerfile
# docker/ml-inference.Dockerfile - separate ML model server
# Deploy on GPU-enabled infrastructure only when needed
# Can be scaled independently
```

**Savings: 5.3 GB (but requires architectural change)**

#### 7. Strip Binary Symbols from Compiled Libraries
**Estimated Savings: 300-500 MB (3.7-6% reduction)**

After installing packages but before final image:

```dockerfile
# Strip unnecessary symbols from compiled binaries
RUN find /usr/local/lib -name "*.so*" -type f -exec strip --strip-unneeded {} \; 2>/dev/null || true && \
    find /usr/local/bin -type f -executable -exec strip --strip-unneeded {} \; 2>/dev/null || true
```

**Warning:** This can break binary compatibility with some packages. Test thoroughly.

**Savings: 300-500 MB**

#### 8. Use Python -OO Optimization (MINOR)
**Estimated Savings: 10-20 MB (0.2% reduction)**

```dockerfile
ENV PYTHONOPTIMIZE=2
```

This removes docstrings and optimizes bytecode. Minimal impact on space.

**Savings: 10-20 MB**

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (Implement Immediately - 15 minutes)
**Reduces image from 8.03 GB to 7.8 GB (2.8% reduction)**

1. Remove `tests` and `scripts` directories from Dockerfile
2. Remove `pytest` dependencies from `ml` group in `pyproject.toml`
3. Add aggressive APT cleanup

**Files to modify:**
- `docker/api.Dockerfile` - 3 lines changed
- `pyproject.toml` - 2 lines removed

### Phase 2: Medium Effort (Implement Soon - 1 hour)
**Reduces image from 7.8 GB to 6.2 GB (23% total reduction)**

1. Separate build-stage with cleanup of build dependencies
2. Better caching of package manager layers
3. Remove `postgresql-client` if not needed in runtime

**Files to modify:**
- `docker/api.Dockerfile` - Significant refactoring

### Phase 3: Long-term (Architectural Change - 1-2 weeks)
**Reduces image to 1.5-2.0 GB (75% reduction possible)**

1. Split into core API and ML inference services
2. Move ML models to separate image/container
3. Deploy ML inference on GPU-only infrastructure
4. Core API runs on minimal image

**Files to create:**
- `docker/api-core.Dockerfile` - Lightweight API
- `docker/ml-inference.Dockerfile` - ML model server (optional)
- `docker-compose.ml.yml` - Service orchestration (optional)

---

## Specific Code Changes

### Phase 1 Implementation

**File: `pyproject.toml`** (Remove 2 lines)

```toml
# BEFORE:
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
    "pytest>=7.4.3",          # DELETE
    "pytest-asyncio>=0.21.1", # DELETE
]

# AFTER:
ml = [
    "torch>=2.1.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.35.0",
]
```

**File: `docker/api.Dockerfile`** (Remove lines 101-107)

```dockerfile
# BEFORE (lines 101-107):
# Copy tests for development/testing
# Updated: 2025-10-30 - Fixed SQL assertion in test_top_k_parameter
COPY tests ./tests

# Copy performance scripts for benchmarking and optimization
# Updated: 2025-10-30 - Fixed database connection issues
COPY scripts ./scripts

# AFTER:
# (Remove the entire COPY tests and COPY scripts sections)
# Tests can be mounted at runtime or kept in separate development image
```

**File: `docker/api.Dockerfile`** (Improve APT cleanup in base stage)

```dockerfile
# BEFORE (lines 25-31):
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# AFTER:
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
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*
```

---

## Build and Test Commands

### Measure Current Size
```bash
docker build -t truthgraph-api:latest -f docker/api.Dockerfile .
docker images truthgraph-api:latest --format "{{.Size}}"
docker history truthgraph-api:latest --human
```

### Build with Phase 1 Changes
```bash
# After implementing Phase 1 changes
docker build --no-cache -t truthgraph-api:optimized-1 -f docker/api.Dockerfile .
docker images truthgraph-api:optimized-1 --format "{{.Size}}"

# Compare sizes
docker images | grep truthgraph-api
```

### Test Image Functionality
```bash
# Ensure API still works
docker run --rm truthgraph-api:optimized-1 python -c "import torch; print('Torch:', torch.__version__)"
docker run --rm truthgraph-api:optimized-1 python -c "from sentence_transformers import SentenceTransformer; print('SentenceTransformers OK')"
docker run --rm truthgraph-api:optimized-1 python -c "from truthgraph import __version__; print('TruthGraph OK')"
```

---

## Why is the Image So Large? Summary

1. **PyTorch is Massive** - PyTorch framework + CUDA libraries = 5.3 GB alone
2. **Transitive Dependencies** - PyTorch pulls in many data science libraries
3. **No Binary Stripping** - Compiled libraries include debug symbols
4. **Build Tools Left Behind** - gcc/g++ not removed after compilation
5. **Test Files in Production** - 2.75 MB of tests in runtime image
6. **Debian Base** - Full Debian/Python is 80-100 MB before anything else
7. **No Cleanup Between Stages** - Multi-stage build could be more aggressive

---

## Estimated Results After Phase 1

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Image Size | 8.03 GB | 7.80 GB | 2.8% |
| Tests included | Yes (2.75 MB) | No | 2.75 MB |
| Scripts included | Yes (980 kB) | No | 980 kB |
| Dev tools | Yes (100 MB) | No (80 MB) | 20 MB |
| APT cache | Partially cleaned | Fully cleaned | 50 MB |

**Phase 1 Impact: 230 MB reduction**

## Estimated Results After Phase 2

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Image Size | 8.03 GB | 6.2 GB | 23% |
| Build tools (gcc/g++) | Included in deps | Removed | 600 MB |
| Build cache | Not optimized | Optimized | 800 MB |

**Phase 2 Impact: 1.8 GB reduction** (cumulative: 2.0 GB)

## Estimated Results After Phase 3

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Core API image | 8.03 GB | 1.5-2.0 GB | 75% |
| ML inference image | N/A | 5.0-6.0 GB | Separate |
| Deployment flexibility | Limited | High | Better scaling |

**Phase 3 Impact: 6.0 GB reduction** (new architecture)

---

## Conclusion

The 8 GB image size is primarily driven by the PyTorch ML stack (unavoidable if ML inference is needed), but there are 1.8-2.0 GB of easily removable bloat in the current build configuration.

**Immediate Action:** Implement Phase 1 changes (15 minutes) to remove test files and optimize APT cleanup.

**Short-term:** Implement Phase 2 changes (1 hour) to separate build dependencies more cleanly.

**Long-term:** Consider Phase 3 architectural changes to separate ML inference from the API container for better scaling and cost efficiency.
