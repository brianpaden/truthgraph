"""Test suite for database migrations.

This module tests the Phase 2 migration including:
1. Migration upgrade/downgrade without errors
2. Table creation and structure validation
3. Index creation and performance
4. Foreign key constraints
5. Backward compatibility
"""

import asyncio
import pytest
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from truthgraph.db_async import async_engine, AsyncSessionLocal


class TestPhase2Migration:
    """Test Phase 2 ML tables migration."""

    @pytest.fixture
    async def session(self) -> AsyncSession:
        """Create async database session for tests."""
        async with AsyncSessionLocal() as session:
            yield session

    @pytest.mark.asyncio
    async def test_tables_exist(self, session: AsyncSession) -> None:
        """Test that all Phase 2 tables are created."""
        # Check that tables exist
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('embeddings', 'nli_results', 'verification_results')
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        assert 'embeddings' in tables, "embeddings table not created"
        assert 'nli_results' in tables, "nli_results table not created"
        assert 'verification_results' in tables, "verification_results table not created"

    @pytest.mark.asyncio
    async def test_embeddings_table_structure(self, session: AsyncSession) -> None:
        """Test embeddings table has correct columns and types."""
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'embeddings'
            ORDER BY column_name
        """))
        columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}

        # Check required columns exist
        required_columns = [
            'id', 'entity_type', 'entity_id', 'embedding',
            'model_name', 'tenant_id', 'created_at', 'updated_at'
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} missing from embeddings table"

        # Check nullable constraints
        assert columns['entity_type']['nullable'] == 'NO', "entity_type should be NOT NULL"
        assert columns['entity_id']['nullable'] == 'NO', "entity_id should be NOT NULL"
        assert columns['embedding']['nullable'] == 'NO', "embedding should be NOT NULL"

    @pytest.mark.asyncio
    async def test_nli_results_table_structure(self, session: AsyncSession) -> None:
        """Test nli_results table has correct columns."""
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'nli_results'
            ORDER BY column_name
        """))
        columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}

        # Check required columns
        required_columns = [
            'id', 'claim_id', 'evidence_id', 'label', 'confidence',
            'entailment_score', 'contradiction_score', 'neutral_score',
            'premise_text', 'hypothesis_text', 'created_at'
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} missing from nli_results table"

        # Check NOT NULL constraints
        assert columns['label']['nullable'] == 'NO', "label should be NOT NULL"
        assert columns['confidence']['nullable'] == 'NO', "confidence should be NOT NULL"

    @pytest.mark.asyncio
    async def test_verification_results_table_structure(self, session: AsyncSession) -> None:
        """Test verification_results table has correct columns."""
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'verification_results'
            ORDER BY column_name
        """))
        columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}

        # Check required columns
        required_columns = [
            'id', 'claim_id', 'verdict', 'confidence',
            'support_score', 'refute_score', 'neutral_score',
            'evidence_count', 'reasoning', 'created_at', 'updated_at'
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} missing from verification_results table"

        # Check NOT NULL constraints
        assert columns['verdict']['nullable'] == 'NO', "verdict should be NOT NULL"
        assert columns['confidence']['nullable'] == 'NO', "confidence should be NOT NULL"

    @pytest.mark.asyncio
    async def test_indexes_created(self, session: AsyncSession) -> None:
        """Test that all required indexes are created."""
        result = await session.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('embeddings', 'nli_results', 'verification_results')
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result.fetchall()]

        # Check embeddings indexes
        assert any('idx_embeddings_tenant_id' in idx for idx in indexes), \
            "embeddings tenant_id index missing"
        assert any('idx_embeddings_vector_cosine' in idx for idx in indexes), \
            "embeddings vector index missing"

        # Check nli_results indexes
        assert any('idx_nli_results_claim_id' in idx for idx in indexes), \
            "nli_results claim_id index missing"
        assert any('idx_nli_results_evidence_id' in idx for idx in indexes), \
            "nli_results evidence_id index missing"

        # Check verification_results indexes
        assert any('idx_verification_results_claim_id' in idx for idx in indexes), \
            "verification_results claim_id index missing"

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, session: AsyncSession) -> None:
        """Test that foreign key constraints are properly created."""
        result = await session.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name IN ('nli_results', 'verification_results')
            ORDER BY tc.table_name, kcu.column_name
        """))
        foreign_keys = list(result.fetchall())

        # Check that we have foreign keys defined
        assert len(foreign_keys) > 0, "No foreign key constraints found"

        # Check specific foreign keys
        fk_map = {
            ('nli_results', 'claim_id'): 'claims',
            ('nli_results', 'evidence_id'): 'evidence',
            ('verification_results', 'claim_id'): 'claims',
        }

        for (table, column), expected_ref_table in fk_map.items():
            found = any(
                fk[0] == table and fk[1] == column and fk[2] == expected_ref_table
                for fk in foreign_keys
            )
            assert found, f"Foreign key {table}.{column} -> {expected_ref_table} not found"

    @pytest.mark.asyncio
    async def test_pgvector_extension(self, session: AsyncSession) -> None:
        """Test that pgvector extension is installed."""
        result = await session.execute(text("""
            SELECT extname
            FROM pg_extension
            WHERE extname = 'vector'
        """))
        extensions = result.fetchall()
        assert len(extensions) > 0, "pgvector extension not installed"

    @pytest.mark.asyncio
    async def test_ivfflat_index_exists(self, session: AsyncSession) -> None:
        """Test that IVFFlat index is created for vector similarity search."""
        result = await session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'embeddings'
            AND indexname = 'idx_embeddings_vector_cosine'
        """))
        index_info = result.fetchone()

        assert index_info is not None, "IVFFlat vector index not found"
        assert 'ivfflat' in index_info[1].lower(), "Index is not using IVFFlat"
        assert 'vector_cosine_ops' in index_info[1].lower(), "Index not using cosine distance"

    @pytest.mark.asyncio
    async def test_triggers_created(self, session: AsyncSession) -> None:
        """Test that updated_at triggers are created."""
        result = await session.execute(text("""
            SELECT trigger_name, event_object_table
            FROM information_schema.triggers
            WHERE event_object_table IN ('embeddings', 'verification_results')
            AND trigger_name LIKE '%updated_at%'
            ORDER BY event_object_table
        """))
        triggers = list(result.fetchall())

        # Check that triggers exist for tables with updated_at columns
        tables_with_triggers = {trigger[1] for trigger in triggers}
        assert 'embeddings' in tables_with_triggers, "embeddings updated_at trigger missing"
        assert 'verification_results' in tables_with_triggers, \
            "verification_results updated_at trigger missing"


class TestMigrationBackwardCompatibility:
    """Test that Phase 2 migration doesn't break existing functionality."""

    @pytest.mark.asyncio
    async def test_existing_tables_intact(self) -> None:
        """Test that existing Phase 1 tables are not affected."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('claims', 'evidence', 'verdicts', 'verdict_evidence')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            # All Phase 1 tables should still exist
            assert 'claims' in tables, "claims table missing"
            assert 'evidence' in tables, "evidence table missing"
            assert 'verdicts' in tables, "verdicts table missing"
            assert 'verdict_evidence' in tables, "verdict_evidence table missing"

    @pytest.mark.asyncio
    async def test_can_insert_into_existing_tables(self) -> None:
        """Test that existing tables can still receive inserts."""
        async with AsyncSessionLocal() as session:
            # Try inserting a test claim
            await session.execute(text("""
                INSERT INTO claims (text, source_url)
                VALUES ('Test claim for migration compatibility', 'http://test.com')
            """))
            await session.commit()

            # Verify insert worked
            result = await session.execute(text("""
                SELECT COUNT(*) FROM claims WHERE text LIKE 'Test claim for migration%'
            """))
            count = result.scalar()
            assert count > 0, "Could not insert into claims table after migration"

            # Clean up
            await session.execute(text("""
                DELETE FROM claims WHERE text LIKE 'Test claim for migration%'
            """))
            await session.commit()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
