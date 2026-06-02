"""load modelo 190 perception subkeys

Revision ID: 20260602_0113_aeat_190_subclaves_percepcion
Revises: 20260602_0112_modelo_clave_hierarchy_schema
Create Date: 2026-06-02

Revision 0112 added parent_id/nivel to modelo_clave. This revision loads the
official Modelo 190 2025 subclave catalogue as level-2 rows under the existing
main perception keys. It does not change campaign assertion, profile
obligations, or the A-L parent keys.
"""

from __future__ import annotations

from collections import Counter

import sqlalchemy as sa

from alembic import op

revision = "20260602_0113_aeat_190_subclaves_percepcion"
down_revision = "20260602_0112_modelo_clave_hierarchy_schema"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
DR_190_2025_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
    "DR_100_199/archivos_25/DISENOS_LOGICOS_190_2025.pdf"
)
DR_190_2025_HASH = "a7d1092f78620431812354e560a5146a3ae244e0aed69d9d58c353370ba0134d"
DR_190_2025_LENGTH = 1110488

SUBCLAVE_COUNTS = {
    "B": 5,
    "C": 9,
    "E": 4,
    "F": 7,
    "G": 8,
    "H": 4,
    "I": 3,
    "K": 5,
    "L": 32,
}

EXPECTED_CODES = {
    "B": ["01", "02", "03", "04", "99"],
    "C": ["01", "02", "03", "04", "05", "06", "07", "08", "09"],
    "E": ["01", "02", "03", "04"],
    "F": ["01", "02", "03", "04", "05", "06", "07"],
    "G": ["01", "02", "03", "04", "05", "06", "07", "08"],
    "H": ["01", "02", "03", "04"],
    "I": ["01", "02", "03"],
    "K": ["01", "02", "03", "04", "05"],
    "L": [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "99",
    ],
}

NOISE_MARKERS = (
    "Modelo 190",
    "Declaracion Informativa",
    "Agencia Tributaria",
    "Resumen anual",
    "POSICION",
    "Ejercicio 2025",
)

