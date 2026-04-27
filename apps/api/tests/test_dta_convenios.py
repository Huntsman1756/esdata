"""Tests for DTA Conventions & Withholding Rules router (Fase 25.8)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# DTA Conventions
# ---------------------------------------------------------------------------


class TestListarConveniosDTA:
    def test_devuelve_listado(self):
        resp = client.get("/v1/internacional/convenios")
        assert resp.status_code == 200
        data = resp.json()
        assert "convenios" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_filtra_por_pais_a(self):
        resp = client.get("/v1/internacional/convenios", params={"pais_a": "US"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for c in data["convenios"]:
            assert c["pais_origen"] == "US"

    def test_filtra_por_pais_b(self):
        resp = client.get("/v1/internacional/convenios", params={"pais_b": "ES"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for c in data["convenios"]:
            assert c["pais_destino"] == "ES"

    def test_filtra_por_estado(self):
        resp = client.get(
            "/v1/internacional/convenios", params={"estado": "vigente"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_filtra_por_tipo_acuerdo(self):
        resp = client.get(
            "/v1/internacional/convenios",
            params={"tipo_acuerdo": "bilateral"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for c in data["convenios"]:
            assert c["tipo_acuerdo"] == "bilateral"


class TestDetalleConvenioDTA:
    def test_detalle_existente(self):
        resp = client.get("/v1/internacional/convenios/ES_US_DTA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["codigo"] == "ES_US_DTA"
        assert data["pais_origen"] == "US"
        assert data["pais_destino"] == "ES"

    def test_detalle_no_existe_404(self):
        resp = client.get("/v1/internacional/convenios/XX_YY_DTA")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Withholding Rules
# ---------------------------------------------------------------------------


class TestListarReglasRetencion:
    def test_devuelve_listado(self):
        resp = client.get("/v1/internacional/convenios/retenciones")
        assert resp.status_code == 200
        data = resp.json()
        assert "reglas" in data
        assert "total" in data
        assert data["total"] >= 4

    def test_filtra_por_tipo_renta(self):
        resp = client.get(
            "/v1/internacional/convenios/retenciones",
            params={"tipo_renta": "dividends"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for r in data["reglas"]:
            assert r["tipo_renta"] == "dividends"

    def test_filtra_por_pais(self):
        resp = client.get(
            "/v1/internacional/convenios/retenciones",
            params={"pais": "US"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 0

    def test_filtra_por_estado(self):
        resp = client.get(
            "/v1/internacional/convenios/retenciones",
            params={"estado": "activo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for r in data["reglas"]:
            assert r["estado"] == "activo"


class TestDetalleReglaRetencion:
    def test_detalle_existente(self):
        resp = client.get("/v1/internacional/convenios/retenciones/DIVIDEND")
        assert resp.status_code == 200
        data = resp.json()
        assert data["codigo"] == "DIVIDEND"
        assert data["tipo_renta"] == "dividends"
        assert data["tipo_retencion_default"] == 30.0

    def test_detalle_no_existe_404(self):
        resp = client.get("/v1/internacional/convenios/retenciones/FAKE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Withholding Check
# ---------------------------------------------------------------------------


class TestCalcularRetencion:
    def test_con_dta_y_tasa_reducida(self):
        resp = client.post(
            "/v1/internacional/convenios/retencion",
            json={"pais_residencia": "US", "tipo_renta": "dividends"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tiene_convenio_dta"] is True
        assert data["codigo_convenio"] == "ES_US_DTA"
        assert data["tipo_retencion_aplicable"] == 15.0
        assert data["requiere_w8"] is True
        # Sin GIIN, no se puede determinar W-8BEN-E
        assert data["formulario_recomendado"] == "W-8BEN"

    def test_sin_dta_usa_default(self):
        resp = client.post(
            "/v1/internacional/convenios/retencion",
            json={"pais_residencia": "ZZ", "tipo_renta": "dividends"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tiene_convenio_dta"] is False
        assert data["tipo_retencion_aplicable"] == 30.0
        assert data["formulario_recomendado"] == "W-8BEN"

    def test_sin_pais_usa_default(self):
        resp = client.post(
            "/v1/internacional/convenios/retencion",
            json={"pais_residencia": None, "tipo_renta": "dividends"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tiene_convenio_dta"] is False
        assert data["tipo_retencion_aplicable"] == 30.0

    def test_con_giin_recomienda_w8ben_e(self):
        resp = client.post(
            "/v1/internacional/convenios/retencion",
            json={
                "pais_residencia": "US",
                "tipo_renta": "dividends",
                "entidad_giin": "FAKE_GIIN_001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["formulario_recomendado"] == "W-8BEN-E"

    def test_campos_respuesta(self):
        resp = client.post(
            "/v1/internacional/convenios/retencion",
            json={"pais_residencia": "US", "tipo_renta": "dividends"},
        )
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "pais_residencia",
            "tipo_renta",
            "tipo_retencion_aplicable",
            "tiene_convenio_dta",
            "codigo_convenio",
            "requiere_w8",
            "formulario_recomendado",
            "notas",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
