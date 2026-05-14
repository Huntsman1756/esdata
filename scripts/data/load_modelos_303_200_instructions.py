#!/usr/bin/env python3
"""Emit SQL to load official partial instructions for Modelos 303 and 200."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


URL_303_INSTRUCTIONS = (
    "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/"
    "iva/modelo-303-iva-autoliquidacion_/instrucciones-2025.html"
)
URL_303_PRESENTATION = "https://sede.agenciatributaria.gob.es/Sede/iva/presentar-declaracion-iva-modelo-303.html"
URL_200_MODEL = "https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/modelo-200.html"
URL_200_PDF = "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GE04/200/Modelo_200.pdf"
URL_200_MANUAL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/"
    "manuales-practicos/manual-sociedades-2024/capitulo-01-cuestiones-generales/"
    "declaracion-impuesto-sociedades-cuestiones-generales.html"
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


def emit_keyword(keyword: str, dominio: str) -> str:
    return f"""
    INSERT INTO modelo_trigger_keyword (modelo_id, keyword, dominio)
    VALUES (v_modelo_id, {q(keyword)}, {q(dominio)})
    ON CONFLICT DO NOTHING;
    """


def emit_model_block(modelo: str, instructions: list[str], keywords: list[str]) -> str:
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

    DELETE FROM modelo_instruccion
    WHERE campana_id IN (SELECT id FROM modelo_campana WHERE modelo_id = v_modelo_id);

    {' '.join(instructions)}
    {' '.join(keywords)}
    """


def model_303_sql(hashes: dict[str, str]) -> str:
    instructions = [
        emit_instruction(
            "presentacion",
            "Presentacion electronica del Modelo 303",
            "Las instrucciones AEAT 2025 indican que el modelo 303 se presenta electronicamente y que para ejercicios anteriores debe accederse a Ejercicios anteriores.",
            URL_303_INSTRUCTIONS,
            hashes[URL_303_INSTRUCTIONS],
            10,
        ),
        emit_instruction(
            "iva_devengado",
            "IVA devengado",
            "Las instrucciones AEAT asignan las casillas 150-152 para bases al 0%, 01-03 para 4%, 04-06 para 10% y 07-09 para 21%. Tambien contemplan adquisiciones intracomunitarias de bienes en 10 y 11.",
            URL_303_INSTRUCTIONS,
            hashes[URL_303_INSTRUCTIONS],
            20,
            "01-11,150-152",
        ),
        emit_instruction(
            "recargo_equivalencia",
            "Recargo de equivalencia",
            "Las instrucciones AEAT incluyen casillas especificas para recargo de equivalencia, entre ellas 156-158, 168-170, 19-21 y 22-24 segun el tipo aplicable.",
            URL_303_INSTRUCTIONS,
            hashes[URL_303_INSTRUCTIONS],
            30,
            "156-170,19-24",
        ),
        emit_instruction(
            "iva_deducible",
            "IVA deducible",
            "Las instrucciones AEAT indican que si no hay IVA deducible no se declaran las casillas de IVA deducible; para el resto se utilizan las casillas 28 y siguientes segun el grupo aplicable.",
            URL_303_INSTRUCTIONS,
            hashes[URL_303_INSTRUCTIONS],
            40,
            "28 y siguientes",
        ),
        emit_instruction(
            "resultado",
            "Resultado de la autoliquidacion",
            "La pagina AEAT de presentacion del modelo 303 describe el procedimiento para presentar la declaracion de IVA y acceder a la ayuda Pre303 o al tramite de presentacion electronica.",
            URL_303_PRESENTATION,
            hashes[URL_303_PRESENTATION],
            50,
        ),
    ]
    keywords = [
        emit_keyword(keyword, "IVA")
        for keyword in [
            "modelo 303",
            "IVA autoliquidacion",
            "IVA devengado",
            "IVA deducible",
            "base imponible IVA",
            "resultado modelo 303",
            "Pre303",
        ]
    ]
    return emit_model_block("303", instructions, keywords)


def model_200_sql(hashes: dict[str, str]) -> str:
    instructions = [
        emit_instruction(
            "procedimiento",
            "Modelo 200 IS e IRNR establecimientos permanentes",
            "La sede AEAT identifica el Modelo 200 como la declaracion del Impuesto sobre Sociedades y del IRNR para establecimientos permanentes y entidades en atribucion de rentas constituidas en el extranjero con presencia en territorio espanol.",
            URL_200_MODEL,
            hashes[URL_200_MODEL],
            10,
        ),
        emit_instruction(
            "obligados",
            "Declaracion del Impuesto sobre Sociedades",
            "El manual practico AEAT indica que el modelo 200 es aplicable, con caracter general, a todos los contribuyentes del Impuesto sobre Sociedades obligados a presentar y suscribir declaracion por este impuesto.",
            URL_200_MANUAL,
            hashes[URL_200_MANUAL],
            20,
        ),
        emit_instruction(
            "formulario",
            "Formulario Modelo 200",
            "El PDF oficial del Modelo 200 estructura la declaracion del Impuesto sobre Sociedades en paginas y apartados de identificacion, resultado contable, ajustes, base imponible, liquidacion, pagos y resultado.",
            URL_200_PDF,
            hashes[URL_200_PDF],
            30,
        ),
        emit_instruction(
            "resultado_contable",
            "Resultado contable y correcciones",
            "La cumplimentacion del Modelo 200 parte del resultado contable y de los ajustes o correcciones fiscales aplicables antes de determinar la base imponible.",
            URL_200_PDF,
            hashes[URL_200_PDF],
            40,
        ),
        emit_instruction(
            "liquidacion",
            "Base imponible, cuota y resultado",
            "El Modelo 200 recoge la base imponible, cuota integra, deducciones, pagos fraccionados y resultado de ingreso o devolucion dentro de la liquidacion del impuesto.",
            URL_200_PDF,
            hashes[URL_200_PDF],
            50,
        ),
    ]
    keywords = [
        emit_keyword(keyword, "IS")
        for keyword in [
            "modelo 200",
            "Impuesto sobre Sociedades",
            "declaracion sociedades",
            "resultado contable",
            "base imponible sociedades",
            "cuota integra sociedades",
            "liquidacion modelo 200",
        ]
    ]
    return emit_model_block("200", instructions, keywords)


def main() -> int:
    urls = [URL_303_INSTRUCTIONS, URL_303_PRESENTATION, URL_200_MODEL, URL_200_PDF, URL_200_MANUAL]
    hashes = {url: fetch_hash(url) for url in urls}
    capture_date = date.today().isoformat()
    sql = f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    {model_303_sql(hashes)}
    {model_200_sql(hashes)}
END $$;
"""
    sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
