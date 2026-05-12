from pathlib import Path
import importlib
import sys

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import create_engine, text

from .conftest import engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app

pytestmark = pytest.mark.usefixtures("pgc_test_db")
WORKERS_DIR = Path(__file__).resolve().parents[2] / "workers"


def _prepend_workers_dir():
    wdir = str(WORKERS_DIR)
    while wdir in sys.path:
        sys.path.remove(wdir)
    sys.path.insert(0, wdir)


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_pgc_fixture_seeds_catalog_marco(pgc_catalog):
    with engine.connect() as conn:
        marco = conn.execute(
            text("SELECT codigo, titulo, tipo, anio FROM pgc_marco")
        ).mappings().one()

    assert marco["codigo"] == pgc_catalog["marco"]["codigo"]
    assert marco["titulo"] == pgc_catalog["marco"]["titulo"]
    assert marco["tipo"] == pgc_catalog["marco"]["tipo"]
    assert marco["anio"] == pgc_catalog["marco"]["anio"]


def test_pgc_fixture_seeds_normas_and_leaves_later_phase_tables_empty(pgc_catalog):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM pgc_norma_valoracion")).scalar_one() == len(pgc_catalog["normas"])
        assert conn.execute(text("SELECT COUNT(*) FROM pgc_estado_financiero")).scalar_one() == len(pgc_catalog["estados_financieros"])
        assert conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta_fiscal_ref")).scalar_one() == len(pgc_catalog["referencias_fiscales"])
        assert conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta_modelo_aeat_ref")).scalar_one() == len(pgc_catalog["referencias_aeat"])


def test_pgc_fixture_fiscal_ref_schema_keeps_expected_unique_index():
    with engine.connect() as conn:
        indexes = conn.execute(text("PRAGMA index_list('pgc_cuenta_fiscal_ref')")).mappings().all()

        unique_index_name = None
        for index in indexes:
            if index["unique"]:
                unique_index_name = index["name"]
                break

        assert unique_index_name is not None

        columns = conn.execute(text(f"PRAGMA index_info('{unique_index_name}')")).mappings().all()
        assert [column["name"] for column in columns] == ["cuenta_id", "modelo", "casilla", "ejercicio"]


def test_pgc_worker_does_not_define_fiscal_links_constant(monkeypatch):
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("runtime", None)

    runtime = importlib.import_module("runtime")

    def _fail_if_resolved_at_import_time():
        raise AssertionError("get_database_url should not run at import time")

    monkeypatch.setattr(runtime, "get_database_url", _fail_if_resolved_at_import_time)

    pgc = importlib.import_module("pgc")

    assert not hasattr(pgc, "FISCAL_LINKS")


def test_pgc_worker_dataset_matches_shared_catalog(monkeypatch, pgc_catalog):
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("pgc_dataset", None)
    sys.modules.pop("runtime", None)

    pgc_dataset = importlib.import_module("pgc_dataset")

    assert pgc_dataset.PGC_MARCO_2021 == pgc_catalog["marco"]
    assert pgc_dataset.PGC_ACCOUNTS_2021 == pgc_catalog["accounts"]
    assert pgc_dataset.PGC_NORMAS_2021 == pgc_catalog["normas"]
    assert pgc_dataset.PGC_ESTADOS_FINANCIEROS_2021 == pgc_catalog["estados_financieros"]
    assert pgc_dataset.PGC_REFERENCIAS_FISCALES_2021 == pgc_catalog["referencias_fiscales"]


