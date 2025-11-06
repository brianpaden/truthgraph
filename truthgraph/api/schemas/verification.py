"""Verification request and response models for TruthGraph API.

This module provides comprehensive Pydantic models for claim verification,
including request options, verification results, and async task status tracking.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from truthgraph.api.schemas.evidence import EvidenceItem


class VerificationOptions(BaseModel):
    """Options for configuring verification requests.

    Allows clients to customize the verification process including
    evidence retrieval limits, confidence thresholds, and output options.
    """

    max_evidence_items: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=50,
            description="Maximum number of evidence items to retrieve (1-50)",
        ),
    ] = 10
    confidence_threshold: Annotated[
        float,
        Field(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="Minimum confidence threshold for verdict (0.0-1.0)",
        ),
    ] = 0.5
    return_reasoning: Annotated[
        bool, Field(default=True, description="Include reasoning explanation in response")
    ] = True
    search_mode: Annotated[
        Literal["hybrid", "vector", "keyword"],
        Field(default="hybrid", description="Evidence search strategy to use"),
    ] = "hybrid"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_evidence_items": 10,
                "confidence_threshold": 0.7,
                "return_reasoning": True,
                "search_mode": "hybrid",
            }
        }
    )


class VerifyClaimRequest(BaseModel):
    """Request model for claim verification endpoint.

    Accepts a claim to verify along with optional corpus filtering
    and verification options.
    """

    claim_id: Annotated[str, Field(min_length=1, description="Unique claim identifier")]
    claim_text: Annotated[
        str, Field(min_length=1, max_length=5000, description="Claim text to verify")
    ]
    corpus_ids: Annotated[
        Optional[list[str]],
        Field(default=None, description="Specific corpus IDs to search (if None, search all)"),
    ] = None
    options: Annotated[
        Optional[VerificationOptions],
        Field(default=None, description="Verification options (uses defaults if None)"),
    ] = None

    @field_validator("claim_text")
    @classmethod
    def validate_claim_text(cls, v: str) -> str:
        """Validate and clean claim text.

        Ensures claim text is non-empty after stripping whitespace
        and doesn't exceed maximum length.
        """
        if not v or not v.strip():
            raise ValueError("Claim text cannot be empty")
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("Claim text exceeds 5000 characters")
        return v

    @field_validator("corpus_ids")
    @classmethod
    def validate_corpus_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate corpus IDs list if provided."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("corpus_ids cannot be empty list (use None instead)")
            if not all(corpus_id.strip() for corpus_id in v):
                raise ValueError("All corpus IDs must be non-empty strings")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claim_id": "claim_123",
                "claim_text": "The Earth orbits around the Sun",
                "corpus_ids": ["wikipedia", "scientific_papers"],
                "options": {
                    "max_evidence_items": 5,
                    "confidence_threshold": 0.7,
                    "return_reasoning": True,
                    "search_mode": "hybrid",
                },
            }
        }
    )


class VerificationResult(BaseModel):
    """Complete verification result with verdict and evidence.

    Contains the final verdict, confidence score, supporting evidence,
    and reasoning for the verification decision.
    """

    claim_id: Annotated[str, Field(description="Original claim identifier")]
    claim_text: Annotated[str, Field(description="Original claim text that was verified")]
    verdict: Annotated[
        Literal["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO"],
        Field(description="Final verification verdict"),
    ]
    confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Confidence in the verdict (0.0-1.0, higher is more confident)",
        ),
    ]
    reasoning: Annotated[
        Optional[str], Field(default=None, description="Human-readable explanation of the verdict")
    ] = None
    evidence: Annotated[
        list[EvidenceItem], Field(description="Evidence items analyzed during verification")
    ]
    verified_at: Annotated[
        datetime, Field(description="Timestamp when verification was completed")
    ]
    processing_time_ms: Annotated[
        int, Field(ge=0, description="Total processing time in milliseconds")
    ]
    corpus_ids_searched: Annotated[
        Optional[list[str]],
        Field(default=None, description="Corpus IDs that were searched (if filtered)"),
    ] = None

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, v: list[EvidenceItem]) -> list[EvidenceItem]:
        """Validate evidence list is not None."""
        if v is None:
            raise ValueError("Evidence list cannot be None (use empty list instead)")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claim_id": "claim_123",
                "claim_text": "The Earth orbits around the Sun",
                "verdict": "SUPPORTED",
                "confidence": 0.95,
                "reasoning": "Multiple high-quality scientific sources confirm that Earth orbits the Sun. This is a well-established astronomical fact supported by centuries of observations and calculations.",
                "evidence": [
                    {
                        "id": "evidence_abc123",
                        "text": "The Earth orbits the Sun once every 365.25 days in an elliptical path.",
                        "source": "Astronomy Textbook",
                        "relevance": 0.98,
                        "url": "https://example.com/astronomy",
                        "publication_date": "2023-01-15",
                        "nli_label": "entailment",
                        "nli_confidence": 0.96,
                    }
                ],
                "verified_at": "2025-11-06T10:30:00Z",
                "processing_time_ms": 1250,
                "corpus_ids_searched": ["wikipedia", "scientific_papers"],
            }
        }
    )


class TaskStatus(BaseModel):
    """Status tracking for asynchronous verification tasks.

    Used to track the progress and results of long-running verification
    operations submitted for background processing.
    """

    task_id: Annotated[str, Field(description="Unique identifier for the async task")]
    status: Annotated[
        Literal["pending", "processing", "completed", "failed"],
        Field(description="Current status of the task"),
    ]
    created_at: Annotated[datetime, Field(description="Timestamp when task was created")]
    completed_at: Annotated[
        Optional[datetime], Field(default=None, description="Timestamp when task completed (if done)")
    ] = None
    result: Annotated[
        Optional[VerificationResult],
        Field(default=None, description="Verification result (if status is completed)"),
    ] = None
    error: Annotated[
        Optional[str], Field(default=None, description="Error message (if status is failed)")
    ] = None
    progress_percentage: Annotated[
        Optional[int],
        Field(default=None, ge=0, le=100, description="Progress percentage for processing tasks (0-100)"),
    ] = None

    @field_validator("result")
    @classmethod
    def validate_result(cls, v: Optional[VerificationResult], info) -> Optional[VerificationResult]:
        """Validate that result is provided only when status is completed."""
        if v is not None and info.data.get("status") != "completed":
            raise ValueError("Result can only be provided when status is 'completed'")
        return v

    @field_validator("error")
    @classmethod
    def validate_error(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that error is provided only when status is failed."""
        if v is not None and info.data.get("status") != "failed":
            raise ValueError("Error can only be provided when status is 'failed'")
        return v

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that completed_at is provided when task is done."""
        status = info.data.get("status")
        if v is not None and status not in ["completed", "failed"]:
            raise ValueError(
                "completed_at can only be provided when status is 'completed' or 'failed'"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "task_id": "task_xyz789",
                    "status": "pending",
                    "created_at": "2025-11-06T10:29:00Z",
                    "completed_at": None,
                    "result": None,
                    "error": None,
                    "progress_percentage": 0,
                },
                {
                    "task_id": "task_xyz789",
                    "status": "processing",
                    "created_at": "2025-11-06T10:29:00Z",
                    "completed_at": None,
                    "result": None,
                    "error": None,
                    "progress_percentage": 45,
                },
                {
                    "task_id": "task_xyz789",
                    "status": "completed",
                    "created_at": "2025-11-06T10:29:00Z",
                    "completed_at": "2025-11-06T10:30:30Z",
                    "result": {
                        "claim_id": "claim_123",
                        "claim_text": "The Earth orbits around the Sun",
                        "verdict": "SUPPORTED",
                        "confidence": 0.95,
                        "reasoning": "Multiple sources confirm this astronomical fact.",
                        "evidence": [],
                        "verified_at": "2025-11-06T10:30:30Z",
                        "processing_time_ms": 1500,
                    },
                    "error": None,
                    "progress_percentage": 100,
                },
                {
                    "task_id": "task_xyz789",
                    "status": "failed",
                    "created_at": "2025-11-06T10:29:00Z",
                    "completed_at": "2025-11-06T10:29:15Z",
                    "result": None,
                    "error": "Failed to retrieve evidence: Database connection timeout",
                    "progress_percentage": None,
                },
            ]
        }
    )
