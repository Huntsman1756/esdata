"""Tests para el router de Ley 10/2010 PBC (Prevencion Blanqueo de Capitales).

Cubre: obligated subjects, internal controls, suspicious activity reports, beneficial owners.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

# --- Seed de datos PBC ---


PBC_SEED_SQL = [
    """
    INSERT INTO pbc_obligated_subject (subject_type, tin, registration_number, supervisory_authority, pbc_license, status)
    VALUES ('credit entity', 'ESA11111111', 'CE-001', 'Banco de Espana', 'LIC-001', 'active')
    """,
    """
    INSERT INTO pbc_obligated_subject (subject_type, tin, registration_number, supervisory_authority, pbc_license, status)
    VALUES ('lawyer', 'ESA22222222', 'LN-001', 'ICAM', 'LIC-002', 'active')
    """,
    """
    INSERT INTO pbc_obligated_subject (subject_type, tin, registration_number, supervisory_authority, pbc_license, status)
    VALUES ('real_estate_agency', 'ESA33333333', 'REA-001', 'Banco de Espana', 'LIC-003', 'active')
    """,
    """
    INSERT INTO pbc_obligated_subject (subject_type, tin, registration_number, supervisory_authority, pbc_license, status)
    VALUES ('casino', 'ESA44444444', 'CAS-001', 'Banco de Espana', 'LIC-004', 'suspended')
    """,
    """
    INSERT INTO pbc_internal_control (obligated_subject_id, risk_assessment_date, compliance_officer, internal_reporting_channel, training_program, audit_trail)
    VALUES (1, '2025-01-15', 'Juan Garcia', true, true, true)
    """,
    """
    INSERT INTO pbc_internal_control (obligated_subject_id, risk_assessment_date, compliance_officer, internal_reporting_channel, training_program, audit_trail)
    VALUES (2, '2025-03-01', 'Maria Lopez', true, false, true)
    """,
    """
    INSERT INTO suspicious_activity_report (obligated_subject_id, submission_date, description, severity, status, sepblac_reference)
    VALUES (1, '2025-06-15', 'Operaciones inusuales de transferencias internacionales', 'high', 'under_review', 'SEP-2025-001')
    """,
    """
    INSERT INTO suspicious_activity_report (obligated_subject_id, submission_date, description, severity, status, sepblac_reference)
    VALUES (1, '2025-07-20', 'Posible structuración de depósitos', 'critical', 'filed', 'SEP-2025-002')
    """,
    """
    INSERT INTO suspicious_activity_report (obligated_subject_id, submission_date, description, severity, status, sepblac_reference)
    VALUES (2, '2025-08-01', 'Consultoría para estructura offshore', 'medium', 'investigated', 'SEP-2025-003')
    """,
    """
    INSERT INTO beneficial_owner_record (entity_id, owner_name, ownership_percentage, acquisition_date, verification_method, verification_date)
    VALUES (1, 'Carlos Fernandez', 45.50, '2024-01-10', 'certificado_notarial', '2024-01-15')
    """,
    """
    INSERT INTO beneficial_owner_record (entity_id, owner_name, ownership_percentage, acquisition_date, verification_method, verification_date)
    VALUES (1, 'Inversiones ABC S.L.', 30.00, '2024-01-10', 'registro_mercantil', '2024-01-20')
    """,
    """
    INSERT INTO beneficial_owner_record (entity_id, owner_name, ownership_percentage, acquisition_date, verification_method, verification_date)
    VALUES (2, 'Ana Martinez', 100.00, '2023-06-01', 'declaracion_hurada', '2023-06-05')
    """,
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_pbc():
    """Semilla basica de datos PBC para tests del router."""
    from db import engine

    with engine.begin() as conn:
        for sql in PBC_SEED_SQL:
            conn.execute(text(sql))

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM beneficial_owner_record"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='beneficial_owner_record'"))
        conn.execute(text("DELETE FROM suspicious_activity_report"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='suspicious_activity_report'"))
        conn.execute(text("DELETE FROM pbc_internal_control"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='pbc_internal_control'"))
        conn.execute(text("DELETE FROM pbc_obligated_subject"))
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='pbc_obligated_subject'"))


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ====================================================================
# Test: GET /v1/pbc/obligated-subjects (lista)
# ====================================================================


class TestPbcListObligatedSubjects:
    @pytest.mark.asyncio
    async def test_obligated_subjects_lista_status_200(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_obligated_subjects_lista_response_model(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects")
        data = resp.json()
        assert "subjects" in data
        assert isinstance(data["subjects"], list)

    @pytest.mark.asyncio
    async def test_obligated_subjects_lista_contiene_registros(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects")
        data = resp.json()
        assert len(data["subjects"]) >= 4

    @pytest.mark.asyncio
    async def test_obligated_subjects_campos(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects")
        data = resp.json()
        for s in data["subjects"]:
            assert "id" in s
            assert "subject_type" in s
            assert "tin" in s
            assert "registration_number" in s
            assert "supervisory_authority" in s
            assert "status" in s

    @pytest.mark.asyncio
    async def test_obligated_subjects_filtro_subject_type(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects", params={"subject_type": "credit entity"})
        data = resp.json()
        assert len(data["subjects"]) >= 1
        for s in data["subjects"]:
            assert s["subject_type"] == "credit entity"

    @pytest.mark.asyncio
    async def test_obligated_subjects_filtro_supervisory_authority(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects", params={"supervisory_authority": "ICAM"})
        data = resp.json()
        assert len(data["subjects"]) >= 1
        for s in data["subjects"]:
            assert s["supervisory_authority"] == "ICAM"

    @pytest.mark.asyncio
    async def test_obligated_subjects_filtro_status(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects", params={"status": "suspended"})
        data = resp.json()
        assert len(data["subjects"]) >= 1
        for s in data["subjects"]:
            assert s["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_obligated_subjects_filtro_search(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects", params={"search": "ESA111"})
        data = resp.json()
        assert len(data["subjects"]) >= 1


# ====================================================================
# Test: GET /v1/pbc/obligated-subjects/{id} (detalle)
# ====================================================================


class TestPbcGetObligatedSubject:
    @pytest.mark.asyncio
    async def test_obligated_subject_detalle_status_200(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_obligated_subject_detalle_tin(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects/1")
        data = resp.json()
        assert data["tin"] == "ESA11111111"

    @pytest.mark.asyncio
    async def test_obligated_subject_detalle_404(self, client):
        resp = await client.get("/v1/pbc/obligated-subjects/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/pbc/internal-controls (lista)
# ====================================================================


class TestPbcListInternalControls:
    @pytest.mark.asyncio
    async def test_internal_controls_lista_status_200(self, client):
        resp = await client.get("/v1/pbc/internal-controls")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_internal_controls_lista_response_model(self, client):
        resp = await client.get("/v1/pbc/internal-controls")
        data = resp.json()
        assert "controls" in data
        assert len(data["controls"]) >= 2

    @pytest.mark.asyncio
    async def test_internal_controls_campos(self, client):
        resp = await client.get("/v1/pbc/internal-controls")
        data = resp.json()
        for c in data["controls"]:
            assert "id" in c
            assert "obligated_subject_id" in c
            assert "compliance_officer" in c
            assert "internal_reporting_channel" in c

    @pytest.mark.asyncio
    async def test_internal_controls_filtro_obligated_subject_id(self, client):
        resp = await client.get("/v1/pbc/internal-controls", params={"obligated_subject_id": "1"})
        data = resp.json()
        assert len(data["controls"]) >= 1
        for c in data["controls"]:
            assert c["obligated_subject_id"] == 1


# ====================================================================
# Test: GET /v1/pbc/internal-controls/{id} (detalle)
# ====================================================================


class TestPbcGetInternalControl:
    @pytest.mark.asyncio
    async def test_internal_control_detalle_status_200(self, client):
        resp = await client.get("/v1/pbc/internal-controls/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_internal_control_detalle_404(self, client):
        resp = await client.get("/v1/pbc/internal-controls/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/pbc/suspicious-reports (lista)
# ====================================================================


class TestPbcListSuspiciousReports:
    @pytest.mark.asyncio
    async def test_suspicious_reports_lista_status_200(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_suspicious_reports_lista_response_model(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["reports"]) == 3
        assert data["reports"][0]["sepblac_reference"].startswith("SEP-2025-")

    @pytest.mark.asyncio
    async def test_suspicious_reports_campos(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports")
        data = resp.json()
        for r in data["reports"]:
            assert "id" in r
            assert "obligated_subject_id" in r
            assert "submission_date" in r
            assert "severity" in r
            assert "status" in r
            assert "sepblac_reference" in r

    @pytest.mark.asyncio
    async def test_suspicious_reports_filtro_status(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports", params={"status": "filed"})
        data = resp.json()
        assert data["total"] == 1
        for r in data["reports"]:
            assert r["status"] == "filed"

    @pytest.mark.asyncio
    async def test_suspicious_reports_filtro_severity(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports", params={"severity": "critical"})
        data = resp.json()
        assert data["total"] == 1
        for r in data["reports"]:
            assert r["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_suspicious_reports_filtro_search(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports", params={"search": "SEP-2025-001"})
        data = resp.json()
        assert data["total"] == 1
        assert data["reports"][0]["sepblac_reference"] == "SEP-2025-001"


# ====================================================================
# Test: GET /v1/pbc/suspicious-reports/{id} (detalle)
# ====================================================================


class TestPbcGetSuspiciousReport:
    @pytest.mark.asyncio
    async def test_suspicious_report_detalle_status_200(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_suspicious_report_detalle_severity(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports/1")
        data = resp.json()
        assert data["severity"] == "high"

    @pytest.mark.asyncio
    async def test_suspicious_report_detalle_404(self, client):
        resp = await client.get("/v1/pbc/suspicious-reports/9999")
        assert resp.status_code == 404


# ====================================================================
# Test: GET /v1/pbc/beneficial-owners (lista)
# ====================================================================


class TestPbcListBeneficialOwners:
    @pytest.mark.asyncio
    async def test_beneficial_owners_lista_status_200(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_beneficial_owners_lista_response_model(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners")
        data = resp.json()
        assert "records" in data
        assert len(data["records"]) >= 3

    @pytest.mark.asyncio
    async def test_beneficial_owners_campos(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners")
        data = resp.json()
        for r in data["records"]:
            assert "id" in r
            assert "entity_id" in r
            assert "owner_name" in r
            assert "ownership_percentage" in r
            assert "verification_method" in r

    @pytest.mark.asyncio
    async def test_beneficial_owners_filtro_entity_id(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners", params={"entity_id": "1"})
        data = resp.json()
        assert len(data["records"]) >= 2
        for r in data["records"]:
            assert r["entity_id"] == 1

    @pytest.mark.asyncio
    async def test_beneficial_owners_filtro_search(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners", params={"search": "Carlos"})
        data = resp.json()
        assert len(data["records"]) >= 1
        for r in data["records"]:
            assert "Carlos" in r["owner_name"]


# ====================================================================
# Test: GET /v1/pbc/beneficial-owners/{id} (detalle)
# ====================================================================


class TestPbcGetBeneficialOwner:
    @pytest.mark.asyncio
    async def test_beneficial_owner_detalle_status_200(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners/1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_beneficial_owner_detalle_name(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners/1")
        data = resp.json()
        assert "Carlos" in data["owner_name"]

    @pytest.mark.asyncio
    async def test_beneficial_owner_detalle_404(self, client):
        resp = await client.get("/v1/pbc/beneficial-owners/9999")
        assert resp.status_code == 404
