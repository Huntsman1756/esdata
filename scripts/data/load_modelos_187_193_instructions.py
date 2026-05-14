#!/usr/bin/env python3
"""Emit SQL to load official Modelo 187 and 193 instructions and keys."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


ORDER_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2024-27528"

MODEL_SOURCES = {
    "187": {
        "dr_url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/DR_Modelo_187_2022.pdf",
        "help_url": "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-181-189/modelo-187.html",
    },
    "193": {
        "dr_url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/DR_Modelo_193_2025.pdf",
        "help_url": "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-190-198/modelo-193.html",
    },
}


def fetch_hash(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "esdata-official-source-loader/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return hashlib.md5(response.read()).hexdigest()


def q(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def emit_instruction(
    seccion: str,
    titulo: str,
    contenido: str,
    source_url: str,
    source_hash: str,
    orden: int,
    casilla_referencia: str | None = None,
) -> str:
    return f"""
    INSERT INTO modelo_instruccion
        (campana_id, seccion, titulo, contenido, orden, texto,
         casilla_referencia, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(seccion)}, {q(titulo)}, {q(contenido)}, {orden},
         {q(contenido)}, {q(casilla_referencia)}, {q(source_url)},
         {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, seccion, titulo)
    DO UPDATE SET
        contenido = EXCLUDED.contenido,
        orden = EXCLUDED.orden,
        texto = EXCLUDED.texto,
        casilla_referencia = EXCLUDED.casilla_referencia,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_clave(
    codigo: str,
    etiqueta: str,
    tipo: str,
    descripcion: str,
    criterio: str,
    source_url: str,
    source_hash: str,
) -> str:
    return f"""
    INSERT INTO modelo_clave
        (campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
         criterio_aplicacion, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(codigo)}, {q(etiqueta)}, {q(descripcion)}, {q(tipo)},
         {q(tipo)}, {q(criterio)}, {q(source_url)}, {q(source_hash)},
         v_capture_date)
    ON CONFLICT (campana_id, codigo)
    DO UPDATE SET
        etiqueta = EXCLUDED.etiqueta,
        descripcion = EXCLUDED.descripcion,
        tipo_clave = EXCLUDED.tipo_clave,
        tipo = EXCLUDED.tipo,
        criterio_aplicacion = EXCLUDED.criterio_aplicacion,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_keyword(keyword: str, dominio: str) -> str:
    return f"""
    INSERT INTO modelo_trigger_keyword (modelo_id, keyword, dominio)
    VALUES (v_modelo_id, {q(keyword)}, {q(dominio)})
    ON CONFLICT DO NOTHING;
    """


def model_187_sql(hashes: dict[str, str]) -> str:
    dr_url = MODEL_SOURCES["187"]["dr_url"]
    help_url = MODEL_SOURCES["187"]["help_url"]
    instructions = [
        emit_instruction("aprobacion", "Modelo 187", "La Orden HAC/1504/2024 modifica la Orden HAP/1608/2014, que aprueba el Modelo 187 de acciones y participaciones de instituciones de inversion colectiva.", ORDER_URL, hashes[ORDER_URL], 10),
        emit_instruction("objeto", "Objeto del Modelo 187", "El Modelo 187 informa acciones y participaciones representativas del capital o patrimonio de instituciones de inversion colectiva y resume retenciones e ingresos a cuenta asociados.", dr_url, hashes[dr_url], 20),
        emit_instruction("tipo_socio", "Tipo de socio o participe", "El diseno AEAT distingue residentes y no residentes con establecimiento permanente, no residentes sin establecimiento permanente, regimen especial IRNR, y entidades comercializadoras extranjeras.", dr_url, hashes[dr_url], 30, "81"),
        emit_instruction("tipo_operacion", "Tipo de operacion", "El diseno AEAT usa el campo Tipo de operacion para adquisiciones, transmisiones o reembolsos, ventas de derechos de suscripcion, traspasos, fusiones y liquidaciones de SICAV.", dr_url, hashes[dr_url], 40, "104"),
        emit_instruction("presentacion", "Presentacion tecnica AEAT", "La ayuda tecnica AEAT del Modelo 187 remite a presentacion mediante formulario o fichero y a los disenos de registro vigentes.", help_url, hashes[help_url], 50),
    ]
    claves: list[str] = []
    for code, label in [
        ("SOCIO_R", "Residentes y no residentes que obtengan rentas mediante establecimiento permanente"),
        ("SOCIO_N", "No residentes que obtengan rentas sin mediacion de establecimiento permanente"),
        ("SOCIO_E", "Personas fisicas residentes en Espana contribuyentes por IRNR del articulo 9.2 LIRPF"),
        ("SOCIO_I", "Contribuyente IRPF del regimen especial de tributacion por IRNR del articulo 93 LIRPF"),
        ("SOCIO_C", "Entidades residentes en el extranjero comercializadoras de IIC espanolas por cuenta de clientes"),
    ]:
        claves.append(emit_clave(code, label, "TIPO_SOCIO", label, "Usar en la posicion 81 del registro de tipo 2.", dr_url, hashes[dr_url]))
    for code, label in [
        ("NAT_F", "Persona fisica"),
        ("NAT_J", "Persona juridica"),
        ("NAT_E", "Entidad en regimen de atribucion de rentas"),
    ]:
        claves.append(emit_clave(code, label, "NATURALEZA_SOCIO", label, "Usar en la posicion 82 del registro de tipo 2.", dr_url, hashes[dr_url]))
    for code, label in [
        ("OPERACION_A", "Adquisiciones salvo claves B, I o R"),
        ("OPERACION_B", "Adquisiciones por reinversion de importes de transmision o reembolso sin computo de ganancia o perdida"),
        ("OPERACION_C", "Enajenaciones de participaciones en fondos cotizados o acciones de SICAV indice cotizadas"),
        ("OPERACION_E", "Enajenaciones salvo claves C, F, G, H, J, K, L, P, Q o T"),
        ("OPERACION_F", "Enajenaciones sin computo de ganancia o perdida por aplicacion del articulo 94.1.a LIRPF"),
        ("OPERACION_G", "Transmisiones o reembolsos de entidades comercializadoras extranjeras sin retencion por exencion"),
        ("OPERACION_H", "Transmisiones o reembolsos de entidades comercializadoras extranjeras con retencion IRNR"),
        ("OPERACION_I", "Adquisiciones por reinversion con comunicacion del articulo 28.2 LIIC"),
        ("OPERACION_J", "Enajenaciones sin computo de ganancia o perdida con comunicacion del articulo 28.2 LIIC"),
        ("OPERACION_K", "Enajenaciones de IIC de contribuyentes del regimen especial de desplazados sin renta territorial espanola"),
        ("OPERACION_L", "Enajenaciones de IIC de contribuyentes del regimen especial de desplazados distintas de la clave K"),
        ("OPERACION_M", "Venta de derechos de suscripcion sometidos a retencion"),
        ("OPERACION_N", "Venta de derechos de suscripcion de contribuyentes desplazados sin renta territorial espanola"),
        ("OPERACION_O", "Venta de derechos de suscripcion de contribuyentes desplazados distinta de la clave N"),
        ("OPERACION_P", "Transmisiones por canje derivadas de fusion de IIC con computo de ganancia o perdida"),
        ("OPERACION_Q", "Transmisiones o reembolsos vinculados a traspaso posterior a fusion de IIC"),
        ("OPERACION_R", "Adquisiciones o suscripciones por reinversion de cuota de liquidacion de SICAV"),
        ("OPERACION_T", "Transmision o cancelacion derivada de liquidacion de SICAV acogida a la DT 41 LIS"),
    ]:
        claves.append(emit_clave(code, label, "TIPO_OPERACION", label, "Usar en la posicion 104 del registro de tipo 2.", dr_url, hashes[dr_url]))
    for code, label in [("RESULTADO_O", "Comunicacion de circunstancias de los articulos 97.2 RIRPF y 13.3 RIRNR"), ("RESULTADO_R", "No concurren las circunstancias anteriores")]:
        claves.append(emit_clave(code, label, "TIPO_RESULTADO", label, "Usar en el campo Tipo de resultado.", dr_url, hashes[dr_url]))
    keywords = [
        emit_keyword(keyword, "IIC")
        for keyword in [
            "modelo 187",
            "participaciones IIC",
            "fondos de inversion",
            "acciones sicav",
            "transmision participaciones",
            "reembolso fondos",
            "derechos de suscripcion IIC",
        ]
    ]
    return emit_model_block("187", instructions, claves, keywords)


def model_193_sql(hashes: dict[str, str]) -> str:
    dr_url = MODEL_SOURCES["193"]["dr_url"]
    help_url = MODEL_SOURCES["193"]["help_url"]
    instructions = [
        emit_instruction("aprobacion", "Modelo 193", "La Orden HAC/1504/2024 modifica la Orden EHA/3377/2011, relativa al Modelo 193 de retenciones e ingresos a cuenta sobre determinados rendimientos del capital mobiliario.", ORDER_URL, hashes[ORDER_URL], 10),
        emit_instruction("objeto", "Objeto del Modelo 193", "El Modelo 193 resume retenciones e ingresos a cuenta del IRPF sobre determinados rendimientos del capital mobiliario y retenciones de IS e IRNR con establecimiento permanente sobre determinadas rentas.", dr_url, hashes[dr_url], 20),
        emit_instruction("clave_percepcion", "Clave de percepcion", "El diseno AEAT distingue rendimientos por participacion en fondos propios, cesion a terceros de capitales propios, otros rendimientos y cesion a entidades vinculadas.", dr_url, hashes[dr_url], 30, "92"),
        emit_instruction("naturaleza", "Naturaleza asociada a la percepcion", "La naturaleza se consigna segun la clave de percepcion A, B, C o D y concreta el origen del rendimiento o renta.", dr_url, hashes[dr_url], 40, "93-94"),
        emit_instruction("presentacion", "Presentacion tecnica AEAT", "La ayuda tecnica AEAT del Modelo 193 remite a presentacion mediante formulario o fichero y a los disenos de registro vigentes.", help_url, hashes[help_url], 50),
    ]
    claves: list[str] = []
    for code, label in [
        ("PERCEPCION_A", "Rendimientos o rentas por participacion en fondos propios de cualquier entidad"),
        ("PERCEPCION_B", "Rendimientos o rentas por cesion a terceros de capitales propios distintos de la letra D"),
        ("PERCEPCION_C", "Otros rendimientos de capital mobiliario o rentas no incluidos en A, B o D"),
        ("PERCEPCION_D", "Rendimientos por cesion a entidades vinculadas cuando el perceptor sea contribuyente IRPF"),
    ]:
        claves.append(emit_clave(code, label, "CLAVE_PERCEPCION", label, "Usar en la posicion 92 del registro de tipo 2.", dr_url, hashes[dr_url]))
    for code, label in [
        ("NAT_A_01", "Primas por asistencia a juntas"),
        ("NAT_A_02", "Dividendos y participaciones en beneficios"),
        ("NAT_A_03", "Rendimientos de activos que faculten para participar en beneficios o conceptos analogos"),
        ("NAT_A_04", "Rendimientos por constitucion o cesion de derechos de uso o disfrute sobre valores"),
        ("NAT_A_05", "Otras utilidades procedentes de una entidad por condicion de socio o participe"),
        ("NAT_A_06", "Rendimientos exentos"),
        ("NAT_A_07", "Dividendos y beneficios distribuidos por IIC"),
        ("NAT_A_08", "Dividendos no sometidos a retencion ni ingreso a cuenta"),
        ("NAT_BD_01", "Intereses de obligaciones, bonos, certificados de deposito u otros titulos privados"),
        ("NAT_BD_02", "Intereses de obligaciones, bonos, cedulas, deuda publica u otros titulos publicos"),
        ("NAT_BD_03", "Intereses de prestamos no bancarios"),
        ("NAT_BD_04", "Rendimientos con regimen transitorio de beneficios en operaciones financieras"),
        ("NAT_BD_05", "Rendimientos por transmision, cesion o transferencia de credito de entidad financiera"),
        ("NAT_BD_06", "Otros rendimientos de capital mobiliario por cesion a terceros"),
        ("NAT_BD_07", "Rendimientos exentos"),
        ("NAT_C_01", "Propiedad intelectual cuando el perceptor no sea el autor"),
        ("NAT_C_02", "Propiedad industrial no afecta a actividades economicas del perceptor"),
        ("NAT_C_03", "Prestacion de asistencia tecnica fuera de actividad economica"),
        ("NAT_C_04", "Arrendamiento o subarrendamiento de bienes muebles, negocios o minas"),
        ("NAT_C_05", "Rentas vitalicias o temporales por imposicion de capitales"),
        ("NAT_C_06", "Cesion del derecho de explotacion de imagen para perceptores IRPF"),
        ("NAT_C_07", "Subarrendamiento de bienes inmuebles urbanos sin actividad economica"),
        ("NAT_C_08", "Cesion del derecho de explotacion de imagen para IS o IRNR con establecimiento permanente"),
        ("NAT_C_09", "Premios de juegos, concursos, rifas o combinaciones aleatorias"),
        ("NAT_C_10", "Cargos de administrador o consejero en otras sociedades"),
        ("NAT_C_12", "Otros rendimientos a integrar en la base imponible general"),
        ("NAT_C_13", "Otros rendimientos a integrar en la base imponible del ahorro"),
        ("NAT_C_14", "Otros rendimientos cuando el perceptor no sea contribuyente IRPF"),
        ("NAT_C_15", "Anticipos por cesion de explotacion de derechos de autor devengados en varios anios"),
    ]:
        claves.append(emit_clave(code, label, "NATURALEZA", label, "Usar en posiciones 93-94 segun clave de percepcion.", dr_url, hashes[dr_url]))
    for code, label in [
        ("PAGO_1", "Como emisor"),
        ("PAGO_2", "Como mediador de valor nacional"),
        ("PAGO_3", "Como mediador de valor extranjero"),
        ("PAGO_4", "Como mediador de valor extranjero no retenedor"),
        ("PAGO_5", "Como mediador de otros rendimientos por cesion a terceros de capitales propios"),
    ]:
        claves.append(emit_clave(code, label, "PAGO", label, "Usar en posicion 95 para claves de percepcion A, B o D.", dr_url, hashes[dr_url]))
    keywords = [
        emit_keyword(keyword, "CAPITAL_MOBILIARIO")
        for keyword in [
            "modelo 193",
            "capital mobiliario",
            "retenciones capital mobiliario",
            "dividendos",
            "intereses",
            "cesion a terceros de capitales propios",
            "clave percepcion 193",
        ]
    ]
    return emit_model_block("193", instructions, claves, keywords)


def emit_model_block(modelo: str, instructions: list[str], claves: list[str], keywords: list[str]) -> str:
    return f"""
    SELECT id INTO v_modelo_id FROM aeat_modelo WHERE codigo = {q(modelo)};
    IF v_modelo_id IS NULL THEN
        RAISE EXCEPTION 'Modelo {modelo} not found';
    END IF;

    SELECT id INTO v_campana_id
    FROM modelo_campana
    WHERE modelo_id = v_modelo_id AND activo = true
    ORDER BY campana DESC
    LIMIT 1;

    IF v_campana_id IS NULL THEN
        RAISE EXCEPTION 'Active campaign for Modelo {modelo} not found';
    END IF;

    DELETE FROM modelo_clave
    WHERE campana_id IN (SELECT id FROM modelo_campana WHERE modelo_id = v_modelo_id);
    DELETE FROM modelo_instruccion
    WHERE campana_id IN (SELECT id FROM modelo_campana WHERE modelo_id = v_modelo_id);

    {' '.join(instructions)}
    {' '.join(claves)}
    {' '.join(keywords)}
    """


def main() -> int:
    urls = [ORDER_URL]
    for source in MODEL_SOURCES.values():
        urls.extend([source["dr_url"], source["help_url"]])
    hashes = {url: fetch_hash(url) for url in urls}
    capture_date = date.today().isoformat()
    sql = f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    {model_187_sql(hashes)}
    {model_193_sql(hashes)}
END $$;
"""
    sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
