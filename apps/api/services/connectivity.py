from sqlalchemy import text


def get_article_connectivity(db, norma_codigo: str, articulo_numero: str):
    articulo = (
        db.execute(
            text(
                """
                SELECT a.id, n.codigo AS norma, a.numero, a.titulo
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :norma_codigo AND a.numero = :articulo_numero
                LIMIT 1
                """
            ),
            {"norma_codigo": norma_codigo, "articulo_numero": articulo_numero},
        )
        .mappings()
        .first()
    )
    if not articulo:
        return None

    modelos = list(
        db.execute(
            text(
                """
                SELECT DISTINCT m.codigo, m.nombre, m.impuesto, ma.fuente
                FROM modelo_articulo ma
                JOIN aeat_modelo m ON m.id = ma.modelo_id
                WHERE ma.articulo_id = :articulo_id
                ORDER BY m.codigo ASC
                """
            ),
            {"articulo_id": articulo["id"]},
        ).mappings()
    )

    doctrina = list(
        db.execute(
            text(
                """
                SELECT DISTINCT d.id, d.referencia, d.organismo_emisor, d.tipo_documento, da.confianza_enlace
                FROM documento_articulo da
                JOIN documento_interpretativo d ON d.id = da.documento_id
                WHERE da.articulo_id = :articulo_id
                ORDER BY da.confianza_enlace DESC, d.referencia ASC
                """
            ),
            {"articulo_id": articulo["id"]},
        ).mappings()
    )

    obligaciones = list(
        db.execute(
            text(
                """
                SELECT DISTINCT o.codigo, o.nombre, o.fuente, od.tipo_relacion
                FROM documento_articulo da
                JOIN obligacion_documento od ON od.documento_id = da.documento_id
                JOIN obligacion_regulatoria o ON o.id = od.obligacion_id
                WHERE da.articulo_id = :articulo_id
                ORDER BY o.codigo ASC
                """
            ),
            {"articulo_id": articulo["id"]},
        ).mappings()
    )

    return {
        "articulo": {
            "norma": articulo["norma"],
            "numero": articulo["numero"],
            "titulo": articulo["titulo"],
        },
        "modelos": [dict(row) for row in modelos],
        "doctrina": [
            {
                "referencia": row["referencia"],
                "organismo_emisor": row["organismo_emisor"],
                "tipo_documento": row["tipo_documento"],
                "confianza_enlace": float(row["confianza_enlace"]),
            }
            for row in doctrina
        ],
        "obligaciones": [dict(row) for row in obligaciones],
        "totales": {
            "modelos": len(modelos),
            "doctrina": len(doctrina),
            "obligaciones": len(obligaciones),
        },
    }


def get_document_connectivity(db, referencia: str):
    documento = (
        db.execute(
            text(
                """
                SELECT id, referencia, organismo_emisor, tipo_documento
                FROM documento_interpretativo
                WHERE referencia = :referencia
                LIMIT 1
                """
            ),
            {"referencia": referencia},
        )
        .mappings()
        .first()
    )
    if not documento:
        return None

    articulos = list(
        db.execute(
            text(
                """
                SELECT DISTINCT n.codigo AS norma, a.numero, da.metodo_enlace, da.confianza_enlace
                FROM documento_articulo da
                JOIN articulo a ON a.id = da.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE da.documento_id = :documento_id
                ORDER BY da.confianza_enlace DESC, n.codigo ASC, a.numero ASC
                """
            ),
            {"documento_id": documento["id"]},
        ).mappings()
    )

    obligaciones = list(
        db.execute(
            text(
                """
                SELECT DISTINCT o.codigo, o.nombre, o.fuente, od.tipo_relacion
                FROM obligacion_documento od
                JOIN obligacion_regulatoria o ON o.id = od.obligacion_id
                WHERE od.documento_id = :documento_id
                ORDER BY o.codigo ASC
                """
            ),
            {"documento_id": documento["id"]},
        ).mappings()
    )

    return {
        "documento": {
            "referencia": documento["referencia"],
            "organismo_emisor": documento["organismo_emisor"],
            "tipo_documento": documento["tipo_documento"],
        },
        "articulos": [
            {
                "norma": row["norma"],
                "numero": row["numero"],
                "metodo_enlace": row["metodo_enlace"],
                "confianza_enlace": float(row["confianza_enlace"]),
            }
            for row in articulos
        ],
        "obligaciones": [dict(row) for row in obligaciones],
        "totales": {
            "articulos": len(articulos),
            "obligaciones": len(obligaciones),
        },
    }


def get_obligation_connectivity(db, codigo: str):
    obligacion = (
        db.execute(
            text(
                """
                SELECT id, codigo, nombre, fuente
                FROM obligacion_regulatoria
                WHERE codigo = :codigo
                LIMIT 1
                """
            ),
            {"codigo": codigo},
        )
        .mappings()
        .first()
    )
    if not obligacion:
        return None

    documentos = list(
        db.execute(
            text(
                """
                SELECT DISTINCT d.id, d.referencia, d.organismo_emisor, d.tipo_documento, od.tipo_relacion
                FROM obligacion_documento od
                JOIN documento_interpretativo d ON d.id = od.documento_id
                WHERE od.obligacion_id = :obligacion_id
                ORDER BY d.referencia ASC
                """
            ),
            {"obligacion_id": obligacion["id"]},
        ).mappings()
    )

    articulos = list(
        db.execute(
            text(
                """
                SELECT DISTINCT n.codigo AS norma, a.numero, da.metodo_enlace, da.confianza_enlace
                FROM obligacion_documento od
                JOIN documento_articulo da ON da.documento_id = od.documento_id
                JOIN articulo a ON a.id = da.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE od.obligacion_id = :obligacion_id
                ORDER BY da.confianza_enlace DESC, n.codigo ASC, a.numero ASC
                """
            ),
            {"obligacion_id": obligacion["id"]},
        ).mappings()
    )

    return {
        "obligacion": {
            "codigo": obligacion["codigo"],
            "nombre": obligacion["nombre"],
            "fuente": obligacion["fuente"],
        },
        "documentos": [dict(row) for row in documentos],
        "articulos": [
            {
                "norma": row["norma"],
                "numero": row["numero"],
                "metodo_enlace": row["metodo_enlace"],
                "confianza_enlace": float(row["confianza_enlace"]),
            }
            for row in articulos
        ],
        "totales": {
            "documentos": len(documentos),
            "articulos": len(articulos),
        },
    }
