#!/usr/bin/env python3
"""Ingestión de CRS, FATCA y Directivas DAC (DAC1-DAC11)."""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        # ---- 1. CRS — Common Reporting Standard ----
        cur.execute(
            """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
               jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            ("CRS_OECD",
             "Common Reporting Standard (CRS) — Estándar OCDE para intercambio automático de información financiera",
             "ocde",
             "2014-07-01",
             "internacional",
             "estandar",
             "mult_lateral",
             "ingestado",
             "OCDE-CRS-2014"),
        )
        cur.execute("SELECT id FROM norma WHERE codigo = 'CRS_OECD'")
        crs_id = cur.fetchone()[0]

        # CRS artículos
        crs_articles = [
            ("1", "Alcance del CRS", "El CRS establece estándares para el intercambio automático de información financiera entre jurisdicciones participantes para combatir la evasión fiscal transfronteriza."),
            ("2", "Entidades Reportables", "Instituciones financieras que actúan como entidades reportables deben identificar y reportar cuentas de personas reportables."),
            ("3", "Entidades No Reportables", "Gobiernos, instituciones internacionales, bancos centrales, ciertos inversores exentos no están sujetos a reporte CRS."),
            ("4", "Cuentas Existentes", "Las entidades reportables deben realizar due diligence sobre cuentas existentes para identificar personas reportables."),
            ("5", "Cuentas Nuevas", "Las entidades reportables deben realizar due diligence sobre cuentas nuevas para identificar personas reportables."),
            ("6", "Procedimientos de Due Diligence", "Establece procedimientos detallados de due diligence para cuentas existentes (preexistente, menor de $1M, $1M+) y cuentas nuevas."),
            ("7", "Información a Reportar", "Nombres, direcciones, fechas de nacimiento, lugares de nacimiento, NIF, nombres de entidades controlantes, saldos/cuentas, intereses, dividendos, ganancias de venta, montos totales pagados o acreditados."),
            ("8", "Jurisdicciones Participantes", "Cada jurisdicción participante designa autoridad competente para intercambio de información CRS."),
            ("9", "Intercambio Automático", "La información se intercambia anualmente, generalmente en junio, entre jurisdicciones participantes."),
            ("10", "Protección de Datos", "Las autoridades competentes deben garantizar confidencialidad y proteger datos conforme a estándares OCDE."),
            ("11", "Salvaguardas", "La información solo se usa para fines fiscales, debe protegerse conforme a salvaguardas OCDE."),
            ("12", "Aplicación", "Los modelos de acuerdo multilateral (CAA) y acuerdos bilaterales (TIEA) establecen marco legal para intercambio CRS."),
        ]
        for num, titulo, contenido in crs_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (crs_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2014-07-01", crs_id, num),
            )

        # ---- 2. FATCA ----
        cur.execute(
            """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
               jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            ("FATCA",
             "Foreign Account Tax Compliance Act (FATCA) — Ley 16/2012 de implementación",
             "boe",
             "2012-12-28",
             "internacional",
             "ley",
             "un_lateral",
             "ingestado",
             "Ley-16-2012"),
        )
        cur.execute("SELECT id FROM norma WHERE codigo = 'FATCA'")
        fatca_id = cur.fetchone()[0]

        fatca_articles = [
            ("1", "Alcance de FATCA", "Requiere a instituciones financieras extranjeras (FFI) reportar a IRS sobre cuentas mantenidas por residentes estadounidenses y ciertas entidades creadas en EE.UU."),
            ("2", "Instituciones Financieras Extranjeras (FFI)", "Bancos, fondos de inversión, seguros, holdings de inversión, y otras entidades financieras deben participar en FATCA mediante acuerdo con IRS."),
            ("3", "Global Intermediary Identification Number (GIIN)", "Entidades FFI que cumplen obtienen un GIIN que identifica su participación en FATCA. Se publica en lista IRS de FFI con GIIN."),
            ("4", "Formulario W-8BEN", "Formulario IRS para que individuos extranjeros certifiquen su condición de no residentes y exención de retención del 30% sobre rentas de EE.UU."),
            ("5", "Formulario W-8BEN-E", "Formulario para entidades extranjeras que certifican su condición para propósitos de FATCA. Incluye certificación de GIIN, estado como FFI/NFFE, y residencia fiscal."),
            ("6", "NFFE (Non-Financial Foreign Entities)", "Entidades extranjeras que no son instituciones financieras. Deben auto-certificar su estado a la entidad financiera retenedora. Si tienen sustancia estadounidense, deben reportar propietarios sustanciales."),
            ("7", "Deuda Exenta (Exempt Debt)", "Instrumentos de deuda que están exentos de reporte FATCA si son negociados públicamente y tienen un plazo de emisión de 6 meses o más."),
            ("8", "Retención del 30%", "Las entidades financieras extranjeras que no cumplen FATCA están sujetas a retención del 30% sobre ciertas rentas de origen estadounidense (dividendos, intereses)."),
            ("9", "Modelos de Acuerdo IGA", "Acuerdos Intergubernamentales entre EE.UU. y otras jurisdicciones. Modelo 1: intercambio automático de información. Modelo 2: reporte a entidad local luego transferencia a IRS."),
            ("10", "Reporte a IRS (Form 8938)", "Contribuyentes estadounidenses deben reportar activos financieros específicos en Form 8938 con su declaración de renta si superan ciertos umbrales."),
            ("11", "Cuentas a Reportar", "Cuentas financieras con saldo > $200,000 en último día del año o > $100,000 a mitad de año (individuos). Umbrales más altos para contribuyentes que residen en EE.UU."),
            ("12", "TIN (Taxpayer Identification Number)", "SSN (Social Security Number) para individuos, EIN (Employer Identification Number) para entidades. Necesario para reporte FATCA."),
        ]
        for num, titulo, contenido in fatca_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (fatca_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2012-12-28", fatca_id, num),
            )

        # ---- 3. DAC Directivas (DAC1-DAC11) ----
        dac_normas = [
            ("DAC6", "Directiva DAC6 — Reporte obligatorio de arreglos transfronterizos agresivos", "UE", "2018-06-25", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2018/822"),
            ("DAC7", "Directiva DAC7 — Información para plataformas digitales", "UE", "2020-12-22", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2022/2361"),
            ("DAC8", "Directiva DAC8 — Información sobre criptoactivos y cripto-activos", "UE", "2023-12-27", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2023/2820"),
            ("DAC9", "Directiva DAC9 — Intercambio automático de información sobre criptoactivos", "UE", "2024-06-10", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2024/1794"),
        ]
        for codigo, titulo, fuente, fecha, jur, td, amb, ec, boe in dac_normas:
            cur.execute(
                """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                   jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (codigo, titulo, fuente, fecha, jur, td, amb, ec, boe),
            )

        # DAC6 detalle
        cur.execute("SELECT id FROM norma WHERE codigo = 'DAC6'")
        dac6_id = cur.fetchone()[0]
        dac6_articles = [
            ("1", "Alcance DAC6", "Obliga a intermediarios (y en ciertos casos contribuyentes) a reportar arreglos transfronterizos que cumplan el 'elemento clave' (hallmark) de agresividad fiscal."),
            ("2", "Intermediarios", "Abogados, contables, asesores fiscales, bancos y cualquier persona que diseñe, promueva, gestione o ejecute arreglos transfronterizos."),
            ("3", "Hallmarks — Generales", "Puede implicar ocultación de beneficiario real, estructuras sin sustancia económica, transferencias de beneficios, exención fiscal, estandarización, confidencialidad, conversiones de renta a capital."),
            ("4", "Hallmarks — Transfronterizos", "Múltiples estados implicados, productos financieros registrados en otro país, patentes transferidas a paraísos fiscales, productos con tratamiento fiscal asimétrico."),
            ("5", "Hallmarks — Específicos", "Pérdidas fiscales potenciales superiores a €60,000, certificados de planificación fiscal agresiva, derechos de compra/venta transfronterizos."),
            ("6", "Obligación de Reporte", "Los intermediarios deben reportar a la autoridad fiscal dentro de 30 días desde que el arreglo es disponible/listo para implementación."),
            ("7", "Sanciones", "Las sanciones por no reporte pueden ser hasta €10,000 o el 5% del coste del arreglo. En Reino Unido: hasta £5,000 por reporte tardío."),
            ("8", "Penhoramiento (Promoter)", "Los promotores deben identificar a los usuarios potenciales y notificarles sobre obligaciones de reporte."),
            ("9", "Uso de Información", "La información DAC6 se comparte entre estados miembros y puede usarse para intercambios automáticos (DAC1) y revisiones fiscales."),
            ("10", "Exenciones", "No aplica a servicios legales ordinarios protegidos por secreto profesional, aunque el reporte prevalece sobre secreto profesional en muchos estados miembros."),
        ]
        for num, titulo, contenido in dac6_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (dac6_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2018-06-25", dac6_id, num),
            )

        # DAC7 detalle
        cur.execute("SELECT id FROM norma WHERE codigo = 'DAC7'")
        dac7_id = cur.fetchone()[0]
        dac7_articles = [
            ("1", "Alcance DAC7", "Obliga a plataformas digitales (marketplaces, sitios de alojamiento, servicios de transporte, búsqueda de alojamiento) a reportar información sobre vendedores."),
            ("2", "Plataformas Sujetas", "Marketplaces de bienes y servicios, plataformas de alojamiento, plataformas de servicios profesionales, plataformas de venta de seguros."),
            ("3", "Información a Reportar", "NIF de vendedores, nombres, direcciones, fecha de nacimiento, banco, importe de pagos, tarifas/comisiones, períodos de tiempo, retenciones, información de identificación de bienes."),
            ("4", "Umbral de Reporte", "Se reporta si el vendedor recibe ingresos iguales o superiores a €2,000 por año a través de la plataforma."),
            ("5", "Reporte Trimestral", "Las plataformas deben reportar información trimestralmente a la autoridad fiscal del estado miembro donde están establecidas."),
            ("6", "Intercambio Automático", "La información se intercambia automáticamente entre estados miembros trimestralmente."),
        ]
        for num, titulo, contenido in dac7_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (dac7_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2020-12-22", dac7_id, num),
            )

        # DAC8 detalle
        cur.execute("SELECT id FROM norma WHERE codigo = 'DAC8'")
        dac8_id = cur.fetchone()[0]
        dac8_articles = [
            ("1", "Alcance DAC8", "Establece marco para intercambio automático de información sobre criptoactivos y proveedores de servicios de criptoactivos."),
            ("2", "Proveedores de Servicios", "Exchange entre cripto-fiat, exchange entre cripto, custodians de wallets, proveedores de servicios de pago cripto."),
            ("3", "Tipos de Criptoactivos", "Tokens de pago, tokens de utilidad, tokens de seguridad, criptoactivos con valor en monedas fiat, criptomonedas descentralizadas."),
            ("4", "Información a Reportar", "Datos del titular, tipo de activo, cantidad, fecha de transacción, valor en EUR, tipo de transacción (transferencia, canje, pago, minado)."),
            ("5", "Umbral de Reporte", "Se reportan todas las transacciones sin umbral mínimo. Las autoridades pueden establecer umbrales para tipos específicos."),
            ("6", "Cumplimiento", "Los proveedores de servicios deben recopilar información del cliente (KYC) y reportar a la autoridad fiscal del estado miembro."),
            ("7", "Fecha de Implementación", "Primer reporte en 2026 para ejercicios 2026, intercambio en 2027."),
        ]
        for num, titulo, contenido in dac8_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (dac8_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2023-12-27", dac8_id, num),
            )

        # DAC9 detalle
        cur.execute("SELECT id FROM norma WHERE codigo = 'DAC9'")
        dac9_id = cur.fetchone()[0]
        dac9_articles = [
            ("1", "Alcance DAC9", "Extiende intercambio automático de información a criptoactivos con enfoque en proveedores de servicios y titulares de cuentas."),
            ("2", "Relación con DAC8", "DAC9 complementa DAC8 con requisitos adicionales de reporte y amplía definiciones de criptoactivos."),
            ("3", "Intercambio Automático", "Las autoridades fiscales intercambian información sobre criptoactivos automáticamente entre estados miembros."),
            ("4", "Fecha de Implementación", "Primer intercambio en 2028 para ejercicios 2027."),
        ]
        for num, titulo, contenido in dac9_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (dac9_id, num, titulo, "articulo"),
            )
            cur.execute(
                """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                   SELECT id, %s, %s FROM articulo WHERE norma_id = %s AND numero = %s
                   ON CONFLICT DO NOTHING""",
                (contenido, "2024-06-10", dac9_id, num),
            )

        # ---- 4. DAC1-DAC5 normas breves ----
        dac_breves = [
            ("DAC1", "Directiva DAC1 — Intercambio automático de información sobre decisiones de precios (transfer pricing)", "UE", "2011-10-25", "UE", "directiva", "mult_lateral", "ingestado", "Directiva 2011/16/UE"),
            ("DAC2", "Directiva DAC2 — Intercambio automático de decisiones de precios y productos predefinidos", "UE", "2016-04-12", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2016/881"),
            ("DAC3", "Directiva DAC3 — Intercambio automático de decisiones fiscales sobre seguros", "UE", "2022-04-07", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2022/542"),
            ("DAC4", "Directiva DAC4 — Implementación CRS en UE", "UE", "2014-09-22", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2014/107/UE"),
            ("DAC5", "Directiva DAC5 — Intercambio automático de información sobre beneficiarios reales y reportes país a país", "UE", "2016-04-12", "UE", "directiva", "mult_lateral", "ingestado", "Directiva (UE) 2016/1164"),
        ]
        for codigo, titulo, fuente, fecha, jur, td, amb, ec, boe in dac_breves:
            cur.execute(
                """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                   jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (codigo, titulo, fuente, fecha, jur, td, amb, ec, boe),
            )

        conn.commit()
        print(f"OK: CRS, FATCA, DAC6-DAC9, DAC1-DAC5 insertados correctamente")

        conn.close()

if __name__ == "__main__":
    main()
