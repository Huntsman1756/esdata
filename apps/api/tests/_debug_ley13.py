"""Debug: check version_articulo data in conftest test DB."""
import sys, os, tempfile
from pathlib import Path

sys.path.insert(0, r"G:\_Proyectos\esdata\apps\api")
sys.path.insert(0, r"G:\_Proyectos\esdata\apps\api\tests")
os.chdir(r"G:\_Proyectos\esdata\apps\api")

# Remove cached modules
for mod in list(sys.modules.keys()):
    if mod in ("db", "conftest", "main", "routers.ley13_2023"):
        del sys.modules[mod]

import conftest as _c
from sqlalchemy import text

with _c.engine.begin() as conn:
    # Check what's in the DB
    rows = conn.execute(text("""
        SELECT va.id, va.articulo_id, va.texto, va.vigente_desde, va.vigente_hasta, va.boe_bloque_id, a.numero, a.titulo
        FROM version_articulo va
        JOIN articulo a ON a.id = va.articulo_id
        WHERE a.norma_id IN (SELECT id FROM norma WHERE codigo = 'LEY13_2023')
    """)).fetchall()
    print(f"Found {len(rows)} version_articulo rows:")
    for r in rows:
        print(f"  id={r[0]}, articulo_id={r[1]}, texto={r[2][:40] if r[2] else 'NULL'}, vigente_desde={r[3]}, vigente_hasta={r[4]}, boe_bloque_id={r[5]}, numero={r[6]}")
    
    # Now run the exact router query
    rows2 = conn.execute(text("""
        SELECT a.numero, a.titulo, a.tipo,
               va.texto, va.vigente_desde, va.vigente_hasta
        FROM version_articulo va
        JOIN articulo a ON a.id = va.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE va.articulo_id = 17
        ORDER BY va.vigente_desde DESC
    """)).fetchall()
    print(f"\nRouter query returned {len(rows2)} rows:")
    for r in rows2:
        print(f"  numero={r[0]}, titulo={r[1][:30] if r[1] else 'NULL'}, tipo={r[2]}, texto={r[3][:40] if r[3] else 'NULL'}, vigente_desde={r[4]}, vigente_hasta={r[5]}")
