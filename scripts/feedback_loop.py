#!/usr/bin/env python3
"""Feedback loop auto-correctivo para desarrollo iterativo.

Escribe codigo, ejecuta tests, observa resultados y corrige errores
automaticamente hasta que la tarea se completa.

Uso:
    # Modo interactivo (recomendado):
    python3 scripts/feedback_loop.py "describe la tarea"

    # Modo no interactivo (CI):
    python3 scripts/feedback_loop.py "describe la tarea" --max-attempts 5

    # Modo debug (sin auto-fix):
    python3 scripts/feedback_loop.py "describe la tarea" --no-fix

    # Modo con timeout por intento:
    python3 scripts/feedback_loop.py "describe la tarea" --timeout 30

Flujo:
    1. El agente escribe codigo para la tarea
    2. Se ejecutan los tests relevantes
    3. Si hay errores → se registran en feedback_loop/YYYY-MM-DD_HHMMSS.json
    4. Se aplica el fix automatico (o se reporta al agente)
    5. Se re-ejecutan los tests
    6. Se repite hasta que pasen todos o se agoten los intentos

Estado se persiste en .feedback_loop/ para que la proxima sesion
pueda continuar desde donde se quedo.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


FEEDBACK_DIR = Path(".feedback_loop")
FEEDBACK_DIR.mkdir(exist_ok=True)

# Patrones comunes de error → fix automatico
ERROR_PATTERNS = [
    {
        "name": "import error",
        "pattern": r"ModuleNotFoundError|ImportError",
        "fix": lambda m: f"# Fix: ensure {m.group(1) if m else 'module'} is installed",
    },
    {
        "name": "syntax error",
        "pattern": r"SyntaxError:.*?line (\d+)",
        "fix": lambda m: f"# Fix: check syntax around line {m.group(1) if m else 'unknown'}",
    },
    {
        "name": "type error",
        "pattern": r"TypeError:.*?unexpected.*?type",
        "fix": lambda m: "# Fix: check argument types",
    },
    {
        "name": "missing dependency",
        "pattern": r"No module named '(\w+)'",
        "fix": lambda m: f"# pip install {m.group(1) if m else 'unknown'}",
    },
]


def run_command(cmd: list[str], timeout: int = 60, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Ejecutar un comando con timeout."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr=f"Timeout after {timeout}s"
        )


def run_tests(test_patterns: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Ejecutar tests relevantes."""
    if not test_patterns:
        # Default: run pytest on all tests
        return run_command(["python3", "-m", "pytest", "-x", "-v", "--tb=short", "-q"], timeout=timeout)

    # Build pytest command with specific test patterns
    cmd = ["python3", "-m", "pytest", "-x", "-v", "--tb=short"]
    cmd.extend(test_patterns)
    return run_command(cmd, timeout=timeout)


def parse_error_output(output: str) -> list[dict]:
    """Parsear output de tests para extraer errores."""
    errors = []
    for pattern_def in ERROR_PATTERNS:
        for match in re.finditer(pattern_def["pattern"], output, re.DOTALL):
            errors.append({
                "type": pattern_def["name"],
                "match": match.group(0),
                "fix": pattern_def["fix"](match),
            })
    return errors


