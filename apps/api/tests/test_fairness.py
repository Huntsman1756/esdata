"""Tests for AI fairness evaluation (Fase 26.6)."""

# ruff: noqa: E402

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from apps.api.services import fairness


class TestGeographicBias:
    def test_empty_results(self):
        report = fairness._detect_geographic_bias([], threshold=0.4)
        assert report.bias_detected is False
        assert report.severity == "low"
        assert report.distribution == {}

    def test_madrid_concentration(self):
        results = [
            {
                "norma": "Ley CMF",
                "fuente": "comunidad de madrid",
                "fragmento": "normativa de la comunidad de madrid",
            }
            for _ in range(8)
        ] + [
            {
                "norma": "Ley CAT",
                "fuente": "cataluna",
                "fragmento": "normativa de cataluna",
            }
            for _ in range(2)
        ]
        report = fairness._detect_geographic_bias(results, threshold=0.4)
        assert report.bias_detected is True
        assert report.dominant_category == "madrid"
        assert report.dominant_ratio == 0.8
        assert report.severity in ("high", "critical")
        assert "alerta" in report.recommendation.lower()

    def test_balanced_distribution(self):
        results = [
            {"norma": "Ley AND", "fuente": "andalucia", "fragmento": "andalucia"},
            {"norma": "Ley CAT", "fuente": "cataluna", "fragmento": "cataluna"},
            {"norma": "Ley GAL", "fuente": "galicia", "fragmento": "galicia"},
            {"norma": "Ley ARG", "fuente": "aragon", "fragmento": "aragon"},
        ]
        report = fairness._detect_geographic_bias(results, threshold=0.4)
        assert report.bias_detected is False
        assert report.dominant_ratio <= 0.4

    def test_no_geographic_refs(self):
        results = [
            {"norma": "Ley X", "fuente": "boe", "fragmento": "texto general sin referencia"},
            {"norma": "Ley Y", "fuente": "boe", "fragmento": "otra disposicion general"},
        ]
        report = fairness._detect_geographic_bias(results)
        assert report.dominant_category == "sin clasificar"
        assert report.recommendation

    def test_severity_critical(self):
        results = [
            {"norma": "Ley", "fuente": "comunidad de madrid", "fragmento": "madrid"}
            for _ in range(10)
        ]
        report = fairness._detect_geographic_bias(results, threshold=0.4)
        assert report.severity == "critical"

    def test_severity_high(self):
        results = [
            {"norma": "Ley", "fuente": "comunidad de madrid", "fragmento": "madrid"}
            for _ in range(7)
        ] + [
            {"norma": "Ley", "fuente": "cataluna", "fragmento": "cataluna"}
            for _ in range(3)
        ]
        report = fairness._detect_geographic_bias(results, threshold=0.4)
        assert report.severity == "high"

    def test_severity_medium(self):
        results = [
            {"norma": "Ley", "fuente": "comunidad de madrid", "fragmento": "madrid"}
            for _ in range(5)
        ] + [
            {"norma": "Ley", "fuente": "cataluna", "fragmento": "cataluna"}
            for _ in range(5)
        ]
        report = fairness._detect_geographic_bias(results, threshold=0.4)
        assert report.bias_detected is True
        assert report.severity == "medium"


class TestTemporalBias:
    def setup_method(self):
        pass

    def test_empty_results(self):
        report = fairness._detect_temporal_bias([], window_years=5)
        assert report.bias_detected is False

    def test_old_results_bias(self):
        results = [
            {"ano": "2010", "norma": "Ley", "fragmento": "test"},
            {"ano": "2011", "norma": "Ley", "fragmento": "test"},
            {"ano": "2012", "norma": "Ley", "fragmento": "test"},
            {"ano": "2020", "norma": "Ley", "fragmento": "test"},
            {"ano": "2021", "norma": "Ley", "fragmento": "test"},
        ]
        report = fairness._detect_temporal_bias(results, window_years=5)
        assert report.bias_detected is True
        assert "anos" in report.recommendation.lower()

    def test_year_concentration(self):
        results = [
            {"ano": "2023", "norma": "Ley", "fragmento": "test"}
            for _ in range(7)
        ] + [
            {"ano": "2021", "norma": "Ley", "fragmento": "test"}
            for _ in range(3)
        ]
        report = fairness._detect_temporal_bias(results, window_years=5)
        assert report.bias_detected is True
        assert report.dominant_category == "2023"
        assert report.dominant_ratio == 0.7

    def test_no_year_data(self):
        results = [
            {"norma": "Ley", "fragmento": "sin ano"},
            {"norma": "Ley", "fragmento": "sin fecha"},
        ]
        report = fairness._detect_temporal_bias(results)
        assert report.bias_detected is False

    def test_fresh_results_no_bias(self):
        results = [
            {"ano": "2024", "norma": "Ley", "fragmento": "test"},
            {"ano": "2025", "norma": "Ley", "fragmento": "test"},
            {"ano": "2026", "norma": "Ley", "fragmento": "test"},
        ]
        report = fairness._detect_temporal_bias(results, window_years=5)
        assert report.bias_detected is False

    def test_high_severity_majority_old(self):
        results = [
            {"ano": "2010", "norma": "Ley", "fragmento": "test"}
            for _ in range(8)
        ] + [
            {"ano": "2020", "norma": "Ley", "fragmento": "test"}
            for _ in range(2)
        ]
        report = fairness._detect_temporal_bias(results, window_years=5)
        assert report.severity == "high"


