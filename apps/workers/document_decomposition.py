#!/usr/bin/env python
"""Derive sections, fragments, CNMV versions, and lineage from official documents."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from runtime import configure_logging, get_database_url
from sqlalchemy import create_engine, text


logger = configure_logging("worker-document-decomposition")
DATABASE_URL = get_database_url()


def chunk_text(value: str, size: int = 1600) -> list[tuple[int, int, str]]:
    chunks = []
    start = 0
    text_value = value.strip()
    while start < len(text_value):
        end = min(start + size, len(text_value))
        if end < len(text_value):
            split_at = text_value.rfind("\n", start, end)
            if split_at <= start:
                split_at = text_value.rfind(". ", start, end)
            if split_at > start:
                end = split_at + 1
        chunk = text_value[start:end].strip()
        if chunk:
            chunks.append((start, end, chunk))
        start = end
    return chunks


def upsert_lineage(conn, entry_id: str, table_name: str, field: str, source: str, transform: str, worker: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO data_lineage (
                entry_id, tabla, campo, fuente_origen, transformacion,
                fecha_ingestion, worker_correspondiente, calidad_score, observaciones
            )
            VALUES (
                :entry_id, :tabla, :campo, :fuente_origen, :transformacion,
                :fecha_ingestion, :worker, 100, :observaciones
            )
            ON CONFLICT (entry_id) DO UPDATE SET
                fuente_origen = EXCLUDED.fuente_origen,
                transformacion = EXCLUDED.transformacion,
                fecha_ingestion = EXCLUDED.fecha_ingestion,
                worker_correspondiente = EXCLUDED.worker_correspondiente,
                observaciones = EXCLUDED.observaciones
            """
        ),
        {
            "entry_id": entry_id,
            "tabla": table_name,
            "campo": field,
            "fuente_origen": source,
            "transformacion": transform,
            "fecha_ingestion": datetime.now(UTC).isoformat(),
            "worker": worker,
            "observaciones": "Derivado de documento_interpretativo con fuente oficial conservada.",
        },
    )


def ensure_section(conn, doc: dict) -> int:
    existing = conn.execute(
        text(
            """
            SELECT id FROM documento_seccion
            WHERE documento_origen_tipo = 'documento_interpretativo'
              AND documento_origen_id = :doc_id
              AND tipo_seccion = 'documento'
              AND orden = 1
            LIMIT 1
            """
        ),
        {"doc_id": doc["id"]},
    ).scalar_one_or_none()
    if existing:
        return int(existing)

    row = conn.execute(
        text(
            """
            INSERT INTO documento_seccion (
                documento_origen_tipo, documento_origen_id, tipo_seccion,
                numero, titulo, nivel, orden
            )
            VALUES (
                'documento_interpretativo', :doc_id, 'documento',
                :referencia, :titulo, 1, 1
            )
            RETURNING id
            """
        ),
        {"doc_id": doc["id"], "referencia": doc["referencia"], "titulo": doc["titulo"]},
    ).scalar_one()
    return int(row)


def upsert_fragment(conn, doc: dict, section_id: int, chunk_index: int, start: int, end: int, chunk: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO documento_fragmento (
                documento_origen_tipo, documento_origen_id, seccion_id, chunk_index,
                chunk_type, titulo, texto, char_start, char_end, token_count,
                content_hash
            )
            VALUES (
                'documento_interpretativo', :doc_id, :seccion_id, :chunk_index,
                'natural', :titulo, :texto, :char_start, :char_end, :token_count,
                md5(:texto)
            )
            ON CONFLICT (documento_origen_tipo, documento_origen_id, chunk_index)
            DO UPDATE SET
                seccion_id = EXCLUDED.seccion_id,
                titulo = EXCLUDED.titulo,
                texto = EXCLUDED.texto,
                char_start = EXCLUDED.char_start,
                char_end = EXCLUDED.char_end,
                token_count = EXCLUDED.token_count,
                content_hash = EXCLUDED.content_hash
            """
        ),
        {
            "doc_id": doc["id"],
            "seccion_id": section_id,
            "chunk_index": chunk_index,
            "titulo": doc["titulo"],
            "texto": chunk,
            "char_start": start,
            "char_end": end,
            "token_count": len(chunk.split()),
        },
    )


def upsert_cnmv_version(conn, doc: dict) -> int:
    if (doc["organismo_emisor"] or "").upper() != "CNMV":
        return 0
    conn.execute(
        text(
            """
            INSERT INTO documento_cnmv_version (
                documento_referencia, version_numero, estado_version,
                fecha_version, resumen_cambios, fuente_version
            )
            VALUES (
                :referencia, 1, :estado, :fecha, :resumen, :fuente
            )
            ON CONFLICT (documento_referencia, version_numero) DO UPDATE SET
                estado_version = EXCLUDED.estado_version,
                fecha_version = EXCLUDED.fecha_version,
                resumen_cambios = EXCLUDED.resumen_cambios,
                fuente_version = EXCLUDED.fuente_version
            """
        ),
        {
            "referencia": doc["referencia"],
            "estado": doc["estado_vigencia"] or "vigente_no_verificado",
            "fecha": doc["fecha"],
            "resumen": "Version inicial derivada del documento oficial ingerido.",
            "fuente": doc["url_fuente"],
        },
    )
    return 1


def run_sync(engine=None, run_once: bool = False) -> dict:
    del run_once
    engine = engine or create_engine(DATABASE_URL, future=True)
    docs_sql = """
        SELECT id, organismo_emisor, referencia, fecha, titulo, texto, url_fuente, estado_vigencia
        FROM documento_interpretativo
        WHERE url_fuente IS NOT NULL
          AND texto IS NOT NULL
          AND length(texto) > 50
        ORDER BY id
    """
    stats = {"documents": 0, "sections": 0, "fragments": 0, "cnmv_versions": 0}
    with engine.begin() as conn:
        docs = [dict(row) for row in conn.execute(text(docs_sql)).mappings().all()]
        for doc in docs:
            stats["documents"] += 1
            section_id = ensure_section(conn, doc)
            stats["sections"] += 1
            upsert_lineage(
                conn,
                f"documento_seccion:{section_id}",
                "documento_seccion",
                "titulo",
                doc["url_fuente"],
                "section_from_documento_interpretativo",
                "document-decomposition",
            )
            for idx, (start, end, chunk) in enumerate(chunk_text(doc["texto"]), start=1):
                upsert_fragment(conn, doc, section_id, idx, start, end, chunk)
                stats["fragments"] += 1
                upsert_lineage(
                    conn,
                    f"documento_fragmento:{doc['id']}:{idx}",
                    "documento_fragmento",
                    "texto",
                    doc["url_fuente"],
                    "chunk_from_documento_interpretativo",
                    "document-decomposition",
                )
            if upsert_cnmv_version(conn, doc):
                stats["cnmv_versions"] += 1
                upsert_lineage(
                    conn,
                    f"documento_cnmv_version:{doc['referencia']}:1",
                    "documento_cnmv_version",
                    "fuente_version",
                    doc["url_fuente"],
                    "version_from_cnmv_document",
                    "document-decomposition",
                )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompose official documents")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true")
    args = parser.parse_args()
    engine = create_engine(args.db_url or DATABASE_URL, future=True)
    result = run_sync(engine=engine, run_once=args.run_once)
    logger.info("Document decomposition complete: %s", result)


if __name__ == "__main__":
    main()
