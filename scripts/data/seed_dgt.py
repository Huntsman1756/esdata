"""
Seed script for DGT consultaciones vinculantes (DGT Petete).
Source: apps/workers/dgt.py
Table: documento_interpretativo
Upsert key: referencia
"""

import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA = [
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V2274-22",
        "2023-02-15",
        "V2274-22 — Determinaciones sobre aplicacion del IVA a servicios de telecomunicaciones electronicos y radiodifusion",
        "Las entidades no establecidas en el territorio de aplicacion del Impuesto sobre el Valor Añadido que presten servicios de telecomunicaciones, de radiodifusion y de servicios electronicos a no empresarios o profesionales, cuando el destinatario este establecido en el territorio de aplicacion del Impuesto, deberan repercutir dicho Impuesto segun el lugar donde tenga su domicilio o residencia el destinatario o la persona a quien se dirigian las entregas, de conformidad con lo dispuesto en el articulo 74, apartado 3, de la Directiva 2006/112/CE.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V1923-24",
        "2024-06-10",
        "V1923-24 — Aplicacion del tipo reducido del IVA en operaciones de suministro de gas natural y gas de petroleo",
        "El gas natural y el gas de petroleo liquefactado o licuado, incluidos los gases procedentes del refino de petroleo, que se encuentren en el estado fisico de gas, a los que se refiere el anexo I de la Ley 37/1992, del Impuesto sobre el Valor Añadido, podran tributar al tipo reducido del cuatro por ciento, siempre que se suministren a consumidores finales y su consumo no sea industrial.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1923-24",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V2691-21",
        "2022-01-20",
        "V2691-21 — Retencion del IRPF en dividendos distribuidos por sociedades extranjeras",
        "Los dividendos distribuidos por sociedades residentes en Estados miembros de la Union Europea o Espacio Economico Europeo estan sujetos a retencion a cuenta del Impuesto sobre la Renta de las Personas Fisicas. El tipo de retencion sera el general establecido en la normativa del IRPF, salvo que el conveno bilateral de doble tributacion establezca un tipo reducido.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2691-21",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V1387-20",
        "2021-04-08",
        "V1387-20 — Determinacion del lugar de inicio de la obra de construccion para el ITPAJD",
        "Para la determinacion del lugar de inicio de la obra de construccion a efectos del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados, se tendra en cuenta la fecha de obtencion de la licencia municipal de obras o, en su defecto, la fecha de inicio efectivo de los trabajos de construccion.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1387-20",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V1140-24",
        "2024-09-05",
        "V1140-24 — Tratamiento fiscal de las opciones de compra de acciones para empleados (ESOP)",
        "Las opciones de compra de acciones (ESOP) otorgadas a empleados no generan hecho imponible en el momento de su concesion. El hecho imponible se realizara en el momento del ejercicio de la opcion, tributarando el trabajador en el IRPF por la diferencia entre el valor de mercado de las acciones en ese momento y el precio de ejercicio pagado.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1140-24",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V2509-20",
        "2021-11-12",
        "V2509-20 — Aplicabilidad de la exencion del IRPF por venta de vivienda habitual",
        "La exencion prevista en el articulo 45.1.a) de la Ley 35/2006 del IRPF requiere que el contribuyente haya residido efectivamente en la vivienda durante al menos los tres anos anteriores a su venta, que el importe de la enajenacion se haya reinvertido en la adquisicion de otra vivienda habitual en el plazo de dos anos, y que el capital disponible no supere los 240.000 euros.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2509-20",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V0228-25",
        "2025-01-15",
        "V0228-25 — Determinacion de la residencia fiscal de personas fisicas con actividad economica dual",
        "A efectos de determinar la residencia fiscal de una persona fisica que desarrolla actividad economica en mas de un pais, se aplicaran los criterios de la regla de la luz mutua de los convenios de doble tributacion. Se considerara residente en Espana cuando el centro de intereses economicos estee predominantemente en Espana, aun cuando el numero de dias de estancia fuera del territorio nacional no supere los 183 anos durante el ejercicio.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0228-25",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V2223-22",
        "2023-05-18",
        "V2223-22 — Deduccion por doble imposicion internacional en el Impuesto sobre Sociedades",
        "Las empresas residentes en Espana que obtengan rendimientos en el extranjero podran aplicar una deduccion por doble imposicion internacional limitada al importe de la cuota tributaria correspondiente a dichos rendimientos. La deduccion no podra superar el porcentaje proporcional de la cuota liquidada que corresponda a los rendimientos obtenidos en el extranjero.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2223-22",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V0745-20",
        "2020-10-22",
        "V0745-20 — Clasificacion IVA de servicios de hosting y alojamiento web",
        "Los servicios de hosting y alojamiento web se encuentran dentro del ambito de aplicacion del Impuesto sobre el Valor Añadido. La prestacion de estos servicios electronicos a consumidores finales establecidos en la Union Europea se sujetara al IVA del pais de residencia del consumidor, de conformidad con las normas de lugar de aplicacion de la Directiva 2006/112/CE.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0745-20",
    ),
    (
        "consulta_vinculante",
        "DGT",
        "es",
        "dgt",
        "fiscal",
        "V1902-23",
        "2024-03-01",
        "V1902-23 — Deduccion por actividades de I+D+i en el Impuesto sobre Sociedades",
        "Las inversiones en actividades de investigacion, desarrollo e innovacion podran ser objeto de una deduccion en la cuota del Impuesto sobre Sociedades. La deduccion se calcula aplicando un tipo del 10% a las inversiones en I+D+i realizadas, con un limite equivalente al 25% de la cuota íntegra. Adicionalmente, las inversiones superiores a las del ejercicio anterior podran aplicar un tipo del 17% sobre el incremento.",
        "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1902-23",
    ),
]


def main():
    print("Seeding DGT consultaciones vinculantes...")
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://esdata:esdata_dev@localhost:5432/esdata",
    )
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()
        upsert_sql = """
            INSERT INTO documento_interpretativo (
                tipo_documento, organismo_emisor, jurisdiccion,
                tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (referencia)
            DO UPDATE SET
                fecha = EXCLUDED.fecha,
                titulo = EXCLUDED.titulo,
                texto = EXCLUDED.texto,
                url_fuente = EXCLUDED.url_fuente
        """
        for row in DATA:
            cur.execute(upsert_sql, row)
        conn.commit()
    print(f"Done. {len(DATA)} DGT consultaciones seeded.")


if __name__ == "__main__":
    main()
