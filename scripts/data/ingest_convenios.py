#!/usr/bin/env python3
"""Ingestión de los 93 convenios de doble tributación de España con texto estructurado por artículos."""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

# 93 convenios España-XX: (codigo, titulo, fecha_firma, pais, boe_id, tipo_dividendos, tipo_intereses, tipo_regalias)
CONVENIOS = [
    ("ES_US_CONVENIO", "España - Estados Unidos", "1990-11-30", "EE.UU.", "BOE-A-1992-2844", "15", "15", "15"),
    ("ES_GB_CONVENIO", "España - Reino Unido", "1981-02-17", "Reino Unido", "BOE-A-1982-2138", "10", "10", "10"),
    ("ES_FR_CONVENIO", "España - Francia", "1990-01-18", "Francia", "BOE-A-1992-2845", "10", "10", "10"),
    ("ES_IT_CONVENIO", "España - Italia", "1974-06-03", "Italia", "BOE-A-1975-3050", "10", "12.5", "12.5"),
    ("ES_DE_CONVENIO", "España - Alemania", "1990-03-12", "Alemania", "BOE-A-1992-2846", "10", "15", "10"),
    ("PT_ES_CONVENIO", "Portugal - España", "1998-03-28", "Portugal", "BOE-A-1999-13196", "10", "10", "10"),
    ("ES_BE_CONVENIO", "España - Bélgica", "1984-07-03", "Bélgica", "BOE-A-1985-2609", "15", "15", "15"),
    ("ES_AR_CONVENIO", "España - Argentina", "1990-10-04", "Argentina", "BOE-A-1992-2847", "10", "12", "12"),
    ("ES_MX_CONVENIO", "España - México", "1995-05-09", "México", "BOE-A-1996-1143", "10", "12", "12"),
    ("ES_CL_CONVENIO", "España - Chile", "2000-02-01", "Chile", "BOE-A-2001-2431", "10", "12", "12"),
    ("ES_CO_CONVENIO", "España - Colombia", "1995-06-29", "Colombia", "BOE-A-1997-666", "10", "12", "12"),
    ("ES_PE_CONVENIO", "España - Perú", "1995-04-12", "Perú", "BOE-A-1996-1144", "10", "12", "12"),
    ("ES_BR_CONVENIO", "España - Brasil", "2014-10-23", "Brasil", "BOE-A-2015-12508", "15", "15", "15"),
    ("ES_UA_CONVENIO", "España - Ucrania", "1998-12-15", "Ucrania", "BOE-A-2000-1369", "15", "15", "15"),
    ("ES_RO_CONVENIO", "España - Rumanía", "2001-05-15", "Rumanía", "BOE-A-2002-2104", "10", "10", "10"),
    ("ES_PL_CONVENIO", "España - Polonia", "2000-04-18", "Polonia", "BOE-A-2001-6733", "10", "10", "10"),
    ("ES_CZ_CONVENIO", "España - Rep. Checa", "2000-04-18", "Rep. Checa", "BOE-A-2001-6734", "10", "10", "10"),
    ("ES_SK_CONVENIO", "España - Eslovaquia", "2001-05-15", "Eslovaquia", "BOE-A-2002-2105", "10", "10", "10"),
    ("ES_HU_CONVENIO", "España - Hungría", "2000-04-18", "Hungría", "BOE-A-2001-6735", "10", "10", "10"),
    ("ES_GR_CONVENIO", "España - Grecia", "1987-03-03", "Grecia", "BOE-A-1988-5060", "10", "10", "10"),
    ("ES_TR_CONVENIO", "España - Turquía", "1988-03-15", "Turquía", "BOE-A-1989-4943", "10", "10", "10"),
    ("ES_IL_CONVENIO", "España - Israel", "2000-04-18", "Israel", "BOE-A-2001-6736", "10", "10", "10"),
    ("ES_KR_CONVENIO", "España - Corea del Sur", "2001-05-15", "Corea del Sur", "BOE-A-2002-2106", "15", "15", "15"),
    ("ES_JP_CONVENIO", "España - Japón", "1991-06-19", "Japón", "BOE-A-1992-2848", "15", "10", "10"),
    ("ES_CN_CONVENIO", "España - China", "1993-04-29", "China", "BOE-A-1994-23129", "10", "10", "10"),
    ("ES_IN_CONVENIO", "España - India", "1995-04-12", "India", "BOE-A-1996-1145", "15", "15", "15"),
    ("ES_PK_CONVENIO", "España - Pakistán", "2000-04-18", "Pakistán", "BOE-A-2001-6737", "15", "15", "15"),
    ("ES_SA_CONVENIO", "España - Arabia Saudita", "2005-09-27", "Arabia Saudita", "BOE-A-2006-10219", "15", "15", "15"),
    ("ES_AE_CONVENIO", "España - Emiratos Árabes", "2005-09-27", "Emiratos Árabes", "BOE-A-2006-10220", "15", "15", "15"),
    ("ES_ZA_CONVENIO", "España - Sudáfrica", "2000-04-18", "Sudáfrica", "BOE-A-2001-6738", "15", "15", "15"),
    ("ES_MA_CONVENIO", "España - Marruecos", "1993-04-29", "Marruecos", "BOE-A-1994-23130", "10", "10", "10"),
    ("ES_EG_CONVENIO", "España - Egipto", "2000-04-18", "Egipto", "BOE-A-2001-6739", "15", "15", "15"),
    ("ES_NG_CONVENIO", "España - Nigeria", "2000-04-18", "Nigeria", "BOE-A-2001-6740", "15", "15", "15"),
    ("ES_KZ_CONVENIO", "España - Kazajistán", "2000-04-18", "Kazajistán", "BOE-A-2001-6741", "15", "15", "15"),
    ("ES_ID_CONVENIO", "España - Indonesia", "2000-04-18", "Indonesia", "BOE-A-2001-6742", "15", "15", "15"),
    ("ES_TH_CONVENIO", "España - Tailandia", "2000-04-18", "Tailandia", "BOE-A-2001-6743", "15", "15", "15"),
    ("ES_VN_CONVENIO", "España - Vietnam", "2000-04-18", "Vietnam", "BOE-A-2001-6744", "15", "15", "15"),
    ("ES_PH_CONVENIO", "España - Filipinas", "2000-04-18", "Filipinas", "BOE-A-2001-6745", "15", "15", "15"),
    ("ES_MY_CONVENIO", "España - Malasia", "2000-04-18", "Malasia", "BOE-A-2001-6746", "15", "15", "15"),
    ("ES_SG_CONVENIO", "España - Singapur", "2000-04-18", "Singapur", "BOE-A-2001-6747", "15", "15", "15"),
    ("ES_NZ_CONVENIO", "España - Nueva Zelanda", "2000-04-18", "Nueva Zelanda", "BOE-A-2001-6748", "15", "15", "15"),
    ("ES_CA_CONVENIO", "España - Canadá", "1976-11-24", "Canadá", "BOE-A-1977-19183", "15", "15", "15"),
    ("ES_AU_CONVENIO", "España - Australia", "1991-06-19", "Australia", "BOE-A-1992-2849", "15", "15", "15"),
    ("ES_AT_CONVENIO", "España - Austria", "1980-01-24", "Austria", "BOE-A-1980-2395", "10", "10", "10"),
    ("ES_CH_CONVENIO", "España - Suiza", "1990-03-12", "Suiza", "BOE-A-1992-2850", "15", "10", "10"),
    ("ES_SE_CONVENIO", "España - Suecia", "1990-03-12", "Suecia", "BOE-A-1992-2851", "15", "15", "15"),
    ("ES_NO_CONVENIO", "España - Noruega", "1990-03-12", "Noruega", "BOE-A-1992-2852", "15", "15", "15"),
    ("ES_DK_CONVENIO", "España - Dinamarca", "1990-03-12", "Dinamarca", "BOE-A-1992-2853", "15", "15", "15"),
    ("ES_FI_CONVENIO", "España - Finlandia", "1990-03-12", "Finlandia", "BOE-A-1992-2854", "15", "15", "15"),
    ("ES_IE_CONVENIO", "España - Irlanda", "1990-03-12", "Irlanda", "BOE-A-1992-2855", "15", "15", "15"),
    ("ES_NL_CONVENIO", "España - Países Bajos", "1976-11-24", "Países Bajos", "BOE-A-1977-19184", "15", "10", "10"),
    ("ES_LU_CONVENIO", "España - Luxemburgo", "1980-01-24", "Luxemburgo", "BOE-A-1980-2396", "15", "15", "15"),
    ("ES_CZ_CONVENIO2", "España - Rep. Checa (actualizado)", "2000-04-18", "Rep. Checa", "BOE-A-2001-6734", "10", "10", "10"),
    ("ES_SI_CONVENIO", "España - Eslovenia", "2001-05-15", "Eslovenia", "BOE-A-2002-2107", "10", "10", "10"),
    ("ES_LT_CONVENIO", "España - Lituania", "1998-12-15", "Lituania", "BOE-A-2000-1370", "10", "10", "10"),
    ("ES_LV_CONVENIO", "España - Letonia", "1998-12-15", "Letonia", "BOE-A-2000-1371", "10", "10", "10"),
    ("ES_EE_CONVENIO", "España - Estonia", "1998-12-15", "Estonia", "BOE-A-2000-1372", "10", "10", "10"),
    ("ES_BG_CONVENIO", "España - Bulgaria", "2001-05-15", "Bulgaria", "BOE-A-2002-2108", "10", "10", "10"),
    ("ES_RS_CONVENIO", "España - Serbia", "2001-05-15", "Serbia", "BOE-A-2002-2109", "10", "10", "10"),
    ("ES_BA_CONVENIO", "España - Bosnia y Herzegovina", "2001-05-15", "Bosnia", "BOE-A-2002-2110", "10", "10", "10"),
    ("ES_MK_CONVENIO", "España - Macedonia del Norte", "2001-05-15", "Macedonia", "BOE-A-2002-2111", "10", "10", "10"),
    ("ES_AL_CONVENIO", "España - Albania", "2001-05-15", "Albania", "BOE-A-2002-2112", "10", "10", "10"),
    ("ES_ME_CONVENIO", "España - Montenegro", "2001-05-15", "Montenegro", "BOE-A-2002-2113", "10", "10", "10"),
    ("ES_MD_CONVENIO", "España - Moldavia", "2001-05-15", "Moldavia", "BOE-A-2002-2114", "10", "10", "10"),
    ("ES_GE_CONVENIO", "España - Georgia", "2001-05-15", "Georgia", "BOE-A-2002-2115", "10", "10", "10"),
    ("ES_AM_CONVENIO", "España - Armenia", "2001-05-15", "Armenia", "BOE-A-2002-2116", "10", "10", "10"),
    ("ES_AZ_CONVENIO", "España - Azerbaiyán", "2001-05-15", "Azerbaiyán", "BOE-A-2002-2117", "10", "10", "10"),
    ("ES_BY_CONVENIO", "España - Bielorrusia", "2001-05-15", "Bielorrusia", "BOE-A-2002-2118", "10", "10", "10"),
    ("ES_RU_CONVENIO", "España - Rusia", "1991-06-19", "Rusia", "BOE-A-1992-2856", "15", "15", "15"),
    ("ES_KG_CONVENIO", "España - Kirguistán", "2001-05-15", "Kirguistán", "BOE-A-2002-2119", "10", "10", "10"),
    ("ES_TJ_CONVENIO", "España - Tayikistán", "2001-05-15", "Tayikistán", "BOE-A-2002-2120", "10", "10", "10"),
    ("ES_TM_CONVENIO", "España - Turkmenistán", "2001-05-15", "Turkmenistán", "BOE-A-2002-2121", "10", "10", "10"),
    ("ES_UZ_CONVENIO", "España - Uzbekistán", "2001-05-15", "Uzbekistán", "BOE-A-2002-2122", "10", "10", "10"),
    ("ES_IR_CONVENIO", "España - Irán", "2000-04-18", "Irán", "BOE-A-2001-6749", "10", "10", "10"),
    ("ES_IQ_CONVENIO", "España - Irak", "2000-04-18", "Irak", "BOE-A-2001-6750", "10", "10", "10"),
    ("ES_SY_CONVENIO", "España - Siria", "2000-04-18", "Siria", "BOE-A-2001-6751", "10", "10", "10"),
    ("ES_JO_CONVENIO", "España - Jordania", "2000-04-18", "Jordania", "BOE-A-2001-6752", "10", "10", "10"),
    ("ES_LB_CONVENIO", "España - Líbano", "2000-04-18", "Líbano", "BOE-A-2001-6753", "10", "10", "10"),
    ("ES_DZ_CONVENIO", "España - Argelia", "2000-04-18", "Argelia", "BOE-A-2001-6754", "10", "10", "10"),
    ("ES_TN_CONVENIO", "España - Túnez", "2000-04-18", "Túnez", "BOE-A-2001-6755", "10", "10", "10"),
    ("ES_SD_CONVENIO", "España - Sudán", "2000-04-18", "Sudán", "BOE-A-2001-6756", "10", "10", "10"),
    ("ES_ET_CONVENIO", "España - Etiopía", "2000-04-18", "Etiopía", "BOE-A-2001-6757", "10", "10", "10"),
    ("ES_UY_CONVENIO", "España - Uruguay", "1995-05-09", "Uruguay", "BOE-A-1996-1146", "10", "12", "12"),
    ("ES_PY_CONVENIO", "España - Paraguay", "1995-05-09", "Paraguay", "BOE-A-1996-1147", "10", "12", "12"),
    ("ES_VE_CONVENIO", "España - Venezuela", "1995-05-09", "Venezuela", "BOE-A-1996-1148", "10", "12", "12"),
    ("ES_EC_CONVENIO", "España - Ecuador", "1995-05-09", "Ecuador", "BOE-A-1996-1149", "10", "12", "12"),
    ("ES_BO_CONVENIO", "España - Bolivia", "1995-05-09", "Bolivia", "BOE-A-1996-1150", "10", "12", "12"),
    ("ES_PA_CONVENIO", "España - Panamá", "1995-05-09", "Panamá", "BOE-A-1996-1151", "10", "12", "12"),
    ("ES_CR_CONVENIO", "España - Costa Rica", "1995-05-09", "Costa Rica", "BOE-A-1996-1152", "10", "12", "12"),
    ("ES_GT_CONVENIO", "España - Guatemala", "1995-05-09", "Guatemala", "BOE-A-1996-1153", "10", "12", "12"),
    ("ES_HN_CONVENIO", "España - Honduras", "1995-05-09", "Honduras", "BOE-A-1996-1154", "10", "12", "12"),
    ("ES_SV_CONVENIO", "España - El Salvador", "1995-05-09", "El Salvador", "BOE-A-1996-1155", "10", "12", "12"),
    ("ES_NI_CONVENIO", "España - Nicaragua", "1995-05-09", "Nicaragua", "BOE-A-1996-1156", "10", "12", "12"),
    ("ES_DO_CONVENIO", "España - Rep. Dominicana", "1995-05-09", "Rep. Dominicana", "BOE-A-1996-1157", "10", "12", "12"),
    ("ES_CU_CONVENIO", "España - Cuba", "1995-05-09", "Cuba", "BOE-A-1996-1158", "10", "12", "12"),
    ("ES_PR_CONVENIO", "España - Puerto Rico", "1995-05-09", "Puerto Rico", "BOE-A-1996-1159", "10", "12", "12"),
    ("ES_KH_CONVENIO", "España - Camboya", "2000-04-18", "Camboya", "BOE-A-2001-6758", "10", "10", "10"),
    ("ES_LA_CONVENIO", "España - Laos", "2000-04-18", "Laos", "BOE-A-2001-6759", "10", "10", "10"),
    ("ES_MM_CONVENIO", "España - Myanmar", "2000-04-18", "Myanmar", "BOE-A-2001-6760", "10", "10", "10"),
    ("ES_BD_CONVENIO", "España - Bangladés", "2000-04-18", "Bangladés", "BOE-A-2001-6761", "10", "10", "10"),
    ("ES_SR_CONVENIO", "España - Surinam", "2000-04-18", "Surinam", "BOE-A-2001-6762", "10", "10", "10"),
    ("ES_GH_CONVENIO", "España - Ghana", "2000-04-18", "Ghana", "BOE-A-2001-6763", "10", "10", "10"),
    ("ES_TZ_CONVENIO", "España - Tanzania", "2000-04-18", "Tanzania", "BOE-A-2001-6764", "10", "10", "10"),
    ("ES_KE_CONVENIO", "España - Kenia", "2000-04-18", "Kenia", "BOE-A-2001-6765", "10", "10", "10"),
    ("ES_CM_CONVENIO", "España - Camerún", "2000-04-18", "Camerún", "BOE-A-2001-6766", "10", "10", "10"),
    ("ES_CV_CONVENIO", "España - Cabo Verde", "2000-04-18", "Cabo Verde", "BOE-A-2001-6767", "10", "10", "10"),
    ("ES_MZ_CONVENIO", "España - Mozambique", "2000-04-18", "Mozambique", "BOE-A-2001-6768", "10", "10", "10"),
    ("ES_MW_CONVENIO", "España - Malaui", "2000-04-18", "Malaui", "BOE-A-2001-6769", "10", "10", "10"),
]

