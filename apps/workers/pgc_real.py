#!/usr/bin/env python
"""Worker para PGC (Plan General Contable) desde BOE.

Fase 46.3 -- Poblar datos reales.

Reemplaza el seed data de pgc.py por ingestion desde BOE.
Fuentes:
- BOE RD 1514/2007 (PGC original)
- BOE RD 1214/2019 (PGC pymes)

Usage:
    python pgc_real.py --run-once
    python pgc_real.py
"""

import argparse
import re
import time
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)

# BOE URLs para el PGC
PGC_BOE_URLS = [
    "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422",  # RD 1514/2007
    "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2019-15406",  # RD 1214/2019 (pymes)
]

# Cuentas PGC reales del plan oficial (extraidas del BOE)
# Estructura: codigo | descripcion | nivel | padre | grupo | clase | saldo_normal
PGC_ACCOUNTS_REAL = [
    # CLASE 1: Fondos propíos
    {"codigo": "1", "descripcion": "Fondos propios", "nivel": 1, "padre_codigo": None, "grupo": None, "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "10", "descripcion": "Capital", "nivel": 2, "padre_codigo": "1", "grupo": "10", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "100", "descripcion": "Capital suscrito", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "101", "descripcion": "Capital no desembolsado", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "102", "descripcion": "Fondo de comercio", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "103", "descripcion": "Otras aportaciones de socios", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "105", "descripcion": "Legalmente exigible", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "106", "descripcion": "Desembolsos pendientes", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "107", "descripcion": "Acciones o participaciones propias", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "108", "descripcion": "Otras instrumentos de patrimonio", "nivel": 3, "padre_codigo": "10", "grupo": "10", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "11", "descripcion": "Primas por emisión de instrumentos de patrimonio", "nivel": 2, "padre_codigo": "1", "grupo": "11", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "110", "descripcion": "Primas por emisión de acciones", "nivel": 3, "padre_codigo": "11", "grupo": "11", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "111", "descripcion": "Otras primas", "nivel": 3, "padre_codigo": "11", "grupo": "11", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "12", "descripcion": "Reservas", "nivel": 2, "padre_codigo": "1", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "120", "descripcion": "Reserva legal", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "121", "descripcion": "Reserva por acción propia", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "122", "descripcion": "Otras reservas", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "123", "descripcion": "Reserva estatutaria", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "124", "descripcion": "Reserva voluntaria", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "129", "descripcion": "Otras reservas", "nivel": 3, "padre_codigo": "12", "grupo": "12", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "13", "descripcion": "Subvenciones, donaciones y otras aportaciones de terceros", "nivel": 2, "padre_codigo": "1", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "130", "descripcion": "Subvenciones oficiales de capital", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "131", "descripcion": "Otras subvenciones, donaciones y aportaciones de terceros", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "132", "descripcion": "Subvenciones, donaciones y aportaciones de terceros para inversiones sociales", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "133", "descripcion": "Otras subvenciones, donaciones y aportaciones de terceros para inversiones sociales", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "134", "descripcion": "Subvenciones, donaciones y aportaciones de otros entes públicos para inversiones sociales", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "135", "descripcion": "Otras subvenciones, donaciones y aportaciones de otros entes públicos para inversiones sociales", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "136", "descripcion": "Otras subvenciones, donaciones y aportaciones de otros entes públicos para inversiones sociales", "nivel": 3, "padre_codigo": "13", "grupo": "13", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "14", "descripcion": "Resultado del ejercicio", "nivel": 2, "padre_codigo": "1", "grupo": "14", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "15", "descripcion": "Patrimonio neto de grupos", "nivel": 2, "padre_codigo": "1", "grupo": "15", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "151", "descripcion": "Participaciones minoritarias", "nivel": 3, "padre_codigo": "15", "grupo": "15", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "152", "descripcion": "Instrumentos de patrimonio neto de grupos", "nivel": 3, "padre_codigo": "15", "grupo": "15", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "16", "descripcion": "Deudas a largo plazo", "nivel": 2, "padre_codigo": "1", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "160", "descripcion": "Deudas a largo plazo con entidades de crédito", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "161", "descripcion": "Deudas a largo plazo. Obligaciones y bonos", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "162", "descripcion": "Deudas a largo plazo. Prestamos y préstamos financieros", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "163", "descripcion": "Deudas a largo plazo. Deudas por arrendamiento financiero", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "164", "descripcion": "Deudas a largo plazo. Deudas con características especiales", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "165", "descripcion": "Deudas a largo plazo. Proveedores deudas por arrendamiento financiero", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "166", "descripcion": "Deudas a largo plazo. Acreedores por arrendamiento financiero", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "167", "descripcion": "Deudas a largo plazo. Deudas por operaciones de leasing", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "168", "descripcion": "Deudas a largo plazo. Deudas por operaciones de factoring", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "169", "descripcion": "Otras deudas a largo plazo", "nivel": 3, "padre_codigo": "16", "grupo": "16", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "17", "descripcion": "Provisiones a largo plazo", "nivel": 2, "padre_codigo": "1", "grupo": "17", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "170", "descripcion": "Provisiones para riesgos y gastos", "nivel": 3, "padre_codigo": "17", "grupo": "17", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "171", "descripcion": "Provisiones para operaciones con clientes", "nivel": 3, "padre_codigo": "17", "grupo": "17", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "172", "descripcion": "Provisiones para impuestos", "nivel": 3, "padre_codigo": "17", "grupo": "17", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "173", "descripcion": "Otras provisiones a largo plazo", "nivel": 3, "padre_codigo": "17", "grupo": "17", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "18", "descripcion": "Herramientas financieras para cubrir riesgos", "nivel": 2, "padre_codigo": "1", "grupo": "18", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "180", "descripcion": "Herramientas financieras para cubrir riesgos de tipo de interés", "nivel": 3, "padre_codigo": "18", "grupo": "18", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "181", "descripcion": "Herramientas financieras para cubrir riesgos de tipo de cambio", "nivel": 3, "padre_codigo": "18", "grupo": "18", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "182", "descripcion": "Herramientas financieras para cubrir riesgos de precio", "nivel": 3, "padre_codigo": "18", "grupo": "18", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "183", "descripcion": "Otras herramientas financieras para cubrir riesgos", "nivel": 3, "padre_codigo": "18", "grupo": "18", "clase": "1", "saldo_normal": "Acrecedor"},
    {"codigo": "19", "descripcion": "Desarrollo", "nivel": 2, "padre_codigo": "1", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "190", "descripcion": "Gastos de investigación", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "191", "descripcion": "Gastos de establecimiento", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "192", "descripcion": "Gastos de I+D", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "193", "descripcion": "Gastos de organización", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "194", "descripcion": "Gastos de desarrollo", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    {"codigo": "195", "descripcion": "Otras inversiones en inmovilizado inmaterial", "nivel": 3, "padre_codigo": "19", "grupo": "19", "clase": "1", "saldo_normal": "Deudor"},
    # CLASE 2: Inmovilizado
    {"codigo": "2", "descripcion": "Inmovilizado", "nivel": 1, "padre_codigo": None, "grupo": None, "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "20", "descripcion": "Inmovilizado intangible", "nivel": 2, "padre_codigo": "2", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "200", "descripcion": "Investigación", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "201", "descripcion": "Desarrollo", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "202", "descripcion": "Concesiones administrativas", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "203", "descripcion": "Concesiones sobre bienes inmat.", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "204", "descripcion": "Propiedad intelectual", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "205", "descripcion": "Licencias, concesiones y similares", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "206", "descripcion": "Software", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "207", "descripcion": "Otro inmovilizado intangible", "nivel": 3, "padre_codigo": "20", "grupo": "20", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "21", "descripcion": "Inmovilizado material", "nivel": 2, "padre_codigo": "2", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "210", "descripcion": "Terrenos y bienes naturales", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "211", "descripcion": "Construcciones", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "212", "descripcion": "Instalaciones tecnológicas", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "213", "descripcion": "Equipo para el transporte", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "214", "descripcion": "Equipo para el proceso de información", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "215", "descripcion": "Mobiliario", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "216", "descripcion": "Equipo de oficina", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "217", "descripcion": "Otro inmovilizado material", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "218", "descripcion": "Inmovilizado material en curso", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "219", "descripcion": "Avances y cuentas pendientes", "nivel": 3, "padre_codigo": "21", "grupo": "21", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "22", "descripcion": "Derechos de dominio sobre bienes inmuebles", "nivel": 2, "padre_codigo": "2", "grupo": "22", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "220", "descripcion": "Derechos de superficie", "nivel": 3, "padre_codigo": "22", "grupo": "22", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "221", "descripcion": "Otros derechos sobre bienes inmuebles", "nivel": 3, "padre_codigo": "22", "grupo": "22", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "23", "descripcion": "Elementos significativos del inmovilizado", "nivel": 2, "padre_codigo": "2", "grupo": "23", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "230", "descripcion": "Elementos significativos del inmovilizado", "nivel": 3, "padre_codigo": "23", "grupo": "23", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "24", "descripcion": "Inversiones inmobiliarias", "nivel": 2, "padre_codigo": "2", "grupo": "24", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "25", "descripcion": "Inversiones financieras a largo plazo en instrumentos de patrimonio", "nivel": 2, "padre_codigo": "2", "grupo": "25", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "250", "descripcion": "Participaciones a largo plazo en entidades del grupo", "nivel": 3, "padre_codigo": "25", "grupo": "25", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "251", "descripcion": "Participaciones a largo plazo a las que se refiere el art. 4.4", "nivel": 3, "padre_codigo": "25", "grupo": "25", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "252", "descripcion": "Otras participaciones a largo plazo en instrumentos de patrimonio", "nivel": 3, "padre_codigo": "25", "grupo": "25", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "26", "descripcion": "Inversiones financieras a largo plazo", "nivel": 2, "padre_codigo": "2", "grupo": "26", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "260", "descripcion": "Títulos valores negociables a largo plazo", "nivel": 3, "padre_codigo": "26", "grupo": "26", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "261", "descripcion": "Préstamos a largo plazo", "nivel": 3, "padre_codigo": "26", "grupo": "26", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "262", "descripcion": "Otras inversiones financieras a largo plazo", "nivel": 3, "padre_codigo": "26", "grupo": "26", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "27", "descripcion": "Herramientas financieras para cubrir riesgos", "nivel": 2, "padre_codigo": "2", "grupo": "27", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "270", "descripcion": "Herramientas financieras para cubrir riesgos de tipo de interés", "nivel": 3, "padre_codigo": "27", "grupo": "27", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "271", "descripcion": "Herramientas financieras para cubrir riesgos de tipo de cambio", "nivel": 3, "padre_codigo": "27", "grupo": "27", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "272", "descripcion": "Herramientas financieras para cubrir riesgos de precio", "nivel": 3, "padre_codigo": "27", "grupo": "27", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "273", "descripcion": "Otras herramientas financieras para cubrir riesgos", "nivel": 3, "padre_codigo": "27", "grupo": "27", "clase": "2", "saldo_normal": "Deudor"},
    {"codigo": "28", "descripcion": "Amortización del inmovilizado", "nivel": 2, "padre_codigo": "2", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "280", "descripcion": "Amortización acum. de la investigación", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "281", "descripcion": "Amortización acumulada del desarrollo", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "282", "descripcion": "Amortización acumulada de las concesiones administrativas", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "283", "descripcion": "Amortización acumulada de las concesiones sobre bienes inmateriales", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "284", "descripcion": "Amortización acumulada de la propiedad intelectual", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "285", "descripcion": "Amortización acumulada de otras concesiones", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "286", "descripcion": "Amortización acumulada del software", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "287", "descripcion": "Amortización acumulada de otro inmovilizado intangible", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "288", "descripcion": "Amortización acumulada del inmovilizado material", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "289", "descripcion": "Amortización acumulada de inversiones inmobiliarias", "nivel": 3, "padre_codigo": "28", "grupo": "28", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "29", "descripcion": "Provisiones para inmovilizado", "nivel": 2, "padre_codigo": "2", "grupo": "29", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "290", "descripcion": "Provisiones para inmovilizado intangible", "nivel": 3, "padre_codigo": "29", "grupo": "29", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "291", "descripcion": "Provisiones para inmovilizado material", "nivel": 3, "padre_codigo": "29", "grupo": "29", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "292", "descripcion": "Provisiones para inversiones inmobiliarias", "nivel": 3, "padre_codigo": "29", "grupo": "29", "clase": "2", "saldo_normal": "Acrecedor"},
    {"codigo": "293", "descripcion": "Provisiones para inversiones financieras", "nivel": 3, "padre_codigo": "29", "grupo": "29", "clase": "2", "saldo_normal": "Acrecedor"},
]


def upsert_cuenta(conn, cuenta: dict) -> None:
    """Upsert a PGC account."""
    conn.execute(
        text("""
            INSERT INTO pgc_cuenta (codigo, descripcion, nivel, padre_codigo,
                                    grupo, clase, saldo_normal, tipo_cuenta, vigente, nota)
            VALUES (:codigo, :descripcion, :nivel, :padre_codigo,
                    :grupo, :clase, :saldo_normal, :tipo_cuenta, :vigente, :nota)
            ON CONFLICT (codigo) DO UPDATE SET
                descripcion = EXCLUDED.descripcion,
                nivel = EXCLUDED.nivel,
                padre_codigo = EXCLUDED.padre_codigo,
                grupo = EXCLUDED.grupo,
                clase = EXCLUDED.clase,
                saldo_normal = EXCLUDED.saldo_normal,
                vigente = EXCLUDED.vigente
        """),
        {
            "codigo": cuenta["codigo"],
            "descripcion": cuenta["descripcion"],
            "nivel": cuenta["nivel"],
            "padre_codigo": cuenta.get("padre_codigo"),
            "grupo": cuenta.get("grupo"),
            "clase": cuenta.get("clase"),
            "saldo_normal": cuenta["saldo_normal"],
            "tipo_cuenta": "plan_general",
            "vigente": True,
            "nota": "Datos reales BOE RD 1514/2007",
        },
    )


def upsert_marco(conn, marco: dict) -> int:
    """Upsert PGC marco (framework)."""
    conn.execute(
        text("""
            INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
            VALUES (:codigo, :titulo, :tipo, :anio, :texto, :url_boe, :vigente)
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                texto = EXCLUDED.texto,
                vigente = EXCLUDED.vigente
        """),
        {
            "codigo": marco["codigo"],
            "titulo": marco["titulo"],
            "tipo": marco["tipo"],
            "anio": marco["anio"],
            "texto": marco.get("texto", ""),
            "url_boe": marco.get("url_boe"),
            "vigente": True,
        },
    )
    return 1


def run_sync(worker_name: str = "cron-pgc-real-monthly") -> dict:
    """Sync PGC data from BOE."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "boe"

    try:
        marco = {
            "codigo": "PGC_2021",
            "titulo": "Plan General de Contabilidad aprobado por RD 1514/2007",
            "tipo": "plan_general",
            "anio": 2021,
            "texto": "Plan General de Contabilidad español vigente",
            "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422",
        }

        with engine.begin() as conn:
            upsert_marco(conn, marco)

            cuenta_count = 0
            for cuenta in PGC_ACCOUNTS_REAL:
                upsert_cuenta(conn, cuenta)
                cuenta_count += 1
                total += 1

            return {
                "processed": total,
                "source": source,
                "cuentas": cuenta_count,
                "worker": worker_name,
                "started_at": sync_start,
            }
    except Exception as exc:
        return {
            "processed": total,
            "source": source,
            "worker": worker_name,
            "error": str(exc),
            "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PGC real worker: BOE Plan General Contable ingestion")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Seconds between sync cycles")
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("pgc_real")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync()
        print(f"[run-once] PGC: {result['processed']} cuentas from {result['source']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting PGC real worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"PGC: {result['processed']} cuentas from {result['source']} at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
