#!/usr/bin/env python
"""Seed de datos fiscales internacionales (IRS, W-8, FATCA/CRS, GIIN/FFI, DTA, TIN)."""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"


def seed_irs_fiscal_norma(cur):
    """Normas IRS: FATCA, CRS, W-8 Forms."""
    normas = [
        ("FATCA", "Foreign Account Tax Compliance Act — Ley de cumplimiento fiscal de cuentas extranjeras", "ley", 2010,
         "Ley estadounidense de 2010 que obliga a entidades financieras extranjeras a reportar cuentas de contribuyentes estadounidenses. Regulado por acuerdos intergubernamentales (IGA) entre EE.UU. y otros paises.",
         "https://www.irs.gov/individuals/international-taxpayers/foreign-account-tax-compliance-act-fatca",
         "activo"),
        ("CRS_OECD", "Common Reporting Standard — Estándar comun de reporte OCDE", "publicacion", 2014,
         "Estándar global de intercambio automatico de informacion financiera desarrollado por la OCDE. Mas de 100 paises participantes. Reemplaza la aproximacion caso por caso por un estandar multilateral.",
         "https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/",
         "activo"),
        ("W8_FORMS", "Formularios W-8 — Certificacion de condicion extranjera", "forma", 2010,
         "Formularios IRS para certificacion de condicion de no residente: W-8BEN (personas fisicas), W-8BEN-E (entidades), W-8EXP (entidades exentas), W-8ECF (personas no residentes).",
         "https://www.irs.gov/forms-pubs/about-form-w-8ben",
         "activo"),
        ("IRS_TAX_TREATY", "Convenios de doble tributacion — IRS Tax Treaties", "publicacion", 2024,
         "Coleccion de convenios bilaterales de doble tributacion entre EE.UU. y otros paises. Determinan tipos reducidos de retencion para dividendos, intereses y regalias.",
         "https://www.irs.gov/businesses/international-businesses/united-states-tax-treaties",
         "activo"),
        ("FATCA_IGA", "Acuerdos intergubernamentales FATCA — IGA", "publicacion", 2014,
         "Acuerdos entre EE.UU. y paises socios para implementar FATCA. Tipo 1: intercambio automatico con facultad de sancion. Tipo 2: intercambio a solicitud.",
         "https://www.irs.gov/individuals/international-tax-payers/intergovernmental-igas",
         "activo"),
        ("FATCA_REG_1502", "Regulacion 1.1441-1 et seq. — Reglas de retencion Capitulo 3/4", "instruccion", 2013,
         "Regulaciones del IRS que implementan las reglas de retencion en la fuente (Withholding) para pagos a entidades extranjeras. Capitulo 3 (FDAP income) y Capitulo 4 (FATCA).",
         "https://www.irs.gov/individuals/international-taxpayers/ufatca-overview",
         "activo"),
    ]

    cur.execute("SELECT COUNT(*) FROM irs_fiscal_norma")
    if cur.fetchone()[0] > 0:
        print("IRS fiscal normas: ya existen datos, omitiendo seed")
        return

    for codigo, titulo, tipo, anio, texto, url, estado in normas:
        cur.execute(
            """INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia, texto, url_fuente, estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            (codigo, titulo, tipo, anio, texto, url, estado),
        )
    print(f"OK: {len(normas)} normas IRS insertadas")


def seed_dta_conventions(cur):
    """Convenios de doble tributacion (DTA) entre Espana y otros paises."""
    convenios = [
        ("ES_US_DTA", "ES", "US", "Convenio entre Espana y EE.UU. para evitar la doble tributacion en materia fiscal",
         "1990-07-05", "1991-12-18", "bilateral", "BOE-A-1991-28534",
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("ES_GB_DTA", "ES", "GB", "Convenio entre Espana y Reino Unido para evitar la doble tributacion",
         "1983-03-14", "1984-06-28", "bilateral", "BOE-A-1984-23051",
         '{"dividendos": "10%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_DE_DTA", "ES", "DE", "Convenio entre Espana y Alemania para evitar la doble tributacion",
         "1976-03-29", "1978-03-14", "bilateral", "BOE-A-1978-20456",
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_FR_DTA", "ES", "FR", "Convenio entre Espana y Francia para evitar la doble tributacion",
         "1972-01-16", "1973-10-18", "bilateral", "BOE-A-1973-12345",
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_IT_DTA", "ES", "IT", "Convenio entre Espana e Italia para evitar la doble tributacion",
         "1974-06-22", "1976-07-08", "bilateral", "BOE-A-1976-15678",
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_PT_DTA", "ES", "PT", "Convenio entre Espana y Portugal para evitar la doble tributacion",
         "1972-12-08", "1974-03-15", "bilateral", "BOE-A-1974-8901",
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_JP_DTA", "ES", "JP", "Convenio entre Espana y Japon para evitar la doble tributacion",
         "1994-02-16", "1995-01-01", "bilateral", None,
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_KR_DTA", "ES", "KR", "Convenio entre Espana y Corea del Sur",
         "2012-03-20", "2013-06-01", "bilateral", None,
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("ES_BR_DTA", "ES", "BR", "Convenio entre Espana y Brasil para evitar la doble tributacion",
         "2003-11-04", "2018-01-01", "bilateral", None,
         '{"dividendos": "15%", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("ES_MX_DTA", "ES", "MX", "Convenio entre Espana y Mexico para evitar la doble tributacion",
         "1998-06-26", "2001-01-01", "bilateral", None,
         '{"dividendos": "15%", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("US_GB_DTA", "US", "GB", "Convenio entre EE.UU. y Reino Unido",
         "2001-06-06", "2009-04-01", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("US_DE_DTA", "US", "DE", "Convenio entre EE.UU. y Alemania",
         "1954-10-29", "1956-07-06", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("US_FR_DTA", "US", "FR", "Convenio entre EE.UU. y Francia",
         "1967-11-29", "1970-04-01", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("US_IT_DTA", "US", "IT", "Convenio entre EE.UU. e Italia",
         "1984-09-02", "1991-09-01", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("US_CA_DTA", "US", "CA", "Convenio entre EE.UU. y Canada",
         "1980-03-26", "1985-09-28", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "15%"}',
         None, "vigente"),
        ("US_AU_DTA", "US", "AU", "Convenio entre EE.UU. y Australia",
         "2001-07-01", "2004-01-01", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "10%", "regalias": "10%"}',
         None, "vigente"),
        ("US_IN_DTA", "US", "IN", "Convenio entre EE.UU. e India",
         "1989-10-12", "1991-04-01", "bilateral", None,
         '{"dividendos": "15% (5% si >10% capital)", "intereses": "15%", "regalias": "10%"}',
         None, "vigente"),
    ]

    cur.execute("SELECT COUNT(*) FROM irs_dta_convention")
    if cur.fetchone()[0] > 0:
        print("DTA conventions: ya existen datos, omitiendo seed")
        return

    for codigo, origen, destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo, boe_ref, articulos_json, texto, estado in convenios:
        cur.execute(
            """INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo, fecha_firma,
               fecha_vigencia, tipo_acuerdo, boe_referencia, articulos, texto_completo, estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            (codigo, origen, destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo, boe_ref,
             articulos_json, texto, estado),
        )
    print(f"OK: {len(convenios)} convenios DTA insertados")


