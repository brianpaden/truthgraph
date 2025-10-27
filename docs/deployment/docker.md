# TruthGraph Docker Deployment Guide

## Quick Reference

### Start Services

```bash
# Basic startup (CPU)
docker-compose up

# With GPU support
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up

# Background
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Stop Services

```bash
# Graceful shutdown
docker-compose down

# Remove volumes
docker-compose down -v
```

### Health Check

```bash
# Quick health check
curl http://localhost:8000/health

# Full validation script
bash docker/docker-health-check.sh
```

## Architecture Overview

### Service Stack

```
TruthGraph v0 with ML Services
├── PostgreSQL 16 + pgvector
│   └── Port: 5432
│   └── Volume: .volumes/postgres
├── FastAPI Backend (ML-enabled)
│   └── Port: 8000
│   └── Volume: .volumes/models (model cache)
└── Frontend (Flask + htmx)
    └── Port: 5000
```

### Key Features

- **Multi-stage Docker build**: Optimized layer caching
- **ML model caching**: Persistent across container restarts
- **GPU support**: Optional NVIDIA GPU acceleration
- **Health checks**: Automatic service monitoring
- **Resource limits**: Memory and CPU constraints
- **Development-friendly**: Hot reload and debugging

## Model Details

### Included Models

| Model | Purpose | Size | Memory | Load Time |
|-------|---------|------|--------|-----------|
| all-MiniLM-L6-v2 | Text embeddings (384-dim) | ~80 MB | ~400 MB | ~2s |
| deberta-v3-base | Natural Language Inference | ~440 MB | ~700 MB | ~5s |

### First Startup

1. Container initializes (< 1s)
2. API starts, detects missing models
3. Models download from Hugging Face (~2-3 min)
4. Models save to cache volume
5. Health check passes
6. Ready for requests

Subsequent starts use cached models (< 1s startup).

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=your_secure_password

# API
API_PORT=8000
LOG_LEVEL=INFO

# ML (advanced)
TORCH_NUM_THREADS=4
# TRANSFORMERS_OFFLINE=1  # Use only cached models
```

### Resource Limits

Edit `docker-compose.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        memory: 4G          # Adjust based on available RAM
        cpus: "2.0"         # Number of CPU cores
      reservations:
        memory: 2G          # Soft limit
```

## Building

### Build with ML Support (Default)

```bash
# Automatic (via docker-compose)
docker-compose build

# Manual build
docker build -f docker/api.Dockerfile -t truthgraph-api .
```

**Build time**: ~5-10 minutes (first), ~1 minute (cached)

### Build Without ML (Testing)

```bash
docker build --build-arg INCLUDE_ML=false \
  -f docker/api.Dockerfile \
  -t truthgraph-api:core .
```

**Build time**: ~2-3 minutes

### Build Arguments

- `INCLUDE_ML=true|false`: Include torch, transformers (default: true)

### Image Sizes

- With ML: ~3.5 GB (after extraction)
- Core only: ~1.2 GB
- Difference: ~2.3 GB for ML dependencies

## GPU Support

### Prerequisites

1. NVIDIA GPU (Compute Capability 5.0+)
2. NVIDIA Docker runtime installed
3. NVIDIA Docker Compose plugin

### Installation

```bash
# Install nvidia-docker (Ubuntu/Debian)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi
```

### Running with GPU

```bash
# Use GPU override file
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up

# Monitor GPU
nvidia-smi
docker exec truthgraph-api nvidia-smi
```

### Performance

GPU provides ~4-10x speedup:

| Operation | CPU | GPU | Speedup |
|-----------|-----|-----|---------|
| Embed 100 texts | ~200ms | ~50ms | 4x |
| NLI 10 pairs | ~5s | ~500ms | 10x |

## Memory Management

### Memory Usage

At runtime with loaded models:

```
Base OS:              ~50 MB
Python:               ~150 MB
Sentence-Transformers: ~400 MB
DeBERTa:              ~700 MB
Application:          ~100-200 MB
─────────────────────────────
Total:                ~1.4-1.5 GB
Available (4GB limit): ~2.5 GB
```

### OOM Prevention

If experiencing out-of-memory errors:

```bash
# Option 1: Increase limit
# Edit docker-compose.yml, set memory: 6G

# Option 2: Reduce batch sizes
# In code: batch_size=16 (from 32)

# Option 3: Enable memory profiling
docker exec truthgraph-api python -m memory_profiler script.py
```

## Health Checks

### API Health Endpoint

```bash
# Quick check
curl http://localhost:8000/health

# With details
curl http://localhost:8000/health | jq .
```

### Service Status

```bash
# All services
docker-compose ps

# Specific service
docker-compose ps api

# Detailed status
docker-compose ls
```

### Extended Startup

The API health check has an extended startup period to allow ML model loading:

```yaml
healthcheck:
  start_period: 60s  # 60 seconds for first-time model loading
```

This doesn't affect subsequent starts (cached models load in < 1s).

## Volumes and Persistence

### Volume Structure

```
.volumes/
├── postgres/          # PostgreSQL data
│   └── (database files)
└── models/            # ML model cache
    ├── models--sentence-transformers--all-MiniLM-L6-v2/
    └── models--microsoft--deberta-v3-base/
```

### Cleanup

```bash
# Remove containers but keep volumes
docker-compose down

# Remove everything including volumes
docker-compose down -v

# Clean unused images
docker image prune

# Full cleanup (careful!)
docker system prune -a
```

## Development Workflow

### Hot Reload

The API source code is mounted with hot reload:

