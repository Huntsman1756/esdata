from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import DocInterpretativoDetail, DocInterpretativoListResponse
from sqlalchemy import text

router = APIRouter(prefix="/v1/cendoj", tags=["cendoj"])


def _normalize_tipo_documento(value: str | None) -> str | None:
    if value == "sentencia_ts":
        return "sentencia"
    return value


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_cendoj")
async def listar_cendoj(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tribunal: str | None = Query(None, description="Filtrar por tribunal (tribunal_supremo, audiencia_nacional, tsj)"),
    tipo: str | None = Query(None, description="Filtrar por tipo de documento (sentencia, auto, providencia)"),
    organismo: str | None = Query(None, description="Filtrar por organismo emisor"),
):
    filters = [
        "d.tipo_fuente = 'cendoj'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    if tribunal:
        filters.append("LOWER(COALESCE(d.organismo_emisor, '')) LIKE LOWER(:court_term)")
        params["court_term"] = f"%{tribunal.replace('_', ' ')}%"

    if tipo:
        if tipo == "sentencia":
            filters.append("d.tipo_documento IN ('sentencia', 'sentencia_ts')")
        else:
            filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo

    if organismo:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo)")
        params["organismo"] = organismo

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente, organismo_emisor
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
                    "tipo_documento": _normalize_tipo_documento(row["tipo_documento"]),
                    "ambito": row["ambito"],
                    "fragmento": row["texto"][:220]
                    + ("..." if len(row["texto"]) > 220 else ""),
                    "url_fuente": row["url_fuente"],
                    "organismo_emisor": row.get("organismo_emisor"),
                }
                for row in rows
            ]
        }


@router.get("/{referencia:path}", response_model=DocInterpretativoDetail, operation_id="get_cendoj")
async def get_cendoj(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente, organismo_emisor
                    FROM documento_interpretativo d
                    WHERE d.tipo_fuente = 'cendoj'
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
            raise HTTPException(status_code=404, detail={"error": "Documento CENDOJ no encontrado"})

        return {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": _normalize_tipo_documento(row["tipo_documento"]),
            "ambito": row["ambito"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "organismo_emisor": row.get("organismo_emisor"),
        }
