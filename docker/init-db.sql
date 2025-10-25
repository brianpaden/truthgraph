-- TruthGraph v0 Database Initialization
-- PostgreSQL 15+ with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create claims table
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    source_url TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create evidence table
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50),  -- 'document', 'article', 'manual_entry', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create verdicts table
CREATE TABLE IF NOT EXISTS verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    verdict VARCHAR(20),  -- 'SUPPORTED', 'REFUTED', 'INSUFFICIENT', NULL for pending
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create verdict_evidence junction table
CREATE TABLE IF NOT EXISTS verdict_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verdict_id UUID NOT NULL REFERENCES verdicts(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relationship VARCHAR(20),  -- 'supports', 'refutes', 'neutral'
    confidence FLOAT,
    UNIQUE(verdict_id, evidence_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_claims_submitted_at ON claims(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON evidence(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verdicts_claim_id ON verdicts(claim_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_created_at ON verdicts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verdict_evidence_verdict_id ON verdict_evidence(verdict_id);

-- Create trigger function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for automatic updated_at management
CREATE TRIGGER update_claims_updated_at BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_verdicts_updated_at BEFORE UPDATE ON verdicts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'TruthGraph v0 database initialized successfully';
END $$;
