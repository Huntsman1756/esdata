import psycopg
DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"
with psycopg.connect(DB) as conn:
    cur = conn.cursor()
    
    # Count articles per norma
    cur.execute("""
        SELECT n.codigo, COUNT(va.id) as articulos_con_texto, COUNT(DISTINCT a.id) as total_articulos
        FROM articulo a
        JOIN norma n ON n.id = a.norma_id
        LEFT JOIN version_articulo va ON va.articulo_id = a.id
        GROUP BY n.codigo ORDER BY n.codigo
    """)
    print("=== Artículos por norma ===")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} con texto, {r[2]} total")
    
    # Check FactA-specific articles
    cur.execute("""
        SELECT a.numero, a.titulo FROM articulo a
        WHERE a.norma_id = (SELECT id FROM norma WHERE codigo = 'LIVA')
        AND a.numero::text ~ '^[0-9]+$'
        AND CAST(a.numero AS integer) >= 162 AND CAST(a.numero AS integer) <= 187
        ORDER BY CAST(a.numero AS integer)
    """)
    print("\n=== LIVA FactA articles (162-187) ===")
    for r in cur.fetchall():
        print(f"  Art. {r[0]}: {r[1][:60]}")
    
    # Check IRNR articles
    cur.execute("""
        SELECT a.numero, a.titulo FROM articulo a
        WHERE a.norma_id = (SELECT id FROM norma WHERE codigo = 'IRNR')
        ORDER BY a.numero
    """)
    print("\n=== IRNR articles ===")
    for r in cur.fetchall():
        print(f"  Art. {r[0]}: {r[1][:60]}")
    
    # Check ES_US_CONVENIO
    cur.execute("SELECT id, titulo FROM norma WHERE codigo = 'ES_US_CONVENIO'")
    row = cur.fetchone()
    print(f"\n=== Convenio España-EE.UU. ===")
    if row:
        print(f"  ID: {row[0]}, Titulo: {row[1][:80]}...")
    else:
        print("  NO ENCONTRADO")
    
    # Check materias
    cur.execute("SELECT slug, etiqueta FROM materia WHERE slug IN ('facta', 'no_residentes', 'intracomunitario', 'fatca', 'convenios_doble_tributacion', 'exportacion_servicios')")
    print("\n=== Materias FactA ===")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
