import os
import uuid

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

ACCOUNT_UUIDS = {
    "1": "0159d6c7-973f-5e7a-a9a0-d195d0ea6fe2",
    "10": "0159d6c7-973f-5e7a-a9a0-d195d0ea6fe2",
    "100": "3c64bce0-4f00-54bc-a9fb-a2402a364b87",
    "110": "0159d6c7-973f-5e7a-a9a0-d195d0ea6fe2",
    "14": "db680066-c83d-5ed7-89a4-1d79466ea62d",
    "17": "db680066-c83d-5ed7-89a4-1d79466ea62d",
    "20": "66e549b7-01e2-5d07-98d5-430f74d8d3b2",
    "21": "292c8e99-2378-55aa-83d8-350e0ac3f1cc",
    "22": "0e3b230a-0509-55d8-96a0-9875f387a2be",
    "24": "a1b9b633-da11-58be-b1a9-5cfa2848f186",
    "3": "604ed872-ae2d-5d91-8e3e-572f3a3aaaa5",
    "30": "604ed872-ae2d-5d91-8e3e-572f3a3aaaa5",
    "4": "681046ff-9129-5ade-b11c-769864e02184",
    "40": "681046ff-9129-5ade-b11c-769864e02184",
    "472": "6c08ca44-3e28-55dc-ae58-b2db4021f662",
    "473": "759c652a-0944-5d8c-a3cd-a16d539354cd",
    "477": "a862e2eb-160d-584a-9356-0646e73fd657",
    "5": "681046ff-9129-5ade-b11c-769864e02184",
    "51": "f428abba-f3c6-50d1-ace0-b15fe2b42d8a",
    "52": "6768f5a2-051e-54ea-ad74-832847c693cf",
    "57": "dc9e84f6-774e-53fc-833f-a683841deef6",
    "572": "dc9e84f6-774e-53fc-833f-a683841deef6",
    "6": "083fc808-0906-5c2e-abd2-0d4c1603a9e2",
    "60": "083fc808-0906-5c2e-abd2-0d4c1603a9e2",
    "601": "f5286103-0609-5c94-b7b7-e46bafd15ac8",
    "61": "43ee290a-b01b-5a38-a99b-1afb62a7193a",
    "62": "18c2f394-3c7e-519c-9232-7a4470c7868f",
    "63": "08c02838-0ff8-5ad7-9ac9-66bac02971eb",
    "68": "22276c6f-08f9-5944-bcd2-81e6bf89fd72",
    "7": "85105cfe-bec4-5f56-971f-98d24a8063fd",
    "70": "85105cfe-bec4-5f56-971f-98d24a8063fd",
    "700": "1ca8abf3-3341-5726-be14-324f333b36c5",
}

ESTADOS = [
    ("1", "100", "Balance", "anual", 1, "anual", None, None, "Activo total = Patrimonio neto + Pasivo total"),
    ("1", "110", "Resultado de ejercicio", "anual", 2, "anual", None, None, "Ingresos - Gastos del ejercicio"),
    ("1", "120", "Estado de cambios en el patrimonio neto", "anual", 3, "anual", None, None, "Movimientos en fondos propios"),
    ("1", "130", "Estado de flujos de efectivo", "anual", 4, "anual", None, None, "Flujos de efectivo por actividad, inversión y financiación"),
    ("1", "140", "Memoria", "anual", 5, "anual", None, None, "Notas y aclaraciones a las cuentas anuales"),
    ("1", "101", "Balance trimestral", "trimestral", 1, "trimestral", None, None, "Activo total = Patrimonio neto + Pasivo total"),
    ("1", "102", "Balance semestral", "semestral", 1, "semestral", None, None, "Activo total = Patrimonio neto + Pasivo"),
    ("1", "111", "Resultado trimestral", "trimestral", 2, "trimestral", None, None, "Ingresos - Gastos"),
    ("1", "112", "Resultado semestral", "semestral", 2, "semestral", None, None, "Ingresos - Gastos"),
    ("1", "200", "Balance interino", "mensual", 1, "mensual", None, None, "Activo total = Patrimonio neto + Pasivo"),
    ("1", "201", "Resultado mensual", "mensual", 2, "mensual", None, None, "Ingresos - Gastos"),
    ("1", "300", "Balance consolidado", "anual", 1, "anual", None, None, "Activo total consolidado"),
    ("1", "301", "Resultado consolidado", "anual", 2, "anual", None, None, "Ingresos consolidados - Gastos consolidados"),
    ("1", "302", "Grupo consolidado", "anual", 3, "anual", None, None, "Estado de consolidación del grupo"),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    for e in ESTADOS:
        cuenta_ref, cuenta_code, estado, tipo_presentacion, orden, periodo, importe_base, importe_anterior, nota_pieds = e
        cuenta_id = ACCOUNT_UUIDS.get(cuenta_ref)
        cur.execute(
            """
            INSERT INTO pgc_estado_financiero (id, cuenta_id, estado, tipo_presentacion, orden, periodo, importe_base, importe_anterior, nota_pieds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(uuid.uuid5(uuid.NAMESPACE_DNS, cuenta_ref)), cuenta_id, estado, periodo, orden, periodo, importe_base, importe_anterior, nota_pieds),
        )

    conn.commit()
    print(f"Seeded {len(ESTADOS)} pgc_estado_financiero records")
    conn.close()


if __name__ == "__main__":
    seed()
