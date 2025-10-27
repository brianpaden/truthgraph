"""Unit tests for VerificationPipelineService.

These tests verify the pipeline orchestration logic using mocked dependencies.
"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from truthgraph.services.ml.nli_service import NLILabel, NLIResult
from truthgraph.services.vector_search_service import SearchResult
from truthgraph.services.verification_pipeline_service import (
    EvidenceItem,
    VerdictLabel,
    VerificationPipelineResult,
    VerificationPipelineService,
    retry_on_failure,
)


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_retry_succeeds_on_first_attempt(self):
        """Test that successful operations don't retry."""
        mock_func = Mock(return_value="success")
        decorated = retry_on_failure(max_attempts=3)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test that operations retry after failures."""
        mock_func = Mock(
            side_effect=[RuntimeError("fail"), RuntimeError("fail"), "success"]
        )
        decorated = retry_on_failure(
            max_attempts=3, initial_delay=0.01, exceptions=(RuntimeError,)
        )(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_exhausts_attempts(self):
        """Test that retry gives up after max attempts."""
        mock_func = Mock(side_effect=RuntimeError("persistent failure"))
        decorated = retry_on_failure(
            max_attempts=3, initial_delay=0.01, exceptions=(RuntimeError,)
        )(mock_func)

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            decorated()

        assert mock_func.call_count == 3

    def test_retry_respects_exception_types(self):
        """Test that retry only catches specified exceptions."""
        mock_func = Mock(side_effect=ValueError("wrong type"))
        decorated = retry_on_failure(
            max_attempts=3, initial_delay=0.01, exceptions=(RuntimeError,)
        )(mock_func)

        with pytest.raises(ValueError, match="wrong type"):
            decorated()

        assert mock_func.call_count == 1  # No retries for ValueError


class TestVerificationPipelineService:
    """Test VerificationPipelineService initialization and configuration."""

    def test_initialization_default(self):
        """Test service initialization with default parameters."""
        service = VerificationPipelineService()

        assert service.embedding_dimension == 384
        assert service.cache_ttl_seconds == 3600
        assert service.embedding_service is not None
        assert service.nli_service is not None
        assert service.vector_search_service is not None
        assert len(service._verification_cache) == 0

    def test_initialization_custom_params(self):
        """Test service initialization with custom parameters."""
        mock_embedding = Mock()
        mock_nli = Mock()
        mock_vector_search = Mock()

        service = VerificationPipelineService(
            embedding_service=mock_embedding,
            nli_service=mock_nli,
            vector_search_service=mock_vector_search,
            embedding_dimension=1536,
            cache_ttl_seconds=7200,
        )

        assert service.embedding_service is mock_embedding
        assert service.nli_service is mock_nli
        assert service.vector_search_service is mock_vector_search
        assert service.embedding_dimension == 1536
        assert service.cache_ttl_seconds == 7200


class TestCachingMechanism:
    """Test caching functionality."""

    def test_compute_claim_hash_consistency(self):
        """Test that same claim produces same hash."""
        service = VerificationPipelineService()

        hash1 = service._compute_claim_hash("The Earth is round")
        hash2 = service._compute_claim_hash("The Earth is round")

        assert hash1 == hash2

    def test_compute_claim_hash_normalization(self):
        """Test that claim hash normalizes whitespace and case."""
        service = VerificationPipelineService()

        hash1 = service._compute_claim_hash("The Earth is round")
        hash2 = service._compute_claim_hash("  THE EARTH IS ROUND  ")

        assert hash1 == hash2

    def test_compute_claim_hash_different_claims(self):
        """Test that different claims produce different hashes."""
        service = VerificationPipelineService()

        hash1 = service._compute_claim_hash("The Earth is round")
        hash2 = service._compute_claim_hash("The Earth is flat")

        assert hash1 != hash2

    def test_cache_result_and_retrieve(self):
        """Test caching and retrieving results."""
        service = VerificationPipelineService()
        claim_text = "Test claim"

        result = VerificationPipelineResult(
            claim_id=uuid4(),
            claim_text=claim_text,
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.9,
            support_score=0.9,
            refute_score=0.05,
            neutral_score=0.05,
            evidence_items=[],
            reasoning="Test reasoning",
            pipeline_duration_ms=100.0,
            retrieval_method="vector",
        )

        service._cache_result(claim_text, result)
        cached = service._get_cached_result(claim_text)

        assert cached is not None
        assert cached.claim_text == claim_text
        assert cached.verdict == VerdictLabel.SUPPORTED

    def test_cache_expiration(self):
        """Test that expired cache entries are not returned."""
        service = VerificationPipelineService(cache_ttl_seconds=1)
        claim_text = "Test claim"

        result = VerificationPipelineResult(
            claim_id=uuid4(),
            claim_text=claim_text,
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.9,
            support_score=0.9,
            refute_score=0.05,
            neutral_score=0.05,
            evidence_items=[],
            reasoning="Test",
            pipeline_duration_ms=100.0,
            retrieval_method="vector",
        )

        # Manually insert expired entry
        claim_hash = service._compute_claim_hash(claim_text)
        expired_time = datetime.utcnow() - timedelta(seconds=10)
        service._verification_cache[claim_hash] = (result, expired_time)

        cached = service._get_cached_result(claim_text)

        assert cached is None
        assert claim_hash not in service._verification_cache

    def test_cache_miss(self):
        """Test cache miss for uncached claim."""
        service = VerificationPipelineService()
        cached = service._get_cached_result("Uncached claim")

        assert cached is None

    def test_clear_cache(self):
        """Test clearing all cache entries."""
        service = VerificationPipelineService()

        # Add multiple cache entries
        for i in range(5):
            claim_text = f"Claim {i}"
            result = VerificationPipelineResult(
                claim_id=uuid4(),
                claim_text=claim_text,
                verdict=VerdictLabel.SUPPORTED,
                confidence=0.9,
                support_score=0.9,
                refute_score=0.05,
                neutral_score=0.05,
                evidence_items=[],
                reasoning="Test",
                pipeline_duration_ms=100.0,
                retrieval_method="vector",
            )
            service._cache_result(claim_text, result)

        assert len(service._verification_cache) == 5

        service.clear_cache()

        assert len(service._verification_cache) == 0


class TestVerdictAggregation:
    """Test verdict aggregation logic."""

    def test_aggregate_verdict_strong_support(self):
        """Test aggregation with strong supporting evidence."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        evidence_items = [
            EvidenceItem(
                evidence_id=uuid4(),
                content="Supporting evidence 1",
                source_url="http://example.com/1",
                similarity=0.9,
                nli_label=NLILabel.ENTAILMENT,
                nli_confidence=0.95,
                nli_scores={"entailment": 0.95, "contradiction": 0.02, "neutral": 0.03},
            ),
            EvidenceItem(
                evidence_id=uuid4(),
                content="Supporting evidence 2",
                source_url="http://example.com/2",
                similarity=0.85,
                nli_label=NLILabel.ENTAILMENT,
                nli_confidence=0.92,
                nli_scores={"entailment": 0.92, "contradiction": 0.03, "neutral": 0.05},
            ),
        ]

        result = service._aggregate_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=evidence_items,
            pipeline_duration_ms=1000.0,
        )

        assert result.verdict == VerdictLabel.SUPPORTED
        assert result.confidence > 0.6
        assert result.support_score > result.refute_score
        assert len(result.evidence_items) == 2
        assert "support" in result.reasoning.lower()

    def test_aggregate_verdict_strong_refutation(self):
        """Test aggregation with strong refuting evidence."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        evidence_items = [
            EvidenceItem(
                evidence_id=uuid4(),
                content="Refuting evidence 1",
                source_url="http://example.com/1",
                similarity=0.9,
                nli_label=NLILabel.CONTRADICTION,
                nli_confidence=0.94,
                nli_scores={"entailment": 0.02, "contradiction": 0.94, "neutral": 0.04},
            ),
            EvidenceItem(
                evidence_id=uuid4(),
                content="Refuting evidence 2",
                source_url="http://example.com/2",
                similarity=0.88,
                nli_label=NLILabel.CONTRADICTION,
                nli_confidence=0.91,
                nli_scores={"entailment": 0.03, "contradiction": 0.91, "neutral": 0.06},
            ),
        ]

        result = service._aggregate_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=evidence_items,
            pipeline_duration_ms=1000.0,
        )

        assert result.verdict == VerdictLabel.REFUTED
        assert result.confidence > 0.6
        assert result.refute_score > result.support_score
        assert len(result.evidence_items) == 2
        assert "refut" in result.reasoning.lower() or "contradict" in result.reasoning.lower()

    def test_aggregate_verdict_mixed_evidence(self):
        """Test aggregation with mixed evidence."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        evidence_items = [
            EvidenceItem(
                evidence_id=uuid4(),
                content="Supporting evidence",
                source_url="http://example.com/1",
                similarity=0.8,
                nli_label=NLILabel.ENTAILMENT,
                nli_confidence=0.7,
                nli_scores={"entailment": 0.7, "contradiction": 0.15, "neutral": 0.15},
            ),
            EvidenceItem(
                evidence_id=uuid4(),
                content="Refuting evidence",
                source_url="http://example.com/2",
                similarity=0.75,
                nli_label=NLILabel.CONTRADICTION,
                nli_confidence=0.65,
                nli_scores={"entailment": 0.15, "contradiction": 0.65, "neutral": 0.20},
            ),
            EvidenceItem(
                evidence_id=uuid4(),
                content="Neutral evidence",
                source_url="http://example.com/3",
                similarity=0.7,
                nli_label=NLILabel.NEUTRAL,
                nli_confidence=0.8,
                nli_scores={"entailment": 0.1, "contradiction": 0.1, "neutral": 0.8},
            ),
        ]

        result = service._aggregate_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=evidence_items,
            pipeline_duration_ms=1000.0,
        )

        # With mixed evidence, should be INSUFFICIENT
        assert result.verdict == VerdictLabel.INSUFFICIENT
        assert len(result.evidence_items) == 3
        assert "insufficient" in result.reasoning.lower()

    def test_aggregate_verdict_no_evidence(self):
        """Test aggregation with no evidence."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        result = service._aggregate_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=[],
            pipeline_duration_ms=1000.0,
        )

        assert result.verdict == VerdictLabel.INSUFFICIENT
        assert result.confidence == 0.0
        assert len(result.evidence_items) == 0
        assert "no relevant evidence" in result.reasoning.lower()

    def test_aggregate_verdict_similarity_weighting(self):
        """Test that similarity scores properly weight NLI results."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        # High similarity, high confidence support
        high_sim = EvidenceItem(
            evidence_id=uuid4(),
            content="High similarity support",
            source_url="http://example.com/1",
            similarity=0.95,
            nli_label=NLILabel.ENTAILMENT,
            nli_confidence=0.9,
            nli_scores={"entailment": 0.9, "contradiction": 0.05, "neutral": 0.05},
        )

        # Low similarity, high confidence refutation (should be weighted less)
        low_sim = EvidenceItem(
            evidence_id=uuid4(),
            content="Low similarity refutation",
            source_url="http://example.com/2",
            similarity=0.3,
            nli_label=NLILabel.CONTRADICTION,
            nli_confidence=0.85,
            nli_scores={"entailment": 0.05, "contradiction": 0.85, "neutral": 0.10},
        )

        result = service._aggregate_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_items=[high_sim, low_sim],
            pipeline_duration_ms=1000.0,
        )

        # High similarity support should dominate
        assert result.support_score > result.refute_score


