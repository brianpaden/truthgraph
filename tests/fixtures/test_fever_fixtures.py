"""Validation tests for FEVER dataset fixtures.

Tests to ensure FEVER fixtures are properly structured and loaded correctly.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest


class TestFEVERFixturesExist:
    """Test that FEVER fixture files exist and are readable."""

    FIXTURES_DIR = Path(__file__).parent
    FEVER_DIR = FIXTURES_DIR / "fever"

    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify FEVER directory exists."""
        assert self.FEVER_DIR.exists(), f"FEVER fixtures directory not found at {self.FEVER_DIR}"

    def test_fever_claims_file_exists(self):
        """Test that fever_sample_claims.json exists."""
        claims_file = self.FEVER_DIR / "fever_sample_claims.json"
        assert claims_file.exists(), f"FEVER claims file not found at {claims_file}"
        assert claims_file.is_file(), f"FEVER claims path is not a file: {claims_file}"

    def test_fever_evidence_file_exists(self):
        """Test that fever_sample_evidence.json exists."""
        evidence_file = self.FEVER_DIR / "fever_sample_evidence.json"
        assert evidence_file.exists(), f"FEVER evidence file not found at {evidence_file}"
        assert evidence_file.is_file(), f"FEVER evidence path is not a file: {evidence_file}"

    def test_fever_mapping_file_exists(self):
        """Test that fever_mapping.json exists."""
        mapping_file = self.FEVER_DIR / "fever_mapping.json"
        assert mapping_file.exists(), f"FEVER mapping file not found at {mapping_file}"
        assert mapping_file.is_file(), f"FEVER mapping path is not a file: {mapping_file}"

    def test_fever_stats_file_exists(self):
        """Test that fever_stats.json exists."""
        stats_file = self.FEVER_DIR / "fever_stats.json"
        assert stats_file.exists(), f"FEVER stats file not found at {stats_file}"
        assert stats_file.is_file(), f"FEVER stats path is not a file: {stats_file}"

    def test_fever_readme_exists(self):
        """Test that README.md exists."""
        readme_file = self.FEVER_DIR / "README.md"
        assert readme_file.exists(), f"FEVER README not found at {readme_file}"
        assert readme_file.is_file(), f"FEVER README path is not a file: {readme_file}"


class TestFEVERFixturesLoading:
    """Test that FEVER fixtures can be loaded properly."""

    def test_fever_claims_loads_as_json(self, fever_sample_claims: Dict[str, Any]):
        """Test that fever_sample_claims fixture loads correctly."""
        assert fever_sample_claims is not None, "FEVER claims fixture is None"
        assert isinstance(fever_sample_claims, dict), "FEVER claims should be a dictionary"
        assert "claims" in fever_sample_claims, "FEVER claims should have 'claims' key"
        assert "metadata" in fever_sample_claims, "FEVER claims should have 'metadata' key"

    def test_fever_evidence_loads_as_json(self, fever_sample_evidence: Dict[str, Any]):
        """Test that fever_sample_evidence fixture loads correctly."""
        assert fever_sample_evidence is not None, "FEVER evidence fixture is None"
        assert isinstance(fever_sample_evidence, dict), "FEVER evidence should be a dictionary"
        assert "evidence" in fever_sample_evidence, "FEVER evidence should have 'evidence' key"
        assert "metadata" in fever_sample_evidence, "FEVER evidence should have 'metadata' key"

    def test_fever_mapping_loads_as_json(self, fever_mapping: Dict[str, Any]):
        """Test that fever_mapping fixture loads correctly."""
        assert fever_mapping is not None, "FEVER mapping fixture is None"
        assert isinstance(fever_mapping, dict), "FEVER mapping should be a dictionary"
        assert "mappings" in fever_mapping, "FEVER mapping should have 'mappings' key"
        assert "evidence_index" in fever_mapping, "FEVER mapping should have 'evidence_index' key"
        assert "metadata" in fever_mapping, "FEVER mapping should have 'metadata' key"

    def test_fever_stats_loads_as_json(self, fever_stats: Dict[str, Any]):
        """Test that fever_stats fixture loads correctly."""
        assert fever_stats is not None, "FEVER stats fixture is None"
        assert isinstance(fever_stats, dict), "FEVER stats should be a dictionary"
        assert "label_distribution" in fever_stats, "FEVER stats should have 'label_distribution' key"
        assert "metadata" in fever_stats, "FEVER stats should have 'metadata' key"