SUBCLAVES = [
    {
        "clave": "B",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones consistentes en pensiones y haberes pasivos de los regimenes de la Seguridad Social y Clases Pasivas, con excepcion de las que deban relacionarse bajo la subclave 02. Tambien se consignaran en esta subclave las percepciones en concepto de incapacidad laboral abonadas directamente al trabajador por alguno de los regimenes publicos de la Seguridad Social o Clases Pasivas o, en su caso, por la respectiva Mutua Colaboradora con la Seguridad Social. Si dichas prestaciones son directamente abonadas por el empleador (en virtud del respectivo acuerdo de colaboracion con la Seguridad Social), se reflejaran en la clave A.",
    },
    {
        "clave": "B",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave en todas las percepciones de la clave B en las que el importe de las retenciones se haya determinado con arreglo al procedimiento especial previsto en el articulo 89.A del Reglamento del Impuesto.",
    },
    {
        "clave": "B",
        "codigo": "03",
        "descripcion": "Prestaciones percibidas por los beneficiarios de mutualidades generales obligatorias de funcionarios, colegios de huerfanos y entidades similares.",
    },
    {
        "clave": "B",
        "codigo": "04",
        "descripcion": "Prestaciones derivadas de Planes de Pensiones y otros Sistemas de Prevision Social a los que se refiere el articulo 17.2.a) de la Ley 35/2006, de 28 de noviembre.",
    },
    {
        "clave": "B",
        "codigo": "99",
        "descripcion": "Resto de prestaciones de la Clave B distintas de las que deban relacionarse bajo las subclaves anteriores.",
    },
    {
        "clave": "C",
        "codigo": "01",
        "descripcion": "Prestaciones por desempleo. Se incluiran en esta subclave las prestaciones por desempleo que, debiendo relacionarse en el modelo 190, sean distintas de las especificamente senaladas en las subclaves siguientes.",
    },
    {
        "clave": "C",
        "codigo": "02",
        "descripcion": "Prestaciones por desempleo ERE. Se consignaran en esta subclave las prestaciones por desempleo satisfechas vinculadas a la normativa reguladora de los expedientes de regulacion de empleo (ERE).",
    },
    {
        "clave": "C",
        "codigo": "03",
        "descripcion": "Prestaciones por desempleo ERTE. Se consignaran en esta subclave las prestaciones por desempleo satisfechas vinculadas a un expediente de regulacion temporal de empleo (ERTE).",
    },
    {
        "clave": "C",
        "codigo": "04",
        "descripcion": "Prestacion por cese de actividad de trabajadores autonomos. Se consignaran en esta subclave las prestaciones por cese de actividad (de caracter extraordinario o no) satisfechas a trabajadores autonomos.",
    },
    {
        "clave": "C",
        "codigo": "05",
        "descripcion": "Subsidios por desempleo. Se consignaran en esta subclave los diferentes subsidios satisfechos, en su modalidad no contributiva, tales como los subsidios por cotizacion insuficiente, subsidios para mayores de 45 o 52 anos, para emigrantes retornados, el subsidio extraordinario por desempleo y otros subsidios de caracter no contributivo, a excepcion de la renta activa de insercion, que se reflejara en la subclave 06 siguiente.",
    },
    {
        "clave": "C",
        "codigo": "06",
        "descripcion": "Renta activa de insercion. Ayuda economica satisfecha vinculada a la realizacion de las acciones en materia de politicas activas de empleo que no conlleven retribuciones salariales.",
    },
    {
        "clave": "C",
        "codigo": "07",
        "descripcion": "Otras prestaciones de caracter contributivo. Se consignaran en esta subclave el resto de las prestaciones, o ayudas de caracter contributivo satisfechas, que no deban reflejarse en las subclaves anteriores.",
    },
    {
        "clave": "C",
        "codigo": "08",
        "descripcion": "Otras prestaciones de caracter no contributivo. Se consignaran en esta subclave el resto de las prestaciones, subsidios o ayudas de caracter no contributivo satisfechas, que no deban reflejarse en las subclaves anteriores.",
    },
    {
        "clave": "C",
        "codigo": "09",
        "descripcion": "Supuestos de percepcion en el ejercicio de prestaciones de mas de uno de los tipos anteriores por el mismo perceptor.",
    },
    {
        "clave": "E",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave unicamente cuando el Consejero o Administrador este incluido en el regimen general de la Seguridad Social como trabajador asimilado a trabajadores por cuenta ajena, y los rendimientos percibidos no deban reflejarse en la subclave 02.",
    },
    {
        "clave": "E",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave unicamente cuando el Consejero o Administrador este incluido en el regimen general de la Seguridad Social como trabajador asimilado a trabajadores por cuenta ajena, y los rendimientos procedan de entidades cuyo importe neto de la cifra de negocios del ultimo periodo impositivo finalizado con anterioridad al pago de los rendimientos sea inferior a 100.000 euros.",
    },
    {
        "clave": "E",
        "codigo": "03",
        "descripcion": "Se consignara esta subclave unicamente cuando el Consejero o Administrador este incluido en el regimen especial de la Seguridad Social de trabajadores autonomos, y los rendimientos procedan de entidades cuyo importe neto de la cifra de negocios del ultimo periodo impositivo finalizado con anterioridad al pago de los rendimientos sea inferior a 100.000 euros.",
    },
    {
        "clave": "E",
        "codigo": "04",
        "descripcion": "Se consignara esta subclave en todas las percepciones de la clave E distintas de las que deban relacionarse bajo las subclaves 01, 02 y 03.",
    },
    {
        "clave": "F",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a alguno de los premios literarios, cientificos o artisticos no exentos del Impuesto a que se refiere el articulo 12.1, letra g), del Reglamento del Impuesto.",
    },
    {
        "clave": "F",
        "codigo": "02",
        "descripcion": "Rendimientos del trabajo derivados de impartir cursos, conferencias, coloquios y similares.",
    },
    {
        "clave": "F",
        "codigo": "03",
        "descripcion": "Rendimientos del trabajo derivados de la elaboracion de obras literarias, artisticas o cientificas a los que resulte aplicable el tipo de retencion establecido con caracter general en el articulo 101.3 de la Ley del Impuesto.",
    },
    {
        "clave": "F",
        "codigo": "04",
        "descripcion": "Rendimientos del trabajo derivados de la elaboracion de obras literarias, artisticas o cientificas a los que resulte aplicable el tipo de retencion reducido establecido en el articulo 101.3 de la Ley del Impuesto.",
    },
    {
        "clave": "F",
        "codigo": "05",
        "descripcion": "Rendimientos derivados de la propiedad intelectual, cuando tengan la consideracion de rendimientos del trabajo, a los que sea aplicable el tipo general establecido en el articulo 101.9 de la ley del Impuesto.",
    },
    {
        "clave": "F",
        "codigo": "06",
        "descripcion": "Rendimientos derivados de la propiedad intelectual, cuando tengan la consideracion de rendimientos del trabajo, a los que sea aplicable el tipo de retencion reducido establecido en el articulo 101.9 de la Ley del Impuesto.",
    },
    {
        "clave": "F",
        "codigo": "07",
        "descripcion": "Anticipos a cuenta derivados de la cesion de la explotacion de los derechos de autor, cuando tales anticipos tengan la consideracion de rendimientos del trabajo, que se vayan a devengar a lo largo de varios anos.",
    },
    {
        "clave": "G",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion establecido con caracter general en el articulo 95.1 del Reglamento del Impuesto.",
    },
    {
        "clave": "G",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion especifico establecido en el citado articulo del Reglamento del Impuesto para los rendimientos satisfechos a recaudadores municipales, mediadores de seguros que utilicen los servicios de auxiliares externos y delegados comerciales de la entidad publica empresarial Loterias y Apuestas del Estado.",
    },
    {
        "clave": "G",
        "codigo": "03",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion reducido establecido en el articulo 95.1 del Reglamento del Impuesto para los rendimientos satisfechos a contribuyentes que inicien el ejercicio de actividades profesionales, tanto en el periodo impositivo en que se produzca dicho inicio como en los dos siguientes.",
    },
    {
        "clave": "G",
        "codigo": "04",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion especifico establecido en la letra d) del articulo 95.1 del Reglamento del Impuesto.",
    },
    {
        "clave": "G",
        "codigo": "05",
        "descripcion": "Rendimientos derivados de la propiedad intelectual, a los que resulte aplicable el tipo general de retencion previsto en el articulo 101.9 de la Ley del Impuesto.",
    },
    {
        "clave": "G",
        "codigo": "06",
        "descripcion": "Rendimientos derivados de la propiedad intelectual, a los que resulte aplicable el tipo de retencion reducido previsto en el articulo 101.9 de la Ley del Impuesto.",
    },
    {
        "clave": "G",
        "codigo": "07",
        "descripcion": "Anticipos a cuenta derivados de la cesion de la explotacion de derechos de autor, cuando tales anticipos tengan la consideracion de rendimientos de actividades profesionales, que se vayan a devengar a lo largo de varios anos.",
    },
    {
        "clave": "G",
        "codigo": "08",
        "descripcion": "Rendimientos derivados de la cesion del derecho a la explotacion de la imagen. Se consignara esta subclave cuando las percepciones satisfechas por dicha cesion tengan para su perceptor la calificacion de rendimientos derivados de su actividad profesional.",
    },
    {
        "clave": "H",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion establecido con caracter general en el articulo 95.4.2.o del Reglamento del Impuesto.",
    },
    {
        "clave": "H",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones a las que resulte aplicable el tipo de retencion especifico establecido en el articulo 95.4.1.o del Reglamento del Impuesto para los rendimientos que sean contraprestacion de actividades ganaderas de engorde de porcino y avicultura.",
    },
    {
        "clave": "H",
        "codigo": "03",
        "descripcion": "Se consignara esta subclave cuando las percepciones satisfechas sean contraprestacion de las actividades forestales a que se refiere el articulo 95.5 del Reglamento del Impuesto.",
    },
    {
        "clave": "H",
        "codigo": "04",
        "descripcion": "Se consignara esta subclave cuando las percepciones satisfechas sean contraprestacion de las actividades economicas en estimacion objetiva recogidas en el articulo 95.6.2.o del Reglamento del Impuesto.",
    },
    {
        "clave": "I",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones satisfechas por la persona o entidad declarante en concepto de rendimientos procedentes de la cesion del derecho a la explotacion del derecho de imagen.",
    },
    {
        "clave": "I",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones derivadas de la propiedad intelectual, a las que sea aplicable el tipo de retencion establecido con caracter general en el articulo 101.9 de la Ley del Impuesto.",
    },
    {
        "clave": "I",
        "codigo": "03",
        "descripcion": "Se consignara esta subclave cuando se trate de percepciones satisfechas por la persona o entidad declarante por cualquier otro de los conceptos a que se refiere el articulo 75.2, letra b) del Reglamento del Impuesto.",
    },
    {
        "clave": "K",
        "codigo": "01",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a premios que, por su importe, se encuentren sometidos a retencion, derivados de por la participacion en juegos, rifas o combinaciones aleatorias sin fines publicitarios, enmarcables en la definicion del concepto de \"juego\" que se contiene en el articulo 3.a) de la Ley 13/2011, de 27 de mayo, de regulacion del juego, caracterizado por arriesgarse cantidades de dinero u otros elementos patrimoniales a cambio de la posibilidad de obtener un premio o ganancia. Estos premios se consignaran por su importe integro, sin perjuicio del derecho del perceptor a minorar su importe en las perdidas en el juego obtenidas en el mismo periodo impositivo, en los terminos establecidos en el articulo 35.5.d) de la Ley del impuesto.",
    },
    {
        "clave": "K",
        "codigo": "02",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a ganancias patrimoniales obtenidas por los vecinos como consecuencia de aprovechamientos forestales en montes publicos.",
    },
    {
        "clave": "K",
        "codigo": "03",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a premios que, por su importe, se encuentren sometidos a retencion, derivados de por la participacion en concursos o combinaciones aleatorias con fines publicitarios, en los que no se realice un desembolso economico por su participacion en ellos, y por tanto, no enmarcables en la definicion del concepto de \"juego\" que se contiene en el articulo 3.a) de la Ley 13/2011, de 27 de mayo, de regulacion del juego. Se incluyen aqui premios derivados de programas desarrollados en medios de comunicacion, asi como los derivados de combinaciones aleatorias con fines publicitarios y promocionales definidas en el art. 3.i) de la Ley 13/2011.",
    },
    {
        "clave": "K",
        "codigo": "04",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a premios que, por su importe, no se encuentren sometidos a retencion, derivados de la participacion en juegos, rifas o combinaciones aleatorias sin fines publicitarios, enmarcables en la definicion del concepto de \"juego\" que se contiene en el articulo 3.a) de la Ley 13/2011, de 27 de mayo, de regulacion del juego, caracterizado por arriesgarse cantidades de dinero u otros elementos patrimoniales a cambio de la posibilidad de obtener un premio o ganancia. Estos premios se consignaran por su importe integro, sin perjuicio del derecho del perceptor a minorar su importe en las perdidas en el juego obtenidas en el mismo periodo impositivo, en los terminos establecidos en el articulo 35.5.d) de la Ley del impuesto.",
    },
    {
        "clave": "K",
        "codigo": "05",
        "descripcion": "Se consignara esta subclave cuando las percepciones correspondan a premios que, por su importe, no se encuentren sometidos a retencion, derivados de la participacion en concursos o combinaciones aleatorias con fines publicitarios, en los que no se realice un desembolso economico por su participacion en ellos, y por tanto, no enmarcables en la definicion del concepto de \"juego\" que se contiene en el articulo 3.a) de la Ley 13/2011, de 27 de mayo, de regulacion del juego. Se incluyen aqui premios derivados de programas desarrollados en medios de comunicacion, asi como los derivados de combinaciones aleatorias con fines publicitarios y promocionales definidas en el art. 3.i) de la Ley 13/2011.",
    },
    {
        "clave": "L",
        "codigo": "01",
        "descripcion": "Dietas y asignaciones para gastos de viaje exceptuadas de gravamen conforme a lo previsto en el articulo 9 del Reglamento del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "02",
        "descripcion": "Prestaciones publicas extraordinarias por actos de terrorismo y pensiones derivadas de medallas y condecoraciones concedidas por actos de terrorismo que esten exentas en virtud de lo establecido en la letra a) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "03",
        "descripcion": "Ayudas percibidas por los afectados por el virus de la inmunodeficiencia humana a que se refiere la letra b) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "04",
        "descripcion": "Pensiones por lesiones o mutilaciones sufridas con ocasion o como consecuencia de la Guerra Civil 1936/1939 que esten exentas en virtud de lo establecido en la letra c) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "05",
        "descripcion": "Indemnizaciones por despido o cese del trabajador que esten exentas en virtud de lo establecido en la letra e) del articulo 7 de la Ley del Impuesto y en el articulo 1 del Reglamento.",
    },
    {
        "clave": "L",
        "codigo": "06",
        "descripcion": "Prestaciones por incapacidad permanente absoluta o gran invalidez que esten exentas conforme a lo establecido en la letra f) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "07",
        "descripcion": "Pensiones por inutilidad o incapacidad permanente del regimen de clases pasivas a que se refiere la letra g) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "08",
        "descripcion": "Prestaciones, pensiones y haberes pasivos que esten exentos en virtud de lo establecido en la letra h) del articulo 7 de la Ley del Impuesto, sin incluir en esta subclave las prestaciones publicas por maternidad o paternidad exentas que deban consignarse en la subclave 27.",
    },
    {
        "clave": "L",
        "codigo": "09",
        "descripcion": "Prestaciones economicas de instituciones publicas con motivo del acogimiento de personas con discapacidad, mayores de sesenta y cinco anos o menores y ayudas economicas otorgadas por instituciones publicas a personas con discapacidad o mayores de sesenta y cinco anos para financiar su estancia en residencias o centros de dia, que esten exentas en virtud de lo establecido en la letra i) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "10",
        "descripcion": "Becas que esten exentas en virtud de lo establecido en la letra j) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "11",
        "descripcion": "Premios literarios, artisticos o cientificos relevantes, asi como los premios Principe de Asturias, que esten exentos en virtud de lo establecido en la letra l) del articulo 7 de la Ley del Impuesto y en el articulo 3 del Reglamento.",
    },
    {
        "clave": "L",
        "codigo": "12",
        "descripcion": "Ayudas economicas a los deportistas de alto nivel que esten exentas en virtud de lo establecido en la letra m) del articulo 7 de la Ley del Impuesto y en el articulo 4 del Reglamento.",
    },
    {
        "clave": "L",
        "codigo": "13",
        "descripcion": "Prestaciones por desempleo abonadas en la modalidad de pago unico que esten exentas en virtud de lo establecido en la letra n) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "14",
        "descripcion": "Gratificaciones extraordinarias satisfechas por el Estado espanol por la participacion en misiones internacionales de paz o humanitarias que esten exentas en virtud de lo establecido en la letra o) del articulo 7 de la Ley del Impuesto y en el articulo 5 del Reglamento.",
    },
    {
        "clave": "L",
        "codigo": "15",
        "descripcion": "Rendimientos del trabajo percibidos por trabajos realizados en el extranjero que esten exentos en virtud de lo establecido en la letra p) del articulo 7 de la Ley del Impuesto y en el articulo 6 del Reglamento.",
    },
    {
        "clave": "L",
        "codigo": "16",
        "descripcion": "Prestaciones por entierro o sepelio que esten exentas en virtud de lo establecido en la letra r) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "17",
        "descripcion": "Ayudas a favor de las personas que hayan desarrollado la hepatitis C como consecuencia de haber recibido tratamiento en el ambito del sistema sanitario publico, que esten exentas en virtud de lo establecido en la letra s) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "18",
        "descripcion": "Prestaciones en forma de renta obtenidas por las personas con discapacidad correspondientes a aportaciones a sistemas de prevision social constituidos en favor de las mismas, que esten exentas en virtud de lo establecido en la letra w) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "19",
        "descripcion": "Prestaciones economicas publicas vinculadas al servicio para cuidados en el entorno familiar y de asistencia personalizada que se derivan de la Ley de promocion de la autonomia personal y atencion a las personas en situacion de dependencia, que esten exentas en virtud de lo establecido en la letra x) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "20",
        "descripcion": "Prestaciones y ayudas familiares publicas vinculadas al nacimiento, adopcion, acogimiento o cuidado de hijos menores, que esten exentas en virtud de lo establecido en la letra z) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "21",
        "descripcion": "Rendimientos del trabajo de la persona titular de un patrimonio protegido a que se refiere la disposicion adicional decimoctava de la Ley del Impuesto, derivados de las aportaciones a dichos patrimonios protegidos, que esten exentos en virtud de lo establecido en el segundo parrafo de la letra w) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "22",
        "descripcion": "Ayudas establecidas por Comunidades Autonomas o por entidades locales para atender, con arreglo a su normativa, a colectivos en riesgo de exclusion social, situaciones de emergencia social, necesidades habitacionales de personas sin recursos o necesidades de alimentacion, escolarizacion y demas necesidades basicas de menores o personas con discapacidad cuando ellos y las personas a su cargo, carezcan de medios economicos suficientes, que esten exentas en virtud de lo establecido en el primer parrafo de la letra y) del articulo 7 de la Ley del Impuesto, sin incluir en esta subclave las prestaciones economicas establecidas por las CC.AA. en concepto de renta minima de insercion que deban consignarse en la subclave 28.",
    },
    {
        "clave": "L",
        "codigo": "23",
        "descripcion": "Ayudas concedidas a victimas de delitos violentos a que se refiere la Ley 35/1995, de 11 de diciembre, de ayudas y asistencia a las victimas de delitos violentos y contra la libertad sexual, ayudas previstas en la Ley Organica 1/2004, de 28 de diciembre, de Medidas de Proteccion Integral contra la Violencia de Genero, y demas ayudas publicas satisfechas a victimas de violencia de genero por tal condicion, que esten exentas en virtud de lo establecido en el segundo parrafo de la letra y) del articulo 7 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "24",
        "descripcion": "Rendimientos del trabajo en especie exentos de acuerdo con lo dispuesto en las letras a) b), c), y e) del articulo 42.3 de la Ley del Impuesto, sin incluir en esta subclave los rendimientos del trabajo en especie exentos que deban consignarse en la subclave 25 siguiente. No obstante, respecto de los rendimientos del trabajo exentos previstos en las letras a) y b) del articulo 42.3 de la Ley del Impuesto que se incluyan en esta subclave 24, unicamente se exigiran datos cuando para la prestacion de los servicios se utilicen formulas indirectas.",
    },
    {
        "clave": "L",
        "codigo": "25",
        "descripcion": "Rendimientos del trabajo en especie exentos de acuerdo con lo dispuesto en la letra b) del articulo 42.3 de la Ley del Impuesto, exclusivamente referidos a aquellos destinados por las empresas o empleadores a prestar el servicio de primer ciclo de educacion infantil a los hijos de sus trabajadores. No obstante, respecto de los rendimientos del trabajo exentos previstos en esta subclave, unicamente se exigiran datos cuando para la prestacion de los servicios se utilicen formulas indirectas.",
    },
    {
        "clave": "L",
        "codigo": "26",
        "descripcion": "Rendimientos del trabajo en especie exentos de acuerdo con lo dispuesto en la letra d) del articulo 42.3 de la Ley del Impuesto.",
    },
    {
        "clave": "L",
        "codigo": "27",
        "descripcion": "Prestaciones publicas por maternidad o paternidad exentas del IRPF.",
    },
    {
        "clave": "L",
        "codigo": "28",
        "descripcion": "Prestaciones economicas establecidas por las Comunidades Autonomas en concepto de renta minima de insercion para garantizar recursos economicos de subsistencia a las personas que carezcan de ellos y que esten exentas en virtud de lo establecido en el primer parrafo de la letra y) del articulo 7 de la Ley del Impuesto, sin incluir en esta subclave el resto de ayudas exentas establecidas en este primer parrafo de la letra y) que deban consignarse en la subclave 22 anterior.",
    },
    {
        "clave": "L",
        "codigo": "29",
        "descripcion": "Prestacion economica de la Seguridad Social correspondiente al Ingreso Minimo Vital.",
    },
    {
        "clave": "L",
        "codigo": "30",
        "descripcion": "Rendimientos del trabajo en especie exentos previstos en la letra f) del articulo 42.3 de la Ley del Impuesto, derivados de la entrega a los trabajadores en activo, de forma gratuita o por precio inferior al normal de mercado, de acciones o participaciones de la propia empresa o de otras empresas del grupo de sociedades, que no deban incluirse en la subclave 31 siguiente.",
    },
    {
        "clave": "L",
        "codigo": "31",
        "descripcion": "Rendimientos del trabajo en especie exentos previstos en la letra f) del articulo 42.3 de la Ley del Impuesto, derivados de la entrega de acciones o participaciones concedidas a los trabajadores de una empresa emergente a las que se refiere la Ley 28/2022, de 21 de diciembre, de fomento del ecosistema de las empresas emergentes.",
    },
    {
        "clave": "L",
        "codigo": "99",
        "descripcion": "Otras rentas exentas. Se incluiran en esta subclave las rentas exentas del Impuesto sobre la Renta de las Personas Fisicas que, debiendo relacionarse en el modelo 190, sean distintas de las especificamente senaladas en las subclaves anteriores.",
    },
]


