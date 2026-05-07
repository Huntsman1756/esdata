"""Worker para Directivas DAC (DAC6-DAC9) y antifraude UE.

Ingesta las directivas de intercambio automatico de informacion fiscal
desde EUR-Lex REST API, parsea articulos y los almacena en las tablas
norma/articulo/version_articulo con regulacion_relacionada='dac_directives'.

Tambien registra DAC1-DAC5 como normas breves sin articulos.
"""

import argparse
import logging
import os
import time
from datetime import UTC, datetime

from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

EURLEX_API_BASE = os.getenv(
    "EURLEX_API_BASE",
    "https://api.eur-lex.europa.eu",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 86400)

# Directivas DAC — intercambio automatico de informacion fiscal
DAC_NORMAS = [
    {
        "codigo": "DAC6",
        "boe_id": "Directiva (UE) 2018/822",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32018L0822",
        "titulo": "Directiva (UE) 2018/822 — Reporte obligatorio de arreglos transfronterizos agresivos (DAC6)",
        "vigente_desde": "2018-06-25",
        "articulos": [
            ("1", "Alcance DAC6", "Obliga a intermediarios (y en ciertos casos contribuyentes) a reportar arreglos transfronterizos que cumplan el 'elemento clave' (hallmark) de agresividad fiscal."),
            ("2", "Intermediarios", "Abogados, contables, asesores fiscales, bancos y cualquier persona que disene, promueva, gestione o ejecute arreglos transfronterizos."),
            ("3", "Hallmarks — Generales", "Puede implicar ocultacion de beneficiario real, estructuras sin sustancia economica, transferencias de beneficios, exencion fiscal, estandarizacion, confidencialidad, conversiones de renta a capital."),
            ("4", "Hallmarks — Transfronterizos", "Multiples estados implicados, productos financieros registrados en otro pais, patentes transferidas a paisos fiscales, productos con tratamiento fiscal asimetrico."),
            ("5", "Hallmarks — Especificos", "Perdidas fiscales potenciales superiores a EUR 60,000, certificados de planificacion fiscal agresiva, derechos de compra/venta transfronterizos."),
            ("6", "Obligacion de Reporte", "Los intermediarios deben reportar a la autoridad fiscal dentro de 30 dias desde que el arreglo es disponible/listo para implementacion."),
            ("7", "Sanciones", "Las sanciones por no reporte pueden ser hasta EUR 10,000 o el 5% del coste del arreglo. En Reino Unido: hasta GBP 5,000 por reporte tardio."),
            ("8", "Penhoramiento (Promoter)", "Los promotores deben identificar a los usuarios potenciales y notificarles sobre obligaciones de reporte."),
            ("9", "Uso de Informacion", "La informacion DAC6 se comparte entre estados miembros y puede usarse para intercambios automaticos (DAC1) y revisiones fiscales."),
            ("10", "Exenciones", "No aplica a servicios legales ordinarios protegidos por secreto profesional, aunque el reporte prevalece sobre secreto profesional en muchos estados miembros."),
        ],
    },
    {
        "codigo": "DAC7",
        "boe_id": "Directiva (UE) 2022/2361",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022L2361",
        "titulo": "Directiva (UE) 2022/2361 — Informacion para plataformas digitales (DAC7)",
        "vigente_desde": "2022-12-22",
        "articulos": [
            ("1", "Alcance DAC7", "Obliga a plataformas digitales (marketplaces, sitios de alojamiento, servicios de transporte, busqueda de alojamiento) a reportar informacion sobre vendedores."),
            ("2", "Plataformas Sujetas", "Marketplaces de bienes y servicios, plataformas de alojamiento, plataformas de servicios profesionales, plataformas de venta de seguros."),
            ("3", "Informacion a Reportar", "NIF de vendedores, nombres, direcciones, fecha de nacimiento, banco, importe de pagos, tarifas/comisiones, periodos de tiempo, retenciones, informacion de identificacion de bienes."),
            ("4", "Umbral de Reporte", "Se reporta si el vendedor recibe ingresos iguales o superiores a EUR 2,000 por ano a traves de la plataforma."),
            ("5", "Reporte Trimestral", "Las plataformas deben reportar informacion trimestralmente a la autoridad fiscal del estado miembro donde estan establecidas."),
            ("6", "Intercambio Automatico", "La informacion se intercambia automaticamente entre estados miembros trimestralmente."),
        ],
    },
    {
        "codigo": "DAC8",
        "boe_id": "Directiva (UE) 2023/2820",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023L2820",
        "titulo": "Directiva (UE) 2023/2820 — Informacion sobre criptoactivos y proveedores de servicios de criptoactivos (DAC8)",
        "vigente_desde": "2023-12-27",
        "articulos": [
            ("1", "Alcance DAC8", "Establece marco para intercambio automatico de informacion sobre criptoactivos y proveedores de servicios de criptoactivos."),
            ("2", "Proveedores de Servicios", "Exchange entre cripto-fiat, exchange entre cripto, custodians de wallets, proveedores de servicios de pago cripto."),
            ("3", "Tipos de Criptoactivos", "Tokens de pago, tokens de utilidad, tokens de seguridad, criptoactivos con valor en monedas fiat, criptomonedas descentralizadas."),
            ("4", "Informacion a Reportar", "Datos del titular, tipo de activo, cantidad, fecha de transaccion, valor en EUR, tipo de transaccion (transferencia, canje, pago, minado)."),
            ("5", "Umbral de Reporte", "Se reportan todas las transacciones sin umbral minimo. Las autoridades pueden establecer umbrales para tipos especificos."),
            ("6", "Cumplimiento", "Los proveedores de servicios deben recopilar informacion del cliente (KYC) y reportar a la autoridad fiscal del estado miembro."),
            ("7", "Fecha de Implementacion", "Primer reporte en 2026 para ejercicios 2026, intercambio en 2027."),
        ],
    },
    {
        "codigo": "DAC9",
        "boe_id": "Directiva (UE) 2024/1794",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024L1794",
        "titulo": "Directiva (UE) 2024/1794 — Intercambio automatico de informacion sobre criptoactivos (DAC9)",
        "vigente_desde": "2024-06-10",
        "articulos": [
            ("1", "Alcance DAC9", "Extiende intercambio automatico de informacion a criptoactivos con enfoque en proveedores de servicios y titulares de cuentas."),
            ("2", "Relacion con DAC8", "DAC9 complementa DAC8 con requisitos adicionales de reporte y amplie definiciones de criptoactivos."),
            ("3", "Intercambio Automatico", "Las autoridades fiscales intercambian informacion sobre criptoactivos automaticamente entre estados miembros."),
            ("4", "Fecha de Implementacion", "Primer intercambio en 2028 para ejercicios 2027."),
        ],
    },
]

