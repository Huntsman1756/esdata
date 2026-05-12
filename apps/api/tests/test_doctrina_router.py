import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def _client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class _EmptyResult:
    def mappings(self):
        return []


class _FakeDb:
    def execute(self, *_args, **_kwargs):
        return _EmptyResult()


def test_postgres_doctrina_search_falls_back_when_chunks_return_no_rows(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import routers.doctrina as doctrina

    fallback_called = {}

    def fake_fallback(db, q, tipo, desde, organismo_emisor, params, use_ts_rank):
        fallback_called["args"] = (db, q, tipo, desde, organismo_emisor, use_ts_rank)
        return {
            "q": q,
            "resultados": [
                {
                    "referencia": q,
                    "tipo_documento": "consulta_vinculante",
                    "organismo_emisor": "DGT",
                    "fecha": "2024-08-02",
                    "titulo": "Consulta DGT",
                    "nivel_enlace": 0.0,
                    "norma": None,
                    "numero": None,
                    "fragmento": "Consulta localizada por referencia exacta.",
                    "source_url": f"https://petete.tributos.hacienda.gob.es/consultas/?num_consulta={q}",
                }
            ],
        }

    monkeypatch.setattr(doctrina, "_buscar_doctrina_pg_fallback", fake_fallback)

    result = doctrina._buscar_doctrina_pg(
        _FakeDb(), "V1923-24", None, None, "DGT"
    )

    assert fallback_called["args"][1:] == (
        "V1923-24",
        None,
        None,
        "DGT",
        True,
    )
    assert result["resultados"][0]["referencia"] == "V1923-24"


def test_normalize_doctrina_results_deduplicates_and_keeps_exact_reference_only():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import routers.doctrina as doctrina

    results = [
        {"referencia": "V1923-24", "fragmento": "exact"},
        {"referencia": "V2274-22", "fragmento": "other"},
        {"referencia": "V1923-24", "fragmento": "duplicate"},
    ]

    normalized = doctrina._normalize_doctrina_results("V1923-24", results)

    assert normalized == [{"referencia": "V1923-24", "fragmento": "exact"}]


def test_normalize_doctrina_results_deduplicates_generic_queries():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import routers.doctrina as doctrina

    results = [
        {"referencia": "V2274-22", "fragmento": "first"},
        {"referencia": "V2274-22", "fragmento": "duplicate"},
        {"referencia": "V1923-24", "fragmento": "second"},
    ]

    normalized = doctrina._normalize_doctrina_results("IVA", results)

    assert normalized == [
        {"referencia": "V2274-22", "fragmento": "first"},
        {"referencia": "V1923-24", "fragmento": "second"},
    ]


@pytest.mark.asyncio
async def test_doctrina_detail_exposes_fecha_and_source_url():
    async with _client() as c:
        response = await c.get("/v1/doctrina/V0000-26")

    assert response.status_code == 200
    data = response.json()
    assert data["referencia"] == "V0000-26"
    assert data["fecha"] == "2026-01-15"
    assert data["url_fuente"] == "https://example.invalid/dgt/V0000-26"
