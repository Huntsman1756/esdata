import re
import unicodedata

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import DocInterpretativoDetail, DocInterpretativoListResponse
from sqlalchemy import text

router = APIRouter(prefix="/v1/aepd", tags=["aepd"])

_NORMALIZED_DOC_EXPR = (
    "translate(LOWER(COALESCE(d.texto, '') || ' ' || COALESCE(d.titulo, '')), "
    ":accent_src, :accent_dst)"
)
_LOWER_DOC_EXPR = "LOWER(COALESCE(d.texto, '') || ' ' || COALESCE(d.titulo, ''))"
_ACCENT_SRC = "".join(
    chr(codepoint)
    for codepoint in [
        0x00E1,
        0x00E0,
        0x00E4,
        0x00E2,
        0x00E9,
        0x00E8,
        0x00EB,
        0x00EA,
        0x00ED,
        0x00EC,
        0x00EF,
        0x00EE,
        0x00F3,
        0x00F2,
        0x00F6,
        0x00F4,
        0x00FA,
        0x00F9,
        0x00FC,
        0x00FB,
        0x00F1,
        0x00E7,
    ]
)
_ACCENT_DST = "aaaaeeeeiiiioooouuuunc"


def _fragment(text_value: str) -> str:
    return text_value[:220] + ("..." if len(text_value) > 220 else "")


def _normalize_search_terms(q: str) -> list[str]:
    without_accents = unicodedata.normalize("NFKD", q).encode("ascii", "ignore").decode("ascii")
    return [term.lower() for term in re.findall(r"[a-zA-Z0-9]+", without_accents) if len(term) >= 2]


def _doc_search_expr(db) -> str:
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    if getattr(dialect, "name", "") == "sqlite":
        return _LOWER_DOC_EXPR
    return _NORMALIZED_DOC_EXPR


async def _listar_aepd_response(
    *,
    q: str | None,
    tipo: str | None,
    ambito: str | None,
    limit: int,
    offset: int,
):
    filters = ["d.tipo_fuente = 'aepd'"]
    params: dict[str, str | int] = {"limit": limit, "offset": offset}

    if tipo:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo

    if ambito:
        filters.append("d.ambito = :ambito")
        params["ambito"] = ambito

    with db_session() as db:
        if q:
            terms = _normalize_search_terms(q)
            if not terms:
                terms = [q.lower()]
            search_expr = _doc_search_expr(db)
            if search_expr == _NORMALIZED_DOC_EXPR:
                params["accent_src"] = _ACCENT_SRC
                params["accent_dst"] = _ACCENT_DST
            for idx, term in enumerate(terms):
                key = f"term_{idx}"
                filters.append(f"{search_expr} LIKE :{key}")
                params[key] = f"%{term}%"

        where_clause = " AND ".join(filters)
        count_params = {key: value for key, value in params.items() if key not in {"limit", "offset"}}
        rows = db.execute(
            text(
                f"""
                SELECT referencia, fecha, titulo, tipo_documento, ambito, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()

        total = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM documento_interpretativo d
                WHERE {where_clause}
                """
            ),
            count_params,
        ).scalar_one()

    documentos = [
        {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "tipo_documento": row["tipo_documento"],
            "ambito": row["ambito"],
            "fragmento": _fragment(row["texto"]),
            "url_fuente": row["url_fuente"],
            "url_aepd": row["url_fuente"],
        }
        for row in rows
    ]
    has_more = offset + len(documentos) < total
    return {
        "documentos": documentos,
        "items": documentos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "skip": offset,
        "has_more": has_more,
        "next_offset": offset + limit if has_more else None,
    }


@router.get("", response_model=DocInterpretativoListResponse, operation_id="listar_aepd")
async def listar_aepd(
    q: str | None = Query(None, description="Filtrar por texto o titulo"),
    tipo: str | None = Query(None, description="Filtrar por tipo (guia_aepd, resolucion_aepd, instruccion_aepd)"),
    ambito: str | None = Query(None, description="Filtrar por ambito (proteccion_datos, derechos_ar, ficheros_datos, cookies)"),
    limit: int = Query(20, ge=1, le=100, description="Limite de documentos devueltos"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    return await _listar_aepd_response(q=q, tipo=tipo, ambito=ambito, limit=limit, offset=offset)


@router.get("/buscar", response_model=DocInterpretativoListResponse, operation_id="buscar_aepd")
async def buscar_aepd(
    q: str = Query(..., min_length=1, description="Filtrar por texto o titulo"),
    tipo: str | None = Query(None, description="Filtrar por tipo"),
    ambito: str | None = Query(None, description="Filtrar por ambito"),
    limit: int = Query(20, ge=1, le=100, description="Limite de documentos devueltos"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    return await _listar_aepd_response(q=q, tipo=tipo, ambito=ambito, limit=limit, offset=offset)


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
        "url_aepd": row["url_fuente"],
    }
