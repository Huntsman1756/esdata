#!/usr/bin/env python
"""Seed de modelos AEAT curados para consulta fiscal."""

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
}

OBLIGACIONES = [
    ("IRNR_FACTA", "Declaración FactA - No residentes", "D.L. 13/1995 (IRNR)", "AEAT", "declaracion_operaciones_intracomunitarias", "retenedor_no_residente", "mensual", "124,216,296", "tributario_internacional", "vigente", "boe", "BOE-A-2004-4527", "Sección 5", "Art. 44", "Operaciones con no residentes", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Entidades que realicen entregas a no residentes", 50, 150, "5%", "5-10%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IVA_INTRACOMUNITARIO", "Declaración intracomunitaria de operaciones (SII + 349)", "LIVA + Ley 37/1992", "AEAT", "declaracion_intracomunitaria", "empresario_intracomunitario", "mensual/trimestral", "349,303,036,108,304", "iva_intracomunitario", "vigente", "boe", "BOE-A-1992-2880", "Sección 7", "Art. 74", "Operaciones intracomunitarias", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Empresarios con operaciones intracomunitarias", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRPF_RETENCIONES", "Retenciones sobre rendimientos del trabajo y capital", "LIRPF + D.L. 439/1993", "AEAT", "retencion_ingreso_cuenta", "retenedor", "mensual", "115,124", "irpf_retenciones", "vigente", "boe", "BOE-A-2006-18559", "Sección 3", "Art. 86", "Retenciones IRPF", 20, "mensual", "primeros_20_dias_periodo_siguiente", "fin_mes", "electronica", "Retenedores de rendimientos del trabajo y capital", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IRPF_ANUAL", "Autoliquidación anual IRPF", "LIRPF (Ley 35/2006)", "AEAT", "autoliquidacion_anual", "contribuyente_irpf", "anual", "100", "irpf_anual", "vigente", "boe", "BOE-A-2006-18559", "Sección 1", "Art. 65", "Declaración anual IRPF", None, "anual", "campana_renta_aeat", "fin_anio_fiscal", "electronica", "Contribuyentes IRPF con rendimientos > 22.000€", 50, 20, "5%", "5-20%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("IVA_TRIMESTRAL", "Autoliquidación trimestral IVA", "LIVA (Ley 37/1992)", "AEAT", "autoliquidacion_iva", "empresario_profesional_iva", "trimestral", "303,300,130", "iva_trimestral", "vigente", "boe", "BOE-A-1992-2880", "Sección 4", "Art. 29", "Autoliquidación IVA", 20, "trimestral", "primeros_20_dias_periodo_siguiente", "fin_trimestre", "electronica", "Empresarios y profesionales con entregas de bienes o prestaciones de servicios", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
    ("IS_ANUAL", "Autoliquidación Impuesto Sociedades", "LIS (Ley 27/2014)", "AEAT", "autoliquidacion_anual", "sociedad_contribuyente", "anual", "200", "is_anual", "vigente", "boe", "BOE-A-2014-12611", "Sección 2", "Art. 59", "Impuesto Sociedades", 180, "anual", "primeros_6_meses_ejercicio_siguiente", "fin_anio_fiscal", "electronica", "Sociedades sujetas al Impuesto sobre Sociedades", 50, 20, "5%", "5-20%", "TIE + 4%", 4, "50%", None, "seed_curado", "curado"),
    ("OPS_TER_CER_TER", "Declaración de operaciones con terceras personas (347)", "LIS (Ley 27/2014)", "AEAT", "declaracion_informativa", "empresa_profesional", "anual", "347", "informativo", "vigente", "boe", "BOE-A-2014-12611", "Sección 6", "Art. 97", "Declaración informativa 347", 90, "anual", "enero_marzo_ano_siguiente", "fin_anio_fiscal", "electronica", "Empresas con volumen de operaciones > 6.000€ con terceros", 50, 150, "5%", "5-20%", "TIE + 4%", 4, None, None, "seed_curado", "curado"),
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
    models_with_campaign = ["100", "303", "124", "216", "349", "200"]
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
        "216": "retenedor_irnr",
        "349": "empresario_intracomunitario",
        "200": "sociedad_contribuyente",
    }
    frec_dict = {
        "100": "anual", "303": "trimestral", "124": "mensual",
        "216": "mensual", "349": "mensual", "200": "anual",
    }
    ventana_dict = {
        "100": "campana de renta (abril-junio)",
        "303": "primeros 20 días del mes siguiente al trimestre",
        "124": "primeros 20 días del mes siguiente",
        "216": "primeros 20 días del mes siguiente",
        "349": "primeros 20 días del mes siguiente al trimestre",
        "200": "primeros 6 meses del ejercicio siguiente",
    }
    obligados_dict = {
        "100": "Contribuyentes IRPF con rendimientos > 22.000€ o con rentas del capital, patrimoniales, etc.",
        "303": "Empresarios y profesionales con entregas de bienes o prestaciones de servicios",
        "124": "Entidades que retengan dividendos o rentas de capital a no residentes",
        "216": "Entidades que facturen a clientes no residentes (FactA)",
        "349": "Empresarios con operaciones intracomunitarias de bienes o servicios",
        "200": "Sociedades sujetas al Impuesto sobre Sociedades",
    }
    norma_base_dict = {
        "100": "IRPF art. 65",
        "303": "LIVA art. 71",
        "124": "IRNR art. 25",
        "216": "IRNR art. 14",
        "349": "LIVA operaciones intracomunitarias",
        "200": "LIS art. 21",
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
                       jsonb_build_object(), %s, %s)
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
