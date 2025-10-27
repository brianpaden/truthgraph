"""Unit tests for the EmbeddingService class.

These tests use mocks to test the embedding service without loading the actual model.
For integration tests with the real model, see test_embedding_service_integration.py.
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from truthgraph.services.ml.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset the singleton instance before each test.

    This ensures tests don't interfere with each other.
    """
    EmbeddingService._instance = None
    EmbeddingService._model = None
    EmbeddingService._device = None


class TestEmbeddingServiceSingleton:
    """Test singleton pattern implementation."""

    def test_get_instance_creates_singleton(self) -> None:
        """Test that get_instance creates and returns singleton."""
        service1 = EmbeddingService.get_instance()
        service2 = EmbeddingService.get_instance()

        assert service1 is service2
        assert isinstance(service1, EmbeddingService)

    def test_direct_instantiation_raises_error(self) -> None:
        """Test that direct instantiation after singleton creation raises error."""
        _ = EmbeddingService.get_instance()

        with pytest.raises(RuntimeError, match="singleton"):
            EmbeddingService()

    def test_get_embedding_service_returns_singleton(self) -> None:
        """Test convenience function returns singleton."""
        service1 = get_embedding_service()
        service2 = EmbeddingService.get_instance()

        assert service1 is service2


class TestDeviceDetection:
    """Test device detection functionality."""

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.get_device_name")
    @patch("torch.cuda.get_device_properties")
    def test_detect_device_cuda(
        self,
        mock_props: Mock,
        mock_name: Mock,
        mock_cuda: Mock,
    ) -> None:
        """Test CUDA device detection."""
        mock_cuda.return_value = True
        mock_name.return_value = "NVIDIA GeForce RTX 3080"
        mock_props.return_value = Mock(total_memory=10e9)

        device = EmbeddingService._detect_device()

        assert device == "cuda"
        mock_cuda.assert_called_once()

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_detect_device_mps(
        self,
        mock_mps: Mock,
        mock_cuda: Mock,
    ) -> None:
        """Test MPS (Apple Silicon) device detection."""
        mock_cuda.return_value = False
        mock_mps.return_value = True

        device = EmbeddingService._detect_device()

        assert device == "mps"

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_detect_device_cpu_fallback(
        self,
        mock_mps: Mock,
        mock_cuda: Mock,
    ) -> None:
        """Test CPU fallback when no accelerators available."""
        mock_cuda.return_value = False
        mock_mps.return_value = False

        device = EmbeddingService._detect_device()

        assert device == "cpu"