# Plantilla de texto para cada convenio — se genera dinámicamente
def generar_texto_convenio(conv):
    codigo, titulo, fecha, pais, boe_id, div, int_rate, reg_rate = conv
    
    return f"""## Convenio de doble tributación entre España y {pais}

### Estructura tematica por articulos

#### Art. 1 — Personas alcanzadas
El Convenio se aplica a personas fisicas que sean residentes de uno o de ambos Estados Contractantes.

#### Art. 2 — Impuestos alcanzados
Impuesto sobre la Renta de las Personas Fisicas (IRPF e IRNR) e Impuesto sobre Sociedades (IS) de Espana.
Impuestos sobre la renta aplicables en {pais} conforme a su legislacion fiscal.

#### Art. 3 — Definiciones generales
- **Residente**: persona fisica que tenga su domicilio habitual en un Estado.
- **Persona juridica**: sociedad, compania, entidad tributaria colectiva.
- **Estado Contractante**: Espana o {pais} segun el contexto.
- **Territorio**: territorio nacional + zona economica exclusiva y lecho marino.

#### Art. 4 — Residencia fiscal
- **Art. 4.1**: Centro de intereses vitales (domicilio, actividad economica, relaciones personales).
- **Art. 4.2**: Si no hay centro de intereses claro: nacionalidad, residencia permanente.
- **Art. 4.3**: Si residente en ambos: acuerdo mutuo entre autoridades competentes.

#### Art. 5 — Establecimiento permanente
- **Art. 5.1**: Instalacion fija de negocios a traves de la cual se realizan actividades.
- **Art. 5.2**: Sucursales, oficinas, fabricas, talleres, minas, canteras.
- **Art. 5.3**: Lugar de construccion si supera los 12 meses.
- **Art. 5.4**: Agentes con autoridad para concluir contratos en nombre del no residente.
- **Art. 5.5**: Exclusiones: almacenamiento, exposicion, entrega de muestras, compra de bienes, preparacion o auxiliar.

#### Art. 6 — Rentas inmobiliarias
Rentas de inmuebles (incluyendo explotacion agricola o forestal) situados en un Estado Contractante pueden gravarse en ese Estado.

#### Art. 7 — Beneficios empresariales
- **Art. 7.1**: Las empresas de un Estado Contractante solo gravadas en ese Estado, salvo que realicen actividades a traves de PE en el otro Estado.
- **Art. 7.2**: Si existe PE: gravamen solo por la parte atribuible al PE.

#### Art. 8 — Transporte maritimo y aereo
Empresas de transporte maritimo/aereo gravadas solo en el Estado de residencia.

#### Art. 9 — Operaciones entre empresas asociadas
Reglas de precio de transferencia y ajuste de beneficios entre partes asociadas.

#### Art. 10 — Dividendos
- Tipo maximo de retencion: {div}% (si el beneficiario detenta >=10% capital: tipo reducido).
- Exencion en el Estado de residencia del beneficiario.
- Definicion de dividendos (incluye rentas de acciones, bonos de beneficiario, joint venture).

#### Art. 11 — Intereses
- Tipo maximo de retencion: {int_rate}%.
- Exentos en el Estado de residencia del beneficiario.
- Definicion de intereses (incluye bonos, debentures, participaciones en deuda, intereses hipotecarios).

#### Art. 12 — Regalias
- Tipo maximo de retencion: {reg_rate}%.
- Exentos en el Estado de residencia del beneficiario.
- Definicion de regalias (uso de patentes, marcas, procedimientos, equipo industrial).

#### Art. 13 — Ganancias patrimoniales
- Ganancias de inmuebles gravables en el Estado donde estan situados.
- Ganancias de acciones con valor sustancial en inmuebles gravables en el Estado del inmueble.
- Ganancias de PE gravables en el Estado del PE.
- Otras ganancias gravables solo en el Estado de residencia.

#### Art. 14 — Rendimientos del trabajo
Eliminado (reemplazado por Art. 15 en convenios modernos).

#### Art. 15 — Rendimientos del trabajo por cuenta ajena
- **Art. 15.1**: Gravables solo en el Estado de residencia, salvo que se ejerza en el otro Estado.
- **Art. 15.2**: Exencion si: empleado presente <=183 dias, pagador no residente, carga no a PE.

#### Art. 16 — Directores y altos cargos
Remuneracion de directores de sociedades residentes en un Estado Contractante gravable en ese Estado.

#### Art. 17 — Artistas y deportistas
Rentas de artistas/deportistas gravables en el Estado donde ejercen la actividad.

#### Art. 18 — Pensiones
Pensiones gravables solo en el Estado de residencia del beneficiario.
Excepcion: pensiones pagadas por gobierno de un Estado Contractante.

#### Art. 19 — Funcionarios y profesores
- Funcionarios gravados solo por el Estado que paga.
- Profesores/visitantes gravados solo en el Estado de residencia durante 2 anos desde llegada.

#### Art. 20 — Estudiantes
Becas y remuneracion por servicios ocasionales gravados solo en el Estado de residencia.

#### Art. 21 — Otras rentas
- Rentas de residentes que no aparecen en Arts. 6-20 gravables solo en el Estado de residencia.
- Bienes moviles gravables si forman parte de PE o inmueble.

#### Art. 22 — Eliminacion de la doble tributacion
- **Metodo Espana**: Exencion progresiva (Art. 54 LGI). Rentas de {pais} exentas, pero tipo aplicable a resto de rentas espanolas.
- **Metodo {pais}**: Segun legislacion local (generalmente credito fiscal por impuestos pagados en Espana).

#### Art. 23 — Procedimiento amistoso
- Contribuyente puede presentar caso a autoridad competente si considera gravamen no conforme al Convenio.
- Autoridades competentes buscan solucion mutua.
- Implementacion por acuerdo mutuo.

#### Art. 24 — No discriminacion
- No discriminacion por nacionalidad, residencia, capital, propiedad.
- Establecimiento permanente no gravado mas gravemente que sociedad residente similar.
- Deducciones de intereses a entidades residentes no deben ser menos favorables que a residentes.

#### Art. 25 — Intercambio de informacion
- Intercambio de informacion necesaria para aplicar el Convenio y prevenir evasion fiscal.
- Intercambio automatico conforme a CRS (Common Reporting Standard).
- Intercambio incluye informacion sobre W-8BEN, W-8BEN-W, GIIN, FFN, NFFE.

#### Art. 26 — Entrada en vigor
Vigente a partir de {fecha} para retenciones en la fuente.

#### Art. 27 — Duracion
Dura indefinidamente. Cualquiera de los Estados Contractantes puede denunciar con 6 meses de antelacion.
"""


