"""Pytest fixtures for edge case test data.

This module provides fixtures that load and validate edge case data from JSON files
in the edge_cases directory. Edge cases test the system's ability to handle challenging
scenarios including insufficient evidence, contradictory information, ambiguous evidence,
extreme claim lengths, special characters, and adversarial examples.

Fixtures:
    - edge_case_insufficient_evidence: Insufficient evidence edge cases
    - edge_case_contradictory: Contradictory evidence edge cases
    - edge_case_ambiguous: Ambiguous/neutral evidence edge cases
    - edge_case_long_claims: Long-form claims (>500 words)
    - edge_case_short_claims: Short claims (<10 words)
    - edge_case_special_characters: Special characters and multilingual claims
    - edge_case_adversarial: Adversarial examples and misleading claims
    - all_edge_cases: Combined dictionary with all edge case categories
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest

# Define fixture data directory
FIXTURES_DIR = Path(__file__).parent


def _load_edge_case_file(filename: str) -> Dict[str, Any]:
    """Load and validate an edge case JSON file.

    Args:
        filename: Name of the JSON file to load

    Returns:
        Dictionary containing the loaded edge case data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the JSON is invalid
    """
    file_path = FIXTURES_DIR / filename

    if not file_path.exists():
        pytest.fail(f"Edge case fixture file not found at {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in {filename}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load {filename}: {e}")


@pytest.fixture(scope="session")
def edge_case_insufficient_evidence() -> Dict[str, Any]:
    """Load insufficient evidence edge cases.

    Returns:
        Dictionary containing claims with insufficient evidence for verification
    """
    return _load_edge_case_file("insufficient_evidence.json")


@pytest.fixture(scope="session")
def edge_case_contradictory() -> Dict[str, Any]:
    """Load contradictory evidence edge cases.

    Returns:
        Dictionary containing claims with contradictory evidence
    """
    return _load_edge_case_file("contradictory_evidence.json")


@pytest.fixture(scope="session")
def edge_case_ambiguous() -> Dict[str, Any]:
    """Load ambiguous/neutral evidence edge cases.

    Returns:
        Dictionary containing claims with ambiguous or tangential evidence
    """
    return _load_edge_case_file("ambiguous_evidence.json")


@pytest.fixture(scope="session")
def edge_case_long_claims() -> Dict[str, Any]:
    """Load long-form claims edge cases.

    Returns:
        Dictionary containing paragraph-length and compound claims (>500 words equivalent)
    """
    return _load_edge_case_file("long_claims.json")


@pytest.fixture(scope="session")
def edge_case_short_claims() -> Dict[str, Any]:
    """Load short claims edge cases.

    Returns:
        Dictionary containing minimal context claims (<10 words)
    """
    return _load_edge_case_file("short_claims.json")


@pytest.fixture(scope="session")
def edge_case_special_characters() -> Dict[str, Any]:
    """Load special characters and multilingual edge cases.

    Returns:
        Dictionary containing claims with emojis, special characters, and non-Latin scripts
    """
    return _load_edge_case_file("special_characters.json")


@pytest.fixture(scope="session")
def edge_case_adversarial() -> Dict[str, Any]:
    """Load adversarial examples edge cases.

    Returns:
        Dictionary containing near-false claims and misleading statements
    """
    return _load_edge_case_file("adversarial_examples.json")


@pytest.fixture(scope="session")
def all_edge_cases(
    edge_case_insufficient_evidence: Dict[str, Any],
    edge_case_contradictory: Dict[str, Any],
    edge_case_ambiguous: Dict[str, Any],
    edge_case_long_claims: Dict[str, Any],
    edge_case_short_claims: Dict[str, Any],
    edge_case_special_characters: Dict[str, Any],
    edge_case_adversarial: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Load all edge case categories combined.

    Returns:
        Dictionary with categories as keys mapping to their edge case data
    """
    return {
        "insufficient_evidence": edge_case_insufficient_evidence,
        "contradictory_evidence": edge_case_contradictory,
        "ambiguous_evidence": edge_case_ambiguous,
        "long_claims": edge_case_long_claims,
        "short_claims": edge_case_short_claims,
        "special_characters": edge_case_special_characters,
        "adversarial_examples": edge_case_adversarial,
    }


@pytest.fixture
def get_edge_case_by_id(all_edge_cases: Dict[str, Dict[str, Any]]) -> Callable:
    """Factory fixture to retrieve specific edge case claims by ID.

    Args:
        all_edge_cases: All edge cases fixture

    Returns:
        Callable that takes a claim ID and returns the claim object and category
    """

    def _get_claim(claim_id: str) -> tuple:
        """Get a specific edge case claim by ID.

        Args:
            claim_id: The ID of the claim to retrieve

        Returns:
            Tuple of (claim, category) if found

        Raises:
            ValueError: If claim ID is not found
        """
        for category, data in all_edge_cases.items():
            for claim in data.get("claims", []):
                if claim["id"] == claim_id:
                    return claim, category
        raise ValueError(f"Edge case claim with ID '{claim_id}' not found")

    return _get_claim


@pytest.fixture
def get_edge_case_claims_by_category(all_edge_cases: Dict[str, Dict[str, Any]]) -> Callable:
    """Factory fixture to retrieve all claims in a specific edge case category.

    Args:
        all_edge_cases: All edge cases fixture

    Returns:
        Callable that takes a category name and returns list of claims
    """

    def _get_claims(category: str) -> List[Dict[str, Any]]:
        """Get all claims for a specific edge case category.

        Args:
            category: The edge case category name

        Returns:
            List of claims in that category

        Raises:
            ValueError: If category is not found
        """
        if category not in all_edge_cases:
            raise ValueError(f"Edge case category '{category}' not found")
        return all_edge_cases[category].get("claims", [])

    return _get_claims


@pytest.fixture
def get_edge_case_evidence(all_edge_cases: Dict[str, Dict[str, Any]]) -> Callable:
    """Factory fixture to retrieve evidence for specific edge cases.

    Args:
        all_edge_cases: All edge cases fixture

    Returns:
        Callable that takes a category and returns all evidence items
    """

    def _get_evidence(category: str) -> List[Dict[str, Any]]:
        """Get all evidence for a specific edge case category.

        Args:
            category: The edge case category name

        Returns:
            List of evidence items for that category

        Raises:
            ValueError: If category is not found
        """
        if category not in all_edge_cases:
            raise ValueError(f"Edge case category '{category}' not found")
        return all_edge_cases[category].get("evidence", [])

    return _get_evidence


@pytest.fixture
def edge_case_statistics(all_edge_cases: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Generate statistics about all edge cases.

    Args:
        all_edge_cases: All edge cases fixture

    Returns:
        Dictionary containing statistics about edge case coverage
    """
    stats = {
        "total_categories": len(all_edge_cases),
        "total_claims": 0,
        "total_evidence": 0,
        "categories": {},
    }

    for category, data in all_edge_cases.items():
        claims = data.get("claims", [])
        evidence = data.get("evidence", [])
        stats["total_claims"] += len(claims)
        stats["total_evidence"] += len(evidence)
        stats["categories"][category] = {
            "claim_count": len(claims),
            "evidence_count": len(evidence),
            "description": data.get("description", ""),
        }

    return stats
