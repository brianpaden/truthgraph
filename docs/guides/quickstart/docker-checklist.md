# Docker Quick Checklist

## Pre-Start Checklist

- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] 4 GB RAM available
- [ ] 2 GB disk space available
- [ ] Internet connection (for first model download)
- [ ] Port 5432 available (PostgreSQL)
- [ ] Port 8000 available (API)
- [ ] Port 5000 available (Frontend, optional)

## First-Time Setup

- [ ] Clone/navigate to truthgraph directory
- [ ] Create volume directories:
  ```bash
  mkdir -p .volumes/postgres .volumes/models
  ```
- [ ] Create .env file (optional):
  ```bash
  cp .env.example .env  # or create manually
  ```
- [ ] Validate configuration:
  ```bash
  docker-compose config
  ```

## Starting Services

- [ ] Start all services:
  ```bash
  docker-compose up
  ```
- [ ] Wait for PostgreSQL health check (first message)
- [ ] Wait for API initialization (~2-3 min on first run)
- [ ] Wait for models to download and cache
- [ ] Verify services are healthy:
  ```bash
  docker-compose ps
  # All should show "Up" or "Up (healthy)"
  ```

## Verification

- [ ] Check API health:
  ```bash
  curl http://localhost:8000/health
  # Should return: {"status": "healthy"}
  ```
- [ ] View Swagger UI:
  ```
  http://localhost:8000/docs
  ```
- [ ] Check database connection:
  ```bash
  docker-compose logs postgres | grep "ready to accept"
  ```
- [ ] Verify model cache:
  ```bash
  ls -la .volumes/models/
  # Should contain model directories after first startup
  ```

## Common Tasks

### View Logs
```bash
docker-compose logs -f api              # Follow API logs
docker-compose logs postgres            # Database logs
docker-compose logs --tail=100 api      # Last 100 lines
```

### Check Service Health
```bash
docker-compose ps                       # Service status
docker stats                            # Resource usage
docker exec truthgraph-api curl -f http://localhost:8000/health
```

### Restart Services
```bash
docker-compose restart api              # Restart API
docker-compose restart                  # Restart all
docker-compose down && docker-compose up  # Full restart
```

### Stop Services
```bash
docker-compose down                     # Stop all (keep volumes)
docker-compose down -v                  # Stop and remove volumes
```

### Rebuild Images
```bash
docker-compose build api                # Rebuild API image
docker-compose build                    # Rebuild all
docker-compose build --no-cache api     # Force rebuild
```

## GPU Setup (Optional)

- [ ] Check NVIDIA GPU:
  ```bash
  nvidia-smi
  ```
- [ ] Install nvidia-docker:
  ```bash
  # See ../../deployment/docker-ml.md for installation
  ```
- [ ] Verify NVIDIA runtime:
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.1.0-runtime nvidia-smi
  ```
- [ ] Start with GPU:
  ```bash
  docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up
  ```

## Troubleshooting

### Services Won't Start
```bash
docker-compose logs api
# Check for errors, then:
1. Verify ports aren't in use: lsof -i :8000
2. Check disk space: df -h
3. Rebuild images: docker-compose build --no-cache
```

### Models Not Downloading
```bash
# Check internet
docker exec truthgraph-api curl https://huggingface.co

# Check disk space
du -sh .volumes/

# Manual download
docker exec truthgraph-api python -c \
  "from sentence_transformers import SentenceTransformer; \
   SentenceTransformer('all-MiniLM-L6-v2')"
```

### High Memory Usage
```bash
docker stats                            # Check current usage
docker-compose config | grep memory     # Check limits

# If over 4GB:
# 1. Reduce batch sizes in code
# 2. Increase limit: docker-compose.yml memory: 6G
# 3. Clear unused containers: docker system prune -a
```

### API Unresponsive
```bash
docker-compose logs -f api              # View live logs
docker-compose restart api              # Restart
curl -v http://localhost:8000/health    # Test endpoint
```

## Validation Scripts

### Run Build Test
```bash
bash docker/docker-build-test.sh
# Tests: config, Dockerfile, build size, volumes
```

### Run Health Check
```bash
bash docker/docker-health-check.sh
# Tests: services, PostgreSQL, API, cache, resources
```

## Development Tips

### Hot Reload Code Changes
```bash
# Source code is mounted read-only:
# ./truthgraph:/app/truthgraph:ro
# Changes reload automatically via --reload flag
# No container rebuild needed for code changes
```

### Local Development (Without Docker)
```bash
# Start only database
docker-compose up postgres

