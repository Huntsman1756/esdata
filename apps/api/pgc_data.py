from sqlalchemy import text


def get_pgc_marco_actual(db) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT codigo, titulo, tipo, anio, texto, url_boe, vigente
            FROM pgc_marco
            WHERE vigente = true
            ORDER BY anio DESC, codigo ASC
            LIMIT 1
            """
        )
    ).mappings().first()
    return dict(row) if row else None


def list_pgc_cuentas(
    db,
    codigo: str | None = None,
    q: str | None = None,
    tipo: str | None = None,
    nivel: int | None = None,
    clase: str | None = None,
    grupo: str | None = None,
    padre_codigo: str | None = None,
) -> list[dict]:
    filters = []
    params: dict[str, object] = {}

    if codigo:
        filters.append("codigo = :codigo")
        params["codigo"] = codigo

    if q:
        filters.append("(LOWER(codigo) LIKE :q OR LOWER(descripcion) LIKE :q)")
        params["q"] = f"%{q.lower()}%"

    if tipo:
        filters.append("tipo_cuenta = :tipo")
        params["tipo"] = tipo

    if nivel is not None:
        filters.append("nivel = :nivel")
        params["nivel"] = nivel

    if clase:
        filters.append("clase = :clase")
        params["clase"] = clase

    if grupo:
        filters.append("grupo = :grupo")
        params["grupo"] = grupo

    if padre_codigo:
        filters.append("padre_codigo = :padre_codigo")
        params["padre_codigo"] = padre_codigo

    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT codigo, descripcion, nivel, padre_codigo, grupo, clase, saldo_normal, tipo_cuenta, vigente, nota
            FROM pgc_cuenta
            {where}
            ORDER BY codigo ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def search_pgc_cuentas(db, q: str) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT codigo, descripcion, nivel, padre_codigo, grupo, clase, saldo_normal, tipo_cuenta, vigente, nota
            FROM pgc_cuenta
            WHERE LOWER(codigo) LIKE :q OR LOWER(descripcion) LIKE :q OR LOWER(COALESCE(nota, '')) LIKE :q
            ORDER BY CASE WHEN LOWER(codigo) = :exact_q THEN 0 ELSE 1 END, codigo ASC
            """
        ),
        {"q": f"%{q.lower()}%", "exact_q": q.lower()},
    ).mappings()
    return [dict(row) for row in rows]


def list_pgc_normas_valoracion(
    db,
    norma_ref: str | None = None,
    cuenta_codigo: str | None = None,
) -> list[dict]:
    filters = []
    params: dict[str, object] = {}

    if norma_ref:
        filters.append("nv.norma_ref = :norma_ref")
        params["norma_ref"] = norma_ref

    if cuenta_codigo:
        filters.append("c.codigo = :cuenta_codigo")
        params["cuenta_codigo"] = cuenta_codigo

    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT nv.norma_ref, nv.articulo, nv.descripcion, c.codigo AS cuenta_codigo, c.descripcion AS cuenta_descripcion
            FROM pgc_norma_valoracion nv
            LEFT JOIN pgc_cuenta c ON c.id = nv.cuenta_id
            {where}
            ORDER BY nv.norma_ref ASC, nv.articulo ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def list_pgc_estados_financieros(
    db,
    estado: str | None = None,
    tipo_presentacion: str | None = None,
    periodo: str | None = None,
) -> list[dict]:
    filters = []
    params: dict[str, object] = {}

    if estado:
        filters.append("ef.estado = :estado")
        params["estado"] = estado

    if tipo_presentacion:
        filters.append("ef.tipo_presentacion = :tipo_presentacion")
        params["tipo_presentacion"] = tipo_presentacion

    if periodo:
        filters.append("ef.periodo = :periodo")
        params["periodo"] = periodo

    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT CAST(ef.id AS TEXT) AS id, ef.estado, ef.tipo_presentacion, ef.orden, ef.periodo,
                   ef.importe_base, ef.importe_anterior, ef.nota_pieds,
                   c.codigo AS cuenta_codigo, c.descripcion AS cuenta_descripcion
            FROM pgc_estado_financiero ef
            LEFT JOIN pgc_cuenta c ON c.id = ef.cuenta_id
            {where}
            ORDER BY ef.estado ASC, ef.orden ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def list_pgc_referencias_fiscales(
    db,
    modelo: str | None = None,
    cuenta_codigo: str | None = None,
) -> list[dict]:
    filters = []
    params: dict[str, object] = {}

    if modelo:
        filters.append("rf.modelo = :modelo")
        params["modelo"] = modelo

    if cuenta_codigo:
        filters.append("c.codigo = :cuenta_codigo")
        params["cuenta_codigo"] = cuenta_codigo

    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT rf.modelo, rf.casilla, rf.ejercicio, rf.nota,
                   c.codigo AS cuenta_codigo, c.descripcion AS cuenta_descripcion
            FROM pgc_cuenta_fiscal_ref rf
            LEFT JOIN pgc_cuenta c ON c.id = rf.cuenta_id
            {where}
            ORDER BY rf.modelo ASC, rf.casilla ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def list_pgc_aeat_references(
    db,
    modelo_id: int | None = None,
    cuenta_codigo: str | None = None,
    campana: str | None = None,
) -> list[dict]:
    filters = []
    params: dict[str, object] = {}

    if modelo_id is not None:
        filters.append("ra.modelo_id = :modelo_id")
        params["modelo_id"] = modelo_id

    if cuenta_codigo:
        filters.append("c.codigo = :cuenta_codigo")
        params["cuenta_codigo"] = cuenta_codigo

    if campana:
        filters.append("COALESCE(ra.campana, '') = :campana")
        params["campana"] = campana

    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT ra.modelo_id, ra.campana, ra.nota,
                   c.codigo AS cuenta_codigo, c.descripcion AS cuenta_descripcion
            FROM pgc_cuenta_modelo_aeat_ref ra
            LEFT JOIN pgc_cuenta c ON c.id = ra.cuenta_id
            {where}
            ORDER BY ra.modelo_id ASC, ra.campana ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]
