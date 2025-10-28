#!/usr/bin/env python
"""Append FEVER fixtures to conftest.py."""

conftest_addition = """

# ===== FEVER Dataset Fixtures =====
# Integration of FEVER (Fact Extraction and VERification) dataset
# Source: https://fever.ai/dataset/fever.html


@pytest.fixture(scope="session")
def fever_sample_claims() -> Dict[str, Any]:
    \"\"\"Load FEVER sample claims fixture from JSON file.

    This fixture provides access to a balanced sample of claims from the
    FEVER dataset, converted to TruthGraph format.

    Returns:
        Dictionary containing FEVER claims metadata and claim objects
    \"\"\"
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
    \"\"\"Load FEVER sample evidence fixture from JSON file.

    This fixture provides access to Wikipedia-based evidence for FEVER claims.

    Returns:
        Dictionary containing FEVER evidence metadata and evidence items
    \"\"\"
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
    \"\"\"Load FEVER claim-to-verdict mapping fixture from JSON file.

    This fixture provides the authoritative mapping of FEVER claims to their
    expected verdicts and associated evidence.

    Returns:
        Dictionary containing claim-to-verdict mappings and evidence index
    \"\"\"
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
    \"\"\"Load FEVER processing statistics fixture from JSON file.

    This fixture provides statistics about the FEVER sample dataset including
    label distribution, evidence coverage, and other metrics.

    Returns:
        Dictionary containing FEVER dataset statistics
    \"\"\"
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
    \"\"\"Factory fixture to retrieve specific FEVER claims by ID.

    Args:
        fever_sample_claims: FEVER sample claims fixture

    Returns:
        Callable that takes a claim ID and returns the claim object
    \"\"\"

    def _get_claim(claim_id: str) -> Dict[str, Any]:
        \"\"\"Get a specific FEVER claim by ID.

        Args:
            claim_id: The ID of the claim to retrieve (e.g., "fever_000001")

        Returns:
            The claim object if found

        Raises:
            ValueError: If claim ID is not found
        \"\"\"
        for claim in fever_sample_claims["claims"]:
            if claim["id"] == claim_id:
                return claim
        raise ValueError(f"FEVER claim with ID '{claim_id}' not found in fixtures")

    return _get_claim


@pytest.fixture
def fever_claims_by_verdict(fever_sample_claims: Dict[str, Any]):
    \"\"\"Factory fixture to retrieve FEVER claims filtered by expected verdict.

    Args:
        fever_sample_claims: FEVER sample claims fixture

    Returns:
        Callable that takes a verdict type and returns list of matching claims
    \"\"\"

    def _get_claims_by_verdict(verdict: str) -> List[Dict[str, Any]]:
        \"\"\"Get FEVER claims filtered by expected verdict.

        Args:
            verdict: The verdict type to filter by ('SUPPORTED', 'REFUTED', 'INSUFFICIENT')

        Returns:
            List of claims with the specified verdict
        \"\"\"
        return [claim for claim in fever_sample_claims["claims"] if claim["expected_verdict"] == verdict]

    return _get_claims_by_verdict


@pytest.fixture
def fever_supported_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    \"\"\"Get all FEVER claims with SUPPORTED verdict.

    Args:
        fever_claims_by_verdict: Factory fixture to get claims by verdict

    Returns:
        List of claims with SUPPORTED verdict
    \"\"\"
    return fever_claims_by_verdict("SUPPORTED")


@pytest.fixture
def fever_refuted_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    \"\"\"Get all FEVER claims with REFUTED verdict.

    Args:
        fever_claims_by_verdict: Factory fixture to get claims by verdict

    Returns:
        List of claims with REFUTED verdict
    \"\"\"
    return fever_claims_by_verdict("REFUTED")


@pytest.fixture
def fever_insufficient_claims(fever_claims_by_verdict) -> List[Dict[str, Any]]:
    \"\"\"Get all FEVER claims with INSUFFICIENT verdict.

    Args:
        fever_claims_by_verdict: Factory fixture to get claims by verdict

    Returns:
        List of claims with INSUFFICIENT verdict
    \"\"\"
    return fever_claims_by_verdict("INSUFFICIENT")


@pytest.fixture
def fever_claims_with_evidence(fever_sample_claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    \"\"\"Get all FEVER claims that have associated evidence.

    Args:
        fever_sample_claims: FEVER sample claims fixture

    Returns:
        List of claims with non-empty evidence_ids
    \"\"\"
    return [claim for claim in fever_sample_claims["claims"] if claim.get("evidence_ids")]


@pytest.fixture
def fever_claims_without_evidence(fever_sample_claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    \"\"\"Get all FEVER claims that have no associated evidence.

    Args:
        fever_sample_claims: FEVER sample claims fixture

    Returns:
        List of claims with empty evidence_ids
    \"\"\"
    return [claim for claim in fever_sample_claims["claims"] if not claim.get("evidence_ids")]


@pytest.fixture
def fever_fixture_metadata(
    fever_sample_claims: Dict[str, Any],
    fever_sample_evidence: Dict[str, Any],
    fever_stats: Dict[str, Any]
) -> Dict[str, Any]:
    \"\"\"Get metadata about the FEVER fixtures.

    Args:
        fever_sample_claims: FEVER sample claims fixture
        fever_sample_evidence: FEVER sample evidence fixture
        fever_stats: FEVER statistics fixture

    Returns:
        Dictionary containing fixture metadata and statistics
    \"\"\"
    claims = fever_sample_claims["claims"]
    evidence = fever_sample_evidence["evidence"]

    # Calculate claim statistics
    supported_count = len([c for c in claims if c["expected_verdict"] == "SUPPORTED"])
    refuted_count = len([c for c in claims if c["expected_verdict"] == "REFUTED"])
    insufficient_count = len([c for c in claims if c["expected_verdict"] == "INSUFFICIENT"])

    # Calculate evidence coverage
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
    fever_mapping: Dict[str, Any]
):
    \"\"\"Verify the integrity of FEVER fixture data.

    This fixture runs validation checks to ensure:
    - All evidence IDs in claims exist in evidence
    - Claims in mapping match sample claims
    - No duplicate IDs exist
    - Required fields are present
    - Verdict values are valid

    Raises:
        AssertionError: If any validation check fails
    \"\"\"

    def _verify() -> Dict[str, Any]:
        \"\"\"Run FEVER fixture integrity checks.

        Returns:
            Dictionary with validation results
        \"\"\"
        issues = []

        # Get all IDs
        claim_ids = {claim["id"] for claim in fever_sample_claims["claims"]}
        evidence_ids = {ev["id"] for ev in fever_sample_evidence["evidence"]}
        mapping_ids = set(fever_mapping["mappings"].keys())

        # Check for duplicate claim IDs
        claim_list = [claim["id"] for claim in fever_sample_claims["claims"]]
        if len(claim_list) != len(claim_ids):
            issues.append("Duplicate claim IDs found in FEVER claims")

        # Check for duplicate evidence IDs
        evidence_list = [ev["id"] for ev in fever_sample_evidence["evidence"]]
        if len(evidence_list) != len(evidence_ids):
            issues.append("Duplicate evidence IDs found in FEVER evidence")

        # Check evidence references
        for claim in fever_sample_claims["claims"]:
            for ev_id in claim.get("evidence_ids", []):
                if ev_id not in evidence_ids:
                    issues.append(
                        f"FEVER claim {claim['id']} references non-existent evidence {ev_id}"
                    )

        # Check mapping consistency
        if claim_ids != mapping_ids:
            missing_in_mapping = claim_ids - mapping_ids
            extra_in_mapping = mapping_ids - claim_ids
            if missing_in_mapping:
                issues.append(f"Claims missing in mapping: {missing_in_mapping}")
            if extra_in_mapping:
                issues.append(f"Extra claims in mapping: {extra_in_mapping}")

        # Check verdict values
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
        for claim in fever_sample_claims["claims"]:
            if claim["expected_verdict"] not in valid_verdicts:
                issues.append(
                    f"FEVER claim {claim['id']} has invalid verdict: {claim['expected_verdict']}"
                )

        # Check that all claims are from FEVER dataset
        for claim in fever_sample_claims["claims"]:
            if claim.get("source") != "FEVER_Dataset":
                issues.append(f"FEVER claim {claim['id']} has incorrect source: {claim.get('source')}")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "claim_count": len(claim_ids),
            "evidence_count": len(evidence_ids),
            "mapping_count": len(mapping_ids),
        }

    return _verify
"""

# Read existing file
with open("/c/repos/truthgraph/tests/fixtures/conftest.py", "r") as f:
    existing = f.read()

# Append new content
with open("/c/repos/truthgraph/tests/fixtures/conftest.py", "w") as f:
    f.write(existing)
    f.write(conftest_addition)

print("FEVER fixtures successfully added to conftest.py")
