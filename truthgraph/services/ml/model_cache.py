"""Centralized model cache for ML services.

This module provides a unified caching system for all ML models used in TruthGraph.
It handles model lifecycle, memory optimization, and provides a single point of
control for model loading and unloading.

Key features:
    - Singleton pattern for model instances
    - Lazy loading with automatic device detection
    - Memory management and cleanup
    - GPU/CPU resource monitoring
    - Thread-safe model access
    - Model warmup for predictable latency

Performance targets:
    - Model load time: <5s on first load, ~0ms on cache hit
    - Memory usage: <4GB total for all models
    - GPU utilization: >80% when available
    - Zero model reload overhead during inference

Example:
    >>> from truthgraph.services.ml.model_cache import ModelCache
    >>> cache = ModelCache.get_instance()
    >>> embedding_service = cache.get_embedding_service()
    >>> nli_service = cache.get_nli_service()
    >>> cache.warmup_all_models()  # Pre-load all models
    >>> stats = cache.get_cache_stats()
    >>> print(f"Total memory: {stats['total_memory_mb']:.1f} MB")
"""

import gc
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, ClassVar

import torch

logger = logging.getLogger(__name__)


@dataclass
class ModelStats:
    """Statistics for a cached model.

    Attributes:
        model_name: Name/identifier of the model
        loaded: Whether model is currently loaded
        load_time_ms: Time taken to load model (milliseconds)
        memory_mb: Memory used by model (megabytes)
        device: Device model is loaded on (cuda/mps/cpu)
        last_access: Timestamp of last access
        access_count: Number of times model has been accessed
    """

    model_name: str
    loaded: bool
    load_time_ms: float
    memory_mb: float
    device: str
    last_access: float
    access_count: int


