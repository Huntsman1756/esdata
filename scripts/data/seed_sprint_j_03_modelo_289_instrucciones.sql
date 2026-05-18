BEGIN;

WITH campana AS (
    SELECT mc.id AS campana_id
    FROM modelo_campana mc
    JOIN aeat_modelo am ON am.id = mc.modelo_id
    WHERE am.codigo = '289'
    ORDER BY mc.id DESC
    LIMIT 1
),
rows_to_insert AS (
    SELECT
        campana.campana_id,
        data.seccion,
        data.titulo,
        data.contenido,
        data.orden,
        data.source_url
    FROM campana
    CROSS JOIN (
        VALUES
        (
            'clasificacion',
            'Determinacion de Institucion Financiera Obligada',
            'Es IFO toda entidad que sea: (1) entidad de custodia, (2) entidad de deposito, (3) entidad de inversion, o (4) compania de seguros especifica. Base: RD 1021/2015 art. 1.',
            1,
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'clasificacion',
            'Cuenta financiera reportable',
            'Cuenta mantenida por persona o entidad residente fiscal en jurisdiccion reportable distinta de Espana. Incluye entidades pasivas con personas que ejercen el control residentes en jurisdiccion reportable. Base: RD 1021/2015, reglas de diligencia debida CRS.',
            2,
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'plazo',
            'Plazo de presentacion Modelo 289',
            'Presentacion anual del 1 de enero al 31 de mayo de cada ano respecto del ano natural anterior. Presentacion por servicio web AEAT. Base: Orden HAC/1150/2024 y procedimiento AEAT GI42.',
            3,
            'https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml'
        ),
        (
            'procedimiento',
            'Declaracion negativa NilReport',
            'Si la Institucion Financiera Obligada no mantiene cuentas reportables en el ejercicio, debe presentar declaracion negativa mediante MessageTypeIndic CRS704 (NilReport). Fuente: guia tecnica AEAT CRS Modelo 289 v2.6.',
            4,
            'https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf'
        ),
        (
            'procedimiento',
            'Correccion y cancelacion de declaraciones',
            'Nueva presentacion: CRS701. Correccion: CRS702 con CorrDocRefId que referencia el DocRefId original. Cancelacion: CRS703. Fuente: guia tecnica AEAT CRS Modelo 289 v2.6.',
            5,
            'https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf'
        )
    ) AS data(seccion, titulo, contenido, orden, source_url)
)
INSERT INTO modelo_instruccion (
    campana_id,
    seccion,
    titulo,
    contenido,
    orden,
    texto,
    source_url,
    capture_date
)
SELECT
    campana_id,
    seccion,
    titulo,
    contenido,
    orden,
    contenido,
    source_url,
    CURRENT_DATE
FROM rows_to_insert r
WHERE NOT EXISTS (
    SELECT 1
    FROM modelo_instruccion mi
    WHERE mi.campana_id = r.campana_id
      AND mi.titulo = r.titulo
);

COMMIT;
