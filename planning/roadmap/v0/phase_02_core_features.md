# Phase 2: Core Features (Weeks 3-5)

## Overview and Goals

Phase 2 brings TruthGraph v0 to life by adding the core ML/NLP functionality that enables end-to-end claim verification. Building on the foundation established in Phase 1, this phase implements embedding generation, semantic search, NLI-based verification, and verdict aggregation.

**Timeline**: Weeks 3-5 (60-80 engineering hours)

**Primary Objectives**:
1. Implement embedding generation pipeline with sentence-transformers
2. Enable semantic search with pgvector integration
3. Build NLI-based verification with DeBERTa-v3
4. Create verdict aggregation logic
5. Achieve end-to-end claim verification in under 60 seconds

**Success Criteria**:
- Submit claim via API → receive verdict within 60 seconds
- Embedding model loads and caches correctly
- Evidence retrieval returns semantically relevant results
- Verdicts align with human judgment (70%+ accuracy on test claims)
- System handles 100+ claims without performance degradation
- Complete ML pipeline uses <4GB RAM on CPU

---

## 1. Embedding Generation

### Model Selection: sentence-transformers/all-MiniLM-L6-v2

**Why This Model?**

- **Dimension**: 384 (compact, fast)
- **Speed**: ~1000 sentences/second on CPU
- **Quality**: Strong balance between speed and semantic accuracy
- **Size**: ~80MB model file
- **Training**: Fine-tuned on 1B+ sentence pairs
- **Performance**: Mean Pooling + normalization for cosine similarity

**Comparison with Alternatives**:

| Model | Dimensions | Speed (CPU) | Quality | Size |
|-------|------------|-------------|---------|------|
| all-MiniLM-L6-v2 | 384 | ~1000/s | Good | 80MB |
| all-mpnet-base-v2 | 768 | ~400/s | Better | 420MB |
| Contriever | 768 | ~500/s | Better | 440MB |
| all-MiniLM-L12-v2 | 384 | ~600/s | Better | 120MB |

**Verdict**: all-MiniLM-L6-v2 is the best choice for v0 MVP due to its speed and small footprint, enabling CPU-only deployment.

---

### Loading and Caching Models

Modern Python best practices for model management:

**File**: `truthgraph/ml/embeddings.py`

```python
"""
Embedding generation service using sentence-transformers.

This module provides efficient embedding generation with automatic model
caching, batch processing, and memory-optimized inference.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Type aliases for clarity
Embedding = list[float]
EmbeddingBatch = list[Embedding]


class EmbeddingService:
    """
    Manages embedding generation with automatic model caching.

    Features:
    - Lazy loading on first use
    - Automatic GPU detection and fallback to CPU
    - Batch processing for efficiency
    - Thread-safe model caching
    """

    _instance: EmbeddingService | None = None
    _model: SentenceTransformer | None = None

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir: Path | str | None = None,
        device: str | None = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Hugging Face model identifier
            cache_dir: Directory for model cache (default: ~/.cache/huggingface)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.device = device or self._detect_device()

    @staticmethod
    def _detect_device() -> str:
        """Detect best available device."""
        if torch.cuda.is_available():
            logger.info("GPU detected, using CUDA")
            return "cuda"
        elif torch.backends.mps.is_available():
            logger.info("Apple Silicon detected, using MPS")
            return "mps"
        else:
            logger.info("No GPU detected, using CPU")
            return "cpu"

    def _load_model(self) -> SentenceTransformer:
        """
        Load model with caching.

        Returns:
            Loaded SentenceTransformer model
        """
        if self._model is None:
            logger.info(
                f"Loading embedding model: {self.model_name} on {self.device}"
            )

            # Load model with cache directory
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(self.cache_dir) if self.cache_dir else None,
                device=self.device,
            )

            # Set model to evaluation mode
            self._model.eval()

            logger.info(
                f"Model loaded successfully. Dimension: {self._model.get_sentence_embedding_dimension()}"
            )

        return self._model

    @property
    def model(self) -> SentenceTransformer:
        """Get model instance (lazy loading)."""
        return self._load_model()

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> Embedding:
        """
        Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector (384 dimensions)

        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.embed_text("The Earth is round")
            >>> len(embedding)
            384
        """
        # Use batch method for consistency
        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> EmbeddingBatch:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts
            batch_size: Batch size for inference (32 is optimal for CPU)
            show_progress: Show progress bar
            normalize: L2-normalize embeddings for cosine similarity

        Returns:
            List of embedding vectors

        Example:
            >>> service = EmbeddingService()
            >>> texts = ["The Earth is round", "The sky is blue"]
            >>> embeddings = service.embed_batch(texts)
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            384
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")

        # Generate embeddings with batching
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )

        # Convert to list for JSON serialization
        return embeddings.tolist()

    @classmethod
    def get_instance(cls, **kwargs) -> EmbeddingService:
        """
        Get singleton instance (recommended for production).

        This ensures only one model is loaded in memory.

        Args:
            **kwargs: Arguments for EmbeddingService constructor

        Returns:
            Singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance


# Module-level convenience function
def get_embedding_service() -> EmbeddingService:
    """
    Get global embedding service instance.

    This is the recommended way to access embeddings in the application.
    """
    return EmbeddingService.get_instance()
```

---

### Generate Embedding for Claim

**Example Usage**:

```python
from truthgraph.ml.embeddings import get_embedding_service

# Get service instance (loads model on first call)
embedding_service = get_embedding_service()

# Generate embedding for a claim
claim_text = "The Earth is round and orbits the Sun"
claim_embedding = embedding_service.embed_text(claim_text)

print(f"Embedding dimension: {len(claim_embedding)}")
# Output: Embedding dimension: 384

print(f"First 5 values: {claim_embedding[:5]}")
# Output: First 5 values: [0.023, -0.154, 0.089, -0.045, 0.112]
```

---

### Batch Embed Evidence Corpus

For efficient corpus embedding:

**File**: `scripts/embed_corpus.py`

```python
"""
Batch embed evidence corpus and store in database.

Usage:
    python -m scripts.embed_corpus --input data/corpus.csv --batch-size 128
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

import pandas as pd
from tqdm import tqdm

from truthgraph.db import get_db
from truthgraph.ml.embeddings import get_embedding_service
from truthgraph.models import Evidence

logger = logging.getLogger(__name__)


async def load_evidence_corpus(file_path: Path) -> list[Evidence]:
    """
    Load evidence corpus from CSV/Parquet file.

    Expected columns: id, content, source_url, source_type
    """
    if file_path.suffix == ".csv":
        df = pd.read_csv(file_path)
    elif file_path.suffix == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    logger.info(f"Loaded {len(df)} evidence items from {file_path}")

    # Convert to Evidence objects
    evidence_list = []
    for _, row in df.iterrows():
        evidence = Evidence(
            id=row.get("id"),
            content=row["content"],
            source_url=row.get("source_url"),
            source_type=row.get("source_type", "document"),
        )
        evidence_list.append(evidence)

    return evidence_list


async def embed_and_store_batch(
    evidence_batch: list[Evidence],
    embedding_service: EmbeddingService,
    db_session,
) -> int:
    """
    Embed a batch of evidence and store in database.

    Returns:
        Number of embeddings stored
    """
    # Extract texts
    texts = [e.content for e in evidence_batch]

    # Generate embeddings
    embeddings = embedding_service.embed_batch(
        texts,
        batch_size=32,
        show_progress=False,
    )

    # Store in database
    count = 0
    for evidence, embedding in zip(evidence_batch, embeddings):
        await db_session.execute(
            """
            INSERT INTO evidence_embeddings (evidence_id, embedding, tenant_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (evidence_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """,
            evidence.id,
            embedding,
            "default",
        )
        count += 1

    await db_session.commit()
    return count


async def embed_corpus(
    corpus_path: Path,
    batch_size: int = 128,
) -> None:
    """
    Main function to embed entire corpus.

    Args:
        corpus_path: Path to corpus file
        batch_size: Number of items to process per batch
    """
    # Load corpus
    evidence_list = await load_evidence_corpus(corpus_path)

    # Get services
    embedding_service = get_embedding_service()
    db = await get_db()

    # Process in batches with progress bar
    total_embedded = 0
    pbar = tqdm(total=len(evidence_list), desc="Embedding corpus")

    for i in range(0, len(evidence_list), batch_size):
        batch = evidence_list[i:i + batch_size]

        try:
            count = await embed_and_store_batch(batch, embedding_service, db)
            total_embedded += count
            pbar.update(len(batch))

        except Exception as e:
            logger.error(f"Failed to embed batch {i//batch_size}: {e}")
            continue

    pbar.close()
    logger.info(f"Successfully embedded {total_embedded} evidence items")


def main():
    parser = argparse.ArgumentParser(description="Embed evidence corpus")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input corpus file (CSV or Parquet)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Batch size for embedding (default: 128)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run async function
    asyncio.run(embed_corpus(args.input, args.batch_size))


if __name__ == "__main__":
    main()
```

