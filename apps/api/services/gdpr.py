"""GDPR compliance: ARCO requests and DPIA tracking (Fase 26.10).

Implements data subject rights (acceso, rectificacion, supresion,
oposicion, limitacion, portabilidad) and Data Protection Impact
Assessment for AI Act compliance.

In-memory implementation: production would use `gdpr_dpia_requests`
database table.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ARCOType(str, Enum):
    ACCESO = "acceso"
    RECTIFICACION = "rectificacion"
    SUPRESION = "supresion"
    OPOSICION = "oposicion"
    LIMITACION = "limitacion"
    PORTABILIDAD = "portabilidad"


class ARCOStatus(str, Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    RECHAZADA = "rechazada"


class GDPRRequest(BaseModel):
    """A GDPR data subject request (ARCO)."""

    request_id: str = Field(description="Unique request identifier")
    solicitante: str = Field(description="Requester email or identifier")
    tipo_solicitud: str = Field(description="ARCO type")
    datos_afectados: str = Field(description="Description of affected data")
    estado: str = Field(default="pendiente", description="Request status")
    fecha_solicitud: str = Field(description="Request timestamp (ISO 8601)")
    fecha_respuesta: str | None = Field(default=None, description="Response timestamp")
    respuesta: str = Field(default="", description="Response text")


class DPIASummary(BaseModel):
    """Summary of Data Protection Impact Assessment."""

    tratamiento_descripcion: str = Field(
        default="Procesamiento de datos personales por componentes de IA en esdata",
    )
    datos_personales: list[str] = Field(default_factory=lambda: [
        "email",
        "nombre",
        "ip_address",
        "user_agent",
    ])
    base_legal: list[str] = Field(default_factory=lambda: [
        "consentimiento",
        "interes_legitimo",
    ])
    fines: list[str] = Field(default_factory=lambda: [
        "busqueda_legislativa",
        "clasificacion_de_contenido",
        "generacion_de_resumenes",
    ])
    riesgos_identificados: list[str] = Field(default_factory=lambda: [
        "sesgo_en_clasificacion",
        "falsos_positivos_en_deteccion_de_ia",
        "retencion_de_datos_de_solicitantes",
    ])
    medidas_mitigacion: list[str] = Field(default_factory=lambda: [
        "minimizacion_de_datos",
        "pseudonimizacion",
        "cifrado_en_transito_y_reposo",
        "revision_humana_de_decisiones_automatizadas",
        "retencion_limitada_de_logs",
    ])
    requiere_consulta_aepd: bool = Field(default=False)
    ultima_actualizacion: str = Field(description="Last update timestamp")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GDPRService:
    """In-memory GDPR ARCO request and DPIA management.

    In production this would be backed by:
    - `gdpr_dpia_requests` table
    - AEPD consultation tracking
    """

    # AI Act high-risk components that may trigger DPIA
    HIGH_RISK_COMPONENTS = {
        "adversarial",
        "fairness",
        "xai",
        "human_review",
        "ai_risk",
    }

    def __init__(self):
        self._requests: dict[str, GDPRRequest] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"gdpr-{self._counter:06d}"

    def create_arco_request(
        self,
        tipo: str,
        datos_afectados: str,
        solicitante: str,
    ) -> GDPRRequest:
        """Create a new ARCO (data subject) request.

        Args:
            tipo: ARCO type (acceso, rectificacion, supresion, etc.)
            datos_afectados: Description of affected data.
            solicitante: Requester email or identifier.

        Returns:
            The created GDPRRequest.
        """
        request_id = self._next_id()
        now = datetime.now(UTC).isoformat()

        request = GDPRRequest(
            request_id=request_id,
            solicitante=solicitante,
            tipo_solicitud=tipo,
            datos_afectados=datos_afectados,
            estado=ARCOStatus.PENDIENTE,
            fecha_solicitud=now,
        )

        self._requests[request_id] = request
        logger.info("GDPR request created: %s (%s) for %s", request_id, tipo, solicitante)
        return request

    def get_request(self, request_id: str) -> GDPRRequest | None:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_all_requests(self, estado: str | None = None) -> list[GDPRRequest]:
        """Get all requests, optionally filtered by status."""
        requests = list(self._requests.values())
        if estado:
            requests = [r for r in requests if r.estado == estado]
        return sorted(requests, key=lambda r: r.fecha_solicitud)

    def fulfill_arco_request(
        self,
        request_id: str,
        estado: str = "completada",
        respuesta: str = "",
    ) -> GDPRRequest | None:
        """Fulfill an ARCO request.

        Args:
            request_id: The request to fulfill.
            estado: Final status (completada or rechazada).
            respuesta: Response text explaining the action taken.

        Returns:
            The updated GDPRRequest or None if not found.
        """
        request = self._requests.get(request_id)
        if not request:
            return None

        if estado not in (ARCOStatus.COMPLETADA, ARCOStatus.RECHAZADA):
            raise ValueError(f"Invalid estado: {estado}. Must be completada or rechazada.")

        request.estado = estado
        request.fecha_respuesta = datetime.now(UTC).isoformat()
        request.respuesta = respuesta

        logger.info(
            "GDPR request fulfilled: %s -> %s",
            request_id, estado,
        )
        return request

    def get_dpia_summary(self) -> dict[str, Any]:
        """Get the Data Protection Impact Assessment summary."""
        return DPIASummary(
            ultima_actualizacion=datetime.now(UTC).isoformat(),
        ).model_dump()

    def get_pending_requests(self) -> list[GDPRRequest]:
        """Get all pending ARCO requests."""
        return self.get_all_requests(estado=ARCOStatus.PENDIENTE)

    def get_request_count_by_type(self) -> dict[str, int]:
        """Count requests grouped by ARCO type."""
        counts: dict[str, int] = {}
        for req in self._requests.values():
            counts[req.tipo_solicitud] = counts.get(req.tipo_solicitud, 0) + 1
        return counts

    @property
    def total_requests(self) -> int:
        """Total ARCO requests."""
        return len(self._requests)


# Module-level singleton
_service = GDPRService()


def get_gdpr_service() -> GDPRService:
    """Get the global GDPR service singleton."""
    return _service


def reset_gdpr_service() -> None:
    """Reset the GDPR service (for testing only)."""
    global _service
    _service = GDPRService()
