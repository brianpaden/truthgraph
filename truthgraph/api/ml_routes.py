"""ML API routes for TruthGraph Phase 2.

This module implements REST endpoints for ML functionality:
- /verify: Full claim verification pipeline
- /embed: Generate embeddings
- /search: Hybrid/vector/keyword search
- /nli: Natural Language Inference
- /verdict: Retrieve existing verdicts
"""

import asyncio
import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import Claim, VerificationResult, Evidence, NLIResult as DBNLIResult
from ..services.ml.embedding_service import get_embedding_service
from ..services.ml.nli_service import get_nli_service, NLILabel
from ..services.vector_search_service import VectorSearchService
from .models import (
    EmbedRequest,
    EmbedResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    NLIRequest,
    NLIResponse,
    NLIScores,
    NLIBatchRequest,
    NLIBatchResponse,
    VerifyRequest,
    VerifyResponse,
    EvidenceItem,
    VerdictRequest,
    VerdictResponse,
    ErrorResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ML Services"])


# ===== Dependency Injection =====

def get_embedding_service_dep():
    """Dependency to get embedding service instance."""
    return get_embedding_service()


def get_nli_service_dep():
    """Dependency to get NLI service instance."""
    return get_nli_service()


def get_vector_search_service():
    """Dependency to get vector search service instance."""
    return VectorSearchService(embedding_dimension=384)


# ===== Embedding Endpoint =====

@router.post(
    "/embed",
    response_model=EmbedResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Generate text embeddings",
    description="""
    Generate semantic embeddings for one or more texts using the sentence-transformers model.

    Returns 384-dimensional embeddings suitable for semantic similarity and search.
    Maximum 100 texts per request.
    """,
)
async def embed_texts(
    request: EmbedRequest,
    embedding_service=Depends(get_embedding_service_dep),
) -> EmbedResponse:
    """Generate embeddings for provided texts.

    Args:
        request: Embedding request with texts and batch_size
        embedding_service: Injected embedding service

    Returns:
        EmbedResponse with embeddings and metadata

    Raises:
        HTTPException: 400 for invalid input, 500 for processing errors
    """
    start_time = time.time()

    try:
        # Use run_in_executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: embedding_service.embed_batch(
                texts=request.texts,
                batch_size=request.batch_size,
                show_progress=False
            )
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Generated {len(embeddings)} embeddings in {processing_time:.2f}ms"
        )

        return EmbedResponse(
            embeddings=embeddings,
            count=len(embeddings),
            dimension=384,
            processing_time_ms=processing_time
        )

    except ValueError as e:
        logger.error(f"Embedding validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings"
        )


# ===== Search Endpoint =====

@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Search for relevant evidence",
    description="""
    Search evidence database using hybrid, vector, or keyword search modes.

    - **hybrid**: Combines semantic and keyword search (recommended)
    - **vector**: Pure semantic similarity search
    - **keyword**: Traditional text-based search

    Returns up to 100 results ordered by relevance.
    """,
)
async def search_evidence(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    embedding_service=Depends(get_embedding_service_dep),
    vector_search_service=Depends(get_vector_search_service),
) -> SearchResponse:
    """Search for evidence using specified mode.

    Args:
        request: Search request with query and parameters
        db: Database session
        embedding_service: Injected embedding service
        vector_search_service: Injected vector search service

    Returns:
        SearchResponse with results and metadata

    Raises:
        HTTPException: 400 for invalid input, 500 for search errors
    """
    start_time = time.time()

    try:
        # Generate query embedding for vector/hybrid modes
        if request.mode in ["vector", "hybrid"]:
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None,
                embedding_service.embed_text,
                request.query
            )

            # Perform vector search
            search_results = vector_search_service.search_similar_evidence(
                db=db,
                query_embedding=query_embedding,
                top_k=request.limit,
                min_similarity=request.min_similarity,
                tenant_id=request.tenant_id,
                source_filter=request.source_filter,
            )
        else:
            # Keyword search not implemented yet
            logger.warning("Keyword search mode not yet implemented, falling back to vector")
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Keyword search mode not yet implemented"
            )

        query_time = (time.time() - start_time) * 1000

        # Convert to response format
        result_items = [
            SearchResultItem(
                evidence_id=result.evidence_id,
                content=result.content,
                source_url=result.source_url,
                similarity=result.similarity,
                rank=i + 1
            )
            for i, result in enumerate(search_results)
        ]

        logger.info(
            f"Search returned {len(result_items)} results in {query_time:.2f}ms "
            f"(mode={request.mode}, tenant={request.tenant_id})"
        )

        return SearchResponse(
            results=result_items,
            count=len(result_items),
            query=request.query,
            mode=request.mode,
            query_time_ms=query_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        )


# ===== NLI Endpoint =====