def _validate_subclave_constant() -> None:
    counts = Counter(row["clave"] for row in SUBCLAVES)
    if counts != SUBCLAVE_COUNTS:
        raise RuntimeError(f"Modelo 190 subclave count mismatch: {counts!r}")

    seen = set()
    for row in SUBCLAVES:
        key = (row["clave"], row["codigo"])
        if key in seen:
            raise RuntimeError(f"Duplicate Modelo 190 subclave: {key!r}")
        seen.add(key)
        if row["codigo"] not in EXPECTED_CODES[row["clave"]]:
            raise RuntimeError(f"Unexpected Modelo 190 subclave code: {key!r}")
        if not row["descripcion"].strip():
            raise RuntimeError(f"Empty Modelo 190 subclave description: {key!r}")
        if any(marker in row["descripcion"] for marker in NOISE_MARKERS):
            raise RuntimeError(f"PDF header/footer noise in Modelo 190 subclave: {key!r}")


def _campaign_id(bind) -> int:
    campana_id = bind.execute(
        sa.text(
            """
            SELECT mc.id
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo = '190'
              AND mc.campana = '2025'
              AND mc.activo = true
            """
        )
    ).scalar()
    if campana_id is None:
        raise RuntimeError("Active Modelo 190 campaign 2025 not found")
    return int(campana_id)


