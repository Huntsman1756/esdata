from fastapi_mcp import FastApiMCP


def mount_mcp(app) -> None:
    mcp = FastApiMCP(
        app,
        include_operations=[
            "list_legislacion",
            "get_norma",
            "list_articulos",
            "get_articulo",
            "get_articulo_historial",
            "buscar",
            "buscar_legislacion",
            "list_materias",
            "get_materia",
            "buscar_doctrina",
            "get_doctrina",
        ],
    )
    mcp.mount_http(mount_path="/mcp")
