from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import BORMEDetail, BORMEListResponse

router = APIRouter(prefix="/v1/borme", tags=["borme"])


@router.get("", response_model=BORMEListResponse, operation_id="listar_borme")
async def listar_borme(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tipo: str | None = Query(None, description="Filtrar por tipo de acto detectado"),
):
    filters = [
        "d.organismo_emisor = 'BORME'",
        "d.tipo_fuente = 'borme'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    if tipo:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, tipo_documento, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {
            "actos": [
                {
                    "referencia": row["referencia"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "titulo": row["titulo"],
                    "tipo_documento": row["tipo_documento"],
                    "fragmento": row["texto"][:220]
                    + ("..." if len(row["texto"]) > 220 else ""),
                    "url_fuente": row["url_fuente"],
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=BORMEDetail, operation_id="get_borme")
async def get_borme(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'BORME'
                      AND d.tipo_fuente = 'borme'
                      AND d.referencia = :referencia
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Acto BORME no encontrado"})

        empresas = list(
            db.execute(
                text(
                    """
                    SELECT e.id, e.nombre, de.rol, de.confianza_extraccion
                    FROM documento_empresa de
                    JOIN documento_interpretativo d ON d.id = de.documento_id
                    JOIN empresa e ON e.id = de.empresa_id
                    WHERE d.referencia = :referencia
                    ORDER BY de.confianza_extraccion DESC, e.nombre ASC
                    """
                ),
                {"referencia": referencia},
            ).mappings()
        )

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "empresas_relacionadas": [
                {
                    "id": item["id"],
                    "nombre": item["nombre"],
                    "rol": item["rol"],
                    "confianza_extraccion": float(item["confianza_extraccion"]),
                }
                for item in empresas
            ],
        }