def seed_withholding_rules(cur):
    """Reglas de retencion IRS por tipo de renta."""
    reglas = [
        ("DIVIDEND_DEFAULT", "dividends", "Dividendos", 30.0, None, None,
         "Tipo de retencion default para dividendos pagados a no residentes. Puede reducirse por convenio DTA.",
         "IRC Section 1441", "1441(a)", "activo"),
        ("DIVIDEND_DTA", "dividends", "Dividendos", 15.0, 30.0, None,
         "Tipo reducido para dividendos cuando aplica convenio de doble tributacion. Puede ser 5% si el beneficiario posee >=10% del capital.",
         "IRC Section 1442", "1442(b)", "activo"),
        ("INTEREST_DEFAULT", "interest", "Intereses", 30.0, None, None,
         "Tipo de retencion default para intereses de origen estadounidense (FDAP income).",
         "IRC Section 1441", "1441(a)", "activo"),
        ("INTEREST_DTA", "interest", "Intereses", 10.0, 30.0, None,
         "Tipo reducido para intereses cuando aplica convenio DTA.",
         "IRC Section 1442", "1442(b)", "activo"),
        ("ROYALTY_DEFAULT", "royalties", "Regalias", 30.0, None, None,
         "Tipo de retencion default para regalias e ingresos por propiedad intelectual.",
         "IRC Section 1441", "1441(a)", "activo"),
        ("ROYALTY_DTA", "royalties", "Regalias", 0.0, 30.0, None,
         "Muchos convenios DTA establecen 0% para regalias. Verificar convenio especifico.",
         "IRC Section 1442", "1442(b)", "activo"),
        ("CAPITAL_GAINS_DEFAULT", "capital_gains", "Ganancias de capital", 0.0, None, None,
         "Las ganancias de capital ordinarias de no residentes generalmente estan exentas de retencion en EE.UU., salvo excepciones (ej. propiedades inmobiliarias.",
         "IRC Section 871(a)", "871(a)(1)", "activo"),
        ("CAPITAL_GAINS_REIT", "capital_gains", "Ganancias de capital (REIT)", 0.0, None, None,
         "Ganancias por venta de acciones de REITs estadounidenses. Tipo 0% si el inversor posee <10% del REIT.",
         "IRC Section 871(k)", "871(k)", "activo"),
        ("CAPITAL_GAINS_FIRPTA", "capital_gains", "Ganancias de capital (FIRPTA)", 15.0, None, None,
         "FIRPTA: Ley de retencion en propiedades inmobiliarias extranjeras. 15% sobre el precio de venta de propiedades inmobiliarias estadounidenses.",
         "IRC Section 1445", "1445(c)", "activo"),
        ("SERVICE_FEE", "services", "Servicios", 30.0, None, None,
         "Tipo default para pagos por servicios a no residentes. Puede ser exento si no constituye establecimiento permanente.",
         "IRC Section 1441", "1441(a)", "activo"),
        ("PENSION", "pension", "Pensiones", 30.0, None, None,
         "Tipo default para pensiones y jubilaciones pagadas a no residentes.",
         "IRC Section 1441", "1441(a)", "activo"),
        ("GAMBLING", "gambling", "Apuestas y premios", 30.0, None, None,
         "Tipo de retencion para apuestas, loterias y premios a no residentes.",
         "IRC Section 1441", "1441(a)", "activo"),
    ]

    cur.execute("SELECT COUNT(*) FROM irs_withholding_rule")
    if cur.fetchone()[0] > 0:
        print("Withholding rules: ya existen datos, omitiendo seed")
        return

    for codigo, tipo_renta, tipo_es, ret_default, ret_dta, pais, desc, norma, articulo, estado in reglas:
        cur.execute(
            """INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol,
               tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion,
               norma_referencia, articulo_referencia, estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET descripcion = EXCLUDED.descripcion""",
            (codigo, tipo_renta, tipo_es, ret_default, ret_dta, pais, desc, norma, articulo, estado),
        )
    print(f"OK: {len(reglas)} reglas de retencion insertadas")


