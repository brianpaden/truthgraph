# TruthGraph v0 API Dockerfile
# Python 3.12 with uv package manager

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy project files for installation
COPY pyproject.toml ./
COPY truthgraph ./truthgraph

# Install Python dependencies using uv
RUN /root/.local/bin/uv pip install --system --no-cache .

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "truthgraph.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
