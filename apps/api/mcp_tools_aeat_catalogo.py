from __future__ import annotations

from typing import Any

from mcp_tools_perfil import MCPToolContract
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session


class ModeloAEATCatalogoItem(BaseModel):
    codigo: str
    nombre: str
    completeness: str
    instrucciones_count: int
    claves_count: int
    reglas_inclusion_count: int
    source_url: str | None = None


BUSCAR_MODELOS_AEAT_CATALOGO = MCPToolContract(
    name="buscar_modelos_aeat_catalogo",
    description=(
        "WHEN to use: Para saber que es un modelo, como se rellena, que campos/casillas "
        "tiene, que claves o instrucciones existen, independientemente del perfil de la "
        "entidad. Ejemplos: 'que es el modelo 303', 'como se rellena el modelo 290', "
        "'que claves tiene el modelo 198'. Parametros: codigo opcional, por ejemplo '123' "
        "o '303'; termino opcional para buscar texto en codigo o descripcion. Devuelve "
        "codigo, nombre, completeness, instrucciones_count, claves_count, "
        "reglas_inclusion_count y source_url. "
        "EXPLICIT WARNING: Esta herramienta NO indica si una entidad tiene obligación de "
        "presentar el modelo. Para obligatoriedad, usar obtener_obligaciones_perfil. "
        "NO combinar resultados de esta herramienta con obligaciones de perfil sin "
        "separación explícita."
    ),
    parameters={
        "codigo": {
            "type": "string",
            "required": False,
            "description": "Codigo de modelo AEAT, por ejemplo '123' o '303'.",
        },
        "termino": {
            "type": "string",
            "required": False,
            "description": "Texto para buscar en codigo o descripcion del modelo.",
        },
    },
    returns=(
        "list[{codigo, nombre, completeness, instrucciones_count, claves_count, "
        "reglas_inclusion_count, source_url}]"
    ),
)

AEAT_CATALOGO_MCP_TOOL_CONTRACTS: tuple[MCPToolContract, ...] = (BUSCAR_MODELOS_AEAT_CATALOGO,)


def _catalog_completeness(
    instrucciones_count: int,
    claves_count: int,
    reglas_inclusion_count: int,
) -> str:
    if instrucciones_count > 0 and (claves_count > 0 or reglas_inclusion_count > 0):
        return "completa"
    if instrucciones_count > 0 or claves_count > 0 or reglas_inclusion_count > 0:
        return "parcial"
    return "parcial"


def buscar_modelos_aeat_catalogo(
    db: Session,
    *,
    codigo: str | None = None,
    termino: str | None = None,
) -> list[ModeloAEATCatalogoItem]:
    codigo_norm = (codigo or "").strip()
    termino_norm = (termino or "").strip().lower()
    like_term = f"%{termino_norm}%"

    rows = db.execute(
        text(
            """
            SELECT
                m.codigo,
                m.nombre,
                m.url_info AS source_url,
                (
                    SELECT COUNT(*)
                    FROM modelo_campana c
                    JOIN modelo_instruccion i ON i.campana_id = c.id
                    WHERE c.modelo_id = m.id
                ) AS instrucciones_count,
                (
                    SELECT COUNT(*)
                    FROM modelo_campana c
                    JOIN modelo_clave k ON k.campana_id = c.id
                    WHERE c.modelo_id = m.id
                ) AS claves_count,
                (
                    SELECT COUNT(*)
                    FROM modelo_campana c
                    JOIN modelo_regla_inclusion r ON r.campana_id = c.id
                    WHERE c.modelo_id = m.id
                ) AS reglas_inclusion_count
            FROM aeat_modelo m
            WHERE COALESCE(m.activo, true) = true
              AND (:codigo = '' OR m.codigo = :codigo)
              AND (
                  :termino = ''
                  OR lower(COALESCE(m.codigo, '')) LIKE :like_term
                  OR lower(COALESCE(m.nombre, '')) LIKE :like_term
              )
            ORDER BY m.codigo
            LIMIT 50
            """
        ),
        {"codigo": codigo_norm, "termino": termino_norm, "like_term": like_term},
    ).mappings()

    items: list[ModeloAEATCatalogoItem] = []
    for row in rows:
        instrucciones_count = int(row["instrucciones_count"] or 0)
        claves_count = int(row["claves_count"] or 0)
        reglas_inclusion_count = int(row["reglas_inclusion_count"] or 0)
        items.append(
            ModeloAEATCatalogoItem(
                codigo=str(row["codigo"]),
                nombre=str(row["nombre"]),
                completeness=_catalog_completeness(
                    instrucciones_count,
                    claves_count,
                    reglas_inclusion_count,
                ),
                instrucciones_count=instrucciones_count,
                claves_count=claves_count,
                reglas_inclusion_count=reglas_inclusion_count,
                source_url=row["source_url"],
            )
        )
    return items
