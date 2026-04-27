"""AI risk management router for AI Act compliance (Fase 24.1).

Endpoints for querying the risk register and reporting risk incidents.
"""

from fastapi import APIRouter, Query

from schemas import BaseModel, Field
from services.ai_risk import get_risk_framework


router = APIRouter(prefix="/v1/ai", tags=["ai_risk"])


class RiskRegisterResponse(BaseModel):
    """Response model for the risk register."""

    total: int = Field(description="Total registered risks")
    risks: list[dict] = Field(default_factory=list, description="Risk register items")


class RiskEventItem(BaseModel):
    """Single risk event."""

    event_id: str = Field(description="Event identifier")
    risk_id: str = Field(description="Associated risk ID")
    severity: str = Field(description="Event severity")
    description: str = Field(description="Event description")
    detected_at: str = Field(description="Detection timestamp")
    resolved: bool = Field(description="Whether resolved")
    resolution_notes: str = Field(default="", description="Resolution notes")


class RiskEventsResponse(BaseModel):
    """Response model for risk events."""

    total: int = Field(description="Total events matching filters")
    risk_id: str | None = Field(default=None, description="Risk ID filter applied")
    resolved: bool | None = Field(default=None, description="Resolved filter applied")
    events: list[RiskEventItem] = Field(default_factory=list, description="Risk events")


class RiskReportRequest(BaseModel):
    """Request model for reporting a risk incident."""

    risk_id: str = Field(description="Associated risk ID from the register")
    severity: str = Field(description="Event severity: critical, high, medium, low, info")
    description: str = Field(description="Description of the incident")
    resolved: bool = Field(default=False, description="Whether the incident is resolved")
    resolution_notes: str = Field(default="", description="Resolution notes if resolved")


@router.get(
    "/risk/register",
    response_model=RiskRegisterResponse,
    summary="AI risk register",
    description="Retrieve the AI risk register. Sensitive security details are redacted.",
)
async def get_risk_register(status: str | None = Query(None, description="Filter by status: active, mitigated, monitoring, closed")):
    """Get the AI risk register."""
    fw = get_risk_framework()
    risks = fw.get_risk_register(status=status)

    # Redact sensitive details: keep only non-sensitive fields
    risk_data = [
        {
            "risk_id": r.risk_id,
            "category": r.category,
            "description": r.description,
            "severity": r.severity,
            "status": r.status,
            "probability": r.probability,
            "impact": r.impact,
            "risk_score": r.risk_score,
            "mitigation": r.mitigation,
            "responsible": r.responsible,
            "review_frequency": r.review_frequency,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in risks
    ]

    return {"total": len(risk_data), "risks": risk_data}


@router.post(
    "/risk/report",
    summary="Report risk incident",
    description="Log a risk incident/event for tracking and remediation.",
)
async def report_risk_incident(req: RiskReportRequest):
    """Report a risk incident."""
    fw = get_risk_framework()

    # Validate risk_id exists in register
    risk = fw.get_risk_by_id(req.risk_id)
    if not risk:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Risk ID not found: {req.risk_id}")

    event = fw.log_risk_event(
        risk_id=req.risk_id,
        severity=req.severity,
        description=req.description,
        resolved=req.resolved,
        resolution_notes=req.resolution_notes,
    )

    return {
        "event_id": event.event_id,
        "risk_id": event.risk_id,
        "severity": event.severity,
        "detected_at": event.detected_at,
        "message": "Incidente registrado correctamente",
    }


@router.get(
    "/risk/events",
    response_model=RiskEventsResponse,
    summary="Risk events history",
    description="Retrieve logged risk events with optional filters.",
)
async def get_risk_events(
    risk_id: str | None = Query(None, description="Filter by risk ID"),
    resolved: bool | None = Query(None, description="Filter by resolution status"),
):
    """Get risk events with optional filters."""
    fw = get_risk_framework()
    events = fw.get_risk_events(risk_id=risk_id, resolved=resolved)

    return {
        "total": len(events),
        "risk_id": risk_id,
        "resolved": resolved,
        "events": [
            RiskEventItem(
                event_id=e.event_id,
                risk_id=e.risk_id,
                severity=e.severity,
                description=e.description,
                detected_at=e.detected_at,
                resolved=e.resolved,
                resolution_notes=e.resolution_notes,
            )
            for e in events
        ],
    }
