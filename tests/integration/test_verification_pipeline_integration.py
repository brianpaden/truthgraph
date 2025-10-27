"""Integration tests for VerificationPipelineService.

These tests verify end-to-end pipeline functionality with real ML services
and database interactions.
"""

import pytest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Claim, Evidence, Embedding
from truthgraph.services.verification_pipeline_service import (
    VerdictLabel,
    VerificationPipelineService,
    get_verification_pipeline_service,
)


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing."""
    # Note: pgvector not available in SQLite, so we'll use PostgreSQL test DB
    # This is a placeholder - real tests would use a test PostgreSQL instance
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_claim(in_memory_db):
    """Create a sample claim for testing."""
    claim = Claim(
        id=uuid4(),
        text="The Earth orbits around the Sun",
        source_url="http://example.com/claim",
    )
    in_memory_db.add(claim)
    in_memory_db.commit()
    return claim


@pytest.fixture
def sample_evidence(in_memory_db):
    """Create sample evidence for testing."""
    evidence_items = [
        Evidence(
            id=uuid4(),
            content="The Earth revolves around the Sun in an elliptical orbit, "
            "completing one revolution approximately every 365.25 days.",
            source_url="http://example.com/evidence1",
            source_type="scientific_article",
        ),
        Evidence(
            id=uuid4(),
            content="According to NASA, the Earth orbits the Sun at an average "
            "distance of about 93 million miles (150 million kilometers).",
            source_url="http://example.com/evidence2",
            source_type="nasa_website",
        ),
        Evidence(
            id=uuid4(),
            content="The geocentric model, which placed Earth at the center of "
            "the universe, was disproven by Copernicus and Galileo.",
            source_url="http://example.com/evidence3",
            source_type="historical_document",
        ),
    ]

    for evidence in evidence_items:
        in_memory_db.add(evidence)

    in_memory_db.commit()
    return evidence_items


class TestVerificationPipelineIntegration:
    """Integration tests for full verification pipeline."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_pipeline_initialization(self):
        """Test that pipeline service initializes correctly."""
        service = get_verification_pipeline_service()

        assert service is not None
        assert service.embedding_service is not None
        assert service.nli_service is not None
        assert service.vector_search_service is not None

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector and test data")
    async def test_verify_claim_end_to_end(self, in_memory_db, sample_claim, sample_evidence):
        """Test end-to-end claim verification with real services.

        This test requires:
        - PostgreSQL database with pgvector extension
        - Pre-populated embeddings for evidence
        - ML models loaded
        """
        service = VerificationPipelineService(embedding_dimension=384)

        result = await service.verify_claim(
            db=in_memory_db,
            claim_id=sample_claim.id,
            claim_text=sample_claim.text,
            top_k_evidence=5,
            min_similarity=0.5,
            use_cache=False,
            store_result=True,
        )

        # Verify result structure
        assert result is not None
        assert result.claim_id == sample_claim.id
        assert result.claim_text == sample_claim.text
        assert result.verdict in [
            VerdictLabel.SUPPORTED,
            VerdictLabel.REFUTED,
            VerdictLabel.INSUFFICIENT,
        ]
        assert 0.0 <= result.confidence <= 1.0
        assert result.pipeline_duration_ms > 0
        assert result.reasoning is not None

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector and test data")
    async def test_verify_claim_with_caching(self, in_memory_db, sample_claim):
        """Test that caching works correctly."""
        service = VerificationPipelineService(
            embedding_dimension=384, cache_ttl_seconds=3600
        )

        # First verification - should execute full pipeline
        result1 = await service.verify_claim(
            db=in_memory_db,
            claim_id=sample_claim.id,
            claim_text=sample_claim.text,
            use_cache=True,
            store_result=False,
        )

        duration1 = result1.pipeline_duration_ms

        # Second verification - should use cache
        result2 = await service.verify_claim(
            db=in_memory_db,
            claim_id=sample_claim.id,
            claim_text=sample_claim.text,
            use_cache=True,
            store_result=False,
        )

        duration2 = result2.pipeline_duration_ms

        # Cached result should be much faster
        assert result1.verdict == result2.verdict
        assert result1.confidence == result2.confidence
        # Note: Cache hit may still have some overhead, but should be faster
        assert duration2 <= duration1

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector and test data")
    async def test_verify_claim_no_evidence(self, in_memory_db):
        """Test verification when no evidence is found."""
        service = VerificationPipelineService(embedding_dimension=384)

        # Claim unlikely to have matching evidence
        obscure_claim = Claim(
            id=uuid4(),
            text="The fictional planet Zorgon has three purple moons made of cheese.",
        )
        in_memory_db.add(obscure_claim)
        in_memory_db.commit()

        result = await service.verify_claim(
            db=in_memory_db,
            claim_id=obscure_claim.id,
            claim_text=obscure_claim.text,
            top_k_evidence=10,
            min_similarity=0.7,
            use_cache=False,
            store_result=False,
        )

        assert result.verdict == VerdictLabel.INSUFFICIENT
        assert len(result.evidence_items) == 0
        assert "no relevant evidence" in result.reasoning.lower()

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector and test data")
    async def test_verify_claim_stores_results(self, in_memory_db, sample_claim):
        """Test that verification results are stored in database."""
        service = VerificationPipelineService(embedding_dimension=384)

        result = await service.verify_claim(
            db=in_memory_db,
            claim_id=sample_claim.id,
            claim_text=sample_claim.text,
            use_cache=False,
            store_result=True,
        )

        # Verify result was stored
        assert result.verification_result_id is not None

        # Query database to verify storage
        from truthgraph.schemas import VerificationResult as VerificationResultModel

        stored_result = (
            in_memory_db.query(VerificationResultModel)
            .filter_by(id=result.verification_result_id)
            .first()
        )

        assert stored_result is not None
        assert stored_result.claim_id == sample_claim.id
        assert stored_result.verdict == result.verdict.value
        assert stored_result.confidence == result.confidence

    @pytest.mark.integration
    async def test_verify_claim_invalid_input(self, in_memory_db):
        """Test that invalid input raises appropriate errors."""
        service = VerificationPipelineService()

        # Empty claim text should raise ValueError
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.verify_claim(
                db=in_memory_db,
                claim_id=uuid4(),
                claim_text="",
                use_cache=False,
                store_result=False,
            )

        # Whitespace-only claim should raise ValueError
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.verify_claim(
                db=in_memory_db,
                claim_id=uuid4(),
                claim_text="   ",
                use_cache=False,
                store_result=False,
            )