def seed_w8_forms(cur):
    """Formularios W-8 del IRS."""
    formularios = [
        ("W8BEN", "Formulario W-8BEN — Certificado de condicion extranjera para personas fisicas",
         "Persona fisica que no es residente de EE.UU.",
         "Certificar la condicion de no residente extranjero para reducir o eximir retencion del 30% sobre ingresos de EE.UU. (dividendos, intereses, royalties). Tambien se usa para reclamar beneficios de convenio de doble tributacion.",
         '{"parte_i": "Identificacion del beneficial owner (nombre, pais de ciudadania, direccion, TIN pais residencia, TIN EE.UU. si aplica, fecha nacimiento)",
          "parte_ii": "Descripcion de la renta (dividendos, intereses, royalties, otros)",
          "parte_iii": "Exenciones (solo si aplica IRC 871(l) o 881(c))",
          "parte_iv": "Reclamacion de beneficios del tratado de doble tributacion (pais, articulos del tratado)",
          "parte_v": "Firmas y fechas (debe ser firmada por el beneficial owner)",
          "parte_vi": "Identificacion de persona autorizada (si aplica)"}',
         3, "FATCA / IRC 1441",
         "Validez: ano calendario en que se firma + 3 anos completos. Termina si cambian las circunstancias que afectan la precision de la certificacion. Ejemplo: firmado en marzo 2024 -> valido hasta 31 dic 2027.",
         "activo"),
        ("W8BEN_E", "Formulario W-8BEN-E — Certificado de condicion extranjera para entidades",
         "Persona juridica (sociedad, trust, fondo, etc.) que no es residentede EE.UU.",
         "Certificar la condicion de entidad extranjera para reducir o eximir retencion. Incluye preguntas FATCA (tipo de entidad, GIIN, estado FATCA, controlling persons si es NFFE).",
         '{"parte_i": "Nombre de la entidad, pais de organizacion/residencia, direccion, TIN",
          "parte_ii": "Estado de la entidad (corporacion, partnership, trust, fondo gubernamental, etc.)",
          "parte_iii": "Propietario/beneficiario (si aplica)",
          "parte_iv": "Beneficial owner(s) — tipo, pais de residencia, numero de identificacion",
          "parte_v": "Capitulo 3 / Capitulo 4 (FATCA) — TIN, estado de retencion, codigo de exencion",
          "parte_vii": "FATCA — tipo de entidad FATCA (FFI, NFFE Active, NFFE Passive, Exempt beneficial owner, Sponsored entity, etc.), GIIN, estado FATCA",
          "parte_viii": "Controlling persons (solo NFFE Passive) — nombre, TIN, pais, fecha nacimiento"}',
         3, "FATCA / IRC 1441",
         "Validez: mismo que W-8BEN (3 anos + ano calendario en curso). Controlling persons debe actualizarse cada 3 anos si la entidad es NFFE Passive.",
         "activo"),
        ("W8EXP", "Formulario W-8EXP — Certificado de exencion para entidades exentas",
         "Entidad exenta de retencion (gobierno, organizacion sin animo de lucro, fondo pension, instituto tecnologico, etc.)",
         "Certificar la exencion de retencion del 30% sobre ingresos de EE.UU. para entidades especificamente exentas por el IRC.",
         '{"parte_i": "Identificacion de la entidad exenta",
          "parte_ii": "Descripcion de la exencion (gobierno, organizacion 501(c), fondo pension, etc.)",
          "parte_iii": "Certificacion del responsable (firmado por persona autorizada)"}',
         3, "FATCA / IRC 1441",
         "Validez: 3 anos + ano calendario en curso. Debe actualizarse si cambia la condicion de exencion.",
         "activo"),
        ("W8ECF", "Formulario W-8ECF — Personas no residentes con ingresos de EE.UU.",
         "Persona fisica no residente que necesita declarar ingresos de EE.UU. y presentar declaracion de la renta (Form 1040-NR). Tambien para entidades gubernamentales extranjeras.",
         "Certificar la condicion de no residente para fines de retencion y presentacion de declaraciones.",
         '{"parte_i": "Identificacion (nombre, direccion, TIN pais residencia, TIN EE.UU. si aplica)",
          "parte_ii": "Tipo de ingreso (salarios, honorarios, pension, otros)",
          "parte_iii": "Fecha de salida de EE.UU. (si aplica)",
          "parte_iv": "Firmas"}',
         3, "FATCA / IRC 1441",
         "Validez: 3 anos + ano calendario en curso.",
         "activo"),
        ("W9", "Formulario W-9 — Solicitud de TIN e identificacion de contribuyente",
         "Persona fisica o entidad de EE.UU. (residente)",
         "Solicitar el TIN (SSN o EIN) de contribuyentes estadounidenses. Se entrega al pagador, NO se presenta al IRS. Reemplaza al W-8 cuando el beneficiario es residente de EE.UU.",
         '{"parte_i": "Nombre, nombre comercial (si aplica), direccion",
          "parte_ii": "TIN (SSN para personas fisicas, EIN para entidades)",
          "parte_iii": "Tipo de entidad (individual/sole proprietor, C corporation, S corporation, Partnership, Trust/estate, LLC, etc.)",
          "parte_iv": "Solicitud de exencion de backup withholding (si aplica)",
          "parte_v": "Firma del contribuyente"}',
         None, "FATCA / IRC 1441",
         "Valido hasta que cambien los nombres, direccion o TIN. No tiene fecha de expiracion fija.",
         "activo"),
    ]

    cur.execute("SELECT COUNT(*) FROM irs_w8_form")
    if cur.fetchone()[0] > 0:
        print("W-8 forms: ya existen datos, omitiendo seed")
        return

    for codigo, nombre, descripcion, finalidad, partes_json, validez, obligacion, texto_detalle, estado in formularios:
        cur.execute(
            """INSERT INTO irs_w8_form (codigo, nombre, descripcion, finalidad, partes,
               validez_anios, obligacion_asociada, texto_detalle, estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre""",
            (codigo, nombre, descripcion, finalidad, partes_json, validez, obligacion, texto_detalle, estado),
        )
    print(f"OK: {len(formularios)} formularios W-8 insertados")