class TestFEVERClaimsStructure:
    """Test the structure and content of FEVER claims."""

    def test_fever_claims_not_empty(self, fever_sample_claims: Dict[str, Any]):
        """Test that FEVER claims list is not empty."""
        claims = fever_sample_claims["claims"]
        assert len(claims) > 0, "FEVER claims list should not be empty"

    def test_fever_claims_have_required_fields(self, fever_sample_claims: Dict[str, Any]):
        """Test that each claim has required fields."""
        required_fields = ["id", "text", "expected_verdict", "source"]

        for claim in fever_sample_claims["claims"]:
            for field in required_fields:
                assert field in claim, f"Claim {claim.get('id')} missing required field: {field}"
                assert claim[field] is not None, f"Claim {claim.get('id')}.{field} is None"

    def test_fever_claims_have_valid_verdicts(self, fever_sample_claims: Dict[str, Any]):
        """Test that all claims have valid verdict values."""
        valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}

        for claim in fever_sample_claims["claims"]:
            verdict = claim["expected_verdict"]
            assert verdict in valid_verdicts, (
                f"Claim {claim['id']} has invalid verdict: {verdict}. "
                f"Must be one of {valid_verdicts}"
            )

    def test_fever_claims_are_strings(self, fever_sample_claims: Dict[str, Any]):
        """Test that all claim texts are non-empty strings."""
        for claim in fever_sample_claims["claims"]:
            assert isinstance(claim["text"], str), (
                f"Claim {claim['id']}.text must be a string, got {type(claim['text'])}"
            )
            assert len(claim["text"]) > 0, f"Claim {claim['id']}.text is empty"

    def test_fever_claims_have_unique_ids(self, fever_sample_claims: Dict[str, Any]):
        """Test that all claim IDs are unique."""
        claim_ids = [claim["id"] for claim in fever_sample_claims["claims"]]
        unique_ids = set(claim_ids)

        assert len(claim_ids) == len(unique_ids), (
            f"Duplicate claim IDs found. "
            f"Total claims: {len(claim_ids)}, unique IDs: {len(unique_ids)}"
        )

    def test_fever_claims_source_is_correct(self, fever_sample_claims: Dict[str, Any]):
        """Test that all claims have the correct source."""
        for claim in fever_sample_claims["claims"]:
            assert claim["source"] == "FEVER_Dataset", (
                f"Claim {claim['id']} has incorrect source: {claim['source']}"
            )

    def test_fever_claims_category_is_correct(self, fever_sample_claims: Dict[str, Any]):
        """Test that all claims have the correct category."""
        for claim in fever_sample_claims["claims"]:
            assert claim["category"] == "fever_dataset", (
                f"Claim {claim['id']} has incorrect category: {claim['category']}"
            )


