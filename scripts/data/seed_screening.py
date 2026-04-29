#!/usr/bin/env python3
"""Seed Screening — Listas de sanciones, PEPs y matches de ejemplo.

Cubre listas UE, UN, OFAC con entries y matches de screening.

Uso:
    python scripts/data/seed_screening.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


LISTS_DATA = [
    {
        "codigo": "OFAC_SDN",
        "nombre": "OFAC Specially Designated Nationals List",
        "tipo": "sanctions",
        "organismo": "OFAC (US Treasury)",
        "pais": "US",
        "url_fuente": "https://sanctionssearch.ofac.treas.gov/",
        "descripcion": "Lista de personas y entidades designadas por el Tesoro de EE.UU. por actividades terroristas, narcotrafico, proliferacion de armas.",
        "actualizada": "2026-04-01",
    },
    {
        "codigo": "EU_SANCTIONS",
        "nombre": "EU Consolidated Sanctions List",
        "tipo": "sanctions",
        "organismo": "Consejo de la Union Europea",
        "pais": "EU",
        "url_fuente": "https://www.sanctionsmap.eu/",
        "descripcion": "Lista consolidada de sanciones de la UE para regimenes de sanciones (Rusia, Iran, Corea del Norte, terrorismo).",
        "actualizada": "2026-04-01",
    },
    {
        "codigo": "UN_SANCTIONS",
        "nombre": "UN Security Council Sanctions List",
        "tipo": "sanctions",
        "organismo": "Naciones Unidas",
        "pais": "UN",
        "url_fuente": "https://www.un.org/securitycouncil/sanctions/information",
        "descripcion": "Lista de sanciones del Consejo de Seguridad de la ONU (Al-Qaida, Taliban, Iran, Corea del Norte).",
        "actualizada": "2026-04-01",
    },
    {
        "codigo": "EU_PEP",
        "nombre": "EU High-Risk Third-Country PEPs List",
        "tipo": "pep",
        "organismo": "Comision Europea",
        "pais": "EU",
        "url_fuente": "https://eur-lex.europa.eu/eli/dir/2018/1673/oj",
        "descripcion": "Lista de Personas Expuestas Politicamente de alto riesgo de paises terceros segun directiva 2018/1673.",
        "actualizada": "2026-03-15",
    },
    {
        "codigo": "BE_MALFEASANCE",
        "nombre": "Belgian List of Malfeasance",
        "tipo": "watchlist",
        "organismo": "Estado Belga",
        "pais": "BE",
        "url_fuente": "https://kbfb.fgov.be/en/lists-and-registers/malfeasance-list.html",
        "descripcion": "Lista belga de personas y entidades involucradas en corrupcion y malversacion.",
        "actualizada": "2026-02-01",
    },
]


ENTRIES_DATA = [
    # OFAC SDN
    {"list_codigo": "OFAC_SDN", "entidad_id": "OFAC-24001", "nombre": "AL-KHALIJ TRADING CO.", "nombre_normalizado": "AL-KHALIJ TRADING CO.", "tipo_entidad": "entity", "pais": "SY", "nif": None, "fecha_nacimiento": None, "aliases": ["AL-KHALIJ TRADING", "KHALIJ TRADE"], "categorias": ["Syria", "Terrorism"], "descripcion": "Entity designated for supporting terrorist activities in Syria", "fecha_sancion": "2024-03-15", "activo": True},
    {"list_codigo": "OFAC_SDN", "entidad_id": "OFAC-24002", "nombre": "PETROVA, Ivan Dmitrievich", "nombre_normalizado": "PETROVA IVAN DMITRIEVICH", "tipo_entidad": "person", "pais": "RU", "nif": "7712345678", "fecha_nacimiento": "1965-03-22", "aliases": ["IVAN PETROV", "I.D. PETROVA"], "categorias": ["Russia", "EO14024"], "descripcion": "Russian official designated under EO 14024", "fecha_sancion": "2024-06-10", "activo": True},
    {"list_codigo": "OFAC_SDN", "entidad_id": "OFAC-24003", "nombre": "NATIONAL IRANIAN POST BANK", "nombre_normalizado": "NATIONAL IRANIAN POST BANK", "tipo_entidad": "entity", "pais": "IR", "nif": None, "fecha_nacimiento": None, "aliases": ["NIPB"], "categorias": ["Iran", "Nuclear Proliferation"], "descripcion": "Iranian bank designated for supporting nuclear proliferation", "fecha_sancion": "2023-11-20", "activo": True},
    {"list_codigo": "OFAC_SDN", "entidad_id": "OFAC-24004", "nombre": "AL-RAZZAQ TRANSPORT", "nombre_normalizado": "AL-RAZZAQ TRANSPORT", "tipo_entidad": "entity", "pais": "SY", "nif": None, "fecha_nacimiento": None, "aliases": ["AL-RAZZAQ GROUP"], "categorias": ["Syria", "Terrorism"], "descripcion": "Transport company linked to terrorist financing", "fecha_sancion": "2024-01-05", "activo": True},
    {"list_codigo": "OFAC_SDN", "entidad_id": "OFAC-24005", "nombre": "MOHAMMED, Ali Hassan", "nombre_normalizado": "MOHAMMED ALI HASSAN", "tipo_entidad": "person", "pais": "SO", "nif": None, "fecha_nacimiento": "1978-07-14", "aliases": ["ALI HASSAN MOHAMMED"], "categorias": ["Somalia", "Terrorism"], "descripcion": "Individual associated with Al-Shabaab", "fecha_sancion": "2024-02-28", "activo": True},
    # EU Sanctions
    {"list_codigo": "EU_SANCTIONS", "entidad_id": "EU-24001", "nombre": "VOLKOV, Sergey Mikhailovich", "nombre_normalizado": "VOLKOV SERGEY MIKHAILOVICH", "tipo_entidad": "person", "pais": "RU", "nif": "7798765432", "fecha_nacimiento": "1960-11-03", "aliases": ["S.M. VOLKOV"], "categorias": ["Russia", "EU Sanctions"], "descripcion": "Russian business figure subject to EU asset freeze", "fecha_sancion": "2024-02-15", "activo": True},
    {"list_codigo": "EU_SANCTIONS", "entidad_id": "EU-24002", "nombre": "BELARUSIAN CEMENT COMPANY", "nombre_normalizado": "BELARUSIAN CEMENT COMPANY", "tipo_entidad": "entity", "pais": "BY", "nif": None, "fecha_nacimiento": None, "aliases": ["BELCEMENT"], "categorias": ["Belarus", "EU Sanctions"], "descripcion": "Belarusian state-owned enterprise supporting the Belarusian regime", "fecha_sancion": "2023-08-10", "activo": True},
    {"list_codigo": "EU_SANCTIONS", "entidad_id": "EU-24003", "nombre": "SYRIAN AIRLINES", "nombre_normalizado": "SYRIAN AIRLINES", "tipo_entidad": "entity", "pais": "SY", "nif": None, "fecha_nacimiento": None, "aliases": ["SAC"], "categorias": ["Syria", "EU Sanctions"], "descripcion": "Syrian state airline subject to EU operating ban", "fecha_sancion": "2012-07-19", "activo": True},
    # UN Sanctions
    {"list_codigo": "UN_SANCTIONS", "entidad_id": "UN-24001", "nombre": "AL-QAIDA NETWORK", "nombre_normalizado": "AL-QAIDA NETWORK", "tipo_entidad": "entity", "pais": "AF", "nif": None, "fecha_nacimiento": None, "aliases": ["AL-QAIDA", "AL QAIDA"], "categorias": ["Al-Qaida", "Terrorism"], "descripcion": "Global terrorist network subject to UN sanctions", "fecha_sancion": "1999-10-15", "activo": True},
    {"list_codigo": "UN_SANCTIONS", "entidad_id": "UN-24002", "nombre": "ISLAMIC STATE", "nombre_normalizado": "ISLAMIC STATE", "tipo_entidad": "entity", "pais": "IQ", "nif": None, "fecha_nacimiento": None, "aliases": ["ISIS", "ISIL", "DAESH"], "categorias": ["ISIS", "Terrorism"], "descripcion": "Terrorist organization subject to UN sanctions", "fecha_sancion": "2014-08-06", "activo": True},
    {"list_codigo": "UN_SANCTIONS", "entidad_id": "UN-24003", "nombre": "KIM, Jong Un", "nombre_normalizado": "KIM JONG UN", "tipo_entidad": "person", "pais": "KP", "nif": None, "fecha_nacimiento": "1984-01-08", "aliases": ["KIM JONG-UN"], "categorias": ["North Korea", "Nuclear Proliferation"], "descripcion": "Leader of North Korea subject to UN sanctions", "fecha_sancion": "2006-10-14", "activo": True},
    # EU PEP
    {"list_codigo": "EU_PEP", "entidad_id": "EU-PEP-001", "nombre": "GARCIA RODRIGUEZ, Maria del Carmen", "nombre_normalizado": "GARCIA RODRIGUEZ MARIA CARMEN", "tipo_entidad": "person", "pais": "ES", "nif": "12345678A", "fecha_nacimiento": "1968-05-12", "aliases": [], "categorias": ["Minister", "Spain"], "descripcion": "Former Spanish Minister of Economy — PEP domestic", "fecha_sancion": None, "activo": True},
    {"list_codigo": "EU_PEP", "entidad_id": "EU-PEP-002", "nombre": "MARTINEZ LOPEZ, Jose Luis", "nombre_normalizado": "MARTINEZ LOPEZ JOSE LUIS", "tipo_entidad": "person", "pais": "ES", "nif": "87654321B", "fecha_nacimiento": "1972-09-30", "aliases": [], "categorias": ["Regional Politician", "Spain"], "descripcion": "Former regional president of Andalusia — PEP domestic", "fecha_sancion": None, "activo": True},
    {"list_codigo": "EU_PEP", "entidad_id": "EU-PEP-003", "nombre": "CHEN, Wei Ming", "nombre_normalizado": "CHEN WEI MING", "tipo_entidad": "person", "pais": "CN", "nif": None, "fecha_nacimiento": "1965-02-20", "aliases": [], "categorias": ["Foreign Politician", "China"], "descripcion": "Chinese provincial governor — PEP foreign high-risk", "fecha_sancion": None, "activo": True},
    # Belgian Malfeasance
    {"list_codigo": "BE_MALFEASANCE", "entidad_id": "BE-MAL-001", "nombre": "CORPORACION DEL NORTE SA", "nombre_normalizado": "CORPORACION DEL NORTE SA", "tipo_entidad": "entity", "pais": "BE", "nif": "BE0123456789", "fecha_nacimiento": None, "aliases": [], "categorias": ["Corruption", "Bribery"], "descripcion": "Company convicted of corruption and bribery in Belgium", "fecha_sancion": "2023-06-15", "activo": True},
]


MATCHES_DATA = [
    {"entidad_id": "OFAC-24002", "list_codigo": "OFAC_SDN", "confianza": 0.92, "motivo": "Nombre y NIF coinciden con screening de contraparte", "match_campo": "nombre+nif", "match_texto": "PETROVA, Ivan D. — NIF: 7712345678", "revisado": False, "notas": "Pendiente de revision por compliance"},
    {"entidad_id": "EU-24001", "list_codigo": "EU_SANCTIONS", "confianza": 0.87, "motivo": "Coincidencia parcial de nombre", "match_campo": "nombre", "match_texto": "VOLKOV, Sergey M.", "revisado": False, "notas": "Mismo nombre que contraparte empresarial"},
    {"entidad_id": "UN-24003", "list_codigo": "UN_SANCTIONS", "confianza": 0.95, "motivo": "Nombre coincide con contraparte en lista de sancionados", "match_campo": "nombre", "match_texto": "KIM, Jong Un", "revisado": True, "notas": "Falso positivo — mismo nombre, sin relacion"},
    {"entidad_id": "EU-PEP-001", "list_codigo": "EU_PEP", "confianza": 0.88, "motivo": "PEP detected during customer onboarding", "match_campo": "nombre", "match_texto": "GARCIA RODRIGUEZ, Maria del Carmen", "revisado": True, "notas": "Cliente PEP — enriquecimiento de datos aplicado"},
    {"entidad_id": "OFAC-24005", "list_codigo": "OFAC_SDN", "confianza": 0.78, "motivo": "Coincidencia parcial en alias", "match_campo": "alias", "match_texto": "MOHAMMED, Ali H.", "revisado": False, "notas": "Requiere revision manual"},
    {"entidad_id": "BE-MAL-001", "list_codigo": "BE_MALFEASANCE", "confianza": 0.99, "motivo": "Nombre exacto de entidad en lista de malfeasance", "match_campo": "nombre", "match_texto": "CORPORACION DEL NORTE SA", "revisado": True, "notas": "Bloqueada — entidad en lista belga de malversacion"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed Screening data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(LISTS_DATA)} screening lists")
        total_entries = len(ENTRIES_DATA)
        print(f"[DRY RUN] Would insert {total_entries} screening entries")
        for l in LISTS_DATA:
            count = sum(1 for e in ENTRIES_DATA if e["list_codigo"] == l["codigo"])
            print(f"  {l['codigo']}: {count} entries")
        print(f"[DRY RUN] Would insert {len(MATCHES_DATA)} screening matches")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert lists
    list_ids = {}
    for l in LISTS_DATA:
        cur.execute(
            """INSERT INTO screening_lists (codigo, nombre, tipo, organismo, pais,
               url_fuente, descripcion, actualizada)
               VALUES (%(codigo)s, %(nombre)s, %(tipo)s, %(organismo)s, %(pais)s,
                       %(url_fuente)s, %(descripcion)s, %(actualizada)s)
               ON CONFLICT (codigo) DO UPDATE SET
                   nombre = EXCLUDED.nombre, tipo = EXCLUDED.tipo""",
            l,
        )
        cur.execute("SELECT id FROM screening_lists WHERE codigo = %s", (l["codigo"],))
        list_ids[l["codigo"]] = cur.fetchone()[0]

    # Insert entries
    entry_ids = {}
    for e in ENTRIES_DATA:
        entry = dict(e)
        entry["list_id"] = list_ids[e["list_codigo"]]
        cur.execute(
            """INSERT INTO screening_entries (list_id, entidad_id, nombre, nombre_normalizado,
               tipo_entidad, pais, nif, fecha_nacimiento, aliases, categorias,
               descripcion, fecha_sancion, activo)
               VALUES (%(list_id)s, %(entidad_id)s, %(nombre)s, %(nombre_normalizado)s,
                       %(tipo_entidad)s, %(pais)s, %(nif)s, %(fecha_nacimiento)s,
                       %(aliases)s, %(categorias)s, %(descripcion)s, %(fecha_sancion)s,
                       %(activo)s)
               ON CONFLICT (list_id, entidad_id) DO UPDATE SET
                   nombre = EXCLUDED.nombre, tipo_entidad = EXCLUDED.tipo_entidad""",
            entry,
        )
        cur.execute("SELECT id FROM screening_entries WHERE list_id = %s AND entidad_id = %s",
                     (list_ids[e["list_codigo"]], e["entidad_id"]))
        entry_ids[e["entidad_id"]] = cur.fetchone()[0]

    # Insert matches
    for m in MATCHES_DATA:
        entry_id = entry_ids.get(m["entidad_id"])
        if entry_id:
            cur.execute(
                """INSERT INTO screening_matches (empresa_id, entry_id, list_id, confianza, motivo,
                   match_campo, match_texto, revisado, notas)
                   VALUES ((SELECT id FROM empresa WHERE nombre = 'IBERBANK, S.A.'), %(entry_id)s, %(list_id)s, %(confianza)s, %(motivo)s,
                           %(match_campo)s, %(match_texto)s, %(revisado)s, %(notas)s)
                   ON CONFLICT (empresa_id, entry_id) DO UPDATE SET
                       confianza = EXCLUDED.confianza, motivo = EXCLUDED.motivo""",
                {
                    "entry_id": entry_id,
                    "list_id": list_ids[m["list_codigo"]],
                    "confianza": m["confianza"],
                    "motivo": m["motivo"],
                    "match_campo": m["match_campo"],
                    "match_texto": m["match_texto"],
                    "revisado": m["revisado"],
                    "notas": m["notas"],
                },
            )

    conn.commit()
    total = len(LISTS_DATA) + len(ENTRIES_DATA) + len(MATCHES_DATA)
    print(f"OK: {total} registros screening insertados ({len(LISTS_DATA)} lists, {len(ENTRIES_DATA)} entries, {len(MATCHES_DATA)} matches)")
    conn.close()


if __name__ == "__main__":
    main()
