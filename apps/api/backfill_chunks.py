#!/usr/bin/env python3
"""Backfill chunks for documento_interpretativo (and optionally legislación).

Idempotent: uses UNIQUE(documento_origen_tipo, documento_origen_id, chunk_index)
to skip already-chunked documents on re-run.

Usage:
    # Dry-run for all documentos
    python scripts/backfill_chunks.py --dry-run

    # Backfill doctrina (documento_interpretativo)
    python scripts/backfill_chunks.py --corpus doctrina

    # Backfill legislación
    python scripts/backfill_chunks.py --corpus legislacion

    # Backfill everything
    python scripts/backfill_chunks.py --corpus all

    # Backfill a single document by reference
    python scripts/backfill_chunks.py --reference V0000-26

    # Backfill a single document by DB id
    python scripts/backfill_chunks.py --doc-id 42

    # Backfill with custom chunk size (default 1500)
    python scripts/backfill_chunks.py --corpus doctrina --chunk-size 2000
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


# ── Chunking helpers ──────────────────────────────────────────────

# Patterns that mark section boundaries in Spanish legal/ doctrinal texts
_SECTION_PATTERNS = [
    # "Primero.", "Segundo.", "Tercero." (ordinal words)
    r"(?:Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|Séptimo|Octavo|Noveno|Décimo|Décimo\w+)\.",
    # "Artículo X", "Capítulo X", "Sección X", "Apartado X"
    r"(?:Art[íi]culo|Cap[íi]tulo|Secci[óo]n|Apartado|P[áa]rrafo|Punto|Inciso|Literal)\s+\w+",
    # "I.", "II.", "1.", "1.1.", "a)", "b)"
    r"(?:^|\n)(\d{1,3}(?:\.\d{1,3})*[\.\)]|[\w]+[\.\)])\s",
    # Bold-like markers (two consecutive newlines or similar)
    r"(?:^|\n)[\s]*[A-Z][a-záéíóúñü]+(?:\s+[A-Z][a-záéíóúñü]+)*[.:]\s*$",
]

_COMBINED_RE = re.compile("|".join(_SECTION_PATTERNS), re.MULTILINE | re.IGNORECASE)


def _split_into_chunks(text: str, max_size: int = 1500) -> list[dict[str, Any]]:
    """Split text into chunks by natural boundaries or size fallback.

    Returns list of dicts with keys: chunk_type, titulo, texto, char_start, char_end, token_count.
    """
    if not text:
        return []

    # Try natural split first
    parts = _natural_split(text, max_size)
    if len(parts) > 1:
        return parts

    # Fallback: size-based split
    return _size_split(text, max_size)


def _natural_split(text: str, max_size: int) -> list[dict[str, Any]]:
    """Split by section boundaries, then ensure each part fits max_size."""
    matches = list(_COMBINED_RE.finditer(text))
    if not matches:
        return _size_split(text, max_size)

    # Group matches into sections
    sections: list[tuple[int, int]] = []
    pos = 0
    for m in matches:
        if m.start() > max_size:
            # First section too large — emit what we have, then switch to size-based
            if pos < len(text):
                sections.append((pos, len(text)))
                return _size_split(text[pos:], max_size)
        if pos < m.start():
            sections.append((pos, m.start()))
        pos = m.start()
    if pos < len(text):
        sections.append((pos, len(text)))

    if len(sections) <= 1:
        return _size_split(text, max_size)

    chunks: list[dict[str, Any]] = []
    for idx, (start, end) in enumerate(sections):
        chunk_text = text[start:end].strip()
        if not chunk_text:
            continue
        # Extract a title from the section header
        header_match = _COMBINED_RE.search(chunk_text[:200])
        titulo = header_match.group(0).strip() if header_match else None
        chunks.append({
            "chunk_type": "natural",
            "titulo": titulo,
            "texto": chunk_text,
            "char_start": start,
            "char_end": end,
            "token_count": len(chunk_text.split()),
        })

    return chunks


def _size_split(text: str, max_size: int) -> list[dict[str, Any]]:
    """Fallback: split text into fixed-size chunks with overlap."""
    overlap = max_size // 4
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        # Try to break at a sentence boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", ", ", "; ", " "]:
                idx = text.rfind(sep, start + max_size // 2, end)
                if idx > start + max_size // 3:
                    end = idx + len(sep)
                    break

        chunk_text = text[start:end].strip()
        if not chunk_text:
            break
        chunks.append({
            "chunk_type": "fallback",
            "titulo": None,
            "texto": chunk_text,
            "char_start": start,
            "char_end": end,
            "token_count": len(chunk_text.split()),
        })
        start = end - overlap if end < len(text) else end

    return chunks


# ── Document queries ──────────────────────────────────────────────

QUERY_DOCTRINA = text(
    """
    SELECT id, referencia, titulo, texto
    FROM documento_interpretativo
    ORDER BY id
    """
)

QUERY_LEGISLACION = text(
    """
    SELECT
        a.id AS articulo_id,
        n.codigo || '-' || a.numero AS doc_ref,
        n.codigo AS norma,
        a.numero AS articulo_num,
        a.titulo AS art_titulo,
        va.texto
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.vigente_desde = (
        SELECT MAX(v2.vigente_desde)
        FROM version_articulo v2
        JOIN articulo a2 ON a2.id = v2.articulo_id
        WHERE a2.id = a.id
    )
    ORDER BY n.codigo, a.numero, va.vigente_desde
    """
)


# ── Core logic ────────────────────────────────────────────────────

def backfill_chunks(
    engine,
    corpus: str,
    chunk_size: int,
    dry_run: bool,
    reference: str | None = None,
    doc_id: int | None = None,
) -> dict[str, int]:
    """Run the backfill. Returns counts: inserted, skipped, documents_processed."""
    counts = {"inserted": 0, "skipped": 0, "documents_processed": 0, "dry_run": dry_run}

    with engine.connect() as conn:
        if corpus == "doctrina" or corpus == "all":
            n = _backfill_corpus_doctrina(conn, chunk_size, dry_run, reference, counts)
            counts["inserted"] += n
            counts["documents_processed"] += n

        if corpus == "legislacion" or corpus == "all":
            n = _backfill_corpus_legislacion(conn, chunk_size, dry_run, reference, counts)
            counts["inserted"] += n
            counts["documents_processed"] += n

    return counts


def _backfill_corpus_doctrina(
    conn,
    chunk_size: int,
    dry_run: bool,
    reference_filter: str | None,
    counts: dict[str, int],
) -> int:
    """Backfill chunks for documento_interpretativo."""
    docs = conn.execute(QUERY_DOCTRINA).mappings()
    inserted = 0

    for doc in docs:
        doc_id_val = doc["id"]
        referencia = doc["referencia"]

        # Filter by reference if specified
        if reference_filter and referencia != reference_filter:
            continue

        # Check if already has chunks (idempotency)
        existing = conn.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM documento_fragmento "
                "WHERE documento_origen_tipo = 'doctrina' "
                "AND documento_origen_id = :doc_id"
            ),
            {"doc_id": doc_id_val},
        ).scalar()

        if existing > 0:
            counts["skipped"] += 1
            continue

        chunks = _split_into_chunks(doc["texto"], chunk_size)
        if not chunks:
            continue

        for idx, chunk in enumerate(chunks):
            if dry_run:
                print(
                    f"  [DRY-RUN] INSERT doctrina doc={doc_id_val} ref={referencia} "
                    f"idx={idx} type={chunk['chunk_type']} tokens={chunk['token_count']}"
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO documento_fragmento
                            (documento_origen_tipo, documento_origen_id, chunk_index,
                             chunk_type, titulo, texto, char_start, char_end, token_count)
                        VALUES
                            ('doctrina', :doc_id, :idx, :chunk_type, :titulo, :texto,
                             :char_start, :char_end, :token_count)
                        ON CONFLICT (documento_origen_tipo, documento_origen_id, chunk_index)
                        DO NOTHING
                        """
                    ),
                    {
                        "doc_id": doc_id_val,
                        "idx": idx,
                        "chunk_type": chunk["chunk_type"],
                        "titulo": chunk["titulo"],
                        "texto": chunk["texto"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "token_count": chunk["token_count"],
                    },
                )
                inserted += 1

        if not dry_run and inserted > 0:
            conn.commit()

        counts["documents_processed"] += 1

    return inserted