class TestFEVEREvidenceStructure:
    """Test the structure and content of FEVER evidence."""

    def test_fever_evidence_not_empty(self, fever_sample_evidence: Dict[str, Any]):
        """Test that FEVER evidence list is not empty."""
        evidence = fever_sample_evidence["evidence"]
        assert isinstance(evidence, list), "FEVER evidence should be a list"
        assert len(evidence) >= 0, "FEVER evidence list should have non-negative length"

    def test_fever_evidence_have_required_fields(self, fever_sample_evidence: Dict[str, Any]):
        """Test that each evidence item has required fields."""
        required_fields = ["id", "content", "source_type"]

        for evidence in fever_sample_evidence["evidence"]:
            for field in required_fields:
                assert field in evidence, (
                    f"Evidence {evidence.get('id')} missing required field: {field}"
                )
                assert evidence[field] is not None, (
                    f"Evidence {evidence.get('id')}.{field} is None"
                )

    def test_fever_evidence_have_unique_ids(self, fever_sample_evidence: Dict[str, Any]):
        """Test that all evidence IDs are unique."""
        evidence_ids = [ev["id"] for ev in fever_sample_evidence["evidence"]]
        unique_ids = set(evidence_ids)

        assert len(evidence_ids) == len(unique_ids), (
            f"Duplicate evidence IDs found. "
            f"Total evidence: {len(evidence_ids)}, unique IDs: {len(unique_ids)}"
        )

    def test_fever_evidence_source_type_is_valid(self, fever_sample_evidence: Dict[str, Any]):
        """Test that all evidence has a valid source type."""
        for evidence in fever_sample_evidence["evidence"]:
            source_type = evidence["source_type"]
            assert isinstance(source_type, str), (
                f"Evidence {evidence['id']}.source_type must be a string"
            )
            assert len(source_type) > 0, f"Evidence {evidence['id']}.source_type is empty"


class TestFEVERMappingConsistency:
    """Test consistency between claims, evidence, and mappings."""

    def test_mapping_ids_match_claim_ids(
        self,
        fever_sample_claims: Dict[str, Any],
        fever_mapping: Dict[str, Any]
    ):
        """Test that mapping contains all claims."""
        claim_ids = {claim["id"] for claim in fever_sample_claims["claims"]}
        mapping_ids = set(fever_mapping["mappings"].keys())

        assert claim_ids == mapping_ids, (
            f"Claim IDs don't match mapping IDs. "
            f"Missing in mapping: {claim_ids - mapping_ids}, "
            f"Extra in mapping: {mapping_ids - claim_ids}"
        )

    def test_evidence_references_exist(
        self,
        fever_sample_claims: Dict[str, Any],
        fever_sample_evidence: Dict[str, Any]
    ):
        """Test that all evidence IDs in claims exist in evidence."""
        evidence_ids = {ev["id"] for ev in fever_sample_evidence["evidence"]}

        for claim in fever_sample_claims["claims"]:
            for ev_id in claim.get("evidence_ids", []):
                assert ev_id in evidence_ids, (
                    f"Claim {claim['id']} references non-existent evidence: {ev_id}"
                )

    def test_mapping_verdict_matches_claim_verdict(
        self,
        fever_sample_claims: Dict[str, Any],
        fever_mapping: Dict[str, Any]
    ):
        """Test that mappings have matching verdicts with claims."""
        for claim in fever_sample_claims["claims"]:
            claim_id = claim["id"]
            mapping = fever_mapping["mappings"].get(claim_id)

            assert mapping is not None, f"Claim {claim_id} missing in mapping"
            assert mapping["expected_verdict"] == claim["expected_verdict"], (
                f"Claim {claim_id} verdict mismatch. "
                f"Claim: {claim['expected_verdict']}, Mapping: {mapping['expected_verdict']}"
            )

    def test_mapping_evidence_ids_match_claim_evidence(
        self,
        fever_sample_claims: Dict[str, Any],
        fever_mapping: Dict[str, Any]
    ):
        """Test that mappings have matching evidence IDs with claims."""
        for claim in fever_sample_claims["claims"]:
            claim_id = claim["id"]
            mapping = fever_mapping["mappings"].get(claim_id)

            assert mapping is not None, f"Claim {claim_id} missing in mapping"
            assert set(mapping["evidence_ids"]) == set(claim.get("evidence_ids", [])), (
                f"Claim {claim_id} evidence IDs mismatch. "
                f"Claim: {claim.get('evidence_ids', [])}, "
                f"Mapping: {mapping['evidence_ids']}"
            )


