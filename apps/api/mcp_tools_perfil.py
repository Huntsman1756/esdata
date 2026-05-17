from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session


DominioPerfil = Literal["FISCAL", "PBC_FT", "CNMV", "ALL"]
PerfilCodigo = Literal[
    "sociedad_valores",
    "agencia_valores",
    "sgiic",
    "eaf",
    "entidad_credito",
    "empresa_servicios_pago",
]
Periodicidad = Literal["diaria", "mensual", "trimestral", "semestral", "anual", "ad_hoc", "continua"]

CALENDARIO_PERIODICIDADES: tuple[Periodicidad, ...] = (
    "diaria",
    "mensual",
    "trimestral",
    "semestral",
    "anual",
    "ad_hoc",
    "continua",
)


class PerfilResumen(BaseModel):
    codigo: str
    nombre: str
    supervisor: str
    regimen_primario: str | None = None


class ObligacionItem(BaseModel):
    descripcion: str
    obligacion_tipo: str
    periodicidad: str | None = None
    plazo_descripcion: str | None = None
    modelo_aeat: str | None = None
    norma_codigo: str | None = None
    articulo_referencia: str | None = None
    fuente_secundaria: str | None = None
    verified: bool
    completeness: str
    source_url: str = Field(min_length=1)
    evidence_notice: str


class ObligacionesResponse(BaseModel):
    perfil: PerfilResumen
    dominio_filtrado: DominioPerfil = "ALL"
    obligaciones: list[ObligacionItem]
    total: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    safe_to_answer: bool = True
    evidence_notice: str = ""

    @model_validator(mode="after")
    def derive_counts_and_safety(self) -> ObligacionesResponse:
        total = len(self.obligaciones)
        verified_count = sum(1 for item in self.obligaciones if item.verified)
        unverified_count = total - verified_count

        self.total = total
        self.verified_count = verified_count
        self.unverified_count = unverified_count
        self.safe_to_answer = unverified_count <= total * 0.3 if total else True
        if unverified_count:
            self.evidence_notice = (
                f"evidence_limited: {unverified_count} de {total} obligaciones "
                "pendientes de verificacion completa"
            )
        else:
            self.evidence_notice = "Todas las obligaciones devueltas tienen evidencia verificada"
        return self


class CalendarioResponse(BaseModel):
    perfil: PerfilResumen
    calendario: dict[Periodicidad, list[ObligacionItem]]


@dataclass(frozen=True)
class MCPToolContract:
    name: str
    description: str
    parameters: dict[str, Any]
    returns: str


LISTAR_PERFILES_ENTIDAD = MCPToolContract(
    name="listar_perfiles_entidad",
    description=(
        "Lista los tipos de entidad supervisada disponibles en ESData. Usar cuando "
        "el usuario pregunta que tipo de entidad es, que perfil tiene, o que categorias "
        "de entidad supervisada existen en el sistema. No usar para buscar obligaciones concretas."
    ),
    parameters={},
    returns="list[{codigo, nombre, supervisor, regimen_primario}]",
)

OBTENER_OBLIGACIONES_PERFIL = MCPToolContract(
    name="obtener_obligaciones_perfil",
    description=(
        "Devuelve las obligaciones regulatorias concretas para un tipo de entidad supervisada "
        "espanola. Usar cuando el usuario pregunta que obligaciones tiene una sociedad de "
        "valores, agencia de valores, SGIIC o EAF en materia fiscal (AEAT), PBC/FT "
        "(SEPBLAC) o mercados (CNMV). Incluye que modelos AEAT presentar, con que "
        "periodicidad, y que norma lo exige. No usar para buscar texto normativo; usar "
        "herramientas de busqueda legislativa para eso."
    ),
    parameters={
        "perfil_codigo": {
            "type": "string",
            "required": True,
            "enum": [
                "sociedad_valores",
                "agencia_valores",
                "sgiic",
                "eaf",
                "entidad_credito",
                "empresa_servicios_pago",
            ],
        },
        "dominio": {
            "type": "string",
            "required": False,
            "enum": ["FISCAL", "PBC_FT", "CNMV", "ALL"],
            "default": "ALL",
        },
    },
    returns="ObligacionesResponse",
)

CALENDARIO_OBLIGACIONES_PERFIL = MCPToolContract(
    name="calendario_obligaciones_perfil",
    description=(
        "Devuelve el calendario operativo de obligaciones de una entidad supervisada agrupado "
        "por periodicidad. Usar cuando el usuario pregunta cuando hay que presentar modelos, "
        "que vence este trimestre, que hay que hacer mensualmente, o como organizar el "
        "calendario anual de compliance. No usar para conocer el contenido de una obligacion; "
        "usar obtener_obligaciones_perfil para eso."
    ),
    parameters={
        "perfil_codigo": {
            "type": "string",
            "required": True,
            "enum": [
                "sociedad_valores",
                "agencia_valores",
                "sgiic",
                "eaf",
                "entidad_credito",
                "empresa_servicios_pago",
            ],
        }
    },
    returns="CalendarioResponse",
)

PERFIL_MCP_TOOL_CONTRACTS: tuple[MCPToolContract, ...] = (
    LISTAR_PERFILES_ENTIDAD,
    OBTENER_OBLIGACIONES_PERFIL,
    CALENDARIO_OBLIGACIONES_PERFIL,
)


class PerfilNotFoundError(ValueError):
    """Raised when a requested applicability profile is not configured."""


