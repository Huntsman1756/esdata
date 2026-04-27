#!/usr/bin/env python
"""Worker dedicado para Real Decreto 217/2008, de 14 de febrero, sobre normas contables para las sociedades que elaboren sus estados financieros individualmente o consolidadas.

Normas contables para bancos y sociedades de valores.
BOE ID: BOE-A-2008-500
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

NORMA_CODIGO = "RD2172008"


def main():
    parser = argparse.ArgumentParser(
        description="Worker RD2172008: ingesta articulado RD 217/2008 (normas contables bancos y sociedades de valores)"
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
        result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-rd2172008")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
        )
    else:
        print(f"Starting RD2172008 worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(codigos=[NORMA_CODIGO], worker_name="cron-rd2172008")
            print(
                f"RD2172008 synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(datetime.UTC).isoformat()}"
            )
            time.sleep(interval)


if __name__ == "__main__":
    main()
