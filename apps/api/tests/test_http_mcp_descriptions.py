from __future__ import annotations

from fastapi import FastAPI

from routers import modelos as modelos_router
from routers import norma as norma_router
from routers import perfil as perfil_router


def _openapi() -> dict:
    app = FastAPI()
    app.include_router(perfil_router.router)
    app.include_router(modelos_router.router)
    app.include_router(norma_router.router)
    return app.openapi()


def test_openapi_perfil_obligaciones_description_mentions_calendar_tool() -> None:
    spec = _openapi()
    description = spec["paths"]["/v1/perfil/{codigo}/obligaciones"]["get"]["description"]

    assert "calendario_obligaciones_perfil" in description


def test_openapi_calendario_description_contains_trigger() -> None:
    spec = _openapi()
    description = spec["paths"]["/v1/perfil/{codigo}/obligaciones/calendario"]["get"][
        "description"
    ]

    assert "este trimestre" in description


def test_openapi_modelos_catalogo_description_warns_not_obligation_source() -> None:
    spec = _openapi()
    description = spec["paths"]["/v1/modelos/catalogo"]["get"]["description"]

    assert "NO indica si una entidad tiene obligación" in description


def test_openapi_norma_eu_description_routes_away_from_profile_obligations() -> None:
    spec = _openapi()
    description = spec["paths"]["/v1/norma/eu"]["get"]["description"]

    assert "No usar para obtener obligaciones de una entidad" in description
    assert "obtener_obligaciones_perfil" in description
