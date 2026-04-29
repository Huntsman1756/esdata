"""baseline schema

# Revision ID: 20260416_0001
# Revises: None
# Create Date: 2026-04-16 12:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS pg_trgm"
    )

    op.execute(
        """
        CREATE TABLE norma (
            id SERIAL PRIMARY KEY,
            codigo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            boe_id TEXT UNIQUE NOT NULL,
            eli_uri TEXT UNIQUE,
            jurisdiccion TEXT NOT NULL,
            tipo_fuente TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            ambito TEXT NOT NULL,
            estado_cobertura TEXT NOT NULL,
            vigente_desde DATE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE articulo (
            id SERIAL PRIMARY KEY,
            norma_id INTEGER NOT NULL REFERENCES norma(id),
            numero TEXT NOT NULL,
            titulo TEXT,
            tipo TEXT NOT NULL,
            UNIQUE (norma_id, numero)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE version_articulo (
            id SERIAL PRIMARY KEY,
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            texto TEXT NOT NULL,
            vigente_desde DATE NOT NULL,
            vigente_hasta DATE,
            boe_bloque_id TEXT,
            search_vector TSVECTOR
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documento_interpretativo (
            id SERIAL PRIMARY KEY,
            tipo_documento TEXT NOT NULL,
            organismo_emisor TEXT NOT NULL,
            jurisdiccion TEXT NOT NULL,
            tipo_fuente TEXT NOT NULL,
            ambito TEXT NOT NULL,
            referencia TEXT UNIQUE NOT NULL,
            fecha DATE NOT NULL,
            titulo TEXT,
            texto TEXT NOT NULL,
            url_fuente TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE empresa (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            nif TEXT,
            domicilio TEXT,
            fuente_inicial TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (nombre)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE obligacion_regulatoria (
            id SERIAL PRIMARY KEY,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            fuente TEXT NOT NULL,
            organismo_emisor TEXT NOT NULL,
            tipo_obligacion TEXT NOT NULL,
            sujeto_obligado TEXT NOT NULL,
            periodicidad TEXT,
            reporte_modelo TEXT,
            ambito TEXT NOT NULL,
            estado_vigencia TEXT NOT NULL,
            documento_origen_tipo TEXT NOT NULL,
            documento_origen_ref TEXT NOT NULL,
            seccion_origen TEXT,
            anexo_origen TEXT,
            nota TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE obligacion_documento (
            obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id),
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            tipo_relacion TEXT NOT NULL,
            PRIMARY KEY (obligacion_id, documento_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documento_empresa (
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            rol TEXT NOT NULL,
            confianza_extraccion NUMERIC(3,2) NOT NULL,
            nota TEXT,
            PRIMARY KEY (documento_id, empresa_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documento_articulo (
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            metodo_enlace TEXT NOT NULL,
            confianza_enlace NUMERIC(3,2) NOT NULL,
            nota TEXT,
            PRIMARY KEY (documento_id, articulo_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE materia (
            id SERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            etiqueta TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE articulo_materia (
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            materia_id INTEGER NOT NULL REFERENCES materia(id),
            relevancia SMALLINT NOT NULL DEFAULT 1,
            PRIMARY KEY (articulo_id, materia_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sync_log (
            id SERIAL PRIMARY KEY,
            worker TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL,
            bloques_processed INTEGER,
            articulos_upserted INTEGER,
            documentos_processed INTEGER,
            documentos_upserted INTEGER,
            doctrina_links_created INTEGER,
            error_msg TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE aeat_modelo (
            id SERIAL PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            periodo TEXT,
            impuesto TEXT,
            url_info TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_articulo (
            modelo_id INTEGER REFERENCES aeat_modelo(id) ON DELETE CASCADE,
            articulo_id INTEGER REFERENCES articulo(id) ON DELETE CASCADE,
            casilla TEXT,
            nota TEXT,
            fuente TEXT NOT NULL,
            url_fuente TEXT,
            PRIMARY KEY (modelo_id, articulo_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_campana (
            id SERIAL PRIMARY KEY,
            modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
            campana TEXT NOT NULL,
            version_form TEXT,
            url_instrucciones TEXT,
            url_normativa TEXT,
            url_formato TEXT,
            activo BOOLEAN NOT NULL DEFAULT true,
            creado_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(modelo_id, campana)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_casilla (
            id SERIAL PRIMARY KEY,
            campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
            codigo TEXT NOT NULL,
            etiqueta TEXT NOT NULL,
            descripcion TEXT,
            tipo_casilla TEXT,
            pagina INTEGER,
            orden INTEGER,
            activa BOOLEAN NOT NULL DEFAULT true,
            creado_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(campana_id, codigo)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_clave (
            id SERIAL PRIMARY KEY,
            campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
            codigo TEXT NOT NULL,
            etiqueta TEXT NOT NULL,
            descripcion TEXT,
            tipo_clave TEXT,
            activa BOOLEAN NOT NULL DEFAULT true,
            creado_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(campana_id, codigo)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_instruccion (
            id SERIAL PRIMARY KEY,
            campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
            seccion TEXT NOT NULL,
            titulo TEXT NOT NULL,
            contenido TEXT NOT NULL,
            orden INTEGER DEFAULT 0,
            creado_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_normativa (
            id SERIAL PRIMARY KEY,
            modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
            boe_id TEXT,
            titulo TEXT NOT NULL,
            fecha DATE,
            url_boe TEXT,
            resumen TEXT,
            creado_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(modelo_id, boe_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE modelo_formato (
            id SERIAL PRIMARY KEY,
            campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
            tipo_registro TEXT NOT NULL,
            campos JSONB,
            url_diseno TEXT,
            creado_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_version_articulo_texto_trgm ON version_articulo USING gin (texto gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_version_articulo_search_vector ON version_articulo USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articulo_titulo_trgm ON articulo USING GIN (titulo gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_campana_modelo ON modelo_campana(modelo_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_campana_unique_active ON modelo_campana(modelo_id) WHERE activo = true"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_casilla_campana ON modelo_casilla(campana_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_clave_campana ON modelo_clave(campana_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_instruccion_campana ON modelo_instruccion(campana_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_instruccion_unique ON modelo_instruccion(campana_id, seccion, titulo)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_normativa_modelo ON modelo_normativa(modelo_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_modelo_formato_campana ON modelo_formato(campana_id)"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_version_articulo_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.texto, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_version_articulo_search_vector ON version_articulo"
    )
    op.execute(
        """
        CREATE TRIGGER trg_version_articulo_search_vector
        BEFORE INSERT OR UPDATE OF texto ON version_articulo
        FOR EACH ROW
        EXECUTE FUNCTION update_version_articulo_search_vector()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION modelo_campana_activa(p_modelo_id INTEGER)
        RETURNS TABLE (
            id INTEGER,
            campana TEXT,
            url_instrucciones TEXT,
            url_normativa TEXT,
            url_formato TEXT
        ) AS $$
            SELECT id, campana, url_instrucciones, url_normativa, url_formato
            FROM modelo_campana
            WHERE modelo_id = p_modelo_id AND activo = true
            ORDER BY campana DESC
            LIMIT 1;
        $$ LANGUAGE sql STABLE
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Baseline migration is not reversible. Restore from backup for full rollback."
    )
