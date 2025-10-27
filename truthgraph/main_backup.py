"""TruthGraph v0 FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .db import Base, engine
from .logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting TruthGraph v0 API")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    yield

    # Shutdown
    logger.info("Shutting down TruthGraph v0 API")


# Create FastAPI app
app = FastAPI(
    title="TruthGraph v0",
    description="Local-first fact-checking system",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok", "service": "truthgraph-api"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "TruthGraph v0",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