def _parent_ids(bind, campana_id: int) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            """
            SELECT codigo, id
            FROM modelo_clave
            WHERE campana_id = :campana_id
              AND parent_id IS NULL
              AND nivel = 1
              AND COALESCE(tipo, tipo_clave) = 'CLAVE_PERCEPCION'
              AND codigo IN ('B','C','E','F','G','H','I','K','L')
            """
        ),
        {"campana_id": campana_id},
    ).mappings()
    parents = {str(row["codigo"]): int(row["id"]) for row in rows}
    missing = set(SUBCLAVE_COUNTS) - set(parents)
    if missing:
        raise RuntimeError(f"Missing Modelo 190 parent perception keys: {sorted(missing)!r}")
    return parents


def _common(campana_id: int) -> dict[str, object]:
    return {
        "campana_id": campana_id,
        "source_url": DR_190_2025_URL,
        "source_hash": DR_190_2025_HASH,
        "capture_date": CAPTURE_DATE,
    }


def upgrade() -> None:
    _validate_subclave_constant()
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    parents = _parent_ids(bind, campana_id)
    common = _common(campana_id)

    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET content_length = COALESCE(content_length, :content_length),
                metadata = COALESCE(metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'capture_date', CAST(:capture_date AS text),
                        'evidence_scope_subclaves', 'modelo_190_subclaves_77'
                    )
            WHERE campana_id = :campana_id
              AND tipo_recurso = 'diseno_registro'
              AND url_recurso = :source_url
              AND sha256_contenido = :source_hash
            """
        ),
        {**common, "content_length": DR_190_2025_LENGTH},
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_clave
            WHERE campana_id = :campana_id
              AND nivel = 2
              AND COALESCE(tipo, tipo_clave) = 'SUBCLAVE_PERCEPCION'
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        common,
    )

    for row in SUBCLAVES:
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_clave (
                    campana_id, parent_id, nivel, codigo, etiqueta, descripcion,
                    tipo_clave, tipo, criterio_aplicacion,
                    source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :parent_id, 2, :codigo, :etiqueta, :descripcion,
                    'SUBCLAVE_PERCEPCION', 'SUBCLAVE_PERCEPCION', :descripcion,
                    :source_url, :source_hash, :capture_date
                )
                """
            ),
            {
                **common,
                "parent_id": parents[row["clave"]],
                "codigo": row["codigo"],
                "etiqueta": f"Clave {row['clave']} subclave {row['codigo']}",
                "descripcion": row["descripcion"],
            },
        )

    loaded = bind.execute(
        sa.text(
            """
            WITH active_campaign AS (
                SELECT mc.id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '190'
                  AND mc.campana = '2025'
                  AND mc.activo = true
            ),
            subclaves AS (
                SELECT p.codigo AS clave, c.codigo, c.descripcion
                FROM modelo_clave c
                JOIN modelo_clave p ON p.id = c.parent_id
                WHERE c.campana_id IN (SELECT id FROM active_campaign)
                  AND c.nivel = 2
                  AND p.nivel = 1
                  AND COALESCE(c.tipo, c.tipo_clave) = 'SUBCLAVE_PERCEPCION'
                  AND COALESCE(p.tipo, p.tipo_clave) = 'CLAVE_PERCEPCION'
                  AND c.source_url = :source_url
                  AND c.source_hash = :source_hash
                  AND c.capture_date IS NOT NULL
            ),
            grouped AS (
                SELECT clave, COUNT(*) AS total, array_agg(codigo::text ORDER BY codigo::text) AS codes
                FROM subclaves
                GROUP BY clave
            )
            SELECT COUNT(*) = 77
               AND COUNT(*) FILTER (
                    WHERE descripcion IS NULL
                       OR btrim(descripcion) = ''
                       OR descripcion ~ '(Modelo 190|Declaracion Informativa|Agencia Tributaria|Resumen anual|POSICION|Ejercicio 2025)'
               ) = 0
               AND (
                    SELECT COUNT(*) = 9
                       AND COUNT(*) FILTER (WHERE clave='B' AND total=5 AND codes=ARRAY['01','02','03','04','99']) = 1
                       AND COUNT(*) FILTER (WHERE clave='C' AND total=9 AND codes=ARRAY['01','02','03','04','05','06','07','08','09']) = 1
                       AND COUNT(*) FILTER (WHERE clave='E' AND total=4 AND codes=ARRAY['01','02','03','04']) = 1
                       AND COUNT(*) FILTER (WHERE clave='F' AND total=7 AND codes=ARRAY['01','02','03','04','05','06','07']) = 1
                       AND COUNT(*) FILTER (WHERE clave='G' AND total=8 AND codes=ARRAY['01','02','03','04','05','06','07','08']) = 1
                       AND COUNT(*) FILTER (WHERE clave='H' AND total=4 AND codes=ARRAY['01','02','03','04']) = 1
                       AND COUNT(*) FILTER (WHERE clave='I' AND total=3 AND codes=ARRAY['01','02','03']) = 1
                       AND COUNT(*) FILTER (WHERE clave='K' AND total=5 AND codes=ARRAY['01','02','03','04','05']) = 1
                       AND COUNT(*) FILTER (WHERE clave='L' AND total=32 AND codes=ARRAY['01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','99']) = 1
                    FROM grouped
               )
            FROM subclaves
            """
        ),
        {"source_url": DR_190_2025_URL, "source_hash": DR_190_2025_HASH},
    ).scalar()
    if loaded is not True:
        raise RuntimeError("Modelo 190 subclave load did not satisfy COUNT(*) = 77")


def downgrade() -> None:
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    common = _common(campana_id)
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_clave
            WHERE campana_id = :campana_id
              AND nivel = 2
              AND COALESCE(tipo, tipo_clave) = 'SUBCLAVE_PERCEPCION'
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        common,
    )
    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET metadata = COALESCE(metadata, '{}'::jsonb) - 'evidence_scope_subclaves'
            WHERE campana_id = :campana_id
              AND tipo_recurso = 'diseno_registro'
              AND url_recurso = :source_url
              AND sha256_contenido = :source_hash
            """
        ),
        common,
    )
