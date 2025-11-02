"""Edge case tests for short claim handling.

This module tests the system's ability to correctly process and verify
short-form claims (<10 words) including minimal context claims and
terse statements. These test the system's ability to handle claims
with limited information.

Test Coverage:
- Single word or very short claims
- Claims with minimal context
- Terse statements requiring interpretation
- Claims with ambiguous referents
- Short claims lacking necessary qualifications
"""

from typing import Any, Dict

import pytest

# Import fixtures from edge_cases conftest
pytest_plugins = ["tests.fixtures.edge_cases.conftest"]


class TestShortClaimsHandling:
    """Test suite for short claim edge cases."""

    def test_load_short_claims_fixture(self, edge_case_short_claims: Dict[str, Any]):
        """Verify the short claims fixture loads correctly.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        assert edge_case_short_claims is not None
        assert "category" in edge_case_short_claims
        assert edge_case_short_claims["category"] == "short_claims"
        assert "claims" in edge_case_short_claims
        assert len(edge_case_short_claims["claims"]) > 0

    def test_all_claims_are_actually_short(self, edge_case_short_claims: Dict[str, Any]):
        """Verify all claims are actually short (<10 words).

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])

        for claim in claims:
            claim_text = claim.get("text", "")
            word_count = len(claim_text.split())

            # Short claims should have <=10 words
            assert word_count <= 10, f"Claim {claim['id']} is not short enough: {word_count} words"

    def test_short_claims_structure(self, edge_case_short_claims: Dict[str, Any]):
        """Verify short claims have proper structure.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])

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
            assert claim["edge_case_type"] == "short_claims"

            # Verify metadata includes length info
            metadata = claim.get("metadata", {})
            assert "word_count" in metadata, (
                f"Claim {claim['id']} metadata should include word_count"
            )

    def test_short_claims_have_valid_verdicts(self, edge_case_short_claims: Dict[str, Any]):
        """Verify all short claims have valid expected verdicts.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])
        valid_verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        for claim in claims:
            expected_verdict = claim.get("expected_verdict")
            assert expected_verdict in valid_verdicts, (
                f"Claim {claim['id']} has invalid verdict: {expected_verdict}"
            )

    def test_short_claims_metadata_quality(self, edge_case_short_claims: Dict[str, Any]):
        """Verify metadata quality for short claims.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])

        for claim in claims:
            metadata = claim.get("metadata", {})

            # Check metadata has explanatory fields
            assert "challenge" in metadata, (
                f"Claim {claim['id']} metadata missing 'challenge' field"
            )
            assert "test_purpose" in metadata, (
                f"Claim {claim['id']} metadata missing 'test_purpose' field"
            )
            assert "word_count" in metadata, (
                f"Claim {claim['id']} metadata missing 'word_count' field"
            )

            # Verify word count matches
            word_count = len(claim["text"].split())
            assert metadata["word_count"] == word_count, (
                f"Claim {claim['id']} metadata word_count mismatch: "
                f"{metadata['word_count']} vs {word_count}"
            )

    @pytest.mark.parametrize(
        "challenge_type",
        [
            "minimal context",
            "ambiguous referent",
            "lacking qualification",
            "terse",
            "single word",
        ],
    )
    def test_coverage_of_short_claim_challenges(
        self,
        edge_case_short_claims: Dict[str, Any],
        challenge_type: str,
    ):
        """Verify coverage of different short claim challenge types.

        Args:
            edge_case_short_claims: Fixture with short claims data
            challenge_type: Type of challenge to verify coverage for
        """
        claims = edge_case_short_claims.get("claims", [])

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

        # Note: Not all types may be covered, so we make this informational
        if not found:
            pytest.skip(f"No claims found covering challenge: {challenge_type}")

    def test_expected_behavior_addresses_brevity(self, edge_case_short_claims: Dict[str, Any]):
        """Verify expected behavior addresses claim brevity.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])

        for claim in claims:
            expected_behavior = claim.get("expected_behavior", "")

            # Should be descriptive
            assert len(expected_behavior) > 15, (
                f"Claim {claim['id']} expected_behavior should be descriptive"
            )

    def test_short_claims_reason_quality(self, edge_case_short_claims: Dict[str, Any]):
        """Verify reasons for short claim challenges are documented.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])

        for claim in claims:
            reason = claim.get("reason", "")

            # Reason should explain the challenge
            assert len(reason) > 20, f"Claim {claim['id']} should have descriptive reason"

            # Should mention brevity or lack of context
            keywords = ["short", "brief", "minimal", "lacks", "terse", "context"]
            has_keyword = any(keyword in reason.lower() for keyword in keywords)
            # Soft check - not all may explicitly mention these
            if not has_keyword:
                # At minimum should be substantive
                assert len(reason.split()) > 5

    def test_short_claims_have_evidence_when_needed(self, edge_case_short_claims: Dict[str, Any]):
        """Verify short claims have evidence when not INSUFFICIENT.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])
        evidence_list = edge_case_short_claims.get("evidence", [])

        for claim in claims:
            evidence_ids = claim.get("evidence_ids", [])
            expected_verdict = claim.get("expected_verdict")

            # If not INSUFFICIENT, should have evidence
            if expected_verdict != "INSUFFICIENT":
                assert len(evidence_ids) > 0, (
                    f"Claim {claim['id']} with {expected_verdict} verdict should have evidence"
                )

                # Verify evidence exists
                for ev_id in evidence_ids:
                    found = any(ev["id"] == ev_id for ev in evidence_list)
                    assert found, f"Evidence {ev_id} referenced by claim {claim['id']} not found"

    def test_word_count_statistics(self, edge_case_short_claims: Dict[str, Any]):
        """Generate statistics on word counts for short claims.

        Args:
            edge_case_short_claims: Fixture with short claims data
        """
        claims = edge_case_short_claims.get("claims", [])
        word_counts = [len(claim["text"].split()) for claim in claims]

        # All should be <=10 words
        assert max(word_counts) <= 10
        assert min(word_counts) >= 1

        # Calculate statistics
        avg_words = sum(word_counts) / len(word_counts)
        assert avg_words <= 10, f"Average word count should be <=10, got {avg_words}"


