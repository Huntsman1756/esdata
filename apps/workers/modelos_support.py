from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from sqlalchemy import text


AEAT_SEDE = "https://sede.agenciatributaria.gob.es"


@dataclass
class SyncResult:
    models_checked: int = 0
    campaigns_created: int = 0
    casillas_upserted: int = 0
    instrucciones_upserted: int = 0
    claves_upserted: int = 0
    normativa_upserted: int = 0
    operativa_upserted: int = 0
    operativa_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def build_client(ssl_verify: bool) -> httpx.Client:
    return httpx.Client(
        base_url=AEAT_SEDE,
        follow_redirects=True,
        timeout=30,
        verify=ssl_verify,
        headers={
            "User-Agent": "esdata-bot/1.0 (fiscal data infrastructure bot)",
        },
    )


def _clean_html_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def _normalize_casilla_code(codigo: str) -> str:
    return codigo.zfill(4) if len(codigo) < 4 else codigo


def scrape_casillas_from_page(html: str, modelo_codigo: str) -> list[dict]:
    del modelo_codigo
    casillas = []

    table_rows = re.findall(
        r"<td[^>]*>\s*(\d{1,4})\s*</td>\s*<td[^>]*>(.*?)</td>",
        html,
        re.DOTALL,
    )
    if table_rows:
        for i, (codigo, etiqueta_raw) in enumerate(table_rows):
            etiqueta = _clean_html_text(etiqueta_raw)
            if etiqueta and len(etiqueta) > 3:
                casillas.append(
                    {
                        "codigo": _normalize_casilla_code(codigo),
                        "etiqueta": etiqueta,
                        "orden": i + 1,
                    }
                )
        return casillas

    def_rows = re.findall(
        r"<dt[^>]*>\s*(\d{1,4})\s*</dt>\s*<dd[^>]*>(.*?)</dd>",
        html,
        re.DOTALL,
    )
    if def_rows:
        for i, (codigo, desc_raw) in enumerate(def_rows):
            desc = _clean_html_text(desc_raw)
            if desc:
                casillas.append(
                    {
                        "codigo": _normalize_casilla_code(codigo),
                        "etiqueta": desc[:100],
                        "descripcion": desc if len(desc) > 100 else None,
                        "orden": i + 1,
                    }
                )
        return casillas

    li_rows = re.findall(
        r"<li[^>]*>\s*(\d{1,4})\s*[-–—:]\s*(.*?)</li>",
        html,
        re.DOTALL,
    )
    if li_rows:
        for i, (codigo, etiqueta_raw) in enumerate(li_rows):
            etiqueta = _clean_html_text(etiqueta_raw)
            if etiqueta and len(etiqueta) > 3:
                casillas.append(
                    {
                        "codigo": _normalize_casilla_code(codigo),
                        "etiqueta": etiqueta,
                        "orden": i + 1,
                    }
                )
        return casillas

    return casillas


def scrape_claves_from_page(html: str) -> list[dict]:
    claves = []
    clave_rows = re.findall(
        r"(?:Clave\s*)?([A-Z])\s*[-–—:)\.]\s*([^\n<]{5,80})",
        html,
        re.MULTILINE,
    )
    for codigo, etiqueta in clave_rows:
        etiqueta = etiqueta.strip()
        if etiqueta and len(etiqueta) > 3 and not etiqueta.startswith("http"):
            claves.append({"codigo": codigo, "etiqueta": etiqueta})

    if not claves:
        num_claves = re.findall(
            r"(?:Clave\s*)?(\d{1,2})\s*[-–—:)\.]\s*([^\n<]{5,80})",
            html,
            re.MULTILINE,
        )
        for codigo, etiqueta in num_claves:
            etiqueta = etiqueta.strip()
            if etiqueta and len(etiqueta) > 3 and not etiqueta.startswith("http"):
                claves.append({"codigo": codigo, "etiqueta": etiqueta})

    return claves


