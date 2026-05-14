#!/usr/bin/env python3
"""Emit SQL to load official Modelo 296 IRNR instructions and keys.

The script downloads official BOE/AEAT sources only to compute source hashes.
It does not connect to the database; pipe the generated SQL into psql via the
production Docker Compose postgres service.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


ORDER_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497"
DR_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
    "DR_200_299/archivos_24/DR_296_2024.pdf"
)
FORM_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/"
    "declaraciones-informativas-ayuda-tecnica/modelos-291-347/modelo-296-formulario.html"
)
FILE_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/"
    "declaraciones-informativas-ayuda-tecnica/modelos-291-347/modelo-296-fichero.html"
)


def fetch_hash(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "esdata-official-source-loader/1.0"},
    )
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
    exclusiones: str | None = None,
    source_url: str = ORDER_URL,
) -> str:
    return f"""
    INSERT INTO modelo_clave
        (campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
         criterio_aplicacion, exclusiones, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(codigo)}, {q(etiqueta)}, {q(descripcion)}, {q(tipo)},
         {q(tipo)}, {q(criterio)}, {q(exclusiones)}, {q(source_url)},
         {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, codigo)
    DO UPDATE SET
        etiqueta = EXCLUDED.etiqueta,
        descripcion = EXCLUDED.descripcion,
        tipo_clave = EXCLUDED.tipo_clave,
        tipo = EXCLUDED.tipo,
        criterio_aplicacion = EXCLUDED.criterio_aplicacion,
        exclusiones = EXCLUDED.exclusiones,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_keyword(keyword: str, dominio: str = "IRNR") -> str:
    return f"""
    INSERT INTO modelo_trigger_keyword (modelo_id, keyword, dominio)
    VALUES (v_modelo_id, {q(keyword)}, {q(dominio)})
    ON CONFLICT DO NOTHING;
    """


