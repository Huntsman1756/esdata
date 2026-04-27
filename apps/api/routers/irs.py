from db import db_session
from fastapi import APIRouter, Query
from services import irs as irs_svc

router = APIRouter(prefix="/v1/irs/modelos", tags=["IRS modelos"])


@router.get(
    "",
    operation_id="list_irs_modelos",
    summary="Listar modelos IRS",
    description="Consulta de modelos fiscales del IRS (Internal Revenue Service) con filtros por periodo, impuesto y estado activo.",
)
async def list_irs_modelos(
    periodo: str | None = Query(None, description="Filtrar por periodo: anual, trimestral, mensual, evento"),
    impuesto: str | None = Query(None, description="Filtrar por impuesto: Income Tax, Payroll Tax, Excise Tax"),
    activo: bool | None = Query(None, description="Filtrar por estado activo"),
):
    with db_session() as db:
        rows = irs_svc.list_irs_models(db, periodo=periodo, impuesto=impuesto, activo=activo)
        return {"modelos": rows, "total": len(rows)}


@router.get(
    "/{codigo}",
    operation_id="get_irs_modelo",
    summary="Detalle modelo IRS",
    description="Obtiene detalle de un modelo fiscal IRS por su codigo (ej: 1040, 1120, 1065).",
)
async def get_irs_modelo(codigo: str):
    with db_session() as db:
        modelo = irs_svc.get_irs_model(db, codigo)
        if not modelo:
            return {"error": f"Modelo {codigo} not found", "codigo": codigo}
        return {"modelo": modelo}
