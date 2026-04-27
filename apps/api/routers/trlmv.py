"""Router de consulta para TRLMV — RD Legislativo 4/2015 (Ley del Mercado de Valores).

Endpoints:
- GET /v1/trlmv/cobertura — resumen de cobertura
- GET /v1/trlmv/articulos-clave — articulos clave de la norma
- GET /v1/trlmv/articulos/{numero} — detalle de articulo
- GET /v1/trlmv/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/trlmv", tags=["trlmv"])

# Articulos clave del TRLMV con sus descripciones operativas
ARTICULOS_CLAVE = {
    "50": {
        "descripcion": "Autorizacion de entidades: requisitos y procedimiento para el establecimiento de sociedades de valores",
    },
    "63": {
        "descripcion": "Sociedades de valores: constitucion, organizacion y actividad de las entidades que negocian valores",
    },
    "215": {
        "descripcion": "Obligaciones de transparencia: deberes de informacion de los emissores de valores cotizados",
    },
    "228": {
        "descripcion": "Gobierno corporativo: principios y codigo de buen gobierno para emissores de valores",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de articulos y versiones del TRLMV."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT
                    n.codigo,
                    n.titulo,
                    COUNT(DISTINCT a.id) AS articulos,
                    COUNT(va.id) AS versiones
                FROM norma n
                LEFT JOIN articulo a ON a.norma_id = n.id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'TRLMV'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "TRLMV no encontrada. Ejecuta el worker trlmv.py"},
            )

        return {
            "codigo": row["codigo"],
            "titulo": row["titulo"],
            "articulos": row["articulos"],
            "versiones": row["versiones"],
            "articulos_clave": len(ARTICULOS_CLAVE),
        }


@router.get("/articulos-clave")
async def list_articulos_clave():
    """Lista de articulos clave del TRLMV con metadatos."""
    with db_session() as db:
        nums = tuple(ARTICULOS_CLAVE.keys())
        placeholders = ", ".join(f":n{i}" for i in range(len(nums)))
        params = {f"n{i}": n for i, n in enumerate(nums)}
        rows = db.execute(
            text(
                f"""
                SELECT a.numero, a.titulo
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                WHERE n.codigo = 'TRLMV'
                  AND a.numero IN ({placeholders})
                ORDER BY CAST(a.numero AS INTEGER)
                """
            ),
            params,
        ).mappings()

        articulos_db = {row["numero"]: row for row in rows}

        resultado = []
        for numero, meta in ARTICULOS_CLAVE.items():
            articulo = articulos_db.get(numero, {})
            resultado.append({
                "numero": numero,
                "titulo": articulo.get("titulo"),
                "descripcion": meta["descripcion"],
                "vigente": True,
                "fuente": "TRLMV",
            })

        return {"norma": "TRLMV", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_trlmv_articulo")
async def get_articulo(
    numero: str,
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    """Detalle de un articulo del TRLMV."""
    with db_session() as db:
        filters = ["n.codigo = 'TRLMV'", "a.numero = :numero"]
        params = {"numero": numero}

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
            raise HTTPException(
                status_code=404,
                detail={"error": f"Articulo {numero} no encontrado en TRLMV"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "TRLMV",
            "ley": "4/2015",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2011-14568",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get(
    "/articulos/{numero}/historial",
    operation_id="get_trlmv_articulo_historial",
)
async def get_articulo_historial(numero: str):
    """Historial de versiones de un articulo del TRLMV."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'TRLMV' AND a.numero = :numero
                ORDER BY va.vigente_desde DESC
                """
            ),
            {"numero": numero},
        ).mappings()

        historial = [
            {
                "texto": row["texto"],
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            }
            for row in rows
        ]

        if not historial:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Articulo {numero} no encontrado en TRLMV"},
            )

        return {"norma": "TRLMV", "ley": "4/2015", "numero": numero, "historial": historial}
