-- Modelos AEAT y su relación con artículos legislativos
-- Fase 1: estructura base + top 6 modelos
-- Cada relación modelo_articulo requiere fuente oficial explícita.

CREATE TABLE aeat_modelo (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,        -- '100', '303', etc.
    nombre TEXT NOT NULL,               -- 'IRPF Declaración anual'
    periodo TEXT,                       -- 'anual', 'trimestral', 'mensual'
    impuesto TEXT,                      -- 'IRPF', 'IVA', 'IS'
    url_info TEXT,                      -- enlace a página AEAT del modelo
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE modelo_articulo (
    modelo_id INTEGER REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    articulo_id INTEGER REFERENCES articulo(id) ON DELETE CASCADE,
    casilla TEXT,                       -- '0002', '0416', etc.
    nota TEXT,                          -- contexto breve de la relación
    fuente TEXT NOT NULL,               -- 'Instrucción Modelo 100 2025'
    url_fuente TEXT,                    -- URL directa a la fuente
    PRIMARY KEY (modelo_id, articulo_id)
);