@router.post(
    "/nli",
    response_model=NLIResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Run Natural Language Inference",
    description="""
    Verify the relationship between a premise (evidence) and hypothesis (claim).

    Returns:
    - **entailment**: Premise supports the hypothesis
    - **contradiction**: Premise contradicts the hypothesis
    - **neutral**: No clear relationship

    Uses microsoft/deberta-v3-base fine-tuned on MNLI.
    """,
)
async def run_nli(
    request: NLIRequest,
    nli_service=Depends(get_nli_service_dep),
) -> NLIResponse:
    """Run NLI inference on premise-hypothesis pair.

    Args:
        request: NLI request with premise and hypothesis
        nli_service: Injected NLI service

    Returns:
        NLIResponse with label, confidence, and scores

    Raises:
        HTTPException: 400 for invalid input, 500 for inference errors
    """
    start_time = time.time()

    try:
        # Run NLI inference in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            nli_service.verify_single,
            request.premise,
            request.hypothesis
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"NLI inference: {result.label.value} "
            f"(confidence={result.confidence:.3f}, time={processing_time:.2f}ms)"
        )

        return NLIResponse(
            label=result.label.value,
            confidence=result.confidence,
            scores=NLIScores(
                entailment=result.scores["entailment"],
                contradiction=result.scores["contradiction"],
                neutral=result.scores["neutral"]
            ),
            processing_time_ms=processing_time
        )

    except ValueError as e:
        logger.error(f"NLI validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"NLI inference failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="NLI inference failed"
        )


@router.post(
    "/nli/batch",
    response_model=NLIBatchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Run batch NLI inference",
    description="""
    Verify multiple premise-hypothesis pairs efficiently in batches.

    Maximum 50 pairs per request for optimal performance.
    """,
)
async def run_nli_batch(
    request: NLIBatchRequest,
    nli_service=Depends(get_nli_service_dep),
) -> NLIBatchResponse:
    """Run NLI inference on multiple pairs.

    Args:
        request: Batch NLI request with pairs
        nli_service: Injected NLI service

    Returns:
        NLIBatchResponse with results for all pairs

    Raises:
        HTTPException: 400 for invalid input, 500 for inference errors
    """
    start_time = time.time()

    try:
        # Run batch NLI inference
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: nli_service.verify_batch(
                pairs=request.pairs,
                batch_size=request.batch_size
            )
        )

        processing_time = (time.time() - start_time) * 1000

        # Convert to response format
        response_results = [
            NLIResponse(
                label=result.label.value,
                confidence=result.confidence,
                scores=NLIScores(
                    entailment=result.scores["entailment"],
                    contradiction=result.scores["contradiction"],
                    neutral=result.scores["neutral"]
                )
            )
            for result in results
        ]

        logger.info(
            f"Batch NLI inference: {len(results)} pairs in {processing_time:.2f}ms"
        )

        return NLIBatchResponse(
            results=response_results,
            count=len(response_results),
            total_processing_time_ms=processing_time
        )

    except ValueError as e:
        logger.error(f"Batch NLI validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch NLI inference failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch NLI inference failed"
        )


# ===== Verification Endpoint =====

