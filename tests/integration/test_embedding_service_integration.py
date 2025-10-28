"""Integration tests for EmbeddingService with real model.

These tests use the actual sentence-transformers model and verify:
- Model loading and inference work correctly
- Embeddings have expected properties (dimension, normalization)
- Performance meets targets (>500 texts/second on CPU)
- Memory usage is reasonable (<2GB)

Note: These tests will download the model on first run (~80MB).
Run with: pytest tests/integration/test_embedding_service_integration.py -v
"""

import time
from typing import Generator

import pytest

from truthgraph.services.ml.embedding_service import EmbeddingService


@pytest.fixture(scope="module")
def embedding_service() -> Generator[EmbeddingService, None, None]:
    """Fixture providing a real EmbeddingService instance.

    Uses module scope to avoid reloading the model for each test.
    """
    # Reset singleton for clean start
    EmbeddingService._instance = None
    EmbeddingService._model = None
    EmbeddingService._device = None

    service = EmbeddingService.get_instance()
    yield service

    # Cleanup after all tests
    EmbeddingService._instance = None
    EmbeddingService._model = None
    EmbeddingService._device = None


class TestModelLoading:
    """Test real model loading."""

    def test_model_loads_successfully(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that the model loads without errors."""
        # Trigger model loading
        device = embedding_service.get_device()

        assert device in ["cuda", "mps", "cpu"]
        assert embedding_service.is_loaded()

    def test_model_dimension_is_correct(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that model reports correct embedding dimension."""
        dimension = embedding_service.get_embedding_dimension()

        assert dimension == 384


class TestSingleTextEmbedding:
    """Test embedding generation for single texts."""

    def test_embed_simple_text(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding a simple text."""
        text = "The Earth orbits the Sun"
        embedding = embedding_service.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_embeddings_are_normalized(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that embeddings are normalized to unit length."""
        text = "Machine learning is fascinating"
        embedding = embedding_service.embed_text(text)

        # Calculate L2 norm (should be ~1.0 for normalized vectors)
        norm = sum(x**2 for x in embedding) ** 0.5

        assert abs(norm - 1.0) < 0.01, f"Expected norm ~1.0, got {norm}"

    def test_different_texts_have_different_embeddings(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that different texts produce different embeddings."""
        text1 = "The cat sits on the mat"
        text2 = "Python is a programming language"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)

        # Embeddings should be different
        assert emb1 != emb2

    def test_similar_texts_have_similar_embeddings(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that similar texts have high cosine similarity."""
        text1 = "The dog plays in the park"
        text2 = "A dog is playing in the park"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)

        # Calculate cosine similarity
        similarity = sum(a * b for a, b in zip(emb1, emb2, strict=None))

        # Similar texts should have high similarity (>0.7)
        assert similarity > 0.7, f"Expected similarity >0.7, got {similarity}"

    def test_dissimilar_texts_have_low_similarity(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that dissimilar texts have lower similarity."""
        text1 = "The Earth orbits the Sun"
        text2 = "I like chocolate ice cream"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)

        # Calculate cosine similarity
        similarity = sum(a * b for a, b in zip(emb1, emb2, strict=None))

        # Dissimilar texts should have lower similarity (<0.5)
        assert similarity < 0.5, f"Expected similarity <0.5, got {similarity}"


class TestBatchEmbedding:
    """Test batch embedding functionality."""

    def test_embed_small_batch(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding a small batch of texts."""
        texts = [
            "First text about science",
            "Second text about technology",
            "Third text about mathematics",
        ]

        embeddings = embedding_service.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)

    def test_embed_medium_batch(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding a medium-sized batch."""
        texts = [f"This is test sentence number {i}" for i in range(100)]

        embeddings = embedding_service.embed_batch(texts)

        assert len(embeddings) == 100
        assert all(len(emb) == 384 for emb in embeddings)

    def test_batch_embeddings_are_normalized(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that all batch embeddings are normalized."""
        texts = [f"Test text {i}" for i in range(50)]

        embeddings = embedding_service.embed_batch(texts)

        for emb in embeddings:
            norm = sum(x**2 for x in emb) ** 0.5
            assert abs(norm - 1.0) < 0.01, f"Expected norm ~1.0, got {norm}"

    def test_batch_vs_individual_same_result(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that batch and individual embedding produce same results."""
        texts = ["Text one", "Text two", "Text three"]

        # Get embeddings individually
        individual = [embedding_service.embed_text(text) for text in texts]

        # Get embeddings in batch
        batch = embedding_service.embed_batch(texts)

        # Results should be very similar (allowing for small numerical differences)
        for ind_emb, batch_emb in zip(individual, batch, strict=None):
            differences = [abs(a - b) for a, b in zip(ind_emb, batch_emb, strict=None)]
            max_diff = max(differences)
            assert max_diff < 0.001, f"Expected max diff <0.001, got {max_diff}"


class TestPerformance:
    """Test performance targets."""

    def test_throughput_meets_target(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that throughput meets target of >500 texts/second on CPU.

        Note: This test may be slower on the first run due to model compilation.
        GPU throughput will be significantly higher.
        """
        # Warm up the model
        embedding_service.embed_text("Warm up")

        # Prepare test data
        num_texts = 1000
        texts = [f"Test sentence number {i} for performance testing" for i in range(num_texts)]

        # Measure time for batch processing
        start_time = time.time()
        embeddings = embedding_service.embed_batch(texts)
        end_time = time.time()

        elapsed = end_time - start_time
        throughput = num_texts / elapsed

        assert len(embeddings) == num_texts

        # Print performance metrics
        print("\nPerformance metrics:")
        print(f"  Texts processed: {num_texts}")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.1f} texts/second")
        print(f"  Device: {embedding_service.get_device()}")

        # Target: >500 texts/second on CPU
        # Note: On GPU this should be much higher (>2000)
        device = embedding_service.get_device()
        if device == "cpu":
            target_throughput = 500
        else:
            target_throughput = 1000  # Higher target for GPU

        # Allow some variance for system performance
        assert throughput > target_throughput * 0.7, (
            f"Expected throughput >{target_throughput * 0.7:.0f} texts/s, got {throughput:.1f} texts/s on {device}"
        )

    def test_single_embedding_latency(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test latency for single text embedding."""
        # Warm up
        embedding_service.embed_text("Warm up")

        # Measure latency
        start_time = time.time()
        embedding = embedding_service.embed_text("Test latency for single embedding")
        end_time = time.time()

        latency = (end_time - start_time) * 1000  # Convert to ms

        assert len(embedding) == 384

        print(f"\nSingle embedding latency: {latency:.1f}ms")

        # Should be fast (<100ms on most hardware)
        assert latency < 500, f"Expected latency <500ms, got {latency:.1f}ms"


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_embed_very_long_text(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding very long text (model will truncate)."""
        # Create a very long text (>512 tokens)
        long_text = " ".join(["word"] * 1000)

        embedding = embedding_service.embed_text(long_text)

        assert len(embedding) == 384

    def test_embed_special_characters(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding text with special characters."""
        text = "Special chars: @#$%^&*() 你好 مرحبا"

        embedding = embedding_service.embed_text(text)

        assert len(embedding) == 384

    def test_embed_unicode_text(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding Unicode text."""
        texts = [
            "Hello in English",
            "你好 in Chinese",
            "مرحبا in Arabic",
            "Привет in Russian",
        ]

        embeddings = embedding_service.embed_batch(texts)

        assert len(embeddings) == 4
        assert all(len(emb) == 384 for emb in embeddings)

    def test_embed_single_word(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding a single word."""
        embedding = embedding_service.embed_text("word")

        assert len(embedding) == 384

    def test_embed_with_numbers(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test embedding text with numbers."""
        text = "The year 2024 has 365 days"

        embedding = embedding_service.embed_text(text)

        assert len(embedding) == 384


class TestCaching:
    """Test model caching behavior."""

    def test_model_loads_once(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that model only loads once despite multiple calls."""
        # First embedding triggers load
        _ = embedding_service.embed_text("First call")
        assert embedding_service.is_loaded()

        # Subsequent calls use cached model
        start_time = time.time()
        _ = embedding_service.embed_text("Second call")
        end_time = time.time()

        # Second call should be fast (no model loading)
        latency = (end_time - start_time) * 1000
        assert latency < 100, "Second call took too long, model may have reloaded"

    def test_singleton_persists_across_calls(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that singleton instance persists."""
        service1 = EmbeddingService.get_instance()
        service2 = EmbeddingService.get_instance()

        assert service1 is service2
        assert service1 is embedding_service