**Running the script**:

```bash
# Embed corpus from CSV
python -m scripts.embed_corpus --input data/evidence_corpus.csv --batch-size 128

# Embed corpus from Parquet (faster for large datasets)
python -m scripts.embed_corpus --input data/evidence_corpus.parquet --batch-size 256
```

---

### Store Embeddings in pgvector

**Database Schema** (already created in Phase 1):

```sql
CREATE TABLE evidence_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    evidence_id UUID REFERENCES evidence(id) ON DELETE CASCADE,
    embedding VECTOR(384),  -- all-MiniLM-L6-v2 dimension
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for tenant-scoped vector search
CREATE INDEX idx_embeddings_tenant_vector ON evidence_embeddings(tenant_id) INCLUDE (embedding);
CREATE INDEX idx_embeddings_vector_similarity ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops);
```

**Storing embeddings**:

```python
import asyncpg
from typing import List

async def store_embedding(
    db_pool: asyncpg.Pool,
    evidence_id: str,
    embedding: List[float],
    tenant_id: str = "default",
) -> None:
    """
    Store embedding in pgvector.

    Args:
        db_pool: Database connection pool
        evidence_id: UUID of evidence item
        embedding: 384-dimensional embedding vector
        tenant_id: Tenant identifier (default for v0)
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO evidence_embeddings (evidence_id, embedding, tenant_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (evidence_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """,
            evidence_id,
            embedding,
            tenant_id,
        )
```

---

### Performance Optimization

**Memory Management**:

```python
import gc
import torch

def optimize_memory():
    """Clear unused memory between batches."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Use in batch processing
for batch in batches:
    embeddings = embed_batch(batch)
    store_embeddings(embeddings)
    optimize_memory()  # Clear memory after each batch
```

**Batch Size Tuning**:

| Hardware | Batch Size | Throughput |
|----------|------------|------------|
| CPU (8 cores) | 32 | ~1000 texts/s |
| CPU (16 cores) | 64 | ~1800 texts/s |
| GPU (RTX 3060) | 128 | ~5000 texts/s |
| GPU (RTX 4090) | 256 | ~12000 texts/s |

**Recommendation**: Start with batch_size=32 for CPU, increase to 128+ if GPU is available.

---

## 2. Semantic Search with pgvector

### Vector Similarity Search (Cosine Distance)

**Core Search Function**:

**File**: `truthgraph/retrieval/vector_search.py`

```python
"""
Vector similarity search using pgvector.

Implements efficient semantic search with tenant isolation and result ranking.
"""

from __future__ import annotations

import logging
from typing import NamedTuple
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class SearchResult(NamedTuple):
    """Search result with similarity score."""
    evidence_id: UUID
    content: str
    source_url: str | None
    similarity: float  # Cosine similarity (0-1, higher is better)


async def search_similar_evidence(
    db_pool: asyncpg.Pool,
    query_embedding: list[float],
    tenant_id: str = "default",
    limit: int = 10,
    min_similarity: float = 0.3,
) -> list[SearchResult]:
    """
    Find evidence similar to query embedding.

    Uses cosine distance operator (<->) from pgvector.
    Lower distance = higher similarity.

    Args:
        db_pool: Database connection pool
        query_embedding: Query embedding vector (384 dims)
        tenant_id: Tenant identifier
        limit: Maximum number of results
        min_similarity: Minimum cosine similarity (0-1)

    Returns:
        List of search results ordered by similarity (descending)

    Example:
        >>> results = await search_similar_evidence(
        ...     db_pool,
        ...     claim_embedding,
        ...     limit=10,
        ... )
        >>> for result in results:
        ...     print(f"{result.similarity:.3f}: {result.content[:100]}")
    """
    # Convert similarity threshold to distance threshold
    # distance = 1 - similarity (for cosine)
    max_distance = 1.0 - min_similarity

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                e.id AS evidence_id,
                e.content,
                e.source_url,
                1 - (ee.embedding <-> $1::vector) AS similarity
            FROM evidence e
            JOIN evidence_embeddings ee ON e.id = ee.evidence_id
            WHERE
                ee.tenant_id = $2
                AND e.tenant_id = $2
                AND (ee.embedding <-> $1::vector) < $3
            ORDER BY ee.embedding <-> $1::vector ASC
            LIMIT $4
            """,
            query_embedding,
            tenant_id,
            max_distance,
            limit,
        )

    results = [
        SearchResult(
            evidence_id=row["evidence_id"],
            content=row["content"],
            source_url=row["source_url"],
            similarity=row["similarity"],
        )
        for row in rows
    ]

    logger.info(
        f"Vector search returned {len(results)} results "
        f"(min_similarity={min_similarity})"
    )

    return results


async def search_similar_evidence_batch(
    db_pool: asyncpg.Pool,
    query_embeddings: list[list[float]],
    tenant_id: str = "default",
    limit_per_query: int = 10,
) -> list[list[SearchResult]]:
    """
    Batch search for multiple queries.

    More efficient than calling search_similar_evidence multiple times.

    Args:
        db_pool: Database connection pool
        query_embeddings: List of query embeddings
        tenant_id: Tenant identifier
        limit_per_query: Max results per query

    Returns:
        List of result lists (one per query)
    """
    results = []

    for embedding in query_embeddings:
        result = await search_similar_evidence(
            db_pool,
            embedding,
            tenant_id=tenant_id,
            limit=limit_per_query,
        )
        results.append(result)

    return results
```

---

### Hybrid Search (FTS + Vector)

Combine full-text search and vector search for best results:

**File**: `truthgraph/retrieval/hybrid_search.py`

