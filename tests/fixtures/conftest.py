"""Pytest fixtures for test claims and evidence data.

This module provides fixtures that load and validate test data from JSON files
in the fixtures directory. The fixtures are designed to support comprehensive
testing of the verification pipeline with known verdicts.

Fixtures:
    - test_claims: Loads all test claims with metadata
    - test_evidence: Loads all evidence items
    - claim_by_id: Factory fixture to get specific claims by ID
    - evidence_by_id: Factory fixture to get specific evidence by ID
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Define fixture data directory
FIXTURES_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def test_claims() -> Dict[str, Any]:
    """Load test claims fixture from JSON file.

    Returns:
        Dictionary containing claims metadata and claim objects
    """
    claims_file = FIXTURES_DIR / "test_claims.json"

    if not claims_file.exists():
        pytest.fail(f"Test claims fixture file not found at {claims_file}")

    try:
        with open(claims_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in test claims fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load test claims fixture: {e}")


@pytest.fixture(scope="session")
def test_evidence() -> Dict[str, Any]:
    """Load test evidence fixture from JSON file.

    Returns:
        Dictionary containing evidence metadata and evidence items
    """
    evidence_file = FIXTURES_DIR / "sample_evidence.json"

    if not evidence_file.exists():
        pytest.fail(f"Test evidence fixture file not found at {evidence_file}")

    try:
        with open(evidence_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in test evidence fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load test evidence fixture: {e}")


@pytest.fixture
def claim_by_id(test_claims: Dict[str, Any]):
    """Factory fixture to retrieve specific claims by ID.

    Args:
        test_claims: Test claims fixture

    Returns:
        Callable that takes a claim ID and returns the claim object
    """

    def _get_claim(claim_id: str) -> Dict[str, Any]:
        """Get a specific claim by ID.

        Args:
            claim_id: The ID of the claim to retrieve

        Returns:
            The claim object if found

        Raises:
            ValueError: If claim ID is not found
        """
        for claim in test_claims["claims"]:
            if claim["id"] == claim_id:
                return claim
        raise ValueError(f"Claim with ID '{claim_id}' not found in test fixtures")

    return _get_claim


@pytest.fixture
def evidence_by_id(test_evidence: Dict[str, Any]):
    """Factory fixture to retrieve specific evidence items by ID.

    Args:
        test_evidence: Test evidence fixture

    Returns:
        Callable that takes an evidence ID and returns the evidence object
    """

    def _get_evidence(evidence_id: str) -> Dict[str, Any]:
        """Get a specific evidence item by ID.

        Args:
            evidence_id: The ID of the evidence item to retrieve

        Returns:
            The evidence object if found

        Raises:
            ValueError: If evidence ID is not found
        """
        for evidence in test_evidence["evidence"]:
            if evidence["id"] == evidence_id:
                return evidence
        raise ValueError(f"Evidence with ID '{evidence_id}' not found in test fixtures")

    return _get_evidence


@pytest.fixture
def claims_by_verdict(test_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims filtered by expected verdict.

    Args:
        test_claims: Test claims fixture

    Returns:
        Callable that takes a verdict type and returns list of matching claims
    """

    def _get_claims_by_verdict(verdict: str) -> List[Dict[str, Any]]:
        """Get claims filtered by expected verdict.

        Args:
            verdict: The verdict type to filter by ('SUPPORTED', 'REFUTED', 'INSUFFICIENT')

        Returns:
            List of claims with the specified verdict
        """
        return [claim for claim in test_claims["claims"] if claim["expected_verdict"] == verdict]

    return _get_claims_by_verdict


