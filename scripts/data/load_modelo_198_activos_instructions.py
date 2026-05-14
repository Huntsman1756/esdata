#!/usr/bin/env python3
"""Emit SQL to load official Modelo 198 instructions and keys."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


ORDER_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2024-27528"
DR_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
    "DR_100_199/DR_Modelo_198_2024.pdf"
)
HELP_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/"
    "declaraciones-informativas-ayuda-tecnica/modelos-190-198/modelo-198.html"
)


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
    source_hash: str,
    source_url: str = DR_URL,
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


def emit_keyword(keyword: str) -> str:
    return f"""
    INSERT INTO modelo_trigger_keyword (modelo_id, keyword, dominio)
    VALUES (v_modelo_id, {q(keyword)}, 'ACTIVOS_FINANCIEROS')
    ON CONFLICT DO NOTHING;
    """


def main() -> int:
    hashes = {url: fetch_hash(url) for url in (ORDER_URL, DR_URL, HELP_URL)}
    capture_date = date.today().isoformat()

    instructions = [
        emit_instruction(
            "aprobacion",
            "Aprobacion del Modelo 198",
            "La Orden HAC/1504/2024 modifica la Orden EHA/3895/2004, que aprueba el Modelo 198 de declaracion anual de operaciones con activos financieros y otros valores mobiliarios.",
            ORDER_URL,
            hashes[ORDER_URL],
            10,
        ),
        emit_instruction(
            "objeto",
            "Objeto de la declaracion",
            "El Modelo 198 es una declaracion informativa anual de operaciones con activos financieros y otros valores mobiliarios.",
            ORDER_URL,
            hashes[ORDER_URL],
            20,
        ),
        emit_instruction(
            "diseno_registro",
            "Diseno de registro",
            "El diseno de registro AEAT 2024 define campos de operacion, origen, mercado, representacion, valor, importes y datos del declarado para los registros del Modelo 198.",
            DR_URL,
            hashes[DR_URL],
            30,
        ),
        emit_instruction(
            "clave_origen",
            "Clave de origen",
            "El campo Clave de origen distingue operaciones a titulo oneroso, lucrativo inter vivos, adjudicacion o aplicacion, y lucrativo mortis causa.",
            DR_URL,
            hashes[DR_URL],
            40,
            "133",
        ),
        emit_instruction(
            "clave_operacion",
            "Clave de operacion",
            "El campo Clave de operacion identifica la naturaleza de la operacion: adquisicion, canje, conversion, cancelacion, reducciones de capital, prestamos de valores, suscripcion, transmision, fusion, escision u otras operaciones previstas en el diseno.",
            DR_URL,
            hashes[DR_URL],
            50,
            "134",
        ),
        emit_instruction(
            "clave_valor",
            "Clave de valor",
            "El campo Clave de valor identifica la clase de valor o derecho: acciones, activos financieros con rendimientos explicitos o implicitos, segregados, derechos, preferentes, IIC, contratos por diferencias u otros.",
            DR_URL,
            hashes[DR_URL],
            60,
            "137",
        ),
        emit_instruction(
            "ayuda_aeat",
            "Pagina AEAT del Modelo 198",
            "La sede AEAT mantiene la pagina del Modelo 198 dentro de retenciones, ingresos a cuenta y pagos fraccionados, con acceso a gestiones, informacion y ayuda del modelo.",
            HELP_URL,
            hashes[HELP_URL],
            70,
        ),
    ]

    claves: list[str] = []
    for codigo, etiqueta in [
        ("ORIGEN_A", "Operaciones a titulo oneroso"),
        ("ORIGEN_B", "Operaciones a titulo lucrativo inter vivos"),
        ("ORIGEN_C", "Operaciones de adjudicacion o aplicacion distintas del resto de claves"),
        ("ORIGEN_D", "Operaciones a titulo lucrativo mortis causa"),
    ]:
        claves.append(
            emit_clave(codigo, etiqueta, "CLAVE_ORIGEN", etiqueta, "Usar en la posicion 133 del registro de tipo 2.", hashes[DR_URL])
        )

    for codigo, etiqueta in [
        ("OPERACION_A", "Adquisicion o constitucion de derechos"),
        ("OPERACION_C", "Canje"),
        ("OPERACION_D", "Conversion"),
        ("OPERACION_E", "Cancelacion o extincion de derechos"),
        ("OPERACION_F", "Devolucion de prima de emision"),
        ("OPERACION_G", "Reduccion de capital con devolucion de aportaciones"),
        ("OPERACION_H", "Devolucion de prima de emision de valores no admitidos a negociacion"),
        ("OPERACION_I", "Reduccion de capital con devolucion de aportaciones de valores no admitidos a negociacion"),
        ("OPERACION_J", "Reduccion de capital con amortizacion de valores"),
        ("OPERACION_K", "Reduccion de capital procedente de beneficios no distribuidos"),
        ("OPERACION_L", "Split y contrasplit de valores"),
        ("OPERACION_O", "Prestamos de valores regulados en la Ley 62/2003"),
        ("OPERACION_P", "Constitucion prestamo de valores"),
        ("OPERACION_Q", "Extincion prestamo de valores"),
        ("OPERACION_S", "Suscripcion"),
        ("OPERACION_T", "Transmision, amortizacion o reembolso"),
        ("OPERACION_V", "Canje de valores que cumpla los requisitos del articulo 80 LIS"),
        ("OPERACION_X", "Entrega de acciones liberadas"),
        ("OPERACION_Y", "Fusion que cumpla los requisitos del articulo 77 LIS"),
        ("OPERACION_Z", "Escision que cumpla los requisitos del articulo 77 LIS"),
    ]:
        claves.append(
            emit_clave(codigo, etiqueta, "CLAVE_OPERACION", etiqueta, "Usar en la posicion 134 del registro de tipo 2.", hashes[DR_URL])
        )

    for codigo, etiqueta in [
        ("MERCADO_A", "Mercado secundario oficial de valores espanol"),
        ("MERCADO_B", "Mercado secundario oficial de valores extranjeros de la Union Europea"),
        ("MERCADO_C", "Otros mercados nacionales"),
        ("MERCADO_D", "Otros mercados extranjeros"),
        ("MERCADO_F", "Operaciones intervenidas por fedatarios publicos"),
        ("MERCADO_O", "Operaciones realizadas fuera de mercado OTC"),
        ("MERCADO_P", "Mercado secundario oficial de valores extranjeros excluidos los de la Union Europea"),
    ]:
        claves.append(
            emit_clave(codigo, etiqueta, "CLAVE_MERCADO", etiqueta, "Usar en la posicion 135 del registro de tipo 2.", hashes[DR_URL])
        )

    for codigo, etiqueta in [
        ("REPRESENTACION_A", "Valores representados mediante anotaciones en cuenta"),
        ("REPRESENTACION_B", "Valores no representados mediante anotaciones en cuenta"),
    ]:
        claves.append(
            emit_clave(codigo, etiqueta, "CLAVE_REPRESENTACION", etiqueta, "Usar en la posicion 136 del registro de tipo 2.", hashes[DR_URL])
        )

    for codigo, etiqueta in [
        ("VALOR_A", "Acciones y participaciones en sociedades de responsabilidad limitada"),
        ("VALOR_B", "Activos financieros con rendimientos explicitos excluidos de retencion"),
        ("VALOR_C", "Activos financieros con rendimientos implicitos excluidos de retencion"),
        ("VALOR_D", "Principales segregados"),
        ("VALOR_E", "Cupones segregados"),
        ("VALOR_F", "Derechos de garantia"),
        ("VALOR_G", "Derechos de disfrute"),
        ("VALOR_H", "Derechos de suscripcion"),
        ("VALOR_K", "Participaciones preferentes u otros instrumentos de deuda"),
        ("VALOR_M", "Acciones y participaciones en instituciones de inversion colectiva"),
        ("VALOR_J", "Activos financieros de entes publicos territoriales con rendimiento explicito excluidos de retencion"),
        ("VALOR_L", "Contratos por diferencias"),
        ("VALOR_I", "Otros"),
    ]:
        claves.append(
            emit_clave(codigo, etiqueta, "CLAVE_VALOR", etiqueta, "Usar en la posicion 137 del registro de tipo 2.", hashes[DR_URL])
        )

    keywords = [
        emit_keyword(keyword)
        for keyword in [
            "modelo 198",
            "activos financieros",
            "valores mobiliarios",
            "sociedad de valores",
            "operaciones con activos financieros",
            "transmision onerosa",
            "transmision no onerosa",
            "clave de operacion 198",
            "clave de valor 198",
            "clave de mercado 198",
        ]
    ]

    sql = f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    SELECT id INTO v_modelo_id FROM aeat_modelo WHERE codigo = '198';
    IF v_modelo_id IS NULL THEN
        RAISE EXCEPTION 'Modelo 198 not found';
    END IF;

    SELECT id INTO v_campana_id
    FROM modelo_campana
    WHERE modelo_id = v_modelo_id AND activo = true
    ORDER BY campana DESC
    LIMIT 1;

    IF v_campana_id IS NULL THEN
        RAISE EXCEPTION 'Active campaign for Modelo 198 not found';
    END IF;

    DELETE FROM modelo_clave
    WHERE campana_id IN (SELECT id FROM modelo_campana WHERE modelo_id = v_modelo_id);
    DELETE FROM modelo_instruccion
    WHERE campana_id IN (SELECT id FROM modelo_campana WHERE modelo_id = v_modelo_id);

    {' '.join(instructions)}
    {' '.join(claves)}
    {' '.join(keywords)}
END $$;
"""
    sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
