"""LEGACY / NO AUTORITATIVO.

Legacy seed for `modelo_articulo` mappings.

No usar como flujo canonico productivo AEAT. Esta ruta se mantiene solo como
compatibilidad temporal hasta endurecer `modelo_articulo` en Fase 3.2.
"""

import os
import uuid

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

MAPPINGS = [
    ("100", "IRPF", "1", "Casilla 001-005", "Hecho imponible"),
    ("100", "IRPF", "2", "Casilla 006-010", "Rendimientos del trabajo"),
    ("100", "IRPF", "3", "Casilla 011-020", "Rendimientos del capital mobiliario"),
    ("100", "IRPF", "4", "Casilla 021-030", "Rendimientos del capital inmobiliario"),
    ("100", "IRPF", "5", "Casilla 031-040", "Actividades económicas"),
    ("100", "IRPF", "6", "Casilla 041-050", "Pérdidas patrimoniales"),
    ("100", "IRPF", "7", "Casilla 051-060", "Reducciones especiales"),
    ("100", "IRPF", "8", "Casilla 061-070", "Cuota íntegra"),
    ("100", "IRPF", "9", "Casilla 071-080", "Cuota líquida"),
    ("100", "IRPF", "10", "Casilla 081-090", "Pagos fraccionados"),
    ("100", "IRPF", "11", "Casilla 091-100", "Autoliquidación"),
    ("100", "IRPF", "12", "Casilla 101-110", "Devolución"),
    ("100", "IRPF", "14", "Casilla 111-120", "Minimización tributaria"),
    ("100", "IRPF", "15", "Casilla 121-130", "Retenciones"),
    ("100", "IRPF", "19", "Casilla 131-140", "Bases imponibles"),
    ("100", "IRPF", "20", "Casilla 141-150", "Tipos de retención"),
    ("100", "IRPF", "28", "Casilla 151-160", "Bienes inmuebles"),
    ("100", "IRPF", "29", "Casilla 161-170", "Entregas intracomunitarias"),
    ("100", "IRPF", "31", "Casilla 171-180", "Deducciones generales"),
    ("100", "IRPF", "32", "Casilla 181-190", "Deducciones autonómicas"),
    ("100", "IRPF", "33", "Casilla 191-200", "Deducciones por doble imposición"),
    ("100", "IRPF", "35", "Casilla 201-210", "Deducciones por inversión de capital"),
    ("100", "IRPF", "50", "Casilla 211-220", "Deducciones por mecenazgo"),
    ("100", "IRPF", "55", "Casilla 221-230", "Deducciones por formación"),
    ("100", "IRPF", "56", "Casilla 231-240", "Deducciones por vivienda"),
    ("100", "IRPF", "59", "Casilla 241-250", "Deducciones por donaciones"),
    ("100", "IRPF", "65", "Casilla 251-260", "Deducciones por maternidad"),
    ("100", "IRPF", "66", "Casilla 261-270", "Deducciones por discapacidad"),
    ("200", "IS", "1", "Casilla 001-005", "Hecho imponible"),
    ("200", "IS", "2", "Casilla 006-010", "Bases imponibles"),
    ("200", "IS", "4", "Casilla 011-020", "Tipos impositivos"),
    ("200", "IS", "5", "Casilla 021-030", "Deducciones"),
    ("200", "IS", "6", "Casilla 031-040", "Cuota íntegra"),
    ("200", "IS", "7", "Casilla 041-050", "Cuota líquida"),
    ("200", "IS", "8", "Casilla 051-060", "Pagos fraccionados"),
    ("200", "IS", "10", "Casilla 061-070", "Bienes inmuebles"),
    ("200", "IS", "15", "Casilla 071-080", "Amortización fiscal"),
    ("200", "IS", "20", "Casilla 081-090", "Deducciones IS"),
    ("200", "IS", "28", "Casilla 091-100", "Inversiones"),
    ("303", "IVA", "1", "Casilla 001-005", "Autoliquidación trimestral"),
    ("303", "IVA", "2", "Casilla 006-010", "Cuotas repercutidas"),
    ("303", "IVA", "3", "Casilla 011-020", "Cuotas soportadas"),
    ("303", "IVA", "4", "Casilla 021-030", "Cuotas deducibles"),
    ("303", "IVA", "5", "Casilla 031-040", "Resultado"),
    ("303", "IVA", "6", "Casilla 041-050", "Desglose operaciones"),
    ("303", "IVA", "7", "Casilla 051-060", "Operaciones exentas"),
    ("303", "IVA", "8", "Casilla 061-070", "Entregas intracomunitarias"),
    ("303", "IVA", "9", "Casilla 071-080", "Adquisiciones intracomunitarias"),
    ("303", "IVA", "28", "Casilla 081-090", "IVA diferido"),
    ("303", "IVA", "29", "Casilla 091-100", "IVA devengado"),
    ("303", "IVA", "31", "Casilla 101-110", "IVA soportado"),
    ("303", "IVA", "32", "Casilla 111-120", "IVA repercutido"),
    ("303", "IVA", "33", "Casilla 121-130", "IVA deducible"),
    ("303", "IVA", "35", "Casilla 131-140", "IVA no deducible"),
    ("347", "OP.347", "1", "Casilla 001-005", "Operaciones > 3.005,06€"),
    ("347", "OP.347", "2", "Casilla 006-010", "Entregas bienes"),
    ("347", "OP.347", "3", "Casilla 011-020", "Prestaciones servicios"),
    ("347", "OP.347", "4", "Casilla 021-030", "Intereses"),
    ("347", "OP.347", "5", "Casilla 031-040", "Arrendamientos"),
    ("349", "FACTA", "1", "Casilla 001-005", "Entregas intracomunitarias"),
    ("349", "FACTA", "2", "Casilla 006-010", "Prestaciones servicios"),
    ("349", "FACTA", "3", "Casilla 011-020", "Adquisiciones"),
    ("349", "FACTA", "4", "Casilla 021-030", "Adquisiciones servicios"),
    ("390", "IVA.A", "1", "Casilla 001-005", "Resumen anual operaciones"),
    ("390", "IVA.A", "2", "Casilla 006-010", "Resumen anual bienes"),
    ("390", "IVA.A", "3", "Casilla 011-020", "Resumen anual servicios"),
    ("111", "IRPF.T", "1", "Casilla 001-005", "Retribuciones trabajadores"),
    ("111", "IRPF.T", "2", "Casilla 006-010", "Retenciones profesionales"),
    ("111", "IRPF.T", "3", "Casilla 011-020", "Retenciones honorarios"),
    ("111", "IRPF.T", "4", "Casilla 021-030", "Retenciones arrendamientos"),
    ("111", "IRPF.T", "5", "Casilla 031-040", "Retenciones actividades"),
    ("111", "IRPF.T", "6", "Casilla 041-050", "Retenciones transporte"),
    ("111", "IRPF.T", "7", "Casilla 051-060", "Retenciones publicidad"),
    ("114", "IRPF", "1", "Casilla 001-005", "Profesionales"),
    ("114", "IRPF", "2", "Casilla 006-010", "Arrendamientos"),
    ("114", "IRPF", "3", "Casilla 011-020", "Actividades económicas"),
    ("124", "IRNR", "1", "Casilla 001-005", "Dividendos"),
    ("124", "IRNR", "2", "Casilla 006-010", "Intereses"),
    ("124", "IRNR", "3", "Casilla 011-020", "Regalías"),
    ("124", "IRNR", "4", "Casilla 021-030", "Rentas inmobiliarias"),
    ("124", "IRNR", "5", "Casilla 031-040", "Rendimientos capital mobiliario"),
    ("124", "IRNR", "6", "Casilla 041-050", "Rendimientos capital inmobiliario"),
    ("124", "IRNR", "7", "Casilla 051-060", "Prestaciones servicios"),
    ("124", "IRNR", "8", "Casilla 061-070", "Utilidades"),
    ("124", "IRNR", "9", "Casilla 071-080", "Plusvalías"),
    ("216", "IRNR", "1", "Casilla 001-005", "Facturas terceros"),
    ("216", "IRNR", "2", "Casilla 006-010", "Pagos al extranjero"),
    ("216", "IRNR", "3", "Casilla 011-020", "Retenciones IRNR"),
    ("290", "DAC2", "1", "Casilla 001-005", "Cuentas financieras"),
    ("290", "DAC2", "2", "Casilla 006-010", "Titulares"),
    ("290", "DAC2", "3", "Casilla 011-020", "Saldos"),
    ("394", "SII", "1", "Casilla 001-005", "Facturas emitidas"),
    ("394", "SII", "2", "Casilla 006-010", "Facturas ingresadas"),
    ("394", "SII", "3", "Casilla 011-020", "Resumen operaciones"),
    ("720", "BIEN.EX", "1", "Casilla 001-005", "Bienes en el extranjero"),
    ("720", "BIEN.EX", "2", "Casilla 006-010", "Cuentas en el extranjero"),
    ("720", "BIEN.EX", "3", "Casilla 011-020", "Valores en el extranjero"),
    ("878", "PROV.NR", "1", "Casilla 001-005", "Proveedores no residentes"),
    ("878", "PROV.NR", "2", "Casilla 006-010", "Pagos al extranjero"),
    ("878", "PROV.NR", "3", "Casilla 011-020", "Retenciones proveedores"),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    for m in MAPPINGS:
        modelo, impuesto, articulo_num, casilla, desc = m
        cur.execute(
            """
            INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
            VALUES (
                (SELECT id FROM aeat_modelo WHERE codigo = %s),
                (SELECT id FROM articulo WHERE numero = %s LIMIT 1),
                %s,
                %s,
                %s,
                NULL
            )
            ON CONFLICT DO NOTHING
            """,
            (modelo, articulo_num, casilla, desc, impuesto),
        )

    conn.commit()
    print(f"Seeded {len(MAPPINGS)} modelo_articulo mappings")
    conn.close()


if __name__ == "__main__":
    seed()
