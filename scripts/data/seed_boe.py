#!/usr/bin/env python3
"""Seed BOE legislation — Normas tributarias consolidadas.

Crea normas BOE (LIVA, LIRPF, LIS, LGT, ITPAJD) con metadata de legislacion
consolidada. Basado en el worker boe.py.

Uso:
    python scripts/data/seed_boe.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

NORMAS_DATA = [
    {
        "codigo": "LIVA",
        "titulo": "Ley 37/1992, del Impuesto sobre el Valor Añadido",
        "boe_id": "BOE-A-1992-28740",
        "eli_uri": "https://www.boe.es/eli/es/l/1992/12/30/37",
        "jurisdiccion": "es",
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
        "estado_cobertura": "ingestada",
        "vigente_desde": "1992-12-30",
    },
    {
        "codigo": "LIRPF",
        "titulo": "Ley 35/2006, del IRPF",
        "boe_id": "BOE-A-2006-20764",
        "eli_uri": "https://www.boe.es/eli/es/l/2006/12/26/35",
        "jurisdiccion": "es",
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
        "estado_cobertura": "ingestada",
        "vigente_desde": "2006-12-26",
    },
    {
        "codigo": "LIS",
        "titulo": "Ley 27/2014, del Impuesto sobre Sociedades",
        "boe_id": "BOE-A-2014-12328",
        "eli_uri": "https://www.boe.es/eli/es/l/2014/09/24/27",
        "jurisdiccion": "es",
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
        "estado_cobertura": "ingestada",
        "vigente_desde": "2014-09-24",
    },
    {
        "codigo": "LGT",
        "titulo": "Ley 58/2003, General Tributaria",
        "boe_id": "BOE-A-2003-23186",
        "eli_uri": "https://www.boe.es/eli/es/l/2003/12/17/58",
        "jurisdiccion": "es",
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
        "estado_cobertura": "ingestada",
        "vigente_desde": "2003-12-17",
    },
    {
        "codigo": "ITPAJD",
        "titulo": "Real Decreto Legislativo 1/1993, del ITPAJD",
        "boe_id": "BOE-A-1993-25359",
        "eli_uri": "https://www.boe.es/eli/es/rdlg/1993/09/24/1/con",
        "jurisdiccion": "es",
        "tipo_fuente": "boe",
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "tributario",
        "estado_cobertura": "ingestada",
        "vigente_desde": "1993-10-21",
    },
]

ARTICULOS_DATA = [
    # LIVA articulos clave
    {"norma_codigo": "LIVA", "numero": "1", "titulo": "Hecho impositivo", "tipo": "articulo"},
    {"norma_codigo": "LIVA", "numero": "75", "titulo": "Base imponible", "tipo": "articulo"},
    {"norma_codigo": "LIVA", "numero": "78", "titulo": "Devengo", "tipo": "articulo"},
    {"norma_codigo": "LIVA", "numero": "91", "titulo": "Modificacion de la base imponible", "tipo": "articulo"},
    {"norma_codigo": "LIVA", "numero": "20", "titulo": "Exenciones", "tipo": "articulo"},
    {"norma_codigo": "LIVA", "numero": "105", "titulo": "SII", "tipo": "articulo"},
    # LIRPF articulos clave
    {"norma_codigo": "LIRPF", "numero": "1", "titulo": "Hecho impositivo", "tipo": "articulo"},
    {"norma_codigo": "LIRPF", "numero": "32", "titulo": "Rendimientos del capital mobiliario", "tipo": "articulo"},
    {"norma_codigo": "LIRPF", "numero": "33", "titulo": "Ganancias y perdidas patrimoniales", "tipo": "articulo"},
    {"norma_codigo": "LIRPF", "numero": "65", "titulo": "Autoliquidacion", "tipo": "articulo"},
    # LIS articulos clave
    {"norma_codigo": "LIS", "numero": "1", "titulo": "Hecho impositivo", "tipo": "articulo"},
    {"norma_codigo": "LIS", "numero": "11", "titulo": "Entidades no residentes", "tipo": "articulo"},
    {"norma_codigo": "LIS", "numero": "59", "titulo": "Autoliquidacion", "tipo": "articulo"},
    # LGT articulos clave
    {"norma_codigo": "LGT", "numero": "2", "titulo": "Normas tributarias", "tipo": "articulo"},
    {"norma_codigo": "LGT", "numero": "29", "titulo": "Periodos de liquidacion", "tipo": "articulo"},
    {"norma_codigo": "LGT", "numero": "66", "titulo": "Inspeccion", "tipo": "articulo"},
]

VERSIONES_DATA = [
    # LIVA versiones
    {"norma_codigo": "LIVA", "articulo_numero": "1", "texto": "El hecho impositivo definido en los artculos 68 a 74 consiste en la entrega de bienes y la prestacin de servicios realizada por un empresario o profesional con carcter habitual.", "vigente_desde": "1992-12-30", "boe_bloque_id": "BOE-LIVA-ART1"},
    {"norma_codigo": "LIVA", "articulo_numero": "75", "texto": "La base imponible del Impuesto se determinar en funcin del valor real del bien o servicio entregado o prestado, menos el importe de las rebajas, descuentos y bonificaciones.", "vigente_desde": "1992-12-30", "boe_bloque_id": "BOE-LIVA-ART75"},
    # LIRPF versiones
    {"norma_codigo": "LIRPF", "articulo_numero": "1", "texto": "Este impuesto grava los siguientes rendimientos, ganancias y perdidas patrimoniales y rentas imputadas:", "vigente_desde": "2006-12-26", "boe_bloque_id": "BOE-LIRPF-ART1"},
    {"norma_codigo": "LIRPF", "articulo_numero": "32", "texto": "Estn constituidos por las ganancias y perdidas patrimoniales que se obtengan y por los rendimientos del capital mobiliario.", "vigente_desde": "2006-12-26", "boe_bloque_id": "BOE-LIRPF-ART32"},
    # LIS versiones
    {"norma_codigo": "LIS", "articulo_numero": "1", "texto": "Este impuesto grava las rentas de las personas jurdicas y entidades a las que se identifica con ellas en este texto.", "vigente_desde": "2014-09-24", "boe_bloque_id": "BOE-LIS-ART1"},
]

MATERIAS_DATA = [
    {"slug": "tipo-reducido-iva", "etiqueta": "Tipo reducido IVA"},
    {"slug": "sistema-iva", "etiqueta": "Sistema IVA"},
    {"slug": "retenciones-irpf", "etiqueta": "Retenciones IRPF"},
    {"slug": "impuesto-sociedades", "etiqueta": "Impuesto Sociedades"},
    {"slug": "tributacion-internacional", "etiqueta": "Tributacion internacional"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed BOE legislation")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    # Insert materias
    for mat in MATERIAS_DATA:
        cur.execute(
            """INSERT INTO materia (slug, etiqueta)
               VALUES (%(slug)s, %(etiqueta)s)
               ON CONFLICT (slug) DO UPDATE SET etiqueta = EXCLUDED.etiqueta""",
            mat,
        )

    # Insert normas
    for n in NORMAS_DATA:
        cur.execute(
            """INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion,
               tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
               VALUES (%(codigo)s, %(titulo)s, %(boe_id)s, %(eli_uri)s, %(jurisdiccion)s,
                       %(tipo_fuente)s, %(tipo_documento)s, %(ambito)s, %(estado_cobertura)s,
                       %(vigente_desde)s)
               ON CONFLICT (codigo) DO UPDATE SET
                   titulo = EXCLUDED.titulo,
                   boe_id = EXCLUDED.boe_id,
                  eli_uri = EXCLUDED.eli_uri,
                   tipo_documento = EXCLUDED.tipo_documento,
                   ambito = EXCLUDED.ambito,
                   estado_cobertura = EXCLUDED.estado_cobertura,
                   vigente_desde = EXCLUDED.vigente_desde""",
            n,
        )

    # Insert articulos
    for a in ARTICULOS_DATA:
        cur.execute(
            """INSERT INTO articulo (norma_id, numero, titulo, tipo)
               SELECT n.id, %(numero)s, %(titulo)s, %(tipo)s
               FROM norma n WHERE n.codigo = %(norma_codigo)s
               ON CONFLICT (norma_id, numero) DO UPDATE SET
                   titulo = EXCLUDED.titulo,
                   tipo = EXCLUDED.tipo""",
            a,
        )

    # Insert version_articulo
    for v in VERSIONES_DATA:
        cur.execute(
            """INSERT INTO version_articulo (articulo_id, texto, vigente_desde, boe_bloque_id)
               SELECT a.id, %(texto)s, %(vigente_desde)s, %(boe_bloque_id)s
               FROM articulo a
               JOIN norma n ON n.id = a.norma_id
               WHERE n.codigo = %(norma_codigo)s AND a.numero = %(articulo_numero)s
               ON CONFLICT DO NOTHING""",
            v,
        )

    conn.commit()
    total = len(NORMAS_DATA) + len(ARTICULOS_DATA) + len(VERSIONES_DATA) + len(MATERIAS_DATA)
    print(f"OK: {total} registros BOE insertados ({len(NORMAS_DATA)} normas, {len(ARTICULOS_DATA)} articulos, {len(VERSIONES_DATA)} versiones, {len(MATERIAS_DATA)} materias)")
    conn.close()


if __name__ == "__main__":
    main()
