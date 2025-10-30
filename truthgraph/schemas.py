"""SQLAlchemy ORM schemas for database tables."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
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

    __table_args__ = (Index("idx_claims_submitted_at", submitted_at.desc()),)


class Evidence(Base):
    """Evidence table - stores evidence documents and snippets."""

    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    source_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_evidence_created_at", created_at.desc()),)


class Verdict(Base):
    """Verdict table - stores verification results for claims."""

    __tablename__ = "verdicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    verdict = Column(String(20), nullable=True)  # SUPPORTED, REFUTED, INSUFFICIENT
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    claim = relationship("Claim", back_populates="verdicts")

    __table_args__ = (
        Index("idx_verdicts_claim_id", claim_id),
        Index("idx_verdicts_created_at", created_at.desc()),
    )


class VerdictEvidence(Base):
    """Junction table linking verdicts to supporting/refuting evidence."""

    __tablename__ = "verdict_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verdict_id = Column(
        UUID(as_uuid=True), ForeignKey("verdicts.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id = Column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = Column(String(20), nullable=True)  # supports, refutes, neutral
    confidence = Column(Float, nullable=True)

    __table_args__ = (Index("idx_verdict_evidence_verdict_id", verdict_id),)


# Phase 2: ML-Enhanced Verification Tables


class Embedding(Base):
    """Embeddings table - stores vector embeddings for evidence and claims.

    Uses pgvector extension for efficient similarity search.
    Dimension: 384 for sentence-transformers/all-MiniLM-L6-v2 model.

    This matches the EmbeddingService configuration. For different models,
    update both the schema dimension and the Alembic migration to match.
    """

    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Polymorphic relationship - can embed evidence or claims
    entity_type = Column(String(20), nullable=False)  # 'evidence' or 'claim'
    entity_id = Column(UUID(as_uuid=True), nullable=False)

    # Vector embedding (384 dimensions for all-MiniLM-L6-v2)
    # Note: This matches the migration dimension. For other models, update both
    # the schema and migration to match the model's embedding dimension.
    embedding = Column(Vector(384), nullable=False)

    # Model metadata
    model_name = Column(String(100), nullable=False, default="sentence-transformers/all-MiniLM-L6-v2")
    model_version = Column(String(50), nullable=True)

    # Tenant isolation for multi-tenancy support
    tenant_id = Column(String(255), nullable=False, default="default")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for tenant isolation
        Index("idx_embeddings_tenant_id", tenant_id),
        # Composite index for entity lookups
        Index("idx_embeddings_entity", entity_type, entity_id),
        # Unique constraint to prevent duplicate embeddings
        Index("idx_embeddings_entity_unique", entity_type, entity_id, unique=True),
        # IVFFlat index for vector similarity search (cosine distance)
        # Lists parameter should be ~sqrt(total_rows) for optimal performance
        # Note: This index is created separately in migration for better control
    )


class NLIResult(Base):
    """NLI Results table - stores Natural Language Inference verification pairs.

    Each record represents a single premise-hypothesis pair processed through
    the NLI model (e.g., microsoft/deberta-v3-base).
    """

    __tablename__ = "nli_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to claim being verified
    claim_id = Column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )

    # Link to evidence used as premise
    evidence_id = Column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )

    # NLI prediction results
    label = Column(String(20), nullable=False)  # 'ENTAILMENT', 'CONTRADICTION', 'NEUTRAL'
    confidence = Column(Float, nullable=False)  # Probability of predicted label (0-1)

    # All three class scores for transparency
    entailment_score = Column(Float, nullable=False)
    contradiction_score = Column(Float, nullable=False)
    neutral_score = Column(Float, nullable=False)

    # Model metadata
    model_name = Column(String(100), nullable=False, default="microsoft/deberta-v3-base")
    model_version = Column(String(50), nullable=True)

    # Text inputs (stored for auditability)
    premise_text = Column(Text, nullable=False)  # Evidence content
    hypothesis_text = Column(Text, nullable=False)  # Claim text

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for claim-based lookups
        Index("idx_nli_results_claim_id", claim_id),
        # Index for evidence-based lookups
        Index("idx_nli_results_evidence_id", evidence_id),
        # Composite index for quick pair lookups
        Index("idx_nli_results_claim_evidence", claim_id, evidence_id),
        # Index for filtering by label
        Index("idx_nli_results_label", label),
    )


class VerificationResult(Base):
    """Verification Results table - stores aggregated verdicts from NLI pipeline.

    This table contains the final verdict after aggregating multiple NLI results
    for a given claim. One claim can have multiple verification results over time.
    """

    __tablename__ = "verification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to claim being verified
    claim_id = Column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )

    # Final aggregated verdict
    verdict = Column(String(20), nullable=False)  # 'SUPPORTED', 'REFUTED', 'INSUFFICIENT'
    confidence = Column(Float, nullable=False)  # Overall confidence (0-1)

    # Aggregated scores from NLI results
    support_score = Column(Float, nullable=False)  # Weighted entailment score
    refute_score = Column(Float, nullable=False)  # Weighted contradiction score
    neutral_score = Column(Float, nullable=False)  # Weighted neutral score

    # Evidence statistics
    evidence_count = Column(Integer, nullable=False)  # Number of evidence items analyzed
    supporting_evidence_count = Column(Integer, nullable=False, default=0)
    refuting_evidence_count = Column(Integer, nullable=False, default=0)
    neutral_evidence_count = Column(Integer, nullable=False, default=0)

    # Human-readable explanation
    reasoning = Column(Text, nullable=True)

    # NLI result IDs used in this verification (for traceability)
    nli_result_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Pipeline metadata
    pipeline_version = Column(String(50), nullable=True)
    retrieval_method = Column(String(50), nullable=True)  # 'vector', 'hybrid', 'keyword'

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for claim-based lookups
        Index("idx_verification_results_claim_id", claim_id),
        # Index for filtering by verdict
        Index("idx_verification_results_verdict", verdict),
        # Index for sorting by confidence
        Index("idx_verification_results_confidence", confidence.desc()),
        # Index for time-based queries
        Index("idx_verification_results_created_at", created_at.desc()),
    )
