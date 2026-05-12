"""Official reference-data worker for regulatory tables.

This worker only loads compact normative reference catalogs from official
sources. It deliberately does not create entity, fund, filing, incident, client,
or product rows, because those require a real upstream registry, filing feed, or
user workflow input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from boe import _ensure_sync_log_table, log_sync
from runtime import ensure_database_connection, get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

CSRD_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772"
DORA_CLASSIFICATION_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1772"
DORA_REPORTING_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R0301"
SEPA_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32012R0260"
SEPA_INSTANT_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R0886"
PBC_SOURCE_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737&tn=2"
EU_SANCTIONS_SOURCE_URL = (
    "https://finance.ec.europa.eu/eu-and-world/sanctions-restrictive-measures/"
    "overview-sanctions-and-related-resources_en"
)
SEPBLAC_SOURCE_URL = "https://www.sepblac.es/"
IRS_PUB_515_URL = "https://www.irs.gov/publications/p515"
IRS_W8_URL = "https://www.irs.gov/forms-pubs/about-form-w-8-ben"
IRS_W8_INSTRUCTIONS_URL = "https://www.irs.gov/instructions/iw8"
OECD_TIN_URL = "https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/"
FATCA_IGA_ES_US_SOURCE_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2014-6854"
FATCA_MODELO_290_SOURCE_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2014-6922"
CRS_RD_1021_2015_SOURCE_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2015-12399"
CRS_MODELO_289_SOURCE_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2016-9834"
DAC2_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0107"
DAC6_SOURCE_URL = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32018L0822"


CSRD_ESRS_ROWS = [
    ("ESRS 1", "General requirements"),
    ("ESRS 2", "General disclosures"),
    ("ESRS E1", "Climate change"),
    ("ESRS E2", "Pollution"),
    ("ESRS E3", "Water and marine resources"),
    ("ESRS E4", "Biodiversity and ecosystems"),
    ("ESRS E5", "Resource use and circular economy"),
    ("ESRS S1", "Own workforce"),
    ("ESRS S2", "Workers in the value chain"),
    ("ESRS S3", "Affected communities"),
    ("ESRS S4", "Consumers and end-users"),
    ("ESRS G1", "Business conduct"),
]


SEPA_RULE_ROWS = [
    {
        "scheme_version": "EPC SCT 2025 rulebook",
        "payment_type": "credit_transfer",
        "service_level": "SEPA",
        "local_instrument": "SCT",
        "category_purpose": None,
        "cut_off_time": None,
        "settlement_days": 1,
        "source_url": SEPA_SOURCE_URL,
    },
    {
        "scheme_version": "EPC SCT Inst 2025 rulebook",
        "payment_type": "instant_credit_transfer",
        "service_level": "SEPA",
        "local_instrument": "SCT Inst",
        "category_purpose": None,
        "cut_off_time": None,
        "settlement_days": 0,
        "source_url": SEPA_INSTANT_SOURCE_URL,
    },
]

PBC_OBLIGATED_SUBJECT_ROWS = [
    "credit_institutions",
    "financial_institutions",
    "payment_and_e_money_entities",
    "investment_services_companies",
    "insurance_entities_and_brokers",
    "real_estate_and_professional_services",
]

SCREENING_LIST_ROWS = [
    {
        "codigo": "EU_SANCTIONS",
        "nombre": "EU restrictive measures and financial sanctions resources",
        "tipo": "sanctions",
        "organismo": "European Commission / European Union",
        "pais": None,
        "url_fuente": EU_SANCTIONS_SOURCE_URL,
        "descripcion": "Official EU sanctions resource catalogue. Entries require a separate official-list parser.",
        "actualizada": None,
        "activo": True,
    },
    {
        "codigo": "SEPBLAC",
        "nombre": "SEPBLAC official AML/CFT authority resources",
        "tipo": "watchlist",
        "organismo": "SEPBLAC",
        "pais": "ES",
        "url_fuente": SEPBLAC_SOURCE_URL,
        "descripcion": "Official Spanish AML/CFT authority reference. Entries require a specific official publication source.",
        "actualizada": None,
        "activo": True,
    },
]

IRS_FISCAL_NORMA_ROWS = [
    {
        "codigo": "IRS_PUB_515_2026",
        "titulo": "Publication 515 (2026), Withholding of Tax on Nonresident Aliens and Foreign Entities",
        "tipo": "publicacion",
        "anio_vigencia": 2026,
        "texto": "Official IRS publication for withholding agents; use current IRS text for operative decisions.",
        "url_fuente": IRS_PUB_515_URL,
        "estado": "activo",
    },
    {
        "codigo": "IRS_W8_REQUESTER_INSTRUCTIONS",
        "titulo": "Instructions for the Requester of Forms W-8",
        "tipo": "instruccion",
        "anio_vigencia": 2022,
        "texto": "Official IRS requester instructions for W-8BEN, W-8BEN-E, W-8ECI, W-8EXP, and W-8IMY.",
        "url_fuente": IRS_W8_INSTRUCTIONS_URL,
        "estado": "activo",
    },
]

IRS_MODELO_ROWS = [
    ("W-8BEN", "Certificate of Foreign Status of Beneficial Owner for United States Tax Withholding and Reporting (Individuals)", IRS_W8_URL),
    ("W-8BEN-E", "Certificate of Status of Beneficial Owner for United States Tax Withholding and Reporting (Entities)", "https://www.irs.gov/forms-pubs/about-form-w-8-ben-e"),
    ("W-8ECI", "Certificate of Foreign Person's Claim That Income Is Effectively Connected With the Conduct of a Trade or Business in the United States", "https://www.irs.gov/forms-pubs/about-form-w-8-eci"),
    ("W-8IMY", "Certificate of Foreign Intermediary, Foreign Flow-Through Entity, or Certain U.S. Branches for United States Tax Withholding and Reporting", "https://www.irs.gov/forms-pubs/about-form-w-8-imy"),
]

IRS_TIN_REFERENCE_ROWS = [
    {
        "codigo_pais": "ES",
        "pais_nombre": "Spain",
        "formato_tin": "NIF/NIE/CIF; validate against official Spanish/OECD TIN guidance",
        "ejemplo_tin": None,
        "emisor_espana": "AEAT / competent Spanish authority",
        "emisor_pais": "Spain",
        "es_ocde": True,
        "es_eu_vat": True,
        "source_url": OECD_TIN_URL,
    },
    {
        "codigo_pais": "US",
        "pais_nombre": "United States",
        "formato_tin": "SSN/ITIN/EIN; validate against official IRS guidance",
        "ejemplo_tin": None,
        "emisor_espana": None,
        "emisor_pais": "Internal Revenue Service",
        "es_ocde": True,
        "es_eu_vat": False,
        "source_url": "https://www.irs.gov/individuals/international-taxpayers/taxpayer-identification-numbers-tin",
    },
]

IRS_WITHHOLDING_RULE_ROWS = [
    {
        "codigo": "CH3_FDAP_DEFAULT",
        "tipo_renta": "FDAP",
        "tipo_renta_espanol": "Renta fija o determinable anual o periodica de fuente estadounidense",
        "tipo_retencion_default": 30.0,
        "tipo_retencion_dta": None,
        "pais_aplicable": None,
        "descripcion": "Default Chapter 3 statutory withholding reference; treaty or exemption analysis must use official current IRS text.",
        "norma_referencia": "IRS Publication 515 (2026)",
        "articulo_referencia": "Chapter 3 withholding / FDAP income",
        "estado": "activo",
        "source_url": IRS_PUB_515_URL,
    },
]

INTERNATIONAL_OBLIGATION_ROWS = [
    {
        "codigo": "FATCA",
        "titulo": "FATCA en Espana: acuerdo Espana-Estados Unidos y modelo 290",
        "tipo": "referencia_normativa",
        "jurisdiccion_origen": "ES-US",
        "jurisdiccion_aplicacion": "ES",
        "vigente_desde": "2013-12-09",
        "vigente_hasta": None,
        "descripcion": (
            "Entrada agregada para localizar las fuentes oficiales FATCA relevantes "
            "en Espana. Para aplicar una obligacion concreta, contrastar el acuerdo "
            "BOE-A-2014-6854, la Orden HAP/1136/2014 y el modelo AEAT 290."
        ),
        "estado": "activo",
        "source_url": FATCA_IGA_ES_US_SOURCE_URL,
    },
    {
        "codigo": "FATCA_IGA_ES",
        "titulo": (
            "Acuerdo Espana-Estados Unidos para la mejora del cumplimiento fiscal "
            "internacional y la implementacion de FATCA"
        ),
        "tipo": "convenio",
        "jurisdiccion_origen": "ES-US",
        "jurisdiccion_aplicacion": "ES-US",
        "vigente_desde": "2013-12-09",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia normativa oficial del acuerdo FATCA publicado como BOE-A-2014-6854. "
            "Esta fila identifica la fuente; la aplicabilidad operativa exige analizar el "
            "tipo de institucion financiera, cuenta y persona reportable."
        ),
        "estado": "activo",
        "source_url": FATCA_IGA_ES_US_SOURCE_URL,
    },
    {
        "codigo": "MODELO_290_FATCA",
        "titulo": (
            "Orden HAP/1136/2014 que aprueba el modelo 290 de cuentas financieras "
            "de determinadas personas estadounidenses"
        ),
        "tipo": "orden",
        "jurisdiccion_origen": "ES",
        "jurisdiccion_aplicacion": "ES",
        "vigente_desde": "2014-07-03",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia BOE del modelo 290 FATCA. La fila no sustituye al detalle de "
            "casillas AEAT ni confirma por si sola la obligacion de un caso concreto."
        ),
        "estado": "activo",
        "source_url": FATCA_MODELO_290_SOURCE_URL,
    },
    {
        "codigo": "CRS",
        "titulo": "CRS/DAC2 en Espana: Real Decreto 1021/2015 y modelo 289",
        "tipo": "referencia_normativa",
        "jurisdiccion_origen": "ES-UE",
        "jurisdiccion_aplicacion": "ES",
        "vigente_desde": "2016-01-01",
        "vigente_hasta": None,
        "descripcion": (
            "Entrada agregada para localizar las fuentes oficiales CRS/DAC2 relevantes "
            "en Espana. Para aplicar una obligacion concreta, contrastar el Real Decreto "
            "1021/2015, la Directiva 2014/107/UE y el modelo AEAT 289."
        ),
        "estado": "activo",
        "source_url": CRS_RD_1021_2015_SOURCE_URL,
    },
    {
        "codigo": "CRS_RD_1021_2015",
        "titulo": (
            "Real Decreto 1021/2015 sobre identificacion de residencia fiscal y "
            "comunicacion de cuentas financieras en asistencia mutua"
        ),
        "tipo": "real_decreto",
        "jurisdiccion_origen": "ES",
        "jurisdiccion_aplicacion": "ES",
        "vigente_desde": "2016-01-01",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia normativa oficial CRS/DAC2 en Espana. Define obligaciones de "
            "identificacion y comunicacion para instituciones financieras en los terminos "
            "del propio Real Decreto."
        ),
        "estado": "activo",
        "source_url": CRS_RD_1021_2015_SOURCE_URL,
    },
    {
        "codigo": "MODELO_289_CRS",
        "titulo": (
            "Orden HAP/1695/2016 que aprueba el modelo 289 de cuentas financieras "
            "en el ambito de la asistencia mutua"
        ),
        "tipo": "orden",
        "jurisdiccion_origen": "ES",
        "jurisdiccion_aplicacion": "ES",
        "vigente_desde": "2016-10-28",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia BOE del modelo 289 DAC2/CRS. La fila aporta fuente normativa; "
            "las respuestas deben seguir marcando evidencia limitada si faltan campos "
            "o reglas completas del caso consultado."
        ),
        "estado": "activo",
        "source_url": CRS_MODELO_289_SOURCE_URL,
    },
    {
        "codigo": "DAC2_2014_107_UE",
        "titulo": (
            "Directiva 2014/107/UE sobre intercambio automatico obligatorio de "
            "informacion en fiscalidad"
        ),
        "tipo": "directiva",
        "jurisdiccion_origen": "UE",
        "jurisdiccion_aplicacion": "UE",
        "vigente_desde": "2014-12-09",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia EUR-Lex de DAC2, marco UE relacionado con CRS. En Espana se "
            "contrasta junto con el Real Decreto 1021/2015 y el modelo 289."
        ),
        "estado": "activo",
        "source_url": DAC2_SOURCE_URL,
    },
    {
        "codigo": "DAC6",
        "titulo": "DAC6: mecanismos transfronterizos sujetos a comunicacion",
        "tipo": "directiva",
        "jurisdiccion_origen": "UE",
        "jurisdiccion_aplicacion": "UE",
        "vigente_desde": "2018-06-25",
        "vigente_hasta": None,
        "descripcion": (
            "Entrada agregada para localizar la Directiva (UE) 2018/822. El detalle "
            "operativo nacional debe contrastarse con normativa espanola de transposicion "
            "y el dominio DAC cargado."
        ),
        "estado": "activo",
        "source_url": DAC6_SOURCE_URL,
    },
    {
        "codigo": "DAC6_2018_822_UE",
        "titulo": (
            "Directiva (UE) 2018/822 sobre comunicacion obligatoria de mecanismos "
            "transfronterizos sujetos a comunicacion"
        ),
        "tipo": "directiva",
        "jurisdiccion_origen": "UE",
        "jurisdiccion_aplicacion": "UE",
        "vigente_desde": "2018-06-25",
        "vigente_hasta": None,
        "descripcion": (
            "Referencia EUR-Lex de DAC6. Se incluye como referencia internacional; "
            "el detalle articulo-a-articulo se sirve desde el dominio DAC si esta cargado."
        ),
        "estado": "activo",
        "source_url": DAC6_SOURCE_URL,
    },
]

AEAT_OBLIGATION_MODELS = [
    "100",
    "111",
    "115",
    "130",
    "131",
    "200",
    "202",
    "210",
    "216",
    "303",
    "347",
    "390",
]


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_reference_revision(conn, worker_name: str, entity_type: str, entity_id: str, payload: Any, source_url: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO source_revision (
                worker_name, source_entity_tipo, source_entity_id,
                content_hash_sha256, dgt_url, fetched_at
            )
            VALUES (:worker, :etype, :eid, :hash, :url, now())
            ON CONFLICT (worker_name, source_entity_tipo, source_entity_id)
            DO UPDATE SET
                content_hash_sha256 = EXCLUDED.content_hash_sha256,
                dgt_url = EXCLUDED.dgt_url,
                fetched_at = EXCLUDED.fetched_at
            """
        ),
        {
            "worker": worker_name,
            "etype": entity_type,
            "eid": entity_id,
            "hash": _hash_payload(payload),
            "url": source_url,
        },
    )


