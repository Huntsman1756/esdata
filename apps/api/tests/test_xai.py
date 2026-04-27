"""Tests for XAI service (Fase 26.5)."""

from unittest import TestCase

from services.xai import (
    ExplanationType,
    XAIConfig,
    XAIExplanation,
    XAIRankingExplanation,
    _explain_chunk_relevance,
    _explain_fulltext_match,
    _explain_rrf_sources,
    _explain_semantic_match,
    explain_batch_results,
    explain_search_result,
)


class TestExplainRRFSources(TestCase):
    """Tests for RRF source explanation."""

    def test_single_fulltext_source(self):
        exp = _explain_rrf_sources(
            rrf_sources=["fulltext"],
            rrf_score=0.008,
            hybrid_weight=0.3,
            ft_rank=3,
        )
        self.assertEqual(exp.type, ExplanationType.RRF_RANKING)
        self.assertIn("texto completo", exp.description)
        self.assertIn("3", exp.description)
        self.assertEqual(len(exp.factors), 1)
        self.assertEqual(exp.factors[0]["componente"], "fulltext")

    def test_single_vector_source(self):
        exp = _explain_rrf_sources(
            rrf_sources=["vector"],
            rrf_score=0.005,
            hybrid_weight=0.3,
            vec_rank=5,
        )
        self.assertEqual(exp.type, ExplanationType.RRF_RANKING)
        self.assertIn("semantica", exp.description)
        self.assertIn("5", exp.description)

    def test_hybrid_both_sources(self):
        exp = _explain_rrf_sources(
            rrf_sources=["fulltext", "vector"],
            rrf_score=0.015,
            hybrid_weight=0.3,
            ft_rank=2,
            vec_rank=3,
        )
        self.assertEqual(exp.type, ExplanationType.RRF_RANKING)
        self.assertIn("texto completo", exp.description)
        self.assertIn("semantica", exp.description)
        self.assertEqual(len(exp.factors), 2)

    def test_no_sources(self):
        exp = _explain_rrf_sources(
            rrf_sources=[],
            rrf_score=0.0,
            hybrid_weight=0.3,
        )
        self.assertEqual(exp.type, ExplanationType.RRF_RANKING)
        self.assertIn("Sin fuentes", exp.title)
        self.assertEqual(exp.confidence, 0.0)

    def test_no_ranks_provided(self):
        exp = _explain_rrf_sources(
            rrf_sources=["fulltext"],
            rrf_score=0.005,
            hybrid_weight=0.3,
        )
        self.assertEqual(exp.type, ExplanationType.RRF_RANKING)
        self.assertIn("Coincide en busqueda", exp.description)

    def test_confidence_scales_with_score(self):
        exp_low = _explain_rrf_sources(["fulltext"], 0.001, 0.3, ft_rank=10)
        exp_high = _explain_rrf_sources(["fulltext"], 0.05, 0.3, ft_rank=1)
        self.assertLess(exp_low.confidence, exp_high.confidence)


class TestExplainChunkRelevance(TestCase):
    """Tests for chunk relevance explanation."""

    def test_normal_text_overlap(self):
        exp = _explain_chunk_relevance(
            fragmento="El IVA se aplica al 21%",
            query="cuanto es el tipo de iva",
        )
        self.assertEqual(exp.type, ExplanationType.CHUNK_RELEVANCE)
        self.assertIn("coinciden", exp.description)
        self.assertGreater(len(exp.factors), 0)

    def test_no_overlap_semantic(self):
        exp = _explain_chunk_relevance(
            fragmento="La normativa fiscal establece",
            query="comparacion entre españa y portugal",
        )
        self.assertEqual(exp.type, ExplanationType.CHUNK_RELEVANCE)
        self.assertIn("sin coincidencia literal", exp.description)

    def test_with_rank_score(self):
        exp = _explain_chunk_relevance(
            fragmento="El IRPF",
            query="irpf",
            rank=0.05,
        )
        self.assertIn("0.05", exp.description)
        self.assertIn("medio", exp.description)

    def test_high_rank_score(self):
        exp = _explain_chunk_relevance(
            fragmento="El IRPF",
            query="irpf",
            rank=0.2,
        )
        self.assertIn("alto", exp.description)

    def test_empty_fragment(self):
        exp = _explain_chunk_relevance(
            fragmento=None,
            query="test",
        )
        self.assertEqual(exp.type, ExplanationType.CHUNK_RELEVANCE)
        self.assertIn("Sin fragmento", exp.title)

    def test_factors_include_overlap(self):
        exp = _explain_chunk_relevance(
            fragmento="base imponible del iva",
            query="base imponible iva",
        )
        factor_types = [f["tipo"] for f in exp.factors]
        self.assertIn("superposicion_palabras", factor_types)


