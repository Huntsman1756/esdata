from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import DocInterpretativoDetail, DocInterpretativoListResponse
from sqlalchemy import text

router = APIRouter(prefix="/v1/aepd", tags=["aepd"])


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_aepd")
async def listar_aepd(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tipo: str | None = Query(None, description="Filtrar por tipo (guia_aepd, resolucion_aepd, instruccion_aepd)"),
    ambito: str | None = Query(None, description="Filtrar por ámbito (proteccion_datos, derechos_ar, ficheros_datos, cookies)"),
):
    filters = [
        "d.tipo_fuente = 'aepd'",
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

    if ambito:
        filters.append("d.ambito = :ambito")
        params["ambito"] = ambito

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {
            "documentos": [
                {
                    "referencia": row["referencia"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "titulo": row["titulo"],
                    "tipo_documento": row["tipo_documento"],
                    "ambito": row["ambito"],
                    "fragmento": row["texto"][:220]
                    + ("..." if len(row["texto"]) > 220 else ""),
                    "url_fuente": row["url_fuente"],
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=DocInterpretativoDetail, operation_id="get_aepd")
async def get_aepd(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.tipo_fuente = 'aepd'
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
            raise HTTPException(status_code=404, detail={"error": "Documento AEPD no encontrado"})

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
        }
