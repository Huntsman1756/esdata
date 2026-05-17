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

QUARTER_MONTHS: dict[str, dict[str, object]] = {
    "Q1": {"meses": (1, 2, 3), "vencimientos_mes_sig": 4},
    "Q2": {"meses": (4, 5, 6), "vencimientos_mes_sig": 7},
    "Q3": {"meses": (7, 8, 9), "vencimientos_mes_sig": 10},
    "Q4": {"meses": (10, 11, 12), "vencimientos_mes_sig": 1},
}


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


class CalendarioQuarterResponse(BaseModel):
    perfil: PerfilResumen
    quarter: str
    obligaciones: list[ObligacionItem]
    total: int = 0

    @model_validator(mode="after")
    def derive_total(self) -> CalendarioQuarterResponse:
        self.total = len(self.obligaciones)
        return self


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
        "usar obtener_obligaciones_perfil para eso. Si se proporciona el parametro quarter "
        "(ej: 2026-Q3), devuelve solo las obligaciones con vencimiento en ese trimestre "
        "segun periodicidad y plazo_descripcion estructurados."
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
        "quarter": {
            "type": "string",
            "required": False,
            "description": "Trimestre a consultar: Q1, Q2, Q3, Q4 o YYYY-QN, ej: 2026-Q3",
        },
    },
    returns="CalendarioResponse | CalendarioQuarterResponse",
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
        notice = f"Verificado contra {norma} {articulo}".strip()
        if str(row["completeness"]) == "parcial":
            return f"{notice} (condicional)"
        return notice
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


def normalize_quarter(quarter: str) -> str:
    value = quarter.strip().upper()
    if "-" in value:
        value = value.rsplit("-", 1)[-1]
    if value not in QUARTER_MONTHS:
        raise ValueError(f"Trimestre no soportado: {quarter}")
    return value


def _is_due_in_quarter(obligacion: ObligacionItem, quarter: str) -> bool:
    if not obligacion.plazo_descripcion:
        return False
    periodicidad = obligacion.periodicidad
    if periodicidad == "mensual":
        return True
    if periodicidad == "continua":
        return True
    if periodicidad != "trimestral":
        return False

    # Modelo 202 has three statutory instalments: April (Q2), October and
    # December (Q4). It is not due in Q1 or Q3.
    if obligacion.modelo_aeat == "202":
        return quarter in {"Q2", "Q4"}

    return True


def build_calendario_quarter_response(
    *,
    perfil: PerfilResumen,
    obligaciones: list[ObligacionItem],
    quarter: str,
) -> CalendarioQuarterResponse:
    quarter_key = normalize_quarter(quarter)
    due = [
        obligacion
        for obligacion in obligaciones
        if obligacion.periodicidad in {"mensual", "trimestral", "continua"}
        and _is_due_in_quarter(obligacion, quarter_key)
    ]
    return CalendarioQuarterResponse(perfil=perfil, quarter=quarter_key, obligaciones=due)


def calendario_obligaciones_perfil(
    db: Session,
    perfil_codigo: str,
    quarter: str | None = None,
) -> CalendarioResponse | CalendarioQuarterResponse:
    response = obtener_obligaciones_perfil(db, perfil_codigo, "ALL")
    if quarter:
        return build_calendario_quarter_response(
            perfil=response.perfil,
            obligaciones=response.obligaciones,
            quarter=quarter,
        )
    return build_calendario_response(perfil=response.perfil, obligaciones=response.obligaciones)
