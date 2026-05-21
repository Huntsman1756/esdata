#!/usr/bin/env python3
"""Fase 3 — Evaluador automático y benchmark de retrieval en esdata.

Carga el golden dataset, ejecuta cada pregunta contra los endpoints,
calcula métricas por dominio y exporta JSON + resumen legible.

Uso:
    python scripts/eval/eval_phase3.py                          # SQLite local
    python scripts/eval/eval_phase3.py --base-url http://localhost:8001  # PG remoto
    python scripts/eval/eval_phase3.py --baseline old_results.json  # comparar
    python scripts/eval/eval_phase3.py --summary-only           # solo resumen sin ejecutar
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# ── Paths ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT_DIR / "scripts"
GOLDEN_PATH = SCRIPTS_DIR / "golden_queries.json"
TELEMETRY_FILE = SCRIPTS_DIR / "telemetry" / "eval_failures.jsonl"
OUTPUT_DIR = SCRIPTS_DIR / "eval_results"

# ── Umbrales por dominio (80% minimal, 90% fuerte) ────────────────────

THRESHOLDS = {
    "fuerte": 0.90,
    "aceptable": 0.80,
    "falla": 0.70,
}

DOMAIN_WEIGHTS = {
    "iva": 1.5,
    "irpf_is": 1.3,
    "internacional": 1.2,
    "compliance": 1.0,
    "mixto": 0.8,
}


def _auth_headers() -> dict[str, str]:
    api_key = os.getenv("ESDATA_API_KEY")
    return {"x-api-key": api_key} if api_key else {}


# ── Carga del golden dataset ──────────────────────────────────────────

def load_golden() -> dict:
    if not GOLDEN_PATH.exists():
        print(f"ERROR: golden dataset no encontrado: {GOLDEN_PATH}")
        sys.exit(1)
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Ejecución de queries ──────────────────────────────────────────────

async def run_query_vs_consulta(
    client: httpx.AsyncClient, pregunta: str, params: dict | None = None
) -> dict:
    """Ejecuta contra /v1/consulta y devuelve raw response."""
    try:
        r = await client.get(
            "/v1/consulta",
            params={"q": pregunta, **(params or {})},
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


async def run_query_vs_buscar(
    client: httpx.AsyncClient, pregunta: str, params: dict | None = None
) -> dict:
    """Ejecuta contra /v1/legislacion/buscar."""
    try:
        r = await client.get(
            "/v1/legislacion/buscar",
            params={"q": pregunta, **(params or {})},
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


async def run_query_vs_doctrina(
    client: httpx.AsyncClient, pregunta: str
) -> dict:
    """Ejecuta contra /v1/doctrina/buscar."""
    try:
        r = await client.get(
            "/v1/doctrina/buscar",
            params={"q": pregunta},
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


async def run_query_vs_hybrid(
    client: httpx.AsyncClient,
    pregunta: str,
    buscar_params: dict | None = None,
) -> dict:
    """Ejecuta contra /v1/legislacion/buscar/hybrid con peso 0.5."""
    try:
        params = {"q": pregunta, "hybrid_weight": 0.3}
        if buscar_params:
            params.update(buscar_params)
        r = await client.get(
            "/v1/legislacion/buscar/hybrid",
            params=params,
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


async def run_query_vs_borme(
    client: httpx.AsyncClient, pregunta: str
) -> dict:
    """Ejecuta contra /v1/borme."""
    try:
        r = await client.get(
            "/v1/borme",
            params={"q": pregunta},
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


async def run_query_vs_bdns(
    client: httpx.AsyncClient, pregunta: str
) -> dict:
    """Ejecuta contra /v1/bdns."""
    try:
        r = await client.get(
            "/v1/bdns",
            params={"q": pregunta},
            headers=_auth_headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


# ── Local mode (TestClient) ──────────────────────────────────────────

def run_local_vs_consulta(client, pregunta, params=None):
    """Versión síncrona de run_query_vs_consulta usando TestClient."""
    try:
        r = client.get(
            "/v1/consulta",
            params={"q": pregunta, **(params or {})},
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def run_local_vs_buscar(client, pregunta, params=None):
    """Versión síncrona de run_query_vs_buscar usando TestClient."""
    try:
        r = client.get(
            "/v1/legislacion/buscar",
            params={"q": pregunta, **(params or {})},
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def run_local_vs_doctrina(client, pregunta):
    """Versión síncrona de run_query_vs_doctrina usando TestClient."""
    try:
        r = client.get(
            "/v1/doctrina/buscar",
            params={"q": pregunta},
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def run_local_vs_hybrid(client, pregunta, params=None):
    """Versión síncrona de run_local_vs_hybrid usando TestClient."""
    try:
        base_params = {"q": pregunta, "hybrid_weight": 0.5}
        all_params = {**base_params, **(params or {})}
        r = client.get(
            "/v1/legislacion/buscar/hybrid",
            params=all_params,
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def run_local_vs_borme(client, pregunta):
    """Versión síncrona de run_query_vs_borme usando TestClient."""
    try:
        r = client.get(
            "/v1/borme",
            params={"q": pregunta},
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def run_local_vs_bdns(client, pregunta):
    """Versión síncrona de run_query_vs_bdns usando TestClient."""
    try:
        r = client.get(
            "/v1/bdns",
            params={"q": pregunta},
            headers=_auth_headers(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def evaluate_query_local(client, query):
    """Versión síncrona de evaluate_query usando TestClient."""
    qid = query["id"]
    pregunta = query["pregunta"]
    criterios = query["criterios"]
    dominio = query["dominio"]

    results = {
        "query_id": qid,
        "pregunta": pregunta,
        "dominio": dominio,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
        "metricas": {},
        "falla": False,
    }

    # Ejecutar los 3 endpoints
    start_consulta = time.monotonic()
    consulta_resp = run_local_vs_consulta(client, pregunta)
    results["endpoints"]["consulta"] = {
        "status": "ok" if "_error" not in consulta_resp else "error",
        "latencia_ms": round((time.monotonic() - start_consulta) * 1000, 1),
        "data": consulta_resp,
    }

    # Build extra params from criterios (e.g., norma_filtro)
    buscar_params = {}
    norma_filtro = criterios.get("norma_filtro")
    if norma_filtro:
        buscar_params["norma"] = norma_filtro

    start_buscar = time.monotonic()
    buscar_resp = run_local_vs_buscar(client, pregunta, buscar_params)
    results["endpoints"]["buscar"] = {
        "status": "ok" if "_error" not in buscar_resp else "error",
        "latencia_ms": round((time.monotonic() - start_buscar) * 1000, 1),
        "data": buscar_resp,
    }

    start_doctrina = time.monotonic()
    doctrina_resp = run_local_vs_doctrina(client, pregunta)
    results["endpoints"]["doctrina"] = {
        "status": "ok" if "_error" not in doctrina_resp else "error",
        "latencia_ms": round((time.monotonic() - start_doctrina) * 1000, 1),
        "data": doctrina_resp,
    }

    start_hybrid = time.monotonic()
    hybrid_resp = run_local_vs_hybrid(client, pregunta, buscar_params)
    results["endpoints"]["hybrid"] = {
        "status": "ok" if "_error" not in hybrid_resp else "error",
        "latencia_ms": round((time.monotonic() - start_hybrid) * 1000, 1),
        "data": hybrid_resp,
    }

    # BORME
    start_borme = time.monotonic()
    borme_resp = run_local_vs_borme(client, pregunta)
    results["endpoints"]["borme"] = {
        "status": "ok" if "_error" not in borme_resp else "error",
        "latencia_ms": round((time.monotonic() - start_borme) * 1000, 1),
        "data": borme_resp,
    }

    # BDNS
    start_bdns = time.monotonic()
    bdns_resp = run_local_vs_bdns(client, pregunta)
    results["endpoints"]["bdns"] = {
        "status": "ok" if "_error" not in bdns_resp else "error",
        "latencia_ms": round((time.monotonic() - start_bdns) * 1000, 1),
        "data": bdns_resp,
    }

    # ── Métricas (mismas que evaluate_query) ──────────────────────────

    # Extract sources from both buscar_resp and consulta_resp (consulta has modelos AEAT)
    fuentes_buscar = _extraer_fuentes(buscar_resp)
    fuentes_consulta = _extraer_fuentes(consulta_resp)
    fuentes_encontradas = fuentes_buscar | fuentes_consulta
    fuentes_esperadas = criterios.get("fuente_esperada", [])
    acierto_fuente = False
    if fuentes_esperadas:
        acierto_fuente = any(
            f in fuentes_encontradas for f in fuentes_esperadas
        )
    else:
        acierto_fuente = len(fuentes_encontradas) > 0

    articulos_encontrados = _extraer_articulos(buscar_resp)
    articulo_esperado = criterios.get("articulo_esperado")
    acierto_articulo = False
    if articulo_esperado:
        acierto_articulo = any(
            articulo_esperado in a for a in articulos_encontrados
        )
    else:
        acierto_articulo = len(articulos_encontrados) > 0

    acierto_vigencia = (
        _verificar_vigencia(consulta_resp) if acierto_articulo else None
    )

    chunk_precision = _medir_chunk_precision(
        consulta_resp, articulo_esperado
    )

    recall_top3 = _check_recall_top_n(
        consulta_resp, fuentes_esperadas, 3
    )
    recall_top5 = _check_recall_top_n(
        consulta_resp, fuentes_esperadas, 5
    )

    posicion = _posicion_fuente(consulta_resp, fuentes_esperadas)

    acierto_doctrina = (
        _check_doctrina_present(doctrina_resp)
        if criterios.get("doctrina_esperada")
        else None
    )

    acierto_modelo = (
        _check_modelo_present(consulta_resp, criterios["modelo_esperado"])
        if criterios.get("modelo_esperado")
        else None
    )

    acierto_borme = (
        _check_borme_present(borme_resp)
        if criterios.get("borme_esperado")
        else None
    )

    acierto_bdns = (
        _check_bdns_present(bdns_resp)
        if criterios.get("bdns_esperado")
        else None
    )

    # Edge case: query vacia o ultra-corta
    query_vacia = not pregunta or len(pregunta.strip()) == 0
    query_ultra_corta = len(pregunta.strip()) <= 1 and not query_vacia

    # Score compuesto
    score_compuesto = _calcular_score(
        acierto_fuente, acierto_articulo, acierto_vigencia,
        chunk_precision, recall_top3, recall_top5,
        acierto_doctrina, acierto_modelo,
        acierto_borme, acierto_bdns,
        query_vacia, query_ultra_corta,
    )

    results["metricas"] = {
        "score_compuesto": round(score_compuesto, 4),
        "acierto_fuente": acierto_fuente,
        "fuentes_encontradas": list(fuentes_encontradas),
        "fuentes_esperadas": fuentes_esperadas,
        "acierto_articulo": acierto_articulo,
        "articulos_encontrados": articulos_encontrados,
        "acierto_vigencia": acierto_vigencia,
        "chunk_precision": chunk_precision,
        "recall_top3": recall_top3,
        "recall_top5": recall_top5,
        "posicion_fuente": posicion,
        "acierto_doctrina": acierto_doctrina,
        "acierto_modelo": acierto_modelo,
        "acierto_borme": acierto_borme,
        "acierto_bdns": acierto_bdns,
        "query_vacia": query_vacia,
        "query_ultra_corta": query_ultra_corta,
    }

    results["falla"] = not acierto_fuente

    return results


def _run_local_sync(queries):
    """Ejecuta todas las queries en modo local con TestClient."""
    import sys

    # Use PostgreSQL (not SQLite test DB) to have real seeded data
    pg_url = os.getenv(
        "ESDATA_DB_URL",
        "postgresql://esdata:esdata_dev@localhost:5432/esdata",
    )
    os.environ["DATABASE_URL"] = pg_url

    # Limpiar caches de módulos importados para forzar reimport con nuevo DATABASE_URL
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("main") or mod_name == "db" or mod_name.startswith("routers"):
            del sys.modules[mod_name]

    # Importar app (ahora con DATABASE_URL correcto)
    api_path = ROOT_DIR / "apps" / "api"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)

    results = []
    for q in queries:
        result = evaluate_query_local(client, q)
        results.append(result)

    return results


async def evaluate_query(
    client: httpx.AsyncClient,
    query: dict,
) -> dict:
    """Ejecuta una pregunta del golden dataset y mide todas las métricas."""
    qid = query["id"]
    pregunta = query["pregunta"]
    criterios = query["criterios"]
    dominio = query["dominio"]

    results = {
        "query_id": qid,
        "pregunta": pregunta,
        "dominio": dominio,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
        "metricas": {},
        "falla": False,
    }

    # Ejecutar los 3 endpoints
    start_consulta = time.monotonic()
    consulta_resp = await run_query_vs_consulta(client, pregunta)
    results["endpoints"]["consulta"] = {
        "status": "ok" if "_error" not in consulta_resp else "error",
        "latencia_ms": round((time.monotonic() - start_consulta) * 1000, 1),
        "data": consulta_resp,
    }

    # Build extra params from criterios (e.g., norma_filtro)
    buscar_params = {}
    norma_filtro = criterios.get("norma_filtro")
    if norma_filtro:
        buscar_params["norma"] = norma_filtro

    start_buscar = time.monotonic()
    buscar_resp = await run_query_vs_buscar(client, pregunta, buscar_params)
    results["endpoints"]["buscar"] = {
        "status": "ok" if "_error" not in buscar_resp else "error",
        "latencia_ms": round((time.monotonic() - start_buscar) * 1000, 1),
        "data": buscar_resp,
    }

    start_doctrina = time.monotonic()
    doctrina_resp = await run_query_vs_doctrina(client, pregunta)
    results["endpoints"]["doctrina"] = {
        "status": "ok" if "_error" not in doctrina_resp else "error",
        "latencia_ms": round((time.monotonic() - start_doctrina) * 1000, 1),
        "data": doctrina_resp,
    }

    start_hybrid = time.monotonic()
    hybrid_resp = await run_query_vs_hybrid(client, pregunta, buscar_params)
    results["endpoints"]["hybrid"] = {
        "status": "ok" if "_error" not in hybrid_resp else "error",
        "latencia_ms": round((time.monotonic() - start_hybrid) * 1000, 1),
        "data": hybrid_resp,
    }

    # BORME
    start_borme = time.monotonic()
    borme_resp = await run_query_vs_borme(client, pregunta)
    results["endpoints"]["borme"] = {
        "status": "ok" if "_error" not in borme_resp else "error",
        "latencia_ms": round((time.monotonic() - start_borme) * 1000, 1),
        "data": borme_resp,
    }

    # BDNS
    start_bdns = time.monotonic()
    bdns_resp = await run_query_vs_bdns(client, pregunta)
    results["endpoints"]["bdns"] = {
        "status": "ok" if "_error" not in bdns_resp else "error",
        "latencia_ms": round((time.monotonic() - start_bdns) * 1000, 1),
        "data": bdns_resp,
    }

    # ── Métricas ──────────────────────────────────────────────────────

    # 1. Acierto de fuente (combinar buscar_resp + consulta_resp)
    # buscar_resp devuelve normas de documento_fragmento (puede estar vacío)
    # consulta_resp devuelve modelos[].norma_base ("LIVA art. 71", "LIRNR art. 14")
    fuentes_buscar = _extraer_fuentes(buscar_resp)
    fuentes_consulta = _extraer_fuentes(consulta_resp)
    fuentes_encontradas = fuentes_buscar | fuentes_consulta
    fuentes_esperadas = criterios.get("fuente_esperada", [])
    acierto_fuente = False
    if fuentes_esperadas:
        # Normalizar con aliases (LIRNR <-> IRNR, LIVA <-> IVA, etc.)
        encontrados_norm = {SOURCE_ALIASES.get(f, f) for f in fuentes_encontradas}
        esperadas_norm = {SOURCE_ALIASES.get(f, f) for f in fuentes_esperadas}
        acierto_fuente = bool(encontrados_norm & esperadas_norm)
    else:
        # Si no hay fuente esperada, no penalizamos
        acierto_fuente = True

    # 2. Acierto de artículo
    articulos_encontrados = _extraer_articulos(buscar_resp)
    art_esperado = criterios.get("articulo_esperado")
    acierto_articulo = False
    if art_esperado:
        acierto_articulo = art_esperado in articulos_encontrados
    else:
        acierto_articulo = len(articulos_encontrados) > 0

    # 3. Vigencia correcta
    acierto_vigencia = None
    if criterios.get("vigencia_necesaria"):
        acierto_vigencia = _verificar_vigencia(consulta_resp)

    # 4. Precisión de chunk
    chunk_precision = None
    if criterios.get("chunk_esperado"):
        chunk_precision = _medir_chunk_precision(consulta_resp, art_esperado)

    # 5. Recall: ¿aparece en top-3?
    recall_top3 = _check_recall_top_n(consulta_resp, fuentes_esperadas, n=3)
    recall_top5 = _check_recall_top_n(consulta_resp, fuentes_esperadas, n=5)

    # 6. Ranking de posición
    pos_fuente = _posicion_fuente(consulta_resp, fuentes_esperadas)

    # 7. Doctrina
    acierto_doctrina = None
    if criterios.get("doctrina_esperada"):
        acierto_doctrina = _check_doctrina_present(doctrina_resp)

    # 8. Modelo AEAT esperado
    acierto_modelo = None
    modelo_esperado = criterios.get("modelo_esperado")
    if modelo_esperado:
        acierto_modelo = _check_modelo_present(consulta_resp, modelo_esperado)

    # 9. BORME esperado
    acierto_borme = None
    if criterios.get("borme_esperado"):
        acierto_borme = _check_borme_present(borme_resp)

    # 10. BDNS esperado
    acierto_bdns = None
    if criterios.get("bdns_esperado"):
        acierto_bdns = _check_bdns_present(bdns_resp)

    # Edge case: query vacia o ultra-corta
    query_vacia = not pregunta or len(pregunta.strip()) == 0
    query_ultra_corta = len(pregunta.strip()) <= 1 and not query_vacia

    # Score compuesto ponderado
    score = _calcular_score(
        acierto_fuente=acierto_fuente,
        acierto_articulo=acierto_articulo,
        acierto_vigencia=acierto_vigencia,
        chunk_precision=chunk_precision,
        recall_top3=recall_top3,
        recall_top5=recall_top5,
        acierto_doctrina=acierto_doctrina,
        acierto_modelo=acierto_modelo,
        acierto_borme=acierto_borme,
        acierto_bdns=acierto_bdns,
        query_vacia=query_vacia,
        query_ultra_corta=query_ultra_corta,
    )

    results["metricas"] = {
        "acierto_fuente": acierto_fuente,
        "fuentes_encontradas": list(fuentes_encontradas),
        "fuentes_esperadas": fuentes_esperadas,
        "acierto_articulo": acierto_articulo,
        "articulos_encontrados": articulos_encontrados,
        "acierto_vigencia": acierto_vigencia,
        "chunk_precision": chunk_precision,
        "recall_top3": recall_top3,
        "recall_top5": recall_top5,
        "posicion_fuente": pos_fuente,
        "acierto_doctrina": acierto_doctrina,
        "acierto_modelo": acierto_modelo,
        "score_compuesto": round(score, 4),
    }

    results["falla"] = not acierto_fuente

    return results


# ── Helpers de extracción ─────────────────────────────────────────────

# Allowlist de prefixes de fuentes reconocidas por el sistema.
# Se usan para filtrar matches del regex y evitar falsos positivos.
KNOWN_SOURCE_PREFIXES = frozenset({
    "LIVA", "LIRPF", "LIRNR", "LIS", "LGT", "ITPAJD", "IRNR", "IIEE", "HL",
    "DAC6", "DAC6RD", "DAC6EU", "RIRPF", "RIVA", "RIS", "RD1080",
    "LIVA_IGIC", "SEPBLAC", "CNMV",
})

# Aliases para normalizar nombres de fuentes (ley vs acronimo)
# Ej: "LIRPF" (Ley IRPF) y "IRPF" son la misma fuente
SOURCE_ALIASES = {
    "LIRPF": "IRPF",
    "LIRNR": "IRNR",
    "LIVA": "IVA",
    "LIS": "IS",
    "LGT": "LGT",
    "ITPAJD": "ITPAJD",
    "RIRPF": "IRPF",
    "RIVA": "IVA",
    "RIS": "IS",
}


def _extraer_fuentes(resp: dict) -> set[str]:
    """Extraer lista de fuentes/normas de los resultados.
    
    Soporta ambos formatos:
    - /v1/legislacion/buscar: {resultados: [{norma, codigo, ...}]}
    - /v1/consulta: {modelos: [{codigo, ...}], normativa: [{norma, ...}]}
    
    Prioridad: modelos[].norma_base (ej: "LIVA art. 71" -> "LIVA")
    Filtrado con allowlist de prefixes conocidos para evitar falsos positivos.
    """
    fuentes = set()
    if "_error" in resp:
        return fuentes
    
    # Formato /v1/consulta: extraer de modelos[].norma_base
    # Regex busca tokens mayusculas (ej: "LIRNR art. 14" -> "LIRNR")
    # Filtrado con allowlist para evitar matches como "ART", "RD", etc.
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
                token = match.group()
                if token in KNOWN_SOURCE_PREFIXES:
                    fuentes.add(token)
        # Detectar fuentes por codigo de modelo AEAT (SEPBLAC, CNMV, etc.)
        # Solo codigos alfanumericos que esten en la allowlist
        codigo = m.get("codigo", "")
        if codigo and codigo in KNOWN_SOURCE_PREFIXES:
            fuentes.add(codigo)
    
    # Formato /v1/legislacion/buscar
    for r in resp.get("resultados", []):
        if r.get("norma"):
            fuentes.add(r["norma"])
        if r.get("fuente"):
            fuentes.add(r["fuente"])
    
    # Formato /v1/consulta: fallback a normativa[].norma
    for n in resp.get("normativa", []):
        if n.get("norma"):
            fuentes.add(n["norma"])
    
    return fuentes


def _extraer_articulos(resp: dict) -> list[str]:
    """Extraer lista de articulos encontrados.
    
    Soporta ambos formatos:
    - /v1/legislacion/buscar: resultados[].articulo, resultados[].numero
    - /v1/consulta: normativa[].articulo, modelos[].norma_base (ej: "LIVA art. 71" -> "71")
    """
    import re
    articulos = []
    if "_error" in resp:
        return articulos
    
    # Formato /v1/legislacion/buscar
    for r in resp.get("resultados", []):
        if r.get("articulo"):
            articulos.append(str(r["articulo"]))
        if r.get("numero"):
            articulos.append(str(r["numero"]))
    
    # Formato /v1/consulta: extraer de modelos[].norma_base (ej: "LIVA art. 71" -> "71")
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            match = re.search(r'art\.\s*(\d+)', norma_base, re.IGNORECASE)
            if match:
                articulos.append(match.group(1))
    
    # Formato /v1/consulta: normativa[].articulo
    for n in resp.get("normativa", []):
        if n.get("articulo"):
            articulos.append(str(n["articulo"]))
        if n.get("numero"):
            articulos.append(str(n["numero"]))
    
    return articulos


def _verificar_vigencia(resp: dict) -> bool:
    """Verificar que los resultados tienen vigencia correcta."""
    if "_error" in resp:
        return False

    # Formato /v1/legislacion/buscar
    for r in resp.get("resultados", []):
        vd = r.get("vigente_desde")
        if vd is not None:
            return True

    # Formato /v1/consulta: normativa[].vigente_desde
    for n in resp.get("normativa", []):
        if n.get("vigente_desde") is not None:
            return True

    return False


def _medir_chunk_precision(
    resp: dict, art_esperado: str | None
) -> float:
    """Medir % de resultados que son chunked vs plain text."""
    if "_error" in resp:
        return 0.0
    
    # Formato /v1/legislacion/buscar
    resultados = resp.get("resultados", [])
    # Formato /v1/consulta
    resultados += resp.get("normativa", [])
    
    if not resultados:
        return 0.0
    
    chunks_count = 0
    for r in resultados:
        if r.get("articulo") and str(r["articulo"]) == art_esperado:
            if r.get("chunk_id") or r.get("chunk_type"):
                chunks_count += 1
    return round(chunks_count / len(resultados), 4) if resultados else 0.0


def _get_all_items(resp: dict) -> list[dict]:
    """Unifica todos los items de respuesta en una sola lista."""
    items = []
    if "_error" in resp:
        return items
    
    items.extend(resp.get("resultados", []))
    items.extend(resp.get("normativa", []))
    items.extend(resp.get("modelos", []))
    items.extend(resp.get("obligacion", []))
    
    return items


def _check_recall_top_n(
    resp: dict, fuentes_esperadas: list[str], n: int
) -> bool:
    """Verificar si alguna fuente esperada est en top-n."""
    if "_error" in resp or not fuentes_esperadas:
        return False
    items = _get_all_items(resp)[:n]
    fuentes_set = set(fuentes_esperadas)
    for item in items:
        norma = item.get("norma", "") or item.get("codigo", "")
        if norma in fuentes_set:
            return True
        # Tambien chequear norma_base con regex (puede contener "LIVA art. 71")
        norma_base = item.get("norma_base", "") or ""
        for token in re.findall(r'[A-Z][A-Z0-9]*', norma_base):
            if token in fuentes_set:
                return True
    return False


def _posicion_fuente(
    resp: dict, fuentes_esperadas: list[str]
) -> int | None:
    """Posicion 1-based de la primera fuente esperada, o None si no est."""
    if "_error" in resp or not fuentes_esperadas:
        return None
    fuentes_set = set(fuentes_esperadas)
    for i, item in enumerate(_get_all_items(resp), 1):
        norma = item.get("norma", "") or item.get("codigo", "")
        if norma in fuentes_set:
            return i
        norma_base = item.get("norma_base", "") or ""
        for token in re.findall(r'[A-Z][A-Z0-9]*', norma_base):
            if token in fuentes_set:
                return i
    return None


def _check_doctrina_present(resp: dict) -> bool:
    """Verificar si hay resultados de doctrina."""
    if "_error" in resp:
        return False
    return len(resp.get("resultados", [])) > 0


def _check_modelo_present(resp: dict, modelo_codigo: str) -> bool:
    """Verificar si un modelo AEAT aparece en la respuesta."""
    if "_error" in resp:
        return False
    for m in resp.get("modelos", []):
        if isinstance(m, dict) and m.get("codigo") == modelo_codigo:
            return True
        if str(m) == modelo_codigo:
            return True
    return False


def _check_borme_present(resp: dict) -> bool:
    """Verificar si hay resultados de BORME."""
    if "_error" in resp:
        return False
    return len(resp.get("actos", [])) > 0


def _check_bdns_present(resp: dict) -> bool:
    """Verificar si hay resultados de BDNS."""
    if "_error" in resp:
        return False
    return len(resp.get("convocatorias", [])) > 0


def _calcular_score(
    acierto_fuente: bool,
    acierto_articulo: bool,
    acierto_vigencia: bool | None,
    chunk_precision: float | None,
    recall_top3: bool,
    recall_top5: bool,
    acierto_doctrina: bool | None,
    acierto_modelo: bool | None,
    acierto_borme: bool | None = None,
    acierto_bdns: bool | None = None,
    query_vacia: bool = False,
    query_ultra_corta: bool = False,
) -> float:
    """Score compuesto 0-1 ponderado por importancia."""
    weights = {
        "fuente": 0.30,
        "articulo": 0.15,
        "vigencia": 0.10,
        "chunk": 0.10,
        "recall_top3": 0.15,
        "recall_top5": 0.10,
        "doctrina": 0.10,
        "modelo": 0.10,
        "borme": 0.0,
        "bdns": 0.0,
    }

    values = {
        "fuente": 1.0 if acierto_fuente else 0.0,
        "articulo": 1.0 if acierto_articulo else 0.0,
        "vigencia": 1.0 if acierto_vigencia else (0.0 if acierto_vigencia is not None else 1.0),
        "chunk": chunk_precision if chunk_precision is not None else 1.0,
        "recall_top3": 1.0 if recall_top3 else 0.0,
        "recall_top5": 1.0 if recall_top5 else 0.0,
        "doctrina": 1.0 if acierto_doctrina else (0.0 if acierto_doctrina is not None else 1.0),
        "modelo": 1.0 if acierto_modelo else (0.0 if acierto_modelo is not None else 1.0),
        "borme": 1.0 if acierto_borme else (0.0 if acierto_borme is not None else 1.0),
        "bdns": 1.0 if acierto_bdns else (0.0 if acierto_bdns is not None else 1.0),
    }

    total = sum(weights[k] * values[k] for k in weights)

    # Penalizacion edge cases: query vacia o ultra-corta no debe fallar
    if query_vacia or query_ultra_corta:
        # Solo contar fuente + articulo para edge cases
        weights["fuente"] = 0.5
        weights["articulo"] = 0.5
        total = sum(weights[k] * values[k] for k in weights)
        # Si no hay error 500, dar score minimo 0.5
        if not (acierto_fuente is False and acierto_articulo is False):
            return max(0.5, total)

    return total


# ── Telemetría ────────────────────────────────────────────────────────

def save_telemetry(results: dict) -> None:
    """Guardar fallos en JSONL local para iteración."""
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not results.get("falla"):
        return

    entry = {
        "telemetry_id": str(uuid.uuid4()),
        "timestamp": results["timestamp"],
        "query_id": results["query_id"],
        "dominio": results["dominio"],
        "pregunta": results["pregunta"],
        "score": results["metricas"]["score_compuesto"],
        "acierto_fuente": results["metricas"]["acierto_fuente"],
        "fuentes_encontradas": results["metricas"]["fuentes_encontradas"],
        "fuentes_esperadas": results["metricas"]["fuentes_esperadas"],
        "latencia_consulta_ms": results["endpoints"]["consulta"]["latencia_ms"],
        "latencia_buscar_ms": results["endpoints"]["buscar"]["latencia_ms"],
        "latencia_doctrina_ms": results["endpoints"]["doctrina"]["latencia_ms"],
    }

    with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Telemetría persistente Postgres ──────────────────────────────────

def persist_eval_to_db(
    metrics: dict,
    all_results: list[dict],
    api_url: str,
    golden_version: str,
) -> None:
    """Persistir resultados de evaluacion en tabla eval_history de Postgres."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("  [skip] psycopg2 no instalado, persistencia Postgres omitida")
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("  [skip] DATABASE_URL no definido, persistencia Postgres omitida")
        return

    run_id = uuid.uuid4()
    total = metrics.get("total_queries", 0)
    failures = metrics.get("total_failures", 0)
    global_score = metrics.get("global_score", 0.0)
    source_rate = metrics.get("fuente_tasa_global", 0.0)

    # Calcular latencia promedio
    latencias = []
    for r in all_results:
        lat = r.get("endpoints", {}).get("consulta", {}).get("latencia_ms")
        if lat is not None:
            latencias.append(lat)
    avg_latency = round(sum(latencias) / len(latencias), 1) if latencias else None

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Insert eval_run
        cur.execute(
            """
            INSERT INTO eval_run (id, api_url, golden_version, global_score,
                                  total_queries, total_failures, source_hit_rate,
                                  avg_latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (run_id, api_url, golden_version, global_score,
             total, failures, source_rate, avg_latency),
        )

        # Insert eval_query
        for r in all_results:
            fuentes_encontradas = json.dumps(r.get("metricas", {}).get("fuentes_encontradas", []))
            fuentes_esperadas = json.dumps(r.get("metricas", {}).get("fuentes_esperadas", []))
            articulos_encontrados = json.dumps(r.get("metricas", {}).get("articulos_encontrados", []))

            cur.execute(
                """
                INSERT INTO eval_query (
                    run_id, query_id, dominio, pregunta,
                    score_compuesto, acierto_fuente, acierto_articulo,
                    acierto_vigencia, chunk_precision, recall_top3, recall_top5,
                    posicion_fuente, acierto_doctrina, acierto_modelo, falla,
                    latencia_consulta_ms, latencia_buscar_ms, latencia_doctrina_ms,
                    fuentes_encontradas, fuentes_esperadas, articulos_encontrados
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    r.get("query_id"),
                    r.get("dominio"),
                    r.get("pregunta"),
                    r.get("metricas", {}).get("score_compuesto"),
                    r.get("metricas", {}).get("acierto_fuente"),
                    r.get("metricas", {}).get("acierto_articulo"),
                    r.get("metricas", {}).get("acierto_vigencia"),
                    r.get("metricas", {}).get("chunk_precision"),
                    r.get("metricas", {}).get("recall_top3"),
                    r.get("metricas", {}).get("recall_top5"),
                    r.get("metricas", {}).get("posicion_fuente"),
                    r.get("metricas", {}).get("acierto_doctrina"),
                    r.get("metricas", {}).get("acierto_modelo"),
                    r.get("falla", False),
                    r.get("endpoints", {}).get("consulta", {}).get("latencia_ms"),
                    r.get("endpoints", {}).get("buscar", {}).get("latencia_ms"),
                    r.get("endpoints", {}).get("doctrina", {}).get("latencia_ms"),
                    fuentes_encontradas,
                    fuentes_esperadas,
                    articulos_encontrados,
                ),
            )

        conn.commit()
        cur.close()
        conn.close()
        print(f"  [persisted] eval_run {run_id} -> eval_history ({total} queries)")
    except Exception as e:
        print(f"  [error] persistencia Postgres: {e}")


