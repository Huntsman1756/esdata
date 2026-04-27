"""Routers para CSDR (Reglamento UE 909/2014 sobre CSD).

Endpoints de consulta del Reglamento CSDR y sus articulos.
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    ArticuloDetail as ArticuloDetailSchema,
    ArticulosListResponse,
    Norma as NormaSchema,
    NormasListResponse,
)

router = APIRouter(prefix="/v1/csdr", tags=["csdr"])


@router.get("", operation_id="list_csdr", response_model=NormasListResponse)
async def list_csdr():
    """Listar normas CSDR."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, titulo, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                WHERE codigo LIKE 'CSDR_%'
                ORDER BY codigo
                """
            )
        ).mappings()
        return {"normas": list(rows)}


@router.get(
    "/micro-obligaciones",
    operation_id="list_csdr_micro_obligaciones",
)
async def list_csdr_micro_obligaciones():
    """Listar micro-obligaciones CSDR."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, descripcion, regulacion_relacionada,
                       ambito, trigger_evento, frecuencia, owner_rol, severidad, activo
                FROM micro_obligacion
                WHERE regulacion_relacionada = 'csdr'
                ORDER BY codigo ASC
                """
            )
        ).mappings()

        micro_obligaciones = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM micro_obligacion
                WHERE regulacion_relacionada = 'csdr'
                """
            )
        ).scalar()

        return {"micro_obligaciones": micro_obligaciones, "total": total}


@router.get("/{codigo}", operation_id="get_csdr_norma", response_model=NormaSchema)
async def get_csdr_norma(codigo: str):
    """Obtener detalle de una norma CSDR."""
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                    FROM norma
                    WHERE codigo = :codigo
                      AND codigo LIKE 'CSDR_%'
                    """
                ),
                {"codigo": codigo},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Norma CSDR no encontrada"})
        return dict(row)


@router.get("/{codigo}/articulos", operation_id="list_csdr_articulos", response_model=ArticulosListResponse,
            summary="Lista articulos de una norma CSDR")
async def list_csdr_articulos(codigo: str, tipo: str | None = Query(None, description="Filtrar por tipo de articulo")):
    """Listar articulos de una norma CSDR."""
    with db_session() as db:
        filters = ["n.codigo = :codigo"]
        params = {"codigo": codigo}

        if tipo is not None:
            filters.append("a.tipo = :tipo")
            params["tipo"] = tipo

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
                    status_code=404, detail={"error": "Norma CSDR no encontrada"}
                )
        return {"norma": codigo, "articulos": rows}


@router.get(
    "/{codigo}/articulos/{numero}",
    operation_id="get_csdr_articulo",
    response_model=ArticuloDetailSchema,
    summary="Detalle de un articulo CSDR",
)
async def get_csdr_articulo(codigo: str, numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    """Obtener detalle de un articulo CSDR."""
    with db_session() as db:
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
            raise HTTPException(status_code=404, detail={"error": "Articulo CSDR no encontrado"})
        return {
            "norma": row["codigo"],
            "numero": row["numero"],
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
            "confianza": {
                "nivel": 1,
                "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                "aviso": None,
            },
        }


@router.get(
    "/{codigo}/articulos/{numero}/historial",
    operation_id="get_csdr_articulo_historial",
)
async def get_csdr_articulo_historial(codigo: str, numero: str):
    """Historial de versiones de un articulo CSDR."""
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
            raise HTTPException(status_code=404, detail={"error": "Articulo CSDR no encontrado"})
        return {"norma": codigo, "numero": numero, "historial": historial}
