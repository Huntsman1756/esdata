"""Router de consulta para NRV 9ª del PGC (instrumentos financieros).

BOE ID: BOE-A-2008-10273 (RD 1514/2006).

Endpoints:
- GET /v1/pgc/nrv/9/cobertura — resumen de cobertura
- GET /v1/pgc/nrv/9/articulos-clave — articulos clave de valoracion
- GET /v1/pgc/nrv/9/articulos/{numero} — detalle de articulo
- GET /v1/pgc/nrv/9/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/pgc/nrv/9", tags=["nrv9"])

# Articulos clave de la NRV 9ª con sus descripciones operativas
ARTICULOS_CLAVE = {
    "1": {
        "descripcion": "Alcance: instrumentos financieros y contratos de compraventa a precio futuro",
    },
    "2": {
        "descripcion": "Definiciones: activos financieros, pasivos financieros, instrumentos de patrimonio",
    },
    "3": {
        "descripcion": "Clasificacion inicial: activos y pasivos financieros a valor razonable",
    },
    "4": {
        "descripcion": "Clasificacion: inversiones mantenidas hasta vencimiento, disponibles para la venta, prestamos y cobros",
    },
    "5": {
        "descripcion": "Reclasificacion de instrumentos financieros cuando deja de ser apropiado el modelo de negocio",
    },
    "6": {
        "descripcion": "Valor razonable: metodo de valoracion y jerarquia de valores de mercado",
    },
    "7": {
        "descripcion": "Deterioro de valor: reconocimiento y medicion de perdidas por deterioro crediticio",
    },
    "8": {
        "descripcion": "Coberturas: contabilidad de coberturas para instrumentos derivados y contratos",
    },
    "9": {
        "descripcion": "Desreconocimiento: baja en balanace de instrumentos financieros",
    },
    "10": {
        "descripcion": "Informacion a revelar: clasificacion, valoracion, deterioro y coberturas",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de articulos y versiones de la NRV 9ª."""
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
                WHERE n.codigo = 'NRV9'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NRV9 no encontrada. Ejecuta el worker nrv9.py"
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
    """Lista de articulos clave de la NRV 9ª con metadatos."""
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
                WHERE n.codigo = 'NRV9'
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
                "fuente": "NRV9",
            })

        return {"norma": "NRV9", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_nrv9_articulo")
async def get_articulo(
    numero: str,
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    """Detalle de un articulo de la NRV 9ª PGC."""
    with db_session() as db:
        filters = ["n.codigo = 'NRV9'", "a.numero = :numero"]
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
                detail={
                    "error": f"Articulo {numero} no encontrado en NRV9"
                },
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "NRV9",
            "norma_completa": "NRV 9ª PGC",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2008-10273",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get(
    "/articulos/{numero}/historial",
    operation_id="get_nrv9_articulo_historial",
)
async def get_articulo_historial(numero: str):
    """Historial de versiones de un articulo de la NRV 9ª PGC."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'NRV9' AND a.numero = :numero
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
                detail={
                    "error": f"Articulo {numero} no encontrado en NRV9"
                },
            )

        return {"norma": "NRV9", "norma_completa": "NRV 9ª PGC", "numero": numero, "historial": historial}
