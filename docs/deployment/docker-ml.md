# Docker ML Services Setup Guide

## Overview

TruthGraph Phase 2 includes ML services for semantic search and natural language inference. This guide covers Docker configuration for development and production deployments.

### What's Included

- **FastAPI Backend**: Python 3.12 with ML support
- **PostgreSQL + pgvector**: Semantic search database
- **Sentence-Transformers**: all-MiniLM-L6-v2 embeddings (384-dim)
- **DeBERTa-v3-base**: Natural language inference (NLI)
- **Model Caching**: Automatic download and persistent cache

### Key Statistics

| Component | Size | Memory | Load Time |
|-----------|------|--------|-----------|
| Sentence-Transformers | ~80 MB | ~400 MB | ~2s (first), <100ms (cached) |
| DeBERTa-v3-base | ~440 MB | ~700 MB | ~5s (first), <500ms (cached) |
| Total Runtime | ~520 MB | ~1.1 GB | ~7s (first), <1s (cached) |
| Headroom (4GB limit) | N/A | ~2.9 GB | — |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- 4 GB RAM available (2 GB minimum)
- 2 GB disk space for model cache
- Internet connection (for first startup)

### Basic Setup (CPU)

```bash
# 1. Navigate to repository
cd truthgraph

# 2. Create necessary directories
mkdir -p .volumes/postgres .volumes/models

# 3. Start services
docker-compose up

# 4. Initial startup (~1-2 minutes)
# Models download automatically on first run
# Subsequent starts use cached models (<10s)

# 5. Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI
```

### Environment Setup

Create `.env` file for custom configuration:

```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# ML Model Cache (advanced)
# TRANSFORMERS_OFFLINE=1  # Use only cached models
# TORCH_NUM_THREADS=4     # Parallel processing threads
```

## Docker Architecture

### Multi-Stage Build

The `docker/api.Dockerfile` uses multi-stage builds for optimization:

```text
Stage 1 (base): Core system dependencies
    ↓
Stage 2a (ml-stage): ML dependencies (torch, transformers)
    OR
Stage 2b (core-stage): Core only (FastAPI, database drivers)
    ↓
Stage 3 (runtime): Final image with application code
```

**Benefits**:
- Smaller final images (only runtime dependencies)
- Faster rebuilds with cached base layers
- Flexibility to build with/without ML

### Build Arguments

```bash
# Build with ML support (default)
docker-compose build --build-arg INCLUDE_ML=true

# Build without ML (for testing core features)
docker-compose build --build-arg INCLUDE_ML=false
```

## Model Cache Management

### Cache Location

Models are stored in a named volume to persist across restarts:

```text
.volumes/models/
├── models--sentence-transformers--all-MiniLM-L6-v2/
│   └── snapshots/...
└── models--microsoft--deberta-v3-base/
    └── snapshots/...
```

### First Startup Sequence

1. Container starts with empty cache
2. Health check waits for API initialization (60s timeout)
3. API loads, detects missing models
4. Models download from Hugging Face (requires internet)
5. Models saved to cache volume
6. Subsequent restarts skip download (< 1s)

### Troubleshooting Cache

**Problem**: Models re-downloading on every startup

```bash
# Solution: Verify volume is mounted
docker inspect truthgraph-api | grep -A 20 Mounts

# Expected output should show:
# "Source": ".../truthgraph/.volumes/models",
# "Destination": "/root/.cache/huggingface"
```

**Problem**: Cache taking too much disk space

```bash
# Clean up old model versions
rm -rf .volumes/models/

# Note: Will require re-download on next startup (~2 min)
```

## GPU Support

### Model Prerequisites

1. NVIDIA GPU (Compute Capability 5.0+)
2. NVIDIA Docker runtime

```bash
# Install NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

1. Verify GPU support

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi
```

### Running with GPU

```bash
# Use GPU override compose file
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up

# Monitor GPU usage
nvidia-smi  # Run on host
docker exec truthgraph-api nvidia-smi  # From inside container
```

### GPU Performance

| Operation | CPU | GPU | Speedup |
|-----------|-----|-----|---------|
| Embed 100 texts | ~200ms | ~50ms | 4x |
| NLI 10 pairs | ~5s | ~500ms | 10x |
| Pipeline (10 claims) | ~60s | ~15s | 4x |

### Troubleshooting GPU

**GPU not detected in container**:

```bash
# Check host GPU
nvidia-smi

# Rebuild image for GPU
docker-compose build --build-arg INCLUDE_ML=true

# Force GPU in container
docker run -it --gpus all truthgraph-api nvidia-smi
```

## Health Checks

### Health Endpoint

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

### Docker Health Check

```bash
# Check service health
docker-compose ps

# Should show: truthgraph-api    Up (healthy)

# Manual health check
docker exec truthgraph-api curl localhost:8000/health
```

### Extended Startup Period

The API requires extra time on first startup:

```yaml
healthcheck:
  start_period: 60s  # Allow 60s for model loading
```

After initial startup, models cache locally and subsequent starts complete in < 1s.

## Memory Management

### Memory Limits

Default docker-compose configuration:

```yaml
api:
  deploy:
    resources:
      limits:
        memory: 4G      # Hard limit
      reservations:
        memory: 2G      # Soft limit (for placement)
```

### Memory Breakdown

At runtime with cached models:

- Base OS: ~50 MB
- Python + dependencies: ~150 MB
- Sentence-Transformers (loaded): ~400 MB
- DeBERTa-v3 (loaded): ~700 MB
- Application + buffers: ~100-200 MB
- **Total: ~1.4-1.5 GB** (well under 4 GB limit)

