import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp_security import _RATE_BUCKETS, _rate_limit_per_minute, _required_api_key
from mcp_server import mount_mcp
from routers import (
    buscar,
    doctrina,
    jurisprudencia,
    legislacion,
    materias,
    modelos,
    status,
)

app = FastAPI(
    title="esdata API",
    version="0.1.6",
    description="API de consulta de legislacion espanola consolidada, doctrina interpretativa y modelos tributarios AEAT. "
    "Permite buscar articulos por texto, consultar normas, doctrina (DGT, TEAC) y obtener casillas, claves e instrucciones de modelos fiscales.",
)

app.include_router(status.router)
app.include_router(buscar.router)
app.include_router(legislacion.router)
app.include_router(materias.router)
app.include_router(doctrina.router)
app.include_router(jurisprudencia.router)
app.include_router(modelos.router)

mount_mcp(app)


@app.middleware("http")
async def mcp_security_guard(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    required_key = _required_api_key()
    if not required_key:
        return await call_next(request)

    provided_key = request.headers.get("X-API-Key", "")
    if provided_key != required_key:
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    bucket = _RATE_BUCKETS[provided_key]
    now = time.time()
    while bucket and now - bucket[0] > 60:
        bucket.popleft()

    if len(bucket) >= _rate_limit_per_minute():
        return JSONResponse({"detail": "MCP rate limit exceeded"}, status_code=429)

    bucket.append(now)
    return await call_next(request)