def upsert_csrd_ess(conn, worker_name: str) -> int:
    count = 0
    for code, topic in CSRD_ESRS_ROWS:
        description = (
            f"{topic}. Official ESRS catalogue under Commission Delegated "
            f"Regulation (EU) 2023/2772. Entity applicability depends on CSRD "
            f"scope and phase-in rules; this row is normative reference metadata."
        )
        existing = conn.execute(
            text("SELECT id FROM csrd_ess WHERE standard_code = :code LIMIT 1"),
            {"code": code},
        ).mappings().first()
        payload = {
            "standard_code": code,
            "topic": topic,
            "applicable_from_year": 2024,
            "description": description,
            "status": "active",
        }
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE csrd_ess
                    SET topic = :topic,
                        applicable_from_year = :year,
                        description = :description,
                        status = :status
                    WHERE id = :id
                    """
                ),
                {**payload, "year": payload["applicable_from_year"], "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO csrd_ess (
                        standard_code, topic, applicable_from_year,
                        description, status, created_at
                    )
                    VALUES (:standard_code, :topic, :applicable_from_year,
                        :description, :status, now())
                    """
                ),
                payload,
            )
        record_reference_revision(conn, worker_name, "csrd_ess", code, payload, CSRD_SOURCE_URL)
        count += 1
    return count


