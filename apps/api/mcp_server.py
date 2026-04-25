from fastapi_mcp import FastApiMCP


def mount_mcp(app) -> None:
    mcp = FastApiMCP(
        app,
        include_operations=[
            # Consulta fiscal inteligente (principal)
            "consulta_fiscal",
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
            "list_modelos_campanas_operativas",
            "get_modelo",
            "get_modelo_articulos",
            "get_modelo_casillas",
            "get_modelo_claves",
            "get_modelo_instrucciones",
            "get_modelo_normativa",
            "get_modelo_artefactos",
            "get_modelo_campana_operativa",
            "get_modelo_resumen_operativo",
            "get_modelo_fuentes_oficiales",
            # BORME - Registro Mercantil
            "listar_borme",
            "get_borme",
            # SEPBLAC - Blanqueo de capitales
            "listar_sepblac",
            "get_sepblac",
            # Empresas
            "listar_empresas",
            "get_empresa",
            # Obligaciones regulatorias
            "listar_obligaciones",
            "listar_obligaciones_aplicables",
            "get_obligacion",
            "listar_obligaciones_operativas",
            "listar_deadlines",
            # BDNS - Subvenciones
            "listar_bdns",
            "get_bdns",
            # CNMV - Mercado de valores
            "listar_cnmv",
            "get_cnmv",
        ],
    )
    mcp.mount_http(mount_path="/mcp")
