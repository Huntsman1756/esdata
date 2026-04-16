from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import EmpresaDetail, EmpresasListResponse

router = APIRouter(prefix="/v1/empresas", tags=["empresas"])


@router.get("", response_model=EmpresasListResponse, operation_id="listar_empresas")
async def listar_empresas(
    q: str | None = Query(None, description="Filtrar por denominación o domicilio"),
):
    filters = ["1=1"]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(e.nombre) LIKE LOWER(:term) OR LOWER(COALESCE(e.domicilio, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    e.id,
                    e.nombre,
                    e.nif,
                    e.domicilio,
                    e.fuente_inicial,
                    COUNT(de.documento_id) AS documentos_count
                FROM empresa e
                LEFT JOIN documento_empresa de ON de.empresa_id = e.id
                WHERE {where_clause}
                GROUP BY e.id, e.nombre, e.nif, e.domicilio, e.fuente_inicial
                ORDER BY documentos_count DESC, e.nombre ASC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {"empresas": [dict(row) for row in rows]}


@router.get("/{empresa_id}", response_model=EmpresaDetail, operation_id="get_empresa")
async def get_empresa(empresa_id: int):
    with db_session() as db:
        empresa = (
            db.execute(
                text(
                    """
                    SELECT id, nombre, nif, domicilio, fuente_inicial
                    FROM empresa
                    WHERE id = :empresa_id
                    LIMIT 1
                    """
                ),
                {"empresa_id": empresa_id},
            )
            .mappings()
            .first()
        )

        if not empresa:
            raise HTTPException(status_code=404, detail={"error": "Empresa no encontrada"})

        documentos = list(
            db.execute(
                text(
                    """
                    SELECT
                        d.referencia,
                        d.organismo_emisor,
                        d.tipo_fuente,
                        d.tipo_documento,
                        d.fecha,
                        de.rol,
                        de.confianza_extraccion
                    FROM documento_empresa de
                    JOIN documento_interpretativo d ON d.id = de.documento_id
                    WHERE de.empresa_id = :empresa_id
                    ORDER BY d.fecha DESC, d.referencia DESC
                    """
                ),
                {"empresa_id": empresa_id},
            ).mappings()
        )

        return {
            **empresa,
            "documentos": [
                {
                    **dict(row),
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "confianza_extraccion": float(row["confianza_extraccion"]),
                }
                for row in documentos
            ],
        }
