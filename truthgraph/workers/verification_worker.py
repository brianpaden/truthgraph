"""Verification worker with retry logic and error handling.

This module implements the verification worker that processes
verification tasks in the background with proper error handling,
exponential backoff retry, and progress tracking.
"""

import asyncio
import time
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from truthgraph.api.schemas.evidence import EvidenceItem
from truthgraph.api.schemas.verification import VerificationResult
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
    VerdictLabel,
    get_verification_pipeline_service,
)
from truthgraph.workers.task_status import TaskMetadata

logger = structlog.get_logger(__name__)


class TemporaryError(Exception):
    """Exception for temporary errors that should be retried."""

    pass


class PermanentError(Exception):
    """Exception for permanent errors that should not be retried."""

    pass


class VerificationWorker:
    """Worker for processing verification tasks with retry logic.

    This worker:
    - Executes verification pipeline for claims
    - Handles temporary errors with exponential backoff retry
    - Tracks progress during processing
    - Converts pipeline results to API models
    - Stores results on completion

    Attributes:
        pipeline_service: Verification pipeline service instance
        max_retries: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff delay in seconds (default: 2)
        max_backoff: Maximum backoff delay in seconds (default: 30)
    """

    def __init__(
        self,
        pipeline_service: Optional[VerificationPipelineService] = None,
        max_retries: int = 3,
        initial_backoff: float = 2.0,
        max_backoff: float = 30.0,
    ):
        """Initialize verification worker.

        Args:
            pipeline_service: Verification pipeline service (default: singleton)
            max_retries: Maximum retry attempts (default: 3)
            initial_backoff: Initial backoff delay in seconds (default: 2.0)
            max_backoff: Maximum backoff delay in seconds (default: 30.0)
        """
        self.pipeline_service = pipeline_service or get_verification_pipeline_service()
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff

        logger.info(
            "verification_worker_initialized",
            max_retries=max_retries,
            initial_backoff=initial_backoff,
            max_backoff=max_backoff,
        )

    async def process_verification(
        self,
        db: Session,
        claim_id: str,
        claim_uuid: UUID,
        claim_text: str,
        task_metadata: TaskMetadata,
        top_k_evidence: int = 10,
        min_similarity: float = 0.3,
        tenant_id: str = "default",
        corpus_ids: Optional[list[str]] = None,
        validation_warnings: Optional[list[str]] = None,
    ) -> VerificationResult:
        """Process verification task with retry logic.

        Args:
            db: Database session
            claim_id: Original claim identifier from request
            claim_uuid: Database UUID for claim
            claim_text: Claim text to verify
            task_metadata: Task metadata for progress tracking
            top_k_evidence: Number of evidence items to retrieve
            min_similarity: Minimum similarity threshold
            tenant_id: Tenant identifier
            corpus_ids: Optional corpus filter
            validation_warnings: Optional validation warnings

        Returns:
            VerificationResult with verdict and evidence

        Raises:
            PermanentError: For errors that should not be retried
            TemporaryError: For errors after max retries exhausted
        """
        logger.info(
            "verification_processing_started",
            task_id=task_metadata.task_id,
            claim_id=claim_id,
            claim_uuid=str(claim_uuid),
        )

        start_time = time.time()
        attempt = 0

        while attempt <= self.max_retries:
            try:
                # Update progress
                progress = 25 + (attempt * 10)
                task_metadata.update_progress(progress)

                # Run verification pipeline
                pipeline_result = await self.pipeline_service.verify_claim(
                    db=db,
                    claim_id=claim_uuid,
                    claim_text=claim_text,
                    top_k_evidence=top_k_evidence,
                    min_similarity=min_similarity,
                    tenant_id=tenant_id,
                    use_cache=True,
                    store_result=True,
                )

                # Update progress
                task_metadata.update_progress(90)

                # Calculate processing time
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Convert pipeline result to API model
                verification_result = self._convert_to_api_result(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    pipeline_result=pipeline_result,
                    processing_time_ms=processing_time_ms,
                    corpus_ids=corpus_ids,
                    validation_warnings=validation_warnings,
                )

                logger.info(
                    "verification_completed",
                    task_id=task_metadata.task_id,
                    claim_id=claim_id,
                    verdict=verification_result.verdict,
                    confidence=verification_result.confidence,
                    processing_time_ms=processing_time_ms,
                    attempts=attempt + 1,
                )

                return verification_result

            except PermanentError as e:
                # Don't retry permanent errors
                logger.error(
                    "verification_permanent_error",
                    task_id=task_metadata.task_id,
                    claim_id=claim_id,
                    error=str(e),
                    exc_info=True,
                )
                raise

            except Exception as e:
                attempt += 1
                task_metadata.increment_retry()

                # Check if we should retry
                if attempt > self.max_retries:
                    logger.error(
                        "verification_max_retries_exceeded",
                        task_id=task_metadata.task_id,
                        claim_id=claim_id,
                        attempts=attempt,
                        error=str(e),
                        exc_info=True,
                    )
                    raise TemporaryError(
                        f"Verification failed after {self.max_retries} attempts: {e}"
                    ) from e

                # Calculate backoff delay with exponential backoff
                backoff = min(
                    self.initial_backoff * (2 ** (attempt - 1)),
                    self.max_backoff,
                )

                logger.warning(
                    "verification_retry",
                    task_id=task_metadata.task_id,
                    claim_id=claim_id,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    backoff_seconds=backoff,
                    error=str(e),
                )

                # Wait before retrying
                await asyncio.sleep(backoff)

        # Should never reach here, but handle it
        raise TemporaryError(
            f"Verification failed after {self.max_retries} attempts"
        )

    def _convert_to_api_result(
        self,
        claim_id: str,
        claim_text: str,
        pipeline_result,
        processing_time_ms: int,
        corpus_ids: Optional[list[str]],
        validation_warnings: Optional[list[str]],
    ) -> VerificationResult:
        """Convert pipeline result to API response model.

        Args:
            claim_id: Original claim identifier
            claim_text: Claim text
            pipeline_result: Result from verification pipeline
            processing_time_ms: Processing time in milliseconds
            corpus_ids: Optional corpus filter
            validation_warnings: Optional validation warnings

        Returns:
            VerificationResult API model
        """
        from datetime import UTC, datetime

        # Convert evidence items
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

        return VerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=verdict_map[pipeline_result.verdict],
            confidence=pipeline_result.confidence,
            reasoning=pipeline_result.reasoning,
            evidence=evidence_items,
            verified_at=datetime.now(UTC),
            processing_time_ms=processing_time_ms,
            corpus_ids_searched=corpus_ids,
            validation_warnings=validation_warnings,
        )


# Global singleton instance
_worker_instance: Optional[VerificationWorker] = None


def get_verification_worker(
    max_retries: int = 3,
    initial_backoff: float = 2.0,
    max_backoff: float = 30.0,
) -> VerificationWorker:
    """Get or create global verification worker instance.

    Args:
        max_retries: Maximum retry attempts (default: 3)
        initial_backoff: Initial backoff delay (default: 2.0)
        max_backoff: Maximum backoff delay (default: 30.0)

    Returns:
        VerificationWorker instance
    """
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = VerificationWorker(
            max_retries=max_retries,
            initial_backoff=initial_backoff,
            max_backoff=max_backoff,
        )
    return _worker_instance
