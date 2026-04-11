CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE version_articulo
ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

UPDATE version_articulo
SET search_vector = to_tsvector('spanish', COALESCE(texto, ''));

CREATE INDEX IF NOT EXISTS idx_version_articulo_search_vector
    ON version_articulo USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_articulo_titulo_trgm
    ON articulo USING GIN (titulo gin_trgm_ops);

CREATE OR REPLACE FUNCTION update_version_articulo_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.texto, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_version_articulo_search_vector ON version_articulo;

CREATE TRIGGER trg_version_articulo_search_vector
BEFORE INSERT OR UPDATE OF texto ON version_articulo
FOR EACH ROW
EXECUTE FUNCTION update_version_articulo_search_vector();