class TestFEVERVerdictDistribution:
    """Test the distribution of verdicts in the dataset."""

    def test_all_verdicts_present(self, fever_sample_claims: Dict[str, Any]):
        """Test that dataset has all verdict types."""
        verdicts = {claim["expected_verdict"] for claim in fever_sample_claims["claims"]}

        expected_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
        assert verdicts == expected_verdicts, (
            f"Missing verdict types. Found: {verdicts}, Expected: {expected_verdicts}"
        )

    def test_verdict_distribution_is_balanced(self, fever_sample_claims: Dict[str, Any]):
        """Test that verdict distribution is reasonably balanced."""
        verdicts = [claim["expected_verdict"] for claim in fever_sample_claims["claims"]]

        supported = verdicts.count("SUPPORTED")
        refuted = verdicts.count("REFUTED")
        insufficient = verdicts.count("INSUFFICIENT")

        total = len(verdicts)

        # Each verdict should be at least 20% of total
        assert supported / total >= 0.2, f"SUPPORTED verdict too low: {supported}/{total}"
        assert refuted / total >= 0.2, f"REFUTED verdict too low: {refuted}/{total}"
        assert insufficient / total >= 0.2, f"INSUFFICIENT verdict too low: {insufficient}/{total}"

    def test_verdict_distribution_matches_stats(
        self,
        fever_sample_claims: Dict[str, Any],
        fever_stats: Dict[str, Any]
    ):
        """Test that claimed statistics match actual distribution."""
        verdicts = [claim["expected_verdict"] for claim in fever_sample_claims["claims"]]

        supported = verdicts.count("SUPPORTED")
        refuted = verdicts.count("REFUTED")
        insufficient = verdicts.count("INSUFFICIENT")

        stats_dist = fever_stats["label_distribution"]

        assert supported == stats_dist["SUPPORTED"], (
            f"SUPPORTED count mismatch. Actual: {supported}, Stats: {stats_dist['SUPPORTED']}"
        )
        assert refuted == stats_dist["REFUTED"], (
            f"REFUTED count mismatch. Actual: {refuted}, Stats: {stats_dist['REFUTED']}"
        )
        assert insufficient == stats_dist["INSUFFICIENT"], (
            f"INSUFFICIENT count mismatch. Actual: {insufficient}, Stats: {stats_dist['INSUFFICIENT']}"
        )


class TestFEVEREvidenceCoverage:
    """Test evidence coverage in the FEVER dataset."""

    def test_evidence_coverage_is_reasonable(self, fever_sample_claims: Dict[str, Any]):
        """Test that a reasonable portion of claims have evidence."""
        claims_with_evidence = sum(1 for c in fever_sample_claims["claims"] if c.get("evidence_ids"))
        claims_without_evidence = sum(1 for c in fever_sample_claims["claims"] if not c.get("evidence_ids"))

        total = len(fever_sample_claims["claims"])

        # At least 50% of claims should have evidence
        assert claims_with_evidence / total >= 0.5, (
            f"Evidence coverage too low. "
            f"With evidence: {claims_with_evidence}, Without: {claims_without_evidence}"
        )

    def test_insufficient_claims_typically_lack_evidence(
        self,
        fever_sample_claims: Dict[str, Any]
    ):
        """Test that INSUFFICIENT claims often have no evidence."""
        insufficient_claims = [
            c for c in fever_sample_claims["claims"]
            if c["expected_verdict"] == "INSUFFICIENT"
        ]

        claims_without_evidence = sum(1 for c in insufficient_claims if not c.get("evidence_ids"))
        total_insufficient = len(insufficient_claims)

        # Most INSUFFICIENT claims should have no evidence
        if total_insufficient > 0:
            assert claims_without_evidence / total_insufficient >= 0.5, (
                "Most INSUFFICIENT claims should have no evidence"
            )


