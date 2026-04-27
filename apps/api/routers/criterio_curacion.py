"""Curacion pipeline for linea_criterio — auto-suggest + manual assign.

Fase 21 deliverable: pipeline basico de curacion manual o semiasistida
sobre CENDOJ/doctrina.

Rules:
- never generate criterio lines without explicit documentary support
- never present weak inferences as consolidated doctrinal or jurisprudential
- keep separation between curated summary, verbatim citation and source reference
"""

import json

from db import db_session
from fastapi import APIRouter, HTTPException
from schemas import (
    CuracionAssignRequest,
    CuracionAssignResponse,
    LineaCriterioCuracionResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/criterio/curacion", tags=["criterio-curacion"])

# Known ambito values that can be matched against documento_interpretativo.ambito
KNOWN_AMBITOS = [
    "jurisprudencia_tributaria",
    "jurisprudencia_pbcft",
    "jurisprudencia_mercantil_regulatoria",
]


def _score_documento(doc: dict) -> int:
    """Return a relevance score (0-2) for a documento_interpretativo.

    Score logic:
    - 1 point if ambito matches a known ambito
    - 1 point if tipo_documento is "sentencia" or "auto" (higher authority)
    - 1 point if organismo_emisor is "Tribunal Supremo" or "Audiencia Nacional"
    """
    score = 0
    ambito = doc.get("ambito", "") or ""
    if ambito in KNOWN_AMBITOS:
        score += 1

    tipo = (doc.get("tipo_documento") or "").lower()
    if tipo in ("sentencia", "auto"):
        score += 1

    org = (doc.get("organismo_emisor") or "").lower()
    if "tribunal supremo" in org or "audiencia nacional" in org:
        score += 1

    return score


@router.get(
    "/suggest",
    response_model=LineaCriterioCuracionResponse,
    operation_id="sugerir_curacion_lineas",
)
async def sugerir_curacion_lineas():
    """Suggest documentos_interpretativo that could be assigned to existing linea_criterio.

    Matches are based on:
    1. The `ambitos` column of each linea_criterio
    2. The `ambito` column of each documento_interpretativo
    3. Relevance scoring by document type and issuer authority
    """
    with db_session() as db:
        # Fetch all active linea_criterio with ambitos
        linea_rows = db.execute(
            text(
                """
                SELECT id, titulo, ambitos
                FROM linea_criterio
                WHERE activo = true
                  AND ambitos IS NOT NULL
                  AND ambitos != '[]'
                  AND ambitos != ''
                ORDER BY id
                """
            )
        ).mappings()

        suggestions = []
        for linea in linea_rows:
            linea_id = int(linea["id"])
            linea_titulo = linea["titulo"]
            ambitos_raw = linea["ambitos"]
            # ambitos may be JSON string in SQLite or list in PostgreSQL
            if isinstance(ambitos_raw, str):
                try:
                    linea_ambitos = json.loads(ambitos_raw)
                except (json.JSONDecodeError, TypeError):
                    linea_ambitos = []
            else:
                linea_ambitos = ambitos_raw or []

            if not linea_ambitos:
                continue

            # Find matching documentos_interpretativo
            # Use LIKE for JSON array matching (PostgreSQL TEXT[] or JSON)
            ambito_conditions = []
            params = {}
            for i, ambito in enumerate(linea_ambitos):
                key = f"ab{i}"
                ambito_conditions.append(f":{key}")
                params[key] = ambito

            docs = db.execute(
                text(
                    """
                    SELECT id, referencia, tipo_documento, organismo_emisor,
                           ambito, fecha, titulo, url_fuente
                    FROM documento_interpretativo
                    WHERE ambito IN ({conditions})
                    ORDER BY fecha DESC
                    """.format(conditions=", ".join(ambito_conditions))
                ),
                params,
            ).mappings()

            candidatos = []
            for doc in docs:
                score = _score_documento(dict(doc))
                candidatos.append(
                    {
                        "id": int(doc["id"]),
                        "referencia": doc["referencia"],
                        "tipo_documento": doc["tipo_documento"],
                        "organismo_emisor": doc["organismo_emisor"],
                        "ambito": doc["ambito"],
                        "fecha": str(doc["fecha"]),
                        "titulo": doc["titulo"],
                        "url_fuente": doc["url_fuente"],
                        "score": score,
                    }
                )

            # Sort by score descending, then fecha descending
            candidatos.sort(key=lambda c: (c["score"], c["fecha"]), reverse=True)
            # Limit to top 10 per linea
            candidatos = candidatos[:10]

            if candidatos:
                suggestions.append(
                    {
                        "linea_id": linea_id,
                        "linea_titulo": linea_titulo,
                        "candidatos": candidatos,
                        "total_sugeridos": len(candidatos),
                    }
                )

        return {
            "sugerencias": suggestions,
            "total_lineas": len(suggestions),
        }


@router.post(
    "/assign",
    response_model=CuracionAssignResponse,
    operation_id="asignar_documento_a_linea",
)
async def asignar_documento_a_linea(data: CuracionAssignRequest):
    """Assign a documento_interpretativo to a linea_criterio.

    Creates or updates a linea_criterio_referencia entry linking the
    document to the line. This is the manual/semi-assisted curation
    action that the suggest endpoint recommends.
    """
    with db_session() as db:
        # Verify linea exists and is active
        linea = db.execute(
            text("SELECT id, titulo FROM linea_criterio WHERE id = :id AND activo = true"),
            {"id": data.linea_id},
        ).mappings().one_or_none()

        if not linea:
            raise HTTPException(status_code=404, detail="Linea de criterio no encontrada o inactiva")

        # Check if reference already exists
        existing = db.execute(
            text(
                """
                SELECT id FROM linea_criterio_referencia
                WHERE linea_id = :linea_id AND documento_referencia = :doc_ref
                """
            ),
            {"linea_id": data.linea_id, "doc_ref": data.documento_referencia},
        ).mappings().one_or_none()

        if existing:
            return {
                "assigned": False,
                "linea_id": data.linea_id,
                "documento_referencia": data.documento_referencia,
                "referencia_existia": True,
            }

        # Insert the reference
        db.execute(
            text(
                """
                INSERT INTO linea_criterio_referencia
                    (linea_id, documento_referencia, tipo_documento, organismo_emisor, rol_en_linea, orden)
                SELECT
                    :linea_id,
                    :doc_ref,
                    d.tipo_documento,
                    d.organismo_emisor,
                    :rol,
                    COALESCE(
                        (SELECT COALESCE(MAX(orden), 0) + 1 FROM linea_criterio_referencia WHERE linea_id = :linea_id),
                        1
                    )
                FROM documento_interpretativo d
                WHERE d.referencia = :doc_ref
                """
            ),
            {
                "linea_id": data.linea_id,
                "doc_ref": data.documento_referencia,
                "rol": data.rol_en_linea,
            },
        )

        # If document not found in documento_interpretativo, create a bare reference
        if db.execute(
            text(
                """
                SELECT COUNT(*) FROM linea_criterio_referencia
                WHERE linea_id = :linea_id AND documento_referencia = :doc_ref
                """
            ),
            {"linea_id": data.linea_id, "doc_ref": data.documento_referencia},
        ).scalar() == 0:
            db.execute(
                text(
                    """
                    INSERT INTO linea_criterio_referencia
                        (linea_id, documento_referencia, rol_en_linea, orden)
                    VALUES
                        (:linea_id, :doc_ref, :rol,
                         COALESCE((SELECT COALESCE(MAX(orden), 0) + 1 FROM linea_criterio_referencia WHERE linea_id = :linea_id), 1))
                    """
                ),
                {
                    "linea_id": data.linea_id,
                    "doc_ref": data.documento_referencia,
                    "rol": data.rol_en_linea,
                },
            )

        db.commit()

        return {
            "assigned": True,
            "linea_id": data.linea_id,
            "documento_referencia": data.documento_referencia,
            "referencia_existia": False,
        }
