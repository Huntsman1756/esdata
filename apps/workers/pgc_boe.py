#!/usr/bin/env python
"""Ingest PGC data from the official BOE text."""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from runtime import configure_logging, ensure_database_connection, get_database_url
from sqlalchemy import create_engine, text


logger = configure_logging("worker-pgc-boe")

PGC_BOE_ID = "BOE-A-2007-19884"
PGC_BOE_URL = f"https://www.boe.es/buscar/doc.php?id={PGC_BOE_ID}"
PGC_ACT_URL = f"https://www.boe.es/buscar/act.php?id={PGC_BOE_ID}"
DATABASE_URL = get_database_url()


def fetch_boe_text(url: str = PGC_BOE_URL) -> str:
    response = httpx.get(url, timeout=60.0, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text("\n", strip=True)


def _section(text_value: str, start: str, end: str | None = None) -> str:
    start_idx = text_value.find(start)
    if start_idx < 0:
        return ""
    end_idx = text_value.find(end, start_idx + len(start)) if end else -1
    return text_value[start_idx:] if end_idx < 0 else text_value[start_idx:end_idx]


def parse_pgc_accounts(text_value: str) -> list[dict]:
    section = _section(text_value, "CUARTA PARTE\nCUADRO DE CUENTAS", "QUINTA PARTE")
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    accounts: list[dict] = []
    seen: set[str] = set()

    for idx, line in enumerate(lines[:-1]):
        match = re.fullmatch(r"(\d{1,4})\.", line)
        if not match:
            continue
        code = match.group(1)
        description = lines[idx + 1].strip()
        if not description or re.fullmatch(r"\d{1,4}\.", description):
            continue
        if code in seen:
            continue
        seen.add(code)
        accounts.append(
            {
                "codigo": code,
                "descripcion": description[:500],
                "nivel": len(code),
                "padre_codigo": None,
                "grupo": code[:2] if len(code) >= 2 else code,
                "clase": code[:1],
                "saldo_normal": None,
                "tipo_cuenta": {1: "grupo", 2: "subgrupo", 3: "cuenta", 4: "subcuenta"}.get(len(code), "cuenta"),
                "nota": f"Fuente BOE oficial {PGC_BOE_ID}: cuarta parte, cuadro de cuentas. {PGC_ACT_URL}",
            }
        )

    codes = {item["codigo"] for item in accounts}
    for item in accounts:
        prefixes = [item["codigo"][:length] for length in range(len(item["codigo"]) - 1, 0, -1)]
        item["padre_codigo"] = next((prefix for prefix in prefixes if prefix in codes), None)
    return accounts


def parse_pgc_marco(text_value: str) -> list[dict]:
    parts = [
        ("PGC_RD_1514_2007", "Real Decreto 1514/2007", "real_decreto"),
        ("PGC_PARTE_1", "Primera parte. Marco conceptual de la contabilidad", "marco_conceptual"),
        ("PGC_PARTE_2", "Segunda parte. Normas de registro y valoración", "normas_registro_valoracion"),
        ("PGC_PARTE_3", "Tercera parte. Cuentas anuales", "cuentas_anuales"),
        ("PGC_PARTE_4", "Cuarta parte. Cuadro de cuentas", "cuadro_cuentas"),
        ("PGC_PARTE_5", "Quinta parte. Definiciones y relaciones contables", "definiciones"),
    ]
    return [
        {
            "codigo": code,
            "titulo": title,
            "tipo": kind,
            "anio": 2007,
            "texto": f"Fuente BOE oficial {PGC_BOE_ID}. {title}.",
            "url_boe": PGC_ACT_URL,
        }
        for code, title, kind in parts
        if title.upper().split(".")[0] in text_value.upper() or code == "PGC_RD_1514_2007"
    ]


def parse_pgc_normas(text_value: str) -> list[dict]:
    section = _section(text_value, "SEGUNDA PARTE", "TERCERA PARTE")
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    normas = []
    seen = set()
    for idx, line in enumerate(lines):
        match = re.match(r"^(\d+)\.\s*ª\s*(.*)$", line)
        if match:
            title = match.group(2).strip() or (lines[idx + 1] if idx + 1 < len(lines) else "")
            norma_ref = f"NRV{match.group(1)}"
            if norma_ref not in seen:
                seen.add(norma_ref)
                normas.append(
                    {
                        "norma_ref": norma_ref,
                        "articulo": line,
                        "descripcion": f"{title}. Fuente BOE oficial {PGC_BOE_ID}.",
                    }
                )
    return normas


def default_financial_statement_rows() -> list[dict]:
    return [
        {
            "estado": "balance",
            "tipo_presentacion": "normal",
            "orden": 1,
            "periodo": "anual",
            "nota_pieds": f"Modelo oficial de balance incluido en la tercera parte del PGC. Fuente BOE {PGC_BOE_ID}. {PGC_ACT_URL}",
        },
        {
            "estado": "cuenta_perdidas_ganancias",
            "tipo_presentacion": "normal",
            "orden": 2,
            "periodo": "anual",
            "nota_pieds": f"Modelo oficial de cuenta de perdidas y ganancias incluido en la tercera parte del PGC. Fuente BOE {PGC_BOE_ID}. {PGC_ACT_URL}",
        },
        {
            "estado": "memoria",
            "tipo_presentacion": "normal",
            "orden": 3,
            "periodo": "anual",
            "nota_pieds": f"Contenido de memoria incluido en la tercera parte del PGC. Fuente BOE {PGC_BOE_ID}. {PGC_ACT_URL}",
        },
    ]


def upsert_marco(conn, marco: dict) -> int:
    conn.execute(
        text(
            """
            INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
            VALUES (:codigo, :titulo, :tipo, :anio, :texto, :url_boe, true)
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                anio = EXCLUDED.anio,
                texto = EXCLUDED.texto,
                url_boe = EXCLUDED.url_boe,
                vigente = true
            """
        ),
        marco,
    )
    return 1


def upsert_account(conn, account: dict) -> int:
    conn.execute(
        text(
            """
            INSERT INTO pgc_cuenta (
                codigo, descripcion, nivel, padre_codigo, grupo, clase,
                saldo_normal, tipo_cuenta, vigente, nota
            )
            VALUES (
                :codigo, :descripcion, :nivel, :padre_codigo, :grupo, :clase,
                :saldo_normal, :tipo_cuenta, true, :nota
            )
            ON CONFLICT (codigo) DO UPDATE SET
                descripcion = EXCLUDED.descripcion,
                nivel = EXCLUDED.nivel,
                padre_codigo = EXCLUDED.padre_codigo,
                grupo = EXCLUDED.grupo,
                clase = EXCLUDED.clase,
                tipo_cuenta = EXCLUDED.tipo_cuenta,
                nota = EXCLUDED.nota,
                vigente = true
            """
        ),
        account,
    )
    return 1


def upsert_norma(conn, norma: dict) -> int:
    exists = conn.execute(
        text("SELECT 1 FROM pgc_norma_valoracion WHERE norma_ref = :norma_ref LIMIT 1"),
        {"norma_ref": norma["norma_ref"]},
    ).first()
    if exists:
        conn.execute(
            text(
                """
                UPDATE pgc_norma_valoracion
                SET articulo = :articulo, descripcion = :descripcion
                WHERE norma_ref = :norma_ref
                """
            ),
            norma,
        )
        return 0
    conn.execute(
        text(
            """
            INSERT INTO pgc_norma_valoracion (norma_ref, articulo, descripcion)
            VALUES (:norma_ref, :articulo, :descripcion)
            """
        ),
        norma,
    )
    return 1


def upsert_estado(conn, estado: dict) -> int:
    exists = conn.execute(
        text(
            """
            SELECT 1 FROM pgc_estado_financiero
            WHERE estado = :estado
              AND tipo_presentacion = :tipo_presentacion
              AND orden = :orden
              AND periodo = :periodo
            LIMIT 1
            """
        ),
        estado,
    ).first()
    if exists:
        conn.execute(
            text(
                """
                UPDATE pgc_estado_financiero
                SET nota_pieds = :nota_pieds
                WHERE estado = :estado
                  AND tipo_presentacion = :tipo_presentacion
                  AND orden = :orden
                  AND periodo = :periodo
                """
            ),
            estado,
        )
        return 0
    conn.execute(
        text(
            """
            INSERT INTO pgc_estado_financiero (
                estado, tipo_presentacion, orden, periodo, nota_pieds
            )
            VALUES (:estado, :tipo_presentacion, :orden, :periodo, :nota_pieds)
            """
        ),
        estado,
    )
    return 1


def log_sync(conn, stats: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                rows_processed, errors, error_msg
            )
            VALUES (
                'cron-pgc-boe-monthly', :started_at, now(), :status,
                :rows_processed, :errors, :error_msg
            )
            """
        ),
        stats,
    )


def run_sync(engine=None, run_once: bool = False) -> dict:
    del run_once
    started_at = datetime.now(UTC)
    engine = engine or create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    html_text = fetch_boe_text()
    marcos = parse_pgc_marco(html_text)
    accounts = parse_pgc_accounts(html_text)
    normas = parse_pgc_normas(html_text)
    estados = default_financial_statement_rows()

    if len(accounts) < 100:
        raise RuntimeError(f"PGC BOE account parser produced too few accounts: {len(accounts)}")

    with engine.begin() as conn:
        marcos_count = sum(upsert_marco(conn, item) for item in marcos)
        accounts_count = sum(upsert_account(conn, item) for item in accounts)
        normas_count = sum(upsert_norma(conn, item) for item in normas)
        estados_count = sum(upsert_estado(conn, item) for item in estados)
        rows_processed = marcos_count + accounts_count + normas_count + estados_count
        log_sync(
            conn,
            {
                "started_at": started_at,
                "status": "ok",
                "rows_processed": rows_processed,
                "errors": 0,
                "error_msg": f"marcos={marcos_count}; cuentas={accounts_count}; normas={normas_count}; estados={estados_count}",
            },
        )
    return {
        "marcos": marcos_count,
        "cuentas": accounts_count,
        "normas": normas_count,
        "estados": estados_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PGC from official BOE text")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true")
    args = parser.parse_args()
    engine = create_engine(args.db_url or DATABASE_URL, future=True)
    result = run_sync(engine=engine, run_once=args.run_once)
    logger.info("PGC BOE sync complete: %s", result)


if __name__ == "__main__":
    main()
