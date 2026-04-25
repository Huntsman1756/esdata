from fastapi import APIRouter

from compliance_workflow_data import list_workflow_cases

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


@router.get("/workflow", operation_id="listar_workflow_compliance")
async def listar_workflow_compliance():
    return list_workflow_cases()