class TestExplainSemanticMatch(TestCase):
    """Tests for semantic match explanation."""

    def test_high_similarity(self):
        exp = _explain_semantic_match(
            query="tipo impositivo iva",
            fragmento="el iva se aplica al veintiuno por ciento",
            similarity=0.85,
        )
        self.assertEqual(exp.type, ExplanationType.SEMANTIC_MATCH)
        self.assertIn("Alta similitud", exp.description)
        self.assertEqual(exp.confidence, 0.85)

    def test_medium_similarity(self):
        exp = _explain_semantic_match(
            query="irpf",
            fragmento="impuesto sobre la renta",
            similarity=0.5,
        )
        self.assertEqual(exp.type, ExplanationType.SEMANTIC_MATCH)
        self.assertIn("moderada", exp.description)

    def test_low_similarity(self):
        exp = _explain_semantic_match(
            query="tributacion internacional",
            fragmento="normas contables",
            similarity=0.2,
        )
        self.assertEqual(exp.type, ExplanationType.SEMANTIC_MATCH)
        self.assertIn("baja", exp.description)

    def test_no_similarity_provided(self):
        exp = _explain_semantic_match(
            query="test",
            fragmento="fragmento de prueba",
        )
        self.assertEqual(exp.type, ExplanationType.SEMANTIC_MATCH)
        self.assertEqual(exp.confidence, 0.5)

    def test_with_lexical_overlap(self):
        exp = _explain_semantic_match(
            query="iva 21 por ciento",
            fragmento="el tipo de iva es 21",
            similarity=0.6,
        )
        factor_types = [f["tipo"] for f in exp.factors]
        self.assertIn("superposicion_lexica", factor_types)


class TestExplainFulltextMatch(TestCase):
    """Tests for fulltext match explanation."""

    def test_high_ts_rank(self):
        exp = _explain_fulltext_match(
            query="iva recargo equivalencia",
            fragmento="el recargo de equivalencia aplica al iva",
            rank=0.15,
        )
        self.assertEqual(exp.type, ExplanationType.FULLTEXT_MATCH)
        self.assertIn("Alta", exp.description)
        self.assertIn("0.15", exp.description)

    def test_medium_ts_rank(self):
        exp = _explain_fulltext_match(
            query="irpf",
            fragmento="irpf 2024",
            rank=0.03,
        )
        self.assertIn("moderada", exp.description)

    def test_boost_applied(self):
        exp = _explain_fulltext_match(
            query="test",
            fragmento="test fragment",
            rank=0.05,
            boosted=True,
        )
        self.assertIn("boost", exp.description)
        boost_factors = [f for f in exp.factors if f.get("tipo") == "boost_aplicado"]
        self.assertEqual(len(boost_factors), 1)
        self.assertEqual(exp.factors[1]["tipo"], "boost_aplicado")

    def test_no_boost(self):
        exp = _explain_fulltext_match(
            query="test",
            fragmento="test fragment",
            rank=0.05,
        )
        boost_factors = [f for f in exp.factors if f.get("tipo") == "boost_aplicado"]
        self.assertEqual(len(boost_factors), 0)

    def test_matched_terms(self):
        exp = _explain_fulltext_match(
            query="iva deducciones inversiones",
            fragmento="deducciones por inversiones en activos",
            rank=0.08,
        )
        term_factors = [f for f in exp.factors if f.get("tipo") == "terminos_coincidentes"]
        self.assertGreater(len(term_factors), 0)
        self.assertIn("deducciones", term_factors[0]["terminos"])