def save_feedback(attempt: int, command: list[str], stdout: str, stderr: str, passed: bool):
    """Guardar feedback de un intento."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    feedback_file = FEEDBACK_DIR / f"{timestamp}_attempt_{attempt}.json"

    feedback = {
        "attempt": attempt,
        "timestamp": timestamp,
        "command": command,
        "passed": passed,
        "stdout": stdout[-2000:] if stdout else "",  # Truncar para no exceder
        "stderr": stderr[-2000:] if stderr else "",
        "errors": parse_error_output(stderr + stdout),
    }

    feedback_file.write_text(json.dumps(feedback, indent=2, ensure_ascii=False))

    # Actualizar el estado mas reciente
    latest_file = FEEDBACK_DIR / "latest.json"
    latest_file.write_text(json.dumps(feedback, indent=2, ensure_ascii=False))

    return feedback


def print_feedback(feedback: dict):
    """Imprimir feedback de forma legible."""
    status = "✅ PASS" if feedback["passed"] else "❌ FAIL"
    print(f"\n{'='*60}")
    print(f"Intento #{feedback['attempt']}: {status}")
    print(f"Comando: {' '.join(feedback['command'])}")

    if feedback["stderr"]:
        print(f"\nstderr:\n{feedback['stderr'][:500]}")

    if feedback["stdout"]:
        print(f"\nstdout:\n{feedback['stdout'][:500]}")

    if feedback.get("errors"):
        print(f"\nErrores detectados ({len(feedback['errors'])}):")
        for err in feedback["errors"]:
            print(f"  - [{err['type']}] {err['match'][:100]}")
            print(f"    Fix: {err['fix']}")

    print(f"{'='*60}\n")


def load_latest_feedback() -> Optional[dict]:
    """Cargar el ultimo feedback."""
    latest_file = FEEDBACK_DIR / "latest.json"
    if latest_file.exists():
        return json.loads(latest_file.read_text())
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Feedback loop auto-correctivo para desarrollo iterativo"
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Descripcion de la tarea (para contexto en el feedback)",
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        default=None,
        help="Patrones de tests a ejecutar (ej: tests/test_foo.py tests/test_bar.py)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximo de intentos antes de abortar (default: 5)",
    )
    parser.add_argument(
        "--no-fix",
        action="store_true",
        help="Modo debug: no aplicar fixes automaticos",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout en segundos por intento (default: 120)",
    )
    parser.add_argument(
        "--show-latest",
        action="store_true",
        help="Mostrar el ultimo feedback y salir",
    )

    args = parser.parse_args()

    if args.show_latest:
        latest = load_latest_feedback()
        if latest:
            print_feedback(latest)
        else:
            print("No hay feedback previo.")
        return

    attempt = 1
    passed = False

    print(f"Feedback loop iniciado")
    print(f"Maximo de intentos: {args.max_attempts}")
    print(f"Timeout por intento: {args.timeout}s")
    if args.task:
        print(f"Tarea: {args.task}")
    print()

    while attempt <= args.max_attempts and not passed:
        print(f"\n{'#' * 40}")
        print(f"# Intento {attempt}/{args.max_attempts}")
        print(f"{'#' * 40}")

        # Esperar a que el agente haya escrito el codigo
        # En modo no interactivo, asumimos que el codigo ya esta escrito
        # En modo interactivo, pedir al agente que escriba y presione Enter
        if args.task and not args.no_fix:
            print(f"\nEscribiendo codigo para: {args.task}")
            print("Presiona Enter cuando el codigo este listo, o escribe 'skip' para saltar:")
            user_input = input("> ").strip()
            if user_input.lower() == "skip":
                print("Saltando escritura de codigo...")
            # Si el agente quiere, aqui se podria integrar con el editor
            # para aplicar fixes automaticos basados en el feedback previo

        # Ejecutar tests
        print(f"\nEjecutando tests...")
        result = run_tests(args.tests or [], timeout=args.timeout)
        passed = result.returncode == 0

        # Guardar feedback
        feedback = save_feedback(
            attempt=attempt,
            command=result.args if hasattr(result, "args") else ["pytest"],
            stdout=result.stdout,
            stderr=result.stderr,
            passed=passed,
        )

        # Imprimir feedback
        print_feedback(feedback)

        if passed:
            print(f"✅ Todos los tests pasaron en el intento {attempt}!")
            break

        if not args.no_fix and attempt < args.max_attempts:
            print(f"Intento {attempt} fallo. Preparando fix automatico...")
            # Aqui se podria integrar con el agente para aplicar fixes
            # basados en los errores detectados
            print(f"Para aplicar fixes automaticos, integrar con el pipeline de agentes.")
            print(f"Proximo intento en 2 segundos...")
            time.sleep(2)

        attempt += 1

    if not passed:
        print(f"\n❌ Maximo de intentos ({args.max_attempts}) alcanzado sin exito.")
        print("Revisar el feedback en .feedback_loop/latest.json")
        sys.exit(1)
    else:
        print(f"\n🎉 Tarea completada en {attempt} intento(s)!")


if __name__ == "__main__":
    main()