def main() -> int:
    hashes = {url: fetch_hash(url) for url in (ORDER_URL, DR_URL, FORM_URL, FILE_URL)}
    capture_date = date.today().isoformat()

    instructions = [
        emit_instruction(
            "presentacion",
            "Aprobacion del Modelo 296",
            "La Orden EHA/3290/2008 aprueba el Modelo 296 como declaracion anual de retenciones e ingresos a cuenta del IRNR para no residentes sin establecimiento permanente.",
            ORDER_URL,
            hashes[ORDER_URL],
            10,
        ),
        emit_instruction(
            "obligados",
            "Quienes deben presentar",
            "Deben presentar el modelo 296 los retenedores u obligados a ingresar a cuenta que deban resumir anualmente las rentas sujetas al IRNR sin mediacion de establecimiento permanente.",
            ORDER_URL,
            hashes[ORDER_URL],
            20,
        ),
        emit_instruction(
            "plazo",
            "Plazo anual",
            "La declaracion anual de retenciones e ingresos a cuenta, modelo 296, se presenta en relacion con las cantidades retenidas e ingresos a cuenta del anio inmediato anterior en el plazo establecido para enero por la Orden.",
            ORDER_URL,
            hashes[ORDER_URL],
            30,
        ),
        emit_instruction(
            "naturaleza",
            "Naturaleza de la renta",
            "En el campo Naturaleza se consigna D para renta dineraria y E para renta en especie.",
            ORDER_URL,
            hashes[ORDER_URL],
            40,
            "99",
        ),
        emit_instruction(
            "clave",
            "Clave de tipo de renta",
            "En el campo Clave se consigna la clave numerica que corresponda en funcion del tipo de renta declarado en el Modelo 296.",
            ORDER_URL,
            hashes[ORDER_URL],
            50,
            "100-101",
        ),
        emit_instruction(
            "subclave",
            "Subclave de calculo de retencion",
            "En el campo Subclave se consigna la circunstancia tenida en cuenta para el calculo de la retencion o ingreso a cuenta.",
            ORDER_URL,
            hashes[ORDER_URL],
            60,
            "102-103",
        ),
        emit_instruction(
            "presentacion_formulario",
            "Presentacion mediante formulario",
            "La ayuda tecnica AEAT indica que la presentacion mediante formulario esta disponible para declaraciones de menos de 40.000 registros y requiere identificacion electronica admitida.",
            FORM_URL,
            hashes[FORM_URL],
            70,
        ),
        emit_instruction(
            "presentacion_fichero",
            "Presentacion mediante fichero",
            "La ayuda tecnica AEAT indica que la presentacion por fichero requiere identificacion electronica y ajuste al diseno de registro publicado.",
            FILE_URL,
            hashes[FILE_URL],
            80,
        ),
    ]

    claves = [
        emit_clave("D", "Renta dineraria", "NATURALEZA", "Renta de naturaleza dineraria.", "Usar en posicion 99 cuando la renta sea dineraria.", hashes[ORDER_URL]),
        emit_clave("E", "Renta en especie", "NATURALEZA", "Renta de naturaleza en especie.", "Usar en posicion 99 cuando la renta sea en especie.", hashes[ORDER_URL]),
    ]

    rent_keys = [
        ("1", "Dividendos y otras rentas derivadas de la participacion en fondos propios de entidades"),
        ("2", "Intereses y otras rentas derivadas de la cesion a terceros de capitales propios"),
        ("3", "Canones derivados de patentes, marcas, dibujos, modelos, planos, formulas o procedimientos secretos"),
        ("4", "Canones derivados de derechos sobre obras literarias y artisticas"),
        ("5", "Canones derivados de derechos sobre obras cientificas"),
        ("6", "Canones derivados de peliculas cinematograficas y obras sonoras o visuales grabadas"),
        ("7", "Canones derivados de informaciones relativas a experiencias industriales, comerciales o cientificas"),
        ("9", "Canones derivados de derechos personales susceptibles de cesion"),
        ("10", "Canones derivados de equipos industriales, comerciales o cientificos"),
        ("11", "Otros canones no relacionados anteriormente"),
        ("12", "Rendimientos de capital mobiliario de operaciones de capitalizacion y seguros de vida o invalidez"),
        ("13", "Otros rendimientos de capital mobiliario no citados anteriormente"),
        ("14", "Rendimientos de bienes inmuebles"),
        ("15", "Rentas de actividades empresariales"),
        ("16", "Rentas derivadas de prestaciones de asistencia tecnica"),
        ("17", "Rentas de actividades artisticas"),
        ("18", "Rentas de actividades deportivas"),
        ("19", "Rentas de actividades profesionales"),
        ("20", "Rentas del trabajo"),
        ("21", "Pensiones y haberes pasivos"),
        ("22", "Retribuciones de administradores y miembros de consejos de administracion"),
        ("23", "Rendimientos derivados de operaciones de reaseguros"),
        ("24", "Entidades de navegacion maritima o aerea"),
        ("25", "Otras rentas"),
    ]
    claves.extend(
        emit_clave(
            codigo,
            etiqueta,
            "CLAVE_RENTA",
            etiqueta,
            "Usar en posiciones 100-101 segun el tipo de renta declarado.",
            hashes[ORDER_URL],
        )
        for codigo, etiqueta in rent_keys
    )

    subkeys = [
        ("01", "Retencion a tipos generales o escalas del articulo 25 TRLIRNR"),
        ("02", "Retencion aplicando limites de imposicion de Convenios"),
        ("03", "Exencion interna, principalmente articulo 14 TRLIRNR, excepto subclaves especificas"),
        ("04", "Exencion por aplicacion de Convenio"),
        ("05", "Sin retencion por previo pago del impuesto por el contribuyente o representante"),
        ("06", "Entidad extranjera de gestion colectiva de derechos de propiedad intelectual"),
        ("07", "Contribuyente del regimen fiscal especial de desplazados, salvo subclaves 13 y 14"),
        ("08", "Entidad comercializadora extranjera de IIC con limite de Convenio inferior al articulo 25 TRLIRNR"),
        ("09", "Entidad comercializadora extranjera de IIC con tipo de gravamen del articulo 25 TRLIRNR"),
        ("10", "Ingreso a cuenta del articulo 36.2 TRLIRNR por entidad en atribucion de rentas"),
        ("11", "Contribuyente que acredito uso del procedimiento del articulo 32 TRLIRNR, modelo 247"),
        ("12", "Dietas y asignaciones para gastos de viaje exceptuadas de gravamen"),
        ("13", "Regimen especial de desplazados: dietas y asignaciones exceptuadas"),
        ("14", "Regimen especial de desplazados: rendimientos del trabajo en especie exentos"),
        ("15", "Rendimientos del trabajo en especie exentos"),
    ]
    claves.extend(
        emit_clave(
            codigo,
            etiqueta,
            "SUBCLAVE_RETENCION",
            etiqueta,
            "Usar en posiciones 102-103 segun la circunstancia de calculo de la retencion o ingreso a cuenta.",
            hashes[ORDER_URL],
        )
        for codigo, etiqueta in subkeys
    )

    keywords = [
        emit_keyword(keyword)
        for keyword in [
            "IRNR",
            "modelo 296",
            "no residente",
            "retencion no residente",
            "ingreso a cuenta no residente",
            "renta no residente",
            "convenio doble imposicion",
            "clave renta 296",
            "subclave 296",
            "perceptor no residente",
        ]
    ]

    sql = f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    SELECT id INTO v_modelo_id FROM aeat_modelo WHERE codigo = '296';
    IF v_modelo_id IS NULL THEN
        RAISE EXCEPTION 'Modelo 296 not found';
    END IF;

    SELECT id INTO v_campana_id
    FROM modelo_campana
    WHERE modelo_id = v_modelo_id AND activo = true
    ORDER BY campana DESC
    LIMIT 1;

    IF v_campana_id IS NULL THEN
        RAISE EXCEPTION 'Active campaign for Modelo 296 not found';
    END IF;

    DELETE FROM modelo_clave WHERE campana_id = v_campana_id;
    DELETE FROM modelo_instruccion WHERE campana_id = v_campana_id;

    {' '.join(instructions)}
    {' '.join(claves)}
    {' '.join(keywords)}
END $$;
"""
    sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
