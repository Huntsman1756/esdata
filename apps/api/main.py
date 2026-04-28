import json
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

from agent_monitor import start_agent_monitor, stop_agent_monitor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from mcp_security import guard_mcp_http
from mcp_server import mount_mcp
from middleware.ai_audit import ai_audit_middleware
from middleware.ai_safety import ai_safety_middleware
from middleware.api_key_auth import ApiKeyAuthMiddleware
from middleware.human_review import HumanReviewMiddleware
from middleware.metrics import create_metrics_endpoint, create_metrics_middleware
from middleware.rate_limit import rate_limit_middleware
from middleware.request_logging import RequestLoggingMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.xai import xai_middleware
from routers import (
    aepd,
    ai_audit_log,
    ai_risk,
    ai_safety,
    aifmd_ucits,
    banking,
    bde,
    bdns,
    borme,
    buscar,
    calendario_fiscal,
    cambios,
    cendoj,
    chunks,
    cnmv,
    compliance,
    connectivity,
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
    dora,
    dta_convenios,
    editorial,
    editorial_posiciones,
    empresas,
    entidades,
    eurlex,
    fairness,
    fraud,
    gdpr,
    human_review,
    internacional,
    irs,
    irs_fiscal,
    irs_w8,
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
    xai,
    xbrl,
)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

logger = logging.getLogger(__name__)
MCP_HTTP_TRANSPORT = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    def _load_model():
        try:
            from apps.workers.embeddings import get_model
            model = get_model()
            if model:
                logger.info("Embedding model loaded in background thread")
            else:
                logger.warning("Embedding model not available")
        except Exception:
            logger.warning("Failed to load embedding model", exc_info=True)
    t = threading.Thread(target=_load_model, daemon=True)
    t.start()
    logger.info("Embedding model loading in background...")

    # Start agent monitor (opt-in via AGENT_MONITOR_ENABLED)
    start_agent_monitor()

    if MCP_HTTP_TRANSPORT is not None:
        await MCP_HTTP_TRANSPORT._ensure_session_manager_started()

    yield

    if MCP_HTTP_TRANSPORT is not None:
        await MCP_HTTP_TRANSPORT.shutdown()

    # Stop agent monitor on shutdown
    stop_agent_monitor()

def _validate_runtime_env() -> None:
    app_env = os.environ.get("APP_ENV", "development").lower()
    esdata_api_key = os.environ.get("ESDATA_API_KEY", "").strip()
    mcp_api_key = os.environ.get("MCP_API_KEY", "").strip()
    allow_insecure_test_auth = os.environ.get("ESDATA_ALLOW_INSECURE_TEST_AUTH", "").lower() == "true"

    if app_env != "test" and not esdata_api_key:
        raise RuntimeError(
            "ESDATA_API_KEY is required outside APP_ENV=test. "
            "The API must not start in fail-open mode."
        )

    if app_env != "test" and not mcp_api_key:
        raise RuntimeError(
            "MCP_API_KEY is required outside APP_ENV=test. "
            "The /mcp surface must not start unprotected."
        )

    if app_env == "test" and allow_insecure_test_auth:
        logger.warning("Insecure auth bypass enabled for APP_ENV=test")
    else:
        logger.info("API key auth enforced for protected endpoints")


def _resolve_root_dir() -> Path:
    current = Path(__file__).resolve()
    candidates = [current.parent, *current.parents]
    for candidate in candidates:
        if (candidate / "docs").exists():
            return candidate
    return current.parent


ROOT_DIR = _resolve_root_dir()


async def gpt_action_modelos_openapi():
    spec_path = ROOT_DIR / "docs" / "openapi-gpt-minimal-modelos.json"
    return JSONResponse(json.loads(spec_path.read_text(encoding="utf-8")))


