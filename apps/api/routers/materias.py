from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db import db_session

router = APIRouter(prefix="/v1/materias", tags=["materias"])


@router.get("", operation_id="list_materias")
async def list_materias():
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT m.slug, m.etiqueta, COUNT(am.articulo_id) AS articulos_count
                FROM materia m
                LEFT JOIN articulo_materia am ON am.materia_id = m.id
                GROUP BY m.id, m.slug, m.etiqueta
                ORDER BY m.slug
                """
            )
        ).mappings()
        return {"materias": list(rows)}


@router.get("/{slug}", operation_id="get_materia")
async def get_materia(slug: str):
    with db_session() as db:
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