def scrape_instructions_from_page(html: str) -> list[dict]:
    instrucciones = []
    section_patterns = [
        (r"Caracter[aí]sticas|¿Qu[eé] es\??", "caracteristicas"),
        (r"[¿Qq]ui[eé]n debe presentar|Obligados|Sujetos pasivos", "quien-debe"),
        (r"[Cc]ómo rellenar|[Cc]ómo cumplimentar|[Cc]ómo presentar", "como-rellenar"),
        (r"[Pp]lazo|[Ff]echa de presentaci[oó]n|[Cc]u[aá]ndo", "plazo"),
    ]

    for pattern, seccion in section_patterns:
        match = re.search(
            rf"(?:<h[23][^>]*>.*?{pattern}.*?</h[23]>|{pattern})",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            continue

        start = match.end()
        content_html = html[start : start + 2000]
        content = re.sub(r"<[^>]+>", "\n", content_html)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        if len(content) <= 50:
            continue

        instrucciones.append(
            {
                "seccion": seccion,
                "titulo": match.group(0).replace("<", " ").replace(">", " ").strip()[:80],
                "contenido": content[:5000],
            }
        )

    return instrucciones


def _infer_operativa_frequency(periodo: str | None, plazo: str | None) -> str | None:
    periodo_value = (periodo or "").lower()
    plazo_value = (plazo or "").lower()
    if "mensual" in periodo_value:
        return "mensual"
    if "trimestral" in periodo_value:
        return "trimestral"
    if "anual" in periodo_value:
        return "anual"
    if "eventual" in periodo_value:
        return "eventual"
    if "mensual" in plazo_value:
        return "mensual"
    if "trimestral" in plazo_value:
        return "trimestral"
    if "anual" in plazo_value:
        return "anual"
    return None


def _infer_operativa_window(plazo: str | None) -> str | None:
    plazo_value = (plazo or "").lower()
    if "primeros veinte dias" in plazo_value or "1 al 20" in plazo_value:
        return "primeros_20_dias_periodo_siguiente"
    if "mes de febrero" in plazo_value:
        return "febrero_ano_siguiente"
    if "un mes" in plazo_value:
        return "1_mes_desde_hecho"
    if "campana de renta" in plazo_value:
        return "campana_renta_aeat"
    if "plazo fijado por la aeat" in plazo_value or "plazos generales" in plazo_value:
        return "plazo_general_aeat"
    return None


def _infer_operativa_channel(presentacion: str | None) -> str | None:
    presentacion_value = (presentacion or "").lower()
    if "electronica" in presentacion_value or "electrónica" in presentacion_value:
        return "electronica"
    if "presencial" in presentacion_value:
        return "presencial"
    return None


def _infer_operativa_category(modelo_codigo: str, impuesto: str | None, obligados: str | None) -> str | None:
    obligados_value = (obligados or "").lower()
    if modelo_codigo in {"124", "216", "296"} or "no residentes" in obligados_value:
        return "retenedor_irnr"
    if modelo_codigo == "303" or "autoliquidar el iva" in obligados_value:
        return "empresario_o_profesional_iva"
    if modelo_codigo == "349":
        return "operador_intracomunitario_iva"
    if modelo_codigo == "390":
        return "sujeto_pasivo_iva"
    if modelo_codigo == "036":
        return "obligado_censal"
    if modelo_codigo == "347":
        return "declarante_operaciones_terceros"
    if modelo_codigo == "111":
        return "retenedor_irpf"
    if modelo_codigo == "115":
        return "retenedor_arrendamientos"
    if modelo_codigo == "100" or "irpf" in obligados_value:
        return "contribuyente_irpf"
    if impuesto:
        return f"obligado_{impuesto.lower()}"
    return None


def derive_campaign_operativa(
    modelo_codigo: str,
    impuesto: str | None,
    periodo: str | None,
    instrucciones: list[dict],
) -> dict:
    who = None
    deadline = None
    presentation = None

    for item in instrucciones:
        section = (item.get("seccion") or "").strip().lower()
        content = item.get("contenido")
        if section in {"quien-debe", "quien_debe", "obligados"} and not who:
            who = content
        elif section in {"plazo", "presentacion", "plazo-presentacion"} and not deadline:
            deadline = content
        elif section in {"como-presentar", "como_presentar", "como-rellenar"} and not presentation:
            presentation = content

    return {
        "categoria_obligado": _infer_operativa_category(modelo_codigo, impuesto, who),
        "frecuencia_presentacion": _infer_operativa_frequency(periodo, deadline),
        "ventana_presentacion": _infer_operativa_window(deadline),
        "canal_presentacion": _infer_operativa_channel(presentation),
        "obligados_resumen": who,
        "plazo_resumen": deadline,
        "presentacion_resumen": presentation,
        "origen_metadato": "worker_derivado",
        "estado_metadato": "borrador",
    }


def _get_campaign_operativa_existing_row(conn, campana_id: int) -> dict | None:
    try:
        row = conn.execute(
            text(
                """
                SELECT campana_id, origen_metadato, estado_metadato, nota
                FROM modelo_campana_operativa
                WHERE campana_id = :campana_id
                """
            ),
            {"campana_id": campana_id},
        ).mappings().first()
    except Exception:
        row = conn.execute(
            text(
                """
                SELECT campana_id, nota
                FROM modelo_campana_operativa
                WHERE campana_id = :campana_id
                """
            ),
            {"campana_id": campana_id},
        ).mappings().first()
    return dict(row) if row else None


def _is_curated_operativa(row: dict | None) -> bool:
    if not row:
        return False

    origen = (row.get("origen_metadato") or "").strip().lower()
    estado = (row.get("estado_metadato") or "").strip().lower()
    nota = (row.get("nota") or "").strip().lower()

    if origen in {"seed_curado", "manual_curado"}:
        return True
    if estado == "curado":
        return True
    return "metadato operativo curado" in nota


def upsert_campaign_operativa(conn, campana_id: int, payload: dict) -> bool:
    existing = _get_campaign_operativa_existing_row(conn, campana_id)
    incoming_origen = (payload.get("origen_metadato") or "").strip().lower()
    params = {"campana_id": campana_id, **payload}

    if existing and _is_curated_operativa(existing) and incoming_origen == "worker_derivado":
        return False

    try:
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana_operativa (
                    campana_id,
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
                )
                VALUES (
                    :campana_id,
                    :categoria_obligado,
                    :frecuencia_presentacion,
                    :ventana_presentacion,
                    :canal_presentacion,
                    :obligados_resumen,
                    :plazo_resumen,
                    :presentacion_resumen,
                    :norma_base,
                    :nota,
                    :origen_metadato,
                    :estado_metadato
                )
                ON CONFLICT (campana_id) DO UPDATE SET
                    categoria_obligado = EXCLUDED.categoria_obligado,
                    frecuencia_presentacion = EXCLUDED.frecuencia_presentacion,
                    ventana_presentacion = EXCLUDED.ventana_presentacion,
                    canal_presentacion = EXCLUDED.canal_presentacion,
                    obligados_resumen = EXCLUDED.obligados_resumen,
                    plazo_resumen = EXCLUDED.plazo_resumen,
                    presentacion_resumen = EXCLUDED.presentacion_resumen,
                    norma_base = EXCLUDED.norma_base,
                    nota = EXCLUDED.nota,
                    origen_metadato = EXCLUDED.origen_metadato,
                    estado_metadato = EXCLUDED.estado_metadato
                """
            ),
            params,
        )
    except Exception:
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana_operativa (
                    campana_id,
                    categoria_obligado,
                    frecuencia_presentacion,
                    ventana_presentacion,
                    canal_presentacion,
                    obligados_resumen,
                    plazo_resumen,
                    presentacion_resumen,
                    norma_base,
                    nota
                )
                VALUES (
                    :campana_id,
                    :categoria_obligado,
                    :frecuencia_presentacion,
                    :ventana_presentacion,
                    :canal_presentacion,
                    :obligados_resumen,
                    :plazo_resumen,
                    :presentacion_resumen,
                    :norma_base,
                    :nota
                )
                ON CONFLICT (campana_id) DO UPDATE SET
                    categoria_obligado = EXCLUDED.categoria_obligado,
                    frecuencia_presentacion = EXCLUDED.frecuencia_presentacion,
                    ventana_presentacion = EXCLUDED.ventana_presentacion,
                    canal_presentacion = EXCLUDED.canal_presentacion,
                    obligados_resumen = EXCLUDED.obligados_resumen,
                    plazo_resumen = EXCLUDED.plazo_resumen,
                    presentacion_resumen = EXCLUDED.presentacion_resumen,
                    norma_base = EXCLUDED.norma_base,
                    nota = EXCLUDED.nota
                """
            ),
            params,
        )

    return True


