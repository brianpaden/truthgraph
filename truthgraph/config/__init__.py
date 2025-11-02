"""Configuration package for TruthGraph."""

from .embedding_config import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    MODEL_DIMENSIONS,
    EmbeddingModel,
)

__all__ = [
    "EmbeddingModel",
    "DEFAULT_EMBEDDING_MODEL",
    "MODEL_DIMENSIONS",
    "DEFAULT_EMBEDDING_DIMENSION",
]
