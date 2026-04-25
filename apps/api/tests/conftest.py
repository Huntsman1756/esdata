import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"esdata_test_{os.getpid()}.sqlite3"

if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except PermissionError:
        pass

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
    CREATE TABLE materia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        etiqueta TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE articulo_materia (
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
        relevancia INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (articulo_id, materia_id)
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
    INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
    VALUES
        ('LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740', 'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe', 'ley', 'tributario', 'ingestada', '1993-01-01'),
        ('LIRPF', 'Ley del Impuesto sobre la Renta de las Personas Fisicas', 'BOE-A-2006-20764', 'https://www.boe.es/eli/es/l/2006/11/23/35', 'es', 'boe', 'ley', 'tributario', 'ingestada', '2007-01-01'),
        ('LIS', 'Ley del Impuesto sobre Sociedades', 'BOE-A-2014-12328', 'https://www.boe.es/eli/es/l/2014/11/27/27', 'es', 'boe', 'ley', 'tributario', 'ingestada', '2015-01-01'),
        ('LGT', 'Ley General Tributaria', 'BOE-A-2003-23186', 'https://www.boe.es/eli/es/l/2003/12/17/58', 'es', 'boe', 'ley', 'tributario', 'ingestada', '2004-01-01'),
        ('ITPAJD', 'Ley del ITPAJD', 'BOE-A-1993-25359', 'https://www.boe.es/eli/es/rdl/1993/09/24/1', 'es', 'boe', 'real_decreto_legislativo', 'tributario', 'ingestada', '1993-09-25'),
        ('IRNR', 'RDL 5/2004 — Ley del IRNR', 'BOE-A-2004-4527', 'https://www.boe.es/eli/es/rdl/2004/12/03/5', 'es', 'boe', 'real_decreto_legislativo', 'tributario', 'ingestada', '2004-12-03'),
        ('IIEE', 'Ley de Impuestos Especiales', 'BOE-A-1992-28741', 'https://www.boe.es/eli/es/l/1992/12/28/38', 'es', 'boe', 'ley', 'tributario', 'ingestada', '1993-01-01'),
        ('HL', 'Ley de Haciendas Locales', 'BOE-A-2004-4214', 'https://www.boe.es/eli/es/rdl/2004/03/05/2', 'es', 'boe', 'real_decreto_legislativo', 'tributario_local', 'ingestada', '2004-03-09'),
        ('DAC6', 'Ley 10/2020 de transposicion DAC6', 'BOE-A-2020-11325', 'https://www.boe.es/eli/es/l/2020/12/29/10', 'es', 'boe', 'ley', 'tributario_internacional', 'ingestada', '2020-12-30'),
        ('DAC6RD', 'Real Decreto 243/2021 DAC6', 'BOE-A-2021-5090', 'https://www.boe.es/eli/es/rd/2021/04/06/243', 'es', 'boe', 'real_decreto', 'tributario_internacional', 'ingestada', '2021-04-07'),
        ('DAC6EU', 'Directiva (UE) 2018/822', 'EUR-Lex-32018L0822', 'https://eur-lex.europa.eu/eli/dir/2018/822/oj', 'ue', 'eurlex', 'directiva_ue', 'tributario_internacional', 'referenciada', '2018-06-25')
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '91', 'Tipos impositivos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '14', 'Rentas exentas', 'articulo' FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '7', 'Hecho imponible', 'articulo' FROM norma WHERE codigo = 'ITPAJD'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '60', 'Impuestos especiales', 'articulo' FROM norma WHERE codigo = 'IIEE'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '20', 'Tributos locales', 'articulo' FROM norma WHERE codigo = 'HL'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '206 bis', 'Obligaciones de informacion', 'articulo' FROM norma WHERE codigo = 'DAC6'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id,
           'Articulo 91. El tipo reducido se aplica a alimentos, productos sanitarios y bienes de primera necesidad conforme a los tipos impositivos reducidos.',
           '1993-01-01',
           NULL,
           'a91'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id,
           'Articulo 14. Rentas obtenidas sin mediación de establecimiento permanente exentas en los supuestos legalmente previstos.',
           '2004-12-03',
           NULL,
           'irnr-14'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 7. Constituye el hecho imponible la transmision patrimonial onerosa y otras transmisiones sujetas al ITPAJD.', '1993-09-25', NULL, 'itpajd-7'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'ITPAJD' AND a.numero = '7'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 60. Impuestos especiales sobre hidrocarburos y otros productos objeto de gravamen especifico.', '1993-01-01', NULL, 'iiee-60'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IIEE' AND a.numero = '60'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 20. Tasas y tributos locales.', '2004-03-09', NULL, 'hl-20'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'HL' AND a.numero = '20'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 206 bis. Obligaciones de informacion de mecanismos transfronterizos.', '2020-01-01', NULL, 'dac6-206bis'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6' AND a.numero = '206 bis'
    """,
    """
    INSERT INTO materia (slug, etiqueta)
    VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
    """,
    """
    INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
    SELECT a.id, m.id, 1
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    JOIN materia m ON m.slug = 'tipo-reducido-iva'
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO documento_interpretativo (tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente)
    VALUES
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Consulta DGT sobre tipo reducido', 'Consulta sobre la aplicacion del tipo reducido del IVA conforme al articulo 91 de la Ley 37/1992.', 'https://example.invalid/dgt/V0000-26'),
        ('circular_cnmv', 'CNMV', 'es', 'cnmv', 'reporting_financiero', 'BOE-A-2009-133', '2009-01-02', 'Circular 9/2008 de la CNMV', 'Normas contables, estados de información reservada y pública y cuentas anuales. Estados de información reservada para entidades supervisadas.', 'https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133'),
        ('formulario_sepblac', 'SEPBLAC', 'es', 'sepblac', 'aml_cft_reporting', 'SEPBLAC-MODELO-19', '2026-04-16', 'Comunicación por indicio - Modelo 19 SEPBLAC', 'Procedimiento para la comunicación por indicio y formulario oficial Modelo 19 SEPBLAC.', 'https://www.sepblac.es/es/'),
        ('convocatoria_bdns', 'BDNS', 'es', 'bdns', 'subvenciones', 'BDNS-749075-1034404', '2025-02-01', 'Convocatoria de becas 2025', 'Convocatoria publica de becas y ayudas al estudio para el curso 2025.', 'https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075'),
        ('nombramiento', 'BORME', 'es', 'borme', 'mercantil', 'BORME-A-2025-55-37', '2025-03-01', 'Nombramientos y reelecciones societarias', 'Se publican nombramientos y otras modificaciones societarias en el BORME para Alvarez Garcia Ganaderia, S.L. y Murillo & Barrero, Sociedad Limitada.', 'https://www.boe.es/borme/dias/2025/03/01/pdfs/BORME-A-2025-55-37.pdf')
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
    CREATE TABLE documento_empresa (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        rol TEXT NOT NULL,
        confianza_extraccion REAL,
        nota TEXT,
        PRIMARY KEY (documento_id, empresa_id, rol)
    )
    """,
    """
    CREATE TABLE documento_articulo (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        metodo_enlace TEXT NOT NULL,
        confianza_enlace REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, articulo_id)
    )
    """,
    """
    CREATE TABLE sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        bloques_processed INTEGER,
        articulos_upserted INTEGER,
        documentos_processed INTEGER,
        documentos_upserted INTEGER,
        doctrina_links_created INTEGER,
        error_msg TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_regulatoria (
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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        plazo_dias INTEGER,
        frecuencia_presentacion TEXT,
        ventana_presentacion TEXT,
        trigger_presentacion TEXT,
        canal_presentacion TEXT,
        obligados_resumen TEXT,
        sancion_min NUMERIC(10,2),
        sancion_max NUMERIC(10,2),
        recargo_voluntario TEXT,
        recargo_involuntario TEXT,
        interes_demora TEXT,
        prescripcion_anos INTEGER,
        deposito_previo TEXT,
        fuentes_operativas TEXT,
        ultima_actualizacion TEXT,
        origen_metadato TEXT,
        estado_metadato TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_documento (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id) ON DELETE CASCADE,
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        tipo_relacion TEXT NOT NULL,
        PRIMARY KEY (obligacion_id, documento_id)
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
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
        'Obligación base derivada del corpus CNMV para el primer slice de obligaciones.',
        NULL, 'mensual', 'primeros_20_dias_periodo_siguiente', 'fin_mes',
        'electronica', 'Empresas de servicios de inversión', 3000, 60000000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
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
        'Obligación base del primer slice operativo SEPBLAC.',
        15, 'eventual', '1_mes_desde_hecho', 'detectar_indicio',
        'electronica', 'Sujetos obligados PBCFT', 10000, 6000000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'IRNR_FACTA',
        'Presentar modelos IRNR por retenciones a no residentes sin establecimiento permanente',
        'aeat',
        'AEAT',
        'declaracion_tributaria',
        'retenedor_irnr',
        'periodica',
        '216',
        'tributario_internacional',
        'vigente',
        'real_decreto_legislativo',
        'BOE-A-2004-4527',
        'articulo 14',
        NULL,
        'Obligacion fiscal base para retenciones IRNR sin establecimiento permanente.',
        20, 'mensual', 'primeros_20_dias_periodo_siguiente', 'fin_mes',
        'electronica', 'Retenedores sobre rentas de no residentes sin establecimiento permanente.', 50, 150,
        '5%', '5-10%', 'TIE + 4%', 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'IRPF_ANUAL',
        'Presentar declaracion anual del IRPF',
        'aeat',
        'AEAT',
        'declaracion_tributaria',
        'contribuyente_irpf',
        'periodica',
        '100',
        'tributario',
        'vigente',
        'ley',
        'BOE-A-2006-20764',
        NULL,
        NULL,
        'Obligacion anual del IRPF para contribuyentes obligados a declarar.',
        120, 'anual', 'campana_renta', 'cierre_ejercicio',
        'electronica', 'Contribuyentes del IRPF obligados a declarar.', 0, 150000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
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
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'V0000-26'
    WHERE o.codigo = 'IRNR_FACTA'
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
           ('111', 'IRPF Retenciones e ingresos a cuenta', 'trimestral', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-111'),
           ('115', 'IRPF Retenciones arrendamientos', 'trimestral', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-115'),
           ('303', 'IVA Autoliquidación', 'trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-303'),
           ('349', 'Declaración recapitulativa operaciones intracomunitarias', 'mensual', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-349'),
           ('390', 'IVA Resumen anual', 'anual', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-390'),
           ('124', 'Retenciones IRNR — rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-124'),
           ('216', 'IRNR Retenciones rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-216'),
           ('296', 'IRNR Resumen anual retenciones sin EP', 'anual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-296'),
           ('036', 'Declaración censal alta/modificación/baja', 'eventual', 'CENSAL', 'https://sede.agenciatributaria.gob.es/modelo-036'),
           ('347', 'Declaración anual operaciones con terceros', 'anual', 'INFORMATIVO', 'https://sede.agenciatributaria.gob.es/modelo-347')
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
    """
    CREATE TABLE modelo_campana_operativa (
        campana_id               INTEGER PRIMARY KEY REFERENCES modelo_campana(id) ON DELETE CASCADE,
        categoria_obligado       TEXT,
        frecuencia_presentacion  TEXT,
        ventana_presentacion     TEXT,
        canal_presentacion       TEXT,
        obligados_resumen        TEXT,
        plazo_resumen            TEXT,
        presentacion_resumen     TEXT,
        norma_base               TEXT,
        nota                     TEXT,
        origen_metadato          TEXT DEFAULT 'seed_curado',
        estado_metadato          TEXT DEFAULT 'curado',
        actualizado_at           TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Seed: campaign for model 100 ---
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa, url_formato)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-100-normativa',
           'https://sede.agenciatributaria.gob.es/modelo-100-formato'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-111-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-111-normativa'
    FROM aeat_modelo m WHERE m.codigo = '111'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-115-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-115-normativa'
    FROM aeat_modelo m WHERE m.codigo = '115'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-124-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-124-normativa'
    FROM aeat_modelo m WHERE m.codigo = '124'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-216-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-216-normativa'
    FROM aeat_modelo m WHERE m.codigo = '216'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-296-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-296-normativa'
    FROM aeat_modelo m WHERE m.codigo = '296'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-303-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-303-normativa'
    FROM aeat_modelo m WHERE m.codigo = '303'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-349-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-349-normativa'
    FROM aeat_modelo m WHERE m.codigo = '349'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-390-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-390-normativa'
    FROM aeat_modelo m WHERE m.codigo = '390'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-036-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-036-normativa'
    FROM aeat_modelo m WHERE m.codigo = '036'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-347-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-347-normativa'
    FROM aeat_modelo m WHERE m.codigo = '347'
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
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 100', 'Deben presentar este modelo los contribuyentes del IRPF obligados a declarar conforme a los limites legales vigentes.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 100', 'La presentacion de la declaracion anual del IRPF correspondiente a la campana 2025 se realiza dentro del plazo general de la campana de renta publicado por AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 216', 'Deben presentar el modelo 216 los obligados a practicar retenciones o ingresos a cuenta sobre determinadas rentas obtenidas por no residentes sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 111', 'Deben presentar el modelo 111 los obligados a practicar retenciones e ingresos a cuenta por rendimientos del trabajo y determinadas actividades economicas.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 111', 'El modelo 111 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 111', 'La presentacion del modelo 111 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 115', 'Deben presentar el modelo 115 los obligados a practicar retenciones por arrendamientos de inmuebles urbanos.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 115', 'El modelo 115 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 115', 'La presentacion del modelo 115 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 216', 'El modelo 216 se presenta con caracter mensual dentro de los primeros veinte dias naturales del mes siguiente al periodo de declaracion, salvo las especialidades previstas por AEAT.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 216', 'La presentacion del modelo 216 se realiza por via electronica a traves de la sede de la AEAT utilizando los sistemas de identificacion admitidos.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 124', 'Deben presentar el modelo 124 los obligados a retener sobre determinadas rentas del capital mobiliario obtenidas por no residentes sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 124', 'El modelo 124 se presenta con caracter mensual dentro de los primeros veinte dias naturales del mes siguiente al periodo de declaracion.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 124', 'La presentacion del modelo 124 se realiza por medios electronicos a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 296', 'Deben presentar el modelo 296 los retenedores y obligados a ingresar a cuenta que deban resumir anualmente las rentas sujetas al IRNR sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 296', 'El modelo 296 se presenta con caracter anual en el plazo fijado por la AEAT para el resumen anual de retenciones e ingresos a cuenta.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 296', 'La presentacion del modelo 296 se realiza electronicamente mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 303', 'Deben presentar el modelo 303 los empresarios y profesionales que deban autoliquidar el IVA en el periodo correspondiente, salvo los supuestos exceptuados por la normativa.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 303', 'El modelo 303 se presenta con caracter trimestral o mensual segun el regimen aplicable, dentro de los plazos generales establecidos por la AEAT para la autoliquidacion del IVA.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 303', 'La presentacion del modelo 303 se realiza por via electronica mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 349', 'Deben presentar el modelo 349 los sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 349', 'El modelo 349 se presenta con caracter mensual o trimestral segun el volumen de operaciones, del 1 al 20 del mes siguiente al periodo.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 349', 'La presentacion del modelo 349 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 390', 'Deben presentar el modelo 390 los sujetos pasivos del IVA obligados a presentar el resumen anual, salvo excepciones previstas por la normativa.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 390', 'El modelo 390 se presenta con caracter anual en el plazo fijado por la AEAT junto con el cierre del ejercicio de IVA.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 390', 'La presentacion del modelo 390 se realiza por via electronica mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 036', 'Deben presentar el modelo 036 las personas fisicas o juridicas que inicien actividad, modifiquen datos censales o causen baja en el censo.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 036', 'El modelo 036 se presenta dentro del plazo de un mes desde el inicio de actividad o desde la modificacion censal correspondiente.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 036', 'La presentacion del modelo 036 puede realizarse por la sede de la AEAT con los sistemas de identificacion admitidos.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 347', 'Deben presentar el modelo 347 quienes hayan realizado operaciones con terceros por importe superior al umbral legal anual.', 1
     FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
     WHERE m.codigo = '347' AND mc.campana = '2025'
     """,
    # --- workflow_cases table ---
    """
    CREATE TABLE IF NOT EXISTS workflow_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_id TEXT UNIQUE NOT NULL,
        cambio_codigo TEXT NOT NULL,
        obligacion_codigo TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendiente_revision',
        owner_rol TEXT NOT NULL,
        fecha_objetivo TEXT NOT NULL,
        evidencia_requerida TEXT NOT NULL DEFAULT '[]',
        checklist TEXT NOT NULL DEFAULT '[]',
        resultado_revision TEXT,
        notas TEXT,
        accion_recomendada_confirmada TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT OR IGNORE INTO workflow_cases (
        workflow_id, cambio_codigo, obligacion_codigo, estado, owner_rol,
        fecha_objetivo, evidencia_requerida, checklist
    ) VALUES (
        'WF-001',
        'CAMBIO-CNMV-001',
        'CNMV-IR-RESERVADA',
        'pendiente_revision',
        'compliance',
        '2026-05-05',
        '["analisis_impacto","actualizacion_calendario"]',
        '["validar impacto normativo","asignar responsable","confirmar fecha objetivo"]'
    )
    """,
]

with engine.begin() as conn:
    for statement in STATEMENTS:
        conn.execute(text(statement))
