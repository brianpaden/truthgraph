"""Phase 2: Add ML-enhanced verification tables (embeddings, NLI results, verification results)

Revision ID: phase2_ml_tables
Revises:
Create Date: 2025-10-25 00:00:00.000000

This migration adds three new tables to support ML-based verification:
1. embeddings - Vector embeddings for semantic search (1536-dim)
2. nli_results - Natural Language Inference verification pairs
3. verification_results - Aggregated verdicts from NLI pipeline

Key features:
- pgvector extension for efficient similarity search
- IVFFlat index for vector operations
- Comprehensive indexing for query performance
- Tenant isolation support
- Full audit trail with timestamps
"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase2_ml_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add Phase 2 ML tables."""

    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. Create embeddings table
    op.create_table(
        "embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "entity_type",
            sa.String(20),
            nullable=False,
            comment="Type of entity: evidence or claim",
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="ID of the entity being embedded",
        ),
        sa.Column(
            "embedding",
            Vector(384),
            nullable=False,
            comment="Vector embedding (384-dim for all-MiniLM-L6-v2)",
        ),
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=False,
            server_default="all-MiniLM-L6-v2",
            comment="Name of the embedding model used",
        ),
        sa.Column(
            "model_version", sa.String(50), nullable=True, comment="Version of the embedding model"
        ),
        sa.Column(
            "tenant_id",
            sa.String(255),
            nullable=False,
            server_default="default",
            comment="Tenant ID for multi-tenancy isolation",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        comment="Stores vector embeddings for evidence and claims with pgvector support",
    )

    # Create indexes for embeddings table
    op.create_index("idx_embeddings_tenant_id", "embeddings", ["tenant_id"])
    op.create_index("idx_embeddings_entity", "embeddings", ["entity_type", "entity_id"])
    op.create_index(
        "idx_embeddings_entity_unique", "embeddings", ["entity_type", "entity_id"], unique=True
    )

    # Create IVFFlat index for vector similarity search (cosine distance)
    # Lists parameter = 100 is a good starting point (adjust based on corpus size)
    # Use ~sqrt(total_rows) for optimal performance
    op.execute("""
        CREATE INDEX idx_embeddings_vector_cosine
        ON embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # Create trigger for updated_at timestamp on embeddings
    op.execute("""
        CREATE TRIGGER update_embeddings_updated_at
        BEFORE UPDATE ON embeddings
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)

    # 2. Create nli_results table
    op.create_table(
        "nli_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
            comment="Claim being verified",
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            nullable=False,
            comment="Evidence used as premise",
        ),
        sa.Column(
            "label",
            sa.String(20),
            nullable=False,
            comment="NLI prediction: ENTAILMENT, CONTRADICTION, or NEUTRAL",
        ),
        sa.Column(
            "confidence", sa.Float(), nullable=False, comment="Probability of predicted label (0-1)"
        ),
        sa.Column(
            "entailment_score", sa.Float(), nullable=False, comment="Score for ENTAILMENT class"
        ),
        sa.Column(
            "contradiction_score",
            sa.Float(),
            nullable=False,
            comment="Score for CONTRADICTION class",
        ),
        sa.Column("neutral_score", sa.Float(), nullable=False, comment="Score for NEUTRAL class"),
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=False,
            server_default="microsoft/deberta-v3-base",
            comment="NLI model used",
        ),
        sa.Column("model_version", sa.String(50), nullable=True, comment="Model version"),
        sa.Column("premise_text", sa.Text(), nullable=False, comment="Evidence content (premise)"),
        sa.Column("hypothesis_text", sa.Text(), nullable=False, comment="Claim text (hypothesis)"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        comment="Stores Natural Language Inference results for claim-evidence pairs",
    )

    # Create indexes for nli_results table
    op.create_index("idx_nli_results_claim_id", "nli_results", ["claim_id"])
    op.create_index("idx_nli_results_evidence_id", "nli_results", ["evidence_id"])
    op.create_index("idx_nli_results_claim_evidence", "nli_results", ["claim_id", "evidence_id"])
    op.create_index("idx_nli_results_label", "nli_results", ["label"])

    # 3. Create verification_results table
    op.create_table(
        "verification_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
            comment="Claim being verified",
        ),
        sa.Column(
            "verdict",
            sa.String(20),
            nullable=False,
            comment="Final verdict: SUPPORTED, REFUTED, or INSUFFICIENT",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, comment="Overall confidence (0-1)"),
        sa.Column("support_score", sa.Float(), nullable=False, comment="Weighted entailment score"),
        sa.Column(
            "refute_score", sa.Float(), nullable=False, comment="Weighted contradiction score"
        ),
        sa.Column("neutral_score", sa.Float(), nullable=False, comment="Weighted neutral score"),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
            comment="Number of evidence items analyzed",
        ),
        sa.Column(
            "supporting_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Count of supporting evidence",
        ),
        sa.Column(
            "refuting_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Count of refuting evidence",
        ),
        sa.Column(
            "neutral_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Count of neutral evidence",
        ),
        sa.Column(
            "reasoning",
            sa.Text(),
            nullable=True,
            comment="Human-readable explanation of the verdict",
        ),
        sa.Column(
            "nli_result_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
            comment="Array of NLI result IDs used",
        ),
        sa.Column(
            "pipeline_version",
            sa.String(50),
            nullable=True,
            comment="Version of the verification pipeline",
        ),
        sa.Column(
            "retrieval_method",
            sa.String(50),
            nullable=True,
            comment="Retrieval method: vector, hybrid, or keyword",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        comment="Stores aggregated verification results from NLI pipeline",
    )

    # Create indexes for verification_results table
    op.create_index("idx_verification_results_claim_id", "verification_results", ["claim_id"])
    op.create_index("idx_verification_results_verdict", "verification_results", ["verdict"])
    op.create_index(
        "idx_verification_results_confidence", "verification_results", [sa.text("confidence DESC")]
    )
    op.create_index(
        "idx_verification_results_created_at", "verification_results", [sa.text("created_at DESC")]
    )

    # Create trigger for updated_at timestamp on verification_results
    op.execute("""
        CREATE TRIGGER update_verification_results_updated_at
        BEFORE UPDATE ON verification_results
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Downgrade database schema - remove Phase 2 ML tables."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("verification_results")
    op.drop_table("nli_results")
    op.drop_table("embeddings")

    # Note: We don't drop the pgvector extension as it might be used by other tables
    # If you need to drop it completely: op.execute('DROP EXTENSION IF EXISTS vector')
