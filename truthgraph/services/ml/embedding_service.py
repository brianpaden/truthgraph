"""Embedding generation service using sentence-transformers.

This module provides a singleton service for generating semantic embeddings
from text using the sentence-transformers library with the all-MiniLM-L6-v2 model.
The service supports GPU/CPU/MPS device detection, batch processing, and efficient
model caching.

Performance targets:
    - >500 texts/second throughput (batch processing on CPU)
    - 384-dimensional embeddings
    - <2GB memory usage
    - Model loads once (singleton pattern)

Example:
    >>> service = EmbeddingService.get_instance()
    >>> embedding = service.embed_text("The Earth orbits the Sun")
    >>> len(embedding)
    384
    >>> embeddings = service.embed_batch(["text1", "text2", "text3"])
    >>> len(embeddings)
    3
"""

import gc
import logging
from typing import ClassVar

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton service for generating text embeddings.

    This class implements the singleton pattern to ensure only one model instance
    is loaded in memory. It provides methods for generating embeddings from single
    texts or batches of texts with automatic device detection and memory optimization.

    The service uses the sentence-transformers/all-MiniLM-L6-v2 model which produces
    384-dimensional embeddings normalized to unit length.

    Attributes:
        _instance: Class variable storing the singleton instance
        _model: The loaded SentenceTransformer model
        _device: The device being used (cuda, mps, or cpu)

    Thread Safety:
        This implementation is NOT thread-safe. For multi-threaded applications,
        external synchronization is required.
    """

    _instance: ClassVar["EmbeddingService | None"] = None
    _model: SentenceTransformer | None = None
    _device: str | None = None

    # Model configuration
    MODEL_NAME: ClassVar[str] = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: ClassVar[int] = 384
    DEFAULT_BATCH_SIZE: ClassVar[int] = 32

    def __init__(self) -> None:
        """Initialize the embedding service.

        This should not be called directly. Use get_instance() instead.

        Raises:
            RuntimeError: If called more than once (singleton violation)
        """
        if EmbeddingService._instance is not None:
            raise RuntimeError("EmbeddingService is a singleton. Use get_instance() instead.")

        # Model will be lazy-loaded on first use
        self._model = None
        self._device = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Get or create the singleton instance of EmbeddingService.

        This method implements the singleton pattern. The first call creates
        the instance, subsequent calls return the same instance.

        Returns:
            The singleton EmbeddingService instance

        Example:
            >>> service1 = EmbeddingService.get_instance()
            >>> service2 = EmbeddingService.get_instance()
            >>> service1 is service2
            True
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info("Created new EmbeddingService singleton instance")
        return cls._instance

    @staticmethod
    def _detect_device() -> str:
        """Detect the best available device for computation.

        Checks for available devices in order of preference:
        1. CUDA (NVIDIA GPU)
        2. MPS (Apple Silicon GPU)
        3. CPU (fallback)

        Returns:
            Device string: "cuda", "mps", or "cpu"

        Example:
            >>> device = EmbeddingService._detect_device()
            >>> device in ["cuda", "mps", "cpu"]
            True
        """
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(
                f"CUDA available: {torch.cuda.get_device_name(0)}, "
                f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f}GB"
            )
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            logger.info("MPS (Apple Silicon) acceleration available")
        else:
            device = "cpu"
            logger.info("Using CPU for computation")

        return device

    def _load_model(self) -> None:
        """Load the sentence-transformers model if not already loaded.

        This method implements lazy loading - the model is only loaded when
        first needed. The model is cached for subsequent calls.

        The model is configured with:
        - Automatic device detection (GPU/CPU/MPS)
        - Normalized embeddings (unit length)
        - Eval mode (no gradient computation)

        Raises:
            RuntimeError: If model loading fails
        """
        if self._model is not None:
            logger.debug("Model already loaded, skipping initialization")
            return

        try:
            # Detect device
            self._device = self._detect_device()
            logger.info(f"Loading model {self.MODEL_NAME} on device: {self._device}")

            # Load model
            self._model = SentenceTransformer(
                self.MODEL_NAME,
                device=self._device,
            )

            # Set to eval mode for inference
            self._model.eval()

            logger.info(
                f"Model loaded successfully. Embedding dimension: {self.EMBEDDING_DIMENSION}"
            )

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load embedding model: {e}") from e

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        This method generates a 384-dimensional semantic embedding for the input text.
        The embedding is normalized to unit length and suitable for cosine similarity.

        Args:
            text: Input text to embed. Must be non-empty string.

        Returns:
            List of 384 float values representing the text embedding

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If model fails to generate embedding

        Example:
            >>> service = EmbeddingService.get_instance()
            >>> embedding = service.embed_text("Machine learning is fascinating")
            >>> len(embedding)
            384
            >>> abs(sum(x**2 for x in embedding) - 1.0) < 0.01  # Check normalization
            True
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")

        # Ensure model is loaded
        self._load_model()

        try:
            # Generate embedding (returns numpy array)
            # convert_to_tensor=False ensures we get numpy arrays
            assert self._model is not None, "Model must be loaded"
            embedding_array = self._model.encode(
                text,
                normalize_embeddings=True,
                convert_to_tensor=False,
                show_progress_bar=False,
            )

            # Convert to list for JSON serialization
            embedding: list[float] = embedding_array.tolist()

            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        This method processes texts in batches for optimal throughput. Batch processing
        is significantly faster than processing texts individually.

        Performance:
            - CPU: >500 texts/second with batch_size=32
            - GPU: >2000 texts/second with batch_size=128

        Args:
            texts: List of input texts to embed. Empty strings will raise an error.
            batch_size: Number of texts to process at once. If None, uses
                DEFAULT_BATCH_SIZE (32 for CPU, 128 for GPU).
            show_progress: Whether to display a progress bar

        Returns:
            List of embeddings, where each embedding is a list of 384 floats.
            Order matches input texts.

        Raises:
            ValueError: If texts is empty or contains invalid entries
            RuntimeError: If batch processing fails

        Example:
            >>> service = EmbeddingService.get_instance()
            >>> texts = ["First text", "Second text", "Third text"]
            >>> embeddings = service.embed_batch(texts)
            >>> len(embeddings)
            3
            >>> all(len(emb) == 384 for emb in embeddings)
            True
        """
        if not texts:
            raise ValueError("texts list cannot be empty")

        if not all(isinstance(t, str) and t for t in texts):
            raise ValueError("All texts must be non-empty strings")

        # Ensure model is loaded
        self._load_model()

        # Determine optimal batch size
        if batch_size is None:
            # Use larger batches for GPU
            batch_size = 128 if self._device in ["cuda", "mps"] else self.DEFAULT_BATCH_SIZE

        try:
            logger.info(
                f"Processing {len(texts)} texts with batch_size={batch_size} "
                f"on device={self._device}"
            )

            # Generate embeddings (returns numpy array)
            assert self._model is not None, "Model must be loaded"
            embeddings_array = self._model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_tensor=False,
                show_progress_bar=show_progress,
            )

            # Convert to list of lists for JSON serialization
            embeddings: list[list[float]] = embeddings_array.tolist()

            logger.info(f"Successfully generated {len(embeddings)} embeddings")

            # Memory cleanup for large batches
            if len(texts) > 1000:
                self._cleanup_memory()

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise RuntimeError(f"Failed to generate batch embeddings: {e}") from e

    def _cleanup_memory(self) -> None:
        """Clean up GPU/CPU memory after processing large batches.

        This method is called automatically after processing large batches (>1000 texts)
        to prevent memory accumulation.
        """
        gc.collect()

        if self._device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("Cleared CUDA cache")
        elif self._device == "mps" and hasattr(torch, "mps"):
            # MPS doesn't have explicit cache clearing yet
            logger.debug("Memory cleanup requested (MPS)")

    def get_device(self) -> str:
        """Get the current device being used.

        Returns:
            Device string: "cuda", "mps", or "cpu"

        Note:
            This will trigger model loading if not already loaded.
        """
        self._load_model()
        return self._device  # type: ignore

    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings produced by this model.

        Returns:
            Number of dimensions (384 for all-MiniLM-L6-v2)
        """
        return self.EMBEDDING_DIMENSION

    def is_loaded(self) -> bool:
        """Check if the model is currently loaded in memory.

        Returns:
            True if model is loaded, False otherwise
        """
        return self._model is not None


# Convenience function for quick access
def get_embedding_service() -> EmbeddingService:
    """Get the singleton EmbeddingService instance.

    This is a convenience function that wraps EmbeddingService.get_instance().

    Returns:
        The singleton EmbeddingService instance

    Example:
        >>> service = get_embedding_service()
        >>> embedding = service.embed_text("Hello world")
    """
    return EmbeddingService.get_instance()
