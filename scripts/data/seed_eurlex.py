#!/usr/bin/env python
"""Seed EUR-Lex: ejecutar worker eurlex.py para poblar normas UE.

Fase 35.9 — EUR-Lex (Legislacion de la UE)

Ejecuta el worker eurlex.py con los CELEXs hardcodeados y
SPARQL discovery para encontrar nueva legislacion.

Uso:
    python scripts/data/seed_eurlex.py [--run-once]
"""

import sys
from pathlib import Path

# Agregar apps/workers al path para importar eurlex
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "workers"))

from eurlex import run_sync


def main() -> None:
    print("=" * 60)
    print("EUR-Lex Seed — Fase 35.9")
    print("=" * 60)
    print(f"  CELEXs hardcodeados: {len(__import__('eurlex', fromlist=['EURLEX_NORMAS']).EURLEX_NORMAS)}")
    print()

    result = run_sync(worker_name="seed-eurlex")

    print()
    print("-" * 60)
    print(f"  Bloques procesados: {result['bloques']}")
    print(f"  Articulos upserted: {result['articulos']}")
    print(f"  Normas upserted:    {result['normas']}")
    print(f"  Nuevos (SPARQL):    {result['nuevos_sparql']}")
    print("-" * 60)
    print("OK: EUR-Lex seed completado")


if __name__ == "__main__":
    main()
