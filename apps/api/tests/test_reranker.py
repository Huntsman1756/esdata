import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_rerank_orders_by_relevance(monkeypatch):
    from services import reranker as reranker_module

    class _FakeModel:
        def predict(self, pairs, show_progress_bar=False):
            assert show_progress_bar is False
            scores = {
                "El IVA en restauracion es del 10%": 0.92,
                "La LGT regula el procedimiento sancionador": 0.11,
                "El tipo reducido del IVA aplica a alimentos": 0.81,
            }
            return [scores[text] for _, text in pairs]

    monkeypatch.setattr(reranker_module, "_load_model", lambda: _FakeModel())

    chunks = [
        {
            "chunk_id": "c1",
            "text": "El IVA en restauracion es del 10%",
            "source_document": "LIVA",
            "article_number": "91",
        },
        {
            "chunk_id": "c2",
            "text": "La LGT regula el procedimiento sancionador",
            "source_document": "LGT",
            "article_number": None,
        },
        {
            "chunk_id": "c3",
            "text": "El tipo reducido del IVA aplica a alimentos",
            "source_document": "LIVA",
            "article_number": "91",
        },
    ]

    result = reranker_module.rerank("tipo de IVA en restaurantes", chunks, top_k=2)

    assert [item.chunk_id for item in result] == ["c1", "c3"]
    assert len(result) == 2
    assert result[0].rerank_score >= result[1].rerank_score


def test_rerank_empty_input():
    from services import reranker as reranker_module

    assert reranker_module.rerank("cualquier query", [], top_k=5) == []


def test_normalize_rerank_score_uses_absolute_sigmoid():
    from services import reranker as reranker_module

    normalized = reranker_module.normalize_rerank_score(-3.5246732234954834)

    assert 0.0 < normalized < 0.1
    assert normalized == pytest.approx(0.0286, rel=1e-2)


def test_serialized_citations_normalize_scores_and_keep_source_url():
    from routers.consulta import (
        _serialize_cited_chunks_for_response,
        _serialize_claim_citations_for_response,
    )
    from services.reranker import normalize_rerank_score

    cited_chunks = [
        {
            "chunk_id": "hash-lis-69",
            "rerank_score": -3.5246732234954834,
            "excerpt": "Articulo 69. Tipo de gravamen del grupo fiscal.",
        }
    ]
    claim_citations = [
        {
            "claim": {
                "tipo": "normativa",
                "codigo": "LIS",
                "articulo": "69",
                "nombre": "Tipo de gravamen",
            },
            "citations": [
                {
                    "chunk_id": "hash-lis-69",
                    "rerank_score": 10.8,
                    "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-12328",
                }
            ],
        }
    ]

    serialized_chunks = _serialize_cited_chunks_for_response(cited_chunks)
    serialized_claims = _serialize_claim_citations_for_response(claim_citations)

    assert serialized_chunks[0]["relevance_score"] == pytest.approx(
        normalize_rerank_score(-3.5246732234954834), rel=1e-4
    )
    assert 0.0 <= serialized_claims[0]["confidence"] <= 1.0
    assert serialized_claims[0]["confidence"] == pytest.approx(
        normalize_rerank_score(10.8), rel=1e-4
    )
    assert serialized_claims[0]["source_url"] == "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-12328"


def test_grounding_abstention_keeps_official_full_article_results_when_faithfulness_is_high():
    from routers.consulta import _apply_grounding_abstention_if_needed

    resultados = [
        {
            "tipo": "normativa",
            "norma": "LGT",
            "articulo": "66",
            "texto": "Artículo 66. Plazos de prescripción.",
            "fragmento": "Artículo 66. Plazos de prescripción.",
            "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2003-23186",
            "source_hash": "hash-lgt-66",
            "chunk_id": None,
            "evidencia": {
                "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2003-23186",
                "source_hash": "hash-lgt-66",
                "fragmento_exacto": "Artículo 66. Plazos de prescripción.",
            },
        }
    ]
    confianza = {
        "faithfulness_score": 1.0,
        "review_required": False,
        "aviso": None,
    }
    cited_chunks = [
        {
            "chunk_id": "hash-lgt-66",
            "source_document": "LGT",
            "article_number": "66",
            "rerank_score": -1.3,
            "excerpt": "Artículo 66. Plazos de prescripción.",
        }
    ]

    final_results, updated_confianza, updated_cited_chunks = _apply_grounding_abstention_if_needed(
        "plazo prescripción LGT",
        resultados,
        [],
        [],
        confianza,
        cited_chunks,
    )

    assert final_results == resultados
    assert updated_confianza["aviso"] is None
    assert updated_cited_chunks == cited_chunks


def test_extract_keywords_ignores_substring_matches_inside_words():
    from routers.consulta import _extract_keywords

    keywords = _extract_keywords("normativa fiscal de Marte", "")

    assert "iva" not in keywords


