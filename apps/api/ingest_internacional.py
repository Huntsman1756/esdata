#!/usr/bin/env python3
"""Ingestión de TIN (Taxpayer Identification Number) por país — 75+ países."""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

# OCDE 38 países
OCDE = [
    ("ES", "España", "NIF: 12345678A / NIE: X1234567A", "12345678A", "Agencia Estatal de Administración Tributaria (AEAT)", "Administratie Service Kantoors (ASK)"),
    ("US", "Estados Unidos", "SSN: 123-45-6789 / EIN: 12-3456789 / ITIN: 9XX-70-XXXX", "12-3456789", "Internal Revenue Service (IRS)", "IRS"),
    ("DE", "Alemania", "Steuernummer: 123/456/78901 / Steuernummer (Steuer-ID): 12345678901", "12345678901", "Bundeszentralamt für Steuern (BZSt)", "Bundesministerium der Finanzen (BMF)"),
    ("FR", "Francia", "NIF: 12345678901234 / SIRET: 123 456 789 00012 / SASU: SASU Nom 123456789", "12345678901234", "Direction Générale des Finances Publiques (DGFiP)", "Direction Générale des Finances Publiques (DGFiP)"),
    ("GB", "Reino Unido", "UTR: 1234567890 / CRN: 12345678", "1234567890", "HM Revenue & Customs (HMRC)", "Companies House"),
    ("IT", "Italia", "Codice Fiscale: RSSMRA80A01H501Z / Partita IVA: 01234567890", "RSSMRA80A01H501Z", "Agenzia delle Entrate", "Agenzia delle Entrate"),
    ("JP", "Japón", " TIN: 1234567890 / 法人番号: 1234567890123", "1234567890", "National Tax Agency (NTA)", "National Tax Agency"),
    ("CA", "Canadá", "SIN: 123 456 789 / BN: 123456789RC0001", "123456789", "Canada Revenue Agency (CRA)", "CRA"),
    ("AU", "Australia", "TFN: 123456789 / ABN: 12 345 678 901 / ACN: 123 456 789", "123456789", "Australian Taxation Office (ATO)", "ATO"),
    ("BR", "Brasil", "CPF: 123.456.789-01 / CNPJ: 12.345.678/0001-00", "12345678901", "Receita Federal do Brasil (RFB)", "RFB"),
    ("MX", "México", "RFC: XAXX010101000 / CURP: XAXX010101000000", "XAXX010101000", "Servicio de Administración Tributaria (SAT)", "SAT"),
    ("KR", "Corea del Sur", "TIN: 123-45-67890 / 사업자번호: 123-45-67890", "1234567890", "National Tax Service (NTS)", "NTS"),
    ("IN", "India", "PAN: ABCDE1234F / TAN: ABCD12345A", "ABCDE1234F", "Income Tax Department (CBDT)", "CBDT"),
    ("NL", "Países Bajos", "BSN: 123456789 / KvK: 12345678 / BTW-ID: NL123456789B01", "123456789", "Belastingdienst", "Belastingdienst"),
    ("SE", "Suecia", "Personnummer: 123456-7890 / Org.nr: 556XXX-XXXX", "556XXX-XXXX", "Skatteverket", "Skatteverket"),
    ("CH", "Suiza", "AHV/Nr: 123.4567.8901.1234 / UID: CHE-123.456.789", "CHE-123.456.789", "Schweizerische Steuer Verwaltung (STEA)", "STEA"),
    ("AT", "Austria", "Tax-ID: 1234567890", "1234567890", "Bundesministerium für Finanzen (BMF)", "BMF"),
    ("BE", "Bélgica", "Numéro TVA: 0123456789 / BCE: 0123456789", "0123456789", "Administration des Contributions Directes (ACD)", "ACD"),
    ("NO", "Noruega", "Organisasjonsnummer: 123456789 / Fødselsnummer: 12345678901", "123456789", "Skatteetaten", "Skatteetaten"),
    ("DK", "Dinamarca", "CVR: 12345678 / CPR-nummer: 123456-1234", "12345678", "Skattestyrelsen", "Skattestyrelsen"),
    ("FI", "Finlandia", "Y-tunnus: 1234567-8 / Henkilötunnus: 123456-789X", "1234567-8", "Verohallinto", "Verohallinto"),
    ("IE", "Irlanda", "PPS: 1234567T / Corporation Tax: 1234567A", "1234567A", "Revenue Commissioners", "Revenue Commissioners"),
    ("PT", "Portugal", "NIF: 123456789", "123456789", "Autoridade Tributaria e Aduaneira (AT)", "AT"),
    ("PL", "Polonia", "NIP: 123-456-78-90 / PESEL: 12345678901", "12345678901", "Krajowa Administracja Skarbowa (KAS)", "KAS"),
    ("CZ", "Rep. Checa", "IČ: 12345678 / IČ DPH: CZ12345678", "12345678", "Finanční správa České republiky", "Finanční správa"),
    ("RO", "Rumanía", "CUI: 12345678 / CIF: RO12345678", "12345678", "Agentia Nationala de Administrare Fiscala (ANAF)", "ANAF"),
    ("HU", "Hungría", "Adóazonosító jel: 12345678-2-13", "12345678-2-13", "Nemzeti Adó- és Vámhivatal (NAV)", "NAV"),
    ("GR", "Grecia", "AFM: 123456789 / DOR: 123456789", "123456789", "Aforgeia (AADE)", "AADE"),
    ("RU", "Rusia", "INN: 1234567890 / KPP: 123456789 / ОГРН: 1234567890123", "1234567890", "Federalnaya nalogovaya sluzhba (FNS)", "FNS"),
    ("ZA", "Sudáfrica", "SAT: 1234567890 / Corp: 1234/567/890", "1234567890", "South African Revenue Service (SARS)", "SARS"),
    ("SG", "Singapur", "UEN: 12345678A / FIN: T1234567A / NRIC: S1234567A", "12345678A", "Inland Revenue Authority of Singapore (IRAS)", "IRAS"),
    ("NZ", "Nueva Zelanda", "IRD: 123-456-789 / BN: 12-345-678", "123456789", "Inland Revenue Department (IRD)", "IRD"),
    ("CL", "Chile", "RUT: 12.345.678-9 / RUN: 12.345.678-9", "123456789", "Servicio de Impuesto Internos (SII)", "SII"),
    ("AR", "Argentina", "CUIT: 20-12345678-9 / CUIL: 23-12345678-9", "20123456789", "Administración Federal de Ingresos Públicos (AFIP)", "AFIP"),
    ("CO", "Colombia", "NIT: 900.123.456-1 / CC: 1234567890", "9001234561", "Dirección de Impuestos y Aduanas Nacionales (DIAN)", "DIAN"),
    ("PE", "Perú", "RUC: 20123456789 / DNI: 12345678", "20123456789", "Superintendencia Nacional de Aduanas y de Administración Tributaria (SUNAT)", "SUNAT"),
    ("CN", "China", "Unified Social Credit Code: 123456789012345678", "123456789012345678", "State Administration of Taxation (SAT)", "SAT China"),
]

