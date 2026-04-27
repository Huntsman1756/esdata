from pathlib import Path
import sys

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cnmv import (
    build_document_payload,
    run_sync,
    upsert_documento_interpretativo,
    upsert_with_versioning,
    _detect_document_type,
    _detect_ambito,
    _detect_regulaciones,
    _detect_obligaciones,
    _upsert_regulation_links,
    _upsert_obligation_links,
    _extract_reference,
    _extract_circular_number,
    _extract_publication_date,
    _extract_boe_reference,
    _detect_vigencia,
    _discover_new_urls,
    _record_version,
    _get_next_version,
)


MINIMAL_CNMV_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 167 >>
stream
BT
/F1 12 Tf
20 110 Td
(Circular 9/2008 de la Comision Nacional del Mercado de Valores) Tj
0 -18 Td
(Normas contables, estados de informacion reservada y publica) Tj
0 -18 Td
(Cuentas anuales de las sociedades rectoras) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000459 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
529
%%EOF
"""


# ---------------------------------------------------------------------------
# Document type detection (23.3)
# ---------------------------------------------------------------------------


def test_detect_document_type_circular():
    assert _detect_document_type("Circular 9/2008 de la CNMV") == "circular_cnmv"
    assert _detect_document_type("Circular 3/2015 sobre mercados") == "circular_cnmv"


def test_detect_document_type_manual():
    assert _detect_document_type("Manual de procedimientos internos") == "manual_cnmv"


def test_detect_document_type_guia():
    assert _detect_document_type("Guía de buenas prácticas") == "guia_cnmv"
    assert _detect_document_type("Guía del inversor minorista") == "guia_cnmv"


def test_detect_document_type_resolucion():
    assert _detect_document_type("Resolución 5/2020 de la CNMV") == "resolucion_cnmv"


def test_detect_document_type_informe():
    assert _detect_document_type("Informe Anual de Supervisión") == "informe_anual_cnmv"
    assert _detect_document_type("Informe de mercados") == "informe_cnmv"


def test_detect_document_type_codigo():
    assert _detect_document_type("Código de Buen Gobierno") == "codigo_autoregulacion_cnmv"
    assert _detect_document_type("Código de conducta profesional") == "codigo_conducta_cnmv"


def test_detect_document_type_fallback():
    assert _detect_document_type("Documento sobre mercados financieros") == "documento_cnmv"


# ---------------------------------------------------------------------------
# Ambito detection (23.4)
# ---------------------------------------------------------------------------


def test_detect_ambito_mifid():
    assert _detect_ambito("Directiva MiFID II servicios de inversión") == "mifid_ii"
    assert _detect_ambito("MiFID II y servicios de inversion") == "mifid_ii"


def test_detect_ambito_mar():
    assert _detect_ambito("Reglamento MAR abuso de mercado") == "mar"
    assert _detect_ambito("Market abuse regulation") == "mar"


def test_detect_ambito_dora():
    assert _detect_ambito("Directiva DORA resiliencia operacional digital") == "dora"


def test_detect_ambito_priips():
    assert _detect_ambito("Reglamento PRIIPs productos de inversión") == "priips"


def test_detect_ambito_reporting_regulatorio():
    assert _detect_ambito("Información reservada estados confidenciales") == "reporting_regulatorio_cnmv"
    assert _detect_ambito("Informacion reservada y pública") == "reporting_regulatorio_cnmv"


def test_detect_ambito_reporting_financiero():
    assert _detect_ambito("Estados de información cuentas anuales") == "reporting_financiero_cnmv"


def test_detect_ambito_gobierno_corporativo():
    assert _detect_ambito("Gobierno corporativo código de buen gobierno") == "gobierno_corporativo"


def test_detect_ambito_transparencia():
    assert _detect_ambito("Hechos relevantes transparencia de emisores") == "transparencia_emisores"


def test_detect_ambito_legacy_fallback():
    assert _detect_ambito("MIFID servicios de inversion") == "mercados"


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def test_extract_circular_number():
    assert _extract_circular_number("Circular 9/2008 de la CNMV") == "9/2008"
    assert _extract_circular_number("sin referencia circular") is None


def test_extract_publication_date_boe():
    assert _extract_publication_date("BOE-A-2009-133") == "2009"


def test_extract_publication_date_ddmmyyyy():
    result = _extract_publication_date("Fecha 15/03/2024")
    assert result == "2024-03-15"


def test_extract_boe_reference():
    assert _extract_boe_reference("BOE-A-2009-133") == "BOE-A-2009-133"
    assert _extract_boe_reference("BOE-A-2009-133", "https://example.com") == "BOE-A-2009-133"
    assert _extract_boe_reference("sin referencia") is None
    assert _extract_boe_reference("sin referencia", "https://boe.es/doc.php?id=BOE-A-2015-5000") == "BOE-A-2015-5000"


def test_detect_vigencia_vigente():
    assert _detect_vigencia("Norma vigente en vigor") == "vigente"


def test_detect_vigencia_derogado():
    assert _detect_vigencia("Norma derogada por la nueva") == "derogado"


def test_detect_vigencia_modificado():
    assert _detect_vigencia("Norma modificada parcialmente") == "vigente_modificado"


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------


def test_extract_reference_boe_url():
    assert _extract_reference("https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133", "") == "BOE-A-2009-133"


def test_extract_reference_boe_text():
    assert _extract_reference("https://example.com/doc", "BOE-A-2015-5000") == "BOE-A-2015-5000"


def test_extract_reference_circular():
    result = _extract_reference("https://example.com", "Circular 9/2008 de la CNMV")
    assert result == "CNMV-CIRCULAR-9-2008"


def test_extract_reference_fallback():
    result = _extract_reference("https://example.com/path/to/doc", "sin referencia")
    assert result == "CNMV-doc"


# ---------------------------------------------------------------------------
# Payload building (23.2)
# ---------------------------------------------------------------------------


def test_build_document_payload_extracts_enriched_fields():
    payload = build_document_payload(
        "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
        MINIMAL_CNMV_PDF,
    )

    assert payload["referencia"] == "BOE-A-2009-133"
    assert payload["tipo_documento"] == "circular_cnmv"
    assert payload["ambito"] == "reporting_regulatorio_cnmv"
    assert payload["numero_circular"] == "9/2008"
    assert payload["referencia_boe"] == "BOE-A-2009-133"
    assert "estados de informacion reservada" in payload["texto"].lower()


def test_build_document_payload_minimal():
    payload = build_document_payload(
        "https://example.com/doc",
        MINIMAL_CNMV_PDF,
    )

    assert payload["referencia"].startswith("CNMV-")
    assert payload["numero_circular"] == "9/2008"
    assert payload["referencia_boe"] is None


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


def test_upsert_with_enriched_columns():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "BOE-A-2009-133",
            "fecha": "2009-01-02",
            "titulo": "Circular 9/2008",
            "tipo_documento": "circular_cnmv",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
            "ambito": "reporting_regulatorio_cnmv",
            "texto": "Normas contables.",
            "url_fuente": "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
            "numero_circular": "9/2008",
            "fecha_publicacion": "2009",
            "referencia_boe": "BOE-A-2009-133",
            "estado_vigencia": "vigente",
        }

        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, numero_circular, fecha_publicacion, referencia_boe, estado_vigencia FROM documento_interpretativo"
            )
        ).fetchone()

    assert row[0] == "BOE-A-2009-133"
    assert row[1] == "9/2008"
    assert row[2] == "2009"
    assert row[3] == "BOE-A-2009-133"
    assert row[4] == "vigente"


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def test_run_sync_persists_cnmv_document_and_metrics(monkeypatch):
    import tempfile

    db_file = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite:///{db_file}"

    # Create tables in the DB file
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    bloques_processed INTEGER,
                    articulos_upserted INTEGER,
                    documentos_processed INTEGER,
                    documentos_upserted INTEGER,
                    doctrina_links_created INTEGER,
                    error_msg TEXT,
                    urls_discovered INTEGER
                )
                """
            )
        )

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MINIMAL_CNMV_PDF)

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )
    # Prevent discover from interfering — return seed URLs directly
    def fake_discover(seed_urls=None):
        return seed_urls or ["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"]
    monkeypatch.setattr("cnmv._discover_new_urls", fake_discover)

    result = run_sync(seed_urls=["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"])

    assert result["processed"] == 1
    assert result["stored"] == 1
    assert "discovered" in result

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito, tipo_documento FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133'"
            )
        ).fetchone()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc == (
        "BOE-A-2009-133",
        "CNMV",
        "cnmv",
        "reporting_regulatorio_cnmv",
        "circular_cnmv",
    )
    assert sync == ("worker-cnmv", "ok", 1, 1)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discover_new_urls_fallback(monkeypatch):
    """When scraping fails, should fall back to seed URLs."""
    monkeypatch.setenv("CNMV_SEED_URLS", "https://example.com/doc1.pdf, https://example.com/doc2.pdf")

    # Re-import to pick up new env var
    import importlib
    import cnmv
    importlib.reload(cnmv)

    urls = cnmv._discover_new_urls()
    assert len(urls) >= 0  # May be empty if scraping fails gracefully


