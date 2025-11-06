"""Verification API routes for claim verification workflow.

This module implements the REST endpoints for the verification workflow:
- POST /api/v1/claims/{claim_id}/verify - Trigger async verification
- GET /api/v1/verdicts/{claim_id} - Get verification result

These endpoints follow the specification in Feature 4.1 of the Phase 2 handoff.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from truthgraph.api.handlers.verification_handlers import get_verification_handler
from truthgraph.api.schemas.verification import (
    TaskStatus,
    VerificationResult,
    VerifyClaimRequest,
)
from truthgraph.db import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Verification"])


@router.post(
    "/claims/{claim_id}/verify",
    response_model=TaskStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger claim verification",
    description="""
    Trigger asynchronous verification for a claim.

    This endpoint:
    1. Accepts a claim with optional verification options
    2. Creates or retrieves the claim record
    3. Checks for existing verification results
    4. Queues verification task in background
    5. Returns immediately with task_id and status (202 Accepted)

    **Use the returned task_id** to poll for results or use the verdict endpoint
    with the claim_id to get the final result.

    ## Request Body

    - **claim_id**: Unique identifier for this claim (used for result retrieval)
    - **claim_text**: The claim text to verify (1-5000 characters)
    - **corpus_ids**: Optional list of corpus IDs to search (null = search all)
    - **options**: Optional verification configuration

    ## Response

    Returns a TaskStatus object with:
    - **task_id**: Unique identifier for tracking this verification task
    - **status**: Current task status (pending, processing, completed, failed)
    - **created_at**: When the task was created
    - **progress_percentage**: Progress indicator (0-100)

    ## Status Codes

    - **202 Accepted**: Verification task queued successfully
    - **400 Bad Request**: Invalid request (empty claim, validation error)
    - **409 Conflict**: Claim is already being verified (returns existing task)
    - **500 Internal Server Error**: Server error during task creation

    ## Example

    ```bash
    curl -X POST "http://localhost:8000/api/v1/claims/claim_123/verify" \\
      -H "Content-Type: application/json" \\
      -d '{
        "claim_id": "claim_123",
        "claim_text": "The Earth orbits around the Sun",
        "options": {
          "max_evidence_items": 5,
          "confidence_threshold": 0.7,
          "return_reasoning": true
        }
      }'
    ```
    """,
    responses={
        202: {
            "description": "Verification task accepted and queued",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "task_abc123xyz",
                        "status": "pending",
                        "created_at": "2025-11-06T10:30:00Z",
                        "completed_at": None,
                        "result": None,
                        "error": None,
                        "progress_percentage": 0,
                    }
                }
            },
        },
        400: {
            "description": "Bad request - validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Claim text cannot be empty"
                    }
                }
            },
        },
        409: {
            "description": "Conflict - claim already verified",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "task_existing",
                        "status": "completed",
                        "created_at": "2025-11-06T10:25:00Z",
                        "completed_at": "2025-11-06T10:25:30Z",
                        "result": {"verdict": "SUPPORTED", "confidence": 0.95},
                        "progress_percentage": 100,
                    }
                }
            },
        },
    },
)
async def verify_claim(
    claim_id: str,
    request: VerifyClaimRequest,
    db: Session = Depends(get_db),
) -> TaskStatus:
    """Trigger verification for a claim.

    Args:
        claim_id: Unique identifier for the claim
        request: Verification request with claim text and options
        db: Database session (injected)

    Returns:
        TaskStatus with task_id and status

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        # Validate claim_id matches request
        if claim_id != request.claim_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path claim_id '{claim_id}' does not match request claim_id '{request.claim_id}'",
            )

        handler = get_verification_handler()
        task_status = await handler.trigger_verification(
            db=db,
            claim_id=claim_id,
            request=request,
        )

        logger.info(
            "verify_endpoint_called",
            claim_id=claim_id,
            task_id=task_status.task_id,
            status=task_status.status,
        )

        return task_status

    except ValueError as e:
        logger.warning(
            "verify_endpoint_validation_error",
            claim_id=claim_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "verify_endpoint_error",
            claim_id=claim_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger verification",
        ) from e


