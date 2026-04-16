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
    CREATE TABLE empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        domicilio TEXT,
        fuente_inicial TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (nombre)
    )
    """,
    """
    CREATE TABLE obligacion_regulatoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE obligacion_documento (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id),
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        tipo_relacion TEXT NOT NULL,
        PRIMARY KEY (obligacion_id, documento_id)
    )
    """,
    """
    CREATE TABLE documento_empresa (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        rol TEXT NOT NULL,
        confianza_extraccion REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, empresa_id)
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
        'BOE-A-1993-25359',
        'https://www.boe.es/eli/es/rdlg/1993/09/24/1/con',
        'es',
        'boe',
        'real_decreto_legislativo',
        'tributario',
        'ingestada',
        '1993-09-25'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'IIEE',
        'Ley de Impuestos Especiales',
        'BOE-A-1992-28741',
        'https://www.boe.es/eli/es/l/1992/12/28/38',
        'es',
        'boe',
        'ley',
        'tributario',
        'ingestada',
        '1993-01-01'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'HL',
        'Texto refundido de la Ley Reguladora de las Haciendas Locales',
        'BOE-A-2004-4214',
        'https://www.boe.es/eli/es/rdl/2004/03/05/2',
        'es',
        'boe',
        'real_decreto_legislativo',
        'tributario_local',
        'ingestada',
        '2004-03-10'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'DAC6',
        'Ley 10/2020, de 29 de diciembre, por la que se modifica la Ley 58/2003, de 17 de diciembre, General Tributaria, en transposición de la Directiva (UE) 2018/822 del Consejo, de 25 de mayo de 2018',
        'BOE-A-2020-17265',
        'https://www.boe.es/eli/es/l/2020/12/29/10',
        'es',
        'boe',
        'ley',
        'tributario_internacional',
        'ingestada',
        '2020-12-30'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'DAC6RD',
        'Real Decreto 243/2021, de 6 de abril, por el que se modifica el Reglamento General de las actuaciones y los procedimientos de gestión e inspección tributaria y de desarrollo de las normas comunes de los procedimientos de aplicación de los tributos, aprobado por el Real Decreto 1065/2007, de 27 de julio, en transposición de la Directiva (UE) 2018/822 del Consejo, de 25 de mayo de 2018',
        'BOE-A-2021-5394',
        'https://www.boe.es/eli/es/rd/2021/04/06/243',
        'es',
        'boe',
        'real_decreto',
        'tributario_internacional',
        'ingestada',
        '2021-04-07'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'DAC6EU',
        'Directiva (UE) 2018/822 del Consejo, de 25 de mayo de 2018, que modifica la Directiva 2011/16/UE por lo que se refiere al intercambio automático y obligatorio de información en el ámbito de la fiscalidad en relación con los mecanismos transfronterizos sujetos a comunicación de información',
        'DOUE-L-2018-80963',
        'https://eur-lex.europa.eu/eli/dir/2018/822/oj',
        'ue',
        'eurlex',
        'directiva_ue',
        'tributario_ue',
        'referenciada',
        '2018-06-25'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'IRNR',
        'Texto refundido de la Ley del Impuesto sobre la Renta de no Residentes',
        'BOE-A-2004-19886',
        'https://www.boe.es/eli/es/rdl/2004/12/03/5',
        'es',
        'boe',
        'real_decreto_legislativo',
        'tributario',
        'ingestada',
        '2004-12-03'
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
    # --- IIEE 60: fixture básica para Impuestos Especiales ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '60', 'Impuesto especial sobre hidrocarburos', 'articulo'
    FROM norma WHERE codigo = 'IIEE'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 60. El impuesto especial sobre hidrocarburos grava la fabricación e importación de los productos objeto del impuesto.', '1993-01-01', NULL, 'iiee-a60'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IIEE' AND a.numero = '60'
    """,
    # --- HL 20: fixture básica para Haciendas Locales ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '20', 'Hecho imponible de las tasas', 'articulo'
    FROM norma WHERE codigo = 'HL'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 20. Las entidades locales podrán establecer tasas por la utilización privativa o el aprovechamiento especial del dominio público local.', '2004-03-10', NULL, 'hl-a20'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'HL' AND a.numero = '20'
    """,
    # --- DAC6 206 bis: obligación informativa sobre mecanismos transfronterizos ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '206 bis', 'Obligación de información de determinados mecanismos transfronterizos de planificación fiscal', 'articulo'
    FROM norma WHERE codigo = 'DAC6'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 206 bis. Deberán declararse los mecanismos transfronterizos de planificación fiscal cuando concurran las señas distintivas previstas en la normativa aplicable.', '2020-12-30', NULL, 'dac6-a206bis'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6' AND a.numero = '206 bis'
    """,
    # --- DAC6RD 45: desarrollo reglamentario de la declaración ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '45', 'Obligación de informar sobre mecanismos transfronterizos', 'articulo'
    FROM norma WHERE codigo = 'DAC6RD'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 45. Se regula el contenido y plazo de las declaraciones informativas relativas a mecanismos transfronterizos sujetos a comunicación.', '2021-04-07', NULL, 'dac6rd-a45'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6RD' AND a.numero = '45'
    """,
    # --- IRNR 13/14/25/26: fixtures para relaciones de modelos IRNR ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '13', 'Rentas inmobiliarias obtenidas sin establecimiento permanente', 'articulo'
    FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '14', 'Rentas obtenidas sin mediación de establecimiento permanente', 'articulo'
    FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '25', 'Rendimientos del capital mobiliario en el IRNR', 'articulo'
    FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '26', 'Ganancias patrimoniales en el IRNR', 'articulo'
    FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 13. Rentas inmobiliarias obtenidas en territorio español por contribuyentes no residentes sin establecimiento permanente.', '2004-12-03', NULL, 'irnr-a13'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '13'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 14. Rentas obtenidas sin mediación de establecimiento permanente sujetas al impuesto.', '2004-12-03', NULL, 'irnr-a14'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 25. Rendimientos del capital mobiliario obtenidos por no residentes sin establecimiento permanente.', '2004-12-03', NULL, 'irnr-a25'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '25'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 26. Ganancias patrimoniales obtenidas por no residentes sin establecimiento permanente.', '2004-12-03', NULL, 'irnr-a26'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '26'
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
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'convocatoria_subvencion',
        'BDNS',
        'es',
        'bdns',
        'subvenciones',
        'BDNS-749075-1034404',
        '2026-04-16',
        'Convocatoria 749075 - Becas de carácter general para estudiantes de enseñanzas postobligatorias',
        'Convocatoria de subvención pública para becas de carácter general. Incluye beneficiarios, cuantía, plazo de presentación y bases reguladoras.',
        'https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075/document/1034404'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'nombramiento',
        'BORME',
        'es',
        'borme',
        'mercantil',
        'BORME-A-2025-55-37',
        '2025-03-20',
        'Actos de SALAMANCA del BORME núm. 55 de 2025',
        'Constitución. ALVAREZ GARCIA GANADERIA, S.L. Domicilio: C/ SANTA LUCIA 19. Capital: 3.000,00 Euros. Nombramientos. Adm. Unico: ALVAREZ GARCIA JOSE MARIA.',
        'https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'circular_cnmv',
        'CNMV',
        'es',
        'cnmv',
        'reporting_financiero',
        'BOE-A-2009-133',
        '2009-01-02',
        'Circular 9/2008, de 10 de diciembre, de la Comisión Nacional del Mercado de Valores',
        'Circular 9/2008, de la Comisión Nacional del Mercado de Valores, sobre normas contables, estados de información reservada y pública y cuentas anuales de las sociedades rectoras de los mercados secundarios oficiales.',
        'https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'formulario_sepblac',
        'SEPBLAC',
        'es',
        'sepblac',
        'aml_cft_reporting',
        'SEPBLAC-MODELO-19',
        '2026-04-16',
        'Comunicación por indicio - Modelo 19 SEPBLAC',
        'Procedimiento para la comunicación por indicio de hechos u operaciones respecto de los que existan indicios o certeza de blanqueo de capitales o financiación del terrorismo. Incluye el formulario oficial Modelo 19 SEPBLAC.',
        'https://www.sepblac.es/es/'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota
    )
    VALUES (
        'CNMV-IR-RESERVADA',
        'Remitir información reservada periódica a la CNMV',
        'cnmv',
        'CNMV',
        'remision_informacion',
        'empresa_servicios_inversion',
        'periodica',
        'estados_reservados',
        'reporting_regulatorio',
        'vigente',
        'circular_cnmv',
        'BOE-A-2009-133',
        NULL,
        NULL,
        'Obligación base derivada del corpus CNMV para el primer slice de obligaciones.'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota
    )
    VALUES (
        'SEPBLAC-INDICIO-M19',
        'Comunicar operativa sospechosa por indicio mediante Modelo 19',
        'sepblac',
        'SEPBLAC',
        'comunicacion_indicio',
        'sujeto_obligado_pbcft',
        'eventual',
        'modelo_19',
        'aml_cft_reporting',
        'vigente',
        'formulario_sepblac',
        'SEPBLAC-MODELO-19',
        '15.5',
        NULL,
        'Obligación base del primer slice operativo SEPBLAC.'
    )
    """,
    """
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'BOE-A-2009-133'
    WHERE o.codigo = 'CNMV-IR-RESERVADA'
    """,
    """
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'SEPBLAC-MODELO-19'
    WHERE o.codigo = 'SEPBLAC-INDICIO-M19'
    """,
    """
    INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
    VALUES (
        'ALVAREZ GARCIA GANADERIA, S.L.',
        NULL,
        'C/ SANTA LUCIA 19',
        'BORME'
    )
    """,
    """
    INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
    VALUES (
        'MURILLO & BARRERO, SOCIEDAD LIMITADA',
        NULL,
        NULL,
        'BORME'
    )
    """,
    """
    INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
    SELECT d.id, e.id, 'principal', 0.85, 'Test fixture BORME empresa'
    FROM documento_interpretativo d
    JOIN empresa e ON e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    WHERE d.referencia = 'BORME-A-2025-55-37'
    """,
    """
    INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
    SELECT d.id, e.id, 'absorbida', 0.70, 'Test fixture BORME empresa relacionada'
    FROM documento_interpretativo d
    JOIN empresa e ON e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    WHERE d.referencia = 'BORME-A-2025-55-37'
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
           ('303', 'IVA Autoliquidación', 'trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-303'),
           ('124', 'Retenciones IRNR — rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-124'),
           ('216', 'IRNR Retenciones rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-216'),
           ('296', 'IRNR Resumen anual retenciones sin EP', 'anual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-296')
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, '0002', 'Rendimientos trabajo', 'Instrucciones Modelo 100 2025', 'https://sede.agenciatributaria.gob.es'
    FROM aeat_modelo m, articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '100' AND n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Rentas obtenidas sin EP', 'Instrucciones Modelo 124 2025', 'https://sede.agenciatributaria.gob.es/modelo-124'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '124' AND n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Retenciones IRNR sin EP', 'Instrucciones Modelo 216 2025', 'https://sede.agenciatributaria.gob.es/modelo-216'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '216' AND n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Resumen anual IRNR', 'Instrucciones Modelo 296 2025', 'https://sede.agenciatributaria.gob.es/modelo-296'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '296' AND n.codigo = 'IRNR' AND a.numero = '14'
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
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-124-instrucciones'
    FROM aeat_modelo m WHERE m.codigo = '124'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-216-instrucciones'
    FROM aeat_modelo m WHERE m.codigo = '216'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-296-instrucciones'
    FROM aeat_modelo m WHERE m.codigo = '296'
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
    """
    INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
    SELECT m.id, 'BOE-A-2004-19886', 'RDL 5/2004 — IRNR', '2004-12-03', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', 'Texto refundido de la Ley del IRNR'
    FROM aeat_modelo m WHERE m.codigo IN ('124', '216', '296')
    """,
    # --- Note: modelo_campana_activa() is a Postgres function.
    # For SQLite tests, the API code falls back to direct queries when the function
    # is not available. The campaign seeded above has activo=1 so it will be picked
    # by the "ORDER BY campana DESC LIMIT 1" query in the router.
]

with engine.begin() as conn:
    for statement in STATEMENTS:
        conn.execute(text(statement))
