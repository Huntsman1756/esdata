from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import JurisprudenciaDetail, JurisprudenciaSearchResponse
from sqlalchemy import text

router = APIRouter(prefix="/v1/jurisprudencia", tags=["jurisprudencia"])


def _build_fragmento(row, q: str) -> str:
    q_lower = q.lower()
    titulo = row["titulo"] or ""
    referencia = row["referencia"] or ""
    texto = row["texto"] or ""

    if q_lower in titulo.lower():
        return titulo
    if q_lower in referencia.lower():
        return referencia
    return texto[:300]


@router.get(
    "/buscar",
    operation_id="buscar_jurisprudencia",
    response_model=JurisprudenciaSearchResponse,
    summary="Buscar jurisprudencia tributaria",
)
async def buscar_jurisprudencia(
    q: str = Query(
        ..., min_length=1, description="Termino de busqueda en jurisprudencia"
    ),
):
    params = {"q": f"%{q}%"}

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    di.referencia,
                    di.tipo_documento,
                    di.organismo_emisor,
                    di.fecha,
                    di.titulo,
                    di.texto,
                    MAX(da.confianza_enlace) AS nivel_enlace
                FROM documento_interpretativo di
                LEFT JOIN documento_articulo da ON da.documento_id = di.id
                WHERE di.tipo_documento LIKE 'sentencia_%'
                  AND (
                      LOWER(COALESCE(di.texto, '')) LIKE LOWER(:q)
                      OR LOWER(COALESCE(di.titulo, '')) LIKE LOWER(:q)
                      OR LOWER(di.referencia) LIKE LOWER(:q)
                  )
                GROUP BY di.id, di.referencia, di.tipo_documento, di.organismo_emisor,
                         di.fecha, di.titulo, di.texto
                ORDER BY di.fecha DESC
                LIMIT 30
                """
            ),
            params,
        ).mappings()

        resultados = []
        for row in rows:
            link = (
                db.execute(
                    text(
                        """
                        SELECT
                            n.codigo AS norma,
                            a.numero
                        FROM documento_articulo da
                        JOIN articulo a ON a.id = da.articulo_id
                        JOIN norma n ON n.id = a.norma_id
                        WHERE da.documento_id = (
                            SELECT id FROM documento_interpretativo WHERE referencia = :referencia
                        )
                        ORDER BY da.confianza_enlace DESC, n.codigo, a.numero
                        LIMIT 1
                        """
                    ),
                    {"referencia": row["referencia"]},
                )
                .mappings()
                .first()
            )
            resultados.append(
                {
                    "referencia": row["referencia"],
                    "tipo_documento": row["tipo_documento"],
                    "organismo_emisor": row["organismo_emisor"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "titulo": row["titulo"],
                    "nivel_enlace": float(row["nivel_enlace"] or 0),
                    "norma": link["norma"] if link else None,
                    "numero": link["numero"] if link else None,
                    "fragmento": _build_fragmento(row, q),
                }
            )

    return {
        "q": q,
        "resultados": resultados,
    }


@router.get(
    "/{referencia:path}",
    operation_id="get_jurisprudencia",
    response_model=JurisprudenciaDetail,
)
async def get_jurisprudencia(referencia: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT
                        d.id,
                        d.referencia,
                        d.tipo_documento,
                        d.organismo_emisor,
                        d.jurisdiccion,
                        d.fecha,
                        d.titulo,
                        d.texto,
                        d.url_fuente
                    FROM documento_interpretativo d
                    WHERE d.referencia = :referencia
                      AND d.tipo_documento LIKE 'sentencia_%'
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404, detail={"error": "Documento no encontrado"}
            )

        articulos = list(
            db.execute(
                text(
                    """
                    SELECT
                        n.codigo AS norma,
                        a.numero,
                        a.titulo,
                        da.metodo_enlace,
                        da.confianza_enlace,
                        da.nota
                    FROM documento_articulo da
                    JOIN articulo a ON a.id = da.articulo_id
                    JOIN norma n ON n.id = a.norma_id
                    WHERE da.documento_id = :documento_id
                    ORDER BY da.confianza_enlace DESC, n.codigo, a.numero
                    """
                ),
                {"documento_id": row["id"]},
            ).mappings()
        )

        doctrina_rows = list(
            db.execute(
                text(
                    """
                    SELECT DISTINCT
                        di2.referencia,
                        di2.organismo_emisor,
                        di2.fecha,
                        n.codigo AS norma,
                        a.numero
                    FROM documento_articulo da1
                    JOIN documento_articulo da2 ON da2.articulo_id = da1.articulo_id
                    JOIN documento_interpretativo di2 ON di2.id = da2.documento_id
                    JOIN articulo a ON a.id = da2.articulo_id
                    JOIN norma n ON n.id = a.norma_id
                    WHERE da1.documento_id = :documento_id
                      AND da2.documento_id != :documento_id
                      AND di2.tipo_documento IN ('consulta_vinculante', 'resolucion_teac')
                    ORDER BY di2.fecha DESC, di2.referencia
                    """
                ),
                {"documento_id": row["id"]},
            ).mappings()
        )

    doctrina_map = {}
    for item in doctrina_rows:
        ref = item["referencia"]
        if ref not in doctrina_map:
            doctrina_map[ref] = {
                "referencia": ref,
                "organismo_emisor": item["organismo_emisor"],
                "fecha": str(item["fecha"]) if item["fecha"] else None,
                "via_articulos": [],
            }
        doctrina_map[ref]["via_articulos"].append(
            {"norma": item["norma"], "numero": item["numero"]}
        )

    return {
        "referencia": row["referencia"],
        "tipo_documento": row["tipo_documento"],
        "organismo_emisor": row["organismo_emisor"],
        "jurisdiccion": row["jurisdiccion"],
        "fecha": str(row["fecha"]) if row["fecha"] else None,
        "titulo": row["titulo"],
        "texto": row["texto"],
        "url_fuente": row["url_fuente"],
        "articulos": [
            {
                "norma": item["norma"],
                "numero": item["numero"],
                "titulo": item["titulo"],
                "metodo_enlace": item["metodo_enlace"],
                "confianza_enlace": float(item["confianza_enlace"]),
                "nota": item["nota"],
            }
            for item in articulos
        ],
        "doctrina_relacionada": list(doctrina_map.values()),
    }