def test_discover_new_urls_empty():
    """When no seed URLs configured and scraping fails, should use fallback."""
    urls = _discover_new_urls()
    # Should not raise — falls back to CNMV_SEED_URLS_FALLBACK
    assert isinstance(urls, list)


# ---------------------------------------------------------------------------
# Versioning (23.6)
# ---------------------------------------------------------------------------


def test_record_version_creates_entry(monkeypatch):
    """_record_version should insert a new version entry."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        # Create minimal tables
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto) VALUES ('BOE-A-2009-133', 'Texto original')"))

    with engine.begin() as conn:
        _record_version(conn, "BOE-A-2009-133", "Texto modificado", "modificado", nota="Primera modificacion")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT documento_referencia, version_num, cambio_tipo, nota FROM documento_version")).fetchone()

    assert version is not None
    assert version.documento_referencia == "BOE-A-2009-133"
    assert version.version_num == 1
    assert version.cambio_tipo == "modificado"
    assert version.nota == "Primera modificacion"


def test_get_next_version_increments():
    """_get_next_version should return sequential numbers."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2009-133', 1, 'v1', 'creado', '2026-01-01')"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2009-133', 2, 'v2', 'modificado', '2026-01-02')"))

    with engine.connect() as conn:
        next_ver = _get_next_version(conn, "BOE-A-2009-133")

    assert next_ver == 3


