CREATE TABLE IF NOT EXISTS documento_seccion (
    id SERIAL PRIMARY KEY,
    documento_origen_tipo TEXT NOT NULL,
    documento_origen_id INTEGER NOT NULL,
    tipo_seccion TEXT NOT NULL,
    numero TEXT,
    titulo TEXT,
    nivel INTEGER DEFAULT 0,
    orden INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documento_seccion_origen ON documento_seccion(documento_origen_tipo, documento_origen_id);
CREATE INDEX IF NOT EXISTS idx_documento_seccion_tipo ON documento_seccion(tipo_seccion);

CREATE TABLE IF NOT EXISTS documento_fragmento (
    id SERIAL PRIMARY KEY,
    documento_origen_tipo TEXT NOT NULL,
    documento_origen_id INTEGER NOT NULL,
    seccion_id INTEGER,
    chunk_index INTEGER NOT NULL,
    chunk_type TEXT NOT NULL DEFAULT 'natural',
    titulo TEXT,
    texto TEXT NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    token_count INTEGER,
    search_vector TSVECTOR,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(documento_origen_tipo, documento_origen_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_documento_fragmento_origen ON documento_fragmento(documento_origen_tipo, documento_origen_id);
CREATE INDEX IF NOT EXISTS idx_documento_fragmento_seccion ON documento_fragmento(seccion_id);
CREATE INDEX IF NOT EXISTS idx_documento_fragmento_chunk_type ON documento_fragmento(chunk_type);
CREATE INDEX IF NOT EXISTS idx_documento_fragmento_search_vector ON documento_fragmento USING GIN (search_vector);

CREATE OR REPLACE FUNCTION update_documento_fragmento_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.titulo, '') || ' ' || NEW.texto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_documento_fragmento_search_vector ON documento_fragmento;
CREATE TRIGGER trg_documento_fragmento_search_vector
    BEFORE INSERT OR UPDATE OF texto, titulo ON documento_fragmento
    FOR EACH ROW EXECUTE FUNCTION update_documento_fragmento_search_vector();