```python
"""
Hybrid search combining full-text search and vector similarity.

This approach leverages both lexical matching (FTS) and semantic matching (vectors)
to achieve better retrieval quality than either method alone.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

import asyncpg

from truthgraph.ml.embeddings import get_embedding_service
from truthgraph.retrieval.vector_search import SearchResult, search_similar_evidence

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Hybrid search result with combined score."""
    evidence_id: UUID
    content: str
    source_url: str | None
    fts_score: float  # PostgreSQL ts_rank score
    vector_score: float  # Cosine similarity
    combined_score: float  # Weighted combination


async def full_text_search(
    db_pool: asyncpg.Pool,
    query: str,
    tenant_id: str = "default",
    limit: int = 10,
) -> list[SearchResult]:
    """
    Full-text search using PostgreSQL FTS.

    Args:
        db_pool: Database connection pool
        query: Search query text
        tenant_id: Tenant identifier
        limit: Maximum results

    Returns:
        List of results with FTS rank scores
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id AS evidence_id,
                content,
                source_url,
                ts_rank(
                    to_tsvector('english', content),
                    plainto_tsquery('english', $1)
                ) AS similarity
            FROM evidence
            WHERE
                tenant_id = $2
                AND to_tsvector('english', content) @@ plainto_tsquery('english', $1)
            ORDER BY similarity DESC
            LIMIT $3
            """,
            query,
            tenant_id,
            limit,
        )

    return [
        SearchResult(
            evidence_id=row["evidence_id"],
            content=row["content"],
            source_url=row["source_url"],
            similarity=row["similarity"],
        )
        for row in rows
    ]


async def hybrid_search(
    db_pool: asyncpg.Pool,
    query_text: str,
    tenant_id: str = "default",
    limit: int = 10,
    fts_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> list[HybridSearchResult]:
    """
    Hybrid search combining FTS and vector similarity.

    Strategy:
    1. Run FTS and vector search in parallel
    2. Merge results and deduplicate
    3. Combine scores with configurable weights
    4. Re-rank by combined score

    Args:
        db_pool: Database connection pool
        query_text: Search query
        tenant_id: Tenant identifier
        limit: Maximum results to return
        fts_weight: Weight for FTS score (0-1)
        vector_weight: Weight for vector score (0-1)

    Returns:
        List of hybrid search results ordered by combined score

    Example:
        >>> results = await hybrid_search(
        ...     db_pool,
        ...     "The Earth orbits the Sun",
        ...     limit=10,
        ... )
        >>> for result in results:
        ...     print(f"{result.combined_score:.3f}: {result.content[:80]}")
    """
    # Generate embedding for vector search
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.embed_text(query_text)

    # Run searches in parallel
    fts_task = full_text_search(db_pool, query_text, tenant_id, limit * 2)
    vector_task = search_similar_evidence(
        db_pool,
        query_embedding,
        tenant_id,
        limit * 2,
    )

    fts_results, vector_results = await asyncio.gather(fts_task, vector_task)

    # Merge results by evidence_id
    evidence_scores: dict[UUID, dict] = {}

    # Add FTS results
    for result in fts_results:
        evidence_scores[result.evidence_id] = {
            "content": result.content,
            "source_url": result.source_url,
            "fts_score": result.similarity,
            "vector_score": 0.0,
        }

    # Add vector results (merge if already exists)
    for result in vector_results:
        if result.evidence_id in evidence_scores:
            evidence_scores[result.evidence_id]["vector_score"] = result.similarity
        else:
            evidence_scores[result.evidence_id] = {
                "content": result.content,
                "source_url": result.source_url,
                "fts_score": 0.0,
                "vector_score": result.similarity,
            }

    # Normalize and combine scores
    hybrid_results = []

    for evidence_id, scores in evidence_scores.items():
        # Normalize FTS score (ts_rank can be 0-1)
        fts_normalized = min(scores["fts_score"], 1.0)

        # Vector score already normalized (0-1)
        vector_normalized = scores["vector_score"]

        # Combined score (weighted sum)
        combined_score = (
            fts_weight * fts_normalized +
            vector_weight * vector_normalized
        )

        hybrid_results.append(
            HybridSearchResult(
                evidence_id=evidence_id,
                content=scores["content"],
                source_url=scores["source_url"],
                fts_score=fts_normalized,
                vector_score=vector_normalized,
                combined_score=combined_score,
            )
        )

    # Sort by combined score (descending)
    hybrid_results.sort(key=lambda x: x.combined_score, reverse=True)

    # Return top-k results
    top_results = hybrid_results[:limit]

    logger.info(
        f"Hybrid search returned {len(top_results)} results "
        f"(FTS: {len(fts_results)}, Vector: {len(vector_results)})"
    )

    return top_results
```

---

### Query Optimization

**Index Tuning**:

```sql
-- For pgvector, IVFFlat index provides ~3x speedup with minor accuracy trade-off
-- Recommended when corpus exceeds 10,000 items

-- Create IVFFlat index (use 100-500 lists depending on corpus size)
CREATE INDEX idx_embeddings_ivfflat ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- For better accuracy with larger corpus
DROP INDEX idx_embeddings_ivfflat;
CREATE INDEX idx_embeddings_ivfflat ON evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 500);

-- Analyze table for query planner
ANALYZE evidence_embeddings;
```

**Query Tuning**:

```python
# Enable query plan analysis
async with db_pool.acquire() as conn:
    await conn.execute("SET enable_seqscan = OFF")  # Force index usage
```

---

### Top-K Retrieval

```python
async def retrieve_evidence_for_claim(
    db_pool: asyncpg.Pool,
    claim_text: str,
    tenant_id: str = "default",
    k: int = 10,
) -> list[HybridSearchResult]:
    """
    Main retrieval function for claim verification.

    This is the entry point used by the verification pipeline.

    Args:
        db_pool: Database connection pool
        claim_text: Claim to find evidence for
        tenant_id: Tenant identifier
        k: Number of evidence items to retrieve

    Returns:
        Top-k most relevant evidence items
    """
    return await hybrid_search(
        db_pool,
        claim_text,
        tenant_id=tenant_id,
        limit=k,
        fts_weight=0.3,
        vector_weight=0.7,
    )
```

---

## 3. NLI-Based Verification

### Model Selection: microsoft/deberta-v3-base (MNLI)

**Why DeBERTa-v3?**

DeBERTa-v3 (Decoding-enhanced BERT with disentangled attention) is the state-of-the-art NLI model as of 2024:

- **Architecture**: Improved attention mechanism over BERT/RoBERTa
- **Training**: Fine-tuned on MultiNLI (MNLI) dataset
- **Performance**: 90.9% accuracy on MNLI test set
- **Size**: ~440MB model file
- **Speed**: ~350ms per inference on CPU

**Comparison with Alternatives**:

| Model | MNLI Accuracy | Speed (CPU) | Size |
|-------|---------------|-------------|------|
| DeBERTa-v3-base | 90.9% | ~350ms | 440MB |
| RoBERTa-large | 90.2% | ~500ms | 1.4GB |
| BART-large-MNLI | 89.4% | ~450ms | 1.6GB |
| DeBERTa-v2-xlarge | 91.7% | ~1200ms | 1.5GB |

**Verdict**: DeBERTa-v3-base offers the best balance of accuracy and speed for CPU deployment.

---

### Premise (Evidence) + Hypothesis (Claim) Format

**NLI Task Definition**:

Given:
- **Premise**: A piece of evidence (assumed to be true)
- **Hypothesis**: A claim to verify

Predict one of three relationships:
- **ENTAILMENT**: Evidence supports the claim (premise implies hypothesis)
- **CONTRADICTION**: Evidence refutes the claim (premise contradicts hypothesis)
- **NEUTRAL**: Evidence is neither supportive nor contradictory

---

### Three-Class Output: ENTAILMENT, CONTRADICTION, NEUTRAL

**Output Format**:

```python
{
    "label": "ENTAILMENT",  # or "CONTRADICTION" or "NEUTRAL"
    "scores": {
        "ENTAILMENT": 0.87,
        "CONTRADICTION": 0.05,
        "NEUTRAL": 0.08
    }
}
```

