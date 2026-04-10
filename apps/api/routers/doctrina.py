from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db import get_db

router = APIRouter(prefix="/v1/doctrina", tags=["doctrina"])


@router.get("/{referencia}")
async def get_doctrina(referencia: str):
    db = next(get_db())
    row = db.execute(
        text(
            """
            SELECT
                d.referencia,
                d.tipo_documento,
                d.organismo_emisor,
                d.texto,
                a.numero AS articulo_numero
            FROM documento_interpretativo d
            LEFT JOIN documento_articulo da ON da.documento_id = d.id
            LEFT JOIN articulo a ON a.id = da.articulo_id
            WHERE d.referencia = :referencia
            LIMIT 1
            """
        ),
        {"referencia": referencia},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"error": "Documento no encontrado"})

    has_anchor = bool(row["articulo_numero"])
    return {
        "referencia": row["referencia"],
        "tipo_documento": row["tipo_documento"],
        "organismo_emisor": row["organismo_emisor"],
        "texto": row["texto"],
        "confianza": {
            "nivel": 2 if has_anchor else 0,
            "fuentes": [row["referencia"]],
            "aviso": None if has_anchor else "Criterio sin anclaje normativo suficiente",
        },
    }
