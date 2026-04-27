"""Middleware that intercepts AI responses requiring human review.

Checks AI confidence scores and flags responses that need human approval.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

try:
    from fastapi import Request, Response
except ImportError:
    Request = None  # type: ignore[misc,assignment]
    Response = None  # type: ignore[misc,assignment]

from services.human_review import (
    check_review_required,
    create_human_review,
)

logger = logging.getLogger(__name__)

AI_CONFIDENCE_HEADER = "X-AI-Confidence"
AI_DECISION_HEADER = "X-AI-Decision-Type"
REVIEW_REQUIRED_HEADER = "X-Review-Required"
REVIEW_ID_HEADER = "X-Review-ID"

AI_ENDPOINT_PATTERNS = [
    "/v1/ai/",
    "/v1/search",
]

CONFIDENCE_THRESHOLD = 0.5
AUTO_APPROVE_THRESHOLD = 0.95


def _is_ai_endpoint(path: str) -> bool:
    return any(pattern in path for pattern in AI_ENDPOINT_PATTERNS)


class HumanReviewMiddleware(BaseHTTPMiddleware):
    """Intercepts AI responses and flags those requiring human review."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        if not _is_ai_endpoint(path):
            return await call_next(request)

        response = await call_next(request)

        ai_confidence_str = response.headers.get(AI_CONFIDENCE_HEADER)
        decision_type = response.headers.get(AI_DECISION_HEADER, "general")

        if ai_confidence_str is None:
            return response

        try:
            ai_confidence = float(ai_confidence_str)
        except (ValueError, TypeError):
            return response

        check = check_review_required(
            ai_confidence,
            CONFIDENCE_THRESHOLD,
            AUTO_APPROVE_THRESHOLD,
        )

        if check["requires_review"]:
            request_id = request.headers.get("X-Request-ID", "unknown")
            try:
                review = create_human_review(
                    request_id=request_id,
                    decision_type=decision_type,
                    ai_response_id=str(request.url.path),
                    ai_confidence=ai_confidence,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                    metadata={"endpoint": path},
                )
                response.headers[REVIEW_REQUIRED_HEADER] = "true"
                response.headers[REVIEW_ID_HEADER] = review.review_id
                logger.info(
                    "AI response flagged for review: %s [%s] confidence=%.3f",
                    review.review_id,
                    decision_type,
                    ai_confidence,
                )
            except Exception as e:
                logger.warning("Failed to create review entry: %s", e)
                response.headers[REVIEW_REQUIRED_HEADER] = "true"

        return response
