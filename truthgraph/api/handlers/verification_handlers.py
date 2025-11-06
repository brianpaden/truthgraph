"""Verification request handlers with business logic.

This module contains the business logic for handling claim verification requests,
managing async task queuing, and storing verification results. This is a simplified
implementation for Feature 4.1 that uses in-memory storage. Feature 4.3 will replace
this with proper background task processing using Celery/RQ.
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Dict, Optional

import structlog
from sqlalchemy.orm import Session

from truthgraph.api.schemas.evidence import EvidenceItem
from truthgraph.api.schemas.verification import (
    TaskStatus,
    VerificationOptions,
    VerificationResult,
    VerifyClaimRequest,
)
from truthgraph.schemas import Claim
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
    VerdictLabel,
    get_verification_pipeline_service,
)

logger = structlog.get_logger(__name__)


# In-memory storage (will be replaced with proper queue in Feature 4.3)
# This is a simplified implementation for Phase 1
verification_tasks: Dict[str, TaskStatus] = {}
verification_results: Dict[str, VerificationResult] = {}


class VerificationHandler:
    """Handler for claim verification operations.

    This handler orchestrates claim verification including:
    - Request validation
    - Async task queueing
    - Pipeline execution
    - Result storage and retrieval

    For Feature 4.1, uses simplified in-memory storage. Feature 4.3 will add
    proper background processing with Celery/RQ.
    """

    def __init__(
        self,
        pipeline_service: Optional[VerificationPipelineService] = None,
    ):
        """Initialize verification handler.

        Args:
            pipeline_service: Verification pipeline service instance.
                If None, creates a new instance.
        """
        self.pipeline_service = pipeline_service or get_verification_pipeline_service()

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
        3. Queues verification task in background
        4. Returns task status immediately (202 Accepted)

        Args:
            db: Database session
            claim_id: Unique identifier for the claim
            request: Verification request with options

        Returns:
            TaskStatus with task_id and initial status

        Raises:
            ValueError: If request validation fails
        """
        logger.info(
            "verification_triggered",
            claim_id=claim_id,
            claim_text_length=len(request.claim_text),
        )

        # Check if claim already exists
        existing_claim = db.query(Claim).filter(Claim.text == request.claim_text).first()

        if existing_claim:
            claim_uuid = existing_claim.id
            logger.info("claim_exists", claim_id=claim_id, claim_uuid=str(claim_uuid))

            # Check if already verified
            if claim_id in verification_results:
                existing_result = verification_results[claim_id]
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
                verification_tasks[task_id] = task_status
                return task_status
        else:
            # Create new claim
            db_claim = Claim(text=request.claim_text)
            db.add(db_claim)
            db.commit()
            db.refresh(db_claim)
            claim_uuid = db_claim.id
            logger.info("claim_created", claim_id=claim_id, claim_uuid=str(claim_uuid))

        # Create task
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        task_status = TaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now(UTC),
            progress_percentage=0,
        )
        verification_tasks[task_id] = task_status

        # Queue verification task in background
        asyncio.create_task(
            self._run_verification_task(
                db=db,
                task_id=task_id,
                claim_id=claim_id,
                claim_uuid=claim_uuid,
                claim_text=request.claim_text,
                options=request.options or VerificationOptions(),
                corpus_ids=request.corpus_ids,
            )
        )

        logger.info(
            "verification_queued",
            task_id=task_id,
            claim_id=claim_id,
        )

        return task_status

    async def _run_verification_task(
        self,
        db: Session,
        task_id: str,
        claim_id: str,
        claim_uuid: uuid.UUID,
        claim_text: str,
        options: VerificationOptions,
        corpus_ids: Optional[list[str]],
    ) -> None:
        """Run verification task in background.

        This is executed asynchronously after the request returns 202.
        Updates task status as it progresses and stores final result.

        Args:
            db: Database session
            task_id: Unique task identifier
            claim_id: Original claim identifier from request
            claim_uuid: Database UUID for the claim
            claim_text: Claim text to verify
            options: Verification options
            corpus_ids: Optional corpus filter
        """
        try:
            # Update status to processing
            verification_tasks[task_id].status = "processing"
            verification_tasks[task_id].progress_percentage = 10

            logger.info(
                "verification_task_started",
                task_id=task_id,
                claim_id=claim_id,
            )

            # Run pipeline
            start_time = time.time()

            # Update progress
            verification_tasks[task_id].progress_percentage = 25

            pipeline_result = await self.pipeline_service.verify_claim(
                db=db,
                claim_id=claim_uuid,
                claim_text=claim_text,
                top_k_evidence=options.max_evidence_items,
                min_similarity=0.3,  # Lower threshold for diverse evidence
                tenant_id="default",
                use_cache=True,
                store_result=True,
            )

            # Update progress
            verification_tasks[task_id].progress_percentage = 90

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Convert pipeline result to API response model
            evidence_items = [
                EvidenceItem(
                    id=str(item.evidence_id),
                    text=item.content,
                    source=item.source_url or "Unknown",
                    relevance=item.similarity,
                    url=item.source_url,
                    publication_date=None,
                    nli_label=item.nli_label.value.lower(),
                    nli_confidence=item.nli_confidence,
                )
                for item in pipeline_result.evidence_items
            ]

            # Map verdict label
            verdict_map = {
                VerdictLabel.SUPPORTED: "SUPPORTED",
                VerdictLabel.REFUTED: "REFUTED",
                VerdictLabel.INSUFFICIENT: "NOT_ENOUGH_INFO",
            }

            verification_result = VerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict_map[pipeline_result.verdict],
                confidence=pipeline_result.confidence,
                reasoning=pipeline_result.reasoning,
                evidence=evidence_items,
                verified_at=datetime.now(UTC),
                processing_time_ms=processing_time_ms,
                corpus_ids_searched=corpus_ids,
            )

            # Store result
            verification_results[claim_id] = verification_result

            # Update task to completed
            verification_tasks[task_id].status = "completed"
            verification_tasks[task_id].completed_at = datetime.now(UTC)
            verification_tasks[task_id].result = verification_result
            verification_tasks[task_id].progress_percentage = 100

            logger.info(
                "verification_task_completed",
                task_id=task_id,
                claim_id=claim_id,
                verdict=verification_result.verdict,
                confidence=verification_result.confidence,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.error(
                "verification_task_failed",
                task_id=task_id,
                claim_id=claim_id,
                error=str(e),
                exc_info=True,
            )
            # Update task to failed
            verification_tasks[task_id].status = "failed"
            verification_tasks[task_id].completed_at = datetime.now(UTC)
            verification_tasks[task_id].error = str(e)

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
        return verification_results.get(claim_id)

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
        return verification_tasks.get(task_id)


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
