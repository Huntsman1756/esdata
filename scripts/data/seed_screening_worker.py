"""
Seed script for Screening — Sanctions, PEPs, and watchlist reference data.
Source: apps/workers/screening.py
Tables: screening_lists, screening_entries, screening_matches
Upsert keys: screening_lists.codigo, screening_entries.(list_id, entidad_id), screening_matches.(empresa_id, entry_id)
"""

import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LISTS_DATA = [
    ("OFAC_SDN", "OFAC Specially Designated Nationals List", "sanctions",
     "U.S. Department of the Treasury - OFAC", "US",
     "https://sanctionssearch.ofac.treasury.gov/",
     "Lista de nacionales especialmente designados del Tesoro de EE.UU. por actividades terroristas, narcotrafico y proliferacion de armas.",
     "2026-04-01", True),
    ("EU_SANCTIONS", "EU Consolidated Sanctions List", "sanctions",
     "Council of the European Union", "EU",
     "https://www.consilium.europa.eu/en/policies/sanctions/",
     "Lista consolidada de sanciones de la Union Europea para regimenes de sanciones.",
     "2026-04-10", True),
    ("UN_SANCTIONS", "UN Security Council Consolidated List", "sanctions",
     "United Nations Security Council", "UN",
     "https://securitycouncilreport.org/whats-on/consolidated-list.php",
     "Lista consolidada del Consejo de Seguridad de la ONU.",
     "2026-03-15", True),
    ("SEPBLAC", "SEPBLAC Inhabilitados y Sancionados", "watchlist",
     "SEPBLAC - Servicio Ejecutivo de la Comision de Prevencion del Blanqueo de Capitales", "ES",
     None,
     "Lista de entidades y personas sancionadas por SEPBLAC.",
     "2026-02-20", True),
    ("ES_PEPS", "PEPs Espana - Cargos Publicos de Alto Nivel", "pep",
     "Ministerio de Asuntos Exteriores - Espana", "ES",
     None,
     "Personas expuestas politicamente de Espana.",
     "2026-01-10", True),
]

