"""Centralized embedding configuration.

This module defines the embedding models supported by TruthGraph and their
corresponding vector dimensions. All services and tests should import from
this module to ensure consistency across the codebase.

To switch embedding models:
1. Change DEFAULT_EMBEDDING_MODEL to the desired model
2. Update .env file with corresponding VECTOR_DIMENSION (optional)
3. Ensure database migration supports the dimension (Vector type is flexible)
4. Re-embed existing data if needed (requires migration script)

Example:
    >>> from truthgraph.config import DEFAULT_EMBEDDING_DIMENSION
    >>> service = VectorSearchService(embedding_dimension=DEFAULT_EMBEDDING_DIMENSION)
"""

from enum import Enum


class EmbeddingModel(Enum):
    """Supported embedding models with their identifiers.

    Each model has a specific dimensionality that must match the
    embedding vectors stored in the database.
    """

    MINILM = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_SMALL = "text-embedding-3-small"


# Current model in use
# NOTE: Changing this requires re-embedding existing data
DEFAULT_EMBEDDING_MODEL = EmbeddingModel.MINILM

# Model dimensions mapping
MODEL_DIMENSIONS = {
    EmbeddingModel.MINILM: 384,
    EmbeddingModel.OPENAI_SMALL: 1536,
}

# Default dimension based on current model
# This is the single source of truth for embedding dimensions
DEFAULT_EMBEDDING_DIMENSION = MODEL_DIMENSIONS[DEFAULT_EMBEDDING_MODEL]
