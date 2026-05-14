#!/usr/bin/env python3
"""Emit SQL to load official Modelo 216 IRNR instructions and operational keys."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


ORDER_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497"
HELP_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/"
    "presentacion-declaraciones-ayuda-tecnica/modelo-216.html"
)


def fetch_hash(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "esdata-official-source-loader/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return hashlib.md5(response.read()).hexdigest()


def q(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def emit_instruction(seccion: str, titulo: str, contenido: str, source_url: str, source_hash: str, orden: int) -> str:
    return f"""
    INSERT INTO modelo_instruccion
        (campana_id, seccion, titulo, contenido, orden, texto, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(seccion)}, {q(titulo)}, {q(contenido)}, {orden}, {q(contenido)},
         {q(source_url)}, {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, seccion, titulo)
    DO UPDATE SET
        contenido = EXCLUDED.contenido,
        orden = EXCLUDED.orden,
        texto = EXCLUDED.texto,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_clave(codigo: str, etiqueta: str, tipo: str, descripcion: str, criterio: str, source_url: str, source_hash: str) -> str:
    return f"""
    INSERT INTO modelo_clave
        (campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
         criterio_aplicacion, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(codigo)}, {q(etiqueta)}, {q(descripcion)}, {q(tipo)}, {q(tipo)},
         {q(criterio)}, {q(source_url)}, {q(source_hash)}, v_capture_date)
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
    VALUES (v_modelo_id, {q(keyword)}, 'IRNR')
    ON CONFLICT DO NOTHING;
    """


def main() -> int:
    hashes = {url: fetch_hash(url) for url in (ORDER_URL, HELP_URL)}
    capture_date = date.today().isoformat()
    instructions = [
        emit_instruction(
            "aprobacion",
            "Aprobacion del Modelo 216",
            "La Orden EHA/3290/2008 aprueba el Modelo 216 para IRNR: rentas obtenidas sin mediacion de establecimiento permanente, retenciones e ingresos a cuenta.",
            ORDER_URL,
            hashes[ORDER_URL],
            10,
        ),
        emit_instruction(
            "obligados",
            "Obligados a presentar",
            "El Modelo 216 debe utilizarse por los sujetos obligados a retener o efectuar ingreso a cuenta sobre rentas obtenidas sin establecimiento permanente por contribuyentes del IRNR, salvo los supuestos que la Orden remite a declaraciones especificas.",
            ORDER_URL,
            hashes[ORDER_URL],
            20,
        ),
        emit_instruction(
            "sin_retencion",
            "Uso cuando no procede retener",
            "El Modelo 216 tambien se utiliza cuando, conforme al articulo 31.4 TRLIRNR, no procede practicar retencion o ingreso a cuenta.",
            ORDER_URL,
            hashes[ORDER_URL],
            30,
        ),
        emit_instruction(
            "exclusiones",
            "Rentas excluidas",
            "La Orden excluye de este modelo, entre otras, determinadas rentas exentas del articulo 14.1.a TRLIRNR, rentas de valores emitidos en Espana por no residentes, cuentas de no residentes, intereses de Deuda Publica y rentas exceptuadas de retener por el Reglamento IRNR.",
            ORDER_URL,
            hashes[ORDER_URL],
            40,
        ),
        emit_instruction(
            "plazo",
            "Plazo de presentacion",
            "Con caracter general el Modelo 216 se presenta en los veinte primeros dias naturales de abril, julio, octubre y enero; para grandes empresas, en los veinte primeros dias naturales de cada mes por el mes inmediato anterior, con regla especial para julio.",
            ORDER_URL,
            hashes[ORDER_URL],
            50,
        ),
        emit_instruction(
            "presentacion_aeat",
            "Presentacion electronica",
            "La ayuda tecnica AEAT del Modelo 216 permite identificacion con Cl@ve, certificado electronico o DNIe, importar ficheros .216 ajustados al diseno de registro, validar y formalizar ingreso/devolucion.",
            HELP_URL,
            hashes[HELP_URL],
            60,
        ),
    ]
    claves = [
        emit_clave("TRIMESTRAL", "Periodicidad trimestral", "PERIODO", "Presentacion general trimestral.", "Usar para obligados no considerados gran empresa: abril, julio, octubre y enero.", ORDER_URL, hashes[ORDER_URL]),
        emit_clave("MENSUAL_GRAN_EMPRESA", "Periodicidad mensual gran empresa", "PERIODO", "Presentacion mensual para retenedores u obligados con condicion de gran empresa.", "Usar cuando concurra la condicion de gran empresa indicada por la Orden.", ORDER_URL, hashes[ORDER_URL]),
        emit_clave("SIN_RETENCION_ART31_4", "No procede practicar retencion", "SUPUESTO", "Uso del modelo cuando no procede retener conforme al articulo 31.4 TRLIRNR.", "Usar cuando exista obligacion de declarar negativa sin retencion o ingreso a cuenta.", ORDER_URL, hashes[ORDER_URL]),
        emit_clave("RESULTADO_INGRESAR", "Resultado a ingresar", "RESULTADO", "Declaracion con deuda tributaria a ingresar.", "Usar si hay importe a ingresar y debe formalizarse el pago/NRC segun la ayuda AEAT.", HELP_URL, hashes[HELP_URL]),
        emit_clave("RESULTADO_NEGATIVA", "Declaracion negativa", "RESULTADO", "Declaracion sin importe a ingresar.", "Usar en los supuestos de declaracion negativa previstos por la Orden.", ORDER_URL, hashes[ORDER_URL]),
    ]
    keywords = [
        emit_keyword(keyword)
        for keyword in [
            "modelo 216",
            "IRNR retenciones",
            "retencion no residente",
            "ingreso a cuenta no residente",
            "rentas sin establecimiento permanente",
            "declaracion negativa IRNR",
        ]
    ]
    sql = f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    SELECT id INTO v_modelo_id FROM aeat_modelo WHERE codigo = '216';
    IF v_modelo_id IS NULL THEN
        RAISE EXCEPTION 'Modelo 216 not found';
    END IF;

    SELECT id INTO v_campana_id
    FROM modelo_campana
    WHERE modelo_id = v_modelo_id AND activo = true
    ORDER BY campana DESC
    LIMIT 1;

    IF v_campana_id IS NULL THEN
        RAISE EXCEPTION 'Active campaign for Modelo 216 not found';
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
