#!/usr/bin/env python3
"""Emit SQL to load official Modelo 290 FATCA instructions and rules.

The script downloads official BOE sources only to compute the source hashes.
It does not connect to the database; pipe the generated SQL into psql via the
production Docker Compose postgres service.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from datetime import date


ORDER_URL = "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-6922"
AGREEMENT_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2014-6854"
AEAT_XSD_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/"
    "GI38/Ayuda/XSD_WSDL/290_XSD_2.0_WSDL_2.1.1.zip"
)


def fetch_hash(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "esdata-official-source-loader/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return hashlib.md5(response.read()).hexdigest()


def q(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def emit_instruction(
    seccion: str,
    titulo: str,
    contenido: str,
    source_url: str,
    source_hash: str,
    orden: int,
    casilla_referencia: str | None = None,
) -> str:
    return f"""
    INSERT INTO modelo_instruccion
        (campana_id, seccion, titulo, contenido, orden, texto,
         casilla_referencia, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(seccion)}, {q(titulo)}, {q(contenido)}, {orden},
         {q(contenido)}, {q(casilla_referencia)}, {q(source_url)},
         {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, seccion, titulo)
    DO UPDATE SET
        contenido = EXCLUDED.contenido,
        orden = EXCLUDED.orden,
        texto = EXCLUDED.texto,
        casilla_referencia = EXCLUDED.casilla_referencia,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_clave(
    codigo: str,
    etiqueta: str,
    tipo: str,
    descripcion: str,
    criterio: str,
    source_url: str,
    source_hash: str,
    exclusiones: str | None = None,
) -> str:
    return f"""
    INSERT INTO modelo_clave
        (campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
         criterio_aplicacion, exclusiones, source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(codigo)}, {q(etiqueta)}, {q(descripcion)}, {q(tipo)},
         {q(tipo)}, {q(criterio)}, {q(exclusiones)}, {q(source_url)},
         {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, codigo)
    DO UPDATE SET
        etiqueta = EXCLUDED.etiqueta,
        descripcion = EXCLUDED.descripcion,
        tipo_clave = EXCLUDED.tipo_clave,
        tipo = EXCLUDED.tipo,
        criterio_aplicacion = EXCLUDED.criterio_aplicacion,
        exclusiones = EXCLUDED.exclusiones,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_rule(
    supuesto: str,
    decision: str,
    condicion: str | None,
    umbral: str | None,
    fuente_normativa: str,
    source_url: str,
    source_hash: str,
) -> str:
    return f"""
    INSERT INTO modelo_regla_inclusion
        (campana_id, supuesto, decision, condicion, umbral, fuente_normativa,
         source_url, source_hash, capture_date)
    VALUES
        (v_campana_id, {q(supuesto)}, {q(decision)}, {q(condicion)},
         {q(umbral)}, {q(fuente_normativa)}, {q(source_url)},
         {q(source_hash)}, v_capture_date)
    ON CONFLICT (campana_id, supuesto)
    DO UPDATE SET
        decision = EXCLUDED.decision,
        condicion = EXCLUDED.condicion,
        umbral = EXCLUDED.umbral,
        fuente_normativa = EXCLUDED.fuente_normativa,
        source_url = EXCLUDED.source_url,
        source_hash = EXCLUDED.source_hash,
        capture_date = EXCLUDED.capture_date;
    """


def emit_keyword(keyword: str, dominio: str = "FATCA") -> str:
    return f"""
    INSERT INTO modelo_trigger_keyword (modelo_id, keyword, dominio)
    VALUES (v_modelo_id, {q(keyword)}, {q(dominio)})
    ON CONFLICT DO NOTHING;
    """


def main() -> int:
    hashes = {
        ORDER_URL: fetch_hash(ORDER_URL),
        AGREEMENT_URL: fetch_hash(AGREEMENT_URL),
        AEAT_XSD_URL: fetch_hash(AEAT_XSD_URL),
    }
    capture_date = date.today().isoformat()

    instructions = [
        emit_instruction(
            "presentacion",
            "Aprobacion y periodicidad del Modelo 290",
            "La Orden HAP/1136/2014 aprueba el Modelo 290 como declaracion informativa anual de cuentas financieras de determinadas personas estadounidenses. Las instituciones financieras obligadas remiten anualmente la declaracion a la AEAT mediante mensaje informatico.",
            ORDER_URL,
            hashes[ORDER_URL],
            10,
        ),
        emit_instruction(
            "presentacion",
            "Formato y diseno de los mensajes",
            "El formato y diseno de los mensajes informaticos y los elementos del contenido de la declaracion son los que consten en cada momento en la sede electronica de la AEAT.",
            ORDER_URL,
            hashes[ORDER_URL],
            20,
        ),
        emit_instruction(
            "contenido",
            "Datos de la institucion financiera declarante",
            "El anexo de la Orden exige, entre otros datos, NIF, GIIN, denominacion o razon social, direccion, pais de residencia, ejercicio y marca de declaracion complementaria o sustitutiva.",
            ORDER_URL,
            hashes[ORDER_URL],
            30,
        ),
        emit_instruction(
            "contenido",
            "Datos de cuenta financiera sujeta a comunicacion",
            "Para cada cuenta financiera determinada como sujeta a comunicacion de informacion deben consignarse numero de cuenta, saldo o valor, moneda y datos del titular.",
            ORDER_URL,
            hashes[ORDER_URL],
            40,
        ),
        emit_instruction(
            "titular",
            "Tipo de titular de la cuenta",
            "El anexo identifica tres categorias de titular declarable: persona estadounidense especifica; entidad no estadounidense no financiera pasiva con una o varias personas de control ciudadanas o residentes de Estados Unidos; e institucion financiera con titulares documentados que sean personas estadounidenses especificas.",
            ORDER_URL,
            hashes[ORDER_URL],
            50,
            "17",
        ),
        emit_instruction(
            "diligencia_debida",
            "Cuenta preexistente de entidad pasiva",
            "El Acuerdo FATCA exige identificar si la entidad titular tiene personas que ejercen el control, si es una entidad no estadounidense distinta de institucion financiera extranjera pasiva y si alguna persona de control es ciudadana o residente de Estados Unidos.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
            60,
        ),
        emit_instruction(
            "diligencia_debida",
            "Cuenta nueva de entidad pasiva",
            "Si la entidad titular de una cuenta nueva es una entidad no estadounidense distinta de institucion financiera extranjera pasiva, la institucion financiera debe identificar a las personas que ejercen el control y determinar si cualquiera de ellas es ciudadana o residente de Estados Unidos.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
            70,
        ),
    ]

    claves = [
        emit_clave(
            "US_SPECIFIED_PERSON",
            "Persona estadounidense especifica",
            "TIPO_TITULAR",
            "Categoria de titular del Modelo 290 para persona estadounidense especifica.",
            "Usar cuando el titular de la cuenta financiera sea una persona estadounidense especifica.",
            ORDER_URL,
            hashes[ORDER_URL],
        ),
        emit_clave(
            "PASSIVE_NFFE_US_CONTROL",
            "Entidad no estadounidense pasiva con control US",
            "TIPO_TITULAR",
            "Entidad no estadounidense distinta de institucion financiera con caracter pasivo cuando una o varias personas que ejercen el control son ciudadanos o residentes de Estados Unidos.",
            "Usar cuando el titular sea entidad pasiva y exista una o varias personas de control US.",
            ORDER_URL,
            hashes[ORDER_URL],
            "No usar si ninguna persona que ejerce el control es ciudadana o residente de Estados Unidos.",
        ),
        emit_clave(
            "OWNER_DOCUMENTED_FI",
            "Owner-Documented Financial Institution",
            "TIPO_TITULAR",
            "Institucion financiera con titulares documentados que sean personas estadounidenses especificas.",
            "Usar cuando el titular sea una Owner-Documented Financial Institution conforme a la Orden.",
            ORDER_URL,
            hashes[ORDER_URL],
        ),
        emit_clave(
            "PASSIVE_NFFE",
            "Entidad no estadounidense no financiera pasiva",
            "TIPO_ENTIDAD",
            "Entidad no estadounidense distinta de institucion financiera extranjera que no es entidad activa ni sociedad de personas/fideicomiso extranjero retenedor.",
            "Determina la necesidad de identificar personas que ejercen el control y su condicion US.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_clave(
            "ACTIVE_NFFE",
            "Entidad no estadounidense no financiera activa",
            "TIPO_ENTIDAD",
            "Entidad no estadounidense distinta de institucion financiera extranjera que cumple alguno de los criterios de entidad activa del Anexo I del Acuerdo.",
            "Si se determina razonablemente que la entidad es activa, la cuenta no se comunica por la regla de entidad pasiva.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_clave(
            "FINANCIAL_INSTITUTION",
            "Institucion financiera",
            "TIPO_ENTIDAD",
            "Entidad identificada como institucion financiera bajo el Acuerdo FATCA.",
            "El procedimiento distingue instituciones financieras espanolas, de jurisdiccion socia, participantes y no participantes.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_clave(
            "NONPARTICIPATING_FI",
            "Institucion financiera no participante",
            "TIPO_ENTIDAD",
            "Institucion financiera no participante identificada por IRS conforme al Acuerdo.",
            "La cuenta no es cuenta estadounidense sujeta a comunicacion, pero los pagos al titular pueden estar sujetos a comunicacion agregada.",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
    ]

    rules = [
        emit_rule(
            "Persona estadounidense especifica titular de cuenta financiera",
            "INCLUIR",
            "La cuenta se trata como cuenta estadounidense sujeta a comunicacion salvo excepcion oficial aplicable tras diligencia debida.",
            None,
            "Acuerdo FATCA Espana-EE.UU., art. 1.1.dd y Anexo I, secciones IV/V",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_rule(
            "Entidad no estadounidense no financiera pasiva con una o mas personas de control ciudadanas o residentes de Estados Unidos",
            "INCLUIR",
            "Debe comunicarse la cuenta y la informacion de la entidad y de cada persona estadounidense especifica que ejerce el control.",
            "El texto oficial usado no fija un porcentaje; remite a personas que ejercen el control y a procedimientos KYC/AML.",
            "Acuerdo FATCA Espana-EE.UU., Anexo I, secciones IV.C, IV.D.4 y V.C.2",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_rule(
            "Entidad no estadounidense no financiera pasiva sin personas de control ciudadanas o residentes de Estados Unidos",
            "EXCLUIR",
            "La cuenta no es cuenta estadounidense sujeta a comunicacion de informacion por esta regla.",
            "El texto oficial usado no fija un porcentaje; exige verificar la condicion de las personas que ejercen el control.",
            "Acuerdo FATCA Espana-EE.UU., Anexo I, seccion V.C.3.v",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_rule(
            "Entidad no estadounidense no financiera activa",
            "EXCLUIR",
            "Si se determina razonablemente que la entidad es activa, la cuenta no se comunica por la regla de entidad pasiva.",
            "Criterio activo principal: menos del 50 por ciento de renta pasiva y menos del 50 por ciento de activos pasivos, u otros criterios oficiales.",
            "Acuerdo FATCA Espana-EE.UU., Anexo I, seccion VI.B.4",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
        emit_rule(
            "Institucion financiera no participante",
            "CONDICIONAL",
            "La cuenta no es cuenta estadounidense sujeta a comunicacion, pero los pagos efectuados al titular se comunican agregadamente segun el Acuerdo.",
            None,
            "Acuerdo FATCA Espana-EE.UU., Anexo I, seccion V.C.4 y art. 4.1.b",
            AGREEMENT_URL,
            hashes[AGREEMENT_URL],
        ),
    ]

    keywords = [
        "FATCA",
        "modelo 290",
        "290 FATCA",
        "passive NFFE",
        "active NFFE",
        "entidad pasiva FATCA",
        "entidad activa FATCA",
        "FFI",
        "GIIN",
        "cuenta estadounidense",
        "persona estadounidense especifica",
        "controlling person",
        "persona que ejerce el control",
        "titular sustancial",
        "substantial owner",
        "Owner-Documented Financial Institution",
    ]

    print("-- Generated by scripts/data/load_modelo_290_fatca_instructions.py")
    print("-- Official sources:")
    for url, source_hash in hashes.items():
        print(f"-- {url} md5={source_hash}")
    print("BEGIN;")
    print(
        f"""
DO $$
DECLARE
    v_modelo_id INTEGER;
    v_campana_id INTEGER;
    v_capture_date DATE := DATE {q(capture_date)};
BEGIN
    SELECT m.id, c.id
      INTO v_modelo_id, v_campana_id
      FROM aeat_modelo m
      JOIN modelo_campana c ON c.modelo_id = m.id
     WHERE m.codigo = '290'
       AND c.activo = true
     ORDER BY c.campana DESC
     LIMIT 1;

    IF v_modelo_id IS NULL OR v_campana_id IS NULL THEN
        RAISE EXCEPTION 'Modelo 290 active campaign not found';
    END IF;
"""
    )
    print(
        """
    DELETE FROM modelo_regla_inclusion WHERE campana_id = v_campana_id;
    DELETE FROM modelo_trigger_keyword WHERE modelo_id = v_modelo_id;
"""
    )
    for statement in instructions + claves + rules:
        print(statement)
    for keyword in keywords:
        print(emit_keyword(keyword))
    print("END $$;")
    print("COMMIT;")
    return 0


if __name__ == "__main__":
    sys.exit(main())
