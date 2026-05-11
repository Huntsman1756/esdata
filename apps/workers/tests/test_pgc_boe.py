import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pgc_boe
from pgc_boe import parse_pgc_accounts, parse_pgc_marco, parse_pgc_normas


def test_parse_pgc_accounts_from_boe_text():
    text = textwrap.dedent("""
    CUARTA PARTE
    CUADRO DE CUENTAS
    Grupo 1
    Financiación básica
    10.
    CAPITAL
    100.
    Capital social
    1030.
    Socios por desembolsos no exigidos, capital social
    QUINTA PARTE
    """)

    result = parse_pgc_accounts(text)

    by_code = {item["codigo"]: item for item in result}
    assert by_code["10"]["descripcion"] == "CAPITAL"
    assert by_code["100"]["descripcion"] == "Capital social"
    assert by_code["1030"]["padre_codigo"] == "10"
    assert "BOE-A-2007-19884" in by_code["100"]["nota"]


def test_parse_pgc_marco_has_official_url():
    result = parse_pgc_marco("Real Decreto 1514/2007 PRIMERA PARTE SEGUNDA PARTE")

    assert any(item["codigo"] == "PGC_RD_1514_2007" for item in result)
    assert all(item["url_boe"].startswith("https://www.boe.es/") for item in result)


def test_parse_pgc_normas_from_second_part():
    text = textwrap.dedent("""
    SEGUNDA PARTE
    NORMAS DE REGISTRO Y VALORACIÓN
    1.ª Desarrollo del Marco Conceptual de la Contabilidad
    2.ª Inmovilizado material
    TERCERA PARTE
    """)

    result = parse_pgc_normas(text)

    assert [item["norma_ref"] for item in result] == ["NRV1", "NRV2"]
    assert "Inmovilizado material" in result[1]["descripcion"]


def test_pgc_boe_checks_database_connection_before_fetch(monkeypatch):
    calls = []

    class FakeConnection:
        pass

    class FakeTransaction:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeTransaction()

    fake_engine = FakeEngine()

    monkeypatch.setattr(pgc_boe, "ensure_database_connection", lambda engine, logger=None: calls.append(("ensure", engine)))
    monkeypatch.setattr(pgc_boe, "fetch_boe_text", lambda: calls.append("fetch") or "BOE text")
    monkeypatch.setattr(pgc_boe, "parse_pgc_marco", lambda _text: [{"codigo": "PGC"}])
    monkeypatch.setattr(pgc_boe, "parse_pgc_accounts", lambda _text: [{"codigo": str(i)} for i in range(100)])
    monkeypatch.setattr(pgc_boe, "parse_pgc_normas", lambda _text: [{"norma_ref": "NRV1"}])
    monkeypatch.setattr(pgc_boe, "default_financial_statement_rows", lambda: [{"estado": "balance"}])
    monkeypatch.setattr(pgc_boe, "upsert_marco", lambda _conn, _item: 1)
    monkeypatch.setattr(pgc_boe, "upsert_account", lambda _conn, _item: 1)
    monkeypatch.setattr(pgc_boe, "upsert_norma", lambda _conn, _item: 1)
    monkeypatch.setattr(pgc_boe, "upsert_estado", lambda _conn, _item: 1)
    monkeypatch.setattr(pgc_boe, "log_sync", lambda *_args, **_kwargs: calls.append("log_sync"))

    result = pgc_boe.run_sync(engine=fake_engine, run_once=True)

    assert calls[0] == ("ensure", fake_engine)
    assert calls[1] == "fetch"
    assert result == {"marcos": 1, "cuentas": 100, "normas": 1, "estados": 1}