# Run API locally
cd truthgraph
python -m uvicorn main:app --reload

# Benefits: Faster iteration, better debugging
```

### Run Tests
```bash
docker-compose run --rm api pytest              # All tests
docker-compose run --rm api pytest -v           # Verbose
docker-compose run --rm api pytest --cov=truthgraph  # With coverage
```

### Execute Commands in Container
```bash
docker-compose exec api python -c "print('hello')"  # One-off command
docker-compose run --rm api bash                    # Interactive shell
docker-compose exec api bash                        # Shell in running container
```

## Performance Tuning

### Check Build Time
```bash
time docker-compose build api
# First build: 5-10 min
# Cached build: ~1 min
```

### Monitor Runtime Performance
```bash
docker stats --no-stream
# Check memory usage (should be <2GB)
# Check CPU usage (should be reasonable)
```

### Profile Models
```bash
# Check if models are cached
ls -la .volumes/models/models--*/

# Monitor model loading
docker logs truthgraph-api | grep -i "model\|load\|cache"
```

## Environment Configuration

### Set Environment Variables
```bash
# Create .env file
cat > .env <<EOF
POSTGRES_PASSWORD=your_secure_password
LOG_LEVEL=INFO
TORCH_NUM_THREADS=4
EOF

# Load from environment file
docker-compose --env-file .env.production up
```

### Common Variables
```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# ML
TORCH_NUM_THREADS=4
API_HEALTH_START_PERIOD=60s
```

## Volume Management

### Check Volume Usage
```bash
du -sh .volumes/
du -sh .volumes/models
du -sh .volumes/postgres
```

### Clean Up
```bash
# Remove containers but keep volumes
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove unused volumes
docker volume prune

# Deep clean (warning: removes all Docker data)
docker system prune -a
```

### Backup
```bash
# Backup database volume
docker run --rm -v truthgraph_postgres-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/postgres-backup.tar.gz -C /data .

# Restore
docker run --rm -v truthgraph_postgres-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/postgres-backup.tar.gz -C /data
```

## Security

### Secrets Management
```bash
# Don't commit .env with secrets
echo .env.production >> .gitignore

# Use environment file for sensitive data
export POSTGRES_PASSWORD=your_secure_password
docker-compose up
```

### Image Scanning
```bash
docker scan truthgraph-api
docker run truthgraph-api pip audit
```

### Check Non-Root User
```bash
docker exec truthgraph-api whoami
# Should ideally be 'appuser' (work in progress)
```

## Production Checklist

### Before Deployment
- [ ] Set secure POSTGRES_PASSWORD
- [ ] Configure resource limits
- [ ] Set LOG_LEVEL=WARNING
- [ ] Disable --reload in production CMD
- [ ] Set up monitoring/logging
- [ ] Test backup strategy
- [ ] Security scan images
- [ ] Load test with expected volumes

### Monitoring
```bash
# Set up log aggregation
# Configure health check monitoring
# Enable metrics collection (Prometheus, etc.)
# Set up alerting for resource usage
```

### Operations
```bash
# Regular backup schedule
# Monitor disk usage
# Update images regularly
# Review security advisories
# Track performance metrics
```

## Documentation

### Main References
- [Docker Deployment Guide](../../deployment/docker.md) - Full deployment guide
- [Docker ML Setup](../../deployment/docker-ml.md) - ML configuration guide
- [Docker Implementation Summary](../../../archive/implementation_summaries/docker-implementation-summary.md) - Implementation details
- [Feature 11 Delivery Report](../../../archive/completed_features/feature-11-docker-delivery.md) - Delivery details

### Quick Links
- Docker Compose: https://docs.docker.com/compose/
- Docker Buildx: https://docs.docker.com/build/
- Hugging Face Models: https://huggingface.co/models
- NVIDIA Docker: https://github.com/NVIDIA/nvidia-docker

## Getting Help

1. **Check Logs**
   ```bash
   docker-compose logs api
   ```

2. **Run Health Check**
   ```bash
   bash docker/docker-health-check.sh
   ```

3. **Review Documentation**
   - [Docker Deployment Guide](../../deployment/docker.md#troubleshooting)
   - [Docker ML Setup](../../deployment/docker-ml.md#troubleshooting)

4. **Common Issues**
   - Models not downloading? Check internet + disk space
   - Memory errors? Reduce batch sizes or increase limit
   - GPU not detected? Install nvidia-docker + verify CUDA
   - Port in use? Find process: `lsof -i :8000`

---

**Print this checklist or save as bookmark for quick reference!**

Last Updated: 2025-10-25
