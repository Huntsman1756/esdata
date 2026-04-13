import os
from pathlib import Path

from sqlalchemy import create_engine, text

TEST_DB_PATH = Path(__file__).resolve().parent / "test_esdata.sqlite3"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)

STATEMENTS = [
    """
    CREATE TABLE norma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        boe_id TEXT UNIQUE NOT NULL,
        eli_uri TEXT UNIQUE,
        jurisdiccion TEXT NOT NULL,
        tipo_fuente TEXT NOT NULL,
        tipo_documento TEXT NOT NULL,
        ambito TEXT NOT NULL,
        estado_cobertura TEXT NOT NULL,
        vigente_desde TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        norma_id INTEGER NOT NULL REFERENCES norma(id),
        numero TEXT NOT NULL,
        titulo TEXT,
        tipo TEXT NOT NULL,
        UNIQUE (norma_id, numero)
    )
    """,
    """
    CREATE TABLE version_articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        texto TEXT NOT NULL,
        vigente_desde TEXT NOT NULL,
        vigente_hasta TEXT,
        boe_bloque_id TEXT
    )
    """,
    """
    CREATE TABLE documento_interpretativo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_documento TEXT NOT NULL,
        organismo_emisor TEXT NOT NULL,
        jurisdiccion TEXT NOT NULL,
        tipo_fuente TEXT NOT NULL,
        ambito TEXT NOT NULL,
        referencia TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        titulo TEXT,
        texto TEXT NOT NULL,
        url_fuente TEXT
    )
    """,
    """
    CREATE TABLE documento_articulo (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        metodo_enlace TEXT NOT NULL,
        confianza_enlace REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, articulo_id)
    )
    """,
    """
    CREATE TABLE materia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        etiqueta TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE articulo_materia (
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        materia_id INTEGER NOT NULL REFERENCES materia(id),
        relevancia INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (articulo_id, materia_id)
    )
    """,
    """
    CREATE TABLE sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        bloques_processed INTEGER,
        articulos_upserted INTEGER,
        documentos_processed INTEGER,
        documentos_upserted INTEGER,
        doctrina_links_created INTEGER,
        error_msg TEXT
    )
    """,
    # --- Normas (metadatos de referencia) ---
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740',
        'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe',
        'ley', 'tributario', 'ingestada', '1993-01-01'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'ITPAJD',
        'Texto refundido del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados',
        'BOE-A-1993-253',
        'https://www.boe.es/eli/es/rdlg/1993/09/24/1/con',
        'es',
        'boe',
        'real_decreto_legislativo',
        'tributario',
        'ingestada',
        '1993-09-25'
    )
    """,
    # --- LIVA 91: fixture de test con texto realista del BOE ---
    # Este no es un placeholder de producción; el worker BOE ingesta el texto real.
    # Aquí usamos un extracto representativo para que los tests verifiquen búsqueda y estructura.
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '91', 'Tipos impositivos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Artículo 91. Tipos impositivos reducidos.
Uno. Se aplicará el tipo reducido a las siguientes operaciones:
1. Las entregas de bienes de primera necesidad.
2. Los servicios de hostelería y restaurante.
Dos. Se aplicará un tipo superreducido al pan, leche y libros.', '1993-01-01', NULL, 'a91'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- ITPAJD 7: fixture para validar la nueva cobertura ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '7', 'Transmisiones patrimoniales sujetas', 'articulo'
    FROM norma WHERE codigo = 'ITPAJD'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 7. Son transmisiones patrimoniales sujetas:
1. Las transmisiones onerosas por actos inter vivos de toda clase de bienes y derechos.
2. La constitucion de derechos reales, prestamos, fianzas, arrendamientos y pensiones.',
    '1993-09-25', NULL, 'itpajd-a7'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'ITPAJD' AND a.numero = '7'
    """,
    # --- Materias (taxonomía curada) ---
    """
    INSERT INTO materia (slug, etiqueta)
    VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
    """,
    # --- Enlace materia <-> artículo (requiere que LIVA 91 exista) ---
    """
    INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
    SELECT a.id, m.id, 3
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    JOIN materia m ON m.slug = 'tipo-reducido-iva'
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- Doctrina de referencia ---
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Consulta DGT sobre tipo reducido', 'Documento de referencia relacionado con LIVA 91.', 'https://example.invalid/dgt/V0000-26'
    )
    """,
    # --- Enlace doctrina <-> artículo ---
    """
    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
    SELECT d.id, a.id, 'manual', 1.00, 'Test fixture'
    FROM documento_interpretativo d
    JOIN articulo a ON a.numero = '91'
    JOIN norma n ON n.id = a.norma_id
    WHERE d.referencia = 'V0000-26' AND n.codigo = 'LIVA'
    """,
    # --- Modelos AEAT ---
    """
    CREATE TABLE aeat_modelo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        periodo TEXT,
        impuesto TEXT,
        url_info TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE modelo_articulo (
        modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        casilla TEXT,
        nota TEXT,
        fuente TEXT NOT NULL,
        url_fuente TEXT,
        PRIMARY KEY (modelo_id, articulo_id)
    )
    """,
    # --- Seed: Modelo 100 linked to LIVA 91 (for testing doctrina derivada) ---
    """
    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
    VALUES ('100', 'IRPF Declaración anual', 'anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-100'),
           ('303', 'IVA Autoliquidación', 'trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-303')
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, '0002', 'Rendimientos trabajo', 'Instrucciones Modelo 100 2025', 'https://sede.agenciatributaria.gob.es'
    FROM aeat_modelo m, articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '100' AND n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- Modelos v2 schema: campañas, casillas, claves, instrucciones, normativa ---
    """
    CREATE TABLE modelo_campana (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        campana         TEXT NOT NULL,
        version_form    TEXT,
        url_instrucciones TEXT,
        url_normativa   TEXT,
        url_formato     TEXT,
        activo          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, campana)
    )
    """,
    """
    CREATE TABLE modelo_casilla (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_casilla    TEXT,
        pagina          INTEGER,
        orden           INTEGER,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE modelo_clave (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_clave      TEXT,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE modelo_instruccion (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        seccion         TEXT NOT NULL,
        titulo          TEXT NOT NULL,
        contenido       TEXT NOT NULL,
        orden           INTEGER DEFAULT 0,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE modelo_normativa (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        boe_id          TEXT,
        titulo          TEXT NOT NULL,
        fecha           TEXT,
        url_boe         TEXT,
        resumen         TEXT,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, boe_id)
    )
    """,
    # --- Seed: campaign for model 100 ---
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    # --- Seed: casillas for model 100 campaign ---
    """
    INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
    SELECT mc.id, '0002', 'Rendimientos del trabajo', 'Suma de todos los rendimientos del trabajo', 'importe', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    # --- Seed: instrucciones for model 100 campaign ---
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'caracteristicas', 'Que es el modelo 100?', 'El modelo 100 es la declaracion anual del IRPF.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    # --- Seed: normativa for model 100 ---
    """
    INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
    SELECT m.id, 'BOE-A-2024-26789', 'Orden HAC/1234/2024', '2024-12-20', 'https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf', 'Aprueba el modelo 100'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    # --- Note: modelo_campana_activa() is a Postgres function.
    # For SQLite tests, the API code falls back to direct queries when the function
    # is not available. The campaign seeded above has activo=1 so it will be picked
    # by the "ORDER BY campana DESC LIMIT 1" query in the router.
]

with engine.begin() as conn:
    for statement in STATEMENTS:
        conn.execute(text(statement))