### OOM Prevention

If you see memory errors:

```bash
# Option 1: Increase limit
# Edit docker-compose.yml, set memory: 6G

# Option 2: Reduce batch size in code
# Edit embeddings.py, set batch_size=16 (from 32)

# Option 3: Enable swapping (slower)
# Not recommended for production
```

## Resource Limits

### CPU Configuration

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: "2.0"  # Limit to 2 CPU cores
```

### Recommendations

- **Development**: No limit (use all cores)
- **Production**: Limit to 2-4 cores per service
- **ML batch sizes**:
  - 1-2 cores: batch_size=16
  - 2-4 cores: batch_size=32
  - 4+ cores: batch_size=64

## Production Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production` (if using Flask)
- [ ] Disable `--reload` flag in CMD
- [ ] Use proper secret management (not .env file)
- [ ] Configure resource limits
- [ ] Enable persistent volumes
- [ ] Set up monitoring and logging
- [ ] Test with actual data volumes
- [ ] Implement backup strategy

### Production Configuration

```yaml
api:
  environment:
    LOG_LEVEL: INFO
    # No --reload in CMD for production
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: "4"  # Based on your hardware
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
```

### Docker Compose Production

```bash
# Use production compose file (without hot reload)
docker-compose -f docker-compose.yml \
               -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose logs -f api

# Restart services
docker-compose restart

# Graceful shutdown
docker-compose down  # 10s timeout before kill
```

## Layer Caching Optimization

### Build Performance

The multi-stage Dockerfile optimizes build times:

```text
First build:     ~5-10 minutes (downloads, installs ML deps)
Subsequent builds: ~30-60 seconds (reuses cached layers)
```

### Cache Invalidation

Rebuild is triggered when:

- `pyproject.toml` changes (dependency updates)
- Files in `truthgraph/` directory change
- `Dockerfile` itself changes

### Fast Builds

```bash
# Only rebuild if code changed (dependencies cached)
docker-compose build --no-cache=false

# Force rebuild (invalidates all caches)
docker-compose build --no-cache
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Port already in use: netstat -an | grep 8000
# 2. Insufficient disk space: df -h
# 3. Database not healthy: docker-compose logs postgres
```

### Models Not Downloading

```bash
# Check internet connection
docker exec truthgraph-api curl https://huggingface.co

# Check disk space (models need ~1GB)
df -h .volumes/

# Manual model cache warm-up
docker exec truthgraph-api python -c \
  "from sentence_transformers import SentenceTransformer; \
   SentenceTransformer('all-MiniLM-L6-v2')"
```

### High Memory Usage

```bash
# Check memory consumption
docker stats truthgraph-api

# Profile with memory tools
docker exec truthgraph-api python -m memory_profiler api_code.py
```

### Slow Performance

```bash
# Check CPU usage
docker stats

# Check if GPU is being used
docker exec truthgraph-api nvidia-smi

# Profile with cProfile
docker exec truthgraph-api python -m cProfile -s cumtime
```

## Development Workflows

### Local Development

```bash
# Start only database
docker-compose up postgres

# Run API locally (not in container)
cd truthgraph
python -m uvicorn main:app --reload

# Benefits: Faster iteration, better debugging
```

### Hot Reload

```bash
# Mount source code for hot reload
volumes:
  - ./truthgraph:/app/truthgraph:ro

# Changes to Python files reload automatically
# Note: Dependency changes still require rebuild
```

### Testing

```bash
# Run tests in container
docker-compose run --rm api pytest

# Run specific test file
docker-compose run --rm api pytest tests/unit/test_embeddings.py

# Run with coverage
docker-compose run --rm api pytest --cov=truthgraph
```

## Monitoring and Logging

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs api

# Follow logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Container Metrics

```bash
# CPU, memory, network stats
docker stats

# Detailed inspection
docker inspect truthgraph-api
```

### Health Monitoring

```bash
# Check service health
docker-compose ps

# Manual health check
docker exec truthgraph-api curl -f http://localhost:8000/health

# Check all endpoints
docker exec truthgraph-api curl http://localhost:8000/docs
```

## Security Best Practices

### Running as Non-Root

The Dockerfile includes non-root user creation:

```dockerfile
useradd -m -u 1000 appuser
# Note: Currently still runs as root for development
```

### Secret Management

Never commit secrets to version control:

```bash
# Create .env.local (ignored by git)
echo "POSTGRES_PASSWORD=my_secure_password" > .env.local

# Use only in development
# For production: use Docker secrets, Kubernetes secrets, etc.
```

### Image Scanning

```bash
# Scan for vulnerabilities
docker scan truthgraph-api

# Check dependencies
docker run -it truthgraph-api pip audit
```

## Further Reading

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [PyTorch Deployment](https://pytorch.org/docs/stable/deployment.html)
- [Hugging Face Model Loading](https://huggingface.co/docs/transformers/model_doc/auto)
- [PostgreSQL + pgvector](https://github.com/pgvector/pgvector)
- [NVIDIA Docker](https://github.com/NVIDIA/nvidia-docker)

## Support

For issues or questions:

1. Check logs: `docker-compose logs api`
2. Review this guide
3. Check [Phase 2 Implementation Plan](../PHASE_2_IMPLEMENTATION_PLAN.md)
4. Open an issue on GitHub

---

**Last Updated**: 2025-10-25
**Version**: 1.0
**For**: TruthGraph v0 Phase 2
