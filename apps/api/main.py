import json
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

from agent_monitor import start_agent_monitor, stop_agent_monitor
from mcp_security import guard_mcp_http
from mcp_server import mount_mcp
from middleware.api_key_auth import ApiKeyAuthMiddleware
from middleware.metrics import create_metrics_endpoint, create_metrics_middleware
from middleware.rate_limit import rate_limit_middleware
from middleware.request_logging import RequestLoggingMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from routers import (
    aepd,
    bde,
    bdns,
    borme,
    buscar,
    cambios,
    cendoj,
    cnmv,
    chunks,
    compliance,
    consulta,
    doctrina,
    empresas,
    eurlex,
    legislacion,
    materias,
    modelos,
    obligaciones,
    sepblac,
    status,
)

logger = logging.getLogger(__name__)


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

    yield

    # Stop agent monitor on shutdown
    stop_agent_monitor()

app = FastAPI(
    title="esdata API",
    version="0.1.6",
    description="API de consulta de legislacion espanola consolidada, doctrina interpretativa y modelos tributarios AEAT. "
    "Permite buscar articulos por texto, consultar normas, doctrina (DGT, TEAC) y obtener casillas, claves e instrucciones de modelos fiscales.",
    lifespan=lifespan,
)

# Rate limiting middleware (primero para que se aplique antes de cualquier logica)
app.middleware("http")(rate_limit_middleware)

# MCP HTTP guard — API key + rate limit for /mcp endpoint
app.middleware("http")(guard_mcp_http)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware (configurable via env)
_cors_origins_str = os.environ.get("ESDATA_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",")] if _cors_origins_str != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key auth middleware (applied after rate limiting & CORS)
app.add_middleware(ApiKeyAuthMiddleware)

# Request logging middleware (after auth so it logs the real status)
app.add_middleware(RequestLoggingMiddleware)

# Env var validation at startup
_esdata_api_key = os.environ.get("ESDATA_API_KEY")
_esdata_auth_enabled = os.environ.get("ESDATA_AUTH_ENABLED", "").lower() == "true"
if _esdata_auth_enabled and not _esdata_api_key:
    raise RuntimeError(
        "ESDATA_AUTH_ENABLED=true requires ESDATA_API_KEY to be set. "
        "Set ESDATA_API_KEY=<your-key> or disable auth with ESDATA_AUTH_ENABLED=false."
    )
if _esdata_auth_enabled:
    logger.info("API key auth enabled (ESDATA_AUTH_ENABLED=true)")
else:
    logger.info("API key auth disabled (set ESDATA_AUTH_ENABLED=true to enable)")

# Middleware de metrics Prometheus (si prometheus_client esta disponible)
metrics_middleware = create_metrics_middleware()
if metrics_middleware:
    app.middleware("http")(metrics_middleware)

# Endpoint /metrics para Prometheus (si prometheus_client esta disponible)
metrics_endpoint = create_metrics_endpoint()
if metrics_endpoint:
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

app.include_router(status.router)
app.include_router(buscar.router)
app.include_router(cambios.router)
app.include_router(compliance.router)
app.include_router(legislacion.router)
app.include_router(materias.router)
app.include_router(doctrina.router)
app.include_router(bdns.router)
app.include_router(borme.router)
app.include_router(cnmv.router)
app.include_router(sepblac.router)
app.include_router(obligaciones.router)
app.include_router(empresas.router)
app.include_router(modelos.router)
app.include_router(consulta.router)
app.include_router(chunks.router)
app.include_router(cendoj.router)
app.include_router(eurlex.router)
app.include_router(bde.router)
app.include_router(aepd.router)

mount_mcp(app)

# Sentry error monitoring (optional, only if ESDATA_SENTRY_DSN is set)
_sentry_dsn = None
try:
    import os
    _sentry_dsn = os.environ.get("ESDATA_SENTRY_DSN")
except Exception:
    pass

if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
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


def _resolve_root_dir() -> Path:
    current = Path(__file__).resolve()
    candidates = [current.parent, *current.parents]
    for candidate in candidates:
        if (candidate / "docs").exists():
            return candidate
    return current.parent


ROOT_DIR = _resolve_root_dir()


@app.get("/gpt-actions/modelos/openapi.json", include_in_schema=False)
async def gpt_action_modelos_openapi():
    spec_path = ROOT_DIR / "docs" / "openapi-gpt-minimal-modelos.json"
    return JSONResponse(json.loads(spec_path.read_text(encoding="utf-8")))


@app.get("/privacy", include_in_schema=False, response_class=HTMLResponse)
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
