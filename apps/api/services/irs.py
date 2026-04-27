"""Service para consulta de modelos IRS (Internal Revenue Service)."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_irs_models(
    db: Session,
    periodo: str | None = None,
    impuesto: str | None = None,
    activo: bool | None = None,
) -> list:
    """Lista modelos IRS con filtros opcionales."""
    query = text(
        """
        SELECT id, codigo, nombre, periodo, impuesto, url_info, activo
        FROM irs_modelo
        WHERE 1=1
        """
    )
    params: dict = {}

    if periodo:
        query = text(str(query) + " AND periodo = :periodo")
        params["periodo"] = periodo

    if impuesto:
        query = text(str(query) + " AND impuesto = :impuesto")
        params["impuesto"] = impuesto

    if activo is True:
        query = text(str(query) + " AND activo = :activo")
        params["activo"] = activo

    rows = db.execute(query, params).mappings()
    return [dict(r) for r in rows]


def get_irs_model(db: Session, codigo: str) -> dict | None:
    """Obtiene un modelo IRS por codigo."""
    row = db.execute(
        text("SELECT id, codigo, nombre, periodo, impuesto, url_info, activo FROM irs_modelo WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).mappings().first()

    if row:
        return dict(row)
    return None
