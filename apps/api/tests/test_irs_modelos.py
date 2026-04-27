"""Tests para el servicio y router de IRS modelos."""

from unittest.mock import MagicMock

from services import irs as irs_svc


class TestListIrsModels:
    """Pruebas para list_irs_models."""

    def test_devuelve_listado_vacio_sin_filtros(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        result = irs_svc.list_irs_models(db)
        assert result == []
        db.execute.assert_called_once()

    def test_filtra_por_periodo(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        irs_svc.list_irs_models(db, periodo="anual")
        args = db.execute.call_args
        assert args[0][1]["periodo"] == "anual"

    def test_filtra_por_impuesto(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        irs_svc.list_irs_models(db, impuesto="Payroll Tax")
        args = db.execute.call_args
        assert args[0][1]["impuesto"] == "Payroll Tax"

    def test_filtra_por_activo(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        irs_svc.list_irs_models(db, activo=True)
        args = db.execute.call_args
        assert args[0][1]["activo"] is True

    def test_activo_false_omite_filtro(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        irs_svc.list_irs_models(db, activo=False)
        args = db.execute.call_args
        assert "activo" not in args[0][1]

    def test_convierte_rows_a_dicts(self):
        db = MagicMock()
        mock_row = {"id": 1, "codigo": "1040", "nombre": "Individual Income Tax Return", "periodo": "anual", "impuesto": "Income Tax", "url_info": "https://www.irs.gov/1040", "activo": True}
        db.execute.return_value.mappings.return_value = [mock_row]
        result = irs_svc.list_irs_models(db)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["codigo"] == "1040"


class TestGetIrsModel:
    """Pruebas para get_irs_model."""

    def test_devuelve_none_si_no_existe(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        result = irs_svc.get_irs_model(db, "999")
        assert result is None

    def test_devuelve_modelo_por_codigo(self):
        db = MagicMock()
        mock_row = {"id": 1, "codigo": "1040", "nombre": "Individual Income Tax Return", "periodo": "anual", "impuesto": "Income Tax", "url_info": "https://www.irs.gov/1040", "activo": True}
        db.execute.return_value.mappings.return_value.first.return_value = mock_row
        result = irs_svc.get_irs_model(db, "1040")
        assert result is not None
        assert result["codigo"] == "1040"
        assert result["nombre"] == "Individual Income Tax Return"

    def test_filtra_por_codigo(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        irs_svc.get_irs_model(db, "1120")
        args = db.execute.call_args
        assert args[0][1]["codigo"] == "1120"