---

### Implementation

**File**: `truthgraph/ml/verification.py`

```python
"""
NLI-based claim verification using DeBERTa-v3.

This module implements natural language inference (NLI) for fact-checking,
determining whether evidence supports, refutes, or is neutral to a claim.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class NLILabel(str, Enum):
    """NLI prediction labels."""
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"


@dataclass
class NLIResult:
    """Result of NLI inference."""
    label: NLILabel
    confidence: float  # Score for predicted label (0-1)
    scores: dict[NLILabel, float]  # All class scores


class NLIVerifier:
    """
    NLI-based verification service.

    Uses DeBERTa-v3-base fine-tuned on MNLI for three-class classification.
    """

    _instance: NLIVerifier | None = None
    _model: AutoModelForSequenceClassification | None = None
    _tokenizer: AutoTokenizer | None = None

    def __init__(
        self,
        model_name: str = "microsoft/deberta-v3-base",
        device: str | None = None,
    ):
        """
        Initialize NLI verifier.

        Args:
            model_name: Hugging Face model identifier
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name
        self.device = device or self._detect_device()

        # Label mapping (model-specific, check model card)
        self.label_map = {
            0: NLILabel.ENTAILMENT,
            1: NLILabel.NEUTRAL,
            2: NLILabel.CONTRADICTION,
        }

    @staticmethod
    def _detect_device() -> str:
        """Detect best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _load_model(self) -> tuple[AutoModelForSequenceClassification, AutoTokenizer]:
        """Load model and tokenizer with caching."""
        if self._model is None or self._tokenizer is None:
            logger.info(f"Loading NLI model: {self.model_name} on {self.device}")

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # Load model
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )
            self._model.to(self.device)
            self._model.eval()

            logger.info("NLI model loaded successfully")

        return self._model, self._tokenizer

    @property
    def model(self) -> AutoModelForSequenceClassification:
        """Get model instance (lazy loading)."""
        model, _ = self._load_model()
        return model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """Get tokenizer instance (lazy loading)."""
        _, tokenizer = self._load_model()
        return tokenizer

    def verify_single(
        self,
        premise: str,
        hypothesis: str,
    ) -> NLIResult:
        """
        Run NLI on a single premise-hypothesis pair.

        Args:
            premise: Evidence text (assumed true)
            hypothesis: Claim to verify

        Returns:
            NLI result with label and confidence scores

        Example:
            >>> verifier = NLIVerifier()
            >>> result = verifier.verify_single(
            ...     premise="The Earth orbits around the Sun.",
            ...     hypothesis="The Earth revolves around the Sun."
            ... )
            >>> result.label
            <NLILabel.ENTAILMENT: 'ENTAILMENT'>
            >>> result.confidence
            0.94
        """
        # Tokenize input (premise first, then hypothesis)
        inputs = self.tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits

        # Get probabilities
        probs = torch.softmax(logits, dim=1)[0]

        # Get predicted label
        predicted_idx = torch.argmax(probs).item()
        predicted_label = self.label_map[predicted_idx]
        confidence = probs[predicted_idx].item()

        # Build scores dict
        scores = {
            self.label_map[i]: probs[i].item()
            for i in range(len(probs))
        }

        return NLIResult(
            label=predicted_label,
            confidence=confidence,
            scores=scores,
        )

    def verify_batch(
        self,
        premise_hypothesis_pairs: list[tuple[str, str]],
        batch_size: int = 8,
    ) -> list[NLIResult]:
        """
        Run NLI on multiple premise-hypothesis pairs efficiently.

        Args:
            premise_hypothesis_pairs: List of (premise, hypothesis) tuples
            batch_size: Batch size for inference (8 is optimal for CPU)

        Returns:
            List of NLI results

        Example:
            >>> verifier = NLIVerifier()
            >>> pairs = [
            ...     ("The sky is blue.", "The sky has a blue color."),
            ...     ("The Earth is flat.", "The Earth is round."),
            ... ]
            >>> results = verifier.verify_batch(pairs)
            >>> len(results)
            2
        """
        results = []

        for i in range(0, len(premise_hypothesis_pairs), batch_size):
            batch = premise_hypothesis_pairs[i:i + batch_size]

            # Process batch
            premises, hypotheses = zip(*batch)

            # Tokenize batch
            inputs = self.tokenizer(
                list(premises),
                list(hypotheses),
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            # Get probabilities
            probs = torch.softmax(logits, dim=1)

            # Parse results
            for j in range(len(batch)):
                predicted_idx = torch.argmax(probs[j]).item()
                predicted_label = self.label_map[predicted_idx]
                confidence = probs[j][predicted_idx].item()

                scores = {
                    self.label_map[k]: probs[j][k].item()
                    for k in range(len(probs[j]))
                }

                results.append(
                    NLIResult(
                        label=predicted_label,
                        confidence=confidence,
                        scores=scores,
                    )
                )

        return results

    @classmethod
    def get_instance(cls, **kwargs) -> NLIVerifier:
        """Get singleton instance (recommended for production)."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance


# Module-level convenience function
def get_nli_verifier() -> NLIVerifier:
    """Get global NLI verifier instance."""
    return NLIVerifier.get_instance()
```

---

### Example Usage

```python
from truthgraph.ml.verification import get_nli_verifier, NLILabel

# Get verifier instance (loads model on first call)
verifier = get_nli_verifier()

# Example 1: Evidence supports claim
result = verifier.verify_single(
    premise="NASA confirms that the Earth orbits the Sun in approximately 365 days.",
    hypothesis="The Earth orbits the Sun."
)
print(f"Label: {result.label}")  # ENTAILMENT
print(f"Confidence: {result.confidence:.3f}")  # 0.94

# Example 2: Evidence refutes claim
result = verifier.verify_single(
    premise="Scientific consensus agrees that the Earth is an oblate spheroid.",
    hypothesis="The Earth is flat."
)
print(f"Label: {result.label}")  # CONTRADICTION
print(f"Confidence: {result.confidence:.3f}")  # 0.91

# Example 3: Evidence is neutral
result = verifier.verify_single(
    premise="The sky is blue due to Rayleigh scattering.",
    hypothesis="The Earth orbits the Sun."
)
print(f"Label: {result.label}")  # NEUTRAL
print(f"Confidence: {result.confidence:.3f}")  # 0.88
```

---

## 4. Verdict Aggregation

### Combining Multiple NLI Results

**File**: `truthgraph/verification/aggregation.py`