def _backfill_corpus_legislacion(
    conn,
    chunk_size: int,
    dry_run: bool,
    reference_filter: str | None,
    counts: dict[str, int],
) -> int:
    """Backfill chunks for legislación (version_articulo vigentes).

    Each article version becomes a document with tipo='legislacion'.
    """
    docs = conn.execute(QUERY_LEGISLACION).mappings()
    inserted = 0

    for doc in docs:
        articulo_id = doc["articulo_id"]
        doc_ref = doc["doc_ref"]
        norma = doc["norma"]
        art_num = doc["articulo_num"]

        # Filter by reference if specified (accepts "LIVA", "LIVA-91", or "91")
        if reference_filter:
            if reference_filter != norma and reference_filter != doc_ref and reference_filter != art_num:
                continue

        # Check if already has chunks (idempotency)
        existing = conn.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM documento_fragmento "
                "WHERE documento_origen_tipo = 'legislacion' "
                "AND documento_origen_id = :doc_id"
            ),
            {"doc_id": articulo_id},
        ).scalar()

        if existing > 0:
            counts["skipped"] += 1
            continue

        chunks = _split_into_chunks(doc["texto"], chunk_size)
        if not chunks:
            continue

        for idx, chunk in enumerate(chunks):
            if dry_run:
                print(
                    f"  [DRY-RUN] INSERT legislacion doc={doc_ref} (articulo_id={articulo_id}) "
                    f"idx={idx} type={chunk['chunk_type']} tokens={chunk['token_count']}"
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO documento_fragmento
                            (documento_origen_tipo, documento_origen_id, chunk_index,
                             chunk_type, titulo, texto, char_start, char_end, token_count)
                        VALUES
                            ('legislacion', :doc_id, :idx, :chunk_type, :titulo, :texto,
                             :char_start, :char_end, :token_count)
                        ON CONFLICT (documento_origen_tipo, documento_origen_id, chunk_index)
                        DO NOTHING
                        """
                    ),
                    {
                        "doc_id": articulo_id,
                        "idx": idx,
                        "chunk_type": chunk["chunk_type"],
                        "titulo": chunk["titulo"],
                        "texto": chunk["texto"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "token_count": chunk["token_count"],
                    },
                )
                inserted += 1

        if not dry_run and inserted > 0:
            conn.commit()

        counts["documents_processed"] += 1

    return inserted


# ── CLI ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill chunks for documento_interpretativo and legislación."
    )
    parser.add_argument(
        "--corpus",
        choices=["doctrina", "legislacion", "all"],
        default="doctrina",
        help="Which corpus to backfill (default: doctrina).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1500,
        help="Max characters per chunk (default: 1500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be inserted without writing.",
    )
    parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help="Backfill only the document with this reference (e.g. V0000-26).",
    )
    parser.add_argument(
        "--doc-id",
        type=int,
        default=None,
        help="Backfill only the documento_interpretativo with this DB id.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="DATABASE_URL override (default: env var DATABASE_URL).",
    )

    args = parser.parse_args()

    db_url = args.database_url or (
        "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"
    )

    print(f"Connecting to database...")
    engine = create_engine(db_url, future=True)

    try:
        # Verify tables exist
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('documento_interpretativo', 'documento_fragmento', 'version_articulo', 'norma', 'articulo')"
                )
            ).fetchall()
            table_names = {t[0] for t in tables}
            if "documento_fragmento" not in table_names:
                print("ERROR: documento_fragmento table not found. Run Alembic migration first.", file=sys.stderr)
                return 1
            print(f"Schema OK. Tables found: {', '.join(sorted(table_names))}")

        print(f"Backfilling corpus='{args.corpus}' chunk_size={args.chunk_size} dry_run={args.dry_run}")
        if args.reference:
            print(f"  Filter by reference: {args.reference}")
        if args.doc_id:
            print(f"  Filter by doc_id: {args.doc_id}")

        counts = backfill_chunks(
            engine,
            corpus=args.corpus,
            chunk_size=args.chunk_size,
            dry_run=args.dry_run,
            reference=args.reference,
        )

        print()
        print("=== Results ===")
        print(f"  Documents processed: {counts['documents_processed']}")
        print(f"  Chunks inserted:     {counts['inserted']}")
        print(f"  Documents skipped:   {counts['skipped']}")
        if counts["dry_run"]:
            print("  (dry-run — no data was written)")
        else:
            print("  (search_vector populated by DB trigger)")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