# ── Aggregate metrics ────────────────────────────────────────────────

def aggregate_metrics(
    all_results: list[dict],
) -> dict[str, Any]:
    """Calcular métricas agregadas por dominio y globales."""
    by_dominio: dict[str, list[dict]] = {}
    for r in all_results:
        by_dominio.setdefault(r["dominio"], []).append(r)

    global_metrics: dict[str, Any] = {
        "total_queries": len(all_results),
        "total_failures": sum(1 for r in all_results if r["falla"]),
        "global_score": 0.0,
        "dominios": {},
    }

    weights = []
    scores = []
    for dominio, results in by_dominio.items():
        n = len(results)
        aciertos_fuente = sum(1 for r in results if r["metricas"]["acierto_fuente"])
        aciertos_articulo = sum(
            1 for r in results if r["metricas"]["acierto_articulo"]
        )
        aciertos_vigencia = sum(
            1 for r in results if r["metricas"]["acierto_vigencia"] is True
        )
        avg_chunk = (
            sum(r["metricas"]["chunk_precision"] for r in results) / n
            if all(r["metricas"]["chunk_precision"] is not None for r in results)
            else None
        )
        recall_top3 = sum(1 for r in results if r["metricas"]["recall_top3"]) / n
        recall_top5 = sum(1 for r in results if r["metricas"]["recall_top5"]) / n
        avg_score = sum(r["metricas"]["score_compuesto"] for r in results) / n
        avg_pos = (
            sum(
                r["metricas"]["posicion_fuente"] or 999
                for r in results
                if r["metricas"]["posicion_fuente"] is not None
            )
            / sum(
                1
                for r in results
                if r["metricas"]["posicion_fuente"] is not None
            )
            if any(r["metricas"]["posicion_fuente"] is not None for r in results)
            else None
        )
        avg_latencia = (
            sum(r["endpoints"]["consulta"]["latencia_ms"] for r in results) / n
        )

        dominio_metrics = {
            "n": n,
            "fuente_aciertos": aciertos_fuente,
            "fuente_tasa": round(aciertos_fuente / n, 4),
            "articulo_aciertos": aciertos_articulo,
            "articulo_tasa": round(aciertos_articulo / n, 4),
            "vigencia_aciertos": aciertos_vigencia,
            "vigencia_tasa": round(aciertos_vigencia / n, 4) if n > 0 else None,
            "chunk_precision_avg": round(avg_chunk, 4) if avg_chunk is not None else None,
            "recall_top3": round(recall_top3, 4),
            "recall_top5": round(recall_top5, 4),
            "posicion_media": round(avg_pos, 2) if avg_pos is not None else None,
            "score_promedio": round(avg_score, 4),
            "latencia_promedio_ms": round(avg_latencia, 1),
            "fallas": sum(1 for r in results if r["falla"]),
        }

        # Status según umbral
        tasa = dominio_metrics["fuente_tasa"]
        if tasa >= THRESHOLDS["fuerte"]:
            dominio_metrics["status"] = "fuerte"
        elif tasa >= THRESHOLDS["aceptable"]:
            dominio_metrics["status"] = "aceptable"
        else:
            dominio_metrics["status"] = "falla"

        global_metrics["dominios"][dominio] = dominio_metrics

        w = DOMAIN_WEIGHTS.get(dominio, 1.0)
        weights.append(w)
        scores.append(avg_score)

    # Global weighted
    if weights:
        global_metrics["global_score"] = round(
            sum(w * s for w, s in zip(weights, scores)) / sum(weights), 4
        )
        global_metrics["global_tasa_fuente"] = round(
            sum(
                m["fuente_tasa"] * DOMAIN_WEIGHTS.get(d, 1.0)
                for d, m in global_metrics["dominios"].items()
            )
            / sum(DOMAIN_WEIGHTS.get(d, 1.0) for d in global_metrics["dominios"]),
            4,
        )

    return global_metrics