@router.get(
    "/verdicts/{claim_id}",
    response_model=VerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Get verification verdict",
    description="""
    Retrieve the verification verdict for a claim by its ID.

    This endpoint:
    1. Looks up the verification result by claim_id
    2. Returns the complete result if verification is complete
    3. Returns 404 if claim not found or not yet verified
    4. Returns 202 if verification is still in progress

    ## Path Parameters

    - **claim_id**: The unique claim identifier used when triggering verification

    ## Response

    Returns a VerificationResult object with:
    - **claim_id**: Original claim identifier
    - **claim_text**: The verified claim text
    - **verdict**: SUPPORTED, REFUTED, or NOT_ENOUGH_INFO
    - **confidence**: Confidence score (0.0-1.0)
    - **reasoning**: Human-readable explanation
    - **evidence**: List of evidence items analyzed
    - **verified_at**: Timestamp of verification completion
    - **processing_time_ms**: Total processing time

    ## Status Codes

    - **200 OK**: Verdict available, returned successfully
    - **202 Accepted**: Verification still in progress (check again later)
    - **404 Not Found**: Claim not found or not verified yet
    - **500 Internal Server Error**: Server error retrieving verdict

    ## Example

    ```bash
    # Get verdict for claim
    curl "http://localhost:8000/api/v1/verdicts/claim_123"
    ```

    ## Polling Pattern

    For async verification, poll this endpoint until you receive:
    - 200 OK with verdict (completed)
    - 404 with error (failed or not found)

    Recommended polling:
    - First 10s: Poll every 1s
    - After 10s: Poll every 5s
    - Timeout after 60s
    """,
    responses={
        200: {
            "description": "Verdict available and returned",
            "content": {
                "application/json": {
                    "example": {
                        "claim_id": "claim_123",
                        "claim_text": "The Earth orbits around the Sun",
                        "verdict": "SUPPORTED",
                        "confidence": 0.95,
                        "reasoning": "Analysis of 5 evidence items shows strong support for this claim.",
                        "evidence": [
                            {
                                "id": "evidence_abc123",
                                "text": "The Earth orbits the Sun once every 365.25 days.",
                                "source": "Astronomy Textbook",
                                "relevance": 0.98,
                                "nli_label": "entailment",
                                "nli_confidence": 0.96,
                            }
                        ],
                        "verified_at": "2025-11-06T10:30:30Z",
                        "processing_time_ms": 1250,
                    }
                }
            },
        },
        202: {
            "description": "Verification still in progress",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Verification in progress. Please check again later.",
                        "status": "processing",
                    }
                }
            },
        },
        404: {
            "description": "Claim not found or not verified",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No verification result found for claim: claim_123"
                    }
                }
            },
        },
    },
)
async def get_verdict(
    claim_id: str,
) -> VerificationResult:
    """Get verification verdict for a claim.

    Args:
        claim_id: Unique identifier for the claim

    Returns:
        VerificationResult with verdict and evidence

    Raises:
        HTTPException: 202 if still processing, 404 if not found, 500 for errors
    """
    try:
        handler = get_verification_handler()
        result = await handler.get_verification_result(claim_id=claim_id)

        if result is None:
            # Check if there's a task in progress
            from truthgraph.api.handlers.verification_handlers import verification_tasks

            # Check if any task is processing this claim
            for task_status in verification_tasks.values():
                if task_status.status in ["pending", "processing"]:
                    # Still processing
                    logger.info(
                        "verdict_endpoint_still_processing",
                        claim_id=claim_id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_202_ACCEPTED,
                        detail="Verification in progress. Please check again later.",
                    )

            # Not found
            logger.warning(
                "verdict_endpoint_not_found",
                claim_id=claim_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No verification result found for claim: {claim_id}",
            )

        logger.info(
            "verdict_endpoint_success",
            claim_id=claim_id,
            verdict=result.verdict,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "verdict_endpoint_error",
            claim_id=claim_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verdict",
        ) from e
