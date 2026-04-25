-- Migration: Add pgvector extension and embedding columns
-- Phase 5: Hybrid search (RRF with hybrid_weight)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding columns to tables that need them
ALTER TABLE version_articulo ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE documento_fragmento ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Create HNSW indexes for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_version_articulo_embedding ON version_articulo USING hnsw (embedding vector_ip_ops);
CREATE INDEX IF NOT EXISTS idx_documento_fragmento_embedding ON documento_fragmento USING hnsw (embedding vector_ip_ops);
CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_embedding ON documento_interpretativo USING hnsw (embedding vector_ip_ops);