class TestExplainSearchResult(TestCase):
    """Tests for main explain_search_result function."""

    def test_hybrid_result_both_sources(self):
        result = {
            "doc_id": 101,
            "norma": "LIVA",
            "numero": "articulo 49",
            "rrf_score": 0.025,
            "rrf_sources": ["fulltext", "vector"],
            "source": "hybrid",
            "rank": 0.85,
            "fragmento": "El recargo de equivalencia se aplica al iva",
        }
        exp = explain_search_result(result, "recargo equivalencia iva", 0.3, ft_rank=2, vec_rank=3)
        self.assertIsInstance(exp, XAIRankingExplanation)
        self.assertEqual(exp.result_id, 101)
        self.assertEqual(exp.result_norma, "LIVA")
        self.assertEqual(exp.relevance_level, "Alta")
        self.assertEqual(exp.rrf_score, 0.025)
        self.assertEqual(len(exp.explanations), 4)
        self.assertIn("fulltext", exp.rrf_contributions)
        self.assertIn("vector", exp.rrf_contributions)

    def test_fulltext_only_result(self):
        result = {
            "doc_id": 102,
            "norma": "LIRPF",
            "numero": "articulo 23",
            "rrf_score": 0.008,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.05,
            "fragmento": "Las retenciones del irpf",
        }
        exp = explain_search_result(result, "retencion irpf", 0.3, ft_rank=5)
        self.assertEqual(exp.relevance_level, "Media")
        self.assertIn("fulltext", exp.rrf_contributions)
        self.assertNotIn("vector", exp.rrf_contributions)

    def test_vector_only_result(self):
        result = {
            "doc_id": 103,
            "norma": "LIS",
            "numero": "articulo 11",
            "rrf_score": 0.004,
            "rrf_sources": ["vector"],
            "source": "vector",
            "rank": 0.65,
            "fragmento": "Impuesto sobre sociedades",
        }
        exp = explain_search_result(result, "impuesto sociedades", 0.3, vec_rank=8)
        self.assertEqual(exp.relevance_level, "Baja")
        self.assertNotIn("fulltext", exp.rrf_contributions)
        self.assertIn("vector", exp.rrf_contributions)

    def test_high_relevance_level(self):
        result = {
            "doc_id": 1,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.03,
            "rrf_sources": ["fulltext", "vector"],
            "source": "hybrid",
            "rank": 0.9,
            "fragmento": "test",
        }
        exp = explain_search_result(result, "test", 0.3)
        self.assertEqual(exp.relevance_level, "Alta")

    def test_medium_relevance_level(self):
        result = {
            "doc_id": 2,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.01,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.05,
            "fragmento": "test",
        }
        exp = explain_search_result(result, "test", 0.3)
        self.assertEqual(exp.relevance_level, "Media")

    def test_low_relevance_level(self):
        result = {
            "doc_id": 3,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.001,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.001,
            "fragmento": "test",
        }
        exp = explain_search_result(result, "test", 0.3)
        self.assertEqual(exp.relevance_level, "Baja")

    def test_boosted_result(self):
        result = {
            "doc_id": 4,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.02,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.1,
            "fragmento": "test",
            "_boosted": True,
            "_boost_value": 1.5,
        }
        exp = explain_search_result(result, "test", 0.3)
        boost_exps = [e for e in exp.explanations if e.type == ExplanationType.BOOST_APPLIED]
        self.assertEqual(len(boost_exps), 1)

    def test_no_fragment(self):
        result = {
            "doc_id": 5,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.01,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.05,
        }
        exp = explain_search_result(result, "test", 0.3)
        self.assertIsInstance(exp, XAIRankingExplanation)
        self.assertEqual(len(exp.explanations), 3)

    def test_explanation_summary_contains_norma(self):
        result = {
            "doc_id": 6,
            "norma": "LIRPF",
            "numero": "art 23",
            "rrf_score": 0.01,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.05,
            "fragmento": "test",
        }
        exp = explain_search_result(result, "test", 0.3)
        self.assertIn("LIRPF", exp.explanation)
        self.assertIn("art 23", exp.explanation)

    def test_explanations_are_xai_explanation_models(self):
        result = {
            "doc_id": 7,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.01,
            "rrf_sources": ["fulltext"],
            "source": "fulltext",
            "rank": 0.05,
            "fragmento": "test",
        }
        exp = explain_search_result(result, "test", 0.3)
        for e in exp.explanations:
            self.assertIsInstance(e, XAIExplanation)
            self.assertIsInstance(e.type, ExplanationType)


