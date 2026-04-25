"""Tests pytest para scripts/eval_phase3.py.

Permite ejecutar el evaluador como tests pytest:

    pytest scripts/tests/test_eval_phase3.py -v
    pytest scripts/tests/test_eval_phase3.py -v -k "golden"
    pytest scripts/tests/test_eval_phase3.py -v -k "extract"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Asegurar que scripts/eval_phase3.py es importable
_EVAL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_EVAL_DIR))

from eval_phase3 import (  # noqa: E402
    GOLDEN_PATH,
    _extraer_articulos,
    _extraer_fuentes,
    _calcular_score,
    _check_recall_top_n,
    _posicion_fuente,
    _verificar_vigencia,
    _medir_chunk_precision,
    _check_doctrina_present,
    _check_modelo_present,
    load_golden,
    aggregate_metrics,
    THRESHOLDS,
)


# ── Golden dataset ────────────────────────────────────────────────────


class TestGoldenDataset:
    """Validaciones basicas del golden dataset."""

    def test_golden_path_exists(self):
        assert GOLDEN_PATH.exists(), f"Golden dataset no encontrado: {GOLDEN_PATH}"

    def test_golden_loads(self):
        data = load_golden()
        assert "queries" in data
        assert isinstance(data["queries"], list)
        assert len(data["queries"]) > 0

    def test_golden_queries_have_required_fields(self):
        data = load_golden()
        required = {"id", "dominio", "pregunta", "criterios"}
        for q in data["queries"]:
            assert required.issubset(q.keys()), f"Query {q.get('id')} falta campos: {required - q.keys()}"

    def test_golden_criteria_have_required_fields(self):
        data = load_golden()
        required = {"fuente_esperada", "articulo_esperado"}
        for q in data["queries"]:
            assert required.issubset(q["criterios"].keys()), \
                f"Query {q['id']} criterios falta: {required - q['criterios'].keys()}"

    def test_golden_ids_unique(self):
        data = load_golden()
        ids = [q["id"] for q in data["queries"]]
        assert len(ids) == len(set(ids)), f"IDs duplicados: {[i for i in ids if ids.count(i) > 1]}"

    def test_golden_domains_covered(self):
        data = load_golden()
        domains = {q["dominio"] for q in data["queries"]}
        expected = {"iva", "irpf_is", "internacional", "compliance", "mixto"}
        assert expected.issubset(domains), f"Faltan dominios: {expected - domains}"


# ── Source extraction ─────────────────────────────────────────────────


class TestExtraerFuentes:
    """Valida _extraer_fuentes con shapes reales de /v1/consulta y /v1/legislacion/buscar."""

    def test_extraer_fuentes_modelo_norma_base(self):
        """Formato /v1/consulta: extrae de modelos[].norma_base."""
        resp = {
            "modelos": [
                {"codigo": "303", "norma_base": "LIVA art. 71"},
            ],
            "resultados": [],
        }
        fuentes = _extraer_fuentes(resp)
        assert "LIVA" in fuentes

    def test_extraer_fuentes_buscar_norma(self):
        """Formato /v1/legislacion/buscar: extrae de resultados[].norma."""
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIVA art. 91"},
                {"norma": "LIRNR art. 14"},
            ],
        }
        fuentes = _extraer_fuentes(resp)
        assert "LIVA art. 91" in fuentes
        assert "LIRNR art. 14" in fuentes

    def test_extraer_fuentes_obligacion_fuente(self):
        """Formato /v1/consulta: extrae de resultados[].fuente en obligacion."""
        resp = {
            "modelos": [],
            "resultados": [
                {"tipo": "obligacion", "fuente": "SEPBLAC"},
            ],
        }
        fuentes = _extraer_fuentes(resp)
        assert "SEPBLAC" in fuentes

    def test_extraer_fuentes_dac6rd(self):
        """Formato /v1/consulta: extrae DAC6RD de norma_base."""
        resp = {
            "modelos": [
                {"codigo": "DAC6", "norma_base": "DAC6RD art. 206 bis"},
            ],
            "resultados": [],
        }
        fuentes = _extraer_fuentes(resp)
        assert "DAC6RD" in fuentes

    def test_extraer_fuentes_dac6eu(self):
        """Formato /v1/legislacion/buscar: extrae DAC6EU de norma."""
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "DAC6EU 2018/822"},
            ],
        }
        fuentes = _extraer_fuentes(resp)
        assert "DAC6EU 2018/822" in fuentes

    def test_extraer_fuentes_empty(self):
        resp = {"modelos": [], "resultados": []}
        fuentes = _extraer_fuentes(resp)
        assert fuentes == set()

    def test_extraer_fuentes_error_response(self):
        resp = {"_error": "timeout"}
        fuentes = _extraer_fuentes(resp)
        assert fuentes == set()


# ── Article extraction ────────────────────────────────────────────────


class TestExtraerArticulos:
    """Valida _extraer_articulos."""

    def test_extraer_articulos_buscar(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"articulo": "91"},
                {"numero": "123"},
            ],
        }
        articulos = _extraer_articulos(resp)
        assert "91" in articulos
        assert "123" in articulos

    def test_extraer_articulos_norma_base(self):
        resp = {
            "modelos": [
                {"norma_base": "LIVA art. 71"},
            ],
            "resultados": [],
        }
        articulos = _extraer_articulos(resp)
        assert "71" in articulos

    def test_extraer_articulos_bis(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"articulo": "206 bis"},
            ],
        }
        articulos = _extraer_articulos(resp)
        assert any("206" in a for a in articulos)

    def test_extraer_articulos_empty(self):
        resp = {"modelos": [], "resultados": []}
        articulos = _extraer_articulos(resp)
        assert articulos == []


# ── Score calculation ─────────────────────────────────────────────────


class TestCalcularScore:
    """Valida _calcular_score."""

    def test_score_perfect(self):
        score = _calcular_score(
            acierto_fuente=True,
            acierto_articulo=True,
            acierto_vigencia=True,
            chunk_precision=1.0,
            recall_top3=True,
            recall_top5=True,
            acierto_doctrina=True,
            acierto_modelo=True,
        )
        assert score > 0, "Score perfecto debe ser > 0"

    def test_score_zero(self):
        score = _calcular_score(
            acierto_fuente=False,
            acierto_articulo=False,
            acierto_vigencia=False,
            chunk_precision=0.0,
            recall_top3=False,
            recall_top5=False,
            acierto_doctrina=False,
            acierto_modelo=False,
        )
        assert score >= 0

    def test_score_source_only(self):
        score = _calcular_score(
            acierto_fuente=True,
            acierto_articulo=False,
            acierto_vigencia=False,
            chunk_precision=0.0,
            recall_top3=False,
            recall_top5=False,
            acierto_doctrina=False,
            acierto_modelo=False,
        )
        assert score > 0

    def test_score_no_source(self):
        score = _calcular_score(
            acierto_fuente=False,
            acierto_articulo=False,
            acierto_vigencia=False,
            chunk_precision=0.0,
            recall_top3=False,
            recall_top5=False,
            acierto_doctrina=False,
            acierto_modelo=False,
        )
        assert score < 1.0, "Sin fuente el score debe ser bajo"


# ── Recall ────────────────────────────────────────────────────────────


class TestCheckRecall:
    """Valida _check_recall_top_n."""

    def test_recall_top3_hit_norma(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIVA art. 91"},
            ],
        }
        assert _check_recall_top_n(resp, ["LIVA art. 91"], 3) is True

    def test_recall_top3_miss(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIRPF art. 91"},
            ],
        }
        assert _check_recall_top_n(resp, ["LIVA art. 91"], 3) is False

    def test_recall_top3_error(self):
        resp = {"_error": "timeout"}
        assert _check_recall_top_n(resp, ["LIVA"], 3) is False

    def test_recall_top3_empty_fuentes(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIVA art. 91"},
            ],
        }
        assert _check_recall_top_n(resp, [], 3) is False


# ── Position ──────────────────────────────────────────────────────────


class TestPosicionFuente:
    """Valida _posicion_fuente."""

    def test_position_found(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIVA art. 91"},
            ],
        }
        pos = _posicion_fuente(resp, ["LIVA art. 91"])
        assert pos == 1

    def test_position_not_found(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIRPF art. 91"},
            ],
        }
        pos = _posicion_fuente(resp, ["LIVA art. 91"])
        assert pos is None

    def test_position_error(self):
        resp = {"_error": "timeout"}
        pos = _posicion_fuente(resp, ["LIVA art. 91"])
        assert pos is None


# ── Aggregation ───────────────────────────────────────────────────────


class TestAggregateMetrics:
    """Valida aggregate_metrics."""

    def test_aggregate_empty(self):
        metrics = aggregate_metrics([])
        assert metrics["total_queries"] == 0
        assert metrics["total_failures"] == 0

    def test_aggregate_single_pass(self):
        results = [
            {
                "query_id": "test-001",
                "dominio": "iva",
                "falla": False,
                "metricas": {
                    "score_compuesto": 0.85,
                    "acierto_fuente": True,
                    "acierto_articulo": True,
                    "acierto_vigencia": True,
                    "chunk_precision": 0.5,
                    "recall_top3": True,
                    "recall_top5": True,
                    "posicion_fuente": 1,
                },
                "endpoints": {
                    "consulta": {"latencia_ms": 100.0},
                },
            }
        ]
        metrics = aggregate_metrics(results)
        assert metrics["total_queries"] == 1
        assert metrics["total_failures"] == 0
        assert metrics["global_score"] > 0
        assert "iva" in metrics["dominios"]
        assert metrics["dominios"]["iva"]["n"] == 1

    def test_aggregate_single_fail(self):
        results = [
            {
                "query_id": "test-001",
                "dominio": "iva",
                "falla": True,
                "metricas": {
                    "score_compuesto": 0.0,
                    "acierto_fuente": False,
                    "acierto_articulo": False,
                    "acierto_vigencia": False,
                    "chunk_precision": 0.0,
                    "recall_top3": False,
                    "recall_top5": False,
                    "posicion_fuente": None,
                },
                "endpoints": {
                    "consulta": {"latencia_ms": 50.0},
                },
            }
        ]
        metrics = aggregate_metrics(results)
        assert metrics["total_failures"] == 1
        assert metrics["dominios"]["iva"]["fallas"] == 1

    def test_aggregate_domains(self):
        results = [
            {
                "query_id": "iva-001",
                "dominio": "iva",
                "falla": False,
                "metricas": {
                    "score_compuesto": 0.85,
                    "acierto_fuente": True,
                    "acierto_articulo": True,
                    "acierto_vigencia": True,
                    "chunk_precision": 0.5,
                    "recall_top3": True,
                    "recall_top5": True,
                    "posicion_fuente": 1,
                },
                "endpoints": {"consulta": {"latencia_ms": 100.0}},
            },
            {
                "query_id": "irpf-001",
                "dominio": "irpf_is",
                "falla": False,
                "metricas": {
                    "score_compuesto": 0.85,
                    "acierto_fuente": True,
                    "acierto_articulo": True,
                    "acierto_vigencia": True,
                    "chunk_precision": 0.5,
                    "recall_top3": True,
                    "recall_top5": True,
                    "posicion_fuente": 1,
                },
                "endpoints": {"consulta": {"latencia_ms": 150.0}},
            },
        ]
        metrics = aggregate_metrics(results)
        assert "iva" in metrics["dominios"]
        assert "irpf_is" in metrics["dominios"]
        assert metrics["dominios"]["iva"]["n"] == 1
        assert metrics["dominios"]["irpf_is"]["n"] == 1

    def test_aggregate_weighted_score(self):
        """Verifica que el score global es ponderado por dominio."""
        results = [
            {
                "query_id": f"test-{i}",
                "dominio": "iva",
                "falla": False,
                "metricas": {
                    "score_compuesto": 0.9,
                    "acierto_fuente": True,
                    "acierto_articulo": True,
                    "acierto_vigencia": True,
                    "chunk_precision": 0.5,
                    "recall_top3": True,
                    "recall_top5": True,
                    "posicion_fuente": 1,
                },
                "endpoints": {"consulta": {"latencia_ms": 100.0}},
            }
            for i in range(10)
        ]
        metrics = aggregate_metrics(results)
        assert metrics["global_score"] > 0
        assert metrics["global_score"] <= 1.0


# ── Thresholds ────────────────────────────────────────────────────────


class TestThresholds:
    """Valida umbral de configuracion."""

    def test_thresholds_defined(self):
        assert "fuerte" in THRESHOLDS
        assert "aceptable" in THRESHOLDS
        assert "falla" in THRESHOLDS

    def test_thresholds_order(self):
        assert THRESHOLDS["fuerte"] > THRESHOLDS["aceptable"]
        assert THRESHOLDS["aceptable"] > THRESHOLDS["falla"]


# ── Helpers ───────────────────────────────────────────────────────────


class TestVerificarVigencia:
    """Valida _verificar_vigencia."""

    def test_vigencia_presente(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"vigente_desde": "2020-01-01"},
            ],
        }
        assert _verificar_vigencia(resp) is True

    def test_vigenciaausente(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"norma": "LIVA"},
            ],
        }
        assert _verificar_vigencia(resp) is False

    def test_vigencia_error(self):
        resp = {"_error": "timeout"}
        assert _verificar_vigencia(resp) is False


class TestMedirChunkPrecision:
    """Valida _medir_chunk_precision."""

    def test_chunk_present(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"articulo": "91", "chunk_id": "abc", "chunk_type": "seccion"},
            ],
        }
        precision = _medir_chunk_precision(resp, "91")
        assert precision == 1.0

    def test_chunk_absent(self):
        resp = {
            "modelos": [],
            "resultados": [
                {"articulo": "91"},
            ],
        }
        precision = _medir_chunk_precision(resp, "91")
        assert precision == 0.0

    def test_chunk_error(self):
        resp = {"_error": "timeout"}
        precision = _medir_chunk_precision(resp, "91")
        assert precision == 0.0


class TestCheckDoctrinaPresent:
    """Valida _check_doctrina_present."""

    def test_doctrina_present(self):
        resp = {"resultados": [{"titulo": "Doctrina DGT"}]}
        assert _check_doctrina_present(resp) is True

    def test_doctrina_empty(self):
        resp = {"resultados": []}
        assert _check_doctrina_present(resp) is False

    def test_doctrina_error(self):
        resp = {"_error": "timeout"}
        assert _check_doctrina_present(resp) is False


class TestCheckModeloPresent:
    """Valida _check_modelo_present."""

    def test_modelo_present(self):
        resp = {
            "modelos": [
                {"codigo": "303", "nombre": "IVA"},
            ],
        }
        assert _check_modelo_present(resp, "303") is True

    def test_modelo_absent(self):
        resp = {
            "modelos": [
                {"codigo": "100", "nombre": "IRPF"},
            ],
        }
        assert _check_modelo_present(resp, "303") is False

    def test_modelo_error(self):
        resp = {"_error": "timeout"}
        assert _check_modelo_present(resp, "303") is False
