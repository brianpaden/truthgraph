"""API routes for TruthGraph v0."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ClaimCreate, ClaimListResponse, ClaimResponse
from ..schemas import Claim, Verdict

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/claims", response_model=ClaimResponse, status_code=201)
def create_claim(
    claim: ClaimCreate,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new claim for verification."""
    db_claim = Claim(text=claim.text, source_url=claim.source_url)
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)

    logger.info(f"Claim created: {db_claim.id}")

    return ClaimResponse(
        id=db_claim.id,
        text=db_claim.text,
        source_url=db_claim.source_url,
        submitted_at=db_claim.submitted_at,
        verdict=None
    )


@router.get("/claims", response_model=ClaimListResponse)
def list_claims(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """List all claims with pagination."""
    total = db.query(Claim).count()
    claims = db.query(Claim).order_by(Claim.submitted_at.desc()).offset(skip).limit(limit).all()

    logger.info(f"Claims listed: {len(claims)} of {total}")

    return ClaimListResponse(
        items=[
            ClaimResponse(
                id=c.id,
                text=c.text,
                source_url=c.source_url,
                submitted_at=c.submitted_at,
                verdict=None  # Will be populated in Phase 2
            )
            for c in claims
        ],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: UUID,
    db: Annotated[Session, Depends(get_db)]
):
    """Get a specific claim by ID."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if not claim:
        logger.warning(f"Claim not found: {claim_id}")
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get latest verdict if available
    verdict = db.query(Verdict).filter(
        Verdict.claim_id == claim_id
    ).order_by(Verdict.created_at.desc()).first()

    logger.info(f"Claim retrieved: {claim_id}")

    return ClaimResponse(
        id=claim.id,
        text=claim.text,
        source_url=claim.source_url,
        submitted_at=claim.submitted_at,
        verdict={
            "id": verdict.id,
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reasoning": verdict.reasoning
        } if verdict else None
    )