class TestSourceTypeBias:
    def setup_method(self):
        pass

    def test_empty_results(self):
        report = fairness._detect_source_type_bias([], min_diversity=2)
        assert report.bias_detected is False

    def test_single_source_type(self):
        results = [
            {"norma": "Ley", "fuente": "boletin oficial del estado", "fragmento": "test"},
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"norma": "Ley", "fuente": "boletin oficial del estado", "fragmento": "test"},
        ]
        report = fairness._detect_source_type_bias(results, min_diversity=2)
        assert report.bias_detected is True
        assert report.dominant_category == "boe"

    def test_diverse_sources(self):
        results = [
            {"norma": "Ley", "fuente": "boletin oficial del estado", "fragmento": "test"},
            {"norma": "Ley", "fuente": "comunidad de madrid", "fragmento": "test"},
            {"norma": "Sentencia", "fuente": "tribunal", "fragmento": "test"},
        ]
        report = fairness._detect_source_type_bias(results, min_diversity=2)
        assert report.bias_detected is False

    def test_only_autonomic(self):
        results = [
            {"norma": "Ley", "fuente": "diario oficial comunidad", "fragmento": "test"},
            {"norma": "Ley", "fuente": "regional", "fragmento": "test"},
        ]
        report = fairness._detect_source_type_bias(results, min_diversity=2)
        assert report.bias_detected is True
        assert report.dominant_category == " Autonomico"

    def test_eu_sources(self):
        results = [
            {"norma": "Directiva", "fuente": "eur-lex", "fragmento": "test"},
            {"norma": "Reglamento", "fuente": "comision europea", "fragmento": "test"},
        ]
        report = fairness._detect_source_type_bias(results, min_diversity=2)
        assert report.bias_detected is True
        assert report.dominant_category == "europa"

    def test_unknown_source_classified_as_other(self):
        results = [
            {"norma": "Ley", "fuente": "blog personal", "fragmento": "test"},
        ]
        report = fairness._detect_source_type_bias(results, min_diversity=2)
        assert report.dominant_category == "otro"


class TestEvaluateFairness:
    def test_all_dimensions_checked(self):
        results = [
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"},
        ]
        report = fairness.evaluate_fairness(results)
        assert "biases" in report
        assert len(report["biases"]) == 3
        assert report["bias_detected"] is True

    def test_disabled_config(self):
        config = fairness.FairnessConfig(enabled=False)
        results = [
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"},
        ]
        report = fairness.evaluate_fairness(results, config)
        assert report["biases"] == []
        assert report["overall_severity"] == "skipped"
        assert report["bias_detected"] is False

    def test_recommendations_collected(self):
        results = [
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"}
            for _ in range(10)
        ]
        report = fairness.evaluate_fairness(results)
        assert len(report["recommendations"]) > 0

    def test_overall_severity_takes_highest(self):
        results = [
            {"ano": "2010", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2011", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2012", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2013", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2014", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2020", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2021", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2022", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2023", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
            {"ano": "2024", "norma": "Ley", "fuente": "boe", "fragmento": "test"},
        ]
        report = fairness.evaluate_fairness(results)
        assert report["overall_severity"] in ("medium", "high", "critical")

    def test_empty_results_no_bias(self):
        report = fairness.evaluate_fairness([])
        assert report["bias_detected"] is False


class TestEvaluateSingleDimension:
    def test_geographic_dimension(self):
        results = [
            {"norma": "Ley", "fuente": "comunidad de madrid", "fragmento": "madrid"}
            for _ in range(5)
        ]
        report = fairness.evaluate_single_dimension(results, "geographic")
        assert report.dimension == "geographic"
        assert report.bias_detected is True

    def test_temporal_dimension(self):
        results = [
            {"ano": "2010", "norma": "Ley", "fragmento": "test"}
            for _ in range(5)
        ]
        report = fairness.evaluate_single_dimension(results, "temporal")
        assert report.dimension == "temporal"
        assert report.bias_detected is True

    def test_source_type_dimension(self):
        results = [
            {"norma": "Ley", "fuente": "boe", "fragmento": "test"}
            for _ in range(3)
        ]
        report = fairness.evaluate_single_dimension(results, "source_type")
        assert report.dimension == "source_type"
        assert report.bias_detected is True

    def test_unsupported_dimension(self):
        report = fairness.evaluate_single_dimension([], "unsupported_xyz")
        assert report.bias_detected is False
        assert "no soportada" in report.recommendation.lower()


class TestFairnessConfig:
    def test_default_config(self):
        config = fairness.FairnessConfig()
        assert config.enabled is True
        assert config.geographic_threshold == 0.4
        assert config.temporal_window_years == 5
        assert config.min_source_diversity == 2

    def test_custom_config(self):
        config = fairness.FairnessConfig(
            geographic_threshold=0.6,
            temporal_window_years=10,
            min_source_diversity=3,
        )
        assert config.geographic_threshold == 0.6
        assert config.temporal_window_years == 10
        assert config.min_source_diversity == 3

    def test_config_to_dict(self):
        config = fairness.FairnessConfig()
        d = config.model_dump()
        assert "enabled" in d
        assert "geographic_threshold" in d
