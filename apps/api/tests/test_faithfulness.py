import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


CHUNKS_REALES = [
    {
        "chunk_id": "m303-1",
        "text": "El modelo 303 es la autoliquidacion periodica del IVA. El periodo de liquidacion coincide con el trimestre natural.",
    },
    {
        "chunk_id": "m303-2",
        "text": "Los sujetos pasivos con volumen de operaciones superior a 6.010.121,04 euros presentan declaracion mensual.",
    },
]


def test_faithfulness_alta_con_respuesta_anclada():
    from services.faithfulness import compute_faithfulness

    respuesta_buena = (
        "El modelo 303 es la autoliquidacion del IVA [m303-1]. "
        "La liquidacion es trimestral salvo grandes empresas, que presentan mensualmente [m303-2]."
    )
    score = compute_faithfulness(respuesta_buena, CHUNKS_REALES)
    assert score > 0.70, f"Esperado >0.70, obtenido {score}"


def test_faithfulness_baja_con_respuesta_inventada():
    from services.faithfulness import compute_faithfulness

    respuesta_inventada = (
        "El modelo 303 debe presentarse antes del dia 5 de cada mes. "
        "El tipo general del IVA aplicable es del 23%. "
        "Las sociedades holding estan exentas de presentarlo."
    )
    score = compute_faithfulness(respuesta_inventada, CHUNKS_REALES)
    assert score < 0.40, f"Esperado <0.40, obtenido {score}"


def test_faithfulness_cero_con_chunks_vacios():
    from services.faithfulness import compute_faithfulness

    score = compute_faithfulness("cualquier respuesta", [])
    assert score == 0.0


def test_faithfulness_distingue_buena_de_inventada():
    from services.faithfulness import compute_faithfulness

    respuesta_buena = "El periodo es trimestral [m303-1]."
    respuesta_inventada = "El IVA en Espana es del 25% para servicios digitales."
    score_buena = compute_faithfulness(respuesta_buena, CHUNKS_REALES)
    score_inventada = compute_faithfulness(respuesta_inventada, CHUNKS_REALES)
    assert score_buena > score_inventada, (
        f"El scorer no distingue: buena={score_buena}, inventada={score_inventada}"
    )


def test_compute_confianza_keeps_faithfulness_as_advisory_signal():
    from routers.consulta import _compute_confianza

    resultados = [
        {
            "tipo": "normativa",
            "norma": "LIS",
            "articulo": "14",
            "texto": "Artículo 14 LIS sobre sujetos pasivos.",
        }
    ]

    confianza = _compute_confianza([], resultados, "sujetos pasivos LIS", [])

    assert "faithfulness_score" in confianza
    assert "faithfulness_label" in confianza
    assert confianza["review_required"] is False


def test_apply_abstention_fail_closes_low_faithfulness_without_evidence():
    from routers.consulta import _apply_abstention_if_needed

    resultados = [{"tipo": "normativa", "codigo": "LIS", "articulo": "14"}]
    confianza = {
        "faithfulness_score": 0.0,
        "faithfulness_label": "baja",
        "review_required": False,
        "aviso": None,
    }

    final_results, updated_confianza = _apply_abstention_if_needed(resultados, confianza)

    assert final_results == []
    assert updated_confianza["review_required"] is True
    assert updated_confianza["faithfulness_score"] == 0.0
    assert updated_confianza["faithfulness_label"] == "baja"
    assert updated_confianza["aviso"]
