from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import EurLexDetail, EurLexListResponse
from sqlalchemy import text

router = APIRouter(prefix="/v1/eurlex", tags=["eurlex"])

# EUR-Lex normas se almacenan en `norma + articulo + version_articulo`
# (no en `documento_interpretativo`). El worker apps/workers/eurlex.py
# escribe con `tipo_fuente='eurlex'` y CELEX como `codigo`/`boe_id`.


@router.get("", response_model=EurLexListResponse, operation_id="listar_eurlex")
async def listar_eurlex(
    q: str | None = Query(None, description="Filtrar por texto o título"),
    tipo: str | None = Query(None, description="Filtrar por tipo (directiva, reglamento, decision)"),
    ambito: str | None = Query(
        None,
        description="Filtrar por ámbito (fiscal_ue, mercado_interior, competencia_ue, ...)",
    ),
    limit: int = Query(20, ge=1, le=100, description="Limite de documentos devueltos"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["n.tipo_fuente = 'eurlex'"]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "("
            "LOWER(COALESCE(n.titulo, '')) LIKE LOWER(:term) "
            "OR EXISTS ("
            "  SELECT 1 FROM articulo a "
            "  JOIN version_articulo va ON va.articulo_id = a.id "
            "  WHERE a.norma_id = n.id "
            "    AND va.vigente_hasta IS NULL "
            "    AND LOWER(va.texto) LIKE LOWER(:term)"
            ")"
            ")"
        )
        params["term"] = f"%{q}%"

    if tipo:
        filters.append("n.tipo_documento = :tipo")
        params["tipo"] = tipo

    if ambito:
        filters.append("n.ambito = :ambito")
        params["ambito"] = ambito

    where_clause = " AND ".join(filters)

    sql = f"""
        SELECT
            n.codigo                              AS referencia,
            n.vigente_desde                       AS fecha,
            n.titulo                              AS titulo,
            n.tipo_documento                      AS tipo_documento,
            n.ambito                              AS ambito,
            n.eli_uri                             AS url_fuente,
            (
                SELECT va.texto
                FROM version_articulo va
                JOIN articulo a ON a.id = va.articulo_id
                WHERE a.norma_id = n.id
                  AND va.vigente_hasta IS NULL
                ORDER BY a.id ASC
                LIMIT 1
            )                                     AS primer_texto
        FROM norma n
        WHERE {where_clause}
        ORDER BY n.vigente_desde DESC, n.codigo DESC
        LIMIT :limit OFFSET :offset
    """

    with db_session() as db:
        rows = db.execute(text(sql), {**params, "limit": limit, "offset": offset}).mappings().all()
        total = db.execute(
            text(f"SELECT COUNT(*) FROM norma n WHERE {where_clause}"),
            params,
        ).scalar()

    documentos = []
    for row in rows:
        primer = row["primer_texto"] or ""
        fragmento = primer[:220] + ("..." if len(primer) > 220 else "")
        documentos.append(
            {
                "referencia": row["referencia"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "tipo_documento": row["tipo_documento"],
                "ambito": row["ambito"],
                "fragmento": fragmento,
                "url_fuente": row["url_fuente"],
            }
        )
    next_offset = offset + limit if offset + len(documentos) < int(total or 0) else None
    return {
        "documentos": documentos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": next_offset is not None,
        "next_offset": next_offset,
    }


@router.get("/{referencia:path}", response_model=EurLexDetail, operation_id="get_eurlex")
async def get_eurlex(referencia: str):
    with db_session() as db:
        norma_row = (
            db.execute(
                text(
                    """
                    SELECT id, codigo, vigente_desde, titulo, tipo_documento, ambito, eli_uri
                    FROM norma
                    WHERE tipo_fuente = 'eurlex'
                      AND codigo = :referencia
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )

        if not norma_row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Documento EUR-Lex no encontrado"},
            )

        articulos = (
            db.execute(
                text(
                    """
                    SELECT va.texto
                    FROM articulo a
                    JOIN version_articulo va ON va.articulo_id = a.id
                    WHERE a.norma_id = :norma_id
                      AND va.vigente_hasta IS NULL
                    ORDER BY a.id ASC
                    """
                ),
                {"norma_id": norma_row["id"]},
            )
            .mappings()
            .all()
        )

    texto_completo = "\n\n".join(r["texto"] for r in articulos if r["texto"])

    return {
        "referencia": norma_row["codigo"],
        "fecha": str(norma_row["vigente_desde"]) if norma_row["vigente_desde"] else None,
        "titulo": norma_row["titulo"],
        "tipo_documento": norma_row["tipo_documento"],
        "ambito": norma_row["ambito"],
        "texto": texto_completo,
        "url_fuente": norma_row["eli_uri"],
    }
