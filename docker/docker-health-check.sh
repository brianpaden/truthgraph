#!/bin/bash
# TruthGraph Docker Health Check Script
# Validates running services and tests endpoints
# Usage: ./docker/docker-health-check.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$PROJECT_DIR/docker-health-check-${TIMESTAMP}.log"

echo "TruthGraph Docker Health Check"
echo "==============================="
echo "Log file: $LOG_FILE"
echo ""

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local max_retries=${3:-5}
    local retry_count=0

    log "Checking $name: $url"

    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log "  ✓ $name is responsive"
            return 0
        fi

        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            log "  ! Retry $retry_count/$max_retries (waiting 5s)..."
            sleep 5
        fi
    done

    log "  ✗ $name is not responding"
    return 1
}

# Test 1: Check Docker daemon
log "Test 1: Checking Docker daemon..."
if docker ps > /dev/null 2>&1; then
    log "✓ Docker daemon is running"
else
    log "✗ Docker daemon is not accessible"
    exit 1
fi

# Test 2: Check running services
log ""
log "Test 2: Checking running services..."
cd "$PROJECT_DIR"

SERVICES=("postgres" "api" "frontend")
for service in "${SERVICES[@]}"; do
    if docker-compose ps $service 2>/dev/null | grep -q "Up"; then
        log "  ✓ $service is running"
    else
        log "  ! $service is not running (this is OK if just starting)"
    fi
done

# Test 3: Check PostgreSQL connectivity
log ""
log "Test 3: Checking PostgreSQL health..."
POSTGRES_CONTAINER=$(docker-compose ps -q postgres 2>/dev/null || echo "")

if [ -z "$POSTGRES_CONTAINER" ]; then
    log "  ! PostgreSQL container not found (service may not be running)"
else
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U truthgraph > /dev/null 2>&1; then
        log "  ✓ PostgreSQL is healthy"

        # Check pgvector extension
        if docker exec "$POSTGRES_CONTAINER" psql -U truthgraph -d truthgraph -c "SELECT extname FROM pg_extension WHERE extname='vector';" > /dev/null 2>&1; then
            log "  ✓ pgvector extension is installed"
        else
            log "  ! pgvector extension not loaded"
        fi
    else
        log "  ✗ PostgreSQL is not responding"
    fi
fi

# Test 4: Check API health
log ""
log "Test 4: Checking API service health..."
if check_endpoint "http://localhost:8000/health" "API health endpoint" 10; then
    log "  API is ready for requests"
else
    log "  ! API may still be initializing"
fi

# Test 5: Check API endpoints
log ""
log "Test 5: Testing API endpoints..."
if check_endpoint "http://localhost:8000/docs" "API Swagger docs"; then
    log "  ✓ Swagger documentation is available at http://localhost:8000/docs"
fi

if check_endpoint "http://localhost:8000/openapi.json" "API OpenAPI schema"; then
    log "  ✓ OpenAPI schema is available"
fi

# Test 6: Check resource usage
log ""
log "Test 6: Checking resource usage..."
if command -v docker stats &> /dev/null; then
    log "Current container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" | tee -a "$LOG_FILE"
else
    log "docker stats not available (Windows might need different approach)"
fi

# Test 7: Check volume mounts
log ""
log "Test 7: Validating volume mounts..."
API_CONTAINER=$(docker-compose ps -q api 2>/dev/null || echo "")

if [ -n "$API_CONTAINER" ]; then
    log "Checking volume mounts in API container:"
    docker inspect "$API_CONTAINER" --format='{{range .Mounts}}{{println .Source "→" .Destination}}{{end}}' | tee -a "$LOG_FILE"
else
    log "! API container not found"
fi

# Test 8: Check disk usage
log ""
log "Test 8: Checking disk usage..."
log "Volume directory sizes:"
du -sh "$PROJECT_DIR/.volumes"/* 2>/dev/null | tee -a "$LOG_FILE" || log "  (volumes directory not yet populated)"

# Test 9: Check model cache
log ""
log "Test 9: Checking ML model cache..."
MODEL_CACHE="$PROJECT_DIR/.volumes/models"

if [ -d "$MODEL_CACHE" ]; then
    CACHE_SIZE=$(du -sh "$MODEL_CACHE" 2>/dev/null | cut -f1)
    log "✓ Model cache directory exists"
    log "  Cache size: $CACHE_SIZE"

    if [ -d "$MODEL_CACHE/models--sentence-transformers--all-MiniLM-L6-v2" ]; then
        log "  ✓ Sentence-Transformers model is cached"
    else
        log "  ! Sentence-Transformers model not yet cached (will download on first use)"
    fi

    if [ -d "$MODEL_CACHE/models--microsoft--deberta-v3-base" ]; then
        log "  ✓ DeBERTa model is cached"
    else
        log "  ! DeBERTa model not yet cached (will download on first use)"
    fi
else
    log "! Model cache directory not found (will be created on startup)"
fi

# Test 10: Check logs for errors
log ""
log "Test 10: Checking service logs for errors..."
API_CONTAINER=$(docker-compose ps -q api 2>/dev/null || echo "")

if [ -n "$API_CONTAINER" ]; then
    ERROR_COUNT=$(docker logs "$API_CONTAINER" 2>&1 | grep -i "error" | wc -l)
    if [ $ERROR_COUNT -eq 0 ]; then
        log "  ✓ No errors found in API logs"
    else
        log "  ! Found $ERROR_COUNT error messages in logs"
        log "Last 5 error lines:"
        docker logs "$API_CONTAINER" 2>&1 | grep -i "error" | tail -5 | tee -a "$LOG_FILE"
    fi
fi

# Test 11: Check environment variables
log ""
log "Test 11: Verifying environment configuration..."
API_CONTAINER=$(docker-compose ps -q api 2>/dev/null || echo "")

if [ -n "$API_CONTAINER" ]; then
    log "API environment variables related to ML:"
    docker exec "$API_CONTAINER" env | grep -E "(HF_HOME|TRANSFORMERS|TORCH|MODEL|CUDA)" || log "  (none found or container not ready)"
fi

# Summary
log ""
log "==============================="
log "Health Check Summary"
log "==============================="

# Get service statuses
POSTGRES_HEALTH=$(docker-compose ps postgres 2>/dev/null | grep -c "healthy" || echo "0")
API_HEALTH=$(docker-compose ps api 2>/dev/null | grep -c "healthy" || echo "0")
FRONTEND_HEALTH=$(docker-compose ps frontend 2>/dev/null | grep -c "Up" || echo "0")

if [ "$POSTGRES_HEALTH" -gt 0 ]; then
    log "✓ PostgreSQL: Healthy"
else
    log "! PostgreSQL: Not healthy"
fi

if [ "$API_HEALTH" -gt 0 ]; then
    log "✓ API: Healthy"
else
    log "! API: Not healthy (may still be initializing)"
fi

if [ "$FRONTEND_HEALTH" -gt 0 ]; then
    log "✓ Frontend: Running"
else
    log "! Frontend: Not running"
fi

log ""
log "Next steps:"
log "1. View full logs: docker-compose logs -f api"
log "2. Test API: curl http://localhost:8000/health"
log "3. Access Swagger UI: http://localhost:8000/docs"
log ""
log "Health check complete! Log saved to: $LOG_FILE"