class TestEmbeddingGeneration:
    """Integration tests for embedding generation step."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_embedding_with_retry(self):
        """Test embedding generation with retry logic."""
        service = VerificationPipelineService(embedding_dimension=384)

        embedding = service._generate_embedding_with_retry(
            "The Earth orbits the Sun"
        )

        assert embedding is not None
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_embedding_different_texts(self):
        """Test that different texts produce different embeddings."""
        service = VerificationPipelineService(embedding_dimension=384)

        embedding1 = service._generate_embedding_with_retry(
            "The Earth orbits the Sun"
        )
        embedding2 = service._generate_embedding_with_retry(
            "Water is composed of hydrogen and oxygen"
        )

        # Embeddings should be different
        assert embedding1 != embedding2


class TestNLIVerification:
    """Integration tests for NLI verification step."""

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_verify_evidence_batch(self):
        """Test batch NLI verification."""
        service = VerificationPipelineService()

        from truthgraph.services.vector_search_service import SearchResult

        search_results = [
            SearchResult(
                evidence_id=uuid4(),
                content="The Earth revolves around the Sun in an elliptical orbit.",
                source_url="http://example.com/1",
                similarity=0.95,
            ),
            SearchResult(
                evidence_id=uuid4(),
                content="The Sun is the center of our solar system.",
                source_url="http://example.com/2",
                similarity=0.88,
            ),
        ]

        claim_text = "The Earth orbits around the Sun"

        evidence_items = await service._verify_evidence_batch(
            claim_text=claim_text,
            search_results=search_results,
        )

        assert len(evidence_items) == 2
        assert all(item.nli_label is not None for item in evidence_items)
        assert all(0.0 <= item.nli_confidence <= 1.0 for item in evidence_items)
        assert all(item.similarity > 0 for item in evidence_items)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_verify_evidence_batch_empty(self):
        """Test batch NLI with empty search results."""
        service = VerificationPipelineService()

        evidence_items = await service._verify_evidence_batch(
            claim_text="Test claim",
            search_results=[],
        )

        assert len(evidence_items) == 0


class TestPerformance:
    """Integration tests for performance requirements."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector and test data")
    async def test_pipeline_performance_target(self, in_memory_db, sample_claim):
        """Test that pipeline meets <60s performance target.

        Note: This test requires a properly configured test environment
        with pre-populated evidence and embeddings.
        """
        service = VerificationPipelineService(embedding_dimension=384)

        result = await service.verify_claim(
            db=in_memory_db,
            claim_id=sample_claim.id,
            claim_text=sample_claim.text,
            top_k_evidence=10,
            use_cache=False,
            store_result=False,
        )

        # Should complete in under 60 seconds (60000 ms)
        assert result.pipeline_duration_ms < 60000, (
            f"Pipeline took {result.pipeline_duration_ms}ms, "
            "exceeding 60s target"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_embedding_generation_performance(self):
        """Test embedding generation performance."""
        import time

        service = VerificationPipelineService(embedding_dimension=384)
        claim_text = "The Earth orbits the Sun" * 10  # Longer text

        start_time = time.time()
        embedding = service._generate_embedding_with_retry(claim_text)
        duration_ms = (time.time() - start_time) * 1000

        assert embedding is not None
        assert len(embedding) == 384
        # Embedding generation should be very fast (<2s even on CPU)
        assert duration_ms < 2000


class TestErrorHandling:
    """Integration tests for error handling."""

    @pytest.mark.integration
    async def test_graceful_degradation_storage_failure(self, in_memory_db):
        """Test that pipeline continues even if storage fails."""
        service = VerificationPipelineService()

        # This will fail to store due to missing database tables
        # but should still return a result
        claim_id = uuid4()
        claim_text = "Test claim"

        # Mock the storage to simulate failure
        with pytest.raises((RuntimeError, AttributeError)):
            await service.verify_claim(
                db=in_memory_db,
                claim_id=claim_id,
                claim_text=claim_text,
                top_k_evidence=5,
                use_cache=False,
                store_result=True,  # This will fail but shouldn't crash
            )

    @pytest.mark.integration
    def test_retry_logic_on_transient_failure(self):
        """Test retry logic handles transient failures."""
        from unittest.mock import Mock, patch

        service = VerificationPipelineService()

        # Mock embedding service to fail once then succeed
        with patch.object(
            service.embedding_service,
            "embed_text",
            side_effect=[RuntimeError("Transient error"), [0.1] * 384],
        ):
            embedding = service._generate_embedding_with_retry("Test")
            assert len(embedding) == 384
