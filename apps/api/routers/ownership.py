from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    OwnershipGrafoResponse,
    OwnershipGrafoArista,
    OwnershipGrafoNodo,
    OwnershipRelation,
    OwnershipRelationList,
    OwnershipSearchResponse,
    OwnershipSearchResult,
    OwnershipShare,
    OwnershipShareList,
    UboRecord,
    UboRecordList,
)

router = APIRouter(prefix="/v1/ownership", tags=["ownership"])


# ---------------------------------------------------------------------------
# Participaciones
# ---------------------------------------------------------------------------

@router.get(
    "/{empresa_id}/participaciones",
    response_model=OwnershipShareList,
    operation_id="get_participaciones",
)
async def get_participaciones(empresa_id: int):
    with db_session() as db:
        empresa = db.execute(
            text("SELECT id, nombre, nif FROM empresa WHERE id = :eid LIMIT 1"),
            {"eid": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id},
            )

        rows = list(
            db.execute(
                text(
                    """
                    SELECT
                        os.id,
                        os.empresa_id,
                        os.titular_id,
                        os.titular_tipo,
                        os.titular_nombre,
                        os.porcentaje,
                        os.tipo_participacion,
                        os.vigencia_desde,
                        os.vigencia_hasta,
                        os.fuente,
                        os.fuente_ref,
                        di.referencia as documento_referencia
                    FROM ownership_share os
                    LEFT JOIN documento_interpretativo di ON di.id = os.documento_id
                    WHERE os.empresa_id = :eid
                    ORDER BY os.porcentaje DESC, os.id ASC
                    """
                ),
                {"eid": empresa_id},
            ).mappings()
        )

        participaciones = []
        for row in rows:
            participaciones.append(OwnershipShare(
                id=row["id"],
                empresa_id=row["empresa_id"],
                titular_id=row["titular_id"],
                titular_tipo=row["titular_tipo"],
                titular_nombre=row["titular_nombre"],
                porcentaje=float(row["porcentaje"]),
                tipo_participacion=row["tipo_participacion"],
                vigencia_desde=str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
                vigencia_hasta=str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
                fuente=row["fuente"],
                fuente_ref=row["fuente_ref"],
                documento_referencia=row["documento_referencia"],
            ))

        return OwnershipShareList(
            empresa_id=empresa_id,
            nombre=empresa["nombre"],
            participaciones=participaciones,
        )


# ---------------------------------------------------------------------------
# Relaciones societarias
# ---------------------------------------------------------------------------

@router.get(
    "/{empresa_id}/relaciones",
    response_model=OwnershipRelationList,
    operation_id="get_relaciones_societarias",
)
async def get_relaciones_societarias(empresa_id: int):
    with db_session() as db:
        empresa = db.execute(
            text("SELECT id, nombre, nif FROM empresa WHERE id = :eid LIMIT 1"),
            {"eid": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id},
            )

        rows = list(
            db.execute(
                text(
                    """
                    SELECT
                        or_.id,
                        or_.empresa_origen_id,
                        or_.empresa_destino_id,
                        or_.tipo_relacion,
                        or_.porcentaje,
                        or_.vigencia_desde,
                        or_.vigencia_hasta,
                        or_.fuente,
                        or_.fuente_ref,
                        di.referencia as documento_referencia,
                        or_.nota
                    FROM ownership_relation or_
                    LEFT JOIN documento_interpretativo di ON di.id = or_.documento_id
                    WHERE or_.empresa_origen_id = :eid OR or_.empresa_destino_id = :eid
                    ORDER BY or_.tipo_relacion, or_.empresa_destino_id ASC
                    """
                ),
                {"eid": empresa_id},
            ).mappings()
        )

        relaciones = []
        for row in rows:
            relaciones.append(OwnershipRelation(
                id=row["id"],
                empresa_origen_id=row["empresa_origen_id"],
                empresa_destino_id=row["empresa_destino_id"],
                tipo_relacion=row["tipo_relacion"],
                porcentaje=float(row["porcentaje"]) if row["porcentaje"] else None,
                vigencia_desde=str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
                vigencia_hasta=str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
                fuente=row["fuente"],
                fuente_ref=row["fuente_ref"],
                documento_referencia=row["documento_referencia"],
                nota=row["nota"],
            ))

        return OwnershipRelationList(
            empresa_id=empresa_id,
            nombre=empresa["nombre"],
            relaciones=relaciones,
        )


