import argparse
import os

from sqlalchemy import create_engine, text

if __package__:
    from .pgc_dataset import PGC_ACCOUNTS_2021, PGC_AEAT_REFERENCES_2021, PGC_ESTADOS_FINANCIEROS_2021, PGC_MARCO_2021, PGC_NORMAS_2021, PGC_REFERENCIAS_FISCALES_2021
    from .runtime import get_database_url
else:
    from pgc_dataset import PGC_ACCOUNTS_2021, PGC_AEAT_REFERENCES_2021, PGC_ESTADOS_FINANCIEROS_2021, PGC_MARCO_2021, PGC_NORMAS_2021, PGC_REFERENCIAS_FISCALES_2021
    from runtime import get_database_url

PGC_MARCO = PGC_MARCO_2021
PGC_ACCOUNTS = PGC_ACCOUNTS_2021


def _upsert_marco(conn) -> int:
    row = conn.execute(
        text("SELECT 1 FROM pgc_marco WHERE codigo = :codigo LIMIT 1"),
        {"codigo": PGC_MARCO["codigo"]},
    ).first()
    if row:
        return 0

    conn.execute(
        text(
            """
            INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
            VALUES (:codigo, :titulo, :tipo, :anio, :texto, :url_boe, true)
            """
        ),
        PGC_MARCO,
    )
    return 1


def _upsert_cuenta(conn, cuenta) -> int:
    row = conn.execute(
        text("SELECT 1 FROM pgc_cuenta WHERE codigo = :codigo LIMIT 1"),
        {"codigo": cuenta["codigo"]},
    ).first()
    if row:
        return 0

    conn.execute(
        text(
            """
            INSERT INTO pgc_cuenta (
                codigo, descripcion, nivel, padre_codigo, grupo, clase,
                saldo_normal, tipo_cuenta, vigente, nota
            )
            VALUES (
                :codigo, :descripcion, :nivel, :padre_codigo, :grupo, :clase,
                :saldo_normal, :tipo_cuenta, true, :nota
            )
            """
        ),
        {
            "codigo": cuenta["codigo"],
            "descripcion": cuenta["descripcion"],
            "nivel": cuenta["nivel"],
            "padre_codigo": cuenta["padre_codigo"],
            "grupo": cuenta["grupo"],
            "clase": cuenta["clase"],
            "saldo_normal": cuenta["saldo_normal"],
            "tipo_cuenta": cuenta["tipo_cuenta"],
            "nota": cuenta["nota"],
        },
    )
    return 1


def _upsert_estado_financiero(conn, estado) -> int:
    existing = conn.execute(
        text(
            """
            SELECT 1
            FROM pgc_estado_financiero ef
            LEFT JOIN pgc_cuenta c ON c.id = ef.cuenta_id
            WHERE ef.estado = :estado
              AND ef.tipo_presentacion = :tipo_presentacion
              AND ef.orden = :orden
              AND ef.periodo = :periodo
            LIMIT 1
            """
        ),
        {
            "estado": estado["estado"],
            "tipo_presentacion": estado["tipo_presentacion"],
            "orden": estado["orden"],
            "periodo": estado["periodo"],
        },
    ).first()
    if existing:
        return 0

    cuenta_id = None
    if estado.get("cuenta_codigo"):
        cuenta_id = conn.execute(
            text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo LIMIT 1"),
            {"codigo": estado["cuenta_codigo"]},
        ).scalar_one_or_none()

    conn.execute(
        text(
            """
            INSERT INTO pgc_estado_financiero (cuenta_id, estado, tipo_presentacion, orden, periodo, importe_base, importe_anterior, nota_pieds)
            VALUES (:cuenta_id, :estado, :tipo_presentacion, :orden, :periodo, :importe_base, :importe_anterior, :nota_pieds)
            """
        ),
        {
            "cuenta_id": cuenta_id,
            "estado": estado["estado"],
            "tipo_presentacion": estado["tipo_presentacion"],
            "orden": estado["orden"],
            "periodo": estado["periodo"],
            "importe_base": estado.get("importe_base"),
            "importe_anterior": estado.get("importe_anterior"),
            "nota_pieds": estado.get("nota_pieds"),
        },
    )
    return 1


def _upsert_norma(conn, norma) -> int:
    existing = conn.execute(
        text(
            """
            SELECT 1
            FROM pgc_norma_valoracion nv
            LEFT JOIN pgc_cuenta c ON c.id = nv.cuenta_id
            WHERE nv.norma_ref = :norma_ref
              AND COALESCE(nv.articulo, '') = COALESCE(:articulo, '')
              AND COALESCE(c.codigo, '') = COALESCE(:cuenta_codigo, '')
            LIMIT 1
            """
        ),
        {
            "norma_ref": norma["norma_ref"],
            "articulo": norma["articulo"],
            "cuenta_codigo": norma["cuenta_codigo"],
        },
    ).first()
    if existing:
        return 0

    marco_id = conn.execute(
        text("SELECT id FROM pgc_marco WHERE codigo = :codigo LIMIT 1"),
        {"codigo": PGC_MARCO["codigo"]},
    ).scalar_one()

    cuenta_id = None
    if norma["cuenta_codigo"]:
        cuenta_id = conn.execute(
            text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo LIMIT 1"),
            {"codigo": norma["cuenta_codigo"]},
        ).scalar_one_or_none()

    conn.execute(
        text(
            """
            INSERT INTO pgc_norma_valoracion (marco_id, cuenta_id, norma_ref, articulo, descripcion)
            VALUES (:marco_id, :cuenta_id, :norma_ref, :articulo, :descripcion)
            """
        ),
        {
            "marco_id": marco_id,
            "cuenta_id": cuenta_id,
            "norma_ref": norma["norma_ref"],
            "articulo": norma["articulo"],
            "descripcion": norma["descripcion"],
        },
    )
    return 1