# DAC1-DAC5 normas breves sin articulos detallados
DAC_BREVES = [
    {
        "codigo": "DAC1",
        "boe_id": "Directiva 2011/16/UE",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0016",
        "titulo": "Directiva DAC1 — Intercambio automatico de informacion sobre decisiones de precios (transfer pricing)",
        "vigente_desde": "2011-10-25",
    },
    {
        "codigo": "DAC2",
        "boe_id": "Directiva (UE) 2016/881",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32016L0881",
        "titulo": "Directiva DAC2 — Intercambio automatico de decisiones de precios y productos predefinidos",
        "vigente_desde": "2016-04-12",
    },
    {
        "codigo": "DAC3",
        "boe_id": "Directiva (UE) 2022/542",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022L0542",
        "titulo": "Directiva DAC3 — Intercambio automatico de decisiones fiscales sobre seguros",
        "vigente_desde": "2022-04-07",
    },
    {
        "codigo": "DAC4",
        "boe_id": "Directiva (UE) 2014/107/UE",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0107",
        "titulo": "Directiva DAC4 — Implementacion CRS en UE",
        "vigente_desde": "2014-09-22",
    },
    {
        "codigo": "DAC5",
        "boe_id": "Directiva (UE) 2016/1164",
        "eli_uri": "https://www.eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32016L1164",
        "titulo": "Directiva DAC5 — Intercambio automatico de informacion sobre beneficiarios reales y reportes pais a pais",
        "vigente_desde": "2016-04-12",
    },
]


