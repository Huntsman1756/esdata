#!/usr/bin/env python
"""
CANONICAL AEAT FLOW - STEP 2 OF 2

Populate campaign data after running:
`python scripts/seed-modelos.py --db-url <DATABASE_URL>`

This script is not a standalone AEAT bootstrap. It enriches existing
`aeat_modelo` rows with campaign data, casillas, claves, instrucciones,
normativa and operational metadata.

Safe mode:
- use `--dry-run` to inspect intended campaign inserts/upserts without writing

Seed v2: campaigns, casillas, claves, instrucciones, normativa, formato
for all AEAT models in esdata.

Populates:
- modelo_campana: campaign versions per model
- modelo_campana_operativa: normalized operational metadata per campaign
- modelo_casilla: complete casilla inventory per campaign
- modelo_clave: clave codes per campaign
- modelo_instruccion: step-by-step instructions per campaign
- modelo_normativa: BOE orders per model
- modelo_formato: electronic filing format specs per campaign

Usage:
    python scripts/seed-modelos-v2.py [--db-url URL] [--dry-run] [--campana 2025]
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

CAMPANA_DEFAULT = "2025"

# ===========================================================================
# CAMPAIGNS
# ===========================================================================
# Note: campana field uses CAMPANA_DEFAULT placeholder, which is overridden
# by the --campana CLI argument at runtime in seed_v2().
CAMPAÑAS = [
    # (modelo_codigo, url_instrucciones, url_normativa, url_formato)
    # The campana value is determined at runtime by the --campana argument.
    # --- IRPF ---
    ("100",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
     "https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf",
     None),
    ("111",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     None),
    ("115",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/instrucciones/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     None),
    ("123",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     None),
    ("130",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/instrucciones/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     None),
    ("180",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-180.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("187",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-187.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("189",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("190",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-190.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("193",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-193.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("194",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("196",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-196.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("198",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html",
     "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     None),
    ("110", None,
     "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     None),

    # --- IVA ---
    ("303",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     None),
    ("349",
     "https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     None),
    ("390",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     None),

    # --- IRNR ---
    ("124",
     "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     None),
    ("216",
     "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     None),
    ("296",
     "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     None),

    # --- CENSAL ---
    ("036",
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303",
     None),

    # --- INFORMATIVO ---
    ("289",
     "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/campana-declaraciones-informativas-2025/normativa/modelo-289.html",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-24098",
     None),
    ("290",
     "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328",
     None),
    ("299", None, None,
     "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html"),
    ("347",
     "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/modelo-347-declaracion-anual-operaciones-terceras-personas/index.shtml",
     "https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303",
     None),
]

# ===========================================================================
# CASILLAS — inventario completo por modelo/campaña
# ===========================================================================
CASILLAS = {
    # --- MODELO 100 — IRPF Declaración anual ---
    "100": [
        ("0001", "Nombre y apellidos", None, "texto", 1, 1),
        ("0002", "Rendimientos del trabajo — ingresos íntegros", "Suma de todos los rendimientos del trabajo devengados en el ejercicio", "importe", 2, 2),
        ("0003", "Rendimientos de actividades económicas", "Ingresos íntegros de actividades económicas en estimación directa", "importe", 2, 3),
        ("0004", "Rendimientos del capital mobiliario", "Dividendos, intereses, rendimientos de seguros", "importe", 3, 4),
        ("0005", "Rendimientos del capital inmobiliario", "Rendimientos procedentes del arrendamiento de inmuebles", "importe", 3, 5),
        ("0006", "Rendimientos del capital mobiliario obtenidos en Ceuta y Melilla", None, "importe", 3, 6),
        ("0007", "Rendimientos del capital inmobiliario obtenidos en Ceuta y Melilla", None, "importe", 3, 7),
        ("0008", "Subtot. rendimientos", "Suma de rendimientos parciales", "importe", 3, 8),
        ("0009", "Reducciones por rendimientos", "Reducciones aplicables sobre los rendimientos", "importe", 3, 9),
        ("0010", "Rendimiento neto", "Rendimiento neto tras reducciones", "importe", 4, 10),
        ("0015", "Ganancias patrimoniales derivadas de transmisiones", "Plusvalías por venta de inmuebles, acciones, etc.", "importe", 5, 15),
        ("0016", "Ganancias patrimoniales no derivadas de transmisiones", "Premios, subvenciones, ayudas", "importe", 5, 16),
        ("0017", "Pérdidas patrimoniales derivadas de transmisiones", "Minusvalías por venta", "importe", 5, 17),
        ("0018", "Pérdidas patrimoniales no derivadas de transmisiones", None, "importe", 5, 18),
        ("0019", "Rendimiento neto actividades económicas en estim. objetiva", None, "importe", 4, 11),
        ("0416", "Ganancias patrimoniales de la base imponible del ahorro", "Ganancias patrimoniales que integran la base del ahorro", "importe", 6, 20),
        ("0417", "Pérdidas patrimoniales de la base imponible del ahorro", None, "importe", 6, 21),
        ("0418", "Saldo neto ganancias y pérdidas patrimoniales", None, "importe", 6, 22),
        ("0447", "Base imponible general", "Base imponible del IRPF tras compensaciones", "importe", 7, 30),
        ("0448", "Base liquidable general", "Base general tras mínimos personales", "importe", 7, 31),
        ("0449", "Base imponible del ahorro", "Base del ahorro", "importe", 7, 32),
        ("0450", "Base liquidable del ahorro", "Base del ahorro tras compensaciones", "importe", 7, 33),
        ("0468", "Cuota íntegra estatal general", "Cuota resultante de aplicar el tipo a la base liquidable general", "importe", 8, 40),
        ("0469", "Cuota íntegra estatal del ahorro", None, "importe", 8, 41),
        ("0470", "Cuota íntegra estatal", "Suma de ambas cuotas", "importe", 8, 42),
        ("0490", "Cuota líquida estatal", "Cuota íntegra menos deducciones estatales", "importe", 9, 50),
        ("0500", "Cuota líquida total", "Cuota estatal + autonómica tras deducciones", "importe", 10, 55),
        ("0506", "Resultado de la declaración", "A ingresar, a devolver o cero", "importe", 11, 60),
    ],

    # --- MODELO 111 — Retenciones IRPF ---
    "111": [
        ("01", "Rendimientos del trabajo", "Retenciones practicadas por rendimientos del trabajo", "importe", 1, 1),
        ("02", "Rendimientos de actividades económicas", "Retenciones por actividades económicas, profesionales", "importe", 1, 2),
        ("03", "Premios", "Retenciones por premios de loterías, rifas, combinaciones aleatorias", "importe", 1, 3),
        ("04", "Capacidad mobiliario", "Retenciones por rendimientos de capital mobiliario", "importe", 1, 4),
        ("05", "Imputaciones de renta", "Retenciones por imputaciones de renta", "importe", 1, 5),
        ("06", "Ganancias patrimoniales", "Retenciones por ganancias patrimoniales", "importe", 1, 6),
        ("07", "Contraprestaciones por cesión de derechos de imagen", None, "importe", 1, 7),
        ("08", "Indemnizaciones", "Retenciones por indemnizaciones como rendimientos de trabajo", "importe", 1, 8),
        ("09", "Prestaciones por desempleo", "Retenciones por prestaciones de desempleo", "importe", 1, 9),
        ("10", "Calificación de beneficiario", None, "numero", 1, 10),
        ("11", "Nº de perceptores", "Número total de perceptores", "numero", 1, 11),
        ("12", "Cuotas a ingresar", "Total de retenciones e ingresos a cuenta", "importe", 2, 12),
    ],

    # --- MODELO 115 — Retenciones arrendamientos ---
    "115": [
        ("01", "Base de retenciones e ingresos a cuenta", "Base de las rentas de inmuebles urbanos", "importe", 1, 1),
        ("02", "Tipo de retención", "Porcentaje aplicable", "importe", 1, 2),
        ("03", "Retenciones", "Cuota resultante", "importe", 1, 3),
        ("04", "Ingresos a cuenta", None, "importe", 1, 4),
        ("05", "A ingresar", "Resultado de la autoliquidación", "importe", 1, 5),
        ("06", "Nº de perceptores", "Número de perceptores de rentas", "numero", 1, 6),
        ("07", "NIF del perceptor", None, "texto", 1, 7),
    ],

    # --- MODELO 303 — IVA Autoliquidación ---
    "303": [
        ("01", "Entrega de bienes y prestaciones de servicios (régimen general) — base", "Base imponible de operaciones corrientes", "importe", 1, 1),
        ("03", "Entrega de bienes y prestaciones de servicios (régimen general) — tipo 21%", "Cuota al 21%", "importe", 1, 2),
        ("04", "Entrega de bienes y prestaciones de servicios (régimen general) — tipo 10%", "Cuota al 10%", "importe", 1, 3),
        ("05", "Entrega de bienes y prestaciones de servicios (régimen general) — tipo 4%", "Cuota al 4%", "importe", 1, 4),
        ("06", "Adquisiciones interiores de bienes y servicios — base", "Base de adquisiciones sujetas a inversión del sujeto pasivo", "importe", 1, 5),
        ("07", "Adquisiciones interiores — cuota al 21%", "Cuota de adquisiciones al 21%", "importe", 1, 6),
        ("08", "Adquisiciones interiores — cuota al 10%", "Cuota de adquisiciones al 10%", "importe", 1, 7),
        ("09", "Adquisiciones interiores — cuota al 4%", "Cuota de adquisiciones al 4%", "importe", 1, 8),
        ("10", "Adquisiciones intracomunitarias de bienes — base", "Base de adquisiciones intracomunitarias", "importe", 1, 9),
        ("11", "Adquisiciones intracomunitarias — cuota al 21%", "Cuota intracomunitaria 21%", "importe", 1, 10),
        ("12", "Adquisiciones intracomunitarias — cuota al 10%", "Cuota intracomunitaria 10%", "importe", 1, 11),
        ("13", "Adquisiciones intracomunitarias — cuota al 4%", "Cuota intracomunitaria 4%", "importe", 1, 12),
        ("14", "Importaciones de bienes", "Cuota tributaria de las importaciones", "importe", 1, 13),
        ("21", "Operaciones interiores exentas", "Base de operaciones exentas IVA", "importe", 1, 14),
        ("22", "Exportaciones y operaciones asimiladas", "Base de exportaciones y operaciones asimiladas", "importe", 1, 15),
        ("28", "Rectificación de deducciones", "Rectificación anual de deducciones de inversiones", "importe", 2, 16),
        ("38", "Cuota deducible por bienes de inversión", "Cuota soportada en adquisiciones de bienes de inversión", "importe", 2, 17),
        ("39", "Cuota deducible distintas de bienes de inversión", "Cuota soportada en adquisiciones corrientes", "importe", 2, 18),
        ("40", "Deducciones por importaciones", "Cuota de importaciones deducible", "importe", 2, 19),
        ("41", "Deducciones por adquisiciones intracomunitarias", "Cuota de adquisiciones intracomunitarias deducible", "importe", 2, 20),
        ("43", "Deducción por régimen especial de bienes usados", None, "importe", 2, 21),
        ("44", "Deducciones por adquisiciones con inversión del sujeto pasivo", None, "importe", 2, 22),
        ("46", "Deducciones por operaciones no sujetas con inversión del sujeto pasivo", None, "importe", 2, 23),
        ("47", "Deducciones por cuotas soportadas en adquisiciones de bienes de inversión (régimen especial agrícola)", None, "importe", 2, 24),
        ("48", "Cuotas soportadas en adquisiciones o importaciones de bienes de capital no deducibles", None, "importe", 2, 25),
        ("49", "Regularización de cuotas soportadas no deducibles", None, "importe", 2, 26),
        ("50", "Total cuotas deducibles", "Suma de todas las cuotas deducibles", "importe", 2, 27),
        ("51", "Resultado líquido", "Diferencia entre cuota repercutida y deducible", "importe", 2, 28),
        ("52", "Compensaciones pendientes de aplicación de periodos anteriores", None, "importe", 2, 29),
        ("53", "Regularización anual de cuotas", "Resultado de la regularización anual", "importe", 2, 30),
        ("54", "Deducciones por exportaciones temporales", None, "importe", 2, 31),
        ("55", "Autoliquidaciones de subgrupos de IVA", None, "importe", 2, 32),
        ("56", "Autoliquidaciones de grupos de IVA", None, "importe", 2, 33),
        ("57", "Cuota devengada", "Total cuotas repercutidas", "importe", 2, 34),
        ("58", "Cuota deducible", "Total cuotas deducibles", "importe", 2, 35),
        ("59", "Resultado de las liquidaciones", "Diferencia", "importe", 2, 36),
        ("60", "A compensar", "Cuota a compensar en periodos siguientes", "importe", 2, 37),
        ("61", "A devolver", "Cuota a devolver", "importe", 2, 38),
        ("62", "A ingresar", "Resultado final a ingresar", "importe", 3, 39),
        ("63", "Número de operaciones intracomunitarias", "Nº total de operaciones intracomunitarias", "numero", 3, 40),
        ("64", "Entregas intracomunitarias de bienes", "Base de entregas intracomunitarias", "importe", 3, 41),
        ("65", "Número de entregas intracomunitarias", None, "numero", 3, 42),
        ("66", "Adquisiciones intracomunitarias notificadas en territorio", "Base de adquisiciones notificadas", "importe", 3, 43),
        ("67", "Número de adquisiciones", None, "numero", 3, 44),
        ("68", "Entregas de bienes a distancia desde otros Estados miembros", "Base de entregas a distancia desde otros EEMM", "importe", 3, 45),
        ("69", "Entregas de bienes a distancia desde terceros países (régimen IOSS)", None, "importe", 3, 46),
        ("70", "Entregas de bienes a distancia desde terceros países (no IOSS)", None, "importe", 3, 47),
        ("71", "Ventas a distancia y servicios a particulares", "Operaciones realizadas desde otros EEMM", "importe", 3, 48),
        ("72", "Cuotas satisfechas en régimen OSS — tipo reducido", None, "importe", 3, 49),
        ("73", "Cuotas satisfechas en régimen OSS — tipo normal", None, "importe", 3, 50),
        ("74", "Cuotas satisfechas en régimen OSS — servicios", None, "importe", 3, 51),
        ("75", "Adquisiciones intracomunitarias de servicios", None, "importe", 3, 52),
        ("76", "Cuota deducible por adquisiciones intracomunitarias de servicios", None, "importe", 3, 53),
        ("77", "Servicios prestados por empresarios no establecidos", None, "importe", 3, 54),
        ("78", "Operaciones no sujetas con inversión del sujeto pasivo", None, "importe", 3, 55),
        ("79", "Total de operaciones del período", "Volumen total de operaciones", "importe", 3, 56),
        ("80", "Operaciones realizadas por empresarios no establecidos", None, "importe", 3, 57),
    ],

    # --- MODELO 390 — IVA Resumen anual ---
    "390": [
        ("01", "Total base imponible operaciones corrientes (régimen general)", None, "importe", 1, 1),
        ("03", "Total cuota operaciones corrientes (régimen general) — tipo 21%", None, "importe", 1, 2),
        ("04", "Total cuota operaciones corrientes (régimen general) — tipo 10%", None, "importe", 1, 3),
        ("05", "Total cuota operaciones corrientes (régimen general) — tipo 4%", None, "importe", 1, 4),
        ("06", "Total base adquisiciones interiores — inversión sujeto pasivo", None, "importe", 1, 5),
        ("10", "Total base adquisiciones intracomunitarias", None, "importe", 1, 6),
        ("14", "Total base importaciones", None, "importe", 1, 7),
        ("21", "Total base operaciones interiores exentas", None, "importe", 1, 8),
        ("22", "Total base exportaciones y asimiladas", None, "importe", 1, 9),
        ("28", "Rectificación anual de deducciones", None, "importe", 1, 10),
        ("38", "Cuota deducible bienes de inversión", None, "importe", 1, 11),
        ("39", "Cuota deducible corriente", None, "importe", 1, 12),
        ("40", "Total deducciones por importaciones", None, "importe", 1, 13),
        ("41", "Total deducciones por adquisiciones intracomunitarias", None, "importe", 1, 14),
        ("50", "Total cuotas deducibles", None, "importe", 1, 15),
        ("51", "Resultado", None, "importe", 1, 16),
        ("62", "Total a ingresar", None, "importe", 1, 17),
        ("63", "Nº operaciones intracomunitarias", None, "numero", 1, 18),
        ("64", "Entregas intracomunitarias", None, "importe", 1, 19),
        ("66", "Adquisiciones intracomunitarias", None, "importe", 1, 20),
        ("69", "Volumen total de operaciones", None, "importe", 1, 21),
        ("95", "Régimen especial agricultura — base", None, "importe", 1, 22),
        ("97", "Régimen especial agricultura — compensaciones", None, "importe", 1, 23),
        ("111", "Resumen anual", "Referencia al resumen anual", "texto", 1, 24),
    ],

    # --- MODELO 347 — Operaciones con terceros ---
    "347": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", "Año al que se refiere la declaración", "numero", 1, 2),
        ("03", "Tipo de declaración", "Normal o complementaria", "texto", 1, 3),
        ("14", "NIF del tercero", "NIF de la persona o entidad con la que se realizan operaciones", "texto", 1, 4),
        ("15", "Apellidos o denominación social del tercero", None, "texto", 1, 5),
        ("16", "Importe total operaciones", "Importe anual de operaciones con el tercero (umbral > 3.005,06 €)", "importe", 1, 6),
        ("17", "Importe total operaciones en metálico", "Operaciones en efectivo", "importe", 1, 7),
        ("18", "Importe total cobros en metálico", None, "importe", 1, 8),
        ("19", "Importe total percibido en metálico", None, "importe", 1, 9),
        ("20", "Identificación de inmuebles — referencia catastral", None, "texto", 1, 10),
        ("21", "Identificación de inmuebles — dirección", None, "texto", 1, 11),
        ("22", "Nº de titular", None, "numero", 1, 12),
        ("23", "Importe percibido por arrendamiento de inmuebles", None, "importe", 1, 13),
        ("24", "Importe percibido por subarriendo", None, "importe", 1, 14),
        ("25", "Tipo de operación", "Entrega de bienes, prestación de servicios, arrendamiento", "texto", 1, 15),
        ("26", "Periodo de imputación", "Trimestre al que se imputan las operaciones", "texto", 1, 16),
    ],

    # --- MODELO 349 — Operaciones intracomunitarias ---
    "349": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Periodo", "Mensual o trimestral", "texto", 1, 3),
        ("04", "Tipo de declaración", "Normal o complementaria", "texto", 1, 4),
        ("05", "NIF del operador comunitario", "NIF-IVA del destinatario en otro Estado miembro", "texto", 1, 5),
        ("06", "Apellidos o denominación social del operador", None, "texto", 1, 6),
        ("07", "País del operador", "Código de país del Estado miembro", "texto", 1, 7),
        ("08", "Clave de operación", "A=Entrega bienes, B=Adquisición bienes, C=Servicios, D=Triangulación", "texto", 1, 8),
        ("09", "Base imponible", "Importe de las operaciones con el operador", "importe", 1, 9),
        ("10", "Facturas rectificativas", "Nº de facturas rectificativas incluidas", "numero", 1, 10),
    ],

    # --- MODELO 190 — IRPF Retenciones resumen ---
    "190": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de declaración", "Normal o complementaria", "texto", 1, 3),
        ("04", "Rendimientos del trabajo — nº perceptores", None, "numero", 1, 4),
        ("05", "Rendimientos del trabajo — base de retenciones", "Suma de bases de retenciones por rendimientos del trabajo", "importe", 1, 5),
        ("06", "Rendimientos del trabajo — retenciones", "Total de retenciones por rendimientos del trabajo", "importe", 1, 6),
        ("07", "Actividades económicas — nº perceptores", None, "numero", 1, 7),
        ("08", "Actividades económicas — base de retenciones", None, "importe", 1, 8),
        ("09", "Actividades económicas — retenciones", None, "importe", 1, 9),
        ("10", "Capital mobiliario — nº perceptores", None, "numero", 1, 10),
        ("11", "Capital mobiliario — base de retenciones", None, "importe", 1, 11),
        ("12", "Capital mobiliario — retenciones", None, "importe", 1, 12),
        ("13", "Premios — nº perceptores", None, "numero", 1, 13),
        ("14", "Premios — base de retenciones", None, "importe", 1, 14),
        ("15", "Premios — retenciones", None, "importe", 1, 15),
        ("16", "Ganancias patrimoniales — nº perceptores", None, "numero", 1, 16),
        ("17", "Ganancias patrimoniales — base de retenciones", None, "importe", 1, 17),
        ("18", "Ganancias patrimoniales — retenciones", None, "importe", 1, 18),
        ("19", "Imputaciones de renta — nº perceptores", None, "numero", 1, 19),
        ("20", "Imputaciones de renta — base de retenciones", None, "importe", 1, 20),
        ("21", "Imputaciones de renta — retenciones", None, "importe", 1, 21),
    ],

    # --- MODELO 193 — Retenciones capital mobiliario ---
    "193": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de declaración", None, "texto", 1, 3),
        ("04", "NIF del perceptor", None, "texto", 1, 4),
        ("05", "NIF representante del perceptor", None, "texto", 1, 5),
        ("06", "Clave de rendimiento", "Tipo de rendimiento: A=Dividendos, B=Intereses, C=Rendimientos cuenta corriente, etc.", "texto", 1, 6),
        ("07", "Nº percepciones", "Número de percepciones al perceptor", "numero", 1, 7),
        ("08", "Base de retención o ingreso a cuenta", None, "importe", 1, 8),
        ("09", "Tipo de retención", None, "importe", 1, 9),
        ("10", "Cuota", "Retención practicada", "importe", 1, 10),
        ("11", "Base no sujeta por residencia en otro EEMM", None, "importe", 1, 11),
        ("12", "Comentarios", None, "texto", 1, 12),
    ],

    # --- MODELO 196 — Resumen anual capital mobiliario ---
    "196": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de declaración", None, "texto", 1, 3),
        ("04", "NIF del perceptor", None, "texto", 1, 4),
        ("05", "NIF representante del perceptor", None, "texto", 1, 5),
        ("06", "Clave de rendimiento", None, "texto", 1, 6),
        ("07", "Nº percepciones", None, "numero", 1, 7),
        ("08", "Base de retención", None, "importe", 1, 8),
        ("09", "Tipo de retención", None, "importe", 1, 9),
        ("10", "Cuota", None, "importe", 1, 10),
        ("11", "Base no sujeta por residencia EEMM", None, "importe", 1, 11),
    ],

    # --- MODELO 180 — Resumen anual arrendamientos ---
    "180": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de declaración", None, "texto", 1, 3),
        ("04", "NIF del perceptor", None, "texto", 1, 4),
        ("05", "Clave", None, "texto", 1, 5),
        ("06", "Base de retenciones e ingresos a cuenta", None, "importe", 1, 6),
        ("07", "Tipo de retención", None, "importe", 1, 7),
        ("08", "Retenciones", None, "importe", 1, 8),
        ("09", "Nº de expedientes", None, "numero", 1, 9),
    ],

    # --- MODELO 187 — Acciones y participaciones IIC ---
    "187": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "NIF del perceptor", None, "texto", 1, 3),
        ("04", "Clave de rendimiento", "A=Dividendos, B=Intereses, C=Reembolso participaciones", "texto", 1, 4),
        ("05", "Nº percepciones", None, "numero", 1, 5),
        ("06", "Base de retención", None, "importe", 1, 6),
        ("07", "Tipo de retención", None, "importe", 1, 7),
        ("08", "Cuota", None, "importe", 1, 8),
    ],

    # --- MODELO 189 — Certificaciones individuales ---
    "189": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "NIF del socio/partícipe", None, "texto", 1, 3),
        ("04", "Clave", None, "texto", 1, 4),
        ("05", "Importe total de beneficios distribuidos", None, "importe", 1, 5),
        ("06", "Importe retenido", None, "importe", 1, 6),
    ],

    # --- MODELO 194 — Operaciones vinculadas y paraísos fiscales ---
    "194": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de operación", "A=Operaciones vinculadas, B=Operaciones paraísos fiscales", "texto", 1, 3),
        ("04", "NIF del tercero", None, "texto", 1, 4),
        ("05", "Denominación del tercero", None, "texto", 1, 5),
        ("06", "País de residencia", None, "texto", 1, 6),
        ("07", "Importe de la operación", None, "importe", 1, 7),
        ("08", "Método de valoración", "Método de valoración de operaciones vinculadas", "texto", 1, 8),
    ],

    # --- MODELO 198 — Operaciones con activos financieros ---
    "198": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "NIF del perceptor", None, "texto", 1, 3),
        ("04", "Clave de activo", None, "texto", 1, 4),
        ("05", "Nº de operaciones", None, "numero", 1, 5),
        ("06", "Valor de transmisión", None, "importe", 1, 6),
        ("07", "Valor de adquisición", None, "importe", 1, 7),
        ("08", "Ganancia o pérdida", None, "importe", 1, 8),
    ],

    # --- MODELO 296 — IRNR Resumen anual retenciones ---
    "296": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "NIF del perceptor no residente", None, "texto", 1, 3),
        ("04", "País de residencia del perceptor", None, "texto", 1, 4),
        ("05", "Clave de rendimiento", None, "texto", 1, 5),
        ("06", "Nº percepciones", None, "numero", 1, 6),
        ("07", "Base de retención", None, "importe", 1, 7),
        ("08", "Tipo de retención", None, "importe", 1, 8),
        ("09", "Cuota", None, "importe", 1, 9),
        ("10", "Aplicación de convenio", "Indica si se aplica convenio de doble imposición", "texto", 1, 10),
    ],

    # --- MODELO 036 — Declaración censal ---
    "036": [
        ("001", "Causas de presentación", None, "texto", 1, 1),
        ("002", "NIF/NIE", None, "texto", 1, 2),
        ("003", "Apellidos y nombre / Denominación", None, "texto", 1, 3),
        ("004", "Domicilio fiscal", None, "texto", 1, 4),
        ("005", "Epígrafes IAE", "Actividades económicas en el censo", "texto", 2, 5),
        ("006", "Régimen de IVA", "Régimen tributario del IVA", "texto", 2, 6),
        ("007", "Régimen de retenciones", "Régimen de retenciones e ingresos a cuenta", "texto", 2, 7),
        ("008", "Delegación/Empresa", "Delegación o empresa que presenta", "texto", 2, 8),
    ],

    # --- MODELO 123 — Retenciones IRPF/IS/IRNR ---
    "123": [
        ("01", "Rendimientos del trabajo", None, "importe", 1, 1),
        ("02", "Actividades económicas", None, "importe", 1, 2),
        ("03", "Premios", None, "importe", 1, 3),
        ("04", "Capital mobiliario", None, "importe", 1, 4),
        ("05", "Imputaciones de renta", None, "importe", 1, 5),
        ("06", "Ganancias patrimoniales", None, "importe", 1, 6),
        ("07", "Contraprestaciones por cesión de derechos de imagen", None, "importe", 1, 7),
        ("08", "Indemnizaciones", None, "importe", 1, 8),
        ("09", "Prestaciones por desempleo", None, "importe", 1, 9),
        ("10", "Otras rentas", None, "importe", 1, 10),
        ("11", "Nº de perceptores", None, "numero", 1, 11),
        ("12", "Cuotas a ingresar", None, "importe", 1, 12),
    ],

    # --- MODELO 130 — IRPF Pago fraccionado ---
    "130": [
        ("01", "Rendimientos netos estimación objetiva", None, "importe", 1, 1),
        ("02", "Rendimientos netos reducido estimación objetiva", None, "importe", 1, 2),
        ("03", "Rendimientos netos estimación objetiva — Ceuta y Melilla", None, "importe", 1, 3),
        ("04", "Rendimientos netos reducido estimación objetiva — Ceuta y Melilla", None, "importe", 1, 4),
        ("05", "Pagos fraccionados previos", None, "importe", 1, 5),
        ("06", "Resultado a ingresar", None, "importe", 1, 6),
    ],

    # --- MODELO 124 — IRNR retenciones sin EP ---
    "124": [
        ("01", "Rentas obtenidas sin mediación de establecimiento permanente — base", None, "importe", 1, 1),
        ("02", "Rentas obtenidas sin mediación de establecimiento permanente — retención", None, "importe", 1, 2),
        ("03", "Rendimientos del capital mobiliario", None, "importe", 1, 3),
        ("04", "Ganancias patrimoniales", None, "importe", 1, 4),
        ("05", "Nº de perceptores", None, "numero", 1, 5),
        ("06", "Cuotas a ingresar", None, "importe", 1, 6),
    ],

    # --- MODELO 216 — IRNR retenciones sin EP ---
    "216": [
        ("01", "NIF del declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Mes", None, "numero", 1, 3),
        ("04", "NIF del perceptor no residente", None, "texto", 1, 4),
        ("05", "País de residencia", None, "texto", 1, 5),
        ("06", "Clave de rendimiento", None, "texto", 1, 6),
        ("07", "Base de retención", None, "importe", 1, 7),
        ("08", "Tipo de retención", None, "importe", 1, 8),
        ("09", "Cuota", None, "importe", 1, 9),
    ],

    # --- MODELO 289 — Cuentas financieras DAC2/CRS ---
    "289": [
        ("01", "NIF de la entidad declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "Tipo de entidad", None, "texto", 1, 3),
        ("04", "NIF del titular de la cuenta", None, "texto", 1, 4),
        ("05", "País de residencia del titular", None, "texto", 1, 5),
        ("06", "Saldo o valor de la cuenta", None, "importe", 1, 6),
        ("07", "Rendimientos financieros", None, "importe", 1, 7),
    ],

    # --- MODELO 290 — Cuentas financieras FATCA ---
    "290": [
        ("01", "NIF de la entidad declarante", None, "texto", 1, 1),
        ("02", "Ejercicio", None, "numero", 1, 2),
        ("03", "NIF del titular de la cuenta", None, "texto", 1, 3),
        ("04", "País de residencia fiscal (EEUU)", None, "texto", 1, 4),
        ("05", "Saldo o valor de la cuenta", None, "importe", 1, 5),
        ("06", "Rendimientos financieros", None, "importe", 1, 6),
    ],
}

# ===========================================================================
# CLAVES — códigos de rendimiento/régimen por modelo/campaña
# ===========================================================================
CLAVES = {
    "111": [
        ("01", "Rendimientos del trabajo", "Clave de rendimiento: trabajo", "rendimiento"),
        ("02", "Actividades económicas", "Clave de rendimiento: actividades económicas", "rendimiento"),
        ("03", "Premios", "Clave de rendimiento: premios", "rendimiento"),
        ("04", "Capital mobiliario", "Clave de rendimiento: capital mobiliario", "rendimiento"),
        ("05", "Ganancias patrimoniales", "Clave de rendimiento: ganancias patrimoniales", "rendimiento"),
    ],
    "190": [
        ("A", "Rendimientos del trabajo", "Clave: rendimientos del trabajo", "rendimiento"),
        ("B", "Actividades económicas", "Clave: actividades económicas", "rendimiento"),
        ("C", "Premios", "Clave: premios", "rendimiento"),
        ("D", "Ganancias patrimoniales", "Clave: ganancias patrimoniales", "rendimiento"),
    ],
    "193": [
        ("A", "Dividendos y demás rendimientos de participación en recursos propios", "Clave: dividendos", "rendimiento"),
        ("B", "Rendimientos de cuenta corriente, depósitos y seguros de vida", "Clave: intereses y seguros", "rendimiento"),
        ("C", "Rendimientos derivados de la transmisión de activos financieros", "Clave: transmisión activos", "rendimiento"),
        ("D", "Rendimientos de contratos de renta vitalicia", "Clave: renta vitalicia", "rendimiento"),
        ("E", "Rendimientos de operaciones de capitalización", "Clave: capitalización", "rendimiento"),
    ],
    "196": [
        ("A", "Dividendos", "Clave: dividendos", "rendimiento"),
        ("B", "Intereses y seguros", "Clave: intereses", "rendimiento"),
        ("C", "Transmisión activos financieros", "Clave: transmisión", "rendimiento"),
    ],
    "296": [
        ("A", "Rendimientos del capital mobiliario", "Clave IRNR: capital mobiliario", "rendimiento"),
        ("B", "Ganancias patrimoniales", "Clave IRNR: ganancias patrimoniales", "rendimiento"),
        ("C", "Rentas inmobiliarias", "Clave IRNR: renta inmuebles", "rendimiento"),
        ("D", "Rentas de actividades económicas", "Clave IRNR: actividades económicas", "rendimiento"),
    ],
    "216": [
        ("A", "Rendimientos del capital mobiliario", "Clave IRNR: capital mobiliario sin EP", "rendimiento"),
        ("B", "Ganancias patrimoniales", "Clave IRNR: ganancias patrimoniales sin EP", "rendimiento"),
        ("C", "Rentas inmobiliarias", "Clave IRNR: inmuebles sin EP", "rendimiento"),
        ("D", "Rentas de actividades económicas", "Clave IRNR: actividades sin EP", "rendimiento"),
    ],
    "303": [
        ("0", "Régimen general", "Clave de régimen: general", "regimen"),
        ("1", "Régimen especial de agricultura, ganadería y pesca", "Clave de régimen: agrícola", "regimen"),
        ("2", "Régimen especial del recargo de equivalencia", "Clave de régimen: recargo equivalencia", "regimen"),
        ("3", "Régimen especial de bienes usados", "Clave de régimen: bienes usados", "regimen"),
        ("4", "Régimen especial del criterio de caja", "Clave de régimen: criterio caja", "regimen"),
        ("5", "Régimen especial de agencias de viajes", "Clave de régimen: agencias viaje", "regimen"),
        ("6", "Régimen especial de servicios de telecomunicaciones", "Clave de régimen: telecomunicaciones", "regimen"),
        ("7", "Régimen especial OSS (One Stop Shop)", "Clave de régimen: OSS", "regimen"),
    ],
}

# ===========================================================================
# INSTRUCCIONES — contenido por modelo/campaña
# ===========================================================================
INSTRUCCIONES = {
    "100": [
        ("caracteristicas", "¿Qué es el modelo 100?",
         "El modelo 100 es la declaración anual del IRPF. Permite regularizar la situación fiscal del contribuyente respecto al Impuesto sobre la Renta de las Personas Físicas durante todo el año natural.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Todos los residentes fiscales en España que hayan obtenido rentas durante el ejercicio, salvo que estén exentos por el importe y tipo de rentas percibidas.", 2),
        ("plazo", "Plazo de presentación",
         "Generalmente de abril a junio del año siguiente al que corresponda la declaración. Consulte cada año las fechas concretas en la sede de la AEAT.", 3),
        ("como-rellenar", "Cómo rellenar",
         "1. Identifíquese con Cl@ve, certificado electrónico o referencia.\n"
         "2. Revise los datos fiscales disponibles (borrador).\n"
         "3. Complete o modifique las casillas que correspondan.\n"
         "4. Verifique la casilla 0506 (Resultado de la declaración).\n"
         "5. Si es a ingresar, domicilie el pago o seleccione la forma de pago.\n"
         "6. Si es a devolver, indique el IBAN para la devolución.", 4),
    ],
    "303": [
        ("caracteristicas", "¿Qué es el modelo 303?",
         "Autoliquidación periódica del IVA. Se presenta de forma trimestral (o mensual para grandes empresas) y declara las cuotas repercutidas y deducibles del Impuesto sobre el Valor Añadido.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Todos los sujetos pasivos del IVA, incluidos los inscritos en el ROI, los que realicen entregas de bienes o prestaciones de servicios sujetas al impuesto.", 2),
        ("plazo", "Plazo de presentación",
         "Trimestral: del 1 al 20 de abril, julio, octubre y del 1 al 30 de enero del año siguiente.\n"
         "Mensual: del 1 al 20 del mes siguiente al periodo de liquidación.", 3),
        ("como-rellenar", "Cómo rellenar",
         "1. Registre en las casillas 01-05 la base y cuota de operaciones corrientes.\n"
         "2. Registre adquisiciones interiores (06-09) e intracomunitarias (10-13).\n"
         "3. Declare importaciones (14).\n"
         "4. Registre operaciones exentas (21) y exportaciones (22).\n"
         "5. Indique la cuota deducible (38-50).\n"
         "6. Calcule el resultado (51).\n"
         "7. Si es a ingresar (62), a compensar (60) o a devolver (61).", 4),
    ],
    "111": [
        ("caracteristicas", "¿Qué es el modelo 111?",
         "Declaración trimestral de retenciones e ingresos a cuenta del IRPF sobre rendimientos del trabajo, actividades económicas, premios y determinadas ganancias patrimoniales.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Los obligados a practicar retenciones o ingresos a cuenta por los rendimientos mencionados.", 2),
        ("plazo", "Plazo de presentación",
         "Del 1 al 20 de abril, julio, octubre y del 1 al 20 de enero.", 3),
        ("como-rellenar", "Cómo rellenar",
         "1. Identifíquese como declarante.\n"
         "2. Indique el número de perceptores por cada tipo de rendimiento.\n"
         "3. Registre las bases de retención y las cuotas correspondientes.\n"
         "4. Verifique la casilla 12 (Cuotas a ingresar).", 4),
    ],
    "036": [
        ("caracteristicas", "¿Qué es el modelo 036?",
         "Declaración censal de alta, modificación de datos y baja en el Censo de Empresarios, Profesion y Retenedores.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Personas físicas y jurídicas que inicien una actividad empresarial o profesional, modifiquen sus datos censales o cesen en la actividad.", 2),
        ("plazo", "Plazo de presentación",
         "En el plazo de un mes desde la fecha de inicio de la actividad o desde que se produzca la modificación de datos.", 3),
    ],
    "347": [
        ("caracteristicas", "¿Qué es el modelo 347?",
         "Declaración anual de operaciones con terceras personas. Se debe presentar cuando el volumen de operaciones con un mismo tercero supera los 3.005,06 euros en el año natural.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Personas físicas y jurídicas, incluidas las entidades en régimen de atribución de rentas, que hayan realizado operaciones con terceros por importe superior a 3.005,06 euros.", 2),
        ("plazo", "Plazo de presentación",
         "Del 1 al 28 de febrero del año siguiente al que corresponda la declaración.", 3),
    ],
    "349": [
        ("caracteristicas", "¿Qué es el modelo 349?",
         "Declaración recapitulativa de operaciones intracomunitarias. Informa de las entregas y adquisiciones de bienes y servicios entre Estados miembros de la UE.", 1),
        ("quien-debe", "¿Quién debe presentar?",
         "Sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.", 2),
        ("plazo", "Plazo de presentación",
         "Mensual o trimestral según el volumen de operaciones. Del 1 al 20 del mes siguiente al periodo.", 3),
    ],
}

# ===========================================================================
# NORMATIVA — BOE orders per model
# ===========================================================================
NORMATIVA = [
    ("100", "BOE-A-2024-26789", "Orden HAC/1234/2024 — IRPF modelo 100",
     "2024-12-20", "https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf",
     "Aprueba el modelo 100 de declaración del IRPF y sus instrucciones"),
    ("111", "BOE-A-2011-4948", "Orden EHA/586/2011 — Modelo 110 (sustituido por 111)",
     "2011-03-09", "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     "Aprueba modelos de declaración de retenciones del IRPF"),
    ("115", "BOE-A-2011-4948", "Orden EHA/586/2011 — Modelo 115",
     "2011-03-09", "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     "Aprueba modelo 115 de retenciones por arrendamientos"),
    ("123", "BOE-A-2011-4948", "Orden EHA/586/2011 — Modelo 123",
     "2011-03-09", "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     "Aprueba modelo 123 de retenciones rentas sujetas a retención"),
    ("130", "BOE-A-2011-4948", "Orden EHA/586/2011 — Modelo 130",
     "2011-03-09", "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
     "Aprueba modelo 130 de pago fraccionado IRPF"),
    ("180", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 180",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 180 resumen anual retenciones arrendamientos"),
    ("187", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 187",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 187 acciones y participaciones IIC"),
    ("189", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 189",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 189 certificaciones individuales"),
    ("190", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 190",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 190 resumen anual retenciones"),
    ("193", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 193",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 193 retenciones capital mobiliario"),
    ("194", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 194",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 194 operaciones vinculadas y paraísos fiscales"),
    ("196", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 196",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 196 resumen anual capital mobiliario"),
    ("198", "BOE-A-2024-23244", "Orden HAC/1100/2024 — Modelo 198",
     "2024-11-15", "https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf",
     "Aprueba modelo 198 operaciones con activos financieros"),
    ("303", "BOE-A-2024-16738", "Orden HAC/891/2024 — Modelo 303",
     "2024-09-10", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     "Aprueba modelo 303 de autoliquidación IVA"),
    ("347", "BOE-A-2024-25303", "Orden HAC/1187/2024 — Modelo 347",
     "2024-12-02", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303",
     "Aprueba modelo 347 operaciones con terceros"),
    ("349", "BOE-A-2024-16738", "Orden HAC/891/2024 — Modelo 349",
     "2024-09-10", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     "Aprueba modelo 349 operaciones intracomunitarias"),
    ("390", "BOE-A-2024-16738", "Orden HAC/891/2024 — Modelo 390",
     "2024-09-10", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738",
     "Aprueba modelo 390 resumen anual IVA"),
    ("036", "BOE-A-2024-25303", "Orden HAC/1187/2024 — Modelo 036",
     "2024-12-02", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303",
     "Aprueba modelo 036 declaración censal"),
    ("124", "BOE-A-2004-19886", "RDL 5/2004 — IRNR",
     "2004-12-03", "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     "Texto refundido de la Ley del IRNR"),
    ("216", "BOE-A-2004-19886", "RDL 5/2004 — IRNR",
     "2004-12-03", "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     "Texto refundido de la Ley del IRNR"),
    ("296", "BOE-A-2004-19886", "RDL 5/2004 — IRNR",
     "2004-12-03", "https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886",
     "Texto refundido de la Ley del IRNR"),
    ("289", "BOE-A-2024-24098", "Orden HAC/1150/2024 — Modelo 289",
     "2024-11-20", "https://www.boe.es/buscar/act.php?id=BOE-A-2024-24098",
     "Aprueba modelo 289 cuentas financieras DAC2/CRS"),
    ("290", "BOE-A-2014-6854", "Acuerdo FATCA España-EEUU",
     "2014-07-01", "https://www.boe.es/buscar/act.php?id=BOE-A-2014-6854",
     "Acuerdo FATCA España-EE.UU.; Orden HAP/1136/2014 aprueba Modelo 290"),
]


OPERATIVA_CAMPANA = {
    "100": {
        "categoria_obligado": "contribuyente_irpf",
        "frecuencia_presentacion": "anual",
        "ventana_presentacion": "campana_renta_aeat",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 100 los contribuyentes del IRPF obligados a declarar conforme a los limites legales vigentes.",
        "plazo_resumen": "La presentacion del modelo 100 se realiza dentro del plazo general de la campana de renta fijado cada ano por la AEAT.",
        "presentacion_resumen": "La presentacion del modelo 100 se realiza por via electronica mediante la sede de la AEAT, con los sistemas de identificacion admitidos en cada campana.",
        "norma_base": "LIRPF",
        "nota": "Metadato operativo curado para agentes.",
    },
    "111": {
        "categoria_obligado": "retenedor_irpf",
        "frecuencia_presentacion": "trimestral",
        "ventana_presentacion": "primeros_20_dias_periodo_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 111 los obligados a practicar retenciones e ingresos a cuenta por rendimientos del trabajo y determinadas actividades economicas.",
        "plazo_resumen": "El modelo 111 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.",
        "presentacion_resumen": "La presentacion del modelo 111 se realiza por via electronica a traves de la sede de la AEAT.",
        "norma_base": "LIRPF retenciones",
        "nota": "Metadato operativo curado para agentes.",
    },
    "115": {
        "categoria_obligado": "retenedor_arrendamientos",
        "frecuencia_presentacion": "trimestral",
        "ventana_presentacion": "primeros_20_dias_periodo_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 115 los obligados a practicar retenciones por arrendamientos de inmuebles urbanos.",
        "plazo_resumen": "El modelo 115 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.",
        "presentacion_resumen": "La presentacion del modelo 115 se realiza por via electronica a traves de la sede de la AEAT.",
        "norma_base": "LIRPF arrendamientos",
        "nota": "Metadato operativo curado para agentes.",
    },
    "124": {
        "categoria_obligado": "retenedor_irnr",
        "frecuencia_presentacion": "mensual",
        "ventana_presentacion": "primeros_20_dias_mes_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 124 los obligados a retener sobre determinadas rentas del capital mobiliario obtenidas por no residentes sin establecimiento permanente.",
        "plazo_resumen": "El modelo 124 se presenta mensualmente dentro de los primeros veinte dias naturales del mes siguiente al periodo declarado.",
        "presentacion_resumen": "La presentacion del modelo 124 se realiza por medios electronicos a traves de la sede de la AEAT.",
        "norma_base": "IRNR art. 25",
        "nota": "Metadato operativo curado para agentes.",
    },
    "216": {
        "categoria_obligado": "retenedor_irnr",
        "frecuencia_presentacion": "mensual",
        "ventana_presentacion": "primeros_20_dias_mes_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 216 los obligados a practicar retenciones e ingresos a cuenta sobre determinadas rentas de no residentes sin establecimiento permanente.",
        "plazo_resumen": "El modelo 216 se presenta mensualmente dentro de los primeros veinte dias naturales del mes siguiente al periodo declarado.",
        "presentacion_resumen": "La presentacion del modelo 216 se realiza por via electronica a traves de la sede de la AEAT.",
        "norma_base": "IRNR art. 14",
        "nota": "Metadato operativo curado para agentes.",
    },
    "296": {
        "categoria_obligado": "retenedor_irnr",
        "frecuencia_presentacion": "anual",
        "ventana_presentacion": "plazo_fijado_aeat",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 296 los retenedores y obligados a ingresar a cuenta que deban resumir anualmente las rentas sujetas al IRNR sin establecimiento permanente.",
        "plazo_resumen": "El modelo 296 se presenta con caracter anual en el plazo fijado por la AEAT para el resumen anual de retenciones e ingresos a cuenta.",
        "presentacion_resumen": "La presentacion del modelo 296 se realiza electronicamente mediante la sede de la AEAT.",
        "norma_base": "IRNR art. 14",
        "nota": "Metadato operativo curado para agentes.",
    },
    "303": {
        "categoria_obligado": "empresario_o_profesional_iva",
        "frecuencia_presentacion": "trimestral",
        "ventana_presentacion": "plazo_general_aeat",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 303 los empresarios y profesionales obligados a autoliquidar el IVA del periodo.",
        "plazo_resumen": "El modelo 303 se presenta en los plazos generales fijados por la AEAT para la autoliquidacion del IVA.",
        "presentacion_resumen": "La presentacion del modelo 303 se realiza por via electronica mediante la sede de la AEAT.",
        "norma_base": "LIVA art. 71",
        "nota": "Metadato operativo curado para agentes.",
    },
    "349": {
        "categoria_obligado": "operador_intracomunitario_iva",
        "frecuencia_presentacion": "mensual",
        "ventana_presentacion": "primeros_20_dias_mes_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 349 los sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.",
        "plazo_resumen": "El modelo 349 se presenta con caracter mensual o trimestral segun el volumen de operaciones, del 1 al 20 del mes siguiente al periodo.",
        "presentacion_resumen": "La presentacion del modelo 349 se realiza por via electronica a traves de la sede de la AEAT.",
        "norma_base": "LIVA operaciones intracomunitarias",
        "nota": "Metadato operativo curado para agentes.",
    },
    "390": {
        "categoria_obligado": "sujeto_pasivo_iva",
        "frecuencia_presentacion": "anual",
        "ventana_presentacion": "plazo_fijado_aeat",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 390 los sujetos pasivos del IVA obligados a presentar el resumen anual, salvo excepciones previstas por la normativa.",
        "plazo_resumen": "El modelo 390 se presenta con caracter anual en el plazo fijado por la AEAT junto con el cierre del ejercicio de IVA.",
        "presentacion_resumen": "La presentacion del modelo 390 se realiza por via electronica mediante la sede de la AEAT.",
        "norma_base": "LIVA resumen anual",
        "nota": "Metadato operativo curado para agentes.",
    },
    "036": {
        "categoria_obligado": "obligado_censal",
        "frecuencia_presentacion": "eventual",
        "ventana_presentacion": "1_mes_desde_hecho",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 036 las personas fisicas o juridicas que inicien actividad, modifiquen datos censales o causen baja en el censo.",
        "plazo_resumen": "El modelo 036 se presenta dentro del plazo de un mes desde el inicio de actividad o desde la modificacion censal correspondiente.",
        "presentacion_resumen": "La presentacion del modelo 036 puede realizarse por la sede de la AEAT con los sistemas de identificacion admitidos.",
        "norma_base": "Censo AEAT",
        "nota": "Metadato operativo curado para agentes.",
    },
    "347": {
        "categoria_obligado": "declarante_operaciones_terceros",
        "frecuencia_presentacion": "anual",
        "ventana_presentacion": "febrero_ano_siguiente",
        "canal_presentacion": "electronica",
        "obligados_resumen": "Deben presentar el modelo 347 quienes hayan realizado operaciones con terceros por importe superior al umbral legal anual.",
        "plazo_resumen": "El modelo 347 se presenta con caracter anual durante el mes de febrero del ano siguiente.",
        "presentacion_resumen": "La presentacion del modelo 347 se realiza por via electronica a traves de la sede de la AEAT.",
        "norma_base": "LGT informacion terceros",
        "nota": "Metadato operativo curado para agentes.",
    },
}


def get_db_url(args_db_url):
    if args_db_url:
        return args_db_url
    url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        print("ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found.")
        print("Provide --db-url or set env vars.")
        sys.exit(1)
    return url


def connect(db_url):
    try:
        return psycopg.connect(db_url)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        sys.exit(1)


def seed_v2(conn, dry_run=False, campana=CAMPANA_DEFAULT):
    with conn.cursor() as cur:
        # --- 1. Insert campaigns ---
        print(f"=== Campañas ({campana}) ===")
        for modelo_codigo, url_instr, url_norm, url_fmt in CAMPAÑAS:
            if dry_run:
                print(f"  [DRY] modelo={modelo_codigo} campana={campana}")
                continue
            # Deactivate previous campaigns for this model before inserting
            cur.execute(
                """
                UPDATE modelo_campana SET activo = false
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = %s)
                """,
                (modelo_codigo,),
            )
            cur.execute(
                """
                INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
                SELECT m.id, %s, %s, %s, %s, true
                FROM aeat_modelo m
                WHERE m.codigo = %s
                ON CONFLICT (modelo_id, campana) DO UPDATE SET
                    url_instrucciones = EXCLUDED.url_instrucciones,
                    url_normativa = EXCLUDED.url_normativa,
                    url_formato = EXCLUDED.url_formato,
                    activo = true
                """,
                (campana, url_instr, url_norm, url_fmt, modelo_codigo),
            )
        conn.commit()
        if not dry_run:
            print(f"  Upserted {len(CAMPAÑAS)} campaigns.")

        # --- 2. Insert casillas ---
        print(f"\n=== Casillas ===")
        total_cas = 0
        for modelo_codigo, casillas in CASILLAS.items():
            # Get campana_id
            cur.execute(
                """
                SELECT mc.id FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = %s AND mc.campana = %s
                """,
                (modelo_codigo, campana),
            )
            camp_row = cur.fetchone()
            if not camp_row:
                print(f"  SKIP: modelo {modelo_codigo} campaign {campana} not found")
                continue
            campana_id = camp_row[0]

            for codigo, etiqueta, desc, tipo, pagina, orden in casillas:
                if dry_run:
                    print(f"  [DRY] {modelo_codigo} casilla={codigo} '{etiqueta}'")
                    total_cas += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (campana_id, codigo) DO UPDATE SET
                        etiqueta = EXCLUDED.etiqueta,
                        descripcion = EXCLUDED.descripcion,
                        tipo_casilla = EXCLUDED.tipo_casilla,
                        pagina = EXCLUDED.pagina,
                        orden = EXCLUDED.orden
                    """,
                    (campana_id, codigo, etiqueta, desc, tipo, pagina, orden),
                )
                total_cas += 1

        conn.commit()
        if not dry_run:
            print(f"  Upserted {total_cas} casillas.")

        # --- 3. Insert claves ---
        print(f"\n=== Claves ===")
        total_claves = 0
        for modelo_codigo, claves in CLAVES.items():
            cur.execute(
                """
                SELECT mc.id FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = %s AND mc.campana = %s
                """,
                (modelo_codigo, campana),
            )
            camp_row = cur.fetchone()
            if not camp_row:
                print(f"  SKIP: modelo {modelo_codigo} campaign {campana} not found")
                continue
            campana_id = camp_row[0]

            for codigo, etiqueta, desc, tipo in claves:
                if dry_run:
                    print(f"  [DRY] {modelo_codigo} clave={codigo} '{etiqueta}'")
                    total_claves += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (campana_id, codigo) DO UPDATE SET
                        etiqueta = EXCLUDED.etiqueta,
                        descripcion = EXCLUDED.descripcion,
                        tipo_clave = EXCLUDED.tipo_clave
                    """,
                    (campana_id, codigo, etiqueta, desc, tipo),
                )
                total_claves += 1

        conn.commit()
        if not dry_run:
            print(f"  Upserted {total_claves} claves.")

        # --- 4. Insert instrucciones ---
        print(f"\n=== Instrucciones ===")
        total_instr = 0
        for modelo_codigo, instrs in INSTRUCCIONES.items():
            cur.execute(
                """
                SELECT mc.id FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = %s AND mc.campana = %s
                """,
                (modelo_codigo, campana),
            )
            camp_row = cur.fetchone()
            if not camp_row:
                print(f"  SKIP: modelo {modelo_codigo} campaign {campana} not found")
                continue
            campana_id = camp_row[0]

            for seccion, titulo, contenido, orden in instrs:
                if dry_run:
                    print(f"  [DRY] {modelo_codigo} instr='{titulo}'")
                    total_instr += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (campana_id, seccion, titulo) DO UPDATE SET
                        contenido = EXCLUDED.contenido,
                        orden = EXCLUDED.orden
                    """,
                    (campana_id, seccion, titulo, contenido, orden),
                )
                total_instr += 1

        conn.commit()
        if not dry_run:
            print(f"  Upserted {total_instr} instrucciones.")

        # --- 5. Insert normativa ---
        print(f"\n=== Normativa ===")
        total_norm = 0
        for modelo_codigo, boe_id, titulo, fecha, url_boe, resumen in NORMATIVA:
            cur.execute(
                """
                SELECT id FROM aeat_modelo WHERE codigo = %s
                """,
                (modelo_codigo,),
            )
            model_row = cur.fetchone()
            if not model_row:
                print(f"  SKIP: modelo {modelo_codigo} not found")
                continue
            modelo_id = model_row[0]

            if dry_run:
                print(f"  [DRY] {modelo_codigo} normativa='{titulo}' boe={boe_id}")
                total_norm += 1
                continue

            cur.execute(
                """
                INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (modelo_id, boe_id) DO UPDATE SET
                    titulo = EXCLUDED.titulo,
                    fecha = EXCLUDED.fecha,
                    url_boe = EXCLUDED.url_boe,
                    resumen = EXCLUDED.resumen
                """,
                (modelo_id, boe_id, titulo, fecha, url_boe, resumen),
            )
            total_norm += 1

        conn.commit()
        if not dry_run:
            print(f"  Upserted {total_norm} normativa entries.")

        # --- 6. Insert campaign operational metadata ---
        print(f"\n=== Operativa de campana ===")
        total_operativa = 0
        for modelo_codigo, payload in OPERATIVA_CAMPANA.items():
            payload.setdefault("origen_metadato", "seed_curado")
            payload.setdefault("estado_metadato", "curado")
            cur.execute(
                """
                SELECT mc.id
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE m.codigo = %s AND mc.campana = %s
                """,
                (modelo_codigo, campana),
            )
            camp_row = cur.fetchone()
            if not camp_row:
                print(f"  SKIP: modelo {modelo_codigo} campaign {campana} not found")
                continue
            campana_id = camp_row[0]

            if dry_run:
                print(f"  [DRY] {modelo_codigo} operativa={payload['categoria_obligado']}")
                total_operativa += 1
                continue

            cur.execute(
                """
                INSERT INTO modelo_campana_operativa (
                    campana_id,
                    categoria_obligado,
                    frecuencia_presentacion,
                    ventana_presentacion,
                    canal_presentacion,
                    obligados_resumen,
                    plazo_resumen,
                    presentacion_resumen,
                    norma_base,
                    nota,
                    origen_metadato,
                    estado_metadato
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (campana_id) DO UPDATE SET
                    categoria_obligado = EXCLUDED.categoria_obligado,
                    frecuencia_presentacion = EXCLUDED.frecuencia_presentacion,
                    ventana_presentacion = EXCLUDED.ventana_presentacion,
                    canal_presentacion = EXCLUDED.canal_presentacion,
                    obligados_resumen = EXCLUDED.obligados_resumen,
                    plazo_resumen = EXCLUDED.plazo_resumen,
                    presentacion_resumen = EXCLUDED.presentacion_resumen,
                    norma_base = EXCLUDED.norma_base,
                    nota = EXCLUDED.nota,
                    origen_metadato = EXCLUDED.origen_metadato,
                    estado_metadato = EXCLUDED.estado_metadato
                """,
                (
                    campana_id,
                    payload["categoria_obligado"],
                    payload["frecuencia_presentacion"],
                    payload["ventana_presentacion"],
                    payload["canal_presentacion"],
                    payload["obligados_resumen"],
                    payload["plazo_resumen"],
                    payload["presentacion_resumen"],
                    payload["norma_base"],
                    payload["nota"],
                    payload["origen_metadato"],
                    payload["estado_metadato"],
                ),
            )
            total_operativa += 1

        conn.commit()
        if not dry_run:
            print(f"  Upserted {total_operativa} operativa entries.")


def main():
    parser = argparse.ArgumentParser(description="Seed AEAT models v2 data")
    parser.add_argument("--db-url", help="Database connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("--campana", default=CAMPANA_DEFAULT, help="Campaign year (default: 2025)")
    args = parser.parse_args()

    db_url = get_db_url(args.db_url)
    print(f"Database: {db_url[:40]}...")
    print(f"Dry run: {args.dry_run}")
    print(f"Campaign: {args.campana}")

    conn = connect(db_url)
    try:
        seed_v2(conn, dry_run=args.dry_run, campana=args.campana)
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