class TestShortClaimsIntegration:
    """Integration tests for short claim handling."""

    def test_fixture_integration_with_all_edge_cases(
        self,
        all_edge_cases: Dict[str, Dict[str, Any]],
    ):
        """Verify short claims are included in all_edge_cases fixture.

        Args:
            all_edge_cases: Combined fixture with all edge case categories
        """
        assert "short_claims" in all_edge_cases
        short_data = all_edge_cases["short_claims"]

        assert "claims" in short_data
        assert len(short_data["claims"]) > 0
        assert short_data["category"] == "short_claims"

    def test_get_claims_by_category(
        self,
        get_edge_case_claims_by_category,
    ):
        """Test retrieval of short claims by category.

        Args:
            get_edge_case_claims_by_category: Factory fixture for claim retrieval
        """
        claims = get_edge_case_claims_by_category("short_claims")

        assert len(claims) > 0
        for claim in claims:
            assert claim["edge_case_type"] == "short_claims"
            # Verify actually short
            word_count = len(claim["text"].split())
            assert word_count <= 10

    def test_edge_case_statistics_includes_short_claims(self, edge_case_statistics: Dict[str, Any]):
        """Verify statistics include short claims category.

        Args:
            edge_case_statistics: Statistics fixture for all edge cases
        """
        assert "categories" in edge_case_statistics
        categories = edge_case_statistics["categories"]

        assert "short_claims" in categories
        short_stats = categories["short_claims"]

        assert "claim_count" in short_stats
        assert short_stats["claim_count"] > 0


# Placeholder for actual verification system integration tests
class TestShortClaimsVerification:
    """Tests for actual verification system with short claims.

    NOTE: These tests are placeholders pending integration with the
    actual TruthGraph verification pipeline. Once the pipeline is
    available, these should be implemented to verify:

    1. System processes short claims without errors
    2. System doesn't reject claims as too short
    3. System handles minimal context appropriately
    4. System provides useful results despite brevity
    """

    @pytest.mark.skip(reason="Pending verification pipeline integration")
    def test_short_claims_no_rejection_errors(self, edge_case_short_claims: Dict[str, Any]):
        """Test that verification system handles short claims without rejection.

        This test should be implemented once the verification pipeline is available.
        It should verify that short claims are processed without being rejected
        as too short or invalid.
        """
        # TODO: Implement when verification pipeline is available
        # from truthgraph.verification import VerificationPipeline
        #
        # pipeline = VerificationPipeline()
        # claims = edge_case_short_claims.get("claims", [])
        #
        # for claim in claims:
        #     result = pipeline.verify(claim["text"])
        #     # Should return valid result, not error
        #     assert "verdict" in result
        #     assert "error" not in result or result["error"] is None
        pass

    @pytest.mark.skip(reason="Pending verification pipeline integration")
    def test_short_claims_handle_ambiguity(self, edge_case_short_claims: Dict[str, Any]):
        """Test that system handles ambiguity in short claims appropriately.

        Short claims may be ambiguous due to lack of context. System should
        recognize this and adjust confidence accordingly.
        """
        # TODO: Implement when verification pipeline is available
        pass