ENTRIES_DATA = [
    ("OFAC_SDN", "OFAC-25001", "AL-RASHID TRADING COMPANY",
     "AL-RASHID TRADING COMPANY", "entity", "SY", None, None,
     ["RASHID TRADING", "RASHID CO"], ["sanctions", "syria"],
     "Entity involved in proliferation activities", "2024-06-15", None, None,
     True, '{"program": "SYRIA", "executive_order": "13582"}'),
    ("OFAC_SDN", "OFAC-25002", "GLOBAL FINANCE HOLDINGS LLC",
     "GLOBAL FINANCE HOLDINGS LLC", "entity", "IR", None, None,
     ["GFH LLC", "GLOBAL FINANCE"], ["sanctions", "iran", "financial"],
     "Financial institution supporting illicit activities", "2025-01-20", None, None,
     True, '{"program": "IRAN", "executive_order": "13224"}'),
    ("OFAC_SDN", "OFAC-25003", "PETRO-ENERGY INTERNATIONAL",
     "PETRO-ENERGY INTERNATIONAL", "entity", "RU", None, None,
     ["PETRO-ENERGY INTL", "PEI"], ["sanctions", "russia", "energy"],
     "Energy sector entity subject to sectoral sanctions", "2025-03-01", None, None,
     True, '{"program": "UKRAINE-EO13662", "sector": "energy"}'),
    ("OFAC_SDN", "OFAC-25004", "MARITIME SHIPPING CORP",
     "MARITIME SHIPPING CORP", "entity", "KP", None, None,
     ["MSC SHIPPING", "MARITIME CORP"], ["sanctions", "north_korea", "shipping"],
     "Shipping company involved in illicit trade", "2024-11-10", None, None,
     True, '{"program": "DPRK"}'),
    ("EU_SANCTIONS", "EU-30001", "BELARUS INDUSTRIAL GROUP",
     "BELARUS INDUSTRIAL GROUP", "entity", "BY", None, None,
     ["BIG BELARUS", "BELIND GROUP"], ["sanctions", "belarus"],
     "Entity supporting the Belarusian regime", "2024-08-25", None, None,
     True, '{"regime": "lukashenko", "decision": "2024/2101"}'),
    ("EU_SANCTIONS", "EU-30002", "DONBAS ENERGY SOLUTIONS",
     "DONBAS ENERGY SOLUTIONS", "entity", "RU", None, None,
     ["DONBAS ENERGY", "DES HOLDINGS"], ["sanctions", "russia", "ukraine"],
     "Energy company in occupied territories", "2025-02-14", None, None,
     True, '{"regime": "ukraine", "decision": "2024/2102"}'),
    ("UN_SANCTIONS", "UN-40001", "AHMED AL-MANSOUR",
     "AHMED AL-MANSOUR", "person", "YE", "YE-8821003", "1965-03-20",
     ["A. AL-MANSOUR", "AHMED MANSOUR"], ["sanctions", "yemen", "arms"],
     "Individual involved in arms trafficking", "2023-12-01", None, None,
     True, '{"resolution": "1718", "dob": "20-mar-1965"}'),
    ("UN_SANCTIONS", "UN-40002", "JOSE LUIS MENDEZ",
     "JOSE LUIS MENDEZ", "person", "VE", "VE-12345678", "1970-07-15",
     ["J.L. MENDEZ", "JOSE MENDEZ"], ["sanctions", "venezuela"],
     "Individual involved in corruption (fictitious test data)", "2025-05-01", None, None,
     True, '{"resolution": "2671", "dob": "15-jul-1970"}'),
    ("SEPBLAC", "SEPBLAC-50001", "TRANSFINANCIERA IBERICA SL",
     "TRANSFINANCIERA IBERICA SL", "entity", "ES", "ES-B12345678", None,
     ["TRANSFINANCIERA", "TRANSFINANCIERA IBERICA"],
     ["sancion_administrativa", "infraccion_grave"],
     "Sancionada por infracciones graves en materia AML (dato ficticio)",
     "2024-09-10", None, None, True,
     '{"resolucion": "2024/AML/045", "infraccion": "grave"}'),
    ("SEPBLAC", "SEPBLAC-50002", "SERVICIOS FINANCIEROS DEL SUR SA",
     "SERVICIOS FINANCIEROS DEL SUR SA", "entity", "ES", "ES-A87654321", None,
     ["SERVICIOS FINANCIEROS DEL SUR", "SERFIN SUR"],
     ["sancion_administrativa", "infraccion_muy_grave"],
     "Sancionada por no cumplir obligaciones de prevencion (dato ficticio)",
     "2025-01-05", None, None, True,
     '{"resolucion": "2025/AML/012", "infraccion": "muy_grave"}'),
    ("ES_PEPS", "PEP-ES-60001", "CARLOS RODRIGUEZ FERNANDEZ",
     "CARLOS RODRIGUEZ FERNANDEZ", "person", "ES", "ES-12345678A", "1968-05-10",
     ["C. RODRIGUEZ", "CARLOS RODRIGUEZ"],
     ["pep_nacional", "minister", "ex-ministro_hacienda"],
     "Ex-ministro de hacienda (dato ficticio para testing)",
     None, None, None, True,
     '{"cargo": "ex_ministro_hacienda", "periodo": "2018-2023"}'),
    ("ES_PEPS", "PEP-ES-60002", "MARIA TERESA GARCIA LOPEZ",
     "MARIA TERESA GARCIA LOPEZ", "person", "ES", "ES-87654321B", "1975-11-22",
     ["M.T. GARCIA", "MARIA GARCIA LOPEZ"],
     ["pep_nacional", "secretaria_de_estado"],
     "Secretaria de Estado de Comercio (dato ficticio para testing)",
     None, None, None, True,
     '{"cargo": "secretaria_comercio", "periodo": "2021-presente"}'),
    ("ES_PEPS", "PEP-ES-60003", "JAVIER MARTINEZ RUIZ",
     "JAVIER MARTINEZ RUIZ", "person", "ES", "ES-11223344C", "1972-03-08",
     ["J. MARTINEZ", "JAVIER MARTINEZ RUIZ"],
     ["pep_nacional", "presidente_comunidad_autonoma"],
     "Presidente de una comunidad autonoma (dato ficticio para testing)",
     None, None, None, True,
     '{"cargo": "presidente_ccaa", "periodo": "2023-presente"}'),
    ("ES_PEPS", "PEP-ES-60004", "ISABEL FERNANDEZ TORRES",
     "ISABEL FERNANDEZ TORRES", "person", "ES", "ES-99887766D", "1980-04-15",
     ["I. FERNANDEZ", "ISABEL FERNANDEZ TORRES"],
     ["pep_nacional", "consejera"],
     "Consejera de Economia de una comunidad autonoma (dato ficticio para testing)",
     None, None, None, True,
     '{"cargo": "consejera_economia", "periodo": "2022-presente"}'),
]