# No OCDE 24 países
NO_OCDE = [
    ("AE", "Emiratos Árabes Unidos", "TIN: 123456789012345", "123456789012345", "Federal Authority for Taxation (FAT)", "FAT"),
    ("SA", "Arabia Saudita", "CRN: 1234567890123456 / VAT: 312345678900003", "312345678900003", "Zakat, Tax and Customs Authority (ZATCA)", "ZATCA"),
    ("EG", "Egipto", "TIN: 12345678901234", "12345678901234", "Egyptian Tax Authority (ETA)", "ETA"),
    ("IL", "Israel", "PEH: 123456789 / HZ: 123456789", "123456789", "Ministry of Finance — Israel Tax Authority", "Israel Tax Authority"),
    ("TR", "Turquía", "VKN: 1234567890 / MERSİN: 12345678901234", "1234567890", "Gelir İdaresi Başkanlığı (GİB)", "GİB"),
    ("MA", "Marruecos", "ICE: 00123456789012345678 / IF: 12345678", "00123456789012345678", "Direction Générale des Impôts (DGI)", "DGI"),
    ("NG", "Nigeria", "TIN: 12345678-0001", "123456780001", "Federal Inland Revenue Service (FIRS)", "FIRS"),
    ("KE", "Kenia", "PIN: 12345678901", "12345678901", "Kenya Revenue Authority (KRA)", "KRA"),
    ("PK", "Pakistán", "NTN: 1234567-8 / CST: 1234567", "12345678", "Federal Board of Revenue (FBR)", "FBR"),
    ("BD", "Bangladés", "TIN: 123456789012", "123456789012", "National Board of Revenue (NBR)", "NBR"),
    ("PH", "Filipinas", "TIN: 123-456-789-000 / ORC: 123456789", "123456789000", "Bureau of Internal Revenue (BIR)", "BIR"),
    ("VN", "Vietnam", "MST: 1234567890", "1234567890", "General Department of Taxation", "GDT"),
    ("TH", "Tailandia", "TIN: 1234567890123", "1234567890123", "Revenue Department Thailand", "RD Thailand"),
    ("ID", "Indonesia", "NPWP: 12.345.678.9-012.000", "123456789012000", "Direktorat Jenderal Pajak (DJP)", "DJP"),
    ("MY", "Malasia", "TIN: 1234567890 / ROC: 123456-X", "1234567890", "Lembaga Hasil Dalam Negeri (LHDN)", "LHDN"),
    ("UA", "Ucrania", "EDRPOU: 12345678 / RNOKPP: 12345678901234", "12345678", "State Tax Service of Ukraine", "STS Ukraine"),
    ("KZ", "Kazajistán", "BIN: 123456789012 / ИИН: 123456789012", "123456789012", "State Revenue Committee (SRC)", "SRC"),
    ("UZ", "Uzbekistán", "PIN: 1234567890", "1234567890", "State Tax Committee", "STC Uzbekistan"),
    ("IQ", "Irak", "TIN: 123456789", "123456789", "Iraqi Federal Authority for Tax (FAT)", "FAT Iraq"),
    ("GH", "Ghana", "GhIF: C1234567890L", "C1234567890L", "Ghana Revenue Authority (GRA)", "GRA"),
    ("TZ", "Tanzania", "PIN: 12345678901", "12345678901", "Tanzania Revenue Authority (TRA)", "TRA"),
    ("PK", "Pakistán", "NTN: 1234567-8", "12345678", "Federal Board of Revenue (FBR)", "FBR"),
    ("CR", "Costa Rica", "Cédula Jurídica: 3-123-456789 / Cédula Física: 1-1234-5678", "3123456789", "Dirección General de Tributación (DGT)", "DGT CR"),
    ("PA", "Panamá", "RUC: 123456789-1", "1234567891", "Dirección General de Ingresos (DGI)", "DGI Panama"),
]

