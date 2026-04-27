"""Router de consulta para Ley 27/2014 de Impuesto sobre Sociedades (LIS).

Endpoints:
- GET /v1/ley272014/ — lista de articulos clave
- GET /v1/ley272014/articulos/{numero} — detalle de articulo
- GET /v1/ley272014/cobertura — resumen de cobertura
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

PLACEHOLDER = "?"

router = APIRouter(prefix="/v1/ley272014", tags=["ley272014"])

# Articulos clave de la LIS con sus descripciones operativas
ARTICULOS_CLAVE = {
    "2": {
        "descripcion": "Hecho imponible: el sujeto pasivo realiza actividades económicas o obtiene rentas",
    },
    "15": {
        "descripcion": "Base imponible: resultado contable ajustado a efectos fiscales",
    },
    "20": {
        "descripcion": "Deducciones: inversiones y gastos deducibles",
    },
    "24": {
        "descripcion": "Deber de información entre sociedades vinculadas",
    },
    "100": {
        "descripcion": "Transmisiones patrimoniales: valoración de activos",
    },
    "135": {
        "descripcion": "Conciliación fiscal: diferencias entre contabilidad y fiscalidad",
    },
    "140": {
        "descripcion": "Operaciones entre vinculados: precios de transferencia",
    },
    "200": {
        "descripcion": "Deducciones: inversiones productivas y créditos fiscales",
    },
    "240": {
        "descripcion": "Presentación: obligaciones formales del Impuesto sobre Sociedades",
    },
    "252": {
        "descripcion": "Responsables por cumplimiento del IS",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de artículos y versiones de la LIS."""
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
                WHERE n.codigo = 'LIS'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "LIS no encontrada. Ejecuta el worker ley272014.py"})

        return {
            "codigo": row["codigo"],
            "titulo": row["titulo"],
            "articulos": row["articulos"],
            "versiones": row["versiones"],
            "articulos_clave": len(ARTICULOS_CLAVE),
        }


@router.get("/articulos-clave")
async def list_articulos_clave():
    """Lista de artículos clave de la LIS con metadatos."""
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
                WHERE n.codigo = 'LIS'
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
                "fuente": "LIS",
            })

        return {"norma": "LIS", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_ley272014_articulo")
async def get_articulo(numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    """Detalle de un artículo de la Ley 27/2014."""
    with db_session() as db:
        filters = ["n.codigo = 'LIS'", "a.numero = :numero"]
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
                detail={"error": f"Artículo {numero} no encontrado en LIS"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "LIS",
            "ley": "27/2014",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2014-12328",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get("/articulos/{numero}/historial", operation_id="get_ley272014_articulo_historial")
async def get_articulo_historial(numero: str):
    """Historial de versiones de un artículo de la LIS."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'LIS' AND a.numero = :numero
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
                detail={"error": f"Artículo {numero} no encontrado en LIS"},
            )

        return {"norma": "LIS", "ley": "27/2014", "numero": numero, "historial": historial}
