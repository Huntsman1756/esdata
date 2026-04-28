import asyncio

from fastapi_mcp import FastApiMCP
from starlette.responses import Response


def _patch_http_transport_readiness(http_transport) -> None:
    if http_transport is None:
        return

    original_ensure_started = http_transport._ensure_session_manager_started
    original_handle_request = http_transport.handle_fastapi_request

    async def _ensure_started_and_ready() -> None:
        await original_ensure_started()

        session_manager = getattr(http_transport, "_session_manager", None)
        if session_manager is None:
            return

        for _ in range(50):
            if getattr(session_manager, "_task_group", None) is not None:
                return
            manager_task = getattr(http_transport, "_manager_task", None)
            if manager_task is not None and manager_task.done():
                await manager_task
            await asyncio.sleep(0.01)

        raise RuntimeError("MCP HTTP session manager did not initialize task group in time")

    http_transport._ensure_session_manager_started = _ensure_started_and_ready

    async def _handle_fastapi_request(request):
        accepts_sse = "text/event-stream" in (request.headers.get("accept") or "").lower()
        if request.method == "GET" and not accepts_sse:
            return Response(
                content="Not Acceptable: Client must accept text/event-stream",
                status_code=406,
                media_type="text/plain",
            )
        return await original_handle_request(request)

    http_transport.handle_fastapi_request = _handle_fastapi_request


def mount_mcp(app):
    mcp = FastApiMCP(
        app,
        headers=["authorization", "x-request-id", "x-user-id"],
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
            # 31.9.1 SFDR — Sustainable Finance Disclosure Regulation
            "list_sfdr_products",
            "get_sfdr_product",
            "list_sfdr_pacai_indicators",
            "get_sfdr_pacai_indicator",
            "list_sfdr_entity_paci",
            "get_sfdr_entity_paci",
            "list_sfdr_pre_contractual",
            "get_sfdr_pre_contractual",
            "list_sfdr_annual_reports",
            "get_sfdr_annual_report",
            # 31.9.2 CSRD — Corporate Sustainability Reporting Directive
            "list_csrd_entity_reports",
            "get_csrd_entity_report",
            "list_csrd_esg_data_points",
            "get_csrd_esg_data_point",
            "list_csrd_ess",
            "get_csrd_ess",
            "list_csrd_double_materiality",
            "get_csrd_double_materiality",
            # 31.9.3 AIFMD/UCITS — Fund regulation
            "list_aifmd_funds",
            "get_aifmd_fund",
            "list_aifmd_regulatory_reports",
            "get_aifmd_regulatory_report",
            "list_aifmd_liquidity_management",
            "get_aifmd_liquidity_management",
            "list_ucits_funds",
            "get_ucits_fund",
            "list_ucits_regulatory_reports",
            "get_ucits_regulatory_report",
            # 31.9.4 CRD V/CRR, BRRD, EMIR — Prudential regulation
            "list_crd_capital_positions",
            "get_crd_capital_position",
            "list_crd_stress_tests",
            "get_crd_stress_test",
            "list_brrd_bail_in",
            "get_brrd_bail_in",
            "list_emir_trade_reports",
            "get_emir_trade_report",
            "list_emir_clearing_members",
            "get_emir_clearing_member",
        ],
    )
    mcp.mount_http(mount_path="/mcp")
    http_transport = getattr(mcp, "_http_transport", None)
    _patch_http_transport_readiness(http_transport)
    return http_transport
