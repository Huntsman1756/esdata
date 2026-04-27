"""AI risk management framework for AI Act compliance (Fase 24.1).

Implements risk identification, assessment, mitigation tracking, and
incident logging aligned with ISO 31000 and EU AI Act high-risk system
requirements.

Model-agnostic: applies to embeddings, LLMs, rerankers, or any ML component.
"""

import logging
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskCategory(str, Enum):
    BIAS_RETRIEVAL = "bias_retrieval"
    HALLUCINATION = "hallucination"
    DATA_LEAKAGE = "data_leakage"
    PROMPT_INJECTION = "prompt_injection"
    MODEL_DEGRADATION = "model_degradation"
    STALE_DATA = "stale_data"
    GEOGRAPHIC_BIAS = "geographic_bias"
    PROVIDER_DEPENDENCY = "provider_dependency"


class RiskStatus(str, Enum):
    ACTIVE = "active"
    MITIGATED = "mitigated"
    MONITORING = "monitoring"
    CLOSED = "closed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RiskAssessment(BaseModel):
    """Result of an automated risk assessment."""

    risk_id: str = Field(description="Unique risk identifier")
    category: str = Field(description="Risk category")
    severity: str = Field(description="Severity level")
    probability: float = Field(ge=0, le=1, description="Probability (0-1)")
    impact: float = Field(ge=0, le=1, description="Impact (0-1)")
    risk_score: float = Field(ge=0, le=1, description="Computed risk score")
    mitigation: str = Field(description="Recommended mitigation measure")
    context: str = Field(description="Assessment context")


