from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eurlex import build_document_payload


EURLEX_HTML = b"""
<html>
  <body>
    <h1>Directive (EU) 2014/65 on markets in financial instruments</h1>
    <p>MiFID framework for markets in financial instruments and investor protection.</p>
  </body>
</html>
"""


def test_build_document_payload_extracts_reference_type_and_ambito():
    payload = build_document_payload(
        "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0065",
        EURLEX_HTML,
    )

    assert payload["tipo_fuente"] == "eurlex"
    assert payload["tipo_documento"] == "directive"
    assert payload["ambito"] == "mercados_financieros_ue"
    assert payload["referencia"] == "EURLEX-CELEX-32014L0065"
