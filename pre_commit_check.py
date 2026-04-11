# -*- coding: utf-8 -*-
"""pre_commit_check.py — compatible Windows/Linux/macOS"""
import subprocess, sys, os

# Forzar UTF-8 en stdout para Windows (cp1252 no soporta ✓/✗/⚠)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PASS, FAIL, WARN = "OK", "FAIL", "WARN"
results = []

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def file_contains(path, text):
    """Alternativa portable a grep."""
    try:
        return text in open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return False

# 1. Tests
code, out, err = run("pytest apps/api/tests/test_smoke.py -q --tb=short")
passed_line = next((l for l in out.splitlines() if "passed" in l), None)
results.append((PASS if code == 0 else FAIL,
    f"Tests: {passed_line}" if code == 0 else f"Tests fallaron:\n{out}\n{err}"))

# 2. Archivos criticos
for f in [
    "apps/api/services/search.py",
    "apps/api/mcp_server.py",
    "infra/sql/002_fulltext_search.sql",
]:
    results.append((PASS if os.path.exists(f) else FAIL,
        f"{'Presente' if os.path.exists(f) else 'FALTA'}: {f}"))

# 3. fastapi-mcp en requirements (sin grep)
req_path = "apps/api/requirements.txt"
if file_contains(req_path, "fastapi-mcp"):
    results.append((PASS, "fastapi-mcp en requirements.txt"))
else:
    results.append((FAIL, f"fastapi-mcp NO encontrado en {req_path}"))

# 4. mount_mcp en main.py (sin grep)
main_path = "apps/api/main.py"
if file_contains(main_path, "mount_mcp"):
    results.append((PASS, "mount_mcp en main.py"))
else:
    results.append((FAIL, f"mount_mcp NO encontrado en {main_path}"))

# 5. Lint con ruff
code, _, err = run(
    "ruff check apps/api/services/ apps/api/routers/ apps/api/mcp_server.py --quiet"
)
results.append((PASS if code == 0 else WARN,
    "ruff: sin errores" if code == 0 else f"ruff avisos: {err}"))

# 6. Recordatorios de deploy
results.append((WARN, "Migracion pendiente en prod antes del deploy:"))
results.append((WARN, "  psql $DATABASE_URL -f infra/sql/002_fulltext_search.sql"))

# --- Resumen ---
print()
print("=== Pre-commit check sprint-2 ===")
print()
width = max(len(msg) for _, msg in results) + 4
for icon, msg in results:
    print(f"  [{icon:4}]  {msg}")

fails = [r for r in results if r[0] == FAIL]
print()
if not fails:
    print("Listo para commit.")
else:
    print(f"{len(fails)} problema(s) — revisar antes de commitear.")
print()
sys.exit(0 if not fails else 1)
