import os
import uuid

import psycopg

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

FISCAL_REFS = [
    ("100", "100", "100", "", "Capital social → IRPF 100/110/111"),
    ("100", "200", "200", "", "Capital social → IS base imponible"),
    ("170", "303", "", "", "Deudas → IVA trimestral deducible"),
    ("175", "303", "", "", "Préstamos bancarios → IVA deducible"),
    ("174", "200", "200", "", "Bonos y obligaciones → IS"),
    ("214", "303", "", "", "Equipo informático → IVA deducible"),
    ("215", "303", "", "", "Mobiliario → IVA deducible"),
    ("216", "303", "", "", "Equipos transporte → IVA deducible"),
    ("400", "303", "", "", "Acreedores por compras → IVA soportado"),
    ("410", "303", "", "", "Clientes → IVA repercutido"),
    ("410", "347", "", "", "Clientes → Modelo 347 (operaciones > 3.005,06€)"),
    ("410", "349", "", "", "Clientes → Factura Intracomunitaria 349"),
    ("420", "111", "", "", "Personal → Retenciones IRPF 111"),
    ("420", "114", "", "", "Personal → Retenciones IRPF 114"),
    ("441", "303", "", "", "Crédito IVA → IVA trimestral 303"),
    ("442", "303", "", "", "Devolución IVA → IVA trimestral 303"),
    ("446", "303", "", "", "Crédito IVA operativo → 303"),
    ("447", "303", "", "", "Crédito autoliquidaciones → 303"),
    ("470", "200", "", "", "Pagos fraccionados → IS"),
    ("471", "303", "", "", "Hacienda acreedora IVA → 303"),
    ("471", "390", "", "", "Hacienda acreedora IVA → Anual 390"),
    ("472", "100", "", "", "IRPF pendiente de ingreso → 100"),
    ("472", "111", "", "", "IRPF pendiente → 111"),
    ("473", "124", "", "", "Retenciones IRNR → 124"),
    ("473", "216", "", "", "Retenciones IRNR → 216"),
    ("474", "309", "", "", "ITPAJD → 309"),
    ("475", "200", "", "", "IS → 200"),
    ("475", "269", "", "", "IS tramo estatal → 269"),
    ("476", "303", "", "", "Cuotas trimestrales → 303"),
    ("476", "116", "", "", "Cuotas trimestrales → 116"),
    ("500", "187", "", "", "Acciones → IRPF 187"),
    ("500", "193", "", "", "Acciones → IRPF 193"),
    ("502", "212", "", "", "Participaciones grupo → 212"),
    ("503", "212", "", "", "Participaciones asociada → 212"),
    ("507", "196", "", "", "Deuda valores → IRPF 196"),
    ("508", "198", "", "", "Derivados → IRPF 198"),
    ("600", "303", "", "", "Compras mercaderías → IVA soportado 303"),
    ("600", "347", "", "", "Compras mercaderías → Modelo 347"),
    ("610", "303", "", "", "Arrendamientos → IVA soportado"),
    ("610", "347", "", "", "Arrendamientos → Modelo 347"),
    ("611", "303", "", "", "Reparaciones → IVA soportado"),
    ("612", "303", "", "", "Transportes → IVA soportado"),
    ("614", "303", "", "", "Publicidad → IVA soportado"),
    ("615", "303", "", "", "Servicios profesionales → IVA soportado"),
    ("616", "303", "", "", "Suministros → IVA soportado"),
    ("640", "100", "", "", "Sueldos → IRPF 100"),
    ("640", "111", "", "", "Sueldos → IRPF 111"),
    ("642", "100", "", "", "SS empresa → IRPF 100 deducible"),
    ("642", "200", "", "", "SS empresa → IS deducible"),
    ("660", "200", "", "", "Intereses deudas → IS deducible"),
    ("660", "100", "", "", "Intereses deudas → IRPF 100 deducible"),
    ("664", "200", "", "", "Diferencias cambio → IS"),
    ("664", "100", "", "", "Diferencias cambio → IRPF 100"),
    ("680", "200", "", "", "Amortización material → IS deducible"),
    ("680", "100", "", "", "Amortización material → IRPF 100 deducible"),
    ("681", "200", "", "", "Amortización inmaterial → IS deducible"),
    ("700", "303", "", "", "Ventas mercaderías → IVA repercutido 303"),
    ("700", "347", "", "", "Ventas mercaderías → Modelo 347"),
    ("700", "349", "", "", "Ventas mercaderías → FactA 349"),
    ("700", "390", "", "", "Ventas mercaderías → IVA anual 390"),
    ("700", "394", "", "", "Ventas mercaderías → SII 394"),
    ("701", "303", "", "", "Ventas productos → IVA repercutido"),
    ("701", "347", "", "", "Ventas productos → Modelo 347"),
    ("701", "349", "", "", "Ventas productos → FactA 349"),
    ("720", "200", "", "", "Subvenciones capital → IS no tributarias"),
    ("721", "200", "", "", "Subvenciones explotacion → IS base imponible"),
]

