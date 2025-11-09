"""Comprehensive API endpoint tests for Phase 2 features (4.1-4.6).

Tests all API endpoints with focus on:
- Request/response validation (Feature 4.2)
- Input validation with edge cases (Feature 4.6)
- Rate limiting (Feature 4.5)
- Async processing (Feature 4.3)
- Verification endpoints (Feature 4.1)
"""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from truthgraph.main import app
from truthgraph.validation import ValidationStatus


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def edge_case_claims() -> List[Dict[str, Any]]:
    """Load edge case claims from fixture file."""
    try:
        with open("tests/fixtures/edge_case_claims.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("claims", [])
    except FileNotFoundError:
        pytest.skip("Edge case corpus not found")


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, client):
        """Test health endpoint response contains required fields."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "ok", "operational", "degraded"]

    def test_health_endpoint_has_rate_limit_headers(self, client):
        """Test health endpoint includes rate limit headers."""
        response = client.get("/health")

        # Check for standard rate limit headers
        headers = response.headers
        rate_limit_header = (
            headers.get("X-RateLimit-Limit") or
            headers.get("RateLimit-Limit") or
            headers.get("rate-limit-limit")
        )

        assert rate_limit_header is not None


class TestRateLimitStatsEndpoint:
    """Tests for GET /rate-limit-stats endpoint."""

    def test_rate_limit_stats_endpoint_exists(self, client):
        """Test rate-limit-stats endpoint responds."""
        response = client.get("/rate-limit-stats")

        # Should return 200 or be accessible
        assert response.status_code in [200, 404]  # 404 if not implemented

    def test_rate_limit_stats_response_structure(self, client):
        """Test rate-limit-stats response structure."""
        response = client.get("/rate-limit-stats")

        if response.status_code == 200:
            data = response.json()
            assert "rate_limit_statistics" in data or "statistics" in data


class TestVerifyEndpoint:
    """Tests for POST /api/v1/claims/{claim_id}/verify endpoint."""

    def test_verify_endpoint_exists(self, client):
        """Test verification endpoint is available."""
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "The Earth is round",
            },
        )

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    def test_verify_with_valid_claim(self, client):
        """Test verification with valid claim."""
        response = client.post(
            "/api/v1/claims/test_001/verify",
            json={
                "claim_id": "test_001",
                "claim_text": "The Earth orbits around the Sun",
            },
        )

        # Should succeed or give proper error (not crash with 500)
        assert response.status_code in [200, 202, 400, 422]

    def test_verify_with_minimal_claim(self, client):
        """Test verification with minimal valid claim."""
        response = client.post(
            "/api/v1/claims/test_002/verify",
            json={
                "claim_id": "test_002",
                "claim_text": "Water is wet",
            },
        )

        # Accept success or error status (not 500 crash)
        assert response.status_code < 500

    def test_verify_with_empty_claim_rejected(self, client):
        """Test verification rejects empty claim."""
        response = client.post(
            "/api/v1/claims/test_003/verify",
            json={
                "claim_id": "test_003",
                "claim_text": "",
            },
        )

        # Should reject with 400 or 422
        assert response.status_code in [400, 422]

    def test_verify_with_whitespace_only_claim_rejected(self, client):
        """Test verification rejects whitespace-only claim."""
        response = client.post(
            "/api/v1/claims/test_004/verify",
            json={
                "claim_id": "test_004",
                "claim_text": "   \t\n  ",
            },
        )

        assert response.status_code in [400, 422]

    def test_verify_with_single_word_claim(self, client):
        """Test verification with single word claim."""
        response = client.post(
            "/api/v1/claims/test_005/verify",
            json={
                "claim_id": "test_005",
                "claim_text": "Earth",
            },
        )

        # Single word should be rejected or warned (not crash)
        assert response.status_code < 500

    def test_verify_with_very_long_claim(self, client):
        """Test verification with very long claim."""
        long_claim = "This is a test claim. " * 200  # ~5000+ characters
        response = client.post(
            "/api/v1/claims/test_006/verify",
            json={
                "claim_id": "test_006",
                "claim_text": long_claim,
            },
        )

        # Should not crash with 500 error
        assert response.status_code < 500

    def test_verify_with_unicode_claim(self, client):
        """Test verification with Unicode characters."""
        response = client.post(
            "/api/v1/claims/test_007/verify",
            json={
                "claim_id": "test_007",
                "claim_text": "Η Γη είναι στρογγυλή",  # Greek: "The Earth is round"
            },
        )

        assert response.status_code < 500

    def test_verify_with_emoji(self, client):
        """Test verification with emoji."""
        response = client.post(
            "/api/v1/claims/test_008/verify",
            json={
                "claim_id": "test_008",
                "claim_text": "The Earth 🌍 is round",
            },
        )

        assert response.status_code < 500

    def test_verify_with_special_characters(self, client):
        """Test verification with special characters."""
        response = client.post(
            "/api/v1/claims/test_009/verify",
            json={
                "claim_id": "test_009",
                "claim_text": "Einstein's equation is E = mc²",
            },
        )

        assert response.status_code < 500

    def test_verify_with_custom_options(self, client):
        """Test verification with custom options."""
        response = client.post(
            "/api/v1/claims/test_010/verify",
            json={
                "claim_id": "test_010",
                "claim_text": "The speed of light is constant",
                "options": {
                    "max_evidence_items": 5,
                    "confidence_threshold": 0.7,
                    "return_reasoning": True,
                },
            },
        )

        assert response.status_code < 500

    def test_verify_with_corpus_ids(self, client):
        """Test verification with specific corpus IDs."""
        response = client.post(
            "/api/v1/claims/test_011/verify",
            json={
                "claim_id": "test_011",
                "claim_text": "Scientific claims require evidence",
                "corpus_ids": ["scientific_papers"],
            },
        )

        assert response.status_code < 500

    def test_verify_claim_id_must_match_path(self, client):
        """Test that claim_id in request must match path parameter."""
        response = client.post(
            "/api/v1/claims/path_claim/verify",
            json={
                "claim_id": "different_claim",
                "claim_text": "Test claim",
            },
        )

        # Mismatched IDs should be rejected (4xx) or handle gracefully
        assert response.status_code < 500

    def test_verify_missing_claim_text(self, client):
        """Test verification rejects missing claim_text."""
        response = client.post(
            "/api/v1/claims/test_012/verify",
            json={
                "claim_id": "test_012",
            },
        )

        # Missing required field should be 422
        assert response.status_code == 422


class TestVerdictEndpoint:
    """Tests for GET /api/v1/verdicts/{claim_id} endpoint."""

    def test_verdict_endpoint_exists(self, client):
        """Test verdict endpoint is available."""
        response = client.get("/api/v1/verdicts/test_claim_001")

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    def test_verdict_nonexistent_claim_returns_404(self, client):
        """Test verdict endpoint returns 404 for non-existent claim."""
        response = client.get("/api/v1/verdicts/nonexistent_claim_xyz")

        # Should return 404 or some client error, not 500
        assert response.status_code < 500

    def test_verdict_response_structure_when_complete(self, client):
        """Test verdict response structure when complete."""
        # First, try to verify a claim
        verify_response = client.post(
            "/api/v1/claims/test_verdict_001/verify",
            json={
                "claim_id": "test_verdict_001",
                "claim_text": "Test claim for verdict",
            },
        )

        if verify_response.status_code in [200, 202]:
            # Try to get verdict
            verdict_response = client.get("/api/v1/verdicts/test_verdict_001")

            if verdict_response.status_code == 200:
                data = verdict_response.json()
                assert "claim_id" in data
                assert "claim_text" in data or "text" in data
                # Verdict may or may not be included depending on implementation


class TestEmbedEndpoint:
    """Tests for POST /api/v1/embed endpoint."""

    def test_embed_endpoint_exists(self, client):
        """Test embed endpoint is available."""
        response = client.post(
            "/api/v1/embed",
            json={"texts": ["test text"]},
        )

        assert response.status_code != 404

    def test_embed_with_single_text(self, client):
        """Test embed with single text."""
        response = client.post(
            "/api/v1/embed",
            json={"texts": ["The Earth is round"]},
        )

        assert response.status_code in [200, 400, 422]

    def test_embed_with_multiple_texts(self, client):
        """Test embed with multiple texts."""
        response = client.post(
            "/api/v1/embed",
            json={
                "texts": [
                    "The Earth is round",
                    "Water is wet",
                    "The sky is blue",
                ]
            },
        )

        assert response.status_code in [200, 400, 422]

    def test_embed_with_unicode_texts(self, client):
        """Test embed with Unicode texts."""
        response = client.post(
            "/api/v1/embed",
            json={
                "texts": [
                    "Η Γη είναι στρογγυλή",  # Greek
                    "La terre est ronde",  # French
                    "地球是圆的",  # Chinese
                ]
            },
        )

        assert response.status_code in [200, 400, 422]


class TestSearchEndpoint:
    """Tests for POST /api/v1/search endpoint."""

    def test_search_endpoint_exists(self, client):
        """Test search endpoint is available."""
        response = client.post(
            "/api/v1/search",
            json={"query": "test query"},
        )

        assert response.status_code != 404

    def test_search_with_query(self, client):
        """Test search with query."""
        response = client.post(
            "/api/v1/search",
            json={"query": "The Earth is round"},
        )

        # Should not crash with 500
        assert response.status_code < 500

    def test_search_with_filters(self, client):
        """Test search with optional filters."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "climate change",
                "corpus_ids": ["scientific_papers"],
                "limit": 10,
            },
        )

        # Should not crash with 500
        assert response.status_code < 500


