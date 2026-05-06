import re

from sqlalchemy import text

DIRTY_AEAT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"<script",
        r"</script",
        r"static_files",
        r"saltar al contenido principal",
        r"logotipo del gobierno",
        r"logotipo organismo",
        r"menú móvil",
        r"menu móvil",
        r"abrir menú móvil",
        r"<[^>]+\sclass\s*=",
        r"<[^>]+\ssrc\s*=",
        r"[\"']\s*(?:class|src)\s*=",
    )
]

AEAT_STOP_PHRASES = (
    "Agencia Tributaria",
    "Saltar al contenido principal",
    "Logotipo del Gobierno de España",
    "Logotipo Organismo",
    "Menú móvil",
    "Menu móvil",
    "Abrir menú móvil",
)


def is_dirty_aeat_text(value) -> bool:
    return isinstance(value, str) and any(pattern.search(value) for pattern in DIRTY_AEAT_PATTERNS)


def clean_aeat_text(value):
    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"&nbsp;", " ", cleaned, flags=re.IGNORECASE)
    for phrase in AEAT_STOP_PHRASES:
        cleaned = re.sub(re.escape(phrase), " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def assess_modelo_cleanliness(*values) -> dict:
    def walk(value):
        if value is None:
            return []
        if isinstance(value, dict):
            found = []
            for item in value.values():
                found.extend(walk(item))
            return found
        if isinstance(value, (list, tuple)):
            found = []
            for item in value:
                found.extend(walk(item))
            return found
        return [value] if is_dirty_aeat_text(value) else []

    dirty_values = []
    for value in values:
        dirty_values.extend(walk(value))
    warnings = ["aeat_parser_residue_detected"] if dirty_values else []
    return {
        "verified": not dirty_values,
        "completeness": "partial" if dirty_values else None,
        "warnings": warnings,
    }


def _infer_frecuencia(periodo: str | None, plazo: str | None) -> str | None:
    periodo_value = (periodo or "").lower()
    plazo_value = (plazo or "").lower()
    if "mensual" in periodo_value:
        return "mensual"
    if "trimestral" in periodo_value:
        return "trimestral"
    if "anual" in periodo_value:
        return "anual"
    if "mensual" in plazo_value:
        return "mensual"
    if "trimestral" in plazo_value:
        return "trimestral"
    if "anual" in plazo_value or "resumen anual" in plazo_value:
        return "anual"
    base = f"{periodo_value} {plazo_value}".strip()
    return "variable" if base.strip() else None


def _infer_ventana_presentacion(plazo: str | None) -> str | None:
    text_value = (plazo or "").lower()
    if "primeros veinte dias" in text_value:
        return "primeros_20_dias_mes_siguiente"
    if "campana de renta" in text_value:
        return "campana_renta_aeat"
    if "plazos generales" in text_value:
        return "plazo_general_aeat"
    if "plazo fijado por la aeat" in text_value:
        return "plazo_fijado_aeat"
    return None


def _infer_canal_presentacion(presentacion: str | None) -> str | None:
    text_value = (presentacion or "").lower()
    if "electronica" in text_value or "electrónica" in text_value:
        return "electronica"
    if "presencial" in text_value:
        return "presencial"
    if "internet" in text_value or "telemat" in text_value:
        return "electronica"
    return None


def _infer_categoria_obligado(codigo: str, impuesto: str | None, obligados: str | None) -> str | None:
    text_value = (obligados or "").lower()
    if codigo in {"124", "216", "296"} or "no residentes" in text_value:
        return "retenedor_irnr"
    if codigo == "303" or "autoliquidar el iva" in text_value:
        return "empresario_o_profesional_iva"
    if codigo == "100" or "contribuyentes del irpf" in text_value:
        return "contribuyente_irpf"
    if impuesto:
        return f"obligado_{impuesto.lower()}"
    return None


def _build_truth_contract(*, has_instructions: bool, has_casillas: bool, metadata_state: str | None = None) -> tuple[str, bool]:
    if not has_instructions or not has_casillas:
        return "parcial", False
    if metadata_state in {None, "inferido"}:
        return "parcial", False
    return "completa", True


def build_modelo_truth_contract(
    *, has_instructions: bool, has_casillas: bool, metadata_state: str | None = None
) -> tuple[str, bool]:
    return _build_truth_contract(
        has_instructions=has_instructions,
        has_casillas=has_casillas,
        metadata_state=metadata_state,
    )


def get_modelo_runtime_truth_contract(
    db, codigo: str, campana: str | None = None
) -> tuple[str, bool]:
    camp_row = get_active_campaign(db, codigo, campana)
    campana_id = camp_row["id"] if camp_row else None
    # Consume existence checks immediately so SQLite does not keep read locks
    # around when the audit service opens its write transaction.
    has_instructions = (
        list_campaign_instructions(db, campana_id).first() is not None if campana_id else False
    )
    has_casillas = (
        list_campaign_casillas(db, campana_id).first() is not None if campana_id else False
    )
    operativa_row = get_modelo_campana_operativa_row(db, campana_id) if campana_id else None
    metadata_state = (
        operativa_row["estado_metadato"]
        if operativa_row and operativa_row.get("estado_metadato")
        else None
    )
    return build_modelo_truth_contract(
        has_instructions=has_instructions,
        has_casillas=has_casillas,
        metadata_state=metadata_state,
    )


def get_modelo_campana_operativa_row(db, campana_id: int):
    try:
        return db.execute(
            text(
                """
                SELECT
                    categoria_obligado,
                    frecuencia_presentacion,
                    ventana_presentacion,
                    canal_presentacion,
                    obligados_resumen,
                    plazo_resumen,
                    presentacion_resumen,
                    norma_base,
                    nota,
                    origen_metadato,
                    estado_metadato
                FROM modelo_campana_operativa
                WHERE campana_id = :campana_id
                LIMIT 1
                """
            ),
            {"campana_id": campana_id},
        ).mappings().first()
    except Exception:
        try:
            return db.execute(
                text(
                    """
                    SELECT
                        categoria_obligado,
                        frecuencia_presentacion,
                        ventana_presentacion,
                        canal_presentacion,
                        obligados_resumen,
                        plazo_resumen,
                        presentacion_resumen,
                        norma_base,
                        nota
                    FROM modelo_campana_operativa
                    WHERE campana_id = :campana_id
                    LIMIT 1
                    """
                ),
                {"campana_id": campana_id},
            ).mappings().first()
        except Exception:
            return None


def get_model_row(db, codigo: str):
    return db.execute(
        text(
            """
            SELECT codigo, nombre, periodo, impuesto, url_info
            FROM aeat_modelo
            WHERE codigo = :codigo
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).mappings().first()


def get_active_campaign(db, codigo: str, campana: str | None = None):
    if campana:
        return db.execute(
            text(
                """
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                  AND campana = :campana
                LIMIT 1
                """
            ),
            {"codigo": codigo, "campana": campana},
        ).mappings().first()

    try:
        return db.execute(
            text(
                "SELECT id, campana, url_instrucciones, url_normativa, url_formato FROM modelo_campana_activa((SELECT id FROM aeat_modelo WHERE codigo = :codigo))"
            ),
            {"codigo": codigo},
        ).mappings().first()
    except Exception:
        return db.execute(
            text(
                """
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                  AND activo = true
                ORDER BY campana DESC
                LIMIT 1
                """
            ),
            {"codigo": codigo},
        ).mappings().first()


def list_modelos_summary(db):
    return db.execute(
        text(
            """
            SELECT
                m.codigo,
                m.nombre,
                m.periodo,
                m.impuesto,
                COUNT(DISTINCT CASE WHEN n.id IS NOT NULL THEN ma.articulo_id END) AS articulos_count,
                COUNT(DISTINCT mc.id) AS casillas_count
            FROM aeat_modelo m
            LEFT JOIN modelo_articulo ma ON ma.modelo_id = m.id
                AND ma.metodo_enlace = 'manual_official'
                AND ma.confianza_enlace = 1.0
                AND ma.url_fuente IS NOT NULL
            LEFT JOIN articulo a ON a.id = ma.articulo_id
            LEFT JOIN norma n ON n.id = a.norma_id
                AND ma.norma = n.codigo
                AND ma.numero = a.numero
            LEFT JOIN modelo_campana mcam ON mcam.modelo_id = m.id AND mcam.activo = true
            LEFT JOIN modelo_casilla mc ON mc.campana_id = mcam.id AND mc.activa = true
            GROUP BY m.id, m.codigo, m.nombre, m.periodo, m.impuesto
            ORDER BY m.codigo
            """
        )
    ).mappings()


def list_modelo_articulos(db, codigo: str):
    return db.execute(
        text(
            """
            SELECT
                n.codigo AS norma,
                a.numero,
                a.titulo,
                ma.casilla,
                ma.nota,
                ma.fuente,
                ma.url_fuente
            FROM modelo_articulo ma
            JOIN articulo a ON a.id = ma.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
              AND ma.metodo_enlace = 'manual_official'
              AND ma.confianza_enlace = 1.0
              AND ma.url_fuente IS NOT NULL
              AND ma.norma = n.codigo
              AND ma.numero = a.numero
            ORDER BY n.codigo, a.numero
            """
        ),
        {"codigo": codigo},
    ).mappings()


def list_modelo_campanas(db, codigo: str):
    return db.execute(
        text(
            """
            SELECT campana, activo
            FROM modelo_campana
            WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
            ORDER BY campana DESC
            """
        ),
        {"codigo": codigo},
    ).mappings()


def list_modelo_normativa(db, codigo: str):
    return db.execute(
        text(
            """
            SELECT boe_id, titulo, fecha, url_boe, resumen
            FROM modelo_normativa
            WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
            ORDER BY fecha DESC
            """
        ),
        {"codigo": codigo},
    ).mappings()


def list_campaign_casillas(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT codigo, etiqueta, descripcion, tipo_casilla, pagina, orden
            FROM modelo_casilla
            WHERE campana_id = :campana_id AND activa = true
            ORDER BY orden
            """
        ),
        {"campana_id": campana_id},
    ).mappings()


def list_campaign_claves(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT codigo, etiqueta, descripcion, tipo_clave
            FROM modelo_clave
            WHERE campana_id = :campana_id AND activa = true
            ORDER BY codigo
            """
        ),
        {"campana_id": campana_id},
    ).mappings()


def list_campaign_instructions(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT seccion, titulo, contenido, orden
            FROM modelo_instruccion
            WHERE campana_id = :campana_id
            ORDER BY orden
            """
        ),
        {"campana_id": campana_id},
    ).mappings()