def upsert_instructions(conn, campana_id: int, instrucciones: list[dict]) -> int:
    count = 0
    for orden, inst in enumerate(instrucciones, start=1):
        conn.execute(
            text(
                """
                INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
                VALUES (:campana_id, :seccion, :titulo, :contenido, :orden)
                ON CONFLICT (campana_id, seccion, titulo) DO UPDATE SET
                    contenido = EXCLUDED.contenido,
                    orden = EXCLUDED.orden
                """
            ),
            {
                "campana_id": campana_id,
                "seccion": inst["seccion"],
                "titulo": inst["titulo"],
                "contenido": inst["contenido"],
                "orden": inst.get("orden", orden),
            },
        )
        count += 1
    return count


def detect_campaigns(html: str, modelo_codigo: str) -> list[str]:
    del modelo_codigo
    campaigns = set()
    years = re.findall(r"(?:20[23]\d)", html)
    for year in years:
        if 2020 <= int(year) <= 2030:
            campaigns.add(year)

    camp_matches = re.findall(r"(?:[Cc]ampa[ñn]a|[Ee]jercicio)\s*(20[23]\d)", html)
    for year in camp_matches:
        campaigns.add(year)

    return sorted(campaigns, reverse=True)


def _campaign_sort_key(campaign: str) -> tuple[int, str]:
    match = re.search(r"(20\d{2})", campaign)
    year = int(match.group(1)) if match else -1
    return (year, campaign)


