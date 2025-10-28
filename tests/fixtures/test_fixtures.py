"""Test fixtures to validate fixture integrity and basic functionality."""


def test_claims_fixture_loads(test_claims):
    """Test that test_claims fixture loads correctly."""
    assert test_claims is not None
    assert "claims" in test_claims
    assert "metadata" in test_claims
    assert len(test_claims["claims"]) == 25


def test_evidence_fixture_loads(test_evidence):
    """Test that test_evidence fixture loads correctly."""
    assert test_evidence is not None
    assert "evidence" in test_evidence
    assert "metadata" in test_evidence
    assert len(test_evidence["evidence"]) == 55


def test_claim_by_id_factory(claim_by_id):
    """Test claim_by_id factory fixture."""
    claim = claim_by_id("test_001")
    assert claim["id"] == "test_001"
    assert claim["expected_verdict"] == "SUPPORTED"
    assert claim["confidence"] == 0.95


def test_evidence_by_id_factory(evidence_by_id):
    """Test evidence_by_id factory fixture."""
    evidence = evidence_by_id("ev_001")
    assert evidence["id"] == "ev_001"
    assert evidence["nli_label"] == "entailment"


def test_claims_by_verdict(claims_by_verdict):
    """Test claims_by_verdict factory fixture."""
    supported = claims_by_verdict("SUPPORTED")
    refuted = claims_by_verdict("REFUTED")
    insufficient = claims_by_verdict("INSUFFICIENT")

    assert len(supported) == 15
    assert len(refuted) == 8
    assert len(insufficient) == 2


def test_claims_by_category(claims_by_category):
    """Test claims_by_category factory fixture."""
    science = claims_by_category("science")
    health = claims_by_category("health")
    history = claims_by_category("history")

    assert len(science) == 8
    assert len(health) == 5
    assert len(history) == 5


def test_all_claims_have_required_fields(test_claims):
    """Test that all claims have required fields."""
    required_fields = ["id", "text", "category", "expected_verdict", "confidence", "evidence_ids"]

    for claim in test_claims["claims"]:
        for field in required_fields:
            assert field in claim, f"Claim {claim.get('id')} missing field: {field}"


def test_all_evidence_has_required_fields(test_evidence):
    """Test that all evidence items have required fields."""
    required_fields = ["id", "content", "source", "url", "relevance", "type", "nli_label"]

    for ev in test_evidence["evidence"]:
        for field in required_fields:
            assert field in ev, f"Evidence {ev.get('id')} missing field: {field}"


def test_verdict_values_valid(test_claims):
    """Test that all verdict values are valid."""
    valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

    for claim in test_claims["claims"]:
        assert claim["expected_verdict"] in valid_verdicts, f"Invalid verdict in {claim['id']}"


def test_confidence_values_valid(test_claims):
    """Test that all confidence values are between 0 and 1."""
    for claim in test_claims["claims"]:
        confidence = claim["confidence"]
        assert 0 <= confidence <= 1, f"Invalid confidence in {claim['id']}: {confidence}"


def test_nli_labels_valid(test_evidence):
    """Test that all NLI labels are valid."""
    valid_labels = {"entailment", "contradiction", "neutral"}

    for ev in test_evidence["evidence"]:
        assert ev["nli_label"] in valid_labels, f"Invalid NLI label in {ev['id']}"


def test_claim_evidence_references_valid(test_claims, test_evidence):
    """Test that all claim evidence references are valid."""
    evidence_ids = {ev["id"] for ev in test_evidence["evidence"]}

    for claim in test_claims["claims"]:
        for ev_id in claim["evidence_ids"]:
            assert ev_id in evidence_ids, (
                f"Claim {claim['id']} references non-existent evidence {ev_id}"
            )