def list_related_doctrina(db, articulos: list[dict]):
    if not articulos:
        return []

    conditions = []
    params = {}
    for i, articulo in enumerate(articulos):
        conditions.append(f"n.codigo = :n{i} AND a.numero = :a{i}")
        params[f"n{i}"] = articulo["norma"]
        params[f"a{i}"] = articulo["numero"]

    where_clause = " OR ".join(conditions)
    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT
                di.referencia,
                di.organismo_emisor,
                di.fecha,
                n.codigo AS norma,
                a.numero
            FROM documento_articulo da
            JOIN documento_interpretativo di ON di.id = da.documento_id
            JOIN articulo a ON a.id = da.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE {where_clause}
            ORDER BY di.fecha DESC
            LIMIT 50
            """
        ),
        params,
    ).mappings()

    doctrina_map = {}
    for row in rows:
        referencia = row["referencia"]
        if referencia not in doctrina_map:
            doctrina_map[referencia] = {
                "referencia": referencia,
                "organismo_emisor": row["organismo_emisor"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "via_articulos": [],
            }
        doctrina_map[referencia]["via_articulos"].append(
            {"norma": row["norma"], "numero": row["numero"]}
        )

    return list(doctrina_map.values())


def list_modelo_fuentes_oficiales(db, codigo: str, campana: str | None = None):
    model_row = get_model_row(db, codigo)
    if not model_row:
        return None

    camp_row = get_active_campaign(db, codigo, campana)
    campana_activa = camp_row["campana"] if camp_row else None

    fuentes = []
    seen = set()

    def add_source(
        *,
        tipo: str,
        titulo: str,
        url: str | None,
        organismo: str,
        oficial: bool,
        campana_value: str | None = None,
        boe_id: str | None = None,
        fecha: str | None = None,
        nota: str | None = None,
    ):
        if not url:
            return
        key = (tipo, url)
        if key in seen:
            return
        seen.add(key)
        fuentes.append(
            {
                "tipo": tipo,
                "titulo": titulo,
                "url": url,
                "organismo": organismo,
                "campana": campana_value,
                "boe_id": boe_id,
                "fecha": fecha,
                "oficial": oficial,
                "nota": nota,
            }
        )

    add_source(
        tipo="aeat_modelo",
        titulo=f"Ficha AEAT del modelo {codigo}",
        url=model_row["url_info"],
        organismo="AEAT",
        oficial=True,
        nota="Punto de entrada oficial al modelo en sede electrónica.",
    )

    if camp_row:
        add_source(
            tipo="aeat_instrucciones",
            titulo=f"Instrucciones AEAT del modelo {codigo} ({campana_activa})",
            url=camp_row["url_instrucciones"],
            organismo="AEAT",
            oficial=True,
            campana_value=campana_activa,
            nota="Fuente operativa principal para obligados, plazos y cumplimentación.",
        )
        add_source(
            tipo="aeat_normativa_campana",
            titulo=f"Normativa AEAT del modelo {codigo} ({campana_activa})",
            url=camp_row["url_normativa"],
            organismo="AEAT",
            oficial=True,
            campana_value=campana_activa,
            nota="Enlace de campaña mantenido por AEAT cuando existe.",
        )
        add_source(
            tipo="aeat_formato",
            titulo=f"Formato o diseño de registro AEAT del modelo {codigo} ({campana_activa})",
            url=camp_row["url_formato"],
            organismo="AEAT",
            oficial=True,
            campana_value=campana_activa,
            nota="Referencia técnica de formato cuando AEAT la publica.",
        )

    for row in list_modelo_normativa(db, codigo):
        add_source(
            tipo="boe",
            titulo=row["titulo"],
            url=row["url_boe"],
            organismo="BOE",
            oficial=True,
            boe_id=row["boe_id"],
            fecha=str(row["fecha"]) if row["fecha"] else None,
            nota=row["resumen"],
        )

    for row in list_modelo_articulos(db, codigo):
        fuente = row["fuente"] or "Fuente de enlace artículo-modelo"
        url_fuente = row["url_fuente"]
        organismo = "AEAT" if url_fuente and "agenciatributaria" in url_fuente else "esdata"
        add_source(
            tipo="enlace_articulo_modelo",
            titulo=f"{fuente}: artículo {row['norma']} {row['numero']}",
            url=url_fuente,
            organismo=organismo,
            oficial=organismo == "AEAT",
            nota=row["nota"],
        )

    return {
        "codigo": codigo,
        "campana_activa": campana_activa,
        "criterio_uso": (
            "En esdata, la fuente maestra debe ser siempre oficial y primaria "
            "(AEAT, BOE o equivalente público). Las referencias derivadas solo "
            "se usan para trazabilidad adicional o navegación."
        ),
        "fuentes_oficiales": fuentes,
    }


def list_modelo_artefactos(db, codigo: str, campana: str | None = None):
    model_row = get_model_row(db, codigo)
    if not model_row:
        return None

    camp_row = get_active_campaign(db, codigo, campana)
    campana_activa = camp_row["campana"] if camp_row else None
    artefactos = []
    seen = set()

    def add_artefacto(
        *,
        tipo: str,
        titulo: str,
        url: str | None,
        oficial: bool,
        campana_value: str | None = None,
        boe_id: str | None = None,
        fecha: str | None = None,
        formato: str | None = None,
        nota: str | None = None,
    ):
        if not url:
            return
        key = (tipo, url)
        if key in seen:
            return
        seen.add(key)
        artefactos.append(
            {
                "tipo": tipo,
                "titulo": titulo,
                "url": url,
                "campana": campana_value,
                "boe_id": boe_id,
                "fecha": fecha,
                "formato": formato,
                "oficial": oficial,
                "nota": nota,
            }
        )

    if camp_row:
        add_artefacto(
            tipo="instrucciones",
            titulo=f"Instrucciones de campaña del modelo {codigo}",
            url=camp_row["url_instrucciones"],
            oficial=True,
            campana_value=campana_activa,
            formato="html",
            nota="Guía operativa de cumplimentación publicada por AEAT.",
        )
        add_artefacto(
            tipo="normativa_campana",
            titulo=f"Normativa de campaña del modelo {codigo}",
            url=camp_row["url_normativa"],
            oficial=True,
            campana_value=campana_activa,
            formato="html",
            nota="Página de referencia técnica o normativa mantenida por AEAT para la campaña.",
        )
        add_artefacto(
            tipo="formato",
            titulo=f"Formato o diseño de registro del modelo {codigo}",
            url=camp_row["url_formato"],
            oficial=True,
            campana_value=campana_activa,
            formato="html",
            nota="Artefacto técnico útil para importación, validación o intercambio de datos.",
        )

    for row in list_modelo_normativa(db, codigo):
        url = row["url_boe"]
        formato = "pdf" if url and url.lower().endswith(".pdf") else "html"
        add_artefacto(
            tipo="boe_modelo",
            titulo=row["titulo"],
            url=url,
            oficial=True,
            boe_id=row["boe_id"],
            fecha=str(row["fecha"]) if row["fecha"] else None,
            formato=formato,
            nota=row["resumen"],
        )

    return {
        "codigo": codigo,
        "campana_activa": campana_activa,
        "criterio_validacion": (
            "Estos artefactos sirven para validacion local, trazabilidad y trabajo tecnico "
            "sobre el modelo. La aceptacion formal del modelo solo puede confirmarse contra "
            "los flujos oficiales de AEAT."
        ),
        "artefactos": artefactos,
    }


def get_modelo_resumen_operativo(db, codigo: str, campana: str | None = None):
    model_row = get_model_row(db, codigo)
    if not model_row:
        return None

    camp_row = get_active_campaign(db, codigo, campana)
    campana_activa = camp_row["campana"] if camp_row else None
    campana_id = camp_row["id"] if camp_row else None
    instrucciones = list_campaign_instructions(db, campana_id) if campana_id else []

    quien_debe = None
    plazo = None

    for row in instrucciones:
        seccion = (row["seccion"] or "").strip().lower()
        if seccion in {"quien-debe", "quien_debe", "obligados"} and not quien_debe:
            quien_debe = row["contenido"]
        if seccion in {"plazo", "plazo-presentacion"} and not plazo:
            plazo = row["contenido"]

    if not quien_debe:
        quien_debe = (
            f"Consultar las instrucciones AEAT vigentes del modelo {codigo} para determinar "
            "los sujetos obligados en cada campaña."
        )
    if not plazo:
        plazo = (
            f"Consultar la campaña activa y la ficha AEAT del modelo {codigo} para confirmar "
            "el plazo oficial de presentación."
        )

    fuentes = list_modelo_fuentes_oficiales(db, codigo, campana)

    return {
        "codigo": model_row["codigo"],
        "nombre": model_row["nombre"],
        "impuesto": model_row["impuesto"],
        "periodo": model_row["periodo"],
        "campana_activa": campana_activa,
        "quien_debe_presentarlo": quien_debe,
        "plazo_presentacion": plazo,
        "fuentes_recomendadas": (fuentes or {}).get("fuentes_oficiales", []),
    }


def get_modelo_campana_operativa(db, codigo: str, campana: str | None = None):
    model_row = get_model_row(db, codigo)
    if not model_row:
        return None

    camp_row = get_active_campaign(db, codigo, campana)
    campana_activa = camp_row["campana"] if camp_row else None
    campana_id = camp_row["id"] if camp_row else None
    instrucciones = [dict(row) for row in list_campaign_instructions(db, campana_id)] if campana_id else []
    casillas = [dict(row) for row in list_campaign_casillas(db, campana_id)] if campana_id else []
    operativa_row = get_modelo_campana_operativa_row(db, campana_id) if campana_id else None

    obligados = None
    plazo = None
    presentacion = None

    for row in instrucciones:
        seccion = (row["seccion"] or "").strip().lower()
        if seccion in {"quien-debe", "quien_debe", "obligados"} and not obligados:
            obligados = row["contenido"]
        elif seccion in {"plazo", "plazo-presentacion"} and not plazo:
            plazo = row["contenido"]
        elif seccion in {"como-presentar", "como_presentar", "presentacion"} and not presentacion:
            presentacion = row["contenido"]

    if not obligados:
        obligados = (
            f"Consultar las instrucciones AEAT del modelo {codigo} para confirmar "
            "los obligados de la campaña."
        )
    if not plazo:
        plazo = (
            f"Consultar la sede AEAT y la campaña activa del modelo {codigo} para confirmar "
            "el plazo oficial."
        )
    if not presentacion:
        presentacion = (
            f"Consultar la ficha AEAT del modelo {codigo} para verificar la forma "
            "de presentación admitida."
        )

    fuentes = list_modelo_fuentes_oficiales(db, codigo, campana)
    frecuencia = (
        operativa_row["frecuencia_presentacion"]
        if operativa_row and operativa_row["frecuencia_presentacion"]
        else _infer_frecuencia(model_row["periodo"], plazo)
    )
    ventana = (
        operativa_row["ventana_presentacion"]
        if operativa_row and operativa_row["ventana_presentacion"]
        else _infer_ventana_presentacion(plazo)
    )
    canal = (
        operativa_row["canal_presentacion"]
        if operativa_row and operativa_row["canal_presentacion"]
        else _infer_canal_presentacion(presentacion)
    )
    categoria = (
        operativa_row["categoria_obligado"]
        if operativa_row and operativa_row["categoria_obligado"]
        else _infer_categoria_obligado(codigo, model_row["impuesto"], obligados)
    )
    norma_base = operativa_row["norma_base"] if operativa_row and operativa_row["norma_base"] else None
    obligados_payload = (
        operativa_row["obligados_resumen"]
        if operativa_row and operativa_row["obligados_resumen"]
        else obligados
    )
    plazo_payload = (
        operativa_row["plazo_resumen"]
        if operativa_row and operativa_row["plazo_resumen"]
        else plazo
    )
    presentacion_payload = (
        operativa_row["presentacion_resumen"]
        if operativa_row and operativa_row["presentacion_resumen"]
        else presentacion
    )
    origen_metadato = (
        operativa_row["origen_metadato"]
        if operativa_row and operativa_row.get("origen_metadato")
        else None
    )
    estado_metadato = (
        operativa_row["estado_metadato"]
        if operativa_row and operativa_row.get("estado_metadato")
        else None
    )
    completeness, verified = build_modelo_truth_contract(
        has_instructions=bool(instrucciones),
        has_casillas=bool(casillas),
        metadata_state=estado_metadato,
    )

    return {
        "codigo": model_row["codigo"],
        "nombre": model_row["nombre"],
        "campana": campana_activa,
        "impuesto": model_row["impuesto"],
        "periodo": model_row["periodo"],
        "frecuencia_presentacion": frecuencia,
        "ventana_presentacion": ventana,
        "canal_presentacion": canal,
        "categoria_obligado": categoria,
        "norma_base": norma_base,
        "obligados_resumen": obligados_payload,
        "plazo_resumen": plazo_payload,
        "presentacion_resumen": presentacion_payload,
        "origen_metadato": origen_metadato,
        "estado_metadato": estado_metadato,
        "completeness": completeness,
        "verified": verified,
        "fuentes_recomendadas": (fuentes or {}).get("fuentes_oficiales", []),
    }


def list_modelos_campanas_operativas(db, codigos: list[str], campana: str | None = None):
    resultados = []
    vistos = set()
    for codigo in codigos:
        codigo_normalizado = codigo.strip()
        if not codigo_normalizado or codigo_normalizado in vistos:
            continue
        vistos.add(codigo_normalizado)
        payload = get_modelo_campana_operativa(db, codigo_normalizado, campana)
        if payload:
            resultados.append(payload)
    return resultados


def get_modelos_status(db):
    try:
        row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE campana_id IS NOT NULL) AS campanas_activas,
                    MAX(actualizado_at) AS ultima_actualizacion
                FROM modelo_campana_operativa
                """
            )
        ).mappings().first()
    except Exception:
        return {
            "campanas_activas": 0,
            "ultima_actualizacion": None,
            "estado": "sin_datos",
        }

    campanas_activas = row["campanas_activas"] or 0
    ultima_actualizacion = row["ultima_actualizacion"]

    return {
        "campanas_activas": campanas_activas,
        "ultima_actualizacion": (
            ultima_actualizacion.isoformat()
            if hasattr(ultima_actualizacion, "isoformat")
            else str(ultima_actualizacion)
            if ultima_actualizacion is not None
            else None
        ),
        "estado": "ok" if campanas_activas > 0 and ultima_actualizacion else "sin_datos",
    }
# ruff: noqa: E501
