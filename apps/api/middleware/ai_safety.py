"""AI safety middleware for AI Act compliance (Fase 24.7).

Intercepts requests to AI endpoints, sanitizes input, and blocks
prompt injection attempts before they reach the model.
"""

import logging
import time

from fastapi import Request, Response

from services.adversarial import detect_prompt_injection, sanitize_input

logger = logging.getLogger(__name__)

# AI endpoints that go through safety checks
AI_ENDPOINTS = {
    "/v1/semantic_search",
    "/v1/hybrid_search",
    "/v1/consulta",
    "/mcp",
}

# Minimum injection score to block (0.0 = block anything detected)
INJECTION_BLOCK_THRESHOLD = 0.5


async def ai_safety_middleware(request: Request, call_next) -> Response:
    """Middleware that sanitizes and validates AI input.

    Blocks requests with detected prompt injection attempts.
    Logs safety events for audit trail.
    """
    path = request.url.path
    start_time = time.time()

    # Only check AI endpoints
    if not any(path == ep or path.startswith(ep + "/") for ep in AI_ENDPOINTS):
        response = await call_next(request)
        return response

    method = request.method

    # Skip safety checks for OPTIONS (CORS preflight) — no body to inspect
    if method == "OPTIONS":
        response = await call_next(request)
        return response

    # Read and sanitize body for POST/PUT/PATCH
    blocked = False
    reason = None
    injection_score = 0.0
    injection_types: list[str] = []

    if method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="replace")

        # Quick injection check on raw body
        injection = detect_prompt_injection(body_text)
        injection_score = injection["score"]
        injection_types = injection["types"]

        if injection["injection"] and injection["score"] >= INJECTION_BLOCK_THRESHOLD:
            blocked = True
            reason = f"Prompt injection detected: {', '.join(injection['types'])}"
            logger.warning("AI safety block: %s %s - %s", method, path, reason)

        if not blocked:
            sanitized = sanitize_input(body_text)
            if sanitized["blocked"]:
                blocked = True
                reason = sanitized["reason"]
                logger.warning("AI safety block: %s %s - %s", method, path, reason)

    try:
        if blocked:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "request_blocked",
                    "reason": reason,
                    "injection_score": injection_score,
                    "injection_types": injection_types,
                },
            )

        response = await call_next(request)
        return response

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            "AI safety error: %s %s after %.0fms - %s",
            method, path, latency_ms, e,
        )
        raise
