"""Router de consulta para Real Decreto 217/2008 sobre normas contables.

Normas contables para bancos y sociedades de valores que elaboren estados financieros.
BOE-A-2008-500

Endpoints:
- GET /v1/rd2172008/cobertura — resumen de cobertura
- GET /v1/rd2172008/articulos-clave — articulos clave
- GET /v1/rd2172008/articulos/{numero} — detalle de articulo
- GET /v1/rd2172008/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/rd2172008", tags=["rd2172008"])

# Articulos clave del RD 217/2008 con sus descripciones operativas
ARTICULOS_CLAVE = {
    "3": {
        "descripcion": "Provisiones: constitucion y valoración de provisions para riesgos y gastos",
    },
    "5": {
        "descripcion": "Activos financieros: clasificacion, valoracion y deterioro de instrumentos financieros",
    },
    "8": {
        "descripcion": "Clasificacion de instrumentos: activos disponibles para la venta, mantenidos hasta vencimiento y prestamos y cobros",
    },
    "10": {
        "descripcion": "Instrumentos derivados: valor razonable y cobertura de riesgos",
    },
    "15": {
        "descripcion": "Estados financieros: balance, cuenta de perdidas y ganancias, estado de cambios en el patrimonio",
    },
    "20": {
        "descripcion": "Normas de consolidacion: estados financieros del grupo bancario o de valores",
    },
    "25": {
        "descripcion": "Informacion complementaria: revelacion de riesgos financieros y ratios prudenciales",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de artículos y versiones del RD 217/2008."""
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
                WHERE n.codigo = 'RD2172008'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "RD 217/2008 no encontrado. Ejecuta el worker rd2172008.py"
                },
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
    """Lista de artículos clave del RD 217/2008 con metadatos."""
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
                WHERE n.codigo = 'RD2172008'
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
                "fuente": "RD2172008",
            })

        return {"norma": "RD2172008", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_rd2172008_articulo")
async def get_articulo(numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    """Detalle de un artículo del Real Decreto 217/2008."""
    with db_session() as db:
        filters = ["n.codigo = 'RD2172008'", "a.numero = :numero"]
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
                detail={"error": f"Artículo {numero} no encontrado en RD 217/2008"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "RD2172008",
            "ley": "217/2008",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2008-500",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get("/articulos/{numero}/historial", operation_id="get_rd2172008_articulo_historial")
async def get_articulo_historial(numero: str):
    """Historial de versiones de un artículo del RD 217/2008."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'RD2172008' AND a.numero = :numero
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
                detail={"error": f"Artículo {numero} no encontrado en RD 217/2008"},
            )

        return {"norma": "RD2172008", "ley": "217/2008", "numero": numero, "historial": historial}
