#!/usr/bin/env python3
"""Ingestión de W-8 forms, GIIN, FFI, NFFE."""
import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        # 1. Norma W-8 Forms
        cur.execute(
            """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
               jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            ("W8_FORMS",
             "Formularios W-8 (W-8BEN, W-8BEN-E, W-8EXP, W-8ECF) - IRS - Certificacion de condicion extranjera",
             "irs", "2010-03-18", "internacional", "formulario_irs",
             "un_lateral", "ingestado", "IRS-W8-2024"),
        )
        cur.execute("SELECT id FROM norma WHERE codigo = 'W8_FORMS'")
        w8_id = cur.fetchone()[0]

        w8_articles = [
            ("1", "Formulario W-8BEN - Certificado de condicion extranjera para personas fisicas", "articulo"),
            ("2", "Formulario W-8BEN-E - Certificado de condicion extranjera para entidades", "articulo"),
            ("3", "Formulario W-8EXP - Certificado de exencion para entidades exentas", "articulo"),
            ("4", "Formulario W-8ECF - Personas no residentes con ingresos de EE.UU.", "articulo"),
            ("5", "GIIN - Global Intermediary Identification Number", "articulo"),
            ("6", "FFI - Foreign Financial Institution", "articulo"),
            ("7", "NFFE - Non-Financial Foreign Entity", "articulo"),
            ("8", "Active NFFE vs. Passive NFFE", "articulo"),
            ("9", "Controlling Person - Persona que controla la entidad", "articulo"),
            ("10", "FFN - Foreign Financial Institution (sin GIIN)", "articulo"),
            ("11", "Validez del formulario W-8BEN", "articulo"),
            ("12", "Validez del formulario W-8BEN-E", "articulo"),
            ("13", "Certificado de residencia fiscal (FSC)", "articulo"),
            ("14", "TIN - Taxpayer Identification Number del no residente", "articulo"),
            ("15", "Clasificacion de entidad en W-8BEN-E", "articulo"),
            ("16", "Partes del W-8BEN", "articulo"),
            ("17", "Partes del W-8BEN-E", "articulo"),
            ("18", "Beneficiario final - Beneficial owner", "articulo"),
            ("19", "Agente de contacto - Contact person", "articulo"),
            ("20", "Retencion FATCA 30% por no presentar formulario", "articulo"),
        ]
        for num, titulo, tipo in w8_articles:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (w8_id, num, titulo, tipo),
            )

        conn.commit()
        print(f"OK: {len(w8_articles)} articulos de formularios W-8 insertados")

        # 2. Textos detallados
        textos = [
            ("W8_FORMS", "1",
             "Formulario W-8BEN - Certificado de condicion extranjera para personas fisicas\n\n"
             "Proposito: El formulario W-8BEN se utiliza para demostrar la condicion de no residente extranjero "
             "a efectos de retencion en la fuente de EE.UU. (FATCA y Capitulo 3/4).\n\n"
             "Quien debe presentarlo:\n"
             "- Personas fisicas que no sean residentes de EE.UU.\n"
             "- Que obtengan ingresos de origen estadounidense (dividendos, intereses, royalties, rentas de alquiler, etc.)\n"
             "- Que deseen reducir o eximir la retencion del 30% aplicable por el tratado de doble tributacion (DTA)\n\n"
             "Partes del formulario:\n\n"
             "Parte I - Identificacion del beneficial owner:\n"
             "- Linea 1: Nombre del beneficial owner (persona fisica)\n"
             "- Linea 2: Pais de ciudadania\n"
             "- Linea 3: Direccion (numero, calle, ciudad, codigo postal, pais)\n"
             "- Linea 4A: TIN del pais de residencia (si aplica)\n"
             "- Linea 4B: TIN de EE.UU. (si aplica - SSN, ITIN)\n"
             "- Linea 5: Fecha de nacimiento\n"
             "- Linea 6: Numero de cuenta bancaria (opcional)\n\n"
             "Parte IV - Reclamacion de beneficios del tratado:\n"
             "- Linea 10: Pais con el que se reclama el tratado\n"
             "- Linea 11: Numero de articulos del tratado aplicables (ej. 10, 11, 12 para dividendos, intereses, regalias)\n\n"
             "Validez:\n"
             "- Vigente: ano calendario en el que se firma + siguientes 3 anos completos\n"
             "- Termina si: cambian las circunstancias que afectan la precision de la certificacion\n\n"
             "Ejemplo para residente en Espana:\n"
             "- Linea 1: Juan Garcia Lopez\n"
             "- Linea 4A: B12345678 (NIF espanol)\n"
             "- Linea 10: ES\n"
             "- Linea 11: 10 (dividendos 15%), 11 (intereses 15%), 12 (regalias 15%)"),

            ("W8_FORMS", "2",
             "Formulario W-8BEN-E - Certificado de condicion extranjera para entidades\n\n"
             "Proposito: Certificado de condicion extranjera para entidades (sociedades, trusts, fondos, etc.)\n\n"
             "Partes principales:\n"
             "Parte I - Identificacion de la entidad (nombre, pais, direccion, TIN)\n"
             "Parte IV - Beneficial owner(s) - tipo, pais de residencia, numero de identificacion\n"
             "Parte VII - FATCA: tipo de entidad, GIIN, codigo de exencion, estado FATCA\n"
             "Parte VIII - Controlling persons (solo para NFFE Passive): nombre, TIN, pais, fecha nacimiento\n\n"
             "Clasificacion de entidades:\n\n"
             "FFI (Foreign Financial Institution):\n"
             "- Banco, entidad de inversion, entidad de custodia, entidad de seguros con contrato de efectivo, fondo de inversion\n\n"
             "NFFE (Non-Financial Foreign Entity):\n"
             "- Active NFFE: <50% ingresos pasivos, <50% activos que producen ingresos pasivos\n"
             "- Passive NFFE: >50% ingresos pasivos o >50% activos que producen ingresos pasivos\n\n"
             "FFI Exenta: gobierno, organizacion internacional, sin animo de lucro, fondo de pensiones, etc.\n\n"
             "Validez: mismo que W-8BEN - ano calendario de firma + 3 anos completos"),

            ("W8_FORMS", "5",
             "GIIN - Global Intermediary Identification Number\n\n"
             "El GIIN es un identificador unico asignado por el IRS a las entidades financieras extranjeras (FFI) "
             "que se registran como Participating FFI bajo FATCA.\n\n"
             "Como obtenerlo:\n"
             "1. Registrarse en el portal del IRS: https://irs.gov/ffiregistration\n"
             "2. Completar el formulario de registro FATCA en linea\n"
             "3. Esperar la asignacion del GIIN (generalmente 15-30 dias habiles)\n"
             "4. Publicar el GIIN en el registro de intermediarios del IRS\n\n"
             "Uso del GIIN:\n"
             "- Las entidades financieras deben proporcionar su GIIN a los agentes de retencion/pagadores\n"
             "- El GIIN se incluye en el formulario W-8BEN-E (linea 13)\n"
             "- El GIIN se utiliza para verificar que la entidad esta registrada en FATCA\n\n"
             "Verificacion del GIIN:\n"
             "- Acceder al IRS FFIs List: https://www.irs.gov/individuals/international-taxpayers/updated-global-intermediary-identification-number-giin-list\n"
             "- Buscar el GIIN en la lista y verificar que la entidad esta activa\n\n"
             "Tipos de GIIN:\n"
             "- Participating FFI, Registered Deemed Compliant FFI, Sponsored FFI, Limited FFI, Active NFFE, Exempt Beneficial Owner"),

            ("W8_FORMS", "6",
             "FFI - Foreign Financial Institution\n\n"
             "Una FFI es cualquier entidad bancaria, entidad de inversion, entidad de custodia, entidad de seguros "
             "con contrato de efectivo, o fondo de inversion que no sea residente de EE.UU.\n\n"
             "Tipos de FFI:\n"
             "1. Banco: entidades que aceptan depositos u otros fondos reembolsables\n"
             "2. Entidad de inversion: fondo de inversion, fondo de cobertura, entidad que invierte en valores\n"
             "3. Entidad de custodia: mantiene instrumentos financieros en nombre de terceros\n"
             "4. Entidad de seguros con contrato de efectivo\n"
             "5. Fondo de inversion\n\n"
             "Obligaciones de una Participating FFI:\n"
             "1. Due diligence: identificar titulares de cuentas residentes en EE.UU.\n"
             "2. Retencion: 30% sobre pagos a cuentas no cooperativas\n"
             "3. Reporte: anualmente al IRS (via autoridad fiscal local)\n"
             "4. Registro: obtener GIIN en IRS"),

            ("W8_FORMS", "7",
             "NFFE - Non-Financial Foreign Entity\n\n"
             "Una NFFE es cualquier entidad que no sea una FFI.\n\n"
             "Active NFFE: <50% ingresos pasivos y <50% activos pasivos. Ejemplos: manufactureras, servicios, tecnologia.\n"
             "Passive NFFE: >50% ingresos activos o >50% activos pasivos. Ejemplos: holdings, trusts.\n\n"
             "Obligaciones Passive NFFE:\n"
             "1. Identificar controlling persons (personas con >=10% de propiedad o control)\n"
             "2. Proporcionar informacion de controlling persons a los agentes de retencion\n"
             "3. Informacion reportada al IRS via autoridad fiscal local conforme a FATCA\n\n"
             "Controlling Person:\n"
             "- Corporacion: personas con >=10% de acciones o derechos de voto\n"
             "- Trust: settlor, trustee(s), protector, beneficiaries\n"
             "- Otras entidades: personas con poderes equivalentes\n\n"
             "Documentacion:\n"
             "- Active NFFE: W-8BEN-E Parte IV linea 7A = Active NFFE. No requiere controlling persons\n"
             "- Passive NFFE: W-8BEN-E Parte VIII con informacion completa de cada controlling person"),

            ("W8_FORMS", "11",
             "Validez del formulario W-8BEN\n\n"
             "Reglas generales de validez:\n"
             "1. Ano calendario de firma + 3 anos completos\n"
             "   Ejemplo: firmado el 15/03/2024 -> valido hasta 31/12/2027\n"
             "2. Terminacion anticipada: cambian circunstancias, cambia residencia fiscal, cambia ciudadania\n"
             "3. Renovacion: nuevo formulario antes de que expire el anterior\n"
             "4. Efectos de la expiracion: retencion del 30% inmediata, sin periodo de gracia\n\n"
             "Casos especiales:\n"
             "1. Cambio de residencia: notificar al agente y presentar nuevo W-8BEN con nueva direccion y TIN\n"
             "2. Cambio de ciudadania: si obtiene ciudadania estadounidense, presentar W-9 en lugar de W-8BEN\n"
             "3. Tratado modificado: actualizar formulario con nuevos articulos aplicables"),

            ("W8_FORMS", "13",
             "Certificado de residencia fiscal (FSC - Foreign Status Certification)\n\n"
             "Proposito: Acreditar la residencia fiscal para aplicar los tipos reducidos del convenio de doble tributacion.\n\n"
             "Ejemplos por pais:\n"
             "Espana - AEAT: Certificado de residencia fiscal emitido por la AEAT, valido generalmente 1 ano\n"
             "Alemania - BZSt: Steuerliche Unbedenklichkeitsbescheinigung, formulario bog en R\n"
             "Francia - DGFiP: Attestation de residence fiscale\n"
             "Reino Unido - HMRC: Certificate of Residence via GOV.UK\n"
             "Italia - Agenzia delle Entrate: Certificato di residenza fiscale\n\n"
             "Uso: adjuntar al formulario W-8BEN, proporcionar numero de referencia en linea 8A del W-8BEN.\n\n"
             "Importante: el certificado de residencia fiscal es un documento complementario al W-8BEN, no lo reemplaza."),
        ]

        for norma_code, numero, texto in textos:
            cur.execute("SELECT id FROM norma WHERE codigo = %s", (norma_code,))
            norma_id = cur.fetchone()[0]
            cur.execute(
                "SELECT id FROM articulo WHERE norma_id = %s AND numero = %s",
                (norma_id, numero),
            )
            row = cur.fetchone()
            if row:
                art_id = row[0]
                cur.execute(
                    "SELECT id FROM version_articulo WHERE articulo_id = %s AND vigente_desde = %s",
                    (art_id, "2025-01-01"),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE version_articulo SET texto = %s WHERE id = %s", (texto, existing[0]))
                else:
                    cur.execute(
                        """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                           VALUES (%s, %s, %s)""",
                        (art_id, texto, "2025-01-01"),
                    )

        conn.commit()
        print("OK: Textos detallados de W-8BEN, W-8BEN-E, GIIN, FFI, NFFE insertados")
        conn.close()

if __name__ == "__main__":
    main()
