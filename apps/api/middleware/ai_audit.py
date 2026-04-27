"""AI audit logging middleware for AI Act compliance (Fase 24.2).

Intercepts requests to AI/ML components and logs decisions
for regulatory audit trail. Append-only, no sensitive data.
"""

import logging
import time

from fastapi import Request, Response

from services.ai_audit import get_audit_store
from services.ai_disclaimer import is_ai_component

logger = logging.getLogger(__name__)

# Components that trigger audit logging
AI_COMPONENTS = {
    "/v1/semantic_search": "semantic_search",
    "/v1/hybrid_search": "hybrid_search",
    "/v1/consulta": "consulta",
    "/mcp": "mcp",
}

# Actions mapped to HTTP methods + paths
_ACTIONS = {
    ("GET", "/v1/semantic_search"): "query",
    ("GET", "/v1/hybrid_search"): "query",
    ("GET", "/v1/consulta"): "query",
    ("POST", "/mcp"): "query",
}


async def ai_audit_middleware(request: Request, call_next) -> Response:
    """Middleware that logs AI component decisions.

    Appends to audit log on every request to AI endpoints.
    Does NOT log prompts, personal data, or full request bodies.
    """
    start_time = time.time()

    # Check if this is an AI component request
    path = request.url.path
    is_ai = is_ai_component(path=path)

    if not is_ai:
        response = await call_next(request)
        return response

    # Determine component and action
    componente = "unknown"
    accion = "unknown"
    for prefix, comp in AI_COMPONENTS.items():
        if prefix in path:
            componente = comp
            break

    method = request.method
    key = (method, path)
    if key in _ACTIONS:
        accion = _ACTIONS[key]
    elif method == "GET":
        accion = "query"
    elif method == "POST":
        accion = "execute"

    # Extract safe metadata
    request_id = request.headers.get("x-request-id", "")
    user_id = request.headers.get("x-user-id", None)
    ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else None)

    try:
        response = await call_next(request)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Build result summary (no sensitive data)
        status = response.status_code
        resultado = f"status={status}"

        # Log the decision
        store = get_audit_store()
        store.log_ai_decision(
            componente=componente,
            accion=accion,
            request_id=request_id,
            configuracion={"method": method, "path": path},
            resultado_resumen=resultado,
            latencia_ms=round(latency_ms, 2),
            user_id=user_id,
            ip_address=ip_address,
        )

        return response

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_msg = str(e)[:200]  # Truncate to avoid oversized logs

        store = get_audit_store()
        store.log_ai_decision(
            componente=componente,
            accion=accion,
            request_id=request_id,
            configuracion={"method": method, "path": path},
            resultado_resumen="error",
            latencia_ms=round(latency_ms, 2),
            error=error_msg,
            user_id=user_id,
            ip_address=ip_address,
        )
        raise
