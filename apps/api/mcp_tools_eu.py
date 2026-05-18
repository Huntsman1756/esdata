from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session


TipoNormaEu = Literal["reglamento_ue", "directiva_ue", "rts", "its", "guideline_esma"]


class NormaEuItem(BaseModel):
    codigo: str
    celex: str | None = None
    titulo: str
    tipo_norma: str | None = None
    publicacion_doue: str | None = None
    url_eurlex: str | None = None
    vigente: bool | None = None
    derogada_por: str | None = None


@dataclass(frozen=True)
class MCPToolContract:
    name: str
    description: str
    parameters: dict[str, Any]
    returns: str


BUSCAR_NORMA_EU = MCPToolContract(
    name="buscar_norma_eu",
    description=(
        "Busca reglamentos, directivas, RTS, ITS y guias ESMA de la UE cargados en ESData. "
        "WHEN to use: usar cuando el usuario pregunta por una norma UE concreta como MiFIR, "
        "EMIR, DORA, CRR, UCITS, AIFMD o SFTR, por un CELEX, o por si una norma UE esta "
        "cargada en el sistema. Parametros: termino obligatorio con keyword, CELEX o nombre; "
        "tipo_norma opcional acepta reglamento_ue, directiva_ue, rts, its o guideline_esma. "
        "Devuelve codigo, CELEX, titulo oficial, fecha de publicacion DOUE, URL EUR-Lex, "
        "vigente y derogada_por. No usar para obtener obligaciones de una entidad. Para eso, "
        "usar obtener_obligaciones_perfil. NO responde si un perfil debe cumplir una norma; "
        "solo devuelve ficha normativa UE."
    ),
    parameters={
        "termino": {
            "type": "string",
            "required": True,
            "description": "Keyword, CELEX, or regulation name.",
        },
        "tipo_norma": {
            "type": "string",
            "required": False,
            "enum": ["reglamento_ue", "directiva_ue", "rts", "its", "guideline_esma"],
        },
    },
    returns=(
        "list[{codigo, celex, titulo, tipo_norma, publicacion_doue, "
        "url_eurlex, vigente, derogada_por}]"
    ),
)

EU_MCP_TOOL_CONTRACTS: tuple[MCPToolContract, ...] = (BUSCAR_NORMA_EU,)


def buscar_norma_eu(
    db: Session,
    termino: str,
    tipo_norma: TipoNormaEu | None = None,
) -> list[NormaEuItem]:
    term = (termino or "").strip().lower()
    like_term = f"%{term}%"
    tipo_filter = ""
    params: dict[str, Any] = {"term": term, "like_term": like_term}
    if tipo_norma is not None:
        tipo_filter = "AND tipo_norma = :tipo_norma"
        params["tipo_norma"] = tipo_norma
    rows = db.execute(
        text(
            f"""
            SELECT
                codigo,
                celex,
                titulo,
                tipo_norma,
                CAST(publicacion_doue AS TEXT) AS publicacion_doue,
                url_eurlex,
                vigente,
                derogada_por
            FROM norma
            WHERE tipo_norma IS NOT NULL
              {tipo_filter}
              AND (
                  :term = ''
                  OR lower(COALESCE(titulo, '')) LIKE :like_term
                  OR lower(COALESCE(celex, '')) LIKE :like_term
                  OR lower(COALESCE(codigo, '')) LIKE :like_term
              )
            ORDER BY publicacion_doue IS NULL, publicacion_doue DESC, codigo
            LIMIT 10
            """
        ),
        params,
    ).mappings()
    return [
        NormaEuItem(
            codigo=str(row["codigo"]),
            celex=row["celex"],
            titulo=str(row["titulo"]),
            tipo_norma=row["tipo_norma"],
            publicacion_doue=row["publicacion_doue"],
            url_eurlex=row["url_eurlex"],
            vigente=row["vigente"],
            derogada_por=row["derogada_por"],
        )
        for row in rows
    ]
