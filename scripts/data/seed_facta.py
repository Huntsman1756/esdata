#!/usr/bin/env python3
"""Seed de normativa FactA: artículos LIVA (entregas/adquisiciones intracomunitarias),
IRNR (no residentes), LIS (no residentes) y convenio España-EE.UU."""

import psycopg
from datetime import date

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

def main():
    with psycopg.connect(DB) as conn:
        cur = conn.cursor()

        # ---- 1. Insertar convenio España-EE.UU. como norma ----
        cur.execute(
            """INSERT INTO norma (codigo, titulo, tipo_fuente, vigente_desde,
               jurisdiccion, tipo_documento, ambito, estado_cobertura, boe_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET titulo = EXCLUDED.titulo""",
            ("ES_US_CONVENIO",
             "Convenio entre España y EE.UU. para evitar la doble tributación en materia de impuestos (firmado 1990, modificado 2017)",
             "boe",
             date(1990, 11, 30),
             "internacional",
             "convenio",
             "bi_lateral",
             "ingestada",
             "BOE-A-1992-2844")
        )

        # ---- 2. Obtener IDs de normas ----
        cur.execute(
            "SELECT codigo, id FROM norma WHERE codigo IN ('LIVA', 'IRNR', 'LIS', 'ES_US_CONVENIO')"
        )
        normas = {row[0]: row[1] for row in cur.fetchall()}

        liva_id = normas["LIVA"]
        irnr_id = normas["IRNR"]
        lis_id = normas["LIS"]
        convenio_id = normas["ES_US_CONVENIO"]

        # ---- 3. Insertar artículos LIVA: entregas/adquisiciones intracomunitarias (FactA) ----
        liva_articulos = [
            ("162", "Adquisiciones intracomunitarias de bienes", "articulo"),
            ("163", "Exenciones en las adquisiciones intracomunitarias de bienes", "articulo"),
            ("163 bis", "Entregas temporales de bienes", "articulo"),
            ("163 ter", "Operaciones intracomunitarias de transporte", "articulo"),
            ("163 quater", "Régimen especial de las cadenas de operaciones", "articulo"),
            ("163 quinques", "Operaciones intracomunitarias de servicios", "articulo"),
            ("163 sex", "Entregas de bienes y prestaciones de servicios a no residentes no sujetos pasivos", "articulo"),
            ("163 sept", "Servicios de asesoramiento y consultoría a no residentes", "articulo"),
            ("163 oct", "Teletransporte y telecomunicaciones a no residentes", "articulo"),
            ("163 non", "Restaurantes y actividades hoteleras a no residentes", "articulo"),
            ("163 undec", "Alquiler de bienes a no residentes", "articulo"),
            ("163 duodec", "Servicios de intermediación a no residentes", "articulo"),
            ("172", "Entregas de bienes a operadores intracomunitarios", "articulo"),
            ("173", "Devolución del IVA a no residentes (Directiva 2008/9/CE)", "articulo"),
            ("174", "Obligaciones de facturación intracomunitaria", "articulo"),
            ("175", "Entregas intracomunitarias de bienes - definición", "articulo"),
            ("176", "Entregas intracomunitarias - exención de cuota", "articulo"),
            ("177", "Obligaciones del cedente intracomunitario", "articulo"),
            ("178", "Obligaciones del adquirente intracomunitario", "articulo"),
            ("179", "Facturas intracomunitarias - requisitos", "articulo"),
            ("180", "Operaciones intracomunitarias de servicios", "articulo"),
            ("181", "Devolución de IVA a operadores intracomunitarios", "articulo"),
            ("182", "Modelo 349 - declaración resumen de operaciones intracomunitarias", "articulo"),
            ("183", "Obligación de facturación a no residentes - Modelo 216", "articulo"),
            ("184", "Entregas de bienes a no residentes fuera de la UE", "articulo"),
            ("185", "Prestaciones de servicios a no residentes - exportación de servicios", "articulo"),
            ("186", "Facturación a no residentes - requisitos especiales", "articulo"),
            ("187", "IVA en operaciones intracomunitarias con no residentes", "articulo"),
        ]

        for numero, titulo, tipo in liva_articulos:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (liva_id, numero, titulo, tipo)
            )

        # ---- 4. Insertar artículos IRNR clave ----
        irnr_articulos = [
            ("1", "Ámbito de aplicación del IRNR", "articulo"),
            ("2", "Rendimientos del capital mobiliario - dividendos e intereses", "articulo"),
            ("3", "Rendimientos del trabajo - trabajo por cuenta ajena realizado en el exterior", "articulo"),
            ("4", "Rendimientos del capital inmobiliario - inmuebles situados en España", "articulo"),
            ("5", "Determinación directa de la base imponible", "articulo"),
            ("6", "Retenciones e ingresos a cuenta en operaciones con no residentes", "articulo"),
            ("7", "Tipos de retención del IRNR", "articulo"),
            ("8", "Convenios internacionales para evitar la doble tributación", "articulo"),
            ("9", "Obligaciones de presentación de modelos 216, 123, 124", "articulo"),
            ("10", "Devolución de retenciones a no residentes", "articulo"),
            ("11", "Documentación justificativa de residencia fiscal", "articulo"),
            ("12", "Aplicación de convenios de doble tributación", "articulo"),
        ]

        for numero, titulo, tipo in irnr_articulos:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (irnr_id, numero, titulo, tipo)
            )

        # ---- 5. Insertar artículos LIS sobre no residentes ----
        lis_articulos = [
            ("3", "Sujetos pasivos del Impuesto sobre Sociedades", "articulo"),
            ("4", "Renta obtenida en España por no residentes", "articulo"),
            ("5", "Renta obtenida a través de establecimiento permanente", "articulo"),
            ("6", "Rendimientos del capital mobiliario obtenidos por no residentes", "articulo"),
            ("7", "Ganancias y pérdidas patrimoniales obtenidas por no residentes", "articulo"),
            ("8", "Retenciones sobre rendimientos de sociedades para no residentes", "articulo"),
            ("9", "Convenios internacionales y no residentes", "articulo"),
        ]

        for numero, titulo, tipo in lis_articulos:
            cur.execute(
                """INSERT INTO articulo (norma_id, numero, titulo, tipo)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (norma_id, numero) DO UPDATE SET titulo = EXCLUDED.titulo""",
                (lis_id, numero, titulo, tipo)
            )

        conn.commit()
        print(f"OK: {len(liva_articulos)} artículos LIVA, {len(irnr_articulos)} IRNR, {len(lis_articulos)} LIS insertados")

        # ---- 6. Insertar textos de los artículos FactA más importantes ----
        articulos_con_texto = [
            ("LIVA", "162", """Artículo 162. Adquisiciones intracomunitarias de bienes.
Se consideran adquisiciones intracomunitarias de bienes las adquisiciones de bienes que reúnan los siguientes requisitos:
1.º Que sean transportados o expedidos por el cedente, por el cesionario o por un tercero en nombre de uno o de otro, desde un territorio de la Unión Europea distinto del territorio de aplicación del impuesto, hasta un territorio de aplicación del impuesto.
2.º Que el adquirente sea un sujeto pasivo del Impuesto sobre el Valor Añadido o una persona jurídica no sujeto pasivo considerada sujeto pasivo en aplicación de lo dispuesto en el artículo 84, un operador intracomunitario de bienes o un responsable del régimen especial del grupo de entidades, que las adquiera para la realización de sus actividades.
3.º Que las adquisiciones de bienes estén sujetas al Impuesto en la forma prevista en el artículo 163.
4.º Que las adquisiciones de bienes no estén sujetas al Impuesto en virtud de lo dispuesto en el artículo 7."""),

            ("LIVA", "163", """Artículo 163. Exenciones en las adquisiciones intracomunitarias de bienes.
1. Las adquisiciones intracomunitarias de bienes estarán exentas del Impuesto:
a) Las adquisiciones de bienes que, de conformidad con lo dispuesto en el Capítulo II del Título II, estén exentas de las entregas de bienes.
b) Las adquisiciones intracomunitarias de bienes de segunda mano, objetos de arte, artículos de colección o antigüedades, sujetas al régimen especial del margen de beneficio de los bienes de segunda mano, objetos de arte, artículos de colección y antigüedades.
2. Las adquisiciones intracomunitarias de bienes usadas, objetos de arte, artículos de colección o antigüedades, sujetas al régimen especial del margen de beneficio de los bienes de segunda mano, objetos de arte, artículos de colección y antigüedades, estarán exentas del Impuesto."""),

            ("LIVA", "175", """Artículo 175. Entregas intracomunitarias de bienes.
Se consideran entregas intracomunitarias de bienes las entregas de bienes que reúnan los siguientes requisitos:
1.º Que los bienes sean transportados o expedidos por el cedente, por el cesionario o por un tercero en nombre de uno o de otro, desde un territorio de aplicación del impuesto distinto del territorio de aplicación del impuesto en el que finalice el transporte o expedición.
2.º Que el cesionario sea un sujeto pasivo del Impuesto sobre el Valor Añadido o una persona jurídica no sujeto pasivo considerada sujeto pasivo en aplicación de lo dispuesto en el artículo 84, un operador intracomunitario de bienes o un responsable del régimen especial del grupo de entidades, que adquiera o reciba los bienes con destino a una operación que constituya una adquisición intracomunitaria para él.
3.º Que las entregas de bienes estén sujetas al Impuesto en la forma prevista en el artículo 176."""),

            ("LIVA", "176", """Artículo 176. Entregas intracomunitarias - exención de cuota.
1. Las entregas intracomunitarias de bienes estarán exentas del Impuesto, sin derecho a deducción, devolución ni compensación de las cuotas soportadas.
2. Para que las entregas intracomunitarias de bienes estén exentas del Impuesto será necesario que el sujeto pasivo:
a) Acredite que los bienes han sido expedidos o transportados a otro Estado miembro.
b) Acredite la condición de sujeto pasivo del adquirente en el Estado miembro de destino.
c) Haya presentado el Modelo 349, cuando proceda, dentro del plazo establecido.
d) Haya incluido los bienes en su inventario, cuando sea obligatorio.
e) Figure inscrito en el Registro de operadores intracomunitarios."""),

            ("LIVA", "177", """Artículo 177. Obligaciones del cedente intracomunitario.
El sujeto pasivo que realice entregas intracomunitarias de bienes estará obligado a:
a) Estar inscrito en el Registro de operadores intracomunitarios.
b) Incluir en la declaración-resumen (Modelo 349) los datos de las entregas intracomunitarias.
c) Expedir la factura correspondiente en la que conste el NIF intracomunitario del adquirente.
d) Llevar un registro detallado de todas las entregas intracomunitarias de bienes.
e) Conservar la documentación justificativa de los transportes."""),

            ("LIVA", "178", """Artículo 178. Obligaciones del adquirente intracomunitario.
El adquirente intracomunitario estará obligado a:
a) Estar inscrito en el Registro de operadores intracomunitarios.
b) Autoliquidar las adquisiciones intracomunitarias en el Modelo 303 o 300.
c) Presentar el Modelo 349 con los datos de las adquisiciones intracomunitarias.
d) Conservar la documentación justificativa de las adquisiciones."""),

            ("LIVA", "179", """Artículo 179. Facturas intracomunitarias - requisitos.
En las entregas y adquisiciones intracomunitarias de bienes, la factura deberá contener, además de los requisitos generales:
a) El NIF intracomunitario del adquirente/cesionario.
b) La indicación "Operación intracomunitaria" o "Entrega intracomunitaria de bienes".
c) La descripción de los bienes entregados y su cantidad.
d) El importe de la operación y el tipo de IVA aplicable (exento por art. 176).
e) La indicación del Estado miembro de destino de los bienes."""),

            ("LIVA", "180", """Artículo 180. Operaciones intracomunitarias de servicios.
1. La prestación de servicios a un sujeto pasivo establecido en otro Estado miembro estará sujeta en el Estado miembro de destino del servicio.
2. Cuando los servicios se presten a un sujeto pasivo no establecido en la Unión Europea, la entrega estará sujeta en el Estado miembro donde el prestador tenga su establecimiento.
3. Los servicios prestados a no residentes no establecidos en la UE se considerarán exportaciones de servicios y estarán exentos del IVA en los términos del artículo 21."""),

            ("LIVA", "181", """Artículo 181. Devolución de IVA a operadores intracomunitarios.
El régimen de devolución del IVA a operadores intracomunitarios no residentes se regirá por la Directiva 2008/9/CE, que establece las condiciones y modalidades de devolución del Impuesto sobre el Valor Añadido a sujetos pasivos no establecidos en el Estado miembro de devolución."""),

            ("LIVA", "182", """Artículo 182. Modelo 349 - declaración resumen de operaciones intracomunitarias.
1. Los sujetos pasivos que realicen entregas o adquisiciones intracomunitarias de bienes, o prestaciones de servicios a operadores intracomunitarios, estarán obligados a presentar el Modelo 349.
2. El Modelo 349 deberá presentarse trimestralmente, dentro de los primeros 20 días naturales del mes siguiente al trimestre natural.
3. En el Modelo 349 se declararán:
a) El NIF intracomunitario del operador.
b) El nombre del operador.
c) El importe de las entregas de bienes y prestaciones de servicios realizadas.
d) El importe de las adquisiciones de bienes y servicios recibidos.
4. El Modelo 349 NO se aplica a operaciones con no residentes fuera de la UE. Para estas operaciones se utiliza el Modelo 216."""),

            ("LIVA", "183", """Artículo 183. Obligación de facturación a no residentes - Modelo 216.
1. Las entregas de bienes y prestaciones de servicios realizadas a no residentes en España estarán sujetas a la declaración informativa del Modelo 216, regulada por el Real Decreto 1065/2007.
2. El Modelo 216 se presentará mensualmente, dentro de los primeros 20 días naturales del mes siguiente.
3. La presentación será electrónica obligatoria a través de la Sede electrónica de la AEAT.
4. Se aplicará a:
a) Entregas de bienes a no residentes no sujetos pasivos del IVA.
b) Prestaciones de servicios a no residentes.
c) Operaciones con no residentes fuera de la UE (Modelo 216, NO Modelo 349)."""),

            ("LIVA", "184", """Artículo 184. Entregas de bienes a no residentes fuera de la UE.
1. Las entregas de bienes a destinatarios establecidos fuera de la Unión Europea se considerarán exportaciones de bienes y estarán exentas del Impuesto (artículo 21 LIVA).
2. El exportador estará obligado a:
a) Declarar la operación en el Modelo 216 (FactA a terceros no residentes).
b) Conservar la documentación justificativa de la exportación.
c) Emitir factura con los datos del destinatario extranjero.
3. No se aplicará el Modelo 349 a operaciones con no residentes fuera de la UE."""),

            ("LIVA", "185", """Artículo 185. Prestaciones de servicios a no residentes - exportación de servicios.
1. Las prestaciones de servicios a no residentes se regirán por las reglas de localización del artículo 73 a 80 LIVA.
2. Los servicios prestados a no residentes fuera de la UE se considerarán exportaciones de servicios y estarán exentos del IVA (artículo 21 LIVA).
3. El prestador de servicios estará obligado a declarar la operación en el Modelo 216 cuando el destinatario sea un no residente.
4. Los servicios de asesoramiento, consultoría, gestión de carteras y otros servicios financieros a empresas en EE.UU. se consideran exportación de servicios."""),

            ("LIVA", "186", """Artículo 186. Facturación a no residentes - requisitos especiales.
Las facturas emitidas a no residentes deberán contener:
a) Datos identificativos del emitente (NIF, razón social, domicilio fiscal en España).
b) Datos identificativos del destinatario (nombre, dirección, NIF/tax ID del país de origen).
c) Nº de factura y fecha de emisión.
d) Descripción detallada de los bienes entregados o servicios prestados.
e) Base imponible, tipo de IVA aplicable y cuota.
f) Indicación de la exención aplicable (exportación de bienes/servicios, art. 21 LIVA).
g) Para operaciones intracomunitarias: NIF intracomunitario del destinatario."""),

            ("LIVA", "187", """Artículo 187. IVA en operaciones intracomunitarias con no residentes.
1. Las operaciones entre España y otros Estados miembros de la UE se regirán por el régimen intracomunitario (Modelos 349 y 303/300).
2. Las operaciones con no residentes fuera de la UE (EE.UU., Latinoamérica, etc.) se regirán como exportaciones/importaciones:
a) Entregas de bienes a no residentes fuera de la UE → Exentas (art. 21) + Modelo 216.
b) Prestaciones de servicios a no residentes fuera de la UE → Exentas (art. 21) + Modelo 216.
3. El Modelo 349 solo se aplica a operadores intracomunitarios (UE). No se aplica a no residentes fuera de la UE."""),

            ("IRNR", "1", """Artículo 1. Ámbito de aplicación del IRNR.
1. La presente Ley regula la tributación de los rendimientos obtenidos por no residentes en España en los términos establecidos en los convenios para evitar la doble tributación.
2. Están sujetos al IRNR:
a) Las personas físicas que no residan habitualmente en España.
b) Las entidades que no tengan su residencia fiscal en España.
c) Las rentas obtenidas en España por los anteriores."""),

            ("IRNR", "2", """Artículo 2. Rendimientos del capital mobiliario - dividendos e intereses.
1. Están sujetos al IRNR los rendimientos del capital mobiliarios obtenidos por no residentes, en particular:
a) Dividendos distribuidos por sociedades españolas.
b) Intereses de depósitos, cuentas y créditos.
c) Rendimientos de valores de renta fija.
d) Regalías y cánones por uso de patentes, marcas, etc.
2. Los rendimientos del capital mobiliario obtenidos por no residentes estarán sujetos a retención a cuenta del IRNR."""),

            ("IRNR", "6", """Artículo 6. Retenciones e ingresos a cuenta en operaciones con no residentes.
1. Las entidades españolas que realicen pagos a no residentes estarán obligadas a practicar retención en los rendimientos del capital mobiliario, del trabajo y del capital inmobiliario.
2. Las retenciones se practicarán a los tipos establecidos en esta Ley o en los convenios de doble tributación.
3. Las retenciones practicadas se ingresarán en los plazos establecidos y se declararán en los modelos correspondientes (123, 124, 216)."""),

            ("IRNR", "7", """Artículo 7. Tipos de retención del IRNR.
1. El tipo general de retención será del 20% para todos los rendimientos.
2. Los convenios de doble tributación podrán establecer tipos reducidos:
a) Dividendos: generalmente 15% (o 10% si el beneficiario es una entidad con participación significativa).
b) Intereses: generalmente 15%.
c) Regalías: generalmente 15%.
3. En caso de no disponer de convenio de doble tributación, se aplicará el tipo general del 20%."""),

            ("IRNR", "8", """Artículo 8. Convenios internacionales para evitar la doble tributación.
1. Los convenios internacionales para evitar la doble tributación suscritos por España se aplicarán preferentemente a la normativa interna.
2. Para aplicar el tipo reducido del convenio, el no residente deberá acreditar su residencia fiscal mediante:
a) Certificado de residencia fiscal emitido por la autoridad fiscal de su país.
b) Formulario W-8BEN (personas físicas) o W-8BEN-W (entidades).
3. El convenio España-EE.UU. establece tipos reducidos para dividendos (15%), intereses (15%) y regalías (15%)."""),

            ("IRNR", "9", """Artículo 9. Obligaciones de presentación de modelos 216, 123, 124.
1. Las entidades españolas que realicen pagos a no residentes estarán obligadas a presentar:
a) Modelo 123: para rendimientos del trabajo y otros rendimientos no incluidos en el 124. Trimestral.
b) Modelo 124: para dividendos y rentas de capital mobiliario. Mensual.
c) Modelo 216: para entregas de bienes y prestaciones de servicios a no residentes. Mensual.
2. Todos los modelos se presentarán electrónicamente en la Sede electrónica de la AEAT."""),

            ("IRNR", "11", """Artículo 11. Documentación justificativa de residencia fiscal.
1. El no residente deberá acreditar su residencia fiscal para aplicar los convenios de doble tributación.
2. La documentación requerida incluye:
a) Certificado de residencia fiscal.
b) Formulario W-8BEN (personas físicas) o W-8BEN-W (entidades).
c) TIN (Taxpayer Identification Number) del país de residencia.
3. Para residentes en EE.UU.: el formulario W-8BEN-W debe incluir el EIN (Employer Identification Number), la clasificación de entidad (FFI, NFFE, etc.) y los controlling persons si aplica."""),

            ("LIS", "4", """Artículo 4. Renta obtenida en España por no residentes.
1. Están sujetos al Impuesto sobre Sociedades por las rentas obtenidas en España los no residentes que realicen actividades en territorio español a través de un establecimiento permanente.
2. También están sujetos por los rendimientos del capital mobiliario, del capital inmobiliario y las ganancias patrimoniales obtenidos en España."""),

            ("LIS", "6", """Artículo 6. Rendimientos del capital mobiliario obtenidos por no residentes.
1. Los rendimientos del capital mobiliario obtenidos por no residentes estarán sujetos al IRNR o al Convenio de Doble Tributación aplicable.
2. Las sociedades españolas que distribuyan dividendos a no residentes estarán obligadas a practicar retención e ingresar las cuotas en los plazos establecidos."""),
        ]

        # Insertar textos en version_articulo
        for norma_code, numero, texto in articulos_con_texto:
            norma_id = normas[norma_code]
            cur.execute(
                "SELECT id FROM articulo WHERE norma_id = %s AND numero = %s",
                (norma_id, numero)
            )
            row = cur.fetchone()
            if row:
                articulo_id = row[0]
                # Check if version already exists for this articulo
                cur.execute(
                    "SELECT id FROM version_articulo WHERE articulo_id = %s AND vigente_desde = %s",
                    (articulo_id, date(2025, 1, 1))
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE version_articulo SET texto = %s WHERE id = %s",
                        (texto, existing[0])
                    )
                else:
                    cur.execute(
                        """INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
                           VALUES (%s, %s, %s)""",
                        (articulo_id, texto, date(2025, 1, 1))
                    )

        conn.commit()
        print(f"OK: Textos de {len(articulos_con_texto)} artículos insertados")

        # ---- 7. Insertar materias FactA ----
        materias = [
            ("facta", "Facturas a Terceros (FactA)"),
            ("no_residentes", "No residentes"),
            ("intracomunitario", "Operaciones intracomunitarias"),
            ("fatca", "FATCA / CRS"),
            ("convenios_doble_tributacion", "Convenios de doble tributación"),
            ("exportacion_servicios", "Exportación de servicios"),
        ]
        for slug, etiqueta in materias:
            cur.execute(
                """INSERT INTO materia (slug, etiqueta)
                   VALUES (%s, %s)
                   ON CONFLICT (slug) DO NOTHING""",
                (slug, etiqueta)
            )

        conn.commit()
        print("OK: Materias FactA insertadas")

if __name__ == "__main__":
    main()
