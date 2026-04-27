"""Quick backfill of documento_fragmento from version_articulo and documento_interpretativo."""
from sqlalchemy import create_engine, text
import re

engine = create_engine("postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata")

SECTION_PATTERNS = [
    r"(?:Art[íi]culo|Cap[íi]tulo|Secci[óo]n|Apartado|P[áa]rrafo|Punto|Inciso|Literal)\s+\w+",
    r"(?:Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|Séptimo|Octavo|Noveno|Décimo)\.",
]
COMBINED_RE = re.compile("|".join(SECTION_PATTERNS), re.MULTILINE | re.IGNORECASE)

def split_text(text, max_size=2000, _depth=0):
    if not text:
        return []
    if _depth > 3:
        # hard fallback: size-based
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_size, len(text))
            chunks.append({"chunk_type": "fallback", "titulo": None, "texto": text[start:end].strip(), "chunk_index": len(chunks)})
            start = end
        return chunks
    matches = list(COMBINED_RE.finditer(text))
    if not matches:
        return split_text(text, max_size, _depth + 1)
    sections = []
    pos = 0
    for m in matches:
        if pos < m.start():
            sections.append((pos, m.start()))
        pos = m.start()
    if pos < len(text):
        sections.append((pos, len(text)))
    if len(sections) <= 1:
        return split_text(text, max_size, _depth + 1)
    chunks = []
    for idx, (start, end) in enumerate(sections):
        chunk_text = text[start:end].strip()
        if not chunk_text:
            continue
        header = COMBINED_RE.search(chunk_text[:200])
        chunks.append({"chunk_type": "natural", "titulo": header.group(0).strip() if header else None, "texto": chunk_text, "chunk_index": idx})
    return chunks

def backfill_doctrina(conn):
    docs = conn.execute(text("SELECT id, referencia, titulo, texto FROM documento_interpretativo ORDER BY id")).mappings()
    inserted = 0
    for doc in docs:
        doc_id = doc["id"]
        existing = conn.execute(text("SELECT COUNT(*) FROM documento_fragmento WHERE documento_origen_tipo='doctrina' AND documento_origen_id=:d"), {"d": doc_id}).scalar()
        if existing > 0:
            print(f"  SKIPPED doctrina doc={doc_id}")
            continue
        chunks = split_text(doc["texto"])
        for c in chunks:
            conn.execute(text("""INSERT INTO documento_fragmento (documento_origen_tipo, documento_origen_id, chunk_index, chunk_type, titulo, texto) VALUES (:tipo, :doc_id, :idx, :tipo_chunk, :titulo, :texto) ON CONFLICT DO NOTHING"""), {"tipo": "doctrina", "doc_id": doc_id, "idx": c["chunk_index"], "tipo_chunk": c["chunk_type"], "titulo": c["titulo"], "texto": c["texto"]})
            inserted += 1
    conn.commit()
    print(f"  doctrina: {inserted} chunks inserted")
    return inserted

def backfill_legislacion(conn):
    docs = conn.execute(text("""
        SELECT a.id AS articulo_id, n.codigo || '-' || a.numero AS doc_ref, va.texto
        FROM version_articulo va
        JOIN articulo a ON a.id = va.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE va.vigente_desde = (
            SELECT MAX(v2.vigente_desde) FROM version_articulo v2
            JOIN articulo a2 ON a2.id = v2.articulo_id WHERE a2.id = a.id
        )
        ORDER BY n.codigo, a.numero
    """)).mappings()
    inserted = 0
    for doc in docs:
        art_id = doc["articulo_id"]
        existing = conn.execute(text("SELECT COUNT(*) FROM documento_fragmento WHERE documento_origen_tipo='legislacion' AND documento_origen_id=:d"), {"d": art_id}).scalar()
        if existing > 0:
            continue
        chunks = split_text(doc["texto"])
        for c in chunks:
            conn.execute(text("""INSERT INTO documento_fragmento (documento_origen_tipo, documento_origen_id, chunk_index, chunk_type, titulo, texto) VALUES (:tipo, :doc_id, :idx, :tipo_chunk, :titulo, :texto) ON CONFLICT DO NOTHING"""), {"tipo": "legislacion", "doc_id": art_id, "idx": c["chunk_index"], "tipo_chunk": c["chunk_type"], "titulo": c["titulo"], "texto": c["texto"]})
            inserted += 1
    conn.commit()
    print(f"  legislacion: {inserted} chunks inserted")
    return inserted

with engine.connect() as conn:
    print("Backfilling doctrine...")
    backfill_doctrina(conn)
    print("Backfilling legislacion...")
    backfill_legislacion(conn)
    total = conn.execute(text("SELECT COUNT(*) FROM documento_fragmento")).scalar()
    print(f"Total documento_fragmento rows: {total}")
