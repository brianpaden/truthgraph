"""SQLAlchemy ORM schemas for database tables."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


class Claim(Base):
    """Claim table - stores user-submitted claims for verification."""
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    verdicts = relationship("Verdict", back_populates="claim", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_claims_submitted_at', submitted_at.desc()),
    )


class Evidence(Base):
    """Evidence table - stores evidence documents and snippets."""
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    source_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_evidence_created_at', created_at.desc()),
    )


class Verdict(Base):
    """Verdict table - stores verification results for claims."""
    __tablename__ = "verdicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    verdict = Column(String(20), nullable=True)  # SUPPORTED, REFUTED, INSUFFICIENT
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    claim = relationship("Claim", back_populates="verdicts")

    __table_args__ = (
        Index('idx_verdicts_claim_id', claim_id),
        Index('idx_verdicts_created_at', created_at.desc()),
    )


class VerdictEvidence(Base):
    """Junction table linking verdicts to supporting/refuting evidence."""
    __tablename__ = "verdict_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verdict_id = Column(UUID(as_uuid=True), ForeignKey("verdicts.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(20), nullable=True)  # supports, refutes, neutral
    confidence = Column(Float, nullable=True)

    __table_args__ = (
        Index('idx_verdict_evidence_verdict_id', verdict_id),
    )