class TestExplainBatchResults(TestCase):
    """Tests for batch explanation."""

    def test_batch_single_result(self):
        results = [{
            "doc_id": 1,
            "norma": "LIVA",
            "numero": "1",
            "rrf_score": 0.015,
            "rrf_sources": ["fulltext", "vector"],
            "source": "hybrid",
            "rank": 0.8,
            "fragmento": "test fragment",
        }]
        explanations = explain_batch_results(results, "test query", 0.3)
        self.assertEqual(len(explanations), 1)
        self.assertIsInstance(explanations[0], XAIRankingExplanation)

    def test_batch_multiple_results(self):
        results = [
            {
                "doc_id": i,
                "norma": "LIVA",
                "numero": str(i),
                "rrf_score": 0.01 * (10 - i),
                "rrf_sources": ["fulltext"],
                "source": "fulltext",
                "rank": 0.1 - i * 0.01,
                "fragmento": f"fragment {i}",
            }
            for i in range(1, 4)
        ]
        explanations = explain_batch_results(results, "test", 0.3)
        self.assertEqual(len(explanations), 3)
        for exp in explanations:
            self.assertIsInstance(exp, XAIRankingExplanation)

    def test_batch_empty_results(self):
        explanations = explain_batch_results([], "test", 0.3)
        self.assertEqual(len(explanations), 0)

    def test_batch_different_relevance_levels(self):
        results = [
            {
                "doc_id": 1,
                "norma": "A",
                "numero": "1",
                "rrf_score": 0.03,
                "rrf_sources": ["fulltext"],
                "source": "fulltext",
                "rank": 0.2,
                "fragmento": "test",
            },
            {
                "doc_id": 2,
                "norma": "B",
                "numero": "2",
                "rrf_score": 0.001,
                "rrf_sources": ["fulltext"],
                "source": "fulltext",
                "rank": 0.001,
                "fragmento": "test",
            },
        ]
        explanations = explain_batch_results(results, "test", 0.3)
        self.assertEqual(explanations[0].relevance_level, "Alta")
        self.assertEqual(explanations[1].relevance_level, "Baja")


class TestXAIConfig(TestCase):
    """Tests for XAI configuration model."""

    def test_default_config(self):
        config = XAIConfig()
        self.assertTrue(config.enabled)
        self.assertTrue(config.include_rrf_breakdown)
        self.assertTrue(config.include_chunk_explanations)
        self.assertTrue(config.include_semantic_explanations)
        self.assertEqual(config.min_confidence, 0.0)
        self.assertEqual(config.language, "es")

    def test_disabled_config(self):
        config = XAIConfig(enabled=False)
        self.assertFalse(config.enabled)

    def test_custom_min_confidence(self):
        config = XAIConfig(min_confidence=0.8)
        self.assertEqual(config.min_confidence, 0.8)

    def test_config_to_dict(self):
        config = XAIConfig()
        d = config.model_dump()
        self.assertIn("enabled", d)
        self.assertIn("include_rrf_breakdown", d)
        self.assertIn("language", d)