class TestModelLoading:
    """Test model loading functionality."""

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_load_model_success(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test successful model loading."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        service._load_model()

        assert service._device == "cpu"
        assert service._model is mock_model
        mock_transformer.assert_called_once_with(
            "sentence-transformers/all-mpnet-base-v2",
            device="cpu",
        )
        mock_model.eval.assert_called_once()

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_load_model_idempotent(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that loading model multiple times only loads once."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        service._load_model()
        service._load_model()
        service._load_model()

        # Should only be called once
        mock_transformer.assert_called_once()

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_load_model_failure_raises_runtime_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that model loading failure raises RuntimeError."""
        mock_detect.return_value = "cpu"
        mock_transformer.side_effect = Exception("Model download failed")

        service = EmbeddingService.get_instance()

        with pytest.raises(RuntimeError, match="Failed to load embedding model"):
            service._load_model()


class TestEmbedText:
    """Test single text embedding."""

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_text_success(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test successful text embedding."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()

        # Create a proper numpy array with 384 dimensions
        expected_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = expected_embedding
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        result = service.embed_text("The Earth orbits the Sun")

        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

        mock_model.encode.assert_called_once_with(
            "The Earth orbits the Sun",
            normalize_embeddings=True,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_text_empty_string_raises_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that empty string raises ValueError."""
        mock_detect.return_value = "cpu"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()

        with pytest.raises(ValueError, match="non-empty string"):
            service.embed_text("")

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_text_invalid_type_raises_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that invalid input type raises ValueError."""
        mock_detect.return_value = "cpu"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()

        with pytest.raises(ValueError, match="non-empty string"):
            service.embed_text(123)  # type: ignore

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_text_model_failure_raises_runtime_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that model encoding failure raises RuntimeError."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()
        mock_model.encode.side_effect = Exception("Encoding failed")
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()

        with pytest.raises(RuntimeError, match="Failed to generate embedding"):
            service.embed_text("Test text")


class TestEmbedBatch:
    """Test batch embedding."""

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_batch_success(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test successful batch embedding."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()

        # Create proper numpy array for batch
        texts = ["Text 1", "Text 2", "Text 3"]
        expected_embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.return_value = expected_embeddings
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        result = service.embed_batch(texts)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(len(emb) == 384 for emb in result)
        assert all(isinstance(emb, list) for emb in result)

        mock_model.encode.assert_called_once_with(
            texts,
            batch_size=32,  # Default for CPU
            normalize_embeddings=True,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_batch_custom_batch_size(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test batch embedding with custom batch size."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()

        texts = ["Text 1", "Text 2"]
        expected_embeddings = np.random.rand(2, 384).astype(np.float32)
        mock_model.encode.return_value = expected_embeddings
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        result = service.embed_batch(texts, batch_size=64)

        assert len(result) == 2

        mock_model.encode.assert_called_once_with(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_batch_gpu_uses_larger_batch_size(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that GPU device uses larger default batch size."""
        mock_detect.return_value = "cuda"
        mock_model = MagicMock()

        texts = ["Text 1", "Text 2"]
        expected_embeddings = np.random.rand(2, 384).astype(np.float32)
        mock_model.encode.return_value = expected_embeddings
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        result = service.embed_batch(texts)

        assert len(result) == 2

        # Should use batch size 128 for GPU
        call_args = mock_model.encode.call_args
        assert call_args[1]["batch_size"] == 128

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_batch_empty_list_raises_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that empty list raises ValueError."""
        mock_detect.return_value = "cpu"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()

        with pytest.raises(ValueError, match="cannot be empty"):
            service.embed_batch([])

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_embed_batch_invalid_text_raises_error(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that list with invalid text raises ValueError."""
        mock_detect.return_value = "cpu"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()

        with pytest.raises(ValueError, match="non-empty strings"):
            service.embed_batch(["Valid", "", "Also valid"])

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    @patch("truthgraph.services.ml.embedding_service.gc.collect")
    def test_embed_batch_large_triggers_cleanup(
        self,
        mock_gc: Mock,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test that large batches trigger memory cleanup."""
        mock_detect.return_value = "cpu"
        mock_model = MagicMock()

        # Create large batch
        texts = [f"Text {i}" for i in range(1500)]
        expected_embeddings = np.random.rand(1500, 384).astype(np.float32)
        mock_model.encode.return_value = expected_embeddings
        mock_transformer.return_value = mock_model

        service = EmbeddingService.get_instance()
        service.embed_batch(texts)

        # Should trigger gc.collect()
        mock_gc.assert_called()


class TestUtilityMethods:
    """Test utility methods."""

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_get_device(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test get_device returns correct device."""
        mock_detect.return_value = "cuda"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()
        device = service.get_device()

        assert device == "cuda"

    def test_get_embedding_dimension(self) -> None:
        """Test get_embedding_dimension returns correct value."""
        service = EmbeddingService.get_instance()
        dimension = service.get_embedding_dimension()

        assert dimension == 384

    @patch("truthgraph.services.ml.embedding_service.SentenceTransformer")
    @patch("truthgraph.services.ml.embedding_service.EmbeddingService._detect_device")
    def test_is_loaded(
        self,
        mock_detect: Mock,
        mock_transformer: Mock,
    ) -> None:
        """Test is_loaded correctly reports model state."""
        mock_detect.return_value = "cpu"
        mock_transformer.return_value = MagicMock()

        service = EmbeddingService.get_instance()

        assert not service.is_loaded()

        service._load_model()

        assert service.is_loaded()


class TestMemoryCleanup:
    """Test memory cleanup functionality."""

    @patch("truthgraph.services.ml.embedding_service.gc.collect")
    @patch("torch.cuda.is_available")
    @patch("torch.cuda.empty_cache")
    def test_cleanup_memory_cuda(
        self,
        mock_empty_cache: Mock,
        mock_cuda_available: Mock,
        mock_gc: Mock,
    ) -> None:
        """Test memory cleanup for CUDA."""
        mock_cuda_available.return_value = True

        service = EmbeddingService.get_instance()
        service._device = "cuda"
        service._cleanup_memory()

        mock_gc.assert_called_once()
        mock_empty_cache.assert_called_once()

    @patch("truthgraph.services.ml.embedding_service.gc.collect")
    def test_cleanup_memory_cpu(
        self,
        mock_gc: Mock,
    ) -> None:
        """Test memory cleanup for CPU."""
        service = EmbeddingService.get_instance()
        service._device = "cpu"
        service._cleanup_memory()

        mock_gc.assert_called_once()
