from sqlalchemy import text


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


def get_active_campaign(db, codigo: str, campana: str = None):
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
                COUNT(DISTINCT ma.articulo_id) AS articulos_count,
                COUNT(DISTINCT mc.id) AS casillas_count
            FROM aeat_modelo m
            LEFT JOIN modelo_articulo ma ON ma.modelo_id = m.id
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
