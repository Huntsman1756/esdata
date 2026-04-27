"""XAI middleware for AI Act compliance (Fase 26.5).

Intercepts hybrid search responses and appends XAI explanations
when enabled.
"""

import logging
import time

from fastapi import Request, Response
from services.xai import XAIConfig, explain_batch_results

logger = logging.getLogger(__name__)

# AI search endpoints that get XAI explanations
XAI_ENDPOINTS = {
    "/v1/legislacion/buscar/hybrid",
    "/v1/doctrina/buscar/hybrid",
}


async def xai_middleware(request: Request, call_next) -> Response:
    """Middleware that appends XAI explanations to search results.

    Only processes hybrid search responses. Skips if XAI is disabled
    or if response is not JSON with a 'resultados' field.
    """
    path = request.url.path
    start_time = time.time()

    # Only check search endpoints
    if path not in XAI_ENDPOINTS:
        response = await call_next(request)
        return response

    response = await call_next(request)

    # Only process JSON responses
    if "application/json" not in response.headers.get("content-type", ""):
        return response

    import json

    try:
        body = json.loads(response.body)
    except Exception:
        return response

    # Only process responses with resultados field
    if not isinstance(body, dict) or "resultados" not in body:
        return response

    config = XAIConfig()
    if not config.enabled:
        return response

    results = body.get("resultados", [])
    query = body.get("q", "")
    hybrid_weight = body.get("weights", {}).get("vector", 0.3)

    if not results or not query:
        return response

    try:
        explanations = explain_batch_results(results, query, hybrid_weight)
        body["xai_explanations"] = [e.model_dump() for e in explanations]
        body["xai_enabled"] = True
    except Exception as e:
        logger.warning("XAI explanation failed: %s", e)
        body["xai_enabled"] = False
        body["xai_error"] = str(e)

    response_body = json.dumps(body).encode("utf-8")
    response.headers["content-length"] = str(len(response_body))

    return response