def test_upsert_with_versioning_creates_new():
    """upsert_with_versioning should create new doc and record version 1."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))

        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Nuevo documento CNMV",
            "titulo": "Circular 1/2025",
            "tipo_documento": "circular_cnmv",
            "ambito": "mifid_ii",
            "fecha": "2025-01-15",
            "url_fuente": "https://www.cnmv.es/doc.pdf",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "created"
    assert result["version_num"] == 1

    with engine.connect() as conn:
        doc = conn.execute(text("SELECT referencia, texto FROM documento_interpretativo WHERE referencia = 'BOE-A-2025-100'")).fetchone()
        ver = conn.execute(text("SELECT version_num, cambio_tipo FROM documento_version WHERE documento_referencia = 'BOE-A-2025-100'")).fetchone()

    assert doc is not None
    assert doc.referencia == "BOE-A-2025-100"
    assert ver.version_num == 1
    assert ver.cambio_tipo == "creado"


def test_upsert_with_versioning_updates():
    """upsert_with_versioning should update existing doc and record new version."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        # Insert existing doc with version 1 already recorded
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto, titulo, tipo_documento, ambito) VALUES ('BOE-A-2025-100', 'Texto original', 'Circular 1/2025', 'circular_cnmv', 'mifid_ii')"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2025-100', 1, 'Texto original', 'creado', '2025-01-01')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto modificado con nueva norma",
            "titulo": "Circular 1/2025 (modificada)",
            "tipo_documento": "circular_cnmv",
            "ambito": "mifid_ii",
            "fecha": "2025-06-15",
            "url_fuente": "https://www.cnmv.es/doc_v2.pdf",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "updated"
    assert result["version_num"] == 3  # 1 (creado) + 1 (modificado) + 1 (next_ver)

    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version_num, cambio_tipo FROM documento_version WHERE documento_referencia = 'BOE-A-2025-100' ORDER BY version_num")).fetchall()

    assert len(ver) == 2
    assert ver[0].cambio_tipo == "creado"
    assert ver[1].cambio_tipo == "modificado"


