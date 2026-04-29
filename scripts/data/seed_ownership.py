import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

SHARES = [
    (3, 1, "empresa", "Telefonica, S.A.", 5.2, "directa", "2024-01-01", None, "BOE", "BOE-A-2024-5678", None),
    (4, 3, "empresa", "Banco Santander, S.A.", 100.0, "directa", "2024-01-01", None, "BOE", "BOE-A-2024-9012", None),
    (5, 4, "empresa", "Iberdrola, S.A.", 100.0, "directa", "2024-01-01", None, "BOE", "BOE-A-2024-9014", None),
    (1, 5, "empresa", "Mapfre, S.A.", 100.0, "directa", "2024-01-01", None, "BOE", "BOE-A-2024-9016", None),
    (1, 3, "empresa", "Banco Santander, S.A.", 23.5, "directa", "2024-01-01", None, "BOE", "BOE-A-2024-1234", None),
]

RELATIONS = [
    (1, 3, "participacion_significativa", 5.2, "2024-01-01", None, "BOE", "BOE-A-2024-5678", None, "Telefonica participa en Banco Santander"),
    (3, 4, "participacion_mayoritaria", 100.0, "2024-01-01", None, "BOE", "BOE-A-2024-9012", None, "Santander controla Iberdrola"),
    (4, 5, "grupo_economico", 100.0, "2024-01-01", None, "BOE", "BOE-A-2024-9014", None, "Iberdrola controla Mapfre"),
]

UBOS = [
    (1, "Ministerio de Hacienda (SEPI)", None, None, "es", "control_por_otros_medios", 23.5, "superior_50", "2024-01-01", None, "BOE", "BOE-A-2024-1234", None, None),
    (2, "Consejo de Administracion", None, None, "es", "administrador_legal", 100.0, "superior_50", "2024-01-01", None, "BOE", "BOE-A-2024-5678", None, None),
    (3, "Consejo de Administracion", None, None, "es", "administrador_legal", 100.0, "superior_50", "2024-01-01", None, "BOE", "BOE-A-2024-9020", None, None),
    (4, "Consejo de Administracion", None, None, "es", "administrador_legal", 100.0, "superior_50", "2024-01-01", None, "BOE", "BOE-A-2024-9021", None, None),
    (5, "Consejo de Administracion", None, None, "es", "administrador_legal", 100.0, "superior_50", "2024-01-01", None, "BOE", "BOE-A-2024-9022", None, None),
]

BENEFICIAL_OWNERS = [
    (1, "Ministerio de Hacienda (SEPI)", 23.5, "2024-01-01", "registro_boe", "2024-01-15"),
    (2, "Consejo de Administracion", 100.0, "2024-01-01", "statutory", "2024-01-15"),
    (3, "Consejo de Administracion", 100.0, "2024-01-01", "statutory", "2024-01-15"),
    (4, "Consejo de Administracion", 100.0, "2024-01-01", "statutory", "2024-01-15"),
    (5, "Consejo de Administracion", 100.0, "2024-01-01", "statutory", "2024-01-15"),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    for s in SHARES:
        empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_part, desde, hasta, fuente, fuente_ref, doc_id = s
        cur.execute(
            """
            INSERT INTO ownership_share (id, empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref, documento_id)
            VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje, tipo_part, desde, hasta, fuente, fuente_ref, doc_id),
        )

    for r in RELATIONS:
        origen, destino, tipo, pct, desde, hasta, fuente, ref, doc, nota = r
        cur.execute(
            """
            INSERT INTO ownership_relation (id, empresa_origen_id, empresa_destino_id, tipo_relacion, porcentaje, vigencia_desde, vigencia_hasta, fuente, fuente_ref, documento_id, nota)
            VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (origen, destino, tipo, pct, desde, hasta, fuente, ref, doc, nota),
        )

    for u in UBOS:
        empresa_id, nombre, nac, fnac, pais, tipo_ubo, pct, umbral, desde, hasta, fuente, ref, doc, nota = u
        cur.execute(
            """
            INSERT INTO ubo_record (id, empresa_id, nombre_persona, nacionalidad, fecha_nacimiento, pais_residencia, tipo_ubo, porcentaje_control, umbral_superado, vigencia_desde, vigencia_hasta, fuente, fuente_ref, documento_id, nota)
            VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (empresa_id, nombre, nac, fnac, pais, tipo_ubo, pct, umbral, desde, hasta, fuente, ref, doc, nota),
        )

    for b in BENEFICIAL_OWNERS:
        entity_id, owner_name, pct, acq_date, method, ver_date = b
        cur.execute(
            """
            INSERT INTO beneficial_owner_record (id, entity_id, owner_name, ownership_percentage, acquisition_date, verification_method, verification_date)
            VALUES (DEFAULT, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (entity_id, owner_name, pct, acq_date, method, ver_date),
        )

    conn.commit()
    total = len(SHARES) + len(RELATIONS) + len(UBOS) + len(BENEFICIAL_OWNERS)
    print(f"Seeded {total} ownership/UBO records ({len(SHARES)} shares, {len(RELATIONS)} relations, {len(UBOS)} UBOs, {len(BENEFICIAL_OWNERS)} beneficial owners)")
    conn.close()


if __name__ == "__main__":
    seed()