def test_pgc_worker_run_sync_returns_catalog_counters(monkeypatch, pgc_catalog):
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("pgc_dataset", None)
    sys.modules.pop("runtime", None)

    pgc = importlib.import_module("pgc")
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE pgc_marco (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL, anio INTEGER, texto TEXT, url_boe TEXT, vigente BOOLEAN NOT NULL)"))
        conn.execute(text("CREATE TABLE pgc_cuenta (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, descripcion TEXT NOT NULL, nivel INTEGER NOT NULL, padre_codigo TEXT, grupo TEXT, clase TEXT, saldo_normal TEXT, tipo_cuenta TEXT, vigente BOOLEAN NOT NULL, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_norma_valoracion (id INTEGER PRIMARY KEY AUTOINCREMENT, marco_id INTEGER, cuenta_id INTEGER, norma_ref TEXT NOT NULL, articulo TEXT, descripcion TEXT, tipo_operacion TEXT, debe_haber TEXT)"))
        conn.execute(text("CREATE TABLE pgc_estado_financiero (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, estado TEXT NOT NULL, tipo_presentacion TEXT, orden INTEGER NOT NULL, periodo TEXT NOT NULL, importe_base REAL, importe_anterior REAL, nota_pieds TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_fiscal_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo TEXT NOT NULL, casilla TEXT, ejercicio TEXT, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_modelo_aeat_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo_id INTEGER NOT NULL, campana TEXT, nota TEXT)"))

    result = pgc.run_sync(engine=engine, run_once=True)

    assert result == {
        "marcos_upserted": 1,
        "cuentas_upserted": len(pgc_catalog["accounts"]),
        "normas_upserted": len(pgc_catalog["normas"]),
        "estados_financieros_upserted": len(pgc_catalog["estados_financieros"]),
        "refs_fiscales_upserted": len(pgc_catalog["referencias_fiscales"]),
        "refs_aeat_upserted": len(pgc_catalog["referencias_aeat"]),
    }


def test_pgc_fixture_seeds_all_catalog_accounts(pgc_catalog):
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta")).scalar_one()
        assert total == len(pgc_catalog["accounts"])

        codigos = {
            row[0]
            for row in conn.execute(
                text("SELECT codigo FROM pgc_cuenta ORDER BY codigo")
            ).all()
        }
        assert codigos == {item["codigo"] for item in pgc_catalog["accounts"]}