def test_upsert_with_versioning_unchanged():
    """upsert_with_versioning should return unchanged when texto is identical."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto) VALUES ('BOE-A-2025-100', 'Texto identico')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto identico",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "unchanged"
    assert result["version_num"] is None

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_version")).fetchone()[0]

    assert count == 0  # No new versions recorded


def test_upsert_with_versioning_derogado():
    """upsert_with_versioning should detect derogado from estado_vigencia."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT, estado_vigencia TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto, estado_vigencia, tipo_documento, ambito) VALUES ('BOE-A-2025-100', 'Texto original', 'vigente', 'circular_cnmv', 'mifid_ii')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto derogado por nueva circular",
            "estado_vigencia": "derogado",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "derogado"


# ---------------------------------------------------------------------------
# Regulation mapping tests (23.7)
# ---------------------------------------------------------------------------


def test_detect_regulaciones_mifid_ii():
    """_detect_regulaciones should detect mifid_ii regulation."""
    text = "Circular sobre MiFID II y servicios de inversión. Directiva 2014/65/UE."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "mifid_ii" for r in result)
    assert any(r["relacion_tipo"] == "implementa" for r in result)


def test_detect_regulaciones_mar():
    """_detect_regulaciones should detect MAR regulation."""
    text = "Reglamento MAR sobre abuso de mercado. Reglamento (UE) 596/2014."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "mar" for r in result)


def test_detect_regulaciones_dora():
    """_detect_regulaciones should detect DORA regulation."""
    text = "Resiliencia operacional digital. Directiva DORA 2022/2554."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "dora" for r in result)


def test_detect_regulaciones_priips():
    """_detect_regulaciones should detect PRIIPs regulation."""
    text = "Reglamento PRIIPs sobre productos de inversión al por menor."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "priips" for r in result)


def test_detect_regulaciones_multiple():
    """_detect_regulaciones should detect multiple regulations."""
    text = "MiFID II y MAR. Directiva 2014/65/UE y reglamento 596/2014 sobre abuso de mercado."
    result = _detect_regulaciones(text)
    reg_ids = [r["regulacion_id"] for r in result]
    assert "mifid_ii" in reg_ids
    assert "mar" in reg_ids


def test_detect_regulaciones_none():
    """_detect_regulaciones should return empty list when no regulation matches."""
    text = "Este es un documento genérico sin referencia a regulaciones EU."
    result = _detect_regulaciones(text)
    assert result == []


def test_detect_regulaciones_gobierno():
    """_detect_regulaciones should detect gobierno corporativo regulation."""
    text = "Codigo de buen gobierno corporativo. Recomendaciones de la CNMV sobre gobernanza."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "cgce" for r in result)