def seed_tin_references(cur):
    """Referencias TIN por pais — OCDE, No OCDE, EU VAT."""
    paises = [
        # OCDE
        ("ES", "Espana", "NIF: 12345678A / NIE: X1234567A", "B12345678", "Agencia Estatal de Administracion Tributaria (AEAT)", "Administratie Service Kantoors (ASK)", True, True),
        ("US", "Estados Unidos", "SSN: 123-45-6789 / EIN: 12-3456789 / ITIN: 9XX-70-XXXX", "12-3456789", "Internal Revenue Service (IRS)", "IRS", True, False),
        ("DE", "Alemania", "Steuernummer: 12345678901 / Steuer-ID", "12345678901", "Bundeszentralamt fur Steuern (BZSt)", "Bundesministerium der Finanzen (BMF)", True, True),
        ("FR", "Francia", "NIF: 12345678901234 / SIRET: 123 456 789 00012", "12345678901234", "Direction Generale des Finances Publiques (DGFiP)", "DGFiP", True, True),
        ("GB", "Reino Unido", "UTR: 1234567890 / CRN: 12345678", "1234567890", "HM Revenue & Customs (HMRC)", "Companies House", True, False),
        ("IT", "Italia", "Codice Fiscale: RSSMRA80A01H501Z / Partita IVA: 01234567890", "RSSMRA80A01H501Z", "Agenzia delle Entrate", "AdE", True, True),
        ("JP", "Japon", "TIN: 1234567890 / 法人番号: 1234567890123", "1234567890", "National Tax Agency (NTA)", "NTA", True, False),
        ("CA", "Canada", "SIN: 123 456 789 / BN: 123456789RC0001", "123456789", "Canada Revenue Agency (CRA)", "CRA", True, False),
        ("AU", "Australia", "TFN: 123456789 / ABN: 12 345 678 901", "123456789", "Australian Taxation Office (ATO)", "ATO", True, False),
        ("BR", "Brasil", "CPF: 123.456.789-01 / CNPJ: 12.345.678/0001-00", "12345678901", "Receita Federal do Brasil (RFB)", "RFB", True, False),
        ("MX", "Mexico", "RFC: XAXX010101000 / CURP: XAXX010101000000", "XAXX010101000", "Servicio de Administracion Tributaria (SAT)", "SAT", True, False),
        ("KR", "Corea del Sur", "TIN: 123-45-67890 / 사업자번호: 123-45-67890", "1234567890", "National Tax Service (NTS)", "NTS", True, False),
        ("IN", "India", "PAN: ABCDE1234F / TAN: ABCD12345A", "ABCDE1234F", "Income Tax Department (CBDT)", "CBDT", True, False),
        ("NL", "Paises Bajos", "BSN: 123456789 / BTW-ID: NL123456789B01", "123456789", "Belastingdienst", "Belastingdienst", True, True),
        ("SE", "Suecia", "Personnummer: 123456-7890 / Org.nr: 556XXX-XXXX", "556XXX-XXXX", "Skatteverket", "Skatteverket", True, True),
        ("CH", "Suiza", "AHV/Nr: 123.4567.8901.1234 / UID: CHE-123.456.789", "CHE-123.456.789", "Schweizerische Steuer Verwaltung (STEA)", "STEA", True, False),
        ("AT", "Austria", "Tax-ID: 1234567890", "1234567890", "Bundesministerium fur Finanzen (BMF)", "BMF", True, True),
        ("BE", "Belgica", "Numero TVA: 0123456789 / BCE: 0123456789", "0123456789", "Administration des Contributions Directes (ACD)", "ACD", True, True),
        ("NO", "Noruega", "Organisasjonsnummer: 123456789 / Foddselsnummer: 12345678901", "123456789", "Skatteetaten", "Skatteetaten", True, False),
        ("DK", "Dinamarca", "CVR: 12345678 / CPR-nummer: 123456-1234", "12345678", "Skattestyrelsen", "Skattestyrelsen", True, True),
        ("FI", "Finlandia", "Y-tunnus: 1234567-8 / Henkilotunnus: 123456-789X", "1234567-8", "Verohallinto", "Verohallinto", True, True),
        ("IE", "Irlanda", "PPS: 1234567T / Corporation Tax: 1234567A", "1234567A", "Revenue Commissioners", "Revenue", True, True),
        ("PT", "Portugal", "NIF: 123456789", "123456789", "Autoridade Tributaria e Aduaneira (AT)", "AT", True, True),
        ("PL", "Polonia", "NIP: 123-456-78-90 / PESEL: 12345678901", "12345678901", "Krajowa Administracja Skarbowa (KAS)", "KAS", True, True),
        ("CZ", "Rep. Checa", "IČ: 12345678 / IČ DPH: CZ12345678", "12345678", "Financni sprava Ceske republiky", "Financni sprava", True, True),
        ("RO", "Rumania", "CUI: 12345678 / CIF: RO12345678", "12345678", "Agentia Nationala de Administrare Fiscala (ANAF)", "ANAF", True, True),
        ("HU", "Hungria", "Adoazonosito jel: 12345678-2-13", "12345678-2-13", "Nemzeti Ado- es Vámhivatal (NAV)", "NAV", True, True),
        ("GR", "Grecia", "AFM: 123456789 / DOR: 123456789", "123456789", "Aforgeia (AADE)", "AADE", True, True),
        ("ZA", "Sudafrica", "SAT: 1234567890 / Corp: 1234/567/890", "1234567890", "South African Revenue Service (SARS)", "SARS", True, False),
        ("SG", "Singapur", "UEN: 12345678A / FIN: T1234567A", "12345678A", "Inland Revenue Authority of Singapore (IRAS)", "IRAS", True, False),
        ("NZ", "Nueva Zelanda", "IRD: 123-456-789 / BN: 12-345-678", "123456789", "Inland Revenue Department (IRD)", "IRD", True, False),
        ("CL", "Chile", "RUT: 12.345.678-9 / RUN: 12.345.678-9", "123456789", "Servicio de Impuestos Internos (SII)", "SII", True, False),
        ("AR", "Argentina", "CUIT: 20-12345678-9 / CUIL: 23-12345678-9", "20123456789", "Administracion Federal de Ingresos Publicos (AFIP)", "AFIP", True, False),
        ("CN", "China", "Unified Social Credit Code: 123456789012345678", "123456789012345678", "State Administration of Taxation (SAT)", "SAT China", True, False),
        # No OCDE
        ("AE", "Emiratos Arabes Unidos", "TIN: 123456789012345", "123456789012345", "Federal Authority for Taxation (FAT)", "FAT", False, False),
        ("SA", "Arabia Saudita", "CRN: 1234567890123456 / VAT: 312345678900003", "312345678900003", "Zakat Tax and Customs Authority (ZATCA)", "ZATCA", False, False),
        ("IL", "Israel", "PEH: 123456789 / HZ: 123456789", "123456789", "Ministry of Finance — Israel Tax Authority", "Israel Tax Authority", False, False),
        ("TR", "Turquia", "VKN: 1234567890 / MERSIN: 12345678901234", "1234567890", "Gelir Idare Baskanligi (GIB)", "GIB", False, False),
        ("NG", "Nigeria", "TIN: 12345678-0001", "123456780001", "Federal Inland Revenue Service (FIRS)", "FIRS", False, False),
        ("PH", "Filipinas", "TIN: 123-456-789-000 / ORC: 123456789", "123456789000", "Bureau of Internal Revenue (BIR)", "BIR", False, False),
        ("TH", "Tailandia", "TIN: 1234567890123", "1234567890123", "Revenue Department Thailand", "RD Thailand", False, False),
        ("ID", "Indonesia", "NPWP: 12.345.678.9-012.000", "123456789012000", "Direktorat Jenderal Pajak (DJP)", "DJP", False, False),
        ("CO", "Colombia", "NIT: 900.123.456-1 / CC: 1234567890", "9001234561", "Direccion de Impuestos y Aduanas Nacionales (DIAN)", "DIAN", False, False),
        ("PE", "Peru", "RUC: 20123456789 / DNI: 12345678", "20123456789", "Superintendencia Nacional de Aduanas y de Administracion Tributaria (SUNAT)", "SUNAT", False, False),
        # EU VAT adicionales
        ("BG", "Bulgaria", "EIK: 123456789 / DAN: BG123456789", "BG123456789", "NAP", "NAP", False, True),
        ("HR", "Croacia", "OIB: 12345678901 / PDV ID: HR12345678901", "HR12345678901", "Porezna uprava", "PU", False, True),
        ("SK", "Eslovaquia", "IČ DPH: SK1234567890", "SK1234567890", "Financna sprava", "Financna sprava", False, True),
        ("LT", "Lituania", "PVM kodas: LT123456789", "LT123456789", "VMI", "VMI", False, True),
        ("LV", "Letonia", "PVN kods: 12345678901", "12345678901", "Valsts iejamu dienests", "VID", False, True),
        ("EE", "Estonia", "KMKR: 123456789", "123456789", "Maksu- ja Tolliamet", "MTA", False, True),
        ("SI", "Eslovenia", "DDV: SI12345678", "SI12345678", "Financna uprava RS", "FURS", False, True),
        ("LU", "Luxemburgo", "NIF intracom.: LU12345678", "LU12345678", "Administration de la contribution directe (ACD)", "ACD", False, True),
        ("MT", "Malta", "VAT No.: CZ12345678", "CZ12345678", "Revenue Authority", "RA", False, True),
        ("CY", "Chipre", "VAT No.: CY12345678L", "CY12345678L", "Department of Taxation", "DOT", False, True),
    ]

    cur.execute("SELECT COUNT(*) FROM irs_tin_reference")
    if cur.fetchone()[0] > 0:
        print("TIN references: ya existen datos, omitiendo seed")
        return

    for codigo, nombre, formato, ejemplo, emisor_es, emisor_pais, ocde, eu_vat in paises:
        cur.execute(
            """INSERT INTO irs_tin_reference (codigo_pais, pais_nombre, formato_tin, ejemplo_tin,
               emisor_espana, emisor_pais, es_ocde, es_eu_vat)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo_pais) DO UPDATE SET pais_nombre = EXCLUDED.pais_nombre""",
            (codigo, nombre, formato, ejemplo, emisor_es, emisor_pais, ocde, eu_vat),
        )
    print(f"OK: {len(paises)} referencias TIN insertadas")


