#!/usr/bin/env python3
"""Genera SQL seed para corpus documental (Fase 40).
Popula: norma, articulo, version_articulo, documento_interpretativo,
documento_version, documento_fragmento, documento_seccion, empresa,
obligacion_regulatoria, micro_obligacion, obligacion_micro_obligacion,
obligacion_documento, documento_articulo, embedding_version.
"""

import hashlib
import json

def sql_escape(s):
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"

def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:32]

def generate_seed():
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- Fase 40: Seed corpus documental — Leyes fiscales España")
    lines.append("-- ============================================================")
    lines.append("")

    # ── 1. norma ──────────────────────────────────────────────────
    lines.append("-- 1. norma — leyes fiscales principales")
    lines.append("INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) VALUES")

    normas = [
        ('LGT', 'Ley 58/2003, General Tributaria', 'BOE-A-2003-21814', 'https://www.eli.es/es/l/2003/12/17/58', 'es', 'ley organica', 'ley', 'tributario', 'vigente', '2003-12-17'),
        ('LIRPF', 'Ley 35/2006, IRPF', 'BOE-A-2006-22265', 'https://www.eli.es/es/l/2006/12/28/35', 'es', 'ley', 'ley', 'tributario', 'vigente', '2006-12-28'),
        ('LIVA', 'Ley 37/1992, IVA', 'BOE-A-1992-27212', 'https://www.eli.es/es/l/1992/12/28/37', 'es', 'ley', 'ley', 'tributario', 'vigente', '1992-12-28'),
        ('LGT-REG', 'RGL (RD 439/2000)', 'BOE-A-2000-18976', 'https://www.eli.es/es/rd/2000/03/24/439', 'es', 'real decreto', 'reglamento', 'tributario', 'vigente', '2000-03-24'),
        ('LIS', 'Ley 27/2014, IS', 'BOE-A-2014-10399', 'https://www.eli.es/es/l/2014/11/20/27', 'es', 'ley', 'ley', 'tributario', 'vigente', '2014-11-20'),
        ('LGC', 'Ley 58/2003, General Tributaria (reglamento)', 'BOE-A-2003-21814', 'https://www.eli.es/es/l/2003/12/17/58', 'es', 'ley', 'ley', 'tributario', 'vigente', '2003-12-17'),
    ]

    vals = []
    for codigo, titulo, boe_id, eli_uri, jur, tf, td, ambito, estado, vigente in normas:
        h = content_hash(titulo)
        vals.append(f"  ({sql_escape(codigo)}, {sql_escape(titulo)}, {sql_escape(boe_id)}, {sql_escape(eli_uri)}, {sql_escape(jur)}, {sql_escape(tf)}, {sql_escape(td)}, {sql_escape(ambito)}, {sql_escape(estado)}, {sql_escape(vigente)})")
    lines.append(",\n".join(vals) + ";")
    lines.append("")

    # ── 2. articulo ───────────────────────────────────────────────
    lines.append("-- 2. articulo — artículos de las leyes fiscales")
    articulos = [
        # LGT — artículos clave
        ('LGT', '1', 'Ámbito de aplicación', 'articulo'),
        ('LGT', '2', 'Principios de ejecución tributaria', 'articulo'),
        ('LGT', '3', 'Interpretación tributaria', 'articulo'),
        ('LGT', '4', 'Derechos de la Administración', 'articulo'),
        ('LGT', '5', 'Obligaciones tributarias', 'articulo'),
        ('LGT', '6', 'Obligación tributaria principal: prestación patrimonial', 'articulo'),
        ('LGT', '7', 'Obligaciones tributarias accesorias', 'articulo'),
        ('LGT', '8', 'Obligaciones formales genéricas', 'articulo'),
        ('LGT', '9', 'Obligaciones derivadas', 'articulo'),
        ('LGT', '10', 'Sujeto pasivo', 'articulo'),
        ('LGT', '11', 'Solidaridad y responsabilidad', 'articulo'),
        ('LGT', '12', 'Hecho imponible', 'articulo'),
        ('LGT', '13', 'Fuentes del derecho tributario', 'articulo'),
        ('LGT', '14', 'Normas sobre la obligación tributar', 'articulo'),
        ('LGT', '15', 'Recargo voluntario e involuntario', 'articulo'),
        ('LGT', '16', 'Plazo de presentación y abono', 'articulo'),
        ('LGT', '17', 'Liquidación', 'articulo'),
        ('LGT', '18', 'Liquidación de oficio', 'articulo'),
        ('LGT', '19', 'Recaudación', 'articulo'),
        ('LGT', '20', 'Período de liquidación', 'articulo'),
        ('LGT', '21', 'Prescripción', 'articulo'),
        ('LGT', '22', 'Interrupción', 'articulo'),
        ('LGT', '23', 'Reclamación económico-tributaria', 'articulo'),
        ('LGT', '24', 'Inspección de los tributos', 'articulo'),
        ('LGT', '25', 'Prueba', 'articulo'),
        ('LGT', '26', 'Sanciones', 'articulo'),
        ('LGT', '27', 'Clasificación de infracciones', 'articulo'),
        ('LGT', '28', 'Proporcionalidad de las sanciones', 'articulo'),
        ('LGT', '29', 'Prescripción de las infracciones', 'articulo'),
        ('LGT', '30', 'Responsabilidad', 'articulo'),

        # LIRPF — artículos clave
        ('LIRPF', '1', 'Ámbito territorial', 'articulo'),
        ('LIRPF', '2', 'Sujetos pasivos', 'articulo'),
        ('LIRPF', '3', 'Rendimientos del trabajo', 'articulo'),
        ('LIRPF', '4', 'Rendimientos por actividad económica', 'articulo'),
        ('LIRPF', '5', 'Rendimientos del capital mobiliario', 'articulo'),
        ('LIRPF', '6', 'Ganancias y pérdidas patrimoniales', 'articulo'),
        ('LIRPF', '7', 'Integración en base imponible', 'articulo'),
        ('LIRPF', '8', 'Deducciones en la cuota', 'articulo'),
        ('LIRPF', '9', 'Deducciones estatales autonómicas', 'articulo'),
        ('LIRPF', '10', 'Retenciones e ingresos a cuenta', 'articulo'),
        ('LIRPF', '11', 'Mínimo por trabajo realizado', 'articulo'),
        ('LIRPF', '12', 'Mínimo por ascendientes y descendientes', 'articulo'),
        ('LIRPF', '13', 'Mínimo por maternidad', 'articulo'),
        ('LIRPF', '14', 'Mínimo por situaciones de dependencia', 'articulo'),
        ('LIRPF', '15', 'Mínimo por inversiones en vivienda habitual', 'articulo'),
        ('LIRPF', '16', 'Declaración anual', 'articulo'),
        ('LIRPF', '17', 'Forma de presentación', 'articulo'),
        ('LIRPF', '18', 'Plazo de presentación', 'articulo'),
        ('LIRPF', '19', 'Pagos fraccionados', 'articulo'),
        ('LIRPF', '20', 'Estadísticas', 'articulo'),

        # LIVA — artículos clave
        ('LIVA', '1', 'Hecho imponible', 'articulo'),
        ('LIVA', '2', 'Sujeto pasivo', 'articulo'),
        ('LIVA', '3', 'Bienes y servicios', 'articulo'),
        ('LIVA', '4', 'Operaciones intracomunitarias', 'articulo'),
        ('LIVA', '5', 'Entregas y prestaciones de servicios', 'articulo'),
        ('LIVA', '6', 'Exenciones', 'articulo'),
        ('LIVA', '7', 'No sujetas', 'articulo'),
        ('LIVA', '8', 'Tipo de gravamen', 'articulo'),
        ('LIVA', '9', 'Devengo', 'articulo'),
        ('LIVA', '10', 'Cuota soportada', 'articulo'),
        ('LIVA', '11', 'Cuota repercutida', 'articulo'),
        ('LIVA', '12', 'Autoliquidaciones', 'articulo'),
        ('LIVA', '13', 'Devoluciones', 'articulo'),
        ('LIVA', '14', 'Libros registro', 'articulo'),
        ('LIVA', '15', 'Facturación', 'articulo'),

        # LIS — artículos clave
        ('LIS', '1', 'Ámbito de aplicación', 'articulo'),
        ('LIS', '2', 'Sujetos pasivos', 'articulo'),
        ('LIS', '3', 'Base imponible', 'articulo'),
        ('LIS', '4', 'Rendimientos del capital mobiliario', 'articulo'),
        ('LIS', '5', 'Deducciones', 'articulo'),
        ('LIS', '6', 'Gravamen', 'articulo'),
        ('LIS', '7', 'Devolución', 'articulo'),
        ('LIS', '8', 'Plazo de presentación', 'articulo'),
        ('LIS', '9', 'Dividendos', 'articulo'),
        ('LIS', '10', 'Deducción por doble tributación internacional', 'articulo'),
    ]

    for norma_codigo, numero, titulo, tipo in articulos:
        h = content_hash(f"{norma_codigo}:{numero}")
        lines.append(f"INSERT INTO articulo (norma_id, numero, titulo, tipo, content_hash) SELECT n.id, {sql_escape(numero)}, {sql_escape(titulo)}, {sql_escape(tipo)}, {sql_escape(h)} FROM norma n WHERE n.codigo = {sql_escape(norma_codigo)};")
    lines.append("")

    # ── 3. version_articulo ───────────────────────────────────────
    lines.append("-- 3. version_articulo — versiones de artículos (vigentes)")

    version_articulos = {
        # LGT
        'LGT:1': ('Ámbito de aplicación', '2003-12-17', 'Los principios de libertad, capacidad y solidaridad económica informan todo el ordenamiento jurídico tributario.'),
        'LGT:2': ('Principios de ejecución tributaria', '2003-12-17', 'La actuación de la Administración tributaria se regirá por los principios de eficacia, proporcionalidad, celeridad e imparcialidad.'),
        'LGT:3': ('Interpretación tributaria', '2003-12-17', 'Las normas tributarias se interpretarán de acuerdo con las reglas establecidas en los artículos 3 y 4 del Código Civil.'),
        'LGT:5': ('Obligaciones tributarias', '2003-12-17', 'Las obligaciones tributarias principales y accesorias se establecen en esta ley y en las normas tributarias especiales.'),
        'LGT:10': ('Sujeto pasivo', '2003-12-17', 'Los sujetos pasivos son quienes realizan los hechos imponibles previstos en las normas tributarias.'),
        'LGT:12': ('Hecho imponible', '2003-12-17', 'El hecho imponible es la conducta descrita por la norma tributaria como presupuesto del tributo.'),
        'LGT:17': ('Liquidación', '2003-12-17', 'La liquidación tributaria es el acto mediante el cual se determina la deuda tributaria.'),
        'LGT:21': ('Prescripción', '2003-12-17', 'Los derechos de la Administración para determinar las deudas tributarias prescriben en cuatro años.'),
        'LGT:26': ('Sanciones', '2003-12-17', 'Las infracciones tributarias serán sancionadas conforme a lo dispuesto en esta ley.'),
        'LGT:30': ('Responsabilidad', '2003-12-17', 'Responderán del pago de las deudas tributarias los terceros previstos en esta ley.'),

        # LIRPF
        'LIRPF:1': ('Ámbito territorial', '2006-12-28', 'Los residentes fiscales en España tributarán por sus rentas mundiales. Los no residentes tributarán solo por rentas obtenidas en España.'),
        'LIRPF:2': ('Sujetos pasivos', '2006-12-28', 'Son sujetos pasivos los residentes y no residentes que obtengan rentas en territorio español.'),
        'LIRPF:3': ('Rendimientos del trabajo', '2006-12-28', 'Son rendimientos del trabajo las contraprestaciones obtenidas por servicios laborales por cuenta ajena.'),
        'LIRPF:4': ('Actividades económicas', '2006-12-28', 'Son rendimientos de actividades económicas los obtenidos por el ejercicio directo, profesional o empresarial.'),
        'LIRPF:5': ('Capital mobiliario', '2006-12-28', 'Son rendimientos del capital mobiliario los obtenidos por participaciones en entidades y créditos.'),
        'LIRPF:6': ('Ganancias patrimoniales', '2006-12-28', 'Son ganancias patrimoniales el aumento o disminución del patrimonio obtenido por transmisión o no.'),
        'LIRPF:8': ('Deducciones en la cuota', '2006-12-28', 'Las deducciones en la cuota se aplicarán sobre el resultado de la declaración.'),
        'LIRPF:10': ('Retenciones', '2006-12-28', 'Las retenciones e ingresos a cuenta se practicarán sobre los rendimientos previstos en esta ley.'),
        'LIRPF:16': ('Declaración anual', '2006-12-28', 'Los contribuyentes que obtengan rendimientos del trabajo sujetos a retención presentarán declaración anual.'),
        'LIRPF:19': ('Pagos fraccionados', '2006-12-28', 'Los contribuyentes que ejerzan actividades económicas realizarán pagos fraccionados trimestrales.'),

        # LIVA
        'LIVA:1': ('Hecho imponible', '1992-12-28', 'El hecho imponible del IVA consiste en la entrega de bienes y prestación de servicios en territorio español.'),
        'LIVA:2': ('Sujeto pasivo', '1992-12-28', 'Son sujetos pasivos los empresarios o profesionales que realicen entregas o prestaciones.'),
        'LIVA:3': ('Bienes y servicios', '1992-12-28', 'Se entiende por bienes todas las cosas corporales y por servicios todas las prestaciones.'),
        'LIVA:6': ('Exenciones', '1992-12-28', 'No estarán sujetas al IVA las entregas de bienes y prestaciones de servicios exentas.'),
        'LIVA:8': ('Tipo de gravamen', '1992-12-28', 'El tipo de gravamen general será del 21%. Podrán establecerse tipos reducidos.'),
        'LIVA:10': ('Cuota soportada', '1992-12-28', 'La cuota soportada es la IVA repercutida por el transmitente o prestador.'),
        'LIVA:12': ('Autoliquidaciones', '1992-12-28', 'Los sujetos pasivos practicarán autoliquidaciones trimestrales o mensuales.'),
        'LIVA:15': ('Facturación', '1992-12-28', 'Las entregas de bienes y prestaciones de servicios se documentarán mediante facturas.'),
    }

    for articulo_ref, (titulo, vigente_desde, texto) in version_articulos.items():
        norma_codigo, numero = articulo_ref.split(':')
        h = content_hash(texto)
        lines.append(f"INSERT INTO version_articulo (articulo_id, texto, vigente_desde, content_hash) "
                     f"SELECT a.id, {sql_escape(texto)}, {sql_escape(vigente_desde)}, {sql_escape(h)} "
                     f"FROM articulo a JOIN norma n ON n.id = a.norma_id "
                     f"WHERE n.codigo = {sql_escape(norma_codigo)} AND a.numero = {sql_escape(numero)};")
    lines.append("")

    # ── 4. documento_interpretativo — circulars y resoluciones ─────
    lines.append("-- 4. documento_interpretativo — circulares y resoluciones VAT/IRPF")

    interpretativos = [
        ('VAT-2024-001', 'AEAT', 'España', 'circular', 'tributario', 'general', 'VAT-2024-001', '2024-06-15', 'Interpretación IVA digital services',
         'Las prestaciones de servicios electrónicos a consumidores finales se consideran realizadas en el país de destino del consumidor a partir de 2024.',
         'https://sede.agenciatributaria.gob.es/Sede/ayuda/circulares/index.shtml', None, 'BOE-A-2024-11001', 'vigente', 'digital', 'Directiva 2006/112/CE'),
        ('VAT-2024-002', 'AEAT', 'España', 'resolucion', 'tributario', 'general', 'VAT-2024-002', '2024-09-20', 'Facturación electrónica obligatoria',
         'A partir de 2024, las empresas obligadas a llevar el Libro Registro de Facturas emitidas deberán hacerlo en formato electrónico.',
         'https://sede.agenciatributaria.gob.es/Sede/ayuda/resoluciones/index.shtml', None, 'BOE-A-2024-15002', 'vigente', 'facturacion', 'Ley 18/2022'),
        ('IRPF-2024-001', 'AEAT', 'España', 'circular', 'tributario', 'general', 'IRPF-2024-001', '2024-03-10', 'Deducciones vivienda habitual 2024',
         'Se actualizan los criterios de deducción por vivienda habitual para el ejercicio 2024, manteniendo el régimen transitorio.',
         'https://sede.agenciatributaria.gob.es/Sede/ayuda/circulares/index.shtml', None, 'BOE-A-2024-05001', 'vigente', 'vivienda', 'LIRPF art. 68'),
        ('IRPF-2024-002', 'AEAT', 'España', 'resolucion', 'tributario', 'general', 'IRPF-2024-002', '2024-04-01', 'Retenciones autónomos 2024',
         'Las retenciones para autónomos se calculan aplicando el tipo del 15% sobre la base estimada del ejercicio anterior.',
         'https://sede.agenciatributaria.gob.es/Sede/ayuda/resoluciones/index.shtml', None, 'BOE-A-2024-05501', 'vigente', 'retenciones', 'LIRPF art. 92'),
        ('LIS-2024-001', 'AEAT', 'España', 'circular', 'tributario', 'general', 'LIS-2024-001', '2024-07-15', 'Deducción I+D+i 2024',
         'La deducción por actividades de I+D+i se mantiene en un 42% para la parte fija y 14% para la variable en 2024.',
         'https://sede.agenciatributaria.gob.es/Sede/ayuda/circulares/index.shtml', None, 'BOE-A-2024-12001', 'vigente', 'i+d', 'LIS art. 36'),
    ]

    for referencia, organismo, jurisdiccion, tipo_doc, tipo_fuente, ambito, ref, fecha, titulo, texto, url, num_circ, ref_boe, estado, ambito_tema, reg_rel in interpretativos:
        h = content_hash(texto)
        fecha_sql = sql_escape(fecha)
        lines.append(f"INSERT INTO documento_interpretativo (referencia, tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, fecha, titulo, texto, url_fuente, numero_circular, referencia_boe, estado_vigencia, ambito_tematico, regulacion_relacionada, content_hash) "
                     f"VALUES ({sql_escape(referencia)}, {sql_escape(tipo_doc)}, {sql_escape(organismo)}, {sql_escape(jurisdiccion)}, {sql_escape(tipo_fuente)}, {sql_escape(ambito)}, {fecha_sql}, {sql_escape(titulo)}, {sql_escape(texto)}, {sql_escape(url)}, {sql_escape(num_circ)}, {sql_escape(ref_boe)}, {sql_escape(estado)}, {sql_escape(ambito_tema)}, {sql_escape(reg_rel)}, {sql_escape(h)});")
    lines.append("")

    # ── 5. documento_version ──────────────────────────────────────
    lines.append("-- 5. documento_version — versiones de documentos interpretativos")
    for ref in ['VAT-2024-001', 'VAT-2024-002', 'IRPF-2024-001', 'IRPF-2024-002', 'LIS-2024-001']:
        lines.append(f"INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version, url_version) "
                     f"VALUES ({sql_escape(ref)}, 1, "
                     f"(SELECT texto FROM documento_interpretativo d WHERE d.referencia = {sql_escape(ref)}), "
                     f"'creacion', '2024-01-01', {sql_escape('https://sede.agenciatributaria.gob.es')});")
    lines.append("")

    # ── 6. documento_fragmento ────────────────────────────────────
    lines.append("-- 6. documento_fragmento — fragmentos de documentos")

    fragmentos = [
        ('VAT-2024-001', 1, 'Hecho imponible', 'Las prestaciones de servicios electrónicos a consumidores finales se consideran realizadas en el país de destino del consumidor.', 0, 120, 18),
        ('VAT-2024-001', 2, 'Territorio de destino', 'A efectos del IVA digital, el consumidor se considera ubicado en el Estado miembro donde esté establecido.', 120, 240, 17),
        ('VAT-2024-002', 1, 'Obligación facturación electrónica', 'Las empresas obligadas a llevar el Libro Registro de Facturas deberán hacerlo en formato electrónico.', 0, 110, 16),
        ('IRPF-2024-001', 1, 'Deducción vivienda', 'Se actualizan los criterios de deducción por vivienda habitual manteniendo el régimen transitorio.', 0, 100, 14),
        ('IRPF-2024-002', 1, 'Retenciones autónomos', 'Las retenciones para autónomos se calculan aplicando el tipo del 15% sobre la base estimada.', 0, 95, 13),
        ('LIS-2024-001', 1, 'Deducción I+D', 'La deducción por actividades de I+D+i se mantiene en un 42% para la parte fija y 14% para la variable.', 0, 110, 16),
    ]

    for doc_ref, chunk_idx, titulo, texto, char_start, char_end, token_count in fragmentos:
        h = content_hash(texto)
        lines.append(f"INSERT INTO documento_fragmento (documento_origen_tipo, documento_origen_id, chunk_index, chunk_type, titulo, texto, char_start, char_end, token_count, content_hash) "
                     f"SELECT 'interpretativo', d.id, {chunk_idx}, 'natural', {sql_escape(titulo)}, {sql_escape(texto)}, {char_start}, {char_end}, {token_count}, {sql_escape(h)} "
                     f"FROM documento_interpretativo d WHERE d.referencia = {sql_escape(doc_ref)};")
    lines.append("")

    # ── 7. documento_seccion ──────────────────────────────────────
    lines.append("-- 7. documento_seccion — secciones de documentos")

    secciones = [
        ('VAT-2024-001', 'interpretativo', 1, 'Introducción', 1, 1),
        ('VAT-2024-001', 'interpretativo', 2, 'Servicios electrónicos', 2, 2),
        ('VAT-2024-002', 'interpretativo', 1, 'Introducción', 1, 1),
        ('VAT-2024-002', 'interpretativo', 2, 'Factura electrónica', 2, 2),
        ('IRPF-2024-001', 'interpretativo', 1, 'Introducción', 1, 1),
        ('IRPF-2024-001', 'interpretativo', 2, 'Vivienda habitual', 2, 2),
        ('IRPF-2024-002', 'interpretativo', 1, 'Introducción', 1, 1),
        ('IRPF-2024-002', 'interpretativo', 2, 'Autónomos', 2, 2),
        ('LIS-2024-001', 'interpretativo', 1, 'Introducción', 1, 1),
        ('LIS-2024-001', 'interpretativo', 2, 'I+D+i', 2, 2),
    ]

    for doc_origen_tipo, doc_origen_ref, num, titulo, nivel, orden in secciones:
        lines.append(f"INSERT INTO documento_seccion (documento_origen_tipo, documento_origen_id, tipo_seccion, numero, titulo, nivel, orden) "
                     f"SELECT {sql_escape(doc_origen_tipo)}, d.id, {sql_escape(doc_origen_ref)}, {sql_escape(num)}, {sql_escape(titulo)}, {nivel}, {orden} "
                     f"FROM documento_interpretativo d WHERE d.referencia = {sql_escape(doc_origen_ref)};")
    lines.append("")

    # ── 8. empresa ────────────────────────────────────────────────
    lines.append("-- 8. empresa — empresas de referencia")

    empresas = [
        ('Telefónica, S.A.', 'A28012345', 'Madrid, España', 'registro_mercantil'),
        ('Inditex, S.A.', 'A15098765', 'A Coruña, España', 'registro_mercantil'),
        ('Banco Santander, S.A.', 'A30012345', 'Santander, España', 'registro_mercantil'),
        ('Iberdrola, S.A.', 'A48012345', 'Bilbao, España', 'registro_mercantil'),
        ('Mapfre, S.A.', 'A28098765', 'Madrid, España', 'registro_mercantil'),
    ]

    for nombre, nif, domicilio, fuente in empresas:
        h = content_hash(nombre)
        lines.append(f"INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial, content_hash) VALUES ({sql_escape(nombre)}, {sql_escape(nif)}, {sql_escape(domicilio)}, {sql_escape(fuente)}, {sql_escape(h)});")
    lines.append("")

    # ── 9. documento_empresa ──────────────────────────────────────
    lines.append("-- 9. documento_empresa — vínculos empresa-documento")

    doc_empresas = [
        ('VAT-2024-002', 1, 'contribuyente', 0.95, 'Empresa obligada a facturación electrónica'),
        ('VAT-2024-002', 2, 'contribuyente', 0.95, 'Empresa obligada a facturación electrónica'),
        ('VAT-2024-002', 3, 'contribuyente', 0.90, 'Entidad financiera sujeta a obligaciones'),
        ('IRPF-2024-001', 1, 'contribuyente', 0.90, 'Empresa con empleados con derecho a deducción'),
        ('IRPF-2024-002', 1, 'contribuyente', 0.95, 'Empresa con autónomos como empleados'),
        ('LIS-2024-001', 1, 'contribuyente', 0.95, 'Empresa con actividades I+D'),
        ('LIS-2024-001', 2, 'contribuyente', 0.95, 'Empresa con actividades I+D'),
    ]

    for doc_ref, emp_id, rol, confianza, nota in doc_empresas:
        lines.append(f"INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota) "
                     f"SELECT d.id, e.id, {sql_escape(rol)}, {confianza}, {sql_escape(nota)} "
                     f"FROM documento_interpretativo d, empresa e "
                     f"WHERE d.referencia = {sql_escape(doc_ref)} AND e.id = {emp_id};")
    lines.append("")

    # ── 10. obligacion_regulatoria ────────────────────────────────
    lines.append("-- 10. obligacion_regulatoria — obligaciones regulatorias")

    obligaciones = [
        ('OBL-IRPF-100', 'Presentar modelo 100 — IRPF anual', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'declaracion', 'contribuyente_irpf', 'anual', '100', 'general', 'vigente', 'interpretativo', 'IRPF-2024-001', 'Sección 1', None,
         'Obligación de presentar declaración anual del IRPF para contribuyentes con rentas superiores a umbral legal.',
         90, 'trimestral', 'del 1 al 20 de abril, julio, octubre y enero', 'evento_calendario', 'electronica',
         ' contribuyentes IRPF obligados a declarar ', '500', '6000000', 'voluntario', 'involuntario', 'demora', 4, 'no',
         json.dumps({"tipo": "modelo", "version": "2025", "canal": "electronico"}), '2024-12-20', 'seed_curado', 'curado'),
        ('OBL-IVA-303', 'Presentar modelo 303 — IVA trimestral', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'declaracion', 'empresario_iva', 'trimestral', '303', 'general', 'vigente', 'interpretativo', 'VAT-2024-001', 'Sección 1', None,
         'Obligación de autoliquidar IVA trimestralmente.',
         90, 'trimestral', 'del 1 al 20 de abril, julio, octubre y enero', 'evento_calendario', 'electronica',
         ' empresarios y profesionales sujetos a IVA ', '500', '6000000', 'voluntario', 'involuntario', 'demora', 4, 'no',
         json.dumps({"tipo": "modelo", "version": "2025", "canal": "electronico"}), '2024-12-20', 'seed_curado', 'curado'),
        ('OBL-IVA-390', 'Presentar modelo 390 — IVA anual', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'declaracion', 'empresario_iva', 'anual', '390', 'general', 'vigente', 'interpretativo', 'VAT-2024-001', 'Sección 2', None,
         'Obligación de presentar resumen anual del IVA.',
         90, 'anual', 'enero del año siguiente', 'evento_calendario', 'electronica',
         ' empresarios y profesionales sujetos a IVA ', '500', '6000000', 'voluntario', 'involuntario', 'demora', 4, 'no',
         json.dumps({"tipo": "modelo", "version": "2025", "canal": "electronico"}), '2024-12-20', 'seed_curado', 'curado'),
        ('OBL-FACT-001', 'Facturación electrónica', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'registro', 'empresario_iva', 'continua', None, 'general', 'vigente', 'interpretativo', 'VAT-2024-002', 'Sección 1', None,
         'Obligación de llevar libros registro de facturación en formato electrónico.',
         None, None, 'continua', 'evento_sistema', 'electronica',
         ' empresas obligadas a LRF ', None, None, None, None, None, 4, 'no',
         json.dumps({"tipo": "libro", "version": "electronic", "canal": "siae"}), '2024-12-20', 'seed_curado', 'curado'),
        ('OBL-347', 'Presentar modelo 347 — Operaciones con terceros', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'declaracion', 'declarante', 'anual', '347', 'general', 'vigente', 'interpretativo', 'VAT-2024-001', 'Sección 3', None,
         'Obligación de declarar operaciones con terceros superiores a umbral.',
         90, 'anual', 'febrero del año siguiente', 'evento_calendario', 'electronica',
         ' empresarios y profesionales con operaciones > 3005,06€ ', '500', '6000000', 'voluntario', 'involuntario', 'demora', 4, 'no',
         json.dumps({"tipo": "modelo", "version": "2025", "canal": "electronico"}), '2024-12-20', 'seed_curado', 'curado'),
        ('OBL-IRNR-124', 'Presentar modelo 124 — IRNR retenciones', 'AEAT', 'Agencia Estatal de Administración Tributaria', 'declaracion', 'retenedor_irnr', 'mensual', '124', 'irnr', 'vigente', 'interpretativo', 'IRPF-2024-002', 'Sección 2', None,
         'Obligación de declarar retenciones a no residentes.',
         90, 'mensual', 'primeros 20 días del mes siguiente', 'evento_calendario', 'electronica',
         ' retenedores de rentas a no residentes ', '500', '6000000', 'voluntario', 'involuntario', 'demora', 4, 'no',
         json.dumps({"tipo": "modelo", "version": "2025", "canal": "electronico"}), '2024-12-20', 'seed_curado', 'curado'),
    ]

    for codigo, nombre, fuente, organismo, tipo_obl, sujeto, periodicidad, modelo, ambito, estado, doc_origen_tipo, doc_origen_ref, seccion, anexo, nota, plazo, frecuencia, ventana, trigger, canal, obligados, sancion_min, sancion_max, recargo_v, recargo_iv, interes, prescripcion, deposito, fuentes, actualizacion, origen, estado_meta in obligaciones:
        linea = (f"INSERT INTO obligacion_regulatoria (codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia, "
                 f"documento_origen_tipo, documento_origen_ref, seccion_origen, anexo_origen, nota, plazo_dias, frecuencia_presentacion, ventana_presentacion, "
                 f"trigger_presentacion, canal_presentacion, obligados_resumen, sancion_min, sancion_max, recargo_voluntario, recargo_involuntario, interes_demora, "
                 f"prescripcion_anos, deposito_previo, fuentes_operativas, ultima_actualizacion, origen_metadato, estado_metadato) "
                 f"VALUES ({sql_escape(codigo)}, {sql_escape(nombre)}, {sql_escape(fuente)}, {sql_escape(organismo)}, {sql_escape(tipo_obl)}, {sql_escape(sujeto)}, "
                  f"{sql_escape(periodicidad)}, {sql_escape(modelo)}, {sql_escape(ambito)}, {sql_escape(estado)}, {sql_escape(doc_origen_tipo)}, {sql_escape(doc_origen_ref)}, "
                  f"{sql_escape(seccion)}, {sql_escape(anexo)}, {sql_escape(nota)}, {sql_escape(plazo)}, {sql_escape(frecuencia)}, {sql_escape(ventana)}, "
                 f"{sql_escape(trigger)}, {sql_escape(canal)}, {sql_escape(obligados)}, {sql_escape(sancion_min)}, {sql_escape(sancion_max)}, "
                 f"{sql_escape(recargo_v)}, {sql_escape(recargo_iv)}, {sql_escape(interes)}, {sql_escape(prescripcion)}, {sql_escape(deposito)}, "
                  f"{sql_escape(fuentes)}, {sql_escape(actualizacion)}, {sql_escape(origen)}, {sql_escape(estado_meta)});")
        lines.append(linea)
    lines.append("")

    # ── 11. micro_obligacion ──────────────────────────────────────
    lines.append("-- 11. micro_obligacion — micro-obligaciones desglose")

    micro_obligs = [
        ('MO-IRPF-001', 'Verificar datos personales', 'Recopilar y verificar DNI, NIE y datos fiscales del contribuyente', 'LGT art. 10', 'tributario', 'evento_presentacion', 'anual', 'contribuyente', 'baja', True),
        ('MO-IRPF-002', 'Calcular rendimientos del trabajo', 'Sumar todos los ingresos salariales del año', 'LIRPF art. 3', 'tributario', 'evento_calendario', 'anual', 'contribuyente', 'media', True),
        ('MO-IRPF-003', 'Aplicar retenciones', 'Sumar retenciones practicadas por empleadores', 'LIRPF art. 10', 'tributario', 'evento_calendario', 'trimestral', 'retenedor', 'baja', True),
        ('MO-IVA-001', 'Calcular cuota repercutida', 'Sumar IVA cobrado a clientes', 'LIVA art. 11', 'tributario', 'evento_calendario', 'trimestral', 'empresario', 'media', True),
        ('MO-IVA-002', 'Calcular cuota soportada', 'Sumar IVA pagado a proveedores', 'LIVA art. 10', 'tributario', 'evento_calendario', 'trimestral', 'empresario', 'media', True),
        ('MO-IVA-003', 'Liquidar diferencia', 'Restar soportada de repercutida', 'LIVA art. 12', 'tributario', 'evento_calendario', 'trimestral', 'empresario', 'alta', True),
        ('MO-FACT-001', 'Generar factura electrónica', 'Crear factura en formato XML/NFE', 'LIVA art. 15', 'tributario', 'evento_operacion', 'continua', 'empresario', 'media', True),
        ('MO-FACT-002', 'Registrar factura emitida', 'Cargar factura en Libro Registro', 'LIVA art. 29', 'tributario', 'evento_operacion', 'continua', 'empresario', 'baja', True),
        ('MO-347-001', 'Recopilar operaciones terceros', 'Agrupar operaciones por NIF de tercero', 'LGT art. 240', 'tributario', 'evento_calendario', 'anual', 'declarante', 'media', True),
        ('MO-347-002', 'Verificar umbral 3005,06€', 'Comparar total anual por tercero con umbral', 'LGT art. 240', 'tributario', 'evento_calendario', 'anual', 'declarante', 'alta', True),
    ]

    for codigo, nombre, desc, reg_rel, ambito, trigger, frecuencia, owner, severidad, activo in micro_obligs:
        lines.append(f"INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) "
                     f"VALUES ({sql_escape(codigo)}, {sql_escape(nombre)}, {sql_escape(desc)}, {sql_escape(reg_rel)}, {sql_escape(ambito)}, {sql_escape(trigger)}, {sql_escape(frecuencia)}, {sql_escape(owner)}, {sql_escape(severidad)}, {activo});")
    lines.append("")

    # ── 12. obligacion_micro_obligacion ───────────────────────────
    lines.append("-- 12. obligacion_micro_obligacion — vinculación")

    micro_links = [
        ('OBL-IRPF-100', 'MO-IRPF-001', 1),
        ('OBL-IRPF-100', 'MO-IRPF-002', 2),
        ('OBL-IRPF-100', 'MO-IRPF-003', 3),
        ('OBL-IVA-303', 'MO-IVA-001', 1),
        ('OBL-IVA-303', 'MO-IVA-002', 2),
        ('OBL-IVA-303', 'MO-IVA-003', 3),
        ('OBL-FACT-001', 'MO-FACT-001', 1),
        ('OBL-FACT-001', 'MO-FACT-002', 2),
        ('OBL-347', 'MO-347-001', 1),
        ('OBL-347', 'MO-347-002', 2),
    ]

    for obl_codigo, micro_codigo, orden in micro_links:
        lines.append(f"INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden, evidencia_requerida) "
                     f"SELECT o.id, m.id, {orden}, 'registro_automatico' "
                     f"FROM obligacion_regulatoria o, micro_obligacion m "
                     f"WHERE o.codigo = {sql_escape(obl_codigo)} AND m.codigo = {sql_escape(micro_codigo)};")
    lines.append("")

    # ── 13. obligacion_documento ──────────────────────────────────
    lines.append("-- 13. obligacion_documento — vínculos obligación-documento")

    obl_doc_links = [
        ('OBL-IRPF-100', 'IRPF-2024-001', 'implementa'),
        ('OBL-IVA-303', 'VAT-2024-001', 'implementa'),
        ('OBL-IVA-390', 'VAT-2024-001', 'complementa'),
        ('OBL-FACT-001', 'VAT-2024-002', 'implementa'),
        ('OBL-347', 'VAT-2024-001', 'complementa'),
        ('OBL-IRNR-124', 'IRPF-2024-002', 'implementa'),
    ]

    for obl_codigo, doc_ref, tipo_rel in obl_doc_links:
        lines.append(f"INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion) "
                     f"SELECT o.id, d.id, {sql_escape(tipo_rel)} "
                     f"FROM obligacion_regulatoria o, documento_interpretativo d "
                     f"WHERE o.codigo = {sql_escape(obl_codigo)} AND d.referencia = {sql_escape(doc_ref)};")
    lines.append("")

    # ── 14. documento_articulo — vínculos documento-artículo ──────
    lines.append("-- 14. documento_articulo — vínculos documento-artículo")

    doc_art_links = [
        ('IRPF-2024-001', 'LIRPF:16', 'implementa', 0.95, 'Declaración anual IRPF'),
        ('IRPF-2024-001', 'LIRPF:17', 'implementa', 0.90, 'Forma de presentación'),
        ('IRPF-2024-002', 'LIRPF:10', 'interpreta', 0.92, 'Retenciones e ingresos a cuenta'),
        ('IRPF-2024-002', 'LIRPF:19', 'interpreta', 0.88, 'Pagos fraccionados'),
        ('VAT-2024-001', 'LIVA:1', 'interpreta', 0.95, 'Hecho imponible IVA'),
        ('VAT-2024-001', 'LIVA:12', 'implementa', 0.90, 'Autoliquidaciones'),
        ('VAT-2024-002', 'LIVA:15', 'implementa', 0.95, 'Facturación'),
        ('LIS-2024-001', 'LIS:5', 'interpreta', 0.90, 'Deducciones I+D'),
    ]

    for doc_ref, art_ref, metodo, confianza, nota in doc_art_links:
        norma_codigo, art_numero = art_ref.split(':')
        lines.append(f"INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota) "
                     f"SELECT d.id, a.id, {sql_escape(metodo)}, {confianza}, {sql_escape(nota)} "
                     f"FROM documento_interpretativo d, articulo a, norma n "
                     f"WHERE d.referencia = {sql_escape(doc_ref)} AND a.norma_id = n.id AND n.codigo = {sql_escape(norma_codigo)} AND a.numero = {sql_escape(art_numero)};")
    lines.append("")

    # ── 15. embedding_version ─────────────────────────────────────
    lines.append("-- 15. embedding_version — tracking de embeddings generados")

    embeddings = [
        ('documento_interpretativo', 'VAT-2024-001', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('documento_interpretativo', 'VAT-2024-002', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('documento_interpretativo', 'IRPF-2024-001', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('documento_interpretativo', 'IRPF-2024-002', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('documento_interpretativo', 'LIS-2024-001', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('norma', 'LGT', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('norma', 'LIRPF', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('norma', 'LIVA', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('norma', 'LIS', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('articulo', 'LGT:1', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('articulo', 'LIRPF:1', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
        ('articulo', 'LIVA:1', 'esdata-text-embedding-3-small', 256, '2024-12-20'),
    ]

    for entity_table, ref, model_name, dimensions, fecha in embeddings:
        if entity_table == 'documento_interpretativo':
            ref_col = 'referencia'
        elif entity_table == 'norma':
            ref_col = 'codigo'
        elif entity_table == 'articulo':
            ref_col = 'articulo_ref'
        else:
            ref_col = 'codigo'

        if entity_table == 'articulo':
            norma_codigo, art_numero = ref.split(':')
            lines.append(f"INSERT INTO embedding_version (entity_table, entity_id, model_name, content_hash, dimensions, created_at) "
                         f"SELECT '{entity_table}', a.id, {sql_escape(model_name)}, {sql_escape(content_hash(ref))}, {dimensions}, {sql_escape(fecha)} "
                         f"FROM articulo a, norma n WHERE a.norma_id = n.id AND n.codigo = {sql_escape(norma_codigo)} AND a.numero = {sql_escape(art_numero)};")
        elif entity_table == 'documento_interpretativo':
            lines.append(f"INSERT INTO embedding_version (entity_table, entity_id, model_name, content_hash, dimensions, created_at) "
                         f"SELECT '{entity_table}', d.id, {sql_escape(model_name)}, {sql_escape(content_hash(ref))}, {dimensions}, {sql_escape(fecha)} "
                         f"FROM documento_interpretativo d WHERE d.referencia = {sql_escape(ref)};")
        else:
            lines.append(f"INSERT INTO embedding_version (entity_table, entity_id, model_name, content_hash, dimensions, created_at) "
                         f"SELECT '{entity_table}', n.id, {sql_escape(model_name)}, {sql_escape(content_hash(ref))}, {dimensions}, {sql_escape(fecha)} "
                         f"FROM norma n WHERE n.codigo = {sql_escape(ref)};")
    lines.append("")

    return "\n".join(lines)

if __name__ == '__main__':
    sql = generate_seed()
    with open('scripts/seed-corpus-documental.sql', 'w') as f:
        f.write(sql)
    print(f"Generated SQL: {len(sql.splitlines())} lines, {len(sql)} bytes")
