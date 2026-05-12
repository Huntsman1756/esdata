from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from request_context import get_request_id, get_user_id
from schemas import ArticulosListResponse
from services.query_audit import get_query_audit_service
from sqlalchemy import text

router = APIRouter(prefix="/v1/legislacion", tags=["legislacion"])


def _boe_source_url(boe_id: str | None, anchor: str | None = None) -> str | None:
    if not boe_id:
        return None
    base_url = f"https://www.boe.es/buscar/act.php?id={boe_id}"
    return f"{base_url}#{anchor}" if anchor else base_url


def _article_anchor(numero: str) -> str:
    normalized = "".join(ch for ch in str(numero) if ch.isalnum()).lower()
    return f"a{normalized}"


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
        request_id=get_request_id(request),
        user_id=get_user_id(request),
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
async def list_legislacion(
    limit: int = Query(200, ge=1, le=500, description="Tamano de pagina aplicado"),
    offset: int = Query(0, ge=0, description="Offset de resultados"),
):
    with db_session() as db:
        total = int(db.execute(text("SELECT COUNT(*) FROM norma")).scalar() or 0)
        rows = db.execute(
            text(
                """
                SELECT codigo, titulo, jurisdiccion, tipo_fuente, tipo_documento, ambito,
                       estado_cobertura, boe_id, eli_uri
                FROM norma
                ORDER BY codigo
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": limit, "offset": offset},
        ).mappings()
    # Enrich each norma with per-item provenance (boe_reference + eli_uri)
    # so consumers don't need to round-trip to /{codigo} for citation data.
    result = []
    for row in rows:
        item = dict(row)
        boe_id = item.get("boe_id")
        item["boe_reference"] = boe_id
        item["source_url"] = _boe_source_url(boe_id)
        result.append(item)
    has_more = offset + len(result) < total
    return {
        "normas": result,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + len(result) if has_more else None,
    }


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
                SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
                       tipo_documento, ambito, estado_cobertura, vigente_desde
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
    boe_id = payload.get("boe_id")
    payload["boe_reference"] = boe_id
    payload["source_url"] = _boe_source_url(boe_id)
    payload["vigente_desde"] = (
        str(payload["vigente_desde"]) if payload.get("vigente_desde") else None
    )
    _record_legislacion_query_audit(
        request,
        path=f"/v1/legislacion/{codigo}",
        query_text=codigo,
        tool_name="get_norma",
        retrieved_chunks=[
            {
                "norma": payload["codigo"],
                "title": payload["titulo"],
                "source_url": payload.get("source_url") or payload.get("eli_uri"),
                "referencia": payload.get("boe_reference"),
            }
        ],
        response_summary=f"norma={payload['codigo']}",
        confidence={"score": 0.9, "label": "alta"},
    )
    return payload


@router.get("/{codigo}/articulos", operation_id="list_articulos", response_model=ArticulosListResponse)
async def list_articulos(
    request: Request,
    codigo: str,
    tipo: str | None = None,
    limit: int = Query(200, ge=1, le=500, description="Tamano de pagina aplicado"),
    offset: int = Query(0, ge=0, description="Offset de resultados"),
):
    filters = ["n.codigo = :codigo"]
    params = {"codigo": codigo}

    if tipo is not None:
        filters.append("a.tipo = :tipo")
        params["tipo"] = tipo

    with db_session() as db:
        total_row = db.execute(
            text(
                """
                SELECT COUNT(*) AS total
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings().first()
        total = int(total_row["total"]) if total_row else 0
        rows = list(
            db.execute(
                text(
                    """
                    SELECT a.numero, a.titulo, a.tipo, n.boe_id, n.eli_uri, n.codigo AS norma_codigo
                    FROM norma n
                    JOIN articulo a ON a.norma_id = n.id
                    WHERE {where_clause}
                    ORDER BY a.numero
                    LIMIT :limit OFFSET :offset
                    """.format(where_clause=" AND ".join(filters))
                ),
                {**params, "limit": limit, "offset": offset},
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
    # Enrich each article row with provenance fields derived from the parent
    # norma so consumers can cite articles directly without fetching norma.
    articulos = []
    for row in rows:
        boe_id = row["boe_id"]
        source_url = _boe_source_url(boe_id, _article_anchor(row["numero"]))
        articulos.append({
            "numero": row["numero"],
            "titulo": row["titulo"],
            "tipo": row["tipo"],
            "boe_reference": boe_id,
            "source_url": source_url,
            "eli_uri": row["eli_uri"],
        })
    has_more = offset + len(articulos) < total
    payload = {
        "norma": codigo,
        "articulos": articulos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + len(articulos) if has_more else None,
    }
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
        response_summary=f"articulos={len(rows)}/{total}",
        confidence={"score": 0.9 if total else 0.0, "label": "alta" if total else "baja"},
        verified=bool(total),
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
                SELECT n.codigo, a.numero, va.texto, va.vigente_desde, va.vigente_hasta,
                       n.boe_id, n.eli_uri
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

    # Build traceability fields to BOE (S-16 compliance).
    boe_id = row["boe_id"]
    # Deep-link to the specific article within the consolidated norma on boe.es.
    # BOE uses `#a<numero>` anchors for each article in the consolidated text.
    source_url = _boe_source_url(boe_id, _article_anchor(row["numero"]))

    payload = {
        "norma": row["codigo"],
        "numero": row["numero"],
        "texto": row["texto"],
        "vigente_desde": str(row["vigente_desde"]),
        "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
        "boe_reference": boe_id,
        "source_url": source_url,
        "eli_uri": row["eli_uri"],
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
                SELECT a.numero, va.texto, va.vigente_desde, va.vigente_hasta,
                       n.boe_id, n.eli_uri
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
                "boe_reference": row["boe_id"],
                "source_url": _boe_source_url(
                    row["boe_id"], _article_anchor(row["numero"])
                ),
                "eli_uri": row["eli_uri"],
            }
            for row in rows
        ]
    if not historial:
        raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})
    first_item = historial[0]
    payload = {
        "norma": codigo,
        "numero": numero,
        "boe_reference": first_item.get("boe_reference"),
        "source_url": first_item.get("source_url"),
        "eli_uri": first_item.get("eli_uri"),
        "historial": historial,
    }
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