```python
"""
Verdict aggregation logic for combining multiple NLI results.

This module implements strategies for aggregating evidence-based verdicts
into a final claim verification result.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from truthgraph.ml.verification import NLILabel, NLIResult

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    """Final verdict labels."""
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class AggregatedVerdict:
    """Final aggregated verdict."""
    verdict: Verdict
    confidence: float  # Overall confidence (0-1)
    support_score: float  # Support evidence score
    refute_score: float  # Refutation evidence score
    neutral_score: float  # Neutral evidence score
    evidence_count: int  # Total evidence items
    reasoning: str  # Human-readable explanation


def aggregate_verdicts(
    nli_results: list[NLIResult],
    support_threshold: float = 0.6,
    refute_threshold: float = 0.6,
    confidence_weight: bool = True,
) -> AggregatedVerdict:
    """
    Aggregate multiple NLI results into a final verdict.

    Strategy:
    1. Calculate weighted scores for ENTAILMENT, CONTRADICTION, NEUTRAL
    2. Compare scores against thresholds
    3. Determine final verdict (SUPPORTED/REFUTED/INSUFFICIENT)
    4. Calculate overall confidence
    5. Generate reasoning text

    Args:
        nli_results: List of NLI results from evidence verification
        support_threshold: Threshold for SUPPORTED verdict (0-1)
        refute_threshold: Threshold for REFUTED verdict (0-1)
        confidence_weight: Weight by NLI confidence (recommended)

    Returns:
        Aggregated verdict with confidence and reasoning

    Example:
        >>> results = [
        ...     NLIResult(label=NLILabel.ENTAILMENT, confidence=0.9, scores={}),
        ...     NLIResult(label=NLILabel.ENTAILMENT, confidence=0.85, scores={}),
        ...     NLIResult(label=NLILabel.NEUTRAL, confidence=0.7, scores={}),
        ... ]
        >>> verdict = aggregate_verdicts(results)
        >>> verdict.verdict
        <Verdict.SUPPORTED: 'SUPPORTED'>
        >>> verdict.confidence
        0.88
    """
    if not nli_results:
        logger.warning("No NLI results to aggregate")
        return AggregatedVerdict(
            verdict=Verdict.INSUFFICIENT,
            confidence=0.0,
            support_score=0.0,
            refute_score=0.0,
            neutral_score=0.0,
            evidence_count=0,
            reasoning="No evidence available for verification.",
        )

    # Calculate scores
    support_score = 0.0
    refute_score = 0.0
    neutral_score = 0.0

    for result in nli_results:
        if confidence_weight:
            # Weight by confidence (recommended)
            weight = result.confidence
        else:
            # Equal weight for all evidence
            weight = 1.0

        if result.label == NLILabel.ENTAILMENT:
            support_score += weight
        elif result.label == NLILabel.CONTRADICTION:
            refute_score += weight
        elif result.label == NLILabel.NEUTRAL:
            neutral_score += weight

    # Normalize scores by evidence count
    evidence_count = len(nli_results)
    support_score /= evidence_count
    refute_score /= evidence_count
    neutral_score /= evidence_count

    # Determine verdict
    if support_score > support_threshold:
        verdict = Verdict.SUPPORTED
        confidence = support_score
    elif refute_score > refute_threshold:
        verdict = Verdict.REFUTED
        confidence = refute_score
    else:
        verdict = Verdict.INSUFFICIENT
        confidence = max(support_score, refute_score, neutral_score)

    # Generate reasoning
    reasoning = generate_reasoning(
        verdict=verdict,
        support_score=support_score,
        refute_score=refute_score,
        neutral_score=neutral_score,
        evidence_count=evidence_count,
    )

    logger.info(
        f"Aggregated verdict: {verdict.value} "
        f"(support={support_score:.2f}, refute={refute_score:.2f}, "
        f"neutral={neutral_score:.2f})"
    )

    return AggregatedVerdict(
        verdict=verdict,
        confidence=confidence,
        support_score=support_score,
        refute_score=refute_score,
        neutral_score=neutral_score,
        evidence_count=evidence_count,
        reasoning=reasoning,
    )


def generate_reasoning(
    verdict: Verdict,
    support_score: float,
    refute_score: float,
    neutral_score: float,
    evidence_count: int,
) -> str:
    """
    Generate human-readable reasoning for verdict.

    Args:
        verdict: Final verdict
        support_score: Normalized support score
        refute_score: Normalized refute score
        neutral_score: Normalized neutral score
        evidence_count: Number of evidence items

    Returns:
        Reasoning text
    """
    if verdict == Verdict.SUPPORTED:
        return (
            f"The claim is SUPPORTED by {evidence_count} evidence item(s). "
            f"Support score: {support_score:.2f} (threshold: 0.6). "
            f"Evidence predominantly supports the claim."
        )
    elif verdict == Verdict.REFUTED:
        return (
            f"The claim is REFUTED by {evidence_count} evidence item(s). "
            f"Refutation score: {refute_score:.2f} (threshold: 0.6). "
            f"Evidence predominantly contradicts the claim."
        )
    else:
        return (
            f"INSUFFICIENT evidence to verify the claim ({evidence_count} item(s)). "
            f"Scores - Support: {support_score:.2f}, Refute: {refute_score:.2f}, "
            f"Neutral: {neutral_score:.2f}. "
            f"Evidence is inconclusive or insufficient."
        )
```

---

### Confidence Scoring

```python
def calculate_confidence(
    nli_results: list[NLIResult],
    verdict: Verdict,
) -> float:
    """
    Calculate overall confidence for verdict.

    Confidence is based on:
    1. Consistency of NLI predictions
    2. Individual NLI confidence scores
    3. Number of evidence items

    Args:
        nli_results: List of NLI results
        verdict: Final verdict

    Returns:
        Confidence score (0-1)
    """
    if not nli_results:
        return 0.0

    # Map verdict to NLI label
    target_label = {
        Verdict.SUPPORTED: NLILabel.ENTAILMENT,
        Verdict.REFUTED: NLILabel.CONTRADICTION,
        Verdict.INSUFFICIENT: NLILabel.NEUTRAL,
    }[verdict]

    # Calculate average confidence for matching predictions
    matching_confidences = [
        result.confidence
        for result in nli_results
        if result.label == target_label
    ]

    if not matching_confidences:
        return 0.0

    # Average confidence of supporting evidence
    avg_confidence = sum(matching_confidences) / len(matching_confidences)

    # Penalize if few evidence items
    evidence_penalty = min(len(nli_results) / 5.0, 1.0)

    return avg_confidence * evidence_penalty
```

---

### Final Verdict Logic

```python
def determine_verdict(
    support_score: float,
    refute_score: float,
    support_threshold: float = 0.6,
    refute_threshold: float = 0.6,
) -> Verdict:
    """
    Determine final verdict from aggregated scores.

    Logic:
    - SUPPORTED if support_score > threshold
    - REFUTED if refute_score > threshold
    - INSUFFICIENT otherwise (or if both exceed threshold, take higher score)

    Args:
        support_score: Aggregated support score
        refute_score: Aggregated refutation score
        support_threshold: Threshold for SUPPORTED
        refute_threshold: Threshold for REFUTED

    Returns:
        Final verdict
    """
    if support_score > support_threshold and refute_score > refute_threshold:
        # Both exceed threshold - conflicting evidence
        # Take the stronger signal
        if support_score > refute_score:
            return Verdict.SUPPORTED
        else:
            return Verdict.REFUTED
    elif support_score > support_threshold:
        return Verdict.SUPPORTED
    elif refute_score > refute_threshold:
        return Verdict.REFUTED
    else:
        return Verdict.INSUFFICIENT
```

---

## 5. Complete Verification Pipeline

### End-to-End Workflow

**File**: `truthgraph/verification/pipeline.py`