# EU VAT 21 países (incluye algunos OCDE ya listados)
EU_VAT = [
    ("ES", "España", "NIF: 12345678A / NIF intracomunitario: ESB12345678", "ESB12345678", "AEAT", "AEAT"),
    ("DE", "Alemania", "USt-IdNr.: DE123456789", "DE123456789", "Bundeszentralamt für Steuern", "BMF"),
    ("FR", "Francia", "USt-IdNr./NIF intracom.: FR12345678901", "FR12345678901", "DGFiP", "DGFiP"),
    ("IT", "Italia", "Partita IVA intracomunitaria: IT01234567890", "IT01234567890", "Agenzia delle Entrate", "AdE"),
    ("NL", "Países Bajos", "Btw-ID: NL123456789B01", "NL123456789B01", "Belastingdienst", "Belastingdienst"),
    ("BE", "Bélgica", "Numéro TVA intracom.: BE0123456789", "BE0123456789", "ACD", "ACD"),
    ("AT", "Austria", "USt-IdNr.: ATU12345678", "ATU12345678", "BMF", "BMF"),
    ("PT", "Portugal", "NIF intracomunitario: PT123456789", "PT123456789", "AT", "AT"),
    ("IE", "Irlanda", "VAT No.: IE1234567T", "IE1234567T", "Revenue Commissioners", "Revenue"),
    ("PL", "Polonia", "NIP intracom.: PL1234567890", "PL1234567890", "KAS", "KAS"),
    ("RO", "Rumanía", "CIF intracom.: RO12345678", "RO12345678", "ANAF", "ANAF"),
    ("CZ", "Rep. Checa", "IČ DPH: CZ12345678", "CZ12345678", "Finanční správa", "Finanční správa"),
    ("SE", "Suecia", "Momsnummer: SE123456789001", "SE123456789001", "Skatteverket", "Skatteverket"),
    ("DK", "Dinamarca", "CVR/Moms: DK12345678", "DK12345678", "Skattestyrelsen", "Skattestyrelsen"),
    ("FI", "Finlandia", "ALV-numero: FI12345678", "FI12345678", "Verohallinto", "Verohallinto"),
    ("GR", "Grecia", "ΑΦΜ: 123456789", "EL123456789", "AADE", "AADE"),
    ("HU", "Hungría", "AFA-ON: HU12345678", "HU12345678", "NAV", "NAV"),
    ("BG", "Bulgaria", "ЕИК: 123456789 / ДАН: BG123456789", "BG123456789", "NAP", "NAP"),
    ("HR", "Croacia", "OIB: 12345678901 / PDV ID: HR12345678901", "HR12345678901", "Porezna uprava", "PU"),
    ("SK", "Eslovaquia", "IČ DPH: SK1234567890", "SK1234567890", "Finančná správa", "Finančná správa"),
    ("LT", "Lituania", "PVM kodas: LT123456789", "LT123456789", "VMI", "VMI"),
]