# ── Resumen legible ───────────────────────────────────────────────────

def print_summary(metrics: dict) -> None:
    """Imprimir resumen legible por consola."""
    print("\n" + "=" * 70)
    print("  FASE 3 — BENCHMARK DE RETRIEVAL")
    print("=" * 70)

    n = metrics["total_queries"]
    f = metrics["total_failures"]
    score = metrics["global_score"]
    tasa = metrics["global_tasa_fuente"]

    print(f"\n  Total queries: {n}  |  Fallos: {f}  |  Score: {score}")
    print(f"  Tasa de acierto fuente (ponderada): {tasa:.1%}")

    if score >= THRESHOLDS["fuerte"]:
        print(f"  Status: {'FUERTE'} (>= {THRESHOLDS['fuerte']:.0%})")
    elif score >= THRESHOLDS["aceptable"]:
        print(f"  Status: {'ACEPTABLE'} (>= {THRESHOLDS['aceptable']:.0%})")
    else:
        print(f"  Status: {'FALLA'} (< {THRESHOLDS['aceptable']:.0%})")

    print("\n  ---- Por dominio --------------------------------")
    for dominio, m in sorted(metrics["dominios"].items()):
        status_icon = {
            "fuerte": "OK",
            "aceptable": "WARN",
            "falla": "FAIL",
        }.get(m["status"], "??")
        vig_str = f"{m['vigencia_tasa']:.1%}" if m['vigencia_tasa'] is not None else 'N/A'
        chunk_str = f"{m['chunk_precision_avg']:.2f}" if m['chunk_precision_avg'] is not None else 'N/A'
        print(
            f"  [{status_icon}] {dominio:15s}  n={m['n']:2d}  "
            f"fuente={m['fuente_tasa']:.1%}  "
            f"art={m['articulo_tasa']:.1%}  "
            f"vig={vig_str:>5s}  "
            f"chunk={chunk_str:>5s}  "
            f"r3={m['recall_top3']:.1%}  "
            f"r5={m['recall_top5']:.1%}  "
            f"score={m['score_promedio']:.3f}  "
            f"lat={m['latencia_promedio_ms']:.0f}ms"
        )

    print("\n" + "=" * 70)


