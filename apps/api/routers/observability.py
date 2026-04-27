from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/observability", tags=["observability"])


def _metric_sample_value(registry, metric_name: str, labels: dict[str, str]) -> float | None:
    collector = registry._names_to_collectors.get(metric_name)
    if collector is None:
        return None
    for sample in collector.collect()[0].samples:
        if sample.labels == labels:
            return float(sample.value)
    return None


def _build_dashboard_payload():
    try:
        from prometheus_client import REGISTRY
    except ImportError:
        return {"consulta": {}, "workers": {}, "fuentes": {}, "summary": {}}

    workers = {}
    worker_collector = REGISTRY._names_to_collectors.get("worker_stale_status")
    if worker_collector is not None:
        for sample in worker_collector.collect()[0].samples:
            worker = sample.labels.get("worker")
            if not worker:
                continue
            workers[worker] = {
                "stale": bool(sample.value),
                "lag_seconds": _metric_sample_value(REGISTRY, "worker_lag_seconds", {"worker": worker}),
            }

    fuentes = {}
    source_collector = REGISTRY._names_to_collectors.get("source_freshness_stale_status")
    if source_collector is not None:
        for sample in source_collector.collect()[0].samples:
            source_id = sample.labels.get("source_id")
            if not source_id:
                continue
            fuentes[source_id] = {
                "stale": bool(sample.value),
                "changed_since_previous": bool(
                    _metric_sample_value(
                        REGISTRY,
                        "source_freshness_changed_since_previous",
                        {"source_id": source_id},
                    )
                    or 0.0
                ),
            }

    consulta = {
        "faithfulness_score": _metric_sample_value(
            REGISTRY,
            "consulta_faithfulness_score",
            {"endpoint": "/v1/consulta"},
        )
        or 0.0,
        "review_required_total": _metric_sample_value(
            REGISTRY,
            "consulta_review_required_total_total",
            {"endpoint": "/v1/consulta", "review_required": "true"},
        )
        or 0.0,
        "review_not_required_total": _metric_sample_value(
            REGISTRY,
            "consulta_review_required_total_total",
            {"endpoint": "/v1/consulta", "review_required": "false"},
        )
        or 0.0,
    }

    summary = {
        "stale_workers": sum(1 for worker in workers.values() if worker.get("stale")),
        "stale_sources": sum(1 for source in fuentes.values() if source.get("stale")),
        "changed_sources": sum(1 for source in fuentes.values() if source.get("changed_since_previous")),
        "review_required_total": consulta["review_required_total"],
    }

    return {"consulta": consulta, "workers": workers, "fuentes": fuentes, "summary": summary}


@router.get("/dashboard")
def observability_dashboard():
    return _build_dashboard_payload()


@router.get("/alerts")
def observability_alerts():
    dashboard = _build_dashboard_payload()
    alerts = []

    for worker, payload in dashboard.get("workers", {}).items():
        if payload.get("stale"):
            alerts.append(
                {
                    "domain": "workers",
                    "severity": "warning",
                    "key": worker,
                    "message": f"Worker {worker} appears stale",
                }
            )

    for source_id, payload in dashboard.get("fuentes", {}).items():
        if payload.get("stale"):
            alerts.append(
                {
                    "domain": "sources",
                    "severity": "warning",
                    "key": source_id,
                    "message": f"Source {source_id} appears stale",
                }
            )
        elif payload.get("changed_since_previous"):
            alerts.append(
                {
                    "domain": "sources",
                    "severity": "info",
                    "key": source_id,
                    "message": f"Source {source_id} changed since previous snapshot",
                }
            )

    if dashboard.get("consulta", {}).get("review_required_total", 0.0) > 0:
        alerts.append(
            {
                "domain": "consulta",
                "severity": "warning",
                "key": "review_required_total",
                "message": "Consulta responses currently require human review",
            }
        )

    summary = {
        "warning": sum(1 for alert in alerts if alert["severity"] == "warning"),
        "info": sum(1 for alert in alerts if alert["severity"] == "info"),
        "total": len(alerts),
    }
    return {"alerts": alerts, "summary": summary}
