"""Fairness evaluation for AI Act compliance (Fase 26.6).

Evaluates search results for geographic, temporal, and source bias
to ensure AI recommendations comply with EU AI Act high-risk system
fairness requirements.

Model-agnostic: applies to embeddings, LLMs, rerankers, or any ML component.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BiasDimension(str, Enum):
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    SOURCE_TYPE = "source_type"
    LANGUAGE = "language"


class BiasSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Geographic vocabulary for bias detection
# ---------------------------------------------------------------------------

_COMMUNITY_KEYWORDS: dict[str, list[str]] = {
    "madrid": ["comunidad de madrid", "madrid", "cmf", "cm"],
    "cataluna": ["comunidad catalana", "cataluna", "catalunya", "cat", "ct"],
    "andalucia": ["andalucia", "and", "andalucia"],
    "valencia": ["comunidad valenciana", "valencia", "cv", "cv"],
    "pais Vasco": ["pais vasco", "pais vasco", "pv", "pais vasco"],
    "galicia": ["galicia", "gal", "galicia"],
    "aragon": ["aragon", "arg", "aragon"],
    "castilla-leon": ["castilla y leon", "castilla-leon", "cyl"],
    "castilla-mancha": ["castilla-la mancha", "castilla-mancha", "cm"],
    "canarias": ["canarias", "can", "canarias"],
    "extranjeria": [
        "union europea", "europa", "ue", "eu",
        "portugal", "alemania", "francia", "italia",
        "ee.uu.", "estados unidos", "uk",
    ],
}

_SOURCE_TYPES: dict[str, list[str]] = {
    "boe": ["boe", "boletin oficial", "estado", "federal"],
    " Autonomico": ["comunidad", "regional", "autonomico", "diario oficial"],
    "local": ["ayuntamiento", "diputacion", "insalud", "local", "municipal"],
    "europa": ["directiva", "reglamento ue", "eur-lex", "europa", "comision europea"],
    "jurisprudencia": ["tribunal", "sentencia", "auto", "jurisprudencia", "sts", "sala"],
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FairnessReport(BaseModel):
    """Result of a fairness evaluation."""

    dimension: str = Field(description="Bias dimension evaluated")
    bias_detected: bool = Field(description="Whether bias was detected")
    severity: str = Field(description="Bias severity level")
    distribution: dict[str, int] = Field(
        description="Distribution of results across the dimension",
    )
    dominant_category: str = Field(
        default="",
        description="Category with highest representation",
    )
    dominant_ratio: float = Field(
        ge=0, le=1, default=0.0,
        description="Ratio of dominant category to total",
    )
    recommendation: str = Field(
        default="",
        description="Recommendation to mitigate bias",
    )


class FairnessConfig(BaseModel):
    """Configuration for fairness evaluation."""

    geographic_threshold: float = Field(
        default=0.4, ge=0, le=1,
        description="Max ratio for any single community before flagging geographic bias",
    )
    temporal_window_years: int = Field(
        default=5,
        description="Years window for temporal fairness (results must not be older)",
    )
    min_source_diversity: int = Field(
        default=2,
        description="Minimum number of distinct source types in results",
    )
    enabled: bool = Field(default=True, description="Whether fairness checks are enabled")


# ---------------------------------------------------------------------------
# Detection logic
# ---------------------------------------------------------------------------


def _detect_geographic_bias(
    results: list[dict],
    threshold: float = 0.4,
) -> FairnessReport:
    """Detect geographic bias in search results.

    Checks if results are disproportionately concentrated in
    specific Spanish autonomous communities or foreign jurisdictions.

    Args:
        results: List of search result dicts with source/norm fields.
        threshold: Max allowed ratio for any single community.

    Returns:
        FairnessReport with geographic bias assessment.
    """
    community_counts: Counter = Counter()
    total = len(results)

    if total == 0:
        return FairnessReport(
            dimension=BiasDimension.GEOGRAPHIC.value,
            bias_detected=False,
            severity=BiasSeverity.LOW.value,
            distribution={},
            dominant_category="",
            dominant_ratio=0.0,
            recommendation="Sin resultados para evaluar",
        )

    for r in results:
        text = f"{r.get('norma', '')} {r.get('fuente', '')} {r.get('fragmento', '')}".lower()
        for community, keywords in _COMMUNITY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    community_counts[community] += 1
                    break

    # Find dominant community
    if community_counts:
        dominant = community_counts.most_common(1)[0]
        dominant_ratio = round(dominant[1] / total, 4)
    else:
        dominant = ("sin clasificar", total)
        dominant_ratio = 1.0

    # Bias detected if any community exceeds threshold
    bias_detected = dominant_ratio > threshold
    severity = _severity_from_ratio(dominant_ratio, threshold)

    recommendation = ""
    if bias_detected and dominant[0] != "sin clasificar":
        recommendation = (
            f"Alerta: {dominant_ratio:.0%} de resultados provienen de {dominant[0]}. "
            f"Considerar diversificar fuentes geograficas para cumplir principios de equidad AI Act."
        )
    elif not community_counts:
        recommendation = (
            "No se detectaron referencias geograficas en los resultados. "
            "Verificar cobertura territorial de los chunks indexados."
        )

    return FairnessReport(
        dimension=BiasDimension.GEOGRAPHIC.value,
        bias_detected=bias_detected,
        severity=severity,
        distribution=dict(community_counts),
        dominant_category=dominant[0],
        dominant_ratio=dominant_ratio,
        recommendation=recommendation,
    )


def _detect_temporal_bias(
    results: list[dict],
    window_years: int = 5,
) -> FairnessReport:
    """Detect temporal bias in search results.

    Checks if results are disproportionately old or recent,
    which could indicate stale data or recency bias.

    Args:
        results: List of search result dicts with year/fecha fields.
        window_years: Maximum allowed age for results.

    Returns:
        FairnessReport with temporal bias assessment.
    """
    total = len(results)

    if total == 0:
        return FairnessReport(
            dimension=BiasDimension.TEMPORAL.value,
            bias_detected=False,
            severity=BiasSeverity.LOW.value,
            distribution={},
            dominant_category="",
            dominant_ratio=0.0,
            recommendation="Sin resultados para evaluar",
        )

    # Extract years from results
    year_counts: Counter = Counter()
    old_count = 0
    current_year = datetime.now(UTC).year

    for r in results:
        year_str = r.get("ano", "") or r.get("fecha", "") or ""
        if year_str:
            try:
                year = int(str(year_str).strip()[:4])
                if 2000 <= year <= current_year:
                    year_counts[str(year)] += 1
                    if current_year - year > window_years:
                        old_count += 1
            except (ValueError, TypeError):
                pass

    if not year_counts:
        return FairnessReport(
            dimension=BiasDimension.TEMPORAL.value,
            bias_detected=False,
            severity=BiasSeverity.LOW.value,
            distribution={},
            dominant_category="",
            dominant_ratio=0.0,
            recommendation="Sin anos detectados en los resultados",
        )

    dominant = year_counts.most_common(1)[0]
    dominant_ratio = round(dominant[1] / total, 4)

    # Temporal bias: too many old results or too concentrated in one year
    old_ratio = old_count / total
    bias_detected = old_ratio > 0.3 or dominant_ratio >= 0.7

    severity = BiasSeverity.LOW.value
    if old_ratio > 0.5 or dominant_ratio > 0.8:
        severity = BiasSeverity.HIGH.value
    elif old_ratio > 0.3 or dominant_ratio > 0.7:
        severity = BiasSeverity.MEDIUM.value

    recommendation = ""
    if old_ratio > 0.3:
        recommendation = (
            f"{old_ratio:.0%} de resultados tienen mas de {window_years} anos. "
            "Considerar actualizar los chunks indexados o priorizar normativa vigente."
        )
    elif dominant_ratio >= 0.7:
        recommendation = (
            f"{dominant_ratio:.0%} de resultados concentran en el ano {dominant[0]}. "
            "Verificar si hay sesgo de recencia o datos incompletos de otros anos."
        )

    return FairnessReport(
        dimension=BiasDimension.TEMPORAL.value,
        bias_detected=bias_detected,
        severity=severity,
        distribution=dict(year_counts),
        dominant_category=dominant[0],
        dominant_ratio=dominant_ratio,
        recommendation=recommendation,
    )


def _detect_source_type_bias(
    results: list[dict],
    min_diversity: int = 2,
) -> FairnessReport:
    """Detect source type bias in search results.

    Checks if results come from too few source types
    (e.g., only BOE, only autonomous communities).

    Args:
        results: List of search result dicts with source/fuente fields.
        min_diversity: Minimum distinct source types required.

    Returns:
        FairnessReport with source type bias assessment.
    """
    total = len(results)

    if total == 0:
        return FairnessReport(
            dimension=BiasDimension.SOURCE_TYPE.value,
            bias_detected=False,
            severity=BiasSeverity.LOW.value,
            distribution={},
            dominant_category="",
            dominant_ratio=0.0,
            recommendation="Sin resultados para evaluar",
        )

    type_counts: Counter = Counter()

    for r in results:
        text = f"{r.get('norma', '')} {r.get('fuente', '')} {r.get('fragmento', '')}".lower()
        assigned = False
        for source_type, keywords in _SOURCE_TYPES.items():
            for kw in keywords:
                if kw in text:
                    type_counts[source_type] += 1
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            type_counts["otro"] += 1

    distinct_types = len(type_counts)
    dominant = type_counts.most_common(1)[0]
    dominant_ratio = round(dominant[1] / total, 4)

    bias_detected = distinct_types < min_diversity

    severity = BiasSeverity.MEDIUM.value if bias_detected else BiasSeverity.LOW.value

    recommendation = ""
    if bias_detected:
        recommendation = (
            f"Solo {distinct_types} tipo(s) de fuente detectado(s). "
            f"Se requieren al menos {min_diversity} para diversidad suficiente. "
            "Considerar ampliar cobertura de fuentes."
        )

    return FairnessReport(
        dimension=BiasDimension.SOURCE_TYPE.value,
        bias_detected=bias_detected,
        severity=severity,
        distribution=dict(type_counts),
        dominant_category=dominant[0],
        dominant_ratio=dominant_ratio,
        recommendation=recommendation,
    )


def _severity_from_ratio(ratio: float, threshold: float) -> str:
    """Compute severity based on how much the ratio exceeds the threshold."""
    if ratio <= threshold:
        return BiasSeverity.LOW.value
    excess = ratio - threshold
    if excess > 0.3:
        return BiasSeverity.CRITICAL.value
    if excess > 0.15:
        return BiasSeverity.HIGH.value
    return BiasSeverity.MEDIUM.value


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def evaluate_fairness(
    results: list[dict],
    config: FairnessConfig | None = None,
) -> dict:
    """Run full fairness evaluation on search results.

    Checks geographic, temporal, and source type dimensions.

    Args:
        results: List of search result dicts.
        config: Fairness configuration. Defaults to FairnessConfig().

    Returns:
        dict with 'biases' (list), 'overall_severity', 'bias_detected',
        and 'recommendations'.
    """
    if config is None:
        config = FairnessConfig()

    if not config.enabled:
        return {
            "biases": [],
            "overall_severity": "skipped",
            "bias_detected": False,
            "recommendations": [],
        }

    reports: list[FairnessReport] = []

    geo = _detect_geographic_bias(results, config.geographic_threshold)
    reports.append(geo)

    temporal = _detect_temporal_bias(results, config.temporal_window_years)
    reports.append(temporal)

    source = _detect_source_type_bias(results, config.min_source_diversity)
    reports.append(source)

    all_biases = [r for r in reports if r.bias_detected]
    bias_detected = len(all_biases) > 0

    # Overall severity: take the highest
    severity_order = {
        BiasSeverity.LOW.value: 0,
        BiasSeverity.MEDIUM.value: 1,
        BiasSeverity.HIGH.value: 2,
        BiasSeverity.CRITICAL.value: 3,
    }
    if all_biases:
        overall_severity = max(
            all_biases,
            key=lambda r: severity_order.get(r.severity, 0),
        ).severity
    else:
        overall_severity = BiasSeverity.LOW.value

    recommendations = [r.recommendation for r in reports if r.recommendation]

    return {
        "biases": [r.model_dump() for r in reports],
        "overall_severity": overall_severity,
        "bias_detected": bias_detected,
        "recommendations": recommendations,
    }


def evaluate_single_dimension(
    results: list[dict],
    dimension: str,
    config: FairnessConfig | None = None,
) -> FairnessReport:
    """Evaluate a single fairness dimension.

    Args:
        results: List of search result dicts.
        dimension: One of 'geographic', 'temporal', 'source_type'.
        config: Fairness configuration.

    Returns:
        FairnessReport for the specified dimension.
    """
    if config is None:
        config = FairnessConfig()

    if dimension == BiasDimension.GEOGRAPHIC.value:
        return _detect_geographic_bias(results, config.geographic_threshold)
    elif dimension == BiasDimension.TEMPORAL.value:
        return _detect_temporal_bias(results, config.temporal_window_years)
    elif dimension == BiasDimension.SOURCE_TYPE.value:
        return _detect_source_type_bias(results, config.min_source_diversity)
    else:
        return FairnessReport(
            dimension=dimension,
            bias_detected=False,
            severity=BiasSeverity.LOW.value,
            distribution={},
            dominant_category="",
            dominant_ratio=0.0,
            recommendation=f"Dimension '{dimension}' no soportada",
        )
