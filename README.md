# TruthGraph v0

**Local-first fact-checking system with semantic search and natural language inference**

## Quick Start

### With Docker (Recommended)

```bash
# Start all services
docker-compose up

# View logs
docker-compose logs -f api

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

See [Docker Setup Guide](./docs/deployment/docker-setup-guide.md) for detailed setup instructions.

### With GPU (Optional)

```bash
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

Requires NVIDIA Docker runtime. See [GPU Setup Guide](./docs/deployment/docker-ml.md#gpu-support).

## What's Included

- **API Backend**: FastAPI with Python 3.12
- **Database**: PostgreSQL 16 with pgvector for semantic search
- **ML Services**: Sentence embeddings and NLI verification
- **Frontend**: Flask + htmx (server-side rendered UI)
- **Model Caching**: Automatic model download and persistence

## Architecture

```
TruthGraph v0 Stack
├── PostgreSQL 16 + pgvector (port 5432)
├── FastAPI Backend with ML (port 8000)
├── Flask Frontend (port 5000)
└── Optional: React Frontend (port 5173)
```

### Phase 2: ML Services (CURRENT)

Phase 2 implements core ML capabilities for claim verification:

- **Embedding Generation**: all-MiniLM-L6-v2 for semantic search
- **NLI Verification**: DeBERTa-v3-base for verdict prediction
- **Vector Search**: pgvector integration for evidence retrieval
- **Verdict Aggregation**: Confidence-based verdict scoring

See [Phase 2 Plan](./planning/phases/phase_2/plan.md) for details.

## Documentation

### Quick Links
- **[Documentation Hub](./docs/README.md)** - Complete documentation index
- **[Planning & Roadmap](./planning/README.md)** - Active planning and features
- **[Archive](./archive/README.md)** - Completed features and history

### Deployment
- [Docker Deployment Guide](./docs/deployment/docker.md) - Main deployment guide
- [Docker Setup Guide](./docs/deployment/docker-setup-guide.md) - Setup instructions
- [Docker ML Setup](./docs/deployment/docker-ml.md) - Comprehensive ML configuration
- [Docker Quick Checklist](./docs/guides/quickstart/docker-checklist.md) - Quick reference

### Development
- [Developer Guide](./docs/guides/developer-guide.md) - Development guide
- [API Quick Reference](./docs/guides/api-quick-reference.md) - API reference
- [API Documentation](http://localhost:8000/docs) - Swagger UI (after startup)

### Phase 2
- [Phase 2 Plan](./planning/phases/phase_2/plan.md) - Full feature breakdown
- [Phase 2 Quick Reference](./planning/phases/phase_2/quick-reference.md) - Quick lookup
- [Phase 2 README](./planning/phases/phase_2/README.md) - Navigation hub

## System Requirements

- **Docker & Docker Compose**: For containerized deployment
- **Python 3.12+**: For local development
- **4 GB RAM**: Minimum (with 2+ GB headroom)
- **2 GB Disk Space**: For ML model cache
- **Internet**: For first-time model download

## Key Metrics

| Metric | Value |
|--------|-------|
| Build Time (first) | ~5-10 min |
| Build Time (cached) | ~1 min |
| Memory Usage (api) | ~1.4-1.5 GB |
| Model Cache Size | ~520 MB |
| Startup Time (first) | ~2-3 min |
| Startup Time (cached) | <1s |
| API Latency (health) | <100ms |

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme

# API
API_PORT=8000
LOG_LEVEL=INFO

# ML (optional)
TORCH_NUM_THREADS=4
```

## Health Checks

```bash
# API health
curl http://localhost:8000/health

# Service status
docker-compose ps

# Full validation
bash docker/docker-health-check.sh
```

## Troubleshooting

### Models not downloading
```bash
# Check internet connection
docker exec truthgraph-api curl https://huggingface.co

# Check disk space
df -h .volumes/
```

### High memory usage
```bash
# Monitor real-time
docker stats

# Check limits
docker-compose config | grep memory
```

### GPU not detected
```bash
# Verify NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime nvidia-smi
```

See [Troubleshooting Guide](./docs/deployment/docker-ml.md#troubleshooting) for more.

## Development

### Local Setup

```bash
# Start only database
docker-compose up postgres

# Run API locally
cd truthgraph
python -m uvicorn main:app --reload
```

### Testing

```bash
# Run all tests
docker-compose run --rm api pytest

# With coverage
docker-compose run --rm api pytest --cov=truthgraph
```

## Performance

### Typical Latencies

| Operation | CPU | GPU |
|-----------|-----|-----|
| Embed text | ~2ms | <1ms |
| NLI inference | ~500ms | ~50ms |
| Evidence search | <3s | <1s |
| Pipeline (10 claims) | ~60s | ~15s |

## Production Deployment

1. **Set secure credentials** in `.env.production`
2. **Configure resource limits** in `docker-compose.yml`
3. **Enable monitoring** (logs, metrics, health)
4. **Test with production data**
5. **Set up backups** for PostgreSQL

See [Production Guide](./docs/deployment/docker.md#production-deployment) for details.

## Support

- Check logs: `docker-compose logs api`
- Run health check: `bash docker/docker-health-check.sh`
- Review guides: [Documentation Hub](./docs/README.md)
- Open an issue on GitHub

## Next Steps

- [ ] Start services: `docker-compose up`
- [ ] Test API: `curl http://localhost:8000/health`
- [ ] View docs: http://localhost:8000/docs
- [ ] Submit claims via API
- [ ] Review Phase 2 features

## License

Apache 2.0
