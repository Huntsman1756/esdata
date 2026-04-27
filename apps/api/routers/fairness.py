"""Fairness report router for AI Act compliance (Fase 26.6).

Endpoint to evaluate search results for geographic, temporal, and source bias.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services import fairness

router = APIRouter(prefix="/v1/ai", tags=["fairness"])


class FairnessReportResponse(BaseModel):
    """Response model for a fairness evaluation report."""

    biases: list[dict] = Field(description="Per-dimension bias reports")
    overall_severity: str = Field(description="Highest severity across all dimensions")
    bias_detected: bool = Field(description="Whether any bias was detected")
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations to mitigate bias"
    )


class FairnessReportByQueryResponse(BaseModel):
    """Response model for fairness report computed over query results."""

    query: str | None = Field(default=None, description="Query used to fetch results")
    results_evaluated: int = Field(description="Number of results evaluated")
    report: FairnessReportResponse = Field(description="Fairness evaluation report")


@router.get(
    "/fairness-report",
    response_model=FairnessReportByQueryResponse,
    summary="AI fairness report",
    description=(
        "Evaluate recent search results for geographic, temporal, and source bias "
        "to support EU AI Act high-risk system fairness requirements."
    ),
)
async def get_fairness_report(
    q: str | None = Query(
        None,
        description=(
            "Optional search query to fetch results for evaluation. "
            "If omitted, evaluates the most recent results in the system."
        ),
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Number of results to evaluate (default 50, max 200)",
    ),
    enabled: bool = Query(
        True,
        description="Whether to run fairness checks (false returns empty report)",
    ),
):
    """Compute a fairness report over search results."""
    # Fetch results to evaluate
    from services.search import search_legislacion

    raw = search_legislacion(q) if q else search_legislacion("")
    results = raw["resultados"][:limit]

    # Run evaluation
    config = fairness.FairnessConfig(enabled=enabled)
    report = fairness.evaluate_fairness(results, config=config)

    return {
        "query": q,
        "results_evaluated": len(results),
        "report": FairnessReportResponse(**report),
    }
