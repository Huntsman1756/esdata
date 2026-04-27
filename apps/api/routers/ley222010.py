"""Router de consulta para Ley 22/2010, de 20 de julio.

Modifica el TRLIS: obligaciones informativas, sanciones CNMV.
BOE-A-2010-16380

Endpoints:
- GET /v1/ley222010/cobertura — resumen de cobertura
- GET /v1/ley222010/articulos-clave — articulos clave
- GET /v1/ley222010/articulos/{numero} — detalle de articulo
- GET /v1/ley222010/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/ley222010", tags=["ley222010"])

# Articulos clave de la Ley 22/2010 con sus descripciones operativas
ARTICULOS_CLAVE = {
    "1": {
        "descripcion": "Modificaciones del TRLIS: ambito de aplicacion y sujetos pasivos",
    },
    "5": {
        "descripcion": "Obligaciones informativas: comunicacion de operaciones con entidades de paises无 tributarios",
    },
    "10": {
        "descripcion": "Sanciones CNMV: régimen infractor y graduacion de multas",
    },
    "15": {
        "descripcion": "Gobierno corporativo: obligaciones de los organos de administracion en sociedades cotizadas",
    },
    "18": {
        "descripcion": "Precios de transferencia: documentacion justificativa",
    },
    "20": {
        "descripcion": "Intercambio de informacion: cooperacion con autoridades de la UE",
    },
    "25": {
        "descripcion": "Obligaciones informativas sobre operaciones con partes vinculadas",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de artículos y versiones de la Ley 22/2010."""
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
                WHERE n.codigo = 'LEY222010'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Ley 22/2010 no encontrada. Ejecuta el worker ley222010.py"
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
    """Lista de artículos clave de la Ley 22/2010 con metadatos."""
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
                WHERE n.codigo = 'LEY222010'
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
                "fuente": "LEY222010",
            })

        return {"norma": "LEY222010", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_ley222010_articulo")
async def get_articulo(numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    """Detalle de un artículo de la Ley 22/2010."""
    with db_session() as db:
        filters = ["n.codigo = 'LEY222010'", "a.numero = :numero"]
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
                detail={"error": f"Artículo {numero} no encontrado en Ley 22/2010"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "LEY222010",
            "ley": "22/2010",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2010-16380",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get("/articulos/{numero}/historial", operation_id="get_ley222010_articulo_historial")
async def get_articulo_historial(numero: str):
    """Historial de versiones de un artículo de la Ley 22/2010."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'LEY222010' AND a.numero = :numero
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
                detail={"error": f"Artículo {numero} no encontrado en Ley 22/2010"},
            )

        return {"norma": "LEY222010", "ley": "22/2010", "numero": numero, "historial": historial}
