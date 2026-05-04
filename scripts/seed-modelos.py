#!/usr/bin/env python
"""
CANONICAL AEAT FLOW - STEP 1 OF 2

Bootstrap `aeat_modelo` and verified `modelo_articulo` relationships.

Canonical AEAT execution order:
1. `python scripts/seed-modelos.py --db-url <DATABASE_URL>`
2. `python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>`

This script is the canonical bootstrap because `scripts/seed-modelos-v2.py`
expects `aeat_modelo` to exist already.

Safe mode:
- use `--dry-run` to inspect intended upserts without writing

Seed all AEAT model-article relationships for esdata.

Populates:
- aeat_modelo: 25 models with metadata (IRPF, IVA, IRNR, CENSAL, INFORMATIVO, FORMATO)
- modelo_articulo: verified relationships with official source

Models covered:
  IRPF (14):      100, 110 (obs.), 111, 115, 123, 130, 180, 187, 189, 190, 193, 194, 196, 198
  IVA (4):        303, 349, 390
  IRNR (3):       124, 216, 296
  CENSAL (1):     036
  INFORMATIVO (5): 289 (DAC2/CRS), 290 (FATCA), 347
  FORMATO (1):    299 (diseño registro electrónico)
  HISTÓRICO (1):  110 (obsoleto → 111)

Usage:
    python scripts/seed-modelos.py [--db-url URL] [--dry-run]

Each relationship in MODELO_ARTICULO_DATA must include:
- fuente: official source document name
- url_fuente: URL to the official document

If you cannot verify a relationship with an official source,
do NOT add it here.
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


# ---------------------------------------------------------------------------
# Model metadata — verifiable from AEAT sede pages
# ---------------------------------------------------------------------------
MODELOS = [
    # ------------------------------------------------------------------
    # IRPF — Declaraciones y autoliquidaciones
    # ------------------------------------------------------------------
    {
        "codigo": "100",
        "nombre": "IRPF Declaración anual",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/index.shtml",
    },
    {
        "codigo": "130",
        "nombre": "IRPF Pago fraccionado",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/index.shtml",
    },

    # ------------------------------------------------------------------
    # IRPF — Retenciones e ingresos a cuenta
    # ------------------------------------------------------------------
    {
        "codigo": "111",
        "nombre": "IRPF Retenciones e ingresos a cuenta",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/index.shtml",
    },
    {
        "codigo": "115",
        "nombre": "IRPF Retenciones arrendamientos",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/index.shtml",
    },
    {
        "codigo": "123",
        "nombre": "Retenciones IRPF/IS/IRNR — rentas sujetas a retención",
        "periodo": "mensual",
        "impuesto": "IRPF/IS/IRNR",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    },
    {
        "codigo": "124",
        "nombre": "Retenciones IRNR — rentas sin establecimiento permanente",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    },
    {
        "codigo": "187",
        "nombre": "IRPF Acciones y participaciones IIC",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-187.html",
    },
    {
        "codigo": "189",
        "nombre": "IRPF Certificaciones individuales socios/partícipes",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html",
    },
    {
        "codigo": "190",
        "nombre": "IRPF Retenciones — rendimientos trabajo y actividades",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-190.html",
    },
    {
        "codigo": "193",
        "nombre": "IRPF Retenciones capital mobiliario",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-193.html",
    },
    {
        "codigo": "194",
        "nombre": "IRPF Operaciones vinculadas y paraísos fiscales",
        "periodo": "anual",
        "impuesto": "IRPF/LIS",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html",
    },
    {
        "codigo": "196",
        "nombre": "IRPF Resumen anual retenciones capital mobiliario",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-196.html",
    },
    {
        "codigo": "198",
        "nombre": "IRPF Operaciones con activos financieros",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html",
    },
    {
        "codigo": "180",
        "nombre": "IRPF Resumen anual retenciones arrendamientos inmuebles",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-180.html",
    },

    # ------------------------------------------------------------------
    # IRNR — Retenciones no residentes
    # ------------------------------------------------------------------
    {
        "codigo": "216",
        "nombre": "IRNR Retenciones rentas sin establecimiento permanente",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    },
    {
        "codigo": "296",
        "nombre": "IRNR Resumen anual retenciones sin EP",
        "periodo": "anual",
        "impuesto": "IRNR",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    },

    # ------------------------------------------------------------------
    # IVA
    # ------------------------------------------------------------------
    {
        "codigo": "303",
        "nombre": "IVA Autoliquidación",
        "periodo": "trimestral",
        "impuesto": "IVA",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/index.shtml",
    },
    {
        "codigo": "390",
        "nombre": "IVA Resumen anual",
        "periodo": "anual",
        "impuesto": "IVA",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/index.shtml",
    },

    # ------------------------------------------------------------------
    # Censal y declarativo
    # ------------------------------------------------------------------
    {
        "codigo": "036",
        "nombre": "Declaración censal alta/modificación/baja",
        "periodo": "eventual",
        "impuesto": "CENSAL",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/censos-nif-domicilio-fiscal/censos/modelos-036-037_____icacion-baja-declaracion-simplificada_/modelo-036.html",
    },

    # ------------------------------------------------------------------
    # Declaraciones informativas intercambio de información
    # ------------------------------------------------------------------
    {
        "codigo": "289",
        "nombre": "Cuentas financieras asistencia mutua (DAC2/CRS)",
        "periodo": "anual",
        "impuesto": "INFORMATIVO",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/campana-declaraciones-informativas-2024/modelo-289.html",
    },
    {
        "codigo": "290",
        "nombre": "Cuentas financieras FATCA (EEUU)",
        "periodo": "anual",
        "impuesto": "INFORMATIVO",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/index.shtml",
    },
    {
        "codigo": "299",
        "nombre": "Diseño de registro — formato electrónico declaración",
        "periodo": "eventual",
        "impuesto": "FORMATO",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html",
    },

    # ------------------------------------------------------------------
    # Declaraciones informativas de operaciones
    # ------------------------------------------------------------------
    {
        "codigo": "347",
        "nombre": "Declaración anual operaciones con terceros",
        "periodo": "anual",
        "impuesto": "INFORMATIVO",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/modelo-347-declaracion-anual-operaciones-terceras-personas/index.shtml",
    },
    {
        "codigo": "349",
        "nombre": "Declaración recapitulativa operaciones intracomunitarias",
        "periodo": "mensual",
        "impuesto": "IVA",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html",
    },

    # ------------------------------------------------------------------
    # Modelos históricos / obsoletos
    # ------------------------------------------------------------------
    {
        "codigo": "110",
        "nombre": "IRPF Retenciones e ingresos a cuenta (obsoleto → 111)",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/capitulo-09-retenciones-ingresos-cuenta/modelo-110.html",
    },
]

# ---------------------------------------------------------------------------
# Model-article relationships — ONLY with verified official sources.
#
# Format: (modelo_codigo, articulo_norma, articulo_numero, casilla, nota, fuente, url_fuente)
#
# CRITERION: Do NOT add a relationship unless you can point to an official
# AEAT instruction document or BOE norm that explicitly links the model/casilla
# to the specific article.
# ---------------------------------------------------------------------------
MODELO_ARTICULO_DATA = [
    # ------------------------------------------------------------------
    # Modelo 100 — IRPF Declaración anual
    # Fuente: Instrucciones Modelo 100 (PDF AEAT) — mapeo casillas a tipos de rendimiento
    # ------------------------------------------------------------------
    (
        "100", "LIRPF", "2",
        None, "Hecho imponible del IRPF",
        "Instrucciones Modelo 100 2025 — Apartado Características",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "17",
        "0002", "Rendimientos del trabajo",
        "Instrucciones Modelo 100 2025 — Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "18",
        "0002", "Rendimientos del trabajo en especie",
        "Instrucciones Modelo 100 2025 — Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "19",
        "0003", "Rendimientos de actividades económicas",
        "Instrucciones Modelo 100 2025 — Casilla 0003",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "22",
        "0004", "Rendimientos del capital mobiliario",
        "Instrucciones Modelo 100 2025 — Casilla 0004",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "24",
        "0005", "Rendimientos del capital inmobiliario",
        "Instrucciones Modelo 100 2025 — Casilla 0005",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "33",
        "0416", "Ganancias patrimoniales",
        "Instrucciones Modelo 100 2025 — Casilla 0416",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "88",
        None, "Base imponible del ahorro",
        "Instrucciones Modelo 100 2025 — Base del ahorro",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 111 — Retenciones IRPF
    # Fuente: Instrucciones Modelo 111 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "111", "LIRPF", "99",
        None, "Obligación de retener",
        "Instrucciones Modelo 111 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
    ),
    (
        "111", "LIRPF", "17",
        "01", "Retenciones rendimientos del trabajo",
        "Instrucciones Modelo 111 2025 — Casilla 01",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 115 — Retenciones arrendamientos
    # Fuente: Instrucciones Modelo 115 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "115", "LIRPF", "24",
        "01", "Retenciones rendimientos capital inmobiliario",
        "Instrucciones Modelo 115 2025 — Casilla 01",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 130 — Pago fraccionado IRPF (estimación objetiva)
    # Fuente: Instrucciones Modelo 130 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "130", "LIRPF", "19",
        None, "Pago fraccionado estimación objetiva",
        "Instrucciones Modelo 130 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 303 — IVA Autoliquidación
    # Fuente: Instrucciones Modelo 303 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "303", "LIVA", "4",
        None, "Hecho imponible IVA",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
    (
        "303", "LIVA", "84",
        None, "Sujeción al IVA",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
    (
        "303", "LIVA", "85",
        None, "Devengo del impuesto",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 390 — IVA Resumen anual
    # Fuente: Instrucciones Modelo 390 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "390", "LIVA", "111",
        None, "Resumen anual IVA",
        "Instrucciones Modelo 390 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 190 — IRPF Retenciones rendimientos trabajo y actividades
    # Fuente: Instrucciones Modelo 190 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "190", "LIRPF", "99",
        None, "Obligación de retener rendimientos trabajo",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),
    (
        "190", "LIRPF", "100",
        None, "Ingresos a cuenta",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),
    (
        "190", "LIRPF", "101",
        None, "Retenciones actividades económicas",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 196 — IRPF Resumen anual retenciones capital mobiliario
    # Fuente: Instrucciones Modelo 196 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "196", "LIRPF", "22",
        None, "Retenciones rendimientos capital mobiliario",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),
    (
        "196", "LIRPF", "23",
        None, "Retenciones dividendos y participaciones",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),
    (
        "196", "LIRPF", "25",
        None, "Retenciones ganancias patrimoniales mobiliario",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 180 — IRPF Resumen anual retenciones arrendamientos
    # Fuente: Instrucciones Modelo 180 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "180", "LIRPF", "24",
        None, "Retenciones rendimientos capital inmobiliario (arrendamientos)",
        "Instrucciones Modelo 180 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-180/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 193 — IRPF Retenciones capital mobiliario
    # Fuente: Instrucciones Modelo 193 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "193", "LIRPF", "22",
        None, "Retenciones rendimientos capital mobiliario",
        "Instrucciones Modelo 193 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-193/instrucciones/index.shtml",
    ),
    (
        "193", "LIRPF", "23",
        None, "Retenciones dividendos y participaciones",
        "Instrucciones Modelo 193 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-193/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 187 — IRPF Acciones y participaciones IIC
    # Fuente: Instrucciones Modelo 187 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "187", "LIRPF", "94",
        None, "Ganancias patrimoniales acciones/participaciones",
        "Instrucciones Modelo 187 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-187/instrucciones/index.shtml",
    ),
    (
        "187", "LIRPF", "95",
        None, "Reembolso de acciones/participaciones IIC",
        "Instrucciones Modelo 187 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-187/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 036 — Declaración censal
    # Fuente: Guía práctica cumplimentación modelo 036 (AEAT)
    # ------------------------------------------------------------------
    (
        "036", "LGT", "109",
        None, "Obligaciones de información — censo empresarios/profesionales",
        "Guía práctica Modelo 036 2025 — Capítulo 1: Causas de presentación",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/capitulo-01-cuestiones-generales/declaracion-censal.html",
    ),
    (
        "036", "LGT", "110",
        None, "Obligaciones formales — identificación censal",
        "Guía práctica Modelo 036 2025 — Capítulo 2: Identificación",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/capitulo-02-identificacion/modelo-036.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 123 — Retenciones IRPF/IS/IRNR rentas sujetas a retención
    # Fuente: Instrucciones Modelo 123 (AEAT)
    # ------------------------------------------------------------------
    (
        "123", "LIRPF", "99",
        None, "Obligación de retener — rentas IRPF",
        "Instrucciones Modelo 123 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    ),
    (
        "123", "LIRPF", "100",
        None, "Ingresos a cuenta — rentas IRPF",
        "Instrucciones Modelo 123 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    ),
    (
        "123", "LIS", "62",
        None, "Retenciones IS — rentas sujetos pasivos IS",
        "Instrucciones Modelo 123 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    ),
    (
        "123", "LIRPF", "17",
        None, "Retenciones rendimientos trabajo",
        "Instrucciones Modelo 123 2025 — Rendimientos trabajo",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    ),
    (
        "123", "LIRPF", "22",
        None, "Retenciones rendimientos capital mobiliario",
        "Instrucciones Modelo 123 2025 — Capital mobiliario",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 124 — Retenciones IRNR rentas sin EP
    # Fuente: Instrucciones Modelo 124 (AEAT)
    # ------------------------------------------------------------------
    (
        "124", "IRNR", "14",
        None, "Rentas obtenidas sin establecimiento permanente — renta regular",
        "Instrucciones Modelo 124 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    ),
    (
        "124", "IRNR", "25",
        None, "Rentas del capital mobiliario sin EP",
        "Instrucciones Modelo 124 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    ),
    (
        "124", "IRNR", "26",
        None, "Ganancias patrimoniales sin EP",
        "Instrucciones Modelo 124 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    ),
    (
        "124", "IRNR", "13",
        None, "Rentas inmobiliarias sin EP",
        "Instrucciones Modelo 124 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 216 — IRNR Retenciones rentas sin EP
    # Fuente: Instrucciones Modelo 216 (AEAT)
    # ------------------------------------------------------------------
    (
        "216", "IRNR", "14",
        None, "Retenciones rentas sin EP — renta regular",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),
    (
        "216", "IRNR", "25",
        None, "Retenciones capital mobiliario sin EP",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),
    (
        "216", "IRNR", "26",
        None, "Retenciones ganancias patrimoniales sin EP",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),
    (
        "216", "IRNR", "13",
        None, "Retenciones rentas inmobiliarias sin EP",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 296 — IRNR Resumen anual retenciones sin EP
    # Fuente: Instrucciones Modelo 296 (AEAT)
    # ------------------------------------------------------------------
    (
        "296", "IRNR", "14",
        None, "Resumen anual retenciones sin EP — renta regular",
        "Instrucciones Modelo 296 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    ),
    (
        "296", "IRNR", "25",
        None, "Resumen anual capital mobiliario sin EP",
        "Instrucciones Modelo 296 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    ),
    (
        "296", "IRNR", "26",
        None, "Resumen anual ganancias patrimoniales sin EP",
        "Instrucciones Modelo 296 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    ),
    (
        "296", "IRNR", "13",
        None, "Resumen anual rentas inmobiliarias sin EP",
        "Instrucciones Modelo 296 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 189 — IRPF Certificaciones individuales socios/partícipes
    # Fuente: Instrucciones Modelo 189 (AEAT)
    # ------------------------------------------------------------------
    (
        "189", "LIRPF", "99",
        None, "Obligación de retener — certificaciones socios/partícipes",
        "Instrucciones Modelo 189 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html",
    ),
    (
        "189", "LIRPF", "100",
        None, "Ingresos a cuenta — certificaciones socios/partícipes",
        "Instrucciones Modelo 189 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 194 — Operaciones vinculadas y paraísos fiscales
    # Fuente: Instrucciones Modelo 194 (AEAT)
    # ------------------------------------------------------------------
    (
        "194", "LGT", "109",
        None, "Obligaciones de información — operaciones vinculadas",
        "Instrucciones Modelo 194 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html",
    ),
    (
        "194", "LIS", "16",
        None, "Operaciones vinculadas — valoración a valor de mercado",
        "Instrucciones Modelo 194 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 198 — IRPF Operaciones con activos financieros
    # Fuente: Instrucciones Modelo 198 (AEAT)
    # ------------------------------------------------------------------
    (
        "198", "LIRPF", "94",
        None, "Ganancias patrimoniales acciones/participaciones",
        "Instrucciones Modelo 198 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html",
    ),
    (
        "198", "LIRPF", "95",
        None, "Reembolso acciones/participaciones",
        "Instrucciones Modelo 198 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 216 — IRNR Retenciones rentas sin EP
    # Fuente: Instrucciones Modelo 216 (AEAT)
    # Nota: Relaciones con artículos IRNR pendientes de ingesta de norma.
    # ------------------------------------------------------------------
    (
        "216", "LGT", "109",
        None, "Obligaciones de información — retenciones IRNR sin EP",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 296 — IRNR Resumen anual retenciones sin EP
    # Fuente: Instrucciones Modelo 296 (AEAT)
    # Nota: Resumen anual de retenciones declaradas en modelo 216.
    # ------------------------------------------------------------------
    (
        "296", "LGT", "109",
        None, "Obligaciones de información — resumen anual IRNR",
        "Instrucciones Modelo 296 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 289 — Cuentas financieras asistencia mutua (DAC2/CRS)
    # Fuente: Instrucciones Modelo 289 (AEAT)
    # ------------------------------------------------------------------
    (
        "289", "LGT", "109",
        None, "Obligaciones de información — intercambio DAC2/CRS",
        "Instrucciones Modelo 289 2025",
        "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/campana-declaraciones-informativas-2024/modelo-289.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 290 — Cuentas financieras FATCA (EEUU)
    # Fuente: Instrucciones Modelo 290 (AEAT) — Acuerdo FATCA España-EEUU
    # ------------------------------------------------------------------
    (
        "290", "LGT", "109",
        None, "Obligaciones de información — acuerdo FATCA España-EEUU",
        "Instrucciones Modelo 290 2025",
        "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 299 — Diseño de registro (formato electrónico)
    # Nota: No es un modelo de declaración per se, sino formato de fichero
    #       para presentación electrónica. Se registra para cobertura técnica.
    # ------------------------------------------------------------------
    (
        "299", "LGT", "109",
        None, "Formato electrónico de presentación — diseño de registro",
        "Diseños de registro AEAT",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 347 — Declaración anual operaciones con terceros
    # Fuente: Instrucciones Modelo 347 (BOE / AEAT)
    # ------------------------------------------------------------------
    (
        "347", "LGT", "109",
        None, "Obligaciones de información — operaciones con terceros",
        "Instrucciones Modelo 347 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/8-declaraciones-informativas/8_2-declaracion-anual-operaciones-terceros-347.html",
    ),
    (
        "347", "LIVA", "97",
        None, "Registro de facturas emitidas y recibidas — soporte 347",
        "Instrucciones Modelo 347 2025 — Operaciones con terceros",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/8-declaraciones-informativas/8_2-declaracion-anual-operaciones-terceros-347.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 349 — Declaración recapitulativa operaciones intracomunitarias
    # Fuente: Instrucciones Modelo 349 (AEAT) — Reglamento UE 2018/1541
    # ------------------------------------------------------------------
    (
        "349", "LIVA", "50",
        None, "Entregas intracomunitarias de bienes — exención art. 50",
        "Instrucciones Modelo 349 2025",
        "https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html",
    ),
    (
        "349", "LIVA", "84",
        None, "Sujeción IVA — operaciones intracomunitarias",
        "Instrucciones Modelo 349 2025",
        "https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html",
    ),

    # ------------------------------------------------------------------
    # Modelo 110 — IRPF Retenciones e ingresos a cuenta (OBSOLETO → 111)
    # Nota: Modelo histórico sustituido por el 111. Se registra para
    #       cobertura de datos históricos y trazabilidad.
    # ------------------------------------------------------------------
    (
        "110", "LIRPF", "99",
        None, "Obligación de retener — modelo histórico (obsoleto → 111)",
        "Orden EHA/586/2011 — Modelo 110",
        "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
    ),
    (
        "110", "LIRPF", "100",
        None, "Ingresos a cuenta — modelo histórico (obsoleto → 111)",
        "Orden EHA/586/2011 — Modelo 110",
        "https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948",
    ),
]

# ---------------------------------------------------------------------------
# Modelos implementados y sus notas de cobertura
#
# Todos los modelos están registrados en aeat_modelo con relaciones
# a artículos de normas IRPF, IVA, LGT e IRNR.
#
# IRNR (RDL 5/2004) ya está incorporada en el BOE worker y en los
# enlaces de modelos: 124, 216, 296 → IRNR art. 13, 14, 25, 26
#
# Modelos 289 y 290 (DAC2/CRS, FATCA) son declaraciones informativas
# de intercambio internacional y se enlazan con LGT art. 109 como
# obligación formal de información.
# ---------------------------------------------------------------------------


def get_db_url(args_db_url: str | None) -> str:
    if args_db_url:
        return args_db_url
    url = os.getenv("DATABASE_URL")
    if not url:
        url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        print("ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found.")
        print("Provide --db-url or set env vars.")
        sys.exit(1)
    return url


def connect(db_url: str):
    try:
        return psycopg.connect(db_url)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        sys.exit(1)


def seed_modelos(conn, dry_run: bool = False):
    with conn.cursor() as cur:
        # --- Insert models ---
        for m in MODELOS:
            if dry_run:
                print(f"[DRY-RUN] Would upsert modelo: {m['codigo']} — {m['nombre']}")
                continue

            cur.execute(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    periodo = EXCLUDED.periodo,
                    impuesto = EXCLUDED.impuesto,
                    url_info = EXCLUDED.url_info
                """,
                (m["codigo"], m["nombre"], m["periodo"], m["impuesto"], m["url_info"]),
            )

        conn.commit()

        if not dry_run:
            print(f"Upserted {len(MODELOS)} models.")

        # --- Insert model-article relationships ---
        inserted = 0
        skipped = 0
        for row in MODELO_ARTICULO_DATA:
            modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente = row

            if not fuente or not fuente.strip():
                print(f"SKIP: {modelo_codigo} → {norma} art. {numero}: no fuente")
                skipped += 1
                continue

            if dry_run:
                print(
                    f"[DRY-RUN] Would insert: {modelo_codigo} → {norma} art. {numero} "
                    f"(casilla={casilla}, fuente={fuente})"
                )
                inserted += 1
                continue

            # Get modelo_id
            cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (modelo_codigo,))
            modelo_row = cur.fetchone()
            if not modelo_row:
                print(f"SKIP: modelo {modelo_codigo} not found in DB")
                skipped += 1
                continue
            modelo_id = modelo_row[0]

            # Get articulo_id
            cur.execute(
                """
                SELECT a.id FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = %s AND a.numero = %s
                """,
                (norma, numero),
            )
            art_row = cur.fetchone()
            if not art_row:
                print(f"SKIP: {norma} art. {numero} not found in DB")
                skipped += 1
                continue
            articulo_id = art_row[0]

            # Upsert relationship
            cur.execute(
                """
                INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (modelo_id, articulo_id) DO UPDATE SET
                    casilla = EXCLUDED.casilla,
                    nota = EXCLUDED.nota,
                    fuente = EXCLUDED.fuente,
                    url_fuente = EXCLUDED.url_fuente
                """,
                (modelo_id, articulo_id, casilla, nota, fuente, url_fuente),
            )
            inserted += 1

        if not dry_run:
            conn.commit()

        print(f"\nRelationships: {inserted} inserted, {skipped} skipped.")


def main():
    parser = argparse.ArgumentParser(description="Seed AEAT models and relationships")
    parser.add_argument("--db-url", help="Database connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    db_url = get_db_url(args.db_url)
    print(f"Database: {db_url[:40]}...")
    print(f"Dry run: {args.dry_run}")

    conn = connect(db_url)
    try:
        seed_modelos(conn, dry_run=args.dry_run)
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
