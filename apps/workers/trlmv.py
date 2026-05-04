#!/usr/bin/env python
"""Worker dedicado para TRLMV — RD Legislativo 4/2015 (Ley del Mercado de Valores).

Reutiliza la infraestructura de ingestion de boe.py.
BOE ID: BOE-A-2011-14568
"""

import argparse
import sys
from pathlib import Path

_workers_dir = Path(__file__).resolve().parent
if str(_workers_dir) not in sys.path:
    sys.path.insert(0, str(_workers_dir))

from apps.workers.boe import run_sync

NORMA_CODIGO = "TRLMV"


def main():
    parser = argparse.ArgumentParser(
        description="Worker TRLMV: ingesta articulado RD Legislativo 4/2015 Mercado de Valores"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Ejecutar un solo ciclo y salir"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Segundos entre ciclos (por defecto reutiliza SYNC_INTERVAL_SECONDS de boe)",
    )
    args = parser.parse_args()

    import time
    from datetime import UTC, datetime

    from apps.workers.runtime import configure_logging, get_interval_seconds

    configure_logging("worker-trlmv")
    interval = (
        args.interval
        if args.interval is not None
        else get_interval_seconds("SYNC_INTERVAL_SECONDS", 3600)
    )

    if args.run_once:
        result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-trlmv")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting TRLMV worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-trlmv")
            print(
                f"TRLMV synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)


if __name__ == "__main__":
    main()