class RiskRegisterItem(BaseModel):
    """A single item in the risk register."""

    risk_id: str = Field(description="Unique risk identifier")
    category: str = Field(description="Risk category")
    description: str = Field(description="Risk description")
    severity: str = Field(description="Severity level")
    status: str = Field(default="active", description="Risk status")
    probability: float = Field(ge=0, le=1, description="Probability (0-1)")
    impact: float = Field(ge=0, le=1, description="Impact (0-1)")
    risk_score: float = Field(ge=0, le=1, description="Computed risk score")
    mitigation: str = Field(description="Mitigation measure")
    responsible: str = Field(default="", description="Responsible party")
    review_frequency: str = Field(default="trimestral", description="Review frequency")
    created_at: str = Field(description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(description="Last update timestamp (ISO 8601)")


class RiskEvent(BaseModel):
    """A logged risk incident/event."""

    event_id: str = Field(description="Unique event identifier")
    risk_id: str = Field(description="Associated risk ID")
    severity: str = Field(description="Event severity")
    description: str = Field(description="Event description")
    detected_at: str = Field(description="Detection timestamp (ISO 8601)")
    resolved: bool = Field(default=False, description="Whether resolved")
    resolution_notes: str = Field(default="", description="Resolution notes if any")


# ---------------------------------------------------------------------------
# Seed data: 8 predefined risks
# ---------------------------------------------------------------------------

_SEED_RISKS = [
    {
        "risk_id": "RISK-001",
        "category": RiskCategory.BIAS_RETRIEVAL.value,
        "description": "Sesgo en retrieval: los resultados priorizan fuentes de Madrid/Barcelona sobre otras regiones",
        "severity": RiskSeverity.HIGH.value,
        "probability": 0.6,
        "impact": 0.7,
        "mitigation": "Evaluar cobertura geografica periodicamente con fairness_eval",
        "responsible": "equipo datos",
        "review_frequency": "trimestral",
    },
    {
        "risk_id": "RISK-002",
        "category": RiskCategory.HALLUCINATION.value,
        "description": "Hallucinacion en respuestas: el modelo genera informacion no respaldada por fuentes",
        "severity": RiskSeverity.CRITICAL.value,
        "probability": 0.3,
        "impact": 0.9,
        "mitigation": "Requerir evidencia/anclaje en cada respuesta; disclaimer IA obligatorio",
        "responsible": "equipo AI",
        "review_frequency": "mensual",
    },
    {
        "risk_id": "RISK-003",
        "category": RiskCategory.DATA_LEAKAGE.value,
        "description": "Data leakage: datos sensibles o PII filtrados en respuestas o logs",
        "severity": RiskSeverity.CRITICAL.value,
        "probability": 0.2,
        "impact": 0.95,
        "mitigation": "Sanitizacion de input/output; no loggear datos personales; RLS en DB",
        "responsible": "seguridad",
        "review_frequency": "mensual",
    },
    {
        "risk_id": "RISK-004",
        "category": RiskCategory.PROMPT_INJECTION.value,
        "description": "Prompt injection: inputs maliciosos que manipulan el comportamiento del modelo",
        "severity": RiskSeverity.HIGH.value,
        "probability": 0.4,
        "impact": 0.8,
        "mitigation": "Middleware de sanitizacion; deteccion de patrones inyectores; rechazar en duda",
        "responsible": "seguridad",
        "review_frequency": "mensual",
    },
    {
        "risk_id": "RISK-005",
        "category": RiskCategory.MODEL_DEGRADATION.value,
        "description": "Modelo obsoleto: degradation de calidad del embedding/search con el tiempo",
        "severity": RiskSeverity.MEDIUM.value,
        "probability": 0.5,
        "impact": 0.5,
        "mitigation": "Model registry con versioning; reevaluar calidad periodicamente; alertas de drift",
        "responsible": "equipo AI",
        "review_frequency": "trimestral",
    },
    {
        "risk_id": "RISK-006",
        "category": RiskCategory.STALE_DATA.value,
        "description": "Datos desactualizados: normativa vigente no reflejada en chunks indexados",
        "severity": RiskSeverity.HIGH.value,
        "probability": 0.5,
        "impact": 0.7,
        "mitigation": "Workers de ingestion con deteccion de cambios; flag de vigencia en resultados",
        "responsible": "equipo datos",
        "review_frequency": "mensual",
    },
    {
        "risk_id": "RISK-007",
        "category": RiskCategory.GEOGRAPHIC_BIAS.value,
        "description": "Sesgo geografico: resultados concentrados en una region (Madrid/Barcelona)",
        "severity": RiskSeverity.MEDIUM.value,
        "probability": 0.5,
        "impact": 0.5,
        "mitigation": "Evaluar distribucion geografica de fuentes; diversificar ingestion por comunidad",
        "responsible": "equipo datos",
        "review_frequency": "trimestral",
    },
    {
        "risk_id": "RISK-008",
        "category": RiskCategory.PROVIDER_DEPENDENCY.value,
        "description": "Dependencia de proveedor: bloqueo o cambio de precios del proveedor de embeddings",
        "severity": RiskSeverity.MEDIUM.value,
        "probability": 0.3,
        "impact": 0.6,
        "mitigation": "Soporte para multiples proveedores; modelo embedding local como fallback",
        "responsible": "arquitectura",
        "review_frequency": "semestral",
    },
]


def _compute_risk_score(probability: float, impact: float) -> float:
    """Compute risk score as weighted average of probability and impact."""
    return round((probability * 0.4 + impact * 0.6), 4)


def _seed_risk_register() -> list[RiskRegisterItem]:
    """Build the seed risk register."""
    now = datetime.now(UTC).isoformat()
    items = []
    for r in _SEED_RISKS:
        items.append(
            RiskRegisterItem(
                risk_id=r["risk_id"],
                category=r["category"],
                description=r["description"],
                severity=r["severity"],
                probability=r["probability"],
                impact=r["impact"],
                risk_score=_compute_risk_score(r["probability"], r["impact"]),
                mitigation=r["mitigation"],
                responsible=r["responsible"],
                review_frequency=r["review_frequency"],
                created_at=now,
                updated_at=now,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RiskFramework:
    """In-memory risk register and assessment engine.

    In production this would be backed by tables:
    - `ai_risk_register`
    - `ai_risk_events`
    """

    def __init__(self):
        self._register: list[RiskRegisterItem] = _seed_risk_register()
        self._events: list[RiskEvent] = []

    def assess_risk(self, category: str, context: str = "") -> RiskAssessment:
        """Automatically assess risk for a given category and context.

        Looks up the registered risk and computes a score based on
        its stored probability and impact, adjusted by context.

        Args:
            category: Risk category identifier.
            context: Additional context for the assessment.

        Returns:
            RiskAssessment with computed score and mitigation.
        """
        # Find matching registered risk
        matching = [r for r in self._register if r.category == category]
        if matching:
            risk = matching[0]
            return RiskAssessment(
                risk_id=risk.risk_id,
                category=risk.category,
                severity=risk.severity,
                probability=risk.probability,
                impact=risk.impact,
                risk_score=risk.risk_score,
                mitigation=risk.mitigation,
                context=context if context else risk.description,
            )

        # Unknown category: default medium risk
        return RiskAssessment(
            risk_id=f"UNKNOWN-{category}",
            category=category,
            severity=RiskSeverity.MEDIUM.value,
            probability=0.5,
            impact=0.5,
            risk_score=0.5,
            mitigation="Requiere evaluacion manual",
            context=context or f"Categoria desconocida: {category}",
        )

    def get_risk_register(self, status: str | None = None) -> list[RiskRegisterItem]:
        """Get the full risk register, optionally filtered by status.

        Args:
            status: Filter by risk status (e.g. 'active', 'mitigated').

        Returns:
            List of risk register items.
        """
        if status:
            return [r for r in self._register if r.status == status]
        return list(self._register)

    def get_risk_by_id(self, risk_id: str) -> RiskRegisterItem | None:
        """Get a specific risk by ID.

        Args:
            risk_id: The risk identifier.

        Returns:
            RiskRegisterItem or None.
        """
        for r in self._register:
            if r.risk_id == risk_id:
                return r
        return None

    def update_risk_status(self, risk_id: str, status: str, responsible: str = "") -> RiskRegisterItem | None:
        """Update the status of a registered risk.

        Args:
            risk_id: The risk identifier.
            status: New status value.
            responsible: Optional responsible party update.

        Returns:
            Updated RiskRegisterItem or None if not found.
        """
        for r in self._register:
            if r.risk_id == risk_id:
                r.status = status
                r.updated_at = datetime.now(UTC).isoformat()
                if responsible:
                    r.responsible = responsible
                return r
        return None

    def log_risk_event(
        self,
        risk_id: str,
        severity: str,
        description: str,
        resolved: bool = False,
        resolution_notes: str = "",
    ) -> RiskEvent:
        """Log a risk incident/event.

        Args:
            risk_id: Associated risk ID from the register.
            severity: Event severity level.
            description: Description of the incident.
            resolved: Whether the incident is resolved.
            resolution_notes: Notes on resolution if resolved.

        Returns:
            The created RiskEvent.
        """
        event_id = f"EVT-{len(self._events) + 1:04d}"
        event = RiskEvent(
            event_id=event_id,
            risk_id=risk_id,
            severity=severity,
            description=description,
            detected_at=datetime.now(UTC).isoformat(),
            resolved=resolved,
            resolution_notes=resolution_notes,
        )
        self._events.append(event)

        # Update risk status to monitoring if active
        risk = self.get_risk_by_id(risk_id)
        if risk and risk.status == "active":
            risk.status = "monitoring"
            risk.updated_at = datetime.now(UTC).isoformat()

        logger.info("Risk event logged: %s for risk %s (severity=%s)", event_id, risk_id, severity)
        return event

    def get_risk_events(self, risk_id: str | None = None, resolved: bool | None = None) -> list[RiskEvent]:
        """Get logged risk events with optional filters.

        Args:
            risk_id: Filter by risk ID.
            resolved: Filter by resolution status.

        Returns:
            List of RiskEvent.
        """
        results = list(self._events)
        if risk_id:
            results = [e for e in results if e.risk_id == risk_id]
        if resolved is not None:
            results = [e for e in results if e.resolved == resolved]
        return results

    @property
    def event_count(self) -> int:
        """Total logged events."""
        return len(self._events)

    @property
    def register_count(self) -> int:
        """Total registered risks."""
        return len(self._register)


# Module-level singleton
_risk_framework = RiskFramework()


def get_risk_framework() -> RiskFramework:
    """Get the global risk framework singleton."""
    return _risk_framework


def reset_risk_framework() -> None:
    """Reset the risk framework (for testing only)."""
    global _risk_framework
    _risk_framework = RiskFramework()
