"""Explainable AI (XAI) service for AI Act compliance (Fase 26.5).

Generates human-readable explanations for AI search results,
ranking decisions, and relevance scores.

Covers:
- RRF ranking explanation (why a result ranked where it did)
- Chunk relevance explanation (why a specific fragment matched)
- Semantic similarity explanation (why a vector match was chosen)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExplanationType(str, Enum):
    RRF_RANKING = "rrf_ranking"
    CHUNK_RELEVANCE = "chunk_relevance"
    SEMANTIC_MATCH = "semantic_match"
    FULLTEXT_MATCH = "fulltext_match"
    BOOST_APPLIED = "boost_applied"
    FILTER_APPLIED = "filter_applied"


class XAIExplanation(BaseModel):
    """A single explanation entry."""

    type: ExplanationType = Field(description="Type of explanation")
    title: str = Field(description="Human-readable title")
    description: str = Field(description="Detailed explanation")
    confidence: float = Field(
        ge=0, le=1, default=0.0,
        description="Confidence score for this explanation (0-1)",
    )
    factors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Individual factors contributing to this explanation",
    )


class XAIRankingExplanation(BaseModel):
    """Complete XAI explanation for a search result."""

    result_id: int = Field(description="Document/result ID")
    result_norma: str = Field(description="Norma code (e.g. LIVA, LIRPF)")
    result_numero: str = Field(description="Article/section number")
    explanation: str = Field(description="Human-readable summary of why this result ranked here")
    explanations: list[XAIExplanation] = Field(
        default_factory=list,
        description="Detailed explanation entries",
    )
    rrf_score: float = Field(description="Final RRF fused score")
    rrf_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of RRF contributions by source",
    )
    relevance_level: str = Field(
        description="High, Medium, or Low relevance",
    )


def _explain_rrf_sources(
    rrf_sources: list[str],
    rrf_score: float,
    hybrid_weight: float,
    ft_rank: int | None = None,
    vec_rank: int | None = None,
) -> XAIExplanation:
    """Explain why a result ranked where it did based on RRF sources.

    Args:
        rrf_sources: List of source types that contributed ("fulltext", "vector").
        rrf_score: The final fused RRF score.
        hybrid_weight: The vector weight used (0.0-1.0).
        ft_rank: 1-based rank in fulltext results (optional).
        vec_rank: 1-based rank in vector results (optional).

    Returns:
        XAIExplanation for the RRF ranking.
    """
    ft_weight = 1.0 - hybrid_weight
    factors: list[dict[str, Any]] = []
    parts: list[str] = []

    if not rrf_sources:
        return XAIExplanation(
            type=ExplanationType.RRF_RANKING,
            title="Sin fuentes de ranking",
            description="Este resultado no fue incluido en el ranking por RRF.",
            confidence=0.0,
        )

    # Fulltext contribution
    if "fulltext" in rrf_sources:
        ft_contribution = ft_weight * (1.0 / (60 + (ft_rank or 1)))
        factors.append({
            "componente": "fulltext",
            "peso": round(ft_weight, 2),
            "rango": ft_rank or 0,
            "contribucion": round(ft_contribution, 6),
        })
        if ft_rank:
            parts.append(f"Rango #{ft_rank} en busqueda texto completo")
        else:
            parts.append("Coincide en busqueda de texto completo")

    # Vector contribution
    if "vector" in rrf_sources:
        vec_contribution = hybrid_weight * (1.0 / (60 + (vec_rank or 1)))
        factors.append({
            "componente": "vector",
            "peso": round(hybrid_weight, 2),
            "rango": vec_rank or 0,
            "contribucion": round(vec_contribution, 6),
        })
        if vec_rank:
            parts.append(f"rango #{vec_rank} en busqueda semantica")
        else:
            parts.append("Coincide en busqueda semantica")

    # Combined
    if len(rrf_sources) == 2:
        parts.append(f"Combinacion de ambas fuentes => score {rrf_score:.4f}")

    title_parts = " y ".join(parts)
    description = f"Score RRF: {rrf_score:.4f}. {title_parts}."

    confidence = min(rrf_score * 3, 1.0)

    return XAIExplanation(
        type=ExplanationType.RRF_RANKING,
        title="Explicacion de ranking RRF",
        description=description,
        confidence=round(confidence, 2),
        factors=factors,
    )


def _explain_chunk_relevance(
    fragmento: str | None,
    query: str,
    rank: float | None = None,
) -> XAIExplanation:
    """Explain why a specific chunk/fragment matched the query.

    Args:
        fragmento: The text fragment that was returned.
        query: The original search query.
        rank: The raw relevance rank score (ts_rank or similarity).

    Returns:
        XAIExplanation for the chunk relevance.
    """
    factors: list[dict[str, Any]] = []
    parts: list[str] = []

    if not fragmento:
        return XAIExplanation(
            type=ExplanationType.CHUNK_RELEVANCE,
            title="Sin fragmento disponible",
            description="No hay un fragmento de texto disponible para explicar la relevancia.",
            confidence=0.0,
        )

    # Check for keyword overlap
    query_words = set(query.lower().split())
    fragment_words = set(fragmento.lower().split())
    overlap = query_words & fragment_words
    overlap_ratio = len(overlap) / max(len(query_words), 1)

    if overlap_ratio > 0.3:
        factors.append({
            "tipo": "superposicion_palabras",
            "coincidencias": list(overlap)[:5],
            "ratio": round(overlap_ratio, 2),
        })
        parts.append(f"{len(overlap)} palabras clave del query coinciden en el fragmento")
    elif overlap_ratio > 0:
        factors.append({
            "tipo": "superposicion_parcial",
            "coincidencias": list(overlap),
            "ratio": round(overlap_ratio, 2),
        })
        parts.append("Algunas palabras clave del query aparecen en el fragmento")
    else:
        parts.append("El fragmento se selecciono por relevancia semantica (sin coincidencia literal)")

    if rank is not None:
        factors.append({"tipo": "score_raw", "valor": round(rank, 6)})
        if rank > 0.1:
            parts.append(f"Score de relevancia alto: {rank:.4f}")
        elif rank > 0.01:
            parts.append(f"Score de relevancia medio: {rank:.4f}")
        else:
            parts.append(f"Score de relevancia bajo: {rank:.4f}")

    description = "; ".join(parts) if parts else "Fragmento seleccionado como relevante."

    confidence = min(overlap_ratio + (0.3 if rank and rank > 0.01 else 0.0), 1.0)

    return XAIExplanation(
        type=ExplanationType.CHUNK_RELEVANCE,
        title="Relevancia del fragmento",
        description=description,
        confidence=round(confidence, 2),
        factors=factors,
    )


def _explain_semantic_match(
    query: str,
    fragmento: str | None,
    similarity: float | None = None,
) -> XAIExplanation:
    """Explain why a result was matched semantically (vector similarity).

    Args:
        query: The original search query.
        fragmento: The text fragment that was matched.
        similarity: The cosine similarity score (0-1).

    Returns:
        XAIExplanation for the semantic match.
    """
    factors: list[dict[str, Any]] = []
    parts: list[str] = []

    if similarity is not None:
        factors.append({"tipo": "similitud_cosina", "valor": round(similarity, 4)})

        if similarity > 0.7:
            parts.append(f"Alta similitud semantica: {similarity:.2%}")
            parts.append("El significado del fragmento es muy similar al query")
        elif similarity > 0.4:
            parts.append(f"Similitud semantica moderada: {similarity:.2%}")
            parts.append("El fragmento comparte significado con el query")
        else:
            parts.append(f"Similitud semantica baja: {similarity:.2%}")
            parts.append("El fragmento tiene alguna relacion semantica debil")

    if fragmento and query:
        query_words = set(query.lower().split())
        fragment_words = set(fragmento.lower().split())
        shared = query_words & fragment_words
        if shared:
            factors.append({
                "tipo": "superposicion_lexica",
                "palabras_comunes": list(shared)[:5],
            })
            parts.append(f"Comparten palabras: {', '.join(list(shared)[:3])}")

    description = "; ".join(parts) if parts else "Coincidencia semantica detectada por modelo de embeddings."

    confidence = similarity if similarity else 0.5

    return XAIExplanation(
        type=ExplanationType.SEMANTIC_MATCH,
        title="Coincidencia semantica",
        description=description,
        confidence=round(min(confidence, 1.0), 2),
        factors=factors,
    )


def _explain_fulltext_match(
    query: str,
    fragmento: str | None,
    rank: float | None = None,
    boosted: bool = False,
) -> XAIExplanation:
    """Explain why a result matched via fulltext search.

    Args:
        query: The original search query.
        fragmento: The text fragment.
        rank: The ts_rank score.
        boosted: Whether a boost was applied (e.g., for recency or authority).

    Returns:
        XAIExplanation for the fulltext match.
    """
    factors: list[dict[str, Any]] = []
    parts: list[str] = []

    if rank is not None:
        factors.append({"tipo": "ts_rank", "valor": round(rank, 6)})
        if rank > 0.1:
            parts.append(f"Alta puntuacion de texto completo: {rank:.4f}")
        elif rank > 0.01:
            parts.append(f"Puntuacion de texto completo moderada: {rank:.4f}")
        else:
            parts.append(f"Baja puntuacion de texto completo: {rank:.4f}")

    if boosted:
        factors.append({"tipo": "boost_aplicado", "motivo": "relevancia_extra"})
        parts.append("Se aplico un boost de relevancia a este resultado")

    if fragmento and query:
        query_terms = query.lower().split()
        matched_terms = [t for t in query_terms if t in fragmento.lower()]
        if matched_terms:
            factors.append({
                "tipo": "terminos_coincidentes",
                "terminos": matched_terms[:5],
            })
            parts.append(f"Coincide con: {', '.join(matched_terms[:3])}")

    description = "; ".join(parts) if parts else "Resultado encontrado por busqueda de texto completo."

    confidence = min(rank * 10 if rank else 0.0, 1.0)

    return XAIExplanation(
        type=ExplanationType.FULLTEXT_MATCH,
        title="Coincidencia de texto completo",
        description=description,
        confidence=round(confidence, 2),
        factors=factors,
    )


def explain_search_result(
    result: dict[str, Any],
    query: str,
    hybrid_weight: float = 0.3,
    ft_rank: int | None = None,
    vec_rank: int | None = None,
) -> XAIRankingExplanation:
    """Generate a complete XAI explanation for a single search result.

    This is the main entry point. It combines all individual explanations
    into a comprehensive ranking explanation.

    Args:
        result: A search result dict with fields like doc_id, norma, numero,
            rrf_score, rrf_sources, source, rank, fragmento, chunk_texto.
        query: The original search query string.
        hybrid_weight: The vector weight used in the search (0.0-1.0).
        ft_rank: 1-based rank in fulltext results (optional).
        vec_rank: 1-based rank in vector results (optional).

    Returns:
        XAIRankingExplanation with all explanation entries.
    """
    explanations: list[XAIExplanation] = []
    rrf_contributions: dict[str, float] = {}

    rrf_score = result.get("rrf_score", 0.0) or 0.0
    rrf_sources = result.get("rrf_sources") or []
    source = result.get("source", "")
    rank = result.get("rank")
    fragmento = result.get("fragmento")
    chunk_texto = result.get("chunk_texto")

    # RRF source explanation
    rrf_exp = _explain_rrf_sources(
        rrf_sources, rrf_score, hybrid_weight, ft_rank, vec_rank,
    )
    explanations.append(rrf_exp)

    # Track RRF contributions
    ft_weight = 1.0 - hybrid_weight
    if "fulltext" in rrf_sources and ft_weight > 0:
        ft_contrib = ft_weight * (1.0 / (60 + (ft_rank or 1)))
        rrf_contributions["fulltext"] = round(ft_contrib, 6)
    if "vector" in rrf_sources and hybrid_weight > 0:
        vec_contrib = hybrid_weight * (1.0 / (60 + (vec_rank or 1)))
        rrf_contributions["vector"] = round(vec_contrib, 6)

    # Fulltext match explanation
    if "fulltext" in rrf_sources or source == "fulltext":
        ft_exp = _explain_fulltext_match(query, fragmento or chunk_texto, rank)
        explanations.append(ft_exp)

    # Semantic match explanation
    if "vector" in rrf_sources or source == "vector":
        sim = rank if rank and source == "vector" else None
        sem_exp = _explain_semantic_match(query, fragmento or chunk_texto, sim)
        explanations.append(sem_exp)

    # Chunk relevance explanation
    chunk_exp = _explain_chunk_relevance(fragmento or chunk_texto, query, rank)
    explanations.append(chunk_exp)

    # Determine relevance level
    if rrf_score > 0.02:
        relevance_level = "Alta"
    elif rrf_score > 0.005:
        relevance_level = "Media"
    else:
        relevance_level = "Baja"

    # Build summary explanation
    summary_parts = [
        f"Resultado {result.get('norma', '')} {result.get('numero', '')}",
        f"score RRF: {rrf_score:.4f}",
    ]
    if rrf_sources:
        summary_parts.append(f"fuentes: {', '.join(rrf_sources)}")
    if rrf_contributions:
        contrib_strs = [f"{k}: {v:.4f}" for k, v in rrf_contributions.items()]
        summary_parts.append(f"contribuciones: {', '.join(contrib_strs)}")

    explanation = ". ".join(summary_parts) + "."

    # Add boost explanation if applicable
    if result.get("_boosted"):
        boost_exp = XAIExplanation(
            type=ExplanationType.BOOST_APPLIED,
            title="Boost de relevancia aplicado",
            description="Este resultado recibio un boost por relevancia adicional (recencia, autoridad, etc.).",
            confidence=0.8,
            factors=[{"tipo": "boost", "valor": result.get("_boost_value", 0.0)}],
        )
        explanations.append(boost_exp)

    return XAIRankingExplanation(
        result_id=result.get("doc_id", 0),
        result_norma=result.get("norma", ""),
        result_numero=result.get("numero", ""),
        explanation=explanation,
        explanations=explanations,
        rrf_score=round(rrf_score, 6),
        rrf_contributions=rrf_contributions,
        relevance_level=relevance_level,
    )


def explain_batch_results(
    results: list[dict[str, Any]],
    query: str,
    hybrid_weight: float = 0.3,
) -> list[XAIRankingExplanation]:
    """Generate XAI explanations for a batch of search results.

    Args:
        results: List of search result dicts.
        query: The original search query.
        hybrid_weight: The vector weight used.

    Returns:
        List of XAIRankingExplanation, one per result.
    """
    explanations = []
    for i, result in enumerate(results):
        ft_rank = result.get("_ft_rank") or (i + 1)
        vec_rank = result.get("_vec_rank")
        exp = explain_search_result(result, query, hybrid_weight, ft_rank, vec_rank)
        explanations.append(exp)
    return explanations


class XAIConfig(BaseModel):
    """Configuration for XAI explanations."""

    enabled: bool = Field(default=True, description="Whether XAI explanations are enabled")
    include_rrf_breakdown: bool = Field(default=True, description="Include RRF score breakdown")
    include_chunk_explanations: bool = Field(default=True, description="Include chunk relevance explanations")
    include_semantic_explanations: bool = Field(default=True, description="Include semantic match explanations")
    min_confidence: float = Field(default=0.0, ge=0, le=1, description="Minimum confidence threshold")
    language: str = Field(default="es", description="Explanation language code")