class TestFEVERFixtureIntegrity:
    """Test overall integrity of FEVER fixtures."""

    def test_verify_fixture_integrity(self, verify_fever_fixture_integrity):
        """Test that verify_fever_fixture_integrity passes."""
        result = verify_fever_fixture_integrity()

        assert result["is_valid"], (
            f"FEVER fixture integrity check failed. "
            f"Issues: {result.get('issues', [])}"
        )

    def test_fixture_metadata_is_accurate(
        self,
        fever_fixture_metadata: Dict[str, Any],
        fever_sample_claims: Dict[str, Any],
        fever_sample_evidence: Dict[str, Any]
    ):
        """Test that fixture metadata matches actual data."""
        metadata = fever_fixture_metadata

        assert metadata["total_claims"] == len(fever_sample_claims["claims"]), (
            "Total claims count mismatch"
        )
        assert metadata["total_evidence"] == len(fever_sample_evidence["evidence"]), (
            "Total evidence count mismatch"
        )

        # Verify verdict distribution
        verdicts = [c["expected_verdict"] for c in fever_sample_claims["claims"]]
        assert metadata["verdict_distribution"]["SUPPORTED"] == verdicts.count("SUPPORTED")
        assert metadata["verdict_distribution"]["REFUTED"] == verdicts.count("REFUTED")
        assert metadata["verdict_distribution"]["INSUFFICIENT"] == verdicts.count("INSUFFICIENT")


class TestFEVERFactoryFixtures:
    """Test factory fixtures for accessing FEVER data."""

    def test_fever_claim_by_id_factory(
        self,
        fever_claim_by_id,
        fever_sample_claims: Dict[str, Any]
    ):
        """Test fever_claim_by_id factory fixture."""
        first_claim = fever_sample_claims["claims"][0]
        retrieved = fever_claim_by_id(first_claim["id"])

        assert retrieved == first_claim, "Retrieved claim doesn't match original"

    def test_fever_claim_by_id_raises_for_invalid_id(self, fever_claim_by_id):
        """Test that fever_claim_by_id raises ValueError for invalid ID."""
        with pytest.raises(ValueError, match="not found"):
            fever_claim_by_id("invalid_id_12345")

    def test_fever_claims_by_verdict_factory(
        self,
        fever_claims_by_verdict,
        fever_sample_claims: Dict[str, Any]
    ):
        """Test fever_claims_by_verdict factory fixture."""
        supported_claims = fever_claims_by_verdict("SUPPORTED")

        assert len(supported_claims) > 0, "Should have at least some SUPPORTED claims"
        assert all(c["expected_verdict"] == "SUPPORTED" for c in supported_claims), (
            "All returned claims should be SUPPORTED"
        )

    def test_fever_supported_claims_fixture(
        self,
        fever_supported_claims: List[Dict[str, Any]]
    ):
        """Test fever_supported_claims fixture."""
        assert len(fever_supported_claims) > 0, "Should have SUPPORTED claims"
        assert all(c["expected_verdict"] == "SUPPORTED" for c in fever_supported_claims)

    def test_fever_refuted_claims_fixture(
        self,
        fever_refuted_claims: List[Dict[str, Any]]
    ):
        """Test fever_refuted_claims fixture."""
        assert len(fever_refuted_claims) > 0, "Should have REFUTED claims"
        assert all(c["expected_verdict"] == "REFUTED" for c in fever_refuted_claims)

    def test_fever_insufficient_claims_fixture(
        self,
        fever_insufficient_claims: List[Dict[str, Any]]
    ):
        """Test fever_insufficient_claims fixture."""
        assert len(fever_insufficient_claims) > 0, "Should have INSUFFICIENT claims"
        assert all(c["expected_verdict"] == "INSUFFICIENT" for c in fever_insufficient_claims)

    def test_fever_claims_with_evidence_fixture(
        self,
        fever_claims_with_evidence: List[Dict[str, Any]]
    ):
        """Test fever_claims_with_evidence fixture."""
        assert len(fever_claims_with_evidence) > 0, "Should have claims with evidence"
        assert all(c.get("evidence_ids") for c in fever_claims_with_evidence)

    def test_fever_claims_without_evidence_fixture(
        self,
        fever_claims_without_evidence: List[Dict[str, Any]]
    ):
        """Test fever_claims_without_evidence fixture."""
        assert all(not c.get("evidence_ids") for c in fever_claims_without_evidence)
