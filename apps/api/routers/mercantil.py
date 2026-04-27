"""Router de consulta para Ley de Sociedades de Capital (RD Legislativo 1/2010).

Endpoints:
- GET /v1/mercantil/cobertura — resumen de cobertura
- GET /v1/mercantil/libros-contables — libros contables obligatorios (arts. 28-33)
- GET /v1/mercantil/articulos/{numero} — detalle de articulo
- GET /v1/mercantil/articulos/{numero}/historial — historial de versiones
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/mercantil", tags=["mercantil"])

# Articulos clave sobre libros contables de la LSC
LIBROS_CONTABLES = [
    {
        "numero": "28",
        "titulo_db": "libro inventario",
        "descripcion": "Obligacion de llevar libro de inventario: reflejo fiel del patrimonio, situacion financial y resultados de la sociedad",
    },
    {
        "numero": "30",
        "titulo_db": "libro de cuentas",
        "descripcion": "Obligacion de llevar libro de diario: registro cronologico de todas las operaciones contables",
    },
    {
        "numero": "31",
        "titulo_db": "libro de balances",
        "descripcion": "Obligacion de elaborar balance de situacion annual al cierre de cada ejercicio social",
    },
    {
        "numero": "33",
        "titulo_db": "legalizacion libros",
        "descripcion": "Legalizacion y registro de los libros obligatorios ante el Registro Mercantil correspondiente",
    },
]

# Articulos clave de la LSC con descripciones operativas
ARTICULOS_CLAVE = {
    "1": {
        "descripcion": "Objeto: la ley regula las sociedades de capital (S.A., S.L., S.E.)",
    },
    "2": {
        "descripcion": "Sociedad de responsabilidad limitada: capital no superior a 1M EUR, socios limitados",
    },
    "5": {
        "descripcion": "Sociedad anonima: capital dividido en acciones, minimo 60.000 EUR",
    },
    "14": {
        "descripcion": "Capital social: constitucion, aumentos, reducciones y proteccion del capital",
    },
    "28": {
        "descripcion": "Libro inventario: obligacion de llevar contabilidad que refleje la situacion patrimonial",
    },
    "30": {
        "descripcion": "Libro de cuentas (diario): registro cronologico de todas las operaciones",
    },
    "31": {
        "descripcion": "Libro de balances: balance annual al cierre del ejercicio",
    },
    "33": {
        "descripcion": "Legalizacion de libros: registro ante el Registro Mercantil",
    },
    "92": {
        "descripcion": "Junta general: organo deliberante de la sociedad",
    },
    "146": {
        "descripcion": "Administracion y representacion: organos de gobierno de la sociedad",
    },
    "150": {
        "descripcion": "Administradores: nombramiento, funciones, responsabilidad y deberes",
    },
    "164": {
        "descripcion": "Transformacion, fusion y escision de sociedades",
    },
    "200": {
        "descripcion": "Disolucion y liquidacion: causas y procedimiento",
    },
}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de articulos y versiones de la Ley de Sociedades de Capital."""
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
                WHERE n.codigo = 'LEYSOC'
                GROUP BY n.id, n.codigo, n.titulo
                """
            )
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "LSC no encontrada. Ejecuta el worker ley12010.py"
                },
            )

        return {
            "codigo": row["codigo"],
            "titulo": row["titulo"],
            "articulos": row["articulos"],
            "versiones": row["versiones"],
            "articulos_clave": len(ARTICULOS_CLAVE),
            "boe_id": "BOE-A-2010-15523",
        }


@router.get("/libros-contables")
async def get_libros_contables():
    """Consulta los libros contables obligatorios (arts. 28-33) de la LSC."""
    with db_session() as db:
        nums = tuple(item["numero"] for item in LIBROS_CONTABLES)
        placeholders = ", ".join(f":n{i}" for i in range(len(nums)))
        params = {f"n{i}": n for i, n in enumerate(nums)}

        rows = db.execute(
            text(
                f"""
                SELECT a.numero, a.titulo
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                WHERE n.codigo = 'LEYSOC'
                  AND a.numero IN ({placeholders})
                ORDER BY CAST(a.numero AS INTEGER)
                """.strip()
            ),
            params,
        ).mappings()

        articulos_db = {row["numero"]: row for row in rows}

        resultado = []
        for item in LIBROS_CONTABLES:
            articulo = articulos_db.get(item["numero"], {})
            resultado.append({
                "numero": item["numero"],
                "titulo": articulo.get("titulo"),
                "descripcion": item["descripcion"],
                "vigente": True,
                "fuente": "LEYSOC",
            })

        return {"norma": "LEYSOC", "ley": "1/2010", "libros_contables": resultado}


@router.get("/articulos-clave")
async def list_articulos_clave():
    """Lista de articulos clave de la LSC con metadatos."""
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
                WHERE n.codigo = 'LEYSOC'
                  AND a.numero IN ({placeholders})
                ORDER BY CAST(a.numero AS INTEGER)
                """.strip()
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
                "fuente": "LEYSOC",
            })

        return {"norma": "LEYSOC", "ley": "1/2010", "articulos_clave": resultado}


@router.get("/articulos/{numero}", operation_id="get_mercantil_articulo")
async def get_articulo(
    numero: str,
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    """Detalle de un articulo de la Ley de Sociedades de Capital."""
    with db_session() as db:
        filters = ["n.codigo = 'LEYSOC'", "a.numero = :numero"]
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
                detail={"error": f"Articulo {numero} no encontrado en LSC"},
            )

        meta = ARTICULOS_CLAVE.get(numero, {})

        return {
            "norma": "LEYSOC",
            "ley": "1/2010",
            "numero": row["numero"],
            "titulo": meta.get("descripcion"),
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "fuente": "BOE-A-2010-15523",
            "clave": numero in ARTICULOS_CLAVE,
        }


@router.get(
    "/articulos/{numero}/historial",
    operation_id="get_mercantil_articulo_historial",
)
async def get_articulo_historial(numero: str):
    """Historial de versiones de un articulo de la LSC."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = 'LEYSOC' AND a.numero = :numero
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
                detail={"error": f"Articulo {numero} no encontrado en LSC"},
            )

        return {"norma": "LEYSOC", "ley": "1/2010", "numero": numero, "historial": historial}
