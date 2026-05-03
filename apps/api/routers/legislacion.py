from db import db_session
from fastapi import APIRouter, HTTPException, Request
from services.query_audit import get_query_audit_service
from sqlalchemy import text

router = APIRouter(prefix="/v1/legislacion", tags=["legislacion"])


def _record_legislacion_query_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    retrieved_chunks: list[dict],
    response_summary: str,
    confidence: dict | None = None,
    completeness: str = "completa",
    verified: bool = True,
):
    get_query_audit_service().record_query(
        request_id=request.headers.get("x-request-id")
        or request.headers.get("X-Request-ID")
        or "unknown",
        user_id=request.headers.get("x-user-id") or request.headers.get("X-User-ID"),
        path=path,
        query_text=query_text,
        retrieved_chunks=retrieved_chunks,
        response_summary=response_summary,
        tool_name=tool_name,
        confidence=confidence,
        completeness=completeness,
        verified=verified,
    )


@router.get("", operation_id="list_legislacion")
async def list_legislacion():
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, titulo, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                ORDER BY codigo
                """
            )
        ).mappings()
    return {"normas": list(rows)}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de artículos y versiones por norma para verificar ingesta."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    n.codigo,
                    n.titulo,
                    COUNT(DISTINCT a.id) AS articulos,
                    COUNT(va.id) AS versiones,
                    MAX(va.vigente_desde) AS ultima_version
                FROM norma n
                LEFT JOIN articulo a ON a.norma_id = n.id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                GROUP BY n.id, n.codigo, n.titulo
                ORDER BY n.codigo
                """
            )
        ).mappings()
    return {
        "normas": [
            {
                "codigo": row["codigo"],
                "titulo": row["titulo"],
                "articulos": row["articulos"],
                "versiones": row["versiones"],
                "ultima_version": str(row["ultima_version"])
                if row["ultima_version"]
                else None,
            }
            for row in rows
        ]
    }


@router.get("/{codigo}", operation_id="get_norma")
async def get_norma(request: Request, codigo: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                WHERE codigo = :codigo
                """
                ),
                {"codigo": codigo},
            )
            .mappings()
            .first()
        )
    if not row:
        raise HTTPException(status_code=404, detail={"error": "Norma no encontrada"})
    payload = dict(row)
    _record_legislacion_query_audit(
        request,
        path=f"/v1/legislacion/{codigo}",
        query_text=codigo,
        tool_name="get_norma",
        retrieved_chunks=[
            {
                "norma": payload["codigo"],
                "title": payload["titulo"],
                "source_url": payload.get("eli_uri"),
                "referencia": payload.get("boe_id"),
            }
        ],
        response_summary=f"norma={payload['codigo']}",
        confidence={"score": 0.9, "label": "alta"},
    )
    return payload


@router.get("/{codigo}/articulos", operation_id="list_articulos")
async def list_articulos(request: Request, codigo: str, tipo: str | None = None):
    filters = ["n.codigo = :codigo"]
    params = {"codigo": codigo}

    if tipo is not None:
        filters.append("a.tipo = :tipo")
        params["tipo"] = tipo

    with db_session() as db:
        rows = list(
            db.execute(
                text(
                    """
                    SELECT a.numero, a.titulo, a.tipo
                    FROM norma n
                    JOIN articulo a ON a.norma_id = n.id
                    WHERE {where_clause}
                    ORDER BY a.numero
                    """.format(where_clause=" AND ".join(filters))
                ),
                params,
            ).mappings()
        )
        if not rows:
            existe_norma = db.execute(
                text("SELECT 1 FROM norma WHERE codigo = :codigo"),
                {"codigo": codigo},
            ).first()
            if not existe_norma:
                raise HTTPException(
                    status_code=404, detail={"error": "Norma no encontrada"}
                )
    payload = {"norma": codigo, "articulos": rows}
    _record_legislacion_query_audit(
        request,
        path=f"/v1/legislacion/{codigo}/articulos",
        query_text=codigo if tipo is None else f"{codigo}:{tipo}",
        tool_name="list_articulos",
        retrieved_chunks=[
            {
                "norma": codigo,
                "numero": row["numero"],
                "title": row.get("titulo"),
            }
            for row in rows
        ],
        response_summary=f"articulos={len(rows)}",
        confidence={"score": 0.9 if rows else 0.0, "label": "alta" if rows else "baja"},
        verified=bool(rows),
    )
    return payload


@router.get("/{codigo}/articulos/{numero}", operation_id="get_articulo")
async def get_articulo(request: Request, codigo: str, numero: str, vigente_en: str | None = None):
    filters = ["n.codigo = :codigo", "a.numero = :numero"]
    params = {"codigo": codigo, "numero": numero}

    if vigente_en is not None:
        filters.append(
            """
            va.vigente_desde <= :vigente_en
            AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en)
            """
        )
        params["vigente_en"] = vigente_en

    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                SELECT n.codigo, a.numero, va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE {where_clause}
                ORDER BY va.vigente_desde DESC
                LIMIT 1
                """.format(where_clause=" AND ".join(filters))
                ),
                params,
            )
            .mappings()
            .first()
        )
    if not row:
        raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})
    payload = {
        "norma": row["codigo"],
        "numero": row["numero"],
        "texto": row["texto"],
        "vigente_desde": str(row["vigente_desde"]),
        "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
        "confianza": {
            "nivel": 1,
            "fuentes": [f"{row['codigo']} art. {row['numero']}"],
            "aviso": None,
        },
    }
    _record_legislacion_query_audit(
        request,
        path=f"/v1/legislacion/{codigo}/articulos/{numero}",
        query_text=f"{codigo}:{numero}",
        tool_name="get_articulo",
        retrieved_chunks=[
            {
                "norma": row["codigo"],
                "numero": row["numero"],
                "title": f"Articulo {row['numero']}",
                "content_preview": row["texto"][:220],
            }
        ],
        response_summary=f"articulo={row['codigo']}:{row['numero']}",
        confidence={"score": 0.9, "label": "alta"},
    )
    return payload


@router.get(
    "/{codigo}/articulos/{numero}/historial", operation_id="get_articulo_historial"
)
async def get_articulo_historial(request: Request, codigo: str, numero: str):
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = :codigo AND a.numero = :numero
                ORDER BY va.vigente_desde DESC
                """
            ),
            {"codigo": codigo, "numero": numero},
        ).mappings()
        historial = [
            {
                "texto": row["texto"],
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"])
                if row["vigente_hasta"]
                else None,
            }
            for row in rows
        ]
    if not historial:
        raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})
    payload = {"norma": codigo, "numero": numero, "historial": historial}
    _record_legislacion_query_audit(
        request,
        path=f"/v1/legislacion/{codigo}/articulos/{numero}/historial",
        query_text=f"{codigo}:{numero}",
        tool_name="get_articulo_historial",
        retrieved_chunks=[
            {
                "norma": codigo,
                "numero": numero,
                "title": f"Historial articulo {numero}",
                "content_preview": item["texto"][:220],
            }
            for item in historial
        ],
        response_summary=f"historial={len(historial)}",
        confidence={"score": 0.9, "label": "alta"},
    )
    return payload
