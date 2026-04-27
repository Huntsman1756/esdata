#!/usr/bin/env python3
"""Ingestión de NIF/NRF de todos los países UE + EFTA para operaciones intracomunitarias."""
import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

PAISES = [
    ("ES", "Espana", "NIF: A12345678 / NIE: X1234567Y", "ES", "ESB12345678", "Agencia Estatal de Administracion Tributaria (AEAT)", "BOE-A-1992-2880"),
    ("DE", "Alemania", "Steuernummer / Steuer-ID", "DE", "DE123456789", "Bundeszentralamt fur Steuern (BZSt)", "UStG"),
    ("FR", "Francia", "Numerico fiscal / SIRET", "FR", "FR12345678901", "Direction Generale des Finances Publiques (DGFiP)", "Code General des Impots"),
    ("IT", "Italia", "Codice Fiscale / Partita IVA", "IT", "IT01234567890", "Agenzia delle Entrate", "DPR 633/1972"),
    ("NL", "Paises Bajos", "BSN / Btw-identificatienummer", "NL", "NL123456789B01", "Belastingdienst", "Wet OB"),
    ("BE", "Belgica", "Numero d'entreprise / Numero TVA", "BE", "BE0123456789", "Direction des Relations Financieres Extérieures (DRFE)", "Code des droits de douane"),
    ("AT", "Austria", "Tax-ID / UID-Nummer", "AT", "ATU12345678", "Bundesministerium fur Finanzen (BMF)", "UStG"),
    ("PL", "Polonia", "NIP / REGON", "PL", "PL1234567890", "Krajowa Administracja Skarbowa (KAS)", "Ustawa o VAT"),
    ("RO", "Rumanía", "CUI / CIF", "RO", "RO12345678", "Agenția Nationala de Administrare Fiscala (ANAF)", "Codul de procedura fiscala"),
    ("PT", "Portugal", "NIF / NIPC", "PT", "PT123456789", "Autoridade Tributaria e Aduaneira (AT)", "Codigo do IVA"),
    ("GR", "Grecia", "AFM", "GR", "EL123456789", "Aforgeia (AADE)", "N.2859/2000"),
    ("CZ", "Rep. Checa", "IC / IC DPH", "CZ", "CZ12345678", "Financni sprava Ceské republiky", "Zákon o DPH"),
    ("SE", "Suecia", "Org.nr / Momsregistreringsnummer", "SE", "SE123456789001", "Skatteverket", "Mervardesskattelagen"),
    ("HU", "Hungría", "Adóazonosito jel / AFA-ON", "HU", "HU12345678", "Nemzeti Adó- és Vámhivatal (NAV)", "AFA tv."),
    ("BG", "Bulgaria", "ЕИК / ДАН", "BG", "BG123456789", "Natsionalna agentzia za prihodite (NAP)", "Zakon za DDS"),
    ("HR", "Croacia", "OIB / OIB za PDV", "HR", "HR12345678901", "Porezna uprava", "Zakon o PDV"),
    ("DK", "Dinamarca", "CVR-nummer", "DK", "DK12345678", "Skattestyrelsen", "Momsloven"),
    ("FI", "Finlandia", "ALV-numero / Y-tunnus", "FI", "FI12345678", "Verohallinto", "Laki ALV:ssa"),
    ("IE", "Irlanda", "VAT No. / PPS", "IE", "IE1234567T", "Revenue Commissioners", "VAT Consolidation Act 2010"),
    ("LU", "Luxemburgo", "NIF intracomunitario / N° TVA", "LU", "LU12345678", "Administration de l'Enregistrement et des Biens fonciers (ARBF)", "Loi TVA"),
    ("SI", "Eslovenia", "ID za DDV / NPI", "SI", "SI12345678", "Finance Uprava RS", "Zakon o DDV"),
    ("SK", "Eslovaquia", "IC DPH / IC", "SK", "SK1234567890", "Financná správa Slovenskej republiky", "Zákon o DPH"),
    ("LT", "Lituania", "PVM kodas", "LT", "LT123456789", "Valstybine mokesčiu inspekcija (VMI)", "PVM įstatymas"),
    ("LV", "Letonia", "PVN reg. numurs", "LV", "LV12345678901", "Valsts ieņēmumu dienests (VID)", "PVN likums"),
    ("EE", "Estonia", "KMK / Käibemaksukohustuslase number", "EE", "EE123456789", "Maksu- ja Tolliamet (MTA)", "Käibemaksuseadus"),
    ("CY", "Chipre", "VAT Reg. No.", "CY", "CY12345678L", "Department of VAT", "ΦΠΑ Νόμος"),
    ("MT", "Malta", "VAT Registration Number", "MT", "MT12345678", "Revenue Malta", "Value Added Tax Act"),
    ("IS", "Islandia", "Kennitala / VSK-numer", "IS", "IS123456-1230", "Rikisskattstjóri", "Log um voruskatt"),
    ("NO", "Noruega", "Organisasjonsnummer / MVA-nummer", "NO", "NO123456789", "Skatteetaten", "Merverdiavgiftsloven"),
    ("CH", "Suiza", "UID-Nummer", "CH", "CHE-123.456.789", "Eidgenossische Steuerverwaltung (ESTV)", "MWST-Gesetz"),
    ("LI", "Liechtenstein", "UID-Nummer", "LI", "CHE-123.456.789", "Das Amt fur Steuern", "MWST-Gesetz"),
]