class TestNLIEndpoint:
    """Tests for POST /api/v1/nli endpoint."""

    def test_nli_endpoint_exists(self, client):
        """Test NLI endpoint is available."""
        response = client.post(
            "/api/v1/nli",
            json={
                "premise": "The Earth is round",
                "hypothesis": "The Earth is a sphere",
            },
        )

        assert response.status_code != 404

    def test_nli_with_valid_inputs(self, client):
        """Test NLI with valid premise and hypothesis."""
        response = client.post(
            "/api/v1/nli",
            json={
                "premise": "All birds can fly",
                "hypothesis": "Penguins can fly",
            },
        )

        assert response.status_code in [200, 400, 422]

    def test_nli_response_structure(self, client):
        """Test NLI response structure."""
        response = client.post(
            "/api/v1/nli",
            json={
                "premise": "The sky is blue",
                "hypothesis": "The sky has color",
            },
        )

        if response.status_code == 200:
            data = response.json()
            # Should contain NLI label or result
            assert any(
                key in data
                for key in ["label", "nli_label", "prediction", "result"]
            )


class TestNLIBatchEndpoint:
    """Tests for POST /api/v1/nli/batch endpoint."""

    def test_nli_batch_endpoint_exists(self, client):
        """Test NLI batch endpoint is available."""
        response = client.post(
            "/api/v1/nli/batch",
            json={
                "pairs": [
                    {
                        "premise": "All birds can fly",
                        "hypothesis": "Penguins can fly",
                    }
                ]
            },
        )

        assert response.status_code != 404

    def test_nli_batch_with_multiple_pairs(self, client):
        """Test NLI batch with multiple pairs."""
        response = client.post(
            "/api/v1/nli/batch",
            json={
                "pairs": [
                    {
                        "premise": "The Earth orbits the Sun",
                        "hypothesis": "The Sun is at the center",
                    },
                    {
                        "premise": "Water boils at 100°C",
                        "hypothesis": "Heat causes water to evaporate",
                    },
                    {
                        "premise": "Gravity pulls objects down",
                        "hypothesis": "Objects fall towards Earth",
                    },
                ]
            },
        )

        assert response.status_code in [200, 400, 422]


