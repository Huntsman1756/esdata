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
    - retrieval_latency_seconds: Histogram of retrieval-only latency (P95/P99)
    - component_errors_total: Counter by component and error type
    - query_tokens_total: Counter of input/output tokens per query
    - query_memory_bytes: Gauge of RAM/VRAM used per query
    - faithfulness_score: Histogram of faithfulness scores for trending
    """
    try:
        from prometheus_client import REGISTRY, Counter, Gauge, Histogram
    except ImportError:
        logger.warning("prometheus_client not installed, metrics disabled")
        return None

    # Idempotent registration: re-use existing collectors if already registered
    _existing = REGISTRY._names_to_collectors
    _reuse = "http_requests_total" in _existing and "http_request_duration_seconds" in _existing
    request_count: Counter | None = None
    request_duration: Histogram | None = None
    consulta_review_required: Counter | None = None
    consulta_faithfulness_score: Gauge | None = None
    retrieval_latency: Histogram | None = None
    component_errors: Counter | None = None
    query_tokens: Counter | None = None
    query_memory: Gauge | None = None
    faithfulness_histogram: Histogram | None = None
    if _reuse:
        request_count = _collector_by_name(REGISTRY, "http_requests_total")
        request_duration = _collector_by_name(REGISTRY, "http_request_duration_seconds")
        consulta_review_required = _collector_by_name(REGISTRY, "consulta_review_required_total")
        consulta_faithfulness_score = _collector_by_name(REGISTRY, "consulta_faithfulness_score")
        retrieval_latency = _collector_by_name(REGISTRY, "retrieval_latency_seconds")
        component_errors = _collector_by_name(REGISTRY, "component_errors_total")
        query_tokens = _collector_by_name(REGISTRY, "query_tokens_total")
        query_memory = _collector_by_name(REGISTRY, "query_memory_bytes")
        faithfulness_histogram = _collector_by_name(REGISTRY, "faithfulness_score")
    else:
        request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )
        request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        consulta_review_required = Counter(  # noqa: F841
            "consulta_review_required_total",
            "Total consulta responses grouped by review requirement",
            ["endpoint", "review_required"],
        )
        consulta_faithfulness_score = Gauge(  # noqa: F841
            "consulta_faithfulness_score",
            "Latest faithfulness score observed for consulta endpoint",
            ["endpoint"],
        )
        retrieval_latency = Histogram(  # noqa: F841
            "retrieval_latency_seconds",
            "Retrieval-only latency in seconds (P95/P99)",
            ["endpoint", "source"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )
        component_errors = Counter(  # noqa: F841
            "component_errors_total",
            "Component errors by source and type",
            ["component", "error_type"],
        )
        query_tokens = Counter(  # noqa: F841
            "query_tokens_total",
            "Input and output tokens per query",
            ["query_type", "token_phase"],
        )
        query_memory = Gauge(  # noqa: F841
            "query_memory_bytes",
            "RAM/VRAM used per query in bytes",
            ["component"],
        )
        faithfulness_histogram = Histogram(  # noqa: F841
            "faithfulness_score",
            "Faithfulness score distribution for trending",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

    async def metrics_middleware(request, call_next):
        start_time = time.time()
        endpoint = request.url.path

        # Normalize endpoint for grouping (replace path params with generic)
        normalized_endpoint = _normalize_path(endpoint)

        response = await call_next(request)

        duration = time.time() - start_time
        request_count.labels(
            method=request.method,
            endpoint=normalized_endpoint,
            status=response.status_code,
        ).inc()
        request_duration.labels(
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
        from prometheus_client import REGISTRY, Counter, Gauge
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
        from prometheus_client import REGISTRY, Gauge
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
        from prometheus_client import REGISTRY, Gauge
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


def record_retrieval_latency(endpoint: str, source: str, duration: float) -> None:
    """Record retrieval-only latency for P95/P99 tracking."""
    try:
        from prometheus_client import REGISTRY, Histogram
    except ImportError:
        return

    histogram = _collector_by_name(REGISTRY, "retrieval_latency_seconds")
    if histogram is None:
        histogram = Histogram(
            "retrieval_latency_seconds",
            "Retrieval-only latency in seconds (P95/P99)",
            ["endpoint", "source"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )
    histogram.labels(endpoint=endpoint, source=source).observe(duration)


def record_component_error(component: str, error_type: str) -> None:
    """Record component error for error rate tracking."""
    try:
        from prometheus_client import REGISTRY, Counter
    except ImportError:
        return

    counter = _collector_by_name(REGISTRY, "component_errors_total")
    if counter is None:
        counter = Counter(
            "component_errors_total",
            "Component errors by source and type",
            ["component", "error_type"],
        )
    counter.labels(component=component, error_type=error_type).inc()


def record_query_tokens(query_type: str, phase: str, count: int) -> None:
    """Record input/output tokens per query for cost tracking."""
    try:
        from prometheus_client import REGISTRY, Counter
    except ImportError:
        return

    counter = _collector_by_name(REGISTRY, "query_tokens_total")
    if counter is None:
        counter = Counter(
            "query_tokens_total",
            "Input and output tokens per query",
            ["query_type", "token_phase"],
        )
    counter.labels(query_type=query_type, token_phase=phase).inc(count)


def record_query_memory(component: str, bytes_used: float) -> None:
    """Record RAM/VRAM used per query for resource tracking."""
    try:
        from prometheus_client import REGISTRY, Gauge
    except ImportError:
        return

    gauge = _collector_by_name(REGISTRY, "query_memory_bytes")
    if gauge is None:
        gauge = Gauge(
            "query_memory_bytes",
            "RAM/VRAM used per query in bytes",
            ["component"],
        )
    gauge.labels(component=component).set(bytes_used)


def record_faithfulness_histogram(score: float) -> None:
    """Record faithfulness score in histogram for trending."""
    try:
        from prometheus_client import REGISTRY, Histogram
    except ImportError:
        return

    histogram = _collector_by_name(REGISTRY, "faithfulness_score")
    if histogram is None:
        histogram = Histogram(
            "faithfulness_score",
            "Faithfulness score distribution for trending",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )
    histogram.observe(float(score))


def create_metrics_endpoint(refresh_metrics=None):
    """Create /metrics endpoint handler.

    Returns an async function that serves Prometheus metrics in text format.
    """
    try:
        from prometheus_client import REGISTRY, generate_latest
    except ImportError:
        logger.warning("prometheus_client not installed, metrics endpoint disabled")
        return None

    async def metrics_endpoint():
        try:
            if refresh_metrics is not None:
                refresh_metrics()
            metrics_bytes = generate_latest(REGISTRY)
            return Response(
                content=metrics_bytes,
                media_type="text/plain; charset=utf-8",
            )
        except Exception as e:
            logger.exception("Failed to generate metrics: %s", e)
            return Response(
                content=f"# Error generating metrics: {e}\n",
                status_code=500,
                media_type="text/plain",
            )

    return metrics_endpoint
