"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClaimCreate(BaseModel):
    """Request model for creating a new claim."""

    text: str = Field(..., min_length=1, description="The claim text to verify")
    source_url: Optional[str] = Field(None, description="Optional source URL for the claim")


class VerdictResponse(BaseModel):
    """Response model for verdict information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    verdict: Optional[str] = Field(None, description="SUPPORTED, REFUTED, or INSUFFICIENT")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class ClaimResponse(BaseModel):
    """Response model for claim information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    source_url: Optional[str] = None
    submitted_at: datetime
    verdict: Optional[VerdictResponse] = None


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
        ..., description="Query embedding vector (384-dimensional)", min_length=384, max_length=384
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    min_similarity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold"
    )
    tenant_id: str = Field(default="default", description="Tenant identifier")
    source_filter: Optional[str] = Field(None, description="Filter by source URL")


class VectorSearchResultItem(BaseModel):
    """Individual result from vector similarity search."""

    evidence_id: UUID
    content: str
    source_url: Optional[str] = None
    similarity: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


class VectorSearchResponse(BaseModel):
    """Response model for vector similarity search."""

    results: list[VectorSearchResultItem]
    total: int
    query_time_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# Hybrid Search Models


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search combining vector and keyword search."""

    query_text: str = Field(
        ..., min_length=1, description="Natural language query text for keyword search"
    )
    query_embedding: list[float] = Field(
        ...,
        description="Query embedding vector (384 or 1536-dimensional)",
        min_length=384,
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    vector_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Weight for vector search contribution (0.0-1.0)"
    )
    keyword_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Weight for keyword search contribution (0.0-1.0)"
    )
    min_vector_similarity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold for vector search"
    )
    tenant_id: str = Field(default="default", description="Tenant identifier for multi-tenancy")
    source_filter: Optional[str] = Field(
        None, description="Filter results by source URL (exact match)"
    )
    date_from: Optional[datetime] = Field(
        None, description="Filter results created on or after this date"
    )
    date_to: Optional[datetime] = Field(
        None, description="Filter results created on or before this date"
    )


class HybridSearchResultItem(BaseModel):
    """Individual result from hybrid search."""

    evidence_id: UUID
    content: str
    source_url: Optional[str] = None
    rank_score: float = Field(..., description="Combined RRF score (higher is better)")
    vector_similarity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Cosine similarity from vector search (if found via vector)",
    )
    keyword_rank: Optional[int] = Field(
        None, ge=1, description="Rank position from keyword search (if found via keyword)"
    )
    matched_via: str = Field(
        ..., description="How result was found: 'vector', 'keyword', or 'both'"
    )

    model_config = ConfigDict(from_attributes=True)


class HybridSearchResponse(BaseModel):
    """Response model for hybrid search."""

    results: list[HybridSearchResultItem]
    total: int
    query_time_ms: float
    search_stats: dict = Field(default_factory=dict, description="Additional search statistics")

    model_config = ConfigDict(from_attributes=True)


class SearchStatsResponse(BaseModel):
    """Response model for search statistics."""

    total_evidence: int
    evidence_with_embeddings: int
    embedding_coverage: float = Field(..., ge=0.0, le=100.0)
    tenant_id: str

    model_config = ConfigDict(from_attributes=True)