def upsert_dora_incident_framework(conn, worker_name: str) -> int:
    payload = {
        "framework_version": "DORA RTS 2024/1772 + 2025/301",
        "severity_thresholds": {
            "classification_source": DORA_CLASSIFICATION_SOURCE_URL,
            "criteria_articles": "Commission Delegated Regulation (EU) 2024/1772, Articles 1 to 8",
            "note": (
                "Reference row only. The exact major-incident classification "
                "decision must be evaluated against the official RTS text."
            ),
        },
        "reporting_timelines": {
            "source": DORA_REPORTING_SOURCE_URL,
            "initial_notification": (
                "As early as possible, within four hours from classification as "
                "major, and no later than 24 hours from awareness."
            ),
            "intermediate_report": (
                "At latest within 72 hours from submission of the initial "
                "notification; updated without undue delay when activities recover."
            ),
            "final_report": (
                "No later than one month after the intermediate report or latest "
                "updated intermediate report."
            ),
        },
        "effective_date": "2025-02-20",
        "status": "active",
    }
    existing = conn.execute(
        text(
            """
            SELECT id FROM dora_incident_classification_framework
            WHERE framework_version = :version
            LIMIT 1
            """
        ),
        {"version": payload["framework_version"]},
    ).mappings().first()
    params = {
        "version": payload["framework_version"],
        "severity": json.dumps(payload["severity_thresholds"], sort_keys=True),
        "timelines": json.dumps(payload["reporting_timelines"], sort_keys=True),
        "effective": payload["effective_date"],
        "status": payload["status"],
    }
    if existing:
        conn.execute(
            text(
                """
                UPDATE dora_incident_classification_framework
                SET severity_thresholds = CAST(:severity AS json),
                    reporting_timelines = CAST(:timelines AS json),
                    effective_date = :effective,
                    status = :status
                WHERE id = :id
                """
            ),
            {**params, "id": existing["id"]},
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO dora_incident_classification_framework (
                    framework_version, severity_thresholds, reporting_timelines,
                    effective_date, status, created_at
                )
                VALUES (
                    :version, CAST(:severity AS json), CAST(:timelines AS json),
                    :effective, :status, now()
                )
                """
            ),
            params,
        )
    record_reference_revision(
        conn,
        worker_name,
        "dora_incident_classification_framework",
        payload["framework_version"],
        payload,
        DORA_REPORTING_SOURCE_URL,
    )
    return 1


def upsert_sepa_rules(conn, worker_name: str) -> int:
    count = 0
    for row in SEPA_RULE_ROWS:
        existing = conn.execute(
            text(
                """
                SELECT id FROM sepa_payment_rule
                WHERE scheme_version = :scheme_version
                  AND payment_type = :payment_type
                  AND service_level = :service_level
                LIMIT 1
                """
            ),
            row,
        ).mappings().first()
        params = {k: v for k, v in row.items() if k != "source_url"}
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE sepa_payment_rule
                    SET local_instrument = :local_instrument,
                        category_purpose = :category_purpose,
                        cut_off_time = :cut_off_time,
                        settlement_days = :settlement_days
                    WHERE id = :id
                    """
                ),
                {**params, "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO sepa_payment_rule (
                        scheme_version, payment_type, service_level,
                        local_instrument, category_purpose, cut_off_time,
                        settlement_days, created_at
                    )
                    VALUES (
                        :scheme_version, :payment_type, :service_level,
                        :local_instrument, :category_purpose, :cut_off_time,
                        :settlement_days, now()
                    )
                    """
                ),
                params,
            )
        record_reference_revision(
            conn,
            worker_name,
            "sepa_payment_rule",
            f"{row['scheme_version']}:{row['payment_type']}",
            row,
            row["source_url"],
        )
        count += 1
    return count


def upsert_pbc_obligated_subjects(conn, worker_name: str) -> int:
    count = 0
    for subject_type in PBC_OBLIGATED_SUBJECT_ROWS:
        payload = {
            "subject_type": subject_type,
            "tin": None,
            "registration_number": None,
            "supervisory_authority": "SEPBLAC / competent sector supervisor",
            "pbc_license": "Ley 10/2010 article 2 subject category",
            "status": "active",
        }
        existing = conn.execute(
            text(
                """
                SELECT id FROM pbc_obligated_subject
                WHERE subject_type = :subject_type
                  AND pbc_license = :pbc_license
                LIMIT 1
                """
            ),
            payload,
        ).mappings().first()
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE pbc_obligated_subject
                    SET supervisory_authority = :supervisory_authority,
                        status = :status
                    WHERE id = :id
                    """
                ),
                {**payload, "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO pbc_obligated_subject (
                        subject_type, tin, registration_number,
                        supervisory_authority, pbc_license, status, created_at
                    )
                    VALUES (
                        :subject_type, :tin, :registration_number,
                        :supervisory_authority, :pbc_license, :status, now()
                    )
                    """
                ),
                payload,
            )
        record_reference_revision(
            conn,
            worker_name,
            "pbc_obligated_subject",
            subject_type,
            payload,
            PBC_SOURCE_URL,
        )
        count += 1
    return count


def upsert_screening_lists(conn, worker_name: str) -> int:
    count = 0
    for row in SCREENING_LIST_ROWS:
        existing = conn.execute(
            text("SELECT id FROM screening_lists WHERE codigo = :codigo LIMIT 1"),
            row,
        ).mappings().first()
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE screening_lists
                    SET nombre = :nombre,
                        tipo = :tipo,
                        organismo = :organismo,
                        pais = :pais,
                        url_fuente = :url_fuente,
                        descripcion = :descripcion,
                        actualizada = :actualizada,
                        activo = :activo
                    WHERE id = :id
                    """
                ),
                {**row, "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO screening_lists (
                        codigo, nombre, tipo, organismo, pais, url_fuente,
                        descripcion, actualizada, activo, created_at
                    )
                    VALUES (
                        :codigo, :nombre, :tipo, :organismo, :pais, :url_fuente,
                        :descripcion, :actualizada, :activo, now()
                    )
                    """
                ),
                row,
            )
        record_reference_revision(
            conn,
            worker_name,
            "screening_lists",
            row["codigo"],
            row,
            row["url_fuente"],
        )
        count += 1
    return count


def upsert_irs_references(conn, worker_name: str) -> dict[str, int]:
    fiscal = 0
    for row in IRS_FISCAL_NORMA_ROWS:
        conn.execute(
            text(
                """
                INSERT INTO irs_fiscal_norma (
                    codigo, titulo, tipo, anio_vigencia, texto, url_fuente, estado
                )
                VALUES (
                    :codigo, :titulo, :tipo, :anio_vigencia, :texto, :url_fuente, :estado
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    titulo = EXCLUDED.titulo,
                    tipo = EXCLUDED.tipo,
                    anio_vigencia = EXCLUDED.anio_vigencia,
                    texto = EXCLUDED.texto,
                    url_fuente = EXCLUDED.url_fuente,
                    estado = EXCLUDED.estado,
                    actualizado_en = now()
                """
            ),
            row,
        )
        record_reference_revision(conn, worker_name, "irs_fiscal_norma", row["codigo"], row, row["url_fuente"])
        fiscal += 1

    modelos = 0
    for code, name, url in IRS_MODELO_ROWS:
        payload = {
            "codigo": code,
            "nombre": name,
            "periodo": "current_official_form",
            "impuesto": "US withholding",
            "url_info": url,
            "activo": True,
        }
        conn.execute(
            text(
                """
                INSERT INTO irs_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                VALUES (:codigo, :nombre, :periodo, :impuesto, :url_info, :activo)
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    periodo = EXCLUDED.periodo,
                    impuesto = EXCLUDED.impuesto,
                    url_info = EXCLUDED.url_info,
                    activo = EXCLUDED.activo,
                    actualizado_en = now()
                """
            ),
            payload,
        )
        conn.execute(
            text(
                """
                INSERT INTO irs_w8_form (
                    codigo, nombre, descripcion, tipo_sujeto, finalidad,
                    partes, validez_anios, obligacion_asociada, texto_detalle, estado
                )
                VALUES (
                    :codigo, :nombre, :descripcion, :tipo_sujeto, :finalidad,
                    CAST(:partes AS jsonb), :validez_anios, :obligacion_asociada,
                    :texto_detalle, :estado
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    descripcion = EXCLUDED.descripcion,
                    tipo_sujeto = EXCLUDED.tipo_sujeto,
                    finalidad = EXCLUDED.finalidad,
                    partes = EXCLUDED.partes,
                    validez_anios = EXCLUDED.validez_anios,
                    obligacion_asociada = EXCLUDED.obligacion_asociada,
                    texto_detalle = EXCLUDED.texto_detalle,
                    estado = EXCLUDED.estado,
                    actualizado_en = now()
                """
            ),
            {
                "codigo": code,
                "nombre": name,
                "descripcion": f"Official IRS form reference for {code}.",
                "tipo_sujeto": "individual" if code == "W-8BEN" else "entity_or_intermediary",
                "finalidad": "Foreign status and withholding/treaty documentation",
                "partes": json.dumps({"source_url": url, "detail": "Use current IRS form and instructions."}),
                "validez_anios": 3,
                "obligacion_asociada": "US withholding documentation",
                "texto_detalle": "Validity and required parts can vary by facts; verify against official IRS instructions.",
                "estado": "activo",
            },
        )
        record_reference_revision(conn, worker_name, "irs_modelo", code, payload, url)
        modelos += 1

    tins = 0
    for row in IRS_TIN_REFERENCE_ROWS:
        payload = {k: v for k, v in row.items() if k != "source_url"}
        existing = conn.execute(
            text("SELECT id FROM irs_tin_reference WHERE codigo_pais = :codigo_pais LIMIT 1"),
            payload,
        ).mappings().first()
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE irs_tin_reference
                    SET pais_nombre = :pais_nombre,
                        formato_tin = :formato_tin,
                        ejemplo_tin = :ejemplo_tin,
                        emisor_espana = :emisor_espana,
                        emisor_pais = :emisor_pais,
                        es_ocde = :es_ocde,
                        es_eu_vat = :es_eu_vat
                    WHERE id = :id
                    """
                ),
                {**payload, "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO irs_tin_reference (
                        codigo_pais, pais_nombre, formato_tin, ejemplo_tin,
                        emisor_espana, emisor_pais, es_ocde, es_eu_vat
                    )
                    VALUES (
                        :codigo_pais, :pais_nombre, :formato_tin, :ejemplo_tin,
                        :emisor_espana, :emisor_pais, :es_ocde, :es_eu_vat
                    )
                    """
                ),
                payload,
            )
        record_reference_revision(conn, worker_name, "irs_tin_reference", row["codigo_pais"], row, row["source_url"])
        tins += 1

    withholding = 0
    for row in IRS_WITHHOLDING_RULE_ROWS:
        payload = {k: v for k, v in row.items() if k != "source_url"}
        conn.execute(
            text(
                """
                INSERT INTO irs_withholding_rule (
                    codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default,
                    tipo_retencion_dta, pais_aplicable, descripcion,
                    norma_referencia, articulo_referencia, estado
                )
                VALUES (
                    :codigo, :tipo_renta, :tipo_renta_espanol, :tipo_retencion_default,
                    :tipo_retencion_dta, :pais_aplicable, :descripcion,
                    :norma_referencia, :articulo_referencia, :estado
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    tipo_renta = EXCLUDED.tipo_renta,
                    tipo_renta_espanol = EXCLUDED.tipo_renta_espanol,
                    tipo_retencion_default = EXCLUDED.tipo_retencion_default,
                    tipo_retencion_dta = EXCLUDED.tipo_retencion_dta,
                    pais_aplicable = EXCLUDED.pais_aplicable,
                    descripcion = EXCLUDED.descripcion,
                    norma_referencia = EXCLUDED.norma_referencia,
                    articulo_referencia = EXCLUDED.articulo_referencia,
                    estado = EXCLUDED.estado,
                    actualizado_en = now()
                """
            ),
            payload,
        )
        record_reference_revision(conn, worker_name, "irs_withholding_rule", row["codigo"], row, row["source_url"])
        withholding += 1

    return {
        "irs_fiscal_norma": fiscal,
        "irs_modelo": modelos,
        "irs_w8_form": modelos,
        "irs_tin_reference": tins,
        "irs_withholding_rule": withholding,
    }


def upsert_international_obligations(conn, worker_name: str) -> int:
    count = 0
    for row in INTERNATIONAL_OBLIGATION_ROWS:
        payload = {key: value for key, value in row.items() if key != "source_url"}
        conn.execute(
            text(
                """
                INSERT INTO obligacion_internacional (
                    codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion,
                    vigente_desde, vigente_hasta, descripcion, estado
                )
                VALUES (
                    :codigo, :titulo, :tipo, :jurisdiccion_origen, :jurisdiccion_aplicacion,
                    :vigente_desde, :vigente_hasta, :descripcion, :estado
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    titulo = EXCLUDED.titulo,
                    tipo = EXCLUDED.tipo,
                    jurisdiccion_origen = EXCLUDED.jurisdiccion_origen,
                    jurisdiccion_aplicacion = EXCLUDED.jurisdiccion_aplicacion,
                    vigente_desde = EXCLUDED.vigente_desde,
                    vigente_hasta = EXCLUDED.vigente_hasta,
                    descripcion = EXCLUDED.descripcion,
                    estado = EXCLUDED.estado,
                    actualizado_en = now()
                """
            ),
            payload,
        )
        record_reference_revision(
            conn,
            worker_name,
            "obligacion_internacional",
            row["codigo"],
            payload,
            row["source_url"],
        )
        count += 1
    return count


def upsert_aeat_model_references(conn, worker_name: str) -> dict[str, int]:
    formato_rows = conn.execute(
        text(
            """
            SELECT mc.id AS campana_id, am.codigo, mc.url_formato
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mc.url_formato IS NOT NULL
              AND mc.url_formato <> ''
              AND mc.activo = true
            """
        )
    ).mappings().fetchall()
    formatos = 0
    for row in formato_rows:
        existing = conn.execute(
            text(
                """
                SELECT id FROM modelo_formato
                WHERE campana_id = :campana_id
                  AND tipo_registro = 'official_reference'
                LIMIT 1
                """
            ),
            row,
        ).mappings().first()
        payload = {
            "campana_id": row["campana_id"],
            "tipo_registro": "official_reference",
            "campos": json.dumps({
                "source_url": row["url_formato"],
                "note": "AEAT official design-record reference. Parse exact fields from the official design document before serving field-level answers.",
            }),
            "url_diseno": row["url_formato"],
        }
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE modelo_formato
                    SET campos = CAST(:campos AS jsonb),
                        url_diseno = :url_diseno
                    WHERE id = :id
                    """
                ),
                {**payload, "id": existing["id"]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
                    VALUES (:campana_id, :tipo_registro, CAST(:campos AS jsonb), :url_diseno)
                    """
                ),
                payload,
            )
        record_reference_revision(conn, worker_name, "modelo_formato", str(row["campana_id"]), payload, row["url_formato"])
        formatos += 1

    obligation_rows = conn.execute(
        text(
            """
            SELECT codigo, nombre, url_info
            FROM aeat_modelo
            WHERE codigo = ANY(:codes)
              AND url_info IS NOT NULL
              AND url_info <> ''
            """
        ),
        {"codes": AEAT_OBLIGATION_MODELS},
    ).mappings().fetchall()
    obligaciones = 0
    for row in obligation_rows:
        payload = {
            "codigo": f"AEAT-MODELO-{row['codigo']}",
            "nombre": f"Obligacion fiscal asociada al modelo AEAT {row['codigo']}",
            "fuente": "AEAT",
            "organismo_emisor": "Agencia Estatal de Administracion Tributaria",
            "tipo_obligacion": "declaracion_o_autoliquidacion",
            "sujeto_obligado": "segun_normativa_del_modelo",
            "periodicidad": None,
            "reporte_modelo": row["codigo"],
            "ambito": "tributario",
            "estado_vigencia": "vigente_o_publicado_por_aeat",
            "documento_origen_tipo": "aeat_modelo",
            "documento_origen_ref": row["codigo"],
            "nota": (
                "Reference row derived from the official AEAT model page. "
                "Do not infer deadlines, thresholds, or subject scope from this row alone."
            ),
            "fuentes_operativas": json.dumps({"url_info": row["url_info"], "modelo_nombre": row["nombre"]}),
            "origen_metadato": "official_aeat_model_reference",
            "estado_metadato": "partial_reference",
        }
        conn.execute(
            text(
                """
                INSERT INTO obligacion_regulatoria (
                    codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                    sujeto_obligado, periodicidad, reporte_modelo, ambito,
                    estado_vigencia, documento_origen_tipo, documento_origen_ref,
                    nota, fuentes_operativas, ultima_actualizacion,
                    origen_metadato, estado_metadato
                )
                VALUES (
                    :codigo, :nombre, :fuente, :organismo_emisor, :tipo_obligacion,
                    :sujeto_obligado, :periodicidad, :reporte_modelo, :ambito,
                    :estado_vigencia, :documento_origen_tipo, :documento_origen_ref,
                    :nota, CAST(:fuentes_operativas AS jsonb), now(),
                    :origen_metadato, :estado_metadato
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    fuente = EXCLUDED.fuente,
                    organismo_emisor = EXCLUDED.organismo_emisor,
                    tipo_obligacion = EXCLUDED.tipo_obligacion,
                    sujeto_obligado = EXCLUDED.sujeto_obligado,
                    periodicidad = EXCLUDED.periodicidad,
                    reporte_modelo = EXCLUDED.reporte_modelo,
                    ambito = EXCLUDED.ambito,
                    estado_vigencia = EXCLUDED.estado_vigencia,
                    documento_origen_tipo = EXCLUDED.documento_origen_tipo,
                    documento_origen_ref = EXCLUDED.documento_origen_ref,
                    nota = EXCLUDED.nota,
                    fuentes_operativas = EXCLUDED.fuentes_operativas,
                    ultima_actualizacion = now(),
                    origen_metadato = EXCLUDED.origen_metadato,
                    estado_metadato = EXCLUDED.estado_metadato
                """
            ),
            payload,
        )
        record_reference_revision(conn, worker_name, "obligacion_regulatoria", payload["codigo"], payload, row["url_info"])
        obligaciones += 1

    return {"modelo_formato": formatos, "obligacion_regulatoria": obligaciones}


def run_sync(worker_name: str = "official-regulatory-references") -> dict[str, int]:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    ensure_database_connection(engine, logger=logger)
    started_at = datetime.now(UTC).isoformat()
    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            csrd = upsert_csrd_ess(conn, worker_name)
            dora = upsert_dora_incident_framework(conn, worker_name)
            sepa = upsert_sepa_rules(conn, worker_name)
            pbc = upsert_pbc_obligated_subjects(conn, worker_name)
            screening = upsert_screening_lists(conn, worker_name)
            irs = upsert_irs_references(conn, worker_name)
            international = upsert_international_obligations(conn, worker_name)
            aeat_refs = upsert_aeat_model_references(conn, worker_name)
            total = csrd + dora + sepa + pbc + screening + sum(irs.values()) + international + sum(aeat_refs.values())
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total,
                documentos_upserted=total,
                started_at=started_at,
            )
        return {
            "csrd_ess": csrd,
            "dora_framework": dora,
            "sepa_rules": sepa,
            "pbc_obligated_subjects": pbc,
            "screening_lists": screening,
            **irs,
            "obligacion_internacional": international,
            **aeat_refs,
        }
    except Exception as exc:
        if not handle_worker_failure(engine, worker_name, "official_references", "reference_sync", exc):
            logger.warning("Official reference sync moved to dead-letter")
            return {}
        with engine.begin() as conn:
            log_sync(conn, worker_name, "error", error_msg=str(exc), started_at=started_at)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Official regulatory reference worker")
    parser.add_argument("--run-once", action="store_true", help="Run one sync cycle")
    parser.add_argument("--interval", type=int, default=SYNC_INTERVAL_SECONDS)
    args = parser.parse_args()

    if args.run_once:
        result = run_sync()
        print(f"Official regulatory references sync complete: {result}")
        return

    while True:
        result = run_sync()
        print(f"Official regulatory references sync complete: {result}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