```yaml
volumes:
  - ./truthgraph:/app/truthgraph:ro
```

Changes to Python files automatically reload (via --reload flag).

**Note**: Dependency changes require container rebuild.

### Local Development

```bash
# Option 1: Docker for database only
docker-compose up postgres
# Then run API locally:
cd truthgraph && python -m uvicorn main:app --reload

# Option 2: Full Docker stack
docker-compose up

# Option 3: Docker with debugging
docker-compose run --rm api python -m pdb truthgraph/main.py
```

### Testing

```bash
# Run all tests
docker-compose run --rm api pytest

# Run specific test
docker-compose run --rm api pytest tests/unit/test_embeddings.py

# With coverage
docker-compose run --rm api pytest --cov=truthgraph
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Port in use: netstat -an | grep 8000
# 2. No disk space: df -h
# 3. Docker daemon issues: docker ps
```

### Models Not Downloading

```bash
# Check internet connectivity
docker exec truthgraph-api curl https://huggingface.co

# Check disk space (need ~1GB)
du -sh .volumes/models

# Manual download
docker exec truthgraph-api python -c \
  "from sentence_transformers import SentenceTransformer; \
   SentenceTransformer('all-MiniLM-L6-v2')"
```

### High Memory Usage

```bash
# Check memory stats
docker stats

# Profile memory
docker exec truthgraph-api python -m memory_profiler script.py

# Check for memory leaks
docker logs api | grep -i "memory"
```

### API Unresponsive

```bash
# Check if container is running
docker-compose ps api

# Check logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Check health endpoint
curl -v http://localhost:8000/health
```

### GPU Not Detected

```bash
# Check host GPU
nvidia-smi

# Check container GPU access
docker exec truthgraph-api nvidia-smi

# Verify docker-compose.gpu.yml is used
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml ps
```

## Monitoring and Logging

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs api

# Follow in real-time
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# With timestamps
docker-compose logs --timestamps api
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Memory usage
docker stats --no-stream | grep truthgraph

# Network usage
docker-compose logs api | grep -i "request"
```

### Health Monitoring

```bash
# Container health status
docker ps --format "{{.Names}}\t{{.Status}}"

# Manual health check
docker exec truthgraph-api curl -f http://localhost:0.0.0.0:8000/health

# Check startup logs
docker logs truthgraph-api | head -50
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Use `.env` with secure credentials (not default)
- [ ] Set `LOG_LEVEL=WARNING` (not INFO/DEBUG)
- [ ] Disable `--reload` flag in production
- [ ] Enable resource limits
- [ ] Set up monitoring and alerting
- [ ] Test with production data volumes
- [ ] Configure backup strategy
- [ ] Document deployment procedure

### Production Configuration

```yaml
api:
  environment:
    LOG_LEVEL: WARNING
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: "4"
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
```

### Docker in Production

```bash
# Remove --reload flag from CMD
# Use health checks with extended timeouts
# Configure resource limits
# Set up log drivers (syslog, splunk, etc.)
# Enable auto-restart on failure
# Use named volumes for persistence
```

## Advanced Configuration

### Custom Dockerfile

Extend the provided Dockerfile:

```dockerfile
FROM truthgraph-api:latest

# Add custom dependencies
RUN apt-get install -y your-package

# Add custom code
COPY custom-module ./custom-module
```

### Multi-stage Builds

The Dockerfile uses multi-stage builds:

1. **base**: Core dependencies
2. **ml-stage**: ML dependencies (optional)
3. **core-stage**: Core only (lighter image)
4. **runtime**: Final image

### Layer Caching

To maximize cache hits:

1. Change infrequently (system deps) → Change rarely (dependencies) → Change often (code)
2. Use .dockerignore to exclude unnecessary files
3. Minimize layer count

## Performance Tuning

### Build Optimization

```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker build .

# Use cache
docker build --cache-from truthgraph-api:latest .

# Check layer caching
docker history truthgraph-api
```

### Runtime Optimization

```bash
# Tune batch sizes in code
# Embeddings: 32-64 (CPU), 128+ (GPU)
# NLI: 8-16 (CPU), 32+ (GPU)

# Set thread count
export TORCH_NUM_THREADS=4

# Enable offline mode (after initial cache)
export TRANSFORMERS_OFFLINE=1
```

## Security Best Practices

### Secrets Management

```bash
# Don't commit secrets
echo "POSTGRES_PASSWORD=secret" > .env.local

# Use Docker secrets (Swarm)
echo "password" | docker secret create db_password -

# Or environment files
docker run --env-file .env.prod truthgraph-api
```

### Image Scanning

```bash
# Scan for vulnerabilities
docker scan truthgraph-api

# Check dependencies
docker run truthgraph-api pip audit

# Find outdated packages
docker run truthgraph-api pip list --outdated
```

### Non-root User

The Dockerfile includes non-root user creation (commented):

```dockerfile
useradd -m -u 1000 appuser
# Note: Currently runs as root for development
```

## Further Reading

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [NVIDIA Docker](https://github.com/NVIDIA/nvidia-docker)
- [ML Model Deployment](./docs/DOCKER_ML_SETUP.md)

## Support

For issues or questions:

1. Check [Docker ML Setup Guide](./docs/DOCKER_ML_SETUP.md)
2. Review [Phase 2 Implementation Plan](./PHASE_2_IMPLEMENTATION_PLAN.md)
3. Check logs: `docker-compose logs api`
4. Run health check: `bash docker/docker-health-check.sh`

---

**Last Updated**: 2025-10-25
**Version**: 1.0
**For**: TruthGraph v0 Phase 2