@router.post(
    "/verify",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Verify a claim (full pipeline)",
    description="""
    Run the complete claim verification pipeline:

    1. **Search**: Find relevant evidence using hybrid/vector search
    2. **NLI**: Analyze claim-evidence relationships
    3. **Aggregate**: Compute final verdict and confidence
    4. **Persist**: Save results to database

    Returns verdict (SUPPORTED/REFUTED/INSUFFICIENT) with evidence and explanation.
    """,
)
async def verify_claim(
    request: VerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    embedding_service=Depends(get_embedding_service_dep),
    nli_service=Depends(get_nli_service_dep),
    vector_search_service=Depends(get_vector_search_service),
) -> VerifyResponse:
    """Execute full verification pipeline for a claim.

    Args:
        request: Verification request with claim and parameters
        db: Database session
        embedding_service: Injected embedding service
        nli_service: Injected NLI service
        vector_search_service: Injected vector search service

    Returns:
        VerifyResponse with verdict, evidence, and explanation

    Raises:
        HTTPException: 400 for invalid input, 500 for pipeline errors
    """
    start_time = time.time()

    try:
        # Step 1: Create claim record
        claim = Claim(text=request.claim)
        db.add(claim)
        db.commit()
        db.refresh(claim)

        logger.info(f"Created claim: {claim.id}")

        # Step 2: Generate claim embedding and search for evidence
        loop = asyncio.get_event_loop()
        claim_embedding = await loop.run_in_executor(
            None,
            embedding_service.embed_text,
            request.claim
        )

        search_results = vector_search_service.search_similar_evidence(
            db=db,
            query_embedding=claim_embedding,
            top_k=request.max_evidence,
            min_similarity=0.3,  # Lower threshold to find diverse evidence
            tenant_id=request.tenant_id,
        )

        if not search_results:
            # No evidence found
            logger.warning(f"No evidence found for claim: {claim.id}")

            verification = VerificationResult(
                claim_id=claim.id,
                verdict="INSUFFICIENT",
                confidence=0.0,
                support_score=0.0,
                refute_score=0.0,
                neutral_score=0.0,
                evidence_count=0,
                supporting_evidence_count=0,
                refuting_evidence_count=0,
                neutral_evidence_count=0,
                reasoning="No relevant evidence found in database",
                retrieval_method=request.search_mode,
            )
            db.add(verification)
            db.commit()
            db.refresh(verification)

            processing_time = (time.time() - start_time) * 1000

            return VerifyResponse(
                verdict="INSUFFICIENT",
                confidence=0.0,
                evidence=[],
                explanation="No relevant evidence found in the database to verify this claim.",
                claim_id=claim.id,
                verification_id=verification.id,
                processing_time_ms=processing_time
            )

        # Step 3: Run NLI on claim-evidence pairs
        nli_pairs = [
            (result.content, request.claim)
            for result in search_results
        ]

        nli_results = await loop.run_in_executor(
            None,
            lambda: nli_service.verify_batch(
                pairs=nli_pairs,
                batch_size=8
            )
        )

        # Step 4: Aggregate results and compute verdict
        entailment_count = sum(1 for r in nli_results if r.label == NLILabel.ENTAILMENT)
        contradiction_count = sum(1 for r in nli_results if r.label == NLILabel.CONTRADICTION)
        neutral_count = sum(1 for r in nli_results if r.label == NLILabel.NEUTRAL)

        # Compute weighted scores
        support_score = sum(
            r.confidence for r in nli_results if r.label == NLILabel.ENTAILMENT
        ) / len(nli_results)

        refute_score = sum(
            r.confidence for r in nli_results if r.label == NLILabel.CONTRADICTION
        ) / len(nli_results)

        neutral_score = sum(
            r.confidence for r in nli_results if r.label == NLILabel.NEUTRAL
        ) / len(nli_results)

        # Determine verdict
        if support_score > refute_score and support_score >= request.confidence_threshold:
            verdict = "SUPPORTED"
            confidence = support_score
            explanation = f"The claim is supported by {entailment_count} evidence items with {confidence:.1%} confidence."
        elif refute_score > support_score and refute_score >= request.confidence_threshold:
            verdict = "REFUTED"
            confidence = refute_score
            explanation = f"The claim is refuted by {contradiction_count} evidence items with {confidence:.1%} confidence."
        else:
            verdict = "INSUFFICIENT"
            confidence = max(support_score, refute_score)
            explanation = f"Insufficient evidence to determine verdict (support: {support_score:.1%}, refute: {refute_score:.1%})."

        # Step 5: Save verification result
        verification = VerificationResult(
            claim_id=claim.id,
            verdict=verdict,
            confidence=float(confidence),
            support_score=float(support_score),
            refute_score=float(refute_score),
            neutral_score=float(neutral_score),
            evidence_count=len(search_results),
            supporting_evidence_count=entailment_count,
            refuting_evidence_count=contradiction_count,
            neutral_evidence_count=neutral_count,
            reasoning=explanation,
            retrieval_method=request.search_mode,
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)

        # Build evidence items for response
        evidence_items = [
            EvidenceItem(
                evidence_id=search_results[i].evidence_id,
                content=search_results[i].content,
                source_url=search_results[i].source_url,
                nli_label=nli_results[i].label.value,
                nli_confidence=nli_results[i].confidence,
                similarity=search_results[i].similarity
            )
            for i in range(len(search_results))
        ]

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Verification complete: {verdict} (confidence={confidence:.3f}, "
            f"evidence={len(search_results)}, time={processing_time:.2f}ms)"
        )

        return VerifyResponse(
            verdict=verdict,
            confidence=float(confidence),
            evidence=evidence_items,
            explanation=explanation,
            claim_id=claim.id,
            verification_id=verification.id,
            processing_time_ms=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification pipeline failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification pipeline failed"
        )


# ===== Verdict Retrieval Endpoint =====

@router.get(
    "/verdict/{claim_id}",
    response_model=VerdictResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Claim or verdict not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get verdict for a claim",
    description="""
    Retrieve the most recent verification verdict for a claim by its ID.

    Returns verdict details including confidence, evidence counts, and reasoning.
    """,
)
async def get_verdict(
    claim_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> VerdictResponse:
    """Retrieve verdict for existing claim.

    Args:
        claim_id: UUID of the claim
        db: Database session

    Returns:
        VerdictResponse with verdict details

    Raises:
        HTTPException: 404 if claim/verdict not found, 500 for errors
    """
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim not found: {claim_id}"
            )

        # Get most recent verification result
        verification = (
            db.query(VerificationResult)
            .filter(VerificationResult.claim_id == claim_id)
            .order_by(VerificationResult.created_at.desc())
            .first()
        )

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No verdict found for claim: {claim_id}"
            )

        logger.info(f"Retrieved verdict for claim: {claim_id}")

        return VerdictResponse(
            claim_id=claim.id,
            claim_text=claim.text,
            verdict=verification.verdict,
            confidence=verification.confidence,
            reasoning=verification.reasoning,
            evidence_count=verification.evidence_count,
            supporting_evidence_count=verification.supporting_evidence_count,
            refuting_evidence_count=verification.refuting_evidence_count,
            created_at=verification.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve verdict: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verdict"
        )