# ── Comparación con baseline ──────────────────────────────────────────

def load_baseline(path: str) -> dict:
    """Cargar resultados previos para comparar."""
    p = Path(path)
    if not p.exists():
        print(f"ERROR: baseline no encontrado: {path}")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def compare_with_baseline(
    current: dict, baseline: dict
) -> dict:
    """Comparar métricas actuales vs baseline."""
    baseline_score = baseline.get("global_score", 0)
    current_score = current["global_score"]
    delta = round(current_score - baseline_score, 4)

    print(f"\n  Baseline score: {baseline_score:.4f}")
    print(f"  Current score:  {current_score:.4f}")
    print(f"  Delta:          {'+' if delta >= 0 else ''}{delta:.4f}")

    improvement = delta > 0
    if improvement:
        print(f"  Resultado: {'MEJORA'} ({delta:.1%} absoluto)")
    elif delta < 0:
        print(f"  Resultado: REGRESION ({delta:.1%} absoluto)")
    else:
        print("  Resultado: SIN CAMBIOS")

    # Por dominio
    try:
        print("\n  ── Delta por dominio ────────────────────────────────────")
    except UnicodeEncodeError:
        print("\n  -- Delta por dominio -----------------------------------")
    bl_domains = baseline.get("dominios", {})
    for dominio, cm in current["dominios"].items():
        bm = bl_domains.get(dominio, {})
        if not bm:
            continue
        d_score = round(cm["score_promedio"] - bm.get("score_promedio", 0), 4)
        d_fuente = round(cm["fuente_tasa"] - bm.get("fuente_tasa", 0), 4)
        arrow = "+" if d_score > 0 else "-" if d_score < 0 else "="
        print(
            f"  {dominio:15s}  score {arrow}{d_score:+.4f}  "
            f"fuente {arrow}{d_fuente:+.4f}"
        )

    return {
        "baseline_score": baseline_score,
        "current_score": current_score,
        "delta": delta,
        "improvement": improvement,
    }


