"""Parser de metadata de Orden HAC desde XML del BOE.

Extrae orden, boe_id, modelos afectados, url_eli y titulo desde
el XML publicado por el BOE para las Ordenes HAC que definen
los modelos de declaraciones tributarias y sus casillas.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET


def parse_orden_hac_metadata(xml_text: str) -> dict:
    """Parsear XML del BOE para extraer metadata de una Orden HAC.

    Args:
        xml_text: Texto XML completo del BOE con estructura <metadatos>.

    Returns:
        Dict con claves: orden, boe_id, modelo_codigos, url_eli, titulo.

    Raises:
        ValueError: Si no se encuentra el elemento <metadatos> en el XML.
    """
    root = ET.fromstring(xml_text)
    metadatos = root.find("metadatos")
    if metadatos is None:
        raise ValueError("No metadatos element in BOE XML")

    titulo = ""
    url_eli = ""
    for tag in ("titulo", "url_eli"):
        elem = metadatos.find(tag)
        if elem is not None and elem.text:
            if tag == "titulo":
                titulo = elem.text.strip()
            elif tag == "url_eli":
                url_eli = elem.text.strip()

    boe_id = ""
    boe_match = re.search(r"BOE-A-\d{4}-\d+", titulo)
    if boe_match:
        boe_id = boe_match.group(0)
    if not boe_id:
        root_id = root.get("id", "")
        boe_id_match = re.search(r"BOE-A-\d{4}-\d+", root_id)
        if boe_id_match:
            boe_id = boe_id_match.group(0)

    orden = ""
    orden_match = re.search(r"Orden (HAC|EHA|HG)/\d+/\d{4}", titulo)
    if orden_match:
        orden = orden_match.group(0)

    modelo_codigos = sorted(
        set(re.findall(r"modelo (\d{2,3})", titulo, re.IGNORECASE))
    )

    return {
        "orden": orden,
        "boe_id": boe_id,
        "modelo_codigos": modelo_codigos,
        "url_eli": url_eli,
        "titulo": titulo,
    }


def parse_anexo_casilla_references(xml_text: str, modelo_codigo: str) -> list[dict]:
    """Parsear XML del BOE para extraer referencias a casillas en el ANEXO.

    Busca en el elemento <texto> los <p> que contengan referencias
    como "la casilla 001", "casilla 002", "Casilla 004", etc.

    Args:
        xml_text: Texto XML completo del BOE.
        modelo_codigo: Codigo del modelo para el enlace BOE.

    Returns:
        Lista de dicts con claves: codigo, descripcion, enlace_boe.
        Lista vacia si no se encuentra <texto>, <p> o referencias.
    """
    root = ET.fromstring(xml_text)
    texto = root.find("texto")
    if texto is None:
        return []

    casillas = []
    for p_elem in texto.findall("p"):
        paragraph = p_elem.text or ""
        matches = re.finditer(r"la?\s+casilla\s+(\d{1,4})", paragraph, re.IGNORECASE)
        for match in matches:
            raw_code = match.group(1)
            codigo = raw_code.zfill(4)
            descripcion = paragraph[:200]
            casillas.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "enlace_boe": modelo_codigo,
            })

    return casillas


def parse_boe_table_fields(xml_text: str) -> list[dict]:
    """Parsear XML del BOE para extraer especificaciones de campos desde tablas.

    Busca elementos <table> dentro de <texto> y extrae filas con 2+ columnas
    (<td> o <th>) que definan especificaciones de campos: codigo y descripcion.

    Args:
        xml_text: Texto XML completo del BOE.

    Returns:
        Lista de dicts con claves: codigo, naturaleza, descripcion.
        - codigo: codigo de posicion, cero-padded a 4 digitos si es numerico.
        - naturaleza: "N" por defecto (las tablas HAC tienen solo 2 columnas).
        - descripcion: contenido de la segunda columna.
        Lista vacia si no hay <texto>, <table> o tablas validas.
    """
    root = ET.fromstring(xml_text)
    texto = root.find("texto")
    if texto is None:
        return []

    def _get_cell_text(cell):
        if cell.text and cell.text.strip():
            return cell.text.strip()
        # Text might be in child elements (e.g. <p> inside <td>)
        for child in cell:
            if child.text and child.text.strip():
                return child.text.strip()
        return ""

    fields = []
    for table in texto.findall("table"):
        rows = table.findall("row")
        if not rows:
            rows = table.findall("tr")
        if len(rows) < 2:
            continue

        for row in rows:
            # Also check for HTML-style <th> elements (header cells)
            tds = row.findall("td")
            ths = row.findall("th")
            # Combine both td and th elements
            cells = tds + ths
            if len(cells) < 2:
                continue

            codigo_raw = _get_cell_text(cells[0])
            if not codigo_raw:
                continue

            descripcion = _get_cell_text(cells[1]) if len(cells) > 1 else ""

            # Zero-pad numeric codes to 4 digits
            if codigo_raw.isdigit():
                codigo = codigo_raw.zfill(4)
            else:
                codigo = codigo_raw

            fields.append({
                "codigo": codigo,
                "naturaleza": "N",
                "descripcion": descripcion,
            })

    return fields
