#!/usr/bin/env python
"""Worker dedicado para Ley 11/2021 de prevencion y prevencion del fraude.

Reutiliza la infraestructura de ingestion de boe.py ya que LEY112021
esta en DEFAULT_NORMAS con boe_id=BOE-A-2021-11382.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

_workers_dir = Path(__file__).resolve().parent
if str(_workers_dir) not in sys.path:
    sys.path.insert(0, str(_workers_dir))

from apps.workers.boe import run_sync

NORMA_CODIGO = "LEY112021"


def main():
    parser = argparse.ArgumentParser(
        description="Worker LEY112021: ingesta articulado Ley 11/2021 prevencion fraude"
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

    from apps.workers.runtime import get_interval_seconds

    interval = args.interval if args.interval is not None else get_interval_seconds("SYNC_INTERVAL_SECONDS", 3600)

    if args.run_once:
        result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley112021")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting LEY112021 worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley112021")
            print(
                f"LEY112021 synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(datetime.UTC).isoformat()}"
            )
            time.sleep(interval)


if __name__ == "__main__":
    main()
