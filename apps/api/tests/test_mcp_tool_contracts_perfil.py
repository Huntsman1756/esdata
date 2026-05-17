from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_tools_perfil import (
    CALENDARIO_PERIODICIDADES,
    PERFIL_MCP_TOOL_CONTRACTS,
    ObligacionItem,
    ObligacionesResponse,
    PerfilResumen,
    build_calendario_response,
    _evidence_notice,
)


def _obligacion(*, verified: bool) -> ObligacionItem:
    return ObligacionItem(
        descripcion="Comunicacion de operaciones sospechosas al SEPBLAC",
        obligacion_tipo="COMUNICACION_INDICIO",
        periodicidad="ad_hoc",
        plazo_descripcion=None,
        modelo_aeat=None,
        norma_codigo="LEY10_2010",
        articulo_referencia="art. 18",
        fuente_secundaria=None,
        verified=verified,
        completeness="completa" if verified else "evidence_limited",
        source_url="https://www.boe.es/buscar/act.php?id=BOE-A-2010-6146",
        evidence_notice="Verificado contra LEY10_2010 art. 18"
        if verified
        else "evidence_limited: pendiente verificacion articulo",
    )


def test_obligacion_item_rejects_missing_source_url() -> None:
    with pytest.raises(ValidationError):
        ObligacionItem(
            descripcion="Modelo 200 - Impuesto sobre Sociedades",
            obligacion_tipo="AUTOLIQUIDACION",
            periodicidad="anual",
            plazo_descripcion=None,
            modelo_aeat="200",
            norma_codigo="LIS",
            articulo_referencia="art. 124",
            fuente_secundaria=None,
            verified=True,
            completeness="completa",
            evidence_notice="Verificado contra LIS art. 124",
        )


def test_obligaciones_response_marks_unsafe_when_more_than_30_percent_unverified() -> None:
    response = ObligacionesResponse(
        perfil=PerfilResumen(codigo="sociedad_valores", nombre="Sociedad de Valores", supervisor="CNMV"),
        dominio_filtrado="ALL",
        obligaciones=[_obligacion(verified=True), _obligacion(verified=False)],
    )

    assert response.total == 2
    assert response.verified_count == 1
    assert response.unverified_count == 1
    assert response.safe_to_answer is False
    assert "evidence_limited" in response.evidence_notice


def test_verified_partial_obligation_notice_is_conditional_not_evidence_limited() -> None:
    notice = _evidence_notice(
        {
            "verified": True,
            "norma_codigo": "LGT",
            "articulo_referencia": "DA 22. ap. 1",
            "completeness": "parcial",
        }
    )

    assert "Verificado contra LGT DA 22. ap. 1" in notice
    assert "condicional" in notice
    assert "evidence_limited" not in notice


def test_tool_descriptions_are_routing_grade() -> None:
    assert {contract.name for contract in PERFIL_MCP_TOOL_CONTRACTS} == {
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
    }
    for contract in PERFIL_MCP_TOOL_CONTRACTS:
        assert len(contract.description) > 50
        assert "No usar" in contract.description


def test_calendario_response_has_all_periodicidad_keys() -> None:
    response = build_calendario_response(
        perfil=PerfilResumen(codigo="sociedad_valores", nombre="Sociedad de Valores", supervisor="CNMV"),
        obligaciones=[_obligacion(verified=True)],
    )

    assert set(response.calendario.keys()) == set(CALENDARIO_PERIODICIDADES)
    assert response.calendario["ad_hoc"]
    assert response.calendario["anual"] == []