```python
"""
Complete claim verification pipeline.

This module orchestrates the end-to-end verification process:
1. Receive claim
2. Generate embedding
3. Retrieve evidence
4. Run NLI verification
5. Aggregate verdicts
6. Store and return result
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from uuid import UUID

import asyncpg

from truthgraph.ml.embeddings import get_embedding_service
from truthgraph.ml.verification import get_nli_verifier
from truthgraph.retrieval.hybrid_search import retrieve_evidence_for_claim
from truthgraph.verification.aggregation import Verdict, aggregate_verdicts

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Complete verification result."""
    claim_id: UUID
    claim_text: str
    verdict: Verdict
    confidence: float
    support_score: float
    refute_score: float
    neutral_score: float
    evidence_count: int
    reasoning: str
    evidence_items: list[dict]  # List of evidence with NLI results


async def verify_claim(
    db_pool: asyncpg.Pool,
    claim_id: UUID,
    claim_text: str,
    tenant_id: str = "default",
    max_evidence: int = 10,
) -> VerificationResult:
    """
    Run complete verification pipeline for a claim.

    Steps:
    1. Generate claim embedding
    2. Retrieve relevant evidence (hybrid search)
    3. Run NLI on claim-evidence pairs
    4. Aggregate verdicts
    5. Store result in database
    6. Return verification result

    Args:
        db_pool: Database connection pool
        claim_id: UUID of claim
        claim_text: Claim text to verify
        tenant_id: Tenant identifier
        max_evidence: Maximum evidence items to retrieve

    Returns:
        Complete verification result

    Example:
        >>> result = await verify_claim(
        ...     db_pool,
        ...     claim_id,
        ...     "The Earth is round.",
        ... )
        >>> result.verdict
        <Verdict.SUPPORTED: 'SUPPORTED'>
        >>> result.confidence
        0.89
    """
    logger.info(f"Starting verification for claim {claim_id}: {claim_text[:100]}")

    # Step 1: Retrieve evidence
    logger.info("Step 1/4: Retrieving evidence")
    evidence_results = await retrieve_evidence_for_claim(
        db_pool,
        claim_text,
        tenant_id=tenant_id,
        k=max_evidence,
    )

    if not evidence_results:
        logger.warning(f"No evidence found for claim {claim_id}")
        return VerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=Verdict.INSUFFICIENT,
            confidence=0.0,
            support_score=0.0,
            refute_score=0.0,
            neutral_score=0.0,
            evidence_count=0,
            reasoning="No relevant evidence found in the knowledge base.",
            evidence_items=[],
        )

    logger.info(f"Retrieved {len(evidence_results)} evidence items")

    # Step 2: Run NLI verification
    logger.info("Step 2/4: Running NLI verification")
    verifier = get_nli_verifier()

    # Build premise-hypothesis pairs
    pairs = [
        (evidence.content, claim_text)
        for evidence in evidence_results
    ]

    # Batch NLI inference
    nli_results = verifier.verify_batch(pairs, batch_size=8)

    logger.info(f"NLI verification complete for {len(nli_results)} pairs")

    # Step 3: Aggregate verdicts
    logger.info("Step 3/4: Aggregating verdicts")
    aggregated = aggregate_verdicts(nli_results)

    # Step 4: Store result
    logger.info("Step 4/4: Storing result")
    await store_verification_result(
        db_pool,
        claim_id=claim_id,
        verdict=aggregated.verdict,
        confidence=aggregated.confidence,
        support_score=aggregated.support_score,
        refute_score=aggregated.refute_score,
        neutral_score=aggregated.neutral_score,
        reasoning=aggregated.reasoning,
        evidence_results=evidence_results,
        nli_results=nli_results,
        tenant_id=tenant_id,
    )

    # Build evidence items with NLI results
    evidence_items = [
        {
            "evidence_id": str(evidence.evidence_id),
            "content": evidence.content[:200] + "..." if len(evidence.content) > 200 else evidence.content,
            "source_url": evidence.source_url,
            "similarity": evidence.combined_score,
            "nli_label": nli_result.label.value,
            "nli_confidence": nli_result.confidence,
        }
        for evidence, nli_result in zip(evidence_results, nli_results)
    ]

    result = VerificationResult(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict=aggregated.verdict,
        confidence=aggregated.confidence,
        support_score=aggregated.support_score,
        refute_score=aggregated.refute_score,
        neutral_score=aggregated.neutral_score,
        evidence_count=aggregated.evidence_count,
        reasoning=aggregated.reasoning,
        evidence_items=evidence_items,
    )

    logger.info(
        f"Verification complete for claim {claim_id}: "
        f"{result.verdict.value} (confidence={result.confidence:.2f})"
    )

    return result


async def store_verification_result(
    db_pool: asyncpg.Pool,
    claim_id: UUID,
    verdict: Verdict,
    confidence: float,
    support_score: float,
    refute_score: float,
    neutral_score: float,
    reasoning: str,
    evidence_results: list,
    nli_results: list,
    tenant_id: str = "default",
) -> None:
    """
    Store verification result in database.

    Inserts into:
    - verdicts table (main verdict)
    - verdict_evidence table (evidence relationships)
    """
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Insert verdict
            verdict_id = await conn.fetchval(
                """
                INSERT INTO verdicts (
                    claim_id,
                    verdict,
                    confidence,
                    reasoning,
                    tenant_id,
                    metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                claim_id,
                verdict.value,
                confidence,
                reasoning,
                tenant_id,
                {
                    "support_score": support_score,
                    "refute_score": refute_score,
                    "neutral_score": neutral_score,
                    "evidence_count": len(evidence_results),
                },
            )

            # Insert evidence relationships
            for evidence, nli_result in zip(evidence_results, nli_results):
                # Map NLI label to relationship
                relationship = {
                    "ENTAILMENT": "supports",
                    "CONTRADICTION": "refutes",
                    "NEUTRAL": "neutral",
                }[nli_result.label.value]

                await conn.execute(
                    """
                    INSERT INTO verdict_evidence (
                        verdict_id,
                        evidence_id,
                        relationship,
                        confidence,
                        tenant_id
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    verdict_id,
                    evidence.evidence_id,
                    relationship,
                    nli_result.confidence,
                    tenant_id,
                )

    logger.info(f"Stored verification result for claim {claim_id}")
```

---

### Code Example: Full Pipeline

```python
import asyncio
import asyncpg
from uuid import uuid4

from truthgraph.verification.pipeline import verify_claim


async def main():
    # Connect to database
    db_pool = await asyncpg.create_pool(
        "postgresql://truthgraph:password@localhost:5432/truthgraph"
    )

    # Example claim
    claim_id = uuid4()
    claim_text = "The Earth orbits the Sun once every 365 days."

    # Run verification
    result = await verify_claim(
        db_pool,
        claim_id,
        claim_text,
    )

    # Print result
    print(f"Claim: {result.claim_text}")
    print(f"Verdict: {result.verdict.value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Reasoning: {result.reasoning}")
    print(f"\nEvidence ({result.evidence_count} items):")

    for item in result.evidence_items:
        print(f"  - {item['nli_label']} ({item['nli_confidence']:.2f}): {item['content']}")

    await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected Output**:

```text
Claim: The Earth orbits the Sun once every 365 days.
Verdict: SUPPORTED
Confidence: 89.00%
Reasoning: The claim is SUPPORTED by 5 evidence item(s). Support score: 0.89 (threshold: 0.6). Evidence predominantly supports the claim.

Evidence (5 items):
  - ENTAILMENT (0.94): Earth's orbital period around the Sun is approximately 365.25 days...
  - ENTAILMENT (0.91): The Earth completes one revolution around the Sun in one year...
  - ENTAILMENT (0.87): Our planet takes 365 days, 5 hours, 48 minutes to orbit the Sun...
  - NEUTRAL (0.72): The solar system consists of eight planets orbiting the Sun...
  - NEUTRAL (0.68): Earth is the third planet from the Sun in our solar system...
```

---

## 6. Model Management

### Hugging Face Model Caching

**Environment Variables**:

```bash
# Set cache directory for Hugging Face models
export HF_HOME=/path/to/models/cache
export TRANSFORMERS_CACHE=/path/to/models/cache

