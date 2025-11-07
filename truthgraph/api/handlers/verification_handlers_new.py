"""Verification request handlers with background task queue (Feature 4.3).

This module contains the business logic for handling claim verification requests
using the new async background processing infrastructure with proper task queue,
worker pool, retry logic, and result persistence.

This replaces the simplified in-memory implementation from Feature 4.1.
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import HTTPException
from sqlalchemy.orm import Session

from truthgraph.api.schemas.verification import (
    TaskStatus,
    VerificationOptions,
    VerificationResult,
    VerifyClaimRequest,
)
from truthgraph.schemas import Claim
from truthgraph.validation import ValidationStatus, get_claim_validator
from truthgraph.workers.task_queue import get_task_queue
from truthgraph.workers.verification_worker import get_verification_worker

logger = structlog.get_logger(__name__)


class VerificationHandler:
    """Handler for claim verification operations with background processing.

    This handler orchestrates claim verification including:
    - Request validation
    - Async task queueing with proper worker pool
    - Background pipeline execution with retries
    - Result storage with TTL
    - Task status tracking

    Uses Feature 4.3 background processing infrastructure.
    """

    def __init__(self):
        """Initialize verification handler."""
        self.claim_validator = get_claim_validator()
        self.task_queue = get_task_queue()
        self.verification_worker = get_verification_worker()

    async def trigger_verification(
        self,
        db: Session,
        claim_id: str,
        request: VerifyClaimRequest,
    ) -> TaskStatus:
        """Trigger verification for a claim asynchronously.

        This method:
        1. Validates the claim exists or creates it
        2. Checks for existing verification results
        3. Queues verification task in background worker pool
        4. Returns task status immediately (202 Accepted)

        Args:
            db: Database session
            claim_id: Unique identifier for the claim
            request: Verification request with options

        Returns:
            TaskStatus with task_id and initial status

        Raises:
            HTTPException: If input validation fails (400 Bad Request)
            ValueError: If request validation fails
        """
        logger.info(
            "verification_triggered",
            claim_id=claim_id,
            claim_text_length=len(request.claim_text),
        )

        # Validate claim text with comprehensive input validation
        validation_result = self.claim_validator.validate(request.claim_text)

        # Reject INVALID claims with 400 Bad Request
        if validation_result.status == ValidationStatus.INVALID:
            logger.warning(
                "claim_validation_failed",
                claim_id=claim_id,
                error_code=validation_result.error_code,
                error_type=validation_result.error_type,
                message=validation_result.message,
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid claim text",
                    "error_code": validation_result.error_code,
                    "error_type": validation_result.error_type,
                    "message": validation_result.message,
                    "suggestion": validation_result.suggestion,
                },
            )

        # Log warnings but continue processing
        if validation_result.has_warnings():
            logger.info(
                "claim_validation_warnings",
                claim_id=claim_id,
                warnings=validation_result.warnings,
            )

        # Use normalized text for verification
        normalized_claim_text = validation_result.normalized_text or request.claim_text

        # Check if claim already exists
        existing_claim = db.query(Claim).filter(Claim.text == request.claim_text).first()

        if existing_claim:
            claim_uuid = existing_claim.id
            logger.info("claim_exists", claim_id=claim_id, claim_uuid=str(claim_uuid))

            # Check if already verified (check result storage)
            existing_result = await self.task_queue.get_result(claim_id)
            if existing_result:
                logger.info(
                    "claim_already_verified",
                    claim_id=claim_id,
                    verdict=existing_result.verdict,
                )
                # Return completed task with existing result
                task_id = f"task_{uuid.uuid4().hex[:16]}"
                task_status = TaskStatus(
                    task_id=task_id,
                    status="completed",
                    created_at=existing_result.verified_at,
                    completed_at=existing_result.verified_at,
                    result=existing_result,
                    progress_percentage=100,
                )
                return task_status
        else:
            # Create new claim
            db_claim = Claim(text=request.claim_text)
            db.add(db_claim)
            db.commit()
            db.refresh(db_claim)
            claim_uuid = db_claim.id
            logger.info("claim_created", claim_id=claim_id, claim_uuid=str(claim_uuid))

        # Prepare verification options
        options = request.options or VerificationOptions()

        # Queue verification task using task queue
        task_metadata = await self.task_queue.queue_task(
            claim_id=claim_id,
            claim_text=normalized_claim_text,
            task_func=self._verification_task_wrapper,
            options=options.dict(),
            # Pass all necessary arguments
            db=db,
            claim_uuid=claim_uuid,
            original_claim_text=request.claim_text,
            corpus_ids=request.corpus_ids,
            validation_warnings=validation_result.warnings if validation_result.has_warnings() else None,
            top_k_evidence=options.max_evidence_items,
        )

        # Convert TaskMetadata to TaskStatus API model
        task_status = TaskStatus(
            task_id=task_metadata.task_id,
            status=task_metadata.state.value,
            created_at=task_metadata.created_at,
            completed_at=task_metadata.completed_at,
            result=task_metadata.result,
            error=task_metadata.error,
            progress_percentage=task_metadata.progress,
        )

        logger.info(
            "verification_queued",
            task_id=task_status.task_id,
            claim_id=claim_id,
        )

        return task_status

    async def _verification_task_wrapper(
        self,
        task_metadata,
        db: Session,
        claim_uuid: uuid.UUID,
        original_claim_text: str,
        corpus_ids: Optional[list[str]],
        validation_warnings: Optional[list[str]],
        top_k_evidence: int,
    ) -> VerificationResult:
        """Wrapper for verification task execution.

        This is called by the worker pool and handles the actual
        verification with retry logic.

        Args:
            task_metadata: TaskMetadata for progress tracking
            db: Database session
            claim_uuid: Database UUID for claim
            original_claim_text: Original claim text (for result)
            corpus_ids: Optional corpus filter
            validation_warnings: Optional validation warnings
            top_k_evidence: Number of evidence items to retrieve

        Returns:
            VerificationResult

        Raises:
            Exception: If verification fails after retries
        """
        # Call verification worker with retry logic
        result = await self.verification_worker.process_verification(
            db=db,
            claim_id=task_metadata.claim_id,
            claim_uuid=claim_uuid,
            claim_text=task_metadata.claim_text,
            task_metadata=task_metadata,
            top_k_evidence=top_k_evidence,
            min_similarity=0.3,
            tenant_id="default",
            corpus_ids=corpus_ids,
            validation_warnings=validation_warnings,
        )

        return result

    async def get_verification_result(
        self,
        claim_id: str,
    ) -> Optional[VerificationResult]:
        """Get verification result for a claim.

        Args:
            claim_id: Unique claim identifier

        Returns:
            VerificationResult if verification is complete, None otherwise
        """
        return await self.task_queue.get_result(claim_id)

    async def get_task_status(
        self,
        task_id: str,
    ) -> Optional[TaskStatus]:
        """Get status of a verification task.

        Args:
            task_id: Unique task identifier

        Returns:
            TaskStatus if task exists, None otherwise
        """
        task_metadata = await self.task_queue.get_task_status(task_id)

        if task_metadata is None:
            return None

        # Convert TaskMetadata to TaskStatus API model
        return TaskStatus(
            task_id=task_metadata.task_id,
            status=task_metadata.state.value,
            created_at=task_metadata.created_at,
            completed_at=task_metadata.completed_at,
            result=task_metadata.result,
            error=task_metadata.error,
            progress_percentage=task_metadata.progress,
        )


# Singleton handler instance
_handler_instance: Optional[VerificationHandler] = None


def get_verification_handler() -> VerificationHandler:
    """Get or create verification handler singleton.

    Returns:
        VerificationHandler instance
    """
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = VerificationHandler()
    return _handler_instance
