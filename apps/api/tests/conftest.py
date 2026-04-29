import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"esdata_test_{os.getpid()}.sqlite3"

if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except PermissionError:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ESDATA_API_KEY", "test-secret-key")
os.environ.setdefault("MCP_API_KEY", "test-mcp-key")
os.environ.setdefault("ESDATA_ALLOW_INSECURE_TEST_AUTH", "true")

engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)

# Patch db module to use the same engine as conftest (SQLite test DB)
# This ensures seed fixtures and router queries use the same connection
_db_module = sys.modules.get("db")
if _db_module is None:
    import db as _db_module  # noqa: E402
_db_module.engine = engine
_db_module.SessionLocal = _db_module.sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _patched_db_session():
    """Context manager that replaces db_session to use the test SQLite engine."""
    db = _db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


_db_module.db_session = _db_module.contextmanager(_patched_db_session)


@pytest_asyncio.fixture
async def mcp_client():
    from main import create_app
    from services.query_audit import reset_query_audit_service

    app = create_app()
    reset_query_audit_service()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json",
                "content-type": "application/json",
            },
        ) as client:
            yield client
    reset_query_audit_service()

XBRL_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "xbrl" / "minimal_filing.xbrl"

XBRL_SCHEMA_STATEMENTS = [
    "DROP TABLE IF EXISTS xbrl_fact",
    "DROP TABLE IF EXISTS xbrl_filing",
    "DROP TABLE IF EXISTS xbrl_taxonomy",
    "DROP TABLE IF EXISTS pgc_xbrl_mapping",
    """
    CREATE TABLE xbrl_filing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        source_path TEXT NOT NULL UNIQUE,
        entity_identifier TEXT NOT NULL,
        period_start TEXT,
        period_end TEXT,
        filing_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX idx_xbrl_filing_entity_identifier ON xbrl_filing(entity_identifier)",
    "CREATE INDEX idx_xbrl_filing_period_end ON xbrl_filing(period_end)",
    """
    CREATE TABLE xbrl_fact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_id INTEGER NOT NULL REFERENCES xbrl_filing(id),
        concept TEXT NOT NULL,
        value_raw TEXT NOT NULL,
        value_numeric NUMERIC,
        unit TEXT,
        context_ref TEXT,
        period_start TEXT,
        period_end TEXT,
        entity_identifier TEXT NOT NULL,
        decimals TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (filing_id, concept, context_ref, value_raw)
    )
    """,
    "CREATE INDEX idx_xbrl_fact_filing ON xbrl_fact(filing_id)",
    "CREATE INDEX idx_xbrl_fact_entity_identifier ON xbrl_fact(entity_identifier)",
    "CREATE INDEX idx_xbrl_fact_concept ON xbrl_fact(concept)",
    "CREATE INDEX idx_xbrl_fact_period_end ON xbrl_fact(period_end)",
    """
    CREATE TABLE xbrl_taxonomy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_qname TEXT NOT NULL,
        namespace TEXT NOT NULL,
        label TEXT NOT NULL,
        label_language TEXT NOT NULL DEFAULT 'en',
        label_role TEXT NOT NULL DEFAULT 'label',
        standard TEXT,
        data_type TEXT NOT NULL DEFAULT 'xbrli:monetaryItemType',
        period_type TEXT NOT NULL DEFAULT 'duration',
        is_monetary BOOLEAN NOT NULL DEFAULT TRUE,
        is_negative_allowed BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (concept_qname, label_language, label_role)
    )
    """,
    "CREATE INDEX idx_xbrl_taxonomy_concept_qname ON xbrl_taxonomy(concept_qname)",
    "CREATE INDEX idx_xbrl_taxonomy_namespace ON xbrl_taxonomy(namespace)",
    "CREATE INDEX idx_xbrl_taxonomy_standard ON xbrl_taxonomy(standard)",
    "CREATE INDEX idx_xbrl_taxonomy_language ON xbrl_taxonomy(label_language)",
    """
    CREATE TABLE pgc_xbrl_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xbrl_concept_qname TEXT NOT NULL,
        pgc_account_codigo TEXT NOT NULL,
        confidence TEXT NOT NULL DEFAULT 'medium',
        mapping_type TEXT NOT NULL DEFAULT 'expert',
        note TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (xbrl_concept_qname, pgc_account_codigo)
    )
    """,
    "CREATE INDEX idx_pgc_xbrl_mapping_xbrl_concept ON pgc_xbrl_mapping(xbrl_concept_qname)",
    "CREATE INDEX idx_pgc_xbrl_mapping_pgc_account ON pgc_xbrl_mapping(pgc_account_codigo)",
    "CREATE INDEX idx_pgc_xbrl_mapping_confidence ON pgc_xbrl_mapping(confidence)",
    "CREATE INDEX idx_pgc_xbrl_mapping_active ON pgc_xbrl_mapping(is_active) WHERE is_active = 1",
]


def _xml_local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _coerce_numeric_value(raw_value):
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return None
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _derive_xbrl_fixture_catalog():
    root = ET.parse(XBRL_FIXTURE_PATH).getroot()

    contexts = {}
    for context in root.findall("{http://www.xbrl.org/2003/instance}context"):
        identifier = context.find("{http://www.xbrl.org/2003/instance}entity/{http://www.xbrl.org/2003/instance}identifier")
        period = context.find("{http://www.xbrl.org/2003/instance}period")
        contexts[context.attrib["id"]] = {
            "entity_identifier": identifier.text if identifier is not None else None,
            "period_start": period.findtext("{http://www.xbrl.org/2003/instance}startDate") if period is not None else None,
            "period_end": period.findtext("{http://www.xbrl.org/2003/instance}endDate") if period is not None else None,
        }

    units = {}
    for unit in root.findall("{http://www.xbrl.org/2003/instance}unit"):
        units[unit.attrib["id"]] = unit.findtext("{http://www.xbrl.org/2003/instance}measure")

    facts = []
    for child in root:
        local_name = _xml_local_name(child.tag)
        if local_name in {"context", "unit"}:
            continue
        context = contexts[child.attrib["contextRef"]]
        facts.append(
            {
                "concept": local_name,
                "value_raw": child.text,
                "value_numeric": _coerce_numeric_value(child.text),
                "unit": units.get(child.attrib.get("unitRef")),
                "context_ref": child.attrib["contextRef"],
                "period_start": context["period_start"],
                "period_end": context["period_end"],
                "entity_identifier": context["entity_identifier"],
                "decimals": child.attrib.get("decimals"),
            }
        )

    filing_period_start = next((fact["period_start"] for fact in facts if fact["period_start"]), None)
    filing_period_end = next((fact["period_end"] for fact in facts if fact["period_end"]), None)
    entity_identifier = next((fact["entity_identifier"] for fact in facts if fact["entity_identifier"]), None)

    return {
        "fixture_path": str(XBRL_FIXTURE_PATH),
        "entity_identifier": entity_identifier,
        "filing": {
            "source_name": XBRL_FIXTURE_PATH.name,
            "source_path": str(XBRL_FIXTURE_PATH),
            "entity_identifier": entity_identifier,
            "period_start": filing_period_start,
            "period_end": filing_period_end,
            "filing_type": "xbrl",
        },
        "facts": facts,
    }

PGC_CATALOG = {
    "marco": {
        "codigo": "RD1514/2021",
        "titulo": "Real Decreto 1514/2021 - Plan General de Contabilidad vigente",
        "tipo": "real_decreto",
        "anio": 2021,
        "texto": "Marco base del Plan General Contable vigente usado como referencia inicial en esdata.",
        "url_boe": "https://www.boe.es/",
    },
    "accounts": [
        {"codigo": "1", "descripcion": "Activo no corriente", "nivel": 1, "padre_codigo": None, "grupo": "1", "clase": "1", "saldo_normal": "debe", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "10", "descripcion": "Inmovilizado intangible", "nivel": 2, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "100", "descripcion": "Investigacion y desarrollo", "nivel": 3, "padre_codigo": "10", "grupo": "1", "clase": "1", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "11", "descripcion": "Inmovilizado material", "nivel": 2, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "110", "descripcion": "Terrenos y bienes naturales", "nivel": 3, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "2", "descripcion": "Activo corriente", "nivel": 1, "padre_codigo": None, "grupo": "2", "clase": "2", "saldo_normal": "debe", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "20", "descripcion": "Existencias comerciales", "nivel": 2, "padre_codigo": "2", "grupo": "2", "clase": "2", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "200", "descripcion": "Mercaderias", "nivel": 3, "padre_codigo": "20", "grupo": "2", "clase": "2", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "21", "descripcion": "Materias primas", "nivel": 2, "padre_codigo": "2", "grupo": "2", "clase": "2", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "210", "descripcion": "Materias primas", "nivel": 3, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "3", "descripcion": "Patrimonio neto", "nivel": 1, "padre_codigo": None, "grupo": "3", "clase": "3", "saldo_normal": "haber", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "30", "descripcion": "Capital y reservas", "nivel": 2, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "haber", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "300", "descripcion": "Capital social", "nivel": 3, "padre_codigo": "30", "grupo": "3", "clase": "3", "saldo_normal": "haber", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "4", "descripcion": "Pasivo corriente", "nivel": 1, "padre_codigo": None, "grupo": "4", "clase": "4", "saldo_normal": "haber", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "40", "descripcion": "Proveedores", "nivel": 2, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "haber", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "400", "descripcion": "Proveedores", "nivel": 3, "padre_codigo": "40", "grupo": "4", "clase": "4", "saldo_normal": "haber", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "43", "descripcion": "Clientes", "nivel": 2, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "430", "descripcion": "Clientes", "nivel": 3, "padre_codigo": "43", "grupo": "4", "clase": "4", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "47", "descripcion": "Administraciones Publicas", "nivel": 2, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "haber", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "472", "descripcion": "Hacienda Publica, IVA soportado", "nivel": 3, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "477", "descripcion": "Hacienda Publica, IVA repercutido", "nivel": 3, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "haber", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "5", "descripcion": "Cuentas financieras", "nivel": 1, "padre_codigo": None, "grupo": "5", "clase": "5", "saldo_normal": "debe", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "57", "descripcion": "Tesoreria", "nivel": 2, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "570", "descripcion": "Caja", "nivel": 3, "padre_codigo": "57", "grupo": "5", "clase": "5", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "572", "descripcion": "Bancos e instituciones de credito c/c vista", "nivel": 3, "padre_codigo": "57", "grupo": "5", "clase": "5", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "6", "descripcion": "Compras y gastos", "nivel": 1, "padre_codigo": None, "grupo": "6", "clase": "6", "saldo_normal": "debe", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "60", "descripcion": "Compras", "nivel": 2, "padre_codigo": "6", "grupo": "6", "clase": "6", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "600", "descripcion": "Compras de mercaderias", "nivel": 3, "padre_codigo": "60", "grupo": "6", "clase": "6", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "62", "descripcion": "Servicios exteriores", "nivel": 2, "padre_codigo": "6", "grupo": "6", "clase": "6", "saldo_normal": "debe", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "621", "descripcion": "Arrendamientos y canones", "nivel": 3, "padre_codigo": "62", "grupo": "6", "clase": "6", "saldo_normal": "debe", "tipo_cuenta": "cuenta", "nota": None},
        {"codigo": "7", "descripcion": "Ventas e ingresos", "nivel": 1, "padre_codigo": None, "grupo": "7", "clase": "7", "saldo_normal": "haber", "tipo_cuenta": "agrupacion", "nota": None},
        {"codigo": "70", "descripcion": "Ventas de mercaderias", "nivel": 2, "padre_codigo": "7", "grupo": "7", "clase": "7", "saldo_normal": "haber", "tipo_cuenta": "grupo", "nota": None},
        {"codigo": "700", "descripcion": "Ventas de mercaderias", "nivel": 3, "padre_codigo": "70", "grupo": "7", "clase": "7", "saldo_normal": "haber", "tipo_cuenta": "cuenta", "nota": None},
    ],
    "normas": [
        {"norma_ref": "NRV10", "articulo": "10", "descripcion": "Existencias valoradas al menor entre coste y valor neto realizable", "cuenta_codigo": "200"},
        {"norma_ref": "NRV12", "articulo": "12", "descripcion": "Clientes y deudores comerciales por su valor razonable inicial", "cuenta_codigo": "430"},
        {"norma_ref": "NRV14", "articulo": "14", "descripcion": "Tesoreria y equivalentes clasificados como activos financieros", "cuenta_codigo": "572"},
        {"norma_ref": "NRV16", "articulo": "16", "descripcion": "IVA soportado y repercutido como cuentas separadas del trafico", "cuenta_codigo": "472"},
    ],
    "estados_financieros": [
        {"estado": "balance", "tipo_presentacion": "activo_no_corriente", "orden": 1, "periodo": "anual", "nota_pieds": "Inmovilizado intangible, investigacion y desarrollo", "cuenta_codigo": "100"},
        {"estado": "balance", "tipo_presentacion": "activo_no_corriente", "orden": 2, "periodo": "anual", "nota_pieds": "Terrenos y bienes naturales", "cuenta_codigo": "110"},
        {"estado": "balance", "tipo_presentacion": "activo_no_corriente", "orden": 3, "periodo": "anual", "nota_pieds": "Inmovilizado material", "cuenta_codigo": "11"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 10, "periodo": "anual", "nota_pieds": "Existencias comerciales", "cuenta_codigo": "20"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 11, "periodo": "anual", "nota_pieds": "Mercaderias", "cuenta_codigo": "200"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 12, "periodo": "anual", "nota_pieds": "Materias primas", "cuenta_codigo": "210"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 13, "periodo": "anual", "nota_pieds": "Clientes", "cuenta_codigo": "43"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 14, "periodo": "anual", "nota_pieds": "Clientes", "cuenta_codigo": "430"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 15, "periodo": "anual", "nota_pieds": "Administraciones Publicas, IVA soportado", "cuenta_codigo": "472"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 16, "periodo": "anual", "nota_pieds": "Tesoreria", "cuenta_codigo": "57"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 17, "periodo": "anual", "nota_pieds": "Caja", "cuenta_codigo": "570"},
        {"estado": "balance", "tipo_presentacion": "activo_corriente", "orden": 18, "periodo": "anual", "nota_pieds": "Bancos e instituciones de credito c/c vista", "cuenta_codigo": "572"},
        {"estado": "balance", "tipo_presentacion": "patrimonio_neto", "orden": 20, "periodo": "anual", "nota_pieds": "Capital y reservas", "cuenta_codigo": "30"},
        {"estado": "balance", "tipo_presentacion": "patrimonio_neto", "orden": 21, "periodo": "anual", "nota_pieds": "Capital social", "cuenta_codigo": "300"},
        {"estado": "balance", "tipo_presentacion": "pasivo", "orden": 30, "periodo": "anual", "nota_pieds": "Proveedores", "cuenta_codigo": "40"},
        {"estado": "balance", "tipo_presentacion": "pasivo", "orden": 31, "periodo": "anual", "nota_pieds": "Proveedores", "cuenta_codigo": "400"},
        {"estado": "balance", "tipo_presentacion": "pasivo", "orden": 32, "periodo": "anual", "nota_pieds": "Administraciones Publicas, IVA repercutido", "cuenta_codigo": "477"},
        {"estado": "pyg", "tipo_presentacion": "gastos", "orden": 10, "periodo": "anual", "nota_pieds": "Compras de mercaderias", "cuenta_codigo": "600"},
        {"estado": "pyg", "tipo_presentacion": "gastos", "orden": 11, "periodo": "anual", "nota_pieds": "Servicios exteriores", "cuenta_codigo": "62"},
        {"estado": "pyg", "tipo_presentacion": "gastos", "orden": 12, "periodo": "anual", "nota_pieds": "Arrendamientos y canones", "cuenta_codigo": "621"},
        {"estado": "pyg", "tipo_presentacion": "ingresos", "orden": 20, "periodo": "anual", "nota_pieds": "Ventas de mercaderias", "cuenta_codigo": "700"},
    ],
    "referencias_fiscales": [
        {"modelo": "IRPF", "casilla": "001", "ejercicio": "anual", "nota": "Retenciones e ingresos a cuenta de proveedores", "cuenta_codigo": "400"},
        {"modelo": "IRPF", "casilla": "190", "ejercicio": "anual", "nota": "Ingresos financieros a cuenta", "cuenta_codigo": "572"},
        {"modelo": "IVA", "casilla": "00", "ejercicio": "trimestral", "nota": "Cuota IVA soportado", "cuenta_codigo": "472"},
        {"modelo": "IVA", "casilla": "01", "ejercicio": "trimestral", "nota": "Cuota IVA repercutido", "cuenta_codigo": "477"},
        {"modelo": "IRPF", "casilla": "180", "ejercicio": "anual", "nota": "Retenciones sobre servicios exteriores", "cuenta_codigo": "621"},
        {"modelo": "IS", "casilla": "001", "ejercicio": "anual", "nota": "Base imponible Impuesto Sociedades", "cuenta_codigo": "700"},
    ],
    "referencias_aeat": [
        {"modelo_id": 100, "cuenta_codigo": "400", "campana": "2025", "nota": "IRPF - Retenciones a proveedores y servicios exteriores"},
        {"modelo_id": 100, "cuenta_codigo": "477", "campana": "2025", "nota": "IRPF - Retenciones y ingresos a cuenta de clientes"},
        {"modelo_id": 100, "cuenta_codigo": "572", "campana": "2025", "nota": "IRPF - Ingresos financieros y cuentas bancarias"},
        {"modelo_id": 100, "cuenta_codigo": "621", "campana": "2025", "nota": "IRPF - Retenciones sobre arrendamientos y servicios"},
        {"modelo_id": 303, "cuenta_codigo": "472", "campana": "2025", "nota": "IVA 303 - IVA soportado (casillas 040-043)"},
        {"modelo_id": 303, "cuenta_codigo": "477", "campana": "2025", "nota": "IVA 303 - IVA repercutido (casillas 001-004)"},
        {"modelo_id": 303, "cuenta_codigo": "572", "campana": "2025", "nota": "IVA 303 - Cuota a ingresar o compensar"},
        {"modelo_id": 200, "cuenta_codigo": "472", "campana": "2025", "nota": "IS 200 - Gastos deducibles e IVA soportado"},
        {"modelo_id": 200, "cuenta_codigo": "700", "campana": "2025", "nota": "IS 200 - Base imponible por ventas e ingresos"},
        {"modelo_id": 200, "cuenta_codigo": "600", "campana": "2025", "nota": "IS 200 - Compras y gastos deducibles"},
    ],
}

PGC_SCHEMA_STATEMENTS = [
    "DROP TABLE IF EXISTS pgc_cuenta_modelo_aeat_ref",
    "DROP TABLE IF EXISTS pgc_cuenta_fiscal_ref",
    "DROP TABLE IF EXISTS pgc_estado_financiero",
    "DROP TABLE IF EXISTS pgc_norma_valoracion",
    "DROP TABLE IF EXISTS pgc_cuenta",
    "DROP TABLE IF EXISTS pgc_marco",
    """
    CREATE TABLE pgc_marco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        anio INTEGER,
        texto TEXT,
        url_boe TEXT,
        vigente INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE pgc_norma_valoracion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marco_id INTEGER,
        cuenta_id INTEGER,
        norma_ref TEXT NOT NULL,
        articulo TEXT,
        descripcion TEXT,
        tipo_operacion TEXT,
        debe_haber TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE pgc_cuenta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        descripcion TEXT NOT NULL,
        nivel INTEGER NOT NULL,
        padre_codigo TEXT,
        grupo TEXT,
        clase TEXT,
        saldo_normal TEXT,
        tipo_cuenta TEXT,
        vigente INTEGER NOT NULL DEFAULT 1,
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT
    )
    """,
    """
    CREATE TABLE pgc_estado_financiero (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER,
        estado TEXT NOT NULL,
        tipo_presentacion TEXT,
        orden INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        importe_base NUMERIC(18,2),
        importe_anterior NUMERIC(18,2),
        nota_pieds TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE pgc_cuenta_fiscal_ref (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER NOT NULL,
        modelo TEXT NOT NULL,
        casilla TEXT,
        ejercicio TEXT,
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(cuenta_id, modelo, casilla, ejercicio)
    )
    """,
    """
    CREATE TABLE pgc_cuenta_modelo_aeat_ref (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER NOT NULL,
        modelo_id INTEGER NOT NULL,
        campana TEXT,
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def _seed_pgc(conn):
    conn.execute(
        text(
            """
            INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
            VALUES (:codigo, :titulo, :tipo, :anio, :texto, :url_boe, 1)
            """
        ),
        PGC_CATALOG["marco"],
    )

    conn.execute(
        text(
            """
            INSERT INTO pgc_cuenta (
                codigo, descripcion, nivel, padre_codigo, grupo, clase, saldo_normal, tipo_cuenta, vigente, nota
            ) VALUES (
                :codigo, :descripcion, :nivel, :padre_codigo, :grupo, :clase, :saldo_normal, :tipo_cuenta, 1, :nota
            )
            """
        ),
        PGC_CATALOG["accounts"],
    )

    for norma in PGC_CATALOG["normas"]:
        conn.execute(
            text(
                """
                INSERT INTO pgc_norma_valoracion (marco_id, cuenta_id, norma_ref, articulo, descripcion)
                SELECT m.id, c.id, :norma_ref, :articulo, :descripcion
                FROM pgc_marco m, pgc_cuenta c
                WHERE m.codigo = :marco_codigo AND c.codigo = :cuenta_codigo
                """
            ),
            {**norma, "marco_codigo": PGC_CATALOG["marco"]["codigo"]},
        )

    for estado in PGC_CATALOG["estados_financieros"]:
        cuenta_id = None
        if estado.get("cuenta_codigo"):
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": estado["cuenta_codigo"]},
            ).scalar_one_or_none()
        conn.execute(
            text(
                """
                INSERT INTO pgc_estado_financiero (cuenta_id, estado, tipo_presentacion, orden, periodo, nota_pieds)
                VALUES (:cuenta_id, :estado, :tipo_presentacion, :orden, :periodo, :nota_pieds)
                """
            ),
            {
                "cuenta_id": cuenta_id,
                "estado": estado["estado"],
                "tipo_presentacion": estado["tipo_presentacion"],
                "orden": estado["orden"],
                "periodo": estado["periodo"],
                "nota_pieds": estado["nota_pieds"],
            },
        )

    for ref in PGC_CATALOG["referencias_fiscales"]:
        cuenta_id = None
        if ref.get("cuenta_codigo"):
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": ref["cuenta_codigo"]},
            ).scalar_one_or_none()
        conn.execute(
            text(
                """
                INSERT INTO pgc_cuenta_fiscal_ref (cuenta_id, modelo, casilla, ejercicio, nota)
                VALUES (:cuenta_id, :modelo, :casilla, :ejercicio, :nota)
                """
            ),
            {
                "cuenta_id": cuenta_id,
                "modelo": ref["modelo"],
                "casilla": ref["casilla"],
                "ejercicio": ref["ejercicio"],
                "nota": ref["nota"],
            },
        )

    for ref in PGC_CATALOG["referencias_aeat"]:
        cuenta_id = None
        if ref.get("cuenta_codigo"):
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": ref["cuenta_codigo"]},
            ).scalar_one_or_none()
        conn.execute(
            text(
                """
                INSERT INTO pgc_cuenta_modelo_aeat_ref (cuenta_id, modelo_id, campana, nota)
                VALUES (:cuenta_id, :modelo_id, :campana, :nota)
                """
            ),
            {
                "cuenta_id": cuenta_id,
                "modelo_id": ref["modelo_id"],
                "campana": ref["campana"],
                "nota": ref["nota"],
            },
        )


