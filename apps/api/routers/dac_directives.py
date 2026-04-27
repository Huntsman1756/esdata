"""Router para Directivas DAC (DAC1-DAC9) y antifraude UE (Fase 28.1).

Endpoints para consultar las directivas de intercambio automatico de informacion fiscal.
"""

from __future__ import annotations

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    ArticuloListItem,
    ArticulosListResponse,
    NormasListResponse,
)
from schemas import (
    Norma as NormaSchema,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/dac", tags=["DAC directives"])


@router.get("/normas", response_model=NormasListResponse, operation_id="listar_normas_dac")
async def listar_normas(
    codigo: str | None = Query(None, description="Filtrar por codigo: DAC1, DAC6, etc."),
    estado: str = Query("activo", description="Estado: activo, inactivo, obsoleto"),
):
    """Listar directivas DAC."""
    filters = ["n.regulacion_relacionada = :reg"]
    params: dict = {"reg": "dac_directives"}

    if codigo:
        filters.append("n.codigo = :codigo")
        params["codigo"] = codigo

    if estado:
        filters.append("n.estado_cobertura = :estado")
        params["estado"] = estado

    with db_session() as db:
        where_clause = "WHERE " + " AND ".join(filters)
        rows = db.execute(
            text(
                f"""
                SELECT n.codigo, n.titulo, n.boe_id, n.eli_uri, n.jurisdiccion,
                       n.tipo_fuente, n.tipo_documento, n.ambito, n.estado_cobertura,
                       n.regulacion_relacionada
                FROM norma n
                {where_clause}
                ORDER BY n.vigente_desde DESC
                """
            ),
            params,
        ).mappings()

        items = [NormaSchema(**dict(row)).model_dump() for row in rows]

        total = db.execute(
            text(f"SELECT COUNT(*) FROM norma n {where_clause}"),
            params,
        ).scalar()

        return {"normas": items, "total": total}



@router.get(
    "/normas/{codigo}",
    response_model=NormaSchema,
    operation_id="detalle_norma_dac",
)
async def detalle_norma(codigo: str):
    """Detalle de una directiva DAC."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT n.codigo, n.titulo, n.boe_id, n.eli_uri, n.jurisdiccion,
                       n.tipo_fuente, n.tipo_documento, n.ambito, n.estado_cobertura,
                       n.regulacion_relacionada
                FROM norma n
                WHERE n.codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Norma DAC no encontrada: {codigo}",
            )

        return NormaSchema(**row)


@router.get("/articulos", response_model=ArticulosListResponse, operation_id="listar_articulos_dac")
async def listar_articulos(
    codigo_norma: str = Query("DAC6", description="Codigo de la norma DAC"),
    tipo: str | None = Query(None, description="Tipo: articulo, disposicion_adicional, etc."),
    vigente: bool = Query(True, description="Solo vigentes"),
):
    """Listar articulos de una directiva DAC."""
    filters = ["n.codigo = :codigo_norma"]
    params: dict = {"codigo_norma": codigo_norma}

    if tipo:
        filters.append("a.tipo = :tipo")
        params["tipo"] = tipo

    with db_session() as db:
        where_clause = "WHERE " + " AND ".join(filters)
        rows = db.execute(
            text(
                f"""
                SELECT a.numero, a.titulo, a.tipo
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                    AND va.vigente_desde = (
                        SELECT MAX(va2.vigente_desde)
                        FROM version_articulo va2
                        WHERE va2.articulo_id = a.id
                    )
                    {('AND (va.vigente_hasta IS NULL OR va.vigente_hasta > CURRENT_DATE)' if vigente else '')}
                {where_clause}
                ORDER BY CAST(a.numero AS INTEGER) ASC
                """
            ),
            params,
        ).mappings()

        items = [ArticuloListItem(**dict(row)).model_dump() for row in rows]

        total = db.execute(
            text(f"SELECT COUNT(*) FROM articulo a JOIN norma n ON n.id = a.norma_id {where_clause}"),
            params,
        ).scalar()

        return {"norma": codigo_norma, "articulos": items, "total": total}


@router.get(
    "/articulos/{articulo_id}",
    operation_id="detalle_articulo_dac",
)
async def detalle_articulo(articulo_id: int):
    """Detalle de un articulo de una directiva DAC."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT n.codigo, a.numero, a.titulo, va.texto, va.vigente_desde,
                       va.vigente_hasta, n.boe_id, n.eli_uri
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                    AND va.vigente_desde = (
                        SELECT MAX(va2.vigente_desde)
                        FROM version_articulo va2
                        WHERE va2.articulo_id = a.id
                    )
                WHERE a.id = :articulo_id
                """
            ),
            {"articulo_id": articulo_id},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Articulo DAC no encontrado: {articulo_id}",
            )

        return {
            "norma": row["codigo"],
            "numero": row["numero"],
            "titulo": row.get("titulo"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]) if row.get("vigente_desde") else None,
            "vigente_hasta": str(row["vigente_hasta"]) if row.get("vigente_hasta") else None,
            "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
            "confianza": {
                "nivel": 1,
                "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                "aviso": None,
            },
        }


@router.get(
    "/articulos/{articulo_id}/historial",
    operation_id="historial_articulo_dac",
)
async def historial_articulo(articulo_id: int):
    """Historial de versiones de un articulo DAC."""
    with db_session() as db:
        row = db.execute(
            text("SELECT n.codigo FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE a.id = :articulo_id"),
            {"articulo_id": articulo_id},
        ).mappings().first()

        codigo_norma = row["codigo"] if row else "DAC6"

        rows = db.execute(
            text(
                """
                SELECT a.numero, va.texto, va.vigente_desde, va.vigente_hasta
                FROM version_articulo va
                JOIN articulo a ON a.id = va.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE va.articulo_id = :articulo_id
                ORDER BY va.vigente_desde DESC
                """
            ),
            {"articulo_id": articulo_id},
        ).mappings()

        items = [
            {
                "numero": row["numero"],
                "vigente_desde": str(row["vigente_desde"]) if row.get("vigente_desde") else None,
                "vigente_hasta": str(row["vigente_hasta"]) if row.get("vigente_hasta") else None,
            }
            for row in rows
        ]

        if not items:
            raise HTTPException(
                status_code=404,
                detail=f"Articulo no encontrado: {articulo_id}",
            )

        return {"norma": codigo_norma, "articulos": items}