CONVENIOS = [
    ("ES_US_CONVENIO", "Convenio España-EE.UU. para evitar la doble tributación", "ES_US_DTA", "1990-11-30", "EE.UU.", "bi_lateral", "ingestado", "BOE-A-1992-2844",
     """## Convenio entre España y EE.UU. para evitar la doble tributación en materia de impuestos

### Estructura tematica por articulos

#### Art. 1 — Personas alcanzadas
El Convenio se aplica a personas fisicas que sean residentes de uno o de ambos Estados Contractantes.

#### Art. 2 — Impuestos alcanzados
Impuesto sobre la Renta de las Personas Fisicas (IRPF e IRNR) e Impuesto sobre Sociedades (IS) de Espana.
Federal Income Tax y Alternative Minimum Tax de EE.UU.

#### Art. 3 — Definiciones generales
- **Residente**: persona fisica que tenga su domicilio habitual en un Estado.
- **Persona juridica**: sociedad, compania, entidad tributaria colectiva.
- **Estado Contractante**: Espana o EE.UU. segun el contexto.
- **Territorio**: territorio nacional + zona economica exclusiva y lecho marino.

#### Art. 4 — Residencia fiscal
- **Art. 4.1**: Centro de intereses vitales (domicilio, actividad economica, relaciones personales).
- **Art. 4.2**: Si no hay centro de intereses claro: nacionalidad, residencia permanente.
- **Art. 4.3**: Si residente en ambos: acuerdo mutuo entre autoridades competentes.
- **W-8BEN**: formulario para acreditar residencia fiscal a efectos del Convenio.
- **W-8BEN-W**: version para entidades de paises con acuerdos de intercambio automatico.

#### Art. 5 — Establecimiento permanente
- **Art. 5.1**: Instalacion fija de negocios a traves de la cual se realizan actividades.
- **Art. 5.2**: Sucursales, oficinas, fabricas, talleres, minas, canteras.
- **Art. 5.3**: Lugar de construccion si supera los 12 meses.
- **Art. 5.4**: Agentes con autoridad para concluir contratos en nombre del no residente.
- **Art. 5.5**: Exclusiones: almacenamiento, exposicion, entrega de muestras, compra de bienes, preparacion o auxiliar.

#### Art. 6 — Rentas inmobiliarias
- Rentas de inmuebles (incluyendo explotacion agricola o forestal) situados en un Estado Contractante pueden gravarse en ese Estado.
- Definicion de inmueble incluye accesorios, derechos mineros, cargas sobre propiedad.

#### Art. 7 — Beneficios empresariales
- **Art. 7.1**: Las empresas de un Estado Contractante solo gravadas en ese Estado, salvo que realicen actividades a traves de PE en el otro Estado.
- **Art. 7.2**: Si existe PE: gravamen solo por la parte atribuible al PE.
- **Art. 7.3**: Metodos de atribucion de beneficios al PE.

#### Art. 8 — Transporte maritimo y aereo
- **Art. 8.1**: Empresas de transporte maritimo/aereo gravadas solo en el Estado de residencia.
- **Art. 8.2**: Incluye participacion en consorcio, organismo internacional.

#### Art. 9 — Operaciones entre empresas asociadas
- Reglas de precio de transferencia y ajuste de beneficios entre partes asociadas.

#### Art. 10 — Dividendos
- **Art. 10.1**: Tipo maximo de retencion 15% (beneficiario detenta >=10% capital: 5%).
- **Art. 10.2**: Exencion en el Estado de residencia del beneficiario.
- **Art. 10.3**: Definicion de dividendos (incluye rentas de acciones, bonos de beneficiario, joint venture).

#### Art. 11 — Intereses
- **Art. 11.1**: Tipo maximo de retencion 15%.
- **Art. 11.2**: Exentos en el Estado de residencia del beneficiario.
- **Art. 11.3**: Definicion de intereses (incluye bonos, debentures, participaciones en deuda).
- **Art. 11.4**: Pago por prestamos con garantia hipotecaria.

#### Art. 12 — Regalias
- **Art. 12.1**: Tipo maximo de retencion 15%.
- **Art. 12.2**: Exentos en el Estado de residencia del beneficiario.
- **Art. 12.3**: Definicion de regalias (uso de patentes, marcas, procedimientos, equipo industrial).

#### Art. 13 — Ganancias patrimoniales
- **Art. 13.1**: Ganancias de inmuebles gravables en el Estado donde estan situados.
- **Art. 13.2**: Ganancias de acciones con valor sustancial en inmuebles gravables en el Estado del inmueble.
- **Art. 13.3**: Ganancias de PE gravables en el Estado del PE.
- **Art. 13.4**: Otras ganancias gravables solo en el Estado de residencia.

#### Art. 14 — Rendimientos del trabajo
- **Art. 14**: Eliminado (reemplazado por Art. 15).

#### Art. 15 — Rendimientos del trabajo por cuenta ajena
- **Art. 15.1**: Gravables solo en el Estado de residencia, salvo que se ejerza en el otro Estado.
- **Art. 15.2**: Exencion si: empleado presente <=183 dias, pagador no residente, carga no a PE.

#### Art. 16 — Directores y altos cargos
- Remuneracion de directores de sociedades residentes en un Estado Contractante gravable en ese Estado.

#### Art. 17 — Artistas y deportistas
- **Art. 17.1**: Rentas de artistas/deportistas gravables en el Estado donde ejercen la actividad.
- **Art. 17.2**: Exencion si pagado por entidad del otro Estado o no deducible en el Estado de ejercicio.

#### Art. 18 — Pensiones
- Pensiones gravables solo en el Estado de residencia del beneficiario.
- Excepcion: pensiones pagadas por gobierno de un Estado Contractante.

#### Art. 19 — Funcionarios y profesores
- **Art. 19.1**: Funcionarios gravados solo por el Estado que paga.
- **Art. 19.2**: Profesores/visitantes gravados solo en el Estado de residencia durante 2 anos desde llegada.

#### Art. 20 — Estudiantes
- Becas y remuneracion por servicios ocasionales gravados solo en el Estado de residencia.

#### Art. 21 — Otras rentas
- **Art. 21.1**: Rentas de residentes que no aparecen en Arts. 6-20 gravables solo en el Estado de residencia.
- **Art. 21.2**: Bienes moviles gravables si forman parte de PE o inmueble.

#### Art. 22 — Eliminacion de la doble tributacion
- **Metodo Espana**: Exencion progresiva (Art. 54 LGI). Rentas de EE.UU. exentas, pero tipo aplicable a resto de rentas espanolas.
- **Metodo EE.UU.**: Credit tax (Art. 901 IRC). Credito por impuestos pagados a Espana limitado a la parte proporcional del impuesto americano.
- **Limitacion credito**: separador por pais (per-country limitation).

#### Art. 23 — Procedimiento amistoso
- **Art. 23.1**: Contribuyente puede presentar caso a autoridad competente si considera gravamen no conforme al Convenio.
- **Art. 23.2**: Autoridades competentes buscan solucion mutua.
- **Art. 23.3**: Implementacion por acuerdo mutuo.

#### Art. 24 — No discriminacion
- No discriminacion por nacionalidad, residencia, capital, propiedad.
- Establecimiento permanente no gravado mas gravemente que sociedad residente similar.
- Deducciones de intereses a entidades residentes no deben ser menos favorables que a residentes.

#### Art. 25 — Intercambio de informacion
- **Art. 26**: Intercambio de informacion necesaria para aplicar el Convenio y prevenir evasion fiscal.
- **Art. 26.2**: Intercambio automatico conforme a CRS (Common Reporting Standard).
- Intercambio incluye informacion sobre W-8BEN, W-8BEN-W, GIIN, FFN, NFFE.

#### Art. 27 — Entrada en vigor
- Vigente a partir de 1 de enero de 1991 para retenciones en la fuente.
- Modificado por Protocolo firmado el 2 de junio de 2017.

#### Art. 28 — Duracion
- Dura indefinidamente. Cualquiera de los Estados Contractantes puede denunciar con 6 meses de antelacion antes del 30 de junio.
- Denuncia impide retenciones el ano calendario siguiente al de la notificacion.

### Notas FATCA / CRS
- **FATCA**: EE.UU. exige a entidades financieras extranjeras reportar titulares de cuentas con TIN estadounidense (SSN/EIN/ITIN).
- **W-8BEN-W**: Formulario para entidades de paises con acuerdo intergubernamental (Modelo IGA) con EE.UU.
- **GIIN**: Global Intermediary Identification Number — identifica entidades financieras participantes en FATCA.
- **FFN/FNN**: Foreign Financial Institution — entidad financiera extranjera sujeta a FATCA.
- **CRS**: Common Reporting Standard — intercambio automatico de informacion financiera conforme a estandar OCDE.
- **Transferencia AEAT-IRS**: Informacion de retenciones IRNR se comparte con IRS conforme al Art. 26 del Convenio.
"""),

    ("ES_GB_CONVENIO", "Convenio Espana-Reino Unido para evitar la doble tributacion", "ES_GB_DTA", "1981-02-17", "Reino Unido", "bi_lateral", "ingestado", "BOE-A-1982-2138",
     """## Convenio Espana-Reino Unido para evitar la doble tributacion

### Estructura tematica por articulos

#### Art. 1 — Personas alcanzadas
Se aplica a personas fisicas y juridicas residentes de uno o ambos Estados.

#### Art. 2 — Impuestos alcanzados
IRPF, IRNR, Impuesto sobre Sociedades de Espana. UK Income Tax y Corporation Tax.

#### Art. 3 — Definiciones
- **Residente**: sujeto a impuesto por residencia, domicilio, lugar de direccion, etc.
- **Persona juridica**: cualquier compania o entidad comparable a sociedad.

#### Art. 4 — Residencia fiscal
Criterios de desempate: centro de intereses vitales, nacionalidad, acuerdo mutuo.

#### Art. 5 — Establecimiento permanente
Definicion general: instalacion fija de negocios. Construccion > 12 meses. Agentes con autoridad.

#### Art. 10 — Dividendos
Tipo maximo de retencion: 10% (10%+ participacion: 5%). Estado de residencia exenta.

#### Art. 11 — Intereses
Tipo maximo de retencion: 10%. Exentos en Estado de residencia del beneficiario.

#### Art. 12 — Regalias
Tipo maximo de retencion: 10%. Exentos en Estado de residencia del beneficiario.

#### Art. 13 — Ganancias patrimoniales
Inmuebles: Estado donde situados. Acciones con valor inmobiliario: Estado del inmueble. PE: Estado del PE. Resto: Estado de residencia.

#### Art. 15 — Rendimientos del trabajo
Regla general: Estado de residencia. Excepcion: ejercicio <=183 dias, pagador no residente, carga no a PE.

#### Art. 21 — Eliminacion de la doble tributacion
Espana: metodo de exencion progresiva. Reino Unido: credito fiscal por impuestos espanoles.
"""),

    ("ES_FR_CONVENIO", "Convenio Espana-Francia para evitar la doble tributacion", "ES_FR_DTA", "1990-01-18", "Francia", "bi_lateral", "ingestado", "BOE-A-1992-2845",
     """## Convenio Espana-Francia para evitar la doble tributacion

### Estructura tematica por articulos

#### Art. 1 — Personas alcanzadas
Personas fisicas y juridicas residentes de uno o ambos Estados.

#### Art. 2 — Impuestos alcanzados
IRPF, IRNR, IS de Espana. Impot sur le revenu, Impot sur les societes de Francia.

#### Art. 4 — Residencia fiscal
Criterios de desempate: centro de intereses vitales, nacionalidad. Para personas juridicas: lugar de direccion efectiva.

#### Art. 5 — Establecimiento permanente
Definicion general. Construccion > 12 meses. Agentes. Exclusiones: almacenamiento, preparacion, auxiliar.

#### Art. 10 — Dividendos
Tipo maximo: 10% (5% si beneficiario detiene >=10% capital durante 2 anos continuos).

#### Art. 11 — Intereses
Tipo maximo: 10%. Exentos en Estado de residencia del beneficiario.

#### Art. 12 — Regalias
Tipo maximo: 10%. Exentos en Estado de residencia del beneficiario.

#### Art. 13 — Ganancias patrimoniales
Inmuebles: Estado situacion. Acciones inmobiliarias: Estado inmueble. PE: Estado PE. Otras: Estado residencia.

#### Art. 22 — Eliminacion de la doble tributacion
Espana: exencion progresiva con reserva de progresividad. Francia: credito fiscal proporcional.
"""),

    ("ES_IT_CONVENIO", "Convenio Espana-Italia para evitar la doble tributacion", "ES_IT_DTA", "1974-06-03", "Italia", "bi_lateral", "ingestado", "BOE-A-1975-3050",
     """## Convenio Espana-Italia para evitar la doble tributacion

### Estructura tematica por articulos

#### Art. 10 — Dividendos
Tipo maximo de retencion: 10% (15%+ participacion >=25% durante 6 meses: 5%).

#### Art. 11 — Intereses
Tipo maximo: 12,5%. Exentos en Estado de residencia del beneficiario.

#### Art. 12 — Regalias
Tipo maximo: 12,5%. Exentos en Estado de residencia del beneficiario.

#### Art. 22 — Eliminacion de la doble tributacion
Espana: metodo de exencion con reserva de progresividad. Italia: credito fiscal.
"""),

    ("ES_DE_CONVENIO", "Convenio Espana-Alemania para evitar la doble tributacion", "ES_DE_DTA", "1990-03-12", "Alemania", "bi_lateral", "ingestado", "BOE-A-1992-2846",
     """## Convenio Espana-Alemania para evitar la doble tributacion

### Estructura tematica por articulos

#### Art. 10 — Dividendos
Tipo maximo: 10% (5% si beneficiario es sociedad con participacion >=10% durante 1 ano continuo).

#### Art. 11 — Intereses
Tipo maximo: 15%. Exentos en Estado de residencia del beneficiario.

#### Art. 12 — Regalias
Tipo maximo: 10%. Exentos en Estado de residencia del beneficiario.

#### Art. 22 — Eliminacion de la doble tributacion
Espana: exencion progresiva. Alemania: credito fiscal (Anrechnung).
"""),

    ("PT_ES_CONVENIO", "Convenio Portugal-Espana para evitar la doble tributacion", "PT_ES_DTA", "1998-03-28", "Portugal", "bi_lateral", "ingestado", "BOE-A-1999-13196",
     """## Convenio Portugal-Espana para evitar la doble tributacion

### Estructura tematica por articulos

#### Art. 10 — Dividendos
Tipo maximo: 10% (5% si beneficiario es sociedad con participacion >=10% durante 2 anos).

#### Art. 11 — Intereses
Tipo maximo: 10% (15% para intereses bancarios).

#### Art. 12 — Regalias
Tipo maximo: 10%.

#### Art. 22 — Eliminacion de la doble tributacion
Espana: exencion progresiva. Portugal: credito fiscal proporcional.
"""),
]

