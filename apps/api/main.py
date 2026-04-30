import os
from contextlib import asynccontextmanager

from db import db_session
from fastapi import FastAPI
from mcp_security import guard_mcp_http
from mcp_server import mount_mcp
from middleware.api_key_auth import ApiKeyAuthMiddleware
from middleware.metrics import create_metrics_endpoint, create_metrics_middleware
from middleware.rate_limit import rate_limit_middleware
from middleware.request_logging import RequestLoggingMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from routers import (
    ai_audit_log,
    buscar,
    cambios,
    compliance,
    consulta,
    crd_brrd_emir,
    data_lineage,
    doctrina,
    editorial,
    editorial_posiciones,
    human_review,
    jurisprudencia,
    legislacion,
    materias,
    mica,
    model_registry,
    modelos,
    observability,
    query_audit,
    source_manifest,
    status,
    webhooks,
)
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware


def _validate_auth_config() -> None:
    app_env = os.environ.get("APP_ENV", "development").lower()
    if app_env == "test":
        return

    if not os.environ.get("ESDATA_API_KEY", "").strip():
        raise RuntimeError("ESDATA_API_KEY is required outside APP_ENV=test")

    if not os.environ.get("MCP_API_KEY", "").strip():
        raise RuntimeError("MCP_API_KEY is required outside APP_ENV=test")


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "ESDATA_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if any(origin == "*" for origin in origins):
        raise RuntimeError("ESDATA_CORS_ORIGINS must be an explicit list; '*' is not allowed")
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_auth_config()
    _verify_database_connectivity()
    yield


app = FastAPI(
    title="esdata API",
    version="0.1.6",
    description=(
        "API de consulta fiscal-regulatoria con trazabilidad a fuente oficial, "
        "superficies de governance y workers observables via sync_log."
    ),
    lifespan=lifespan,
)

_metrics_endpoint_fn = create_metrics_endpoint()
if _metrics_endpoint_fn is not None:
    app.add_api_route("/metrics", _metrics_endpoint_fn, methods=["GET"], tags=["metrics"])

_metrics_middleware_fn = create_metrics_middleware()
if _metrics_middleware_fn is not None:
    app.middleware("http")(_metrics_middleware_fn)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ApiKeyAuthMiddleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(guard_mcp_http)

for router in (
    status.router,
    buscar.router,
    legislacion.router,
    materias.router,
    doctrina.router,
    jurisprudencia.router,
    modelos.router,
    consulta.router,
    cambios.router,
    compliance.router,
    mica.router,
    crd_brrd_emir.router,
    crd_brrd_emir.ucits_router,
    ai_audit_log.router,
    human_review.router,
    data_lineage.router,
    model_registry.router,
    model_registry.config_router,
    query_audit.router,
    source_manifest.router,
    observability.router,
    webhooks.webhook_router,
    editorial.router,
    editorial_posiciones.router,
):
    app.include_router(router)

mount_mcp(app)


def _verify_database_connectivity() -> None:
    try:
        with db_session() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Database connectivity check failed: {e}") from e
