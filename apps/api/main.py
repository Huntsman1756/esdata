import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from mcp_server import mount_mcp
from routers import (
    bdns,
    borme,
    buscar,
    cnmv,
    doctrina,
    empresas,
    legislacion,
    materias,
    modelos,
    obligaciones,
    sepblac,
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
app.include_router(bdns.router)
app.include_router(borme.router)
app.include_router(cnmv.router)
app.include_router(sepblac.router)
app.include_router(obligaciones.router)
app.include_router(empresas.router)
app.include_router(modelos.router)

mount_mcp(app)


ROOT_DIR = Path(__file__).resolve().parents[2]


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