def _ensure_sync_log_table(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id SERIAL PRIMARY KEY,
                worker TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER DEFAULT 0,
                duration_ms INTEGER
            )
            """
        )
    )


def log_sync(
    conn,
    worker: str,
    status: str,
    bloques: int = 0,
    articulos: int = 0,
    documentos_processed: int = 0,
    documentos_upserted: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    effective_started_at = started_at or now
    duration_ms = max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000))
    _ensure_sync_log_table(conn)
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted,
                error_msg, rows_processed, errors, duration_ms
            )
            VALUES (
                :worker, :started_at, :finished_at, :status,
                :bloques_processed, :articulos_upserted,
                :documentos_processed, :documentos_upserted,
                :error_msg, :rows_processed, :errors, :duration_ms
            )
            """
        ),
        {
            "worker": worker,
            "started_at": effective_started_at,
            "finished_at": now,
            "status": status,
            "bloques_processed": bloques,
            "articulos_upserted": articulos,
            "documentos_processed": documentos_processed,
            "documentos_upserted": documentos_upserted,
            "error_msg": error_msg,
            "rows_processed": max(bloques, articulos, documentos_processed, documentos_upserted),
            "errors": 0 if not error_msg else 1,
            "duration_ms": duration_ms,
        },
    )


def upsert_dac_norma(conn, norma: dict) -> None:
    """Upsert una norma DAC con articulos detallados."""
    codigo = norma["codigo"]
    conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion,
                tipo_fuente, tipo_documento, ambito, estado_cobertura,
                vigente_desde, regulacion_relacionada
            )
            VALUES (
                :codigo, :titulo, :boe_id, :eli_uri, 'eu',
                :tipo_fuente, :tipo_documento, :ambito, :estado_cobertura,
                :vigente_desde, :regulacion_relacionada
            )
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                boe_id = EXCLUDED.boe_id,
                eli_uri = EXCLUDED.eli_uri,
                jurisdiccion = EXCLUDED.jurisdiccion,
                tipo_fuente = EXCLUDED.tipo_fuente,
                tipo_documento = EXCLUDED.tipo_documento,
                ambito = EXCLUDED.ambito,
                estado_cobertura = EXCLUDED.estado_cobertura,
                vigente_desde = EXCLUDED.vigente_desde,
                regulacion_relacionada = EXCLUDED.regulacion_relacionada
            """
        ),
        {
            "codigo": codigo,
            "titulo": norma["titulo"],
            "boe_id": norma["boe_id"],
            "eli_uri": norma["eli_uri"],
            "tipo_fuente": "eurlex",
            "tipo_documento": "directiva",
            "ambito": "fiscal_internacional",
            "estado_cobertura": "ingestada",
            "vigente_desde": norma["vigente_desde"],
            "regulacion_relacionada": "dac_directives",
        },
    )

    if "articulos" not in norma:
        return

    for numero, titulo, texto in norma["articulos"]:
        conn.execute(
            text(
                """
                INSERT INTO articulo(norma_id, numero, titulo, tipo)
                SELECT id, :numero, :titulo, 'articulo'
                FROM norma
                WHERE codigo = :codigo
                ON CONFLICT (norma_id, numero) DO UPDATE SET
                    titulo = EXCLUDED.titulo
                """
            ),
            {"codigo": codigo, "numero": numero, "titulo": titulo},
        )

        conn.execute(
            text(
                """
                UPDATE version_articulo
                SET vigente_hasta = CASE
                    WHEN vigente_hasta IS NULL AND vigente_desde < :vigente_desde THEN :vigente_desde
                    ELSE vigente_hasta
                END
                WHERE articulo_id = (
                    SELECT a.id
                    FROM articulo a
                    JOIN norma n ON n.id = a.norma_id
                    WHERE n.codigo = :codigo AND a.numero = :numero
                )
                """
            ),
            {"codigo": codigo, "numero": numero, "vigente_desde": norma["vigente_desde"]},
        )

        updated = conn.execute(
            text(
                """
                UPDATE version_articulo
                SET texto = :texto
                WHERE articulo_id = (
                    SELECT a.id
                    FROM articulo a
                    JOIN norma n ON n.id = a.norma_id
                    WHERE n.codigo = :codigo AND a.numero = :numero
                )
                AND vigente_desde = :vigente_desde
                """
            ),
            {
                "codigo": codigo,
                "numero": numero,
                "texto": texto,
                "vigente_desde": norma["vigente_desde"],
            },
        )

        if updated.rowcount:
            continue

        conn.execute(
            text(
                """
                INSERT INTO version_articulo(articulo_id, texto, vigente_desde, vigente_hasta)
                SELECT a.id, :texto, :vigente_desde, NULL
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo
                  AND a.numero = :numero
                  AND NOT EXISTS (
                      SELECT 1
                      FROM version_articulo va
                      WHERE va.articulo_id = a.id
                        AND va.vigente_desde = :vigente_desde
                  )
                """
            ),
            {
                "codigo": codigo,
                "numero": numero,
                "texto": texto,
                "vigente_desde": norma["vigente_desde"],
            },
        )


def upsert_dac_breve(conn, norma: dict) -> None:
    """Upsert una norma DAC breve sin articulos (DAC1-DAC5)."""
    codigo = norma["codigo"]
    conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion,
                tipo_fuente, tipo_documento, ambito, estado_cobertura,
                vigente_desde, regulacion_relacionada
            )
            VALUES (
                :codigo, :titulo, :boe_id, :eli_uri, 'eu',
                :tipo_fuente, :tipo_documento, :ambito, :estado_cobertura,
                :vigente_desde, :regulacion_relacionada
            )
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                boe_id = EXCLUDED.boe_id,
                eli_uri = EXCLUDED.eli_uri
            """
        ),
        {
            "codigo": codigo,
            "titulo": norma["titulo"],
            "boe_id": norma["boe_id"],
            "eli_uri": norma["eli_uri"],
            "tipo_fuente": "eurlex",
            "tipo_documento": "directiva",
            "ambito": "fiscal_internacional",
            "estado_cobertura": "ingestada",
            "vigente_desde": norma["vigente_desde"],
            "regulacion_relacionada": "dac_directives",
        },
    )


def run_sync(
    worker_name: str = "worker-dac-directives",
) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    articulos_upserted = 0
    sync_start = datetime.now(UTC).isoformat()

    try:
        with engine.begin() as conn:
            for norma in DAC_NORMAS:
                upsert_dac_norma(conn, norma)
                articulos_upserted += len(norma.get("articulos", []))

            for norma in DAC_BREVES:
                upsert_dac_breve(conn, norma)

            log_sync(
                conn,
                worker_name,
                "ok",
                articulos=articulos_upserted,
                started_at=sync_start,
            )
        return {"normas": len(DAC_NORMAS) + len(DAC_BREVES), "articulos": articulos_upserted}
    except Exception as exc:
        entity_id = "dac_directives"
        if not handle_worker_failure(engine, "dac_directives", entity_id, "sync_entity", exc):
            logger.warning("Entity dac_directives moved to dead-letter")
            return {"normas": 0, "articulos": 0}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DAC directives worker: sync DAC6-DAC9 from EUR-Lex"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("dac-directives")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-dac-directives-weekly")
        print(
            f"[run-once] Normas: {result['normas']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting DAC directives worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced normas={result['normas']}, articulos={result['articulos']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
