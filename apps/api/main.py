from fastapi import FastAPI

from mcp_server import mount_mcp
from routers import bdns, borme, buscar, cnmv, doctrina, empresas, legislacion, materias, modelos, obligaciones, sepblac, status

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
