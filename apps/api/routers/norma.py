from __future__ import annotations

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from mcp_tools_eu import BUSCAR_NORMA_EU, TipoNormaEu, buscar_norma_eu
from sqlalchemy import text


router = APIRouter(prefix="/v1/norma", tags=["norma", "eu"])


NORMA_EU_DESCRIPTION = BUSCAR_NORMA_EU.description


@router.get(
    "/eu",
    operation_id="buscar_norma_eu",
    summary="Busca normas UE cargadas",
    description=NORMA_EU_DESCRIPTION,
)
async def list_normas_eu(
    termino: str = Query("", description="Keyword, CELEX, or regulation name."),
    tipo_norma: TipoNormaEu | None = Query(None),
):
    with db_session() as db:
        return [
            item.model_dump(mode="json")
            for item in buscar_norma_eu(db, termino=termino, tipo_norma=tipo_norma)
        ]


@router.get(
    "/{codigo}",
    operation_id="get_norma_eu",
    summary="Detalle de norma UE por codigo o CELEX",
    description=NORMA_EU_DESCRIPTION,
)
async def get_norma(codigo: str):
    with db_session() as db:
        norma = db.execute(
            text(
                """
                SELECT
                    codigo,
                    celex,
                    titulo,
                    tipo_norma,
                    CAST(publicacion_doue AS TEXT) AS publicacion_doue,
                    url_eurlex,
                    vigente,
                    derogada_por,
                    boe_id,
                    eli_uri,
                    jurisdiccion,
                    tipo_fuente,
                    tipo_documento,
                    ambito,
                    estado_cobertura,
                    CAST(vigente_desde AS TEXT) AS vigente_desde
                FROM norma
                WHERE codigo = :codigo
                   OR celex = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()
        if norma is None:
            raise HTTPException(status_code=404, detail=f"Norma no encontrada: {codigo}")

        obligaciones = db.execute(
            text(
                """
                SELECT
                    id,
                    perfil_codigo,
                    obligacion_tipo,
                    descripcion,
                    periodicidad,
                    articulo_referencia,
                    verified,
                    completeness,
                    source_url
                FROM obligacion_perfil
                WHERE norma_codigo = :codigo
                ORDER BY perfil_codigo, obligacion_tipo, descripcion
                """
            ),
            {"codigo": norma["codigo"]},
        ).mappings().all()

    return {
        **dict(norma),
        "obligaciones_referenciadas": [dict(row) for row in obligaciones],
    }