logger = logging.getLogger(__name__)


DOMAIN_FILTERS: dict[str, str] = {
    "FISCAL": "op.obligacion_tipo IN ('AUTOLIQUIDACION', 'DECLARACION_INFORMATIVA')",
    "PBC_FT": (
        "op.obligacion_tipo IN ('DILIGENCIA_DEBIDA', 'COMUNICACION_INDICIO', "
        "'CONTROL_INTERNO', 'FORMACION', 'REGISTRO') "
        "AND COALESCE(op.norma_codigo, '') IN ('LEY10_2010', 'RD_304_2014')"
    ),
    "CNMV": (
        "op.obligacion_tipo IN ('REPORTING', 'CONTROL_INTERNO', 'FORMACION') "
        "AND COALESCE(op.norma_codigo, '') NOT IN ('LEY10_2010', 'RD_304_2014')"
    ),
    "ALL": "1 = 1",
}


def listar_perfiles_entidad(db: Session) -> list[PerfilResumen]:
    rows = db.execute(
        text(
            """
            SELECT codigo, nombre, supervisor, regimen_primario
            FROM perfil_entidad
            WHERE activo = true
            ORDER BY supervisor, codigo
            """
        )
    ).mappings()
    return [
        PerfilResumen(
            codigo=str(row["codigo"]),
            nombre=str(row["nombre"]),
            supervisor=str(row["supervisor"]),
            regimen_primario=row["regimen_primario"],
        )
        for row in rows
    ]


def _get_perfil(db: Session, perfil_codigo: str) -> PerfilResumen:
    row = db.execute(
        text(
            """
            SELECT codigo, nombre, supervisor, regimen_primario
            FROM perfil_entidad
            WHERE codigo = :codigo
              AND activo = true
            """
        ),
        {"codigo": perfil_codigo},
    ).mappings().first()
    if row is None:
        raise PerfilNotFoundError(f"Perfil no configurado: {perfil_codigo}")
    return PerfilResumen(
        codigo=str(row["codigo"]),
        nombre=str(row["nombre"]),
        supervisor=str(row["supervisor"]),
        regimen_primario=row["regimen_primario"],
    )


def _evidence_notice(row: Any) -> str:
    if bool(row["verified"]):
        norma = row["norma_codigo"] or "fuente oficial"
        articulo = row["articulo_referencia"] or ""
        return f"Verificado contra {norma} {articulo}".strip()
    return "evidence_limited: pendiente verificacion articulo"


def _obligacion_from_row(row: Any) -> ObligacionItem:
    return ObligacionItem(
        descripcion=str(row["descripcion"]),
        obligacion_tipo=str(row["obligacion_tipo"]),
        periodicidad=row["periodicidad"],
        plazo_descripcion=row["plazo_descripcion"],
        modelo_aeat=row["modelo_aeat"],
        norma_codigo=row["norma_codigo"],
        articulo_referencia=row["articulo_referencia"],
        fuente_secundaria=row["fuente_secundaria"],
        verified=bool(row["verified"]),
        completeness=str(row["completeness"]),
        source_url=str(row["source_url"]),
        evidence_notice=_evidence_notice(row),
    )


def obtener_obligaciones_perfil(
    db: Session,
    perfil_codigo: str,
    dominio: DominioPerfil = "ALL",
) -> ObligacionesResponse:
    perfil = _get_perfil(db, perfil_codigo)
    domain_filter = DOMAIN_FILTERS.get(dominio)
    if domain_filter is None:
        raise ValueError(f"Dominio no soportado: {dominio}")

    rows = db.execute(
        text(
            f"""
            SELECT
                op.id,
                op.obligacion_tipo,
                op.descripcion,
                op.periodicidad,
                op.plazo_descripcion,
                op.modelo_aeat,
                op.norma_codigo,
                op.articulo_referencia,
                op.fuente_secundaria,
                op.verified,
                op.completeness,
                op.source_url
            FROM obligacion_perfil op
            WHERE op.perfil_codigo = :perfil_codigo
              AND op.source_url IS NOT NULL
              AND op.source_url <> ''
              AND {domain_filter}
            ORDER BY op.obligacion_tipo, op.descripcion
            """
        ),
        {"perfil_codigo": perfil_codigo},
    ).mappings().all()

    obligaciones = [_obligacion_from_row(row) for row in rows]
    return ObligacionesResponse(
        perfil=perfil,
        dominio_filtrado=dominio,
        obligaciones=obligaciones,
    )


def build_calendario_response(
    *,
    perfil: PerfilResumen,
    obligaciones: list[ObligacionItem],
) -> CalendarioResponse:
    calendario: dict[Periodicidad, list[ObligacionItem]] = {
        periodicidad: [] for periodicidad in CALENDARIO_PERIODICIDADES
    }
    for obligacion in obligaciones:
        periodicidad = obligacion.periodicidad
        if periodicidad not in calendario:
            periodicidad = "ad_hoc"
        calendario[periodicidad].append(obligacion)  # type: ignore[index]
    return CalendarioResponse(perfil=perfil, calendario=calendario)


def calendario_obligaciones_perfil(db: Session, perfil_codigo: str) -> CalendarioResponse:
    response = obtener_obligaciones_perfil(db, perfil_codigo, "ALL")
    return build_calendario_response(perfil=response.perfil, obligaciones=response.obligaciones)
