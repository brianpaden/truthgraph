"""Integration tests validating fixtures work with TruthGraph schemas."""

import pytest


def test_claims_compatible_with_api_schema(test_claims):
    """Test that fixture claims are compatible with API VerifyRequest schema."""
    # From truthgraph/api/models.py - VerifyRequest
    for claim in test_claims["claims"]:
        claim_text = claim["text"]

        # Validate claim text matches VerifyRequest requirements
        assert isinstance(claim_text, str), f"Claim text must be string for {claim['id']}"
        assert 1 <= len(claim_text) <= 2000, f"Claim text must be 1-2000 chars for {claim['id']}"
        assert claim_text.strip(), f"Claim text cannot be empty for {claim['id']}"


def test_evidence_compatible_with_schema(test_evidence):
    """Test that fixture evidence is compatible with Evidence schema."""
    # From truthgraph/schemas.py - Evidence
    for ev in test_evidence["evidence"]:
        # Validate fields exist and are correct types
        assert isinstance(ev["id"], str), f"Evidence ID must be string for {ev['id']}"
        assert isinstance(ev["content"], str), f"Content must be string for {ev['id']}"
        assert len(ev["content"]) > 0, f"Content cannot be empty for {ev['id']}"
        assert isinstance(ev["source"], str), f"Source must be string for {ev['id']}"


def test_verdict_compatible_with_schema(test_claims):
    """Test that fixture verdicts match VerificationResult schema."""
    # From truthgraph/schemas.py - VerificationResult
    valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

    for claim in test_claims["claims"]:
        verdict = claim["expected_verdict"]
        assert verdict in valid_verdicts, f"Invalid verdict for {claim['id']}"

        confidence = claim["confidence"]
        assert isinstance(confidence, (int, float)), f"Confidence must be numeric for {claim['id']}"
        assert 0 <= confidence <= 1, f"Confidence must be 0-1 for {claim['id']}"


def test_nli_labels_match_schema(test_evidence):
    """Test that NLI labels match NLI schema definitions."""
    # From truthgraph/schemas.py - NLIResult
    valid_labels = {"entailment", "contradiction", "neutral"}

    for ev in test_evidence["evidence"]:
        label = ev["nli_label"]
        assert label in valid_labels, f"Invalid NLI label for {ev['id']}"


def test_claim_evidence_linking(test_claims, test_evidence):
    """Test that claims correctly reference evidence."""
    evidence_ids = {ev["id"] for ev in test_evidence["evidence"]}

    for claim in test_claims["claims"]:
        # Every claim should have at least one evidence reference
        assert claim["evidence_ids"], f"Claim {claim['id']} has no evidence references"
        assert isinstance(claim["evidence_ids"], list), (
            f"Evidence IDs must be list for {claim['id']}"
        )

        # All referenced evidence must exist
        for ev_id in claim["evidence_ids"]:
            assert ev_id in evidence_ids, (
                f"Claim {claim['id']} references non-existent evidence {ev_id}"
            )


def test_fixture_supports_verification_pipeline(test_claims, test_evidence):
    """Test that fixtures support verification pipeline flow."""
    # Verify enough data for a realistic verification pipeline run
    assert len(test_claims["claims"]) >= 20, "Need at least 20 claims"
    assert len(test_evidence["evidence"]) >= 40, "Need at least 40 evidence items"

    # Verify diverse verdict distribution for testing
    verdicts = {}
    for claim in test_claims["claims"]:
        v = claim["expected_verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    assert "SUPPORTED" in verdicts, "Must have SUPPORTED claims"
    assert "REFUTED" in verdicts, "Must have REFUTED claims"
    assert "INSUFFICIENT" in verdicts, "Must have INSUFFICIENT claims"

    # Verify evidence has diverse NLI labels
    nli_labels = set()
    for ev in test_evidence["evidence"]:
        nli_labels.add(ev["nli_label"])

    assert len(nli_labels) == 3, "Must have all 3 NLI labels"


def test_fixture_supports_accuracy_testing(test_claims):
    """Test that fixtures support accuracy metric testing."""
    # Ensure high confidence claims for baseline accuracy testing
    high_conf = [c for c in test_claims["claims"] if c["confidence"] >= 0.90]
    assert len(high_conf) >= 15, "Need at least 15 high-confidence baseline claims"

    # Ensure diverse categories for generalization testing
    categories = set()
    for claim in test_claims["claims"]:
        categories.add(claim["category"])

    assert len(categories) >= 4, "Need at least 4 categories for generalization testing"


def test_fixture_supports_regression_testing(test_claims):
    """Test that fixtures support regression testing."""
    # Ensure stable set of claims for regression comparison
    low_conf = [c for c in test_claims["claims"] if c["confidence"] < 0.90]

    # At least some challenging cases for regression detection
    assert len(low_conf) >= 3, "Need challenging claims for regression testing"


def test_fixture_metadata_comprehensive(fixture_metadata):
    """Test that fixture metadata is comprehensive."""
    stats = fixture_metadata

    # Required metadata fields
    required_fields = [
        "total_claims",
        "total_evidence",
        "verdict_distribution",
        "category_distribution",
        "average_confidence",
        "high_confidence_claims",
    ]

    for field in required_fields:
        assert field in stats, f"Missing metadata field: {field}"

    # Verify counts
    assert stats["total_claims"] == 25
    assert stats["total_evidence"] == 55

    # Verify distributions
    assert "SUPPORTED" in stats["verdict_distribution"]
    assert "REFUTED" in stats["verdict_distribution"]
    assert "INSUFFICIENT" in stats["verdict_distribution"]


@pytest.mark.integration
def test_complete_verification_scenario(claim_by_id, evidence_by_id, fixture_metadata):
    """Test a complete verification scenario using fixtures."""
    # Get a high-confidence supported claim
    claim = claim_by_id("test_001")

    # Verify claim has supporting evidence
    assert claim["expected_verdict"] == "SUPPORTED"
    assert len(claim["evidence_ids"]) >= 2

    # Get evidence items
    evidence_items = []
    for ev_id in claim["evidence_ids"]:
        ev = evidence_by_id(ev_id)
        evidence_items.append(ev)
        # Supporting evidence should be entailment-labeled
        if claim["expected_verdict"] == "SUPPORTED":
            assert ev["nli_label"] in ["entailment", "neutral"]

    # Verify we have good evidence for the claim
    assert len(evidence_items) >= 2
    assert all(ev["relevance"] in ["high", "medium"] for ev in evidence_items)

    # Verify fixture metadata is consistent
    stats = fixture_metadata
    assert stats["total_claims"] == 25
    assert stats["high_confidence_claims"] > 15
