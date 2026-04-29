import os
import uuid

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

MAPPINGS = [
    ("es-gvr:Activo", "1", "high", "direct", "Activo del balance", True),
    ("es-gvr:ActivoCorriente", "2", "high", "direct", "Activo corriente", True),
    ("es-gvr:ActivoNoCorriente", "1", "high", "direct", "Activo no corriente", True),
    ("es-gvr:ActivoNoCorrienteMaterial", "21", "high", "direct", "Inmovilizado material", True),
    ("es-gvr:ActivoNoCorrienteInmaterial", "22", "high", "direct", "Inmovilizado inmaterial", True),
    ("es-gvr:ActivoNoCorrienteFinanciero", "24", "high", "direct", "Inmovilizado financiero", True),
    ("es-gvr:ActivoCorrienteExistencias", "3", "high", "direct", "Existencias", True),
    ("es-gvr:ActivoCorrienteClientes", "4", "high", "direct", "Clientes", True),
    ("es-gvr:ActivoCorrienteCredores", "5", "high", "direct", "Deudores", True),
    ("es-gvr:PatrimonioNeto", "1", "high", "direct", "Patrimonio neto", True),
    ("es-gvr:PatrimonioNetoFondosPropios", "10", "high", "direct", "Fondos propios", True),
    ("es-gvr:PatrimonioNetoCapital", "100", "high", "direct", "Capital social", True),
    ("es-gvr:PatrimonioNetoReservas", "11", "high", "direct", "Reservas", True),
    ("es-gvr:PatrimonioNetoResultado", "110", "high", "direct", "Resultado del ejercicio", True),
    ("es-gvr:Pasivo", "1", "high", "direct", "Pasivo del balance", True),
    ("es-gvr:PasivoNoCorriente", "17", "high", "direct", "Pasivo no corriente", True),
    ("es-gvr:PasivoNoCorrienteProvisiones", "14", "high", "direct", "Provisiones", True),
    ("es-gvr:PasivoNoCorrienteDeudas", "17", "high", "direct", "Deudas a largo plazo", True),
    ("es-gvr:PasivoCorriente", "20", "high", "direct", "Pasivo corriente", True),
    ("es-gvr:PasivoCorrienteDeudas", "51", "high", "direct", "Deudas a corto plazo", True),
    ("es-gvr:PasivoCorrienteAcreedores", "40", "high", "direct", "Acreedores por compras", True),
    ("es-gvr:Ingresos", "7", "high", "direct", "Ingresos", True),
    ("es-gvr:IngresosExplotacion", "70", "high", "direct", "Ingresos por explotación", True),
    ("es-gvr:IngresosExplotacionVentas", "700", "high", "direct", "Ventas de productos", True),
    ("es-gvr:GastosExplotacion", "6", "high", "direct", "Gastos de explotación", True),
    ("es-gvr:GastosExplotacionCompras", "60", "high", "direct", "Compras", True),
    ("es-gvr:GastosExplotacionPersonal", "61", "high", "direct", "Gastos de personal", True),
    ("es-gvr:GastosExplotacionFinancieros", "62", "high", "direct", "Gastos financieros", True),
    ("es-gvr:Amortizacion", "68", "high", "direct", "Amortización del inmovilizado", True),
    ("es-gvr:ResultadoEjercicio", "110", "high", "direct", "Resultado del ejercicio", True),
    ("es-gvr:FlujoEfectivo", "11", "high", "direct", "Flujo de efectivo", True),
    ("es-gvr:IVARepercutido", "477", "high", "direct", "Hacienda P.C. IVA repercutido", True),
    ("es-gvr:IVASoportado", "472", "high", "direct", "Hacienda P.C. IVA soportado", True),
    ("es-gvr:IRPFRetenido", "473", "high", "direct", "Hacienda P.C. IRPF a ingresar", True),
    ("es-gvr:Tesoreria", "57", "high", "direct", "Tesorería", True),
    ("es-gvr:TesoreriaBanco", "572", "high", "direct", "Cuentas corriente en banco", True),
    ("es-gvr:Proveedores", "40", "high", "direct", "Proveedores", True),
    ("es-gvr:Clientes", "43", "high", "direct", "Clientes", True),
    ("es-gvr:ExistenciasMercancias", "30", "high", "direct", "Mercaderías A", True),
    ("es-gvr:DeudasLargoPlazo", "17", "high", "direct", "Deudas a largo plazo", True),
    ("es-gvr:DeudasCortoPlazo", "51", "high", "direct", "Deudas a corto plazo", True),
    ("es-gvr:CapitalSocial", "100", "high", "direct", "Capital social", True),
    ("es-gvr:ReservasLegales", "110", "high", "direct", "Reserva legal", True),
    ("es-gvr:Subvenciones", "14", "high", "direct", "Subvenciones oficiales", True),
    ("es-gvr:ProvisionesRiesgos", "14", "high", "direct", "Provisiones para riesgos", True),
    ("es-gvr:ResultadoAnterior", "110", "medium", "derived", "Resultado de ejercicios anteriores", True),
    ("es-gvr:ComprasMateriasPrimas", "601", "high", "direct", "Compras de materias primas", True),
    ("es-gvr:VariacionExistencias", "63", "medium", "derived", "Variación de existencias", True),
    ("es-gvr:TrabajosRealizados", "70", "medium", "derived", "Trabajos realizados por la empresa", True),
    ("es-gvr:InmovilizadoMaterialNeto", "21", "medium", "derived", "Inmovilizado material neto", True),
    ("es-gvr:DeudasEntidadesCredito", "52", "high", "direct", "Deudas con entidades de crédito", True),
    ("es-gvr:RetencionesIRPF", "473", "high", "direct", "Retenciones IRPF", True),
    ("es-gvr:Seguros", "62", "high", "direct", "Primas de seguros", True),
    ("es-gvr:Transportes", "62", "high", "direct", "Transportes", True),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    for m in MAPPINGS:
        xbrl_qname, account_codigo, confidence, mapping_type, note, is_active = m
        cur.execute(
            """
            INSERT INTO pgc_xbrl_mapping (id, xbrl_concept_qname, pgc_account_codigo, confidence, mapping_type, note, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(uuid.uuid5(uuid.NAMESPACE_DNS, xbrl_qname)), xbrl_qname, account_codigo, confidence, mapping_type, note, is_active),
        )

    conn.commit()
    print(f"Seeded {len(MAPPINGS)} pgc_xbrl_mapping records")
    conn.close()


if __name__ == "__main__":
    seed()
