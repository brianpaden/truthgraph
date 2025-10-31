# syntax=docker/dockerfile:1.6

# TruthGraph v0 API Dockerfile - Multi-stage Build with ML Support
# Python 3.12 with uv package manager
# Optimized for layer caching and fast builds
#
# Stage 1: Base stage with core dependencies (cached)
# Stage 2: Dependency stage with ML stack
# Stage 3: Runtime stage (final image)
#
# Usage:
#   docker build -t truthgraph-api -f docker/api.Dockerfile .

ARG INCLUDE_DEV=0

# Stage 1: Base image with core dependencies
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
# gcc/g++: Required for psycopg[binary], pgvector compilation
# curl: Required for health checks
# postgresql-client: Required for database tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv package manager (pinned to specific version for reproducibility)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Stage 2: Dependency stage (installs Python deps, cached by lockfile)
FROM base AS deps-stage

# Install ML system dependencies for PyTorch
# Build tools needed for compiling some packages from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

ARG INCLUDE_DEV

# Copy metadata needed to resolve dependencies without invalidating cache on app edits
COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install ML (and optional dev) dependencies using uv with cache mounts for wheels
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

# Stage 2b: Core-only stage (without ML)
FROM base AS core-stage

# Copy metadata needed to resolve dependencies without invalidating cache on app edits
COPY pyproject.toml ./
COPY uv.lock ./
COPY truthgraph/__init__.py ./truthgraph/__init__.py

# Install core dependencies only (no ML)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system .

# Stage 3: Runtime stage
FROM base AS runtime

WORKDIR /app

# Copy dependency layers from the deps stage
COPY --from=deps-stage /usr/local /usr/local
COPY --from=deps-stage /root/.local /root/.local

# Copy application metadata and source
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock

# Copy application code
COPY truthgraph ./truthgraph

# Copy Alembic migration files
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Copy tests for development/testing
# Updated: 2025-10-30 - Fixed SQL assertion in test_top_k_parameter
COPY tests ./tests

# Copy performance scripts for benchmarking and optimization
# Updated: 2025-10-30 - Fixed database connection issues
COPY scripts ./scripts

# Install the application package without touching dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv pip install --system --no-deps .

# Runtime-only setup
RUN mkdir -p /root/.cache/huggingface && \
    useradd -m -u 1000 appuser || true

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Python path for module resolution
    PYTHONPATH=/app \
    # ML model caching
    HF_HOME=/root/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface

# Expose API port
EXPOSE 8000

# Health check endpoint
# Waits longer on first run for ML model loading
# Subsequent runs use cached models (faster)
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with Uvicorn
# --reload enabled for development (set PYTHONUNBUFFERED for live logs)
CMD ["python", "-m", "uvicorn", \
    "truthgraph.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--reload"]