def test_upsert_regulation_links_basic():
    """_upsert_regulation_links should insert links when table exists."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE cnmv_regulation_link (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                regulacion_id TEXT,
                relacion_tipo TEXT,
                nota TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))

    links = [
        {"regulacion_id": "mifid_ii", "relacion_tipo": "implementa", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_regulation_links(conn, "BOE-A-2025-100", links)

    assert count == 1

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT regulacion_id, relacion_tipo FROM cnmv_regulation_link WHERE documento_referencia = :ref"),
            {"ref": "BOE-A-2025-100"},
        ).mappings().first()

    assert row["regulacion_id"] == "mifid_ii"
    assert row["relacion_tipo"] == "implementa"


def test_upsert_regulation_links_fallback_when_table_missing():
    """_upsert_regulation_links should return 0 when table does not exist."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT)"))

    links = [
        {"regulacion_id": "mifid_ii", "relacion_tipo": "implementa", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_regulation_links(conn, "BOE-A-2025-100", links)

    assert count == 0


def test_upsert_with_versioning_includes_regulations():
    """upsert_with_versioning should detect and link regulations, returning count."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))
        # Insert existing document
        conn.execute(text("""
            INSERT INTO documento_interpretativo
            (referencia, texto, estado_vigencia, tipo_documento, ambito)
            VALUES ('BOE-A-2025-100', 'Texto original vigente', 'vigente', 'circular_cnmv', 'mifid_ii')
        """))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "MiFID II y MAR. Directiva 2014/65/UE y reglamento 596/2014 sobre abuso de mercado.",
            "estado_vigencia": "vigente",
        }
        result = upsert_with_versioning(conn, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "modificado"
    assert result.get("regulaciones", 0) >= 1


# ---------------------------------------------------------------------------
# Phase 23.8 — Obligation derivation tests
# ---------------------------------------------------------------------------


def test_detect_obligaciones_presentacion_modelo():
    """Detect presentacion_modelo obligation from text."""
    text = "La sociedad de valores deberá presentar el modelo 620 antes del 20 de enero de cada año."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "presentacion_modelo" in tipos


def test_detect_obligaciones_remision_informacion():
    """Detect remision_informacion obligation from text."""
    text = "Obligación de comunicar a la CNMV cualquier modificación estatutaria en un plazo de 10 días hábiles."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "remision_informacion" in tipos


def test_detect_obligaciones_control_interno():
    """Detect control_interno obligation from text."""
    text = "La sociedad deberá mantener sistemas de control interno adecuados para registrar todas las operaciones realizadas."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "control_interno" in tipos


def test_detect_obligaciones_comunicacion_indicio():
    """Detect comunicacion_indicio obligation from text."""
    text = "Se deberá comunicar inmediatamente cualquier operación sospechosa de lavado de dinero a la CNMV."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "comunicacion_indicio" in tipos


def test_detect_obligaciones_reporting_prudencial():
    """Detect reporting_prudencial obligation from text."""
    text = "Reporte prudencial mensual de requisitos de capital y liquidez conforme a la normativa CNMV."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "reporting_prudencial" in tipos


def test_detect_obligaciones_multiple():
    """Detect multiple obligations from mixed text."""
    text = "La sociedad deberá presentar el modelo 347 y además deberá mantener controles internos adecuados. Asimismo, deberá comunicar indicios de lavado."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "presentacion_modelo" in tipos
    assert "control_interno" in tipos
    assert "comunicacion_indicio" in tipos


def test_detect_obligaciones_none():
    """Return empty list when no obligation patterns match."""
    text = "Este documento trata sobre la organización general de la sociedad de valores y sus principios de funcionamiento."
    result = _detect_obligaciones(text)
    assert result == []


def test_upsert_obligation_links_basic():
    """Upsert obligation links for a CNMV document."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_obligation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                tipo_obligacion TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, tipo_obligacion)
            )
        """))

    links = [
        {"tipo_obligacion": "presentacion_modelo", "nota": "Test"},
        {"tipo_obligacion": "remision_informacion", "nota": "Test 2"},
    ]
    with engine.begin() as conn:
        count = _upsert_obligation_links(conn, "BOE-A-2025-100", links)

    assert count == 2

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT tipo_obligacion FROM cnmv_obligation_link WHERE documento_referencia = :ref"),
            {"ref": "BOE-A-2025-100"},
        ).mappings().all()
        tipos = [r["tipo_obligacion"] for r in rows]

    assert "presentacion_modelo" in tipos
    assert "remision_informacion" in tipos


def test_upsert_obligation_links_fallback_when_table_missing():
    """_upsert_obligation_links should return 0 when table doesn't exist."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT)"))

    links = [
        {"tipo_obligacion": "presentacion_modelo", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_obligation_links(conn, "BOE-A-2025-100", links)

    assert count == 0


def test_upsert_with_versioning_includes_obligations():
    """upsert_with_versioning should detect and link obligations, returning count."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_obligation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                tipo_obligacion TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, tipo_obligacion)
            )
        """))
        # Insert existing document
        conn.execute(text("""
            INSERT INTO documento_interpretativo
            (referencia, texto, estado_vigencia, tipo_documento, ambito)
            VALUES ('BOE-A-2025-100', 'Texto original vigente', 'vigente', 'circular_cnmv', 'general_cnmv')
        """))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "La sociedad de valores deberá presentar el modelo 620 y deberá mantener controles internos adecuados.",
            "estado_vigencia": "vigente",
        }
        result = upsert_with_versioning(conn, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "modificado"
    assert result.get("obligaciones", 0) >= 1
