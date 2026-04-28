"""Tests para worker EUR-Lex (Fase 35.9).

Cubre:
- _infer_tipo_y_numero
- _is_supported_block
- _eli_path
- _yyyymmdd_to_iso
- _parse_block_xml
- parse_index
- EURLEX_NORMAS (estructura y conteo)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eurlex import (
    _infer_tipo_y_numero,
    _is_supported_block,
    _eli_path,
    _yyyymmdd_to_iso,
    _parse_block_xml,
    parse_index,
)
import eurlex


def test_infer_tipo_y_numero_articulo_accented():
    tipo, numero = _infer_tipo_y_numero("Artículo 1. Disposiciones generales")
    assert tipo == "articulo"
    assert numero == "1"


def test_infer_tipo_y_numero_articulo_unaccented():
    tipo, numero = _infer_tipo_y_numero("Articulo 5. Definiciones")
    assert tipo == "articulo"
    assert numero == "5"


def test_infer_tipo_y_numero_disposicion_adicional():
    tipo, numero = _infer_tipo_y_numero("Disposición adicional primera")
    assert tipo == "disposicion_adicional"
    assert numero == "primera"


def test_infer_tipo_y_numero_disposicion_transitoria():
    tipo, numero = _infer_tipo_y_numero("Disposición transitoria segunda")
    assert tipo == "disposicion_transitoria"
    assert numero == "segunda"


def test_infer_tipo_y_numero_disposicion_final():
    tipo, numero = _infer_tipo_y_numero("Disposición final tercera")
    assert tipo == "disposicion_final"
    assert numero == "tercera"


def test_infer_tipo_y_numero_disposicion_derogatoria():
    tipo, numero = _infer_tipo_y_numero("Disposición derogatoria única")
    assert tipo == "disposicion_derogatoria"
    assert numero == "única"


def test_infer_tipo_y_numero_seccion():
    tipo, numero = _infer_tipo_y_numero("Sección 2. Requisitos de autorización")
    assert tipo == "seccion"
    assert numero == "Sección 2. Requisitos de autorización"


def test_infer_tipo_y_numero_capitulo():
    tipo, numero = _infer_tipo_y_numero("Capítulo 3. Derechos de los inversores")
    assert tipo == "capitulo"
    assert numero == "Capítulo 3. Derechos de los inversores"


def test_infer_tipo_y_numero_otro():
    tipo, numero = _infer_tipo_y_numero("Prólogo")
    assert tipo == "otro"
    assert numero == "Prólogo"


def test_is_supported_block_articulo():
    assert _is_supported_block("Artículo 1. Disposiciones generales") is True
    assert _is_supported_block("Articulo 2. Definiciones") is True


def test_is_supported_block_disposicion():
    assert _is_supported_block("Disposición adicional primera") is True
    assert _is_supported_block("Disposición transitoria segunda") is True
    assert _is_supported_block("Disposición final tercera") is True
    assert _is_supported_block("Disposición derogatoria única") is True


def test_is_supported_block_seccion_capitulo():
    assert _is_supported_block("Sección 2. Requisitos") is True
    assert _is_supported_block("Capítulo 3. Derechos") is True


def test_is_supported_block_other():
    assert _is_supported_block("Índice") is False
    assert _is_supported_block("Prólogo") is False
    assert _is_supported_block("Anexo") is False


def test_eli_path_regulation():
    assert _eli_path("EUR-CELEX-32014R0909") == "reg/2014/909/oj"


def test_eli_path_directive():
    assert _eli_path("EUR-CELEX-32014L0065") == "dir/2014/65/oj"


def test_eli_path_decision():
    assert _eli_path("EUR-CELEX-32013D0048") == "dec/2013/48/oj"


def test_eli_path_invalid():
    assert _eli_path("INVALID") == "unknown/oj"


def test_yyyymmdd_to_iso():
    assert _yyyymmdd_to_iso("20140912") == "2014-09-12"
    assert _yyyymmdd_to_iso("20220125") == "2022-01-25"


def test_parse_index_basic():
    payload = {
        "data": [
            {
                "bloque": [
                    {"id": "block-001", "titulo": "Artículo 1. Disposiciones generales", "fecha_actualizacion": ""},
                    {"id": "block-002", "titulo": "Artículo 2. Definiciones", "fecha_actualizacion": ""},
                    {"id": "block-003", "titulo": "", "fecha_actualizacion": ""},  # sin titulo -> skip
                ]
            }
        ]
    }
    result = parse_index(payload)
    assert len(result) == 2
    assert result[0]["id"] == "block-001"
    assert result[0]["titulo"] == "Artículo 1. Disposiciones generales"
    assert result[1]["id"] == "block-002"


def test_parse_index_empty():
    result = parse_index({"data": []})
    assert result == []


def test_parse_index_no_data_key():
    result = parse_index({})
    assert result == []


def test_parse_index_no_bloque_key():
    result = parse_index({"data": [{}]})
    assert result == []


def test_parse_index_block_xml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Artículo 1. Disposiciones generales" tipo="articulo">
            <p>Los Estados miembros adoptarán las disposiciones necesarias.</p>
            <p>Las mismas entrarán en vigor el 1 de enero de 2025.</p>
        </bloque>
        <version fecha_vigencia="20240101"/>
    </documento>
    """
    bloque = _parse_block_xml("block-001", xml_text)
    assert bloque.bloque_id == "block-001"
    assert bloque.tipo_bloque == "articulo"
    assert bloque.numero == "1"
    assert bloque.titulo == "Artículo 1. Disposiciones generales"
    assert bloque.tipo_articulo == "articulo"
    assert "Los Estados miembros adoptarán las disposiciones necesarias." in bloque.texto
    assert "Las mismas entrarán en vigor" in bloque.texto
    assert bloque.vigente_desde == "2024-01-01"


