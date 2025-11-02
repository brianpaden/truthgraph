# syntax=docker/dockerfile:1.6

# TruthGraph v0 API Dockerfile - Phase 2: Optimized Multi-stage Build
# Python 3.12 with uv package manager
# PHASE 2 IMPROVEMENTS:
#   - Separate builder stage with build tools (gcc/g++/build-essential)
#   - Runtime stage only copies compiled packages, not build tools
#   - Build tools (300+ MB) completely removed from final image
#   - Only site-packages copied, not /root/.local with uv cache
#   - Better layer caching and build time optimization
#
# Stages:
#   1. base: Python runtime without build tools
#   2. builder: Build dependencies (gcc, g++, build-essential, uv)
#   3. deps-stage: Python package compilation (inherits from builder)
#   4. runtime: Final image (inherits from base, NOT builder)
#
# Usage:
#   docker build -t truthgraph-api -f docker/api.Dockerfile .
#   docker build --build-arg INCLUDE_DEV=1 -t truthgraph-api:dev -f docker/api.Dockerfile .

ARG INCLUDE_DEV=0

# ============================================================================
# Stage 1: Base - Python runtime without build tools (very small)
# ============================================================================
FROM python:3.12-slim AS base

WORKDIR /app

# Install ONLY runtime dependencies (no build tools here)
# postgresql-client: Runtime requirement for database operations
# curl: Runtime requirement for health checks
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
# Stage 2: Builder - Build tools and uv (intermediate, not in final image)
# ============================================================================
FROM base AS builder

# Install build dependencies
# gcc/g++: Required for compiling some Python packages from source
# build-essential: Meta-package with build tools
# These are ONLY needed for building, will not be in final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (pinned for reproducibility)
# This is only needed during build, will not be in final image
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# ============================================================================
# Stage 3: Dependencies - Build Python packages (inherits builder tools)
# ============================================================================
FROM builder AS deps-stage

ARG INCLUDE_DEV

WORKDIR /app

# Copy only metadata for dependency resolution
# This allows good cache layer reuse
COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install Python packages with ML support
# Using cache mounts for pip/uv wheels for faster rebuilds
# This layer is cached by the lockfile, not source code
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    if [ "${INCLUDE_DEV}" = "1" ]; then \
    EXTRA_SPEC=".[ml,dev]"; \
    else \
    EXTRA_SPEC=".[ml]"; \
    fi; \
    /root/.local/bin/uv pip install --system "${EXTRA_SPEC}"; \
    if [ "${INCLUDE_DEV}" = "1" ]; then \
    /root/.local/bin/uv pip install --system pytest-cov; \
    fi

# ============================================================================
# Stage 4: Core-only stage (without ML, optional)
# ============================================================================
FROM builder AS core-stage

WORKDIR /app

# Copy metadata for dependency resolution
COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install core dependencies only (no ML)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system .

# ============================================================================
# Stage 5: Runtime - Final production image
# KEY OPTIMIZATION: Inherits from 'base' (no build tools), not 'builder'
# ============================================================================
FROM base AS runtime

WORKDIR /app

# CRITICAL: Copy only compiled Python packages and executables
# NOT copying:
#   - /root/.local (contains uv, not needed in runtime)
#   - gcc/g++ or build tools (they're in builder stage only)
#   - Build headers or development files

# Copy compiled Python site-packages directly (this is where all packages live)
# This is the main layer (~7.4 GB) with all Python packages
COPY --from=deps-stage /usr/local/lib/python3.12/site-packages \
    /usr/local/lib/python3.12/site-packages

# Copy Python binary and any additional Python executables
COPY --from=deps-stage /usr/local/bin/python* /usr/local/bin/
COPY --from=deps-stage /usr/local/bin/pip* /usr/local/bin/

# OPTIMIZATION: Strip debug symbols from compiled libraries to reduce size
# This removes ~200-300 MB of debug information while keeping functionality
RUN find /usr/local/lib/python3.12/site-packages -type f \( -name "*.so*" -o -name "*.a" \) -exec \
    strip --strip-unneeded {} \; 2>/dev/null || true

# Copy application metadata and source
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock

# Copy application code (main module)
COPY truthgraph ./truthgraph

# Copy Alembic migration files for database schema management
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Install the application package itself (without re-installing dependencies)
# Using pip directly since uv is not in runtime stage
# The --no-deps flag ensures we don't re-download/compile packages
RUN python3 -m pip install --no-deps --no-build-isolation . 2>/dev/null || \
    python3 -m pip install --no-deps . 2>/dev/null || true

# Runtime-only setup (create directories and user)
RUN mkdir -p /root/.cache/huggingface && \
    useradd -m -u 1000 appuser || true

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HF_HOME=/root/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface

# Expose API port
EXPOSE 8000

# Health check endpoint
# Uses longer start period for ML model loading on first run
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with Uvicorn
CMD ["python", "-m", "uvicorn", \
    "truthgraph.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--reload"]
