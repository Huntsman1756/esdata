import re
from datetime import UTC, datetime

from sqlalchemy import text


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


EXPLICIT_COMPLETENESS_STATES = {
    "completa",
    "parcial",
    "no-casillas-expected",
    "deprecated",
}


def _normalize_explicit_completeness(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized if normalized in EXPLICIT_COMPLETENESS_STATES else None


def _build_truth_contract(
    *,
    has_instructions: bool,
    has_casillas: bool,
    metadata_state: str | None = None,
    explicit_completeness: str | None = None,
) -> tuple[str, bool]:
    explicit_state = _normalize_explicit_completeness(explicit_completeness)
    if explicit_state == "deprecated":
        return "deprecated", True
    if explicit_state == "no-casillas-expected":
        return "no-casillas-expected", True
    if explicit_state == "parcial":
        return "parcial", False
    if explicit_state == "completa":
        return "completa", True
    if not has_instructions or not has_casillas:
        return "parcial", False
    if metadata_state in {None, "inferido"}:
        return "parcial", False
    return "completa", True


def build_modelo_truth_contract(
    *,
    has_instructions: bool,
    has_casillas: bool,
    metadata_state: str | None = None,
    explicit_completeness: str | None = None,
) -> tuple[str, bool]:
    return _build_truth_contract(
        has_instructions=has_instructions,
        has_casillas=has_casillas,
        metadata_state=metadata_state,
        explicit_completeness=explicit_completeness,
    )


def _modelo_evidence_status(completeness: str, verified: bool) -> str:
    if completeness == "parcial" or not verified:
        return "evidence_limited"
    if completeness == "no-casillas-expected":
        return "no_casillas_expected"
    if completeness == "deprecated":
        return "deprecated"
    return "verified"


def _modelo_evidence_notice(completeness: str, verified: bool) -> str:
    if completeness == "no-casillas-expected":
        return (
            "ESData tiene verificado que este modelo no dispone de casillas "
            "estructuradas esperadas en la campana consultada. No inferir "
            "obligatoriedad por supuesto concreto."
        )
    if completeness == "deprecated":
        return (
            "ESData tiene verificado que este modelo no esta vigente o queda "
            "clasificado como deprecated. No presentarlo como modelo actual."
        )
    if completeness == "parcial" or not verified:
        return (
            "Evidencia limitada: ESData expone solo los campos/fuentes oficiales "
            "cargados para este modelo y no prueba instrucciones completas, "
            "obligatoriedad ni aplicabilidad a un supuesto concreto."
        )
    return "ESData tiene evidencia suficiente para el contrato operativo declarado."


def _modelo_recurso_title(codigo: str, tipo_recurso: str, formato: str | None = None) -> str:
    label = (tipo_recurso or "recurso_oficial").replace("_", " ").strip().title()
    if formato:
        return f"{label} del modelo {codigo} ({formato})"
    return f"{label} del modelo {codigo}"


GENERIC_MODELO_RECURSO_URL_FRAGMENTS = (
    "/Sede/condiciones-uso-sede-electronica/",
    "/Sede/inicio.html",
    "/Sede/todas-gestiones.html",
    "/Sede/impuestos-tasas.html",
)


CAMPAIGN_BEARING_RESOURCE_TYPES = {
    "aeat_formato",
    "aeat_instrucciones",
    "modelo_recurso:ayuda_tecnica_presentacion",
    "modelo_recurso:diseno_registro",
    "modelo_recurso:formulario_html",
    "modelo_recurso:formulario_pdf",
    "modelo_recurso:instrucciones",
}


CAMPAIGN_NOT_ASSERTABLE_NOTICE = (
    "Campana no afirmable con maxima exactitud fiscal: el valor disponible es "
    "persistido o inferido internamente, pero no esta verificado por evidencia "
    "oficial directa o vinculo documental inequivoco."
)


def _is_exposable_modelo_recurso(tipo_recurso: str | None, url_recurso: str | None) -> bool:
    if not url_recurso:
        return False
    if tipo_recurso == "recurso_oficial":
        return False
    return not any(fragment in url_recurso for fragment in GENERIC_MODELO_RECURSO_URL_FRAGMENTS)


def _extract_campaign_candidate_years(*values: str | None) -> list[str]:
    current_year = datetime.now(UTC).year
    years: set[str] = set()
    for value in values:
        for match in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", value or ""):
            year = int(match)
            if 1990 <= year <= current_year + 1:
                years.add(match)
    return sorted(years)


def _resource_proves_campaign(resource: dict, candidate: str | None) -> bool:
    if not candidate:
        return False
    if resource.get("proves_campaign") is not True:
        return False
    years = resource.get("years") or []
    return candidate in years or resource.get("campana") == candidate


def _campaign_notice(status: str) -> str:
    if status == "resolved_strong":
        return "Campana afirmable: existe evidencia oficial directa o vinculo documental inequivoco."
    if status == "resolved_weak":
        return CAMPAIGN_NOT_ASSERTABLE_NOTICE
    if status == "conflict":
        return (
            "Campana no afirmable: existen anos documentales contradictorios. "
            "El sistema debe abstenerse de seleccionar campana."
        )
    return "Campana no afirmable: no hay evidencia suficiente para determinar una campana afirmable."


def _build_campana_selection(campana_activa: str | None, resources: list[dict]) -> dict:
    evidence = []
    resource_years: set[str] = set()

    for resource in resources:
        tipo = resource.get("tipo")
        if tipo not in CAMPAIGN_BEARING_RESOURCE_TYPES:
            continue
        years = _extract_campaign_candidate_years(
            resource.get("url"),
            resource.get("titulo"),
            resource.get("fecha"),
        )
        if not years:
            continue
        resource_years.update(years)
        evidence.append(
            {
                "tipo": tipo,
                "url": resource.get("url"),
                "years": years,
                "reason": "campaign_bearing_resource_year",
            }
        )

    active_year = campana_activa if campana_activa and campana_activa.isdigit() else None
    evidence_years = ({active_year} if active_year else set()) | resource_years
    conflict = len(evidence_years) > 1
    conflict_years = sorted(evidence_years)
    conflict_span = (
        max(int(year) for year in conflict_years) - min(int(year) for year in conflict_years)
        if conflict
        else 0
    )
    conflict_severity = "strong" if conflict_span >= 3 else "weak" if conflict else "none"
    if conflict:
        resolution_status = "conflict"
    elif active_year or resource_years:
        candidate = campana_activa or next(iter(sorted(resource_years)), None)
        resolution_status = (
            "resolved_strong"
            if any(_resource_proves_campaign(resource, candidate) for resource in resources)
            else "resolved_weak"
        )
    else:
        resolution_status = "insufficient_evidence"
    candidate = None if conflict else campana_activa or next(iter(sorted(resource_years)), None)
    safe_to_assert = resolution_status == "resolved_strong"
    verification_level = {
        "resolved_strong": "direct_official",
        "resolved_weak": "inferred_internal",
        "conflict": "contradictory",
        "insufficient_evidence": "insufficient",
    }.get(resolution_status, "insufficient")
    notice = None
    if conflict:
        notice = (
            "Conflicto semantico: existen recursos tecnicos/anuales con anos distintos "
            "de campana_activa. No seleccionar automaticamente una campana como verdad "
            "definitiva sin revision documental."
        )

    return {
        "campana_persistida": campana_activa,
        "campana_afirmable": candidate if safe_to_assert else None,
        "campana_candidata": candidate,
        "campana_resolution_status": resolution_status,
        "campana_verification_level": verification_level,
        "campana_safe_to_assert": safe_to_assert,
        "campana_user_notice": _campaign_notice(resolution_status),
        "campana_evidence": evidence if resolution_status in {"resolved_strong", "resolved_weak"} else [],
        "campana_conflict": conflict,
        "campana_conflict_severity": conflict_severity,
        "campana_conflict_years": conflict_years if conflict else [],
        "campana_conflict_notice": notice,
        "campana_conflict_evidence": evidence if conflict else [],
    }


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
    explicit_completeness = (
        operativa_row["completeness_estado"]
        if operativa_row and operativa_row.get("completeness_estado")
        else None
    )
    return build_modelo_truth_contract(
        has_instructions=has_instructions,
        has_casillas=has_casillas,
        metadata_state=metadata_state,
        explicit_completeness=explicit_completeness,
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
                    estado_metadato,
                    completeness_estado
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
              AND COALESCE(activo, true) = true
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
                WHERE modelo_id = (
                    SELECT id
                    FROM aeat_modelo
                    WHERE codigo = :codigo
                      AND COALESCE(activo, true) = true
                )
                  AND campana = :campana
                LIMIT 1
                """
            ),
            {"codigo": codigo, "campana": campana},
        ).mappings().first()

    try:
        return db.execute(
            text(
                """
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana_activa((
                    SELECT id
                    FROM aeat_modelo
                    WHERE codigo = :codigo
                      AND COALESCE(activo, true) = true
                ))
                """
            ),
            {"codigo": codigo},
        ).mappings().first()
    except Exception:
        return db.execute(
            text(
                """
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana
                WHERE modelo_id = (
                    SELECT id
                    FROM aeat_modelo
                    WHERE codigo = :codigo
                      AND COALESCE(activo, true) = true
                )
                  AND activo = true
                ORDER BY campana DESC
                LIMIT 1
                """
            ),
            {"codigo": codigo},
        ).mappings().first()


def list_modelos_summary(db):
    url_listado_expr = "m.url_listado"
    url_listado_group = ", m.url_listado"
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name
        rows = db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'aeat_modelo'
                  AND column_name = 'url_listado'
                LIMIT 1
                """
            )
        ).first() if dialect != "sqlite" else db.execute(text("PRAGMA table_info(aeat_modelo)")).fetchall()
        if dialect == "sqlite":
            has_url_listado = any(row[1] == "url_listado" for row in rows)
        else:
            has_url_listado = rows is not None
        if not has_url_listado:
            url_listado_expr = "NULL AS url_listado"
            url_listado_group = ""
    except Exception:
        url_listado_expr = "NULL AS url_listado"
        url_listado_group = ""

    return db.execute(
        text(
            f"""
            SELECT
                m.codigo,
                m.nombre,
                m.periodo,
                m.impuesto,
                m.url_info,
                {url_listado_expr},
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
            WHERE COALESCE(m.activo, true) = true
            GROUP BY m.id, m.codigo, m.nombre, m.periodo, m.impuesto, m.url_info{url_listado_group}
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


def list_campaign_recursos(db, campana_id: int):
    rows = db.execute(
        text(
            """
            SELECT
                tipo_recurso,
                formato,
                url_recurso,
                sha256_contenido,
                fecha_publicacion_recurso
            FROM modelo_recurso
            WHERE campana_id = :campana_id
              AND COALESCE(activa, true) = true
            ORDER BY tipo_recurso, url_recurso
            """
        ),
        {"campana_id": campana_id},
    ).mappings()
    return [
        row
        for row in rows
        if _is_exposable_modelo_recurso(row["tipo_recurso"], row["url_recurso"])
    ]


def _campaign_casillas_filters(
    *,
    campana_id: int,
    q: str | None = None,
    tipo_casilla: str | None = None,
    pagina: int | None = None,
) -> tuple[str, dict]:
    where_parts = ["campana_id = :campana_id", "activa = true"]
    params: dict[str, object] = {"campana_id": campana_id}
    if q:
        where_parts.append(
            """
            (
                LOWER(codigo) LIKE :q_like
                OR LOWER(etiqueta) LIKE :q_like
                OR LOWER(COALESCE(descripcion, '')) LIKE :q_like
            )
            """
        )
        params["q_like"] = f"%{q.lower()}%"
    if tipo_casilla:
        where_parts.append("tipo_casilla = :tipo_casilla")
        params["tipo_casilla"] = tipo_casilla
    if pagina is not None:
        where_parts.append("pagina = :pagina")
        params["pagina"] = pagina
    return " AND ".join(where_parts), params


def count_campaign_casillas(
    db,
    campana_id: int,
    *,
    q: str | None = None,
    tipo_casilla: str | None = None,
    pagina: int | None = None,
) -> int:
    where_clause, params = _campaign_casillas_filters(
        campana_id=campana_id,
        q=q,
        tipo_casilla=tipo_casilla,
        pagina=pagina,
    )
    row = db.execute(
        text(
            f"""
            SELECT COUNT(*) AS total
            FROM modelo_casilla
            WHERE {where_clause}
            """
        ),
        params,
    ).mappings().first()
    return int(row["total"]) if row else 0


def get_campaign_for_casillas(db, codigo: str, campana: str | None = None) -> dict:
    """Select the campaign used to expose model fields.

    If a caller requests a specific campaign, use it strictly. Without an
    explicit campaign, prefer the active campaign, but do not hide official
    parsed fields if the active campaign is empty and a newer/previous campaign
    has casillas. This keeps the response evidence-limited and transparent
    instead of silently returning an empty list while usable data exists.
    """

    active_row = get_active_campaign(db, codigo)
    requested_row = get_active_campaign(db, codigo, campana) if campana else active_row
    active_campaign = active_row["campana"] if active_row else None

    if campana or not requested_row:
        return {
            "campaign": requested_row,
            "active_campaign": active_campaign,
            "selection_notice": None,
        }

    active_total = count_campaign_casillas(db, requested_row["id"])
    if active_total > 0:
        return {
            "campaign": requested_row,
            "active_campaign": active_campaign,
            "selection_notice": None,
        }

    fallback_row = db.execute(
        text(
            """
            SELECT
                mc.id,
                mc.campana,
                mc.url_instrucciones,
                mc.url_normativa,
                mc.url_formato
            FROM modelo_campana mc
            JOIN aeat_modelo m ON m.id = mc.modelo_id
            JOIN modelo_casilla c ON c.campana_id = mc.id AND c.activa = true
            WHERE m.codigo = :codigo
              AND COALESCE(m.activo, true) = true
            GROUP BY mc.id, mc.campana, mc.url_instrucciones, mc.url_normativa, mc.url_formato
            ORDER BY mc.campana DESC
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).mappings().first()

    if fallback_row and fallback_row["id"] != requested_row["id"]:
        return {
            "campaign": fallback_row,
            "active_campaign": active_campaign,
            "selection_notice": (
                f"La campana persistida {active_campaign} no tiene casillas parseadas; "
                f"se devuelven casillas oficiales de la campana {fallback_row['campana']}."
            ),
        }

    return {
        "campaign": requested_row,
        "active_campaign": active_campaign,
        "selection_notice": None,
    }


def list_campaign_casillas(
    db,
    campana_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    q: str | None = None,
    tipo_casilla: str | None = None,
    pagina: int | None = None,
):
    where_clause, params = _campaign_casillas_filters(
        campana_id=campana_id,
        q=q,
        tipo_casilla=tipo_casilla,
        pagina=pagina,
    )
    pagination_clause = ""
    if limit is not None:
        pagination_clause = "LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
    return db.execute(
        text(
            f"""
            SELECT codigo, etiqueta, descripcion, tipo_casilla, pagina, orden
            FROM modelo_casilla
            WHERE {where_clause}
            ORDER BY COALESCE(orden, 2147483647), codigo
            {pagination_clause}
            """
        ),
        params,
    ).mappings()


def list_campaign_claves(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT
                codigo,
                etiqueta,
                descripcion,
                tipo_clave,
                COALESCE(tipo, tipo_clave, 'CLAVE') AS tipo,
                criterio_aplicacion,
                exclusiones,
                source_url,
                source_hash,
                CAST(capture_date AS TEXT) AS capture_date
            FROM modelo_clave
            WHERE campana_id = :campana_id AND activa = true
            ORDER BY COALESCE(tipo, tipo_clave, 'CLAVE'), codigo
            """
        ),
        {"campana_id": campana_id},
    ).mappings()


def list_campaign_instructions(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT
                seccion,
                titulo,
                contenido,
                orden,
                COALESCE(texto, contenido) AS texto,
                casilla_referencia,
                source_url,
                source_hash,
                CAST(capture_date AS TEXT) AS capture_date
            FROM modelo_instruccion
            WHERE campana_id = :campana_id
            ORDER BY orden
            """
        ),
        {"campana_id": campana_id},
    ).mappings()