def _upsert_referencia_fiscal(conn, ref) -> int:
    existing = conn.execute(
        text(
            """
            SELECT 1
            FROM pgc_cuenta_fiscal_ref r
            LEFT JOIN pgc_cuenta c ON c.id = r.cuenta_id
            WHERE COALESCE(c.codigo, '') = COALESCE(:cuenta_codigo, '')
              AND r.modelo = :modelo
              AND COALESCE(r.casilla, '') = COALESCE(:casilla, '')
              AND COALESCE(r.ejercicio, '') = COALESCE(:ejercicio, '')
            LIMIT 1
            """
        ),
        {
            "cuenta_codigo": ref["cuenta_codigo"],
            "modelo": ref["modelo"],
            "casilla": ref["casilla"],
            "ejercicio": ref["ejercicio"],
        },
    ).first()
    if existing:
        return 0

    cuenta_id = None
    if ref["cuenta_codigo"]:
        cuenta_id = conn.execute(
            text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo LIMIT 1"),
            {"codigo": ref["cuenta_codigo"]},
        ).scalar_one_or_none()

    conn.execute(
        text(
            """
            INSERT INTO pgc_cuenta_fiscal_ref (cuenta_id, modelo, casilla, ejercicio, nota)
            VALUES (:cuenta_id, :modelo, :casilla, :ejercicio, :nota)
            """
        ),
        {
            "cuenta_id": cuenta_id,
            "modelo": ref["modelo"],
            "casilla": ref["casilla"],
            "ejercicio": ref["ejercicio"],
            "nota": ref.get("nota"),
        },
    )
    return 1


def _upsert_aeat_reference(conn, ref) -> int:
    existing = conn.execute(
        text(
            """
            SELECT 1
            FROM pgc_cuenta_modelo_aeat_ref r
            LEFT JOIN pgc_cuenta c ON c.id = r.cuenta_id
            WHERE COALESCE(c.codigo, '') = COALESCE(:cuenta_codigo, '')
              AND r.modelo_id = :modelo_id
              AND COALESCE(r.campana, '') = COALESCE(:campana, '')
            LIMIT 1
            """
        ),
        {
            "cuenta_codigo": ref["cuenta_codigo"],
            "modelo_id": ref["modelo_id"],
            "campana": ref.get("campana"),
        },
    ).first()
    if existing:
        return 0

    cuenta_id = None
    if ref["cuenta_codigo"]:
        cuenta_id = conn.execute(
            text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo LIMIT 1"),
            {"codigo": ref["cuenta_codigo"]},
        ).scalar_one_or_none()

    conn.execute(
        text(
            """
            INSERT INTO pgc_cuenta_modelo_aeat_ref (cuenta_id, modelo_id, campana, nota)
            VALUES (:cuenta_id, :modelo_id, :campana, :nota)
            """
        ),
        {
            "cuenta_id": cuenta_id,
            "modelo_id": ref["modelo_id"],
            "campana": ref.get("campana"),
            "nota": ref.get("nota"),
        },
    )
    return 1


def run_sync(engine=None, run_once: bool = False) -> dict[str, int]:
    del run_once
    engine = engine or create_engine(get_database_url(), future=True)

    with engine.begin() as conn:
        marcos_upserted = _upsert_marco(conn)
        cuentas_upserted = sum(_upsert_cuenta(conn, cuenta) for cuenta in PGC_ACCOUNTS)
        normas_upserted = sum(_upsert_norma(conn, norma) for norma in PGC_NORMAS_2021)
        estados_upserted = sum(_upsert_estado_financiero(conn, estado) for estado in PGC_ESTADOS_FINANCIEROS_2021)
        refs_fiscales_upserted = sum(_upsert_referencia_fiscal(conn, ref) for ref in PGC_REFERENCIAS_FISCALES_2021)
        refs_aeat_upserted = sum(_upsert_aeat_reference(conn, ref) for ref in PGC_AEAT_REFERENCES_2021)

    return {
        "marcos_upserted": marcos_upserted,
        "cuentas_upserted": cuentas_upserted,
        "normas_upserted": normas_upserted,
        "estados_financieros_upserted": estados_upserted,
        "refs_fiscales_upserted": refs_fiscales_upserted,
        "refs_aeat_upserted": refs_aeat_upserted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed PGC 11.1 data")
    parser.add_argument("--db-url", help="Database URL override")
    parser.add_argument("--run-once", action="store_true", help="Run a single sync cycle")
    args = parser.parse_args()

    engine = create_engine(args.db_url or os.getenv("DATABASE_URL") or get_database_url(), future=True)
    run_sync(engine=engine, run_once=args.run_once)


if __name__ == "__main__":
    main()