AEAT_MODEL_REFS = [
    ("100", "100", "", "Capital social → IRPF 100"),
    ("100", "110", "", "Capital social → IRPF 110 sustitutivo"),
    ("175", "303", "", "Préstamos → IVA trimestral"),
    ("214", "303", "", "Equipo informático → IVA deducible"),
    ("400", "303", "", "Acreedores → IVA soportado"),
    ("400", "347", "", "Acreedores → Modelo 347"),
    ("410", "303", "", "Clientes → IVA repercutido"),
    ("410", "347", "", "Clientes → Modelo 347"),
    ("410", "349", "", "Clientes → FactA 349"),
    ("420", "111", "", "Personal → IRPF 111"),
    ("420", "114", "", "Personal → IRPF 114"),
    ("441", "303", "", "Crédito IVA → 303"),
    ("446", "303", "", "Crédito IVA operativo → 303"),
    ("471", "303", "", "Hacienda acreedora IVA → 303"),
    ("471", "390", "", "Hacienda acreedora IVA → 390"),
    ("472", "100", "", "IRPF pendiente → 100"),
    ("472", "111", "", "IRPF pendiente → 111"),
    ("475", "200", "", "IS → 200"),
    ("475", "269", "", "IS tramo estatal → 269"),
    ("476", "303", "", "Cuotas trimestrales → 303"),
    ("500", "187", "", "Acciones → IRPF 187"),
    ("500", "193", "", "Acciones → IRPF 193"),
    ("502", "212", "", "Participaciones grupo → 212"),
    ("503", "212", "", "Participaciones asociada → 212"),
    ("507", "196", "", "Deuda valores → IRPF 196"),
    ("508", "198", "", "Derivados → IRPF 198"),
    ("600", "303", "", "Compras → IVA soportado"),
    ("600", "347", "", "Compras → Modelo 347"),
    ("614", "303", "", "Publicidad → IVA soportado"),
    ("640", "100", "", "Sueldos → IRPF 100"),
    ("640", "111", "", "Sueldos → IRPF 111"),
    ("642", "200", "", "SS empresa → IS deducible"),
    ("680", "200", "", "Amortización material → IS deducible"),
    ("700", "303", "", "Ventas → IVA repercutido"),
    ("700", "347", "", "Ventas → Modelo 347"),
    ("700", "349", "", "Ventas → FactA 349"),
    ("700", "390", "", "Ventas → IVA anual 390"),
    ("700", "394", "", "Ventas → SII 394"),
    ("720", "200", "", "Subvenciones capital → IS"),
    ("721", "200", "", "Subvenciones explotación → IS"),
    ("100", "347", "", "Capital social → Operaciones 347"),
    ("174", "200", "", "Bonos → IS"),
    ("175", "303", "", "Préstamos → IVA"),
    ("216", "303", "", "Transporte → IVA"),
    ("473", "124", "", "IRNR retenciones → 124"),
    ("473", "216", "", "IRNR retenciones → 216"),
    ("474", "309", "", "ITPAJD → 309"),
    ("660", "200", "", "Intereses → IS deducible"),
    ("664", "200", "", "Diferencias cambio → IS"),
    ("681", "200", "", "Amort. inmaterial → IS deducible"),
    ("750", "200", "", "Participaciones beneficios → IS tributario"),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    for ref in FISCAL_REFS:
        cuenta, modelo, casilla, ejercicio, nota = ref
        cur.execute(
            """
            INSERT INTO pgc_cuenta_fiscal_ref (id, cuenta_id, modelo, casilla, ejercicio, nota)
            VALUES (gen_random_uuid(), (SELECT id FROM pgc_cuenta WHERE codigo = %s), %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (cuenta, modelo, casilla, ejercicio, nota),
        )

    for ref in AEAT_MODEL_REFS:
        cuenta, modelo, campana, nota = ref
        cur.execute(
            """
            INSERT INTO pgc_cuenta_modelo_aeat_ref (id, cuenta_id, modelo_id, campana, nota)
            VALUES (gen_random_uuid(), (SELECT id FROM pgc_cuenta WHERE codigo = %s), %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (cuenta, modelo, campana, nota),
        )

    conn.commit()
    print(f"Seeded {len(FISCAL_REFS)} fiscal refs + {len(AEAT_MODEL_REFS)} AEAT model refs")
    conn.close()


if __name__ == "__main__":
    seed()
