#!/usr/bin/env python
"""LEGACY / NO AUTORITATIVO.

Seed manual curado de modelos AEAT para consulta fiscal.

No usar como flujo canonico productivo AEAT. La via canonica del repo MCP es:
1. `python scripts/seed-modelos.py --db-url <DATABASE_URL>`
2. `python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>`
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

MODELOS = [
    ("100", "Declaración de la Renta (IRPF)", "anual", "IRPF", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_100_autoliquidacion_irpf.html"),
    ("303", "IVA trimestral", "trimestral", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html"),
    ("300", "IVA mensual (recargo equivalencia)", "mensual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_300_autoliquidacion_ivarecargo_equivalencia.html"),
    ("200", "Impuesto sobre Sociedades", "anual", "IS", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/is/modelo_200_autoliquidacion_impuesto_sociedades.html"),
    ("115", "Retenciones e ingresos en cuenta (IRLS)", "mensual", "IRLS", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_115_declaracion_retenaciones_ingresos_cuenta.html"),
    ("123", "IRNR - Rendimientos sin residente", "trimestral", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_123_autoliquidacion_rendimientos_sin_residente.html"),
    ("124", "IRNR - Dividendos y rentas capital", "mensual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_124_autoliquidacion_retenciones_dividendos.html"),
     ("216", "IRNR - FactA a terceros (no residentes)", "mensual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_declaracion_facta.html"),
    ("296", "IRNR - Intereses y cánones", "mensual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_296_autoliquidacion_intereses_cánones.html"),
    ("347", "Operaciones con terceras personas (347)", "anual", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_347_declaracion_operaciones_con_terceras_personas.html"),
    ("349", "Factura Intracomunitaria (FactA)", "mensual", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_349_declaracion_operaciones_intracomunitarias.html"),
    ("036", "Información registros auxiliares (036)", "trimestral", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_036_registros_auxiliares.html"),
    ("130", "IVA - Cuotas repercutidas (130)", "trimestral", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_130_declaracion_trimestral_cuotas_repercutidas.html"),
    ("108", "Adquisiciones intracomunitarias de bienes", "trimestral", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_108_declaracion_adquisiciones_intracomunitarias_bienes.html"),
    ("304", "IVA - Entrega de bienes (304)", "trimestral", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_304_declaracion_entrega_bienes.html"),
    ("111", "Retribuciones al trabajador (IRPF)", "mensual", "IRPF", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_111_autoliquidacion_retribuciones_trabajadores.html"),
    ("116", "IRNR - Actividades economicas", "trimestral", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_116_autoliquidacion_actividades_economicas.html"),
    ("212", "IRNR - Dividendos y rentas capital (empresas)", "mensual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_212_autoliquidacion_dividendos_rentas_capital.html"),
    ("348", "Operaciones intracomunitarias de servicios", "mensual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_348_declaracion_operaciones_intracomunitarias_servicios.html"),
    ("394", "Resumen anual SII (facturas emitidas/ingresadas)", "anual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_394_resumen_anual_sii.html"),
    ("346", "Relacion de pagos intracomunitarios (SII)", "anual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_346_resumen_anual_pagos_intracomunitarios.html"),
    ("720", "Información de bienes en el extranjero", "anual", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_720_informacion_bienes_extranjero.html"),
    ("201", "Impuesto Sociedades — entidades no residentes", "anual", "IS", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/is/modelo_201_impuesto_sociedades_no_residentes.html"),
    ("430", "Lista de operaciones con aduanas (exportaciones)", "mensual", "estadistico", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/estadistica/modelo_430_listas_operaciones_comerciales.html"),
    ("431", "Lista de operaciones con aduanas (importaciones)", "mensual", "estadistico", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/estadistica/modelo_431_listas_operaciones_comerciales.html"),
    ("037", "Comunicacion de datos censales", "cuando-varia", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_037_comunicacion_datos_censales.html"),
    ("046", "Autoliquidacion tasa sede electronica", "evento", "tasa", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/tasas/modelo_046_autoliquidacion_tasa_sede.html"),
    ("092", "Determinacion del metodo de estimacion directa", "cuando-varia", "informacion", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_092_determinacion_metodo_estimacion.html"),
    ("114", "Retenciones e ingresos a cuenta — profesionales", "trimestral", "IRLS", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_114_autoliquidacion_retribuciones_profesionales.html"),
    ("190", "Remuneraciones totales — anual", "anual", "IRPF", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_190_retribuciones_anual.html"),
    ("878", "Relacion de pagos a proveedores no residentes", "anual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_878_relacion_pagos_proveedores.html"),
    ("269", "Autoliquidacion del Impuesto de Sociedades — tramo estatal", "trimestral", "IS", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/is/modelo_269_autoliquidacion_tramo_estatal.html"),
    ("380", "Facturas-Notas de credito intracomunitarias", "mensual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_380_facturas_notas_credito_intracomunitarias.html"),
    ("828", "Comunicacion de operaciones del art. 79.4 LIVA", "anual", "IVA", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_828_comunicacion_operaciones_art_79.html"),
    ("121", "IRNR — Actividades economicas (periodo anual)", "anual", "IRNR", "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_121_autoliquidacion_actividades_economicas_anual.html"),
]

INSTRUCCIONES = {
    "124": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidad que pague dividendos, intereses u otras rentas de capital a no residentes en España (residentes en UE o fuera de UE). Aplica a dividendos pagados a cualquier no residente, no solo intracomunitarios. Periodo: mensual. Plazo: primeros 20 días del mes siguiente. Si el día 20 es inhábil, se prorroga al primer hábil siguiente. Presentación: electrónica obligatoria vía Sede AEAT."),
        ("plazo", "Plazos y sanciones",
         "Plazo de presentación: mensual, primeros 20 días naturales del mes siguiente al periodo. Si el día 20 es inhábil: primer día hábil siguiente. Recargo voluntario: 5%. Recargo involuntario: 5-10%. Intereses de demora: TIE + 4%. Suspensión: depósito del 50% del autoliquidación o aval."),
        ("como-rellenar", "Cómo rellenar",
         "Sección 1: Datos identificativos (NIF, razón social, domicilio fiscal). Sección 2: Datos del beneficiario (NIF extranjero, país, tipo de rendimiento). Sección 3: Detalle de rendimientos del capital mobiliario - concepto (dividendos/intereses), importe bruto, tipo de retención, cuota retenida. Sección 4: Cálculo de la retención - base imponible x tipo retención. Sección 5: Cuentas contables afectadas. Clave 9: régimen de la operación (convenio doble tributación, tipo reducido)."),
    ],
    "216": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: cualquier entidad española que realice entregas de bienes o prestaciones de servicios a clientes no residentes en España (residentes en otro país de la UE o fuera de la UE). Incluye facturas a empresas o particulares en EE.UU., Latinoamérica, etc. No confundir con el Modelo 349: el 216 es para TODOS los no residentes, el 349 es SOLO para intracomunitarios (UE). Periodo: mensual. Plazo: primeros 20 días del mes siguiente. Presentación: electrónica obligatoria."),
        ("plazo", "Plazos y sanciones",
         "Mensual, primeros 20 días naturales del mes siguiente. Si día 20 inhábil → primer hábil. Recargo voluntario 5%. Recargo involuntario 5-10%. Intereses demora: TIE + 4%. Suspensión con depósito 50%."),
        ("como-rellenar", "Cómo rellenar",
         "Sección 1: Datos del declarante. Sección 2: Datos del destinatario (NIF extranjero o NIF intracomunitario según país, país). Sección 3: Detalle de facturas - nº factura, fecha, importe base, IVA, retención. Sección 4: Totales por tipo de operación. Sección 5: Cálculo cuota. Clave 9: tipo de operación (intracomunitaria si UE, no intracomunitaria si fuera UE)."),
    ],
    "100": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: contribuyentes del IRPF con rendimientos del trabajo superiores a 22.000€ anuales de un solo pagador, o que tengan rendimientos del capital mobiliario, económicos, ganancias/pérdidas patrimoniales, o prestaciones de desempleo. También quienes tengan bienes en el extranjero (modelo 720), cuentas en el extranjero, o que hayan realizado donaciones o herencias. Periodo: anual (ciclo fiscal del año natural). Plazo: campaña de abril-junio 2026 (para ejercicio 2025). Presentación: electrónica o presencial con cita previa."),
        ("plazo", "Plazos y sanciones",
         "Campaña de Renta 2026 (ejercicio 2025): abril a junio 2026. Con certificado digital o Cl@ve: abril-junio. Sin certificado (con ayuda): abril-mayo. Recargo voluntario: 5% (reducido a 1% si se paga íntegro en periodo voluntario). Recargo involuntario: 5-20%. Intereses demora: TIE + 4%. Suspensión: depósito 50% o aval."),
        ("como-rellenar", "Cómo rellenar",
         "Anexo 1: Rendimientos del trabajo (nóminas, prestaciones). Anexo 2: Rendimientos del capital inmobiliario (alquileres). Anexo 3: Rendimientos del capital mobiliario (dividendos, intereses). Anexo 4: Ganancias y pérdidas patrimoniales (ventas de inmuebles, acciones). Anexo 5: Deducciones (vivienda, donativos, maternidad, etc.). Anexo 6: Cuota a pagar o a compensar. Caso FACTA: si eres residente español con facturas a empresas UE, puede afectar a rendimientos patrimoniales (dividendos) → Anexo 3."),
    ],
    "303": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales que realicen entregas de bienes o prestaciones de servicios sujetas a IVA. Periodo: trimestral (ene-mar, abr-jun, jul-sep, oct-dic). Plazo: primeros 20 días naturales del mes siguiente al trimestre. Si día 20 inhábil → primer hábil. Presentación: electrónica obligatoria para la mayoría de contribuyentes."),
        ("como-rellenar", "Cómo rellenar",
         "Casilla 000: Base imponible total. Casilla 001-004: Cuota repercutida por tipo (4%, 10%, 21%). Casilla 040-043: Cuota soportada. Casilla 099: Cuota a ingresar o a compensar. Entregas intracomunitarias → modelo 349. Adquisiciones intracomunitarias → modelo 349. FactA a no residentes → según caso, puede ser exento (art. 21 LIVA) o no sujeto."),
    ],
    "349": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales que realicen entregas de bienes o prestaciones de servicios a operadores intracomunitarios (con NIF intracomunitario de otro país UE). También adquisiciones intracomunitarias de bienes. Periodo: mensual (se declara en el trimestre, pero con datos mensuales). Plazo: primeros 20 días del mes siguiente al trimestre. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Grupo A: Entregas de bienes - NIF intracomunitario destinatario, descripción, importe base, IVA. Grupo B: Prestaciones de servicios - NIF intracomunitario, concepto, importe. Grupo C: Adquisiciones intracomunitarias de bienes - NIF intracomunitario proveedor, importe base. Cada operación se declara con su número de factura y fecha."),
    ],
    "347": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresas y profesionales cuyo volumen de operaciones con terceros supere 6.000€ en el año. Incluye entregas de bienes, prestaciones de servicios, adquisiciones intracomunitarias y operaciones interiores. Umbral por grupo: 6.000€ (total anual). Periodo: anual. Plazo: enero-marzo del año siguiente. Presentación: electrónica."),
    ],
    "200": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: sociedades mercantiles, entidades transparentes fiscales, y todo contribuyente del Impuesto sobre Sociedades. Periodo: anual (ejercicio fiscal coincide con año natural salvo justificación justificada). Plazo: primeros 6 meses del ejercicio siguiente (junio). Prórroga: hasta julio para entidades con activo total > 10M€. Presentación: electrónica obligatoria."),
    ],
    "123": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidades que obtengan rendimientos del capital mobiliario (dividendos, intereses) de residentes no fiscales en España. También ingresos por actividades económicas realizadas en España por no residentes sin establecimiento permanente. Periodo: trimestral. Plazo: primeros 20 días del mes siguiente al trimestre."),
    ],
    "111": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidades que realicen pagos de retribuciones a trabajadores por cuenta ajena con retención de IRPF. Periodo: mensual. Plazo: primeros 20 días del mes siguiente. Presentación: electrónica obligatoria vía Sede AEAT."),
        ("plazo", "Plazos y sanciones",
         "Mensual, primeros 20 días naturales del mes siguiente. Si día 20 inhábil → primer hábil. Recargo voluntario 5%. Recargo involuntario 5-10%. Intereses demora: TIE + 4%."),
        ("como-rellenar", "Cómo rellenar",
         "Sección 1: Datos identificativos del declarante. Sección 2: Datos del trabajador (NIF, nombre, código de cuenta profesional, concepto de retribución). Sección 3: Detalle de retenciones y ingresos a cuenta por concepto. Sección 4: Cálculo de la autoliquidación. Sección 5: Cuentas contables."),
    ],
    "116": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidades que realicen pagos a no residentes por actividades económicas desarrolladas en España sin establecimiento permanente. Periodo: trimestral. Plazo: primeros 20 días del mes siguiente al trimestre. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Sección 1: Datos del declarante. Sección 2: Datos del no residente (NIF extranjero, país, tipo de actividad). Sección 3: Detalle de rendimientos — concepto, importe bruto, tipo de retención, cuota. Sección 4: Cálculo de la cuota. Sección 5: Cuentas contables."),
    ],
    "394": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales acogidos al SII (Suministro Inmediato de Información) del IVA. Periodo: anual. Plazo: enero-febrero del año siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Grupo A: Facturas emitidas — desglose por tipo impositivo (4%, 10%, 21%, 0%). Grupo B: Facturas recibidas — desglose por tipo impositivo. Grupo C: Facturas intracomunitarias. Grupo D: Operaciones exentas. El resumen se genera automáticamente a partir del SII."),
    ],
    "720": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: personas físicas y jurídicas que tengan bienes y derechos en el extranjero por importe superior a 50.000€ en cualquier categoría (cuentas bancarias, valores, seguros, inmuebles). Periodo: anual (enero-marzo). Plazo: trimestral durante el año natural de adquisición. Sanciones: 5% del importe no declarado (mínimo 6.000€), reducible al 5% con pago voluntario."),
        ("como-rellenar", "Cómo rellenar",
         "Grupo 1: Cuentas bancarias en el extranjero (saldo total > 50.000€). Grupo 2: Valores, acciones, derechos. Grupo 3: Seguros. Grupo 4: Inmuebles. Grupo 5: Otros bienes y derechos. Cada grupo se declara con el importe total por entidad/país."),
    ],
    "201": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidades no residentes que obtengan rendimientos en España por establecimiento permanente o entregas de bienes/prestaciones de servicios. Periodo: anual. Plazo: primeros 6 meses del ejercicio siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Cuadro 1: Datos identificativos. Cuadro 2: Base imponible por renta. Cuadro 3: Cuota íntegra. Cuadro 4: Deducciones. Cuadro 5: Cuota a ingresar o a compensar. Aplicable: LIS art. 11 (entidades no residentes con EP)."),
    ],
    "190": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales que hayan realizado pagos o entregas de retribuciones con retención durante el año. Periodo: anual. Plazo: enero-febrero del año siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Grupo 1: Retribuciones al trabajador (datos del trabajador, retribuciones brutas, retenciones). Grupo 2: Rendimientos del capital (dividendos, intereses). Grupo 3: Actividades económicas (pagos a proveedores con retención). Grupo 4: Ganancias patrimoniales."),
    ],
    "430": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales que realicen operaciones de importación/exportación con terceros países (fuera de la UE). Periodo: mensual. Plazo: primeros 10 días del mes siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Relación de facturas de exportación/importación — nº factura, fecha, importe, país de origen/destino, código arancelario, régimen aduanero."),
    ],
    "431": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: mismos que el 430 — declaraciones estadísticas de operaciones con terceros países. Periodo: mensual. Plazo: primeros 10 días del mes siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Relación de facturas de importación/exportación — nº factura, fecha, importe, país, código arancelario, régimen aduanero. Se envía por separado del 430 (exportaciones vs importaciones)."),
    ],
    "114": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: entidades que realicen pagos a profesionales o autónomos con retención de IRPF. Periodo: trimestral. Plazo: primeros 20 días del mes siguiente al trimestre. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Sección 1: Datos del declarante. Sección 2: Datos del profesional (NIF, nombre, IAE, concepto). Sección 3: Detalle de pagos — importe bruto, retención, base imponible. Sección 4: Cálculo de la cuota."),
    ],
    "828": [
        ("quien-debe", "¿Quién debe presentar?",
         "Obligado: empresarios y profesionales que realicen operaciones sujetas al art. 79.4 LIVA (adquisiciones intracomunitarias de bienes, operaciones con terceros países). Periodo: anual. Plazo: enero-febrero del año siguiente. Presentación: electrónica obligatoria."),
        ("como-rellenar", "Cómo rellenar",
         "Relación de operaciones — nº factura, fecha, importe, tipo impositivo, NIF intracomunitario del proveedor, país. El art. 79.4 cubre operaciones de terceros países y adquisiciones intracomunitarias de bienes con características especiales."),
    ],
}

OBLIGACIONES = [
    ("IRNR_FACTA", "Declaración FactA - No residentes", "D.L. 13/1995 (IRNR)", "AEAT", "declaracion_operaciones_intracomunitarias", "retenedor_no_residente", "mensual", "124,216,296", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 44", "Operaciones con no residentes", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Entidades que realicen entregas a no residentes", 50, 150, "5%", "5-10%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IVA_INTRACOMUNITARIO", "Declaración intracomunitaria de operaciones (SII + 349)", "LIVA + Ley 37/1992", "AEAT", "declaracion_intracomunitaria", "empresario_intracomunitario", "mensual/trimestral", "349,303,036,108,304", "iva_intracomunitario", "vigente", "boe", "BOE-A-1992-2880", "Sección 7", "Art. 74", "Operaciones intracomunitarias", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Empresarios con operaciones intracomunitarias", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRPF_RETENCIONES", "Retenciones sobre rendimientos del trabajo y capital", "LIRPF + D.L. 439/1993", "AEAT", "retencion_ingreso_cuenta", "retenedor", "mensual", "115,124", "irpf_retenciones", "vigente", "boe", "BOE-A-2006-18559", "Sección 3", "Art. 86", "Retenciones IRPF", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Retenedores de rendimientos del trabajo y capital", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRPF_ANUAL", "Autoliquidación anual IRPF", "LIRPF (Ley 35/2006)", "AEAT", "autoliquidacion_anual", "contribuyente_irpf", "anual", "100", "irpf_anual", "vigente", "boe", "BOE-A-2006-18559", "Sección 1", "Art. 65", "Declaración anual IRPF", None, "anual", "campana_renta_aeat", "fin_anio_fiscal", "electronica", "Contribuyentes IRPF con rendimientos > 22.000€", 50, 20, "5%", "5-20%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("IVA_TRIMESTRAL", "Autoliquidación trimestral IVA", "LIVA (Ley 37/1992)", "AEAT", "autoliquidacion_iva", "empresario_profesional_iva", "trimestral", "303,300,130", "iva_trimestral", "vigente", "boe", "BOE-A-1992-2880", "Sección 4", "Art. 29", "Autoliquidación IVA", 20, "trimestral", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Empresarios y profesionales con entregas de bienes o prestaciones de servicios", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IS_ANUAL", "Autoliquidación Impuesto Sociedades", "LIS (Ley 27/2014)", "AEAT", "autoliquidacion_anual", "sociedad_contribuyente", "anual", "200", "is_anual", "vigente", "boe", "BOE-A-2014-12611", "Sección 2", "Art. 59", "Impuesto Sociedades", 180, "anual", "primeros_6_meses_ejercicio_siguiente", "fin_anio_fiscal", "electronica", "Sociedades sujetas al Impuesto sobre Sociedades", 50, 20, "5%", "5-20%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("OPS_TER_CER_TER", "Declaración de operaciones con terceras personas (347)", "LIS (Ley 27/2014)", "AEAT", "declaracion_informativa", "empresa_profesional", "anual", "347", "informativo", "vigente", "boe", "BOE-A-2014-12611", "Sección 6", "Art. 97", "Declaración informativa 347", 90, "anual", "enero_marzo_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresas con volumen de operaciones > 6.000€ con terceros", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRPF_RETRIBUCIONES", "Retenciones sobre retribuciones al trabajador", "LIRPF + D.L. 439/1993", "AEAT", "retencion_retribuciones", "retenedor", "mensual", "111,114,115", "irpf_retenciones", "vigente", "boe", "BOE-A-2006-18559", "Sección 3", "Art. 86", "Retenciones retribuciones", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Empresas con trabajadores por cuenta ajena", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRNR_ACTIVIDADES", "Retenciones a no residentes por actividades económicas", "D.L. 13/1995 (IRNR)", "AEAT", "retencion_no_residente", "retenedor_no_residente", "trimestral", "116,121", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 44", "Retenciones no residentes", 20, "trimestral", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Entidades que paguen a no residentes por actividades en España", 50, 150, "5%", "5-10%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRNR_DIVIDENDOS", "Retenciones a no residentes por dividendos y rentas de capital", "D.L. 13/1995 (IRNR)", "AEAT", "retencion_irnr", "retenedor_no_residente", "mensual", "124,212", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 25", "Retenciones dividendos no residentes", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Entidades que paguen dividendos a no residentes", 50, 150, "5%", "5-10%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("RESUMEN_SII", "Resumen anual SII de facturas", "LIVA + Ley 37/1992", "AEAT", "resumen_informativo", "empresario_sii", "anual", "394", "iva_sii", "vigente", "boe", "BOE-A-1992-2880", "Sección 4", "Art. 29", "Resumen anual SII", 90, "anual", "enero_febrero_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresarios acogidos al SII", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("BIENES_EXTRANJERO", "Información de bienes y derechos en el extranjero", "LIRPF (Ley 35/2006)", "AEAT", "declaracion_bienes_extranjero", "contribuyente", "anual", "720", "informacion_internacional", "vigente", "boe", "BOE-A-2006-18559", "Sección 1", "Art. 28", "Declaración bienes extranjero", 90, "anual", "enero_marzo_ano_siguiente", "fin_anio_fiscal", "electronica", "Personas con bienes/derechos en extranjero > 50.000€", 50, 6000, "5%", "5%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IS_NO_RESIDENTES", "Impuesto Sociedades entidades no residentes", "LIS (Ley 27/2014)", "AEAT", "impuesto_sociedades_no_residentes", "entidad_no_residente", "anual", "201", "is_no_residente", "vigente", "boe", "BOE-A-2014-12611", "Sección 2", "Art. 11", "Impuesto Sociedades no residentes", 180, "anual", "primeros_6_meses_ejercicio_siguiente", "fin_anio_fiscal", "electronica", "Entidades no residentes con establecimiento permanente en España", 50, 20, "5%", "5-20%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("RETRIBUCIONES_ANUAL", "Relación anual de retribuciones y pagos", "LIRPF + D.L. 439/1993", "AEAT", "declaracion_anual_retribuciones", "empresa_profesional", "anual", "190,111,114", "irpf_anual", "vigente", "boe", "BOE-A-2006-18559", "Sección 3", "Art. 92", "Declaración anual retribuciones", 90, "anual", "enero_febrero_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresas que hayan realizado pagos con retención", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("OPS_ADUANERAS", "Listas de operaciones de exportación/importación", "Ley 27/2000 de regulación aduanera", "AEAT", "declaracion_estadistica_aduanas", "empresa_comercio_exterior", "mensual", "430,431", "estadistico_comercio_exterior", "vigente", "boe", "BOE-A-2000-1470", "Sección 1", "Art. 30", "Declaraciones estadísticas aduanas", 10, "mensual", "primeros_10_dias_periodo_siguiente", "fin_mes", "electronica", "Empresas con operaciones de importación/exportación fuera UE", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRNR_ACTIV_ANUAL", "IRNR — Actividades económicas (periodo anual)", "D.L. 13/1995 (IRNR)", "AEAT", "autoliquidacion_irnr_anual", "entidad_no_residente", "anual", "121", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 44", "IRNR actividades económicas anual", 180, "anual", "primeros_6_meses_ejercicio_siguiente", "fin_anio_fiscal", "electronica", "No residentes con actividades económicas en España", 50, 150, "5%", "5-10%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("IRNR_PROVEEDORES", "Relación de pagos a proveedores no residentes", "D.L. 13/1995 (IRNR)", "AEAT", "declaracion_anual_pagos_no_residentes", "empresa_profesional", "anual", "878", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 44", "Pagos a no residentes", 90, "anual", "enero_febrero_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresas con pagos a proveedores no residentes", 50, 150, "5%", "5-10%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IS_TRAMO_ESTATAL", "Autoliquidación tramo estatal del IS", "LIS (Ley 27/2014)", "AEAT", "tramo_estatal_is", "sociedad_contribuyente", "trimestral", "269", "is_tramo_estatal", "vigente", "boe", "BOE-A-2014-12611", "Sección 2", "Art. 59", "Tramo estatal IS", 20, "trimestral", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Sociedades con tramo estatal en IS (comunidades autónomas)", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("FACTA_NC_INTRACOM", "Facturas-Notas de crédito intracomunitarias", "LIVA (Ley 37/1992)", "AEAT", "facturas_notas_credito_intracomunitarias", "empresario_intracomunitario", "mensual", "380", "iva_intracomunitario", "vigente", "boe", "BOE-A-1992-2880", "Sección 7", "Art. 74", "Facturas-NC intracomunitarias", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Empresarios con facturas de rectificación intracomunitarias", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("OPS_ART79_4", "Comunicación de operaciones art. 79.4 LIVA", "LIVA (Ley 37/1992)", "AEAT", "comunicacion_operaciones_especiales", "empresario_profesional", "anual", "828", "iva_especial", "vigente", "boe", "BOE-A-1992-2880", "Sección 7", "Art. 79", "Operaciones art. 79.4 LIVA", 90, "anual", "enero_febrero_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresarios con operaciones de terceros países o adquisiciones intracomunitarias especiales", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
]

def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    # 1. Insert models
    for m in MODELOS:
        cur.execute(
            """INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre""",
            m,
        )

    # 2. Insert 2025 campaign for key models + instrucciones
    models_with_campaign = ["100", "303", "124", "216", "349", "200", "111", "116", "394", "720", "201", "190", "430", "431", "114", "269", "828", "121"]
    for codigo in models_with_campaign:
        cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (codigo,))
        modelo_id = cur.fetchone()[0]

        # Insert campaign
        cur.execute(
            """INSERT INTO modelo_campana (modelo_id, campana, url_normativa, url_instrucciones, activo)
               VALUES (%s, '2025', NULL, NULL, true)
               ON CONFLICT (modelo_id, campana) DO UPDATE SET activo = true""",
            (modelo_id,),
        )

        cur.execute(
            "SELECT id FROM modelo_campana WHERE modelo_id = %s AND campana = '2025'",
            (modelo_id,),
        )
        campana_id = cur.fetchone()[0]

        # Insert instructions
        for seccion, titulo, contenido in INSTRUCCIONES.get(codigo, []):
            cur.execute(
                """INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (campana_id, seccion, titulo) DO UPDATE SET contenido = EXCLUDED.contenido""",
                (campana_id, seccion, titulo, contenido),
            )

    # 3. Insert campaign_operativa for key models
    cat_dict = {
        "100": "contribuyente_irpf",
        "303": "empresario_profesional_iva",
        "124": "retenedor_irnr",
        "216": "retenedor_no_residente",
        "349": "empresario_intracomunitario",
        "200": "sociedad_contribuyente",
        "111": "retenedor",
        "116": "retenedor_no_residente",
        "394": "empresario_sii",
        "720": "contribuyente",
        "201": "entidad_no_residente",
        "190": "empresa_profesional",
        "430": "empresa_comercio_exterior",
        "431": "empresa_comercio_exterior",
        "114": "retenedor",
        "269": "sociedad_contribuyente",
        "828": "empresario_profesional",
        "121": "entidad_no_residente",
    }
    frec_dict = {
        "100": "anual", "303": "trimestral", "124": "mensual",
        "216": "mensual", "349": "mensual", "200": "anual",
        "111": "mensual", "116": "trimestral", "394": "anual",
        "720": "anual", "201": "anual", "190": "anual",
        "430": "mensual", "431": "mensual", "114": "trimestral",
        "269": "trimestral", "828": "anual", "121": "anual",
    }
    ventana_dict = {
        "100": "campana de renta (abril-junio)",
        "303": "primeros 20 días del mes siguiente al trimestre",
        "124": "primeros 20 días del mes siguiente",
        "216": "primeros 20 días del mes siguiente",
        "349": "primeros 20 días del mes siguiente al trimestre",
        "200": "primeros 6 meses del ejercicio siguiente",
        "111": "primeros 20 días del mes siguiente",
        "116": "primeros 20 días del mes siguiente al trimestre",
        "394": "enero-febrero del año siguiente",
        "720": "enero-marzo del año siguiente",
        "201": "primeros 6 meses del ejercicio siguiente",
        "190": "enero-febrero del año siguiente",
        "430": "primeros 10 días del mes siguiente",
        "431": "primeros 10 días del mes siguiente",
        "114": "primeros 20 días del mes siguiente al trimestre",
        "269": "primeros 20 días del mes siguiente al trimestre",
        "828": "enero-febrero del año siguiente",
        "121": "primeros 6 meses del ejercicio siguiente",
    }
    obligados_dict = {
        "100": "Contribuyentes IRPF con rendimientos > 22.000€ o con rentas del capital, patrimoniales, etc.",
        "303": "Empresarios y profesionales con entregas de bienes o prestaciones de servicios",
        "124": "Entidades que retengan dividendos o rentas de capital a no residentes",
        "216": "Entidades que facturen a clientes no residentes (FactA)",
        "349": "Empresarios con operaciones intracomunitarias de bienes o servicios",
        "200": "Sociedades sujetas al Impuesto sobre Sociedades",
        "111": "Empresas con trabajadores por cuenta ajena que realicen retenciones de IRPF",
        "116": "Entidades que paguen a no residentes por actividades económicas en España",
        "394": "Empresarios acogidos al SII (Suministro Inmediato de Información) del IVA",
        "720": "Personas físicas o jurídicas con bienes/derechos en el extranjero > 50.000€",
        "201": "Entidades no residentes con establecimiento permanente en España",
        "190": "Empresas que hayan realizado pagos o entregas con retención durante el año",
        "430": "Empresas con operaciones de exportación fuera de la UE",
        "431": "Empresas con operaciones de importación fuera de la UE",
        "114": "Empresas que paguen a profesionales/autónomos con retención IRPF",
        "269": "Sociedades con tramo estatal en el Impuesto sobre Sociedades",
        "828": "Empresarios con operaciones de terceros países o adquisiciones intracomunitarias especiales",
        "121": "No residentes con actividades económicas en España (periodo anual)",
    }
    norma_base_dict = {
        "100": "IRPF art. 65",
        "303": "LIVA art. 71",
        "124": "IRNR art. 25",
        "216": "IRNR art. 14",
        "349": "LIVA operaciones intracomunitarias",
        "200": "LIS art. 21",
        "111": "LIRPF art. 86",
        "116": "IRNR art. 44",
        "394": "LIVA art. 29 SII",
        "720": "LIRPF art. 28",
        "201": "LIS art. 11",
        "190": "LIRPF art. 92",
        "430": "Ley 27/2000 aduanas art. 30",
        "431": "Ley 27/2000 aduanas art. 30",
        "114": "LIRPF art. 86",
        "269": "LIS art. 59",
        "828": "LIVA art. 79.4",
        "121": "IRNR art. 44",
    }

    for codigo in models_with_campaign:
        cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (codigo,))
        modelo_id = cur.fetchone()[0]

        cur.execute(
            "SELECT id FROM modelo_campana WHERE modelo_id = %s AND campana = '2025'",
            (modelo_id,),
        )
        campana_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
               ventana_presentacion, canal_presentacion, obligados_resumen, norma_base, origen_metadato, estado_metadato)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'seed_curado', 'curado')
               ON CONFLICT (campana_id) DO UPDATE SET
                   categoria_obligado = EXCLUDED.categoria_obligado,
                   obligados_resumen = EXCLUDED.obligados_resumen,
                   norma_base = EXCLUDED.norma_base,
                   actualizado_at = now()""",
            (
                campana_id,
                cat_dict[codigo],
                frec_dict[codigo],
                ventana_dict[codigo],
                "electronica",
                obligados_dict[codigo],
                norma_base_dict[codigo],
            ),
        )

    # 4. Insert obligaciones (tabla: obligacion_regulatoria)
    for o in OBLIGACIONES:
        cur.execute(
            """INSERT INTO obligacion_regulatoria (codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
               sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia,
               documento_origen_tipo, documento_origen_ref, seccion_origen, anexo_origen, nota,
               plazo_dias, frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
               canal_presentacion, obligados_resumen, sancion_min, sancion_max,
               recargo_voluntario, recargo_involuntario, interes_demora, prescripcion_anos,
               deposito_previo, fuentes_operativas, origen_metadato, estado_metadato)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET
               nombre = EXCLUDED.nombre, reporte_modelo = EXCLUDED.reporte_modelo,
               plazo_dias = EXCLUDED.plazo_dias, sancion_min = EXCLUDED.sancion_min,
               sancion_max = EXCLUDED.sancion_max""",
            o,
        )

    conn.commit()
    print(f"OK: {len(MODELOS)} modelos, instrucciones y obligaciones seedeados")
    conn.close()


if __name__ == "__main__":
    main()