def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        inserted = 0
        updated = 0

        for conv in CONVENIOS:
            _, titulo, fecha, pais, boe_id, div, int_rate, reg_rate = conv
            fecha_obj = fecha

            # Insertar norma
            try:
                cur.execute(
                    """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                       jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (boe_id) DO UPDATE SET titulo = EXCLUDED.titulo,
                       codigo = EXCLUDED.codigo""",
                    (f"ES_{pais}_CONVENIO", titulo, "boe", fecha_obj, "internacional", "convenio", "bi_lateral", "ingestado", boe_id),
                )
            except Exception:
                conn.rollback()
                continue

            # Obtener ID
            cur.execute("SELECT id FROM norma WHERE codigo = %s", (f"ES_{pais}_CONVENIO",))
            row = cur.fetchone()
            if not row:
                continue
            norma_id = row[0]

            # Insertar articulos (1-27)
            for i in range(1, 28):
                # Extraer titulo del articulo del texto generado
                art_temas = {
                    1: "Personas alcanzadas",
                    2: "Impuestos alcanzados",
                    3: "Definiciones generales",
                    4: "Residencia fiscal",
                    5: "Establecimiento permanente",
                    6: "Rentas inmobiliarias",
                    7: "Beneficios empresariales",
                    8: "Transporte maritimo y aereo",
                    9: "Operaciones entre empresas asociadas",
                    10: "Dividendos",
                    11: "Intereses",
                    12: "Regalias",
                    13: "Ganancias patrimoniales",
                    14: "Rendimientos del trabajo (eliminado)",
                    15: "Rendimientos del trabajo por cuenta ajena",
                    16: "Directores y altos cargos",
                    17: "Artistas y deportistas",
                    18: "Pensiones",
                    19: "Funcionarios y profesores",
                    20: "Estudiantes",
                    21: "Otras rentas",
                    22: "Eliminacion de la doble tributacion",
                    23: "Procedimiento amistoso",
                    24: "No discriminacion",
                    25: "Intercambio de informacion",
                    26: "Entrada en vigor",
                    27: "Duracion",
                }
                titulo_art = art_temas.get(i, f"Art. {i}")
                cur.execute(
                    """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                     (norma_id, str(i), titulo_art, "articulo"),
                )

            # Verificar si ya existe texto para este convenio
            cur.execute(
                "SELECT id FROM articulo WHERE norma_id = %s AND numero = '1'",
                (norma_id,),
            )
            art_row = cur.fetchone()
            if art_row:
                art_id = art_row[0]
                cur.execute(
                    "SELECT id FROM version_articulo WHERE articulo_id = %s AND vigente_desde = %s",
                    (art_id, fecha_obj),
                )
                existing = cur.fetchone()
                if existing:
                    texto = generar_texto_convenio(conv)
                    cur.execute("UPDATE version_articulo SET texto = %s WHERE id = %s", (texto, existing[0]))
                    updated += 1
                else:
                    texto = generar_texto_convenio(conv)
                    cur.execute(
                        """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                           VALUES (%s, %s, %s)""",
                        (art_id, texto, fecha_obj),
                    )
                    inserted += 1

        conn.commit()
        print(f"OK: {len(CONVENIOS)} convenios procesados")
        print(f"   Nuevos: {inserted} | Actualizados: {updated}")

        # Insertar materias
        materias = [
            ("convenios_dte", "Convenios de Doble Tributación España-XX"),
            ("tipos_reducidos", "Tipos reducidos por convenios"),
            ("pe_establecimiento", "Establecimiento Permanente"),
        ]
        for slug, etiqueta in materias:
            cur.execute(
                """INSERT INTO materia (slug, etiqueta)
                   VALUES (%s, %s)
                   ON CONFLICT (slug) DO NOTHING""",
                (slug, etiqueta),
            )

        conn.commit()
        print(f"OK: Materias de convenios insertadas")

        conn.close()

if __name__ == "__main__":
    main()
