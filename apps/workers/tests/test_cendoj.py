from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cendoj import build_document_payload


CENDOJ_HTML = b"""
<html>
  <body>
    <h1>Sentencia del Tribunal Supremo 12345/2024</h1>
    <p>Recurso sobre IVA y obligacion tributaria.</p>
  </body>
</html>
"""


def test_build_document_payload_extracts_court_type_and_ambito():
    payload = build_document_payload(
        "https://www.poderjudicial.es/search/AN/openDocument/abc123",
        CENDOJ_HTML,
    )

    assert payload["tipo_fuente"] == "cendoj"
    assert payload["tipo_documento"] == "sentencia"
    assert payload["court"] == "tribunal_supremo"
    assert payload["ambito"] == "jurisprudencia_tributaria"
    assert payload["referencia"] == "CENDOJ-abc123"
