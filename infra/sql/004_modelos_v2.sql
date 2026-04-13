-- Modelos AEAT v2: versionado por campaña, casillas, claves, instrucciones, normativa, formato
-- Aplicar tras 003_modelos_aeat.sql
-- Cada modelo puede tener múltiples campañas (2024, 2025, etc.) con casillas/claves/instrucciones distintas.

-- ---------------------------------------------------------------------------
-- 1. CAMPAÑAS — cada modelo puede tener N versiones por año/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_campana (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    campana         TEXT NOT NULL,              -- '2025', '2024', 'T1-2025', etc.
    version_form    TEXT,                       -- '1.0', '1.1' — versión del diseño
    url_instrucciones TEXT,                     -- PDF instrucciones AEAT
    url_normativa   TEXT,                       -- BOE/Orden que aprueba el modelo
    url_formato     TEXT,                       —- diseño de registro electrónico
    activo          BOOLEAN NOT NULL DEFAULT true,  -- false = campaña obsoleta
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(modelo_id, campana)
);

CREATE INDEX idx_modelo_campana_modelo ON modelo_campana(modelo_id);

-- ---------------------------------------------------------------------------
-- 2. CASILLAS — inventario completo de casillas por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_casilla (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    codigo          TEXT NOT NULL,              -- '0002', '0416', '01', etc.
    etiqueta        TEXT NOT NULL,              -- 'Rendimientos del trabajo'
    descripcion     TEXT,                       -- explicación breve
    tipo_casilla    TEXT,                       -- 'importe', 'checkbox', 'texto', 'numero', 'seccion'
    pagina          INTEGER,                    -- página del PDF donde aparece
    orden           INTEGER,                    -- orden de aparición en el modelo
    activa          BOOLEAN NOT NULL DEFAULT true,  -- false = casilla eliminada en esta campaña
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campana_id, codigo)
);

CREATE INDEX idx_modelo_casilla_campana ON modelo_casilla(campana_id);

-- ---------------------------------------------------------------------------
-- 3. CLAVES — códigos de rendimiento/régimen/etc. por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_clave (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    codigo          TEXT NOT NULL,              -- '01', '02', 'A', 'B', etc.
    etiqueta        TEXT NOT NULL,              -- 'Rendimientos del trabajo'
    descripcion     TEXT,                       -- explicación de la clave
    tipo_clave      TEXT,                       -- 'rendimiento', 'regimen', 'tipo_retencion', etc.
    activa          BOOLEAN NOT NULL DEFAULT true,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campana_id, codigo)
);

CREATE INDEX idx_modelo_clave_campana ON modelo_clave(campana_id);

-- ---------------------------------------------------------------------------
-- 4. INSTRUCCIONES — contenido paso a paso por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_instruccion (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    seccion         TEXT NOT NULL,              -- 'caracteristicas', 'quien-debe', 'como-rellenar', 'plazo'
    titulo          TEXT NOT NULL,
    contenido       TEXT NOT NULL,              -- Markdown/HTML del contenido
    orden           INTEGER DEFAULT 0,          -- orden de presentación
    creado_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_modelo_instruccion_campana ON modelo_instruccion(campana_id);

-- ---------------------------------------------------------------------------
-- 5. NORMATIVA — órdenes BOE que regulan cada modelo (independiente de campaña)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_normativa (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    boe_id          TEXT,                       -- 'BOE-A-2024-1772'
    titulo          TEXT NOT NULL,              -- 'Orden HAC/1234/2024'
    fecha           DATE,
    url_boe         TEXT,                       -- enlace al BOE
    resumen         TEXT,                       -- breve descripción
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(modelo_id, boe_id)
);

CREATE INDEX idx_modelo_normativa_modelo ON modelo_normativa(modelo_id);

-- ---------------------------------------------------------------------------
-- 6. FORMATO — especificaciones de diseño de registro por campaña
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_formato (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    tipo_registro   TEXT NOT NULL,              -- 'declarante', 'perceptor', 'detalle'
    campos          JSONB,                      -- array de {nombre, tipo, longitud, posicion}
    url_diseno      TEXT,                       -- enlace al diseño de registro AEAT
    creado_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_modelo_formato_campana ON modelo_formato(campana_id);

-- ---------------------------------------------------------------------------
-- 7. VISTA: modelo_casilla_articulo — vincula casillas con artículos
-- ---------------------------------------------------------------------------
-- Esta vista junta modelo_casilla con modelo_articulo para que la API
-- pueda devolver casilla + artículo + normativa de un golpe.
-- La relación se hace via (modelo_id, casilla_codigo) cruzando con modelo_articulo.casilla.

-- ---------------------------------------------------------------------------
-- 8. CAMPAÑA ACTIVA POR DEFECTO
-- ---------------------------------------------------------------------------
-- Helper: función para obtener la campaña activa más reciente de un modelo
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
$$ LANGUAGE sql STABLE;