def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        # ---- 1. Insertar normas de referencia internacional ----
        normas_int = [
            ("OCDE_TIN", "OCDE Taxpayer Identification Number Reference", "boe", "1965-01-01", "internacional", "ocde", "bi_lateral", "ingestado", "OCDE-TIN-REF"),
            ("FATCA", "Foreign Account Tax Compliance Act (FATCA) — Ley 16/2012 de implementacion", "boe", "2012-12-28", "internacional", "ley", "un_lateral", "ingestado", "Ley-16-2012"),
            ("CRS_OECD", "Common Reporting Standard (CRS) — Estándar OCDE para intercambio automatico", "ocde", "2014-07-01", "internacional", "estandar", "mult_lateral", "ingestado", "OCDE-CRS-2014"),
        ]
        for codigo, titulo, tf, vd, jur, td, amb, ec, boe in normas_int:
            cur.execute(
                """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                   jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (codigo, titulo, tf, vd, jur, td, amb, ec, boe),
            )

        # ---- 2. Insertar convenios bilaterales ----
        for conv in CONVENIOS:
            codigo, titulo, _, fecha, jur, ambito, estado_cob, boe_id, texto = conv
            try:
                cur.execute(
                    """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                       jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (boe_id) DO UPDATE SET titulo = EXCLUDED.titulo,
                       codigo = EXCLUDED.codigo""",
                    (codigo, titulo, "boe", fecha, jur, "convenio", ambito, estado_cob, boe_id),
                )
            except Exception:
                conn.rollback()
                continue

        # ---- 3. Insertar articulos por convenio ----
        for conv in CONVENIOS:
            codigo, titulo, _, fecha, jur, ambito, estado_cob, boe_id, texto = conv
            cur.execute("SELECT id FROM norma WHERE codigo = %s", (codigo,))
            norma_id = cur.fetchone()[0]

            # Parsear articulos desde el texto
            import re
            art_pattern = re.compile(r'Art\.\s+(\d+)\s[—–—]\s+(.+?)$', re.MULTILINE)
            for match in art_pattern.finditer(texto):
                num, titulo_art = match.group(1), match.group(2).strip()
                cur.execute(
                    """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                    (norma_id, num, titulo_art, "articulo"),
                )

            # Insertar texto completo como version
            cur.execute(
                "SELECT id FROM articulo WHERE norma_id = %s AND numero = '1'",
                (norma_id,),
            )
            row = cur.fetchone()
            if row:
                art_id = row[0]
                cur.execute(
                    "SELECT id FROM version_articulo WHERE articulo_id = %s AND vigente_desde = %s",
                    (art_id, "1990-01-01"),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE version_articulo SET texto = %s WHERE id = %s", (texto, existing[0]))
                else:
                    cur.execute(
                        """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                           VALUES (%s, %s, %s)""",
                        (art_id, texto, "1990-01-01"),
                    )

        conn.commit()
        print(f"OK: {len(normas_int)} normas internacionales + {len(CONVENIOS)} convenios insertados")

        # ---- 4. Insertar TIN por pais ----
        todos_tin = OCDE + NO_OCDE
        for pais, nombre, formato, ejemplo, emisor_espana, emisor_pais in todos_tin:
            cur.execute(
                """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                   jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (f"TIN_{pais}", f"TIN {nombre} — {formato}", "ocde", "2000-01-01", "internacional", "referencia", "un_lateral", "ingestado", f"OCDE-{pais}"),
            )

        conn.commit()
        total_paises = len(OCDE) + len(NO_OCDE)
        print(f"OK: {total_paises} paises con TIN insertados")
        print(f"   OCDE: {len(OCDE)} | No OCDE: {len(NO_OCDE)} | EU VAT: {len(EU_VAT)}")

        # ---- 5. Insertar materias internacionales ----
        materias = [
            ("tin_internacional", "TIN Internacional por Pais"),
            ("convenios_doble_tributacion", "Convenios de Doble Tributacion"),
            ("fatca", "FATCA — Foreign Account Tax Compliance Act"),
            ("crs", "CRS — Common Reporting Standard"),
            ("dac_directivas", "Directivas DAC (DAC1-DAC11)"),
            ("w8_formularios", "Formularios W-8 (W-8BEN, W-8BEN-E, W-8EXP)"),
            ("giin_ffn", "GIIN — Global Intermediary Identification Number"),
            ("intracomunitario_ue", "Operaciones Intracomunitarias UE"),
        ]
        for slug, etiqueta in materias:
            cur.execute(
                """INSERT INTO materia (slug, etiqueta)
                   VALUES (%s, %s)
                   ON CONFLICT (slug) DO NOTHING""",
                (slug, etiqueta),
            )

        conn.commit()
        print(f"OK: {len(materias)} materias internacionales insertadas")

        conn.close()

if __name__ == "__main__":
    main()