def test_grounding_abstention_rejects_results_when_a_query_term_is_missing_from_all_results():
    from routers.consulta import _apply_grounding_abstention_if_needed

    resultados = [
        {
            "tipo": "normativa",
            "norma": "LIS",
            "articulo": "69",
            "texto": "Artículo 69. Tipo de gravamen del grupo fiscal.",
            "fragmento": "Artículo 69. Tipo de gravamen del grupo fiscal.",
            "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-12328",
            "source_hash": "hash-lis-69",
            "chunk_id": None,
            "evidencia": {
                "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-12328",
                "source_hash": "hash-lis-69",
                "fragmento_exacto": "Artículo 69. Tipo de gravamen del grupo fiscal.",
            },
            "_relevancia": {
                "nivel": "media",
                "score": 0.48,
                "coincidencia": "coincidencia media con terminos relevantes",
                "terminos_encontrados": ["normativa", "fiscal"],
                "terminos_faltantes": ["marte"],
            },
        }
    ]
    confianza = {
        "faithfulness_score": 1.0,
        "review_required": False,
        "aviso": None,
    }
    cited_chunks = [
        {
            "chunk_id": "hash-lis-69",
            "source_document": "LIS",
            "article_number": "69",
            "rerank_score": 10.8,
            "excerpt": "Artículo 69. Tipo de gravamen del grupo fiscal.",
        }
    ]

    final_results, updated_confianza, updated_cited_chunks = _apply_grounding_abstention_if_needed(
        "normativa fiscal de Marte",
        resultados,
        [],
        [],
        confianza,
        cited_chunks,
    )

    assert final_results == []
    assert updated_cited_chunks == []
    assert "evidencia insuficiente" in (updated_confianza.get("aviso") or "").lower()


def test_consulta_delegates_claim_level_abstention_to_grounding_service(monkeypatch):
    import routers.consulta as consulta_module

    delegated = {"called": False}

    def fake_apply_claim_level_abstention(resultados, grounding_summary, confianza, enriched_items=None):
        delegated["called"] = True
        assert grounding_summary["grounding_status"] == "partial"
        assert enriched_items == claim_citations
        return [resultados[0]], {**confianza, "aviso": "delegated"}

    resultados = [
        {"tipo": "normativa", "codigo": "LIS", "articulo": "14"},
        {"tipo": "doctrina", "codigo": "DGT", "articulo": "V0001"},
    ]
    claim_citations = [
        {"claim": {"tipo": "normativa", "codigo": "LIS", "articulo": "14"}, "grounded": True},
        {"claim": {"tipo": "doctrina", "codigo": "DGT", "articulo": "V0001"}, "grounded": False},
    ]
    grounding_summary = {
        "grounding_status": "partial",
        "ungrounded_claims": 1,
    }
    confianza = {"review_required": False, "faithfulness_score": 0.8}

    monkeypatch.setattr(
        consulta_module,
        "apply_claim_level_abstention",
        fake_apply_claim_level_abstention,
    )

    filtered, updated_confianza = consulta_module._apply_claim_level_abstention(
        resultados,
        claim_citations,
        grounding_summary,
        confianza,
    )

    assert delegated["called"] is True
    assert filtered == [resultados[0]]
    assert updated_confianza["aviso"] == "delegated"


@pytest.mark.asyncio
async def test_consulta_includes_cited_chunks():
    from httpx import ASGITransport, AsyncClient
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/consulta?q=modelo+100+irpf")

    assert response.status_code == 200
    data = response.json()
    assert "cited_chunks" in data
    assert isinstance(data["cited_chunks"], list)
    assert data["cited_chunks"]
    assert all("chunk_id" in citation for citation in data["cited_chunks"])
    assert all("content_preview" in citation for citation in data["cited_chunks"])
    assert all("relevance_score" in citation for citation in data["cited_chunks"])


@pytest.mark.asyncio
async def test_consulta_out_of_scope_abstains_even_if_model_suggestions_exist():
    from httpx import ASGITransport, AsyncClient
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/consulta?q=normativa+fiscal+de+Marte")

    assert response.status_code == 200
    data = response.json()
    assert data["resultados"] == []
    assert data["cited_chunks"] == []
    assert data["confianza"]["review_required"] is True
    assert "evidencia insuficiente" in (data["confianza"].get("aviso") or "").lower()


@pytest.mark.asyncio
async def test_consulta_keeps_model_result_when_db_sessions_are_terminal(monkeypatch):
    import db as db_module
    import routers.consulta as consulta_module
    from httpx import ASGITransport, AsyncClient
    from main import app

    real_session_local = db_module.SessionLocal

    @contextmanager
    def strict_db_session():
        session = real_session_local()
        try:
            yield session
        finally:
            session.close()

    strict_session_local = db_module.sessionmaker(
        bind=db_module.engine,
        autoflush=False,
        autocommit=False,
        future=True,
        close_resets_only=False,
    )

    @contextmanager
    def strict_consulta_db_session():
        session = strict_session_local()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(db_module, "SessionLocal", strict_session_local)
    monkeypatch.setattr(db_module, "db_session", strict_db_session)
    monkeypatch.setattr(consulta_module, "db_session", strict_consulta_db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/consulta?q=modelo+100+irpf")

    assert response.status_code == 200, response.text
    data = response.json()
    assert any(item.get("tipo") == "modelo" and item.get("codigo") == "100" for item in data["resultados"])