def seed_giin_registry(cur):
    """Registro GIIN/FFI/NFFE — muestra representativa."""
    registros = [
        ("ES123456789.12.3456", "Banco Santander S.A.", "ES", "FFI (Banco)", "activo", "2020-01-15", "2026-12-31", False, False, "Banco espanol con GIIN registrado en IRS FATCA registry"),
        ("ES987654321.23.4567", "BBVA — Banco Bilbao Vizcaya Argentaria", "ES", "FFI (Banco)", "activo", "2019-06-01", "2025-12-31", False, False, "Banco espanol con GIIN registrado"),
        ("ES111222333.44.5566", "La Caixa — Banc de Catalunya", "ES", "FFI (Banco)", "activo", "2021-03-10", "2027-12-31", False, False, "Entidad bancaria catalana con GIIN"),
        ("ES444555666.77.8899", "Bankinter S.A.", "ES", "FFI (Banco)", "activo", "2022-01-20", "2028-12-31", False, False, "Banco espanol con GIIN"),
        ("ES777888999.00.1122", "Mapfre SA", "ES", "FFI (Seguros)", "activo", "2020-07-01", "2026-06-30", False, False, "Entidad de seguros con GIIN"),
        ("US123456789.00.0000", "JPMorgan Chase Bank", "US", "FFI (Banco)", "activo", "2015-01-01", "2027-12-31", False, False, "Banco estadounidense — FFI con GIIN"),
        ("US987654321.00.0000", "Bank of America N.A.", "US", "FFI (Banco)", "activo", "2015-01-01", "2027-12-31", False, False, "Banco estadounidense — FFI"),
        ("GB111222333.00.0000", "Barclays Bank PLC", "GB", "FFI (Banco)", "activo", "2016-03-15", "2026-03-15", False, False, "Banco britanico con GIIN"),
        ("DE444555666.00.0000", "Deutsche Bank AG", "DE", "FFI (Banco)", "activo", "2016-06-01", "2026-06-01", False, False, "Banco aleman con GIIN"),
        ("FR777888999.00.0000", "BNP Paribas", "FR", "FFI (Banco)", "activo", "2016-09-01", "2026-09-01", False, False, "Banco francés con GIIN"),
        ("CH111222333.45.6789", "UBS Group AG", "CH", "FFI (Banco)", "activo", "2017-01-15", "2027-01-15", False, False, "Banco suizo con GIIN"),
        ("LU444555666.78.9012", "BGL BNP Paribas", "LU", "FFI (Banco)", "activo", "2018-04-01", "2028-04-01", False, False, "Banco luxemburgues con GIIN"),
        ("IE777888999.01.2345", "Irish Life & Permanent (AIB Group)", "IE", "FFI (Banco)", "activo", "2017-06-15", "2027-06-15", False, False, "Banco irlandés con GIIN"),
        ("US222333444.55.6677", "Vanguard Group Inc.", "US", "FFI (Fondo inversion)", "activo", "2015-06-01", "2027-12-31", False, False, "Gestora de fondos con GIIN"),
        ("US555666777.88.9900", "BlackRock Inc.", "US", "FFI (Fondo inversion)", "activo", "2015-09-01", "2027-12-31", False, False, "Gestora de activos con GIIN"),
        ("US888999000.11.2233", "Fidelity Management & Research", "US", "FFI (Fondo inversion)", "activo", "2016-01-15", "2027-12-31", False, False, "Gestora de fondos con GIIN"),
        ("ES333444555.66.7788", "Industria de Desarrollo Tecnologico S.A.", "ES", "NFFE Active", "activo", "2021-06-01", "2027-06-01", False, False, "NFFE activa — entidad no financiera con actividad operacional activa"),
        ("US666777888.99.0011", "TechCorp International LLC", "US", "NFFE Active", "activo", "2020-03-01", "2026-03-01", False, False, "NFFE activa estadounidense"),
        ("ES999000111.22.3344", "Fundacion Espanola para la Ciencia y Tecnologia", "ES", "Exempt beneficial owner", "activo", "2022-01-01", "2028-01-01", True, False, "Exempt beneficial owner — entidad gubernamental/exenta"),
        ("US123000111.22.3344", "American Red Cross", "US", "Exempt beneficial owner", "activo", "2019-01-01", "2025-12-31", True, False, "Organizacion exenta de FATCA"),
    ]

    cur.execute("SELECT COUNT(*) FROM giin_registry")
    if cur.fetchone()[0] > 0:
        print("GIIN registry: ya existen datos, omitiendo seed")
        return

    for giin, nombre, pais, tipo, estado, fecha_reg, fecha_exp, exempt, sponsored, nota in registros:
        cur.execute(
            """INSERT INTO giin_registry (giin, entidad_nombre, entidad_pais, tipo_entidad,
               estado_fatca, fecha_registro, fecha_expiracion, es_exempt_beneficial_owner,
               es_sponsored_ffo, nota)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (giin) DO UPDATE SET entidad_nombre = EXCLUDED.entidad_nombre""",
            (giin, nombre, pais, tipo, estado, fecha_reg, fecha_exp, exempt, sponsored, nota),
        )
    print(f"OK: {len(registros)} registros GIIN insertados")


def main():
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            seed_irs_fiscal_norma(cur)
            seed_dta_conventions(cur)
            seed_withholding_rules(cur)
            seed_w8_forms(cur)
            seed_tin_references(cur)
            seed_giin_registry(cur)
        conn.commit()
        print("Seed IRS/Fiscal Internacional completado")


if __name__ == "__main__":
    main()