def pick_active_campaign(campaigns: list[str]) -> str | None:
    if not campaigns:
        return None
    return max(campaigns, key=_campaign_sort_key)


def fetch_page(fetcher, logger, url: str | None, context: str) -> str | None:
    if not url:
        return None

    try:
        with fetcher() as client:
            response = client.get(url)
            if response.status_code == 200:
                return response.text
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to fetch {context} {url}: {exc}")
    return None


def get_model_rows(conn):
    return conn.execute(
        text(
            """
            SELECT codigo, url_info,
                   (SELECT url_instrucciones FROM modelo_campana
                    WHERE modelo_id = aeat_modelo.id AND activo = true
                    ORDER BY campana DESC LIMIT 1) as url_instrucciones
            FROM aeat_modelo
            ORDER BY codigo
            """
        )
    ).fetchall()


def get_model_id(conn, modelo_codigo: str):
    row = conn.execute(
        text("SELECT id FROM aeat_modelo WHERE codigo = :codigo"),
        {"codigo": modelo_codigo},
    ).fetchone()
    return row[0] if row else None


def get_model_metadata(conn, modelo_codigo: str):
    return conn.execute(
        text(
            """
            SELECT codigo, impuesto, periodo
            FROM aeat_modelo
            WHERE codigo = :codigo
            LIMIT 1
            """
        ),
        {"codigo": modelo_codigo},
    ).mappings().first()


