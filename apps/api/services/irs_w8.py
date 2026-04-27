"""Service para consulta de formularios W-8 del IRS."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_w8_forms(
    db: Session,
    tipo_sujeto: str | None = None,
    estado: str | None = None,
) -> list:
    """Lista formularios W-8 con filtros opcionales."""
    query = text(
        """
        SELECT id, codigo, nombre, descripcion, tipo_sujeto, finalidad,
               validez_anios, obligacion_asociada, texto_detalle, estado,
               partes
        FROM irs_w8_form
        WHERE 1=1
        """
    )
    params: dict = {}

    if tipo_sujeto:
        query = text(str(query) + " AND tipo_sujeto = :tipo_sujeto")
        params["tipo_sujeto"] = tipo_sujeto

    if estado:
        query = text(str(query) + " AND estado = :estado")
        params["estado"] = estado

    rows = db.execute(query, params).mappings()
    return [dict(r) for r in rows]


def get_w8_form(db: Session, codigo: str) -> dict | None:
    """Obtiene un formulario W-8 por codigo."""
    row = db.execute(
        text(
            "SELECT id, codigo, nombre, descripcion, tipo_sujeto, finalidad, "
            "validez_anios, obligacion_asociada, texto_detalle, estado, partes "
            "FROM irs_w8_form WHERE codigo = :codigo"
        ),
        {"codigo": codigo},
    ).mappings().first()

    if row:
        return dict(row)
    return None
