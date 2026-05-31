from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from routers.consulta import (  # noqa: E402
    _build_cited_chunks,
    _build_claim_citations,
    _collect_verifiable_source_urls,
)


def test_consulta_cited_chunks_expose_source_url_and_hash():
    resultados = [
        {
            "tipo": "normativa",
            "norma": "LIVA",
            "articulo": "1",
            "texto": "El impuesto sobre el valor anadido grava entregas de bienes y servicios.",
            "evidencia": {
                "chunk_id": "liva-a1",
                "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1",
                "source_hash": "sha256:test",
            },
        }
    ]
    ranked_chunks = [
        SimpleNamespace(
            chunk_id="liva-a1",
            text="El impuesto sobre el valor anadido grava entregas de bienes y servicios.",
            source_document="LIVA",
            article_number="1",
            rerank_score=0.95,
        )
    ]

    chunks = _build_cited_chunks(ranked_chunks, resultados)

    assert chunks[0]["source_url"] == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1"
    assert chunks[0]["source_hash"] == "sha256:test"


def test_consulta_claim_citations_expose_verifiable_sources():
    resultados = [
        {
            "tipo": "normativa",
            "norma": "LIVA",
            "articulo": "1",
            "texto": "El impuesto sobre el valor anadido grava entregas de bienes y servicios.",
            "evidencia": {
                "chunk_id": "liva-a1",
                "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1",
                "source_hash": "sha256:test",
            },
        }
    ]

    claim_citations = _build_claim_citations(resultados, [], "IVA entregas de bienes")

    assert claim_citations[0]["citations"][0]["source_url"].startswith("https://www.boe.es/")
    assert claim_citations[0]["citations"][0]["source_hash"] == "sha256:test"


def test_source_verification_metadata_collects_urls_from_results_and_citations():
    urls = _collect_verifiable_source_urls(
        resultados=[
            {
                "tipo": "normativa",
                "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1",
            }
        ],
        cited_chunks=[
            {
                "source_url": "https://www.cnmv.es/portal/Legislacion/Circulares",
            }
        ],
        claim_citations=[
            {
                "citations": [
                    {
                        "source_url": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600",
                    }
                ]
            }
        ],
    )

    assert urls == [
        "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1",
        "https://www.cnmv.es/portal/Legislacion/Circulares",
        "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600",
    ]
