"""XAI router for AI Act compliance (Fase 26.5).

Endpoints for generating and querying XAI explanations.
"""

from fastapi import APIRouter
from schemas import BaseModel, Field
from services.xai import XAIConfig, explain_search_result

router = APIRouter(prefix="/v1/ai", tags=["xai"])


class XAIExplanationItem(BaseModel):
    """Single explanation entry."""

    type: str = Field(description="Explanation type")
    title: str = Field(description="Human-readable title")
    description: str = Field(description="Detailed explanation")
    confidence: float = Field(ge=0, le=1, description="Confidence score (0-1)")
    factors: list[dict] = Field(default_factory=list, description="Contributing factors")


class XAIRankingExplanationItem(BaseModel):
    """Complete XAI explanation for a search result."""

    result_id: int = Field(description="Document/result ID")
    result_norma: str = Field(description="Norma code")
    result_numero: str = Field(description="Article/section number")
    explanation: str = Field(description="Human-readable summary")
    explanations: list[XAIExplanationItem] = Field(default_factory=list, description="Detailed entries")
    rrf_score: float = Field(description="Final RRF fused score")
    rrf_contributions: dict = Field(default_factory=dict, description="RRF contribution breakdown")
    relevance_level: str = Field(description="High, Medium, or Low relevance")


class ExplainRequest(BaseModel):
    """Request model for explaining a single result."""

    result: dict = Field(description="Search result dict")
    query: str = Field(description="Original search query")
    hybrid_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Vector weight used")
    ft_rank: int | None = Field(default=None, description="Fulltext rank")
    vec_rank: int | None = Field(default=None, description="Vector rank")


class XAIConfigResponse(BaseModel):
    """Current XAI configuration."""

    enabled: bool = Field(description="XAI enabled")
    include_rrf_breakdown: bool = Field(description="Include RRF breakdown")
    include_chunk_explanations: bool = Field(description="Include chunk explanations")
    include_semantic_explanations: bool = Field(description="Include semantic explanations")
    min_confidence: float = Field(description="Min confidence threshold")
    language: str = Field(description="Explanation language")


@router.get(
    "/xai/config",
    response_model=XAIConfigResponse,
    summary="XAI configuration",
    description="Get current XAI configuration.",
)
async def get_xai_config():
    """Get current XAI configuration."""
    config = XAIConfig()
    return config


@router.post(
    "/xai/explain",
    response_model=XAIRankingExplanationItem,
    summary="Explain search result",
    description="Generate a human-readable explanation for a search result.",
)
async def explain_result(req: ExplainRequest):
    """Explain a single search result."""
    explanation = explain_search_result(
        req.result,
        req.query,
        req.hybrid_weight,
        req.ft_rank,
        req.vec_rank,
    )
    return explanation


@router.get(
    "/xai/status",
    summary="XAI status",
    description="Check if XAI is operational.",
)
async def xai_status():
    """Check XAI operational status."""
    return {
        "xai_enabled": True,
        "version": "1.0.0",
        "capabilities": [
            "rrf_ranking_explanation",
            "chunk_relevance_explanation",
            "semantic_match_explanation",
            "fulltext_match_explanation",
        ],
    }