@pytest.fixture
def claims_by_category(test_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims filtered by category.

    Args:
        test_claims: Test claims fixture

    Returns:
        Callable that takes a category and returns list of matching claims
    """

    def _get_claims_by_category(category: str) -> List[Dict[str, Any]]:
        """Get claims filtered by category.

        Args:
            category: The category to filter by

        Returns:
            List of claims in the specified category
        """
        return [claim for claim in test_claims["claims"] if claim["category"] == category]

    return _get_claims_by_category


@pytest.fixture
def claims_by_edge_case(test_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims by edge case type.

    Args:
        test_claims: Test claims fixture

    Returns:
        Callable that takes an edge case type and returns list of matching claims
    """

    def _get_claims_by_edge_case(edge_case: str) -> List[Dict[str, Any]]:
        """Get claims filtered by edge case type.

        Args:
            edge_case: The edge case type ('insufficient_evidence', 'contradictory_evidence', 'ambiguous_evidence')

        Returns:
            List of claims with the specified edge case type
        """
        return [claim for claim in test_claims["claims"] if claim["edge_case"] == edge_case]

    return _get_claims_by_edge_case


@pytest.fixture
def high_confidence_claims(test_claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all test claims with high confidence (>0.90).

    Args:
        test_claims: Test claims fixture

    Returns:
        List of high-confidence claims
    """
    return [claim for claim in test_claims["claims"] if claim["confidence"] > 0.90]


@pytest.fixture
def evidence_by_nli_label(test_evidence: Dict[str, Any]):
    """Factory fixture to retrieve evidence filtered by NLI label.

    Args:
        test_evidence: Test evidence fixture

    Returns:
        Callable that takes an NLI label and returns matching evidence
    """

    def _get_evidence_by_label(label: str) -> List[Dict[str, Any]]:
        """Get evidence filtered by NLI label.

        Args:
            label: The NLI label ('entailment', 'contradiction', 'neutral')

        Returns:
            List of evidence items with the specified NLI label
        """
        return [ev for ev in test_evidence["evidence"] if ev["nli_label"] == label]

    return _get_evidence_by_label


@pytest.fixture
def evidence_by_type(test_evidence: Dict[str, Any]):
    """Factory fixture to retrieve evidence filtered by source type.

    Args:
        test_evidence: Test evidence fixture

    Returns:
        Callable that takes a source type and returns matching evidence
    """

    def _get_evidence_by_source_type(source_type: str) -> List[Dict[str, Any]]:
        """Get evidence filtered by source type.

        Args:
            source_type: The source type (e.g., 'scientific', 'historical', 'medical')

        Returns:
            List of evidence items with the specified source type
        """
        return [ev for ev in test_evidence["evidence"] if ev["type"] == source_type]

    return _get_evidence_by_source_type


@pytest.fixture
def fixture_metadata(test_claims: Dict[str, Any], test_evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Get metadata about the test fixtures.

    Args:
        test_claims: Test claims fixture
        test_evidence: Test evidence fixture

    Returns:
        Dictionary containing fixture metadata and statistics
    """
    claims = test_claims["claims"]
    evidence = test_evidence["evidence"]

    # Calculate verdict distribution
    verdict_counts = {}
    for claim in claims:
        verdict = claim["expected_verdict"]
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    # Calculate category distribution
    category_counts = {}
    for claim in claims:
        category = claim["category"]
        category_counts[category] = category_counts.get(category, 0) + 1

    # Calculate edge case distribution
    edge_case_counts = {}
    for claim in claims:
        edge_case = claim.get("edge_case")
        if edge_case:
            edge_case_counts[edge_case] = edge_case_counts.get(edge_case, 0) + 1

    # Calculate NLI label distribution
    nli_label_counts = {}
    for ev in evidence:
        label = ev["nli_label"]
        nli_label_counts[label] = nli_label_counts.get(label, 0) + 1

    return {
        "total_claims": len(claims),
        "total_evidence": len(evidence),
        "verdict_distribution": verdict_counts,
        "category_distribution": category_counts,
        "edge_case_distribution": edge_case_counts,
        "nli_label_distribution": nli_label_counts,
        "average_confidence": sum(c["confidence"] for c in claims) / len(claims),
        "high_confidence_claims": sum(1 for c in claims if c["confidence"] > 0.90),
    }


@pytest.fixture
def verify_fixture_integrity(test_claims: Dict[str, Any], test_evidence: Dict[str, Any]):
    """Verify the integrity of fixture data.

    This fixture runs validation checks to ensure:
    - All evidence IDs in claims exist in evidence
    - No duplicate IDs exist
    - Required fields are present
    - Verdict values are valid
    - Confidence values are valid (0-1)

    Raises:
        AssertionError: If any validation check fails
    """

    def _verify() -> Dict[str, Any]:
        """Run fixture integrity checks.

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Get all IDs
        claim_ids = {claim["id"] for claim in test_claims["claims"]}
        evidence_ids = {ev["id"] for ev in test_evidence["evidence"]}

        # Check for duplicate claim IDs
        claim_list = [claim["id"] for claim in test_claims["claims"]]
        if len(claim_list) != len(claim_ids):
            issues.append("Duplicate claim IDs found")

        # Check for duplicate evidence IDs
        evidence_list = [ev["id"] for ev in test_evidence["evidence"]]
        if len(evidence_list) != len(evidence_ids):
            issues.append("Duplicate evidence IDs found")

        # Check evidence references
        for claim in test_claims["claims"]:
            for ev_id in claim.get("evidence_ids", []):
                if ev_id not in evidence_ids:
                    issues.append(f"Claim {claim['id']} references non-existent evidence {ev_id}")

        # Check verdict values
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
        for claim in test_claims["claims"]:
            if claim["expected_verdict"] not in valid_verdicts:
                issues.append(
                    f"Claim {claim['id']} has invalid verdict: {claim['expected_verdict']}"
                )

        # Check confidence values
        for claim in test_claims["claims"]:
            confidence = claim.get("confidence", 0)
            if not (0 <= confidence <= 1):
                issues.append(f"Claim {claim['id']} has invalid confidence: {confidence}")

        # Check NLI labels in evidence
        valid_nli_labels = {"entailment", "contradiction", "neutral"}
        for ev in test_evidence["evidence"]:
            if ev.get("nli_label") not in valid_nli_labels:
                issues.append(f"Evidence {ev['id']} has invalid NLI label: {ev.get('nli_label')}")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "claim_count": len(claim_ids),
            "evidence_count": len(evidence_ids),
        }

    return _verify


@pytest.fixture
def sample_supported_claim(claim_by_id):
    """Get a sample supported claim for testing."""
    return claim_by_id("test_001")


@pytest.fixture
def sample_refuted_claim(claim_by_id):
    """Get a sample refuted claim for testing."""
    return claim_by_id("test_005")


@pytest.fixture
def sample_insufficient_claim(claim_by_id):
    """Get a sample claim with insufficient evidence."""
    return claim_by_id("test_024")


@pytest.fixture
def sample_high_confidence_evidence(evidence_by_id):
    """Get high-relevance evidence for testing."""
    return evidence_by_id("ev_001")


@pytest.fixture
def sample_contradiction_evidence(evidence_by_id):
    """Get evidence marked as contradiction for testing."""
    return evidence_by_id("ev_011")


@pytest.fixture
def sample_neutral_evidence(evidence_by_id):
    """Get evidence marked as neutral for testing."""
    return evidence_by_id("ev_026")


# ===== FEVER Dataset Fixtures =====
# Integration of FEVER (Fact Extraction and VERification) dataset
# Source: https://fever.ai/dataset/fever.html


@pytest.fixture(scope="session")
def fever_sample_claims() -> Dict[str, Any]:
    """Load FEVER sample claims fixture from JSON file."""
    claims_file = FIXTURES_DIR / "fever" / "fever_sample_claims.json"

    if not claims_file.exists():
        pytest.fail(f"FEVER sample claims fixture file not found at {claims_file}")

    try:
        with open(claims_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in FEVER sample claims fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load FEVER sample claims fixture: {e}")


@pytest.fixture(scope="session")
def fever_sample_evidence() -> Dict[str, Any]:
    """Load FEVER sample evidence fixture from JSON file."""
    evidence_file = FIXTURES_DIR / "fever" / "fever_sample_evidence.json"

    if not evidence_file.exists():
        pytest.fail(f"FEVER sample evidence fixture file not found at {evidence_file}")

    try:
        with open(evidence_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in FEVER sample evidence fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load FEVER sample evidence fixture: {e}")


@pytest.fixture(scope="session")
def fever_mapping() -> Dict[str, Any]:
    """Load FEVER claim-to-verdict mapping fixture from JSON file."""
    mapping_file = FIXTURES_DIR / "fever" / "fever_mapping.json"

    if not mapping_file.exists():
        pytest.fail(f"FEVER mapping fixture file not found at {mapping_file}")

    try:
        with open(mapping_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in FEVER mapping fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load FEVER mapping fixture: {e}")


@pytest.fixture(scope="session")
def fever_stats() -> Dict[str, Any]:
    """Load FEVER processing statistics fixture from JSON file."""
    stats_file = FIXTURES_DIR / "fever" / "fever_stats.json"

    if not stats_file.exists():
        pytest.fail(f"FEVER stats fixture file not found at {stats_file}")

    try:
        with open(stats_file, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in FEVER stats fixture: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load FEVER stats fixture: {e}")


@pytest.fixture
def fever_claim_by_id(fever_sample_claims: Dict[str, Any]):
    """Factory fixture to retrieve specific FEVER claims by ID."""

    def _get_claim(claim_id: str) -> Dict[str, Any]:
        for claim in fever_sample_claims["claims"]:
            if claim["id"] == claim_id:
                return claim
        raise ValueError(f"FEVER claim with ID '{claim_id}' not found in fixtures")

    return _get_claim


@pytest.fixture
def fever_claims_by_verdict(fever_sample_claims: Dict[str, Any]):
    """Factory fixture to retrieve FEVER claims filtered by expected verdict."""

    def _get_claims_by_verdict(verdict: str) -> List[Dict[str, Any]]:
        return [
            claim for claim in fever_sample_claims["claims"] if claim["expected_verdict"] == verdict
        ]

    return _get_claims_by_verdict


@pytest.fixture
def fever_supported_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    """Get all FEVER claims with SUPPORTED verdict."""
    return fever_claims_by_verdict("SUPPORTED")


@pytest.fixture
def fever_refuted_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    """Get all FEVER claims with REFUTED verdict."""
    return fever_claims_by_verdict("REFUTED")


@pytest.fixture
def fever_insufficient_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    """Get all FEVER claims with INSUFFICIENT verdict."""
    return fever_claims_by_verdict("INSUFFICIENT")


@pytest.fixture
def fever_claims_with_evidence(fever_sample_claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all FEVER claims that have associated evidence."""
    return [claim for claim in fever_sample_claims["claims"] if claim.get("evidence_ids")]


@pytest.fixture
def fever_claims_without_evidence(fever_sample_claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all FEVER claims that have no associated evidence."""
    return [claim for claim in fever_sample_claims["claims"] if not claim.get("evidence_ids")]


@pytest.fixture
def fever_fixture_metadata(
    fever_sample_claims: Dict[str, Any],
    fever_sample_evidence: Dict[str, Any],
    fever_stats: Dict[str, Any],
) -> Dict[str, Any]:
    """Get metadata about the FEVER fixtures."""
    claims = fever_sample_claims["claims"]
    evidence = fever_sample_evidence["evidence"]

    supported_count = len([c for c in claims if c["expected_verdict"] == "SUPPORTED"])
    refuted_count = len([c for c in claims if c["expected_verdict"] == "REFUTED"])
    insufficient_count = len([c for c in claims if c["expected_verdict"] == "INSUFFICIENT"])

    claims_with_evidence = len([c for c in claims if c.get("evidence_ids")])
    total_evidence_refs = sum(len(c.get("evidence_ids", [])) for c in claims)

    return {
        "total_claims": len(claims),
        "total_evidence": len(evidence),
        "verdict_distribution": {
            "SUPPORTED": supported_count,
            "REFUTED": refuted_count,
            "INSUFFICIENT": insufficient_count,
        },
        "evidence_coverage": {
            "claims_with_evidence": claims_with_evidence,
            "claims_without_evidence": len(claims) - claims_with_evidence,
            "total_evidence_references": total_evidence_refs,
            "average_evidence_per_claim": total_evidence_refs / len(claims) if claims else 0,
        },
        "processing_seed": fever_stats.get("processing_seed"),
        "dataset_source": "FEVER_Dataset",
    }


@pytest.fixture
def verify_fever_fixture_integrity(
    fever_sample_claims: Dict[str, Any],
    fever_sample_evidence: Dict[str, Any],
    fever_mapping: Dict[str, Any],
):
    """Verify the integrity of FEVER fixture data."""

    def _verify() -> Dict[str, Any]:
        issues = []
        claim_ids = {claim["id"] for claim in fever_sample_claims["claims"]}
        evidence_ids = {ev["id"] for ev in fever_sample_evidence["evidence"]}
        mapping_ids = set(fever_mapping["mappings"].keys())

        claim_list = [claim["id"] for claim in fever_sample_claims["claims"]]
        if len(claim_list) != len(claim_ids):
            issues.append("Duplicate claim IDs found in FEVER claims")

        evidence_list = [ev["id"] for ev in fever_sample_evidence["evidence"]]
        if len(evidence_list) != len(evidence_ids):
            issues.append("Duplicate evidence IDs found in FEVER evidence")

        for claim in fever_sample_claims["claims"]:
            for ev_id in claim.get("evidence_ids", []):
                if ev_id not in evidence_ids:
                    issues.append(
                        f"FEVER claim {claim['id']} references non-existent evidence {ev_id}"
                    )

        if claim_ids != mapping_ids:
            missing_in_mapping = claim_ids - mapping_ids
            extra_in_mapping = mapping_ids - claim_ids
            if missing_in_mapping:
                issues.append(f"Claims missing in mapping: {missing_in_mapping}")
            if extra_in_mapping:
                issues.append(f"Extra claims in mapping: {extra_in_mapping}")

        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
        for claim in fever_sample_claims["claims"]:
            if claim["expected_verdict"] not in valid_verdicts:
                issues.append(
                    f"FEVER claim {claim['id']} has invalid verdict: {claim['expected_verdict']}"
                )

        for claim in fever_sample_claims["claims"]:
            if claim.get("source") != "FEVER_Dataset":
                issues.append(
                    f"FEVER claim {claim['id']} has incorrect source: {claim.get('source')}"
                )

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "claim_count": len(claim_ids),
            "evidence_count": len(evidence_ids),
            "mapping_count": len(mapping_ids),
        }

    return _verify