def list_campaign_reglas_inclusion(db, campana_id: int):
    return db.execute(
        text(
            """
            SELECT
                supuesto,
                decision,
                condicion,
                umbral,
                fuente_normativa,
                source_url,
                source_hash,
                CAST(capture_date AS TEXT) AS capture_date
            FROM modelo_regla_inclusion
            WHERE campana_id = :campana_id
            ORDER BY supuesto
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
        proves_campaign: bool = False,
        campaign_evidence_role: str | None = None,
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
                "proves_campaign": proves_campaign,
                "campaign_evidence_role": campaign_evidence_role
                or ("weak" if tipo in CAMPAIGN_BEARING_RESOURCE_TYPES else "none"),
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

        for row in list_campaign_recursos(db, camp_row["id"]):
            url = row["url_recurso"]
            organismo = "BOE" if url and "boe.es" in url else "AEAT"
            add_source(
                tipo=f"modelo_recurso:{row['tipo_recurso']}",
                titulo=_modelo_recurso_title(codigo, row["tipo_recurso"], row["formato"]),
                url=url,
                organismo=organismo,
                oficial=True,
                campana_value=campana_activa,
                fecha=str(row["fecha_publicacion_recurso"]) if row["fecha_publicacion_recurso"] else None,
                nota=(
                    "Recurso oficial activo cacheado en modelo_recurso; "
                    f"sha256={str(row['sha256_contenido'])[:12]}..."
                ),
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
        **_build_campana_selection(campana_activa, fuentes),
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
        proves_campaign: bool = False,
        campaign_evidence_role: str | None = None,
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
                "proves_campaign": proves_campaign,
                "campaign_evidence_role": campaign_evidence_role
                or ("weak" if tipo in CAMPAIGN_BEARING_RESOURCE_TYPES else "none"),
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

        for row in list_campaign_recursos(db, camp_row["id"]):
            add_artefacto(
                tipo=f"modelo_recurso:{row['tipo_recurso']}",
                titulo=_modelo_recurso_title(codigo, row["tipo_recurso"], row["formato"]),
                url=row["url_recurso"],
                oficial=True,
                campana_value=campana_activa,
                fecha=str(row["fecha_publicacion_recurso"]) if row["fecha_publicacion_recurso"] else None,
                formato=row["formato"],
                nota=(
                    "Recurso oficial activo cacheado en modelo_recurso; "
                    f"sha256={str(row['sha256_contenido'])[:12]}..."
                ),
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
        **_build_campana_selection(campana_activa, artefactos),
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
        "campana_persistida": (fuentes or {}).get("campana_persistida", campana_activa),
        "campana_afirmable": (fuentes or {}).get("campana_afirmable"),
        "campana_candidata": (fuentes or {}).get("campana_candidata"),
        "campana_resolution_status": (fuentes or {}).get("campana_resolution_status", "insufficient_evidence"),
        "campana_verification_level": (fuentes or {}).get("campana_verification_level", "insufficient"),
        "campana_safe_to_assert": (fuentes or {}).get("campana_safe_to_assert", False),
        "campana_user_notice": (fuentes or {}).get("campana_user_notice"),
        "campana_evidence": (fuentes or {}).get("campana_evidence", []),
        "campana_conflict": (fuentes or {}).get("campana_conflict", False),
        "campana_conflict_severity": (fuentes or {}).get("campana_conflict_severity", "none"),
        "campana_conflict_years": (fuentes or {}).get("campana_conflict_years", []),
        "campana_conflict_notice": (fuentes or {}).get("campana_conflict_notice"),
        "campana_conflict_evidence": (fuentes or {}).get("campana_conflict_evidence", []),
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
    explicit_completeness = (
        operativa_row["completeness_estado"]
        if operativa_row and operativa_row.get("completeness_estado")
        else None
    )
    completeness, verified = build_modelo_truth_contract(
        has_instructions=bool(instrucciones),
        has_casillas=bool(casillas),
        metadata_state=estado_metadato,
        explicit_completeness=explicit_completeness,
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
        "completeness_estado": explicit_completeness,
        "completeness": completeness,
        "verified": verified,
        "evidence_status": _modelo_evidence_status(completeness, verified),
        "evidence_notice": _modelo_evidence_notice(completeness, verified),
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


MODELO_124_OPERATION_TERMS = (
    "activo financiero",
    "activos financieros",
    "transmision",
    "transmisión",
    "amortizacion",
    "amortización",
    "reembolso",
    "canje",
    "conversion",
    "conversión",
)


def _is_modelo_124_specific_operation(tipo_operacion: str, tipo_renta: str) -> bool:
    operation_text = f"{tipo_operacion} {tipo_renta}".lower()
    has_financial_asset = "activo financiero" in operation_text or "activos financieros" in operation_text
    has_specific_operation = any(
        term in operation_text
        for term in MODELO_124_OPERATION_TERMS
        if term not in {"activo financiero", "activos financieros"}
    )
    return has_financial_asset and has_specific_operation


SOCIEDAD_VALORES_MODEL_RULES = {
    "123": {
        "ambito": "retenciones_residentes",
        "condicion_aplicacion": "Si la sociedad practica retenciones o ingresos a cuenta sobre rendimientos del capital mobiliario de contribuyentes IRPF residentes.",
        "matched_factors": ["clientes_residentes", "capital_mobiliario", "retenciones"],
    },
    "124": {
        "ambito": "retenciones_activos_financieros",
        "condicion_aplicacion": "Si existen rentas o rendimientos del capital mobiliario derivados de transmision, amortizacion, reembolso, canje o conversion de activos.",
        "matched_factors": ["clientes_residentes", "capital_mobiliario", "retenciones"],
    },
    "193": {
        "ambito": "informativa_residentes",
        "condicion_aplicacion": "Si corresponde declaracion informativa anual de retenciones e ingresos a cuenta sobre determinados rendimientos del capital mobiliario.",
        "matched_factors": ["clientes_residentes", "capital_mobiliario", "declaracion_informativa"],
    },
    "216": {
        "ambito": "retenciones_no_residentes",
        "condicion_aplicacion": "Si la sociedad retiene o ingresa a cuenta rentas sujetas al IRNR obtenidas por clientes no residentes sin establecimiento permanente.",
        "matched_factors": ["clientes_no_residentes", "irnr", "retenciones"],
    },
    "296": {
        "ambito": "informativa_no_residentes",
        "condicion_aplicacion": "Si corresponde resumen o declaracion informativa de retenciones e ingresos a cuenta del IRNR.",
        "matched_factors": ["clientes_no_residentes", "irnr", "declaracion_informativa"],
    },
    "200": {
        "ambito": "obligacion_sociedad",
        "condicion_aplicacion": "Si se consulta la obligacion propia de la sociedad por Impuesto sobre Sociedades; no se deriva por si sola de tener clientes residentes o no residentes.",
        "matched_factors": ["sociedad"],
        "clasificacion": "requiere_verificacion",
    },
}


SOCIEDAD_VALORES_EXCLUDED = {
    "100": "IRPF anual de personas fisicas; no es un modelo de la sociedad de valores por tener clientes.",
    "111": "Retenciones sobre rendimientos del trabajo o actividades economicas; no identifica clientes de sociedad de valores.",
    "115": "Retenciones por arrendamientos; no identifica la operativa de clientes residentes/no residentes.",
    "190": "Resumen anual de rendimientos del trabajo o actividades economicas; no identifica clientes de sociedad de valores.",
}


IRNR_296_TIPO_RENTA_CLAVES = {
    "dividendos": {
        "codigo": "1",
        "label": "tipo_renta_dividendos",
        "needle": "dividend",
    },
    "intereses": {
        "codigo": "2",
        "label": "tipo_renta_intereses",
        "needle": "inter",
    },
}


RESIDENTE_193_TIPO_RENTA_CLAVES = {
    "dividendos": {
        "label": "tipo_renta_dividendos_residentes",
        "keys": (
            ("CLAVE_PERCEPCION", "PERCEPCION_A", "participacion"),
            ("NATURALEZA", "NAT_A_02", "dividend"),
        ),
    },
    "intereses": {
        "label": "tipo_renta_intereses_residentes",
        "keys": (
            ("CLAVE_PERCEPCION", "PERCEPCION_B", "cesion"),
            ("NATURALEZA", "NAT_BD_01", "inter"),
        ),
    },
}


def _model_rows_by_code(db, codigos: list[str]) -> dict[str, dict]:
    if not codigos:
        return {}
    placeholders = ",".join([f":c{i}" for i in range(len(codigos))])
    rows = db.execute(
        text(
            f"""
            SELECT codigo, nombre, periodo, impuesto, url_info
            FROM aeat_modelo
            WHERE codigo IN ({placeholders})
              AND COALESCE(activo, true) = true
            """
        ),
        {f"c{i}": codigo for i, codigo in enumerate(codigos)},
    ).mappings()
    return {row["codigo"]: dict(row) for row in rows}


def _modelo_296_tipo_renta_evidence(db, tipo_renta_norm: str) -> dict | None:
    config = IRNR_296_TIPO_RENTA_CLAVES.get(tipo_renta_norm)
    if not config:
        return None
    row = db.execute(
        text(
            """
            SELECT
                cl.codigo,
                cl.etiqueta,
                cl.descripcion,
                cl.criterio_aplicacion,
                cl.source_url,
                cl.source_hash,
                cl.capture_date
            FROM aeat_modelo m
            JOIN modelo_campana mc ON mc.modelo_id = m.id
            JOIN modelo_clave cl ON cl.campana_id = mc.id
            WHERE m.codigo = '296'
              AND COALESCE(m.activo, true) = true
              AND COALESCE(mc.activo, true) = true
              AND COALESCE(cl.activa, true) = true
              AND cl.codigo = :codigo
              AND COALESCE(cl.source_hash, '') <> ''
              AND cl.capture_date IS NOT NULL
              AND lower(COALESCE(cl.etiqueta, '') || ' ' || COALESCE(cl.descripcion, '')) LIKE :needle
            ORDER BY mc.id DESC, cl.id DESC
            LIMIT 1
            """
        ),
        {
            "codigo": config["codigo"],
            "needle": f"%{config['needle']}%",
        },
    ).mappings().first()
    if not row:
        return None
    capture_date = row["capture_date"]
    return {
        "label": config["label"],
        "source": "modelo_clave",
        "source_document": f"296:CLAVE_RENTA:{row['codigo']}",
        "source_url": row["source_url"],
        "source_hash": row["source_hash"],
        "capture_date": (
            capture_date.isoformat()
            if hasattr(capture_date, "isoformat")
            else str(capture_date)
        ),
        "excerpt": row["etiqueta"] or row["descripcion"] or row["criterio_aplicacion"],
        "official": True,
    }


def _modelo_193_tipo_renta_evidence(db, tipo_renta_norm: str) -> dict | None:
    config = RESIDENTE_193_TIPO_RENTA_CLAVES.get(tipo_renta_norm)
    if not config:
        return None
    evidences = []
    for tipo, codigo, needle in config["keys"]:
        row = db.execute(
            text(
                """
                SELECT
                    cl.codigo,
                    cl.tipo,
                    cl.tipo_clave,
                    cl.etiqueta,
                    cl.descripcion,
                    cl.criterio_aplicacion,
                    cl.source_url,
                    cl.source_hash,
                    cl.capture_date
                FROM aeat_modelo m
                JOIN modelo_campana mc ON mc.modelo_id = m.id
                JOIN modelo_clave cl ON cl.campana_id = mc.id
                WHERE m.codigo = '193'
                  AND COALESCE(m.activo, true) = true
                  AND COALESCE(mc.activo, true) = true
                  AND COALESCE(cl.activa, true) = true
                  AND cl.codigo = :codigo
                  AND COALESCE(cl.tipo, cl.tipo_clave) = :tipo
                  AND COALESCE(cl.source_hash, '') <> ''
                  AND cl.capture_date IS NOT NULL
                  AND lower(COALESCE(cl.etiqueta, '') || ' ' || COALESCE(cl.descripcion, '')) LIKE :needle
                ORDER BY mc.id DESC, cl.id DESC
                LIMIT 1
                """
            ),
            {
                "codigo": codigo,
                "tipo": tipo,
                "needle": f"%{needle}%",
            },
        ).mappings().first()
        if not row:
            return None
        capture_date = row["capture_date"]
        source_type = row["tipo"] or row["tipo_clave"] or tipo
        evidences.append(
            {
                "source": "modelo_clave",
                "source_document": f"193:{source_type}:{row['codigo']}",
                "source_url": row["source_url"],
                "source_hash": row["source_hash"],
                "capture_date": (
                    capture_date.isoformat()
                    if hasattr(capture_date, "isoformat")
                    else str(capture_date)
                ),
                "excerpt": row["etiqueta"] or row["descripcion"] or row["criterio_aplicacion"],
                "official": True,
            }
        )
    return {
        "label": config["label"],
        "evidences": evidences,
    }


def list_modelos_por_supuesto(
    db,
    *,
    tipo_entidad: str,
    clientes_residentes: bool,
    clientes_no_residentes: bool,
    tipo_renta: str | None = None,
    tipo_operacion: str | None = None,
    incluir_obligacion_sociedad: bool = False,
) -> dict:
    """Return conservative AEAT model candidates for a fiscal scenario.

    This intentionally does not turn generic model existence into an
    obligation. "confirmado" is reserved for future explicit obligation links.
    """
    tipo_entidad_norm = (tipo_entidad or "").strip().lower()
    tipo_renta_norm = (tipo_renta or "").strip().lower()
    tipo_operacion_norm = (tipo_operacion or "").strip().lower()

    scenario_inputs = {
        "tipo_entidad": tipo_entidad_norm,
        "clientes_residentes": bool(clientes_residentes),
        "clientes_no_residentes": bool(clientes_no_residentes),
        "tipo_renta": tipo_renta_norm or None,
        "tipo_operacion": tipo_operacion_norm or None,
        "incluir_obligacion_sociedad": bool(incluir_obligacion_sociedad),
    }

    if tipo_entidad_norm != "sociedad_valores":
        return {
            "status": "no_verified",
            "verified": False,
            "scenario_inputs": scenario_inputs,
            "modelos": [],
            "excluded_modelos": [],
            "warnings": [
                "ESData no tiene un clasificador de modelos por supuesto para este tipo_entidad. No se infieren modelos."
            ],
            "confidence": {
                "nivel": 0,
                "nivel_texto": "baja",
                "review_required": True,
                "aviso": "NO VERIFICADO: supuesto no soportado por clasificador de modelos.",
            },
        }

    candidate_codes: list[str] = []
    dynamic_excluded: dict[str, str] = {}
    if clientes_residentes:
        candidate_codes.extend(["123", "193"])
        if _is_modelo_124_specific_operation(tipo_operacion_norm, tipo_renta_norm):
            candidate_codes.append("124")
        else:
            dynamic_excluded["124"] = (
                "activos_financieros_no_confirmados_para_124: el Modelo 124 solo se "
                "ofrece como candidato cuando el supuesto identifica transmision, "
                "amortizacion, reembolso, canje o conversion de activos financieros."
            )
    if clientes_no_residentes:
        candidate_codes.extend(["216", "296"])
    if incluir_obligacion_sociedad:
        candidate_codes.append("200")

    ordered_codes = []
    for codigo in candidate_codes:
        if codigo not in ordered_codes:
            ordered_codes.append(codigo)

    rows = _model_rows_by_code(db, ordered_codes + list(SOCIEDAD_VALORES_EXCLUDED))
    tipo_renta_296_evidence = _modelo_296_tipo_renta_evidence(db, tipo_renta_norm)
    tipo_renta_193_evidence = _modelo_193_tipo_renta_evidence(db, tipo_renta_norm)
    modelos = []
    for codigo in ordered_codes:
        row = rows.get(codigo)
        if not row:
            continue
        rule = SOCIEDAD_VALORES_MODEL_RULES[codigo]
        clasificacion = rule.get("clasificacion", "candidato")
        missing_factors = ["evidencia_explicita_de_obligatoriedad_para_sociedad_valores"]
        matched_factors = list(rule["matched_factors"])
        evidencias = [
            {
                "source": "aeat_modelo",
                "source_document": codigo,
                "source_url": row.get("url_info"),
                "source_hash": None,
                "capture_date": None,
                "excerpt": row["nombre"],
                "official": True,
            }
        ]
        if codigo == "296" and tipo_renta_norm in IRNR_296_TIPO_RENTA_CLAVES:
            if tipo_renta_296_evidence:
                matched_factors.append(tipo_renta_296_evidence["label"])
                evidencias.append(tipo_renta_296_evidence)
                missing_factors.append("convenio_o_regla_domestica_por_pais")
                missing_factors.append("certificado_residencia_o_protocolo_si_aplica")
            else:
                missing_factors.append(f"tipo_renta_{tipo_renta_norm}_sin_hash_o_captura")
        if codigo == "193" and tipo_renta_norm in RESIDENTE_193_TIPO_RENTA_CLAVES:
            if tipo_renta_193_evidence:
                matched_factors.append(tipo_renta_193_evidence["label"])
                evidencias.extend(tipo_renta_193_evidence["evidences"])
                missing_factors.append("perceptor_y_retencion_concreta")
                missing_factors.append("exencion_o_no_sujecion_si_aplica")
            else:
                missing_factors.append(
                    f"tipo_renta_{tipo_renta_norm}_residentes_sin_doble_clave_hash_o_captura"
                )
        if codigo == "124":
            matched_factors.append("operacion_activos_financieros_124")
            missing_factors.append("claves_instrucciones_y_reglas_124_pendientes")
        modelos.append(
            {
                "codigo": codigo,
                "nombre": row["nombre"],
                "clasificacion": clasificacion,
                "condicion_aplicacion": rule["condicion_aplicacion"],
                "motivo": (
                    "ESData contiene el modelo AEAT y su descripcion encaja con el factor fiscal indicado; "
                    "no se marca como obligatorio sin un enlace explicito de aplicabilidad."
                ),
                "ambito": rule["ambito"],
                "periodo": row.get("periodo"),
                "impuesto": row.get("impuesto"),
                "candidate_score": 0.65 if clasificacion == "candidato" else 0.35,
                "matched_factors": matched_factors,
                "missing_factors": missing_factors,
                "evidencia": evidencias,
            }
        )

    excluded_modelos = [
        {"codigo": codigo, "reason": reason}
        for codigo, reason in {**dynamic_excluded, **SOCIEDAD_VALORES_EXCLUDED}.items()
    ]

    return {
        "status": "evidence_limited" if modelos else "no_verified",
        "verified": False,
        "scenario_inputs": scenario_inputs,
        "modelos": modelos,
        "excluded_modelos": excluded_modelos,
        "warnings": [
            "No afirmar obligatoriedad: la salida clasifica candidatos y condiciones, no asesoramiento fiscal definitivo.",
            "Confirmar con fuente oficial AEAT/BOE o asesoria fiscal antes de presentar modelos.",
        ],
        "confidence": {
            "nivel": 1 if modelos else 0,
            "nivel_texto": "media" if modelos else "baja",
            "review_required": True,
            "aviso": "EVIDENCIA LIMITADA: modelos candidatos con fuente AEAT en ESData, sin prueba explicita de obligatoriedad para todo el supuesto.",
            "fuentes": [f"modelo_{item['codigo']}" for item in modelos],
        },
    }


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
