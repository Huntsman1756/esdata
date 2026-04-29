import os
import psycopg
import uuid

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

MARCO_RECORDS = [
    {
        "codigo": "mc-nv-01",
        "titulo": "Norma de Valoracion 1ª — Fondos propios",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las participaciones en participaciones y en instrumentos de patrimonio de otras entidades se valoraran por su valor de realizacion estimado, deduciendo, en su caso, las estimaciones de pérdidas.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-02",
        "titulo": "Norma de Valoracion 2ª — Inmovilizado material",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "El inmovilizado material se valorara por su precio de adquisicion o coste de produccion, deduciendo las perdidas que sean consecuencia de la depreciacion en el valor de sus activos.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20423",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-03",
        "titulo": "Norma de Valoracion 3ª — Inmovilizado financiero",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las participaciones en instrumentos de patrimonio se valoraran por su valor de realizacion estimado. Las deudas y creditos a largo plazo se valoraran por su valor razonable.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20424",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-04",
        "titulo": "Norma de Valoracion 4ª — Deterioro y variaciones razonables del activo",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Se reconocera como gasto el importe por el que el valor en libro de un activo supere el valor que se espera recuperar por su uso o venta.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20425",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-05",
        "titulo": "Norma de Valoracion 5ª — Operaciones con partes vinculadas",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las operaciones con partes vinculadas se registraran identificando la naturaleza de las mismas, asi como el importe y condiciones en que se han realizado.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20426",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-06",
        "titulo": "Norma de Valoracion 6ª — Ingresos de explotacion",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Los ingresos por ventas y prestaciones de servicios se reconoceran por el valor razonable de la contrapartida recibida o por cobrar.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20427",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-07",
        "titulo": "Norma de Valoracion 7ª — Transmision de inmovilizado",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Se reconocera como ganancia o perdida la diferencia entre el valor razonable de la contrapartida y el valor neto contable del activo transmitido.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20428",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-08",
        "titulo": "Norma de Valoracion 8ª — Operaciones en moneda extranjera",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las operaciones en moneda extranjera se registraran al tipo de cambio de la moneda nacional aplicable a la fecha de realizacion de la operacion.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20429",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-09",
        "titulo": "Norma de Valoracion 9ª — Operaciones de seguro",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las primas de seguros se reconoceran como ingresos a medida que se produce el riesgo cubierto por la poliza.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20430",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-10",
        "titulo": "Norma de Valoracion 10ª — Operaciones de arrendamiento",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Los contratos de arrendamiento se clasificaran como financieros o operativos segun si transfieren sustancialmente todos los riesgos y ventajas inherentes a la propiedad del activo.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20431",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-11",
        "titulo": "Norma de Valoracion 11ª — Subvenciones, donaciones y aportaciones de terceros",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las subvenciones de capital se registraran como un ingreso diferido y se reconoceran en la cuenta de perdidas y ganancias de forma sistematica a lo largo de la vida util del activo subyacente.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20432",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-12",
        "titulo": "Norma de Valoracion 12ª — Provisiones",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Se reconocera como provision el importe que se estime necesario para cubrir de forma razonable un pasivo o una perdida potenciales.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20433",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-13",
        "titulo": "Norma de Valoracion 13ª — Operaciones con instrumentos financieros",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Los instrumentos financieros se clasificaran en las categorias establecidas y se valoraran por su valor razonable a la fecha de reconocimiento inicial.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20434",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-14",
        "titulo": "Norma de Valoracion 14ª — Provisión para riesgos y gastos",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Se reconocera como gasto una provision para riesgos y gastos cuando exista una obligacion actual derivada de un evento pasado, sea probable que sea necesario utilizar recursos y el importe se pueda estimar de forma fiable.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20435",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-15",
        "titulo": "Norma de Valoracion 15ª — Ingresos extraordinarios",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Los ingresos extraordinarios se reconoceran cuando sea probable que se produzcan flujos economicos futuros y puedan medirse de forma fiable.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20436",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-16",
        "titulo": "Norma de Valoracion 16ª — Coste de las ventas",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "El coste de las ventas se determinara incluyendo el coste de adquisicion o produccion de los bienes vendidos mas los costes directamente atribuibles a la venta.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20437",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-17",
        "titulo": "Norma de Valoracion 17ª — Arrendamientos financieros",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Los arrendamientos financieros se reconoceran como un activo y un pasivo por el valor razonable del activo arrendado o, si es menor, por el valor actual de los pagos minimos del arrendamiento.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20438",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-18",
        "titulo": "Norma de Valoracion 18ª — Subvenciones oficiales de capital",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las subvenciones oficiales de capital se presentaran como un ingreso diferido en el pasivo y se imputaran al resultado de forma sistematica durante la vida util del activo.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20439",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-19",
        "titulo": "Norma de Valoracion 19ª — Operaciones de fusion y escision",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "Las operaciones de fusion y escision se registraran aplicando el metodo de la uniion de participaciones, valorando los activos y pasivos adquiridos a valor razonable.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20440",
        "vigente": True,
    },
    {
        "codigo": "mc-nv-20",
        "titulo": "Norma de Valoracion 20ª — Impuesto sobre beneficios",
        "tipo": "norma_valoracion",
        "anio": 2007,
        "texto": "El impuesto sobre beneficios se calculara aplicando el tipo impositivo vigente a la base imponible, reconociendo diferencias temporarias entre el valor contable y fiscal de los activos y pasivos.",
        "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20441",
        "vigente": True,
    },
]


def seed():
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    for r in MARCO_RECORDS:
        cur.execute(
            """
            INSERT INTO pgc_marco (id, codigo, titulo, tipo, anio, texto, url_boe, vigente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                anio = EXCLUDED.anio,
                texto = EXCLUDED.texto,
                url_boe = EXCLUDED.url_boe,
                vigente = EXCLUDED.vigente
            """,
            (str(uuid.uuid5(uuid.NAMESPACE_DNS, r["codigo"])),
             r["codigo"], r["titulo"], r["tipo"], r["anio"],
             r["texto"], r["url_boe"], r["vigente"]),
        )

    conn.commit()
    print(f"Seeded {len(MARCO_RECORDS)} pgc_marco records")
    conn.close()


if __name__ == "__main__":
    seed()
