"""Verification Pipeline Orchestration Service for TruthGraph Phase 2.

This module orchestrates the end-to-end verification pipeline:
1. Claim embedding generation
2. Evidence retrieval via vector/hybrid search
3. NLI verification against evidence
4. Verdict aggregation
5. Result storage and caching

Performance target: <60s end-to-end for typical claim
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from truthgraph.schemas import (
    NLIResult as NLIResultModel,
)
from truthgraph.schemas import (
    VerificationResult as VerificationResultModel,
)
from truthgraph.services.ml.embedding_service import EmbeddingService
from truthgraph.services.ml.nli_service import NLILabel, NLIService
from truthgraph.services.vector_search_service import (
    SearchResult,
    VectorSearchService,
)

logger = structlog.get_logger(__name__)

# Type variable for retry decorator
T = TypeVar("T")


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None
            func_name = getattr(func, "__name__", "unknown_function")

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "operation_failed_retrying",
                            function=func_name,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay_seconds=delay,
                            error=str(e),
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            "operation_failed_max_retries",
                            function=func_name,
                            attempts=max_attempts,
                            error=str(e),
                            exc_info=True,
                        )

            # All retries exhausted
            raise RuntimeError(
                f"{func_name} failed after {max_attempts} attempts"
            ) from last_exception

        return wrapper

    return decorator


class VerdictLabel(str, Enum):
    """Final verdict labels for claim verification."""

    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class EvidenceItem:
    """Evidence item with NLI result."""

    evidence_id: UUID
    content: str
    source_url: Optional[str]
    similarity: float
    nli_label: NLILabel
    nli_confidence: float
    nli_scores: dict[str, float]


@dataclass
class VerificationPipelineResult:
    """Complete result from verification pipeline.

    Attributes:
        claim_id: UUID of the verified claim
        claim_text: Original claim text
        verdict: Final verdict (SUPPORTED/REFUTED/INSUFFICIENT)
        confidence: Overall confidence score (0-1)
        support_score: Aggregated support score
        refute_score: Aggregated refutation score
        neutral_score: Aggregated neutral score
        evidence_items: List of evidence with NLI results
        reasoning: Human-readable explanation
        pipeline_duration_ms: Total pipeline execution time
        retrieval_method: Method used for evidence retrieval
        verification_result_id: UUID of stored verification result (if saved)
    """

    claim_id: UUID
    claim_text: str
    verdict: VerdictLabel
    confidence: float
    support_score: float
    refute_score: float
    neutral_score: float
    evidence_items: list[EvidenceItem]
    reasoning: str
    pipeline_duration_ms: float
    retrieval_method: str
    verification_result_id: Optional[UUID] = None


class VerificationPipelineService:
    """Service for orchestrating end-to-end claim verification.

    This service coordinates all ML services to perform comprehensive
    claim verification:
    - Embedding generation for semantic search
    - Evidence retrieval using vector similarity
    - NLI verification for each claim-evidence pair
    - Verdict aggregation based on NLI results
    - Result storage and caching

    Performance characteristics:
        - Target: <60s end-to-end for typical claim
        - Parallel NLI processing for evidence batch
        - Caching for repeated claims
        - Graceful degradation on partial failures

    Thread safety: NOT thread-safe. Use one instance per request/task.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        nli_service: Optional[NLIService] = None,
        vector_search_service: Optional[VectorSearchService] = None,
        embedding_dimension: int = 384,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize verification pipeline service.

        Args:
            embedding_service: Service for generating embeddings (default: singleton)
            nli_service: Service for NLI verification (default: singleton)
            vector_search_service: Service for vector search (default: new instance)
            embedding_dimension: Embedding dimension (default: 384 for MiniLM)
            cache_ttl_seconds: Cache time-to-live in seconds (default: 3600)
        """
        self.embedding_service = embedding_service or EmbeddingService.get_instance()
        self.nli_service = nli_service or NLIService.get_instance()
        self.vector_search_service = vector_search_service or VectorSearchService(
            embedding_dimension=embedding_dimension
        )
        self.cache_ttl_seconds = cache_ttl_seconds
        self.embedding_dimension = embedding_dimension

        # In-memory cache for recent verifications
        # Key: claim_text_hash -> (result, timestamp)
        self._verification_cache: dict[str, tuple[VerificationPipelineResult, datetime]] = {}

        logger.info(
            "verification_pipeline_initialized",
            embedding_dimension=embedding_dimension,
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def _compute_claim_hash(self, claim_text: str) -> str:
        """Compute hash of claim text for caching.

        Args:
            claim_text: Claim text to hash

        Returns:
            SHA256 hash of normalized claim text
        """
        normalized = claim_text.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _get_cached_result(self, claim_text: str) -> Optional[VerificationPipelineResult]:
        """Retrieve cached verification result if available and fresh.

        Args:
            claim_text: Claim text to look up

        Returns:
            Cached result if available and not expired, None otherwise
        """
        claim_hash = self._compute_claim_hash(claim_text)

        if claim_hash in self._verification_cache:
            result, timestamp = self._verification_cache[claim_hash]
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()

            if age_seconds < self.cache_ttl_seconds:
                logger.info(
                    "cache_hit",
                    claim_hash=claim_hash[:16],
                    age_seconds=age_seconds,
                )
                return result
            else:
                # Expired, remove from cache
                del self._verification_cache[claim_hash]
                logger.info(
                    "cache_expired",
                    claim_hash=claim_hash[:16],
                    age_seconds=age_seconds,
                )

        return None

    def _cache_result(self, claim_text: str, result: VerificationPipelineResult) -> None:
        """Cache verification result.

        Args:
            claim_text: Claim text to use as cache key
            result: Verification result to cache
        """
        claim_hash = self._compute_claim_hash(claim_text)
        self._verification_cache[claim_hash] = (result, datetime.utcnow())
        logger.debug("result_cached", claim_hash=claim_hash[:16])

    def clear_cache(self) -> None:
        """Clear all cached verification results."""
        cache_size = len(self._verification_cache)
        self._verification_cache.clear()
        logger.info("cache_cleared", entries_removed=cache_size)

    async def verify_claim(
        self,
        db: Session,
        claim_id: UUID,
        claim_text: str,
        top_k_evidence: int = 10,
        min_similarity: float = 0.5,
        tenant_id: str = "default",
        use_cache: bool = True,
        store_result: bool = True,
    ) -> VerificationPipelineResult:
        """Execute end-to-end verification pipeline for a claim.

        Pipeline steps:
        1. Check cache for recent verification
        2. Generate embedding for claim
        3. Search for relevant evidence (vector search)
        4. Run NLI verification on claim vs each evidence
        5. Aggregate NLI results into verdict
        6. Store verification result in database
        7. Cache result for future requests

        Args:
            db: Database session (sync)
            claim_id: UUID of the claim to verify
            claim_text: Text of the claim to verify
            top_k_evidence: Number of evidence items to retrieve (default: 10)
            min_similarity: Minimum similarity threshold for evidence (default: 0.5)
            tenant_id: Tenant identifier for isolation (default: 'default')
            use_cache: Whether to use cached results (default: True)
            store_result: Whether to store result in database (default: True)

        Returns:
            VerificationPipelineResult with verdict and supporting evidence

        Raises:
            ValueError: If claim_text is empty or invalid
            RuntimeError: If pipeline execution fails critically
        """
        if not claim_text or not claim_text.strip():
            raise ValueError("Claim text cannot be empty")

        start_time = time.time()

        # Step 1: Check cache
        if use_cache:
            cached_result = self._get_cached_result(claim_text)
            if cached_result is not None:
                logger.info(
                    "verification_cache_hit",
                    claim_id=str(claim_id),
                    verdict=cached_result.verdict.value,
                )
                return cached_result

        logger.info(
            "verification_pipeline_start",
            claim_id=str(claim_id),
            claim_text_length=len(claim_text),
            top_k_evidence=top_k_evidence,
            min_similarity=min_similarity,
        )

        try:
            # Step 2: Generate claim embedding (with retry)
            embedding_start = time.time()
            claim_embedding = self._generate_embedding_with_retry(claim_text)
            embedding_duration = (time.time() - embedding_start) * 1000

            logger.info(
                "claim_embedding_generated",
                claim_id=str(claim_id),
                duration_ms=embedding_duration,
                embedding_dimension=len(claim_embedding),
            )

            # Step 3: Search for relevant evidence (with retry)
            search_start = time.time()
            search_results = self._search_evidence_with_retry(
                db=db,
                query_embedding=claim_embedding,
                top_k=top_k_evidence,
                min_similarity=min_similarity,
                tenant_id=tenant_id,
            )
            search_duration = (time.time() - search_start) * 1000

            logger.info(
                "evidence_retrieved",
                claim_id=str(claim_id),
                evidence_count=len(search_results),
                duration_ms=search_duration,
            )

            if not search_results:
                # No evidence found - return INSUFFICIENT verdict
                insufficient_result = self._create_insufficient_verdict(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    pipeline_duration_ms=(time.time() - start_time) * 1000,
                )

                if store_result:
                    insufficient_result = await self._store_verification_result(
                        db=db, result=insufficient_result
                    )

                if use_cache:
                    self._cache_result(claim_text, insufficient_result)

                return insufficient_result

            # Step 4: Run NLI verification for each evidence item
            nli_start = time.time()
            evidence_items = await self._verify_evidence_batch(
                claim_text=claim_text,
                search_results=search_results,
            )
            nli_duration = (time.time() - nli_start) * 1000

            logger.info(
                "nli_verification_complete",
                claim_id=str(claim_id),
                evidence_verified=len(evidence_items),
                duration_ms=nli_duration,
            )

            # Step 5: Aggregate results into verdict
            aggregation_start = time.time()
            verdict_result = self._aggregate_verdict(
                claim_id=claim_id,
                claim_text=claim_text,
                evidence_items=evidence_items,
                pipeline_duration_ms=(time.time() - start_time) * 1000,
            )
            aggregation_duration = (time.time() - aggregation_start) * 1000

            logger.info(
                "verdict_aggregated",
                claim_id=str(claim_id),
                verdict=verdict_result.verdict.value,
                confidence=verdict_result.confidence,
                duration_ms=aggregation_duration,
            )

            # Step 6: Store verification result
            if store_result:
                verdict_result = await self._store_verification_result(db=db, result=verdict_result)

            # Step 7: Cache result
            if use_cache:
                self._cache_result(claim_text, verdict_result)

            total_duration = (time.time() - start_time) * 1000
            logger.info(
                "verification_pipeline_complete",
                claim_id=str(claim_id),
                verdict=verdict_result.verdict.value,
                confidence=verdict_result.confidence,
                evidence_count=len(evidence_items),
                total_duration_ms=total_duration,
            )

            return verdict_result

        except Exception as e:
            logger.error(
                "verification_pipeline_failed",
                claim_id=str(claim_id),
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Verification pipeline failed: {e}") from e

    @retry_on_failure(max_attempts=3, initial_delay=1.0, exceptions=(RuntimeError,))
    def _generate_embedding_with_retry(self, claim_text: str) -> list[float]:
        """Generate embedding with retry logic.

        Args:
            claim_text: Text to embed

        Returns:
            Embedding vector

        Raises:
            RuntimeError: If all retry attempts fail
        """
        return self.embedding_service.embed_text(claim_text)

    @retry_on_failure(max_attempts=2, initial_delay=0.5, exceptions=(RuntimeError,))
    def _search_evidence_with_retry(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float,
        tenant_id: str,
    ) -> list[SearchResult]:
        """Search for evidence with retry logic.

        Args:
            db: Database session
            query_embedding: Query embedding vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            tenant_id: Tenant identifier

        Returns:
            List of search results

        Raises:
            RuntimeError: If all retry attempts fail
        """
        return self.vector_search_service.search_similar_evidence(
            db=db,
            query_embedding=query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
            tenant_id=tenant_id,
        )

    async def _verify_evidence_batch(
        self,
        claim_text: str,
        search_results: list[SearchResult],
    ) -> list[EvidenceItem]:
        """Run NLI verification for all evidence items.

        Args:
            claim_text: Claim text (hypothesis)
            search_results: Evidence search results (premises)

        Returns:
            List of EvidenceItem objects with NLI results
        """
        # Prepare pairs for batch NLI
        pairs = [
            (result.content, claim_text)  # (premise, hypothesis)
            for result in search_results
        ]

        # Run batch NLI inference
        nli_results = self.nli_service.verify_batch(
            pairs=pairs,
            batch_size=8,  # Optimal for CPU
        )

        # Combine search results with NLI results
        evidence_items = []
        for search_result, nli_result in zip(search_results, nli_results, strict=False):
            evidence_item = EvidenceItem(
                evidence_id=search_result.evidence_id,
                content=search_result.content,
                source_url=search_result.source_url,
                similarity=search_result.similarity,
                nli_label=nli_result.label,
                nli_confidence=nli_result.confidence,
                nli_scores=nli_result.scores,
            )
            evidence_items.append(evidence_item)

        return evidence_items

    def _aggregate_verdict(
        self,
        claim_id: UUID,
        claim_text: str,
        evidence_items: list[EvidenceItem],
        pipeline_duration_ms: float,
    ) -> VerificationPipelineResult:
        """Aggregate NLI results into final verdict.

        Aggregation strategy:
        1. Weight each NLI score by similarity score (more relevant = higher weight)
        2. Count supporting (ENTAILMENT) vs refuting (CONTRADICTION) evidence
        3. Determine verdict based on weighted scores and counts
        4. Calculate overall confidence

        Args:
            claim_id: UUID of claim
            claim_text: Text of claim
            evidence_items: List of evidence with NLI results
            pipeline_duration_ms: Total pipeline duration

        Returns:
            VerificationPipelineResult with aggregated verdict
        """
        if not evidence_items:
            return self._create_insufficient_verdict(
                claim_id=claim_id,
                claim_text=claim_text,
                pipeline_duration_ms=pipeline_duration_ms,
            )

        # Calculate weighted scores
        total_weight = 0.0
        weighted_support = 0.0
        weighted_refute = 0.0
        weighted_neutral = 0.0

        support_count = 0
        refute_count = 0
        neutral_count = 0

        for item in evidence_items:
            # Use similarity as weight (0-1 range)
            weight = item.similarity
            total_weight += weight

            # Weight NLI scores by similarity
            weighted_support += item.nli_scores.get("entailment", 0.0) * weight
            weighted_refute += item.nli_scores.get("contradiction", 0.0) * weight
            weighted_neutral += item.nli_scores.get("neutral", 0.0) * weight

            # Count by label
            if item.nli_label == NLILabel.ENTAILMENT:
                support_count += 1
            elif item.nli_label == NLILabel.CONTRADICTION:
                refute_count += 1
            else:
                neutral_count += 1

        # Normalize weighted scores
        if total_weight > 0:
            weighted_support /= total_weight
            weighted_refute /= total_weight
            weighted_neutral /= total_weight

        # Determine verdict based on scores and counts
        # Use weighted scores as primary signal
        max_score = max(weighted_support, weighted_refute, weighted_neutral)

        # Confidence thresholds
        HIGH_CONFIDENCE_THRESHOLD = 0.6
        MIN_EVIDENCE_THRESHOLD = 2

        if weighted_support == max_score and weighted_support > HIGH_CONFIDENCE_THRESHOLD:
            verdict = VerdictLabel.SUPPORTED
            confidence = weighted_support
        elif weighted_refute == max_score and weighted_refute > HIGH_CONFIDENCE_THRESHOLD:
            verdict = VerdictLabel.REFUTED
            confidence = weighted_refute
        elif len(evidence_items) < MIN_EVIDENCE_THRESHOLD:
            # Not enough evidence for confident verdict
            verdict = VerdictLabel.INSUFFICIENT
            confidence = 0.5
        else:
            # Scores are close or neutral dominates
            verdict = VerdictLabel.INSUFFICIENT
            confidence = max_score

        # Generate reasoning
        reasoning = self._generate_reasoning(
            verdict=verdict,
            confidence=confidence,
            support_score=weighted_support,
            refute_score=weighted_refute,
            neutral_score=weighted_neutral,
            support_count=support_count,
            refute_count=refute_count,
            neutral_count=neutral_count,
            total_evidence=len(evidence_items),
        )

        return VerificationPipelineResult(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=verdict,
            confidence=confidence,
            support_score=weighted_support,
            refute_score=weighted_refute,
            neutral_score=weighted_neutral,
            evidence_items=evidence_items,
            reasoning=reasoning,
            pipeline_duration_ms=pipeline_duration_ms,
            retrieval_method="vector",
        )

    def _create_insufficient_verdict(
        self,
        claim_id: UUID,
        claim_text: str,
        pipeline_duration_ms: float,
    ) -> VerificationPipelineResult:
        """Create INSUFFICIENT verdict when no evidence is found.

        Args:
            claim_id: UUID of claim
            claim_text: Text of claim
            pipeline_duration_ms: Pipeline duration

        Returns:
            VerificationPipelineResult with INSUFFICIENT verdict
        """
        return VerificationPipelineResult(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=VerdictLabel.INSUFFICIENT,
            confidence=0.0,
            support_score=0.0,
            refute_score=0.0,
            neutral_score=0.0,
            evidence_items=[],
            reasoning="No relevant evidence found in the database.",
            pipeline_duration_ms=pipeline_duration_ms,
            retrieval_method="vector",
        )

    def _generate_reasoning(
        self,
        verdict: VerdictLabel,
        confidence: float,
        support_score: float,
        refute_score: float,
        neutral_score: float,
        support_count: int,
        refute_count: int,
        neutral_count: int,
        total_evidence: int,
    ) -> str:
        """Generate human-readable reasoning for verdict.

        Args:
            verdict: Final verdict
            confidence: Confidence score
            support_score: Weighted support score
            refute_score: Weighted refutation score
            neutral_score: Weighted neutral score
            support_count: Count of supporting evidence
            refute_count: Count of refuting evidence
            neutral_count: Count of neutral evidence
            total_evidence: Total evidence count

        Returns:
            Human-readable reasoning text
        """
        if verdict == VerdictLabel.SUPPORTED:
            reasoning = (
                f"Analysis of {total_evidence} relevant evidence items shows "
                f"strong support for this claim. {support_count} evidence items "
                f"directly support the claim with weighted confidence of {support_score:.2f}. "
            )
            if refute_count > 0:
                reasoning += (
                    f"While {refute_count} items show contradiction "
                    f"(score: {refute_score:.2f}), the supporting evidence is more conclusive."
                )
        elif verdict == VerdictLabel.REFUTED:
            reasoning = (
                f"Analysis of {total_evidence} relevant evidence items shows "
                f"this claim is refuted. {refute_count} evidence items "
                f"contradict the claim with weighted confidence of {refute_score:.2f}. "
            )
            if support_count > 0:
                reasoning += (
                    f"While {support_count} items show support "
                    f"(score: {support_score:.2f}), the refuting evidence is more conclusive."
                )
        else:  # INSUFFICIENT
            reasoning = (
                f"Analysis of {total_evidence} evidence items yielded insufficient "
                f"information to verify this claim. "
            )
            if total_evidence == 0:
                reasoning += "No relevant evidence was found in the database."
            else:
                reasoning += (
                    f"Evidence distribution: {support_count} supporting, "
                    f"{refute_count} refuting, {neutral_count} neutral. "
                    f"Scores: support={support_score:.2f}, refute={refute_score:.2f}, "
                    f"neutral={neutral_score:.2f}. More evidence is needed for a confident verdict."
                )

        return reasoning

    async def _store_verification_result(
        self,
        db: Session,
        result: VerificationPipelineResult,
    ) -> VerificationPipelineResult:
        """Store verification result in database.

        Args:
            db: Database session
            result: Verification result to store

        Returns:
            Updated result with verification_result_id set
        """
        try:
            # Create verification result record
            verification_record = VerificationResultModel(
                claim_id=result.claim_id,
                verdict=result.verdict.value,
                confidence=result.confidence,
                support_score=result.support_score,
                refute_score=result.refute_score,
                neutral_score=result.neutral_score,
                evidence_count=len(result.evidence_items),
                supporting_evidence_count=sum(
                    1 for item in result.evidence_items if item.nli_label == NLILabel.ENTAILMENT
                ),
                refuting_evidence_count=sum(
                    1 for item in result.evidence_items if item.nli_label == NLILabel.CONTRADICTION
                ),
                neutral_evidence_count=sum(
                    1 for item in result.evidence_items if item.nli_label == NLILabel.NEUTRAL
                ),
                reasoning=result.reasoning,
                retrieval_method=result.retrieval_method,
                pipeline_version="1.0.0",
                created_at=datetime.utcnow(),
            )

            db.add(verification_record)
            db.flush()  # Get the ID without committing

            # Store individual NLI results
            for item in result.evidence_items:
                nli_record = NLIResultModel(
                    claim_id=result.claim_id,
                    evidence_id=item.evidence_id,
                    label=item.nli_label.value,
                    confidence=item.nli_confidence,
                    entailment_score=item.nli_scores.get("entailment", 0.0),
                    contradiction_score=item.nli_scores.get("contradiction", 0.0),
                    neutral_score=item.nli_scores.get("neutral", 0.0),
                    model_name="cross-encoder/nli-deberta-v3-base",
                    premise_text=item.content,
                    hypothesis_text=result.claim_text,
                    created_at=datetime.utcnow(),
                )
                db.add(nli_record)

            db.commit()

            # Update result with stored ID
            result.verification_result_id = verification_record.id

            logger.info(
                "verification_result_stored",
                verification_result_id=str(verification_record.id),
                claim_id=str(result.claim_id),
                verdict=result.verdict.value,
                evidence_count=len(result.evidence_items),
            )

            return result

        except Exception as e:
            db.rollback()
            logger.error(
                "verification_result_storage_failed",
                claim_id=str(result.claim_id),
                error=str(e),
                exc_info=True,
            )
            # Don't fail pipeline on storage error
            return result


def get_verification_pipeline_service(
    embedding_dimension: int = 384,
) -> VerificationPipelineService:
    """Get a new instance of VerificationPipelineService.

    Args:
        embedding_dimension: Embedding dimension (default: 384 for MiniLM)

    Returns:
        New VerificationPipelineService instance
    """
    return VerificationPipelineService(embedding_dimension=embedding_dimension)
