-- 006_pgvector.sql — Vector embeddings for semantic search
-- Requires: pgvector extension (pgvector/pgvector:pg16 image)

CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding columns (384-dim for paraphrase-multilingual-MiniLM-L12-v2)
ALTER TABLE version_articulo
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- documento_fragmento may not exist yet (created by migration 0005)
-- Only add embedding if the table exists (post-migration)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documento_fragmento') THEN
        ALTER TABLE documento_fragmento ADD COLUMN IF NOT EXISTS embedding vector(384);
    END IF;
END $$;

ALTER TABLE documento_interpretativo
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- HNSW indexes for vector similarity search
-- m=16, ef_construction=64: good balance of build speed and query accuracy
CREATE INDEX IF NOT EXISTS idx_version_articulo_embedding
    ON version_articulo USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- documento_fragmento index (only if table+column exist)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documento_fragmento' AND column_name = 'embedding'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_embedding
            ON documento_fragmento USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_embedding
    ON documento_interpretativo USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
