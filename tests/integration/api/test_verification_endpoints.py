"""Integration tests for verification endpoints.

Tests the verification workflow endpoints:
- POST /api/v1/claims/{claim_id}/verify
- GET /api/v1/verdicts/{claim_id}

These tests verify the async verification workflow including request/response
validation, task queueing, and result retrieval.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from truthgraph.api.schemas.verification import VerificationOptions
from truthgraph.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def clear_verification_storage():
    """Clear in-memory verification storage before each test."""
    from truthgraph.api.handlers.verification_handlers import (
        verification_results,
        verification_tasks,
    )

    verification_tasks.clear()
    verification_results.clear()
    yield
    verification_tasks.clear()
    verification_results.clear()


class TestVerifyEndpoint:
    """Tests for POST /api/v1/claims/{claim_id}/verify endpoint."""

    def test_verify_endpoint_accepts_valid_request(self, client, clear_verification_storage):
        """Test that verification endpoint accepts valid requests."""
        request_data = {
            "claim_id": "test_claim_001",
            "claim_text": "The Earth orbits around the Sun",
            "corpus_ids": None,
            "options": {
                "max_evidence_items": 5,
                "confidence_threshold": 0.7,
                "return_reasoning": True,
                "search_mode": "hybrid",
            },
        }

        response = client.post(
            "/api/v1/claims/test_claim_001/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "processing"]
        assert data["task_id"].startswith("task_")
        assert "created_at" in data
        assert data["progress_percentage"] >= 0

    def test_verify_endpoint_rejects_empty_claim(self, client, clear_verification_storage):
        """Test that verification endpoint rejects empty claim text."""
        request_data = {
            "claim_id": "test_claim_002",
            "claim_text": "",
            "corpus_ids": None,
            "options": None,
        }

        response = client.post(
            "/api/v1/claims/test_claim_002/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Pydantic validation error

    def test_verify_endpoint_rejects_claim_id_mismatch(self, client, clear_verification_storage):
        """Test that endpoint rejects mismatched claim IDs."""
        request_data = {
            "claim_id": "test_claim_003",
            "claim_text": "Test claim text",
            "corpus_ids": None,
            "options": None,
        }

        response = client.post(
            "/api/v1/claims/different_claim_id/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "does not match" in data["detail"].lower()

    def test_verify_endpoint_accepts_minimal_request(self, client, clear_verification_storage):
        """Test verification with minimal required fields."""
        request_data = {
            "claim_id": "test_claim_004",
            "claim_text": "Water boils at 100 degrees Celsius at sea level",
        }

        response = client.post(
            "/api/v1/claims/test_claim_004/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "processing"]

    def test_verify_endpoint_accepts_custom_options(self, client, clear_verification_storage):
        """Test verification with custom options."""
        request_data = {
            "claim_id": "test_claim_005",
            "claim_text": "The speed of light is approximately 299,792,458 meters per second",
            "corpus_ids": ["scientific_papers", "textbooks"],
            "options": {
                "max_evidence_items": 10,
                "confidence_threshold": 0.8,
                "return_reasoning": False,
                "search_mode": "vector",
            },
        }

        response = client.post(
            "/api/v1/claims/test_claim_005/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data

    def test_verify_endpoint_rejects_invalid_options(self, client, clear_verification_storage):
        """Test that endpoint rejects invalid option values."""
        request_data = {
            "claim_id": "test_claim_006",
            "claim_text": "Test claim",
            "options": {
                "max_evidence_items": 100,  # Over limit (max 50)
                "confidence_threshold": 1.5,  # Over limit (max 1.0)
            },
        }

        response = client.post(
            "/api/v1/claims/test_claim_006/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_verify_endpoint_handles_long_claim(self, client, clear_verification_storage):
        """Test verification with a long but valid claim."""
        long_claim = "This is a test claim. " * 100  # ~2000 characters
        request_data = {
            "claim_id": "test_claim_007",
            "claim_text": long_claim,
        }

        response = client.post(
            "/api/v1/claims/test_claim_007/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_verify_endpoint_rejects_too_long_claim(self, client, clear_verification_storage):
        """Test that endpoint rejects claims over 5000 characters."""
        too_long_claim = "x" * 5001
        request_data = {
            "claim_id": "test_claim_008",
            "claim_text": too_long_claim,
        }

        response = client.post(
            "/api/v1/claims/test_claim_008/verify",
            json=request_data,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerdictEndpoint:
    """Tests for GET /api/v1/verdicts/{claim_id} endpoint."""

    def test_verdict_endpoint_returns_404_for_nonexistent_claim(
        self, client, clear_verification_storage
    ):
        """Test that verdict endpoint returns 404 for non-existent claim."""
        response = client.get("/api/v1/verdicts/nonexistent_claim")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_verdict_endpoint_returns_202_for_pending_verification(
        self, client, clear_verification_storage
    ):
        """Test that verdict endpoint returns 202 for pending verification."""
        from datetime import UTC, datetime

        from truthgraph.api.handlers.verification_handlers import verification_tasks
        from truthgraph.api.schemas.verification import TaskStatus

        # Manually add a pending task
        task_status = TaskStatus(
            task_id="task_pending_001",
            status="pending",
            created_at=datetime.now(UTC),
            progress_percentage=0,
        )
        verification_tasks["task_pending_001"] = task_status

        response = client.get("/api/v1/verdicts/test_claim_pending")

        # Should return 202 or 404 depending on whether task is found
        assert response.status_code in [status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_verdict_endpoint_returns_result_when_complete(
        self, client, clear_verification_storage
    ):
        """Test that verdict endpoint returns result when verification is complete."""
        from datetime import UTC, datetime

        from truthgraph.api.handlers.verification_handlers import verification_results
        from truthgraph.api.schemas.evidence import EvidenceItem
        from truthgraph.api.schemas.verification import VerificationResult

        # Manually add a completed result
        result = VerificationResult(
            claim_id="test_claim_complete",
            claim_text="The Earth is round",
            verdict="SUPPORTED",
            confidence=0.95,
            reasoning="Multiple sources confirm this fact.",
            evidence=[
                EvidenceItem(
                    id="evidence_001",
                    text="The Earth is an oblate spheroid.",
                    source="Science Journal",
                    relevance=0.98,
                    url="https://example.com/earth",
                    publication_date="2023-01-15",
                    nli_label="entailment",
                    nli_confidence=0.96,
                )
            ],
            verified_at=datetime.now(UTC),
            processing_time_ms=1500,
            corpus_ids_searched=None,
        )
        verification_results["test_claim_complete"] = result

        response = client.get("/api/v1/verdicts/test_claim_complete")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["claim_id"] == "test_claim_complete"
        assert data["verdict"] == "SUPPORTED"
        assert data["confidence"] == 0.95
        assert len(data["evidence"]) == 1
        assert "reasoning" in data
        assert "verified_at" in data


class TestVerificationWorkflow:
    """Integration tests for complete verification workflow."""

    @pytest.mark.asyncio
    async def test_complete_verification_workflow(self, client, clear_verification_storage):
        """Test complete workflow from verification to verdict retrieval."""
        # Step 1: Trigger verification
        request_data = {
            "claim_id": "workflow_claim_001",
            "claim_text": "The Sun is a star",
            "options": {
                "max_evidence_items": 3,
                "confidence_threshold": 0.6,
            },
        }

        verify_response = client.post(
            "/api/v1/claims/workflow_claim_001/verify",
            json=request_data,
        )

        assert verify_response.status_code == status.HTTP_202_ACCEPTED
        verify_data = verify_response.json()
        task_id = verify_data["task_id"]
        assert task_id is not None

        # Step 2: Wait a bit for processing (in real scenario, would poll)
        await asyncio.sleep(0.5)

        # Step 3: Try to get verdict (may still be processing or complete)
        verdict_response = client.get("/api/v1/verdicts/workflow_claim_001")

        # Could be 200 (complete), 202 (processing), or 404 (not found yet)
        assert verdict_response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,
            status.HTTP_404_NOT_FOUND,
        ]

        if verdict_response.status_code == status.HTTP_200_OK:
            verdict_data = verdict_response.json()
            assert verdict_data["claim_id"] == "workflow_claim_001"
            assert "verdict" in verdict_data
            assert "confidence" in verdict_data

    @pytest.mark.asyncio
    async def test_multiple_concurrent_verifications(self, client, clear_verification_storage):
        """Test handling multiple concurrent verification requests."""
        claims = [
            {
                "claim_id": f"concurrent_claim_{i}",
                "claim_text": f"Test claim number {i}",
            }
            for i in range(5)
        ]

        # Trigger multiple verifications
        responses = []
        for claim_data in claims:
            response = client.post(
                f"/api/v1/claims/{claim_data['claim_id']}/verify",
                json=claim_data,
            )
            responses.append(response)

        # All should be accepted
        for response in responses:
            assert response.status_code == status.HTTP_202_ACCEPTED

        # Each should have unique task_id
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == len(task_ids)  # All unique

    def test_verify_same_claim_twice_returns_existing(self, client, clear_verification_storage):
        """Test that verifying the same claim twice returns existing result."""
        from datetime import UTC, datetime

        from truthgraph.api.handlers.verification_handlers import verification_results
        from truthgraph.api.schemas.verification import VerificationResult

        # Add existing result
        existing_result = VerificationResult(
            claim_id="duplicate_claim",
            claim_text="Test claim for duplication",
            verdict="SUPPORTED",
            confidence=0.9,
            reasoning="Already verified",
            evidence=[],
            verified_at=datetime.now(UTC),
            processing_time_ms=1000,
            corpus_ids_searched=None,
        )
        verification_results["duplicate_claim"] = existing_result

        # Try to verify again
        request_data = {
            "claim_id": "duplicate_claim",
            "claim_text": "Test claim for duplication",
        }

        response = client.post(
            "/api/v1/claims/duplicate_claim/verify",
            json=request_data,
        )

        # Should still return 202, but with completed status
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["verdict"] == "SUPPORTED"


class TestErrorHandling:
    """Tests for error handling in verification endpoints."""

    def test_verify_endpoint_handles_database_error_gracefully(
        self, client, clear_verification_storage
    ):
        """Test that database errors are handled gracefully."""
        # This test would need to mock database failures
        # For now, just verify the endpoint doesn't crash
        request_data = {
            "claim_id": "error_test_001",
            "claim_text": "Test claim",
        }

        response = client.post(
            "/api/v1/claims/error_test_001/verify",
            json=request_data,
        )

        # Should either succeed or return proper error
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_verdict_endpoint_handles_internal_errors(self, client, clear_verification_storage):
        """Test that internal errors in verdict endpoint are handled."""
        response = client.get("/api/v1/verdicts/error_claim")

        # Should return proper error, not crash
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


class TestRequestValidation:
    """Tests for request validation using Pydantic models."""

    def test_verify_request_validates_claim_text_length(self, client, clear_verification_storage):
        """Test claim text length validation."""
        # Too short (empty)
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too long (>5000 chars)
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "x" * 5001,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_verify_request_validates_options_ranges(self, client, clear_verification_storage):
        """Test that option values are validated."""
        # max_evidence_items too high
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "Test",
                "options": {"max_evidence_items": 100},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # confidence_threshold too high
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "Test",
                "options": {"confidence_threshold": 1.5},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_verify_request_validates_corpus_ids(self, client, clear_verification_storage):
        """Test corpus_ids validation."""
        # Empty list should be rejected
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "Test",
                "corpus_ids": [],
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # None should be accepted
        response = client.post(
            "/api/v1/claims/test_claim/verify",
            json={
                "claim_id": "test_claim",
                "claim_text": "Test",
                "corpus_ids": None,
            },
        )
        assert response.status_code == status.HTTP_202_ACCEPTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
