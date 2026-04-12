from fastapi import FastAPI

from mcp_server import mount_mcp
from routers import buscar, doctrina, legislacion, materias, modelos, status

app = FastAPI(title="esdata API", version="0.1.6")

app.include_router(status.router)
app.include_router(buscar.router)
app.include_router(legislacion.router)
app.include_router(materias.router)
app.include_router(doctrina.router)
app.include_router(modelos.router)

mount_mcp(app)
