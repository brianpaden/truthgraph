"""Edge case data loader for validation testing.

This module provides robust data loading and validation for edge case claims,
supporting various edge case categories and graceful error handling.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ValidationError, field_validator


class EdgeCaseClaim(BaseModel):
    """Model for edge case claim data structure."""

    id: str
    text: str
    category: str
    expected_verdict: str
    edge_case_type: List[str]
    reasoning: str
    complexity_score: float = Field(ge=0.0, le=1.0)
    word_count: Optional[int] = None
    language: Optional[str] = None

    @field_validator("expected_verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        """Validate verdict is one of the allowed types."""
        allowed = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
        if v not in allowed:
            raise ValueError(f"Verdict must be one of {allowed}, got {v}")
        return v

    @field_validator("edge_case_type")
    @classmethod
    def validate_edge_case_types(cls, v: List[str]) -> List[str]:
        """Validate edge case types are recognized."""
        allowed = {
            "insufficient_evidence",
            "contradictory_evidence",
            "ambiguous_phrasing",
            "long_claims",
            "short_claims",
            "special_characters",
            "multilingual",
            "complex_technical",
        }
        for edge_type in v:
            if edge_type not in allowed:
                raise ValueError(f"Unknown edge case type: {edge_type}")
        return v


class EdgeCaseMetadata(BaseModel):
    """Model for edge case data metadata."""

    version: str
    created_date: str
    description: Optional[str] = None
    total_claims: int
    edge_case_categories: List[str]


class EdgeCaseData(BaseModel):
    """Complete edge case dataset model."""

    metadata: EdgeCaseMetadata
    claims: List[EdgeCaseClaim]


class EdgeCaseDataLoader:
    """Loader for edge case test data with validation and categorization."""

    # Default edge case categories
    EDGE_CASE_CATEGORIES = {
        "insufficient_evidence",
        "contradictory_evidence",
        "ambiguous_phrasing",
        "long_claims",
        "short_claims",
        "special_characters",
        "multilingual",
        "complex_technical",
    }

    # Default data path
    DEFAULT_DATA_PATH = Path(__file__).parent.parent.parent / "fixtures" / "edge_case_claims.json"

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize the edge case data loader.

        Args:
            data_path: Optional path to edge case data file. Uses default if not provided.
        """
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self._cached_data: Optional[EdgeCaseData] = None
        self._load_errors: List[str] = []

    def load_edge_cases(self, category: str) -> List[Dict[str, Any]]:
        """Load edge case claims by category.

        Args:
            category: Edge case category to filter by

        Returns:
            List of claims matching the category

        Raises:
            ValueError: If category is not recognized
        """
        if category not in self.EDGE_CASE_CATEGORIES:
            raise ValueError(
                f"Unknown category '{category}'. "
                f"Valid categories: {sorted(self.EDGE_CASE_CATEGORIES)}"
            )

        all_data = self.load_all_edge_cases()
        filtered_claims = []

        for claim in all_data["claims"]:
            if category in claim.get("edge_case_type", []):
                filtered_claims.append(claim)

        return filtered_claims

    def load_all_edge_cases(self) -> Dict[str, Any]:
        """Load all edge case categories.

        Returns:
            Dictionary with metadata and all claims

        Raises:
            FileNotFoundError: If data file doesn't exist
            ValueError: If data is invalid
        """
        # Use cached data if available
        if self._cached_data:
            return self._cached_data.model_dump()

        # Load from file
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Edge case data file not found at: {self.data_path}"
            )

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in data file: {e}") from e

        # Validate structure
        if not self.validate_edge_case_data(raw_data):
            raise ValueError(
                f"Data validation failed: {', '.join(self._load_errors)}"
            )

        # Parse with Pydantic for strict validation
        try:
            self._cached_data = EdgeCaseData(**raw_data)
        except ValidationError as e:
            raise ValueError(f"Data validation error: {e}") from e

        return self._cached_data.model_dump()

    def validate_edge_case_data(self, data: Dict[str, Any]) -> bool:
        """Validate edge case data structure.

        Args:
            data: Raw data dictionary to validate

        Returns:
            True if valid, False otherwise (errors stored in _load_errors)
        """
        self._load_errors = []

        # Check required top-level keys
        if "metadata" not in data:
            self._load_errors.append("Missing 'metadata' key")
            return False

        if "claims" not in data:
            self._load_errors.append("Missing 'claims' key")
            return False

        # Validate metadata
        metadata = data["metadata"]
        required_metadata = ["version", "created_date", "total_claims", "edge_case_categories"]
        for key in required_metadata:
            if key not in metadata:
                self._load_errors.append(f"Missing metadata key: {key}")

        # Validate claims structure
        if not isinstance(data["claims"], list):
            self._load_errors.append("'claims' must be a list")
            return False

        # Check each claim has required fields
        required_claim_fields = {
            "id",
            "text",
            "category",
            "expected_verdict",
            "edge_case_type",
            "reasoning",
            "complexity_score",
        }

        for i, claim in enumerate(data["claims"]):
            missing = required_claim_fields - set(claim.keys())
            if missing:
                self._load_errors.append(
                    f"Claim {i} ({claim.get('id', 'unknown')}) missing fields: {missing}"
                )

            # Validate edge_case_type is list
            if "edge_case_type" in claim and not isinstance(claim["edge_case_type"], list):
                self._load_errors.append(
                    f"Claim {claim.get('id', 'unknown')}: edge_case_type must be list"
                )

        return len(self._load_errors) == 0

    def get_claims_by_verdict(self, verdict: str) -> List[Dict[str, Any]]:
        """Get all claims with a specific expected verdict.

        Args:
            verdict: Expected verdict to filter by

        Returns:
            List of claims with matching expected verdict
        """
        all_data = self.load_all_edge_cases()
        return [
            claim
            for claim in all_data["claims"]
            if claim.get("expected_verdict") == verdict
        ]

    def get_claims_by_complexity(
        self, min_score: float = 0.0, max_score: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Get claims within a complexity score range.

        Args:
            min_score: Minimum complexity score (0.0-1.0)
            max_score: Maximum complexity score (0.0-1.0)

        Returns:
            List of claims within complexity range
        """
        all_data = self.load_all_edge_cases()
        return [
            claim
            for claim in all_data["claims"]
            if min_score <= claim.get("complexity_score", 0) <= max_score
        ]

    def get_multilingual_claims(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all multilingual claims organized by language.

        Returns:
            Dictionary mapping language codes to claims
        """
        all_data = self.load_all_edge_cases()
        multilingual: Dict[str, List[Dict[str, Any]]] = {}

        for claim in all_data["claims"]:
            if "multilingual" in claim.get("edge_case_type", []):
                lang = claim.get("language", "unknown")
                if lang not in multilingual:
                    multilingual[lang] = []
                multilingual[lang].append(claim)

        return multilingual

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the edge case dataset.

        Returns:
            Dictionary with dataset statistics
        """
        all_data = self.load_all_edge_cases()
        claims = all_data["claims"]

        # Count by edge case type
        edge_case_counts: Dict[str, int] = {}
        for claim in claims:
            for edge_type in claim.get("edge_case_type", []):
                edge_case_counts[edge_type] = edge_case_counts.get(edge_type, 0) + 1

        # Count by verdict
        verdict_counts: Dict[str, int] = {}
        for claim in claims:
            verdict = claim.get("expected_verdict", "UNKNOWN")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Complexity statistics
        complexity_scores = [
            claim.get("complexity_score", 0) for claim in claims
        ]

        return {
            "total_claims": len(claims),
            "edge_case_counts": edge_case_counts,
            "verdict_counts": verdict_counts,
            "complexity_stats": {
                "min": min(complexity_scores) if complexity_scores else 0,
                "max": max(complexity_scores) if complexity_scores else 0,
                "avg": sum(complexity_scores) / len(complexity_scores)
                if complexity_scores
                else 0,
            },
            "languages": list(self.get_multilingual_claims().keys()),
        }

    def get_validation_errors(self) -> List[str]:
        """Get any validation errors from the last load attempt.

        Returns:
            List of validation error messages
        """
        return self._load_errors.copy()

    def clear_cache(self) -> None:
        """Clear the cached data, forcing reload on next access."""
        self._cached_data = None
        self._load_errors = []
