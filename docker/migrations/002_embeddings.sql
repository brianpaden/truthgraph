-- Migration 002: Embeddings for Vector Search
-- Creates embeddings table with pgvector for semantic search
-- Supports both evidence and claim embeddings (polymorphic design)
-- Default: 1536-dimensional embeddings (text-embedding-3-small)
-- Alternative: 384-dimensional embeddings (all-MiniLM-L6-v2) - update Vector(384) if using

-- Create embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Polymorphic relationship - can embed evidence or claims
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('evidence', 'claim')),
    entity_id UUID NOT NULL,

    -- Vector embedding (1536 dimensions for text-embedding-3-small)
    -- Change to VECTOR(384) if using all-MiniLM-L6-v2
    embedding VECTOR(1536),

    -- Model metadata
    model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    model_version VARCHAR(50),

    -- Tenant isolation for multi-tenancy support
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
-- Tenant isolation index
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant_id
    ON embeddings(tenant_id);

-- Composite index for entity lookups
CREATE INDEX IF NOT EXISTS idx_embeddings_entity
    ON embeddings(entity_type, entity_id);

-- Unique constraint to prevent duplicate embeddings
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_entity_unique
    ON embeddings(entity_type, entity_id);

-- IVFFlat index for fast approximate nearest neighbor search
-- lists=100 is a good starting point for 10k-100k vectors
-- Adjust based on corpus size: lists ≈ sqrt(total_rows)
-- For >100k vectors, use lists=500-1000
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_similarity
    ON embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Add trigger for updated_at timestamp
CREATE TRIGGER update_embeddings_updated_at
    BEFORE UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE embeddings IS
    'Stores vector embeddings for evidence and claims to enable semantic similarity search using pgvector cosine distance';

COMMENT ON COLUMN embeddings.entity_type IS
    'Type of entity: evidence or claim';

COMMENT ON COLUMN embeddings.embedding IS
    'Vector embedding from ML model. Default: 1536-dim (text-embedding-3-small). Alternative: 384-dim (all-MiniLM-L6-v2)';

COMMENT ON INDEX idx_embeddings_vector_similarity IS
    'IVFFlat index for approximate nearest neighbor search. Tune lists parameter based on corpus size. Use SET ivfflat.probes = N at query time for accuracy/speed tradeoff.';

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 002: embeddings table created successfully';
END $$;
