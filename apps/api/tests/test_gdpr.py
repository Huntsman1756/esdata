"""Tests for GDPR ARCO requests and DPIA (Fase 26.10)."""

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.gdpr import (
    GDPRService,
    ARCOType,
    ARCOStatus,
    get_gdpr_service,
    reset_gdpr_service,
)


@pytest.fixture(autouse=True)
def clean_service():
    reset_gdpr_service()
    yield
    reset_gdpr_service()


# ---------------------------------------------------------------------------
# ARCO request creation
# ---------------------------------------------------------------------------


class TestCreateARCORequest:
    def test_create_acceso_request(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="Datos de busqueda y resultados",
            solicitante="user@example.com",
        )
        assert req.request_id.startswith("gdpr-")
        assert req.estado == ARCOStatus.PENDIENTE
        assert req.solicitante == "user@example.com"
        assert req.tipo_solicitud == ARCOType.ACCESO

    def test_create_supresion_request(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.SUPRESION,
            datos_afectados="Historial de consultas",
            solicitante="user@example.com",
        )
        assert req.tipo_solicitud == ARCOType.SUPRESION

    def test_create_all_arco_types(self):
        service = get_gdpr_service()
        for tipo in ARCOType:
            req = service.create_arco_request(
                tipo=tipo,
                datos_afectados="test",
                solicitante="user@example.com",
            )
            assert req.tipo_solicitud == tipo

    def test_multiple_requests(self):
        service = get_gdpr_service()
        r1 = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="d1",
            solicitante="u1@example.com",
        )
        r2 = service.create_arco_request(
            tipo=ARCOType.SUPRESION,
            datos_afectados="d2",
            solicitante="u2@example.com",
        )
        assert r1.request_id != r2.request_id
        assert service.total_requests == 2


# ---------------------------------------------------------------------------
# Request retrieval
# ---------------------------------------------------------------------------


class TestRequestRetrieval:
    def test_get_by_id(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="d",
            solicitante="u@example.com",
        )
        found = service.get_request(req.request_id)
        assert found is not None
        assert found.request_id == req.request_id

    def test_get_nonexistent(self):
        service = get_gdpr_service()
        assert service.get_request("gdpr-999999") is None

    def test_get_all_requests(self):
        service = get_gdpr_service()
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u1")
        service.create_arco_request(tipo=ARCOType.SUPRESION, datos_afectados="d", solicitante="u2")
        all_reqs = service.get_all_requests()
        assert len(all_reqs) == 2

    def test_filter_by_status(self):
        service = get_gdpr_service()
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u1")
        service.create_arco_request(tipo=ARCOType.SUPRESION, datos_afectados="d", solicitante="u2")
        pending = service.get_all_requests(estado=ARCOStatus.PENDIENTE)
        assert len(pending) == 2

    def test_list_all_pending(self):
        service = get_gdpr_service()
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u1")
        pending = service.get_pending_requests()
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# Fulfilling requests
# ---------------------------------------------------------------------------


class TestFulfillRequest:
    def test_fulfill_completada(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="d",
            solicitante="u@example.com",
        )
        fulfilled = service.fulfill_arco_request(
            request_id=req.request_id,
            estado="completada",
            respuesta="Se proporcionan los datos solicitados",
        )
        assert fulfilled is not None
        assert fulfilled.estado == ARCOStatus.COMPLETADA
        assert fulfilled.respuesta == "Se proporcionan los datos solicitados"
        assert fulfilled.fecha_respuesta is not None

    def test_fulfill_rechazada(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.SUPRESION,
            datos_afectados="d",
            solicitante="u@example.com",
        )
        fulfilled = service.fulfill_arco_request(
            request_id=req.request_id,
            estado="rechazada",
            respuesta="No se encuentran datos que suprimir",
        )
        assert fulfilled.estado == ARCOStatus.RECHAZADA

    def test_fulfill_nonexistent(self):
        service = get_gdpr_service()
        assert service.fulfill_arco_request("gdpr-999999") is None

    def test_fulfill_invalid_status(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="d",
            solicitante="u@example.com",
        )
        with pytest.raises(ValueError):
            service.fulfill_arco_request(
                request_id=req.request_id,
                estado="invalido",
            )

    def test_fulfill_sets_response_date(self):
        service = get_gdpr_service()
        req = service.create_arco_request(
            tipo=ARCOType.ACCESO,
            datos_afectados="d",
            solicitante="u@example.com",
        )
        service.fulfill_arco_request(
            request_id=req.request_id,
            estado="completada",
        )
        updated = service.get_request(req.request_id)
        assert updated.fecha_respuesta is not None
        assert updated.fecha_solicitud is not None


# ---------------------------------------------------------------------------
# DPIA summary
# ---------------------------------------------------------------------------


class TestDPIA:
    def test_get_dpia_summary(self):
        service = get_gdpr_service()
        summary = service.get_dpia_summary()
        assert "tratamiento_descripcion" in summary
        assert "datos_personales" in summary
        assert "medidas_mitigacion" in summary
        assert "ultima_actualizacion" in summary
        assert summary["requiere_consulta_aepd"] is False

    def test_dpia_includes_high_risk_components(self):
        service = get_gdpr_service()
        summary = service.get_dpia_summary()
        # Check that key data categories are present
        assert "email" in summary["datos_personales"]
        assert "ip_address" in summary["datos_personales"]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_total_requests(self):
        service = get_gdpr_service()
        assert service.total_requests == 0
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u")
        service.create_arco_request(tipo=ARCOType.SUPRESION, datos_afectados="d", solicitante="u")
        assert service.total_requests == 2

    def test_count_by_type(self):
        service = get_gdpr_service()
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u1")
        service.create_arco_request(tipo=ARCOType.ACCESO, datos_afectados="d", solicitante="u2")
        service.create_arco_request(tipo=ARCOType.SUPRESION, datos_afectados="d", solicitante="u3")
        counts = service.get_request_count_by_type()
        assert counts[ARCOType.ACCESO] == 2
        assert counts[ARCOType.SUPRESION] == 1

    def test_count_empty(self):
        service = get_gdpr_service()
        counts = service.get_request_count_by_type()
        assert counts == {}
