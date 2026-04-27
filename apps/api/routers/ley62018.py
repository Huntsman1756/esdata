"""Router de consulta para LEY62018 — Ley 6/2018 de Servicios de Inversion (MiFID).

Endpoints:
- GET /v1/ley62018/cobertura — resumen de cobertura
- GET /v1/ley62018/articulos-clave — articulos clave de la norma
- GET /v1/ley62018/articulos/{numero} — detalle de articulo
- GET /v1/ley62018/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/ley62018", tags=["ley62018"])

# Articulos clave de la Ley 6/2018 con sus descripciones operativas
ARTICULOS_CLAVE = {
    "3": {
        "descripcion": "Servicios de inversion: catalogo de servicios sujetos a la ley (recepcion/transmision, ejecucion, gestion de cartera, etc.)",
    },
    "7": {
        "descripcion": "Servicio de asesoramiento: requisitos y deberes en la prestacion de servicios de inversion",
    },
    "12": {
        "descripcion": "Conflictos de interes: identificacion, prevencion y gestion de conflictos en empresas de servicios de inversion",
    },
    "15": {
        "descripcion": "Compliance: funcion de cumplimiento normativo en empresas de servicios de inversion",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de articulos y versiones de la LEY62018."""
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
                WHERE n.codigo = 'LEY62018'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "LEY62018 no encontrada. Ejecuta el worker ley62018.py"},
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
    """Lista de articulos clave de la Ley 6/2018 con metadatos."""
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
                WHERE n.codigo = 'LEY62018'
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
                "fuente": "LEY62018",
            })

        return {"norma": "LEY62018", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_ley62018_articulo")
async def get_articulo(
    numero: str,
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    """Detalle de un articulo de la Ley 6/2018."""
    with db_session() as db:
        filters = ["n.codigo = 'LEY62018'", "a.numero = :numero"]
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
                detail={"error": f"Articulo {numero} no encontrado en LEY62018"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "LEY62018",
            "ley": "6/2018",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2018-10582",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get(
    "/articulos/{numero}/historial",
    operation_id="get_ley62018_articulo_historial",
)
async def get_articulo_historial(numero: str):
    """Historial de versiones de un articulo de la Ley 6/2018."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'LEY62018' AND a.numero = :numero
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
                detail={"error": f"Articulo {numero} no encontrado en LEY62018"},
            )

        return {"norma": "LEY62018", "ley": "6/2018", "numero": numero, "historial": historial}
