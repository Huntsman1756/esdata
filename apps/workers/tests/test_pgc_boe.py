import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgc_boe import parse_pgc_accounts, parse_pgc_marco, parse_pgc_normas


def test_parse_pgc_accounts_from_boe_text():
    text = textwrap.dedent("""
    CUARTA PARTE
    CUADRO DE CUENTAS
    Grupo 1
    Financiación básica
    10.
    CAPITAL
    100.
    Capital social
    1030.
    Socios por desembolsos no exigidos, capital social
    QUINTA PARTE
    """)

    result = parse_pgc_accounts(text)

    by_code = {item["codigo"]: item for item in result}
    assert by_code["10"]["descripcion"] == "CAPITAL"
    assert by_code["100"]["descripcion"] == "Capital social"
    assert by_code["1030"]["padre_codigo"] == "10"
    assert "BOE-A-2007-19884" in by_code["100"]["nota"]


def test_parse_pgc_marco_has_official_url():
    result = parse_pgc_marco("Real Decreto 1514/2007 PRIMERA PARTE SEGUNDA PARTE")

    assert any(item["codigo"] == "PGC_RD_1514_2007" for item in result)
    assert all(item["url_boe"].startswith("https://www.boe.es/") for item in result)


def test_parse_pgc_normas_from_second_part():
    text = textwrap.dedent("""
    SEGUNDA PARTE
    NORMAS DE REGISTRO Y VALORACIÓN
    1.ª Desarrollo del Marco Conceptual de la Contabilidad
    2.ª Inmovilizado material
    TERCERA PARTE
    """)

    result = parse_pgc_normas(text)

    assert [item["norma_ref"] for item in result] == ["NRV1", "NRV2"]
    assert "Inmovilizado material" in result[1]["descripcion"]
