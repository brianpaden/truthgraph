"""Evidence-related Pydantic models for verification responses.

This module provides comprehensive models for evidence items returned by
the verification API, with proper validation and documentation.
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
    """Evidence item in verification results.

    Represents a single piece of evidence retrieved and analyzed during
    claim verification, including relevance scores and NLI relationships.
    """

    id: Annotated[str, Field(description="Unique identifier for the evidence item")]
    text: Annotated[
        str, Field(min_length=1, max_length=10000, description="Content of the evidence")
    ]
    source: Annotated[str, Field(min_length=1, description="Source identifier or name")]
    relevance: Annotated[
        float,
        Field(
            ge=0.0, le=1.0, description="Relevance score of evidence to claim (0.0-1.0, higher is more relevant)"
        ),
    ]
    url: Annotated[Optional[str], Field(default=None, description="URL to the evidence source")] = (
        None
    )
    publication_date: Annotated[
        Optional[str], Field(default=None, description="Publication date in ISO format (YYYY-MM-DD)")
    ] = None
    nli_label: Annotated[
        Optional[str],
        Field(
            default=None,
            description="NLI relationship to claim (entailment, contradiction, neutral)",
        ),
    ] = None
    nli_confidence: Annotated[
        Optional[float],
        Field(default=None, ge=0.0, le=1.0, description="Confidence in NLI prediction (0.0-1.0)"),
    ] = None

    @field_validator("relevance", "nli_confidence")
    @classmethod
    def validate_scores(cls, v: Optional[float]) -> Optional[float]:
        """Validate that scores are within valid range."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None and v.strip():
            # Basic URL validation - must start with http:// or https://
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                raise ValueError("URL must start with http:// or https://")
        return v if v else None

    @field_validator("publication_date")
    @classmethod
    def validate_publication_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate publication date format if provided."""
        if v is not None and v.strip():
            v = v.strip()
            # Validate ISO date format
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid date format, expected ISO format: {e}") from e
        return v if v else None

    @field_validator("nli_label")
    @classmethod
    def validate_nli_label(cls, v: Optional[str]) -> Optional[str]:
        """Validate NLI label is one of the allowed values."""
        if v is not None:
            v = v.lower()
            if v not in ["entailment", "contradiction", "neutral"]:
                raise ValueError(
                    "NLI label must be one of: entailment, contradiction, neutral"
                )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evidence_abc123",
                "text": "Scientific studies from 2023 show that the Earth's average temperature has increased by 1.1°C since pre-industrial times.",
                "source": "Climate Research Journal",
                "relevance": 0.92,
                "url": "https://example.com/climate-study-2023",
                "publication_date": "2023-05-15",
                "nli_label": "entailment",
                "nli_confidence": 0.89,
            }
        }
    )
