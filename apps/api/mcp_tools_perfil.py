from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
