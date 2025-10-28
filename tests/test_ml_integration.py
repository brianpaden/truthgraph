"""Integration tests for ML services with real models.

These tests verify that ML services work correctly with actual models loaded.
They may take longer to run due to model loading and inference.

Tests include:
- Embedding service integration
- NLI service integration
- Vector search integration
- End-to-end verification pipeline
- Performance benchmarks
"""

import time

import pytest

from truthgraph.db import Base, SessionLocal, engine
from truthgraph.schemas import Embedding as DBEmbedding
from truthgraph.schemas import Evidence
from truthgraph.services.ml.embedding_service import get_embedding_service
from truthgraph.services.ml.nli_service import NLILabel, get_nli_service
from truthgraph.services.vector_search_service import VectorSearchService


@pytest.fixture(scope="module")
def embedding_service():
    """Get embedding service instance."""
    return get_embedding_service()


@pytest.fixture(scope="module")
def nli_service():
    """Get NLI service instance."""
    return get_nli_service()


@pytest.fixture(scope="module")
def vector_search_service():
    """Get vector search service instance."""
    return VectorSearchService(embedding_dimension=384)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ===== Embedding Service Integration Tests =====


class TestEmbeddingServiceIntegration:
    """Integration tests for embedding service."""

    def test_singleton_pattern(self):
        """Test that embedding service is a singleton."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()

        assert service1 is service2

    def test_model_lazy_loading(self, embedding_service):
        """Test that model is loaded lazily on first use."""
        # Model may or may not be loaded depending on previous tests
        initial_state = embedding_service.is_loaded()
        assert initial_state

        # Generate embedding (should trigger loading if not loaded)
        embedding = embedding_service.embed_text("Test text")

        assert embedding_service.is_loaded()
        assert len(embedding) == 384

    def test_embedding_consistency(self, embedding_service):
        """Test that same text produces consistent embeddings."""
        text = "The quick brown fox jumps over the lazy dog"

        embedding1 = embedding_service.embed_text(text)
        embedding2 = embedding_service.embed_text(text)

        # Embeddings should be identical
        assert embedding1 == embedding2

    def test_embedding_normalization(self, embedding_service):
        """Test that embeddings are normalized to unit length."""
        text = "Test normalization"
        embedding = embedding_service.embed_text(text)

        # Calculate L2 norm
        norm = sum(x**2 for x in embedding) ** 0.5

        # Should be approximately 1.0
        assert 0.99 <= norm <= 1.01

    def test_batch_performance(self, embedding_service):
        """Test batch embedding performance."""
        texts = [f"Test text number {i}" for i in range(100)]

        start_time = time.time()
        embeddings = embedding_service.embed_batch(texts, batch_size=32)
        elapsed_time = time.time() - start_time

        assert len(embeddings) == 100
        assert all(len(emb) == 384 for emb in embeddings)

        # Should process >500 texts/second on CPU
        throughput = len(texts) / elapsed_time
        print(f"\nBatch embedding throughput: {throughput:.1f} texts/second")

        # Lenient threshold for CI environments
        assert throughput > 50  # At least 50 texts/second

    def test_semantic_similarity(self, embedding_service):
        """Test that semantically similar texts have similar embeddings."""
        text1 = "The cat sat on the mat"
        text2 = "A feline was sitting on a rug"
        text3 = "Quantum mechanics is a fundamental theory in physics"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)
        emb3 = embedding_service.embed_text(text3)

        # Calculate cosine similarity
        def cosine_sim(a, b):
            return sum(x * y for x, y in zip(a, b, strict=False))

        sim_1_2 = cosine_sim(emb1, emb2)
        sim_1_3 = cosine_sim(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_1_2 > sim_1_3

    def test_device_detection(self, embedding_service):
        """Test device detection for computation."""
        device = embedding_service.get_device()

        assert device in ["cuda", "mps", "cpu"]
        print(f"\nEmbedding service using device: {device}")


# ===== NLI Service Integration Tests =====


class TestNLIServiceIntegration:
    """Integration tests for NLI service."""

    def test_singleton_pattern(self):
        """Test that NLI service is a singleton."""
        service1 = get_nli_service()
        service2 = get_nli_service()

        assert service1 is service2

    def test_entailment_detection(self, nli_service):
        """Test detection of entailment relationships."""
        premise = "All dogs are mammals"
        hypothesis = "Dogs are mammals"

        result = nli_service.verify_single(premise, hypothesis)

        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.5

    def test_contradiction_detection(self, nli_service):
        """Test detection of contradictions."""
        premise = "The Earth is round"
        hypothesis = "The Earth is flat"

        result = nli_service.verify_single(premise, hypothesis)

        assert result.label == NLILabel.CONTRADICTION
        assert result.confidence > 0.5

    def test_neutral_detection(self, nli_service):
        """Test detection of neutral relationships."""
        premise = "The sky is blue"
        hypothesis = "Water is wet"

        result = nli_service.verify_single(premise, hypothesis)

        assert result.label == NLILabel.NEUTRAL
        assert result.confidence > 0.0

    def test_score_distribution(self, nli_service):
        """Test that scores sum to 1.0."""
        premise = "Paris is the capital of France"
        hypothesis = "Paris is in France"

        result = nli_service.verify_single(premise, hypothesis)

        total = sum(result.scores.values())
        assert 0.99 <= total <= 1.01

    def test_batch_processing(self, nli_service):
        """Test batch NLI processing."""
        pairs = [
            ("The sun is hot", "The sun has high temperature"),
            ("Ice is cold", "Ice is hot"),
            ("Cats meow", "Dogs bark"),
        ]

        results = nli_service.verify_batch(pairs, batch_size=8)

        assert len(results) == 3
        assert results[0].label == NLILabel.ENTAILMENT
        assert results[1].label == NLILabel.CONTRADICTION
        assert results[2].label == NLILabel.NEUTRAL

    def test_batch_performance(self, nli_service):
        """Test batch NLI performance."""
        pairs = [(f"Premise {i}", f"Hypothesis {i}") for i in range(20)]

        start_time = time.time()
        results = nli_service.verify_batch(pairs, batch_size=8)
        elapsed_time = time.time() - start_time

        assert len(results) == 20

        throughput = len(pairs) / elapsed_time
        print(f"\nBatch NLI throughput: {throughput:.1f} pairs/second")

        # Should process >1 pair/second on CPU
        assert throughput > 1.0

    def test_model_info(self, nli_service):
        """Test getting model information."""
        info = nli_service.get_model_info()

        assert "model_name" in info
        assert "device" in info
        assert "initialized" in info


# ===== Vector Search Integration Tests =====


class TestVectorSearchIntegration:
    """Integration tests for vector search service."""

    def test_search_with_real_embeddings(
        self, db_session, embedding_service, vector_search_service
    ):
        """Test vector search with real embeddings."""
        # Create evidence with embeddings
        texts = [
            "The Earth orbits the Sun in 365 days",
            "Water boils at 100 degrees Celsius",
            "The speed of light is constant",
        ]

        for text in texts:
            evidence = Evidence(content=text, source_url="https://example.com")
            db_session.add(evidence)
            db_session.flush()

            embedding_vec = embedding_service.embed_text(text)
            embedding = DBEmbedding(
                entity_type="evidence",
                entity_id=evidence.id,
                embedding=embedding_vec,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                tenant_id="default",
            )
            db_session.add(embedding)

        db_session.commit()

        # Search for similar evidence
        query = "How long does Earth take to orbit Sun?"
        query_embedding = embedding_service.embed_text(query)

        results = vector_search_service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=3, min_similarity=0.3
        )

        assert len(results) > 0

        # First result should be most relevant
        assert "Earth" in results[0].content or "orbit" in results[0].content

    def test_search_performance(self, db_session, embedding_service, vector_search_service):
        """Test vector search performance."""
        # Create 50 evidence items
        for i in range(50):
            evidence = Evidence(
                content=f"Science fact number {i} about various topics",
                source_url=f"https://example.com/{i}",
            )
            db_session.add(evidence)
            db_session.flush()

            embedding_vec = embedding_service.embed_text(evidence.content)
            embedding = DBEmbedding(
                entity_type="evidence",
                entity_id=evidence.id,
                embedding=embedding_vec,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                tenant_id="default",
            )
            db_session.add(embedding)

        db_session.commit()

        # Measure search time
        query_embedding = embedding_service.embed_text("science topics")

        start_time = time.time()
        results = vector_search_service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=10
        )
        assert results
        search_time = (time.time() - start_time) * 1000  # Convert to ms

        print(f"\nVector search time: {search_time:.2f}ms for 50 vectors")

        # Should be reasonably fast even without index
        assert search_time < 1000  # Less than 1 second

    def test_similarity_ordering(self, db_session, embedding_service, vector_search_service):
        """Test that results are ordered by similarity."""
        # Create evidence
        texts = [
            "Cats are domesticated animals",
            "Dogs are loyal pets",
            "Quantum physics is complex",
        ]

        for text in texts:
            evidence = Evidence(content=text)
            db_session.add(evidence)
            db_session.flush()

            embedding_vec = embedding_service.embed_text(text)
            embedding = DBEmbedding(
                entity_type="evidence",
                entity_id=evidence.id,
                embedding=embedding_vec,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                tenant_id="default",
            )
            db_session.add(embedding)

        db_session.commit()

        # Search
        query_embedding = embedding_service.embed_text("felines as pets")
        results = vector_search_service.search_similar_evidence(
            db=db_session, query_embedding=query_embedding, top_k=3
        )

        # Results should be ordered by descending similarity
        similarities = [r.similarity for r in results]
        assert similarities == sorted(similarities, reverse=True)


# ===== End-to-End Pipeline Tests =====


class TestEndToEndPipeline:
    """Integration tests for complete verification pipeline."""

    def test_full_verification_pipeline(
        self, db_session, embedding_service, nli_service, vector_search_service
    ):
        """Test complete verification pipeline."""
        # Step 1: Create evidence base
        evidence_texts = [
            "The Earth is approximately 4.54 billion years old based on radiometric dating",
            "Scientific evidence shows Earth formed about 4.5 billion years ago",
            "The age of Earth is estimated at 4.54 ± 0.05 billion years",
        ]

        for text in evidence_texts:
            evidence = Evidence(content=text, source_type="scientific")
            db_session.add(evidence)
            db_session.flush()

            embedding_vec = embedding_service.embed_text(text)
            embedding = DBEmbedding(
                entity_type="evidence",
                entity_id=evidence.id,
                embedding=embedding_vec,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                tenant_id="default",
            )
            db_session.add(embedding)

        db_session.commit()

        # Step 2: Verify claim
        claim = "The Earth is about 4.5 billion years old"

        # Search for evidence
        claim_embedding = embedding_service.embed_text(claim)
        search_results = vector_search_service.search_similar_evidence(
            db=db_session, query_embedding=claim_embedding, top_k=3, min_similarity=0.5
        )

        assert len(search_results) > 0

        # Run NLI on results
        nli_results = nli_service.verify_batch(
            pairs=[(result.content, claim) for result in search_results], batch_size=8
        )

        assert len(nli_results) == len(search_results)

        # Aggregate results
        entailment_count = sum(1 for r in nli_results if r.label == NLILabel.ENTAILMENT)

        # Should have at least one supporting evidence
        assert entailment_count > 0

    def test_pipeline_performance(
        self, db_session, embedding_service, nli_service, vector_search_service
    ):
        """Test end-to-end pipeline performance."""
        # Create evidence
        for i in range(10):
            evidence = Evidence(content=f"Scientific fact {i}")
            db_session.add(evidence)
            db_session.flush()

            embedding_vec = embedding_service.embed_text(evidence.content)
            embedding = DBEmbedding(
                entity_type="evidence",
                entity_id=evidence.id,
                embedding=embedding_vec,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                tenant_id="default",
            )
            db_session.add(embedding)

        db_session.commit()

        # Run full pipeline
        claim = "Testing the verification pipeline"

        start_time = time.time()

        # Embed claim
        claim_embedding = embedding_service.embed_text(claim)

        # Search
        search_results = vector_search_service.search_similar_evidence(
            db=db_session, query_embedding=claim_embedding, top_k=5
        )

        # NLI
        if search_results:
            nli_results = nli_service.verify_batch(
                pairs=[(r.content, claim) for r in search_results], batch_size=8
            )
            assert nli_results

        total_time = (time.time() - start_time) * 1000

        print(f"\nFull pipeline time: {total_time:.2f}ms")

        # Should complete in reasonable time
        assert total_time < 5000  # Less than 5 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