class ModelCache:
    """Centralized cache for all ML models.

    This class implements the singleton pattern and provides unified access
    to all ML models used in TruthGraph. It handles:
    - Lazy loading of models
    - Memory management and cleanup
    - Device detection and GPU utilization
    - Model lifecycle tracking

    Thread Safety:
        This implementation uses locks to ensure thread-safe model access.
        Multiple threads can safely get model instances.

    Attributes:
        _instance: Singleton instance
        _embedding_service: Cached embedding service instance
        _nli_service: Cached NLI service instance
        _lock: Threading lock for thread-safe operations
        _stats: Dictionary of model statistics
    """

    _instance: ClassVar["ModelCache | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize the model cache.

        This should not be called directly. Use get_instance() instead.

        Raises:
            RuntimeError: If called more than once (singleton violation)
        """
        if ModelCache._instance is not None:
            raise RuntimeError("ModelCache is a singleton. Use get_instance() instead.")

        self._embedding_service: Any = None
        self._nli_service: Any = None
        self._instance_lock = threading.Lock()
        self._stats: dict[str, ModelStats] = {}

        logger.info("ModelCache initialized")

    @classmethod
    def get_instance(cls) -> "ModelCache":
        """Get or create the singleton ModelCache instance.

        This method is thread-safe and ensures only one instance exists.

        Returns:
            The singleton ModelCache instance

        Example:
            >>> cache = ModelCache.get_instance()
            >>> cache2 = ModelCache.get_instance()
            >>> cache is cache2
            True
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    logger.info("Created new ModelCache singleton instance")
        return cls._instance

    def get_embedding_service(self) -> Any:
        """Get the cached EmbeddingService instance.

        This method returns the singleton embedding service, loading it
        lazily on first access. The model is cached for subsequent calls.

        Returns:
            EmbeddingService instance

        Thread Safety:
            This method is thread-safe and can be called from multiple threads.

        Example:
            >>> cache = ModelCache.get_instance()
            >>> service = cache.get_embedding_service()
            >>> embedding = service.embed_text("Hello world")
        """
        if self._embedding_service is None:
            with self._instance_lock:
                if self._embedding_service is None:
                    logger.info("Loading EmbeddingService (first access)")
                    start_time = time.perf_counter()

                    # Import here to avoid circular imports
                    from truthgraph.services.ml.embedding_service import (
                        EmbeddingService,
                    )

                    self._embedding_service = EmbeddingService.get_instance()

                    # Warm up the model
                    self._embedding_service.embed_text("warmup")

                    load_time = (time.perf_counter() - start_time) * 1000

                    # Record stats
                    self._stats["embedding"] = ModelStats(
                        model_name="sentence-transformers/all-mpnet-base-v2",
                        loaded=True,
                        load_time_ms=load_time,
                        memory_mb=self._estimate_model_memory(),
                        device=self._embedding_service.get_device(),
                        last_access=time.time(),
                        access_count=1,
                    )

                    logger.info(
                        f"EmbeddingService loaded in {load_time:.1f}ms "
                        f"on {self._embedding_service.get_device()}"
                    )
        else:
            # Update access stats
            if "embedding" in self._stats:
                self._stats["embedding"].last_access = time.time()
                self._stats["embedding"].access_count += 1

        return self._embedding_service

    def get_nli_service(self) -> Any:
        """Get the cached NLI service instance.

        This method returns the singleton NLI service, loading it
        lazily on first access. The model is cached for subsequent calls.

        Returns:
            NLIService instance

        Thread Safety:
            This method is thread-safe and can be called from multiple threads.

        Example:
            >>> cache = ModelCache.get_instance()
            >>> service = cache.get_nli_service()
            >>> result = service.verify_single("premise", "hypothesis")
        """
        if self._nli_service is None:
            with self._instance_lock:
                if self._nli_service is None:
                    logger.info("Loading NLI service (first access)")
                    start_time = time.perf_counter()

                    # Import here to avoid circular imports
                    from truthgraph.services.ml.nli_service import get_nli_service

                    self._nli_service = get_nli_service()

                    # Warm up the model
                    self._nli_service.verify_single("warmup premise", "warmup hypothesis")

                    load_time = (time.perf_counter() - start_time) * 1000

                    # Record stats
                    model_info = self._nli_service.get_model_info()
                    self._stats["nli"] = ModelStats(
                        model_name=str(model_info["model_name"]),
                        loaded=True,
                        load_time_ms=load_time,
                        memory_mb=self._estimate_model_memory(),
                        device=str(model_info["device"]),
                        last_access=time.time(),
                        access_count=1,
                    )

                    logger.info(
                        f"NLI service loaded in {load_time:.1f}ms on {model_info['device']}"
                    )
        else:
            # Update access stats
            if "nli" in self._stats:
                self._stats["nli"].last_access = time.time()
                self._stats["nli"].access_count += 1

        return self._nli_service

    def warmup_all_models(self) -> dict[str, float]:
        """Pre-load and warmup all models.

        This method loads all models into memory and runs warmup inferences
        to ensure predictable latency on first real request.

        Returns:
            Dictionary mapping model name to load time (ms)

        Example:
            >>> cache = ModelCache.get_instance()
            >>> load_times = cache.warmup_all_models()
            >>> print(f"Total warmup time: {sum(load_times.values()):.1f}ms")
        """
        logger.info("Warming up all models...")
        load_times = {}

        # Warmup embedding service
        start = time.perf_counter()
        self.get_embedding_service()
        load_times["embedding"] = (time.perf_counter() - start) * 1000

        # Warmup NLI service
        start = time.perf_counter()
        self.get_nli_service()
        load_times["nli"] = (time.perf_counter() - start) * 1000

        total_time = sum(load_times.values())
        logger.info(f"All models warmed up in {total_time:.1f}ms")

        return load_times

    def cleanup_memory(self) -> None:
        """Clean up GPU/CPU memory.

        This method triggers garbage collection and clears GPU caches
        to free up memory. Useful after processing large batches.

        Example:
            >>> cache = ModelCache.get_instance()
            >>> # ... process large batch ...
            >>> cache.cleanup_memory()
        """
        logger.info("Running memory cleanup...")

        # Run garbage collection
        gc.collect()

        # Clear GPU cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleared CUDA cache")

        # MPS cleanup (Apple Silicon)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # MPS doesn't have explicit cache clearing yet
            logger.info("Triggered GC for MPS")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns statistics about all cached models including memory usage,
        load times, access patterns, and device information.

        Returns:
            Dictionary with cache statistics:
                - models_loaded: Number of models currently loaded
                - total_memory_mb: Total memory used by all models
                - device_info: Information about compute devices
                - model_stats: Per-model statistics
                - system_info: System-level resource information

        Example:
            >>> cache = ModelCache.get_instance()
            >>> stats = cache.get_cache_stats()
            >>> print(f"Models loaded: {stats['models_loaded']}")
            >>> print(f"Total memory: {stats['total_memory_mb']:.1f} MB")
        """
        # Collect model stats
        models_loaded = sum(1 for s in self._stats.values() if s.loaded)
        total_memory = sum(s.memory_mb for s in self._stats.values() if s.loaded)

        # Device info
        device_info = {
            "cuda_available": torch.cuda.is_available(),
            "mps_available": (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()),
        }

        if torch.cuda.is_available():
            device_info["cuda_device"] = torch.cuda.get_device_name(0)
            device_info["cuda_memory_allocated_mb"] = torch.cuda.memory_allocated() / 1024 / 1024
            device_info["cuda_memory_reserved_mb"] = torch.cuda.memory_reserved() / 1024 / 1024

        # System info
        system_info = {}
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            system_info["process_memory_rss_mb"] = memory_info.rss / 1024 / 1024
            system_info["process_memory_vms_mb"] = memory_info.vms / 1024 / 1024
        except ImportError:
            system_info["psutil_available"] = False

        return {
            "models_loaded": models_loaded,
            "total_memory_mb": total_memory,
            "device_info": device_info,
            "model_stats": {
                name: {
                    "model_name": stats.model_name,
                    "loaded": stats.loaded,
                    "load_time_ms": stats.load_time_ms,
                    "memory_mb": stats.memory_mb,
                    "device": stats.device,
                    "access_count": stats.access_count,
                }
                for name, stats in self._stats.items()
            },
            "system_info": system_info,
        }

    def _estimate_model_memory(self) -> float:
        """Estimate memory used by models.

        Returns:
            Estimated memory usage in MB
        """
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback: estimate based on GPU memory if available
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1024 / 1024
            return 0.0

    def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model is loaded.

        Args:
            model_name: Name of the model ('embedding' or 'nli')

        Returns:
            True if model is loaded, False otherwise

        Example:
            >>> cache = ModelCache.get_instance()
            >>> if not cache.is_model_loaded('embedding'):
            ...     cache.get_embedding_service()
        """
        return model_name in self._stats and self._stats[model_name].loaded

    def get_optimal_batch_size(self, model_name: str) -> int:
        """Get optimal batch size for a model based on device.

        Args:
            model_name: Name of the model ('embedding' or 'nli')

        Returns:
            Recommended batch size

        Example:
            >>> cache = ModelCache.get_instance()
            >>> batch_size = cache.get_optimal_batch_size('embedding')
            >>> embeddings = service.embed_batch(texts, batch_size=batch_size)
        """
        if model_name not in self._stats:
            # Default values if model not loaded yet
            return 32 if model_name == "embedding" else 8

        device = self._stats[model_name].device

        if model_name == "embedding":
            # Embedding service batch sizes
            if device == "cuda":
                return 128
            elif device == "mps":
                return 64
            else:  # CPU
                return 32
        elif model_name == "nli":
            # NLI service batch sizes
            if device == "cuda":
                return 16
            elif device == "mps":
                return 12
            else:  # CPU
                return 8
        else:
            return 32  # Default


# Convenience function for quick access
def get_model_cache() -> ModelCache:
    """Get the singleton ModelCache instance.

    This is a convenience function that wraps ModelCache.get_instance().

    Returns:
        The singleton ModelCache instance

    Example:
        >>> from truthgraph.services.ml.model_cache import get_model_cache
        >>> cache = get_model_cache()
        >>> embedding_service = cache.get_embedding_service()
    """
    return ModelCache.get_instance()