def test_pgc_fixture_seeds_all_catalog_normas(pgc_catalog):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT nv.norma_ref, nv.articulo, c.codigo AS cuenta_codigo
                FROM pgc_norma_valoracion nv
                LEFT JOIN pgc_cuenta c ON c.id = nv.cuenta_id
                ORDER BY nv.norma_ref, nv.articulo, c.codigo
                """
            )
        ).mappings().all()

    assert rows == [
        {
            "norma_ref": item["norma_ref"],
            "articulo": item["articulo"],
            "cuenta_codigo": item["cuenta_codigo"],
        }
        for item in sorted(
            pgc_catalog["normas"],
            key=lambda item: (item["norma_ref"], item["articulo"], item["cuenta_codigo"]),
        )
    ]


def test_pgc_fixture_seeds_estados_financieros(pgc_catalog):
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM pgc_estado_financiero")).scalar_one()
        assert total == len(pgc_catalog["estados_financieros"])

        estados = conn.execute(
            text("SELECT estado, tipo_presentacion, orden FROM pgc_estado_financiero ORDER BY orden")
        ).mappings().all()

        assert len(estados) > 0
        assert any(e["estado"] == "balance" for e in estados)
        assert any(e["estado"] == "pyg" for e in estados)


@pytest.mark.asyncio
async def test_pgc_cuentas_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_cuentas_returns_catalog_marco_and_cuentas(pgc_catalog):
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas")
    data = r.json()
    assert "marco" in data
    assert "cuentas" in data
    assert data["marco"]["codigo"] == pgc_catalog["marco"]["codigo"]
    assert isinstance(data["cuentas"], list)


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?codigo=472")
    cuentas = r.json()["cuentas"]
    assert len(cuentas) == 1
    assert cuentas[0]["codigo"] == "472"


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_q():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?q=iva")
    cuentas = r.json()["cuentas"]
    assert [item["codigo"] for item in cuentas] == ["472", "477"]


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_tipo():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?tipo=grupo")
    cuentas = r.json()["cuentas"]
    assert len(cuentas) >= 1
    assert all(item["tipo_cuenta"] == "grupo" for item in cuentas)


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_nivel():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?nivel=3")
    cuentas = r.json()["cuentas"]
    assert len(cuentas) >= 1
    assert all(item["nivel"] == 3 for item in cuentas)


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_clase():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?clase=4")
    cuentas = r.json()["cuentas"]
    assert len(cuentas) >= 1
    assert all(item["clase"] == "4" for item in cuentas)


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_grupo():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?grupo=4")
    cuentas = r.json()["cuentas"]
    assert len(cuentas) >= 1
    assert all(item["grupo"] == "4" for item in cuentas)


@pytest.mark.asyncio
async def test_pgc_cuentas_filter_by_padre_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?padre_codigo=43")
    cuentas = r.json()["cuentas"]
    assert [item["codigo"] for item in cuentas] == ["430"]


@pytest.mark.asyncio
async def test_pgc_cuentas_orders_by_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas")
    codigos = [item["codigo"] for item in r.json()["cuentas"]]
    assert codigos == sorted(codigos)


@pytest.mark.asyncio
async def test_pgc_buscar_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/buscar?q=iva")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_buscar_finds_by_text():
    async with _client() as c:
        r = await c.get("/v1/pgc/buscar?q=tesoreria")
    codigos = [item["codigo"] for item in r.json()["resultados"]]
    assert "57" in codigos or "572" in codigos


@pytest.mark.asyncio
async def test_pgc_buscar_finds_by_partial_code():
    async with _client() as c:
        r = await c.get("/v1/pgc/buscar?q=43")
    codigos = [item["codigo"] for item in r.json()["resultados"]]
    assert "43" in codigos or "430" in codigos


@pytest.mark.asyncio
async def test_pgc_normas_valoracion_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/normas-valoracion")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_normas_valoracion_filter_by_norma_ref():
    async with _client() as c:
        r = await c.get("/v1/pgc/normas-valoracion?norma_ref=NRV10")
    normas = r.json()["normas"]
    assert len(normas) >= 1
    assert all(item["norma_ref"] == "NRV10" for item in normas)


@pytest.mark.asyncio
async def test_pgc_normas_valoracion_filter_by_cuenta_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/normas-valoracion?cuenta_codigo=472")
    normas = r.json()["normas"]
    assert len(normas) >= 1
    assert all(item["cuenta_codigo"] == "472" for item in normas)


@pytest.mark.asyncio
async def test_pgc_estados_financieros_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/estados-financieros")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_estados_financieros_returns_marco_and_estados(pgc_catalog):
    async with _client() as c:
        r = await c.get("/v1/pgc/estados-financieros")
    data = r.json()
    assert "marco" in data
    assert "estados" in data
    assert data["marco"]["codigo"] == pgc_catalog["marco"]["codigo"]
    assert len(data["estados"]) == len(pgc_catalog["estados_financieros"])


@pytest.mark.asyncio
async def test_pgc_estados_financieros_filter_by_estado():
    async with _client() as c:
        r = await c.get("/v1/pgc/estados-financieros?estado=pyg")
    estados = r.json()["estados"]
    assert len(estados) >= 1
    assert all(item["estado"] == "pyg" for item in estados)


@pytest.mark.asyncio
async def test_pgc_estados_financieros_filter_by_tipo_presentacion():
    async with _client() as c:
        r = await c.get("/v1/pgc/estados-financieros?tipo_presentacion=activo_corriente")
    estados = r.json()["estados"]
    assert len(estados) >= 1
    assert all(item["tipo_presentacion"] == "activo_corriente" for item in estados)


@pytest.mark.asyncio
async def test_pgc_referencias_fiscales_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-fiscales")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_referencias_fiscales_returns_marco_and_recs(pgc_catalog):
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-fiscales")
    data = r.json()
    assert "marco" in data
    assert "referencias" in data
    assert data["marco"]["codigo"] == pgc_catalog["marco"]["codigo"]
    assert len(data["referencias"]) == len(pgc_catalog["referencias_fiscales"])


@pytest.mark.asyncio
async def test_pgc_referencias_fiscales_filter_by_modelo():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-fiscales?modelo=IRPF")
    recs = r.json()["referencias"]
    assert len(recs) >= 1
    assert all(item["modelo"] == "IRPF" for item in recs)


@pytest.mark.asyncio
async def test_pgc_referencias_fiscales_filter_by_cuenta_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-fiscales?cuenta_codigo=472")
    recs = r.json()["referencias"]
    assert len(recs) >= 1
    assert all(item["cuenta_codigo"] == "472" for item in recs)


@pytest.mark.asyncio
async def test_pgc_aeat_references_status_200():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-aeat")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pgc_aeat_references_returns_marco_and_recs(pgc_catalog):
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-aeat")
    data = r.json()
    assert "marco" in data
    assert "referencias" in data
    assert data["marco"]["codigo"] == pgc_catalog["marco"]["codigo"]
    assert len(data["referencias"]) == len(pgc_catalog["referencias_aeat"])


@pytest.mark.asyncio
async def test_pgc_aeat_references_filter_by_modelo_id():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-aeat?modelo_id=303")
    recs = r.json()["referencias"]
    assert len(recs) >= 1
    assert all(item["modelo_id"] == 303 for item in recs)


@pytest.mark.asyncio
async def test_pgc_aeat_references_filter_by_cuenta_codigo():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-aeat?cuenta_codigo=472")
    recs = r.json()["referencias"]
    assert len(recs) >= 1
    assert all(item["cuenta_codigo"] == "472" for item in recs)


@pytest.mark.asyncio
async def test_pgc_cuentas_returns_etag_header():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas")
    etag = r.headers.get("etag", "")
    assert etag != ""
    assert '"' in etag or len(etag) > 0


@pytest.mark.asyncio
async def test_pgc_cuentas_etag_304_with_if_none_match():
    async with _client() as c:
        r1 = await c.get("/v1/pgc/cuentas")
        etag = r1.headers.get("etag", "")
        if '"' in etag:
            etag = etag.strip('"')
        r2 = await c.get("/v1/pgc/cuentas", headers={"If-None-Match": etag})
    assert r2.status_code == 304


@pytest.mark.asyncio
async def test_pgc_cuentas_csv_format():
    async with _client() as c:
        r = await c.get("/v1/pgc/cuentas?format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "pgc_cuentas.csv" in r.headers.get("content-disposition", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2
    assert "codigo" in lines[0]


@pytest.mark.asyncio
async def test_pgc_buscar_csv_format():
    async with _client() as c:
        r = await c.get("/v1/pgc/buscar?q=iva&format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2


@pytest.mark.asyncio
async def test_pgc_estados_financieros_csv_format():
    async with _client() as c:
        r = await c.get("/v1/pgc/estados-financieros?format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2


@pytest.mark.asyncio
async def test_pgc_aeat_references_csv_format():
    async with _client() as c:
        r = await c.get("/v1/pgc/referencias-aeat?format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2


@pytest.mark.asyncio
async def test_pgc_etag_changes_with_filter():
    async with _client() as c:
        r1 = await c.get("/v1/pgc/cuentas")
        r2 = await c.get("/v1/pgc/cuentas?codigo=472")
    etag1 = r1.headers.get("etag", "")
    etag2 = r2.headers.get("etag", "")
    if '"' in etag1:
        etag1 = etag1.strip('"')
    if '"' in etag2:
        etag2 = etag2.strip('"')
    assert etag1 != etag2


@pytest.mark.asyncio
async def test_pgc_csv_idempotent_with_etag():
    async with _client() as c:
        r1 = await c.get("/v1/pgc/cuentas?format=csv")
        etag = r1.headers.get("etag", "")
        if '"' in etag:
            etag = etag.strip('"')
        r2 = await c.get("/v1/pgc/cuentas?format=csv", headers={"If-None-Match": etag})
    assert r2.status_code == 304


@pytest.mark.asyncio
async def test_pgc_e2e_worker_upsert_to_api_cuentas():
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("pgc_dataset", None)
    sys.modules.pop("runtime", None)

    pgc = importlib.import_module("pgc")
    test_engine = create_engine("sqlite:///:memory:", future=True)

    with test_engine.begin() as conn:
        conn.execute(text("CREATE TABLE pgc_marco (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL, anio INTEGER, texto TEXT, url_boe TEXT, vigente BOOLEAN NOT NULL)"))
        conn.execute(text("CREATE TABLE pgc_cuenta (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, descripcion TEXT NOT NULL, nivel INTEGER NOT NULL, padre_codigo TEXT, grupo TEXT, clase TEXT, saldo_normal TEXT, tipo_cuenta TEXT, vigente BOOLEAN NOT NULL, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_norma_valoracion (id INTEGER PRIMARY KEY AUTOINCREMENT, marco_id INTEGER, cuenta_id INTEGER, norma_ref TEXT NOT NULL, articulo TEXT, descripcion TEXT, tipo_operacion TEXT, debe_haber TEXT)"))
        conn.execute(text("CREATE TABLE pgc_estado_financiero (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, estado TEXT NOT NULL, tipo_presentacion TEXT, orden INTEGER NOT NULL, periodo TEXT NOT NULL, importe_base REAL, importe_anterior REAL, nota_pieds TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_fiscal_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo TEXT NOT NULL, casilla TEXT, ejercicio TEXT, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_modelo_aeat_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo_id INTEGER NOT NULL, campana TEXT, nota TEXT)"))

    pgc.run_sync(engine=test_engine, run_once=True)

    with test_engine.connect() as conn:
        cuenta_count = conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta")).scalar_one()
        assert cuenta_count > 0


@pytest.mark.asyncio
async def test_pgc_e2e_worker_to_api_estados():
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("pgc_dataset", None)
    sys.modules.pop("runtime", None)

    pgc = importlib.import_module("pgc")
    test_engine = create_engine("sqlite:///:memory:", future=True)

    with test_engine.begin() as conn:
        conn.execute(text("CREATE TABLE pgc_marco (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL, anio INTEGER, texto TEXT, url_boe TEXT, vigente BOOLEAN NOT NULL)"))
        conn.execute(text("CREATE TABLE pgc_cuenta (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, descripcion TEXT NOT NULL, nivel INTEGER NOT NULL, padre_codigo TEXT, grupo TEXT, clase TEXT, saldo_normal TEXT, tipo_cuenta TEXT, vigente BOOLEAN NOT NULL, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_norma_valoracion (id INTEGER PRIMARY KEY AUTOINCREMENT, marco_id INTEGER, cuenta_id INTEGER, norma_ref TEXT NOT NULL, articulo TEXT, descripcion TEXT, tipo_operacion TEXT, debe_haber TEXT)"))
        conn.execute(text("CREATE TABLE pgc_estado_financiero (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, estado TEXT NOT NULL, tipo_presentacion TEXT, orden INTEGER NOT NULL, periodo TEXT NOT NULL, importe_base REAL, importe_anterior REAL, nota_pieds TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_fiscal_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo TEXT NOT NULL, casilla TEXT, ejercicio TEXT, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_modelo_aeat_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo_id INTEGER NOT NULL, campana TEXT, nota TEXT)"))

    pgc.run_sync(engine=test_engine, run_once=True)

    with test_engine.connect() as conn:
        estado_count = conn.execute(text("SELECT COUNT(*) FROM pgc_estado_financiero")).scalar_one()
        assert estado_count > 0
        estados = {row[0] for row in conn.execute(text("SELECT DISTINCT estado FROM pgc_estado_financiero")).all()}
        assert "balance" in estados
        assert "pyg" in estados


@pytest.mark.asyncio
async def test_pgc_e2e_worker_to_api_referencias():
    _prepend_workers_dir()
    sys.modules.pop("pgc", None)
    sys.modules.pop("pgc_dataset", None)
    sys.modules.pop("runtime", None)

    pgc = importlib.import_module("pgc")
    test_engine = create_engine("sqlite:///:memory:", future=True)

    with test_engine.begin() as conn:
        conn.execute(text("CREATE TABLE pgc_marco (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL, anio INTEGER, texto TEXT, url_boe TEXT, vigente BOOLEAN NOT NULL)"))
        conn.execute(text("CREATE TABLE pgc_cuenta (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, descripcion TEXT NOT NULL, nivel INTEGER NOT NULL, padre_codigo TEXT, grupo TEXT, clase TEXT, saldo_normal TEXT, tipo_cuenta TEXT, vigente BOOLEAN NOT NULL, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_norma_valoracion (id INTEGER PRIMARY KEY AUTOINCREMENT, marco_id INTEGER, cuenta_id INTEGER, norma_ref TEXT NOT NULL, articulo TEXT, descripcion TEXT, tipo_operacion TEXT, debe_haber TEXT)"))
        conn.execute(text("CREATE TABLE pgc_estado_financiero (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, estado TEXT NOT NULL, tipo_presentacion TEXT, orden INTEGER NOT NULL, periodo TEXT NOT NULL, importe_base REAL, importe_anterior REAL, nota_pieds TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_fiscal_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo TEXT NOT NULL, casilla TEXT, ejercicio TEXT, nota TEXT)"))
        conn.execute(text("CREATE TABLE pgc_cuenta_modelo_aeat_ref (id INTEGER PRIMARY KEY AUTOINCREMENT, cuenta_id INTEGER, modelo_id INTEGER NOT NULL, campana TEXT, nota TEXT)"))

    pgc.run_sync(engine=test_engine, run_once=True)

    with test_engine.connect() as conn:
        fiscal_count = conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta_fiscal_ref")).scalar_one()
        aeat_count = conn.execute(text("SELECT COUNT(*) FROM pgc_cuenta_modelo_aeat_ref")).scalar_one()
        assert fiscal_count > 0
        assert aeat_count > 0
