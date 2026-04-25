import json

from sqlalchemy import text

from db import SessionLocal


JSON_FIELDS = ("evidencia_requerida", "checklist", "accion_recomendada_confirmada")


def _parse_json_row(row: dict) -> dict:
    for key in JSON_FIELDS:
        value = row.get(key)
        if isinstance(value, str):
            try:
                row[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                row[key] = value
    return row


def list_workflow_cases() -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT workflow_id, cambio_codigo, obligacion_codigo, estado,
                       owner_rol, fecha_objetivo, evidencia_requerida,
                       checklist, resultado_revision, notas,
                       accion_recomendada_confirmada
                FROM workflow_cases
                ORDER BY created_at
                """
            )
        ).mappings().all()

        return [_parse_json_row(dict(row)) for row in rows]
