#!/usr/bin/env python
"""Worker dedicado para Ley 27/2014 de Impuesto sobre Sociedades.

Reutiliza la infraestructura de ingestion de boe.py ya que LIS
esta en DEFAULT_NORMAS con boe_id=BOE-A-2014-12328.
"""

import argparse
import sys
from pathlib import Path

_workers_dir = Path(__file__).resolve().parent
if str(_workers_dir) not in sys.path:
    sys.path.insert(0, str(_workers_dir))

from apps.workers.boe import run_sync

NORMA_CODIGO = "LIS"


def main():
    parser = argparse.ArgumentParser(
        description="Worker LIS: ingesta articulado Ley 27/2014 Impuesto Sociedades"
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

    import os
    import time
    from datetime import datetime, timezone

    from apps.workers.runtime import configure_logging, get_interval_seconds

    logger = configure_logging("worker-ley272014")
    interval = args.interval if args.interval is not None else get_interval_seconds("SYNC_INTERVAL_SECONDS", 3600)

    if args.run_once:
        result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley272014")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting LIS worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley272014")
            print(
                f"LIS synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(timezone.utc).isoformat()}"
            )
            time.sleep(interval)


if __name__ == "__main__":
    main()
