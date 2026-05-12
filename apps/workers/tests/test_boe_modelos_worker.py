import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_sync_orden_hac_to_db():
    """Verify sync_orden_hac_to_db orchestrates all 3 layers and returns success."""
    from boe_modelos_worker import sync_orden_hac_to_db, OrdenSyncResult

    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<documento id="BOE-A-2024-16738">
  <metadatos>
    <titulo>Orden HAC/891/2024, de 13 de diciembre. Modelo 303, modelo 036.</titulo>
    <url_eli>https://www.boe.es/eli/es/res/2024/12/13/891</url_eli>
  </metadatos>
  <texto>
    <p>Se debera rellenar la casilla 001 del ANEXO I para indicar el importe total.</p>
    <p>Asimismo, la casilla 002 corresponde a las devoluciones.</p>
    <p>La casilla 003 se utilizara para registrar datos de identificacion.</p>
    <p>La Casilla 004 contendra la referencia ante la AEAT.</p>
  </texto>
</documento>"""

    mock_pdf_result = {
        "success": True,
        "casillas": [{"codigo": "0005", "descripcion": "Casilla PDF 005"}],
        "total_pages": 3,
        "text_length": 2400,
    }

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_cursor = MagicMock()
    mock_cursor.mappings = MagicMock(return_value=MagicMock(**{"first": MagicMock(return_value={"id": 42})}))
    mock_conn.execute = MagicMock(return_value=mock_cursor)

    mock_engine.begin = MagicMock(return_value=mock_conn)
    mock_engine.url = MagicMock()
    mock_engine.url.__str__ = MagicMock(return_value="postgresql://test")

    with patch("boe_modelos_worker._fetch_boe_xml", return_value=xml_content), \
         patch("boe_modelos_worker.download_and_parse_boe_pdf", return_value=mock_pdf_result), \
         patch("boe_modelos_worker.create_engine", return_value=mock_engine):

        result = sync_orden_hac_to_db("BOE-A-2024-16738", "postgresql://test")

    assert isinstance(result, OrdenSyncResult)
    assert result.success is True
    assert result.boe_id == "BOE-A-2024-16738"
    assert "303" in result.modelo_codigos
    assert "036" in result.modelo_codigos
    assert len(result.casillas_parsed) == 8
    assert result.campana_id == 42
    assert len(result.pdf_casillas) == 1
    assert result.errors == []

    mock_engine.begin.assert_called()
    mock_conn.execute.assert_called()


def test_sync_orden_hac_to_db_error():
    """Test error handling when BOE fetch fails."""
    from boe_modelos_worker import sync_orden_hac_to_db, OrdenSyncResult

    import httpx

    with patch(
        "boe_modelos_worker._fetch_boe_xml",
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        ),
    ):
        result = sync_orden_hac_to_db("BOE-A-9999-99999", "postgresql://test")

    assert isinstance(result, OrdenSyncResult)
    assert result.success is False
    assert result.boe_id == "BOE-A-9999-99999"
    assert len(result.errors) > 0
    assert "404" in result.errors[0]


def test_run_sync_once():
    """Mock run_sync with run_once=True and verify loop behavior."""
    from boe_modelos_worker import run_sync, OrdenSyncResult

    mock_engine = MagicMock()
    mock_conn = MagicMock()

    # Lock acquisition succeeds
    mock_cursor = MagicMock()
    mock_cursor.fetchone = MagicMock(return_value=[True])
    mock_cursor.mappings = MagicMock(return_value=MagicMock(**{"first": MagicMock(return_value={"id": 42})}))
    mock_conn.execute = MagicMock(return_value=mock_cursor)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine.begin = MagicMock(return_value=mock_conn)
    mock_engine.url = MagicMock()
    mock_engine.url.__str__ = MagicMock(return_value="postgresql://test")

    mock_result = OrdenSyncResult(
        success=True,
        boe_id="BOE-A-2024-16738",
        modelo_codigos=["303", "036"],
        casillas_parsed=[{"codigo": "0001", "descripcion": "Test"}],
        pdf_casillas=[],
        errors=[],
        campana_id=42,
    )

    with patch("boe_modelos_worker.find_orden_boe_ids", return_value=["BOE-A-2024-16738"]), \
         patch("boe_modelos_worker.sync_orden_hac_to_db", return_value=mock_result), \
         patch("boe_modelos_worker.create_engine", return_value=mock_engine), \
         patch("boe_modelos_worker.sleep_with_heartbeat"):

        result = run_sync(mock_engine, run_once=True)

    assert result["synced"] == 1
    assert result["errors"] == 0

    mock_engine.begin.assert_called()


def test_run_sync_does_not_mark_successful_empty_order_as_partial():
    """A BOE order with no parseable casillas is still a successful sync."""
    from boe_modelos_worker import OrdenSyncResult, run_sync

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone = MagicMock(return_value=[True])
    mock_conn.execute = MagicMock(return_value=mock_cursor)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_engine.begin = MagicMock(return_value=mock_conn)
    mock_engine.url.render_as_string = MagicMock(return_value="postgresql://test")

    sync_calls = []
    mock_result = OrdenSyncResult(
        success=True,
        boe_id="BOE-A-1993-25359",
        modelo_codigos=[],
        casillas_parsed=[],
        pdf_casillas=[],
        errors=[],
    )

    with patch("boe_modelos_worker.find_orden_boe_ids", return_value=["BOE-A-1993-25359"]), \
         patch("boe_modelos_worker.sync_orden_hac_to_db", return_value=mock_result), \
         patch("boe_modelos_worker._log_sync", side_effect=lambda *args, **kwargs: sync_calls.append(args)):
        result = run_sync(mock_engine, run_once=True)

    assert result == {"synced": 1, "errors": 0}
    assert sync_calls[-1][2] == "ok"
