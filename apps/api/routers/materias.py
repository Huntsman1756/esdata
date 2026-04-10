from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db import get_db

router = APIRouter(prefix="/v1/materias", tags=["materias"])


@router.get("/{slug}")
async def get_materia(slug: str):
    db = next(get_db())
    rows = list(
        db.execute(
            text(
                """
                SELECT
                    m.slug,
                    m.etiqueta,
                    n.codigo AS norma,
                    a.numero,
                    am.relevancia
                FROM materia m
                JOIN articulo_materia am ON am.materia_id = m.id
                JOIN articulo a ON a.id = am.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE m.slug = :slug
                ORDER BY am.relevancia DESC, n.codigo, a.numero
                """
            ),
            {"slug": slug},
        ).mappings()
    )
    if not rows:
        raise HTTPException(status_code=404, detail={"error": "Materia no encontrada"})
    return {
        "slug": rows[0]["slug"],
        "etiqueta": rows[0]["etiqueta"],
        "articulos": [
            {
                "norma": row["norma"],
                "numero": row["numero"],
                "relevancia": row["relevancia"],
            }
            for row in rows
        ],
    }