# Offline mode (after models are downloaded)
export TRANSFORMERS_OFFLINE=1
```

**Docker Volume Mount**:

```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - ./volumes/models:/root/.cache/huggingface
```

---

### Lazy Loading on First Request

Models are loaded only when first accessed (implemented in embedding and verification services):

```python
class ModelService:
    _model = None

    @property
    def model(self):
        """Lazy load model on first access."""
        if self._model is None:
            self._model = self._load_model()
        return self._model
```

**Benefits**:
- Faster startup time
- Reduced memory usage if model not needed
- Singleton pattern ensures only one model instance

---

### Memory Management

**Monitor Memory Usage**:

```python
import psutil
import torch


def log_memory_usage():
    """Log current memory usage."""
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024

    logger.info(f"Memory usage: {memory_mb:.1f} MB")

    if torch.cuda.is_available():
        gpu_memory_mb = torch.cuda.memory_allocated() / 1024 / 1024
        logger.info(f"GPU memory: {gpu_memory_mb:.1f} MB")
```

**Clear Unused Memory**:

```python
import gc
import torch


def clear_memory():
    """Force garbage collection and clear GPU cache."""
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

---

### GPU Support (Optional)

**Automatic GPU Detection**:

```python
def detect_device() -> str:
    """Detect best available device."""
    if torch.cuda.is_available():
        logger.info("GPU detected, using CUDA")
        return "cuda"
    elif torch.backends.mps.is_available():  # Apple Silicon
        logger.info("Apple Silicon detected, using MPS")
        return "mps"
    else:
        logger.info("No GPU detected, using CPU")
        return "cpu"
```

**Docker GPU Support**:

```yaml
# docker-compose.yml (for NVIDIA GPUs)
services:
  worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Performance Comparison**:

| Hardware | Embedding (1000 texts) | NLI (100 pairs) | Total Pipeline |
|----------|------------------------|-----------------|----------------|
| CPU (16 cores) | ~1.0s | ~35s | ~40s |
| GPU (RTX 3060) | ~0.2s | ~5s | ~8s |
| GPU (RTX 4090) | ~0.1s | ~2s | ~4s |

---

## 7. Testing Strategy

### Unit Tests with Mock Models

**File**: `tests/unit/test_embeddings.py`

```python
"""Unit tests for embedding generation."""

from unittest.mock import Mock, patch

import pytest