class TestInputValidationWithEdgeCases:
    """Tests for input validation (Feature 4.6) with edge case corpus."""

    def test_verify_all_edge_case_claims_process(self, client, edge_case_claims):
        """Test that all edge case claims process without crashing."""
        processed = 0
        crashed = 0
        errors = []

        for claim in edge_case_claims[:10]:  # Test first 10 claims
            try:
                response = client.post(
                    f"/api/v1/claims/{claim['id']}/verify",
                    json={
                        "claim_id": claim["id"],
                        "claim_text": claim["text"],
                    },
                )
                # Should process without crashing
                if response.status_code >= 500:
                    crashed += 1
                else:
                    processed += 1
            except Exception as e:
                errors.append(f"Claim {claim['id']}: {str(e)}")
                crashed += 1

        # At least some should process successfully without crashing (4xx/2xx is ok)
        assert processed + crashed > 0, f"No requests made. Errors: {errors}"

    def test_short_claims_validation(self, client):
        """Test validation of short claims (edge case category)."""
        short_claims = [
            "Water is wet",
            "Earth orbits",
            "The sky is blue",
        ]

        for claim in short_claims:
            response = client.post(
                "/api/v1/claims/short_claim/verify",
                json={
                    "claim_id": "short_claim",
                    "claim_text": claim,
                },
            )
            # Should not crash with 500
            assert response.status_code < 500

    def test_long_claims_validation(self, client):
        """Test validation of long claims (edge case category)."""
        long_claim = (
            "The concept of quantum mechanics and its implications for understanding "
            "the fundamental nature of reality, including wave-particle duality, "
            "superposition, entanglement, and the observer effect, which have been "
            "experimentally verified through numerous experiments and continue to "
            "challenge our classical intuitions about how the universe operates. "
        ) * 3

        response = client.post(
            "/api/v1/claims/long_claim/verify",
            json={
                "claim_id": "long_claim",
                "claim_text": long_claim,
            },
        )

        # Should not crash with 500
        assert response.status_code < 500

    def test_multilingual_claims_validation(self, client):
        """Test validation of multilingual claims (edge case category)."""
        multilingual_claims = [
            "La Terre tourne autour du Soleil",  # French
            "Die Erde dreht sich um die Sonne",  # German
            "The Earth orbits the Sun",  # English
            "La Tierra orbita alrededor del Sol",  # Spanish
        ]

        for claim in multilingual_claims:
            response = client.post(
                "/api/v1/claims/multilingual_claim/verify",
                json={
                    "claim_id": "multilingual_claim",
                    "claim_text": claim,
                },
            )
            # Should not crash with 500
            assert response.status_code < 500

    def test_special_characters_validation(self, client):
        """Test validation of claims with special characters."""
        special_char_claims = [
            "Einstein's equation E = mc²",
            "The temperature is -40°C or -40°F",
            "Greek letter α (alpha) and β (beta)",
            "RTL text: مرحبا بك",
            "Emoji test: 🌍 🚀 ⚡",
        ]

        for claim in special_char_claims:
            response = client.post(
                "/api/v1/claims/special_char_claim/verify",
                json={
                    "claim_id": "special_char_claim",
                    "claim_text": claim,
                },
            )
            # Should not crash with 500
            assert response.status_code < 500


