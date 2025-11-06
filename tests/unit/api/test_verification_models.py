"""Comprehensive unit tests for verification API models.

Tests cover:
- Valid model creation
- Validation failures
- Field constraints
- Serialization/deserialization
- Edge cases
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from truthgraph.api.schemas.evidence import EvidenceItem
from truthgraph.api.schemas.verification import (
    TaskStatus,
    VerificationOptions,
    VerificationResult,
    VerifyClaimRequest,
)


# ===== EvidenceItem Tests =====


class TestEvidenceItem:
    """Tests for EvidenceItem model."""

    def test_valid_evidence_item_minimal(self):
        """Test creating evidence item with minimal required fields."""
        evidence = EvidenceItem(
            id="evidence_123",
            text="This is evidence text.",
            source="Test Source",
            relevance=0.85,
        )
        assert evidence.id == "evidence_123"
        assert evidence.text == "This is evidence text."
        assert evidence.source == "Test Source"
        assert evidence.relevance == 0.85
        assert evidence.url is None
        assert evidence.publication_date is None
        assert evidence.nli_label is None
        assert evidence.nli_confidence is None

    def test_valid_evidence_item_full(self):
        """Test creating evidence item with all fields."""
        evidence = EvidenceItem(
            id="evidence_456",
            text="Complete evidence with all fields.",
            source="Scientific Journal",
            relevance=0.92,
            url="https://example.com/article",
            publication_date="2023-05-15",
            nli_label="entailment",
            nli_confidence=0.89,
        )
        assert evidence.id == "evidence_456"
        assert evidence.relevance == 0.92
        assert evidence.url == "https://example.com/article"
        assert evidence.publication_date == "2023-05-15"
        assert evidence.nli_label == "entailment"
        assert evidence.nli_confidence == 0.89

    def test_evidence_text_empty_fails(self):
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(id="test", text="", source="source", relevance=0.5)
        errors = exc_info.value.errors()
        assert any("text" in str(error["loc"]) for error in errors)

    def test_evidence_text_too_long_fails(self):
        """Test that text exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test", text="x" * 10001, source="source", relevance=0.5
            )
        errors = exc_info.value.errors()
        assert any("text" in str(error["loc"]) for error in errors)

    def test_relevance_out_of_range_fails(self):
        """Test that relevance scores outside [0, 1] are rejected."""
        # Test negative relevance
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test", text="text", source="source", relevance=-0.1
            )
        errors = exc_info.value.errors()
        assert any("relevance" in str(error["loc"]) for error in errors)

        # Test relevance > 1
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test", text="text", source="source", relevance=1.5
            )
        errors = exc_info.value.errors()
        assert any("relevance" in str(error["loc"]) for error in errors)

    def test_relevance_boundaries_valid(self):
        """Test that relevance scores at boundaries (0 and 1) are valid."""
        evidence_min = EvidenceItem(
            id="test1", text="text", source="source", relevance=0.0
        )
        assert evidence_min.relevance == 0.0

        evidence_max = EvidenceItem(
            id="test2", text="text", source="source", relevance=1.0
        )
        assert evidence_max.relevance == 1.0

    def test_url_validation_valid_urls(self):
        """Test that valid URLs are accepted."""
        # HTTP URL
        evidence_http = EvidenceItem(
            id="test1",
            text="text",
            source="source",
            relevance=0.5,
            url="http://example.com",
        )
        assert evidence_http.url == "http://example.com"

        # HTTPS URL
        evidence_https = EvidenceItem(
            id="test2",
            text="text",
            source="source",
            relevance=0.5,
            url="https://example.com/path?query=1",
        )
        assert evidence_https.url == "https://example.com/path?query=1"

    def test_url_validation_invalid_url_fails(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test",
                text="text",
                source="source",
                relevance=0.5,
                url="not-a-url",
            )
        errors = exc_info.value.errors()
        assert any("url" in str(error["loc"]) for error in errors)

    def test_url_strips_whitespace(self):
        """Test that URL whitespace is handled."""
        evidence = EvidenceItem(
            id="test",
            text="text",
            source="source",
            relevance=0.5,
            url="  https://example.com  ",
        )
        assert evidence.url == "https://example.com"

    def test_publication_date_valid_formats(self):
        """Test various valid ISO date formats."""
        # Basic date
        evidence1 = EvidenceItem(
            id="test1",
            text="text",
            source="source",
            relevance=0.5,
            publication_date="2023-05-15",
        )
        assert evidence1.publication_date == "2023-05-15"

        # Date with time
        evidence2 = EvidenceItem(
            id="test2",
            text="text",
            source="source",
            relevance=0.5,
            publication_date="2023-05-15T10:30:00",
        )
        assert evidence2.publication_date == "2023-05-15T10:30:00"

        # Date with timezone
        evidence3 = EvidenceItem(
            id="test3",
            text="text",
            source="source",
            relevance=0.5,
            publication_date="2023-05-15T10:30:00Z",
        )
        assert evidence3.publication_date == "2023-05-15T10:30:00Z"

    def test_publication_date_invalid_format_fails(self):
        """Test that invalid date formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test",
                text="text",
                source="source",
                relevance=0.5,
                publication_date="not-a-date",
            )
        errors = exc_info.value.errors()
        assert any("publication_date" in str(error["loc"]) for error in errors)

    def test_nli_label_valid_values(self):
        """Test that valid NLI labels are accepted."""
        for label in ["entailment", "contradiction", "neutral"]:
            evidence = EvidenceItem(
                id=f"test_{label}",
                text="text",
                source="source",
                relevance=0.5,
                nli_label=label,
            )
            assert evidence.nli_label == label

    def test_nli_label_case_insensitive(self):
        """Test that NLI labels are case-insensitive."""
        evidence = EvidenceItem(
            id="test",
            text="text",
            source="source",
            relevance=0.5,
            nli_label="ENTAILMENT",
        )
        assert evidence.nli_label == "entailment"

    def test_nli_label_invalid_fails(self):
        """Test that invalid NLI labels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test",
                text="text",
                source="source",
                relevance=0.5,
                nli_label="invalid_label",
            )
        errors = exc_info.value.errors()
        assert any("nli_label" in str(error["loc"]) for error in errors)

    def test_nli_confidence_out_of_range_fails(self):
        """Test that NLI confidence outside [0, 1] is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="test",
                text="text",
                source="source",
                relevance=0.5,
                nli_confidence=1.5,
            )
        errors = exc_info.value.errors()
        assert any("nli_confidence" in str(error["loc"]) for error in errors)

    def test_serialization_deserialization(self):
        """Test that evidence can be serialized and deserialized."""
        original = EvidenceItem(
            id="evidence_789",
            text="Evidence text for serialization.",
            source="Test Source",
            relevance=0.88,
            url="https://example.com",
            publication_date="2023-06-01",
            nli_label="entailment",
            nli_confidence=0.92,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["id"] == "evidence_789"
        assert data["relevance"] == 0.88

        # Deserialize from dict
        reconstructed = EvidenceItem(**data)
        assert reconstructed.id == original.id
        assert reconstructed.text == original.text
        assert reconstructed.relevance == original.relevance
        assert reconstructed.nli_label == original.nli_label

        # Serialize to JSON
        json_str = original.model_dump_json()
        assert "evidence_789" in json_str

        # Deserialize from JSON
        reconstructed_json = EvidenceItem.model_validate_json(json_str)
        assert reconstructed_json.id == original.id


# ===== VerificationOptions Tests =====


class TestVerificationOptions:
    """Tests for VerificationOptions model."""

    def test_default_options(self):
        """Test that default options are set correctly."""
        options = VerificationOptions()
        assert options.max_evidence_items == 10
        assert options.confidence_threshold == 0.5
        assert options.return_reasoning is True
        assert options.search_mode == "hybrid"

    def test_custom_options(self):
        """Test setting custom options."""
        options = VerificationOptions(
            max_evidence_items=5,
            confidence_threshold=0.8,
            return_reasoning=False,
            search_mode="vector",
        )
        assert options.max_evidence_items == 5
        assert options.confidence_threshold == 0.8
        assert options.return_reasoning is False
        assert options.search_mode == "vector"

    def test_max_evidence_items_boundaries(self):
        """Test max_evidence_items at boundaries."""
        # Minimum valid
        options_min = VerificationOptions(max_evidence_items=1)
        assert options_min.max_evidence_items == 1

        # Maximum valid
        options_max = VerificationOptions(max_evidence_items=50)
        assert options_max.max_evidence_items == 50

    def test_max_evidence_items_out_of_range_fails(self):
        """Test that max_evidence_items outside [1, 50] fails."""
        # Less than 1
        with pytest.raises(ValidationError) as exc_info:
            VerificationOptions(max_evidence_items=0)
        errors = exc_info.value.errors()
        assert any("max_evidence_items" in str(error["loc"]) for error in errors)

        # Greater than 50
        with pytest.raises(ValidationError) as exc_info:
            VerificationOptions(max_evidence_items=51)
        errors = exc_info.value.errors()
        assert any("max_evidence_items" in str(error["loc"]) for error in errors)

    def test_confidence_threshold_boundaries(self):
        """Test confidence_threshold at boundaries."""
        # Minimum
        options_min = VerificationOptions(confidence_threshold=0.0)
        assert options_min.confidence_threshold == 0.0

        # Maximum
        options_max = VerificationOptions(confidence_threshold=1.0)
        assert options_max.confidence_threshold == 1.0

    def test_confidence_threshold_out_of_range_fails(self):
        """Test that confidence_threshold outside [0, 1] fails."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationOptions(confidence_threshold=-0.1)
        errors = exc_info.value.errors()
        assert any("confidence_threshold" in str(error["loc"]) for error in errors)

        with pytest.raises(ValidationError) as exc_info:
            VerificationOptions(confidence_threshold=1.1)
        errors = exc_info.value.errors()
        assert any("confidence_threshold" in str(error["loc"]) for error in errors)

    def test_search_mode_valid_values(self):
        """Test all valid search modes."""
        for mode in ["hybrid", "vector", "keyword"]:
            options = VerificationOptions(search_mode=mode)
            assert options.search_mode == mode

    def test_search_mode_invalid_fails(self):
        """Test that invalid search mode fails."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationOptions(search_mode="invalid_mode")
        errors = exc_info.value.errors()
        assert any("search_mode" in str(error["loc"]) for error in errors)


# ===== VerifyClaimRequest Tests =====


class TestVerifyClaimRequest:
    """Tests for VerifyClaimRequest model."""

    def test_valid_request_minimal(self):
        """Test creating request with minimal fields."""
        request = VerifyClaimRequest(
            claim_id="claim_123", claim_text="The Earth is round"
        )
        assert request.claim_id == "claim_123"
        assert request.claim_text == "The Earth is round"
        assert request.corpus_ids is None
        assert request.options is None

    def test_valid_request_full(self):
        """Test creating request with all fields."""
        options = VerificationOptions(max_evidence_items=5)
        request = VerifyClaimRequest(
            claim_id="claim_456",
            claim_text="Water boils at 100°C",
            corpus_ids=["wikipedia", "textbooks"],
            options=options,
        )
        assert request.claim_id == "claim_456"
        assert request.claim_text == "Water boils at 100°C"
        assert request.corpus_ids == ["wikipedia", "textbooks"]
        assert request.options.max_evidence_items == 5

    def test_claim_text_strips_whitespace(self):
        """Test that claim text whitespace is stripped."""
        request = VerifyClaimRequest(
            claim_id="test", claim_text="  The Earth is round  "
        )
        assert request.claim_text == "The Earth is round"

    def test_claim_text_empty_fails(self):
        """Test that empty claim text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerifyClaimRequest(claim_id="test", claim_text="")
        errors = exc_info.value.errors()
        assert any("claim_text" in str(error["loc"]) for error in errors)

    def test_claim_text_whitespace_only_fails(self):
        """Test that whitespace-only claim text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerifyClaimRequest(claim_id="test", claim_text="   ")
        errors = exc_info.value.errors()
        assert any("claim_text" in str(error["loc"]) for error in errors)

    def test_claim_text_too_long_fails(self):
        """Test that claim text exceeding 5000 characters is rejected."""
        long_text = "x" * 5001
        with pytest.raises(ValidationError) as exc_info:
            VerifyClaimRequest(claim_id="test", claim_text=long_text)
        errors = exc_info.value.errors()
        assert any("claim_text" in str(error["loc"]) for error in errors)
        assert any("5000" in str(error["msg"]) for error in errors)

    def test_claim_text_at_max_length_valid(self):
        """Test that claim text at exactly 5000 characters is valid."""
        max_text = "x" * 5000
        request = VerifyClaimRequest(claim_id="test", claim_text=max_text)
        assert len(request.claim_text) == 5000

    def test_corpus_ids_valid_list(self):
        """Test that valid corpus_ids list is accepted."""
        request = VerifyClaimRequest(
            claim_id="test",
            claim_text="test claim",
            corpus_ids=["wiki", "papers", "books"],
        )
        assert request.corpus_ids == ["wiki", "papers", "books"]

    def test_corpus_ids_empty_list_fails(self):
        """Test that empty corpus_ids list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerifyClaimRequest(
                claim_id="test", claim_text="test claim", corpus_ids=[]
            )
        errors = exc_info.value.errors()
        assert any("corpus_ids" in str(error["loc"]) for error in errors)

    def test_corpus_ids_empty_string_fails(self):
        """Test that corpus_ids with empty string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerifyClaimRequest(
                claim_id="test", claim_text="test claim", corpus_ids=["wiki", ""]
            )
        errors = exc_info.value.errors()
        assert any("corpus_ids" in str(error["loc"]) for error in errors)

    def test_corpus_ids_none_valid(self):
        """Test that corpus_ids can be None."""
        request = VerifyClaimRequest(
            claim_id="test", claim_text="test claim", corpus_ids=None
        )
        assert request.corpus_ids is None

    def test_serialization_deserialization(self):
        """Test request serialization and deserialization."""
        original = VerifyClaimRequest(
            claim_id="claim_999",
            claim_text="Test claim for serialization",
            corpus_ids=["corpus1", "corpus2"],
            options=VerificationOptions(max_evidence_items=15),
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["claim_id"] == "claim_999"
        assert data["options"]["max_evidence_items"] == 15

        # Deserialize from dict
        reconstructed = VerifyClaimRequest(**data)
        assert reconstructed.claim_id == original.claim_id
        assert reconstructed.claim_text == original.claim_text
        assert reconstructed.corpus_ids == original.corpus_ids


# ===== VerificationResult Tests =====


class TestVerificationResult:
    """Tests for VerificationResult model."""

    def test_valid_result_minimal(self):
        """Test creating result with minimal fields."""
        result = VerificationResult(
            claim_id="claim_123",
            claim_text="Test claim",
            verdict="SUPPORTED",
            confidence=0.85,
            evidence=[],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=1000,
        )
        assert result.claim_id == "claim_123"
        assert result.verdict == "SUPPORTED"
        assert result.confidence == 0.85
        assert result.evidence == []
        assert result.reasoning is None

    def test_valid_result_with_evidence(self):
        """Test creating result with evidence items."""
        evidence_item = EvidenceItem(
            id="ev1", text="Evidence text", source="Source", relevance=0.9
        )
        result = VerificationResult(
            claim_id="claim_456",
            claim_text="Test claim with evidence",
            verdict="REFUTED",
            confidence=0.78,
            evidence=[evidence_item],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=1500,
            reasoning="The evidence contradicts the claim.",
        )
        assert len(result.evidence) == 1
        assert result.evidence[0].id == "ev1"
        assert result.reasoning == "The evidence contradicts the claim."

    def test_all_verdicts_valid(self):
        """Test all valid verdict values."""
        for verdict in ["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO"]:
            result = VerificationResult(
                claim_id="test",
                claim_text="test",
                verdict=verdict,
                confidence=0.5,
                evidence=[],
                verified_at=datetime.now(timezone.utc),
                processing_time_ms=100,
            )
            assert result.verdict == verdict

    def test_invalid_verdict_fails(self):
        """Test that invalid verdict is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationResult(
                claim_id="test",
                claim_text="test",
                verdict="INVALID_VERDICT",
                confidence=0.5,
                evidence=[],
                verified_at=datetime.now(timezone.utc),
                processing_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert any("verdict" in str(error["loc"]) for error in errors)

    def test_confidence_boundaries(self):
        """Test confidence at boundaries."""
        # Minimum
        result_min = VerificationResult(
            claim_id="test",
            claim_text="test",
            verdict="SUPPORTED",
            confidence=0.0,
            evidence=[],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=100,
        )
        assert result_min.confidence == 0.0

        # Maximum
        result_max = VerificationResult(
            claim_id="test",
            claim_text="test",
            verdict="SUPPORTED",
            confidence=1.0,
            evidence=[],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=100,
        )
        assert result_max.confidence == 1.0

    def test_confidence_out_of_range_fails(self):
        """Test that confidence outside [0, 1] fails."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationResult(
                claim_id="test",
                claim_text="test",
                verdict="SUPPORTED",
                confidence=1.5,
                evidence=[],
                verified_at=datetime.now(timezone.utc),
                processing_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert any("confidence" in str(error["loc"]) for error in errors)

    def test_processing_time_negative_fails(self):
        """Test that negative processing time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationResult(
                claim_id="test",
                claim_text="test",
                verdict="SUPPORTED",
                confidence=0.5,
                evidence=[],
                verified_at=datetime.now(timezone.utc),
                processing_time_ms=-100,
            )
        errors = exc_info.value.errors()
        assert any("processing_time_ms" in str(error["loc"]) for error in errors)

    def test_evidence_none_fails(self):
        """Test that None evidence list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VerificationResult(
                claim_id="test",
                claim_text="test",
                verdict="SUPPORTED",
                confidence=0.5,
                evidence=None,
                verified_at=datetime.now(timezone.utc),
                processing_time_ms=100,
            )
        errors = exc_info.value.errors()
        # The error will be caught either by validation or type checking
        assert len(errors) > 0


# ===== TaskStatus Tests =====


class TestTaskStatus:
    """Tests for TaskStatus model."""

    def test_pending_status(self):
        """Test creating pending task status."""
        status = TaskStatus(
            task_id="task_123",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        assert status.task_id == "task_123"
        assert status.status == "pending"
        assert status.completed_at is None
        assert status.result is None
        assert status.error is None

    def test_processing_status_with_progress(self):
        """Test processing status with progress percentage."""
        status = TaskStatus(
            task_id="task_456",
            status="processing",
            created_at=datetime.now(timezone.utc),
            progress_percentage=45,
        )
        assert status.status == "processing"
        assert status.progress_percentage == 45

    def test_completed_status_with_result(self):
        """Test completed status with verification result."""
        result = VerificationResult(
            claim_id="claim_789",
            claim_text="Test claim",
            verdict="SUPPORTED",
            confidence=0.9,
            evidence=[],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=2000,
        )
        status = TaskStatus(
            task_id="task_789",
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            result=result,
        )
        assert status.status == "completed"
        assert status.result is not None
        assert status.result.claim_id == "claim_789"
        assert status.completed_at is not None

    def test_failed_status_with_error(self):
        """Test failed status with error message."""
        status = TaskStatus(
            task_id="task_fail",
            status="failed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            error="Database connection timeout",
        )
        assert status.status == "failed"
        assert status.error == "Database connection timeout"
        assert status.result is None

    def test_all_status_values_valid(self):
        """Test all valid status values."""
        for status_value in ["pending", "processing", "completed", "failed"]:
            status = TaskStatus(
                task_id=f"task_{status_value}",
                status=status_value,
                created_at=datetime.now(timezone.utc),
            )
            assert status.status == status_value

    def test_invalid_status_fails(self):
        """Test that invalid status value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaskStatus(
                task_id="test",
                status="invalid_status",
                created_at=datetime.now(timezone.utc),
            )
        errors = exc_info.value.errors()
        assert any("status" in str(error["loc"]) for error in errors)

    def test_result_without_completed_status_fails(self):
        """Test that result can only be provided when status is completed."""
        result = VerificationResult(
            claim_id="claim",
            claim_text="test",
            verdict="SUPPORTED",
            confidence=0.9,
            evidence=[],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=1000,
        )
        with pytest.raises(ValidationError) as exc_info:
            TaskStatus(
                task_id="test",
                status="processing",
                created_at=datetime.now(timezone.utc),
                result=result,
            )
        errors = exc_info.value.errors()
        assert any("result" in str(error["loc"]) for error in errors)

    def test_error_without_failed_status_fails(self):
        """Test that error can only be provided when status is failed."""
        with pytest.raises(ValidationError) as exc_info:
            TaskStatus(
                task_id="test",
                status="processing",
                created_at=datetime.now(timezone.utc),
                error="Some error",
            )
        errors = exc_info.value.errors()
        assert any("error" in str(error["loc"]) for error in errors)

    def test_completed_at_with_wrong_status_fails(self):
        """Test that completed_at can only be set for completed/failed status."""
        with pytest.raises(ValidationError) as exc_info:
            TaskStatus(
                task_id="test",
                status="processing",
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        errors = exc_info.value.errors()
        assert any("completed_at" in str(error["loc"]) for error in errors)

    def test_progress_percentage_boundaries(self):
        """Test progress percentage at boundaries."""
        # Minimum
        status_min = TaskStatus(
            task_id="test1",
            status="processing",
            created_at=datetime.now(timezone.utc),
            progress_percentage=0,
        )
        assert status_min.progress_percentage == 0

        # Maximum
        status_max = TaskStatus(
            task_id="test2",
            status="processing",
            created_at=datetime.now(timezone.utc),
            progress_percentage=100,
        )
        assert status_max.progress_percentage == 100

    def test_progress_percentage_out_of_range_fails(self):
        """Test that progress percentage outside [0, 100] fails."""
        with pytest.raises(ValidationError) as exc_info:
            TaskStatus(
                task_id="test",
                status="processing",
                created_at=datetime.now(timezone.utc),
                progress_percentage=101,
            )
        errors = exc_info.value.errors()
        assert any("progress_percentage" in str(error["loc"]) for error in errors)


# ===== Integration Tests =====


class TestModelIntegration:
    """Integration tests combining multiple models."""

    def test_full_verification_workflow(self):
        """Test complete verification workflow with all models."""
        # Create request
        request = VerifyClaimRequest(
            claim_id="integration_test",
            claim_text="Integration test claim",
            corpus_ids=["test_corpus"],
            options=VerificationOptions(
                max_evidence_items=5, confidence_threshold=0.7
            ),
        )

        # Create evidence items
        evidence1 = EvidenceItem(
            id="ev1",
            text="Supporting evidence",
            source="Source A",
            relevance=0.95,
            url="https://example.com/evidence1",
            nli_label="entailment",
            nli_confidence=0.92,
        )

        evidence2 = EvidenceItem(
            id="ev2",
            text="More supporting evidence",
            source="Source B",
            relevance=0.88,
            url="https://example.com/evidence2",
            nli_label="entailment",
            nli_confidence=0.85,
        )

        # Create result
        result = VerificationResult(
            claim_id=request.claim_id,
            claim_text=request.claim_text,
            verdict="SUPPORTED",
            confidence=0.89,
            reasoning="Both evidence items strongly support the claim.",
            evidence=[evidence1, evidence2],
            verified_at=datetime.now(timezone.utc),
            processing_time_ms=1234,
            corpus_ids_searched=request.corpus_ids,
        )

        # Create task status
        task = TaskStatus(
            task_id="task_integration",
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            result=result,
            progress_percentage=100,
        )

        # Verify the complete workflow
        assert task.status == "completed"
        assert task.result.verdict == "SUPPORTED"
        assert len(task.result.evidence) == 2
        assert task.result.evidence[0].nli_label == "entailment"

    def test_json_serialization_round_trip(self):
        """Test that models can be serialized to JSON and back."""
        # Create complex nested structure
        evidence = EvidenceItem(
            id="json_test",
            text="JSON test evidence",
            source="Test Source",
            relevance=0.75,
            url="https://example.com",
            publication_date="2023-01-01",
            nli_label="neutral",
            nli_confidence=0.65,
        )

        result = VerificationResult(
            claim_id="json_claim",
            claim_text="JSON serialization test",
            verdict="NOT_ENOUGH_INFO",
            confidence=0.55,
            evidence=[evidence],
            verified_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            processing_time_ms=500,
        )

        # Serialize to JSON
        json_str = result.model_dump_json()
        assert "json_claim" in json_str
        assert "json_test" in json_str

        # Deserialize from JSON
        reconstructed = VerificationResult.model_validate_json(json_str)
        assert reconstructed.claim_id == result.claim_id
        assert reconstructed.verdict == result.verdict
        assert len(reconstructed.evidence) == 1
        assert reconstructed.evidence[0].id == evidence.id
