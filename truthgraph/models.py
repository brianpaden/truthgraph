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
