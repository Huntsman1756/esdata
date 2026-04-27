"""Router para formularios W-8 del IRS."""

from db import db_session
from fastapi import APIRouter, Query
from services import irs_w8 as w8_svc

router = APIRouter(prefix="/v1/irs/w8-forms", tags=["IRS W-8 Forms"])


@router.get(
    "",
    operation_id="list_w8_forms",
    summary="Listar formularios W-8",
    description="Consulta de formularios W-8 (W-8BEN, W-8BEN-E, W-8EXP, W-8ECF) con filtros por tipo de sujeto y estado.",
)
async def list_w8_forms(
    tipo_sujeto: str | None = Query(
        None,
        description="Filtrar por tipo: persona_fisica, persona_juridica, entidad_gubernamental, organizacion_exenta, fideicomiso",
    ),
    estado: str | None = Query(None, description="Filtrar por estado: activo, descontinuado"),
):
    with db_session() as db:
        forms = w8_svc.list_w8_forms(db, tipo_sujeto=tipo_sujeto, estado=estado)
        return {"forms": forms, "total": len(forms)}


@router.get(
    "/{codigo}",
    operation_id="get_w8_form",
    summary="Detalle formulario W-8",
    description="Obtiene detalle de un formulario W-8 por su codigo con guia de completado.",
)
async def get_w8_form(codigo: str):
    with db_session() as db:
        form = w8_svc.get_w8_form(db, codigo)
        if not form:
            return {"error": f"Formulario {codigo} not found", "codigo": codigo}
        return {"form": form}
