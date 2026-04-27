"""Router de consulta para Ley 11/2021 de prevencion y prevencion del fraude.

Endpoints:
- GET /v1/ley112021/ — lista de articulos clave
- GET /v1/ley112021/articulos/{numero} — detalle de articulo
- GET /v1/ley112021/cobertura — resumen de cobertura
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

PLACEHOLDER = "?"

router = APIRouter(prefix="/v1/ley112021", tags=["ley112021"])

# Articulos clave de la Ley 11/2021 con sus descripciones operativas
ARTICULOS_CLAVE = {
    "1": {
        "descripcion": "Limitaciones de pagos en efectivo: pagos en efectivo con limites de 1.000 EUR",
    },
    "3": {
        "descripcion": "Obligaciones de software factorial: sistemas informaticos que garanticen la correcta registracion de facturas",
    },
    "5": {
        "descripcion": "Registro de facturas recibidas y expedidas: obligaciones de registro y conservacion",
    },
    "10": {
        "descripcion": "Divulgacion de datos: obligacion de informar sobre datos de representantes y beneficiarios",
    },
    "11": {
        "descripcion": "Obligacion de conservacion de documentos: conservacion durante al menos cuatro anos",
    },
    "14": {
        "descripcion": "Certificados de representacion: acreditacion de la identidad y representacion de los afectados",
    },
    "18": {
        "descripcion": "Sanciones: regimen sancionador por incumplimiento de las obligaciones de prevencion del fraude",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de articulos y versiones de la Ley 11/2021."""
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
                WHERE n.codigo = 'LEY112021'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Ley 11/2021 no encontrada. Ejecuta el worker ley112021.py"})

        return {
            "codigo": row["codigo"],
            "titulo": row["titulo"],
            "articulos": row["articulos"],
            "versiones": row["versiones"],
            "articulos_clave": len(ARTICULOS_CLAVE),
        }


@router.get("/articulos-clave")
async def list_articulos_clave():
    """Lista de articulos clave de la Ley 11/2021 con metadatos."""
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
                WHERE n.codigo = 'LEY112021'
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
                "fuente": "LEY112021",
            })

        return {"norma": "LEY112021", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_ley112021_articulo")
async def get_articulo(numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    """Detalle de un articulo de la Ley 11/2021."""
    with db_session() as db:
        filters = ["n.codigo = 'LEY112021'", "a.numero = :numero"]
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
                detail={"error": f"Articulo {numero} no encontrado en Ley 11/2021"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "LEY112021",
            "ley": "11/2021",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2021-11382",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get("/articulos/{numero}/historial", operation_id="get_ley112021_articulo_historial")
async def get_articulo_historial(numero: str):
    """Historial de versiones de un articulo de la Ley 11/2021."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'LEY112021' AND a.numero = :numero
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
                detail={"error": f"Articulo {numero} no encontrado en Ley 11/2021"},
            )

        return {"norma": "LEY112021", "ley": "11/2021", "numero": numero, "historial": historial}