async def privacy_policy():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>esdata Privacy Policy</title>
      </head>
      <body>
        <h1>esdata Privacy Policy</h1>
        <p>esdata processes requests sent through this GPT Action only to return regulatory and tax data from the esdata API.</p>
        <p>No authentication is required for this action. Request logs may be retained for operational debugging and service reliability.</p>
        <p>Do not send secrets, credentials, payment data, or personal tax identifiers through this action.</p>
      </body>
    </html>
    """


def _configure_sentry() -> None:
    sentry_dsn = os.environ.get("ESDATA_SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
            ],
            environment=os.environ.get("APP_ENV", "production"),
        )
        logger.info("Sentry error monitoring enabled")
    else:
        logger.info("Sentry disabled (no ESDATA_SENTRY_DSN)")


def create_app() -> FastAPI:
    app = FastAPI(
        title="esdata API",
        version="0.1.6",
        description="API de consulta de legislacion espanola consolidada, doctrina interpretativa y modelos tributarios AEAT. "
        "Permite buscar articulos por texto, consultar normas, doctrina (DGT, TEAC) y obtener casillas, claves e instrucciones de modelos fiscales.",
        lifespan=lifespan,
    )

    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(guard_mcp_http)
    app.add_middleware(SecurityHeadersMiddleware)

    cors_origins_str = os.environ.get("ESDATA_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    cors_origins = [o.strip() for o in cors_origins_str.split(",")] if cors_origins_str != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(ApiKeyAuthMiddleware)
    app.middleware("http")(ai_audit_middleware)
    app.middleware("http")(ai_safety_middleware)
    app.middleware("http")(xai_middleware)
    app.add_middleware(HumanReviewMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    _validate_runtime_env()

    metrics_middleware = create_metrics_middleware()
    if metrics_middleware:
        app.middleware("http")(metrics_middleware)

    metrics_endpoint = create_metrics_endpoint()
    if metrics_endpoint:
        app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

    app.include_router(status.router)
    app.include_router(buscar.router)
    app.include_router(cambios.router)
    app.include_router(compliance.router)
    app.include_router(connectivity.router)
    app.include_router(legislacion.router)
    app.include_router(materias.router)
    app.include_router(dgt_doctrina.router)
    app.include_router(doctrina.router)
    app.include_router(bdns.router)
    app.include_router(borme.router)
    app.include_router(cnmv.router)
    app.include_router(sepblac.router)
    app.include_router(obligaciones.router)
    app.include_router(empresas.router)
    app.include_router(entidades.router)
    app.include_router(modelos.router)
    app.include_router(consulta.router)
    app.include_router(chunks.router)
    app.include_router(cendoj.router)
    app.include_router(eurlex.router)
    app.include_router(dac_directives.router)
    app.include_router(prospectos.router)
    app.include_router(bde.router)
    app.include_router(aepd.router)
    app.include_router(pgc.router)
    app.include_router(ownership.router)
    app.include_router(screening.router)
    app.include_router(irs.router)
    app.include_router(irs_fiscal.router)
    app.include_router(irs_w8.router)
    app.include_router(calendario_fiscal.router)
    app.include_router(internacional.router)
    app.include_router(dta_convenios.router)
    app.include_router(ley272014.router)
    app.include_router(trlmv.router)
    app.include_router(ley62018.router)
    app.include_router(ley112021.router)
    app.include_router(nrv9.router)
    app.include_router(mercantil.router)
    app.include_router(dac8.router)
    app.include_router(pbc.router)
    app.include_router(fraud.router)
    app.include_router(mica.router)
    app.include_router(xbrl.router)
    app.include_router(playbooks.router)
    app.include_router(risk_control_matrix.router)
    app.include_router(criterio.router)
    app.include_router(criterio_curacion.router)
    app.include_router(editorial.router)
    app.include_router(editorial_posiciones.router)
    app.include_router(micro_obligaciones.router)
    app.include_router(banking.router)
    app.include_router(ai_audit_log.router)
    app.include_router(ai_risk.router)
    app.include_router(ai_safety.router)
    app.include_router(human_review.router)
    app.include_router(model_registry.router)
    app.include_router(model_registry.config_router)
    app.include_router(data_lineage.router)
    app.include_router(query_audit.router)
    app.include_router(gdpr.router)
    app.include_router(source_manifest.router)
    app.include_router(observability.router)
    app.include_router(xai.router)
    app.include_router(fairness.router)
    app.include_router(ley222010.router)
    app.include_router(rd2172008.router)
    app.include_router(ley13_2023.router)
    app.include_router(ley112009_socimi.router)
    app.include_router(ley222014_lecr.router)
    app.include_router(csdr.router)
    app.include_router(corporate_sustainability.router)
    app.include_router(mifid.router)
    app.include_router(mar.router)
    app.include_router(dora.router)
    app.include_router(priips.router)
    app.include_router(transparency.router)
    app.include_router(sustainable_finance.router)
    app.include_router(aifmd_ucits.router)
    app.include_router(aifmd_ucits.ucits_router)
    app.include_router(crd_brrd_emir.router)
    app.include_router(crd_brrd_emir.ucits_router)
    app.include_router(psd2.router)
    app.include_router(psd2.consumer_credit_router)
    app.include_router(psd2.insurance_router)
    global MCP_HTTP_TRANSPORT
    MCP_HTTP_TRANSPORT = mount_mcp(app)

    app.add_api_route(
        "/gpt-actions/modelos/openapi.json",
        gpt_action_modelos_openapi,
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        "/privacy",
        privacy_policy,
        methods=["GET"],
        include_in_schema=False,
        response_class=HTMLResponse,
    )

    return app


_configure_sentry()
app = create_app()
