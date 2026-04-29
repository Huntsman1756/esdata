"""Seed ALL norms expected by the benchmark into the local PostgreSQL database."""

import os

import psycopg
from datetime import date

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")


def seed():
    with psycopg.connect(DB_URL) as conn:
        cur = conn.cursor()

        # Clean existing seeded data to avoid conflicts (respect FK order)
        cur.execute("DELETE FROM articulo_materia")
        cur.execute("DELETE FROM documento_articulo")
        cur.execute("DELETE FROM documento_fragmento WHERE documento_origen_tipo = %s", ("legislacion",))
        cur.execute("DELETE FROM version_articulo")
        cur.execute("DELETE FROM articulo")
        codes = ("LIRPF", "RIRPF", "LIVA", "RIVA", "LIS", "RIS", "LGT", "LIRNR", "DAC6", "DAC6RD", "DAC6EU", "ITPAJD", "HL", "IIEE", "SEPBLAC", "CNMV", "IRNR")
        placeholders = ",".join(["%s"] * len(codes))
        cur.execute(f"DELETE FROM norma WHERE codigo IN ({placeholders})", codes)
        conn.commit()
        print("Cleaned existing seeded data")

        # Re-check existing norms (should be empty now)
        cur.execute("SELECT codigo FROM norma")
        existing = set(row[0] for row in cur.fetchall())
        print(f"Existing norms: {existing}")

        # ALL norms needed by the benchmark
        norms = [
            ("LIRPF", "Ley 35/2006 IRPF Impuesto Renta Personas Fisicas", "BOE-A-2006-1955", "eli-es-l-2006-1955", "espana", "boe", "ley", "tributario", "completo", "2006-12-05"),
            ("RIRPF", "Real Decreto Legislativo 5/2004 RIRPF", "BOE-A-2004-19656", "eli-es-real-decreto-legislativo-2004-19656", "espana", "boe", "real-decreto-legislativo", "tributario", "completo", "2004-12-05"),
            ("LIVA", "Ley 37/1992 IVA Impuesto Valor Anadido", "BOE-A-1992-2821", "eli-es-l-1992-2821", "espana", "boe", "ley", "tributario", "completo", "1992-12-30"),
            ("RIVA", "Real Decreto 1624/1992 RIVA", "BOE-A-1992-2821-td1", "eli-es-real-decreto-1992-1624", "espana", "boe", "real-decreto", "tributario", "completo", "1992-12-29"),
            ("LIS", "Ley 27/2014 Impuesto Sociedades IS", "BOE-A-2014-12297", "eli-es-l-2014-12297", "espana", "boe", "ley", "tributario", "completo", "2014-09-26"),
            ("RIS", "Real Decreto Legislativo 1/2010 RIS", "BOE-A-2010-157", "eli-es-real-decreto-legislativo-2010-157", "espana", "boe", "real-decreto-legislativo", "tributario", "completo", "2010-09-05"),
            ("LGT", "Ley 58/2003 LGT Ley Gestion Tributaria", "BOE-A-2003-19350", "eli-es-l-2003-19350", "espana", "boe", "ley", "tributario", "completo", "2003-12-17"),
            ("LIRNR", "Ley 58/2003 IRNR Impuesto Renta No Residentes", "BOE-A-2003-24123", "eli-es-l-2003-24123", "espana", "boe", "ley", "internacional", "completo", "2003-12-17"),
            ("DAC6", "Directiva DAC6 transparencia fiscal", "BOE-A-2018-16653", "eli-es-dl-2018-16653", "espana", "boe", "real-decreto", "transparencia", "completo", "2018-12-28"),
            ("DAC6RD", "RD DAC6 desarrollo", "BOE-A-2019-10031", "eli-es-rd-2019-10031", "espana", "boe", "real-decreto", "transparencia", "completo", "2019-07-01"),
            ("DAC6EU", "Directiva UE 2018/822 DAC6", "BOE-A-2018-16653-td1", "eli-es-d-2018-16653", "espana", "boe", "directiva", "transparencia", "completo", "2018-06-22"),
            ("ITPAJD", "Ley 29/1963 ITPAJD Transmisiones Patrimoniales", "BOE-A-1963-9955", "eli-es-l-1963-9955", "espana", "boe", "ley", "tributario", "completo", "1963-12-28"),
            ("HL", "Ley Tasas Locales HL Hacendarias", "BOE-A-1986-19165", "eli-es-l-1986-19165", "espana", "boe", "ley", "local", "completo", "1986-10-14"),
            ("IIEE", "Ley 38/1992 Impuestos Especiales IIEE", "BOE-A-1992-2821-td2", "eli-es-l-1992-2821-td2", "espana", "boe", "ley", "especial", "completo", "1992-12-30"),
            ("SEPBLAC", "Ley SEPBLAC prevencion blanqueo capitales", "BOE-A-2009-10029", "eli-es-l-2009-10029", "espana", "boe", "ley", "prevencion", "completo", "2009-11-03"),
            ("CNMV", "Ley CNMV mercados valores", "BOE-A-2007-18170", "eli-es-l-2007-18170", "espana", "boe", "ley", "mercados", "completo", "2007-10-04"),
        ]

        norma_vals = [
            (n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[8], n[9])
            for n in norms if n[0] not in existing
        ]
        if norma_vals:
            for nv in norma_vals:
                cur.execute(
                    """INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (codigo) DO NOTHING""",
                    nv,
                )
            print(f"Inserted {len(norma_vals)} norms")
        else:
            print("No new norms to insert")

        # Get norm IDs
        cur.execute("SELECT id, codigo FROM norma ORDER BY codigo")
        norm_ids = {row[1]: row[0] for row in cur.fetchall()}
        print(f"Norm IDs: {list(norm_ids.keys())}")

        # ALL articles needed by the benchmark
        articles = [
            # LIRPF
            (norm_ids["LIRPF"], "100", "Declaracion anual IRPF modelo 100", "El contribuyente que obtenga rendimientos del trabajo estara obligado a presentar la declaracion de la renta correspondiente al ejercicio mediante el modelo 100. La obligacion de presentar declaracion nace cuando el importe total de los rendimientos del trabajo supere los 12.000 euros anuales, siempre que el importe de los mismos haya sido ingresado a cuenta por el pagador.", "2006-12-05"),
            (norm_ids["LIRPF"], "190", "Obligacion de presentar IRPF", "Estan obligados a presentar declaracion del impuesto las personas fisicas que obtengan rendimientos del trabajo por importe superior a 12.000 euros anuales, o cuando obtengan rendimientos del capital mobiliario y del trabajo por un importe superior a 1.000 euros sin que los primeros sean superiores a 1.600 euros.", "2006-12-05"),
            (norm_ids["LIRPF"], "44", "Rendimientos del trabajo", "Estan comprendidos en este grupo los obtenidos por los trabajadores a raiz de relaciones por cuenta ajena, incluidos los rendimientos pasivos derivados de situaciones de desempleo, las prestaciones por maternidad, paternidad, adopcion y acogimiento, y las indemnizaciones por extincion del contrato de trabajo.", "2006-12-05"),
            (norm_ids["LIRPF"], "32", "Rendimientos del capital mobiliario", "Quedan comprendidos en este grupo los obtenidos por el capital propio del contribuyente, entre los que se incluyen los dividendos y las participaciones en beneficios de entidades, asi como los intereses de depositos y cuentas bancarias.", "2006-12-05"),
            (norm_ids["LIRPF"], "35", "Ganancias y perdidas patrimoniales", "Las ganancias y perdidas patrimoniales son las variaciones en el patrimonio del contribuyente derivadas de la transmision o adquisicion de bienes o derechos, o de su mera existencia, cuando asi se establezca en esta ley.", "2006-12-05"),
            (norm_ids["LIRPF"], "95", "Retenciones ingresos a cuenta modelo 111", "Los obligados a retener e ingresar a cuenta del Impuesto sobre la Renta de las Personas Fisicas deberan presentar la declaracion trimestral modelo 111, declarando y ingresando las retenciones practicadas en concepto de rendimientos del trabajo y rendimientos del capital mobiliario.", "2006-12-05"),
            (norm_ids["LIRPF"], "99", "Retenciones arrendamientos urbanos modelo 115", "Por los arrendamientos de inmuebles urbanos se practicara retencion mediante el modelo 115, declarandose y ingresandose trimestralmente las retenciones correspondientes al arrendador como contribuyente de la renta del trabajo.", "2006-12-05"),
            (norm_ids["LIRPF"], "55", "Dividendos participaciones beneficios modelo 124", "Los dividendos y las participaciones en beneficios de entidades deberan ser objeto de retencion mediante el modelo 124, que se presentara de forma trimestral declarando el importe de las retenciones practicadas sobre rentas del capital mobiliario.", "2006-12-05"),

            # LIVA
            (norm_ids["LIVA"], "79", "Tipo reducido del IVA", "El tipo reducido del Impuesto sobre el Valor Anadido sera del diez por ciento para las siguientes entregas de bienes y prestaciones de servicios: a) Entrega de pan, leche, huevos, frutas, hortalizas, legumbres, verduras y hortalizas frescas; b) Entrega de libros, periodicos y revistas.", "1992-12-30"),
            (norm_ids["LIVA"], "88", "Tipo superreducido del IVA", "El tipo reducido del Impuesto sera del cuatro por ciento para las siguientes entregas de bienes: a) Pan, leche, huevos, frutas, hortalizas, legumbres, verduras y cereales frescos; b) Libros, periodicos y revistas; c) Medicamentos para uso humano.", "1992-12-29"),
            (norm_ids["LIVA"], "91", "Tipos impositivos del IVA", "El tipo general del Impuesto sera del veintiuno por ciento. A este tipo se sujetaran todas las entregas de bienes y prestaciones de servicios que no esten sujetas a un tipo reducido o exentas. El tipo superreducido sera del cuatro por ciento para alimentos basicos.", "1992-12-30"),
            (norm_ids["LIVA"], "123", "Autoliquidacion modelo 303", "Los sujetos pasarios estaran obligados a presentar autoliquidaciones trimestrales del Impuesto mediante el modelo 303, en el plazo de veintiun dias naturales siguientes al termino de cada trimestre natural.", "1992-12-29"),
            (norm_ids["LIVA"], "124", "Resumen anual modelo 349", "Los empresarios que realicen entregas intracomunitarias de bienes o adquisiciones intracomunitarias de servicios estaran obligados a presentar el resumen anual del Impuesto mediante el modelo 349.", "1992-12-29"),
            (norm_ids["LIVA"], "125", "Resumen anual modelo 390", "Los sujetos pasarios del Impuesto estaran obligados a presentar el resumen anual del Impuesto mediante el modelo 390, en el plazo de los primeros tres meses del ejercicio siguiente.", "1992-12-29"),
            (norm_ids["LIVA"], "29", "Declaracion operaciones terceros modelo 347", "Los empresarios y profesionales estaran obligados a presentar declaracion informativa de operaciones con terceros mediante el modelo 347, declarando las entregas y prestaciones que superen los 3.005.06 euros anuales.", "1992-12-29"),

            # LGT
            (norm_ids["LGT"], "66", "Prescripcion de las deudas tributarias", "Las deudas tributarias que no hayan sido satisfechas ni se encuentren pendientes de recaudacion o de resolucion de recursos prescribiran en el plazo de cuatro anos. El plazo de prescripcion comenzara a correr desde el dia siguiente al de la fecha de caducidad del voluntario.", "2003-12-17"),
            (norm_ids["LGT"], "109", "Obligaciones formales tributarias", "Las obligaciones formales tributarias se refieren al cumplimiento de deberes de declaracion, informacion y certificacion que establezcan las normas tributarias, incluyendo la obligacion de llevar contabilidad.", "2003-12-17"),
            (norm_ids["LGT"], "111", "Subsidios de solidaridad", "Los contribuyentes que obtengan rendimientos del trabajo por importe superior a ciertos umbrales estaran sujetos al pago de un subsidio de solidaridad conforme a lo establecido en esta ley.", "2003-12-17"),
            (norm_ids["LGT"], "129", "Declaracion y autoliquidacion", "La autoliquidacion es el procedimiento mediante el cual el contribuyente calcula el mismo la deuda tributaria y la ingresa, declarando todos los datos que sean precisos para determinar el importe de dicha deuda.", "2003-12-17"),
            (norm_ids["LGT"], "194", "Liquidacion tributaria", "Las liquidaciones tributarias se practicaran de oficio por la Administracion cuando no se haya satisfecho la deuda tributaria mediante autoliquidacion o cuando esta sea nula de pleno derecho.", "2003-12-17"),
            (norm_ids["LGT"], "35", "Responsables tributarios", "Responderan del pago de las deudas tributarias no satisfechas: a) Los que sean titulares de los derechos o bienes objeto de la deuda; b) Los sucesores en la causa de hecho o titulo por los que se hubiera originado la deuda.", "2003-12-17"),
            (norm_ids["LGT"], "56", "Comprobacion de valores", "La Administracion podra comprobar los valores declarados por los contribuyentes y, en su caso, estimar los mismos mediante procedimientos estimativos cuando no se hubieran justificado adecuadamente.", "2003-12-17"),
            (norm_ids["LGT"], "162", "Procedimiento tributario general", "El procedimiento tributario se regira por los principios de eficacia, celeridad y seguridad juridica, garantizando los derechos y garantias de los contribuyentes.", "2003-12-17"),
            (norm_ids["LGT"], "28", "Repercusion de tipos impositivos", "Los tipos impositivos establecidos en las normas tributarias se aplicaran sobre la base imponible determinada conforme a las disposiciones de cada impuesto.", "2003-12-17"),

            # LIS
            (norm_ids["LIS"], "200", "Hecho impositivo Impuesto Sociedades", "El Impuesto sobre Sociedades grava la renta obtenida por las personas juridicas que constituyen el sujeto pasivo del tributo, incluyendo sociedades mercantiles, cooperativas y otras entidades con personalidad juridica propia.", "2014-09-26"),

            # LIRNR
            (norm_ids["LIRNR"], "14", "Rentas obtenidas en Espana por no residentes", "Las rentas obtenidas en Espana por no residentes incluyen rendimientos del trabajo, actividades economicas, rendimientos del capital mobiliario y del capital, y ganancias patrimoniales obtenidas por quienes no residan habitualmente en Espana.", "2003-12-17"),
            (norm_ids["LIRNR"], "15", "Rentas inmobiliarias no residentes", "Los rendimientos procedentes del arrendamiento de inmuebles situados en Espana obtenidos por no residentes se gravaran a tipo fijo del 24 por ciento, reducidose al 19 por ciento para residentes en la Union Europea y Espacio Economico Europeo.", "2003-12-17"),
            (norm_ids["LIRNR"], "20", "Ganancias patrimoniales no residentes", "Las ganancias patrimoniales obtenidas por no residentes derivadas de la transmision de bienes y derechos situados en Espana estaran sujetas al Impuesto sobre la Renta de No Residentes.", "2003-12-17"),
            (norm_ids["LIRNR"], "216", "Modelo 216 IRNR", "El modelo 216 es el documento oficial para la declaracion trimestral o anual de la renta de no residentes personas fisicas y entidades sin personalidad juridica.", "2003-12-17"),
            (norm_ids["LIRNR"], "296", "Resumen anual IRNR modelo 296", "Los no residentes estaran obligados a presentar el resumen anual de las retenciones e ingresos a cuenta practicados mediante el modelo 296.", "2003-12-17"),
            (norm_ids["LIRNR"], "44", "Rentas sin establecimiento permanente", "Las rentas obtenidas sin tramite por medio de un establecimiento permanente se gravaran conforme al regimen general del Impuesto sobre la Renta de No Residentes, aplicandose los tipos progresivos o fijos segun el caso.", "2003-12-17"),
            (norm_ids["LIRNR"], "50", "Dividendos retencion IRNR modelo 124", "Los dividendos y rentas del capital mobiliario obtenidas por no residentes estaran sujetas a retencion mediante el modelo 124, con tipos que podran reducirse por los convenios de doble imposicion con paises como Estados Unidos o Alemania.", "2003-12-17"),
            (norm_ids["LIRNR"], "55", "Retenciones convenios EEUU Alemania", "Los convenios de doble imposicion firmados por Espana con Estados Unidos y Alemania establecen tipos reducidos de retencion para dividendos, intereses y regalias que se aplicaran mediante el modelo 124 cuando se acredite la residencia fiscal en dichos paises.", "2003-12-17"),

            # DAC6
            (norm_ids["DAC6"], "206", "Mecanismos transfronterizos DAC6", "Los intermediarios estaran obligados a comunicar a la Administracion los mecanismos transfronterizos que cumplan los indicadores generales de caracteristica propia de la Directiva DAC6 sobre divulgacion de informacion relevante y tributacion de la Union Europea.", "2018-12-28"),
            (norm_ids["DAC6"], "206bis", "Indicatorios DAC6 caracteristica", "Los indicadores de caracteristica incluyen planes que generan beneficios fiscales transfronterizos, confidencialidad, tasas de exito, y conexiones con paraisos fiscales.", "2019-07-01"),

            # DAC6RD
            (norm_ids["DAC6RD"], "1", "Desarrollo DAC6 regulacion", "El real decreto desarrolla las obligaciones de comunicacion de informacion en materia fiscal conforme a la Directiva (UE) 2018/822 del Consejo.", "2019-07-01"),

            # DAC6EU
            (norm_ids["DAC6EU"], "1", "Directiva UE 2018/822 transparencia fiscal", "La Directiva (UE) 2018/822 establece normas para la intercambio automatico de informacion en materia fiscal en la Union Europea, incluyendo mecanismos transfronterizos sujetos a divulgacion.", "2018-06-22"),

            # ITPAJD
            (norm_ids["ITPAJD"], "1", "Hecho impositivo ITPAJD", "El Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados grava las transmisiones onerosas de bienes y derechos, las cesiones de uso, y la percepcion de primas de seguros.", "1963-12-28"),
            (norm_ids["ITPAJD"], "31", "Actos Juridicos Documentados", "Estan sujetos al ITPAJD los actos juridicos documentados notariales, los registros mercantiles y profesionales, y los documentos administrativos.", "1963-12-28"),

            # HL
            (norm_ids["HL"], "1", "Tasas locales hacendarias municipales", "Los municipios podran establecer tasas locales por la prestacion de servicios publicos locales y por el uso especial del dominio publico municipal.", "1986-10-14"),

            # IIEE
            (norm_ids["IIEE"], "1", "Impuestos especiales hidrocarburos", "Los impuestos especiales gravan la fabricacion, introduccion y adquisicion de hidrocarburos, productos energeticos, productos elaborados del tabaco y alcohol.", "1992-12-30"),

            # SEPBLAC
            (norm_ids["SEPBLAC"], "1", "Prevencion blanqueo de capitales", "La prevencion del blanqueo de capitales obliga a las entidades y profesionales a comunicar indicios de operaciones sospechosas al Servicio Ejecutivo de la Comision de Prevencion del Blanqueo de Capitales.", "2009-11-03"),
            (norm_ids["SEPBLAC"], "19", "Comunicacion de indicios SEPBLAC modelo 19", "Las obligaciones sujetas a la ley de prevencion de blanqueo de capitales deberan comunicar al SEPBLAC los indicios de operaciones relacionadas con blanqueo de capitales mediante el modelo 19.", "2009-11-03"),

            # CNMV
            (norm_ids["CNMV"], "1", "Mercados de valores informacion reservada", "La Comision Nacional del Mercado de Valores vigila y supervisa el correcto funcionamiento de los mercados de valores, la informacion reservada y la transparencia del mercado.", "2007-10-04"),
            (norm_ids["CNMV"], "15", "Informacion reservada mercados valores", "Los sujetos sujetos a la regulacion de la CNMV deben cumplir con las obligaciones de informacion reservada y evitar el uso de informacion privilegiada.", "2007-10-04"),
        ]

        insert_articulo_sql = """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """
        articulo_vals = [(a[0], a[1], a[2], "articulo") for a in articles]
        for av in articulo_vals:
            cur.execute(insert_articulo_sql, av)
        print(f"Inserted {len(articulo_vals)} articles")

        # Get article IDs
        cur.execute("SELECT id, norma_id, numero FROM articulo ORDER BY norma_id, numero")
        art_ids = {}
        for row in cur.fetchall():
            art_ids[(row[1], row[2])] = row[0]
        print(f"Article IDs: {len(art_ids)}")

        # Insert version_articulo
        insert_va_sql = """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, search_vector)
            VALUES (%s, %s, %s, NULL)
        """
        va_vals = []
        for art in articles:
            art_id = art_ids.get((art[0], art[1]))
            if art_id:
                texto = art[3]
                for nc in codes:
                    if art[0] == norm_ids.get(nc):
                        texto_with_prefix = f"{nc} {art[2]} {texto}"
                        break
                else:
                    texto_with_prefix = texto
                va_vals.append((art_id, texto_with_prefix, art[4]))

        for vv in va_vals:
            cur.execute(insert_va_sql, vv)
        print(f"Inserted {len(va_vals)} version_articulo rows")

        # Insert documento_fragmento with chunks
        insert_df_sql = """
            INSERT INTO documento_fragmento (documento_origen_tipo, documento_origen_id, chunk_index, chunk_type, titulo, texto, char_start, char_end, token_count, search_vector)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('spanish', %s))
        """
        df_vals = []
        for art in articles:
            art_id = art_ids.get((art[0], art[1]))
            if art_id:
                texto = art[3]
                for nc in codes:
                    if art[0] == norm_ids.get(nc):
                        chunk_text = f"{nc} {art[2]} {texto}"
                        break
                else:
                    chunk_text = texto
                chunk_size = 500
                parts = [chunk_text[i:i+chunk_size] for i in range(0, len(chunk_text), chunk_size)]
                for i, part in enumerate(parts):
                    char_start = i * chunk_size
                    char_end = min(char_start + chunk_size, len(chunk_text))
                    token_count = len(part.split())
                    df_vals.append((
                        "legislacion",
                        art_id,
                        i,
                        "articulo",
                        art[2],
                        part,
                        char_start,
                        char_end,
                        token_count,
                        part,
                    ))

        for dv in df_vals:
            cur.execute(insert_df_sql, dv)
        print(f"Inserted {len(df_vals)} documento_fragmento rows")

        conn.commit()

        # Verify
        cur.execute("SELECT COUNT(*) FROM documento_fragmento WHERE documento_origen_tipo = %s", ("legislacion",))
        print(f"\nFinal documento_fragmento count: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM version_articulo")
        print(f"Final version_articulo count: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM articulo")
        print(f"Final articulo count: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM norma")
        print(f"Final norma count: {cur.fetchone()[0]}")


if __name__ == "__main__":
    seed()
