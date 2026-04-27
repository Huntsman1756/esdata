"""Script para sugerir y asignar automaticamente documentos a lineas de criterio.

Fase 21 — Pipeline de curacion semiasistida.

Este script:
1. Escanea todos los documento_interpretativo con ambito conocido
2. Los agrupa por ambito
3. Para cada linea de criterio con ambitos, muestra los documentos candidatos
4. Permite asignar documentos candidatos a lineas automaticamente (--assign)
5. Solo asigna si la referencia no existe ya en linea_criterio_referencia

Uso basico:
    python scripts/seed_linea_criterio.py --dry-run

Asignar automaticamente:
    python scripts/seed_linea_criterio.py --assign

Asignar solo ambito especifico:
    python scripts/seed_linea_criterio.py --assign --ambito jurisprudencia_tributaria
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))


KNOWN_AMBITOS = [
    "jurisprudencia_tributaria",
    "jurisprudencia_pbcft",
    "jurisprudencia_mercantil_regulatoria",
]


def get_db_url() -> str:
    """Obtener URL de base de datos."""
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")


def get_candidatos_por_linea(conn, ambito_filtro: str | None = None):
    """Devolver lista de lineas con sus documentos candidatos.

    Args:
        conn: Conexion SQLAlchemy
        ambito_filtro: Si se proporciona, filtrar solo este ambito

    Returns:
        Lista de dicts con linea_id, linea_titulo, ambitos, candidatos
    """
    linea_query = """
        SELECT id, titulo, ambitos
        FROM linea_criterio
        WHERE activo = true
          AND ambitos IS NOT NULL
          AND array_length(ambitos, 1) > 0
        ORDER BY id
    """

    lineas = conn.execute(text(linea_query)).mappings().all()
    resultados = []

    for linea in lineas:
        linea_id = int(linea["id"])
        linea_titulo = linea["titulo"]
        linea_ambitos = linea["ambitos"] or []

        if ambito_filtro and ambito_filtro not in linea_ambitos:
            continue

        if not linea_ambitos:
            continue

        placeholders = ", ".join(f":a{i}" for i in range(len(linea_ambitos)))
        docs_query = f"""
            SELECT id, referencia, tipo_documento, organismo_emisor,
                   ambito, fecha, titulo, url_fuente
            FROM documento_interpretativo
            WHERE ambito = ANY(ARRAY[{placeholders}])
            ORDER BY fecha DESC
        """

        docs = conn.execute(
            text(docs_query),
            {f"a{i}": a for i, a in enumerate(linea_ambitos)},
        ).mappings().all()

        candidatos = []
        for doc in docs:
            doc_dict = dict(doc)
            score = _score_documento(doc_dict)
            candidatos.append({
                "id": int(doc_dict["id"]),
                "referencia": doc_dict["referencia"],
                "tipo_documento": doc_dict["tipo_documento"],
                "organismo_emisor": doc_dict["organismo_emisor"],
                "ambito": doc_dict["ambito"],
                "fecha": str(doc_dict["fecha"]),
                "titulo": doc_dict["titulo"],
                "url_fuente": doc_dict["url_fuente"],
                "score": score,
            })

        candidatos.sort(key=lambda c: (c["score"], c["fecha"]), reverse=True)
        candidatos = candidatos[:10]

        if candidatos:
            resultados.append({
                "linea_id": linea_id,
                "linea_titulo": linea_titulo,
                "ambitos": linea_ambitos,
                "candidatos": candidatos,
            })

    return resultados


def _score_documento(doc: dict) -> int:
    """Puntuacion de relevancia (0-2)."""
    score = 0
    ambito = doc.get("ambito", "") or ""
    if ambito in KNOWN_AMBITOS:
        score += 1

    tipo = (doc.get("tipo_documento") or "").lower()
    if tipo in ("sentencia", "auto"):
        score += 1

    org = (doc.get("organismo_emisor") or "").lower()
    if "tribunal supremo" in org or "audiencia nacional" in org:
        score += 1

    return score


def _asignar_candidatos(conn, resultados, dry_run: bool = True):
    """Asignar candidatos a lineas de criterio.

    Args:
        conn: Conexion SQLAlchemy
        resultados: Lista de lineas con candidatos (de get_candidatos_por_linea)
        dry_run: Si True, solo muestra que se asignaria sin hacerlo

    Returns:
        Tuple (asignados, ya_existian, errores)
    """
    asignados = 0
    ya_existian = 0
    errores = 0

    for linea in resultados:
        linea_id = linea["linea_id"]
        linea_titulo = linea["linea_titulo"]

        for candidato in linea["candidatos"]:
            doc_ref = candidato["referencia"]

            # Verificar si ya existe
            existe = conn.execute(
                text(
                    """
                    SELECT id FROM linea_criterio_referencia
                    WHERE linea_id = :linea_id AND documento_referencia = :doc_ref
                    """
                ),
                {"linea_id": linea_id, "doc_ref": doc_ref},
            ).mappings().one_or_none()

            if existe:
                ya_existian += 1
                continue

            # Verificar si el documento existe en documento_interpretativo
            doc_exists = conn.execute(
                text(
                    """
                    SELECT id, tipo_documento, organismo_emisor
                    FROM documento_interpretativo
                    WHERE referencia = :doc_ref
                    """
                ),
                {"doc_ref": doc_ref},
            ).mappings().one_or_none()

            if doc_exists:
                query = """
                    INSERT INTO linea_criterio_referencia
                        (linea_id, documento_referencia, tipo_documento, organismo_emisor, rol_en_linea, orden)
                    SELECT
                        :linea_id,
                        :doc_ref,
                        d.tipo_documento,
                        d.organismo_emisor,
                        'soporte_complementario',
                        COALESCE(
                            (SELECT COALESCE(MAX(orden), 0) + 1 FROM linea_criterio_referencia WHERE linea_id = :linea_id),
                            1
                        )
                    FROM documento_interpretativo d
                    WHERE d.referencia = :doc_ref
                """
            else:
                query = """
                    INSERT INTO linea_criterio_referencia
                        (linea_id, documento_referencia, rol_en_linea, orden)
                    VALUES
                        (:linea_id, :doc_ref, 'soporte_complementario',
                         COALESCE((SELECT COALESCE(MAX(orden), 0) + 1 FROM linea_criterio_referencia WHERE linea_id = :linea_id), 1))
                """

            if dry_run:
                print(f"  [DRY-RUN] Asignaria '{doc_ref}' a '{linea_titulo}'")
                asignados += 1
            else:
                try:
                    conn.execute(
                        text(query),
                        {"linea_id": linea_id, "doc_ref": doc_ref},
                    )
                    asignados += 1
                except Exception as e:
                    print(f"  [ERROR] Fallando asignar '{doc_ref}' a '{linea_titulo}': {e}")
                    errores += 1

    return asignados, ya_existian, errores


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de curacion semiasistida para lineas de criterio"
    )
    parser.add_argument(
        "--assign",
        action="store_true",
        help="Asignar automaticamente candidatos a lineas de criterio",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo mostrar que se haria sin ejecutar cambios",
    )
    parser.add_argument(
        "--ambito",
        choices=KNOWN_AMBITOS,
        default=None,
        help="Filtrar por ambito especifico",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="URL de base de datos (sobreescribe DATABASE_URL)",
    )
    args = parser.parse_args()

    db_url = args.db_url or get_db_url()
    engine = create_engine(db_url, future=True)

    with engine.begin() as conn:
        resultados = get_candidatos_por_linea(conn, ambito_filtro=args.ambito)

        if not resultados:
            print("No se encontraron lineas de criterio con ambitos o documentos candidatos.")
            return

        print(f"Lineas de criterio con sugerencias: {len(resultados)}\n")

        for linea in resultados:
            print(f"Linea #{linea['linea_id']}: {linea['linea_titulo']}")
            print(f"  Ambitos: {', '.join(linea['ambitos'])}")
            print(f"  Candidatos: {len(linea['candidatos'])}\n")

            for c in linea["candidatos"]:
                score_str = "+++" if c["score"] == 2 else "++" if c["score"] == 1 else "+"
                print(f"  [{score_str}] {c['referencia']} ({c['tipo_documento']}) - {c['organismo_emisor']}")
                print(f"       Fecha: {c['fecha']} | Ambito: {c['ambito']}")
                if c.get("url_fuente"):
                    print(f"       URL: {c['url_fuente']}")
                print()

            if args.assign:
                print(f"  -> Procesando asignaciones para linea #{linea['linea_id']}...")
                asignados, ya_existian, errores = _asignar_candidatos(
                    conn, [linea], dry_run=not args.assign
                )
                print(f"     Asignados: {asignados}, Ya existian: {ya_existian}, Errores: {errores}\n")

    if not args.dry_run and args.assign:
        print("Cambios persistidos en base de datos.")
    else:
        print("\nModo dry-run: no se realizaron cambios.")


if __name__ == "__main__":
    main()