# ── Quality Gate ──────────────────────────────────────────────────────

def check_quality_gate(metrics: dict) -> dict:
    """Verificar si el sistema pasa el gate de calidad.

    Reglas:
    - Global score >= 0.80 (aceptable)
    - Cada dominio con >= 3 queries debe tener fuente_tasa >= 0.70 (falla)
    - Ningun dominio critico (iva, irpf_is, internacional) por debajo de 0.80

    Returns:
        dict con passed (bool), violations (list), warnings (list)
    """
    result = {
        "passed": True,
        "violations": [],
        "warnings": [],
    }

    # 1. Global score >= 0.80
    if metrics["global_score"] < THRESHOLDS["aceptable"]:
        result["passed"] = False
        result["violations"].append(
            f"Global score {metrics['global_score']:.4f} < {THRESHOLDS['aceptable']:.4f}"
        )

    # 2. Dominios criticos >= 0.80
    CRITICAL_DOMAINS = {"iva", "irpf_is", "internacional"}
    for dominio, dm in metrics["dominios"].items():
        score = dm["score_promedio"]
        tasa = dm["fuente_tasa"]
        n = dm["n"]

        # Dominios criticos
        if dominio in CRITICAL_DOMAINS:
            if tasa < THRESHOLDS["aceptable"]:
                result["passed"] = False
                result["violations"].append(
                    f"Dominio critico '{dominio}' fuente_tasa {tasa:.4f} < {THRESHOLDS['aceptable']:.4f}"
                )
            if score < 0.75:
                result["warnings"].append(
                    f"Dominio critico '{dominio}' score bajo {score:.4f}"
                )

        # Dominios con suficiente coverage
        if n >= 3:
            if tasa < THRESHOLDS["falla"]:
                result["passed"] = False
                result["violations"].append(
                    f"Dominio '{dominio}' fuente_tasa {tasa:.4f} < {THRESHOLDS['falla']:.4f}"
                )
            elif tasa < THRESHOLDS["aceptable"]:
                result["warnings"].append(
                    f"Dominio '{dominio}' fuente_tasa {tasa:.4f} < {THRESHOLDS['aceptable']:.4f}"
                )

    return result


