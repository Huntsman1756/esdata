import os
from contextlib import asynccontextmanager
from pathlib import Path

from db import db_session
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from mcp_security import guard_mcp_http
from mcp_server import mount_mcp
from middleware.ai_audit import ai_audit_middleware
from middleware.api_key_auth import ApiKeyAuthMiddleware
from middleware.domain_availability import DomainAvailabilityMiddleware
from middleware.metrics import create_metrics_endpoint, create_metrics_middleware
from middleware.rate_limit import rate_limit_middleware
from middleware.request_logging import RequestLoggingMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from routers import (
    aepd,
    ai_audit_log,
    aifmd_ucits,
    banking,
    bde,
    bdns,
    boe_diario,
    borme,
    buscar,
    cambios,
    cendoj,
    cnmv,
    compliance,
    consulta,
    corporate_sustainability,
    crd_brrd_emir,
    criterio,
    criterio_curacion,
    csdr,
    dac8,
    dac_directives,
    data_lineage,
    dgt_doctrina,
    doctrina,
    domain_availability,
    dora,
    dta_convenios,
    editorial,
    editorial_posiciones,
    empresas,
    entidades,
    esma_dlt,
    esma_firds,
    esma_mifir,
    eurlex,
    eurlex_market,
    fraud,
    human_review,
    internacional,
    irs_fiscal,
    irs_w8,
    jurisprudencia,
    legislacion,
    ley13_2023,
    ley62018,
    ley112009_socimi,
    ley112021,
    ley222010,
    ley222014_lecr,
    ley272014,
    mar,
    materias,
    mercantil,
    mica,
    micro_obligaciones,
    mifid,
    model_registry,
    modelos,
    nrv9,
    obligaciones,
    observability,
    ownership,
    pbc,
    pgc,
    playbooks,
    priips,
    prospectos,
    psd2,
    query_audit,
    rd2172008,
    risk_control_matrix,
    screening,
    sepblac,
    source_manifest,
    status,
    sustainable_finance,
    transparency,
    trlmv,
    webhooks,
    xbrl,
)
from services.model_registry import get_model_registry, register_registry_callbacks
from services.reranker import register_reranker_callbacks
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


_validate_auth_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_auth_config()
    _verify_database_connectivity()
    registry = get_model_registry()
    register_registry_callbacks(registry)
    register_reranker_callbacks()
    mcp_transport = getattr(app.state, "_mcp_http_transport", None)
    if mcp_transport is not None:
        await mcp_transport._ensure_session_manager_started()
    yield
    if mcp_transport is not None:
        await mcp_transport.shutdown()


app = FastAPI(
    title="esdata API",
    version="0.1.6",
    description=(
        "API de consulta fiscal-regulatoria con trazabilidad a fuente oficial, "
        "superficies de governance y workers observables via sync_log."
    ),
    lifespan=lifespan,
)

_metrics_endpoint_fn = create_metrics_endpoint(status.refresh_worker_status_metrics)
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
app.add_middleware(DomainAvailabilityMiddleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(guard_mcp_http)
app.middleware("http")(ai_audit_middleware)

# Expose SQLAlchemy engine for middleware that needs read-only count queries
# (e.g. DomainAvailabilityMiddleware). Routers continue to use db_session().
from db import engine as _db_engine  # noqa: E402

app.state.engine = _db_engine

for router in (
    status.router,
    buscar.router,
    ley112009_socimi.router,
    ley112021.router,
    ley13_2023.router,
    ley222010.router,
    ley222014_lecr.router,
    ley272014.router,
    ley62018.router,
    legislacion.router,
    materias.router,
    mercantil.router,
    micro_obligaciones.router,
    criterio.router,
    criterio_curacion.router,
    dgt_doctrina.router,
    doctrina.router,
    jurisprudencia.router,
    modelos.router,
    nrv9.router,
    ownership.router,
    pgc.router,
    prospectos.router,
    consulta.router,
    cambios.router,
    compliance.router,
    playbooks.router,
    mica.router,
    priips.router,
    psd2.router,
    psd2.consumer_credit_router,
    psd2.insurance_router,
    screening.router,
    mifid.router,
    aifmd_ucits.router,
    aifmd_ucits.ucits_router,
    crd_brrd_emir.router,
    crd_brrd_emir.ucits_router,
    risk_control_matrix.router,
    ai_audit_log.router,
    human_review.router,
    data_lineage.router,
    domain_availability.router,
    model_registry.router,
    model_registry.config_router,
    query_audit.router,
    source_manifest.router,
    observability.router,
    webhooks.webhook_router,
    rd2172008.router,
    banking.router,
    pbc.router,
    internacional.router,
    dta_convenios.router,
    irs_fiscal.router,
    irs_w8.router,
    corporate_sustainability.router,
    csdr.router,
    dac8.router,
    dac_directives.router,
    dora.router,
    editorial.router,
    editorial_posiciones.router,
    empresas.router,
    entidades.router,
    eurlex_market.router,
    eurlex.router,
    esma_mifir.router,
    esma_firds.router,
    esma_dlt.router,
    fraud.router,
    mar.router,
    obligaciones.router,
    sustainable_finance.router,
    transparency.router,
    cnmv.router,
    borme.router,
    boe_diario.router,
    bde.router,
    bdns.router,
    aepd.router,
    cendoj.router,
    sepblac.router,
    trlmv.router,
    xbrl.router,
):
    app.include_router(router)

mount_mcp(app)


def _resolve_docs_artifact_path(
    artifact_name: str,
    current_file: Path | None = None,
) -> Path:
    resolved = (current_file or Path(__file__)).resolve()
    search_roots = [resolved.parent, *resolved.parents]

    for root in search_roots:
        candidate = root / "docs" / artifact_name
        if candidate.exists():
            return candidate

    return resolved.parent / "docs" / artifact_name


def _resolve_gpt_openapi_path(current_file: Path | None = None) -> Path:
    return _resolve_docs_artifact_path("openapi-gpt.json", current_file)


_GPT_OPENAPI_PATH = _resolve_gpt_openapi_path()
_GPT_ACTIONS_30_OPENAPI_PATH = _resolve_docs_artifact_path("openapi-gpt-actions-30.json")


@app.get("/gpt-actions/modelos/openapi.json", include_in_schema=False)
def gpt_actions_openapi():
    return _load_gpt_actions_spec()


@app.get("/gpt-actions/core/openapi.json", include_in_schema=False)
def gpt_actions_core_openapi():
    return _load_gpt_actions_core_spec()


@app.get("/privacy", include_in_schema=False, response_class=HTMLResponse)
def privacy_policy():
    return """
    <html>
      <head><title>esdata privacy</title></head>
      <body>
        <h1>esdata privacy</h1>
        <p>
          esdata procesa consultas y metadatos operativos minimos para ofrecer respuestas
          trazables sobre fuentes regulatorias y fiscales.
        </p>
        <p>
          No publiques secretos ni datos personales innecesarios en prompts o documentos.
        </p>
      </body>
    </html>
    """


def _load_gpt_actions_spec() -> dict:
    import json

    with _GPT_OPENAPI_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_gpt_actions_core_spec() -> dict:
    import json

    with _GPT_ACTIONS_30_OPENAPI_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _verify_database_connectivity() -> None:
    try:
        with db_session() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Database connectivity check failed: {e}") from e
