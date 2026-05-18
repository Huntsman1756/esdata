BEGIN;

WITH campana AS (
    SELECT mc.id AS campana_id
    FROM modelo_campana mc
    JOIN aeat_modelo am ON am.id = mc.modelo_id
    WHERE am.codigo = '289'
    ORDER BY mc.id DESC
    LIMIT 1
),
rows_to_upsert AS (
    SELECT
        campana.campana_id,
        'XSD:' || data.path AS codigo,
        replace(data.path, '/', ' > ') AS etiqueta,
        data.descripcion,
        data.orden
    FROM campana
    CROSS JOIN (
        VALUES
        ('MessageSpec/SendingEntityIN', 'NIF o identificador de la entidad declarante en cabecera del mensaje CRS.', 1),
        ('MessageSpec/TransmittingCountry', 'Pais transmisor del mensaje CRS; para Modelo 289, ES.', 2),
        ('MessageSpec/ReceivingCountry', 'Pais receptor del mensaje CRS.', 3),
        ('MessageSpec/MessageType', 'Tipo de mensaje: CRS.', 4),
        ('MessageSpec/MessageTypeIndic', 'Indicador CRS701 nueva presentacion, CRS702 correccion, CRS703 cancelacion, CRS704 NilReport.', 5),
        ('MessageSpec/ReportingPeriod', 'Ejercicio declarado o periodo de reporte CRS.', 6),
        ('MessageSpec/Timestamp', 'Fecha y hora de generacion del mensaje.', 7),
        ('ReportingFI/IN', 'Identificador fiscal de la institucion financiera declarante.', 8),
        ('ReportingFI/ResCountryCode', 'Pais de residencia de la institucion financiera declarante.', 9),
        ('ReportingFI/Name', 'Denominacion de la institucion financiera declarante.', 10),
        ('ReportingFI/Address/CountryCode', 'Pais de la direccion de la institucion financiera declarante.', 11),
        ('ReportingFI/DocSpec/DocTypeIndic', 'Tipo documental OECD0/OECD1/OECD2/OECD3 de la ReportingFI.', 12),
        ('ReportingFI/DocSpec/DocRefId', 'Identificador unico del documento ReportingFI.', 13),
        ('AccountReport/DocSpec/DocTypeIndic', 'Tipo documental del bloque AccountReport.', 14),
        ('AccountReport/DocSpec/DocRefId', 'Identificador unico del documento AccountReport.', 15),
        ('AccountReport/AccountNumber', 'Numero de cuenta financiera reportada.', 16),
        ('AccountReport/AccountClosed', 'Indicador booleano de cuenta cerrada.', 17),
        ('AccountReport/AccountBalance', 'Saldo o valor de la cuenta financiera.', 18),
        ('AccountReport/Payment/Type', 'Tipo de pago CRS: dividendos, intereses, producto bruto, otros o seguros.', 19),
        ('AccountReport/Payment/AmntEndsmnt', 'Importe del pago reportado.', 20),
        ('AccountHolder/AcctHolderType', 'Tipo de titular CRS: individual, NFE pasiva, NFE activa, institucion financiera o exenta.', 21),
        ('AccountHolder/Individual', 'Datos de persona fisica titular de la cuenta.', 22),
        ('AccountHolder/Organisation', 'Datos de entidad titular de la cuenta.', 23),
        ('AccountHolder/ResCountryCode', 'Pais de residencia fiscal del titular.', 24),
        ('AccountHolder/TIN', 'Identificador fiscal del titular en su jurisdiccion de residencia.', 25),
        ('ControllingPerson/Individual', 'Datos de la persona que ejerce el control sobre una NFE pasiva.', 26),
        ('ControllingPerson/CtrlgPersonType', 'Tipo de persona de control CRS.', 27)
    ) AS data(path, descripcion, orden)
)
INSERT INTO modelo_casilla (
    campana_id,
    codigo,
    etiqueta,
    descripcion,
    tipo_casilla,
    orden,
    activa
)
SELECT
    campana_id,
    codigo,
    etiqueta,
    descripcion,
    'diseno_registro_xsd_campo',
    orden,
    TRUE
FROM rows_to_upsert
ON CONFLICT (campana_id, codigo) DO UPDATE SET
    etiqueta = EXCLUDED.etiqueta,
    descripcion = EXCLUDED.descripcion,
    tipo_casilla = EXCLUDED.tipo_casilla,
    orden = EXCLUDED.orden,
    activa = EXCLUDED.activa;

COMMIT;
