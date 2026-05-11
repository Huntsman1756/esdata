from fastapi import APIRouter, Query

from compliance_workflow_data import list_workflow_cases

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


@router.get("/workflow", operation_id="listar_workflow_compliance")
async def listar_workflow_compliance(
    limit: int = Query(200, ge=1, le=500, description="Tamano de pagina aplicado"),
    offset: int = Query(0, ge=0, description="Offset de resultados"),
):
    items = list_workflow_cases()
    page = items[offset : offset + limit]
    total = len(items)
    has_more = offset + len(page) < total
    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + len(page) if has_more else None,
    }
