from fastapi_mcp import FastApiMCP


def mount_mcp(app) -> None:
    mcp = FastApiMCP(
        app,
        include_operations=[
            # Legislacion
            "list_legislacion",
            "get_norma",
            "list_articulos",
            "get_articulo",
            "get_articulo_historial",
            "buscar",
            "buscar_legislacion",
            # Materias
            "list_materias",
            "get_materia",
            # Doctrina
            "buscar_doctrina",
            "get_doctrina",
            # Modelos AEAT
            "list_modelos",
            "get_modelo",
            "get_modelo_articulos",
            "get_modelo_casillas",
            "get_modelo_claves",
            "get_modelo_instrucciones",
            "get_modelo_normativa",
        ],
    )
    mcp.mount_http(mount_path="/mcp")