# ---------------------------------------------------------------------------
# Beneficiarios finales (UBOs)
# ---------------------------------------------------------------------------

@router.get(
    "/{empresa_id}/beneficiarios",
    response_model=UboRecordList,
    operation_id="get_beneficiarios_finales",
)
async def get_beneficiarios_finales(empresa_id: int):
    with db_session() as db:
        empresa = db.execute(
            text("SELECT id, nombre, nif FROM empresa WHERE id = :eid LIMIT 1"),
            {"eid": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id},
            )

        rows = list(
            db.execute(
                text(
                    """
                    SELECT
                        ubo.id,
                        ubo.empresa_id,
                        ubo.nombre_persona,
                        ubo.nacionalidad,
                        ubo.fecha_nacimiento,
                        ubo.pais_residencia,
                        ubo.tipo_ubo,
                        ubo.porcentaje_control,
                        ubo.umbral_superado,
                        ubo.vigencia_desde,
                        ubo.vigencia_hasta,
                        ubo.fuente,
                        ubo.fuente_ref,
                        di.referencia as documento_referencia,
                        ubo.nota
                    FROM ubo_record ubo
                    LEFT JOIN documento_interpretativo di ON di.id = ubo.documento_id
                    WHERE ubo.empresa_id = :eid
                    ORDER BY ubo.porcentaje_control DESC NULLS LAST, ubo.id ASC
                    """
                ),
                {"eid": empresa_id},
            ).mappings()
        )

        beneficiarios = []
        for row in rows:
            beneficiarios.append(UboRecord(
                id=row["id"],
                empresa_id=row["empresa_id"],
                nombre_persona=row["nombre_persona"],
                nacionalidad=row["nacionalidad"],
                fecha_nacimiento=str(row["fecha_nacimiento"]) if row["fecha_nacimiento"] else None,
                pais_residencia=row["pais_residencia"],
                tipo_ubo=row["tipo_ubo"],
                porcentaje_control=float(row["porcentaje_control"]) if row["porcentaje_control"] else None,
                umbral_superado=row["umbral_superado"],
                vigencia_desde=str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
                vigencia_hasta=str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
                fuente=row["fuente"],
                fuente_ref=row["fuente_ref"],
                documento_referencia=row["documento_referencia"],
                nota=row["nota"],
            ))

        return UboRecordList(
            empresa_id=empresa_id,
            nombre=empresa["nombre"],
            beneficiarios=beneficiarios,
        )


# ---------------------------------------------------------------------------
# Grafo de control societario
# ---------------------------------------------------------------------------