def test_parse_index_block_xml_disposicion():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Disposición adicional primera. Referencia" tipo="disposicion">
            <p>Se hace referencia al anexo I.</p>
        </bloque>
        <version fecha_vigencia="20230601"/>
    </documento>
    """
    bloque = _parse_block_xml("block-002", xml_text)
    assert bloque.tipo_articulo == "disposicion_adicional"
    assert bloque.numero == "primera"
    assert "Se hace referencia al anexo I." in bloque.texto
    assert bloque.vigente_desde == "2023-06-01"


def test_parse_index_block_xml_invalid_no_bloque():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <version fecha_vigencia="20240101"/>
    </documento>
    """
    try:
        _parse_block_xml("block-bad", xml_text)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid EUR-Lex block payload" in str(e)


def test_parse_index_block_xml_invalid_no_version():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Artículo 1" tipo="articulo">
            <p>Texto.</p>
        </bloque>
    </documento>
    """
    try:
        _parse_block_xml("block-bad", xml_text)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid EUR-Lex block payload" in str(e)


def test_eurlex_normas_has_required_fields():
    """Verificar que cada entrada de EURLEX_NORMAS tiene los campos requeridos."""
    required = {"codigo", "boe_id", "tipo_documento", "titulo", "vigente_desde", "ambito"}
    for norma in eurlex.EURLEX_NORMAS:
        assert required.issubset(norma.keys()), f"Faltan campos en {norma.get('codigo', 'unknown')}"
        assert norma["boe_id"].startswith("EUR-CELEX-"), f"boe_id debe empezar con EUR-CELEX-: {norma['boe_id']}"


def test_eurlex_normas_count():
    """Verificar que tenemos al menos 30 CELEXs."""
    assert len(eurlex.EURLEX_NORMAS) >= 30, f"Solo {len(eurlex.EURLEX_NORMAS)} CELEXs, se esperan >= 30"


def test_eurlex_normas_unique_codigos():
    """Verificar que los códigos son únicos."""
    codigos = [n["codigo"] for n in eurlex.EURLEX_NORMAS]
    assert len(codigos) == len(set(codigos)), f"Códigos duplicados encontrados: {len(codigos)} vs {len(set(codigos))}"


def test_eurlex_normas_boe_id_unique():
    """Verificar que los CELEXs son únicos."""
    celexs = [n["boe_id"] for n in eurlex.EURLEX_NORMAS]
    assert len(celexs) == len(set(celexs)), f"CELEXs duplicados encontrados"


def test_eurlex_normas_types():
    """Verificar que solo hay directivas y reglamentos."""
    tipos = {n["tipo_documento"] for n in eurlex.EURLEX_NORMAS}
    assert tipos.issubset({"directiva", "reglamento"}), f"Tipos inesperados: {tipos}"


def test_eurlex_normas_amplitudes():
    """Verificar que los ambitos son razonables."""
    ambitos = {n["ambito"] for n in eurlex.EURLEX_NORMAS}
    # Deberia haber variedad de ambitos
    assert len(ambitos) >= 10, f"Solo {len(ambitos)} ambitos diferentes, se espera >= 10"


def test_eli_path_format():
    """Verificar que _eli_path genera paths válidos."""
    # Reglamentos
    assert _eli_path("EUR-CELEX-32014R0909") == "reg/2014/909/oj"
    assert _eli_path("EUR-CELEX-32017R1129") == "reg/2017/1129/oj"
    # Directivas
    assert _eli_path("EUR-CELEX-32014L0065") == "dir/2014/65/oj"
    assert _eli_path("EUR-CELEX-32011L0061") == "dir/2011/61/oj"
    # Decisiones
    assert _eli_path("EUR-CELEX-32013D0048") == "dec/2013/48/oj"