class TestInsufficientVerdict:
    """Test creation of INSUFFICIENT verdicts."""

    def test_create_insufficient_verdict(self):
        """Test creating INSUFFICIENT verdict."""
        service = VerificationPipelineService()
        claim_id = uuid4()
        claim_text = "Test claim"

        result = service._create_insufficient_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            pipeline_duration_ms=500.0,
        )

        assert result.verdict == VerdictLabel.INSUFFICIENT
        assert result.confidence == 0.0
        assert result.support_score == 0.0
        assert result.refute_score == 0.0
        assert result.neutral_score == 0.0
        assert len(result.evidence_items) == 0
        assert result.claim_id == claim_id
        assert result.claim_text == claim_text
        assert result.pipeline_duration_ms == 500.0
        assert "no relevant evidence" in result.reasoning.lower()


class TestReasoningGeneration:
    """Test reasoning text generation."""

    def test_generate_reasoning_supported(self):
        """Test reasoning for SUPPORTED verdict."""
        service = VerificationPipelineService()

        reasoning = service._generate_reasoning(
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.85,
            support_score=0.85,
            refute_score=0.1,
            neutral_score=0.05,
            support_count=3,
            refute_count=1,
            neutral_count=0,
            total_evidence=4,
        )

        assert "support" in reasoning.lower()
        assert "3 evidence" in reasoning.lower()
        assert "0.85" in reasoning

    def test_generate_reasoning_refuted(self):
        """Test reasoning for REFUTED verdict."""
        service = VerificationPipelineService()

        reasoning = service._generate_reasoning(
            verdict=VerdictLabel.REFUTED,
            confidence=0.82,
            support_score=0.12,
            refute_score=0.82,
            neutral_score=0.06,
            support_count=1,
            refute_count=3,
            neutral_count=0,
            total_evidence=4,
        )

        assert "refut" in reasoning.lower() or "contradict" in reasoning.lower()
        assert "3 evidence" in reasoning.lower()
        assert "0.82" in reasoning

    def test_generate_reasoning_insufficient_no_evidence(self):
        """Test reasoning for INSUFFICIENT verdict with no evidence."""
        service = VerificationPipelineService()

        reasoning = service._generate_reasoning(
            verdict=VerdictLabel.INSUFFICIENT,
            confidence=0.0,
            support_score=0.0,
            refute_score=0.0,
            neutral_score=0.0,
            support_count=0,
            refute_count=0,
            neutral_count=0,
            total_evidence=0,
        )

        assert "insufficient" in reasoning.lower()
        assert "no relevant evidence" in reasoning.lower()

    def test_generate_reasoning_insufficient_mixed(self):
        """Test reasoning for INSUFFICIENT verdict with mixed evidence."""
        service = VerificationPipelineService()

        reasoning = service._generate_reasoning(
            verdict=VerdictLabel.INSUFFICIENT,
            confidence=0.5,
            support_score=0.4,
            refute_score=0.35,
            neutral_score=0.25,
            support_count=2,
            refute_count=2,
            neutral_count=1,
            total_evidence=5,
        )

        assert "insufficient" in reasoning.lower()
        assert "2 supporting" in reasoning.lower()
        assert "2 refuting" in reasoning.lower()
        assert "1 neutral" in reasoning.lower()


