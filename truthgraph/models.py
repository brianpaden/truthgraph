"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    """Request model for creating a new claim."""
    text: str = Field(..., min_length=1, description="The claim text to verify")
    source_url: Optional[str] = Field(None, description="Optional source URL for the claim")


class VerdictResponse(BaseModel):
    """Response model for verdict information."""
    id: UUID
    verdict: Optional[str] = Field(None, description="SUPPORTED, REFUTED, or INSUFFICIENT")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True


class ClaimResponse(BaseModel):
    """Response model for claim information."""
    id: UUID
    text: str
    source_url: Optional[str] = None
    submitted_at: datetime
    verdict: Optional[VerdictResponse] = None

    class Config:
        from_attributes = True


class ClaimListResponse(BaseModel):
    """Response model for paginated claim list."""
    items: list[ClaimResponse]
    total: int
    skip: int
    limit: int


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    database: str


class VectorSearchRequest(BaseModel):
    """Request model for vector similarity search."""
    query_embedding: list[float] = Field(
        ...,
        description="Query embedding vector (384-dimensional)",
        min_length=384,
        max_length=384
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold"
    )
    tenant_id: str = Field(default="default", description="Tenant identifier")
    source_filter: Optional[str] = Field(None, description="Filter by source URL")


class VectorSearchResultItem(BaseModel):
    """Individual result from vector similarity search."""
    evidence_id: UUID
    content: str
    source_url: Optional[str] = None
    similarity: float = Field(..., ge=0.0, le=1.0)

    class Config:
        from_attributes = True


class VectorSearchResponse(BaseModel):
    """Response model for vector similarity search."""
    results: list[VectorSearchResultItem]
    total: int
    query_time_ms: Optional[float] = None

    class Config:
        from_attributes = True