def print_quality_gate(gate: dict) -> None:
    """Imprimir resultado del gate de calidad."""
    print("\n" + "=" * 70)
    print("  GATE DE CALIDAD")
    print("=" * 70)

    if gate["passed"]:
        print("\n  Status: APROBADO")
    else:
        print("\n  Status: RECHAZADO")

    if gate["violations"]:
        print("\n  Violaciones:")
        for v in gate["violations"]:
            print(f"    [x] {v}")

    if gate["warnings"]:
        print("\n  Advertencias:")
        for w in gate["warnings"]:
            print(f"    ! {w}")

    if not gate["violations"] and not gate["warnings"]:
        print("\n  Sin issues detectados.")


# ── Main ──────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    """Punto de entrada principal."""
    golden = load_golden()
    queries = golden["queries"]
    print(f"Golden dataset: {len(queries)} queries cargadas")
    if args.summary_only:
        domains = sorted({query["dominio"] for query in queries})
        print("Modo summary-only: no se ejecutan queries ni quality gate.")
        print(f"Dominios cubiertos: {len(domains)}")
        return

    # Determinar base URL
    base_url = args.base_url or os.getenv(
        "ESDATA_API_URL", "http://localhost:8000"
    )
    print(f"API URL: {base_url}")

    # Ejecutar queries
    if args.local:
        print("\nModo local: usando TestClient in-process (SQLite de tests)")
        all_results = _run_local_sync(queries)
    else:
        # Determinar base URL
        base_url = args.base_url or os.getenv(
            "ESDATA_API_URL", "http://localhost:8000"
        )
        print(f"API URL: {base_url}")

        # Conectar con retry automático (httpx transport retries)
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=60.0,
            http2=False,
            transport=transport,
        ) as client:
            # Health check
            try:
                r = await client.get("/status", headers=_auth_headers())
                r.raise_for_status()
                print(f"API conectada: {r.json().get('version', '?')}")
            except Exception as e:
                print(f"ERROR: no se puede conectar a la API: {e}")
                print("Usa --local para modo in-process o --base-url para otro endpoint.")
                sys.exit(1)

            # Ejecutar queries en paralelo con concurrencia controlada
            # 70 queries x 6 endpoints = 420 llamadas API
            # Concurrency=3 reduce tiempo y evita sobrecarga
            CONCURRENCY = 3
            semaphore = asyncio.Semaphore(CONCURRENCY)
            
            async def _eval_with_semaphore(q, idx, total):
                async with semaphore:
                    print(f"  [{idx}/{total}] {q['id']}: {q['pregunta'][:60]}...")
                    result = await evaluate_query(client, q)
                    save_telemetry(result)
                    status_icon = "[OK]" if not result["falla"] else "[FAIL]"
                    print(
                        f"    {status_icon} score={result['metricas']['score_compuesto']:.3f}  "
                        f"fuente={'OK' if result['metricas']['acierto_fuente'] else 'FAIL'}"
                    )
                    return result
            
            tasks = [_eval_with_semaphore(q, i, len(queries)) for i, q in enumerate(queries, 1)]
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results = [
                {"query_id": queries[i]["id"], "falla": True, "endpoints": {}, "metricas": {"score_compuesto": 0, "acierto_fuente": False, "fuentes_encontradas": [], "fuentes_esperadas": []}, "dominio": queries[i]["dominio"], "_error": str(r)} if isinstance(r, Exception) else r
                for i, r in enumerate(all_results)
            ]

    # Agregar métricas
    metrics = aggregate_metrics(all_results)

    # Persistir a Postgres si DATABASE_URL apunta a PostgreSQL
    if not args.local:
        print("\nPersistiendo a eval_history...")
        persist_eval_to_db(metrics, all_results, base_url, golden.get("metadata", {}).get("version", "unknown"))

    # Comparar con baseline si existe
    comparison = None
    if args.baseline:
        baseline = load_baseline(args.baseline)
        comparison = compare_with_baseline(metrics, baseline)

    # Imprimir resumen
    print_summary(metrics)

    # Guardar resultados
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"eval_{ts}.json"

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_url": base_url,
        "golden_version": golden.get("metadata", {}).get("version", "unknown"),
        "metrics": metrics,
        "results": all_results,
    }
    if comparison:
        output["comparison"] = comparison

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nResultados guardados: {output_file}")

    # Telemetry summary
    if TELEMETRY_FILE.exists():
        n_failures = sum(1 for line in TELEMETRY_FILE.read_text().strip().split("\n") if line)
        print(f"Telemetría de fallos: {TELEMETRY_FILE} ({n_failures} entradas)")

    # Quality gate
    gate = check_quality_gate(metrics)
    print_quality_gate(gate)

    # Exit code: falla si gate no pasa o global < 0.80
    if not gate["passed"] or metrics["global_score"] < THRESHOLDS["aceptable"]:
        print(f"\n[WARN] Gate de calidad NO superado: score={metrics['global_score']:.4f}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fase 3 — Evaluador y benchmark de retrieval esdata"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="URL base de la API (default: localhost:8000)",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Archivo JSON de baseline para comparar",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Solo imprimir resumen sin ejecutar queries",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Usar TestClient in-process (no requiere servidor HTTP)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import asyncio
    asyncio.run(main(args))