class TestRetryWrapperMethods:
    """Test retry wrapper methods."""

    def test_generate_embedding_with_retry_success(self):
        """Test embedding generation with retry succeeds."""
        mock_embedding_service = Mock()
        mock_embedding_service.embed_text.return_value = [0.1] * 384

        service = VerificationPipelineService(
            embedding_service=mock_embedding_service
        )

        embedding = service._generate_embedding_with_retry("Test claim")

        assert len(embedding) == 384
        assert mock_embedding_service.embed_text.call_count == 1

    def test_search_evidence_with_retry_success(self):
        """Test evidence search with retry succeeds."""
        mock_vector_search = Mock()
        mock_results = [
            SearchResult(
                evidence_id=uuid4(),
                content="Evidence",
                source_url="http://example.com",
                similarity=0.9,
            )
        ]
        mock_vector_search.search_similar_evidence.return_value = mock_results

        service = VerificationPipelineService(
            vector_search_service=mock_vector_search
        )

        mock_db = Mock()
        results = service._search_evidence_with_retry(
            db=mock_db,
            query_embedding=[0.1] * 384,
            top_k=10,
            min_similarity=0.5,
            tenant_id="default",
        )

        assert len(results) == 1
        assert mock_vector_search.search_similar_evidence.call_count == 1