@router.get(
    "/{empresa_id}/grafo",
    response_model=OwnershipGrafoResponse,
    operation_id="get_grafo_control",
)
async def get_grafo_control(
    empresa_id: int,
    profundidad: int = Query(default=2, ge=1, le=5, description="Profundidad de exploración del grafo (1-5)"),
):
    with db_session() as db:
        empresa = db.execute(
            text("SELECT id, nombre, nif FROM empresa WHERE id = :eid LIMIT 1"),
            {"eid": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id},
            )

        # Collect all nodes and edges within depth limit using recursive CTE
        rows = list(
            db.execute(
                text(
                    """
                    WITH RECURSIVE ownership_tree AS (
                        SELECT
                            e_orig.id as origen_id,
                            e_dest.id as destino_id,
                            or_.tipo_relacion,
                            or_.porcentaje,
                            0 as depth
                        FROM empresa e_orig
                        JOIN ownership_relation or_ ON or_.empresa_origen_id = e_orig.id
                        JOIN empresa e_dest ON e_dest.id = or_.empresa_destino_id
                        WHERE e_orig.id = :eid

                        UNION

                        SELECT
                            ot.origen_id,
                            e_dest.id as destino_id,
                            or_.tipo_relacion,
                            or_.porcentaje,
                            ot.depth + 1
                        FROM ownership_tree ot
                        JOIN ownership_relation or_ ON or_.empresa_origen_id = ot.destino_id
                        JOIN empresa e_dest ON e_dest.id = or_.empresa_destino_id
                        WHERE ot.depth < :depth
                    )
                    SELECT DISTINCT origen_id, destino_id, tipo_relacion, porcentaje
                    FROM ownership_tree
                    """
                ),
                {"eid": empresa_id, "depth": profundidad - 1},
            ).mappings()
        )

        # Collect all empresa IDs involved
        empresa_ids = {empresa_id}
        aristas = []
        for row in rows:
            empresa_ids.add(row["origen_id"])
            empresa_ids.add(row["destino_id"])
            aristas.append(OwnershipGrafoArista(
                origen_id=row["origen_id"],
                destino_id=row["destino_id"],
                tipo=row["tipo_relacion"],
                porcentaje=float(row["porcentaje"]) if row["porcentaje"] else None,
            ))

        # Fetch empresa details for all nodes
        empresas = {}
        for eid in empresa_ids:
            emp = db.execute(
                text("SELECT id, nombre, nif FROM empresa WHERE id = :eid LIMIT 1"),
                {"eid": eid},
            ).mappings().first()
            if emp:
                empresas[eid] = OwnershipGrafoNodo(
                    id=emp["id"],
                    nombre=emp["nombre"],
                    nif=emp["nif"],
                )

        # Calculate max depth
        max_depth = db.execute(
            text(
                """
                WITH RECURSIVE ownership_tree AS (
                    SELECT
                        e_orig.id as origen_id,
                        e_dest.id as destino_id,
                        0 as depth
                    FROM empresa e_orig
                    JOIN ownership_relation or_ ON or_.empresa_origen_id = e_orig.id
                    JOIN empresa e_dest ON e_dest.id = or_.empresa_destino_id
                    WHERE e_orig.id = :eid

                    UNION

                    SELECT
                        ot.origen_id,
                        e_dest.id as destino_id,
                        ot.depth + 1
                    FROM ownership_tree ot
                    JOIN ownership_relation or_ ON or_.empresa_origen_id = ot.destino_id
                    JOIN empresa e_dest ON e_dest.id = or_.empresa_destino_id
                    WHERE ot.depth < :depth
                )
                SELECT COALESCE(MAX(depth), 0) as max_depth FROM ownership_tree
                """
            ),
            {"eid": empresa_id, "depth": profundidad - 1},
        ).mappings().first()

        return OwnershipGrafoResponse(
            empresa_id=empresa_id,
            nombre=empresa["nombre"],
            profundidad=max_depth["max_depth"],
            nodos=list(empresas.values()),
            aristas=aristas,
        )


# ---------------------------------------------------------------------------
# Búsqueda con filtros de ownership
# ---------------------------------------------------------------------------

@router.get(
    "/buscar",
    response_model=OwnershipSearchResponse,
    operation_id="buscar_con_ownership",
)
async def buscar_con_ownership(
    q: str = Query(..., description="Término de búsqueda por nombre, NIF o denominación"),
    solo_con_participaciones: bool = Query(default=False, description="Solo empresas con participaciones registradas"),
    solo_con_ubos: bool = Query(default=False, description="Solo empresas con beneficiarios finales"),
):
    q_lower = q.lower().strip()

    with db_session() as db:
        base_query = """
            SELECT
                e.id,
                e.nombre,
                e.nif,
                COALESCE(os_count.c, 0) as participaciones_count,
                COALESCE(ubo_count.c, 0) as ubos_count
            FROM empresa e
            LEFT JOIN (
                SELECT empresa_id, COUNT(*) as c
                FROM ownership_share
                GROUP BY empresa_id
            ) os_count ON os_count.empresa_id = e.id
            LEFT JOIN (
                SELECT empresa_id, COUNT(*) as c
                FROM ubo_record
                GROUP BY empresa_id
            ) ubo_count ON ubo_count.empresa_id = e.id
            WHERE
                LOWER(e.nombre) LIKE :q_like
                OR LOWER(COALESCE(e.nif, '')) LIKE :q_like
        """

        params = {"q_like": f"%{q_lower}%"}

        if solo_con_participaciones:
            base_query += " AND os_count.c > 0"
        if solo_con_ubos:
            base_query += " AND ubo_count.c > 0"

        base_query += " ORDER BY e.nombre ASC LIMIT 50"

        rows = list(db.execute(text(base_query), params).mappings())

        resultados = []
        for row in rows:
            resultados.append(OwnershipSearchResult(
                id=row["id"],
                nombre=row["nombre"],
                nif=row["nif"],
                tiene_participaciones=row["participaciones_count"] > 0,
                tiene_ubos=row["ubos_count"] > 0,
                tiene_relaciones=False,  # se calcula en endpoint de detalle
                participaciones_count=row["participaciones_count"],
                ubos_count=row["ubos_count"],
            ))

        return OwnershipSearchResponse(q=q, resultados=resultados)