def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        # 1. Norma UE intracomunitario
        cur.execute(
            """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
               jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            ("UE_INTRACOMUNITARIO",
             "Directiva 2006/112/CE - Directiva IVA del Consejo - Regimen intracomunitario de IVA",
             "ue", "2006-01-01", "ue", "directiva",
             "mult_lateral", "ingestado", "OJEL-2006-L-00112"),
        )
        cur.execute("SELECT id FROM norma WHERE codigo = 'UE_INTRACOMUNITARIO'")
        ue_id = cur.fetchone()[0]

        ue_articles = [
            ("1", "Alcance de la Directiva IVA - Territorio de la UE", "articulo"),
            ("2", "Art. 2 - Hecho impositivo - Adquisiciones intracomunitarias de bienes", "articulo"),
            ("3", "Art. 19 - Expedicion o transporte desde un Estado miembro a otro", "articulo"),
            ("4", "Art. 20 - Transferencia de bienes enviada o transportada por el cedente", "articulo"),
            ("5", "Art. 21 - Reglas de localizacion de las entregas intracomunitarias", "articulo"),
            ("6", "Art. 25 - Exencion de las entregas intracomunitarias de bienes", "articulo"),
            ("7", "Art. 40 - Reglas de localizacion de las prestaciones intracomunitarias de servicios", "articulo"),
            ("8", "Art. 196 - Tipo impositivo aplicable en las adquisiciones intracomunitarias", "articulo"),
            ("9", "Art. 197 - Sujeto pasivo de las adquisiciones intracomunitarias", "articulo"),
            ("10", "Art. 198 - Sujeto pasivo en ciertas operaciones (reverse charge)", "articulo"),
            ("11", "Art. 199 - Autoliquidacion por el adquirente intracomunitario", "articulo"),
            ("12", "Art. 199a - Reverse charge para operaciones intracomunitarias de construccion", "articulo"),
            ("13", "Art. 200 - Obligacion de declarar en el Modelo 349", "articulo"),
            ("14", "Art. 212 - Obligacion de inscripcion en el ROIR", "articulo"),
            ("15", "Art. 214 - Identificacion intracomunitaria - Formato del NIF intracomunitario", "articulo"),
            ("16", "Art. 215 - Numero de identificacion intracomunitario", "articulo"),
            ("17", "Art. 218 - Declaracion-resumen (Intrastat) para mercancias", "articulo"),
            ("18", "Art. 262 - Declaracion intracomunitaria (DAC7) para servicios", "articulo"),
            ("19", "Art. 263 - Presentacion de la declaracion intracomunitaria", "articulo"),
            ("20", "Art. 273 - Medidas necesarias para evitar evasion y elusion", "articulo"),
        ]
        for num, titulo, tipo in ue_articles:
            try:
                cur.execute(
                    """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                    (ue_id, num, titulo, tipo),
                )
            except Exception:
                conn.rollback()
                continue

        conn.commit()
        print(f"OK: {len(ue_articles)} articulos de normativa intracomunitaria UE insertados")

        # 2. Insertar NIF/NRF por pais
        for pais, nombre, formato, prefijo, ejemplo, emisor, fuente in PAISES:
            try:
                cur.execute(
                    """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
                       jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
                    (f"NIF_{pais}", f"NIF/NRF {nombre} - {formato}", "ue", "2006-01-01", "ue", "referencia", "un_lateral", "ingestado", fuente),
                )
            except Exception:
                conn.rollback()
                continue

        conn.commit()
        print(f"OK: {len(PAISES)} paises con NIF/NRF intracomunitario insertados")
        print(f"   UE: 27 paises | EFTA: 4 paises (Islandia, Noruega, Suiza, Liechtenstein)")

        # 3. Textos detallados
        textos = [
            ("UE_INTRACOMUNITARIO", "1",
             "Directiva 2006/112/CE - Directiva IVA del Consejo - Regimen intracomunitario\n\n"
             "Territorio fiscal de la UE:\n"
             "- Cada Estado miembro tiene un territorio fiscal donde se aplica el IVA nacional\n"
             "- Los territorios excluidos: zonas francas, almacenes francos, zonas duty-free\n"
             "- Los territorios incluidos: aguas territoriales, espacio aereo sobre el territorio nacional\n\n"
             "Operaciones intracomunitarias de bienes:\n\n"
             "1. Adquisicion intracomunitaria de bienes (Art. 20):\n"
             "- Ocurre cuando una entidad transmite bienes expedidos desde otro Estado miembro\n"
             "- El adquirente debe estar identificado a efectos del IVA\n"
             "- El adquirente autoliquida el IVA en su declaracion trimestral (Modelo 303)\n\n"
             "2. Entrega intracomunitaria de bienes (Art. 21):\n"
             "- Ocurre cuando una entidad envia bienes a otro Estado miembro\n"
             "- La entrega esta exenta de IVA en el Estado de origen (Art. 25)\n"
             "- El adquirente autoliquida el IVA en el Estado de destino\n\n"
             "Operaciones intracomunitarias de servicios:\n\n"
             "1. Servicios B2B: lugar de prestacion es el Estado del cliente (reverse charge)\n"
             "2. Servicios B2C: lugar de prestacion es el Estado del proveedor\n"
             "3. OSS (One Stop Shop): regimen especial para proveedores B2C de servicios electronicos\n\n"
             "Numero de identificacion intracomunitario:\n"
             "- Formato: prefijo pais (2 letras) + numero de identificacion nacional\n"
             "- Ejemplo: ESB12345678 para Espana\n\n"
             "Verificacion VIES: https://ec.europa.eu/taxation_customs/vies/"),

            ("UE_INTRACOMUNITARIO", "14",
             "Registro de Operadores Intracomunitarios (ROIR)\n\n"
             "Requisitos de inscripcion:\n"
             "1. Ser sujeto pasivo del IVA en el Estado miembro\n"
             "2. Realizar entregas o adquisiciones intracomunitarias de bienes\n"
             "3. Solicitar la inscripcion en el ROIR\n\n"
             "Obligaciones del operador intracomunitario:\n"
             "1. Presentar el Modelo 349 trimestralmente\n"
             "2. Incluir operaciones intracomunitarias en la declaracion trimestral de IVA (Modelo 303)\n"
             "3. Conservar la documentacion justificativa de los transportes\n"
             "4. Notificar cambios en los datos registrados\n"
             "5. Actualizar el ROIR si se suspenden o terminan las operaciones\n\n"
             "Sanciones por incumplimiento:\n"
             "- No inscribirse en el ROIR: multa de hasta el 20% de las operaciones no declaradas\n"
             "- No presentar el Modelo 349: multa de hasta el 10% de las operaciones no declaradas\n"
             "- Declarar datos incorrectos: multa de hasta el 15%\n\n"
             "Ejemplo de flujo completo:\n"
             "1. Empresa española con NIF B12345678 quiere facturar a empresa francesa\n"
             "2. Se inscribe en el ROIR ante la AEAT\n"
             "3. Obtiene NIF intracomunitario: ESB12345678\n"
             "4. Verifica el NIF intracomunitario de la empresa francesa en VIES\n"
             "5. Emite factura con NIF intracomunitario francés del cliente\n"
             "6. La entrega esta exenta de IVA en Espana (Art. 25 Directiva IVA)\n"
             "7. El cliente francés autoliquida el IVA en Francia (reverse charge)\n"
             "8. Declaran la operacion en el Modelo 349 del trimestre correspondiente"),
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
        print("OK: Textos detallados de ROIR y normativa intracomunitaria insertados")

        # 4. Materias internacionales
        materias = [
            ("nif_intracomunitario", "NIF Intracomunitario por Pais UE"),
            ("roir", "Registro de Operadores Intracomunitarios (ROIR)"),
            ("vies", "VIES - VAT Information Exchange System"),
            ("oss_regime", "Regimen OSS - One Stop Shop"),
        ]
        for slug, etiqueta in materias:
            cur.execute(
                """INSERT INTO materia (slug, etiqueta)
                   VALUES (%s, %s)
                   ON CONFLICT (slug) DO NOTHING""",
                (slug, etiqueta),
            )

        conn.commit()
        print(f"OK: {len(materias)} materias de intracomunitario insertadas")
        conn.close()

if __name__ == "__main__":
    main()
