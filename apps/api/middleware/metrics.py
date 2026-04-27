"""Prometheus metrics endpoint for esdata API."""

import logging
import time
from typing import Any

from fastapi.responses import Response

logger = logging.getLogger(__name__)


def _collector_by_name(registry: Any, name: str):
    return registry._names_to_collectors.get(name)


def create_metrics_middleware():
    """Create Prometheus metrics middleware for FastAPI.

    Returns a middleware function that tracks:
    - http_requests_total: Counter by method, endpoint, status
    - http_request_duration_seconds: Histogram of request durations
    """
    try:
        from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
    except ImportError:
        logger.warning("prometheus_client not installed, metrics disabled")
        return None

    # Idempotent registration: re-use existing collectors if already registered
    _existing = REGISTRY._names_to_collectors
    _reuse = "http_requests_total" in _existing and "http_request_duration_seconds" in _existing
    REQUEST_COUNT: Counter | None = None
    REQUEST_DURATION: Histogram | None = None
    CONSULTA_REVIEW_REQUIRED: Counter | None = None
    CONSULTA_FAITHFULNESS_SCORE: Gauge | None = None
    if _reuse:
        REQUEST_COUNT = _collector_by_name(REGISTRY, "http_requests_total")
        REQUEST_DURATION = _collector_by_name(REGISTRY, "http_request_duration_seconds")
        CONSULTA_REVIEW_REQUIRED = _collector_by_name(REGISTRY, "consulta_review_required_total")
        CONSULTA_FAITHFULNESS_SCORE = _collector_by_name(REGISTRY, "consulta_faithfulness_score")
    else:
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
        CONSULTA_REVIEW_REQUIRED = Counter(
            "consulta_review_required_total",
            "Total consulta responses grouped by review requirement",
            ["endpoint", "review_required"],
        )
        CONSULTA_FAITHFULNESS_SCORE = Gauge(
            "consulta_faithfulness_score",
            "Latest faithfulness score observed for consulta endpoint",
            ["endpoint"],
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


def record_consulta_metrics(endpoint: str, confianza: dict[str, Any] | None) -> None:
    try:
        from prometheus_client import Counter, Gauge, REGISTRY
    except ImportError:
        return

    if not confianza:
        return

    review_counter = _collector_by_name(REGISTRY, "consulta_review_required_total")
    faithfulness_gauge = _collector_by_name(REGISTRY, "consulta_faithfulness_score")

    if review_counter is None:
        review_counter = Counter(
            "consulta_review_required_total",
            "Total consulta responses grouped by review requirement",
            ["endpoint", "review_required"],
        )
    if faithfulness_gauge is None:
        faithfulness_gauge = Gauge(
            "consulta_faithfulness_score",
            "Latest faithfulness score observed for consulta endpoint",
            ["endpoint"],
        )

    review_required = bool(confianza.get("review_required"))
    faithfulness_score = confianza.get("faithfulness_score")
    review_counter.labels(endpoint=endpoint, review_required=str(review_required).lower()).inc()
    if isinstance(faithfulness_score, (int, float)):
        faithfulness_gauge.labels(endpoint=endpoint).set(float(faithfulness_score))


def record_worker_metrics(worker: str, stale: bool, lag_seconds: float | None) -> None:
    try:
        from prometheus_client import Gauge, REGISTRY
    except ImportError:
        return

    stale_gauge = _collector_by_name(REGISTRY, "worker_stale_status")
    lag_gauge = _collector_by_name(REGISTRY, "worker_lag_seconds")

    if stale_gauge is None:
        stale_gauge = Gauge(
            "worker_stale_status",
            "Worker stale flag as gauge (1 stale, 0 healthy)",
            ["worker"],
        )
    if lag_gauge is None:
        lag_gauge = Gauge(
            "worker_lag_seconds",
            "Seconds since the worker last finished successfully or attempted a run",
            ["worker"],
        )

    stale_gauge.labels(worker=worker).set(1.0 if stale else 0.0)
    if lag_seconds is not None:
        lag_gauge.labels(worker=worker).set(float(lag_seconds))


def record_source_freshness_metrics(sources: list[dict[str, Any]]) -> None:
    try:
        from prometheus_client import Gauge, REGISTRY
    except ImportError:
        return

    stale_gauge = _collector_by_name(REGISTRY, "source_freshness_stale_status")
    changed_gauge = _collector_by_name(REGISTRY, "source_freshness_changed_since_previous")

    if stale_gauge is None:
        stale_gauge = Gauge(
            "source_freshness_stale_status",
            "Source freshness stale flag as gauge (1 stale, 0 healthy)",
            ["source_id"],
        )
    if changed_gauge is None:
        changed_gauge = Gauge(
            "source_freshness_changed_since_previous",
            "Source freshness change flag between latest and previous snapshot",
            ["source_id"],
        )

    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            continue
        stale_gauge.labels(source_id=source_id).set(1.0 if source.get("stale") else 0.0)
        changed_gauge.labels(source_id=source_id).set(1.0 if source.get("changed_since_previous") else 0.0)


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