def _seed_xbrl(conn):
    xbrl_fixture_catalog = _derive_xbrl_fixture_catalog()
    conn.execute(
        text(
            """
            INSERT INTO xbrl_filing (source_name, source_path, entity_identifier, period_start, period_end, filing_type)
            VALUES (:source_name, :source_path, :entity_identifier, :period_start, :period_end, :filing_type)
            """
        ),
        xbrl_fixture_catalog["filing"],
    )

    filing_id = conn.execute(
        text("SELECT id FROM xbrl_filing WHERE source_path = :source_path"),
        {"source_path": xbrl_fixture_catalog["filing"]["source_path"]},
    ).scalar_one()

    for fact in xbrl_fixture_catalog["facts"]:
        conn.execute(
            text(
                """
                INSERT INTO xbrl_fact (
                    filing_id, concept, value_raw, value_numeric, unit, context_ref,
                    period_start, period_end, entity_identifier, decimals
                ) VALUES (
                    :filing_id, :concept, :value_raw, :value_numeric, :unit, :context_ref,
                    :period_start, :period_end, :entity_identifier, :decimals
                )
                """
            ),
            {"filing_id": filing_id, **fact},
        )

STATEMENTS = [
    """
    CREATE TABLE norma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        boe_id TEXT UNIQUE NOT NULL,
        eli_uri TEXT UNIQUE,
        jurisdiccion TEXT NOT NULL,
        tipo_fuente TEXT NOT NULL,
        tipo_documento TEXT NOT NULL,
        ambito TEXT NOT NULL,
        estado_cobertura TEXT NOT NULL,
        regulacion_relacionada TEXT,
        vigente_desde TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT
    )
    """,
    """
    CREATE TABLE articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        norma_id INTEGER NOT NULL REFERENCES norma(id),
        numero TEXT NOT NULL,
        titulo TEXT,
        contenido TEXT,
        tipo TEXT NOT NULL,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT,
        UNIQUE (norma_id, numero)
    )
    """,
    """
    CREATE TABLE version_articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        texto TEXT NOT NULL,
        vigente_desde TEXT NOT NULL,
        vigente_hasta TEXT,
        boe_bloque_id TEXT
    )
    """,
    """
    CREATE TABLE materia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        etiqueta TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE articulo_materia (
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        materia_id INTEGER NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
        relevancia INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (articulo_id, materia_id)
    )
    """,
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
        estado_vigencia TEXT,
        regulacion_relacionada TEXT,
        ambito_tematico TEXT
    )
    """,
    """
    INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, regulacion_relacionada, vigente_desde)
    VALUES
        ('LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740', 'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe', 'ley', 'tributario', 'ingestada', NULL, '1993-01-01'),
        ('LIRPF', 'Ley del Impuesto sobre la Renta de las Personas Fisicas', 'BOE-A-2006-20764', 'https://www.boe.es/eli/es/l/2006/11/23/35', 'es', 'boe', 'ley', 'tributario', 'ingestada', NULL, '2007-01-01'),
        ('LIS', 'Ley del Impuesto sobre Sociedades', 'BOE-A-2014-12328', 'https://www.boe.es/eli/es/l/2014/11/27/27', 'es', 'boe', 'ley', 'tributario', 'ingestada', NULL, '2015-01-01'),
        ('LGT', 'Ley General Tributaria', 'BOE-A-2003-23186', 'https://www.boe.es/eli/es/l/2003/12/17/58', 'es', 'boe', 'ley', 'tributario', 'ingestada', NULL, '2004-01-01'),
        ('ITPAJD', 'Ley del ITPAJD', 'BOE-A-1993-25359', 'https://www.boe.es/eli/es/rdl/1993/09/24/1', 'es', 'boe', 'real_decreto_legislativo', 'tributario', 'ingestada', NULL, '1993-09-25'),
        ('IRNR', 'RDL 5/2004 — Ley del IRNR', 'BOE-A-2004-4527', 'https://www.boe.es/eli/es/rdl/2004/12/03/5', 'es', 'boe', 'real_decreto_legislativo', 'tributario', 'ingestada', NULL, '2004-12-03'),
        ('RIRNR', 'RD 435/1995 — Reglamento del IRNR', 'BOE-A-1995-7256', 'https://www.boe.es/eli/es/rd/1995/03/27/435', 'es', 'boe', 'real_decreto', 'tributario', 'ingestada', NULL, '1995-04-01'),
        ('IIEE', 'Ley de Impuestos Especiales', 'BOE-A-1992-28741', 'https://www.boe.es/eli/es/l/1992/12/28/38', 'es', 'boe', 'ley', 'tributario', 'ingestada', NULL, '1993-01-01'),
        ('HL', 'Ley de Haciendas Locales', 'BOE-A-2004-4214', 'https://www.boe.es/eli/es/rdl/2004/03/05/2', 'es', 'boe', 'real_decreto_legislativo', 'tributario_local', 'ingestada', NULL, '2004-03-09'),
        ('DAC6', 'Ley 10/2020 de transposicion DAC6', 'BOE-A-2020-11325', 'https://www.boe.es/eli/es/l/2020/12/29/10', 'es', 'boe', 'ley', 'tributario_internacional', 'ingestada', 'dac_directives', '2020-12-30'),
        ('DAC6RD', 'Real Decreto 243/2021 DAC6', 'BOE-A-2021-5090', 'https://www.boe.es/eli/es/rd/2021/04/06/243', 'es', 'boe', 'real_decreto', 'tributario_internacional', 'ingestada', 'dac_directives', '2021-04-07'),
        ('DAC6EU', 'Directiva (UE) 2018/822', 'EUR-Lex-32018L0822', 'https://eur-lex.europa.eu/eli/dir/2018/822/oj', 'ue', 'eurlex', 'directiva_ue', 'tributario_internacional', 'referenciada', 'dac_directives', '2018-06-25'),
        ('DAC7', 'Directiva (UE) 2020/284 — DAC7', 'EUR-Lex-32020L0284', 'https://eur-lex.europa.eu/eli/dir/2020/284/oj', 'ue', 'eurlex', 'directiva_ue', 'tributario_internacional', 'referenciada', 'dac_directives', '2020-12-18'),
        ('DAC1', 'Directiva (UE) 77/780 — DAC1', 'EUR-Lex-31977L0780', 'https://eur-lex.europa.eu/eli/dir/1977/780/oj', 'ue', 'eurlex', 'directiva_ue', 'tributario_internacional', 'referenciada', 'dac_directives', '1977-11-12'),
        ('LEY13_2023', 'Ley 13/2023, de 22 de noviembre, de regulacion de la inteligencia artificial', 'BOE-A-2023-23080', 'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-23080', 'es', 'boe', 'ley', 'ia_regulacion', 'activo', NULL, '2023-11-23')
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '91', 'Tipos impositivos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '14', 'Rentas exentas', 'articulo' FROM norma WHERE codigo = 'IRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '31', 'Rendimientos del capital mobiliario — Dividendos e intereses', 'articulo' FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '32', 'Retenciones e ingresos a cuenta — Tipos de retencion', 'articulo' FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '33', 'Ganancias patrimoniales obtenidas en Espana', 'articulo' FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '34', 'Retencion en ganancias patrimoniales', 'articulo' FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '35', 'Convenios de doble imposicion', 'articulo' FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '7', 'Hecho imponible', 'articulo' FROM norma WHERE codigo = 'ITPAJD'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '60', 'Impuestos especiales', 'articulo' FROM norma WHERE codigo = 'IIEE'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '20', 'Tributos locales', 'articulo' FROM norma WHERE codigo = 'HL'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '206 bis', 'Obligaciones de informacion', 'articulo' FROM norma WHERE codigo = 'DAC6'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '30', 'Rendimientos del capital mobiliario', 'articulo' FROM norma WHERE codigo = 'LIRPF'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id,
           'Articulo 91. El tipo reducido se aplica a alimentos, productos sanitarios y bienes de primera necesidad conforme a los tipos impositivos reducidos.',
           '1993-01-01',
           NULL,
           'a91'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id,
           'Articulo 14. Rentas obtenidas sin mediación de establecimiento permanente exentas en los supuestos legalmente previstos.',
           '2004-12-03',
           NULL,
           'irnr-14'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 7. Constituye el hecho imponible la transmision patrimonial onerosa y otras transmisiones sujetas al ITPAJD.', '1993-09-25', NULL, 'itpajd-7'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'ITPAJD' AND a.numero = '7'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 60. Impuestos especiales sobre hidrocarburos y otros productos objeto de gravamen especifico.', '1993-01-01', NULL, 'iiee-60'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'IIEE' AND a.numero = '60'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 20. Tasas y tributos locales.', '2004-03-09', NULL, 'hl-20'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'HL' AND a.numero = '20'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 206 bis. Obligaciones de informacion de mecanismos transfronterizos.', '2020-01-01', NULL, 'dac6-206bis'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6' AND a.numero = '206 bis'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 30. Rendimientos del capital mobiliario. Constituyen rendimientos del capital mobiliario los que obtengan los contribuyentes por la cesion de capitales propios, incluyendo especialmente los derivados de participaciones en instrumentos de patrimonio, dividendos, intereses de depositos y cuentas, rentas de capital de deudas y demas rendimientos financieros.', '2007-01-01', NULL, 'lirpf-30'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '30'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 31. Rendimientos del capital mobiliario. Constituyen rendimientos del capital mobiliario los dividendos, las rentas derivadas de la participacion en inversiones colectivas y los intereses y demas rendimientos equivalentes obtenidos por no residentes sin establecimiento permanente en Espana.', '1995-04-01', NULL, 'rirnr-31'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '31'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 32. Tipos de retencion. Para los rendimientos del capital mobiliario derivados de dividendos e intereses, los tipos de retencion seran: a) 15 por 100 cuando el beneficiario sea residente en un Estado miembro de la Union Europea o del Espacio Economico Europeo con el que exista intercambio de informacion. b) 24 por 100 para el resto de casos. c) El tipo previsto en el convenio de doble imposicion cuando exista y sea mas favorable.', '1995-04-01', NULL, 'rirnr-32'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '32'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 33. Ganancias patrimoniales obtenidas en Espana. Constituyen ganancias patrimoniailes las obtenidas por la transmision de bienes o derechos por los no residentes sin establecimiento permanente, cuando los bienes o derechos tengan su situacion en territorio espanol.', '1995-04-01', NULL, 'rirnr-33'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '33'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 34. Retencion en ganancias patrimoniales. La retencion sobre las ganancias patrimoniales obtenidas por no residentes sera del 19 por 100 en termin generales. Cuando la ganancia derive de la transmision de valores negociados en mercados organizados de valores de la Union Europea, la retencion sera del 7 por 100.', '1995-04-01', NULL, 'rirnr-34'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '34'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 35. Convenios de doble imposicion. Los tipos de retencion previstos en este reglamento se aplicaran sin perjuicio de lo establecido en los convenios para evitar la doble imposicion fiscal celebrados por Espana con otros Estados. Cuando el convenio establezca un tipo de retencion inferior, se aplicara el tipo mas favorable para el contribuyente.', '1995-04-01', NULL, 'rirnr-35'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '35'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '1', 'Obligacion de informacion — Intermediarios', 'articulo' FROM norma WHERE codigo = 'DAC6'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '6', 'Definiciones', 'articulo' FROM norma WHERE codigo = 'DAC6'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '1', 'Obligaciones de informacion — Plataformas digitales', 'articulo' FROM norma WHERE codigo = 'DAC7'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '1', 'Asistencia administrativa mutua', 'articulo' FROM norma WHERE codigo = 'DAC1'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '5', 'Principio general — Aplicacion de IA', 'articulo' FROM norma WHERE codigo = 'LEY13_2023'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 5. Los desarrolladores y despliegadores de sistemas de IA de alto riesgo tendran la obligacion de garantizar la trazabilidad de los procesos de desarrollo y monitoreo continuo durante la operacion.', '2023-11-23', NULL, 'ley13-5'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LEY13_2023' AND a.numero = '5'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 1. Los intermediarios tendran la obligacion de reportar los esquemas transfronterizos potencialmente relevantes al agente de gestion tributaria en un plazo de cinco dias habiles desde que el esquema sea disponible, conforme a las directivas DAC6.', '2020-12-30', NULL, 'dac6-1'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6' AND a.numero = '1'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 6. A efectos de esta ley, se entiende por intermediario cualquier persona fisica o juridica que promueva o preste servicios relativos a los mecanismos transfronterizos.', '2020-12-30', NULL, 'dac6-6'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC6' AND a.numero = '6'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 1. Las plataformas digitales deberan facilitar informacion sobre los ingresos de los proveedores de servicios conforme a DAC7.', '2020-12-18', NULL, 'dac7-1'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC7' AND a.numero = '1'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 1. Los estados miembros se prestaran asistencia administrativa mutua en el ambito fiscal.', '1977-11-12', NULL, 'dac1-1'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'DAC1' AND a.numero = '1'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 5. Los sistemas de inteligencia artificial se regiran por los principios de transparencia, no discriminacion y supervision humana conforme a esta ley.', '2023-06-01', NULL, 'ley13-5'
    FROM articulo a JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LEY13_2023' AND a.numero = '5'
    """,
    """
    INSERT INTO materia (slug, etiqueta)
    VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
    """,
    """
    INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
    SELECT a.id, m.id, 1
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    JOIN materia m ON m.slug = 'tipo-reducido-iva'
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO documento_interpretativo (tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente)
    VALUES
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Consulta DGT sobre tipo reducido', 'Consulta sobre la aplicacion del tipo reducido del IVA conforme al articulo 91 de la Ley 37/1992.', 'https://example.invalid/dgt/V0000-26'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0091-18', '2018-03-15', 'Dividendos y retenciones en IRPF', 'Los dividendos y distribuciones de beneficios tributan como rendimientos del capital mobiliario en el IRPF. El tipo de retencion aplicable sobre dividendos sera del 19 por ciento conforme al articulo 44 del RIRPF. La retencion practica por cuenta del contribuyente corresponde a la entidad distribuidora.', 'https://example.invalid/dgt/V0091-18'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V2424-20', '2020-10-05', 'Imputacion temporal rendimientos mobiliarios', 'La imputacion de los rendimientos del capital mobiliario se realiza en el periodo impositivo en que se devengan conforme al articulo 30 de la Ley 35/2006 del IRPF. Para los dividendos y entregas a cuenta, el rendimiento se devenga en el momento del pago o entrega, independientemente de cuando se haya aprobado la distribucion de beneficios por la junta general. La imputacion temporal debe respetar el principio de devengo para todos los rendimientos del capital mobiliario.', 'https://example.invalid/dgt/V2424-20'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V2965-17', '2017-11-20', 'Retenciones 19 por ciento dividendos', 'El tipo de retencion aplicable sobre los dividendos y distribuciones de beneficios sera del 19 por ciento para los contribuyentes residentes en el IRPF, conforme al articulo 44 del Real Decreto 439/1990 (RIRPF). Este tipo se aplica sobre el importe bruto del dividendo. La retencion practica corresponde a quien distribuye el dividendo y debe ingresarse a cuenta del IRPF del beneficiario. Para no residentes, el tipo puede variar segun convenios de doble imposicion.', 'https://example.invalid/dgt/V2965-17'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0092-19', '2019-05-20', 'Intereses de cuentas bancarias', 'Los intereses generados por depositos bancarios constituyen rendimientos del capital mobiliario. El agente de retencion aplicara un tipo del 19 por ciento sobre los rendimientos del capital mobiliario derivados de cuentas bancarias.', 'https://example.invalid/dgt/V0092-19'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0100-20', '2020-01-10', 'Rendimientos de fondos de inversion', 'Las distribuciones de fondos de inversion se consideran rendimientos del capital mobiliario. Los rendimientos mobiliarios obtenidos por residentes tendran retencion practica segun los tipos del articulo 44 del RIRPF.', 'https://example.invalid/dgt/V0100-20'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0200-21', '2021-06-15', 'Retenciones sobre dividendo anticipado', 'El dividendo anticipado genera un rendimiento del capital mobiliario en el momento del pago. La retencion practica se calcula sobre el importe bruto del dividendo al tipo del 19 por ciento. El contribuyente podra imputar el rendimiento negativo en el periodo impositivo correspondiente.', 'https://example.invalid/dgt/V0200-21'),
        ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0300-22', '2022-09-01', 'Intereses por depositos a plazo fijo', 'Los intereses de depositos a plazo fijo constituyen rendimientos mobiliarios. El banco actuara como agente de retencion aplicando el 19 por ciento sobre el rendimiento del capital mobiliario. La retencion es ingirable a cuenta del IRPF.', 'https://example.invalid/dgt/V0300-22'),
        ('circular_cnmv', 'CNMV', 'es', 'cnmv', 'reporting_financiero', 'BOE-A-2009-133', '2009-01-02', 'Circular 9/2008 de la CNMV', 'Normas contables, estados de información reservada y pública y cuentas anuales. Estados de información reservada para entidades supervisadas.', 'https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133'),
        ('formulario_sepblac', 'SEPBLAC', 'es', 'sepblac', 'aml_cft_reporting', 'SEPBLAC-MODELO-19', '2026-04-16', 'Comunicación por indicio - Modelo 19 SEPBLAC', 'Procedimiento para la comunicación por indicio y formulario oficial Modelo 19 SEPBLAC.', 'https://www.sepblac.es/es/'),
        ('convocatoria_bdns', 'BDNS', 'es', 'bdns', 'subvenciones', 'BDNS-749075-1034404', '2025-02-01', 'Convocatoria de becas 2025', 'Convocatoria publica de becas y ayudas al estudio para el curso 2025.', 'https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075'),
        ('nombramiento', 'BORME', 'es', 'borme', 'mercantil', 'BORME-A-2025-55-37', '2025-03-01', 'Nombramientos y reelecciones societarias', 'Se publican nombramientos y otras modificaciones societarias en el BORME para Alvarez Garcia Ganaderia, S.L. y Murillo & Barrero, Sociedad Limitada.', 'https://www.boe.es/borme/dias/2025/03/01/pdfs/BORME-A-2025-55-37.pdf'),
        ('sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'tributario', 'STS-2847/2025', '2025-06-15', 'Sentencia 2847/2025 — Trib Supremo', 'Sentencia del Tribunal Supremo sobre la aplicacion del tipo reducido del IVA en servicios de restauracion.', 'https://example.invalid/cendoj/STS-2847-2025'),
        ('reglamento', 'UE', 'ue', 'eurlex', 'mercado_interior', 'EUR-Lex-32020R548', '2020-04-17', 'Reglamento (UE) 2020/548', 'Reglamento sobre medidas de solidaridad en el mercado interior y estabilidad financiera.', 'https://example.invalid/eurlex/EUR-Lex-32020P0548'),
        ('informe_bde', 'Banco de España', 'es', 'bde', 'estabilidad_financiera', 'BDE-IB-2025-01', '2025-03-10', 'Informe Bde 1/2025', 'Informe sobre estabilidad financiera y politica monetaria del Banco de Espana.', 'https://example.invalid/bde/BDE-IB-2025-01'),
        ('resolucion_aepd', 'AEPD', 'es', 'aepd', 'proteccion_datos', 'AEPD-R-2025-1234', '2025-02-20', 'Resolucion AEPD 1234/2025', 'Resolucion sobre proteccion de datos y derechos de arrendatarios en ficheros de datos.', 'https://example.invalid/aepd/AEPD-R-2025-1234'),
        ('sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'jurisprudencia_tributaria', 'STS-3301/2025', '2025-09-10', 'STS 3301/2025 — IVA restauracion', 'Sentencia sobre aplicacion del tipo reducido del IVA en restauracion.', 'https://example.invalid/cendoj/STS-3301-2025'),
        ('sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'jurisprudencia_pbcft', 'STS-1100/2025', '2025-08-20', 'STS 1100/2025 — LP indicios', 'Sentencia sobre deberes de comunicacion de indicios de lavado.', 'https://example.invalid/cendoj/STS-1100-2025'),
        ('sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'jurisprudencia_mercantil_regulatoria', 'STS-2200/2025', '2025-07-15', 'STS 2200/2025 — Comisiones MiFID', 'Sentencia sobre comisiones de preferencia e indiferencia bajo MiFID.', 'https://example.invalid/cendoj/STS-2200-2025'),
        ('auto', 'Audiencia Nacional', 'es', 'cendoj', 'jurisprudencia_mercantil_regulatoria', 'AN-445/2025', '2025-06-01', 'AN 445/2025 — Ejecucion preferente', 'Auto sobre criterios de ejecucion preferente de ordenes.', 'https://example.invalid/cendoj/AN-445-2025'),
        ('reglamento', 'Union Europea', 'ue', 'eurlex', 'jurisprudencia_tributaria', 'EUR-Lex-32020R549', '2020-05-01', 'Reglamento UE 2020/549 — IVA', 'Reglamento sobre regulacion del IVA en servicios digitales.', 'https://example.invalid/eurlex/EUR-Lex-32020P0549'),
        ('sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'jurisprudencia_pbcft', 'STS-3456/2024', '2024-04-10', 'STS 3456/2024 — LPFT', 'Sentencia sobre comunicacion de indicios de lavado a SEPBLAC.', 'https://example.invalid/cendoj/STS-3456-2024')
    """,
    """
    CREATE TABLE nota_editorial_interna (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        resumen_ejecutivo TEXT,
        contexto TEXT,
        impacto_practico TEXT,
        advertencias TEXT,
        fuente_oficial_referencia TEXT,
        documento_origen_id INTEGER REFERENCES documento_interpretativo(id) ON DELETE SET NULL,
        autor_id TEXT NOT NULL,
        revisor_id TEXT,
        estado TEXT NOT NULL DEFAULT 'borrador',
        tipo_contenido TEXT NOT NULL DEFAULT 'resumen_interno',
        fecha_creacion DATE NOT NULL DEFAULT CURRENT_DATE,
        fecha_revision DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE posicion_interpretativa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        contenido TEXT,
        fuente_oficial_referencia TEXT,
        documento_origen_id INTEGER REFERENCES documento_interpretativo(id) ON DELETE SET NULL,
        autor_id TEXT NOT NULL,
        revisor_id TEXT,
        estado TEXT NOT NULL DEFAULT 'borrador',
        version INTEGER NOT NULL DEFAULT 1,
        vigencia_desde DATE,
        vigencia_hasta DATE,
        version_anterior_id INTEGER,
        fecha_creacion DATE NOT NULL DEFAULT CURRENT_DATE,
        fecha_revision DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (version_anterior_id) REFERENCES posicion_interpretativa(id)
    )
    """,
    """
    INSERT INTO nota_editorial_interna (
        titulo, resumen_ejecutivo, contexto, impacto_practico,
        fuente_oficial_referencia, documento_origen_id,
        autor_id, estado, tipo_contenido
    ) VALUES (
        'Resumen operativo: Circular CNMV 9/2008',
        'Normas contables y estados de información para entidades supervisadas.',
        'Aplicable a todas las sociedades de valores.',
        'Las sociedades de valores deben preparar estados de información reservada adicionales.',
        'BOE-A-2009-133',
        (SELECT id FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133' LIMIT 1),
        'compliance',
        'vigente',
        'resumen_interno'
    )
    """,
    """
    INSERT INTO posicion_interpretativa (
        titulo, descripcion, contenido, fuente_oficial_referencia,
        autor_id, estado, version, vigencia_desde
    ) VALUES (
        'Criterio interno: adecuación MiFID II',
        'Criterio sobre adecuación (suitability) de MiFID II en servicios de asesoría.',
        'Se requiere documentar la adecuación de la recomendación al perfil del cliente.',
        'eurl:2014:65',
        'compliance',
        'vigente',
        1,
        '2026-05-01'
    )
    """,
    """
    CREATE TABLE empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        domicilio TEXT,
        fuente_inicial TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT,
        UNIQUE (nombre)
    )
    """,
    """
    CREATE TABLE documento_empresa (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        rol TEXT NOT NULL,
        confianza_extraccion REAL,
        nota TEXT,
        PRIMARY KEY (documento_id, empresa_id, rol)
    )
    """,
    """
    CREATE TABLE entity_identifiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        lei TEXT,
        nombre_legal TEXT,
        pais CHAR(2),
        estado TEXT NOT NULL DEFAULT 'active',
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        vlei_status TEXT,
        vlei_cred_url TEXT,
        fuente_ref TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (empresa_id, lei)
    )
    """,
    """
    CREATE TABLE entity_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        alias TEXT NOT NULL,
        alias_normalizado TEXT NOT NULL,
        fuente TEXT NOT NULL,
        confianza REAL NOT NULL DEFAULT 0.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE ownership_share (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        titular_id INTEGER NOT NULL,
        titular_tipo TEXT NOT NULL CHECK (titular_tipo IN ('empresa', 'persona')),
        titular_nombre TEXT NOT NULL,
        porcentaje NUMERIC(5,2) NOT NULL,
        tipo_participacion TEXT NOT NULL DEFAULT 'directa' CHECK (tipo_participacion IN ('directa', 'indirecta')),
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT NOT NULL,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE ownership_relation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_origen_id INTEGER NOT NULL REFERENCES empresa(id),
        empresa_destino_id INTEGER NOT NULL REFERENCES empresa(id),
        tipo_relacion TEXT NOT NULL CHECK (tipo_relacion IN (
            'control', 'participacion_mayoritaria', 'participacion_significativa',
            'absorbente', 'absorbida', 'escindente', 'escindida',
            'filial', 'matriz', 'equivalencia', 'joint_venture',
            'representante_legal', 'administrador', 'grupo_economico'
        )),
        porcentaje NUMERIC(5,2),
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT NOT NULL,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id),
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (empresa_origen_id, empresa_destino_id, tipo_relacion, vigencia_desde)
    )
    """,
    """
    CREATE TABLE ubo_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        nombre_persona TEXT NOT NULL,
        nacionalidad TEXT,
        fecha_nacimiento TEXT,
        pais_residencia TEXT,
        tipo_ubo TEXT NOT NULL CHECK (tipo_ubo IN (
            'titular_poder', 'titular_propiedad', 'control_por_otros_medios',
            'administrador_legal', 'representante'
        )),
        porcentaje_control NUMERIC(5,2),
        umbral_superado TEXT,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT NOT NULL,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id),
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE documento_articulo (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        metodo_enlace TEXT NOT NULL,
        confianza_enlace REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, articulo_id)
    )
    """,
    """
    CREATE TABLE sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        bloques_processed INTEGER,
        articulos_upserted INTEGER,
        documentos_processed INTEGER,
        documentos_upserted INTEGER,
        doctrina_links_created INTEGER,
        error_msg TEXT,
        rows_processed INTEGER,
        errors INTEGER DEFAULT 0,
        duration_ms INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_regulatoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        fuente TEXT NOT NULL,
        organismo_emisor TEXT NOT NULL,
        tipo_obligacion TEXT NOT NULL,
        sujeto_obligado TEXT NOT NULL,
        periodicidad TEXT,
        reporte_modelo TEXT,
        ambito TEXT NOT NULL,
        estado_vigencia TEXT NOT NULL,
        documento_origen_tipo TEXT NOT NULL,
        documento_origen_ref TEXT NOT NULL,
        seccion_origen TEXT,
        anexo_origen TEXT,
        nota TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        plazo_dias INTEGER,
        frecuencia_presentacion TEXT,
        ventana_presentacion TEXT,
        trigger_presentacion TEXT,
        canal_presentacion TEXT,
        obligados_resumen TEXT,
        sancion_min NUMERIC(10,2),
        sancion_max NUMERIC(10,2),
        recargo_voluntario TEXT,
        recargo_involuntario TEXT,
        interes_demora TEXT,
        prescripcion_anos INTEGER,
        deposito_previo TEXT,
        fuentes_operativas TEXT,
        ultima_actualizacion TEXT,
        origen_metadato TEXT,
        estado_metadato TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_documento (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id) ON DELETE CASCADE,
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        tipo_relacion TEXT NOT NULL,
        PRIMARY KEY (obligacion_id, documento_id)
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'CNMV-IR-RESERVADA',
        'Remitir información reservada periódica a la CNMV',
        'cnmv',
        'CNMV',
        'remision_informacion',
        'empresa_servicios_inversion',
        'periodica',
        'estados_reservados',
        'reporting_regulatorio',
        'vigente',
        'circular_cnmv',
        'BOE-A-2009-133',
        NULL,
        NULL,
        'Obligación base derivada del corpus CNMV para el primer slice de obligaciones.',
        NULL, 'mensual', 'primeros_20_dias_periodo_siguiente', 'fin_mes',
        'electronica', 'Empresas de servicios de inversión', 3000, 60000000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'SEPBLAC-INDICIO-M19',
        'Comunicar operativa sospechosa por indicio mediante Modelo 19',
        'sepblac',
        'SEPBLAC',
        'comunicacion_indicio',
        'sujeto_obligado_pbcft',
        'eventual',
        'modelo_19',
        'aml_cft_reporting',
        'vigente',
        'formulario_sepblac',
        'SEPBLAC-MODELO-19',
        '15.5',
        NULL,
        'Obligación base del primer slice operativo SEPBLAC.',
        15, 'eventual', '1_mes_desde_hecho', 'detectar_indicio',
        'electronica', 'Sujetos obligados PBCFT', 10000, 6000000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'IRNR_FACTA',
        'Presentar modelos IRNR por retenciones a no residentes sin establecimiento permanente',
        'aeat',
        'AEAT',
        'declaracion_tributaria',
        'retenedor_irnr',
        'periodica',
        '216',
        'tributario_internacional',
        'vigente',
        'real_decreto_legislativo',
        'BOE-A-2004-4527',
        'articulo 14',
        NULL,
        'Obligacion fiscal base para retenciones IRNR sin establecimiento permanente.',
        20, 'mensual', 'primeros_20_dias_periodo_siguiente', 'fin_mes',
        'electronica', 'Retenedores sobre rentas de no residentes sin establecimiento permanente.', 50, 150,
        '5%', '5-10%', 'TIE + 4%', 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, documento_origen_tipo,
        documento_origen_ref, seccion_origen, anexo_origen, nota,
        plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        canal_presentacion, obligados_resumen, sancion_min, sancion_max,
        recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
        deposito_previo, fuentes_operativas, origen_metadato, estado_metadato
    )
    VALUES (
        'IRPF_ANUAL',
        'Presentar declaracion anual del IRPF',
        'aeat',
        'AEAT',
        'declaracion_tributaria',
        'contribuyente_irpf',
        'periodica',
        '100',
        'tributario',
        'vigente',
        'ley',
        'BOE-A-2006-20764',
        NULL,
        NULL,
        'Obligacion anual del IRPF para contribuyentes obligados a declarar.',
        120, 'anual', 'campana_renta', 'cierre_ejercicio',
        'electronica', 'Contribuyentes del IRPF obligados a declarar.', 0, 150000,
        NULL, NULL, NULL, 4, NULL, '{}', 'seed_curado', 'curado'
    )
    """,
    """
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'BOE-A-2009-133'
    WHERE o.codigo = 'CNMV-IR-RESERVADA'
    """,
    """
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'SEPBLAC-MODELO-19'
    WHERE o.codigo = 'SEPBLAC-INDICIO-M19'
    """,
    """
    INSERT INTO obligacion_documento (obligacion_id, documento_id, tipo_relacion)
    SELECT o.id, d.id, 'fuente_principal'
    FROM obligacion_regulatoria o
    JOIN documento_interpretativo d ON d.referencia = 'V0000-26'
    WHERE o.codigo = 'IRNR_FACTA'
    """,
    """
    CREATE TABLE IF NOT EXISTS cnmv_regulation_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_referencia TEXT NOT NULL,
        regulacion_id TEXT NOT NULL,
        relacion_tipo TEXT NOT NULL DEFAULT 'implementa',
        nota TEXT,
        UNIQUE(documento_referencia, regulacion_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cnmv_obligation_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_referencia TEXT NOT NULL,
        tipo_obligacion TEXT NOT NULL,
        nota TEXT,
        UNIQUE(documento_referencia, tipo_obligacion)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS micro_obligacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        regulacion_relacionada TEXT NOT NULL,
        ambito TEXT NOT NULL,
        trigger_evento TEXT,
        frecuencia TEXT,
        owner_rol TEXT,
        severidad TEXT NOT NULL DEFAULT 'media',
        activo INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_micro_obligacion (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id) ON DELETE CASCADE,
        micro_obligacion_id INTEGER NOT NULL REFERENCES micro_obligacion(id) ON DELETE CASCADE,
        orden INTEGER NOT NULL DEFAULT 0,
        evidencia_requerida TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (obligacion_id, micro_obligacion_id)
    )
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_SUITABILITY', 'Evaluacion de adecuacion', 'Evaluar si el producto/inversion es adecuado al perfil del cliente (art. 53 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_APPROPRIATENESS', 'Evaluacion de conveniencia', 'Evaluar conocimientos y experiencia del cliente (art. 54 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'inicial', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_BEST_EXECUTION', 'Ejecucion preferente', 'Obtener resultado mejor posible para cliente (art. 61 LMCV)', 'mifid_ii', 'mercados', 'solicitud_ordenes', 'continua', 'trading', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_CONFLICTS', 'Gestion de conflictos de interes', 'Identificar y gestionar conflictos de interes (art. 59 LMCV)', 'mifid_ii', 'mercados', 'continuo', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_INDUCEMENTS', 'Inducimientos', 'Registrar y gestionar inducements (art. 63 LMCV)', 'mifid_ii', 'mercados', 'recepcion_inducement', 'continua', 'compliance', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_PRODUCT_GOVERNANCE', 'Gobierno de productos', 'Diseñar y distribuir productos con alcance destino (art. 98 LMCV)', 'mifid_ii', 'mercados', 'diseno_producto', 'continua', 'producto', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFIR_REPORTING', 'Reporte MiFIR', 'Reportar operaciones transaccion en tiempo real (Reg. 1287/2014)', 'mifir', 'mercados', 'ejecucion_orden', 'en_tiempo_real', 'reporting', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_INSIDER_LIST', 'Listas de inside', 'Crear y mantener listas de personas con informacion privilegiada (art. 66 LMCV)', 'mifid_ii', 'mercados', 'acceso_info_privilegiada', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_ORDER_RECORD', 'Registro de ordenes', 'Registrar y archivar ordenes (art. 23 RDM)', 'mifid_ii', 'mercados', 'ejecucion_orden', 'continua', 'operaciones', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_CLIENT_CATEGORIES', 'Categorias de cliente', 'Clasificar cliente como minorista/profesional/institucional (art. 52 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'inicial', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_COMPENSATION', 'Politica de compensacion', 'Implementar politica de compensacion alineada con riesgos (art. 95 LMCV)', 'mifid_ii', 'mercados', 'continuo', 'anual', 'rrhh', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('MIFID_MARKET_ABUSE', 'Deteccion abuso mercado', 'Detectar y reportar operaciones sospechosas de abuso (art. 13 MAR)', 'mar', 'mercados', 'operacion_sospechosa', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_REPORTING_RESERVADO', 'Reporting reservado CNMV', 'Comunicaciones confidenciales a CNMV (Disp Adic 4 LMCV)', 'cnmv_lmcv', 'reporting_regulatorio', 'cambios_internos', 'eventual', 'secretaria', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_TRANSPARENCIA', 'Transparencia emisores', 'Publicar informacion periodica de emisores (RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'trimestral', 'comercial', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_GOBIERNO_CORP', 'Gobierno corporativo', 'Cumplir Codigo de Buen Gobierno (recomendaciones)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'anual', 'consejo', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_OPS_INSTRUMENTOS_PROPIOS', 'Ops con instrumentos propios', 'Cumplir restricciones operaciones con instrumentos propios (art. 116 TRLC)', 'cnmv_lmcv', 'mercados', 'ejecucion_orden', 'continua', 'trading', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_COMUNICACION_HECHOS_ESENCIALES', 'Comunicacion hechos relevantes', 'Comunicacion hechos relevantes en tiempo real (art. 1 RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'hecho_relevante', 'eventual', 'secretaria', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_REGISTRO_OPERACIONES_INSIDER', 'Registro operaciones insider', 'Registrar operaciones de PPI (art. 19 MAR)', 'mar', 'mercados', 'operacion_ppi', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_CONCILIACION', 'Conciliacion financiera', 'Conciliacion periodica carteras clientes', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'mensual', 'back_office', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_DOCUMENTOS_INFORMACION', 'Documentos de informacion', 'Elaborar y publicar DI (art. 10 RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'continua', 'comercial', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_KYC', 'Deber de diligencia debida', 'Identificacion y verificacion cliente (RD 289/2022 art. 19)', 'pblcft', 'aml_cft', 'onboarding', 'inicial', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_MONITORING', 'Monitorizacion continua', 'Monitorizacion continua de operaciones (RD 289/2022 art. 27)', 'pblcft', 'aml_cft', 'operacion', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_STR', 'Comunicacion de indicios STR', 'Comunicar indicios de LP a SEPBLAC (art. 59 Ley 10/2010)', 'pblcft', 'aml_cft', 'indicio_lp', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_SUSPENSION', 'Suspension operacion', 'Suspender operacion si riesgo LP no mitigado (RD 289/2022 art. 23)', 'pblcft', 'aml_cft', 'riesgo_no_mitigado', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_PEP_SCREENING', 'Screening PEP', 'Verificar PEP en onboarding y periodicamente (RD 289/2022 art. 25)', 'pblcft', 'aml_cft', 'onboarding', 'inicial', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_RECORD_KEEPING', 'Conservacion documentos', 'Conservar documentos identificacion 6 anos (RD 289/2022 art. 42)', 'pblcft', 'aml_cft', 'continuo', 'continua', 'compliance', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_FORMACION', 'Formacion AML', 'Formacion empleados prevencion LP (art. 7 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'anual', 'rrhh', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_GOBIERNO_AML', 'Gobierno AML interno', 'Implementar controles internos prevencion LP (art. 6 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_MITIGACION', 'Politica mitigacion riesgos', 'Politica de mitigacion de riesgos LP (art. 5 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'anual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SEPBLAC_REPORTE_ANUAL', 'Reporte anual SEPBLAC', 'Presentar memoria anual de actividades (si aplica)', 'pblcft', 'aml_cft', 'periodicidad', 'anual', 'compliance', 'media')
    """,
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 0
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE (o.fuente = 'cnmv' AND m.regulacion_relacionada IN ('cnmv_lmcv', 'mar'))
       OR (o.fuente = 'sepblac' AND m.regulacion_relacionada = 'pblcft')
       OR (o.fuente = 'boe' AND m.regulacion_relacionada IN ('mifid_ii', 'mifir', 'mar'))
     """,
    # --- IRS Fiscal Compliance (Fase 24) ---
    """
    CREATE TABLE IF NOT EXISTS irs_fiscal_norma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'publicacion',
        anio_vigencia INTEGER,
        texto TEXT,
        url_fuente TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_dta_convention (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        pais_origen TEXT NOT NULL,
        pais_destino TEXT NOT NULL,
        titulo TEXT NOT NULL,
        fecha_firma TEXT,
        fecha_vigencia TEXT,
        tipo_acuerdo TEXT NOT NULL DEFAULT 'bilateral',
        boe_referencia TEXT,
        articulos TEXT,
        texto_completo TEXT,
        estado TEXT NOT NULL DEFAULT 'vigente',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_withholding_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        tipo_renta TEXT NOT NULL,
        tipo_renta_espanol TEXT,
        tipo_retencion_default REAL NOT NULL DEFAULT 30.0,
        tipo_retencion_dta REAL,
        pais_aplicable TEXT,
        descripcion TEXT,
        norma_referencia TEXT,
        articulo_referencia TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_w8_form (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_sujeto TEXT NOT NULL DEFAULT 'persona_fisica',
        finalidad TEXT,
        partes TEXT,
        validez_anios INTEGER NOT NULL DEFAULT 3,
        obligacion_asociada TEXT,
        texto_detalle TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_tin_reference (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_pais TEXT NOT NULL,
        pais_nombre TEXT NOT NULL,
        formato_tin TEXT,
        ejemplo_tin TEXT,
        emisor_espana TEXT,
        emisor_pais TEXT,
        es_ocde INTEGER NOT NULL DEFAULT 0,
        es_eu_vat INTEGER NOT NULL DEFAULT 0,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS giin_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giin TEXT UNIQUE NOT NULL,
        entidad_nombre TEXT NOT NULL,
        entidad_pais TEXT NOT NULL,
        tipo_entidad TEXT NOT NULL,
        estado_fatca TEXT NOT NULL DEFAULT 'activo',
        fecha_registro TEXT,
        fecha_expiracion TEXT,
        es_exempt_beneficial_owner INTEGER NOT NULL DEFAULT 0,
        es_sponsored_ffo INTEGER NOT NULL DEFAULT 0,
        nota TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_dta_convention (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        pais_origen TEXT NOT NULL,
        pais_destino TEXT NOT NULL,
        titulo TEXT NOT NULL,
        fecha_firma TEXT,
        fecha_vigencia TEXT,
        tipo_acuerdo TEXT NOT NULL DEFAULT 'bilateral',
        boe_referencia TEXT,
        articulos TEXT,
        texto_completo TEXT,
        estado TEXT NOT NULL DEFAULT 'vigente',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_withholding_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        tipo_renta TEXT NOT NULL,
        tipo_renta_espanol TEXT,
        tipo_retencion_default REAL NOT NULL DEFAULT 30.0,
        tipo_retencion_dta REAL,
        pais_aplicable TEXT,
        descripcion TEXT,
        norma_referencia TEXT,
        articulo_referencia TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_w8_form (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_sujeto TEXT NOT NULL DEFAULT 'persona_fisica',
        finalidad TEXT,
        partes TEXT,
        validez_anios INTEGER NOT NULL DEFAULT 3,
        obligacion_asociada TEXT,
        texto_detalle TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_tin_reference (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_pais TEXT NOT NULL,
        pais_nombre TEXT NOT NULL,
        formato_tin TEXT,
        ejemplo_tin TEXT,
        emisor_espana TEXT,
        emisor_pais TEXT,
        es_ocde INTEGER NOT NULL DEFAULT 0,
        es_eu_vat INTEGER NOT NULL DEFAULT 0,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS giin_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giin TEXT UNIQUE NOT NULL,
        entidad_nombre TEXT NOT NULL,
        entidad_pais TEXT NOT NULL,
        tipo_entidad TEXT NOT NULL,
        estado_fatca TEXT NOT NULL DEFAULT 'activo',
        fecha_registro TEXT,
        fecha_expiracion TEXT,
        es_exempt_beneficial_owner INTEGER NOT NULL DEFAULT 0,
        es_sponsored_ffo INTEGER NOT NULL DEFAULT 0,
        nota TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia, estado) VALUES ('FORM_1040', 'Form 1040 - U.S. Individual Income Tax Return', 'forma', 2026, 'activo')
    """,
    """
    INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia, estado) VALUES ('FORM_W9', 'Form W-9 - Request for Taxpayer Identification Number', 'forma', 2026, 'activo')
    """,
    """
    INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia, estado) VALUES ('IRC_1441', 'Internal Revenue Code Section 1441 - Withholding on Nonresidents', 'ley', 2026, 'activo')
    """,
    """
    INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, estado) VALUES ('DTA_US_ES', 'US', 'ES', 'Convenio de Doble Tributacion Estados Unidos - Espana', 'vigente')
    """,
    """
    INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, estado) VALUES ('DTA_US_GB', 'US', 'GB', 'Convenio de Doble Tributacion Estados Unidos - Reino Unido', 'vigente')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, estado) VALUES ('WHT_DIVIDENDS', 'dividends', 'Dividendos', 30.0, 15.0, 'activo')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, estado) VALUES ('WHT_INTEREST', 'interest', 'Intereses', 30.0, 10.0, 'activo')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, estado) VALUES ('WHT_ROYALTIES', 'royalties', 'Regalias', 30.0, 0.0, 'activo')
    """,
    """
    INSERT INTO irs_w8_form (codigo, nombre, tipo_sujeto, validez_anios, estado) VALUES ('W8BEN', 'Form W-8BEN - Foreign Individual', 'persona_fisica', 3, 'activo')
    """,
    """
    INSERT INTO irs_w8_form (codigo, nombre, tipo_sujeto, validez_anios, estado) VALUES ('W8BENE', 'Form W-8BEN-E - Foreign Entity', 'persona_juridica', 3, 'activo')
    """,
    """
    INSERT INTO irs_tin_reference (codigo_pais, pais_nombre, formato_tin, ejemplo_tin, es_ocde) VALUES ('US', 'Estados Unidos', 'XX-XXXXXXX', '12-3456789', 1)
    """,
    """
    INSERT INTO irs_tin_reference (codigo_pais, pais_nombre, formato_tin, ejemplo_tin, es_ocde, es_eu_vat) VALUES ('ES', 'Espana', 'XX-XXXXXXX-X', 'A12345678', 1, 1)
    """,
    """
    INSERT INTO giin_registry (giin, entidad_nombre, entidad_pais, tipo_entidad, estado_fatca) VALUES ('GIIN123.456.789.001', 'Spanish Bank FFI', 'ES', 'FFI', 'activo')
    """,
    """
    INSERT INTO giin_registry (giin, entidad_nombre, entidad_pais, tipo_entidad, estado_fatca, es_exempt_beneficial_owner) VALUES ('GIIN999.888.777.002', 'Exempt Institution', 'US', 'Exempt Beneficial Owner', 'activo', 1)
    """,
    # --- International Obligations (FATCA / CRS) ---
    """
    CREATE TABLE IF NOT EXISTS obligacion_internacional (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'ley',
        jurisdiccion_origen TEXT,
        jurisdiccion_aplicacion TEXT,
        vigente_desde TEXT NOT NULL,
        vigente_hasta TEXT,
        descripcion TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO obligacion_internacional (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion, vigente_desde, descripcion, estado) VALUES ('FATCA', 'Foreign Account Tax Compliance Act (FATCA) — Ley 16/2012', 'ley', 'US', 'ES', '2012-12-28', 'Ley espanola que implementa FATCA.', 'activo')
    """,
    """
    INSERT INTO obligacion_internacional (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion, vigente_desde, descripcion, estado) VALUES ('CRS', 'Common Reporting Standard (CRS) — Estandar OCDE', 'estandar', 'OCDE', 'internacional', '2016-01-01', 'Estandar internacional para intercambio automatico de informacion financiera.', 'activo')
    """,
    """
    INSERT INTO obligacion_internacional (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion, vigente_desde, descripcion, estado) VALUES ('FATCA_IGA_ES', 'Acuerdo Intergubernamental FATCA entre Espana y Estados Unidos', 'convenio', 'ES-US', 'ES-US', '2013-09-02', 'Acuerdo intergubernamental Modelo 1 para la implementacion de FATCA.', 'activo')
    """,
    """
    INSERT INTO obligacion_internacional (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion, vigente_desde, descripcion, estado) VALUES ('DAC6', 'Directiva DAC6 — Reporte obligatorio de arreglos transfronterizos agresivos', 'directiva', 'UE', 'UE', '2018-06-25', 'Obliga a intermediarios a reportar arreglos transfronterizos agresivos.', 'activo')
    """,
    """
    INSERT INTO obligacion_internacional (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion, vigente_desde, descripcion, estado) VALUES ('FATCA_INACTIVO', 'FATCA Obsoleta', 'ley', 'US', 'ES', '2010-01-01', 'Obligacion obsoleta para tests.', 'inactivo')
    """,
    # --- Expansion LECR micro-obligaciones ---
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_ECR_REGISTRATION', 'Registro en ECR', 'Registro en el Registro Central de Representantes de ECR (Ley 22/2014 arts. 1-12)', 'lecr', 'ecr_regulatorio', 'constitucion', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_SGEIC', 'Autorizacion SGEIC / Autogestion', 'Autorizacion como SGEIC opcional (art. 26 LECR) o contratar SGEIC externo', 'lecr', 'ecr_regulatorio', 'constitucion', 'eventual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_DIVERSIFICATION', 'Diversificacion >=50% no cotizados', 'Diversificacion de posiciones: >=50% empresas no cotizadas (art. 26 LECR)', 'lecr', 'ecr_regulatorio', 'periodicidad', 'trimestral', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_MIID_DIVERSIFICATION', 'Diversificacion MiID >=50%', 'Diversificacion MiID (art. 134 LECR) para fondos de inversion', 'lecr', 'ecr_regulatorio', 'periodicidad', 'trimestral', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_CONDUCT_RULES', 'Reglas de conducta MiFID II', 'Cumplir reglas de conducta MiFID II (arts. 53-63 LMCV) como ECR', 'lecr', 'ecr_regulatorio', 'continuo', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_FISCAL_NON_RESIDENT', '95% exencion dividendos no residentes', 'Exencion 95% dividendos y plusvalias para no residentes (art. 21 Ley IS + art. 30 Ley 22/2014)', 'lecr', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    # --- Expansion SOCIMI micro-obligaciones ---
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SOCIMI_ASSET_COMPOSITION', '>=80% activos inmobiliarios arrendados', 'Mantener >=80% del valor del activo en inmuebles arrendados (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SOCIMI_DISTRIBUTION', '>=80% distribucion de resultados', 'Distribuir >=80% de los resultados imponibles (art. 12 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SOCIMI_TAX_UNDISTRIBUTED', 'Gravamen 15-19% beneficios no distribuidos', 'Gravamen 15-19% sobre beneficios no distribuidos (art. 24 Ley 11/2009)', 'socimi', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SOCIMI_TAX_REGIME', 'Regimen fiscal SOCIMI 0% IS', 'Aplicar regimen fiscal SOCIMI con tipo 0% si distribuye >=80% beneficios (art. 23 Ley 11/2009)', 'socimi', 'tributario', 'continuo', 'anual', 'finanzas', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('SOCIMI_80_20_RULE', 'Regla 80/20 SOCIMI', '80% activo inmobiliario arrendado + 20% liquidez maxima (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta')
    """,
    # --- Expansion CSDR micro-obligaciones ---
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CSDR_SETTLEMENT', 'T+2 settlement / T+1 inminente', 'Cumplir T+2 settlement vigente, preparar T+1 (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'ejecucion_orden', 'continua', 'operaciones', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CSDR_REPORTING', 'Segregacion y reporting CSDR', 'Segregacion de posiciones y reporting a CSD (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'periodicidad', 'mensual', 'reporting', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CSDR_SETTLEMENT_FAILURE', 'Gestion fallidos de settlement CSDR', 'Gestion de fallidos de settlement y multas CSDR (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'fallido_settlement', 'eventual', 'operaciones', 'alta')
    """,
    # --- Expansion CNMV ECR micro-obligaciones ---
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_ECR_REPORTING', 'Reporte estados reservados CNMV ECR', 'Comunicacion de estados reservados a CNMV via ECR (XML requerimientos)', 'cnmv_ecr', 'reporting_cnmv_ecr', 'periodicidad', 'trimestral', 'reporting', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_ECR_XML_FORMAT', 'XML formatos ECR CNMV', 'Generar XML segun formatos requeridos por CNMV para ECR', 'cnmv_ecr', 'reporting_cnmv_ecr', 'periodicidad', 'trimestral', 'reporting', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_ECR_ACTIVE_LIST', 'Listado FCR/SCR activos CNMV', 'Mantener listado actualizado de FCR/SCR inscritos en CNMV', 'cnmv_ecr', 'reporting_cnmv_ecr', 'continuo', 'mensual', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_ECR_FAQS', 'FAQs criterios interpretativos CNMV', 'Seguir FAQs y criterios interpretativos de CNMV para ECR', 'cnmv_ecr', 'reporting_cnmv_ecr', 'continuo', 'continua', 'compliance', 'media')
    """,
    # --- Expansion Doctrina DGT micro-obligaciones ---
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_SOCIMI_GRAVAMENES', 'Doctrina DGT gravamenes SOCIMI', 'Aplicar doctrina DGT V0992-20 sobre gravamenes a socios >5% en SOCIMI', 'doctrina_dgt', 'doctrina_dgt', 'continuo', 'continua', 'finanzas', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_SOCIMI_DISTRIBUCION', 'Doctrina DGT distribucion SOCIMI', 'Interpretar doctrina DGT sobre obligacion de distribucion de beneficios en SOCIMI', 'doctrina_dgt', 'doctrina_dgt', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_ETI_EMISORES', 'Doctrina DGT ETI emisores MiFID', 'Interpretar doctrina DGT sobre emisores con ETI y folletos MiFID', 'doctrina_dgt', 'doctrina_dgt', 'continuo', 'continua', 'compliance', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_FCR_EXENCIONES', 'Doctrina DGT exenciones FCR/SCR', 'Aplicar doctrina DGT V2424-20 sobre exenciones fiscales similares para FCR/SCR', 'doctrina_dgt', 'doctrina_dgt', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    # --- Expansion N:M mappings ---
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 0
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE o.fuente = 'boe' AND m.regulacion_relacionada IN ('lecr', 'socimi', 'csdr', 'doctrina_dgt', 'cnmv_ecr')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_SAFETY_VALVE', 'Aplicacion safety valve LECR', 'Aplicar mecanismo safety valve para inversiones en instrumentos financieros (art. 26 LECR)', 'lecr', 'ecr_regulatorio', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('LECR_TAX_COMPLIANCE', 'Cumplimiento fiscal LECR', 'Cumplir obligaciones fiscales derivadas de la condicion de ECR (art. 31 LECR)', 'lecr', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CSDR_CASH_ALLOCATION', 'Alocacion liquida CSDR', 'Comunicar alocacion de liquida en operaciones CSDR (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'ejecucion_orden', 'continua', 'operaciones', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CSDR_PARTICIPATION', 'Participacion CSDR y T2S', 'Participar en infraestructuras CSD y T2S (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'continuo', 'continua', 'operaciones', 'media')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('CNMV_ECR_GOBIERNO', 'Gobierno ECR CNMV', 'Implementar gobierno interno para registros ECR (Circular 6/2014)', 'cnmv_ecr', 'reporting_cnmv_ecr', 'continuo', 'continua', 'compliance', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_SOCIMI_CONTRATOS', 'Doctrina DGT contratos arrendamiento SOCIMI', 'Interpretar doctrina DGT sobre requisitos de contratos de arrendamiento para SOCIMI', 'doctrina_dgt', 'doctrina_dgt', 'continuo', 'continua', 'finanzas', 'alta')
    """,
    """
    INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad) VALUES ('DGT_SOCIMI_ENTIDADES', 'Doctrina DGT SOCIMI y entidades participadas', 'Aplicar doctrina DGT sobre SOCIMI con participaciones en entidades', 'doctrina_dgt', 'doctrina_dgt', 'periodicidad', 'anual', 'finanzas', 'alta')
    """,
    """
    INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
    VALUES (
        'ALVAREZ GARCIA GANADERIA, S.L.',
        NULL,
        'C/ SANTA LUCIA 19',
        'BORME'
    )
    """,
    """
    INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
    VALUES (
        'MURILLO & BARRERO, SOCIEDAD LIMITADA',
        NULL,
        NULL,
        'BORME'
    )
    """,
    """
    INSERT INTO entity_identifiers (empresa_id, lei, nombre_legal, pais, estado, vigencia_desde, fuente_ref)
    SELECT e.id, '5493001KJTIURC11JN06', 'BBVA BANCO POPULAR ESPAÑOL', 'ES', 'active', '2012-01-01', 'GLEIF:5493001KJTIURC11JN06'
    FROM empresa e WHERE e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    """,
    """
    INSERT INTO entity_aliases (empresa_id, alias, alias_normalizado, fuente, confianza)
    SELECT e.id, 'BBVA', 'bbva', 'GLEIF', 0.9
    FROM empresa e WHERE e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    """,
    """
    INSERT INTO entity_aliases (empresa_id, alias, alias_normalizado, fuente, confianza)
    SELECT e.id, 'Banco Popular Español', 'banco popular español', 'GLEIF', 0.8
    FROM empresa e WHERE e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    """,
    """
    INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
    SELECT d.id, e.id, 'principal', 0.85, 'Test fixture BORME empresa'
    FROM documento_interpretativo d
    JOIN empresa e ON e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    WHERE d.referencia = 'BORME-A-2025-55-37'
    """,
    """
    INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
    SELECT d.id, e.id, 'absorbida', 0.70, 'Test fixture BORME empresa relacionada'
    FROM documento_interpretativo d
    JOIN empresa e ON e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    WHERE d.referencia = 'BORME-A-2025-55-37'
    """,
    # --- Ownership seed: participaciones ---
    """
    INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref)
    SELECT e.id, (SELECT id FROM empresa WHERE nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'), 'empresa', 'ALVAREZ GARCIA GANADERIA, S.L.', 60.0, 'directa', '2020-01-01', NULL, 'BORME', 'BORME-A-2025-55-37'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    """
    INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref)
    SELECT e.id, (SELECT id FROM empresa WHERE nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'), 'empresa', 'MURILLO & BARRERO, SOCIEDAD LIMITADA', 100.0, 'directa', '2018-06-15', NULL, 'BORME', 'BORME-A-2025-55-37'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    """
    INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref)
    SELECT e.id, (SELECT id FROM empresa WHERE nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'), 'empresa', 'ALVAREZ GARCIA GANADERIA, S.L.', 30.0, 'indirecta', '2020-01-01', NULL, 'BORME', 'BORME-A-2025-55-37'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    # --- Ownership seed: relaciones societarias ---
    """
    INSERT INTO ownership_relation (empresa_origen_id, empresa_destino_id, tipo_relacion, porcentaje, vigencia_desde, fuente, fuente_ref, nota)
    SELECT e.id, (SELECT id FROM empresa WHERE nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'), 'absorbente', 60.0, '2020-01-01', 'BORME', 'BORME-A-2025-55-37', 'Murillo & Barreno es absorbente de Alvarez Garcia'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    """
    INSERT INTO ownership_relation (empresa_origen_id, empresa_destino_id, tipo_relacion, porcentaje, vigencia_desde, fuente, fuente_ref, nota)
    SELECT e.id, (SELECT id FROM empresa WHERE nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'), 'filial', 60.0, '2020-01-01', 'BORME', 'BORME-A-2025-55-37', 'Alvarez Garcia es filial de Murillo & Barreno'
    FROM empresa e WHERE e.nombre = 'ALVAREZ GARCIA GANADERIA, S.L.'
    """,
    # --- Ownership seed: UBO records ---
    """
    INSERT INTO ubo_record (empresa_id, nombre_persona, nacionalidad, fecha_nacimiento, pais_residencia, tipo_ubo, porcentaje_control, umbral_superado, fuente, fuente_ref)
    SELECT e.id, 'Carlos Alvarez Garcia', 'ES', '1975-03-15', 'ES', 'titular_poder', 60.0, '>25%', 'BORME', 'BORME-A-2025-55-37'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    """
    INSERT INTO ubo_record (empresa_id, nombre_persona, nacionalidad, fecha_nacimiento, pais_residencia, tipo_ubo, porcentaje_control, umbral_superado, fuente, fuente_ref)
    SELECT e.id, 'Maria Garcia Lopez', 'ES', '1980-07-22', 'ES', 'titular_propiedad', 40.0, '>25%', 'BORME', 'BORME-A-2025-55-37'
    FROM empresa e WHERE e.nombre = 'MURILLO & BARRERO, SOCIEDAD LIMITADA'
    """,
    # --- Enlace doctrina <-> artículo ---
    """
    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
    SELECT d.id, a.id, 'manual', 1.00, 'Test fixture'
    FROM documento_interpretativo d
    JOIN articulo a ON a.numero = '91'
    JOIN norma n ON n.id = a.norma_id
    WHERE d.referencia = 'V0000-26' AND n.codigo = 'LIVA'
    """,
    """
    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
    SELECT d.id, a.id, 'manual', 0.95, 'DGT rendimientos mobiliarios vinculados a art.30 LIRPF'
    FROM documento_interpretativo d
    JOIN articulo a ON a.numero = '30'
    JOIN norma n ON n.id = a.norma_id
    WHERE d.referencia IN ('V0091-18', 'V2424-20', 'V2965-17') AND n.codigo = 'LIRPF'
    """,
    # --- Modelos AEAT ---
    """
    CREATE TABLE aeat_modelo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        periodo TEXT,
        impuesto TEXT,
        url_info TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT
    )
    """,
    """
    CREATE TABLE modelo_articulo (
        modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        casilla TEXT,
        nota TEXT,
        fuente TEXT NOT NULL,
        url_fuente TEXT,
        PRIMARY KEY (modelo_id, articulo_id)
    )
    """,
    # --- Seed: Modelo 100 linked to LIVA 91 (for testing doctrina derivada) ---
    """
    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
    VALUES ('100', 'IRPF Declaración anual', 'anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-100'),
           ('111', 'IRPF Retenciones e ingresos a cuenta', 'trimestral', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-111'),
           ('115', 'IRPF Retenciones arrendamientos', 'trimestral', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-115'),
           ('303', 'IVA Autoliquidación', 'trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-303'),
           ('349', 'Declaración recapitulativa operaciones intracomunitarias', 'mensual', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-349'),
            ('390', 'IVA Resumen anual', 'anual', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-390'),
            ('124', 'Retenciones IRNR — rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-124'),
            ('216', 'IRNR Retenciones rentas sin establecimiento permanente', 'mensual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-216'),
            ('296', 'IRNR Resumen anual retenciones sin EP', 'anual', 'IRNR', 'https://sede.agenciatributaria.gob.es/modelo-296'),
            ('190', 'IRPF Retenciones y pagos a cuenta (no laborales)', 'anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-190'),
            ('001', 'IRPF Dividendos y rentas similares', 'anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-001'),
            ('036', 'Declaración censal alta/modificación/baja', 'eventual', 'CENSAL', 'https://sede.agenciatributaria.gob.es/modelo-036'),
           ('347', 'Declaración anual operaciones con terceros', 'anual', 'INFORMATIVO', 'https://sede.agenciatributaria.gob.es/modelo-347')
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, '0002', 'Rendimientos trabajo', 'Instrucciones Modelo 100 2025', 'https://sede.agenciatributaria.gob.es'
    FROM aeat_modelo m, articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '100' AND n.codigo = 'LIVA' AND a.numero = '91'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Rentas obtenidas sin EP', 'Instrucciones Modelo 124 2025', 'https://sede.agenciatributaria.gob.es/modelo-124'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '124' AND n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Retenciones IRNR sin EP', 'Instrucciones Modelo 216 2025', 'https://sede.agenciatributaria.gob.es/modelo-216'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '216' AND n.codigo = 'IRNR' AND a.numero = '14'
    """,
    """
    INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
    SELECT m.id, a.id, NULL, 'Resumen anual IRNR', 'Instrucciones Modelo 296 2025', 'https://sede.agenciatributaria.gob.es/modelo-296'
    FROM aeat_modelo m
    JOIN articulo a ON 1=1
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '296' AND n.codigo = 'IRNR' AND a.numero = '14'
    """,
    # --- Modelos v2 schema: campañas, casillas, claves, instrucciones, normativa ---
    """
    CREATE TABLE modelo_campana (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        campana         TEXT NOT NULL,
        version_form    TEXT,
        url_instrucciones TEXT,
        url_normativa   TEXT,
        url_formato     TEXT,
        activo          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, campana)
    )
    """,
    """
    CREATE TABLE modelo_casilla (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_casilla    TEXT,
        pagina          INTEGER,
        orden           INTEGER,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE modelo_clave (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_clave      TEXT,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE modelo_instruccion (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        seccion         TEXT NOT NULL,
        titulo          TEXT NOT NULL,
        contenido       TEXT NOT NULL,
        orden           INTEGER DEFAULT 0,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE modelo_normativa (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        boe_id          TEXT,
        titulo          TEXT NOT NULL,
        fecha           TEXT,
        url_boe         TEXT,
        resumen         TEXT,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, boe_id)
    )
    """,
    """
    CREATE TABLE modelo_campana_operativa (
        campana_id               INTEGER PRIMARY KEY REFERENCES modelo_campana(id) ON DELETE CASCADE,
        categoria_obligado       TEXT,
        frecuencia_presentacion  TEXT,
        ventana_presentacion     TEXT,
        canal_presentacion       TEXT,
        obligados_resumen        TEXT,
        plazo_resumen            TEXT,
        presentacion_resumen     TEXT,
        norma_base               TEXT,
        nota                     TEXT,
        origen_metadato          TEXT DEFAULT 'seed_curado',
        estado_metadato          TEXT DEFAULT 'curado',
        actualizado_at           TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Seed: campaign for model 100 ---
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa, url_formato)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-100-normativa',
           'https://sede.agenciatributaria.gob.es/modelo-100-formato'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-111-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-111-normativa'
    FROM aeat_modelo m WHERE m.codigo = '111'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-115-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-115-normativa'
    FROM aeat_modelo m WHERE m.codigo = '115'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-124-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-124-normativa'
    FROM aeat_modelo m WHERE m.codigo = '124'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-216-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-216-normativa'
    FROM aeat_modelo m WHERE m.codigo = '216'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-296-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-296-normativa'
    FROM aeat_modelo m WHERE m.codigo = '296'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-303-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-303-normativa'
    FROM aeat_modelo m WHERE m.codigo = '303'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-349-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-349-normativa'
    FROM aeat_modelo m WHERE m.codigo = '349'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-390-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-390-normativa'
    FROM aeat_modelo m WHERE m.codigo = '390'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-036-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-036-normativa'
    FROM aeat_modelo m WHERE m.codigo = '036'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, url_normativa)
    SELECT m.id, '2025', 1,
           'https://sede.agenciatributaria.gob.es/modelo-347-instrucciones',
           'https://sede.agenciatributaria.gob.es/modelo-347-normativa'
    FROM aeat_modelo m WHERE m.codigo = '347'
    """,
    # --- Seed: modelo_normativa ---
    """
    INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
    SELECT m.id, 'BOE-A-2024-26789', 'Modelo 100 IRPF', '2024-10-01',
           'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-26789',
           'Norma base del modelo 100'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    # --- Seed: modelo_campana_operativa ---
    """
    INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
        ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen,
        norma_base, origen_metadato, estado_metadato)
    SELECT mc.id, 'retenedor_irnr', 'mensual', 'primeros_20_dias_mes_siguiente', 'electronica',
           'obligados a practicar retenciones o ingresos a cuenta sobre determinadas rentas obtenidas por no residentes...',
           'primeros veinte dias naturales del mes siguiente...', 'via electronica...',
           'IRNR art. 14', 'seed_curado', 'curado'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
        ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen,
        norma_base, origen_metadato, estado_metadato)
    SELECT mc.id, 'retenedor_irpf', 'trimestral', '1-20_abril_julio_octubre_enero', 'electronica',
           'obligados a practicar retenciones e ingresos a cuenta por rendimientos del trabajo...',
           'trimestral...', 'via electronica...',
           'IRPF art. 86', 'seed_curado', 'curado'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
        ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen,
        norma_base, origen_metadato, estado_metadato)
    SELECT mc.id, 'retenedor_irpf', 'trimestral', '1-20_abril_julio_octubre_enero', 'electronica',
           'obligados a practicar retenciones por arrendamientos de inmuebles urbanos...',
           'trimestral...', 'via electronica...',
           'IRPF art. 86', 'seed_curado', 'curado'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
        ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen,
        norma_base, origen_metadato, estado_metadato)
    SELECT mc.id, 'empresario_o_profesional_iva', 'trimestral', 'plazos_generales', 'electronica',
           'empresarios y profesionales obligados a autoliquidar el IVA...',
           'plazos generales...', 'electronica...',
           'LIVA art. 71', 'seed_curado', 'curado'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
        ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen,
        norma_base, origen_metadato, estado_metadato)
    SELECT mc.id, 'obligado_censal', 'anual', '1_mes_desde_hecho', 'electronica',
           'obligados a inscribirse en el censo de empresarios...',
           'anual...', 'electronica...',
           'LIRPF art. 85', 'seed_curado', 'curado'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    # --- Seed: casillas for model 100 campaign ---
    """
    INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
    SELECT mc.id, '0002', 'Rendimientos del trabajo', 'Suma de todos los rendimientos del trabajo', 'importe', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    # --- Seed: instrucciones for model 100 campaign ---
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'caracteristicas', 'Que es el modelo 100?', 'El modelo 100 es la declaracion anual del IRPF.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 100', 'Deben presentar este modelo los contribuyentes del IRPF obligados a declarar conforme a los limites legales vigentes.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 100', 'La presentacion de la declaracion anual del IRPF correspondiente a la campana 2025 se realiza dentro del plazo general de la campana de renta publicado por AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 216', 'Deben presentar el modelo 216 los obligados a practicar retenciones o ingresos a cuenta sobre determinadas rentas obtenidas por no residentes sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 111', 'Deben presentar el modelo 111 los obligados a practicar retenciones e ingresos a cuenta por rendimientos del trabajo y determinadas actividades economicas.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 111', 'El modelo 111 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 111', 'La presentacion del modelo 111 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '111' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 115', 'Deben presentar el modelo 115 los obligados a practicar retenciones por arrendamientos de inmuebles urbanos.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 115', 'El modelo 115 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 115', 'La presentacion del modelo 115 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '115' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 216', 'El modelo 216 se presenta con caracter mensual dentro de los primeros veinte dias naturales del mes siguiente al periodo de declaracion, salvo las especialidades previstas por AEAT.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 216', 'La presentacion del modelo 216 se realiza por via electronica a traves de la sede de la AEAT utilizando los sistemas de identificacion admitidos.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '216' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 124', 'Deben presentar el modelo 124 los obligados a retener sobre determinadas rentas del capital mobiliario obtenidas por no residentes sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 124', 'El modelo 124 se presenta con caracter mensual dentro de los primeros veinte dias naturales del mes siguiente al periodo de declaracion.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 124', 'La presentacion del modelo 124 se realiza por medios electronicos a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '124' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 296', 'Deben presentar el modelo 296 los retenedores y obligados a ingresar a cuenta que deban resumir anualmente las rentas sujetas al IRNR sin establecimiento permanente.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 296', 'El modelo 296 se presenta con caracter anual en el plazo fijado por la AEAT para el resumen anual de retenciones e ingresos a cuenta.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 296', 'La presentacion del modelo 296 se realiza electronicamente mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '296' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 303', 'Deben presentar el modelo 303 los empresarios y profesionales que deban autoliquidar el IVA en el periodo correspondiente, salvo los supuestos exceptuados por la normativa.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 303', 'El modelo 303 se presenta con caracter trimestral o mensual segun el regimen aplicable, dentro de los plazos generales establecidos por la AEAT para la autoliquidacion del IVA.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 303', 'La presentacion del modelo 303 se realiza por via electronica mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 349', 'Deben presentar el modelo 349 los sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 349', 'El modelo 349 se presenta con caracter mensual o trimestral segun el volumen de operaciones, del 1 al 20 del mes siguiente al periodo.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 349', 'La presentacion del modelo 349 se realiza por via electronica a traves de la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '349' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 390', 'Deben presentar el modelo 390 los sujetos pasivos del IVA obligados a presentar el resumen anual, salvo excepciones previstas por la normativa.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 390', 'El modelo 390 se presenta con caracter anual en el plazo fijado por la AEAT junto con el cierre del ejercicio de IVA.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 390', 'La presentacion del modelo 390 se realiza por via electronica mediante la sede de la AEAT.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '390' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 036', 'Deben presentar el modelo 036 las personas fisicas o juridicas que inicien actividad, modifiquen datos censales o causen baja en el censo.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'plazo', 'Plazo de presentacion del modelo 036', 'El modelo 036 se presenta dentro del plazo de un mes desde el inicio de actividad o desde la modificacion censal correspondiente.', 2
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'como-presentar', 'Forma de presentacion del modelo 036', 'La presentacion del modelo 036 puede realizarse por la sede de la AEAT con los sistemas de identificacion admitidos.', 3
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '036' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'quien-debe', 'Quienes deben presentar el modelo 347', 'Deben presentar el modelo 347 quienes hayan realizado operaciones con terceros por importe superior al umbral legal anual.', 1
     FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
     WHERE m.codigo = '347' AND mc.campana = '2025'
     """,
    # --- workflow_cases table ---
    """
    CREATE TABLE IF NOT EXISTS workflow_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_id TEXT UNIQUE NOT NULL,
        cambio_codigo TEXT NOT NULL,
        obligacion_codigo TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendiente_revision',
        owner_rol TEXT NOT NULL,
        fecha_objetivo TEXT NOT NULL,
        evidencia_requerida TEXT NOT NULL DEFAULT '[]',
        checklist TEXT NOT NULL DEFAULT '[]',
        resultado_revision TEXT,
        notas TEXT,
        accion_recomendada_confirmada TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT OR IGNORE INTO workflow_cases (
        workflow_id, cambio_codigo, obligacion_codigo, estado, owner_rol,
        fecha_objetivo, evidencia_requerida, checklist
    ) VALUES (
        'WF-001',
        'CAMBIO-CNMV-001',
        'CNMV-IR-RESERVADA',
        'pendiente_revision',
        'compliance',
        '2026-05-05',
        '["analisis_impacto","actualizacion_calendario"]',
        '["validar impacto normativo","asignar responsable","confirmar fecha objetivo"]'
    )
    """,
    # --- Screening tables ---
    """
    CREATE TABLE IF NOT EXISTS screening_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('sanctions', 'pep', 'watchlist')),
        organismo TEXT NOT NULL,
        pais CHAR(2),
        url_fuente TEXT,
        descripcion TEXT,
        actualizada TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_lists_tipo ON screening_lists(tipo)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_lists_activo ON screening_lists(activo)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_lists_pais ON screening_lists(pais)
    """,
    """
    CREATE TABLE IF NOT EXISTS screening_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL REFERENCES screening_lists(id),
        entidad_id TEXT NOT NULL,
        nombre TEXT NOT NULL,
        nombre_normalizado TEXT NOT NULL,
        tipo_entidad TEXT NOT NULL CHECK (tipo_entidad IN ('person', 'entity', 'vessel', 'aircraft')),
        pais CHAR(2),
        nif TEXT,
        fecha_nacimiento TEXT,
        aliases TEXT DEFAULT '[]',
        categorias TEXT DEFAULT '[]',
        descripcion TEXT,
        fecha_sancion TEXT,
        fecha_alta TEXT,
        fecha_baja TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        embedding_384 TEXT,
        embedding_model_name TEXT,
        content_hash TEXT,
        UNIQUE (list_id, entidad_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_entries_list ON screening_entries(list_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_entries_tipo_entidad ON screening_entries(tipo_entidad)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_entries_pais ON screening_entries(pais)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_entries_activo ON screening_entries(activo)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_entries_nif ON screening_entries(nif)
    """,
    """
    CREATE TABLE IF NOT EXISTS screening_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        entry_id INTEGER NOT NULL REFERENCES screening_entries(id),
        list_id INTEGER NOT NULL REFERENCES screening_lists(id),
        confianza REAL NOT NULL,
        motivo TEXT NOT NULL,
        match_campo TEXT NOT NULL,
        match_texto TEXT,
        revisado INTEGER NOT NULL DEFAULT 0,
        revisor TEXT,
        revisado_at TEXT,
        notas TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (empresa_id, entry_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_empresa ON screening_matches(empresa_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_entry ON screening_matches(entry_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_list ON screening_matches(list_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_confianza ON screening_matches(confianza)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_revisado ON screening_matches(revisado)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_matches_motivo ON screening_matches(motivo)
    """,
    # --- Seed screening lists ---
    """
    INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
    VALUES ('OFAC_SDN', 'OFAC Specially Designated Nationals List', 'sanctions', 'OFAC', 'US', 'https://www.treasury.gov/sdn', 'US Treasury OFAC SDN list', '2026-04-01', 1)
    """,
    """
    INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
    VALUES ('EU_SANCTIONS', 'EU Consolidated Sanctions List', 'sanctions', 'EEAS', 'EU', 'https://www.consilium.europa.eu/sanctions', 'EU consolidated sanctions list', '2026-04-01', 1)
    """,
    """
    INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
    VALUES ('UN_SANCTIONS', 'UN Security Council Sanctions List', 'sanctions', 'UN', 'INTL', 'https://www.un.org/securitycouncil/sanctions', 'UN Security Council sanctions lists', '2026-04-01', 1)
    """,
    """
    INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
    VALUES ('SEPBLAC', 'Lista SEPBLAC Sujetos Obligados', 'watchlist', 'SEPBLAC', 'ES', 'https://www.sepblac.es', 'Lista de sujetos obligados SEPBLAC', '2026-04-01', 1)
    """,
    """
    INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
    VALUES ('ES_PEPS', 'Lista de Personas Politicamente Exponentes Espanolas', 'pep', 'UE', 'ES', 'https://www.boe.es', 'Personas politicamente expuestas espanolas', '2026-04-01', 1)
    """,
    # --- Seed screening entries ---
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'OFAC-25001', 'AL-RASHID TRADING COMPANY', 'al-rashid trading company', 'entity', 'SY', NULL, NULL, '["AL-RASHID CO","ALRASHID TRADING"]', '["sanctions","syria","trading"]', 'Syrian trading company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'OFAC_SDN'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'OFAC-25002', 'PETRO-ENERGY INTL', 'petro-energy intl', 'entity', 'RU', NULL, NULL, '["PETRO ENERGY INTERNATIONAL"]', '["sanctions","russia","energy"]', 'Russian energy company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'OFAC_SDN'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'OFAC-25003', 'AHMED AL-MANSOUR', 'ahmed al-mansour', 'person', 'SY', 'SY-8821001', '1970-05-15', '["A. AL-MANSOUR","AHMED MANSOUR"]', '["sanctions","syria","individual"]', 'Syrian individual', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'OFAC_SDN'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'OFAC-25004', 'DAMASCUS EXPORTS LLC', 'damascus exports llc', 'entity', 'SY', NULL, NULL, '["DAMASCUS EXPORT"]', '["sanctions","syria","exports"]', 'Syrian export company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'OFAC_SDN'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'EU-10001', 'VOLGA TRADING OOO', 'volga trading ooo', 'entity', 'RU', NULL, NULL, '["VOLGA TRADING"]', '["sanctions","russia","trading"]', 'Russian trading company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'EU_SANCTIONS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'EU-10002', 'KREMLIN ENERGY JSC', 'kremlin energy jsc', 'entity', 'RU', NULL, NULL, '["KREMLIN ENERGY"]', '["sanctions","russia","energy"]', 'Russian energy company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'EU_SANCTIONS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'UN-40001', 'AHMED AL-MANSOUR', 'ahmed al-mansour', 'person', 'YE', 'YE-8821003', NULL, '["A. AL-MANSOUR"]', '["sanctions","yemen","individual"]', 'Yemeni individual', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'UN_SANCTIONS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'UN-40002', 'AL-SALEEM CONSTRUCTION', 'al-saleem construction', 'entity', 'SY', NULL, NULL, '["AL SALEEM CONSTRUCTION","AL-SALEEM CON"]', '["sanctions","syria","construction"]', 'Syrian construction company', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'UN_SANCTIONS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'SEPBLAC-001', 'TRANSFINANCIERA IBERICA SL', 'transfinanciera iberica sl', 'entity', 'ES', 'ES-B12345678', NULL, '["TRANSFINANCIERA"]', '["aml_suspect","spain","financial"]', 'Spanish financial suspect', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'SEPBLAC'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'SEPBLAC-002', 'GALICIA MONEY SERVICES SA', 'galicia money services sa', 'entity', 'ES', 'ES-A87654321', NULL, '["GALICIA MONEY"]', '["aml_suspect","spain","money_services"]', 'Spanish money services suspect', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'SEPBLAC'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'ESPEP-001', 'CARLOS RODRIGUEZ FERNANDEZ', 'carlos rodriguez fernandez', 'person', 'ES', 'ES-12345678A', '1965-03-20', '["Carlos Rodriguez F."]','["pep","spain","government_official"]', 'Spanish government official PEP', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'ES_PEPS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'ESPEP-002', 'MARIA TERESA GARCIA LOPEZ', 'maria teresa garcia lopez', 'person', 'ES', 'ES-87654321B', '1972-07-10', '["M. T. Garcia Lopez"]','["pep","spain","former_minister"]', 'Former Spanish minister PEP', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'ES_PEPS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'ESPEP-003', 'JUAN PABLO MARTINEZ RUIZ', 'juan pablo martinez ruiz', 'person', 'ES', 'ES-11223344C', NULL, '["J. P. Martinez Ruiz"]','["pep","spain","regional_official"]', 'Spanish regional official PEP', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'ES_PEPS'
    """,
    """
    INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, fecha_alta, fecha_baja, activo)
    SELECT l.id, 'ESPEP-004', 'ISABEL FERNANDEZ TORRES', 'isabel fernandez torres', 'person', 'ES', 'ES-55667788D', '1968-11-25', '["Isabel Fernandez T."]','["pep","spain","parliament_member"]', 'Spanish parliament member PEP', NULL, NULL, NULL, 1
    FROM screening_lists l WHERE l.codigo = 'ES_PEPS'
    """,
    # --- DTA Conventions & Withholding Rules (Fase 25.8) ---
    """
    CREATE TABLE IF NOT EXISTS irs_dta_convention (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        pais_origen TEXT NOT NULL,
        pais_destino TEXT NOT NULL,
        titulo TEXT NOT NULL,
        fecha_firma TEXT,
        fecha_vigencia TEXT,
        tipo_acuerdo TEXT NOT NULL DEFAULT 'bilateral',
        boe_referencia TEXT,
        articulos TEXT,
        texto_completo TEXT,
        estado TEXT NOT NULL DEFAULT 'vigente',
        creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_dta_pais_origen ON irs_dta_convention(pais_origen)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_dta_pais_destino ON irs_dta_convention(pais_destino)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_dta_estado ON irs_dta_convention(estado)
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_withholding_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        tipo_renta TEXT NOT NULL,
        tipo_renta_espanol TEXT,
        tipo_retencion_default REAL NOT NULL DEFAULT 30.0,
        tipo_retencion_dta REAL,
        pais_aplicable TEXT,
        descripcion TEXT,
        norma_referencia TEXT,
        articulo_referencia TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_withholding_tipo_renta ON irs_withholding_rule(tipo_renta)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_withholding_pais ON irs_withholding_rule(pais_aplicable)
    """,
    # Seed DTA conventions
    """
    INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo, estado)
    VALUES ('ES_US_DTA', 'US', 'ES', 'Convenio Espana-Estados Unidos DTA', '1993-10-08', '1994-06-01', 'bilateral', 'vigente')
    """,
    """
    INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo, estado)
    VALUES ('ES_GB_DTA', 'GB', 'ES', 'Convenio Espana-Reino Unido DTA', '1987-04-23', '1988-01-01', 'bilateral', 'vigente')
    """,
    """
    INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo, estado)
    VALUES ('ES_MX_DTA', 'MX', 'ES', 'Convenio Espana-Mexico DTA', '1995-11-27', '1997-01-01', 'bilateral', 'vigente')
    """,
    # Seed withholding rules
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion, estado)
    VALUES ('DIVIDEND', 'dividends', 'Dividendos', 30.0, 15.0, NULL, 'Retencion sobre dividendos', 'activo')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion, estado)
    VALUES ('INTEREST', 'interest', 'Intereses', 30.0, 10.0, NULL, 'Retencion sobre intereses', 'activo')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion, estado)
    VALUES ('ROYALTY', 'royalties', 'Regalias', 30.0, 5.0, NULL, 'Retencion sobre regalias', 'activo')
    """,
    """
    INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion, estado)
    VALUES ('CAPITAL_GAINS', 'capital_gains', 'Ganancias de capital', 30.0, NULL, NULL, 'Retencion sobre ganancias de capital', 'activo')
    """,
    # --- XBRL tables ---
    """
    CREATE TABLE IF NOT EXISTS xbrl_filing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        source_path TEXT NOT NULL UNIQUE,
        entity_identifier TEXT NOT NULL,
        period_start TEXT,
        period_end TEXT,
        filing_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_filing_entity_identifier ON xbrl_filing(entity_identifier)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_filing_period_end ON xbrl_filing(period_end)
    """,
    """
    CREATE TABLE IF NOT EXISTS xbrl_fact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_id INTEGER NOT NULL REFERENCES xbrl_filing(id),
        concept TEXT NOT NULL,
        value_raw TEXT NOT NULL,
        value_numeric NUMERIC,
        unit TEXT,
        context_ref TEXT,
        period_start TEXT,
        period_end TEXT,
        entity_identifier TEXT NOT NULL,
        decimals TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (filing_id, concept, context_ref, value_raw)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_fact_filing ON xbrl_fact(filing_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_fact_entity_identifier ON xbrl_fact(entity_identifier)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_fact_concept ON xbrl_fact(concept)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_xbrl_fact_period_end ON xbrl_fact(period_end)
    """,
    # --- Playbooks operativos y evidencia de cumplimiento ---
    """
    CREATE TABLE IF NOT EXISTS playbook_operativo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        obligacion_codigo TEXT NOT NULL,
        descripcion TEXT,
        frecuencia TEXT,
        owner_rol TEXT,
        owner_id TEXT,
        sistema_apoyo TEXT,
        errores_frecuentes TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        version INTEGER NOT NULL DEFAULT 1,
        version_anterior_id INTEGER,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (obligacion_codigo) REFERENCES obligacion_regulatoria(codigo),
        FOREIGN KEY (version_anterior_id) REFERENCES playbook_operativo(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_operativo_obligacion
        ON playbook_operativo(obligacion_codigo)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_operativo_estado
        ON playbook_operativo(estado)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_operativo_owner
        ON playbook_operativo(owner_rol)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_operativo_frecuencia
        ON playbook_operativo(frecuencia)
    """,
    """
    CREATE TABLE IF NOT EXISTS playbook_step (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playbook_id INTEGER NOT NULL,
        orden INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        tipo_paso TEXT NOT NULL DEFAULT 'accion',
        responsable_rol TEXT,
        input_requerido TEXT,
        output_esperado TEXT,
        prerrequisito_step_id INTEGER,
        checklist TEXT NOT NULL DEFAULT '[]',
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playbook_id) REFERENCES playbook_operativo(id) ON DELETE CASCADE,
        FOREIGN KEY (prerrequisito_step_id) REFERENCES playbook_step(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_step_playbook
        ON playbook_step(playbook_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_step_orden
        ON playbook_step(playbook_id, orden)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_step_tipo
        ON playbook_step(tipo_paso)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_playbook_step_responsable
        ON playbook_step(responsable_rol)
    """,
    """
    CREATE TABLE IF NOT EXISTS evidencia_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        playbook_id INTEGER NOT NULL,
        step_id INTEGER,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_evidencia TEXT NOT NULL DEFAULT 'documento',
        formato_requerido TEXT,
        conservacion_dias INTEGER,
        obligatoria BOOLEAN NOT NULL DEFAULT 1,
        estado TEXT NOT NULL DEFAULT 'requerido',
        capturado_en DATE,
        verificado_por TEXT,
        verificado_en DATE,
        nota TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playbook_id) REFERENCES playbook_operativo(id) ON DELETE CASCADE,
        FOREIGN KEY (step_id) REFERENCES playbook_step(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_evidencia_control_playbook
        ON evidencia_control(playbook_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_evidencia_control_step
        ON evidencia_control(step_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_evidencia_control_tipo
        ON evidencia_control(tipo_evidencia)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_evidencia_control_estado
        ON evidencia_control(estado)
    """,
    """
    INSERT INTO playbook_operativo (codigo, nombre, obligacion_codigo, descripcion, frecuencia, owner_rol, estado, version)
    VALUES ('PLAYBOOK-CNMV-IR', 'Preparacion y remision de informacion reservada a la CNMV', 'CNMV-IR-RESERVADA', 'Procedimiento operativo para la preparacion, revision y remision de los estados de informacion reservada exigidos por la Circular 9/2008 de la CNMV a las entidades supervisadas.', 'mensual', 'compliance', 'activo', 1)
    """,
    """
    INSERT INTO playbook_operativo (codigo, nombre, obligacion_codigo, descripcion, frecuencia, owner_rol, estado, version)
    VALUES ('PLAYBOOK-SEPBLAC-INDICIO', 'Comunicacion de operativas sospechosas por indicio (Modelo 19 SEPBLAC)', 'SEPBLAC-INDICIO-M19', 'Procedimiento operativo para la deteccion, evaluacion y comunicacion de operativas sospechosas a SEPBLAC mediante el Modelo 19.', 'eventual', 'compliance', 'activo', 1)
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, checklist)
    SELECT id, 1, 'Recopilar datos contables mensuales', 'Extraer los datos contables y financieros del mes desde el sistema de contabilidad y tesoreria.', 'accion', 'contabilidad', 'Libro mayor, extractos bancarios, registros de tesoreria', 'Dataset de datos contables del periodo', '["Verificar integridad de datos","Conciliar balances","Validar cuentas maestras"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 2, 'Preparar estados financieros reservados', 'Elaborar los estados de informacion reservada conforme al formato exigido por la CNMV (balance, cuenta de resultados, notas).', 'captura', 'contabilidad', 'Dataset de datos contables del periodo, plantillas CNMV', 'Estados financieros reservados del periodo', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 1), '["Formato CNMV vigente","Cruce con estados publicos","Notas a cuentas completas"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 3, 'Revision de compliance', 'El responsable de compliance revisa los estados reservados y valida el cumplimiento de la normativa aplicable.', 'revision', 'compliance', 'Estados financieros reservados, normativa CNMV vigente', 'Informe de revision de compliance firmado', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 2), '["Validar ratios prudenciales","Verificar limites de riesgo","Confirmar cumplimiento normativo"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 4, 'Aprobacion por direccion', 'La direccion general aprueba los estados financieros reservados antes de su remision a la CNMV.', 'aprobacion', 'direccion_general', 'Estados financieros reservados, informe de compliance', 'Acta de aprobacion de estados reservados', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 3), '["Aprobacion formal por escrito","Registro de aprobacion"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 5, 'Remision a la CNMV', 'Enviar los estados reservados a la CNMV a traves del canal electronico habilitado dentro del plazo legal (primeros 20 dias del mes siguiente).', 'accion', 'compliance', 'Estados aprobados, certificado digital, canal CNMV', 'Acuse de recibo de la CNMV', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 4), '["Verificar fecha limite","Confirmar acuse de recibo","Archivar evidencia de envio"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-CNMV-IR-001', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'), 'Estados financieros reservados del periodo', 'Estados de informacion reservada (balance, cuenta de resultados, notas) elaborados conforme a la Circular 9/2008 CNMV.', 'documento', 'pdf', 3650, 1, 'requerido')
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-CNMV-IR-002', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'), (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 3), 'Informe de revision de compliance', 'Informe del responsable de compliance validando el cumplimiento normativo de los estados reservados.', 'documento', 'pdf', 3650, 1, 'requerido')
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-CNMV-IR-003', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'), (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 4), 'Acta de aprobacion por direccion', 'Documento formal de aprobacion de los estados reservados por la direccion general.', 'aprobacion', 'pdf', 3650, 1, 'requerido')
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-CNMV-IR-004', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'), (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 5), 'Acuse de recibo CNMV', 'Confirmacion electronica de envio y recepcion por parte de la CNMV.', 'log', 'xml', 3650, 1, 'requerido')
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, checklist)
    SELECT id, 1, 'Deteccion del indicio', 'Identificar un indicio de actividad sospechosa en las operaciones del cliente o contraparte.', 'accion', 'compliance', 'Datos de la operacion, perfil del cliente, historial transaccional', 'Registro interno del indicio detectado', '["Describir el hecho","Identificar las partes involucradas","Documentar la fecha y monto"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 2, 'Evaluacion interna', 'Evaluar si el indicio constituye una operativa sospechosa que debe comunicarse a SEPBLAC.', 'revision', 'compliance', 'Registro del indicio, analisis de riesgo del cliente, normativa PBCFT', 'Informe de evaluacion con conclusion', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 1), '["Analizar patrones","Verificar historial","Consultar lista de riesgos"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 3, 'Completar Modelo 19', 'Rellenar el formulario oficial Modelo 19 de comunicacion por indicio con toda la informacion requerida.', 'captura', 'compliance', 'Informe de evaluacion, datos del cliente, datos de la operacion, formulario Modelo 19', 'Modelo 19 completado y revisado', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 2), '["Datos completos del sujeto","Descripcion detallada del hecho","Documentacion de soporte"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
    """,
    """
    INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
    SELECT id, 4, 'Comunicacion a SEPBLAC', 'Enviar el Modelo 19 a SEPBLAC a traves del canal electronico oficial dentro del plazo de 1 mes desde el hecho.', 'accion', 'compliance', 'Modelo 19 completado, certificado digital, canal SEPBLAC', 'Confirmacion de envio a SEPBLAC', (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 3), '["Verificar certificado digital","Confirmar recepcion","Archivar copia"]' FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-SEPBLAC-IND-001', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'), 'Registro interno del indicio detectado', 'Documento interno que registra los hechos que constituyen el indicio de actividad sospechosa.', 'documento', 'pdf', 5475, 1, 'requerido')
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-SEPBLAC-IND-002', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'), (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 2), 'Informe de evaluacion interna', 'Informe del responsable de compliance con la evaluacion y conclusion sobre la comunicacion obligatoria.', 'documento', 'pdf', 5475, 1, 'requerido')
    """,
    """
    INSERT INTO evidencia_control (codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia, formato_requerido, conservacion_dias, obligatoria, estado)
    VALUES ('EVID-SEPBLAC-IND-003', (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'), (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 4), 'Confirmacion de envio a SEPBLAC', 'Acuse de recibo o confirmacion electronica del envio del Modelo 19 a SEPBLAC.', 'log', 'xml', 5475, 1, 'requerido')
    """,
    # --- Fase 22: Risk-Control Matrix tables ---
    """
    CREATE TABLE IF NOT EXISTS riesgo_regulatorio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        obligacion_codigo TEXT,
        categoria TEXT,
        severidad TEXT NOT NULL DEFAULT 'media',
        probabilidad TEXT,
        riesgo_inherente TEXT,
        area_responsable TEXT,
        owner_rol TEXT,
        estado TEXT NOT NULL DEFAULT 'identificado',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_riesgo_regulatorio_severidad ON riesgo_regulatorio(severidad)",
    "CREATE INDEX IF NOT EXISTS idx_riesgo_regulatorio_estado ON riesgo_regulatorio(estado)",
    "CREATE INDEX IF NOT EXISTS idx_riesgo_regulatorio_categoria ON riesgo_regulatorio(categoria)",
    "CREATE INDEX IF NOT EXISTS idx_riesgo_regulatorio_nombre ON riesgo_regulatorio(nombre)",
    "CREATE INDEX IF NOT EXISTS idx_riesgo_regulatorio_obligacion ON riesgo_regulatorio(obligacion_codigo)",
    """
    CREATE TABLE IF NOT EXISTS control_interno (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_control TEXT NOT NULL DEFAULT 'preventivo',
        frecuencia TEXT,
        owner_rol TEXT,
        sistema_apoyo TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_control_interno_tipo ON control_interno(tipo_control)",
    "CREATE INDEX IF NOT EXISTS idx_control_interno_estado ON control_interno(estado)",
    "CREATE INDEX IF NOT EXISTS idx_control_interno_owner ON control_interno(owner_rol)",
    """
    CREATE TABLE IF NOT EXISTS riesgo_control_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        riesgo_id INTEGER NOT NULL REFERENCES riesgo_regulatorio(id) ON DELETE CASCADE,
        control_id INTEGER NOT NULL REFERENCES control_interno(id) ON DELETE CASCADE,
        efectividad TEXT NOT NULL DEFAULT 'no_evaluada',
        riesgo_residual TEXT NOT NULL DEFAULT 'no_evaluada',
        frecuencia_prueba TEXT,
        criterio_suficiencia TEXT,
        caducidad_dias INTEGER,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(riesgo_id, control_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_risk_ctrl_link_riesgo ON riesgo_control_link(riesgo_id)",
    "CREATE INDEX IF NOT EXISTS idx_risk_ctrl_link_control ON riesgo_control_link(control_id)",
    "CREATE INDEX IF NOT EXISTS idx_risk_ctrl_link_efectividad ON riesgo_control_link(efectividad)",
    """
    CREATE TABLE IF NOT EXISTS prueba_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id INTEGER NOT NULL REFERENCES riesgo_control_link(id) ON DELETE CASCADE,
        fecha_prueba DATE NOT NULL,
        resultado TEXT NOT NULL,
        evidencia_descripcion TEXT,
        evidencia_url TEXT,
        ejecutado_por TEXT,
        nota TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_prueba_control_link ON prueba_control(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_prueba_control_fecha ON prueba_control(fecha_prueba)",
    "CREATE INDEX IF NOT EXISTS idx_prueba_control_resultado ON prueba_control(resultado)",
    # Seed data for risk-control matrix
    """
    INSERT INTO riesgo_regulatorio (codigo, nombre, obligacion_codigo, categoria, severidad, probabilidad, area_responsable, owner_rol, estado)
    VALUES ('RC-CNMV-001', 'Riesgo de incumplimiento de obligaciones CNMV', 'OBL-CNMV-001', 'regulatorio', 'critica', 'probable', 'compliance', 'compliance_officer', 'identificado')
    """,
    """
    INSERT INTO riesgo_regulatorio (codigo, nombre, obligacion_codigo, categoria, severidad, probabilidad, area_responsable, owner_rol, estado)
    VALUES ('RC-SEPBLAC-001', 'Riesgo de lavado de activos', 'OBL-SEPBLAC-001', 'compliance', 'alta', 'probable', 'compliance', 'compliance_officer', 'identificado')
    """,
    """
    INSERT INTO riesgo_regulatorio (codigo, nombre, obligacion_codigo, categoria, severidad, probabilidad, area_responsable, owner_rol, estado)
    VALUES ('RC-AEPD-001', 'Riesgo de tratamiento ilicito de datos personales', 'OBL-AEPD-001', 'proteccion_datos', 'alta', 'posible', 'legal', 'data_protection_officer', 'identificado')
    """,
    """
    INSERT INTO riesgo_regulatorio (codigo, nombre, obligacion_codigo, categoria, severidad, probabilidad, area_responsable, owner_rol, estado)
    VALUES ('RC-BDE-001', 'Riesgo de no reportado a Banco de Espana', 'OBL-BDE-001', 'regulatorio', 'media', 'posible', 'finanzas', 'treasurer', 'identificado')
    """,
    """
    INSERT INTO riesgo_regulatorio (codigo, nombre, obligacion_codigo, categoria, severidad, probabilidad, area_responsable, owner_rol, estado)
    VALUES ('RC-AEAT-001', 'Riesgo de incumplimiento tributario', 'OBL-AEAT-001', 'tributario', 'alta', 'probable', 'finanzas', 'tax_manager', 'identificado')
    """,
    """
    INSERT INTO control_interno (codigo, nombre, tipo_control, frecuencia, owner_rol, estado)
    VALUES ('CTRL-CNMV-001', 'Revision periodica de obligaciones CNMV', 'preventivo', 'mensual', 'compliance_officer', 'activo')
    """,
    """
    INSERT INTO control_interno (codigo, nombre, tipo_control, frecuencia, owner_rol, estado)
    VALUES ('CTRL-AML-001', 'Monitoreo de operaciones sospechosas', 'detectivo', 'semanal', 'compliance_officer', 'activo')
    """,
    """
    INSERT INTO control_interno (codigo, nombre, tipo_control, frecuencia, owner_rol, estado)
    VALUES ('CTRL-DPO-001', 'Evaluacion de impacto de proteccion de datos', 'preventivo', 'trimestral', 'data_protection_officer', 'activo')
    """,
    """
    INSERT INTO control_interno (codigo, nombre, tipo_control, frecuencia, owner_rol, estado)
    VALUES ('CTRL-FIN-001', 'Conciliacion y reporte financiero mensual', 'preventivo', 'mensual', 'treasurer', 'activo')
    """,
    """
    INSERT INTO control_interno (codigo, nombre, tipo_control, frecuencia, owner_rol, estado)
    VALUES ('CTRL-TAX-001', 'Revision de declaraciones tributarias', 'preventivo', 'trimestral', 'tax_manager', 'activo')
    """,
    # --- Fase 31: MiCA / DAC8-DAC9 / PBC / Antifraude tables ---
    """
    CREATE TABLE IF NOT EXISTS casp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        registration_number TEXT UNIQUE,
        home_member_state TEXT,
        passport_active INTEGER NOT NULL DEFAULT 0,
        services_offered TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_casp_home_state ON casp(home_member_state)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_casp_status ON casp(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS crypto_asset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_type TEXT NOT NULL,
        reference_uid TEXT,
        issuer_jurisdiction TEXT,
        is_sha INTEGER NOT NULL DEFAULT 0,
        market_value_eur NUMERIC(20,2),
        holders_count INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_asset_type ON crypto_asset(asset_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_asset_sha ON crypto_asset(is_sha)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_asset_status ON crypto_asset(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS tokenized_asset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        underlying_type TEXT,
        issuer_id INTEGER,
        face_value NUMERIC(20,2),
        total_amount NUMERIC(20,2),
        listing_date DATE,
        regulated_market TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tokenized_asset_type ON tokenized_asset(underlying_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tokenized_asset_status ON tokenized_asset(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS wallet_custodian (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        wallet_type TEXT,
        custody_mechanism TEXT,
        insurance_coverage NUMERIC(20,2),
        audit_frequency TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_wallet_custodian_type ON wallet_custodian(wallet_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_wallet_custodian_status ON wallet_custodian(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS crypto_transaction (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_wallet TEXT,
        receiver_wallet TEXT,
        sender_jurisdiction TEXT,
        receiver_jurisdiction TEXT,
        asset_type TEXT,
        amount NUMERIC(38,18),
        value_eur NUMERIC(20,2),
        timestamp TIMESTAMP,
        reporting_period TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_transaction_asset ON crypto_transaction(asset_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_transaction_period ON crypto_transaction(reporting_period)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_transaction_sender ON crypto_transaction(sender_wallet)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crypto_transaction_receiver ON crypto_transaction(receiver_wallet)
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_reporting_entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tin TEXT,
        entity_type TEXT,
        member_state TEXT,
        dac8_registered INTEGER NOT NULL DEFAULT 0,
        dac9_registered INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_reporting_entity_tin ON dac_reporting_entity(tin)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_reporting_entity_state ON dac_reporting_entity(member_state)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_reporting_entity_type ON dac_reporting_entity(entity_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_reporting_entity_status ON dac_reporting_entity(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_crypto_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        reporting_period TEXT,
        submitted_at TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'draft',
        crypto_transactions_count INTEGER NOT NULL DEFAULT 0,
        wallet_holders_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_crypto_report_entity ON dac_crypto_report(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_crypto_report_period ON dac_crypto_report(reporting_period)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_crypto_report_status ON dac_crypto_report(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_wallet_holder (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,
        wallet_address TEXT,
        holder_tin TEXT,
        holder_member_state TEXT,
        holder_type TEXT,
        total_value_eur NUMERIC(20,2),
        verification_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_wallet_holder_report ON dac_wallet_holder(report_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_wallet_holder_address ON dac_wallet_holder(wallet_address)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_wallet_holder_state ON dac_wallet_holder(holder_member_state)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dac_wallet_holder_status ON dac_wallet_holder(verification_status)
    """,
    """
    CREATE TABLE IF NOT EXISTS pbc_obligated_subject (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_type TEXT,
        tin TEXT,
        registration_number TEXT,
        supervisory_authority TEXT,
        pbc_license TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_pbc_obligated_subject_type ON pbc_obligated_subject(subject_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_pbc_obligated_subject_tin ON pbc_obligated_subject(tin)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_pbc_obligated_subject_status ON pbc_obligated_subject(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS pbc_internal_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligated_subject_id INTEGER,
        risk_assessment_date DATE,
        compliance_officer TEXT,
        internal_reporting_channel INTEGER NOT NULL DEFAULT 0,
        training_program INTEGER NOT NULL DEFAULT 0,
        audit_trail INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_pbc_internal_control_subject ON pbc_internal_control(obligated_subject_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS suspicious_activity_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligated_subject_id INTEGER,
        submission_date DATE,
        description TEXT,
        severity TEXT,
        status TEXT NOT NULL DEFAULT 'filed',
        sepblac_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_suspicious_activity_report_subject ON suspicious_activity_report(obligated_subject_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_suspicious_activity_report_status ON suspicious_activity_report(status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_suspicious_activity_report_severity ON suspicious_activity_report(severity)
    """,
    """
    CREATE TABLE IF NOT EXISTS beneficial_owner_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        owner_name TEXT,
        ownership_percentage NUMERIC(5,2),
        acquisition_date DATE,
        verification_method TEXT,
        verification_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_beneficial_owner_record_entity ON beneficial_owner_record(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS fraud_prevention_program (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        code_of_conduct INTEGER NOT NULL DEFAULT 0,
        internal_reporting_system INTEGER NOT NULL DEFAULT 0,
        training_schedule TEXT,
        audit_frequency TEXT,
        compliance_officer_name TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_fraud_prevention_program_entity ON fraud_prevention_program(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS fraud_risk_assessment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        assessment_date DATE,
        risk_areas TEXT,
        mitigation_measures TEXT,
        next_review_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_fraud_risk_assessment_entity ON fraud_risk_assessment(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS fraud_incident (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        incident_date DATE,
        description TEXT,
        amount_eur NUMERIC(12,2),
        status TEXT NOT NULL DEFAULT 'open',
        resolution_date DATE,
        regulatory_notification INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_fraud_incident_entity ON fraud_incident(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_fraud_incident_status ON fraud_incident(status)
    """,
    # --- Fase 31.10: PSD2/PSD3, SEPA, Consumer Credit, IDD, Solvency II tables ---
    """
    CREATE TABLE IF NOT EXISTS psd2_aspsp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        bic TEXT,
        psd2_license TEXT,
        strong_customer_auth_applied INTEGER NOT NULL DEFAULT 0,
        api_version TEXT DEFAULT 'v2',
        regulatory_status TEXT NOT NULL DEFAULT 'registered',
        home_member_state TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_psd2_aspsp_entity ON psd2_aspsp(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_aisp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        registration_number TEXT,
        registration_id TEXT,
        access_scope TEXT,
        valid_from DATE,
        valid_to DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_psd2_aisp_entity ON psd2_aisp(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_pisp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        registration_number TEXT,
        authorization_status TEXT NOT NULL DEFAULT 'authorized',
        home_member_state TEXT,
        psd3_transition_status TEXT DEFAULT 'not_started',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_psd2_pisp_entity ON psd2_pisp(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_consent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        aspsp_id INTEGER,
        consent_type TEXT NOT NULL DEFAULT 'AIS',
        accounts_accessed TEXT,
        payment_count_limit INTEGER,
        used_count INTEGER NOT NULL DEFAULT 0,
        valid_from DATE,
        valid_to DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_psd2_consent_aspsp ON psd2_consent(aspsp_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_incident_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aspsp_id INTEGER,
        incident_type TEXT,
        severity TEXT NOT NULL DEFAULT 'medium',
        description TEXT,
        reported_to_bde INTEGER NOT NULL DEFAULT 0,
        reported_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_psd2_incident_aspsp ON psd2_incident_report(aspsp_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS sepa_payment_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_version TEXT NOT NULL,
        payment_type TEXT NOT NULL,
        service_level TEXT NOT NULL,
        local_instrument TEXT,
        category_purpose TEXT,
        cut_off_time TEXT,
        settlement_days INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_contract (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lender_id INTEGER,
        borrower_id INTEGER,
        credit_type TEXT NOT NULL DEFAULT 'installment',
        principal_amount NUMERIC(12,2),
        annual_percentage_rate NUMERIC(6,2),
        total_amount NUMERIC(12,2),
        term_months INTEGER,
        purpose TEXT,
        signing_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_consumer_credit_contract_lender ON consumer_credit_contract(lender_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_disclosure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER,
        fap NUMERIC(6,2),
        total_cost NUMERIC(12,2),
        regular_payment NUMERIC(10,2),
        amortization_schedule_url TEXT,
        right_of_withdrawal INTEGER NOT NULL DEFAULT 1,
        early_repayment_penalty NUMERIC(10,2),
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_consumer_credit_disclosure_contract ON consumer_credit_disclosure(contract_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_overindebtedness (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower_id INTEGER,
        declared_date DATE,
        total_debt NUMERIC(12,2),
        monthly_income NUMERIC(10,2),
        unsecured_debt NUMERIC(12,2),
        procedure_status TEXT NOT NULL DEFAULT 'declared',
        court_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_consumer_credit_overindebtedness_borrower ON consumer_credit_overindebtedness(borrower_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS idd_distributor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        registration_number TEXT,
        insurance_ao TEXT,
        products_covered TEXT,
        professional_indemnity INTEGER NOT NULL DEFAULT 0,
        training_certified INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_idd_distributor_entity ON idd_distributor(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS idd_product_uci (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_type TEXT NOT NULL DEFAULT 'life',
        risk_coverage TEXT,
        cost_breakdown TEXT,
        exit_costs TEXT,
        taxes TEXT,
        version TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_idd_product_uci_product ON idd_product_uci(product_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS solvency_ii_entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        entity_type TEXT NOT NULL DEFAULT 'life',
        solvency_capital_requirement NUMERIC(14,2),
        minimum_capital_requirement NUMERIC(14,2),
        solvency_ratio NUMERIC(8,2),
        reporting_date DATE,
        home_supervisor TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_solvency_ii_entity_entity ON solvency_ii_entity(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS solvency_ii_sfp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        reporting_period TEXT,
        fund_breakdown TEXT,
        asset_allocation TEXT,
        url TEXT,
        status TEXT NOT NULL DEFAULT 'published',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_solvency_ii_sfp_entity ON solvency_ii_sfp(entity_id)
    """,
    # --- Fase 31.8: MiFID II/MiFIR tables ---
    """
    CREATE TABLE IF NOT EXISTS mifid_client_category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        category TEXT NOT NULL,
        assessment_date DATE,
        knowledge_level TEXT,
        experience_level TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_client_category_entity ON mifid_client_category(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_client_category_category ON mifid_client_category(category)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_client_category_status ON mifid_client_category(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_suitability_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        product_id INTEGER,
        assessment_date DATE,
        suitability_score INTEGER,
        recommendation TEXT,
        advisor_id INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_suitability_client ON mifid_suitability_report(client_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_suitability_status ON mifid_suitability_report(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_best_execution_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        venue TEXT,
        execution_price NUMERIC(20,6),
        market_impact NUMERIC(10,4),
        speed_ms INTEGER,
        quality_metrics TEXT,
        execution_timestamp TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_best_exec_venue ON mifid_best_execution_record(venue)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_best_exec_status ON mifid_best_execution_record(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_conflict_of_interest_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT,
        conflict_type TEXT,
        description TEXT,
        mitigation_measure TEXT,
        identified_date DATE,
        review_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_coi_type ON mifid_conflict_of_interest_registry(conflict_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_coi_status ON mifid_conflict_of_interest_registry(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_product_governance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        target_market TEXT,
        distribution_channels TEXT,
        key_features TEXT,
        risk_level INTEGER,
        review_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_pg_product ON mifid_product_governance(product_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_pg_risk ON mifid_product_governance(risk_level)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_pg_status ON mifid_product_governance(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_order_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        instrument TEXT,
        direction TEXT,
        quantity NUMERIC(20,4),
        price NUMERIC(20,6),
        timestamp TIMESTAMP,
        venue TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        retention_until DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_order_client ON mifid_order_record(client_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_order_instrument ON mifid_order_record(instrument)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_order_status ON mifid_order_record(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_insider_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insider_name TEXT,
        insider_tin TEXT,
        entity_id INTEGER,
        inside_information_description TEXT,
        date_created DATE,
        date_removed DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_insider_entity ON mifid_insider_list(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_insider_status ON mifid_insider_list(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_compensation_policy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        policy_version TEXT,
        alignment_score INTEGER,
        risk_adjustment_applied INTEGER NOT NULL DEFAULT 0,
        approval_date DATE,
        next_review DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_comp_entity ON mifid_compensation_policy(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mifid_comp_status ON mifid_compensation_policy(status)
    """,
    # --- Fase 31.8: MAR tables ---
    """
    CREATE TABLE IF NOT EXISTS mar_insider_transaction (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ppi_name TEXT,
        ppi_role TEXT,
        instrument TEXT,
        transaction_type TEXT,
        quantity NUMERIC(20,4),
        value_eur NUMERIC(20,2),
        price NUMERIC(20,6),
        date_time TIMESTAMP,
        country TEXT,
        status TEXT NOT NULL DEFAULT 'reported',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_insider_txn_ppi ON mar_insider_transaction(ppi_name)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_insider_txn_instrument ON mar_insider_transaction(instrument)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_insider_txn_status ON mar_insider_transaction(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_suspicious_transaction_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        instrument TEXT,
        pattern_description TEXT,
        detection_method TEXT,
        severity TEXT,
        submitted_to_cnmv INTEGER NOT NULL DEFAULT 0,
        cnmv_reference TEXT,
        status TEXT NOT NULL DEFAULT 'under_review',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_str_entity ON mar_suspicious_transaction_report(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_str_instrument ON mar_suspicious_transaction_report(instrument)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_str_status ON mar_suspicious_transaction_report(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_market_manipulation_indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_type TEXT,
        instrument TEXT,
        time_window TEXT,
        volume_anomaly_pct NUMERIC(8,2),
        price_anomaly_pct NUMERIC(8,2),
        confidence_score NUMERIC(5,4),
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_mmi_pattern ON mar_market_manipulation_indicator(pattern_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_mmi_instrument ON mar_market_manipulation_indicator(instrument)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_mmi_status ON mar_market_manipulation_indicator(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_insider_communication (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content_summary TEXT,
        timestamp TIMESTAMP,
        channel TEXT,
        inside_info_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_ic_sender ON mar_insider_communication(sender_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_ic_receiver ON mar_insider_communication(receiver_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_mar_ic_ts ON mar_insider_communication(timestamp)
    """,
    # --- Fase 31.8: DORA tables ---
    """
    CREATE TABLE IF NOT EXISTS dora_tic_incident (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        incident_severity TEXT,
        description TEXT,
        impact_scope TEXT,
        detection_date DATE,
        resolution_date DATE,
        root_cause TEXT,
        classification TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tic_severity ON dora_tic_incident(incident_severity)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tic_class ON dora_tic_incident(classification)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tic_status ON dora_tic_incident(status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tic_detection ON dora_tic_incident(detection_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_third_party_provider (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name TEXT,
        provider_type TEXT,
        criticality_assessment TEXT,
        contract_start DATE,
        contract_end DATE,
        eu_supervision_status TEXT,
        exit_strategy TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tpp_type ON dora_third_party_provider(provider_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tpp_crit ON dora_third_party_provider(criticality_assessment)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_tpp_status ON dora_third_party_provider(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_ict_risk_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        risk_description TEXT,
        likelihood TEXT,
        impact TEXT,
        mitigation TEXT,
        owner TEXT,
        review_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_ict_risk_entity ON dora_ict_risk_register(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_ict_risk_likelihood ON dora_ict_risk_register(likelihood)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_ict_risk_status ON dora_ict_risk_register(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_penetration_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        test_type TEXT,
        tester TEXT,
        test_date DATE,
        findings_count INTEGER,
        critical_findings INTEGER,
        remediation_deadline DATE,
        status TEXT NOT NULL DEFAULT 'scheduled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_pt_entity ON dora_penetration_test(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_pt_type ON dora_penetration_test(test_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_pt_status ON dora_penetration_test(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_incident_classification_framework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        framework_version TEXT,
        severity_thresholds TEXT,
        reporting_timelines TEXT,
        effective_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_icf_version ON dora_incident_classification_framework(framework_version)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_dora_icf_status ON dora_incident_classification_framework(status)
    """,
    # --- Fase 31.8: PRIIPs / LIVMC tables ---
    """
    CREATE TABLE IF NOT EXISTS priips_kid (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_type TEXT,
        currency TEXT,
        risk_scale INTEGER,
        cost_impact TEXT,
        negative_scenario_returns TEXT,
        version TEXT,
        publication_date DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_kid_product ON priips_kid(product_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_kid_risk ON priips_kid(risk_scale)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_kid_status ON priips_kid(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS priips_product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER,
        product_name TEXT,
        underlying_assets TEXT,
        maturity_date DATE,
        currency TEXT,
        min_investment NUMERIC(20,2),
        distribution_channels TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_product_issuer ON priips_product(issuer_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_product_currency ON priips_product(currency)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_priips_product_status ON priips_product(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS livmc_client_protection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        protection_type TEXT,
        provider_id INTEGER,
        coverage_amount NUMERIC(20,2),
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_cp_client ON livmc_client_protection(client_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_cp_type ON livmc_client_protection(protection_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_cp_status ON livmc_client_protection(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS livmc_voice_procedure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        procedure_type TEXT,
        description TEXT,
        effective_date DATE,
        next_review DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_vp_entity ON livmc_voice_procedure(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_vp_type ON livmc_voice_procedure(procedure_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_livmc_vp_status ON livmc_voice_procedure(status)
    """,
    # --- Fase 31.8: Transparencia tables ---
    """
    CREATE TABLE IF NOT EXISTS transparency_issuer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER,
        listing_market TEXT,
        ticker TEXT,
        reporting_frequency TEXT,
        home_member_state TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_issuer_market ON transparency_issuer(listing_market)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_issuer_ticker ON transparency_issuer(ticker)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_issuer_status ON transparency_issuer(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_regulated_information (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER,
        info_type TEXT,
        publication_date DATE,
        content_url TEXT,
        filing_reference TEXT,
        status TEXT NOT NULL DEFAULT 'published',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ri_issuer ON transparency_regulated_information(issuer_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ri_type ON transparency_regulated_information(info_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ri_date ON transparency_regulated_information(publication_date)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ri_status ON transparency_regulated_information(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_voting_rights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER,
        shareholder_id INTEGER,
        voting_rights_pct NUMERIC(6,4),
        date_acquired DATE,
        date_reported DATE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_vr_issuer ON transparency_voting_rights(issuer_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_vr_shareholder ON transparency_voting_rights(shareholder_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_vr_date ON transparency_voting_rights(date_acquired)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_vr_status ON transparency_voting_rights(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_internal_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        designated_persons TEXT,
        internal_procedure TEXT,
        retention_period TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ir_entity ON transparency_internal_rule(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transp_ir_status ON transparency_internal_rule(status)
    """,
    # --- Fase 31.9: SFDR tables ---
    """
    CREATE TABLE IF NOT EXISTS sfdr_product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        product_type TEXT NOT NULL DEFAULT 'other',
        sustainability_strategy TEXT,
        principal_adverse_impact TEXT DEFAULT 'false',
        paci_aggregated TEXT,
        paci_detailed_url TEXT,
        distribution_country TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_product_type ON sfdr_product(product_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_product_status ON sfdr_product(status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_product_name ON sfdr_product(product_name)
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_paci_indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        indicator_code TEXT NOT NULL,
        indicator_name TEXT NOT NULL,
        value NUMERIC,
        unit TEXT,
        reference_period TEXT,
        methodology TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_paci_product ON sfdr_paci_indicator(product_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_paci_code ON sfdr_paci_indicator(indicator_code)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_paci_status ON sfdr_paci_indicator(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_entity_paci (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        aggregated_paci TEXT,
        sectoral_decarbonization TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_epaci_entity ON sfdr_entity_paci(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_epaci_year ON sfdr_entity_paci(reporting_year)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_epaci_status ON sfdr_entity_paci(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_pre_contractual (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        url TEXT,
        published_date DATE,
        version TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_pc_product ON sfdr_pre_contractual(product_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_pc_type ON sfdr_pre_contractual(document_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_pc_status ON sfdr_pre_contractual(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_annual_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        paci_results TEXT,
        engagement_activities TEXT,
        good_practice_examples TEXT,
        url TEXT,
        published_date DATE,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_ar_entity ON sfdr_annual_report(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_ar_year ON sfdr_annual_report(reporting_year)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_sfdr_ar_status ON sfdr_annual_report(status)
    """,
    # --- CSRD (31.9.2) ---
    """
    CREATE TABLE IF NOT EXISTS csrd_entity_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        esap_url TEXT,
        assurance_status TEXT DEFAULT 'none',
        reporting_standard TEXT DEFAULT 'ESGAS',
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_er_entity ON csrd_entity_report(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_er_year ON csrd_entity_report(reporting_year)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_er_status ON csrd_entity_report(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_esg_data_point (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        indicator_code TEXT,
        value NUMERIC,
        unit TEXT,
        scope INTEGER,
        verification_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_edp_report ON csrd_esg_data_point(report_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_edp_topic ON csrd_esg_data_point(topic)
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_ess (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        standard_code TEXT NOT NULL,
        topic TEXT,
        applicable_from_year INTEGER,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_ess_code ON csrd_ess(standard_code)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_ess_topic ON csrd_ess(topic)
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_double_materiality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        impact_materiality TEXT,
        financial_materiality TEXT,
        assessment_date DATE,
        key_impacts TEXT,
        key_dependencies TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_dm_entity ON csrd_double_materiality(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_csrd_dm_year ON csrd_double_materiality(assessment_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS aifmd_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name TEXT NOT NULL,
        aifm_id INTEGER,
        fund_type TEXT NOT NULL DEFAULT 'alternative',
        registration_date DATE,
        home_member_state TEXT,
        cross_border_passport INTEGER NOT NULL DEFAULT 0,
        total_aum_eur NUMERIC,
        investor_type TEXT DEFAULT 'professional',
        lock_up_period TEXT,
        redemption_frequency TEXT,
        leverage_method TEXT,
        leverage_max_pct NUMERIC,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_fund_name ON aifmd_fund(fund_name)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_fund_type ON aifmd_fund(fund_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_fund_status ON aifmd_fund(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS ucits_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name TEXT NOT NULL,
        management_company TEXT,
        registration_date DATE,
        home_member_state TEXT,
        cross_border_passport INTEGER NOT NULL DEFAULT 0,
        total_aum_eur NUMERIC,
        depositary_id INTEGER,
        krid_url TEXT,
        investment_strategy TEXT,
        risk_profile TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ucits_fund_name ON ucits_fund(fund_name)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ucits_fund_company ON ucits_fund(management_company)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ucits_fund_status ON ucits_fund(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS aifmd_regulatory_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL,
        report_type TEXT NOT NULL DEFAULT 'annual',
        reporting_period TEXT,
        url TEXT,
        filed_date DATE,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_rr_fund ON aifmd_regulatory_report(fund_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_rr_type ON aifmd_regulatory_report(report_type)
    """,
    """
    CREATE TABLE IF NOT EXISTS ucits_regulatory_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL,
        report_type TEXT NOT NULL DEFAULT 'annual',
        reporting_period TEXT,
        url TEXT,
        filed_date DATE,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ucits_rr_fund ON ucits_regulatory_report(fund_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ucits_rr_type ON ucits_regulatory_report(report_type)
    """,
    """
    CREATE TABLE IF NOT EXISTS aifmd_liquidity_management (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL,
        redemption_suspended INTEGER NOT NULL DEFAULT 0,
        suspension_date DATE,
        gating_applied INTEGER NOT NULL DEFAULT 0,
        swing_price_applied INTEGER NOT NULL DEFAULT 0,
        side_pocket_applied INTEGER NOT NULL DEFAULT 0,
        stress_test_result TEXT,
        valuation_frequency TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_aifmd_lm_fund ON aifmd_liquidity_management(fund_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS crd_capital_position (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_date DATE NOT NULL,
        cet1_ratio NUMERIC(10,4),
        tier1_ratio NUMERIC(10,4),
        total_capital_ratio NUMERIC(10,4),
        cet1_amount NUMERIC(20,2),
        tier1_amount NUMERIC(20,2),
        total_capital_amount NUMERIC(20,2),
        leverage_ratio NUMERIC(10,4),
        risk_weighted_assets NUMERIC(20,2),
        status TEXT NOT NULL DEFAULT 'filed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crd_cp_entity ON crd_capital_position(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crd_cp_date ON crd_capital_position(reporting_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS crd_stress_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        test_date DATE NOT NULL,
        scenario_name TEXT,
        cet1_impact_pct NUMERIC(10,4),
        tier1_impact_pct NUMERIC(10,4),
        capital_ratio_post_test NUMERIC(10,4),
        competent_authority TEXT,
        status TEXT NOT NULL DEFAULT 'published',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crd_st_entity ON crd_stress_test(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_crd_st_date ON crd_stress_test(test_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS brrd_bail_in (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        total_eligible_liabilities NUMERIC(20,2),
        mrel_target_pct NUMERIC(10,4),
        mrel_compliance_pct NUMERIC(10,4),
        internal_mrel NUMERIC(10,4),
        resolution_status TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_brrd_bi_entity ON brrd_bail_in(entity_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS emir_trade_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT NOT NULL,
        asset_class TEXT NOT NULL DEFAULT 'equity',
        instrument_class TEXT,
        clearing_obligation_applied INTEGER NOT NULL DEFAULT 0,
        reporting_delay_days INTEGER,
        counterparty_type TEXT DEFAULT 'financial',
        status TEXT NOT NULL DEFAULT 'reported',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_emir_tr_trade_id ON emir_trade_report(trade_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_emir_tr_asset_class ON emir_trade_report(asset_class)
    """,
    """
    CREATE TABLE IF NOT EXISTS emir_clearing_member (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        emir_registration TEXT,
        clearing_type TEXT NOT NULL DEFAULT 'central',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_emir_cm_entity ON emir_clearing_member(entity_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_emir_cm_type ON emir_clearing_member(clearing_type)
    """,
]

with engine.begin() as conn:
    for statement in STATEMENTS:
        conn.execute(text(statement))

LINEA_CRITERIO_SCHEMA_STATEMENTS = [
    "DROP TABLE IF EXISTS linea_criterio_referencia",
    "DROP TABLE IF EXISTS linea_criterio",
    """
    CREATE TABLE linea_criterio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        cuestion_practica TEXT NOT NULL,
        descripcion TEXT,
        criterio_dominante TEXT,
        matices TEXT,
        excepciones TEXT,
        ultimo_cambio DATE,
        estado TEXT NOT NULL DEFAULT 'borrador',
        autor_id INTEGER,
        revisor_id INTEGER,
        activo BOOLEAN NOT NULL DEFAULT 1,
        ambitos TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX ix_linea_criterio_estado ON linea_criterio(estado)",
    "CREATE INDEX ix_linea_criterio_activo ON linea_criterio(activo)",
    """
    CREATE TABLE linea_criterio_referencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linea_id INTEGER NOT NULL REFERENCES linea_criterio(id) ON DELETE CASCADE,
        documento_referencia TEXT NOT NULL,
        tipo_documento TEXT,
        organismo_emisor TEXT,
        fecha DATE,
        rol_en_linea TEXT DEFAULT 'soporte',
        orden INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(linea_id, documento_referencia)
    )
    """,
    "CREATE INDEX ix_linea_criterio_referencia_linea ON linea_criterio_referencia(linea_id)",
    "CREATE INDEX ix_linea_criterio_referencia_doc ON linea_criterio_referencia(documento_referencia)",
    """
    INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, estado, autor_id, revisor_id, ambitos) VALUES
    ('IVA reducido en restauracion', 'Se aplica el tipo reducido del IVA a servicios de restauracion?',
     'Analizar la evolucion del criterio del Tribunal Supremo sobre la aplicacion del tipo reducido (10%) al servicio de restauracion y hosteleria, frente al tipo general (21%).',
     'El Tribunal Supremo ha ido restringiendo el ambito de aplicacion del tipo reducido, exigiendo que el servicio preste efectivamente la actividad de restauracion y no mera cesion de alimentos.',
     'Distinguir entre venta al por menor de alimentos (tipo reducido) y servicio de restauracion (tambien reducido pero con requisitos estrictos de prestacion).',
     'No aplica a ventas a granel o productos envasados sin servicio adicional.',
     'vigente', 1, 1, '["jurisprudencia_tributaria"]'),
    ('Comisiones preferencia e indiferencia', 'Las sociedades de valores pueden cobrar comisiones que favorezcan a unos clientes sobre otros?',
     'Analizar los limites de las comisiones de preferencia e indiferencia bajo MiFID II y la normativa CNMV, y cuando constituyen conflicto de interes.',
     'Permitidas con limites estrictos y transparencia total al cliente. Deben reflejar costes reales y no superar los beneficios para el cliente.',
     'Requiere divulgacion previa al cliente y registro documental de las comisiones aplicadas.',
     'No aplica a operaciones institucionales con acuerdos de soft dollar documentados.',
     'vigente', 1, 1, '["jurisprudencia_mercantil_regulatoria"]'),
    ('Ejecucion preferente de ordenes', 'Que criterios debe seguir una sociedad de valores para garantizar la ejecucion preferente?',
     'Analizar las obligaciones de best execution bajo art. 61 LMCV y Reg. 2017/565, incluyendo calidad ejecucion, costes, rapidez y probabilidad de ejecucion.',
     'Obligacion continua de tomar medidas diligentes para obtener el mejor resultado para el cliente. Factor de calidad incluye precio, costes, rapidez, ejecucion, size, probabilidad.',
     'Debe mantener politica de ejecucion documentada y revisar periodicamente los destinos de orden.',
     'Puede ejecutarse por medios exclusivos solo si el cliente acuerda explicitamente.',
     'vigente', 1, 1, '["jurisprudencia_mercantil_regulatoria"]'),
    ('Adecuacion y conveniencia de productos', 'Cual es la diferencia entre evaluar adecuacion y conveniencia, y cuando aplica cada una?',
     'Suitability (art. 53 LMCV) aplica a servicios de inversion: evaluar perfil del cliente vs caracteristicas del producto. Appropriateness (art. 54 LMCV) aplica solo a servicios de ejecucion: verificar conocimientos basicos.',
     'Suitability exige conocimiento de situacion financiera, objetivos, tolerancia riesgo. Appropriateness solo verifica conocimientos y experiencia en la categoria de producto.',
     'Si el cliente proporciona informacion actualizada automaticamente se considera adecuada. No se requiere suitability para servicios de ejecucion no asistida.',
     'Excepcion: clientes institucionales, profesionales automaticos y productos no complejos para apropiateness.',
     'vigente', 1, 1, '["jurisprudencia_mercantil_regulatoria"]'),
    ('Informacion privilegiada y listas insider', 'Que obligaciones tiene la sociedad de valores en materia de informacion privilegiada?',
     'Analizar obligaciones MAR: creacion y mantenimiento de listas insider, listas de vigilancia, restriccion de personas con acceso, y reporte de operaciones de PPI.',
     'Obligacion de crear lista insider para cada informacion privilegiada. Personas en la lista no pueden operar en el emisor. Lista de vigilancia para empleados con acceso recurrente.',
     'Deben existir procedimientos escritos y controles tecnologicos. Las listas deben actualizarse en tiempo real.',
     'Excepcion para M&A con acuerdos de confidencialidad y necesidad de conocimiento justificada.',
     'vigente', 1, 1, '["jurisprudencia_mercantil_regulatoria"]'),
    ('Gobierno de productos (product governance)', 'Como debe disenarse y distribuirse un producto financiero bajo MiFID II?',
     'Analizar obligaciones de fabricacion y distribucion: identificar mercado objetivo, restriccion de distribucion al target, revision periodica de productos.',
     'El fabricante debe definir mercado objetivo y tomar medidas para que el producto llegue a ese target. El distribuidor debe considerar si el target es consistente.',
     'Revision periodica obligatoria. Si el producto se vende fuera del target, notificar al fabricante y suspender distribucion si es necesario.',
     'No aplica a productos para clientes profesionales o institucionales en la misma medida.',
     'vigente', 1, 1, '["jurisprudencia_mercantil_regulatoria"]'),
    ('Comunicacion de indicios de LP', 'Cuales son los deberes de comunicacion de indicios de lavado a SEPBLAC?',
     'Analizar obligaciones de comunicacion de operaciones sospechosas (indicios) a SEPBLAC, deber de abstencion, y sanciones por incumplimiento.',
     'Obligacion de comunicar sin delay cuando existan indicios de LP. Prohibicion absoluta de informar al cliente (tipping-off). Retencion de fondos solo via orden judicial.',
     'La comunicacion es confidencial. SEPBLAC puede solicitar informacion complementaria. El deber de comunicacion prevalece sobre secreto profesional o contractual.',
     'Excepcion: abogados y asesores legales con representacion judicial (solo para origen de fondos del cliente).',
     'vigente', 1, 1, '["jurisprudencia_pbcft"]')
    """,
    """
    INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
    (1, 'STS-2847/2025', 'sentencia', 'Tribunal Supremo', '2025-06-15', 'doctrina_principal', 1),
    (1, 'V0123/2024', 'consulta_vinculante', 'DGT', '2024-03-10', 'soporte_complementario', 2),
    (1, 'BOE-A-2012-11194', 'ley', 'Boe', '2012-09-28', 'base_legal', 3),
    (2, 'Circular 3/2015 CNMV', 'circular', 'CNMV', '2015-05-14', 'base_regulatoria', 1),
    (2, 'STS-1234/2024', 'sentencia', 'Tribunal Supremo', '2024-11-20', 'doctrina_principal', 2),
    (3, 'Reg. UE 2017/565', 'reglamento', 'Union Europea', '2016-10-07', 'base_legal', 1),
    (3, 'V0456/2024', 'consulta_vinculante', 'DGT', '2024-06-15', 'soporte_complementario', 2),
    (3, 'STS-5678/2023', 'sentencia', 'Tribunal Supremo', '2023-09-12', 'doctrina_principal', 3),
    (4, 'Directiva 2014/65/UE (MiFID II)', 'directiva', 'Union Europea', '2014-06-04', 'base_legal', 1),
    (4, 'LMCV art. 52-54', 'ley', 'Boe', '2014-07-30', 'base_legal', 2),
    (4, 'V0789/2024', 'consulta_vinculante', 'DGT', '2024-08-20', 'soporte_complementario', 3),
    (5, 'Reg. UE 596/2014 (MAR)', 'reglamento', 'Union Europea', '2014-04-16', 'base_legal', 1),
    (5, 'STS-9012/2024', 'sentencia', 'Tribunal Supremo', '2024-02-28', 'doctrina_principal', 2),
    (5, 'Circular 2/2017 CNMV', 'circular', 'CNMV', '2017-03-22', 'base_regulatoria', 3),
    (6, 'Reg. UE 2017/565 anexo I', 'reglamento', 'Union Europea', '2016-10-07', 'base_legal', 1),
    (6, 'Circular 5/2018 CNMV', 'circular', 'CNMV', '2018-09-10', 'base_regulatoria', 2),
    (7, 'Ley 10/2010 PREV LPFT', 'ley', 'Boe', '2010-07-26', 'base_legal', 1),
    (7, 'RD 289/2022', 'real_decreto', 'Boe', '2022-05-17', 'base_legal', 2),
    (7, 'STS-3456/2024', 'sentencia', 'Tribunal Supremo', '2024-04-10', 'doctrina_principal', 3)
    """,
]

# Module-level execution: create linea_criterio tables + seed for all tests
with engine.begin() as conn:
    for statement in LINEA_CRITERIO_SCHEMA_STATEMENTS:
        conn.execute(text(statement))


def _seed_linea_criterio(conn):
    from sqlalchemy import text
    for statement in LINEA_CRITERIO_SCHEMA_STATEMENTS:
        conn.execute(text(statement))


@pytest.fixture
def linea_criterio_test_db():
    with engine.begin() as conn:
        for statement in LINEA_CRITERIO_SCHEMA_STATEMENTS:
            conn.execute(text(statement))
    yield engine


@pytest.fixture
def pgc_catalog():
    return PGC_CATALOG


@pytest.fixture
def xbrl_fixture_catalog():
    return _derive_xbrl_fixture_catalog()


@pytest.fixture
def pgc_test_db():
    with engine.begin() as conn:
        for statement in PGC_SCHEMA_STATEMENTS:
            conn.execute(text(statement))
        _seed_pgc(conn)
    yield engine


@pytest.fixture
def xbrl_test_db():
    with engine.begin() as conn:
        for statement in XBRL_SCHEMA_STATEMENTS:
            conn.execute(text(statement))
        _seed_xbrl(conn)
    yield engine


@pytest.fixture
def xbrl_taxonomy_seed(xbrl_test_db):
    from apps.workers import xbrl_taxonomy as xbrl_tax
    xbrl_tax.seed_taxonomy(engine=engine)
    return engine


@pytest.fixture
def pgc_xbrl_mapping_seed():
    """Seed pgc_xbrl_mapping table and run the mapping worker for enriched-facts tests."""
    from apps.workers import pgc_xbrl_mapping as mapper
    mapper.run_sync(engine=engine)
    return engine


@pytest.fixture
def pgc_xbrl_enriched_db(pgc_test_db, xbrl_test_db, pgc_xbrl_mapping_seed):
    """Combined fixture: PGC accounts + XBRL schema/facts + pgc_xbrl_mapping for enriched-facts endpoint."""
    # The endpoint needs pgc_cuenta (from pgc_test_db), xbrl tables (from xbrl_test_db),
    # and pgc_xbrl_mapping (from pgc_xbrl_mapping_seed).
    # All three fixtures already ran; yield the shared engine.
    return engine


@pytest.fixture(autouse=True)
def _disable_auth_and_rate_limit():
    """Provide a stable test baseline without reopening runtime defaults."""
    original = dict(os.environ)
    os.environ["APP_ENV"] = "test"
    os.environ.setdefault("ESDATA_API_KEY", "test-secret-key")
    os.environ.setdefault("MCP_API_KEY", "test-mcp-key")
    # Disable rate limiting for tests to avoid 429s across test files
    os.environ["ESDATA_RATE_LIMIT_ENABLED"] = "false"
    os.environ["ESDATA_CORS_ORIGINS"] = "*"
    yield
    # Restore only the vars we modified — never clear() the entire env
    for key in list(os.environ.keys()):
        if key in original:
            continue
        os.environ.pop(key, None)
    for key, value in original.items():
        os.environ[key] = value


@pytest_asyncio.fixture(autouse=True)
async def _seed_ley13_2023():
    """Seed LEY13_2023 data (norma, articulo, version_articulo) for all tests."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
            VALUES ('LEY13_2023', 'Ley 13/2023, de 22 de noviembre, de regulacion de la inteligencia artificial', 'BOE-A-2023-23080', 'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-23080', 'es', 'boe', 'ley', 'ia_regulacion', 'activo', '2023-11-23')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
            SELECT id, '5', 'Principio general — Aplicacion de IA', 'articulo' FROM norma WHERE codigo = 'LEY13_2023'
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT a.id, 'Articulo 5. Los desarrolladores y despliegadores de sistemas de IA de alto riesgo tendran la obligacion de garantizar la trazabilidad de los procesos de desarrollo y monitoreo continuo durante la operacion.', '2023-11-23', NULL, 'ley13-5'
            FROM articulo a JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = 'LEY13_2023' AND a.numero = '5'
              AND NOT EXISTS (SELECT 1 FROM version_articulo WHERE articulo_id = a.id AND boe_bloque_id = 'ley13-5')
        """))
    yield


@pytest_asyncio.fixture(autouse=True)
async def _seed_mica():
    """Create MiCA/crypto tables and seed test data for all tests."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS casp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                registration_number TEXT NOT NULL UNIQUE,
                home_member_state TEXT NOT NULL,
                passport_active BOOLEAN NOT NULL DEFAULT 0,
                services_offered TEXT DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS crypto_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                reference_uid TEXT NOT NULL,
                issuer_jurisdiction TEXT,
                is_sha BOOLEAN NOT NULL DEFAULT 0,
                market_value_eur REAL,
                holders_count INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tokenized_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                underlying_type TEXT NOT NULL,
                issuer_id INTEGER,
                face_value REAL,
                total_amount REAL,
                listing_date DATE,
                regulated_market TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wallet_custodian (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                wallet_type TEXT NOT NULL,
                custody_mechanism TEXT,
                insurance_coverage REAL,
                audit_frequency TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS crypto_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_wallet TEXT NOT NULL,
                receiver_wallet TEXT NOT NULL,
                sender_jurisdiction TEXT,
                receiver_jurisdiction TEXT,
                asset_type TEXT NOT NULL,
                amount REAL NOT NULL,
                value_eur REAL,
                timestamp TIMESTAMP NOT NULL,
                reporting_period TEXT,
                status TEXT NOT NULL DEFAULT 'reported',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Seed CASP data
        conn.execute(text("""
            INSERT OR IGNORE INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
            VALUES ('Bit2Me S.L.', 'ES-CASP-2024-001', 'ES', 0, '["exchange", "payment"]', 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
            VALUES ('Coinbase Europe Ltd. (sucursal Espana)', 'ES-CASP-2024-002', 'IE', 1, '["exchange", "custody", "execution"]', 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO casp (name, registration_number, home_member_state, passport_active, services_offered, status)
            VALUES ('Kraken Europe Ltd. (sucursal Espana)', 'ES-CASP-2024-004', 'MT', 1, '["exchange", "execution", "payment"]', 'active')
        """))

        # Seed crypto assets
        conn.execute(text("""
            INSERT OR IGNORE INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
            VALUES ('utility', 'UNI-Ethereum', 'US', 0, 8500000000.00, 520000, 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
            VALUES ('asset-referenced', 'USDC-Ethereum', 'US', 1, 42000000000.00, 2100000, 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction, is_sha, market_value_eur, holders_count, status)
            VALUES ('e-money', 'EURC-Ethereum', 'IE', 1, 180000000.00, 45000, 'active')
        """))

        # Seed tokenized assets
        conn.execute(text("""
            INSERT OR IGNORE INTO tokenized_asset (underlying_type, issuer_id, face_value, total_amount, listing_date, regulated_market, status)
            VALUES ('bond', NULL, 1000.00, 50000000.00, '2025-06-15', 'BME', 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO tokenized_asset (underlying_type, issuer_id, face_value, total_amount, listing_date, regulated_market, status)
            VALUES ('equity', NULL, 10.00, 10000000.00, '2025-09-01', 'Euronext Madrid', 'active')
        """))

        # Seed wallet custodians
        conn.execute(text("""
            INSERT OR IGNORE INTO wallet_custodian (entity_id, wallet_type, custody_mechanism, insurance_coverage, audit_frequency, status)
            VALUES (NULL, 'cold', 'multi-sig', 250000000.00, 'quarterly', 'active')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO wallet_custodian (entity_id, wallet_type, custody_mechanism, insurance_coverage, audit_frequency, status)
            VALUES (NULL, 'hybrid', 'MPC', 150000000.00, 'monthly', 'active')
        """))

        # Seed crypto transactions
        conn.execute(text("""
            INSERT OR IGNORE INTO crypto_transaction (sender_wallet, receiver_wallet, sender_jurisdiction, receiver_jurisdiction, asset_type, amount, value_eur, timestamp, reporting_period, status)
            VALUES ('0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a00', '0x9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f00', 'ES', 'DE', 'utility', 1500.00, 12750.00, '2025-10-15 14:30:00+00', '2025-10', 'reported')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO crypto_transaction (sender_wallet, receiver_wallet, sender_jurisdiction, receiver_jurisdiction, asset_type, amount, value_eur, timestamp, reporting_period, status)
            VALUES ('0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b11', '0x8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e22', 'FR', 'ES', 'asset-referenced', 50000.00, 50000.00, '2025-11-02 09:15:00+00', '2025-11', 'reported')
        """))
    yield
