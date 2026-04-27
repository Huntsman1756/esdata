#!/usr/bin/env python
"""Worker dedicado para Ley 22/2010, de 20 de julio, por la que se modifica el Texto Refundido de la Ley del Impuesto sobre Sociedades.

Modifica el TRLMV (TRLIS): obligaciones informativas, sanciones CNMV.
BOE ID: BOE-A-2010-16380
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

NORMA_CODIGO = "LEY222010"


def main():
    parser = argparse.ArgumentParser(
        description="Worker LEY222010: ingesta articulado Ley 22/2010 (obligaciones informativas, sanciones CNMV)"
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
        result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley222010")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting LEY222010 worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-ley222010")
            print(
                f"LEY222010 synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(datetime.UTC).isoformat()}"
            )
            time.sleep(interval)


if __name__ == "__main__":
    main()
