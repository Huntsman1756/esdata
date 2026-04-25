"""Prometheus metrics endpoint for esdata API.

Exposes /metrics endpoint with HTTP request counters and histograms.
Integrates with prometheus_client library.
"""

import logging
import time

from fastapi.responses import Response

logger = logging.getLogger(__name__)


def create_metrics_middleware():
    """Create Prometheus metrics middleware for FastAPI.

    Returns a middleware function that tracks:
    - http_requests_total: Counter by method, endpoint, status
    - http_request_duration_seconds: Histogram of request durations
    """
    try:
        from prometheus_client import Counter, Histogram, generate_latest
    except ImportError:
        logger.warning("prometheus_client not installed, metrics disabled")
        return None

    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    async def metrics_middleware(request, call_next):
        start_time = time.time()
        endpoint = request.url.path

        # Normalize endpoint for grouping (replace path params with generic)
        normalized_endpoint = _normalize_path(endpoint)

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=normalized_endpoint,
            status=response.status_code,
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=normalized_endpoint,
        ).observe(duration)

        return response

    return metrics_middleware


def _normalize_path(path: str) -> str:
    """Normalize path for metrics by replacing path params.

    E.g., /v1/modelos/303 -> /v1/modelos/{codigo}
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if part.isdigit() or _is_uuid_like(part):
            normalized.append("{}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


def _is_uuid_like(s: str) -> bool:
    """Check if string looks like a UUID."""
    if len(s) != 36:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def create_metrics_endpoint():
    """Create /metrics endpoint handler.

    Returns an async function that serves Prometheus metrics in text format.
    """
    try:
        from prometheus_client import generate_latest, REGISTRY
    except ImportError:
        logger.warning("prometheus_client not installed, metrics endpoint disabled")
        return None

    async def metrics_endpoint():
        try:
            metrics_bytes = generate_latest(REGISTRY)
            return Response(
                content=metrics_bytes,
                media_type="text/plain; charset=utf-8",
            )
        except Exception as e:
            logger.error("Failed to generate metrics: %s", e, exc_info=True)
            return Response(
                content=f"# Error generating metrics: {e}\n",
                status_code=500,
                media_type="text/plain",
            )

    return metrics_endpoint
