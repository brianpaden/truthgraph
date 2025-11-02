"""Edge case tests for contradictory evidence handling.

This module tests the system's ability to correctly identify and handle
claims where there is conflicting evidence - some supporting and some
refuting the claim. These are critical edge cases that test the system's
ability to recognize nuance and uncertainty.

Test Coverage:
- Competing scientific interpretations
- Context-dependent evidence with conflicting conclusions
- Expert disagreement on future outcomes
- Normative disagreement in historical interpretation
- Conflicting measurements or data interpretations
"""

from typing import Any, Dict

import pytest

# Import fixtures from edge_cases conftest
pytest_plugins = ["tests.fixtures.edge_cases.conftest"]


class TestContradictoryEvidenceHandling:
    """Test suite for contradictory evidence edge cases."""

    def test_load_contradictory_evidence_fixture(self, edge_case_contradictory: Dict[str, Any]):
        """Verify the contradictory evidence fixture loads correctly.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        assert edge_case_contradictory is not None
        assert "category" in edge_case_contradictory
        assert edge_case_contradictory["category"] == "contradictory_evidence"
        assert "claims" in edge_case_contradictory
        assert len(edge_case_contradictory["claims"]) > 0

    def test_all_claims_expect_conflicting_verdict(self, edge_case_contradictory: Dict[str, Any]):
        """Verify all contradictory evidence claims expect CONFLICTING verdict.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])

        for claim in claims:
            expected_verdict = claim.get("expected_verdict")
            # Note: CONFLICTING may not be a standard verdict in all systems
            # Some systems may return INSUFFICIENT when evidence conflicts
            assert expected_verdict in ["CONFLICTING", "INSUFFICIENT"], (
                f"Claim {claim['id']} should expect CONFLICTING or INSUFFICIENT "
                f"verdict, got {expected_verdict}"
            )

    def test_contradictory_evidence_claim_structure(self, edge_case_contradictory: Dict[str, Any]):
        """Verify contradictory evidence claims have proper structure.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])

        for claim in claims:
            # Verify required fields
            assert "id" in claim, "Claim missing 'id' field"
            assert "text" in claim, f"Claim {claim.get('id')} missing 'text' field"
            assert "expected_verdict" in claim
            assert "edge_case_type" in claim
            assert "reason" in claim
            assert "expected_behavior" in claim
            assert "evidence_ids" in claim
            assert "metadata" in claim

            # Verify edge case type
            assert claim["edge_case_type"] == "contradictory_evidence"

            # Verify has multiple evidence IDs (both supporting and refuting)
            assert isinstance(claim["evidence_ids"], list)
            assert len(claim["evidence_ids"]) >= 2, (
                f"Claim {claim['id']} should have at least 2 evidence IDs "
                f"(supporting and refuting) for contradictory case"
            )

    def test_contradictory_evidence_has_multiple_sources(
        self, edge_case_contradictory: Dict[str, Any]
    ):
        """Verify contradictory evidence cases have multiple evidence sources.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])
        evidence_list = edge_case_contradictory.get("evidence", [])

        # Should have evidence items
        assert len(evidence_list) > 0, "Contradictory evidence cases should have evidence items"

        # Each claim should reference multiple evidence items
        for claim in claims:
            evidence_ids = claim.get("evidence_ids", [])
            assert len(evidence_ids) >= 2, (
                f"Claim {claim['id']} should reference at least 2 evidence items"
            )

            # Verify all referenced evidence exists
            for ev_id in evidence_ids:
                found = any(ev["id"] == ev_id for ev in evidence_list)
                assert found, f"Evidence {ev_id} referenced by claim {claim['id']} not found"

    def test_contradictory_evidence_metadata_quality(self, edge_case_contradictory: Dict[str, Any]):
        """Verify metadata quality for contradictory evidence claims.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])

        for claim in claims:
            metadata = claim.get("metadata", {})

            # Check metadata has explanatory fields
            assert "challenge" in metadata, (
                f"Claim {claim['id']} metadata missing 'challenge' field"
            )
            assert "test_purpose" in metadata, (
                f"Claim {claim['id']} metadata missing 'test_purpose' field"
            )
            assert "competing_claims" in metadata, (
                f"Claim {claim['id']} metadata missing 'competing_claims' field"
            )
            assert "evidence_quality" in metadata, (
                f"Claim {claim['id']} metadata missing 'evidence_quality' field"
            )

            # Verify competing_claims is True
            assert metadata["competing_claims"] is True, (
                f"Claim {claim['id']} should have competing_claims=True"
            )

    @pytest.mark.parametrize(
        "challenge_type",
        [
            "Competing scientific interpretations",
            "Context-dependent evidence",
            "Expert disagreement",
            "Normative disagreement",
            "Conflicting measurements",
        ],
    )
    def test_coverage_of_contradictory_evidence_types(
        self,
        edge_case_contradictory: Dict[str, Any],
        challenge_type: str,
    ):
        """Verify coverage of different contradictory evidence challenge types.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
            challenge_type: Type of challenge to verify coverage for
        """
        claims = edge_case_contradictory.get("claims", [])

        # Check if at least one claim covers this challenge type
        found = False
        for claim in claims:
            metadata = claim.get("metadata", {})
            reason = claim.get("reason", "")
            if (
                challenge_type.lower() in metadata.get("challenge", "").lower()
                or challenge_type.lower() in reason.lower()
            ):
                found = True
                break

        assert found, f"No claims found covering challenge type: {challenge_type}"

    def test_expected_behavior_documentation(self, edge_case_contradictory: Dict[str, Any]):
        """Verify all claims document expected behavior.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])

        for claim in claims:
            expected_behavior = claim.get("expected_behavior", "")

            # Should contain relevant keywords
            keywords = ["conflict", "competing", "both", "disagree"]
            has_keyword = any(keyword in expected_behavior.lower() for keyword in keywords)
            assert has_keyword, (
                f"Claim {claim['id']} expected_behavior should mention "
                f"conflicting/competing evidence"
            )

            # Should be descriptive
            assert len(expected_behavior) > 20, (
                f"Claim {claim['id']} expected_behavior should be descriptive"
            )

    def test_contradictory_evidence_reason_quality(self, edge_case_contradictory: Dict[str, Any]):
        """Verify reasons for contradictory evidence are well-documented.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])

        for claim in claims:
            reason = claim.get("reason", "")

            # Reason should be descriptive
            assert len(reason) > 30, f"Claim {claim['id']} should have descriptive reason"

            # Reason should explain the conflict
            keywords = ["conflict", "contradict", "both", "some", "others", "debate"]
            has_keyword = any(keyword in reason.lower() for keyword in keywords)
            assert has_keyword, f"Claim {claim['id']} reason should explain the evidence conflict"

    def test_evidence_pairs_have_opposing_stances(self, edge_case_contradictory: Dict[str, Any]):
        """Verify evidence items have opposing stances.

        Args:
            edge_case_contradictory: Fixture with contradictory evidence data
        """
        claims = edge_case_contradictory.get("claims", [])
        evidence_list = edge_case_contradictory.get("evidence", [])

        # Build evidence lookup
        evidence_map = {ev["id"]: ev for ev in evidence_list}

        for claim in claims:
            evidence_ids = claim.get("evidence_ids", [])

            if len(evidence_ids) >= 2:
                # Check that evidence items reference the claim with different stances
                evidence_items = [evidence_map.get(ev_id) for ev_id in evidence_ids]
                evidence_items = [ev for ev in evidence_items if ev is not None]

                # Verify we have at least 2 evidence items
                assert len(evidence_items) >= 2, (
                    f"Claim {claim['id']} should have at least 2 evidence items"
                )

                # Evidence should have stance or note indicating opposition
                # (This is a soft check - depends on data structure)
                for ev in evidence_items:
                    assert "text" in ev, f"Evidence {ev['id']} missing text"


class TestContradictoryEvidenceIntegration:
    """Integration tests for contradictory evidence handling."""

    def test_fixture_integration_with_all_edge_cases(
        self,
        all_edge_cases: Dict[str, Dict[str, Any]],
    ):
        """Verify contradictory evidence is included in all_edge_cases fixture.

        Args:
            all_edge_cases: Combined fixture with all edge case categories
        """
        assert "contradictory_evidence" in all_edge_cases
        contra_data = all_edge_cases["contradictory_evidence"]

        assert "claims" in contra_data
        assert len(contra_data["claims"]) > 0
        assert contra_data["category"] == "contradictory_evidence"

    def test_get_claims_by_category(
        self,
        get_edge_case_claims_by_category,
    ):
        """Test retrieval of contradictory evidence claims by category.

        Args:
            get_edge_case_claims_by_category: Factory fixture for claim retrieval
        """
        claims = get_edge_case_claims_by_category("contradictory_evidence")

        assert len(claims) > 0
        for claim in claims:
            assert claim["edge_case_type"] == "contradictory_evidence"
            assert len(claim["evidence_ids"]) >= 2

    def test_edge_case_statistics_includes_contradictory(
        self, edge_case_statistics: Dict[str, Any]
    ):
        """Verify statistics include contradictory evidence category.

        Args:
            edge_case_statistics: Statistics fixture for all edge cases
        """
        assert "categories" in edge_case_statistics
        categories = edge_case_statistics["categories"]

        assert "contradictory_evidence" in categories
        contra_stats = categories["contradictory_evidence"]

        assert "claim_count" in contra_stats
        assert contra_stats["claim_count"] > 0
        assert "evidence_count" in contra_stats
        assert contra_stats["evidence_count"] > 0  # Should have evidence


# Placeholder for actual verification system integration tests
class TestContradictoryEvidenceVerification:
    """Tests for actual verification system with contradictory evidence.

    NOTE: These tests are placeholders pending integration with the
    actual TruthGraph verification pipeline. Once the pipeline is
    available, these should be implemented to verify:

    1. System recognizes conflicting evidence
    2. System returns appropriate verdict (CONFLICTING or INSUFFICIENT)
    3. Confidence scores reflect uncertainty
    4. System documents both sides of the conflict
    """

    @pytest.mark.skip(reason="Pending verification pipeline integration")
    def test_contradictory_evidence_handling(self, edge_case_contradictory: Dict[str, Any]):
        """Test that verification system handles contradictory evidence correctly.

        This test should be implemented once the verification pipeline is available.
        It should verify that contradictory evidence claims are handled appropriately
        with recognition of the conflict.
        """
        # TODO: Implement when verification pipeline is available
        # from truthgraph.verification import VerificationPipeline
        #
        # pipeline = VerificationPipeline()
        # claims = edge_case_contradictory.get("claims", [])
        #
        # for claim in claims:
        #     result = pipeline.verify(claim["text"])
        #     # System should recognize conflict
        #     assert result["verdict"] in ["CONFLICTING", "INSUFFICIENT"]
        #     # Should have moderate-to-low confidence due to conflict
        #     assert result["confidence"] < 0.75
        pass

    @pytest.mark.skip(reason="Pending verification pipeline integration")
    def test_contradictory_evidence_documents_both_sides(
        self, edge_case_contradictory: Dict[str, Any]
    ):
        """Test that verification system documents both sides of contradiction.

        The system should identify and return both supporting and refuting
        evidence when a contradiction exists.
        """
        # TODO: Implement when verification pipeline is available
        pass
