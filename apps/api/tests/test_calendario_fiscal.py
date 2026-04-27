"""Tests para el servicio y router de calendario fiscal."""

from unittest.mock import MagicMock, patch

from services import calendario_fiscal as cf


class TestListCalendario:
    """Pruebas para list_calendario."""

    def test_devuelve_listado_vacio_sin_filtros(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        result = cf.list_calendario(db)
        assert result == []
        db.execute.assert_called_once()

    def test_filtra_por_codigo(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.list_calendario(db, codigo="100")
        args = db.execute.call_args
        assert args[0][1]["codigo"] == "100"

    def test_filtra_por_campana(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.list_calendario(db, campana="2025")
        args = db.execute.call_args
        assert args[0][1]["campana"] == "2025"

    def test_filtra_por_rango_fechas(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.list_calendario(db, desde="2025-01-01", hasta="2025-12-31")
        args = db.execute.call_args
        assert args[0][1]["desde"] == "2025-01-01"
        assert args[0][1]["hasta"] == "2025-12-31"

    def test_incluye_activo_por_defecto(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.list_calendario(db)
        args = db.execute.call_args
        assert args[0][1]["activo"] is True

    def test_activo_false_omite_filtro(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.list_calendario(db, activo=False)
        args = db.execute.call_args
        assert "activo" not in args[0][1]


class TestGetProximoVencimiento:
    """Pruebas para get_proximo_vencimiento."""

    def test_devuelve_none_sin_resultados(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        result = cf.get_proximo_vencimiento(db)
        assert result is None

    def test_devuelve_siguiente_vencimiento(self):
        db = MagicMock()
        mock_row = {"modelo_codigo": "100", "fecha_limite": "2026-04-01", "estado": "pronto"}
        db.execute.return_value.mappings.return_value.first.return_value = mock_row
        result = cf.get_proximo_vencimiento(db)
        assert result is not None
        assert result["modelo_codigo"] == "100"
        assert result["estado"] == "pronto"


class TestGetCalendarioModelo:
    """Pruebas para get_calendario_modelo."""

    def test_devuelve_listado_vacio_si_no_hay_datos(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        result = cf.get_calendario_modelo(db, "999")
        assert result == []

    def test_filtra_por_codigo(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.get_calendario_modelo(db, "100")
        args = db.execute.call_args
        assert args[0][1]["codigo"] == "100"

    def test_filtra_por_codigo_y_campana(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value = []
        cf.get_calendario_modelo(db, "303", campana="2025-T1")
        args = db.execute.call_args
        assert args[0][1]["codigo"] == "303"
        assert args[0][1]["campana"] == "2025-T1"

    def test_incluye_estado(self):
        db = MagicMock()
        mock_row = {"modelo_codigo": "100", "estado": "futuro"}
        db.execute.return_value.mappings.return_value = [mock_row]
        result = cf.get_calendario_modelo(db, "100")
        assert len(result) == 1
        assert result[0]["estado"] == "futuro"
