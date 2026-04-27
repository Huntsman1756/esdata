from sqlalchemy import text


def list_calendario(
    db,
    codigo: str | None = None,
    campana: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    activo: bool = True,
):
    params: dict = {}

    base = """
        SELECT
            c.id,
            c.campana_id,
            m.codigo AS modelo_codigo,
            m.nombre AS modelo_nombre,
            mc.campana,
            c.fecha_inicio_presentacion,
            c.fecha_fin_presentacion,
            c.fecha_fin_prorroga,
            c.observaciones,
            c.fuente,
            c.activo
        FROM modelo_fiscal_calendar c
        JOIN modelo_campana mc ON mc.id = c.campana_id
        JOIN aeat_modelo m ON m.id = mc.modelo_id
        WHERE 1 = 1
    """

    if codigo:
        params["codigo"] = codigo
        base += " AND m.codigo = :codigo"
    if campana:
        params["campana"] = campana
        base += " AND mc.campana = :campana"
    if desde:
        params["desde"] = desde
        base += " AND c.fecha_fin_presentacion >= :desde"
    if hasta:
        params["hasta"] = hasta
        base += " AND c.fecha_inicio_presentacion <= :hasta"
    if activo:
        params["activo"] = True
        base += " AND c.activo = :activo"

    base += " ORDER BY c.fecha_fin_presentacion"

    rows = db.execute(text(base), params).mappings()
    return [dict(r) for r in rows]


def get_proximo_vencimiento(db, desde: str | None = None):
    base = """
        SELECT
            c.id,
            c.campana_id,
            m.codigo AS modelo_codigo,
            m.nombre AS modelo_nombre,
            mc.campana,
            c.fecha_inicio_presentacion,
            c.fecha_fin_presentacion,
            c.fecha_fin_prorroga,
            c.observaciones,
            c.fuente,
            c.activo,
            LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                AS fecha_limite,
            CASE
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE THEN 'vencido'
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE + INTERVAL '7 days' THEN 'proximo'
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE + INTERVAL '30 days' THEN 'pronto'
                ELSE 'futuro'
            END AS estado
        FROM modelo_fiscal_calendar c
        JOIN modelo_campana mc ON mc.id = c.campana_id
        JOIN aeat_modelo m ON m.id = mc.modelo_id
        WHERE c.activo = true
          AND LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
              >= CURRENT_DATE
    """

    if desde:
        base += " AND c.fecha_fin_presentacion >= :desde"

    base += " ORDER BY fecha_limite ASC LIMIT 1"

    params = {}
    if desde:
        params["desde"] = desde

    row = db.execute(text(base), params).mappings().first()
    return row


def get_calendario_modelo(db, codigo: str, campana: str | None = None):
    base = """
        SELECT
            c.id,
            c.campana_id,
            m.codigo AS modelo_codigo,
            m.nombre AS modelo_nombre,
            mc.campana,
            c.fecha_inicio_presentacion,
            c.fecha_fin_presentacion,
            c.fecha_fin_prorroga,
            c.observaciones,
            c.fuente,
            c.activo,
            LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                AS fecha_limite,
            CASE
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE THEN 'vencido'
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE + INTERVAL '7 days' THEN 'proximo'
                WHEN LEAST(c.fecha_fin_presentacion, COALESCE(c.fecha_fin_prorroga, c.fecha_fin_presentacion))
                    <= CURRENT_DATE + INTERVAL '30 days' THEN 'pronto'
                ELSE 'futuro'
            END AS estado
        FROM modelo_fiscal_calendar c
        JOIN modelo_campana mc ON mc.id = c.campana_id
        JOIN aeat_modelo m ON m.id = mc.modelo_id
        WHERE m.codigo = :codigo
          AND c.activo = true
    """

    params = {"codigo": codigo}

    if campana:
        base += " AND mc.campana = :campana"
        params["campana"] = campana

    base += " ORDER BY c.fecha_fin_presentacion"

    rows = db.execute(text(base), params).mappings()
    return [dict(r) for r in rows]