from truthgraph.ml.embeddings import EmbeddingService


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer model."""
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 384
    model.encode.return_value = [[0.1] * 384, [0.2] * 384]
    return model


def test_embed_single_text(mock_model):
    """Test single text embedding."""
    with patch("truthgraph.ml.embeddings.SentenceTransformer", return_value=mock_model):
        service = EmbeddingService()
        embedding = service.embed_text("test text")

        assert len(embedding) == 384
        assert isinstance(embedding, list)


def test_embed_batch(mock_model):
    """Test batch embedding."""
    with patch("truthgraph.ml.embeddings.SentenceTransformer", return_value=mock_model):
        service = EmbeddingService()
        texts = ["text 1", "text 2"]
        embeddings = service.embed_batch(texts)

        assert len(embeddings) == 2
        assert all(len(emb) == 384 for emb in embeddings)
```

---

### Integration Tests with Real Models

**File**: `tests/integration/test_verification_pipeline.py`

```python
"""Integration tests for verification pipeline."""

import pytest
import asyncpg

from truthgraph.verification.pipeline import verify_claim
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.integration
async def test_verify_supported_claim(db_pool: asyncpg.Pool):
    """Test verification of a supported claim."""
    claim_id = uuid4()
    claim_text = "The Earth orbits the Sun."

    result = await verify_claim(db_pool, claim_id, claim_text)

    assert result.verdict.value == "SUPPORTED"
    assert result.confidence > 0.7
    assert result.evidence_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_verify_refuted_claim(db_pool: asyncpg.Pool):
    """Test verification of a refuted claim."""
    claim_id = uuid4()
    claim_text = "The Earth is flat."

    result = await verify_claim(db_pool, claim_id, claim_text)

    assert result.verdict.value == "REFUTED"
    assert result.confidence > 0.6


@pytest.mark.asyncio
@pytest.mark.integration
async def test_verify_insufficient_evidence(db_pool: asyncpg.Pool):
    """Test claim with insufficient evidence."""
    claim_id = uuid4()
    claim_text = "Aliens visited Earth in 1947."

    result = await verify_claim(db_pool, claim_id, claim_text)

    # Should return INSUFFICIENT if no relevant evidence
    assert result.verdict.value in ["INSUFFICIENT", "REFUTED"]
```

---

### Test Fixtures (Known Claim-Verdict Pairs)

**File**: `tests/fixtures/test_claims.json`

```json
[
  {
    "claim": "The Earth orbits the Sun",
    "expected_verdict": "SUPPORTED",
    "min_confidence": 0.8
  },
  {
    "claim": "The Earth is flat",
    "expected_verdict": "REFUTED",
    "min_confidence": 0.7
  },
  {
    "claim": "Water boils at 100 degrees Celsius at sea level",
    "expected_verdict": "SUPPORTED",
    "min_confidence": 0.8
  },
  {
    "claim": "Humans can breathe underwater without equipment",
    "expected_verdict": "REFUTED",
    "min_confidence": 0.9
  }
]
```

**Using Fixtures in Tests**:

```python
import json
import pytest

@pytest.fixture
def test_claims():
    """Load test claims from fixtures."""
    with open("tests/fixtures/test_claims.json") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_known_claims(db_pool, test_claims):
    """Test verification against known claims."""
    for claim_data in test_claims:
        result = await verify_claim(
            db_pool,
            uuid4(),
            claim_data["claim"],
        )

        assert result.verdict.value == claim_data["expected_verdict"]
        assert result.confidence >= claim_data["min_confidence"]
```

---

### Performance Benchmarks

**File**: `tests/performance/test_benchmarks.py`

```python
"""Performance benchmark tests."""

import time
import pytest

from truthgraph.ml.embeddings import get_embedding_service
from truthgraph.ml.verification import get_nli_verifier


def test_embedding_performance():
    """Benchmark embedding generation speed."""
    service = get_embedding_service()
    texts = ["test text"] * 1000

    start = time.time()
    embeddings = service.embed_batch(texts, batch_size=32)
    duration = time.time() - start

    throughput = len(texts) / duration

    print(f"Embedding throughput: {throughput:.0f} texts/second")
    assert throughput > 500, "Embedding too slow"


def test_nli_performance():
    """Benchmark NLI inference speed."""
    verifier = get_nli_verifier()
    pairs = [("premise", "hypothesis")] * 100

    start = time.time()
    results = verifier.verify_batch(pairs, batch_size=8)
    duration = time.time() - start

    throughput = len(pairs) / duration

    print(f"NLI throughput: {throughput:.0f} pairs/second")
    assert throughput > 2, "NLI too slow"


@pytest.mark.asyncio
async def test_end_to_end_latency(db_pool):
    """Benchmark end-to-end verification latency."""
    claim_text = "The Earth orbits the Sun."

    start = time.time()
    result = await verify_claim(db_pool, uuid4(), claim_text)
    duration = time.time() - start

    print(f"End-to-end latency: {duration:.1f} seconds")
    assert duration < 60, "Verification too slow (>60s)"
```

---

## 8. Performance Optimization

### Model Caching

Models are automatically cached using singleton pattern:

```python
# First call: loads model (~3s)
embedding_service = get_embedding_service()

# Subsequent calls: instant (cached)
embedding_service = get_embedding_service()
```

---

### Batch Processing

Always use batch methods for efficiency:

```python
# Slow: one-by-one inference
for text in texts:
    embedding = service.embed_text(text)  # Bad

# Fast: batch inference
embeddings = service.embed_batch(texts)  # Good
```

**Performance Gain**: 10-20x faster for batches of 32+

---

### Query Optimization - Phase 2

**pgvector Index Tuning**:

```sql
-- Increase maintenance_work_mem for faster index builds
SET maintenance_work_mem = '1GB';

-- Build IVFFlat index with optimal list count
CREATE INDEX CONCURRENTLY idx_embeddings_ivfflat
ON evidence_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 500);

-- Analyze table for query planner
ANALYZE evidence_embeddings;

-- Set probes for query time (higher = more accurate, slower)
SET ivfflat.probes = 10;  -- Default: 1, Range: 1-lists
```

---

### Acceptable Latency (<60s)

**Target Breakdown**:

| Component | Target Latency | Typical Latency (CPU) |
|-----------|----------------|------------------------|
| Embedding generation | <1s | 0.5s |
| Evidence retrieval | <3s | 2s |
| NLI verification (10 items) | <40s | 35s |
| Verdict aggregation | <1s | 0.5s |
| Database I/O | <5s | 2s |
| **Total** | **<60s** | **~40s** |

**Optimization Priorities**:
1. NLI inference (dominant factor) - use batch size 8
2. Evidence retrieval - use IVFFlat index
3. Embedding generation - cache claim embeddings
4. Database queries - optimize with proper indexes

---

## 9. TODO Checklist

### ML Models

- [ ] Download sentence-transformers/all-MiniLM-L6-v2 model
- [ ] Download microsoft/deberta-v3-base model
- [ ] Implement EmbeddingService with lazy loading
- [ ] Implement NLIVerifier with lazy loading
- [ ] Test model caching behavior
- [ ] Verify model dimension (384 for embeddings)
- [ ] Test GPU detection and fallback to CPU
- [ ] Implement memory monitoring and logging

### Embedding Pipeline

- [ ] Create `truthgraph/ml/embeddings.py` module
- [ ] Implement `embed_text()` for single text
- [ ] Implement `embed_batch()` for multiple texts
- [ ] Add progress bar for batch embedding
- [ ] Create `scripts/embed_corpus.py` script
- [ ] Test batch embedding with 1000+ items
- [ ] Measure embedding throughput (target: >500 texts/s on CPU)
- [ ] Optimize batch size for CPU vs GPU

### Vector Search

- [ ] Create `truthgraph/retrieval/vector_search.py` module
- [ ] Implement `search_similar_evidence()` function
- [ ] Test cosine distance queries with pgvector
- [ ] Create IVFFlat index for large corpus (>10k items)
- [ ] Implement `search_similar_evidence_batch()` for multiple queries
- [ ] Test query performance with various list counts
- [ ] Add min_similarity threshold filtering
- [ ] Benchmark retrieval latency (target: <3s)

### Hybrid Search

- [ ] Create `truthgraph/retrieval/hybrid_search.py` module
- [ ] Implement `full_text_search()` with PostgreSQL FTS
- [ ] Implement `hybrid_search()` combining FTS + vector
- [ ] Test parallel execution of FTS and vector search
- [ ] Implement result merging and deduplication
- [ ] Add configurable score weighting (FTS vs vector)
- [ ] Test with various weight combinations
- [ ] Measure hybrid search quality vs single method

### NLI Verification

- [ ] Create `truthgraph/ml/verification.py` module
- [ ] Implement NLIVerifier class
- [ ] Implement `verify_single()` for single pair
- [ ] Implement `verify_batch()` for multiple pairs
- [ ] Test NLI with known entailment/contradiction/neutral pairs
- [ ] Verify label mapping (model-specific)
- [ ] Measure NLI inference speed (target: <500ms per pair)
- [ ] Optimize batch size for NLI (recommended: 8 for CPU)

### Verdict Aggregation

- [ ] Create `truthgraph/verification/aggregation.py` module
- [ ] Implement `aggregate_verdicts()` function
- [ ] Test aggregation with various NLI result combinations
- [ ] Implement confidence weighting
- [ ] Implement `generate_reasoning()` for human-readable explanations
- [ ] Test threshold tuning (support_threshold, refute_threshold)
- [ ] Add confidence calculation logic
- [ ] Validate aggregation against known test cases

### Complete Pipeline

- [ ] Create `truthgraph/verification/pipeline.py` module
- [ ] Implement `verify_claim()` end-to-end function
- [ ] Test full pipeline with sample claims
- [ ] Implement `store_verification_result()` for database persistence
- [ ] Add error handling for each pipeline step
- [ ] Log progress at each step
- [ ] Test pipeline with insufficient evidence
- [ ] Test pipeline with contradictory evidence
- [ ] Measure end-to-end latency (target: <60s)

### Testing

- [ ] Create `tests/unit/test_embeddings.py` with mocks
- [ ] Create `tests/unit/test_verification.py` with mocks
- [ ] Create `tests/unit/test_aggregation.py` with known inputs
- [ ] Create `tests/integration/test_verification_pipeline.py`
- [ ] Create `tests/fixtures/test_claims.json` with known verdicts
- [ ] Create `tests/performance/test_benchmarks.py`
- [ ] Test with FEVER dataset samples
- [ ] Test with real-world claims from fact-checking sites
- [ ] Achieve 70%+ accuracy on 20+ test claims
- [ ] Run full test suite (`pytest tests/ -v`)

### Performance Optimization - Todo Checklist

- [ ] Profile embedding generation with cProfile
- [ ] Profile NLI inference with cProfile
- [ ] Optimize batch sizes for CPU/GPU
- [ ] Implement model caching verification
- [ ] Test memory usage under load
- [ ] Optimize pgvector index parameters
- [ ] Test query performance with 10k+ evidence items
- [ ] Measure and optimize end-to-end latency
- [ ] Add performance logging and monitoring
- [ ] Document performance tuning recommendations

### Documentation

- [ ] Add docstrings to all public functions
- [ ] Add type hints throughout
- [ ] Create usage examples for each module
- [ ] Document model selection rationale
- [ ] Document performance benchmarks
- [ ] Create troubleshooting guide
- [ ] Add inline comments for complex logic
- [ ] Update README with Phase 2 features

### Integration

- [ ] Integrate verification pipeline with API endpoints
- [ ] Add API endpoint: POST `/api/v1/claims/{id}/verify`
- [ ] Add API endpoint: GET `/api/v1/verdicts/{claim_id}`
- [ ] Update claim submission to trigger verification
- [ ] Add verification status tracking
- [ ] Implement async verification (background worker)
- [ ] Test API integration end-to-end
- [ ] Update frontend to display verdicts

### Deployment

- [ ] Update Docker images with ML dependencies
- [ ] Test Docker build with models
- [ ] Configure model cache volume mount
- [ ] Test deployment with `docker-compose up`
- [ ] Verify models load correctly on startup
- [ ] Test with limited memory (4GB)
- [ ] Document deployment requirements
- [ ] Create sample corpus loading script

---

## 10. Next Steps

After Phase 2 is complete:

1. **Phase 3 (Future)**: Enhanced features
   - Multi-hop reasoning
   - Temporal tracking
   - Visualization
   - Advanced aggregation strategies

2. **Production Readiness**:
   - Load testing with 100+ concurrent claims
   - Memory profiling and optimization
   - Error recovery and retry logic
   - Monitoring and alerting

3. **Quality Improvements**:
   - Fine-tune aggregation thresholds
   - Add evidence quality scoring
   - Implement claim complexity detection
   - Add explanation generation

---

**Version**: 1.0
**Last Updated**: 2025-10-24
**Status**: Ready for Implementation