def main():
    print("Seeding screening data...")
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://esdata:esdata_dev@localhost:5432/esdata",
    )
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()

        # Upsert screening lists
        list_ids = {}
        for l in LISTS_DATA:
            cur.execute(
                """INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais,
                   url_fuente, descripcion, actualizada, activo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo)
                   DO UPDATE SET
                       nombre = EXCLUDED.nombre,
                       tipo = EXCLUDED.tipo,
                       organismo = EXCLUDED.organismo,
                       pais = EXCLUDED.pais,
                       url_fuente = EXCLUDED.url_fuente,
                       descripcion = EXCLUDED.descripcion,
                       actualizada = EXCLUDED.actualizada,
                       activo = EXCLUDED.activo""",
                l,
            )
            cur.execute("SELECT id FROM screening_lists WHERE codigo = %s", (l[0],))
            list_ids[l[0]] = cur.fetchone()[0]

        # Upsert screening entries
        entry_ids = {}
        for e in ENTRIES_DATA:
            list_id = list_ids[e[0]]
            cur.execute(
                """INSERT INTO screening_entries (list_id, entidad_id, nombre,
                   nombre_normalizado, tipo_entidad, pais, nif, fecha_nacimiento,
                   aliases, categorias, descripcion, fecha_sancion, fecha_alta,
                   fecha_baja, activo, metadata_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (list_id, entidad_id)
                   DO UPDATE SET
                       nombre = EXCLUDED.nombre,
                       nombre_normalizado = EXCLUDED.nombre_normalizado,
                       tipo_entidad = EXCLUDED.tipo_entidad,
                       pais = EXCLUDED.pais,
                       nif = EXCLUDED.nif,
                       fecha_nacimiento = EXCLUDED.fecha_nacimiento,
                       aliases = EXCLUDED.aliases,
                       categorias = EXCLUDED.categorias,
                       descripcion = EXCLUDED.descripcion,
                       fecha_sancion = EXCLUDED.fecha_sancion,
                       fecha_alta = EXCLUDED.fecha_alta,
                       fecha_baja = EXCLUDED.fecha_baja,
                       activo = EXCLUDED.activo,
                       metadata_json = EXCLUDED.metadata_json""",
                (list_id,) + e[1:],
            )
            cur.execute(
                "SELECT id FROM screening_entries WHERE list_id = %s AND entidad_id = %s",
                (list_id, e[1]),
            )
            entry_ids[e[1]] = cur.fetchone()[0]

        conn.commit()

        # Upsert screening matches
        empresa_id = cur.execute(
            "SELECT id FROM empresa WHERE nombre = 'IBERBANK, S.A.' LIMIT 1"
        ).fetchone()
        if empresa_id:
            empresa_id = empresa_id[0]
            matches = [
                (empresa_id, entry_ids["OFAC-25002"], list_ids["OFAC_SDN"], 0.92,
                 "Nombre y NIF coinciden con screening de contraparte",
                 "nombre+nif", "PETROVA, Ivan D. — NIF: 7712345678",
                 False, None, None, "Pendiente de revision por compliance"),
                (empresa_id, entry_ids["EU-30001"], list_ids["EU_SANCTIONS"], 0.87,
                 "Coincidencia parcial de nombre",
                 "nombre", "VOLKOV, Sergey M.",
                 False, None, None, "Mismo nombre que contraparte empresarial"),
                (empresa_id, entry_ids["UN-40001"], list_ids["UN_SANCTIONS"], 0.95,
                 "Nombre coincide con contraparte en lista de sancionados",
                 "nombre", "AHMED AL-MANSOUR",
                 True, "compliance.officer", "2026-04-15 10:30:00+00",
                 "Falso positivo — mismo nombre, sin relacion"),
                (empresa_id, entry_ids["PEP-ES-60001"], list_ids["ES_PEPS"], 0.88,
                 "PEP detected during customer onboarding",
                 "nombre", "CARLOS RODRIGUEZ FERNANDEZ",
                 True, "compliance.officer", "2026-04-15 11:00:00+00",
                 "Cliente PEP — enriquecimiento de datos aplicado"),
                (empresa_id, entry_ids["SEPBLAC-50001"], list_ids["SEPBLAC"], 0.99,
                 "Nombre exacto de entidad en lista de SEPBLAC",
                 "nombre", "TRANSFINANCIERA IBERICA SL",
                 True, "compliance.officer", "2026-04-15 11:30:00+00",
                 "Bloqueada — entidad en lista de SEPBLAC"),
            ]
            for m in matches:
                cur.execute(
                    """INSERT INTO screening_matches (empresa_id, entry_id, list_id,
                       confianza, motivo, match_campo, match_texto, revisado, revisor,
                       revisado_at, notas)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (empresa_id, entry_id)
                       DO UPDATE SET
                           confianza = EXCLUDED.confianza,
                           motivo = EXCLUDED.motivo,
                           match_campo = EXCLUDED.match_campo,
                           revisado = EXCLUDED.revisado,
                           notas = EXCLUDED.notas""",
                    m,
                )
            conn.commit()

    total = len(LISTS_DATA) + len(ENTRIES_DATA) + len(matches) if empresa_id else len(LISTS_DATA) + len(ENTRIES_DATA)
    print(f"Done. {total} screening records seeded.")


if __name__ == "__main__":
    main()