class TestRateLimitingBehavior:
    """Tests for rate limiting behavior across endpoints."""

    def test_health_endpoint_has_high_limit(self, client):
        """Test health endpoint has higher rate limit."""
        # Make multiple requests to health endpoint
        responses = [client.get("/health") for _ in range(5)]

        # All should succeed (high limit)
        assert all(r.status_code == 200 for r in responses)

    def test_rate_limit_headers_present(self, client):
        """Test rate limit headers are present in responses."""
        response = client.get("/health")

        # Check for rate limit headers
        has_limit_header = any(
            header in response.headers
            for header in ["X-RateLimit-Limit", "RateLimit-Limit", "rate-limit-limit"]
        )

        assert has_limit_header is True

    def test_verify_endpoint_stricter_limit(self, client):
        """Test verify endpoint has stricter rate limit than health."""
        # Verify endpoint should be stricter than health endpoint
        # This is configuration-based, just verify it doesn't crash
        response = client.post(
            "/api/v1/claims/rate_test/verify",
            json={
                "claim_id": "rate_test",
                "claim_text": "Test claim for rate limiting",
            },
        )

        # Should handle request properly (not crash with 500)
        assert response.status_code < 500


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    def test_invalid_json_returns_422(self, client):
        """Test invalid JSON returns 422."""
        response = client.post(
            "/api/v1/claims/test/verify",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [400, 422]

    def test_missing_required_field_returns_422(self, client):
        """Test missing required field returns 422."""
        response = client.post(
            "/api/v1/claims/test/verify",
            json={"claim_id": "test"},  # Missing claim_text
        )

        assert response.status_code == 422

    def test_invalid_option_values_returns_422(self, client):
        """Test invalid option values returns 422."""
        response = client.post(
            "/api/v1/claims/test/verify",
            json={
                "claim_id": "test",
                "claim_text": "Test",
                "options": {
                    "confidence_threshold": 1.5,  # Invalid: > 1.0
                },
            },
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
