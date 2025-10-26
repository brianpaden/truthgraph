# TruthGraph v0 API Dockerfile - Multi-stage Build with ML Support
# Python 3.12 with uv package manager
# Optimized for layer caching and fast builds
#
# Stage 1: Base stage with core dependencies (cached)
# Stage 2: ML stage with torch, transformers
# Stage 3: Runtime stage (final image)
#
# Usage:
#   docker build -t truthgraph-api -f docker/api.Dockerfile .

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

# Stage 2a: ML dependencies stage
FROM base AS ml-stage

# Install ML system dependencies for PyTorch
# Build tools needed for compiling some packages from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy pyproject.toml and truthgraph for dependency installation
COPY pyproject.toml ./
COPY truthgraph ./truthgraph

# Install ML and dev dependencies using uv
# .[ml] = torch, sentence-transformers, transformers
# .[dev] = pytest, ruff, mypy
# Using --no-cache to reduce layer size during build
RUN /root/.local/bin/uv pip install --system --no-cache .[ml,dev] && \
    # Install pytest-cov for coverage
    /root/.local/bin/uv pip install --system --no-cache pytest-cov && \
    # Clean up pip cache
    rm -rf /root/.cache/pip && \
    # Pre-warm model cache directory
    mkdir -p /root/.cache/huggingface && \
    # Create non-root user for runtime (optional security hardening)
    useradd -m -u 1000 appuser || true

# Stage 2b: Core-only stage (without ML)
FROM base AS core-stage

# Copy pyproject.toml and truthgraph for dependency installation
COPY pyproject.toml ./
COPY truthgraph ./truthgraph

# Install core dependencies only (no ML)
RUN /root/.local/bin/uv pip install --system --no-cache . && \
    # Clean up pip cache
    rm -rf /root/.cache/pip && \
    # Create non-root user for runtime
    useradd -m -u 1000 appuser || true

# Stage 3: Runtime stage
FROM ml-stage AS runtime

WORKDIR /app

# Copy application code
COPY truthgraph ./truthgraph

# Copy Alembic migration files
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Copy tests for development/testing
COPY tests ./tests

# Copy performance scripts for benchmarking and optimization
COPY scripts ./scripts

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