def ensure_campaigns(conn, modelo_id: int, modelo_codigo: str, campaigns: list[str], instruction_url: str | None, fallback_url: str, result: SyncResult, logger) -> None:
    existing = conn.execute(
        text(
            """
            SELECT campana FROM modelo_campana
            WHERE modelo_id = :modelo_id
            """
        ),
        {"modelo_id": modelo_id},
    ).fetchall()
    existing_campaigns = {row[0] for row in existing}
    active_campaign = pick_active_campaign(campaigns)

    for campaign in campaigns:
        if campaign not in existing_campaigns:
            url_instr = instruction_url or fallback_url
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, activo)
                    VALUES (:modelo_id, :campana, :url_instr, false)
                    ON CONFLICT (modelo_id, campana) DO UPDATE SET
                        url_instrucciones = EXCLUDED.url_instrucciones
                    """
                ),
                {
                    "modelo_id": modelo_id,
                    "campana": campaign,
                    "url_instr": url_instr,
                },
            )
            result.campaigns_created += 1
            logger.info(f"  New campaign created: {modelo_codigo} -> {campaign}")

    if not active_campaign:
        return

    conn.execute(
        text(
            """
            UPDATE modelo_campana SET activo = false
            WHERE modelo_id = :modelo_id
            """
        ),
        {"modelo_id": modelo_id},
    )
    conn.execute(
        text(
            """
            UPDATE modelo_campana SET activo = true
            WHERE modelo_id = :modelo_id AND campana = :campana
            """
        ),
        {"modelo_id": modelo_id, "campana": active_campaign},
    )


def get_campaign_row(conn, modelo_id: int, campana: str):
    return conn.execute(
        text(
            """
            SELECT id, url_instrucciones FROM modelo_campana
            WHERE modelo_id = :modelo_id AND campana = :campana
            """
        ),
        {"modelo_id": modelo_id, "campana": campana},
    ).fetchone()


def upsert_casillas(conn, campana_id: int, casillas: list[dict]) -> int:
    count = 0
    for casilla in casillas:
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, orden)
                VALUES (:campana_id, :codigo, :etiqueta, :descripcion, :orden)
                ON CONFLICT (campana_id, codigo) DO UPDATE SET
                    etiqueta = EXCLUDED.etiqueta,
                    descripcion = COALESCE(EXCLUDED.descripcion, modelo_casilla.descripcion),
                    orden = EXCLUDED.orden
                """
            ),
            {
                "campana_id": campana_id,
                "codigo": casilla["codigo"],
                "etiqueta": casilla["etiqueta"],
                "descripcion": casilla.get("descripcion"),
                "orden": casilla.get("orden"),
            },
        )
        count += 1
    return count


def upsert_claves(conn, campana_id: int, claves: list[dict]) -> int:
    count = 0
    for clave in claves:
        conn.execute(
            text(
                """
                INSERT INTO modelo_clave (campana_id, codigo, etiqueta)
                VALUES (:campana_id, :codigo, :etiqueta)
                ON CONFLICT (campana_id, codigo) DO UPDATE SET
                    etiqueta = EXCLUDED.etiqueta
                """
            ),
            {
                "campana_id": campana_id,
                "codigo": clave["codigo"],
                "etiqueta": clave["etiqueta"],
            },
        )
        count += 1
    return count


def log_sync_result(conn, result: SyncResult) -> None:
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted,
                doctrina_links_created, error_msg
            ) VALUES (
                'modelos', now(), now(),
                CASE WHEN :errors = 0 THEN 'ok' ELSE 'error' END,
                :models, :casillas, 0, 0, 0, :error_msg
            )
            """
        ),
        {
            "errors": len(result.errors),
            "models": result.models_checked,
            "casillas": result.casillas_upserted,
            "error_msg": "; ".join(result.errors) if result.errors else None,
        },
    )
