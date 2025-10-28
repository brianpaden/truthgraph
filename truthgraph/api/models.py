"""Pydantic v2 models for API request/response validation.

This module provides comprehensive request and response models for all TruthGraph API endpoints,
using Pydantic v2 with modern validation and serialization features.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ===== Base Models =====


class BaseResponseModel(BaseModel):
    """Base response model with common configuration."""

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": {}})


# ===== Embedding Models =====


class EmbedRequest(BaseModel):
    """Request model for embedding generation."""

    texts: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=100,
            description="List of texts to generate embeddings for (max 100)",
        ),
    ]
    batch_size: Annotated[
        int, Field(default=32, ge=1, le=128, description="Batch size for processing (1-128)")
    ] = 32

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: list[str]) -> list[str]:
        """Validate that all texts are non-empty."""
        if not all(text.strip() for text in v):
            raise ValueError("All texts must be non-empty strings")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "texts": ["The Earth orbits the Sun", "Water freezes at 0 degrees Celsius"],
                "batch_size": 32,
            }
        }
    )


class EmbedResponse(BaseResponseModel):
    """Response model for embedding generation."""

    embeddings: Annotated[
        list[list[float]], Field(description="List of 384-dimensional embeddings")
    ]
    count: Annotated[int, Field(description="Number of embeddings generated")]
    dimension: Annotated[int, Field(description="Dimensionality of embeddings (384)")]
    processing_time_ms: Annotated[
        Optional[float], Field(description="Processing time in milliseconds")
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "embeddings": [[0.1] * 384, [0.2] * 384],
                "count": 2,
                "dimension": 384,
                "processing_time_ms": 125.5,
            }
        }
    )


# ===== Search Models =====


class SearchRequest(BaseModel):
    """Request model for hybrid/vector/keyword search."""

    query: Annotated[str, Field(min_length=1, max_length=1000, description="Search query text")]
    limit: Annotated[
        int, Field(default=10, ge=1, le=100, description="Maximum number of results (1-100)")
    ] = 10
    mode: Annotated[
        Literal["hybrid", "vector", "keyword"],
        Field(description="Search mode: hybrid (default), vector, or keyword"),
    ] = "hybrid"
    min_similarity: Annotated[
        float,
        Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0-1.0)"),
    ] = 0.0
    tenant_id: Annotated[
        str,
        Field(default="default", max_length=255, description="Tenant identifier for multi-tenancy"),
    ] = "default"
    source_filter: Annotated[
        Optional[str], Field(default=None, description="Filter results by source URL")
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "climate change effects on polar ice caps",
                "limit": 10,
                "mode": "hybrid",
                "min_similarity": 0.5,
                "tenant_id": "default",
            }
        }
    )


class SearchResultItem(BaseResponseModel):
    """Individual search result item."""

    evidence_id: UUID
    content: Annotated[str, Field(description="Evidence content text")]
    source_url: Annotated[Optional[str], Field(description="Source URL of the evidence")] = None
    similarity: Annotated[float, Field(ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")]
    rank: Annotated[int, Field(ge=1, description="Result rank (1-based)")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Studies show that polar ice caps are melting at accelerating rates...",
                "source_url": "https://example.com/climate-study",
                "similarity": 0.87,
                "rank": 1,
            }
        }
    )


class SearchResponse(BaseResponseModel):
    """Response model for search results."""

    results: Annotated[
        list[SearchResultItem], Field(description="List of search results ordered by relevance")
    ]
    count: Annotated[int, Field(description="Number of results returned")]
    query: Annotated[str, Field(description="Original search query")]
    mode: Annotated[str, Field(description="Search mode used")]
    query_time_ms: Annotated[
        Optional[float], Field(description="Query execution time in milliseconds")
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
                        "content": "Climate research findings...",
                        "source_url": "https://example.com/study",
                        "similarity": 0.87,
                        "rank": 1,
                    }
                ],
                "count": 1,
                "query": "climate change effects",
                "mode": "hybrid",
                "query_time_ms": 45.2,
            }
        }
    )


# ===== NLI Models =====


class NLIRequest(BaseModel):
    """Request model for NLI verification."""

    premise: Annotated[
        str, Field(min_length=1, max_length=2000, description="Premise text (evidence)")
    ]
    hypothesis: Annotated[
        str, Field(min_length=1, max_length=2000, description="Hypothesis text (claim)")
    ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "premise": "The Earth revolves around the Sun in an elliptical orbit",
                "hypothesis": "The Earth orbits the Sun",
            }
        }
    )


class NLIBatchRequest(BaseModel):
    """Request model for batch NLI verification."""

    pairs: Annotated[
        list[tuple[str, str]],
        Field(
            min_length=1, max_length=50, description="List of (premise, hypothesis) pairs (max 50)"
        ),
    ]
    batch_size: Annotated[
        int, Field(default=8, ge=1, le=32, description="Batch size for processing (1-32)")
    ] = 8

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pairs": [["Evidence text 1", "Claim text 1"], ["Evidence text 2", "Claim text 2"]],
                "batch_size": 8,
            }
        }
    )


class NLIScores(BaseModel):
    """NLI probability scores for all labels."""

    entailment: Annotated[float, Field(ge=0.0, le=1.0, description="Entailment probability")]
    contradiction: Annotated[float, Field(ge=0.0, le=1.0, description="Contradiction probability")]
    neutral: Annotated[float, Field(ge=0.0, le=1.0, description="Neutral probability")]


class NLIResponse(BaseResponseModel):
    """Response model for NLI verification."""

    label: Annotated[
        Literal["entailment", "contradiction", "neutral"], Field(description="Predicted NLI label")
    ]
    confidence: Annotated[
        float, Field(ge=0.0, le=1.0, description="Confidence score for predicted label")
    ]
    scores: Annotated[NLIScores, Field(description="Probability scores for all labels")]
    processing_time_ms: Annotated[
        Optional[float], Field(description="Processing time in milliseconds")
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "label": "entailment",
                "confidence": 0.92,
                "scores": {"entailment": 0.92, "contradiction": 0.03, "neutral": 0.05},
                "processing_time_ms": 85.3,
            }
        }
    )


class NLIBatchResponse(BaseResponseModel):
    """Response model for batch NLI verification."""

    results: Annotated[list[NLIResponse], Field(description="List of NLI results")]
    count: Annotated[int, Field(description="Number of results")]
    total_processing_time_ms: Annotated[
        Optional[float], Field(description="Total processing time in milliseconds")
    ] = None


# ===== Verification Models =====


class VerifyRequest(BaseModel):
    """Request model for full claim verification."""

    claim: Annotated[str, Field(min_length=1, max_length=2000, description="Claim text to verify")]
    tenant_id: Annotated[
        str, Field(default="default", max_length=255, description="Tenant identifier")
    ] = "default"
    max_evidence: Annotated[
        int, Field(default=10, ge=1, le=50, description="Maximum evidence items to retrieve (1-50)")
    ] = 10
    confidence_threshold: Annotated[
        float,
        Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold for verdict"),
    ] = 0.7
    search_mode: Annotated[
        Literal["hybrid", "vector", "keyword"], Field(description="Evidence search mode")
    ] = "hybrid"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claim": "The Earth is approximately 4.54 billion years old",
                "tenant_id": "default",
                "max_evidence": 10,
                "confidence_threshold": 0.7,
                "search_mode": "hybrid",
            }
        }
    )


class EvidenceItem(BaseResponseModel):
    """Evidence item in verification response."""

    evidence_id: UUID
    content: Annotated[str, Field(description="Evidence content")]
    source_url: Annotated[Optional[str], Field(description="Source URL")] = None
    nli_label: Annotated[
        Literal["entailment", "contradiction", "neutral"],
        Field(description="NLI relationship to claim"),
    ]
    nli_confidence: Annotated[float, Field(ge=0.0, le=1.0, description="NLI confidence score")]
    similarity: Annotated[float, Field(ge=0.0, le=1.0, description="Semantic similarity to claim")]


class VerifyResponse(BaseResponseModel):
    """Response model for claim verification."""

    verdict: Annotated[
        Literal["SUPPORTED", "REFUTED", "INSUFFICIENT"],
        Field(description="Final verdict for the claim"),
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Overall confidence in verdict")]
    evidence: Annotated[list[EvidenceItem], Field(description="Evidence items analyzed")]
    explanation: Annotated[str, Field(description="Human-readable explanation of verdict")]
    claim_id: Annotated[Optional[UUID], Field(description="Created claim ID (if persisted)")] = None
    verification_id: Annotated[
        Optional[UUID], Field(description="Verification result ID (if persisted)")
    ] = None
    processing_time_ms: Annotated[
        Optional[float], Field(description="Total processing time in milliseconds")
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verdict": "SUPPORTED",
                "confidence": 0.87,
                "evidence": [
                    {
                        "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
                        "content": "Geological evidence confirms Earth's age at 4.54 billion years...",
                        "source_url": "https://example.com/geology",
                        "nli_label": "entailment",
                        "nli_confidence": 0.91,
                        "similarity": 0.85,
                    }
                ],
                "explanation": "The claim is supported by strong geological evidence with high confidence.",
                "claim_id": "223e4567-e89b-12d3-a456-426614174000",
                "verification_id": "323e4567-e89b-12d3-a456-426614174000",
                "processing_time_ms": 1250.5,
            }
        }
    )


# ===== Verdict Retrieval Models =====


class VerdictRequest(BaseModel):
    """Request model for retrieving verdict."""

    claim_id: Annotated[UUID, Field(description="Claim UUID to retrieve verdict for")]

    model_config = ConfigDict(
        json_schema_extra={"example": {"claim_id": "123e4567-e89b-12d3-a456-426614174000"}}
    )


class VerdictResponse(BaseResponseModel):
    """Response model for verdict retrieval."""

    claim_id: UUID
    claim_text: Annotated[str, Field(description="Original claim text")]
    verdict: Annotated[
        Literal["SUPPORTED", "REFUTED", "INSUFFICIENT"], Field(description="Verdict for the claim")
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Verdict confidence")]
    reasoning: Annotated[Optional[str], Field(description="Reasoning for the verdict")] = None
    evidence_count: Annotated[int, Field(description="Number of evidence items analyzed")]
    supporting_evidence_count: Annotated[int, Field(description="Count of supporting evidence")]
    refuting_evidence_count: Annotated[int, Field(description="Count of refuting evidence")]
    created_at: Annotated[datetime, Field(description="Verdict creation timestamp")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claim_id": "123e4567-e89b-12d3-a456-426614174000",
                "claim_text": "The Earth is approximately 4.54 billion years old",
                "verdict": "SUPPORTED",
                "confidence": 0.87,
                "reasoning": "Strong geological evidence supports this claim",
                "evidence_count": 10,
                "supporting_evidence_count": 8,
                "refuting_evidence_count": 0,
                "created_at": "2025-10-26T12:00:00Z",
            }
        }
    )


# ===== Error Response Models =====


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Annotated[
        Optional[str], Field(description="Field that caused the error (if applicable)")
    ] = None
    message: Annotated[str, Field(description="Error message")]
    error_code: Annotated[Optional[str], Field(description="Application-specific error code")] = (
        None
    )


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: Annotated[str, Field(description="Error type")]
    message: Annotated[str, Field(description="Human-readable error message")]
    details: Annotated[
        Optional[list[ErrorDetail]], Field(description="Detailed error information")
    ] = None
    request_id: Annotated[Optional[str], Field(description="Request tracking ID")] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "details": [
                    {
                        "field": "claim",
                        "message": "Claim text cannot be empty",
                        "error_code": "EMPTY_CLAIM",
                    }
                ],
                "request_id": "req_abc123",
            }
        }
    )


# ===== Health Check Models =====


class ServiceStatus(BaseModel):
    """Individual service status."""

    status: Annotated[
        Literal["healthy", "degraded", "unhealthy"], Field(description="Service health status")
    ]
    message: Annotated[Optional[str], Field(description="Status message")] = None
    latency_ms: Annotated[Optional[float], Field(description="Service latency in milliseconds")] = (
        None
    )


class HealthResponse(BaseResponseModel):
    """Response model for health check."""

    status: Annotated[
        Literal["healthy", "degraded", "unhealthy"], Field(description="Overall system health")
    ]
    timestamp: Annotated[datetime, Field(description="Health check timestamp")]
    services: Annotated[dict[str, ServiceStatus], Field(description="Individual service statuses")]
    version: Annotated[str, Field(description="API version")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-26T12:00:00Z",
                "services": {
                    "database": {"status": "healthy", "latency_ms": 5.2},
                    "embedding_service": {"status": "healthy", "latency_ms": 12.3},
                    "nli_service": {"status": "healthy", "latency_ms": 45.7},
                },
                "version": "2.0.0",
            }
        }
    )
