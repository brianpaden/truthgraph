"""TruthGraph Phase 2 FastAPI Application with ML Integration."""

import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.middleware import (
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RateLimitMonitoringMiddleware,
    RequestIDMiddleware,
)
from .api.ml_routes import router as ml_router
from .api.models import HealthResponse, ServiceStatus
from .api.rate_limit import create_limiter, get_rate_limit_config
from .api.routes import router
from .api.route_modules.verification import router as verification_router
from .db import Base, engine
from .logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting TruthGraph Phase 2 API with ML Services")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # Pre-load ML models (optional - can be lazy loaded)
    try:
        logger.info("ML services available for lazy loading")
    except Exception as e:
        logger.warning(f"ML services initialization warning: {e}")

    # Start background workers for async task processing (Feature 4.3)
    try:
        from truthgraph.workers.task_queue import get_task_queue

        task_queue = get_task_queue(max_workers=5, result_ttl_seconds=3600)
        await task_queue.start_workers()
        logger.info("Background task workers started (5 workers)")
    except Exception as e:
        logger.error(f"Failed to start background workers: {e}", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down TruthGraph Phase 2 API")

    # Stop background workers gracefully
    try:
        from truthgraph.workers.task_queue import get_task_queue

        task_queue = get_task_queue()
        await task_queue.stop_workers(timeout=30.0)
        logger.info("Background task workers stopped")
    except Exception as e:
        logger.error(f"Error stopping background workers: {e}", exc_info=True)


# Create FastAPI app
app = FastAPI(
    title="TruthGraph Phase 2",
    description="""
    **TruthGraph Phase 2** - AI-powered fact-checking system with ML integration

    ## Features

    - **Full Verification Pipeline**: End-to-end claim verification with evidence retrieval and NLI
    - **Embedding Generation**: Generate semantic embeddings using sentence-transformers
    - **Hybrid Search**: Vector and keyword search for relevant evidence
    - **NLI Verification**: Natural Language Inference for claim-evidence analysis
    - **Verdict Management**: Store and retrieve verification verdicts

    ## ML Models

    - **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (384-dim)
    - **NLI**: microsoft/deberta-v3-base fine-tuned on MNLI
    - **Search**: pgvector with IVFFlat index for similarity search

    ## Rate Limits

    Rate limits are enforced per IP address with standard headers:
    - `RateLimit-Limit`: Maximum requests allowed
    - `RateLimit-Remaining`: Requests remaining in window
    - `RateLimit-Reset`: Unix timestamp when limit resets
    - `Retry-After`: Seconds to wait before retrying (on 429 error)

    **Endpoint Limits:**
    - `/api/v1/verify`: 5 requests/minute (full verification pipeline)
    - `/api/v1/embed`: 10 requests/minute (embedding generation)
    - `/api/v1/search`: 20 requests/minute (search operations)
    - `/api/v1/nli`: 10 requests/minute (NLI inference)
    - `/api/v1/verdict/{claim_id}`: 20 requests/minute (verdict retrieval)
    - `/health`: 100 requests/minute (health checks)
    - Default: 60 requests/minute (all other endpoints)

    ## API Documentation

    See the interactive documentation below for detailed endpoint information and examples.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Initialize rate limiter with slowapi
import os
from pathlib import Path

config_path = os.getenv(
    "RATE_LIMIT_CONFIG",
    str(Path(__file__).parent / "api" / "rate_limits.yaml")
)
limiter = create_limiter(
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
)
app.state.limiter = limiter

# Add slowapi exception handler for 429 errors
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware (order matters - first added is outermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMonitoringMiddleware)
# Note: Keep legacy RateLimitMiddleware for backwards compatibility
# but slowapi decorators on endpoints will take precedence
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    ml_requests_per_minute=10,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Claims"])
app.include_router(ml_router, tags=["ML Services"])
app.include_router(verification_router, tags=["Verification"])


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
    description="Check health status of API and all services",
)
@limiter.limit("100/minute")
async def health_check(request: Request, response: Response):
    """Comprehensive health check endpoint.

    Checks:
    - Database connectivity
    - ML service availability
    - Overall system status

    Returns:
        HealthResponse with service statuses
    """
    logger = logging.getLogger(__name__)
    services = {}

    # Check database
    try:
        from .db import SessionLocal

        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        services["database"] = ServiceStatus(status="healthy", message="Database connection OK")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = ServiceStatus(
            status="unhealthy", message=f"Database error: {str(e)}"
        )

    # Check embedding service
    try:
        from .services.ml.embedding_service import get_embedding_service

        svc = get_embedding_service()
        start = time.time()
        # Don't load model yet, just check availability
        services["embedding_service"] = ServiceStatus(
            status="healthy",
            message=f"Embedding service available (loaded: {svc.is_loaded()})",
            latency_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        services["embedding_service"] = ServiceStatus(
            status="unhealthy", message=f"Service error: {str(e)}"
        )

    # Check NLI service
    try:
        from .services.ml.nli_service import get_nli_service

        svc = get_nli_service()
        start = time.time()
        info = svc.get_model_info()
        services["nli_service"] = ServiceStatus(
            status="healthy",
            message=f"NLI service available (initialized: {info['initialized']})",
            latency_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        logger.error(f"NLI service health check failed: {e}")
        services["nli_service"] = ServiceStatus(
            status="unhealthy", message=f"Service error: {str(e)}"
        )

    # Determine overall status
    if all(s.status == "healthy" for s in services.values()):
        overall_status = "healthy"
    elif any(s.status == "unhealthy" for s in services.values()):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status, timestamp=datetime.now(UTC), services=services, version="2.0.0"
    )


@app.get(
    "/rate-limit-stats",
    tags=["System"],
    summary="Get rate limit statistics",
    description="View rate limit monitoring statistics including violations and usage patterns",
)
def get_rate_limit_stats():
    """Get rate limit statistics and monitoring data."""
    from .api.rate_limit import get_rate_limit_monitor

    monitor = get_rate_limit_monitor()
    stats = monitor.get_stats()

    return {
        "rate_limit_statistics": stats,
        "message": "Rate limit monitoring data",
    }


@app.get(
    "/",
    tags=["System"],
    summary="API root endpoint",
    description="Get API information and available endpoints",
)
def root():
    """Root endpoint with API information."""
    return {
        "service": "TruthGraph Phase 2",
        "version": "2.0.0",
        "description": "AI-powered fact-checking system with ML integration",
        "docs": "/docs",
        "health": "/health",
        "rate_limits": "/rate-limit-stats",
        "endpoints": {
            "verify": "/api/v1/verify",
            "embed": "/api/v1/embed",
            "search": "/api/v1/search",
            "nli": "/api/v1/nli",
            "verdict": "/api/v1/verdict/{claim_id}",
        },
    }


# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "NotFound",
            "message": "The requested resource was not found",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler."""
    logger = logging.getLogger(__name__)
    logger.error(f"Internal server error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )
